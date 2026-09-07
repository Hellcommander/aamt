#!/usr/bin/env python3
"""Build and clone Soulash 2 item / creature entity JSON (Geomancy / summoning layout)."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from s2_paths import core2_dir, skip_mod_path, workshop_root
from s2_schema import slug_name

# messages.json item_type indexes. Usable=17 matches workshop skill books.
ITEM_TYPE = {
    "any": 0,
    "head_armor": 1,
    "head_cloth": 2,
    "amulet": 3,
    "torso_armor": 4,
    "torso_cloth": 5,
    "belt": 6,
    "legs_armor": 7,
    "legs_cloth": 8,
    "boots": 9,
    "cape": 10,
    "gloves": 11,
    "ring": 12,
    "weapon": 13,
    "shield": 14,
    "arrow": 15,
    "resource": 16,
    "usable": 17,
    "corpse": 18,
    "fish": 19,
    "food": 20,
    "bolt": 21,
    "bag": 22,
    "light_source": 23,
    "seed": 24,
    "note": 25,
}

# Tag 5 is the player faction on workshop summons (Friendly Wolf allies=["5"]).
PLAYER_TAG = "5"
# Paper / parchment used by Geomancy's Book of Geomancy craft recipe.
DEFAULT_BOOK_RESOURCE = "2006"

ENTITY_REF_KEYS = (
    "summon",
    "summon_on_move",
    "construct",
    "transform",
    "aura",
    "sense",
)

SPEC_ONLY_KEYS = ("_role", "_file", "_cloned_from")


def glyph(index: int = 0, color: Optional[List[int]] = None) -> Dict[str, Any]:
    return {
        "frames": [{"color": list(color or [255, 255, 255]), "delay": 0, "index": int(index)}],
        "random_frame_start": False,
    }


def detect_role(entity: Dict[str, Any]) -> str:
    comps = set(entity.get("components") or [])
    if "actor" in comps:
        return "creature"
    if "background" in comps:
        return "tile"
    if "item" in comps:
        return "item"
    return "entity"


def public_entity(entity: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: v for k, v in entity.items() if k not in SPEC_ONLY_KEYS}
    out.pop("file", None)
    return out


def _base_item(
    *,
    eid: str,
    name: str,
    description: str,
    item_type: int,
    glyph_index: int,
    value: int,
    weight: float,
    extra_components: Iterable[str] = (),
) -> Dict[str, Any]:
    components = ["glyph", "item", "minimap_pixel", "name", "position_2d", "value", "weight"]
    for c in extra_components:
        if c not in components:
            components.append(c)
    components = sorted(components)
    return {
        "_role": "item",
        "id": eid,
        "name": name,
        "description": description,
        "components": components,
        "glyph": glyph(glyph_index),
        "item": {"image": 0, "type": int(item_type)},
        "minimap_pixel": [179, 178, 176],
        "value": int(value),
        "weight": float(weight),
    }


def make_item(
    *,
    eid: str,
    name: str,
    preset: str = "generic",
    description: str = "",
    skill_id: str = "",
    glyph_index: int = 0,
    value: int = 100,
    weight: float = 0.2,
    damage: Optional[List[int]] = None,
    damage_type: str = "physical",
    resource_id: str = DEFAULT_BOOK_RESOURCE,
) -> Dict[str, Any]:
    preset = (preset or "generic").lower()
    desc = description or name
    if preset in ("skill_book", "book"):
        ent = _base_item(
            eid=eid,
            name=name,
            description=desc,
            item_type=ITEM_TYPE["usable"],
            glyph_index=glyph_index,
            value=value if value != 100 else 5000,
            weight=weight,
            extra_components=("craftable", "stackable", "usable"),
        )
        ent["craftable"] = {
            "backgrounds": [],
            "biomes": [],
            "cooldown": 432000,
            "magic_slots": 0,
            "resources": [{"amount": 1, "id": str(resource_id)}],
            "time": 60,
            "tools": [],
        }
        ent["usable"] = {"ability": "", "recipe": "", "skill_p": skill_id}
        return ent
    if preset in ("weapon",):
        dmg = damage or [2, 4]
        ent = _base_item(
            eid=eid,
            name=name,
            description=desc,
            item_type=ITEM_TYPE["weapon"],
            glyph_index=glyph_index or 71,
            value=value,
            weight=weight if weight != 0.2 else 1.5,
            extra_components=("weapon",),
        )
        ent["weapon"] = {
            "attack_speed": 1.0,
            "critical_hit": 0.0,
            "damage": [{"dmg_min": int(dmg[0]), "dmg_max": int(dmg[-1]), "dmg_type": damage_type}],
            "hands": 1,
            "hit_bonus": 0,
            "parry_bonus": 0,
            "range": 1,
            "type": 2,
        }
        return ent
    if preset in ("usable", "consumable"):
        ent = _base_item(
            eid=eid,
            name=name,
            description=desc,
            item_type=ITEM_TYPE["usable"],
            glyph_index=glyph_index,
            value=value,
            weight=weight,
            extra_components=("usable", "stackable"),
        )
        ent["usable"] = {"ability": "", "recipe": "", "skill_p": ""}
        return ent
    return _base_item(
        eid=eid,
        name=name,
        description=desc,
        item_type=ITEM_TYPE["resource"] if preset == "resource" else ITEM_TYPE["usable"],
        glyph_index=glyph_index,
        value=value,
        weight=weight,
    )


def make_creature(
    *,
    eid: str,
    name: str,
    preset: str = "summon",
    description: str = "",
    health: int = 80,
    damage: Optional[List[int]] = None,
    damage_type: str = "physical",
    glyph_index: int = 90,
    speed: float = 1.0,
    level: int = 5,
    stats: Optional[Dict[str, List[int]]] = None,
    can_regenerate_health: Optional[bool] = None,
) -> Dict[str, Any]:
    preset = (preset or "summon").lower()
    dmg = damage or [3, 6]
    ally = preset in ("summon", "ally", "companion")
    stats = stats or {
        "strength": [12, 16],
        "dexterity": [8, 12],
        "endurance": [12, 16],
        "intelligence": [4, 8],
        "willpower": [8, 12],
    }
    ai = {
        "allies": [PLAYER_TAG] if ally else [],
        "allow_production": [],
        "behaviors": [],
        "enemies": [] if ally else [PLAYER_TAG],
    }
    creature = {
        "_role": "creature",
        "id": eid,
        "name": name,
        "description": description or name,
        "components": [
            "actor",
            "artificial_intelligence",
            "collidable",
            "equipment",
            "experience_gainer",
            "fighter",
            "glyph",
            "health",
            "minimap_pixel",
            "moveable",
            "name",
            "position_2d",
            "sight",
            "stamina",
            "statistics",
            "tags",
            "weapon",
        ],
        "artificial_intelligence": ai,
        "equipment": {"disabled_slots": list(range(19))},
        "experience_gainer": {"exp": 0, "level": int(level)},
        "fighter": {"attackNames": ["Strike"]},
        "glyph": glyph(glyph_index),
        "health": int(health),
        "minimap_pixel": [115, 125, 132] if ally else [180, 60, 60],
        "moveable": {"speed": float(speed)},
        "sight": {"ignore_infra_penalty": True, "infravision": True, "range": 8, "threesixty": False},
        "stamina": {"fatigue": 100, "stamina": 100, "stamina_regen": 0.0},
        "statistics": stats,
        "tags": ["3", "9"],
        "weapon": {
            "attack_speed": 1.0,
            "critical_hit": 0.0,
            "damage": [{"dmg_min": int(dmg[0]), "dmg_max": int(dmg[-1]), "dmg_type": damage_type}],
            "hands": 1,
            "hit_bonus": 0,
            "parry_bonus": 0,
            "range": 1,
            "type": 2,
        },
    }
    if can_regenerate_health is not None:
        creature["can_regenerate_health"] = bool(can_regenerate_health)
    return creature


def make_tile(
    *,
    eid: str,
    name: str,
    description: str = "",
    glyph_index: int = 1,
    health: int = 1,
    movement_penalty: float = 0.5,
) -> Dict[str, Any]:
    return {
        "_role": "tile",
        "id": eid,
        "name": name,
        "description": description or name,
        "components": ["background", "glyph", "health", "minimap_pixel", "name", "position_2d"],
        "background": {
            "color": [44, 45, 41],
            "movement_penalty": float(movement_penalty),
            "noise": 2,
            "noise_intensity": 5,
        },
        "glyph": glyph(glyph_index),
        "health": int(health),
        "corpse": [],
        "minimap_pixel": [56, 36, 18],
    }


def attach_granted_passive(entity: Dict[str, Any], passive_id: str) -> None:
    """Storm Core-style: resource.granted_passive on an item."""
    comps = entity.setdefault("components", [])
    if "resource" not in comps:
        comps.append("resource")
        comps.sort()
    res = entity.setdefault("resource", {})
    if not isinstance(res, dict):
        res = {}
        entity["resource"] = res
    res["granted_passive"] = str(passive_id)
    res.setdefault("affix", "")
    res.setdefault("magic_ingredient", 0)
    res.setdefault("quality", 1)
    res.setdefault("type", 0)


def grant_entity_milestones(entity: Dict[str, Any], milestone_ids: List[str]) -> None:
    """Entity Editor → Skills → Milestones (innate / racial grants)."""
    comps = entity.setdefault("components", [])
    if "skills" not in comps:
        comps.append("skills")
        comps.sort()
    skills = entity.setdefault("skills", {})
    if not isinstance(skills, dict):
        skills = {}
        entity["skills"] = skills
    miles = list(skills.get("milestones") or [])
    for mid in milestone_ids:
        if str(mid) not in miles:
            miles.append(str(mid))
    skills["milestones"] = miles


def entity_filename(entity: Dict[str, Any]) -> str:
    if entity.get("_file"):
        return str(entity["_file"])
    return f"{slug_name(entity.get('name') or entity['id'])}.json"


def _iter_entity_files() -> Iterable[Tuple[str, Path]]:
    core = core2_dir() / "entities"
    if core.is_dir():
        for path in core.glob("*.json"):
            yield "core_2", path
    ws = workshop_root()
    if not ws:
        return
    for mod in sorted(ws.iterdir()):
        if not mod.is_dir() or skip_mod_path(mod):
            continue
        folder = mod / "entities"
        if not folder.is_dir():
            continue
        for path in folder.glob("*.json"):
            yield mod.name, path


def _header_match(path: Path, query: str) -> bool:
    stem = path.stem.lower().replace("_", " ")
    q = query.lower().replace("_", " ")
    return q in stem or q in path.stem.lower()


def search_entities(
    query: str,
    limit: int = 40,
    *,
    role: Optional[str] = None,
) -> List[Dict[str, Any]]:
    q = (query or "").strip()
    # Allow numeric vanilla ids ("15") as well as short names.
    if len(q) < 2 and not q.isdigit():
        return []
    role_filter = (role or "").strip().lower()
    q_l = q.lower()
    hits: List[Dict[str, Any]] = []
    for source, path in _iter_entity_files():
        stem_l = path.stem.lower()
        if not _header_match(path, q) and q_l not in stem_l and q not in path.stem:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        name = str(data.get("name") or "")
        eid = str(data.get("id") or path.stem)
        if q_l not in eid.lower() and q_l not in name.lower() and not _header_match(path, q):
            continue
        detected = detect_role(data)
        if role_filter and detected != role_filter:
            continue
        hits.append(
            {
                "id": eid,
                "name": name or eid,
                "role": detected,
                "source": source,
                "file": str(path),
            }
        )
        if len(hits) >= limit:
            break
    return hits


def load_vanilla_entity(entity_id: str) -> Dict[str, Any]:
    wanted = str(entity_id).strip()
    core = core2_dir() / "entities"
    candidates = []
    if core.is_dir():
        candidates.extend(sorted(core.glob(f"*{wanted}*.json")))
        exact = core / f"{wanted}.json"
        if exact.is_file():
            candidates.insert(0, exact)
    for source, path in _iter_entity_files():
        if wanted.lower() in path.stem.lower():
            candidates.append(path)
    seen = set()
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        if str(data.get("id")) == wanted or path.stem == wanted or path.stem.startswith(f"{wanted}_"):
            data["_cloned_from"] = str(path)
            data["_role"] = detect_role(data)
            return data
        if str(data.get("name") or "").lower() == wanted.lower():
            data["_cloned_from"] = str(path)
            data["_role"] = detect_role(data)
            return data
    for source, path in _iter_entity_files():
        if str(path) in seen:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        if isinstance(data, dict) and str(data.get("id")) == wanted:
            data["_cloned_from"] = str(path)
            data["_role"] = detect_role(data)
            return data
    raise FileNotFoundError(f"Entity not found: {entity_id}")


def clone_entity(source_id: str, *, new_id: str, name: Optional[str] = None) -> Dict[str, Any]:
    ent = deepcopy(load_vanilla_entity(source_id))
    ent["id"] = new_id
    if name:
        ent["name"] = name
    ent["_role"] = detect_role(ent)
    ent.pop("_file", None)
    return ent
