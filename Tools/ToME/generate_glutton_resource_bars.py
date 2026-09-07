#!/usr/bin/env python3
"""
Generate Glutton Minimalist resource-bar fronts (256x40).

  python generate_glutton_resource_bars.py
  python generate_glutton_resource_bars.py --install-mod --skip-generate
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from tome_sd_client import generate_sd_image, get_sd_api_url  # noqa: E402
from tome_sd_pipeline import NEGATIVE, _coverage, _cutout_alpha  # noqa: E402

import numpy as np

OUTPUT = Path(
    r"D:\games\Steam\steamapps\common\Transcendence\Tools\Output\UniqueClassAssets\glutton\ui\resources"
)
GLUTTON_MOD = Path(
    r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\addons\tome-glutton-remade"
)
HATE_REF = Path(
    r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\source\tome-gfx\data\gfx\ui\resources\front_hate.png"
)

BAR_W, BAR_H = 256, 40
# Preserve wide aspect during SD (plan_sd_size would squash 256x40 badly)
SD_W, SD_H = 1024, 160

STYLE = (
    "exact Tales of Maj'Eyal Minimalist resource bar layout like the Hate meter, "
    "ONE single continuous horizontal frame, left ornamental head, "
    "long dark hollow cylindrical center empty for the fill bar, ornamental right tip, "
    "TWISTED ELDRITCH BODY-HORROR dark fantasy, flat matte black background, "
    "no text no logo no numbers, no second object, no disconnected pieces"
)

ASSETS = [
    (
        "front_satiation",
        86101,
        "flesh-and-bone hunger bar, left end toothy dripping maw with acid-green bile glow, "
        "ribbed meat casing tube, visceral red and green",
        (130, 40, 35),
        (100, 210, 70),
    ),
    (
        "front_amalgam",
        86117,
        "void-purple amalgam bar, left end swirling orchid orb of fused flesh and stolen magic, "
        "dark fused-organ tube, eldritch violet glow",
        (95, 35, 140),
        (190, 90, 230),
    ),
]


def make_dark(src: Image.Image) -> Image.Image:
    dark = ImageEnhance.Brightness(src).enhance(0.58)
    dark = ImageEnhance.Color(dark).enhance(0.72)
    dark = ImageEnhance.Contrast(dark).enhance(1.05)
    return dark


def remaster_onto_hate(
    detail_rgb: Image.Image,
    shift_rgb: tuple[int, int, int],
    glow_rgb: tuple[int, int, int],
) -> Image.Image:
    """Fit SD detail onto the vanilla Hate bar silhouette so layout stays ToME-correct."""
    hate = Image.open(HATE_REF).convert("RGBA")
    detail = _cutout_alpha(detail_rgb, tol=48).resize(hate.size, Image.Resampling.LANCZOS)
    ba = np.array(hate).astype(np.float32)
    da = np.array(detail).astype(np.float32)
    rgb, alpha = ba[:, :, :3], ba[:, :, 3:4]
    lum = rgb.mean(axis=2, keepdims=True)
    target = np.array(shift_rgb, dtype=np.float32).reshape(1, 1, 3)
    mixed = lum * 0.30 + target * 0.70
    hi = (rgb.max(axis=2, keepdims=True) > 180).astype(np.float32)
    mixed = mixed * (1 - hi * 0.4) + rgb * (hi * 0.4)
    xs = np.linspace(1.0, 0.0, ba.shape[1]).reshape(1, -1, 1)
    glow = np.array(glow_rgb, dtype=np.float32).reshape(1, 1, 3)
    edge = (alpha > 40).astype(np.float32) * xs
    mixed = mixed * (1 - edge * 0.4) + glow * (edge * 0.55) + mixed * edge * 0.1
    dmask = (alpha > 40).astype(np.float32) * (da[:, :, 3:4] / 255.0)
    w = np.ones((1, ba.shape[1], 1), dtype=np.float32)
    w[0, :75, 0] = 1.0
    w[0, 75 : ba.shape[1] - 50, 0] = 0.35
    w[0, ba.shape[1] - 50 :, 0] = 0.9
    dmask = dmask * w * 0.75
    rgb2 = mixed * (1 - dmask) + da[:, :, :3] * dmask
    img = Image.fromarray(
        np.clip(np.concatenate([rgb2, alpha], axis=2), 0, 255).astype(np.uint8), "RGBA"
    )
    return ImageEnhance.Sharpness(img).enhance(1.2)


def postprocess_bar(
    raw_path: Path,
    out_path: Path,
    shift_rgb: tuple[int, int, int],
    glow_rgb: tuple[int, int, int],
) -> bool:
    rgb = Image.open(raw_path).convert("RGB")
    rgba = remaster_onto_hate(rgb, shift_rgb, glow_rgb)
    if rgba.size != (BAR_W, BAR_H):
        rgba = rgba.resize((BAR_W, BAR_H), Image.Resampling.LANCZOS)
    cov = _coverage(rgba)
    if cov < 0.15 or cov > 0.85:
        print(f"  bad coverage {cov:.0%}")
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rgba.save(out_path)
    make_dark(rgba).save(out_path.with_name(out_path.stem + "_dark.png"))
    return True


def generate_one(
    name: str,
    seed: int,
    subject: str,
    shift_rgb: tuple[int, int, int],
    glow_rgb: tuple[int, int, int],
) -> bool:
    prompt = f"no text, no logo, no watermark, fantasy RPG UI asset, {subject}, {STYLE}"
    out_path = OUTPUT / f"{name}.png"
    raw = Path(tempfile.gettempdir()) / f"glutton_bar_{name}_{seed}.png"
    if raw.exists():
        raw.unlink()
    if out_path.exists():
        out_path.unlink()
    dark = out_path.with_name(name + "_dark.png")
    if dark.exists():
        dark.unlink()

    print(f"\n=== ui/resources/{name} ===")
    print(f"  {subject[:100]}...")

    result = generate_sd_image(
        prompt,
        raw,
        negative_prompt=NEGATIVE
        + ", sword, axe, vertical layout, square icon, character portrait, full body, "
        "two bars, split objects, disconnected pieces, steampunk, brass gauges, "
        "progress fill drawn in, green fill bar, numbers, letters",
        delivery_w=BAR_W,
        delivery_h=BAR_H,
        kind="icon",
        width=SD_W,
        height=SD_H,
        steps=24,
        seed=seed,
        guidance_scale=7.5,
        lock_label=f"glutton_bar_{name}",
    )
    if not result.ok or not result.output_path:
        print("  FAIL", result.error)
        return False
    if not postprocess_bar(Path(result.output_path), out_path, shift_rgb, glow_rgb):
        return False
    meta = {
        "ok": True,
        "name": name,
        "seed": seed,
        "size": [BAR_W, BAR_H],
        "sd_size": [SD_W, SD_H],
        "prompt": prompt,
        "path": str(out_path),
        "dark": str(dark),
    }
    out_path.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"  OK -> {out_path}")
    print(f"  OK -> {dark}")
    try:
        raw.unlink(missing_ok=True)
    except OSError:
        pass
    return True


def install() -> int:
    if not OUTPUT.exists():
        print("No drafts")
        return 0
    n = 0
    targets = [
        GLUTTON_MOD / "data" / "gfx" / "ui" / "resources",
        GLUTTON_MOD / "overload" / "data" / "gfx" / "ui" / "resources",
        GLUTTON_MOD / "data" / "gfx" / "dark-ui" / "minimalist" / "resources",
        GLUTTON_MOD / "overload" / "data" / "gfx" / "dark-ui" / "minimalist" / "resources",
    ]
    for png in sorted(OUTPUT.glob("*.png")):
        for dst_dir in targets:
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(png, dst_dir / png.name)
            n += 1
        print(f"  installed {png.name}")
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--install-mod", action="store_true")
    ap.add_argument("--skip-generate", action="store_true")
    ap.add_argument("--only", choices=["satiation", "amalgam", "all"], default="all")
    args = ap.parse_args()

    assets = ASSETS
    if args.only == "satiation":
        assets = [ASSETS[0]]
    elif args.only == "amalgam":
        assets = [ASSETS[1]]

    if not args.skip_generate:
        if not get_sd_api_url(verbose=True):
            print("SD server not ready on :1338")
            return 1
        if not HATE_REF.exists():
            print(f"Missing Hate bar reference: {HATE_REF}")
            return 1
        ok = True
        for name, seed, subject, shift, glow in assets:
            if not generate_one(name, seed, subject, shift, glow):
                ok = False
        if not ok:
            return 1

    if args.install_mod:
        n = install()
        print(f"Installed {n} bar tiles into Glutton mod")
    else:
        print(f"\nDrafts: {OUTPUT}")
        print("Review then: python generate_glutton_resource_bars.py --install-mod --skip-generate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
