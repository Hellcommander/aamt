#!/usr/bin/env python3
"""
Resolve and copy original Elemental / LH assets for monster gear packs.

Philosophy: never invent meshes or textures from scratch.
XML already points at original HKB ModelFile + Texture_* paths.
This module supplies:
  - original texture files (copied/converted for Source/ artist refs)
  - original medallion/card icons resized for item UI
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional

from er_ai_pipeline import find_magick
from er_tool_lib import find_mesh, resolve_mesh_candidates

try:
    from PIL import Image

    PIL_OK = True
except ImportError:
    PIL_OK = False
    Image = None  # type: ignore


# Default medallion / card art per race (LH / Reforged Gfx/Medallions)
DEFAULT_ICONS: dict[str, list[str]] = {
    "Demon": ["M_AssassinDemon_01_Card.png", "M_CrowDemon_Ancient_Card_01.png"],
    "Darkling": ["M_Darkling_Warrior_Card.png", "M_Darkling_Card.png", "M_Darkling_Shaman_Card.png"],
    "FireElemental": ["M_Fire_Elemental_Card.png", "M_Elemental_Fire_Card.png", "M_AssassinDemon_01_Card.png"],
    "EarthElemental": ["M_EarthElemental_Card.png", "M_Elemental_Earth_Card.png", "M_Golem_Card_01.png"],
    "AirElemental": ["M_AirElemental_Card.png", "M_Elemental_Air_Card.png"],
    "IceElemental": ["M_IceElemental_Card.png", "M_Elemental_Ice_Card.png", "M_Warg_IceWarg_Card.png"],
    "Ogre": ["M_Giant_Ogre_Card_01.png", "M_Giant_Troll_Card_01.png", "Ability_Juggernaut_Icon.png"],
    "Troll": ["M_Giant_Troll_Card_01.png", "M_Giant_Ogre_Card_01.png"],
    "Golem": ["M_Golem_Card_01.png", "M_Golem_ObsidianGolem_Card_01.png", "M_Golem_bronze_card.png"],
    "Drake": ["M_Drake_Drake_Card_01.png", "M_Drake_Slag_Card_01.png"],
    "Brood": ["M_AlbinoRockSpider_Giant_Card_01.png", "M_Spider_Corps_Card_01.png"],
    "Dragon": ["M_Drake_Slag_Card_01.png", "M_Drake_Drake_Card_01.png"],
    "Skath": ["M_Warg_Skath_Card.png", "M_Warg_IceWarg_Card.png", "M_Warg_PlainsWarg_Card.png"],
    "Warg": ["M_Warg_PlainsWarg_Card.png", "M_Warg_IceWarg_Card.png"],
    "Shrill": ["M_Spider_Corps_Card_01.png", "M_AlbinoRockSpider_Giant_Card_01.png"],
}

WEAPON_ICON_FALLBACKS = {
    "axe": ["W_Axe_Guillotine_Icon_01.png", "W_Axe_01.png", "Ability_Juggernaut_Icon.png"],
    "blade": ["K_Basic_Longsword_01.png", "W_Rusty_Shortsword_01.png"],
    "club": ["W_Club_Crude_Icon_01.png", "W_Champions_Club_Mesh_01.png"],
    "bow": ["W_Crossbow_01.png", "DLC03_Longbow_Skath_01.png"],
    "mace": ["W_Club_Crude_Icon_01.png"],
}


def _gfx_roots(cfg: dict[str, Any]) -> list[Path]:
    roots: list[Path] = []
    for key in ("gamePath",):
        raw = cfg.get(key)
        if raw:
            roots.append(Path(raw) / "Gfx")
    ref = cfg.get("referenceHkbPath")
    if ref:
        # .../Gfx/HKB → .../Gfx
        p = Path(ref)
        roots.append(p.parent if p.name.lower() == "hkb" else p)
        roots.append(p.parent.parent / "Gfx" if p.name.lower() == "hkb" else p)
    # LH game root sibling
    lh = Path(r"E:\SteamLibrary\steamapps\common\FE Legendary Heroes\Gfx")
    if lh.is_dir():
        roots.append(lh)
    # dedupe
    out: list[Path] = []
    seen: set[str] = set()
    for r in roots:
        k = str(r.resolve()) if r.exists() else str(r)
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def find_named_asset(cfg: dict[str, Any], filename: str) -> Optional[Path]:
    name = Path(filename).name
    stem = Path(filename).stem
    for root in _gfx_roots(cfg):
        if not root.exists():
            continue
        for sub in ("Medallions", "Items", "Icons", "HKB/Monsters", "HKB/Weapons", "HKB", ""):
            base = root / sub if sub else root
            for cand in (
                base / name,
                base / f"{stem}.png",
                base / f"{stem}.dds",
                base / f"{stem}.PNG",
            ):
                if cand.is_file():
                    return cand
        # shallow glob
        hits = list(root.rglob(name))[:1]
        if hits:
            return hits[0]
        hits = list(root.rglob(f"{stem}.png"))[:1]
        if hits:
            return hits[0]
    return None


def find_original_texture(cfg: dict[str, Any], texture_name: str) -> Optional[Path]:
    if not texture_name:
        return None
    # Try mesh-style resolver first (Monsters/Weapons folders)
    hit = find_mesh(cfg, texture_name)
    if hit:
        return hit
    return find_named_asset(cfg, texture_name)


def find_original_icon(
    cfg: dict[str, Any],
    race_key: str,
    race: dict[str, Any],
    kind: str,
    pack: dict[str, Any],
) -> Optional[Path]:
    # Explicit override
    for key in ("iconSource", "icon"):
        if race.get(key):
            hit = find_named_asset(cfg, str(race[key]))
            if hit:
                return hit
        if pack.get(key):
            hit = find_named_asset(cfg, str(pack[key]))
            if hit:
                return hit

    if kind == "weapon":
        style = (pack.get("iconStyle") or "blade").lower()
        for name in WEAPON_ICON_FALLBACKS.get(style, WEAPON_ICON_FALLBACKS["blade"]):
            hit = find_named_asset(cfg, name)
            if hit:
                return hit

    for name in DEFAULT_ICONS.get(race_key, []):
        hit = find_named_asset(cfg, name)
        if hit:
            return hit
    return None


def convert_to_png(src: Path, dst: Path, size: Optional[int] = None) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    magick = find_magick()
    if magick:
        cmd = [str(magick), str(src)]
        if size:
            cmd += ["-resize", f"{size}x{size}>", "-background", "none", "-gravity", "center", "-extent", f"{size}x{size}"]
        cmd.append(str(dst))
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return dst.is_file()
        except Exception:
            pass

    if PIL_OK and Image:
        try:
            im = Image.open(src)
            if size:
                im = im.convert("RGBA")
                im.thumbnail((size, size), Image.Resampling.LANCZOS)
                canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                canvas.paste(im, ((size - im.size[0]) // 2, (size - im.size[1]) // 2), im if im.mode == "RGBA" else None)
                canvas.save(dst)
            else:
                im.convert("RGBA" if "A" in im.getbands() else "RGB").save(dst)
            return dst.is_file()
        except Exception:
            # DDS may need magick; last resort copy if already png
            if src.suffix.lower() == ".png":
                shutil.copy2(src, dst)
                return True
    elif src.suffix.lower() == ".png":
        shutil.copy2(src, dst)
        return True
    return False


def materialize_original_assets(
    cfg: dict[str, Any],
    race_key: str,
    race: dict[str, Any],
    kind: str,
    pack: dict[str, Any],
    *,
    icon_dst: Path,
    texture_dst: Path,
    source_dir: Path,
    icon_size: int = 128,
) -> dict[str, Any]:
    """
    Build item icon + texture template from original game art.
    Returns status dict.
    """
    source_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "icon": False,
        "texture": False,
        "icon_src": None,
        "texture_src": None,
        "mesh": pack.get("model"),
    }

    # --- icon from original medallion/card ---
    icon_src = find_original_icon(cfg, race_key, race, kind, pack)
    if icon_src:
        result["icon_src"] = str(icon_src)
        src_copy = source_dir / f"{icon_dst.stem}_Original{icon_src.suffix}"
        shutil.copy2(icon_src, src_copy)
        if convert_to_png(icon_src, icon_dst, size=icon_size):
            result["icon"] = True

    # --- texture from original race/weapon texture ---
    tex_name = pack.get("texture")
    if tex_name:
        tex_src = find_original_texture(cfg, str(tex_name))
        if tex_src:
            result["texture_src"] = str(tex_src)
            src_copy = source_dir / f"{texture_dst.stem}_Original{tex_src.suffix}"
            shutil.copy2(tex_src, src_copy)
            # Keep a PNG working copy for artists; XML still references original game texture name
            if convert_to_png(tex_src, texture_dst, size=None):
                result["texture"] = True
            else:
                # still record that we found it even if convert failed
                shutil.copy2(tex_src, texture_dst.with_suffix(tex_src.suffix))

    return result
