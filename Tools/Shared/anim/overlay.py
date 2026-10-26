"""skeleton.png: the rig drawn over frame0.png through cam.json, vertices tinted by the bone that owns them.
The quickest way to judge a UniRig result by eye. python overlay.py <work>"""
import json, sys

import numpy as np
from PIL import Image, ImageDraw

w = sys.argv[1]
r = np.load(w + "/rig.npz", allow_pickle=True)
P = np.array(json.load(open(w + "/cam.json"))["P"])
J, par = r["joints"], r["parents"]


def proj(X):
    x = X @ P[:, :3].T + P[:, 3]
    return x[:, :2] / x[:, 2:]


im = Image.open(w + "/frame0.png").convert("RGB")
d = ImageDraw.Draw(im)
V = np.load(w + "/mesh.npz")["verts"]
vis = np.load(w + "/visible.npy")
own = r["weights"].argmax(1)
cols = np.random.default_rng(0).integers(40, 255, (len(J), 3))
for (u, v), o in zip(proj(V[vis][::2]), own[vis][::2]):
    d.point((u, v), fill=tuple(int(c) for c in cols[o]))
uv = proj(J)
for j, p in enumerate(par):
    if p >= 0:
        d.line([tuple(uv[p]), tuple(uv[j])], fill=(0, 0, 0), width=3)
for (u, v) in uv:
    d.ellipse([u - 3, v - 3, u + 3, v + 3], fill=(230, 30, 30))
im.save(w + "/skeleton.png")
print(json.dumps({"ok": True, "joints": len(J), "png": w + "/skeleton.png"}))
