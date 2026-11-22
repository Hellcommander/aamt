"""Reads a Granny file the way the Noesis GR2 reader script (Jayn23, v1.3.5, after Norbyte's
lslib) lays it out, written from reading that script, none of its code run: sections placed
end to end by decompressed size, relocations patched in as 4-byte offsets, type members of
44 bytes. Then compares what that view sees with what the toolkit's own Granny.py sees."""
import struct
import sys
import zlib

MAGIC_LE64 = bytes([0xE5, 0x9B, 0x49, 0x5E, 0x6F, 0x63, 0x1F, 0x14, 0x1E, 0x13, 0xEB, 0xA9, 0x90, 0xBE, 0xED, 0xC4])


def check(path, compare=True):
    """path: a file, or the file's bytes."""
    data = bytes(path) if isinstance(path, (bytes, bytearray)) else open(path, 'rb').read()
    notes, problems = [], []
    if data[:16] != MAGIC_LE64:
        problems.append('magic is not the 64-bit little-endian version 7 one')
    size, fmt = struct.unpack_from('<II', data, 16)
    version, file_size, crc, sec_off, sec_count, type_sec, type_off, root_sec, root_off, tag = struct.unpack_from('<10I', data, 32)
    header_end = 32 + 40 + 16 + (16 if version == 7 else 0)
    if version != 7:
        problems.append(f'version {version}')
    if file_size != len(data):
        problems.append(f'file size field {file_size} against {len(data)} bytes')
    if zlib.crc32(data[header_end:]) != crc:
        problems.append('CRC field does not match the bytes after the header')
    if fmt != 0:
        problems.append(f'format field {fmt}')
    sections, offsets, total = [], [], 0
    for i in range(sec_count):
        s = struct.unpack_from('<11I', data, 32 + sec_off + 44 * i)
        sections.append(s)
        offsets.append(total)
        total += s[3]
    flat = bytearray()
    compressed = False
    for i, (comp, off, dsize, usize, align, s16, s8, rel_off, rel_count, mar_off, mar_count) in enumerate(sections):
        if comp:
            compressed = True
            flat += bytes(usize)
            continue
        if dsize != usize:
            problems.append(f'section {i}: stored size {dsize} is not its unpacked size {usize}')
        if off + dsize > len(data):
            problems.append(f'section {i}: data runs past the end of the file')
        flat += data[off:off + dsize]
    notes.append(f'{sec_count} sections, {total} bytes of data, header {size} bytes, tag 0x{tag:08X}'
                 + (', sections are compressed (the script would hand these to granny2.dll)' if compressed else ''))
    notes.append('section fields (compression, alignment, stop16, stop8, relocations, marshallings): '
                 + ' '.join(f'[{s[0]},{s[4]},{s[5]},{s[6]},{s[8]},{s[10]}]' for s in sections))
    if compressed:
        return notes, problems, None
    patched = high = 0
    for i, s in enumerate(sections):
        rel_off, rel_count = s[7], s[8]
        if rel_count and rel_off + 12 * rel_count > len(data):
            problems.append(f'section {i}: relocation table runs past the end of the file')
            continue
        for k in range(rel_count):
            at, target_sec, target_off = struct.unpack_from('<3I', data, rel_off + 12 * k)
            if at + 8 > s[3] or target_sec >= sec_count or target_off > sections[target_sec][3]:
                problems.append(f'section {i}: relocation {k} points outside its section')
                continue
            where = offsets[i] + at
            if flat[where + 4:where + 8] != b'\0\0\0\0':
                high += 1
            flat[where:where + 4] = struct.pack('<I', offsets[target_sec] + target_off)
            patched += 1
    notes.append(f'{patched} relocations applied')
    if high:
        problems.append(f'{high} pointer slots have non-zero upper bytes (the script writes only the lower four)')
    if any(s[10] for s in sections):
        notes.append('marshalling records present (the script skips them on little-endian files)')

    def string(at):
        end = flat.index(b'\0', at)
        return flat[at:end].decode('latin1')

    def members(at):
        out = []
        while True:
            kind = struct.unpack_from('<I', flat, at)[0]
            if kind == 0:
                return out
            name, definition = struct.unpack_from('<QQ', flat, at + 4)
            width = struct.unpack_from('<I', flat, at + 20)[0]
            out.append((kind, string(name), definition, width))
            at += 44

    root_type = members(offsets[type_sec] + type_off)
    root = offsets[root_sec] + root_off
    notes.append('root members: ' + ', '.join(m[1] for m in root_type))
    seen = {}
    at = root
    for kind, name, definition, width in root_type:
        # Sizes of the member kinds the root uses: 2 reference (8), 3 reference to array (4 + 8),
        # 4 array of references (4 + 8), 5 variant (16), 8 string (8).
        if kind in (3, 4):
            count, pointer = struct.unpack_from('<IQ', flat, at)
            seen[name] = (count, pointer)
            at += 12
        elif kind == 5:
            at += 16
        elif kind in (2, 8):
            if kind == 8:
                pointer = struct.unpack_from('<Q', flat, at)[0]
                seen[name] = string(pointer) if pointer else None
            at += 8
        else:
            problems.append(f'root member {name}: kind {kind} is not one this check sizes')
            break
    view = {'counts': {k: v[0] for k, v in seen.items() if isinstance(v, tuple)}, 'file': seen.get('FromFileName')}
    # Bone names through the flat view: Skeletons[0] -> Name, Bones (count, pointer); a bone starts with its name.
    count, pointer = seen.get('Skeletons', (0, 0))
    if count:
        skeleton = struct.unpack_from('<Q', flat, pointer)[0]
        skeleton_type = members(next(m[2] for m in root_type if m[1] == 'Skeletons'))
        bone_type = members(next(m[2] for m in skeleton_type if m[1] == 'Bones'))
        sizes = {1: None, 2: 8, 3: 12, 4: 12, 5: 16, 7: 20, 8: 8, 9: 68, 10: 4, 19: 4, 20: 4}
        stride = sum((sizes.get(m[0]) or 0) * max(1, m[3]) for m in bone_type)
        bones, first = struct.unpack_from('<IQ', flat, skeleton + 8)
        view['bones'] = [string(struct.unpack_from('<Q', flat, first + stride * k)[0]) for k in range(bones)]
        view['boneStride'] = stride
    # Mesh index arrays through the flat view, read the way the game's mesh loader takes them
    # (Mesh::LoadGeometry, image 95032 0xFA04C0): the 32-bit Indices when filled, else Indices16
    # as unsigned 16-bit; every index must name a vertex of the mesh.
    widths = {1: None, 2: 8, 3: 12, 4: 12, 5: 16, 7: 20, 8: 8, 9: 68, 10: 4, 11: 1, 12: 1, 13: 1, 14: 1,
              15: 2, 16: 2, 17: 2, 18: 2, 19: 4, 20: 4, 21: 2, 22: 8}

    def size(type_at):
        return sum((size(d) if k == 1 else widths[k]) * max(1, wd) for k, _, d, wd in members(type_at))

    def layout(type_at):
        out, o = {}, 0
        for kind, name, definition, width in members(type_at):
            out.setdefault(name, (o, kind, definition))
            o += (size(definition) if kind == 1 else widths[kind]) * max(1, width)
        return out

    view['meshes'] = []
    count, table = seen.get('Meshes', (0, 0))
    if count:
        mesh_layout = layout(next(m[2] for m in root_type if m[1] == 'Meshes'))
        for k in range(count):
            mesh = struct.unpack_from('<Q', flat, table + 8 * k)[0]
            name_ptr = struct.unpack_from('<Q', flat, mesh + mesh_layout['Name'][0])[0]
            vd = struct.unpack_from('<Q', flat, mesh + mesh_layout['PrimaryVertexData'][0])[0]
            topo = struct.unpack_from('<Q', flat, mesh + mesh_layout['PrimaryTopology'][0])[0]
            vertices = struct.unpack_from('<I', flat, vd + layout(mesh_layout['PrimaryVertexData'][2])['Vertices'][0] + 8)[0]
            topo_layout = layout(mesh_layout['PrimaryTopology'][2])
            n32, p32 = struct.unpack_from('<IQ', flat, topo + topo_layout['Indices'][0])
            n16, p16 = struct.unpack_from('<IQ', flat, topo + topo_layout['Indices16'][0])
            ng, pg = struct.unpack_from('<IQ', flat, topo + topo_layout['Groups'][0])
            label = string(name_ptr) if name_ptr else f'mesh {k}'
            index = struct.unpack_from(f'<{n32}i', flat, p32) if n32 else struct.unpack_from(f'<{n16}H', flat, p16) if n16 else ()
            if n32 and n16:
                problems.append(f'{label}: both Indices ({n32}) and Indices16 ({n16}) are filled; the game uses Indices')
            if len(index) % 3:
                problems.append(f'{label}: {len(index)} indices is not a whole number of triangles')
            if index and (max(index) >= vertices or min(index) < 0):
                problems.append(f'{label}: indices reach {min(index)}..{max(index)}, the mesh has {vertices} vertices')
            for g in range(ng):
                _, first, tris = struct.unpack_from('<3i', flat, pg + 12 * g)
                if first < 0 or first + tris > len(index) // 3:
                    problems.append(f'{label}: group {g} covers triangles {first}..{first + tris}, the mesh has {len(index) // 3}')
            if vertices > 65536 and not n32:
                problems.append(f'{label}: {vertices} vertices need 32-bit Indices')
            view['meshes'].append({'name': label, 'vertices': vertices, 'bytesPerIndex': 4 if n32 else 2, 'index': index})
        wide = sum(1 for m in view['meshes'] if m['bytesPerIndex'] == 4)
        notes.append(f'{count} meshes, {sum(m["vertices"] for m in view["meshes"])} vertices, {wide} with 32-bit indices, '
                     f'largest {max(m["vertices"] for m in view["meshes"])} vertices')
    if compare:
        import Granny
        tree = Granny.read(bytes(data)).root()
        mine = {k: len(v) for k, v in tree.items() if isinstance(v, list)}
        for key, value in view['counts'].items():
            if mine.get(key) != value:
                problems.append(f'{key}: the script\'s view counts {value}, Granny.py {mine.get(key)}')
        own_bones = [b['Name'] for b in tree['Skeletons'][0]['Bones']] if tree.get('Skeletons') else []
        if view.get('bones') is not None and view['bones'] != own_bones:
            problems.append(f'bone names differ between the two views ({len(view["bones"])} against {len(own_bones)})')
        notes.append(f'counts agree with Granny.py: {view["counts"]}; {len(own_bones)} bone names agree: {view.get("bones") == own_bones}')
        for seen_mesh, mesh in zip(view['meshes'], tree.get('Meshes') or []):
            if list(seen_mesh['index']) != Granny.mesh_indices(mesh['PrimaryTopology']):
                problems.append(f'{seen_mesh["name"]}: the indices differ between the two views')
        if view['meshes']:
            notes.append('mesh indices agree with Granny.mesh_indices: '
                         + str(not any('indices differ' in p for p in problems)))
    for mesh in view['meshes']:
        del mesh['index']
    return notes, problems, view


INDEX_TEST_MODELS = ('hd/character/enemy/sandleaper1/torso_lod0.model', 'hd/character/enemy/quillrat1/torso_lod0.model',
                     'hd/character/enemy/pig/torso_lod1.model', 'hd/character/enemy/spiritwolf/torso_lod0.model',
                     'hd/character/enemy/druidbear/torso_lod0.model')


def index_test(game, models=INDEX_TEST_MODELS):
    """Mesh index formats through the toolkit's writers, checked by both views; returns failures.

    Stock files: written by Granny.Writer, read back, written again (same bytes), their indices
    unchanged and the check view clean. Made meshes of 40,000 and 70,000 vertices: Indices16 holding
    numbers past 32,767 (stored unsigned), then 32-bit Indices past 65,536; through MeshImport's
    replace_geometry and GrannyMesh.remove_geometry back below 65,536 (16-bit again)."""
    import numpy as np
    import Granny
    import GrannyMesh
    import MeshImport
    from d2r_casc import D2RArchive
    failures = []

    def expect(ok, what):
        print(('   ok    ' if ok else '   FAIL  ') + what)
        if not ok:
            failures.append(what)

    def write(source, tree):
        return Granny.Writer(source.tag, tuple(source.extra_tags)).build(source.describe(source.root_type), tree)

    with D2RArchive(game) as arc:
        stock = {name: arc.read(name) for name in models}
    for name, data in stock.items():
        print(name)
        if data is None:
            expect(False, f'{name}: not in the archive')
            continue
        source = Granny.read(data)
        tree = source.root()
        before = [Granny.mesh_indices(m['PrimaryTopology']) for m in tree['Meshes']]
        once = write(source, tree)
        again_source = Granny.read(once)
        again = write(again_source, again_source.root())
        expect(once == again, f'written twice, same bytes ({len(once)})')
        after = [Granny.mesh_indices(m['PrimaryTopology']) for m in Granny.read(once).root()['Meshes']]
        expect(before == after, 'indices unchanged by the writer')
        notes, problems, view = check(once)
        expect(not problems, f'check view: {problems or notes[-2]}')
    # Made meshes on the Sand Leaper body: a grid of n vertices, two triangles per square.
    base = Granny.read(stock[INDEX_TEST_MODELS[0]])
    for n, width in ((40000, 2), (70000, 4)):
        side = int(np.ceil(np.sqrt(n)))
        x, y = np.meshgrid(np.linspace(-1, 1, side), np.linspace(0, 2, side))
        positions = np.stack([x.ravel(), y.ravel(), np.zeros(side * side)], 1)[:n]
        rows = n // side
        squares = np.array([(r * side + c, r * side + c + 1, (r + 1) * side + c, (r + 1) * side + c + 1)
                            for r in range(rows - 1) for c in range(side - 1)], dtype=np.int64)
        triangles = np.concatenate([squares[:, [0, 2, 1]], squares[:, [1, 2, 3]]])
        triangles = np.concatenate([triangles, [[n - 1, n - 2, n - 3]]])     # reaches the last vertex
        mesh = MeshImport.Mesh(positions, np.tile([0.0, 0.0, 1.0], (n, 1)), (positions[:, :2] + 1) / 3, triangles)
        built, lines = MeshImport.replace_geometry(stock[INDEX_TEST_MODELS[0]], mesh)
        print(f'made mesh, {n} vertices: {lines[0]}')
        notes, problems, view = check(built)
        first = view['meshes'][0]
        expect(not problems and first['vertices'] == n and first['bytesPerIndex'] == width,
               f'replace_geometry: {first["vertices"]} vertices, {first["bytesPerIndex"]} bytes per index, problems {problems}')
        reread = Granny.read(built).root()['Meshes'][0]['PrimaryTopology']
        flat = Granny.mesh_indices(reread)
        expect(flat == [int(v) for v in triangles.reshape(-1)], 'indices read back as written (unsigned past 32,767)')
        if width == 4:
            expect(any(s.startswith('  ') and '32-bit' in s for s in lines), 'the report says 32-bit indices')
            # Remove the upper half of the grid: 35,000 vertices left, so 16-bit again.
            out, report = GrannyMesh.remove_geometry(built, [{'box': {'min': [-2, 1.0, -1], 'max': [2, 3, 1]}, 'any': True}])
            notes, problems, view = check(out)
            expect(not problems and view['meshes'][0]['bytesPerIndex'] == 2 and view['meshes'][0]['vertices'] < 65536,
                   f'remove_geometry: {report[0]}; {view["meshes"][0]["bytesPerIndex"]} bytes per index, problems {problems}')
            # Grow it past 65,536 again by adding the upper half back as a part.
            out2, report2 = GrannyMesh.add_geometry(out, [{'pick': {'box': {'min': [-2, -1, -1], 'max': [2, 3, 1]}},
                                                          'translate': [0, 0, 0.5]}])
            notes, problems, view = check(out2)
            expect(not problems and view['meshes'][0]['bytesPerIndex'] == 4,
                   f'add_geometry: {report2[0]}; {view["meshes"][0]["vertices"]} vertices, '
                   f'{view["meshes"][0]["bytesPerIndex"]} bytes per index, problems {problems}')
    print(f'{len(failures)} failures')
    return failures


if __name__ == '__main__':
    if sys.argv[1:2] == ['--index-test']:
        game = sys.argv[sys.argv.index('--game') + 1] if '--game' in sys.argv else r'D:\games\Steam\steamapps\common\Diablo II Resurrected'
        sys.exit(1 if index_test(game) else 0)
    for path in sys.argv[1:]:
        notes, problems, view = check(path)
        print(path.replace('\\', '/').split('/')[-1])
        for n in notes:
            print('   ', n)
        print('    PROBLEMS:', problems if problems else 'none')
