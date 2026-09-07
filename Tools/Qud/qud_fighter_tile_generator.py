#!/usr/bin/env python3
"""
Choose Your Fighter — CoQ player tile replacement generator.

Follows Caves of Qud tile rules (wiki: Modding:Tiles / Custom Player Tiles):

  Default (classic shader):
    - Size 16×24 (width×height)
    - Black  #000000 → TileColor / Foreground
    - White  #FFFFFF → DetailColor
    - Transparent     → background (usually k)
    - Optional midtone blend color (124,101,44) for mixed FG/Detail

  Truecolor (optional):
    - Full RGBA PNG; requires modconfig.json shaderMode truecolor
    - Still prefers 16×24 aspect; larger sizes for tile-scaling mods

  Scaled sizes (same 2:3 aspect as vanilla):
    16×24, 32×48, 48×72, 64×96

  Animation (optional):
    frame00..N PNGs + AnimatedMaterialGeneric TileAnimationFrames snippet
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
except ImportError as e:
    raise SystemExit("Pillow required: pip install Pillow") from e


# Vanilla CoQ player tile aspect (width × height)
VANILLA_W, VANILLA_H = 16, 24
BLEND_MID = (124, 101, 44, 255)  # official 4th-color blend channel

SIZE_PRESETS = {
    "vanilla": (16, 24),
    "2x": (32, 48),
    "3x": (48, 72),
    "4x": (64, 96),
}

DEFAULT_FRAMES = 8
DEFAULT_ANIM_LENGTH = 160

# Swappable worn-gear slots. Mutations (heads, brood sack) stay on the base body.
OVERLAY_SLOTS: Dict[str, Dict[str, Any]] = {
    "chest": {
        "role": "apron",
        "flag": "worn_gear",
        "keywords": ("apron", "cloak", "robe", "vest", "shirt", "tunic", "armor", "chain", "plate"),
    },
    "spectacles": {
        "role": "spectacles",
        "flag": "worn_spectacles",
        "keywords": ("spectacle", "glasses", "goggles", "visor"),
    },
    "claws": {
        "role": "claw",
        "flag": "overlay_claws",
        "keywords": ("claw", "gauntlet"),
    },
}


def _log(msg: str) -> None:
    print(msg, file=sys.stderr)


def _slug(name: str) -> str:
    s = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in (name or "fighter"))
    return s.strip("_") or "fighter"


def _labels(fighter: Dict[str, Any]) -> str:
    muts = fighter.get("mutationLabels") or [
        m.get("name", "") for m in (fighter.get("mutations") or []) if isinstance(m, dict)
    ]
    chrome = fighter.get("cyberneticLabels") or []
    return (" ".join(str(x) for x in muts) + " " + " ".join(str(x) for x in chrome)).lower()


def _mutation_level(fighter: Dict[str, Any], needle: str) -> int:
    key = needle.lower().replace(" ", "")
    for m in fighter.get("mutations") or []:
        if not isinstance(m, dict):
            continue
        name = str(m.get("name") or "").lower().replace(" ", "")
        variant = str(m.get("variant") or "").lower().replace(" ", "")
        if key in name or key in variant:
            try:
                return max(1, int(m.get("level") or 1))
            except (TypeError, ValueError):
                return 1
    return 0


def _head_count(fighter: Dict[str, Any], flags: Dict[str, bool]) -> int:
    """Multiple Heads: Recur bodies are typically 1 + extras (often 3 total)."""
    if not flags.get("multi_head"):
        return 1
    lvl = _mutation_level(fighter, "multiplehead") or 1
    # L1 → 3 heads (original + 2 managed). Cap at 4 so 16×24 still reads.
    return min(4, lvl + 2)


def _is_feline(fighter: Dict[str, Any]) -> bool:
    extra = " ".join(
        str(fighter.get(k) or "")
        for k in ("tile", "genotype", "subtype", "type_name", "name", "id", "description")
    ).lower()
    blob = f"{_labels(fighter)} {extra}"
    return any(
        k in blob
        for k in (
            "kitty",
            "tabby",
            "feline",
            "cat companion",
            "astral paw",
            "sw_kitty",
            "house cat",
            "cheshire",
        )
    )


def _is_slime(fighter: Dict[str, Any]) -> bool:
    """WM Gelatinous Form / poison ooze / explicit slime variant id."""
    extra = " ".join(
        str(fighter.get(k) or "")
        for k in ("tile", "genotype", "subtype", "type_name", "name", "id", "description", "colorMode")
    ).lower()
    blob = f"{_labels(fighter)} {extra}"
    return any(
        k in blob
        for k in (
            "gelatinous",
            "slime",
            "poisonslime",
            "poison_slime",
            "ooze",
            "pseudopod",
            "oral arm",
        )
    )


def suggest_colors(fighter: Dict[str, Any]) -> Tuple[str, str]:
    """Suggest Foreground / Detail single-letter CoQ color codes."""
    text = _labels(fighter) + " " + str(fighter.get("genotype", "")).lower()
    fg, detail = fighter.get("foreground") or "", fighter.get("detail") or ""
    if fg and len(fg) == 1 and detail and len(detail) == 1:
        return fg, detail
    if "brood" in text or "insect" in text or "arachnid" in text:
        return "m", "M"
    if "cyber" in text or "truekin" in text or "true kin" in text:
        return "c", "Y"
    if "esper" in text or "telepath" in text or "mental" in text:
        return "b", "M"
    if "chimera" in text or "carapace" in text:
        return "g", "W"
    if "astral" in text or "phase" in text:
        return "y", "M"
    # Recur exports often carry tile colors already
    if fighter.get("foreground") and len(str(fighter["foreground"])) == 1:
        fg = str(fighter["foreground"])
    else:
        fg = "y"
    if fighter.get("detail") and len(str(fighter["detail"])) == 1:
        detail = str(fighter["detail"])
    else:
        detail = "W"
    return fg, detail


def _feature_flags(fighter: Dict[str, Any]) -> Dict[str, bool]:
    t = _labels(fighter)
    compact = t.replace(" ", "")
    astral = "astral" in t or "incorporeal" in t
    phase = "phas" in compact or "incorporeal" in compact or astral
    slime = _is_slime(fighter)
    # Slime mutants stay quadruped (kitty body) and gain one oral-arm tendril.
    feline = _is_feline(fighter) or slime
    quad = feline or "quadruped" in t or "animal legs" in t or "kitty" in t or "tabby" in t
    return {
        "feline": feline,
        "slime": slime,
        "multi_head": "multiplehead" in compact or "hydra" in t,
        "wings": "wing" in t or "flight" in t,
        "tail": True if feline else ("tail" in t or "stinger" in t or "ovipositor" in t or quad or astral),
        "arms": "multiplearms" in compact or "multiple arm" in t,
        "quad": quad,
        "carapace": "carapace" in t or "quill" in t,
        "chrome": bool(fighter.get("cyberneticLabels")),
        "brood": "brood" in t or "ovipositor" in t or "broodling sack" in " ".join(
            str(x) for x in (fighter.get("equipmentLabels") or [])
        ).lower(),
        "conjoined": "conjoin" in compact or "fusion" in t,
        "gigantic": "gigant" in compact,
        "phase": phase,
        "astral": astral,
        "vortex": "vortex" in t or "spacetime" in compact,
        "jitter": "jitter" in t or "quantum" in t,
        "blink": "blink" in t or "tic" in t,
        "claws": "claw" in t or "paw" in t or astral,
        "amphibious": "amphib" in compact,
    }


# 16×24 unit roles for feline sprites. Truecolor maps each role to a real palette
# color (not a 1–2 color luminance wash). Classic maps roles to FG/mid/detail.
_FELINE_LUMA = {
    "body": 72,
    "stripe": 50,
    "belly": 140,
    "ear": 90,
    "muzzle": 150,
    "nose": 200,
    "eye": 255,
    "paw": 160,
    "claw": 255,
    "sack": 170,
    "sack_hi": 230,
    "conjoin": 120,
    "vortex": 255,
    "spectacles": 240,
    "inner_ear": 160,
    "apron": 110,
    "tendril": 180,
    "tendril_tip": 240,
}

_FELINE_RGB = {
    "body": (0x40, 0xA4, 0xB9),   # c cyan fur (Oshwoyushur FG)
    "stripe": (0x15, 0x53, 0x52), # K in-game astral tabby body
    "belly": (0xB1, 0xC9, 0xC3),  # y cream bib
    "ear": (0x40, 0xA4, 0xB9),
    "muzzle": (0xB1, 0xC9, 0xC3),
    "nose": (0xD5, 0x42, 0x00),   # R
    "eye": (0xFF, 0xFF, 0xFF),    # Y
    "paw": (0xB1, 0xC9, 0xC3),
    "claw": (0xCF, 0xC0, 0x41),   # W gold astral claws
    "sack": (0xB1, 0x54, 0xCF),   # m chitin brood sack
    "sack_hi": (0xDA, 0x5B, 0xD6),# M sack glow
    "conjoin": (0xA6, 0x4A, 0x2E),# r fused flesh
    "vortex": (0x77, 0xBF, 0xCF), # C spacetime speck
    "spectacles": (0xCF, 0xC0, 0x41),  # W gigantic spectacles
    "inner_ear": (0xE8, 0x9A, 0x9A),   # pink inner ear
    "apron": (0x98, 0x87, 0x5F),       # worn gear overlay only (not on the base body)
    "tendril": (0x3A, 0xC4, 0x5A),     # toxic jelly oral arm
    "tendril_tip": (0xB1, 0x54, 0xCF), # poison tip / magenta venom
}

# Sitting haunch + thin left tail. Heads stamp onto the shoulders (not floating).
_SW_KITTY_BODY = [
    "                ",
    "                ",
    "                ",
    "                ",
    "                ",
    "                ",
    "                ",
    "                ",
    "                ",
    "                ",
    "        ###     ",
    "       #####    ",
    "  #   yy#####   ",
    "   #   yy#####  ",
    "   #    ######  ",
    "  #     ######  ",
    " #     #######  ",
    " #     #######  ",
    "  #    ######   ",
    "     ########   ",
    "    #########   ",
    "                ",
    "                ",
    "                ",
]


def _stamp_cat_head(
    put,
    ox: int,
    oy: int,
    *,
    blink: bool = False,
    spectacles: bool = False,
) -> None:
    """Right-facing kitty skull: ears, eye, cream snout. Compact 4×5."""
    put(ox + 1, oy, "ear")
    put(ox + 3, oy, "ear")
    put(ox + 1, oy + 1, "spectacles" if spectacles else "body")
    put(ox + 2, oy + 1, "spectacles" if spectacles else "body")
    put(ox + 3, oy + 1, "body")
    put(ox, oy + 2, "body")
    put(ox + 1, oy + 2, "body" if blink else "eye")
    put(ox + 2, oy + 2, "body")
    put(ox + 3, oy + 2, "muzzle")
    put(ox + 1, oy + 3, "body")
    put(ox + 2, oy + 3, "muzzle")
    put(ox + 3, oy + 3, "muzzle")
    put(ox + 2, oy + 4, "body")


def _stamp_tendril_arm(put, ox: int, oy: int, frame: int = 0) -> None:
    """One oral-arm tendril from the shoulder (Gelatinous Form). Not extra legs."""
    sway = 1 if frame % 4 >= 2 else 0
    # Root attached at shoulder / ribcage
    put(ox, oy, "tendril")
    put(ox + 1, oy, "tendril")
    put(ox + 1, oy + 1, "tendril")
    put(ox + 2, oy + 1, "tendril")
    put(ox + 2 + sway, oy + 2, "tendril")
    put(ox + 3 + sway, oy + 3, "tendril")
    put(ox + 3 + sway, oy + 4, "tendril_tip")
    put(ox + 4 + sway, oy + 4, "tendril_tip")


def _fill_neck(put, x0: int, y0: int, x1: int, y1: int) -> None:
    """Solid 2px-wide neck so heads do not float as debris."""
    if y1 < y0:
        y0, y1 = y1, y0
    if x1 < x0:
        x0, x1 = x1, x0
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            put(x, y, "body")


def _kitty_roles(
    fighter: Dict[str, Any],
    flags: Dict[str, bool],
    frame: int,
    total_frames: int,
) -> Dict[Tuple[int, int], str]:
    """Sitting cat, tail left, three kitty heads on the shoulders (connected)."""
    roles: Dict[Tuple[int, int], str] = {}
    tail_up = 1 if frame % 4 >= 2 else 0
    pulse = 1 if flags.get("brood") and frame % 2 == 0 else 0
    heads = _head_count(fighter, flags)
    blink_i = (frame % heads) if flags.get("blink") and heads > 1 else -1

    def put(x: int, y: int, role: str) -> None:
        if 0 <= x < 16 and 0 <= y < 24:
            # Prefer facial / gear detail over plain body when stamps overlap.
            prev = roles.get((x, y))
            if prev in (
                "eye",
                "muzzle",
                "ear",
                "spectacles",
                "sack",
                "sack_hi",
                "claw",
                "apron",
                "tendril",
                "tendril_tip",
            ):
                if role == "body":
                    return
            roles[(x, y)] = role

    for y, row in enumerate(_SW_KITTY_BODY):
        for x, ch in enumerate(row):
            if ch == " ":
                continue
            yy = y - tail_up if x <= 3 and ch == "#" else y
            if ch == "y":
                put(
                    x,
                    yy,
                    "apron"
                    if flags.get("worn_gear") and 12 <= yy <= 14 and 6 <= x <= 8
                    else "belly",
                )
                continue
            h = (x * 7 + y * 13 + frame) % 14
            if h == 0:
                put(x, yy, "stripe")
            elif h == 1 and flags.get("astral"):
                put(x, yy, "vortex")
            else:
                put(x, yy, "body")

    # Main head on the shoulders (spectacles = myopia / gigantic glasses).
    _stamp_cat_head(put, 7, 5, blink=(blink_i == 0), spectacles=True)
    _fill_neck(put, 8, 9, 10, 11)

    if heads >= 2:
        # Second head left-forward, still attached.
        _stamp_cat_head(put, 3, 4, blink=(blink_i == 1))
        _fill_neck(put, 5, 8, 7, 11)

    if heads >= 3:
        # Third head right-rear of main, attached.
        _stamp_cat_head(put, 11, 4, blink=(blink_i == 2))
        _fill_neck(put, 11, 8, 12, 11)

    if heads >= 4:
        _stamp_cat_head(put, 7, 1, blink=(blink_i == 3))
        _fill_neck(put, 8, 5, 9, 6)

    if flags.get("brood"):
        hi = "sack_hi" if pulse else "sack"
        # Brood sack on the rump / back (left of torso), not floating mid-air.
        for dx, dy, role in (
            (3, 0, "sack"), (4, 0, hi),
            (2, 1, "sack"), (3, 1, hi), (4, 1, "sack"),
            (3, 2, "sack"),
        ):
            put(dx, 11 + dy, role)

    if flags.get("conjoined"):
        put(13, 15, "conjoin")
        if (_mutation_level(fighter, "conjoin") or 1) >= 2:
            put(14, 16, "conjoin")

    if flags.get("claws") or flags.get("astral") or flags.get("overlay_claws"):
        put(6, 20, "claw")
        put(11, 20, "claw")

    if flags.get("slime"):
        # Quadruped kitty + single oral-arm tendril (not a blob, not extra legs).
        _stamp_tendril_arm(put, 12, 12, frame)

    if flags.get("vortex"):
        put(14, 16 + (frame % 2), "vortex")

    return roles


def _scale_tile(img: Image.Image, width: int, height: int) -> Image.Image:
    if img.size == (width, height):
        return img
    return img.resize((width, height), Image.Resampling.NEAREST)


def _render_feline_mask(
    width: int,
    height: int,
    fighter: Dict[str, Any],
    flags: Dict[str, bool],
    frame: int,
    total_frames: int,
) -> Image.Image:
    """Classic luminance: sw_kitty silhouette + extra heads + sack on back."""
    small = Image.new("L", (16, 24), 0)
    px = small.load()
    for (x, y), role in _kitty_roles(fighter, flags, frame, total_frames).items():
        px[x, y] = _FELINE_LUMA.get(role, 72)
    return _scale_tile(small, width, height)


def _median_rgb(samples: List[Tuple[int, int, int]]) -> Tuple[int, int, int]:
    if not samples:
        return _FELINE_RGB["body"]
    rs, gs, bs = zip(*samples)
    mid = len(samples) // 2
    return (sorted(rs)[mid], sorted(gs)[mid], sorted(bs)[mid])


def _palette_from_detail(img: Image.Image) -> Dict[str, Tuple[int, int, int]]:
    """Steal gold / cream from the painting. Keep distinct role hues.

    Apron is omitted — gigantic gear replaces it in play. Sack, glasses,
    eyes, and extra heads stay their own colors so 16×24 still reads.
    """
    pal = dict(_FELINE_RGB)
    small = img.convert("RGBA").resize((48, 72), Image.Resampling.BOX)
    small = _knockout_background(small)
    teal, light, gold = [], [], []
    for r, g, b, a in small.getdata():
        if a < 200:
            continue
        luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
        rgb = (r, g, b)
        cyan = b > r + 12 and g > r and b >= g - 25
        olive = g > b + 18 and g > r
        if cyan and not olive:
            teal.append(rgb)
        elif r > 130 and g > 95 and b < 110 and r + g > 2 * b:
            gold.append(rgb)
        elif luma > 155 and not olive:
            light.append(rgb)
    if teal:
        body = _median_rgb(teal)
        if body[2] >= body[1] - 10:
            pal["body"] = pal["ear"] = body
    if light:
        pal["belly"] = pal["muzzle"] = pal["paw"] = _median_rgb(light)
    if gold:
        pal["spectacles"] = pal["claw"] = pal["sack_hi"] = _median_rgb(gold)
    return pal


def _palette_from_gear(img: Image.Image) -> Dict[str, Tuple[int, int, int]]:
    """Sample worn-item colors only. Never overwrites fur / sack / faces."""
    pal: Dict[str, Tuple[int, int, int]] = {}
    small = img.convert("RGBA").resize((48, 72), Image.Resampling.BOX)
    small = _knockout_background(small)
    leather, cloth, metal = [], [], []
    for r, g, b, a in small.getdata():
        if a < 200:
            continue
        luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
        rgb = (r, g, b)
        if r > 70 and r >= g and r > b + 8 and g < 120 and luma < 160:
            leather.append(rgb)
        elif luma > 140 and abs(r - g) < 28 and abs(g - b) < 28:
            metal.append(rgb)
        elif luma < 140 and abs(r - g) < 40:
            cloth.append(rgb)
    if leather:
        pal["apron"] = _median_rgb(leather)
    elif cloth:
        pal["apron"] = _median_rgb(cloth)
    elif metal:
        pal["apron"] = _median_rgb(metal)
    return pal


def _render_feline_truecolor(
    width: int,
    height: int,
    fighter: Dict[str, Any],
    flags: Dict[str, bool],
    frame: int,
    total_frames: int,
    palette: Optional[Dict[str, Tuple[int, int, int]]] = None,
) -> Image.Image:
    """Truecolor sitting-cat layout. Each role keeps its own color."""
    pal = dict(_FELINE_RGB)
    if flags.get("slime"):
        # Poisonous gelatinous fur — keep quadruped, tint jelly + venom tendril.
        pal.update(
            {
                "body": (0x2E, 0xA8, 0x4A),
                "stripe": (0x1A, 0x5C, 0x32),
                "belly": (0x8F, 0xE0, 0x9A),
                "ear": (0x2E, 0xA8, 0x4A),
                "muzzle": (0xB8, 0xF0, 0xC0),
                "paw": (0x8F, 0xE0, 0x9A),
                "tendril": (0x3A, 0xC4, 0x5A),
                "tendril_tip": (0xB1, 0x54, 0xCF),
                "vortex": (0xDA, 0x5B, 0xD6),
            }
        )
    if palette:
        pal.update(palette)
    body_a = 210 if flags.get("phase") else 255
    small = Image.new("RGBA", (16, 24), (0, 0, 0, 0))
    px = small.load()
    for (x, y), role in _kitty_roles(fighter, flags, frame, total_frames).items():
        rgb = pal.get(role) or _FELINE_RGB.get(role, pal["body"])
        a = body_a if role in ("body", "ear", "stripe", "tendril") and flags.get("phase") else 255
        px[x, y] = (*rgb, a)
    return _scale_tile(small, width, height)


def render_mask(
    width: int,
    height: int,
    fighter: Dict[str, Any],
    frame: int = 0,
    total_frames: int = 1,
) -> Image.Image:
    """
    Mutation-first luminance mask:
      0   = transparent (background)
      1-127 ≈ foreground (black channel)
      128-254 ≈ mid blend
      255 = detail (white channel)

    Gear is optional garnish. Multi-head / body-plan / phase / brood / conjoin
    must read at 16×24.
    """
    flags = _feature_flags(fighter)
    if flags.get("feline"):
        return _render_feline_mask(width, height, fighter, flags, frame, total_frames)

    img = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(img)

    t = (frame / max(1, total_frames)) * 2 * math.pi
    bob_amp = max(1, height // (24 if flags["jitter"] else 48))
    bob = int(round(math.sin(t) * bob_amp))
    if flags["jitter"]:
        bob += int(round(math.sin(t * 3.0 + frame) * max(1, width // 16)))
    cx = width // 2 + (1 if flags["jitter"] and frame % 2 else 0)
    cy = height // 2 + bob

    # Gigantism fills more of the tile; quadruped is a horizontal animal, not a biped.
    scale = 1.18 if flags["gigantic"] else 1.0
    if flags["quad"]:
        body_w = max(6, int(width * 0.72 * scale))
        body_h = max(5, int(height * 0.34 * scale))
        cy = int(height * 0.58) + bob
    else:
        body_w = max(5, int(width * 0.52 * scale))
        body_h = max(6, int(height * 0.44 * scale))
    head_r = max(2, int(min(width, height) * (0.14 if flags["multi_head"] else 0.16) * min(scale, 1.1)))
    stroke = max(1, width // 16)

    # Legs / astral paws
    leg_n = 4 if flags["quad"] else 2
    for i in range(leg_n):
        sway = int(math.sin(t + i * 0.9) * max(1, width // 20))
        lx = cx - body_w // 2 + (i + 1) * (body_w // (leg_n + 1))
        y0 = cy + body_h // 3
        y1 = min(height - 1, cy + body_h // 2 + max(3, height // 7))
        draw.line([(lx, y0), (lx + sway, y1)], fill=95, width=stroke)
        if flags["claws"] or flags["astral"]:
            draw.point((max(0, min(width - 1, lx + sway)), max(0, min(height - 1, y1))), fill=255)
            if width >= 24:
                draw.point((max(0, min(width - 1, lx + sway - 1)), max(0, min(height - 1, y1))), fill=255)

    # Wings / carapace flare
    if flags["wings"] or flags["carapace"]:
        for side in (-1, 1):
            pts = [
                (cx, cy - body_h // 4),
                (cx + side * int(width * 0.45), cy + bob // 2),
                (cx + side * int(width * 0.25), cy + body_h // 4),
            ]
            draw.polygon(pts, fill=200)

    # Torso
    torso = [
        cx - body_w // 2,
        cy - body_h // 2,
        cx + body_w // 2,
        cy + body_h // 2,
    ]
    draw.rectangle(torso, fill=78 if flags["amphibious"] else 70)
    if flags["amphibious"]:
        draw.line(
            [(cx - body_w // 3, cy), (cx + body_w // 3, cy)],
            fill=130,
            width=1,
        )

    # Conjoined L3: fused extra masses on the flanks (not gear).
    if flags["conjoined"]:
        n_lumps = min(3, max(1, _mutation_level(fighter, "conjoin") or 1))
        for i in range(n_lumps):
            side = -1 if i % 2 == 0 else 1
            ly = cy - body_h // 4 + (i * max(2, height // 14))
            lx = cx + side * (body_w // 2 + max(1, width // 18))
            rr = max(1, head_r - 1)
            pulse = 1 if flags["jitter"] and (frame + i) % 2 else 0
            draw.ellipse(
                [lx - rr - pulse, ly - rr, lx + rr + pulse, ly + rr],
                fill=120,
            )
            draw.point((max(0, min(width - 1, lx)), max(0, min(height - 1, ly))), fill=210)

    # Extra arms
    if flags["arms"]:
        for side, phase in ((-1, 0.4), (1, 1.1), (-1, 1.7), (1, 2.3)):
            ang = t * 0.5 + phase
            ax = cx + side * (body_w // 2 + max(1, width // 10))
            ay = cy + int(math.sin(ang) * max(1, height // 40))
            draw.line([(cx + side * body_w // 3, cy), (ax, ay)], fill=100, width=stroke)
            draw.point((ax, ay), fill=255)

    # Broodmother sack — bulb on the back, pulses in animation.
    if flags["brood"]:
        pulse = 1 if math.sin(t) > 0 else 0
        sx0 = cx - max(2, body_w // 5) - pulse
        sy0 = cy - body_h // 2 - max(2, height // 12) - pulse
        sx1 = cx + max(2, body_w // 5) + pulse
        sy1 = cy - body_h // 6
        draw.ellipse([sx0, sy0, sx1, sy1], fill=155)
        draw.point((cx, max(0, sy0 + 1)), fill=255)
        if width >= 24:
            draw.point((cx - 2, max(0, sy0 + 2)), fill=255)
            draw.point((cx + 2, max(0, sy0 + 2)), fill=255)

    # Heads — primary read. Multiple Heads = a row of distinct skulls.
    heads = _head_count(fighter, flags)
    head_span = max(3, min(width - 2 * head_r - 1, (heads - 1) * max(3, head_r * 2 + 1)))
    hy = cy - body_h // 2 - max(head_r, height // 16)
    blink_i = (frame % heads) if flags["blink"] and heads > 1 else -1
    for hi in range(heads):
        if heads == 1:
            hx = cx
        else:
            hx = int(cx - head_span // 2 + hi * (head_span / max(1, heads - 1)))
        hx = max(head_r, min(width - 1 - head_r, hx))
        hy_i = hy + (1 if flags["jitter"] and hi == frame % heads else 0)
        draw.ellipse([hx - head_r, hy_i - head_r, hx + head_r, hy_i + head_r], fill=88)
        # Eyes (detail). Blinking Tic: one head dark on rotating frames.
        if hi != blink_i:
            ex = max(1, head_r // 3)
            draw.point((hx - ex, hy_i - 1), fill=255)
            draw.point((hx + ex, hy_i - 1), fill=255)
        if flags["claws"] or flags["astral"]:
            # fang speck
            draw.point((hx, min(height - 1, hy_i + max(1, head_r // 2))), fill=240)

    # Tail
    if flags["tail"]:
        tip_x = cx + int(math.cos(t) * width * 0.22)
        tip_y = min(height - 1, cy + body_h // 2 + int(height * 0.10) + int(math.sin(t)))
        draw.line([(cx + body_w // 4, cy + body_h // 4), (tip_x, tip_y)], fill=110, width=stroke)
        draw.point((max(0, min(width - 1, tip_x)), max(0, min(height - 1, tip_y))), fill=255)

    # Spacetime vortex — small rotating detail, not a background wash.
    if flags["vortex"]:
        vr = max(2, min(head_r, width // 6))
        vx = max(vr, min(width - 1 - vr, cx - body_w // 2 - max(1, width // 20)))
        vy = max(vr, min(height - 1 - vr, cy - body_h // 3))
        ang = t
        draw.ellipse([vx - vr, vy - vr, vx + vr, vy + vr], outline=200)
        draw.point(
            (
                max(0, min(width - 1, vx + int(math.cos(ang) * vr))),
                max(0, min(height - 1, vy + int(math.sin(ang) * vr))),
            ),
            fill=255,
        )

    # Chrome leftover accents
    if flags["chrome"] and not flags["brood"]:
        for i, (dx, dy) in enumerate(((-2, 0), (2, 1), (0, -2))):
            px = cx + dx * max(1, width // 16)
            py = cy + dy * max(1, height // 24)
            if 0 <= px < width and 0 <= py < height:
                draw.point((px, py), fill=255)

    return img


def mask_to_classic(mask: Image.Image) -> Image.Image:
    """Map luminance mask → CoQ classic 3-color (+ optional mid blend) RGBA."""
    w, h = mask.size
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px_m = mask.load()
    px_o = out.load()
    for y in range(h):
        for x in range(w):
            v = px_m[x, y]
            if v <= 0:
                continue
            if v >= 220:
                px_o[x, y] = (255, 255, 255, 255)  # detail
            elif v >= 140:
                px_o[x, y] = BLEND_MID  # blended FG/Detail
            else:
                px_o[x, y] = (0, 0, 0, 255)  # foreground
    return out


PALETTE_RGB = {
    "r": (166, 74, 46), "R": (215, 66, 0),
    "o": (241, 95, 34), "O": (233, 159, 16),
    "w": (152, 135, 95), "W": (207, 192, 65),
    "g": (0, 148, 3), "G": (0, 196, 32),
    "b": (0, 72, 189), "B": (0, 150, 255),
    "c": (64, 164, 185), "C": (119, 191, 207),
    "m": (177, 84, 207), "M": (218, 91, 214),
    "k": (15, 59, 58), "K": (21, 83, 82),
    "y": (177, 201, 195), "Y": (255, 255, 255),
}


def mask_to_truecolor(mask: Image.Image, fighter: Dict[str, Any]) -> Image.Image:
    """Truecolor RGBA using Recur/suggested CoQ palette. Phase/astral = partial alpha."""
    flags = _feature_flags(fighter)
    fg_c, det_c = suggest_colors(fighter)
    fg = PALETTE_RGB.get(fg_c, (64, 164, 185))
    det = PALETTE_RGB.get(det_c, (177, 201, 195))
    body_a = 200 if flags["phase"] else 255
    w, h = mask.size
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px_m = mask.load()
    px_o = out.load()
    for y in range(h):
        for x in range(w):
            v = px_m[x, y]
            if v <= 0:
                continue
            if v >= 220:
                px_o[x, y] = (*det, 255)
            elif v >= 140:
                u = (v - 140) / 80.0
                col = tuple(int(fg[i] * (1 - u) + det[i] * u) for i in range(3))
                px_o[x, y] = (*col, 255 if flags["astral"] else body_a)
            else:
                px_o[x, y] = (*fg, body_a)
    return out


def _bake_truecolor(
    fighter: Dict[str, Any],
    width: int,
    height: int,
    frame: int,
    total: int,
) -> Image.Image:
    flags = _feature_flags(fighter)
    if flags.get("feline"):
        img = _render_feline_truecolor(width, height, fighter, flags, frame, total)
        # Feline idle is sack pulse / tail / blink. A ghost offset turns 16×24 to noise.
        return img
    mask = render_mask(width, height, fighter, frame, total)
    img = mask_to_truecolor(mask, fighter)
    if not (flags["phase"] or flags["astral"] or flags["jitter"]):
        return img
    ghost = img.copy()
    ga = ghost.split()[-1].point(lambda a: int(a * 0.45) if a else 0)
    ghost.putalpha(ga)
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    dx = 1 if (flags["phase"] or flags["astral"]) else 0
    if flags["jitter"]:
        dx += 1 if frame % 2 else -1
    canvas.paste(ghost, (dx, 0), ghost)
    canvas.alpha_composite(img)
    return canvas


def build_animation_xml(
    tile_rel_paths: Sequence[str],
    animation_length: int = DEFAULT_ANIM_LENGTH,
) -> str:
    if not tile_rel_paths:
        return ""
    n = len(tile_rel_paths)
    step = max(1, animation_length // n)
    frames = ",".join(f"{i * step}={rel}" for i, rel in enumerate(tile_rel_paths))
    return (
        f'<part Name="AnimatedMaterialGeneric" AnimationLength="{animation_length}" '
        f'TileAnimationFrames="{frames}" />'
    )


def build_pregen_xml(
    fighter: Dict[str, Any],
    tile_rel: str,
    foreground: str,
    detail: str,
) -> str:
    name = fighter.get("name") or "Fighter"
    geno = fighter.get("genotype") or "Mutated Human"
    # Genotype display names often needed; leave raw if already friendly
    if geno.endswith("Genotype"):
        geno = "Mutated Human"
    desc = fighter.get("promptDescription") or fighter.get("description") or name
    desc = str(desc).replace("&", "&amp;").replace("<", "&lt;")
    return f"""<embarkmodules>
  <module Class="XRL.CharacterBuilds.Qud.QudPregenModule">
    <pregens>
      <pregen Name="{name}" Genotype="{geno}" Tile="{tile_rel}" Foreground="{foreground}" Detail="{detail}" Background="k">
        <code><!-- paste build code or leave empty for tile-only preset tooling --></code>
        <description>
{desc}
        </description>
      </pregen>
    </pregens>
  </module>
</embarkmodules>
"""


def _crop_aspect(img: Image.Image, aspect: float) -> Image.Image:
    w, h = img.size
    if w <= 0 or h <= 0 or aspect <= 0:
        return img
    cur = w / float(h)
    if abs(cur - aspect) < 0.02:
        return img
    if cur > aspect:
        nw = max(1, int(round(h * aspect)))
        left = (w - nw) // 2
        return img.crop((left, 0, left + nw, h))
    nh = max(1, int(round(w / aspect)))
    top = (h - nh) // 2
    return img.crop((0, top, w, top + nh))


def _knockout_background(img: Image.Image) -> Image.Image:
    """Transparent bg for CoQ (k). Corners + near-black + viridian void."""
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    br = sum(c[0] for c in corners) // 4
    bg = sum(c[1] for c in corners) // 4
    bb = sum(c[2] for c in corners) // 4
    out = []
    for r, g, b, a in img.getdata():
        if a < 24:
            out.append((r, g, b, 0))
            continue
        luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
        dist = (r - br) ** 2 + (g - bg) ** 2 + (b - bb) ** 2
        viridian = abs(r - 15) < 22 and abs(g - 59) < 26 and abs(b - 58) < 26
        if luma < 14 or viridian or dist < 2200:
            out.append((r, g, b, 0))
        else:
            out.append((r, g, b, 255))
    dst = Image.new("RGBA", img.size)
    dst.putdata(out)
    return dst


def _downscale_keep_detail(img: Image.Image, size: Tuple[int, int]) -> Image.Image:
    """LANCZOS downscale of a detailed painting. Never posterize / silhouette-stamp."""
    tw, th = size
    img = _crop_aspect(img.convert("RGBA"), tw / float(th))
    # Knock out on a small buffer — a Python pixel loop on a 2k painting is minutes.
    buf_w, buf_h = tw * 4, th * 4
    if img.size[0] > buf_w or img.size[1] > buf_h:
        img = img.resize((buf_w, buf_h), Image.Resampling.LANCZOS)
        img = ImageEnhance.Sharpness(img).enhance(1.2)
    img = _knockout_background(img)
    img = img.resize((tw, th), Image.Resampling.LANCZOS)
    img = ImageEnhance.Sharpness(img).enhance(1.65)
    img = ImageEnhance.Contrast(img).enhance(1.22)
    return _knockout_background(img)


def _classic_from_detail(img: Image.Image) -> Image.Image:
    """Map a detailed sprite onto vanilla FG/Detail/transparent — still from the painting."""
    gray = img.convert("L")
    alpha = img.split()[-1]
    gx = list(gray.getdata())
    ax = list(alpha.getdata())
    opaque = [g for g, a in zip(gx, ax) if a >= 16]
    if not opaque:
        return Image.new("RGBA", img.size, (0, 0, 0, 0))
    s = sorted(opaque)
    t_lo = s[max(0, int(len(s) * 0.22))]
    t_hi = s[min(len(s) - 1, int(len(s) * 0.62))]
    if t_hi <= t_lo:
        t_hi = t_lo + 1
    out_px = []
    for g, a in zip(gx, ax):
        if a < 16:
            out_px.append((0, 0, 0, 0))
        elif g <= t_lo:
            out_px.append((0, 0, 0, 255))
        elif g >= t_hi:
            out_px.append((255, 255, 255, 255))
        else:
            out_px.append(BLEND_MID)
    out = Image.new("RGBA", img.size)
    out.putdata(out_px)
    return out


def _idle_hires(img: Image.Image, frame: int, total: int, flags: Dict[str, bool]) -> Image.Image:
    """Keep every painted pixel; only bob / phase-alpha for idle."""
    total = max(1, total)
    bob = int(round(math.sin((frame / total) * 2 * math.pi) * max(1, img.height // 64)))
    if flags.get("jitter") and frame % 2:
        bob += max(1, img.height // 128)
    canvas = Image.new("RGBA", img.size, (0, 0, 0, 0))
    canvas.paste(img, (0, bob), img)
    if (flags.get("phase") or flags.get("astral")) and frame % 2:
        a = canvas.split()[-1].point(lambda v: int(v * 0.86) if v else 0)
        canvas.putalpha(a)
    return canvas


def _is_tiny_tile(path: Path) -> bool:
    try:
        with Image.open(path) as im:
            w, h = im.size
        return w <= 24 and h <= 36
    except Exception:
        return True


def find_detail_sources(
    out_dir: Path,
    name: str,
    from_image: Optional[Path] = None,
) -> List[Path]:
    found: List[Path] = []
    if from_image:
        p = Path(from_image)
        if p.is_dir():
            found.extend(sorted(p.glob("*.png")))
        elif p.is_file():
            found.append(p)
    if out_dir and out_dir.is_dir():
        kf = out_dir / "keyframes"
        if kf.is_dir():
            keys = sorted(kf.glob("*.png"))
            if len(keys) >= 2:
                found.extend(keys)
        if not found:
            for pat in (
                f"{name}_sd_draft.png",
                f"{name}_concept.png",
                f"{name}_detailed.png",
                f"fighter_{name}.png",
            ):
                q = out_dir / pat
                if q.is_file():
                    found.append(q)
            found.extend(sorted(out_dir.glob(f"{name}_cyf_f*.png")))
            found.extend(sorted(out_dir.glob(f"{name}_key*.png")))
            found.extend(sorted(out_dir.glob("fighter_*.png")))
    uniq: List[Path] = []
    seen = set()
    for p in found:
        try:
            key = str(p.resolve())
        except OSError:
            continue
        if key in seen or not p.is_file():
            continue
        seen.add(key)
        if _is_tiny_tile(p):
            continue
        uniq.append(p)
    return uniq


def canonical_base_path(out_dir: Path, name: str) -> Path:
    return Path(out_dir) / "base" / f"{name}_base.png"


def canonical_gear_path(out_dir: Path, name: str) -> Path:
    return Path(out_dir) / "gear" / f"{name}_gear.png"


def find_base_image(
    out_dir: Path,
    name: str,
    explicit: Optional[Path] = None,
) -> Optional[Path]:
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return p
    pinned = canonical_base_path(out_dir, name)
    if pinned.is_file():
        return pinned
    man = Path(out_dir) / f"{name}.tile.json"
    if man.is_file():
        try:
            data = json.loads(man.read_text(encoding="utf-8"))
            raw = data.get("baseImage")
            if raw and Path(raw).is_file() and not _is_tiny_tile(Path(raw)):
                return Path(raw)
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    return None


def pin_base_image(out_dir: Path, name: str, source: Path, *, overwrite: bool) -> Path:
    dest = canonical_base_path(out_dir, name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    src = Path(source)
    if dest.exists() and not overwrite:
        return dest
    try:
        if dest.exists() and src.resolve() == dest.resolve():
            return dest
    except OSError:
        pass
    shutil.copy2(src, dest)
    _log(f"  [tile] pinned base character image → {dest}")
    return dest


def pin_gear_image(out_dir: Path, name: str, source: Path) -> Path:
    dest = canonical_gear_path(out_dir, name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    src = Path(source)
    try:
        if dest.exists() and src.resolve() == dest.resolve():
            return dest
    except OSError:
        pass
    shutil.copy2(src, dest)
    _log(f"  [tile] stored gear overlay → {dest}")
    return dest


def overlay_root(out_dir: Path) -> Path:
    return Path(out_dir) / "overlays"


def overlay_catalog_path(out_dir: Path) -> Path:
    return overlay_root(out_dir) / "catalog.json"


def empty_overlay_catalog() -> Dict[str, Any]:
    return {
        "version": 1,
        "slots": {
            slot: {"role": meta["role"], "items": {}}
            for slot, meta in OVERLAY_SLOTS.items()
        },
    }


def load_overlay_catalog(out_dir: Path) -> Dict[str, Any]:
    path = overlay_catalog_path(out_dir)
    if not path.is_file():
        return empty_overlay_catalog()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_overlay_catalog()
    cat = empty_overlay_catalog()
    slots = data.get("slots") if isinstance(data, dict) else None
    if isinstance(slots, dict):
        for slot, body in slots.items():
            if slot not in OVERLAY_SLOTS or not isinstance(body, dict):
                continue
            cat["slots"][slot]["items"] = dict(body.get("items") or {})
    return cat


def save_overlay_catalog(out_dir: Path, catalog: Dict[str, Any]) -> Path:
    root = overlay_root(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    for slot in OVERLAY_SLOTS:
        (root / slot).mkdir(exist_ok=True)
    path = overlay_catalog_path(out_dir)
    path.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    return path


def _item_slug(label: str) -> str:
    s = re.sub(r"\(mod [^)]+\)", "", (label or "").lower())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "item"


def infer_overlay_slot(label: str) -> Optional[str]:
    t = (label or "").lower()
    if "brood" in t or "sack" in t:
        return None
    for slot, meta in OVERLAY_SLOTS.items():
        if any(k in t for k in meta["keywords"]):
            return slot
    return None


def _parse_slot_id(spec: str) -> Tuple[str, str]:
    raw = (spec or "").strip()
    if "=" not in raw:
        raise SystemExit(f"Overlay spec must be SLOT=ID (got {spec!r})")
    slot, item_id = raw.split("=", 1)
    slot = slot.strip().lower()
    item_id = _item_slug(item_id.strip())
    if slot not in OVERLAY_SLOTS:
        raise SystemExit(f"Unknown overlay slot {slot!r}. Use: {', '.join(OVERLAY_SLOTS)}")
    if not item_id:
        raise SystemExit(f"Missing overlay id in {spec!r}")
    return slot, item_id


def _palette_for_overlay_slot(img: Image.Image, slot: str) -> Dict[str, Tuple[int, int, int]]:
    role = str(OVERLAY_SLOTS[slot]["role"])
    if slot == "chest":
        sampled = _palette_from_gear(img)
        if role in sampled:
            return {role: sampled[role]}
        return {role: _FELINE_RGB[role]}
    detail = _palette_from_detail(img)
    if slot == "spectacles":
        return {"spectacles": detail.get("spectacles", _FELINE_RGB["spectacles"])}
    if slot == "claws":
        return {"claw": detail.get("claw", _FELINE_RGB["claw"])}
    return {role: _FELINE_RGB.get(role, _FELINE_RGB["body"])}


def store_overlay(
    out_dir: Path,
    slot: str,
    item_id: str,
    *,
    source: Optional[Path] = None,
    label: Optional[str] = None,
    blueprints: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    if slot not in OVERLAY_SLOTS:
        raise SystemExit(f"Unknown overlay slot {slot!r}")
    catalog = load_overlay_catalog(out_dir)
    save_overlay_catalog(out_dir, catalog)
    items = catalog["slots"][slot]["items"]
    item = items.get(item_id) or {
        "id": item_id,
        "label": label or item_id,
        "image": None,
        "palette": {},
        "blueprints": [],
    }
    if label:
        item["label"] = label
    if blueprints:
        merged = list(item.get("blueprints") or [])
        for b in blueprints:
            if b and b not in merged:
                merged.append(b)
        item["blueprints"] = merged
    role = str(OVERLAY_SLOTS[slot]["role"])
    if source and Path(source).is_file():
        dest = overlay_root(out_dir) / slot / f"{item_id}.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        src = Path(source)
        try:
            same = dest.exists() and src.resolve() == dest.resolve()
        except OSError:
            same = False
        if not same:
            shutil.copy2(src, dest)
        item["image"] = f"{slot}/{item_id}.png"
        pal = _palette_for_overlay_slot(Image.open(dest).convert("RGBA"), slot)
        item["palette"] = {k: list(v) for k, v in pal.items()}
        _log(f"  [tile] overlay {slot}/{item_id} ← {dest}")
    elif not item.get("palette"):
        item["palette"] = {role: list(_FELINE_RGB[role])}
    items[item_id] = item
    save_overlay_catalog(out_dir, catalog)
    return item


def seed_overlays_from_fighter(out_dir: Path, fighter: Dict[str, Any]) -> Dict[str, Any]:
    catalog = load_overlay_catalog(out_dir)
    labels = [str(x) for x in (fighter.get("equipmentLabels") or [])]
    for label in labels:
        slot = infer_overlay_slot(label)
        if not slot:
            continue
        item_id = _item_slug(label)
        items = catalog["slots"][slot]["items"]
        if item_id in items:
            continue
        role = str(OVERLAY_SLOTS[slot]["role"])
        items[item_id] = {
            "id": item_id,
            "label": label,
            "image": None,
            "palette": {role: list(_FELINE_RGB[role])},
            "blueprints": [label.split("(")[0].strip()],
        }
        _log(f"  [tile] overlay stub {slot}/{item_id}")
    save_overlay_catalog(out_dir, catalog)
    return catalog


def match_overlays_from_fighter(
    fighter: Dict[str, Any],
    catalog: Dict[str, Any],
) -> Dict[str, str]:
    selection: Dict[str, str] = {}
    for label in fighter.get("equipmentLabels") or []:
        slot = infer_overlay_slot(str(label))
        if not slot or slot in selection:
            continue
        slug = _item_slug(str(label))
        items = catalog["slots"].get(slot, {}).get("items") or {}
        if slug in items:
            selection[slot] = slug
            continue
        for iid, item in items.items():
            blob = " ".join(
                [
                    iid,
                    str(item.get("label") or ""),
                    " ".join(str(x) for x in (item.get("blueprints") or [])),
                ]
            ).lower()
            if slug in iid or iid in slug or slug.replace("-", " ") in blob:
                selection[slot] = iid
                break
    return selection


def overlay_palette(
    out_dir: Path,
    catalog: Dict[str, Any],
    selection: Dict[str, str],
) -> Dict[str, Tuple[int, int, int]]:
    pal: Dict[str, Tuple[int, int, int]] = {}
    for slot, item_id in selection.items():
        item = (catalog.get("slots") or {}).get(slot, {}).get("items", {}).get(item_id)
        if not item:
            continue
        raw = item.get("palette") or {}
        for key, val in raw.items():
            if isinstance(val, (list, tuple)) and len(val) >= 3:
                pal[key] = (int(val[0]), int(val[1]), int(val[2]))
        rel = item.get("image")
        if rel:
            img_path = overlay_root(out_dir) / rel
            if img_path.is_file():
                pal.update(_palette_for_overlay_slot(Image.open(img_path).convert("RGBA"), slot))
    return pal


def list_overlay_catalog(out_dir: Path) -> Dict[str, Any]:
    catalog = load_overlay_catalog(out_dir)
    listing: Dict[str, Any] = {"catalog": str(overlay_catalog_path(out_dir)), "slots": {}}
    for slot, body in catalog["slots"].items():
        listing["slots"][slot] = []
        for iid, item in (body.get("items") or {}).items():
            listing["slots"][slot].append(
                {
                    "id": iid,
                    "label": item.get("label"),
                    "image": item.get("image"),
                    "hasImage": bool(item.get("image")),
                }
            )
    return listing


def build_detail_tile_prompt(fighter: Dict[str, Any]) -> Tuple[str, str]:
    name = fighter.get("name") or "fighter"
    desc = (
        fighter.get("detailedArtDescription")
        or fighter.get("promptDescription")
        or fighter.get("description")
        or name
    )
    muts = ", ".join(str(x) for x in (fighter.get("mutationLabels") or [])[:24])
    gear = ", ".join(str(x) for x in (fighter.get("equipmentLabels") or [])[:12])
    prompt = (
        f"Detailed full-body Caves of Qud character of {name}, science-fantasy, "
        "bizarre mutations, vibrant colors, high detail, entire body visible, "
        "2:3 portrait, dark void background. "
        f"{desc} Visible mutations: {muts}. Wearing: {gear}. "
        "Show what they really look like — extra heads, brood sack, conjoined fusions, "
        "gear, chrome — not a simplified icon, not a 2-color silhouette, not a pixel stamp."
    )
    negative = (
        "silhouette, two-color sprite, 1-bit, flat icon, simplified icon, chibi stamp, "
        "empty outline, yellow background, white background, portrait bust, headshot, "
        "text, watermark, collage, scanlines, CRT, pixel-art dither grid"
    )
    return prompt, negative


def build_gear_update_prompt(fighter: Dict[str, Any]) -> Tuple[str, str]:
    name = fighter.get("name") or "fighter"
    gear = ", ".join(str(x) for x in (fighter.get("equipmentLabels") or [])[:12]) or "no worn armor"
    prompt = (
        f"The same Caves of Qud character {name}, keep identical anatomy and pose: "
        "three feline heads, broodling sack on the rump, sitting cat, teal marble fur, "
        "gold spectacles. Full body, 2:3 portrait, dark void background. "
        f"Update only worn equipment to: {gear}. "
        "Do not change species, number of heads, or the brood sack."
    )
    negative = (
        "different character, new creature, extra heads, missing heads, silhouette, "
        "pixel stamp, portrait bust, text, watermark"
    )
    return prompt, negative


def _try_sd_detail(
    fighter: Dict[str, Any],
    draft_path: Path,
    *,
    reference_image: Optional[Path] = None,
    force: bool = False,
) -> Optional[Path]:
    try:
        from qud_sd_client import generate_sd_draft  # noqa: WPS433
    except Exception as ex:
        _log(f"  [tile] SD client unavailable ({ex})")
        return None
    prompt, negative = (
        build_gear_update_prompt(fighter)
        if reference_image
        else build_detail_tile_prompt(fighter)
    )
    _log(
        "  [tile] SD gear update from base image..."
        if reference_image
        else "  [tile] SD detailed full-body (not a silhouette stamp)..."
    )
    result = generate_sd_draft(
        prompt,
        draft_path,
        negative_prompt=negative,
        width=512,
        height=768,
        steps=16,
        guidance_scale=7.5,
        lock_label=f"cyf_tile_{draft_path.stem}",
        force=force or bool(reference_image),
        reference_image=reference_image,
        image_strength=0.38 if reference_image else 0.35,
    )
    if result.ok and result.output_path and Path(result.output_path).is_file():
        return Path(result.output_path)
    _log(f"  [tile] SD failed: {result.error}")
    return None


def generate_fighter_tiles(
    fighter: Dict[str, Any],
    out_dir: Path,
    *,
    size: str = "vanilla",
    color_mode: str = "classic",
    animated: bool = False,
    frames: int = DEFAULT_FRAMES,
    animation_length: int = DEFAULT_ANIM_LENGTH,
    from_image: Optional[Path] = None,
    base_image: Optional[Path] = None,
    gear_image: Optional[Path] = None,
    save_base: bool = False,
    update_gear: bool = False,
    overlays: Optional[Sequence[str]] = None,
    pin_overlay: Optional[str] = None,
    auto_overlays: bool = True,
    use_sd: Optional[bool] = None,
    allow_silhouette: bool = False,
) -> Dict[str, Any]:
    if size not in SIZE_PRESETS:
        raise ValueError(f"size must be one of {list(SIZE_PRESETS)}")
    if color_mode not in ("classic", "truecolor"):
        raise ValueError("color_mode must be classic or truecolor")

    width, height = SIZE_PRESETS[size]
    out_dir = Path(out_dir)
    tex = out_dir / "Textures" / "Creatures"
    tex.mkdir(parents=True, exist_ok=True)

    name = _slug(str(fighter.get("id") or fighter.get("name") or "fighter"))
    fg, detail = suggest_colors(fighter)
    flags = _feature_flags(fighter)
    if use_sd is None:
        use_sd = color_mode == "truecolor"

    pinned_base = find_base_image(out_dir, name, base_image)
    gear_path = Path(gear_image) if gear_image and Path(gear_image).is_file() else None
    catalog = seed_overlays_from_fighter(out_dir, fighter)
    overlay_selection: Dict[str, str] = {}
    if auto_overlays:
        overlay_selection.update(match_overlays_from_fighter(fighter, catalog))
    for spec in overlays or []:
        slot, iid = _parse_slot_id(spec)
        overlay_selection[slot] = iid
    if pin_overlay:
        slot, iid = _parse_slot_id(pin_overlay)
        labels = [str(x) for x in (fighter.get("equipmentLabels") or [])]
        label = next((x for x in labels if infer_overlay_slot(x) == slot), iid)
        store_overlay(out_dir, slot, iid, source=gear_path, label=label)
        overlay_selection[slot] = iid
        catalog = load_overlay_catalog(out_dir)
    elif gear_path:
        labels = [str(x) for x in (fighter.get("equipmentLabels") or [])]
        slot = next((infer_overlay_slot(x) for x in labels if infer_overlay_slot(x)), "chest")
        label = next((x for x in labels if infer_overlay_slot(x) == slot), slot)
        iid = _item_slug(label)
        store_overlay(out_dir, slot, iid, source=gear_path, label=label)
        overlay_selection[slot] = iid
        catalog = load_overlay_catalog(out_dir)
    flags["worn_gear"] = "chest" in overlay_selection
    extra_pal = overlay_palette(out_dir, catalog, overlay_selection)
    if update_gear and not pinned_base:
        raise SystemExit(
            "Gear update needs a pinned base character image. "
            "Pass --base-image, or bake once with --from-image so the tool can pin "
            f"{canonical_base_path(out_dir, name)}."
        )

    sources = find_detail_sources(out_dir, name, from_image)
    method = "detail-image"
    if update_gear and pinned_base:
        if gear_path:
            sources = [gear_path]
            method = "gear-overlay"
        elif use_sd:
            draft = _try_sd_detail(
                fighter,
                out_dir / f"{name}_sd_gear.png",
                reference_image=pinned_base,
                force=True,
            )
            if draft:
                sources = [draft]
                gear_path = pin_gear_image(out_dir, name, draft)
                method = "gear-sd"
            else:
                sources = [pinned_base]
                method = "base-rebake"
        else:
            sources = [pinned_base]
            method = "base-rebake"
    if not sources and pinned_base:
        sources = [pinned_base]
        method = "base-image"
    if not sources and use_sd:
        draft = _try_sd_detail(
            fighter,
            out_dir / f"{name}_sd_draft.png",
            reference_image=pinned_base,
        )
        if draft:
            sources = [draft]
            method = "detail-sd"
    if not sources and color_mode == "classic":
        allow_silhouette = True
    if not sources:
        if not allow_silhouette:
            raise SystemExit(
                "No detailed source image and SD did not produce one. "
                "Pass --from-image or --base-image, start the SD server, "
                "or pass --allow-silhouette for the old 2-color stamp (it will lack detail)."
            )
        _log("  [tile] WARNING: stamping a silhouette — detail will be lost.")
        method = "silhouette-fallback"

        def bake(frame_i: int, total: int) -> Image.Image:
            if color_mode == "classic":
                return mask_to_classic(render_mask(width, height, fighter, frame_i, total))
            return _bake_truecolor(fighter, width, height, frame_i, total)
    else:
        pin_src = sources[0]
        if pin_src and not update_gear:
            pinned_base = pin_base_image(
                out_dir, name, pin_src, overwrite=save_base
            )
        elif pin_src and save_base:
            pinned_base = pin_base_image(out_dir, name, pin_src, overwrite=True)
        if gear_path:
            gear_path = pin_gear_image(out_dir, name, gear_path)
        flags["worn_gear"] = "chest" in overlay_selection

        hires: List[Image.Image] = []
        for p in sources:
            try:
                hires.append(Image.open(p).convert("RGBA"))
            except Exception as ex:
                _log(f"  [tile] skip {p}: {ex}")
        if not hires:
            raise SystemExit(f"Could not open detail sources: {sources}")

        identity = Image.open(pinned_base).convert("RGBA") if pinned_base else hires[0]
        gear_im = Image.open(gear_path).convert("RGBA") if gear_path else None

        def bake(frame_i: int, total: int) -> Image.Image:
            src = hires[frame_i % len(hires)]
            # 16×24 cannot carry a painting. Sitting-cat layout + palette from the
            # pinned base (gear overlay only tints worn items).
            if width <= 32:
                pal = _palette_from_detail(identity)
                if gear_im is not None:
                    pal.update(_palette_from_gear(gear_im))
                pal.update(extra_pal)
                return _render_feline_truecolor(
                    width, height, fighter, flags, frame_i, total, palette=pal
                ) if color_mode == "truecolor" else mask_to_classic(
                    render_mask(width, height, fighter, frame_i, total)
                )
            paint = gear_im if gear_im is not None else src
            if len(hires) == 1 and total > 1 and gear_im is None:
                paint = _idle_hires(src, frame_i, total, flags)
            tile = _downscale_keep_detail(paint, (width, height))
            if color_mode == "classic":
                return _classic_from_detail(tile)
            return tile

    static = bake(0, 1)
    static_path = tex / f"{name}.png"
    static.save(static_path, "PNG")
    rel_static = f"Creatures/{static_path.name}"

    frame_paths: List[Path] = []
    rel_frames: List[str] = []
    xml_anim = ""
    gif_path = None

    if animated:
        n = max(2, int(frames))
        for i in range(n):
            fr = bake(i, n)
            fp = tex / f"{name}_frame{i:02d}.png"
            fr.save(fp, "PNG")
            frame_paths.append(fp)
            rel_frames.append(f"Creatures/{fp.name}")
        xml_anim = build_animation_xml(rel_frames, animation_length=animation_length)
        try:
            preview = [Image.open(p).convert("RGBA") for p in frame_paths]
            scale = max(1, 96 // width)
            preview = [
                im.resize((width * scale, height * scale), Image.Resampling.NEAREST)
                for im in preview
            ]
            gif_path = out_dir / f"{name}_preview.gif"
            preview[0].save(
                gif_path,
                save_all=True,
                append_images=preview[1:],
                duration=80,
                loop=0,
                disposal=2,
            )
        except Exception as e:
            _log(f"  [tile] GIF preview skipped: {e}")

    pregen = build_pregen_xml(fighter, rel_static, fg, detail)
    pregen_path = out_dir / "EmbarkModules.pregen.snippet.xml"
    pregen_path.write_text(pregen, encoding="utf-8")

    modconfig_snip = None
    if color_mode == "truecolor":
        modconfig_snip = '{\n  "shaderMode": 1\n}\n'
        (out_dir / "modconfig.json.snippet").write_text(modconfig_snip, encoding="utf-8")

    if xml_anim:
        (out_dir / f"{name}.animation.snippet.xml").write_text(xml_anim + "\n", encoding="utf-8")

    manifest = {
        "purpose": "player-tile-replacement",
        "followsQudRestrictions": True,
        "colorMode": color_mode,
        "sizePreset": size,
        "pixelSize": [width, height],
        "aspect": "2:3 (vanilla player tile)",
        "bakeMethod": method,
        "detailSources": [str(p) for p in sources],
        "baseImage": str(pinned_base) if pinned_base else None,
        "gearImage": str(gear_path) if gear_path else None,
        "updateGear": bool(update_gear),
        "wornGearOnTile": bool(flags.get("worn_gear")),
        "overlayCatalog": str(overlay_catalog_path(out_dir)),
        "overlaySelection": overlay_selection,
        "classicChannels": {
            "black": "Foreground / TileColor",
            "white": "DetailColor",
            "transparent": "background (k)",
            "midtoneRGBA": list(BLEND_MID),
        },
        "foreground": fg,
        "detail": detail,
        "staticTile": str(static_path),
        "renderTile": rel_static,
        "animated": animated,
        "frames": [str(p) for p in frame_paths],
        "previewGif": str(gif_path) if gif_path else None,
        "suggestedRender": (
            f'<part Name="Render" Tile="{rel_static}" '
            f'TileColor="&amp;{fg}" DetailColor="{detail}" ColorString="&amp;{fg}" />'
        ),
        "suggestedAnimationPart": xml_anim,
        "pregenSnippet": str(pregen_path),
        "modconfigSnippet": str(out_dir / "modconfig.json.snippet") if color_mode == "truecolor" else None,
        "notes": [
            "Overlays live in overlays/catalog.json (slots: chest, spectacles, claws). Mutations stay on the base. --overlay SLOT=ID applies a stored item; --pin-overlay SLOT=ID --gear-image adds one.",
            "Pin a body painting with --base-image / --save-base (stored as base/{id}_base.png). Later gear swaps pick overlays instead of regenerating the creature.",
            "Worn gear (apron, etc.) is omitted from the base tile and only painted when a gear overlay is supplied.",
            "Vanilla 16×24 (and 2x) uses the sitting-cat pixel layout plus a palette sampled from the base — not a LANCZOS shrink, which reads as a mini elephant.",
            "3x/4x still downscale the detailed painting (gear overlay if present).",
            "Classic mode still uses black/white/transparent, derived from the same layout.",
            "Pass --allow-silhouette only if you explicitly want the old 2-color stamp.",
            "Truecolor requires modconfig.json shaderMode 1 and Arendeth_TruecolorStatus for HP overlay.",
            "Animated frames use AnimatedMaterialGeneric TileAnimationFrames.",
        ],
    }
    man_path = out_dir / f"{name}.tile.json"
    man_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["manifestPath"] = str(man_path)
    return manifest


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Generate CoQ player tiles from detailed art (not silhouettes)")
    p.add_argument("fighter_json", nargs="?", type=Path, default=None)
    p.add_argument("-o", "--out", type=Path, required=True)
    p.add_argument("--size", choices=list(SIZE_PRESETS), default="vanilla",
                   help="vanilla=16x24; 2x/3x/4x for tile-scaling mods")
    p.add_argument("--color-mode", choices=["classic", "truecolor"], default="classic",
                   help="classic=black/white/transparent shader; truecolor needs modconfig")
    p.add_argument("--animated", action="store_true")
    p.add_argument("--frames", type=int, default=DEFAULT_FRAMES)
    p.add_argument("--animation-length", type=int, default=DEFAULT_ANIM_LENGTH)
    p.add_argument("--from-image", type=Path, default=None,
                   help="Detailed painting, SD draft, or a folder of keyframe PNGs")
    p.add_argument("--base-image", type=Path, default=None,
                   help="Canonical body painting (mutations, no swappable outfit). Auto-pinned on first bake.")
    p.add_argument("--gear-image", type=Path, default=None,
                   help="Outfit overlay / updated portrait. Does not replace the base body image.")
    p.add_argument("--save-base", action="store_true",
                   help="Overwrite the pinned base with --from-image / current source")
    p.add_argument("--update-gear", action="store_true",
                   help="Rebake from the pinned base; SD img2img or --gear-image for the new outfit")
    p.add_argument("--overlay", action="append", default=[], metavar="SLOT=ID",
                   help="Apply a stored overlay (repeatable). Slots: chest, spectacles, claws")
    p.add_argument("--pin-overlay", type=str, default=None, metavar="SLOT=ID",
                   help="Store --gear-image (or a palette stub) in the overlay database")
    p.add_argument("--list-overlays", action="store_true",
                   help="Print the overlay catalog for --out and exit")
    p.add_argument("--no-auto-overlays", action="store_true",
                   help="Do not auto-match overlays from equipped items")
    p.add_argument("--sd", action="store_true",
                   help="Generate detailed SD art then downscale (default for truecolor)")
    p.add_argument("--no-sd", action="store_true",
                   help="Do not call SD even in truecolor mode")
    p.add_argument("--allow-silhouette", action="store_true",
                   help="Permit the old 2-color stamp if no detailed source exists")
    args = p.parse_args(argv)
    if args.list_overlays:
        print(json.dumps(list_overlay_catalog(args.out), indent=2))
        return 0
    if not args.fighter_json:
        raise SystemExit("fighter_json is required unless --list-overlays")

    fighter = json.loads(Path(args.fighter_json).read_text(encoding="utf-8"))
    use_sd: Optional[bool]
    if args.no_sd:
        use_sd = False
    elif args.sd:
        use_sd = True
    else:
        use_sd = None
    man = generate_fighter_tiles(
        fighter,
        args.out,
        size=args.size,
        color_mode=args.color_mode,
        animated=args.animated,
        frames=args.frames,
        animation_length=args.animation_length,
        from_image=args.from_image,
        base_image=args.base_image,
        gear_image=args.gear_image,
        save_base=args.save_base,
        update_gear=args.update_gear,
        overlays=args.overlay,
        pin_overlay=args.pin_overlay,
        auto_overlays=not args.no_auto_overlays,
        use_sd=use_sd,
        allow_silhouette=args.allow_silhouette,
    )
    print(json.dumps(man, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
