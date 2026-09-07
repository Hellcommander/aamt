"""Wrappers around Grim Dawn ArchiveTool.exe."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Optional, Sequence


class ArchiveToolError(RuntimeError):
    pass


class ArchiveTool:
    def __init__(self, game_dir: Path, archive_tool: Optional[Path] = None) -> None:
        self.game_dir = Path(game_dir)
        self.exe = Path(archive_tool) if archive_tool else self.game_dir / "ArchiveTool.exe"
        if not self.exe.is_file():
            raise FileNotFoundError(f"ArchiveTool not found: {self.exe}")

    def _run(self, args: Sequence[str], timeout: int = 600) -> str:
        cmd = [str(self.exe), *args]
        proc = subprocess.run(
            cmd,
            cwd=str(self.game_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            raise ArchiveToolError(
                f"ArchiveTool failed ({proc.returncode}): {' '.join(args)}\n{out[-2000:]}"
            )
        return out

    def extract_database(self, arz_path: Path, dest_dir: Path) -> str:
        # Resolve paths: ArchiveTool cwd is the game install.
        dest_dir = Path(dest_dir).resolve()
        dest_dir.mkdir(parents=True, exist_ok=True)
        return self._run(
            [str(Path(arz_path).resolve()), "-database", str(dest_dir)],
            timeout=1800,
        )

    def extract_arc(self, arc_path: Path, dest_dir: Path) -> str:
        dest_dir = Path(dest_dir).resolve()
        dest_dir.mkdir(parents=True, exist_ok=True)
        return self._run(
            [str(Path(arc_path).resolve()), "-extract", str(dest_dir)],
            timeout=1800,
        )

    def update_arc(self, arc_path: Path, source_dir: Path, compression: int = 6) -> str:
        """Pack/update an .arc from a directory (ArchiveTool -update)."""
        arc_path = Path(arc_path).resolve()
        source_dir = Path(source_dir).resolve()
        arc_path.parent.mkdir(parents=True, exist_ok=True)
        return self._run(
            [str(arc_path), "-update", ".", str(source_dir), str(compression)],
            timeout=1800,
        )

    def list_archive(self, archive_path: Path) -> str:
        return self._run([str(Path(archive_path).resolve()), "-list"], timeout=300)


def kill_orphan_archivetool() -> None:
    """Best-effort cleanup of leftover ArchiveTool processes (upstream merger issue)."""
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "ArchiveTool.exe"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        time.sleep(0.2)
    except Exception:
        pass
