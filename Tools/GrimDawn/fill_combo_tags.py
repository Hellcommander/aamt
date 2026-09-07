#!/usr/bin/env python3
"""Generate all missing combo tags and inject into a mod's Text_EN.arc."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from archive_tool import ArchiveTool, kill_orphan_archivetool
from class_combo_names import (
    collect_tags,
    discover_mastery_ids,
    harvest_tag_roots,
    missing_all_combos,
    placeholder_names,
    write_tags,
)
from gd_paths import GamePaths, resolve_arzedit, resolve_game_dir
from patch_survival_classes import write_combo_tags

TOOLS = Path(__file__).resolve().parent


def inject_tags_into_text_arc(game: GamePaths, mod_root: Path, tag_file: Path) -> str:
    """Unpack Text_EN.arc, drop tag file into text_en/, repack with arzedit arc."""
    res = mod_root / "resources"
    arc = None
    for name in ("Text_EN.arc", "text_en.arc", "Text_en.arc"):
        cand = res / name
        if cand.is_file():
            arc = cand
            break
    if arc is None:
        return "No Text_EN.arc to inject into"

    work = TOOLS / "work" / "text_en_inject" / mod_root.name
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    print(f"Extracting {arc.name} ...", flush=True)
    ArchiveTool(game.game_dir).extract_arc(arc, work)
    kill_orphan_archivetool()

    # Find text_en folder
    text_dirs = [p for p in work.rglob("*") if p.is_dir() and p.name.lower() == "text_en"]
    if not text_dirs:
        # flat extract
        dest_dir = work / "text_en"
        dest_dir.mkdir(parents=True, exist_ok=True)
    else:
        dest_dir = text_dirs[0]
    shutil.copy2(tag_file, dest_dir / tag_file.name)

    arz = resolve_arzedit()
    if arz is None:
        return f"Tags copied to {dest_dir} but arzedit missing — Text_EN.arc not repacked"

    # Repack: arzedit arc <folder> <outfile>
    out_arc = res / arc.name
    bak = res / f"{arc.name}.bak_combos"
    if not bak.exists():
        shutil.copy2(arc, bak)
    cmd_cwd = str(arz.parent)
    import subprocess

    # Pack the parent of text_en so arc paths stay text_en/...
    pack_root = dest_dir.parent if dest_dir.name.lower() == "text_en" else work
    proc = subprocess.run(
        [str(arz), "arc", str(pack_root), str(out_arc)],
        cwd=cmd_cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    if proc.returncode != 0:
        return f"arzedit arc failed: {(proc.stdout or '') + (proc.stderr or '')}"[-1500:]
    return f"Injected {tag_file.name} into {out_arc}"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--game", default=None)
    p.add_argument(
        "--mod",
        action="append",
        default=None,
        help="Mod name under mods/ (default SurvivalPlayground + CampaignKitchenSink + survivalmode4)",
    )
    p.add_argument("--dry-run-names", action="store_true", default=True)
    p.add_argument("--no-dry-run-names", action="store_true")
    p.add_argument("--skip-text-arc", action="store_true")
    args = p.parse_args()

    game = GamePaths(resolve_game_dir(args.game))
    dry = not args.no_dry_run_names
    mods = args.mod or ["SurvivalPlayground", "CampaignKitchenSink"]
    targets = []
    for m in mods:
        path = Path(m)
        if not path.is_dir():
            path = game.mods_dir / m
        targets.append(path)
    sm4 = game.game_dir / "survivalmode4"
    if sm4.is_dir() and not args.mod:
        targets.append(sm4)

    for mod in targets:
        db = mod / "database" if (mod / "database").is_dir() else mod
        if not db.is_dir():
            print(f"Skip missing {mod}")
            continue
        print(f"\n=== {mod.name} ===", flush=True)
        n = write_combo_tags(db, mod, dry_run=dry, model=None)
        print(f"Generated/updated {n} combo tags", flush=True)
        tag = mod / "localization" / "tags_kitchen_sink_combos.txt"
        if tag.is_file() and not args.skip_text_arc:
            print(inject_tags_into_text_arc(game, mod, tag), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
