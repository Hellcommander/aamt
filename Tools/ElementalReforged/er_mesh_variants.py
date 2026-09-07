#!/usr/bin/env python3
"""
Automated mesh-variant + texture-recolor for Elemental Reforged monster gear.

Why this exists
---------------
New game-ready skinned meshes cannot be authored by AI or scripts: Reforged
uses Havok-7.1.0-r1 packfiles and there is no reliable decoder/exporter outside
a manual Softimage/HCT session. So instead of inventing geometry we:

  1. Reuse the game's OWN meshes that are already skinned to a race's skeleton
     (e.g. Darkling -> M_Darkling_Armored_Mesh_01). Races animate on a small set
     of shared skeletons (Wraith / Darkling / Juggernaut), so any mesh skinned to
     that skeleton is interchangeable across races that share the UnitModelType.
  2. Produce distinct clothes/armor by RECOLORING the original DDS texture toward
     each race's palette (ImageMagick), installed as a new LHL_* texture the XML
     references. Guaranteed loadable, zero manual modeling.

Fallback chain (always produces a usable model/texture):
  model:   alt mesh (family pool, on disk) -> configured model -> baseModelPath
  texture: recolored LHL_*.dds -> original texture -> sibling kind texture -> None
"""
from __future__ import annotations

import copy
import re
import subprocess
from pathlib import Path
from typing import Any, Optional

from er_ai_pipeline import find_magick
from er_tool_lib import find_mesh

# UnitModelType -> skeleton family. Meshes skinned to the same family are swappable.
SKELETON_FAMILY = {
    "WraithMale": "wraith",
    "WraithFemale": "wraith",
    "DarklingMale": "darkling",
    "DarklingFemale": "darkling",
    "JuggernautMale": "juggernaut",
    "JuggernautFemale": "juggernaut",
}

ARMOR_HINTS = (
    "armored", "armor", "equipment", "warrior", "plate", "breastplate",
    "slag", "rock", "sandbrute", "super", "shell", "gear", "fire", "yeti",
)
CLOTH_HINTS = ("cloth", "shirt", "skirt", "robe", "wrap", "hide", "peasant", "mesh_01")
WEAPON_HINTS = {
    "axe": ("axe", "cleaver", "hatchet"),
    "blade": ("sword", "blade", "scimitar", "longsword"),
    "club": ("club", "mace", "maul", "hammer", "blunt"),
    "bow": ("bow", "longbow", "crossbow"),
}


def skeleton_family(race: dict[str, Any]) -> str:
    umt = race.get("unitModelTypePrimary") or (race.get("unitModelTypes") or [""])[0]
    return SKELETON_FAMILY.get(umt, "wraith")


def _mesh_name(model: str) -> str:
    return Path(model.replace("\\", "/")).stem


def _norm_model(model: str) -> str:
    return model.replace("\\", "/")


def build_family_pool(cfg: dict[str, Any]) -> dict[str, list[str]]:
    """Group known-good mesh model paths by skeleton family, seeded from config."""
    pool: dict[str, set[str]] = {}
    for race in cfg["races"].values():
        fam = skeleton_family(race)
        pool.setdefault(fam, set())
        for kind in ("clothes", "armor"):
            pack = race.get(kind)
            if pack and pack.get("model"):
                pool[fam].add(_norm_model(pack["model"]))
        if race.get("baseModelPath"):
            pool[fam].add(_norm_model(race["baseModelPath"]))
    return {k: sorted(v) for k, v in pool.items()}


def build_weapon_pool(cfg: dict[str, Any]) -> list[str]:
    """All configured weapon models (proven usable)."""
    out: set[str] = set()
    for race in cfg["races"].values():
        pack = race.get("weapon")
        if pack and pack.get("model"):
            out.add(_norm_model(pack["model"]))
    return sorted(out)


def _score(name: str, hints: tuple[str, ...]) -> int:
    low = name.lower()
    return sum(1 for h in hints if h in low)


def _weapon_style(pack: dict[str, Any]) -> str:
    style = (pack.get("iconStyle") or "").lower()
    if style in WEAPON_HINTS:
        return style
    up = (pack.get("weaponUpgradeType") or "").lower()
    wt = (pack.get("weaponType") or "").lower()
    name = (pack.get("itemName") or "").lower()
    blob = f"{up} {wt} {name}"
    if "bow" in blob:
        return "bow"
    if "axe" in blob or "cleaver" in blob:
        return "axe"
    if "club" in blob or "mace" in blob or "maul" in blob or "blunt" in blob:
        return "club"
    return "blade"


def suggest_variants(cfg: dict[str, Any], race_key: str) -> dict[str, Any]:
    """Recommend clothes/armor meshes for a race from the proven-compatible pool."""
    race = cfg["races"][race_key]
    fam = skeleton_family(race)
    pool = build_family_pool(cfg).get(fam, [])

    cur_clothes = (race.get("clothes") or {}).get("model")
    cur_armor = (race.get("armor") or {}).get("model")
    own_prefix = race_key.lower()

    def best(hints: tuple[str, ...], default: Optional[str]) -> Optional[str]:
        cands = list(pool)
        if default and _norm_model(default) not in {_norm_model(c) for c in cands}:
            cands.append(default)
        scored = sorted(
            cands,
            key=lambda m: (
                _score(_mesh_name(m), hints),
                own_prefix in _mesh_name(m).lower(),
            ),
            reverse=True,
        )
        return scored[0] if scored else default

    clothes_pick = best(CLOTH_HINTS, cur_clothes) or cur_clothes
    armor_pick = best(ARMOR_HINTS, cur_armor) or cur_armor

    return {
        "race": race_key,
        "family": fam,
        "poolSize": len(pool),
        "clothes": {
            "current": cur_clothes,
            "suggested": clothes_pick,
            "onDisk": bool(find_mesh(cfg, clothes_pick)) if clothes_pick else False,
        },
        "armor": {
            "current": cur_armor,
            "suggested": armor_pick,
            "onDisk": bool(find_mesh(cfg, armor_pick)) if armor_pick else False,
        },
    }


def _pick_alt_model(
    cfg: dict[str, Any],
    race: dict[str, Any],
    kind: str,
    primary: str,
) -> tuple[str, str]:
    """
    Pick an alternate model different from primary when possible.
    Returns (model, source) where source is alt|primary|base|fallback.
    """
    primary_n = _norm_model(primary) if primary else ""
    fam = skeleton_family(race)

    if kind == "weapon":
        pool = build_weapon_pool(cfg)
        pack = race.get("weapon") or {}
        hints = WEAPON_HINTS.get(_weapon_style(pack), WEAPON_HINTS["blade"])
        cands = [m for m in pool if _norm_model(m) != primary_n]
        # Prefer same weapon style, then any other weapon, then primary.
        scored = sorted(cands, key=lambda m: _score(_mesh_name(m), hints), reverse=True)
        for m in scored:
            if find_mesh(cfg, m) or True:  # configured weapons are trusted even if packed
                return m, "alt"
        return primary, "primary"

    pool = build_family_pool(cfg).get(fam, [])
    hints = ARMOR_HINTS if kind == "armor" else CLOTH_HINTS
    own = (race.get("display") or "").lower()
    cands = [m for m in pool if _norm_model(m) != primary_n]

    def rank(m: str) -> tuple:
        on_disk = 1 if find_mesh(cfg, m) else 0
        return (_score(_mesh_name(m), hints), own in _mesh_name(m).lower(), on_disk)

    scored = sorted(cands, key=rank, reverse=True)
    if scored:
        return scored[0], "alt"

    base = race.get("baseModelPath")
    if base and _norm_model(base) != primary_n:
        return _norm_model(base), "base"

    return primary, "primary"


def _find_texture_src(cfg: dict[str, Any], texture_name: str) -> Optional[Path]:
    if not texture_name:
        return None
    src = find_mesh(cfg, texture_name)
    if src:
        return src
    from er_original_assets import find_original_texture

    return find_original_texture(cfg, str(texture_name))


def _hex_ok(c: str) -> bool:
    return bool(re.fullmatch(r"#?[0-9a-fA-F]{6}", c or ""))


def recolor_texture(
    src: Path,
    dst: Path,
    palette: list[str],
    *,
    tint: int = 45,
    saturation: int = 115,
) -> bool:
    """Recolor DDS/PNG toward palette; write DXT5 + full mipmaps."""
    magick = find_magick()
    if not magick or not src.is_file():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)

    tint_color = next(
        (c if c.startswith("#") else f"#{c}" for c in palette if _hex_ok(c)),
        "#808080",
    )
    cmd = [
        str(magick),
        str(src),
        "-modulate",
        f"100,{saturation},100",
        "-channel",
        "RGB",
        "-fill",
        tint_color,
        "-tint",
        str(tint),
        "+channel",
    ]
    if dst.suffix.lower() == ".dds":
        cmd += ["-define", "dds:compression=dxt5", "-define", "dds:mipmaps=9"]
    cmd.append(str(dst))
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return dst.is_file()
    except Exception:
        return False


def variant_texture_name(cfg: dict[str, Any], race_key: str, kind: str, *, alt: bool = False) -> str:
    prefix = cfg.get("prefix", "LHL_")
    suffix = "_Alt" if alt else ""
    return f"{prefix}{race_key}_{kind.capitalize()}{suffix}_Texture.dds"


def make_texture_variant(
    cfg: dict[str, Any],
    race_key: str,
    kind: str,
    *,
    dst_dir: Path,
    source_texture: Optional[str] = None,
    alt: bool = False,
) -> Optional[str]:
    """
    Produce a recolored DDS from source_texture (or pack texture).
    Returns filename to reference in XML, or None on failure.
    """
    race = cfg["races"][race_key]
    pack = race.get(kind) or {}
    orig_name = source_texture or pack.get("texture")
    if not orig_name:
        # Fall back to sibling clothes/armor texture
        for other in ("clothes", "armor"):
            if other == kind:
                continue
            sib = (race.get(other) or {}).get("texture")
            if sib:
                orig_name = sib
                break
    if not orig_name:
        return None

    src = _find_texture_src(cfg, str(orig_name))
    if not src or not src.is_file():
        return None

    out_name = variant_texture_name(cfg, race_key, kind, alt=alt)
    dst = dst_dir / out_name
    palette = list(race.get("palette") or ["#808080"])
    if alt:
        # Shift palette emphasis for Alt (use last accent color, stronger tint)
        if len(palette) > 1:
            palette = [palette[-1], palette[0]] + palette[1:]
        tint = 70 if kind == "armor" else 55
        sat = 130
    else:
        tint = 55 if kind == "armor" else (35 if kind == "weapon" else 40)
        sat = 115
    if recolor_texture(src, dst, palette, tint=tint, saturation=sat):
        return out_name
    return None


def resolve_item_assets(
    cfg: dict[str, Any],
    race_key: str,
    kind: str,
    *,
    alt: bool = False,
    dst_dir: Optional[Path] = None,
    make_texture: bool = True,
) -> dict[str, Any]:
    """
    Resolve model + texture for a primary or Alt item with full fallbacks.

    Never fails to return a model if the pack has one configured.
    Texture may be None (omit from XML) when nothing is available.
    """
    race = cfg["races"][race_key]
    pack = copy.deepcopy(race.get(kind) or {})
    primary_model = pack.get("model") or race.get("baseModelPath") or ""
    primary_tex = pack.get("texture")

    model = primary_model
    model_source = "primary"
    if alt and primary_model:
        model, model_source = _pick_alt_model(cfg, race, kind, primary_model)

    # If preferred model missing on disk but another pool mesh exists, keep configured
    # path anyway (game packs often resolve from gamedata.dat).
    texture = primary_tex
    texture_source = "original" if primary_tex else "none"
    variant_file = None

    if make_texture and dst_dir is not None and (kind in ("clothes", "armor", "weapon")):
        # Weapons: only recolor when an original texture name exists
        if kind == "weapon" and not primary_tex:
            texture = None
            texture_source = "none"
        else:
            variant = make_texture_variant(
                cfg,
                race_key,
                kind,
                dst_dir=dst_dir,
                source_texture=primary_tex,
                alt=alt,
            )
            if variant:
                texture = variant
                texture_source = "recolor_alt" if alt else "recolor"
                variant_file = str(dst_dir / variant)
            elif primary_tex:
                texture = primary_tex
                texture_source = "original_fallback"
            else:
                # Last resort: sibling texture name (no recolor)
                for other in ("clothes", "armor"):
                    sib = (race.get(other) or {}).get("texture")
                    if sib:
                        texture = sib
                        texture_source = "sibling_fallback"
                        break
                else:
                    texture = None
                    texture_source = "none"

    pack["model"] = model
    if texture:
        pack["texture"] = texture
    elif "texture" in pack:
        # Keep empty weapons without inventing a texture
        if kind == "weapon":
            pack.pop("texture", None)
        else:
            pack["texture"] = primary_tex  # may still be None

    # Alt display name
    if alt and pack.get("itemName"):
        pack["itemName"] = f"{pack['itemName']} (Alt)"
        # Slightly different stats so Alt is distinct in design screen
        if kind in ("clothes", "armor") and pack.get("defense") is not None:
            pack["defense"] = int(pack["defense"]) + (1 if kind == "armor" else 0)
        if kind == "weapon" and pack.get("attack") is not None:
            pack["attack"] = int(pack["attack"]) + 1

    return {
        "pack": pack,
        "model": model,
        "modelSource": model_source,
        "texture": texture,
        "textureSource": texture_source,
        "variantTextureFile": variant_file,
        "alt": alt,
        "usedFallback": model_source != ("alt" if alt else "primary")
        or texture_source
        in ("original_fallback", "sibling_fallback", "none", "primary"),
    }


if __name__ == "__main__":
    import json
    import sys

    from er_tool_lib import load_config

    cfg = load_config()
    if "--pool" in sys.argv:
        print(json.dumps(build_family_pool(cfg), indent=2))
    elif "--resolve" in sys.argv:
        out = {}
        for rk in cfg["races"]:
            out[rk] = {}
            for kind in ("clothes", "armor", "weapon"):
                if kind not in cfg["races"][rk]:
                    continue
                out[rk][kind] = {
                    "primary": resolve_item_assets(cfg, rk, kind, alt=False, make_texture=False),
                    "alt": resolve_item_assets(cfg, rk, kind, alt=True, make_texture=False),
                }
                # shrink for display
                for v in out[rk][kind].values():
                    v.pop("pack", None)
        print(json.dumps(out, indent=2))
    else:
        keys = list(cfg["races"])
        print(json.dumps({k: suggest_variants(cfg, k) for k in keys}, indent=2))
