"""Reads, edits and writes Diablo II: Resurrected .particles files.

A .particles file is a PopcornFX baked effect (runtime 2.9.5). It holds the
compiled effect, not the editable node graph, and there is no public editor for
it. This module decodes the container so that the parts that are plain data can
be changed: renderer properties (textures, meshes, numbers, colours), curves,
attribute defaults, strings, and the compiled scripts: their constants and,
through PopcornVm.py, their instructions.

Layout (little endian), worked out from the game's 1991 files, 2026-11-13, and
rechecked on its 2206 files, 2026-11-16:

  0x00  u32 magic 0xCA000B11
  0x04  u32 version bytes 02 09 05 01
  0x08  u32 8000
  0x0C  u32 object count
  0x10  u32 class count
  0x14  u32 offset of the string table
  0x18  u32 0
  0x1C  class count x (u32 class, u32 objects of that class); the classes in the order
        they first appear among the objects (encode() rebuilds this table)
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
  CLayerGraphCompileCache         f0 platform name (PC, Switch, PS4, PS5); the objects of that
                                  platform's copy follow it, up to the next one (platform_range)
  CLayerCompileCache              one layer: f20 name, f17 parent layer, f9 its scripts
  CLayerCompileCacheRenderer      f1 particle input objects, f2 property objects, f4 material (.pkma)
  CLayerCompileCacheRendererProperty
                                  f0 name ("Blend.TextureBase", "General.Mesh", "Transparent.Type" ...),
                                  f1 type code (3 int, 7 float, 14 path, ...), f2 four 32-bit values,
                                  f3 path string
  CParticleNodeSamplerData_Curve  f17 key times (in order), f18 key values (the same number per key),
                                  f19 tangents (two per value)
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
                                    w6 w7 w8 the registers used in banks p, q, r (highest index + 1);
                                    w2 and w4 are always 0;
                                    the bytecode (starts 7C, ends 7D);
                                    the constants, 32 bytes each (a value repeated for eight lanes,
                                    or eight different numbers), directly after the code;
                                    zero bytes up to the next word.
                                  validate() checks all of this; every file of the game passes.

usage:
  PopcornBaked.py dump <file> [--class <name>]          readable listing
  PopcornBaked.py props <file> [--platform PC]          renderers and their properties
  PopcornBaked.py code <file>                           compiled scripts: names, constants, bytecode size
  PopcornBaked.py dis <file> [object number ...]        compiled scripts as readable instructions
  PopcornBaked.py diff <old file> <new file>            what changed, by object and field
  PopcornBaked.py check <file or folder> ...            consistency checks (run them on an edited file)
  PopcornBaked.py roundtrip <file or folder> ... [--check]
                                                        parse + write must give the same bytes
"""
import argparse
import json
import os
import struct
import sys

MAGIC = 0xCA000B11
_DIR = os.path.dirname(os.path.abspath(__file__))
_SCHEMA = None


def schema():
    global _SCHEMA
    if _SCHEMA is None:
        with open(os.path.join(_DIR, 'PopcornBaked.schema.json'), encoding='utf-8') as f:
            raw = json.load(f)
        _SCHEMA = {c: {int(f): (t[0], int(t[1:])) for f, t in fields.items()} for c, fields in raw.items()}
    return _SCHEMA


def _vm():
    """PopcornVm, found next to this file also when it is not on the import path (python -I)."""
    if _DIR not in sys.path:
        sys.path.insert(0, _DIR)
    import PopcornVm
    return PopcornVm


class Obj:
    """One object. `fields` is a list of [field id, payload bytes] in file order, or
    None when the record could not be split (then `raw` is written back as it was)."""

    def __init__(self, baked, number, cls, fields, raw):
        self.baked, self.number, self.cls, self.fields, self.raw = baked, number, cls, fields, raw

    def __repr__(self):
        return '<#%d %s>' % (self.number, self.cls_name)

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

    def _body(self, fid):
        p = self.get(fid)
        if p is None:
            return None
        kind, _ = schema()[self.cls_name][fid]
        return p[4:] if kind == 'A' else p

    def floats(self, fid):
        body = self._body(fid)
        return None if body is None else list(struct.unpack('<%df' % (len(body) // 4), body[:len(body) // 4 * 4]))

    def ints(self, fid):
        body = self._body(fid)
        return None if body is None else list(struct.unpack('<%di' % (len(body) // 4), body[:len(body) // 4 * 4]))

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
        if self.cls_name != 'CCompilerBlobCache' or words is None or len(words) < 40:
            return None
        body = words[4:]
        header = list(struct.unpack_from('<9I', body, 0))
        code_len, const_len = header[1], header[3]
        start = 36
        code = body[start:start + code_len]
        cstart = start + code_len  # the constants follow the code directly, unaligned
        consts = [body[cstart + i:cstart + i + 32] for i in range(0, const_len, 32)]
        return {'header': header, 'code': code, 'constants': consts}

    def set_program(self, prog, recount=True):
        """Writes back what program() returned (code and constants may have changed length).
        The header's sizes follow the code and constants. With `recount` (the default) the
        code is decoded and the instruction and register counts are set from it too; that
        raises ValueError if the code does not decode. recount=False keeps them as given."""
        header = list(prog['header'])
        code = bytes(prog['code'])
        consts = b''.join(prog['constants'])
        if len(consts) % 32:
            raise ValueError('constants are 32 bytes each')
        header[1], header[3], header[5] = len(code), len(consts), len(consts) // 32
        if recount:
            header[0], header[6], header[7], header[8] = _vm().counts(_vm().decode(code))
        body = struct.pack('<9I', *header) + code + consts
        body += b'\0' * (-len(body) % 4)
        self.set(2, struct.pack('<I', len(body) // 4) + body)

    def instructions(self):
        """For a CCompilerBlobCache: its decoded bytecode (see PopcornVm.decode)."""
        return _vm().decode(self.program()['code'])

    def set_instructions(self, instructions):
        """Encodes the instructions back into the script (constants unchanged, counts updated)."""
        prog = self.program()
        prog['code'] = _vm().encode(instructions)
        self.set_program(prog)

    def names(self):
        """For a CCompilerBlobCache: the names in f5 (None where the slot is empty)."""
        return [self.baked.strings[i] if 0 <= i < len(self.baked.strings) else None for i in self.ints(5) or []]

    def functions(self):
        """For a CCompilerBlobCache: the names of the functions its calls refer to (f6)."""
        return [self.baked.strings[i] if 0 <= i < len(self.baked.strings) else None for i in self.ints(6) or []]

    def disassemble(self):
        """For a CCompilerBlobCache: its bytecode as text (see PopcornVm.py)."""
        vm = _vm()
        prog = self.program()
        return vm.listing(vm.decode(prog['code']), prog['constants'], self.names(), self.functions())

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
        if len(data) < 0x1C:
            raise ValueError('too short for a PopcornFX baked file')
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
        types = schema().get(self.strings[cls]) if cls < len(self.strings) else None
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

    def platform_range(self, name='PC'):
        """(first, end): the objects of a platform's copy are those numbered first < n < end
        (first is its CLayerGraphCompileCache). None when the file has no such copy."""
        plats = self.platforms()
        if name not in plats:
            return None
        first = plats[name].number
        later = [o.number for o in plats.values() if o.number > first]
        return first, min(later) if later else len(self.objects) + 1

    def platform_objects(self, name='PC'):
        """The objects of one platform's copy, in file order ([] when there is none)."""
        r = self.platform_range(name)
        return [] if r is None else self.objects[r[0]:r[1] - 1]

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

    def class_table(self):
        """The header's class table for the objects as they are now: [(class, count)] in
        the order the classes first appear (the game's files all have it so)."""
        counts = {}
        for o in self.objects:
            counts[o.cls] = counts.get(o.cls, 0) + 1
        return list(counts.items())

    def validate(self):
        """Consistency checks on what an edit can get wrong. Returns a list of problems
        ([] for every file of the game)."""
        problems = []
        n = len(self.objects)
        nstr = len(self.strings)

        def bad(o, msg):
            problems.append('#%d %s: %s' % (o.number, o.cls_name, msg))

        if [tuple(r) for r in self.runs] != self.class_table():
            problems.append('the class table does not match the objects (encode() rebuilds it)')
        for o in self.objects:
            if o.cls >= nstr:
                problems.append('#%d: class %d is not a string' % (o.number, o.cls))
        vm = _vm()
        checked = {}
        for o in self.objects:
            if o.fields is None or o.cls >= nstr:
                continue
            c = o.cls_name
            if c == 'CCompilerBlobCache':
                for msg in self._check_script(o, vm, checked):
                    bad(o, msg)
            elif c == 'CLayerCompileCacheRenderer':
                for fid in (1, 2):
                    for ref in o.ints(fid) or []:
                        if not 1 <= ref <= n:
                            bad(o, 'f%d refers to object %d (the file has %d)' % (fid, ref, n))
            elif c == 'CLayerCompileCache':
                for ref in o.ints(9) or []:
                    t = self.obj(ref)
                    if t is None or t.cls_name != 'CCompilerBlobCache':
                        bad(o, 'script %d is not a CCompilerBlobCache' % ref)
            elif c == 'CLayerCompileCacheRendererProperty':
                for fid in (0, 3):
                    i = o.int(fid)
                    if (i is not None or fid == 0) and not (i is not None and 0 <= i < nstr):
                        bad(o, 'f%d is not a string (%s)' % (fid, i))
            elif c == 'CParticleNodeSamplerData_Curve':
                t, v, g = o.floats(17), o.floats(18), o.floats(19)
                if t is None:
                    continue
                if v is not None and t and len(v) % len(t):
                    bad(o, '%d values for %d keys' % (len(v), len(t)))
                if v is not None and g is not None and len(g) != 2 * len(v):
                    bad(o, '%d tangents for %d values (two each)' % (len(g), len(v)))
                if any(t[i] > t[i + 1] for i in range(len(t) - 1)):
                    bad(o, 'key times are out of order')
        return problems

    def _check_script(self, o, vm, cache):
        f4, f5, f6 = o.ints(4) or [], o.ints(5) or [], o.ints(6) or []
        nstr = len(self.strings)
        out = []
        if len(f4) != 5 * len(f5):
            out.append('f4 has %d words for %d externals (five each)' % (len(f4), len(f5)))
        if any(not -1 <= i < nstr for i in f5):
            out.append('an external name in f5 is not a string')
        if any(not 0 <= i < nstr for i in f6):
            out.append('a function name in f6 is not a string')
        words = o.get(2)
        key = (words, len(f5), len(f6))
        if key in cache:
            return out + cache[key]
        found = []
        cache[key] = found
        prog = o.program()
        if prog is None:
            found.append('no program in f2')
            return out + found
        h = prog['header']
        size = len(words) - 4
        if 36 + h[1] + h[3] > size:
            found.append('code and constants (%d + %d bytes) run past f2' % (h[1], h[3]))
            return out + found
        if any(words[4 + 36 + h[1] + h[3]:]) or size - (36 + h[1] + h[3]) >= 4:
            found.append('f2 has data after the constants')
        if h[2] or h[4]:
            found.append('header words 2 and 4 are not 0')
        if h[3] != 32 * h[5]:
            found.append('header: %d bytes of constants but %d constants' % (h[3], h[5]))
        try:
            ins = vm.decode(prog['code'])
        except ValueError as e:
            found.append('code does not decode: %s' % e)
            return out + found
        want = vm.counts(ins)
        have = (h[0], h[6], h[7], h[8])
        if want != have:
            found.append('header counts (instructions, registers p q r) are %s, the code needs %s' % (have, want))
        if not ins or ins[0]['op'] != 0x7C or ins[-1]['op'] != 0x7D:
            found.append('code does not start with begin and end with end')
        for i in ins:
            for index, kind, typ in i['regs']:
                if kind == 0 and typ != 0xFF and index >= h[5]:
                    found.append('%04X uses constant %d of %d' % (i['at'], index, h[5]))
            if 'name' in i and i['name'] >= len(f5):
                found.append('%04X uses external %d of %d' % (i['at'], i['name'], len(f5)))
            if i['op'] == 0x7B:
                if i['fn'] >= len(f6):
                    found.append('%04X calls function %d of %d' % (i['at'], i['fn'], len(f6)))
                if i['obj'] >= len(f5):
                    found.append('%04X calls on external %d of %d' % (i['at'], i['obj'], len(f5)))
        return out + found

    def encode(self):
        recs = [o.encode() for o in self.objects]
        self.runs = self.class_table()
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

    def save(self, path):
        data = self.encode()
        with open(path, 'wb') as f:
            f.write(data)
        return data


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


def const_text(c):
    """A 32-byte script constant as text: one value when all eight lanes agree."""
    f = struct.unpack('<8f', c)
    n = struct.unpack('<8i', c)
    vals = [('%d' % a) if -65536 < a < 65536 else ('%.6g' % b) for a, b in zip(n, f)]
    return vals[0] + ' (all lanes)' if len(set(n)) == 1 else ' '.join(vals)


def _field_text(o, fid, payload, limit=96):
    kind, size = schema()[o.cls_name][fid]
    body = payload[4:] if kind == 'A' else payload
    if size % 4 or len(body) % 4:
        return body[:48].hex()
    strings = o.baked.strings if len(body) <= 48 else []
    text = ', '.join(_show4(body[j:j + 4], strings) for j in range(0, min(len(body), limit), 4))
    if len(body) > limit:
        text += ' ... (%d values)' % (len(body) // 4)
    return text


def dump(baked, only=None):
    for o in baked.objects:
        if only and o.cls_name != only:
            continue
        print('#%d %s' % (o.number, o.cls_name))
        if o.fields is None:
            print('   (not decoded, %d bytes)' % len(o.raw))
            continue
        for fid, p in o.fields:
            print('   f%d = %s' % (fid, _field_text(o, fid, p)))


def show_props(baked, platform='PC'):
    rng = baked.platform_range(platform)
    if rng is None:
        print('no %s copy (the file has: %s)' % (platform, ', '.join(sorted(str(p) for p in baked.platforms()))))
        return 1
    for r, props in baked.renderers():
        if not rng[0] < r.number < rng[1]:
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
    return 0


def diff(a, b):
    """What changed from `a` to `b` (two Baked), as lines of text."""
    out = []
    for name in ('version', 'unk8', 'unk18'):
        if getattr(a, name) != getattr(b, name):
            out.append('header %s: %08X -> %08X' % (name, getattr(a, name), getattr(b, name)))
    for i in range(min(len(a.strings), len(b.strings))):
        if a.strings[i] != b.strings[i]:
            out.append('string %d: "%s" -> "%s"' % (i, a.strings[i], b.strings[i]))
    for i in range(len(a.strings), len(b.strings)):
        out.append('string %d added: "%s"' % (i, b.strings[i]))
    for i in range(len(b.strings), len(a.strings)):
        out.append('string %d removed: "%s"' % (i, a.strings[i]))
    for oa, ob in zip(a.objects, b.objects):
        ra, rb = oa.encode(), ob.encode()
        if ra == rb and oa.cls_name == ob.cls_name:
            continue
        head = '#%d %s' % (oa.number, oa.cls_name)
        if oa.cls_name != ob.cls_name:
            out.append('%s: is now a %s' % (head, ob.cls_name))
            continue
        if oa.fields is None or ob.fields is None:
            out.append('%s: record changed (%d -> %d bytes, not decoded)' % (head, len(ra), len(rb)))
            continue
        ids = sorted(set(f for f, _ in oa.fields) | set(f for f, _ in ob.fields))
        for fid in ids:
            pa, pb = oa.get(fid), ob.get(fid)
            if pa == pb:
                continue
            if pa is None:
                out.append('%s f%d added: %s' % (head, fid, _field_text(ob, fid, pb)))
            elif pb is None:
                out.append('%s f%d removed (was %s)' % (head, fid, _field_text(oa, fid, pa)))
            elif oa.cls_name == 'CCompilerBlobCache' and fid == 2:
                out += ['%s %s' % (head, line) for line in _diff_program(oa, ob)]
            else:
                out.append('%s f%d: %s' % (head, fid, _diff_values(oa, ob, fid, pa, pb)))
    for o in a.objects[len(b.objects):]:
        out.append('#%d %s removed' % (o.number, o.cls_name))
    for o in b.objects[len(a.objects):]:
        out.append('#%d %s added' % (o.number, o.cls_name))
    return out


def _diff_values(oa, ob, fid, pa, pb):
    kind, size = schema()[oa.cls_name][fid]
    ba, bb = (pa[4:], pb[4:]) if kind == 'A' else (pa, pb)
    if size % 4 or len(ba) % 4 or len(bb) % 4 or len(ba) <= 32 or len(bb) <= 32:
        return '%s -> %s' % (_field_text(oa, fid, pa), _field_text(ob, fid, pb))
    if len(ba) != len(bb):
        return '%d -> %d values' % (len(ba) // 4, len(bb) // 4)
    changed = [j for j in range(0, len(ba), 4) if ba[j:j + 4] != bb[j:j + 4]]
    parts = ['[%d] %s -> %s' % (j // 4, _show4(ba[j:j + 4], []), _show4(bb[j:j + 4], [])) for j in changed[:8]]
    more = ' ... (%d values differ)' % len(changed) if len(changed) > 8 else ''
    return '; '.join(parts) + more


def _diff_program(oa, ob):
    pa, pb = oa.program(), ob.program()
    if pa is None or pb is None:
        return ['f2 changed']
    out = []
    words = [i for i in range(9) if pa['header'][i] != pb['header'][i]]
    if words:
        out.append('header ' + ', '.join('w%d %d -> %d' % (i, pa['header'][i], pb['header'][i]) for i in words))
    if pa['code'] != pb['code']:
        out.append('code %d -> %d bytes' % (len(pa['code']), len(pb['code'])))
    ca, cb = pa['constants'], pb['constants']
    for i in range(max(len(ca), len(cb))):
        x = ca[i] if i < len(ca) else None
        y = cb[i] if i < len(cb) else None
        if x != y:
            out.append('const %d: %s -> %s' % (i, const_text(x) if x else '(none)', const_text(y) if y else '(none)'))
    return out or ['f2 changed (padding)']


def _files(paths):
    for a in paths:
        if os.path.isdir(a):
            for d, _, fs in os.walk(a):
                for f in sorted(fs):
                    if f.endswith('.particles'):
                        yield os.path.join(d, f)
        else:
            yield a


def main(argv=None):
    ap = argparse.ArgumentParser(prog='PopcornBaked.py', description='Diablo II: Resurrected .particles files',
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split('usage:')[1])
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('dump')
    p.add_argument('file')
    p.add_argument('--class', dest='cls')
    p = sub.add_parser('props')
    p.add_argument('file')
    p.add_argument('--platform', default='PC')
    p = sub.add_parser('code')
    p.add_argument('file')
    p = sub.add_parser('dis')
    p.add_argument('file')
    p.add_argument('objects', nargs='*', type=int)
    p = sub.add_parser('diff')
    p.add_argument('old')
    p.add_argument('new')
    p = sub.add_parser('check')
    p.add_argument('paths', nargs='+')
    p = sub.add_parser('roundtrip')
    p.add_argument('paths', nargs='+')
    p.add_argument('--check', action='store_true', help='also run the consistency checks')
    args = ap.parse_args(argv)

    if args.cmd == 'dump':
        dump(load(args.file), args.cls)
    elif args.cmd == 'props':
        return show_props(load(args.file), args.platform)
    elif args.cmd == 'code':
        baked = load(args.file)
        for o in baked.of('CCompilerBlobCache'):
            prog = o.program()
            if prog is None:
                continue
            print('#%d  code %d bytes, header %s' % (o.number, len(prog['code']), prog['header']))
            print('    names: %s' % ', '.join(str(n) for n in o.names()))
            for i, c in enumerate(prog['constants']):
                print('    const %d: %s' % (i, const_text(c)))
    elif args.cmd == 'dis':
        baked = load(args.file)
        want = set(args.objects)
        status = 0
        for o in baked.of('CCompilerBlobCache'):
            if want and o.number not in want:
                continue
            prog = o.program()
            if prog is None:
                continue
            print('#%d  %d instructions' % (o.number, prog['header'][0]))
            try:
                text = o.disassemble()
            except ValueError as e:
                print('    (does not decode: %s)' % e)
                status = 1
                continue
            print('\n'.join('    ' + line for line in text.split('\n')))
        return status
    elif args.cmd == 'diff':
        lines = diff(load(args.old), load(args.new))
        print('\n'.join(lines) if lines else 'no differences')
        return 1 if lines else 0
    elif args.cmd == 'check':
        count = bad = 0
        for f in _files(args.paths):
            count += 1
            try:
                problems = load(f).validate()
            except Exception as e:  # noqa: BLE001 - report the file, go on
                problems = ['does not load: %s' % e]
            if problems:
                bad += 1
                print(f)
                print('\n'.join('   ' + x for x in problems))
        print('%d file(s), %d with problems' % (count, bad))
        return 1 if bad else 0
    elif args.cmd == 'roundtrip':
        files = list(_files(args.paths))
        differ = failed = invalid = raw = total = 0
        for f in files:
            with open(f, 'rb') as fh:
                data = fh.read()
            try:
                b = Baked(data)
                out = b.encode()
            except Exception as e:  # noqa: BLE001 - report the file, go on
                failed += 1
                print('fails: %s: %s' % (f, e))
                continue
            total += len(b.objects)
            raw += sum(1 for o in b.objects if o.fields is None)
            if out != data:
                differ += 1
                print('differs:', f)
            if args.check:
                problems = b.validate()
                if problems:
                    invalid += 1
                    print('problems: %s: %s' % (f, '; '.join(problems[:3])))
        print('%d files, %d differ, %d fail to read%s; %d objects, %d kept undecoded'
              % (len(files), differ, failed, ', %d with problems' % invalid if args.check else '', total, raw))
        return 1 if differ or failed or invalid else 0
    return 0


if __name__ == '__main__':
    sys.exit(main())
