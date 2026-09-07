#!/usr/bin/env python3
"""Resolve Dwarf Fortress install, vanilla packs, mods/, and DFHack paths."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional

_HERE = Path(__file__).resolve().parent
_TOOLS = _HERE.parent
_SHARED = _TOOLS / "Shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

try:
    from tool_paths import get_path, get_setting, tools_root
except ImportError:  # pragma: no cover
    def tools_root() -> Path:
        return _TOOLS

    def get_path(key: str, *, env=None, default=None):  # type: ignore
        for name in env or ():
            raw = (os.environ.get(name) or "").strip().strip('"')
            if raw:
                return Path(os.path.expandvars(raw))
        return Path(default) if default else None

    def get_setting(key: str, *, env=None, default=None):  # type: ignore
        for name in env or ():
            raw = (os.environ.get(name) or "").strip().strip('"')
            if raw:
                return os.path.expandvars(raw)
        return default


DF_CANDIDATES = [
    Path(r"E:\SteamLibrary\steamapps\common\Dwarf Fortress"),
    Path(r"D:\games\Steam\steamapps\common\Dwarf Fortress"),
    Path(r"C:\Program Files (x86)\Steam\steamapps\common\Dwarf Fortress"),
    Path(r"C:\Program Files\Steam\steamapps\common\Dwarf Fortress"),
]


def dwarf_fortress_root() -> Path:
    """Return DF install root (folder containing Dwarf Fortress.exe)."""
    env = get_path(
        "DwarfFortressPath",
        env=("AAMT_DF_PATH", "DWARF_FORTRESS_PATH", "DF_PATH"),
    )
    if env and _looks_like_df(env):
        return env.resolve()
    for cand in DF_CANDIDATES:
        if _looks_like_df(cand):
            return cand.resolve()
    raise FileNotFoundError(
        "Dwarf Fortress install not found. Set DwarfFortressPath in "
        "TranscendenceTools.ini or AAMT_DF_PATH."
    )


def _looks_like_df(p: Path) -> bool:
    if not p.is_dir():
        return False
    exe = p / "Dwarf Fortress.exe"
    vanilla = p / "data" / "vanilla"
    return exe.is_file() or vanilla.is_dir()


def vanilla_root(df: Optional[Path] = None) -> Path:
    root = df or dwarf_fortress_root()
    return root / "data" / "vanilla"


def vanilla_bodies(df: Optional[Path] = None) -> Path:
    return vanilla_root(df) / "vanilla_bodies" / "objects"


def vanilla_creatures(df: Optional[Path] = None) -> Path:
    return vanilla_root(df) / "vanilla_creatures" / "objects"


def vanilla_entities(df: Optional[Path] = None) -> Path:
    return vanilla_root(df) / "vanilla_entities" / "objects"


def vanilla_languages(df: Optional[Path] = None) -> Path:
    return vanilla_root(df) / "vanilla_languages" / "objects"


def vanilla_graphics(df: Optional[Path] = None) -> Path:
    return vanilla_root(df) / "vanilla_creatures_graphics" / "graphics"


def mods_dir(df: Optional[Path] = None) -> Path:
    root = df or dwarf_fortress_root()
    d = root / "mods"
    d.mkdir(parents=True, exist_ok=True)
    return d


def dfhack_present(df: Optional[Path] = None) -> bool:
    root = df or dwarf_fortress_root()
    return (root / "hack").is_dir()


def dfhack_scripts(df: Optional[Path] = None) -> Optional[Path]:
    root = df or dwarf_fortress_root()
    scripts = root / "hack" / "scripts"
    return scripts if scripts.is_dir() else None


def output_root() -> Path:
    """Staging output under Tools/Output/DwarfFortress/."""
    raw = get_setting("OutputDir", env=("AAMT_OUTPUT_DIR",))
    if raw:
        base = Path(os.path.expandvars(raw))
        if base.name.lower() != "output":
            # Prefer Tools/Output when OutputDir is a generic dump
            preferred = tools_root() / "Output" / "DwarfFortress"
            preferred.mkdir(parents=True, exist_ok=True)
            return preferred
    out = tools_root() / "Output" / "DwarfFortress"
    out.mkdir(parents=True, exist_ok=True)
    return out


def templates_dir() -> Path:
    return _HERE / "templates"


def tool_dir() -> Path:
    return _HERE


def list_body_raw_files(df: Optional[Path] = None) -> List[Path]:
    bodies = vanilla_bodies(df)
    return sorted(bodies.glob("body_*.txt")) + sorted(bodies.glob("b_detail_plan_*.txt"))
