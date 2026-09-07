#!/usr/bin/env python3
"""
Mandibore 5% screenshot -> 16x24.

Pencil pressure shifts create many grey levels; soft downscales read that as slime.
Flatten pressure: any non-paper mark becomes solid graphite OR solid green.
Then NEAREST/BOX fit into 16x24.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
from PIL import Image

MOD = Path(r"C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Broodmother Mutation")
SRC = Path(
    r"C:\Users\Arend\.cursor\projects\c-Users-Arend-AppData-LocalLow-Freehold-Games-CavesOfQud-Mods"
    r"\assets\c__Users_Arend_AppData_Roaming_Cursor_User_workspaceStorage_empty-window_images_Photos_fM3xDUlZH3-44f13421-19d5-4aaa-bc62-395714adbc70.png"
)
OUT = MOD / "Textures" / "Creatures" / "BroodlingMandibore_T4.png"
PREVIEW = MOD / "DesignDrafts" / "BroodlingMandibore_T4_preview.png"
REF = MOD / "DesignDrafts" / "Reference" / "Mandibore_pressure_flat.png"
W, H = 16, 24

GRAPHITE = np.array([22, 24, 18, 255], dtype=np.uint8)
LIME = np.array([160, 220, 40, 255], dtype=np.uint8)


def flatten_pressure(rgb: np.ndarray) -> np.ndarray:
    """Ignore pressure greys — binary graphite vs green vs paper."""
    r = rgb[:, :, 0].astype(np.float32)
    g = rgb[:, :, 1].astype(np.float32)
    b = rgb[:, :, 2].astype(np.float32)
    luma = (r + g + b) / 3.0
    greenness = g - np.maximum(r, b)

    # Art paper (bright). Include light pressure ghosts as MARKS not paper.
    paper = luma >= 198

    # Green colored pencil (even weak wash) — chroma, not value
    green = (~paper) & (greenness >= 2.5) & (g >= r) & (g >= b - 2)

    # Everything else that's not paper = graphite stroke (any pressure)
    graphite = (~paper) & (~green)

    out = np.zeros((*rgb.shape[:2], 4), dtype=np.uint8)
    out[graphite] = GRAPHITE
    out[green] = LIME
    return out


def strip_cursor(labels: np.ndarray) -> np.ndarray:
    """
    Cursor is the diagonal pointer in the upper-left of this screenshot.
    Clear a triangle-ish zone on the left that isn't connected to the main body.
    """
    out = labels.copy()
    h, w = out.shape[:2]
    # Hard crop: creature mass is mostly x>=12 on the 51px shot; cursor left of that
    # Keep a little margin — clear x < 11 in top 2/3 only if sparse
    fg = out[:, :, 3] > 0
    # Remove left strip that is mostly cursor (columns 0..10)
    left = 11
    out[:, :left] = 0

    # Also clear isolated speckles (cursor crumbs)
    for _ in range(2):
        fg = out[:, :, 3] > 0
        # count 4-neighbors
        n = np.zeros(fg.shape, dtype=np.uint8)
        n[1:] += fg[:-1]
        n[:-1] += fg[1:]
        n[:, 1:] += fg[:, :-1]
        n[:, :-1] += fg[:, 1:]
        alone = fg & (n == 0)
        out[alone] = 0
    return out


def fit_tile(im: Image.Image) -> Image.Image:
    bbox = im.getbbox()
    if not bbox:
        raise SystemExit("empty after flatten")
    im = im.crop(bbox)
    # 1px pad
    pad = Image.new("RGBA", (im.width + 2, im.height + 2), (0, 0, 0, 0))
    pad.paste(im, (1, 1), im)
    im = pad
    w, h = im.size
    scale = min(W / w, H / h)
    nw = max(1, int(round(w * scale)))
    nh = max(1, int(round(h * scale)))
    # Flattened already — NEAREST preserves stroke blocks; BOX if shrinking a lot
    resample = Image.Resampling.NEAREST if scale >= 0.55 else Image.Resampling.BOX
    scaled = im.resize((nw, nh), resample)
    # Re-flatten after BOX (BOX can reintroduce mid greys)
    a = np.array(scaled)
    keep = a[:, :, 3] >= 20
    green = keep & (a[:, :, 1] > a[:, :, 0] + 5) & (a[:, :, 1] > a[:, :, 2] + 5)
    graphite = keep & ~green
    flat = np.zeros_like(a)
    flat[graphite] = GRAPHITE
    flat[green] = LIME
    scaled = Image.fromarray(flat, "RGBA")

    tile = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    tile.paste(scaled, ((W - nw) // 2, (H - nh) // 2), scaled)
    return tile


def ascii(tile: Image.Image) -> str:
    a = np.array(tile)
    lines = []
    for y in range(H):
        row = []
        for x in range(W):
            if a[y, x, 3] < 16:
                row.append(".")
            elif a[y, x, 1] > a[y, x, 0] + 5:
                row.append("G")
            else:
                row.append("#")
        lines.append("".join(row))
    return "\n".join(lines)


def main() -> None:
    rgb = np.array(Image.open(SRC).convert("RGB"))
    print("src", rgb.shape[1], "x", rgb.shape[0])
    flat = strip_cursor(flatten_pressure(rgb))
    im = Image.fromarray(flat, "RGBA")
    REF.parent.mkdir(parents=True, exist_ok=True)
    im.save(REF)
    tile = fit_tile(im)
    print(ascii(tile))
    a = np.array(tile)
    op = a[:, :, 3] >= 16
    print(f"opaque={int(op.sum())} graphite={int(((op)&(a[:,:,1]<=a[:,:,0]+5)).sum())} green={int(((op)&(a[:,:,1]>a[:,:,0]+5)).sum())}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tile.save(OUT)
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    tile.resize((160, 240), Image.Resampling.NEAREST).save(PREVIEW)
    print("wrote", OUT)
    print("wrote", PREVIEW)


if __name__ == "__main__":
    main()
