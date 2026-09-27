#!/usr/bin/env python3
"""In-memory skill spec that round-trips to Soulash 2 mod JSON (Geomancy layout)."""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from s2_assets import write_packaging
from s2_buildings import building_filename, public_building
from s2_entities import ENTITY_REF_KEYS, detect_role, entity_filename, public_entity
from s2_paths import core2_dir, output_root, skip_mod_path, staging_dir, workshop_root
from s2_races import load_character_into_spec, write_character_json
from s2_schema import infer_amplifier_type, is_effects_keys_id, slug_name

# Vanilla Pyromancy interleaves +1 statistic with empty/milestone-only levels.
VANILLA_STAT_POINTS = [
    2, 4, 5, 7, 8, 10, 11, 13, 14, 16, 17, 19, 20, 22, 23, 25, 26, 28, 29, 31, 33, 35, 37, 39, 41, 43, 45, 47, 49
]
# Skill Stat Rebalance (workshop 3766934606): no +1 on 1–10, then every
# level 11–50. Combat trees also get a unique level-30 all-attribute mastery.
AFTER_10_STAT_POINTS = list(range(11, 51))
DEFAULT_STAT_POINTS = list(AFTER_10_STAT_POINTS)
EARLY_PLUS_AFTER_10 = [2, 4, 5, 7, 8, 10] + AFTER_10_STAT_POINTS

STAT_POINT_PRESETS = {
    "default": list(DEFAULT_STAT_POINTS),
    "rebalance": list(AFTER_10_STAT_POINTS),
    "after10": list(AFTER_10_STAT_POINTS),
    "early": list(EARLY_PLUS_AFTER_10),
    "vanilla": list(VANILLA_STAT_POINTS),
    "none": [],
}

MASTERY_STATS = ("strength", "dexterity", "endurance", "intelligence", "willpower")
MASTERY_LEVEL = 30
MASTERY_PERCENT = 0.1
# Every skill starts at 10 for free. Passives on 1–10 are free power.
PAID_UNLOCK_MIN = 11


def require_paid_passive_level(
    level: Optional[int],
    *,
    innate: bool = False,
    what: str = "Passive",
) -> None:
    if innate or level is None:
        return
    if int(level) < PAID_UNLOCK_MIN:
        raise ValueError(
            f"{what} unlock_level {level} is in the free 1–10 band (every skill starts at 10). "
            "Skill Stat Rebalance: passives start at 11+, or use --innate."
        )


def is_rebalance_mastery(passive: Dict[str, Any]) -> bool:
    got = set()
    for row in passive.get("effects") or []:
        if not isinstance(row, dict):
            continue
        if row.get("effect") != "statistic_percent":
            continue
        try:
            pct = float(row.get("secondary_value"))
        except (TypeError, ValueError):
            continue
        if abs(pct - MASTERY_PERCENT) < 1e-9:
            got.add(str(row.get("value")))
    return set(MASTERY_STATS) <= got


def parse_item_ref(token: str) -> Dict[str, Any]:
    """Parse `70:1` or `70` into vanilla-style starting_gear {id, amount}. Ids stay strings."""
    raw = (token or "").strip()
    if not raw:
        raise ValueError("Empty item id")
    if ":" in raw:
        eid, _, amt = raw.partition(":")
        return {"id": str(eid).strip(), "amount": int(amt.strip())}
    return {"id": raw, "amount": 1}


def parse_starting_gear(item: str) -> Dict[str, Any]:
    """Parse one starting_gear choice.

    `70:1` — always grant. `70:1|111:1` or `first=70:1,second=111:1` — character-create choice.
    """
    raw = (item or "").strip()
    if not raw:
        raise ValueError("Empty starting_gear")
    if "|" in raw and "=" not in raw:
        first, _, second = raw.partition("|")
        out: Dict[str, Any] = {"first": parse_item_ref(first)}
        if second.strip():
            out["second"] = parse_item_ref(second)
        return out
    if "=" not in raw:
        return {"first": parse_item_ref(raw)}
    parts: Dict[str, Any] = {}
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            raise ValueError(f"Expected first=id:amount in {item!r}")
        key, _, val = chunk.partition("=")
        key = key.strip().lower()
        if key not in ("first", "second"):
            raise ValueError(f"starting_gear key must be first or second, got {key!r}")
        parts[key] = parse_item_ref(val)
    if "first" not in parts:
        raise ValueError("starting_gear needs first=id[:amount]")
    return parts


def parse_exp_source(item: str) -> Dict[str, Any]:
    """Parse `ability=2` or `production=2:6` (rate:production_action id)."""
    raw = (item or "").strip()
    if not raw:
        raise ValueError("Empty exp_source")
    extra_action = ""
    if "," in raw:
        main, _, rest = raw.partition(",")
        for chunk in rest.split(","):
            key, _, val = chunk.partition("=")
            if key.strip() in ("action", "production_action"):
                extra_action = val.strip()
        raw = main.strip()
    if "=" not in raw:
        raise ValueError("Expected id=rate, e.g. ability=2 or production=2:6")
    eid, _, rest = raw.partition("=")
    eid = eid.strip()
    rest = rest.strip()
    action = extra_action
    rate_text = rest
    if ":" in rest:
        rate_text, _, action = rest.partition(":")
        action = action.strip()
    try:
        rate: Any = float(rate_text) if "." in rate_text else int(rate_text)
    except ValueError as exc:
        raise ValueError(f"exp_source rate must be a number, got {rate_text!r}") from exc
    out: Dict[str, Any] = {"id": eid, "rate": rate}
    if action:
        out["production_action"] = str(action)
    return out


def add_starting_gear(spec: Dict[str, Any], choice: Dict[str, Any]) -> Dict[str, Any]:
    gear = spec.setdefault("skill", {}).setdefault("starting_gear", [])
    gear.append(choice)
    return choice


def add_exp_source(spec: Dict[str, Any], source: Dict[str, Any], *, replace_same_id: bool = False) -> Dict[str, Any]:
    sources = spec.setdefault("skill", {}).setdefault("exp_sources", [])
    if replace_same_id:
        sid = source.get("id")
        spec["skill"]["exp_sources"] = [row for row in sources if row.get("id") != sid]
        sources = spec["skill"]["exp_sources"]
    sources.append(source)
    return source


def patch_mod_meta(
    spec: Dict[str, Any],
    *,
    thumbnail: Optional[str] = None,
    steam_publish_id: Optional[int] = None,
    disable_portraits: Optional[bool] = None,
    author: Optional[str] = None,
    version: Optional[str] = None,
    description: Optional[str] = None,
    name: Optional[str] = None,
) -> None:
    mod = spec.setdefault("mod", {})
    if thumbnail is not None:
        if thumbnail:
            mod["thumbnail"] = thumbnail
        else:
            mod.pop("thumbnail", None)
    if steam_publish_id is not None:
        mod["steam_publish_id"] = int(steam_publish_id)
    if disable_portraits is True:
        mod["disable_portraits"] = True
    elif disable_portraits is False:
        mod.pop("disable_portraits", None)
    if author is not None:
        mod["author"] = author
    if version is not None:
        mod["version"] = version
    if description is not None:
        mod["description"] = description
    if name is not None:
        mod["name"] = name


def apply_skill_update(spec: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Merge Skill-tab / set-skill fields. Unknown keys are ignored."""
    skill = spec.setdefault("skill", {})
    for key in ("name", "description", "combat_skill", "difficulty", "level_start", "image"):
        if key not in payload:
            continue
        val = payload[key]
        if val is None or val == "":
            skill.pop(key, None)
        else:
            skill[key] = val
    if "exp_sources" in payload:
        skill["exp_sources"] = payload["exp_sources"] or []
    if "starting_gear" in payload:
        if payload["starting_gear"]:
            skill["starting_gear"] = payload["starting_gear"]
        else:
            skill.pop("starting_gear", None)
    if "stat_points" in payload:
        if payload["stat_points"] is None:
            skill.pop("stat_points", None)
        else:
            skill["stat_points"] = [int(x) for x in payload["stat_points"]]
    if payload.get("stat_preset"):
        apply_stat_preset(spec, payload["stat_preset"])
    if payload.get("fill_stats_after_10"):
        fill_stats_after_10(spec, through=int(payload.get("stat_through") or 50))
    if "mod" in payload and isinstance(payload["mod"], dict):
        patch_mod_meta(
            spec,
            thumbnail=payload["mod"].get("thumbnail", None) if "thumbnail" in payload["mod"] else None,
            steam_publish_id=payload["mod"].get("steam_publish_id") if "steam_publish_id" in payload["mod"] else None,
            disable_portraits=payload["mod"].get("disable_portraits") if "disable_portraits" in payload["mod"] else None,
            author=payload["mod"].get("author"),
            version=payload["mod"].get("version"),
            description=payload["mod"].get("description"),
        )
    return skill


def patch_ability_costs(
    ability: Dict[str, Any],
    *,
    stamina: Optional[int] = None,
    health: Optional[int] = None,
    cost_item: Optional[str] = None,
    cost_item_type: Optional[int] = None,
    ammo: Optional[int] = None,
    min_range: Optional[int] = None,
    require_one_of: Optional[List[Any]] = None,
    require_always: Optional[List[Any]] = None,
    cast_time: Optional[float] = None,
    cooldown: Optional[float] = None,
    duration: Optional[float] = None,
) -> None:
    """Docs §6.2 costs. JSON keys: cost.stamina/health/item/item_type/ammo; requirements.one_of/always."""
    cost = ability.setdefault("cost", {"health": 0, "stamina": 0})
    if stamina is not None:
        cost["stamina"] = int(stamina)
    if health is not None:
        cost["health"] = int(health)
    if cost_item:
        cost["item"] = str(cost_item)
    if cost_item_type is not None:
        cost["item_type"] = int(cost_item_type)
    if ammo is not None:
        cost["ammo"] = int(ammo)
    if min_range is not None:
        ability["min_range"] = int(min_range)
    if cast_time is not None:
        ability["cast_time"] = float(cast_time)
    if cooldown is not None:
        ability["cooldown"] = float(cooldown)
    if duration is not None:
        ability["duration"] = float(duration)
    if require_one_of or require_always:
        req = ability.setdefault("requirements", {})
        if require_one_of:
            req["one_of"] = [int(x) if str(x).isdigit() else x for x in require_one_of]
        if require_always:
            req["always"] = [int(x) if str(x).isdigit() else x for x in require_always]


DEFAULT_ID_AUTHOR = "Arendeth"


def author_id_prefix(author: Optional[str] = None) -> str:
    """Vanilla skills are core_2_pyromancy. Custom skills use {author}_{school}."""
    return slug_name(author or DEFAULT_ID_AUTHOR).lower()


def prefixed_skill_id(raw_id: str, *, author: Optional[str] = None) -> str:
    """Prefix a school id so it cannot collide with a later vanilla skill of the same name."""
    sid = slug_name(str(raw_id or "").strip()).lower()
    if not sid:
        raise ValueError("Empty skill id")
    if sid.startswith("core_2_"):
        return sid
    prefix = author_id_prefix(author) + "_"
    if sid.startswith(prefix):
        return sid
    return prefix + sid


def has_author_prefix(skill_id: str, *, author: Optional[str] = None) -> bool:
    sid = str(skill_id or "").strip()
    if sid.startswith("core_2_"):
        return True
    prefix = author_id_prefix(author) + "_"
    return sid.startswith(prefix) and len(sid) > len(prefix)


def retarget_owned_ids(spec: Dict[str, Any], old_id: str, new_id: str) -> int:
    """Rewrite skill_id / mod id and every owned string id that starts with old_id_."""
    old = str(old_id or "").strip()
    new = str(new_id or "").strip()
    if not old or not new or old == new:
        return 0
    owned = old + "_"
    count = 0

    def remap(value: Any) -> Any:
        nonlocal count
        if isinstance(value, dict):
            return {k: remap(v) for k, v in value.items()}
        if isinstance(value, list):
            return [remap(v) for v in value]
        if isinstance(value, str):
            if value == old or value.startswith(owned):
                count += 1
                return new + value[len(old) :]
        return value

    remapped = remap(spec)
    spec.clear()
    spec.update(remapped)
    spec["id"] = new
    spec["mod_id"] = new
    spec["skill_id"] = new
    spec.setdefault("skill", {})["id"] = new
    return count


def new_spec(skill_id: str, name: str, *, mod_id: Optional[str] = None, level_start: Optional[int] = None, author: Optional[str] = None, prefix: bool = True) -> Dict[str, Any]:
    sid = prefixed_skill_id(skill_id, author=author) if prefix else slug_name(str(skill_id or "").strip()).lower()
    mid = prefixed_skill_id(mod_id, author=author) if (prefix and mod_id) else ((mod_id or sid).strip() if mod_id else sid)
    skill = {
            "id": sid,
            "name": name,
            "image": 0,
            "description": f"{name}.\n\nYou can train this skill by using abilities.",
            "combat_skill": True,
            "exp_sources": [{"id": "ability", "rate": 2}],
            "stat_points": list(DEFAULT_STAT_POINTS),
            "difficulty": 2,
        }
    if level_start is not None:
        skill["level_start"] = int(level_start)
    return {
        "id": mid,
        "mod_id": mid,
        "skill_id": sid,
        "mod": {
            "author": author or DEFAULT_ID_AUTHOR,
            "description": f"{name} skill.",
            "game_required": "0.10.0",
            "icon": "icon.png",
            "mods_required": ["core_2"],
            "name": name,
            "version": "0.1.0",
        },
        "skill": skill,
        "abilities": [],
        "passives": [],
        "amplifiers": [],
        "milestones": [],
        "entities": [],
        "stackers": [],
        "animations": [],
        "races": [],
        "control_actions": [],
        "character_tags": [],
        "production_actions": [],
        "buildings": [],
        "loot_exclude": [],
    }


def load_spec(path: Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def list_staged_specs() -> List[Path]:
    root = output_root()
    if not root.is_dir():
        return []
    return sorted(p for p in root.glob("*/skill.json") if p.is_file())


def save_spec(spec: Dict[str, Any], path: Optional[Path] = None) -> Path:
    out = Path(path) if path else (staging_dir(spec) / "skill.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    return out


def _ensure_lists(spec: Dict[str, Any]) -> None:
    for key in (
        "abilities",
        "passives",
        "amplifiers",
        "milestones",
        "entities",
        "stackers",
        "animations",
        "races",
        "control_actions",
        "character_tags",
        "production_actions",
        "buildings",
        "loot_exclude",
    ):
        spec.setdefault(key, [])


def stat_point_levels(spec: Dict[str, Any]) -> List[int]:
    raw = (spec.get("skill") or {}).get("stat_points")
    if raw is None:
        return list(DEFAULT_STAT_POINTS)
    return [int(x) for x in raw]


def apply_stat_preset(spec: Dict[str, Any], preset: str) -> List[int]:
    key = str(preset or "default").strip().lower().replace("-", "").replace("_", "")
    if key in ("after10", "from11", "delayed", "rebalance"):
        key = "after10"
    if key in ("default", "full", "all"):
        key = "default"
    if key in ("early", "earlyplus", "with1to10"):
        key = "early"
    if key not in STAT_POINT_PRESETS:
        raise ValueError(f"Unknown stat_points preset {preset!r} (default/rebalance/after10, early, vanilla, none)")
    points = list(STAT_POINT_PRESETS[key])
    spec.setdefault("skill", {})["stat_points"] = points
    return points


def fill_stats_after_10(spec: Dict[str, Any], *, through: int = 50) -> List[int]:
    """Union 11..through into stat_points. Does not move milestones; both can share a level."""
    skill = spec.setdefault("skill", {})
    have = [int(x) for x in (skill.get("stat_points") or [])]
    added = [n for n in range(11, int(through) + 1) if n not in have]
    skill["stat_points"] = sorted(set(have) | set(range(11, int(through) + 1)))
    return added


def add_combat_mastery(
    spec: Dict[str, Any],
    *,
    unlock_level: int = MASTERY_LEVEL,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Unique combat-branch mastery: +10% all five attributes (Skill Stat Rebalance)."""
    skill_name = str((spec.get("skill") or {}).get("name") or spec.get("skill_id") or "Skill")
    pid = f"{spec['skill_id']}_mastery"
    passive = {
        "id": pid,
        "name": name or f"{skill_name} Mastery",
        "image": 0,
        "effects": [
            {"effect": "statistic_percent", "value": stat, "secondary_value": MASTERY_PERCENT}
            for stat in MASTERY_STATS
        ],
    }
    return add_passive(spec, passive, unlock_level=int(unlock_level))


def _milestone(
    spec: Dict[str, Any],
    *,
    mid: str,
    name: str,
    level: int,
    kind: str,
    reward_id: str,
    innate: bool = False,
) -> Dict[str, Any]:
    mile = {
        "id": mid,
        "name": name,
        "requirements": {"milestones": [], "skill": int(level)},
        "rewards": [{kind: reward_id}],
        "skill_id": spec["skill_id"],
        "steps": [],
        "steps_type": 0,
        "file": f"{int(level)}_{slug_name(name)}.json",
    }
    if innate:
        mile["innate"] = True
        mile["requirements"] = {}
        mile["file"] = f"innate_{slug_name(name)}.json"
    return mile


def find_row(rows: List[Dict[str, Any]], rid: str, *, what: str) -> Dict[str, Any]:
    for row in rows or []:
        if row.get("id") == rid:
            return row
    raise KeyError(f"{what} not found: {rid}")


def _upsert_by_id(items: List[Dict[str, Any]], obj: Dict[str, Any], *, preserve_image: bool = True) -> bool:
    """Replace the row with the same id. Returns True if an existing row was replaced."""
    oid = obj.get("id")
    for i, existing in enumerate(items):
        if existing.get("id") != oid:
            continue
        if preserve_image and not obj.get("image") and existing.get("image"):
            obj["image"] = existing["image"]
        items[i] = obj
        return True
    items.append(obj)
    return False


def _upsert_milestone(
    spec: Dict[str, Any],
    *,
    mid: str,
    name: str,
    level: Optional[int],
    kind: str,
    reward_id: str,
    innate: bool = False,
) -> Dict[str, Any]:
    existing = next((m for m in spec.get("milestones") or [] if m.get("id") == mid), None)
    if existing:
        if innate:
            existing["innate"] = True
            existing["requirements"] = {}
            existing["file"] = f"innate_{slug_name(name or existing.get('name') or mid)}.json"
        elif level is not None:
            existing.setdefault("requirements", {})["skill"] = int(level)
            existing["file"] = f"{int(level)}_{slug_name(name or existing.get('name') or mid)}.json"
        if name:
            existing["name"] = name
        existing["rewards"] = [{kind: reward_id}]
        return existing
    if level is None and not innate:
        raise ValueError(f"Cannot create milestone {mid} without unlock_level")
    mile = _milestone(
        spec,
        mid=mid,
        name=name or mid,
        level=0 if level is None else int(level),
        kind=kind,
        reward_id=reward_id,
        innate=innate,
    )
    spec["milestones"].append(mile)
    return mile


def add_ability(
    spec: Dict[str, Any],
    ability: Dict[str, Any],
    *,
    unlock_level: Optional[int] = None,
    no_milestone: bool = False,
) -> Dict[str, Any]:
    _ensure_lists(spec)
    ability = deepcopy(ability)
    ability.pop("_cloned_from", None)
    raw_id = str(ability.get("id") or "")
    if not raw_id or raw_id.isdigit():
        ability["id"] = f"{spec['skill_id']}_{slug_name(ability.get('name') or raw_id or 'ability').lower()}"
    ability["skill"] = spec["skill_id"]
    ability.setdefault("slots", {"offensive": 1, "utility": 1})
    ability.setdefault("cost", {"health": 0, "stamina": 0})
    ability.setdefault("cast_time", 1.0)
    ability.setdefault("cooldown", 0.0)
    ability.setdefault("duration", 0.0)
    ability.setdefault("range", 1)
    ability.setdefault("target", "health")
    ability.setdefault("animation", "0")
    ability.setdefault("image", 0)
    ability.setdefault("effects", {})
    ensure_aoe_shape(ability)
    if not str(ability.get("description") or "").strip():
        effects = ability.get("effects") or {}
        if "damage" in effects:
            ability["description"] = "Deals ::damage ::damage_type damage."
        elif "heal" in effects:
            ability["description"] = "This ability heals ::heal health."
    aid = ability["id"]
    _upsert_by_id(spec["abilities"], ability)
    if not no_milestone and unlock_level is not None:
        _upsert_milestone(
            spec,
            mid=aid,
            name=ability.get("name") or aid,
            level=unlock_level,
            kind="ability",
            reward_id=aid,
        )
    return ability


def ensure_aoe_shape(ability: Dict[str, Any]) -> None:
    """Vanilla Meteor/Fireball always set aoe_shape with aoe_range. Missing it makes aoe_tile casts do nothing."""
    tgt = str(ability.get("target") or "")
    fx = ability.get("effects")
    if not isinstance(fx, dict):
        return
    if tgt in ("aoe_tile", "aoe_target", "aoe_self") and "aoe_range" in fx and "aoe_shape" not in fx:
        fx["aoe_shape"] = 1


def add_passive(
    spec: Dict[str, Any],
    passive: Dict[str, Any],
    *,
    unlock_level: Optional[int] = None,
    no_milestone: bool = False,
    innate: bool = False,
) -> Dict[str, Any]:
    _ensure_lists(spec)
    require_paid_passive_level(unlock_level, innate=innate, what=f"Passive {passive.get('id')}")
    passive = deepcopy(passive)
    passive.setdefault("image", 0)
    _upsert_by_id(spec["passives"], passive)
    if innate:
        _upsert_milestone(
            spec,
            mid=passive["id"],
            name=passive.get("name") or passive["id"],
            level=unlock_level,
            kind="passive",
            reward_id=passive["id"],
            innate=True,
        )
    elif not no_milestone and unlock_level is not None:
        _upsert_milestone(
            spec,
            mid=passive["id"],
            name=passive.get("name") or passive["id"],
            level=unlock_level,
            kind="passive",
            reward_id=passive["id"],
        )
    return passive


def add_amplifier(
    spec: Dict[str, Any],
    amplifier: Dict[str, Any],
    *,
    unlock_level: Optional[int] = None,
    no_milestone: bool = False,
) -> Dict[str, Any]:
    _ensure_lists(spec)
    amplifier = deepcopy(amplifier)
    amplifier.setdefault("image", 0)
    if "type" not in amplifier:
        first = None
        bonuses = amplifier.get("bonuses") or []
        if bonuses and isinstance(bonuses[0], dict):
            first = bonuses[0].get("effect")
        amplifier["type"] = infer_amplifier_type(str(first or "range"))
    _upsert_by_id(spec["amplifiers"], amplifier)
    if not no_milestone and unlock_level is not None:
        _upsert_milestone(
            spec,
            mid=amplifier["id"],
            name=amplifier.get("name") or amplifier["id"],
            level=unlock_level,
            kind="amplifier",
            reward_id=amplifier["id"],
        )
    return amplifier


def _milestone_grants(mile: Dict[str, Any], kind: str, reward_id: str) -> bool:
    for reward in mile.get("rewards") or []:
        if isinstance(reward, dict) and str(reward.get(kind) or "") == reward_id:
            return True
    return False


_KIND_BUCKET = {
    "ability": ("abilities", "Ability"),
    "passive": ("passives", "Passive"),
    "amplifier": ("amplifiers", "Amplifier"),
}


def remove_reward(spec: Dict[str, Any], kind: str, rid: str) -> Dict[str, Any]:
    """Drop an ability, passive, or amplifier and every milestone that grants it."""
    _ensure_lists(spec)
    if kind not in _KIND_BUCKET:
        raise ValueError(f"Cannot remove kind {kind}")
    bucket, label = _KIND_BUCKET[kind]
    row = find_row(spec[bucket], rid, what=label)
    spec[bucket] = [item for item in spec[bucket] if item.get("id") != rid]
    spec["milestones"] = [
        mile
        for mile in spec["milestones"]
        if mile.get("id") != rid and not _milestone_grants(mile, kind, rid)
    ]
    return row


def remove_amplifier(spec: Dict[str, Any], amp_id: str) -> Dict[str, Any]:
    return remove_reward(spec, "amplifier", amp_id)


def remove_ability(spec: Dict[str, Any], ability_id: str) -> Dict[str, Any]:
    return remove_reward(spec, "ability", ability_id)


def remove_passive(spec: Dict[str, Any], passive_id: str) -> Dict[str, Any]:
    return remove_reward(spec, "passive", passive_id)


def add_stacker(
    spec: Dict[str, Any],
    stacker: Dict[str, Any],
    *,
    bind_ability: Optional[str] = None,
    stacker_count: int = 1,
) -> Dict[str, Any]:
    """Stackers are not skill-tree rewards. Abilities/amplifiers reference them by id."""
    _ensure_lists(spec)
    stacker = deepcopy(stacker)
    stacker.setdefault("image", 0)
    stacker.setdefault("effects", [])
    stacker.setdefault("max_stacks", 10)
    stacker.setdefault("apply_caster", False)
    _upsert_by_id(spec["stackers"], stacker)
    if bind_ability:
        bind_ability_stacker(spec, bind_ability, stacker["id"], count=stacker_count)
    return stacker


def add_animation(
    spec: Dict[str, Any],
    animation: Dict[str, Any],
    *,
    bind_ability: Optional[Any] = None,
) -> Dict[str, Any]:
    _ensure_lists(spec)
    animation = deepcopy(animation)
    animation.pop("_cloned_from", None)
    aid = animation.get("id")
    replaced = False
    if aid:
        for i, existing in enumerate(spec["animations"]):
            if existing.get("id") == aid:
                spec["animations"][i] = animation
                replaced = True
                break
    if not replaced:
        spec["animations"].append(animation)
    binds = bind_ability
    if isinstance(binds, str):
        binds = [binds]
    for bid in binds or []:
        bid = str(bid).strip()
        if not bid:
            continue
        found = False
        for ab in spec.get("abilities") or []:
            if ab.get("id") == bid:
                ab["animation"] = animation["id"]
                found = True
                break
        if not found:
            raise KeyError(f"Ability not found: {bid}")
    return animation


def bind_ability_stacker(spec: Dict[str, Any], ability_id: str, stacker_id: str, *, count: int = 1) -> None:
    set_ability_effect(spec, ability_id, "stacker", stacker_id, keys=True)
    set_ability_effect(spec, ability_id, "stacker_count", int(count), keys=False)


def load_vanilla_stacker(stacker_id: str) -> Dict[str, Any]:
    wanted = str(stacker_id).strip()
    files: List[Path] = []
    core = core2_dir() / "ability_stackers.json"
    if core.is_file():
        files.append(core)
    ws = workshop_root()
    if ws and ws.is_dir():
        for path in ws.glob("*/ability_stackers.json"):
            if skip_mod_path(path):
                continue
            files.append(path)
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        for row in data:
            if not isinstance(row, dict):
                continue
            if str(row.get("id") or "") == wanted or str(row.get("name") or "").lower() == wanted.lower():
                out = deepcopy(row)
                out["_cloned_from"] = str(path)
                return out
    raise FileNotFoundError(f"Stacker not found: {stacker_id}")


def clone_stacker(source_id: str, *, new_id: str, name: Optional[str] = None) -> Dict[str, Any]:
    row = load_vanilla_stacker(source_id)
    row["id"] = new_id
    if name:
        row["name"] = name
    row.pop("_cloned_from", None)
    return row


ABILITY_CLONE_DROP = ("level", "profession", "upgrades", "file", "_cloned_from", "_file")


def _iter_ability_files():
    core = core2_dir() / "abilities"
    if core.is_dir():
        for path in sorted(core.glob("*.json")):
            yield "core_2", path
    ws = workshop_root()
    if ws and ws.is_dir():
        for path in sorted(ws.glob("*/abilities/*.json")):
            if skip_mod_path(path):
                continue
            yield path.parent.parent.name, path


def search_abilities(query: str, limit: int = 40) -> List[Dict[str, Any]]:
    q = (query or "").strip()
    if len(q) < 2 and not q.isdigit():
        return []
    q_low = q.lower()
    hits: List[Dict[str, Any]] = []
    for source, path in _iter_ability_files():
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        aid = str(data.get("id") or path.stem)
        name = str(data.get("name") or "")
        stem = path.stem.lower().replace("_", " ")
        if q_low not in aid.lower() and q_low not in name.lower() and q_low not in stem and q not in path.stem:
            continue
        hits.append(
            {
                "id": aid,
                "name": name or aid,
                "source": source,
                "skill": str(data.get("skill") or ""),
                "target": str(data.get("target") or ""),
                "file": str(path),
            }
        )
        if len(hits) >= limit:
            break
    return hits


def load_vanilla_ability(source_id: str) -> Dict[str, Any]:
    wanted = str(source_id).strip()
    wanted_low = wanted.lower()
    stem_hit: Optional[Dict[str, Any]] = None
    name_hit: Optional[Dict[str, Any]] = None
    for _source, path in _iter_ability_files():
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        aid = str(data.get("id") or "")
        name = str(data.get("name") or "")
        if aid == wanted or path.stem == wanted:
            out = deepcopy(data)
            out["_cloned_from"] = str(path)
            return out
        if stem_hit is None and path.stem.startswith(f"{wanted}_"):
            stem_hit = deepcopy(data)
            stem_hit["_cloned_from"] = str(path)
        if name_hit is None and name.lower() == wanted_low:
            name_hit = deepcopy(data)
            name_hit["_cloned_from"] = str(path)
    if stem_hit:
        return stem_hit
    if name_hit:
        return name_hit
    raise FileNotFoundError(f"Ability not found: {source_id}")


def clone_ability(
    source_id: str,
    *,
    skill_id: str,
    new_id: Optional[str] = None,
    name: Optional[str] = None,
    keep_image: bool = False,
) -> Dict[str, Any]:
    """Copy vanilla/workshop ability JSON and retarget id + skill (Geomancy string ids)."""
    ab = load_vanilla_ability(source_id)
    display = name or str(ab.get("name") or source_id)
    if name:
        ab["name"] = name
    aid = new_id or f"{skill_id}_{slug_name(display).lower()}"
    if str(aid).isdigit():
        raise ValueError(
            f"New ability ids must be strings like {skill_id}_fireball, not vanilla numeric ids ({aid})"
        )
    ab["id"] = aid
    ab["skill"] = skill_id
    if not keep_image:
        ab["image"] = 0
    for key in ABILITY_CLONE_DROP:
        ab.pop(key, None)
    return ab


def add_entity(spec: Dict[str, Any], entity: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_lists(spec)
    entity = deepcopy(entity)
    eid = entity.get("id")
    if not eid:
        raise ValueError("Entity needs an id")
    for i, existing in enumerate(spec["entities"]):
        if existing.get("id") == eid:
            spec["entities"][i] = entity
            return entity
    spec["entities"].append(entity)
    return entity


def bind_ability_entity(spec: Dict[str, Any], ability_id: str, key: str, entity_id: str) -> None:
    key = key or "summon"
    if key not in ENTITY_REF_KEYS:
        raise ValueError(f"Not an entity-ref key: {key}")
    set_ability_effect(spec, ability_id, key, entity_id, keys=True)


def grant_existing(
    spec: Dict[str, Any],
    *,
    kind: str,
    reward_id: str,
    name: str,
    unlock_level: int,
    milestone_id: Optional[str] = None,
    innate: bool = False,
) -> Dict[str, Any]:
    _ensure_lists(spec)
    if kind == "passive":
        require_paid_passive_level(None if innate else unlock_level, innate=innate, what=f"Passive {reward_id}")
    mid = milestone_id or f"{spec['skill_id']}_{slug_name(name).lower()}"
    return _upsert_milestone(
        spec,
        mid=mid,
        name=name,
        level=None if innate else int(unlock_level),
        kind=kind,
        reward_id=reward_id,
        innate=innate,
    )


def add_loot_exclude(spec: Dict[str, Any], entity_id: str) -> None:
    _ensure_lists(spec)
    eid = str(entity_id)
    if eid not in spec["loot_exclude"]:
        spec["loot_exclude"].append(eid)


def set_ability_effect(spec: Dict[str, Any], ability_id: str, key: str, value: Any, *, keys: Optional[bool] = None) -> None:
    ab = find_row(spec.get("abilities") or [], ability_id, what="Ability")
    use_keys = is_effects_keys_id(key) if keys is None else keys
    bucket = "effects_keys" if use_keys else "effects"
    ab.setdefault(bucket, {})[key] = value


def clear_ability_effect(spec: Dict[str, Any], ability_id: str, key: str) -> str:
    """Remove a key from effects or effects_keys. Returns which bucket was cleared."""
    ab = find_row(spec.get("abilities") or [], ability_id, what="Ability")
    for bucket in ("effects", "effects_keys", "effect_keys"):
        data = ab.get(bucket)
        if isinstance(data, dict) and key in data:
            data.pop(key)
            if not data:
                ab.pop(bucket, None)
            return bucket
    raise KeyError(f"{ability_id} has no effect {key}")


def patch_amplifier(
    spec: Dict[str, Any],
    amp_id: str,
    *,
    name: Optional[str] = None,
    amp_type: Optional[str] = None,
    description: Optional[str] = None,
    bonuses: Optional[List[Dict[str, Any]]] = None,
    append_bonuses: Optional[List[Dict[str, Any]]] = None,
    clear_bonuses: bool = False,
    cooldown: Optional[float] = None,
    cast_time: Optional[float] = None,
    range_val: Optional[int] = None,
    cost_stamina: Optional[int] = None,
    duration: Optional[float] = None,
    image: Optional[int] = None,
) -> Dict[str, Any]:
    row = find_row(spec.get("amplifiers") or [], amp_id, what="Amplifier")
    if name is not None:
        row["name"] = name
    if amp_type is not None:
        row["type"] = amp_type
    if description is not None:
        row["description"] = description
    if clear_bonuses:
        row.pop("bonuses", None)
    if bonuses is not None:
        row["bonuses"] = bonuses
    if append_bonuses:
        row.setdefault("bonuses", []).extend(append_bonuses)
    if cooldown is not None:
        row["cooldown"] = cooldown
    if cast_time is not None:
        row["cast_time"] = cast_time
    if range_val is not None:
        row["range"] = range_val
    if cost_stamina is not None:
        row["cost_stamina"] = cost_stamina
    if duration is not None:
        row["duration"] = duration
    if image is not None:
        row["image"] = image
    return row


def patch_passive(
    spec: Dict[str, Any],
    passive_id: str,
    *,
    name: Optional[str] = None,
    effects: Optional[List[Dict[str, Any]]] = None,
    append_effects: Optional[List[Dict[str, Any]]] = None,
    clear_effects: bool = False,
    apply_mode: Optional[str] = None,
    image: Optional[int] = None,
) -> Dict[str, Any]:
    row = find_row(spec.get("passives") or [], passive_id, what="Passive")
    if name is not None:
        row["name"] = name
    if clear_effects:
        row["effects"] = []
    if effects is not None:
        row["effects"] = effects
    if append_effects:
        row.setdefault("effects", []).extend(append_effects)
    if apply_mode is not None:
        row["apply_mode"] = apply_mode
    if image is not None:
        row["image"] = image
    return row


def patch_stacker(
    spec: Dict[str, Any],
    stacker_id: str,
    *,
    name: Optional[str] = None,
    effects: Optional[List[Dict[str, Any]]] = None,
    append_effects: Optional[List[Dict[str, Any]]] = None,
    clear_effects: bool = False,
    max_stacks: Optional[int] = None,
    duration: Optional[int] = None,
    description: Optional[str] = None,
    image: Optional[int] = None,
    apply_caster: Optional[bool] = None,
) -> Dict[str, Any]:
    row = find_row(spec.get("stackers") or [], stacker_id, what="Stacker")
    if name is not None:
        row["name"] = name
    if clear_effects:
        row["effects"] = []
    if effects is not None:
        row["effects"] = effects
    if append_effects:
        row.setdefault("effects", []).extend(append_effects)
    if max_stacks is not None:
        row["max_stacks"] = max_stacks
    if duration is not None:
        row["duration"] = duration
    if description is not None:
        row["description"] = description
    if image is not None:
        row["image"] = image
    if apply_caster is not None:
        row["apply_caster"] = apply_caster
    return row


def cycle_images(spec: Dict[str, Any], *, kinds: Optional[List[str]] = None, modulo: int = 8) -> Dict[str, int]:
    """Assign placeholder tilesheet indexes 0..modulo-1 so image:0 is not every row."""
    mapping = {
        "ability": "abilities",
        "amplifier": "amplifiers",
        "passive": "passives",
        "stacker": "stackers",
    }
    counts: Dict[str, int] = {}
    for kind in kinds or ["ability", "amplifier", "passive"]:
        bucket = mapping.get(kind)
        if not bucket:
            raise ValueError(f"cycle-images kind must be ability/amplifier/passive/stacker, got {kind}")
        rows = spec.get(bucket) or []
        for i, row in enumerate(rows):
            row["image"] = i % int(modulo)
        counts[kind] = len(rows)
    return counts


def set_slots(spec: Dict[str, Any], ability_id: str, **slots: int) -> None:
    for ab in spec.get("abilities") or []:
        if ab.get("id") == ability_id:
            ab.setdefault("slots", {}).update({k: int(v) for k, v in slots.items() if v is not None})
            return
    raise KeyError(f"Ability not found: {ability_id}")


def tree_rows(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for m in spec.get("milestones") or []:
        level = (m.get("requirements") or {}).get("skill")
        if m.get("innate"):
            level = "innate"
        rewards = m.get("rewards") or []
        kind, rid = "", ""
        if rewards and isinstance(rewards[0], dict) and rewards[0]:
            kind, rid = next(iter(rewards[0].items()))
        rows.append({"level": level, "id": m.get("id"), "name": m.get("name"), "kind": kind, "reward": rid})
    for lv in stat_point_levels(spec):
        rows.append({"level": lv, "id": f"stat_{lv}", "name": "+1 statistic", "kind": "stat", "reward": ""})
    def _lvl(row: Dict[str, Any]) -> tuple:
        lv = row["level"]
        if lv == "innate":
            return (-1, 0, row["name"] or "")
        if lv is None:
            return (10_000, 0, row["name"] or "")
        kind_rank = 0 if row.get("kind") == "stat" else 1
        return (int(lv), kind_rank, row["name"] or "")
    rows.sort(key=_lvl)
    return rows


def _dump(obj: Any) -> str:
    return json.dumps(obj, indent="\t") + "\n"


def write_mod(spec: Dict[str, Any], dest: Optional[Path] = None) -> Path:
    root = Path(dest) if dest else staging_dir(spec)
    skill_id = spec["skill_id"]
    root.mkdir(parents=True, exist_ok=True)
    preview = root / "_fx_preview"
    if preview.is_dir():
        shutil.rmtree(preview)
    write_packaging(spec, root)
    (root / "mod.json").write_text(_dump(spec["mod"]), encoding="utf-8")
    (root / "skills.json").write_text(_dump([spec["skill"]]), encoding="utf-8")
    abilities = root / "abilities"
    abilities.mkdir(exist_ok=True)
    written_abs = set()
    for ab in spec.get("abilities") or []:
        fname = f"{slug_name(ab.get('name') or ab['id'])}.json"
        (abilities / fname).write_text(_dump(ab), encoding="utf-8")
        written_abs.add(fname)
    for stale in abilities.glob("*.json"):
        if stale.name not in written_abs:
            stale.unlink()
    (root / "passives.json").write_text(_dump(spec.get("passives") or []), encoding="utf-8")
    (root / "ability_amplifiers.json").write_text(_dump(spec.get("amplifiers") or []), encoding="utf-8")
    (root / "ability_stackers.json").write_text(
        _dump([{k: v for k, v in s.items() if not str(k).startswith("_")} for s in spec.get("stackers") or []]),
        encoding="utf-8",
    )
    miles = root / "milestones" / skill_id
    miles.mkdir(parents=True, exist_ok=True)
    written_miles = set()
    for m in spec.get("milestones") or []:
        payload = {k: v for k, v in m.items() if k != "file"}
        fname = m.get("file") or f"{slug_name(m.get('name') or m['id'])}.json"
        (miles / fname).write_text(_dump(payload), encoding="utf-8")
        written_miles.add(fname)
    for stale in miles.glob("*.json"):
        if stale.name not in written_miles:
            stale.unlink()
    ents = root / "entities"
    if spec.get("entities") is not None:
        ents.mkdir(exist_ok=True)
        written_ents = set()
        for ent in spec.get("entities") or []:
            fname = entity_filename(ent)
            (ents / fname).write_text(_dump(public_entity(ent)), encoding="utf-8")
            written_ents.add(fname)
        if ents.is_dir():
            for stale in ents.glob("*.json"):
                if stale.name not in written_ents:
                    stale.unlink()
    adir = root / "animations"
    if spec.get("animations") is not None:
        adir.mkdir(exist_ok=True)
        written = set()
        for anim in spec.get("animations") or []:
            payload = {k: v for k, v in anim.items() if not str(k).startswith("_")}
            fname = slug_name(anim.get("name") or anim["id"]) + ".json"
            (adir / fname).write_text(_dump(payload), encoding="utf-8")
            written.add(fname)
        if adir.is_dir():
            for stale in adir.glob("*.json"):
                if stale.name not in written:
                    stale.unlink()
    if spec.get("loot_exclude"):
        (root / "loot_exclude.json").write_text(_dump(spec["loot_exclude"]), encoding="utf-8")
    bdir = root / "buildings"
    if spec.get("buildings"):
        bdir.mkdir(exist_ok=True)
        for building in spec["buildings"]:
            (bdir / building_filename(building)).write_text(
                _dump(public_building(building)), encoding="utf-8"
            )
    write_character_json(spec, root)
    save_spec(spec, root / "skill.json")
    return root


def _read_json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def _as_row_list(raw: Any) -> List[Any]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if isinstance(raw, dict):
        if "id" in raw or "name" in raw:
            return [raw]
        return [v for v in raw.values() if isinstance(v, dict)]
    return []


def _load_json_dir(folder: Path, *, role: Optional[str] = None) -> List[Dict[str, Any]]:
    if not folder.is_dir():
        return []
    loaded: List[Dict[str, Any]] = []
    for p in sorted(folder.glob("*.json")):
        row = _read_json_file(p)
        if not isinstance(row, dict):
            continue
        row["_file"] = p.name
        if role == "entity":
            row["_role"] = detect_role(row)
        loaded.append(row)
    return loaded


_DISK_LIST_KEYS = (
    "abilities",
    "passives",
    "amplifiers",
    "milestones",
    "stackers",
    "animations",
    "entities",
    "buildings",
    "loot_exclude",
    "races",
    "control_actions",
    "character_tags",
    "production_actions",
)


def load_mod_folder(folder: Path) -> Dict[str, Any]:
    """Assemble a studio spec from a Geomancy-layout mod folder (live JSON, not skill.json)."""
    folder = Path(folder)
    if not folder.exists():
        raise FileNotFoundError(f"Mod path does not exist: {folder}")
    mod = _read_json_file(folder / "mod.json")
    if not isinstance(mod, dict):
        mod = {}
    skills = _read_json_file(folder / "skills.json")
    if not isinstance(skills, list):
        skills = []
    skill = skills[0] if skills and isinstance(skills[0], dict) else None
    if not skill:
        skill = {"id": folder.name, "name": folder.name}
    spec = new_spec(
        str(skill.get("id") or folder.name),
        str(skill.get("name") or folder.name),
        mod_id=folder.name,
        prefix=False,
    )
    spec["id"] = folder.name
    spec["mod_id"] = folder.name
    spec["mod"] = mod or spec["mod"]
    spec["skill"] = skill
    spec["skill_id"] = skill.get("id") or folder.name

    spec["passives"] = _as_row_list(_read_json_file(folder / "passives.json"))
    amp_path = folder / "ability_amplifiers.json"
    if not amp_path.is_file():
        amp_path = folder / "amplifiers.json"
    spec["amplifiers"] = _as_row_list(_read_json_file(amp_path))
    spec["stackers"] = _as_row_list(_read_json_file(folder / "ability_stackers.json"))
    spec["abilities"] = _load_json_dir(folder / "abilities")
    miles: List[Dict[str, Any]] = []
    mdir = folder / "milestones"
    if mdir.is_dir():
        for p in sorted(mdir.rglob("*.json")):
            if "translations" in p.parts:
                continue
            row = _read_json_file(p)
            if not isinstance(row, dict):
                continue
            row["file"] = p.name
            miles.append(row)
    spec["milestones"] = miles
    spec["entities"] = _load_json_dir(folder / "entities", role="entity")
    spec["animations"] = _load_json_dir(folder / "animations")
    assets = _read_json_file(folder / "assets.json")
    if assets is not None:
        spec["assets"] = assets
    loot = _read_json_file(folder / "loot_exclude.json")
    if loot is not None:
        spec["loot_exclude"] = loot if isinstance(loot, list) else _as_row_list(loot)
    spec["buildings"] = _load_json_dir(folder / "buildings")
    load_character_into_spec(spec, folder)

    studio = _read_json_file(folder / "skill.json")
    if isinstance(studio, dict):
        for key in _DISK_LIST_KEYS:
            if spec.get(key):
                continue
            extra = studio.get(key)
            if not extra:
                continue
            spec[key] = extra if isinstance(extra, list) else _as_row_list(extra)
        if not spec.get("assets") and studio.get("assets") is not None:
            spec["assets"] = studio["assets"]
        if not skills and isinstance(studio.get("skill"), dict):
            spec["skill"] = studio["skill"]
            spec["skill_id"] = studio.get("skill_id") or spec["skill"].get("id") or spec["skill_id"]
    _ensure_lists(spec)
    return spec
    
    def load_mod_folder(folder: Path) -> Dict[str, Any]:
    folder = Path(folder)
    if not folder.is_dir():
        raise FileNotFoundError(f"Mod folder not found: {folder}")

    # Read mod.json / skills.json
    mod_meta = {}
    skills = []
    if (folder / "mod.json").is_file():
        mod_meta = json.loads((folder / "mod.json").read_text(encoding="utf-8-sig"))
    if (folder / "skills.json").is_file():
        skills = json.loads((folder / "skills.json").read_text(encoding="utf-8-sig"))

    # Base spec: keep ids as-is (no prefix rewrite)
    skill_row = skills[0] if skills and isinstance(skills[0], dict) else {}
    sid = str(skill_row.get("id") or folder.name)
    name = skill_row.get("name") or sid

    spec = new_spec(sid, name, mod_id=mod_meta.get("id") or sid, prefix=False)

    # Clear lists; we will assemble from disk
    for key in (
        "abilities", "passives", "amplifiers", "milestones",
        "stackers", "animations", "entities", "buildings",
        "loot_exclude", "races", "control_actions",
        "character_tags", "production_actions"
    ):
        spec[key] = []

    # Abilities/*.json
    abil_dir = folder / "abilities"
    if abil_dir.is_dir():
        for path in sorted(abil_dir.glob("*.json")):
            try:
                row = json.loads(path.read_text(encoding="utf-8-sig"))
                if isinstance(row, dict):
                    spec["abilities"].append(row)
            except Exception:
                pass

    # Passives.json
    p = folder / "passives.json"
    if p.is_file():
        try:
            rows = json.loads(p.read_text(encoding="utf-8-sig"))
            if isinstance(rows, dict):
                rows = [rows]
            spec["passives"].extend(r for r in rows if isinstance(r, dict))
        except Exception:
            pass

    # Amplifiers
    a = folder / "ability_amplifiers.json"
    if not a.is_file():
        a = folder / "amplifiers.json"
    if a.is_file():
        try:
            rows = json.loads(a.read_text(encoding="utf-8-sig"))
            if isinstance(rows, dict):
                rows = [rows]
            spec["amplifiers"].extend(r for r in rows if isinstance(r, dict))
        except Exception:
            pass

    # Stackers
    s = folder / "ability_stackers.json"
    if s.is_file():
        try:
            rows = json.loads(s.read_text(encoding="utf-8-sig"))
            if isinstance(rows, dict):
                rows = [rows]
            spec["stackers"].extend(r for r in rows if isinstance(r, dict))
        except Exception:
            pass

    # Milestones/**/*.json
    miles_root = folder / "milestones"
    if miles_root.is_dir():
        for path in sorted(miles_root.rglob("*.json")):
            if "translations" in path.parts:
                continue
            try:
                row = json.loads(path.read_text(encoding="utf-8-sig"))
                if isinstance(row, dict):
                    spec["milestones"].append(row)
            except Exception:
                pass

    # Animations/*.json
    anim_dir = folder / "animations"
    if anim_dir.is_dir():
        for path in sorted(anim_dir.glob("*.json")):
            try:
                row = json.loads(path.read_text(encoding="utf-8-sig"))
                if isinstance(row, dict):
                    spec["animations"].append(row)
            except Exception:
                pass

    _ensure_lists(spec)
    return spec

