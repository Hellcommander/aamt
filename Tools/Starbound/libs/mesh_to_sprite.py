#!/usr/bin/env python3
"""Mesh-to-sprite bake wrapper for Magi-Tech MeshToSpritePipeline.

C++ lives at Tools/Starbound/cpp_generators/mesh_to_sprite/.
When Blender is available this delegates to Shared/ship_spritesheet_export.py
(8-directional orthographic capture). Otherwise it packs existing stills into
Starbound sheets using SpritesheetAssembler.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from PIL import Image

_HERE = Path(__file__).resolve().parent
_TOOLS = _HERE.parent
_SHARED = _TOOLS.parent / "Shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from libs.spritesheet_assembler import Layout, SpritesheetAssembler, pack_named_rows


DIRECTIONS_8 = ["front", "front_right", "right", "back_right", "back", "back_left", "left", "front_left"]


def bake_stills_to_starbound(
    stills: Sequence[Path],
    out_dir: Path,
    asset_name: str,
    animation_name: str = "idle",
    tile: Optional[tuple] = None,
) -> Dict[str, Any]:
    """Pack already-rendered frames (Unity/Blender stills) as a Starbound cycle."""
    frames = []
    for p in stills:
        with Image.open(p) as im:
            frames.append(im.convert("RGBA"))
    assembler = SpritesheetAssembler(padding=0)
    names = [f"{animation_name}.{i + 1}" for i in range(len(frames))]
    packed = assembler.assemble(
        frames,
        layout=Layout.HORIZONTAL,
        tile=tile,
        names=names,
        alias=animation_name,
        extra_aliases={"default": names[0], "idle": names},
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / f"{asset_name}_{animation_name}.png"
    frames_path = out_dir / f"{asset_name}_{animation_name}.frames"
    packed.save_png(png)
    packed.save_frames(frames_path)
    anim = {
        "animatedParts": {
            "stateTypes": {
                "movement": {
                    "default": animation_name,
                    "states": {
                        animation_name: {
                            "frames": len(frames),
                            "cycle": max(0.4, len(frames) / 12.0),
                            "mode": "loop",
                        }
                    },
                }
            },
            "parts": {
                "body": {
                    "properties": {"image": f"{asset_name}_{animation_name}.png:<frame>"},
                }
            },
        }
    }
    anim_path = out_dir / f"{asset_name}.animation"
    anim_path.write_text(json.dumps(anim, indent=2) + "\n", encoding="utf-8")
    return {"png": str(png), "frames": str(frames_path), "animation": str(anim_path), "frames_n": len(frames)}


def try_blender_export(**kwargs) -> Optional[Path]:
    try:
        from ship_spritesheet_export import export_spritesheet  # type: ignore
    except Exception:
        return None
    try:
        return export_spritesheet(**kwargs)
    except Exception:
        return None


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Bake stills or a mesh into Starbound sprite sheets")
    ap.add_argument("--stills", nargs="+", help="PNG frames already rendered")
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--animation", default="idle")
    args = ap.parse_args()
    if not args.stills:
        raise SystemExit("Pass --stills PNG... (mesh bake needs Blender / C++ pipeline)")
    result = bake_stills_to_starbound([Path(p) for p in args.stills], Path(args.out), args.name, args.animation)
    print(json.dumps(result, indent=2))
