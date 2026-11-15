"""Puts the shared tree placement code and the stock cell table into skill-page mods.

    python TreePlacement.py --game <D2R folder> <mod folder> [<mod folder> ...] [--check]

The skill-page mods (second pages of a class tab, drawn by the SkillTab4 plugin) put each new
skill in the tree cell of a stock skill of the parent tab (its `slot`). TreePlacement.js decides
the cells; it also copes with mods that rework the class trees (total conversions). For that it
needs to know where each slot skill sits in the unmodded game, which a mod cannot read once
another mod has changed the tables, so the stock cells are embedded.

For each mod.js this writes two marked blocks, in front of `function findRow(` the first time:
  // <tree-placement> ... // </tree-placement>   the code of TreePlacement.js
  // <stock-cells> ... // </stock-cells>         STOCK_CELLS for the mod's slot skills
The slot skills are the `slot: '<name>'` entries of the mod.js; their values come from the
game's own global\\excel\\skills.txt and skilldesc.txt (via ModAssets.py and its cache).
--check only reports whether the blocks are up to date.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def game_tables(game, cache, python):
    paths = ['global/excel/skills.txt', 'global/excel/skilldesc.txt']
    missing = [p for p in paths if not (cache / p).exists()]
    if missing:
        subprocess.run([python, str(HERE / 'ModAssets.py'), 'fetch', '--game', str(game), '--out', str(cache)] + missing,
                       check=True, capture_output=True)
    out = []
    for p in paths:
        lines = (cache / p).read_text(encoding='utf-8', errors='replace').replace('\r\n', '\n').split('\n')
        head = lines[0].split('\t')
        out.append([dict(zip(head, l.split('\t'))) for l in lines[1:] if l])
    return out


def stock_block(mod_js, skills, descs):
    slots = []
    for m in re.finditer(r"\bslot: '([^']+)'", mod_js):
        if m.group(1) not in slots:
            slots.append(m.group(1))
    by_skill = {}
    for r in skills:
        by_skill.setdefault(r['skill'].lower(), r)
    by_desc = {}
    for d in descs:
        by_desc.setdefault(d['skilldesc'].lower(), d)
    lines = []
    for name in slots:
        r = by_skill.get(name.lower())
        if not r:
            raise SystemExit('slot skill %r is not in the game\'s skills.txt' % name)
        d = by_desc[r['skilldesc'].lower()]
        reqs = [r[c] for c in ('reqskill1', 'reqskill2', 'reqskill3') if r.get(c)]
        values = '[%s, %s, %s, %s, %s, [%s]]' % (d['SkillPage'], d['SkillRow'], d['SkillColumn'], r['reqlevel'] or '1',
                                                 d['IconCel'] or '0', ', '.join("'%s'" % q for q in reqs))
        lines.append("  '%s': %s," % (name, values))
    return ('// <stock-cells> written by TreePlacement.py (Ai assisted toolkit, Tools\\DiabloII) from the game\'s own\n'
            '// skills.txt and skilldesc.txt; do not edit by hand. Where each slot skill sits in the unmodded game:\n'
            '// [SkillPage, SkillRow, SkillColumn, reqlevel, IconCel, [prerequisites]]. placeOnTree uses it when\n'
            '// another mod has moved or removed the slot skill.\n'
            'const STOCK_CELLS = {\n' + '\n'.join(lines) + '\n};\n// </stock-cells>\n')


def code_block():
    code = (HERE / 'TreePlacement.js').read_text(encoding='utf-8').rstrip() + '\n'
    return '// <tree-placement> written by TreePlacement.py from TreePlacement.js; do not edit here.\n' + code + '// </tree-placement>\n'


def replace_block(text, tag, block):
    pattern = re.compile(r'// <%s>.*?// </%s>\n' % (tag, tag), re.S)
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
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    skills, descs = game_tables(Path(args.game), Path(args.cache), args.python)
    stale = 0
    for mod in args.mods:
        path = Path(mod) / 'mod.js'
        raw = path.read_bytes().decode('utf-8')
        eol = '\r\n' if '\r\n' in raw else '\n'  # keep the file's line endings
        text = raw.replace('\r\n', '\n')
        new = replace_block(text, 'tree-placement', code_block())
        new = replace_block(new, 'stock-cells', stock_block(new, skills, descs))
        if new == text:
            print('%s: up to date' % path)
        elif args.check:
            stale += 1
            print('%s: OUT OF DATE' % path)
        else:
            path.write_bytes(new.replace('\n', eol).encode('utf-8'))
            print('%s: written' % path)
    return 1 if stale else 0


if __name__ == '__main__':
    sys.exit(main())
