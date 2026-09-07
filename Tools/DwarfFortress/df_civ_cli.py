#!/usr/bin/env python3
"""
AAMT Dwarf Fortress Creature + Civ CLI.

Commands: new, import, body, validate, generate, art, install, pack, editor
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SHARED = _HERE.parent / "Shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from df_body_logic import apply_fixes, validate
from df_body_parser import compose_body, export_catalog_json, load_body_catalog
from df_creature_schema import BODY_PRESETS, load_spec, new_spec, save_spec, write_presets_file
from df_mod_pack import assemble_mod, install_mod, list_generated_files, pack_zip, staging_dir
from df_paths import dwarf_fortress_root, output_root, templates_dir, tool_dir
from df_raw_parser import extract_named_block_from_file
from df_tile_generator import generate_art_for_spec


def _spec_path_from_args(args: argparse.Namespace) -> Path:
    if getattr(args, "spec", None):
        return Path(args.spec)
    if getattr(args, "id", None):
        return staging_dir({"id": args.id}) / "creature.json"
    raise SystemExit("Provide --spec or --id")


def cmd_new(args: argparse.Namespace) -> int:
    write_presets_file()
    spec = new_spec(args.id, args.name, preset=args.preset)
    if args.culture:
        spec["culture_preset"] = args.culture
    if args.phonology:
        spec["phonology"] = args.phonology
    out = Path(args.output) if args.output else (staging_dir(spec) / "creature.json")
    save_spec(spec, out)
    print(f"Created spec: {out}")
    print(json.dumps({k: spec[k] for k in ("id", "name_singular", "preset", "body_fragments") if k in spec}, indent=2))
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    path = Path(args.raw)
    if not path.is_file():
        print(f"RAW file not found: {path}", file=sys.stderr)
        return 1
    kind = (args.kind or "CREATURE").upper()
    oid = args.object_id
    block = extract_named_block_from_file(path, kind, oid)
    if block is None:
        print(f"Object [{kind}:{oid}] not found in {path}", file=sys.stderr)
        return 1
    frags = []
    desc = ""
    names = ["", "", ""]
    for tok, a in block.tokens:
        if tok.upper() == "BODY" and a:
            frags = list(a)
        elif tok.upper() == "DESCRIPTION" and a:
            desc = a[0]
        elif tok.upper() == "NAME" and len(a) >= 3:
            names = a[:3]
    new_id = args.id or oid
    spec = new_spec(new_id, names[0] or oid, preset="humanoid_civ")
    if frags:
        spec["body_fragments"] = frags
    if desc:
        spec["description"] = desc
    if names[0]:
        spec["name_singular"], spec["name_plural"], spec["name_adj"] = names[0], names[1], names[2]
    out = Path(args.output) if args.output else (staging_dir(spec) / "creature.json")
    save_spec(spec, out)
    print(f"Imported {kind}:{oid} -> {out}")
    print(json.dumps({"id": spec["id"], "body_fragments": spec["body_fragments"][:8], "fragment_count": len(spec["body_fragments"])}, indent=2))
    return 0


def cmd_body(args: argparse.Namespace) -> int:
    if getattr(args, "edit", False):
        return cmd_editor(args)
    cat = load_body_catalog()
    if args.export_catalog:
        out = export_catalog_json(Path(args.export_catalog) if args.export_catalog != "1" else None, cat)
        print(f"Catalog: {out} ({len(cat.bodies)} bodies, {len(cat.detail_plans)} detail plans)")
        return 0
    if args.list:
        for name in sorted(cat.bodies.keys()):
            print(name)
        return 0
    if args.spec:
        spec = load_spec(args.spec)
        graph = compose_body(spec.get("body_fragments") or [], cat)
        print(json.dumps({
            "fragments": graph.fragments,
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
            "flags": {k: v for k, v in graph.flags_present.items()},
            "warnings": graph.warnings,
        }, indent=2))
        return 0
    print("Use --list, --export-catalog, --spec, or --edit", file=sys.stderr)
    return 1


def cmd_validate(args: argparse.Namespace) -> int:
    path = _spec_path_from_args(args)
    spec = load_spec(path)
    result = validate(spec)
    if args.fix:
        fixed = apply_fixes(spec)
        save_spec(fixed, path)
        result = validate(fixed)
        spec = fixed
        print(f"Applied fixes -> {path}")
    print(json.dumps(result.to_dict(), indent=2))

    if getattr(args, "police", False):
        from df_ollama_police import police_body_plan

        report = police_body_plan(spec, validation=result.to_dict())
        print("--- police ---")
        print(json.dumps(report, indent=2))

    return 0 if result.ok else 2


def cmd_analyze(args: argparse.Namespace) -> int:
    path = _spec_path_from_args(args)
    spec = load_spec(path)
    if getattr(args, "fix_layout", False):
        spec = apply_fixes(spec)
        save_spec(spec, path)
        print(f"Applied layout fixes -> {path}")

    workers = getattr(args, "workers", None)
    police = getattr(args, "police", False)
    if workers or police:
        from df_workers import analyze_async

        bundle = analyze_async(spec, workers=workers, police=police)
        report = bundle.get("cost") if isinstance(bundle.get("cost"), dict) else {}
        print(json.dumps(bundle, indent=2))
    else:
        from df_body_cost import analyze_costs, save_cost_report

        report = analyze_costs(spec, full=True)
        print(json.dumps(report, indent=2))

    out = staging_dir(spec) / "cost_report.json"
    try:
        from df_body_cost import save_cost_report

        save_cost_report(spec, out)
        print(f"Wrote {out}")
    except Exception as exc:
        print(f"Warning: could not write cost_report.json: {exc}", file=sys.stderr)
    return 0


def cmd_adventure_kit(args: argparse.Namespace) -> int:
    path = _spec_path_from_args(args)
    spec = load_spec(path)
    from df_adventure_kit import stage_adventure_kit

    root = staging_dir(spec)
    root.mkdir(parents=True, exist_ok=True)
    written = stage_adventure_kit(spec, root)
    print(f"Adventure kit staged under {root}")
    for p in written:
        print(f"  {p}")
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    path = _spec_path_from_args(args)
    spec = load_spec(path)
    if args.fix:
        spec = apply_fixes(spec)
        save_spec(spec, path)
    root = assemble_mod(spec, adventure_kit=bool(getattr(args, "adventure_kit", False)))
    print(f"Generated mod: {root}")
    for f in list_generated_files(root):
        print(f"  {f}")
    return 0


def cmd_art(args: argparse.Namespace) -> int:
    path = _spec_path_from_args(args)
    spec = load_spec(path)
    root = staging_dir(spec)
    root.mkdir(parents=True, exist_ok=True)
    from df_graphics_writer import write_graphics

    write_graphics(spec, root)

    if getattr(args, "blender", False):
        from df_blender_bake import bake_creature_art

        bake = bake_creature_art(spec, root, no_sd=args.no_sd)
        print("[art] blender bake:")
        print(json.dumps({
            "blender": bake.get("blender"),
            "fallback": bake.get("fallback"),
            "arts": {k: str(v) for k, v in (bake.get("arts") or {}).items() if k != "sd"},
        }, indent=2))
        return 0

    arts = generate_art_for_spec(
        spec, root, no_sd=args.no_sd, force=args.force, workers=getattr(args, "workers", None)
    )
    print(f"Art written under {root / 'graphics' / 'images'}")
    payload = {k: str(v) for k, v in arts.items() if k != "sd"}
    payload["sd_used"] = bool(arts.get("sd"))
    print(json.dumps(payload, indent=2))
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    path = _spec_path_from_args(args)
    spec = load_spec(path)
    if not staging_dir(spec).is_dir() or not (staging_dir(spec) / "info.txt").is_file():
        print("Staging incomplete; running generate first...")
        assemble_mod(spec)
    dest = install_mod(spec)
    print(f"Installed to {dest}")
    try:
        print(f"DF root: {dwarf_fortress_root()}")
    except FileNotFoundError as exc:
        print(f"Warning: {exc}")
    return 0


def cmd_pack(args: argparse.Namespace) -> int:
    path = _spec_path_from_args(args)
    spec = load_spec(path)
    if not (staging_dir(spec) / "info.txt").is_file():
        assemble_mod(spec)
    z = pack_zip(spec, Path(args.output) if args.output else None)
    print(f"Packed: {z}")
    return 0


def cmd_editor(args: argparse.Namespace) -> int:
    from df_body_editor import run_server

    spec = None
    if getattr(args, "spec", None):
        spec = Path(args.spec)
    elif getattr(args, "id", None):
        spec = staging_dir({"id": args.id}) / "creature.json"
    host = getattr(args, "host", None) or "127.0.0.1"
    port = int(getattr(args, "port", None) or 8765)
    run_server(host, port, spec, open_browser=not getattr(args, "no_browser", False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="df_civ_cli",
        description="AAMT Dwarf Fortress Creature + Civilization tool",
    )
    sub = p.add_subparsers(dest="command", required=True)

    n = sub.add_parser("new", help="Create a new creature.json spec")
    n.add_argument("--id", required=True)
    n.add_argument("--name", required=True)
    n.add_argument("--preset", default="humanoid_civ", choices=sorted(BODY_PRESETS.keys()))
    n.add_argument("--culture", default="dwarf_industry")
    n.add_argument("--phonology", default="harsh")
    n.add_argument("--output", "-o")
    n.set_defaults(func=cmd_new)

    imp = sub.add_parser("import", help="Import BODY/NAME from a vanilla CREATURE raw")
    imp.add_argument("--raw", required=True, help="Path to creature raw file")
    imp.add_argument("--object-id", required=True)
    imp.add_argument("--kind", default="CREATURE")
    imp.add_argument("--id", help="New id (default=object-id)")
    imp.add_argument("--output", "-o")
    imp.set_defaults(func=cmd_import)

    b = sub.add_parser("body", help="Body catalog / compose graph")
    b.add_argument("--list", action="store_true")
    b.add_argument("--export-catalog", nargs="?", const="1")
    b.add_argument("--spec")
    b.add_argument("--edit", action="store_true", help="Launch SVG body editor for --spec")
    b.add_argument("--host", default="127.0.0.1")
    b.add_argument("--port", type=int, default=8765)
    b.set_defaults(func=cmd_body)

    v = sub.add_parser("validate", help="Validate body + civ flags")
    v.add_argument("--spec")
    v.add_argument("--id")
    v.add_argument("--fix", action="store_true")
    v.add_argument("--police", action="store_true", help="Ollama body-plan critique (soft-skip if missing)")
    v.set_defaults(func=cmd_validate)

    an = sub.add_parser("analyze", help="Biological cost / evolution / balance report")
    an.add_argument("--spec")
    an.add_argument("--id")
    an.add_argument("--fix-layout", action="store_true", help="Apply existing body auto-fixes first")
    an.add_argument("--police", action="store_true")
    an.add_argument("--workers", type=int, default=None, help="Thread pool size (AAMT-side only)")
    an.set_defaults(func=cmd_analyze)

    g = sub.add_parser("generate", help="Write full mod under Output/DwarfFortress/<ID>/")
    g.add_argument("--spec")
    g.add_argument("--id")
    g.add_argument("--fix", action="store_true", help="Apply body fixes before generate")
    g.add_argument("--adventure-kit", action="store_true", help="Include Adventure Mode parity kit files")
    g.set_defaults(func=cmd_generate)

    a = sub.add_parser("art", help="Generate part sheet + portrait")
    a.add_argument("--spec")
    a.add_argument("--id")
    a.add_argument("--no-sd", action="store_true")
    a.add_argument("--force", action="store_true")
    a.add_argument("--blender", action="store_true", help="Route through df_blender_bake (falls back to tiles)")
    a.add_argument("--workers", type=int, default=None, help="Parallel Pillow part-sheet cells (AAMT-side)")
    a.set_defaults(func=cmd_art)

    i = sub.add_parser("install", help="Copy staging mod into DF mods/")
    i.add_argument("--spec")
    i.add_argument("--id")
    i.set_defaults(func=cmd_install)

    pk = sub.add_parser("pack", help="Zip staging mod")
    pk.add_argument("--spec")
    pk.add_argument("--id")
    pk.add_argument("--output", "-o")
    pk.set_defaults(func=cmd_pack)

    ed = sub.add_parser("editor", help="Launch Creature Studio (body + graphics GUI)")
    ed.add_argument("--spec")
    ed.add_argument("--id")
    ed.add_argument("--host", default="127.0.0.1")
    ed.add_argument("--port", type=int, default=8765)
    ed.add_argument("--no-browser", action="store_true")
    ed.set_defaults(func=cmd_editor)

    adv = sub.add_parser("adventure-kit", help="Stage Adventure Mode parity kit into the mod folder")
    adv.add_argument("--spec")
    adv.add_argument("--id")
    adv.set_defaults(func=cmd_adventure_kit)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not (templates_dir() / "presets.json").is_file():
        write_presets_file()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
