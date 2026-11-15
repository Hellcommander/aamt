"""Gets the game files a Diablo II: Resurrected mod needs, straight from the archive.

Read-only against the game. Used by ModHarness.js (Test-D2RMod.ps1), which asks
for files as a mod script reads them, and by hand to look things up while
designing a mod.

usage:
  ModAssets.py fetch  --game <D2R folder> --out <folder> [--deps] <path> ...   (or "-" = paths on stdin)
  ModAssets.py exists --game <D2R folder> <path> ...                           (or "-")
  ModAssets.py deps   --game <D2R folder> <hd definition path> ...
  ModAssets.py show   --game <D2R folder> <table> <row name>[,<row name>...] [--base]
  ModAssets.py find   --game <D2R folder> <table> <regex> [--base] [--cols a,b,c]
  ModAssets.py ls     --game <D2R folder> <regex>

  fetch   writes each file under <folder>\\<path> and prints {"path": size or null}.
          --deps also fetches what an HD definition (.json under hd/) names in
          `dependencies`, and the textures those particle files name.
  exists  prints {"path": true/false}.
  deps    prints the dependency tree of HD definitions: definition -> particles,
          models, ... -> textures named inside particle files.
  show    prints the non-empty columns of rows of global/excel/<table>.txt
          (skills, missiles, monstats, skilldesc, states, ...), matched on the
          table's first column, case-insensitive.
  find    rows whose text matches the regex: first column, or --cols.
  ls      archive file names that match the regex.

Paths are archive paths with forward slashes, with or without a leading "data/".
--game can come from D2R_PATH.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from d2r_casc import D2RArchive  # noqa: E402

# Paths a compiled file (.particles, .model ...) names inside itself.
# Strings sit back to back in those files, so the match stops at the first extension.
EMBEDDED_PATH = re.compile(rb'data/hd/[A-Za-z0-9_/\-]+?\.(?:texture|particles|model|skeleton|animation)')


def norm(path):
    p = path.replace('\\', '/').strip()
    if p.lower().startswith('data/'):
        p = p[5:]
    return p.lower()


def read_paths(args):
    if args == ['-']:
        return [norm(line) for line in sys.stdin.read().splitlines() if line.strip()]
    return [norm(p) for p in args]


def parse_jsonc(data):
    """HD definitions are JSON, sometimes with a BOM, comments or trailing commas."""
    text = data.decode('utf-8-sig')
    out, i, in_str = [], 0, False
    while i < len(text):
        c = text[i]
        if in_str:
            out.append(c)
            if c == '\\':
                i += 1
                out.append(text[i])
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            out.append(c)
        elif text.startswith('//', i):
            while i < len(text) and text[i] != '\n':
                i += 1
            out.append('\n')
        elif text.startswith('/*', i):
            i = text.index('*/', i) + 1
        else:
            out.append(c)
        i += 1
    return json.loads(re.sub(r',(\s*[}\]])', r'\1', ''.join(out)))


def direct_deps(path, data):
    """Archive paths a file names: `dependencies` of an HD definition, or paths embedded in a binary."""
    found = []
    if path.endswith('.json') and path.startswith('hd/'):
        try:
            doc = parse_jsonc(data)
        except (ValueError, UnicodeDecodeError):
            return found
        if isinstance(doc, dict):
            for group in (doc.get('dependencies') or {}).values():
                for dep in group or []:
                    if isinstance(dep, dict) and dep.get('path'):
                        found.append(norm(dep['path']))
    elif path.endswith(('.particles', '.model')):
        found = [norm(m.decode('latin1')) for m in EMBEDDED_PATH.findall(data)]
    seen, out = set(), []
    for p in found:
        if p not in seen and p != path:
            seen.add(p)
            out.append(p)
    return out


def read_any(archive, path):
    """Reads a file; a model named without its level of detail is stored as `_lod0.model`."""
    data = archive.read(path)
    if data is None and path.endswith('.model') and not path.endswith('_lod0.model'):
        data = archive.read(path[:-6] + '_lod0.model')
    return data


def table(archive, name, base):
    path = f"global/excel/{'base/' if base else ''}{name}.txt"
    data = archive.read(path)
    if data is None:
        raise SystemExit(f'no such table: {path}')
    lines = data.decode('latin1').split('\n')
    headers = lines[0].rstrip('\r').split('\t')
    rows = [dict(zip(headers, line.rstrip('\r').split('\t'))) for line in lines[1:] if line.strip()]
    return headers, rows


def show_row(index, row):
    return f'[{index}] ' + ' '.join(f'{k}={v}' for k, v in row.items() if v != '' and not k.startswith('*'))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['fetch', 'exists', 'deps', 'show', 'find', 'ls'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('--game', default=os.environ.get('D2R_PATH'))
    ap.add_argument('--casclib', default=None)
    ap.add_argument('--out')
    ap.add_argument('--deps', action='store_true')
    ap.add_argument('--base', action='store_true', help='the classic-rules table (global/excel/base)')
    ap.add_argument('--cols', default='')
    a = ap.parse_args()
    if not a.game or not os.path.isdir(a.game):
        raise SystemExit('Pass --game (or set D2R_PATH) to the folder that contains D2R.exe.')

    with D2RArchive(a.game.replace('/', '\\'), a.casclib) as archive:
        if a.command == 'fetch':
            if not a.out:
                raise SystemExit('fetch needs --out')
            result, queue, seen = {}, read_paths(a.args), set()
            while queue:
                path = queue.pop(0)
                if path in seen:
                    continue
                seen.add(path)
                data = read_any(archive, path)
                result[path] = None if data is None else len(data)
                if data is None:
                    continue
                target = os.path.join(a.out, *path.split('/'))
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, 'wb') as f:
                    f.write(data)
                if a.deps:
                    queue.extend(direct_deps(path, data))
            print(json.dumps(result))
        elif a.command == 'exists':
            print(json.dumps({p: read_any(archive, p) is not None for p in read_paths(a.args)}))
        elif a.command == 'deps':
            def walk(path, depth, seen):
                data = read_any(archive, path)
                print('  ' * depth + path + ('' if data is not None else '   MISSING') + (f'   {len(data)} bytes' if data else ''))
                if data is None or path in seen:
                    return
                seen.add(path)
                for dep in direct_deps(path, data):
                    walk(dep, depth + 1, seen)
            for p in read_paths(a.args):
                walk(p, 0, set())
        elif a.command == 'show':
            headers, rows = table(archive, a.args[0], a.base)
            wanted = [n.strip().lower() for n in ','.join(a.args[1:]).split(',') if n.strip()]
            for name in wanted:
                hits = [(i, r) for i, r in enumerate(rows) if r[headers[0]].lower() == name]
                if not hits:
                    print(f'-- no row "{name}" in {a.args[0]}')
                for i, r in hits:
                    print(show_row(i, r))
                    print()
        elif a.command == 'find':
            headers, rows = table(archive, a.args[0], a.base)
            pattern = re.compile(a.args[1], re.I)
            cols = [c for c in a.cols.split(',') if c] or [headers[0]]
            for i, r in enumerate(rows):
                if any(pattern.search(r.get(c, '')) for c in cols):
                    print(f'[{i}] {r[headers[0]]}' + ''.join(f' {c}={r.get(c, "")}' for c in cols if c != headers[0]))
        elif a.command == 'ls':
            pattern = re.compile(a.args[0], re.I)
            for name in archive.list():
                if pattern.search(name):
                    print(name)


if __name__ == '__main__':
    main()
