#!/usr/bin/env python3
"""Load mined effect catalog and type-check values."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from s2_paths import catalog_dir

_CACHE: Dict[str, Any] = {}


JSON_PATH_FOR_KIND = {
    "ability": "effects.{id}",
    "ability_key": "effects_keys.{id}",
    "passive": "effects[].effect",
    "amplifier": "bonuses[].effect",
    "amplifier_field": "{id}",
    "passive_field": "{id}",
    "stacker": "ability_stackers.effects[].effect",
    "stacker_field": "ability_stackers.{id}",
    "skill_field": "skills.json.{id}",
    "milestone_field": "milestones.{id}",
}


def apply_patch_overlay(effects: List[Dict[str, Any]]) -> None:
    """Merge catalog/patch_overlay.json into a live effects list (Warlock-confirmed ids, docs gaps)."""
    path = catalog_dir() / "patch_overlay.json"
    if not path.is_file():
        return
    try:
        overlay = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Failed to load catalog/patch_overlay.json: {exc}", file=sys.stderr)
        return
    by_key = {(e.get("kind"), e.get("id")): e for e in effects}
    for row in overlay.get("effects") or []:
        if not isinstance(row, dict) or not row.get("id") or not row.get("kind"):
            continue
        key = (row["kind"], row["id"])
        dest = by_key.get(key)
        if dest is None:
            kind = str(row["kind"])
            dest = {
                "id": row["id"],
                "kind": kind,
                "json_path": JSON_PATH_FOR_KIND.get(kind, kind).format(id=row["id"]),
                "value_schema": "unknown",
                "schemas": {},
                "valid_values": None,
                "numeric_min_max": None,
                "description": "",
                "display": None,
                "docs_value": None,
                "docs_secondary": None,
                "docs_third": None,
                "examples": [],
                "count": 0,
                "sources": ["patch"],
                "confidence": row.get("confidence") or "patch",
            }
            effects.append(dest)
            by_key[key] = dest
        for field in ("description", "docs_value", "docs_secondary", "docs_third", "display"):
            if row.get(field):
                dest[field] = row[field]
        srcs = set(dest.get("sources") or [])
        srcs.add("patch")
        dest["sources"] = sorted(srcs)
        wanted = row.get("confidence")
        current = dest.get("confidence")
        if wanted == "patch" and current in ("unconfirmed", "docs_unused", None, "", "workshop"):
            dest["confidence"] = "patch"
        elif current == "unconfirmed":
            dest["confidence"] = wanted or "patch"
        elif not current:
            dest["confidence"] = wanted or "patch"
    effects.sort(key=lambda e: (e["kind"], e["id"]))


def load_effects() -> List[Dict[str, Any]]:
    path = catalog_dir() / "effects.json"
    if "effects" not in _CACHE:
        if not path.is_file():
            rows: List[Dict[str, Any]] = []
        else:
            rows = json.loads(path.read_text(encoding="utf-8")).get("effects") or []
        apply_patch_overlay(rows)
        _CACHE["effects"] = rows
    return _CACHE["effects"]


def load_enums() -> Dict[str, Any]:
    path = catalog_dir() / "enums.json"
    if "enums" not in _CACHE:
        if not path.is_file():
            _CACHE["enums"] = {}
        else:
            _CACHE["enums"] = json.loads(path.read_text(encoding="utf-8"))
    return _CACHE["enums"]


def reload() -> None:
    _CACHE.clear()


def find_effect(eid: str, kind: Optional[str] = None) -> Optional[Dict[str, Any]]:
    hits = [e for e in load_effects() if e["id"] == eid and (kind is None or e["kind"] == kind)]
    if not hits:
        return None
    if kind:
        return hits[0]
    for prefer in ("ability", "amplifier", "passive", "ability_key", "amplifier_field"):
        for e in hits:
            if e["kind"] == prefer:
                return e
    return hits[0]


def list_effects(kind: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = load_effects()
    if kind:
        if kind == "amplifier":
            return [e for e in rows if e["kind"] in ("amplifier", "amplifier_field")]
        return [e for e in rows if e["kind"] == kind]
    return rows


# In-game ability editor list, grouped more tightly than the flat F2 dropdown.
_ABILITY_GROUPS: List[Tuple[str, set]] = [
    (
        "Damage",
        {
            "damage",
            "damage_type",
            "damage_bonus",
            "damage_bonus_percent",
            "damage_weapon",
            "skill_level_damage",
            "distance_damage",
            "damage_on_missing_health",
            "damage_on_missing_stamina",
            "damage_as_life",
            "damage_from_thorns",
            "damage_without_companions",
            "dmg_per_companion",
            "dmg_on_cooldown",
            "magic_power_damage",
            "magic_to_weapon_damage",
            "weapon_damage_to_magic",
            "ability_damage_multiplier",
            "knockback_damage_percent",
            "damage_receive_bonus_percent",
            "damage_to_bloodlust",
            "bleed_per_damage",
            "magic_power",
            "magic_power_per_entity",
            "magic_power_per_tag",
        },
    ),
    (
        "Status",
        {
            "bleed",
            "burn",
            "stun",
            "fear",
            "poison_effect",
            "silence",
            "corrupt",
            "vulnerable",
            "immobilize",
            "disarm",
            "challenge",
            "hide",
            "frostbite",
            "burning_light",
            "fertility",
            "neutralize",
            "consume_tick_damage",
            "stacker",
            "increase_effect",
            "power_up",
            "disadvantage",
        },
    ),
    (
        "Defense",
        {
            "damage_reduce",
            "damage_reduce_percent",
            "resistance",
            "resistance_percent",
            "parry_chance",
            "deflection",
            "magic_deflection",
            "hide_health",
            "thorns",
            "always_hit",
            "hit_chance",
            "ability_can_crit",
            "critical_hit",
            "break_armor",
        },
    ),
    (
        "Movement / targeting",
        {
            "knockback",
            "lunge",
            "charge",
            "rollback",
            "pull_target",
            "pierce",
            "chain",
            "trade_places",
            "movement_speed",
            "aoe_range",
            "aoe_shape",
            "aoe_break",
            "hit_self",
            "ignore_party",
            "move_to_side",
            "copy_to_party",
        },
    ),
    (
        "Summon / entity",
        {
            "summon",
            "summon_on_move",
            "summon_count",
            "summon_weather",
            "construct",
            "construct_item_cost",
            "sense",
            "aura",
            "transform",
            "cage",
            "restrict_to_tag",
            "stacker_to_dot",
        },
    ),
    (
        "Stats / recovery",
        {
            "strength",
            "endurance",
            "dexterity",
            "intelligence",
            "willpower",
            "stamina",
            "sight",
            "attack_speed",
            "heal",
            "regeneration",
            "full_vision",
            "light_source",
            "stamina_regen",
            "cast_heals",
        },
    ),
    (
        "Cooldown / cost",
        {
            "reset_cooldown_on_kill",
            "clear_cooldowns",
            "increase_target_cooldown",
            "health_for_stamina",
            "burn_stamina",
            "repeat_ability_second_weapon",
            "reduce_random_cooldown",
            "remove_on_next_ability",
            "revenge_counter",
        },
    ),
]


def _effect_label(row: Dict[str, Any]) -> str:
    display = (row.get("display") or "").strip()
    if display:
        return display
    return str(row.get("id") or "").replace("_", " ")


def _ability_group(eid: str, kind: str) -> str:
    if kind == "ability_key":
        return "Summon / entity"
    for name, ids in _ABILITY_GROUPS:
        if eid in ids:
            return name
    return "Other valid effects"


def _is_dropdown_valid(row: Dict[str, Any]) -> bool:
    if row.get("confidence") == "unconfirmed":
        return False
    if row.get("kind") in ("amplifier_field", "stacker_field", "stacker", "passive_field", "skill_field", "milestone_field"):
        return False
    return True


# Counts shipped content actually uses. Official docs say "as many as you want."
# The exe does not publish caps. The F2 editor may wipe or fail to show extra
# rows past these counts; JSON written by this CLI can still work in-game.
OBSERVED_LIMITS = {
    "ability_effects": {
        "normal": 8,
        "seen": 8,
        "label": "ability effects + effects_keys",
        "note": "F2 editor wipes past 8. Hand-written JSON may still load.",
    },
    "amplifier_bonuses": {
        "normal": 2,
        "seen": 3,
        "label": "amplifier bonuses",
        "note": "Vanilla typically 2; workshop JSON has used 3. Top-level cooldown/range/cost do not count.",
    },
    "passive_effects": {
        "normal": 3,
        "seen": 6,
        "label": "passive effects",
        "note": "Vanilla typically 3; workshop JSON has used 6 (Skill Stat Rebalance masteries use 5).",
    },
    "ability_slots_total": {
        "normal": 4,
        "seen": 8,
        "label": "amplifier slots (all colors)",
        "note": "Vanilla typical total. Higher totals exist in test JSON. Color counts are separate.",
    },
    "stacker_effects": {
        "normal": 2,
        "seen": 2,
        "label": "stacker effects",
        "note": "Vanilla/workshop use 1–2 per-stack bonuses. 0 is valid when on_max_stacks_cast is set (Blessed Knuckles).",
    },
    "warning": (
        "Observed counts (vanilla, workshop, F2 editor). The in-game editor may wipe or "
        "fail to show extra rows; JSON authored here can still work. The game does not "
        "publish an engine cap."
    ),
}


def observed_limits() -> Dict[str, Any]:
    return OBSERVED_LIMITS


def observed_count_warning(key: str, count: int) -> Optional[str]:
    """Warn only when a count exceeds anything observed. Silent inside that range."""
    meta = OBSERVED_LIMITS.get(key) or {}
    typical = int(meta.get("normal") or 0)
    seen = int(meta.get("seen") or typical)
    if count <= seen:
        return None
    label = str(meta.get("label") or key)
    return (
        f"{count} {label} (vanilla typically {typical}; highest observed {seen}). "
        "The F2 editor may wipe extra rows; JSON authored here can still work. "
        "The game does not publish an engine cap."
    )


VALID_WHERE = {
    "ability": {
        "place": "Ability",
        "how": "Numeric/status fields on the ability `effects` object. One key per type. Vanilla/F2 typically 8 effects+keys together; the F2 editor may wipe past that, JSON can still load.",
        "path": "effects.{id}",
    },
    "ability_key": {
        "place": "Ability (entity / ability ref)",
        "how": "String ids on `effects_keys` (summon, construct, stacker, sense, aura, transform, cage, …). Counts toward the ability effect total (vanilla/F2 typically 8).",
        "path": "effects_keys.{id}",
    },
    "amplifier": {
        "place": "Amplifier / augment",
        "how": "`bonuses[]` entries `{effect, value, secondary_value?, third_value?}`. Docs: same bonuses as abilities. Vanilla typically 2; workshop JSON has used 3.",
        "path": "bonuses[].effect",
    },
    "amplifier_field": {
        "place": "Amplifier top-level",
        "how": "Not a bonus row. Put the field on the amplifier object itself (`cooldown`, `cast_time`, `range`, `cost_stamina`, …).",
        "path": "{id}",
    },
    "passive": {
        "place": "Passive",
        "how": "`effects[]` entries `{effect, value, secondary_value?, third_value?}`. Always on while the passive is unlocked. Vanilla typically 3; workshop JSON has used 6. Use `apply_mode` (party_only/solo_only), not `only_party`.",
        "path": "effects[].effect",
    },
    "passive_field": {
        "place": "Passive object",
        "how": "Top-level on the passive, not an effects[] row. `apply_mode` replaces `only_party`. `restrict_tags` / `restrict_tags_enemy` / `restrict_weapon_type` gate when it applies.",
        "path": "{id}",
    },
    "skill_field": {
        "place": "skills.json entry",
        "how": "Optional field on the skill object itself (e.g. `level_start`).",
        "path": "{id}",
    },
    "milestone_field": {
        "place": "Milestone object",
        "how": "`innate: true` with empty `requirements`. Grant on entities via `skills.milestones` (not a skill-tree unlock check).",
        "path": "{id}",
    },
    "stacker": {
        "place": "Stacker",
        "how": "`ability_stackers.json` effect list (movement_speed, attack_speed, … per stack). Vanilla/workshop typically 1–2.",
        "path": "ability_stackers.effects[].effect",
    },
    "stacker_field": {
        "place": "Stacker field",
        "how": "Stacker object fields such as `max_stacks` and `on_max_stacks_cast`.",
        "path": "ability_stackers.{id}",
    },
}


def effect_cards() -> Dict[str, Any]:
    """Per-id explanation: what it does and where it is valid."""
    if "cards" in _CACHE:
        return _CACHE["cards"]
    by_id: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in load_effects():
        by_id[str(row.get("id") or "")].append(row)
    cards: Dict[str, Any] = {}
    for eid, rows in by_id.items():
        if not eid:
            continue
        kinds = sorted({str(r.get("kind") or "") for r in rows})
        valid = []
        seen_place = set()
        for kind in kinds:
            info = VALID_WHERE.get(kind)
            if not info or info["place"] in seen_place:
                continue
            seen_place.add(info["place"])
            valid.append(
                {
                    "kind": kind,
                    "place": info["place"],
                    "how": info["how"],
                    "path": info["path"].format(id=eid),
                }
            )
        if "ability" in kinds and "amplifier" not in kinds and "ability_key" not in kinds:
            info = VALID_WHERE["amplifier"]
            if info["place"] not in seen_place:
                valid.append(
                    {
                        "kind": "amplifier",
                        "place": info["place"],
                        "how": "Official docs: amplifier bonuses are the same set as ability effects.",
                        "path": "bonuses[].effect",
                    }
                )
        descs = [str(r.get("description") or "").strip() for r in rows]
        descs = [d for d in descs if d and not d.startswith("Found in Soulash 2.exe")]
        descs.sort(key=len, reverse=True)
        docs_bits = []
        for r in rows:
            if r.get("docs_value"):
                docs_bits.append(f"value: {r['docs_value']}")
            if r.get("docs_secondary"):
                docs_bits.append(f"secondary_value: {r['docs_secondary']}")
            if r.get("docs_third"):
                docs_bits.append(f"third_value: {r['docs_third']}")
        docs_bits = list(dict.fromkeys(docs_bits))
        examples = []
        seen_ex = set()
        for r in rows:
            for ex in r.get("examples") or []:
                if not isinstance(ex, dict) or ex.get("file") == "Soulash 2.exe":
                    continue
                key = (
                    ex.get("file"),
                    json.dumps((ex.get("value"), ex.get("secondary_value"), ex.get("third_value")), default=str),
                )
                if key in seen_ex:
                    continue
                seen_ex.add(key)
                row_ex = {"file": ex.get("file"), "value": ex.get("value")}
                if "secondary_value" in ex:
                    row_ex["secondary_value"] = ex["secondary_value"]
                if "third_value" in ex:
                    row_ex["third_value"] = ex["third_value"]
                examples.append(row_ex)
                if len(examples) >= 4:
                    break
            if len(examples) >= 4:
                break
        label = ""
        for r in rows:
            if r.get("display"):
                label = str(r["display"])
                break
        if not label:
            label = eid.replace("_", " ")
        schemas = sorted({str(r.get("value_schema") or "unknown") for r in rows if r.get("value_schema")})
        sources = sorted({s for r in rows for s in (r.get("sources") or [])})
        confs = [str(r.get("confidence") or "") for r in rows]
        confidence = ""
        for prefer in ("vanilla", "patch", "workshop", "docs", "docs_unused"):
            if prefer in confs:
                confidence = prefer
                break
        if not confidence:
            confidence = confs[0] if confs else ""
        does = descs[0] if descs else ""
        if not does and examples:
            does = "No docs blurb; seen in game data (examples below)."
        if not does:
            does = "No description mined from docs or JSON. Treat as engine-supported if it appears in the valid-in list."
        cards[eid] = {
            "id": eid,
            "label": label,
            "does": does,
            "valid_in": valid,
            "schemas": schemas,
            "docs_fields": docs_bits,
            "examples": examples,
            "sources": sources,
            "confidence": confidence,
            "kinds": kinds,
        }
    _CACHE["cards"] = cards
    return cards


def _choice(row: Dict[str, Any], group: str, card: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    card = card or {}
    return {
        "id": row["id"],
        "kind": row["kind"],
        "label": _effect_label(row),
        "group": group,
        "schema": row.get("value_schema") or "unknown",
        "description": (row.get("description") or card.get("does") or ""),
        "json_path": row.get("json_path") or "",
        "confidence": row.get("confidence"),
        "valid_in": [v["place"] for v in card.get("valid_in") or []],
    }


def dropdowns() -> Dict[str, Any]:
    """Valid in-game-style effect lists for the studio dropdowns (no exe-only guesses)."""
    effects = load_effects()
    enums = load_enums()
    cards = effect_cards()
    ability: List[Dict[str, Any]] = []
    amplifier: List[Dict[str, Any]] = []
    passive: List[Dict[str, Any]] = []
    stacker: List[Dict[str, Any]] = []
    seen_amp: set = set()
    seen_st: set = set()
    stacker_extra = {
        "intelligence",
        "strength",
        "regeneration",
        "stamina_regen",
        "bonus_damage",
        "bonus_damage_percent",
        "damage_bonus",
        "damage_bonus_percent",
        "attack_speed",
        "movement_speed",
        "hit_chance",
        "parry_chance",
        "critical_hit",
        "resistance",
        "resistance_percent",
        "thorns",
        "ability_damage_multiplier",
    }
    for row in effects:
        kind = row.get("kind")
        eid = row.get("id")
        card = cards.get(str(eid))
        if row.get("confidence") != "unconfirmed" and eid and eid not in seen_st:
            if kind == "stacker" or (kind in ("ability", "passive") and eid in stacker_extra):
                stacker.append(_choice(row, "Per-stack bonuses", card))
                seen_st.add(eid)
        if not _is_dropdown_valid(row):
            continue
        if kind in ("ability", "ability_key"):
            ability.append(_choice(row, _ability_group(str(eid), str(kind)), card))
        if kind == "passive":
            group = "Documented passives" if row.get("display") or "docs" in (row.get("sources") or []) else "Vanilla / workshop passives"
            if row.get("confidence") == "docs_unused":
                group = "Documented passives"
            passive.append(_choice(row, group, card))
        if kind in ("ability", "amplifier"):
            # Docs 5.3: amplifier bonuses are the same set as ability effects.
            if eid not in seen_amp:
                seen_amp.add(eid)
                amplifier.append(_choice(row, _ability_group(str(eid), "ability" if kind == "ability" else str(kind)), card))

    def _sort(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        group_order = [name for name, _ in _ABILITY_GROUPS] + [
            "Summon / entity",
            "Other valid effects",
            "Documented passives",
            "Vanilla / workshop passives",
            "Per-stack bonuses",
            "amplifier",
        ]
        return sorted(
            rows,
            key=lambda r: (
                group_order.index(r["group"]) if r["group"] in group_order else 99,
                r["label"].lower(),
                r["id"],
            ),
        )

    targets = enums.get("target") or []
    if isinstance(targets, dict):
        targets = list(targets.keys())
    damage = enums.get("damage_type") or []
    return {
        "ability": _sort(ability),
        "amplifier": _sort(amplifier),
        "passive": _sort(passive),
        "stacker": _sort(stacker),
        "target": [{"id": t, "label": t} for t in targets],
        "damage_type": [
            {"id": d.get("id"), "label": d.get("display") or d.get("id")}
            for d in damage
            if isinstance(d, dict)
        ],
        "amplifier_type": list(enums.get("amplifier_type") or ["offensive", "defensive", "utility"]),
        "exp_source": [{"id": s, "label": s} for s in (enums.get("exp_source") or [])],
        "tool_types": [
            {"id": t.get("id"), "label": t.get("name") or str(t.get("id"))}
            for t in (enums.get("tool_types") or [])
            if isinstance(t, dict)
        ],
    }


def infer_amplifier_type(bonus_effect: str) -> str:
    offensive = {
        "damage",
        "bleed",
        "burn",
        "poison_effect",
        "bonus_damage",
        "damage_bonus_percent",
        "skill_level_damage",
        "damage_on_missing_health",
        "damage_on_missing_stamina",
        "chain",
        "pierce",
        "frostbite",
        "burning_light",
    }
    defensive = {
        "damage_reduce",
        "damage_reduce_percent",
        "parry_chance",
        "resistance",
        "resistance_percent",
        "thorns",
        "deflection",
        "magic_deflection",
        "hide_health",
    }
    if bonus_effect in offensive:
        return "offensive"
    if bonus_effect in defensive:
        return "defensive"
    return "utility"


def parse_value(raw: str) -> Any:
    text = raw.strip()
    # Do not coerce true/false to bool. Soulash damage_type includes "true"
    # (Warlock Eldritch Blast, Rend). Use JSON true/false only inside [...] / {...}.
    if text.startswith("[") or text.startswith("{"):
        return json.loads(text)
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def parse_kv(item: str) -> Tuple[str, Any, Optional[Any], Optional[Any]]:
    """Parse `key=value`, `key=value:secondary`, or `key=value:secondary:third`."""
    text = (item or "").strip()
    if "=" not in text:
        raise ValueError(f"Expected key=value, got {item!r}")
    key, _, rest = text.partition("=")
    parts = [p.strip() for p in rest.split(":")]
    value = parse_value(parts[0]) if parts and parts[0] != "" else None
    secondary = parse_value(parts[1]) if len(parts) > 1 and parts[1] != "" else None
    third = parse_value(parts[2]) if len(parts) > 2 and parts[2] != "" else None
    return key.strip(), value, secondary, third


def bonus_from_kv(item: str) -> Dict[str, Any]:
    key, value, secondary, third = parse_kv(item)
    row: Dict[str, Any] = {"effect": key}
    if value is not None:
        row["value"] = value
    if secondary is not None:
        row["secondary_value"] = secondary
    if third is not None:
        row["third_value"] = third
    return row


def is_effects_keys_id(eid: str) -> bool:
    # Only string-id refs. Catalog sometimes tags numeric fields as ability_key
    # (e.g. magic_power_damage); those belong on effects, not effects_keys.
    return eid in {
        "summon",
        "summon_on_move",
        "construct",
        "transform",
        "aura",
        "sense",
        "stacker",
        "cage",
    }


def apply_ability_kv(ability: Dict[str, Any], item: str) -> None:
    key, value, _, _ = parse_kv(item)
    if is_effects_keys_id(key):
        ability.setdefault("effects_keys", {})[key] = value
    else:
        ability.setdefault("effects", {})[key] = value


def slug_name(name: str) -> str:
    out = []
    for ch in name.strip():
        if ch.isalnum():
            out.append(ch)
        elif ch in (" ", "-", "_"):
            out.append("_")
    s = "".join(out).strip("_")
    return s or "unnamed"
