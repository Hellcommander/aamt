#!/usr/bin/env python3
"""
Expand packed Magi-Tech Unity stills into full OpenStarbound action cycles.

Reads icons already written by pack_unity_stills_to_starbound.py and emits:
  - combined atlas + .frames with vanilla names (idle.1, walk.1, fire.1, ...)
  - per-cycle strips (mech form JSON / object orientations)
  - .animation state machines matching basegame wand / mech / object layouts
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

from starbound_action_cycles import (
    cycles_for_batch,
    pack_named_atlas,
    pack_strip,
    render_cycle,
    write_strip_frames,
    build_active_item_animation,
    build_object_animation,
    build_mech_animation,
)

SKIP_BATCHES = {"ui", "ui_strip"}
CYCLE_SUFFIXES = (
    "idle", "walk", "run", "jump", "fall", "fire", "attack", "hurt", "death",
    "charge", "boost", "move", "open", "close", "working", "altFire",
    "spark", "discharge", "cooldown", "sheet",
)

WEAPON_PART = {
    "magitechbasicwand": "wand",
    "magitechbasicstaff": "staff",
    "magitechbasicorb": "orb",
    "magitechdevice": "device",
    "magitech_device_upgraded": "device",
}

WEAPON_INSTALL = {
    "magitechbasicwand": "items/active/weapons/wand",
    "magitechbasicstaff": "items/active/weapons/staff",
    "magitechbasicorb": "items/active/weapons/orb",
    "magitechdevice": "items/active/weapons/magitech",
    "magitech_device_upgraded": "items/active",
}

OBJECT_INSTALL = {
    "deviceworkbench": "objects/magitech/deviceworkbench",
    "magitechspellcraftingstation": "objects/magitech",
}


def list_icons(sheets_root: Path):
    """Prefer the packer manifest so names like spellstone_fire are not skipped."""
    manifest = sheets_root / "manifest.json"
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        for rec in data.get("assets", []):
            batch = rec.get("batch")
            if batch in SKIP_BATCHES:
                continue
            icon = rec.get("outputs", {}).get("icon")
            asset_id = rec.get("asset_id")
            if icon and asset_id and Path(icon).exists():
                yield batch, asset_id, Path(icon)
        return
    for batch_dir in sorted(p for p in sheets_root.iterdir() if p.is_dir()):
        batch = batch_dir.name
        if batch in SKIP_BATCHES:
            continue
        for png in sorted(batch_dir.glob("*.png")):
            stem = png.stem
            if any(stem.endswith(f"_{s}") for s in CYCLE_SUFFIXES):
                continue
            yield batch, stem, png


def expand_one(icon_path: Path, batch: str, asset_id: str, out_dir: Path) -> dict:
    cycles_spec = cycles_for_batch(batch)
    with Image.open(icon_path) as im:
        base = im.convert("RGBA")
    rendered = {}
    prefixes = {}
    for spec in cycles_spec:
        frames = render_cycle(base, spec)
        rendered[spec.name] = frames
        prefixes[spec.name] = spec.vanilla_prefix
        strip = out_dir / f"{asset_id}_{spec.name}.png"
        pack_strip(frames, strip)
        write_strip_frames(
            out_dir / f"{asset_id}_{spec.name}.frames",
            frames[0].width, frames[0].height, spec.vanilla_prefix, len(frames),
        )

    atlas = out_dir / f"{asset_id}_sheet.png"
    frames_path = out_dir / f"{asset_id}_sheet.frames"
    tw, th = pack_named_atlas(rendered, prefixes, atlas, frames_path)

    anim_path = out_dir / f"{asset_id}.animation"
    rel = f"{asset_id}_sheet.png"
    if batch in ("weapon", "grenade"):
        part = WEAPON_PART.get(asset_id, "weapon")
        anim = build_active_item_animation(part, rel, cycles_spec)
    elif batch == "station":
        anim = build_object_animation(asset_id, rel)
    elif batch in ("mech", "minion"):
        anim = build_mech_animation(rel)
    else:
        anim = build_active_item_animation("body", rel, cycles_spec)
    anim_path.write_text(json.dumps(anim, indent=2) + "\n", encoding="utf-8")
    return {
        "asset_id": asset_id,
        "batch": batch,
        "cycles": [c.name for c in cycles_spec],
        "atlas": str(atlas),
        "animation": str(anim_path),
        "tile": [tw, th],
    }


def install(mod: Path, asset_id: str, batch: str, out_dir: Path) -> list:
    written = []
    sheet = out_dir / f"{asset_id}_sheet.png"
    frames = out_dir / f"{asset_id}_sheet.frames"
    anim = out_dir / f"{asset_id}.animation"

    if asset_id in WEAPON_INSTALL:
        dest = mod / WEAPON_INSTALL[asset_id]
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(sheet, dest / f"{asset_id}_sheet.png")
        shutil.copy2(frames, dest / f"{asset_id}_sheet.frames")
        part = WEAPON_PART.get(asset_id, "weapon")
        # Shared magitechdevice.animation next to the weapon, vanilla wand layout
        anim_out = dest / "magitechdevice.animation"
        rel = f"{asset_id}_sheet.png"
        from starbound_action_cycles import cycles_for_batch as cyc, build_active_item_animation as bai
        anim_out.write_text(json.dumps(bai(part, rel, cyc(batch)), indent=2) + "\n", encoding="utf-8")
        written.append(str(anim_out))

    if asset_id in OBJECT_INSTALL:
        dest = mod / OBJECT_INSTALL[asset_id]
        dest.mkdir(parents=True, exist_ok=True)
        # Object orientations use deviceworkbench.png:<color>.<frame> — idle strip named default.N
        idle_strip = out_dir / f"{asset_id}_idle.png"
        idle_frames = out_dir / f"{asset_id}_idle.frames"
        if idle_strip.exists():
            shutil.copy2(idle_strip, dest / f"{asset_id}.png")
            shutil.copy2(idle_frames, dest / f"{asset_id}.frames")
        shutil.copy2(sheet, dest / f"{asset_id}_sheet.png")
        shutil.copy2(frames, dest / f"{asset_id}_sheet.frames")
        anim_out = dest / f"{asset_id}.animation"
        shutil.copy2(anim, anim_out)
        written.append(str(anim_out))
        if asset_id == "deviceworkbench":
            shutil.copy2(anim, dest / "deviceworkbench.animation")

    if batch in ("grenade", "reagent", "minion"):
        dest_map = {
            "grenade": [
                mod / "items" / "ammo" / "specializedgrenades",
                mod / "items" / "ammo" / "chemicalgrenadeammo",
                mod / "items" / "weapons" / "alchemicalgrenadelauncher",
            ],
            "reagent": [mod / "items" / "consumable" / "reagents"],
            "minion": [mod / "items" / "magitech" / "minion_enhancements"],
        }
        for dest in dest_map[batch]:
            dest.mkdir(parents=True, exist_ok=True)
            if sheet.exists():
                shutil.copy2(sheet, dest / f"{asset_id}_sheet.png")
                shutil.copy2(frames, dest / f"{asset_id}_sheet.frames")
            icon = out_dir / f"{asset_id}.png"
            if icon.exists():
                shutil.copy2(icon, dest / f"{asset_id}.png")
            written.append(str(dest / f"{asset_id}.png"))

    if batch == "mech":
        forms = mod / "sprites" / "forms"
        forms.mkdir(parents=True, exist_ok=True)
        for spec in cycles_for_batch("mech"):
            src = out_dir / f"{asset_id}_{spec.name}.png"
            if src.exists():
                shutil.copy2(src, forms / f"{asset_id}_{spec.name}.png")
                shutil.copy2(
                    out_dir / f"{asset_id}_{spec.name}.frames",
                    forms / f"{asset_id}_{spec.name}.frames",
                )
        shutil.copy2(anim, forms / f"{asset_id}.animation")
        sheet = out_dir / f"{asset_id}_sheet.png"
        sheet_frames = out_dir / f"{asset_id}_sheet.frames"
        if sheet.exists():
            shutil.copy2(sheet, forms / f"{asset_id}_sheet.png")
        if sheet_frames.exists():
            shutil.copy2(sheet_frames, forms / f"{asset_id}_sheet.frames")
        written.append(str(forms / f"{asset_id}.animation"))
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description="Expand Unity stills into Starbound action cycles")
    ap.add_argument(
        "--mod-path",
        default=r"F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    )
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--batches", default="", help="Comma list to limit (weapon,mech,station,...)")
    args = ap.parse_args()
    mod = Path(args.mod_path)
    sheets = mod / "assets" / "magitech" / "unity_sheets"
    if not sheets.is_dir():
        raise SystemExit(f"Packed sheets missing: {sheets}")

    allow = {b.strip() for b in args.batches.split(",") if b.strip()}
    results = []
    for batch, asset_id, icon in list_icons(sheets):
        if allow and batch not in allow:
            continue
        out_dir = sheets / batch
        info = expand_one(icon, batch, asset_id, out_dir)
        if args.install:
            info["installed"] = install(mod, asset_id, batch, out_dir)
        results.append(info)
        print(f"  [{batch}] {asset_id}: {', '.join(info['cycles'])}")

    manifest = sheets / "action_cycles_manifest.json"
    manifest.write_text(json.dumps({"count": len(results), "assets": results}, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] Action cycles for {len(results)} assets")
    print(f"  Manifest: {manifest}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    raise SystemExit(main())
