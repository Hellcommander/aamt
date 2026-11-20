"""Reads a Granny file the way the Noesis GR2 reader script (Jayn23, v1.3.5, after Norbyte's
lslib) lays it out, written from reading that script, none of its code run: sections placed
end to end by decompressed size, relocations patched in as 4-byte offsets, type members of
44 bytes. Then compares what that view sees with what the toolkit's own Granny.py sees."""
import struct
import sys
import zlib

MAGIC_LE64 = bytes([0xE5, 0x9B, 0x49, 0x5E, 0x6F, 0x63, 0x1F, 0x14, 0x1E, 0x13, 0xEB, 0xA9, 0x90, 0xBE, 0xED, 0xC4])


def check(path, compare=True):
    data = open(path, 'rb').read()
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
    return notes, problems, view


if __name__ == '__main__':
    for path in sys.argv[1:]:
        notes, problems, view = check(path)
        print(path.replace('\\', '/').split('/')[-1])
        for n in notes:
            print('   ', n)
        print('    PROBLEMS:', problems if problems else 'none')
