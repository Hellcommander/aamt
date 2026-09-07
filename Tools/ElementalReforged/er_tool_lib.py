#!/usr/bin/env python3
"""Shared helpers for Elemental Reforged monster race asset tools."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / "monster_race_config.json"
KINDS = ("clothes", "armor", "weapon")


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = Path(path) if path else DEFAULT_CONFIG
    return json.loads(cfg_path.read_text(encoding="utf-8"))


def race_keys(cfg: dict[str, Any], race: str | None = None) -> list[str]:
    if not race or race.lower() == "all":
        return list(cfg["races"])
    if race not in cfg["races"]:
        raise SystemExit(f"Unknown race '{race}'. Valid: {', '.join(cfg['races'])}")
    return [race]


def kinds_for_race(race: dict[str, Any], kinds: list[str] | None = None) -> list[str]:
    wanted = kinds or list(KINDS)
    return [k for k in wanted if k in race]


def weapon_icon_style(pack: dict[str, Any]) -> str:
    if pack.get("iconStyle"):
        return str(pack["iconStyle"])
    wt = (pack.get("weaponType") or "").lower()
    up = (pack.get("weaponUpgradeType") or "").lower()
    name = (pack.get("itemName") or "").lower()
    if "bow" in wt or "bow" in up or "bow" in name:
        return "bow"
    if "axe" in up or "cleaver" in name or "axe" in name:
        return "axe"
    if "blunt" in wt or "club" in name or "maul" in name or "mace" in name:
        return "club"
    return "blade"


def normalize_hkb_name(model: str) -> str:
    p = model.replace("\\", "/").strip()
    return Path(p).name.lower()


def resolve_mesh_candidates(cfg: dict[str, Any], model: str) -> list[Path]:
    """Return likely filesystem locations for an HKB referenced in XML."""
    name = Path(model.replace("\\", "/")).name
    rel = model.replace("\\", "/").lstrip("/")
    roots: list[Path] = []
    for key in ("referenceHkbPath", "gamePath"):
        raw = cfg.get(key)
        if not raw:
            continue
        base = Path(raw)
        roots.append(base)
        if key == "gamePath":
            roots.append(base / "Gfx" / "HKB")
            roots.append(base / "Gfx")
        else:
            roots.append(base.parent if base.name.lower() == "hkb" else base)

    out: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        candidates = [
            root / name,
            root / "Monsters" / name,
            root / "Weapons" / name,
            root / "Clothes" / name,
            root / "Armor" / name,
            root / "Dragons" / name,
            root / Path(rel),
            root / "Monsters" / Path(rel).name,
            root / "Weapons" / Path(rel).name,
        ]
        # Also try under Gfx/HKB when root is game path
        if (root / "Gfx" / "HKB").exists():
            hkb = root / "Gfx" / "HKB"
            candidates.extend(
                [
                    hkb / name,
                    hkb / "Monsters" / name,
                    hkb / "Weapons" / name,
                    hkb / "Clothes" / name,
                    hkb / Path(rel),
                ]
            )
        for c in candidates:
            key = str(c).lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(c)
    return out


def find_mesh(cfg: dict[str, Any], model: str) -> Path | None:
    for c in resolve_mesh_candidates(cfg, model):
        if c.is_file():
            return c
    return None


def validate_config(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if "races" not in cfg or not cfg["races"]:
        errors.append("config missing races")
        return errors
    for key, race in cfg["races"].items():
        if "display" not in race:
            errors.append(f"{key}: missing display")
        if "unitModelTypes" not in race or not race["unitModelTypes"]:
            errors.append(f"{key}: missing unitModelTypes")
        if "clothes" not in race and "armor" not in race:
            errors.append(f"{key}: needs clothes and/or armor pack")
        for kind in KINDS:
            pack = race.get(kind)
            if not pack:
                continue
            if not pack.get("model"):
                errors.append(f"{key}.{kind}: missing model")
            if not pack.get("itemName"):
                errors.append(f"{key}.{kind}: missing itemName")
            if kind != "weapon" and not pack.get("texture"):
                errors.append(f"{key}.{kind}: missing texture (clothes/armor)")
    return errors


def mod_path(cfg: dict[str, Any], override: str | None = None) -> Path:
    return Path(override or cfg.get("modDefaultPath") or "")


def extra_units_path(cfg: dict[str, Any], override: str | None = None) -> Path:
    return mod_path(cfg, override) / "Data" / "GameCore" / "LHL_ExtraUnits.xml"
