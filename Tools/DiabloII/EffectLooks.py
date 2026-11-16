"""A mod's own HD effect looks, made from stock missile effects by rules.

Every effect mod's dev/build_effects.py did the same thing in its own copy: for each look, read a
stock HD missile definition, go through the PC copy of each of its particle files, turn a list of
rules into an EffectEdit recipe (swap textures for drawn art, swap meshes, retint colour
constants, change settings), run the recipe, check that every rule fitted something, and write a
manifest that the mod's install script reads. This module is that loop, once:

    import EffectLooks as L
    B, BL, GR = L.BASE, L.BLEND, L.GRADIENT
    LOOKS = {
        'crescent': ('holy_bolt', [L.tex(B, 'holybolt_core', 'pdo_crescent'),
                                   L.tex(GR, '*', 'pdo_grad_gold'),
                                   L.tint((0.9, 0.8, 0.3), (1.0, 0.85, 0.4))], []),
    }
    builder = L.Builder(game, MOD, 'pdo', drawn=TEXTURES)
    manifest = builder.build(LOOKS)
    builder.clean()
    L.write_block(os.path.join(MOD, 'mod.js'), START, END, 'AUTHORED', manifest)

A look is (stock definition in hd/missiles without .json, rules, meshes); meshes are
{"model": path, "textures": [paths]} the look adds (its models and their textures go into the
manifest). Rules (tuples, as the mods wrote them, or these helpers):

    tex(property, part of the texture's name, art, layers=None)
        the first tex rule that fits a texture property wins. The property is its full name
        ("Blend.TextureBase") or a feature ("Blend" fits every Blend.* property). The name part
        is matched in lower case; "*" fits any texture but the defaults (White, Black,
        Default_AlphaMap), which only their own full name fits. art: a drawn texture's name
        (put at texture_path) or a full data/... path.
    mesh(layer index, model)          the mesh a mesh layer draws (model: path or {"model": ...})
    tint(colour now, colour new, layers=None)
        every f3 / f4 script constant whose first three numbers are within 0.02 of `now`
        (its fourth number is kept)
    vec(colour now, colour new, layers=None)
        a colour a script builds as vector(a, b, c, ...) from three single numbers; a number
        the script also uses elsewhere is left alone (and reported)
    prop(property, value, layers=None) a setting of every renderer that has it
    num(number now, number new, layers=None)
        every single-number constant of that value (only that script, not its copy)
layers: None (all) or layer indices.

On a layer that reads an atlas (Atlas.SubDiv more than 1x1), drawn art that is not listed in
`atlas` as fitting that grid is not put in the slots read by the particle's UVs (base, blend,
masks); `atlas` = {name: (cols, rows) or None for art that fits any}. Without `atlas` this check
is off.

The builder writes the drawn textures through the recipes (PNG files in art_dir named after the
texture), the particle files at output_path, and a recipe per particle file in recipes_dir.
`on_effect(look, name, before, after, edits)` (optional) is called for every file written, with
the EffectEdit descriptions before and after (for stills).
"""
import json
import os
import re

import EffectEdit

BASE, BLEND, BLEND_MASK, ALPHA_MASK = 'Blend.TextureBase', 'Blend.TextureBlend', 'BlendMask.Mask', 'AlphaMask.Mask'
GRADIENT, DIFFUSE, NORMAL, DISTORT_MASK = 'GradientRemap.GradientMap', 'Diffuse.DiffuseMap', 'Lit.NormalMap', 'UVDistortion.MaskDistort'
UV_SLOTS = (BASE, BLEND, BLEND_MASK, ALPHA_MASK)
DEFAULT_TEXTURES = ('white', 'black', 'default_alphamap')
VECTOR = re.compile(r'vector\(f1\(([-\d.e+]+)\)\[c(\d+)\], f1\(([-\d.e+]+)\)\[c(\d+)\], f1\(([-\d.e+]+)\)\[c(\d+)\]')


def tex(prop, stem, art, layers=None):
    return ('tex', prop, stem, art, layers)


def mesh(layer, model):
    return ('mesh', layer, model)


def tint(old, new, layers=None):
    return ('tint', old, new, layers)


def vec(old, new, layers=None):
    return ('vec', old, new, layers)


def prop(name, value, layers=None):
    return ('prop', name, value, layers)


def num(old, new, layers=None):
    return ('num', old, new, layers)


def _layers(rule, at):
    return rule[at] if len(rule) > at else None


def _layer_ok(layers, index):
    return layers is None or index in layers


def _numeric(value):
    return isinstance(value, (list, tuple)) and len(value) >= 3 and all(isinstance(x, (int, float)) for x in value[:3])


def close(a, b, tolerance=0.02):
    """The first three numbers of `a` within `tolerance` of `b`."""
    return _numeric(a) and all(abs(x - y) < tolerance for x, y in zip(a, b))


def _prop_fits(rule_prop, name):
    return rule_prop == name or name.startswith(rule_prop + '.')


def _stem(path):
    return path.lower().rsplit('/', 1)[-1].rsplit('.', 1)[0]


class Builder:
    def __init__(self, game, mod_dir, prefix, drawn=(), texture_path=None, output_path=None,
                 recipes_dir=None, art_dir=None, atlas=None, on_effect=None):
        """game: EffectEdit.Game; mod_dir: the mod folder; prefix: the mod's short tag (file names
        and the default folders hd/vfx/textures/<prefix>, hd/vfx/particles/<prefix>); drawn: the
        names of the textures the mod draws (only those that some look uses are kept)."""
        self.game = game
        self.mod = mod_dir
        self.prefix = prefix
        self.drawn = list(drawn)
        self.texture_path = texture_path or 'data/hd/vfx/textures/%s/%%s.texture' % prefix
        self.output_path = output_path or 'data/hd/vfx/particles/%s/%%s.particles' % prefix
        self.recipes = recipes_dir or os.path.join(mod_dir, 'effect_recipes')
        self.art = art_dir or os.path.join(mod_dir, 'effect_art')
        self.atlas = atlas
        self.on_effect = on_effect
        self.report = []
        self.used = set()           # drawn textures some look uses
        self.written = set()        # particle files (names) this run wrote

    # -- one look ----------------------------------------------------------
    def look(self, name, definition, rules, meshes=()):
        hd = json.loads(self.game.read('data/hd/missiles/%s.json' % definition).decode('utf-8-sig'))
        sources = []
        for entity in hd['entities']:
            for comp in entity['components']:
                if comp['type'] == 'VfxDefinitionComponent' and comp['filename'] and comp['filename'] not in sources:
                    sources.append(comp['filename'])
        particles, textures, extra, hit = {}, set(), set(), set()
        for source in sources:
            effect = EffectEdit.Effect(self.game.read(source), source)
            desc = effect.describe(scripts=True)
            edits = self._edits(name, desc, rules, hit, textures, extra)
            if not edits:
                continue
            file_name = '%s_%s_%s' % (self.prefix, name, re.sub(r'[^a-z0-9]+', '_', _stem(source)))
            drawn_here = sorted({_stem(e['value']) for e in edits
                                 if e['op'] == 'property' and isinstance(e['value'], str) and self._is_drawn(e['value'])})
            art_rel = os.path.relpath(self.art, self.recipes).replace(os.sep, '/')
            recipe = {'source': source, 'output': self.output_path % file_name,
                      'textures': [{'png': '%s/%s.png' % (art_rel, t), 'texture': self.texture_path % t} for t in drawn_here],
                      'edits': edits}
            os.makedirs(self.recipes, exist_ok=True)
            with open(os.path.join(self.recipes, file_name + '.json'), 'w', encoding='utf-8') as out:
                json.dump(recipe, out, indent=1)
            data, _, after = EffectEdit.run_recipe(recipe, self.game, self.mod, self.recipes)
            particles[source] = recipe['output']
            self.written.add(file_name)
            self.report.append('%-13s %-52s %3d edits, %d bytes' % (name, file_name, len(edits), len(data)))
            if self.on_effect:
                self.on_effect(name, file_name, desc, after.describe(scripts=True), edits)
        missed = [rules[i] for i in range(len(rules)) if i not in hit]
        if missed:
            raise EffectEdit.EditError('%s: rules that fit nothing in %s: %s' % (name, definition, missed))
        self.used |= textures
        return {
            'def': definition, 'particles': particles,
            'textures': sorted(self.texture_path % t for t in textures) + sorted(extra)
                        + sorted({t for m in meshes for t in m.get('textures', [])}),
            'models': sorted({m['model'] for m in meshes}),
        }

    def _is_drawn(self, path):
        folder = self.texture_path.rsplit('/', 1)[0] + '/'
        return path.startswith(folder)

    def _edits(self, look, desc, rules, hit, textures, extra):
        edits = []
        for lay in desc['layers']:
            li = lay['index']
            for r in lay['renderers']:
                values = {p['name']: p['value'] for p in r['properties']}
                sub = values.get('Atlas.SubDiv')
                atlas = tuple(sub[:2]) if isinstance(sub, list) and len(sub) >= 2 and sub[0] * sub[1] > 1 else None
                for p in r['properties']:
                    def edit(value, name=p['name'], ri=r['index']):
                        return {'op': 'property', 'layer': '#%d' % li, 'renderer': ri, 'name': name, 'value': value}
                    if p['name'] == 'General.Mesh':
                        for i, rule in enumerate(rules):
                            if rule[0] == 'mesh' and rule[1] == li:
                                model = rule[2]['model'] if isinstance(rule[2], dict) else rule[2]
                                edits.append(edit(model))
                                hit.add(i)
                        continue
                    for i, rule in enumerate(rules):
                        if rule[0] == 'prop' and rule[1] == p['name'] and _layer_ok(_layers(rule, 3), li):
                            edits.append(edit(rule[2]))
                            hit.add(i)
                    if p['type'] != 'texture' or not isinstance(p['value'], str):
                        continue
                    stem = _stem(p['value'])
                    default = stem in DEFAULT_TEXTURES
                    for i, rule in enumerate(rules):
                        if rule[0] != 'tex' or not _prop_fits(rule[1], p['name']) or not _layer_ok(_layers(rule, 4), li):
                            continue
                        want = rule[2].lower()
                        if not (want == stem or (not default and (want == '*' or want in stem))):
                            continue
                        art = rule[3]
                        full = art.startswith('data/')
                        if (self.atlas is not None and atlas and p['name'] in UV_SLOTS and not full
                                and (art not in self.atlas or self.atlas[art] not in (None, atlas))):
                            self.report.append('%-13s skipped #%d %s %s: the layer reads a %dx%d atlas' % (look, li, p['name'], art, atlas[0], atlas[1]))
                            hit.add(i)
                            break
                        edits.append(edit(art if full else self.texture_path % art))
                        (extra if full else textures).add(art)
                        hit.add(i)
                        break
            for sc in lay.get('scripts', []):
                for c in sc.get('constants', []):
                    if c.get('type') in ('f3', 'f4') and _numeric(c.get('value')):
                        for i, rule in enumerate(rules):
                            if rule[0] == 'tint' and _layer_ok(_layers(rule, 3), li) and close(c['value'], rule[1]):
                                edits.append({'op': 'constant', 'layer': '#%d' % li, 'script': sc['index'], 'index': c['index'],
                                              'value': list(rule[2]) + list(c['value'][3:4])})
                                hit.add(i)
                for c in sc.get('constants', []):
                    if c.get('type') == 'f1' and isinstance(c.get('value', [None])[0], (int, float)):
                        for i, rule in enumerate(rules):
                            if rule[0] == 'num' and _layer_ok(_layers(rule, 3), li) and abs(c['value'][0] - rule[1]) < 1e-5:
                                edits.append({'op': 'constant', 'layer': '#%d' % li, 'script': sc['index'], 'index': c['index'],
                                              'value': [rule[2]], 'both': False})
                                hit.add(i)
                listing = sc.get('listing', '')
                for m in VECTOR.finditer(listing):
                    now = [float(m.group(1)), float(m.group(3)), float(m.group(5))]
                    idx = [int(m.group(2)), int(m.group(4)), int(m.group(6))]
                    for i, rule in enumerate(rules):
                        if rule[0] != 'vec' or not _layer_ok(_layers(rule, 3), li) or not close(now, rule[1]):
                            continue
                        for lane in range(3):
                            if abs(rule[2][lane] - now[lane]) < 1e-6:
                                continue
                            if listing.count('[c%d]' % idx[lane]) != 1:
                                self.report.append('%-13s left #%d script %d constant %d (%g): the script uses it elsewhere'
                                                   % (look, li, sc['index'], idx[lane], now[lane]))
                                continue
                            edits.append({'op': 'constant', 'layer': '#%d' % li, 'script': sc['index'], 'index': idx[lane],
                                          'value': [rule[2][lane]], 'both': False})
                            hit.add(i)
        return edits

    # -- all looks -----------------------------------------------------------
    def build(self, looks):
        """{look: (definition, rules[, meshes])} -> the manifest {look: {def, particles, textures, models}}."""
        out = {}
        for name, entry in looks.items():
            definition, rules = entry[0], entry[1]
            meshes = entry[2] if len(entry) > 2 else ()
            out[name] = self.look(name, definition, rules, meshes)
        return out

    def clean(self):
        """Removes what an earlier run of this builder left: drawn textures no look uses now, and
        particle files and recipes named like this builder's ("<prefix>_...") that this run did
        not write. A recipe is only removed when its output is in this builder's particle folder,
        so recipes saved with the effect editor (same folder) stay. Returns the removed paths."""
        removed = []
        for name in self.drawn:
            full = os.path.join(self.mod, *(self.texture_path % name)[len('data/'):].split('/'))
            if name not in self.used and os.path.exists(full):
                os.remove(full)
                removed.append(full)
        ours = self.prefix + '_'
        out_folder = self.output_path.rsplit('/', 1)[0] + '/'
        folder = os.path.join(self.mod, *out_folder[len('data/'):-1].split('/'))
        for directory, suffix in ((folder, '.particles'), (self.recipes, '.json')):
            if not os.path.isdir(directory):
                continue
            for f in os.listdir(directory):
                name = f[:-len(suffix)]
                if not f.endswith(suffix) or not name.startswith(ours) or name in self.written:
                    continue
                path = os.path.join(directory, f)
                if suffix == '.json' and not self._builder_recipe(path, out_folder):
                    continue
                os.remove(path)
                removed.append(path)
        return removed

    @staticmethod
    def _builder_recipe(path, out_folder):
        try:
            with open(path, encoding='utf-8') as f:
                output = json.load(f).get('output', '')
        except (OSError, ValueError, AttributeError):
            return False
        return isinstance(output, str) and output.startswith(out_folder)


def write_block(mod_js, start, end, const_name, manifest):
    """Rewrites the `const <name> = ...;` block between the start and end marker lines of mod.js."""
    with open(mod_js, encoding='utf-8', newline='') as f:
        text = f.read()
    block = '%s\nconst %s = %s;\n%s' % (start, const_name, json.dumps(manifest, indent=2), end)
    pattern = re.compile(re.escape(start) + r'.*?' + re.escape(end), re.S)
    if not pattern.search(text):
        raise SystemExit('%s has no %s ... %s block' % (mod_js, start, end))
    with open(mod_js, 'w', encoding='utf-8', newline='') as f:
        f.write(pattern.sub(lambda m: block, text))


def write_manifest(path, manifest):
    with open(path, 'w', encoding='utf-8', newline='\n') as out:
        json.dump(manifest, out, indent=2)
        out.write('\n')
