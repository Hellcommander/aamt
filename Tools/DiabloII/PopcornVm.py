"""Bytecode of the compiled scripts in Diablo II: Resurrected .particles files.

Each CCompilerBlobCache object of a .particles file (see PopcornBaked.py) holds one
script for PopcornFX's CPU virtual machine. This module turns its bytecode into a
list of instructions and back, and prints it as readable text.

Worked out from the game's own files, 2026-11-13: all 11241 distinct scripts found
in the 1991 files decode with exactly the instruction count their header gives, and
encode back to the same bytes. Rechecked 2026-11-16 on the game's 2206 files (11849
distinct scripts), which added opcode 76.

Operand (4 bytes): u16 index, u8 kind, u8 type.
  kind  00 constant (index into the script's 32-byte constants)
        20 / 40 / 60 register, in three separate banks (shown p, q, r)
        80 immediate: the index itself is the value (0, 1, 2 ...)
        FF none (with type FF)
  type  20-23 float1-4, 1A-1D int1-4, 02 bool, 04 bool3, 00 a context handle, 25 unknown

Instructions (opcode byte first):
  7C xx                      begin (xx always 0)
  7D                         end
  69 reg, u16 name           load: reg = the external the script's name table names
  6A reg, u16 name           store: that external = reg
  6B u16 name                the external is declared, not written
  6C dst, src                convert (int -> float, bool -> int, ...)
  6F dst, src                spread one number over a vector
  6D n, dst, n+2 regs        build a vector from parts
  6E sub, u16 mask, dst, src swizzle; mask has 3 bits per output part:
                             0-3 = x y z w of the source, 4 = 0, 5 = 1 (4 and 5 presumed)
  71 72 73 74 dst, a, b      add, subtract, multiply, divide
  75 dst, a, b, c            a * b + c
  76 dst, a, b, m, s         integer a / b, b a constant; m and s are the compiler's
                             magic multiplier and shift for it (b 100: m 0x51EB851F, s 5).
                             First seen 2026-11-16 in one script of the game's newer files.
  70 sub, dst, a, b          integer / bool operations and comparisons, see SUB70
  77 sub, dst, a             one-argument function, see FUNCTIONS
  78 sub, dst, a, b          two-argument function, see FUNCTIONS
  79 sub, dst, a, b, c       three-argument function: lerp, clamp, within (SUB79)
  7A dst, a, b, mask         choose: mask ? b : a
  7B flag, i16 obj, u16 fn, u8 argc, dst, argc x (u8 tag, reg)
                             call function `fn` of the script's f4 table; obj is -1 or
                             a name index (a sampler or event the call acts on)

Names (2026-11-26): read from the game's own VM, in the D2R memory image (image 95032 =
Steam): the bytecode loader at RVA 0x16D155A dispatches opcodes 69-7D through a table at
0x2A05A30, followed by the VM's own name lists (0x2A05AD8): the three-argument functions
(lerp clamp within), the opcode mnemonics (ld st stz cvt vct swz dup mop add sub mul div
madd idivmi mfn1 mfn2 mfn3 sel call prlg eplg), the 70 sub-operations and the 53 one- and
two-argument functions, indexed by sub-code ("hp" = precise, "lp" = fast). The script-
language names in FUNCTIONS are the ones the function descriptors carry (table 0x1DA4330,
looked up through 0x1DD8D20 by 0xC49F30). Every name fits how the game's 15176 distinct
scripts use it (operand types, argument counts, constants).
"""
import re
import struct

TYPE_NAMES = {0x20: 'f1', 0x21: 'f2', 0x22: 'f3', 0x23: 'f4', 0x1A: 'i1', 0x1B: 'i2', 0x1C: 'i3', 0x1D: 'i4',
              0x02: 'b1', 0x04: 'b3', 0x00: 'ctx', 0x25: 't25', 0xFF: ''}
TYPE_WIDTH = {'f1': 1, 'f2': 2, 'f3': 3, 'f4': 4, 'i1': 1, 'i2': 2, 'i3': 3, 'i4': 4, 'b1': 1, 'b3': 3}
KIND_NAMES = {0x00: 'c', 0x20: 'p', 0x40: 'q', 0x60: 'r', 0x80: '#'}

OPS = {0x7C: 'begin', 0x7D: 'end', 0x69: 'load', 0x6A: 'store', 0x6B: 'keep', 0x6C: 'convert', 0x6F: 'spread',
       0x6D: 'vector', 0x6E: 'swizzle', 0x71: 'add', 0x72: 'sub', 0x73: 'mul', 0x74: 'div', 0x75: 'muladd', 0x76: 'idiv',
       0x70: 'logic', 0x77: 'fn1', 0x78: 'fn2', 0x79: 'fn3', 0x7A: 'choose', 0x7B: 'call'}
# The game VM's own mnemonics for opcodes 69-7D (OPS above are this module's readable names).
VM_MNEMONICS = dict(zip(range(0x69, 0x7E), 'ld st stz cvt vct swz dup mop add sub mul div madd idivmi mfn1 mfn2 mfn3 '
                                           'sel call prlg eplg'.split()))
# 70 sub-operations, by sub-code (the VM's names: cmplt, cmple, ...).
SUB70 = dict(enumerate('add sub mul div mod neg sll sar and or xor not lt le gt ge eq ne'.split()))
# 77 / 78 functions, by sub-code: one table for both (1D dot and the others from 19 on take two).
FUNCTIONS = dict(enumerate(
    'sqrt rsqrt cbrt length normalize sin cos sincos tan asin acos atan atan2 exp exp2 log log2 rcp '
    'abs sign ceil floor frac fracSign saturate step discretize min max dot cross '
    'fast_sqrt fast_rsqrt fast_cbrt fast_length fast_normalize fast_sin fast_cos fast_sincos fast_tan fast_asin '
    'fast_acos fast_atan fast_atan2 fast_exp fast_exp2 fast_log fast_log2 fast_rcp all any isfinite isinf'.split()))
SUB77 = FUNCTIONS
SUB78 = FUNCTIONS
SUB79 = {0: 'lerp', 1: 'clamp', 2: 'within'}

# opcode -> (has sub byte, number of register operands, trailing u16 fields)
_FIXED = {0x6C: (False, 2), 0x6F: (False, 2), 0x71: (False, 3), 0x72: (False, 3), 0x73: (False, 3), 0x74: (False, 3),
          0x75: (False, 4), 0x76: (False, 5), 0x7A: (False, 4), 0x77: (True, 2), 0x70: (True, 3), 0x78: (True, 3),
          0x79: (True, 4)}


def _reg(code, p):
    return struct.unpack_from('<HBB', code, p)


def decode(code):
    """Bytecode -> list of dicts: {'op', 'sub'?, 'regs': [(index, kind, type)], 'name'?, 'mask'?,
    'obj'?, 'fn'?, 'tags'?}. Raises ValueError on an opcode it does not know."""
    out = []
    p = 0
    n = len(code)
    while p < n:
        op = code[p]
        ins = {'op': op, 'at': p, 'regs': []}
        if op == 0x7C:
            ins['sub'] = code[p + 1]
            p += 2
        elif op == 0x7D:
            p += 1
        elif op in (0x69, 0x6A):
            ins['regs'] = [_reg(code, p + 1)]
            ins['name'] = struct.unpack_from('<H', code, p + 5)[0]
            p += 7
        elif op == 0x6B:
            ins['name'] = struct.unpack_from('<H', code, p + 1)[0]
            p += 3
        elif op in _FIXED:
            has_sub, count = _FIXED[op]
            q = p + 1
            if has_sub:
                ins['sub'] = code[q]
                q += 1
            ins['regs'] = [_reg(code, q + 4 * i) for i in range(count)]
            p = q + 4 * count
        elif op == 0x6D:
            ins['sub'] = code[p + 1]
            count = code[p + 1] + 2
            ins['regs'] = [_reg(code, p + 2 + 4 * i) for i in range(count)]
            p += 2 + 4 * count
        elif op == 0x6E:
            ins['sub'] = code[p + 1]
            ins['mask'] = struct.unpack_from('<H', code, p + 2)[0]
            ins['regs'] = [_reg(code, p + 4), _reg(code, p + 8)]
            p += 12
        elif op == 0x7B:
            ins['sub'] = code[p + 1]
            ins['obj'], ins['fn'] = struct.unpack_from('<hH', code, p + 2)
            argc = code[p + 6]
            ins['regs'] = [_reg(code, p + 7)] + [_reg(code, p + 12 + 5 * i) for i in range(argc)]
            ins['tags'] = [code[p + 11 + 5 * i] for i in range(argc)]
            p += 11 + 5 * argc
        else:
            raise ValueError('unknown opcode %02X at offset %d' % (op, p))
        if p > n:
            raise ValueError('instruction at offset %d runs past the end' % ins['at'])
        out.append(ins)
    return out


def encode(instructions):
    out = bytearray()
    for ins in instructions:
        op = ins['op']
        regs = ins.get('regs', [])
        out.append(op)
        if op == 0x7C:
            out.append(ins.get('sub', 0))
        elif op == 0x7D:
            pass
        elif op in (0x69, 0x6A):
            out += struct.pack('<HBB', *regs[0]) + struct.pack('<H', ins['name'])
        elif op == 0x6B:
            out += struct.pack('<H', ins['name'])
        elif op in _FIXED:
            has_sub, count = _FIXED[op]
            if len(regs) != count:
                raise ValueError('%s takes %d operands' % (OPS[op], count))
            if has_sub:
                out.append(ins['sub'])
            for r in regs:
                out += struct.pack('<HBB', *r)
        elif op == 0x6D:
            out.append(len(regs) - 2)
            for r in regs:
                out += struct.pack('<HBB', *r)
        elif op == 0x6E:
            out.append(ins['sub'])
            out += struct.pack('<H', ins['mask'])
            for r in regs:
                out += struct.pack('<HBB', *r)
        elif op == 0x7B:
            out.append(ins['sub'])
            out += struct.pack('<hHB', ins['obj'], ins['fn'], len(regs) - 1)
            out += struct.pack('<HBB', *regs[0])
            for tag, r in zip(ins['tags'], regs[1:]):
                out.append(tag)
                out += struct.pack('<HBB', *r)
        else:
            raise ValueError('unknown opcode %02X' % op)
    return bytes(out)


def counts(instructions):
    """(number of instructions, registers used in bank p, q, r): what header words 0, 6, 7
    and 8 of a script hold (true for every script of the game, 2026-11-16)."""
    top = {0x20: 0, 0x40: 0, 0x60: 0}
    for ins in instructions:
        for index, kind, _ in ins.get('regs', []):
            if kind in top:
                top[kind] = max(top[kind], index + 1)
    return len(instructions), top[0x20], top[0x40], top[0x60]


def constant_value(const, type_name):
    """The numbers of a 32-byte constant as the given operand type reads them."""
    width = TYPE_WIDTH.get(type_name, 1)
    if type_name.startswith('f'):
        return struct.unpack_from('<%df' % width, const)
    return struct.unpack_from('<%di' % width, const)


def show_reg(reg, constants=None):
    index, kind, typ = reg
    if kind == 0xFF:
        return '-'
    t = TYPE_NAMES.get(typ, 't%02X' % typ)
    if kind == 0x00 and constants is not None and index < len(constants):
        vals = constant_value(constants[index], t)
        text = ', '.join(('%.6g' % v) if isinstance(v, float) else str(v) for v in vals)
        return '%s(%s)[c%d]' % (t, text, index)
    if kind == 0x80:
        return '%s(#%d)' % (t, index)
    return '%s%d:%s' % (KIND_NAMES.get(kind, 'k%02X_' % kind), index, t)


def show_mask(mask, width):
    parts = []
    for i in range(width):
        v = (mask >> (3 * i)) & 7
        parts.append('xyzw01??'[v])
    return ''.join(parts)


def function_label(functions, i):
    """A call's function as the listing shows it: its name, "name@i" when the script's function
    table has that name more than once, "fn<i>" when it has none."""
    if not functions or i >= len(functions) or functions[i] is None:
        return 'fn%d' % i
    name = functions[i]
    return name if functions.count(name) == 1 else '%s@%d' % (name, i)


def listing(instructions, constants=None, names=None, functions=None):
    """Readable text, one instruction per line. assemble() reads it back."""
    def ext(i):
        return names[i] if names and i < len(names) and names[i] is not None else 'name%d' % i

    lines = []
    for ins in instructions:
        op = ins['op']
        regs = [show_reg(r, constants) for r in ins.get('regs', [])]
        sub = ins.get('sub')
        if op == 0x7C:
            text = 'begin'
        elif op == 0x7D:
            text = 'end'
        elif op == 0x69:
            text = '%s = load %s' % (regs[0], ext(ins['name']))
        elif op == 0x6A:
            text = 'store %s = %s' % (ext(ins['name']), regs[0])
        elif op == 0x6B:
            text = 'keep %s' % ext(ins['name'])
        elif op in (0x6C, 0x6F):
            text = '%s = %s %s' % (regs[0], OPS[op], regs[1])
        elif op == 0x6D:
            text = '%s = vector(%s)' % (regs[0], ', '.join(regs[1:]))
        elif op == 0x6E:
            width = TYPE_WIDTH.get(TYPE_NAMES.get(ins['regs'][0][2], ''), 1)
            text = '%s = %s.%s   (swizzle %02X/%04X)' % (regs[0], regs[1], show_mask(ins['mask'], width), sub, ins['mask'])
        elif op in (0x71, 0x72, 0x73, 0x74):
            text = '%s = %s %s %s' % (regs[0], regs[1], {0x71: '+', 0x72: '-', 0x73: '*', 0x74: '/'}[op], regs[2])
        elif op == 0x75:
            text = '%s = %s * %s + %s' % tuple(regs)
        elif op == 0x76:
            text = '%s = %s / %s   (integer: magic %s, shift %s)' % tuple(regs)
        elif op == 0x7A:
            text = '%s = %s ? %s : %s' % (regs[0], regs[3], regs[2], regs[1])
        elif op == 0x70:
            text = '%s = %s(%s)' % (regs[0], SUB70.get(sub, 'logic%02X' % sub), ', '.join(r for r in regs[1:] if r != '-'))
        elif op == 0x77:
            text = '%s = %s(%s)' % (regs[0], SUB77.get(sub, 'fn1_%02X' % sub), regs[1])
        elif op == 0x78:
            text = '%s = %s(%s)' % (regs[0], SUB78.get(sub, 'fn2_%02X' % sub), ', '.join(regs[1:]))
        elif op == 0x79:
            text = '%s = %s(%s)' % (regs[0], SUB79.get(sub, 'fn3_%02X' % sub), ', '.join(regs[1:]))
        elif op == 0x7B:
            fn = function_label(functions, ins['fn'])
            target = '' if ins['obj'] < 0 else ' on %s' % ext(ins['obj'])
            args = ', '.join('%s' % a for a in regs[1:])
            head = '' if regs[0] == '-' else '%s = ' % regs[0]
            text = '%scall %s(%s)%s   (flag %02X, tags %s)' % (head, fn, args, target, sub, ' '.join('%02X' % t for t in ins['tags']))
        else:
            text = '?? %02X' % op
        lines.append('%04X  %s' % (ins['at'], text))
    return '\n'.join(lines)


# --- text back to instructions --------------------------------------------------------------

_TYPE_CODES = {v: k for k, v in TYPE_NAMES.items() if v}
_KIND_CODES = {v: k for k, v in KIND_NAMES.items() if v != '#'}
_OPERAND = re.compile(r'-(?![\w.])|[pqr]\d+:\w*|\w+\(#\d+\)|\w+\([^()]*\)\[c\d+\]|[fib]\d\([^()#]*\)(?!\[)')
_NONE = (0xFFFF, 0xFF, 0xFF)


def _type_code(name):
    if name in _TYPE_CODES:
        return _TYPE_CODES[name]
    if name == 'ctx':
        return 0x00
    if re.fullmatch(r't[0-9A-Fa-f]{2}', name):
        return int(name[1:], 16)
    raise ValueError('unknown operand type "%s"' % name)


def pack_constant(type_name, values):
    """32 bytes for a constant of that operand type: its numbers repeated over the eight lanes,
    the way the compiler writes them (x y z x y z x y for a float3)."""
    values = list(values)
    width = TYPE_WIDTH.get(type_name, 1)
    if len(values) != width:
        raise ValueError('%s takes %d number(s), not %d' % (type_name, width, len(values)))
    lanes = [values[i % width] for i in range(8)]
    if type_name.startswith('f'):
        return struct.pack('<8f', *[float(v) for v in lanes])
    return struct.pack('<8i', *[int(v) for v in lanes])


def parse_operand(text, pool=None):
    """'p3:f1' (register), 'f1(0.5)[c3]' (constant 3; the value shown is not read), 'i1(#2)'
    (immediate), '-' (none) -> (index, kind, type). With `pool` (the script's constants, a list
    of 32-byte values, extended in place) a value without an index, 'f3(1, 0.5, 0)', is a new
    constant: an equal one is reused, otherwise it is added."""
    text = text.strip()
    if text == '-':
        return _NONE
    m = re.fullmatch(r'([pqr])(\d+):(\w*)', text)
    if m:
        return int(m.group(2)), _KIND_CODES[m.group(1)], _type_code(m.group(3) or 'ctx')
    m = re.fullmatch(r'(\w+)\(#(\d+)\)', text)
    if m:
        return int(m.group(2)), 0x80, _type_code(m.group(1))
    m = re.fullmatch(r'(\w+)\([^()]*\)\[c(\d+)\]', text)
    if m:
        return int(m.group(2)), 0x00, _type_code(m.group(1))
    m = re.fullmatch(r'([fib]\d)\(([^()#]*)\)', text)
    if m and pool is not None:
        numbers = [float(v) for v in m.group(2).split(',')]
        raw = pack_constant(m.group(1), numbers)
        if raw not in pool:
            pool.append(raw)
        return pool.index(raw), 0x00, _type_code(m.group(1))
    raise ValueError('cannot read operand "%s"' % text)


def _operands(text, pool=None):
    found = _OPERAND.findall(text)
    if re.sub(r'[\s,]', '', ''.join(found)) != re.sub(r'[\s,]', '', text):
        raise ValueError('cannot read operands "%s"' % text)
    return [parse_operand(o, pool) for o in found]


def _by_name(table, label, kind):
    """Index of an external ("name<i>" when it has no name) or a call's function ("name@i", "fn<i>")."""
    m = re.fullmatch(r'(.*)@(\d+)', label)
    if m:
        return int(m.group(2))
    m = re.fullmatch(r'(?:name|fn)(\d+)', label)
    if m and (not table or label not in table):
        return int(m.group(1))
    if table and label in table:
        if table.count(label) > 1:
            raise ValueError('%s "%s" is in the table more than once; write %s@<index>' % (kind, label, label))
        return table.index(label)
    raise ValueError('no %s "%s" in this script (it has: %s)' % (kind, label, ', '.join(str(n) for n in table or [])))


_NAMED = {name: (0x70, sub) for sub, name in SUB70.items()}
_NAMED.update({name: (0x79, sub) for sub, name in SUB79.items()})
_FUNCTION_CODES = {name: sub for sub, name in FUNCTIONS.items()}
_ARITH = {'+': 0x71, '-': 0x72, '*': 0x73, '/': 0x74}


def assemble(text, names=None, functions=None, constants=None):
    """Listing text (as listing() or `PopcornBaked.py dis` prints it) -> instructions for encode().

    One instruction per line; a leading hex address, "#..." header lines, blank lines and
    "; comments" are ignored. Externals and functions are written by name and resolved in the
    script's own tables (`names`, `functions`); constants by their [cN] index (the value shown
    beside it is not read). A value written without an index, f1(2.5) or f3(1, 0, 0), becomes a
    constant of the script when `constants` (its list of 32-byte constants) is given: an equal
    one is reused, a new one is appended to the list."""
    out = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split(';', 1)[0].strip()
        line = re.sub(r'^[0-9A-Fa-f]{4,}\s+', '', line)
        if not line or line.startswith('#'):
            continue
        try:
            out.append(_assemble_line(line, names, functions, constants))
        except (ValueError, KeyError, IndexError) as e:
            raise ValueError('line %d: %s\n    %s' % (number, e, raw.strip())) from None
    return out


def _assemble_line(line, names, functions, pool=None):
    def operand(t):
        return parse_operand(t, pool)

    def operands(t):
        return _operands(t, pool) if t.strip() else []

    if line == 'begin':
        return {'op': 0x7C, 'sub': 0, 'regs': []}
    if line == 'end':
        return {'op': 0x7D, 'regs': []}
    m = re.fullmatch(r'keep (.+)', line)
    if m:
        return {'op': 0x6B, 'name': _by_name(names, m.group(1), 'external'), 'regs': []}
    m = re.fullmatch(r'store (.+?) = (.+)', line)
    if m:
        return {'op': 0x6A, 'name': _by_name(names, m.group(1), 'external'), 'regs': [operand(m.group(2))]}
    m = re.fullmatch(r'(?:(\S+) = )?call (\S+?)\((.*)\)(?: on (.+?))?\s+\(flag ([0-9A-Fa-f]{2}), tags ?([0-9A-Fa-f ]*)\)', line)
    if m:
        args = operands(m.group(3))
        tags = [int(t, 16) for t in m.group(6).split()]
        if len(tags) != len(args):
            raise ValueError('a call needs one tag per argument')
        return {'op': 0x7B, 'sub': int(m.group(5), 16), 'fn': _by_name(functions, m.group(2), 'function'),
                'obj': -1 if m.group(4) is None else _by_name(names, m.group(4), 'external'),
                'regs': [operand(m.group(1)) if m.group(1) else _NONE] + args, 'tags': tags}
    m = re.fullmatch(r'(\S+) = (.+)', line)
    if not m:
        raise ValueError('cannot read this instruction')
    dst, rest = operand(m.group(1)), m.group(2).strip()
    m = re.fullmatch(r'load (.+)', rest)
    if m:
        return {'op': 0x69, 'name': _by_name(names, m.group(1), 'external'), 'regs': [dst]}
    m = re.fullmatch(r'(convert|spread) (\S+)', rest)
    if m:
        return {'op': 0x6C if m.group(1) == 'convert' else 0x6F, 'regs': [dst, operand(m.group(2))]}
    m = re.fullmatch(r'vector\((.*)\)', rest)
    if m:
        return {'op': 0x6D, 'regs': [dst] + operands(m.group(1))}
    m = re.fullmatch(r'(.+)\.[\w?]+\s+\(swizzle ([0-9A-Fa-f]{2})/([0-9A-Fa-f]{4})\)', rest)
    if m:
        return {'op': 0x6E, 'sub': int(m.group(2), 16), 'mask': int(m.group(3), 16), 'regs': [dst, operand(m.group(1))]}
    m = re.fullmatch(r'(.+) / (.+?)\s+\(integer: magic (.+), shift (.+)\)', rest)
    if m:
        return {'op': 0x76, 'regs': [dst] + [operand(g) for g in m.groups()]}
    m = re.fullmatch(r'(.+) \* (.+) \+ (.+)', rest)
    if m:
        return {'op': 0x75, 'regs': [dst] + [operand(g) for g in m.groups()]}
    m = re.fullmatch(r'(.+) \? (.+) : (.+)', rest)
    if m:
        mask, b, a = (operand(g) for g in m.groups())
        return {'op': 0x7A, 'regs': [dst, a, b, mask]}
    m = re.fullmatch(r'(\w+)\((.*)\)', rest)
    if m and not re.fullmatch(r'\w+\(#\d+\)', rest) and not re.fullmatch(r'\w+\([^()]*\)\[c\d+\]', rest):
        name, args = m.group(1), operands(m.group(2))
        if name in _NAMED:
            op, sub = _NAMED[name]
            if op == 0x70:
                args = (args + [_NONE, _NONE])[:2]
            return {'op': op, 'sub': sub, 'regs': [dst] + args}
        if name in _FUNCTION_CODES:
            if len(args) not in (1, 2):
                raise ValueError('%s takes one or two arguments' % name)
            return {'op': 0x77 if len(args) == 1 else 0x78, 'sub': _FUNCTION_CODES[name], 'regs': [dst] + args}
        m2 = re.fullmatch(r'(fn[123]|logic)_?([0-9A-Fa-f]{2})', name)
        if m2:
            op = {'fn1': 0x77, 'fn2': 0x78, 'fn3': 0x79, 'logic': 0x70}[m2.group(1)]
            return {'op': op, 'sub': int(m2.group(2), 16), 'regs': [dst] + args}
        raise ValueError('unknown function "%s"' % name)
    for symbol, op in _ARITH.items():
        parts = rest.split(' %s ' % symbol)
        if len(parts) == 2:
            return {'op': op, 'regs': [dst, operand(parts[0]), operand(parts[1])]}
    raise ValueError('cannot read "%s"' % rest)
