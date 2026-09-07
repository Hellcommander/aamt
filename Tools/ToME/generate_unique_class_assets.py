#!/usr/bin/env python3
"""
Unique class assets with distinct art directions:

  Smog Devil → magictech / steampunk
  Glutton    → horror twisted

  python generate_unique_class_assets.py
  python generate_unique_class_assets.py --install-mod
  python generate_unique_class_assets.py --install-mod --skip-generate
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from tome_sd_client import generate_sd_image, get_sd_api_url  # noqa: E402
from tome_sd_pipeline import NEGATIVE, _coverage, _cutout_alpha  # noqa: E402

OUTPUT = Path(r"D:\games\Steam\steamapps\common\Transcendence\Tools\Output\UniqueClassAssets")
SMOG_MOD = Path(r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\addons\tome-smog-devil-class")
GLUTTON_MOD = Path(r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\addons\tome-glutton-remade")

STYLE = {
    "smog": (
        "Tales of Maj'Eyal 64x64 RPG icon, MAGICTECH STEAMPUNK dark fantasy, "
        "brass iron copper pipes pressure gauges valves glowing arcane crystals, "
        "toxic teal-green steam mixed with violet mana, bold black ink outlines, "
        "single centered subject, flat matte black background, sharp readable at 64px, no text no logo"
    ),
    "glutton": (
        "Tales of Maj'Eyal 64x64 RPG icon, TWISTED ELDRITCH BODY-HORROR dark fantasy, "
        "bloated flesh jagged teeth green bile void-purple hunger visceral demented cult, "
        "bold black ink outlines, single centered subject, flat matte black background, "
        "sharp readable at 64px, no text no logo"
    ),
}

SMOG_ASSETS = [
    ("object", "steam_staff", 74001,
     "vertical brass-and-iron steamtech wizard staff with pipe haft, pressure gauge, "
     "venting toxic-green steam, violet arcane gem tip, mage weapon not a sword"),
    ("object", "refined_arcane_gem", 74017,
     "faceted violet-teal arcane gem ammo in a brass steamtech collar with tiny vents"),
    ("effects", "steam_overload", 74033,
     "bursting pressurized steam overload aura from brass pipe ruptures"),
    ("effects", "steam_mana_converter", 74049,
     "brass gear converter ring turning violet mana into white steam jets"),
    ("effects", "steam_mana_symphony", 74065,
     "interlocking concentric rings of teal steam and violet arcane light"),
    ("effects", "smog_devil_apotheosis", 74081,
     "horned brass devil silhouette in toxic smog with violet arcane corona"),
    ("effects", "steam_staff_charged", 74097,
     "charged steam-staff tip overflowing with teal steam and violet sparks"),
]

GLUTTON_ASSETS = [
    ("object/artifact", "ring_of_kindred_horrors", 85001,
     "eldritch ring of twisted living flesh with pulsing veins and a tiny toothy maw, void-purple glow"),
    ("effects", "glutton_digesting", 85017,
     "stomach-maw digesting a silhouette, acid-green bile dripping"),
    ("effects", "glutton_starving", 85033,
     "emaciated horror face with huge empty maw and hollow purple eyes"),
    ("effects", "glutton_hungry", 85049,
     "salivating toothy maw dripping green bile, urgent hunger"),
    ("effects", "glutton_sated", 85065,
     "bloated satisfied horror gut sealed with a grinning maw, green satiation glow"),
    ("effects", "glutton_maws_mark", 85081,
     "cursed brand: circular ring of teeth around a purple void, the Endless Maw mark"),
    ("effects", "glutton_absorbed_skill", 85097,
     "stolen skill rune half-dissolved into fleshy tendrils"),
    ("effects", "glutton_amalgam", 85113,
     "amalgam core organ: swirling merged resource orbs inside a fleshy sphere"),
]


def postprocess_64(raw_path: Path, out_path: Path) -> bool:
    rgb = Image.open(raw_path).convert("RGB")
    rgba = _cutout_alpha(rgb)
    cov = _coverage(rgba)
    if cov < 0.06 or cov > 0.97:
        print(f"  bad coverage {cov:.0%}")
        return False
    if rgba.size != (64, 64):
        rgba = rgba.resize((64, 64), Image.Resampling.LANCZOS)
    rgba = ImageEnhance.Sharpness(rgba).enhance(1.15)
    rgba = ImageEnhance.Contrast(rgba).enhance(1.08)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rgba.save(out_path)
    return True


def generate_one(mod_key: str, subdir: str, name: str, seed: int, subject: str) -> bool:
    prompt = (
        f"no text, no logo, no watermark, fantasy RPG game icon, {subject}, {STYLE[mod_key]}"
    )
    out_path = OUTPUT / mod_key / subdir / f"{name}.png"
    raw = Path(tempfile.gettempdir()) / f"unique_{mod_key}_{name}_{seed}.png"
    if raw.exists():
        raw.unlink()
    if out_path.exists():
        out_path.unlink()

    print(f"\n=== {mod_key}/{subdir}/{name} ===")
    print(f"  [{ 'magictech-steampunk' if mod_key=='smog' else 'horror-twisted' }] {subject[:90]}...")

    result = generate_sd_image(
        prompt,
        raw,
        negative_prompt=NEGATIVE + (
            ", sword, axe, saw, melee weapon" if mod_key == "smog"
            else ", steampunk, brass gears, cute"
        ),
        delivery_w=64,
        delivery_h=64,
        kind="icon",
        seed=seed,
        guidance_scale=7.3,
        lock_label=f"unique_{mod_key}_{name}",
    )
    if not result.ok or not result.output_path:
        print("  FAIL", result.error)
        return False
    if not postprocess_64(Path(result.output_path), out_path):
        return False
    meta = {
        "ok": True,
        "mod": mod_key,
        "name": name,
        "subdir": subdir,
        "seed": seed,
        "art_direction": "magictech-steampunk" if mod_key == "smog" else "horror-twisted",
        "prompt": prompt,
        "path": str(out_path),
    }
    out_path.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"  OK -> {out_path}")
    try:
        raw.unlink(missing_ok=True)
    except OSError:
        pass
    return True


def install_mod(mod_key: str) -> int:
    mod = SMOG_MOD if mod_key == "smog" else GLUTTON_MOD
    src_root = OUTPUT / mod_key
    if not src_root.exists():
        print(f"No drafts for {mod_key}")
        return 0
    n = 0
    for png in src_root.rglob("*.png"):
        rel = png.relative_to(src_root)
        for base in (mod / "data" / "gfx", mod / "overload" / "data" / "gfx"):
            dst = base / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(png, dst)
            meta = png.with_suffix(".meta.json")
            if meta.exists():
                shutil.copy2(meta, dst.with_suffix(".meta.json"))
        n += 1
        print(f"  installed {rel}")
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description="Unique Smog Devil / Glutton assets")
    ap.add_argument("--install-mod", action="store_true")
    ap.add_argument("--skip-generate", action="store_true")
    ap.add_argument("--class", dest="which", choices=["smog", "glutton", "all"], default="all")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    keys = ["smog", "glutton"] if args.which == "all" else [args.which]
    catalog = {"smog": SMOG_ASSETS, "glutton": GLUTTON_ASSETS}

    if not args.skip_generate:
        if not get_sd_api_url(verbose=True):
            print("SD server not ready on :1338")
            return 1
        for key in keys:
            assets = catalog[key]
            if args.limit:
                assets = assets[: args.limit]
            for subdir, name, seed, subject in assets:
                generate_one(key, subdir, name, seed, subject)

    if args.install_mod:
        total = sum(install_mod(k) for k in keys)
        print(f"Installed {total} unique assets into mods (data/ + overload/)")
    else:
        print(f"\nDrafts: {OUTPUT}")
        print("Review then: python generate_unique_class_assets.py --install-mod --skip-generate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
