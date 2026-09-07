"""Resolve Grim Dawn install paths, DLC layers, and mod folders."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


DEFAULT_GAME_DIR = Path(r"D:\games\Steam\steamapps\common\Grim Dawn")
DEFAULT_NYDIAMAR_SOURCE = DEFAULT_GAME_DIR / "mods" / "Nydiamar"

CLASS_HUB_RELATIVE = [
    "records/ui/skills/skills_mastertable.dbr",
    "records/ui/skills/classselection/skills_classselectiontable.dbr",
    "records/creatures/pc/malepc01.dbr",
    "records/creatures/pc/femalepc01.dbr",
]


@dataclass(frozen=True)
class GamePaths:
    game_dir: Path

    @property
    def archive_tool(self) -> Path:
        return self.game_dir / "ArchiveTool.exe"

    @property
    def asset_manager(self) -> Path:
        return self.game_dir / "AssetManager.exe"

    @property
    def editor(self) -> Path:
        return self.game_dir / "Editor.exe"

    @property
    def quest_editor(self) -> Path:
        return self.game_dir / "QuestEditor.exe"

    @property
    def mods_dir(self) -> Path:
        return self.game_dir / "mods"

    @property
    def base_arz(self) -> Path:
        return self.game_dir / "database" / "database.arz"

    def dlc_arz_files(self) -> List[Path]:
        files: List[Path] = []
        for name, arz in (
            ("gdx1", "GDX1.arz"),
            ("gdx2", "GDX2.arz"),
            ("gdx3", "GDX3.arz"),
        ):
            p = self.game_dir / name / "database" / arz
            if p.is_file():
                files.append(p)
        return files

    def survival_arz_files(self) -> List[Path]:
        """Official Crucible/Survival DLC layers (survivalmode1–3) next to the game EXE."""
        files: List[Path] = []
        for layer in survival_layer_dirs(self.game_dir):
            db = layer / "database"
            if not db.is_dir():
                continue
            files.extend(sorted(db.glob("*.arz")))
        return files

    def layer_arz_files(self) -> List[Path]:
        layers: List[Path] = []
        if self.base_arz.is_file():
            layers.append(self.base_arz)
        layers.extend(self.dlc_arz_files())
        return layers

    def validate(self) -> None:
        if not self.game_dir.is_dir():
            raise FileNotFoundError(f"Game directory not found: {self.game_dir}")
        if not self.archive_tool.is_file():
            raise FileNotFoundError(f"ArchiveTool.exe not found in {self.game_dir}")
        self.mods_dir.mkdir(parents=True, exist_ok=True)


def survival_layer_dirs(game_dir: Path) -> List[Path]:
    """
    Crucible expansion folders at the game root (parallel to gdx1/gdx2/gdx3).

    survivalmode1 ≈ AoM Crucible, survivalmode2 ≈ FG, survivalmode3 ≈ FoA.
    Custom playgrounds can deploy as survivalmode4 to act like a Survival DLC layer.
    """
    root = Path(game_dir)
    found: List[Path] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        name = child.name.lower()
        if name.startswith("survivalmode") and name != "survivalmode":
            # skip mods/survivalmode — only game-root layers
            if child.parent.resolve() == root.resolve():
                found.append(child)
    return found


def resolve_game_dir(explicit: Optional[str] = None) -> Path:
    if explicit:
        return Path(explicit)
    env = os.environ.get("GD_GAME_DIR") or os.environ.get("GRIM_DAWN_DIR")
    if env:
        return Path(env)
    if DEFAULT_GAME_DIR.is_dir():
        return DEFAULT_GAME_DIR
    raise FileNotFoundError(
        "Grim Dawn install not found. Pass --game or set GD_GAME_DIR."
    )


def resolve_arzedit(explicit: Optional[str] = None) -> Optional[Path]:
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None
    env = os.environ.get("GD_ARZEDIT")
    if env:
        p = Path(env)
        if p.is_file():
            return p
    here = Path(__file__).resolve().parent
    for candidate in (
        here / "bin" / "arzedit.exe",
        here / "arzedit.exe",
        here / "arzedit" / "toolset" / "bin" / "arzedit.exe",
        Path.cwd() / "arzedit.exe",
    ):
        if candidate.is_file():
            return candidate
    return None


def find_mod_roots(mods_dir: Path, name_or_path: str) -> List[Path]:
    """Resolve a mod argument to playable mod roots (folders with database/*.arz or root *.arz)."""
    raw = Path(name_or_path)
    candidates: List[Path] = []
    if raw.is_dir():
        candidates.append(raw)
    else:
        direct = mods_dir / name_or_path
        if direct.is_dir():
            candidates.append(direct)

    roots: List[Path] = []
    for base in candidates:
        if _is_playable_mod(base):
            roots.append(base)
            continue
        for child in sorted(base.iterdir()):
            if child.is_dir() and _is_playable_mod(child):
                roots.append(child)
    return roots


def _is_playable_mod(path: Path) -> bool:
    db = path / "database"
    if db.is_dir() and any(db.glob("*.arz")):
        return True
    # Small overlay mods (e.g. Riftwalk) ship .arz at the mod root
    if any(path.glob("*.arz")):
        return True
    # Already-unpacked working mods
    if db.is_dir() and any(db.rglob("*.dbr")):
        return True
    return False


def iter_arz_in_mod(mod_root: Path) -> Iterable[Path]:
    db = mod_root / "database"
    if db.is_dir():
        yield from sorted(db.glob("*.arz"))
    # Root-level ARZ overlays
    yield from sorted(mod_root.glob("*.arz"))


def iter_arc_in_mod(mod_root: Path) -> Iterable[Path]:
    for folder in (mod_root / "resources", mod_root / "database"):
        if folder.is_dir():
            yield from sorted(folder.glob("*.arc"))
