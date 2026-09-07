#!/usr/bin/env python3
"""
Generate ToME subclass birth icons (class-icons/{name}_128_bg.png + _32_bg.png).

Uses SD3.5 (:1338) with hand-tuned prompts matching vanilla ToME class-icon style,
then applies the shared vanilla rounded-corner alpha mask.

  python generate_class_icons.py
  python generate_class_icons.py --class smog_devil --variations 4
  python generate_class_icons.py --install-mod
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from tome_sd_client import generate_sd_image, get_sd_api_url  # noqa: E402

OUTPUT = Path(r"D:\games\Steam\steamapps\common\Transcendence\Tools\Output\ClassIcons")
VANILLA_MASK_128 = Path(
    r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\source\tome-gfx\data\gfx\class-icons\corruptor_128_bg.png"
)
VANILLA_MASK_32 = Path(
    r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\source\tome-gfx\data\gfx\class-icons\corruptor_32_bg.png"
)

NEGATIVE = (
    "text, logo, watermark, letters, words, ui chrome, thick outer border frame, "
    "photograph, photorealistic, 3d render, plastic, cluttered background, "
    "gradient background, white background, scene, landscape, full body standing, "
    "blurry, lowres, jpeg artifacts, multiple faces, collage"
)

CLASSES = {
    "smog_devil": {
        "display_name": "Smog Devil",
        "mod": Path(r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\addons\tome-smog-devil-class"),
        "file_stem": "smog_devil",
        # Steam+arcane MAGIC caster (steam-staff) — NOT melee. Resources: steam, mana, vim.
        "prompts": [
            (
                "Tales of Maj'Eyal class icon, dark fantasy game UI icon, bold black outlines, "
                "high contrast painted illustration, single centered composition on flat matte black background, "
                "STEAM-STAFF MAGE not melee: brass-and-iron steamtech wizard staff with pressure gauges, "
                "tip glowing violet arcane gem, thick toxic gray-green smog and white steam venting from pipes, "
                "horned devil silhouette formed inside the smog, corrupt purple vim sparks, "
                "no sword no axe no saw no dagger, readable silhouette, sharp, no text, no logo"
            ),
            (
                "Tales of Maj'Eyal class icon style like alchemist and archmage icons, magic caster emblem, "
                "hooded smog devil warlock with brass horns and teal eyes, vertical steam-staff with arcane focus, "
                "industrial smog and violet mana swirl, palette soot black toxic teal brass gold arcane violet, "
                "flat matte black background, bold outline, crisp game icon, no melee weapons, no text"
            ),
            (
                "ToME RPG subclass icon, steam and arcane magic theme, steamtech mage staff and focus lens, "
                "wrapped in green toxic smog, devilish brass horns motif, violet mana glow, "
                "dark fantasy, thick ink outlines, centered, black background, no blades, no text"
            ),
        ],
        "seeds": [71001, 71017, 71033, 71049, 71065, 71081],
    },
    "glutton": {
        "display_name": "Glutton",
        "mod": Path(r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\addons\tome-glutton-remade"),
        "file_stem": "glutton",
        # Accurate to birth desc: eldritch maw, consume flesh/essence, satiation, demented horror
        "prompts": [
            (
                "Tales of Maj'Eyal class icon, dark fantasy game UI icon, bold black outlines, "
                "high contrast painted illustration, single centered composition on flat matte black background, "
                "eldritch gluttonous horror head that is mostly a massive gaping maw of jagged teeth, "
                "bloated fleshy cheeks dripping neon green bile and acid, "
                "multiple hungry eyes, dark purple void glow inside the throat, "
                "small writhing tentacles framing the mouth, visceral demented cult aesthetic, "
                "readable silhouette, sharp, no text, no logo"
            ),
            (
                "Tales of Maj'Eyal class icon style like corruptor and writhing one icons, "
                "endless hungry Maw symbol: circular ring of teeth around a black void stomach, "
                "lime-green digestive slime dripping downward, bruised purple-red flesh, "
                "tiny bone fragments orbiting, flat matte black background, bold outline, crisp game icon, no text"
            ),
            (
                "ToME RPG subclass icon, bloated eldritch devourer face with enormous open mouth, "
                "green satiation slime, crimson gums, void-purple tongue, hunger made flesh, "
                "dark fantasy, thick ink outlines, centered, black background, no text"
            ),
        ],
        "seeds": [82001, 82017, 82033, 82049, 82065, 82081],
    },
}


def _load_masks() -> tuple[Image.Image, Image.Image]:
    m128 = Image.open(VANILLA_MASK_128).convert("RGBA").split()[3]
    m32 = Image.open(VANILLA_MASK_32).convert("RGBA").split()[3]
    return m128, m32


def _force_black_bg(rgb: Image.Image, thresh: int = 28) -> Image.Image:
    """Crush near-black / near-white corner wash to pure black so the cutout matches vanilla."""
    px = rgb.load()
    w, h = rgb.size
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if r <= thresh and g <= thresh and b <= thresh:
                px[x, y] = (0, 0, 0)
    return rgb


def _compose_class_icon(raw: Image.Image, mask: Image.Image, size: int) -> Image.Image:
    rgb = raw.convert("RGB")
    if rgb.size != (size, size):
        rgb = rgb.resize((size, size), Image.Resampling.LANCZOS)
    rgb = _force_black_bg(rgb)
    rgb = ImageEnhance.Sharpness(rgb).enhance(1.15)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.08)
    # Slight unsharp for 32px readability path
    if size <= 32:
        rgb = rgb.filter(ImageFilter.SHARPEN)
    rgba = rgb.convert("RGBA")
    if mask.size != (size, size):
        mask = mask.resize((size, size), Image.Resampling.NEAREST)
    rgba.putalpha(mask)
    return rgba


def generate_candidate(
    class_key: str,
    prompt: str,
    seed: int,
    out_dir: Path,
    mask128: Image.Image,
    mask32: Image.Image,
    variation_idx: int,
) -> dict:
    stem = CLASSES[class_key]["file_stem"]
    raw_path = out_dir / "raw" / f"{stem}_v{variation_idx}_s{seed}.png"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    if raw_path.exists():
        raw_path.unlink()

    print(f"\n=== {CLASSES[class_key]['display_name']} variation {variation_idx} seed={seed} ===")
    print(f"  prompt: {prompt[:140]}...")

    result = generate_sd_image(
        prompt,
        raw_path,
        negative_prompt=NEGATIVE,
        delivery_w=128,
        delivery_h=128,
        kind="icon",
        seed=seed,
        guidance_scale=7.2,
        lock_label=f"class_icon_{stem}_{variation_idx}",
    )
    if not result.ok or not result.output_path:
        return {"ok": False, "error": result.error or "SD failed", "seed": seed}

    raw = Image.open(result.output_path)
    icon128 = _compose_class_icon(raw, mask128, 128)
    # Prefer downscale from finished 128 (keeps frame consistency) for 32
    icon32 = _compose_class_icon(icon128.convert("RGB"), mask32, 32)

    cand_dir = out_dir / "candidates" / stem
    cand_dir.mkdir(parents=True, exist_ok=True)
    p128 = cand_dir / f"{stem}_128_bg_v{variation_idx}.png"
    p32 = cand_dir / f"{stem}_32_bg_v{variation_idx}.png"
    icon128.save(p128)
    icon32.save(p32)

    # Also write "best pick" slots updated later
    meta = {
        "ok": True,
        "class": class_key,
        "variation": variation_idx,
        "seed": seed,
        "prompt": prompt,
        "path_128": str(p128),
        "path_32": str(p32),
        "settings": result.settings,
    }
    p128.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"  OK -> {p128.name} / {p32.name}")
    return meta


def pick_best_and_finalize(class_key: str, metas: list[dict], out_dir: Path) -> dict | None:
    """Pick first successful variation as default best (manual override via --pick)."""
    ok = [m for m in metas if m.get("ok")]
    if not ok:
        return None
    best = ok[0]
    stem = CLASSES[class_key]["file_stem"]
    final = out_dir / "final"
    final.mkdir(parents=True, exist_ok=True)
    dst128 = final / f"{stem}_128_bg.png"
    dst32 = final / f"{stem}_32_bg.png"
    shutil.copy2(best["path_128"], dst128)
    shutil.copy2(best["path_32"], dst32)
    best_meta = dict(best)
    best_meta["final_128"] = str(dst128)
    best_meta["final_32"] = str(dst32)
    (final / f"{stem}.meta.json").write_text(json.dumps(best_meta, indent=2), encoding="utf-8")
    return best_meta


def install_to_mod(class_key: str, out_dir: Path) -> int:
    stem = CLASSES[class_key]["file_stem"]
    mod = CLASSES[class_key]["mod"]
    src128 = out_dir / "final" / f"{stem}_128_bg.png"
    src32 = out_dir / "final" / f"{stem}_32_bg.png"
    if not src128.exists() or not src32.exists():
        print(f"  Missing finals for {stem}")
        return 0
    dst = mod / "data" / "gfx" / "class-icons"
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src128, dst / f"{stem}_128_bg.png")
    shutil.copy2(src32, dst / f"{stem}_32_bg.png")
    print(f"  Installed -> {dst}")
    return 2


def set_pick(class_key: str, variation: int, out_dir: Path) -> bool:
    stem = CLASSES[class_key]["file_stem"]
    cand = out_dir / "candidates" / stem
    p128 = cand / f"{stem}_128_bg_v{variation}.png"
    p32 = cand / f"{stem}_32_bg_v{variation}.png"
    if not p128.exists() or not p32.exists():
        print(f"Variation {variation} not found for {stem}")
        return False
    final = out_dir / "final"
    final.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p128, final / f"{stem}_128_bg.png")
    shutil.copy2(p32, final / f"{stem}_32_bg.png")
    meta_src = p128.with_suffix(".meta.json")
    if meta_src.exists():
        shutil.copy2(meta_src, final / f"{stem}.meta.json")
    print(f"Selected {stem} variation {variation} as final")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate ToME class-icons for Smog Devil / Glutton")
    ap.add_argument("--class", dest="class_key", choices=["smog_devil", "glutton", "all"], default="all")
    ap.add_argument("--variations", type=int, default=3, help="Candidates per class (max 6)")
    ap.add_argument("--install-mod", action="store_true", help="Copy finals into live addons")
    ap.add_argument("--pick", type=int, default=-1, help="Select candidate variation index as final")
    ap.add_argument("--pick-class", choices=["smog_devil", "glutton"], default=None)
    args = ap.parse_args()

    if not get_sd_api_url(verbose=True) and not args.install_mod and args.pick < 0:
        print("SD server not ready on :1338")
        return 1

    OUTPUT.mkdir(parents=True, exist_ok=True)
    mask128, mask32 = _load_masks()

    keys = ["smog_devil", "glutton"] if args.class_key == "all" else [args.class_key]

    if args.pick >= 0:
        pk = args.pick_class or (keys[0] if len(keys) == 1 else None)
        if not pk:
            print("--pick requires --pick-class when generating all")
            return 1
        if not set_pick(pk, args.pick, OUTPUT):
            return 1
        if args.install_mod:
            install_to_mod(pk, OUTPUT)
        return 0

    if args.install_mod and args.variations == 0:
        n = 0
        for k in keys:
            n += install_to_mod(k, OUTPUT)
        return 0 if n else 1

    for key in keys:
        cfg = CLASSES[key]
        n_var = max(1, min(args.variations, len(cfg["seeds"])))
        metas: list[dict] = []
        for i in range(n_var):
            prompt = cfg["prompts"][i % len(cfg["prompts"])]
            seed = cfg["seeds"][i]
            meta = generate_candidate(key, prompt, seed, OUTPUT, mask128, mask32, i)
            metas.append(meta)
        best = pick_best_and_finalize(key, metas, OUTPUT)
        if not best:
            print(f"FAILED: no successful candidates for {key}")
            continue
        print(f"Finalized {cfg['display_name']} -> variation {best['variation']}")
        if args.install_mod:
            install_to_mod(key, OUTPUT)

    print(f"\nDrafts: {OUTPUT}")
    print("Review candidates/, then: python generate_class_icons.py --pick N --pick-class smog_devil --install-mod")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
