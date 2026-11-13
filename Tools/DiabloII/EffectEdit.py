"""Editor core and command line for Diablo II: Resurrected particle effects.

Reads a .particles file (from the game archive or from disk) into a description a
person or a bot can work with, and applies a *recipe* - a JSON list of edits - to
produce a new .particles file plus any textures the recipe makes from PNG files.
The web editor (EffectEditor.py) is a front end to this module.

An effect is a tree of named layers. Each layer has renderers (what is drawn:
billboards, meshes, ribbons, lights, decals, each with textures and settings),
scripts (compiled code that spawns and updates its particles, with the numbers it
uses as constants), and samplers (curves, turbulence, shapes).

The game's PC build reads the "PC" copy of an effect; a file also carries copies
for Switch, PS4 and PS5 that often have fewer layers. Edits address the PC copy.
`replace-texture` is the exception: it changes every copy.

Recipe:
{
  "source": "data/hd/vfx/particles/missiles/mephisto_missile/vfx_mephisto_missile.particles",
  "output": "data/hd/vfx/particles/mymod/my_skull.particles",
  "textures": [ {"png": "art/seal.png", "texture": "data/hd/vfx/textures/mymod/seal.texture", "size": 256} ],
  "edits": [
    {"op": "property", "layer": "tail", "renderer": 0, "name": "Blend.TextureBase",
     "value": "data/hd/vfx/textures/mymod/seal.texture"},
    {"op": "property", "layer": "tail", "renderer": 0, "name": "SoftParticles.SoftnessDistance", "value": [2.0]},
    {"op": "replace-texture", "from": "t_fx_hemisphere_exponential", "to": "data/hd/vfx/textures/mymod/seal.texture"},
    {"op": "constant", "layer": "tail", "script": 1, "index": 6, "value": [1.5]},
    {"op": "curve", "layer": "tail", "sampler": 0, "times": [0, 1], "values": [1, 0], "tangents": [0, 0, 0, 0]},
    {"op": "attribute", "name": "Fade", "default": [1.0]}
  ]
}
A layer is named by its name, or by "#<n>" (its position, from 0) when names repeat.
"png" paths are relative to the recipe file. "size" (optional) resizes to size x size.

usage:
  EffectEdit.py list [regex]                     particle files in the game
  EffectEdit.py missiles [regex]                 missile name -> HD definition -> particle files
  EffectEdit.py show <source> [--json] [--scripts]
  EffectEdit.py apply <recipe.json> --out <mod folder>
  <source> is an archive path (data/hd/...) or a file on disk. --game or D2R_PATH names the game folder.
"""
import argparse
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import HdTexture  # noqa: E402
import PopcornVm  # noqa: E402
from PopcornBaked import Baked  # noqa: E402

SAMPLER_DATA = 'CParticleNodeSamplerData_'
PROP_TYPES = {-1: 'feature', 1: 'bool', 3: 'int', 4: 'int4', 7: 'float', 8: 'float4', 12: 'texture', 13: 'atlas', 14: 'mesh'}
RENDERER_KINDS = [('GeometryBillboard', 'billboard'), ('GeometryRibbon', 'ribbon'), ('GeometryMesh', 'mesh'),
                  ('GeometryLight', 'light'), ('Decal', 'decal')]
SCRIPT_ROLES = ['spawn', 'update', 'update (second copy)']


class EditError(Exception):
    pass


class Effect:
    def __init__(self, data, source=''):
        self.source = source
        self.baked = Baked(data)
        plats = self.baked.platforms()
        if 'PC' not in plats:
            raise EditError('the effect has no PC copy')
        first = plats['PC'].number
        later = sorted(o.number for o in plats.values() if o.number > first)
        self.pc = (first, later[0] if later else len(self.baked.objects) + 1)
        self.platform_names = sorted(plats)
        self._layers = None

    # -- structure --------------------------------------------------------
    def layers(self):
        """[{'index', 'name', 'object', 'parent', 'renderers': [obj], 'scripts': [obj], 'samplers': [(name, obj)]}]"""
        if self._layers is not None:
            return self._layers
        b = self.baked
        lo, hi = self.pc
        objs = [o for o in b.objects if lo < o.number < hi]
        layer_objs = [o for o in objs if o.cls_name == 'CLayerCompileCache']
        bounds = [o.number for o in layer_objs] + [hi]
        number_to_index = {o.number: i for i, o in enumerate(layer_objs)}
        out = []
        for i, lay in enumerate(layer_objs):
            inside = [o for o in objs if bounds[i] < o.number < bounds[i + 1]]
            samplers = []
            for k, o in enumerate(inside):
                if o.cls_name == 'CLayerCompileCacheSampler':
                    nxt = inside[k + 1] if k + 1 < len(inside) else None
                    if nxt is not None and nxt.cls_name.startswith(SAMPLER_DATA):
                        samplers.append((o.string(0) or '', nxt))
            scripts = [b.obj(n) for n in (lay.ints(9) or [])]
            out.append({
                'index': i, 'name': lay.string(20) or '', 'object': lay,
                'parent': number_to_index.get(lay.int(17, 0)),
                'renderers': [o for o in inside if o.cls_name == 'CLayerCompileCacheRenderer'],
                'scripts': [o for o in scripts if o is not None and o.cls_name == 'CCompilerBlobCache'],
                'samplers': samplers,
            })
        self._layers = out
        return out

    def layer(self, ref):
        layers = self.layers()
        if isinstance(ref, int):
            ref = '#%d' % ref
        ref = str(ref)
        if ref.startswith('#'):
            i = int(ref[1:])
            if not 0 <= i < len(layers):
                raise EditError('no layer %s (the effect has %d)' % (ref, len(layers)))
            return layers[i]
        found = [l for l in layers if l['name'] == ref]
        if not found:
            raise EditError('no layer named "%s" (layers: %s)' % (ref, ', '.join(l['name'] or '#%d' % l['index'] for l in layers)))
        if len(found) > 1:
            raise EditError('%d layers are named "%s"; use "#<n>" (%s)' % (len(found), ref, ', '.join('#%d' % l['index'] for l in found)))
        return found[0]

    def properties(self, renderer):
        """[(name, property object)] of a renderer, in file order."""
        out = []
        for n in renderer.ints(2) or []:
            o = self.baked.obj(n)
            if o is not None and o.fields is not None:
                out.append((o.string(0) or '', o))
        return out

    def attributes(self):
        return self.baked.of('CParticleAttributeDeclaration')

    # -- description ------------------------------------------------------
    def describe(self, scripts=False):
        layers = []
        for lay in self.layers():
            renderers = []
            for ri, r in enumerate(lay['renderers']):
                props = []
                kind = 'other'
                names = set()
                for name, o in self.properties(r):
                    names.add(name)
                    t = o.int(1, -1)
                    entry = {'name': name, 'type': PROP_TYPES.get(t, 'type%d' % t)}
                    v = o.get(2)
                    if o.has(3):
                        entry['value'] = o.string(3)
                    elif v is not None:
                        if PROP_TYPES.get(t) in ('float', 'float4'):
                            entry['value'] = [round(x, 6) for x in struct.unpack('<4f', v)]
                        else:
                            entry['value'] = list(struct.unpack('<4i', v))
                    else:
                        entry['value'] = None
                    props.append(entry)
                for marker, label in RENDERER_KINDS:
                    if marker in names:
                        kind = label
                        break
                renderers.append({'index': ri, 'object': r.number, 'kind': kind,
                                  'material': (r.string(4) or '').split('/')[-1].replace('.pkma', ''), 'properties': props})
            script_list = []
            for si, s in enumerate(lay['scripts']):
                prog = s.program()
                ins = PopcornVm.decode(prog['code'])
                use = _constant_types(ins)
                consts = []
                for ci, c in enumerate(prog['constants']):
                    t = use.get(ci, 'f1')
                    lanes = struct.unpack('<4I', c[:16])
                    if t[0] == 'f' and all(x < 0x00800000 for x in lanes) and any(lanes):
                        t = 'i' + t[1:]     # too small to be a real float: a whole number the script reads as bits
                    if PopcornVm.TYPE_WIDTH.get(t, 1) == 1 and len(set(lanes)) > 1:
                        t = t[0] + '4'      # used one part at a time, but the lanes differ: show the vector
                    consts.append({'index': ci, 'type': t, 'value': [_clean(x) for x in PopcornVm.constant_value(c, t)]})
                entry = {'index': si, 'object': s.number, 'role': SCRIPT_ROLES[si] if si < len(SCRIPT_ROLES) else 'script %d' % si,
                         'instructions': len(ins), 'functions': s.functions(), 'constants': consts}
                if scripts:
                    entry['listing'] = s.disassemble()
                script_list.append(entry)
            samplers = []
            for xi, (name, o) in enumerate(lay['samplers']):
                entry = {'index': xi, 'name': name, 'kind': o.cls_name[len(SAMPLER_DATA):].lower(), 'object': o.number}
                if o.cls_name.endswith('_Curve'):
                    entry['times'] = [_clean(x) for x in (o.floats(17) or [])]
                    entry['values'] = [_clean(x) for x in (o.floats(18) or [])]
                    entry['tangents'] = [_clean(x) for x in (o.floats(19) or [])]
                samplers.append(entry)
            layers.append({'index': lay['index'], 'name': lay['name'], 'parent': lay['parent'], 'object': lay['object'].number,
                           'renderers': renderers, 'scripts': script_list, 'samplers': samplers})
        attrs = []
        for a in self.attributes():
            entry = {'name': a.string(0) or ''}
            for key, fid in (('default', 14), ('max', 44)):
                if a.has(fid):
                    entry[key] = [_clean(x) for x in a.floats(fid)]
            attrs.append(entry)
        return {'source': self.source, 'platforms': self.platform_names, 'objects': len(self.baked.objects),
                'attributes': attrs, 'layers': layers}

    def textures(self):
        """Every texture and mesh path the PC copy names."""
        out = []
        for lay in self.layers():
            for r in lay['renderers']:
                for _, o in self.properties(r):
                    if o.has(3) and o.string(3) and o.string(3) not in out:
                        out.append(o.string(3))
        return out

    # -- edits ------------------------------------------------------------
    def apply(self, edit):
        op = edit.get('op')
        handler = {'property': self._edit_property, 'replace-texture': self._edit_replace, 'constant': self._edit_constant,
                   'curve': self._edit_curve, 'attribute': self._edit_attribute}.get(op)
        if handler is None:
            raise EditError('unknown op "%s"' % op)
        handler(edit)

    def _renderer(self, edit):
        lay = self.layer(edit.get('layer', '#0'))
        i = int(edit.get('renderer', 0))
        if not 0 <= i < len(lay['renderers']):
            raise EditError('layer "%s" has %d renderer(s), not %d' % (lay['name'], len(lay['renderers']), i + 1))
        return lay['renderers'][i]

    def _edit_property(self, edit):
        r = self._renderer(edit)
        name = edit['name']
        prop = dict(self.properties(r)).get(name)
        if prop is None:
            raise EditError('the renderer has no property "%s"' % name)
        t = PROP_TYPES.get(prop.int(1, -1), '')
        value = edit['value']
        if isinstance(value, str):
            if t not in ('texture', 'mesh', 'atlas'):
                raise EditError('"%s" is a %s, not a path' % (name, t))
            prop.set_string(3, value)
            return
        if t in ('texture', 'mesh', 'atlas'):
            raise EditError('"%s" takes a path' % name)
        if not isinstance(value, list):
            value = [value]
        old = prop.get(2)
        is_float = t in ('float', 'float4')
        current = list(struct.unpack('<4f' if is_float else '<4i', old)) if old is not None else [0, 0, 0, 0]
        if len(value) > 4:
            raise EditError('"%s" holds at most four numbers' % name)
        for i, v in enumerate(value):
            current[i] = float(v) if is_float else int(v)
        if len(value) == 1 and is_float and old is None:
            current = [float(value[0])] * 4
        prop.set(2, struct.pack('<4f' if is_float else '<4i', *current))

    def _edit_replace(self, edit):
        needle = edit['from'].lower()
        new = edit['to']
        count = 0
        for o in self.baked.of('CLayerCompileCacheRendererProperty'):
            if o.fields is None or not o.has(3):
                continue
            cur = (o.string(3) or '')
            base = cur.lower().rsplit('/', 1)[-1].rsplit('.', 1)[0]
            if cur.lower() == needle or base == needle.rsplit('/', 1)[-1].rsplit('.', 1)[0]:
                if edit.get('name') and o.string(0) != edit['name']:
                    continue
                o.set_string(3, new)
                count += 1
        if not count:
            raise EditError('no property uses "%s"' % edit['from'])

    def _edit_constant(self, edit):
        lay = self.layer(edit.get('layer', '#0'))
        si = int(edit.get('script', 0))
        if not 0 <= si < len(lay['scripts']):
            raise EditError('layer "%s" has %d script(s)' % (lay['name'], len(lay['scripts'])))
        targets = [lay['scripts'][si]]
        # the second update script is a copy of the first: keep them alike
        if edit.get('both', True) and si in (1, 2) and len(lay['scripts']) == 3:
            a, b = lay['scripts'][1], lay['scripts'][2]
            if a.program()['code'] == b.program()['code'] and a.program()['constants'] == b.program()['constants']:
                targets = [a, b]
        for s in targets:
            prog = s.program()
            ci = int(edit['index'])
            if not 0 <= ci < len(prog['constants']):
                raise EditError('the script has %d constant(s)' % len(prog['constants']))
            value = edit['value'] if isinstance(edit['value'], list) else [edit['value']]
            as_int = edit.get('as') == 'int'
            fmt = '<8i' if as_int else '<8f'
            lanes = list(struct.unpack(fmt, prog['constants'][ci]))
            conv = int if as_int else float
            if len(value) == 1:
                lanes = [conv(value[0])] * 8
            elif len(value) <= 4:
                for i, v in enumerate(value):       # a vector sits in lanes 0-3 and again in 4-7
                    lanes[i] = lanes[i + 4] = conv(v)
            elif len(value) == 8:
                lanes = [conv(v) for v in value]
            else:
                raise EditError('a constant takes 1 to 4 numbers, or all 8 lanes')
            prog['constants'][ci] = struct.pack(fmt, *lanes)
            s.set_program(prog)

    def _edit_curve(self, edit):
        lay = self.layer(edit.get('layer', '#0'))
        i = int(edit.get('sampler', 0))
        if not 0 <= i < len(lay['samplers']):
            raise EditError('layer "%s" has %d sampler(s)' % (lay['name'], len(lay['samplers'])))
        o = lay['samplers'][i][1]
        if not o.cls_name.endswith('_Curve'):
            raise EditError('sampler %d of layer "%s" is not a curve' % (i, lay['name']))
        times = [float(x) for x in edit.get('times', o.floats(17) or [])]
        values = [float(x) for x in edit.get('values', o.floats(18) or [])]
        if not times or len(values) % len(times):
            raise EditError('a curve needs the same number of values for every key')
        per_key = len(values) // len(times)
        tangents = edit.get('tangents')
        if tangents is None:
            old = o.floats(19) or []
            tangents = old if len(old) == 2 * len(values) else [0.0] * (2 * len(values))
        if len(tangents) != 2 * per_key * len(times):
            raise EditError('a curve needs two tangents per value (%d here)' % (2 * per_key * len(times)))
        o.set_floats(17, times)
        o.set_floats(18, values)
        o.set_floats(19, [float(x) for x in tangents])

    def _edit_attribute(self, edit):
        for a in self.attributes():
            if a.string(0) == edit['name']:
                for key, fid in (('default', 14), ('max', 44)):
                    if key in edit:
                        cur = a.floats(fid) or [0.0, 0.0, 0.0, 0.0]
                        for i, v in enumerate(edit[key][:4]):
                            cur[i] = float(v)
                        a.set_floats(fid, cur)
                return
        raise EditError('no attribute "%s"' % edit['name'])

    def encode(self):
        out = self.baked.encode()
        Baked(out)  # must read back
        return out


def _clean(x):
    if isinstance(x, float):
        if x != x or x in (float('inf'), float('-inf')):
            return str(x)
        return float('%.6g' % x)
    return x


def _constant_types(instructions):
    """constant index -> the operand type it is used as (first use wins)."""
    out = {}
    for ins in instructions:
        for index, kind, typ in ins.get('regs', []):
            if kind == 0 and index not in out:
                out[index] = PopcornVm.TYPE_NAMES.get(typ, 'f1') or 'f1'
    return out


# ---------------------------------------------------------------------------
class Game:
    """Reads the game archive (lazily) and files on disk."""

    def __init__(self, game=None):
        self.game = game or os.environ.get('D2R_PATH')
        self._archive = None
        self._names = None

    def archive(self):
        if self._archive is None:
            if not self.game:
                raise EditError('pass --game or set D2R_PATH to the folder that contains D2R.exe')
            from d2r_casc import D2RArchive
            self._archive = D2RArchive(self.game)
        return self._archive

    def read(self, source, roots=()):
        """Bytes of an archive path or a disk file. `roots`: mod folders searched first for data/... paths."""
        if os.path.isfile(source):
            return open(source, 'rb').read()
        rel = source.replace('\\', '/')
        rel = rel[5:] if rel.lower().startswith('data/') else rel
        for root in roots:
            p = os.path.join(root, rel.replace('/', os.sep))
            if os.path.isfile(p):
                return open(p, 'rb').read()
        data = self.archive().read(source)
        if data is None:
            raise EditError('not found: %s' % source)
        return data

    def names(self):
        if self._names is None:
            a = self.archive()
            lister = getattr(a, 'list', None) or getattr(a, 'files', None)
            if lister is None:
                raise EditError('the archive reader cannot list files')
            self._names = sorted(str(n).replace('\\', '/') for n in lister())
        return self._names

    def find(self, pattern, suffix):
        rx = re.compile(pattern or '.', re.I)
        return [n if n.lower().startswith('data/') else 'data/' + n for n in self.names() if n.lower().endswith(suffix) and rx.search(n)]


def run_recipe(recipe, game, out_dir=None, base_dir='.'):
    """Applies a recipe. Returns (particle bytes, {texture path: bytes}, description). Writes when out_dir is given."""
    roots = [out_dir] if out_dir else []
    effect = Effect(game.read(recipe['source'], roots), recipe['source'])
    textures = {}
    for t in recipe.get('textures', []):
        from PIL import Image
        png = t['png'] if os.path.isabs(t['png']) else os.path.join(base_dir, t['png'])
        if not os.path.isfile(png):
            raise EditError('no such image: %s' % png)
        img = Image.open(png).convert('RGBA')
        if t.get('size'):
            img = img.resize((int(t['size']), int(t['size'])), Image.LANCZOS)
        textures[t['texture']] = HdTexture.from_image(img)
    for i, edit in enumerate(recipe.get('edits', [])):
        try:
            effect.apply(edit)
        except (EditError, KeyError, ValueError, struct.error) as e:
            raise EditError('edit %d (%s): %s' % (i + 1, edit.get('op'), e))
    data = effect.encode()
    if out_dir:
        if not recipe.get('output'):
            raise EditError('the recipe has no "output" path')
        for path, content in [(recipe['output'], data)] + list(textures.items()):
            rel = path.replace('\\', '/')
            rel = rel[5:] if rel.lower().startswith('data/') else rel
            full = os.path.join(out_dir, rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, 'wb') as f:
                f.write(content)
    return data, textures, effect


def manifest(recipe, effect):
    """What a mod script needs: which particle file replaces which, and the textures to declare."""
    own = sorted(t['texture'] for t in recipe.get('textures', []))
    named = [p for p in effect.textures() if p.lower().endswith('.texture')]
    return {'particles': {recipe['source']: recipe.get('output', '')}, 'textures': own, 'uses': named}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['list', 'missiles', 'show', 'apply'])
    ap.add_argument('target', nargs='?')
    ap.add_argument('--game')
    ap.add_argument('--out')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--scripts', action='store_true')
    args = ap.parse_args()
    game = Game(args.game)
    try:
        if args.command == 'list':
            print('\n'.join(game.find(args.target, '.particles')))
        elif args.command == 'missiles':
            table = json.loads(game.read('data/hd/missiles/missiles.json').decode('utf-8-sig'))
            rx = re.compile(args.target or '.', re.I)
            for name, file in table.items():
                if name == 'dependencies' or not rx.search(name) or file == 'null':
                    continue
                try:
                    d = json.loads(game.read('data/hd/missiles/%s.json' % file).decode('utf-8-sig'))
                    parts = [c['filename'] for e in d['entities'] for c in e['components'] if c['type'] == 'VfxDefinitionComponent']
                except EditError:
                    parts = ['(no definition)']
                print('%s -> %s: %s' % (name, file, ', '.join(parts)))
        elif args.command == 'show':
            if not args.target:
                ap.error('show needs a source')
            effect = Effect(game.read(args.target), args.target)
            d = effect.describe(scripts=args.scripts)
            if args.json:
                print(json.dumps(d, indent=1))
            else:
                print_description(d)
        elif args.command == 'apply':
            if not args.target or not args.out:
                ap.error('apply needs a recipe file and --out')
            recipe = json.load(open(args.target, encoding='utf-8'))
            data, textures, effect = run_recipe(recipe, game, args.out, os.path.dirname(os.path.abspath(args.target)))
            print(json.dumps({'written': recipe['output'], 'bytes': len(data), 'manifest': manifest(recipe, effect)}, indent=1))
    except EditError as e:
        print('error: %s' % e, file=sys.stderr)
        return 1
    return 0


def print_description(d):
    print('%s  (%d objects; copies for %s)' % (d['source'], d['objects'], ', '.join(d['platforms'])))
    for a in d['attributes']:
        print('attribute %s: default %s' % (a['name'], a.get('default')))
    for lay in d['layers']:
        parent = '' if lay['parent'] is None else '  (inside #%d)' % lay['parent']
        print('\nlayer #%d "%s"%s' % (lay['index'], lay['name'], parent))
        for r in lay['renderers']:
            print('  renderer %d: %s, %s' % (r['index'], r['kind'], r['material']))
            for p in r['properties']:
                if p['type'] == 'feature' or p['value'] is None:
                    continue
                print('     %-40s %s' % (p['name'], p['value']))
        for s in lay['scripts']:
            print('  script %d (%s): %d instructions, calls %s' % (s['index'], s['role'], s['instructions'], ', '.join(f.split('_')[0] for f in s['functions'] if f) or 'nothing'))
            for c in s['constants']:
                print('     constant %d (%s): %s' % (c['index'], c['type'], c['value']))
            if 'listing' in s:
                print('\n'.join('       ' + line for line in s['listing'].split('\n')))
        for x in lay['samplers']:
            extra = ''
            if x['kind'] == 'curve':
                extra = ': times %s values %s' % (x['times'], x['values'])
            print('  sampler %d "%s" (%s)%s' % (x['index'], x['name'], x['kind'], extra))


if __name__ == '__main__':
    sys.exit(main())
