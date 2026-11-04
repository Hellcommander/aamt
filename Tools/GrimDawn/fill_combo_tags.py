#!/usr/bin/env python3
"""Generate all missing combo tags and inject into a mod's Text_EN.arc."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Sequence

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


def _generated_keys(tag_files: Sequence[Path]) -> set:
    keys = set()
    for f in tag_files:
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            k, sep, _ = line.partition("=")
            if sep and k.strip().lower().startswith("tag"):
                keys.add(k.strip().lower())
    return keys


def strip_conflicting_combo_tags(text_root: Path, tag_files) -> int:
    """Drop lines for tags we regenerate (combo names, skill labels) from the mod's other text files.

    Combo lines were numbered for the mod's original class order and our label lines carry the
    full new value; with duplicates, which one the game keeps is undefined.
    """
    tag_files = [tag_files] if isinstance(tag_files, Path) else list(tag_files)
    ours_l = _generated_keys(tag_files)
    names = {f.name.lower() for f in tag_files}
    removed = 0
    for path in text_root.rglob("*.txt"):
        if path.name.lower() in names:
            continue
        lines = path.read_bytes().splitlines(keepends=True)
        kept = []
        for line in lines:
            # bytes-level so we never re-encode the mod's text files
            key = line.split(b"=", 1)[0].lstrip(b"\xef\xbb\xbf").strip().lower()
            if b"=" in line and key.decode("ascii", "ignore") in ours_l:
                removed += 1
                continue
            kept.append(line)
        if len(kept) != len(lines):
            path.write_bytes(b"".join(kept))
    return removed


def merge_with_game_text(game: GamePaths, root: Path) -> int:
    """
    A mod text file named like a game text file REPLACES the game's file, so a stale copy
    (e.g. Nydiamar's tags_items.txt) blanks every game tag it lacks. Rewrite such files as
    current game tags + the mod's tags on top (mod wins per tag). Returns files merged.
    """
    from class_combo_names import extract_text_roots

    game_files: Dict[str, List[Path]] = {}
    for r in extract_text_roots(game.game_dir, [], TOOLS / "work"):
        for p in r.rglob("*.txt"):
            game_files.setdefault(p.name.lower(), []).append(p)
    merged = 0
    for p in root.glob("*.txt"):
        srcs = game_files.get(p.name.lower())
        if not srcs:
            continue
        mod_lines = p.read_bytes().decode("utf-8", errors="replace").splitlines()
        mod_keys = {l.split("=", 1)[0].strip().lower() for l in mod_lines if "=" in l}
        extra = []
        for src in srcs:
            for l in src.read_bytes().decode("utf-8", errors="replace").splitlines():
                k = l.split("=", 1)[0].strip().lower()
                if "=" in l and k and k not in mod_keys:
                    extra.append(l)
                    mod_keys.add(k)
        if extra:
            body = "\n".join(mod_lines).rstrip() + "\n// current game tags missing from this mod copy (added by fill_combo_tags.py)\n" + "\n".join(extra) + "\n"
            p.write_bytes(body.encode("utf-8"))
            merged += 1
    return merged


def inject_tags_into_text_arc(
    game: GamePaths, mod_root: Path, tag_file, *, create: bool = False
) -> str:
    """Unpack Text_EN.arc, add tag file(s) at the archive's top level, repack.

    create=True builds a new resources/Text_EN.arc (just our tags) for mods that ship none;
    the game layers it over the official text. Archives an older version of this function
    packed as text_en/... (or text_en/text_en/...) are repaired in the same step.
    """
    from archive_tool import arc_root, pack_arc, strip_nested
    res = mod_root / "resources"
    arc = None
    for name in ("Text_EN.arc", "text_en.arc", "Text_en.arc"):
        cand = res / name
        if cand.is_file():
            arc = cand
            break
    if arc is None and not create:
        return "No Text_EN.arc to inject into"

    work = TOOLS / "work" / "text_en_inject" / mod_root.name
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    if arc is None:
        res.mkdir(parents=True, exist_ok=True)
        arc = res / "Text_EN.arc"
        root = work
    else:
        print(f"Extracting {arc.name} ...", flush=True)
        raw = work / "_raw"
        ArchiveTool(game.game_dir).extract_arc(arc, raw)
        kill_orphan_archivetool()
        # Text archives are flat: drop any text_en/ nesting older packers left (newest copy wins)
        root = work / "_flat"
        strip_nested(arc_root(raw, arc), root, arc.stem)
        shutil.rmtree(raw, ignore_errors=True)

    tag_files = [tag_file] if isinstance(tag_file, Path) else [Path(f) for f in tag_file]
    for f in tag_files:
        shutil.copy2(f, root / f.name)
    stripped = strip_conflicting_combo_tags(root, tag_files)
    if stripped:
        print(f"Removed {stripped} superseded tag lines from the mod's other text files", flush=True)
    n_merged = merge_with_game_text(game, root)
    if n_merged:
        print(f"Merged current game tags into {n_merged} mod text files that shadow game files", flush=True)

    if resolve_arzedit() is None:
        return f"Tags copied to {root} but arzedit missing — Text_EN.arc not repacked"
    bak = res / f"{arc.name}.bak_combos"
    if arc.is_file() and not bak.exists():
        shutil.copy2(arc, bak)
    try:
        pack_arc(root, res / arc.name)
    except Exception as exc:
        return f"arzedit arc failed: {exc}"
    return f"Injected {', '.join(f.name for f in tag_files)} into {res / arc.name}"


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
    p.add_argument("--no-dry-run-names", action="store_true", help="Use Ollama for names")
    p.add_argument("--ollama", dest="no_dry_run_names", action="store_true", help="Same as --no-dry-run-names")
    p.add_argument("--ollama-model", default=None)
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
        n = write_combo_tags(db, mod, dry_run=dry, model=args.ollama_model)
        print(f"Generated/updated {n} combo tags", flush=True)
        tag = mod / "localization" / "tags_kitchen_sink_combos.txt"
        if tag.is_file() and not args.skip_text_arc:
            print(inject_tags_into_text_arc(game, mod, tag), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
