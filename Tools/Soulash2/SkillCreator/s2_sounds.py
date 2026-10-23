#!/usr/bin/env python3
"""Custom sound assets for Soulash 2 mods.

What the game reads (0.10.4):

* `assets.json` -> `sounds` is parsed by the same per-mod loader as `tilesheets` / `textures`
  (`{}/assets.json`; keys walk/equipment/ui/events/screens/combat and `music`). No shipped mod uses it
  yet, so treat custom sounds as engine-supported but untested in game.
* `sounds.combat` rows are `{id, name, file}`; `file` is relative to the mod folder
  (core_2: `assets/sfx/abilities/bash.ogg`). Vanilla ids are "1".."168", so mods use prefixed string ids.
* Animations play one: `"sound": {"id": "<combat sound id>", "volume": 100}`.
* Production actions take a game-root path instead: `"sound": "data/mods/<mod>/assets/sfx/x.ogg"`
  (only resolves for mods under data/mods, not Workshop installs).

All vanilla sfx are Ogg Vorbis; the exe links SDL_mixer with vorbis, so ship .ogg.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from s2_paths import core2_dir, mods_dir, skip_mod_path, soulash2_root, workshop_root
from s2_schema import slug_name

AUDIO_MAGIC = {b"OggS": "ogg", b"RIFF": "wav"}


def audio_kind(path: Path) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            return AUDIO_MAGIC.get(f.read(4))
    except OSError:
        return None


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def combat_sounds(folder: Path) -> List[Dict[str, Any]]:
    data = _load(Path(folder) / "assets.json")
    rows = (((data or {}).get("sounds") or {}).get("combat") or []) if isinstance(data, dict) else []
    return [r for r in rows if isinstance(r, dict)]


def _mod_folders() -> Iterable[Tuple[Path, str]]:
    yield core2_dir(), "core_2"
    for root in (mods_dir, workshop_root):
        try:
            base = root()
        except FileNotFoundError:
            continue
        if not base or not base.is_dir():
            continue
        for mod in sorted(p for p in base.iterdir() if p.is_dir() and p.name != "core_2"):
            if not skip_mod_path(mod):
                yield mod, mod.name


def search_sounds(query: str = "", *, limit: int = 60) -> List[Dict[str, Any]]:
    needle = str(query or "").casefold()
    out: List[Dict[str, Any]] = []
    for folder, source in _mod_folders():
        for row in combat_sounds(folder):
            hay = f"{row.get('id')} {row.get('name')} {row.get('file')}".casefold()
            if needle and needle not in hay:
                continue
            out.append({**row, "source": source, "exists": (folder / str(row.get("file") or "")).is_file()})
            if len(out) >= limit:
                return out
    return out


def known_sound_ids() -> Dict[str, str]:
    """Combat sound id -> source mod, across core_2, installed and Workshop mods."""
    out: Dict[str, str] = {}
    for folder, source in _mod_folders():
        for row in combat_sounds(folder):
            out.setdefault(str(row.get("id")), source)
    return out


def _spec_sounds(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    from s2_assets import default_assets

    assets = spec.get("assets") or default_assets()
    spec["assets"] = assets
    return assets.setdefault("sounds", {}).setdefault("combat", [])


def add_combat_sound(
    spec: Dict[str, Any],
    source: Path,
    *,
    name: str,
    sound_id: Optional[str] = None,
    staging: Optional[Path] = None,
) -> Dict[str, Any]:
    """Register an audio file as a combat sound in the spec and stage a copy of it."""
    source = Path(source)
    kind = audio_kind(source)
    if kind is None:
        raise ValueError(f"{source} is not an Ogg Vorbis (.ogg) or WAV file")
    owner = str(spec.get("skill_id") or spec.get("id") or "mod")
    slug = slug_name(name).lower() or source.stem.lower()
    sid = sound_id or f"{owner}_{slug}"
    if sid.isdigit():
        raise ValueError(f"sound id {sid!r} is numeric; vanilla uses 1-168, pick a prefixed string id")
    rel = f"assets/sfx/{slug}.{kind}"
    row = {"id": sid, "name": name, "file": rel}
    rows = _spec_sounds(spec)
    for index, previous in enumerate(rows):
        if str(previous.get("id")) == sid:
            rows[index] = row
            break
    else:
        rows.append(row)
    spec.setdefault("sound_sources", {})[rel] = str(source.resolve())
    if staging is not None:
        dest = Path(staging) / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
    return row


def bind_animation_sound(spec: Dict[str, Any], animation_id: str, sound_id: str, volume: int = 100) -> Dict[str, Any]:
    for anim in spec.get("animations") or []:
        if str(anim.get("id")) == str(animation_id):
            anim["sound"] = {"id": str(sound_id), "volume": int(volume)}
            return anim
    raise KeyError(f"Animation {animation_id} is not in this spec (add-animation / new-animation first)")


def copy_sound_sources(spec: Dict[str, Any], root: Path) -> List[str]:
    """`write` helper: make sure every staged sound file exists under the written mod folder."""
    written = []
    for rel, src in (spec.get("sound_sources") or {}).items():
        dest = Path(root) / rel
        if dest.is_file() or not Path(src).is_file():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        written.append(rel)
    return written


def check_sounds(folder: Path, *, rows: Optional[List[Dict[str, Any]]] = None, animations: Optional[List[Dict[str, Any]]] = None,
                 production_actions: Optional[List[Dict[str, Any]]] = None) -> List[Tuple[str, str]]:
    """(level, message) for a mod folder, or for spec data when rows/animations are passed."""
    folder = Path(folder)
    issues: List[Tuple[str, str]] = []
    rows = combat_sounds(folder) if rows is None else rows
    is_core = folder.resolve() == core2_dir().resolve()
    seen = set()
    for row in rows:
        sid = str(row.get("id") or "")
        where = f"sounds.combat {sid or '?'}"
        if not sid:
            issues.append(("error", f"{where}: needs an id"))
            continue
        if sid in seen:
            issues.append(("error", f"{where}: duplicate id"))
        seen.add(sid)
        if not row.get("file"):
            # core_2 ships silent placeholders this way (26 Raise zombie, 28, 29).
            if not is_core:
                issues.append(("info", f"{where}: empty file, plays nothing"))
            continue
        if sid.isdigit() and not is_core:
            issues.append(("warn", f"{where}: numeric id collides with vanilla combat sounds 1-168; use a prefixed id"))
        path = folder / str(row["file"])
        if not path.is_file():
            issues.append(("error", f"{where}: file {row['file']} not found in the mod folder"))
        elif audio_kind(path) is None:
            issues.append(("error", f"{where}: {row['file']} is not Ogg Vorbis or WAV"))
    known = known_sound_ids()
    local = {str(r.get("id")) for r in rows}
    if animations is None:
        animations = []
        for path in sorted((folder / "animations").rglob("*.json")) if (folder / "animations").is_dir() else []:
            data = _load(path)
            if isinstance(data, dict):
                animations.append(data)
    for anim in animations:
        sound = anim.get("sound")
        if not isinstance(sound, dict) or sound.get("id") in (None, ""):
            continue
        sid = str(sound["id"])
        if sid in ("-1", "0"):  # vanilla "no sound" (core_2 animation 139 uses "0")
            continue
        if sid not in local and sid not in known:
            issues.append(("error", f"animation {anim.get('id')}: sound id {sid!r} is not a combat sound in core_2 or any installed mod"))
        elif sid not in local and known.get(sid) not in (None, "core_2", folder.name):
            issues.append(("warn", f"animation {anim.get('id')}: sound {sid!r} comes from {known[sid]}; add it to mods_required or ship your own copy"))
    if production_actions is None:
        character = _load(folder / "character.json")
        production_actions = (character.get("production_actions") or []) if isinstance(character, dict) else []
    game = soulash2_root()
    for action in production_actions:
        sound = action.get("sound") if isinstance(action, dict) else None
        if isinstance(sound, str) and sound and not (game / sound).is_file():
            issues.append(("error", f"production_action {action.get('id')}: sound path {sound!r} not found under the game folder"))
    return issues
