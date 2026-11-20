"""Legacy sprites for an HD monster: what the game shows when HD graphics are switched off.

In legacy graphics the game draws a monster from 2D sprite files that belong to its
`monstats.txt` `Code` (a two-letter token): per animation mode one DCC file with every frame
from every view direction, and a COF file that describes the animation. An HD monster made
from a donor has no sprites of its own and shows as its donor's token. This tool makes them:
it poses the HD model with its own clips, draws every frame from the legacy camera with the
model's albedo texture, fits the picture to the game palette and writes the files.

    python HdToLegacy.py build <spec.json> --game <D2R folder> --mod <mod folder>
                               [--out <folder>] [--modes nu,wl] [--sheets <folder>] [--frames-only]

    <out>/global/monsters/<token>/tr/<token>trlit<mode>hth.dcc   the frames
    <out>/global/monsters/<token>/cof/<token><mode>hth.cof       the animation descriptors
    <out>/global/monsters/<token>/cof/palshift.dat               colour shift table (none)
    <sheets>/<token>_<mode>.png                                  every direction and frame, to look at
    <out>/legacy_<token>.report.json                             files, sizes, AssetMerge animdata rows

spec.json:
    "token": "wb"            the new two-character token (must not be a stock one)
    "definition": "hd/character/enemy/wb_wild_boar.json"   in the mod folder or the game
    "like": "tg"             a stock token: its modes, frame counts, directions, speed and event
                             frames are copied, so the game times the new token like the old one
                             (and the report's animdata rows copy the donor's timing by name)
    "clips": {"nu": "neutral", "a1": "attack"}   mode -> clip; default: the definition's state machine
    "modes": {"dt": {"clip": "death", "frames": 16, "directions": 8, "speed": 256, "events": {"7": 1}}}
                             modes without a donor, or changes to a donor's mode
    "albedo": {"torso": "hd/character/enemy/wb_wild_boar/boaralb.texture"}   texture per model
                             (file name start); default: the model's own AlbedoTexture
    "lod": 2                 which LOD files to draw (a sprite is small; 2 is plenty)
    "light": {"ambient": 0.45, "diffuse": 1.0, "gain": 1.15, "from": [-0.45, 0.75, 0.5]}
    "scale": 1.0             on top of the definition's own scale

The camera (found by fitting stock HD bodies to their own sprites): 30 degrees down, 8 * sqrt(2)
pixels per model unit (a model unit is a foot, two to a subtile), mirrored left to right; a
monster facing the viewer is "south". Directions are stored in the game's order
(LegacySprite.VIEW_ORDER).

Whether the game accepts these files has to be seen in the game: the encoder is checked against
the toolkit's own decoder and Blizzard's header numbers, not against the game.
"""
import argparse
import io
import json
import math
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import Granny  # noqa: E402
import GrannyAnim  # noqa: E402
import HdTexture  # noqa: E402
import LegacySprite  # noqa: E402

PIXELS_PER_UNIT = 8 * math.sqrt(2)
ELEVATION = math.radians(30)
MODE_IDS = {'dt': 0, 'nu': 1, 'wl': 2, 'gh': 3, 'a1': 4, 'a2': 5, 'bl': 6, 'sc': 7, 's1': 8, 's2': 9,
            's3': 10, 's4': 11, 'dd': 12, 'kb': 13, 'xx': 14, 'rn': 15}
LOOPING = {'nu', 'wl', 'rn', 'dd'}
SUPERSAMPLE = 4


class Files:
    """Mod folder first, then the game archive. Paths as the game writes them, with or without data/."""

    def __init__(self, archive, mod_dir):
        self.archive, self.mod_dir = archive, mod_dir
        self._names = None

    @staticmethod
    def clean(path):
        path = path.replace('\\', '/')
        return path[5:] if path.lower().startswith('data/') else path

    def read(self, path):
        path = self.clean(path)
        if self.mod_dir:
            local = os.path.join(self.mod_dir, *path.split('/'))
            if os.path.isfile(local):
                with open(local, 'rb') as f:
                    return f.read()
        data = self.archive.read(path) if self.archive else None
        if data is None:
            raise FileNotFoundError(path)
        return data

    def has(self, path):
        path = self.clean(path)
        if self.mod_dir and os.path.isfile(os.path.join(self.mod_dir, *path.split('/'))):
            return True
        if self._names is None:
            self._names = set(self.archive.list()) if self.archive else set()
        return path in self._names or path.lower() in self._names

    def names(self):
        self.has('')
        return self._names


# --- the body ------------------------------------------------------------------------------

class Part:
    """One mesh: bind-pose vertices, skin, UVs, triangles and its texture."""

    def __init__(self, tree, mesh, texture):
        items = mesh['PrimaryVertexData']['Vertices']['$items']
        scale = float(mesh['ExtendedData']['$value'].get('VertexScale') or 1.0)
        self.positions = np.array([it['Position'][:3] for it in items], dtype=np.float64) / 32767.0 * scale
        self.uvs = np.array([it.get('TextureCoordinates0', [0.0, 0.0]) for it in items], dtype=np.float64)
        self.bones = [b['BoneName'] for b in mesh['BoneBindings']]
        if 'BoneWeights' in items[0]:
            self.weights = np.array([it['BoneWeights'] for it in items], dtype=np.float64) / 255.0
            self.indices = np.array([it['BoneIndices'] for it in items], dtype=np.int64)
        else:
            self.weights = np.ones((len(items), 1))
            self.indices = np.zeros((len(items), 1), dtype=np.int64)
        topology = mesh['PrimaryTopology']
        self.triangles = np.array(topology['Indices16'] or topology['Indices'], dtype=np.int64).reshape(-1, 3)
        self.texture = texture
        self.skeleton = GrannyAnim.Skeleton(tree)
        self.bone = None                # a prop: the body bone that carries it
        self.local = None               # and its vertices in that bone's frame


def _albedo_path(mesh):
    for binding in mesh.get('MaterialBindings') or []:
        for entry in binding['Material'].get('Maps') or []:
            if entry['Usage'] == 'AlbedoTexture' and entry['Map'].get('Texture'):
                return entry['Map']['Texture']['FromFileName']
    return None


def _texture(files, path, cache, size=256):
    if path not in cache:
        try:
            image = HdTexture.to_image(files.read(path)).convert('RGB')
            image.thumbnail((size, size))
            cache[path] = np.asarray(image, dtype=np.float64) / 255.0
        except (FileNotFoundError, ValueError) as error:
            print(f'  texture {path}: {error}; drawn grey')
            cache[path] = np.full((2, 2, 3), 0.55)
    return cache[path]


def _model_file(files, name, lod):
    """data/.../torso.model -> the LOD file to read (the wanted LOD, or the nearest that exists)."""
    stem = Files.clean(name)[:-len('.model')]
    for level in [lod] + list(range(lod - 1, -1, -1)) + list(range(lod + 1, 6)):
        if files.has(f'{stem}_lod{level}.model'):
            return f'{stem}_lod{level}.model'
    if files.has(f'{stem}.model'):
        return f'{stem}.model'
    return None


def _euler(rotation):
    x, y, z = (math.radians(rotation[k]) for k in 'xyz')
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rz @ ry @ rx


class Body:
    """Everything a definition draws: its models, the props attached to its bones, its clips."""

    def __init__(self, files, spec):
        self.files = files
        definition = json.loads(files.read(spec['definition']))
        components = [c for e in definition['entities'] for c in e['components']]
        lod = int(spec.get('lod', 2))
        textures = {}
        self.parts = []
        self.notes = []
        self.scale = float(spec.get('scale', 1.0))
        for c in components:
            if c['type'] == 'TransformDefinitionComponent' and c.get('scale') and 'root' in c['name']:
                self.scale *= float(c['scale']['y'])
        overrides = spec.get('albedo') or {}
        for c in components:
            if c['type'] != 'ModelDefinitionComponent':
                continue
            path = _model_file(files, c['filename'], lod)
            if path is None:
                self.notes.append(f"{c['filename']}: no file, skipped")
                continue
            base = os.path.basename(path)
            if any(key in base.lower() for key in ('vfxshell', 'objectfx')):
                continue
            tree = Granny.read(files.read(path)).root()
            for mesh in tree['Meshes']:
                wanted = next((v for k, v in overrides.items() if base.lower().startswith(k.lower())), None) or _albedo_path(mesh)
                self.parts.append(Part(tree, mesh, _texture(files, wanted, textures) if wanted else np.full((2, 2, 3), 0.55)))
        if not self.parts:
            raise ValueError('the definition draws no model that could be read')
        self.skeleton = self.parts[0].skeleton
        for c in components:
            if c['type'] != 'UnitAttachmentComponent' or not c.get('overrideBoneName'):
                continue
            try:
                prop = json.loads(files.read(c['filename']))
            except FileNotFoundError:
                self.notes.append(f"{c['filename']}: prop not found, skipped")
                continue
            if c['overrideBoneName'] not in self.skeleton.index:
                self.notes.append(f"prop on {c['overrideBoneName']}: no such bone, skipped")
                continue
            t = c['attachmentTransform']
            for pc in (pc for e in prop['entities'] for pc in e['components'] if pc['type'] == 'ModelDefinitionComponent'):
                path = _model_file(files, pc['filename'], lod)
                if path is None:
                    continue
                tree = Granny.read(files.read(path)).root()
                for mesh in tree['Meshes']:
                    albedo = _albedo_path(mesh)
                    if albedo is None:
                        albedo = next((d['path'] for d in prop['dependencies'].get('textures', []) if 'alb' in d['path'].lower()), None)
                    part = Part(tree, mesh, _texture(files, albedo, textures) if albedo else np.full((2, 2, 3), 0.8))
                    part.bone = c['overrideBoneName']
                    scaled = part.positions * np.array([t['scale'][k] for k in 'xyz'])
                    part.local = scaled @ _euler(t['rotation']).T + np.array([t['translation'][k] for k in 'xyz'])
                    self.parts.append(part)
        root = next(c for c in components if c['type'] == 'UnitRootComponent')
        self.state_clips = {}
        if root.get('state_machine_filename'):
            try:
                machine = json.loads(files.read(root['state_machine_filename']))
                for state in machine.get('states', []):
                    bound = state.get('animationBindings') or {}
                    clip = (bound.get('hth') or next(iter(bound.values()), [None]))[0] if bound else None
                    if clip and state.get('skillIndex', -1) == -1 and state.get('modeId') not in self.state_clips:
                        self.state_clips[state['modeId']] = clip
                folder = os.path.dirname(Files.clean(root['state_machine_filename']))
                self.animations = GrannyAnim.load(files.read(f'{folder}/animation/combined.animations'))
            except FileNotFoundError as error:
                raise ValueError(f'the state machine or its animations are missing: {error}')
        else:
            raise ValueError('the definition has no state machine, so there are no clips to draw')

    def posed(self, pose):
        """[(vertices N x 3 in model units, scaled), triangles, uvs, texture)] for a pose."""
        out = []
        world = None
        for part in self.parts:
            if part.bone is None:
                verts = GrannyAnim.skin(part.positions, part.weights, part.indices, part.bones, part.skeleton, pose)
            else:
                world = world if world is not None else GrannyAnim.world(self.skeleton, pose)
                verts = (np.concatenate([part.local, np.ones((len(part.local), 1))], axis=1) @ world[part.bone])[:, :3]
            out.append((verts * self.scale, part.triangles, part.uvs, part.texture))
        return out


# --- drawing -------------------------------------------------------------------------------

def view_axes(yaw):
    """Rows: screen right, screen down, towards the viewer, as directions in model space.

    The legacy camera: yaw 0 looks at a monster that faces it (south on screen), from 30 degrees
    above, with left and right swapped (found by fitting stock bodies to their sprites)."""
    c, s = math.cos(yaw), math.sin(yaw)
    right = np.array([c, 0.0, s])
    toward = np.array([-s, 0.0, c])
    up = np.array([0.0, 1.0, 0.0])
    ce, se = math.cos(ELEVATION), math.sin(ELEVATION)
    return np.stack([-right, -(up * ce - toward * se), toward * ce + up * se])


def rasterise(screen, depth, triangles, width, height):
    """Nearest triangle per pixel. screen N x 2 in pixels, depth N (larger = nearer).

    Returns (triangle index H x W, -1 where empty; barycentric weights H x W x 3)."""
    p = screen[triangles]
    area = (p[:, 1, 0] - p[:, 0, 0]) * (p[:, 2, 1] - p[:, 0, 1]) - (p[:, 2, 0] - p[:, 0, 0]) * (p[:, 1, 1] - p[:, 0, 1])
    low = np.floor(p.min(1)).astype(np.int64)
    high = np.ceil(p.max(1)).astype(np.int64)
    span = (high - low).max(1) + 1
    keep = (np.abs(area) > 1e-9) & (high[:, 0] >= 0) & (high[:, 1] >= 0) & (low[:, 0] < width) & (low[:, 1] < height)
    found = {'pixel': [], 'depth': [], 'triangle': [], 'a': [], 'b': []}
    for size in (4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048):
        rows = np.flatnonzero(keep & (span <= size) & (span > size // 2 if size > 4 else True))
        step = max(1, 2_000_000 // (size * size))
        offsets = np.arange(size)
        for start in range(0, len(rows), step):
            r = rows[start:start + step]
            x = low[r, 0][:, None, None] + offsets[None, None, :]
            y = low[r, 1][:, None, None] + offsets[None, :, None]
            px, py = x + 0.5, y + 0.5
            a, b, c = p[r, 0], p[r, 1], p[r, 2]
            w0 = (b[:, 0, None, None] - px) * (c[:, 1, None, None] - py) - (c[:, 0, None, None] - px) * (b[:, 1, None, None] - py)
            w1 = (c[:, 0, None, None] - px) * (a[:, 1, None, None] - py) - (a[:, 0, None, None] - px) * (c[:, 1, None, None] - py)
            total = area[r][:, None, None]
            w0, w1 = w0 / total, w1 / total
            w2 = 1.0 - w0 - w1
            inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0) & (x >= 0) & (x < width) & (y >= 0) & (y < height)
            if not inside.any():
                continue
            d = depth[triangles[r]]
            z = w0 * d[:, 0, None, None] + w1 * d[:, 1, None, None] + w2 * d[:, 2, None, None]
            which = np.broadcast_to(r[:, None, None], inside.shape)
            found['pixel'].append((y * width + x)[inside])
            found['depth'].append(z[inside])
            found['triangle'].append(which[inside])
            found['a'].append(w0[inside])
            found['b'].append(w1[inside])
    index = np.full(width * height, -1, dtype=np.int64)
    weights = np.zeros((width * height, 3))
    if found['pixel']:
        pixel, z = np.concatenate(found['pixel']), np.concatenate(found['depth'])
        order = np.lexsort((-z, pixel))
        pixel = pixel[order]
        first = np.concatenate([[True], pixel[1:] != pixel[:-1]])
        chosen = order[first]
        where = pixel[first]
        index[where] = np.concatenate(found['triangle'])[chosen]
        a, b = np.concatenate(found['a'])[chosen], np.concatenate(found['b'])[chosen]
        weights[where] = np.stack([a, b, 1.0 - a - b], axis=1)
    return index.reshape(height, width), weights.reshape(height, width, 3)


def draw(posed, yaw, canvas, origin, light):
    """One frame: (rgb H x W x 3 in 0..1, opaque H x W) on a canvas of `canvas` = (width, height)
    pixels with the unit's standing point at `origin`."""
    axes = view_axes(yaw)
    ss = SUPERSAMPLE
    width, height = canvas[0] * ss, canvas[1] * ss
    all_screen, all_depth, all_tris, all_uv, all_normal, texture_of = [], [], [], [], [], []
    base = 0
    textures = []
    for verts, tris, uvs, texture in posed:
        normal = np.zeros_like(verts)
        face = np.cross(verts[tris[:, 1]] - verts[tris[:, 0]], verts[tris[:, 2]] - verts[tris[:, 0]])
        for k in range(3):
            np.add.at(normal, tris[:, k], face)
        length = np.linalg.norm(normal, axis=1, keepdims=True)
        length[length == 0] = 1.0
        seen = verts @ axes.T
        all_screen.append((seen[:, :2] * PIXELS_PER_UNIT + np.array(origin)) * ss)
        all_depth.append(seen[:, 2])
        all_tris.append(tris + base)
        all_uv.append(uvs)
        all_normal.append(normal / length)
        texture_of.append(np.full(len(tris), len(textures)))
        textures.append(texture)
        base += len(verts)
    screen, depth, tris = np.concatenate(all_screen), np.concatenate(all_depth), np.concatenate(all_tris)
    uv, normal, texture_of = np.concatenate(all_uv), np.concatenate(all_normal), np.concatenate(texture_of)
    index, weights = rasterise(screen, depth, tris, width, height)
    hit = index >= 0
    rgb = np.zeros((height, width, 3))
    if hit.any():
        t = tris[index[hit]]
        w = weights[hit]
        at = (uv[t] * w[:, :, None]).sum(1)
        n = (normal[t] * w[:, :, None]).sum(1)
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
        # The light stands still on the screen (up, to the left, in front), as in drawn sprites.
        towards = np.array(light.get('from', [-0.45, 0.75, 0.5]), dtype=np.float64)
        towards = (towards / np.linalg.norm(towards)) * [1, -1, 1]
        facing = np.abs(n @ axes[2])[:, None]            # two-sided: a mirrored view flips the winding
        lit = np.maximum(0.0, (n @ axes.T) @ towards * np.sign(n @ axes[2] + 1e-12))[:, None]
        shade = light.get('ambient', 0.45) + light.get('diffuse', 1.0) * lit + 0.1 * facing
        colour = np.zeros((len(t), 3))
        which = texture_of[index[hit]]
        for k, texture in enumerate(textures):
            rows = which == k
            if rows.any():
                th, tw = texture.shape[:2]
                u = np.clip((at[rows, 0] % 1.0) * tw, 0, tw - 1).astype(int)
                v = np.clip((at[rows, 1] % 1.0) * th, 0, th - 1).astype(int)
                colour[rows] = texture[v, u]
        rgb[hit] = np.clip(colour * shade * light.get('gain', 1.15), 0.0, 1.0)
    cover = hit.reshape(canvas[1], ss, canvas[0], ss).mean((1, 3))
    summed = rgb.reshape(canvas[1], ss, canvas[0], ss, 3).sum((1, 3))
    return summed / np.maximum(cover[:, :, None] * ss * ss, 1e-9), cover >= 0.5


def to_palette(rgb, opaque, palette, tree):
    """Nearest palette colour per opaque pixel (never index 0, which is see-through)."""
    out = np.zeros(opaque.shape, dtype=np.uint8)
    if opaque.any():
        _, nearest = tree.query(rgb[opaque] * 255.0)
        out[opaque] = nearest + 1
    return out


def extent(body, clip, times, yaws):
    """(width, height, origin) of a canvas that holds every frame of a mode from every direction."""
    low, high = np.full(2, np.inf), np.full(2, -np.inf)
    for t in times:
        posed = body.posed(clip.pose(t))
        verts = np.concatenate([p[0] for p in posed])
        for yaw in yaws:
            seen = (verts @ view_axes(yaw).T)[:, :2] * PIXELS_PER_UNIT
            low, high = np.minimum(low, seen.min(0)), np.maximum(high, seen.max(0))
    low, high = np.floor(low).astype(int) - 2, np.ceil(high).astype(int) + 2
    return int(high[0] - low[0]), int(high[1] - low[1]), (int(-low[0]), int(-low[1]))


# --- one token ----------------------------------------------------------------------------

def donor_modes(files, token):
    """{mode: {frames, directions, speed, events, weapon}} from a stock token's COF files."""
    token = token.lower()
    prefix = f'global/monsters/{token}/cof/{token}'
    out = {}
    for name in sorted(files.names()):
        if not (name.startswith(prefix) and name.endswith('.cof')):
            continue
        mode, weapon = name[len(prefix):len(prefix) + 2], name[len(prefix) + 2:-4]
        if mode not in MODE_IDS or (mode in out and weapon != 'hth'):
            continue
        data = files.read(name)
        layers, frames, directions = data[0], data[1], data[2]
        marks = data[28 + 9 * layers:28 + 9 * layers + frames]
        out[mode] = {'frames': frames, 'directions': directions, 'speed': struct.unpack_from('<H', data, 24)[0],
                     'events': {str(i): v for i, v in enumerate(marks) if v}, 'weapon': weapon, 'donor': os.path.basename(name)[:-4].upper()}
    return out


def build(spec, files, out_dir, sheets=None, only=None, frames_only=False, log=print):
    from scipy.spatial import cKDTree
    from PIL import Image
    token = spec['token'].lower()
    if len(token) != 2:
        raise ValueError('"token" must be two characters')
    if any(n.startswith(f'global/monsters/{token}/') for n in files.archive.list()):
        raise ValueError(f'"{token}" is a stock token; pick one the game does not have')
    body = Body(files, spec)
    for note in body.notes:
        log('  ' + note)
    palette = LegacySprite.load_palette(files.read('global/palette/act1/pal.dat'))
    tree = cKDTree(palette[1:, :3].astype(np.float64))
    modes = donor_modes(files, spec['like']) if spec.get('like') else {}
    for mode, change in (spec.get('modes') or {}).items():
        modes.setdefault(mode.lower(), {'frames': 0, 'directions': 8, 'speed': 256, 'events': {}, 'weapon': 'hth'}).update(change)
    clips = {m: body.state_clips.get(MODE_IDS[m]) for m in modes}
    clips.update({k.lower(): v for k, v in (spec.get('clips') or {}).items()})
    light = spec.get('light') or {}
    report = {'token': token, 'like': spec.get('like'), 'scale': body.scale, 'modes': {}, 'animdata': [], 'files': []}
    known = body.animations.names()
    for mode, info in modes.items():
        if only and mode not in only:
            continue
        name = info.get('clip') or clips.get(mode)
        if not name or name not in known:
            log(f'  {mode}: no clip ({name!r}); mode left out')
            report['modes'][mode] = {'skipped': f'no clip {name!r}'}
            continue
        clip = body.animations.clip(name)
        frames = int(info['frames']) or max(2, min(60, int(round(clip.duration * 25 * info['speed'] / 256))))
        count = int(info['directions'])
        if count not in LegacySprite.VIEW_ORDER:
            raise ValueError(f'{mode}: {count} directions are not handled')
        if 'at' in info:
            times = [float(info['at']) * clip.duration] * frames
        elif mode in LOOPING:
            times = [clip.duration * i / frames for i in range(frames)]
        else:
            times = [clip.duration * i / max(frames - 1, 1) for i in range(frames)]
        order = LegacySprite.VIEW_ORDER[count]                   # stored index of each facing, going round from south
        yaws = [2 * math.pi * k / count for k in range(count)]
        width, height, origin = extent(body, clip, times, yaws)
        stored = [None] * count
        poses = [body.posed(clip.pose(t)) for t in times]
        for facing, yaw in enumerate(yaws):
            row = []
            for posed in poses:
                rgb, opaque = draw(posed, yaw, (width, height), origin, light)
                row.append(to_palette(rgb, opaque, palette, tree))
            stored[order[facing]] = row
        solid = np.argwhere(np.stack([f for row in stored for f in row]).any(0))
        box = (int(solid[:, 1].min() - origin[0]), int(solid[:, 0].min() - origin[1]),
               int(solid[:, 1].max() - origin[0]), int(solid[:, 0].max() - origin[1]))
        weapon = info.get('weapon', 'hth')
        dcc = LegacySprite.encode(stored, origin, palette)
        cof = LegacySprite.encode_cof(frames, count, box, info['speed'], ('tr',), info.get('events'), weapon)
        written = {f'global/monsters/{token}/tr/{token}trlit{mode}{weapon}.dcc': dcc,
                   f'global/monsters/{token}/cof/{token}{mode}{weapon}.cof': cof}
        if not frames_only:
            for path, data in written.items():
                full = os.path.join(out_dir, *path.split('/'))
                os.makedirs(os.path.dirname(full), exist_ok=True)
                with open(full, 'wb') as f:
                    f.write(data)
                report['files'].append({'path': path, 'bytes': len(data)})
        if sheets:
            os.makedirs(sheets, exist_ok=True)
            decoded = LegacySprite.Dcc(dcc)
            w, h = decoded.box[2] - decoded.box[0] + 1, decoded.box[3] - decoded.box[1] + 1
            sheet = Image.new('RGBA', (w * frames * 2, h * count * 2), (40, 44, 52, 255))
            for r, d in enumerate(order):
                for c, frame in enumerate(decoded.frames[d]):
                    image = LegacySprite.to_image(frame, palette, decoded.box, 2)
                    sheet.paste(image, (c * w * 2, r * h * 2), image)
            sheet.save(os.path.join(sheets, f'{token}_{mode}.png'))
        cof_name = f'{token}{mode}{weapon}'.upper()
        row = {'name': cof_name, 'frames': frames, 'speed': info['speed'],
               'events': ' '.join(f'{k}:{v}' for k, v in sorted((info.get('events') or {}).items(), key=lambda e: int(e[0]))) or '-'}
        if info.get('donor'):
            row['source'] = info['donor']
        report['animdata'].append(row)
        report['modes'][mode] = {'clip': name, 'frames': frames, 'directions': count, 'speed': info['speed'], 'box': box, 'dccBytes': len(dcc)}
        log(f'  {mode}: {name}, {count} directions x {frames} frames, box {box}, {len(dcc)} bytes')
    if not frames_only:
        shift = os.path.join(out_dir, 'global', 'monsters', token, 'cof', 'palshift.dat')
        os.makedirs(os.path.dirname(shift), exist_ok=True)
        with open(shift, 'wb') as f:
            f.write(bytes(range(256)) * 8)                       # eight colour variants, all unshifted
        with open(os.path.join(out_dir, f'legacy_{token}.report.json'), 'w', encoding='utf-8', newline='\n') as f:
            json.dump(report, f, indent=1)
    return report


def main(argv):
    parser = argparse.ArgumentParser(description='Legacy sprites (DCC + COF) drawn from an HD monster.')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('build')
    p.add_argument('spec')
    p.add_argument('--game', default=os.environ.get('D2R_PATH'))
    p.add_argument('--mod', help='mod folder: its files are read before the game\'s, and it is the default output')
    p.add_argument('--out')
    p.add_argument('--modes', help='only these modes, e.g. nu,wl')
    p.add_argument('--sheets', help='folder for one picture per mode')
    p.add_argument('--frames-only', action='store_true', help='draw the pictures, write no game files')
    args = parser.parse_args(argv)
    with open(args.spec, encoding='utf-8') as f:
        spec = json.load(f)
    out = args.out or args.mod
    if not out and not args.frames_only:
        parser.error('--out or --mod is needed')
    from d2r_casc import D2RArchive
    with D2RArchive(args.game) as archive:
        report = build(spec, Files(archive, args.mod), out, args.sheets, set(args.modes.lower().split(',')) if args.modes else None, args.frames_only)
    done = [m for m, v in report['modes'].items() if 'skipped' not in v]
    print(f"{report['token']}: {len(done)} modes written" + (f" to {out}" if not args.frames_only else ' (pictures only)'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
