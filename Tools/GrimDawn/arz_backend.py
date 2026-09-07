"""Optional ARZ rebuild via arzedit or instructions for AssetManager."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional, Tuple


def build_database(
    mod_dir: Path,
    game_dir: Path,
    arzedit: Optional[Path] = None,
    templates_dir: Optional[Path] = None,
) -> Tuple[bool, str]:
    """
    Try `arzedit build` like the upstream merger.
    Returns (ok, message).
    """
    if arzedit is None or not Path(arzedit).is_file():
        return (
            False,
            "arzedit not found. Set GD_ARZEDIT or --arzedit, or rebuild the mod "
            f"database with AssetManager.exe on: {mod_dir}",
        )

    templates = templates_dir or (mod_dir / "database" / "templates")
    templates.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(arzedit),
        "build",
        str(mod_dir),
        str(mod_dir),
        "-g",
        str(game_dir),
        "-t",
        str(templates),
        "-A",
        "-R",
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(Path(arzedit).parent),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3600,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            return False, f"arzedit failed ({proc.returncode}):\n{out[-3000:]}"
        return True, out[-2000:] or "arzedit build completed."
    except Exception as exc:
        return False, f"arzedit error: {exc}"
