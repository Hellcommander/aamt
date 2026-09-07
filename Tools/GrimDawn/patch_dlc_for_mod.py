#!/usr/bin/env python3
"""Pass B: reconcile imported DLC records against mod deltas."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from archive_tool import kill_orphan_archivetool
from compat_engine import CompatEngine
from gd_paths import GamePaths, find_mod_roots, resolve_game_dir
from patch_mod_for_dlc import prepare_mod_database


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Patch DLC content for a mod")
    p.add_argument("--game", default=None)
    p.add_argument("--mod", required=True)
    p.add_argument("--work", default=None)
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
    engine = CompatEngine(game, db, work / "_vanilla_cache")
    report = engine.pass_b_patch_dlc_for_mod()
    report_path = work / f"{mod_root.name}_dlc_for_mod_report.md"
    report.write(report_path)
    print(f"Report: {report_path}")
    kill_orphan_archivetool()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
