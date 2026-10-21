#!/usr/bin/env python3
"""Read, search, clone, and author Soulash 2 procedural map definitions."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from s2_paths import core2_dir, mods_dir, skip_mod_path, workshop_root
from s2_schema import slug_name

MAP_DIR_NAMES = ("procedural_maps", "procedual_maps")
MAP_FIELDS = (
    "background",
    "biome",
    "bridge",
    "entities",
    "hill_amount",
    "hill_size",
    "hill_slope_down",
    "hill_slope_up",
    "hill_wall",
    "id",
    "name",
    "river",
    "road",
    "slope_amount",
    "underground_background",
    "underground_wall",
)


def _map_folders() -> List[tuple[Path, str]]:
    found: List[tuple[Path, str]] = []
    seen: set[str] = set()

    def add(folder: Path, source: str) -> None:
        try:
            resolved = folder.resolve()
        except OSError:
            resolved = folder
        key = str(resolved).casefold()
        if folder.is_dir() and key not in seen and not skip_mod_path(folder):
            seen.add(key)
            found.append((resolved, source))

    try:
        add(core2_dir() / "procedural_maps", "core_2")
    except (FileNotFoundError, OSError):
        pass
    try:
        root = mods_dir()
        for mod in sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name.casefold()):
            if skip_mod_path(mod):
                continue
            for folder_name in MAP_DIR_NAMES:
                add(mod / folder_name, mod.name)
    except (FileNotFoundError, OSError):
        pass
    try:
        root = workshop_root()
        if root:
            for mod in sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name.casefold()):
                if skip_mod_path(mod):
                    continue
                for folder_name in MAP_DIR_NAMES:
                    add(mod / folder_name, mod.name)
    except OSError:
        pass
    return found


def _read_map(path: Path, source: str) -> Optional[Dict[str, Any]]:
    try:
        row = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    if not isinstance(row, dict):
        return None
    row["_file"] = path.name
    row["_map_dir"] = path.parent.name
    row["_source"] = source
    row["_path"] = str(path)
    return row


def _iter_procedural_maps() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for folder, source in _map_folders():
        for path in sorted(folder.glob("*.json"), key=lambda p: p.name.casefold()):
            key = str(path.resolve()).casefold()
            if key in seen:
                continue
            seen.add(key)
            row = _read_map(path, source)
            if row is not None:
                rows.append(row)
    return rows


def public_procedural_map(row: Dict[str, Any]) -> Dict[str, Any]:
    """Strip editor provenance from a game-ready map definition."""
    return {key: value for key, value in row.items() if not str(key).startswith("_") and key != "file"}


def procedural_map_filename(row: Dict[str, Any]) -> str:
    original = str(row.get("_file") or "").replace("\\", "/").rsplit("/", 1)[-1]
    if original.lower().endswith(".json") and original not in (".", ".."):
        return original
    map_id = row.get("id")
    name = slug_name(str(row.get("name") or f"map_{map_id}")).strip("_")
    return f"{map_id}_{name or 'map'}.json"


def validate_procedural_map(row: Any) -> Dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError("Procedural map must be a JSON object")
    missing = [field for field in MAP_FIELDS if field not in row]
    if missing:
        raise ValueError("Procedural map is missing required fields: " + ", ".join(missing))
    if isinstance(row.get("id"), bool) or not isinstance(row.get("id"), int):
        raise ValueError("Procedural map id must be an integer")
    if not str(row.get("name") or "").strip():
        raise ValueError("Procedural map name cannot be empty")
    if isinstance(row.get("biome"), bool) or not isinstance(row.get("biome"), int):
        raise ValueError("Procedural map biome must be an integer")
    if not isinstance(row.get("entities"), list):
        raise ValueError("Procedural map entities must be an array")
    for key in ("hill_amount", "hill_size", "slope_amount"):
        values = row.get(key)
        if not isinstance(values, list) or len(values) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in values):
            raise ValueError(f"Procedural map {key} must be a pair of numbers")
    for index, entry in enumerate(row["entities"]):
        if not isinstance(entry, dict) or "index" not in entry or "density" not in entry:
            raise ValueError(f"Procedural map entities[{index}] needs index and density")
        if isinstance(entry.get("density"), bool) or not isinstance(entry.get("density"), (int, float)):
            raise ValueError(f"Procedural map entities[{index}].density must be numeric")
    return row


def search_procedural_maps(query: str = "", *, limit: int = 40) -> List[Dict[str, Any]]:
    needle = str(query or "").strip().casefold()
    results = []
    for row in _iter_procedural_maps():
        haystack = " ".join(str(row.get(key) or "") for key in ("id", "name", "biome", "_source", "_file")).casefold()
        if needle and needle not in haystack:
            continue
        results.append({
            "id": row.get("id"),
            "name": row.get("name") or "",
            "biome": row.get("biome"),
            "source": row.get("_source") or "unknown",
            "file": row.get("_file") or "",
            "clone_key": row.get("_path") or str(row.get("id") or ""),
        })
        if len(results) >= max(1, int(limit)):
            break
    return results


def load_procedural_map(source: str | int) -> Dict[str, Any]:
    key = str(source).strip()
    direct = Path(key).expanduser()
    if direct.is_file():
        row = _read_map(direct, direct.parent.parent.name)
        if row is not None:
            return row
        raise FileNotFoundError(f"Procedural map JSON could not be read: {direct}")
    matches = _iter_procedural_maps()
    for row in matches:
        if str(row.get("id") or "") == key or Path(str(row.get("_file") or "")).stem.casefold() == key.casefold() or str(row.get("name") or "").casefold() == key.casefold():
            return row
    raise FileNotFoundError(f"Procedural map not found: {source}")


def clone_procedural_map(source: str | int, *, new_id: int, name: Optional[str] = None) -> Dict[str, Any]:
    row = deepcopy(load_procedural_map(source))
    row["id"] = int(new_id)
    if name is not None:
        row["name"] = str(name)
    for key in ("_source", "_path", "_file", "_map_dir"):
        row.pop(key, None)
    return validate_procedural_map(row)


def add_procedural_map(spec: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
    payload = deepcopy(validate_procedural_map(row))
    maps = spec.setdefault("procedural_maps", [])
    for index, previous in enumerate(maps):
        if str(previous.get("id")) == str(payload.get("id")):
            for key in ("_file", "_map_dir"):
                if key not in payload and previous.get(key):
                    payload[key] = previous[key]
            maps[index] = payload
            return payload
    maps.append(payload)
    return payload


def map_folder_name(value: Any) -> str:
    folder = str(value or "procedural_maps").strip().replace("\\", "/").rsplit("/", 1)[-1]
    return folder if folder in MAP_DIR_NAMES else "procedural_maps"
