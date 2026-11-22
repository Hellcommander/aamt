"""Two Worlds II textures: find, export to PNG, import PNG back to the game's DDS layout, map texture -> meshes.

What the game uses (surveyed 2026-11-21 over 6,026 sampled DDS files in all archives; `survey` repeats it):
  - DXT1 53%, DXT5 42%, A8R8G8B8 3%, R8G8B8 / DXT3 / cube maps rare. Full mip chain (79%) or one level (21%).
  - Meshes (.vdf/.chv) name each material's textures by bare file name in slots TexS0..TexS4, read by the
    material's shader (ShaderName, an .efx compiled to Shaders\\*.efo, which keeps readable GLSL):
      TexS0  base colour. Alpha: unused by the opaque shaders; cut-out/blend for *_alpha, leafs, grass, blend,
             pointsprite; reflection mask for chrome*/mirror/cristal.
      TexS1  normal map, one of two packings (the shader decides; `detect_packing` reads it from the pixels):
               "AG"  (_BUMP, DXT5): normal X in alpha, Y in green, specular in red, blue 0.
                      Shaders metal, metal_char, lightmap*, chrome*, alien, fire, fur, mirror, post_glass ...
               "RGB" (_NORMAL, _BDX1 in DXT1): plain tangent-space normal, X Y Z in R G B.
                      Shaders metalcity (the most used), lightmapcity, paralax, metal_wind*.
             Both are +Y up (OpenGL style; checked against the paired base colours), Z rebuilt by the shader.
      TexS2  lightmap on UV set 2 (lightmap*), dye mask on UV set 2 (metal_char*: RGBA = 4 dye zones that tint
             the base colour), or a cube map (chrome).
      TexS3  extra colour (chrome*, metal_blend) or lightmap (lightmap2_3uv).
  - Texture names repeat across folders (1,570 of 12,985 sampled references): a replacement keeps the original's
    full path, so the copy the game loads is the one replaced.

usage:
  python tw2tex.py find PATTERN [--limit N]          textures whose path contains PATTERN (format, size, archive)
  python tw2tex.py info REF|FILE.dds                 header: format, size, mips, normal packing
  python tw2tex.py export REF... [--out DIR] [--raw]  DDS -> PNG + REF.json sidecar. Normal maps come out as a
                                                       standard RGB normal (+ NAME_spec.png for "AG"); --raw
                                                       keeps the channels as stored
  python tw2tex.py import IN.png [--like REF] [--out PATCH] [--size WxH] [--spec SPEC.png] [--encoder texconv|pillow]
                                                     PNG -> DDS in the original's format, packing and mip layout,
                                                     at PATCH\\files\\<original path> (a tw2patch patch folder);
                                                     --like defaults to the sidecar written by export
  python tw2tex.py index                             scan every mesh once: texture -> mesh/material/shader/slot
                                                     (Output\\cache\\texrefs.tsv, a few minutes)
  python tw2tex.py uses REF                          meshes and shaders that use a texture (needs index)
  python tw2tex.py survey [--per N]                  format statistics over a sample of every archive
REF is a game path (Textures\\X.dds) or a bare file name as meshes write it (X.dds).
Output defaults to Tools\\TwoWorldsII\\Output (gitignored). Read-only on the game.
"""
import argparse
import collections
import io
import json
import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

import tw2common as C

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    raise SystemExit('Pillow is needed (python -m pip install Pillow)')

# shader -> what each slot holds (from the GLSL in Shaders\*.efo; "_hs" variants share their base's layout)
NORMAL_AG = {'metal', 'metal_2uv', 'metal_alpha', 'metal_blend', 'metal_char', 'metal_char_alpha', 'metal_flag',
             'lightmap', 'lightmap_3uv', 'lightmap2_3uv', 'lightmap_3uvalpha', 'lightmap_alpha', 'chrome',
             'chrome_dest', 'newchrome', 'cristal', 'alien', 'fire', 'fur', 'mirror', 'post_glass', 'hair'}
NORMAL_RGB = {'metalcity', 'lightmapcity', 'paralax', 'metal_wind', 'metal_wind_a'}
ALPHA_CUT = {'metal_alpha', 'metal_char_alpha', 'lightmap_alpha', 'lightmap_3uvalpha', 'diffonly_alpha', 'blend',
             'metal_leafs', 'metal_grass', 'leafs_sss', 'pointsprite', 'pointsprite_polygon', 'metal_wind_a',
             'diffuse_hor', 'metal_flag', 'fur'}
ALPHA_REFLECT = {'chrome', 'chrome_dest', 'newchrome', 'mirror', 'cristal'}


def shader_base(name):
    s = (name or '').lower().rsplit('/', 1)[-1].rsplit('\\', 1)[-1]
    s = s[:-4] if s.endswith('.efx') else s
    return s[:-3] if s.endswith('_hs') else s


def slot_roles(shader):
    """{'TexS0': role, ...} for a shader name, from the table above."""
    s = shader_base(shader)
    r = {'TexS0': 'base' + (' (alpha: cut-out)' if s in ALPHA_CUT else
                            ' (alpha: reflection mask)' if s in ALPHA_REFLECT else '')}
    if s in NORMAL_AG:
        r['TexS1'] = 'normal AG (X=alpha Y=green, spec=red)'
    elif s in NORMAL_RGB:
        r['TexS1'] = 'normal RGB'
    elif s == 'hdrlight' or s.startswith('diffonly'):
        r['TexS1'] = 'unused'
    else:
        r['TexS1'] = 'normal (packing: see the texture)'
    if s.startswith('lightmap'):
        r['TexS2'] = 'lightmap (UV2)'
    elif s.startswith('metal_char'):
        r['TexS2'] = 'dye mask (UV2, RGBA = 4 dye zones)'
    elif s.startswith('chrome') or s == 'mirror':
        r['TexS2'] = 'reflection cube'
    if s.startswith('chrome') or s == 'metal_blend':
        r['TexS3'] = 'colour'
    elif s == 'lightmap2_3uv':
        r['TexS3'] = 'lightmap'
    return r


# ---------------------------------------------------------------------------------------------- DDS header
def dds_info(data):
    if data[:4] != b'DDS ':
        raise ValueError('not a DDS file')
    flags, h, w, pitch, depth, mips = struct.unpack_from('<6I', data, 8)
    pf_flags, fourcc, bits = struct.unpack_from('<I4sI', data, 80)
    masks = struct.unpack_from('<4I', data, 92)
    caps2 = struct.unpack_from('<I', data, 112)[0]
    if pf_flags & 4:
        fmt = fourcc.decode('latin-1')
    elif pf_flags & 0x20000:
        fmt = 'L%d' % bits
    else:
        fmt = ('A8R8G8B8' if bits == 32 and pf_flags & 1 else 'X8R8G8B8' if bits == 32 else
               'R8G8B8' if bits == 24 else 'A4R4G4B4' if bits == 16 and pf_flags & 1 else 'RGB%d' % bits)
    mips = max(1, mips)
    full = max(w, h).bit_length()
    return {'width': w, 'height': h, 'mips': mips, 'format': fmt, 'bits': bits, 'masks': masks,
            'cube': bool(caps2 & 0x200), 'mip_layout': 'full' if mips >= full else ('one' if mips == 1 else 'partial')}


def decode(data):
    """Top mip as an RGBA Pillow image (cube maps: the first face)."""
    img = Image.open(io.BytesIO(data))
    img.load()
    return img.convert('RGBA')


def read_ref(fs, ref):
    """REF (path, bare name, or a .dds on disk) -> (stored path or file path, bytes)."""
    if os.path.isfile(ref):
        return ref, open(ref, 'rb').read()
    p = fs.resolve(ref)
    if not p:
        raise SystemExit('not found in the game archives: %s' % ref)
    return p, fs.read(p)


# ---------------------------------------------------------------------------------------------- normal maps
def _stats(img):
    import numpy as np
    a = np.asarray(img, dtype=np.float32) / 255.0
    return a, a.reshape(-1, 4).mean(0), a.reshape(-1, 4).std(0)


def detect_packing(img, name=''):
    """'AG' (DXT5nm: X in alpha), 'RGB' (plain normal) or None (not a normal map), from the pixels and name."""
    _, mean, std = _stats(img)
    n = name.upper()
    looks_normal = any(t in n for t in ('_BUMP', '_NORMAL', '_NM', '_BDX', '_PAR', 'NORM'))
    if mean[2] < 0.05 and std[3] > 0.01 and abs(mean[3] - 0.5) < 0.2 and abs(mean[1] - 0.5) < 0.2:
        return 'AG'
    if mean[2] > 0.6 and abs(mean[0] - 0.5) < 0.15 and abs(mean[1] - 0.5) < 0.15 and (looks_normal or std[2] < 0.15):
        return 'RGB'
    return None


def unpack_normal(img, packing):
    """Stored normal map -> (standard RGB normal image, spec image or None)."""
    import numpy as np
    a, _, _ = _stats(img)
    if packing == 'AG':
        x, y, spec = a[..., 3] * 2 - 1, a[..., 1] * 2 - 1, a[..., 0]
    else:
        x, y, spec = a[..., 0] * 2 - 1, a[..., 1] * 2 - 1, None
    z = np.sqrt(np.clip(1 - x * x - y * y, 0, 1))
    rgb = np.stack([x, y, z], -1) * 0.5 + 0.5
    out = Image.fromarray((rgb * 255 + 0.5).astype('uint8'), 'RGB').convert('RGBA')
    sp = None if spec is None else Image.fromarray((spec * 255 + 0.5).astype('uint8'), 'L')
    return out, sp


def pack_normal(rgb_img, packing, spec=None):
    """Standard RGB normal image (+ optional spec) -> the game's stored layout (renormalised)."""
    import numpy as np
    a = np.asarray(rgb_img.convert('RGB'), dtype=np.float32) / 255.0 * 2 - 1
    ln = np.maximum(np.linalg.norm(a, axis=-1, keepdims=True), 1e-6)
    a = a / ln
    if packing == 'AG':
        s = (np.asarray(spec.convert('L').resize(rgb_img.size), dtype=np.float32) / 255.0 if spec is not None
             else np.full(a.shape[:2], 0.25, np.float32))
        out = np.stack([s, a[..., 1] * 0.5 + 0.5, np.zeros_like(s), a[..., 0] * 0.5 + 0.5], -1)
    else:
        out = np.concatenate([a * 0.5 + 0.5, np.ones(a.shape[:2] + (1,), np.float32)], -1)
    return Image.fromarray((out * 255 + 0.5).astype('uint8'), 'RGBA')


# ---------------------------------------------------------------------------------------------- DDS writing
TEXCONV_FMT = {'DXT1': 'BC1_UNORM', 'DXT3': 'BC2_UNORM', 'DXT5': 'BC3_UNORM', 'DXT2': 'BC2_UNORM'}


def _mip_count(info, w, h):
    full = max(w, h).bit_length()
    if info['mip_layout'] == 'full':
        return full
    if info['mip_layout'] == 'one':
        return 1
    return min(info['mips'], full)


def _mips(img, n):
    out = [img]
    for _ in range(n - 1):
        w, h = out[-1].size
        out.append(out[-1].resize((max(1, w // 2), max(1, h // 2)), Image.LANCZOS))
    return out


def _texconv():
    try:
        sys.path.insert(0, C.SHARED)
        import tool_paths
        p = tool_paths.texconv_exe()
        return str(p) if p else None
    except Exception:
        return shutil.which('texconv')


def _payload_texconv(img, fmt, mips):
    exe = _texconv()
    if not exe:
        return None
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, 'in.png')
        img.save(src)
        cmd = [exe, '-nologo', '-y', '-f', TEXCONV_FMT[fmt], '-m', str(mips), '-dx9', '-o', d, src]
        r = subprocess.run(cmd, capture_output=True, text=True)
        out = os.path.join(d, 'in.dds')
        if r.returncode or not os.path.isfile(out):
            print('texconv failed, using Pillow: %s' % (r.stdout + r.stderr).strip()[-300:], file=sys.stderr)
            return None
        data = open(out, 'rb').read()
    if data[84:88] == b'DX10':
        return None
    return data[128:]


def _payload_pillow(img, fmt, mips):
    pf = {'DXT2': 'DXT3'}.get(fmt, fmt)
    out = bytearray()
    for level in _mips(img, mips):
        b = io.BytesIO()
        (level if fmt != 'DXT1' else level.convert('RGBA')).save(b, 'DDS', pixel_format=pf)
        out += b.getvalue()[128:]
    return bytes(out)


def _payload_raw(img, info, mips):
    """Uncompressed: pack every mip with the original's channel masks."""
    import numpy as np
    bits, masks = info['bits'], info['masks']
    out = bytearray()
    for level in _mips(img, mips):
        a = np.asarray(level, dtype=np.uint32)
        px = np.zeros(a.shape[:2], np.uint32)
        for ch, m in enumerate(masks):
            if not m:
                continue
            shift = (m & -m).bit_length() - 1
            width = bin(m).count('1')
            px |= ((a[..., ch] * ((1 << width) - 1) + 127) // 255) << shift
        if bits == 32:
            out += px.astype('<u4').tobytes()
        elif bits == 24:
            out += px.astype('<u4').view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
        elif bits == 16:
            out += px.astype('<u2').tobytes()
        elif bits == 8:
            out += px.astype(np.uint8).tobytes()
        else:
            raise ValueError('cannot write %d-bit uncompressed DDS' % bits)
    return bytes(out)


def encode_like(img, original, size=None, encoder='auto'):
    """RGBA image -> DDS bytes laid out like `original` (format, header, mip layout). size=(w, h) to resize."""
    info = dds_info(original)
    if info['cube']:
        raise SystemExit('cube maps are not supported for import')
    w, h = size or img.size
    if (w, h) != img.size:
        img = img.resize((w, h), Image.LANCZOS)
    for v in (w, h):
        if v & (v - 1):
            print('warning: %d is not a power of two; the game\'s own textures always are' % v, file=sys.stderr)
    mips = _mip_count(info, w, h)
    fmt = info['format']
    if fmt in TEXCONV_FMT:
        payload = None if encoder == 'pillow' else _payload_texconv(img, fmt, mips)
        if payload is None:
            if encoder == 'texconv':
                raise SystemExit('texconv not found or failed (set AAMT_TEXCONV)')
            payload = _payload_pillow(img, fmt, mips)
        linear = max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * (8 if fmt == 'DXT1' else 16)
    else:
        payload = _payload_raw(img, info, mips)
        linear = w * info['bits'] // 8
    head = bytearray(original[:128])
    flags = struct.unpack_from('<I', head, 8)[0] | 0x1007
    flags = (flags | 0x20000) if mips > 1 else (flags & ~0x20000)
    flags = (flags | 0x80000) & ~0x8 if fmt in TEXCONV_FMT else (flags | 0x8) & ~0x80000
    caps = struct.unpack_from('<I', head, 108)[0] | 0x1000
    caps = (caps | 0x400008) if mips > 1 else (caps & ~0x400008)
    struct.pack_into('<6I', head, 8, flags, h, w, linear, 0, mips)
    struct.pack_into('<I', head, 108, caps)
    return bytes(head) + payload


# ---------------------------------------------------------------------------------------------- texture index
INDEX = os.path.join(C.CACHE, 'texrefs.tsv')


def material_rows(tree_nodes):
    """(mesh name, material name, shader, slot, texture) for every material in a mesh tree."""
    out = []

    def walk(n, mesh):
        for c in n.children:
            if c.kind != 2:
                continue
            m = c.str('Name') if c.get('Vertexes') is not None else mesh
            if c.get('ShaderName') is not None:
                for k in c.children:
                    if k.kind == 1 and k.name.startswith('TexS'):
                        out.append((m or '', c.str('Name') or '', c.str('ShaderName'), k.name,
                                    k.value.decode('latin-1')))
            walk(c, m)
    walk(tree_nodes[0], None)
    return out


def build_index(fs):
    C.ensure_dir(C.CACHE)
    meshes = fs.glob('.VDF', '.CHV')
    n = 0
    with open(INDEX + '.tmp', 'w', encoding='utf-8') as o:
        o.write('texture\tslot\tshader\tmesh_file\tmesh\tmaterial\n')
        for i, p in enumerate(meshes):
            if i % 1000 == 0:
                print('  %d / %d meshes' % (i, len(meshes)), file=sys.stderr)
            try:
                rows = material_rows(C.tree(fs.read(p)))
            except Exception as exc:
                print('  skip %s: %s' % (p, exc), file=sys.stderr)
                continue
            for mesh, mat, sh, slot, tex in rows:
                o.write('%s\t%s\t%s\t%s\t%s\t%s\n' % (tex.replace('/', '\\').rsplit('\\', 1)[-1].upper(), slot,
                                                      sh, p, mesh, mat))
                n += 1
    os.replace(INDEX + '.tmp', INDEX)
    print('%d texture references from %d meshes -> %s' % (n, len(meshes), INDEX))


def uses(name):
    if not os.path.isfile(INDEX):
        raise SystemExit('no index yet: run  python tw2tex.py index')
    key = name.replace('/', '\\').rsplit('\\', 1)[-1].upper()
    if not key.endswith('.DDS'):
        key += '.DDS'
    with open(INDEX, encoding='utf-8') as f:
        next(f)
        return [l.rstrip('\n').split('\t') for l in f if l.split('\t', 1)[0] == key]


def packing_for(name, img):
    """Packing of a texture: its users' shaders when indexed, else the pixels."""
    if os.path.isfile(INDEX):
        sh = collections.Counter(shader_base(r[2]) for r in uses(name) if r[1] == 'TexS1')
        if sh:
            ag = sum(v for k, v in sh.items() if k in NORMAL_AG)
            rgb = sum(v for k, v in sh.items() if k in NORMAL_RGB)
            if ag or rgb:
                return 'AG' if ag >= rgb else 'RGB'
    return detect_packing(img, name)


# ---------------------------------------------------------------------------------------------- commands
def head_bytes(fs, p, n=128):
    arc, e = fs.files[p.upper()]
    name, flags, off, psize, size, extra = e
    if flags & 8:
        return fs.read(p)[:n]
    h = fs._h(arc)
    h.seek(off)
    raw = h.read(min(psize, 4096))
    return zlib.decompressobj().decompress(raw)[:n] if flags & 1 else raw[:n]


def cmd_find(fs, a):
    hits = [p for p in fs.glob('.DDS', contains=a.pattern)]
    for p in hits[:a.limit]:
        try:
            i = dds_info(head_bytes(fs, p))
            desc = '%-8s %5dx%-5d mips %-2d%s' % (i['format'], i['width'], i['height'], i['mips'],
                                                ' cube' if i['cube'] else '')
        except Exception as exc:
            desc = 'unreadable: %s' % exc
        print('%-34s %-22s %s' % (desc, fs.where(p), p))
    if len(hits) > a.limit:
        print('... %d more (--limit)' % (len(hits) - a.limit))


def cmd_info(fs, a):
    p, data = read_ref(fs, a.ref)
    i = dds_info(data)
    img = decode(data)
    print(p)
    if not os.path.isfile(a.ref):
        print('archive: %s (%d copies)' % (fs.where(p), fs.copies[p.upper()]))
    print('format %s  %dx%d  mips %d (%s)%s' % (i['format'], i['width'], i['height'], i['mips'], i['mip_layout'],
                                               '  cube' if i['cube'] else ''))
    print('normal packing: %s' % (packing_for(os.path.basename(p), img) or 'not a normal map'))


def export_one(fs, ref, out, raw=False):
    p, data = read_ref(fs, ref)
    info = dds_info(data)
    img = decode(data)
    base = os.path.splitext(C.safe_name(p))[0]
    C.ensure_dir(out)
    packing = None if raw else packing_for(C.safe_name(p), img)
    files = []
    if packing:
        nrm, spec = unpack_normal(img, packing)
        nrm.convert('RGB').save(os.path.join(out, base + '.png'))
        files.append(base + '.png')
        if spec is not None:
            spec.save(os.path.join(out, base + '_spec.png'))
            files.append(base + '_spec.png')
    else:
        (img if info['format'] not in ('DXT1', 'R8G8B8', 'X8R8G8B8') else img.convert('RGB')).save(
            os.path.join(out, base + '.png'))
        files.append(base + '.png')
    side = {'path': p, 'archive': None if os.path.isfile(ref) else fs.where(p), 'format': info['format'],
            'width': info['width'], 'height': info['height'], 'mips': info['mips'],
            'mip_layout': info['mip_layout'], 'packing': packing, 'raw': raw, 'files': files}
    with open(os.path.join(out, base + '.json'), 'w') as f:
        json.dump(side, f, indent=1)
    open(os.path.join(out, base + '.orig.dds'), 'wb').write(data)
    return side


def cmd_export(fs, a):
    out = a.out or os.path.join(C.OUTPUT, 'textures')
    for ref in a.refs:
        s = export_one(fs, ref, out, a.raw)
        print('%s -> %s  (%s %dx%d%s)' % (s['path'], ', '.join(os.path.join(out, f) for f in s['files']),
                                         s['format'], s['width'], s['height'],
                                         ', normal ' + s['packing'] if s['packing'] else ''))


def import_one(fs, png, like=None, out=None, size=None, spec=None, encoder='auto'):
    side = {}
    sj = os.path.splitext(png)[0] + '.json'
    if os.path.isfile(sj):
        side = json.load(open(sj))
    like = like or side.get('path')
    if not like:
        raise SystemExit('%s: no sidecar .json; give --like REF' % png)
    orig_dds = os.path.splitext(png)[0] + '.orig.dds'
    p, original = (side['path'], open(orig_dds, 'rb').read()) if side and os.path.isfile(orig_dds) and \
        like == side.get('path') else read_ref(fs, like)
    img = Image.open(png).convert('RGBA')
    packing = side.get('packing') if side.get('path') == p else None
    if packing is None and not side.get('raw'):
        packing = packing_for(C.safe_name(p), decode(original))
    if packing:
        sp = spec or (os.path.splitext(png)[0] + '_spec.png')
        img = pack_normal(img, packing, Image.open(sp) if os.path.isfile(sp) else None)
    data = encode_like(img, original, size, encoder)
    out = out or os.path.join(C.OUTPUT, 'patch')
    dst = os.path.join(out, 'files', *p.replace('/', '\\').split('\\'))
    C.ensure_dir(os.path.dirname(dst))
    open(dst, 'wb').write(data)
    i = dds_info(data)
    print('%s -> %s  (%s %dx%d mips %d%s)' % (png, dst, i['format'], i['width'], i['height'], i['mips'],
                                             ', normal ' + packing if packing else ''))
    return dst


def cmd_import(fs, a):
    size = tuple(int(v) for v in a.size.lower().split('x')) if a.size else None
    import_one(fs, a.png, a.like, a.out, size, a.spec, a.encoder)


def cmd_uses(fs, a):
    rows = uses(a.ref)
    if not rows:
        print('no mesh references %s' % a.ref)
    by = collections.Counter((r[1], shader_base(r[2])) for r in rows)
    for (slot, sh), n in sorted(by.items()):
        print('%-6s %-20s %5d  %s' % (slot, sh, n, slot_roles(sh).get(slot, '?')))
    for r in rows[:40]:
        print('  %s  [%s / %s]' % (r[3], r[4], r[5]))
    if len(rows) > 40:
        print('  ... %d more' % (len(rows) - 40))


def cmd_survey(fs, a):
    random.seed(1)
    fmts, layouts, sizes = collections.Counter(), collections.Counter(), collections.Counter()
    by_arc = collections.defaultdict(list)
    for p in fs.glob('.DDS'):
        by_arc[fs.where(p)].append(p)
    n = 0
    for arc, ps in sorted(by_arc.items()):
        for p in random.sample(ps, min(a.per, len(ps))):
            try:
                i = dds_info(head_bytes(fs, p))
            except Exception:
                fmts['unreadable'] += 1
                continue
            fmts[i['format'] + (' cube' if i['cube'] else '')] += 1
            layouts[i['mip_layout']] += 1
            sizes['%dx%d' % (i['width'], i['height'])] += 1
            n += 1
    print('%d textures sampled (%d per archive) of %d' % (n, a.per, len(fs.glob('.DDS'))))
    print('formats:', ', '.join('%s %d' % kv for kv in fmts.most_common()))
    print('mips:   ', ', '.join('%s %d' % kv for kv in layouts.most_common()))
    print('sizes:  ', ', '.join('%s %d' % kv for kv in sizes.most_common(12)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('find'); s.add_argument('pattern'); s.add_argument('--limit', type=int, default=60)
    s = sub.add_parser('info'); s.add_argument('ref')
    s = sub.add_parser('export'); s.add_argument('refs', nargs='+'); s.add_argument('--out'); s.add_argument('--raw', action='store_true')
    s = sub.add_parser('import'); s.add_argument('png'); s.add_argument('--like'); s.add_argument('--out')
    s.add_argument('--size'); s.add_argument('--spec'); s.add_argument('--encoder', default='auto',
                                                                         choices=['auto', 'texconv', 'pillow'])
    sub.add_parser('index')
    s = sub.add_parser('uses'); s.add_argument('ref')
    s = sub.add_parser('survey'); s.add_argument('--per', type=int, default=300)
    argv = C.take_stock_flag(list(sys.argv[1:] if argv is None else argv))
    if not argv:
        print(__doc__); return 2
    a = ap.parse_args(argv)
    fs = C.GameFS()
    {'find': cmd_find, 'info': cmd_info, 'export': cmd_export, 'import': cmd_import,
     'index': lambda fs, a: build_index(fs), 'uses': cmd_uses, 'survey': cmd_survey}[a.cmd](fs, a)
    return 0


if __name__ == '__main__':
    sys.exit(main())
