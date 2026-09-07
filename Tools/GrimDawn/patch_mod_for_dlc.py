#!/usr/bin/env python3
"""Pass A: patch a mod so it works with FoA / v1.3 (import DLC + class hubs)."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from archive_tool import ArchiveTool, kill_orphan_archivetool
from arz_backend import build_database
from compat_engine import CompatEngine
from gd_paths import (
    GamePaths,
    find_mod_roots,
    iter_arz_in_mod,
    resolve_arzedit,
    resolve_game_dir,
)


def prepare_mod_database(game: GamePaths, mod_root: Path, work: Path) -> Path:
    """Extract mod ARZ into work/database if needed; return database folder."""
    db = mod_root / "database"
    # Prefer working extract so we don't mutate packed-only installs blindly
    extract_root = work / mod_root.name
    records = extract_root / "database"
    if records.exists() and any(records.rglob("*.dbr")):
        return records

    kill_orphan_archivetool()
    tool = ArchiveTool(game.game_dir)
    if extract_root.exists():
        shutil.rmtree(extract_root)
    records.mkdir(parents=True)
    arz_files = list(iter_arz_in_mod(mod_root))
    if not arz_files:
        # Already unpacked?
        if (db / "records").is_dir() or any(db.rglob("*.dbr")):
            shutil.copytree(db, records, dirs_exist_ok=True)
            return records
        raise FileNotFoundError(f"No .arz or unpacked DBRs in {mod_root}")

    for arz in arz_files:
        print(f"Extracting {arz} ...")
        tool.extract_database(arz, records)
    return records


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Patch mod for FoA/v1.3 DLC")
    p.add_argument("--game", default=None)
    p.add_argument("--mod", required=True, help="Mod name or path under mods/")
    p.add_argument("--work", default=None, help="Working directory for extracts")
    p.add_argument(
        "--out",
        default=None,
        help="Optional output Custom Game name under mods/ (copies patched DBRs)",
    )
    p.add_argument("--full-compat", action="store_true", help="Run Pass A + Pass B")
    p.add_argument(
        "--full-classes",
        action="store_true",
        help="Import all DLC class trees and keep mod class lines in hubs",
    )
    p.add_argument(
        "--class-mods",
        nargs="*",
        default=[],
        help="Extra mods to pull custom class lines from",
    )
    p.add_argument("--rebuild", action="store_true")
    p.add_argument("--arzedit", default=None)
    args = p.parse_args(argv)

    game = GamePaths(resolve_game_dir(args.game))
    game.validate()
    roots = find_mod_roots(game.mods_dir, args.mod)
    if not roots:
        print(f"Mod not found: {args.mod}", file=sys.stderr)
        return 1
    mod_root = roots[0]
    work = Path(args.work) if args.work else (Path(__file__).resolve().parent / "work")
    work.mkdir(parents=True, exist_ok=True)

    db = prepare_mod_database(game, mod_root, work)
    cache = work / "_vanilla_cache"
    engine = CompatEngine(game, db, cache)

    extras = []
    for name in args.class_mods or []:
        found = find_mod_roots(game.mods_dir, name)
        for fr in found:
            extras.append(prepare_mod_database(game, fr, work / "_class_mods"))

    if args.full_compat:
        report = engine.full_compat(
            full_classes=args.full_classes or bool(extras),
            extra_class_dbs=extras or None,
        )
    else:
        report = engine.pass_a_patch_mod_for_dlc(
            full_classes=args.full_classes or bool(extras)
        )
        if extras:
            engine.unlock_full_classes(extra_class_dbs=extras)
            report = engine.report

    report_path = work / f"{mod_root.name}_compat_report.md"
    report.write(report_path)
    print(f"Report: {report_path}")
    print(f"Working database: {db}")

    out_root = mod_root
    if args.out:
        out_root = game.mods_dir / args.out
        if out_root.exists():
            shutil.rmtree(out_root)
        shutil.copytree(mod_root, out_root, ignore=shutil.ignore_patterns("*.arz"))
        dest_db = out_root / "database"
        dest_db.mkdir(parents=True, exist_ok=True)
        for p in db.rglob("*"):
            if not p.is_file() or p.suffix.lower() == ".arz":
                continue
            rel = p.relative_to(db)
            target = dest_db / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
        shutil.copy2(report_path, out_root / "compat_report.md")
        print(f"Output Custom Game: {out_root}")

    if args.rebuild:
        ok, msg = build_database(out_root, game.game_dir, resolve_arzedit(args.arzedit))
        print(msg if ok else f"Rebuild: {msg}")

    kill_orphan_archivetool()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
