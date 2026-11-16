"""Decompiles Diablo II: Resurrected compiled tables (global/excel/*.bin) back to .txt.

Some mods ship their tables only compiled (.bin). D2RMM runs the game on .txt tables, so such a
mod's changes do nothing there until they are turned back into text. The layouts are not written
down anywhere and change with game patches, so this works them out from the game itself: the
archive holds every table both as .txt and as .bin, and every column of the .txt is matched against
every byte position of the .bin records: numbers of each width and sign, flags packed into bits,
text, 4-letter codes, rows of other tables, and formulas (offsets into skillscode.bin & co., turned
back into text by BinCalc.py).

    python BinTables.py infer <table> [<table> ...]          # layouts from the game's own pairs
    python BinTables.py roundtrip <table> [<table> ...]      # decompile the game's .bin, compare with its .txt
    python BinTables.py decompile <data dir> --out <dir> <table> [<table> ...]
    python BinTables.py report <table>                        # the layout, column by column

<data dir> is a mod's data folder (with global\\excel\\*.bin). Rows named inside a decompiled table
(a skill's missile, a formula's skill('X'...)) are named from the mod's own tables where the mod
has them, from the game's otherwise. Layouts are kept in %LOCALAPPDATA%\\D2RModAssets\\binlayouts.
"""
import argparse
import json
import os
import re
import struct
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import BinCalc  # noqa: E402

VANILLA = Path(os.environ.get('LOCALAPPDATA', '.')) / 'D2RModAssets' / 'vanilla'
LAYOUTS = Path(os.environ.get('LOCALAPPDATA', '.')) / 'D2RModAssets' / 'binlayouts'
INT_TYPES = [('u8', 1), ('i8', 1), ('u16', 2), ('i16', 2), ('u32', 4), ('i32', 4)]
WIDTH = dict(INT_TYPES)
# formulas: table -> (code buffer, calc keyword table)
CALCS = {'skills': ('skillscode', 'skillcalc'), 'skilldesc': ('skilldesccode', 'skillcalc'),
         'missiles': ('misscode', 'misscalc'), 'monstats': ('moncode', 'moncalc'), 'monpet': ('moncode', 'moncalc'),
         'misc': ('itemscode', 'skillcalc'), 'uniqueitems': ('itemscode', 'skillcalc'),
         'setitems': ('itemscode', 'skillcalc'), 'treasureclassex': ('tccode', 'skillcalc')}
# bump when the inference changes: cached layouts made by an older one are worked out again
LAYOUT_VERSION = 13
# a .bin the compiler makes from another table's .txt (levels.txt -> levels.bin and leveldefs.bin,
# the second holding the map columns: SizeX, Vis0, Warp0, ...)
TXT_OF = {'leveldefs': 'levels'}


# ----------------------------------------------------------------------------- reading

def read_txt(path):
    text = Path(path).read_bytes().decode('latin1')
    lines = text.replace('\r\n', '\n').split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    headers = lines[0].split('\t')
    rows = []
    for line in lines[1:]:
        cells = line.split('\t')
        cells += [''] * (len(headers) - len(cells))
        rows.append(cells[:len(headers)])
    return headers, rows


def read_bin(path):
    raw = Path(path).read_bytes()
    n = struct.unpack_from('<I', raw, 0)[0]
    size = (len(raw) - 4) // n if n else 0
    if n and 4 + n * size != len(raw):
        raise ValueError('%s: %d bytes is not 4 + %d records' % (path, len(raw), n))
    data = np.frombuffer(raw, dtype=np.uint8, offset=4).reshape(n, size) if n else np.zeros((0, 0), np.uint8)
    return n, size, data


def views(data):
    """Every int type read at every offset of every record: {type: (n, offsets) array}."""
    n, size = data.shape
    out = {}
    d = data.astype(np.int64)
    for name, width in INT_TYPES:
        if width > size:
            continue
        v = np.zeros((n, size - width + 1), np.int64)
        for k in range(width):
            v |= d[:, k:size - width + 1 + k] << (8 * k)
        if name.startswith('i'):
            top = 1 << (8 * width - 1)
            v = np.where(v >= top, v - (top << 1), v)
        out[name] = v
    return out


def as_int(s):
    s = s.strip()
    if s == '':
        return 0
    try:
        return int(s)
    except ValueError:
        try:
            f = float(s)
            return int(f) if f == int(f) else None
        except (ValueError, OverflowError):  # 'inf' / 'nan' in a cell are not numbers the game stores
            return None


def compiled_rows(rows):
    """The .txt rows a compiled table has: the 'Expansion' separator rows are left out."""
    return [r for r in rows if not (r and r[0].strip().lower() == 'expansion')]


def strip_parens(t):
    return re.sub(r'[()\s"]', '', str(t)).lower()


def field_width(f):
    t = f['type']
    if t in WIDTH:
        return WIDTH[t]
    if t in ('ref', 'enum', 'strkey', 'param', 'kindref'):
        return WIDTH[f['width']]
    if t in ('calc', 'code4'):
        return 4
    return 1


def span(f):
    t = f['type']
    if t in WIDTH:
        return range(f['offset'], f['offset'] + WIDTH[t])
    if t in ('code4', 'calc'):
        return range(f['offset'], f['offset'] + 4)
    if t in ('ref', 'enum', 'strkey', 'param'):
        return range(f['offset'], f['offset'] + WIDTH[f['width']])
    if t == 'reflist':
        return range(f['offset'], f['offset'] + f['count'])
    if t == 'kindref':  # the row and the byte telling its table
        return sorted(set(range(f['offset'], f['offset'] + WIDTH[f['width']])) | {f['kind']})
    if t in ('bit', 'bits', 'str'):
        return range(f['offset'], f['offset'] + 1)
    return range(0)


# ----------------------------------------------------------------------------- tables of a source

class Source:
    """The tables of one data folder (the game's cache, or a mod's data), .txt or .bin."""

    def __init__(self, root):
        self.root = Path(root)
        self.cache = {}

    def path(self, name, ext):
        p = self.root / 'global' / 'excel' / (name + ext)
        if p.exists():
            return p
        for q in (self.root / 'global' / 'excel').glob('*' + ext):  # mods spell names in other cases
            if q.stem.lower() == name.lower():
                return q
        return None

    def txt(self, name):
        key = ('txt', name)
        if key not in self.cache:
            p = self.path(name, '.txt')
            self.cache[key] = read_txt(p) if p else None
        return self.cache[key]

    def code(self, name):
        p = self.path(name, '.bin')
        return p.read_bytes() if p else None


class Strings:
    """String keys and ids of a data folder's local/lng/strings/*.json (a key may have several ids)."""

    def __init__(self, *roots):
        self.ids = {}   # key lower -> set of ids
        self.keys = {}  # id -> key
        for root in roots:
            if root is None:
                continue
            for f in sorted((Path(root) / 'local' / 'lng' / 'strings').glob('*.json')):
                try:
                    entries = json.loads(f.read_text(encoding='utf-8-sig'))
                except ValueError:
                    continue
                for e in entries if isinstance(entries, list) else []:
                    if isinstance(e, dict) and 'Key' in e and 'id' in e:
                        self.ids.setdefault(str(e['Key']).lower(), set()).add(e['id'])
                        self.keys.setdefault(e['id'], e['Key'])


# tables whose 4-byte refs may name a row of a second table instead: (that table, number added to its row)
GROUP_TABLES = {'properties': ('propertygroups', 0x10000)}


def ci_first(src, table):
    tab = src.txt(table)
    return tab[0][0] if tab else None


class Refs:
    """Key columns of the game's tables, for columns that hold a row of another table."""

    def __init__(self, src):
        self.src = src
        self._cands = None

    def candidates(self):
        if self._cands is None:
            out = []
            for p in sorted((self.src.root / 'global' / 'excel').glob('*.txt')):
                tab = self.src.txt(p.stem)
                if not tab:
                    continue
                h, rows = tab
                rows = compiled_rows(rows)
                for ci, col in enumerate(h[:3]):
                    index = {}
                    for i, r in enumerate(rows):
                        k = r[ci].lower().strip()
                        if k and k not in index:
                            index[k] = i
                    if len(index) > 1:
                        out.append((p.stem, col, index))
            # a property slot can hold a property group instead (Virulent-Affix1: 0x10000 + its row)
            for k, (t, col, index) in enumerate(out):
                if t in GROUP_TABLES and ci_first(self.src, t) == col:
                    gt, base = GROUP_TABLES[t]
                    grp = self.src.txt(gt)
                    if grp:
                        more = dict(index)
                        for i, r in enumerate(compiled_rows(grp[1])):
                            g = r[0].lower().strip()
                            if g and g not in more:
                                more[g] = base + i
                        out[k] = (t, col, more)
            self._cands = out
        return self._cands


def calc_context(src, table, fallback=None):
    """Names for formula numbers: the calc keyword table and the skills / missiles / stats rows."""
    code_name, calc_name = CALCS[table]

    def names(t):
        for s in (src, fallback):
            if s is not None:
                got = s.names(t) if hasattr(s, 'names') else None
                if got:
                    return got
        return []
    return BinCalc.Context(names(calc_name), names('skills'), names('missiles'), names('itemstatcost'), names('misscalc'),
                           names('skillcalc'))


class Names:
    """Row names of tables: decompiled from a mod's .bin where it has one, else the game's .txt."""

    def __init__(self, primary, game=None, decoded=None):
        self.primary = primary
        self.game = game
        self.decoded = decoded if decoded is not None else {}

    def names(self, table, key=None):
        """The values of a table's key column (its first column by default), in compiled row order."""
        got = self.decoded.get(table)
        if got is not None:
            if key is None:
                return next(iter(got.values()))
            if key in got:
                return got[key]
        for s in (self.primary, self.game):
            if s is None:
                continue
            tab = s.txt(table)
            if tab:
                h, rows = tab
                ci = h.index(key) if key in h else 0
                return [r[ci] for r in compiled_rows(rows)]
        return []


# ----------------------------------------------------------------------------- inference

def infer(table, game_src, log=print):
    headers, rows = game_src.txt(TXT_OF.get(table, table))
    n, size, data = read_bin(game_src.path(table, '.bin'))
    if n != len(rows) and n == len(compiled_rows(rows)):
        rows = compiled_rows(rows)
    if n != len(rows):
        raise ValueError('%s: %d rows in the .txt, %d records in the .bin' % (table, len(rows), n))
    V = views(data)
    refs = Refs(game_src)
    strings = Strings(game_src.root)
    code = ctx = None
    if table in CALCS:
        code = game_src.code(CALCS[table][0])
        ctx = calc_context(Names(game_src), table)
    fields, ambiguous = {}, {}
    for ci, col in enumerate(headers):
        vals = [r[ci].strip() for r in rows]
        if all(v == '' for v in vals):
            continue
        ints = [as_int(v) for v in vals]
        found = []
        if code is not None and re.search(r'calc|delay|petmax|sumumod|^range$|^radius$', col, re.I):
            found = find_calc(vals, V, code, ctx)  # formula columns hold formulas even when they read like numbers
        if found:
            pass
        elif all(x is not None for x in ints) and len(set(ints)) > 1:
            found = find_number(ints, data, V)
        elif not all(x is not None for x in ints):
            found = (find_reflist(vals, data, refs) or find_text(vals, rows, data, size) or find_code4(vals, data, size)
                     or find_strkey(vals, V, strings, strict=ci == 0) or find_ref(col, vals, V, refs)
                     or find_kindref(vals, data, V, game_src))
            nums = [as_int(v) if v else 0 for v in vals]
            if not found and all(x is not None for x in nums) and len(set(nums)) > 1:
                found = find_number(nums, data, V)  # a number column with some cells left empty (sounds Group Weight)
        constant = all(x is not None for x in ints) and len(set(ints)) == 1
        if code is not None and not found and not constant:  # one number everywhere: a constant, not a formula
            found = find_calc(vals, V, code, ctx)
        if not found and not all(x is not None for x in ints):
            found = find_enum(vals, V)
        if not found and all(x is not None for x in ints) and len(set(ints)) == 1:
            found = [{'type': 'const', 'value': ints[0]}]
        # the compiler aligns fields: a 2-byte number at an even offset, a 4-byte one at a multiple of 4
        aligned = [c for c in found if 'offset' not in c or c['offset'] % field_width(c) == 0]
        found = aligned or found
        if len(found) == 1:
            fields[col] = found[0]
        elif found:
            ambiguous[col] = found
        else:
            fields[col] = {'type': 'missing', 'sample': next(v for v in vals if v)[:60]}
    # ambiguous columns, by elimination: a candidate on bytes (or, for flags, the bit) another
    # column already owns is out; repeat while that settles something
    taken, bits = set(), set()

    def bit_set(f):
        return {(f['offset'], f['bit'] + k) for k in range(f.get('count', 1))}

    def is_bits(f):
        return f['type'] in ('bit', 'bits')

    def own(f):
        if is_bits(f):
            bits.update(bit_set(f))
        else:
            taken.update(span(f))
    for f in fields.values():
        own(f)
    progress = True
    while ambiguous and progress:
        progress = False
        for col in list(ambiguous):
            bit_bytes = {b[0] for b in bits}
            free = [c for c in ambiguous[col]
                    if ((not (bit_set(c) & bits) and c['offset'] not in taken) if is_bits(c)
                        else (not (set(span(c)) & taken) and not any(o in bit_bytes for o in span(c))))]
            widest = sorted(free, key=lambda c: (is_bits(c), -len(span(c)), not c['type'].startswith('i'), c['type']))
            # one number field, or a number and bits inside it that read the same: take the number
            if len(free) == 1 or (free and not is_bits(widest[0]) and all(set(span(c)) <= set(span(widest[0])) for c in free)):
                fields[col] = dict(widest[0], guessed=len(free) > 1)
                own(widest[0])
                del ambiguous[col]
                progress = True
            else:
                ambiguous[col] = free
    # what the game's own data cannot tell apart (two flags set on the same few rows): the first
    # free place, marked as a guess
    for col in sorted(ambiguous, key=lambda c: len(ambiguous[c])):
        free = [c for c in ambiguous[col] if (is_bits(c) and not (bit_set(c) & bits) and c['offset'] not in taken)
                or (not is_bits(c) and not (set(span(c)) & taken))]
        pick = sorted(free or ambiguous[col], key=lambda c: (is_bits(c), -len(span(c)), not c['type'].startswith('i')))
        if pick:
            fields[col] = dict(pick[0], guessed=True, alternatives=len(ambiguous[col]))
            own(pick[0])
    # a key column read as its own row number plus something is a counter of another column
    # (difficultylevels: Name as ManaStealDivisor 1, 2, 3): the key is not stored
    key = fields.get(headers[0]) or {}
    if key.get('type') == 'ref' and key.get('table') == TXT_OF.get(table, table) and key.get('plus'):
        fields[headers[0]] = {'type': 'rowname'}  # the game's name of the row number
    refine(headers, rows, fields, size, V, game_src)
    kinds = {}
    for f in fields.values():
        kinds[f['type']] = kinds.get(f['type'], 0) + 1
    log('%s: %d columns, records of %d bytes: %s' % (table, len(headers), size, ', '.join('%s %d' % kv for kv in sorted(kinds.items()))))
    # zero means empty in the .txt when the game's file never writes a 0 in that column
    for col, f in fields.items():
        ci = headers.index(col)
        f['zero'] = '0' if any(r[ci].strip() == '0' for r in rows) else ''
    return {'table': table, 'size': size, 'rows': n, 'columns': headers, 'fields': fields,
            'stock': fingerprint(game_src, table)}


# ----------------------------------------------------------------------------- refining a layout
# What the column-by-column search cannot settle: columns the game's own file leaves empty or
# constant (a mod fills them), and members of a numbered series read with the wrong width.

def _sig(f):
    """What two fields of one series have in common (everything but the place)."""
    keep = ('type', 'width', 'table', 'key', 'empty', 'plus', 'count')
    return tuple(f.get(k) for k in keep) + ((json.dumps(f.get('map'), sort_keys=True),) if f['type'] == 'enum' else ())


class _Owner:
    """Bytes and bits of a record the layout's fields already use."""

    def __init__(self, fields, headers, rows):
        self.fields, self.headers, self.rows = fields, headers, rows
        self.rebuild()

    def rebuild(self):
        """Again from the fields: a field another guess replaced no longer holds its bytes."""
        self.taken, self.bits = set(), set()
        for col, f in self.fields.items():
            self.add(f, col, self.headers, self.rows)

    def add(self, f, col=None, headers=None, rows=None):
        if 'offset' not in f:
            return
        if f['type'] in ('bit', 'bits'):
            self.bits |= {(f['offset'], f['bit'] + k) for k in range(f.get('count', 1))}
        elif f['type'] == 'str' and headers is not None and col in headers:
            ci = headers.index(col)
            longest = max((len(r[ci]) for r in rows), default=0)
            self.taken |= set(range(f['offset'], f['offset'] + longest + 1))
        else:
            self.taken |= set(span(f))

    def free(self, f, ignore=None):
        taken, bits = self.taken, self.bits
        if ignore is not None and 'offset' in ignore:
            if ignore['type'] in ('bit', 'bits'):
                bits = bits - {(ignore['offset'], ignore['bit'] + k) for k in range(ignore.get('count', 1))}
            else:
                taken = taken - set(span(ignore))
        if f['type'] in ('bit', 'bits'):
            return not ({(f['offset'], f['bit'] + k) for k in range(f.get('count', 1))} & bits) and f['offset'] not in taken
        bit_bytes = {b[0] for b in bits}
        return not (set(span(f)) & taken) and not any(o in bit_bytes for o in span(f))


_PARAM_TABLES = {}


def param_tables(game_src):
    """Properties whose parameter is a row of another table (oskill: a skill, state: a state), from
    the game's own tables: prop code -> table. The .bin keeps the row number."""
    key = str(game_src.root)
    if key in _PARAM_TABLES:
        return _PARAM_TABLES[key]
    lookup = {}
    for t in ('skills', 'states', 'monstats'):
        tab = game_src.txt(t)
        if tab:
            lookup[t] = {r[0].strip().lower() for r in compiled_rows(tab[1]) if r[0].strip()}
    seen = {}
    for p in sorted((game_src.root / 'global' / 'excel').glob('*.txt')):
        tab = game_src.txt(p.stem)
        if not tab:
            continue
        h, rows = tab
        low = {c.lower(): i for i, c in enumerate(h)}
        for c, pi in low.items():
            for par, props in (('param', ('code', 'prop')), ('par', ('prop', 'code'))):
                if par not in c:
                    continue
                for prop in props:
                    ci = low.get(c.replace(par, prop, 1))
                    if ci is None:
                        continue
                    for r in rows:
                        v, code = r[pi].strip().strip('"').lower(), r[ci].strip().lower()
                        if v and code and as_int(v) is None:
                            for t, names in lookup.items():
                                if v in names:
                                    seen.setdefault(code, {}).setdefault(t, 0)
                                    seen[code][t] += 1
                    break
                break
    _PARAM_TABLES[key] = {code: max(ts, key=ts.get) for code, ts in seen.items()}
    return _PARAM_TABLES[key]


def _enums_to_refs(mem, fields, size, own, game_src):
    """An enum among refs of one series (mod2code read as one byte of the few codes the game's file
    uses, where mod1code is a 4-byte row of properties): when its numbers are rows of that table,
    it is the same ref (a mod uses codes the game's file never puts in that slot)."""
    model = next((fields[c] for c in mem.values() if c in fields and fields[c]['type'] == 'ref'), None)
    tab = game_src.txt(model['table']) if model else None
    if not tab:
        return
    th, trows = tab
    ki = th.index(model['key']) if model.get('key') in th else 0
    target = [r[ki].strip().lower() for r in compiled_rows(trows)]
    plus = model.get('plus', 0)
    for col in mem.values():
        cur = fields.get(col)
        if not cur or cur['type'] != 'enum':
            continue
        pairs = [(as_int(num), name.strip().lower()) for num, name in cur['map'].items() if name.strip()]
        if not pairs or not all(n is not None and 0 <= n - plus < len(target) and target[n - plus] == name
                                for n, name in pairs):
            continue
        new = {x: y for x, y in model.items() if x not in ('guessed', 'alternatives', 'zero', 'placed', 'offset')}
        new['offset'] = cur['offset']
        if new['offset'] % field_width(new) or new['offset'] + field_width(new) > size or not own.free(new, ignore=cur):
            continue
        fields[col] = dict(new, guessed=True, placed='series-ref')
        own.rebuild()


def refine(headers, rows, fields, size, V, game_src):
    own = _Owner(fields, headers, rows)

    # 1. a column the game's file holds one number in: the one place (not used yet) every record has it;
    # again while that settles something (GambleSet is only clear once GambleUnique, after it, is placed)
    again = True
    while again:
        again = _place_consts(headers, fields, V, own)

    # 2.-4. series, parameters, lists; before the gap rules (an empty Skill4 belongs to its series)
    _refine_series(headers, rows, fields, size, V, game_src, own)
    own.rebuild()

    # 1b. a column the game's file leaves empty, alone between two placed neighbours that leave a free
    # gap of one number's width, zero in every record
    placed = [(i, fields[c]) for i, c in enumerate(headers) if 'offset' in fields.get(c, {})
              and fields[c]['type'] in WIDTH]
    for (i, fa), (j, fb) in zip(placed, placed[1:]):
        if j - i != 2 or headers[i + 1] in fields:
            continue
        start = fa['offset'] + WIDTH[fa['type']]
        gap = fb['offset'] - start
        kind = {1: 'i8', 2: 'i16', 4: 'i32'}.get(gap)
        if not kind or start % gap or not np.all(V['u8'][:, start:start + gap] == 0):
            continue
        new = {'type': kind, 'offset': start}
        if own.free(new):
            fields[headers[i + 1]] = dict(new, guessed=True, placed='gap')
            own.add(new)
    # 1c. the same in record order: a placed number, then the column after it in the file empty, then
    # free zero bytes of the same width up to the next used byte (armor StrBonus at 278, DexBonus,
    # reqstr at 282 though reqstr is elsewhere in the file)
    for i, col in enumerate(headers[:-1]):
        fa, nxt = fields.get(col), headers[i + 1]
        if not fa or fa['type'] not in WIDTH or 'offset' not in fa or nxt in fields:
            continue
        ci = i + 1
        if any(r[ci].strip() not in ('', '0') for r in rows):
            continue
        w = WIDTH[fa['type']]
        start = fa['offset'] + w
        new = {'type': fa['type'], 'offset': start}
        after = [o for o in own.taken | {b[0] for b in own.bits} if o >= start]
        if start % w or not after or min(after) != start + w or not own.free(new) \
                or not np.all(V['u8'][:, start:start + w] == 0):
            continue
        fields[nxt] = dict(new, guessed=True, placed='gap')
        own.add(new)


def _place_consts(headers, fields, V, own):
    settled = False
    for col in headers:
        f = fields.get(col)
        if not f or f['type'] != 'const' or not f['value']:
            continue
        cands = []
        for name, width in INT_TYPES:
            if name in V:
                hit = np.nonzero(np.all(V[name] == f['value'], axis=0))[0]
                cands += [{'type': name, 'offset': int(o)} for o in hit if o % width == 0]
        cands = [c for c in cands if own.free(c)]
        if len({c['offset'] for c in cands}) > 1:
            # several places hold that number: the one between its neighbours in the file
            # (GambleRare at 108, GambleSet, GambleUnique at 116)
            ci = headers.index(col)
            before = [fields[c]['offset'] for c in headers[:ci] if 'offset' in fields.get(c, {})]
            after = [fields[c]['offset'] for c in headers[ci + 1:] if 'offset' in fields.get(c, {})]
            if before and after and before[-1] < after[0]:
                cands = [c for c in cands if before[-1] < c['offset'] < after[0]]
        if len({c['offset'] for c in cands}) == 1:
            pick = max(cands, key=lambda c: WIDTH[c['type']])
            fields[col] = dict(pick, guessed=True, placed='constant')
            own.add(pick)
            settled = True
    return settled


def _refine_series(headers, rows, fields, size, V, game_src, own):
    # 2. numbered series (prop1..prop7, Skill1..Skill6, Sk1mode..Sk8mode): members two or more of
    # them agree on (same kind, evenly spaced) place the others, also ones the file leaves empty
    families = {}
    for col in headers:
        for m in re.finditer(r'\d+', col):
            families.setdefault((col[:m.start()], col[m.end():]), {})[int(m.group())] = col
    for mem in families.values():
        if len(mem) >= 2:
            _enums_to_refs(mem, fields, size, own, game_src)
        if len(mem) < 3:
            continue
        located = {k: fields[c] for k, c in mem.items()
                   if c in fields and 'offset' in fields[c] and fields[c]['type'] not in ('bit', 'bits')}
        best = None
        ks = sorted(located)
        for i, a in enumerate(ks):
            for b in ks[i + 1:]:
                fa, fb = located[a], located[b]
                if _sig(fa) != _sig(fb) or (fb['offset'] - fa['offset']) % (b - a):
                    continue
                step = (fb['offset'] - fa['offset']) // (b - a)
                if abs(step) < field_width(fa):
                    continue
                base = fa['offset'] - a * step
                agree = [k for k in ks if _sig(located[k]) == _sig(fa) and located[k]['offset'] == base + k * step]
                if best is None or len(agree) > len(best[3]):
                    best = (step, base, fa, agree)
        if not best or len(best[3]) < 2:
            continue
        step, base, model, agree = best
        for k, col in sorted(mem.items()):
            if k in agree:
                continue
            new = {x: y for x, y in model.items() if x not in ('guessed', 'alternatives', 'zero', 'placed')}
            new['offset'] = base + k * step
            if new['offset'] < 0 or new['offset'] + field_width(new) > size:
                continue
            cur = fields.get(col)
            if cur and cur.get('offset') == new['offset'] and cur['type'] in WIDTH and new['type'] in WIDTH \
                    and WIDTH[cur['type']] == WIDTH[new['type']]:
                continue  # signed or not was read off this column's own numbers (129, not -127)
            # a guess of another kind (an enum of whole lists where the model is one code) stays
            replaceable = (cur is None or cur['type'] in ('missing', 'const') or cur.get('offset') == new['offset']
                           or (cur.get('guessed') and cur['type'] == new['type']))
            if replaceable and own.free(new, ignore=cur):
                fields[col] = dict(new, guessed=True, placed='series')
                own.rebuild()  # a wider guess it replaces (Mode3 read as 2 bytes) frees Mode4's byte

    # 3. a property's parameter: the 4 bytes before its min (prop/par/min/max, T1Code/T1Param/T1Min...)
    low = {c.lower(): c for c in headers}
    for col in headers:
        f = fields.get(col)
        if not f or 'min' not in col.lower() or f.get('type') != 'i32':
            continue
        lc = col.lower()
        for par, prop in (('par', 'prop'), ('param', 'code'), ('param', 'prop'), ('par', 'code')):
            pcol, propcol = low.get(lc.replace('min', par, 1)), low.get(lc.replace('min', prop, 1))
            if not pcol or not propcol:
                continue
            new = {'type': 'param', 'offset': f['offset'] - 4, 'width': 'i32', 'prop': propcol}
            cur = fields.get(pcol)
            if new['offset'] >= 0 and (cur is None or cur['type'] in ('missing', 'const', 'enum', 'i32') or cur.get('guessed')) \
                    and own.free(new, ignore=cur):
                fields[pcol] = dict(new, guessed=True, placed='param')
                own.rebuild()
            break
    # 4. lists of rows (monstats2 HDv..S8v): a list stops where the next field starts; a sibling the
    # game's file only fills with one code is a list of the same table too (a mod may fill it with several)
    lists = [f for f in fields.values() if f['type'] == 'reflist']
    if lists:
        tables = {f['table'] for f in lists}
        size_of = max(set(f['count'] for f in lists), key=[f['count'] for f in lists].count)
        data = V['u8']  # one byte at every offset: the records themselves
        for col in headers:
            f = fields.get(col)
            if f and f['type'] == 'ref' and f['width'] == 'u8' and f['empty'] == LIST_END and not f.get('plus') \
                    and f['table'] in tables:
                ci = headers.index(col)
                lens = [1 if r[ci].strip() else 0 for r in rows]
                room = list_room(data, f['offset'], lens)
                if room >= 2:
                    fields[col] = {'type': 'reflist', 'offset': f['offset'], 'count': room, 'table': f['table'],
                                   'key': f['key'], 'guessed': True, 'placed': 'list'}
        starts = sorted({f['offset'] for f in fields.values() if 'offset' in f})
        for f in fields.values():
            if f['type'] == 'reflist':
                nxt = [o for o in starts if o > f['offset']]
                f['count'] = min(f['count'], size_of, (nxt[0] - f['offset']) if nxt else f['count'])
    if any(f['type'] == 'param' for f in fields.values()):
        tabs = param_tables(game_src)
        for f in fields.values():
            if f['type'] == 'param':
                f['tables'] = tabs


def find_text(vals, rows, data, size):
    sample = next(v for v in vals if v)
    first = vals.index(sample)
    rec = data[first].tobytes()
    enc = sample.encode('latin1')
    out = []
    start = 0
    while True:
        o = rec.find(enc, start)
        if o < 0:
            break
        ok = True
        for i, v in enumerate(vals):
            b = data[i].tobytes()
            e = v.encode('latin1')
            if b[o:o + len(e)] != e or (o + len(e) < size and b[o + len(e)] != 0):
                ok = False
                break
        if ok:
            out.append({'type': 'str', 'offset': o})
        start = o + 1
    return out


def find_code4(vals, data, size):
    if not all(len(v) <= 4 for v in vals):
        return []
    want = [v.encode('latin1') for v in vals]
    out = []
    for o in range(size - 3):
        if all(data[i, o:o + 4].tobytes().rstrip(b' \0') == w for i, w in enumerate(want)):
            out.append({'type': 'code4', 'offset': o})
    return out


# rows of one of several tables, the table told by a kind byte (monpet monster: 1 monstats, 2 superuniques)
KIND_TABLES = [{'1': 'monstats', '2': 'superuniques'}]


def find_kindref(vals, data, V, src):
    if not any(vals) or 'u16' not in V:
        return []
    names = Names(src)
    out = []
    for tables in KIND_TABLES:
        idx = {}
        for k, t in tables.items():
            idx[k] = {}
            for j, n in enumerate(names.names(t)):
                idx[k].setdefault(n.strip().lower(), j)
        rows_of = [{k: idx[k].get(v.lower()) for k in tables} if v else None for v in vals]
        if any(r is not None and all(x is None for x in r.values()) for r in rows_of):
            continue
        M = V['u16']
        for ko in range(data.shape[1]):
            kc = data[:, ko].tolist()
            if len({kc[i] for i, r in enumerate(rows_of) if r}) < 2:
                continue  # one table only: a plain ref
            want = [None if r is None else r.get(str(kc[i])) for i, r in enumerate(rows_of)]
            if any(r is not None and w is None for r, w in zip(rows_of, want)):
                continue  # a kind that is no table here, or a name its table lacks
            for o in range(0, M.shape[1], 2):
                if o <= ko < o + 2:
                    continue
                col = M[:, o]
                if all(w is None or int(col[i]) == w for i, w in enumerate(want)):
                    out.append({'type': 'kindref', 'offset': o, 'width': 'u16', 'kind': ko, 'tables': tables})
    return out


def find_ref(col, vals, V, refs):
    distinct = {v.lower() for v in vals if v}
    best = []
    for t, kcol, index in refs.candidates():
        unknown = distinct - set(index)
        if len(unknown) > max(0, len(distinct) // 50):  # a value or two may name nothing (Blizzard's data has a few)
            continue
        mask = np.array([not v or v.lower() in index for v in vals])
        found = []
        for plus in (0, 1):
            for name, width in INT_TYPES:
                if name not in V:
                    continue
                full = (1 << (8 * width)) - 1 if name.startswith('u') else -1
                for empty in ((0,) if plus else (full, 0)):
                    y = np.array([(index[v.lower()] + plus) if v and v.lower() in index else empty for v in vals], np.int64)
                    hit = np.nonzero(np.all((V[name] == y[:, None]) | ~mask[:, None], axis=0))[0]
                    found += [{'type': 'ref', 'offset': int(o), 'width': name, 'table': t, 'key': kcol,
                               'empty': empty, 'plus': plus} for o in hit]
        if not found and len(distinct) >= 3:
            # a row number plus a constant (treasure classes: row + 161, after the game's own weapN/armoN)
            known = np.array([bool(v) and v.lower() in index for v in vals])
            idx = np.array([index[v.lower()] if k else 0 for v, k in zip(vals, known)], np.int64)
            blank = np.array([not v for v in vals])
            for name, width in INT_TYPES:
                if name not in V or WIDTH[name] < 2:
                    continue
                d = V[name][known] - idx[known][:, None]
                ok = np.nonzero(np.all(d == d[0], axis=0) & (d[0] > 1) & (d[0] < 4096))[0]
                for o in ok:
                    rest = V[name][blank, o]
                    if len(set(rest.tolist())) > 1:
                        continue
                    empty = int(rest[0]) if len(rest) else 0
                    found.append({'type': 'ref', 'offset': int(o), 'width': name, 'table': t, 'key': kcol,
                                  'empty': empty, 'plus': int(d[0, o])})
        if found:
            # several tables can hold the same names (skills and skilldesc): prefer the one the column is named after
            score = len(set(re.findall('[a-z]+', col.lower())) & set(re.findall('[a-z]+', t.lower())))
            best.append((score, -len(index), found))
    if not best:
        return []
    best.sort(key=lambda x: (-x[0], x[1]))
    return best[0][2]


LIST_END = 255


def _list_tokens(v):
    v = v.strip().strip('"')
    toks = [x.strip().lower() for x in v.split(',')] if v else []
    while toks and not toks[-1]:  # "a,b," (a trailing comma names nothing)
        toks.pop()
    return toks


def list_room(data, o, lens):
    """How many bytes a list at o has: the fewest of (its length + the 255s after it) over the rows."""
    room = data.shape[1] - o
    for i, k in enumerate(lens):
        j = o + k
        while j < data.shape[1] and data[i, j] == LIST_END and j - o < 32:
            j += 1
        room = min(room, j - o)
    return room


def find_reflist(vals, data, refs, tables=None):
    """A comma list of rows of another table (monstats2 HDv: "lit,med,hvy"): one byte per row number,
    255 after the last."""
    if tables is None and not any(',' in v for v in vals):
        return []
    lists = [_list_tokens(v) for v in vals]
    distinct = {x for toks in lists for x in toks}
    if not distinct or any(not x for toks in lists for x in toks):
        return []
    out = []
    for t, kcol, index in refs.candidates():
        if (tables is not None and t not in tables) or not distinct <= set(index) or max(index.values()) >= LIST_END:
            continue
        lens = [len(toks) for toks in lists]
        width = max(lens)
        want = np.full((len(lists), width + 1), -1, np.int64)
        for i, toks in enumerate(lists):
            want[i, :len(toks)] = [index[x] for x in toks]
            want[i, len(toks)] = LIST_END
        for o in range(data.shape[1] - width + 1):
            ok = True
            for i, toks in enumerate(lists):
                k = len(toks) + (1 if o + len(toks) < data.shape[1] else 0)
                if not np.array_equal(data[i, o:o + k].astype(np.int64), want[i, :k]):
                    ok = False
                    break
            if ok:
                room = list_room(data, o, lens)
                if room >= max(width, 2):
                    out.append({'type': 'reflist', 'offset': o, 'count': room, 'table': t, 'key': kcol})
        if out:
            return out
    return out


def find_number(ints, data, V):
    """Fields holding a column of numbers: a whole number, a flag bit or a few packed bits."""
    found = []
    y = np.array(ints, np.int64)
    for name, width in INT_TYPES:
        if name in V:
            hit = np.nonzero(np.all(V[name] == y[:, None], axis=0))[0]
            found += [{'type': name, 'offset': int(o)} for o in hit]
    if min(ints) < 0:  # -1 kept in an unsigned field (255 / 65535)
        for name, width in (('u8', 1), ('u16', 2)):
            if name in V and max(ints) < (1 << (8 * width)):
                ym = y & ((1 << (8 * width)) - 1)
                hit = np.nonzero(np.all(V[name] == ym[:, None], axis=0))[0]
                found += [{'type': name, 'offset': int(o), 'wrap': True} for o in hit]
    if not found and min(ints) >= 0:  # a few values too big for the field, cut to it (sounds Group Weight 47177 -> 73)
        for name, width in (('u8', 1), ('u16', 2)):
            ym = y & ((1 << (8 * width)) - 1)
            over = int(np.count_nonzero(ym != y))
            if name in V and 0 < over <= max(1, len(ints) // 100):
                hit = np.nonzero(np.all(V[name] == ym[:, None], axis=0))[0]
                found += [{'type': name, 'offset': int(o)} for o in hit]
            if found:
                break
    # a flag; a stray 2 in it (missiles Explosion, NoMultiShot) is set like a 1
    stray = sum(1 for x in ints if x not in (0, 1))
    if stray == 0 or (not found and min(ints) >= 0 and stray <= max(1, len(ints) // 100)):
        yb = (y != 0).astype(np.uint8)
        for bit in range(8):
            hit = np.nonzero(np.all(((data >> bit) & 1) == yb[:, None], axis=0))[0]
            found += [{'type': 'bit', 'offset': int(o), 'bit': bit} for o in hit]
    if stray and min(ints) >= 0 and max(ints) < 8 and not any(f['type'] == 'bit' for f in found):  # a small number packed into a few bits
        yb = y.astype(np.uint8)
        for nb in (2, 3):
            if max(ints) >= (1 << nb):
                continue
            for shift in range(9 - nb):
                hit = np.nonzero(np.all(((data >> shift) & ((1 << nb) - 1)) == yb[:, None], axis=0))[0]
                found += [{'type': 'bits', 'offset': int(o), 'bit': shift, 'count': nb} for o in hit]
    return found


def find_strkey(vals, V, strings, strict=False):
    """A key of the language files, stored as its string id."""
    # a few keys the language files lack (monstats NameStr 'Bunny', misc namestr 'hpo') are let through;
    # not in a key column (superuniques Superunique would take Name's field)
    keyed = [v for v in vals if v]
    known = [v for v in keyed if v.lower() in strings.ids]
    if not keyed or len(known) < (1 if strict else 0.95) * len(keyed) or len({v.lower() for v in known}) < 2:
        return []
    out = []
    for name in ('u16', 'u32', 'i16', 'i32'):
        if name not in V:
            continue
        M = V[name]
        for o in range(0, M.shape[1], WIDTH[name]):
            col = M[:, o]
            empty = None
            ok = True
            for v, x in zip(vals, col):
                x = int(x)
                if not v:
                    if empty is None:
                        empty = x
                    elif empty != x:
                        ok = False
                        break
                elif v.lower() not in strings.ids:
                    continue
                elif x not in strings.ids[v.lower()]:
                    ok = False
                    break
            if ok:
                out.append({'type': 'strkey', 'offset': o, 'width': name, 'empty': empty if empty is not None else 0})
    return out


def find_enum(vals, V):
    """Text values the game turns into numbers of its own (range: none/h2h/rng/both): a field
    whose number is the same for every row with the same text and different for different texts."""
    keys = [v.strip().lower() for v in vals]
    distinct = sorted(set(keys))
    if len(distinct) < 2 or len(distinct) > 80:
        return []
    out = []
    for name, width in INT_TYPES:
        if name not in V:
            continue
        M = V[name]
        for o in range(M.shape[1]):
            col = M[:, o]
            seen = {}
            ok = True
            for k, v in zip(keys, col):
                v = int(v)
                if seen.setdefault(k, v) != v:
                    ok = False
                    break
            if ok and len(set(seen.values())) == len(seen):
                out.append({'type': 'enum', 'offset': o, 'width': name,
                            'map': {str(v): vals[keys.index(k)].strip() for k, v in seen.items()}})
    # the narrowest field at each place
    best = {}
    for c in out:
        if c['offset'] not in best or WIDTH[c['width']] < WIDTH[best[c['offset']]['width']]:
            best[c['offset']] = c
    return list(best.values())


def find_calc(vals, V, code, ctx):
    pat = np.array([bool(v) for v in vals])
    if not pat.any() or 'u32' not in V:
        return []
    u32 = V['u32']
    out = []
    rows_with = np.nonzero(pat)[0]
    for o in range(u32.shape[1]):
        col = u32[:, o]
        if not np.array_equal(col != 0xFFFFFFFF, pat):
            continue
        good = 0
        for i in rows_with[:40]:
            try:
                text, _ = BinCalc.decode(code, int(col[i]), ctx)
            except (BinCalc.CalcError, struct.error, IndexError):
                continue
            good += strip_parens(text) == strip_parens(vals[i])
        if good >= max(1, int(0.8 * min(40, len(rows_with)))):
            out.append({'type': 'calc', 'offset': o})
    return out


# ----------------------------------------------------------------------------- hand-made codecs
# Tables whose columns are packed structures the search above cannot find (a cube input is one
# text cell, but an item index, flags, a quality and a count in the .bin). Worked out from the
# game's own cubemain.txt / .bin pair; `roundtrip cubemain` checks them.

CUBE_QUALITY = {1: 'low', 2: 'nor', 3: 'hiq', 4: 'mag', 5: 'set', 6: 'rar', 7: 'uni', 8: 'crf', 9: 'tmp'}
CUBE_IN_FLAGS = [(0x4, 'nos'), (0x8, 'sock'), (0x10, 'eth'), (0x20, 'noe'), (0x80, 'upg'), (0x100, 'bas'),
                 (0x200, 'exc'), (0x400, 'eli'), (0x800, 'nru')]
CUBE_OUT_FLAGS = [(0x1, 'mod'), (0x4, 'eth'), (0x10, 'uns'), (0x20, 'rem'), (0x40, 'reg'), (0x80, 'exc'),
                  (0x100, 'eli'), (0x200, 'rep'), (0x400, 'rch')]
CUBE_OUT_TYPES = {-1: 'usetype', -2: 'useitem', 1: 'Cow Portal', 2: 'Pandemonium Portal', 3: 'Pandemonium Finale Portal',
                  4: 'Red Portal'}


def _cell(tokens):
    tokens = [t for t in tokens if t]
    return ('"%s"' % ','.join(tokens)) if len(tokens) > 1 else (tokens[0] if tokens else '')


def _cube_names(names):
    items = names.names('weapons', 'code') + names.names('armor', 'code') + names.names('misc', 'code')
    return {'item': items, 'type': names.names('itemtypes', 'Code'), 'uni': names.names('uniqueitems', 'index'),
            'set': names.names('setitems', 'index'), 'prop': names.names('properties', 'code'),
            'class': names.names('playerclass', 'Code')}


def _pick(lst, i):
    return lst[i] if 0 <= i < len(lst) else '#%d' % i


def _cube_input(b, N):
    flags, item, ident, quality, qty = struct.unpack_from('<HHHBB', b)
    if not flags and not item:
        return ''
    if flags & 0x1:
        base = 'any' if item == 0xFFFF else _pick(N['item'], item)
    elif flags & 0x2:
        base = _pick(N['type'], item)
    else:
        base = '#in%d:%d' % (flags & 0x3, item)
    named = flags & 0x40 and ident and quality in (5, 7)
    if named:  # a unique or set item by name: the id is its row + 1
        base = _pick(N['set' if quality == 5 else 'uni'], ident - 1)
    tokens = [base, CUBE_QUALITY.get(quality, '#q%d' % quality) if quality and not named else '']
    tokens += [name for bit, name in CUBE_IN_FLAGS if flags & bit]
    rest = flags & ~(0x3 | 0x40 * bool(named) | sum(bit for bit, _ in CUBE_IN_FLAGS)) & 0xFFFF
    if rest:
        tokens.append('#flags%x' % rest)
    if qty:
        tokens.append('qty=%d' % qty)
    return _cell(tokens)


def _cube_output(b, N):
    flags, item, ident, quality, qty, lvl, kind = struct.unpack_from('<HHHBBBb', b)
    if kind == -4:
        base = _pick(N['item'], item)
    elif kind == -3:
        base = _pick(N['type'], item)
    elif kind == 0 and not flags and not item:
        return ''
    else:
        base = CUBE_OUT_TYPES.get(kind, '#type%d' % kind)
    named = flags & 0x8 and ident and quality in (5, 7)
    if named:
        base = _pick(N['set' if quality == 5 else 'uni'], ident - 1)
    tokens = [base, CUBE_QUALITY.get(quality, '#q%d' % quality) if quality and not named else '']
    tokens += [name for bit, name in CUBE_OUT_FLAGS if flags & bit]
    rest = flags & ~(0x2 | 0x8 * bool(named) | sum(bit for bit, _ in CUBE_OUT_FLAGS)) & 0xFFFF
    if rest:
        tokens.append('#flags%x' % rest)
    for k in range(3):
        p = struct.unpack_from('<H', b, 13 + 2 * k)[0]
        if p:
            tokens.append('pre=%d' % p)
    for k in range(3):
        s = struct.unpack_from('<H', b, 19 + 2 * k)[0]
        if s:
            tokens.append('suf=%d' % s)
    if lvl:
        tokens.append('lvl=%d' % lvl)
    if flags & 0x2:
        tokens.append('sock=%d' % qty)
    elif qty:
        tokens.append('qty=%d' % qty)
    return _cell(tokens)


def decode_cubemain(data, headers, rows, names):
    N = _cube_names(names)
    H = {c: i for i, c in enumerate(headers)}

    def put(i, col, v):
        if col in H:
            rows[i][H[col]] = v
    for i in range(data.shape[0]):
        b = data[i].tobytes()
        enabled, mindiff, cls, op, param, value, numinputs, version, first, last = struct.unpack_from('<BBBBiiHHhh', b)
        put(i, 'enabled', str(enabled))
        put(i, 'min diff', str(mindiff) if mindiff else '')
        put(i, 'class', _pick(N['class'], cls) if cls != 0xFF else '')
        put(i, 'op', str(op) if op else '')
        put(i, 'param', str(param) if param else '')
        put(i, 'value', str(value) if value else '')
        put(i, 'numinputs', str(numinputs))
        put(i, 'version', str(version))
        put(i, 'firstLadderSeason', str(first) if first else '')
        put(i, 'lastLadderSeason', str(last) if last else '')
        ins = [_cube_input(b[20 + 8 * k:28 + 8 * k], N) for k in range(7)]
        for k, v in enumerate(ins):
            put(i, 'input %d' % (k + 1), v)
        outs = []
        for pre, off in (('', 80), ('b ', 169), ('c ', 258)):  # three outputs of 89 bytes
            ob = b[off:off + 89]
            out = _cube_output(ob, N)
            outs.append(out)
            put(i, 'output' + (' ' + pre.strip() if pre else ''), out)
            lv, pl, il = ob[10], ob[11], ob[12]
            put(i, pre + 'lvl', str(lv) if lv else '')
            put(i, pre + 'plvl', str(pl) if pl else '')
            put(i, pre + 'ilvl', str(il) if il else '')
            for m in range(5):
                prop, par, lo, hi, chance = struct.unpack_from('<IHhhH', ob, 25 + 12 * m)
                name = '%smod %d' % (pre, m + 1)
                has = prop != 0xFFFFFFFF
                put(i, name, _pick(N['prop'], prop) if has else '')
                put(i, name + ' chance', str(chance) if has and chance else '')
                put(i, name + ' param', str(par) if has and par else '')
                put(i, name + ' min', str(lo) if has and (lo or hi) else '')
                put(i, name + ' max', str(hi) if has and (lo or hi) else '')
        # the description is a comment the compiler drops (the record keeps only its row number)
        put(i, 'description', '%s -> %s' % (' + '.join(x.strip('"') for x in ins if x), outs[0].strip('"') or '?'))


CUSTOM = {'cubemain': decode_cubemain}
CUSTOM_COLUMNS = {'cubemain': lambda c: c != '*eol'}


# ----------------------------------------------------------------------------- decompiling

def decompile(layout, bin_path, names, code=None, ctx=None, strings=None):
    """-> (headers, rows) of a table from a .bin with the layout found on the game's files."""
    n, size, data = read_bin(bin_path)
    if size != layout['size']:
        raise ValueError('%s: records of %d bytes, the layout is for %d (another game version?)' % (bin_path, size, layout['size']))
    V = views(data)
    headers = layout['columns']
    rows = [[''] * len(headers) for _ in range(n)]
    for ci, col in enumerate(headers):
        f = layout['fields'].get(col)
        if not f:
            continue
        t = f['type']
        zero = f.get('zero', '')
        for i in range(n):
            if t in WIDTH:
                v = int(V[t][i, f['offset']])
                if f.get('wrap') and v == (1 << (8 * WIDTH[t])) - 1:
                    v = -1
                rows[i][ci] = zero if v == 0 else str(v)
            elif t == 'bits':
                v = (int(data[i, f['offset']]) >> f['bit']) & ((1 << f['count']) - 1)
                rows[i][ci] = zero if v == 0 else str(v)
            elif t == 'bit':
                rows[i][ci] = '1' if (data[i, f['offset']] >> f['bit']) & 1 else zero
            elif t == 'str':
                raw = data[i, f['offset']:].tobytes()
                rows[i][ci] = raw[:raw.find(b'\0') if b'\0' in raw else len(raw)].decode('latin1')
            elif t == 'code4':
                rows[i][ci] = data[i, f['offset']:f['offset'] + 4].tobytes().rstrip(b' \0').decode('latin1')
            elif t == 'ref':
                v = int(V[f['width']][i, f['offset']])
                if v == f['empty'] or v == (1 << 8 * WIDTH[f['width']]) - 1:  # all ones: no row
                    continue
                k = v - f.get('plus', 0)
                target = names.names(f['table'], f.get('key'))
                grp = GROUP_TABLES.get(f['table'])
                if grp and k >= grp[1]:
                    k -= grp[1]
                    target = names.names(grp[0])
                rows[i][ci] = target[k] if 0 <= k < len(target) else '#%d' % k
            elif t == 'kindref':
                tab = f['tables'].get(str(int(data[i, f['kind']])))
                v = int(V[f['width']][i, f['offset']])
                if tab:
                    target = names.names(tab)
                    rows[i][ci] = target[v] if 0 <= v < len(target) else '#%d' % v
            elif t == 'strkey':
                v = int(V[f['width']][i, f['offset']])
                if v != f['empty']:
                    rows[i][ci] = strings.keys.get(v, '#%d' % v) if strings else '#%d' % v
            elif t == 'enum':
                v = int(V[f['width']][i, f['offset']])
                rows[i][ci] = f['map'].get(str(v), '#%d' % v)
            elif t == 'calc':
                v = int(V['u32'][i, f['offset']])
                if v == 0xFFFFFFFF or code is None:
                    continue
                try:
                    rows[i][ci] = BinCalc.decode(code, v, ctx)[0]
                except (BinCalc.CalcError, struct.error, IndexError) as e:
                    rows[i][ci] = '?calc:%s' % e
            elif t == 'const':
                rows[i][ci] = '' if f['value'] == 0 and zero == '' else str(f['value'])
            elif t == 'rowname':
                target = names.names(TXT_OF.get(layout.get('table'), layout.get('table')), col)
                rows[i][ci] = target[i] if i < len(target) else ''
            elif t == 'reflist':
                target = names.names(f['table'], f.get('key'))
                toks = []
                for x in data[i, f['offset']:f['offset'] + f['count']].tolist():
                    if x == LIST_END:
                        break
                    toks.append(target[x] if x < len(target) else '#%d' % x)
                rows[i][ci] = ('"%s"' % ','.join(toks)) if len(toks) > 1 else (toks[0] if toks else '')
    # a property's parameter, once the property is known: a row of the table it names, or a number
    for ci, col in enumerate(headers):
        f = layout['fields'].get(col)
        if not f or f['type'] != 'param':
            continue
        pi = headers.index(f['prop'])
        for i in range(n):
            v = int(V['i32'][i, f['offset']])
            prop = rows[i][pi].strip().lower()
            table = f.get('tables', {}).get(prop)
            if not prop or (not v and not table):
                rows[i][ci] = ''
            elif table:
                target = names.names(table)
                rows[i][ci] = target[v] if 0 <= v < len(target) else str(v)
            else:
                rows[i][ci] = str(v)
    if layout.get('table') in CUSTOM:
        CUSTOM[layout['table']](data, headers, rows, names)
    return headers, rows


def fingerprint(game_src, table):
    """What a layout was worked out from: the game's .txt and .bin of the table (a patch changes them)."""
    import hashlib
    h = hashlib.sha1(b'layout %d' % LAYOUT_VERSION)
    for ext in ('.txt', '.bin'):
        p = game_src.path(TXT_OF.get(table, table) if ext == '.txt' else table, ext)
        h.update(p.read_bytes() if p else b'-')
    return h.hexdigest()


def load_layout(table, game_src, out_dir=LAYOUTS, log=print):
    """The cached layout, worked out again when the game's files of the table changed (a patch)."""
    p = out_dir / (table + '.json')
    if p.exists():
        lay = json.loads(p.read_text(encoding='utf-8'))
        if lay.get('stock') == fingerprint(game_src, table):
            return lay
        log('%s: the game files changed since the layout was made; working it out again' % table)
    lay = infer(table, game_src, log)
    out_dir.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(lay, indent=1), encoding='utf-8')
    return lay


def self_keyed(lay, table):
    """A table whose key column is only its row number (itemstatcost, states, skilldesc ...): no name is stored."""
    f = lay['fields'].get(lay['columns'][0]) or {}
    return f.get('type') == 'rowname' or (f.get('type') == 'ref' and f.get('table') == table and not f.get('plus'))


# a made-up name for a mod's new row of a self-keyed table: the row of another table that uses it
NAME_HINTS = {'skilldesc': ('skills', 'skilldesc'), 'monstats2': ('monstats', 'MonStatsEx'), 'pettype': ('skills', 'pettype')}


def name_rows(tables, mod, game, decoded, log=print):
    """Names for the rows of self-keyed tables, put in `decoded` so the key column and every reference use them.

    The record stores its own row number, so a row is the game's row of the same number (mods append);
    rows past the game's get made-up names: a skilldesc row the name of the skill using it, others
    '<table>_<row>'. The made-up names are the same on every run."""
    lays = {t: load_layout(t, game, log=log) for t in tables}
    for t in tables:
        lay = lays[t]
        p = mod.path(t, '.bin')
        key = lay['columns'][0]
        if not p or t in CUSTOM or not self_keyed(lay, t) or key in decoded.get(t, {}):
            continue
        f = lay['fields'][key]
        n, size, data = read_bin(p)
        dup = {}
        if f['type'] == 'ref':
            stored = views(data)[f['width']][:, f['offset']]
            # a row storing an earlier row's number has that row's name (the compiler numbers a key by its first row)
            dup = {i: int(stored[i]) for i in range(n) if int(stored[i]) != i}
        odd = [i for i, j in dup.items() if not 0 <= j < i]
        if odd:
            log('%s: %d rows do not store their own row number (e.g. row %d); names may be off' % (t, len(odd), odd[0]))
        stock = Names(game).names(t, key)
        names = list(stock[:n])
        taken = {x.lower() for x in names}
        hints = {}
        src, col = NAME_HINTS.get(t, (None, None))
        if src and mod.path(src, '.bin'):
            sl = load_layout(src, game, log=log)
            g = sl['fields'].get(col) or {}
            src_names = decoded.get(src, {}).get(sl['columns'][0])
            if g.get('type') == 'ref' and src_names:
                _, _, sd = read_bin(mod.path(src, '.bin'))
                for name, v in zip(src_names, views(sd)[g['width']][:, g['offset']].tolist()):
                    if name.strip():
                        hints.setdefault(int(v), name.lower() if t == 'skilldesc' else name)
        for i in range(len(names), n):
            if i in dup and i not in odd:
                names.append(names[dup[i]])
                continue
            base = hints.get(i) or '%s_%d' % (t, i)
            name, k = base, 2
            while name.lower() in taken:
                name, k = '%s %d' % (base, k), k + 1
            taken.add(name.lower())
            names.append(name)
        decoded.setdefault(t, {})[key] = names
        if n > len(stock):
            log('%s: %d rows past the game\'s got made-up names (%s ...)' % (t, n - len(stock), ', '.join(names[len(stock):len(stock) + 3])))


def decompile_mod(mod_root, out, tables, game, log=print):
    """Decompile a mod's tables to <out>/global/excel/<table>.txt, rows named consistently across the tables."""
    mod = Source(mod_root)
    decoded = {}
    names = Names(mod, game, decoded)
    strings = Strings(mod.root, game.root)  # the mod's own entries first: an id keeps the key the mod gives it
    # key names first, so references between the tables name the mod's own rows
    for t in tables:
        lay = load_layout(t, game, log=log)
        p = mod.path(t, '.bin')
        keys = {c: f for c, f in lay['fields'].items() if f['type'] in ('str', 'code4')}
        if p and keys:
            h, rows = decompile({'size': lay['size'], 'columns': list(keys), 'fields': keys}, p, names)
            decoded[t] = {c: [r[i] for r in rows] for i, c in enumerate(h)}
    name_rows(tables, mod, game, decoded, log)
    done = {}
    for t in tables:
        lay = load_layout(t, game, log=log)
        p = mod.path(t, '.bin')
        if not p:
            log('%s: no %s.bin in the mod' % (t, t))
            continue
        code = ctx = None
        if t in CALCS:
            code = mod.code(CALCS[t][0]) or game.code(CALCS[t][0])
            ctx = calc_context(names, t)
        h, rows = decompile(lay, p, names, code, ctx, strings)
        if out is not None:
            write_txt(Path(out) / 'global' / 'excel' / (t + '.txt'), h, rows)
        done[t] = (h, rows)
        custom = CUSTOM_COLUMNS.get(t, lambda c: False)
        missing = [c for c, f in lay['fields'].items() if f['type'] in ('missing', 'ambiguous') and not custom(c)]
        log('%s: %d rows written; columns not found in the layout (left empty): %s' % (t, len(rows), ', '.join(missing) or 'none'))
    return done


def write_txt(path, headers, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(('\r\n'.join(['\t'.join(headers)] + ['\t'.join(r) for r in rows]) + '\r\n').encode('latin1', 'replace'))


def same(a, b):
    a, b = a.strip(), b.strip()
    if a == b or (a in ('', '0') and b in ('', '0')):
        return True
    return strip_parens(a) == strip_parens(b)


def same_param(f, got, want, headers, row, names):
    """A property's parameter written as a row number where the decompiler names the row (36 = Fire Bolt)."""
    k = as_int(want.strip().strip('"'))
    table = f.get('tables', {}).get(row[headers.index(f['prop'])].strip().lower())
    if k is None or not table:
        return False
    target = names.names(table)
    return 0 <= k < len(target) and target[k].strip().lower() == got.strip().lower()


def roundtrip(table, game_src, log=print):
    lay = load_layout(table, game_src, log=log)
    names = Names(game_src)
    code = ctx = None
    if table in CALCS:
        code = game_src.code(CALCS[table][0])
        ctx = calc_context(names, table)
    h, got = decompile(lay, game_src.path(table, '.bin'), names, code, ctx, Strings(game_src.root))
    _, want = game_src.txt(TXT_OF.get(table, table))
    if len(want) != len(got):
        want = compiled_rows(want)
    cells = ok = 0
    by_col = {}
    for ci, col in enumerate(h):
        if col.startswith('*'):
            continue
        f = lay['fields'].get(col) or {}
        for g, w in zip(got, want):
            if not w[ci].strip() and not g[ci].strip():
                continue
            cells += 1
            if same(g[ci], w[ci]) or (f.get('type') == 'param' and same_param(f, g[ci], w[ci], h, g, names)):
                ok += 1
            else:
                by_col[col] = by_col.get(col, 0) + 1
    log('%s: %d of %d filled cells come back the same (%.1f%%); columns with differences: %s' % (
        table, ok, cells, 100.0 * ok / max(cells, 1), ', '.join('%s %d' % kv for kv in sorted(by_col.items(), key=lambda x: -x[1])[:15])))
    return ok, cells, by_col


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=('infer', 'report', 'roundtrip', 'decompile'))
    ap.add_argument('args', nargs='+')
    ap.add_argument('--vanilla', default=str(VANILLA))
    ap.add_argument('--layouts', default=str(LAYOUTS))
    ap.add_argument('--out')
    a = ap.parse_intermixed_args()
    game = Source(a.vanilla)
    lay_dir = Path(a.layouts)
    if a.cmd == 'infer':
        lay_dir.mkdir(parents=True, exist_ok=True)
        for t in a.args:
            lay = infer(t, game)
            (lay_dir / (t + '.json')).write_text(json.dumps(lay, indent=1), encoding='utf-8')
    elif a.cmd == 'report':
        lay = json.loads((lay_dir / (a.args[0] + '.json')).read_text(encoding='utf-8'))
        for col in lay['columns']:
            f = lay['fields'].get(col)
            if f:
                print('%-28s %s' % (col, json.dumps(f)[:150]))
    elif a.cmd == 'roundtrip':
        for t in a.args:
            roundtrip(t, game)
    else:
        decompile_mod(a.args[0], Path(a.out or '.'), a.args[1:], game)


if __name__ == '__main__':
    main()
