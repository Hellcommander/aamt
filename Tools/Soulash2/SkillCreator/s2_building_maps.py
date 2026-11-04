#!/usr/bin/env python3
"""Link `building_maps/*.smap` prefab layouts to `buildings/*.json`.

.smap is one line of `|`-separated fields. Measured on all 3000 core_2 maps (0.10.4):

    field 0  map id       unique per map ("100", "Divine_Monk_1"); NOT a building id. locations.json
                          `special[].scenarios[].building_maps[].ids` pick maps by this id (all 4169 core_2
                          references resolve this way), so renaming it breaks locations that use it
    field 1  display name ("Dwarven Barracks I")
    field 2  building id  the buildings/*.json `id` this layout belongs to ("67", "482")
    field 3+ width, height, origin, size, ..., tile payload

Every vanilla filename is `<anything>_<field 2>.smap`, and most are `<field 0>_<name>_<field 2>.smap`.
Only the header is rewritten here; the tile payload is copied byte-for-byte. Maps are never invented.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from s2_paths import core2_dir, mods_dir, output_root

HEADER_FIELDS = 3  # map id, name, building id


def read_header(path: Path) -> Tuple[List[str], bytes]:
    """Return ([map_id, name, building_id], rest_of_file_bytes_after_the_third_separator)."""
    raw = Path(path).read_bytes()
    parts = raw.split(b"|", HEADER_FIELDS)
    if len(parts) <= HEADER_FIELDS:
        raise ValueError(f"{path.name}: not a .smap (fewer than {HEADER_FIELDS + 1} '|' fields)")
    return [p.decode("utf-8", "replace") for p in parts[:HEADER_FIELDS]], parts[HEADER_FIELDS]


def write_header(path: Path, map_id: str, name: str, building_id: str, rest: bytes) -> None:
    for label, value in (("map id", map_id), ("name", name), ("building id", building_id)):
        if "|" in value or "\n" in value:
            raise ValueError(f"{label} may not contain '|' or newlines: {value!r}")
    head = "|".join((map_id, name, building_id)).encode("utf-8")
    Path(path).write_bytes(head + b"|" + rest)


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def building_rows(folder: Path) -> Dict[str, Dict[str, Any]]:
    """Building id -> row (with `_file`) for every buildings/**/*.json in a mod folder."""
    out: Dict[str, Dict[str, Any]] = {}
    for path in sorted((Path(folder) / "buildings").rglob("*.json")):
        data = _load(path)
        for row in data if isinstance(data, list) else [data]:
            if isinstance(row, dict) and row.get("id") is not None:
                out[str(row["id"])] = {**row, "_file": str(path)}
    return out


def map_files(folder: Path) -> List[Path]:
    root = Path(folder) / "building_maps"
    return sorted(root.rglob("*.smap")) if root.is_dir() else []


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", str(text)).strip("_")


def conventional_name(map_id: str, building_id: str) -> str:
    """Vanilla style: `<map id>_<building id>.smap` (the trailing token is always the building)."""
    return f"{_slug(map_id)}_{building_id}.smap"


def resolve_mod(name_or_path: str) -> Path:
    p = Path(name_or_path)
    if p.is_dir():
        return p.resolve()
    cand = mods_dir() / name_or_path
    if cand.is_dir():
        return cand.resolve()
    raise FileNotFoundError(f"Mod folder not found: {name_or_path} (looked in {mods_dir()})")


def known_map_ids(exclude: Optional[Path] = None, extra_roots: Iterable[Path] = ()) -> Dict[str, List[str]]:
    """Map id -> ["mod/file.smap", ...] across core_2 and installed mods (optionally excluding one mod)."""
    seen: Dict[str, List[str]] = {}
    roots = [core2_dir()] + [p for p in sorted(mods_dir().iterdir()) if p.is_dir() and p.name != "core_2"]
    roots += [Path(r) for r in extra_roots]
    for mod in roots:
        if exclude is not None and Path(mod).resolve() == Path(exclude).resolve():
            continue
        for path in map_files(mod):
            try:
                header, _ = read_header(path)
            except (OSError, ValueError):
                continue
            seen.setdefault(header[0], []).append(f"{Path(mod).name}/{path.name}")
    return seen


LOCATION_SECTIONS = ("cultures", "settlements", "special", "unknown_special_images")


def _map_groups(value: Any) -> List[Dict[str, Any]]:
    if isinstance(value, dict):
        return [value]
    return [g for g in value if isinstance(g, dict)] if isinstance(value, list) else []


def location_map_refs(folder: Path) -> List[Tuple[str, str]]:
    """(location/scenario, map id) for every building_maps ids entry in a mod's locations.json.

    Vanilla shape: special[] -> scenarios[] -> building_maps[] {count, ids, mode, placement}.
    Older/invented shapes (a top-level `locations` list with building_maps as one object) are read too
    so their references can still be checked; `check_locations_shape` reports the shape itself.
    """
    data = _load(Path(folder) / "locations.json")
    if not isinstance(data, dict):
        return []
    out: List[Tuple[str, str]] = []
    for section, rows in data.items():
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict):
                continue
            label = row.get("id") or row.get("internal_name") or "?"
            holders = [(f"{section}:{label}", row)]
            holders += [
                (f"{section}:{label}/{sc.get('internal_name') or i}", sc)
                for i, sc in enumerate(row.get("scenarios") or [])
                if isinstance(sc, dict)
            ]
            for where, holder in holders:
                for group in _map_groups(holder.get("building_maps")):
                    for map_id in group.get("ids") or []:
                        out.append((where, str(map_id)))
    return out


def check_locations_shape(folder: Path) -> List[str]:
    """Problems the loader would hit in locations.json (core_2 0.10.4 / workshop shape)."""
    data = _load(Path(folder) / "locations.json")
    if data is None:
        return []
    if not isinstance(data, dict):
        return ["locations.json top level must be an object with a `special` array"]
    problems = [
        f"locations.json top-level key {key!r} is not read by the game (vanilla keys: {', '.join(LOCATION_SECTIONS)}); special locations go in `special`"
        for key in data
        if key not in LOCATION_SECTIONS
    ]
    for i, loc in enumerate(data.get("special") or []):
        if not isinstance(loc, dict):
            continue
        missing = [k for k in ("id", "name", "biomes", "difficulty", "image", "algorithm", "scenarios") if k not in loc]
        if missing:
            problems.append(f"special[{i}] {loc.get('id') or loc.get('name') or '?'} missing {', '.join(missing)}")
        for j, sc in enumerate(loc.get("scenarios") or []):
            if isinstance(sc, dict) and isinstance(sc.get("building_maps"), dict):
                problems.append(f"special[{i}].scenarios[{j}].building_maps must be an array of groups ([{{count, ids, mode, placement}}])")
    return problems


def scan_mod_maps(folder: Path, *, other_map_ids: Optional[Dict[str, List[str]]] = None) -> List[Dict[str, str]]:
    """Issues as {level, file, message}. level: error | warn | info."""
    folder = Path(folder)
    own = building_rows(folder)
    core = building_rows(core2_dir())
    others = other_map_ids if other_map_ids is not None else known_map_ids(exclude=folder)
    issues: List[Dict[str, str]] = []
    seen_ids: Dict[str, str] = {}
    seen_hash: Dict[str, str] = {}
    maps_per_building: Dict[str, int] = {}

    def add(level: str, path: Path, message: str) -> None:
        issues.append({"level": level, "file": path.name, "message": message})

    for path in map_files(folder):
        try:
            (map_id, name, bid), _ = read_header(path)
        except ValueError as exc:
            add("error", path, str(exc))
            continue
        digest = hashlib.sha1(path.read_bytes()).hexdigest()
        if digest in seen_hash:
            add("warn", path, f"identical copy of {seen_hash[digest]} (the game loads both)")
        seen_hash[digest] = path.name
        if not bid:
            add("error", path, "header building id (field 3) is empty")
        elif bid not in own and bid not in core:
            add("error", path, f"links to building {bid!r}, which is not in this mod's buildings/ or core_2")
        else:
            maps_per_building[bid] = maps_per_building.get(bid, 0) + 1
        if not map_id:
            add("error", path, "header map id (field 1) is empty")
        # core_2 itself reuses 13 map ids, so a collision is not proven fatal; still avoid it.
        elif map_id in seen_ids:
            add("warn", path, f"map id {map_id!r} also used by {seen_ids[map_id]} in this mod")
        elif map_id in others:
            add("warn", path, f"map id {map_id!r} collides with {', '.join(others[map_id][:3])}")
        seen_ids.setdefault(map_id, path.name)
        if bid and not path.stem.endswith("_" + bid):
            add("info", path, f"filename does not end with _{bid} (vanilla: {conventional_name(map_id or 'map', bid)})")
    for problem in check_locations_shape(folder):
        issues.append({"level": "error", "file": "locations.json", "message": problem})
    # locations.json `building_maps.ids` name maps by header map id (field 1), never by filename.
    local_ids = set(seen_ids)
    for rel, map_id in location_map_refs(folder):
        if map_id not in local_ids and map_id not in others:
            issues.append(
                {
                    "level": "error",
                    "file": "locations.json",
                    "message": f"{rel} uses map id {map_id!r}, but no .smap in this mod, core_2 or installed mods has that header id",
                }
            )
    for bid, row in own.items():
        if not maps_per_building.get(bid):
            continue
        player = row.get("allow_player") in (True, 1, "true") or str(row.get("race")) == "-1"
        missing = [k for k in ("group", "min_area") if k not in row]
        if player and missing:
            issues.append(
                {
                    "level": "warn",
                    "file": Path(row["_file"]).name,
                    "message": (
                        f"player building {bid} has a .smap but no {'/'.join(missing)}; the only vanilla player hall "
                        "with maps (Divine Monastery 482) sets group \"military\", min_area 30 and required_entities"
                    ),
                }
            )
    return issues


def _backup(path: Path, mod: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = output_root() / "_building_map_backups" / mod.name / stamp / path.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    return dest


def _unique_map_id(base: str, taken: set) -> str:
    base = _slug(base) or "map"
    if base not in taken:
        return base
    n = 1
    while f"{base}_{n}" in taken:
        n += 1
    return f"{base}_{n}"


def plan_relink(folder: Path, *, only: Optional[str] = None) -> List[Dict[str, Any]]:
    """Plan header/filename fixes for every map in a mod. Nothing is written."""
    folder = Path(folder)
    own = building_rows(folder)
    core = building_rows(core2_dir())
    taken = set(known_map_ids(exclude=folder))
    # Special locations pick maps by header id, so an id this mod's locations.json uses must not move.
    referenced = {map_id: where for where, map_id in location_map_refs(folder)}
    plan: List[Dict[str, Any]] = []
    seen_hash: Dict[str, str] = {}
    for path in map_files(folder):
        if only and path.name != only:
            continue
        try:
            (map_id, name, bid), _ = read_header(path)
        except ValueError:
            continue
        digest = hashlib.sha1(path.read_bytes()).hexdigest()
        if digest in seen_hash:
            plan.append({"file": path, "action": "skip", "why": f"duplicate of {seen_hash[digest]}; delete one by hand"})
            continue
        seen_hash[digest] = path.name
        new_bid = bid
        if bid not in own and bid not in core:
            # Recover the link from the filename tail when the header is wrong.
            tail = [b for b in own if path.stem.endswith("_" + b) or path.stem == b]
            if len(tail) == 1:
                new_bid = tail[0]
            elif len(own) == 1:
                new_bid = next(iter(own))
            else:
                plan.append({"file": path, "action": "skip", "why": f"cannot tell which building {bid!r} should be"})
                continue
        new_id = map_id
        if not map_id or map_id in taken:
            if map_id in referenced:
                plan.append({"file": path, "action": "skip", "why": f"map id {map_id!r} is used by locations.json ({referenced[map_id]}); rename both by hand"})
                continue
            new_id = _unique_map_id(f"{new_bid}_{len([p for p in plan if p.get('building') == new_bid]) + 1}", taken)
        taken.add(new_id)
        new_name = name or str((own.get(new_bid) or core.get(new_bid) or {}).get("name") or new_bid)
        target = path.with_name(conventional_name(new_id, new_bid))
        changes = []
        if new_id != map_id:
            changes.append(f"map id {map_id!r} -> {new_id!r}")
        if new_bid != bid:
            changes.append(f"building {bid!r} -> {new_bid!r}")
        if new_name != name:
            changes.append(f"name {name!r} -> {new_name!r}")
        if target.name != path.name:
            changes.append(f"rename -> {target.name}")
        plan.append(
            {
                "file": path,
                "action": "change" if changes else "ok",
                "changes": changes,
                "map_id": new_id,
                "name": new_name,
                "building": new_bid,
                "target": target,
            }
        )
    return plan


def apply_plan(folder: Path, plan: List[Dict[str, Any]]) -> List[str]:
    notes: List[str] = []
    for row in plan:
        if row["action"] != "change":
            continue
        path: Path = row["file"]
        target: Path = row["target"]
        if target != path and target.exists():
            notes.append(f"{path.name}: target {target.name} exists, skipped")
            continue
        backup = _backup(path, Path(folder))
        _, rest = read_header(path)
        write_header(path, row["map_id"], row["name"], row["building"], rest)
        if target != path:
            path.rename(target)
        notes.append(f"{path.name}: {'; '.join(row['changes'])} (backup {backup})")
    return notes


def link_map(
    folder: Path,
    source: Path,
    building_id: str,
    *,
    map_id: Optional[str] = None,
    name: Optional[str] = None,
    apply: bool = False,
) -> Dict[str, Any]:
    """Copy/move an existing .smap into <mod>/building_maps and point its header at building_id."""
    folder = Path(folder)
    source = Path(source)
    if source.suffix.lower() != ".smap" or not source.is_file():
        raise FileNotFoundError(f"Existing .smap required: {source}")
    own = building_rows(folder)
    if building_id not in own and building_id not in building_rows(core2_dir()):
        raise ValueError(f"Building {building_id!r} not found in {folder.name}/buildings or core_2 (ids: {', '.join(own) or 'none'})")
    _, rest = read_header(source)
    taken = set(known_map_ids(exclude=folder))
    taken |= {read_header(p)[0][0] for p in map_files(folder) if p.resolve() != source.resolve()}
    new_id = map_id or _unique_map_id(f"{building_id}_1", taken)
    if new_id in taken:
        raise ValueError(f"map id {new_id!r} is already used; pick another --map-id")
    new_name = name or str(own.get(building_id, {}).get("name") or building_id)
    target = folder / "building_maps" / conventional_name(new_id, building_id)
    result = {"source": str(source), "target": str(target), "map_id": new_id, "name": new_name, "building": building_id}
    if not apply:
        return {**result, "applied": False}
    if target.exists() and target.resolve() != source.resolve():
        raise FileExistsError(f"{target} exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    inside = source.resolve().parent == target.parent.resolve()
    if inside:
        result["backup"] = str(_backup(source, folder))
    write_header(target, new_id, new_name, building_id, rest)
    if inside and source.resolve() != target.resolve():
        source.unlink()
    return {**result, "applied": True}
