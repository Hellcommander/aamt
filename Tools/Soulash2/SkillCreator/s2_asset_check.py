#!/usr/bin/env python3
"""Tilesheet (assets.json) checks and previews for installed Soulash 2 mods.

How the game resolves art (changelog 0.7.7 + docs): every `image` / glyph `index` is a cell number on a
named tilesheet, counted from the **bottom-left** cell. A mod that lists a sheet under a vanilla name
(`glyph32`, `items`, `abilities`, ...) uses *its own* sheet for its own content; otherwise core_2's sheet
applies. So a cloned vanilla entity with glyph index 491 inside a mod that ships a 32-cell `glyph32`
points past the end of that mod's sheet.

Index fields checked (field -> sheet):
    abilities/*.json image               -> abilities
    ability_amplifiers.json image        -> amplifiers
    passives.json image                  -> passive_skills
    ability_stackers.json image          -> stackers
    skills.json image                    -> skills
    entities glyph.frames[].index        -> glyph32
    entities light_source.lit_image      -> glyph32
    entities item.image                  -> items
    entities persona.occupationIconIndex -> professions
    buildings image / occupation_image   -> buildings / professions
    character.json production_actions[].image -> actions, races[].state_crests[].image -> state_crests
    animations particles[].tile_id       -> particles32
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from s2_paths import core2_dir


# Out-of-range values core_2 0.10.4 itself ships (14 entities, e.g. Dark Druid / Mushman glyphs).
KNOWN_VANILLA_ODD = {("glyph32", 6462548)}
# core_2's own portrait sheet is 3380x3328 on a 12x12 grid; portraits are layered parts, not even cells.
UNEVEN_OK = {"portraits"}


@dataclass
class Sheet:
    name: str
    cols: int
    rows: int
    file: str
    path: Path
    source: str  # "core_2" or the mod folder name
    png: Optional[Tuple[int, int]] = None

    @property
    def cells(self) -> int:
        return self.cols * self.rows

    @property
    def cell_px(self) -> Optional[Tuple[float, float]]:
        if not self.png:
            return None
        return self.png[0] / self.cols, self.png[1] / self.rows


@dataclass
class AssetIssue:
    level: str
    mod: str
    file: str
    message: str


def png_size(path: Path) -> Optional[Tuple[int, int]]:
    try:
        with open(path, "rb") as f:
            head = f.read(24)
    except OSError:
        return None
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def read_sheets(folder: Path, source: str) -> Dict[str, Sheet]:
    data = _load(Path(folder) / "assets.json")
    out: Dict[str, Sheet] = {}
    for row in ((data or {}).get("graphics") or {}).get("tilesheets") or [] if isinstance(data, dict) else []:
        if not isinstance(row, dict) or not row.get("name"):
            continue
        tiles = row.get("tiles") or [1, 1]
        try:
            cols, rows = int(tiles[0]), int(tiles[1] if len(tiles) > 1 else 1)
        except (TypeError, ValueError, IndexError):
            cols, rows = 0, 0
        rel = str(row.get("file") or "")
        path = (Path(folder) / rel).resolve() if rel else Path(folder)
        out[str(row["name"])] = Sheet(str(row["name"]), cols, rows, rel, path, source, png_size(path) if rel else None)
    return out


def effective_sheets(folder: Path) -> Dict[str, Sheet]:
    """core_2 sheets, replaced name-by-name by the mod's own (what the mod's content draws from)."""
    sheets = read_sheets(core2_dir(), "core_2")
    if Path(folder).resolve() != core2_dir().resolve():
        sheets.update(read_sheets(folder, Path(folder).name))
    return sheets


def _rows(data: Any) -> List[Dict[str, Any]]:
    return [r for r in (data if isinstance(data, list) else [data]) if isinstance(r, dict)]


def _json_files(folder: Path, sub: str) -> Iterable[Path]:
    root = Path(folder) / sub
    return sorted(p for p in root.rglob("*.json") if "translations" not in p.parts) if root.is_dir() else []


def iter_index_refs(folder: Path) -> Iterable[Tuple[str, str, str, Any]]:
    """Yield (sheet name, file, what, index) for every art index a mod sets."""
    folder = Path(folder)
    for path in _json_files(folder, "abilities"):
        for row in _rows(_load(path)):
            if "image" in row:
                yield "abilities", path.name, f"ability {row.get('id')}", row["image"]
    for name, sheet in (("ability_amplifiers.json", "amplifiers"), ("passives.json", "passive_skills"),
                        ("ability_stackers.json", "stackers"), ("skills.json", "skills")):
        for row in _rows(_load(folder / name)):
            if "image" in row:
                yield sheet, name, f"{sheet} {row.get('id')}", row["image"]
    for path in _json_files(folder, "entities"):
        for row in _rows(_load(path)):
            eid = row.get("id")
            glyph = row.get("glyph")
            for i, frame in enumerate((glyph or {}).get("frames") or [] if isinstance(glyph, dict) else []):
                if isinstance(frame, dict) and "index" in frame:
                    yield "glyph32", path.name, f"entity {eid} glyph frame {i}", frame["index"]
            light = row.get("light_source")
            if isinstance(light, dict) and "lit_image" in light:
                yield "glyph32", path.name, f"entity {eid} light_source.lit_image", light["lit_image"]
            item = row.get("item")
            if isinstance(item, dict) and "image" in item:
                yield "items", path.name, f"entity {eid} item.image", item["image"]
            persona = row.get("persona")
            if isinstance(persona, dict) and "occupationIconIndex" in persona:
                yield "professions", path.name, f"entity {eid} persona.occupationIconIndex", persona["occupationIconIndex"]
    for path in _json_files(folder, "buildings"):
        for row in _rows(_load(path)):
            if "image" in row:
                yield "buildings", path.name, f"building {row.get('id')} image", row["image"]
            if "occupation_image" in row:
                yield "professions", path.name, f"building {row.get('id')} occupation_image", row["occupation_image"]
    character = _load(folder / "character.json")
    if isinstance(character, dict):
        for row in _rows(character.get("production_actions") or []):
            if "image" in row:
                yield "actions", "character.json", f"production_action {row.get('id')}", row["image"]
        for race in _rows(character.get("races") or []):
            for crest in _rows(race.get("state_crests") or []):
                if "image" in crest:
                    yield "state_crests", "character.json", f"race {race.get('id')} crest {crest.get('id')}", crest["image"]
    for path in _json_files(folder, "animations"):
        for row in _rows(_load(path)):
            for i, part in enumerate(row.get("particles") or []):
                if isinstance(part, dict) and "tile_id" in part:
                    yield "particles32", path.name, f"animation {row.get('id')} particle {i}", part["tile_id"]


def check_mod_assets(folder: Path) -> List[AssetIssue]:
    folder = Path(folder)
    mod = folder.name
    issues: List[AssetIssue] = []
    core = read_sheets(core2_dir(), "core_2")
    own = read_sheets(folder, mod)
    sheets = {**core, **own}

    for sheet in own.values():
        where = "assets.json"
        if sheet.cols <= 0 or sheet.rows <= 0:
            issues.append(AssetIssue("error", mod, where, f"sheet {sheet.name}: tiles must be [cols, rows] > 0"))
            continue
        if not sheet.file or not sheet.path.is_file():
            issues.append(AssetIssue("error", mod, where, f"sheet {sheet.name}: file {sheet.file!r} not found; the game skips drawing everything on it"))
            continue
        if folder.resolve() not in sheet.path.parents:
            issues.append(AssetIssue("warn", mod, where, f"sheet {sheet.name}: file {sheet.file!r} points outside the mod folder (breaks when installed from Workshop)"))
        if sheet.png is None:
            issues.append(AssetIssue("error", mod, where, f"sheet {sheet.name}: {sheet.file} is not a PNG"))
            continue
        w, h = sheet.png
        if (w % sheet.cols or h % sheet.rows) and sheet.name not in UNEVEN_OK:
            issues.append(AssetIssue("warn", mod, where, f"sheet {sheet.name}: {w}x{h}px does not divide into tiles {sheet.cols}x{sheet.rows} (cells would be {w / sheet.cols:.2f}x{h / sheet.rows:.2f}px)"))
        if sheet.name in core and sheet.cells < core[sheet.name].cells:
            issues.append(
                AssetIssue(
                    "info",
                    mod,
                    where,
                    f"sheet {sheet.name} replaces core_2's for this mod with {sheet.cells} cells (core_2 has {core[sheet.name].cells}); vanilla indexes used by this mod now point into your sheet",
                )
            )

    for sheet_name, fname, what, raw in iter_index_refs(folder):
        try:
            index = int(raw)
        except (TypeError, ValueError):
            issues.append(AssetIssue("error", mod, fname, f"{what}: index {raw!r} is not a number"))
            continue
        sheet = sheets.get(sheet_name)
        if sheet is None:
            issues.append(AssetIssue("error", mod, fname, f"{what}: no tilesheet named {sheet_name!r} in this mod or core_2"))
            continue
        if index < 0:
            # -1 is the vanilla "no image" value (e.g. workerless buildings).
            if index != -1:
                issues.append(AssetIssue("error", mod, fname, f"{what}: index {index} is negative"))
            continue
        if (sheet_name, index) in KNOWN_VANILLA_ODD:
            issues.append(AssetIssue("info", mod, fname, f"{what}: index {index} is the same out-of-range value core_2 ships on 14 entities"))
            continue
        if index >= sheet.cells:
            hint = ""
            if sheet.source != "core_2" and sheet_name in core and index < core[sheet_name].cells:
                hint = f"; it fits core_2's {sheet_name} ({core[sheet_name].cells} cells), so it looks like a vanilla index used against your own sheet"
            issues.append(AssetIssue("error", mod, fname, f"{what}: index {index} is past the end of {sheet.source}'s {sheet_name} ({sheet.cells} cells, 0-{sheet.cells - 1}){hint}"))
    from s2_sounds import check_sounds

    for level, message in check_sounds(folder):
        issues.append(AssetIssue(level, mod, "sounds", message))
    return issues


def cell_box(sheet: Sheet, index: int) -> Tuple[int, int, int, int]:
    """Pixel box of a cell; index 0 is the bottom-left cell, counting right then up."""
    if not sheet.png:
        raise ValueError(f"{sheet.name}: PNG size unknown")
    cw, ch = sheet.png[0] // sheet.cols, sheet.png[1] // sheet.rows
    col = index % sheet.cols
    row_from_bottom = index // sheet.cols
    top = (sheet.rows - 1 - row_from_bottom) * ch
    return col * cw, top, (col + 1) * cw, top + ch


def render_cells(sheet: Sheet, indexes: List[int], out: Path, *, scale: int = 4) -> Path:
    """Write a labelled contact sheet of the given cells (needs Pillow)."""
    from PIL import Image, ImageDraw

    src = Image.open(sheet.path).convert("RGBA")
    cw, ch = sheet.png[0] // sheet.cols, sheet.png[1] // sheet.rows
    tile_w, tile_h = cw * scale, ch * scale
    label_h = 14
    per_row = min(8, max(1, len(indexes)))
    rows = (len(indexes) + per_row - 1) // per_row
    canvas = Image.new("RGBA", (per_row * (tile_w + 6) + 6, rows * (tile_h + label_h + 6) + 6), (24, 24, 28, 255))
    draw = ImageDraw.Draw(canvas)
    for n, index in enumerate(indexes):
        x = 6 + (n % per_row) * (tile_w + 6)
        y = 6 + (n // per_row) * (tile_h + label_h + 6)
        if 0 <= index < sheet.cells:
            tile = src.crop(cell_box(sheet, index)).resize((tile_w, tile_h), Image.NEAREST)
            canvas.paste(tile, (x, y + label_h), tile)
            draw.text((x, y), f"{index}", fill=(230, 230, 230, 255))
        else:
            draw.rectangle((x, y + label_h, x + tile_w, y + label_h + tile_h), outline=(200, 60, 60, 255))
            draw.text((x, y), f"{index} (out of range)", fill=(230, 90, 90, 255))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    return out
