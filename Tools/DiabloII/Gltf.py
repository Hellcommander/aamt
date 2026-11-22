"""A small glTF 2.0 reader and writer for MeshImport.py: geometry, UVs, the skin (joint names,
weights, bind matrices) and the material's pictures. trimesh reads glTF geometry too, but drops
the rig, and the rig is the point here.

    model = Gltf.load_model('boar.glb')
    model.positions / normals / uvs / triangles      numpy arrays; UVs with v down, as glTF and the game have them
    model.joint_names, model.joints (N x 4 indices into the names), model.weights (N x 4)   or None
    model.rig         {joint name: (parent joint name or None, 4 x 4 bind matrix, row vectors, in model space)}
    model.images      {'albedo' | 'normal' | 'orm' | 'occlusion': PIL image}
    model.has_uv      False when the file has no UVs (uvs are zeros then); model.colours N x 3 (0..255) or None
    model.rest        {joint name: 4 x 4 local matrix against its parent joint, row vectors}
    model.clips       {clip name: duration in seconds}; model.pose(clip, time) -> {joint: 4 x 4 local}

    Gltf.write_rigged(path, positions, normals, uvs, triangles, joints, weights, bones, albedo_png)
        a skinned .glb: bones = [(name, parent index, 4 x 4 local matrix, 4 x 4 inverse bind matrix)], row vectors

Read: .glb and .gltf (external or data-URI buffers and pictures), triangle primitives, every mesh
node of the default scene joined into one mesh, and the animations of the skin's joints (linear
and step; a cubic spline is read through its key values). Not read: sparse accessors, morph
targets, animated nodes above the joints, Draco or meshopt compression (export without it).

Written to glTF 2.0 (Khronos specification 2.0.1). Checked 2026-11-19 against Blender 5.2.3 LTS:
its importer opens a file from write_rigged (armature, vertex groups, texture) and a file it
exports again (export_yup on, the default) reads back here with the same joint names and weights.
"""
import base64
import io
import json
import os
import struct

import numpy as np

_COMPONENT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
_WIDTH = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


class File:
    def __init__(self, path):
        self.folder = os.path.dirname(os.path.abspath(path))
        with open(path, 'rb') as f:
            raw = f.read()
        self.binary = None
        if raw[:4] == b'glTF':
            at = 12
            while at < len(raw):
                size, kind = struct.unpack_from('<II', raw, at)
                chunk = raw[at + 8:at + 8 + size]
                if kind == 0x4E4F534A:
                    self.doc = json.loads(chunk.decode('utf-8'))
                elif kind == 0x004E4942 and self.binary is None:
                    self.binary = chunk
                at += 8 + size
        else:
            self.doc = json.loads(raw.decode('utf-8-sig'))
        for used in self.doc.get('extensionsRequired', []):
            if 'draco' in used.lower() or 'meshopt' in used.lower():
                raise ValueError(f'the file is compressed ({used}); export it without mesh compression')
        self._buffers = {}

    def _uri(self, uri):
        if uri.startswith('data:'):
            return base64.b64decode(uri.split(',', 1)[1])
        with open(os.path.join(self.folder, uri.replace('%20', ' ')), 'rb') as f:
            return f.read()

    def buffer(self, index):
        if index not in self._buffers:
            entry = self.doc['buffers'][index]
            self._buffers[index] = self._uri(entry['uri']) if 'uri' in entry else self.binary
        return self._buffers[index]

    def view(self, index):
        view = self.doc['bufferViews'][index]
        start = view.get('byteOffset', 0)
        return self.buffer(view['buffer'])[start:start + view['byteLength']], view.get('byteStride')

    def accessor(self, index):
        a = self.doc['accessors'][index]
        if 'sparse' in a:
            raise ValueError('sparse accessors are not read')
        kind, width, count = np.dtype(_COMPONENT[a['componentType']]), _WIDTH[a['type']], a['count']
        data, stride = self.view(a['bufferView'])
        start = a.get('byteOffset', 0)
        size = kind.itemsize * width
        if stride and stride != size:
            rows = np.frombuffer(data, dtype=np.uint8, count=(count - 1) * stride + size, offset=start)
            picked = np.lib.stride_tricks.as_strided(rows, (count, size), (stride, 1))
            out = np.ascontiguousarray(picked).view(kind).reshape(count, width)
        else:
            out = np.frombuffer(data, dtype=kind, count=count * width, offset=start).reshape(count, width)
        out = out.astype(np.float64) if kind.kind == 'f' else out.astype(np.int64)
        if a.get('normalized') and kind.kind != 'f':
            out = out / float(np.iinfo(kind).max)
        return out

    def image(self, texture_info):
        from PIL import Image
        if not texture_info:
            return None
        source = self.doc['textures'][texture_info['index']].get('source')
        if source is None:
            return None
        entry = self.doc['images'][source]
        data = self._uri(entry['uri']) if 'uri' in entry else self.view(entry['bufferView'])[0]
        image = Image.open(io.BytesIO(data))
        image.load()
        return image


def _local(node):
    """A node's transform as a 4 x 4 for row vectors."""
    if 'matrix' in node:
        return np.array(node['matrix'], dtype=np.float64).reshape(4, 4)      # column-major of the column form = row form
    m = np.eye(4)
    x, y, z, w = node.get('rotation', [0, 0, 0, 1])
    rotation = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w)],
                         [2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w)],
                         [2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y)]])
    m[:3, :3] = np.diag(node.get('scale', [1, 1, 1])) @ rotation
    m[3, :3] = node.get('translation', [0, 0, 0])
    return m


def _trs_matrix(translation, rotation, scale):
    m = np.eye(4)
    x, y, z, w = rotation
    turn = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w)],
                     [2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w)],
                     [2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y)]])
    m[:3, :3] = np.diag(scale) @ turn
    m[3, :3] = translation
    return m


def _trs_of(node):
    """(translation, rotation, scale) of a node; a matrix node is taken apart (no shear)."""
    if 'matrix' not in node:
        return (np.array(node.get('translation', [0, 0, 0]), dtype=np.float64),
                np.array(node.get('rotation', [0, 0, 0, 1]), dtype=np.float64),
                np.array(node.get('scale', [1, 1, 1]), dtype=np.float64))
    m = np.array(node['matrix'], dtype=np.float64).reshape(4, 4)
    scale = np.linalg.norm(m[:3, :3], axis=1)
    return m[3, :3].copy(), _quaternion(m[:3, :3] / scale[:, None]), scale


def _quaternion(rows):
    """Quaternion (x, y, z, w) of a rotation matrix for row vectors."""
    m = np.asarray(rows).T
    trace = m[0, 0] + m[1, 1] + m[2, 2]
    if trace > 0:
        k = np.sqrt(trace + 1.0) * 2
        q = [(m[2, 1] - m[1, 2]) / k, (m[0, 2] - m[2, 0]) / k, (m[1, 0] - m[0, 1]) / k, 0.25 * k]
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        k = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        q = [0.25 * k, (m[0, 1] + m[1, 0]) / k, (m[0, 2] + m[2, 0]) / k, (m[2, 1] - m[1, 2]) / k]
    elif m[1, 1] > m[2, 2]:
        k = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        q = [(m[0, 1] + m[1, 0]) / k, 0.25 * k, (m[1, 2] + m[2, 1]) / k, (m[0, 2] - m[2, 0]) / k]
    else:
        k = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        q = [(m[0, 2] + m[2, 0]) / k, (m[1, 2] + m[2, 1]) / k, 0.25 * k, (m[1, 0] - m[0, 1]) / k]
    q = np.array(q)
    return q / np.linalg.norm(q)


def _sample(times, values, t, mode, rotation):
    if mode == 'CUBICSPLINE':
        values = values.reshape(len(times), 3, -1)[:, 1]
    if t <= times[0]:
        return values[0]
    if t >= times[-1]:
        return values[-1]
    k = int(np.searchsorted(times, t, side='right')) - 1
    if mode == 'STEP':
        return values[k]
    f = (t - times[k]) / max(times[k + 1] - times[k], 1e-12)
    a, b = values[k], values[k + 1]
    if rotation:
        if float(a @ b) < 0:
            b = -b
        out = a + (b - a) * f
        return out / np.linalg.norm(out)
    return a + (b - a) * f


class Model:
    def pose(self, clip, time):
        """{joint name: 4 x 4 local matrix against its parent joint} at a moment of a clip."""
        tracks = self._tracks[clip]
        out = {}
        for name, (trs, above) in self._joints.items():
            parts = list(trs)
            for slot, key in enumerate(('translation', 'rotation', 'scale')):
                if (name, key) in tracks:
                    times, values, mode = tracks[(name, key)]
                    parts[slot] = _sample(times, values, time, mode, key == 'rotation')
            local = _trs_matrix(*parts)
            out[name] = local if above is None else local @ above
        return out


def load_model(path):
    f = File(path)
    doc = f.doc
    nodes = doc.get('nodes', [])
    parent = {}
    for index, node in enumerate(nodes):
        for child in node.get('children', []):
            parent[child] = index
    world = {}

    def world_of(index):
        if index not in world:
            local = _local(nodes[index])
            world[index] = local @ world_of(parent[index]) if index in parent else local
        return world[index]

    out = Model()
    positions, normals, uvs, triangles, joints, weights = [], [], [], [], [], []
    out.joint_names, out.rig, out.images = None, {}, {}
    out.has_uv, out.rest, out.clips, out._tracks, out._joints = True, {}, {}, {}, {}
    colours = []
    skin_used = None
    base = 0
    for index, node in enumerate(nodes):
        if 'mesh' not in node:
            continue
        skinned = 'skin' in node
        if skinned:
            if skin_used is not None and skin_used != node['skin']:
                raise ValueError('the file has meshes on different skins; join them onto one armature')
            skin_used = node['skin']
        for primitive in doc['meshes'][node['mesh']]['primitives']:
            if primitive.get('mode', 4) != 4:
                continue
            attributes = primitive['attributes']
            p = f.accessor(attributes['POSITION'])
            n = f.accessor(attributes['NORMAL']) if 'NORMAL' in attributes else np.zeros_like(p)
            t = f.accessor(primitive['indices']).reshape(-1, 3) if 'indices' in primitive else np.arange(len(p)).reshape(-1, 3)
            if not skinned:
                m = world_of(index)
                p = p @ m[:3, :3] + m[3, :3]
                n = n @ np.linalg.inv(m[:3, :3]).T
                if np.linalg.det(m[:3, :3]) < 0:
                    t = t[:, ::-1]
            positions.append(p)
            normals.append(n)
            if 'TEXCOORD_0' in attributes:
                uvs.append(f.accessor(attributes['TEXCOORD_0'])[:, :2])
            else:
                uvs.append(np.zeros((len(p), 2)))
                out.has_uv = False
            if 'COLOR_0' in attributes:
                shade = f.accessor(attributes['COLOR_0'])[:, :3].astype(np.float64)
                colours.append(shade * 255.0 if shade.max() <= 1.0 else shade)
            else:
                colours.append(None)
            triangles.append(t + base)
            if skinned and 'JOINTS_0' in attributes:
                joints.append(f.accessor(attributes['JOINTS_0']))
                weights.append(f.accessor(attributes['WEIGHTS_0']).astype(np.float64))
            elif skinned:
                raise ValueError('a skinned mesh has no weights')
            base += len(p)
            material = doc['materials'][primitive['material']] if 'material' in primitive else {}
            pbr = material.get('pbrMetallicRoughness', {})
            for key, info in (('albedo', pbr.get('baseColorTexture')), ('orm', pbr.get('metallicRoughnessTexture')),
                              ('normal', material.get('normalTexture')), ('occlusion', material.get('occlusionTexture'))):
                if key not in out.images and info:
                    picture = f.image(info)
                    if picture is not None:
                        out.images[key] = picture
    if not positions:
        raise ValueError(f'{path}: no triangle mesh')
    if joints and len(joints) != len(positions):
        raise ValueError('some meshes of the file are skinned and some are not; join them onto the armature')
    out.positions, out.uvs, out.triangles = np.concatenate(positions), np.concatenate(uvs), np.concatenate(triangles)
    normal = np.concatenate(normals)
    missing = np.linalg.norm(normal, axis=1) < 1e-6
    if missing.any():
        face = np.cross(out.positions[out.triangles[:, 1]] - out.positions[out.triangles[:, 0]],
                        out.positions[out.triangles[:, 2]] - out.positions[out.triangles[:, 0]])
        summed = np.zeros_like(normal)
        for k in range(3):
            np.add.at(summed, out.triangles[:, k], face)
        normal[missing] = summed[missing]
    length = np.linalg.norm(normal, axis=1, keepdims=True)
    length[length == 0] = 1.0
    out.normals = normal / length
    out.colours = np.concatenate(colours) if colours and all(c is not None for c in colours) else None
    out.joints = out.weights = None
    if joints:
        skin = doc['skins'][skin_used]
        out.joint_names = [nodes[j].get('name', f'joint_{j}') for j in skin['joints']]
        out.joints, out.weights = np.concatenate(joints), np.concatenate(weights)
        inverse = f.accessor(skin['inverseBindMatrices']).reshape(-1, 4, 4) if 'inverseBindMatrices' in skin else None
        is_joint = {j: k for k, j in enumerate(skin['joints'])}
        for k, j in enumerate(skin['joints']):
            up = parent.get(j)
            while up is not None and up not in is_joint:
                up = parent.get(up)
            bind = np.linalg.inv(inverse[k]) if inverse is not None else world_of(j)
            out.rig[out.joint_names[k]] = (out.joint_names[is_joint[up]] if up is not None else None, bind)
            # What lies between a joint and the joint above it (an armature node, a helper) is
            # taken as standing still and folded into the joint's local matrix.
            direct = parent.get(j)
            if direct is None:
                above = None
            elif up is None:
                above = world_of(direct)
            elif direct == up:
                above = None
            else:
                above = world_of(direct) @ np.linalg.inv(world_of(up))
            out._joints[out.joint_names[k]] = (_trs_of(nodes[j]), above)
            local = _local(nodes[j])
            out.rest[out.joint_names[k]] = local if above is None else local @ above
        for number, animation in enumerate(doc.get('animations', [])):
            name = animation.get('name') or f'clip_{number}'
            tracks = {}
            end = 0.0
            for channel in animation['channels']:
                target = channel['target']
                if target.get('node') not in is_joint or target['path'] not in ('translation', 'rotation', 'scale'):
                    continue
                sampler = animation['samplers'][channel['sampler']]
                times = f.accessor(sampler['input']).reshape(-1).astype(np.float64)
                values = f.accessor(sampler['output']).astype(np.float64)
                tracks[(out.joint_names[is_joint[target['node']]], target['path'])] = (times, values, sampler.get('interpolation', 'LINEAR'))
                end = max(end, float(times[-1]))
            if tracks:
                out._tracks[name] = tracks
                out.clips[name] = end
    return out


def write_rigged(path, positions, normals, uvs, triangles, joints, weights, bones, albedo_png=None, animations=None):
    """A skinned .glb. bones: [(name, parent index or -1, local 4 x 4, inverse bind 4 x 4)], row vectors.
    animations: {clip name: {bone number: {'rotation' | 'translation' | 'scale': (times, values)}}}."""
    blob = bytearray()
    views, accessors = [], []

    def add(array, component, kind, target=None, bounds=False, normalized=False):
        while len(blob) % 4:
            blob.append(0)
        raw = np.ascontiguousarray(array).tobytes()
        view = {'buffer': 0, 'byteOffset': len(blob), 'byteLength': len(raw)}
        if target:
            view['target'] = target
        views.append(view)
        blob.extend(raw)
        entry = {'bufferView': len(views) - 1, 'componentType': component, 'count': len(array), 'type': kind}
        if bounds:
            entry['min'], entry['max'] = array.min(0).tolist(), array.max(0).tolist()
        if normalized:
            entry['normalized'] = True
        accessors.append(entry)
        return len(accessors) - 1

    w = np.asarray(weights, dtype=np.float32)
    w = w / np.maximum(w.sum(1, keepdims=True), 1e-9)
    attributes = {'POSITION': add(np.asarray(positions, dtype=np.float32), 5126, 'VEC3', 34962, True),
                  'NORMAL': add(np.asarray(normals, dtype=np.float32), 5126, 'VEC3', 34962),
                  'TEXCOORD_0': add(np.asarray(uvs, dtype=np.float32), 5126, 'VEC2', 34962),
                  'JOINTS_0': add(np.asarray(joints, dtype=np.uint16), 5123, 'VEC4', 34962),
                  'WEIGHTS_0': add(w, 5126, 'VEC4', 34962)}
    indices = add(np.asarray(triangles, dtype=np.uint32).reshape(-1), 5125, 'SCALAR', 34963)
    inverse = add(np.array([b[3] for b in bones], dtype=np.float32).reshape(-1, 16), 5126, 'MAT4')
    nodes = [{'name': 'body', 'mesh': 0, 'skin': 0}]
    for name, _, local, _ in bones:
        local = np.asarray(local, dtype=np.float64)
        scale = np.linalg.norm(local[:3, :3], axis=1)
        nodes.append({'name': name, 'translation': [float(v) for v in local[3, :3]],
                      'rotation': [float(v) for v in _quaternion(local[:3, :3] / scale[:, None])],
                      'scale': [float(v) for v in scale]})
    roots = []
    for k, (_, up, _, _) in enumerate(bones):
        if up < 0:
            roots.append(k + 1)
        else:
            nodes[up + 1].setdefault('children', []).append(k + 1)
    material = {'name': 'body', 'pbrMetallicRoughness': {'metallicFactor': 0.0, 'roughnessFactor': 0.8}}
    doc = {'asset': {'version': '2.0', 'generator': 'AAMT MeshImport'}, 'scene': 0, 'scenes': [{'nodes': [0] + roots}],
           'nodes': nodes, 'meshes': [{'name': 'body', 'primitives': [{'attributes': attributes, 'indices': indices, 'material': 0}]}],
           'skins': [{'joints': list(range(1, len(bones) + 1)), 'inverseBindMatrices': inverse}], 'materials': [material]}
    if animations:
        doc['animations'] = []
        for clip, tracks in animations.items():
            entry = {'name': clip, 'samplers': [], 'channels': []}
            for bone, paths in tracks.items():
                for key, (times, values) in paths.items():
                    times = np.asarray(times, dtype=np.float32).reshape(-1, 1)
                    stamp = add(times, 5126, 'SCALAR', bounds=True)
                    data = add(np.asarray(values, dtype=np.float32), 5126, 'VEC4' if key == 'rotation' else 'VEC3')
                    entry['samplers'].append({'input': stamp, 'output': data, 'interpolation': 'LINEAR'})
                    entry['channels'].append({'sampler': len(entry['samplers']) - 1, 'target': {'node': int(bone) + 1, 'path': key}})
            doc['animations'].append(entry)
    if albedo_png:
        while len(blob) % 4:
            blob.append(0)
        views.append({'buffer': 0, 'byteOffset': len(blob), 'byteLength': len(albedo_png)})
        blob.extend(albedo_png)
        doc['images'] = [{'bufferView': len(views) - 1, 'mimeType': 'image/png'}]
        doc['textures'] = [{'source': 0}]
        material['pbrMetallicRoughness']['baseColorTexture'] = {'index': 0}
    while len(blob) % 4:
        blob.append(0)
    doc.update({'buffers': [{'byteLength': len(blob)}], 'bufferViews': views, 'accessors': accessors})
    text = json.dumps(doc, separators=(',', ':')).encode('utf-8')
    text += b' ' * (-len(text) % 4)
    with open(path, 'wb') as f:
        f.write(struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(text) + 8 + len(blob)))
        f.write(struct.pack('<II', len(text), 0x4E4F534A) + text)
        f.write(struct.pack('<II', len(blob), 0x004E4942) + bytes(blob))
