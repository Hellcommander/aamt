"""Embeds the plain game's template rows in skill-page mods, so total conversions do not leak in.

    python StockRows.py --game <D2R folder> <mod folder> [<mod folder> ...] [--check]

A skill-page mod builds its new rows (skills, descriptions, missiles, states, monsters, items) from
copies of stock rows and fills in its own columns. Every column it leaves alone keeps what the
installed table has, so a total conversion installed before it (Frankenstein, Reimagined...) that
reworked those stock rows leaks its edits into the new skills. The fix is to copy the plain game's
rows instead: StockRows.js has the helper (stockRow), and this script puts it into each mod.js with
the rows that mod copies.

For each mod.js this writes two marked blocks, in front of `function findRow(` the first time:
  // <stock-rows-code> ... // </stock-rows-code>   the code of StockRows.js
  // <stock-rows> ... // </stock-rows>             STOCK_ROWS / STOCK_ROWS_BASE for the mod
The mod's own template copies (its cloneRow) must ask stockRow first and fall back to the live
row when it returns undefined, and set `stockSet` to 'main' or 'base' for each set of tables.

Which rows a mod copies is found by running it (ModHarness.js) on the plain game with the option
recordStockRows on, once with its default options and once for each other value of each checkbox
and list option in its mod.json (templates can depend on options). stockRow logs every name it is
asked for; the rows come from the game's own tables in the harness cache. Base (classic-rules)
rows are stored only where they differ from the main ones (null: the base table has no such row).
Rerun after a game patch or after a mod starts copying other rows; --check only reports whether
the blocks are up to date (it still runs the mod).
"""
import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARNESS = HERE / 'ModHarness.js'
RECORD = re.compile(r'^\[stock-rows\] ([^\t]*)\t([^\t]*)\t(.*)$')


def load(path):
    """A table the way ModHarness.js (and D2RMM) reads it: latin-1, cells by header, '' for missing."""
    if not path.exists():
        return None
    lines = re.split(r'\r?\n', path.read_bytes().decode('latin-1'))
    head = lines[0].split('\t')
    rows = []
    for line in lines[1:]:
        if line == '':
            continue
        cells = line.split('\t')
        rows.append({h: (cells[i] if i < len(cells) else '') for i, h in enumerate(head)})
    return rows


def find(rows, col, name):
    v = name.lower()
    return next((r for r in rows or [] if (r.get(col) or '').lower() == v), None)


def variants(mod):
    """Option sets to run the mod with: defaults, then each other checkbox / list value."""
    meta = json.loads((mod / 'mod.json').read_text(encoding='utf-8'))
    out = [[]]

    def each(c):
        if c.get('id'):
            if c.get('type') == 'checkbox':
                out.extend([['%s=true' % c['id']], ['%s=false' % c['id']]])
            elif c.get('type') == 'select':
                out.extend([['%s=%s' % (c['id'], o['value'])] for o in c.get('options', []) if 'value' in o])
        for child in c.get('children', []) or []:
            each(child)
    for c in meta.get('config', []) or []:
        each(c)
    return out


def record(mod, args):
    """(file, column, name) of every row the mod asks stockRow for, over all option sets."""
    def run(extra):
        cmd = ['node', str(HARNESS), '--game', args.game, '--cache', args.cache, '--python', args.python,
               '--max-page', '99', '--keep-going', '--config', 'recordStockRows=true']
        for e in extra:
            cmd += ['--config', e]
        r = subprocess.run(cmd + [str(mod)], capture_output=True, text=True, encoding='utf-8', errors='replace')
        out = (r.stdout or '') + (r.stderr or '')
        if r.returncode == 2 or 'the script threw' in out:
            line = next((l for l in out.splitlines() if 'the script threw' in l), 'exit %s' % r.returncode)
            print('  warning: %s with %s: %s' % (mod.name, ' '.join(extra) or 'default options', line.strip()))
        return [m.groups() for m in map(RECORD.match, out.splitlines()) if m]
    runs = variants(mod)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(run, runs))
    seen = {}
    for rec in results:
        for table, col, name in rec:
            seen.setdefault((table, col, name.lower()), (table, col, name))
    return list(seen.values()), len(runs)


def stock_block(mod, records, cache):
    tables = {}
    main_rows, base_rows, notes = {}, {}, []
    for table, col, name in records:
        if table in ('', 'undefined'):
            raise SystemExit('%s: stockRow got key column %r (row %r) without a table; pass the file' % (mod.name, col, name))
        if table not in tables:
            tables[table] = (load(cache / 'global/excel' / (table + '.txt')), load(cache / 'global/excel/base' / (table + '.txt')))
        main_t, base_t = tables[table]
        if main_t is None:
            raise SystemExit('%s: no %s.txt in the cache %s' % (mod.name, table, cache))
        row = find(main_t, col, name)
        keep = {k: v for k, v in row.items() if v != ''} if row else None
        brow = find(base_t, col, name) if base_t is not None else None
        bkeep = {k: v for k, v in brow.items() if v != ''} if brow else None
        if not row and not brow:
            notes.append('%s %r is not in the game\'s %s.txt (copied as it is now)' % (col, name, table))
            continue
        key = (row or brow)[col]
        if row:
            main_rows.setdefault(table, {})[key] = keep
        if base_t is not None and bkeep != keep:
            base_rows.setdefault(table, {})[key] = bkeep

    def dump(obj):
        lines = ['{']
        for table in sorted(obj):
            lines.append('  %s: {' % json.dumps(table))
            for name in sorted(obj[table], key=lambda n: (n.lower(), n)):
                lines.append('    %s: %s,' % (json.dumps(name), json.dumps(obj[table][name], separators=(', ', ': '))))
            lines.append('  },')
        lines.append('}')
        return '\n'.join(lines)

    block = ('// <stock-rows> written by StockRows.py (Ai assisted toolkit, Tools\\DiabloII) from the game\'s own\n'
             '// tables; do not edit by hand. The plain game\'s rows this mod copies (non-empty columns), found by\n'
             '// running the mod on the plain game. STOCK_ROWS_BASE: classic-rules rows that differ from the main\n'
             '// ones (null: the base table has no such row).\n'
             'const STOCK_ROWS = ' + dump(main_rows) + ';\n'
             'const STOCK_ROWS_BASE = ' + dump(base_rows) + ';\n'
             '// </stock-rows>\n')
    return block, sum(len(v) for v in main_rows.values()), sum(len(v) for v in base_rows.values()), notes


def code_block():
    code = (HERE / 'StockRows.js').read_text(encoding='utf-8').rstrip() + '\n'
    return '// <stock-rows-code> written by StockRows.py from StockRows.js; do not edit here.\n' + code + '// </stock-rows-code>\n'


EMPTY = '// <stock-rows>\nconst STOCK_ROWS = {};\nconst STOCK_ROWS_BASE = {};\n// </stock-rows>\n'


def replace_block(text, tag, block):
    pattern = re.compile(r'// <%s>.*?// </%s>\n' % (re.escape(tag), re.escape(tag)), re.S)
    if pattern.search(text):
        return pattern.sub(lambda m: block, text, count=1)
    at = text.find('function findRow(')
    if at < 0:
        raise SystemExit('no "function findRow(" to put the %s block in front of' % tag)
    return text[:at] + block + '\n' + text[at:]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mods', nargs='+')
    ap.add_argument('--game', required=True)
    ap.add_argument('--cache', default=os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'D2RModAssets', 'vanilla'))
    ap.add_argument('--python', default=sys.executable)
    ap.add_argument('--jobs', type=int, default=4, help='harness runs at the same time')
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    stale = 0
    for m in args.mods:
        mod = Path(m).resolve()
        path = mod / 'mod.js'
        raw = path.read_bytes().decode('utf-8')
        eol = '\r\n' if '\r\n' in raw else '\n'  # keep the file's line endings
        text = raw.replace('\r\n', '\n')
        disk = text
        new = replace_block(text, 'stock-rows-code', code_block())
        if not re.search(r'// <stock-rows>[ \n].*?// </stock-rows>\n', new, re.S):
            new = replace_block(new, 'stock-rows', EMPTY)
        if not args.check and new != disk:
            path.write_bytes(new.replace('\n', eol).encode('utf-8'))  # the run below needs stockRow
            disk = new
        if 'stockRow(' not in new.split('// </stock-rows-code>')[-1]:
            print('%s: warning: nothing calls stockRow yet (wire the template copies to it, see StockRows.js)' % path)
        records, runs = record(mod, args)
        block, count, based, notes = stock_block(mod, records, Path(args.cache))
        for n in notes:
            print('  note: %s' % n)
        new = replace_block(new, 'stock-rows', block)
        what = '%d rows, %d base differences, %d option sets' % (count, based, runs)
        if not args.check and new != disk:
            path.write_bytes(new.replace('\n', eol).encode('utf-8'))
        if new == text:
            print('%s: up to date (%s)' % (path, what))
        elif args.check:
            stale += 1
            print('%s: OUT OF DATE (%s)' % (path, what))
        else:
            print('%s: written (%s)' % (path, what))
    return 1 if stale else 0


if __name__ == '__main__':
    sys.exit(main())
