#!/usr/bin/env python3
"""Resolve Soulash 2 install, workshop, core_2, docs, and tool output paths."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
_SOULASH2 = _HERE.parent
_TOOLS = _HERE.parent.parent
_SHARED = _TOOLS / "Shared"
for _p in (_SOULASH2, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    from tool_paths import get_path, tools_root
except ImportError:  # pragma: no cover
    def tools_root() -> Path:
        return _TOOLS

    def get_path(key: str, *, env=None, default=None):  # type: ignore
        for name in env or ():
            raw = (os.environ.get(name) or "").strip().strip('"')
            if raw:
                return Path(os.path.expandvars(raw))
        return Path(default) if default else None


GAME_CANDIDATES = [
    Path(r"E:\SteamLibrary\steamapps\common\Soulash 2"),
    Path(r"D:\games\Steam\steamapps\common\Soulash 2"),
    Path(r"C:\Program Files (x86)\Steam\steamapps\common\Soulash 2"),
    Path(r"C:\Program Files\Steam\steamapps\common\Soulash 2"),
]

WORKSHOP_CANDIDATES = [
    Path(r"E:\SteamLibrary\steamapps\workshop\content\2399160"),
    Path(r"D:\games\Steam\steamapps\workshop\content\2399160"),
    Path(r"C:\Program Files (x86)\Steam\steamapps\workshop\content\2399160"),
]

# Formerly blocked hydromancy/water_magic paths after a bad milestone rebuild.
# Cleared: Hydromancy is a normal skill id; prefer Geomancy/Warlock layout still.
SKIP_MOD_NAME_FRAGMENTS: tuple[str, ...] = ()


def tool_dir() -> Path:
    return _HERE


def catalog_dir() -> Path:
    d = _HERE / "catalog"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _looks_like_soulash(p: Path) -> bool:
    if not p.is_dir():
        return False
    return (p / "data" / "mods" / "core_2").is_dir() or (p / "data" / "docs" / "index.html").is_file()


def soulash2_root() -> Path:
    env = get_path(
        "Soulash2Path",
        env=("AAMT_SOULASH2_PATH", "SOULASH2_PATH"),
    )
    if env and _looks_like_soulash(env):
        return env.resolve()
    for cand in GAME_CANDIDATES:
        if _looks_like_soulash(cand):
            return cand.resolve()
    raise FileNotFoundError(
        "Soulash 2 install not found. Set Soulash2Path in TranscendenceTools.ini "
        "or AAMT_SOULASH2_PATH."
    )


def workshop_root() -> Optional[Path]:
    env = get_path(
        "Soulash2WorkshopPath",
        env=("AAMT_SOULASH2_WORKSHOP", "SOULASH2_WORKSHOP"),
    )
    if env and env.is_dir():
        return env.resolve()
    for cand in WORKSHOP_CANDIDATES:
        if cand.is_dir():
            return cand.resolve()
    game = None
    try:
        game = soulash2_root()
    except FileNotFoundError:
        return None
    # SteamLibrary/steamapps/common/Soulash 2 -> steamapps/workshop/content/2399160
    guess = game.parent.parent / "workshop" / "content" / "2399160"
    return guess.resolve() if guess.is_dir() else None


def core2_dir(game: Optional[Path] = None) -> Path:
    return (game or soulash2_root()) / "data" / "mods" / "core_2"


def docs_index(game: Optional[Path] = None) -> Path:
    return (game or soulash2_root()) / "data" / "docs" / "index.html"


def mods_dir(game: Optional[Path] = None) -> Path:
    return (game or soulash2_root()) / "data" / "mods"


def soulash2_exe(game: Optional[Path] = None) -> Path:
    root = game or soulash2_root()
    exe = root / "Soulash 2.exe"
    if exe.is_file():
        return exe
    for h in root.glob("*.exe"):
        if h.name.lower().startswith("soulash"):
            return h
    raise FileNotFoundError(f"Soulash 2.exe not found under {root}")


def output_root() -> Path:
    return tools_root() / "Output" / "Soulash2"


def skip_mod_path(path: Path) -> bool:
    low = str(path).lower().replace("\\", "/")
    return any(frag in low for frag in SKIP_MOD_NAME_FRAGMENTS)


def staging_dir(spec: dict) -> Path:
    sid = str(spec.get("id") or spec.get("mod_id") or "unnamed")
    return output_root() / sid
