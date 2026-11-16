"""Installs and updates mods that already are D2RMM mods (mod.json + mod.js, e.g. Relics of
Sanctuary from Nexus), with the same safety as ModConverter's Update for converted data mods.

  - The download (a folder, or a .zip / .7z / .rar) is staged in <D2RMM>\\converter-work, patched,
    run through ModHarness.js, and only then put in place of <D2RMM>\\mods\\<id>. The old folder
    is kept in converter-work\\<id>.previous until the new one is in, and comes back on a failure.
  - The mod's settings stay: D2RMM keys them by the folder name (kept the same) and keeps them in
    <mod>\\config.json, which is carried over.
  - The download is remembered in <mod>\\d2rmm\\native.json. Without --source, --update takes the
    newest download with the same name (Nexus names them "<Name> <nexus id> <version> <date> <x>")
    from the folder the last one was in, the game and D2RMM folders and Downloads.

Patches (applied to every install, so they come back with each update):
  pause-menu  a mod that copies its own global\\ui\\layouts\\pauselayoutgardenhd.json with
              D2RMM.copyFile(..., true) replaces the pause menu every earlier mod built (Item
              Dictionary, Loot Guide, Frankenstein...). The copy is taken out and the mod's own
              button tables are merged into the menu at install time instead, right of the main
              buttons. The mod's own switch for those buttons keeps working.

usage:
  NativeModUpdate.py --game <D2R folder> [--d2rmm <D2RMM folder>] --install <download> [--id <mod id>]
  NativeModUpdate.py --game <D2R folder> [--d2rmm <D2RMM folder>] --update <mod id> [--source <download>]
  add --dry-run to stage, patch and check without touching mods\\
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARCHIVES = ('.zip', '.7z', '.rar')
NEXUS_NAME = re.compile(r'^(?P<name>.+?) (?P<nexus>\d+) (?P<version>\d[\w.\-]*) \d{4}-\d\d-\d\dT')
VANILLA_PAUSE_CHILDREN = {'TransparentBG', 'LogoWidget', 'PauseText', 'PauseTable', 'LootChron Separator',
                          'PauseTableExtra', 'AgeDescriptorImage', 'ViolenceDescriptorImage'}
PATCH_MARK = 'AAMT pause-menu merge'


def log(msg):
    print(msg, flush=True)


# --------------------------------------------------------------------------- places

def find_d2rmm(game):
    for cand in [game] + sorted(p for p in game.iterdir() if p.is_dir()):
        if (cand / 'mods').is_dir() and any((cand / n).exists() for n in ('D2RMM Custom.exe', 'D2RMM.exe', 'types.d.ts')):
            return cand
    return None


def find_7z():
    for p in (shutil.which('7z'), shutil.which('7za'), r'C:\Program Files\7-Zip\7z.exe', r'C:\Program Files (x86)\7-Zip\7z.exe'):
        if p and Path(p).exists():
            return p
    return None


def mod_root(folder, depth=4):
    """The folder under `folder` that holds mod.json and mod.js (the D2RMM mod), or None."""
    if (folder / 'mod.json').is_file() and (folder / 'mod.js').is_file():
        return folder
    if depth <= 0:
        return None
    for c in sorted(x for x in folder.iterdir() if x.is_dir()):
        found = mod_root(c, depth - 1)
        if found:
            return found
    return None


def version_key(text):
    return tuple(int(n) for n in re.findall(r'\d+', str(text or '')))


def read_json(path):
    """JSON as D2R and D2RMM accept it: // and /* */ comments and trailing commas allowed."""
    text = Path(path).read_text(encoding='utf-8-sig')
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        out, i, n, in_str = [], 0, len(text), False
        while i < n:
            ch = text[i]
            if in_str:
                out.append(ch)
                if ch == '\\' and i + 1 < n:
                    out.append(text[i + 1])
                    i += 1
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
                out.append(ch)
            elif text.startswith('//', i):
                while i < n and text[i] != '\n':
                    i += 1
                continue
            elif text.startswith('/*', i):
                i = text.find('*/', i + 2)
                i = n if i < 0 else i + 2
                continue
            else:
                out.append(ch)
            i += 1
        return json.loads(re.sub(r',(\s*[\]}])', r'\1', ''.join(out)))


# --------------------------------------------------------------------------- the download

def stage(source, work, sevenzip):
    """-> (folder holding the mod, folder to delete afterwards or None)."""
    src = Path(source)
    if src.is_dir():
        root = mod_root(src)
        if not root:
            raise SystemExit(f'{src}: no mod.json + mod.js in it - not a D2RMM mod (a data mod goes through ModConverter.py)')
        return root, None
    if not src.is_file() or src.suffix.lower() not in ARCHIVES:
        raise SystemExit(f'{src}: not a folder or a {"/".join(ARCHIVES)} download')
    out = work / ('unpacked-' + re.sub(r'[^\w.\-]+', '_', src.stem))
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    log(f'unpacking {src.name}')
    if src.suffix.lower() == '.zip':
        with zipfile.ZipFile(src) as z:
            z.extractall(out)
    else:
        if not sevenzip:
            raise SystemExit(f'{src.name}: 7-Zip is needed for {src.suffix} (install it, or unpack the download yourself)')
        r = subprocess.run([sevenzip, 'x', '-y', f'-o{out}', str(src)], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f'7-Zip failed on {src.name}:\n{r.stdout[-2000:]}{r.stderr[-2000:]}')
    root = mod_root(out)
    if not root:
        raise SystemExit(f'{src.name}: no mod.json + mod.js in it - not a D2RMM mod')
    return root, out


def newest_download(record, game, d2rmm):
    """The newest download named like the one the mod came from, or None."""
    prefix = record.get('name_prefix')
    if not prefix:
        return None
    dirs = [Path(d) for d in record.get('search', [])] + [game, d2rmm, Path.home() / 'Downloads']
    seen, found = set(), []
    for d in dirs:
        if not d.is_dir() or str(d).lower() in seen:
            continue
        seen.add(str(d).lower())
        for p in d.iterdir():
            if not p.name.lower().startswith(prefix.lower()):
                continue
            if p.is_file() and p.suffix.lower() not in ARCHIVES:
                continue
            m = NEXUS_NAME.match(p.stem if p.is_file() else p.name)
            version = m.group('version') if m else None
            if p.is_dir():
                root = mod_root(p)
                if not root:
                    continue
                try:
                    version = read_json(root / 'mod.json').get('version') or version
                except Exception:
                    pass
            found.append((version_key(version), p.stat().st_mtime, p))
    if not found:
        return None
    found.sort(key=lambda t: (t[0], t[1]))
    return found[-1][2]


# --------------------------------------------------------------------------- patches

COPY_CALL = re.compile(r"""D2RMM\.copyFile\(\s*(['"])(?P<src>[^'"]+)\1\s*,\s*(['"])global(?:\\\\|/)ui(?:\\\\|/)layouts\3\s*,\s*true\s*\)\s*;?""")

MERGE_JS = r"""
  // --- %(mark)s (NativeModUpdate.py, redone on every update) ---
  // The mod's copy of pauselayoutgardenhd.json would replace the pause menu that every mod above
  // it built. Its own button tables are added to that menu instead, right of the main buttons
  // (below anything another mod already put there).
  (function aamtMergePauseMenu(added) {
    const file = 'global\\ui\\layouts\\pauselayoutgardenhd.json';
    const layout = D2RMM.readJson(file);
    if (!layout || !Array.isArray(layout.children)) return;
    const names = new Set(added.map(w => w.name));
    layout.children = layout.children.filter(c => !names.has(c.name));
    const rect = w => (w.fields && w.fields.rect) || {};
    const width = w => ((w.fields && w.fields.columns) || []).reduce((s, c) => s + (c.width || 0), 0) || 658;
    const bottom = w => (rect(w).y || 0) + ((w.children || []).length * ((w.fields && w.fields.rowHeight) || 140));
    const main = layout.children.find(c => c.name === 'PauseTable');
    const left = main ? (rect(main).x || -329) + width(main) + 70 : 400;
    let y = main ? (rect(main).y || -340) : -340;
    layout.children
      .filter(c => c.type === 'TableWidget' && (rect(c).x || 0) >= left - 10)
      .forEach(c => { y = Math.max(y, bottom(c) + 20); });
    added.forEach(w => {
      const copy = JSON.parse(JSON.stringify(w));
      copy.fields = Object.assign({}, copy.fields, { anchor: { x: 0.5, y: 0.5 }, rect: { x: left, y: y } });
      layout.children.push(copy);
      y = bottom(copy) + 20;
    });
    D2RMM.writeJson(file, layout);
  })(%(tables)s);
  // --- end %(mark)s ---
"""


def patch_pause_menu(mod):
    """-> description of what was done, or None when the mod does not need it."""
    js_path = mod / 'mod.js'
    js = js_path.read_text(encoding='utf-8-sig')
    if PATCH_MARK in js:
        return 'pause-menu: already merged'
    m = COPY_CALL.search(js)
    if not m:
        return None
    layout_dir = mod / m.group('src').replace('\\\\', '/').replace('\\', '/')
    pause = layout_dir / 'pauselayoutgardenhd.json'
    if not pause.is_file():
        return None
    tables = [c for c in read_json(pause).get('children', [])
              if c.get('type') == 'TableWidget' and c.get('name') not in VANILLA_PAUSE_CHILDREN]
    keep = mod / 'd2rmm' / 'original-pauselayoutgardenhd.json'
    keep.parent.mkdir(exist_ok=True)
    shutil.move(str(pause), str(keep))
    if not tables:
        return 'pause-menu: the copy changed no buttons, left out'
    code = MERGE_JS % {'mark': PATCH_MARK, 'tables': json.dumps(tables, ensure_ascii=False)}
    js = js[:m.end()] + '\n' + code + js[m.end():]
    js_path.write_text(js, encoding='utf-8')
    return 'pause-menu: ' + ', '.join(t.get('name', '?') for t in tables) + ' merged instead of copying the whole menu'


PATCHES = [patch_pause_menu]


# --------------------------------------------------------------------------- check

def check(mod, game, work):
    """Runs the mod alone in ModHarness.js; raises on a script error or a lost pause menu."""
    out = work / 'harness-out'
    if out.exists():
        shutil.rmtree(out)
    cmd = ['node', str(HERE / 'ModHarness.js'), '--game', str(game), '--python', sys.executable, '--out', str(out), str(mod)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    text = (r.stdout or '') + (r.stderr or '')
    lines = text.strip().splitlines()
    errors = [ln for ln in lines if re.search(r'Error\b|threw|FAILED', ln) and not ln.lstrip().startswith('at ')]
    tail = '\n'.join((errors[:4] or []) + lines[-3:])
    if r.returncode not in (0, 1):
        raise SystemExit(f'the mod failed in the test run (exit {r.returncode}):\n{tail}')
    problems = re.search(r'(\d+) PROBLEM\(S\)', text)
    log(f'test run: script ran, {problems.group(1) if problems else 0} harness problem(s) (the mod\'s own, shown with Test-D2RMod.ps1)')
    pause = out / 'global' / 'ui' / 'layouts' / 'pauselayoutgardenhd.json'
    js = (mod / 'mod.js').read_text(encoding='utf-8-sig')
    if PATCH_MARK in js and pause.is_file():
        names = {c.get('name') for c in read_json(pause).get('children', [])}
        if not {'PauseTable', 'PauseTableExtra'} <= names:
            raise SystemExit('the merged pause menu lost the game\'s own buttons')
    shutil.rmtree(out, ignore_errors=True)


# --------------------------------------------------------------------------- install

def replace_dir(src, dst):
    try:
        os.replace(src, dst)
    except OSError:
        shutil.copytree(src, dst)
        shutil.rmtree(src, ignore_errors=True)


def install(source, mod_id, d2rmm, game, record, dry_run):
    work = d2rmm / 'converter-work'
    work.mkdir(exist_ok=True)
    root, unpacked = stage(source, work, find_7z())
    meta = read_json(root / 'mod.json')
    mod_id = mod_id or record.get('id') or root.name
    target = d2rmm / 'mods' / mod_id
    log(f'{meta.get("name", mod_id)} {meta.get("version", "?")} by {meta.get("author", "?")} -> mods\\{mod_id}')

    staged = work / f'{mod_id}.new'
    if staged.exists():
        shutil.rmtree(staged)
    shutil.copytree(root, staged, ignore=shutil.ignore_patterns('config.json', 'd2rmm'))
    if unpacked:
        shutil.rmtree(unpacked, ignore_errors=True)
    applied = [d for d in (p(staged) for p in PATCHES) if d]
    for d in applied:
        log('patch ' + d)
    check(staged, game, work)

    src = Path(source)
    m = NEXUS_NAME.match(src.stem if src.is_file() else src.name)
    if not m and src.is_dir():
        m = NEXUS_NAME.match(src.parent.name)
    download = src if src.is_file() or not m or NEXUS_NAME.match(src.name) else src.parent
    record = dict(record, id=mod_id, source=str(download.resolve()), version=meta.get('version'),
                  name=meta.get('name'), patches=applied, installed=time.strftime('%Y-%m-%d %H:%M'))
    if m:
        record.update(name_prefix=m.group('name'), nexus_id=m.group('nexus'))
    record['search'] = sorted({str(download.resolve().parent)} | set(record.get('search', [])))
    (staged / 'd2rmm').mkdir(exist_ok=True)
    (staged / 'd2rmm' / 'native.json').write_text(json.dumps(record, indent=2), encoding='utf-8')

    if dry_run:
        log(f'dry run: left in {staged}')
        return
    previous = work / f'{mod_id}.previous'
    if previous.exists():
        shutil.rmtree(previous)
    if target.exists():
        if (target / 'config.json').is_file():
            shutil.copy2(target / 'config.json', staged / 'config.json')
            log('settings kept (config.json)')
        replace_dir(target, previous)
    try:
        replace_dir(staged, target)
    except Exception:
        if previous.exists() and not target.exists():
            replace_dir(previous, target)
            log('install failed, the old version is back')
        raise
    shutil.rmtree(previous, ignore_errors=True)
    log(f'installed in {target}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', required=True)
    ap.add_argument('--d2rmm')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--install', metavar='DOWNLOAD')
    g.add_argument('--update', metavar='MOD_ID')
    ap.add_argument('--source', help='with --update: this download instead of the newest one')
    ap.add_argument('--id', help='with --install: the folder name in mods\\ (default: the mod folder\'s own name)')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    game = Path(a.game)
    d2rmm = Path(a.d2rmm) if a.d2rmm else find_d2rmm(game)
    if not d2rmm or not (d2rmm / 'mods').is_dir():
        raise SystemExit('D2RMM folder not found: pass --d2rmm')

    if a.install:
        record = {}
        if a.id and (d2rmm / 'mods' / a.id / 'd2rmm' / 'native.json').is_file():
            record = read_json(d2rmm / 'mods' / a.id / 'd2rmm' / 'native.json')
        install(a.install, a.id, d2rmm, game, record, a.dry_run)
        return
    rec_path = d2rmm / 'mods' / a.update / 'd2rmm' / 'native.json'
    if not rec_path.is_file():
        raise SystemExit(f'mods\\{a.update} was not installed with this tool (no d2rmm\\native.json): use --install <download> --id {a.update}')
    record = read_json(rec_path)
    source = a.source or newest_download(record, game, d2rmm) or record.get('source')
    if not source or not Path(source).exists():
        raise SystemExit('no download found: pass --source')
    log(f'source: {source}')
    install(source, a.update, d2rmm, game, record, a.dry_run)


if __name__ == '__main__':
    main()
