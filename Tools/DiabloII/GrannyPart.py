"""Cut a part out of a monster's body mesh and write it as a standalone mesh model.

Made so a monster's missiles can be the very things it carries: a quill taken
off the Spike Giant's back becomes the mesh its quill missiles draw, with the
body's own UVs, so the body's textures fit it and a launched quill is a copy of
a quill on its back.

    part = GrannyPart.cut(body_model_path, 'spike_', which='largest')   # or which=34 (joint number), or 'all'
    GrannyPart.write_static(donor_static_model_bytes, part, out_path, scale=1.86)

`cut` takes the vertices that follow one joint (the triangles that lie entirely
within them), and lays the part out the way the game's quill missile mesh is:
long along X with the root at -X and the tip at +X, centred on its length.
`write_static` puts that geometry into a copy of an existing static mesh model
(its skeleton of one bone, material slot and settings are kept) and writes it
with Granny.py's writer. Name the file `<name>_lod0.model`; definitions and
effects refer to it as `<name>.model`, and a model at a new path needs an entry
in the mod's model index (ModelLodDesc.py).

Command line:
    python GrannyPart.py quill --game <D2R> --body <body _lod0.model> --out <.../name_lod0.model>
                               [--prefix spike_] [--which largest] [--scale 1.0]
                               [--donor hd/vfx/meshes/fx_mesh_quillrat_spike_lod0.model]
"""
import argparse
import copy
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import Granny  # noqa: E402
import GrannyMesh  # noqa: E402
import GrannyPreview  # noqa: E402


class Part:
    def __init__(self, positions, normals, tangents, uvs, triangles, source):
        self.positions, self.normals, self.tangents, self.uvs, self.triangles, self.source = positions, normals, tangents, uvs, triangles, source

    def length(self):
        return float(np.ptp(self.positions[:, 0]))

    def radius(self):
        return float(np.linalg.norm(self.positions[:, 1:], axis=1).max())


def _number(name, prefix):
    digits = ''.join(ch for ch in name[len(prefix):] if ch.isdigit())
    return int(digits) if digits else 0


def cut(model_path, prefix='spike_', which='largest'):
    """The part of the first mesh that follows one joint whose name starts with `prefix`."""
    mesh = GrannyMesh.Model(model_path).meshes[0]
    positions = mesh.positions()
    weights, indices = mesh.weights()
    triangles = GrannyPreview.load_meshes(model_path)[0][2]
    normals = mesh._column('Normal', 4, np.int8).astype(np.float64)[:, :3] / 127.0
    tangent_raw = mesh._column('Tangent', 4, np.int8).astype(np.float64)
    uvs = mesh._column('TextureCoordinates0', 4, '<f2').astype(np.float64)
    bones, _ = GrannyPreview.load_bones(model_path)
    owner = indices[np.arange(len(positions)), weights.argmax(1)]
    candidates = []
    for k, name in enumerate(mesh.bones):
        if not name.startswith(prefix) or name not in bones:
            continue
        mine = owner == k
        inside = mine[triangles].all(1)
        if inside.sum() < 4:
            continue
        joint = np.array(bones[name][1])
        rel = positions[mine] - joint
        candidates.append((float(np.linalg.norm(rel, axis=1).max()), name, mine, inside, joint))
    if not candidates:
        raise ValueError(f'no part found for joints starting with "{prefix}"')
    if which == 'largest':
        chosen = max(candidates, key=lambda c: c[0])
    else:
        chosen = next((c for c in candidates if _number(c[1], prefix) == int(which)), None)
        if chosen is None:
            raise ValueError(f'no joint numbered {which}; found {sorted(_number(c[1], prefix) for c in candidates)}')
    _, name, mine, inside, joint = chosen
    rel = positions[mine] - joint
    far = rel[np.linalg.norm(rel, axis=1).argmax()]
    axis = far / np.linalg.norm(far)
    # A frame with X along the part; the other two axes from the part's own spread.
    across = rel - np.outer(rel @ axis, axis)
    second = np.linalg.svd(across, full_matrices=False)[2][0]
    second = second - axis * (second @ axis)
    second /= np.linalg.norm(second)
    third = np.cross(axis, second)
    frame = np.stack([axis, second, third])                 # rows: new X, Y, Z in model space
    local = rel @ frame.T
    local[:, 0] -= (local[:, 0].min() + local[:, 0].max()) / 2      # centred on its length, root at -X
    local[:, 1:] -= local[local[:, 0] < local[:, 0].min() + 0.15 * np.ptp(local[:, 0])][:, 1:].mean(0)
    remap = -np.ones(len(positions), dtype=np.int64)
    remap[mine] = np.arange(int(mine.sum()))
    tangents = np.concatenate([tangent_raw[mine][:, :3] / 127.0 @ frame.T, tangent_raw[mine][:, 3:4] / 127.0], axis=1)
    return Part(local, normals[mine] @ frame.T, tangents, uvs[mine], remap[triangles[inside]], name)


def write_static(donor_bytes, part, out_path, scale=1.0):
    """Writes the part into a copy of a static mesh model (one mesh, positions/normals/tangents/UVs)."""
    source = Granny.read(donor_bytes)
    tree = source.root()
    mesh = tree['Meshes'][0]
    vertices = mesh['PrimaryVertexData']['Vertices']
    names = [m['name'] for m in vertices['$type']]
    if names != ['Position', 'Normal', 'Tangent', 'TextureCoordinates0']:
        raise ValueError(f'the donor mesh has vertex layout {names}; a static mesh with position, normal, tangent and UV is needed')
    positions = part.positions * scale
    reach = float(np.abs(positions).max())
    vertex_scale = max(1.0, reach)
    template = vertices['$items'][0]
    items = []
    quantised = np.clip(np.round(positions / vertex_scale * 32767.0), -32767, 32767).astype(int)
    normals = np.clip(np.round(part.normals * 127.0), -127, 127).astype(int)
    tangents = np.clip(np.round(part.tangents * 127.0), -127, 127).astype(int)
    for k in range(len(positions)):
        items.append({'Position': [int(v) for v in quantised[k]] + [template['Position'][3]],
                      'Normal': [int(v) for v in normals[k]] + [template['Normal'][3]],
                      'Tangent': [int(v) for v in tangents[k]],
                      'TextureCoordinates0': [float(v) for v in part.uvs[k]]})
    vertices['$items'] = items
    topology = mesh['PrimaryTopology']
    Granny.set_mesh_indices(topology, part.triangles.reshape(-1), len(items))
    group = copy.deepcopy(topology['Groups'][0])
    group.update({'TriFirst': 0, 'TriCount': int(len(part.triangles))})
    topology['Groups'] = [group]
    stored = quantised.astype(np.float64) / 32767.0 * vertex_scale
    low, high = stored.min(0), stored.max(0)
    extended = mesh['ExtendedData']['$value']
    extended['bbMin'], extended['bbMax'], extended['VertexScale'] = [float(v) for v in low], [float(v) for v in high], float(vertex_scale)
    # The donor's one bone carries the mesh; its box is in that bone's space.
    bone = tree['Models'][0]['Skeleton']['Bones'][0]
    inverse = np.array(bone['InverseWorldTransform'], dtype=np.float64).reshape(4, 4)
    in_bone = np.concatenate([stored, np.ones((len(stored), 1))], axis=1) @ inverse
    for binding in mesh['BoneBindings']:
        binding['OBBMin'], binding['OBBMax'] = [float(v) for v in in_bone[:, :3].min(0)], [float(v) for v in in_bone[:, :3].max(0)]
    data = Granny.Writer(source.tag, tuple(source.extra_tags)).build(source.describe(source.root_type), tree)
    folder = os.path.dirname(out_path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(data)
    return {'vertices': len(items), 'triangles': int(len(part.triangles)), 'length': float(np.ptp(stored[:, 0])),
            'radius': float(np.linalg.norm(stored[:, 1:], axis=1).max()), 'vertexScale': vertex_scale}


def main(argv):
    parser = argparse.ArgumentParser(description='Cut a part out of a body mesh.')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('quill')
    p.add_argument('--game', default=os.environ.get('D2R_PATH'))
    p.add_argument('--body', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--prefix', default='spike_')
    p.add_argument('--which', default='largest')
    p.add_argument('--scale', type=float, default=1.0)
    p.add_argument('--donor', default='hd/vfx/meshes/fx_mesh_quillrat_spike_lod0.model')
    args = parser.parse_args(argv)
    from d2r_casc import D2RArchive
    with D2RArchive(args.game) as archive:
        donor = archive.read(args.donor)
    part = cut(args.body, args.prefix, args.which)
    info = write_static(donor, part, args.out, args.scale)
    print(f"{part.source}: {info['vertices']} vertices, {info['triangles']} triangles, {info['length']:.2f} long, "
          f"{info['radius']:.2f} radius -> {args.out}")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
