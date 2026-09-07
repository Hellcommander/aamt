#!/usr/bin/env python3
"""Clone and author Soulash 2 races via a partial character.json merge.

The engine merges character.json arrays by id. Never copy vanilla's whole
file. Playable races need id, name, description, playable, statistics, tags,
names, items, recipes. Civilization extras (settlement, base_entities, crests)
are optional. Locations, maps, portraits, and Steam Workshop publishing are
out of scope. Player training buildings are in ``s2_buildings``.

Race ``abilities`` (patch / workshop Draken) are starting actives, not skill
milestones. ``control_actions`` belong here, not in milestone rewards.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from s2_paths import core2_dir, skip_mod_path, workshop_root
from s2_schema import slug_name

CIV_KEYS = (
    "base_entities",
    "settlement",
    "state_crests",
    "courting",
    "orphan_surname",
    "forbidden_actions",
    "trade_restrictions",
    "crimes",
)

STAT_KEYS = (
    "strength",
    "endurance",
    "dexterity",
    "intelligence",
    "willpower",
    "hearing",
    "sneaking",
    "magic_power",
    "health_regen",
    "health_regen_tick",
)

CLONE_DROP = ("file", "_cloned_from", "_source", "_name_files")

PLAYABLE_MIN = ("id", "name", "description", "playable", "statistics", "tags", "names", "items", "recipes")

WAR_CAUSES = ("conquest", "ride_for_wealth", "soul_harvest")

BASE_ENTITY_ROLES = ("adult", "child", "leader", "recruit", "rebel", "adventurer")

MALE_NAME_PREFIXES = ("Kael", "Tor", "Bran", "Voss", "Hal", "Ryn", "Orr", "Drenn", "Kor", "Mal", "Steg", "Ulric")
FEMALE_NAME_PREFIXES = ("Mira", "Sena", "Lira", "Nyx", "Tess", "Yara", "Neris", "Vala", "Isha", "Rena", "Kira", "Sola")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def _iter_character_files() -> Iterable[Tuple[str, Path]]:
    core = core2_dir() / "character.json"
    if core.is_file():
        yield "core_2", core
    ws = workshop_root()
    if not ws or not ws.is_dir():
        return
    for mod in sorted(ws.iterdir()):
        if not mod.is_dir() or skip_mod_path(mod):
            continue
        path = mod / "character.json"
        if path.is_file():
            yield mod.name, path


def _blob(race: Dict[str, Any]) -> str:
    return " ".join(
        str(x or "")
        for x in (
            race.get("id"),
            race.get("name"),
            race.get("description"),
            " ".join(str(p) for p in (race.get("passives") or [])),
        )
    ).lower()


def search_races(query: str, limit: int = 40) -> List[Dict[str, Any]]:
    q = (query or "").strip().lower()
    if not q and not (query or "").isdigit():
        return []
    hits: List[Dict[str, Any]] = []
    for source, path in _iter_character_files():
        data = _load_json(path)
        if not isinstance(data, dict):
            continue
        for race in data.get("races") or []:
            if not isinstance(race, dict):
                continue
            rid = str(race.get("id") or "")
            name = str(race.get("name") or "")
            hay = _blob(race)
            if q not in hay and q not in rid.lower() and q not in name.lower():
                continue
            hits.append(
                {
                    "id": rid,
                    "name": name or rid,
                    "source": source,
                    "playable": bool(race.get("playable")),
                    "passives": list(race.get("passives") or []),
                    "abilities": list(race.get("abilities") or []),
                    "civilization": bool(race.get("settlement") or race.get("base_entities")),
                    "file": str(path),
                }
            )
            if len(hits) >= limit:
                return hits
    return hits


def search_control_actions(query: str = "", limit: int = 40) -> List[Dict[str, Any]]:
    q = (query or "").strip().lower()
    hits: List[Dict[str, Any]] = []
    seen = set()
    for source, path in _iter_character_files():
        data = _load_json(path)
        if not isinstance(data, dict):
            continue
        for row in data.get("control_actions") or []:
            if not isinstance(row, dict):
                continue
            cid = str(row.get("id") or "")
            name = str(row.get("name") or "")
            if cid in seen:
                continue
            hay = f"{cid} {name} {' '.join(str(t) for t in (row.get('tags') or []))}".lower()
            if q and q not in hay:
                continue
            seen.add(cid)
            hits.append(
                {
                    "id": cid,
                    "name": name or cid,
                    "source": source,
                    "tags": list(row.get("tags") or []),
                    "file": str(path),
                }
            )
            if len(hits) >= limit:
                return hits
    return hits


def search_tags(query: str = "", limit: int = 80) -> List[Dict[str, Any]]:
    q = (query or "").strip().lower()
    hits: List[Dict[str, Any]] = []
    seen = set()
    for source, path in _iter_character_files():
        data = _load_json(path)
        if not isinstance(data, dict):
            continue
        for tag in data.get("tags") or []:
            if not isinstance(tag, dict):
                continue
            tid = str(tag.get("id") or "")
            name = str(tag.get("name") or "")
            key = (tid, name)
            if key in seen:
                continue
            if q and q not in tid.lower() and q not in name.lower():
                continue
            seen.add(key)
            hits.append({"id": tid, "name": name or tid, "source": source, "options": list(tag.get("options") or [])})
            if len(hits) >= limit:
                return hits
    return hits


def load_vanilla_race(source_id: str) -> Dict[str, Any]:
    wanted = str(source_id).strip()
    wanted_low = wanted.lower()
    name_hit: Optional[Dict[str, Any]] = None
    for source, path in _iter_character_files():
        data = _load_json(path)
        if not isinstance(data, dict):
            continue
        for race in data.get("races") or []:
            if not isinstance(race, dict):
                continue
            rid = str(race.get("id") or "")
            name = str(race.get("name") or "")
            if rid == wanted or name.lower() == wanted_low:
                out = deepcopy(race)
                out["_cloned_from"] = str(path)
                out["_source"] = source
                if rid == wanted:
                    return out
                if name_hit is None:
                    name_hit = out
    if name_hit:
        return name_hit
    raise FileNotFoundError(f"Race not found: {source_id}")


def load_vanilla_control_action(source_id: str) -> Dict[str, Any]:
    wanted = str(source_id).strip()
    wanted_low = wanted.lower()
    for source, path in _iter_character_files():
        data = _load_json(path)
        if not isinstance(data, dict):
            continue
        for row in data.get("control_actions") or []:
            if not isinstance(row, dict):
                continue
            cid = str(row.get("id") or "")
            name = str(row.get("name") or "")
            if cid == wanted or name.lower() == wanted_low:
                out = deepcopy(row)
                out["_cloned_from"] = str(path)
                out["_source"] = source
                return out
    raise FileNotFoundError(f"Control action not found: {source_id}")


def search_production_actions(query: str = "", limit: int = 40) -> List[Dict[str, Any]]:
    q = (query or "").strip().lower()
    hits: List[Dict[str, Any]] = []
    seen = set()
    for source, path in _iter_character_files():
        data = _load_json(path)
        if not isinstance(data, dict):
            continue
        for row in data.get("production_actions") or []:
            if not isinstance(row, dict):
                continue
            pid = str(row.get("id") or "")
            name = str(row.get("name") or "")
            if pid in seen:
                continue
            hay = f"{pid} {name} {row.get('required_tool')}".lower()
            if q and q not in hay:
                continue
            seen.add(pid)
            hits.append(
                {
                    "id": pid,
                    "name": name or pid,
                    "source": source,
                    "required_tool": row.get("required_tool"),
                    "image": row.get("image"),
                    "equipment": bool(row.get("equipment")),
                    "file": str(path),
                }
            )
            if len(hits) >= limit:
                return hits
    return hits


def load_vanilla_production_action(source_id: str) -> Dict[str, Any]:
    wanted = str(source_id).strip()
    wanted_low = wanted.lower()
    for source, path in _iter_character_files():
        data = _load_json(path)
        if not isinstance(data, dict):
            continue
        for row in data.get("production_actions") or []:
            if not isinstance(row, dict):
                continue
            pid = str(row.get("id") or "")
            name = str(row.get("name") or "")
            if pid == wanted or name.lower() == wanted_low:
                out = deepcopy(row)
                out["_cloned_from"] = str(path)
                out["_source"] = source
                return out
    raise FileNotFoundError(f"Production action not found: {source_id}")


def clone_production_action(
    source_id: str,
    *,
    new_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    required_tool: Optional[int] = None,
) -> Dict[str, Any]:
    row = load_vanilla_production_action(source_id)
    for key in CLONE_DROP:
        row.pop(key, None)
    row["id"] = str(new_id)
    if name:
        row["name"] = name
    if description is not None:
        row["description"] = description
    if required_tool is not None:
        row["required_tool"] = int(required_tool)
    return row


def make_production_action(
    action_id: str,
    name: str,
    *,
    description: str = "",
    required_tool: int = 0,
    image: int = 0,
    sound: str = "",
    equipment: bool = False,
    clone_from: Optional[str] = None,
) -> Dict[str, Any]:
    if clone_from:
        return clone_production_action(
            clone_from,
            new_id=action_id,
            name=name if name and name != clone_from else None,
            description=description or None,
            required_tool=required_tool if required_tool else None,
        )
    return {
        "id": str(action_id),
        "name": name,
        "description": description or f"{name}.",
        "required_tool": int(required_tool),
        "image": int(image),
        "sound": sound,
        "equipment": bool(equipment),
    }


def add_production_action(spec: Dict[str, Any], action: Dict[str, Any]) -> Dict[str, Any]:
    spec.setdefault("production_actions", [])
    action = deepcopy(action)
    for key in CLONE_DROP:
        action.pop(key, None)
    pid = action.get("id")
    if not pid:
        raise ValueError("Production action needs an id")
    for i, existing in enumerate(spec["production_actions"]):
        if existing.get("id") == pid:
            spec["production_actions"][i] = action
            return action
    spec["production_actions"].append(action)
    return action


def _read_name_text(rel: str) -> Optional[str]:
    rel = str(rel).replace("\\", "/").lstrip("/")
    core = core2_dir() / rel
    if core.is_file():
        return core.read_text(encoding="utf-8")
    ws = workshop_root()
    if ws and ws.is_dir():
        for mod in ws.iterdir():
            if not mod.is_dir() or skip_mod_path(mod):
                continue
            cand = mod / rel
            if cand.is_file():
                return cand.read_text(encoding="utf-8")
    return None


def placeholder_names(stem: str, count: int = 12, *, female: bool = False) -> str:
    prefixes = FEMALE_NAME_PREFIXES if female else MALE_NAME_PREFIXES
    tail = (stem[:4] or "Nam").title()
    lines = [f"{p}{tail}" for p in prefixes[:count]]
    return "\n".join(lines) + "\n"


def _strip_civ(race: Dict[str, Any]) -> None:
    for key in CIV_KEYS:
        race.pop(key, None)
    names = race.get("names")
    if isinstance(names, dict):
        for extra in ("settlements", "states", "surnames"):
            names.pop(extra, None)


def _rewrite_names(
    race: Dict[str, Any],
    *,
    race_id: str,
    copy_source: bool,
) -> Dict[str, str]:
    """Return relative-path -> text for npc/names files. Mutates race['names']."""
    blobs: Dict[str, str] = {}
    old = race.get("names") if isinstance(race.get("names"), dict) else {}
    male_rel = f"npc/names/{race_id}_male.txt"
    female_rel = f"npc/names/{race_id}_female.txt"
    male_src = str(old.get("male") or "")
    female_src = str(old.get("female") or "")
    male_text = _read_name_text(male_src) if copy_source and male_src else None
    female_text = _read_name_text(female_src) if copy_source and female_src else None
    stem = slug_name(str(race.get("name") or race_id))
    blobs[male_rel] = male_text if male_text else placeholder_names(stem, female=False)
    blobs[female_rel] = female_text if female_text else placeholder_names(stem, female=True)
    race["names"] = {"male": male_rel, "female": female_rel}
    return blobs


def clone_race(
    source_id: str,
    *,
    new_id: str,
    name: Optional[str] = None,
    keep_id: bool = False,
    civilization: bool = False,
    overlay: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """Copy a vanilla/workshop race. overlay+keep_id = Draken-style patch of vanilla id."""
    race = load_vanilla_race(source_id)
    display = name or str(race.get("name") or source_id)
    if name:
        race["name"] = name
    rid = str(race.get("id") or source_id) if keep_id else str(new_id)
    race["id"] = rid
    for key in CLONE_DROP:
        race.pop(key, None)
    blobs: Dict[str, str] = {}
    if overlay and keep_id:
        # Patch vanilla in place: stats / names / civ stay in core_2.
        keep = {
            "id": rid,
            "name": race.get("name") or display,
            "description": race.get("description") or "",
            "passives": list(race.get("passives") or []),
            "abilities": list(race.get("abilities") or []),
        }
        if race.get("playable") is not None:
            keep["playable"] = race["playable"]
        return keep, blobs
    if not civilization:
        _strip_civ(race)
    if overlay:
        return race, blobs
    blobs = _rewrite_names(race, race_id=slug_name(rid).lower() or rid, copy_source=True)
    race.setdefault("items", [])
    race.setdefault("recipes", [])
    race.setdefault("playable", True)
    return race, blobs


def make_race(
    *,
    race_id: str,
    name: str,
    description: str = "",
    playable: bool = True,
    statistics: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
    passives: Optional[List[str]] = None,
    abilities: Optional[List[str]] = None,
    items: Optional[List[str]] = None,
    recipes: Optional[List[str]] = None,
    adult: int = 50,
    child: int = 14,
    elder: int = 70,
    settlement: Optional[Dict[str, Any]] = None,
    base_entities: Optional[Dict[str, str]] = None,
    orphan_surname: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    stats = dict(statistics or {"strength": 1, "endurance": 1, "dexterity": 1, "intelligence": 1, "willpower": 1})
    stem = slug_name(race_id).lower() or slug_name(name).lower()
    male_rel = f"npc/names/{stem}_male.txt"
    female_rel = f"npc/names/{stem}_female.txt"
    race: Dict[str, Any] = {
        "id": race_id,
        "name": name,
        "description": description or name,
        "playable": bool(playable),
        "image": 0,
        "ages": {"adult": int(adult), "child": int(child), "elder": int(elder)},
        "statistics": stats,
        "tags": list(tags or ["9"]),
        "passives": list(passives or []),
        "items": list(items or []),
        "recipes": list(recipes or []),
        "names": {"male": male_rel, "female": female_rel},
    }
    if abilities:
        race["abilities"] = list(abilities)
    if settlement:
        race["settlement"] = settlement
    if base_entities:
        race["base_entities"] = {k: str(v) for k, v in base_entities.items() if v}
    if orphan_surname:
        race["orphan_surname"] = orphan_surname
    blobs = {
        male_rel: placeholder_names(slug_name(name), female=False),
        female_rel: placeholder_names(slug_name(name), female=True),
    }
    return race, blobs


def make_settlement(
    *,
    max_settlements: Optional[int] = None,
    disabled_trading: bool = False,
    collapse_on_leader_death: Optional[bool] = None,
    war_causes: Optional[List[str]] = None,
    birth_resource: Optional[str] = None,
    birth_amount: int = 1,
    aggression_default: Optional[bool] = None,
    single_family: bool = False,
    migration: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    out: Dict[str, Any] = {}
    if max_settlements is not None:
        out["max"] = int(max_settlements)
    if disabled_trading:
        out["disabled_trading"] = True
    if collapse_on_leader_death is not None:
        out["collapse_on_leader_death"] = bool(collapse_on_leader_death)
    if war_causes:
        out["war_causes"] = list(war_causes)
    if birth_resource:
        out["birth_cost"] = {"amount": int(birth_amount), "resource": str(birth_resource)}
    if aggression_default is not None:
        out["aggression_default"] = bool(aggression_default)
    if single_family:
        out["single_family"] = True
    if migration is not None:
        out["migration"] = bool(migration)
    return out or None


def make_control_action(
    *,
    action_id: str,
    name: str,
    tags: List[str],
    description: Optional[str] = None,
    clone_from: str = "core_2_tame",
) -> Dict[str, Any]:
    try:
        row = load_vanilla_control_action(clone_from)
    except FileNotFoundError:
        row = {
            "success_animation": "core_2_Tame_animal",
            "success_message": "{} becomes your new companion!",
            "failure_ability": "12",
            "failure_message": "[{}%] You were unable to tame {}, it becomes enraged!",
            "image": 75,
        }
    for key in CLONE_DROP:
        row.pop(key, None)
    row["id"] = action_id
    row["name"] = name
    row["tags"] = [str(t) for t in tags]
    row["description"] = description or (
        "Use your willpower to attempt taking control of a matching creature. "
        "This action requires an empty companion slot and takes 2 turns."
    )
    return row


def make_character_tag(*, tag_id: str, name: str, options: Optional[List[str]] = None) -> Dict[str, Any]:
    tag: Dict[str, Any] = {"id": str(tag_id), "name": str(name)}
    tag["options"] = list(options or ["sleep_in_bed", "cover_from_weather"])
    return tag


def add_race(spec: Dict[str, Any], race: Dict[str, Any], *, name_files: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    spec.setdefault("races", [])
    race = deepcopy(race)
    for key in CLONE_DROP:
        race.pop(key, None)
    rid = race.get("id")
    if not rid:
        raise ValueError("Race needs an id")
    replaced = False
    for i, existing in enumerate(spec["races"]):
        if existing.get("id") == rid:
            spec["races"][i] = race
            replaced = True
            break
    if not replaced:
        spec["races"].append(race)
    if name_files:
        spec.setdefault("name_files", {})
        spec["name_files"].update(name_files)
    return race


def add_control_action(spec: Dict[str, Any], action: Dict[str, Any]) -> Dict[str, Any]:
    spec.setdefault("control_actions", [])
    action = deepcopy(action)
    for key in CLONE_DROP:
        action.pop(key, None)
    cid = action.get("id")
    if not cid:
        raise ValueError("Control action needs an id")
    for i, existing in enumerate(spec["control_actions"]):
        if existing.get("id") == cid:
            spec["control_actions"][i] = action
            return action
    spec["control_actions"].append(action)
    return action


def add_character_tag(spec: Dict[str, Any], tag: Dict[str, Any]) -> Dict[str, Any]:
    spec.setdefault("character_tags", [])
    tag = deepcopy(tag)
    tid = tag.get("id")
    if not tid:
        raise ValueError("Tag needs an id")
    for i, existing in enumerate(spec["character_tags"]):
        if existing.get("id") == tid:
            spec["character_tags"][i] = tag
            return tag
    spec["character_tags"].append(tag)
    return tag


def parse_base_entity(item: str) -> Tuple[str, str]:
    if "=" not in item:
        raise ValueError(f"Expected role=entity_id, got {item!r}")
    key, _, raw = item.partition("=")
    key = key.strip()
    if key not in BASE_ENTITY_ROLES:
        raise ValueError(f"Unknown base_entities role {key!r}. Use one of: {', '.join(BASE_ENTITY_ROLES)}")
    val = raw.strip()
    if not val:
        raise ValueError(f"base_entities {key} needs an entity id")
    return key, val


def parse_stat_flag(item: str) -> Tuple[str, Any]:
    if "=" not in item:
        raise ValueError(f"Expected stat=value, got {item!r}")
    key, _, raw = item.partition("=")
    key = key.strip()
    if key not in STAT_KEYS:
        raise ValueError(f"Unknown race statistic {key!r}. Use one of: {', '.join(STAT_KEYS)}")
    text = raw.strip()
    try:
        value: Any = float(text) if "." in text else int(text)
    except ValueError as exc:
        raise ValueError(f"Race stat {key} needs a number, got {raw!r}") from exc
    return key, value


def public_race(race: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in race.items() if not str(k).startswith("_")}


def write_character_json(spec: Dict[str, Any], root: Path) -> Optional[Path]:
    """Emit a merge-only character.json plus npc/names stubs. Returns the json path or None."""
    races = [public_race(r) for r in spec.get("races") or []]
    actions = [{k: v for k, v in a.items() if not str(k).startswith("_")} for a in spec.get("control_actions") or []]
    tags = list(spec.get("character_tags") or [])
    prod = [{k: v for k, v in a.items() if not str(k).startswith("_")} for a in spec.get("production_actions") or []]
    payload: Dict[str, Any] = {}
    if races:
        payload["races"] = races
    if actions:
        payload["control_actions"] = actions
    if tags:
        payload["tags"] = tags
    if prod:
        payload["production_actions"] = prod
    if not payload:
        return None
    root = Path(root)
    path = root / "character.json"
    path.write_text(json.dumps(payload, indent="\t") + "\n", encoding="utf-8")
    files = dict(spec.get("name_files") or {})
    for race in races:
        names = race.get("names") if isinstance(race.get("names"), dict) else {}
        for gender in ("male", "female"):
            rel = names.get(gender)
            if not rel or not isinstance(rel, str):
                continue
            dest = root / rel.replace("\\", "/")
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.is_file():
                continue
            text = files.get(rel) or placeholder_names(
                slug_name(str(race.get("name") or race.get("id") or "npc")),
                female=(gender == "female"),
            )
            dest.write_text(text, encoding="utf-8")
    return path


def load_character_into_spec(spec: Dict[str, Any], folder: Path) -> None:
    path = Path(folder) / "character.json"
    if not path.is_file():
        return
    data = _load_json(path)
    if not isinstance(data, dict):
        return
    if isinstance(data.get("races"), list):
        spec["races"] = data["races"]
    if isinstance(data.get("control_actions"), list):
        spec["control_actions"] = data["control_actions"]
    if isinstance(data.get("tags"), list):
        spec["character_tags"] = data["tags"]
    if isinstance(data.get("production_actions"), list):
        spec["production_actions"] = data["production_actions"]
    name_files: Dict[str, str] = {}
    names_dir = Path(folder) / "npc" / "names"
    if names_dir.is_dir():
        for txt in names_dir.glob("*.txt"):
            rel = f"npc/names/{txt.name}"
            name_files[rel] = txt.read_text(encoding="utf-8")
    if name_files:
        spec["name_files"] = name_files


def grant_sources(spec: Dict[str, Any]) -> Tuple[set, set]:
    """Ability / passive ids granted by races (starting kit, not skill-tree)."""
    ab: set = set()
    pa: set = set()
    for race in spec.get("races") or []:
        for aid in race.get("abilities") or []:
            ab.add(str(aid))
        for pid in race.get("passives") or []:
            pa.add(str(pid))
    for ent in spec.get("entities") or []:
        res = ent.get("resource") if isinstance(ent.get("resource"), dict) else {}
        gp = res.get("granted_passive")
        if gp:
            pa.add(str(gp))
        skills = ent.get("skills") if isinstance(ent.get("skills"), dict) else {}
        for mid in skills.get("milestones") or []:
            pa.add(str(mid))
    return ab, pa
