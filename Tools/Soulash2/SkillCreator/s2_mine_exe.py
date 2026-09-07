#!/usr/bin/env python3
"""Extract ability/passive/amplifier identifier tables from Soulash 2.exe."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

# JSON ability object keys mixed into the same string table as effects.
ABILITY_SCHEMA_KEYS = {
    "target",
    "offensive",
    "utility",
    "defensive",
    "requirements",
    "always",
    "one_of",
    "cost",
    "slots",
    "cooldown",
    "ammo",
    "min_range",
    "item_type",
    "cast_time",
    "animation",
    "range",
    "duration",
    "effects",
    "effects_keys",
    "name",
    "skill",
    "description",
}

TARGET_IDS = {
    "any",
    "random",
    "tile",
    "non_actor",
    "health",
    "self",
    "actor",
    "line",
    "aoe_self",
    "line_health",
    "horizontal_line",
    "aoe_target",
    "back_and_forth",
    "ally_command",
    "cone",
    "aoe_tile",
    "line_cone",
    "corpse",
}

ABILITY_KEYS = {
    "summon",
    "summon_on_move",
    "summon_weather",
    "aura",
    "sense",
    "stacker",
    "transform",
    "construct",
    "cage",
}

AMPLIFIER_FIELDS = {
    "cost_health",
    "cost_stamina",
    "range_melee",
    "third_value",
    "secondary_value",
    "restrict_weapon_type",
    "bonuses",
    "cooldown",
    "cast_time",
    "duration",
    "range",
}

# Single-word ids that would otherwise be dropped (clustering requires snake_case or this set).
SHORT_EFFECTS = {
    "bleed",
    "burn",
    "stun",
    "hide",
    "chain",
    "pierce",
    "lunge",
    "aura",
    "sense",
    "thorns",
    "fear",
    "heal",
    "damage",
    "corrupt",
    "charge",
    "disarm",
    "rollback",
    "construct",
    "neutralize",
    "vulnerable",
    "fertility",
    "stacker",
    "summon",
    "transform",
    "silence",
    "knockback",
    "disadvantage",
    "cage",
    "immobilize",
    "deflection",
    "challenge",
    "resistance",
    "stamina",
    "regeneration",
    "frostbite",
}

NOISE_PREFIXES = (
    "score_",
    "portrait_",
    "settlement_",
    "building_",
    "hill_",
    "disable_",
    "answer_",
)

IDENT_RE = re.compile(r"^[a-z][a-z0-9_]{2,47}$")
SNAKE_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")


def _cstrings(data: bytes) -> List[Tuple[int, str]]:
    out: List[Tuple[int, str]] = []
    i = 0
    n = len(data)
    while i < n:
        if 97 <= data[i] <= 122:  # start on lowercase — effect ids are snake_case
            j = i
            while j < n and (97 <= data[j] <= 122 or 48 <= data[j] <= 57 or data[j] == 95):
                j += 1
            if j < n and data[j] == 0 and 3 <= (j - i) <= 48:
                s = data[i:j].decode("ascii")
                if IDENT_RE.match(s):
                    out.append((i, s))
            i = j + 1
        else:
            i += 1
    return out


def _is_effect_like(s: str, known: Optional[Set[str]] = None) -> bool:
    if s in SHORT_EFFECTS or s in TARGET_IDS or s in ABILITY_SCHEMA_KEYS or s in AMPLIFIER_FIELDS:
        return True
    if known and s in known:
        return True
    return bool(SNAKE_RE.match(s))


def _is_noise_id(s: str) -> bool:
    if s.endswith("_key"):
        return True
    return any(s.startswith(p) for p in NOISE_PREFIXES)


def _clusters(strings: List[Tuple[int, str]], known: Optional[Set[str]] = None) -> List[List[Tuple[int, str]]]:
    clusters: List[List[Tuple[int, str]]] = []
    cur: List[Tuple[int, str]] = []
    prev_end = -999
    for off, s in strings:
        if not _is_effect_like(s, known):
            if cur:
                clusters.append(cur)
                cur = []
            prev_end = off + len(s) + 1
            continue
        if cur and off - prev_end > 8:
            clusters.append(cur)
            cur = []
        cur.append((off, s))
        prev_end = off + len(s) + 1
    if cur:
        clusters.append(cur)
    return clusters


def classify_cluster(ids: List[str], known: Dict[str, Set[str]]) -> str:
    """known maps kind -> set of ids already mined from JSON/docs."""
    scores: Dict[str, int] = defaultdict(int)
    for s in ids:
        if s in TARGET_IDS:
            scores["target"] += 2
        if s in ABILITY_KEYS:
            scores["ability_key"] += 2
        if s in ABILITY_SCHEMA_KEYS:
            scores["ability_schema"] += 2
        if s in AMPLIFIER_FIELDS:
            scores["amplifier_field"] += 2
        for kind, bag in known.items():
            if s in bag:
                scores[kind] += 3
    if not scores:
        return "unconfirmed"
    return max(scores, key=scores.get)


def mine_exe(exe: Path, known_by_kind: Optional[Dict[str, Set[str]]] = None) -> Dict[str, object]:
    data = exe.read_bytes()
    strings = _cstrings(data)
    known_by_kind = known_by_kind or {}
    known_flat: Set[str] = set()
    for bag in known_by_kind.values():
        known_flat |= bag
    known_flat |= SHORT_EFFECTS | TARGET_IDS | AMPLIFIER_FIELDS | ABILITY_KEYS
    clusters = _clusters(strings, known_flat)

    kept: List[Dict[str, object]] = []
    by_id: Dict[str, Dict[str, object]] = {}
    for cl in clusters:
        ids = [s for _, s in cl]
        hits = sum(1 for s in ids if s in known_flat)
        # Packed skill-effect tables mix known ids with engine-only names.
        # Long 0-hit runs are scores, keybinds, UI, settlement flags — skip those.
        if hits < 3:
            continue
        kind = classify_cluster(ids, known_by_kind)
        if kind == "ability_schema":
            continue
        rec = {
            "kind_guess": kind,
            "ids": ids,
            "offset": cl[0][0],
            "known_hits": hits,
        }
        kept.append(rec)
        for s in ids:
            if _is_noise_id(s):
                continue
            if s in ABILITY_SCHEMA_KEYS and s not in SHORT_EFFECTS and s not in ABILITY_KEYS:
                continue
            prev = by_id.get(s)
            if prev is None or hits > int(prev.get("cluster_hits") or 0):
                by_id[s] = {"id": s, "kind_guess": kind, "offset": rec["offset"], "cluster_hits": hits}

    return {
        "exe": str(exe),
        "size": len(data),
        "clusters": kept,
        "ids": sorted(by_id.values(), key=lambda r: (r["kind_guess"], r["id"])),
    }
