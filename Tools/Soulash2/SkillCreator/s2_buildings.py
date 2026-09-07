#!/usr/bin/env python3
"""Player-settlement buildings for Soulash 2 skill mods (0.10.x).

Clone Collegium / Dojo / ranch templates, emit `enables` for skill training, and
upgrade 0.9.x workshop buildings that are missing occupation_image, vampire race
\"6\", produces, train conversations, and occupation NPC load fields.

Do not invent .smap maps. Copy existing maps only.
"""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from s2_paths import core2_dir, output_root, skip_mod_path, workshop_root
from s2_schema import slug_name

SPEC_ONLY_KEYS = ("_file", "_cloned_from", "_source")

# Playable races that vanilla player buildings map in occupation_per_race.
# Skeleton 17 is not on those maps. Vampire 6 was added in 0.10.
PLAYER_OCCUPATION_RACES = (
    "0",
    "1",
    "2",
    "4",
    "6",
    "7",
    "8",
    "10",
    "23",
    "26",
    "31",
    "32",
    "33",
)

TEMPLATES = {
    "magic": "389",
    "combat": "387",
    "farm": "404",
}

KNOWN_WORKSHOP = {
    "officers": "3525259869",
    "officers!": "3525259869",
    "battlemages": "3525970281",
    "silkworm": "3558726977",
    "silkworm farm": "3558726977",
    "silkworm_farm": "3558726977",
    "soup": "3317585513",
    "soup for the soulash": "3317585513",
    "sfts": "3317585513",
    "sfts buildings": "3328313908",
    "soup buildings": "3328313908",
    "miningplus": "3352367788",
    "mining plus": "3352367788",
    "darken": "3229736001",
    "arcane materials": "3229736001",
    "natural resource plus": "3559400101",
    "nrp": "3559400101",
    "better weaponsmith": "3557698099",
    "sandmancy": "3736940267",
    "draken": "3509134344",
    "draken races": "3509134344",
    "draken races extended": "3509134344",
}

VANILLA_RANCHER = {
    "0": "2265",
    "1": "2267",
    "2": "2285",
    "4": "core_2_Goblin_Rancher",
    "6": "core_2_Vampire_Rancher",
    "7": "core_2_Troll_Rancher",
    "8": "core_2_Orc_Rancher",
    "10": "2326",
    "23": "core_2_Reptilion_Rancher",
    "26": "2370",
    "31": "core_2_Gnoll_Rancher",
    "32": "core_2_Mushman_Farmer",
    "33": "core_2_Ursan_Rancher",
}

VANILLA_FARMER = {
    "0": "203",
    "1": "2276",
    "2": "2285",
    "4": "core_2_Goblin_Farmer",
    "6": "core_2_Vampire_Farmer",
    "7": "core_2_Troll_Farmer",
    "8": "core_2_Orc_Farmer",
    "10": "2332",
    "23": "core_2_Reptilion_Farmer",
    "26": "2370",
    "31": "core_2_Gnoll_Farmer",
    "32": "core_2_Mushman_Farmer",
    "33": "core_2_Ursan_Farmer",
}

VANILLA_WIZARD = {
    "0": "457",
    "1": "core_2_Dwarf_Wizard",
    "2": "core_2_Elf_Wizard",
    "4": "core_2_Goblin_Wizard",
    "6": "core_2_Vampire_Wizard",
    "7": "core_2_Troll_Wizard",
    "8": "core_2_Orc_Wizard",
    "10": "core_2_Rasimi_Wizard",
    "23": "core_2_Reptilion_Wizard",
    "26": "core_2_Bone_Wraith_Wizard",
    "31": "core_2_Gnoll_Wizard",
    "32": "core_2_Mushman_Wizard",
    "33": "core_2_Ursan_Wizard",
}

OCCUPATION_IMAGE = {
    "magic": 74,
    "combat": 97,
    "military": 97,
    "farm": 28,
    "rancher": 28,
    "food": 94,
    "resources": 28,
    "guard": 20,
}

DEFAULT_EXPERIENCE_GAINER = {"exp": 0, "level": 4}
VAMPIRE_TINT = [187, 93, 191]
TRAIN_OPTION = "core_2_train_1"
GAME_REQUIRED = "0.10.0"


def _dump(obj: Any) -> str:
    return json.dumps(obj, indent="\t", ensure_ascii=False) + "\n"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def public_building(building: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in building.items() if k not in SPEC_ONLY_KEYS}


def building_filename(building: Dict[str, Any]) -> str:
    if building.get("_file"):
        return str(building["_file"])
    return f"{slug_name(building.get('name') or building['id'])}.json"


def _iter_building_files() -> Iterable[Tuple[str, Path]]:
    core = core2_dir() / "buildings"
    if core.is_dir():
        for path in core.glob("*.json"):
            yield "core_2", path
    ws = workshop_root()
    if not ws:
        return
    for mod in sorted(ws.iterdir()):
        if not mod.is_dir() or skip_mod_path(mod):
            continue
        folder = mod / "buildings"
        if not folder.is_dir():
            continue
        for path in folder.glob("*.json"):
            yield mod.name, path


def search_buildings(query: str, limit: int = 40) -> List[Dict[str, Any]]:
    q = (query or "").strip().lower()
    if len(q) < 2 and not q.isdigit():
        return []
    hits: List[Dict[str, Any]] = []
    for source, path in _iter_building_files():
        try:
            data = _load_json(path)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        bid = str(data.get("id") or path.stem)
        name = str(data.get("name") or "")
        enables = " ".join(str(x) for x in (data.get("enables") or []))
        hay = " ".join((bid, name, path.stem, enables, str(data.get("group") or ""))).lower()
        if q not in hay:
            continue
        hits.append(
            {
                "id": bid,
                "name": name or bid,
                "source": source,
                "file": str(path),
                "allow_player": bool(data.get("allow_player")),
                "enables": list(data.get("enables") or []),
                "group": data.get("group"),
                "occupation_image": data.get("occupation_image"),
            }
        )
        if len(hits) >= limit:
            break
    return hits


def load_building(building_id: str) -> Dict[str, Any]:
    wanted = str(building_id).strip()
    stem_hits: List[Path] = []
    for source, path in _iter_building_files():
        if wanted.lower() in path.stem.lower() or path.stem == wanted:
            stem_hits.append(path)
    for path in stem_hits:
        try:
            data = _load_json(path)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        if str(data.get("id")) == wanted or path.stem == wanted:
            data["_cloned_from"] = str(path)
            data["_file"] = path.name
            data["_source"] = path.parent.parent.name
            return data
        if str(data.get("name") or "").lower() == wanted.lower():
            data["_cloned_from"] = str(path)
            data["_file"] = path.name
            data["_source"] = path.parent.parent.name
            return data
    for source, path in _iter_building_files():
        try:
            data = _load_json(path)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        if str(data.get("id")) == wanted or str(data.get("name") or "").lower() == wanted.lower():
            data["_cloned_from"] = str(path)
            data["_file"] = path.name
            data["_source"] = source
            return data
    raise FileNotFoundError(f"Building not found: {building_id}")


def clone_building(
    source_id: str,
    *,
    new_id: str,
    name: Optional[str] = None,
    enables: Optional[List[str]] = None,
) -> Dict[str, Any]:
    row = deepcopy(load_building(source_id))
    row["id"] = new_id
    if name:
        row["name"] = name
    if enables is not None:
        row["enables"] = list(enables)
    row.pop("_file", None)
    return row


def guess_occupation_image(building: Dict[str, Any]) -> int:
    group = str(building.get("group") or "").lower()
    name = str(building.get("name") or "").lower()
    enables = " ".join(str(x) for x in (building.get("enables") or [])).lower()
    if "ranch" in name or "silk" in name or group == "resources":
        return OCCUPATION_IMAGE["rancher"]
    if group == "food" or "garden" in name or "farm" in name:
        return OCCUPATION_IMAGE["food"]
    if "pyromancy" in enables or "cryomancy" in enables or "collegium" in name or "wizard" in name:
        return OCCUPATION_IMAGE["magic"]
    if group in ("military", "militaryofficer") or building.get("type") == "military":
        return OCCUPATION_IMAGE["combat"]
    return OCCUPATION_IMAGE["guard"]


def _occupation_family(building: Dict[str, Any]) -> str:
    opr = building.get("occupation_per_race") or {}
    values = {str(v) for v in opr.values()}
    blob = " ".join(values).lower()
    if values & set(VANILLA_RANCHER.values()) or "rancher" in blob:
        return "rancher"
    if values & set(VANILLA_FARMER.values()) or "farmer" in blob:
        return "farmer"
    if values & set(VANILLA_WIZARD.values()) or "wizard" in blob:
        return "wizard"
    if "samurai" in blob:
        return "samurai"
    group = str(building.get("group") or "").lower()
    name = str(building.get("name") or "").lower()
    hay = f"{group} {name} {building.get('id') or ''}".lower()
    if group in ("food",) or any(w in hay for w in ("farm", "bakery", "tavern", "restaurant", "pastry", "fromage", "butcher", "apiary", "windmill", "inn", "trader")):
        return "farmer"
    if group in ("resources",) or any(w in hay for w in ("smelter", "mine", "excavator", "quarry")):
        return "rancher"
    if any(w in hay for w in ("collegium", "temple", "wizard", "mage")):
        return "wizard"
    return "custom"


def vampire_occupation_id(building: Dict[str, Any]) -> Optional[str]:
    """Vanilla vampire worker id when the occupation family is known."""
    family = _occupation_family(building)
    return {
        "rancher": "core_2_Vampire_Rancher",
        "farmer": "core_2_Vampire_Farmer",
        "wizard": "core_2_Vampire_Wizard",
        "samurai": "core_2_Vampire_Samurai",
    }.get(family)


def is_player_building(building: Dict[str, Any]) -> bool:
    if building.get("allow_player"):
        return True
    return str(building.get("race") or "") == "-1"


def _resting_count(building: Dict[str, Any]) -> Optional[int]:
    workers = building.get("workers")
    if isinstance(workers, list) and len(workers) >= 2:
        try:
            return int(workers[1])
        except (TypeError, ValueError):
            return None
    return None


def fix_building(building: Dict[str, Any], *, occupation_image: Optional[int] = None) -> List[str]:
    """Patch a building dict to the 0.10 player-settlement contract. Mutates in place."""
    notes: List[str] = []
    player = is_player_building(building)
    if player:
        if not building.get("allow_player"):
            building["allow_player"] = True
            notes.append("allow_player")
        if str(building.get("race") or "") != "-1":
            building["race"] = "-1"
            notes.append("race=-1")
        if "occupation_image" not in building:
            building["occupation_image"] = int(occupation_image if occupation_image is not None else guess_occupation_image(building))
            notes.append(f"occupation_image={building['occupation_image']}")
        if "produces" not in building:
            building["produces"] = []
            notes.append("produces=[]")
        opr = building.setdefault("occupation_per_race", {})
        if isinstance(opr, dict) and "6" not in opr:
            vid = vampire_occupation_id(building)
            if vid:
                opr["6"] = vid
                notes.append(f"occupation_per_race.6={vid}")
            else:
                notes.append("occupation_per_race.6 missing (needs cloned vampire worker)")
        want_rest = _resting_count(building)
        req = building.get("required_entities")
        if want_rest and isinstance(req, list):
            for slot in req:
                if isinstance(slot, dict) and slot.get("component") == "resting_place":
                    if int(slot.get("count") or 0) != want_rest:
                        slot["count"] = want_rest
                        notes.append(f"resting_place={want_rest}")
                    break
        group = str(building.get("group") or "")
        if group == "militaryofficer":
            building["group"] = "military"
            notes.append("group=military")
    elif "produces" not in building:
        building["produces"] = []
        notes.append("produces=[]")
    return notes


def add_building(spec: Dict[str, Any], building: Dict[str, Any]) -> Dict[str, Any]:
    spec.setdefault("buildings", [])
    building = deepcopy(building)
    bid = building.get("id")
    if not bid:
        raise ValueError("Building needs an id")
    for i, existing in enumerate(spec["buildings"]):
        if existing.get("id") == bid:
            spec["buildings"][i] = building
            return building
    spec["buildings"].append(building)
    return building


def make_training_building(
    *,
    new_id: str,
    name: str,
    skill_id: str,
    template: str = "magic",
) -> Dict[str, Any]:
    source = TEMPLATES.get(template, template)
    row = clone_building(source, new_id=new_id, name=name, enables=[skill_id])
    fix_building(row)
    return row


def fix_occupation_entity(entity: Dict[str, Any]) -> List[str]:
    """Drop orphan consumer; add experience_gainer on actors. Mutates in place."""
    notes: List[str] = []
    comps = list(entity.get("components") or [])
    if "consumer" in comps and "consumer" not in entity:
        comps = [c for c in comps if c != "consumer"]
        notes.append("removed orphan consumer")
    if "actor" in comps and "experience_gainer" not in comps:
        comps.append("experience_gainer")
        entity["experience_gainer"] = dict(DEFAULT_EXPERIENCE_GAINER)
        notes.append("experience_gainer")
    if comps != list(entity.get("components") or []):
        entity["components"] = comps
    return notes


def clone_as_vampire(entity: Dict[str, Any], *, new_id: str, name: str) -> Dict[str, Any]:
    out = deepcopy(entity)
    out["id"] = new_id
    out["name"] = name
    out.setdefault("humanoid", {})["race"] = "6"
    out["corpse"] = "1061"
    out["minimap_pixel"] = list(VAMPIRE_TINT)
    glyph = out.get("glyph")
    if isinstance(glyph, dict):
        frames = glyph.get("frames") or []
        if frames and isinstance(frames[0], dict):
            frames[0]["color"] = list(VAMPIRE_TINT)
    out.pop("_file", None)
    fix_occupation_entity(out)
    return out


def fix_conversations(
    data: Dict[str, Any],
    *,
    extra_entities: Optional[Dict[str, List[str]]] = None,
) -> List[str]:
    notes: List[str] = []
    extra_entities = extra_entities or {}
    rows = data.get("conversations")
    if not isinstance(rows, list):
        return notes
    for row in rows:
        if not isinstance(row, dict) or row.get("type") != "begin_conversation":
            continue
        opts = row.setdefault("options", [])
        if TRAIN_OPTION not in opts:
            insert_at = next((i for i, o in enumerate(opts) if "exit" in str(o)), len(opts))
            opts.insert(insert_at, TRAIN_OPTION)
            notes.append(f"{row.get('id')}: {TRAIN_OPTION}")
        extras = extra_entities.get(str(row.get("id") or ""))
        if extras:
            ents = row.setdefault("entities", [])
            for eid in extras:
                if eid not in ents:
                    ents.append(eid)
                    notes.append(f"{row.get('id')}: entity {eid}")
    return notes


def resolve_workshop_mod(key: str) -> Path:
    raw = str(key).strip()
    ws = workshop_root()
    if not ws:
        raise FileNotFoundError("Workshop folder not found")
    known = KNOWN_WORKSHOP.get(raw.lower())
    if known:
        path = ws / known
        if path.is_dir():
            return path
    direct = Path(raw)
    if direct.is_dir() and (direct / "mod.json").is_file():
        return direct.resolve()
    steam = ws / raw
    if steam.is_dir():
        return steam
    for mod in ws.iterdir():
        if not mod.is_dir() or skip_mod_path(mod):
            continue
        mj = mod / "mod.json"
        if not mj.is_file():
            continue
        try:
            name = str(_load_json(mj).get("name") or "")
        except Exception:
            continue
        if name.lower() == raw.lower():
            return mod
    raise FileNotFoundError(f"Workshop mod not found: {key}")


def output_mod_dir(folder: Path) -> Path:
    mod = {}
    mj = folder / "mod.json"
    if mj.is_file():
        try:
            mod = _load_json(mj)
        except Exception:
            mod = {}
    name = slug_name(mod.get("name") or folder.name).lower()
    return output_root() / name


def scan_building_issues(building: Dict[str, Any]) -> List[str]:
    issues: List[str] = []
    bid = str(building.get("id") or "")
    if not is_player_building(building):
        return issues
    if "occupation_image" not in building:
        issues.append(f"{bid}: missing occupation_image")
    if "produces" not in building:
        issues.append(f"{bid}: missing produces")
    opr = building.get("occupation_per_race") or {}
    if isinstance(opr, dict) and "6" not in opr:
        issues.append(f"{bid}: occupation_per_race missing vampire 6")
    want_rest = _resting_count(building)
    req = building.get("required_entities")
    if want_rest and isinstance(req, list):
        for slot in req:
            if isinstance(slot, dict) and slot.get("component") == "resting_place":
                if int(slot.get("count") or 0) != want_rest:
                    issues.append(f"{bid}: resting_place {slot.get('count')} != workers max {want_rest}")
                break
    if str(building.get("group") or "") == "militaryofficer":
        issues.append(f"{bid}: custom group militaryofficer (vanilla sheet has 6 tiles)")
    return issues


def scan_mod_folder(folder: Path) -> List[str]:
    folder = Path(folder)
    issues: List[str] = []
    mj = folder / "mod.json"
    if mj.is_file():
        try:
            required = str(_load_json(mj).get("game_required") or "")
        except Exception:
            required = ""
        if required and required != GAME_REQUIRED and not required.startswith("0.10"):
            issues.append(f"mod.json game_required={required} (want {GAME_REQUIRED})")
    bdir = folder / "buildings"
    if bdir.is_dir():
        for path in sorted(bdir.glob("*.json")):
            try:
                data = _load_json(path)
            except Exception as exc:
                issues.append(f"{path.name}: unreadable ({exc})")
                continue
            if isinstance(data, dict):
                issues.extend(scan_building_issues(data))
    edir = folder / "entities"
    if edir.is_dir():
        for path in sorted(edir.glob("*.json")):
            try:
                ent = _load_json(path)
            except Exception:
                continue
            if not isinstance(ent, dict):
                continue
            comps = ent.get("components") or []
            eid = ent.get("id") or path.stem
            if "consumer" in comps and "consumer" not in ent:
                issues.append(f"{eid}: consumer component without consumer object")
            if "actor" in comps and "experience_gainer" not in comps:
                issues.append(f"{eid}: actor missing experience_gainer")
            glyph = ent.get("glyph") or {}
            if isinstance(glyph, dict) and glyph.get("frames") == []:
                issues.append(f"{eid}: empty glyph.frames")
    conv = folder / "conversations.json"
    if conv.is_file():
        try:
            data = _load_json(conv)
        except Exception:
            data = {}
        for row in data.get("conversations") or []:
            if row.get("type") == "begin_conversation":
                opts = row.get("options") or []
                if TRAIN_OPTION not in opts:
                    issues.append(f"{row.get('id')}: begin_conversation missing {TRAIN_OPTION}")
    assets = folder / "assets.json"
    if assets.is_file():
        try:
            sheets = ((_load_json(assets).get("graphics") or {}).get("tilesheets") or [])
        except Exception:
            sheets = []
        for sheet in sheets:
            if isinstance(sheet, dict) and sheet.get("name") == "building_groups":
                issues.append("assets.json tilesheet named building_groups (can fight vanilla group icons)")
    return issues


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump(data), encoding="utf-8")


def _load_entity_file(path: Path) -> Optional[Dict[str, Any]]:
    try:
        data = _load_json(path)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _find_entity_in_folder(folder: Path, entity_id: str) -> Optional[Tuple[Path, Dict[str, Any]]]:
    edir = folder / "entities"
    if not edir.is_dir():
        return None
    for path in edir.glob("*.json"):
        data = _load_entity_file(path)
        if data and str(data.get("id")) == entity_id:
            return path, data
    return None


def _ensure_vampire_worker(
    folder: Path,
    building: Dict[str, Any],
    *,
    new_id: str,
    name: str,
    source_id: str,
) -> List[str]:
    notes: List[str] = []
    opr = building.setdefault("occupation_per_race", {})
    if "6" in opr:
        return notes
    existing = _find_entity_in_folder(folder, new_id)
    if existing:
        opr["6"] = new_id
        notes.append(f"occupation_per_race.6={new_id} (existing)")
        return notes
    found = _find_entity_in_folder(folder, source_id)
    if not found:
        notes.append(f"could not clone vampire worker from {source_id}")
        return notes
    _src_path, src = found
    vamp = clone_as_vampire(src, new_id=new_id, name=name)
    dest = folder / "entities" / f"{slug_name(name)}.json"
    _write_json(dest, vamp)
    opr["6"] = new_id
    notes.append(f"wrote {dest.name} as occupation_per_race.6")
    return notes


def _fix_caught_silkworm_glyph(folder: Path) -> List[str]:
    notes: List[str] = []
    found = _find_entity_in_folder(folder, "core_2_Caught_Silkworm")
    if not found:
        return notes
    path, ent = found
    glyph = ent.get("glyph") or {}
    frames = glyph.get("frames") if isinstance(glyph, dict) else None
    if frames:
        return notes
    worm = _find_entity_in_folder(folder, "core_2_Silkworm")
    src_frames = None
    if worm:
        src_frames = ((worm[1].get("glyph") or {}).get("frames") or None)
    if not src_frames:
        try:
            vanilla = _load_json(core2_dir() / "entities" / "Silkworm.json")
            src_frames = (vanilla.get("glyph") or {}).get("frames")
        except Exception:
            src_frames = [{"color": [255, 255, 255], "delay": 0, "index": 133}]
    ent.setdefault("glyph", {})["frames"] = deepcopy(src_frames)
    ent["glyph"]["random_frame_start"] = False
    _write_json(path, ent)
    notes.append("Caught_Silkworm glyph.frames")
    return notes


def _rename_building_groups_sheet(folder: Path) -> List[str]:
    notes: List[str] = []
    assets_path = folder / "assets.json"
    if not assets_path.is_file():
        return notes
    try:
        assets = _load_json(assets_path)
    except Exception:
        return notes
    sheets = (assets.get("graphics") or {}).get("tilesheets") or []
    changed = False
    for sheet in sheets:
        if isinstance(sheet, dict) and sheet.get("name") == "building_groups":
            sheet["name"] = "officers_building_groups"
            changed = True
    if changed:
        _write_json(assets_path, assets)
        notes.append("renamed tilesheet building_groups -> officers_building_groups")
    groups_path = folder / "building_groups.json"
    if groups_path.is_file():
        try:
            groups = _load_json(groups_path)
        except Exception:
            groups = None
        if isinstance(groups, list):
            for g in groups:
                if isinstance(g, dict) and g.get("id") == "militaryofficer":
                    g["icon"] = 5
                    notes.append("building_groups militaryofficer icon=5")
            _write_json(groups_path, groups)
    return notes


def upgrade_mod_folder(folder: Path) -> List[str]:
    """Apply 0.10 building/occupation/conversation fixes in place."""
    folder = Path(folder)
    notes: List[str] = []
    mj = folder / "mod.json"
    mod_name = folder.name
    if mj.is_file():
        mod = _load_json(mj)
        mod_name = str(mod.get("name") or mod_name)
        if str(mod.get("game_required") or "") != GAME_REQUIRED:
            mod["game_required"] = GAME_REQUIRED
            notes.append(f"game_required={GAME_REQUIRED}")
        ver = str(mod.get("version") or "0.1.0")
        if ver in ("0.1.0", "0.0.1"):
            parts = ver.split(".")
            parts[-1] = str(int(parts[-1]) + 1)
            mod["version"] = ".".join(parts)
            notes.append(f"version={mod['version']}")
        _write_json(mj, mod)

    extra_conv: Dict[str, List[str]] = {}
    def _conv_entities(begin_id: str, *eids: str) -> None:
        have = extra_conv.setdefault(begin_id, [])
        for eid in eids:
            if eid not in have and _find_entity_in_folder(folder, eid):
                have.append(eid)

    bdir = folder / "buildings"
    if bdir.is_dir():
        for path in sorted(bdir.glob("*.json")):
            data = _load_entity_file(path)
            if not data:
                continue
            bnotes = fix_building(data)
            if is_player_building(data) and "6" not in (data.get("occupation_per_race") or {}):
                occ0 = str((data.get("occupation_per_race") or {}).get("0") or data.get("occupation") or "")
                bid = str(data.get("id") or path.stem)
                if "Officer" in bid or "officer" in occ0.lower() or occ0.startswith("Officers!"):
                    vnotes = _ensure_vampire_worker(
                        folder,
                        data,
                        new_id="Officers!_Vampire_Officer",
                        name="Vampire Officer",
                        source_id=occ0 if occ0.startswith("Officers!") else "Officers!_Officer",
                    )
                    bnotes.extend(vnotes)
                elif "Firemage" in bid:
                    vnotes = _ensure_vampire_worker(
                        folder,
                        data,
                        new_id="Battlemages_Vampire_Firemage",
                        name="Vampire Firemage",
                        source_id="Battlemages_Human_Firemage",
                    )
                    bnotes.extend(vnotes)
                elif "Cryomage" in bid:
                    vnotes = _ensure_vampire_worker(
                        folder,
                        data,
                        new_id="Battlemages_Vampire_Cryomage",
                        name="Vampire Cryomage",
                        source_id="Battlemages_Human_Cryomage",
                    )
                    bnotes.extend(vnotes)
            if "6" in (data.get("occupation_per_race") or {}):
                bnotes = [n for n in bnotes if "needs cloned vampire" not in n]
            if bnotes:
                _write_json(path, data)
                notes.append(f"{path.name}: {', '.join(bnotes)}")

    edir = folder / "entities"
    if edir.is_dir():
        for path in sorted(edir.glob("*.json")):
            ent = _load_entity_file(path)
            if not ent:
                continue
            enotes = fix_occupation_entity(ent)
            if enotes:
                _write_json(path, ent)
                notes.append(f"{path.name}: {', '.join(enotes)}")

    notes.extend(_fix_caught_silkworm_glyph(folder))
    if "officer" in mod_name.lower():
        notes.extend(_rename_building_groups_sheet(folder))
    _conv_entities("Officer_begin", "Officers!_Player", "Officers!_Vampire_Officer")
    _conv_entities(
        "Battlemages_begin",
        "Battlemages_Player_Firemage",
        "Battlemages_Player_Cryomage",
        "Battlemages_Vampire_Firemage",
        "Battlemages_Vampire_Cryomage",
    )

    conv_path = folder / "conversations.json"
    if conv_path.is_file():
        conv = _load_json(conv_path)
        cnotes = fix_conversations(conv, extra_entities=extra_conv)
        if cnotes:
            _write_json(conv_path, conv)
            notes.extend(cnotes)
    return notes


def copy_mod_to_output(src: Path, dest: Optional[Path] = None) -> Path:
    src = Path(src)
    dest = Path(dest) if dest else output_mod_dir(src)
    if dest.resolve() == src.resolve():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns("skill.json"))
    return dest


def copy_building_map(source: Path, dest_dir: Path, dest_name: Optional[str] = None) -> Path:
    source = Path(source)
    if source.suffix.lower() != ".smap":
        raise ValueError("Only existing .smap files can be copied (do not invent maps)")
    if not source.is_file():
        raise FileNotFoundError(f"Map not found: {source}")
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / (dest_name or source.name)
    shutil.copy2(source, dest)
    return dest


def find_building_map(building_id: str) -> Optional[Path]:
    """Return an existing .smap next to a cloned-from building, if any."""
    try:
        row = load_building(building_id)
    except FileNotFoundError:
        return None
    cloned = row.get("_cloned_from")
    if not cloned:
        return None
    maps = Path(cloned).parent.parent / "building_maps"
    if not maps.is_dir():
        return None
    stem = Path(cloned).stem
    for path in maps.glob("*.smap"):
        if stem.lower() in path.stem.lower() or str(row.get("id") or "").lower() in path.stem.lower():
            return path
    return None
