"""Granny 3D files as editable trees: read one into plain dicts and lists, change
it, and write it back. Made for Diablo II: Resurrected `.skeleton` files; the
`.animations` and `.model` files are the same container and read the same way.

GrannyFile.py is the other reader in this folder: it keeps the file's bytes and
patches them in place (GrannyMesh.py reshapes meshes that way). This module
rebuilds the file from the tree instead, so things can be added and removed.

  read(data)            -> GrannyFile: header, sections, pointer fix-ups
  GrannyFile.root()     -> the file's object tree as plain dicts / lists
  GrannyFile.describe() -> a type definition as JSON-ready data
  Writer                -> lays a type + object tree out again and returns file
                           bytes (sections stored unpacked, which needs no
                           BitKnit; not yet seen loading in the game)

The object tree is read by walking the type definitions stored in the file, so
nothing here depends on the layout of a particular Granny version.
"""
import os
import struct
import sys
import zlib

MAGIC_LE64 = bytes.fromhex('e59b495e6f631f141e13eba990beedc4')
HEADER_SIZE = 0x1C8          # magic block (0x20) + file header (0x48) + 8 section headers (44 each)
SECTION_COUNT = 8
BITKNIT = 4

# Member types of a Granny type definition.
(T_END, T_INLINE, T_REF, T_REF_ARRAY, T_ARRAY_OF_REFS, T_VARIANT, T_UNUSED6, T_VARIANT_ARRAY, T_STRING,
 T_TRANSFORM, T_REAL32, T_INT8, T_UINT8, T_BINORMAL_INT8, T_NORMAL_UINT8, T_INT16, T_UINT16,
 T_BINORMAL_INT16, T_NORMAL_UINT16, T_INT32, T_UINT32, T_REAL16, T_EMPTY_REF) = range(23)

TYPE_NAMES = ['end', 'inline', 'ref', 'ref_array', 'array_of_refs', 'variant', 'unused6', 'variant_array',
              'string', 'transform', 'real32', 'int8', 'uint8', 'binormal_int8', 'normal_uint8', 'int16',
              'uint16', 'binormal_int16', 'normal_uint16', 'int32', 'uint32', 'real16', 'empty_ref']
SCALAR = {T_REAL32: 'f', T_INT8: 'b', T_UINT8: 'B', T_BINORMAL_INT8: 'b', T_NORMAL_UINT8: 'B',
          T_INT16: 'h', T_UINT16: 'H', T_BINORMAL_INT16: 'h', T_NORMAL_UINT16: 'H',
          T_INT32: 'i', T_UINT32: 'I', T_REAL16: 'e'}
FIXED_SIZE = {T_REF: 8, T_REF_ARRAY: 12, T_ARRAY_OF_REFS: 12, T_VARIANT: 16, T_VARIANT_ARRAY: 20,
              T_STRING: 8, T_TRANSFORM: 68, T_EMPTY_REF: 8}
MEMBER_SIZE = 44             # type u32, name ptr, definition ptr, array width u32, 3 x u32, ptr


# ---------------------------------------------------------------- BitKnit

def bitknit_decode(src, size):
    """Unpacks a BitKnit2 stream to `size` bytes.

    The decoder is not part of this repository: the known ones derive from GPL
    code, which LICENSING.md keeps out. Like GrannyFile.py, this loads
    `bitknit.py` (`decompress(data, size)`) from the folder named by D2R_BITKNIT,
    or from the D2RModAssets/thirdparty folder under %LOCALAPPDATA%.
    """
    if size == 0:
        return b''
    folder = os.environ.get('D2R_BITKNIT') or os.path.join(os.environ.get('LOCALAPPDATA', ''), 'D2RModAssets', 'thirdparty')
    if folder not in sys.path:
        sys.path.append(folder)
    try:
        import bitknit
    except ImportError as error:
        raise RuntimeError(f'BitKnit2 decoder not found in {folder} (see the note in GrannyFile.py); '
                           'only unpacked Granny files can be read without it') from error
    return bitknit.decompress(bytes(src), size)


# ---------------------------------------------------------------- container

class GrannyFile:
    """A parsed container. `mem` is every section back to back; `fix` maps the
    address of each pointer slot to the address it points at."""

    def __init__(self):
        self.tag = 0
        self.extra_tags = (0, 0, 0, 0)
        self.sections = []           # dicts: data, alignment, base, relocations, marshalling
        self.mem = b''
        self.fix = {}
        self.root_type = None        # address in mem
        self.root_object = None
        self._types = {}
        self._objects = {}

    # -- low level
    def u32(self, addr):
        return struct.unpack_from('<I', self.mem, addr)[0]

    def ptr(self, addr):
        return self.fix.get(addr)

    def string(self, addr):
        target = self.fix.get(addr)
        if target is None:
            return None
        end = self.mem.index(b'\0', target)
        return self.mem[target:end].decode('utf-8', 'replace')

    # -- types
    def type_of(self, addr):
        """Members of the type definition at `addr`: dicts with type, name, definition (address), width."""
        if addr in self._types:
            return self._types[addr]
        members = self._types[addr] = []
        while True:
            kind = self.u32(addr)
            if kind == T_END:
                break
            if kind >= len(TYPE_NAMES) or kind == T_UNUSED6:
                raise ValueError(f'unknown member type {kind} at {addr:#x}')
            members.append({'type': kind, 'name': self.string(addr + 4), 'definition': self.ptr(addr + 12),
                            'width': self.u32(addr + 20), 'extra': struct.unpack_from('<3I', self.mem, addr + 24)})
            addr += MEMBER_SIZE
        return members

    def member_size(self, m):
        kind = m['type']
        if kind == T_INLINE:
            one = self.struct_size(m['definition'])
        elif kind in SCALAR:
            one = struct.calcsize(SCALAR[kind])
        else:
            one = FIXED_SIZE[kind]
        return one * max(1, m['width'])

    def struct_size(self, type_addr):
        return sum(self.member_size(m) for m in self.type_of(type_addr))

    # -- objects
    def root(self):
        return self.struct(self.root_object, self.root_type)

    def struct(self, addr, type_addr):
        """The object at `addr`, read as `type_addr`: {member name: value}."""
        key = (addr, type_addr)
        if key in self._objects:
            return self._objects[key]
        obj = self._objects[key] = {}
        members = self.type_of(type_addr)
        for m, name in zip(members, member_keys(m['name'] for m in members)):
            width = m['width']
            if width:
                step = self.member_size(m) // width
                obj[name] = [self._value(addr + i * step, m) for i in range(width)]
            else:
                obj[name] = self._value(addr, m)
            addr += self.member_size(m)
        return obj

    def _array(self, count, addr, type_addr):
        if addr is None or type_addr is None:
            return []
        size = self.struct_size(type_addr)
        members = self.type_of(type_addr)
        if len(members) == 1 and members[0]['type'] in SCALAR and not members[0]['width']:
            return list(struct.unpack_from(f'<{count}{SCALAR[members[0]["type"]]}', self.mem, addr))
        return [self.struct(addr + i * size, type_addr) for i in range(count)]

    def _value(self, addr, m):
        kind, definition = m['type'], m['definition']
        if kind in SCALAR:
            return struct.unpack_from('<' + SCALAR[kind], self.mem, addr)[0]
        if kind == T_STRING:
            return self.string(addr)
        if kind == T_INLINE:
            return self.struct(addr, definition)
        if kind == T_REF:
            target = self.ptr(addr)
            return None if target is None or definition is None else self.struct(target, definition)
        if kind == T_EMPTY_REF:
            return None
        if kind == T_REF_ARRAY:
            return self._array(self.u32(addr), self.ptr(addr + 4), definition)
        if kind == T_ARRAY_OF_REFS:
            count, table = self.u32(addr), self.ptr(addr + 4)
            if table is None or definition is None:
                return []
            targets = [self.ptr(table + 8 * i) for i in range(count)]
            return [None if t is None else self.struct(t, definition) for t in targets]
        if kind == T_VARIANT:
            vtype, target = self.ptr(addr), self.ptr(addr + 8)
            if vtype is None or target is None:
                return None
            return {'$type': self.describe(vtype), '$value': self.struct(target, vtype)}
        if kind == T_VARIANT_ARRAY:
            vtype, count, target = self.ptr(addr), self.u32(addr + 8), self.ptr(addr + 12)
            if vtype is None:
                return None
            return {'$type': self.describe(vtype), '$items': self._array(count, target, vtype)}
        if kind == T_TRANSFORM:
            v = struct.unpack_from('<I16f', self.mem, addr)
            return {'flags': v[0], 'position': list(v[1:4]), 'orientation': list(v[4:8]),
                    'scale_shear': [list(v[8:11]), list(v[11:14]), list(v[14:17])]}
        raise ValueError(f'member type {kind}')

    def describe(self, type_addr, _seen=None):
        """A type definition as JSON-ready data (enough to write it back with Writer).

        A member whose type is one of the structs it sits in is marked '$recursive' (the struct
        that holds the member) or '$recursive:N' (N structs further out: a material map's Map is
        a material, '$recursive:1')."""
        seen = _seen or ()
        if type_addr in seen:
            up = len(seen) - 1 - seen.index(type_addr)
            return '$recursive' if up == 0 else '$recursive:%d' % up
        seen = seen + (type_addr,)
        out = []
        for m in self.type_of(type_addr):
            d = {'name': m['name'], 'type': TYPE_NAMES[m['type']]}
            if m['width']:
                d['width'] = m['width']
            if any(m['extra']):
                d['extra'] = list(m['extra'])
            if m['definition'] is not None:
                d['of'] = self.describe(m['definition'], seen)
            out.append(d)
        return out


def read(data):
    """Parses a Granny container. Raises ValueError when `data` is not one this module knows."""
    if data[:16] != MAGIC_LE64:
        raise ValueError('not a 64-bit little-endian Granny file')
    version, total, crc, sec_off, sec_count = struct.unpack_from('<5I', data, 0x20)
    if version != 7:
        raise ValueError(f'Granny file format {version}, expected 7')
    g = GrannyFile()
    root_type = struct.unpack_from('<2I', data, 0x34)
    root_object = struct.unpack_from('<2I', data, 0x3C)
    g.tag = struct.unpack_from('<I', data, 0x44)[0]
    g.extra_tags = struct.unpack_from('<4I', data, 0x48)
    g.crc_ok = zlib.crc32(data[0x68:total]) == crc      # section headers and everything after
    base = 0
    chunks = []
    for i in range(sec_count):
        comp, off, packed, size, align, stop16, stop32, rel_off, rel_count, mar_off, mar_count = \
            struct.unpack_from('<11I', data, 0x20 + sec_off + i * 44)
        if size == 0:
            body = b''
        elif comp == 0:
            body = data[off:off + size]
        elif comp == BITKNIT:
            body = bitknit_decode(data[off:off + packed], size)
        else:
            raise ValueError(f'section {i}: compression {comp} is not supported (only none and BitKnit)')

        def table(offset, count, width):
            if not count:
                return b''
            if comp == BITKNIT:
                n = struct.unpack_from('<I', data, offset)[0]
                return bitknit_decode(data[offset + 4:offset + 4 + n], count * width)
            return data[offset:offset + count * width]
        rel = table(rel_off, rel_count, 12)
        mar = table(mar_off, mar_count, 16)
        g.sections.append({'data': body, 'alignment': align, 'base': base, 'compression': comp,
                           'relocations': [struct.unpack_from('<3I', rel, j * 12) for j in range(rel_count)],
                           'marshalling': [struct.unpack_from('<4I', mar, j * 16) for j in range(mar_count)]})
        chunks.append(body)
        base += len(body)
    g.mem = b''.join(chunks)
    for s in g.sections:
        for offset, target_section, target_offset in s['relocations']:
            g.fix[s['base'] + offset] = g.sections[target_section]['base'] + target_offset
    g.root_type = g.sections[root_type[0]]['base'] + root_type[1]
    g.root_object = g.sections[root_object[0]]['base'] + root_object[1]
    return g


# ---------------------------------------------------------------- writer

class Writer:
    """Builds a container from a type description (as GrannyFile.describe returns)
    and an object tree (as GrannyFile.root returns).

    Objects go to section 0 and type definitions and their names to section 6,
    the split the game's own files use. Sections are stored unpacked.

    The section table follows the game's own files in two more things (found 2026-11-19 by
    comparing stock models, skeletons and animation files): sections 1 and 3, always empty,
    declare an alignment of 32, the rest 4; and every variant object or variant array whose
    element type holds numbers that are not 32 bits wide (a vertex array, an animation curve)
    gets a marshalling record (element count, where, its type), which a loader on a machine of
    the other byte order needs to swap such data. The rule reproduces the stock records exactly
    (checked on models, a skeleton and two animation files). Neither changes a byte of data.
    """

    ALIGNMENT = (4, 32, 4, 32, 4, 4, 4, 4)

    def __init__(self, tag=0x80000039, extra_tags=(0, 0, 0, 0)):
        self.tag, self.extra_tags = tag, extra_tags
        self.buf = [bytearray() for _ in range(SECTION_COUNT)]
        self.rel = [[] for _ in range(SECTION_COUNT)]
        self.mar = [[] for _ in range(SECTION_COUNT)]
        self._marshalled = set()
        self._types = {}
        self._strings = {}
        self._made = {}              # (type, content) -> where it was written, so equal objects are shared

    # -- helpers
    def _alloc(self, section, size, align=4):
        b = self.buf[section]
        b += bytes(-len(b) % align)
        at = len(b)
        b += bytes(size)
        return at

    def _point(self, section, offset, target):
        """Makes the 8-byte slot at (section, offset) point at `target` = (section, offset)."""
        if target is not None:
            self.rel[section].append((offset, target[0], target[1]))

    def _mixed(self, desc, outer=()):
        """Whether one element of this type stores numbers that are not 32 bits wide."""
        for m in desc:
            kind = TYPE_NAMES.index(m['type'])
            if kind in SCALAR and kind not in (T_REAL32, T_INT32, T_UINT32):
                return True
            if kind == T_INLINE and isinstance(m.get('of'), list) and self._mixed(m['of']):
                return True
        return False

    def _marshal(self, count, where, desc):
        if where is not None and count and where not in self._marshalled and self._mixed(desc):
            self._marshalled.add(where)
            self.mar[where[0]].append((count, where[1]) + self._type(desc))

    def _string(self, text, section):
        key = (section, text)
        if key not in self._strings:
            raw = text.encode('utf-8') + b'\0'
            at = self._alloc(section, len(raw), 1)
            self.buf[section][at:at + len(raw)] = raw
            self._strings[key] = (section, at)
        return self._strings[key]

    # -- types
    def _type(self, desc, _outer=()):
        key = _freeze(desc)
        if key in self._types:
            return self._types[key]
        at = self._alloc(6, MEMBER_SIZE * (len(desc) + 1))
        here = self._types[key] = (6, at)
        stack = _outer + (here,)
        subs = [self._type(m['of'], stack) if isinstance(m.get('of'), list) else None for m in desc]
        for i, m in enumerate(desc):
            o = at + i * MEMBER_SIZE
            struct.pack_into('<I', self.buf[6], o, TYPE_NAMES.index(m['type']))
            self._point(6, o + 4, self._string(m['name'], 6))
            if _recursion(m.get('of')) is not None:
                self._point(6, o + 12, stack[-1 - _recursion(m['of'])])
            else:
                self._point(6, o + 12, subs[i])
            struct.pack_into('<4I', self.buf[6], o + 20, m.get('width', 0), *m.get('extra', (0, 0, 0)))
        return here

    def _size(self, desc):
        return sum(self._member_size(m) for m in desc)

    def _member_size(self, m):
        kind = TYPE_NAMES.index(m['type'])
        if kind == T_INLINE:
            one = self._size(m['of'])
        elif kind in SCALAR:
            one = struct.calcsize(SCALAR[kind])
        else:
            one = FIXED_SIZE[kind]
        return one * max(1, m.get('width', 0))

    # -- objects
    def _struct(self, desc, obj, section, at, outer=()):
        outer = outer + (desc,)
        for m, name in zip(desc, member_keys(m['name'] for m in desc)):
            width = m.get('width', 0)
            value = obj[name]
            if width:
                step = self._member_size(m) // width
                for i in range(width):
                    self._value(m, value[i], section, at + i * step, outer)
            else:
                self._value(m, value, section, at, outer)
            at += self._member_size(m)

    def _new(self, desc, obj, outer=()):
        key = (_freeze(desc), _freeze(obj))
        if key not in self._made:
            at = self._alloc(0, self._size(desc))
            self._made[key] = (0, at)
            self._struct(desc, obj, 0, at, outer)
        return self._made[key]

    def _new_array(self, desc, items, outer=()):
        if not items:
            return None
        key = (_freeze(desc), _freeze(items))
        if key not in self._made:
            self._made[key] = self._write_array(desc, items, outer)
        return self._made[key]

    def _write_array(self, desc, items, outer=()):
        if len(desc) == 1 and TYPE_NAMES.index(desc[0]['type']) in SCALAR and not desc[0].get('width'):
            code = SCALAR[TYPE_NAMES.index(desc[0]['type'])]
            if code == 'h' and max(items) > 32767:
                # A mesh's Indices16 is typed int16, but Granny and the game read it unsigned
                # (R16_UINT): vertices 32768-65535 are stored as their 16-bit pattern.
                if min(items) < -32768 or max(items) > 65535:
                    raise ValueError(f'a 16-bit array holds {min(items)}..{max(items)}')
                items, code = [v & 0xFFFF for v in items], 'H'
            raw = struct.pack(f'<{len(items)}{code}', *items)
            at = self._alloc(0, len(raw))
            self.buf[0][at:at + len(raw)] = raw
            return (0, at)
        size = self._size(desc)
        at = self._alloc(0, size * len(items))
        for i, item in enumerate(items):
            self._struct(desc, item, 0, at + i * size, outer)
        return (0, at)

    def _value(self, m, value, section, at, outer=()):
        kind = TYPE_NAMES.index(m['type'])
        b = self.buf[section]
        of = m.get('of')
        if _recursion(of) is not None:   # a member whose type is a struct it sits in (a material map's Map)
            of = outer[-1 - _recursion(of)]
        if kind in SCALAR:
            struct.pack_into('<' + SCALAR[kind], b, at, value)
        elif kind == T_STRING:
            if value is not None:
                self._point(section, at, self._string(value, 0))
        elif kind == T_INLINE:
            self._struct(of, value, section, at, outer)
        elif kind == T_REF:
            if value is not None:
                self._point(section, at, self._new(of, value, outer))
        elif kind == T_EMPTY_REF:
            pass
        elif kind == T_REF_ARRAY:
            struct.pack_into('<I', self.buf[section], at, len(value))
            self._point(section, at + 4, self._new_array(of, value, outer))
        elif kind == T_ARRAY_OF_REFS:
            struct.pack_into('<I', self.buf[section], at, len(value))
            if value:
                table = self._alloc(0, 8 * len(value))
                self._point(section, at + 4, (0, table))
                for i, item in enumerate(value):
                    if item is not None:
                        self._point(0, table + 8 * i, self._new(of, item, outer))
        elif kind == T_VARIANT:
            if value is not None:
                self._point(section, at, self._type(value['$type']))
                where = self._new(value['$type'], value['$value'])
                self._point(section, at + 8, where)
                self._marshal(1, where, value['$type'])
        elif kind == T_VARIANT_ARRAY:
            if value is not None:
                self._point(section, at, self._type(value['$type']))
                struct.pack_into('<I', self.buf[section], at + 8, len(value['$items']))
                where = self._new_array(value['$type'], value['$items'])
                self._point(section, at + 12, where)
                self._marshal(len(value['$items']), where, value['$type'])
        elif kind == T_TRANSFORM:
            struct.pack_into('<I16f', self.buf[section], at, value['flags'], *value['position'], *value['orientation'],
                             *[x for row in value['scale_shear'] for x in row])
        else:
            raise ValueError(f'member type {m["type"]}')

    def build(self, root_desc, root_obj):
        """Returns the bytes of a container whose root object is `root_obj` of type `root_desc`."""
        root_object = self._new(root_desc, root_obj)       # first, so it sits at section 0 offset 0
        root_type = self._type(root_desc)
        for b in self.buf:
            b += bytes(-len(b) % 4)
        body = bytearray()
        headers = []
        offset = HEADER_SIZE
        for i in range(SECTION_COUNT):
            headers.append([0, offset, len(self.buf[i]), len(self.buf[i]), self.ALIGNMENT[i], len(self.buf[i]), len(self.buf[i])])
            body += self.buf[i]
            offset += len(self.buf[i])
        for i in range(SECTION_COUNT):
            headers[i] += [offset, len(self.rel[i])]
            for r in self.rel[i]:
                body += struct.pack('<3I', *r)
            offset += 12 * len(self.rel[i])
            headers[i] += [offset, len(self.mar[i])]
            for record in self.mar[i]:
                body += struct.pack('<4I', *record)
            offset += 16 * len(self.mar[i])
        total = HEADER_SIZE + len(body)
        tail = b''.join(struct.pack('<11I', *h) for h in headers) + bytes(body)
        out = bytearray(MAGIC_LE64 + struct.pack('<4I', HEADER_SIZE, 0, 0, 0))
        out += struct.pack('<5I', 7, total, zlib.crc32(tail), 0x48, SECTION_COUNT)
        out += struct.pack('<2I', *root_type) + struct.pack('<2I', *root_object)
        out += struct.pack('<I', self.tag) + struct.pack('<4I', *self.extra_tags)
        out += bytes(0x20 + 0x48 - len(out))
        return bytes(out) + tail


# ---------------------------------------------------------------- mesh indices

INDEX16_VERTICES = 65536     # vertices a 16-bit index reaches (0..65535, read unsigned)


def mesh_indices(topology):
    """A mesh topology's triangle corners as one flat list of vertex numbers.

    The 32-bit `Indices` array wins when it is filled, as in Granny's own GrannyGetMeshIndices and
    GrannyGetMeshBytesPerIndex (game image 95032: 0x1624370 / 0x1624320); otherwise `Indices16`,
    read unsigned (its type says int16, the game binds it as R16_UINT)."""
    if topology.get('Indices'):
        return [int(v) for v in topology['Indices']]
    return [int(v) & 0xFFFF for v in topology.get('Indices16') or []]


def set_mesh_indices(topology, flat, vertex_count=None):
    """Stores triangle corners in a mesh topology; returns the bytes per index used (2 or 4).

    16-bit `Indices16` while every vertex fits (as the stock files that size do, so they stay
    byte for byte the same), the 32-bit `Indices` array past 65,536 vertices. The game's mesh
    loader (Mesh::LoadGeometry, 0xFA04C0) takes either: index buffer stride = bytes per index,
    DXGI_FORMAT_R32_UINT for 4 (0x10F1240), and stock bodies such as the spirit wolf ship 32-bit."""
    flat = [int(v) for v in flat]
    top = max(vertex_count or 0, (max(flat) + 1) if flat else 0)
    if 'Indices' not in topology or 'Indices16' not in topology:
        raise ValueError('the topology type has no Indices / Indices16 member')
    if top > INDEX16_VERTICES:
        topology['Indices'], topology['Indices16'] = flat, []
        return 4
    topology['Indices16'], topology['Indices'] = flat, []
    return 2


def member_keys(names):
    """Keys of an object's members: the member names, with '#2', '#3' ... added to repeats."""
    seen, out = {}, []
    for name in names:
        seen[name] = seen.get(name, 0) + 1
        out.append(name if seen[name] == 1 else f'{name}#{seen[name]}')
    return out


_frozen = {}


def _recursion(of):
    """How many structs out a '$recursive' type marker points (0 = the one holding the member), or None."""
    if isinstance(of, str) and of.startswith('$recursive'):
        return int(of.split(':', 1)[1]) if ':' in of else 0
    return None


def _freeze(value):
    """A hashable stand-in for a tree of dicts and lists; equal trees give the same object."""
    if isinstance(value, (list, dict)):
        hit = _frozen.get(id(value))
        if hit is not None and hit[0] is value:
            return hit[1]
        if isinstance(value, list):
            key = tuple(_freeze(v) for v in value)
        else:
            key = tuple((k, _freeze(v)) for k, v in value.items())
        key = _interned.setdefault(key, key)
        _frozen[id(value)] = (value, key)
        return key
    if isinstance(value, float):
        return struct.pack('<d', value)          # keeps -0.0 and NaN apart from 0.0
    return value


_interned = {}
