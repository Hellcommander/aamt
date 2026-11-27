"""Diablo II: Resurrected `.physics` files: the collision mesh of a map preset, a
terrain cluster or a model (`terrain.physics`, `<name>_collision.physics`).

A file is one triangle mesh with a bounding-box tree over it. Layout (little
endian), checked on all 3,031 files of game build 3.4.95041:

  0x00  u64 offset of the tree nodes (always 0x30)
  0x08  u64 offset of the vertices
  0x10  u64 offset of the triangles
  0x18  u32 node count
  0x1C  u32 vertex count
  0x20  u32 triangle count
  0x24  u32 depth of the tree (a single leaf = 1)
  0x28  f32 total area of the triangles
  0x2C  u32 0

  node, 32 bytes      f32 min[3], f32 max[3], u32 value, u16 0xFFFF, u8 kind, u8 count
                      kind 0/1/2 = split on x/y/z: children are node i+1 and node i+value
                      kind 3     = leaf: `count` (1-4) triangles starting at triangle `value`
                      boxes are grown by 0.0328 (one centimetre; units are feet)
  vertex, 16 bytes    f32 x, y, z, 0
  triangle, 32 bytes  i32 vertex[3], i32 across[3], u32 0, u16 0xFFFF, u16 0
                      across[e] = the third vertex of the triangle on the other side of
                      edge (vertex[e], vertex[e+1]), or -1 where the mesh ends

usage:
  HdPhysics.py info   <file> [--game <D2R folder>]
  HdPhysics.py to-obj <file> <out.obj> [--game <D2R folder>]
  HdPhysics.py from-obj <in.obj> <out.physics>
  HdPhysics.py check  <file> ... [--game <D2R folder>]

`from-obj` builds a new file (triangles only, its own tree). It reads back with
this tool; the game has not been seen loading one.
"""
import argparse
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MARGIN = 0.0328084
NODE = np.dtype([('min', '<f4', 3), ('max', '<f4', 3), ('value', '<u4'), ('pad', '<u2'), ('kind', 'u1'), ('count', 'u1')])
TRIANGLE = np.dtype([('vertex', '<i4', 3), ('across', '<i4', 3), ('zero', '<u4'), ('ffff', '<u2'), ('flags', '<u2')])


def read(data):
    """-> dict: vertices (N x 3), triangles (M x 3), across (M x 3), nodes (structured), depth, area."""
    nodes_at, vertices_at, triangles_at = struct.unpack_from('<3Q', data, 0)
    node_count, vertex_count, triangle_count, depth = struct.unpack_from('<4I', data, 0x18)
    area = struct.unpack_from('<f', data, 0x28)[0]
    if nodes_at != 0x30 or vertices_at - nodes_at != 32 * node_count or triangles_at - vertices_at != 16 * vertex_count \
            or len(data) - triangles_at != 32 * triangle_count:
        raise ValueError('not a .physics file this tool knows')
    nodes = np.frombuffer(data, NODE, node_count, nodes_at)
    vertices = np.frombuffer(data, '<f4', vertex_count * 4, vertices_at).reshape(-1, 4)[:, :3]
    triangles = np.frombuffer(data, TRIANGLE, triangle_count, triangles_at)
    return {'vertices': vertices, 'triangles': triangles['vertex'], 'across': triangles['across'],
            'nodes': nodes, 'depth': depth, 'area': area}


def across_edges(triangles):
    """For every triangle edge, the third vertex of the triangle on the other side (-1 at a border)."""
    opposite = {}
    for t in triangles:
        for e in range(3):
            opposite[(int(t[e]), int(t[(e + 1) % 3]))] = int(t[(e + 2) % 3])
    return np.array([[opposite.get((int(t[(e + 1) % 3]), int(t[e])), -1) for e in range(3)] for t in triangles],
                    dtype='<i4').reshape(-1, 3)


def mesh_area(vertices, triangles):
    v = vertices.astype(float)
    return float(0.5 * np.linalg.norm(np.cross(v[triangles[:, 1]] - v[triangles[:, 0]],
                                               v[triangles[:, 2]] - v[triangles[:, 0]]), axis=1).sum())


def tree_depth(nodes):
    deepest, stack = 0, [(0, 1)]
    while stack:
        i, d = stack.pop()
        deepest = max(deepest, d)
        if nodes[i]['kind'] != 3:
            stack += [(i + 1, d + 1), (i + int(nodes[i]['value']), d + 1)]
    return deepest


def problems(mesh):
    """What does not hold of a file read with `read` (empty = everything checks)."""
    out = []
    nodes, triangles = mesh['nodes'], mesh['triangles']
    if len(triangles) and (triangles.min() < 0 or triangles.max() >= len(mesh['vertices'])):
        return ['a triangle names a vertex that does not exist']
    # An edge that two triangles run along in the same direction (overlapping triangles: three
    # stock files have them) has no single other side, so those slots are left out.
    used = {}
    for t in triangles:
        for e in range(3):
            key = (int(t[e]), int(t[(e + 1) % 3]))
            used[key] = used.get(key, 0) + 1
    plain = np.array([[used[(int(t[e]), int(t[(e + 1) % 3]))] == 1 and used.get((int(t[(e + 1) % 3]), int(t[e])), 0) <= 1
                       for e in range(3)] for t in triangles], dtype=bool).reshape(-1, 3)
    if not np.array_equal(across_edges(triangles)[plain], mesh['across'][plain]):
        out.append('edge neighbours differ from the mesh')
    if abs(mesh_area(mesh['vertices'], triangles) - mesh['area']) > 1e-3 * max(1.0, mesh['area']):
        out.append('area differs from the mesh')
    if tree_depth(nodes) != mesh['depth']:
        out.append('tree depth differs')
    covered = np.zeros(len(triangles), int)
    for n in nodes[nodes['kind'] == 3]:
        covered[n['value']:n['value'] + n['count']] += 1
    if not (covered == 1).all():
        out.append('leaves do not hold every triangle once')
    return out


def build(vertices, triangles, leaf=4):
    """New file bytes for a triangle mesh. Triangles are reordered so each leaf's are together."""
    vertices = np.asarray(vertices, dtype='<f4').reshape(-1, 3)
    triangles = np.asarray(triangles, dtype='<i4').reshape(-1, 3)
    corners = vertices[triangles]                           # M x 3 x 3
    low, high, centre = corners.min(axis=1), corners.max(axis=1), corners.mean(axis=1)
    nodes, order = [], []

    def make(items, depth):
        index = len(nodes)
        box_min, box_max = low[items].min(axis=0) - MARGIN, high[items].max(axis=0) + MARGIN
        nodes.append(None)
        if len(items) <= leaf:
            nodes[index] = (box_min, box_max, len(order), 3, len(items))
            order.extend(items)
            return depth
        axis = int(np.argmax(box_max - box_min))
        items = sorted(items, key=lambda t: centre[t][axis])
        half = len(items) // 2
        left = make(items[:half], depth + 1)
        right_at = len(nodes)
        right = make(items[half:], depth + 1)
        nodes[index] = (box_min, box_max, right_at - index, axis, 0)
        return max(left, right)

    depth = make(list(range(len(triangles))), 1) if len(triangles) else 0
    triangles = triangles[order]
    node_data = np.zeros(len(nodes), NODE)
    for i, (box_min, box_max, value, kind, count) in enumerate(nodes):
        node_data[i] = (box_min, box_max, value, 0xFFFF, kind, count)
    triangle_data = np.zeros(len(triangles), TRIANGLE)
    triangle_data['vertex'] = triangles
    triangle_data['across'] = across_edges(triangles) if len(triangles) else triangles
    triangle_data['ffff'] = 0xFFFF
    vertex_data = np.zeros((len(vertices), 4), '<f4')
    vertex_data[:, :3] = vertices
    vertices_at = 0x30 + node_data.nbytes
    triangles_at = vertices_at + vertex_data.nbytes
    head = struct.pack('<3Q4IfI', 0x30, vertices_at, triangles_at, len(nodes), len(vertices), len(triangles), depth,
                       mesh_area(vertices, triangles) if len(triangles) else 0.0, 0)
    return head + node_data.tobytes() + vertex_data.tobytes() + triangle_data.tobytes()


def load(path, game=None):
    if os.path.isfile(path):
        with open(path, 'rb') as f:
            return f.read()
    if game:
        from d2r_casc import D2RArchive
        with D2RArchive(game.replace('/', '\\')) as archive:
            data = archive.read(path.replace('\\', '/'))
        if data is not None:
            return data
    raise SystemExit(f'no such file: {path}' + ('' if game else ' (pass --game to read from the game archive)'))


def read_obj(path):
    vertices, triangles = [], []
    with open(path, encoding='utf-8') as f:
        for line in f:
            parts = line.split()
            if parts[:1] == ['v']:
                vertices.append([float(x) for x in parts[1:4]])
            elif parts[:1] == ['f']:
                corner = [int(p.split('/')[0]) for p in parts[1:]]
                corner = [c - 1 if c > 0 else len(vertices) + c for c in corner]
                triangles += [[corner[0], corner[i], corner[i + 1]] for i in range(1, len(corner) - 1)]
    return vertices, triangles


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['info', 'to-obj', 'from-obj', 'check'])
    ap.add_argument('args', nargs='+')
    ap.add_argument('--game', default=os.environ.get('D2R_PATH'))
    a = ap.parse_args()
    if a.command == 'info':
        m = read(load(a.args[0], a.game))
        v = m['vertices']
        print(f"{len(v)} vertices, {len(m['triangles'])} triangles, {len(m['nodes'])} tree nodes, depth {m['depth']}, area {m['area']:.2f}")
        if len(v):
            print(f"box {np.round(v.min(axis=0), 3).tolist()} to {np.round(v.max(axis=0), 3).tolist()}")
        print('checks: ' + ('; '.join(problems(m)) or 'ok'))
    elif a.command == 'to-obj':
        m = read(load(a.args[0], a.game))
        with open(a.args[1], 'w', encoding='utf-8', newline='\n') as f:
            f.writelines(f'v {x:.6f} {y:.6f} {z:.6f}\n' for x, y, z in m['vertices'].tolist())
            f.writelines(f'f {i + 1} {j + 1} {k + 1}\n' for i, j, k in m['triangles'].tolist())
        print(f"{a.args[1]}: {len(m['vertices'])} vertices, {len(m['triangles'])} triangles")
    elif a.command == 'from-obj':
        data = build(*read_obj(a.args[0]))
        bad = problems(read(data))
        if bad:
            raise SystemExit('the built file does not check: ' + '; '.join(bad))
        with open(a.args[1], 'wb') as f:
            f.write(data)
        print(f'{a.args[1]}: {len(data)} bytes')
    else:
        failed = 0
        for path in a.args:
            bad = problems(read(load(path, a.game)))
            failed += bool(bad)
            print(('FAIL ' + '; '.join(bad) if bad else 'ok  ') + ' ' + path)
        sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
