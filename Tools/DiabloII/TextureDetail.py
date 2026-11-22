"""Higher-resolution feather albedo with drawn detail, from a stock feather-card atlas.

A recolour keeps the stock texture's resolution: scaled up on a big body (the Giant Raven is the
Druid's Raven x4) the feather cards show soft texels and saw-tooth alpha edges. `feathers()`
makes a texture twice the size (or `scale` times) that follows the stock layout card by card:

  - every card (a connected piece of the alpha mask) gets its own frame from its shape: the long
    axis, the tip (the end away from the thin quill), and a midline (the rachis) found per
    slice along the axis, so slightly curved feathers are followed;
  - barbs: fine ridges leaving the rachis at `barbAngle` degrees towards the tip on both vanes,
    slightly curved, with jittered spacing and a few vane splits (gaps where barbs part);
  - a soft gloss: low-frequency sheen in `glossColour` across the vanes, strongest part-way out
    from the rachis, varying along each feather; a thin highlight on the rachis;
  - small pieces (down, hair-like strands) get fine strands along their own axis instead;
  - alpha: upscaled, the stock texel steps smoothed out and the edge ramp narrowed to about two
    texels, so an alpha test cuts a smooth contour instead of stair steps; the vane margins are
    frayed a little along the barbs (feather edges, not a saw);
  - colour under transparent texels is filled from the nearest card, so mips and filtering do
    not pull in the background.

Colour: the stock colour is recoloured first (`recolor`, as RecolorEffect.recolor_rgb), so the
result keeps the stock's look and only gains detail. Everything is computed; nothing is copied
from anywhere but the input image.

`encode_bc3()` writes the game's own .texture layout (BC3 sRGB, full mip chain, the header of
HdTexture.from_image_bc3) through DirectXTex texconv when it is installed (better blocks, and
`--keep-coverage` keeps alpha-tested cards from thinning out in the mips), else through Pillow.

usage:
  TextureDetail.py feathers <stock.texture|png> <out.texture> [--png preview.png] [--options json]
"""
import io
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import HdTexture  # noqa: E402

DEFAULTS = {
    'scale': 2,
    'barbPeriod': 3.4,          # texels of the output between barbs
    'barbAngle': 38.0,          # degrees from the rachis, towards the tip
    'barbCurve': 0.004,         # bend of the barbs (per texel of distance from the rachis)
    'barbStrength': 0.26,       # luminance swing of the barb ridges
    'splits': 0.22,             # share of the vane with a split (barbs parted)
    'clump': 6.0,               # barbs per clump: neighbouring barbs cling together in groups
    'gloss': 0.55,              # strength of the sheen
    'glossColour': [40, 50, 92],    # sRGB added at full sheen: raven blue-violet
    'rachis': 0.25,             # highlight on the shaft
    'fray': 0.10,               # alpha threshold swing at the vane margins
    'edge': [0.22, 0.78],       # alpha remap: smoothstep(edge0, edge1) after smoothing
    'smooth': 0.9,              # Gaussian sigma (output texels) that rounds the stock texel steps
    'minCard': 900,             # input texels: smaller pieces count as down / strands
    'seed': 7,
    'recolor': None,            # {"hue", "minSat", "hueShift", "sat", "value"}
}


def _smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _noise(shape, cell, rng, octaves=3):
    """Smooth value noise in 0..1 (fbm of bicubic-upscaled random grids)."""
    from PIL import Image
    h, w = shape
    out = np.zeros(shape, np.float32)
    total = 0.0
    amp = 1.0
    for o in range(octaves):
        c = max(2.0, cell / (2 ** o))
        gh, gw = int(h / c) + 3, int(w / c) + 3
        grid = rng.random((gh, gw)).astype(np.float32)
        img = Image.fromarray(grid, 'F').resize((int(gw * c), int(gh * c)), Image.BICUBIC)
        out += amp * np.asarray(img)[:h, :w]
        total += amp
        amp *= 0.5
    out /= total
    lo, hi = np.percentile(out, 1), np.percentile(out, 99)
    return np.clip((out - lo) / max(1e-6, hi - lo), 0, 1)


def _recolor(rgb, op):
    """Vectorised RecolorEffect.recolor_rgb on an (..., 3) array in 0..1."""
    if not op:
        return rgb
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(-1), rgb.min(-1)
    v = mx
    d = mx - mn
    s = np.where(mx > 0, d / np.maximum(mx, 1e-9), 0)
    h = np.zeros_like(mx)
    nz = d > 1e-9
    rc = np.where(nz, (mx - r) / np.maximum(d, 1e-9), 0)
    gc = np.where(nz, (mx - g) / np.maximum(d, 1e-9), 0)
    bc = np.where(nz, (mx - b) / np.maximum(d, 1e-9), 0)
    h = np.where(r == mx, bc - gc, np.where(g == mx, 2.0 + rc - bc, 4.0 + gc - rc))
    h = np.where(nz, (h / 6.0) % 1.0, 0)
    if 'hue' in op:
        h = np.full_like(h, (op['hue'] % 360) / 360.0)
        s = np.maximum(s, op.get('minSat', 0.0))
    h = (h + op.get('hueShift', 0) / 360.0) % 1.0
    s = np.minimum(1.0, s * op.get('sat', 1.0))
    v = np.minimum(1.0, v * op.get('value', 1.0))
    i = np.floor(h * 6.0).astype(int) % 6
    f = h * 6.0 - np.floor(h * 6.0)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    out = np.stack([np.choose(i, [v, q, p, p, t, v]), np.choose(i, [t, v, v, q, p, p]), np.choose(i, [p, p, t, v, v, q])], -1)
    return out


def _card_frames(alpha_in, scale, opts):
    """Per output texel: card id, along (towards the tip), across (from the midline), half-width.
    Computed on the input mask, then scaled up."""
    from scipy import ndimage
    mask = alpha_in > 0.5
    labels, count = ndimage.label(mask, structure=np.ones((3, 3)))
    H, W = alpha_in.shape
    oh, ow = H * scale, W * scale
    yy, xx = np.mgrid[0:oh, 0:ow].astype(np.float32)
    yy = (yy + 0.5) / scale - 0.5
    xx = (xx + 0.5) / scale - 0.5
    # every output texel belongs to the nearest card (so the frame also covers the soft margins)
    dist, (iy, ix) = ndimage.distance_transform_edt(~mask, return_indices=True)
    near = labels[iy, ix]
    near_out = near[np.clip(np.round(yy).astype(int), 0, H - 1), np.clip(np.round(xx).astype(int), 0, W - 1)]
    along = np.zeros((oh, ow), np.float32)
    across = np.zeros((oh, ow), np.float32)
    half = np.ones((oh, ow), np.float32)
    kind = np.zeros((oh, ow), np.int8)       # 1 = feather card, 2 = down / strand
    cards = []
    for k, sl in enumerate(ndimage.find_objects(labels), start=1):
        if sl is None:
            continue
        ys, xs = np.nonzero(labels[sl] == k)
        ys = ys + sl[0].start
        xs = xs + sl[1].start
        area = len(ys)
        pts = np.stack([xs, ys], 1).astype(np.float64)
        c = pts.mean(0)
        cov = np.cov((pts - c).T) if area > 2 else np.eye(2)
        w_, v_ = np.linalg.eigh(cov)
        u = v_[:, 1]
        n = np.array([-u[1], u[0]])
        s = (pts - c) @ u
        t = (pts - c) @ n
        sel = (near_out == k)
        S = (xx[sel] - c[0]) * u[0] + (yy[sel] - c[1]) * u[1]
        T = (xx[sel] - c[0]) * n[0] + (yy[sel] - c[1]) * n[1]
        if area < opts['minCard'] or len(s) < 10:
            along[sel] = S * scale
            across[sel] = T * scale
            half[sel] = max(1.0, math.sqrt(w_[0]) * 2 * scale)
            kind[sel] = 2
            continue
        # midline and width per slice along the axis
        bins = np.linspace(s.min(), s.max() + 1e-6, max(8, int((s.max() - s.min()) / 6)) + 1)
        idx = np.clip(np.digitize(s, bins) - 1, 0, len(bins) - 2)
        mids = np.array([np.median(t[idx == b]) if np.any(idx == b) else np.nan for b in range(len(bins) - 1)])
        widths = np.array([(t[idx == b].max() - t[idx == b].min()) if np.any(idx == b) else 0 for b in range(len(bins) - 1)])
        centres = (bins[:-1] + bins[1:]) / 2
        ok = ~np.isnan(mids)
        mids = np.interp(centres, centres[ok], mids[ok])
        mids = ndimage.uniform_filter1d(mids, 3, mode='nearest')
        widths = ndimage.uniform_filter1d(widths.astype(float), 3, mode='nearest')
        # the quill end is the end with the long bare stretch (both ends taper; the quill stays thin
        # for a long way): count the thin slices from each end. The tip is the other end.
        thin = widths < 0.22 * widths.max()
        run_start = int(np.argmin(thin)) if not thin.all() else len(thin)
        run_end = int(np.argmin(thin[::-1])) if not thin.all() else len(thin)
        if run_start != run_end:
            sign = 1.0 if run_start > run_end else -1.0
        else:
            q = max(1, len(widths) // 5)
            sign = 1.0 if widths[:q].mean() < widths[-q:].mean() else -1.0
        mid_out = np.interp(S, centres, mids)
        half_out = np.maximum(1.0, np.interp(S, centres, widths) / 2)
        along[sel] = sign * S * scale
        across[sel] = (T - mid_out) * scale
        half[sel] = half_out * scale
        kind[sel] = 1
        cards.append({'id': k, 'area': int(area), 'centre': [round(float(c[0]), 1), round(float(c[1]), 1)],
                      'axis': [round(float(u[0] * sign), 3), round(float(u[1] * sign), 3)]})
    return along, across, half, kind, cards


def _fill_transparent(rgb, alpha, iterations=10):
    """Colour under transparent texels from the nearest opaque ones (no background bleed in mips)."""
    from scipy import ndimage
    solid = alpha > 0.5
    if not solid.any():
        return rgb
    _, (iy, ix) = ndimage.distance_transform_edt(~solid, return_indices=True)
    filled = rgb[iy, ix]
    w = _smoothstep(0.0, 0.5, alpha)[..., None]
    return rgb * w + filled * (1 - w)


def feathers(img, options=None):
    """Stock feather atlas (Pillow RGBA) -> (Pillow RGBA at scale x, report)."""
    from PIL import Image, ImageFilter
    from scipy import ndimage
    opts = dict(DEFAULTS)
    opts.update(options or {})
    scale = int(opts['scale'])
    rng = np.random.default_rng(opts['seed'])
    src = np.asarray(img.convert('RGBA')).astype(np.float32) / 255.0
    H, W = src.shape[:2]
    oh, ow = H * scale, W * scale
    # colour: premultiplied Lanczos upscale (no dark fringe), then unpremultiplied
    a_in = src[..., 3]
    pre = src[..., :3] * a_in[..., None]

    def up(ch):
        return np.asarray(Image.fromarray(ch.astype(np.float32), 'F').resize((ow, oh), Image.LANCZOS))
    a_up = np.clip(up(a_in), 0, 1)
    rgb_up = np.stack([up(pre[..., i]) for i in range(3)], -1)
    rgb_fill = np.stack([up(_fill_transparent(src[..., :3], a_in)[..., i]) for i in range(3)], -1)
    rgb = np.where(a_up[..., None] > 0.05, np.clip(rgb_up / np.maximum(a_up[..., None], 1e-4), 0, 1), np.clip(rgb_fill, 0, 1))
    rgb = _recolor(rgb, opts['recolor'])

    along, across, half, kind, cards = _card_frames(a_in, scale, opts)
    feather = kind == 1
    down = kind == 2
    rel = np.clip(np.abs(across) / half, 0, 1.5)             # 0 at the rachis, 1 at the margin

    # barbs: iso-lines of w = along - |across| / tan(angle) - curve * across^2
    theta = math.radians(opts['barbAngle'])
    jitter = (_noise((oh, ow), 40 * scale, rng) - 0.5) * 3.0 + (_noise((oh, ow), 9 * scale, rng) - 0.5) * 1.6   # wander of the spacing
    w = along - np.abs(across) / math.tan(theta) - opts['barbCurve'] * across * across + jitter
    period = opts['barbPeriod'] / math.sin(theta)                 # along the axis
    phase = 2 * math.pi * w / period
    ridge = (0.5 + 0.5 * np.cos(phase)) ** 2.2                    # thin bright barb ridges
    # clumps: groups of barbs cling together; the barbs at a clump's edge are darker (shadowed)
    clump_phase = phase / opts['clump'] + (_noise((oh, ow), 18 * scale, rng) - 0.5) * 3.0
    clump = 0.5 + 0.5 * np.cos(clump_phase)
    # vane splits: a few places where neighbouring barbs part (a dark gap along a barb)
    split_field = _noise((oh, ow), 26 * scale, rng)
    split_gate = _smoothstep(1 - opts['splits'] - 0.05, 1 - opts['splits'] + 0.05, split_field)
    gap = split_gate * _smoothstep(0.92, 0.99, 0.5 + 0.5 * np.cos(phase / 7.0 + 1.3)) * (rel > 0.12)
    # fine barbules: a faint cross-hatch along the barbs
    barbule = 0.5 + 0.5 * np.sin(2 * math.pi * (along * 0.9 + np.abs(across) * 1.4) / 1.7)
    # no barbs on the shaft itself, nor on the bare quill (where the card is only a few texels wide)
    vane = _smoothstep(0.03, 0.12, rel) * _smoothstep(2.5 * scale, 5.0 * scale, half)
    lum = 1.0 + feather * vane * (opts['barbStrength'] * (ridge - 0.35) * (0.55 + 0.45 * clump) + 0.16 * (clump - 0.5)
                                  + 0.06 * (barbule - 0.5) - 0.55 * gap)
    # down and strands: fine lines along their own axis
    strands = 0.5 + 0.5 * np.sin(2 * math.pi * across / 2.1 + (_noise((oh, ow), 12 * scale, rng) - 0.5) * 5)
    lum = lum + down * 0.22 * (strands - 0.5)
    # rachis highlight
    shaft = np.exp(-(across / (0.9 * scale)) ** 2) * feather
    # gloss: sheen strongest part-way out on the vanes, varying along the feather and across cards
    sheen = np.exp(-((rel - 0.42) / 0.3) ** 2) * feather + 0.35 * down
    variation = _noise((oh, ow), 90 * scale, rng)
    streak = 0.5 + 0.5 * np.sin(2 * math.pi * along / (140.0 * scale) + variation * 4)
    gloss = opts['gloss'] * sheen * (0.35 + 0.65 * variation * streak) * (0.75 + 0.25 * ridge)
    gc = np.asarray(opts['glossColour'], np.float32) / 255.0
    out = rgb * lum[..., None] + gc * gloss[..., None] * (0.55 + 0.45 * ridge[..., None]) + gc * opts['rachis'] * shaft[..., None]
    out = np.clip(out, 0, 1)

    # alpha: smooth the stock texel steps, narrow the ramp, fray the vane margins along the barbs
    a_s = ndimage.gaussian_filter(a_up, opts['smooth'])
    e0, e1 = opts['edge']
    margin = feather * _smoothstep(0.7, 1.0, rel)
    shift = opts['fray'] * margin * (0.5 - ridge) * 2
    alpha = _smoothstep(e0 + shift, e1 + shift, a_s)
    # thin parts (loose barbs at the quill, down) keep the stock's soft coverage instead of vanishing
    alpha = np.maximum(alpha, 0.9 * np.clip(a_up, 0, 1) * (1 - margin))
    # keep fine soft parts (down, strands) as soft as the stock had them
    alpha = np.where(down, np.maximum(alpha * 0.85, np.clip(a_up, 0, 1) * 0.9), alpha)
    out = _fill_transparent(out, alpha)
    rgba = np.dstack([out, alpha])
    result = Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), 'RGBA')
    report = {'input': [W, H], 'output': [ow, oh], 'cards': len(cards), 'downPieces': int(len(np.unique(np.asarray(kind == 2)))),
              'options': {k: v for k, v in opts.items()}}
    return result, report


def _texconv():
    for path in (os.environ.get('AAMT_TEXCONV'), r'D:\decompilers\DirectXTex\texconv.exe', shutil.which('texconv')):
        if path and os.path.isfile(path):
            return path
    return None


def _dds_levels(data, width, height):
    """Mip levels (bytes) of a BC3 DDS file written by texconv."""
    if data[:4] != b'DDS ':
        raise ValueError('not a DDS file')
    mips = struct.unpack_from('<I', data, 28)[0] or 1
    fourcc = data[84:88]
    offset = 128 + (20 if fourcc == b'DX10' else 0)
    if fourcc == b'DX10':
        dxgi = struct.unpack_from('<I', data, 128)[0]
        if dxgi not in (77, 78):        # BC3_UNORM, BC3_UNORM_SRGB
            raise ValueError(f'DDS is DXGI format {dxgi}, not BC3')
    elif fourcc != b'DXT5':
        raise ValueError(f'DDS is {fourcc!r}, not BC3')
    out = []
    w, h = width, height
    for _ in range(mips):
        size = max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * 16
        out.append(data[offset:offset + size])
        if len(out[-1]) != size:
            raise ValueError('DDS is shorter than its mip chain')
        offset += size
        w, h = max(1, w // 2), max(1, h // 2)
    return out


def _texture_bytes(levels, width, height, srgb=True):
    """The header HdTexture.from_image_bc3 writes (the game's character texture layout)."""
    count = len(levels)
    head = HdTexture.MAGIC + bytes([0x3E if srgb else 0x3D, 0x00, 0x02, count]) + struct.pack('<IIIIII', width, height, 1, 0, 0, count) + struct.pack('<I', 4)
    table_at = len(head)
    data_at = table_at + 8 * count
    table = b''
    for k, pixels in enumerate(levels):
        offset_field = table_at + 8 * k + 4
        table += struct.pack('<II', len(pixels), data_at - offset_field)
        data_at += len(pixels)
    return head + table + b''.join(levels)


def encode_bc3(img, srgb=True, coverage=0.5):
    """Pillow RGBA (power-of-two sides) -> .texture bytes, BC3, full mip chain. Returns (bytes, encoder)."""
    exe = _texconv()
    if exe is None:
        return HdTexture.from_image_bc3(img, srgb=srgb), 'pillow'
    w, h = img.size
    with tempfile.TemporaryDirectory() as work:
        src = os.path.join(work, 'albedo.png')
        img.convert('RGBA').save(src)
        cmd = [exe, '-nologo', '-y', '-f', 'BC3_UNORM_SRGB' if srgb else 'BC3_UNORM', '-m', '0', '-sepalpha', '-o', work]
        if srgb:
            cmd += ['-srgb']
        if coverage:
            cmd += ['--keep-coverage', str(coverage)]
        proc = subprocess.run(cmd + [src], capture_output=True, text=True)
        dds = os.path.join(work, 'albedo.dds')
        if proc.returncode != 0 or not os.path.isfile(dds):
            raise RuntimeError(f'texconv failed: {(proc.stderr or proc.stdout)[-400:]}')
        with open(dds, 'rb') as f:
            levels = _dds_levels(f.read(), w, h)
    return _texture_bytes(levels, w, h, srgb), 'texconv'


def check_texture(data, expect_size=None):
    """Reads a .texture back: header, mip table, every level decoded. Returns a short report."""
    from PIL import Image
    h = HdTexture.header(data)
    report = {'format': '0x%02X' % h['format'], 'width': h['width'], 'height': h['height'], 'mips': h['mips']}
    w, ht = h['width'], h['height']
    end = 0
    for k in range(h['mips']):
        size, rel = struct.unpack_from('<II', data, 36 + 8 * k)
        offset = 36 + 8 * k + 4 + rel
        want = max(1, (w + 3) // 4) * max(1, (ht + 3) // 4) * 16
        if size != want:
            raise ValueError(f'mip {k}: {size} bytes, {want} expected')
        end = max(end, offset + size)
        w, ht = max(1, w // 2), max(1, ht // 2)
    if end != len(data):
        raise ValueError(f'file is {len(data)} bytes, mips end at {end}')
    if w != 1 or ht != 1:
        pass
    report['lastMip'] = [w, ht]
    report['bytes'] = len(data)
    img = HdTexture.to_image(data)
    if expect_size and img.size != tuple(expect_size):
        raise ValueError(f'decoded {img.size}, expected {expect_size}')
    return report, img


def main():
    args = sys.argv[1:]
    if len(args) < 3 or args[0] != 'feathers':
        print(__doc__)
        return 2
    from PIL import Image
    source, target = args[1], args[2]
    options = {}
    if '--options' in args:
        options = json.loads(args[args.index('--options') + 1])
    if source.endswith('.texture'):
        with open(source, 'rb') as f:
            img = HdTexture.to_image(f.read())
    else:
        img = Image.open(source)
    result, report = feathers(img, options)
    if '--png' in args:
        result.save(args[args.index('--png') + 1])
    data, encoder = encode_bc3(result)
    with open(target, 'wb') as f:
        f.write(data)
    check, _ = check_texture(data, result.size)
    print(json.dumps({'encoder': encoder, 'texture': check, 'cards': report['cards']}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
