"""Reads, edits and writes Diablo II: Resurrected .particles files.

A .particles file is a PopcornFX baked effect (runtime 2.9.5). It holds the
compiled effect, not the editable node graph, and there is no public editor for
it. This module decodes the container so that the parts that are plain data can
be changed: renderer properties (textures, meshes, numbers, colours), curves,
attribute defaults, strings, and the compiled scripts: their constants and,
through PopcornVm.py, their instructions.

Layout (little endian), worked out from the game's 1991 files, 2026-11-13:

  0x00  u32 magic 0xCA000B11
  0x04  u32 version bytes 02 09 05 01
  0x08  u32 8000
  0x0C  u32 object count
  0x10  u32 class count
  0x14  u32 offset of the string table
  0x18  u32 0
  0x1C  class count x (u32 class index, u32 objects of that class)
        object count x record: u32 length, then
            u8 0x20, u32 class (index into the strings), u16 field count,
            field count x (u16 field id, payload)
        string table: u32 count, then count x (length, bytes); the length is
            one byte, or two when the first has its top bit set (low 7 bits
            first).

  A payload has no type tag: its size follows from (class, field id). The
  sizes in PopcornBaked.schema.json were inferred by fitting every record of
  every file ("F4" = 4 bytes, "A4" = u32 count + count x 4 bytes).
  Four-byte values are an int, a float, a string index, or a 1-based object
  number (0 = none) depending on the field.

What the fields mean, as far as it is known:

  CParticleEffect                 f1 the per-platform CLayerGraphCompileCache objects, f3 the attribute list
  CLayerGraphCompileCache         f0 platform name (PC, Switch, PS4, PS5)
  CLayerCompileCacheRenderer      f1 particle input objects, f2 property objects, f4 material (.pkma)
  CLayerCompileCacheRendererProperty
                                  f0 name ("Blend.TextureBase", "General.Mesh", "Transparent.Type" ...),
                                  f1 type code (3 int, 7 float, 14 path, ...), f2 four 32-bit values,
                                  f3 path string
  CParticleNodeSamplerData_Curve  f17 key times, f18 key values, f19 tangents (two per value)
  CParticleAttributeDeclaration   f0 name, f14 default value, f44 maximum
  CCompilerBlobCache              one compiled script ("CPU/CPU_VM" in f0). f1 a small number (1-5).
                                  f5 the externals the script loads and stores (string indices, -1 = none);
                                  f4 one record of five words per external: 0, type (operand type
                                  minus 1: 1F float, 21 float3, 22 float4, 19 int, 1 bool, -1 a context),
                                  a size class, 2 for a read-only input, access (1 read, 3 read and
                                  write, 6 write);
                                  f6 the functions the script calls, by name with their signature
                                  ("self.kill_bool_pCtxS", "effect.age_pCtxI", ...).
                                  f2 is the program, as 32-bit words:
                                    9 header words: w0 number of instructions, w1 bytecode length in
                                    bytes, w3 size of the constants in bytes, w5 number of constants,
                                    w8 number of functions, w6-w7 small counts (w2 and w4 are always 0);
                                    the bytecode (starts 7C, ends 7D);
                                    the constants, 32 bytes each (a value repeated for eight lanes,
                                    or eight different numbers), directly after the code;
                                    zero bytes up to the next word.

usage:
  PopcornBaked.py dump <file> [--class <name>]      readable listing
  PopcornBaked.py props <file>                      renderers and their properties (PC only)
  PopcornBaked.py code <file>                       compiled scripts: names, constants, bytecode size
  PopcornBaked.py dis <file> [object number ...]    compiled scripts as readable instructions
  PopcornBaked.py roundtrip <file or folder> ...    parse + write must give the same bytes
"""
import json
import os
import struct
import sys

MAGIC = 0xCA000B11
_SCHEMA = None


def schema():
    global _SCHEMA
    if _SCHEMA is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'PopcornBaked.schema.json')
        raw = json.load(open(path, encoding='utf-8'))
        _SCHEMA = {c: {int(f): (t[0], int(t[1:])) for f, t in fields.items()} for c, fields in raw.items()}
    return _SCHEMA


class Obj:
    """One object. `fields` is a list of [field id, payload bytes] in file order, or
    None when the record could not be split (then `raw` is written back as it was)."""

    def __init__(self, baked, number, cls, fields, raw):
        self.baked, self.number, self.cls, self.fields, self.raw = baked, number, cls, fields, raw

    @property
    def cls_name(self):
        return self.baked.strings[self.cls]

    def has(self, fid):
        return self.fields is not None and any(f == fid for f, _ in self.fields)

    def get(self, fid):
        for f, payload in self.fields or ():
            if f == fid:
                return payload
        return None

    def set(self, fid, payload):
        if self.fields is None:
            raise ValueError('%s #%d was not decoded' % (self.cls_name, self.number))
        for item in self.fields:
            if item[0] == fid:
                item[1] = bytes(payload)
                return
        self.fields.append([fid, bytes(payload)])
        self.fields.sort(key=lambda x: x[0])

    # typed helpers -------------------------------------------------------
    def int(self, fid, default=None):
        p = self.get(fid)
        return default if p is None else struct.unpack_from('<i', p)[0]

    def string(self, fid):
        i = self.int(fid)
        return None if i is None or not 0 <= i < len(self.baked.strings) else self.baked.strings[i]

    def set_string(self, fid, text):
        self.set(fid, struct.pack('<i', self.baked.string_index(text)))

    def floats(self, fid):
        p = self.get(fid)
        if p is None:
            return None
        kind, _ = schema()[self.cls_name][fid]
        body = p[4:] if kind == 'A' else p
        return list(struct.unpack('<%df' % (len(body) // 4), body))

    def ints(self, fid):
        p = self.get(fid)
        if p is None:
            return None
        kind, _ = schema()[self.cls_name][fid]
        body = p[4:] if kind == 'A' else p
        return list(struct.unpack('<%di' % (len(body) // 4), body))

    def set_floats(self, fid, values):
        self._set_numbers(fid, values, 'f')

    def set_ints(self, fid, values):
        self._set_numbers(fid, values, 'i')

    def _set_numbers(self, fid, values, code):
        kind, size = schema()[self.cls_name][fid]
        body = struct.pack('<%d%s' % (len(values), code), *values)
        if kind == 'A':
            if len(body) % size:
                raise ValueError('field %d holds elements of %d bytes' % (fid, size))
            body = struct.pack('<I', len(body) // size) + body
        elif len(body) != size:
            raise ValueError('field %d holds %d bytes' % (fid, size))
        self.set(fid, body)

    # compiled scripts --------------------------------------------------
    def program(self):
        """For a CCompilerBlobCache: {'header': 9 ints, 'code': bytes, 'constants': [bytes of 32]}."""
        words = self.get(2)
        if self.cls_name != 'CCompilerBlobCache' or words is None:
            return None
        body = words[4:]
        header = list(struct.unpack_from('<9I', body, 0))
        code_len, const_len = header[1], header[3]
        start = 36
        code = body[start:start + code_len]
        cstart = start + code_len  # the constants follow the code directly, unaligned
        consts = [body[cstart + i:cstart + i + 32] for i in range(0, const_len, 32)]
        return {'header': header, 'code': code, 'constants': consts}

    def set_program(self, prog):
        """Writes back what program() returned (code and constants may have changed length)."""
        header = list(prog['header'])
        code = bytes(prog['code'])
        consts = b''.join(prog['constants'])
        if len(consts) % 32:
            raise ValueError('constants are 32 bytes each')
        header[1], header[3], header[5] = len(code), len(consts), len(consts) // 32
        body = struct.pack('<9I', *header) + code + consts
        body += b'\0' * (-len(body) % 4)
        self.set(2, struct.pack('<I', len(body) // 4) + body)

    def names(self):
        """For a CCompilerBlobCache: the names in f5 (None where the slot is empty)."""
        return [self.baked.strings[i] if 0 <= i < len(self.baked.strings) else None for i in self.ints(5) or []]

    def functions(self):
        """For a CCompilerBlobCache: the names of the functions its calls refer to (f6)."""
        return [self.baked.strings[i] if 0 <= i < len(self.baked.strings) else None for i in self.ints(6) or []]

    def disassemble(self):
        """For a CCompilerBlobCache: its bytecode as text (see PopcornVm.py)."""
        import PopcornVm
        prog = self.program()
        return PopcornVm.listing(PopcornVm.decode(prog['code']), prog['constants'], self.names(), self.functions())

    def encode(self):
        if self.fields is None:
            return self.raw
        out = [b'\x20', struct.pack('<IH', self.cls, len(self.fields))]
        for fid, payload in self.fields:
            out.append(struct.pack('<H', fid))
            out.append(payload)
        return b''.join(out)


class Baked:
    def __init__(self, data):
        magic, self.version, self.unk8, nobj, nclass, stroff = struct.unpack_from('<IIIIII', data, 0)
        if magic != MAGIC:
            raise ValueError('not a PopcornFX baked file')
        self.unk18 = struct.unpack_from('<I', data, 0x18)[0]
        p = 0x1C
        self.runs = [struct.unpack_from('<II', data, p + 8 * i) for i in range(nclass)]
        p += 8 * nclass
        records = []
        for _ in range(nobj):
            n = struct.unpack_from('<I', data, p)[0]
            records.append(data[p + 4:p + 4 + n])
            p += 4 + n
        if p != stroff:
            raise ValueError('records do not end at the string table')
        count = struct.unpack_from('<I', data, p)[0]
        p += 4
        self.strings = []
        for _ in range(count):
            n = data[p]
            p += 1
            if n & 0x80:
                n = (n & 0x7F) | (data[p] << 7)
                p += 1
            self.strings.append(data[p:p + n].decode('latin1'))
            p += n
        if p != len(data):
            raise ValueError('data after the string table')
        self.objects = [self._split(i + 1, r) for i, r in enumerate(records)]

    def _split(self, number, rec):
        cls, nf = struct.unpack_from('<IH', rec, 1)
        types = schema().get(self.strings[cls])
        fields = []
        p = 7
        ok = rec[0] == 0x20 and types is not None
        for _ in range(nf if ok else 0):
            if p + 2 > len(rec):
                ok = False
                break
            fid = struct.unpack_from('<H', rec, p)[0]
            p += 2
            t = types.get(fid)
            if t is None:
                ok = False
                break
            if t[0] == 'F':
                e = p + t[1]
            else:
                if p + 4 > len(rec):
                    ok = False
                    break
                e = p + 4 + struct.unpack_from('<I', rec, p)[0] * t[1]
            if e > len(rec):
                ok = False
                break
            fields.append([fid, rec[p:e]])
            p = e
        if ok and p != len(rec):
            ok = False
        return Obj(self, number, cls, fields if ok else None, rec)

    # ---------------------------------------------------------------------
    def string_index(self, text):
        """Index of a string, adding it at the end when new (existing indices stay)."""
        if text in self.strings:
            return self.strings.index(text)
        if len(text.encode('latin1')) > 0x3FFF:
            raise ValueError('string too long')
        self.strings.append(text)
        return len(self.strings) - 1

    def of(self, cls_name):
        return [o for o in self.objects if o.cls_name == cls_name]

    def obj(self, number):
        return self.objects[number - 1] if 1 <= number <= len(self.objects) else None

    def platforms(self):
        """{platform name: CLayerGraphCompileCache object}"""
        return {o.string(0): o for o in self.of('CLayerGraphCompileCache')}

    def renderers(self):
        """[(renderer object, {property name: property object})] in file order (all platforms)."""
        out = []
        for r in self.of('CLayerCompileCacheRenderer'):
            props = {}
            for n in r.ints(2) or []:
                o = self.obj(n)
                if o is not None and o.fields is not None:
                    props[o.string(0)] = o
            out.append((r, props))
        return out

    def encode(self):
        recs = [o.encode() for o in self.objects]
        body = b''.join(struct.pack('<I', len(r)) + r for r in recs)
        head_len = 0x1C + 8 * len(self.runs)
        out = [struct.pack('<IIIIII', MAGIC, self.version, self.unk8, len(recs), len(self.runs), head_len + len(body)),
               struct.pack('<I', self.unk18)]
        out += [struct.pack('<II', *r) for r in self.runs]
        out.append(body)
        out.append(struct.pack('<I', len(self.strings)))
        for s in self.strings:
            b = s.encode('latin1')
            out.append(bytes([len(b)]) if len(b) < 0x80 else bytes([0x80 | (len(b) & 0x7F), len(b) >> 7]))
            out.append(b)
        return b''.join(out)


def load(path):
    with open(path, 'rb') as f:
        return Baked(f.read())


# ---------------------------------------------------------------------------
def _show4(b, strings):
    i, = struct.unpack('<i', b)
    f, = struct.unpack('<f', b)
    s = str(i)
    if 0 <= i < len(strings):
        s += ' "%s"' % strings[i][:70]
    if i and 1e-6 < abs(f) < 1e7:
        s += ' (%.6g)' % f
    return s


def dump(baked, only=None):
    for o in baked.objects:
        if only and o.cls_name != only:
            continue
        print('#%d %s' % (o.number, o.cls_name))
        if o.fields is None:
            print('   (not decoded, %d bytes)' % len(o.raw))
            continue
        for fid, p in o.fields:
            kind, size = schema()[o.cls_name][fid]
            body = p[4:] if kind == 'A' else p
            if size % 4 == 0 and len(body) % 4 == 0:
                strings = baked.strings if len(body) <= 48 else []
                text = ', '.join(_show4(body[j:j + 4], strings) for j in range(0, min(len(body), 96), 4))
                if len(body) > 96:
                    text += ' ... (%d values)' % (len(body) // 4)
            else:
                text = body[:48].hex()
            print('   f%d = %s' % (fid, text))


def show_props(baked, platform='PC'):
    pc = baked.platforms().get(platform)
    first = pc.number if pc else 0
    others = sorted(o.number for o in baked.platforms().values() if o.number > first)
    last = others[0] if others else len(baked.objects) + 1
    for r, props in baked.renderers():
        if not first < r.number < last:
            continue
        print('renderer #%d  %s' % (r.number, r.string(4)))
        for name, o in props.items():
            v = o.get(2)
            path = o.string(3) if o.has(3) else None
            text = ''
            if path is not None:
                text = path
            elif v is not None:
                i = struct.unpack('<4i', v)
                f = struct.unpack('<4f', v)
                text = '  '.join('%d' % a if -100000 < a < 100000 else '%.4g' % b for a, b in zip(i, f))
            print('   %-44s type %-3s %s' % (name, o.int(1, ''), text))


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    cmd = args[0]
    if cmd == 'dump':
        only = args[args.index('--class') + 1] if '--class' in args else None
        dump(load(args[1]), only)
    elif cmd == 'props':
        show_props(load(args[1]))
    elif cmd == 'code':
        baked = load(args[1])
        for o in baked.of('CCompilerBlobCache'):
            prog = o.program()
            if prog is None:
                continue
            print('#%d  code %d bytes, header %s' % (o.number, len(prog['code']), prog['header']))
            print('    names: %s' % ', '.join(str(n) for n in o.names()))
            for i, c in enumerate(prog['constants']):
                f = struct.unpack('<8f', c)
                n = struct.unpack('<8i', c)
                same = len(set(n)) == 1
                vals = [('%d' % a) if -65536 < a < 65536 else ('%.6g' % b) for a, b in zip(n, f)]
                print('    const %d: %s' % (i, vals[0] + ' (all lanes)' if same else ' '.join(vals)))
    elif cmd == 'dis':
        baked = load(args[1])
        want = set(int(a) for a in args[2:])
        for o in baked.of('CCompilerBlobCache'):
            if want and o.number not in want:
                continue
            print('#%d  %d instructions' % (o.number, o.program()['header'][0]))
            print('\n'.join('    ' + line for line in o.disassemble().split('\n')))
    elif cmd == 'roundtrip':
        files = []
        for a in args[1:]:
            if os.path.isdir(a):
                for d, _, fs in os.walk(a):
                    files += [os.path.join(d, f) for f in fs if f.endswith('.particles')]
            else:
                files.append(a)
        bad = raw = total = 0
        for f in files:
            data = open(f, 'rb').read()
            b = Baked(data)
            total += len(b.objects)
            raw += sum(1 for o in b.objects if o.fields is None)
            if b.encode() != data:
                bad += 1
                print('differs:', f)
        print('%d files, %d differ; %d objects, %d kept undecoded' % (len(files), bad, total, raw))
        return 1 if bad else 0
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
