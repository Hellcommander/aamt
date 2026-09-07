#!/usr/bin/env python3
"""
Survival Mode power-level playground.

Keeps Survival Mode's maps/waves as the base Custom Game, then:
  1) Unlocks full base + AoM + FG + FoA (Berserker) class roster
  2) Merges **mod class lines** (custom masteries) from --class-mods / content mods
  3) Overlays **other mod content** (items, loot, creatures, UI tags, resource ARCs)
     so you can gear up and power-level for fun

Does not overwrite stock `survivalmode` by default — writes a new Custom Game folder.

Examples:
  python patch_survival_classes.py --out SurvivalPlayground --dry-run-names
  python patch_survival_classes.py --content-mods grimarillion --out SurvivalGrimarillion
  python patch_survival_classes.py --mods "Dawn of Masteries" grimarillion --out SurvivalKitchenSink
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Set, Tuple

from archive_tool import ArchiveTool, kill_orphan_archivetool
from arz_backend import build_database
from class_combo_names import (
    collect_tags,
    discover_mastery_ids,
    ollama_generate,
    placeholder_names,
    resolve_ollama_model,
    write_tags,
)
from compat_engine import CompatEngine
from dbr_io import get_list_field, merge_dbr_preserve_both, read_dbr, write_dbr
from gd_paths import (
    GamePaths,
    find_mod_roots,
    iter_arc_in_mod,
    resolve_arzedit,
    resolve_game_dir,
)
from merge_rules import (
    ModMergeRules,
    default_items_prefix,
    default_quest_prefix,
    filter_enabled_mods,
    find_rules_for_mod,
    load_all_rules,
    paired_sort_by_priority,
    rules_for_mod,
    should_field_merge_rel,
    should_skip_item_rel,
    should_skip_overlay_rel,
    sort_mods_by_priority,
)
from patch_mod_for_dlc import prepare_mod_database
from quest_remap import remap_tree, write_report as write_quest_report

TOOLS_DIR = Path(__file__).resolve().parent

# Resource ARCs useful for items/gear/UI when power-leveling (skip huge audio by default)
DEFAULT_CONTENT_ARCS = {
    "items.arc",
    "weapons.arc",
    "ui.arc",
    "text_en.arc",
    "fx.arc",
    "creatures.arc",
    "level art.arc",
    "shaders.arc",
    "textures.arc",
}

# Keep Survival/Crucible achievement + scoring hooks when overlaying other mods
PROTECTED_REL_PREFIXES = (
    "records/game/gameachievements.dbr",
    "records/ui/achievements/",
    "records/ui/survivalpane/",
)

# Portal-style campaign mods: merge gear/skills + *namespaced* quests; not world/maps
PORTAL_MOD_SKIP_PREFIXES = (
    "records/world/",
    "records/levels/",
    "records/storyelements/",
    "records/proxies/",
    "maps/",
)


def _is_protected_rel(rel_posix: str) -> bool:
    r = rel_posix.replace("\\", "/").lower()
    for prefix in PROTECTED_REL_PREFIXES:
        if r == prefix.lower() or r.startswith(prefix.lower()):
            return True
    if "/achievementlist/achievement_s" in r:
        return True
    return False


def _is_portal_skip_rel(rel_posix: str, quest_prefix: Optional[str] = None) -> bool:
    """
    Skip campaign-replacement paths. Allow records/quests/<quest_prefix>/ after remap.
    Un-namespaced records/quests/* are skipped so they cannot override vanilla.
    """
    r = rel_posix.replace("\\", "/").lower()
    if any(r.startswith(p) for p in PORTAL_MOD_SKIP_PREFIXES):
        return True
    if r.startswith("records/quests/"):
        if quest_prefix and r.startswith(f"records/quests/{quest_prefix.lower()}/"):
            return False
        return True
    if r.startswith("records/conversations/"):
        if quest_prefix and r.startswith(
            f"records/conversations/{quest_prefix.lower()}/"
        ):
            return False
        return True
    return False


def snapshot_protected(db: Path) -> dict:
    snapped = {}
    if not db.is_dir():
        return snapped
    for path in db.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(db).as_posix()
        if _is_protected_rel(rel):
            snapped[rel] = path.read_bytes()
    return snapped


def restore_protected(db: Path, snapped: dict) -> int:
    n = 0
    for rel, data in snapped.items():
        target = db.joinpath(*rel.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        n += 1
    return n


def overlay_database_tree(
    src_db: Path,
    dest_db: Path,
    *,
    skip_protected: bool = True,
    portal_content_only: bool = False,
    quest_prefix: Optional[str] = None,
    rules: Optional[ModMergeRules] = None,
) -> Tuple[int, int, int, int]:
    """
    Copy non-ARZ files from src onto dest (later wins).
    Applies per-mod rules (portal skips, items isolate/namespace, field conflict merge).
    Returns (copied, overwrites, skipped, field_merged).
    """
    copied = overwrites = skipped = field_merged = 0
    if not src_db.is_dir():
        return 0, 0, 0, 0
    items_mode = (rules.items_mode if rules else "merge") or "merge"
    items_prefix = (
        (rules.items_prefix if rules else None)
        or (default_items_prefix(rules.id) if rules else None)
    )

    for path in src_db.rglob("*"):
        if not path.is_file() or path.suffix.lower() == ".arz":
            continue
        rel = path.relative_to(src_db)
        rel_posix = rel.as_posix()
        if skip_protected and _is_protected_rel(rel_posix):
            skipped += 1
            continue
        if portal_content_only and _is_portal_skip_rel(rel_posix, quest_prefix):
            skipped += 1
            continue
        if should_skip_item_rel(rel_posix, rules):
            skipped += 1
            continue
        if should_skip_overlay_rel(rel_posix, rules):
            skipped += 1
            continue

        # Optional: namespace items under records/items/<prefix>/
        out_rel = rel_posix
        if (
            items_mode == "namespace"
            and items_prefix
            and rel_posix.replace("\\", "/").lower().startswith("records/items/")
        ):
            parts = rel_posix.replace("\\", "/").split("/")
            # records/items/... -> records/items/<prefix>/...
            if len(parts) >= 3 and parts[2].lower() != items_prefix.lower():
                out_rel = "/".join(parts[:2] + [items_prefix] + parts[2:])

        target = dest_db.joinpath(*out_rel.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        if (
            target.exists()
            and path.suffix.lower() == ".dbr"
            and should_field_merge_rel(rel_posix, rules)
        ):
            try:
                merged = merge_dbr_preserve_both(
                    read_dbr(target),
                    read_dbr(path),
                    prefer_overlay_substrings=(
                        rules.prefer_field_substrings if rules else None
                    ),
                    keep_base_substrings=(
                        rules.keep_base_field_substrings if rules else None
                    ),
                )
                write_dbr(target, merged)
                field_merged += 1
                overwrites += 1
                copied += 1
                continue
            except Exception:
                # Fall back to replace on parse errors
                pass
        if target.exists():
            overwrites += 1
        shutil.copy2(path, target)
        copied += 1
    return copied, overwrites, skipped, field_merged


def apply_quest_remap_for_rules(
    db_root: Path,
    rules: ModMergeRules,
    work: Path,
    mod_label: str,
) -> Tuple[str, int, int]:
    """Run quest_remap when rules.quest_remap is set. Returns (prefix, moves, rewrites)."""
    prefix = rules.quest_prefix or default_quest_prefix(mod_label)
    moves, rewrites = remap_tree(db_root, prefix, dry_run=False)
    report = work / f"quest_remap_{rules.id}_{mod_label}.md"
    write_quest_report(report, moves, rewrites)
    print(
        f"Quest remap [{rules.id}/{mod_label}] prefix={prefix}: "
        f"{len(moves)} moves, {len(rewrites)} rewrites -> {report}",
        flush=True,
    )
    return prefix, len(moves), len(rewrites)


def overlay_content_resources(
    game: GamePaths,
    content_mod: Path,
    out_mod: Path,
    work: Path,
    *,
    include_sounds: bool,
    arc_allow: Optional[Set[str]] = None,
    rules: Optional[ModMergeRules] = None,
) -> List[str]:
    """
    Unpack selected resource ARCs from a content mod and merge into out_mod resources.
    Later content wins on file conflicts.
    When rules.items_mode=isolate, skips Items.arc / Weapons.arc so loot stays in-mod-world.
    """
    tool = ArchiveTool(game.game_dir)
    done: List[str] = []
    allow = {a.lower() for a in (arc_allow or DEFAULT_CONTENT_ARCS)}
    if include_sounds:
        allow.update({"sounds.arc", "sound.arc", "music.arc"})
    if rules and rules.items_mode == "isolate":
        allow -= {"items.arc", "weapons.arc"}

    stage_root = work / "_content_arcs" / content_mod.name
    stage_root.mkdir(parents=True, exist_ok=True)
    source_merge = out_mod / "source" / "_content_merge"
    source_merge.mkdir(parents=True, exist_ok=True)

    for arc in iter_arc_in_mod(content_mod):
        if arc.name.lower() not in allow:
            continue
        print(f"  Content ARC {content_mod.name}/{arc.name} ...", flush=True)
        extract_to = stage_root / arc.stem
        if extract_to.exists():
            shutil.rmtree(extract_to)
        extract_to.mkdir(parents=True)
        try:
            tool.extract_arc(arc, extract_to)
        except Exception as exc:
            print(f"  WARN: extract failed {arc.name}: {exc}", file=sys.stderr)
            continue

        # Merge files into a per-arc source folder then pack into out resources
        dest_src = source_merge / arc.stem
        dest_src.mkdir(parents=True, exist_ok=True)
        for path in extract_to.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(extract_to)
            target = dest_src / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)

        dest_arc = (
            out_mod / "resources" / arc.name
            if arc.parent.name.lower() == "resources"
            else out_mod / "database" / arc.name
        )
        try:
            tool.update_arc(dest_arc, dest_src)
            done.append(f"{content_mod.name}/{arc.name}")
        except Exception as exc:
            print(f"  WARN: pack failed {arc.name}: {exc}", file=sys.stderr)
            # Fallback: copy ARC wholesale if out doesn't have it
            if not dest_arc.exists():
                dest_arc.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(arc, dest_arc)
                done.append(f"{content_mod.name}/{arc.name} (copied raw)")
    return done


def assemble_out(game: GamePaths, src_mod: Path, work_db: Path, out_name: str) -> Path:
    out = game.mods_dir / out_name
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src_mod, out, ignore=shutil.ignore_patterns("*.arz"))
    dest_db = out / "database"
    dest_db.mkdir(parents=True, exist_ok=True)
    for p in work_db.rglob("*"):
        if not p.is_file() or p.suffix.lower() == ".arz":
            continue
        rel = p.relative_to(work_db)
        target = dest_db / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
    return out


def resolve_mod_list(game: GamePaths, names: Sequence[str]) -> List[Path]:
    roots: List[Path] = []
    for name in names:
        found = find_mod_roots(game.mods_dir, name)
        if not found:
            print(f"WARN: mod not found: {name}", file=sys.stderr)
            continue
        roots.extend(found)
    return roots


def prepare_dbs(game: GamePaths, work: Path, mods: Sequence[Path]) -> List[Path]:
    dbs: List[Path] = []
    for root in mods:
        db = prepare_mod_database(game, root, work)
        dbs.append(db)
        print(f"DB ready: {root.name} -> {db}", flush=True)
    return dbs


def write_combo_tags(mod_db: Path, out_mod: Path, dry_run: bool, model: Optional[str]) -> int:
    """Fill ALL missing dual-class combo tags (not just Berserker), harvesting existing mod tags."""
    from class_combo_names import (
        collect_tags,
        discover_mastery_ids,
        harvest_tag_roots,
        missing_all_combos,
        ollama_generate,
        placeholder_names,
        resolve_ollama_model,
        write_tags,
    )

    tag_out = out_mod / "localization" / "tags_kitchen_sink_combos.txt"
    game_mods = out_mod.parent if out_mod.parent.name.lower() == "mods" else None
    roots = harvest_tag_roots(mod_db, out_mod, game_mods)
    # Keep legacy foa tags file in the harvest set
    roots.append(out_mod / "localization" / "tags_survival_foa.txt")
    tags = collect_tags(roots)
    masteries = discover_mastery_ids(mod_db)
    missing = missing_all_combos(tags, masteries)
    if not missing:
        print(
            f"No missing combo tags (masteries={len(masteries)}, existing={len(tags)}).",
            flush=True,
        )
        return 0
    print(
        f"Combo tags: masteries={len(masteries)} existing={len(tags)} missing={len(missing)}",
        flush=True,
    )
    generated = placeholder_names(missing)
    if not dry_run:
        # Polish a limited batch with Ollama; rest stay as CamelCase placeholders
        m = resolve_ollama_model(model)
        polish_n = min(80, len(missing))
        try:
            polished = ollama_generate(m, missing[:polish_n])
            generated.update(polished)
            print(f"Ollama polished {len(polished)} combo names", flush=True)
        except Exception as exc:
            print(f"Ollama failed ({exc}); placeholders only", file=sys.stderr)
    write_tags(tag_out, generated, tags)
    shutil.copy2(tag_out, out_mod / "database" / "tags_kitchen_sink_combos.txt")
    # Also keep/refresh legacy foa file with Berserker-related lines for older tooling
    legacy = out_mod / "localization" / "tags_survival_foa.txt"
    if not legacy.is_file():
        shutil.copy2(tag_out, legacy)
    return len(generated)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Survival Mode playground: full classes + mod class lines + items/content"
    )
    p.add_argument("--game", default=None)
    p.add_argument("--mod", default="survivalmode", help="Base mode (default survivalmode)")
    p.add_argument(
        "--class-mods",
        nargs="*",
        default=[],
        help="Mods that contribute custom class lines (masteries)",
    )
    p.add_argument(
        "--content-mods",
        nargs="*",
        default=[],
        help="Mods that contribute items and other content (DB + resource ARCs)",
    )
    p.add_argument(
        "--mods",
        nargs="*",
        default=[],
        help="Shorthand: treat as both class-mods and content-mods (kitchen-sink)",
    )
    p.add_argument(
        "--portal-mods",
        nargs="*",
        default=[],
        help=(
            "Campaign-style mods to pull as content-only (items/skills/affixes), "
            "skipping world/maps/quests so they stay portal destinations (e.g. ReignOfTerror)"
        ),
    )
    p.add_argument("--out", default="SurvivalPlayground")
    p.add_argument("--work", default=None)
    p.add_argument("--vanilla-cache", default=None)
    p.add_argument(
        "--profile",
        default=None,
        help="JSON profile (default: profiles/survivalmode.json if present and no mod lists given)",
    )
    p.add_argument(
        "--include-sounds",
        action="store_true",
        help="Also merge Sounds/Music ARCs from content mods (large)",
    )
    p.add_argument("--skip-resources", action="store_true", help="DB-only content overlay")
    p.add_argument("--skip-names", action="store_true")
    p.add_argument("--dry-run-names", action="store_true")
    p.add_argument("--ollama-model", default=None)
    p.add_argument("--rebuild", action="store_true")
    p.add_argument("--arzedit", default=None)
    args = p.parse_args(argv)

    profile_path: Optional[Path] = None
    if args.profile:
        profile_path = Path(args.profile)
        if not profile_path.is_file():
            profile_path = TOOLS_DIR / "profiles" / args.profile
    elif not (args.class_mods or args.content_mods or args.mods or args.portal_mods):
        default_prof = TOOLS_DIR / "profiles" / "survivalmode.json"
        if default_prof.is_file():
            profile_path = default_prof

    profile: dict = {}
    if profile_path and profile_path.is_file():
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        print(f"Profile: {profile_path}", flush=True)

    game = GamePaths(resolve_game_dir(args.game or profile.get("game_dir")))
    game.validate()
    base_mod = args.mod
    if profile.get("mod") and args.mod == "survivalmode":
        base_mod = str(profile["mod"])
    roots = find_mod_roots(game.mods_dir, base_mod)
    if not roots:
        print(f"Mod not found: {base_mod}", file=sys.stderr)
        return 1
    mod_root = roots[0]

    # CLI lists win when provided; otherwise use profile
    cli_lists = bool(args.class_mods or args.content_mods or args.mods or args.portal_mods)
    class_names = list(args.class_mods or ([] if cli_lists else profile.get("class_mods") or []))
    content_names = list(
        args.content_mods or ([] if cli_lists else profile.get("content_mods") or [])
    )
    portal_names = list(
        args.portal_mods or ([] if cli_lists else profile.get("portal_mods") or [])
    )
    if not cli_lists and profile.get("class_mods") is not None:
        class_names = list(profile.get("class_mods") or [])
        content_names = list(profile.get("content_mods") or [])
        portal_names = list(profile.get("portal_mods") or [])
    if profile.get("out_name") and args.out == "SurvivalPlayground":
        args.out = str(profile["out_name"])
    for name in args.mods or []:
        if name not in class_names:
            class_names.append(name)
        if name not in content_names and name not in portal_names:
            content_names.append(name)

    work = Path(args.work) if args.work else (TOOLS_DIR / "work" / "survival_playground")
    work.mkdir(parents=True, exist_ok=True)

    print(f"Base: {mod_root}", flush=True)
    print(f"Class mods: {class_names or '(none)'}", flush=True)
    print(f"Content mods: {content_names or '(none)'}", flush=True)
    print(f"Portal mods (content-only): {portal_names or '(none)'}", flush=True)

    db = prepare_mod_database(game, mod_root, work)
    protected = snapshot_protected(db)
    print(f"Protected Survival achievement/UI files: {len(protected)}", flush=True)

    if args.vanilla_cache:
        cache = Path(args.vanilla_cache)
    else:
        shared = TOOLS_DIR / "work" / "nydiamar" / "_vanilla_cache"
        cache = shared if shared.is_dir() else (work / "_vanilla_cache")

    class_mods = resolve_mod_list(game, class_names)
    content_mods = resolve_mod_list(game, content_names)
    portal_mods = resolve_mod_list(game, portal_names)
    all_rules = load_all_rules()

    class_mods, skip_c = filter_enabled_mods(class_mods, all_rules)
    content_mods, skip_o = filter_enabled_mods(content_mods, all_rules)
    portal_mods, skip_p = filter_enabled_mods(portal_mods, all_rules)
    for name in skip_c + skip_o + skip_p:
        print(f"SKIP (rules.enabled=false): {name}", flush=True)

    # Ascending priority — higher priority overlays last and wins conflicts
    content_mods = sort_mods_by_priority(content_mods, all_rules)
    portal_mods = sort_mods_by_priority(portal_mods, all_rules)
    class_mods = sort_mods_by_priority(class_mods, all_rules, class_aware=True)

    # Prepare DBs first, then overlay content+portal interleaved by priority
    content_dbs = prepare_dbs(game, work / "_content_mods", content_mods) if content_mods else []
    portal_dbs = prepare_dbs(game, work / "_portal_mods", portal_mods) if portal_mods else []
    class_dbs = prepare_dbs(game, work / "_class_mods", class_mods) if class_mods else []

    overlay_pairs = paired_sort_by_priority(
        content_mods + portal_mods,
        content_dbs + portal_dbs,
        all_rules,
    )
    print(
        "Merge order (low->high priority): "
        + (
            ", ".join(
                f"{m.name}[{rules_for_mod(m.name, all_rules).priority}]"
                for m, _ in overlay_pairs
            )
            or "(none)"
        ),
        flush=True,
    )

    portal_set = {str(p.resolve()) for p in portal_mods}
    for cm, cdb in overlay_pairs:
        rules = find_rules_for_mod(cm.name, all_rules)
        is_portal = str(cm.resolve()) in portal_set
        if is_portal:
            rules = rules or ModMergeRules(
                id=cm.name.lower(),
                mode="portal",
                quest_remap=True,
                quest_prefix=default_quest_prefix(cm.name),
                skip_world_maps=True,
                skip_unnamespaced_quests=True,
                items_mode="isolate",
                items_prefix=default_items_prefix(cm.name),
                priority=80,
            )
            qprefix = None
            if rules.quest_remap:
                qprefix, _, _ = apply_quest_remap_for_rules(cdb, rules, work, cm.name)
            copied, overwrites, skipped, field_merged = overlay_database_tree(
                cdb,
                db,
                skip_protected=True,
                portal_content_only=True,
                quest_prefix=qprefix or rules.quest_prefix,
                rules=rules,
            )
            print(
                f"Overlayed portal-mod DB {cm.name} "
                f"(rules={rules.id}, priority={rules.priority}, "
                f"quest_prefix={qprefix or rules.quest_prefix}, "
                f"items_mode={rules.items_mode}): "
                f"files={copied} overwrites={overwrites} skipped={skipped} "
                f"field_merged={field_merged}",
                flush=True,
            )
        else:
            copied, overwrites, skipped, field_merged = overlay_database_tree(
                cdb, db, skip_protected=True, rules=rules
            )
            imode = rules.items_mode if rules else "merge"
            pri = rules.priority if rules else 50
            print(
                f"Overlayed content DB {cm.name} (priority={pri}, items_mode={imode}): "
                f"files={copied} overwrites={overwrites} skipped={skipped} "
                f"field_merged={field_merged}",
                flush=True,
            )

    for cdb, cm in zip(class_dbs, class_mods):
        if cm in content_mods or cm in portal_mods:
            continue
        rules = find_rules_for_mod(cm.name, all_rules)
        copied, overwrites, skipped, field_merged = overlay_database_tree(
            cdb, db, skip_protected=True, rules=rules
        )
        print(
            f"Overlayed class-mod DB {cm.name} "
            f"(class_priority={rules.class_priority if rules else 50}): "
            f"files={copied} overwrites={overwrites} skipped={skipped} "
            f"field_merged={field_merged}",
            flush=True,
        )

    restored = restore_protected(db, protected)
    print(f"Restored protected Survival files: {restored}", flush=True)

    engine = CompatEngine(game, db, cache)
    engine.pass_a_patch_mod_for_dlc(full_classes=True)
    # Class DBs low→high class_priority so highest overwrites overlapping trees
    paired = paired_sort_by_priority(
        class_mods + content_mods + portal_mods,
        class_dbs + content_dbs + portal_dbs,
        all_rules,
        class_aware=True,
    )
    seen_db: set = set()
    extras = []
    for _mod, edb in paired:
        key = str(edb.resolve())
        if key in seen_db:
            continue
        seen_db.add(key)
        extras.append(edb)
    if extras:
        engine.unlock_full_classes(extra_class_dbs=extras)
    engine.pass_b_patch_dlc_for_mod()

    # Re-assert Survival achievement hooks after Pass B merges
    restored = restore_protected(db, protected)
    if restored:
        print(f"Re-restored protected Survival files after compat: {restored}", flush=True)

    report_path = work / f"{mod_root.name}_playground_report.md"
    engine.report.write(report_path)
    print(f"Report: {report_path}", flush=True)
    print(f"Class lines ({len(engine.report.class_lines)}):", flush=True)
    for line in engine.report.class_lines:
        print(f"  {line}", flush=True)

    out_mod = assemble_out(game, mod_root, db, args.out)
    shutil.copy2(report_path, out_mod / "compat_report.md")

    resource_notes: List[str] = []
    if (content_mods or portal_mods) and not args.skip_resources:
        print("Merging content-mod resources (items/UI/text)...", flush=True)
        for cm in content_mods:
            resource_notes.extend(
                overlay_content_resources(
                    game,
                    cm,
                    out_mod,
                    work,
                    include_sounds=args.include_sounds,
                    rules=find_rules_for_mod(cm.name, all_rules),
                )
            )
        # Portal mods: never pack Maps.arc / Level Art into Survival
        portal_arcs = set(DEFAULT_CONTENT_ARCS) - {"level art.arc"}
        for cm in portal_mods:
            prules = find_rules_for_mod(cm.name, all_rules) or ModMergeRules(
                id=cm.name.lower(), mode="portal", items_mode="isolate"
            )
            resource_notes.extend(
                overlay_content_resources(
                    game,
                    cm,
                    out_mod,
                    work,
                    include_sounds=False,
                    arc_allow=portal_arcs,
                    rules=prules,
                )
            )

    readme = out_mod / "README_PLAYGROUND.md"
    readme.write_text(
        "\n".join(
            [
                "# Survival Mode — power-level playground",
                "",
                "Survival maps/waves stay as the base. This pack adds:",
                "- Full base + AoM + FG + FoA (Berserker) classes",
                "- Mod **class lines** (custom masteries) when provided",
                "- Mod **items and other content** overlaid for gearing / fun power-leveling",
                "",
                "Load via **Custom Game** → this folder.",
                "Rebuild the database with Asset Manager (or `--rebuild` / arzedit) before play.",
                "",
                f"- Base: `{mod_root}`",
                f"- Class mods: {class_names or '(none)'}",
                f"- Content mods: {content_names or '(none)'}",
                f"- Portal mods (items/skills only, no campaign maps): {portal_names or '(none)'}",
                f"- Resource merges: {resource_notes or '(none / skipped)'}",
                "",
                "Survival achievement DBRs are preserved for Steam unlock best-effort.",
                "ReignOfTerror (portal-mod): world/maps/quests are NOT merged here —",
                "use a separate Editor portal stitch (like Nydiamar) to visit RoT while",
                "keeping base campaign / Survival maps.",
                "",
                "Stock `survivalmode` is left untouched.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    if not args.skip_names:
        n = write_combo_tags(db, out_mod, dry_run=args.dry_run_names, model=args.ollama_model)
        print(f"Combo tags written: {n}", flush=True)

    try:
        from patch_class_ui import patch_mod_database as patch_class_ui_db

        print(patch_class_ui_db(out_mod / "database", max_classes=120), flush=True)
    except Exception as exc:
        print(f"Class UI patch skipped/failed: {exc}", flush=True)

    if args.rebuild:
        ok, msg = build_database(out_mod, game.game_dir, resolve_arzedit(args.arzedit))
        print(msg if ok else f"Rebuild: {msg}", flush=True)
    else:
        print("Database left unpacked. Build with AssetManager or pass --rebuild.", flush=True)

    pc = out_mod / "database" / "records" / "creatures" / "pc" / "malepc01.dbr"
    if pc.is_file():
        trees = get_list_field(read_dbr(pc), "skillTree")
        print(f"Verify malepc01 skillTree count: {len(trees)}", flush=True)
    items = out_mod / "database" / "records" / "items"
    if items.is_dir():
        print(f"Item DBRs present under records/items: yes", flush=True)

    kill_orphan_archivetool()
    print(f"Done: {out_mod}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
