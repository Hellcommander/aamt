#!/usr/bin/env python3
"""Pass A: patch a mod so it works with the latest Grim Dawn patch + expansions.

`--latest` is the one-shot updater: FoA/v1.3+ compat (Pass A + B), every official
class (Berserker and any future gdxN class) on the class hubs, class-selection UI
expanded to fit, dual-class combo names (Ollama optional) injected into Text_EN.arc,
and optionally a rebuilt .arz. Output goes to a new Custom Game folder by default
so the original mod is untouched.

Examples:
  python patch_mod_for_dlc.py --mod grimarillion --latest --ollama
  python patch_mod_for_dlc.py --mod dom --latest --out dom_Latest --rebuild
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from archive_tool import ArchiveTool, kill_orphan_archivetool
from arz_backend import build_database
from compat_engine import CompatEngine
from dbr_io import get_list_field, read_dbr
from gd_paths import (
    GamePaths,
    file_stamp,
    find_mod_roots,
    iter_arz_in_mod,
    resolve_arzedit,
    resolve_game_dir,
)

COMBO_TAG_FILE = "tags_mod_combos.txt"


def prepare_mod_database(
    game: GamePaths, mod_root: Path, work: Path, *, fresh: bool = False
) -> Path:
    """Extract mod ARZ into work/<mod>/database; re-extract when the mod's .arz changed."""
    db = mod_root / "database"
    extract_root = work / mod_root.name
    records = extract_root / "database"
    stamp_file = extract_root / ".source_stamp"
    arz_files = list(iter_arz_in_mod(mod_root))
    stamp = file_stamp(arz_files)
    # Unpacked-only mods (e.g. earlier tool output) are re-copied every run: no cheap stamp
    if (
        not fresh
        and arz_files
        and records.exists()
        and stamp_file.is_file()
        and stamp_file.read_text(encoding="utf-8") == stamp
        and next(records.rglob("*.dbr"), None)
    ):
        return records
    if records.exists() and arz_files:
        print(f"{mod_root.name}: mod archive changed (or --fresh); re-extracting", flush=True)

    kill_orphan_archivetool()
    tool = ArchiveTool(game.game_dir)
    if extract_root.exists():
        shutil.rmtree(extract_root)
    records.mkdir(parents=True)
    if not arz_files:
        # Already unpacked?
        if (db / "records").is_dir() or next(db.rglob("*.dbr"), None):
            shutil.copytree(db, records, dirs_exist_ok=True)
            _save_original_roster(records)
            return records
        raise FileNotFoundError(f"No .arz or unpacked DBRs in {mod_root}")

    for arz in arz_files:
        print(f"Extracting {arz} ...", flush=True)
        tool.extract_database(arz, records)
    stamp_file.write_text(stamp, encoding="utf-8")
    _save_original_roster(records)
    return records


def _save_original_roster(records: Path) -> None:
    pc = records / "records/creatures/pc/malepc01.dbr"
    if pc.is_file():
        trees = get_list_field(read_dbr(pc), "skillTree")
        (records.parent / ".original_roster.json").write_text(json.dumps(trees), encoding="utf-8")


def original_roster(records: Path) -> Optional[List[str]]:
    """Class order the mod shipped with (its own combo tags are numbered against it)."""
    try:
        return json.loads((records.parent / ".original_roster.json").read_text(encoding="utf-8"))
    except Exception:
        return None


def combo_source(game: GamePaths, mod_root: Path, records: Path, work: Path):
    from class_combo_names import ComboSource, mod_text_roots

    return ComboSource(
        mod_root.name,
        records,
        mod_text_roots(game.game_dir, mod_root, work),
        original_roster(records),
    )


def copy_records(db: Path, dest_db: Path) -> None:
    dest_db.mkdir(parents=True, exist_ok=True)
    for p in db.rglob("*"):
        if not p.is_file() or p.suffix.lower() == ".arz":
            continue
        target = dest_db / p.relative_to(db)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)


def extra_template_dirs(game: GamePaths) -> List[Path]:
    """Template packs dropped in mods/ (e.g. the Templates zip Dawn of Masteries links)."""
    out = []
    for d in sorted(game.mods_dir.iterdir()) if game.mods_dir.is_dir() else []:
        t = d / "templates"
        if d.is_dir() and t.is_dir() and next(t.rglob("*.tpl"), None):
            out.append(t)
    return out


def install_extra_templates(game: GamePaths, db: Path) -> int:
    """Copy missing extra .tpl files into <mod>/database/templates (arzedit + Asset Manager read it)."""
    n = 0
    dest_root = db / "templates"
    for tdir in extra_template_dirs(game):
        for tpl in tdir.rglob("*.tpl"):
            dest = dest_root / tpl.relative_to(tdir)
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(tpl, dest)
                n += 1
    return n


def apply_compat(engine: CompatEngine, mode: str, *, full_classes: bool, extras=None) -> Tuple[bool, List[str]]:
    """Run Pass A+B only when needed: mode auto (detect) | force | skip. Returns (ran, reasons)."""
    if mode == "skip":
        return False, ["compat=skip"]
    reasons: List[str] = ["compat=force"]
    if mode == "auto":
        stale, reasons = engine.needs_update()
        if not stale and not extras:
            print("Mod is already up to date with the installed game/DLC; compat skipped.", flush=True)
            engine.report.notes.append("Up to date with installed game; compat skipped")
            return False, ["up to date"]
    for r in reasons:
        print(f"  out of date: {r}", flush=True)
    engine.full_compat(full_classes=full_classes or bool(extras), extra_class_dbs=extras or None)
    engine.report.notes.extend(f"Compat reason: {r}" for r in reasons)
    return True, reasons


def finish_mod(
    game: GamePaths,
    out_root: Path,
    *,
    class_ui: bool = True,
    max_classes: int = 120,
    combo_names: bool = True,
    use_ollama: bool = False,
    ollama_model: Optional[str] = None,
    ollama_host: str = "http://127.0.0.1:11434",
    ollama_limit: int = -1,
    text_mods: Sequence[Path] = (),
    sources: Sequence = (),
    skill_labels: bool = True,
    inject_text: bool = True,
    patch_dirs: Optional[Sequence[Path]] = None,
    mod_dbs: Optional[dict] = None,
    rebuild: bool = False,
    arzedit: Optional[str] = None,
) -> List[str]:
    """
    Class UI -> combo names + skill class labels (-> Text_EN.arc) -> uTXTp patches ->
    extra templates -> optional .arz build, on an unpacked mod.
    """
    notes: List[str] = []
    db = out_root / "database"
    text_files: List[Path] = []
    if class_ui:
        from patch_class_ui import patch_mod_database as patch_class_ui_db

        try:
            msg = patch_class_ui_db(db, max_classes=max_classes)
            print(msg, flush=True)
            notes.append(msg.splitlines()[1].strip() if "\n" in msg else msg)
        except Exception as exc:
            notes.append(f"Class UI patch skipped: {exc}")
            print(f"WARN: class UI patch: {exc}", file=sys.stderr)

    if combo_names:
        from class_combo_names import generate_combo_tags

        tag_file = out_root / "localization" / COMBO_TAG_FILE
        n, masteries = generate_combo_tags(
            db,
            tag_file,
            game_dir=game.game_dir,
            text_mods=text_mods,
            sources=sources,
            use_ollama=use_ollama,
            model=ollama_model,
            host=ollama_host,
            limit=ollama_limit,
        )
        notes.append(f"Combo names: {n} generated for {len(masteries)} masteries")
        if n:
            text_files.append(tag_file)

    if skill_labels:
        from skill_class_tags import LABEL_FILE, generate_build_labels

        label_file = out_root / "localization" / LABEL_FILE
        try:
            n = generate_build_labels(db, label_file, game_dir=game.game_dir)
            notes.append(f"Skill class labels: {n} skills")
            if n:
                text_files.append(label_file)
        except Exception as exc:
            notes.append(f"Skill class labels skipped: {exc}")
            print(f"WARN: skill class labels: {exc}", file=sys.stderr)

    if inject_text and text_files:
        from fill_combo_tags import inject_tags_into_text_arc

        msg = inject_tags_into_text_arc(game, out_root, text_files, create=True)
        print(msg, flush=True)
        notes.append(msg)

    # Declarative uTXTp patches (GD-DPS format) re-applied on every build
    from utxtp import apply_patches, default_patch_dirs, load_patches

    dirs = list(patch_dirs) if patch_dirs is not None else default_patch_dirs(game.game_dir)
    patches = load_patches(dirs) if dirs else []
    if patches:
        rep = apply_patches(db, patches, mod_dbs=mod_dbs)
        print(rep.summary(), flush=True)
        for line in rep.errors:
            print(f"  ERROR {line}", file=sys.stderr)
        notes.append(f"{rep.summary()} from {[d.name for d in dirs]}")

    n_tpl = install_extra_templates(game, db)
    if n_tpl:
        notes.append(f"Extra templates installed: {n_tpl}")

    if rebuild:
        ok, msg = build_database(out_root, game.game_dir, resolve_arzedit(arzedit))
        print(msg if ok else f"Rebuild: {msg}", flush=True)
        notes.append("ARZ rebuilt" if ok else f"ARZ rebuild failed: {msg[:200]}")
    return notes


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Patch a mod for the latest Grim Dawn patch + DLC")
    p.add_argument("--game", default=None)
    p.add_argument("--mod", required=True, help="Mod name or path under mods/")
    p.add_argument("--work", default=None, help="Working directory for extracts")
    p.add_argument(
        "--out",
        default=None,
        help="Output Custom Game name under mods/ (default with --latest: <mod>_Latest)",
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
    p.add_argument(
        "--latest",
        action="store_true",
        help="One-shot: full compat + all classes + class UI + combo names (+ --rebuild)",
    )
    p.add_argument("--class-ui", action="store_true", help="Expand class selection UI")
    p.add_argument("--max-classes", type=int, default=120)
    p.add_argument("--combo-names", action="store_true", help="Generate dual-class combo names")
    p.add_argument("--ollama", action="store_true", help="Name combos with a local Ollama model")
    p.add_argument("--ollama-model", default=None)
    p.add_argument("--ollama-host", default="http://127.0.0.1:11434")
    p.add_argument("--ollama-limit", type=int, default=-1, help="Max uncached pairs to name (-1=all)")
    p.add_argument(
        "--compat",
        choices=("auto", "force", "skip"),
        default="auto",
        help="auto: patch only if the mod is behind the installed game (rule 'compat' can override)",
    )
    p.add_argument("--patches", nargs="*", default=None, help="uTXTp files/folders (default patches/ + GD-DPS User Text Patch)")
    p.add_argument("--no-patches", action="store_true")
    p.add_argument("--no-skill-labels", action="store_true", help="Skip SkillClassTags-style labels")
    p.add_argument("--in-place", action="store_true", help="Write into the mod itself (backs up .arz)")
    p.add_argument("--fresh", action="store_true", help="Re-extract the mod even if cached")
    p.add_argument("--rebuild", action="store_true")
    p.add_argument("--arzedit", default=None)
    args = p.parse_args(argv)

    if args.latest:
        args.full_compat = args.full_classes = args.class_ui = args.combo_names = True

    game = GamePaths(resolve_game_dir(args.game))
    game.validate()
    roots = find_mod_roots(game.mods_dir, args.mod)
    if not roots:
        print(f"Mod not found: {args.mod}", file=sys.stderr)
        return 1
    mod_root = roots[0]
    work = Path(args.work) if args.work else (Path(__file__).resolve().parent / "work")
    work.mkdir(parents=True, exist_ok=True)

    db = prepare_mod_database(game, mod_root, work, fresh=args.fresh)
    cache = work / "_vanilla_cache"
    engine = CompatEngine(game, db, cache)
    print(f"DLC layers: {', '.join(game.dlc_layer_names()) or '(none)'}", flush=True)

    extras = []
    text_mods: List[Path] = []
    sources = []
    for name in args.class_mods or []:
        for fr in find_mod_roots(game.mods_dir, name):
            extra_db = prepare_mod_database(game, fr, work / "_class_mods")
            extras.append(extra_db)
            text_mods.append(fr)
            if args.combo_names:
                sources.append(combo_source(game, fr, extra_db, work))
    if args.combo_names:
        sources.append(combo_source(game, mod_root, db, work))  # the mod itself wins

    if args.full_compat:
        mode = args.compat
        if mode == "auto":
            from merge_rules import find_rules_for_mod

            rule = find_rules_for_mod(mod_root.name)
            mode = rule.compat if rule else "auto"
            if mode != "auto":
                print(f"Merge rule '{rule.id}' sets compat={mode}", flush=True)
        apply_compat(engine, mode, full_classes=args.full_classes, extras=extras)
        report = engine.report
    else:
        report = engine.pass_a_patch_mod_for_dlc(
            full_classes=args.full_classes or bool(extras)
        )
        if extras:
            engine.unlock_full_classes(extra_class_dbs=extras)
            report = engine.report

    out_root = mod_root
    if args.out is None and args.latest and not args.in_place:
        args.out = f"{mod_root.name}_Latest"
    if args.out:
        out_root = game.mods_dir / args.out
        if out_root.resolve() == mod_root.resolve():
            print("--out must differ from the source mod (use --in-place)", file=sys.stderr)
            return 1
        if out_root.exists():
            shutil.rmtree(out_root)
        shutil.copytree(mod_root, out_root, ignore=shutil.ignore_patterns("*.arz"))
        copy_records(db, out_root / "database")
        print(f"Output Custom Game: {out_root}")
    elif args.class_ui or args.combo_names or args.rebuild:
        # In-place: keep a backup of the packed DB, then unpack the patched records next to it
        for arz in iter_arz_in_mod(mod_root):
            bak = arz.with_suffix(".arz.bak_latest")
            if not bak.exists():
                shutil.copy2(arz, bak)
        copy_records(db, mod_root / "database")

    if args.class_ui or args.combo_names or args.rebuild:
        notes = finish_mod(
            game,
            out_root,
            class_ui=args.class_ui,
            max_classes=args.max_classes,
            combo_names=args.combo_names,
            use_ollama=args.ollama,
            ollama_model=args.ollama_model,
            ollama_host=args.ollama_host,
            ollama_limit=args.ollama_limit,
            text_mods=text_mods,
            sources=sources,
            skill_labels=args.latest and not args.no_skill_labels,
            patch_dirs=[] if args.no_patches else ([Path(x) for x in args.patches] if args.patches is not None else None),
            mod_dbs={mod_root.name: db},
            rebuild=args.rebuild,
            arzedit=args.arzedit,
        )
        report.notes.extend(notes)

    report_path = work / f"{mod_root.name}_compat_report.md"
    report.write(report_path)
    if out_root != mod_root:
        shutil.copy2(report_path, out_root / "compat_report.md")
    print(f"Report: {report_path}")
    print(f"Working database: {db}")

    kill_orphan_archivetool()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
