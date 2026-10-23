#!/usr/bin/env python3
"""Read, search, clone, author and validate Soulash 2 weather events (`<mod>/weather.json`).

`weather.json` is an array. Fields (docs §11 plus what Soulash 2.exe 0.10.4 reads):

    id, name, animation, animation_tick, ability[], ability_trigger_time, disabled_under_roof,
    duration, trigger_every, trigger_chance, biomes[], trigger_message
    change_entities_on_start  [{from: entity id, to: id | [ids]}]  (0.10.0: tiles swap when it starts)
    force_night               bool   (Blood Moon)
    thirst_multiplier         float  (Heatwave)
    stop_on_map_exit          bool   (exe-only field; no vanilla example yet)

A weather with empty `biomes` never rolls on its own; it only starts from an ability
(`effects_keys.summon_weather: "<weather id>"`, vanilla Summon Rain) or the `weather` console command.
"""

from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from s2_paths import core2_dir, mods_dir, skip_mod_path, workshop_root

REQUIRED_FIELDS = (
    "id",
    "name",
    "animation",
    "animation_tick",
    "ability",
    "ability_trigger_time",
    "disabled_under_roof",
    "duration",
    "trigger_every",
    "trigger_chance",
    "biomes",
    "trigger_message",
)
OPTIONAL_FIELDS = ("change_entities_on_start", "force_night", "thirst_multiplier", "stop_on_map_exit")
NUMBER_FIELDS = ("animation_tick", "ability_trigger_time", "duration", "trigger_every", "trigger_chance")
BOOL_FIELDS = ("disabled_under_roof", "force_night", "stop_on_map_exit")

# Defaults copied from vanilla Rain (id 1), the docs example.
DEFAULTS: Dict[str, Any] = {
    "animation_tick": 2000.0,
    "ability": [],
    "ability_trigger_time": 1.0,
    "disabled_under_roof": True,
    "duration": 500.0,
    "trigger_every": 500.0,
    "trigger_chance": 0.25,
    "biomes": [],
}


def _sources() -> List[tuple[Path, str]]:
    found: List[tuple[Path, str]] = []
    try:
        found.append((core2_dir() / "weather.json", "core_2"))
    except FileNotFoundError:
        pass
    for root in (mods_dir, workshop_root):
        try:
            base = root()
        except FileNotFoundError:
            continue
        if not base or not base.is_dir():
            continue
        for mod in sorted((p for p in base.iterdir() if p.is_dir() and p.name != "core_2"), key=lambda p: p.name.casefold()):
            if not skip_mod_path(mod) and (mod / "weather.json").is_file():
                found.append((mod / "weather.json", mod.name))
    return found


def _read(path: Path) -> List[Dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return []
    return [row for row in (data if isinstance(data, list) else [data]) if isinstance(row, dict)]


def iter_weather() -> List[Dict[str, Any]]:
    rows = []
    for path, source in _sources():
        for row in _read(path):
            rows.append({**row, "_source": source, "_path": str(path)})
    return rows


def public_weather(row: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in row.items() if not str(k).startswith("_")}


def known_biomes() -> Set[str]:
    """Biome ids seen in core_2 weather/worldgen plus every installed weather.json."""
    out: Set[str] = set()
    for row in iter_weather():
        out.update(str(b) for b in row.get("biomes") or [])
    try:
        world = json.loads((core2_dir() / "worldgen.json").read_text(encoding="utf-8-sig"))
        for group in (world.get("biomes") or {}).values():
            if isinstance(group, dict):
                out.update(group)
        out.update((world.get("seaports") or {}).keys())
    except (OSError, ValueError, FileNotFoundError):
        pass
    return out


def search_weather(query: str = "", *, limit: int = 40) -> List[Dict[str, Any]]:
    needle = str(query or "").strip().casefold()
    out = []
    for row in iter_weather():
        hay = " ".join(str(row.get(k) or "") for k in ("id", "name", "animation", "_source", "trigger_message")).casefold()
        hay += " " + " ".join(str(b) for b in row.get("biomes") or []).casefold()
        if needle and needle not in hay:
            continue
        out.append(
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "source": row.get("_source"),
                "biomes": row.get("biomes") or [],
                "ability": row.get("ability") or [],
                "animation": row.get("animation"),
                "extras": [k for k in OPTIONAL_FIELDS if k in row],
            }
        )
        if len(out) >= max(1, int(limit)):
            break
    return out


def load_weather(source: str) -> Dict[str, Any]:
    key = str(source).strip()
    rows = iter_weather()
    for row in rows:
        if str(row.get("id")) == key:
            return row
    for row in rows:
        if str(row.get("name") or "").casefold() == key.casefold():
            return row
    raise FileNotFoundError(f"Weather not found: {source} (try list-weather --search)")


def parse_change(items: Iterable[str]) -> List[Dict[str, Any]]:
    """`from=to` or `from=to1,to2` -> change_entities_on_start rows."""
    out = []
    for item in items or []:
        if "=" not in item:
            raise ValueError(f"--change needs from=to[,to2]: {item!r}")
        src, _, dst = item.partition("=")
        targets = [t.strip() for t in dst.split(",") if t.strip()]
        if not src.strip() or not targets:
            raise ValueError(f"--change needs from=to[,to2]: {item!r}")
        out.append({"from": src.strip(), "to": targets})
    return out


def make_weather(
    weather_id: str,
    name: str,
    *,
    animation: str,
    trigger_message: str,
    base: Optional[Dict[str, Any]] = None,
    **fields: Any,
) -> Dict[str, Any]:
    row = deepcopy(public_weather(base)) if base else deepcopy(DEFAULTS)
    row.update({"id": str(weather_id), "name": name, "animation": str(animation), "trigger_message": trigger_message})
    for key, value in fields.items():
        if value is None:
            continue
        row[key] = value
    for key in REQUIRED_FIELDS:
        row.setdefault(key, deepcopy(DEFAULTS.get(key)))
    ordered = {k: row[k] for k in REQUIRED_FIELDS}
    ordered.update({k: v for k, v in row.items() if k not in ordered})
    return ordered


def upsert_weather(spec: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
    rows = spec.setdefault("weather", [])
    for index, previous in enumerate(rows):
        if str(previous.get("id")) == str(row.get("id")):
            rows[index] = row
            return row
    rows.append(row)
    return row


def remove_weather(spec: Dict[str, Any], weather_id: str) -> bool:
    rows = spec.get("weather") or []
    keep = [r for r in rows if str(r.get("id")) != str(weather_id)]
    spec["weather"] = keep
    return len(keep) != len(rows)


def validate_weather_rows(
    rows: List[Any],
    *,
    entity_ids: Set[str],
    ability_ids: Set[str],
    animation_ids: Set[str],
    vanilla_ids: Optional[Set[str]] = None,
    biomes: Optional[Set[str]] = None,
) -> List[tuple[str, str, str]]:
    """Return (level, where, message). Numeric vanilla ids ("88") are accepted as-is."""
    issues: List[tuple[str, str, str]] = []
    seen: Set[str] = set()
    vanilla_ids = vanilla_ids if vanilla_ids is not None else {str(r.get("id")) for r in _read(core2_dir() / "weather.json")}
    biomes = biomes if biomes is not None else known_biomes()

    def ref_ok(value: Any, known: Set[str]) -> bool:
        s = str(value)
        return s in known or s.lstrip("-").isdigit()

    for index, row in enumerate(rows):
        where = f"weather[{index}]"
        if not isinstance(row, dict):
            issues.append(("error", where, "weather entry must be an object"))
            continue
        wid = str(row.get("id") or "")
        where = f"weather {wid or index}"
        for key in REQUIRED_FIELDS:
            if key not in row:
                issues.append(("error", where, f"missing {key}"))
        if not isinstance(row.get("id"), str) or not wid:
            issues.append(("error", where, "id must be a non-empty string (vanilla uses \"1\".. \"17\")"))
        if wid in seen:
            issues.append(("error", where, "duplicate weather id in this mod"))
        seen.add(wid)
        if wid in vanilla_ids:
            issues.append(("warn", where, f"id {wid!r} replaces vanilla weather {wid}; use a prefixed id unless that is intended"))
        for key in NUMBER_FIELDS:
            if key in row and (isinstance(row[key], bool) or not isinstance(row[key], (int, float))):
                issues.append(("error", where, f"{key} must be a number"))
        chance = row.get("trigger_chance")
        if isinstance(chance, (int, float)) and not isinstance(chance, bool) and not 0 <= chance <= 1:
            issues.append(("error", where, "trigger_chance must be between 0 and 1"))
        for key in BOOL_FIELDS:
            if key in row and not isinstance(row[key], bool):
                issues.append(("error", where, f"{key} must be true/false"))
        if "thirst_multiplier" in row and (isinstance(row["thirst_multiplier"], bool) or not isinstance(row["thirst_multiplier"], (int, float))):
            issues.append(("error", where, "thirst_multiplier must be a number (vanilla Heatwave: 4.0)"))
        if "stop_on_map_exit" in row:
            issues.append(("info", where, "stop_on_map_exit is read by the exe but no vanilla weather uses it yet; test in game"))
        abilities = row.get("ability")
        if not isinstance(abilities, list):
            issues.append(("error", where, "ability must be an array of ability ids ([] for none)"))
        else:
            for aid in abilities:
                if not ref_ok(aid, ability_ids):
                    issues.append(("error", where, f"ability {aid!r} not found in core_2 or this mod"))
        anim = row.get("animation")
        if anim is not None and not ref_ok(anim, animation_ids):
            issues.append(("error", where, f"animation {anim!r} not found in core_2 or this mod"))
        row_biomes = row.get("biomes")
        if not isinstance(row_biomes, list):
            issues.append(("error", where, "biomes must be an array"))
        else:
            if not row_biomes:
                issues.append(("info", where, "no biomes: never rolls by itself; start it with an ability effects_keys.summon_weather"))
            for biome in row_biomes:
                if biomes and str(biome) not in biomes:
                    issues.append(("warn", where, f"biome {biome!r} not seen in vanilla weather/worldgen ({', '.join(sorted(biomes)[:6])}, ...)"))
        changes = row.get("change_entities_on_start")
        if changes is not None:
            if not isinstance(changes, list):
                issues.append(("error", where, "change_entities_on_start must be an array of {from, to}"))
            else:
                for ci, change in enumerate(changes):
                    if not isinstance(change, dict) or "from" not in change or "to" not in change:
                        issues.append(("error", where, f"change_entities_on_start[{ci}] needs from and to"))
                        continue
                    to = change["to"]
                    # Soulash 2.exe: "change_entities_on_start 'to' must be a string or array of strings"
                    if not (isinstance(to, str) or (isinstance(to, list) and all(isinstance(t, str) for t in to))):
                        issues.append(("error", where, f"change_entities_on_start[{ci}].to must be a string or array of strings"))
                        continue
                    for eid in [change["from"], *([to] if isinstance(to, str) else to)]:
                        if not ref_ok(eid, entity_ids):
                            issues.append(("error", where, f"change_entities_on_start[{ci}] entity {eid!r} not found"))
    return issues


@lru_cache(maxsize=8)
def core_ids(sub: str) -> frozenset:
    """core_2 ids for entities/abilities/animations (cached: core_2 has thousands of entity files)."""
    try:
        return frozenset(ids_in_folder(core2_dir(), sub))
    except FileNotFoundError:
        return frozenset()


def validate_spec_weather(spec: Dict[str, Any]) -> List[tuple[str, str, str]]:
    def local(key: str) -> Set[str]:
        return {str(r.get("id")) for r in spec.get(key) or [] if isinstance(r, dict) and r.get("id") is not None}

    return validate_weather_rows(
        spec.get("weather") or [],
        entity_ids=set(core_ids("entities")) | local("entities"),
        ability_ids=set(core_ids("abilities")) | local("abilities"),
        animation_ids=set(core_ids("animations")) | local("animations"),
    )


def ids_in_folder(folder: Path, sub: str) -> Set[str]:
    out: Set[str] = set()
    root = Path(folder) / sub
    if not root.is_dir():
        return out
    for path in root.rglob("*.json"):
        if "translations" in path.parts:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        for row in data if isinstance(data, list) else [data]:
            if isinstance(row, dict) and row.get("id") is not None:
                out.add(str(row["id"]))
    return out
