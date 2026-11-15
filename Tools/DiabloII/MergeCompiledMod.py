r"""Turns a data mod that ships its tables only as compiled .bin (Rebirth) into a data mod with
.txt tables, ready for ConvertDataMod.py.

    python MergeCompiledMod.py <extracted mod folder> <out mod folder> [--name Rebirth]

<extracted mod folder> holds data\ (and modinfo.json...), e.g. what
    python MpqArchive.py extract <...>\mods\Rebirth\Rebirth.mpq <folder>
gives. The result is <out mod folder>\<name>.mpq\ with the merged .txt tables and every other
file of the mod, plus <out mod folder>\merge-report.json.

Three-way merge, for every table whose .bin the mod changes: the game's .bin and the mod's .bin
are decompiled the same way (BinTables.py). Rows are matched by decoded key (duplicates of a key
paired by most equal cells). A matched row is the game's .txt row with only the cells whose two
decodes differ taken from the mod; a new row is the mod's decode. Rows come in the mod's order;
rows the mod dropped go; the game's 'Expansion' separator rows stay in front of the row that
followed them. levels takes each column from levels.bin or leveldefs.bin, whichever decodes it.
Label columns the game never compiles are filled on new rows (misc name/rarity, gamble name,
lvlprest Name). The mod's .bin tables are left out (the game would load them over the .txt)."""
import argparse
import collections
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import BinTables as B  # noqa: E402

REFS = ['skills', 'missiles', 'states', 'itemstatcost', 'properties', 'propertygroups', 'monstats', 'skilldesc',
        'itemtypes', 'weapons', 'armor', 'misc', 'uniqueitems', 'setitems', 'playerclass', 'overlay', 'pettype',
        'monprop', 'sounds', 'levels', 'treasureclassex', 'superuniques', 'events']


def _kinds(t, game, log):
    lay = B.load_layout(t, game, log=log)
    custom = B.CUSTOM_COLUMNS.get(t, lambda c: False)
    return {c: (f['type'] not in ('missing', 'ambiguous') or custom(c)) for c, f in lay['fields'].items()}


def _combined(dec, t, game, log):
    """(headers, rows, decoded columns) of a table; levels gets the leveldefs columns levels.bin lacks."""
    h, rows = dec[t]
    ok = _kinds(t, game, log)
    if t != 'levels' or 'leveldefs' not in dec:
        return h, rows, {c for c in h if ok.get(c, True)}
    dh, drows = dec['leveldefs']
    dok = _kinds('leveldefs', game, log)
    assert len(drows) == len(rows), 'levels/leveldefs row counts differ'
    take = [c for c in dh if dok.get(c) and not ok.get(c, True) and c in h]
    rows = [list(r) for r in rows]
    for r, d in zip(rows, drows):
        for c in take:
            r[h.index(c)] = d[dh.index(c)]
    return h, rows, {c for c in h if ok.get(c, True)} | set(take)


def _key_groups(rows):
    g = collections.defaultdict(list)
    for i, r in enumerate(rows):
        g[r[0].strip().lower()].append(i)
    return g


def _pair(grows, mrows):
    """{mod row index: game row index}; within a key, pairs with the most equal cells first."""
    gg, mg = _key_groups(grows), _key_groups(mrows)
    out = {}
    for k, ms in mg.items():
        gs = gg.get(k, [])
        if not gs:
            continue
        if len(gs) == 1 and len(ms) == 1:
            out[ms[0]] = gs[0]
            continue
        score = sorted(((sum(B.same(a, b) for a, b in zip(grows[g], mrows[m])), -abs(gs.index(g) - ms.index(m)), m, g)
                        for m in ms for g in gs), reverse=True)
        um, ug = set(), set()
        for _, _, m, g in score:
            if m not in um and g not in ug:
                out[m] = g
                um.add(m)
                ug.add(g)
    return out


def merge(src, out_mpq, echo=print):
    """Merges the mod in src (a folder with data\\) into out_mpq (a <name>.mpq folder, created).
    Returns the report {table: counts}."""
    src, out_mpq = Path(src), Path(out_mpq)
    log = lambda *a: None
    game = B.Source(B.VANILLA)
    mod = B.Source(src / 'data')
    excel_in = src / 'data' / 'global' / 'excel'
    if not excel_in.is_dir():
        raise SystemExit('%s: no data\\global\\excel' % src)

    changed = []
    for p in sorted(excel_in.glob('*.bin')):
        t = p.stem.lower()
        gp = game.path(t, '.bin')
        if t.endswith('code') or not gp or gp.read_bytes() == p.read_bytes():
            continue
        changed.append(t)
    if 'leveldefs' in changed and 'levels' not in changed:
        changed.append('levels')
    tables = changed + [t for t in REFS if t not in changed and mod.path(t, '.bin')]
    echo('changed tables: %d' % len(changed))
    gdec = B.decompile_mod(B.VANILLA, None, tables, game, log)
    mdec = B.decompile_mod(src / 'data', None, tables, game, log)

    report = {}
    excel = out_mpq / 'data' / 'global' / 'excel'
    for t in changed:
        if t == 'leveldefs':
            continue  # merged into levels
        gh, grows, gdecoded = _combined(gdec, t, game, log)
        mh, mrows, _ = _combined(mdec, t, game, log)
        assert gh == mh, t + ': game and mod decode to different columns'
        th, trows = game.txt(t)
        trows = [r + [''] * (len(th) - len(r)) for r in trows]
        real = [i for i, r in enumerate(trows) if not (r and r[0].strip().lower() == 'expansion')]
        assert len(real) == len(grows), '%s: %d game .txt rows, %d decoded' % (t, len(real), len(grows))
        col = {c: gh.index(c) for c in th if c in gh}
        use = [c for c in th if c in col and c in gdecoded and not c.startswith('*')]
        m2g = _pair(grows, mrows)
        before = {}  # game row index -> Expansion rows in front of it
        pend = []
        for i, r in enumerate(trows):
            if i in real:
                if pend:
                    before[real.index(i)] = pend
                    pend = []
            else:
                pend.append(r)
        out, cells, new, blank = [], 0, 0, collections.Counter()
        for m, mr in enumerate(mrows):
            g = m2g.get(m)
            if g is None:
                row = [mr[col[c]] if c in col else '' for c in th]
                new += 1
                for c in th:
                    if c not in col or (c not in gdecoded and not c.startswith('*')):
                        blank[c] += 1
            else:
                out.extend(before.get(g, []))
                row = list(trows[real[g]])
                gr = grows[g]
                for c in use:
                    a, b = gr[col[c]], mr[col[c]]
                    if not B.same(a, b):
                        row[th.index(c)] = b
                        cells += 1
            out.append(row)
        if pend and len(m2g):
            out.extend(pend)
        dropped = len(grows) - len(set(m2g.values()))
        B.write_txt(excel / (t + '.txt'), th, out)
        report[t] = {'rows': len(mrows), 'matched': len(m2g), 'new': new, 'dropped': dropped, 'cellsChanged': cells,
                     'newRowColumnsLeftEmpty': dict(blank)}
        echo('%-17s rows %5d  matched %5d  new %4d  dropped %4d  cells %6d%s' % (
            t, len(mrows), len(m2g), new, dropped, cells,
            ('  new rows lack: ' + ', '.join(sorted(blank))) if blank and new else ''))

    # label columns the game never compiles, filled on new rows so the .txt reads like the game's
    def rd(t):
        p = excel / (t + '.txt')
        return B.read_txt(p) if p.exists() else game.txt(t)

    names = {}
    item_names = src / 'data' / 'local' / 'lng' / 'strings' / 'item-names.json'
    if item_names.exists():
        for s in json.loads(item_names.read_text(encoding='utf-8-sig')):
            names.setdefault(s['Key'], re.sub('\u00ffc.', '', s.get('enUS', '')).strip())
    label = {}
    for t in ('weapons', 'armor', 'misc'):
        h, rows = rd(t)
        for r in rows:
            r = r + [''] * (len(h) - len(r))
            label.setdefault(r[h.index('code')], r[h.index('name')] or names.get(r[h.index('namestr')], ''))
    filled = collections.Counter()
    if 'misc' in changed:
        h, rows = rd('misc')
        rows = [r + [''] * (len(h) - len(r)) for r in rows]
        rar = {}
        for r in rows:
            if r[0] and r[h.index('rarity')]:
                rar.setdefault(r[h.index('type')], r[h.index('rarity')])
        for r in rows:
            if not r[0]:
                r[0] = names.get(r[h.index('namestr')]) or names.get(r[h.index('code')]) or r[h.index('code')]
                label[r[h.index('code')]] = r[0]
                filled['misc name'] += 1
                if not r[h.index('rarity')]:
                    r[h.index('rarity')] = rar.get(r[h.index('type')], '0')
                    filled['misc rarity'] += 1
        B.write_txt(excel / 'misc.txt', h, rows)
    if 'gamble' in changed:
        h, rows = rd('gamble')
        for r in rows:
            if not r[0]:
                r[0] = label.get(r[1], r[1])
                filled['gamble name'] += 1
        B.write_txt(excel / 'gamble.txt', h, rows)
    if 'lvlprest' in changed:
        h, rows = rd('lvlprest')
        lh, lrows = rd('levels')
        lname = {}
        for r in lrows:
            r = r + [''] * (len(lh) - len(r))
            if r[lh.index('Id')].strip():
                lname[r[lh.index('Id')]] = r[lh.index('LevelName')] or r[0]
        for r in rows:
            if not r[0]:
                r[0] = lname.get(r[h.index('LevelId')], 'new %s' % r[h.index('Def')])
                filled['lvlprest Name'] += 1
        B.write_txt(excel / 'lvlprest.txt', h, rows)
    echo('labels filled: %s' % dict(filled))

    # everything else of the mod, as it is (its .bin tables are replaced by the .txt above)
    n = 0
    for p in src.rglob('*'):
        r = p.relative_to(src)
        low = r.as_posix().lower()
        if p.is_dir() or low.startswith('data/global/excel/') and low.endswith('.bin'):
            continue
        d = out_mpq / r
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, d)
        n += 1
    echo('copied %d other files' % n)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src', help='the extracted mod (a folder with data\\)')
    ap.add_argument('out', help='the mod folder to write <name>.mpq and merge-report.json into')
    ap.add_argument('--name', help='archive folder name (default: the source folder name without .mpq)')
    args = ap.parse_args()
    src, out = Path(args.src), Path(args.out)
    name = args.name or re.sub(r'(?i)(-unpacked)?(\.mpq)?$', '', src.name)
    report = merge(src, out / (name + '.mpq'))
    (out / 'merge-report.json').write_text(json.dumps(report, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
