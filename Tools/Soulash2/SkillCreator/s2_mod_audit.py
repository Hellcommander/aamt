#!/usr/bin/env python3
"""Audit a set of Soulash 2 mods the way the game sees them together.

Three checks the per-spec validator cannot do, because they need every enabled mod at once:

* conflicts   - the same id defined twice (across mods, inside one mod, or replacing a core_2 row)
* references  - milestone rewards, entity milestones/ability kits, transform/summon targets, stackers,
                passive ability refs (`ability_extend_duration`), building occupations and `enables`
                that point at ids no loaded mod defines; starting gear / race items that are not
                item entities (0.10.4 throws "ECStorage::get: entity N is not in the store" and the
                game dies right after world generation)
* shapes      - files the loader needs as an array/object (e.g. skills.json must be `[...]`;
                0.10.4 logs "Failed to load mod ... type must be array, but is object" and drops the mod)

Also parses `<game>/logs/errors.log`. The game boots once with only core_2 and then reloads with the
mod list; the first pass logs "Unable to find building of id <modded id>" for every modded building.
That pass is reported separately as boot noise so it is not mistaken for a broken mod.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from s2_paths import core2_dir, soulash2_root

# Files whose top level must be a JSON array (core_2 0.10.4 shapes).
ARRAY_FILES = ("skills.json", "passives.json", "ability_amplifiers.json", "ability_stackers.json", "loot_exclude.json", "weather.json")
OBJECT_FILES = ("mod.json", "character.json", "assets.json", "conversations.json")
ROW_FOLDERS = ("abilities", "entities", "milestones", "buildings", "animations")
LIST_FILES = {
    "skills": "skills.json",
    "passives": "passives.json",
    "amplifiers": "ability_amplifiers.json",
    "stackers": "ability_stackers.json",
    "weather": "weather.json",
}
CHARACTER_SECTIONS = ("races", "tags", "control_actions", "production_actions", "custom_eq_slots")
REWARD_TABLE = {
    "ability": "abilities",
    "passive": "passives",
    "amplifier": "amplifiers",
    "recipe": "entities",
    "production_action": "production_actions",
    "control_action": "control_actions",
}
ENTITY_KEYS = ("transform", "summon", "construct", "summon_on_move")
# Passive effects whose `value` is an ability id.
PASSIVE_ABILITY_EFFECTS = ("ability_extend_duration",)


@dataclass
class Issue:
    level: str  # error | warn | info
    mod: str
    file: str
    message: str


@dataclass
class ModIndex:
    """Every id a mod defines, per table, with the file it came from."""

    name: str
    folder: Path
    rows: Dict[str, Dict[str, List[Tuple[str, Dict[str, Any]]]]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(list)))
    shape_issues: List[Issue] = field(default_factory=list)

    def ids(self, table: str) -> Iterable[str]:
        return self.rows.get(table, {}).keys()


_DUPLICATE_KEYS: Dict[str, List[str]] = {}


def _load(path: Path) -> Tuple[Any, Optional[str]]:
    """Parse JSON and remember keys that appear twice in one object (json keeps the last silently)."""
    dupes: List[str] = []

    def pairs(kv: List[Tuple[str, Any]]) -> Dict[str, Any]:
        seen = set()
        for key, _ in kv:
            if key in seen:
                dupes.append(key)
            seen.add(key)
        return dict(kv)

    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=pairs)
    except json.JSONDecodeError as exc:
        return None, f"JSON parse error line {exc.lineno}: {exc.msg}"
    except OSError as exc:
        return None, str(exc)
    if dupes:
        _DUPLICATE_KEYS[str(path)] = dupes
    return data, None


def index_mod(folder: Path) -> ModIndex:
    folder = Path(folder)
    idx = ModIndex(folder.name, folder)

    def add(table: str, rid: Any, rel: str, row: Dict[str, Any]) -> None:
        if rid is not None and str(rid) != "":
            idx.rows[table][str(rid)].append((rel, row))

    for table in ROW_FOLDERS:
        for path in sorted((folder / table).rglob("*.json")) if (folder / table).is_dir() else []:
            if "translations" in path.parts:
                continue
            data, err = _load(path)
            rel = str(path.relative_to(folder))
            if err:
                idx.shape_issues.append(Issue("error", folder.name, rel, err))
                continue
            for row in data if isinstance(data, list) else [data]:
                if isinstance(row, dict):
                    add(table, row.get("id"), rel, row)
    for table, name in LIST_FILES.items():
        path = folder / name
        if not path.is_file():
            continue
        data, err = _load(path)
        if err:
            idx.shape_issues.append(Issue("error", folder.name, name, err))
            continue
        if not isinstance(data, list):
            idx.shape_issues.append(
                Issue("error", folder.name, name, f"top level must be an array [...], got {type(data).__name__}; the game drops the whole mod")
            )
            data = [data] if isinstance(data, dict) else []
        for row in data:
            if isinstance(row, dict):
                add(table, row.get("id"), name, row)
    for name in ARRAY_FILES:
        if name in LIST_FILES.values() or not (folder / name).is_file():
            continue
        data, err = _load(folder / name)
        if err or not isinstance(data, list):
            idx.shape_issues.append(Issue("error", folder.name, name, err or f"top level must be an array, got {type(data).__name__}"))
    for name in OBJECT_FILES:
        if not (folder / name).is_file():
            continue
        data, err = _load(folder / name)
        if err or not isinstance(data, dict):
            idx.shape_issues.append(Issue("error", folder.name, name, err or f"top level must be an object, got {type(data).__name__}"))
            continue
        if name == "character.json":
            for section in CHARACTER_SECTIONS:
                for row in data.get(section) or []:
                    if isinstance(row, dict):
                        add(section, row.get("id"), name, row)
        if name == "conversations.json":
            for row in data.get("conversations") or []:
                if isinstance(row, dict):
                    add("conversations", row.get("id"), name, row)
    for path_text, keys in sorted(_DUPLICATE_KEYS.items()):
        path = Path(path_text)
        if folder in path.parents:
            names = ", ".join(sorted(set(keys)))
            idx.shape_issues.append(
                Issue("warn", folder.name, str(path.relative_to(folder)), f"duplicate key(s) {names} in one object; only the last value is used")
            )
    return idx


def check_conflicts(indexes: Sequence[ModIndex], core: ModIndex) -> List[Issue]:
    issues: List[Issue] = []
    owners: Dict[Tuple[str, str], List[Tuple[str, str]]] = defaultdict(list)
    for idx in indexes:
        for table, by_id in idx.rows.items():
            for rid, places in by_id.items():
                if len(places) > 1:
                    files = ", ".join(rel for rel, _ in places)
                    issues.append(Issue("error", idx.name, places[0][0], f"{table} id {rid!r} defined {len(places)}x in this mod ({files}); only one survives"))
                owners[(table, rid)].append((idx.name, places[0][0]))
    for (table, rid), where in sorted(owners.items()):
        if len(where) > 1:
            mods = "; ".join(f"{m}/{f}" for m, f in where)
            issues.append(Issue("error", where[-1][0], where[-1][1], f"{table} id {rid!r} also defined by another mod ({mods}); load order decides which one wins"))
        if rid in core.rows.get(table, {}):
            for mod, rel in where:
                issues.append(Issue("info", mod, rel, f"replaces core_2 {table} {rid!r} (fine if it is a deliberate edit; must load after core_2)"))
    return issues


def _known(table: str, indexes: Sequence[ModIndex]) -> set:
    out: set = set()
    for idx in indexes:
        out.update(idx.ids(table))
    return out


def check_references(targets: Sequence[ModIndex], universe: Sequence[ModIndex]) -> List[Issue]:
    """References inside `targets` are resolved against everything in `universe` (core_2 + the mod set)."""
    tables = {t: _known(t, universe) for t in (
        "abilities", "entities", "milestones", "buildings", "animations", "skills", "passives", "amplifiers",
        "stackers", "production_actions", "control_actions", "races", "weather",
    )}
    owners: Dict[Tuple[str, str], set] = defaultdict(set)
    for u in universe:
        for table in tables:
            for rid in u.ids(table):
                owners[(table, rid)].add(u.name)
    required: Dict[str, set] = {}
    for idx in targets:
        mod_json, _ = _load(idx.folder / "mod.json")
        req = mod_json.get("mods_required") if isinstance(mod_json, dict) else None
        required[idx.name] = {idx.name, "core_2", *[str(m) for m in (req or [])]}
    undeclared: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    issues: List[Issue] = []
    # Job titles (persona.occupation, e.g. "Wizard") are display text; buildings need the worker entity id.
    titles: Dict[str, List[str]] = defaultdict(list)
    for idx in universe:
        for eid, places in idx.rows.get("entities", {}).items():
            persona = places[0][1].get("persona")
            if isinstance(persona, dict) and persona.get("occupation"):
                titles[str(persona["occupation"])].append(eid)

    def missing(idx: ModIndex, rel: str, table: str, value: Any, what: str) -> None:
        sval = str(value)
        if sval in ("", "-1", "None"):
            return
        if sval in tables[table]:
            providers = owners.get((table, sval), set())
            if providers and not providers & required.get(idx.name, {idx.name, "core_2"}):
                for provider in sorted(providers):
                    undeclared[(idx.name, provider)].append(f"{rel}: {what} {sval!r}")
            return
        hint = ""
        for other, ids in tables.items():
            if other != table and sval in ids:
                hint = f" (an id with that name exists in {other})"
                break
        if not hint and table == "entities" and sval in titles:
            hint = f" (that is a persona job title; use the worker entity id: {', '.join(titles[sval][:3])})"
        issues.append(Issue("error", idx.name, rel, f"{what} {sval!r} not found in any loaded {table}{hint}"))

    # Entity id -> components, for gear that must be an item (core_2_Rope is a placed object, not an item).
    components: Dict[str, List[str]] = {}
    for u in universe:
        for eid, places in u.rows.get("entities", {}).items():
            comps = places[-1][1].get("components")
            components[eid] = comps if isinstance(comps, list) else []

    def not_item(idx: ModIndex, rel: str, value: Any, what: str, amount: Any = None) -> None:
        sval = str(value)
        if amount is not None and (
            isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount < 1 or float(amount) != int(amount)
        ):
            issues.append(Issue("error", idx.name, rel, f"{what} {sval!r} amount {amount!r} must be a whole number of at least 1"))
        if sval not in tables["entities"]:
            missing(idx, rel, "entities", value, what)
            return
        if "item" not in components.get(sval, []):
            issues.append(
                Issue(
                    "error",
                    idx.name,
                    rel,
                    f"{what} {sval!r} is not an item entity (no 'item' component); creating the starting kit throws "
                    "'ECStorage::get: entity N is not in the store' and the game crashes on new character",
                )
            )

    for idx in targets:
        for mid, places in idx.rows.get("milestones", {}).items():
            rel, row = places[0]
            rewards = row.get("rewards")
            for reward in rewards if isinstance(rewards, list) else [rewards] if isinstance(rewards, dict) else []:
                if not isinstance(reward, dict):
                    continue
                for kind, value in reward.items():
                    if kind in REWARD_TABLE:
                        missing(idx, rel, REWARD_TABLE[kind], value, f"milestone {mid} rewards {kind}")
            reqs = row.get("requirements") or {}
            for need in reqs.get("milestones") or [] if isinstance(reqs, dict) else []:
                missing(idx, rel, "milestones", need, f"milestone {mid} requires milestone")
            if row.get("skill_id"):
                missing(idx, rel, "skills", row["skill_id"], f"milestone {mid} skill_id")
        for eid, places in idx.rows.get("entities", {}).items():
            rel, row = places[0]
            skills = row.get("skills") if isinstance(row.get("skills"), dict) else {}
            for mile in skills.get("milestones") or []:
                missing(idx, rel, "milestones", mile, f"entity {eid} skills.milestones")
            for ability in row.get("ability_user") or [] if isinstance(row.get("ability_user"), list) else []:
                missing(idx, rel, "abilities", ability, f"entity {eid} ability_user")
        for aid, places in idx.rows.get("abilities", {}).items():
            rel, row = places[0]
            keys = row.get("effects_keys") or row.get("effect_keys") or {}
            for key in ENTITY_KEYS:
                if isinstance(keys, dict) and keys.get(key):
                    missing(idx, rel, "entities", keys[key], f"ability {aid} effects_keys.{key}")
            if isinstance(keys, dict) and keys.get("stacker"):
                missing(idx, rel, "stackers", keys["stacker"], f"ability {aid} effects_keys.stacker")
            if isinstance(keys, dict) and keys.get("summon_weather"):
                missing(idx, rel, "weather", keys["summon_weather"], f"ability {aid} effects_keys.summon_weather")
            anim = row.get("animation")
            if isinstance(anim, str) and anim and not anim.lstrip("-").isdigit():
                missing(idx, rel, "animations", anim, f"ability {aid} animation")
            if row.get("skill"):
                missing(idx, rel, "skills", row["skill"], f"ability {aid} skill")
        for amp_id, places in idx.rows.get("amplifiers", {}).items():
            rel, row = places[0]
            for bonus in row.get("bonuses") or []:
                if isinstance(bonus, dict) and bonus.get("effect") == "stacker":
                    missing(idx, rel, "stackers", bonus.get("value"), f"amplifier {amp_id} stacker bonus")
        for pid, places in idx.rows.get("passives", {}).items():
            rel, row = places[0]
            for fx in row.get("effects") or []:
                if isinstance(fx, dict) and fx.get("effect") == "trigger_ability_on_cast":
                    missing(idx, rel, "abilities", fx.get("value"), f"passive {pid} trigger source")
                    missing(idx, rel, "abilities", fx.get("secondary_value"), f"passive {pid} trigger cast")
                if isinstance(fx, dict) and fx.get("effect") in PASSIVE_ABILITY_EFFECTS:
                    missing(idx, rel, "abilities", fx.get("value"), f"passive {pid} {fx['effect']}")
        for sid, places in idx.rows.get("skills", {}).items():
            rel, row = places[0]
            for n, gear in enumerate(row.get("starting_gear") or []):
                for side in ("first", "second"):
                    pick = gear.get(side) if isinstance(gear, dict) else None
                    if isinstance(pick, dict) and "id" in pick:
                        not_item(idx, rel, pick["id"], f"skill {sid} starting_gear[{n}].{side}", pick.get("amount"))
        for rid, places in idx.rows.get("races", {}).items():
            rel, row = places[0]
            for item in row.get("items") or []:
                gid = item.get("id") if isinstance(item, dict) else item
                if gid is not None:
                    not_item(idx, rel, gid, f"race {rid} items", item.get("amount") if isinstance(item, dict) else None)
        for wid, places in idx.rows.get("weather", {}).items():
            rel, row = places[0]
            for ability in row.get("ability") or []:
                missing(idx, rel, "abilities", ability, f"weather {wid} ability")
            anim = row.get("animation")
            if isinstance(anim, str) and anim and not anim.lstrip("-").isdigit():
                missing(idx, rel, "animations", anim, f"weather {wid} animation")
            for change in row.get("change_entities_on_start") or []:
                if not isinstance(change, dict):
                    continue
                to = change.get("to")
                for ent in [change.get("from"), *(to if isinstance(to, list) else [to])]:
                    missing(idx, rel, "entities", ent, f"weather {wid} change_entities_on_start")
        for bid, places in idx.rows.get("buildings", {}).items():
            rel, row = places[0]
            missing(idx, rel, "entities", row.get("occupation"), f"building {bid} occupation")
            per_race = row.get("occupation_per_race")
            if isinstance(per_race, dict):
                for race, ent in per_race.items():
                    missing(idx, rel, "entities", ent, f"building {bid} occupation_per_race[{race}]")
            for skill in row.get("enables") or []:
                missing(idx, rel, "skills", skill, f"building {bid} enables")
        for eid, places in idx.rows.get("entities", {}).items():
            rel, row = places[0]
            skills = row.get("skills") if isinstance(row.get("skills"), dict) else {}
            for skill in skills.get("skills") or []:
                missing(idx, rel, "skills", skill, f"entity {eid} skills.skills")
    for (mod, provider), refs in sorted(undeclared.items()):
        sample = "; ".join(refs[:2]) + (f" (+{len(refs) - 2} more)" if len(refs) > 2 else "")
        issues.append(
            Issue(
                "warn",
                mod,
                "mod.json",
                f"uses {len(refs)} id(s) from {provider}, which is not in mods_required; they break when {provider} is disabled ({sample})",
            )
        )
    return issues


def audit(mod_folders: Sequence[Path], *, universe_extra: Sequence[Path] = ()) -> Dict[str, Any]:
    _DUPLICATE_KEYS.clear()
    core = index_mod(core2_dir())
    targets = [index_mod(p) for p in mod_folders]
    extra = [index_mod(p) for p in universe_extra if Path(p).resolve() not in {t.folder.resolve() for t in targets}]
    issues: List[Issue] = []
    for idx in targets:
        issues.extend(idx.shape_issues)
    issues.extend(check_conflicts(targets, core))
    issues.extend(check_references(targets, [core, *targets, *extra]))
    return {"mods": [t.name for t in targets], "issues": issues}


# ---------------------------------------------------------------- errors.log


_LINE = re.compile(r"^\[(?P<time>[\d:]+)\]\s+\[(?P<level>\w+)\]\s+(?P<msg>.*)$")


def errors_log_path(game: Optional[Path] = None) -> Path:
    return (game or soulash2_root()) / "logs" / "errors.log"


def read_game_log(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Split errors.log into load passes: [{start, mods, messages: Counter, boot_noise: bool}]."""
    path = Path(path) if path else errors_log_path()
    passes: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    reading_mods = False
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _LINE.match(raw.strip())
        if not m:
            continue
        msg = m.group("msg").strip()
        if "Initializing mods loading" in msg:
            current = {"start": m.group("time"), "mods": [], "messages": Counter(), "boot_noise": False}
            passes.append(current)
            reading_mods = False
            continue
        if current is None:
            current = {"start": m.group("time"), "mods": [], "messages": Counter(), "boot_noise": False}
            passes.append(current)
        if msg == "Loading mods:":
            reading_mods = True
            continue
        if reading_mods and msg.startswith("- "):
            current["mods"].append(msg[2:].strip())
            continue
        reading_mods = False
        current["messages"][f"[{m.group('level')}] {msg}"] += 1
    for i, p in enumerate(passes):
        # core_2-only pass followed by a fuller reload: its missing-building lines are expected.
        later = passes[i + 1 :]
        p["boot_noise"] = p["mods"] == ["core_2"] and any(len(q["mods"]) > 1 for q in later)
    return passes


def explain_log_line(msg: str) -> str:
    if "Unable to find building of id" in msg:
        return "a .smap/settlement references a building id no loaded mod defines"
    if "type must be array, but is object" in msg:
        return "a list file (skills.json, passives.json, ...) is a single object; wrap it in [ ]"
    if "Unable to find font for index" in msg:
        return "a font index beyond core_2's fonts (Romulus=0, Lato=1); not from mod JSON, check font options"
    if "already exists" in msg and "Special location" in msg:
        return "vanilla data overrides itself; not caused by mods"
    return ""
