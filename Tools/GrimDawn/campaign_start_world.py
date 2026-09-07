#!/usr/bin/env python3
"""
Install the kitchen-sink campaign start world (World001) into a Custom Game.

Nydiamar Maps.arc stays for portal destinations only — never the spawn world.

IMPORTANT: World001 must come from the merged content mods (e.g. Grimarillion's
edited levels.arc), NOT vanilla gdx*/Levels.arc. Copying stock FoA world would
drop Grimarillion (and similar) map edits — that is not a merge.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from archive_tool import ArchiveTool, kill_orphan_archivetool
from gd_paths import GamePaths, resolve_game_dir
from merge_rules import find_rules_for_mod, load_all_rules, sort_mods_by_priority

TOOLS = Path(__file__).resolve().parent
MIN_LEVELS_BYTES = 1_000_000  # ignore empty/stub ARCs (often 2048 bytes)


def _levels_arc_in(mod_root: Path) -> Optional[Path]:
    res = mod_root / "resources"
    if not res.is_dir():
        return None
    for name in ("levels.arc", "Levels.arc"):
        cand = res / name
        if cand.is_file() and cand.stat().st_size >= MIN_LEVELS_BYTES:
            return cand
    # case-insensitive scan
    for cand in res.glob("*.arc"):
        if cand.name.lower() == "levels.arc" and cand.stat().st_size >= MIN_LEVELS_BYTES:
            return cand
    return None


def _level_art_arc_in(mod_root: Path) -> Optional[Path]:
    res = mod_root / "resources"
    if not res.is_dir():
        return None
    for cand in res.glob("*.arc"):
        if cand.name.lower() in ("level art.arc", "levelart.arc") and cand.stat().st_size > 0:
            return cand
    return None


def _profile_content_mod_names(game: GamePaths) -> List[str]:
    profile = TOOLS / "profiles" / "survivalmode.json"
    if not profile.is_file():
        return []
    try:
        data = json.loads(profile.read_text(encoding="utf-8"))
    except Exception:
        return []
    names: List[str] = []
    for key in ("content_mods", "class_mods", "portal_mods"):
        for n in data.get(key) or []:
            if n not in names:
                names.append(str(n))
    return names


def resolve_kitchen_sink_levels(
    game: GamePaths,
    *,
    staging_mod: Optional[Path] = None,
) -> Tuple[Path, Path, str]:
    """
    Pick Levels.arc from kitchen-sink contributors (highest merge priority wins).

    Returns (levels_arc, source_mod_root, reason).
    """
    candidates: List[Tuple[int, str, Path, Path]] = []
    # staging first as explicit merge output (may lack levels if skip-resources)
    if staging_mod is not None:
        arc = _levels_arc_in(staging_mod)
        if arc:
            return arc, staging_mod, f"staging {staging_mod.name}"

    rules = load_all_rules()
    names = _profile_content_mod_names(game)
    # Always consider known world editors even if profile omitted
    for extra in ("grimarillion", "Rebirth", "dom"):
        if extra not in names:
            names.append(extra)

    mod_paths: List[Path] = []
    for name in names:
        p = game.mods_dir / name
        if p.is_dir():
            mod_paths.append(p)

    # Ascending priority — last contributor with a real Levels.arc wins
    for mod_path in sort_mods_by_priority(mod_paths, rules):
        arc = _levels_arc_in(mod_path)
        if not arc:
            continue
        mr = find_rules_for_mod(mod_path.name, rules)
        pri = mr.priority if mr else 0
        candidates.append((pri, mod_path.name, arc, mod_path))

    if not candidates:
        raise FileNotFoundError(
            "No kitchen-sink Levels.arc found (need grimarillion/resources/levels.arc "
            "or SurvivalPlayground with merged levels). Refusing vanilla gdx Levels — "
            "that would drop Grimarillion world edits."
        )

    pri, name, arc, root = candidates[-1]
    return arc, root, f"kitchen-sink {name} (priority {pri})"


def install_campaign_start_world(
    game: GamePaths,
    mod_root: Path,
    *,
    source_levels: Optional[Path] = None,
    staging_mod: Optional[Path] = None,
) -> List[str]:
    """
    Install merged kitchen-sink World001 (Levels.arc) as Custom Game start.
    Leaves Nydiamar Maps.arc untouched for portals.
    """
    notes: List[str] = []
    src_mod: Optional[Path] = None
    if source_levels is not None:
        src = Path(source_levels)
        reason = f"explicit {src}"
    else:
        src, src_mod, reason = resolve_kitchen_sink_levels(game, staging_mod=staging_mod)
    notes.append(f"Campaign start Levels source: {reason} -> {src}")

    res = mod_root / "resources"
    res.mkdir(parents=True, exist_ok=True)
    dest_levels = res / "Levels.arc"

    tool = ArchiveTool(game.game_dir)
    try:
        listing = tool.list_archive(src).lower()
        kill_orphan_archivetool()
        if "world001.map" not in listing:
            raise FileNotFoundError(f"world001.map not listed in {src}")
        notes.append("Verified world001.map in kitchen-sink Levels.arc")
    except Exception as exc:
        notes.append(f"WARN: list Levels.arc failed ({exc}); copying anyway")

    # Replace stub/empty Levels from bad prior installs
    if dest_levels.exists():
        dest_levels.unlink()
    shutil.copy2(src, dest_levels)
    notes.append(f"Installed {dest_levels.name} ({dest_levels.stat().st_size} bytes)")

    # Level Art from same kitchen-sink mod (Grimarillion ships a small companion ARC)
    art_src = _level_art_arc_in(src_mod) if src_mod else None
    if art_src is None and src.parent.name.lower() == "resources":
        art_src = _level_art_arc_in(src.parent.parent)
    if art_src is not None:
        dest_art = res / "Level Art.arc"
        # Prefer kitchen-sink art over Nydiamar's when installing campaign start
        shutil.copy2(art_src, dest_art)
        notes.append(f"Installed Level Art.arc from {art_src.parent.parent.name}")

    play = mod_root / "PLAY_START.txt"
    play.write_text(
        "\n".join(
            [
                "START HERE — Custom Game map selection",
                "=====================================",
                "",
                "Select:  this mod  ~  World001.map",
                "",
                "Do NOT start on nydiamar.map / nydiamardungeons.map",
                "(portal destinations only).",
                "",
                f"Levels source: {reason}",
                "",
                "World001 is the kitchen-sink/Grimarillion edited map — not stock FoA.",
                "FoA Asterkarn regions live in gdx3 world001; those two map files cannot",
                "be auto-merged. If Asterkarn is missing: use FoA-updated Grimarillion",
                "levels, or Editor-stitch FoA regions into this World001 (see",
                "editor_stitch_checklist.md). Never replace Levels with stock gdx3",
                "alone — that wipes Grimarillion world edits.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    notes.append(f"Wrote {play.name}")

    # Detect likely missing FoA map markers in the installed kitchen-sink Levels
    try:
        blob = dest_levels.read_bytes().lower()
        if blob.count(b"kurn") < 10 and blob.count(b"asterkarn") < 2:
            notes.append(
                "WARN: installed Levels.arc looks light on FoA map markers "
                "(kurn/asterkarn). Grimarillion edits are kept; full FoA map "
                "access needs FoA-updated grim levels or Editor stitch — "
                "not a stock gdx3 Levels replace."
            )
    except OSError:
        pass
    return notes


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--game", default=None)
    p.add_argument(
        "--mod",
        action="append",
        default=None,
        help="Target mod under mods/ (default: CampaignKitchenSink)",
    )
    p.add_argument(
        "--staging",
        default="SurvivalPlayground",
        help="Kitchen-sink staging mod to prefer for Levels (if present)",
    )
    p.add_argument("--levels-arc", default=None, help="Override Levels.arc path")
    args = p.parse_args(argv)

    game = GamePaths(resolve_game_dir(args.game))
    staging = game.mods_dir / args.staging if args.staging else None
    if staging and not staging.is_dir():
        staging = None
    mods = args.mod or ["CampaignKitchenSink"]
    src = Path(args.levels_arc) if args.levels_arc else None
    for name in mods:
        root = Path(name)
        if not root.is_dir():
            root = game.mods_dir / name
        if not root.is_dir():
            print(f"Missing mod: {root}", file=sys.stderr)
            return 1
        for line in install_campaign_start_world(
            game, root, source_levels=src, staging_mod=staging
        ):
            print(line)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
