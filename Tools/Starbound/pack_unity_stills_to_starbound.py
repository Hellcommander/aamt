#!/usr/bin/env python3
"""
Pack Magi-Tech Unity AI stills into Starbound spritesheets + .frames.

Unity could not emit sheets (one still per run). This takes
<mod>/images/*.png, knocks out flat backgrounds, fits each still to a
tile, builds an 8-frame idle-glow strip, writes Starbound metadata, and
optionally installs icons next to the items that need them.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys

from PIL import Image, ImageEnhance, ImageFilter, ImageChops

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
from libs.spritesheet_assembler import pack_strip as _pack_strip_lib, write_starbound_frames

EASTERN = timezone(timedelta(hours=-4))
IDLE_FRAMES = 8

# Conversation batches from 2026-08-09 Unity AI session (UUIDv7 timestamps).
SPELLSTONE_IDS = [
    "spellstone_core_common",
    "spellstone_core_uncommon",
    "spellstone_core_rare",
    "spellstone_core_epic",
    "spellstone_core_legendary",
    "spellstone_fire",
    "spellstone_ice",
    "spellstone_poison",
    "spellstone_electric",
    "spellstone_cosmic",
]

INGREDIENT_IDS = [
    "fire_ruby", "ice_crystal", "lightning_core", "earth_core", "water_pearl",
    "air_wisp", "shadow_wisp", "light_prism", "nature_seed", "cosmic_dust",
    "mana_crystal", "focus_crystal", "resonance_crystal", "prismatic_crystal", "chaos_crystal",
    "stability_catalyst", "power_amplifier", "resonance_tuner", "mana_conductor", "elemental_focus",
    "salamander_scale", "frost_essence", "storm_catalyst", "void_fragment", "solar_essence",
    "mountain_stone", "ocean_essence", "life_essence", "star_fragment", "void_crystal",
    "phoenix_feather", "dimensional_anchor", "temporal_dust", "living_crystal", "quantum_particle",
]

WEAPON_IDS_TALL = ["magitechbasicwand", "magitechbasicstaff"]
WEAPON_IDS_SQUARE = ["magitechbasicorb", "magitechdevice", "magitech_device_upgraded"]
STATION_IDS = ["deviceworkbench", "magitechspellcraftingstation"]
GRENADE_IDS = [
    "alchemical_grenade_launcher", "chemicalgrenade",
    "grenade_fire", "grenade_frost", "grenade_acid", "grenade_storm", "grenade_shadow",
    "chemicalgrenadeammo", "chemicalgrenadeammo_mk2", "chemicalgrenadeammo_mk3",
    "flamelord_grenadegun", "chemicalgrenadelauncher", "chemicalgrenadelauncher_tech2",
    "chemicalgrenadelauncher_tech3",
]
REAGENT_IDS = [
    "reagent_vial", "reagent_fireessence", "reagent_icecrystal",
    "reagent_poisoncloud", "reagent_oilpowder", "reagent_catalyst",
]
MINION_IDS = [
    "magitech_berserker_core", "magitech_elemental_shard",
    "magitech_essence_crystal", "magitech_evolution_catalyst",
]
ARMOR_IDS = ["battlemage", "elementalist", "chronomancer", "runic", "runic_runner"]


def uuidv7_dt(name: str) -> Optional[datetime]:
    stem = Path(name).stem.replace("-", "")
    if len(stem) < 12:
        return None
    try:
        ts_ms = int(stem[:12], 16)
        return datetime.fromtimestamp(ts_ms / 1000, tz=EASTERN)
    except ValueError:
        return None


def knockout_flat_background(img: Image.Image, tolerance: int = 28) -> Image.Image:
    """Make near-uniform corner color transparent (Unity often baked white/grey)."""
    rgba = img.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()
    corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    # Already mostly transparent
    if sum(1 for c in corners if c[3] < 16) >= 3:
        return rgba

    def avg(cs):
        n = len(cs)
        return tuple(sum(c[i] for c in cs) // n for i in range(3))

    bg = avg(corners)
    # Don't key out if corners disagree (real artwork to the edge)
    spread = max(
        max(abs(c[i] - bg[i]) for i in range(3))
        for c in corners
    )
    if spread > 40:
        return rgba

    out = rgba.copy()
    opx = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = opx[x, y]
            if a == 0:
                continue
            if max(abs(r - bg[0]), abs(g - bg[1]), abs(b - bg[2])) <= tolerance:
                opx[x, y] = (r, g, b, 0)
    return out


def crop_content(img: Image.Image, pad: int = 2) -> Image.Image:
    bbox = img.split()[-1].point(lambda v: 255 if v > 12 else 0).getbbox()
    if not bbox:
        return img
    x0, y0, x1, y1 = bbox
    x0 = max(0, x0 - pad)
    y0 = max(0, y0 - pad)
    x1 = min(img.width, x1 + pad)
    y1 = min(img.height, y1 + pad)
    return img.crop((x0, y0, x1, y1))


def fit_tile(img: Image.Image, tw: int, th: int) -> Image.Image:
    canvas = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    if img.width == 0 or img.height == 0:
        return canvas
    scale = min(tw / img.width, th / img.height)
    nw = max(1, int(img.width * scale))
    nh = max(1, int(img.height * scale))
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
    x = (tw - nw) // 2
    y = (th - nh) // 2
    canvas.paste(resized, (x, y), resized)
    return canvas


def dominant_hue(img: Image.Image) -> Tuple[Optional[float], float, float]:
    """Return (hue 0-360 or None, saturation, value) of opaque pixels."""
    small = img.convert("RGBA").resize((32, 32), Image.Resampling.BOX)
    hsv = small.convert("HSV")
    hs, ss, vs, a = hsv.split()[0], hsv.split()[1], hsv.split()[2], small.split()[-1]
    hues, sats, vals = [], [], []
    for h, s, v, al in zip(hs.getdata(), ss.getdata(), vs.getdata(), a.getdata()):
        if al < 40:
            continue
        hues.append(h * 360 / 255)
        sats.append(s / 255)
        vals.append(v / 255)
    if not hues:
        return None, 0.0, 0.0
    # circular mean for hue is overkill; histogram peak is enough
    buckets = [0] * 36
    for h, s in zip(hues, sats):
        if s < 0.12:
            continue
        buckets[int(h / 10) % 36] += 1
    if max(buckets) == 0:
        return None, sum(sats) / len(sats), sum(vals) / len(vals)
    peak = buckets.index(max(buckets))
    return peak * 10 + 5, sum(sats) / len(sats), sum(vals) / len(vals)


def hue_to_element(hue: Optional[float], sat: float) -> Optional[str]:
    if hue is None or sat < 0.18:
        return None
    if hue <= 20 or hue >= 345:
        return "fire"
    if 20 < hue <= 50:
        return "electric"
    if 50 < hue <= 85:
        return "electric"
    if 85 < hue <= 165:
        return "poison"
    if 165 < hue <= 210:
        return "ice"
    if 210 < hue <= 255:
        return "ice"
    if 255 < hue <= 310:
        return "cosmic"
    if 310 < hue < 345:
        return "fire"
    return None


def make_idle_frames(base: Image.Image, count: int = IDLE_FRAMES) -> List[Image.Image]:
    """Stable-silhouette glow pulse. No rotation — Unity stills are the art."""
    glow = base.filter(ImageFilter.GaussianBlur(radius=max(1, base.width // 24)))
    glow = ImageEnhance.Brightness(glow).enhance(1.55)
    glow = ImageEnhance.Color(glow).enhance(1.25)
    frames = []
    for i in range(count):
        t = i / max(1, count)
        pulse = 0.5 + 0.5 * math.sin(t * 2 * math.pi)
        bright = ImageEnhance.Brightness(base).enhance(0.96 + 0.12 * pulse)
        overlay = glow.copy()
        # scale overlay alpha by pulse
        r, g, b, a = overlay.split()
        a = a.point(lambda v, p=pulse: int(v * (0.18 + 0.42 * p)))
        overlay = Image.merge("RGBA", (r, g, b, a))
        frame = Image.alpha_composite(bright, overlay)
        frames.append(frame)
    return frames


def pack_strip(frames: List[Image.Image], dest: Path) -> Tuple[int, int, int]:
    packed = _pack_strip_lib(frames, dest)
    tw, th = packed.tile
    return tw, th, len(frames)


def write_frames(path: Path, tw: int, th: int, n: int, names: Optional[List[str]] = None) -> None:
    if names is None:
        names = [str(i) for i in range(n)]
    write_starbound_frames(path, tw, th, names, alias="idle", extra_aliases={"default": names[0]})


def write_icon_frames(path: Path, tw: int, th: int) -> None:
    data = {
        "aliases": {"default": [0]},
        "frameGrid": {"size": [tw, th], "dimensions": [1, 1]},
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def classify(dt: Optional[datetime], size: Tuple[int, int]) -> str:
    w, h = size
    if dt is None:
        return "unknown"
    t = dt.hour * 60 + dt.minute
    if w >= 1400 or (w == 720 and h == 448):
        return "ui_strip"
    if t < 2 * 60 + 40:
        return "spellstone"
    if t < 3 * 60 + 5:
        return "ingredient"
    if t < 3 * 60 + 18:
        return "weapon"
    if t < 3 * 60 + 40:
        return "station"
    if t < 4 * 60 + 0:
        return "grenade"
    if t < 5 * 60 + 0:
        return "ui"
    if t < 5 * 60 + 12:
        return "minion"
    if t < 5 * 60 + 18:
        return "misc_icon"
    return "mech"


def tile_for(batch: str, size: Tuple[int, int]) -> Tuple[int, int]:
    w, h = size
    if batch == "weapon" and h >= w * 1.4:
        return 32, 64
    if batch in ("mech",):
        return 128, 128
    if batch in ("ui", "ui_strip"):
        return min(w, 64), min(h, 64)
    if batch == "station":
        return 64, 64
    return 64, 64


def install_copies(mod: Path, asset_id: str, icon: Path, sheet: Path, frames: Path, icon_frames: Path) -> List[str]:
    """Copy into known Magi-Tech locations. Returns dest paths written."""
    written = []
    sprites = mod / "assets" / "items" / "sprites"
    if (sprites / f"{asset_id}.frames").exists() or asset_id in SPELLSTONE_IDS + INGREDIENT_IDS + REAGENT_IDS + ARMOR_IDS:
        dest_icon = sprites / f"{asset_id}.png"
        dest_fr = sprites / f"{asset_id}.frames"
        shutil.copy2(icon, dest_icon)
        shutil.copy2(icon_frames, dest_fr)
        shutil.copy2(sheet, sprites / f"{asset_id}_idle.png")
        shutil.copy2(frames, sprites / f"{asset_id}_idle.frames")
        written += [str(dest_icon), str(dest_fr)]

    relatives = {
        "mana_crystal": mod / "items" / "materials" / "spellcrafting" / "mana_crystal.png",
        "magitechbasicwand": mod / "items" / "active" / "weapons" / "wand" / "magitechbasicwand.png",
        "magitechbasicstaff": mod / "items" / "active" / "weapons" / "staff" / "magitechbasicstaff.png",
        "magitechbasicorb": mod / "items" / "active" / "weapons" / "orb" / "magitechbasicorb.png",
        "magitechdevice": mod / "items" / "active" / "weapons" / "magitech" / "magitechdevice.png",
        "magitech_device_upgraded": mod / "items" / "active" / "magitech_device_upgraded.png",
        "deviceworkbench": mod / "objects" / "magitech" / "deviceworkbench" / "deviceworkbenchicon.png",
        "magitechspellcraftingstation": mod / "objects" / "magitech" / "magitechspellcraftingstationicon.png",
    }
    # item-folder relatives matching inventoryIcon filenames
    for folder, names in [
        (mod / "items" / "ammo" / "specializedgrenades", GRENADE_IDS),
        (mod / "items" / "consumable" / "reagents", REAGENT_IDS),
        (mod / "items" / "ammo" / "chemicalgrenadeammo", ["chemicalgrenadeammo", "chemicalgrenadeammo_mk2", "chemicalgrenadeammo_mk3"]),
        (mod / "items" / "weapons" / "alchemicalgrenadelauncher", ["flamelord_grenadegun", "chemicalgrenadelauncher", "chemicalgrenadelauncher_tech2", "chemicalgrenadelauncher_tech3"]),
        (mod / "items" / "magitech" / "minion_enhancements", MINION_IDS),
        (mod / "items" / "materials" / "spellcrafting", ["mana_crystal", "lightning_essence", "ice_essence", "fire_essence", "explosive_core"]),
    ]:
        if asset_id in names:
            dest = folder / f"{asset_id}.png"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(icon, dest)
            written.append(str(dest))

    if asset_id in relatives:
        dest = relatives[asset_id]
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(icon, dest)
        written.append(str(dest))
        # held weapons also get the idle sheet beside the icon
        if asset_id.startswith("magitech"):
            shutil.copy2(sheet, dest.with_name(dest.stem + "_idle.png"))
            shutil.copy2(frames, dest.with_name(dest.stem + "_idle.frames"))
    return written


def assign_ids(records: List[dict]) -> None:
    by_batch: Dict[str, List[dict]] = defaultdict(list)
    for r in records:
        by_batch[r["batch"]].append(r)

    # Spellstones: hue → element, leftover cores by brightness
    stones = by_batch.get("spellstone", [])
    used = set()
    element_map = {
        "fire": "spellstone_fire",
        "ice": "spellstone_ice",
        "poison": "spellstone_poison",
        "electric": "spellstone_electric",
        "cosmic": "spellstone_cosmic",
    }
    for elem, aid in element_map.items():
        cands = [r for r in stones if r.get("element") == elem]
        if not cands:
            continue
        pick = max(cands, key=lambda r: r["sat"] * r["val"])
        pick["asset_id"] = aid
        used.add(id(pick))
    cores = [r for r in stones if id(r) not in used]
    cores.sort(key=lambda r: r["val"])
    for r, aid in zip(cores, SPELLSTONE_IDS[:5]):
        r["asset_id"] = aid
        used.add(id(r))
    extra_i = 1
    for r in stones:
        if "asset_id" not in r:
            r["asset_id"] = f"spellstone_variant_{extra_i:02d}"
            extra_i += 1

    def sequential(batch: str, ids: List[str], prefix: str) -> None:
        rows = by_batch.get(batch, [])
        for i, r in enumerate(rows):
            r["asset_id"] = ids[i] if i < len(ids) else f"{prefix}_{i+1:02d}"

    sequential("ingredient", INGREDIENT_IDS, "ingredient")
    sequential("grenade", GRENADE_IDS, "grenade")
    # classify() has no reagent window; leftover grenade-batch stills are the vials.
    grenade_rows = by_batch.get("grenade", [])
    extra_start = len(GRENADE_IDS)
    for i, r in enumerate(grenade_rows[extra_start:], start=0):
        if i < len(REAGENT_IDS):
            r["batch"] = "reagent"
            r["asset_id"] = REAGENT_IDS[i]
    sequential("reagent", REAGENT_IDS, "reagent")
    sequential("minion", MINION_IDS, "minion")
    sequential("station", STATION_IDS, "station")
    sequential("ui", [], "ui")
    sequential("mech", [], "mech")
    sequential("misc_icon", ARMOR_IDS, "icon")
    sequential("ui_strip", [], "ui_strip")

    weapons = by_batch.get("weapon", [])
    tall = [r for r in weapons if r["size"][1] >= r["size"][0] * 1.4]
    square = [r for r in weapons if r not in tall]
    for i, r in enumerate(tall):
        r["asset_id"] = WEAPON_IDS_TALL[i] if i < len(WEAPON_IDS_TALL) else f"weapon_tall_{i+1:02d}"
    for i, r in enumerate(square):
        r["asset_id"] = WEAPON_IDS_SQUARE[i] if i < len(WEAPON_IDS_SQUARE) else f"weapon_{i+1:02d}"

    for r in records:
        r.setdefault("asset_id", Path(r["source"]).stem)


def process(mod: Path, install: bool, frame_count: int) -> dict:
    src = mod / "images"
    out_root = mod / "assets" / "magitech" / "unity_sheets"
    out_root.mkdir(parents=True, exist_ok=True)

    files = sorted(src.glob("*.png"), key=lambda p: (uuidv7_dt(p.name) or datetime.min.replace(tzinfo=EASTERN), p.name))
    records = []
    for f in files:
        if f.name.lower().startswith("base-asset"):
            continue
        with Image.open(f) as im:
            size = im.size
        dt = uuidv7_dt(f.name)
        batch = classify(dt, size)
        records.append({
            "source": f.name,
            "path": str(f),
            "size": size,
            "when": dt.isoformat() if dt else None,
            "batch": batch,
        })

    # Hue pass for spellstones (need pixels)
    for r in records:
        if r["batch"] != "spellstone":
            continue
        with Image.open(r["path"]) as im:
            cleaned = crop_content(knockout_flat_background(im))
            hue, sat, val = dominant_hue(cleaned)
        r["hue"] = hue
        r["sat"] = sat
        r["val"] = val
        r["element"] = hue_to_element(hue, sat)

    assign_ids(records)

    summary = defaultdict(int)
    for r in records:
        src_img = Image.open(r["path"])
        cleaned = crop_content(knockout_flat_background(src_img))
        src_img.close()

        if r["batch"] == "ui_strip":
            dest_dir = out_root / "ui_strip"
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f"{r['asset_id']}.png"
            cleaned.save(dest, "PNG")
            r["outputs"] = {"raw": str(dest)}
            summary["ui_strip_copied"] += 1
            continue

        tw, th = tile_for(r["batch"], r["size"])
        tile = fit_tile(cleaned, tw, th)
        frames = make_idle_frames(tile, frame_count)
        dest_dir = out_root / r["batch"]
        sheet_path = dest_dir / f"{r['asset_id']}_idle.png"
        frames_path = dest_dir / f"{r['asset_id']}_idle.frames"
        icon_path = dest_dir / f"{r['asset_id']}.png"
        icon_frames_path = dest_dir / f"{r['asset_id']}.frames"
        pack_strip(frames, sheet_path)
        write_frames(frames_path, tw, th, frame_count)
        tile.save(icon_path, "PNG")
        write_icon_frames(icon_frames_path, tw, th)
        r["outputs"] = {
            "icon": str(icon_path),
            "iconFrames": str(icon_frames_path),
            "sheet": str(sheet_path),
            "sheetFrames": str(frames_path),
            "tile": [tw, th],
        }
        if install:
            r["installed"] = install_copies(
                mod, r["asset_id"], icon_path, sheet_path, frames_path, icon_frames_path
            )
        summary[r["batch"]] += 1

    manifest_path = out_root / "manifest.json"
    serializable = []
    for r in records:
        row = dict(r)
        row["size"] = list(row["size"])
        serializable.append(row)
    manifest_path.write_text(json.dumps({
        "generatedAt": datetime.now(tz=EASTERN).isoformat(),
        "sourceDir": str(src),
        "outputDir": str(out_root),
        "frameCount": frame_count,
        "counts": dict(summary),
        "assets": serializable,
    }, indent=2) + "\n", encoding="utf-8")
    return {"manifest": str(manifest_path), "counts": dict(summary), "total": len(records)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Pack Unity stills into Starbound spritesheets")
    ap.add_argument(
        "--mod-path",
        default=r"F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    )
    ap.add_argument("--install", action="store_true", help="Copy mapped icons into item/object paths")
    ap.add_argument("--frames", type=int, default=IDLE_FRAMES)
    args = ap.parse_args()
    mod = Path(args.mod_path)
    if not (mod / "images").is_dir():
        raise SystemExit(f"images folder missing: {mod / 'images'}")
    result = process(mod, args.install, args.frames)
    print("[OK] Packed Unity stills -> Starbound sheets")
    print(f"  Manifest: {result['manifest']}")
    print(f"  Total: {result['total']}")
    for k, v in sorted(result["counts"].items()):
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
