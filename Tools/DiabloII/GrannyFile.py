"""Reader for Granny 3D files: D2R's HD .model, .skeleton and .animations.

Granny v7, 64-bit little endian. Sections are BitKnit2-compressed; pointers are
stored as fixups (section offset -> target section + offset). Files describe
their own data with a type tree, so the object graph can be walked generically.

BitKnit2 decompression is not part of this repository (the known decoders are
GPL). Put a `bitknit.py` with `decompress(data, size)` in
%LOCALAPPDATA%\\D2RModAssets\\thirdparty, or point D2R_BITKNIT at its folder.
Uncompressed Granny files are read without it.
"""
import os
import struct
import sys
import zlib



def _load_bitknit():
    folder = os.environ.get('D2R_BITKNIT') or os.path.join(os.environ.get('LOCALAPPDATA', ''), 'D2RModAssets', 'thirdparty')
    if folder not in sys.path:
        sys.path.insert(0, folder)
    try:
        import bitknit
    except ImportError as error:
        raise RuntimeError(f'BitKnit2 decoder not found in {folder} (see the note at the top of GrannyFile.py)') from error
    return bitknit

COMPRESSION = {0: 'none', 1: 'Oodle0', 2: 'Oodle1', 3: 'BitKnit1', 4: 'BitKnit2'}
DT = {
    0: 'end', 1: 'inline', 2: 'reference', 3: 'reference_to_array', 4: 'array_of_references',
    5: 'variant_reference', 7: 'reference_to_variant_array', 8: 'string', 9: 'transform',
    10: 'float', 11: 'int8', 12: 'uint8', 13: 'binormal_int8', 14: 'normal_uint8',
    15: 'int16', 16: 'uint16', 17: 'binormal_int16', 18: 'normal_uint16',
    19: 'int32', 20: 'uint32', 21: 'half', 22: 'empty_reference',
}
SCALAR = {10: ('f', 4), 11: ('b', 1), 12: ('B', 1), 13: ('b', 1), 14: ('B', 1), 15: ('h', 2), 16: ('H', 2),
          17: ('h', 2), 18: ('H', 2), 19: ('i', 4), 20: ('I', 4), 21: ('e', 2)}
TYPE_INFO_SIZE = 44  # type u32, name ptr, reference type ptr, count u32, tags[3], reserved u64


def bitknit2(data, size):
    return _load_bitknit().decompress(bytes(data), size)


class Granny:
    def __init__(self, data):
        self.raw = data
        magic = data[:16]
        if magic.hex() != 'e59b495e6f631f141e13eba990beedc4':
            raise ValueError('not a 64-bit little-endian Granny file')
        self.header_size, self.header_format = struct.unpack_from('<II', data, 16)
        (self.version, self.file_size, self.crc, section_table, count,
         rt_sec, rt_off, ro_sec, ro_off, self.type_tag) = struct.unpack_from('<10I', data, 32)
        self.root_type = (rt_sec, rt_off)
        self.root_obj = (ro_sec, ro_off)
        self.header_words = list(struct.unpack_from('<18I', data, 32))   # the whole 72-byte header
        self.section_headers = []
        self.sections = []
        self.fixups = {}  # (section, offset) -> (section, offset)
        self.fixup_tables = []    # per section, the raw 12-byte entries in file order
        self.marshal_tables = []  # per section, the raw 16-byte entries
        base = 32 + section_table
        for i in range(count):
            h = struct.unpack_from('<11I', data, base + i * 44)
            self.section_headers.append(h)
            comp, off, clen, ulen = h[0], h[1], h[2], h[3]
            if comp == 0:
                self.sections.append(bytearray(data[off:off + ulen]))
            elif comp == 4:
                self.sections.append(bytearray(bitknit2(data[off:off + clen], ulen)) if ulen else bytearray())
            else:
                raise ValueError(f'section {i}: unsupported compression {COMPRESSION.get(comp, comp)}')
        for i, h in enumerate(self.section_headers):
            comp = h[0]
            tables = []
            # Fixups (12 bytes each) and marshalling records (16 bytes each). In a compressed
            # section each table is stored as a length-prefixed BitKnit2 stream of its own.
            for offset, count, size in ((h[7], h[8], 12), (h[9], h[10], 16)):
                if not count:
                    tables.append(b'')
                elif comp == 4:
                    clen = struct.unpack_from('<I', data, offset)[0]
                    tables.append(bitknit2(data[offset + 4:offset + 4 + clen], count * size))
                else:
                    tables.append(bytes(data[offset:offset + count * size]))
            self.fixup_tables.append(tables[0])
            self.marshal_tables.append(tables[1])
            for k in range(h[8]):
                src, tsec, toff = struct.unpack_from('<III', tables[0], k * 12)
                self.fixups[(i, src)] = (tsec, toff)

    # --- writing ---
    def to_bytes(self):
        """The file with every section stored uncompressed.

        Granny reads uncompressed sections natively, so no compressor is needed.
        Section contents are written as they are now in `self.sections` (edit
        them in place first); pointers keep working because fixups address
        sections by offset and the section sizes do not change.
        """
        count = len(self.sections)
        header_size = 32 + 72 + count * 44
        position = header_size
        placed = []
        for i, section in enumerate(self.sections):
            old = self.section_headers[i]
            align = max(old[4], 4)
            position = (position + align - 1) // align * align
            placed.append(position)
            position += len(section)
        table_offsets = []
        for i in range(count):
            position = (position + 3) // 4 * 4
            fix_at = position
            position += len(self.fixup_tables[i])
            marshal_at = position
            position += len(self.marshal_tables[i])
            table_offsets.append((fix_at, marshal_at))
        out = bytearray(position)
        out[0:16] = bytes.fromhex('e59b495e6f631f141e13eba990beedc4')
        struct.pack_into('<II', out, 16, header_size, 0)
        words = list(self.header_words)
        words[1] = position          # file size
        words[2] = 0                 # crc, filled in below
        words[3] = 72                # section table offset, from the start of this header
        words[4] = count
        struct.pack_into('<18I', out, 32, *words)
        for i, section in enumerate(self.sections):
            old = self.section_headers[i]
            size = len(section)
            fix_at, marshal_at = table_offsets[i]
            struct.pack_into('<11I', out, 104 + i * 44,
                             0, placed[i], size, size, old[4], min(old[5], size), min(old[6], size),
                             fix_at, len(self.fixup_tables[i]) // 12, marshal_at, len(self.marshal_tables[i]) // 16)
            out[placed[i]:placed[i] + size] = section
            out[fix_at:fix_at + len(self.fixup_tables[i])] = self.fixup_tables[i]
            out[marshal_at:marshal_at + len(self.marshal_tables[i])] = self.marshal_tables[i]
        # The checksum covers everything after the fixed header: section table, data, tables.
        struct.pack_into('<I', out, 40, zlib.crc32(bytes(out[104:])) & 0xFFFFFFFF)
        return bytes(out)

    def save(self, path):
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(path, 'wb') as f:
            f.write(self.to_bytes())

    def checksum_ok(self):
        return zlib.crc32(bytes(self.raw[104:])) & 0xFFFFFFFF == self.crc

    # --- low level ---
    def ptr(self, at):
        """The pointer stored at a (section, offset), or None for null."""
        return self.fixups.get(at)

    def cstr(self, at):
        if at is None:
            return None
        sec, off = at
        data = self.sections[sec]
        end = data.index(b'\0', off)
        return data[off:end].decode('utf-8', 'replace')

    def u32(self, at):
        return struct.unpack_from('<I', self.sections[at[0]], at[1])[0]

    def i32(self, at):
        return struct.unpack_from('<i', self.sections[at[0]], at[1])[0]

    # --- type tree ---
    def read_type(self, at, cache=None):
        """A struct definition: list of members up to the 'end' marker."""
        cache = self._types if hasattr(self, '_types') else {}
        self._types = cache
        if at in cache:
            return cache[at]
        members = []
        cache[at] = members
        sec, off = at
        while True:
            kind = self.u32((sec, off))
            if kind == 0:
                break
            name = self.cstr(self.ptr((sec, off + 4)))
            ref = self.ptr((sec, off + 12))
            count = self.u32((sec, off + 20))
            members.append({'kind': kind, 'name': name, 'ref': ref, 'count': count})
            off += TYPE_INFO_SIZE
        return members

    def member_size(self, m):
        kind = m['kind']
        n = max(m['count'], 1)
        if kind in SCALAR:
            return SCALAR[kind][1] * n
        if kind == 1:
            return self.struct_size(self.read_type(m['ref'])) * n
        if kind in (2, 8, 22):
            return 8 * n
        if kind in (3, 4):
            return 12 * n   # count u32 + pointer
        if kind == 5:
            return 16 * n   # type pointer + object pointer
        if kind == 7:
            return 20 * n   # type pointer + count u32 + pointer
        if kind == 9:
            return 68 * n   # flags + position[3] + orientation[4] + scale/shear[9]
        raise ValueError(f'unknown member kind {kind}')

    def struct_size(self, members):
        return sum(self.member_size(m) for m in members)

    # --- generic walk ---
    def read_struct(self, members, at, depth=0, max_depth=12, array_limit=4):
        sec, off = at
        out = {}
        for m in members:
            out[m['name']] = self.read_member(m, (sec, off), depth, max_depth, array_limit)
            off += self.member_size(m)
        return out

    def read_member(self, m, at, depth, max_depth, array_limit):
        kind, n = m['kind'], m['count']
        sec, off = at
        data = self.sections[sec]
        if kind in SCALAR:
            fmt, size = SCALAR[kind]
            values = list(struct.unpack_from('<' + fmt * max(n, 1), data, off))
            return values if n else values[0]
        if kind == 8:
            return self.cstr(self.ptr(at))
        if kind == 9:
            flags, = struct.unpack_from('<I', data, off)
            f = struct.unpack_from('<16f', data, off + 4)
            return {'flags': flags, 'position': f[0:3], 'orientation': f[3:7], 'scaleShear': f[7:16]}
        if depth >= max_depth:
            return f'<{DT[kind]}>'
        if kind == 1:
            return self.read_struct(self.read_type(m['ref']), at, depth + 1, max_depth, array_limit)
        if kind == 2:
            target = self.ptr(at)
            if target is None or m['ref'] is None:
                return None
            return self.read_struct(self.read_type(m['ref']), target, depth + 1, max_depth, array_limit)
        if kind == 22:
            return None
        if kind == 3:      # count + pointer to array of structs
            count = self.i32(at)
            target = self.ptr((sec, off + 4))
            return self.read_array(m['ref'], target, count, depth, max_depth, array_limit)
        if kind == 4:      # count + pointer to array of pointers
            count = self.i32(at)
            target = self.ptr((sec, off + 4))
            items = []
            if target is None:
                return {'count': count, 'items': []}
            sub = self.read_type(m['ref']) if m['ref'] else None
            for k in range(min(count, array_limit)):
                p = self.ptr((target[0], target[1] + 8 * k))
                items.append(self.read_struct(sub, p, depth + 1, max_depth, array_limit) if (p and sub) else None)
            return {'count': count, 'items': items}
        if kind == 5:      # variant: type pointer + object pointer
            type_at = self.ptr(at)
            obj = self.ptr((sec, off + 8))
            if type_at is None or obj is None:
                return None
            return self.read_struct(self.read_type(type_at), obj, depth + 1, max_depth, array_limit)
        if kind == 7:      # variant array: type pointer + count + pointer
            type_at = self.ptr(at)
            count = self.i32((sec, off + 8))
            target = self.ptr((sec, off + 12))
            return self.read_array(type_at, target, count, depth, max_depth, array_limit, describe=True)
        raise ValueError(kind)

    def read_array(self, type_at, target, count, depth, max_depth, array_limit, describe=False):
        if type_at is None or target is None or count <= 0:
            return {'count': count, 'items': []}
        members = self.read_type(type_at)
        size = self.struct_size(members)
        out = {'count': count, 'itemSize': size}
        if describe:
            out['layout'] = [f"{m['name']}:{DT[m['kind']]}" + (f"[{m['count']}]" if m['count'] else '') for m in members]
        out['items'] = [self.read_struct(members, (target[0], target[1] + size * k), depth + 1, max_depth, array_limit)
                        for k in range(min(count, array_limit))]
        return out

    def root(self, **kw):
        return self.read_struct(self.read_type(self.root_type), self.root_obj, **kw)

    def describe_type(self, at=None, indent=0, seen=None, out=None, max_depth=6):
        out = [] if out is None else out
        seen = set() if seen is None else seen
        members = self.read_type(at or self.root_type)
        for m in members:
            out.append('  ' * indent + f"{m['name']}: {DT[m['kind']]}" + (f"[{m['count']}]" if m['count'] else ''))
            if m['ref'] and m['ref'] not in seen and indent < max_depth:
                seen.add(m['ref'])
                self.describe_type(m['ref'], indent + 1, seen, out, max_depth)
        return out


def load(path):
    with open(path, 'rb') as f:
        return Granny(f.read())


if __name__ == '__main__':
    g = load(sys.argv[1])
    print('sections:', [len(s) for s in g.sections], 'fixups:', len(g.fixups))
    print('\n'.join(g.describe_type()))
