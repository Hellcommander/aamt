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
    hd/character/enemy/<name>/*.model   the donor's models, edited, for a variant with "reshape"
    hd/model_lod_desc.bin               the game's model index with the new models added (only with "reshape")
    model_index.json                    which models were added and from which game build; Update-D2RModelIndex.ps1
                                        rebuilds the index from it after a game patch
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


def multiply_root_scale(definition, factor):
    for entity in definition['entities']:
        if any(c['type'] == 'UnitRootComponent' for c in entity['components']):
            transform = next(c for c in entity['components'] if c['type'] == 'TransformDefinitionComponent')
            for axis in ('x', 'y', 'z'):
                transform['scale'][axis] = round(transform['scale'][axis] * factor, 4)


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
    flat = []
    for entry in attach:
        # "bones": one copy of the entry per bone, each a little different in size.
        names = entry.get('bones')
        if not names:
            flat.append(entry)
            continue
        jitter = float(entry.get('scaleJitter', 0.0))
        for k, bone in enumerate(names):
            factor = 1.0 + jitter * (((k * 37) % 11) / 10.0 - 0.5)
            scale = scale_vector(entry.get('scale', 1.0))
            copy = {key: value for key, value in entry.items() if key not in ('bones', 'scaleJitter')}
            copy['bone'] = bone
            copy['scale'] = {axis: round(v * factor, 3) for axis, v in scale.items()}
            flat.append(copy)
    for index, entry in enumerate(flat):
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


def reshape_models(archive, definition, variant, out_dir, write, index):
    """Rewrites the donor's body models with the variant's "reshape" edit.

    Every model the definition names (and each of its LOD files) is read from
    the archive, edited with GrannyMesh.reshape against the donor's skeleton,
    and written under hd/character/enemy/<variant>/. The definition is pointed
    at the new files. The skeleton and animations stay the donor's.
    `index` collects {"model", "donor"} for the model index the caller writes
    afterwards.
    """
    import tempfile
    import GrannyMesh
    import GrannyPreview
    name = variant['name']
    spec = variant['reshape']
    files = archive.list()
    skeleton = next((c['filename'] for e in definition['entities'] for c in e['components']
                     if c['type'] == 'SkeletonDefinitionComponent'), None)
    if skeleton is None:
        raise ValueError(f'{name}: the donor has no skeleton, so it cannot be reshaped')
    written = []
    with tempfile.TemporaryDirectory() as work:
        def fetch(archive_path):
            target = os.path.join(work, archive_path.replace('/', '_'))
            with open(target, 'wb') as f:
                f.write(archive.read(archive_path))
            return target
        bones, _ = GrannyPreview.load_bones(fetch(skeleton[len('data/'):]))
        renamed = {}
        for entity in definition['entities']:
            for component in entity['components']:
                if component['type'] != 'ModelDefinitionComponent':
                    continue
                stem = component['filename'][len('data/'):-len('.model')]
                sources = [f for f in files if f == f'{stem}.model' or (f.startswith(f'{stem}_lod') and f.endswith('.model'))]
                if not sources:
                    raise FileNotFoundError(f"{name}: no model files for {component['filename']}")
                new_stem = f"hd/character/enemy/{name}/{stem.split('/')[-1]}"
                for source in sorted(sources):
                    model = GrannyMesh.Model(fetch(source))
                    report = GrannyMesh.reshape(model, bones, spec.get('quills'), spec.get('bulk'), spec.get('shape'))
                    report += point_textures(model, variant.get('retexture', []))
                    target = new_stem + source[len(stem):]
                    if write:
                        model.save(os.path.join(out_dir, *target.split('/')))
                    written.append({'file': target, 'from': source, 'edits': report})
                # The game only draws models listed in hd/model_lod_desc.bin (see ModelLodDesc.py).
                index.append({'model': f'data/{new_stem}.model', 'donor': component['filename']})
                renamed[component['filename']] = f'data/{new_stem}.model'
                component['filename'] = f'data/{new_stem}.model'
        for dep in definition['dependencies'].get('models', []):
            dep['path'] = renamed.get(dep['path'], dep['path'])
    return written


def point_textures(model, retexture):
    """Points a rewritten model's materials at the variant's own textures.

    A model names its textures by path (Textures[].FromFileName). The new path must have the
    old one's length, so the string is swapped in place and nothing else in the file moves.
    """
    out = []
    for item in retexture:
        old, new = item['from'].encode('ascii'), item['to'].encode('ascii')
        if len(old) != len(new):
            raise ValueError(f"retexture: {item['to']} must be as long as {item['from']} ({len(old)} characters)")
        hits = 0
        for section in model.g.sections:
            count = section.count(old + b'\0')
            if count:
                section[:] = section.replace(old + b'\0', new + b'\0')
                hits += count
        out.append(f"texture {item['from'].rsplit('/', 1)[-1]} -> {item['to'].rsplit('/', 1)[-1]}: {hits} reference(s)")
    return out


def write_textures(archive, definition, variant, out_dir, write):
    """Writes the variant's recoloured textures ("retexture") and lists them in the definition.

    Each entry: {"from": "data/hd/.../x_alb.texture", "to": "data/hd/character/enemy/<name>/textures/...",
    "format": "bc3" | "bc1" | "rgba8", "recolor": {"hue", "minSat", "hueShift", "sat", "value"}}.
    Block textures are recoloured block by block (RecolorEffect.py: the two end colours of every
    4x4 block, every mip), so the file keeps its format, size and mips.
    """
    import RecolorEffect
    out = []
    for item in variant.get('retexture', []):
        tex = RecolorEffect.Texture(archive.read(item['from'][len('data/'):]))
        kind = item.get('format', 'bc3')
        _, size, w, h = tex.mips[0]
        per_block = {'bc1': 8, 'bc3': 16}.get(kind)
        if kind == 'rgba8':
            if tex.kind() != 'rgba8':
                raise ValueError(f"retexture: {item['from']} is not RGBA8 ({tex.describe()})")
            data = RecolorEffect.recolor_rgba8(tex, item['recolor'])
        elif per_block and size == max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * per_block:
            data = RecolorEffect.recolor_blocks(tex, item['recolor'], kind)
        else:
            raise ValueError(f"retexture: {item['from']} does not look like {kind} ({tex.describe()})")
        if write:
            target = os.path.join(out_dir, *item['to'][len('data/'):].split('/'))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as f:
                f.write(data)
        textures = definition['dependencies'].setdefault('textures', [])
        for dep in textures:
            if dep['path'] == item['from']:
                dep['path'] = item['to']
        if not any(dep['path'] == item['to'] for dep in textures):
            textures.append({'path': item['to']})
        out.append({'file': item['to'][len('data/'):], 'from': item['from'][len('data/'):], 'texture': tex.describe(), 'recolor': item['recolor']})
    return out


def included_models(out_dir, folders):
    """Model index entries of other mods ("modelIndexIncludes": mod folders relative to this one).

    Both mods ship the whole hd/model_lod_desc.bin and the one installed last wins, so the
    index this mod ships also carries the other mod's models (bounding boxes read from that
    mod's own model files). Each entry keeps "source" so a rebuild finds the files again.
    """
    import ModelLodDesc
    out, notes = [], []
    seen = set()
    for folder in folders:
        manifest = ModelLodDesc.read_manifest(os.path.normpath(os.path.join(out_dir, folder)))
        if manifest is None:
            notes.append(f'{folder}: no {ModelLodDesc.MANIFEST}, nothing included')
            continue
        count = 0
        for item in manifest['models']:
            # An entry the other mod itself carries from a third mod ("source", relative to the other
            # mod) is resolved to that third mod, whose folder holds the model files.
            source = os.path.join(folder, item['source']) if item.get('source') else folder
            if item['model'] in seen:
                continue
            seen.add(item['model'])
            out.append({'model': item['model'], 'donor': item['donor'], 'source': os.path.normpath(source).replace('\\', '/')})
            count += 1
        notes.append(f"{folder}: {count} model(s) included")
    return out, notes


MODE_STATES = {'DT': 'State_Death', 'NU': 'State_Neutral', 'WL': 'State_Walk', 'GH': 'State_GetHit', 'A1': 'State_Attack1',
               'A2': 'State_Attack2', 'BL': 'State_Block', 'SC': 'State_Cast', 'S1': 'State_Skill1', 'S2': 'State_Skill2',
               'S3': 'State_Skill3', 'S4': 'State_Skill4', 'DD': 'State_Dead', 'KB': 'State_Knockback', 'RN': 'State_Run'}


def add_sequence_state(machine):
    """Adds a state for the sequence mode (SQ, mode 14), which many monsters' state machines lack.

    Shaped like the stock ones (act2hire's Jab_Sequence): next free stateId, modeId 14, with a
    transition group of its own and a transition to it from every other state.
    """
    new_id = max(st['stateId'] for st in machine['states']) + 1
    template = next(st for st in machine['states'] if st['name'] == 'State_Attack1')
    state = json.loads(json.dumps(template))
    state.update({'name': 'State_Sequence', '_name': 'Sequence', 'stateId': new_id, 'modeId': 14, 'loopCount': 1})
    machine['states'].append(state)
    names = {st['stateId']: st['_name'] for st in machine['states']}
    seconds = machine['transitions'][0]['settings'][0]['crossfadeSeconds']
    for group in machine['transitions']:
        group['settings'].append({'type': 'AnimationTransitionItem', 'name': f"{names[group['from']]}_transition_to_Sequence",
                                  'crossfadeSeconds': seconds, 'to': new_id})
    machine['transitions'].append({
        'type': 'AnimationTransitionGroup', 'name': 'Sequence_transitions', 'from': new_id,
        'settings': [{'type': 'AnimationTransitionItem', 'name': f'Sequence_transition_to_{names[i]}', 'crossfadeSeconds': seconds, 'to': i}
                     for i in sorted(names) if i != new_id]})
    return state


def own_animations(archive, definition, variant, out_dir, write):
    """Gives a variant its own skeleton, state machine and animation file, with new clips added.

    The donor's `animation/combined.animations` is copied to
    hd/character/enemy/<name>/animation/ with the clips described in the
    variant's "animations" added (GrannyAnim.build_clip), the donor's state
    machine is copied with its clip paths pointed there, and the donor's
    skeleton is copied to hd/character/enemy/<name>/skeleton/<name>.skeleton.
    The state machine already has a state for every mode (run, cast, skill1-4,
    block, ...); a mode works as soon as a clip of that name exists.
    """
    import GrannyAnim
    name = variant['name']
    root = next(c for e in definition['entities'] for c in e['components'] if c['type'] == 'UnitRootComponent')
    skeleton_component = next(c for e in definition['entities'] for c in e['components'] if c['type'] == 'SkeletonDefinitionComponent')
    old_machine = root['state_machine_filename']
    old_folder = old_machine[:old_machine.rindex('/')]                  # data/hd/character/enemy/<donor>
    new_folder = f'data/hd/character/enemy/{name}'
    skeleton_bytes = archive.read(skeleton_component['filename'][len('data/'):])
    skeleton = GrannyAnim.Skeleton(skeleton_bytes)
    animations = GrannyAnim.load(archive.read(f"{old_folder[len('data/'):]}/animation/combined.animations"))
    stock = animations.names()
    added = []
    for spec in variant['animations']:
        keys = GrannyAnim.build_clip(animations, skeleton, spec)
        added.append({'clip': spec['name'], 'base': spec.get('base') or '+'.join(part['base'] for part in spec['parts']), 'seconds': round(keys.duration, 3), 'keys': len(keys.times),
                      'mode': spec.get('mode')})
    machine = json.loads(archive.read(old_machine[len('data/'):]).decode('utf-8'))
    text = json.dumps(machine, separators=(',', ':')).replace(f'{old_folder}/animation/', f'{new_folder}/animation/')
    machine = json.loads(text)
    machine['name'] = f'{name}_statemachine'
    # A clip with "mode" is bound to that mode's state under its own name (a clip called
    # "charge" on S3), instead of having to be named after the state's stock clip.
    for spec in variant['animations']:
        if not spec.get('mode'):
            continue
        state_name = MODE_STATES.get(spec['mode'].upper())
        state = next((st for st in machine['states'] if st['name'] == state_name), None)
        if state is None and spec['mode'].upper() == 'SQ':
            state = add_sequence_state(machine)
        if state is None:
            raise ValueError(f"{name}: clip {spec['name']} asks for mode {spec['mode']}, which the state machine has no state for")
        state['animationBindings'] = {key: [spec['name']] for key in state['animationBindings']}
        if 'loop' in spec:
            state['loopCount'] = 0 if spec['loop'] else 1
    # Every new clip is listed as an AnimationItem (bound to a state or not), so a mod can bind it
    # by name in states of its own, e.g. skill-indexed states its install script adds.
    for spec in variant['animations']:
        clip_path = f"{new_folder}/animation/{spec['name']}.animation"
        if not any(a['name'] == spec['name'] for a in machine['animations']):
            machine['animations'].append({'type': 'AnimationItem', 'name': spec['name'], 'filename': clip_path})
            machine['dependencies']['animations'].append({'path': clip_path})
    new_machine = f'{new_folder}/{name}_state_machine.json'
    new_skeleton = f'{new_folder}/skeleton/{name}.skeleton'
    root['state_machine_filename'] = new_machine
    skeleton_component['filename'] = new_skeleton
    for dep in definition['dependencies'].get('json', []):
        if dep['path'] == old_machine:
            dep['path'] = new_machine
    for dep in definition['dependencies'].get('skeletons', []):
        dep['path'] = new_skeleton
    if write:
        animations.save(os.path.join(out_dir, *f"{new_folder[len('data/'):]}/animation/combined.animations".split('/')))
        write_json(out_dir, new_machine[len('data/'):], machine)
        target = os.path.join(out_dir, *new_skeleton[len('data/'):].split('/'))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'wb') as f:
            f.write(skeleton_bytes)
    return {'stockClips': stock, 'added': added, 'stateMachine': new_machine[len('data/'):], 'skeleton': new_skeleton[len('data/'):]}


def sprite_scale(archive, variant, audit, definition_models_height=None):
    """Root scale that makes the donor's HD body as tall as a sprite monster.

    variant["scale"] = {"sprite": "<token>"}: the sprite monster's neutral pose
    height over the donor's own sprite height (both from their COF boxes), so
    the HD body gets the size the original art has next to its donor.
    "reshapedHeight" / "donorHeight" (model units) correct for a reshape that
    made the mesh taller, so the result still matches the sprite.
    """
    import LegacyToHd
    sources = LegacyToHd.Sources(archive)
    target = LegacyToHd.measure(sources, variant['scale']['sprite'])
    donor = LegacyToHd.measure(sources, audit['token'])
    scale = target['height'] / donor['height']
    return scale, {'sprite': variant['scale']['sprite'], 'spriteHeightPx': target['height'],
                   'donorToken': audit['token'], 'donorHeightPx': donor['height']}


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
    index = []
    with D2RArchive(game_path, casclib) as archive:
        for variant in preset['variants']:
            donor = variant['donor']
            if donor not in report['audits']:
                report['audits'][donor] = audit_animations(archive, donor)
            audit = report['audits'][donor]
            if not audit['hdHasModel']:
                raise ValueError(f'{donor} has no HD model in the archive, so it cannot be a donor')
            scale = variant['scale']
            sized = None
            if isinstance(scale, dict) and 'sprite' in scale:
                scale, sized = sprite_scale(archive, variant, audit)
            entry = {
                'name': variant['name'], 'donor': donor, 'donorHd': audit['hdDefinition'],
                'scale': scale, 'playableModes': audit['playable'],
                'file': f"hd/character/enemy/{variant['name']}.json",
            }
            if sized:
                entry['sizedFromSprite'] = sized
            attachments = expand_attachments(variant.get('attach', []))
            used_props = sorted({a['prop'] for a in attachments})
            for prop_name in used_props:
                if prop_name not in preset.get('props', {}):
                    raise KeyError(f"{variant['name']}: prop \"{prop_name}\" is not defined in the preset's props")
            if attachments:
                entry['attachments'] = len(attachments)
                entry['props'] = [prop_path(name) for name in used_props]
            definition = build_scaled_definition(archive, audit['hdDefinition'], variant['name'], scale)
            if attachments:
                part, part_variant = donor_part(definition)
                attach_props(definition, variant['name'], attachments, part, part_variant)
            if variant.get('retexture') and not variant.get('reshape'):
                raise ValueError(f"{variant['name']}: \"retexture\" needs \"reshape\" (the variant's own model files to point at the textures)")
            if variant.get('reshape'):
                entry['models'] = reshape_models(archive, definition, variant, out_dir, not audit_only, index)
            if variant.get('retexture'):
                entry['textures'] = write_textures(archive, definition, variant, out_dir, not audit_only)
            if sized and variant.get('reshape') and not audit_only:
                # A reshape that made the mesh taller would overshoot the sprite's size: take it back out of the root scale.
                import ModelLodDesc
                donor_model = index[-1]['donor']
                new_boxes = ModelLodDesc.model_boxes(out_dir, index[-1]['model'])[0]
                desc = ModelLodDesc.ModelLodDesc(archive.read(ModelLodDesc.INDEX)).describe(donor_model)
                donor_height = max(m['box'][4] for m in desc['lods'][0]) - min(m['box'][1] for m in desc['lods'][0])
                new_height = max(high[1] for _, high in new_boxes) - min(low[1] for low, _ in new_boxes)
                multiply_root_scale(definition, donor_height / new_height)
                scale = round(scale * donor_height / new_height, 3)
                sized.update({'donorMeshHeight': round(donor_height, 3), 'reshapedMeshHeight': round(new_height, 3)})
                entry['scale'] = scale
            if variant.get('animations'):
                entry['animations'] = own_animations(archive, definition, variant, out_dir, not audit_only)
            prop_definitions = {name: build_prop_definition(archive, name, preset['props'][name]) for name in used_props}
            if not audit_only:
                write_json(out_dir, entry['file'], definition)
                for name, prop_definition in prop_definitions.items():
                    write_json(out_dir, prop_path(name), prop_definition)
            report['variants'].append(entry)
        for extra in preset.get('auditOnly', []):
            report['audits'][extra] = audit_animations(archive, extra)
        if index:
            report['modelIndex'] = {'file': 'hd/model_lod_desc.bin', 'manifest': 'model_index.json',
                                    'added': [item['model'] for item in index]}
            if not audit_only:
                # Writes model_index.json (what this mod adds) and the index built from this game build's.
                # Entries other tools put in the mod's manifest (effect meshes, ...) are kept; entries
                # taken from other mods ("source") are read again from those mods.
                import ModelLodDesc
                existing = ModelLodDesc.read_manifest(out_dir) or {'models': []}
                included, notes = included_models(out_dir, preset.get('modelIndexIncludes', []))
                mine = {item['model'] for item in index}
                kept = [item for item in existing['models'] if item['model'] not in mine and 'source' not in item]
                merged = index + kept
                merged += [item for item in included if item['model'] not in {m['model'] for m in merged}]
                report['modelIndex']['included'] = notes
                ModelLodDesc.build_for_mod(archive, out_dir, merged, report['gameBuild'])
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
        if v.get('sizedFromSprite'):
            z = v['sizedFromSprite']
            extra += f", sized from sprite {z['sprite']} ({z['spriteHeightPx']} px over {z['donorToken']} {z['donorHeightPx']} px)"
        if v.get('animations'):
            extra += f", own animations: +{' +'.join(a['clip'] for a in v['animations']['added'])}"
        if v.get('models'):
            extra += f", {len(v['models'])} model files reshaped"
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
