#!/usr/bin/env python3
"""
Alt-mesh + item catalog for Transcendence ship hull/shield HUDs.

Indexes armor / shield ItemTypes from base game, DLC source trees, and installed
Extensions, then resolves per-ship mesh fallbacks:

  Source/Models/Alt/{Armor|Shield}/{itemEntity}.fbx
    -> family pool mesh
    -> ship Source/Models/{Ship}.fbx
    -> Meshes/{Ship}.fbx
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

TX_ROOT_DEFAULT = Path(r"D:\games\Steam\steamapps\common\Transcendence")
SOURCE_ROOTS = (
    "game_and_dlc_source/Transcendence_Source",
    "game_and_dlc_source/CorporateHierarchyVol01_Source",
    "game_and_dlc_source/NearStarsVol01_Source",
    "game_and_dlc_source/ElementalShift_Source",
    "Extensions",
)

ITEM_BLOCK_RE = re.compile(
    r'<ItemType\s+UNID="&(?P<entity>[^;]+);"(?P<head>.*?)>(?P<body>.*?)</ItemType>',
    re.IGNORECASE | re.DOTALL,
)
ATTR_RE = re.compile(r'\b(?P<k>name|level|attributes)\s*=\s*"(?P<v>[^"]*)"', re.I)

ARMOR_FAMILY_HINTS: Dict[str, Tuple[str, ...]] = {
    "reactive": ("reactive", "plated", "plate"),
    "ceramic": ("ceramic", "ceralloy", "plasteel"),
    "meteor": ("meteor", "xenophobe", "bennin"),
    "organic": ("organic", "bio", "chitin", "scale"),
    "heavy": ("heavy", "titanium", "advanced", "reinforced"),
    "light": ("light", "composite", "alloy"),
}
SHIELD_FAMILY_HINTS: Dict[str, Tuple[str, ...]] = {
    "deflector": ("deflector", "class1", "class2", "class3"),
    "plasma": ("plasma", "ion", "energy"),
    "gravitic": ("gravitic", "gravity", "repulsor"),
    "organic": ("organic", "bio", "living"),
    "military": ("military", "fleet", "commonwealth", "ram"),
}

FAMILY_COLORS: Dict[str, Tuple[int, int, int]] = {
    "reactive": (120, 140, 160),
    "ceramic": (180, 160, 130),
    "meteor": (160, 80, 120),
    "organic": (90, 140, 90),
    "heavy": (90, 100, 120),
    "light": (150, 170, 190),
    "deflector": (80, 200, 255),
    "plasma": (120, 180, 255),
    "gravitic": (180, 140, 255),
    "military": (100, 160, 220),
    "default": (110, 130, 150),
}


def _tx_root(explicit: Optional[Path] = None) -> Path:
    return Path(explicit) if explicit else TX_ROOT_DEFAULT


def _scan_roots(tx_root: Path) -> List[Path]:
    return [tx_root / rel for rel in SOURCE_ROOTS if (tx_root / rel).is_dir()]


def _kind_of_item(body: str) -> Optional[str]:
    if re.search(r"<\s*Shields\b", body, re.I):
        return "shield"
    if re.search(r"<\s*Armor\b", body, re.I) and not re.search(r"<\s*ArmorSection\b", body, re.I):
        return "armor"
    return None


def _attrs(head: str, body: str) -> Dict[str, str]:
    blob = head + " " + body[:800]
    out: Dict[str, str] = {}
    for m in ATTR_RE.finditer(blob):
        out[m.group("k").lower()] = m.group("v")
    return out


def _family(kind: str, entity: str, name: str, attributes: str) -> str:
    blob = f"{entity} {name} {attributes}".lower()
    hints = ARMOR_FAMILY_HINTS if kind == "armor" else SHIELD_FAMILY_HINTS
    best, score = "default", 0
    for fam, words in hints.items():
        s = sum(1 for w in words if w in blob)
        if s > score:
            best, score = fam, s
    return best


def catalog_armor_shield_items(
    tx_root: Optional[Path] = None,
    *,
    max_files: int = 500,
) -> Dict[str, List[Dict[str, Any]]]:
    root = _tx_root(tx_root)
    armor: List[Dict[str, Any]] = []
    shield: List[Dict[str, Any]] = []
    seen: set[str] = set()
    files_scanned = 0
    for base in _scan_roots(root):
        for xml in base.rglob("*.xml"):
            if files_scanned >= max_files:
                break
            try:
                text = xml.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            files_scanned += 1
            if "<ItemType" not in text:
                continue
            for m in ITEM_BLOCK_RE.finditer(text):
                entity = m.group("entity")
                if entity in seen:
                    continue
                kind = _kind_of_item(m.group("body"))
                if not kind:
                    continue
                seen.add(entity)
                attrs = _attrs(m.group("head"), m.group("body"))
                try:
                    level = int(attrs.get("level") or "1")
                except ValueError:
                    level = 1
                rec = {
                    "entity": entity,
                    "kind": kind,
                    "name": attrs.get("name") or entity,
                    "level": level,
                    "attributes": attrs.get("attributes") or "",
                    "family": _family(
                        kind, entity, attrs.get("name") or "", attrs.get("attributes") or ""
                    ),
                    "source": str(xml.relative_to(root)) if xml.is_relative_to(root) else str(xml),
                }
                (armor if kind == "armor" else shield).append(rec)
        if files_scanned >= max_files:
            break
    armor.sort(key=lambda r: (r["level"], r["entity"]))
    shield.sort(key=lambda r: (r["level"], r["entity"]))
    return {"armor": armor, "shield": shield}


def alt_models_dir(pack_dir: Path) -> Path:
    return Path(pack_dir) / "Source" / "Models" / "Alt"


def seed_alt_mesh_pool(
    pack_dir: Path,
    ship_name: str,
    *,
    base_mesh: Optional[Path],
    catalog: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ship_level: int = 5,
    tx_root: Optional[Path] = None,
    max_per_kind: int = 12,
) -> Dict[str, Any]:
    alt = alt_models_dir(pack_dir)
    armor_dir = alt / "Armor"
    shield_dir = alt / "Shield"
    armor_dir.mkdir(parents=True, exist_ok=True)
    shield_dir.mkdir(parents=True, exist_ok=True)

    cat = catalog or catalog_armor_shield_items(tx_root)
    seeded: Dict[str, List[str]] = {"armor": [], "shield": []}

    readme = alt / "README.txt"
    if not readme.is_file():
        readme.write_text(
            "Alt meshes for ship hull / shield HUD styling\n"
            "============================================\n"
            "Drop or edit FBX files here to customize HUD silhouette per item family.\n"
            "  Armor/{itemEntity}.fbx   e.g. itReactiveArmor.fbx\n"
            "  Shield/{itemEntity}.fbx  e.g. itClass1Deflector.fbx\n"
            "  Armor/family_{name}.fbx  shared by family\n"
            "  Shield/family_{name}.fbx\n\n"
            "Resolve order: item FBX -> family FBX -> ship Source/Models mesh.\n"
            "Alt UI textures: Textures/{Armor|Shield}/*.png — regenerate with\n"
            "  Generate-AamtShipHudAltTextures.ps1 -PackDir <pack>  (after adding mods).\n"
            "Disable unique HUD: GenerateGameAsset.ps1 ... -NoUniqueHud\n",
            encoding="utf-8",
        )

    def _seed(kind: str, items: Iterable[Dict[str, Any]], dest: Path) -> None:
        if not base_mesh or not Path(base_mesh).is_file():
            return
        picked: List[Dict[str, Any]] = []
        for rec in items:
            if abs(int(rec.get("level") or 1) - ship_level) <= 2:
                picked.append(rec)
            if len(picked) >= max_per_kind:
                break
        if not picked:
            picked = list(items)[:max_per_kind]
        families_done: set[str] = set()
        for rec in picked:
            entity = rec["entity"]
            dest_item = dest / f"{entity}.fbx"
            if not dest_item.is_file():
                shutil.copy2(base_mesh, dest_item)
                seeded[kind].append(str(dest_item))
            fam = rec.get("family") or "default"
            if fam not in families_done:
                fam_path = dest / f"family_{fam}.fbx"
                if not fam_path.is_file():
                    shutil.copy2(base_mesh, fam_path)
                    seeded[kind].append(str(fam_path))
                families_done.add(fam)

    _seed("armor", cat.get("armor") or [], armor_dir)
    _seed("shield", cat.get("shield") or [], shield_dir)

    meta = {
        "ship": ship_name,
        "baseMesh": str(base_mesh) if base_mesh else None,
        "seeded": seeded,
        "armorCount": len(cat.get("armor") or []),
        "shieldCount": len(cat.get("shield") or []),
        "items": {
            "armor": [
                {"entity": r["entity"], "family": r["family"], "level": r["level"]}
                for r in (cat.get("armor") or [])[:80]
            ],
            "shield": [
                {"entity": r["entity"], "family": r["family"], "level": r["level"]}
                for r in (cat.get("shield") or [])[:80]
            ],
        },
    }
    (alt / "catalog.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def resolve_alt_mesh(
    pack_dir: Path,
    *,
    kind: str,
    entity: str,
    family: str = "default",
    ship_mesh: Optional[Path] = None,
) -> Path:
    alt = alt_models_dir(pack_dir)
    kind_dir = alt / ("Armor" if kind == "armor" else "Shield")
    candidates = [
        kind_dir / f"{entity}.fbx",
        kind_dir / f"family_{family}.fbx",
        kind_dir / "family_default.fbx",
    ]
    if ship_mesh:
        candidates.append(Path(ship_mesh))
    models = Path(pack_dir) / "Source" / "Models"
    if models.is_dir():
        for p in sorted(models.glob("*.fbx")):
            candidates.append(p)
            break
    mesh_dir = Path(pack_dir) / "Meshes"
    if mesh_dir.is_dir():
        for p in sorted(mesh_dir.glob("*.fbx")):
            candidates.append(p)
            break
    for c in candidates:
        if c and Path(c).is_file():
            return Path(c)
    raise FileNotFoundError(f"No alt mesh for {kind}/{entity} under {pack_dir}")


def pick_default_items(
    catalog: Dict[str, List[Dict[str, Any]]],
    *,
    armor_entity: Optional[str] = None,
    shield_entity: Optional[str] = None,
    ship_level: int = 5,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    def _pick(kind: str, want: Optional[str]) -> Dict[str, Any]:
        items = catalog.get(kind) or []
        want_clean = (want or "").strip().strip("&;")
        if want_clean:
            for r in items:
                if r["entity"] == want_clean:
                    return r
        preferred = (
            ("itReactiveArmor", "itPlasteelArmor", "itTitaniumArmor")
            if kind == "armor"
            else ("itClass1Deflector", "itClass2Deflector", "itPlasmaShieldGenerator")
        )
        for ent in preferred:
            for r in items:
                if r["entity"] == ent:
                    return r
        if not items:
            return {
                "entity": want_clean
                or ("itReactiveArmor" if kind == "armor" else "itClass1Deflector"),
                "kind": kind,
                "name": want_clean or kind,
                "level": ship_level,
                "attributes": "",
                "family": "default",
                "source": "fallback",
            }
        return min(items, key=lambda r: abs(int(r.get("level") or 1) - ship_level))

    return _pick("armor", armor_entity), _pick("shield", shield_entity)


def family_color(family: str) -> Tuple[int, int, int]:
    return FAMILY_COLORS.get(family, FAMILY_COLORS["default"])
