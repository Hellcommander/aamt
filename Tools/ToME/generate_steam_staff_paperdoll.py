#!/usr/bin/env python3
"""
Generate + install Smog Devil steam-staff paper-doll layers (ToME moddable tiles).

Produces 128x256 RGBA left_/right_steam_staff.png for each race folder, wired as:
  moddable_tile = "special/%s_steam_staff"

  python generate_steam_staff_paperdoll.py
  python generate_steam_staff_paperdoll.py --install-mod --skip-generate
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageOps

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from tome_sd_client import generate_sd_image, get_sd_api_url  # noqa: E402
from tome_sd_pipeline import NEGATIVE, _coverage, _cutout_alpha  # noqa: E402

OUTPUT = Path(r"D:\games\Steam\steamapps\common\Transcendence\Tools\Output\UniqueClassAssets\smog\paperdoll")
SMOG_MOD = Path(r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\addons\tome-smog-devil-class")
GFX_PLAYER = Path(
    r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\source\tome-gfx\data\gfx\shockbolt\player"
)

DOLL_W, DOLL_H = 128, 256
SEED_RIGHT = 74113

PROMPT = (
    "no text, no logo, no watermark, Tales of Maj'Eyal Shockbolt paper-doll weapon layer, "
    "128x256 tall sprite strip, single vertical MAGICTECH STEAMPUNK steam-staff, "
    "brass iron pipe haft, pressure gauge head, teal-green steam vents, violet arcane gem tip, "
    "wizard staff not a sword, thin shaft with clear gap in the middle for the character hand grip, "
    "staff on the LEFT side of the frame leaning slightly, flat matte black background, "
    "bold readable silhouette, game asset overlay"
)

NEGATIVE_EXTRA = (
    ", sword, axe, saw, melee weapon, character, person, hands, arms, body, full scene, "
    "horizontal layout, multiple staves, white background, gray background"
)

RACES = [
    "dwarf_female",
    "dwarf_male",
    "elf_female",
    "elf_male",
    "ghoul",
    "halfling_female",
    "halfling_male",
    "human_female",
    "human_male",
    "ogre_female",
    "ogre_male",
    "orc_male",
    "runic_golem",
    "runic_golem_drolem",
    "skeleton",
    "yeek",
]


def _hand_gap_rows(ref: Image.Image) -> tuple[int, int] | None:
    a = np.array(ref.convert("RGBA"))
    mask = (a[:, :, :3].sum(axis=2) > 15) & (a[:, :, 3] > 20)
    rows = mask.any(axis=1)
    # Prefer a gap in the mid-lower grip band (typical staff dolls ~190-200).
    best = None
    in_gap = False
    start = 0
    for y, occ in enumerate(rows):
        if not occ and not in_gap:
            in_gap = True
            start = y
        elif occ and in_gap:
            if 160 <= start <= 210 and (y - start) >= 3:
                best = (start, y - 1)
            in_gap = False
    return best


def _align_to_ref(src: Image.Image, ref: Image.Image) -> Image.Image:
    """Shift generated staff horizontally toward the reference centroid."""
    s = np.array(src.convert("RGBA"))
    r = np.array(ref.convert("RGBA"))
    sm = (s[:, :, :3].sum(axis=2) > 15) & (s[:, :, 3] > 20)
    rm = (r[:, :, :3].sum(axis=2) > 15) & (r[:, :, 3] > 20)
    if not sm.any() or not rm.any():
        return src
    sy, sx = np.where(sm)
    ry, rx = np.where(rm)
    dx = int(round(rx.mean() - sx.mean()))
    if dx == 0:
        return src
    out = Image.new("RGBA", src.size, (0, 0, 0, 0))
    out.paste(src, (dx, 0), src)
    return out


def _punch_hand_gap(img: Image.Image, gap: tuple[int, int] | None, pad: int = 1) -> Image.Image:
    if not gap:
        return img
    out = img.convert("RGBA")
    y0 = max(0, gap[0] - pad)
    y1 = min(out.size[1] - 1, gap[1] + pad)
    px = out.load()
    for y in range(y0, y1 + 1):
        for x in range(out.size[0]):
            px[x, y] = (0, 0, 0, 0)
    return out


def postprocess_right(raw_path: Path, out_path: Path, ref_path: Path) -> bool:
    rgb = Image.open(raw_path).convert("RGB")
    rgba = _cutout_alpha(rgb)
    if rgba.size != (DOLL_W, DOLL_H):
        rgba = rgba.resize((DOLL_W, DOLL_H), Image.Resampling.LANCZOS)
    cov = _coverage(rgba)
    if cov < 0.02 or cov > 0.55:
        print(f"  bad coverage {cov:.0%} (want thin staff strip)")
        return False

    ref = Image.open(ref_path).convert("RGBA")
    if ref.size != (DOLL_W, DOLL_H):
        ref = ref.resize((DOLL_W, DOLL_H), Image.Resampling.NEAREST)

    rgba = _align_to_ref(rgba, ref)
    rgba = _punch_hand_gap(rgba, _hand_gap_rows(ref))
    rgba = ImageEnhance.Sharpness(rgba).enhance(1.12)
    rgba = ImageEnhance.Contrast(rgba).enhance(1.06)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    rgba.save(out_path)
    return True


def make_left(right_path: Path, left_path: Path) -> None:
    right = Image.open(right_path).convert("RGBA")
    left = ImageOps.mirror(right)
    left_path.parent.mkdir(parents=True, exist_ok=True)
    left.save(left_path)


def generate() -> bool:
    ref = GFX_PLAYER / "human_female" / "right_hand_08_01.png"
    if not ref.exists():
        print(f"Missing reference staff doll: {ref}")
        return False

    right_out = OUTPUT / "right_steam_staff.png"
    left_out = OUTPUT / "left_steam_staff.png"
    raw = Path(tempfile.gettempdir()) / f"steam_staff_doll_{SEED_RIGHT}.png"
    if raw.exists():
        raw.unlink()
    if right_out.exists():
        right_out.unlink()

    print("=== paperdoll / steam_staff (right) ===")
    result = generate_sd_image(
        PROMPT,
        raw,
        negative_prompt=NEGATIVE + NEGATIVE_EXTRA,
        delivery_w=DOLL_W,
        delivery_h=DOLL_H,
        kind="icon",
        seed=SEED_RIGHT,
        guidance_scale=7.4,
        lock_label="steam_staff_paperdoll",
    )
    if not result.ok or not result.output_path:
        print("  FAIL", result.error)
        return False
    if not postprocess_right(Path(result.output_path), right_out, ref):
        return False
    make_left(right_out, left_out)

    meta = {
        "ok": True,
        "asset": "steam_staff_paperdoll",
        "seed": SEED_RIGHT,
        "size": [DOLL_W, DOLL_H],
        "moddable_tile": "special/%s_steam_staff",
        "prompt": PROMPT,
        "right": str(right_out),
        "left": str(left_out),
    }
    (OUTPUT / "steam_staff_paperdoll.meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    print(f"  OK -> {right_out}")
    print(f"  OK -> {left_out}")
    try:
        raw.unlink(missing_ok=True)
    except OSError:
        pass
    return True


def install() -> int:
    right = OUTPUT / "right_steam_staff.png"
    left = OUTPUT / "left_steam_staff.png"
    if not right.exists() or not left.exists():
        print("Missing drafts — generate first")
        return 0

    n = 0
    for race in RACES:
        rel = Path("player") / race / "special"
        for base in (SMOG_MOD / "data" / "gfx", SMOG_MOD / "overload" / "data" / "gfx"):
            dst_dir = base / rel
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(right, dst_dir / "right_steam_staff.png")
            shutil.copy2(left, dst_dir / "left_steam_staff.png")
            n += 2
        print(f"  installed {race}/special/{{left,right}}_steam_staff.png")
    return n


def wire_lua() -> None:
    path = SMOG_MOD / "data" / "general" / "objects" / "steam-staves.lua"
    text = path.read_text(encoding="utf-8")
    if "moddable_tile" in text:
        print("  steam-staves.lua already has moddable_tile")
        return
    needle = '\timage = "object/steam_staff.png",\n'
    insert = (
        '\timage = "object/steam_staff.png",\n'
        '\tmoddable_tile = "special/%s_steam_staff",\n'
    )
    if needle not in text:
        raise SystemExit(f"Could not wire moddable_tile in {path}")
    path.write_text(text.replace(needle, insert, 1), encoding="utf-8")
    print(f"  wired moddable_tile in {path.name}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Steam-staff paper dolls for Smog Devil")
    ap.add_argument("--install-mod", action="store_true")
    ap.add_argument("--skip-generate", action="store_true")
    args = ap.parse_args()

    if not args.skip_generate:
        if not get_sd_api_url(verbose=True):
            print("SD server not ready on :1338")
            return 1
        if not generate():
            return 1

    if args.install_mod:
        n = install()
        wire_lua()
        print(f"Installed {n} doll tiles (data/ + overload/) and wired Lua")
    else:
        print(f"\nDrafts: {OUTPUT}")
        print("Review then: python generate_steam_staff_paperdoll.py --install-mod --skip-generate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
