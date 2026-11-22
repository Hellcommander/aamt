"""UV coordinates for a mesh that has none (a sculpt, a scan, an image-to-3D result), and a
texture baked from its vertex colours.

    positions, triangles, uvs, source = MeshUnwrap.unwrap(positions, triangles)
        new vertex list (a vertex on a chart border is doubled), uvs N x 2 in 0..1 (v down), and
        `source`: for each new vertex the old vertex it came from (to carry normals, skin, colours)
    image = MeshUnwrap.bake_colours(uvs, triangles, colours, size=1024)      # PIL RGB

How: the surface is cut into charts of faces that look roughly the same way (six directions,
then split where they are not connected; crumbs join a neighbour), each chart is flattened with
a least squares conformal map (pmp-library's LSCM through Tools/Shared/pmp_lib.py), scaled so
that texture area follows surface area, and the charts are packed in rows.

A chart pmp cannot take (a pinched vertex, no open edge) or one that comes out folded is
flattened by looking straight at it instead (reported in the notes). This is an unwrap for
getting colour onto a body, not a hand-laid layout: seams fall wherever the facing changes.

Checked with pmpwrap 1 (pmp-library 3.0.0), numpy 2.5.2, scipy 1.18.1.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Shared'))

_DIRECTIONS = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], dtype=np.float64)


def _cross2(a, b):
    return a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]


def _charts(triangles, normals, minimum):
    """Chart number per face: same facing and connected; charts under `minimum` faces join a neighbour."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    count = len(triangles)
    label = (normals @ _DIRECTIONS.T).argmax(1)
    edges = np.sort(np.concatenate([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]]), axis=1)
    face = np.tile(np.arange(count), 3)
    key = edges[:, 0] * (int(triangles.max()) + 1) + edges[:, 1]
    order = np.argsort(key, kind='stable')
    key, face = key[order], face[order]
    same = key[1:] == key[:-1]
    a, b = face[:-1][same], face[1:][same]                 # faces that share an edge
    for _ in range(8):
        joined = label[a] == label[b]
        graph = coo_matrix((np.ones(joined.sum()), (a[joined], b[joined])), shape=(count, count))
        _, chart = connected_components(graph, directed=False)
        sizes = np.bincount(chart)
        small = sizes[chart] < minimum
        if not small.any():
            break
        # A crumb takes the facing of the chart it shares most edges with.
        across = chart[a] != chart[b]
        changed = False
        for first, second in ((a[across], b[across]), (b[across], a[across])):
            rows = small[first] & ~small[second]
            if rows.any():
                pairs = np.unique(np.stack([chart[first[rows]], label[second[rows]]], axis=1), axis=0)
                take = dict(pairs.tolist())
                hit = np.isin(chart, list(take))
                label[hit] = [take[c] for c in chart[hit]]
                changed = True
        if not changed:
            break
    return chart


def _flatten(points, faces):
    """UVs for one chart: LSCM, or a straight-on view when that fails or folds. Returns (uv, how)."""
    import pmp_lib
    used = np.unique(faces)
    remap = -np.ones(int(faces.max()) + 1, dtype=np.int64)
    remap[used] = np.arange(len(used))
    local = remap[faces]
    p = points[used]
    how = 'lscm'
    uv = None
    try:
        with pmp_lib.Mesh(p, local) as m:
            uv = m.lscm()
        if not np.isfinite(uv).all():
            uv = None
    except (ValueError, RuntimeError):
        uv = None
    if uv is not None:
        area = _cross2(uv[local[:, 1]] - uv[local[:, 0]], uv[local[:, 2]] - uv[local[:, 0]])
        if (np.sign(area) != np.sign(np.median(area))).mean() > 0.02 or np.abs(area).sum() < 1e-12:
            uv = None
    if uv is None:
        how = 'flat'
        normal = np.cross(p[local[:, 1]] - p[local[:, 0]], p[local[:, 2]] - p[local[:, 0]]).sum(0)
        normal /= np.linalg.norm(normal) or 1.0
        helper = np.array([0.0, 1.0, 0.0]) if abs(normal[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
        right = np.cross(helper, normal)
        right /= np.linalg.norm(right)
        uv = np.stack([p @ right, p @ np.cross(normal, right)], axis=1)
    # Texture area follows surface area.
    surface = np.linalg.norm(np.cross(p[local[:, 1]] - p[local[:, 0]], p[local[:, 2]] - p[local[:, 0]]), axis=1).sum()
    flat = np.abs(_cross2(uv[local[:, 1]] - uv[local[:, 0]], uv[local[:, 2]] - uv[local[:, 0]])).sum()
    uv = (uv - uv.min(0)) * np.sqrt(surface / max(flat, 1e-18))
    return used, local, uv, how


def _pack(sizes, padding):
    """Rows of rectangles in a unit square: (scale, [(x, y)]) for (width, height) sizes."""
    order = np.argsort(-sizes[:, 1])

    def lay(scale):
        spots = np.zeros((len(sizes), 2))
        x = y = row = 0.0
        for k in order:
            w, h = sizes[k] * scale + padding
            if w > 1.0:
                return None
            if x + w > 1.0:
                x, y, row = 0.0, y + row, 0.0
            spots[k] = (x, y)
            x += w
            row = max(row, h)
        return spots if y + row <= 1.0 else None

    low, high = 0.0, 1.0 / max(float(sizes.max()), 1e-9)
    best = None
    for _ in range(40):
        middle = (low + high) / 2
        spots = lay(middle)
        if spots is None:
            high = middle
        else:
            low, best = middle, spots
    if best is None:
        raise ValueError('the charts could not be packed (too many for the padding)')
    return low, best


def unwrap(positions, triangles, min_chart_faces=24, padding=0.004):
    """See the module text. Returns (positions, triangles, uvs, source, notes)."""
    positions = np.asarray(positions, dtype=np.float64)
    triangles = np.asarray(triangles, dtype=np.int64)
    spot, first, place = np.unique(np.round(positions, 6), axis=0, return_index=True, return_inverse=True)
    place = place.reshape(-1)
    welded = place[triangles]
    alive = (welded[:, 0] != welded[:, 1]) & (welded[:, 1] != welded[:, 2]) & (welded[:, 0] != welded[:, 2])
    welded, kept = welded[alive], triangles[alive]
    normal = np.cross(spot[welded[:, 1]] - spot[welded[:, 0]], spot[welded[:, 2]] - spot[welded[:, 0]])
    normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-18)
    chart = _charts(welded, normal, min_chart_faces)
    pieces, sizes, flat_count = [], [], 0
    for number in np.unique(chart):
        rows = np.flatnonzero(chart == number)
        used, local, uv, how = _flatten(spot, welded[rows])
        flat_count += how == 'flat'
        # The old vertex behind each chart vertex: the one a face of this chart uses there.
        origin = np.zeros(len(used), dtype=np.int64)
        origin[local.reshape(-1)] = kept[rows].reshape(-1)
        pieces.append((used, local, uv, origin))
        sizes.append(uv.max(0))
    scale, spots = _pack(np.array(sizes), padding)
    out_positions, out_triangles, out_uv, source = [], [], [], []
    base = 0
    for (used, local, uv, origin), corner in zip(pieces, spots):
        out_positions.append(spot[used])
        out_triangles.append(local + base)
        out_uv.append(uv * scale + corner + padding / 2)
        source.append(origin)
        base += len(used)
    notes = [f'unwrapped into {len(pieces)} charts ({flat_count} flattened by a straight-on view), '
             f'{base} vertices; texture use {float((np.array(sizes).prod(1) * scale * scale).sum()):.0%} of the square']
    return np.concatenate(out_positions), np.concatenate(out_triangles), np.concatenate(out_uv), np.concatenate(source), notes


def bake_colours(uvs, triangles, colours, size=1024):
    """A texture from per-vertex colours (N x 3, 0..255): every triangle is drawn into its place
    in the UV square, and the empty texels around the charts take the nearest drawn colour, so
    the seams do not show the background when the texture is filtered."""
    from PIL import Image
    from scipy import ndimage
    import HdToLegacy
    index, weights = HdToLegacy.rasterise(np.asarray(uvs, dtype=np.float64) * size, np.zeros(len(uvs)), triangles, size, size)
    hit = index >= 0
    image = np.zeros((size, size, 3))
    corner = np.asarray(colours, dtype=np.float64)[:, :3][triangles[index[hit]]]
    image[hit] = (corner * weights[hit][:, :, None]).sum(1)
    if not hit.all() and hit.any():
        nearest = ndimage.distance_transform_edt(~hit, return_distances=False, return_indices=True)
        image = image[nearest[0], nearest[1]]
    return Image.fromarray(np.clip(np.round(image), 0, 255).astype(np.uint8), 'RGB')
