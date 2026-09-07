#!/usr/bin/env python3
"""Write DF graphics RAWs (tile pages + CREATURE_GRAPHICS) and tile JSON manifest."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


def write_graphics(
    spec: Dict[str, Any],
    mod_root: Path,
    *,
    body_png_rel: str = "images/{id}_body.png",
    portrait_png_rel: str = "images/{id}_portrait.png",
) -> Dict[str, Path]:
    """
    Write graphics/ tile_page + creature graphics using ANIMAL_PEOPLE layer set
    for humanoid profile. simple profile writes a minimal DEFAULT layer set.
    """
    cid = str(spec["id"]).upper()
    cid_l = cid.lower()
    profile = (spec.get("graphics_profile") or "humanoid").lower()
    graphics_dir = Path(mod_root) / "graphics"
    images_dir = graphics_dir / "images"
    graphics_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    body_rel = body_png_rel.format(id=cid_l)
    portrait_rel = portrait_png_rel.format(id=cid_l)
    page_id = f"CREATURES_AAMT_{cid}"
    portrait_page = f"PORTRAIT_AAMT_{cid}"

    # 7 tiles wide × 5 rows (default, child, animated, corpse, list_icon) @ 32px
    # = 224 × 160 pixels
    tile_page = f"""graphics_tile_page_{cid_l}

[OBJECT:TILE_PAGE]

[TILE_PAGE:{page_id}]
\t[FILE:{body_rel}]
\t[TILE_DIM:32:32]
\t[PAGE_DIM_PIXELS:224:160]

[TILE_PAGE:{portrait_page}]
\t[FILE:{portrait_rel}]
\t[TILE_DIM:96:96]
\t[PAGE_DIM_PIXELS:96:96]
"""
    tile_page_path = graphics_dir / f"tile_page_{cid_l}.txt"
    tile_page_path.write_text(tile_page, encoding="utf-8")

    if profile == "humanoid":
        creature_gfx = f"""graphics_creatures_{cid_l}

[OBJECT:GRAPHICS]

[CREATURE_GRAPHICS:{cid}]
\t[SKELETON_WITH_SKULL:BONE_PILE:1:0]
\t[SKELETON:BONE_PILE:0:0]

\t[LAYER_SET:DEFAULT]
\t\t[USE_LAYER_SET_TEMPLATE:ANIMAL_PEOPLE]
\t\t\t[ARG_WEARABLES_TP:ANIMAL_PEOPLE_WEARABLES]
\t\t\t[ARG_HEAD:YES]
\t\t\t\t[ARG_HEAD_TEXTURE:{page_id}:0:0]
\t\t\t\t[ARG_HEAD_OFFSETS:-6:-4]
\t\t\t[ARG_BODY:YES]
\t\t\t\t[ARG_BODY_TEXTURE:{page_id}:1:0]
\t\t\t\t[ARG_BODY_OFFSETS:0:0]
\t\t\t[ARG_RIGHT_HAND_WIDE:YES]
\t\t\t\t[ARG_WIDE_RH:RH]
\t\t\t\t[ARG_RIGHT_HAND_WIDE_TEXTURE:{page_id}:2:0]
\t\t\t\t[ARG_RIGHT_HAND_WIDE_OFFSETS:0:0]
\t\t\t\t[ARG_WIELDABLES_RHW_OFFSETS:2:0]
\t\t\t[ARG_LEFT_HAND_WIDE:YES]
\t\t\t\t[ARG_WIDE_LH:LH]
\t\t\t\t[ARG_LEFT_HAND_WIDE_TEXTURE:{page_id}:3:0]
\t\t\t\t[ARG_LEFT_HAND_WIDE_OFFSETS:0:0]
\t\t\t\t[ARG_WIELDABLES_LHW_OFFSETS:-6:-3]
\t\t\t[ARG_RIGHT_FOOT:YES]
\t\t\t\t[ARG_RIGHT_FOOT_TEXTURE:{page_id}:4:0]
\t\t\t\t[ARG_RIGHT_FOOT_OFFSETS:0:0]
\t\t\t[ARG_LEFT_FOOT:YES]
\t\t\t\t[ARG_LEFT_FOOT_TEXTURE:{page_id}:5:0]
\t\t\t\t[ARG_LEFT_FOOT_OFFSETS:0:0]
\t\t\t[ARG_TAIL:YES]
\t\t\t\t[ARG_TAIL_TEXTURE:{page_id}:6:0]
\t\t\t\t[ARG_TAIL_OFFSETS:0:0]

\t[LAYER_SET:CHILD]
\t\t[USE_LAYER_SET_TEMPLATE:ANIMAL_PEOPLE]
\t\t\t[ARG_WEARABLES_TP:ANIMAL_PEOPLE_WEARABLES]
\t\t\t[ARG_HEAD:YES]
\t\t\t\t[ARG_HEAD_TEXTURE:{page_id}:0:1]
\t\t\t\t[ARG_HEAD_OFFSETS:-6:-4]
\t\t\t[ARG_BODY:YES]
\t\t\t\t[ARG_BODY_TEXTURE:{page_id}:1:1]
\t\t\t\t[ARG_BODY_OFFSETS:0:0]
\t\t\t[ARG_RIGHT_HAND_WIDE:YES]
\t\t\t\t[ARG_WIDE_RH:RH]
\t\t\t\t[ARG_RIGHT_HAND_WIDE_TEXTURE:{page_id}:2:1]
\t\t\t\t[ARG_RIGHT_HAND_WIDE_OFFSETS:0:0]
\t\t\t[ARG_LEFT_HAND_WIDE:YES]
\t\t\t\t[ARG_WIDE_LH:LH]
\t\t\t\t[ARG_LEFT_HAND_WIDE_TEXTURE:{page_id}:3:1]
\t\t\t\t[ARG_LEFT_HAND_WIDE_OFFSETS:0:0]
\t\t\t[ARG_RIGHT_FOOT:YES]
\t\t\t\t[ARG_RIGHT_FOOT_TEXTURE:{page_id}:4:1]
\t\t\t\t[ARG_RIGHT_FOOT_OFFSETS:0:0]
\t\t\t[ARG_LEFT_FOOT:YES]
\t\t\t\t[ARG_LEFT_FOOT_TEXTURE:{page_id}:5:1]
\t\t\t\t[ARG_LEFT_FOOT_OFFSETS:0:0]

\t[ANIMATED:{page_id}:1:2]
\t[CORPSE:{page_id}:1:3]
\t[LARGE_IMAGE:{portrait_page}:0:0]
\t[LIST_ICON:{page_id}:0:4]
"""
    else:
        # Simple: single-tile style referencing body cell
        creature_gfx = f"""graphics_creatures_{cid_l}

[OBJECT:GRAPHICS]

[CREATURE_GRAPHICS:{cid}]
\t[DEFAULT:{page_id}:1:0]
\t[CHILD:{page_id}:1:1]
\t[ANIMATED:{page_id}:1:2]
\t[CORPSE:{page_id}:1:3]
\t[LIST_ICON:{page_id}:0:4]
\t[LARGE_IMAGE:{portrait_page}:0:0]
"""

    gfx_path = graphics_dir / f"graphics_creatures_{cid_l}.txt"
    gfx_path.write_text(creature_gfx, encoding="utf-8")

    manifest = {
        "id": cid,
        "graphics_profile": profile,
        "tile_page": page_id,
        "portrait_page": portrait_page,
        "body_sheet": f"graphics/{body_rel}",
        "portrait": f"graphics/{portrait_rel}",
        "tile_dim": [32, 32],
        "sheet_tiles": ["head", "body", "RH", "LH", "RF", "LF", "tail"],
        "sheet_states": ["default", "child", "animated", "corpse", "list_icon"],
        "page_dim_pixels": [224, 160],
        "portrait_dim": [96, 96],
        "wearables_arg": "ANIMAL_PEOPLE_WEARABLES" if profile == "humanoid" else None,
    }
    manifest_path = Path(mod_root) / "graphics.tile.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    return {
        "tile_page": tile_page_path,
        "creature_graphics": gfx_path,
        "manifest": manifest_path,
    }
