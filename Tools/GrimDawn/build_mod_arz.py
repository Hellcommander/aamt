#!/usr/bin/env python3
"""
Build .arz databases via toolset arzedit (CLI Alternative to Asset Manager).

Defaults: rebuild Survival DLC (survivalmode4) + Campaign Custom Game
(CampaignKitchenSink). Requires bin/arzedit.exe (run Build-Arzedit.bat first).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from arz_backend import build_database
from gd_paths import GamePaths, resolve_arzedit, resolve_game_dir

TOOLS_DIR = Path(__file__).resolve().parent


def _rename_arz(db_dir: Path, preferred_stem: str) -> Optional[str]:
    """Ensure database/<preferred_stem>.arz exists (arzedit names after folder)."""
    preferred = db_dir / f"{preferred_stem}.arz"
    arz_files = sorted(db_dir.glob("*.arz"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not arz_files:
        return None
    newest = arz_files[0]
    if newest.resolve() == preferred.resolve():
        return str(preferred)
    if preferred.exists():
        preferred.unlink()
    newest.rename(preferred)
    return str(preferred)


def build_target(
    game: GamePaths,
    mod_dir: Path,
    *,
    arz_stem: Optional[str] = None,
    arzedit: Optional[Path] = None,
) -> Tuple[bool, str]:
    if not mod_dir.is_dir():
        return False, f"Missing folder: {mod_dir}"
    if not (mod_dir / "database").is_dir():
        return False, f"No database/ under {mod_dir}"

    ok, msg = build_database(mod_dir, game.game_dir, arzedit=arzedit)
    stem = arz_stem or mod_dir.name
    renamed = _rename_arz(mod_dir / "database", stem)
    if ok and renamed:
        msg = f"{msg}\nARZ: {renamed}"
    elif ok and not renamed:
        msg = f"{msg}\nWARN: build reported OK but no .arz found under {mod_dir / 'database'}"
        ok = False
    return ok, msg


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Build .arz via toolset arzedit")
    p.add_argument("--game", default=None)
    p.add_argument("--arzedit", default=None)
    p.add_argument(
        "--target",
        action="append",
        choices=("survival", "campaign", "staging", "all"),
        help="Repeatable. Default: survival + campaign. staging=SurvivalPlayground",
    )
    p.add_argument(
        "--mod",
        action="append",
        default=None,
        help="Extra mod folder name under mods/ or absolute path",
    )
    args = p.parse_args(argv)

    game = GamePaths(resolve_game_dir(args.game))
    game.validate()
    arz = resolve_arzedit(args.arzedit)
    if arz is None:
        print(
            "arzedit.exe not found. Build it first:\n"
            f"  {TOOLS_DIR / 'Build-Arzedit.bat'}\n"
            "Or set GD_ARZEDIT / --arzedit.",
            file=sys.stderr,
        )
        return 1

    print(f"Using arzedit: {arz}", flush=True)

    targets = args.target or ["survival", "campaign"]
    if "all" in targets:
        targets = ["survival", "campaign", "staging"]

    jobs: List[Tuple[Path, str]] = []
    for t in targets:
        if t == "survival":
            jobs.append((game.game_dir / "survivalmode4", "SurvivalMode4"))
        elif t == "campaign":
            jobs.append((game.mods_dir / "CampaignKitchenSink", "CampaignKitchenSink"))
        elif t == "staging":
            jobs.append((game.mods_dir / "SurvivalPlayground", "SurvivalPlayground"))

    for m in args.mod or []:
        path = Path(m)
        if not path.is_dir():
            path = game.mods_dir / m
        jobs.append((path, path.name))

    # Deduplicate by path
    seen = set()
    unique: List[Tuple[Path, str]] = []
    for path, stem in jobs:
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        unique.append((path, stem))

    failed = 0
    for path, stem in unique:
        print(f"\n=== Building {path.name} -> {stem}.arz ===", flush=True)
        ok, msg = build_target(game, path, arz_stem=stem, arzedit=arz)
        print(msg, flush=True)
        if not ok:
            failed += 1

    if failed:
        print(f"\nFinished with {failed} failure(s).", file=sys.stderr)
        return 1
    print("\nAll ARZ builds succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
