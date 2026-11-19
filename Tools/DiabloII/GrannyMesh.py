"""Edit the meshes of a Granny model in place and write it back uncompressed.

Vertex positions are read as floats, changed, and stored again with a new
quantisation scale and bounding box. Vertex count, triangles, skin weights and
the skeleton are untouched, so the result plays the donor's animations.

    model = GrannyMesh.Model(path)
    for mesh in model.meshes:
        v = mesh.positions()            # N x 3 floats, model space, bind pose
        mesh.set_positions(v * 1.1)
    model.save(out_path)

`reshape` applies the two edits used to turn a Spike Fiend into a Quill Bear:
longer and thicker quills, and a heavier torso.
"""
import struct

import numpy as np

import GrannyFile as granny


def _offsets(g, members):
    out = {}
    offset = 0
    for m in members:
        out[m['name']] = (offset, m)
        offset += g.member_size(m)
    return out


class Mesh:
    def __init__(self, g, members, at):
        self.g = g
        self.at = at
        self.fields = _offsets(g, members)
        self.name = g.cstr(g.ptr((at[0], at[1] + self.fields['Name'][0])))
        vd_at = g.ptr((at[0], at[1] + self.fields['PrimaryVertexData'][0]))
        self.layout = g.read_type(g.ptr(vd_at))
        self.count = g.i32((vd_at[0], vd_at[1] + 8))
        self.vertex_at = g.ptr((vd_at[0], vd_at[1] + 12))
        self.stride = g.struct_size(self.layout)
        self.vfields = _offsets(g, self.layout)
        kind = self.vfields['Position'][1]['kind']
        if kind not in (15, 17):
            raise ValueError(f'{self.name}: positions are {granny.DT[kind]}, only normalised int16 is handled')
        # Extended data: VertexScale, bbMin, bbMax.
        ext_at = (at[0], at[1] + self.fields['ExtendedData'][0])
        ext_type = g.ptr(ext_at)
        self.ext_obj = g.ptr((ext_at[0], ext_at[1] + 8))
        self.ext_fields = _offsets(g, g.read_type(ext_type)) if ext_type and self.ext_obj else {}
        # Bone bindings: the names BoneIndices refer to.
        bind_off, bind_member = self.fields['BoneBindings']
        bind_count = g.i32((at[0], at[1] + bind_off))
        bind_at = g.ptr((at[0], at[1] + bind_off + 4))
        bind_members = g.read_type(bind_member['ref'])
        bind_size = g.struct_size(bind_members)
        self.bones = [g.cstr(g.ptr((bind_at[0], bind_at[1] + k * bind_size))) for k in range(bind_count)] if bind_at else []

    def _column(self, name, width, dtype):
        g = self.g
        section = g.sections[self.vertex_at[0]]
        raw = np.frombuffer(section, dtype=np.uint8, count=self.count * self.stride, offset=self.vertex_at[1])
        raw = raw.reshape(self.count, self.stride)
        offset = self.vfields[name][0]
        return raw[:, offset:offset + width].copy().view(dtype)

    def _ext_float(self, name, index=0):
        offset = self.ext_fields[name][0] + 4 * index
        return (self.ext_obj[0], self.ext_obj[1] + offset)

    def vertex_scale(self):
        if 'VertexScale' not in self.ext_fields:
            return 1.0
        at = self._ext_float('VertexScale')
        return struct.unpack_from('<f', self.g.sections[at[0]], at[1])[0] or 1.0

    def bounds(self):
        """(bbMin, bbMax) as stored in the mesh's extended data."""
        out = []
        for name in ('bbMin', 'bbMax'):
            at = self._ext_float(name)
            out.append(struct.unpack_from('<3f', self.g.sections[at[0]], at[1]))
        return tuple(out)

    def positions(self):
        return self._column('Position', 6, '<i2').astype(np.float64) / 32767.0 * self.vertex_scale()

    def weights(self):
        """(weights N x 4 in 0..1, bone names per vertex slot N x 4 as indices into self.bones)."""
        if 'BoneWeights' not in self.vfields:
            return None, None
        w = self._column('BoneWeights', 4, np.uint8).astype(np.float64) / 255.0
        i = self._column('BoneIndices', 4, np.uint8).astype(np.int64)
        return w, i

    def set_positions(self, positions):
        g = self.g
        positions = np.asarray(positions, dtype=np.float64)
        if positions.shape != (self.count, 3):
            raise ValueError('set_positions needs one x, y, z per existing vertex')
        reach = float(np.abs(positions).max()) or 1.0
        scale = self.vertex_scale()
        if reach > scale:
            # Only requantise when the mesh outgrew its old range; an edit that fits keeps
            # the stored scale, so unchanged vertices keep their exact bytes.
            if 'VertexScale' not in self.ext_fields:
                raise ValueError(f'{self.name}: no VertexScale to grow, positions must stay within -1..1')
            scale = reach
        quantised = np.clip(np.round(positions / scale * 32767.0), -32767, 32767).astype('<i2')
        section = g.sections[self.vertex_at[0]]
        offset = self.vfields['Position'][0]
        view = np.frombuffer(section, dtype=np.uint8, count=self.count * self.stride, offset=self.vertex_at[1])
        view = view.reshape(self.count, self.stride)      # a view on the bytearray: writes go into the section
        view[:, offset:offset + 6] = quantised.view(np.uint8).reshape(self.count, 6)
        if 'VertexScale' in self.ext_fields:
            at = self._ext_float('VertexScale')
            struct.pack_into('<f', g.sections[at[0]], at[1], scale)
        stored = quantised.astype(np.float64) / 32767.0 * scale
        for name, values in (('bbMin', stored.min(0)), ('bbMax', stored.max(0))):
            if name in self.ext_fields:
                for axis in range(3):
                    at = self._ext_float(name, axis)
                    struct.pack_into('<f', g.sections[at[0]], at[1], float(values[axis]))


class Model:
    def __init__(self, path):
        self.g = granny.load(path)
        g = self.g
        fields = _offsets(g, g.read_type(g.root_type))
        offset, member = fields['Meshes']
        at = (g.root_obj[0], g.root_obj[1] + offset)
        count = g.i32(at)
        target = g.ptr((at[0], at[1] + 4))
        members = g.read_type(member['ref'])
        self.meshes = [Mesh(g, members, g.ptr((target[0], target[1] + 8 * k))) for k in range(count)] if target else []

    def save(self, path):
        self.g.save(path)


def _unit(v):
    v = np.asarray(v, dtype=np.float64)
    return v / (np.linalg.norm(v) or 1.0)


def graded(positions, group):
    """How strongly a "shape" group acts on each vertex, 0..1, from where the vertex lies.

    Along `axis` the strength ramps from 0 at `from` to 1 at `to` (raised to `power`); each entry
    of `within` ({"axis", "center", "width"}) fades it out linearly with the distance from `center`
    along its own axis, reaching 0 at `width`.
    """
    s = positions @ _unit(group.get('axis', [0, 0, 1]))
    lo, hi = float(group.get('from', s.min())), float(group.get('to', s.max()))
    t = np.clip((s - lo) / ((hi - lo) or 1e-9), 0.0, 1.0) ** float(group.get('power', 1.0))
    for gate in group.get('within', []):
        d = np.abs(positions @ _unit(gate['axis']) - float(gate.get('center', 0.0)))
        t = t * np.clip(1.0 - d / float(gate['width']), 0.0, 1.0)
    return t


def deform(positions, weights, indices, names, bones, quills=None, bulk=None, shape=None):
    """The reshape edit on plain arrays: returns (new positions, report lines).

    positions N x 3 (bind pose), weights / indices N x 4 as Mesh.weights() gives them, names the
    mesh's bone names, bones {name: (rotation rows, position, parent index)} from
    GrannyPreview.load_bones (parents index into the same order).
    shape: graded edits (see reshape), applied after bulk and before quills.
    """
    report = []
    moved = positions.copy()
    groups = [] if not bulk else (bulk if isinstance(bulk, list) else [bulk])
    order = list(bones)
    applied = []
    for group in groups:
        selected = np.array([any(n.startswith(p) for p in group['bones']) for n in names])
        share = (weights * selected[indices]).sum(1)
        pivot = np.array(group.get('pivot', [0.0, 0.0, 0.0]), dtype=np.float64)
        factor = np.array([group.get('x', 1.0), group.get('y', 1.0), group.get('z', 1.0)], dtype=np.float64)
        moved += ((positions - pivot) * factor + pivot - positions) * share[:, None]
        applied.append((group['bones'], pivot, factor))
        report.append(f"bulk {group.get('name', '/'.join(group['bones'][:2]))} on {int((share > 0.01).sum())} vertices")
    for group in ([] if not shape else (shape if isinstance(shape, list) else [shape])):
        selected = np.array([any(n.startswith(p) for p in group['bones']) for n in names])
        strength = (weights * selected[indices]).sum(1) * graded(positions, group)
        if 'offset' in group:
            moved += np.asarray(group['offset'], dtype=np.float64)[None, :] * strength[:, None]
        if any(k in group for k in ('x', 'y', 'z')):
            pivot = np.array(group.get('pivot', [0.0, 0.0, 0.0]), dtype=np.float64)
            factor = np.array([group.get('x', 1.0), group.get('y', 1.0), group.get('z', 1.0)], dtype=np.float64)
            moved += ((positions - pivot) * factor + pivot - positions) * strength[:, None]
        report.append(f"shape {group.get('name', '/'.join(group['bones'][:2]))} on {int((strength > 0.01).sum())} vertices")
    quill_sets = [] if not quills else (quills if isinstance(quills, list) else [quills])
    if quill_sets:
        dominant = indices[np.arange(len(indices)), weights.argmax(1)]
    for spec in quill_sets:
        prefix = spec.get('prefix', 'spike_')
        count = 0
        for k, name in enumerate(names):
            if not name.startswith(prefix) or name not in bones:
                continue
            digits = ''.join(ch for ch in name[len(prefix):] if ch.isdigit())
            number = int(digits) if digits else 0
            if not spec.get('first', 0) <= number <= spec.get('last', 10 ** 9):
                continue
            mine = dominant == k
            if not mine.any():
                continue
            joint = np.array(bones[name][1], dtype=np.float64)
            # The bulk edits moved the quill's root with the body part it grows from; carry the joint along.
            parent = bones[name][2]
            parent_name = order[parent] if isinstance(parent, (int, np.integer)) and 0 <= parent < len(order) else ''
            carried = joint.copy()
            for prefixes, pivot, factor in applied:
                if any(parent_name.startswith(p) for p in prefixes) or (len(applied) == 1 and not parent_name):
                    carried += (joint - pivot) * factor + pivot - joint
            rel = moved[mine] - carried
            far = rel[np.linalg.norm(rel, axis=1).argmax()]
            axis = far / (np.linalg.norm(far) or 1.0)
            along = rel @ axis
            across = rel - along[:, None] * axis
            moved[mine] = carried + (along * spec.get('length', 1.0))[:, None] * axis + across * spec.get('thickness', 1.0)
            count += 1
        report.append(f'{count} quills reshaped')
    return moved, report


def reshape(model, bones, quills=None, bulk=None, shape=None):
    """Applies the quill, bulk and shape edits to every mesh of a model.

    bones: {name: (3x3 rotation rows, position, parent)} from GrannyPreview.load_bones.
    quills: {"prefix": "spike_", "length": 1.6, "thickness": 1.5, "first": 20, "last": 62}, or a list of them.
        Vertices that follow a quill joint are stretched along the quill (the
        direction from the joint to the far end of its own vertices) and
        thickened around it. `first`/`last` limit it to a range of joint numbers.
    bulk: {"bones": ["spine_", "pelvis", "neck"], "x": 1.3, "y": 1.2, "z": 1.0, "pivot": [0, 2.3, 0.5]}, or a list
        of them (one per body part). Vertices that follow the named bones are scaled about the pivot, in
        proportion to how much they follow them, so the edit fades out towards the neighbouring parts
        without a seam.
    shape: a graded edit, or a list of them: {"bones": ["head"], "axis": [0, 0, 1], "from": 0.55, "to": 0.78,
        "power": 2, "within": [{"axis": [1, 0, 0], "center": 0, "width": 0.2}], "offset": [0, -0.07, 0]}
        and/or "x"/"y"/"z" + "pivot" like bulk. Vertices that follow the bones are moved by `offset`
        (or scaled about the pivot) in proportion to how far they lie along `axis` between `from`
        and `to` (see graded): a beak tip bent into a hook, a tail made longer in the middle
        than at the sides, a throat ruff pushed out.
    Returns a short report.
    """
    report = []
    for mesh in model.meshes:
        weights, indices = mesh.weights()
        if weights is None:
            report.append(f'{mesh.name}: no skin weights, left alone')
            continue
        moved, lines = deform(mesh.positions(), weights, indices, mesh.bones, bones, quills, bulk, shape)
        report += [f'{mesh.name}: {line}' for line in lines]
        mesh.set_positions(moved)
    return report


# --- removing geometry (rebuilds the file through Granny.py) ---------------------------------

def _selected_bones(bone_names, spec):
    """Names picked by a remove rule's "bones": a name, a name start ("spike_"), a list of either,
    or {"prefix", "first", "last"} (numbered joints)."""
    if isinstance(spec, dict):
        prefix, first, last = spec['prefix'], spec.get('first', 0), spec.get('last', 10 ** 9)
        picked = set()
        for n in bone_names:
            if n.startswith(prefix):
                digits = ''.join(ch for ch in n[len(prefix):] if ch.isdigit())
                if first <= (int(digits) if digits else 0) <= last:
                    picked.add(n)
        return picked
    wanted = [spec] if isinstance(spec, str) else list(spec)
    return {n for n in bone_names if any(n == w or n.startswith(w) for w in wanted)}


def _below(bone_names, parents, picked):
    """The picked bones and everything under them."""
    out = set(picked)
    changed = True
    while changed:
        changed = False
        for n, p in zip(bone_names, parents):
            if p >= 0 and n not in out and bone_names[p] in out:
                out.add(n)
                changed = True
    return out


_TOPOLOGY_EXTRAS = ('VertexToVertexMap', 'VertexToTriangleMap', 'SideToNeighborMap', 'PolygonIndexStarts',
                    'PolygonIndices', 'BonesForTriangle', 'TriangleToBoneIndices', 'TriAnnotationSets')


def remove_geometry(data, rules):
    """Removes triangles from the meshes of a model; returns (new file bytes, report lines).

    rules: a list; a triangle goes when any rule takes it. A rule selects vertices and takes a
    triangle when all three of its vertices are selected ("any": true: when one is):
        {"bones": "spike_", "below": true, "weight": 0.5}
            vertices that follow those bones (with "below": and every bone under them) by at least
            `weight` in all (default 0.5). "bones" is a name, a name start, a list of them, or
            {"prefix", "first", "last"}. A rigid mesh (no skin weights) follows its one bone.
        {"box": {"min": [x, y, z], "max": [x, y, z]}}
            vertices inside a model-space box (bind pose); "outside": true selects the rest.
        "mesh": "name" limits a rule to the meshes of that name.
    Vertices no triangle uses any more are dropped and the indices renumbered; material groups,
    the mesh box (bbMin/bbMax; VertexScale stays) and each bone binding's box (OBBMin/OBBMax, in
    that bone's space) are recomputed from what is left. The bone bindings themselves stay, so
    the vertices' bone indices keep meaning the same bones. A mesh may not lose every triangle.
    """
    import Granny
    source = Granny.read(data)
    tree = source.root()
    skeleton = tree['Models'][0]['Skeleton']['Bones'] if tree.get('Models') else []
    bone_names = [b['Name'] for b in skeleton]
    parents = [b['ParentIndex'] for b in skeleton]
    inverse = {b['Name']: np.array(b['InverseWorldTransform'], dtype=np.float64).reshape(4, 4) for b in skeleton}
    report = []
    for mesh in tree['Meshes']:
        name = mesh['Name']
        vertices = mesh['PrimaryVertexData']['Vertices']
        items = vertices['$items']
        topology = mesh['PrimaryTopology']
        applies = [r for r in rules if not r.get('mesh') or r['mesh'] == name]
        if not applies:
            continue
        if topology.get('Indices'):
            raise ValueError(f'{name}: 32-bit indices are not handled')
        for extra in _TOPOLOGY_EXTRAS:
            if topology.get(extra):
                raise ValueError(f'{name}: the topology has {extra}, which removing triangles would leave stale')
        if mesh.get('MorphTargets'):
            raise ValueError(f'{name}: morph targets are not handled')
        triangles = np.array(topology['Indices16'], dtype=np.int64).reshape(-1, 3)
        extended = mesh['ExtendedData']['$value']
        scale = float(extended.get('VertexScale') or 1.0)
        positions = np.array([it['Position'][:3] for it in items], dtype=np.float64) / 32767.0 * scale
        bindings = [b['BoneName'] for b in mesh['BoneBindings']]
        skinned = 'BoneWeights' in items[0]
        if skinned:
            weights = np.array([it['BoneWeights'] for it in items], dtype=np.float64) / 255.0
            slots = np.array([it['BoneIndices'] for it in items], dtype=np.int64)
        gone = np.zeros(len(triangles), dtype=bool)
        for rule in applies:
            if 'bones' in rule:
                picked = _selected_bones(bone_names or bindings, rule['bones'])
                if rule.get('below'):
                    picked = _below(bone_names, parents, picked)
                hits = np.array([b in picked for b in bindings], dtype=bool)
                if skinned:
                    follow = (weights * hits[slots]).sum(1)
                else:
                    follow = np.full(len(items), 1.0 if hits[:1].any() else 0.0)
                chosen = follow >= float(rule.get('weight', 0.5))
            elif 'box' in rule:
                low, high = np.array(rule['box']['min'], dtype=float), np.array(rule['box']['max'], dtype=float)
                chosen = ((positions >= low) & (positions <= high)).all(1)
                if rule.get('outside'):
                    chosen = ~chosen
            else:
                raise ValueError('a remove rule needs "bones" or "box"')
            per_triangle = chosen[triangles]
            gone |= per_triangle.any(1) if rule.get('any') else per_triangle.all(1)
        if not gone.any():
            report.append(f'{name}: nothing removed')
            continue
        if gone.all():
            raise ValueError(f'{name}: the rules would remove every triangle; drop the model instead')
        # Material groups keep their order; each keeps the triangles left in its range.
        kept_rows, groups = [], []
        for group in topology['Groups']:
            first, count = group['TriFirst'], group['TriCount']
            rows = [t for t in range(first, first + count) if not gone[t]]
            if rows:
                new = dict(group)
                new.update({'TriFirst': len(kept_rows), 'TriCount': len(rows)})
                groups.append(new)
                kept_rows += rows
        kept = triangles[kept_rows]
        used = np.unique(kept)
        remap = -np.ones(len(items), dtype=np.int64)
        remap[used] = np.arange(len(used))
        vertices['$items'] = [items[i] for i in used]
        topology['Indices16'] = [int(v) for v in remap[kept].reshape(-1)]
        topology['Groups'] = groups
        left = positions[used]
        extended['bbMin'], extended['bbMax'] = [float(v) for v in left.min(0)], [float(v) for v in left.max(0)]
        homogeneous = np.concatenate([left, np.ones((len(left), 1))], axis=1)
        for k, binding in enumerate(mesh['BoneBindings']):
            if skinned:
                mine = ((slots[used] == k) & (weights[used] > 0)).any(1)
            else:
                mine = np.full(len(used), k == 0)
            if binding['BoneName'] in inverse and mine.any():
                local = homogeneous[mine] @ inverse[binding['BoneName']]
                binding['OBBMin'] = [float(v) for v in local[:, :3].min(0)]
                binding['OBBMax'] = [float(v) for v in local[:, :3].max(0)]
            if binding.get('TriangleIndices'):
                binding['TriangleIndices'] = []
        report.append(f'{name}: {int(gone.sum())} of {len(triangles)} triangles and '
                      f'{len(items) - len(used)} of {len(items)} vertices removed')
    out = Granny.Writer(source.tag, tuple(source.extra_tags)).build(source.describe(source.root_type), tree)
    return out, report


def main(argv):
    """python GrannyMesh.py remove <in.model> <out.model> <rules.json or a JSON list>"""
    import json
    import os
    if len(argv) != 4 or argv[0] != 'remove':
        print(main.__doc__)
        return 2
    _, source, target, rules = argv
    rules = json.load(open(rules, encoding='utf-8')) if os.path.isfile(rules) else json.loads(rules)
    with open(source, 'rb') as f:
        data, report = remove_geometry(f.read(), rules if isinstance(rules, list) else [rules])
    if os.path.dirname(target):
        os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, 'wb') as f:
        f.write(data)
    print('\n'.join(report))
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:]))
