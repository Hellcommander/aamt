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


def arc_root(extract_dir: Path, arc_path: Path) -> Path:
    """
    Folder holding an archive's real contents after ArchiveTool -extract.

    ArchiveTool nests files under <arc stem> (Creatures.arc -> creatures/...), but paths INSIDE
    an .arc never include that name (the game resolves "creatures/x.msh" as Creatures.arc + "x.msh").
    Older packers in this toolkit repacked one level too high, so also strip any extra
    stem-named folders they left behind (text_en/text_en/...).
    """
    root = Path(extract_dir)
    stem = Path(arc_path).stem.lower()
    while root.is_dir():
        kids = list(root.iterdir())
        if len(kids) == 1 and kids[0].is_dir() and kids[0].name.lower() == stem:
            root = kids[0]
            continue
        break
    return root


def pack_arc(root: Path, arc_path: Path) -> None:
    """Pack `root`'s contents as the archive's top level (arzedit arc)."""
    from gd_paths import resolve_arzedit

    arz = resolve_arzedit()
    if not arz:
        raise ArchiveToolError("bin/arzedit.exe missing (run Build-Arzedit.bat)")
    Path(arc_path).parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([str(arz), "arc", str(root), str(arc_path)], capture_output=True, text=True)
    if proc.returncode != 0:
        raise ArchiveToolError(f"arzedit arc {arc_path}: {(proc.stdout + proc.stderr)[-1500:]}")


def arc_entries(game_dir: Path, arc_path: Path) -> list:
    out = subprocess.run(
        [str(Path(game_dir) / "ArchiveTool.exe"), str(Path(arc_path).resolve()), "-list"],
        capture_output=True, text=True, cwd=str(game_dir), errors="replace",
    ).stdout
    return [l.strip().replace("\\", "/") for l in out.splitlines() if l.strip()]


def needs_repair(game_dir: Path, arc_path: Path) -> bool:
    entries = arc_entries(game_dir, arc_path)
    prefix = Path(arc_path).stem.lower() + "/"
    return bool(entries) and all(e.lower().startswith(prefix) for e in entries)


def strip_nested(src_root: Path, dest_root: Path, stem: str) -> int:
    """
    Copy files to dest_root with every leading "<stem>/" removed (text_en/text_en/x -> x).
    When the same file exists at several depths, the shallowest (= most recently packed) wins.
    Returns the number of files written.
    """
    import shutil

    best: dict = {}
    for p in Path(src_root).rglob("*"):
        if not p.is_file():
            continue
        parts = list(p.relative_to(src_root).parts)
        depth = 0
        while len(parts) > 1 and parts[0].lower() == stem.lower():
            parts.pop(0)
            depth += 1
        key = "/".join(parts).lower()
        if key not in best or depth < best[key][0]:
            best[key] = (depth, p, parts)
    for _, p, parts in best.values():
        dest = Path(dest_root).joinpath(*parts)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
    return len(best)


def repair_arc(game_dir: Path, arc_path: Path, work: Path, *, strip: bool = False) -> bool:
    """
    Re-pack an archive whose entries all wrongly start with its own name. Returns True if fixed.

    strip=True also fixes MIXED nesting (some entries prefixed, some not) -- only use it for
    archives known to be broken: some mods ship a real sub-folder named like the archive
    (Nydiamar's Sound.arc has sound/...).
    """
    import shutil

    if not strip and not needs_repair(game_dir, arc_path):
        return False
    if strip:
        prefix = Path(arc_path).stem.lower() + "/"
        if not any(e.lower().startswith(prefix) for e in arc_entries(game_dir, arc_path)):
            return False
        tmp = Path(work) / f"_repair_{Path(arc_path).stem}"
        clean = Path(work) / f"_repair_{Path(arc_path).stem}_clean"
        for d in (tmp, clean):
            if d.exists():
                shutil.rmtree(d)
            d.mkdir(parents=True)
        try:
            ArchiveTool(game_dir).extract_arc(arc_path, tmp)
            bak = Path(arc_path).with_suffix(".arc.bak_prefix")
            if not bak.exists():
                shutil.copy2(arc_path, bak)
            strip_nested(arc_root(tmp, arc_path), clean, Path(arc_path).stem)
            pack_arc(clean, arc_path)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            shutil.rmtree(clean, ignore_errors=True)
        return True
    tmp = Path(work) / f"_repair_{Path(arc_path).stem}"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    try:
        ArchiveTool(game_dir).extract_arc(arc_path, tmp)
        bak = Path(arc_path).with_suffix(".arc.bak_prefix")
        if not bak.exists():
            shutil.copy2(arc_path, bak)
        pack_arc(arc_root(tmp, arc_path), arc_path)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return True


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


def main(argv: Optional[Sequence[str]] = None) -> int:
    """python archive_tool.py --repair <mod name or folder> [...]  -- fix prefixed archives."""
    import argparse

    from gd_paths import GamePaths, resolve_game_dir

    p = argparse.ArgumentParser(description="Archive helpers")
    p.add_argument("--repair", nargs="+", required=True, help="Mods (under mods/) or folders whose resources/*.arc to check")
    p.add_argument("--strip", nargs="*", default=[], help="Archive names known broken with MIXED nesting (e.g. ui.arc text_en.arc)")
    p.add_argument("--game", default=None)
    a = p.parse_args(argv)
    strip_names = {s.lower() for s in a.strip}
    game = GamePaths(resolve_game_dir(a.game))
    work = Path(__file__).resolve().parent / "work"
    for target in a.repair:
        root = Path(target) if Path(target).is_dir() else game.mods_dir / target
        for arc in sorted((root / "resources").glob("*.arc")):
            try:
                fixed = repair_arc(game.game_dir, arc, work, strip=arc.name.lower() in strip_names)
                print(f"{'FIXED ' if fixed else 'ok    '} {arc}", flush=True)
            except Exception as exc:  # e.g. >2 GB maps ArchiveTool can't unpack: rebuild those instead
                print(f"FAILED {arc}: {str(exc)[:200]}", flush=True)
    kill_orphan_archivetool()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
