#!/usr/bin/env python3
"""Deploy Cursor-generated UN_crcc_*.png portraits into the Elin mod Portrait/ folder.

Elin unique portraits are 240x320 RGBA PNGs. Filename without extension is the portrait ID.
Uses UN_crcc_* so we never override vanilla UN_* IDs.

  python elin_deploy_portraits.py
  python elin_deploy_portraits.py --assets-dir "..." --mod-path "..."
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

CATALOG = Path(__file__).with_name("elin_asset_catalog.json")
TARGET = (240, 320)
WHITE_THRESH = 245


def whitish_to_alpha(im: Image.Image) -> Image.Image:
    """Convert near-white studio background to transparency (vanilla Elona look)."""
    rgba = im.convert("RGBA")
    px = rgba.load()
    w, h = rgba.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if r >= WHITE_THRESH and g >= WHITE_THRESH and b >= WHITE_THRESH:
                px[x, y] = (r, g, b, 0)
    return rgba


def content_bbox(im: Image.Image) -> tuple[int, int, int, int] | None:
    alpha = im.split()[-1]
    return alpha.getbbox()


def fit_portrait(src: Image.Image) -> Image.Image:
    """Crop to subject (prefer upper body), pad to 3:4, resize to 240x320."""
    im = whitish_to_alpha(src)
    box = content_bbox(im)
    if box:
        im = im.crop(box)

    tw, th = TARGET
    target_ratio = tw / th
    w, h = im.size
    ratio = w / h if h else target_ratio

    # Prefer upper portion for full-body accidental generations
    if ratio < target_ratio * 0.85:
        # too tall — take upper 3:4 of content
        new_h = int(w / target_ratio)
        if new_h < h:
            im = im.crop((0, 0, w, new_h))
            w, h = im.size
    elif ratio > target_ratio * 1.15:
        # too wide — center crop
        new_w = int(h * target_ratio)
        x0 = max(0, (w - new_w) // 2)
        im = im.crop((x0, 0, x0 + new_w, h))
        w, h = im.size

    # Pad to exact 3:4 on transparent canvas, then resize
    canvas_h = max(h, int(w / target_ratio))
    canvas_w = max(w, int(canvas_h * target_ratio))
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    ox = (canvas_w - w) // 2
    oy = max(0, (canvas_h - h) // 6)  # bias upward
    canvas.paste(im, (ox, oy), im)
    return canvas.resize(TARGET, Image.Resampling.LANCZOS)


def main() -> int:
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets-dir", type=Path, default=Path(cat["cursorAssetsDir"]))
    ap.add_argument("--mod-path", type=Path, default=Path(cat["modPath"]))
    args = ap.parse_args()

    out_dir = args.mod_path / "Portrait"
    out_dir.mkdir(parents=True, exist_ok=True)

    heroes = [h["id"] for h in cat["heroes"]]
    written = []
    missing = []
    for hid in heroes:
        name = f"UN_crcc_{hid.lower()}.png"
        src = args.assets_dir / name
        if not src.is_file():
            missing.append(name)
            continue
        dst = out_dir / name
        portrait = fit_portrait(Image.open(src))
        portrait.save(dst, optimize=True)
        written.append((name, dst.stat().st_size))

    print(f"Wrote {len(written)} portraits -> {out_dir}")
    for name, size in written:
        print(f"  {name}  {size} bytes")
    if missing:
        print(f"MISSING ({len(missing)}):")
        for m in missing:
            print(f"  {m}")
        return 1

    # Sanity: every file is 240x320 RGBA
    bad = []
    for p in sorted(out_dir.glob("UN_crcc_*.png")):
        im = Image.open(p)
        if im.size != TARGET or im.mode != "RGBA":
            bad.append((p.name, im.size, im.mode))
    if bad:
        print("BAD FORMAT:")
        for row in bad:
            print(" ", row)
        return 1
    print(f"OK: {len(written)} x {TARGET[0]}x{TARGET[1]} RGBA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
