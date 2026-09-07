#!/usr/bin/env python3
"""
Merge multiple Grim Dawn mods into one Custom Game folder.

Adapted from Ian Chapman / LazyGuyWithRSI grim_dawn_mod_merger (MIT) —
extract ARZ/ARC via ArchiveTool, overlay files (later wins), rebuild with arzedit.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import List, Tuple

from archive_tool import ArchiveTool, kill_orphan_archivetool
from arz_backend import build_database
from gd_paths import (
    find_mod_roots,
    iter_arc_in_mod,
    iter_arz_in_mod,
    resolve_arzedit,
    resolve_game_dir,
    GamePaths,
)


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def overlay_tree(
    src: Path,
    dest: Path,
    conflicts: List[Tuple[str, str, str]],
    winner_label: str,
    skip_ext: Tuple[str, ...] = (".arz", ".arc"),
) -> None:
    if not src.exists():
        return
    for item in src.rglob("*"):
        if item.is_dir():
            continue
        if item.suffix.lower() in skip_ext:
            continue
        rel = item.relative_to(src)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            conflicts.append((_rel(target, dest), winner_label, "previous"))
        shutil.copy2(item, target)


def merge_mods(
    game: GamePaths,
    mod_roots: List[Path],
    out_name: str,
    arzedit: Path | None,
    rebuild: bool,
) -> Path:
    kill_orphan_archivetool()
    tool = ArchiveTool(game.game_dir)
    out_dir = game.mods_dir / out_name
    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "database").mkdir(parents=True)
    (out_dir / "database" / "templates").mkdir(parents=True)
    (out_dir / "resources").mkdir(parents=True)
    (out_dir / "source").mkdir(parents=True)

    work = out_dir / "_merge_work"
    work.mkdir(parents=True)
    conflicts: List[Tuple[str, str, str]] = []

    for mod in mod_roots:
        label = mod.name
        print(f"Merging: {mod}")
        # Non-archive files
        overlay_tree(mod, out_dir, conflicts, label)

        # Extract databases into shared database tree (later overwrites)
        db_dest = out_dir / "database"
        for arz in iter_arz_in_mod(mod):
            print(f"  Extract ARZ {arz.name}")
            staged = work / f"arz_{mod.name}_{arz.stem}"
            if staged.exists():
                shutil.rmtree(staged)
            staged.mkdir(parents=True)
            tool.extract_database(arz, staged)
            overlay_tree(staged, db_dest, conflicts, label, skip_ext=())

        # Extract resource ARCs into source/<arcname>/ then pack back
        for arc in iter_arc_in_mod(mod):
            print(f"  Extract ARC {arc.name}")
            arc_stem = arc.stem
            extract_to = out_dir / "source" / arc_stem
            extract_to.mkdir(parents=True, exist_ok=True)
            before = {p for p in extract_to.rglob("*") if p.is_file()}
            tool.extract_arc(arc, extract_to)
            after = {p for p in extract_to.rglob("*") if p.is_file()}
            for p in after:
                if p in before:
                    conflicts.append((_rel(p, out_dir), label, "previous"))
            # Pack into resources (or database if that was the source folder)
            dest_arc = (
                out_dir / "resources" / arc.name
                if arc.parent.name.lower() == "resources"
                else out_dir / "database" / arc.name
            )
            try:
                tool.update_arc(dest_arc, extract_to)
            except Exception as exc:
                print(f"  WARN: could not pack {arc.name}: {exc}")

    report = out_dir / "merge_conflicts.txt"
    with report.open("w", encoding="utf-8") as fh:
        fh.write(f"Merged mods (later wins): {[m.name for m in mod_roots]}\n")
        fh.write(f"Conflicts / overwrites: {len(conflicts)}\n\n")
        for path, winner, loser in conflicts:
            fh.write(f"{path}\twinner={winner}\toverwrote={loser}\n")
    print(f"Conflict report: {report} ({len(conflicts)} entries)")

    if rebuild:
        ok, msg = build_database(out_dir, game.game_dir, arzedit)
        print(msg if ok else f"Rebuild skipped/failed: {msg}")
    else:
        print("Skipping ARZ rebuild (--no-rebuild). Use AssetManager or pass --rebuild.")

    kill_orphan_archivetool()
    # Clean staging
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    return out_dir


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Merge Grim Dawn mod databases")
    parser.add_argument("--game", default=None, help="Grim Dawn install directory")
    parser.add_argument("--out", required=True, help="Output mod folder name under mods/")
    parser.add_argument(
        "--mods",
        nargs="+",
        required=True,
        help="Mod folder names or paths (order = priority, later wins)",
    )
    parser.add_argument("--arzedit", default=None, help="Path to arzedit.exe")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Attempt arzedit rebuild after merge",
    )
    parser.add_argument(
        "--no-rebuild",
        action="store_true",
        help="Do not rebuild (default unless --rebuild)",
    )
    args = parser.parse_args(argv)

    game_dir = resolve_game_dir(args.game)
    game = GamePaths(game_dir)
    game.validate()

    roots: List[Path] = []
    for name in args.mods:
        found = find_mod_roots(game.mods_dir, name)
        if not found:
            print(f"ERROR: mod not found: {name}", file=sys.stderr)
            return 1
        roots.extend(found)

    arzedit = resolve_arzedit(args.arzedit)
    rebuild = bool(args.rebuild) and not args.no_rebuild
    out = merge_mods(game, roots, args.out, arzedit, rebuild)
    print(f"Done: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
