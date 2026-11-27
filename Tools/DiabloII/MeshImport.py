"""Bring a mesh made outside the game (Blender, a sculpt, an image-to-3D model) into D2R as a
skinned body: a creature that is new from the ground up, not a reshaped donor.

The new mesh takes over a donor's place: its skeleton, bone bindings, material slot and LOD
files. What makes it move is the donor's skin, carried over by position: every new vertex gets
the bone weights of the donor's surface nearest to it. So the mesh has to be modelled around the
donor, in its bind pose (legs where the donor's legs are); `reference` writes the donor out for
that.

    python MeshImport.py reference --game <D2R> --donor hd/character/enemy/pig/torso --out <folder>
        <folder>/donor.obj (bind pose, game axes: +Y up, +Z to the head, one unit = a foot),
        donor.png (its albedo texture) and bones.json (joint positions), to model against.

    python MeshImport.py build <spec.json> --game <D2R> --out <mod folder> [--stills <folder>]
        <out>/hd/character/enemy/<name>/<part>_lod0..N.model, <name>_alb/_nrm/_orm.texture and
        mesh_import_<name>.report.json (the model to list in the index, with its donor).

spec.json:
    "name": "wb_true_boar"
    "mesh": "boar.glb"            .obj, .glb, .gltf, .ply, .stl: anything trimesh reads; it needs UVs
    "donor": "hd/character/enemy/pig/torso"     the model whose skeleton, skin and files it takes
    "albedo": "boar_albedo.png"   colour texture (default: the base colour image inside a .glb)
    "normal" / "orm": pictures for the normal and occlusion-roughness-metal maps; left out, a flat
                      map in the donor texture's average colour is written (no surface detail)
    "axes": {"up": "+y", "forward": "+z"}       which way the file's axes point (Blender's own
                      space is {"up": "+z", "forward": "-y"}; its glTF and OBJ exports are +y / +z)
    "fit": "donor"    scale the mesh to the donor's length, stand it on the ground and centre it
                      (default). "none": the file is already in game space (made on `reference`).
    "scale", "rotate" ([x, y, z] degrees), "translate": applied after the fit
    "skin": {"smooth": 2, "neighbours": 12, "samples": 150000, "ignore": ["tongue_"]}
                      smooth: passes that even the weights out over the mesh's own edges;
                      ignore: donor bones the new body has no part for (their weight goes to
                      the bone above them)
    "lods": [1.0, 0.6, 0.35, 0.2, 0.1]          triangles kept per LOD file (default: the donor's
                      own ratios); lower LODs are made by merging vertices on a grid
    "texture_size": 1024
    "weld": true      merge vertices that are the same point with the same UV and skin (default;
                      undoes an exporter splitting every triangle's corners apart)
    "max_vertices": 65535   a LOD file with more vertices is simplified below that (default 65535,
                      as before). 0 (or a bigger number) keeps such meshes: past 65,536 vertices
                      they are written with 32-bit indices (Granny's Indices array), which the
                      game draws as it does the stock Druid bear (74,589 vertices, 32-bit). No
                      plugin is needed; mind the cost of very dense bodies.

In a ScaledMonster preset a variant takes the same block as `"import"` (name and donor come from
the variant); `"reshape"`, `"add"` and `"remove"` then work on the imported body.

A file with its own rig (a .glb / .gltf whose joints carry the game's bone names: `reference`
writes one, donor.glb) keeps its own weights instead ("skin": {"from": "auto" | "file" |
"donor"}). Joints the game skeleton lacks, parented under one of its bones, are added as new
bones to every model file and to a copy of the donor's .skeleton file ("new_bones": false
refuses them). Stock clips have no track for a new bone: it holds its bind pose on its parent.

    "normal": "from_albedo"   relief guessed from the colour picture ("normal_strength": 2.0);
                              "normal_green": "down" for a DirectX-style map (default "up")
    "orm_metal": true         also write the metal channel (blue), which stock creature maps leave empty
    "simplify": "auto" | "meshlib" | "grid"     how the lower LODs are made

A .glb's own normal, metallic-roughness and occlusion pictures are converted to the game's
layouts when the spec names none.

Without a donor ("donor" left out, or "skeleton": "file"): the body is the file's own through
and through. Its rig becomes the skeleton (every joint, any names), its weights the skin, its
animations the clips (hd/character/enemy/<name>/animation/combined.animations, sampled at
"fps", default 30), and a .skeleton file is written to match. A stock model ("template",
default hd/character/enemy/sandleaper1/torso) only lends the file format, the material slot and
the number of LOD files; none of its bones, skin or shape is kept. It has to be a one-mesh body
in every LOD file (2026-11-19 scan: baboon1, bighead1, quillrat1, larva, sandleaper1, scorpion,
snake, hydra1 and others; not spiritwolf, which has two or three meshes; since 2026-11-20 a
32-bit template such as druidbear works too). Such a file is used as it is
("fit" defaults to "none"). In a preset, a variant with no "donor" does the same and also
writes the definition and a state machine whose states play the file's clips
("modes": {"NU": "idle", "WL": "walk"}; "template": the stock monster that lends the layout).

A file without UVs (a sculpt, a scan, an image-to-3D mesh) is unwrapped ("uv": "unwrap" forces
it; MeshUnwrap.py) and its vertex colours, if any, are baked into the colour texture.

Limits: one mesh and one material per body; without a rig in the file, a mesh that strays far
from the donor's shape (wings on a pig) gets poor weights there; new bones are untested in the
game.

Versions this was written and checked against (2026-11-19):
    Python 3.14.8, numpy 2.5.2, scipy 1.18.1, trimesh 5.2.1 (reads .obj / .ply / .stl / unrigged glTF),
    Pillow 12.3.0 (DXT5 DDS writing, needs 10.3 or newer),
    meshlib 3.2.0.29 (pip; MeshInspector/MeshLib; non-commercial licence; optional: LODs),
    Blender 5.2.3 LTS glTF importer / exporter (the rigged reference round trip),
    game build 3.4.95041 (pig donor files).
    pmp-library 3.0.0 (clone 3.0.0-310-gfc0bfd7a; MIT, C++) through Tools/Shared/pmp_lib.py and
    pmpwrap.dll (Tools/Shared/pmp_wrap, built with MSVC Build Tools 18 and CMake 4.5.0):
    the conformal map behind MeshUnwrap.py. Optional: only a file without UVs needs it.
"""
import argparse
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import Granny  # noqa: E402
import GrannyMesh  # noqa: E402
import HdTexture  # noqa: E402

# The stock model that lends its file format when a body has no donor (any skinned one-mesh body does).
TEMPLATE = 'hd/character/enemy/sandleaper1/torso'

NEUTRAL_MASK = 'data/hd/character/common/common_ktint.texture'

AXES = {'+x': (0, 1), '-x': (0, -1), '+y': (1, 1), '-y': (1, -1), '+z': (2, 1), '-z': (2, -1)}


class Mesh:
    """positions N x 3, normals N x 3, uvs N x 2 (v down, as the game stores them), triangles M x 3."""

    def __init__(self, positions, normals, uvs, triangles):
        self.positions, self.normals, self.uvs, self.triangles = positions, normals, uvs, triangles
        # A rig the file brought (glTF): joint names, per vertex four joint numbers and weights,
        # and {name: (parent name, 4 x 4 bind matrix for row vectors)}. None without one.
        self.joint_names = self.joints = self.weights = None
        self.rig = {}
        self.images = {}            # 'albedo', 'normal', 'orm', 'occlusion' pictures from the file
        self.model = None           # the Gltf.Model behind a rigged file (its clips: model.pose)
        self.frame = np.eye(4)      # file space -> game space, everything load and place did (row vectors)
        self.colours = None         # N x 3 vertex colours, 0..255
        self.needs_uv = False       # the file had no UVs (uvs are zeros until ensure_uvs)

    def take(self, keep, triangles, positions=None, normals=None):
        """A mesh of the vertices `keep` (indices into this one) and new triangles over them."""
        out = Mesh(self.positions[keep] if positions is None else positions,
                   self.normals[keep] if normals is None else normals, self.uvs[keep], triangles)
        out.joint_names, out.rig, out.images = self.joint_names, self.rig, self.images
        out.model, out.frame, out.needs_uv = self.model, self.frame, self.needs_uv
        if self.joints is not None:
            out.joints, out.weights = self.joints[keep], self.weights[keep]
        if self.colours is not None:
            out.colours = self.colours[keep]
        return out

    def copy(self):
        return self.take(np.arange(len(self.positions)), self.triangles.copy())


def _basis(axes):
    """Rows: the game's X, Y, Z axes written in the file's space."""
    axes = axes or {}
    up, forward = AXES[axes.get('up', '+y').lower()], AXES[axes.get('forward', '+z').lower()]
    if up[0] == forward[0]:
        raise ValueError('"axes": up and forward are the same axis')
    y = np.zeros(3)
    y[up[0]] = up[1]
    z = np.zeros(3)
    z[forward[0]] = forward[1]
    return np.stack([np.cross(y, z), y, z])


def load(path, axes=None):
    """A mesh file as a Mesh in game axes (+Y up, +Z to the head); also returns the base colour
    picture found inside it, if any. A .glb / .gltf is read with Gltf.py, which keeps its rig
    (mesh.joint_names, joints, weights, rig) and its material's pictures (mesh.images)."""
    if str(path).lower().endswith(('.glb', '.gltf')):
        import Gltf
        model = Gltf.load_model(path)
        basis = _basis(axes)
        triangles = model.triangles[:, ::-1] if np.linalg.det(basis) < 0 else model.triangles
        mesh = Mesh(model.positions @ basis.T, GrannyMesh._unit_rows(model.normals @ basis.T), model.uvs.copy(), triangles)
        mesh.images = model.images
        mesh.colours, mesh.needs_uv = model.colours, not model.has_uv
        turn = np.eye(4)
        turn[:3, :3] = basis.T
        mesh.frame = turn
        if model.joints is not None:
            mesh.model = model
            mesh.joint_names, mesh.joints, mesh.weights = model.joint_names, model.joints, model.weights
            mesh.rig = {name: (parent, bind @ turn) for name, (parent, bind) in model.rig.items()}
        return mesh, model.images.get('albedo')
    import trimesh
    loaded = trimesh.load(path, process=False)
    image = None
    if isinstance(loaded, trimesh.Scene):
        if not loaded.geometry:
            raise ValueError(f'{path}: no geometry')
        loaded = loaded.to_mesh()
    uv = getattr(loaded.visual, 'uv', None)
    colours = None
    no_uv = uv is None or len(uv) != len(loaded.vertices)
    if no_uv:
        # No UVs (a sculpt, a scan, an image-to-3D mesh): ensure_uvs unwraps it, and vertex
        # colours, when the file has them, are baked into the texture.
        uv = np.zeros((len(loaded.vertices), 2))
        if getattr(loaded.visual, 'kind', None) == 'vertex':
            colours = np.asarray(loaded.visual.vertex_colors, dtype=np.float64)[:, :3]
    material = getattr(loaded.visual, 'material', None)
    for key in ('baseColorTexture', 'image'):
        if material is not None and getattr(material, key, None) is not None:
            image = getattr(material, key)
            break
    positions = np.asarray(loaded.vertices, dtype=np.float64)
    normals = np.asarray(loaded.vertex_normals, dtype=np.float64)
    triangles = np.asarray(loaded.faces, dtype=np.int64)
    uvs = np.asarray(uv, dtype=np.float64).copy()
    uvs[:, 1] = 1.0 - uvs[:, 1]                         # trimesh keeps v up; the game stores v down
    basis = _basis(axes)
    positions, normals = positions @ basis.T, normals @ basis.T
    if np.linalg.det(basis) < 0:
        triangles = triangles[:, ::-1]
    mesh = Mesh(positions, normals, uvs, triangles)
    mesh.colours, mesh.needs_uv = colours, no_uv
    mesh.frame[:3, :3] = basis.T
    return mesh, image


def weld(mesh, tolerance=1e-5):
    """Merges vertices that are the same point with the same UV (and the same skin): exporters
    that write flat shading or per-corner data split every triangle's corners apart (Blender's
    glTF export of a generated mesh: three vertices per triangle), which triples the count and
    shades in facets. Normals of merged vertices are averaged. Returns (mesh, vertices before)."""
    before = len(mesh.positions)
    parts = [np.round(mesh.positions / tolerance), np.round(mesh.uvs / tolerance)]
    if mesh.joints is not None:
        # The same skin may list its bones in another slot order per corner (UniRig's export does:
        # 60,000 corners of 26,506 points stayed apart), so compare the slots sorted by bone.
        joints = np.asarray(mesh.joints, dtype=np.float64)
        weights = np.asarray(mesh.weights, dtype=np.float64)
        joints = np.where(weights > 0, joints, -1.0)
        order = np.argsort(joints, axis=1, kind='stable')
        parts += [np.take_along_axis(joints, order, 1), np.round(np.take_along_axis(weights, order, 1) * 1000.0)]
    _, keep, inverse = np.unique(np.hstack(parts), axis=0, return_index=True, return_inverse=True)
    inverse = inverse.reshape(-1)
    if len(keep) == before:
        return mesh, before
    normals = np.zeros((len(keep), 3))
    np.add.at(normals, inverse, mesh.normals)
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = np.where(lengths > 1e-9, normals / np.maximum(lengths, 1e-9), mesh.normals[keep])
    triangles = inverse[mesh.triangles]
    whole = (triangles[:, 0] != triangles[:, 1]) & (triangles[:, 1] != triangles[:, 2]) & (triangles[:, 0] != triangles[:, 2])
    return mesh.take(keep, triangles[whole], normals=normals), before


def ensure_uvs(mesh, spec):
    """(mesh, notes): the mesh unwrapped when its file had no UVs, or when the spec says
    "uv": "unwrap" (MeshUnwrap.py, pmp-library's conformal map). Vertex colours, if the file had
    them and no colour texture is given, are baked into one ("texture_size")."""
    if not (mesh.needs_uv or spec.get('uv') == 'unwrap'):
        return mesh, []
    import MeshUnwrap
    positions, triangles, uvs, source, notes = MeshUnwrap.unwrap(mesh.positions, mesh.triangles, int(spec.get('min_chart_faces', 24)))
    out = mesh.take(source, triangles, positions)
    out.uvs, out.needs_uv = uvs, False
    if out.colours is not None and not spec.get('albedo') and 'albedo' not in out.images:
        out.images = dict(out.images, albedo=MeshUnwrap.bake_colours(uvs, triangles, out.colours, int(spec.get('texture_size', 1024))))
        notes.append('colour texture baked from the vertex colours')
    return out, notes


def place(mesh, donor_box, spec):
    """Fit to the donor and apply the spec's own scale / rotate / translate. Returns notes."""
    notes = []
    moved = np.eye(4)                                   # everything done here, for the rig's bind matrices
    # A file that brings a rig was made on the rigged reference, in game space: it is not fitted
    # unless the spec asks for it.
    if spec.get('fit', 'none' if mesh.joints is not None else 'donor') == 'donor':
        low, high = mesh.positions.min(0), mesh.positions.max(0)
        factor = (donor_box[1][2] - donor_box[0][2]) / max(high[2] - low[2], 1e-9)
        centre = np.array([(low[0] + high[0]) / 2, low[1], (low[2] + high[2]) / 2])
        target = np.array([0.0, donor_box[0][1], (donor_box[0][2] + donor_box[1][2]) / 2])
        mesh.positions = (mesh.positions - centre) * factor + target
        moved[:3, :3] *= factor
        moved[3, :3] = target - centre * factor
        notes.append(f'fitted to the donor: scale {factor:.4f}')
    scale = spec.get('scale', 1.0)
    scale = np.array([scale] * 3 if np.isscalar(scale) else scale, dtype=np.float64)
    rotation = GrannyMesh._euler(spec.get('rotate', [0, 0, 0]))
    shift = np.array(spec.get('translate', [0, 0, 0]), dtype=np.float64)
    mesh.positions = (mesh.positions * scale) @ rotation.T + shift
    mesh.normals = GrannyMesh._unit_rows((mesh.normals / scale) @ rotation.T)
    own = np.eye(4)
    own[:3, :3] = np.diag(scale) @ rotation.T
    own[3, :3] = shift
    moved = moved @ own
    mesh.rig = {name: (parent, bind @ moved) for name, (parent, bind) in mesh.rig.items()}
    mesh.frame = mesh.frame @ moved
    return notes


def simplify(mesh, target, method='auto'):
    """A copy with about `target` triangles.

    method "meshlib" (the default when the meshlib package is installed): quadric edge collapse
    that only ever keeps existing vertices, so every vertex left has its own UV, normal and skin
    untouched, and leaves open edges alone: a UV seam is an open edge between two sets of
    vertices, so seams neither crack nor smear. The price is that seams and borders stay as
    dense as they were, and a far LOD can end above its target.
    method "grid": vertices that fall in one cell of a grid are merged (the cell size is
    searched for). Crude, needs nothing installed; also used after meshlib when that stopped
    more than half above the target."""
    if target >= len(mesh.triangles):
        return mesh.copy()
    if method in ('auto', 'meshlib'):
        # meshlib 3.2.0.29: DecimateSettings fields and mrmeshnumpy helpers as used below.
        try:
            import meshlib.mrmeshnumpy as mn
            import meshlib.mrmeshpy as mr
        except ImportError:
            if method == 'meshlib':
                raise
        else:
            body = mn.meshFromFacesVerts(mesh.triangles.astype(np.int32), mesh.positions.astype(np.float32))
            settings = mr.DecimateSettings()
            settings.maxDeletedFaces = len(mesh.triangles) - int(target)
            settings.maxError = 1e9
            settings.touchBdVerts = False
            settings.optimizeVertexPos = False
            settings.packMesh = False
            mr.decimateMesh(body, settings)
            alive = mn.getNumpyBitSet(body.topology.getValidFaces())
            faces = mn.getNumpyFaces(body.topology)
            faces = faces[alive[:len(faces)]].astype(np.int64)
            count = len(mesh.positions)
            if len(faces) and faces.max() >= count:
                # meshlib splits a vertex where the surface is not manifold (two sheets meeting
                # in a point) and numbers the copies past the end. Each copy goes back to one of
                # our vertices at that point: the one whose UV sits nearest the triangle's others.
                from scipy.spatial import cKDTree
                points = mn.getNumpyVerts(body).astype(np.float64)
                tree = cKDTree(mesh.positions)
                for row in np.nonzero((faces >= count).any(axis=1))[0]:
                    known = [v for v in faces[row] if v < count]
                    for corner in range(3):
                        v = faces[row, corner]
                        if v < count:
                            continue
                        distance, nearest = tree.query(points[v])
                        same = tree.query_ball_point(points[v], distance + 1e-6)
                        if known and len(same) > 1:
                            centre = mesh.uvs[known].mean(0)
                            nearest = min(same, key=lambda c: float(((mesh.uvs[c] - centre) ** 2).sum()))
                        faces[row, corner] = nearest
                faces = faces[(faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & (faces[:, 0] != faces[:, 2])]
            keep = np.unique(faces)
            remap = -np.ones(len(mesh.positions), dtype=np.int64)
            remap[keep] = np.arange(len(keep))
            out = mesh.take(keep, remap[faces])
            if len(out.triangles) <= 1.5 * target or method == 'meshlib':
                return out
            mesh = out
    low = mesh.positions.min(0)
    span = float((mesh.positions.max(0) - low).max())

    def merged(cell):
        keys = np.floor((mesh.positions - low) / cell).astype(np.int64)
        _, first, group = np.unique(keys, axis=0, return_index=True, return_inverse=True)
        group = group.reshape(-1)
        tris = group[mesh.triangles]
        tris = tris[(tris[:, 0] != tris[:, 1]) & (tris[:, 1] != tris[:, 2]) & (tris[:, 0] != tris[:, 2])]
        return first, group, tris

    small, large = span / 4096, span / 2
    for _ in range(24):
        cell = math.sqrt(small * large)
        if len(merged(cell)[2]) > target:
            small = cell
        else:
            large = cell
    first, group, tris = merged(large)
    tris = tris[np.unique(np.sort(tris, axis=1), axis=0, return_index=True)[1]]
    counts = np.bincount(group, minlength=len(first)).astype(np.float64)[:, None]
    positions = np.zeros((len(first), 3))
    np.add.at(positions, group, mesh.positions)
    normals = np.zeros((len(first), 3))
    np.add.at(normals, group, mesh.normals)
    used = np.unique(tris)
    remap = -np.ones(len(first), dtype=np.int64)
    remap[used] = np.arange(len(used))
    return mesh.take(first[used], remap[tris], (positions / counts)[used], GrannyMesh._unit_rows(normals)[used])


def tangents(mesh):
    """N x 4: the direction u grows in along the surface, and +1 / -1 for which way v grows
    (cross(normal, tangent) . dP/dv), the way the game's own bodies store it."""
    p, uv, tri = mesh.positions, mesh.uvs, mesh.triangles
    e1, e2 = p[tri[:, 1]] - p[tri[:, 0]], p[tri[:, 2]] - p[tri[:, 0]]
    d1, d2 = uv[tri[:, 1]] - uv[tri[:, 0]], uv[tri[:, 2]] - uv[tri[:, 0]]
    det = d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]
    det[np.abs(det) < 1e-12] = 1e-12
    along_u = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) / det[:, None]
    along_v = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) / det[:, None]
    tu, tv = np.zeros_like(p), np.zeros_like(p)
    for k in range(3):
        np.add.at(tu, tri[:, k], along_u)
        np.add.at(tv, tri[:, k], along_v)
    n = mesh.normals
    tu = tu - n * (tu * n).sum(1, keepdims=True)
    flat = np.linalg.norm(tu, axis=1) < 1e-9
    if flat.any():                                      # no usable UV direction: any direction across the normal
        helper = np.where(np.abs(n[flat, 1:2]) < 0.9, [[0.0, 1.0, 0.0]], [[1.0, 0.0, 0.0]])
        tu[flat] = np.cross(helper, n[flat])
    tu = GrannyMesh._unit_rows(tu)
    hand = np.where((np.cross(n, tu) * tv).sum(1) < 0, -1.0, 1.0)
    return np.concatenate([tu, hand[:, None]], axis=1)


class Donor:
    """The donor body's skin, as points to take weights from."""

    def __init__(self, tree, mesh=None):
        self.geometry = GrannyMesh._Geometry(tree, mesh if mesh is not None else tree['Meshes'][0])
        g = self.geometry
        if not g.skinned:
            raise ValueError(f'{g.name}: the donor has no skin weights')
        self.dense = np.zeros((len(g.items), len(g.bindings)))
        for slot in range(g.weights.shape[1]):
            np.add.at(self.dense, (np.arange(len(g.items)), g.slots[:, slot]), g.weights[:, slot])
        self.box = (g.positions.min(0), g.positions.max(0))

    def cloud(self, samples, seed=7):
        """(points, weights): the donor's vertices plus points spread over its triangles."""
        g = self.geometry
        rng = np.random.default_rng(seed)
        corners = g.positions[g.triangles]
        area = np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1)
        pick = rng.choice(len(area), size=samples, p=area / area.sum())
        a, b = rng.random(samples), rng.random(samples)
        over = a + b > 1
        a[over], b[over] = 1 - a[over], 1 - b[over]
        bary = np.stack([1 - a - b, a, b], axis=1)
        points = (corners[pick] * bary[:, :, None]).sum(1)
        weights = (self.dense[g.triangles[pick]] * bary[:, :, None]).sum(1)
        own = GrannyMesh._unit_rows(np.array([it['Normal'][:3] for it in g.items], dtype=np.float64))
        normals = GrannyMesh._unit_rows((own[g.triangles[pick]] * bary[:, :, None]).sum(1))
        return np.concatenate([g.positions, points]), np.concatenate([self.dense, weights]), np.concatenate([own, normals])

    def fold(self, weights, prefixes):
        """Gives the weight of bones whose names start with one of `prefixes` to the nearest bone
        above them that is not left out (a new body without a tongue: {"ignore": ["tongue_"]})."""
        g = self.geometry
        column = {name: k for k, name in enumerate(g.bindings)}
        for k, name in enumerate(g.bindings):
            if not any(name.startswith(p) for p in prefixes):
                continue
            at = g.bone_names.index(name) if name in g.bone_names else -1
            while at >= 0:
                at = g.parents[at]
                parent = g.bone_names[at] if at >= 0 else None
                if parent in column and not any(parent.startswith(p) for p in prefixes):
                    weights[:, column[parent]] += weights[:, k]
                    break
            weights[:, k] = 0.0
        return weights


def transfer_skin(mesh, donor, options=None):
    """(weights N x 4 as bytes summing to 255, bone numbers N x 4) for the mesh's vertices, from
    the donor surface nearest to each. Vertices at one place (a UV seam) get the same skin; the
    result is smoothed over the mesh's own edges so parts do not tear along a border."""
    from scipy.spatial import cKDTree
    options = options or {}
    points, weights, facing = donor.cloud(int(options.get('samples', 150000)))
    if options.get('ignore'):
        weights = donor.fold(weights, list(options['ignore']))
    spot, first, place_of = np.unique(np.round(mesh.positions, 5), axis=0, return_index=True, return_inverse=True)
    place_of = place_of.reshape(-1)
    normal = np.zeros((len(spot), 3))
    np.add.at(normal, place_of, mesh.normals)
    normal = GrannyMesh._unit_rows(normal)
    k = int(options.get('neighbours', 12))
    distance, nearest = cKDTree(points).query(spot, k=k)
    # Near counts most, and a donor surface that faces the other way (the inside of a mouth
    # behind a lip, the far side of a thin ear) counts for next to nothing.
    agree = np.clip((facing[nearest] * normal[:, None, :]).sum(2), 0.0, 1.0) ** 2 + 0.02
    share = agree / (distance + 1e-4) ** 2
    share /= share.sum(1, keepdims=True)
    skin = (weights[nearest] * share[:, :, None]).sum(1)
    edges = place_of[mesh.triangles]
    pairs = np.concatenate([edges[:, [0, 1]], edges[:, [1, 2]], edges[:, [2, 0]]])
    pairs = np.concatenate([pairs, pairs[:, ::-1]])
    for _ in range(int(options.get('smooth', 2))):
        total = skin.copy()
        count = np.ones(len(skin))
        np.add.at(total, pairs[:, 0], skin[pairs[:, 1]])
        np.add.at(count, pairs[:, 0], 1.0)
        skin = total / count[:, None]
    top = np.argsort(-skin, axis=1)[:, :4]
    best = np.take_along_axis(skin, top, axis=1)
    best /= best.sum(1, keepdims=True)
    quantised = np.floor(best * 255.0).astype(np.int64)
    quantised[:, 0] += 255 - quantised.sum(1)
    top = np.where(quantised > 0, top, top[:, :1])        # an unused slot repeats the main bone, as stock files do
    return quantised[place_of], top[place_of], float(distance[:, 0].max()), float(np.median(distance[:, 0]))


def uses_own_rig(mesh, bone_names, options=None):
    """Whether the skin comes from the file: "from": "file" | "donor" | "auto" (the default: the
    file's, when it has a rig and at least one of its joints is a bone of the donor)."""
    wanted = (options or {}).get('from', 'auto')
    if wanted == 'file' and mesh.joints is None:
        raise ValueError('"skin": {"from": "file"}: the mesh file has no rig (only .glb / .gltf carry one)')
    return mesh.joints is not None and (wanted == 'file' or (wanted == 'auto' and any(n in bone_names for n in mesh.joint_names)))


def missing_bones(mesh, bone_names):
    """Joints of the file's rig that carry weight (or sit above one that does) and that the
    skeleton does not have, parents first: [(name, parent name, bind 4 x 4)]."""
    used = {mesh.joint_names[j] for j in np.unique(mesh.joints[mesh.weights > 0])}
    wanted = []
    for name in used:
        chain = []
        while name is not None and name not in bone_names:
            chain.append(name)
            name = mesh.rig[name][0]
        if chain and name is None:
            raise ValueError(f'the joint "{chain[0]}" hangs under no bone of the game skeleton; parent it to one')
        for one in reversed(chain):
            if one not in wanted:
                wanted.append(one)
    order = {name: k for k, name in enumerate(mesh.joint_names)}
    wanted.sort(key=lambda n: (len(_chain(mesh, n)), order[n]))
    return [(name, mesh.rig[name][0], mesh.rig[name][1]) for name in wanted]


def _chain(mesh, name):
    out = []
    while name is not None:
        out.append(name)
        name = mesh.rig[name][0] if name in mesh.rig else None
    return out


def add_bones(bones, new):
    """Appends bones to a skeleton's bone list (a model's embedded one, or a .skeleton file's).
    new: [(name, parent name, bind matrix)] as missing_bones gives them. Returns the names added."""
    added = []
    for name, parent, bind in new:
        names = [b['Name'] for b in bones]
        if name in names:
            continue
        if parent not in names:
            raise ValueError(f'new bone "{name}": its parent "{parent}" is not in the skeleton')
        above = bones[names.index(parent)]
        local = bind @ np.array(above['InverseWorldTransform'], dtype=np.float64).reshape(4, 4)
        bones.append(_make_bone(bones[-1], name, names.index(parent), local, bind, above.get('LODError', 0.0)))
        added.append(name)
    return added


def _local_parts(local, what='a bone'):
    """(position, quaternion, 3 x 3 scale, stretched) of a 4 x 4 local matrix for row vectors."""
    import GrannyAnim
    size = np.linalg.norm(local[:3, :3], axis=1)
    turn = local[:3, :3] / size[:, None]
    if np.linalg.det(turn) < 0:
        raise ValueError(f'{what} is mirrored against its parent; apply the scale in the modelling program')
    quaternion = GrannyAnim.matrix_quat(turn)
    stretched = not np.allclose(size, 1.0, atol=1e-4)
    return local[3, :3], quaternion, (local[:3, :3] @ GrannyAnim.quat_matrix(quaternion).T if stretched else np.eye(3)), stretched


def _make_bone(template, name, parent_index, local, bind, lod_error):
    import copy
    position, quaternion, scale, stretched = _local_parts(local, f'bone "{name}"')
    bone = copy.deepcopy(template)
    key = 'LocalTransform' if 'LocalTransform' in bone else 'Transform'
    bone[key] = {'flags': 3 | (4 if stretched else 0), 'position': [float(v) for v in position],
                 'orientation': [float(v) for v in quaternion], 'scale_shear': [[float(v) for v in row] for row in scale]}
    bone.update({'Name': name, 'ParentIndex': parent_index, 'LODError': lod_error,
                 'InverseWorldTransform': [float(v) for v in np.linalg.inv(bind).reshape(-1)]})
    if 'ExtendedData' in bone:
        bone['ExtendedData'] = None
    return bone


def set_skeleton(bones, mesh):
    """Replaces a bone list (a model's embedded skeleton, a .skeleton file's) by the file's own
    rig: every joint, parents first, with its bind pose as the rest pose. Returns the names."""
    template = bones[0]
    error = float(np.median([b.get('LODError', 0.0) for b in bones]))
    order = sorted(mesh.joint_names, key=lambda n: (len(_chain(mesh, n)), mesh.joint_names.index(n)))
    made = []
    for name in order:
        parent, bind = mesh.rig[name]
        local = bind if parent is None else bind @ np.linalg.inv(mesh.rig[parent][1])
        made.append(_make_bone(template, name, -1 if parent is None else order.index(parent), local, bind, error))
    bones[:] = made
    return order


def own_skeleton_file(data, mesh):
    """A stock .skeleton file as the container for the file's own rig; returns bytes."""
    source = Granny.read(data)
    tree = source.root()
    order = set_skeleton(tree['Skeletons'][0]['Bones'], mesh)
    for holder in [tree['Skeletons'][0]] + list(tree.get('Models') or []):
        holder['Name'] = order[0]
    return Granny.Writer(source.tag, tuple(source.extra_tags)).build(source.describe(source.root_type), tree)


def own_clips(mesh, template, skeleton_source, fps=30.0):
    """The file's animations as a game animation file. template: a stock combined.animations (its
    structure and flags are reused, none of its motion); skeleton_source: a model or skeleton
    file that already holds the file's rig. Returns (bytes, {clip: seconds})."""
    import copy
    import GrannyAnim
    animations = GrannyAnim.load(template)
    base = copy.deepcopy(animations.tree['Animations'][0])
    groups = base['TrackGroups']
    wanted = 'root' if len(groups) > 1 and any(g['Name'] == 'root' for g in groups) else None
    for group in groups:
        if wanted is None or group['Name'] == wanted:
            group['TransformTracks'] = []
    if wanted is None:
        del groups[1:]
    animations.tree['Animations'] = []
    skeleton = GrannyAnim.Skeleton(skeleton_source)
    roots = {name for name, (parent, _) in mesh.rig.items() if parent is None}
    done = {}
    for clip, seconds in mesh.model.clips.items():
        count = max(2, int(round(seconds * fps)) + 1)
        times = np.linspace(0.0, seconds, count)
        poses = []
        for t in times:
            pose = {}
            for name, local in mesh.model.pose(clip, float(t)).items():
                position, quaternion, scale, _ = _local_parts(local @ mesh.frame if name in roots else local, f'joint "{name}" in clip "{clip}"')
                pose[name] = GrannyAnim.Local(position, quaternion, scale)
            poses.append(pose)
        animations.add(clip, GrannyAnim.Keys(times, poses, base, wanted), skeleton)
        done[clip] = float(seconds)
    if animations.tree['Animations'] and 'TrackGroups' in animations.tree:
        animations.tree['TrackGroups'] = list(animations.tree['Animations'][0]['TrackGroups'])
    return animations.to_bytes(), done


def extend_skeleton(data, new):
    """A .skeleton file with bones added (see add_bones); returns (bytes, names added)."""
    source = Granny.read(data)
    tree = source.root()
    added = add_bones(tree['Skeletons'][0]['Bones'], new)
    return Granny.Writer(source.tag, tuple(source.extra_tags)).build(source.describe(source.root_type), tree), added


def file_skin(mesh, geometry):
    """(weights N x 4 as bytes summing to 255, bone numbers N x 4) from the file's own rig: each
    joint is the game bone of the same name."""
    slot = np.zeros(len(mesh.joint_names), dtype=np.int64)
    for j in np.unique(mesh.joints[mesh.weights > 0]):
        slot[j] = GrannyMesh._binding_slot(geometry, mesh.joint_names[j])
    weights = np.where(mesh.weights > 0, mesh.weights, 0.0)
    order = np.argsort(-weights, axis=1)
    weights = np.take_along_axis(weights, order, axis=1)
    slots = slot[np.take_along_axis(mesh.joints, order, axis=1)]
    total = weights.sum(1, keepdims=True)
    if (total <= 0).any():
        raise ValueError(f'{int((total <= 0).sum())} vertices of the file follow no joint; weight them in the modelling program')
    quantised = np.floor(weights / total * 255.0).astype(np.int64)
    quantised[:, 0] += 255 - quantised.sum(1)
    return quantised, np.where(quantised > 0, slots, slots[:, :1])


def replace_geometry(data, mesh, skin_options=None, textures=None, own_skeleton=False):
    """A donor model file with its first mesh's geometry replaced by `mesh` (already in game
    space); returns (bytes, report lines). Skeleton, bone bindings, material and the model's LOD
    number stay. The skin is the file's own when it brought a rig on the game's bone names
    (uses_own_rig; joints the skeleton lacks are added to it as new bones), otherwise it is
    carried over from the donor geometry being replaced.
    own_skeleton: no donor at all. The file's rig replaces the skeleton outright and the skin is
    the file's; the model file then only lends its format (types, material slot, LOD number)."""
    source = Granny.read(data)
    tree = source.root()
    if len(tree['Meshes']) != 1:
        raise ValueError(f'the donor file has {len(tree["Meshes"])} meshes; a one-mesh body is needed')
    # A model file carries its own LOD level and, in a second model entry with a mesh and a
    # skeleton of its own, the next level (see GrannyMesh.all_meshes). Every entry gets the new
    # body: the next level a simpler copy, by the ratio the stock meshes have.
    places = GrannyMesh.all_meshes(tree)
    skeletons = GrannyMesh.bone_lists(tree)
    stock = [len(Granny.mesh_indices(m['PrimaryTopology'])) // 3 for m in places]
    levels = [mesh] + [mesh if stock[k] >= stock[0] else simplify(mesh, max(64, int(len(mesh.triangles) * stock[k] / stock[0])),
                                                                 (skin_options or {}).get('simplify', 'auto')) for k in range(1, len(places))]
    report = []
    if own_skeleton:
        if mesh.joints is None:
            raise ValueError('a body without a donor needs its own rig: a .glb / .gltf with an armature and weights')
        import copy
        for bones in skeletons:
            order = set_skeleton(bones, mesh)
        for holder in list(tree.get('Skeletons') or []) + list(tree.get('Models') or []) + [m['Skeleton'] for m in tree.get('Models') or []]:
            holder['Name'] = order[0]
        for place, level in zip(places, levels):
            bindings = place['BoneBindings']
            first = copy.deepcopy(bindings[0])
            first.update({'BoneName': order[0], 'OBBMin': [0.0, 0.0, 0.0], 'OBBMax': [0.0, 0.0, 0.0], 'TriangleIndices': []})
            bindings[:] = [first]
            report += _fill_mesh(GrannyMesh._Geometry(tree, place), level, True, [], None, skin_options)
    else:
        known = {b['Name'] for b in skeletons[0]}
        own = uses_own_rig(mesh, known, skin_options)
        added = []
        if own:
            new = missing_bones(mesh, known)
            if new and not (skin_options or {}).get('new_bones', True):
                raise ValueError(f'the file uses joints the skeleton lacks ({", ".join(n for n, _, _ in new)}) and "new_bones" is off')
            for bones in skeletons:
                added = add_bones(bones, new)
        for place, level in zip(places, levels):
            donor = Donor(tree, place)
            report += _fill_mesh(donor.geometry, level, own, added, donor, skin_options)
    for k in range(1, len(report)):
        if not report[k].startswith('  '):
            report[k] = '  next LOD level, ' + report[k]
    if textures:
        lowered = dict(textures)
        lowered.update({k.lower(): v for k, v in textures.items()})
        report.append(f'  {GrannyMesh._rename_strings(tree, lowered)} texture names changed')
    out = Granny.Writer(source.tag, tuple(source.extra_tags)).build(source.describe(source.root_type), tree)
    return out, report


def _fill_mesh(geometry, mesh, own, added, donor, skin_options):
    """Puts `mesh` into one mesh of the tree (geometry: its GrannyMesh._Geometry); report lines."""
    if own:
        weights, slots = file_skin(mesh, geometry)
        far = typical = 0.0
    else:
        weights, slots, far, typical = transfer_skin(mesh, donor, skin_options)
    tangent = tangents(mesh)
    template = geometry.items[0]
    scale = float(np.abs(mesh.positions).max())
    if 'VertexScale' in geometry.extended:
        geometry.extended['VertexScale'] = scale
    elif scale > 1.0:
        raise ValueError('the donor mesh has no VertexScale; the new mesh must stay within -1..1')
    else:
        scale = 1.0
    quantised = np.clip(np.round(mesh.positions / scale * 32767.0), -32767, 32767).astype(int)
    normals = np.round(mesh.normals * 127.0).astype(int)
    tangent_bytes = np.round(tangent * 127.0).astype(int)
    items = []
    for k in range(len(mesh.positions)):
        vertex = {}
        for field in template:
            if field == 'Position':
                vertex[field] = [int(v) for v in quantised[k]] + list(template[field][3:])
            elif field == 'Normal':
                vertex[field] = [int(v) for v in normals[k]] + list(template[field][3:])
            elif field == 'Tangent':
                vertex[field] = [int(v) for v in tangent_bytes[k]]
            elif field.startswith('TextureCoordinates'):
                vertex[field] = [float(v) for v in mesh.uvs[k]]
            elif field == 'BoneWeights':
                vertex[field] = [int(v) for v in weights[k]]
            elif field == 'BoneIndices':
                vertex[field] = [int(v) for v in slots[k]]
            else:
                vertex[field] = template[field]
        items.append(vertex)
    geometry.items[:] = items
    topology = geometry.topology
    width = Granny.set_mesh_indices(topology, mesh.triangles.reshape(-1), len(items))
    group = dict(topology['Groups'][0])
    group.update({'TriFirst': 0, 'TriCount': len(mesh.triangles)})
    topology['Groups'][:] = [group]
    GrannyMesh._refresh_boxes(geometry)
    if own:
        report = [f'{geometry.name}: {len(mesh.triangles)} triangles, {len(items)} vertices; skin from the file\'s own rig '
                  f'({len(np.unique(slots[weights > 0]))} bones)']
        if added:
            report.append(f'  new bones added to the skeleton: {", ".join(added)}')
    else:
        report = [f'{geometry.name}: {len(mesh.triangles)} triangles, {len(items)} vertices; skin from the donor '
                  f'(typical distance {typical:.3f}, farthest {far:.3f} units)']
    if donor is not None and far > 0.25 * float((donor.box[1] - donor.box[0]).max()):
        report.append('  some vertices lie far from the donor: their weights are a guess; model closer to the reference')
    if width == 4:
        report.append(f'  {len(items)} vertices: over 65,536, so 32-bit indices (Indices); the game reads those (stock bodies use them too)')
    return report


# --- textures ------------------------------------------------------------------------------

def donor_textures(tree):
    """{usage: path} of a model's material maps (AlbedoTexture, NormalTexture, ORMTexture, ...)."""
    out = {}
    for binding in tree['Meshes'][0].get('MaterialBindings') or []:
        for entry in binding['Material'].get('Maps') or []:
            if entry['Map'].get('Texture'):
                out[entry['Usage']] = entry['Map']['Texture']['FromFileName']
    return out


def normal_to_game(picture, green='up'):
    """A tangent-space normal map as modelling programs write it (x in red, y in green, z in
    blue) -> the game's layout: x in alpha, y in green, red full, blue empty (z is worked out
    from x and y). The game's green points up the picture (its shader's green axis is the
    opposite of dP/dv, v running down; stock maps, shader and an in-game test agree, see the
    README), so a map with green up (glTF, Blender, OpenGL; the default) is kept as it is and
    a "down" (DirectX) map is flipped. Before 2026-11-26 this was the other way round: bodies
    built before then carry upside-down relief until their textures are made again."""
    from PIL import Image
    rgb = np.asarray(picture.convert('RGB'), dtype=np.uint8)
    out = np.zeros(rgb.shape[:2] + (4,), dtype=np.uint8)
    out[..., 0] = 255
    out[..., 1] = 255 - rgb[..., 1] if green == 'down' else rgb[..., 1]
    out[..., 3] = rgb[..., 0]
    return Image.fromarray(out, 'RGBA')


def orm_to_game(roughness_metal, occlusion=None, metal=False):
    """glTF's metallic-roughness picture (roughness in green, metal in blue) and its occlusion
    picture (red) -> the game's ORM map: occlusion in red, roughness in green. Blue (metal) is
    empty in every stock creature map looked at; "orm_metal": true writes it anyway."""
    from PIL import Image
    source = np.asarray(roughness_metal.convert('RGB'), dtype=np.uint8)
    out = np.zeros(source.shape[:2] + (4,), dtype=np.uint8)
    out[..., 0] = 255
    if occlusion is not None:
        out[..., 0] = np.asarray(occlusion.convert('RGB').resize(roughness_metal.size), dtype=np.uint8)[..., 0]
    out[..., 1] = source[..., 1]
    if metal:
        out[..., 2] = source[..., 2]
    out[..., 3] = 255
    return Image.fromarray(out, 'RGBA')


def normal_from_albedo(picture, strength=2.0):
    """A normal map (green up) guessed from the colour picture: bright is taken for high. It adds
    fur and wrinkle relief where there is none; it knows nothing of the real shape."""
    from PIL import Image, ImageFilter
    grey = np.asarray(picture.convert('L').filter(ImageFilter.GaussianBlur(1.0)), dtype=np.float64) / 255.0
    dx = (np.roll(grey, -1, axis=1) - np.roll(grey, 1, axis=1)) * strength
    dy = (np.roll(grey, -1, axis=0) - np.roll(grey, 1, axis=0)) * strength
    normal = np.stack([-dx, dy, np.ones_like(grey) / 4.0], axis=2)
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    return Image.fromarray(np.round((normal * 0.5 + 0.5) * 255.0).astype(np.uint8), 'RGB')


def make_textures(spec, name, folder, read, tree, embedded=None, base_dir='.', images=None):
    """Writes the body's own textures; returns ({donor path: new path}, [written game paths]).
    images: the pictures the mesh file carried (Mesh.images); spec entries come first."""
    from PIL import Image
    maps = donor_textures(tree)
    size = int(spec.get('texture_size', 1024))
    renames, written = {}, {}
    images = dict(images or {})
    if embedded is not None:
        images.setdefault('albedo', embedded)
    colour = Image.open(os.path.join(base_dir, spec['albedo'])) if spec.get('albedo') else images.get('albedo')
    made = {}
    if spec.get('normal') == 'from_albedo':
        if colour is None:
            raise ValueError('"normal": "from_albedo" needs a colour texture')
        made['normal'] = normal_to_game(normal_from_albedo(colour, float(spec.get('normal_strength', 2.0))))
    elif spec.get('normal'):
        made['normal'] = normal_to_game(Image.open(os.path.join(base_dir, spec['normal'])), spec.get('normal_green', 'up'))
    elif images.get('normal') is not None:
        made['normal'] = normal_to_game(images['normal'])
    if spec.get('orm'):
        given = Image.open(os.path.join(base_dir, spec['orm']))
        made['orm'] = orm_to_game(given, given, bool(spec.get('orm_metal')))
    elif images.get('orm') is not None:
        made['orm'] = orm_to_game(images['orm'], images.get('occlusion'), bool(spec.get('orm_metal')))
    for key, usage, suffix, srgb in (('albedo', 'AlbedoTexture', 'alb', True), ('normal', 'NormalTexture', 'nrm', False),
                                     ('orm', 'ORMTexture', 'orm', False), ('sss', 'ThicknessTexture', 'sss', True)):
        old = maps.get(usage)
        if old is None:
            continue
        if key in made:
            picture = made[key]
        elif key == 'albedo' and colour is not None:
            picture = colour
        elif key == 'sss' and spec.get('sss'):
            picture = Image.open(os.path.join(base_dir, spec['sss']))
        elif key == 'albedo':
            raise ValueError('no colour texture: give "albedo", or use a .glb that carries one')
        else:
            # No picture given: one flat colour, the average of the donor's map, so the surface
            # is plain there instead of carrying the donor's details on the wrong UVs.
            stock = np.asarray(HdTexture.to_image(read(old)), dtype=np.float64)
            flat = np.round(stock.reshape(-1, 4).mean(0)).astype(np.uint8)
            picture = Image.fromarray(np.tile(flat, (16, 16, 1)), 'RGBA')
        new = f'{folder}/{name}_{suffix}.texture'
        flat_map = key != 'albedo' and key not in made and not (key == 'sss' and spec.get('sss'))
        written[new] = HdTexture.from_image_bc3(picture, srgb=srgb, size=16 if flat_map else size)
        renames[old] = f'data/{new}'
    # The tint mask says where a colour variant tints the body. The template's own mask is laid
    # out for the template's UVs, so the body gets the game's shared neutral mask instead.
    mask = maps.get('MaskTexture')
    if mask and mask.lower() != NEUTRAL_MASK:
        renames[mask] = NEUTRAL_MASK
    return renames, written


# --- commands ------------------------------------------------------------------------------

def _lod_files(names, stem):
    stem = stem[5:] if stem.startswith('data/') else stem
    stem = stem[:-len('.model')] if stem.endswith('.model') else stem
    files = sorted(n for n in names if n.startswith(f'{stem}_lod') and n.endswith('.model'))
    if not files and f'{stem}.model' in names:
        files = [f'{stem}.model']
    if not files:
        raise ValueError(f'donor {stem}: no model files in the game')
    return stem, files


def import_body(spec, name, read, names, base_dir='.', log=print):
    """The whole import: {game path: bytes} for the model files and textures, plus a report."""
    # No "donor" (or "skeleton": "file"): the body is all the file's own, skeleton, skin and
    # clips; a stock model ("template") only lends the file format and the LOD file count.
    standalone = spec.get('skeleton') == 'file' or not spec.get('donor')
    stem, files = _lod_files(names, spec.get('donor') or spec.get('template') or TEMPLATE)
    part = stem.rsplit('/', 1)[-1]
    folder = f'hd/character/enemy/{name}'
    donors = [read(f) for f in files]
    first = Granny.read(donors[0]).root()
    donor = Donor(first)
    mesh, embedded = load(os.path.join(base_dir, spec['mesh']), spec.get('axes'))
    if standalone and mesh.joints is None:
        raise ValueError('without a "donor" the mesh file has to bring its own rig: a .glb / .gltf with an armature and weights')
    mesh, unwrap_notes = ensure_uvs(mesh, spec)
    if spec.get('weld', True):
        mesh, before = weld(mesh)
        if before != len(mesh.positions):
            unwrap_notes = unwrap_notes + [f'welded: {before} vertices -> {len(mesh.positions)} (same point, UV and skin)']
    embedded = embedded if embedded is not None else mesh.images.get('albedo')
    notes = unwrap_notes + place(mesh, donor.box, dict(spec, fit=spec.get('fit', 'none')) if standalone else spec)
    renames, out = make_textures(spec, name, folder, read, first, embedded, base_dir, mesh.images)
    bone_names = {b['Name'] for b in first['Models'][0]['Skeleton']['Bones']}
    new_bones = missing_bones(mesh, bone_names) if not standalone and uses_own_rig(mesh, bone_names, spec.get('skin')) else []
    counts = [len(Granny.mesh_indices(Granny.read(d).root()['Meshes'][0]['PrimaryTopology'])) // 3 for d in donors]
    ratios = spec.get('lods') or [c / counts[0] for c in counts]
    report = {'name': name, 'donor': f'data/{stem}.model', 'standalone': standalone, 'model': f'data/{folder}/{part}.model', 'notes': notes, 'files': [],
              'textures': sorted(renames.values()), 'box': [mesh.positions.min(0).round(4).tolist(), mesh.positions.max(0).round(4).tolist()]}
    for k, (path, data) in enumerate(zip(files, donors)):
        ratio = ratios[min(k, len(ratios) - 1)]
        level = mesh if ratio >= 1.0 else simplify(mesh, max(64, int(len(mesh.triangles) * ratio)), spec.get('simplify', 'auto'))
        cap = int(spec.get('max_vertices', 65535) or 0)
        if cap and len(level.positions) > cap:
            level = simplify(level, int(len(level.triangles) * cap * 60000 / 65535 / len(level.positions)), spec.get('simplify', 'auto'))
        built, lines = replace_geometry(data, level, spec.get('skin'), renames, standalone)
        target = f'{folder}/{part}{path[len(stem):]}'
        out[target] = built
        report['files'].append({'path': target, 'triangles': len(level.triangles), 'vertices': len(level.positions), 'notes': lines})
        log(f'  {target}: {lines[0].split(": ", 1)[1]}')
        for line in lines[1:]:
            log(f'  {line.strip()}')
    if standalone:
        folder_of = stem.rsplit('/', 1)[0]
        stock = sorted(n for n in names if n.startswith(f'{folder_of}/skeleton/') and n.endswith('.skeleton'))
        if not stock:
            raise ValueError(f'the template {stem} has no .skeleton file beside it to use as a container')
        out[f'{folder}/skeleton/{name}.skeleton'] = own_skeleton_file(read(stock[0]), mesh)
        report['skeleton'] = {'file': f'data/{folder}/skeleton/{name}.skeleton', 'bones': len(mesh.joint_names)}
        log(f'  {folder}/skeleton/{name}.skeleton: the file\'s own {len(mesh.joint_names)} bones')
        clips_template = f'{folder_of}/animation/combined.animations'
        if mesh.model.clips and clips_template in names:
            built, clips = own_clips(mesh, read(clips_template), out[f'{folder}/skeleton/{name}.skeleton'], float(spec.get('fps', 30.0)))
            out[f'{folder}/animation/combined.animations'] = built
            report['clips'] = clips
            log(f'  {folder}/animation/combined.animations: {", ".join(f"{k} {v:.2f}s" for k, v in clips.items())}')
        elif not mesh.model.clips:
            log('  the file has no animations: the body has a skeleton but no clips yet')
    if new_bones:
        # The definition's .skeleton file needs the same bones as the models' embedded skeletons.
        folder_of = stem.rsplit('/', 1)[0]
        stock = sorted(n for n in names if n.startswith(f'{folder_of}/skeleton/') and n.endswith('.skeleton'))
        report['newBones'] = [{'name': n, 'parent': p} for n, p, _ in new_bones]
        if stock:
            built, _ = extend_skeleton(read(stock[0]), new_bones)
            out[f'{folder}/skeleton/{name}.skeleton'] = built
            report['skeleton'] = {'file': f'data/{folder}/skeleton/{name}.skeleton', 'from': f'data/{stock[0]}'}
            log(f'  {folder}/skeleton/{name}.skeleton: {len(new_bones)} new bones; point the definition\'s skeleton at it')
        else:
            log(f'  {len(new_bones)} new bones, but no .skeleton file found beside the donor to extend')
    return out, report


def write_reference(read, names, donor, out_dir):
    from PIL import Image
    stem, files = _lod_files(names, donor)
    tree = Granny.read(read(files[0])).root()
    g = GrannyMesh._Geometry(tree, tree['Meshes'][0])
    os.makedirs(out_dir, exist_ok=True)
    uvs = np.array([it['TextureCoordinates0'] for it in g.items], dtype=np.float64)
    normals = GrannyMesh._unit_rows(np.array([it['Normal'][:3] for it in g.items], dtype=np.float64))
    with open(os.path.join(out_dir, 'donor.obj'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(f'# {stem}: bind pose, +Y up, +Z to the head, one unit = one foot\nmtllib donor.mtl\nusemtl donor\n')
        for p in g.positions:
            f.write(f'v {p[0]:.5f} {p[1]:.5f} {p[2]:.5f}\n')
        for t in uvs:
            f.write(f'vt {t[0]:.5f} {1 - t[1]:.5f}\n')
        for n in normals:
            f.write(f'vn {n[0]:.4f} {n[1]:.4f} {n[2]:.4f}\n')
        for a, b, c in g.triangles + 1:
            f.write(f'f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}\n')
    with open(os.path.join(out_dir, 'donor.mtl'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('newmtl donor\nKd 1 1 1\nmap_Kd donor.png\n')
    albedo = donor_textures(tree).get('AlbedoTexture')
    if albedo:
        HdTexture.to_image(read(albedo)).convert('RGB').save(os.path.join(out_dir, 'donor.png'))
    bones = {}
    for name, inverse in g.inverse.items():
        world = np.linalg.inv(inverse)
        bones[name] = {'position': world[3, :3].round(4).tolist(), 'parent': g.bone_names[g.parents[g.bone_names.index(name)]] if g.parents[g.bone_names.index(name)] >= 0 else None}
    with open(os.path.join(out_dir, 'bones.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'model': stem, 'box': [g.positions.min(0).round(4).tolist(), g.positions.max(0).round(4).tolist()], 'bones': bones}, f, indent=1)
    if g.skinned:
        # The same body with its armature and skin: weight a new mesh to these bones (or add
        # bones under them) and export it; the importer then takes the file's own weights.
        import io
        import Gltf
        rig = []
        for k, bone in enumerate(g.bone_names):
            bind = np.linalg.inv(g.inverse[bone])
            up = g.parents[k]
            rig.append((bone, up, bind @ g.inverse[g.bone_names[up]] if up >= 0 else bind, g.inverse[bone]))
        number = np.array([g.bone_names.index(b) for b in g.bindings], dtype=np.int64)
        png = None
        if albedo:
            buffer = io.BytesIO()
            HdTexture.to_image(read(albedo)).convert('RGB').save(buffer, 'PNG')
            png = buffer.getvalue()
        Gltf.write_rigged(os.path.join(out_dir, 'donor.glb'), g.positions, normals, uvs, g.triangles, number[g.slots], g.weights, rig, png)
    return len(g.items), len(g.triangles)


def main(argv):
    parser = argparse.ArgumentParser(description='Import a mesh made outside the game as a skinned D2R body.')
    sub = parser.add_subparsers(dest='command', required=True)
    r = sub.add_parser('reference')
    r.add_argument('--game', default=os.environ.get('D2R_PATH'))
    r.add_argument('--donor', required=True)
    r.add_argument('--out', required=True)
    b = sub.add_parser('build')
    b.add_argument('spec')
    b.add_argument('--game', default=os.environ.get('D2R_PATH'))
    b.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    from d2r_casc import D2RArchive
    with D2RArchive(args.game) as archive:
        names = set(archive.list())

        def read(path):
            return archive.read(path[5:] if path.startswith('data/') else path)
        if args.command == 'reference':
            vertices, triangles = write_reference(read, names, args.donor, args.out)
            print(f'{args.donor}: {vertices} vertices, {triangles} triangles -> {args.out} (donor.obj, donor.png, bones.json, donor.glb with the armature)')
            return 0
        with open(args.spec, encoding='utf-8') as f:
            spec = json.load(f)
        files, report = import_body(spec, spec['name'], read, names, os.path.dirname(os.path.abspath(args.spec)))
    for path, data in files.items():
        full = os.path.join(args.out, *path.split('/'))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'wb') as f:
            f.write(data)
    with open(os.path.join(args.out, f"mesh_import_{spec['name']}.report.json"), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(report, f, indent=1)
    print(f"{spec['name']}: {len(files)} files written to {args.out}; list {report['model']} in the model index with donor {report['donor']}")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
