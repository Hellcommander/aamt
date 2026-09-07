#!/usr/bin/env python3
"""
Imbalance: full mob level scaling to the player (Smash n Grab–style).

Only this feature — not loot/XP/skills/devotion, and not merging Smash n Grab.

Sets every Proxy / ProxyAmbush DBR's difficultyLimitsFile to
records/proxies/limit_unlimited.dbr (and ensures that limits file exists).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from dbr_io import read_dbr, write_dbr
from gd_paths import GamePaths, resolve_game_dir

UNLIMITED = "records/proxies/limit_unlimited.dbr"
PROXY_CLASSES = {"proxy", "proxyambush"}


def ensure_unlimited_limits(db: Path) -> bool:
    """Create/overwrite limit_unlimited.dbr so min=max=averagePlayerLevel on all diffs."""
    path = db / "records" / "proxies" / "limit_unlimited.dbr"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "templateName": "database/templates/proxylimits.tpl",
        "FileDescription": "Kitchen-sink imbalance: mobs always match player level",
        "minPlayerLevelEquationNormal": "averagePlayerLevel*1",
        "maxPlayerLevelEquationNormal": "averagePlayerLevel*1",
        "minPlayerLevelEquationEpic": "averagePlayerLevel*1",
        "maxPlayerLevelEquationEpic": "averagePlayerLevel*1",
        "minPlayerLevelEquationLegendary": "averagePlayerLevel*1",
        "maxPlayerLevelEquationLegendary": "averagePlayerLevel*1",
    }
    write_dbr(path, data)
    return True


def _is_spawn_proxy(data: dict) -> bool:
    cls = (data.get("Class") or "").strip().lower()
    if cls in PROXY_CLASSES:
        return True
    tpl = (data.get("templateName") or "").replace("\\", "/").lower()
    return tpl.endswith("/proxy.tpl") or tpl.endswith("/proxyambush.tpl")


def patch_database(db: Path) -> Tuple[int, int, int]:
    """
    Returns (changed, already_ok, skipped).
    """
    ensure_unlimited_limits(db)
    changed = already = skipped = 0
    proxies = db / "records" / "proxies"
    if not proxies.is_dir():
        return 0, 0, 0

    for path in proxies.rglob("*.dbr"):
        if path.name.lower() == "limit_unlimited.dbr":
            skipped += 1
            continue
        if path.name.lower().startswith("limit_"):
            skipped += 1
            continue
        try:
            data = read_dbr(path)
        except Exception:
            skipped += 1
            continue

        # Always force spawn proxies; also fix any record that already has the field
        has_field = "difficultyLimitsFile" in data
        if not has_field and not _is_spawn_proxy(data):
            skipped += 1
            continue

        cur = data.get("difficultyLimitsFile", "")
        if cur.replace("\\", "/") == UNLIMITED:
            already += 1
            continue
        data["difficultyLimitsFile"] = UNLIMITED
        write_dbr(path, data)
        changed += 1

    return changed, already, skipped


def default_targets(game: GamePaths) -> List[Path]:
    out: List[Path] = []
    for name in ("SurvivalPlayground", "CampaignKitchenSink"):
        db = game.mods_dir / name / "database"
        if db.is_dir():
            out.append(db)
    sm4 = game.game_dir / "survivalmode4" / "database"
    if sm4.is_dir():
        out.append(sm4)
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--game", default=None)
    p.add_argument(
        "--mod",
        action="append",
        default=None,
        help="Mod folder under mods/ or absolute path (repeatable). "
        "Default: SurvivalPlayground, CampaignKitchenSink, survivalmode4",
    )
    args = p.parse_args(argv)
    game = GamePaths(resolve_game_dir(args.game))

    targets: List[Path] = []
    if args.mod:
        for m in args.mod:
            path = Path(m)
            if not path.is_dir():
                path = game.mods_dir / m
            if (path / "database").is_dir():
                path = path / "database"
            targets.append(path)
    else:
        targets = default_targets(game)

    if not targets:
        print("No target databases found.", file=sys.stderr)
        return 1

    rc = 0
    for db in targets:
        try:
            changed, already, skipped = patch_database(db)
            print(
                f"{db}: changed={changed} already_unlimited={already} skipped={skipped}",
                flush=True,
            )
        except Exception as exc:
            print(f"ERROR {db}: {exc}", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
