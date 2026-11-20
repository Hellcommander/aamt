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

`remove_geometry` and `add_geometry` are the exceptions to "counts untouched":
the first takes triangles out (by bone or by box) and can cap the holes, the
second puts parts of other models (or of the same one) into a mesh, bound to
the body's bones. Both rebuild the file through Granny.py.

    python GrannyMesh.py remove in.model out.model '[{"bones": "spike_", "below": true, "cap": true}]'
    python GrannyMesh.py add in.model out.model '[{"from": "tusk_lod0.model", "bone": "jaw_bind_jnt", "space": "bone", "twin": "x"}]'
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
        places = [g.ptr((target[0], target[1] + 8 * k)) for k in range(count)] if target else []
        # A model file holds a second model entry for the next LOD level (file _lod0: levels 0
        # and 1), whose mesh is reached only through that entry. It is edited like the first.
        if 'Models' in fields:
            offset, member = fields['Models']
            at = (g.root_obj[0], g.root_obj[1] + offset)
            table = g.ptr((at[0], at[1] + 4))
            model_fields = _offsets(g, g.read_type(member['ref']))
            for k in range(g.i32(at) if table else 0):
                model_at = g.ptr((table[0], table[1] + 8 * k))
                if model_at is None or 'MeshBindings' not in model_fields:
                    continue
                bind_off, bind_member = model_fields['MeshBindings']
                first = g.ptr((model_at[0], model_at[1] + bind_off + 4))
                size = g.struct_size(g.read_type(bind_member['ref']))
                for j in range(g.i32((model_at[0], model_at[1] + bind_off)) if first else 0):
                    mesh_at = g.ptr((first[0], first[1] + j * size))
                    if mesh_at is not None and mesh_at not in places:
                        places.append(mesh_at)
        # meshes: the root list (what the file is about); next_level: the next LOD level's copies.
        self.meshes = [Mesh(g, members, at) for at in places[:count if target else 0]]
        self.next_level = [Mesh(g, members, at) for at in places[count if target else 0:]]

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
    for mesh in model.meshes + model.next_level:
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


def _cut_loops(welded, triangles, gone, capped):
    """The holes the `capped` removed triangles leave in the kept ones.

    welded: one id per vertex, equal for vertices at the same place (a UV seam doubles vertices, and
    a hole's rim crosses seams). Returns (loops, open edge count); a loop is a list of
    (triangle, a, b): the kept triangle on the rim and its edge a -> b, in order round the hole.
    Edges that were already open before the removal are not part of any loop.
    """
    def keys(rows):
        w = welded[triangles[rows]]
        e = np.concatenate([w[:, [0, 1]], w[:, [1, 2]], w[:, [2, 0]]])
        e.sort(axis=1)
        return e[:, 0] * (int(welded.max()) + 1) + e[:, 1]
    kept_rows = np.flatnonzero(~gone)
    kept_keys = keys(kept_rows)
    values, counts = np.unique(kept_keys, return_counts=True)
    single = values[counts == 1]
    rim = np.isin(kept_keys, np.intersect1d(single, np.unique(keys(np.flatnonzero(capped)))))
    starts = {}
    for n in np.flatnonzero(rim):
        t, corner = kept_rows[n % len(kept_rows)], n // len(kept_rows)
        a, b = int(triangles[t, corner]), int(triangles[t, (corner + 1) % 3])
        starts.setdefault(int(welded[a]), []).append((int(t), a, b))
    loops, stray = [], 0
    while starts:
        first = next(iter(starts))
        loop = []
        at = first
        while at in starts:
            edge = starts[at].pop()
            if not starts[at]:
                del starts[at]
            loop.append(edge)
            at = int(welded[edge[2]])
            if at == first:
                break
        if at == first and len(loop) >= 3:
            loops.append(loop)
        else:
            stray += len(loop)
    return loops, stray


def _newell(points):
    """The normal of a closed loop of points (not unit length; zero for a degenerate loop)."""
    after = np.roll(points, -1, axis=0)
    return np.stack([((points[:, 1] - after[:, 1]) * (points[:, 2] + after[:, 2])).sum(),
                     ((points[:, 2] - after[:, 2]) * (points[:, 0] + after[:, 0])).sum(),
                     ((points[:, 0] - after[:, 0]) * (points[:, 1] + after[:, 1])).sum()])


def all_meshes(tree):
    """Every mesh of a decoded model file: the root list, then the meshes only a model entry
    reaches. A file holds two model entries, its own LOD level and the next one (_lod0: levels 0
    and 1; _lod3 and _lod4 hold one), each with a mesh and a skeleton of its own."""
    out = list(tree.get('Meshes') or [])
    for model in tree.get('Models') or []:
        for binding in model.get('MeshBindings') or []:
            if binding.get('Mesh') is not None and not any(binding['Mesh'] is m for m in out):
                out.append(binding['Mesh'])
    return out


def bone_lists(tree):
    """Every distinct bone list of a decoded model file (see all_meshes)."""
    out = []
    for holder in list(tree.get('Skeletons') or []) + [m.get('Skeleton') for m in tree.get('Models') or []]:
        if holder is not None and not any(holder['Bones'] is b for b in out):
            out.append(holder['Bones'])
    return out


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
        "cap": true closes the holes the rule's removal opens: each hole gets a fan of triangles
            from its rim to a new vertex in the middle (a three-edged hole just one triangle). The
            new vertex copies the skin weights of the rim vertex nearest to it, takes the mean of
            the rim's UVs and faces out of the hole. Edges that were open in the stock mesh stay
            open, and so does a rim that does not close into a ring (reported).
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
    for mesh in all_meshes(tree):
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
        capped = np.zeros(len(triangles), dtype=bool)
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
            taken = per_triangle.any(1) if rule.get('any') else per_triangle.all(1)
            gone |= taken
            if rule.get('cap'):
                capped |= taken
        if not gone.any():
            report.append(f'{name}: nothing removed')
            continue
        if gone.all():
            raise ValueError(f'{name}: the rules would remove every triangle; drop the model instead')
        original = list(items)
        # Caps: new triangles (and a middle vertex per hole) for the group of the rim they close.
        patches = {}            # first triangle of a group's range -> [[a, b, c], ...]
        cap_note = ''
        if capped.any():
            import copy
            quantised = np.array([it['Position'][:3] for it in items], dtype=np.int64)
            welded = np.unique(quantised, axis=0, return_inverse=True)[1].reshape(-1)
            loops, stray = _cut_loops(welded, triangles, gone, capped)
            # Which way the stock triangles wind against their normals, so the new vertex faces out.
            sample = triangles[~gone][:2000]
            flat = np.cross(positions[sample[:, 1]] - positions[sample[:, 0]], positions[sample[:, 2]] - positions[sample[:, 0]])
            stored = np.array([items[i]['Normal'][:3] for i in sample[:, 0]], dtype=np.float64)
            winding = 1.0 if np.median((flat * stored).sum(1)) >= 0 else -1.0
            starts = [g['TriFirst'] for g in topology['Groups']]
            added = 0
            for loop in loops:
                owner = max(s for s in starts if s <= loop[0][0])
                rim = [a for _, a, _ in loop]
                if len(loop) == 3:
                    patches.setdefault(owner, []).append([rim[0], rim[2], rim[1]])
                    added += 1
                    continue
                middle = positions[rim].mean(0)
                nearest = rim[int(np.linalg.norm(positions[rim] - middle, axis=1).argmin())]
                vertex = copy.deepcopy(items[nearest])
                spot = np.clip(np.round(middle / scale * 32767.0), -32767, 32767)
                vertex['Position'][:3] = [int(v) for v in spot]
                facing = _newell(positions[rim[::-1]]) * winding
                if np.linalg.norm(facing) > 0:
                    vertex['Normal'][:3] = [int(v) for v in np.round(facing / np.linalg.norm(facing) * 127.0)]
                for field in vertex:
                    if field.startswith('TextureCoordinates'):
                        vertex[field] = [float(v) for v in np.mean([items[i][field] for i in rim], axis=0)]
                index = len(items)
                items.append(vertex)
                positions = np.concatenate([positions, [spot / 32767.0 * scale]])
                if skinned:
                    weights = np.concatenate([weights, weights[nearest:nearest + 1]])
                    slots = np.concatenate([slots, slots[nearest:nearest + 1]])
                patches.setdefault(owner, []).extend([b, a, index] for _, a, b in loop)
                added += len(loop)
            cap_note = f'; {len(loops)} holes capped with {added} triangles'
            if stray:
                cap_note += f', {stray} cut edges left open (their rim is not a ring)'
        # Material groups keep their order; each keeps the triangles left in its range.
        parts, groups, total = [], [], 0
        for group in topology['Groups']:
            first, count = group['TriFirst'], group['TriCount']
            rows = triangles[first:first + count][~gone[first:first + count]]
            if patches.get(first):
                rows = np.concatenate([rows, np.array(patches[first], dtype=np.int64)])
            if len(rows):
                new = dict(group)
                new.update({'TriFirst': total, 'TriCount': len(rows)})
                groups.append(new)
                parts.append(rows)
                total += len(rows)
        kept = np.concatenate(parts)
        used = np.unique(kept)
        if len(used) > 65535:
            raise ValueError(f'{name}: more than 65535 vertices after capping')
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
        report.append(f'{name}: {int(gone.sum())} of {len(triangles)} triangles removed, '
                      f'{len(original)} -> {len(used)} vertices{cap_note}')
    out = Granny.Writer(source.tag, tuple(source.extra_tags)).build(source.describe(source.root_type), tree)
    return out, report


# --- adding geometry (rebuilds the file through Granny.py) -----------------------------------

class _Geometry:
    """One mesh of a decoded model as arrays (bind pose, model space)."""

    def __init__(self, tree, mesh):
        self.mesh = mesh
        self.name = mesh['Name']
        skeleton = tree['Models'][0]['Skeleton']['Bones'] if tree.get('Models') else []
        self.bone_names = [b['Name'] for b in skeleton]
        self.parents = [b['ParentIndex'] for b in skeleton]
        self.inverse = {b['Name']: np.array(b['InverseWorldTransform'], dtype=np.float64).reshape(4, 4) for b in skeleton}
        self.items = mesh['PrimaryVertexData']['Vertices']['$items']
        self.topology = mesh['PrimaryTopology']
        if self.topology.get('Indices'):
            raise ValueError(f'{self.name}: 32-bit indices are not handled')
        for extra in _TOPOLOGY_EXTRAS:
            if self.topology.get(extra):
                raise ValueError(f'{self.name}: the topology has {extra}, which a changed triangle list would leave stale')
        if mesh.get('MorphTargets'):
            raise ValueError(f'{self.name}: morph targets are not handled')
        self.triangles = np.array(self.topology['Indices16'], dtype=np.int64).reshape(-1, 3)
        self.extended = mesh['ExtendedData']['$value']
        self.scale = float(self.extended.get('VertexScale') or 1.0)
        self.positions = np.array([it['Position'][:3] for it in self.items], dtype=np.float64) / 32767.0 * self.scale
        self.bindings = [b['BoneName'] for b in mesh['BoneBindings']]
        self.skinned = bool(self.items) and 'BoneWeights' in self.items[0]
        if self.skinned:
            self.weights = np.array([it['BoneWeights'] for it in self.items], dtype=np.float64) / 255.0
            self.slots = np.array([it['BoneIndices'] for it in self.items], dtype=np.int64)

    def chosen(self, rule):
        """The vertices a "bones" or "box" rule selects (the rules remove_geometry takes)."""
        if 'bones' in rule:
            picked = _selected_bones(self.bone_names or self.bindings, rule['bones'])
            if rule.get('below'):
                picked = _below(self.bone_names, self.parents, picked)
            hits = np.array([b in picked for b in self.bindings], dtype=bool)
            if self.skinned:
                follow = (self.weights * hits[self.slots]).sum(1)
            else:
                follow = np.full(len(self.items), 1.0 if hits[:1].any() else 0.0)
            return follow >= float(rule.get('weight', 0.5))
        if 'box' in rule:
            low, high = np.array(rule['box']['min'], dtype=float), np.array(rule['box']['max'], dtype=float)
            inside = ((self.positions >= low) & (self.positions <= high)).all(1)
            return ~inside if rule.get('outside') else inside
        raise ValueError('a "pick" needs "bones" or "box"')


def _euler(degrees):
    """Rotation about X, then Y, then Z (degrees), for column vectors: the attachment convention."""
    x, y, z = np.radians(np.asarray(degrees, dtype=np.float64))
    cx, sx, cy, sy, cz, sz = np.cos(x), np.sin(x), np.cos(y), np.sin(y), np.cos(z), np.sin(z)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rz @ ry @ rx


def _unit_rows(rows):
    length = np.linalg.norm(rows, axis=1, keepdims=True)
    length[length == 0] = 1.0
    return rows / length


def _refresh_boxes(geometry):
    """bbMin/bbMax and every bone binding's OBB from the mesh's items as they are now."""
    mesh, items = geometry.mesh, geometry.items
    stored = np.array([it['Position'][:3] for it in items], dtype=np.float64) / 32767.0 * float(geometry.extended.get('VertexScale') or 1.0)
    geometry.extended['bbMin'], geometry.extended['bbMax'] = [float(v) for v in stored.min(0)], [float(v) for v in stored.max(0)]
    homogeneous = np.concatenate([stored, np.ones((len(stored), 1))], axis=1)
    skinned = 'BoneWeights' in items[0]
    if skinned:
        weights = np.array([it['BoneWeights'] for it in items], dtype=np.int64)
        slots = np.array([it['BoneIndices'] for it in items], dtype=np.int64)
    for k, binding in enumerate(mesh['BoneBindings']):
        mine = ((slots == k) & (weights > 0)).any(1) if skinned else np.full(len(items), k == 0)
        if binding['BoneName'] in geometry.inverse and mine.any():
            local = homogeneous[mine] @ geometry.inverse[binding['BoneName']]
            binding['OBBMin'] = [float(v) for v in local[:, :3].min(0)]
            binding['OBBMax'] = [float(v) for v in local[:, :3].max(0)]
        if binding.get('TriangleIndices'):
            binding['TriangleIndices'] = []


def _binding_slot(geometry, bone):
    """The number vertices use for a bone in this mesh; binds the bone if the mesh did not use it yet."""
    import copy
    import difflib
    bindings = geometry.mesh['BoneBindings']
    for k, binding in enumerate(bindings):
        if binding['BoneName'] == bone:
            return k
    if bone not in geometry.inverse:
        close = difflib.get_close_matches(bone, geometry.bone_names, 4, 0.4)
        raise ValueError(f'{geometry.name}: the skeleton has no bone "{bone}"' + (f' (close: {", ".join(close)})' if close else ''))
    if len(bindings) >= 256:
        raise ValueError(f'{geometry.name}: already bound to 256 bones, "{bone}" does not fit a vertex\'s one-byte bone number')
    new = copy.deepcopy(bindings[0])
    new.update({'BoneName': bone, 'OBBMin': [0.0, 0.0, 0.0], 'OBBMax': [0.0, 0.0, 0.0], 'TriangleIndices': []})
    bindings.append(new)
    return len(bindings) - 1


def _graft(target, part, rule, label):
    """Puts one source mesh's picked triangles into the target mesh; returns a report line or None."""
    import copy
    chosen = part.chosen(rule['pick']) if rule.get('pick') else np.ones(len(part.items), dtype=bool)
    per_triangle = chosen[part.triangles]
    taken = per_triangle.any(1) if (rule.get('pick') or {}).get('any') else per_triangle.all(1)
    if not taken.any():
        return None
    triangles = part.triangles[taken]
    used = np.unique(triangles)
    remap = -np.ones(len(part.items), dtype=np.int64)
    remap[used] = np.arange(len(used))
    triangles = remap[triangles]
    points = part.positions[used]
    # Where the part's own origin is: a point, one of its bones (bind position), or its middle.
    origin = rule.get('origin', [0.0, 0.0, 0.0])
    if origin == 'center':
        origin = (points.min(0) + points.max(0)) / 2
    elif isinstance(origin, str):
        if origin not in part.inverse:
            raise ValueError(f'{label}: "origin" names the bone "{origin}", which the source skeleton does not have')
        origin = np.linalg.inv(part.inverse[origin])[3, :3]
    # points -> points @ linear + shift (row vectors).
    scale = rule.get('scale', 1.0)
    scale = np.array([scale] * 3 if np.isscalar(scale) else scale, dtype=np.float64)
    linear = np.diag(scale) @ _euler(rule.get('rotate', [0, 0, 0])).T
    shift = np.array(rule.get('translate', [0.0, 0.0, 0.0]), dtype=np.float64)
    # Mirroring comes last: the placed part is reflected to the other side of the frame.
    side = np.ones(3)
    for axis in rule.get('mirror', ''):
        side['xyz'.index(axis)] = -1.0
    linear, shift = linear * side, shift * side
    bone = rule.get('bone')
    slot = _binding_slot(target, bone) if bone and target.skinned else None
    if bone and bone not in target.inverse:
        raise ValueError(f'{target.name}: the skeleton has no bone "{bone}"')
    if rule.get('space', 'model') == 'bone':
        if not bone:
            raise ValueError(f'{label}: "space": "bone" needs "bone"')
        world = np.linalg.inv(target.inverse[bone])
        linear, shift = linear @ world[:3, :3], shift @ world[:3, :3] + world[3, :3]
    moved = (points - np.asarray(origin, dtype=np.float64)) @ linear + shift
    flipped = np.linalg.det(linear) < 0
    if flipped:
        triangles = triangles[:, ::-1]
    source_items = [part.items[i] for i in used]
    normals = _unit_rows(np.array([it.get('Normal', [0, 127, 0, 0])[:3] for it in source_items], dtype=np.float64) @ np.linalg.inv(linear).T)
    tangent_raw = np.array([it.get('Tangent', [127, 0, 0, 127]) for it in source_items], dtype=np.float64)
    tangents = _unit_rows(tangent_raw[:, :3] @ linear)
    handed = np.where(tangent_raw[:, 3] < 0, -127, 127) * (-1 if flipped else 1)
    uvs = np.array([it.get('TextureCoordinates0', [0.0, 0.0]) for it in source_items], dtype=np.float64)
    if rule.get('uv'):
        u0, v0, u1, v1 = rule['uv']
        low, span = uvs.min(0), np.ptp(uvs, axis=0)
        span[span == 0] = 1.0
        uvs = (uvs - low) / span * [u1 - u0, v1 - v0] + [u0, v0]
    # Skin: rigid on one bone, or the part's own weights with its bones found by name in the target.
    if target.skinned:
        if slot is not None:
            skin_weights = [[255, 0, 0, 0]] * len(used)
            skin_slots = [[slot] * 4] * len(used)
            bound = f'rigid on {bone}'
        elif part.skinned:
            table = {}
            skin_weights, skin_slots = [], []
            for it in source_items:
                mapped = []
                for weight, number in zip(it['BoneWeights'], it['BoneIndices']):
                    if weight:
                        if number not in table:
                            table[number] = _binding_slot(target, part.bindings[number])
                        mapped.append(table[number])
                    else:
                        mapped.append(None)
                first = next(m for m in mapped if m is not None)
                skin_weights.append(list(it['BoneWeights']))
                skin_slots.append([first if m is None else m for m in mapped])
            bound = f'skinned to {len(table)} bones by name'
        else:
            raise ValueError(f'{label}: the source has no skin weights; name the bone that carries it with "bone"')
    else:
        bound = 'unskinned'
    # The stored range grows with the mesh; the old vertices are then stored again on the new scale.
    reach = float(np.abs(moved).max())
    old_scale = float(target.extended.get('VertexScale') or 1.0)
    if reach > old_scale:
        if 'VertexScale' not in target.extended:
            raise ValueError(f'{target.name}: no VertexScale to grow; the added part must stay within -1..1')
        for it in target.items:
            it['Position'][:3] = [int(round(v * old_scale / reach)) for v in it['Position'][:3]]
        target.extended['VertexScale'] = reach
        old_scale = reach
    quantised = np.clip(np.round(moved / old_scale * 32767.0), -32767, 32767).astype(int)
    template = target.items[0]
    base = len(target.items)
    if base + len(used) > 65535:
        raise ValueError(f'{target.name}: {base} + {len(used)} vertices is more than the 65535 that 16-bit indices reach')
    for k in range(len(used)):
        vertex = {}
        for field in template:
            if field == 'Position':
                vertex[field] = [int(v) for v in quantised[k]] + list(template[field][3:])
            elif field == 'Normal':
                vertex[field] = [int(v) for v in np.round(normals[k] * 127.0)] + list(template[field][3:])
            elif field == 'Tangent':
                vertex[field] = [int(v) for v in np.round(tangents[k] * 127.0)] + [int(handed[k])]
            elif field.startswith('TextureCoordinates'):
                vertex[field] = [float(v) for v in uvs[k]]
            elif field == 'BoneWeights':
                vertex[field] = list(skin_weights[k])
            elif field == 'BoneIndices':
                vertex[field] = list(skin_slots[k])
            else:
                vertex[field] = copy.deepcopy(template[field])
        target.items.append(vertex)
    # The new triangles go to the end of a material group (the first by default).
    groups = target.topology['Groups']
    number = int(rule.get('group', 0))
    if not 0 <= number < len(groups):
        raise ValueError(f'{target.name}: no material group {number}')
    old = target.triangles
    end = groups[number]['TriFirst'] + groups[number]['TriCount']
    target.triangles = np.concatenate([old[:end], triangles + base, old[end:]])
    groups[number]['TriCount'] += len(triangles)
    for later in groups:
        if later is not groups[number] and later['TriFirst'] >= end:
            later['TriFirst'] += len(triangles)
    target.topology['Indices16'] = [int(v) for v in target.triangles.reshape(-1)]
    return f'{target.name}: {len(triangles)} triangles and {len(used)} vertices added from {label} ({bound})'


def _rename_strings(node, names, seen=None):
    """Replaces strings in a decoded tree (texture paths); returns how many were changed."""
    seen = set() if seen is None else seen
    if id(node) in seen:
        return 0
    seen.add(id(node))
    count = 0
    for key, value in (node.items() if isinstance(node, dict) else enumerate(node)):
        if isinstance(value, str):
            new = names.get(value, names.get(value.lower()))
            if new is not None and key != '$recursive':
                node[key] = new
                count += 1
        elif isinstance(value, (dict, list)):
            count += _rename_strings(value, names, seen)
    return count


def add_geometry(data, rules, load=None, alone=False, textures=None):
    """Adds triangles to the meshes of a model; returns (new file bytes, report lines).

    data: the target model's bytes (the body). rules: a list, each one part put into the body:
        "from": the model the part comes from: a file path, or a name `load(name)` turns into
            bytes (the pipeline reads the game archive). Left out: the target itself, as it was
            before any rule (copy a part of the body to another place).
        "mesh": only that mesh of the source (default: all of them).
        "pick": which of its triangles, as a remove rule selects them ({"bones": ...} or
            {"box": ...}, with "below", "weight", "outside", "any"). Left out: all of them.
        "to": the target mesh by name (default: the first), "group": its material group (0).
        "bone": the target bone that carries the part: every added vertex follows it alone.
            Left out: the part keeps its own skin weights and its bones are found by name in
            the target's skeleton (a part of the same body, or of a model on the same skeleton).
            A bone the mesh did not use yet gets a bone binding.
        "origin": the part's own zero point: [x, y, z], "center" (the middle of its box) or one
            of the source's bones (its bind position). Default [0, 0, 0].
        "scale" (a number or [x, y, z]), "rotate" ([x, y, z] degrees, about X then Y then Z),
        "translate" ([x, y, z]): applied in that order about the origin. "space": "bone"
            places the result in the bind-pose frame of "bone", the way attachments are placed;
            the default "model" is model space.
        "mirror": "x" (or "y", "z", several) reflects the placed part to the other side of that
            frame: the same rule with "mirror": "x" is the left twin of a right tusk.
            "twin": "x" adds the part and its mirror image in one rule.
        "uv": [u0, v0, u1, v1] fits the part's UVs into that rectangle of the body's texture
            (default: the UVs stay as they are, right for a part of the same body).
    The part wears the target's material: every stock model has one material and one group per
    mesh. For a part with textures of its own use `alone`: the result then holds only the added
    parts (the stock triangles go, as do meshes that got nothing), still on the body's skeleton
    with its skin, to be listed as a second model of the same monster. `textures` renames
    texture paths in the result ({old path: new path}; any length).
    Normals and tangents turn with the part; a mirrored part has its winding and tangent
    handedness flipped. Positions are stored on the mesh's 16-bit grid: when a part reaches
    past VertexScale the scale grows and the stock vertices are stored again (moves them by
    less than a grid step). Boxes (bbMin/bbMax, each binding's OBB) are recomputed.
    """
    import os
    import Granny
    source = Granny.read(data)
    tree = source.root()
    report = []
    opened = {}

    def source_tree(name):
        if name not in opened:
            if name is None:
                raw = data
            elif os.path.isfile(name):
                with open(name, 'rb') as f:
                    raw = f.read()
            elif load is not None:
                raw = load(name)
            else:
                raise ValueError(f'"from": {name} is not a file (and there is no archive to read it from)')
            opened[name] = Granny.read(raw).root()
        return opened[name]

    targets = {}
    stock = {}
    every = all_meshes(tree)
    for rule in rules:
        name = rule.get('to') or tree['Meshes'][0]['Name']
        # The part goes into the mesh of that name in every model entry (the file's own LOD
        # level and the next one it carries).
        meshes = [m for m in every if m['Name'] == name]
        if not meshes:
            raise ValueError(f'"to": no mesh named {name} (meshes: {", ".join(m["Name"] for m in every)})')
        other = source_tree(rule.get('from'))
        wanted = [m for m in other['Meshes'] if not rule.get('mesh') or m['Name'] == rule['mesh']]
        if not wanted:
            raise ValueError(f'"mesh": {rule.get("from") or "the model"} has no mesh named {rule.get("mesh")}')
        lines = []
        for mesh in meshes:
            if id(mesh) not in targets:
                targets[id(mesh)] = _Geometry(tree, mesh)
                stock[id(mesh)] = (len(targets[id(mesh)].triangles), [dict(g) for g in mesh['PrimaryTopology']['Groups']])
            target = targets[id(mesh)]
            for one in wanted:
                label = f'{os.path.basename(rule["from"]) if rule.get("from") else "itself"}:{one["Name"]}'
                passes = [rule]
                if rule.get('twin'):
                    passes.append(dict(rule, mirror=rule.get('mirror', '') + rule['twin']))
                for one_pass in passes:
                    line = _graft(target, _Geometry(other, one), one_pass, label)
                    if line:
                        lines.append(line + (' (twin)' if one_pass is not rule else '') + ('' if mesh is meshes[0] else ' (next LOD level)'))
        if not lines:
            raise ValueError(f'a rule added nothing: its "pick" selects no triangle of {rule.get("from") or "the model"}')
        report += lines
    if alone:
        for key, target in targets.items():
            # Stock triangles sit in front of the added ones in every group.
            keep = np.ones(len(target.triangles), dtype=bool)
            shift = 0
            for group, before in zip(target.topology['Groups'], stock[key][1]):
                keep[group['TriFirst']:group['TriFirst'] + before['TriCount']] = False
                group['TriFirst'] -= shift
                group['TriCount'] -= before['TriCount']
                shift += before['TriCount']
            target.topology['Groups'][:] = [g for g in target.topology['Groups'] if g['TriCount']]
            kept = target.triangles[keep]
            used = np.unique(kept)
            remap = -np.ones(len(target.items), dtype=np.int64)
            remap[used] = np.arange(len(used))
            target.items[:] = [target.items[i] for i in used]
            target.triangles = remap[kept]
            target.topology['Indices16'] = [int(v) for v in target.triangles.reshape(-1)]
            report.append(f'{target.name}: stock geometry dropped, {len(kept)} triangles and {len(used)} vertices stay')
        dropped = [m for m in every if id(m) not in targets]
        if dropped:
            gone = {id(m) for m in dropped} | {id(m['PrimaryTopology']) for m in dropped} | {id(m['PrimaryVertexData']) for m in dropped}
            for key in ('Meshes', 'TriTopologies', 'VertexDatas'):
                tree[key][:] = [x for x in tree.get(key) or [] if id(x) not in gone]
            for model in tree.get('Models') or []:
                model['MeshBindings'][:] = [b for b in model['MeshBindings'] if id(b['Mesh']) not in gone]
            report.append(f'meshes dropped: {", ".join(m["Name"] for m in dropped)}')
    for target in targets.values():
        _refresh_boxes(target)
    if textures:
        lowered = dict(textures)
        lowered.update({k.lower(): v for k, v in textures.items()})
        changed = _rename_strings(tree, lowered)
        report.append(f'{changed} texture names changed' if changed else 'textures: none of the given paths is in the model')
    out = Granny.Writer(source.tag, tuple(source.extra_tags)).build(source.describe(source.root_type), tree)
    return out, report


def main(argv):
    """python GrannyMesh.py remove <in.model> <out.model> <rules.json or a JSON list>
    python GrannyMesh.py add <in.model> <out.model> <rules.json or a JSON list> [--game <D2R folder>]
                             [--alone] [--textures <JSON {old: new}>]
    In "add" rules "from" is a file, or with --game a path in the game archive
    (hd/character/enemy/act5barb2/head_ghm_lod0.model)."""
    import json
    import os
    argv = list(argv)
    options = {}
    for flag, takes in (('--game', True), ('--textures', True), ('--alone', False)):
        if flag in argv:
            at = argv.index(flag)
            options[flag] = argv[at + 1] if takes else True
            del argv[at:at + (2 if takes else 1)]
    if len(argv) != 4 or argv[0] not in ('remove', 'add'):
        print(main.__doc__)
        return 2
    command, source, target, rules = argv
    rules = json.load(open(rules, encoding='utf-8')) if os.path.isfile(rules) else json.loads(rules)
    rules = rules if isinstance(rules, list) else [rules]
    with open(source, 'rb') as f:
        if command == 'remove':
            data, report = remove_geometry(f.read(), rules)
        else:
            archive = None
            if options.get('--game'):
                from d2r_casc import D2RArchive
                archive = D2RArchive(options['--game']).__enter__()
            data, report = add_geometry(f.read(), rules, load=archive.read if archive else None,
                                        alone=bool(options.get('--alone')),
                                        textures=json.loads(options['--textures']) if options.get('--textures') else None)
    if os.path.dirname(target):
        os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, 'wb') as f:
        f.write(data)
    print('\n'.join(report))
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:]))
