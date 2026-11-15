"""Gives an original-graphics (sprite) monster an HD version in Diablo II: Resurrected.

A sprite monster has no bones, so its HD version is built from the HD monster
that is closest to it: that donor's definition and skeleton are copied under a
new name, sized to the sprite, and the skeleton copy is left as editable JSON.

  LegacyToHd.py measure --game <D2R> [--data <mod data>] <token>
  LegacyToHd.py donors  --game <D2R> [--data <mod data>] <token> [--top N]
  LegacyToHd.py build   --game <D2R> [--data <mod data>] --token <token> --name <new hd name>
                        --out <mod folder> [--donor <monstats Id>] [--scale S] [--strip]
  LegacyToHd.py encode  --out <mod folder> --name <new hd name>

  measure  size of the sprite monster, from its animation descriptors (COF):
           modes, frames, layers and the box the sprites fill.
  donors   HD monsters ranked by how close they are to it (see `closeness`).
  build    writes, under --out:
             hd/character/enemy/<name>.json                       donor definition, scaled, using the new skeleton
             hd/character/enemy/<name>/skeleton/<name>.skeleton   the skeleton the game loads
             skeleton_src/<name>.skeleton.json                    the same skeleton decoded, for editing
             <name>.legacy_to_hd.json                             what was chosen and why
           --donor picks the donor yourself; --scale overrides the size taken from the sprites.
  encode   rebuilds the .skeleton from the edited skeleton_src JSON.

<token> is the two-letter legacy animation token (monstats `Code`), read from
--data (a mod's data folder: global/monsters/<token>/cof/...) first, then from the game.

What a skeleton file controls, as seen in the game (2026-11-13, Sorceress on the
character screen): an encoded skeleton loads and the body animates as before.
Changing a bone's bind matrix (InverseWorldTransform), rest-pose scale or
rest-pose position in it changed nothing, and neither did the same edits in the
copy of the bones each .model carries: animations set every bone's position,
rotation and scale on every frame. So the body size goes on the definition's
root entity (the way Blizzard resizes brute2 or colossal1, and ScaledMonster.py
does). The skeleton copy is the place for the bone list: names and parents.
Proportions have to be made in the mesh vertices (GrannyMesh.py) or the
animations. --strip is safe: a skeleton without its Maya attributes loads too.
"""
import argparse
import json
import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import HdSkeleton  # noqa: E402
from d2r_casc import D2RArchive  # noqa: E402
from ScaledMonster import build_scaled_definition, read_json, read_tsv, write_json  # noqa: E402

MODES = ['dt', 'nu', 'wl', 'gh', 'a1', 'a2', 'bl', 'sc', 's1', 's2', 's3', 's4', 'dd', 'kb', 'sq', 'rn']
LAYERS = ['HD', 'TR', 'LG', 'RA', 'LA', 'RH', 'LH', 'SH', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8']


class Sources:
    """Legacy files from a mod's data folder first, then from the game archive."""

    def __init__(self, archive, data_dir=None):
        self.archive, self.data_dir = archive, data_dir
        self._names = None

    def read(self, path):
        if self.data_dir:
            local = os.path.join(self.data_dir, *path.split('/'))
            if os.path.isfile(local):
                with open(local, 'rb') as f:
                    return f.read()
        return self.archive.read(path)

    def names(self):
        if self._names is None:
            self._names = set(self.archive.list())
            if self.data_dir:
                for root, _, files in os.walk(os.path.join(self.data_dir, 'global', 'monsters')):
                    rel = os.path.relpath(root, self.data_dir).replace('\\', '/').lower()
                    self._names.update(f'{rel}/{name.lower()}' for name in files)
        return self._names


def parse_cof(data):
    layers, frames, directions = data[0], data[1], data[2]
    xmin, xmax, ymin, ymax = struct.unpack_from('<4i', data, 8)
    return {'frames': frames, 'directions': directions, 'speed': struct.unpack_from('<H', data, 24)[0],
            'layers': sorted({LAYERS[data[28 + 9 * i]] for i in range(layers) if data[28 + 9 * i] < 16}),
            'box': [xmin, xmax, ymin, ymax]}


def measure(sources, token):
    """The sprite monster's modes and size. `height` is how far the neutral pose rises above its feet, in pixels."""
    token = token.lower()
    prefix = f'global/monsters/{token}/cof/{token}'
    cofs = sorted(n for n in sources.names() if n.startswith(prefix) and n.endswith('.cof'))
    modes = {}
    for name in cofs:
        mode, weapon = name[len(prefix):len(prefix) + 2], name[len(prefix) + 2:-4]
        if mode in MODES and (mode not in modes or weapon == 'hth'):
            data = sources.read(name)
            if data and len(data) >= 28:
                modes[mode] = dict(parse_cof(data), weapon=weapon)
    if not modes:
        raise SystemExit(f'no animation descriptors found for token "{token}" (global/monsters/{token}/cof/)')
    ref = modes.get('nu') or modes.get('wl') or next(iter(modes.values()))
    xmin, xmax, ymin, ymax = ref['box']
    return {'token': token, 'modes': modes, 'height': max(-ymin, 0), 'width': xmax - xmin,
            'layers': sorted({l for m in modes.values() for l in m['layers']})}


def closeness(target, donor):
    """Smaller is closer. Returns (score, parts): missing modes weigh most, then shape, layers, timing, size."""
    missing = [m for m in target['modes'] if m not in donor['modes']]
    def ratio(a, b):
        return abs(math.log(a / b)) if a > 0 and b > 0 else 1.0
    shape = ratio(target['width'] / max(target['height'], 1), donor['width'] / max(donor['height'], 1))
    a, b = set(target['layers']), set(donor['layers'])
    layers = 1 - len(a & b) / max(len(a | b), 1)
    common = [m for m in target['modes'] if m in donor['modes']]
    timing = sum(ratio(target['modes'][m]['frames'], donor['modes'][m]['frames']) for m in common) / max(len(common), 1)
    size = ratio(target['height'], donor['height'])
    parts = {'missingModes': missing, 'shape': round(shape, 3), 'layers': round(layers, 3),
             'timing': round(timing, 3), 'size': round(size, 3)}
    return len(missing) + shape + 0.5 * layers + 0.25 * timing + 0.5 * size, parts


def hd_monsters(sources):
    """[(monstats Id, token, hd definition name)] for monsters whose HD definition has a skeleton, one per definition."""
    names = sources.names()
    hd = read_json(sources.archive, 'hd/character/monsters.json')
    out, seen = [], set()
    for row in read_tsv(sources.archive, 'global/excel/monstats.txt'):
        definition = hd.get(row['Id'])
        token = (row.get('Code') or '').lower()
        if not definition or not token or definition in seen:
            continue
        if f'hd/character/enemy/{definition}/skeleton/{definition}.skeleton' not in names:
            continue
        seen.add(definition)
        out.append((row['Id'], token, definition))
    return out


def rank_donors(sources, target):
    ranked, measured = [], {}
    for monster, token, definition in hd_monsters(sources):
        if token == target['token']:
            continue
        if token not in measured:
            try:
                measured[token] = measure(sources, token)
            except SystemExit:
                measured[token] = None
        donor = measured[token]
        if donor is None or donor['height'] <= 0:
            continue
        score, parts = closeness(target, donor)
        ranked.append({'monster': monster, 'token': token, 'definition': definition, 'score': round(score, 3),
                       'height': donor['height'], 'width': donor['width'], **parts})
    ranked.sort(key=lambda d: d['score'])
    return ranked


def skeleton_paths(out_dir, name):
    return (os.path.join(out_dir, 'hd', 'character', 'enemy', name, 'skeleton', f'{name}.skeleton'),
            os.path.join(out_dir, 'skeleton_src', f'{name}.skeleton.json'))


def write_skeleton(out_dir, name, doc):
    target, source = skeleton_paths(out_dir, name)
    for path in (target, source):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(source, 'w', encoding='utf-8') as f:
        json.dump(doc, f, indent=1)
    data = HdSkeleton.from_document(doc)
    # Edited numbers are stored as 32-bit floats, so compare what the file holds with itself re-encoded.
    if HdSkeleton.from_document(HdSkeleton.to_document(data)) != data:
        raise SystemExit('the encoded skeleton does not read back as it was written')
    with open(target, 'wb') as f:
        f.write(data)
    return target, source, len(data)


def build(sources, a):
    target = measure(sources, a.token)
    ranked = rank_donors(sources, target)
    if a.donor:
        hd = read_json(sources.archive, 'hd/character/monsters.json')
        row = next((r for r in read_tsv(sources.archive, 'global/excel/monstats.txt') if r['Id'] == a.donor), None)
        if row is None or a.donor not in hd:
            raise SystemExit(f'donor "{a.donor}" is not a monstats Id with an HD definition')
        donor = next((d for d in ranked if d['definition'] == hd[a.donor]), None)
        if donor is None:
            m = measure(sources, row['Code'])
            score, parts = closeness(target, m)
            donor = {'monster': a.donor, 'token': row['Code'].lower(), 'definition': hd[a.donor],
                     'score': round(score, 3), 'height': m['height'], 'width': m['width'], **parts}
    else:
        if not ranked:
            raise SystemExit('no HD monster to use as a donor')
        donor = ranked[0]
    if a.scale:
        scale = a.scale
    elif target['height'] > 0 and donor['height'] > 0:
        scale = round(target['height'] / donor['height'], 3)
    else:
        scale = 1.0

    definition = build_scaled_definition(sources.archive, donor['definition'], a.name, scale)
    old = f"data/hd/character/enemy/{donor['definition']}/skeleton/{donor['definition']}.skeleton"
    new = f'data/hd/character/enemy/{a.name}/skeleton/{a.name}.skeleton'
    swapped = 0
    for dep in definition['dependencies'].get('skeletons', []):
        if dep['path'].lower() == old.lower():
            dep['path'] = new
            swapped += 1
    for entity in definition['entities']:
        for component in entity['components']:
            if component['type'] == 'SkeletonDefinitionComponent' and component['filename'].lower() == old.lower():
                component['filename'] = new
                swapped += 1
    if swapped < 2:
        raise SystemExit(f"{donor['definition']}.json does not name its skeleton the expected way")

    data = sources.archive.read(old[5:])
    doc = HdSkeleton.to_document(data, a.strip)
    doc['root'] = json.loads(json.dumps(doc['root']))            # an own copy to edit
    bone_count = sum(len(s['Bones']) for s in doc['root']['Skeletons'])

    write_json(a.out, f'hd/character/enemy/{a.name}.json', definition)
    skeleton, source, size = write_skeleton(a.out, a.name, doc)
    report = {'token': target['token'], 'name': a.name, 'sprite': {'height': target['height'], 'width': target['width'],
              'modes': sorted(target['modes']), 'layers': target['layers']},
              'donor': donor, 'scale': scale,
              'missingModes': donor['missingModes'],
              'files': {'definition': f'hd/character/enemy/{a.name}.json',
                        'skeleton': f'hd/character/enemy/{a.name}/skeleton/{a.name}.skeleton',
                        'skeletonSource': f'skeleton_src/{a.name}.skeleton.json'},
              'install': f'copy hd/ into the game data and set hd/character/monsters.json["<monstats Id>"] = "{a.name}"'}
    with open(os.path.join(a.out, f'{a.name}.legacy_to_hd.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(report, f, indent=2)
    print(f"sprite {target['token']}: {target['height']} px tall, {target['width']} px wide, modes {' '.join(sorted(target['modes']))}")
    print(f"donor  {donor['monster']} ({donor['definition']}, token {donor['token']}): {donor['height']} px tall, score {donor['score']}")
    if donor['missingModes']:
        print(f"       the donor has no {' '.join(donor['missingModes'])} animation; the monster cannot use those modes in HD")
    print(f'scale  {scale}')
    print(f'wrote  {report["files"]["definition"]}')
    print(f'wrote  {report["files"]["skeleton"]} ({size} bytes, {bone_count} bones)')
    print(f'wrote  {report["files"]["skeletonSource"]} (edit, then: LegacyToHd.py encode --out ... --name {a.name})')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['measure', 'donors', 'build', 'encode'])
    ap.add_argument('token_arg', nargs='?')
    ap.add_argument('--game', default=os.environ.get('D2R_PATH'))
    ap.add_argument('--casclib')
    ap.add_argument('--data', help="a mod's data folder holding the sprite monster's global/monsters/<token> files")
    ap.add_argument('--token')
    ap.add_argument('--name')
    ap.add_argument('--out')
    ap.add_argument('--donor')
    ap.add_argument('--scale', type=float)
    ap.add_argument('--strip', action='store_true', help='leave the Maya attribute dumps out of the skeleton')
    ap.add_argument('--top', type=int, default=10)
    a = ap.parse_args()
    a.token = a.token or a.token_arg

    if a.command == 'encode':
        if not a.out or not a.name:
            raise SystemExit('encode needs --out and --name')
        target, source = skeleton_paths(a.out, a.name)
        with open(source, encoding='utf-8') as f:
            doc = json.load(f)
        target, _, size = write_skeleton(a.out, a.name, doc)
        print(f'wrote {target} ({size} bytes)')
        return
    if not a.game or not os.path.isdir(a.game):
        raise SystemExit('Pass --game (or set D2R_PATH) to the folder that contains D2R.exe.')
    if not a.token:
        raise SystemExit('Pass the legacy token (monstats Code), e.g. fa.')
    with D2RArchive(a.game.replace('/', '\\'), a.casclib) as archive:
        sources = Sources(archive, a.data)
        if a.command == 'measure':
            m = measure(sources, a.token)
            print(f"{m['token']}: {m['height']} px tall, {m['width']} px wide, layers {' '.join(m['layers'])}")
            for mode, c in m['modes'].items():
                print(f"  {mode} {c['weapon']}: {c['frames']} frames x {c['directions']} directions, speed {c['speed']}, box {c['box']}")
        elif a.command == 'donors':
            target = measure(sources, a.token)
            print(f"{target['token']}: {target['height']} px tall, {target['width']} px wide")
            for d in rank_donors(sources, target)[:a.top]:
                print(f"  {d['score']:6.3f}  {d['monster']:<16} {d['definition']:<18} {d['height']:>4} px  scale {target['height'] / d['height']:.2f}"
                      f"  shape {d['shape']} layers {d['layers']} timing {d['timing']}"
                      + (f"  missing {' '.join(d['missingModes'])}" if d['missingModes'] else ''))
        else:
            if not a.name or not a.out:
                raise SystemExit('build needs --name and --out')
            build(sources, a)


if __name__ == '__main__':
    main()
