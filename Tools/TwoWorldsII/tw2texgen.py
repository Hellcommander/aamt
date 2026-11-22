"""Two Worlds II texture regeneration with SD3.5: the game's texture in, an original texture of our own out, laid out
on the same UVs and packed the way the game reads it, in a tw2patch patch folder (files\\<original path>).

Why img2img: most of the game's textures are unwrapped atlases (a sword's blade, guard and grip side by side, see
`tw2mesh.py uvmap`). A new texture must keep every island where the mesh's UVs expect it, so the stock texture is
the layout reference and SD repaints its surface (strength 0.3-0.6). Tiling surfaces (walls, ground, bark) can go
higher with --tile, which also makes the edges wrap.

Per texture, in Output\\texgen\\<NAME>\\ (kept, so a result can be refined and rebuilt):
  original.png, original_normal.png, original_spec.png   the stock maps (tw2tex export)
  sd_raw.png                                             what SD returned
  base.png, normal.png                                   the finished maps (edit these and run `build` again)
  compare.png                                            stock | new, side by side
  recipe.json                                            prompt, seed, strength, size: enough to redo it
and the DDS files in the patch folder (default Output\\patch, a tw2patch patch with mod.json).

Steps after SD: resize to the target size, colour matched to the stock texture (--match, 0..1), alpha taken from
the stock texture (cut-outs and reflection masks stay as they were), --tile seams wrapped. The normal map is the
stock one (--normal keep, default: same UVs, so it still fits), or rebuilt from the new base colour's detail over
the stock normal's shape (--normal derive), or left alone (--normal none). The AG specular stays the stock one.

usage:
  python tw2texgen.py gen REF... [--prompt TEXT] [--strength 0.45] [--scale 2] [--seed N] [--tile]
                                 [--normal keep|derive|none] [--match 0.6] [--patch DIR] [--no-sd] [--preview]
  python tw2texgen.py mesh MESHREF [same options]   every base texture a mesh uses
  python tw2texgen.py build NAME [--patch DIR]      re-pack Output\\texgen\\NAME\\base.png/normal.png after hand edits
REF: a base-colour texture, by game path or bare name (WP_SWORD_109.dds). --scale 2 doubles the resolution (capped at
2048, the game's largest). --no-sd skips SD (upscaled stock texture) to test the rest of the chain. --preview also
renders the meshes using the texture with the new maps (Shared\\mesh_edit.py preview).
SD runs through Tools\\Shared\\sd_http_client.py (port 1338, starts the server when needed, takes the GPU lock).
"""
import argparse
import json
import os
import random
import re
import sys

import numpy as np
from PIL import Image, ImageFilter

import tw2common as C
import tw2tex as T

STYLE = ('hand-painted game texture, Two Worlds II dark-fantasy style, realistic painterly materials, '
         'muted earthy palette, fine surface detail, worn and weathered, evenly lit, flat albedo, no shadows')
NEGATIVE = ('text, letters, watermark, signature, logo, frame, border, perspective, 3d render, photo of an object, '
            'person, face, cast shadows, strong lighting, blurry, lowres, jpeg artifacts, oversaturated, neon')

# words in texture or mesh paths -> what the surface is (for the prompt)
HINTS = [
    (r'SWORD|SABER|KATANA|BLADE|AXE|DAGGER|MACE|HAMMER|POLEARM|SPEAR|HALBERD', 'forged steel weapon parts: blade, guard, grip wrapped in leather'),
    (r'STAFF|WAND', 'carved wooden magic staff with metal fittings'),
    (r'BOW|CROSSBOW|QUIVER|ARROW', 'bent wood and sinew, leather and fletching'),
    (r'SHIELD|BUCKLER', 'shield of wood planks and iron rim'),
    (r'ROBE|CLOTH|TROUSERS|HOOD|CLOAK|MAG', 'woven fabric garment with stitched seams and trim'),
    (r'PLATE|ARMOR|ARMOUR|AR_|HELM|GAUNTLET|BOOTS', 'armour of hammered metal plates, leather straps and rivets'),
    (r'LEATHER', 'tanned leather with stitching'),
    (r'WOOD|PLANK|TRUNK|BARK|TREE|BEAM', 'aged wood grain'),
    (r'STONE|ROCK|WALL|BRICK|CASTLE|CATACOMB|CRYPT|CONCRET|FLOOR', 'old stone masonry'),
    (r'ROOF|THATCH', 'roof tiles and thatch'),
    (r'GRASS|TERRAIN|GROUND|DIRT|SAND|MUD', 'natural ground surface'),
    (r'METAL|IRON|RUST|CHAIN', 'old iron and steel'),
    (r'GOLD|JEWEL|RING|AMULET', 'gold and gemstones'),
    (r'POTION|BOTTLE|GLASS', 'glass and cork'),
    (r'SKIN|BODY|HEAD|FACE|ORC|ZOMBIE|MONSTER|CREATURE', 'creature skin and hide'),
]


def describe(name, users):
    text = ' '.join([name] + [u[3] for u in users[:10]]).upper()
    for pat, hint in HINTS:
        if re.search(pat, text):
            return hint
    return 'fantasy game surface'


def is_tiling(name, users):
    text = ' '.join([name] + [u[3] for u in users[:10]]).upper()
    return bool(re.search(r'TERRAIN|GRASS|ROAD|WALL|FLOOR|STONE|ROCK|BARK|ROOF|BRICK|PLANK|GROUND|TILE', text)) and \
        not re.search(r'EQ\\|EQUIPMENT|WP_|AR_|ROBE|CHARACTER', text)


# ---------------------------------------------------------------------------------------------- image steps
def match_colour(img, ref, amount):
    """Move img's per-channel mean/std towards ref's (keeps the game's palette)."""
    if amount <= 0:
        return img
    a = np.asarray(img.convert('RGB'), np.float32)
    r = np.asarray(ref.convert('RGB').resize(img.size), np.float32)
    am, asd = a.reshape(-1, 3).mean(0), a.reshape(-1, 3).std(0) + 1e-3
    rm, rsd = r.reshape(-1, 3).mean(0), r.reshape(-1, 3).std(0) + 1e-3
    t = (a - am) / asd * rsd + rm
    out = a + (t - a) * amount
    return Image.fromarray(np.clip(out, 0, 255).astype('uint8'), 'RGB')


def make_tileable(img, band=0.25):
    """Blend with a half-offset copy so the edges wrap (the seam moves to a feathered cross in the middle)."""
    a = np.asarray(img, np.float32)
    h, w = a.shape[:2]
    rolled = np.roll(np.roll(a, h // 2, 0), w // 2, 1)

    def ramp(n):
        x = np.minimum(np.arange(n), np.arange(n)[::-1]).astype(np.float32) / (n * band)
        return np.clip(x, 0, 1)
    m = np.minimum.outer(ramp(h), ramp(w))[..., None]
    return Image.fromarray(np.clip(a * m + rolled * (1 - m), 0, 255).astype('uint8'), img.mode)


def derive_normal(base, stock_normal, strength=2.5, mix=0.5):
    """Detail normal from the new base colour's luminance, laid over the stock normal (both standard RGB)."""
    g = np.asarray(base.convert('L').filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255.0
    dx = (np.roll(g, -1, 1) - np.roll(g, 1, 1)) * strength
    dy = (np.roll(g, -1, 0) - np.roll(g, 1, 0)) * strength
    det = np.stack([-dx, dy, np.ones_like(g)], -1)          # +Y up: bright = raised
    det /= np.linalg.norm(det, axis=-1, keepdims=True)
    if stock_normal is not None:
        s = np.asarray(stock_normal.convert('RGB').resize(base.size, Image.LANCZOS), np.float32) / 127.5 - 1
        s /= np.maximum(np.linalg.norm(s, axis=-1, keepdims=True), 1e-6)
        # whiteout blend: stock shape + new detail
        n = np.stack([s[..., 0] + det[..., 0] * mix, s[..., 1] + det[..., 1] * mix, s[..., 2] * det[..., 2]], -1)
    else:
        n = det
    n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-6)
    return Image.fromarray(((n * 0.5 + 0.5) * 255 + 0.5).astype('uint8'), 'RGB')


def sd_generate(prompt, ref_png, out_png, size, strength, seed):
    sys.path.insert(0, C.SHARED)
    from sd_http_client import generate_image, plan_sd_size
    gw, gh, steps = plan_sd_size(size[0], size[1])
    gw, gh = min(gw, 1536), min(gh, 1536)
    generate_image(prompt, __import__('pathlib').Path(out_png), negative_prompt=NEGATIVE, width=gw, height=gh,
                   steps=max(steps, 30), guidance_scale=6.0, seed=seed, reference_image=ref_png,
                   image_strength=strength)
    return Image.open(out_png).convert('RGB')


# ---------------------------------------------------------------------------------------------- pipeline
def normal_ref_for(fs, base_path, users):
    """The normal map that goes with a base texture: TexS1 of the materials that use it, else NAME_BUMP/_NORMAL."""
    names = [u for u in users if u[1] == 'TexS0']
    if os.path.isfile(T.INDEX) and names:
        key = set((n[3], n[5]) for n in names)
        with open(T.INDEX, encoding='utf-8') as f:
            next(f)
            for l in f:
                r = l.rstrip('\n').split('\t')
                if r[1] == 'TexS1' and (r[3], r[5]) in key:
                    p = fs.resolve(r[0])
                    if p:
                        return p
    stem = os.path.splitext(C.safe_name(base_path))[0]
    for suf in ('_BUMP', '_NORMAL', '_BDX1', '_NM', '_bump', '_normal'):
        p = fs.resolve(stem + suf + '.dds')
        if p:
            return p
    if stem.upper().endswith('_DIFFUSE'):
        p = fs.resolve(stem[:-8] + '_NORMAL.dds')
        if p:
            return p
    return None


def ensure_patch(patch):
    C.ensure_dir(os.path.join(patch, 'files'))
    mj = os.path.join(patch, 'mod.json')
    if not os.path.isfile(mj):
        json.dump({'id': os.path.basename(os.path.normpath(patch)), 'name': 'AI-regenerated textures (AAMT)',
                   'author': 'AAMT tw2texgen', 'version': '0.1.0',
                   'description': 'Textures regenerated with SD3.5 from the stock ones, same UV layout and format. '
                                  'Whole files under files\\, packed at their original paths.',
                   'enabled': False}, open(mj, 'w'), indent=1)


def pack(fs, work, patch, encoder='auto'):
    """Encode work\\base.png (+ normal.png) into the patch, in the stock textures' formats."""
    rec = json.load(open(os.path.join(work, 'recipe.json')))
    ensure_patch(patch)
    base = Image.open(os.path.join(work, 'base.png')).convert('RGBA')
    dsts = [T.import_one(fs, os.path.join(work, 'base.png'), rec['base'], patch, base.size, None, encoder)]
    npng = os.path.join(work, 'normal.png')
    if rec.get('normal_path') and os.path.isfile(npng) and rec.get('normal_mode') != 'none':
        nside = json.load(open(os.path.join(work, 'original_normal.json')))
        nsize = base.size if rec.get('normal_mode') == 'derive' else \
            (round(nside['width'] * rec['scale']), round(nside['height'] * rec['scale']))
        nsize = tuple(min(2048, v) for v in nsize)
        tmp = os.path.join(work, 'normal_for_import.png')
        Image.open(npng).save(tmp)
        json.dump({**nside, 'files': ['normal_for_import.png']},
                  open(os.path.join(work, 'normal_for_import.json'), 'w'), indent=1)
        sp = os.path.join(work, 'original_normal_spec.png')
        dsts.append(T.import_one(fs, tmp, nside['path'], patch, nsize, sp if os.path.isfile(sp) else None, encoder))
    return dsts


def regenerate(fs, ref, a):
    p = fs.resolve(ref)
    if not p:
        raise SystemExit('texture not found: %s' % ref)
    users = T.uses(p) if os.path.isfile(T.INDEX) else []
    name = os.path.splitext(C.safe_name(p))[0]
    work = C.ensure_dir(os.path.join(C.OUTPUT, 'texgen', name))
    side = T.export_one(fs, p, work + os.sep + '_x')
    for f in os.listdir(work + os.sep + '_x'):
        dst = f.replace(name, 'original', 1)
        os.replace(os.path.join(work, '_x', f), os.path.join(work, dst))
    os.rmdir(os.path.join(work, '_x'))
    if side['packing']:
        raise SystemExit('%s is a normal map; give the base-colour texture (its normal map follows it)' % p)
    stock = Image.open(os.path.join(work, 'original.png')).convert('RGBA')
    np_ = normal_ref_for(fs, p, users)
    if np_:
        nside = T.export_one(fs, np_, work + os.sep + '_n')
        nname = os.path.splitext(C.safe_name(np_))[0]
        for f in os.listdir(work + os.sep + '_n'):
            os.replace(os.path.join(work, '_n', f), os.path.join(work, f.replace(nname, 'original_normal', 1)))
        os.rmdir(os.path.join(work, '_n'))
    scale = a.scale
    tw, th = (min(2048, round(side['width'] * scale)), min(2048, round(side['height'] * scale)))
    scale = tw / side['width']
    tiling = a.tile or (a.tile is None and is_tiling(name, users))
    hint = describe(name, users)
    prompt = ', '.join(x for x in [a.prompt, hint, 'seamless tiling texture' if tiling else 'unwrapped texture atlas, same layout', STYLE] if x)
    seed = a.seed if a.seed is not None else random.randrange(1, 2 ** 31)
    ref_png = os.path.join(work, 'sd_ref.png')
    stock.convert('RGB').save(ref_png)
    print('%s: %dx%d -> %dx%d, %s, strength %.2f, seed %d%s' % (p, side['width'], side['height'], tw, th,
                                                                  hint, a.strength, seed, ', tiling' if tiling else ''))
    if a.no_sd:
        new = stock.convert('RGB').resize((tw, th), Image.LANCZOS)
        new.save(os.path.join(work, 'sd_raw.png'))
    else:
        new = sd_generate(prompt, ref_png, os.path.join(work, 'sd_raw.png'), (tw, th), a.strength, seed)
    new = new.resize((tw, th), Image.LANCZOS)
    new = match_colour(new, stock, a.match)
    if tiling:
        new = make_tileable(new)
    alpha = stock.getchannel('A').resize((tw, th), Image.LANCZOS)
    out = new.convert('RGBA')
    out.putalpha(alpha)
    out.save(os.path.join(work, 'base.png'))
    nmode = a.normal if np_ else 'none'
    if nmode != 'none':
        stock_n = Image.open(os.path.join(work, 'original_normal.png'))
        (derive_normal(new, stock_n) if nmode == 'derive' else stock_n).save(os.path.join(work, 'normal.png'))
    cw = 512
    sheet = Image.new('RGB', (cw * 2 + 8, cw), (20, 20, 20))
    sheet.paste(stock.convert('RGB').resize((cw, cw)), (0, 0))
    sheet.paste(out.convert('RGB').resize((cw, cw)), (cw + 8, 0))
    sheet.save(os.path.join(work, 'compare.png'))
    json.dump({'base': p, 'normal_path': np_, 'normal_mode': nmode, 'prompt': prompt, 'negative': NEGATIVE,
               'strength': a.strength, 'seed': seed, 'scale': scale, 'size': [tw, th], 'tiling': tiling,
               'match': a.match, 'sd': not a.no_sd},
              open(os.path.join(work, 'recipe.json'), 'w'), indent=1)
    dsts = pack(fs, work, a.patch, a.encoder)
    print('  work: %s\n  compare: %s' % (work, os.path.join(work, 'compare.png')))
    if a.preview:
        preview(fs, p, work, users)
    return dsts


def preview(fs, base_path, work, users):
    """Render the first mesh that uses the texture, with the new maps (mesh_edit.py four-view sheet)."""
    import subprocess
    import tw2mesh as M
    mesh = next((u[3] for u in users if u[1] == 'TexS0'), None)
    if not mesh:
        print('  preview: no mesh uses this texture (run tw2tex.py index first)')
        return
    _, meshes = M.load(fs, mesh)
    cache = {}
    with open(os.path.join(work, 'base.png'), 'rb') as f:
        cache[base_path] = f.read()
    rec = json.load(open(os.path.join(work, 'recipe.json')))
    if rec.get('normal_path') and os.path.isfile(os.path.join(work, 'normal.png')):
        b = __import__('io').BytesIO()
        Image.open(os.path.join(work, 'normal.png')).convert('RGB').save(b, 'PNG')
        cache[rec['normal_path']] = b.getvalue()
    mats, key_of, pairs = [], {}, []
    for m in meshes:
        mi = None
        if m.mat:
            key = (m.shader, tuple(sorted(m.textures().items())))
            if key not in key_of:
                slots, cut = M.material_images(fs, m, cache)
                mats.append((m.mat.str('Name') or 'material', slots, cut))
                key_of[key] = len(mats) - 1
            mi = key_of[key]
        pairs.append((m, mi))
    glb = os.path.join(work, 'preview.glb')
    M.write_glb(glb, pairs, mats)
    png = os.path.join(work, 'preview.png')
    r = subprocess.run([sys.executable, os.path.join(C.SHARED, 'mesh_edit.py'), 'preview', glb, png],
                       capture_output=True, text=True)
    print('  preview (%s): %s' % (mesh, png if r.returncode == 0 else (r.stderr.strip()[-300:] or 'failed')))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)

    def opts(s):
        s.add_argument('--prompt', default='')
        s.add_argument('--strength', type=float, default=0.45)
        s.add_argument('--scale', type=float, default=2.0)
        s.add_argument('--seed', type=int)
        s.add_argument('--tile', action='store_true', default=None)
        s.add_argument('--no-tile', dest='tile', action='store_false')
        s.add_argument('--normal', choices=['keep', 'derive', 'none'], default='keep')
        s.add_argument('--match', type=float, default=0.6)
        s.add_argument('--patch', default=os.path.join(C.OUTPUT, 'patch'))
        s.add_argument('--no-sd', action='store_true')
        s.add_argument('--preview', action='store_true')
        s.add_argument('--encoder', default='auto', choices=['auto', 'texconv', 'pillow'])
    s = sub.add_parser('gen'); s.add_argument('refs', nargs='+'); opts(s)
    s = sub.add_parser('mesh'); s.add_argument('mesh'); opts(s)
    s = sub.add_parser('build'); s.add_argument('name'); s.add_argument('--patch', default=os.path.join(C.OUTPUT, 'patch'))
    s.add_argument('--encoder', default='auto', choices=['auto', 'texconv', 'pillow'])
    argv = C.take_stock_flag(list(sys.argv[1:] if argv is None else argv))
    if not argv:
        print(__doc__); return 2
    a = ap.parse_args(argv)
    fs = C.GameFS()
    if a.cmd == 'build':
        for d in pack(fs, os.path.join(C.OUTPUT, 'texgen', a.name), a.patch, a.encoder):
            pass
        return 0
    refs = a.refs if a.cmd == 'gen' else []
    if a.cmd == 'mesh':
        import tw2mesh as M
        _, meshes = M.load(fs, a.mesh)
        refs = sorted({m.textures().get('TexS0') for m in meshes if m.textures().get('TexS0')})
        print('%s uses: %s' % (a.mesh, ', '.join(refs)))
    for r in refs:
        regenerate(fs, r, a)
    print('patch folder: %s  (copy it to <TW2>\\_modding\\patches\\ and enable it with tw2patch)' % a.patch)
    return 0


if __name__ == '__main__':
    sys.exit(main())
