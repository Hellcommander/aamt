#!/usr/bin/env python3
"""
Elemental Reforged Monster Race Asset Tool (AAMT)

Unified CLI for clothes / armor / weapon packs used by LH_Legacy_Expansion.

Examples:
  python monster_race_tool.py doctor --start-sd
  python monster_race_tool.py generate --all --mode both --start-sd --install
  python monster_race_tool.py generate --race Darkling --mode ai --install
  python monster_race_tool.py generate --all --mode tools --install
  python monster_race_tool.py banner --start-sd --install --force
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from build_armor_xml import KIND_META, build_item, internal_name, wrap
from er_tool_lib import (
    DEFAULT_CONFIG,
    KINDS,
    extra_units_path,
    find_mesh,
    kinds_for_race,
    load_config,
    mod_path,
    race_keys,
    validate_config,
    weapon_icon_style,
)
from generate_procedural_icon import make_icon, make_texture
from patch_unit_model_types import patch_unit_block
from er_harden_units import (
    harden_mod_units,
    harden_unit_block,
    race_key_from_unit,
    validate_designable_units,
    validate_leader_units,
)
import re


ROOT = Path(__file__).resolve().parent


def _log(msg: str) -> None:
    print(msg, flush=True)


def cmd_list(cfg: dict[str, Any]) -> int:
    print(f"{'Race':<16} {'Tier':<12} {'UMT':<18} Packs")
    print("-" * 72)
    for key, race in cfg["races"].items():
        packs = ",".join(kinds_for_race(race))
        umt = (race.get("unitModelTypePrimary") or (race.get("unitModelTypes") or ["?"])[0])
        print(f"{key:<16} {race.get('bodyTier','?'):<12} {umt:<18} {packs}")
    return 0


def cmd_doctor(cfg: dict[str, Any], args: argparse.Namespace) -> int:
    from er_ai_pipeline import probe_tools

    errs = validate_config(cfg)
    mod = mod_path(cfg, args.mod)
    print("Config:", args.config or DEFAULT_CONFIG)
    print("Mod:", mod, "OK" if mod.exists() else "MISSING")
    print("Game:", cfg.get("gamePath"), "OK" if Path(cfg.get("gamePath") or "").exists() else "MISSING")
    ref = Path(cfg.get("referenceHkbPath") or "")
    print("HKB ref:", ref, "OK" if ref.exists() else "MISSING")

    start_sd = bool(getattr(args, "start_sd", False))
    tools = probe_tools(start_sd=start_sd, wait_sd_sec=getattr(args, "sd_wait", 120.0), cfg=cfg)
    print("Shared:", "OK" if tools["shared"] else "MISSING")
    print("Pillow:", "OK" if tools["pillow"] else "MISSING")
    print("Ollama:", "OK" if tools["ollama"] else "DOWN (start ollama serve)")
    print("Stable Diffusion:", "OK" if tools["sd"] else "DOWN (Start-StableDiffusionServer.ps1)")
    if tools.get("sd_url"):
        print("  SD API:", tools["sd_url"])
    print("ImageMagick:", tools["magick"] or "MISSING")
    print("Blender:", tools["blender"] or "optional / not found")

    havok = tools.get("havok") or {}
    if havok.get("ok"):
        ver = havok.get("productVersion") or "?"
        tag = "OK (7.1)" if havok.get("recommended") else f"FOUND ({ver}) - prefer 7.1"
        print("Havok HCT:", tag)
        print("  Path:", havok.get("filterManager"))
        for note in havok.get("notes") or []:
            print(" ", note)
    else:
        print("Havok HCT: MISSING (set havokPath -> HCT 7.1 32-bit)")
        for note in havok.get("notes") or []:
            print(" ", note)

    xsi = tools.get("softimage") or {}
    if xsi.get("ok"):
        fv = xsi.get("fileVersion") or "?"
        print(f"Softimage: OK ({fv})")
        print("  Path:", xsi.get("xsi"))
        print("  FBX plugin:", "OK" if xsi.get("fbxPlugin") else "MISSING")
        print(
            "  HCT plugins:",
            "FOUND" if xsi.get("havokPluginsOk") else "not installed in Softimage",
        )
        for note in xsi.get("notes") or []:
            print(" ", note)
    else:
        print("Softimage: MISSING (set softimagePath)")
        for note in xsi.get("notes") or []:
            print(" ", note)

    if getattr(args, "havok_checklist", False):
        from er_havok import print_export_checklist

        print_export_checklist()

    if not tools["pillow"]:
        errs.append("Pillow not installed")
    if errs:
        print(f"Config issues ({len(errs)}):")
        for e in errs:
            print(" -", e)
        return 1
    print("Config: OK")
    if not tools["ollama"] or not tools["sd"]:
        print("Note: AI mode needs Ollama + SD; Tools mode still works.")
    return 0


def cmd_havok(cfg: dict[str, Any], args: argparse.Namespace) -> int:
    from er_havok import open_filter_manager, print_export_checklist, probe_havok

    info = probe_havok(cfg)
    print(json.dumps(info, indent=2))
    if args.checklist:
        print_export_checklist()
    if args.open:
        return open_filter_manager(cfg)
    return 0 if info.get("ok") else 1


def cmd_variants(cfg: dict[str, Any], args: argparse.Namespace) -> int:
    from er_mesh_variants import resolve_item_assets, suggest_variants

    keys = race_keys(cfg, None if args.all or args.race == "All" else args.race)
    print(
        f"textureVariants={cfg.get('textureVariants')} "
        f"altItems={cfg.get('altItems')} meshPolicy={cfg.get('meshPolicy')}"
    )
    print(f"{'Race':<16}{'Kind':<8}{'Var':<5}{'ModelSrc':<10}{'TexSrc':<18}Model")
    print("-" * 90)
    for key in keys:
        for kind in ("clothes", "armor", "weapon"):
            if kind not in cfg["races"][key]:
                continue
            for alt in (False, True):
                r = resolve_item_assets(cfg, key, kind, alt=alt, make_texture=False)
                tag = "Alt" if alt else "Base"
                print(
                    f"{key:<16}{kind:<8}{tag:<5}{r['modelSource']:<10}"
                    f"{r['textureSource']:<18}{Path(r['model'] or '-').name}"
                )
    print("\nFallbacks: alt mesh -> configured model -> baseModelPath")
    print("           recolor DDS -> original texture -> sibling texture -> omit")
    if args.suggest:
        print("\n--- mesh suggestions (advisory) ---")
        for key in keys:
            s = suggest_variants(cfg, key)
            for kind in ("clothes", "armor"):
                cur = Path(s[kind]["current"] or "-").name
                sug = Path(s[kind]["suggested"] or "-").name
                mark = "" if cur == sug else " *"
                print(f"{key:<16}{kind:<8}{cur} -> {sug}{mark}")
    return 0


def cmd_softimage(cfg: dict[str, Any], args: argparse.Namespace) -> int:
    from er_softimage import install_havok_addon, open_softimage, probe_softimage

    if args.install_havok:
        return install_havok_addon(cfg, copy=bool(args.copy))

    info = probe_softimage(cfg)
    print(json.dumps(info, indent=2))
    if args.open:
        scene = Path(args.scene) if args.scene else None
        return open_softimage(cfg, scene=scene)
    return 0 if info.get("ok") else 1


def cmd_check_meshes(cfg: dict[str, Any], args: argparse.Namespace) -> int:
    keys = race_keys(cfg, None if args.all or args.race == "All" else args.race)
    missing = 0
    found = 0
    for key in keys:
        race = cfg["races"][key]
        print(f"\n=== {key} ({race.get('display')}) [{race.get('bodyTier')}] ===")
        for kind in kinds_for_race(race):
            model = race[kind]["model"]
            hit = find_mesh(cfg, model)
            if hit:
                found += 1
                print(f"  OK  {kind:<8} {model} -> {hit}")
            else:
                missing += 1
                print(f"  ??  {kind:<8} {model} (not on disk; may still resolve in-game)")
            tex = race[kind].get("texture")
            if tex:
                tex_hit = find_mesh(cfg, tex)  # textures often sit beside meshes
                # also search by filename in same roots
                if not tex_hit:
                    from er_tool_lib import resolve_mesh_candidates

                    for c in resolve_mesh_candidates(cfg, tex):
                        # try sibling texture extensions already in path
                        if c.is_file():
                            tex_hit = c
                            break
                        # try replacing extension variants in Monsters folder
                        for alt in (
                            c.with_suffix(".dds"),
                            c.with_suffix(".png"),
                            c.with_suffix(".DDS"),
                        ):
                            if alt.is_file():
                                tex_hit = alt
                                break
                        if tex_hit:
                            break
                status = "OK" if tex_hit else "??"
                print(f"  {status}  texture  {tex}" + (f" -> {tex_hit}" if tex_hit else ""))
    print(f"\nMeshes found: {found} | missing on disk: {missing}")
    return 0 if missing == 0 else 0  # missing on disk is warning, not hard fail


def cmd_scan(cfg: dict[str, Any], args: argparse.Namespace) -> int:
    mod = mod_path(cfg, args.mod)
    xml = mod / "Data" / "GameCore" / "LHL_GeneratedMonsterArmor.xml"
    units = extra_units_path(cfg, args.mod)
    print(f"Mod: {mod}")
    print(f"XML: {'present' if xml.exists() else 'MISSING'} ({xml.name})")
    print(f"ExtraUnits: {'present' if units.exists() else 'MISSING'}")
    print()
    print(f"{'Race':<16} {'Clothes':<8} {'Armor':<8} {'Weapon':<8} {'UMT units':<10}")
    print("-" * 60)

    unit_text = units.read_text(encoding="utf-8") if units.exists() else ""
    for key, race in cfg["races"].items():
        row = []
        for kind in KINDS:
            if kind not in race:
                row.append("-")
                continue
            internal = internal_name(cfg, key, kind)
            icon = mod / "Gfx" / "Items" / f"{internal}_Icon.png"
            row.append("OK" if icon.exists() else "no")
        # count units with this race key that have UnitModelType
        umt_n = len(
            re.findall(
                rf'InternalName="Unit_\w+_{re.escape(key)}">[\s\S]*?<UnitModelType>',
                unit_text,
            )
        )
        print(f"{key:<16} {row[0]:<8} {row[1]:<8} {row[2]:<8} {umt_n:<10}")
    return 0


def _icon_style_for(kind: str, pack: dict[str, Any], race: dict[str, Any]) -> str:
    if kind == "weapon":
        return weapon_icon_style(pack)
    if pack.get("iconStyle"):
        return str(pack["iconStyle"])
    if kind == "clothes":
        return "robe"
    if race.get("bodyTier") == "beast":
        return "plate"
    return "armor"


def generate_race_package(
    cfg: dict[str, Any],
    race_key: str,
    out_dir: Path,
    *,
    icon_size: int = 128,
    texture_size: int = 512,
    kinds: list[str] | None = None,
) -> dict[str, Any]:
    """Build pack from original game meshes/textures/icons (procedural only as fallback).

    When altItems is enabled (default), also emits an Alt variant per kind with a
    different model when available and a differently recolored texture, falling
    back to the primary model/texture when no alt exists.
    """
    from er_mesh_variants import resolve_item_assets
    from er_original_assets import materialize_original_assets

    race = cfg["races"][race_key]
    out_dir.mkdir(parents=True, exist_ok=True)
    source = out_dir / "Source"
    items_dir = out_dir / "Gfx" / "Items"
    armor_dir = out_dir / "Gfx" / "HKB" / "Armor"
    variant_tex_dir = out_dir / "Gfx" / "HKB" / "Monsters"
    for d in (source, items_dir, armor_dir, variant_tex_dir):
        d.mkdir(parents=True, exist_ok=True)

    make_variants = bool(cfg.get("textureVariants", True))
    make_alts = bool(cfg.get("altItems", True))
    palette = list(race.get("palette") or ["#444", "#888", "#ccc", "#222"])
    results = []

    for kind in kinds_for_race(race, kinds):
        variants = [False]
        if make_alts:
            variants.append(True)

        for is_alt in variants:
            resolved = resolve_item_assets(
                cfg,
                race_key,
                kind,
                alt=is_alt,
                dst_dir=variant_tex_dir if make_variants else None,
                make_texture=make_variants,
            )
            pack = resolved["pack"]
            internal = internal_name(cfg, race_key, kind, alt=is_alt)
            style = _icon_style_for(kind, pack, race)
            seed = sum(ord(c) for c in internal) % 100000

            icon_name = f"{internal}_Icon.png"
            tex_name = f"{internal}_Texture.png"
            icon_dst = items_dir / icon_name
            tex_dst = armor_dir / tex_name

            # Icons/source refs use the race's configured pack (not mutated alt pack)
            # so medallions still resolve; Alt gets a slight procedural tint via seed.
            base_pack = race[kind]
            orig = materialize_original_assets(
                cfg,
                race_key,
                race,
                kind,
                base_pack,
                icon_dst=icon_dst,
                texture_dst=tex_dst,
                source_dir=source,
                icon_size=icon_size,
            )

            if not orig["icon"]:
                icon = make_icon(icon_size, palette, seed, style)
                icon.save(source / icon_name)
                shutil.copy2(source / icon_name, icon_dst)
            elif is_alt and icon_dst.exists():
                # Distinguish Alt icons lightly (hue shift) when ImageMagick available
                try:
                    from er_ai_pipeline import find_magick
                    import subprocess as _sp

                    mag = find_magick()
                    if mag:
                        tmp = icon_dst.with_suffix(".alt.png")
                        _sp.run(
                            [
                                str(mag),
                                str(icon_dst),
                                "-modulate",
                                "100,120,115",
                                str(tmp),
                            ],
                            check=True,
                            capture_output=True,
                        )
                        if tmp.exists():
                            shutil.move(str(tmp), str(icon_dst))
                except Exception:
                    pass

            if not orig["texture"]:
                tex = make_texture(texture_size, palette, seed + 17)
                tex.save(source / tex_name)
                shutil.copy2(source / tex_name, tex_dst)

            chunk = build_item(cfg, race_key, kind, icon_name, pack=pack, alt=is_alt)
            (out_dir / f"{internal}.xml").write_text(chunk, encoding="utf-8")
            results.append(
                {
                    "kind": kind,
                    "alt": is_alt,
                    "internal": internal,
                    "itemName": pack.get("itemName"),
                    "model": resolved["model"],
                    "modelSource": resolved["modelSource"],
                    "gameTexture": resolved["texture"],
                    "textureSource": resolved["textureSource"],
                    "variantTexture": Path(resolved["variantTextureFile"]).name
                    if resolved.get("variantTextureFile")
                    else None,
                    "variantTextureFile": resolved.get("variantTextureFile"),
                    "style": style,
                    "icon": str(icon_dst),
                    "texture": str(tex_dst),
                    "xml": str(out_dir / f"{internal}.xml"),
                    "original": orig,
                    "ai": {"icon": False, "texture": False},
                }
            )

    return {
        "race": race_key,
        "display": race.get("display"),
        "bodyTier": race.get("bodyTier"),
        "items": results,
        "policy": cfg.get("assetPolicy") or "originals",
        "altItems": make_alts,
    }


def apply_ai_pass(
    cfg: dict[str, Any],
    manifest: list[dict[str, Any]],
    *,
    tools: dict[str, Any],
    enhance: bool,
    steps: int,
    ai_kinds: list[str],
    force: bool,
) -> None:
    """
    Optional AI polish. With assetPolicy=originals, skip inventing new art unless --force-ai.
    Prefer keeping original medallion icons + original HKB textures referenced in XML.
    """
    policy = (cfg.get("assetPolicy") or "originals").lower()
    if policy == "originals" and not force:
        _log("[AI] skipped — assetPolicy=originals (meshes/textures/icons from game art)")
        _log("     Pass --force-ai to overlay SD on icons (not recommended for mesh/texture).")
        return

    from er_ai_pipeline import ai_assets_for_item, postprocess_icon

    if not tools.get("sd"):
        _log("[AI] SD not available — keeping original/procedural icons")
        return

    _log(f"[AI] Ollama enhance={'ON' if enhance and tools.get('ollama') else 'OFF'} | SD={tools.get('sd_url')}")
    for pkg in manifest:
        race = cfg["races"][pkg["race"]]
        source = Path()
        if pkg["items"]:
            source = Path(pkg["items"][0]["icon"]).resolve().parents[2] / "Source"
        _log(f"--- AI {pkg['race']} ---")
        for it in pkg["items"]:
            if it["kind"] not in ai_kinds:
                continue
            pack = race[it["kind"]]
            # Only polish icons from original base — never replace game texture refs in XML
            result = ai_assets_for_item(
                cfg=cfg,
                race=race,
                kind=it["kind"],
                pack=pack,
                icon_path=Path(it["icon"]),
                texture_path=Path(it["texture"]),
                source_dir=source,
                tools=tools,
                enhance=enhance and bool(tools.get("ollama")),
                force=force,
                steps=steps,
                gen_icon=True,
                gen_texture=False,  # XML uses original Texture_*; do not invent
            )
            it["ai"] = {"icon": result["icon"], "texture": False}
            _log(f"  {it['internal']}: {'AI icon' if result['icon'] else 'kept original'}")
            postprocess_icon(Path(it["icon"]), size=128)


def cmd_generate(cfg: dict[str, Any], args: argparse.Namespace) -> int:
    errs = validate_config(cfg)
    if errs:
        for e in errs:
            _log(f"CONFIG: {e}")
        return 1

    keys = race_keys(cfg, None if args.all else args.race)
    out_root = Path(args.output or (ROOT / "Output"))
    out_root.mkdir(parents=True, exist_ok=True)
    kinds = [k.strip() for k in (args.kinds or "clothes,armor,weapon").split(",") if k.strip()]
    mode = (args.mode or "tools").lower()
    want_ai = mode in ("ai", "both")
    want_tools = mode in ("tools", "both", "ai")  # AI still seeds procedural first

    from er_ai_pipeline import probe_tools

    tools = {"sd": False, "ollama": False, "magick": None}
    if want_ai or getattr(args, "start_sd", False):
        tools = probe_tools(
            start_sd=bool(getattr(args, "start_sd", False) or (want_ai and not args.skip_sd_start)),
            wait_sd_sec=float(getattr(args, "sd_wait", 180.0)),
            cfg=cfg,
        )
        _log(
            f"Tools: Ollama={'OK' if tools.get('ollama') else 'no'} | "
            f"SD={'OK' if tools.get('sd') else 'no'} | "
            f"Magick={'OK' if tools.get('magick') else 'no'}"
        )
        if mode == "ai" and not tools.get("sd"):
            _log("ERROR: --mode ai requires Stable Diffusion. Use --start-sd or Mode Both/Tools.")
            return 1

    t0 = time.perf_counter()
    manifest: list[dict[str, Any]] = []

    def work(rk: str) -> dict[str, Any]:
        race_out = out_root / rk
        return generate_race_package(
            cfg,
            rk,
            race_out,
            icon_size=args.icon_size,
            texture_size=args.texture_size,
            kinds=kinds,
        )

    workers = max(1, min(args.jobs, len(keys)))
    _log(f"Generating {len(keys)} race(s), mode={mode}, policy={cfg.get('assetPolicy','originals')}, kinds={kinds}, jobs={workers}")
    if want_tools:
        if workers == 1:
            for rk in keys:
                _log(f"--- {rk} ---")
                pkg = work(rk)
                n_orig = sum(1 for it in pkg["items"] if it.get("original", {}).get("icon"))
                _log(f"  {len(pkg['items'])} items [{pkg.get('bodyTier')}] originals_icons={n_orig}")
                manifest.append(pkg)
        else:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                futs = {ex.submit(work, rk): rk for rk in keys}
                for fut in as_completed(futs):
                    rk = futs[fut]
                    pkg = fut.result()
                    n_orig = sum(1 for it in pkg["items"] if it.get("original", {}).get("icon"))
                    _log(f"--- {rk} --- {len(pkg['items'])} items originals_icons={n_orig}")
                    manifest.append(pkg)
            order = {k: i for i, k in enumerate(keys)}
            manifest.sort(key=lambda p: order.get(p["race"], 999))

    if want_ai:
        ai_kinds = [k.strip() for k in (args.ai_kinds or "clothes,armor,weapon").split(",") if k.strip()]
        apply_ai_pass(
            cfg,
            manifest,
            tools=tools,
            enhance=not args.no_enhance,
            steps=args.sd_steps,
            ai_kinds=ai_kinds,
            force=args.force_ai,
        )

    # Combined XML — use already-resolved per-item fragments (includes Alt + fallbacks)
    chunks: list[str] = []
    for pkg in manifest:
        for it in pkg["items"]:
            frag = Path(it["xml"])
            if frag.exists():
                chunks.append(frag.read_text(encoding="utf-8").rstrip() + "\n")
            else:
                chunks.append(
                    build_item(
                        cfg,
                        pkg["race"],
                        it["kind"],
                        Path(it["icon"]).name,
                        alt=bool(it.get("alt")),
                    )
                )
    combined = out_root / "LHL_GeneratedMonsterArmor.xml"
    combined.write_text(wrap(chunks), encoding="utf-8")
    (out_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    elapsed = time.perf_counter() - t0
    ai_icons = sum(1 for p in manifest for it in p["items"] if it.get("ai", {}).get("icon"))
    n_alt = sum(1 for p in manifest for it in p["items"] if it.get("alt"))
    _log(
        f"Combined XML: {combined} ({len(chunks)} items, {n_alt} alt, "
        f"{elapsed:.1f}s, AI icons={ai_icons})"
    )

    if args.install:
        return install_to_mod(cfg, args, out_root, manifest, combined)
    return 0


def install_to_mod(
    cfg: dict[str, Any],
    args: argparse.Namespace,
    out_root: Path,
    manifest: list[dict[str, Any]],
    combined: Path,
) -> int:
    mod = mod_path(cfg, args.mod)
    if not mod.exists():
        _log(f"Mod path not found: {mod}")
        return 1

    items = mod / "Gfx" / "Items"
    armor = mod / "Gfx" / "HKB" / "Armor"
    monsters = mod / "Gfx" / "HKB" / "Monsters"
    gc = mod / "Data" / "GameCore"
    for d in (items, armor, monsters, gc):
        d.mkdir(parents=True, exist_ok=True)

    shutil.copy2(combined, gc / "LHL_GeneratedMonsterArmor.xml")
    copied_icons = 0
    copied_tex = 0
    copied_variants = 0
    for pkg in manifest:
        for it in pkg["items"]:
            icon = Path(it["icon"])
            tex = Path(it["texture"])
            if icon.exists():
                shutil.copy2(icon, items / icon.name)
                copied_icons += 1
            if tex.exists():
                shutil.copy2(tex, armor / tex.name)
                copied_tex += 1
            # Recolored DDS variant referenced by XML (bare-name resolvable).
            vfile = it.get("variantTextureFile")
            if vfile and Path(vfile).exists():
                shutil.copy2(vfile, monsters / Path(vfile).name)
                copied_variants += 1

    # Harden all LHL unit XMLs (poses, UnitModelType, skeleton/anim/cutscene)
    if not args.skip_patch:
        report = harden_mod_units(mod, cfg)
        _log(
            f"  Hardened units: {report['totals']['patched']} / {report['totals']['units']} "
            f"(skipped {report['totals']['skipped']})"
        )

    _log(f"Installed into {mod}")
    _log(f"  XML + {copied_icons} icons + {copied_tex} textures + {copied_variants} recolored DDS variants")
    return 0


def cmd_harden_units(cfg: dict[str, Any], args: argparse.Namespace) -> int:
    """Apply presentation fields to all LHL_*Units.xml in the mod."""
    mod = mod_path(cfg, args.mod)
    if not mod.exists():
        _log(f"Mod path not found: {mod}")
        return 1
    if getattr(args, "dry_run", False):
        would = 0
        total = 0
        for path in sorted((mod / "Data" / "GameCore").glob("LHL_*Units.xml")):
            text = path.read_text(encoding="utf-8")
            for name, body in re.findall(
                r'<UnitType InternalName="([^"]+)">(.*?)</UnitType>', text, re.S
            ):
                total += 1
                key = race_key_from_unit(name, body, cfg)
                if not key:
                    continue
                if harden_unit_block(body, cfg["races"][key]) != body:
                    would += 1
        _log(json.dumps({"dry_run": True, "would_patch": would, "units": total}))
        return 0

    report = harden_mod_units(mod, cfg)
    _log(json.dumps(report, indent=2))
    errs = validate_designable_units(mod)
    lead_errs = validate_leader_units(mod)
    if lead_errs:
        _log(f"Leader presentation errors: {len(lead_errs)}")
        for e in lead_errs[:40]:
            _log(f"  {e}")
        if len(lead_errs) > 40:
            _log(f"  ... +{len(lead_errs) - 40} more")
    if errs:
        _log(f"Validation warnings after harden: {len(errs)}")
        for e in errs[:40]:
            _log(f"  {e}")
        if len(errs) > 40:
            _log(f"  ... +{len(errs) - 40} more")
        if getattr(args, "strict", False):
            return 1
    if lead_errs and getattr(args, "strict", False):
        return 1
    if not errs and not lead_errs:
        _log("All designable + leader units have viable presentation/poses.")
    return 0


def cmd_install(cfg: dict[str, Any], args: argparse.Namespace) -> int:
    out_root = Path(args.output or (ROOT / "Output"))
    combined = out_root / "LHL_GeneratedMonsterArmor.xml"
    manifest_path = out_root / "manifest.json"
    if not combined.exists() or not manifest_path.exists():
        _log("No Output package found. Run generate first.")
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return install_to_mod(cfg, args, out_root, manifest, combined)


def cmd_banner(cfg: dict[str, Any], args: argparse.Namespace) -> int:
    """Generate Mod Manager banner via local SD/Ollama (no Cursor image credits)."""
    from er_banner import generate_banner, install_banner, package_cfg, write_banner_meta

    pkg = package_cfg(cfg)
    out_root = Path(args.output or (ROOT / "Output"))
    out_root.mkdir(parents=True, exist_ok=True)
    banner_path = out_root / pkg["bannerFile"]

    result = generate_banner(
        cfg,
        output=banner_path,
        prompt=args.prompt or None,
        enhance=not args.no_enhance,
        force=bool(args.force),
        steps=int(args.sd_steps),
        guidance=float(args.guidance),
        allow_procedural=not args.require_sd,
        start_sd=bool(args.start_sd),
        sd_wait=float(args.sd_wait),
    )
    write_banner_meta(cfg, result, out_root)

    if not result.get("ok"):
        return 1

    if args.install:
        installed = install_banner(cfg, banner_path, mod=mod_path(cfg, args.mod))
        if not installed:
            return 1
    else:
        _log(f"Banner ready (not installed): {banner_path}")
        _log("Pass --install to copy into the mod folder.")
    return 0


def cmd_validate(cfg: dict[str, Any], args: argparse.Namespace) -> int:
    import validate_install as vi

    argv = ["--config", str(args.config or DEFAULT_CONFIG)]
    if args.mod:
        argv += ["--mod", args.mod]
    code = int(vi.main(argv) or 0)
    # validate_install already checks unit presentation; keep a second pass for clarity
    mod = mod_path(cfg, args.mod)
    errs = validate_designable_units(mod)
    if errs:
        _log(f"Unit presentation FAIL: {len(errs)}")
        for e in errs[:50]:
            _log(f" - {e}")
        return 1
    return code


def cmd_patch_units(cfg: dict[str, Any], args: argparse.Namespace) -> int:
    units = Path(args.units) if args.units else extra_units_path(cfg, args.mod)
    if not units.exists():
        _log(f"Missing units file: {units}")
        return 1
    from patch_unit_model_types import main as patch_main
    import sys as _sys

    argv = ["patch_unit_model_types.py", "--config", str(args.config or DEFAULT_CONFIG), "--units", str(units)]
    if args.dry_run:
        argv.append("--dry-run")
    old = _sys.argv
    try:
        _sys.argv = argv
        patch_main()
    finally:
        _sys.argv = old
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Elemental Reforged monster race clothes/armor/weapon tool"
    )
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--mod", default="", help="Override mod path")

    sub = ap.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List races and packs")
    p_list.set_defaults(func=lambda c, a: cmd_list(c))

    p_doc = sub.add_parser("doctor", help="Check config, paths, Ollama/SD/ImageMagick")
    p_doc.add_argument("--start-sd", action="store_true", help="Try to start SD3.5 server")
    p_doc.add_argument("--sd-wait", type=float, default=120.0)
    p_doc.add_argument("--havok-checklist", action="store_true", help="Print HCT Packfile export steps")
    p_doc.set_defaults(func=cmd_doctor)

    p_havok = sub.add_parser("havok", help="Probe / open Havok Content Tools 7.1")
    p_havok.add_argument("--open", action="store_true", help="Launch Standalone Filter Manager")
    p_havok.add_argument("--checklist", action="store_true", help="Print Packfile export checklist")
    p_havok.set_defaults(func=cmd_havok)

    p_xsi = sub.add_parser("softimage", help="Probe / open Softimage Mod Tool")
    p_xsi.add_argument("--open", action="store_true", help="Launch Softimage (xsi.exe)")
    p_xsi.add_argument("--scene", default="", help="Optional scene/FBX path to open")
    p_xsi.add_argument(
        "--install-havok",
        action="store_true",
        help="Link HCT XSI plugins into Softimage Addons/HavokContentTools",
    )
    p_xsi.add_argument(
        "--copy",
        action="store_true",
        help="With --install-havok, copy Application/Data instead of junction",
    )
    p_xsi.set_defaults(func=cmd_softimage)

    p_var = sub.add_parser("variants", help="Preview mesh/texture variant selection per race")
    p_var.add_argument("--race", default="All")
    p_var.add_argument("--all", action="store_true")
    p_var.add_argument("--suggest", action="store_true", help="Also show advisory mesh suggestions")
    p_var.set_defaults(func=cmd_variants)

    p_scan = sub.add_parser("scan", help="Scan mod install status")
    p_scan.set_defaults(func=cmd_scan)

    p_chk = sub.add_parser("check-meshes", help="Verify HKB/texture paths on disk")
    p_chk.add_argument("--race", default="All")
    p_chk.add_argument("--all", action="store_true")
    p_chk.set_defaults(func=cmd_check_meshes)

    p_gen = sub.add_parser("generate", help="Generate icons/textures/XML (tools and/or AI)")
    p_gen.add_argument("--race", default="")
    p_gen.add_argument("--all", action="store_true")
    p_gen.add_argument("--kinds", default="clothes,armor,weapon")
    p_gen.add_argument("--output", default="")
    p_gen.add_argument("--install", action="store_true")
    p_gen.add_argument("--skip-patch", action="store_true")
    p_gen.add_argument("--jobs", type=int, default=4)
    p_gen.add_argument("--icon-size", type=int, default=128)
    p_gen.add_argument("--texture-size", type=int, default=512)
    p_gen.add_argument(
        "--mode",
        choices=["tools", "ai", "both"],
        default="tools",
        help="tools=procedural, ai=SD+Ollama (requires SD), both=procedural then AI overlay",
    )
    p_gen.add_argument("--start-sd", action="store_true", help="Auto-start SD3.5 if down")
    p_gen.add_argument("--skip-sd-start", action="store_true", help="Do not auto-start SD")
    p_gen.add_argument("--sd-wait", type=float, default=180.0)
    p_gen.add_argument("--sd-steps", type=int, default=28)
    p_gen.add_argument("--ai-kinds", default="clothes,armor,weapon", help="Which packs get AI art")
    p_gen.add_argument("--no-enhance", action="store_true", help="Skip Ollama prompt enhancement")
    p_gen.add_argument("--force-ai", action="store_true", help="Overwrite even if AI files exist")
    p_gen.set_defaults(func=cmd_generate)

    p_ins = sub.add_parser("install", help="Install existing Output/ into mod")
    p_ins.add_argument("--output", default="")
    p_ins.add_argument("--skip-patch", action="store_true")
    p_ins.set_defaults(func=cmd_install)

    p_ban = sub.add_parser(
        "banner",
        help="Generate Mod Manager banner via local SD/Ollama (procedural fallback)",
    )
    p_ban.add_argument("--output", default="", help="Output folder (default: Output/)")
    p_ban.add_argument("--install", action="store_true", help="Copy banner into mod root")
    p_ban.add_argument("--force", action="store_true", help="Overwrite existing banner")
    p_ban.add_argument("--prompt", default="", help="Override banner prompt")
    p_ban.add_argument("--start-sd", action="store_true", help="Start local SD server if down")
    p_ban.add_argument("--sd-wait", type=float, default=180.0)
    p_ban.add_argument(
        "--sd-steps",
        type=int,
        default=40,
        help="SD steps (default 40; higher = sharper, slower)",
    )
    p_ban.add_argument(
        "--guidance",
        type=float,
        default=7.5,
        help="CFG / guidance scale (default 7.5)",
    )
    p_ban.add_argument("--no-enhance", action="store_true", help="Skip Ollama prompt enhance")
    p_ban.add_argument(
        "--require-sd",
        action="store_true",
        help="Fail if SD is down (no procedural fallback)",
    )
    p_ban.set_defaults(func=cmd_banner)

    p_val = sub.add_parser("validate", help="Validate mod install")
    p_val.set_defaults(func=cmd_validate)

    p_patch = sub.add_parser("patch-units", help="Patch ExtraUnits UnitModelType")
    p_patch.add_argument("--units", default="")
    p_patch.add_argument("--dry-run", action="store_true")
    p_patch.set_defaults(func=cmd_patch_units)

    p_hard = sub.add_parser(
        "harden-units",
        help="Apply ClothPoseIndex/UnitModelType/skeleton/anim/cutscene to all LHL_*Units.xml",
    )
    p_hard.add_argument("--dry-run", action="store_true")
    p_hard.add_argument("--strict", action="store_true", help="Fail if designable units still incomplete")
    p_hard.set_defaults(func=cmd_harden_units)

    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    cfg_path = Path(args.config) if args.config else DEFAULT_CONFIG
    cfg = load_config(cfg_path)
    if not args.mod:
        args.mod = ""
    # normalize generate race selection
    if getattr(args, "cmd", "") == "generate":
        if not args.all and not args.race:
            ap.error("generate requires --race KEY or --all")
        if args.race and args.race.lower() == "all":
            args.all = True
    return int(args.func(cfg, args) or 0)


if __name__ == "__main__":
    sys.exit(main())
