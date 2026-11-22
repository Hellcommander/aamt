"""Deep JSON patches for the game's JSON files (HD state machines, animation timelines, item / missile /
overlay / preset definitions, UI layouts): the difference between the game's copy and a mod's copy,
merged at install time into the file as the mods above left it. Used by ConvertDataMod.py (data
mods' copied JSON) and ConvertReplaceMod.py (D2RMM mods that copy whole files). JSON_JS is the
install-time twin of json_apply, inserted into both converters' mod.js.
"""
import json
import re
from pathlib import Path

# The game's JSON a mod may change (the four HD name maps ConvertDataMod merges by key are matched first).
JSON_PATH = re.compile(r'(?i)(?:^|/)((?:hd/.+\.(?:json|timelines))|(?:global/ui/layouts/.+\.json))$')

# ---------------------------------------------------------------- deep JSON patches
# A patch is one of:
#   {"=": value}                                  replace (also: an added key)
#   {"{": {key: patch}, "-": [keys]}             object: patch these keys, delete those
#   {"[": field, "set": {id: patch}, "add": [[after_id, value]], "-": [ids]}
#                                                 list of objects named by `field` (name, id...):
#                                                 patch / add after the entry before it / delete by name
#   {"#": {index: patch}, "n": length}            list patched by position (same length)
#   {"+": [values]}                               list the mod only appended to
ID_FIELDS = ('name', 'Name', 'id', 'ID', 'path', 'key', 'Key')


def _id_field(*lists):
    for f in ID_FIELDS:
        ok = True
        for lst in lists:
            if not lst or not all(isinstance(e, dict) and isinstance(e.get(f), (str, int)) for e in lst):
                ok = False
                break
            ids = [e[f] for e in lst]
            if len(set(ids)) != len(ids):
                ok = False
                break
        if ok:
            return f
    return None


def json_patch(v, m):
    """The patch that turns v into m, or None when they are equal."""
    if v == m:
        return None
    if isinstance(v, dict) and isinstance(m, dict):
        sub = {}
        for k, mv in m.items():
            if k not in v:
                sub[k] = {'=': mv}
            else:
                p = json_patch(v[k], mv)
                if p is not None:
                    sub[k] = p
        gone = [k for k in v if k not in m]
        out = {'{': sub}
        if gone:
            out['-'] = gone
        return out
    if isinstance(v, list) and isinstance(m, list):
        f = _id_field(v, m)
        if f is not None and {e[f] for e in v} - {e[f] for e in m} and len(v) == len(m):
            f = None  # an entry renamed in place: the sequence diff pairs it with its old self
        if f is not None:
            common = {e[f] for e in v} & {e[f] for e in m}
            if [e[f] for e in v if e[f] in common] != [e[f] for e in m if e[f] in common]:
                f = None  # the mod reordered entries: the sequence diff keeps its order
        if f is None:
            return seq_patch(v, m)
        if f is not None:
            vid = {e[f]: e for e in v}
            mid = [e[f] for e in m]
            sub, add = {}, []
            prev = None
            for e in m:
                k = e[f]
                if k in vid:
                    p = json_patch(vid[k], e)
                    if p is not None:
                        sub[str(k)] = p
                else:
                    add.append([prev, e])
                prev = k
            gone = [k for k in vid if k not in set(mid)]
            out = {'[': f, 'set': sub, 'add': add}
            if gone:
                out['-'] = gone
            return out
    return {'=': m}


# ---- lists without a name field: a sequence diff
# {"~": [[op...]], "v": [fingerprint of every stock entry]}; ops in order:
#   ["mod", i, patch]   the stock entry i changed
#   ["del", i]          the stock entry i removed
#   ["ins", i, value]   a new entry after the stock entry i (-1: at the start)
# At install time the fingerprints find the stock entries in the list as the mods above left it
# (another mod may have inserted or changed some), and the ops go in around them.

def canon_num(s):
    """A number's shortest round-trip text (Python repr / JS String) as digits and exponent, so
    92, 92.0 and 9.2e1 match and 6.12731409072876 never matches 6.127314 (JS twin: canonNum)."""
    s = s.strip().lower()
    neg = s.startswith('-')
    s = s.lstrip('+-')
    if s in ('nan', 'inf', 'infinity'):
        return s
    exp = 0
    if 'e' in s:
        s, e = s.split('e')
        exp = int(e)
    if '.' in s:
        whole, frac = s.split('.')
    else:
        whole, frac = s, ''
    digits = (whole + frac).lstrip('0')
    exp += len(whole) - (len(whole + frac) - len(digits))  # position of the first significant digit
    digits = digits.rstrip('0')
    if not digits:
        return '0'
    return ('-' if neg else '') + digits + 'e' + str(exp)


def canon(x):
    """The same text in Python and in the wrapper's JS (canon()), for comparing entries."""
    if x is None:
        return 'null'
    if x is True:
        return 'true'
    if x is False:
        return 'false'
    if isinstance(x, (int, float)):
        return canon_num(repr(x))
    if isinstance(x, str):
        return '"' + x.replace('\\', '\\\\').replace('"', '\\"') + '"'
    if isinstance(x, list):
        return '[' + ','.join(canon(e) for e in x) + ']'
    return '{' + ','.join(canon(k) + ':' + canon(x[k]) for k in sorted(x)) + '}'


# Gaps bigger than this many cells (len(A) * len(B)) are split at anchors first (patience diff):
# a full table for hd/texture_desc_cache.json (31k entries) would need gigabytes (Reimagined failed
# at install with "invalid array buffer length", 2026-11-21).
LCS_MAX_CELLS = 2000000


def _lcs_range(a, b, a0, a1, b0, b1, pairs):
    """Append the common pairs of a[a0:a1] and b[b0:b1] to pairs, in order."""
    s = 0
    while a0 + s < a1 and b0 + s < b1 and a[a0 + s] == b[b0 + s]:
        s += 1
    e = 0
    while e < a1 - a0 - s and e < b1 - b0 - s and a[a1 - 1 - e] == b[b1 - 1 - e]:
        e += 1
    pairs.extend((a0 + k, b0 + k) for k in range(s))
    A0, A1, B0, B1 = a0 + s, a1 - e, b0 + s, b1 - e
    la, lb = A1 - A0, B1 - B0
    if la and lb and la * lb <= LCS_MAX_CELLS:
        W = lb + 1
        dp = [0] * ((la + 1) * W)
        for i in range(la - 1, -1, -1):
            for j in range(lb - 1, -1, -1):
                dp[i * W + j] = dp[(i + 1) * W + j + 1] + 1 if a[A0 + i] == b[B0 + j] else max(dp[(i + 1) * W + j], dp[i * W + j + 1])
        i = j = 0
        while i < la and j < lb:
            if a[A0 + i] == b[B0 + j]:
                pairs.append((A0 + i, B0 + j))
                i += 1
                j += 1
            elif dp[(i + 1) * W + j] >= dp[i * W + j + 1]:
                i += 1
            else:
                j += 1
    elif la and lb:
        # anchors: entries found exactly once on each side, kept in a longest increasing run
        ca, cb = {}, {}
        for i in range(A0, A1):
            ca[a[i]] = -1 if a[i] in ca else i
        for j in range(B0, B1):
            cb[b[j]] = -1 if b[j] in cb else j
        cand = [(i, cb[a[i]]) for i in range(A0, A1) if ca[a[i]] >= 0 and cb.get(a[i], -1) >= 0]
        tails, prev = [], []  # patience sort on the b index
        for k, (_, j) in enumerate(cand):
            lo, hi = 0, len(tails)
            while lo < hi:
                mid = (lo + hi) // 2
                if cand[tails[mid]][1] < j:
                    lo = mid + 1
                else:
                    hi = mid
            prev.append(tails[lo - 1] if lo else -1)
            if lo == len(tails):
                tails.append(k)
            else:
                tails[lo] = k
        run = []
        k = tails[-1] if tails else -1
        while k >= 0:
            run.append(cand[k])
            k = prev[k]
        run.reverse()
        pi, pj = A0, B0
        for (i, j) in run:
            _lcs_range(a, b, pi, i, pj, j, pairs)
            pairs.append((i, j))
            pi, pj = i + 1, j + 1
        if run:
            _lcs_range(a, b, pi, A1, pj, B1, pairs)
    pairs.extend((a1 - e + k, b1 - e + k) for k in range(e))


def lcs_pairs(a, b):
    """Index pairs of a longest common subsequence of the string lists a and b (exact up to
    LCS_MAX_CELLS per gap, anchored on unique entries beyond)."""
    pairs = []
    _lcs_range(a, b, 0, len(a), 0, len(b), pairs)
    return pairs


def align(vkeys, ckeys):
    """stock index -> index in the current list: the common entries, then the changed ones paired
    in order inside each gap (an entry another mod or this mod edited in place)."""
    pairs = lcs_pairs(vkeys, ckeys)
    out = {}
    pi = pj = -1
    for (i, j) in pairs + [(len(vkeys), len(ckeys))]:
        gi, gj = list(range(pi + 1, i)), list(range(pj + 1, j))
        for x, y in zip(gi, gj):
            out[x] = y
        if i < len(vkeys):
            out[i] = j
        pi, pj = i, j
    return out


def seq_patch(v, m):
    vk = [canon(e) for e in v]
    mk = [canon(e) for e in m]
    pairs = lcs_pairs(vk, mk)
    ops = []
    pi = pj = -1
    for (i, j) in pairs + [(len(v), len(m))]:
        gi, gj = list(range(pi + 1, i)), list(range(pj + 1, j))
        k = 0
        last = pi
        while k < len(gi) and k < len(gj):  # changed in place
            p = json_patch(v[gi[k]], m[gj[k]])
            if p is not None:
                ops.append(['mod', gi[k], p])
            last = gi[k]
            k += 1
        for x in gi[k:]:
            ops.append(['del', x])
        for y in gj[k:]:
            ops.append(['ins', last, m[y]])
        pi, pj = i, j
    return {'~': ops, 'v': vk}


def seq_apply(cur, p):
    if not isinstance(cur, list):
        return cur
    vk = p['v']
    where = align(vk, [canon(e) for e in cur])
    out = list(cur)
    dels = set()
    inserts = {}  # current index (or -1) -> values after it, in order
    # entries other mods added (not stock ones): an insert equal to one of them is already there
    mapped = set(where.values())
    present = {canon(e) for i, e in enumerate(cur) if i not in mapped}
    for op in p['~']:
        if op[0] == 'mod':
            if op[1] in where:
                out[where[op[1]]] = json_apply(out[where[op[1]]], op[2])
        elif op[0] == 'del':
            if op[1] in where:
                dels.add(where[op[1]])
        else:
            anchor = -1 if op[1] < 0 else where.get(op[1], len(cur) - 1)
            if canon(op[2]) not in present:
                inserts.setdefault(anchor, []).append(op[2])
    result = list(inserts.get(-1, []))
    for i, e in enumerate(out):
        if i not in dels:
            result.append(e)
        result.extend(inserts.get(i, []))
    return result


def json_apply(cur, p):
    """Python twin of applyJsonPatch in the wrapper: apply p to cur (what the mods above left)."""
    if p is None:
        return cur
    if '=' in p:
        return p['=']
    if '{' in p:
        if not isinstance(cur, dict):
            return cur
        out = dict(cur)
        for k, sp in p['{'].items():
            if k in out:
                out[k] = json_apply(out[k], sp)
            elif '=' in sp:
                out[k] = sp['=']
        for k in p.get('-', []):
            out.pop(k, None)
        return out
    if '#' in p:
        if not isinstance(cur, list):
            return cur
        out = list(cur)
        for i, sp in p['#'].items():
            i = int(i)
            if i < len(out):
                out[i] = json_apply(out[i], sp)
        return out
    if '[' in p:
        if not isinstance(cur, list):
            return cur
        f = p['[']
        out = [e for e in cur if not (isinstance(e, dict) and e.get(f) in p.get('-', []))]
        for k, sp in p['set'].items():
            for i, e in enumerate(out):
                if isinstance(e, dict) and str(e.get(f)) == k:
                    out[i] = json_apply(e, sp)
                    break
        for after, val in p['add']:
            if any(isinstance(e, dict) and e.get(f) == val.get(f) for e in out):
                for i, e in enumerate(out):  # another mod added it too: this mod's version
                    if isinstance(e, dict) and e.get(f) == val.get(f):
                        out[i] = val
                continue
            at = next((i for i, e in enumerate(out) if isinstance(e, dict) and e.get(f) == after), None) if after is not None else -1
            if at is None:
                out.append(val)
            else:
                out.insert(at + 1, val)
        return out
    if '+' in p:
        if not isinstance(cur, list):
            return cur
        return list(cur) + [x for x in p['+'] if x not in cur]
    if '~' in p:
        return seq_apply(cur, p)
    return cur


def strip_comments(text):
    """JSON with // and /* */ comments (the game's UI layouts) -> plain JSON; strings are left alone."""
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == '\\' else 1
            out.append(text[i:j + 1])
            i = j + 1
        elif text.startswith('//', i):
            j = text.find('\n', i)
            i = n if j < 0 else j
        elif text.startswith('/*', i):
            j = text.find('*/', i + 2)
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def read_json_file(path):
    """The game's JSON (comments and trailing commas allowed, as the game and D2RMM read it), or None."""
    try:
        text = Path(path).read_bytes().decode('utf-8-sig')
    except (OSError, UnicodeDecodeError):
        return None
    try:
        return json.loads(text)
    except ValueError:
        try:
            return json.loads(re.sub(r',(\s*[}\]])', r'\1', strip_comments(text)))
        except ValueError:
            return None


JSON_JS = r'''
// Deep JSON patches (ConvertReplaceMod.json_patch / json_apply): the mod's changes to a JSON file,
// merged into the file as the mods above left it.
function applyJsonPatch(cur, p) {
  if (!p) return cur;
  if ('=' in p) return p['='];
  const isObj = (x) => x && typeof x === 'object' && !Array.isArray(x);
  if ('{' in p) {
    if (!isObj(cur)) return cur;
    const out = Object.assign({}, cur);
    Object.keys(p['{']).forEach((k) => {
      const sp = p['{'][k];
      if (k in out) out[k] = applyJsonPatch(out[k], sp);
      else if ('=' in sp) out[k] = sp['='];
    });
    (p['-'] || []).forEach((k) => delete out[k]);
    return out;
  }
  if ('#' in p) {
    if (!Array.isArray(cur)) return cur;
    const out = cur.slice();
    Object.keys(p['#']).forEach((i) => { if (Number(i) < out.length) out[Number(i)] = applyJsonPatch(out[Number(i)], p['#'][i]); });
    return out;
  }
  if ('[' in p) {
    if (!Array.isArray(cur)) return cur;
    const f = p['['];
    const gone = new Set(p['-'] || []);
    const named = (e) => isObj(e) && e[f] !== undefined;
    let out = cur.filter((e) => !(named(e) && gone.has(e[f])));
    Object.keys(p.set).forEach((k) => {
      const i = out.findIndex((e) => named(e) && String(e[f]) === k);
      if (i >= 0) out[i] = applyJsonPatch(out[i], p.set[k]);
    });
    p.add.forEach(([after, val]) => {
      const there = out.findIndex((e) => named(e) && e[f] === val[f]);
      if (there >= 0) { out[there] = val; return; } // another mod added it too: this mod's version
      const at = after === null ? -1 : out.findIndex((e) => named(e) && e[f] === after);
      if (after !== null && at < 0) out.push(val);
      else out.splice(at + 1, 0, val);
    });
    return out;
  }
  if ('+' in p) {
    if (!Array.isArray(cur)) return cur;
    const seen = new Set(cur.map((x) => JSON.stringify(x)));
    return cur.concat(p['+'].filter((x) => !seen.has(JSON.stringify(x))));
  }
  if ('~' in p) return seqApply(cur, p);
  return cur;
}
// Twins of ConvertReplaceMod.canon / lcs_pairs / align / seq_apply (same results, same tie-breaks).
function canonNum(t) {
  let s = t.trim().toLowerCase();
  const neg = s.startsWith('-');
  s = s.replace(/^[+-]+/, '');
  if (s === 'nan' || s === 'infinity') return s === 'infinity' ? 'inf' : s;
  let exp = 0;
  if (s.includes('e')) {
    const parts = s.split('e');
    s = parts[0];
    exp = parseInt(parts[1], 10);
  }
  const dot = s.indexOf('.');
  const whole = dot < 0 ? s : s.slice(0, dot);
  const frac = dot < 0 ? '' : s.slice(dot + 1);
  let digits = (whole + frac).replace(/^0+/, '');
  exp += whole.length - ((whole + frac).length - digits.length);
  digits = digits.replace(/0+$/, '');
  if (!digits) return '0';
  return (neg ? '-' : '') + digits + 'e' + exp;
}
function canon(x) {
  if (x === null || x === undefined) return 'null';
  if (x === true) return 'true';
  if (x === false) return 'false';
  if (typeof x === 'number') return canonNum(String(x));
  if (typeof x === 'string') return '"' + x.replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"';
  if (Array.isArray(x)) return '[' + x.map(canon).join(',') + ']';
  return '{' + Object.keys(x).sort().map((k) => canon(k) + ':' + canon(x[k])).join(',') + '}';
}
const LCS_MAX_CELLS = 2000000; // bigger gaps are split at unique entries first (patience diff)
function lcsRange(a, b, a0, a1, b0, b1, pairs) {
  let s = 0;
  while (a0 + s < a1 && b0 + s < b1 && a[a0 + s] === b[b0 + s]) s++;
  let e = 0;
  while (e < a1 - a0 - s && e < b1 - b0 - s && a[a1 - 1 - e] === b[b1 - 1 - e]) e++;
  for (let k = 0; k < s; k++) pairs.push([a0 + k, b0 + k]);
  const A0 = a0 + s, A1 = a1 - e, B0 = b0 + s, B1 = b1 - e;
  const la = A1 - A0, lb = B1 - B0;
  if (la && lb && la * lb <= LCS_MAX_CELLS) {
    const W = lb + 1;
    const dp = new Int32Array((la + 1) * W);
    for (let i = la - 1; i >= 0; i--) {
      for (let j = lb - 1; j >= 0; j--) {
        dp[i * W + j] = a[A0 + i] === b[B0 + j] ? dp[(i + 1) * W + j + 1] + 1 : Math.max(dp[(i + 1) * W + j], dp[i * W + j + 1]);
      }
    }
    let i = 0, j = 0;
    while (i < la && j < lb) {
      if (a[A0 + i] === b[B0 + j]) { pairs.push([A0 + i, B0 + j]); i++; j++; }
      else if (dp[(i + 1) * W + j] >= dp[i * W + j + 1]) i++;
      else j++;
    }
  } else if (la && lb) {
    const ca = new Map(), cb = new Map();
    for (let i = A0; i < A1; i++) ca.set(a[i], ca.has(a[i]) ? -1 : i);
    for (let j = B0; j < B1; j++) cb.set(b[j], cb.has(b[j]) ? -1 : j);
    const cand = [];
    for (let i = A0; i < A1; i++) {
      if (ca.get(a[i]) >= 0 && cb.has(a[i]) && cb.get(a[i]) >= 0) cand.push([i, cb.get(a[i])]);
    }
    const tails = [], prev = [];
    cand.forEach(([, j], k) => {
      let lo = 0, hi = tails.length;
      while (lo < hi) {
        const mid = (lo + hi) >> 1;
        if (cand[tails[mid]][1] < j) lo = mid + 1; else hi = mid;
      }
      prev.push(lo ? tails[lo - 1] : -1);
      if (lo === tails.length) tails.push(k); else tails[lo] = k;
    });
    const run = [];
    for (let k = tails.length ? tails[tails.length - 1] : -1; k >= 0; k = prev[k]) run.push(cand[k]);
    run.reverse();
    let pi = A0, pj = B0;
    run.forEach(([i, j]) => {
      lcsRange(a, b, pi, i, pj, j, pairs);
      pairs.push([i, j]);
      pi = i + 1; pj = j + 1;
    });
    if (run.length) lcsRange(a, b, pi, A1, pj, B1, pairs);
  }
  for (let k = 0; k < e; k++) pairs.push([a1 - e + k, b1 - e + k]);
}
function lcsPairs(a, b) {
  const pairs = [];
  lcsRange(a, b, 0, a.length, 0, b.length, pairs);
  return pairs;
}
function alignSeq(vkeys, ckeys) {
  const pairs = lcsPairs(vkeys, ckeys).concat([[vkeys.length, ckeys.length]]);
  const out = new Map();
  let pi = -1, pj = -1;
  pairs.forEach(([i, j]) => {
    for (let x = pi + 1, y = pj + 1; x < i && y < j; x++, y++) out.set(x, y);
    if (i < vkeys.length) out.set(i, j);
    pi = i; pj = j;
  });
  return out;
}
function seqApply(cur, p) {
  if (!Array.isArray(cur)) return cur;
  const where = alignSeq(p.v, cur.map(canon));
  const out = cur.slice();
  const dels = new Set();
  const inserts = new Map();
  const mapped = new Set(where.values());
  const present = new Set(cur.filter((e, i) => !mapped.has(i)).map(canon));
  p['~'].forEach((op) => {
    if (op[0] === 'mod') {
      if (where.has(op[1])) out[where.get(op[1])] = applyJsonPatch(out[where.get(op[1])], op[2]);
    } else if (op[0] === 'del') {
      if (where.has(op[1])) dels.add(where.get(op[1]));
    } else {
      const anchor = op[1] < 0 ? -1 : (where.has(op[1]) ? where.get(op[1]) : cur.length - 1);
      if (!present.has(canon(op[2]))) {
        if (!inserts.has(anchor)) inserts.set(anchor, []);
        inserts.get(anchor).push(op[2]);
      }
    }
  });
  const result = (inserts.get(-1) || []).slice();
  out.forEach((e, i) => {
    if (!dels.has(i)) result.push(e);
    (inserts.get(i) || []).forEach((x) => result.push(x));
  });
  return result;
}
'''
