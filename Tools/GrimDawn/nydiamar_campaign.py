#!/usr/bin/env python3
"""
Nydiamar + FoA unified Custom Game pipeline.

1) Copy / merge Nydiamar (+ optional NydiamarDungeons)
2) Bidirectional FoA/v1.3 compat (Pass A + B)
3) Namespace quests under nydiamar/
4) Generate Berserker dual-class combo names (Ollama)
5) Unpack Maps/Quests ARCs + portal stubs + Editor stitch checklist

Same characters for FoA + Nydiamar means one Custom Game save, not stock Campaign.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from archive_tool import ArchiveTool, kill_orphan_archivetool
from arz_backend import build_database
from class_combo_names import (
    collect_tags,
    discover_mastery_ids,
    missing_berserker_combos,
    ollama_generate,
    placeholder_names,
    resolve_ollama_model,
    write_tags,
)
from compat_engine import CompatEngine
from editor_stitch import (
    extract_editor_arcs,
    normalize_portal_hub,
    write_editor_checklist,
    write_portal_stubs,
)
from gd_paths import (
    DEFAULT_NYDIAMAR_SOURCE,
    GamePaths,
    find_mod_roots,
    iter_arz_in_mod,
    resolve_arzedit,
    resolve_game_dir,
)
from quest_remap import remap_tree, write_report as write_quest_report

TOOLS_DIR = Path(__file__).resolve().parent
DEFAULT_PROFILE = TOOLS_DIR / "profiles" / "nydiamar.json"


def load_profile(path: Optional[Path]) -> Dict[str, Any]:
    p = path or DEFAULT_PROFILE
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def resolve_nydiamar_roots(game: GamePaths, source: Optional[str]) -> List[Path]:
    """
    Resolve Nydiamar (+ sibling NydiamarDungeons when present).

    Flat layout: mods/Nydiamar + mods/NydiamarDungeons
    Nested layout: mods/Nydiamar-40-.../Nydiamar (+ .../NydiamarDungeons)
    """
    raw = Path(source) if source else DEFAULT_NYDIAMAR_SOURCE
    if not raw.is_absolute():
        cand = game.mods_dir / raw
        if cand.is_dir():
            raw = cand
    if not raw.is_dir():
        alt = game.mods_dir / raw.name
        if alt.is_dir():
            raw = alt
    if not raw.is_dir():
        raise FileNotFoundError(f"Nydiamar source not found: {source or DEFAULT_NYDIAMAR_SOURCE}")

    def _is_playable(p: Path) -> bool:
        db = p / "database"
        return (
            (db.is_dir() and (any(db.glob("*.arz")) or any(db.rglob("*.dbr"))))
            or any(p.glob("*.arz"))
        )

    roots: List[Path] = []

    def _add(p: Path) -> None:
        if not p.is_dir() or not _is_playable(p):
            return
        rp = p.resolve()
        if not any(r.resolve() == rp for r in roots):
            roots.append(p)

    found = find_mod_roots(game.mods_dir, str(raw))
    for f in found:
        _add(f)
    if not roots and _is_playable(raw):
        _add(raw)

    # Prefer a root named Nydiamar as primary ordering
    roots.sort(key=lambda p: (0 if p.name.lower() == "nydiamar" else 1, p.name.lower()))

    # Sibling dungeon pack (flat mods/ or nested next to primary)
    _add(game.mods_dir / "NydiamarDungeons")
    if roots:
        _add(roots[0].parent / "NydiamarDungeons")

    if not any(r.name.lower() == "nydiamar" or "nydiamar" in r.name.lower() for r in roots):
        raise FileNotFoundError(f"Nydiamar mod not found under/near: {raw}")
    return roots


def merge_arc_contents(game: GamePaths, base_arc: Path, overlay_arc: Path, dest_arc: Path) -> str:
    """
    Additive ARC merge: keep every base file, add overlay-only files.
    Same relative path → keep base (no silent replace). Conflicts are counted.
    """
    from archive_tool import ArchiveTool, kill_orphan_archivetool

    work = Path(__file__).resolve().parent / "work" / "arc_merge" / dest_arc.stem
    if work.exists():
        shutil.rmtree(work)
    base_dir = work / "base"
    over_dir = work / "overlay"
    merged = work / "merged"
    base_dir.mkdir(parents=True)
    over_dir.mkdir(parents=True)
    merged.mkdir(parents=True)

    tool = ArchiveTool(game.game_dir)
    tool.extract_arc(base_arc, base_dir)
    kill_orphan_archivetool()
    tool.extract_arc(overlay_arc, over_dir)
    kill_orphan_archivetool()

    added = kept_base = conflicts = 0
    for path in base_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(base_dir)
        target = merged / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        kept_base += 1

    for path in over_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(over_dir)
        target = merged / rel
        if target.is_file():
            # Same path in both — do not override base
            try:
                if target.read_bytes() != path.read_bytes():
                    conflicts += 1
            except OSError:
                conflicts += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        added += 1

    if dest_arc.exists():
        dest_arc.unlink()
    tool.update_arc(dest_arc, merged)
    kill_orphan_archivetool()
    names = sorted({p.name for p in merged.rglob("*") if p.is_file()})
    preview = ", ".join(names[:12]) + ("…" if len(names) > 12 else "")
    return (
        f"{dest_arc.name}: kept_base={kept_base} added={added} "
        f"conflicts_kept_base={conflicts} [{preview}]"
    )


def merge_mod_resources(
    src_mod: Path,
    out_mod: Path,
    *,
    game: Optional[GamePaths] = None,
) -> List[str]:
    """
    Merge resource ARCs from src into out without whole-file replacement.
    When dest ARC already exists, unpack both and additively union members.
    When dest is missing, copy once (first contributor).
    """
    src_res = src_mod / "resources"
    dest_res = out_mod / "resources"
    if not src_res.is_dir():
        return []
    dest_res.mkdir(parents=True, exist_ok=True)
    notes: List[str] = []
    for arc in sorted(src_res.glob("*.arc")):
        dest = dest_res / arc.name
        if game is not None and dest.is_file():
            notes.append(merge_arc_contents(game, dest, arc, dest))
        elif dest.is_file():
            notes.append(
                f"SKIP {arc.name}: dest exists but no game handle for content-merge "
                f"(refusing overwrite)"
            )
        else:
            shutil.copy2(arc, dest)
            notes.append(f"added {arc.name}")
    return notes


def merge_extracted_databases(src_db: Path, dest_db: Path) -> Tuple[int, int, int]:
    """
    Additive DBR merge of src into dest.
    New files are copied; existing .dbr files field-merge (unique keys from both);
    non-dbr conflicts keep dest (no binary overwrite).
    Returns (added, field_merged, kept_base_conflicts).
    """
    from dbr_io import merge_dbr_preserve_both, read_dbr, write_dbr

    added = field_merged = kept_base = 0
    for p in src_db.rglob("*"):
        if not p.is_file() or p.suffix.lower() == ".arz":
            continue
        rel = p.relative_to(src_db)
        target = dest_db / rel
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
            added += 1
            continue
        if p.suffix.lower() == ".dbr" and target.suffix.lower() == ".dbr":
            try:
                merged = merge_dbr_preserve_both(
                    read_dbr(target),
                    read_dbr(p),
                    # Prefer incoming only for explicit skill/item deltas; keep base
                    # quest/story/world keys when both define the same field.
                    prefer_overlay_substrings=(
                        "skill",
                        "Skill",
                        "item",
                        "Item",
                        "loot",
                        "Loot",
                        "character",
                        "Character",
                    ),
                    keep_base_substrings=(
                        "quest",
                        "Quest",
                        "conversation",
                        "Conversation",
                        "map",
                        "Map",
                        "world",
                        "World",
                        "spawn",
                        "Spawn",
                        "level",
                        "Level",
                    ),
                    list_prefixes=("skillName", "itemName", "lootName"),
                    semicolon_keys=("skillTree",),
                )
                write_dbr(target, merged)
                field_merged += 1
            except Exception:
                kept_base += 1
        else:
            kept_base += 1
    return added, field_merged, kept_base


def copy_mod_skeleton(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for name in ("resources", "source", "localization"):
        s = src / name
        if s.exists():
            shutil.copytree(s, dest / name, dirs_exist_ok=True)
    for item in src.iterdir():
        if item.is_file():
            shutil.copy2(item, dest / item.name)
    (dest / "database").mkdir(parents=True, exist_ok=True)
    (dest / "database" / "templates").mkdir(parents=True, exist_ok=True)


def extract_mod_into(game: GamePaths, mod_root: Path, dest_db: Path) -> None:
    tool = ArchiveTool(game.game_dir)
    dest_db.mkdir(parents=True, exist_ok=True)
    arz_files = list(iter_arz_in_mod(mod_root))
    if not arz_files:
        src_db = mod_root / "database"
        if any(src_db.rglob("*.dbr")):
            for p in src_db.rglob("*"):
                if p.is_file() and p.suffix.lower() != ".arz":
                    rel = p.relative_to(src_db)
                    target = dest_db / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, target)
            return
        raise FileNotFoundError(f"No ARZ/DBR in {mod_root}")
    for arz in arz_files:
        print(f"Extracting {arz.name} from {mod_root.name} ...")
        tool.extract_database(arz, dest_db)


def run_combo_names(
    mod_db: Path,
    out_tags: Path,
    *,
    dry_run: bool,
    ollama_model: Optional[str],
    ollama_host: str,
) -> int:
    tags = collect_tags([mod_db, out_tags.parent])
    masteries = discover_mastery_ids(mod_db)
    missing = missing_berserker_combos(tags, masteries)
    print(f"Missing Berserker combos: {len(missing)}")
    if not missing:
        return 0
    if dry_run:
        generated = placeholder_names(missing)
    else:
        model = resolve_ollama_model(ollama_model)
        print(f"Ollama model: {model}")
        try:
            generated = ollama_generate(model, missing, ollama_host)
        except Exception as exc:
            print(f"Ollama failed ({exc}); placeholders", file=sys.stderr)
            generated = placeholder_names(missing)
    write_tags(out_tags, generated, tags)
    return len(generated)


def assemble_output_mod(
    game: GamePaths,
    primary: Path,
    work_db: Path,
    out_name: str,
) -> Path:
    out = game.mods_dir / out_name
    copy_mod_skeleton(primary, out)
    dest_db = out / "database"
    for p in work_db.rglob("*"):
        if not p.is_file() or p.suffix.lower() == ".arz":
            continue
        rel = p.relative_to(work_db)
        target = dest_db / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
    return out


def remap_all_quest_trees(roots: List[Path], prefix: str) -> tuple[List[str], List[str]]:
    all_moves: List[str] = []
    all_rewrites: List[str] = []
    for root in roots:
        if not root.exists():
            continue
        moves, rewrites = remap_tree(root, prefix, dry_run=False)
        all_moves.extend(moves)
        all_rewrites.extend(rewrites)
    return all_moves, all_rewrites


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Build Nydiamar + FoA unified Custom Game")
    p.add_argument("--game", default=None)
    p.add_argument("--profile", default=None, help="JSON profile (default profiles/nydiamar.json)")
    p.add_argument("--source", default=None, help="Nydiamar package folder override")
    p.add_argument("--out", default=None, help="Output Custom Game name under mods/")
    p.add_argument("--work", default=None)
    p.add_argument("--merge-dungeons", action="store_true", help="Overlay NydiamarDungeons (default on)")
    p.add_argument("--include-dungeons", action="store_true", help="Alias for --merge-dungeons")
    p.add_argument("--no-dungeons", action="store_true")
    p.add_argument("--quest-prefix", default=None)
    p.add_argument("--full-compat", action="store_true", default=True, help="Pass A+B (default)")
    p.add_argument("--no-compat", action="store_true", help="Skip FoA compat passes")
    p.add_argument("--remap-quests", action="store_true", default=True, help="Namespace quests (default)")
    p.add_argument("--skip-quest-remap", action="store_true")
    p.add_argument(
        "--prepare-editor-stitch",
        action="store_true",
        default=True,
        help="Unpack Maps/Quests ARCs + portal stubs + checklist (default)",
    )
    p.add_argument("--skip-editor-stitch", action="store_true")
    p.add_argument(
        "--portal-hub",
        default=None,
        help="devils_crossing|homestead|fort_ikon|malmouth|asterkarn",
    )
    p.add_argument("--skip-names", action="store_true")
    p.add_argument("--dry-run-names", action="store_true")
    p.add_argument("--ollama-model", default=None)
    p.add_argument("--ollama-host", default="http://127.0.0.1:11434")
    p.add_argument("--rebuild", action="store_true")
    p.add_argument("--arzedit", default=None)
    args = p.parse_args(argv)

    profile = load_profile(Path(args.profile) if args.profile else None)
    game = GamePaths(resolve_game_dir(args.game or profile.get("game_dir")))
    game.validate()

    source = args.source or profile.get("source") or str(DEFAULT_NYDIAMAR_SOURCE)
    out_name = args.out or profile.get("out_name") or "NydiamarIntegrated"
    quest_prefix = args.quest_prefix or profile.get("quest_prefix") or "nydiamar"
    hub_key = normalize_portal_hub(args.portal_hub or profile.get("portal_hub") or "devils_crossing")

    include_dungeons = profile.get("include_dungeons", True)
    if args.merge_dungeons or args.include_dungeons:
        include_dungeons = True
    if args.no_dungeons:
        include_dungeons = False

    do_compat = not args.no_compat
    do_remap = not args.skip_quest_remap
    do_stitch = not args.skip_editor_stitch

    work = Path(args.work) if args.work else (TOOLS_DIR / "work" / "nydiamar")
    work.mkdir(parents=True, exist_ok=True)

    roots = resolve_nydiamar_roots(game, source)
    primary = next((r for r in roots if r.name.lower() == "nydiamar"), roots[0])
    dungeons = next((r for r in roots if "dungeon" in r.name.lower()), None)
    print(f"Primary: {primary}")
    print(f"Portal hub: {hub_key}")
    if dungeons and include_dungeons:
        print(f"Dungeons: {dungeons}")
    elif not include_dungeons:
        print("Skipping NydiamarDungeons")

    kill_orphan_archivetool()
    extract_root = work / "database"
    if extract_root.exists():
        shutil.rmtree(extract_root)
    extract_root.mkdir(parents=True)

    extract_mod_into(game, primary, extract_root)
    if dungeons and include_dungeons:
        stage = work / "_dungeons_db"
        if stage.exists():
            shutil.rmtree(stage)
        extract_mod_into(game, dungeons, stage)
        added, field_merged, kept = merge_extracted_databases(stage, extract_root)
        print(
            f"Merged dungeons DBRs (added={added} field_merged={field_merged} "
            f"conflicts_kept_base={kept})"
        )

    if do_compat:
        cache = work / "_vanilla_cache"
        engine = CompatEngine(game, extract_root, cache)
        report = engine.full_compat()
        report_path = work / "compat_report.md"
        report.write(report_path)
        print(f"Compat report: {report_path} (imported={len(report.imported)})")
    else:
        print("Skipping FoA compat (--no-compat)")

    # Assemble early so stitch extract + remap can also hit source trees
    out_mod = assemble_output_mod(game, primary, extract_root, out_name)

    # Merge NydiamarDungeons resources (Maps/Quests/etc.) — accessed via portal, not campaign replace
    if dungeons and include_dungeons:
        copied = merge_mod_resources(dungeons, out_mod, game=game)
        print(
            f"Merged {len(copied)} dungeon resource ARCs from {dungeons.name} "
            f"(Maps/Quests content-merged for portal access)",
            flush=True,
        )

    extracted_arcs: List[str] = []
    stub_files: List[str] = []
    if do_stitch:
        tool = ArchiveTool(game.game_dir)
        extracted_arcs = extract_editor_arcs(tool, primary, out_mod)
        if dungeons and include_dungeons:
            # Unpack dungeon Maps/Quests into source/ as well (portal destinations)
            more = extract_editor_arcs(tool, dungeons, out_mod)
            for a in more:
                if a not in extracted_arcs:
                    extracted_arcs.append(f"{a} (dungeons)")
                else:
                    extracted_arcs.append(f"{a} (merged+dungeons)")
        stub_files = write_portal_stubs(out_mod, hub_key, quest_prefix)
        # Remap quests inside extracted Quests/Conversations/Scripts too
        if do_remap:
            source_roots = [
                out_mod / "source",
            ]
            smoves, srewrites = remap_all_quest_trees(source_roots, quest_prefix)
            print(f"Source quest remap: {len(smoves)} moves, {len(srewrites)} rewrites")

    if do_remap:
        moves, rewrites = remap_tree(extract_root, quest_prefix, dry_run=False)
        # Re-sync remapped DB into output
        for p in extract_root.rglob("*"):
            if not p.is_file() or p.suffix.lower() == ".arz":
                continue
            rel = p.relative_to(extract_root)
            target = out_mod / "database" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
        # Also remap the output database tree (portal stubs already namespaced)
        omoves, orewrites = remap_tree(out_mod / "database", quest_prefix, dry_run=False)
        moves = moves + omoves
        rewrites = rewrites + orewrites
        write_quest_report(work / "quest_remap_report.md", moves, rewrites)
        print(f"Quest remap: {len(moves)} moves, {len(rewrites)} rewrites")
    else:
        print("Skipping quest remap")

    if not args.skip_names:
        tag_out = out_mod / "localization" / "tags_nydiamar_foa.txt"
        text_en = out_mod / "source" / "text_en"
        n = run_combo_names(
            extract_root,
            tag_out,
            dry_run=args.dry_run_names or bool(profile.get("dry_run_names")),
            ollama_model=args.ollama_model or profile.get("ollama_model"),
            ollama_host=args.ollama_host,
        )
        shutil.copy2(tag_out, out_mod / "database" / "tags_nydiamar_foa.txt")
        if text_en.is_dir():
            shutil.copy2(tag_out, text_en / "tags_nydiamar_foa.txt")
        print(f"Combo tags written: {n}")

    if do_stitch:
        checklist = out_mod / "EDITOR_STITCH_CHECKLIST.md"
        write_editor_checklist(
            checklist,
            out_mod=out_mod,
            game_editor=game.editor,
            game_quest_editor=game.quest_editor,
            game_asset_manager=game.asset_manager,
            hub_key=hub_key,
            extracted_arcs=extracted_arcs,
            stub_files=stub_files,
            quest_prefix=quest_prefix,
        )
        # Copy static reference alongside
        static = TOOLS_DIR / "editor_stitch_checklist.md"
        if static.is_file():
            shutil.copy2(static, out_mod / "editor_stitch_checklist.md")
        print(f"Editor checklist: {checklist}")

    for name in ("compat_report.md", "quest_remap_report.md"):
        src = work / name
        if src.is_file():
            shutil.copy2(src, out_mod / name)

    if args.rebuild:
        ok, msg = build_database(out_mod, game.game_dir, resolve_arzedit(args.arzedit))
        print(msg if ok else f"Rebuild: {msg}")
    else:
        print(
            "Database left unpacked under database/. "
            "Build with AssetManager or pass --rebuild (arzedit)."
        )

    kill_orphan_archivetool()
    print(f"Done: {out_mod}")
    print("Load via Custom Game (same characters for FoA + Nydiamar after Editor stitch).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
