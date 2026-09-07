#!/usr/bin/env python3
"""Apply core2_asset_references.json image indices to arendeth_water_magic mod JSON files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def load_map(mod_path: Path) -> Dict[str, Any]:
    ref_path = mod_path / "core2_asset_references.json"
    if not ref_path.exists():
        raise FileNotFoundError(f"Missing {ref_path}")
    with open(ref_path, encoding="utf-8") as f:
        return json.load(f)


def patch_json_file(path: Path, image: int, extra: Dict[str, Any] | None = None) -> bool:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    changed = False
    if data.get("image") != image:
        data["image"] = image
        changed = True
    if extra:
        for key, val in extra.items():
            if data.get(key) != val:
                data[key] = val
                changed = True
    if changed:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent="\t")
            f.write("\n")
    return changed


def patch_skill(mod_path: Path, refs: Dict[str, Any]) -> int:
    skill_path = mod_path / "skills.json"
    with open(skill_path, encoding="utf-8") as f:
        skills = json.load(f)
    count = 0
    skill_refs = refs.get("skill", {})
    for skill in skills:
        sid = skill.get("id")
        if sid not in skill_refs:
            continue
        ref = skill_refs[sid]
        changed = False
        if skill.get("image") != ref["image"]:
            skill["image"] = ref["image"]
            changed = True
        if "animation" in ref and skill.get("animation") != ref["animation"]:
            skill["animation"] = ref["animation"]
            changed = True
        if changed:
            count += 1
    if count:
        with open(skill_path, "w", encoding="utf-8") as f:
            json.dump(skills, f, indent="    ")
            f.write("\n")
    return count


def patch_abilities(mod_path: Path, refs: Dict[str, Any]) -> int:
    count = 0
    ability_refs = refs.get("abilities", {})
    for path in (mod_path / "abilities").glob("*.json"):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        aid = data.get("id")
        if aid not in ability_refs:
            continue
        img = ability_refs[aid]["image"]
        if patch_json_file(path, img):
            count += 1
    return count


def patch_passives(mod_path: Path, refs: Dict[str, Any]) -> int:
    passive_path = mod_path / "passives.json"
    with open(passive_path, encoding="utf-8") as f:
        passives = json.load(f)
    count = 0
    pref = refs.get("passives", {})
    for p in passives:
        pid = p.get("id")
        if pid in pref and p.get("image") != pref[pid]["image"]:
            p["image"] = pref[pid]["image"]
            count += 1
    if count:
        with open(passive_path, "w", encoding="utf-8") as f:
            json.dump(passives, f, indent="    ")
            f.write("\n")
    return count


def patch_buildings(mod_path: Path, refs: Dict[str, Any]) -> int:
    count = 0
    brefs = refs.get("buildings", {})
    for path in (mod_path / "buildings").glob("*.json"):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        bid = data.get("id")
        if bid not in brefs:
            continue
        ref = brefs[bid]
        extra = {}
        if "occupation_image" in ref:
            extra["occupation_image"] = ref["occupation_image"]
        if patch_json_file(path, ref["image"], extra):
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply core_2 asset references to hydromancy mod")
    parser.add_argument(
        "--mod-path",
        type=Path,
        default=Path(r"E:\SteamLibrary\steamapps\common\Soulash 2\data\mods\arendeth_water_magic"),
    )
    args = parser.parse_args()
    mod_path = args.mod_path.resolve()
    refs = load_map(mod_path)

    total = 0
    total += patch_skill(mod_path, refs)
    total += patch_abilities(mod_path, refs)
    total += patch_passives(mod_path, refs)
    total += patch_buildings(mod_path, refs)

    print(f"[OK] Updated {total} JSON file(s) in {mod_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
