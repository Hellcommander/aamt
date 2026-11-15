"""Fit an HD monster's mesh to a legacy sprite monster, as seen from the sprite's view directions.

A sprite monster with no HD model (the Quill Bear / Spike Giant, token s7) often
has an HD relative that looks much like it (the Spike Fiend). This tool takes
the relative's HD mesh as the template and finds the body-part proportions that
make its outline match the sprite's in all eight directions at once:

  1. The sprite's neutral frame is decoded for every direction (LegacySprite.py).
     Its transparent/opaque mask is the target outline; the sprite's own origin
     says where the feet are.
  2. The template is posed with its own neutral clip (GrannyAnim.py) and drawn
     as a flat silhouette from the same directions with an orthographic camera
     looking down at the game's angle.
  3. The shape is described by a few numbers per body part (how long, tall and
     wide the torso, head, tail, fore and hind legs are, and how long and thick
     the quills are). An optimiser changes them until the eight outlines overlap
     the sprite's as well as they can (intersection over union).
  4. Optionally an AI image-to-3D model's mesh of the sprite (see SpriteMeshAI.py)
     is used as a second target: its proportions in depth, which a flat outline
     only shows indirectly.

The result is a `"reshape"` block for a ScaledMonster preset plus the root scale,
so the pipeline writes the model: same triangles, skin weights, UVs and LODs as
the template, which is what makes it a valid, animated model.

    python SpriteFit.py fit --game <D2R> --sprite s7 --donor quillrat1 --donor-sprite si
                            --out <folder> [--ai-mesh <mesh.obj>] [--iterations 3]
      writes <folder>/fit.json (the reshape block, scale, score per view) and
      <folder>/fit.png (sprite, template before, template after, for each view)
"""
import argparse
import json
import math
import os
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import GrannyAnim  # noqa: E402
import GrannyMesh  # noqa: E402
import GrannyPreview  # noqa: E402
import LegacySprite  # noqa: E402

# Body parts of the quill rat family's skeleton. A preset can pass its own.
DEFAULT_PARTS = [
    {'name': 'torso', 'bones': ['spine_', 'pelvis']},
    {'name': 'head', 'bones': ['head', 'neck', 'jaw', 'L_nostril', 'R_nostril', 'L_lip', 'R_lip', 'L_cheek', 'R_cheek', 'L_ear', 'R_ear']},
    {'name': 'tail', 'bones': ['tail_', 'R_tailSpkie', 'L_tailSpkie']},
    {'name': 'forelegs', 'bones': ['R_shoulder', 'L_shoulder', 'R_upr_arm', 'L_upr_arm', 'R_lwr_arm', 'L_lwr_arm', 'R_hand', 'L_hand',
                                   'R_mid_', 'L_mid_', 'R_ind_', 'L_ind_', 'R_rng_', 'L_rng_', 'R_tmb_', 'L_tmb_']},
    {'name': 'hindlegs', 'bones': ['R_leg_', 'L_leg_']},
]
DEFAULT_QUILLS = [
    {'name': 'back quills', 'prefix': 'spike_', 'first': 20, 'last': 62},
    {'name': 'neck quills', 'prefix': 'spike_', 'first': 1, 'last': 19},
]
LOW, HIGH = 0.55, 2.2


class Template:
    """The donor's mesh, bones and neutral pose, ready to be deformed and drawn."""

    def __init__(self, model_path, animations, clip='neutral', time=0.0):
        mesh = GrannyMesh.Model(model_path).meshes[0]
        self.positions = mesh.positions()
        self.weights, self.indices = mesh.weights()
        self.names = mesh.bones
        self.triangles = GrannyPreview.load_meshes(model_path)[0][2]
        self.skeleton = GrannyAnim.Skeleton(model_path)
        self.bones, _ = GrannyPreview.load_bones(model_path)
        pose = GrannyAnim.load(animations).clip(clip).pose(time)
        world = GrannyAnim.world(self.skeleton, pose)
        # One matrix per vertex influence: bind space -> posed model space.
        self.skin = {name: self.skeleton.inverse_bind[name] @ world[name] for name in self.names}

    def pivots(self, parts):
        out = []
        for part in parts:
            joints = [np.array(self.bones[n][1]) for n in self.bones if any(n.startswith(p) for p in part['bones'])]
            out.append(np.mean(joints, axis=0) if joints else np.zeros(3))
        return out

    def posed(self, quills=None, bulk=None):
        moved, _ = GrannyMesh.deform(self.positions, self.weights, self.indices, self.names, self.bones, quills, bulk)
        homo = np.concatenate([moved, np.ones((len(moved), 1))], axis=1)
        out = np.zeros((len(moved), 3))
        for slot in range(self.weights.shape[1]):
            for k in np.unique(self.indices[:, slot]):
                rows = (self.indices[:, slot] == k) & (self.weights[:, slot] > 0)
                if rows.any():
                    out[rows] += (homo[rows] @ self.skin[self.names[k]])[:, :3] * self.weights[rows, slot][:, None]
        return out


def project(points, yaw, elevation, mirror=False):
    """Model space (+Y up, +Z to the head) -> screen offsets (x right, y down) in model units.

    yaw 0 = the monster faces the viewer (south on screen); elevation is how far the camera looks down.
    """
    c, s = math.cos(yaw), math.sin(yaw)
    x = points[:, 0] * c + points[:, 2] * s
    toward = -points[:, 0] * s + points[:, 2] * c            # how far towards the viewer
    if mirror:
        x = -x
    up = points[:, 1] * math.cos(elevation) - toward * math.sin(elevation)
    return np.stack([x, -up], axis=1)


def silhouette(screen, triangles, size, origin, pixels_per_unit):
    image = Image.new('L', size, 0)
    draw = ImageDraw.Draw(image)
    pts = screen * pixels_per_unit + np.array(origin)
    tri = pts[triangles]
    for t in tri:
        draw.polygon([(t[0, 0], t[0, 1]), (t[1, 0], t[1, 1]), (t[2, 0], t[2, 1])], fill=255)
    return np.asarray(image) > 0


def iou(a, b):
    union = (a | b).sum()
    return float((a & b).sum()) / union if union else 1.0


class Target:
    """The sprite: one mask per view direction, going round from facing south."""

    def __init__(self, archive, token, mode='nu', frame=0, layer='tr'):
        dcc, palette = LegacySprite.load(archive, token, mode, layer)
        order = LegacySprite.VIEW_ORDER.get(dcc.directions, list(range(dcc.directions)))
        self.box = dcc.box
        self.origin = (-dcc.box[0], -dcc.box[1])                 # where the unit stands, in mask pixels
        self.size = (dcc.box[2] - dcc.box[0] + 1, dcc.box[3] - dcc.box[1] + 1)
        self.images = [LegacySprite.to_image(dcc.frames[d][frame], palette, dcc.box) for d in order]
        self.masks = [np.asarray(im)[:, :, 3] > 0 for im in self.images]
        self.yaws = [2 * math.pi * k / len(order) for k in range(len(order))]
        rows = np.nonzero(np.any(np.stack(self.masks), axis=(0, 2)))[0]
        self.height = int(rows.max() - rows.min() + 1)


def camera_search(template, target, verts):
    """Scale, elevation, turn direction and starting yaw that best line the template up with the sprite."""
    best = None
    span = np.ptp(verts[:, 1]) or 1.0
    for mirror in (False, True):
        for turn in (1, -1):
            for start in range(len(target.yaws)):
                for elevation in (25, 30, 35, 40, 45):
                    for scale in np.array([0.7, 0.85, 1.0, 1.15, 1.3]) * target.height / span:
                        score = 0.0
                        for k in (0, 2, 4, 6) if len(target.yaws) >= 8 else range(len(target.yaws)):
                            yaw = turn * target.yaws[k] + target.yaws[start]
                            mask = silhouette(project(verts, yaw, math.radians(elevation), mirror), template.triangles, target.size, target.origin, scale)
                            score += iou(mask, target.masks[k])
                        if best is None or score > best[0]:
                            best = (score, {'mirror': mirror, 'turn': turn, 'start': start, 'elevation': float(elevation), 'scale': float(scale)})
    return best[1]


def draw_views(template, target, camera, verts):
    return [silhouette(project(verts, camera['turn'] * yaw + target.yaws[camera['start']], math.radians(camera['elevation']), camera['mirror']),
                       template.triangles, target.size, target.origin, camera['scale']) for yaw in target.yaws]


def to_spec(vector, parts, pivots, quills):
    bulk = []
    for i, (part, pivot) in enumerate(zip(parts, pivots)):
        x, y, z = vector[i * 3:i * 3 + 3]
        bulk.append({'name': part['name'], 'bones': part['bones'], 'x': round(float(x), 3), 'y': round(float(y), 3), 'z': round(float(z), 3),
                     'pivot': [round(float(v), 4) for v in pivot]})
    base = len(parts) * 3
    quill_specs = []
    for j, quill in enumerate(quills):
        quill_specs.append(dict({k: v for k, v in quill.items() if k != 'name'},
                                length=round(float(vector[base + j * 2]), 3), thickness=round(float(vector[base + j * 2 + 1]), 3)))
    return quill_specs, bulk


def ai_extents(path):
    """Width, height and length of an AI-made mesh after its longest axis is laid along the body: (x, y, z) ratios."""
    import trimesh
    mesh = trimesh.load(path, force='mesh')
    return np.ptp(np.asarray(mesh.vertices), axis=0)


def fit(template, target, parts=None, quills=None, iterations=3, ai_ratio=None, log=print):
    parts = parts or DEFAULT_PARTS
    quills = quills or DEFAULT_QUILLS
    pivots = template.pivots(parts)
    count = len(parts) * 3 + len(quills) * 2
    vector = np.ones(count)
    camera = camera_search(template, target, template.posed())
    log(f'camera: {camera}')

    def score(vec, cam):
        quill_specs, bulk = to_spec(vec, parts, pivots, quills)
        verts = template.posed(quill_specs, bulk)
        views = draw_views(template, target, cam, verts)
        value = float(np.mean([iou(v, m) for v, m in zip(views, target.masks)]))
        # Stay near the template unless the outline says otherwise.
        value -= 0.01 * float(np.mean((np.log(vec)) ** 2))
        if ai_ratio is not None:
            extent = np.ptp(verts, axis=0)
            mine = np.array([extent[0] / extent[2], extent[1] / extent[2]])
            value -= 0.05 * float(np.mean((np.log(mine / np.array(ai_ratio))) ** 2))
        return value

    before = score(vector, camera)
    log(f'template as it is: {before:.4f}')
    best = before
    steps = [0.25, 0.12, 0.06, 0.03]
    for it in range(iterations):
        step = steps[min(it, len(steps) - 1)]
        for i in range(count):
            for direction in (1, -1):
                improved = True
                while improved:
                    trial = vector.copy()
                    trial[i] = float(np.clip(trial[i] * (1 + direction * step), LOW, HIGH))
                    if trial[i] == vector[i]:
                        break
                    value = score(trial, camera)
                    improved = value > best + 1e-5
                    if improved:
                        vector, best = trial, value
        # The body changed: let the camera's scale follow.
        for factor in (0.94, 0.97, 1.03, 1.06):
            trial = dict(camera, scale=camera['scale'] * factor)
            value = score(vector, trial)
            if value > best + 1e-5:
                camera, best = trial, value
        log(f'pass {it + 1}: {best:.4f}')
    quill_specs, bulk = to_spec(vector, parts, pivots, quills)
    verts = template.posed(quill_specs, bulk)
    views = draw_views(template, target, camera, verts)
    return {'before': before, 'after': best, 'camera': camera, 'reshape': {'quills': quill_specs, 'bulk': bulk},
            'perView': [round(iou(v, m), 4) for v, m in zip(views, target.masks)]}, views


def sheet(target, before_views, after_views, path, scale=3):
    w, h = target.size
    out = Image.new('RGB', (w * scale * len(target.masks), h * scale * 3), (30, 32, 38))
    for k, (image, mask) in enumerate(zip(target.images, target.masks)):
        big = image.resize((w * scale, h * scale), Image.NEAREST)
        out.paste(big, (k * w * scale, 0), big)
        for row, views in ((1, before_views), (2, after_views)):
            canvas = np.zeros((h, w, 3), dtype=np.uint8)
            canvas[mask & views[k]] = (90, 200, 110)          # both
            canvas[mask & ~views[k]] = (220, 90, 80)          # sprite only
            canvas[~mask & views[k]] = (80, 130, 230)         # mesh only
            out.paste(Image.fromarray(canvas).resize((w * scale, h * scale), Image.NEAREST), (k * w * scale, row * h * scale))
    draw = ImageDraw.Draw(out)
    for row, label in enumerate(('sprite', 'template before (green both, red sprite only, blue mesh only)', 'after the fit')):
        draw.text((6, row * h * scale + 4), label, fill=(255, 255, 255))
    out.save(path)


def main(argv):
    parser = argparse.ArgumentParser(description='Fit an HD monster mesh to a legacy sprite.')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('fit')
    p.add_argument('--game', default=os.environ.get('D2R_PATH'))
    p.add_argument('--sprite', required=True, help='token of the sprite monster, e.g. s7')
    p.add_argument('--donor', required=True, help='HD folder of the template under hd/character/enemy, e.g. quillrat1')
    p.add_argument('--part', default='torso')
    p.add_argument('--lod', type=int, default=2, help='which LOD of the template to fit with (a lower-detail one is faster)')
    p.add_argument('--iterations', type=int, default=3)
    p.add_argument('--ai-mesh')
    p.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    from d2r_casc import D2RArchive
    os.makedirs(args.out, exist_ok=True)
    with D2RArchive(args.game) as archive, tempfile.TemporaryDirectory() as work:
        model = os.path.join(work, 'template.model')
        with open(model, 'wb') as f:
            f.write(archive.read(f'hd/character/enemy/{args.donor}/{args.part}_lod{args.lod}.model'))
        animations = archive.read(f'hd/character/enemy/{args.donor}/animation/combined.animations')
        template = Template(model, animations)
        target = Target(archive, args.sprite)
    ratio = None
    if args.ai_mesh:
        extent = ai_extents(args.ai_mesh)
        ratio = (extent[0] / extent[2], extent[1] / extent[2])
    before_camera = camera_search(template, target, template.posed())
    before_views = draw_views(template, target, before_camera, template.posed())
    result, views = fit(template, target, iterations=args.iterations, ai_ratio=ratio)
    result.update({'sprite': args.sprite, 'donor': args.donor, 'spriteHeightPx': target.height, 'aiMesh': args.ai_mesh})
    with open(os.path.join(args.out, 'fit.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(result, f, indent=2)
    sheet(target, before_views, views, os.path.join(args.out, 'fit.png'))
    print(f"outline overlap {result['before']:.3f} -> {result['after']:.3f}; per view {result['perView']}")
    print('written', os.path.join(args.out, 'fit.json'), 'and fit.png')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
