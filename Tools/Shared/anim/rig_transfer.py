"""UniRig's skeleton and skin (on its own extracted copy of the mesh) -> rig.npz on mesh.npz's vertices.
Runs in the animation venv: python rig_transfer.py <work>

UniRig may hand back its copy rescaled, recentred or Y-up; the map back is found by trying the axis conventions and
fitting scale + offset to the bounding boxes, keeping the one whose points sit closest to ours. Each of our vertices
then takes the inverse-distance blend of its nearest UniRig vertices' weights, smoothed once over the mesh so seams
(vertices split for UVs) and noisy patches move together.
"""
import json, sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

work = Path(sys.argv[1])
mesh = np.load(work / "mesh.npz")
V, F = mesh["verts"].astype(np.float64), mesh["faces"]
full = sorted(work.rglob("predict_skin_full.npz"), key=lambda p: p.stat().st_mtime)  # UniRig writes beside its input
if not full:
    raise SystemExit("no predict_skin_full.npz under " + str(work))
u = np.load(full[-1])
UV, S, J, T, par = u["vertices"].astype(np.float64), u["skin"].astype(np.float64), u["joints"].astype(np.float64), u["tails"].astype(np.float64), u["parents"].astype(int)
names = None
sk = sorted(work.rglob("predict_skeleton.npz"), key=lambda p: p.stat().st_mtime)
if sk:
    try:
        n = np.load(sk[-1], allow_pickle=True).get("names")
        names = [str(x) for x in n] if n is not None and len(n) == len(J) else None
    except Exception:
        names = None

AXES = {"same": np.eye(3), "yup": np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float), "yup_neg": np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)}
tree = cKDTree(V)
best = None
for name, M in AXES.items():
    P = UV @ M.T
    lo, hi, vlo, vhi = P.min(0), P.max(0), V.min(0), V.max(0)
    s = float(np.ptp(V, 0).max() / max(np.ptp(P, 0).max(), 1e-9))
    off = (vlo + vhi) / 2 - s * (lo + hi) / 2
    d, _ = tree.query(P * s + off)
    err = float(np.median(d))
    if best is None or err < best[0]:
        best = (err, name, M, s, off)
err, axis, M, s, off = best
to_ours = lambda X: (X @ M.T) * s + off  # noqa: E731
UVo, Jo, To = to_ours(UV), to_ours(J), to_ours(T)

k = 6
d, idx = cKDTree(UVo).query(V, k=k)
w = 1.0 / np.maximum(d, 1e-5) ** 2
w /= w.sum(1, keepdims=True)
W = (S[idx] * w[..., None]).sum(1)
# one pass of neighbour averaging over the triangles, then welded positions share weights
nbr_sum = np.zeros_like(W)
cnt = np.zeros(len(V))
for a, b in ((0, 1), (1, 2), (2, 0)):
    np.add.at(nbr_sum, F[:, a], W[F[:, b]])
    np.add.at(cnt, F[:, a], 1)
W = 0.5 * W + 0.5 * nbr_sum / np.maximum(cnt, 1)[:, None]
key = np.round(V / 1e-5).astype(np.int64)
_, inv = np.unique(key, axis=0, return_inverse=True)
inv = inv.reshape(-1)
acc = np.zeros((inv.max() + 1, W.shape[1]))
np.add.at(acc, inv, W)
W = acc[inv]
W[W < 0.01] = 0
W /= np.maximum(W.sum(1, keepdims=True), 1e-9)
orphans = W.sum(1) < 0.5
if orphans.any():  # nothing nearby: the closest joint takes it
    W[orphans] = 0
    W[orphans, cKDTree(Jo).query(V[orphans])[1]] = 1

safe = names or [f"bone_{i:02d}" for i in range(len(Jo))]
seen = {}
for i, n in enumerate(safe):
    n = "".join(c if c.isalnum() or c in "_-." else "_" for c in n) or f"bone_{i:02d}"
    if n in seen:
        n = f"{n}_{i}"
    seen[n] = i
    safe[i] = n
np.savez(work / "rig.npz", joints=Jo.astype(np.float32), tails=To.astype(np.float32), parents=par, names=np.array(safe),
         weights=W.astype(np.float32))
roots = int((par < 0).sum())
print(json.dumps({"ok": True, "joints": len(Jo), "roots": roots, "axis": axis, "scale": round(s, 4), "match_err": round(err, 5),
                  "unirig_vertices": len(UV), "vertices": len(V), "orphans": int(orphans.sum())}))
