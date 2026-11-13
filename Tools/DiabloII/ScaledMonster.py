"""Scaled monster pipeline for Diablo II: Resurrected.

Builds new HD monster definitions out of an existing monster at a different
size (a giant Quill Rat, a small pack rat, ...) and audits which animation
modes the donor really has, so a mod knows what the new monster can play.

The scale is applied the way Blizzard does it for their own resized monsters
(brute2, colossal1, baaltentacle1): a TransformDefinitionComponent on the
definition's root entity. Model, skeleton, textures, animations and the state
machine stay the donor's, so no art is copied or shipped.

A variant can also be kitbashed: stretched per axis, and given props (any
model in the archive, such as a bone tusk) attached to the donor's bones the
way Blizzard attaches a monster's weapon. That is how a Quill Bear style body
is made from a Spike Fiend without a new model. See README.md.

Output (under --out, normally a D2RMM mod folder):
    hd/character/enemy/<name>.json      one per variant
    hd/character/props/<prop>.json      one per prop used
    scaled_monsters.report.json         what was built + the animation audit

The mod then copies `hd` into the game data and points its monsters at the
new definitions in hd/character/monsters.json (see README.md).
"""
import argparse
import csv
import io
import json
import math
import os
import sys
import zlib

from d2r_casc import D2RArchive

# monstats2 mode columns -> legacy animation mode token / HD clip name.
MODES = [
    ('DT', 'death'), ('NU', 'neutral'), ('WL', 'walk'), ('GH', 'gethit'),
    ('A1', 'attack1'), ('A2', 'attack2'), ('BL', 'block'), ('SC', 'cast'),
    ('S1', 'skill1'), ('S2', 'skill2'), ('S3', 'skill3'), ('S4', 'skill4'),
    ('DD', 'dead'), ('KB', 'knockback'), ('SQ', 'sequence'), ('RN', 'run'),
]
# Trigger values in a COF's per-frame table.
COF_TRIGGERS = {1: 'melee hit', 2: 'missile launch', 3: 'sound', 4: 'skill'}


def read_tsv(archive, path):
    data = archive.read(path)
    if data is None:
        raise FileNotFoundError(path)
    rows = list(csv.reader(io.StringIO(data.decode('latin1')), delimiter='\t', quoting=csv.QUOTE_NONE))
    return [dict(zip(rows[0], r)) for r in rows[1:]]


def read_json(archive, path):
    data = archive.read(path)
    if data is None:
        raise FileNotFoundError(path)
    return json.loads(data.decode('utf-8-sig'))


def parse_cof(data):
    """Legacy animation descriptor: frame count, speed and the frame that triggers the action."""
    layers, frames, directions = data[0], data[1], data[2]
    speed = int.from_bytes(data[24:26], 'little')
    table = data[28 + layers * 9: 28 + layers * 9 + frames]
    triggers = [{'frame': i, 'type': COF_TRIGGERS.get(v, str(v))} for i, v in enumerate(table) if v]
    return {'frames': frames, 'directions': directions, 'layers': layers, 'speed': speed, 'triggers': triggers}


def audit_animations(archive, monster_id):
    """Which modes a monster can really play: monstats2 flags, legacy COF + sprites, and its HD files."""
    monstats = read_tsv(archive, 'global/excel/monstats.txt')
    row = next((r for r in monstats if r['Id'] == monster_id), None)
    if row is None:
        raise KeyError(f'monster "{monster_id}" is not in monstats.txt')
    stats2 = next(r for r in read_tsv(archive, 'global/excel/monstats2.txt') if r['Id'] == row['MonStatsEx'])
    token = row['Code'].lower()
    weapon = (stats2.get('BaseW') or 'hth').lower()
    files = archive.list()
    legacy = [f for f in files if f.startswith(f'global/monsters/{token}/')]
    modes = {}
    for mode, clip in MODES:
        m = mode.lower()
        cof_path = f'global/monsters/{token}/cof/{token}{m}{weapon}.cof'
        sprites = sorted(f.split('/')[-1] for f in legacy if f.endswith(f'{m}{weapon}.dcc'))
        entry = {
            'clip': clip,
            'enabled': stats2.get('m' + mode) == '1',
            'cof': parse_cof(archive.read(cof_path)) if cof_path in legacy else None,
            'sprites': sprites,
        }
        if sprites and not entry['cof']:
            entry['note'] = 'sprites exist but no COF: a cut animation that could be restored'
        modes[mode] = entry
    hd_name = read_json(archive, 'hd/character/monsters.json').get(monster_id)
    hd_files = sorted(f for f in files if f.startswith(f'hd/character/enemy/{hd_name}/')) if hd_name else []
    return {
        'monster': monster_id, 'token': token.upper(), 'weaponClass': weapon.upper(),
        'modes': modes,
        'playable': [m for m, e in modes.items() if e['enabled'] and e['cof']],
        'hdDefinition': hd_name,
        'hdHasModel': any(f.endswith('.model') for f in hd_files),
        'hdHasAnimations': any('/animation/' in f for f in hd_files),
        'hdFileCount': len(hd_files),
    }


def scale_vector(scale):
    """A scale is one number, or {"x", "y", "z"} to stretch a body per axis."""
    if isinstance(scale, dict):
        return {axis: float(scale.get(axis, 1.0)) for axis in ('x', 'y', 'z')}
    return {axis: float(scale) for axis in ('x', 'y', 'z')}


def vector(value, default=0.0):
    value = value or {}
    return {axis: float(value.get(axis, default)) for axis in ('x', 'y', 'z')}


def stable_id(text):
    """Entity ids only have to be unique inside a definition and stable between runs."""
    return (zlib.crc32(text.encode('utf-8')) & 0x7FFFFFFF) or 1


def build_scaled_definition(archive, donor_hd, name, scale):
    """Copies the donor's HD definition and scales its root entity."""
    definition = read_json(archive, f'hd/character/enemy/{donor_hd}.json')
    definition['name'] = name
    root = next((e for e in definition['entities']
                 if any(c['type'] == 'UnitRootComponent' for c in e['components'])), None)
    if root is None:
        raise ValueError(f'{donor_hd}.json has no root entity')
    transform = next((c for c in root['components'] if c['type'] == 'TransformDefinitionComponent'), None)
    if transform is None:
        transform = {
            'type': 'TransformDefinitionComponent', 'name': 'entity_root_TransformDefinition',
            'position': {'x': 0.0, 'y': 0.0, 'z': 0.0},
            'orientation': {'x': 0.0, 'y': 0.0, 'z': 0.0, 'w': 1.0},
            'scale': {'x': 1.0, 'y': 1.0, 'z': 1.0}, 'inheritOnlyPosition': False,
        }
        root['components'].append(transform)
    # A donor that is already scaled keeps its proportions.
    factors = scale_vector(scale)
    for axis in ('x', 'y', 'z'):
        transform['scale'][axis] = round(transform['scale'][axis] * factors[axis], 4)
    return definition


def prop_path(prop_name):
    return f'hd/character/props/{prop_name}.json'


def build_prop_definition(archive, prop_name, prop):
    """A one-model definition, the same shape as a monster weapon (fallen_shaman_dagger.json)."""
    model = prop['model']
    files = archive.list()
    if f'{model}.model' not in files and f'{model}_lod0.model' not in files:
        raise FileNotFoundError(f'prop "{prop_name}": no model {model}.model or {model}_lod0.model in the archive')
    for texture in prop.get('textures', []):
        if texture not in files:
            raise FileNotFoundError(f'prop "{prop_name}": no texture {texture} in the archive')
    dependencies = {kind: [] for kind in ('particles', 'models', 'skeletons', 'animations', 'textures',
                                          'physics', 'json', 'variantdata', 'objecteffects', 'other')}
    dependencies['models'].append({'path': f'data/{model}.model'})
    dependencies['textures'] = [{'path': f'data/{t}'} for t in prop.get('textures', [])]
    return {
        'dependencies': dependencies,
        'type': 'UnitDefinition',
        'name': prop_name,
        'entities': [
            {'type': 'Entity', 'name': 'root_entity', 'id': stable_id(f'{prop_name}/root'), 'components': [{
                'type': 'UnitRootComponent', 'name': 'root_entity_UnitRootComponent',
                'state_machine_filename': '', 'doNotInheritRotation': False,
                'rotationOverride': {'x': 0.0, 'y': 0.0, 'z': 0.0, 'w': 1.0},
                'doNotUseHDHeight': False, 'hideAllMeshWhenInOpenedMode': False,
                'onCreateEventName': '', 'animations': [],
            }]},
            {'type': 'Entity', 'name': 'model_entity', 'id': stable_id(f'{prop_name}/model'), 'components': [{
                'type': 'ModelDefinitionComponent', 'name': 'model_entity_ModelDefinitionComponent',
                'filename': f'data/{model}.model',
                'visibleLayers': 1, 'lightMask': 19, 'shadowMask': 3, 'ghostShadows': False,
                'floorModel': False, 'terrainBlendEnableYUpBlend': False, 'terrainBlendMode': 1,
            }]},
        ],
    }


def expand_attachments(attach):
    """Turns the preset's attach list into single attachments.

    An entry is one prop on one bone, or a "burst": `count` copies spread evenly
    over a sphere (or the part of it within `spread` degrees of the first one).
    A burst is the practical way to bristle a body with spines when the bone's
    axes are not known: every direction is covered and the half that points
    into the body is hidden by it.
    """
    out = []
    for index, entry in enumerate(attach):
        base = {
            'prop': entry['prop'], 'bone': entry.get('bone', ''),
            'translation': vector(entry.get('translation')),
            'rotation': vector(entry.get('rotation')),
            'scale': scale_vector(entry.get('scale', 1.0)),
        }
        burst = entry.get('burst')
        if not burst:
            out.append(dict(base, label=f'{index}'))
            continue
        count = int(burst['count'])
        spread = math.radians(float(burst.get('spread', 180.0)))
        grow = float(burst.get('scaleJitter', 0.0))
        golden = math.pi * (3.0 - math.sqrt(5.0))
        for k in range(count):
            # Fibonacci sphere, cut off at `spread` from the pole.
            polar = math.acos(1.0 - (1.0 - math.cos(spread)) * (k + 0.5) / count)
            turn = golden * k
            item = dict(base, label=f'{index}_{k}')
            item['rotation'] = {
                'x': round(base['rotation']['x'] + math.degrees(polar) * math.cos(turn), 2),
                'y': round(base['rotation']['y'] + math.degrees(turn) % 360.0, 2),
                'z': round(base['rotation']['z'] + math.degrees(polar) * math.sin(turn), 2),
            }
            # Deterministic size variation so the spines do not look stamped.
            factor = 1.0 + grow * (((k * 37) % 11) / 10.0 - 0.5)
            item['scale'] = {axis: round(v * factor, 3) for axis, v in base['scale'].items()}
            out.append(item)
    return out


def attach_props(definition, variant_name, attachments, part, part_variant):
    """Adds one entity per attachment, each a UnitAttachmentComponent on a bone of the donor."""
    json_deps = definition['dependencies'].setdefault('json', [])
    for item in attachments:
        filename = f"data/{prop_path(item['prop'])}"
        if not any(d['path'] == filename for d in json_deps):
            json_deps.append({'path': filename})
        entity_name = f"entity_prop_{item['label']}"
        definition['entities'].append({
            'type': 'Entity', 'name': entity_name, 'id': stable_id(f'{variant_name}/{entity_name}'),
            'components': [{
                'type': 'UnitAttachmentComponent', 'name': f'{entity_name}_UnitAttachment',
                'filename': filename,
                'overrideBoneName': item['bone'], 'orientTowardBoneName': '',
                'attachmentTransform': {
                    'type': 'Transform', 'name': f'{entity_name}_UnitAttachment_attachmentTransform',
                    'translation': item['translation'], 'rotation': item['rotation'], 'scale': item['scale'],
                },
                'attachmentStateMachineFilename': '',
                'part': part, 'variant': part_variant,
            }],
        })


def donor_part(definition):
    """The first body part of the donor; props are shown and hidden with it."""
    for entity in definition['entities']:
        for component in entity['components']:
            if component['type'] == 'UnitPartComponent':
                return component['part'], component['variant']
    return 'torso', 'lit'


def write_json(out_dir, relative, value):
    target = os.path.join(out_dir, *relative.split('/'))
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, separators=(',', ':'))


def run(preset, game_path, casclib, out_dir, audit_only):
    report = {'preset': preset.get('name'), 'gameBuild': None, 'variants': [], 'audits': {}}
    build_info = os.path.join(game_path, '.build.info')
    if os.path.isfile(build_info):
        with open(build_info, encoding='latin1') as f:
            lines = f.read().splitlines()
        if len(lines) > 1:
            head = [h.split('!')[0] for h in lines[0].split('|')]
            if 'Version' in head:
                report['gameBuild'] = lines[1].split('|')[head.index('Version')]
    with D2RArchive(game_path, casclib) as archive:
        for variant in preset['variants']:
            donor = variant['donor']
            if donor not in report['audits']:
                report['audits'][donor] = audit_animations(archive, donor)
            audit = report['audits'][donor]
            if not audit['hdHasModel']:
                raise ValueError(f'{donor} has no HD model in the archive, so it cannot be a donor')
            entry = {
                'name': variant['name'], 'donor': donor, 'donorHd': audit['hdDefinition'],
                'scale': variant['scale'], 'playableModes': audit['playable'],
                'file': f"hd/character/enemy/{variant['name']}.json",
            }
            attachments = expand_attachments(variant.get('attach', []))
            used_props = sorted({a['prop'] for a in attachments})
            for prop_name in used_props:
                if prop_name not in preset.get('props', {}):
                    raise KeyError(f"{variant['name']}: prop \"{prop_name}\" is not defined in the preset's props")
            if attachments:
                entry['attachments'] = len(attachments)
                entry['props'] = [prop_path(name) for name in used_props]
            definition = build_scaled_definition(archive, audit['hdDefinition'], variant['name'], variant['scale'])
            if attachments:
                part, part_variant = donor_part(definition)
                attach_props(definition, variant['name'], attachments, part, part_variant)
            prop_definitions = {name: build_prop_definition(archive, name, preset['props'][name]) for name in used_props}
            if not audit_only:
                write_json(out_dir, entry['file'], definition)
                for name, prop_definition in prop_definitions.items():
                    write_json(out_dir, prop_path(name), prop_definition)
            report['variants'].append(entry)
        for extra in preset.get('auditOnly', []):
            report['audits'][extra] = audit_animations(archive, extra)
    if not audit_only:
        with open(os.path.join(out_dir, 'scaled_monsters.report.json'), 'w', encoding='utf-8', newline='\n') as f:
            json.dump(report, f, indent=2)
    return report


def print_report(report, audit_only):
    for monster, audit in report['audits'].items():
        print(f"{monster} (token {audit['token']}): playable modes {' '.join(audit['playable']) or 'none'}"
              f" | HD model: {'yes' if audit['hdHasModel'] else 'NO'}")
        for mode, e in audit['modes'].items():
            if e.get('note'):
                print(f'  {mode}: {e["note"]}')
            elif e['cof'] and e['cof']['triggers']:
                t = e['cof']['triggers'][0]
                print(f"  {mode}: {e['cof']['frames']} frames, {t['type']} on frame {t['frame']}")
    for v in report['variants']:
        extra = f", {v['attachments']} props attached" if v.get('attachments') else ''
        print(f"{'would build' if audit_only else 'built'} {v['file']}  ({v['donor']} x{v['scale']}{extra})")


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--preset', default=os.path.join(here, 'Presets', 'quillrat_pack.json'))
    ap.add_argument('--game', default=os.environ.get('D2R_PATH'), help='folder that contains D2R.exe (or set D2R_PATH)')
    ap.add_argument('--casclib', help='path to CascLib.dll (or set D2R_CASCLIB)')
    ap.add_argument('--out', help='output folder, normally the D2RMM mod folder')
    ap.add_argument('--audit', action='store_true', help='only report, write nothing')
    args = ap.parse_args()
    if not args.game or not os.path.isdir(args.game):
        ap.error('--game (or D2R_PATH) must point at the Diablo II: Resurrected folder')
    if not args.audit and not args.out:
        ap.error('--out is required unless --audit is given')
    with open(args.preset, encoding='utf-8') as f:
        preset = json.load(f)
    report = run(preset, args.game, args.casclib, args.out, args.audit)
    print_report(report, args.audit)
    return 0


if __name__ == '__main__':
    sys.exit(main())
