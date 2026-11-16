"""Turns a Diablo II: Resurrected data mod (an .mpq folder) into a D2RMM mod.

    python ConvertDataMod.py --game <D2R folder> --mod <mod folder> [--author A] [--name N]
                             [--version V] [--cache <folder>] [--check]

A data mod ships whole game files: <mod>\\<Name>.mpq\\data\\... (with modinfo.json) or
<mod>\\data\\..., and maybe <mod>\\d2rloader\\ (plugins, config, patches). D2RMM can install it
as it is, but then every file it ships replaces that file outright, so whatever an earlier mod
changed in the same table is lost, and every table is frozen at the game version the mod was
made for.

The conversion leaves the mod's files where they are and adds, in the mod folder:

    mod.json, mod.js           the D2RMM mod (mod.js is generated, see below)
    d2rmm\\patches\\...json     one patch per table and per string file the mod changes
    d2rmm\\convert.json         what was found (for the README and for reruns)

What mod.js does at install time:
  - tables (global\\excel\\**\\*.txt the game also has): applies the mod's changes row by row on
    top of what D2RMM hands it. Rows are matched by their first column (spaces around it ignored
    unless --no-match-trim) and the how-many-th row with that name; rows that share a name are
    matched by content (--duplicates content, default), so a changed cell changes only that cell,
    deleted rows go (rows keep: they stay, switched off with --deleted disable), new rows come in
    the mod's order. Rows earlier mods added stay (after the mod's rows).
  - strings (local\\lng\\**\\*.json the game also has, arrays of {Key, ...}): replaces or adds the
    mod's entries by Key and removes the ones the mod removed.
  - every other file: copied as it is (files byte-identical to the game's are skipped).
  - d2rloader\\ (plugins, config, patches, sounds, ...): copied to D2RMM's d2rloader output, as D2RMM does for
    data mods (logs, backups and the package metadata.json left out).
Tables or string files that cannot be patched safely (duplicate column names, not UTF-8, not a
Key list) are copied whole; convert.json lists them.

--check verifies the result: every patch applied to the game's file must give the mod's file
(in Python), and then mod.js itself is run with a mock D2RMM (ConvertDataModCheck.js) and its
output compared with the mod's files.

The patch files reach mod.js through D2RMM.copyFile into a scratch file and D2RMM.readJson
(D2RMM has no call to read a mod's own files); the scratch file d2rmm-convert\\<id>.json is left
empty in the output.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Left out of the d2rloader folder: run-time output, and the package's metadata.json (D2RMM
# writes its own for the merged output).
LOADER_SKIP = ('logs', 'backups', 'metadata.json', 'crashes', 'data')  # data = D2RLoader's own caches
SKIP_SUFFIXES = ('.log',)

# Features: every change of the mod belongs to one, and each gets an on/off switch in the D2RMM
# settings of the converted mod. First match wins (paths relative to data, lower case, '/').
# 'core' (tables and text other changes depend on) is always installed.
import re as _re
FEATURES = [
    ('inventory', 'Inventory, stash and cube size', 'inventory.txt and the inventory, stash and cube panels',
     [r'^global/excel/(base/)?inventory\.txt$', r'^global/ui/layouts/.*(inventory|stash|horadric|cube|bank).*',
      r'^hd/global/ui/(panel|layouts)/.*(inventory|stash|horadric|cube|bank).*']),
    ('cube', 'Cube recipes', 'cubemain.txt', [r'cubemain\.txt$']),
    ('runewords', 'Runewords', 'runes.txt', [r'(^|/)runes\.txt$']),
    ('uniques', 'Unique and set items', 'uniqueitems.txt, setitems.txt, sets.txt', [r'(uniqueitems|setitems|sets)\.txt$']),
    ('affixes', 'Magic and rare affixes', 'magicprefix, magicsuffix, automagic, rare and quality affixes',
     [r'(magicprefix|magicsuffix|automagic|rareprefix|raresuffix|qualityitems|uniqueprefix|uniquesuffix|uniqueappellation|uniquetitle)\.txt$']),
    ('itembases', 'Item bases, gems and item types', 'weapons, armor, misc, itemtypes, gems, books',
     [r'(weapons|armor|misc|itemtypes|gems|books|lowqualityitems|belts)\.txt$', r'^hd/items/', r'^hd/global/ui/items/', r'^global/items/']),
    ('drops', 'Drops', 'treasureclassex.txt, itemratio.txt', [r'(treasureclassex|itemratio)\.txt$']),
    ('monsters', 'Monsters', 'monstats, monprop, superuniques and the monster models',
     [r'(monstats|monstats2|monprop|monumod|monai|monequip|monlvl|monpreset|montype|monsounds|monplace|superuniques|uniquemods)\.txt$',
      r'^hd/character/enemy/', r'^hd/character/monsters\.json$', r'^global/monsters/']),
    ('areas', 'Areas, dungeons and objects', 'levels, lvlmaze, lvlprest, lvlsub, lvltypes, lvlwarp, objects and the map tiles',
     [r'(levels|lvlmaze|lvlprest|lvlsub|lvltypes|lvlwarp|objects|objgroup|objpreset|automap|actinfo)\.txt$',
      r'^global/tiles/', r'^hd/env/', r'^hd/objects/']),
    ('skills', 'Skills and skill trees', 'skills.txt, skilldesc.txt and the skill pictures',
     [r'(skills|skilldesc|skillcalc)\.txt$', r'^hd/global/ui/spells/', r'^global/ui/spells/', r'skillstreepanel']),
    ('characters', 'Characters, mercenaries and leveling', 'charstats, experience, hireling, difficultylevels',
     [r'(charstats|experience|hireling|hirelingdesc|difficultylevels|playerclass)\.txt$', r'^hd/character/player/', r'^hd/character/npc/']),
    ('vendors', 'Vendors and gambling', 'npc.txt, storepage.txt', [r'(npc|storepage|gamble)\.txt$']),
    ('interface', 'Interface (layouts, fonts, pictures)', 'global/ui and hd/global/ui', [r'^global/ui/', r'^hd/global/ui/', r'^hd/ui/']),
    ('visuals', 'Effects, models and sounds', 'the remaining hd files and sounds', [r'^hd/', r'^global/sfx/', r'^global/(chars|missiles|overlays)/']),
]
FEATURE_INFO = {f[0]: f for f in FEATURES}


def feature_of(path):
    p = path.lower().replace('\\', '/')
    for fid, _, _, pats in FEATURES:
        if any(_re.search(x, p) for x in pats):
            return fid
    return 'core'


def loader_unit(path):
    """Which switch a file of the mod's d2rloader folder belongs to: a plugin (its DLL, its .mpq /
    .ini, its config\\<name>.toml), a patch, the loader-wide settings, or the shared rest."""
    parts = path.split('/')[1:]  # drop 'd2rloader'
    low = [x.lower() for x in parts]
    stem = lambda name: name.rsplit('.', 1)[0].lower()
    if low[0] == 'plugins' and len(parts) == 2:
        return 'plugin:' + stem(parts[1])
    if low[0] == 'plugins' and len(parts) > 2:
        # a plugin's own folder (ArenaMusic\...), or its archive as a folder (<name>.mpq\data\...)
        return 'plugin:' + (low[1][:-4] if low[1].endswith('.mpq') else low[1])
    if low[0] == 'config' and len(parts) == 2 and low[1] == 'd2rloader.toml':
        return 'loadersettings'
    if low[0] == 'config' and len(parts) == 2 and low[1].endswith('.toml'):
        return 'plugin:' + stem(parts[1])
    if low[0] == 'patches' and len(parts) == 2:
        return 'patch:' + stem(parts[1])
    return 'loadershared'


def switch_id(unit):
    return _re.sub(r'[^A-Za-z0-9]+', '_', unit).strip('_')


# --------------------------------------------------------------------------- files

def find_data_root(mod):
    if (mod / 'data').is_dir():
        return mod / 'data', None
    for p in sorted(mod.iterdir()):
        if p.is_dir() and p.name.lower().endswith('.mpq') and (p / 'modinfo.json').exists() and (p / 'data').is_dir():
            return p / 'data', p / 'modinfo.json'
    raise SystemExit('%s: no data folder or <name>.mpq\\data with modinfo.json' % mod)


def rel(path, root):
    return path.relative_to(root).as_posix()


def is_table(r):
    low = r.lower()
    return low.startswith('global/excel/') and low.endswith('.txt')


def is_strings(r):
    low = r.lower()
    return low.startswith('local/lng/') and low.endswith('.json')


def use_d2rmm_casclib(d2rmm):
    """Points D2R_CASCLIB (read by ModAssets.py / d2r_casc.py) at D2RMM's own tools\\CascLib.dll when it is
    not set yet, so the game archive opens with D2RMM installed anywhere, not only inside the game folder."""
    if os.environ.get('D2R_CASCLIB') or not d2rmm:
        return
    dll = Path(d2rmm) / 'tools' / 'CascLib.dll'
    if dll.is_file():
        os.environ['D2R_CASCLIB'] = str(dll)


def fetch_vanilla(game, cache, paths, python):
    """Asks ModAssets.py for the game's copies; returns {path: Path or None}."""
    from d2r_casc import check_cache
    if check_cache(str(cache), str(game)):
        print('  game was patched since the cache was filled: fetching its files again', file=sys.stderr)
    result = {}
    todo = []
    for p in paths:
        f = cache / p
        if f.exists():
            result[p] = f
        else:
            todo.append(p)
    for i in range(0, len(todo), 400):
        chunk = todo[i:i + 400]
        proc = subprocess.run([python, str(HERE / 'ModAssets.py'), 'fetch', '--game', str(game), '--out', str(cache), '-'],
                              input='\n'.join(chunk), capture_output=True, text=True)
        if proc.returncode != 0:
            raise SystemExit('ModAssets.py failed:\n' + proc.stderr[-2000:])
        sizes = json.loads(proc.stdout.strip().splitlines()[-1])
        for p in chunk:
            result[p] = cache / p if sizes.get(p) is not None else None
        print('  fetched %d/%d game files' % (min(i + 400, len(todo)), len(todo)), file=sys.stderr)
    return result


# --------------------------------------------------------------------------- tables

def read_table(path):
    """-> (headers, rows as lists) or None when it is not UTF-8."""
    try:
        text = path.read_bytes().decode('utf-8-sig')
    except UnicodeDecodeError:
        return None
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    if not lines:
        return [], []
    headers = lines[0].split('\t')
    rows = []
    for line in lines[1:]:
        cells = line.split('\t')
        cells += [''] * (len(headers) - len(cells))
        rows.append(cells[:len(headers)])
    return headers, rows


def row_ids(rows, trim=False):
    """(first cell, how-many-th row with it). trim: spaces around the first cell do not count
    (the game's cubemain has a description with trailing spaces the mod's copy lacks)."""
    seen = {}
    ids = []
    for r in rows:
        k = r[0] if r else ''
        if trim:
            k = k.strip()
        seen[k] = seen.get(k, 0) + 1
        ids.append((k, seen[k]))
    return ids


def renames(vids, mids):
    """Rows the mod renamed in place: a run of game rows replaced by as many mod rows at the same
    spot (Frankenstein turns Poison Dagger into Poison Weapon on the same row). -> {mod row index:
    game row id}. Between two rows both files have (in the same order), the game rows the mod
    lacks and the mod rows the game lacks are paired up when there are as many of each."""
    vpos = {i: n for n, i in enumerate(vids)}
    pairs = {}
    last_v = -1
    gap = []  # mod rows since the last row both have
    for j, i in enumerate(mids + [None]):
        v = vpos.get(i) if i is not None else len(vids)
        if v is None or v <= last_v:
            gap.append(j)
            continue
        lost = list(range(last_v + 1, v))
        new = [k for k in gap if mids[k] not in vpos]
        if lost and len(lost) == len(new):
            for k, g in zip(new, lost):
                pairs[k] = vids[g]
        last_v = v
        gap = []
    return pairs


# Deleted rows that 'keep' mode leaves in place get this column set to 0 (when --deleted disable),
# so they no longer drop, roll or craft. Row numbers stay the same.
DISABLE_COLUMN = {'uniqueitems.txt': 'spawnable', 'setitems.txt': 'spawnable', 'magicprefix.txt': 'spawnable',
                  'magicsuffix.txt': 'spawnable', 'automagic.txt': 'spawnable', 'cubemain.txt': 'enabled',
                  'runes.txt': 'complete'}
CONTENT_MATCH_LIMIT = 40000  # game rows x mod rows of one name; bigger groups keep matching by order


def content_pairs(vh, vrows, vids, mh, mrows, mids):
    """Rows that share a name (the game's 8 'Rainbow Facet' rows) matched by what is in them rather
    than by the how-many-th: -> ({mod row: game row id}, mod rows decided here). Within a name, the
    most alike pairs go first (ties: the same how-many-th). Game rows of such a name left over are
    then paired with the mod's new rows whose name starts with it ('Rainbow Facet Cold') when at
    least 3/4 of the other cells are the same."""
    common = [h for h in mh[1:] if h in vh]
    vi = [vh.index(h) for h in common]
    mi = [mh.index(h) for h in common]
    score = lambda j, g: sum(1 for a, b in zip(mi, vi) if mrows[j][a] == vrows[g][b]) / (len(common) or 1)
    vgroups, mgroups = {}, {}
    for g, (k, _) in enumerate(vids):
        vgroups.setdefault(k, []).append(g)
    for j, (k, _) in enumerate(mids):
        mgroups.setdefault(k, []).append(j)
    pairs, decided, taken = {}, set(), set()

    def assign(cands):
        for _, _, j, g in sorted(cands, key=lambda c: (-c[0], c[1], c[2], c[3])):
            if j not in pairs and g not in taken:
                pairs[j] = vids[g]
                taken.add(g)
    leftover = []
    for k, gs in vgroups.items():
        js = mgroups.get(k, [])
        if len(gs) < 2 and len(js) < 2:
            continue
        if len(gs) * max(len(js), 1) > CONTENT_MATCH_LIMIT:
            continue
        decided.update(js)
        assign([(score(j, g), abs(mids[j][1] - vids[g][1]), j, g) for j in js for g in gs])
        leftover += [g for g in gs if g not in taken]
    if leftover:
        vkeys = set(vgroups)
        new = [j for j in range(len(mids)) if mids[j][0] not in vkeys]
        cands = []
        for g in leftover:
            k = vids[g][0]
            for j in new:
                if k and mids[j][0].startswith(k):
                    s = score(j, g)
                    if s >= 0.75:
                        cands.append((s, abs(j - g), j, g))
        if len(cands) <= CONTENT_MATCH_LIMIT:
            before = set(pairs)
            assign(cands)
            decided.update(set(pairs) - before)
    return pairs, decided


def table_patch(van, mod, trim=False, duplicates='order', disable=None):
    """trim: match first cells with the spaces around them ignored; duplicates: 'content' matches
    rows that share a name by what is in them (content_pairs), 'order' by the how-many-th;
    disable: the column 'keep' mode sets to 0 in the rows the mod deleted (DISABLE_COLUMN)."""
    vh, vrows = van
    mh, mrows = mod
    if len(set(vh)) != len(vh) or len(set(mh)) != len(mh):
        return None, 'duplicate column names'
    vids = row_ids(vrows, trim)
    mids = row_ids(mrows, trim)
    vmap = {i: dict(zip(vh, r)) for i, r in zip(vids, vrows)}
    pre, decided = content_pairs(vh, vrows, vids, mh, mrows, mids) if duplicates == 'content' else ({}, set())
    reserved = set(pre.values())
    renamed = {j: v for j, v in renames(vids, mids).items() if mids[j] not in vmap}
    out_rows = []
    used = set()
    changed = 0
    for j, (i, r) in enumerate(zip(mids, mrows)):
        if j in decided:
            match = pre.get(j)
        elif i in vmap and i not in used and i not in reserved:
            match = i
        elif j in renamed and renamed[j] not in used and renamed[j] not in reserved:
            match = renamed[j]
        else:
            match = None
        if match is not None:
            used.add(match)
            v = vmap[match]
            diff = {h: val for h, val in zip(mh, r) if v.get(h, '') != val}
            if diff:
                changed += 1
            # [3]: the game's values of those cells, so mod.js can tell an earlier mod's change (load order)
            out_rows.append(['=', [match[0], match[1]]] + ([diff, {h: v.get(h, '') for h in diff}] if diff else []))
        else:
            out_rows.append(['+', r])
    deleted = [[k, n] for (k, n) in vmap if (k, n) not in used]
    patch = {
        'headers': mh,
        'droppedColumns': [h for h in vh if h not in mh],
        'rows': out_rows,
        'deleted': deleted,
    }
    if trim:
        patch['trim'] = True
    if disable and disable in vh:
        patch['disable'] = disable
    stats = {'changed': changed, 'added': sum(1 for r in out_rows if r[0] == '+'), 'deleted': len(deleted),
             'renamed': sum(1 for j in renamed if renamed[j] in used),
             'matchedByContent': sum(1 for j in pre if j in decided and mids[j] != pre[j] and pre[j] in used)}
    if patch.get('disable'):
        col = vh.index(disable)
        stats['disabled'] = sum(1 for i, r in zip(vids, vrows) if i not in used and r[col] not in ('', '0'))
    return patch, stats


def apply_table(van, patch):
    """Python twin of applyTable in mod.js, used to check the patch against the mod's file."""
    vh, vrows = van
    rows = [dict(zip(vh, r)) for r in vrows]
    by_id = {i: r for i, r in zip(row_ids(vrows, patch.get('trim')), rows)}
    used = set()
    out = []
    for e in patch['rows']:
        if e[0] == '=':
            i = tuple(e[1])
            r = dict(by_id[i])
            used.add(i)
            r.update(e[2] if len(e) > 2 else {})
            out.append(r)
        else:
            out.append(dict(zip(patch['headers'], e[1])))
    deleted = {tuple(d) for d in patch['deleted']}
    for i, r in by_id.items():
        if i not in used and i not in deleted:
            out.append(r)
    headers = patch['headers'] + [h for h in vh if h not in patch['headers'] and h not in patch['droppedColumns']]
    return headers, [[r.get(h, '') for h in headers] for r in out]


# --------------------------------------------------------------------------- strings

def read_strings(path):
    try:
        data = json.loads(path.read_bytes().decode('utf-8-sig'))
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(data, list) or not all(isinstance(e, dict) and isinstance(e.get('Key'), str) for e in data):
        return None
    return data


def string_ids(entries):
    """(Key, how-many-th entry with that Key): the game's own files repeat some Keys."""
    seen = {}
    ids = []
    for e in entries:
        seen[e['Key']] = seen.get(e['Key'], 0) + 1
        ids.append((e['Key'], seen[e['Key']]))
    return ids


def by_key(entries):
    """Entries grouped by Key, in order (what the check compares)."""
    out = {}
    for e in entries:
        out.setdefault(e['Key'], []).append(e)
    return out


def strings_patch(van, mod):
    """changed: [[Key, n], the mod's entry, the game's entry] (the game's, so mod.js changes only
    the fields the mod changed and can tell an earlier mod's change); addedKnown: the added
    entries whose Key the game has too (the rest are new Keys, which an earlier mod may also add)."""
    vmap = dict(zip(string_ids(van), van))
    changed, added, used = [], [], set()
    for i, e in zip(string_ids(mod), mod):
        if i in vmap:
            used.add(i)
            if vmap[i] != e:
                changed.append([[i[0], i[1]], e, vmap[i]])
        else:
            added.append(e)
    deleted = [[k, n] for (k, n) in vmap if (k, n) not in used]
    vkeys = {k for k, _ in vmap}
    known = [n for n, e in enumerate(added) if e['Key'] in vkeys]
    patch = {'changed': changed, 'added': added, 'deleted': deleted}
    if known:
        patch['addedKnown'] = known
    return patch, {'changed': len(changed), 'added': len(added), 'deleted': len(deleted)}


def apply_strings(van, patch):
    """Python twin of applyStrings in mod.js."""
    changed = {tuple(c[0]): c[1] for c in patch['changed']}
    deleted = {(k, n) for k, n in patch['deleted']}
    out = []
    for i, e in zip(string_ids(van), van):
        if i in deleted:
            continue
        out.append(changed.get(i, e))
    return out + patch['added']


# --------------------------------------------------------------------------- copy list

def compress(files, all_files):
    """Smallest list of files and folders that copies exactly `files` (relative posix paths)."""
    files = set(files)
    tree = {}
    for f in all_files:
        parts = f.split('/')
        for n in range(1, len(parts)):
            tree.setdefault('/'.join(parts[:n]), set()).add(f)
    out = []

    def walk(prefix, members):
        if members and all(m in files for m in members) and prefix:
            out.append((prefix, True))
            return
        children = {}
        for m in members:
            rest = m[len(prefix) + 1:] if prefix else m
            head = rest.split('/', 1)[0]
            children.setdefault(head, []).append(m)
        for head, ms in sorted(children.items()):
            path = prefix + '/' + head if prefix else head
            if len(ms) == 1 and ms[0] == path:
                if path in files:
                    out.append((path, False))
            else:
                walk(path, ms)

    walk('', sorted(all_files))
    return out


def win(p):
    return p.replace('/', '\\')


# --------------------------------------------------------------------------- mod.js

MOD_JS = r'''/**
 * __NAME__ - D2RMM version of the data mod "__ORIG__"__BY__.
 *
 * Generated by ConvertDataMod.py (Ai assisted toolkit, Tools\DiabloII) from the mod's own files,
 * which stay where they are (__DATA_WIN__). Instead of replacing whole files it:
 *  - patches __NTABLES__ tables row by row (rows matched by their first column), so other mods'
 *    changes to the same tables survive and new game patches still come through;
 *  - merges __NSTRINGS__ string files by Key;
 *  - copies the remaining files (__NCOPY__ files or folders), and the D2RLoader plugins, config
 *    and patches into D2RMM's d2rloader output.
 * Rows (see ROWS below): in 'keep' mode it can sit anywhere in the mod list (mods made for it
 * go below it); in 'rebuild' mode put it at the TOP. Rerun the converter instead of editing this file.
 */

const MOD_ID = '__ID__';
const DATA = '__DATA__';
const PATCHES = 'd2rmm\\patches';
const SCRATCH = 'd2rmm-convert\\' + MOD_ID + '.json';
// How rows are merged with the tables earlier mods left:
//  'keep'    every row stays where it is (row numbers are what saves, plugins and other tables
//            point at), rows the mod deleted stay too (switched off where the patch names a
//            column for it: spawnable, enabled, complete), the mod's new rows go at the end, and
//            numbers in the mod's cells that point at rows of a patched table are moved with them;
//  'rebuild' the table takes the mod's own row order (the data mod exactly), rows earlier mods
//            added go after it, rows the mod deleted go.
// Load order (mod settings > Load order; the converter's choices when not set there):
//  ROWS   'keep' / 'rebuild' as above;
//  CELLS  a cell or string an earlier mod changed that this mod changes too: 'mod' this mod's
//         value, 'earlier' the earlier mod's value (this mod then only fills what nobody touched);
//  FILES  a file an earlier mod already put in the output: 'overwrite' with this mod's, 'keep' it.
const SETTING = (id, allowed, fallback) => {
  const v = typeof config === 'object' && config ? config[id] : undefined;
  return allowed.includes(v) ? v : fallback;
};
const ROWS = SETTING('loadorderRows', ['keep', 'rebuild'], '__ROWS__');
const CELLS = SETTING('loadorderCells', ['mod', 'earlier'], '__CELLS__');
const FILES = SETTING('loadorderFiles', ['overwrite', 'keep'], '__FILES__');
const CLASHES = {}; // path -> [count, first few names]

/* @generated-data-begin */
/* @generated-data-end */

function readPatch(path) {
  D2RMM.copyFile(PATCHES + '\\' + path + '.json', SCRATCH, true);
  return D2RMM.readJson(SCRATCH);
}

function rowId(key, n) {
  return n + '\u0001' + key;
}
// A row's name: its first cell (without the spaces around it when the patch says trim).
function keyOf(row, key, patch) {
  const k = row[key] == null ? '' : String(row[key]);
  return patch.trim ? k.trim() : k;
}

// My mod list (mod settings > My mod list, every rule off by default): fixes for particular mods.
// A ticked rule acts only when one of its mods (`when`) is enabled in D2RMM, and with `above` only
// when that mod comes before this one: `earlier` paths keep the cells/strings mods above changed,
// `skip` (patterns on the paths below) leaves files/tables out, `switches` turns switches off.
// An `option` rule (mod settings > Options) is a part of this mod: on by default, its actions apply
// when it is switched OFF, whatever the mod list. `props`: item property codes taken off items.
const RULES_ON = (() => {
  const list = typeof D2RMM.getModList === 'function' ? D2RMM.getModList() || [] : [];
  const me = list.findIndex((m) => m.id === MOD_ID);
  const at = (id) => list.findIndex((m) => m.id === id || m.name === id);
  return MODLIST.filter((r) => {
    const v = typeof config === 'object' && config ? config[r.id] : undefined;
    if (r.option) {
      const off = v === false || v === 'false';
      console.log(MOD_ID + ': Options > ' + r.name + ': ' + (off ? 'off' : 'on'));
      return off;
    }
    if (v !== true && v !== 'true') return false;
    const hits = r.when.filter((id) => {
      const i = at(id);
      return i >= 0 && (!r.above || me < 0 || i < me);
    });
    console.log(MOD_ID + ': My mod list > ' + r.name + ': ' + (hits.length ? 'used (' + hits.join(', ') + ')'
      : 'not used, ' + r.when.join(' / ') + ' is not ' + (r.above ? 'above this mod' : 'in the mod list')));
    return hits.length > 0;
  });
})();
const SKIP = RULES_ON.flatMap((r) => r.skip || []).map((p) => new RegExp(p, 'i'));
const EARLIER = new Set(RULES_ON.flatMap((r) => r.earlier || []).map((p) => p.toLowerCase()));
const LIST_OFF = new Set(RULES_ON.flatMap((r) => r.switches || []));
const PROPS_OFF = new Set(RULES_ON.flatMap((r) => r.props || []).map((p) => p.toLowerCase()));
const skipped = (path) => SKIP.some((re) => re.test(path));
// 'earlier' for paths a ticked rule names, else the Conflicts setting.
const cellsOf = (path) => (EARLIER.has(path.toLowerCase()) ? 'earlier' : CELLS);

function clash(path, what) {
  const c = (CLASHES[path] = CLASHES[path] || [0, []]);
  c[0]++;
  if (c[1].length < 3) c[1].push(what);
}
// The cells of `diff` to write into `row`. `before` (the game's values of those cells) tells which
// ones an earlier mod changed too; patches made before it existed have none: all cells go in.
function mergeCells(path, row, diff, before, name) {
  if (!before) return diff;
  const out = {};
  Object.keys(diff).forEach((h) => {
    const cur = row[h] == null ? '' : String(row[h]);
    if (h in before && cur !== before[h] && cur !== diff[h]) {
      clash(path, name + ' ' + h);
      if (cellsOf(path) === 'earlier') return;
    }
    out[h] = diff[h];
  });
  return out;
}

function applyTable(path, patch) {
  const table = D2RMM.readTsv(path, { removeCarriageReturns: true });
  const key = table.headers[0];
  const seen = {};
  const byId = new Map();
  const order = [];
  table.rows.forEach((row) => {
    const k = keyOf(row, key, patch);
    seen[k] = (seen[k] || 0) + 1;
    const id = rowId(k, seen[k]);
    byId.set(id, row);
    order.push(id);
  });
  const used = new Set();
  const rows = [];
  let missing = 0;
  patch.rows.forEach((entry) => {
    if (entry[0] === '=') {
      const id = rowId(entry[1][0], entry[1][1]);
      const row = byId.get(id);
      if (!row) {
        missing++;
        return;
      }
      used.add(id);
      rows.push(Object.assign({}, row, mergeCells(path, row, entry[2] || {}, entry[3], entry[1][0])));
    } else {
      const row = {};
      patch.headers.forEach((h, i) => (row[h] = entry[1][i] == null ? '' : entry[1][i]));
      rows.push(row);
    }
  });
  const deleted = new Set(patch.deleted.map((d) => rowId(d[0], d[1])));
  order.forEach((id) => {
    if (!used.has(id) && !deleted.has(id)) rows.push(byId.get(id)); // rows earlier mods added
  });
  const headers = patch.headers.concat(
    table.headers.filter((h) => !patch.headers.includes(h) && !patch.droppedColumns.includes(h))
  );
  if (missing) console.warn(MOD_ID + ': ' + path + ': ' + missing + ' row(s) the mod changes are gone (removed by an earlier mod?)');
  D2RMM.writeTsv(path, { headers, rows });
}

// ---- 'keep' mode -------------------------------------------------------------------------
// Where each row of the mod's own table ended up: INDEX[table path][row in the mod's file].
const INDEX = {};
// Cells that hold a row number of another table: [table name pattern, column pattern, target table].
// A level's number is its row in levels.txt (its Id column, which Vis/Depend/lvlmaze/lvlprest repeat),
// a warp's number its row in lvlwarp.txt: when an earlier mod (Reimagined, Frankenstein...) already
// added levels, the mod's new levels move behind them and every one of these numbers moves with them.
const ROW_REFS = [
  [/^(weapons|misc|armor)\.txt$/i, /^missiletype$/, 'missiles.txt'],
  [/^levels\.txt$/i, /^(Id|Depend|Vis[0-7])$/, 'levels.txt'],
  [/^levels\.txt$/i, /^Warp[0-7]$/, 'lvlwarp.txt'],
  [/^lvlwarp\.txt$/i, /^Id$/, 'lvlwarp.txt'],
  [/^lvlmaze\.txt$/i, /^Level$/, 'levels.txt'],
  [/^lvlprest\.txt$/i, /^LevelId$/, 'levels.txt'],
];
// Item properties whose parameter is a skill (by name or by row number).
const SKILL_PROPS = new Set(['skill', 'oskill', 'aura', 'hit-skill', 'gethit-skill', 'att-skill', 'kill-skill',
  'death-skill', 'levelup-skill', 'charged', 'charge-noconsume']);
const PARAM_OF = [
  [/^prop(\d+)$/, (m) => 'par' + m[1]], [/^aprop(\d+[ab])$/, (m) => 'apar' + m[1]],
  [/^PCode(\d+[ab])$/, (m) => 'PParam' + m[1]], [/^FCode(\d+)$/, (m) => 'FParam' + m[1]],
  [/^T1Code(\d+)$/, (m) => 'T1Param' + m[1]], [/^mod(\d+)code$/, (m) => 'mod' + m[1] + 'param'],
  [/^((?:[bc] )?mod \d+)$/, (m) => m[1] + ' param'], [/^(\w+Mod\d)Code$/, (m) => m[1] + 'Param'],
];
const TARGET_FIRST = ['missiles.txt', 'skills.txt', 'states.txt', 'itemstatcost.txt', 'monstats.txt', 'lvlwarp.txt', 'levels.txt'];

function folderOf(path) {
  return path.slice(0, path.lastIndexOf('\\') + 1);
}
// Tables whose rows are numbered by an Id column that skips separator rows (levels.txt has an
// "Expansion" row without an Id: from there on a level's Id is its row minus one, and lvlwarp.txt
// repeats some Ids), so a row number is no use: every Id above the game's own top one moves by what
// earlier mods added; IDS[table path] = { own: the game's top Id, delta: how far Ids above it move }.
const ID_TABLES = { 'levels.txt': 'Id', 'lvlwarp.txt': 'Id' };
const IDS = {};
function moved(target, value) {
  if (!/^\d+$/.test(String(value))) return value;
  if (IDS[target]) return Number(value) > IDS[target].own ? String(Number(value) + IDS[target].delta) : value;
  const map = INDEX[target];
  const to = map ? map[Number(value)] : undefined;
  return to === undefined || to < 0 ? value : String(to);
}
// Moves the numbers in `cells` (the mod's values for one row) to where their rows ended up.
function remap(path, cells, full) {
  const dir = folderOf(path);
  const name = path.slice(dir.length);
  ROW_REFS.forEach(([re, col, target]) => {
    if (!re.test(name)) return;
    Object.keys(cells).forEach((h) => {
      if (col.test(h)) cells[h] = moved(dir + target, cells[h]);
    });
  });
  Object.keys(full).forEach((code) => {
    const rule = PARAM_OF.find(([re]) => re.test(code));
    if (!rule) return;
    const param = rule[1](code.match(rule[0]));
    if (cells[param] === undefined || !SKILL_PROPS.has(String(full[code]).toLowerCase())) return;
    cells[param] = moved(dir + 'skills.txt', cells[param]);
  });
  return cells;
}

function applyTableKeep(path, patch) {
  const table = D2RMM.readTsv(path, { removeCarriageReturns: true });
  const key = table.headers[0];
  const seen = {};
  const at = new Map();
  table.rows.forEach((row, i) => {
    const k = keyOf(row, key, patch);
    seen[k] = (seen[k] || 0) + 1;
    at.set(rowId(k, seen[k]), i);
  });
  const rows = table.rows;
  // Rows the mod deleted stay (their numbers are what others point at) but are switched off.
  if (patch.disable) {
    patch.deleted.forEach((d) => {
      const i = at.get(rowId(d[0], d[1]));
      const v = i === undefined ? '' : rows[i][patch.disable];
      if (v != null && v !== '' && v !== '0') rows[i][patch.disable] = '0';
    });
  }
  // Where every row of the mod's file ends up, before any cell moves: a row can point at a later
  // row of its own table (a level's Vis numbers), and new rows go behind what earlier mods added.
  const where = [];
  let missing = 0;
  let next = rows.length;
  patch.rows.forEach((entry) => {
    if (entry[0] === '=') {
      const i = at.get(rowId(entry[1][0], entry[1][1]));
      if (i === undefined) missing++;
      where.push(i === undefined ? -1 : i);
    } else {
      where.push(next++);
    }
  });
  INDEX[path] = where;
  const idCol = ID_TABLES[path.slice(path.lastIndexOf('\\') + 1).toLowerCase()];
  if (idCol) {
    const num = (v) => (v != null && /^\d+$/.test(String(v).trim()) ? Number(String(v).trim()) : -1);
    // The mod's new Ids follow its last old one, so they all move by what earlier mods added.
    let top = -1; // highest Id in the table now
    rows.forEach((row) => (top = Math.max(top, num(row[idCol]))));
    let own = -1; // highest Id among the rows the mod already finds in the table
    patch.rows.forEach((entry, n) => {
      if (entry[0] === '=' && where[n] >= 0) own = Math.max(own, num(rows[where[n]][idCol]));
    });
    // Ids up to the game's own top stay (the mod may reuse one of them), every one above moves.
    IDS[path] = { own, delta: top - own };
  }
  patch.rows.forEach((entry, n) => {
    if (entry[0] === '=') {
      const i = where[n];
      if (i < 0) return;
      const diff = mergeCells(path, rows[i], Object.assign({}, entry[2] || {}), entry[3], entry[1][0]);
      Object.assign(rows[i], remap(path, diff, Object.assign({}, rows[i], diff)));
    } else {
      const row = {};
      patch.headers.forEach((h, i) => (row[h] = entry[1][i] == null ? '' : entry[1][i]));
      rows.push(remap(path, row, row));
    }
  });
  const headers = table.headers.concat(patch.headers.filter((h) => !table.headers.includes(h)));
  if (missing) console.warn(MOD_ID + ': ' + path + ': ' + missing + ' row(s) the mod changes are gone (removed by an earlier mod?)');
  D2RMM.writeTsv(path, { headers, rows });
}

// Only the fields the mod changed (a language, say) go in, so an earlier mod's other changes to
// the entry stay. `before`: the game's entry; patches made before it existed replace the entry.
function mergeEntry(path, cur, mine, before) {
  if (!before) return mine;
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const out = Object.assign({}, cur);
  new Set(Object.keys(mine).concat(Object.keys(before))).forEach((f) => {
    if (same(mine[f], before[f])) return; // the mod leaves this field alone
    if (!same(cur[f], before[f]) && !same(cur[f], mine[f])) {
      clash(path, cur.Key + ' ' + f);
      if (cellsOf(path) === 'earlier') return;
    }
    if (f in mine) out[f] = mine[f];
    else delete out[f];
  });
  return out;
}

// Entries matched by Key and the how-many-th entry with that Key (the game repeats some Keys).
function applyStrings(path, patch) {
  const changed = new Map(patch.changed.map((c) => [rowId(c[0][0], c[0][1]), c]));
  const deleted = new Set(patch.deleted.map((d) => rowId(d[0], d[1])));
  const seen = {};
  const list = [];
  D2RMM.readJson(path).forEach((e) => {
    seen[e.Key] = (seen[e.Key] || 0) + 1;
    const id = rowId(e.Key, seen[e.Key]);
    if (deleted.has(id)) return;
    const c = changed.get(id);
    list.push(c ? mergeEntry(path, e, c[1], c[2]) : e);
  });
  // A new Key an earlier mod added as well: one entry, this mod's or the earlier one (CELLS).
  const at = new Map();
  list.forEach((e, i) => at.has(e.Key) || at.set(e.Key, i));
  const known = new Set(patch.addedKnown || []);
  patch.added.forEach((e, n) => {
    const i = known.has(n) ? undefined : at.get(e.Key);
    if (i === undefined) {
      list.push(e);
      return;
    }
    clash(path, e.Key + ' (added by both)');
    if (cellsOf(path) === 'mod') list[i] = Object.assign({}, e, list[i].id !== undefined ? { id: list[i].id } : {});
  });
  D2RMM.writeJson(path, list);
}

// Item property columns: [code column, (match) -> its param, min and max columns].
const PROP_COLS = [
  [/^prop(\d+)$/, (m) => ['par', 'min', 'max'].map((s) => s + m[1])],
  [/^aprop(\d+[ab])$/, (m) => ['apar', 'amin', 'amax'].map((s) => s + m[1])],
  [/^PCode(\d+[ab])$/, (m) => ['PParam', 'PMin', 'PMax'].map((s) => s + m[1])],
  [/^FCode(\d+)$/, (m) => ['FParam', 'FMin', 'FMax'].map((s) => s + m[1])],
  [/^T1Code(\d+)$/, (m) => ['T1Param', 'T1Min', 'T1Max'].map((s) => s + m[1])],
  [/^mod(\d+)code$/, (m) => ['param', 'min', 'max'].map((s) => 'mod' + m[1] + s)],
  [/^((?:[bc] )?mod \d+)$/, (m) => ['param', 'min', 'max', 'chance'].map((s) => m[1] + ' ' + s)],
  [/^(\w+Mod\d)Code$/, (m) => ['Param', 'Min', 'Max'].map((s) => m[1] + s)],
];
// Takes the property `codes` off every row of a table; an affix left with no property stops spawning.
function stripProps(path, codes) {
  const table = D2RMM.readTsv(path, { removeCarriageReturns: true });
  const cols = table.headers
    .map((h) => {
      const r = PROP_COLS.find(([re]) => re.test(h));
      return r ? [h, r[1](h.match(r[0]))] : null;
    })
    .filter(Boolean);
  if (!cols.length) return 0;
  const affix = /^(magicprefix|magicsuffix|automagic)\.txt$/i.test(path.slice(path.lastIndexOf('\\') + 1));
  let n = 0;
  table.rows.forEach((row) => {
    let hit = false;
    cols.forEach(([c, rest]) => {
      if (!codes.has(String(row[c] == null ? '' : row[c]).trim().toLowerCase())) return;
      [c].concat(rest).forEach((h) => {
        if (h in row) row[h] = '';
      });
      hit = true;
    });
    if (!hit) return;
    n++;
    // Close the gap: the properties after a removed one move up (numbered slots; set bonus slots
    // like aprop1a stay, their number is the bonus).
    const slot = /\d+(?=\D*$)/; // the last number: T1Code3 -> 3
    const families = {};
    cols.forEach((c) => {
      if (/\d[ab]$/.test(c[0])) return;
      const f = c[0].replace(slot, '#');
      (families[f] = families[f] || []).push(c);
    });
    Object.values(families).forEach((fam) => {
      fam.sort((a, b) => Number(a[0].match(slot)[0]) - Number(b[0].match(slot)[0]));
      const filled = fam.filter(([c]) => row[c]).map(([c, rest]) => [c].concat(rest).map((h) => (h in row ? row[h] : '')));
      fam.forEach(([c, rest], i) => [c].concat(rest).forEach((h, j) => {
        if (h in row) row[h] = i < filled.length ? filled[i][j] : '';
      }));
    });
    if (affix && cols.every(([c]) => !row[c]) && row.spawnable != null && row.spawnable !== '') row.spawnable = '0';
  });
  if (n) D2RMM.writeTsv(path, table);
  return n;
}

// Every entry names the switch (mod settings) it belongs to; 'core' is always installed.
// A feature that uses another feature's new rows (NEEDS) goes off with it, and one that always-on
// tables use (FORCED) cannot be switched off, so no row is left naming a row that is not there.
const SWITCHED_OFF = (id) => LIST_OFF.has(id) || config[id] === false || config[id] === 'false';
const OFF_FEATURES = new Set();
const WHY_OFF = {};
(() => {
  const ids = new Set(COPY.map((e) => e[2]).concat(TABLES.map((e) => e[1]), STRINGS.map((e) => e[1]),
    Object.keys(NEEDS), [].concat(...Object.values(NEEDS))));
  ids.forEach((id) => {
    if (id && id !== 'core' && SWITCHED_OFF(id)) {
      if (FORCED.includes(id)) console.warn(MOD_ID + ': ' + id + ' cannot be switched off: ' + FORCED_WHY[id] + '. Left on.');
      else OFF_FEATURES.add(id);
    }
  });
  for (let grew = true; grew; ) {
    grew = false;
    Object.keys(NEEDS).forEach((id) => {
      const gone = NEEDS[id].filter((n) => OFF_FEATURES.has(n));
      if (gone.length && !OFF_FEATURES.has(id) && !FORCED.includes(id)) {
        OFF_FEATURES.add(id);
        WHY_OFF[id] = gone;
        grew = true;
      }
    });
  }
  Object.keys(WHY_OFF).forEach((id) =>
    console.log(MOD_ID + ': ' + id + ' is switched off too: it uses new rows of ' + WHY_OFF[id].join(', ') + ' (switched off).'));
})();
const ON = (id) => !id || id === 'core' || FORCED.includes(id) || (!OFF_FEATURES.has(id) && !SWITCHED_OFF(id));
const COPY_ON = COPY.filter((e) => ON(e[2]) && !skipped(e[0]));
const LOADER_ON = LOADER.filter((e) => ON(e[2]) && !skipped(e[0]));
const TABLES_ON = TABLES.filter((e) => ON(e[1]) && !skipped(e[0])).map((e) => e[0]);
const STRINGS_ON = STRINGS.filter((e) => ON(e[1]) && !skipped(e[0])).map((e) => e[0]);

// 'rebuild' puts the mod's own row order first, which only holds when no mod comes before it.
if (ROWS === 'rebuild' && typeof D2RMM.getModList === 'function') {
  const list = D2RMM.getModList() || [];
  const me = list.findIndex((m) => m.id === MOD_ID);
  if (me > 0) console.warn(MOD_ID + ': rows are set to "rebuild" but ' + me + ' mod(s) come before it (' +
    list.slice(0, me).map((m) => m.name || m.id).join(', ') + '): move it to the TOP, or set Load order > Rows to "keep".');
}

// Whole files first, then the patches (a copied folder never holds a patched file).
COPY_ON.forEach(([src]) => D2RMM.copyFile(DATA + '\\' + src, src, FILES === 'overwrite'));
LOADER_ON.forEach(([src]) => D2RMM.copyFile(src, '..\\..\\' + src, true));
if (ROWS === 'keep') {
  // Tables that others point into by row number first, so their new row numbers are known.
  const rank = (p) => {
    const i = TARGET_FIRST.indexOf(p.slice(p.lastIndexOf('\\') + 1).toLowerCase());
    return i < 0 ? TARGET_FIRST.length : i;
  };
  TABLES_ON.slice().sort((a, b) => rank(a) - rank(b)).forEach((path) => applyTableKeep(path, readPatch(path)));
} else {
  TABLES_ON.forEach((path) => applyTable(path, readPatch(path)));
}
STRINGS_ON.forEach((path) => applyStrings(path, readPatch(path)));
if (PROPS_OFF.size) {
  const n = TABLES_ON.reduce((sum, path) => sum + stripProps(path, PROPS_OFF), 0);
  console.log(MOD_ID + ': took ' + [...PROPS_OFF].join(', ') + ' off ' + n + ' row(s) (Options).');
}
D2RMM.writeTxt(SCRATCH, '');

const clashed = Object.keys(CLASHES);
if (clashed.length) {
  console.warn(MOD_ID + ': cells/strings an earlier mod changed as well (' +
    (CELLS === 'mod' ? 'this mod\'s values used' : 'the earlier mod\'s values kept') + ', Load order > Conflicts): ' +
    clashed.map((p) => p.slice(p.lastIndexOf('\\') + 1) + ' ' + CLASHES[p][0] + ' (' + CLASHES[p][1].join('; ') + ')').join(', '));
}
const off = [...new Set(COPY.concat(LOADER).map((e) => e[2]).concat(TABLES.map((e) => e[1])))].filter((id) => !ON(id));
console.log(
  MOD_ID + ': ' + TABLES_ON.length + ' tables patched, ' + STRINGS_ON.length + ' string files merged, ' +
    COPY_ON.length + ' files/folders copied, ' + LOADER_ON.length + ' D2RLoader files/folders copied' +
    (off.length ? '; switched off: ' + off.join(', ') : '') + '.'
);
'''


def js_list(name, items, comment):
    body = ',\n'.join('  ' + json.dumps(i, ensure_ascii=False) for i in items)
    return '// %s\nconst %s = [\n%s%s];\n' % (comment, name, body, ',\n' if items else '')


# --------------------------------------------------------------------------- switches

def old_report(mod):
    try:
        return json.loads((mod / 'd2rmm' / 'convert.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def source_built(folders):
    """Plugins built from source on this machine: {dll name without .dll, lower case: folder}.
    A folder is a source workspace with packages/*.zip (the builds) and upstream/plugins/<name>
    (the sources), like <game>/mods/WildHealer-D2R-Tools. The user asked (2026-11-14) to leave such
    plugins out of conversions and point to the source build: prebuilt copies in downloads have
    been found infected. An optional source-built-aliases.json in the folder maps other DLL names
    a download uses for the same plugin ({"d2rl-charm-inv": "wild-healers-charm-inventory"})."""
    import zipfile
    out = {}
    for folder in folders:
        folder = Path(folder)
        for z in sorted((folder / 'packages').glob('*.zip')):
            try:
                names = zipfile.ZipFile(z).namelist()
            except zipfile.BadZipFile:
                continue
            for n in names:
                if n.lower().endswith('.dll'):
                    out[n.rsplit('/', 1)[-1][:-4].lower()] = str(folder)
        for d in (folder / 'upstream' / 'plugins').glob('*'):
            if d.is_dir():
                out.setdefault(d.name.lower(), str(folder))
                out.setdefault('d2rl-' + d.name.lower(), str(folder))
        aliases = folder / 'source-built-aliases.json'
        if aliases.exists():
            for k, v in json.loads(aliases.read_text(encoding='utf-8-sig')).items():
                if not k.startswith('_'):
                    out[k.lower()] = str(folder)
    return out


def source_folders(game):
    """Source workspaces next to the game's mods: <game>/mods/*/ with packages/ and upstream/plugins/."""
    mods = Path(game) / 'mods'
    return [d for d in sorted(mods.iterdir()) if (d / 'packages').is_dir() and (d / 'upstream' / 'plugins').is_dir()] if mods.is_dir() else []


def installed_targets(d2rmm_loader, mod_id):
    """Files D2RMM's own plugin packages already put into the d2rloader output (other than the
    ones this conversion made): {target path lower case: (package, sha256)}."""
    out = {}
    if not d2rmm_loader.is_dir():
        return out
    for pkg in d2rmm_loader.iterdir():
        manifest = pkg / 'manifest.json'
        if not manifest.is_file() or pkg.name.lower().startswith(mod_id.lower() + '-'):
            continue
        try:
            files = json.loads(manifest.read_text(encoding='utf-8-sig')).get('files', [])
        except ValueError:
            continue
        for f in files:
            if f.get('targetRoot') == 'd2rloader' and f.get('targetPath'):
                out[f['targetPath'].replace('/', '\\').lower()] = (pkg.name, f.get('sha256'))
    return out


def load_order_ui(rows='keep', conflicts='mod', files='overwrite'):
    """The 'Load order' settings (mod.js reads them as loadorderRows / Cells / Files); the defaults
    are what the conversion was made with."""
    rebuilt = rows == 'rebuild'
    return {'id': 'loadorder', 'type': 'section', 'name': 'Load order', 'defaultExpanded': False, 'children': [
        {'id': 'loadorderRows', 'type': 'select', 'name': 'Rows', 'defaultValue': rows,
         'description': 'Keep: every table keeps its row order and this mod\'s new rows go at the end, so it can sit '
                        'anywhere in the list (mods made for it go below it); rows it deleted stay, switched off where '
                        'possible. Rebuild: the tables take this mod\'s own row order, exactly as the original; put it at '
                        'the TOP (the install log warns when it is not). ' + (
                            'Converted with Rebuild: Keep cannot move every row number this mod relies on, so use it only '
                            'when Rebuild clashes with mods above it.' if rebuilt else
                            'Converted with Keep (default).'),
         'options': [{'label': 'Keep (works anywhere in the list)', 'value': 'keep'},
                     {'label': 'Rebuild (top of the list)', 'value': 'rebuild'}]},
        {'id': 'loadorderCells', 'type': 'select', 'name': 'Conflicts with mods above', 'defaultValue': conflicts,
         'description': 'A table cell or string that a mod above this one already changed, and this mod changes too. '
                        'This mod wins: its value is used. Mods above win: their value stays and this mod only changes '
                        'what nobody else touched. Either way the install log lists the clashes.',
         'options': [{'label': 'This mod wins', 'value': 'mod'}, {'label': 'Mods above win', 'value': 'earlier'}]},
        {'id': 'loadorderFiles', 'type': 'select', 'name': 'Files a mod above already put in', 'defaultValue': files,
         'description': 'Other files (textures, models, layouts, sounds) that a mod above this one already installed. '
                        'Overwrite: this mod\'s copy replaces it. Keep: the other mod\'s copy stays.',
         'options': [{'label': 'Overwrite with this mod\'s', 'value': 'overwrite'},
                     {'label': 'Keep the other mod\'s', 'value': 'keep'}]},
    ]}


def modlist_rules(path, mod_id, loader, tables, strings, copy_list, data=None):
    """The 'My mod list' rules (a JSON list, see modlist-rules.example.json) that fit this
    conversion: a rule's `mods` (converted mod ids; none = all) must name it, and only the parts
    that touch something it has are kept (skip patterns matching a path, switches it has, earlier
    paths it patches, `props` codes found in its tables under `data`); a rule left with nothing is
    dropped. A rule with `option` needs no `when`: it is a part of the mod, on by default, that
    applies its actions when switched off. Returns (rules, file used or None)."""
    path = Path(path) if path else None
    if not path or not path.is_file():
        return [], None
    raw = json.loads(path.read_text(encoding='utf-8-sig'))
    raw = raw.get('rules', []) if isinstance(raw, dict) else raw
    paths = [win(p) for p, _, _ in copy_list] + [p for p, _, _ in loader] + [win(t) for t in tables] + [win(s) for s in strings]
    paths = [p.replace('/', '\\') for p in paths]
    switches = {u for _, _, u in loader} | {f for _, _, f in copy_list} | {feature_of(t) for t in tables}
    patched = {win(t).replace('/', '\\').lower() for t in list(tables) + list(strings)}
    out = []
    for r in raw:
        option = isinstance(r, dict) and bool(r.get('option'))
        if not isinstance(r, dict) or not r.get('id') or not (r.get('when') or option):
            continue
        if r.get('mods') and mod_id not in r['mods']:
            continue
        skip = [p for p in r.get('skip', []) if any(_re.search(p, x, _re.I) for x in paths)]
        sw = [s for s in r.get('switches', []) if s in switches]
        earlier = [p for p in r.get('earlier', []) if p.replace('/', '\\').lower() in patched]
        props = [c for c in r.get('props', []) if data and any(
            _re.search(r'(^|\t)' + _re.escape(c) + r'(\t|$)', (Path(data) / t).read_text(encoding='utf-8', errors='replace'),
                       _re.I | _re.M)
            for t in tables if (Path(data) / t).is_file())]
        if not (skip or sw or earlier or props):
            continue
        rule = {'id': r['id'], 'name': r.get('name', r['id']), 'when': list(r.get('when') or []),
                'above': bool(r.get('above'))}
        if option:
            rule['option'] = True
        if props:
            rule['props'] = props
        if skip:
            rule['skip'] = skip
        if sw:
            rule['switches'] = sw
        if earlier:
            rule['earlier'] = [p.replace('/', '\\') for p in earlier]
        rule['description'] = r.get('description', '')
        out.append(rule)
    return out, str(path)


def options_ui(rules):
    """The 'Options' settings: a checkbox per option rule, on by default; off applies its actions."""
    children = []
    for r in rules:
        if not r.get('option'):
            continue
        what = []
        if r.get('props'):
            what.append('takes %s off every item (affixes with nothing else left stop spawning)' % ', '.join(r['props']))
        if r.get('switches'):
            what.append('turns off ' + ', '.join(r['switches']))
        if r.get('skip'):
            what.append('leaves out %d file/table pattern(s)' % len(r['skip']))
        if r.get('earlier'):
            what.append('keeps the values of the mods above in ' + ', '.join(p.rsplit('\\', 1)[-1] for p in r['earlier']))
        children.append({'id': r['id'], 'type': 'checkbox', 'name': r['name'], 'defaultValue': True,
                         'description': (r['description'] + ' ' if r['description'] else '') +
                         'Off: it %s. The install log says whether it is on.' % '; '.join(what)})
    return {'id': 'options', 'type': 'section', 'name': 'Options', 'defaultExpanded': True,
            'description': 'Parts of this mod you can switch off, all on by default (as the mod comes).',
            'children': children} if children else None


def modlist_ui(rules):
    """The 'My mod list' settings: a checkbox per rule, all off by default."""
    children = []
    for r in rules:
        if r.get('option'):
            continue
        cond = ('%s is enabled ABOVE this mod' if r['above'] else '%s is enabled') % ' or '.join(r['when'])
        what = []
        if r.get('earlier'):
            what.append('keeps the values of the mods above in ' + ', '.join(p.rsplit('\\', 1)[-1] for p in r['earlier']))
        if r.get('switches'):
            what.append('turns off ' + ', '.join(r['switches']))
        if r.get('skip'):
            what.append('leaves out %d file/table pattern(s)' % len(r['skip']))
        children.append({'id': r['id'], 'type': 'checkbox', 'name': r['name'], 'defaultValue': False,
                         'description': (r['description'] + ' ' if r['description'] else '') +
                         'Acts only when %s; then it %s. The install log says whether it was used.' % (cond, '; '.join(what))})
    return {'id': 'modlist', 'type': 'section', 'name': 'My mod list', 'defaultExpanded': False,
            'description': 'Fixes for particular mods in this mod list, all off by default. Tick the ones for mods you use.',
            'children': children} if children else None


# What a table's cells name, by table: (table pattern, column pattern, targets), a target being
# (table, id column) in the same folder. A cell is a reference only in such a column, and it is only
# looked up among the NEW rows of those target tables, so a word that happens to equal some other
# table's row name (hp, cold, red...) is not taken for one.
_ITEMS = (('weapons.txt', 'code'), ('armor.txt', 'code'), ('misc.txt', 'code'), ('gems.txt', 'code'), ('itemtypes.txt', 'Code'))
_UNIQ = (('uniqueitems.txt', 'index'), ('setitems.txt', 'index'))
_SKILL = (('skills.txt', 'skill'),)
_MON = (('monstats.txt', 'Id'),)
_PROP_ROWS = r'^(uniqueitems|setitems|sets|runes|magicprefix|magicsuffix|automagic|monprop)\.txt$'
LINK_REFS = [
    (r'^cubemain\.txt$', r'^(input \d+|output( [bc])?)$', _ITEMS + _UNIQ),
    (r'^treasureclassex\.txt$', r'^Item\d+$', _ITEMS + (('treasureclassex.txt', 'Treasure Class'),)),
    (r'^treasureclassex\.txt$', r'^Treasure Class$', ()),
    (r'^monstats\.txt$', r'^Skill\d+$', _SKILL),
    (r'^monstats\.txt$', r'^TreasureClass.*$', (('treasureclassex.txt', 'Treasure Class'),)),
    (r'^monstats\.txt$', r'^(MonProp|Mon Prop)$', (('monprop.txt', 'Id'),)),
    (r'^monstats\.txt$', r'^(rightArmItemType|leftArmItemType|BaseId|NextInClass)$', _ITEMS + _MON),
    (r'^levels\.txt$', r'^(mon|umon|nmon|cmon)\d+$', _MON),
    (r'^hireling\.txt$', r'^Skill\d+$', _SKILL),
    (r'^charstats\.txt$', r'^(StartSkill|Skill \d+)$', _SKILL),
    (r'^charstats\.txt$', r'^item\d+$', _ITEMS),
    (r'^runes\.txt$', r'^(Rune\d+|itype\d+|etype\d+)$', _ITEMS),
    (r'^(uniqueitems|setitems)\.txt$', r'^code$', _ITEMS),
    (r'^(magicprefix|magicsuffix|automagic)\.txt$', r'^(itype|etype)\d+$', _ITEMS),
    (r'^(weapons|armor|misc)\.txt$', r'^(type|type2)$', (('itemtypes.txt', 'Code'),)),
    (r'^itemtypes\.txt$', r'^(Equiv1|Equiv2)$', (('itemtypes.txt', 'Code'),)),
    (r'^skills\.txt$', r'^summon$', _MON),
    (r'^missiles\.txt$', r'^Skill$', _SKILL),
]
MIN_LINKS = 1


def _link_tokens(cell):
    """The names in a cell: the whole cell, and its comma / semicolon / bar parts (cube recipes list
    `"r01",qty=2` or `weap,mag`), without quotes and with 'qty=2' / 'low' style tails cut off."""
    cell = str(cell).strip().lower()
    out = set()
    for part in [cell] + _re.split(r'[,;|]', cell):
        part = part.strip().strip('"\'').strip()
        if part:
            out.add(part)
            out.add(_re.split(r'[=:]', part)[0].strip().strip('"\''))
    return {t for t in out if len(t) > 1 and not t.isdigit()}


def feature_links(patches_dir, tables, game_table=None):
    """Which features use rows that another feature adds. A switched-off feature's new rows are gone,
    so a feature that names them (a cube recipe on a new item, a monster on a new skill, a level on a
    new monster, a unique on a new skill) would point at nothing.
    Returns {user feature: {provider feature: {'count': n, 'examples': ['table: row (column) -> name']}}};
    the user can be 'core' (always installed). References are the LINK_REFS columns, plus the parameter
    of an item property that takes a skill (SKILL_PROPS), looked up among the new rows of the target."""
    cached = {}

    def game_has(t, col):
        """The values the game's own table already has in `col` (a 'new' row may reuse one)."""
        if (t, col) not in cached:
            vals = set()
            got = game_table(t) if game_table else None
            lows = [h.lower() for h in got[0]] if got else []
            if got and col.lower() in lows:
                i = lows.index(col.lower())
                vals = {r[i].strip().lower() for r in got[1] if i < len(r)}
            cached[(t, col)] = vals
        return cached[(t, col)]

    patches = {}
    for t in tables:
        patches[t] = json.loads((patches_dir / (t + '.json')).read_text(encoding='utf-8'))
    provided = {}  # (table name, lower case value) -> feature adding that row
    for t, p in patches.items():
        fid = feature_of(t)
        tname = t.rsplit('/', 1)[-1].lower()
        lows = [h.lower() for h in p['headers']]
        for e in p['rows']:
            if e[0] != '+':
                continue
            for tt, col in {(x, c) for _, _, targets in LINK_REFS for x, c in targets if x == tname}:
                if col.lower() in lows:
                    v = str(e[1][lows.index(col.lower())]).strip().lower() if lows.index(col.lower()) < len(e[1]) else ''
                    if v and v not in game_has(t, col):
                        provided[(tname, v)] = fid
    links = {}

    def hit(user, tname, name, col, value, targets):
        for tok in _link_tokens(value):
            for tt, _ in targets:
                prov = provided.get((tt, tok))
                if prov is None or prov == user or prov == 'core':
                    continue
                slot = links.setdefault(user, {}).setdefault(prov, {'count': 0, 'examples': []})
                slot['count'] += 1
                if len(slot['examples']) < 3:
                    slot['examples'].append('%s: %s (%s) -> %s' % (tname, str(name)[:40], col, tok))
                return

    for t, p in patches.items():
        user = feature_of(t)
        tname = t.rsplit('/', 1)[-1].lower()
        rules = [(_re.compile(c), tg) for tp, c, tg in LINK_REFS if _re.search(tp, tname) and tg]
        for e in p['rows']:
            if e[0] == '+':
                row = dict(zip(p['headers'], e[1]))
                name = e[1][0] if e[1] else ''
            else:
                row = dict((e[2] if len(e) > 2 else None) or {})
                name = e[1][0]
            for h, v in row.items():
                for pat, targets in rules:
                    if pat.search(h):
                        hit(user, tname, name, h, v, targets)
            # a property that takes a skill: its parameter names a skill
            if _re.search(_PROP_ROWS, tname):
                for h, v in row.items():
                    par = param_of(h)
                    if par and par in row and str(v).strip().lower() in SKILL_PROPS:
                        hit(user, tname, name, par, row[par], _SKILL)
    return {u: {p: s for p, s in l.items() if s['count'] >= MIN_LINKS} for u, l in links.items() if l}


def feature_graph(links):
    """-> (needs, forced). needs: {feature: [features whose new rows it uses]}, for switchable
    features only. forced: {feature: the forced feature that needs it, or None for core} for the features that cannot be switched off: the ones the
    always-installed ('core') tables use, and everything those need in turn (a feature switched off
    takes every feature that needs it with it, so a forced one drags what it needs along)."""
    needs = {u: sorted(l) for u, l in links.items() if u != 'core'}
    forced = {f: None for f in links.get('core', {})}  # None: the always-installed tables use it
    todo = list(forced)
    while todo:
        f = todo.pop()
        for n in needs.get(f, []):
            if n not in forced:
                forced[n] = f  # the forced feature f uses it
                todo.append(n)
    return needs, forced


def settings_ui(feature_count, loader, duplicates=None, from_source=None, load_order=None, modlist=None, links=None):
    """The converted mod's settings: a switch per feature it changes and per D2RLoader part."""
    duplicates = duplicates or {}
    from_source = from_source or {}
    links = links or {}
    _, forced = feature_graph(links)
    pinned = set(forced)
    used_by = {}
    for user, l in links.items():
        for prov in l:
            used_by.setdefault(prov, []).append(user)
    flabel = lambda f: FEATURE_INFO[f][1] if f in FEATURE_INFO else f
    features = []
    for fid, fname, what, _ in FEATURES:
        if fid in feature_count:
            lines = []
            needs = links.get(fid, {})
            if fid in forced:
                lines.append('Always on, this switch is ignored: ' + (
                    'tables that cannot be switched off use its new rows (%d references, e.g. %s).' % (
                        links['core'][fid]['count'], links['core'][fid]['examples'][0]) if forced[fid] is None else
                    '%s stays on and uses its new rows.' % flabel(forced[fid])))
            if needs:
                lines.append('Uses new rows of: ' + '; '.join('%s (%d references, e.g. %s)' % (flabel(p), s['count'], s['examples'][0])
                                                              for p, s in sorted(needs.items())) +
                             ('.' if fid in forced else '. When one of those is off, this one is switched off too '
                                                        '(the install log says so).'))
            users = sorted(u for u in used_by.get(fid, []) if u != 'core')
            if users and fid not in forced:
                lines.append('Used by: %s. Turning this off switches them off too, so nothing is left pointing at rows '
                             'that are not there.' % ', '.join(flabel(u) for u in users))
            if not lines:
                lines.append('Nothing else in this mod uses its new rows: safe to switch off on its own.')
            features.append({
                'id': fid, 'type': 'checkbox', 'name': fname, 'defaultValue': True,
                'description': '%s (%d file%s). %s' % (what, feature_count[fid], '' if feature_count[fid] == 1 else 's',
                                                      ' '.join(lines))})
    units = []
    for unit in sorted({u for _, _, u in loader}):
        label = (unit[len('plugin_'):] if unit.startswith('plugin_') else unit[len('patch_'):] if unit.startswith('patch_') else unit)
        name = ('Plugin: ' + label if unit.startswith('plugin_') else 'Patch: ' + label if unit.startswith('patch_')
                else 'Loader settings (d2rloader.toml)' if unit == 'loadersettings'
                else 'Other D2RLoader files (sounds, licences...)')
        dup = duplicates.get(unit)
        units.append({'id': unit, 'type': 'checkbox', 'name': name + (' (already installed separately)' if dup else ''),
                      'defaultValue': not dup,
                      'description': 'Copied to D2RMM\'s d2rloader output when on.' + (
                          ' Off by default: the D2RMM plugin package "%s" installs a different file at the same place, '
                          'and D2RMM refuses to install two different files there.' % dup if dup else '')})
    out = []
    if from_source:
        out.append({'id': 'fromsource', 'type': 'section', 'name': 'Plugins left out: use the source builds', 'defaultExpanded': False,
                    'description': 'These plugins came with the download as prebuilt DLLs, which have been found infected. A build '
                                   'from source is on this machine: install it from there (D2RMM Plugins tab). ' +
                                   '; '.join('%s: %s' % (v['plugin'], v['useInstead']) for v in from_source.values()),
                    'children': []})
    if features:
        out.append({'id': 'features', 'type': 'section', 'name': 'Features', 'defaultExpanded': True, 'children': features})
    if units:
        out.append({'id': 'loaderparts', 'type': 'section', 'name': 'D2RLoader plugins and patches', 'defaultExpanded': False,
                    'children': units})
    if load_order:
        out.append(load_order)
    if modlist:
        out.extend(m for m in (modlist if isinstance(modlist, list) else [modlist]) if m)
    return out


def write_package(d2rmm_loader, mod_id, unit, mod, files):
    """One D2RLoader package for D2RMM's Plugins tab, as a zip in D2RMM's d2rloader folder (D2RMM
    imports zips on start or Plugins > Refresh into <name>/source with its own manifest; hand-made
    folders or edited manifests make D2RMM refuse to start). A package this conversion made before
    is replaced: its imported folder is removed so the new zip is imported fresh."""
    import zipfile
    name = '%s-%s' % (mod_id, unit.split(':', 1)[1])
    old = d2rmm_loader / name
    if old.is_dir():
        shutil.rmtree(old)
    target = d2rmm_loader / (name + '.zip')
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(mod / f, f.split('/', 1)[1])  # drop 'd2rloader/': plugins/..., config/..., patches/...
    return name


def package_loader_folder(loader_dir, d2rmm_loader, prefix, game=None, source_built_folders=None):
    """The plugins and patches of a d2rloader folder that is not the mod's own (a download's
    top-level d2rloader beside mods\\, which a D2RLoader install puts in the game folder) as D2RMM
    packages (zips in D2RMM's d2rloader folder, named <prefix>-<plugin>). Left out: loader settings
    and run-time output, what an installed package already puts there with the same bytes, a
    different file another package puts at the same place, plugins with a source build on this
    machine. A package made before with the same files is not rewritten (D2RMM would re-import it).
    Returns {'packaged', 'unchanged', 'alreadyInstalled', 'conflicts', 'builtFromSource'}."""
    loader_dir, d2rmm_loader = Path(loader_dir), Path(d2rmm_loader)
    base = loader_dir.parent
    files = sorted(rel(p, base) for p in loader_dir.rglob('*') if p.is_file())
    files = ['d2rloader/' + f.split('/', 1)[1] for f in files]  # loader_unit and write_package expect 'd2rloader/...'
    files = [f for f in files if f.split('/')[1].lower() not in LOADER_SKIP and not f.lower().endswith(SKIP_SUFFIXES)]
    real = lambda f: loader_dir / f.split('/', 1)[1]
    units = {}
    for f in files:
        units.setdefault(loader_unit(f), []).append(f)
    for unit in [u for u in units if u.startswith('plugin:') and all(f.endswith('.toml') for f in units[u])]:
        owner = [u for u in units if u != unit and u.startswith('plugin:') and u.split(':', 1)[1].endswith('-' + unit.split(':', 1)[1])]
        if len(owner) == 1:
            units[owner[0]] += units.pop(unit)
    taken = installed_targets(d2rmm_loader, prefix)
    built = source_built(source_built_folders if source_built_folders is not None else (source_folders(game) if game else []))
    out = {'packaged': [], 'unchanged': [], 'alreadyInstalled': {}, 'conflicts': {}, 'builtFromSource': {}}
    sha = lambda f: hashlib.sha256(real(f).read_bytes()).hexdigest()
    for unit, fs in sorted(units.items()):
        if not unit.startswith(('plugin:', 'patch:')):
            continue
        label = unit.split(':', 1)[1]
        dlls = [f.rsplit('/', 1)[-1][:-4].lower() for f in fs if f.lower().endswith('.dll')]
        hit = next((built[x] for x in dlls + [label.lower()] if x in built), None)
        if hit:
            out['builtFromSource'][label] = hit
            continue
        target = {f.split('/', 1)[1].replace('/', '\\').lower(): sha(f) for f in fs}
        owners = {taken[t][0] for t in target if t in taken and taken[t][1] == target[t]}
        clash = {taken[t][0] for t in target if t in taken and taken[t][1] != target[t]}
        if clash:
            out['conflicts'][label] = sorted(clash)
            continue
        if owners and all(t in taken for t in target):
            out['alreadyInstalled'][label] = sorted(owners)
            continue
        name = '%s-%s' % (prefix, label)
        manifest = d2rmm_loader / name / 'manifest.json'
        try:
            old = {f['targetPath'].lower(): f.get('sha256') for f in json.loads(manifest.read_text(encoding='utf-8-sig')).get('files', [])}
        except (OSError, ValueError):
            old = None
        if old == target:
            out['unchanged'].append(name)
            continue
        out['packaged'].append(write_package(d2rmm_loader, prefix, unit, base, fs))
    return out


# --------------------------------------------------------------------------- main

def read_modinfo(path):
    """modinfo.json; the game also takes /* */ and // comments in it (some mods ship a comment block)."""
    text = path.read_text(encoding='utf-8-sig')
    try:
        return json.loads(text)
    except ValueError:
        text = _re.sub(r'/\*.*?\*/', '', text, flags=_re.S)
        text = _re.sub(r'(?m)^\s*//.*$', '', text)
        text = _re.sub(r',(\s*[}\]])', r'\1', text)
        return json.loads(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', required=True)
    ap.add_argument('--mod', required=True)
    ap.add_argument('--name')
    ap.add_argument('--author')
    ap.add_argument('--version')
    ap.add_argument('--description')
    ap.add_argument('--cache', default=os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'D2RModAssets', 'vanilla'))
    ap.add_argument('--python', default=sys.executable)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--rows', choices=('keep', 'rebuild'), default='keep',
                    help='keep (default): rows stay where they are, new rows go at the end, row numbers in '
                         'the mod\'s cells follow them (works next to other mods); rebuild: the mod\'s own row '
                         'order, exactly the data mod (alone, or at the top of the list)')
    ap.add_argument('--plugins', choices=('mod', 'packages'), default='mod',
                    help="mod (default): the D2RLoader plugins and patches are copied by mod.js, each with a "
                         "switch in the mod settings; packages: each plugin and patch becomes its own D2RLoader "
                         "package in D2RMM's d2rloader folder (Plugins tab), the rest stays with mod.js")
    ap.add_argument('--match-trim', action=argparse.BooleanOptionalAction, default=True,
                    help='match rows with the spaces around their first cell ignored (default on; the game has '
                         'names with trailing spaces a mod\'s copy lacks, which otherwise counts as deleted + new)')
    ap.add_argument('--duplicates', choices=('content', 'order'), default='content',
                    help='rows that share a name (Rainbow Facet x8): content (default) matches them by what is in '
                         'them, also to the mod\'s renamed copies (Rainbow Facet Cold); order: by the how-many-th')
    ap.add_argument('--deleted', choices=('disable', 'leave'), default='disable',
                    help="rows mode keep: rows the mod deleted stay in place; disable (default) switches them off "
                         "(spawnable / enabled / complete 0) so they no longer drop or craft; leave: as they are")
    ap.add_argument('--conflicts', choices=('mod', 'earlier'), default='mod',
                    help='default of the Load order > Conflicts setting: a cell or string a mod above changed too; '
                         'mod (default): this mod\'s value; earlier: the mod above keeps its value')
    ap.add_argument('--files', choices=('overwrite', 'keep'), default='overwrite',
                    help='default of the Load order > Files setting: a file a mod above already installed; '
                         'overwrite (default) or keep it')
    ap.add_argument('--modlist-rules', help="'My mod list' rules (JSON) for the converted mod's settings, all off by "
                                           'default (default: <D2RMM>\\mods\\modlist-rules.json when it exists; '
                                           'none = no section); see modlist-rules.example.json')
    ap.add_argument('--source', help='where the mod came from (a download), kept in convert.json for updates')
    ap.add_argument('--d2rmm', help="D2RMM's folder (default: the one the mod sits in): its d2rloader packages are "
                                    'checked for plugins installed already, and --plugins packages writes there')
    ap.add_argument('--source-built', action='append', default=None,
                    help='a source workspace whose plugins are left out (default: <game>/mods/* with packages/ and '
                         'upstream/plugins/); repeatable; --source-built none turns it off')
    args = ap.parse_args()

    mod = Path(args.mod).resolve()
    previous = old_report(mod)
    game = Path(args.game)
    cache = Path(args.cache)
    data, modinfo_path = find_data_root(mod)
    modinfo = read_modinfo(modinfo_path) if modinfo_path else {}
    mod_id = mod.name

    all_files = sorted(rel(p, data) for p in data.rglob('*') if p.is_file())
    print('%s: %d files under %s' % (mod_id, len(all_files), data), file=sys.stderr)
    # D2RLoader's table caches (D2RLBIN header) are not compiled tables: D2RLoader writes them from
    # the .txt it loads. Copying them would put the author's tables back over the merged ones.
    loader_caches = set()
    for f in all_files:
        if f.lower().startswith('global/excel/') and f.lower().endswith('.bin'):
            with open(data / f, 'rb') as fh:
                if fh.read(7) == b'D2RLBIN':
                    loader_caches.add(f)
    if loader_caches:
        print('%d D2RLoader table cache(s) (D2RLBIN) left out.' % len(loader_caches), file=sys.stderr)
    compiled_only = [f for f in all_files if f.lower().startswith('global/excel/') and f.lower().endswith('.bin')
                     and f not in loader_caches and f[:-4] + '.txt' not in all_files]
    if compiled_only:
        print('WARNING: %d table(s) only as compiled .bin (%s...). D2RMM runs the game on .txt tables, so these '
              'are copied but will not apply; decompile them to .txt first.' % (len(compiled_only), ', '.join(compiled_only[:5])),
              file=sys.stderr)
    lookup = [f for f in all_files if f.lower().endswith(('.txt', '.json'))]
    use_d2rmm_casclib(Path(args.d2rmm) if args.d2rmm else mod.parent.parent)
    vanilla = fetch_vanilla(game, cache, lookup, args.python)

    patches_dir = mod / 'd2rmm' / 'patches'
    tables, strings, copies, identical, whole = [], [], [], [], {}
    stats = {}
    for f in all_files:
        if f in loader_caches:
            continue  # kept in all_files so compress() never copies a folder holding one
        src = data / f
        van = vanilla.get(f)
        if van is not None and van.read_bytes() == src.read_bytes():
            identical.append(f)
            continue
        if van is not None and is_table(f):
            m, v = read_table(src), read_table(van)
            if m is None or v is None:
                whole[f] = 'not UTF-8'
            else:
                # also for 'rebuild': the mod settings can switch rows to 'keep' at install time
                disable = DISABLE_COLUMN.get(f.rsplit('/', 1)[-1].lower()) if args.deleted == 'disable' else None
                patch, st = table_patch(v, m, trim=args.match_trim, duplicates=args.duplicates, disable=disable)
                if patch is None:
                    whole[f] = st
                else:
                    h, rows = apply_table(v, patch)
                    assert (h, rows) == m, f + ': patch does not rebuild the file'
                    out = patches_dir / (f + '.json')
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_text(json.dumps(patch, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
                    tables.append(f)
                    stats[f] = st
                    continue
        elif van is not None and is_strings(f):
            m, v = read_strings(src), read_strings(van)
            if m is None or v is None:
                whole[f] = 'not a list of {Key, ...} entries'
            else:
                patch, st = strings_patch(v, m)
                if by_key(apply_strings(v, patch)) != by_key(m):
                    whole[f] = 'repeated Keys in an order the patch cannot rebuild'
                    copies.append(f)
                    continue
                out = patches_dir / (f + '.json')
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(patch, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
                strings.append(f)
                stats[f] = st
                continue
        copies.append(f)

    # Folders are copied whole only when nothing in them is patched or identical (compress checks
    # that every member is a copy), so the patches never meet a copied file. Per feature, so a
    # folder is only copied whole when all of it belongs to one switch.
    by_feature = {}
    for f in copies:
        by_feature.setdefault(feature_of(f), []).append(f)
    copy_list = []
    for fid, fs in sorted(by_feature.items()):
        copy_list += [(p, d, fid) for p, d in compress(fs, all_files)]
    feature_count = {}
    for f in tables + strings + copies:
        fid = feature_of(f)
        feature_count[fid] = feature_count.get(fid, 0) + 1

    loader = []
    packaged = []
    duplicates = {}  # switch -> D2RMM package that installs a different file at the same place
    from_source = {}  # switch -> plugin left out: a source build of it is on this machine
    provided = {}  # switch -> plugin left out: an installed D2RMM package has the same files
    loader_root = mod / 'd2rloader'
    if loader_root.is_dir():
        loader_files = sorted(rel(p, mod) for p in loader_root.rglob('*') if p.is_file())
        wanted = [f for f in loader_files
                  if f.split('/')[1].lower() not in LOADER_SKIP and not f.lower().endswith(SKIP_SUFFIXES)]
        units = {}
        for f in wanted:
            units.setdefault(loader_unit(f), []).append(f)
        # A plugin's config named without the DLL's prefix (ruffneckk-mapsense.toml beside
        # d2rl-ruffneckk-mapsense.dll) goes with that plugin.
        for unit in [u for u in units if u.startswith('plugin:') and all(f.endswith('.toml') for f in units[u])]:
            base = unit.split(':', 1)[1]
            owner = [u for u in units if u != unit and u.startswith('plugin:') and u.split(':', 1)[1].endswith('-' + base)]
            if len(owner) == 1:
                units[owner[0]] += units.pop(unit)
        d2rmm_loader = (Path(args.d2rmm) if args.d2rmm else mod.parent.parent) / 'd2rloader'  # D2RMM's plugin packages
        taken = installed_targets(d2rmm_loader, mod.name)
        folders = [] if args.source_built == ['none'] else (args.source_built or source_folders(game))
        built = source_built(folders)
        for unit in [u for u in units if u.startswith('plugin:')]:
            name = unit.split(':', 1)[1]
            dlls = [f.rsplit('/', 1)[-1][:-4].lower() for f in units[unit] if f.lower().endswith('.dll')]
            hit = next((built[x] for x in dlls + [name] if x in built), None)
            if hit:
                from_source[switch_id(unit)] = {'plugin': name, 'files': units.pop(unit), 'useInstead': hit}
        for unit, fs in sorted(units.items()):
            missing = [f for f in fs if not (mod / f).is_file()]
            if missing:  # a file a virus scanner removed after it was listed, say
                print('WARNING: %s: not in the mod folder, left out: %s' % (unit, ', '.join(missing)), file=sys.stderr)
                fs = [f for f in fs if f not in missing]
                if not fs:
                    continue
            same = set()
            for f in fs:
                hit = taken.get(f.split('/', 1)[1].replace('/', '\\').lower())
                if hit and hit[1] != hashlib.sha256((mod / f).read_bytes()).hexdigest():
                    duplicates[switch_id(unit)] = hit[0]
                elif hit:
                    same.add(hit[0])
            if (unit.startswith(('plugin:', 'patch:')) and switch_id(unit) not in duplicates and same
                    and all(f.split('/', 1)[1].replace('/', '\\').lower() in taken for f in fs)):
                # an installed package (made by hand from these plugins, say) puts the very same files
                # there: copying them again would only make D2RMM write them twice
                provided[switch_id(unit)] = {'plugin': unit.split(':', 1)[1], 'package': sorted(same)}
                continue
            if switch_id(unit) in duplicates and args.plugins == 'packages':
                continue  # installed separately already: no second package
            if args.plugins == 'packages' and unit.startswith(('plugin:', 'patch:')) and d2rmm_loader.is_dir():
                packaged.append(write_package(d2rmm_loader, mod.name, unit, mod, fs))
            else:
                loader += [(p, d, switch_id(unit)) for p, d in compress(fs, loader_files)]

    # A rerun keeps the name and version the conversion was given before, unless told otherwise.
    old_info = {}
    if (mod / 'mod.json').exists():
        try:
            old_info = json.loads((mod / 'mod.json').read_text(encoding='utf-8-sig'))
        except ValueError:
            old_info = {}
    name = args.name or old_info.get('name') or modinfo.get('name') or mod_id
    version = args.version or old_info.get('version') or modinfo.get('version') or '1.0'
    data_rel = win(rel(data, mod))
    rules_path = (None if (args.modlist_rules or '').lower() == 'none' else args.modlist_rules or
                  ((Path(args.d2rmm) if args.d2rmm else mod.parent.parent) / 'mods' / 'modlist-rules.json'))
    rules, rules_used = modlist_rules(rules_path, mod_id, loader, tables, strings, copy_list, data)
    links = feature_links(patches_dir, tables, lambda t: read_table(vanilla[t]) if vanilla.get(t) else None)
    needs, forced = feature_graph(links)
    data_block = '\n'.join([
        '// Generated by ConvertDataMod.py - do not edit by hand.',
        js_list('COPY', [[win(p), d, fid] for p, d, fid in copy_list], 'Copied as they are: [path under DATA, is a folder, switch].'),
        js_list('LOADER', [[win(p), d, u] for p, d, u in loader], 'D2RLoader files, to D2RMM\'s d2rloader output: [path in the mod folder, is a folder, switch].'),
        js_list('TABLES', [[win(t), feature_of(t)] for t in tables], 'Tables patched row by row (d2rmm\\patches\\<path>.json): [path, switch].'),
        js_list('STRINGS', [[win(s), feature_of(s)] for s in strings], 'String files merged by Key (d2rmm\\patches\\<path>.json): [path, switch].'),
        '// Features that use new rows of other features: {feature: [features it needs]}; FORCED: the features always-on\n'
        '// tables use (and what those need), which cannot be switched off, with the reason.\n'
        'const NEEDS = %s;\nconst FORCED = %s;\nconst FORCED_WHY = %s;\n' % (
            json.dumps(needs, ensure_ascii=False), json.dumps(sorted(forced)),
            json.dumps({f: ('tables that cannot be switched off use its new rows' if by is None else '%s needs it' % by)
                        for f, by in forced.items()})),
        js_list('MODLIST', [{k: v for k, v in r.items() if k != 'description'} for r in rules],
                'My mod list rules (settings, off by default) and Options (option: on by default, acts when off): '
                '{id, name, when, above, option, skip, switches, earlier, props}.'),
    ])
    js = (MOD_JS.replace('__NAME__', name).replace('__ORIG__', modinfo.get('name', mod_id))
          .replace('__BY__', ' by ' + args.author if args.author else '')
          .replace('__DATA_WIN__', data_rel).replace('__DATA__', data_rel.replace('\\', '\\\\'))
          .replace('__ID__', mod_id).replace('__ROWS__', args.rows)
          .replace('__CELLS__', args.conflicts).replace('__FILES__', args.files).replace('__NTABLES__', str(len(tables)))
          .replace('__NSTRINGS__', str(len(strings))).replace('__NCOPY__', str(len(copy_list))))
    begin, end = '/* @generated-data-begin */\n', '/* @generated-data-end */'
    head, rest = js.split(begin)
    _, tail = rest.split(end)
    (mod / 'mod.js').write_text(head + begin + data_block + end + tail, encoding='utf-8', newline='\n')

    mod_json = mod / 'mod.json'
    info = json.loads(mod_json.read_text(encoding='utf-8')) if mod_json.exists() else {}
    info.update({
        'name': name,
        'description': args.description or info.get('description') or (
            'D2RMM version of the data mod "%s": patches the tables and strings it changes instead of '
            'replacing whole files, copies its other files and its D2RLoader plugins. %s'
            % (modinfo.get('name', mod_id), 'Rows stay where they are and its new rows go at the end, so it works next '
               'to other mods; mods made for it go below it.' if args.rows == 'keep'
               else 'Put it at the TOP of the mod list.')),
        'author': args.author or info.get('author') or 'unknown',
        'version': version,
        'config': settings_ui(feature_count, loader, duplicates, from_source,
                              load_order_ui(args.rows, args.conflicts, args.files),
                              [options_ui(rules), modlist_ui(rules)], links),
    })
    mod_json.write_text(json.dumps(info, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    report = {
        'data': rel(data, mod),
        'modinfo': modinfo,
        'files': len(all_files),
        'identicalToGame': len(identical),
        'tablesPatched': {t: stats[t] for t in tables},
        'stringsMerged': {s: stats[s] for s in strings},
        'copiedWhole': len(copies),
        'copiedWholeAlthoughInGame': whole,
        'loaderCachesLeftOut': sorted(loader_caches),
        'copyEntries': len(copy_list),
        'loaderEntries': [p for p, _, _ in loader],
        'loaderPackages': packaged,
        'loaderInstalledSeparately': duplicates,
        'loaderBuiltFromSource': from_source,
        'loaderProvidedByPackage': provided,
        'features': feature_count,
        'featureLinks': links,
        'featuresForcedOn': sorted(forced),
        'modListRules': {'file': rules_used, 'rules': [r['id'] for r in rules]},
        'rows': args.rows,
        'rowMatching': {'matchTrim': args.match_trim, 'duplicates': args.duplicates, 'deleted': args.deleted,
                        'matchedByContent': sum(s.get('matchedByContent', 0) for s in stats.values()),
                        'disabled': {t: s['disabled'] for t, s in stats.items() if s.get('disabled')}},
        # what an update (the converter GUI's Update) runs the conversion with again
        'settings': {'name': name, 'author': info['author'], 'version': version, 'rows': args.rows,
                     'plugins': args.plugins, 'matchTrim': args.match_trim, 'duplicates': args.duplicates,
                     'deleted': args.deleted, 'conflicts': args.conflicts, 'files': args.files,
                     'source': args.source or (previous.get('settings') or {}).get('source')},
    }
    (mod / 'd2rmm').mkdir(exist_ok=True)
    (mod / 'd2rmm' / 'convert.json').write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
    write_readme(mod, name, info['author'], version, modinfo.get('name', mod_id), data_rel, tables, strings,
                 copies, copy_list, identical, whole, loader, args.rows)
    if from_source:
        readme = mod / 'README.md'
        if readme.exists() and README_MARK in readme.read_text(encoding='utf-8', errors='replace'):
            with open(readme, 'a', encoding='utf-8') as f:
                f.write('\n## Plugins left out\n\nThe download ships these D2RLoader plugins prebuilt. Prebuilt copies have been found '
                        'infected, and a build from source is on this machine, so the conversion leaves them out: install the '
                        'source build instead (D2RMM Plugins tab).\n\n')
                for v in from_source.values():
                    f.write('- %s (%s): %s\n' % (v['plugin'], ', '.join(x.rsplit('/', 1)[-1] for x in v['files']), v['useInstead']))
        print('%d plugin(s) left out, built from source on this machine: %s'
              % (len(from_source), ', '.join(v['plugin'] for v in from_source.values())))
    if provided:
        readme = mod / 'README.md'
        if readme.exists() and README_MARK in readme.read_text(encoding='utf-8', errors='replace'):
            with open(readme, 'a', encoding='utf-8') as f:
                f.write('\n## Plugins installed by D2RMM packages\n\nThese D2RLoader plugins and patches are not copied by this mod: '
                        'an installed D2RMM plugin package already puts the same files there (enable it on the Plugins tab).\n\n')
                for v in provided.values():
                    f.write('- %s: %s\n' % (v['plugin'], ', '.join(v['package'])))
        print('%d plugin(s)/patch(es) left out, an installed D2RMM package has the same files: %s'
              % (len(provided), ', '.join(sorted({p for v in provided.values() for p in v['package']}))))
    print('%s: %d tables patched, %d string files merged, %d files copied (%d entries), %d identical to the game, '
          '%d copied whole although the game has them %s, %d D2RLoader entries'
          % (mod_id, len(tables), len(strings), len(copies), len(copy_list), len(identical), len(whole),
             sorted(set(whole.values())), len(loader)))

    if args.check:
        check(mod, data, cache, tables, strings, copies, loader, args.rows)


README_MARK = '<!-- written by ConvertDataMod.py; rerunning it rewrites this file -->'


def write_readme(mod, name, author, version, orig, data_rel, tables, strings, copies, copy_list, identical, whole, loader,
                 rows='keep'):
    path = mod / 'README.md'
    if path.exists() and README_MARK not in path.read_text(encoding='utf-8', errors='replace'):
        return  # someone wrote their own
    lines = [
        README_MARK,
        '# %s (D2RMM conversion)' % name,
        '',
        'D2RMM version of the data mod "%s" by %s, version %s. The mod\'s own files stay in `%s`;' % (orig, author, version, data_rel),
        '`mod.js` (generated by the toolkit\'s `Tools\\DiabloII\\ConvertDataMod.py`) installs them through D2RMM:',
        '',
        '- %d tables patched row by row (`d2rmm\\patches`): rows are matched by their first column, so other' % len(tables),
        '  mods\' changes to the same tables survive and game patches still come through for what the mod',
        '  leaves alone;',
        '- %d string files merged by Key;' % len(strings),
        '- %d other files copied as they are (%d copy entries); %d files identical to the game skipped;' % (len(copies), len(copy_list), len(identical)),
        '- %s.' % ('the D2RLoader folder (%d entries: plugins, config, patches...) copied to D2RMM\'s d2rloader output' % len(loader)
                   if loader else 'no D2RLoader files'),
    ]
    if whole:
        lines.append('- copied whole although the game has them: ' + ', '.join('`%s` (%s)' % kv for kv in sorted(whole.items())))
    lines += [
        '',
    ]
    if rows == 'keep':
        lines += [
            '**Rows: keep.** Every row stays where it is (row numbers are what saves, plugins and other tables point',
            "at), rows the mod deleted stay too, the mod's new rows go at the end, and row numbers in its cells",
            '(weapon missiles, skills in item properties, level and warp numbers) follow their rows. It can sit anywhere in the mod list;',
            'mods made for it go below it. Test combinations with `Test-D2RMod.ps1 -KeepGoing`.',
        ]
    else:
        lines += [
            "**Load order:** top of the list (rows: rebuild, the mod's own row order). Mods that build on the",
            'stock skill trees or tables may not fit a mod that changes them; test the combination',
            '(`Test-D2RMod.ps1` with this mod first).',
        ]
    lines += [
        '',
        'To undo the conversion, delete `mod.js`, `mod.json`, `README.md` and `d2rmm\\`: D2RMM then lists',
        'the folder as the original data mod again. To redo it after the mod or the game changes:',
        '',
        '    Convert-D2RDataMod.ps1 -GamePath <game> -Mod <this folder> -Author "%s" -Rows %s -Check' % (author, rows),
        '',
        '`d2rmm\\convert.json` lists what was patched, merged and copied.',
        '',
    ]
    path.write_text('\n'.join(lines), encoding='utf-8')


# Same as ID_TABLES in mod.js
ID_TABLES = {'levels.txt': 'Id', 'lvlwarp.txt': 'Id'}
# Same as ROW_REFS in mod.js: (tables, column pattern, target table)
REF_COLUMNS = [
    (('weapons.txt', 'misc.txt', 'armor.txt'), r'missiletype', 'missiles.txt'),
    (('levels.txt',), r'Id|Depend|Vis[0-7]', 'levels.txt'),
    (('levels.txt',), r'Warp[0-7]', 'lvlwarp.txt'),
    (('lvlwarp.txt',), r'Id', 'lvlwarp.txt'),
    (('lvlmaze.txt',), r'Level', 'levels.txt'),
    (('lvlprest.txt',), r'LevelId', 'levels.txt'),
]
SKILL_PROPS = {'skill', 'oskill', 'aura', 'hit-skill', 'gethit-skill', 'att-skill', 'kill-skill',
               'death-skill', 'levelup-skill', 'charged', 'charge-noconsume'}


def param_of(code):
    import re
    for pat, fn in ((r'^prop(\d+)$', 'par%s'), (r'^aprop(\d+[ab])$', 'apar%s'), (r'^PCode(\d+[ab])$', 'PParam%s'),
                    (r'^FCode(\d+)$', 'FParam%s'), (r'^T1Code(\d+)$', 'T1Param%s'), (r'^mod(\d+)code$', 'mod%sparam'),
                    (r'^((?:[bc] )?mod \d+)$', '%s param'), (r'^(\w+Mod\d)Code$', '%sParam')):
        m = re.match(pat, code)
        if m:
            return fn % m.group(1)
    return None


def check_keep(mod, data, out, tables, cache):
    """'keep' mode: the game's rows stay at their places, the mod's new rows follow in its order,
    every row has the mod's values, and row numbers in the mod's cells point at the same rows as
    in the mod's own files. -> number of tables that fail."""
    patches = {t: json.loads((mod / 'd2rmm' / 'patches' / (t + '.json')).read_text(encoding='utf-8')) for t in tables}
    where = {}
    for t, p in patches.items():
        got = read_table(out / t)
        # where each row of the mod's file is in the output: '=' rows at their place in the game's
        # table (rows stay where they are, renamed ones too), new rows appended
        ids = {i: n for n, i in enumerate(row_ids(read_table(cache / t)[1], p.get('trim')))}
        w = []
        appended = len(got[1]) - sum(1 for e in p['rows'] if e[0] == '+')
        for e in p['rows']:
            if e[0] == '=':
                w.append(ids.get(tuple(e[1]), -1))
            else:
                w.append(appended)
                appended += 1
        where[t] = w
    # tables numbered by an Id column that skips separator rows (levels.txt): the mod's Id -> its new Id
    idmap = {}
    sequence = []
    for t in patches:
        if t.rsplit('/', 1)[-1].lower() in ID_TABLES:
            mh_, mr_ = read_table(data / t)
            gh_, gr_ = read_table(out / t)
            cm, cg = mh_.index('Id'), gh_.index('Id')
            idmap[t] = {r[cm].strip(): gr_[where[t][j]][cg] for j, r in enumerate(mr_)
                        if r[cm].strip() and 0 <= where[t][j] < len(gr_)}
            # every Id above the game's own top one moves by the same amount
            vh_, vr_ = read_table(cache / t)
            own = max([int(r[vh_.index('Id')]) for r in vr_ if r[vh_.index('Id')].strip().isdigit()] or [-1])
            moves = {int(gr_[where[t][j]][cg]) - int(r[cm]) for j, r in enumerate(mr_)
                     if r[cm].strip().isdigit() and int(r[cm]) > own and 0 <= where[t][j] < len(gr_)
                     and gr_[where[t][j]][cg].strip().isdigit()}
            if len(moves) > 1:
                sequence.append(t)
    bad = len(sequence)
    for t in sequence:
        print('  DIFFERS: %s: the mod\'s added Ids did not all move by the same amount' % t)
    for t, p in patches.items():
        folder = t[:t.rfind('/') + 1]
        mh, mrows = read_table(data / t)
        gh, grows = read_table(out / t)
        col = {h: i for i, h in enumerate(gh)}
        code_of = {param_of(c): c for c in mh if param_of(c)}  # parameter column -> its property column
        tname = t.rsplit('/', 1)[-1].lower()
        refs = [(pat, tgt) for names, pat, tgt in REF_COLUMNS if tname in names]
        problems = []
        for j, (e, r) in enumerate(zip(p['rows'], mrows)):
            at = where[t][j]
            if at < 0 or at >= len(grows):
                problems.append('row %d of the mod is missing' % j)
                continue
            row = dict(zip(mh, r))
            # numbers move only in the cells the mod sets (its changes and its new rows)
            set_by_mod = set(row) if e[0] == '+' else set(e[2] if len(e) > 2 else {})
            for h, val in row.items():
                if h not in col:
                    continue
                want = val
                target = None
                if h not in set_by_mod:
                    pass
                elif any(_re.fullmatch(pat, h) for pat, _ in refs):
                    target = folder + next(tgt for pat, tgt in refs if _re.fullmatch(pat, h))
                elif h in code_of and row.get(code_of[h], '').lower() in SKILL_PROPS:
                    target = folder + 'skills.txt'
                if target in idmap and val.isdigit():
                    want = idmap[target].get(val, val)
                elif target in where and val.isdigit() and int(val) < len(where[target]) and where[target][int(val)] >= 0:
                    want = str(where[target][int(val)])
                if grows[at][col[h]] != want:
                    problems.append('row %d (%s) column %s: %r, expected %r' % (j, r[0], h, grows[at][col[h]], want))
        if p.get('disable') and p['disable'] in col:
            # rows the mod deleted stay in place, switched off
            vh, vrows = read_table(cache / t)
            vcol = vh.index(p['disable'])
            ids = {i: n for n, i in enumerate(row_ids(vrows, p.get('trim')))}
            for k, n in p['deleted']:
                at = ids.get((k, n))
                if at is not None and vrows[at][vcol] not in ('', '0') and grows[at][col[p['disable']]] != '0':
                    problems.append('deleted row %s #%d: %s is %r, expected 0' % (k, n, p['disable'], grows[at][col[p['disable']]]))
        if problems:
            bad += 1
            print('  DIFFERS: %s: %s' % (t, '; '.join(problems[:3])))
    return bad


def check(mod, data, cache, tables, strings, copies, loader, rows='rebuild'):
    """Runs mod.js in a mock D2RMM and compares what it writes with the mod's own files."""
    out = Path(tempfile.gettempdir()) / 'ConvertDataModCheck' / mod.name
    if not shutil.which('node'):
        raise SystemExit('The check runs mod.js in Node.js, which is not installed (or not on PATH): get the LTS '
                         'from https://nodejs.org/en/download and run again, or convert without --check.')
    proc = subprocess.run(['node', str(HERE / 'ConvertDataModCheck.js'), str(mod), str(cache), str(out)],
                          capture_output=True, text=True)
    print(proc.stdout.strip())
    if proc.returncode != 0:
        raise SystemExit('mod.js failed in the mock:\n' + proc.stderr[-3000:])
    written = json.loads((out / 'copies.json').read_text(encoding='utf-8'))
    bad = 0
    if rows == 'keep':
        bad += check_keep(mod, data, out, tables, cache)
    for t in (tables if rows != 'keep' else []):
        got = read_table(out / t)
        want = read_table(data / t)
        if got != want:
            bad += 1
            print('  DIFFERS: ' + t)
    for s in strings:
        got = by_key(json.loads((out / s).read_text(encoding='utf-8-sig')))
        want = by_key(read_strings(data / s))
        if got != want:
            bad += 1
            print('  DIFFERS: ' + s)
    copied = set(written['data'])
    missing = [c for c in copies if c not in copied]
    extra = [c for c in copied if c not in set(copies)]
    print('check: %d tables and %d string files rebuilt by mod.js, %d differ; %d of %d copies made, %d unexpected; '
          '%d D2RLoader files' % (len(tables), len(strings), bad, len(copies) - len(missing), len(copies),
                                  len(extra), len(written['loader'])))
    shutil.rmtree(out, ignore_errors=True)
    if bad or missing or extra:
        raise SystemExit('check failed (missing %s, extra %s)' % (missing[:5], extra[:5]))


if __name__ == '__main__':
    main()
