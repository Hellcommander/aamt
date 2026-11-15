"""Bytecode of the compiled scripts in Diablo II: Resurrected .particles files.

Each CCompilerBlobCache object of a .particles file (see PopcornBaked.py) holds one
script for PopcornFX's CPU virtual machine. This module turns its bytecode into a
list of instructions and back, and prints it as readable text.

Worked out from the game's own files, 2026-11-13: all 11241 distinct scripts found
in the 1991 files decode with exactly the instruction count their header gives, and
encode back to the same bytes.

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
  70 sub, dst, a, b          compare and logic, see SUB70
  77 sub, dst, a             one-argument function, see SUB77 (few are identified)
  78 sub, dst, a, b          two-argument function, see SUB78
  79 sub, dst, a, b, c       three-argument function (not identified)
  7A dst, a, b, mask         choose: mask ? b : a
  7B flag, i16 obj, u16 fn, u8 argc, dst, argc x (u8 tag, reg)
                             call function `fn` of the script's f4 table; obj is -1 or
                             a name index (a sampler or event the call acts on)

"presumed" marks names read from how the instruction is used, not proven.
"""
import struct

TYPE_NAMES = {0x20: 'f1', 0x21: 'f2', 0x22: 'f3', 0x23: 'f4', 0x1A: 'i1', 0x1B: 'i2', 0x1C: 'i3', 0x1D: 'i4',
              0x02: 'b1', 0x04: 'b3', 0x00: 'ctx', 0x25: 't25', 0xFF: ''}
TYPE_WIDTH = {'f1': 1, 'f2': 2, 'f3': 3, 'f4': 4, 'i1': 1, 'i2': 2, 'i3': 3, 'i4': 4, 'b1': 1, 'b3': 3}
KIND_NAMES = {0x00: 'c', 0x20: 'p', 0x40: 'q', 0x60: 'r', 0x80: '#'}

OPS = {0x7C: 'begin', 0x7D: 'end', 0x69: 'load', 0x6A: 'store', 0x6B: 'keep', 0x6C: 'convert', 0x6F: 'spread',
       0x6D: 'vector', 0x6E: 'swizzle', 0x71: 'add', 0x72: 'sub', 0x73: 'mul', 0x74: 'div', 0x75: 'muladd',
       0x70: 'logic', 0x77: 'fn1', 0x78: 'fn2', 0x79: 'fn3', 0x7A: 'choose', 0x7B: 'call'}
# 0x10 / 0x11 also take bools, so they are the equality tests; the order of the four
# inequalities is presumed apart from 0x0C (used as "length squared < 1e-16").
SUB70 = {0x04: 'op04', 0x05: 'neg', 0x08: 'and', 0x09: 'or', 0x0A: 'xor', 0x0B: 'not', 0x0C: 'lt', 0x0D: 'le?',
         0x0E: 'gt?', 0x0F: 'ge?', 0x10: 'eq', 0x11: 'ne'}
SUB77 = {0x20: 'rsqrt'}
SUB78 = {0x1B: 'min', 0x1C: 'max', 0x1D: 'dot', 0x1E: 'cross'}

# opcode -> (has sub byte, number of register operands, trailing u16 fields)
_FIXED = {0x6C: (False, 2), 0x6F: (False, 2), 0x71: (False, 3), 0x72: (False, 3), 0x73: (False, 3), 0x74: (False, 3),
          0x75: (False, 4), 0x7A: (False, 4), 0x77: (True, 2), 0x70: (True, 3), 0x78: (True, 3), 0x79: (True, 4)}


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


def listing(instructions, constants=None, names=None, functions=None):
    """Readable text, one instruction per line."""
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
        elif op == 0x7A:
            text = '%s = %s ? %s : %s' % (regs[0], regs[3], regs[2], regs[1])
        elif op == 0x70:
            text = '%s = %s(%s)' % (regs[0], SUB70.get(sub, 'logic%02X' % sub), ', '.join(r for r in regs[1:] if r != '-'))
        elif op == 0x77:
            text = '%s = %s(%s)' % (regs[0], SUB77.get(sub, 'fn1_%02X' % sub), regs[1])
        elif op == 0x78:
            text = '%s = %s(%s)' % (regs[0], SUB78.get(sub, 'fn2_%02X' % sub), ', '.join(regs[1:]))
        elif op == 0x79:
            text = '%s = fn3_%02X(%s)' % (regs[0], sub, ', '.join(regs[1:]))
        elif op == 0x7B:
            fn = functions[ins['fn']] if functions and ins['fn'] < len(functions) else 'fn%d' % ins['fn']
            target = '' if ins['obj'] < 0 else ' on %s' % ext(ins['obj'])
            args = ', '.join('%s' % a for a in regs[1:])
            head = '' if regs[0] == '-' else '%s = ' % regs[0]
            text = '%scall %s(%s)%s   (flag %02X, tags %s)' % (head, fn, args, target, sub, ' '.join('%02X' % t for t in ins['tags']))
        else:
            text = '?? %02X' % op
        lines.append('%04X  %s' % (ins['at'], text))
    return '\n'.join(lines)
