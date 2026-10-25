#!/usr/bin/env python3
"""
Merge multiple Grim Dawn mods into one Custom Game folder.

Adapted from Ian Chapman / LazyGuyWithRSI grim_dawn_mod_merger (MIT) --
extract ARZ/ARC via ArchiveTool, overlay files, rebuild with arzedit -- plus:

  * profiles/merge_rules/*.json: disabled mods dropped, priority order (higher wins),
    skip_overlay_prefixes, items_mode=isolate, per-mod field-merge preferences
  * field-level .dbr merging so overlapping records keep unique keys from both mods
    (--field-merge hubs|rules|all|none; class hubs always union their class lists)
  * --latest: patch the merged result for the newest game patch + DLC classes,
    expand class UI, and (re)name every dual-class combo (Ollama optional)

Examples:
  python merge_mod_databases.py --out MyMerge --mods grimarillion Rebirth --latest --ollama --rebuild
  python merge_mod_databases.py --out Quick --mods a b --keep-order --field-merge none
"""

from __future__ import annotations

import argparse
import filecmp
import json
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from archive_tool import ArchiveTool, arc_root, kill_orphan_archivetool, pack_arc
from arz_backend import build_database
from compat_engine import CLASS_LIST_PREFIXES, CLASS_SELECTION_SEMICOLON_KEYS
from dbr_io import merge_dbr_preserve_both, read_dbr, write_dbr
from gd_paths import (
    CLASS_HUB_RELATIVE,
    find_mod_roots,
    iter_arc_in_mod,
    iter_arz_in_mod,
    resolve_arzedit,
    resolve_game_dir,
    GamePaths,
)
from merge_rules import (
    ModMergeRules,
    filter_enabled_mods,
    load_all_rules,
    rules_for_mod,
    should_field_merge_rel,
    should_skip_item_rel,
    should_skip_overlay_rel,
    sort_mods_by_priority,
)

TOOLS_DIR = Path(__file__).resolve().parent
HUBS = {h.lower() for h in CLASS_HUB_RELATIVE}
# Mastery trees: overlaps go to the higher class_priority mod, not the higher priority one
CLASS_PATH_PREFIXES = ("records/skills/playerclass", "records/ui/skills/class")
FIELD_MODES = ("none", "hubs", "rules", "all")

# (path, winner, overwrote, how) -- how: replace | field | hub-union | arc
Conflict = Tuple[str, str, str, str]


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def overlay_tree(
    src: Path,
    dest: Path,
    conflicts: List[Conflict],
    winner_label: str,
    owners: Dict[str, str],
    skip_ext: Tuple[str, ...] = (".arz", ".arc"),
    skip_db_records: bool = False,
    key_prefix: str = "",
) -> None:
    """Plain later-wins copy (loose mod files, unpacked resources)."""
    if not src.exists():
        return
    for item in src.rglob("*"):
        if item.is_dir() or item.suffix.lower() in skip_ext:
            continue
        rel = item.relative_to(src)
        if skip_db_records and rel.parts[0].lower() == "database" and item.suffix.lower() == ".dbr":
            continue  # merged record-by-record via overlay_records
        target = dest / rel
        key = key_prefix + _rel(target, dest).lower()
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if filecmp.cmp(item, target, shallow=False):
                continue
            conflicts.append((_rel(target, dest), winner_label, owners.get(key, "?"), "replace"))
        shutil.copy2(item, target)
        owners[key] = winner_label


def overlay_records(
    src_db: Path,
    dest_db: Path,
    label: str,
    rules: ModMergeRules,
    field_mode: str,
    conflicts: List[Conflict],
    owners: Dict[str, str],
    stats: Counter,
    rules_by_label: Optional[Dict[str, ModMergeRules]] = None,
) -> None:
    """Overlay one mod's extracted records onto the merged database with per-file policy."""
    rules_by_label = rules_by_label or {}
    for path in src_db.rglob("*"):
        if not path.is_file() or path.suffix.lower() == ".arz":
            continue
        rel = path.relative_to(src_db).as_posix()
        rel_l = rel.lower()
        if should_skip_overlay_rel(rel, rules) or should_skip_item_rel(rel, rules):
            stats["skipped by rules"] += 1
            continue
        target = dest_db.joinpath(*rel.split("/"))
        key = "database/" + rel_l
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            owners[key] = label
            stats["added"] += 1
            continue
        if filecmp.cmp(path, target, shallow=False):
            stats["identical"] += 1
            continue
        owner = rules_by_label.get(owners.get(key, ""))
        if (
            owner
            and rel_l.startswith(CLASS_PATH_PREFIXES)
            and rel_l not in HUBS
            and rules.class_priority < owner.class_priority
        ):
            stats["kept (higher class_priority)"] += 1
            continue

        how = "replace"
        if path.suffix.lower() == ".dbr":
            is_hub = rel_l in HUBS
            if is_hub and field_mode != "none":
                how = "hub-union"
            elif field_mode == "all" or (
                field_mode in ("rules", "all") and should_field_merge_rel(rel, rules)
            ):
                how = "field"
        if how != "replace":
            try:
                merged = merge_dbr_preserve_both(
                    read_dbr(target),
                    read_dbr(path),
                    prefer_overlay_substrings=rules.prefer_field_substrings,
                    keep_base_substrings=rules.keep_base_field_substrings,
                    list_prefixes=CLASS_LIST_PREFIXES if how == "hub-union" else None,
                    semicolon_keys=(
                        CLASS_SELECTION_SEMICOLON_KEYS if "classselection" in rel_l else None
                    ),
                )
                write_dbr(target, merged)
            except Exception:
                how = "replace"  # unparseable record: fall back to whole-file replace
        if how == "replace":
            shutil.copy2(path, target)
        conflicts.append(("database/" + rel, label, owners.get(key, "?"), how))
        owners[key] = label
        stats[how] += 1


def compat_for_merge(game: GamePaths, mod: Path, rules: ModMergeRules) -> Tuple[Path, str]:
    """
    Per-mod latest-patch compat for --latest merges: only mods detected as out of date (or
    rule compat=force) are patched. Results are cached in work/_merge_cache_latest and redone
    when the mod's .arz or any game layer changes.
    """
    from compat_engine import CompatEngine
    from gd_paths import file_stamp
    from patch_mod_for_dlc import apply_compat, prepare_mod_database

    cache = TOOLS_DIR / "work" / "_merge_cache_latest"
    vstamp = file_stamp(game.layer_arz_files())
    db = prepare_mod_database(game, mod, cache)
    marker = db.parent / ".compat_state.json"
    try:
        state = json.loads(marker.read_text(encoding="utf-8"))
    except Exception:
        state = {}
    if state.get("game") == vstamp and state.get("mode") == rules.compat:
        return db, state.get("result", "cached")
    if state.get("result", "").startswith("patched"):
        db = prepare_mod_database(game, mod, cache, fresh=True)  # game changed: patch a clean copy
    engine = CompatEngine(game, db, TOOLS_DIR / "work" / "_vanilla_cache")
    ran, reasons = apply_compat(engine, rules.compat, full_classes=True)
    result = f"patched for latest game ({'; '.join(reasons)[:300]})" if ran else f"compat not needed ({reasons[0]})"
    engine.report.write(db.parent / "compat_report.md")
    marker.write_text(json.dumps({"game": vstamp, "mode": rules.compat, "result": result}), encoding="utf-8")
    print(f"  {mod.name}: {result}", flush=True)
    return db, result


def order_mods(
    mod_roots: List[Path], *, use_rules: bool, include_disabled: bool
) -> Tuple[List[Path], List[str]]:
    if not use_rules:
        return list(mod_roots), []
    all_rules = load_all_rules()
    kept, skipped = (list(mod_roots), []) if include_disabled else filter_enabled_mods(mod_roots, all_rules)
    return sort_mods_by_priority(kept, all_rules), skipped


def write_report(
    out_dir: Path,
    mods: List[Path],
    skipped_mods: List[str],
    conflicts: List[Conflict],
    stats: Counter,
    field_mode: str,
    notes: List[str],
) -> Path:
    report = out_dir / "merge_report.md"
    pairs = Counter((loser, winner, how) for _, winner, loser, how in conflicts)
    lines = [
        "# Merge report",
        "",
        f"Order (low -> high priority, later wins): {', '.join(m.name for m in mods)}",
        f"Disabled by merge rules: {', '.join(skipped_mods) or '(none)'}",
        f"Field merge mode: {field_mode}",
        "",
        "## Records",
        *(f"- {k}: {v}" for k, v in sorted(stats.items())),
        "",
        "## Overlaps by mod pair",
        "| overwritten | winner | how | files |",
        "|---|---|---|---|",
        *(f"| {lo} | {wi} | {how} | {n} |" for (lo, wi, how), n in pairs.most_common()),
        "",
        "## Post-merge",
        *(f"- {n}" for n in notes or ["(none)"]),
        "",
        "Full list: merge_conflicts.txt",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with (out_dir / "merge_conflicts.txt").open("w", encoding="utf-8") as fh:
        fh.write("path\twinner\toverwrote\thow\n")
        for path, winner, loser, how in conflicts:
            fh.write(f"{path}\t{winner}\t{loser}\t{how}\n")
    return report


def merge_mods(
    game: GamePaths,
    mod_roots: List[Path],
    out_name: str,
    arzedit: Optional[Path],
    rebuild: bool,
    *,
    use_rules: bool = True,
    include_disabled: bool = False,
    field_mode: str = "rules",
    skip_resources: bool = False,
    latest: bool = False,
    class_ui: bool = False,
    combo_names: bool = False,
    use_ollama: bool = False,
    ollama_model: Optional[str] = None,
    ollama_limit: int = -1,
    max_classes: int = 120,
    patch_dirs: Optional[List[Path]] = None,
) -> Path:
    from patch_mod_for_dlc import combo_source, finish_mod, prepare_mod_database

    kill_orphan_archivetool()
    tool = ArchiveTool(game.game_dir)
    out_dir = game.mods_dir / out_name
    if any(out_dir.resolve() == m.resolve() for m in mod_roots):
        raise SystemExit(f"--out {out_name} is one of the input mods")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    for sub in ("database/templates", "resources", "source"):
        (out_dir / sub).mkdir(parents=True)

    mods, skipped_mods = order_mods(mod_roots, use_rules=use_rules, include_disabled=include_disabled)
    if skipped_mods:
        print(f"Disabled by merge rules (use --include-disabled to keep): {skipped_mods}")
    print(f"Merge order (later wins): {[m.name for m in mods]}", flush=True)

    # Extracts are cached between runs and refreshed when a mod's .arz changes
    cache = TOOLS_DIR / "work" / "_merge_cache"
    stage = out_dir / "_merge_work"
    stage.mkdir(parents=True)
    conflicts: List[Conflict] = []
    owners: Dict[str, str] = {}
    stats: Counter = Counter()
    all_rules = load_all_rules() if use_rules else []
    rules_by_label: Dict[str, ModMergeRules] = {}
    pending_arcs: Dict[Path, Path] = {}
    mod_dbs: Dict[str, Path] = {}
    notes: List[str] = []
    sources = []

    for mod in mods:
        label = mod.name
        rules = rules_for_mod(label, all_rules)
        if use_rules:
            rules_by_label[label] = rules
        print(f"Merging: {mod}  (priority {rules.priority}, field merge: {field_mode})", flush=True)
        # Loose files (readme, loose text, templates); records and ARCs handled below
        overlay_tree(mod, out_dir, conflicts, label, owners, skip_db_records=True)

        if any(iter_arz_in_mod(mod)) or next((mod / "database").rglob("*.dbr"), None):
            if latest:
                db, state = compat_for_merge(game, mod, rules)
                notes.append(f"{label}: {state}")
            else:
                db = prepare_mod_database(game, mod, cache)
            mod_dbs[label] = db
            overlay_records(
                db, out_dir / "database", label, rules, field_mode, conflicts, owners, stats, rules_by_label
            )
            if combo_names or latest:
                sources.append(combo_source(game, mod, db, cache))

        if skip_resources:
            continue
        for arc in iter_arc_in_mod(mod):
            if rules.items_mode == "isolate" and arc.name.lower() in ("items.arc", "weapons.arc"):
                stats["arc skipped by rules"] += 1
                continue
            print(f"  Extract ARC {arc.name}", flush=True)
            extract_to = out_dir / "source" / arc.stem
            tmp = stage / f"{label}_{arc.stem}"
            tool.extract_arc(arc, tmp)
            overlay_tree(  # from the archive's top level, not ArchiveTool's nested <stem> folder
                arc_root(tmp, arc), extract_to, conflicts, f"{label}:{arc.name}", owners,
                skip_ext=(), key_prefix=f"arc:{arc.stem.lower()}/",
            )
            shutil.rmtree(tmp, ignore_errors=True)
            dest_arc = (
                out_dir / "resources" / arc.name
                if arc.parent.name.lower() == "resources"
                else out_dir / "database" / arc.name
            )
            pending_arcs[dest_arc] = extract_to
    shutil.rmtree(stage, ignore_errors=True)

    # Pack each merged archive once, after every mod has overlaid its files
    for dest_arc, folder in pending_arcs.items():
        print(f"Packing {dest_arc.name} ...", flush=True)
        try:
            if dest_arc.exists():
                dest_arc.unlink()
            pack_arc(folder, dest_arc)
        except Exception as exc:
            print(f"  WARN: could not pack {dest_arc.name}: {exc}")

    if latest:
        from compat_engine import CompatEngine

        # Out-of-date mods were already patched one by one; just make sure the merged roster
        # carries every official class (e.g. when no input mod had the newest one).
        engine = CompatEngine(game, out_dir / "database", TOOLS_DIR / "work" / "_vanilla_cache")
        if engine.ensure_official_classes():
            notes.append("Added missing official classes to the merged roster")
        engine.report.write(out_dir / "compat_report.md")
    # Always: uTXTp patches + extra templates; class UI / names / labels with --latest
    notes.extend(
        finish_mod(
            game,
            out_dir,
            class_ui=latest or class_ui,
            max_classes=max_classes,
            combo_names=latest or combo_names,
            use_ollama=use_ollama,
            ollama_model=ollama_model,
            ollama_limit=ollama_limit,
            sources=sources,
            skill_labels=latest,
            patch_dirs=patch_dirs,
            mod_dbs=mod_dbs,
            rebuild=rebuild,
            arzedit=str(arzedit) if arzedit else None,
        )
    )
    if not rebuild:
        print("Skipping ARZ rebuild. Use AssetManager or pass --rebuild.")

    report = write_report(out_dir, mods, skipped_mods, conflicts, stats, field_mode, notes)
    print(f"Merge report: {report}  ({len(conflicts)} overlaps; {dict(stats)})")
    kill_orphan_archivetool()
    return out_dir


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Merge Grim Dawn mod databases")
    parser.add_argument("--game", default=None, help="Grim Dawn install directory")
    parser.add_argument("--out", required=True, help="Output mod folder name under mods/")
    parser.add_argument(
        "--mods",
        nargs="+",
        required=True,
        help="Mod folder names or paths (merge-rule priority decides order; see --keep-order)",
    )
    parser.add_argument("--keep-order", action="store_true", help="Ignore merge rules; later on the command line wins")
    parser.add_argument("--include-disabled", action="store_true", help="Merge mods whose rule says enabled:false")
    parser.add_argument(
        "--field-merge",
        choices=FIELD_MODES,
        default="rules",
        help="none: whole-file replace; hubs: only class hubs union; "
        "rules: hubs + paths a mod's rule marks conflict_merge (default); all: every overlapping .dbr",
    )
    parser.add_argument("--skip-resources", action="store_true", help="Database only (skip .arc merging)")
    parser.add_argument("--latest", action="store_true", help="Patch result for latest game/DLC + class UI + combo names")
    parser.add_argument("--class-ui", action="store_true")
    parser.add_argument("--combo-names", action="store_true")
    parser.add_argument("--max-classes", type=int, default=120)
    parser.add_argument("--ollama", action="store_true", help="Name new combos with local Ollama")
    parser.add_argument("--ollama-model", default=None)
    parser.add_argument("--ollama-limit", type=int, default=-1)
    parser.add_argument("--patches", nargs="*", default=None, help="uTXTp files/folders (default patches/ + GD-DPS User Text Patch)")
    parser.add_argument("--no-patches", action="store_true")
    parser.add_argument("--arzedit", default=None, help="Path to arzedit.exe")
    parser.add_argument("--rebuild", action="store_true", help="Build the .arz with arzedit after merge")
    parser.add_argument("--no-rebuild", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    game = GamePaths(resolve_game_dir(args.game))
    game.validate()

    roots: List[Path] = []
    for name in args.mods:
        found = find_mod_roots(game.mods_dir, name)
        if not found:
            print(f"ERROR: mod not found: {name}", file=sys.stderr)
            return 1
        roots.extend(found)

    out = merge_mods(
        game,
        roots,
        args.out,
        resolve_arzedit(args.arzedit),
        bool(args.rebuild) and not args.no_rebuild,
        use_rules=not args.keep_order,
        include_disabled=args.include_disabled,
        field_mode=args.field_merge,
        skip_resources=args.skip_resources,
        latest=args.latest,
        class_ui=args.class_ui,
        combo_names=args.combo_names,
        use_ollama=args.ollama,
        ollama_model=args.ollama_model,
        ollama_limit=args.ollama_limit,
        max_classes=args.max_classes,
        patch_dirs=[] if args.no_patches else ([Path(x) for x in args.patches] if args.patches is not None else None),
    )
    print(f"Done: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
