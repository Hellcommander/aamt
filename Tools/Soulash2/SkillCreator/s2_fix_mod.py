#!/usr/bin/env python3
"""Upgrade outdated Soulash 2 workshop mods to the live 0.10 JSON contract.

Safe mechanical fixes only: game_required, icon.png, amplifiers filename,
only_party -> apply_mode, passive/amplifier encoding, 0.10 building fields,
orphan consumer / missing experience_gainer. Does not invent .smap maps,
does not copy particles32, does not install into data/mods/.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from s2_assets import _rgb, write_icon_png
from s2_buildings import (
    GAME_REQUIRED,
    KNOWN_WORKSHOP,
    TRAIN_OPTION,
    _ensure_vampire_worker,
    _load_json,
    _write_json,
    fix_building,
    fix_occupation_entity,
    is_player_building,
    resolve_workshop_mod,
    scan_mod_folder,
    upgrade_mod_folder,
)
from s2_fix_sfts import fix_sfts_mod, is_sfts_mod, scan_sfts
from s2_fix_workshop import (
    drop_protected_atlases,
    expand_steal_atlases,
    fix_content_mod,
    restamp_item_art,
    scan_content_mod,
    tiny_steal_present,
    TINY_ATLAS_CELLS,
    _sheet_cells,
    _vanilla_atlas_cells,
)
from s2_paths import core2_dir, mods_dir, output_root, skip_mod_path, workshop_root
from s2_planner import enabled_mod_ids, resolve_mod
from s2_races import make_control_action

AMP_BONUS_TO_FIELD = {
    "stamina_cost": "cost_stamina",
    "range": "range",
    "cooldown": "cooldown",
    "duration": "duration",
    "cast_time": "cast_time",
}

SPECIAL_BUILDING_IDS = set(KNOWN_WORKSHOP.values())
VANILLA_FILL_KEYS = ("occupation_image", "produces", "occupation_per_race", "allow_player", "race")


def _as_rows(data: Any) -> List[Any]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def _load_optional(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return _load_json(path)
    except Exception:
        return None


def _core_building(building_id: str) -> Optional[Dict[str, Any]]:
    wanted = str(building_id).strip()
    bdir = core2_dir() / "buildings"
    if not bdir.is_dir():
        return None
    for path in bdir.glob("*.json"):
        try:
            data = _load_json(path)
        except Exception:
            continue
        if isinstance(data, dict) and str(data.get("id") or path.stem) == wanted:
            return data
    return None


def iter_workshop_mods() -> List[Path]:
    ws = workshop_root()
    if not ws or not ws.is_dir():
        return []
    out: List[Path] = []
    for folder in sorted(ws.iterdir()):
        if not folder.is_dir() or skip_mod_path(folder):
            continue
        if (folder / "mod.json").is_file():
            out.append(folder)
    return out


def iter_enabled_mods(*, include_local: bool = True) -> List[Path]:
    out: List[Path] = []
    seen = set()
    for mid in enabled_mod_ids():
        if mid == "core_2":
            continue
        folder = resolve_mod(mid)
        if folder is None or skip_mod_path(folder):
            continue
        if not include_local and mods_dir() in folder.parents:
            # workshop copies only: skip data/mods overlays
            if workshop_root() is None or not str(folder).startswith(str(workshop_root())):
                continue
        key = str(folder.resolve())
        if key in seen:
            continue
        seen.add(key)
        out.append(folder)
    return out


def resolve_fix_targets(
    names: Sequence[str],
    *,
    workshop: bool = False,
    enabled: bool = False,
) -> List[Path]:
    if names:
        out: List[Path] = []
        for name in names:
            p = Path(name)
            if p.is_dir() and (p / "mod.json").is_file():
                if skip_mod_path(p):
                    continue
                out.append(p.resolve())
                continue
            folder = resolve_mod(name)
            if folder is None:
                folder = resolve_workshop_mod(name)
            if skip_mod_path(folder):
                continue
            out.append(folder)
        return out
    if enabled and not workshop:
        return iter_enabled_mods()
    return iter_workshop_mods()


def copy_mod_to_fixed(src: Path) -> Path:
    """Snapshot a workshop folder under Output/Soulash2/_fixed/<id>/."""
    src = Path(src)
    dest = output_root() / "_fixed" / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("skill.json"))
    return dest


def scan_outdated_mod(folder: Path) -> List[str]:
    folder = Path(folder)
    issues = list(scan_mod_folder(folder))
    has_trainer = False
    bdir = folder / "buildings"
    if bdir.is_dir():
        for path in bdir.glob("*.json"):
            data = _load_optional(path)
            if isinstance(data, dict) and is_player_building(data) and data.get("enables"):
                has_trainer = True
                break
    skill_ids = {
        str(row.get("id"))
        for row in _as_rows(_load_optional(folder / "skills.json"))
        if isinstance(row, dict) and row.get("id")
    }
    kept: List[str] = []
    for line in issues:
        if "begin_conversation missing" in line and TRAIN_OPTION in line:
            cid = line.split(":", 1)[0]
            if "child" in cid.lower():
                continue
            stem = cid.lower().replace("_begin", "").rstrip("_")
            skillish = any(sid and (cid == f"{sid}_begin" or str(sid).startswith(stem) or stem.startswith(str(sid))) for sid in skill_ids)
            if not has_trainer and not skillish:
                continue
        kept.append(line)
    issues = kept
    mj = folder / "mod.json"
    mod = _load_optional(mj) or {}
    if isinstance(mod, dict):
        icon = str(mod.get("icon") or "")
        if icon in ("", "S.png", "S2.png"):
            issues.append(f"mod.json icon={icon or '(empty)'} (want icon.png)")
        elif icon and not (folder / icon).is_file() and not (folder / "icon.png").is_file():
            issues.append(f"mod.json icon file missing: {icon}")
    old_amps = folder / "amplifiers.json"
    new_amps = folder / "ability_amplifiers.json"
    if not (folder / "assets.json").is_file():
        issues.append("assets.json missing (0.10 always opens it)")
    for name in ("mod.json", "skills.json", "character.json", "locations.json", "assets.json"):
        path = folder / name
        if not path.is_file():
            continue
        try:
            json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            issues.append(f"{name}: JSON parse error line {exc.lineno}: {exc.msg}")
    if old_amps.is_file() and not new_amps.is_file():
        issues.append("amplifiers.json should be ability_amplifiers.json")
    passives = _load_optional(folder / "passives.json")
    for row in _as_rows(passives):
        if not isinstance(row, dict):
            continue
        pid = row.get("id") or "?"
        if "only_party" in row:
            issues.append(f"{pid}: only_party is obsolete (use apply_mode)")
        for fx in row.get("effects") or []:
            if isinstance(fx, dict) and fx.get("effect") == "movement_speed":
                issues.append(f"{pid}: passive movement_speed should be move_speed")
    amp_path = new_amps if new_amps.is_file() else old_amps
    amps = _load_optional(amp_path)
    for row in _as_rows(amps):
        if not isinstance(row, dict):
            continue
        aid = row.get("id") or "?"
        for bonus in row.get("bonuses") or []:
            if not isinstance(bonus, dict):
                continue
            eid = str(bonus.get("effect") or "")
            if eid in AMP_BONUS_TO_FIELD:
                issues.append(f"{aid}: amplifier bonus {eid} should be top-level {AMP_BONUS_TO_FIELD[eid]}")
            if eid == "move_speed":
                issues.append(f"{aid}: amplifier move_speed should be movement_speed")
    assets = _load_optional(folder / "assets.json") or {}
    sheets = ((assets.get("graphics") or {}).get("tilesheets") or []) if isinstance(assets, dict) else []
    protected = {"particles32", "items", "glyph32", "buildings"}
    vanilla_cells = _vanilla_atlas_cells()
    for sheet in sheets:
        if not isinstance(sheet, dict):
            continue
        name = str(sheet.get("name") or "")
        if name not in protected:
            continue
        cells = _sheet_cells(sheet)
        limit = max(TINY_ATLAS_CELLS, vanilla_cells.get(name, TINY_ATLAS_CELLS))
        if cells < limit:
            issues.append(
                f"assets.json overlays tiny {name} ({cells} cells; expand onto a full vanilla clone)"
            )
    char = _load_optional(folder / "character.json")
    have_actions = {
        str(a.get("id"))
        for a in _as_rows((char or {}).get("control_actions") if isinstance(char, dict) else [])
        if isinstance(a, dict) and a.get("id")
    }
    miles = folder / "milestones"
    if miles.is_dir():
        for path in miles.rglob("*.json"):
            if "translations" in path.parts:
                continue
            row = _load_optional(path)
            if not isinstance(row, dict):
                continue
            for reward in row.get("rewards") or []:
                if not isinstance(reward, dict) or "control_action" not in reward:
                    continue
                cid = str(reward.get("control_action") or "")
                if cid and not cid.startswith("core_2_") and cid not in have_actions:
                    issues.append(f"{row.get('id')}: control_action {cid} missing from character.json")
    if is_sfts_mod(folder):
        issues.extend(scan_sfts(folder))
    issues.extend(scan_content_mod(folder))
    return issues


def _fix_mod_json(folder: Path) -> List[str]:
    notes: List[str] = []
    mj = folder / "mod.json"
    if not mj.is_file():
        return notes
    try:
        mod = _load_json(mj)
    except Exception:
        return notes
    if not isinstance(mod, dict):
        return notes
    changed = False
    required = str(mod.get("game_required") or "")
    if required != GAME_REQUIRED:
        mod["game_required"] = GAME_REQUIRED
        notes.append(f"game_required={GAME_REQUIRED}")
        changed = True
    icon = str(mod.get("icon") or "")
    if icon in ("", "S.png", "S2.png") or not (folder / icon).is_file():
        dest = folder / "icon.png"
        src = folder / icon if icon and (folder / icon).is_file() else None
        if src and src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
            notes.append(f"copied {icon} -> icon.png")
        elif not dest.is_file():
            write_icon_png(dest, _rgb(str(mod.get("name") or folder.name)))
            notes.append("wrote placeholder icon.png")
        if icon != "icon.png":
            mod["icon"] = "icon.png"
            notes.append("icon=icon.png")
            changed = True
    if changed:
        _write_json(mj, mod)
    return notes


# Vanilla atlas names. Auto-registering a workshop PNG under these names
# replaces core_2 art for the whole game. Unique stems (darkenarcane_items)
# are kept. A patch with no custom sheets still needs assets.json: tilesheets [].
_VANILLA_SHEET_NAMES = {
    "abilities",
    "amplifiers",
    "buildings",
    "glyph32",
    "glyphs",
    "items",
    "particles32",
    "passive_skills",
    "skills",
    "stackers",
}


def _png_size(path: Path) -> Optional[Tuple[int, int]]:
    with path.open("rb") as fh:
        if fh.read(8) != b"\x89PNG\r\n\x1a\n":
            return None
        length = int.from_bytes(fh.read(4), "big")
        if fh.read(4) != b"IHDR" or length < 8:
            return None
        width = int.from_bytes(fh.read(4), "big")
        height = int.from_bytes(fh.read(4), "big")
        return width, height


def _discover_custom_sheets(folder: Path) -> List[Dict[str, Any]]:
    """Tilesheets for PNGs this mod actually ships under assets/. Not icons."""
    root = folder / "assets"
    if not root.is_dir():
        return []
    sheets: List[Dict[str, Any]] = []
    for png in sorted(root.rglob("*.png")):
        name = png.stem.lower()
        if name in _VANILLA_SHEET_NAMES:
            continue
        size = _png_size(png)
        if not size:
            continue
        cols = max(1, size[0] // 32)
        rows = max(1, size[1] // 32)
        rel = png.relative_to(folder).as_posix()
        sheets.append({"name": png.stem, "tiles": [cols, rows], "file": rel})
    return sheets


def _ensure_assets_json(folder: Path) -> List[str]:
    path = folder / "assets.json"
    if path.is_file():
        return []
    sheets = _discover_custom_sheets(folder)
    _write_json(path, {"graphics": {"tilesheets": sheets}})
    if sheets:
        names = ", ".join(s["name"] for s in sheets)
        return [f"wrote assets.json tilesheets: {names}"]
    return ["wrote assets.json (no custom tilesheets; vanilla atlases stay)"]


def _fix_skills_json_parse(folder: Path) -> List[str]:
    path = folder / "skills.json"
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8-sig")
    try:
        json.loads(text)
        return []
    except json.JSONDecodeError:
        pass
    patched = text.replace('"start_level": 1\n        "disabled"', '"start_level": 1,\n        "disabled"')
    try:
        json.loads(patched)
    except json.JSONDecodeError:
        return ["skills.json unparseable (left as-is)"]
    if patched == text:
        return ["skills.json unparseable (left as-is)"]
    path.write_text(patched, encoding="utf-8")
    return ["skills.json: inserted missing comma"]


def _fix_amplifiers_filename(folder: Path) -> List[str]:
    old = folder / "amplifiers.json"
    new = folder / "ability_amplifiers.json"
    if old.is_file() and not new.is_file():
        old.rename(new)
        return ["renamed amplifiers.json -> ability_amplifiers.json"]
    return []


def _fix_passives_file(folder: Path) -> List[str]:
    path = folder / "passives.json"
    data = _load_optional(path)
    if data is None:
        return []
    notes: List[str] = []
    changed = False
    for row in _as_rows(data):
        if not isinstance(row, dict):
            continue
        pid = row.get("id") or "?"
        if "only_party" in row:
            val = row.pop("only_party")
            if val and not row.get("apply_mode"):
                row["apply_mode"] = "party_only"
                notes.append(f"{pid}: only_party -> apply_mode=party_only")
            else:
                notes.append(f"{pid}: removed only_party")
            changed = True
        for fx in row.get("effects") or []:
            if isinstance(fx, dict) and fx.get("effect") == "movement_speed":
                fx["effect"] = "move_speed"
                notes.append(f"{pid}: movement_speed -> move_speed")
                changed = True
    if changed:
        _write_json(path, data)
    return notes


def _fix_amplifier_encoding(folder: Path) -> List[str]:
    path = folder / "ability_amplifiers.json"
    if not path.is_file():
        path = folder / "amplifiers.json"
    data = _load_optional(path)
    if data is None:
        return []
    notes: List[str] = []
    changed = False
    for row in _as_rows(data):
        if not isinstance(row, dict):
            continue
        aid = row.get("id") or "?"
        kept: List[Any] = []
        for bonus in row.get("bonuses") or []:
            if not isinstance(bonus, dict):
                kept.append(bonus)
                continue
            eid = str(bonus.get("effect") or "")
            field = AMP_BONUS_TO_FIELD.get(eid)
            if field:
                if field not in row:
                    row[field] = bonus.get("value")
                notes.append(f"{aid}: bonus {eid} -> {field}")
                changed = True
                continue
            if eid == "move_speed":
                bonus["effect"] = "movement_speed"
                notes.append(f"{aid}: move_speed -> movement_speed")
                changed = True
            kept.append(bonus)
        if changed:
            row["bonuses"] = kept
    if changed:
        _write_json(path, data)
    return notes


def _fill_building_from_vanilla(building: Dict[str, Any]) -> List[str]:
    notes: List[str] = []
    bid = str(building.get("id") or "")
    if not bid.isdigit():
        return notes
    vanilla = _core_building(bid)
    if not vanilla:
        return notes
    for key in VANILLA_FILL_KEYS:
        if key == "occupation_per_race":
            opr = building.setdefault("occupation_per_race", {})
            src = vanilla.get("occupation_per_race") or {}
            if isinstance(opr, dict) and isinstance(src, dict):
                for rk, rv in src.items():
                    if rk not in opr:
                        opr[rk] = rv
                        notes.append(f"{bid}: occupation_per_race.{rk} from vanilla")
            continue
        if key not in building and key in vanilla:
            building[key] = vanilla[key]
            notes.append(f"{bid}: {key} from vanilla")
    return notes


def _fix_generic_buildings(folder: Path) -> List[str]:
    notes: List[str] = []
    bdir = folder / "buildings"
    has_trainer = False
    if bdir.is_dir():
        for path in sorted(bdir.glob("*.json")):
            data = _load_optional(path)
            if not isinstance(data, dict):
                continue
            bnotes = _fill_building_from_vanilla(data)
            bnotes.extend(fix_building(data))
            if is_player_building(data) and data.get("enables"):
                has_trainer = True
            if is_player_building(data) and "6" not in (data.get("occupation_per_race") or {}):
                occ0 = str((data.get("occupation_per_race") or {}).get("0") or data.get("occupation") or "")
                if occ0 and not occ0.isdigit() and not occ0.startswith("core_2_"):
                    vnotes = _ensure_vampire_worker(
                        folder,
                        data,
                        new_id=f"{occ0}_Vampire",
                        name=f"Vampire {data.get('name') or occ0}",
                        source_id=occ0,
                    )
                    bnotes.extend(vnotes)
            if bnotes:
                _write_json(path, data)
                notes.append(f"{path.name}: {', '.join(bnotes)}")
    edir = folder / "entities"
    if edir.is_dir():
        for path in sorted(edir.glob("*.json")):
            ent = _load_optional(path)
            if not isinstance(ent, dict):
                continue
            enotes = fix_occupation_entity(ent)
            if enotes:
                _write_json(path, ent)
                notes.append(f"{path.name}: {', '.join(enotes)}")
    if has_trainer or (folder / "skills.json").is_file():
        conv_path = folder / "conversations.json"
        conv = _load_optional(conv_path)
        skill_ids = set()
        skills = _load_optional(folder / "skills.json")
        for row in _as_rows(skills):
            if isinstance(row, dict) and row.get("id"):
                skill_ids.add(str(row["id"]))
        if isinstance(conv, dict):
            cnotes: List[str] = []
            for row in conv.get("conversations") or []:
                if not isinstance(row, dict) or row.get("type") != "begin_conversation":
                    continue
                cid = str(row.get("id") or "")
                if "child" in cid.lower():
                    continue
                trainerish = has_trainer and ("_begin" in cid.lower() or "train" in cid.lower())
                stem = cid.lower().replace("_begin", "").rstrip("_")
                skillish = any(
                    sid and (cid == f"{sid}_begin" or cid.startswith(f"{sid}_") or str(sid).startswith(stem) or stem.startswith(str(sid)))
                    for sid in skill_ids
                )
                if not trainerish and not skillish:
                    continue
                opts = row.setdefault("options", [])
                if TRAIN_OPTION not in opts:
                    insert_at = next((i for i, o in enumerate(opts) if "exit" in str(o)), len(opts))
                    opts.insert(insert_at, TRAIN_OPTION)
                    cnotes.append(f"{cid}: {TRAIN_OPTION}")
            if cnotes:
                _write_json(conv_path, conv)
                notes.extend(cnotes)
    return notes


def _fix_missing_control_actions(folder: Path) -> List[str]:
    notes: List[str] = []
    char_path = folder / "character.json"
    data = _load_optional(char_path)
    if not isinstance(data, dict):
        data = {}
    actions = data.setdefault("control_actions", [])
    if not isinstance(actions, list):
        actions = []
        data["control_actions"] = actions
    have = {str(a.get("id")) for a in actions if isinstance(a, dict) and a.get("id")}
    needed: List[Tuple[str, str]] = []
    miles = folder / "milestones"
    if miles.is_dir():
        for path in miles.rglob("*.json"):
            if "translations" in path.parts:
                continue
            row = _load_optional(path)
            if not isinstance(row, dict):
                continue
            for reward in row.get("rewards") or []:
                if isinstance(reward, dict) and reward.get("control_action"):
                    cid = str(reward["control_action"])
                    if cid and not cid.startswith("core_2_"):
                        needed.append((cid, str(row.get("name") or cid)))
    for cid, name in needed:
        if cid in have:
            continue
        actions.append(
            make_control_action(
                action_id=cid,
                name=name.replace("_", " ").title(),
                tags=["2"],
                clone_from="core_2_tame",
            )
        )
        have.add(cid)
        notes.append(f"character.json control_action {cid}")
    if notes:
        _write_json(char_path, data)
    return notes


def upgrade_outdated_mod(folder: Path) -> List[str]:
    folder = Path(folder)
    notes: List[str] = []
    if folder.name in SPECIAL_BUILDING_IDS:
        notes.extend(upgrade_mod_folder(folder))
    else:
        notes.extend(_fix_mod_json(folder))
        notes.extend(_fix_generic_buildings(folder))
    notes.extend(_ensure_assets_json(folder))
    notes.extend(_fix_skills_json_parse(folder))
    notes.extend(_fix_amplifiers_filename(folder))
    notes.extend(_fix_passives_file(folder))
    notes.extend(_fix_amplifier_encoding(folder))
    notes.extend(_fix_missing_control_actions(folder))
    if is_sfts_mod(folder):
        notes.extend(fix_sfts_mod(folder))
    notes.extend(fix_content_mod(folder))
    notes.extend(expand_steal_atlases(folder))
    steal_items = tiny_steal_present(folder)
    notes.extend(drop_protected_atlases(folder))
    notes.extend(restamp_item_art(folder, remap_custom=steal_items))
    if folder.name in SPECIAL_BUILDING_IDS:
        # specialized upgrade already rewrote mod.json; still fix S.png
        extra = _fix_mod_json(folder)
        notes.extend(extra)
    return notes


def summarize_scan(issues: Sequence[str]) -> str:
    if not issues:
        return "ok"
    auto = [i for i in issues if not i.startswith("assets.json overlays particles32")]
    return f"{len(issues)} issue(s)" + ("" if auto else " (warn-only)")
