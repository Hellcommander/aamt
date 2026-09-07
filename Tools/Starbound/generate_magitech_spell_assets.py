#!/usr/bin/env python3
"""
Magi-Tech spell asset helpers for the draft → reference → final pipeline.

- Samples palette from the SD quality draft (vortex_quality style)
- Stages animation frames that inherit draft colors / final look
- Writes a simple Starbound .frames file when CrossGameSpritesheet is unavailable
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageEnhance, ImageFilter


def sample_draft_palette(draft_path: Path, sample_count: int = 12) -> List[str]:
    """Dominant opaque colors from the quality draft (hex)."""
    if not draft_path.exists():
        return []
    with Image.open(draft_path) as img:
        rgba = img.convert("RGBA")
        small = rgba.resize((64, 64), Image.Resampling.BOX)
        pixels = [p for p in small.getdata() if p[3] > 32]
    if not pixels:
        return []
    quantized = [((r // 16) * 16, (g // 16) * 16, (b // 16) * 16) for r, g, b, _ in pixels]
    top = [c for c, _ in Counter(quantized).most_common(sample_count)]
    return [f"#{r:02x}{g:02x}{b:02x}" for r, g, b in top]


def write_frames_json(path: Path, tile: int, columns: int, rows: int, names: List[List[str]]) -> None:
    data = {
        "frameGrid": {
            "size": [tile, tile],
            "dimensions": [columns, rows],
            "names": names,
        }
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def stage_frames(
    final_path: Path,
    draft_path: Path,
    stage_dir: Path,
    frame_count: int,
    tile_size: int,
) -> None:
    """
    Build a simple animated strip from the referenced final.
    Motion is subtle rotation/pulse so sheets are valid; replace later with
    richer procedural/SD keyframes if needed.
    """
    stage_dir.mkdir(parents=True, exist_ok=True)
    base = Image.open(final_path).convert("RGBA")
    if base.size != (tile_size, tile_size):
        base = base.resize((tile_size, tile_size), Image.Resampling.LANCZOS)

    # Soft draft-tint overlay for color lock to the quality draft
    tint: Optional[Tuple[int, int, int]] = None
    palette = sample_draft_palette(draft_path)
    if palette:
        h = palette[0].lstrip("#")
        tint = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    cols = max(1, int(math.ceil(math.sqrt(frame_count))))
    rows = max(1, int(math.ceil(frame_count / cols)))
    names: List[List[Optional[str]]] = [[None for _ in range(cols)] for _ in range(rows)]

    for i in range(frame_count):
        t = i / max(1, frame_count - 1)
        angle = (t - 0.5) * 12.0  # subtle sway
        pulse = 1.0 + 0.06 * math.sin(t * math.pi * 2)
        frame = base.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False)
        frame = ImageEnhance.Brightness(frame).enhance(pulse)
        if tint:
            overlay = Image.new("RGBA", frame.size, (*tint, 28))
            frame = Image.alpha_composite(frame, overlay)
        frame = frame.filter(ImageFilter.SMOOTH_MORE)
        name = f"frame{i:02d}"
        out = stage_dir / f"{name}.png"
        frame.save(out)
        r, c = divmod(i, cols)
        if r < rows and c < cols:
            names[r][c] = name

    # Fill empties
    for r in range(rows):
        for c in range(cols):
            if names[r][c] is None:
                names[r][c] = names[0][0] or "frame00"

    write_frames_json(
        stage_dir / "staged.frames",
        tile_size,
        cols,
        rows,
        names,  # type: ignore[arg-type]
    )

    meta = {
        "draftPalette": palette,
        "frameCount": frame_count,
        "tileSize": tile_size,
        "draftReferenced": str(draft_path),
        "finalSource": str(final_path),
    }
    (stage_dir / "stage_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[OK] Staged {frame_count} frames in {stage_dir}")
    if palette:
        print(f"[OK] Draft palette: {', '.join(palette[:5])}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Magi-Tech draft-referenced frame staging")
    ap.add_argument("--mod-path", required=True)
    ap.add_argument("--asset-id", required=True)
    ap.add_argument("--draft", required=True)
    ap.add_argument("--final", required=True)
    ap.add_argument("--frame-count", type=int, default=8)
    ap.add_argument("--tile-size", type=int, default=64)
    ap.add_argument("--stage-frames", required=True)
    args = ap.parse_args()

    draft = Path(args.draft)
    final = Path(args.final)
    stage = Path(args.stage_frames)
    if not final.exists():
        raise SystemExit(f"Final missing: {final}")
    stage_frames(final, draft, stage, args.frame_count, args.tile_size)

    # Also drop .frames next to the final for Starbound consumers
    out_frames = Path(args.mod_path) / "assets" / "magitech" / "generated" / args.asset_id / f"{args.asset_id}.frames"
    staged = stage / "staged.frames"
    if staged.exists():
        out_frames.write_text(staged.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"[OK] Wrote {out_frames}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
