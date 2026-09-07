#!/usr/bin/env python3
"""Generate collision hitboxes from Magi-Tech mech/minion spritesheets."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from libs.hitbox_generator import HitboxGenerator, write_hitbox_json


def _tile_from_frames(frames_path: Path) -> tuple:
    data = json.loads(frames_path.read_text(encoding="utf-8"))
    size = data.get("frameGrid", {}).get("size") or [64, 64]
    return int(size[0]), int(size[1])


def generate_for_dir(sheet_dir: Path, glob_pat: str = "*_walk.png") -> list:
    gen = HitboxGenerator()
    results = []
    for png in sorted(sheet_dir.glob(glob_pat)):
        frames = png.with_suffix(".frames")
        if frames.exists():
            tw, th = _tile_from_frames(frames)
        else:
            from PIL import Image
            with Image.open(png) as im:
                th = im.height
                tw = th if im.width % th == 0 else im.width
        analysis = gen.analyze_spritesheet(png, tw, th)
        dest = png.with_name(png.stem + ".hitbox.json")
        write_hitbox_json(analysis, dest)
        box = (analysis.max_hitbox.collision_box() if analysis.max_hitbox else None)
        results.append({"sheet": str(png), "hitbox": str(dest), "collisionBox": box})
        print(f"  {png.name} -> {dest.name}")
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="Bake mech hitboxes from spritesheets")
    ap.add_argument(
        "--mod-path",
        default=r"F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    )
    ap.add_argument("--glob", default="*_walk.png")
    args = ap.parse_args()
    mod = Path(args.mod_path)
    targets = [
        mod / "assets" / "magitech" / "unity_sheets" / "mech",
        mod / "sprites" / "forms",
        mod / "assets" / "magitech" / "unity_sheets" / "minion",
    ]
    all_results = []
    for d in targets:
        if not d.is_dir():
            continue
        print(f"Hitboxes in {d}")
        all_results.extend(generate_for_dir(d, args.glob))
    summary = mod / "assets" / "magitech" / "unity_sheets" / "hitboxes.json"
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(json.dumps({"count": len(all_results), "assets": all_results}, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(all_results)} hitboxes -> {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
