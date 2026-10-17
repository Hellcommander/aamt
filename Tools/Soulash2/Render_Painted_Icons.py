#!/usr/bin/env python3
"""
Render_Painted_Icons.py - remake a Soulash 2 mod's skill icons in the painted, framed style (the Cosmic Magic look).

Why: shrinking SD art to a 32px pixel grid loses the detail that makes the good icons good. This tool keeps the painting, puts it on
the same dark vignette and gives it the thin framed border the best tiles in the game use, at 128px cells.

Inputs are the raw Stable Diffusion images the icon generators already cache (Output/Soulash2/<mod>_assets/raw for emblems on a
black background, raw_scene for full-scene tiles). Output sheets keep the mod's own sheet geometry (cols x rows from assets.json);
only the pixel size of the cells changes, which the game derives from the png.

usage:
  python Render_Painted_Icons.py <mod_id|mod_path> [--keep abilities:0,3,7 --keep passives:1] [--cell 128] [--apply]
    --keep   tiles of the existing sheet to leave untouched (art you already like)
    --apply  copy the rendered sheets into the mod (default: staged in Output/Soulash2/<mod>_assets/assets_painted)
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance

TOOLS = Path(__file__).resolve().parent.parent
STAGE = TOOLS / "Output" / "Soulash2"
MODS = Path(r"E:\SteamLibrary\steamapps\common\Soulash 2\data\mods")
SHEET_FILES = {"abilities": "abilities.png", "passives": "passive_skills.png", "amplifiers": "amplifiers.png",
               "stackers": "stackers.png", "skills": "skills.png"}
SHEET_NAMES = {"abilities": "abilities", "passives": "passive_skills", "amplifiers": "amplifiers", "stackers": "stackers", "skills": "skills"}
RAW_RE = re.compile(r"^(?:.*_)?(abilities|passives|amplifiers|stackers|skills)_(\d+)_[0-9a-f]{8}_(\d)\.png$")


def knock_out_light_background(raw: Image.Image) -> Image.Image:
    """some SD tiles came out on white or grey instead of black: flood the light region that touches the edge to black"""
    im = raw.convert("RGB").copy()
    w, h = im.size
    for xy in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)):
        if sum(im.getpixel(xy)) / 3 > 150:
            ImageDraw.floodfill(im, xy, (0, 0, 0), thresh=70)
    return im


def emblem_tile(raw: Image.Image, cell: int) -> Image.Image:
    """an emblem on black -> a full-bleed tile: the subject fills the frame and is screened over a vignette tinted by its own hue"""
    raw = knock_out_light_background(raw)
    a = np.asarray(raw.convert("RGB"), dtype=np.float32) / 255.0
    mask = a.max(axis=2) > 0.12
    if mask.sum() < 40:
        crop = raw.convert("RGB")
    else:
        ys, xs = np.where(mask)
        pad = int(0.04 * raw.width)
        x0, x1 = max(0, xs.min() - pad), min(raw.width, xs.max() + pad)
        y0, y1 = max(0, ys.min() - pad), min(raw.height, ys.max() + pad)
        side = max(x1 - x0, y1 - y0)
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        crop = raw.convert("RGB").crop((cx - side // 2, cy - side // 2, cx + side // 2, cy + side // 2))
    crop = crop.resize((cell, cell), Image.Resampling.LANCZOS)
    e = np.asarray(crop, dtype=np.float32) / 255.0
    w = e.max(axis=2, keepdims=True)
    mean = (e * w).sum(axis=(0, 1)) / max(1e-4, w.sum())
    mean = mean / max(1e-4, mean.max())
    yy, xx = np.mgrid[0:cell, 0:cell].astype(np.float32) / (cell - 1)
    r = np.clip(np.sqrt((xx - 0.5) ** 2 + (yy - 0.5) ** 2) / 0.7071, 0, 1)
    vign = (0.20 * (1 - r) ** 1.4 + 0.03)[..., None]
    bg = np.clip(mean[None, None, :] * (vign + (0.04 + 0.05 * yy)[..., None]), 0, 1)
    out = 1 - (1 - bg) * (1 - e)
    img = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), "RGB")
    img = ImageEnhance.Contrast(img).enhance(1.12)
    return ImageEnhance.Color(img).enhance(1.15)


def scene_tile(raw: Image.Image, cell: int) -> Image.Image:
    im = raw.convert("RGB").copy()
    w0, h0 = im.size
    edge = [im.getpixel(p) for p in ((0, 0), (w0 - 1, 0), (0, h0 - 1), (w0 - 1, h0 - 1))]
    if sum(sum(c) / 3 for c in edge) / 4 > 150:               # light backdrop: darken it
        for xy in ((0, 0), (w0 - 1, 0), (0, h0 - 1), (w0 - 1, h0 - 1), (w0 // 2, 0), (w0 // 2, h0 - 1), (0, h0 // 2), (w0 - 1, h0 // 2)):
            if sum(im.getpixel(xy)) / 3 > 150:
                ImageDraw.floodfill(im, xy, (14, 18, 16), thresh=60)
    w, h = im.size
    s = min(w, h)
    im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s)).resize((cell, cell), Image.Resampling.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    yy, xx = np.mgrid[0:cell, 0:cell].astype(np.float32) / (cell - 1)
    r = np.clip(np.sqrt((xx - .5) ** 2 + (yy - .5) ** 2) / .7071, 0, 1)
    a *= (1 - 0.35 * r ** 2)[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


def drop_template_grey(tile: Image.Image) -> Image.Image:
    """older tiles were painted onto the sheet template's grey square (157,148,163 with a 117,108,123 rim): swap that for a dark
    vignette so kept tiles sit with the new ones"""
    a = np.asarray(tile.convert("RGB")).astype(np.int32)
    k = max(5, int(a.shape[0] * 0.075))        # past any frame an earlier pass drew
    c = a[k:k + 3, k:k + 3].reshape(-1, 3).mean(axis=0)
    if not (abs(c[0] - 157) < 22 and abs(c[1] - 148) < 22 and abs(c[2] - 163) < 22):
        return tile
    def near(col, tol):
        return (np.abs(a - np.array(col)).max(axis=2) < tol)
    mask = near((157, 148, 163), 26) | near((117, 108, 123), 26)
    h, w = mask.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32) / (max(h, w) - 1)
    r = np.clip(np.sqrt((xx - .5) ** 2 + (yy - .5) ** 2) / .7071, 0, 1)
    base = np.stack([14 + 10 * (1 - r), 16 + 12 * (1 - r), 22 + 18 * (1 - r)], axis=2)
    out = np.where(mask[..., None], base, a)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def framed(tile: Image.Image, cell: int) -> Image.Image:
    a = np.asarray(tile.convert("RGB")).astype(np.float32)
    lit = a.max(axis=2) > 110
    hue = a[lit].mean(axis=0) if lit.any() else np.array([160, 120, 220], dtype=np.float32)
    hue = np.clip(hue / max(1.0, hue.max()) * 235, 0, 255)
    d = ImageDraw.Draw(tile)
    t = max(2, cell // 40)
    d.rectangle((0, 0, cell - 1, cell - 1), outline=tuple(int(c * 0.30) for c in hue), width=t)
    d.rectangle((t, t, cell - 1 - t, cell - 1 - t), outline=tuple(int(c * 0.85) for c in hue), width=1)
    return tile


def collect(raw_dir: Path) -> dict:
    found = {}
    if not raw_dir.exists():
        return found
    for f in raw_dir.glob("*.png"):
        m = RAW_RE.match(f.name)
        if not m:
            continue
        key = (m.group(1), int(m.group(2)))
        im = np.asarray(Image.open(f).convert("L").resize((64, 64)), dtype=np.float32) / 255.0
        border = float(np.concatenate([im[0], im[-1], im[:, 0], im[:, -1]]).mean())
        if key not in found or border < found[key][1]:
            found[key] = (f, border)
    return found


def render(mod_dir: Path, mod: str, cell: int, keep: set[tuple[str, int]]) -> Path:
    st = STAGE / f"{mod}_assets"
    out = st / "assets_painted"
    out.mkdir(parents=True, exist_ok=True)
    sheets = {s["name"]: s for s in json.load(open(mod_dir / "assets.json", encoding="utf-8-sig"))["graphics"]["tilesheets"]}
    emblem = collect(st / "raw")
    scene = collect(st / "raw_scene")
    for grid, fname in SHEET_FILES.items():
        sh = sheets.get(SHEET_NAMES[grid])
        if not sh:
            continue
        cols, rows = sh["tiles"]
        if grid == "skills":
            key = (grid, 0)
            if key in scene or key in emblem:
                t = scene_tile(Image.open(scene[key][0]), 512) if key in scene else emblem_tile(Image.open(emblem[key][0]), 512)
                framed(t, 512).save(out / fname)
            continue
        existing = Image.open(mod_dir / sh["file"]).convert("RGBA") if (mod_dir / sh["file"]).exists() else None
        sheet = Image.new("RGBA", (cols * cell, rows * cell), (0, 0, 0, 0))
        if existing is not None and keep:           # carry the tiles you want to keep over, scaled to the new cell size
            ecell = existing.width // cols
            for (g, idx) in keep:
                if g != grid or idx >= cols * rows:
                    continue
                x, y = (idx % cols) * ecell, (rows - 1 - idx // cols) * ecell
                t = existing.crop((x, y, x + ecell, y + ecell)).resize((cell, cell), Image.Resampling.LANCZOS)
                t = framed(drop_template_grey(t.convert("RGB")), cell).convert("RGBA")
                sheet.paste(t, ((idx % cols) * cell, (rows - 1 - idx // cols) * cell))
        n = 0
        for k in sorted({k for k in list(emblem) + list(scene) if k[0] == grid}, key=lambda k: k[1]):
            if k in keep or k[1] >= cols * rows:
                continue
            t = scene_tile(Image.open(scene[k][0]), cell) if k in scene else emblem_tile(Image.open(emblem[k][0]), cell)
            t = framed(t, cell).convert("RGBA")
            sheet.paste(t, ((k[1] % cols) * cell, (rows - 1 - k[1] // cols) * cell))
            n += 1
        if n or keep:
            sheet.save(out / fname)
        print(f"  {mod[8:]:18} {grid:11} {n} tiles rendered, {sum(1 for g, _ in keep if g == grid)} kept")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mod")
    ap.add_argument("--keep", action="append", default=[], help="sheet:idx,idx  (e.g. abilities:0,3,7)")
    ap.add_argument("--cell", type=int, default=128)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    p = Path(a.mod)
    mod_dir = p if p.exists() else MODS / (a.mod if a.mod.startswith("arendeth_") else "arendeth_" + a.mod)
    mod = mod_dir.name
    keep: set[tuple[str, int]] = set()
    for spec in a.keep:
        sheet, _, idxs = spec.partition(":")
        for i in idxs.split(","):
            if i.strip():
                keep.add((sheet.strip(), int(i)))
    out = render(mod_dir, mod, a.cell, keep)
    if a.apply:
        for f in out.glob("*.png"):
            shutil.copy2(f, mod_dir / "assets" / f.name)
            print("  applied", f.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
