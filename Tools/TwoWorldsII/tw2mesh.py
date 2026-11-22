"""Two Worlds II meshes (.vdf static, .chv skinned): materials, glTF export with textures, UV layouts.

Format (decoded 2026-11-21 from ~10,000 sampled meshes; the same tagged tree as .chm, see tw2anim / chm.py):
  A mesh is a container holding Vertexes, Faces, NumVertexes, NumFaces (= index count), VertexFormat, Skinned,
  LODLevel, Name, and one material child (tag 0xFFFFFF03): Name, ShaderName (*.efx), TexS0..TexS4 (bare texture
  file names), SpecColor, DestColor, AFactor, FurLayers/FurParams, DestParams. Faces are u16 triangle indices.
  Vertex layouts (stride = len(Vertexes) / NumVertexes):
    static, VertexFormat 1   36 bytes: f32 x y z, normal u8 z y x 0, tangent u8 z y x sign, UV0, UV1 (f32 u v)
    static, VertexFormat 2   44 bytes: as above + UV2
    skinned (.chv)           52 bytes: f32 x y z, f32 w0 w1 w2 (w3 = 1 - sum), u8 bone indices x4, normal,
                             tangent, UV0, UV1. Bones: NumBones, BoneIDS (512-byte names), BindMatrix (4x4 each)
    face morph meshes (Models\\FACE)  16 bytes, no faces: not exported
  Normals are D3DCOLOR-packed (stored B G R = z y x) and agree with the face winding. V runs UP the texture
  (v = 0 is the bottom row; checked against UV layouts), so glTF gets 1 - v.
  Positions are Y up in a left-handed space: the glTF export negates Z and flips the winding.

usage:
  python tw2mesh.py find PATTERN [--limit N]          meshes whose path contains PATTERN
  python tw2mesh.py info REF                          meshes, vertex layout, materials, shaders, texture slots
  python tw2mesh.py export REF [OUT.glb] [--no-textures]   glTF binary with base colour + normal textures
  python tw2mesh.py uvmap REF [--out DIR] [--size N]  UV layout per texture (wireframe over the texture), the
                                                      guide for repainting or generating a texture
REF is a game path (Models\\...\\X.vdf), or a .vdf/.chv file on disk.
"""
import argparse
import io
import json
import os
import struct
import sys

import tw2common as C
import tw2tex as T

from PIL import Image, ImageDraw


class Mesh:
    def __init__(self, node):
        self.name = node.str('Name') or ''
        self.nv = node.int('NumVertexes')
        self.vfmt = node.int('VertexFormat')
        sk = node.get('Skinned')
        self.skinned = bool(sk and struct.unpack('<I', sk.value)[0])
        self.lod = node.int('LODLevel') or 0
        v = node.get('Vertexes').value
        f = node.get('Faces')
        self.stride = len(v) // self.nv if self.nv else 0
        self.indices = list(struct.unpack('<%dH' % (len(f.value) // 2), f.value)) if f is not None else []
        self.mat = next((c for c in node.containers() if c.get('ShaderName') is not None), None)
        self.pos, self.nrm, self.uvs = [], [], []
        base = 36 if self.skinned else 20
        nuv = max(0, (self.stride - base) // 8)
        self.uvs = [[] for _ in range(nuv)]
        for i in range(self.nv):
            o = i * self.stride
            self.pos.append(struct.unpack_from('<3f', v, o))
            no = o + (28 if self.skinned else 12)
            b = v[no:no + 3]
            self.nrm.append(tuple(c / 127.5 - 1 for c in (b[2], b[1], b[0])))
            for k in range(nuv):
                self.uvs[k].append(struct.unpack_from('<2f', v, o + base + 8 * k))

    @property
    def shader(self):
        return self.mat.str('ShaderName') if self.mat else None

    def textures(self):
        if not self.mat:
            return {}
        return {c.name: c.value.decode('latin-1') for c in self.mat.children if c.kind == 1 and c.name.startswith('TexS')}


def load(fs, ref):
    if os.path.isfile(ref):
        data, p = open(ref, 'rb').read(), ref
    else:
        p = fs.path(ref) or next(iter(fs.glob('.VDF', '.CHV', contains=ref)), None)
        if not p:
            raise SystemExit('mesh not found: %s' % ref)
        data = fs.read(p)
    meshes = []

    def walk(n):
        for c in n.containers():
            if c.get('Vertexes') is not None and c.get('Faces') is not None and c.int('NumVertexes'):
                meshes.append(Mesh(c))
            walk(c)
    walk(C.tree(data)[0])
    return p, meshes


def cmd_find(fs, a):
    hits = fs.glob('.VDF', '.CHV', contains=a.pattern)
    for p in hits[:a.limit]:
        print('%-20s %s' % (fs.where(p), p))
    if len(hits) > a.limit:
        print('... %d more (--limit)' % (len(hits) - a.limit))


def cmd_info(fs, a):
    p, meshes = load(fs, a.ref)
    print(p)
    for m in meshes:
        print('mesh %-24s %6d verts %6d tris  stride %d%s  LOD %d  UV sets %d' % (
            repr(m.name), m.nv, len(m.indices) // 3, m.stride, ' skinned' if m.skinned else '', m.lod, len(m.uvs)))
        if m.mat:
            roles = T.slot_roles(m.shader)
            print('  material %r  shader %s' % (m.mat.str('Name'), m.shader))
            for slot, tex in sorted(m.textures().items()):
                found = fs.resolve(tex)
                print('    %-6s %-40s %-42s %s' % (slot, tex, roles.get(slot, '?'), '' if found else 'MISSING'))


# ---------------------------------------------------------------------------------------------- glTF
def _pad(b, fill=b'\0'):
    return b + fill * ((4 - len(b) % 4) % 4)


def write_glb(path, meshes, images):
    """meshes: [(Mesh, material index or None)]; images: [(name, [(kind, png bytes)], alpha cut-out)] per material."""
    bin_ = bytearray()
    views, accs = [], []

    def add(data, target=None):
        off = len(bin_)
        bin_.extend(_pad(data))
        views.append({'buffer': 0, 'byteOffset': off, 'byteLength': len(data), **({'target': target} if target else {})})
        return len(views) - 1

    def acc(data, ctype, count, typ, mn=None, mx=None, target=34962):
        a = {'bufferView': add(data, target), 'componentType': ctype, 'count': count, 'type': typ}
        if mn is not None:
            a['min'], a['max'] = mn, mx
        accs.append(a)
        return len(accs) - 1

    gl_images, textures, materials, mat_of = [], [], [], {}
    for name, slots, cutout in images:
        mat = {'name': name, 'pbrMetallicRoughness': {'metallicFactor': 0.0, 'roughnessFactor': 0.8}}
        if cutout:
            mat['alphaMode'] = 'MASK'
        for kind, png in slots:
            gl_images.append({'bufferView': add(png), 'mimeType': 'image/png'})
            textures.append({'source': len(gl_images) - 1})
            if kind == 'base':
                mat['pbrMetallicRoughness']['baseColorTexture'] = {'index': len(textures) - 1}
            elif kind == 'normal':
                mat['normalTexture'] = {'index': len(textures) - 1}
        materials.append(mat)

    nodes, gmeshes = [], []
    for m, mi in meshes:
        P = [(x, y, -z) for x, y, z in m.pos]
        N = [(x, y, -z) for x, y, z in m.nrm]
        idx = []
        for t in range(0, len(m.indices) - 2, 3):
            idx += [m.indices[t], m.indices[t + 2], m.indices[t + 1]]
        attrs = {
            'POSITION': acc(struct.pack('<%df' % (3 * len(P)), *[c for p in P for c in p]), 5126, len(P), 'VEC3',
                            [min(p[i] for p in P) for i in range(3)], [max(p[i] for p in P) for i in range(3)]),
            'NORMAL': acc(struct.pack('<%df' % (3 * len(N)), *[c for n in N for c in n]), 5126, len(N), 'VEC3'),
        }
        for k, uv in enumerate(m.uvs[:2]):
            attrs['TEXCOORD_%d' % k] = acc(struct.pack('<%df' % (2 * len(uv)), *[c for u, v in uv for c in (u, 1.0 - v)]),
                                           5126, len(uv), 'VEC2')
        big = len(P) > 65535
        ind = acc(struct.pack('<%d%s' % (len(idx), 'I' if big else 'H'), *idx), 5125 if big else 5123, len(idx),
                  'SCALAR', target=34963)
        prim = {'attributes': attrs, 'indices': ind}
        if mi is not None:
            prim['material'] = mi
        gmeshes.append({'name': m.name, 'primitives': [prim]})
        nodes.append({'name': m.name or 'mesh', 'mesh': len(gmeshes) - 1})

    gltf = {'asset': {'version': '2.0', 'generator': 'AAMT tw2mesh.py'}, 'scene': 0,
            'scenes': [{'nodes': list(range(len(nodes)))}], 'nodes': nodes, 'meshes': gmeshes,
            'accessors': accs, 'bufferViews': views, 'buffers': [{'byteLength': len(bin_)}]}
    if materials:
        gltf['materials'] = materials
    if gl_images:
        gltf['images'], gltf['textures'] = gl_images, textures
    js = _pad(json.dumps(gltf, separators=(',', ':')).encode(), b' ')
    out = struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(bin_))
    out += struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(bin_), 0x004E4942) + bytes(bin_)
    open(path, 'wb').write(out)


def _png(img):
    b = io.BytesIO()
    img.save(b, 'PNG')
    return b.getvalue()


def material_images(fs, m, cache):
    """[(kind, png bytes)] for a mesh's base colour and normal map, and whether its shader cuts by alpha."""
    out = []
    tex = m.textures()
    sb = T.shader_base(m.shader)
    for slot, kind in (('TexS0', 'base'), ('TexS1', 'normal')):
        ref = tex.get(slot)
        p = fs.resolve(ref) if ref else None
        if not p:
            continue
        if p not in cache:
            cache[p] = None
            try:
                img = T.decode(fs.read(p))
            except Exception as exc:
                print('  cannot decode %s: %s' % (p, exc), file=sys.stderr)
                continue
            if kind == 'normal':
                pk = 'AG' if sb in T.NORMAL_AG else 'RGB' if sb in T.NORMAL_RGB else T.detect_packing(img, p)
                cache[p] = _png(T.unpack_normal(img, pk)[0].convert('RGB')) if pk else None
            else:
                cache[p] = _png(img if sb in T.ALPHA_CUT else img.convert('RGB'))
        if cache[p]:
            out.append((kind, cache[p]))
    return out, sb in T.ALPHA_CUT


def cmd_export(fs, a):
    p, meshes = load(fs, a.ref)
    if not meshes:
        raise SystemExit('%s has no exportable meshes (face morph targets and helpers are skipped)' % p)
    out = a.out or os.path.join(C.OUTPUT, 'meshes', os.path.splitext(C.safe_name(p))[0] + '.glb')
    C.ensure_dir(os.path.dirname(os.path.abspath(out)))
    mats, key_of, cache, pairs = [], {}, {}, []
    for m in meshes:
        mi = None
        if m.mat and not a.no_textures:
            key = (m.shader, tuple(sorted(m.textures().items())))
            if key not in key_of:
                slots, cut = material_images(fs, m, cache)
                mats.append((m.mat.str('Name') or 'material', slots, cut))
                key_of[key] = len(mats) - 1
            mi = key_of[key]
        pairs.append((m, mi))
    write_glb(out, pairs, mats)
    print('%s -> %s  (%d meshes, %d materials)' % (p, out, len(pairs), len(mats)))


# ---------------------------------------------------------------------------------------------- UV layouts
def cmd_uvmap(fs, a):
    p, meshes = load(fs, a.ref)
    out = a.out or os.path.join(C.OUTPUT, 'uv', os.path.splitext(C.safe_name(p))[0])
    C.ensure_dir(out)
    groups = {}
    for m in meshes:
        tex = m.textures().get('TexS0') or m.name or 'mesh'
        groups.setdefault(tex, []).append(m)
    for tex, ms in groups.items():
        tp = fs.resolve(tex) if tex.lower().endswith('.dds') else None
        if tp:
            base = T.decode(fs.read(tp)).convert('RGB')
            size = (a.size, a.size) if a.size else base.size
            img = base.resize(size, Image.LANCZOS).point(lambda v: v // 2)
        else:
            size = (a.size or 1024,) * 2
            img = Image.new('RGB', size, (24, 24, 24))
        d = ImageDraw.Draw(img)
        W, H = size
        for m in ms:
            if not m.uvs:
                continue
            uv = m.uvs[0]
            for t in range(0, len(m.indices) - 2, 3):
                pts = [uv[m.indices[t + k]] for k in range(3)]
                xy = [(u * W, (1.0 - v) * H) for u, v in pts]
                d.polygon(xy, outline=(255, 210, 60))
        name = os.path.splitext(C.safe_name(tex))[0]
        dst = os.path.join(out, name + '_uv.png')
        img.save(dst)
        print('%s: %d meshes on %s -> %s' % (p, len(ms), tex, dst))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('find'); s.add_argument('pattern'); s.add_argument('--limit', type=int, default=60)
    s = sub.add_parser('info'); s.add_argument('ref')
    s = sub.add_parser('export'); s.add_argument('ref'); s.add_argument('out', nargs='?')
    s.add_argument('--no-textures', action='store_true')
    s = sub.add_parser('uvmap'); s.add_argument('ref'); s.add_argument('--out'); s.add_argument('--size', type=int)
    argv = C.take_stock_flag(list(sys.argv[1:] if argv is None else argv))
    if not argv:
        print(__doc__); return 2
    a = ap.parse_args(argv)
    fs = C.GameFS()
    {'find': cmd_find, 'info': cmd_info, 'export': cmd_export, 'uvmap': cmd_uvmap}[a.cmd](fs, a)
    return 0


if __name__ == '__main__':
    sys.exit(main())
