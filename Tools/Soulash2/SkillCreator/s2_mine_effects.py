#!/usr/bin/env python3
"""Mine Soulash 2 ability / passive / amplifier effects from docs, core_2, workshop, and the game exe."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from s2_mine_exe import TARGET_IDS, mine_exe
from s2_paths import catalog_dir, core2_dir, docs_index, skip_mod_path, soulash2_exe, soulash2_root, workshop_root
from s2_schema import apply_patch_overlay

ABILITY_DISPLAY_TO_KEY: Dict[str, Tuple[str, str]] = {
    "Light": ("light_source", "effects"),
    "Bleed Per Damage": ("bleed_per_damage", "effects"),
    "Full Vision": ("full_vision", "effects"),
    "Healing": ("heal", "effects"),
    "Summon": ("summon", "effects_keys"),
    "Fear": ("fear", "effects"),
    "Movement Speed": ("movement_speed", "effects"),
    "Sense": ("sense", "effects_keys"),
    "Weapon Damage": ("damage_weapon", "effects"),
    "Bonus Damage": ("damage_bonus", "effects"),
    "Resistance": ("resistance", "effects"),
    "Immobilize": ("immobilize", "effects"),
    "Area Of Effect Range": ("aoe_range", "effects"),
    "Area Of Effect Shape": ("aoe_shape", "effects"),
    "Area Of Effect Break": ("aoe_break", "effects"),
    "Summon on Move": ("summon_on_move", "effects_keys"),
    "Charge": ("charge", "effects"),
    "Disadvantage": ("hit_chance", "effects"),
    "Knockback": ("knockback", "effects"),
    "Lunging": ("lunge", "effects"),
    "Rollback": ("rollback", "effects"),
    "Pierced": ("pierce", "effects"),
    "Poisoned": ("poison_effect", "effects"),
    "Chaining Targets": ("chain", "effects"),
    "Hidden": ("hide", "effects"),
    "Disarming": ("disarm", "effects"),
    "Trade Places": ("trade_places", "effects"),
    "Regeneration": ("regeneration", "effects"),
    "Hitting Self": ("hit_self", "effects"),
    "Damage Reduction": ("damage_reduce", "effects"),
    "Damage Reduction Percent": ("damage_reduce_percent", "effects"),
    "Burning": ("burn", "effects"),
    "Life Steal": ("damage_as_life", "effects"),
    "Corrupt": ("corrupt", "effects"),
    "Stun": ("stun", "effects"),
    "Challange": ("challenge", "effects"),
    "Challenge": ("challenge", "effects"),
    "Deflection": ("deflection", "effects"),
    "Construct": ("construct", "effects_keys"),
    "Neutralize": ("neutralize", "effects"),
    "Hide Health": ("hide_health", "effects"),
    "Bleed": ("bleed", "effects"),
    "Revenge": ("revenge_counter", "effects"),
    "Strengh": ("strength", "effects"),
    "Strength": ("strength", "effects"),
    "Endurance": ("endurance", "effects"),
    "Dexterity": ("dexterity", "effects"),
    "Intelligence": ("intelligence", "effects"),
    "Willpower": ("willpower", "effects"),
    "Hit Chance": ("hit_chance", "effects"),
    "Parry Chance": ("parry_chance", "effects"),
    "Stamina": ("stamina", "effects"),
    "Silence": ("silence", "effects"),
    "Summon Weather": ("summon_weather", "effects_keys"),
    "Max Summon Count": ("summon_count", "effects"),
    "Sight": ("sight", "effects"),
    "Construct item cost": ("construct_item_cost", "effects"),
    "Reset Cooldown On Kill": ("reset_cooldown_on_kill", "effects"),
    "Consume Effect": ("consume_tick_damage", "effects"),
    "Bonus Damage Precent": ("damage_bonus_percent", "effects"),
    "Bonus Damage Percent": ("damage_bonus_percent", "effects"),
    "Effect On Targer": ("stacker", "effects_keys"),
    "Effect On Target": ("stacker", "effects_keys"),
    "Vulnerable": ("vulnerable", "effects"),
    "Knockback Damage": ("knockback_damage_percent", "effects"),
    "Burn stamina": ("burn_stamina", "effects"),
    "Health For Stamina": ("health_for_stamina", "effects"),
    "Thorns": ("thorns", "effects"),
    "Magic Deflection": ("magic_deflection", "effects"),
    "Pulls target": ("pull_target", "effects"),
    "Resistance Percent": ("resistance_percent", "effects"),
    "Repeat Ablility With Second Weapon": ("repeat_ability_second_weapon", "effects"),
    "Repeat Ability With Second Weapon": ("repeat_ability_second_weapon", "effects"),
    "Damage From Missing Health": ("damage_on_missing_health", "effects"),
    "Attack Speed": ("attack_speed", "effects"),
    "Damage From Missing Stamina": ("damage_on_missing_stamina", "effects"),
    "Increase Target Cooldown": ("increase_target_cooldown", "effects"),
    "Clear Cooldowns": ("clear_cooldowns", "effects"),
    "Magic Power Damage": ("magic_power_damage", "effects"),
    "Magic Power For Weapon Damage": ("magic_to_weapon_damage", "effects"),
    "Magic Power Per Entity": ("magic_power_per_entity", "effects"),
    "Critical Hit": ("critical_hit", "effects"),
    "Ability Critical Hits": ("ability_can_crit", "effects"),
}

AMPLIFIER_TOPLEVEL = {
    "cooldown",
    "cast_time",
    "duration",
    "range",
    "range_melee",
    "cost_stamina",
    "cost_health",
}

STACKER_FIELDS = {
    "max_stacks",
    "on_max_stacks_cast",
    "max_stacks_cast_unlock",
    "apply_caster",
    "duration",
}

PASSIVE_TOP_FIELDS = {
    "apply_mode",
    "restrict_tags",
    "restrict_tags_enemy",
    "restrict_weapon_type",
}

DAMAGE_TYPE_DISPLAY = {
    "Physical": "physical",
    "Fire": "fire",
    "Frost": "frost",
    "Electrical": "electricity",
    "Death": "death",
    "Nature": "nature",
    "Acid": "acid",
    "Holy": "holy",
    "None": "none",
    "True": "true",
}


def _schema_of(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        if len(value) == 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in value):
            return "int_pair"
        if value and all(isinstance(x, str) for x in value):
            return "string_list"
        return "list"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _compact(value: Any) -> Any:
    if isinstance(value, list) and len(value) > 8:
        return value[:8] + ["…"]
    return value


class _PassiveTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_table = False
        self.in_5_4 = False
        self.capture = False
        self.cell = 0
        self.row: List[str] = []
        self.buf: List[str] = []
        self.rows: List[Dict[str, str]] = []
        self._id = ""

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        ad = dict(attrs)
        if tag in ("h2", "h3") and ad.get("id") == "5.4-adding-passives":
            self.in_5_4 = True
        if tag == "table" and self.in_5_4:
            self.in_table = True
        if tag == "tr" and self.in_table:
            self.row = []
            self.cell = 0
        if tag == "td" and self.in_table:
            self.buf = []
            self.capture = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self.capture:
            text = re.sub(r"\s+", " ", "".join(self.buf)).strip()
            self.row.append(text)
            self.capture = False
        if tag == "tr" and self.in_table and self.row:
            if self.row[0] not in ("effect", ""):
                self.rows.append(
                    {
                        "id": self.row[0],
                        "value": self.row[1] if len(self.row) > 1 else "",
                        "secondary_value": self.row[2] if len(self.row) > 2 else "",
                        "third_value": self.row[3] if len(self.row) > 3 else "",
                        "example": self.row[4] if len(self.row) > 4 else "",
                    }
                )
            self.row = []
        if tag == "table" and self.in_table:
            self.in_table = False
            self.in_5_4 = False
        if tag in ("h2",) and self.in_5_4 and not self.in_table:
            self.in_5_4 = False

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.buf.append(data)


def parse_docs(index_html: Path) -> Dict[str, Any]:
    text = index_html.read_text(encoding="utf-8", errors="replace")
    p = _PassiveTableParser()
    p.feed(text)
    ability_docs: List[Dict[str, str]] = []
    # Only the effect list under "And it's effects", not cast-time / animation UI fields.
    m = re.search(
        r"And it's effects:</p>\s*(.*?)<p>\s*You can add as many effects as you want",
        text,
        re.S | re.I,
    )
    chunk = m.group(1) if m else ""
    for sm in re.finditer(r"<li>\s*<strong>([^<]+)</strong>\s*[-–]\s*(.*?)</li>", chunk, re.S | re.I):
        display = re.sub(r"\s+", " ", sm.group(1)).strip()
        desc = re.sub(r"<[^>]+>", "", sm.group(2))
        desc = re.sub(r"\s+", " ", desc).strip()
        mapped = ABILITY_DISPLAY_TO_KEY.get(display)
        key, path = mapped if mapped else (re.sub(r"[^a-z0-9]+", "_", display.lower()).strip("_"), "effects")
        ability_docs.append({"display": display, "id": key, "json_path": path, "description": desc})
    return {"passives": p.rows, "abilities": ability_docs}


def _iter_json_files(root: Path, rel: str) -> Iterable[Path]:
    folder = root / rel
    if not folder.is_dir():
        return []
    return [p for p in folder.rglob("*.json") if "translations" not in p.parts]


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def _fx_example(fx: Dict[str, Any], file: str) -> Dict[str, Any]:
    ex: Dict[str, Any] = {"file": file, "value": _compact(fx.get("value"))}
    if "secondary_value" in fx:
        ex["secondary_value"] = _compact(fx["secondary_value"])
    if "third_value" in fx:
        ex["third_value"] = _compact(fx["third_value"])
    return ex


def _record(
    store: Dict[str, Dict[str, Any]],
    *,
    eid: str,
    kind: str,
    json_path: str,
    value: Any,
    source: str,
    file: str,
    description: str = "",
    example: Optional[Dict[str, Any]] = None,
    docs_secondary: str = "",
    docs_third: str = "",
) -> None:
    rec = store.setdefault(
        f"{kind}:{eid}",
        {
            "id": eid,
            "kind": kind,
            "json_path": json_path,
            "schemas": defaultdict(int),
            "examples": [],
            "count": 0,
            "sources": set(),
            "description": description,
            "observed_values": [],
        },
    )
    rec["count"] += 1
    rec["sources"].add(source)
    rec["schemas"][_schema_of(value)] += 1
    if description and not rec["description"]:
        rec["description"] = description
    if docs_secondary and not rec.get("docs_secondary"):
        rec["docs_secondary"] = docs_secondary
    if docs_third and not rec.get("docs_third"):
        rec["docs_third"] = docs_third
    if len(rec["examples"]) < 4:
        rec["examples"].append(example or {"file": file, "value": _compact(value)})
    if isinstance(value, str) and value not in rec["observed_values"] and len(rec["observed_values"]) < 40:
        rec["observed_values"].append(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        nums = rec.setdefault("numeric_min_max", [value, value])
        nums[0] = min(nums[0], value)
        nums[1] = max(nums[1], value)


def mine_abilities(root: Path, source: str, store: Dict[str, Dict[str, Any]], extras: Dict[str, Any]) -> None:
    targets: Dict[str, int] = extras.setdefault("targets", defaultdict(int))
    for path in _iter_json_files(root, "abilities"):
        data = _load_json(path)
        if not isinstance(data, dict):
            continue
        t = data.get("target")
        if isinstance(t, str) and t:
            targets[t] += 1
        effects = data.get("effects")
        if isinstance(effects, dict):
            for k, v in effects.items():
                _record(store, eid=k, kind="ability", json_path=f"effects.{k}", value=v, source=source, file=str(path.name))
        keys = data.get("effects_keys") or data.get("effect_keys")
        if isinstance(keys, dict):
            for k, v in keys.items():
                _record(
                    store,
                    eid=k,
                    kind="ability_key",
                    json_path=f"effects_keys.{k}",
                    value=v,
                    source=source,
                    file=str(path.name),
                )


def mine_passives_file(path: Path, source: str, store: Dict[str, Dict[str, Any]]) -> None:
    data = _load_json(path)
    if not isinstance(data, list):
        return
    for item in data:
        if not isinstance(item, dict):
            continue
        for k in PASSIVE_TOP_FIELDS:
            if k not in item:
                continue
            _record(
                store,
                eid=k,
                kind="passive_field",
                json_path=k,
                value=item[k],
                source=source,
                file=path.name,
                description=f"Passive top-level field ({k}). apply_mode replaces only_party.",
            )
        for fx in item.get("effects") or []:
            if not isinstance(fx, dict) or not fx.get("effect"):
                continue
            eid = str(fx["effect"])
            secondary = fx.get("secondary_value")
            third = fx.get("third_value")
            _record(
                store,
                eid=eid,
                kind="passive",
                json_path="effects[].effect",
                value=fx.get("value"),
                source=source,
                file=path.name,
                example=_fx_example(fx, path.name),
                docs_secondary=f"{_schema_of(secondary)} (observed)" if "secondary_value" in fx else "",
                docs_third=f"{_schema_of(third)} (observed)" if "third_value" in fx else "",
            )


def mine_amplifiers_file(path: Path, source: str, store: Dict[str, Dict[str, Any]]) -> None:
    data = _load_json(path)
    if not isinstance(data, list):
        return
    for item in data:
        if not isinstance(item, dict):
            continue
        for fx in item.get("bonuses") or []:
            if not isinstance(fx, dict) or not fx.get("effect"):
                continue
            eid = str(fx["effect"])
            _record(
                store,
                eid=eid,
                kind="amplifier",
                json_path="bonuses[].effect",
                value=fx.get("value"),
                source=source,
                file=path.name,
                example=_fx_example(fx, path.name),
            )
        for k in AMPLIFIER_TOPLEVEL:
            if k in item:
                _record(
                    store,
                    eid=k,
                    kind="amplifier_field",
                    json_path=k,
                    value=item[k],
                    source=source,
                    file=path.name,
                    description=f"Amplifier top-level field applied to the socketed ability ({k}).",
                )


def mine_stackers_file(path: Path, source: str, store: Dict[str, Dict[str, Any]]) -> None:
    data = _load_json(path)
    if not isinstance(data, list):
        return
    for item in data:
        if not isinstance(item, dict):
            continue
        for fx in item.get("effects") or []:
            if not isinstance(fx, dict) or not fx.get("effect"):
                continue
            eid = str(fx["effect"])
            _record(
                store,
                eid=eid,
                kind="stacker",
                json_path="ability_stackers.effects[].effect",
                value=fx.get("value"),
                source=source,
                file=path.name,
                example=_fx_example(fx, path.name),
            )
        for k in STACKER_FIELDS:
            if k not in item:
                continue
            _record(
                store,
                eid=k,
                kind="stacker_field",
                json_path=f"ability_stackers.{k}",
                value=item[k],
                source=source,
                file=path.name,
                description=f"ability_stackers.json field ({k}).",
            )


def mine_messages(path: Path) -> Dict[str, Any]:
    data = _load_json(path) or {}
    enums: Dict[str, Any] = {}
    if isinstance(data.get("damage_type"), list):
        enums["damage_type"] = []
        for i, row in enumerate(data["damage_type"]):
            name = row.get("name") if isinstance(row, dict) else str(row)
            json_id = DAMAGE_TYPE_DISPLAY.get(str(name), str(name).lower())
            enums["damage_type"].append({"index": i, "display": name, "id": json_id})
    if isinstance(data.get("statistics"), list):
        enums["statistics"] = [
            {"display": r.get("name"), "id": str(r.get("name", "")).lower()}
            for r in data["statistics"]
            if isinstance(r, dict)
        ]
    if isinstance(data.get("item_type"), list):
        enums["item_type"] = []
        for i, row in enumerate(data["item_type"]):
            name = row.get("name") if isinstance(row, dict) else str(row)
            enums["item_type"].append({"index": i, "display": name, "id": str(name).lower().replace(" ", "_")})
    if isinstance(data.get("tool_types"), list):
        enums["tool_types"] = [
            {"id": r.get("id"), "name": r.get("name")} for r in data["tool_types"] if isinstance(r, dict)
        ]
    return enums


def mine_skills_file(path: Path, source: str, store: Dict[str, Dict[str, Any]]) -> None:
    data = _load_json(path)
    if not isinstance(data, list):
        return
    for item in data:
        if not isinstance(item, dict) or "level_start" not in item:
            continue
        _record(
            store,
            eid="level_start",
            kind="skill_field",
            json_path="skills.json.level_start",
            value=item["level_start"],
            source=source,
            file=path.name,
            description="Optional skills.json starting level for this skill.",
        )


def mine_milestones(root: Path, source: str, store: Dict[str, Dict[str, Any]]) -> None:
    folder = root / "milestones"
    if not folder.is_dir():
        return
    for path in folder.rglob("*.json"):
        if "translations" in path.parts:
            continue
        data = _load_json(path)
        if not isinstance(data, dict) or not data.get("innate"):
            continue
        _record(
            store,
            eid="innate",
            kind="milestone_field",
            json_path="milestones.innate",
            value=True,
            source=source,
            file=path.name,
            description="Innate milestones skip skill level-up checks. Empty requirements. Grant on entities via skills.milestones.",
        )


def mine_character_stats(path: Path, source: str, extras: Dict[str, Any]) -> None:
    data = _load_json(path)
    if not isinstance(data, dict):
        return
    keys = extras.setdefault("race_statistics", set())
    for race in data.get("races") or []:
        if not isinstance(race, dict):
            continue
        stats = race.get("statistics")
        if isinstance(stats, dict):
            keys.update(stats.keys())


def _workshop_skill_mods(ws: Path) -> List[Path]:
    out = []
    for child in sorted(ws.iterdir()):
        if not child.is_dir() or skip_mod_path(child):
            continue
        if (child / "skills.json").is_file():
            out.append(child)
    return out


def mine_all() -> Dict[str, Any]:
    game = soulash2_root()
    core = core2_dir(game)
    docs = docs_index(game)
    store: Dict[str, Dict[str, Any]] = {}
    extras: Dict[str, Any] = {}
    docs_data = parse_docs(docs) if docs.is_file() else {"passives": [], "abilities": []}

    for row in docs_data["passives"]:
        _record(
            store,
            eid=row["id"],
            kind="passive",
            json_path="effects[].effect",
            value=None,
            source="docs",
            file="index.html#5.4",
            description=row.get("example") or "",
        )
        rec = store[f"passive:{row['id']}"]
        rec["docs_value"] = row.get("value")
        rec["docs_secondary"] = row.get("secondary_value")
        rec["docs_third"] = row.get("third_value")
        rec["description"] = row.get("example") or rec.get("description") or ""

    for row in docs_data["abilities"]:
        kind = "ability_key" if row["json_path"] == "effects_keys" else "ability"
        path = f"effects_keys.{row['id']}" if kind == "ability_key" else f"effects.{row['id']}"
        _record(
            store,
            eid=row["id"],
            kind=kind,
            json_path=path,
            value=None,
            source="docs",
            file="index.html#6.2",
            description=row["description"],
        )
        rec = store[f"{kind}:{row['id']}"]
        rec["display"] = row["display"]

    mine_abilities(core, "core_2", store, extras)
    mine_passives_file(core / "passives.json", "core_2", store)
    mine_amplifiers_file(core / "ability_amplifiers.json", "core_2", store)
    if (core / "ability_stackers.json").is_file():
        mine_stackers_file(core / "ability_stackers.json", "core_2", store)
    if (core / "skills.json").is_file():
        mine_skills_file(core / "skills.json", "core_2", store)
    mine_milestones(core, "core_2", store)
    if (core / "character.json").is_file():
        mine_character_stats(core / "character.json", "core_2", extras)

    ws = workshop_root()
    workshop_mods: List[str] = []
    if ws:
        for mod in _workshop_skill_mods(ws):
            workshop_mods.append(mod.name)
            mine_abilities(mod, "workshop", store, extras)
            if (mod / "passives.json").is_file():
                mine_passives_file(mod / "passives.json", "workshop", store)
            if (mod / "ability_amplifiers.json").is_file():
                mine_amplifiers_file(mod / "ability_amplifiers.json", "workshop", store)
            if (mod / "ability_stackers.json").is_file():
                mine_stackers_file(mod / "ability_stackers.json", "workshop", store)
            if (mod / "skills.json").is_file():
                mine_skills_file(mod / "skills.json", "workshop", store)
            mine_milestones(mod, "workshop", store)
            if (mod / "character.json").is_file():
                mine_character_stats(mod / "character.json", "workshop", extras)

    known_by_kind: Dict[str, set] = defaultdict(set)
    for rec in store.values():
        known_by_kind[rec["kind"]].add(rec["id"])
    exe_payload: Dict[str, Any] = {"exe": None, "ids": [], "clusters": []}
    try:
        exe_path = soulash2_exe(game)
        exe_payload = mine_exe(exe_path, {k: set(v) for k, v in known_by_kind.items()})
        extras["exe"] = exe_payload
        for row in exe_payload.get("ids") or []:
            eid = str(row["id"])
            guess = str(row.get("kind_guess") or "unconfirmed")
            if guess == "target" or eid in TARGET_IDS:
                extras.setdefault("exe_targets", set()).add(eid)
                continue
            if guess == "ability_schema":
                continue
            kind = {
                "ability": "ability",
                "ability_key": "ability_key",
                "passive": "passive",
                "amplifier": "amplifier",
                "amplifier_field": "amplifier_field",
                "passive_field": "passive_field",
                "stacker": "stacker",
                "stacker_field": "stacker_field",
            }.get(guess, "unconfirmed")
            json_path = {
                "ability": f"effects.{eid}",
                "ability_key": f"effects_keys.{eid}",
                "passive": "effects[].effect",
                "amplifier": "bonuses[].effect",
                "amplifier_field": eid,
                "stacker": "ability_stackers.effects[].effect",
                "stacker_field": f"ability_stackers.{eid}",
            }.get(kind, f"exe.{eid}")
            attached = False
            for rec in store.values():
                if rec["id"] == eid:
                    rec["sources"].add("exe")
                    attached = True
            if attached:
                continue
            _record(
                store,
                eid=eid,
                kind=kind,
                json_path=json_path,
                value=None,
                source="exe",
                file="Soulash 2.exe",
                description="Found in Soulash 2.exe string table; not seen in JSON or docs.",
            )
    except FileNotFoundError:
        extras["exe_error"] = "Soulash 2.exe not found"

    enums = mine_messages(core / "messages.json")
    target_set = set(extras.get("targets") or {})
    target_set |= set(extras.get("exe_targets") or [])
    target_set |= set(TARGET_IDS)
    enums["target"] = sorted(target_set)
    enums["amplifier_type"] = ["offensive", "defensive", "utility"]
    enums["exp_source"] = [
        "location_discovery",
        "location_details_discovery",
        "resource_discovery",
        "attack",
        "parry",
        "ability",
        "craft",
        "upgrade_item",
        "drag",
        "throw",
        "climb",
        "salvage",
        "settle",
        "jump_down",
        "walk",
        "carve",
        "production",
    ]
    enums["milestone_reward"] = ["ability", "passive", "amplifier", "recipe", "production_action"]
    enums["apply_mode"] = ["party_only", "solo_only"]
    race_stats = sorted(extras.get("race_statistics") or [])
    if race_stats:
        enums["race_statistics"] = race_stats

    effects: List[Dict[str, Any]] = []
    for rec in store.values():
        schemas = dict(rec["schemas"])
        primary = max(schemas, key=schemas.get) if schemas else "unknown"
        sources = sorted(rec["sources"])
        if "core_2" in sources:
            confidence = "vanilla"
        elif sources == ["exe"]:
            confidence = "unconfirmed"
        elif "workshop" in sources:
            confidence = "workshop"
        else:
            confidence = "docs_unused"
        effects.append(
            {
                "id": rec["id"],
                "kind": rec["kind"],
                "json_path": rec["json_path"],
                "value_schema": primary,
                "schemas": schemas,
                "valid_values": rec.get("observed_values") or None,
                "numeric_min_max": rec.get("numeric_min_max"),
                "description": rec.get("description") or "",
                "display": rec.get("display"),
                "docs_value": rec.get("docs_value"),
                "docs_secondary": rec.get("docs_secondary"),
                "docs_third": rec.get("docs_third"),
                "examples": rec["examples"],
                "count": rec["count"],
                "sources": sources,
                "confidence": confidence,
            }
        )
    effects.sort(key=lambda e: (e["kind"], e["id"]))
    apply_patch_overlay(effects)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "game": str(game),
        "workshop_mods": workshop_mods,
        "exe": exe_payload.get("exe"),
        "exe_id_count": len(exe_payload.get("ids") or []),
        "effects": effects,
        "enums": enums,
        "targets": dict(extras.get("targets") or {}),
        "exe_clusters": exe_payload.get("clusters") or [],
    }


def write_catalog(payload: Dict[str, Any]) -> Tuple[Path, Path, Path]:
    cat = catalog_dir()
    effects_path = cat / "effects.json"
    enums_path = cat / "enums.json"
    md_path = cat / "EFFECTS.md"
    effects_path.write_text(json.dumps({"generated_at": payload["generated_at"], "effects": payload["effects"]}, indent=2), encoding="utf-8")
    enums_path.write_text(json.dumps(payload["enums"], indent=2), encoding="utf-8")
    (cat / "exe_strings.json").write_text(
        json.dumps(
            {
                "exe": payload.get("exe"),
                "id_count": payload.get("exe_id_count"),
                "clusters": payload.get("exe_clusters"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    lines = [
        "# Soulash 2 skill effect catalog",
        "",
        f"Generated {payload['generated_at']}",
        "",
        "Sources: official `data/docs/index.html`, vanilla `core_2`, Steam Workshop skill mods, `Soulash 2.exe` strings, `catalog/patch_overlay.json`.",
        "Hydromancy is excluded. EXE-only ids are `unconfirmed`. Patch overlay ids are `patch` (dropdown-valid).",
        "",
        "## Enums",
        "",
        f"- damage_type: {', '.join(x['id'] for x in payload['enums'].get('damage_type') or [])}",
        f"- target: {', '.join(payload['enums'].get('target') or [])}",
        f"- amplifier type: {', '.join(payload['enums'].get('amplifier_type') or [])}",
        "",
        "## Effects",
        "",
        "| kind | id | schema | count | confidence | description |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for e in payload["effects"]:
        desc = (e.get("description") or "").replace("|", "/").replace("\n", " ")[:120]
        lines.append(
            f"| {e['kind']} | `{e['id']}` | {e['value_schema']} | {e['count']} | {e['confidence']} | {desc} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return effects_path, enums_path, md_path


def main() -> int:
    payload = mine_all()
    e, n, m = write_catalog(payload)
    kinds: Dict[str, int] = defaultdict(int)
    for fx in payload["effects"]:
        kinds[fx["kind"]] += 1
    print(f"Wrote {e}")
    print(f"Wrote {n}")
    print(f"Wrote {m}")
    print("Counts:", dict(kinds), "total", len(payload["effects"]))
    print("Workshop mods:", ", ".join(payload["workshop_mods"]) or "(none)")
    print("EXE:", payload.get("exe"), "ids", payload.get("exe_id_count"))
    unconf = sum(1 for fx in payload["effects"] if fx.get("confidence") == "unconfirmed")
    print("Unconfirmed (exe-only):", unconf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
