"""Offline preview: decode Granny meshes and draw them (flat shaded, painter's algorithm).

Lets a kitbashed body be looked at without the game: donor mesh in bind pose,
props placed on bones with the same translate / rotate / scale an attachment has.
Assumes attachment rotation is Euler XYZ in degrees, applied in the bone's space.
"""
import json
import math
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw

import GrannyFile as granny


def invert_affine(m16):
    """Inverse of a 4x4 (row-major, translation in row 3) affine matrix: (3x3 rotation rows, translation)."""
    m = [list(m16[i * 4:i * 4 + 4]) for i in range(4)]
    r = [row[:3] for row in m[:3]]
    det = (r[0][0] * (r[1][1] * r[2][2] - r[1][2] * r[2][1]) - r[0][1] * (r[1][0] * r[2][2] - r[1][2] * r[2][0])
           + r[0][2] * (r[1][0] * r[2][1] - r[1][1] * r[2][0]))
    inv = [[(r[(j + 1) % 3][(i + 1) % 3] * r[(j + 2) % 3][(i + 2) % 3]
             - r[(j + 1) % 3][(i + 2) % 3] * r[(j + 2) % 3][(i + 1) % 3]) / det for j in range(3)] for i in range(3)]
    t = m[3][:3]
    it = [-(t[0] * inv[0][j] + t[1] * inv[1][j] + t[2] * inv[2][j]) for j in range(3)]
    return inv, it


def _root_refs(g):
    types = {}
    off = 0
    for m in g.read_type(g.root_type):
        types[m['name']] = (off, m)
        off += g.member_size(m)

    def refs(name):
        o, m = types[name]
        at = (g.root_obj[0], g.root_obj[1] + o)
        count = g.i32(at)
        target = g.ptr((at[0], at[1] + 4))
        members = g.read_type(m['ref'])
        return [(members, g.ptr((target[0], target[1] + 8 * k))) for k in range(count)] if target else []
    return refs


def load_meshes(path):
    """[(name, vertices Nx3 float, triangles Mx3 int)] in model space."""
    g = granny.load(path)
    out = []
    for members, at in _root_refs(g)('Meshes'):
        moff = {}
        o = 0
        for m in members:
            moff[m['name']] = (o, m)
            o += g.member_size(m)
        name = g.cstr(g.ptr((at[0], at[1] + moff['Name'][0])))
        ext = g.read_struct(members, at, max_depth=3, array_limit=0).get('ExtendedData') or {}
        scale = ext.get('VertexScale', 1.0) or 1.0
        vd_at = g.ptr((at[0], at[1] + moff['PrimaryVertexData'][0]))
        layout = g.read_type(g.ptr(vd_at))
        vcount = g.i32((vd_at[0], vd_at[1] + 8))
        vptr = g.ptr((vd_at[0], vd_at[1] + 12))
        stride = g.struct_size(layout)
        pos_off = 0
        pos_kind = None
        for m in layout:
            if m['name'] == 'Position':
                pos_kind = m['kind']
                break
            pos_off += g.member_size(m)
        raw = np.frombuffer(g.sections[vptr[0]], dtype=np.uint8, count=vcount * stride, offset=vptr[1]).reshape(vcount, stride)
        if pos_kind in (17, 15):      # int16, normalised
            verts = raw[:, pos_off:pos_off + 6].copy().view('<i2').astype(np.float64) / 32767.0 * scale
        elif pos_kind == 10:
            verts = raw[:, pos_off:pos_off + 12].copy().view('<f4').astype(np.float64)
        elif pos_kind == 21:
            verts = raw[:, pos_off:pos_off + 6].copy().view('<f2').astype(np.float64)
        else:
            raise ValueError(f'{name}: position type {granny.DT[pos_kind]} not handled')
        topo_at = g.ptr((at[0], at[1] + moff['PrimaryTopology'][0]))
        toff = {}
        o = 0
        for m in g.read_type(moff['PrimaryTopology'][1]['ref']):
            toff[m['name']] = o
            o += g.member_size(m)
        n32 = g.i32((topo_at[0], topo_at[1] + toff['Indices']))
        n16 = g.i32((topo_at[0], topo_at[1] + toff['Indices16']))
        if n32:
            p = g.ptr((topo_at[0], topo_at[1] + toff['Indices'] + 4))
            idx = np.frombuffer(g.sections[p[0]], dtype='<i4', count=n32, offset=p[1])
        else:
            p = g.ptr((topo_at[0], topo_at[1] + toff['Indices16'] + 4))
            idx = np.frombuffer(g.sections[p[0]], dtype='<u2', count=n16, offset=p[1])
        out.append((name, verts, idx.astype(np.int64).reshape(-1, 3)))
    return out


def load_bones(path):
    """{name: (3x3 rotation rows = local axes in model space, position)} in bind pose."""
    g = granny.load(path)
    members, at = _root_refs(g)('Skeletons')[0]
    bones = g.read_struct(members, at, max_depth=2, array_limit=100000)['Bones']['items']
    out = {}
    for b in bones:
        rot, pos = invert_affine(b['InverseWorldTransform'])
        out[b['Name']] = (np.array(rot), np.array(pos), b['ParentIndex'])
    return out, [b['Name'] for b in bones]


def euler_xyz(deg):
    x, y, z = (math.radians(deg[k]) for k in 'xyz')
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rz @ ry @ rx      # column vectors: rotate about X, then Y, then Z


def place(verts, bone, translation, rotation, scale):
    """Prop vertices -> model space, through the attachment transform and the bone."""
    rot, pos, _ = bone
    local = (verts * np.array([scale[k] for k in 'xyz'])) @ euler_xyz(rotation).T + np.array([translation[k] for k in 'xyz'])
    return local @ rot + pos   # rows of rot are the bone's axes


def _view(yaw, pitch):
    ya, pi = math.radians(yaw), math.radians(pitch)
    ry = np.array([[math.cos(ya), 0, math.sin(ya)], [0, 1, 0], [-math.sin(ya), 0, math.cos(ya)]])
    rx = np.array([[1, 0, 0], [0, math.cos(pi), -math.sin(pi)], [0, math.sin(pi), math.cos(pi)]])
    return rx @ ry


def frame_of(parts, yaw=35.0, pitch=20.0):
    """(centre x, centre y, span) that fits the parts on screen; pass it to draw() to keep a camera fixed."""
    allv = np.concatenate([p[0] for p in parts]) @ _view(yaw, pitch).T
    lo, hi = allv.min(0), allv.max(0)
    return (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, max(hi[0] - lo[0], hi[1] - lo[1]) * 1.08


def draw(parts, path, size=900, yaw=35.0, pitch=20.0, title='', frame=None):
    """parts: [(verts, tris, base colour)]; the colour may also be one (r, g, b) per triangle.

    frame: (centre x, centre y, span) from frame_of(), so several pictures share one camera;
    by default the picture is fitted to the parts. path None: the image is only returned.
    """
    view = _view(yaw, pitch)
    cx, cy, span = frame if frame is not None else frame_of(parts, yaw, pitch)
    img = Image.new('RGB', (size, size), (24, 26, 30))
    d = ImageDraw.Draw(img)
    light = np.array([0.35, 0.8, 0.5])
    light = light / np.linalg.norm(light)
    polys = []
    for verts, tris, colour in parts:
        v = verts @ view.T
        a, b, c = v[tris[:, 0]], v[tris[:, 1]], v[tris[:, 2]]
        n = np.cross(b - a, c - a)
        ln = np.linalg.norm(n, axis=1)
        ln[ln == 0] = 1
        n = n / ln[:, None]
        shade = 0.35 + 0.65 * np.abs(n @ light)
        depth = (a[:, 2] + b[:, 2] + c[:, 2]) / 3
        sx = lambda p: (p[:, 0] - cx) / span * size + size / 2
        sy = lambda p: size / 2 - (p[:, 1] - cy) / span * size
        per_triangle = np.ndim(colour) == 2
        for i in range(len(tris)):
            col = tuple(int(min(255, ch * shade[i])) for ch in (colour[i] if per_triangle else colour))
            polys.append((depth[i], [(sx(a[i:i + 1])[0], sy(a[i:i + 1])[0]), (sx(b[i:i + 1])[0], sy(b[i:i + 1])[0]), (sx(c[i:i + 1])[0], sy(c[i:i + 1])[0])], col))
    polys.sort(key=lambda t: t[0])
    for _, pts, col in polys:
        d.polygon(pts, fill=col)
    if title:
        d.text((12, 10), title, fill=(230, 230, 230))
    if path:
        img.save(path)
    return img


def posed_parts(model_paths, skeleton, pose, colours=None, root_scale=1.0):
    """A skinned body in a pose, as draw() parts.

    skeleton: a GrannyAnim.Skeleton; pose: {bone: GrannyAnim.Local}, e.g. clip.pose(t).
    colours: [(bone name prefixes or substrings, (r, g, b)), ...]; each triangle takes the colour of
    the first entry that matches the bone its first vertex follows most (so wings, head and body
    can be told apart in a still). Others are drawn in the default body colour.
    """
    import GrannyAnim
    import GrannyMesh
    out = []
    for path in model_paths:
        triangles = {name: tris for name, _, tris in load_meshes(path)}
        for mesh in GrannyMesh.Model(path).meshes:
            weights, indices = mesh.weights()
            verts = GrannyAnim.skin(mesh.positions(), weights, indices, mesh.bones, skeleton, pose) * root_scale
            tris = triangles[mesh.name]
            colour = (150, 120, 95)
            if colours:
                main = np.array([mesh.bones[indices[k, np.argmax(weights[k])]] for k in range(len(verts))])
                per_vertex = np.tile(np.array(colour, dtype=np.float64), (len(verts), 1))
                assigned = np.zeros(len(verts), dtype=bool)
                for keys, rgb in colours:
                    hit = ~assigned & np.array([any(key in name for key in keys) for name in main])
                    per_vertex[hit] = rgb
                    assigned |= hit
                colour = per_vertex[tris[:, 0]]
            out.append((verts, tris, colour))
    return out


def ground_part(half_size, height=0.0):
    """A flat square on the floor (y = height), so a still shows how high a body is."""
    s = float(half_size)
    verts = np.array([[-s, height, -s], [s, height, -s], [s, height, s], [-s, height, s]])
    return verts, np.array([[0, 1, 2], [0, 2, 3]]), (70, 74, 80)


def clip_sheet(model_paths, skeleton, animations, clip, fractions, path, views=((90.0, 10.0), (35.0, 30.0)),
               size=320, colours=None, root_scale=1.0, ground=None, title=''):
    """One picture per (view, moment) of a clip: rows are views, columns the moments (0..1 of the clip).

    Every picture in a row shares one camera, so movement between the moments shows.
    skeleton: GrannyAnim.Skeleton; animations: GrannyAnim.Animations (or a path to one).
    ground: half size of a floor square at y = 0 to draw under the body, or None.
    """
    import GrannyAnim
    if isinstance(animations, (str, bytes, bytearray)):
        animations = GrannyAnim.load(animations)
    c = animations.clip(clip)
    scenes = []
    for f in fractions:
        parts = posed_parts(model_paths, skeleton, c.pose(f * c.duration), colours, root_scale)
        if ground:
            parts.append(ground_part(ground))
        scenes.append(parts)
    sheet = Image.new('RGB', (size * len(fractions), size * len(views) + 22), (12, 13, 15))
    for row, (yaw, pitch) in enumerate(views):
        frame = frame_of([p for parts in scenes for p in parts], yaw, pitch)
        for col, parts in enumerate(scenes):
            label = f'{clip} {fractions[col] * 100:.0f}% ({fractions[col] * c.duration:.2f}s)  yaw {yaw:g} pitch {pitch:g}'
            sheet.paste(draw(parts, None, size=size, yaw=yaw, pitch=pitch, title=label, frame=frame), (col * size, 22 + row * size))
    ImageDraw.Draw(sheet).text((8, 5), title or f'{clip}: {c.duration:.3f} s', fill=(240, 240, 240))
    if path:
        sheet.save(path)
    return sheet


def build_scene(donor_models, skeleton, props, attachments, root_scale=(1, 1, 1)):
    bones, _ = load_bones(skeleton)
    parts = []
    for model in donor_models:
        for name, verts, tris in load_meshes(model):
            parts.append((verts * np.array(root_scale), tris, (150, 120, 95)))
    cache = {}
    missing = set()
    for a in attachments:
        if a['bone'] not in bones:
            missing.add(a['bone'])
            continue
        if a['prop'] not in cache:
            cache[a['prop']] = load_meshes(props[a['prop']])
        for name, verts, tris in cache[a['prop']]:
            placed = place(verts, bones[a['bone']], a['translation'], a['rotation'], a['scale'])
            parts.append((placed * np.array(root_scale), tris, a.get('colour', (225, 215, 190))))
    if missing:
        print('bones not in the skeleton:', sorted(missing))
    return parts


if __name__ == '__main__':
    spec = json.load(open(sys.argv[1], encoding='utf-8'))
    parts = build_scene(spec['models'], spec['skeleton'], spec.get('props', {}), spec.get('attachments', []), spec.get('rootScale', (1, 1, 1)))
    for view in spec.get('views', [{'yaw': 35, 'pitch': 20}]):
        out = spec['out'].replace('.png', f"_{view.get('name', 'view')}.png")
        draw(parts, out, yaw=view['yaw'], pitch=view['pitch'], title=spec.get('title', '') + ' ' + view.get('name', ''))
        print('wrote', out)
