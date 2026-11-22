"""Turns a D2RMM mod that REPLACES whole tables or string files into one that patches them.

Mods like "Better and New Unique Items" (copyFile('data', 'data')) or a preset copy of ui.json
put their whole copy of a game table over whatever the mods above them wrote, so every change
those mods made to the same file is lost. This converter keeps the mod as it is (its own mod.js,
settings and files) and wraps its mod.js:

  - every table (global\\excel\\**.txt) and string file (local\\lng\\strings*\\*.json) the mod
    ships is compared with the game's own copy; the difference is stored as a row patch in
    <mod>\\d2rmm\\patches\\<the file's path in the mod>.json (the same patch format and merge code
    as ConvertDataMod.py, 'keep' rows: rows stay in place, new rows go at the end, numbers that
    point at rows move with them);
  - the mod's mod.js is moved to <mod>\\d2rmm\\original-mod.js and the new mod.js runs it with a
    D2RMM whose copyFile, when a copy includes one of those files, puts the file back as it was
    and applies the mod's patch to it instead. Everything else the mod does runs unchanged.

So the mod's own changes still win cell by cell ("Load order > Conflicts" = mod), but the rows,
cells and strings it does not touch keep what the mods above it wrote, and the mods below it
patch the result as before.

    python ConvertReplaceMod.py --game <D2R folder> --mod <D2RMM>\\mods\\<mod> [--check]
    python ConvertReplaceMod.py --game <D2R folder> --mod <mod> --undo

Rerun after the mod updates (it reads d2rmm\\original-mod.js when it is there, so it never wraps
its own wrapper). --undo puts the original mod.js back and removes d2rmm\\.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ConvertDataMod as C  # noqa: E402

GAME_PATH = re.compile(r'(?i)(?:^|/)((?:global/excel/(?:base/)?[^/]+\.txt)|(?:local/lng/strings(?:-legacy)?/[^/]+\.json))$')
MARK = '/* ConvertReplaceMod wrapper */'

from JsonPatch import JSON_PATH, json_patch, json_apply, read_json_file  # noqa: E402



def js_segment(start, end):
    s = C.MOD_JS
    a = s.index(start)
    b = s.index(end, a)
    return s[a:b]


def wrapper_js(mod_id, name, patched, original):
    # The merge code is ConvertDataMod's own mod.js code, so both stay the same.
    part_a = js_segment('function readPatch(path) {', '// My mod list')
    part_b = js_segment('function clash(path, what) {', '// Item property columns')
    return MARK + '''
/**
 * ''' + name + ''' - wrapped by ConvertReplaceMod.py (Ai assisted toolkit, Tools\\DiabloII).
 *
 * The mod's own mod.js is in d2rmm\\original-mod.js and runs below unchanged, except that when it
 * copies one of the ''' + str(len(patched)) + ''' tables / string files listed in PATCHED, the file is put back as
 * the mods above left it and the mod's changes are merged into it row by row instead of
 * replacing it. Rerun the converter instead of editing this file.
 */
const MOD_ID = ''' + json.dumps(mod_id) + ''';
const PATCHES = 'd2rmm\\\\patches';
const SCRATCH = 'd2rmm-convert\\\\' + MOD_ID + '.json';
const CLASHES = {};
const CELLS = 'mod';
const cellsOf = () => CELLS;

''' + part_a + part_b + '''
// file in the mod (lower case, backslashes) -> [file in the mod, game path, 'table' | 'strings' | 'json']
const PATCHED = ''' + json.dumps(patched, ensure_ascii=False, indent=1) + ''';
const norm = (p) => String(p).replace(/\\//g, '\\\\').replace(/\\\\+$/, '').toLowerCase();
const MERGED = [];
function patchedUnder(src) {
  const s = norm(src);
  return Object.keys(PATCHED).filter((k) => k === s || k.startsWith(s + '\\\\')).map((k) => PATCHED[k]);
}
function readOr(kind, path) {
  try {
    return kind === 'table' ? D2RMM.readTsv(path, { removeCarriageReturns: true }) : D2RMM.readJson(path);
  } catch (e) {
    return null;
  }
}
const SHIM = {};
Object.getOwnPropertyNames(D2RMM).concat(Object.keys(Object.getPrototypeOf(D2RMM) || {})).forEach((k) => {
  if (!(k in SHIM)) SHIM[k] = typeof D2RMM[k] === 'function' ? D2RMM[k].bind(D2RMM) : D2RMM[k];
});
SHIM.copyFile = (src, dst, overwrite) => {
  const hits = overwrite === false ? [] : patchedUnder(src);
  const was = hits.map(([rel, game, kind]) => [rel, game, kind, readOr(kind, game)]);
  const result = D2RMM.copyFile(src, dst, overwrite);
  was.forEach(([rel, game, kind, before]) => {
    if (!before) return; // nothing to merge into: the copy stays (json: readJson failed)
    if (kind === 'table') {
      D2RMM.writeTsv(game, before);
      applyTableKeep(game, readPatch(rel));
    } else if (kind === 'json') {
      D2RMM.writeJson(game, applyJsonPatch(before, readPatch(rel)));
    } else {
      D2RMM.writeJson(game, before);
      applyStrings(game, readPatch(rel));
    }
    MERGED.push(game);
  });
  return result;
};

(function (D2RMM) {
''' + original.rstrip() + '''
})(SHIM);

D2RMM.writeTxt(SCRATCH, '');
if (MERGED.length) console.log(MOD_ID + ': merged instead of replaced: ' + MERGED.join(', '));
const clashed = Object.keys(CLASHES);
if (clashed.length) {
  console.log(MOD_ID + ': cells/strings a mod above changed as well (this mod\\'s values used): ' +
    clashed.map((p) => p.slice(p.lastIndexOf('\\\\') + 1) + ' ' + CLASHES[p][0]).join(', '));
}
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--game', default=os.environ.get('D2R_PATH'), required=not os.environ.get('D2R_PATH'))
    ap.add_argument('--mod', required=True, help="the mod's folder in D2RMM's mods folder")
    ap.add_argument('--d2rmm', help="D2RMM's folder (default: two levels above the mod)")
    ap.add_argument('--cache', help='game file cache (default %%LOCALAPPDATA%%\\D2RModAssets\\vanilla)')
    ap.add_argument('--python', default=sys.executable)
    ap.add_argument('--check', action='store_true', help='run the wrapped mod alone in ModHarness afterwards')
    ap.add_argument('--undo', action='store_true', help='put the original mod.js back')
    args = ap.parse_args()
    mod = Path(args.mod).resolve()
    meta = mod / 'd2rmm'
    original_file = meta / 'original-mod.js'
    if args.undo:
        if not original_file.exists():
            raise SystemExit('%s was not converted (no d2rmm\\original-mod.js)' % mod.name)
        shutil.copy2(original_file, mod / 'mod.js')
        shutil.rmtree(meta)
        print('%s: original mod.js back, d2rmm\\ removed' % mod.name)
        return
    if (meta / 'convert.json').exists():
        raise SystemExit('%s is a converted data mod (ConvertDataMod.py); it patches already' % mod.name)
    current = (mod / 'mod.js').read_text(encoding='utf-8-sig')
    if original_file.exists():
        original = original_file.read_text(encoding='utf-8-sig')
    elif current.startswith(MARK):
        raise SystemExit('mod.js is a wrapper but d2rmm\\original-mod.js is gone')
    else:
        original = current

    files = []
    for f in sorted(mod.rglob('*')):
        if not f.is_file():
            continue
        rel = f.relative_to(mod).as_posix()
        if rel.lower().startswith(('d2rmm/', 'dev/', '.git/')):
            continue
        m = GAME_PATH.search(rel) or JSON_PATH.search(rel)
        if m:
            files.append((rel, m.group(1).lower()))
    if not files:
        raise SystemExit('%s ships no tables, string files or game JSON: nothing to convert' % mod.name)
    game = Path(args.game)
    cache = Path(args.cache) if args.cache else Path(os.environ.get('LOCALAPPDATA', tempfile.gettempdir())) / 'D2RModAssets' / 'vanilla'
    C.use_d2rmm_casclib(Path(args.d2rmm) if args.d2rmm else mod.parent.parent)
    vanilla = C.fetch_vanilla(game, cache, sorted({g for _, g in files}), args.python)

    patches = meta / 'patches'
    if patches.exists():
        shutil.rmtree(patches)
    patched = {}
    report = {'patched': [], 'kept': {}}
    for rel, gpath in files:
        van = vanilla.get(gpath)
        src = mod / rel
        if van is None:
            report['kept'][rel] = 'the game has no such file (a new file: copied as it is)'
            continue
        if van.read_bytes() == src.read_bytes():
            report['kept'][rel] = 'the same as the game'
            continue
        if JSON_PATH.search(gpath) and not GAME_PATH.search(gpath):
            m, v = read_json_file(src), read_json_file(van)
            if m is None or v is None:
                report['kept'][rel] = 'not JSON: replaced as before'
                continue
            patch = json_patch(v, m)
            if patch is None:
                report['kept'][rel] = 'the same as the game (as JSON)'
                continue
            if json_apply(v, patch) != m:
                report['kept'][rel] = 'the patch does not rebuild the file: replaced as before'
                continue
            st = {'jsonPatch': len(json.dumps(patch))}
            kind = 'json'
        elif C.is_table(gpath):
            m, v = C.read_table(src), C.read_table(van)
            if m is None or v is None:
                report['kept'][rel] = 'not UTF-8: replaced as before'
                continue
            disable = C.DISABLE_COLUMN.get(gpath.rsplit('/', 1)[-1])
            patch, st = C.table_patch(v, m, trim=True, duplicates='content', disable=disable)
            if patch is None:
                report['kept'][rel] = '%s: replaced as before' % st
                continue
            if tuple(C.apply_table(v, patch)) != tuple(m):
                report['kept'][rel] = 'the patch does not rebuild the file: replaced as before'
                continue
            kind = 'table'
        else:
            m, v = C.read_strings(src), C.read_strings(van)
            if m is None or v is None:
                report['kept'][rel] = 'not a list of {Key, ...} entries: replaced as before'
                continue
            patch, st = C.strings_patch(v, m)
            if C.by_key(C.apply_strings(v, patch)) != C.by_key(m):
                report['kept'][rel] = 'repeated Keys in an order the patch cannot rebuild: replaced as before'
                continue
            kind = 'strings'
        out = patches / (rel + '.json')
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(patch, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        win_rel = rel.replace('/', '\\')
        patched[win_rel.lower()] = [win_rel, gpath.replace('/', '\\'), kind]
        report['patched'].append({'file': rel, 'game': gpath, **st})

    meta.mkdir(exist_ok=True)
    if not original_file.exists():
        original_file.write_text(original, encoding='utf-8')
    mod_json = json.loads((mod / 'mod.json').read_text(encoding='utf-8-sig'))
    (mod / 'mod.js').write_text(wrapper_js(mod.name, mod_json.get('name') or mod.name, patched, original), encoding='utf-8')
    (meta / 'replace.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    print('%s: %d file(s) now merged row by row instead of replaced:' % (mod.name, len(patched)))
    for p in report['patched']:
        print('  %s (%s)' % (p['file'], ', '.join('%s %s' % (v, k) for k, v in p.items() if k not in ('file', 'game'))))
    for rel, why in report['kept'].items():
        print('  left as it was: %s (%s)' % (rel, why))
    if args.check:
        harness = HERE / 'ModHarness.js'
        r = subprocess.run(['node', '--max-old-space-size=8192', str(harness), '--game', str(game), '--keep-going', str(mod)],
                           capture_output=True, text=True)
        lines = [l for l in r.stdout.splitlines() if 'FAILED' in l or 'merged instead' in l or 'PROBLEM(S)' in l or 'no problems' in l]
        print('check (ModHarness, the mod alone):')
        for l in lines[:12]:
            print('  ' + l.strip()[:300])


if __name__ == '__main__':
    main()
