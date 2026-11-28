"""Diablo II: Resurrected `.cloth` files: the simulated cloth of a banner, canopy,
tent or cape (`<model>_lodN.cloth`, next to the `.model` it moves).

Decoded 2026-11-26 on all 545 files of build 3.4.95041; "checked" below means the
stated relation holds in every file that has the data. Little endian. The file
is laid out like the memory it is loaded into: 26 offsets, then the arrays, and
after the last array a block of zeros (working space).

  0x000  26 x u64   offsets of the sections below; in the file they come in the order
                    0-15, 18-25, 16, 17. An empty section shares the next one's offset.
  0x0D0  char[32]   name of the driver mesh, cut at 31 characters. The `.model` beside the file
                    has a mesh of that name with the same N vertices and [3] triangles
                    (all 545 files); it is the mesh the cloth moves.
  0x0F0  f32        2.0 in every file
  0x0F4  22 x u16   counts:
           [0]  particles N               [1]  N rounded up, the length of per-particle arrays (P)
           [2]  pinned particles (the first ones; inverse mass 0)
           [3]  triangles
           [4] [5] [6] [7]  batches of the four distance-constraint groups (sections 18-21)
           [8]  distance constraints, padding included
           [9]  bending constraints
           [10] the largest value in section 5 (steps of the longest path)   checked
           [11] [12] driver-mesh vertices tied to particles = entries of sections 24 / 25:
                N in 515 files, 256 in 5 files with 259 particles, 1 (no table) in 25
           [13] shapes in section 22      [14] shapes in section 23
  0x120  8 bytes    a hash
  0x128  P x u16    per vertex of the driver mesh: the id (section 12) of the particle at that
                    vertex. Checked against the models: every vertex lands on its particle in
                    the 515 files with a full table, and the 256 listed ones in 5 more.
                    The 25 files without a table hold 0xFFFF.

  section  element            what
  0        P x f32[4]         particle position (x, y, z, 0), model space, feet
  1        P x f32[4]         particle normal (unit)                                        checked
  2        P x f32            inverse mass; 0 = pinned (padding entries: 1)                 checked, see 17
  3        P x f32            1 for particles, 0 for padding
  4        P x f32[16]        a 4x4 frame per particle, no translation. Third column = the normal,
                              first column = the direction to the neighbour of section 9 (laid
                              into the surface), second = their cross product                checked
  5        P x u16            steps from the pinned particles (0 = pinned)                  checked
  6        P x f32            length of that path: length[parent] + distance to the parent  checked
  7        P x u16            parent: the next particle on the path (0xFFFF for pinned)     checked
  8        P x u16            the pinned particle the path ends at                          checked
  9        P x u16            one neighbouring particle (shares a triangle)                 checked
  10       P x f32[4]         1 0 0 0
  11       P x u16[4]         section 12 four times over (520 files)
  12       P x u16            the particle's id, the number the table at 0x128 names it by
                              (a permutation in 540 files; on a flat banner it counts along the grid)
  13       [3] x u16[3]       triangles (particle indices)
  14       [8] x u16[2]       distance constraints: the two particles; padding entries are (N, N)
  15       [8] x f32          their rest lengths (padding: 1). All equal the distance in section 0
                              in 280 files; in 260 some differ (never fewer than 76% equal)
  18-21    [4..7] x u16[2]    batches: (first, end) ranges into section 14. Together they cover it
                              exactly; every range is a multiple of 8 long.                 checked
                              Order in section 14: group 20, 21, 19, 18. In a flat banner:
                              20 = diagonals, 21 = pairs two apart (not triangle edges),
                              19 = along x, 18 = along y.
  16       [9] x u16[3]       bending constraints: two particles and the one between them
  17       f32[3] per row     weights of section 16's rows:
                              2 * c * w / sum(|c| * w), c = (1, 1, -2), w = inverse mass    checked
                              Only the first 6 x [9] bytes are filled (half of the 12 x [9] the
                              rows need; with an odd count the last row stops after six bytes),
                              as if the block was sized with the 2-byte index type. The rest,
                              to the end of the file, is zeros.
  22       [13] x 80 bytes    collision capsules (80 in all files): f32 position[3], 0, quaternion
                              xyzw, 1 1 1 0, two radii (equal in every file), length, 1, then
                              u16 0xFFFF, u8 4 and 13 bytes that differ between otherwise equal
                              files (leftover memory)
  23       [14] x 48 bytes    collision shapes (30 in all files): f32 position[3], 0, quaternion
                              xyzw, two sizes (0.3 0.3, 0.3 1 or 1 1; which is which not settled),
                              u16 0xFFFF and leftover bytes
  24       [11] x f32[12]     0 0 0 0, 0 0 0 1, 1 1 1 1 in every file
  25       [11] x u16         0, 1, 2 ... in every file

usage:
  HdCloth.py info   <file> [--game <D2R folder>]
  HdCloth.py to-obj <file> <out.obj> [--game <D2R folder>]     particles and triangles; pinned ones in group "pinned"
  HdCloth.py check  <file> ... [--game <D2R folder>]            the "checked" relations above

Left open: which of the two sizes of a section-23 shape is which, and why some
rest lengths differ from the stored distances. There is no writer: no file built
outside the game's own exporter has been tried in the game.
"""
import argparse
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from HdPhysics import load  # noqa: E402

SECTIONS = 26
GROUPS = {20: 'diagonal', 21: 'skip-one', 19: 'x', 18: 'y'}      # names from flat banners; section -> group


def read(data):
    """-> dict of the decoded arrays (padding removed) plus `sections`, the raw bytes of each."""
    offsets = struct.unpack_from(f'<{SECTIONS}Q', data, 0)
    counts = struct.unpack_from('<22H', data, 0xF4)
    n, padded = counts[0], counts[1]
    if offsets[0] != (0x128 + 2 * n + 15) // 16 * 16 or max(offsets) > len(data):
        raise ValueError('not a .cloth file this tool knows')
    ends = sorted(set(offsets) | {len(data)})
    raw = [data[o:ends[ends.index(o) + 1]] for o in offsets]

    def array(section, dtype, count, width=1):
        a = np.frombuffer(data, dtype, count * width, offsets[section])
        return a.reshape(count, width) if width > 1 else a
    pairs = array(14, '<u2', counts[8], 2)
    real = ~(pairs == n).all(axis=1) if len(pairs) else np.zeros(0, bool)     # padding is exactly (N, N)
    group = np.full(counts[8], -1)
    batches = {}
    for section, index in ((18, 4), (19, 5), (20, 6), (21, 7)):
        batches[section] = array(section, '<u2', counts[index], 2)
        for first, end in batches[section].tolist():
            group[first:end] = section
    weighted = counts[9] // 2
    return {
        'name': data[0xD0:0xF0].split(b'\0')[0].decode('latin1'),
        'counts': counts,
        'positions': array(0, '<f4', padded, 4)[:n, :3],
        'normals': array(1, '<f4', padded, 4)[:n, :3],
        'inverse_mass': array(2, '<f4', padded)[:n],
        'pinned': counts[2],
        'frames': array(4, '<f4', padded, 16)[:n].reshape(n, 4, 4),
        'steps': array(5, '<u2', padded)[:n],
        'path_length': array(6, '<f4', padded)[:n],
        'parent': array(7, '<u2', padded)[:n],
        'root': array(8, '<u2', padded)[:n],
        'neighbour': array(9, '<u2', padded)[:n],
        'triangles': array(13, '<u2', counts[3], 3),
        'constraints': pairs[real],
        'rest_lengths': array(15, '<f4', counts[8])[real],
        'constraint_group': group[real],
        'batches': batches,
        'all_pairs': pairs,
        'bending': array(16, '<u2', counts[9], 3),
        'bending_weights': array(17, '<f4', weighted, 3),
        'shapes_a': array(22, '<f4', counts[13], 20),
        'shapes_b': array(23, '<f4', counts[14], 12),
        'sections': raw,
    }


def problems(c):
    """Which of the relations in the docstring do not hold for a file read with `read`."""
    out = []
    n, pinned = len(c['positions']), c['pinned']
    pos = c['positions'].astype(float)
    if not np.allclose(np.linalg.norm(c['normals'], axis=1), 1, atol=1e-2):
        out.append('normals are not unit length')
    if int((c['inverse_mass'] == 0).sum()) != pinned or (c['inverse_mass'][:pinned] != 0).any():
        out.append('pinned particles are not the leading ones without mass')
    if len(c['triangles']) and c['triangles'].max() >= n:
        out.append('a triangle names a particle that does not exist')
    if len(c['constraints']) and c['constraints'].max() >= n:
        return out + ['a distance constraint names a particle that does not exist']
    free = np.arange(n) >= pinned
    if pinned and free.any():
        parent = c['parent'][free].astype(int)
        if (c['parent'][:pinned] != 0xFFFF).any() or (parent >= n).any():
            out.append('parents')
        else:
            if (c['steps'][free] != c['steps'][parent] + 1).any():
                out.append('steps')
            if not np.allclose(c['path_length'][free], c['path_length'][parent] + np.linalg.norm(pos[free] - pos[parent], axis=1), atol=5e-3):
                out.append('path lengths')
            reached = np.arange(n)
            for _ in range(int(c['steps'].max()) + 1):
                reached = np.where(reached >= pinned, c['parent'].astype(int)[np.minimum(reached, n - 1)], reached)
            if (reached[free] != c['root'][free]).any():
                out.append('roots')
    total = len(c['all_pairs'])
    if total:
        ranges = sorted(r for b in c['batches'].values() for r in b.tolist())
        if ranges[0][0] != 0 or ranges[-1][1] != total or any(a[1] != b[0] for a, b in zip(ranges, ranges[1:])):
            out.append('batches do not cover the constraints exactly')
    if len(c['bending']):
        if c['bending'].max() >= n:
            out.append('a bending constraint names a particle that does not exist')
        else:
            w = c['inverse_mass'][c['bending'][:len(c['bending_weights'])]].astype(float)
            coefficient = np.array([1.0, 1.0, -2.0])
            total_w = (np.abs(coefficient) * w).sum(axis=1, keepdims=True)
            expected = np.where(total_w > 0, 2 * coefficient * w / np.where(total_w > 0, total_w, 1), 0)
            if not np.allclose(expected, c['bending_weights'], atol=3e-3):
                out.append('bending weights')
    if n and (c['neighbour'] < n).all():
        normal = c['normals'].astype(float)
        along = pos[c['neighbour'].astype(int)] - pos
        along -= (along * normal).sum(axis=1, keepdims=True) * normal
        along /= np.maximum(np.linalg.norm(along, axis=1, keepdims=True), 1e-9)
        frame = c['frames'].astype(float)
        if not (np.allclose(frame[:, :3, 2], normal, atol=2e-2) and np.allclose(frame[:, :3, 0], along, atol=3e-2)
                and np.allclose(frame[:, :3, 1], np.cross(normal, along), atol=4e-2)):
            out.append('frames')
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['info', 'to-obj', 'check'])
    ap.add_argument('args', nargs='+')
    ap.add_argument('--game', default=os.environ.get('D2R_PATH'))
    a = ap.parse_args()
    if a.command == 'check':
        failed = 0
        for path in a.args:
            bad = problems(read(load(path, a.game)))
            failed += bool(bad)
            print(('FAIL ' + '; '.join(bad) if bad else 'ok  ') + ' ' + path)
        sys.exit(1 if failed else 0)
    c = read(load(a.args[0], a.game))
    p = c['positions']
    if a.command == 'info':
        print(f"{c['name']}: {len(p)} particles ({c['pinned']} pinned), {len(c['triangles'])} triangles")
        print(f"box {np.round(p.min(axis=0), 3).tolist()} to {np.round(p.max(axis=0), 3).tolist()}")
        groups = ', '.join(f"{int((c['constraint_group'] == s).sum())} {name} in {len(c['batches'][s])} batches"
                           for s, name in GROUPS.items())
        print(f"{len(c['constraints'])} distance constraints: {groups}")
        print(f"{len(c['bending'])} bending constraints, longest path from a pin {float(c['path_length'].max()) if len(p) else 0:.3f} "
              f"({int(c['steps'].max()) if len(p) else 0} steps)")
        print(f"collision shapes: {len(c['shapes_a'])} + {len(c['shapes_b'])}")
        for row in c['shapes_a'].tolist():
            print('  A  at ' + ' '.join(f'{x:.3f}' for x in row[:3]) + '  turn ' + ' '.join(f'{x:.3f}' for x in row[4:8])
                  + '  sizes ' + ' '.join(f'{x:g}' for x in np.round(row[8:16], 4)))
        for row in c['shapes_b'].tolist():
            print('  B  at ' + ' '.join(f'{x:.3f}' for x in row[:3]) + '  turn ' + ' '.join(f'{x:.3f}' for x in row[4:8])
                  + '  sizes ' + ' '.join(f'{x:g}' for x in np.round(row[8:10], 4)))
        print('counts ' + ' '.join(str(x) for x in c['counts'][:15]))
        print('checks: ' + ('; '.join(problems(c)) or 'ok'))
    else:
        if len(a.args) != 2:
            raise SystemExit('to-obj needs <file> <out.obj>')
        pinned = set(range(c['pinned']))
        with open(a.args[1], 'w', encoding='utf-8', newline='\n') as f:
            f.write(f"# {c['name']}: the first {c['pinned']} vertices are pinned\n")
            f.writelines(f'v {x:.6f} {y:.6f} {z:.6f}\n' for x, y, z in p.tolist())
            f.writelines(f'vn {x:.6f} {y:.6f} {z:.6f}\n' for x, y, z in c['normals'].tolist())
            for group, wanted in (('cloth', False), ('pinned', True)):
                faces = [t for t in c['triangles'].tolist() if all(i in pinned for i in t) == wanted]
                if faces:
                    f.write(f'g {group}\n')
                    f.writelines(f'f {i + 1}//{i + 1} {j + 1}//{j + 1} {k + 1}//{k + 1}\n' for i, j, k in faces)
        print(f"{a.args[1]}: {len(p)} vertices, {len(c['triangles'])} triangles")


if __name__ == '__main__':
    main()
