"""Split one piece of detailed character art into a layered CYF portrait.

Arendeth_CYFTiles (CYFPortrait.cs) shows the portrait on the character sheet and stacks
these layers by the same rule as the player's layered tile: a portrait layer with
Follow="head2" is drawn only while the tile shows its head2 layer, "!head2" only while it
does not, "glow_eyes,head2" only while both are shown. So the portrait loses a head, its
horns or the brood sack when the character does.

Input is a spec JSON (paths relative to it):

  {
    "fighter": "rhomustos",
    "source": "rhomustos_portrait_src.webp",
    "crop": [x0, y0, x1, y1],                      # output canvas, in source pixels
    "background": {"color": [r, g, b], "soft": [25, 55]},   # colour distance: 0 alpha .. 1 alpha
    "horns":  [{"file": "horns.png", "follow": "horns", "box": [x0,y0,x1,y1],
                "dome": [cx, cy, rx, ry]}],        # head top under the horn: refilled, outline redrawn
    "eyes":   [{"file": "glow1.png", "follow": "glow_eyes", "box": [x0,y0,x1,y1]}],
    "cuts":   [{"file": "head2.png", "follow": "head2", "poly": [[x,y],...],
                "stump": {"file": "stump2.png", "follow": "!head2"}}],
    "sacks":  [{"file": "brood.png", "follow": "brood", "poly": [[x,y],...]}],
    "order":  ["brood.png", "head2.png", "base.png", ...]   # draw order, back to front
  }

  horns  bone-coloured pixels in the box (and their outline) become the layer; the base gets
         the scalp refilled inside the dome ellipse and transparency outside it
  eyes   bright yellow-white pixels in the box become a glow layer; the base gets dark sockets
  cuts   everything inside the polygon becomes the layer (drawn behind the base); the optional
         stump layer is an outline along the cut, shown when the cut part is not
  sacks  non-green, non-magenta pixels inside the polygon (plus the slime and outline they
         enclose) become the layer, drawn behind the base

Writes <out>/Textures/Portraits/<fighter>/<file> for every layer plus base.png and
portrait.xml, and previews (all layers, and each optional part removed) to --preview.

  python cyf_portrait_layers.py <spec.json> <out_dir> [--preview DIR]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List
from xml.sax.saxutils import quoteattr

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

OUTLINE = np.array([14, 18, 16], dtype=np.float32)
SOCKET = np.array([34, 40, 18], dtype=np.float32)


def lum(a: np.ndarray) -> np.ndarray:
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def poly_mask(shape, pts) -> np.ndarray:
    im = Image.new("L", (shape[1], shape[0]), 0)
    ImageDraw.Draw(im).polygon([tuple(p) for p in pts], fill=255)
    return np.asarray(im) > 0


def box_mask(shape, box) -> np.ndarray:
    m = np.zeros(shape, bool)
    x0, y0, x1, y1 = box
    m[y0:y1, x0:x1] = True
    return m


def near(mask: np.ndarray, r: int) -> np.ndarray:
    return ndimage.binary_dilation(mask, iterations=r) if mask.any() else mask


class Split:
    def __init__(self, rgb: np.ndarray, alpha: np.ndarray):
        self.orig = rgb.copy()
        self.rgb = rgb          # the base, edited as parts are lifted out
        self.alpha = alpha
        self.layers: Dict[str, np.ndarray] = {}   # file -> RGBA float
        self.follow: Dict[str, str] = {}

    def add(self, file: str, follow: str, rgb: np.ndarray, alpha: np.ndarray) -> None:
        out = np.zeros(rgb.shape[:2] + (4,), np.float32)
        out[..., :3] = rgb
        out[..., 3] = alpha
        if file in self.layers:  # several parts into one file
            prev = self.layers[file]
            keep = prev[..., 3] >= out[..., 3]
            out[keep] = prev[keep]
        self.layers[file] = out
        self.follow[file] = follow

    def horn(self, spec: Dict) -> None:
        a = self.orig
        box = box_mask(a.shape[:2], spec["box"])
        mx, mn = a.max(2), a.min(2)
        r, g, b = a[..., 0], a[..., 1], a[..., 2]
        # Bone: pale and unsaturated, not green (the scalp), shaded parts included.
        bone = box & (lum(a) > 95) & ((mx - mn) < 75) & (r >= g - 12) & (b <= r + 10) & (self.alpha > 0.5)
        bone = ndimage.binary_opening(bone, iterations=1)
        lab, n = ndimage.label(bone)
        if n:  # the horn is the biggest bone-coloured blob in the box
            sizes = ndimage.sum(bone, lab, range(1, n + 1))
            bone = lab == (1 + int(np.argmax(sizes)))
        dark = box & (lum(a) < 80) & (self.alpha > 0.2)
        horn = bone | (near(bone, 4) & dark)
        horn = ndimage.binary_fill_holes(horn)
        self.add(spec["file"], spec["follow"], self.orig, self.alpha * horn)

        cx, cy, rx, ry = spec["dome"]
        yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
        d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
        # Refill a little wider than the horn so its base shading does not stay as a smudge.
        wide = near(horn, 3) & box
        inside = wide & (d < 0.965)
        ring = horn & (d >= 0.965) & (d < 1.035)
        outside = horn & (d >= 1.035)
        donor = (~wide) & (d < 0.95) & (self.alpha > 0.9) & (lum(a) > 70)
        if inside.any() and donor.any():
            _, idx = ndimage.distance_transform_edt(~donor, return_indices=True)
            fill = self.rgb[idx[0], idx[1]]
            soft = ndimage.uniform_filter(fill, size=(5, 5, 1))
            self.rgb[inside] = soft[inside]
            self.alpha[inside] = 1.0
        self.rgb[ring] = OUTLINE
        self.alpha[ring] = 1.0
        self.alpha[outside] = 0.0

    def eyes(self, spec: Dict) -> None:
        a = self.orig
        box = box_mask(a.shape[:2], spec["box"])
        r, g, b = a[..., 0], a[..., 1], a[..., 2]
        # Yellow-white eye glow; pale-green skin highlights have red well below green.
        core = box & (r > 205) & (g > 200) & (b > 110) & (np.abs(r - g) < 45)
        core = ndimage.binary_opening(core, iterations=1) | (core & near(core, 1))
        halo = near(core, 2) & box & (lum(a) > 120) & (r > g - 30)
        glow = core | halo
        self.add(spec["file"], spec["follow"], self.orig, self.alpha * glow)
        self.rgb[glow] = SOCKET

    def cut(self, spec: Dict) -> None:
        part = poly_mask(self.alpha.shape, spec["poly"]) & (self.alpha > 0)
        self.add(spec["file"], spec["follow"], self.rgb.copy(), self.alpha * part)
        self.alpha[part] = 0.0
        st = spec.get("stump")
        if st:
            edge = near(part, 3) & ~part & (self.alpha > 0.5)
            out = np.broadcast_to(OUTLINE, self.rgb.shape).copy()
            self.add(st["file"], st["follow"], out, edge.astype(np.float32))

    def sack(self, spec: Dict) -> None:
        """Everything inside the polygon (traced along the body parts in front of it), except
        magenta parts in front (a shoulder patch) and the outlines of what stays in the base."""
        a = self.orig
        region = poly_mask(self.alpha.shape, spec["poly"]) & (self.alpha > 0.02)
        r, g, b = a[..., 0], a[..., 1], a[..., 2]
        front = region & (b > g + 50) & (r > 110)
        front = ndimage.binary_opening(front, iterations=1)
        front = ndimage.binary_fill_holes(near(front, 2)) & region
        rest = (self.alpha > 0.5) & ~region
        dark = lum(a) < 70
        keep = front | (region & dark & near(front | rest, 3))
        sack = region & ~keep
        self.add(spec["file"], spec["follow"], self.rgb.copy(), self.alpha * sack)
        self.alpha[sack] = 0.0


def follows(follow: str, shown: set) -> bool:
    for term in [t.strip() for t in follow.split(",") if t.strip()]:
        neg = term.startswith("!")
        on = term[1:] in shown if neg else term in shown
        if on == neg:
            return False
    return True


def composite(layers: Dict[str, np.ndarray], order: List[str], follow: Dict[str, str], shown: set) -> Image.Image:
    h, w = next(iter(layers.values())).shape[:2]
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for f in order:
        if f != "base.png" and not follows(follow.get(f, ""), shown):
            continue
        out.alpha_composite(to_image(layers[f]))
    return out


def to_image(l: np.ndarray) -> Image.Image:
    a = np.clip(l, 0, 255)
    a[..., 3] = np.clip(l[..., 3], 0, 1) * 255
    a[a[..., 3] < 1] = 0  # no colour under clear pixels: smaller files, no fringe when scaled
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def bbox(l: np.ndarray):
    ys, xs = np.nonzero(l[..., 3] > 0.004)
    if len(xs) == 0:
        return 0, 0, 1, 1
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--preview", type=Path, default=None)
    a = ap.parse_args()

    spec = json.loads(a.spec.read_text(encoding="utf-8"))
    src = Image.open(a.spec.parent / spec["source"]).convert("RGB")
    rgb = np.asarray(src).astype(np.float32)
    bg = spec["background"]
    d = np.abs(rgb - np.array(bg["color"], np.float32)).sum(2)
    lo, hi = bg.get("soft", [25, 55])
    alpha = np.clip((d - lo) / max(1, hi - lo), 0, 1)
    # Keep only what is joined to the figure: speckles in the background drop out.
    lab, n = ndimage.label(alpha > 0.5)
    if n:
        sizes = ndimage.sum(alpha > 0.5, lab, range(1, n + 1))
        keep = np.isin(lab, 1 + np.flatnonzero(sizes >= 400))
        alpha = alpha * near(keep, 2)

    s = Split(rgb, alpha)
    for h in spec.get("horns", []):
        s.horn(h)
    for e in spec.get("eyes", []):
        s.eyes(e)
    for c in spec.get("cuts", []):
        s.cut(c)
    for k in spec.get("sacks", []):
        s.sack(k)
    s.add("base.png", "", s.rgb, s.alpha)
    # Specks left by the cuts (stray outline pixels) are dropped from every layer.
    for l in s.layers.values():
        solid = l[..., 3] > 0.3
        lab, n = ndimage.label(solid)
        if n:
            sizes = ndimage.sum(solid, lab, range(1, n + 1))
            small = np.isin(lab, 1 + np.flatnonzero(sizes < 25))
            l[..., 3][near(small, 1) & ~near(solid & ~small, 1)] = 0.0

    x0, y0, x1, y1 = spec.get("crop") or [0, 0, src.width, src.height]
    layers = {f: l[y0:y1, x0:x1] for f, l in s.layers.items()}
    order = spec.get("order") or (["base.png"] + [f for f in layers if f != "base.png"])
    missing = [f for f in layers if f not in order]
    if missing:
        raise SystemExit(f"order is missing {missing}")

    fid = spec["fighter"]
    dst = a.out_dir / "Textures" / "Portraits" / fid
    dst.mkdir(parents=True, exist_ok=True)
    boxes = {}
    for f, l in layers.items():
        bx = bbox(l)  # each layer is stored cropped; X/Y place it on the canvas (top-left origin)
        boxes[f] = bx
        to_image(l[bx[1]:bx[3], bx[0]:bx[2]]).save(dst / f, optimize=True)
    xml = ['<?xml version="1.0" encoding="utf-8"?>',
           f'<portrait Fighter={quoteattr(fid)} Width="{x1 - x0}" Height="{y1 - y0}">']
    for f in order:
        fol = s.follow.get(f, "")
        xml.append(f'  <layer File={quoteattr(f)} X="{boxes[f][0]}" Y="{boxes[f][1]}"'
                   + (f" Follow={quoteattr(fol)}" if fol else "") + " />")
    xml.append("</portrait>")
    (dst / "portrait.xml").write_text("\n".join(xml) + "\n", encoding="utf-8")
    print(f"{len(layers)} layers -> {dst}")

    if a.preview:
        a.preview.mkdir(parents=True, exist_ok=True)
        terms = sorted({t.lstrip("!") for f in s.follow.values() for t in f.split(",") if t.strip()})
        everything = set(terms)
        shots = [("all", everything)] + [(f"no_{t}", everything - {t}) for t in terms]
        bgc = tuple(bg["color"]) + (255,)
        tiles = []
        for name, shown in shots:
            im = composite(layers, order, s.follow, shown)
            im.save(a.preview / f"{fid}_portrait_{name}.png")
            flat = Image.new("RGBA", im.size, bgc)
            flat.alpha_composite(im)
            tiles.append((name, flat))
        tw, th = tiles[0][1].size
        sc = 0.3
        sheet = Image.new("RGBA", (int(tw * sc) * len(tiles), int(th * sc) + 18), (20, 24, 28, 255))
        dr = ImageDraw.Draw(sheet)
        for i, (name, im) in enumerate(tiles):
            sheet.paste(im.resize((int(tw * sc), int(th * sc)), Image.Resampling.LANCZOS), (i * int(tw * sc), 18))
            dr.text((i * int(tw * sc) + 4, 3), name, fill=(230, 230, 230, 255))
        sheet.save(a.preview / f"{fid}_portrait_sheet.png")
        print(f"previews -> {a.preview}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
