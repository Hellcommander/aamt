"""Turns compiled Diablo II: Resurrected formulas (skillscode.bin, misscode.bin, skilldesccode.bin...)
back into the text of a calc column ("par1+(lvl-1)*par2", "skill('Fire Bolt'.blvl)*par8").

The bytecode is a small stack machine; what each opcode does was checked against the game's own
.txt/.bin pairs (BinTables.py finds which record field holds which formula's offset). Opcodes:
  0           end
  1 f n       call function f with n arguments (D2R adds the argument count; 1.14d has only f).
              Functions: 0 min, 1 max, 2 rand, 3 skill, 4 miss, 5 stat, 6 sklvl, 7 sksrc (D2R:
              sksrc('Skill'.code), the skill of the pet's owner), 8 cond (D2R: cond('Name'[, value]))
  4 k / 5 k16 / 6 k32   a keyword: row k of the calc code table (skillcalc.txt: ln12, par1, lvl...)
  7 b / 8 s16 / 9 i32   a number
  10 <  11 >  12 <=  13 >=  14 ==  15 !=  16 +  17 -  18 *  19 /  20 %  22 negate  23 a?b:c
  (20 is what '%' compiles to in the stock monpet.txt; nothing in the stock tables writes '^')
  (D2R moved negate and ?: up by one against 1.14d; checked on the stock tables, see BinTables.py)
Inside skill('Name'.code), miss('name'.code), stat('name'.accr|base|mod) and sklvl(...) the
arguments are numbers: the row of the named skill / missile / stat and the row of the code.
The text is written with full parentheses, so it means the same whatever precedence the game's
parser uses. Reference: the formula evaluator of the 1.14d reconstruction Redivivus
(github.com/jaenster/redivivus, MIT), used only as a map; nothing is taken over unchecked.
"""
import struct

FUNCS = {0: 'min', 1: 'max', 2: 'rand', 3: 'skill', 4: 'miss', 5: 'stat', 6: 'sklvl', 7: 'sksrc', 8: 'cond'}
SKILL_LIKE = {'skill', 'miss', 'stat', 'sksrc'}
BINOPS = {10: '<', 11: '>', 12: '<=', 13: '>=', 14: '==', 15: '!=', 16: '+', 17: '-', 18: '*', 19: '/', 20: '%'}
# cond('Name', value): the names and values the stock tables use (treasureclassex, misc, uniqueitems)
COND_NAMES = {2: 'Desecrated', 3: 'MonsterTestElite', 6: 'Difficulty', 7: 'IsDesecratedZonesEnabled'}
COND_VALUES = {'Difficulty': {0: 'normal', 1: 'nightmare', 2: 'hell'}, 'MonsterTestElite': {512: 'herald'}}
STAT_CODES = {0: 'accr', 1: 'base', 2: 'mod'}


class CalcError(ValueError):
    pass


class Context:
    """Names for the numbers in a formula: the calc code table of this kind of formula and the
    rows of the tables named inside skill(), miss(), stat()."""

    def __init__(self, codes, skills=None, missiles=None, stats=None, misscodes=None, skillcodes=None):
        self.codes = codes          # keyword row -> code (skillcalc / misscalc): bare words of the formula
        self.skills = skills or []  # skill row -> name
        self.missiles = missiles or []
        self.stats = stats or []
        self.misscodes = misscodes or codes    # the .code in miss('x'.code)
        self.skillcodes = skillcodes or codes  # the .code in skill('X'.code): skillcalc even in a missile formula


def _num(v):
    return str(v) if v >= 0 else '(%d)' % v


def decode(code, offset, ctx, limit=4096):
    """-> (text, end offset). Raises CalcError on bytes that are not a formula."""
    stack = []  # (text, literal value or None)
    p = offset
    end = min(len(code), offset + limit)
    while True:
        if p >= end:
            raise CalcError('formula runs off the end')
        op = code[p]
        if op == 0:
            p += 1
            break
        if op == 2:
            # a '(' the compiler left behind (unbalanced text in the table): the game stops here and
            # uses the top of the stack, so the formula means just that
            p += 1
            while p < end and code[p] != 0:
                p += 1
            p += 1
            break
        if op in (7, 8, 9):
            fmt, size = {7: ('<b', 1), 8: ('<h', 2), 9: ('<i', 4)}[op]
            v = struct.unpack_from(fmt, code, p + 1)[0]
            stack.append((_num(v), v))
            p += 1 + size
        elif op in (4, 5, 6):
            fmt, size = {4: ('<B', 1), 5: ('<H', 2), 6: ('<I', 4)}[op]
            k = struct.unpack_from(fmt, code, p + 1)[0]
            if k >= len(ctx.codes):
                raise CalcError('keyword %d out of range' % k)
            stack.append((ctx.codes[k], None))
            p += 1 + size
        elif op == 1:
            f, n = code[p + 1], code[p + 2]
            if n > 3 or len(stack) < n:
                raise CalcError('bad call %d/%d' % (f, n))
            args = stack[len(stack) - n:]
            del stack[len(stack) - n:]
            stack.append((call_text(FUNCS.get(f, 'fn%d' % f), args, ctx), None))
            p += 3
        elif op in BINOPS:
            if len(stack) < 2:
                raise CalcError('operator without operands')
            b = stack.pop()
            a = stack.pop()
            stack.append(('(%s%s%s)' % (a[0], BINOPS[op], b[0]), None))
            p += 1
        elif op == 22:  # D2R: negate is 22 (1.14d: 21), ?: is 23 (1.14d: 22); 21 is not seen in the stock tables
            if not stack:
                raise CalcError('negate without operand')
            a = stack.pop()
            stack.append(('(-%s)' % a[0], None))
            p += 1
        elif op == 23:
            if len(stack) < 3:
                raise CalcError('?: without operands')
            c = stack.pop()
            b = stack.pop()
            a = stack.pop()
            stack.append(('(%s?%s:%s)' % (a[0], b[0], c[0]), None))
            p += 1
        else:
            raise CalcError('opcode %d at %d' % (op, p))
    if not stack:
        raise CalcError('empty formula')
    text = stack[-1][0]  # with values left over (unbalanced text) the game takes the top one
    if text.startswith('(') and text.endswith(')') and balanced(text[1:-1]):
        text = text[1:-1]
    return text, p


def balanced(s):
    d = 0
    for ch in s:
        d += ch == '('
        d -= ch == ')'
        if d < 0:
            return False
    return d == 0


def call_text(fn, args, ctx):
    lit = [a[1] for a in args]
    if fn == 'cond' and args and lit[0] in COND_NAMES:
        name = COND_NAMES[lit[0]]
        if len(args) == 1:
            return "cond('%s')" % name
        if len(args) == 2:
            value = COND_VALUES.get(name, {}).get(lit[1], args[1][0])
            return "cond('%s', %s)" % (name, value)
    if fn in SKILL_LIKE and len(args) == 2 and None not in lit:
        names = {'miss': ctx.missiles, 'stat': ctx.stats}.get(fn, ctx.skills)
        target = names[lit[0]] if 0 <= lit[0] < len(names) else None
        if fn == 'stat':
            prop = STAT_CODES.get(lit[1])
        elif fn == 'miss':
            prop = ctx.misscodes[lit[1]] if 0 <= lit[1] < len(ctx.misscodes) else None
        else:
            prop = ctx.skillcodes[lit[1]] if 0 <= lit[1] < len(ctx.skillcodes) else None
        if target is not None and prop is not None:
            return "%s('%s'.%s)" % (fn, target, prop)
    if fn == 'sklvl' and len(args) == 3 and lit[0] is not None and lit[2] is not None:
        target = ctx.skills[lit[0]] if 0 <= lit[0] < len(ctx.skills) else None
        prop = ctx.skillcodes[lit[2]] if 0 <= lit[2] < len(ctx.skillcodes) else None
        if target is not None and prop is not None:
            return "sklvl('%s'.%s.%s)" % (target, args[1][0], prop)
    return '%s(%s)' % (fn, ','.join(a[0] for a in args))


def tokens(text):
    """Words and numbers of a formula, for comparing a decoded formula with the .txt one."""
    out = []
    cur = ''
    for ch in str(text).lower().replace('"', ''):
        if ch.isalnum() or ch == '_' or ch == ' ' and cur and not cur.isdigit():
            cur += ch
        else:
            if cur.strip():
                out.append(cur.strip())
            cur = ''
    if cur.strip():
        out.append(cur.strip())
    return out
