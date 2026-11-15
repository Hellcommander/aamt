"""Make a 3D mesh of a legacy sprite monster with an AI image-to-3D model (TripoSR).

The sprite is decoded for one view direction (LegacySprite.py), enlarged and put
on the plain grey background the model was trained with, and TripoSR turns that
single picture into a mesh with vertex colours. The mesh is a rough reference:
its triangles, proportions and colours come from a neural network's guess at
the unseen sides. It is not a game model by itself (no skeleton, no UVs, no
LODs). SpriteFit.py uses its proportions as a second target when it fits the HD
donor's mesh to the sprite, and that fitted donor mesh is what becomes the model.

Third-party parts, none of them in this repository (see THIRD_PARTY.md):
  %LOCALAPPDATA%\\D2RModAssets\\thirdparty\\TripoSR      git clone of VAST-AI-Research/TripoSR (MIT)
  the model weights `stabilityai/TripoSR` (MIT), downloaded to the Hugging Face cache on first use (about 1.7 GB)
  pip: torch, omegaconf, einops, transformers, trimesh, scikit-image
TripoSR's two compiled extras are replaced by small stand-ins written here:
marching cubes (scikit-image instead of torchmcubes) and background removal
(not needed: the sprite already has transparency).

    python SpriteMeshAI.py make --game <D2R> --sprite s7 --out <folder> [--view 1] [--resolution 256]
      writes <folder>/input_view<N>.png (what the model saw), <folder>/ai_mesh.obj and a preview PNG

--view counts round the monster from facing south (0) in the sprite's directions;
a three-quarter view (1 or 7) shows the most.
"""
import argparse
import os
import sys
import types

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

THIRD_PARTY = os.environ.get('D2R_THIRDPARTY', os.path.join(os.environ.get('LOCALAPPDATA', ''), 'D2RModAssets', 'thirdparty'))


def _stand_ins():
    """Modules TripoSR imports but that need a compiler or are not needed here."""
    if 'torchmcubes' not in sys.modules:
        import torch
        from skimage import measure

        def marching_cubes(volume, threshold):
            verts, faces, _, _ = measure.marching_cubes(volume.detach().cpu().numpy(), float(threshold))
            # torchmcubes returns x, y, z with x along the last axis of the volume.
            return torch.from_numpy(np.ascontiguousarray(verts[:, ::-1])).float(), torch.from_numpy(faces.astype(np.int64))
        module = types.ModuleType('torchmcubes')
        module.marching_cubes = marching_cubes
        sys.modules['torchmcubes'] = module
    if 'rembg' not in sys.modules:
        try:
            import rembg  # noqa: F401
        except Exception:
            module = types.ModuleType('rembg')
            module.remove = lambda image, **kw: image
            module.new_session = lambda *a, **kw: None
            sys.modules['rembg'] = module


def prepare(image, size=512, fill=0.85, grey=127):
    """Sprite (RGBA) -> the square picture TripoSR expects: object centred on mid grey, filling most of the frame."""
    alpha = np.asarray(image)[:, :, 3]
    ys, xs = np.nonzero(alpha)
    image = image.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    scale = size * fill / max(image.size)
    image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.LANCZOS)
    canvas = Image.new('RGBA', (size, size), (grey, grey, grey, 255))
    canvas.alpha_composite(image, ((size - image.width) // 2, (size - image.height) // 2))
    return canvas.convert('RGB')


def generate(image, resolution=256, device=None):
    """A prepared RGB picture -> trimesh.Trimesh with vertex colours."""
    import torch
    _stand_ins()
    repo = os.path.join(THIRD_PARTY, 'TripoSR')
    if not os.path.isdir(repo):
        raise FileNotFoundError(f'TripoSR not found in {repo}; see THIRD_PARTY.md for how to fetch it')
    if repo not in sys.path:
        sys.path.insert(0, repo)
    from tsr.system import TSR
    device = device or ('cuda:0' if torch.cuda.is_available() else 'cpu')
    model = TSR.from_pretrained('stabilityai/TripoSR', config_name='config.yaml', weight_name='model.ckpt')
    model.renderer.set_chunk_size(8192)
    model.to(device)
    with torch.no_grad():
        codes = model([image], device=device)
        meshes = model.extract_mesh(codes, True, resolution=resolution)
    return meshes[0]


def preview(mesh, path, size=420):
    """Four stills of the mesh, coloured by its vertex colours' average."""
    import GrannyPreview
    verts = np.asarray(mesh.vertices, dtype=np.float64)
    tris = np.asarray(mesh.faces, dtype=np.int64)
    colour = (150, 130, 100)
    try:
        colour = tuple(int(v) for v in np.asarray(mesh.visual.vertex_colors)[:, :3].mean(0))
    except Exception:
        pass
    tiles = []
    for k, (yaw, pitch) in enumerate([(0, 10), (90, 10), (180, 10), (45, 35)]):
        tile = path.replace('.png', f'_{k}.png')
        GrannyPreview.draw([(verts, tris, colour)], tile, size=size, yaw=yaw, pitch=pitch, title=f'AI mesh yaw {yaw}')
        tiles.append(Image.open(tile))
    sheet = Image.new('RGB', (size * len(tiles), size))
    for k, tile in enumerate(tiles):
        sheet.paste(tile, (k * size, 0))
    sheet.save(path)
    for k in range(len(tiles)):
        os.remove(path.replace('.png', f'_{k}.png'))


def main(argv):
    parser = argparse.ArgumentParser(description='AI mesh of a legacy sprite monster.')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('make')
    p.add_argument('--game', default=os.environ.get('D2R_PATH'))
    p.add_argument('--sprite', required=True)
    p.add_argument('--mode', default='nu')
    p.add_argument('--view', type=int, default=1)
    p.add_argument('--resolution', type=int, default=256)
    p.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    import LegacySprite
    from d2r_casc import D2RArchive
    os.makedirs(args.out, exist_ok=True)
    with D2RArchive(args.game) as archive:
        dcc, palette = LegacySprite.load(archive, args.sprite, args.mode)
    order = LegacySprite.VIEW_ORDER.get(dcc.directions, list(range(dcc.directions)))
    sprite = LegacySprite.to_image(dcc.frames[order[args.view % len(order)]][0], palette)
    picture = prepare(sprite)
    picture.save(os.path.join(args.out, f'input_view{args.view}.png'))
    mesh = generate(picture, args.resolution)
    target = os.path.join(args.out, 'ai_mesh.obj')
    mesh.export(target)
    preview(mesh, os.path.join(args.out, 'ai_mesh.png'))
    extent = np.ptp(np.asarray(mesh.vertices), axis=0)
    print(f'{len(mesh.vertices)} vertices, {len(mesh.faces)} triangles, extent {np.round(extent, 3).tolist()} -> {target}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
