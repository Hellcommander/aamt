#!/usr/bin/env python3
"""
Generate Soulash 2 Astral Magic asset grids:

- abilities.png
- amplifiers.png
- passive_skills.png
- skills.png
- stackers.png
- entities.png

Each grid is a packed tilesheet (e.g. 64x64 tiles) suitable for tilemap.json
and glyph indices. SD/Ollama/procedural can be plugged into tile generation
later; for now, tiles are stubbed as transparent or simple astral motifs.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Dict, Tuple

from PIL import Image, ImageDraw

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_DIR = SCRIPT_DIR.parent / "Shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

# If you later want quality gates or Ollama/SD, you can mirror hydromancy_quality here.
TILE_SIZE = 64  # astral looks good at 64x64

GRID_DEFS: Dict[str, Dict[str, object]] = {
    "abilities":   {"file": "abilities.png",      "cols": 8, "count": 32},
    "amplifiers":  {"file": "amplifiers.png",     "cols": 8, "count": 32},
    "passives":    {"file": "passive_skills.png", "cols": 8, "count": 32},
    "skills":      {"file": "skills.png",         "cols": 8, "count": 32},
    "stackers":    {"file": "stackers.png",       "cols": 8, "count": 32},
    "entities":    {"file": "entities.png",       "cols": 8, "count": 32},
}

ASTRAL_BG = (10, 8, 24, 255)
ASTRAL_ACCENT = (120, 200, 255, 255)
ASTRAL_CORE = (180, 230, 255, 255)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Soulash 2 Astral Magic asset grid generator")
    p.add_argument(
        "--mod-path",
        type=Path,
        default=Path(r"E:\SteamLibrary\steamapps\common\Soulash 2\data\mods\arendeth_astral_magic"),
    )
    p.add_argument(
        "--mode",
        choices=["procedural", "sd", "ollama", "all"],
        default="procedural",
        help="Tile generation mode (pipeline hook; currently only procedural is implemented).",
    )
    p.add_argument(
        "--quality",
        choices=["fast", "mechanical", "full"],
        default="mechanical",
    )
    p.add_argument(
        "--grids",
        default="abilities,amplifiers,passives,skills,stackers,entities",
        help="Comma-separated list of grids to generate.",
    )
    p.add_argument("--use-sd", action="store_true")
    p.add_argument("--sd-drafts-dir", type=Path, default=None)
    p.add_argument("--sd-draft-icon", type=Path, default=None)
    p.add_argument("--sd-draft-thumbnail", type=Path, default=None)
    return p.parse_args()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def draw_astral_motif(tile: Image.Image, seed: int = 0) -> None:
    """Simple astral wisp / spark motif stub so tiles aren't just blank."""
    random.seed(seed)
    w, h = tile.size
    draw = ImageDraw.Draw(tile)

    # Background glow
    cx = w / 2 + random.randint(-4, 4)
    cy = h / 2 + random.randint(-4, 4)
    r_outer = w * 0.42
    r_inner = w * 0.22

    for i in range(4):
        r = r_outer * (0.4 + i * 0.12)
        alpha = int(60 + i * 30)
        color = (ASTRAL_ACCENT[0], ASTRAL_ACCENT[1], ASTRAL_ACCENT[2], alpha)
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color, width=2)

    # Core spark
    draw.ellipse(
        (cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner),
        fill=ASTRAL_CORE,
    )

    # Small directional streaks
    for _ in range(5):
        dx = random.uniform(-r_outer * 0.6, r_outer * 0.6)
        dy = random.uniform(-r_outer * 0.6, r_outer * 0.6)
        x1 = cx + dx * 0.4
        y1 = cy + dy * 0.4
        x2 = cx + dx
        y2 = cy + dy
        draw.line((x1, y1, x2, y2), fill=ASTRAL_ACCENT, width=1)


def generate_tile(grid_name: str, index: int, mode: str) -> Image.Image:
    """
    Stub tile generator. Later you can branch on mode:
    - procedural: draw_astral_motif
    - sd: crop from SD drafts
    - ollama: use design spec + procedural
    """
    tile = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
    # For now, all grids share the same astral motif style; you can specialize per-grid later.
    draw_astral_motif(tile, seed=index + hash(grid_name) % 9973)
    return tile


def pack_grid(mod_path: Path, grid_name: str, mode: str) -> Path:
    grid_def = GRID_DEFS[grid_name]
    out_dir = mod_path / "tiles"
    ensure_dir(out_dir)

    count = int(grid_def["count"])
    cols = int(grid_def["cols"])
    rows = (count + cols - 1) // cols

    sheet = Image.new("RGBA", (cols * TILE_SIZE, rows * TILE_SIZE), ASTRAL_BG)

    for idx in range(count):
        tile = generate_tile(grid_name, idx, mode)
        x = (idx % cols) * TILE_SIZE
        y = (idx // cols) * TILE_SIZE
        sheet.paste(tile, (x, y), tile)

    out_path = out_dir / str(grid_def["file"])
    sheet.save(out_path, "PNG")
    print(f"  [OK] {grid_name} → {out_path}")
    return out_path


def main() -> int:
    args = parse_args()
    mod_path = args.mod_path.resolve()

    grids = [g.strip() for g in args.grids.split(",") if g.strip()]
    print(f"Astral Magic asset grids for mod: {mod_path}")
    print(f"  Mode:    {args.mode}")
    print(f"  Quality: {args.quality}")
    print(f"  Grids:   {', '.join(grids)}")
    print("")

    for grid in grids:
        if grid not in GRID_DEFS:
            print(f"  [WARN] Unknown grid '{grid}', skipping")
            continue
        pack_grid(mod_path, grid, args.mode)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
