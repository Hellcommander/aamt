#!/usr/bin/env python3
"""
Export a dual-class build-planner catalog from an unpacked Custom Game database
(default: mods/SurvivalPlayground).

Writes:
  planner/data/catalog.json
  planner/data/catalog_data.js   (window.PLANNER_CATALOG = ...) for file:// UI
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from archive_tool import ArchiveTool, kill_orphan_archivetool
from class_combo_names import collect_tags, parse_tag_file
from dbr_io import get_list_field, read_dbr
from gd_paths import GamePaths, resolve_game_dir

TOOLS_DIR = Path(__file__).resolve().parent
PLANNER_DIR = TOOLS_DIR / "planner"
TAG_CACHE = TOOLS_DIR / "work" / "planner_tags"

TAG_LINE = re.compile(r"^(\S+)\s+(.+)$")


def load_all_tags(paths: List[Path]) -> Dict[str, str]:
    tags: Dict[str, str] = {}
    for root in paths:
        if not root.exists():
            continue
        if root.is_file() and root.suffix.lower() == ".txt":
            tags.update(parse_tag_file(root))
            continue
        for path in root.rglob("*.txt"):
            tags.update(parse_tag_file(path))
    return tags


def ensure_game_tags(game: GamePaths) -> Path:
    """Extract Text_EN.arc (+ DLC text if present) into work/planner_tags once."""
    marker = TAG_CACHE / ".extracted"
    if marker.is_file() and any(TAG_CACHE.rglob("*.txt")):
        return TAG_CACHE
    TAG_CACHE.mkdir(parents=True, exist_ok=True)
    tool = ArchiveTool(game.game_dir)
    arcs = [
        game.game_dir / "resources" / "Text_EN.arc",
        game.game_dir / "gdx1" / "resources" / "Text_EN.arc",
        game.game_dir / "gdx2" / "resources" / "Text_EN.arc",
        game.game_dir / "gdx3" / "resources" / "Text_EN.arc",
    ]
    for arc in arcs:
        if not arc.is_file():
            continue
        dest = TAG_CACHE / arc.parent.parent.name
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        print(f"Extracting tags from {arc.name} ({arc.parent.parent.name}) ...", flush=True)
        try:
            tool.extract_arc(arc, dest)
        except Exception as exc:
            print(f"WARN: tag extract failed {arc}: {exc}", file=sys.stderr)
    marker.write_text("ok", encoding="utf-8")
    kill_orphan_archivetool()
    return TAG_CACHE


def resolve_tag(tags: Dict[str, str], key: str) -> str:
    if not key:
        return ""
    if key in tags:
        return tags[key]
    # case-insensitive
    kl = key.lower()
    for k, v in tags.items():
        if k.lower() == kl:
            return v
    return key


def skill_record(path: Path, tags: Dict[str, str], rel_posix: str) -> Optional[dict]:
    if not path.is_file():
        return None
    data = read_dbr(path)
    name_tag = data.get("skillDisplayName", "")
    desc_tag = data.get("skillBaseDescription", "")
    try:
        max_level = int(float(data.get("skillMaxLevel", "0") or 0))
    except ValueError:
        max_level = 0
    try:
        ultimate = int(float(data.get("skillUltimateLevel", str(max_level)) or max_level))
    except ValueError:
        ultimate = max_level
    try:
        tier = int(float(data.get("skillTier", "0") or 0))
    except ValueError:
        tier = 0
    cls = data.get("Class", "")
    is_mastery = "mastery" in cls.lower() or path.name.lower().startswith("_classtraining")
    return {
        "id": rel_posix.replace("\\", "/").lower(),
        "file": rel_posix.replace("\\", "/"),
        "nameTag": name_tag,
        "name": resolve_tag(tags, name_tag) or path.stem,
        "descTag": desc_tag,
        "description": resolve_tag(tags, desc_tag),
        "maxLevel": max_level,
        "ultimateLevel": ultimate,
        "tier": tier,
        "isMasteryBar": is_mastery,
        "class": cls,
    }


def find_ui_pane_for_tree(mod_db: Path, tree_rel: str) -> Optional[Path]:
    """Match a skill tree DBR to a UI skills/<folder>/classtable.dbr via skill buttons."""
    tree_norm = tree_rel.replace("\\", "/").lower()
    ui_root = mod_db / "records" / "ui" / "skills"
    if not ui_root.is_dir():
        return None
    for folder in sorted(ui_root.iterdir()):
        if not folder.is_dir():
            continue
        name = folder.name.lower()
        if name in ("classcommon", "classselection", "devotion", "skillselectwheel", "hiddendevskills"):
            continue
        table = folder / "classtable.dbr"
        if not table.is_file():
            continue
        # Fast path: folder name appears in tree path
        if name.replace("class", "") and name in tree_norm:
            return folder
        data = read_dbr(table)
        buttons = [
            b.strip()
            for b in (data.get("tabSkillButtons") or "").split(";")
            if b.strip()
        ]
        for bref in buttons[:5]:
            bpath = mod_db / bref.replace("\\", "/")
            if not bpath.is_file():
                continue
            sn = read_dbr(bpath).get("skillName", "").replace("\\", "/").lower()
            if sn and sn in tree_norm:
                return folder
            # skill button points at a skill in same folder as tree
            if sn and Path(sn).parent.as_posix() in tree_norm:
                return folder
    # Fallback: playerclassNN -> classNN
    m = re.search(r"playerclass(\d{2})", tree_norm)
    if m:
        cand = ui_root / f"class{m.group(1)}"
        if cand.is_dir():
            return cand
    m = re.search(r"/(zenithclass\d+|ddclass\d+|class[a-z0-9]+)/", tree_norm)
    if m:
        # try ui folder with similar name
        stem = m.group(1)
        for folder in ui_root.iterdir():
            if folder.is_dir() and folder.name.lower() == stem:
                return folder
            if folder.is_dir() and stem.replace("player", "") == folder.name.lower():
                return folder
    return None


def mastery_from_tree(
    mod_db: Path,
    tree_rel: str,
    tags: Dict[str, str],
) -> Optional[dict]:
    tree_path = mod_db / tree_rel.replace("\\", "/")
    if not tree_path.is_file():
        return None
    tree = read_dbr(tree_path)
    skill_names = get_list_field(tree, "skillName")
    ui_folder = find_ui_pane_for_tree(mod_db, tree_rel)
    display_tag = ""
    desc_tag = ""
    skills: List[dict] = []
    mastery_bar: Optional[dict] = None
    positions: Dict[str, dict] = {}

    if ui_folder and (ui_folder / "classtable.dbr").is_file():
        table = read_dbr(ui_folder / "classtable.dbr")
        display_tag = table.get("skillTabTitle", "")
        desc_tag = table.get("skillPaneDescriptionTag", "")
        buttons = [
            b.strip()
            for b in (table.get("tabSkillButtons") or "").split(";")
            if b.strip()
        ]
        ordered_skills: List[str] = []
        for bref in buttons:
            bpath = mod_db / bref.replace("\\", "/")
            if not bpath.is_file():
                continue
            bdata = read_dbr(bpath)
            sn = bdata.get("skillName", "").replace("\\", "/")
            if not sn:
                continue
            ordered_skills.append(sn)
            try:
                positions[sn.lower()] = {
                    "x": float(bdata.get("bitmapPositionX", "0") or 0),
                    "y": float(bdata.get("bitmapPositionY", "0") or 0),
                }
            except ValueError:
                positions[sn.lower()] = {"x": 0, "y": 0}
        if ordered_skills:
            skill_names = ordered_skills

    for sn in skill_names:
        sn_posix = sn.replace("\\", "/")
        sk = skill_record(mod_db / sn_posix, tags, sn_posix)
        if not sk:
            continue
        pos = positions.get(sn_posix.lower())
        if pos:
            sk["uiX"] = pos["x"]
            sk["uiY"] = pos["y"]
        if sk["isMasteryBar"]:
            mastery_bar = sk
        else:
            skills.append(sk)

    mid = ui_folder.name if ui_folder else Path(tree_rel).parent.name
    name = resolve_tag(tags, display_tag) if display_tag else mid
    if name == display_tag or not name:
        # ActorName on tree sometimes holds a label
        name = tree.get("ActorName") or mid

    return {
        "id": mid.lower(),
        "tree": tree_rel.replace("\\", "/"),
        "uiFolder": ui_folder.name if ui_folder else None,
        "nameTag": display_tag,
        "name": name,
        "descTag": desc_tag,
        "description": resolve_tag(tags, desc_tag),
        "masteryBar": mastery_bar,
        "skills": skills,
    }


def build_catalog(mod_db: Path, tags: Dict[str, str], mod_label: str) -> dict:
    pc = mod_db / "records" / "creatures" / "pc" / "malepc01.dbr"
    if not pc.is_file():
        raise FileNotFoundError(f"Missing PC hub: {pc}")
    trees = get_list_field(read_dbr(pc), "skillTree")
    masteries = []
    seen = set()
    for tree_rel in trees:
        m = mastery_from_tree(mod_db, tree_rel, tags)
        if not m:
            continue
        if m["id"] in seen:
            continue
        seen.add(m["id"])
        masteries.append(m)

    # Combo class names (tagSkillClassNameXY)
    combos = {
        k: v
        for k, v in tags.items()
        if k.lower().startswith("tagskillclassname") and len(k) >= len("tagSkillClassName") + 2
    }

    return {
        "mod": mod_label,
        "sourceDb": str(mod_db),
        "masteryCount": len(masteries),
        "skillPointBudgetDefault": 202,
        "notes": (
            "Skill points include mastery-bar ranks. Default budget ≈ level 100 + quest skill rewards; "
            "adjust in the planner UI. Ultimate ranks use skillUltimateLevel when above skillMaxLevel."
        ),
        "masteries": masteries,
        "comboNames": combos,
    }


def write_catalog(catalog: dict, out_dir: Path) -> Tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "catalog.json"
    js_path = out_dir / "catalog_data.js"
    text = json.dumps(catalog, indent=2, ensure_ascii=False)
    json_path.write_text(text, encoding="utf-8")
    js_path.write_text(
        "window.PLANNER_CATALOG = " + text + ";\n",
        encoding="utf-8",
    )
    return json_path, js_path


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Export combined-mod build planner catalog")
    p.add_argument("--game", default=None)
    p.add_argument(
        "--mod",
        default="SurvivalPlayground",
        help="Custom Game / mod folder name under mods/",
    )
    p.add_argument(
        "--mod-db",
        default=None,
        help="Explicit path to unpacked database/ (overrides --mod)",
    )
    p.add_argument(
        "--out",
        default=None,
        help="Output directory (default: Tools/GrimDawn/planner/data)",
    )
    p.add_argument("--skip-tag-extract", action="store_true")
    args = p.parse_args(argv)

    game = GamePaths(resolve_game_dir(args.game))
    game.validate()

    if args.mod_db:
        mod_db = Path(args.mod_db)
        label = mod_db.parent.name if mod_db.name.lower() == "database" else mod_db.name
    else:
        mod_root = game.mods_dir / args.mod
        mod_db = mod_root / "database"
        label = args.mod
    if not mod_db.is_dir():
        print(f"Mod database not found: {mod_db}", file=sys.stderr)
        print("Build SurvivalPlayground first (patch_survival_classes.py).", file=sys.stderr)
        return 1

    tag_roots: List[Path] = [mod_db, mod_db.parent / "localization"]
    if not args.skip_tag_extract:
        tag_roots.append(ensure_game_tags(game))
    elif TAG_CACHE.is_dir():
        tag_roots.append(TAG_CACHE)

    # Also pull tags from source mods if present (Grimarillion etc.)
    for extra in ("grimarillion", "Rebirth", "dom"):
        for cand in game.mods_dir.rglob(extra):
            if cand.is_dir() and (cand / "database").is_dir():
                tag_roots.append(cand / "database")
                break
            if cand.name.lower() == "database" and cand.parent.name.lower() == extra:
                tag_roots.append(cand)
                break

    print("Loading tags ...", flush=True)
    tags = load_all_tags(tag_roots)
    print(f"Tags loaded: {len(tags)}", flush=True)

    print(f"Scanning masteries in {mod_db} ...", flush=True)
    catalog = build_catalog(mod_db, tags, label)
    out_dir = Path(args.out) if args.out else (PLANNER_DIR / "data")
    jp, jsp = write_catalog(catalog, out_dir)
    print(f"Masteries: {catalog['masteryCount']}", flush=True)
    print(f"Wrote {jp}", flush=True)
    print(f"Wrote {jsp}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
