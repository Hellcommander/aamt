#!/usr/bin/env python3
"""Sheet assembler for blender_tx_facings.py frames -> engine-correct Transcendence rotation sheet.

Engine rules (see tx_image_tester.py R1-R5):
  - frame r sits COLUMN-major: x = (r // framesPerColumn) * cell, y = (r % framesPerColumn) * cell
  - frame 0 = nose up, frames turn clockwise (the renderer already writes them that way)
  - JPG colour + separate 8-bit (L) mask BMP, like vanilla

  python tx_build_facings.py --frames <dir with f000.png..> --out <dir> --id scEvolvedViper
         [--cell 128] [--columns 12] [--quality 95] [--unid "&rsEvolvedViper;"]

Writes <out>/<id>.jpg, <out>/<id>Mask.bmp and <out>/<id>.image.xml (resource + ShipClass <Image> snippets).
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image


def load_frames(frames_dir: Path) -> list[Path]:
    frames = sorted(frames_dir.glob("f[0-9][0-9][0-9].png"))
    if not frames:
        raise SystemExit(f"no f###.png frames in {frames_dir}")
    for i, p in enumerate(frames):
        if p.stem != f"f{i:03d}":
            raise SystemExit(f"frame sequence broken at {p.name} (expected f{i:03d}.png)")
    return frames


def build(frames_dir: Path, out_dir: Path, asset_id: str, cell: int, columns: int, quality: int, unid: str | None) -> dict:
    frames = load_frames(frames_dir)
    n = len(frames)
    fpc = math.ceil(n / columns)                     # frames per column (engine R1)
    sheet_w, sheet_h = columns * cell, fpc * cell
    color = Image.new("RGB", (sheet_w, sheet_h), (0, 0, 0))
    mask = Image.new("L", (sheet_w, sheet_h), 0)
    for r, p in enumerate(frames):
        im = Image.open(p).convert("RGBA")
        if im.size != (cell, cell):
            im = im.resize((cell, cell), Image.LANCZOS)
        x, y = (r // fpc) * cell, (r % fpc) * cell   # column-major (engine R2)
        alpha = im.getchannel("A")
        black = Image.new("RGB", im.size, (0, 0, 0))
        color.paste(Image.composite(im.convert("RGB"), black, alpha), (x, y))
        mask.paste(alpha, (x, y))
    out_dir.mkdir(parents=True, exist_ok=True)
    jpg, bmp = out_dir / f"{asset_id}.jpg", out_dir / f"{asset_id}Mask.bmp"
    color.save(jpg, quality=quality, subsampling=0)
    mask.save(bmp)                                   # mode L = 8-bit, as vanilla (R5)
    rs = unid or f"&rs{asset_id[2:] if asset_id.startswith('sc') else asset_id};"
    xml = (f'<!-- {asset_id}: {n} facings, {cell}px cells, {columns} columns x {fpc} rows (column-major, frame 0 nose up, clockwise) -->\n'
           f'<Image UNID="{rs}" bitmap="{jpg.name}" bitmask="{bmp.name}" loadOnUse="true" />\n\n'
           f'<!-- in the ShipClass: -->\n'
           f'<Image imageID="{rs}" imageWidth="{cell}" imageHeight="{cell}" rotationCount="{n}" rotationColumns="{columns}"/>\n')
    (out_dir / f"{asset_id}.image.xml").write_text(xml, encoding="utf-8")
    return {"id": asset_id, "frames": n, "cell": cell, "columns": columns, "rows": fpc, "sheet": [sheet_w, sheet_h],
            "jpg": str(jpg), "mask": str(bmp)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--frames", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--cell", type=int, default=128)
    ap.add_argument("--columns", type=int, default=12)
    ap.add_argument("--quality", type=int, default=95)
    ap.add_argument("--unid")
    a = ap.parse_args(argv)
    r = build(a.frames, a.out, a.id, a.cell, a.columns, a.quality, a.unid)
    print(f"[facings] {r['id']}: {r['frames']} frames -> {r['sheet'][0]}x{r['sheet'][1]} ({r['columns']}x{r['rows']} @ {r['cell']}px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
