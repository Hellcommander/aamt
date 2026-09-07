#!/usr/bin/env python3
"""Mod packaging: icon.png, placeholder tilesheets, assets.json, animation clone."""

from __future__ import annotations

import hashlib
import json
import struct
import zlib
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from s2_paths import core2_dir, skip_mod_path, workshop_root
from s2_schema import slug_name

TILE = 32  # mod-folder icon.png (docs size)
# Ability/skill atlas cells. Vanilla abilities are ~23px; SD cannot paint that
# small. The engine infers cell size from PNG / tiles[], so 128px cells scale
# down in UI and stay sharp. Stay under 4096px on a side (16×8×128 = 2048×1024).
SHEET_TILE = 128
SHEET_COLS = 16
SHEET_MIN_ROWS = {
    "skills": 1,
    "abilities": 8,
    "amplifiers": 8,
    "passive_skills": 4,
    "stackers": 2,
}

# Named sheets custom skill mods actually ship (Warlock / Geomancy).
DEFAULT_SHEETS = (
    ("skills", 1, 1, "assets/skills.png"),
    ("abilities", SHEET_COLS, SHEET_MIN_ROWS["abilities"], "assets/abilities.png"),
    ("amplifiers", SHEET_COLS, SHEET_MIN_ROWS["amplifiers"], "assets/amplifiers.png"),
    ("passive_skills", SHEET_COLS, SHEET_MIN_ROWS["passive_skills"], "assets/passive_skills.png"),
    ("stackers", SHEET_COLS, SHEET_MIN_ROWS["stackers"], "assets/stackers.png"),
)


def sheet_grid_for(name: str, count: int) -> Tuple[int, int]:
    """Cols/rows for a skill atlas. Pads to SHEET_MIN_ROWS so later icons have empty cells."""
    key = str(name or "")
    if key in ("skills", "skill", "icon"):
        return 1, 1
    cols = SHEET_COLS
    min_rows = SHEET_MIN_ROWS.get(key, 1)
    need = max(1, (max(1, int(count)) + cols - 1) // cols)
    return cols, max(min_rows, need)


def _rgb(seed: str) -> Tuple[int, int, int]:
    h = hashlib.md5((seed or "skill").encode("utf-8")).digest()
    return (48 + h[0] % 160, 48 + h[1] % 160, 48 + h[2] % 160)


def write_png(path: Path, width: int, height: int, rgba: bytes) -> None:
    if len(rgba) != width * height * 4:
        raise ValueError("rgba length mismatch")
    raw = b"".join(b"\x00" + rgba[y * width * 4 : (y + 1) * width * 4] for y in range(height))
    compressed = zlib.compress(raw, 9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def _fill_tile(r: int, g: int, b: int, size: int = TILE) -> bytearray:
    pix = bytearray(size * size * 4)
    for y in range(size):
        for x in range(size):
            i = (y * size + x) * 4
            edge = x < 2 or y < 2 or x >= size - 2 or y >= size - 2
            inner = 8 <= x < size - 8 and 8 <= y < size - 8
            if edge:
                pix[i : i + 4] = bytes((20, 20, 22, 255))
            elif inner:
                pix[i : i + 4] = bytes((min(255, r + 40), min(255, g + 40), min(255, b + 40), 255))
            else:
                pix[i : i + 4] = bytes((r, g, b, 255))
    return pix


def write_icon_png(path: Path, rgb: Tuple[int, int, int], *, overwrite: bool = False) -> bool:
    if path.is_file() and not overwrite:
        return False
    write_png(path, TILE, TILE, bytes(_fill_tile(*rgb)))
    return True


def write_thumbnail_png(path: Path, rgb: Tuple[int, int, int], *, overwrite: bool = False) -> bool:
    """Steam workshop thumbnail: PNG, 4:3 (docs §2). Never overwrites an existing file."""
    if path.is_file() and not overwrite:
        return False
    width, height = 400, 300
    r, g, b = rgb
    pix = bytearray(width * height * 4)
    for y in range(height):
        for x in range(width):
            i = (y * width + x) * 4
            edge = x < 6 or y < 6 or x >= width - 6 or y >= height - 6
            if edge:
                pix[i : i + 4] = bytes((20, 20, 22, 255))
            else:
                pix[i : i + 4] = bytes((r, g, b, 255))
    write_png(path, width, height, bytes(pix))
    return True


def write_sheet_png(
    path: Path,
    rgb: Tuple[int, int, int],
    cols: int,
    rows: int,
    *,
    overwrite: bool = False,
    tile: int = SHEET_TILE,
) -> bool:
    if path.is_file() and not overwrite:
        return False
    cell = max(1, int(tile))
    w, h = cols * cell, rows * cell
    canvas = bytearray(w * h * 4)
    block = _fill_tile(*rgb, size=cell)
    for ty in range(rows):
        for tx in range(cols):
            for y in range(cell):
                src = y * cell * 4
                dst = ((ty * cell + y) * w + tx * cell) * 4
                canvas[dst : dst + cell * 4] = block[src : src + cell * 4]
    write_png(path, w, h, bytes(canvas))
    return True


def default_assets() -> Dict[str, Any]:
    return {
        "graphics": {
            "tilesheets": [
                {"name": name, "tiles": [cols, rows], "file": file}
                for name, cols, rows, file in DEFAULT_SHEETS
            ]
        }
    }


def ensure_mod_icon(spec: Dict[str, Any]) -> None:
    icon = str((spec.get("mod") or {}).get("icon") or "")
    if icon in ("", "S.png", "S2.png"):
        spec.setdefault("mod", {})["icon"] = "icon.png"


def write_packaging(spec: Dict[str, Any], root: Path) -> List[str]:
    """Write icon.png, placeholder tilesheets, and assets.json. Never overwrites existing PNGs."""
    written: List[str] = []
    ensure_mod_icon(spec)
    rgb = _rgb(str(spec.get("skill_id") or spec.get("id") or "skill"))
    icon_name = str(spec["mod"].get("icon") or "icon.png")
    icon_path = root / icon_name
    if write_icon_png(icon_path, rgb):
        written.append(icon_name)
    thumb = str(spec["mod"].get("thumbnail") or "")
    if thumb:
        thumb_path = root / thumb
        if write_thumbnail_png(thumb_path, rgb):
            written.append(thumb)
    assets = spec.get("assets") or default_assets()
    spec["assets"] = assets
    if spec.get("production_actions"):
        sheets = (assets.get("graphics") or {}).setdefault("tilesheets", [])
        if not any(s.get("name") == "actions" for s in sheets):
            sheets.append({"name": "actions", "tiles": [SHEET_COLS, 1], "file": "assets/actions.png"})
    from s2_particle_art import PARTICLE_SHEET, ensure_particle_sheet_on_write

    copied = ensure_particle_sheet_on_write(spec, root)
    if copied:
        written.append(copied)
    for sheet in (assets.get("graphics") or {}).get("tilesheets") or []:
        rel = sheet.get("file")
        if not rel:
            continue
        if sheet.get("name") == PARTICLE_SHEET:
            continue
        tiles = sheet.get("tiles") or [1, 1]
        cols, rows = int(tiles[0]), int(tiles[1] if len(tiles) > 1 else 1)
        path = root / rel
        if write_sheet_png(path, rgb, cols, rows):
            written.append(rel)
    (root / "assets.json").write_text(json.dumps(assets, indent="\t") + "\n", encoding="utf-8")
    written.append("assets.json")
    return written


def _iter_animation_files() -> Iterable[Tuple[str, Path]]:
    core = core2_dir() / "animations"
    if core.is_dir():
        for path in sorted(core.glob("*.json")):
            yield "core_2", path
    ws = workshop_root()
    if ws and ws.is_dir():
        for path in sorted(ws.glob("*/animations/*.json")):
            if skip_mod_path(path):
                continue
            yield path.parent.parent.name, path


def search_animations(query: str, limit: int = 40) -> List[Dict[str, Any]]:
    q = (query or "").strip().lower()
    hits: List[Dict[str, Any]] = []
    for source, path in _iter_animation_files():
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        aid = str(data.get("id") or path.stem)
        name = str(data.get("name") or "")
        if q not in aid.lower() and q not in name.lower() and q not in path.stem.lower().replace("_", " "):
            continue
        hits.append({"id": aid, "name": name or aid, "source": source, "file": str(path)})
        if len(hits) >= limit:
            break
    return hits


def load_animation(source_id: str) -> Dict[str, Any]:
    wanted = str(source_id).strip()
    for _source, path in _iter_animation_files():
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        if str(data.get("id") or "") == wanted or path.stem == wanted or str(data.get("name") or "").lower() == wanted.lower():
            data = deepcopy(data)
            data["_cloned_from"] = str(path)
            return data
    raise FileNotFoundError(f"Animation not found: {source_id}")


def clone_animation(
    source_id: str,
    *,
    new_id: str,
    name: Optional[str] = None,
    color: Optional[List[int]] = None,
) -> Dict[str, Any]:
    anim = load_animation(source_id)
    anim["id"] = new_id
    anim["name"] = name or new_id
    anim.pop("_cloned_from", None)
    if color:
        rgba = list(color) + [255] * max(0, 4 - len(color))
        rgba = [int(rgba[0]), int(rgba[1]), int(rgba[2]), int(rgba[3])]
        for part in anim.get("particles") or []:
            if isinstance(part, dict):
                part["color"] = [rgba]
    return anim


def animation_known(anim_id: str) -> bool:
    if not anim_id:
        return True
    try:
        load_animation(anim_id)
        return True
    except FileNotFoundError:
        return False
