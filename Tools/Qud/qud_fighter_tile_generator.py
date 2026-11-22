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
        # Body features that only the feline layout and the layer set draw.
        "shell": "carapace" in t,
        "horns": "horn" in t,
        "quills": "quill" in t,
        "legs": "multiplelegs" in compact or "multiple leg" in t,
        "stinger": "stinger" in t,
        "beak": "beak" in t,
        "fur": "thickfur" in compact,
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
    "horn": 255,
    "chitin": 90,
    "chitin_hi": 200,
    "wing": 180,
    "wing_edge": 100,
    "quill": 240,
    "stinger": 255,
    "beak": 230,
    "fur": 140,
    # Mutation layers (_draw_mutation_layer)
    "gas_toxic": 150, "gas_mind": 150, "gas_steam": 200, "breath": 230,
    "spark": 255, "spark_hi": 230, "flame": 200, "flame_hi": 255,
    "frost": 230, "frost_hi": 255, "leaf": 100, "leaf_hi": 150, "slime": 180, "web": 230,
    "glow_eye": 255, "glow_eye_dim": 160, "third_eye": 255, "fang": 255, "tongue": 160, "gill": 50,
    "scale": 50, "scale_hi": 150, "psi": 200, "halo": 255, "halo_hi": 255, "force": 200,
    "shadow": 40, "light": 255, "orbit": 230, "hover": 180, "regen": 230, "heart": 160, "muscle": 110,
    "hook": 240, "feather": 150, "feather_hi": 230, "speed": 200, "albino": 240, "albino_eye": 160,
    "antenna": 160, "antenna_tip": 255, "mandible": 200,
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
    "horn": (0xE8, 0xDC, 0xC0),        # bone
    "chitin": (0x5A, 0x3A, 0x6E),      # carapace plate
    "chitin_hi": (0x8C, 0x5C, 0xA8),   # carapace sheen
    "wing": (0x9A, 0xC8, 0xD8),        # folded membrane
    "wing_edge": (0x15, 0x53, 0x52),   # wing bone / leading edge
    "quill": (0xE8, 0xDC, 0xC0),
    "stinger": (0xCF, 0xC0, 0x41),
    "beak": (0xE9, 0x9F, 0x10),        # O
    "fur": (0x77, 0xBF, 0xCF),         # C shaggy tufts (lightened body when sampled)
    # Mutation layers (_draw_mutation_layer); game palette letters in comments
    "gas_toxic": (0x00, 0xC4, 0x20),   # G corrosive / poison clouds
    "gas_mind": (0xDA, 0x5B, 0xD6),    # M sleep / confusion clouds
    "gas_steam": (0xB1, 0xC9, 0xC3),   # y steam / plasma haze
    "breath": (0xFF, 0xFF, 0xFF),      # Y breath plume
    "spark": (0xCF, 0xC0, 0x41),       # W
    "spark_hi": (0x77, 0xBF, 0xCF),    # C
    "flame": (0xF1, 0x5F, 0x22),       # o
    "flame_hi": (0xE9, 0x9F, 0x10),    # O
    "frost": (0x77, 0xBF, 0xCF),       # C
    "frost_hi": (0xFF, 0xFF, 0xFF),    # Y
    "leaf": (0x00, 0x94, 0x03),        # g
    "leaf_hi": (0x00, 0xC4, 0x20),     # G
    "slime": (0x00, 0xC4, 0x20),       # G
    "web": (0xB1, 0xC9, 0xC3),         # y
    "glow_eye": (0x00, 0xC4, 0x20),    # G night vision
    "glow_eye_dim": (0x00, 0x94, 0x03),# g
    "third_eye": (0xDA, 0x5B, 0xD6),   # M
    "fang": (0xFF, 0xFF, 0xFF),        # Y
    "tongue": (0xE8, 0x9A, 0x9A),      # pink
    "gill": (0xA6, 0x4A, 0x2E),        # r
    "scale": (0x15, 0x53, 0x52),       # darkened body when sampled
    "scale_hi": (0x77, 0xBF, 0xCF),    # lightened body when sampled
    "psi": (0xB1, 0x54, 0xCF),         # m
    "halo": (0xCF, 0xC0, 0x41),        # W
    "halo_hi": (0xFF, 0xFF, 0xFF),     # Y
    "force": (0x00, 0x96, 0xFF),       # B
    "shadow": (0x0F, 0x3B, 0x3A),      # k
    "light": (0xFF, 0xFF, 0xFF),       # Y
    "orbit": (0xB1, 0xC9, 0xC3),       # y floating blades / objects
    "hover": (0x77, 0xBF, 0xCF),       # C
    "regen": (0x00, 0xC4, 0x20),       # G
    "heart": (0xD7, 0x42, 0x00),       # R
    "hook": (0xB1, 0xC9, 0xC3),        # y
    "feather": (0x00, 0x96, 0xFF),     # B
    "feather_hi": (0xDA, 0x5B, 0xD6),  # M
    "speed": (0xFF, 0xFF, 0xFF),       # Y
    "albino": (0xFF, 0xFF, 0xFF),      # Y wash over the body
    "albino_eye": (0xE8, 0x9A, 0x9A),  # pink
    "muscle": (0x77, 0xBF, 0xCF),      # lightened body when sampled
    "antenna": (0x98, 0x87, 0x5F),     # w
    "antenna_tip": (0xD7, 0x42, 0x00), # R blinking light
    "mandible": (0x98, 0x87, 0x5F),    # w insect head mandibles
}

# Translucent roles (truecolor alpha); everything else is opaque.
_ROLE_ALPHA = {
    "gas_toxic": 170, "gas_mind": 170, "gas_steam": 150, "breath": 190, "slime": 220, "web": 200,
    "glow_eye_dim": 170, "psi": 200, "force": 150, "shadow": 180, "hover": 140, "speed": 120,
    "albino": 110,
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


def _stamp_oral_arm(put, arm, frame: int, out: int) -> None:
    """A poison-slime oral arm: the arm along its path (two pixels thick at the shoulder
    root), a heavy club knob with a lit upper-outer edge, and a slime drip that forms
    under the knob and falls on later frames."""
    path, knob, (dx, dy) = arm
    for x, y in path:
        put(x, y, "tendril")
    top = min(y for _, y in knob)
    lit_x = max(x for x, _ in knob) if out > 0 else min(x for x, _ in knob)
    for x, y in knob:
        put(x, y, "tendril_tip" if (y == top or x == lit_x) else "tendril")
    phase = frame % 8
    if phase in (2, 3):
        put(dx, dy, "tendril_tip")
    elif phase in (4, 5):
        put(dx, dy + 1, "tendril_tip")
    elif phase == 6:
        put(dx, dy + 2, "tendril_tip")


def _horn_shape(kind: str, ox: int, oy: int) -> List[Tuple[int, int]]:
    """Horn pixels above a head stamped at (ox, oy): a pair, one centred (unicorn/spiral) horn,
    a casque crest or branching antlers."""
    if kind == "single":
        return [(ox + 2, oy - 1), (ox + 2, oy - 2), (ox + 2, oy - 3)]
    if kind == "casque":
        return [(ox + 1, oy - 1), (ox + 2, oy - 1), (ox + 3, oy - 1), (ox + 2, oy - 2)]
    if kind == "antlers":
        return [(ox + 1, oy - 1), (ox, oy - 2), (ox - 1, oy - 2), (ox, oy - 3),
                (ox + 3, oy - 1), (ox + 4, oy - 2), (ox + 5, oy - 2), (ox + 4, oy - 3)]
    return [(ox + 1, oy - 1), (ox, oy - 2), (ox + 3, oy - 1), (ox + 4, oy - 2)]


def _fill_neck(put, x0: int, y0: int, x1: int, y1: int) -> None:
    """Solid 2px-wide neck so heads do not float as debris."""
    if y1 < y0:
        y0, y1 = y1, y0
    if x1 < x0:
        x0, x1 = x1, x0
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            put(x, y, "body")


# ---------------------------------------------------------------- body plans
#
# Body-plan templates, 16×24, facing right. Row characters:
#   '#' body (fur/hide/wood, shaded)   'y' belly / bib / petals   'd' dark detail
#   'e' eye   'p' paw   't' tail (tail layer)   'a' first arm pair (arms layer)
#   'r' roots (roots layer)
# Anchors a template does not set are derived from its silhouette (_plan_anchors).
# The base of a plan is the body only; heads, arms, legs beyond the plan's own,
# tails, fins, tentacles and roots are layers keyed to the player's real limb
# counts, so the game rebuilds the body from the anatomy the player has now.
_PLAN_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "quadruped": {
        "rows": [
            "", "", "", "", "", "", "", "", "", "",
            "        ###     ",
            "       #####    ",
            "  t   yy#####   ",
            "   t   yy#####  ",
            "   t    ######  ",
            "  t     ######  ",
            " t     #######  ",
            " t     #######  ",
            "  t    ######   ",
            "     ########   ",
            "    #########   ",
            "", "", "",
        ],
        "head": (7, 5),
        "neck": (8, 9, 10, 11),
        "heads": {
            "head2": ((3, 4), (5, 8, 7, 11)),
            "head3": ((11, 4), (11, 8, 12, 11)),
            "head4": ((7, 1), (8, 5, 9, 6)),
        },
        "bib": (6, 8, 12, 14),
        "brood": (2, 11),
        "conjoin": [(13, 15), (14, 16)],
        "claws": [(6, 20), (11, 20)],
        "tendril": (12, 12),
        "vortex": (14, 16),
        "wings": (11, 6, 1),
        "back_side": "right",
        "back_rows": (10, 15),
        "arms": [(13, 19, "body"), (14, 19, "body"), (13, 20, "paw"), (14, 20, "paw")],
        "arms2": [(12, 21, "body"), (13, 21, "paw")],
        "legs": [(5, 21, "paw"), (7, 21, "paw"), (9, 21, "paw"), (11, 21, "paw")],
        "tail_tip": (2, 12),
        "fin": [(9, 9), (10, 9), (10, 8)],
        "fur": [(6, 7), (11, 6), (5, 16), (5, 17), (6, 15), (15, 15)],
    },
    "biped": {
        # Bright Qud proportions (2026-11-07): front-facing, a 6 px torso with a pale
        # tunic strip, arms hanging at the sides one pixel clear of it, legs apart,
        # a 5x5 head (plain style) with room for three heads side by side. Bright Qud
        # adds the dark outline and drop shadow at runtime, so the art has none.
        "rows": [
            "", "", "", "", "", "", "", "",
            "    a######a    ",
            "   aa##yy##aa   ",
            "   a ##yy## a   ",
            "   a ##yy## a   ",
            "   a ##yy## a   ",
            "   a ###### a   ",
            "   a ###### a   ",
            "     ######     ",
            "     ##  ##     ",
            "     ##  ##     ",
            "     ##  ##     ",
            "     ##  ##     ",
            "     ##  ##     ",
            "    ppp  ppp    ",
            "",
            "",
        ],
        "shading": "side",
        "head": (5, 2),
        "neck": (7, 7, 8, 7),
        "heads": {
            "head2": ((0, 3), (4, 7, 5, 8)),
            "head3": ((11, 3), (10, 7, 11, 8)),
            # No room above three heads in 16x24: head4 has no cell on this plan.
            "head4": ((5, -8), (6, -2, 7, -2)),
        },
        "bib": (6, 9, 9, 15),
        "brood": (0, 9),
        "conjoin": [(13, 13), (13, 15)],
        "claws": [(3, 14), (12, 14), (4, 21), (11, 21)],
        "tendril": (10, 8),
        "vortex": (14, 18),
        "wings": (3, 7, -1),
        "back_side": "left",
        "back_rows": (9, 15),
        "arms2": [(2, 11, "body"), (2, 12, "body"), (13, 11, "body"), (13, 12, "body"),
                  (2, 13, "paw"), (13, 13, "paw")],
        "legs": [(7, 17, "body"), (8, 17, "body"), (7, 18, "body"), (8, 18, "body"),
                 (7, 19, "body"), (8, 19, "body"), (7, 20, "paw"), (8, 20, "paw")],
        "tail_rows": [(4, 16), (3, 17), (2, 18), (2, 19), (1, 20)],
        "tail_tip": (1, 20),
        "fur": [(5, 9), (10, 9), (4, 17), (11, 17)],
        # Oral arm (WM Gelatinous Form): the Oral Arm part is only a wrist slot; its
        # Tentacle and Pseudopod are the limbs. One poison-slime trunk rises from the top of
        # the right shoulder beside the side head and forks into two heavy club knobs (they
        # strike as clubs): "tentacles" the trunk and the outer, longer tip, "tentacles2" the
        # inner, shorter tip. Each entry: path (root first), knob pixels, drip start.
        "oral_arms": [
            ([(12, 8), (13, 8), (14, 9), (14, 10), (14, 11), (14, 12), (15, 13), (15, 14), (15, 15)],
             [(14, 16), (15, 16), (14, 17), (15, 17), (15, 18)],
             (15, 19)),
            ([(13, 13), (13, 14)],
             [(12, 15), (13, 15), (12, 16), (13, 16), (12, 17)],
             (12, 18)),
        ],
        # Where held items hang, per extra manipulator in body order (right side; the
        # mod mirrors them for left-side parts): the tentacle and pseudopod knobs.
        "grips": [(15, 17), (12, 16)],
    },
    "serpent": {
        "rows": [
            "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
            "                ",
            "   #####        ",
            "  #yyyyy####    ",
            " ##yyyyyyyy#    ",
            "t###########    ",
            "t ##########    ",
            " t              ",
            "", "",
        ],
        "head": (10, 9),
        "neck": (10, 14, 11, 17),
        "back_side": "top",
        "tail_tip": (1, 21),
    },
    "fish": {
        "rows": [
            "", "", "", "", "", "", "", "", "", "", "",
            "t   ######      ",
            "tt##########    ",
            " ###yyyyyyy##   ",
            "tt##yyyyyyy##   ",
            "t  ########     ",
            "", "", "", "", "", "", "", "",
        ],
        "head": (11, 9),
        "neck": (12, 13, 12, 13),
        "back_side": "top",
        "tail_tip": (0, 11),
        "fin": [(6, 10), (7, 10), (7, 9), (7, 16), (8, 16)],
    },
    "blob": {
        "rows": [
            "", "", "", "", "", "", "", "", "", "", "", "", "",
            "     ######     ",
            "   ##########   ",
            "  ##e######e##  ",
            "  ############  ",
            "  ###yyyyyy###  ",
            "  ############  ",
            " ############## ",
            "  ##  ####  ##  ",
            "", "", "",
        ],
        "back_side": "top",
    },
    "radial": {
        "rows": [
            "", "", "", "", "", "",
            "       ##       ",
            "       ##       ",
            "      ####      ",
            "      ####      ",
            " ############## ",
            "   ##########   ",
            "    ##e##e##    ",
            "     ######     ",
            "    ###yy###    ",
            "   ####  ####   ",
            "  ###      ###  ",
            " ###        ### ",
            " ##          ## ",
            "", "", "", "", "",
        ],
        "head": (6, 1),
        "neck": (7, 5, 8, 5),
        "back_side": "top",
    },
    "robot": {
        "rows": [
            "", "", "", "", "", "", "", "", "",
            "     ######     ",
            "    #e####e#    ",
            "    ########    ",
            "   ##########   ",
            "  ###yyyyyy###  ",
            "  ############  ",
            "  ############  ",
            "   ##########   ",
            "  dddddddddddd  ",
            " dd#dd#dd#dd#dd ",
            "  dddddddddddd  ",
            "", "", "", "",
        ],
        "back_side": "top",
    },
    "tree": {
        "rows": [
            "", "",
            "     ######     ",
            "   ##########   ",
            "  ############  ",
            " ######e##e#### ",
            " ############## ",
            "  ############  ",
            "   ##y####y##   ",
            "    ########    ",
            "      dddd      ",
            "       dd       ",
            "       dd       ",
            "       dd       ",
            "      ddd       ",
            "       dd       ",
            "       ddd      ",
            "       dd       ",
            "       dd       ",
            "      dddd      ",
            "     rr  rr     ",
            "    r      r    ",
            "", "",
        ],
        "arms": [(5, 12, "body"), (4, 11, "body"), (10, 13, "body"), (11, 12, "body")],
        "arms2": [(5, 15, "body"), (4, 14, "body"), (10, 16, "body"), (11, 15, "body")],
        "back_side": "top",
    },
    "flower": {
        "rows": [
            "", "", "", "",
            "      ####      ",
            "    ##yyyy##    ",
            "   ##yyyyyy##   ",
            "   #yyeyyeyy#   ",
            "   ##yyyyyy##   ",
            "    ##yyyy##    ",
            "      ####      ",
            "       dd       ",
            "    dd dd       ",
            "   ddd dd ddd   ",
            "       dd ddd   ",
            "       dd       ",
            "       dd       ",
            "       dd       ",
            "       dd       ",
            "       dd       ",
            "      dddd      ",
            "     r rr r     ",
            "", "",
        ],
        "back_side": "top",
    },
    "fungus": {
        "rows": [
            "", "", "", "", "", "",
            "     ######     ",
            "   ##########   ",
            "  ###y###y####  ",
            " ############## ",
            " ############## ",
            "   yyyyyyyyyy   ",
            "     yeyyey     ",
            "     yyyyyy     ",
            "     yyyyyy     ",
            "     yyyyyy     ",
            "     yyyyyy     ",
            "     yyyyyy     ",
            "    yyyyyyyy    ",
            "   ddd    ddd   ",
            "", "", "", "",
        ],
        "back_side": "top",
    },
    "cactus": {
        "rows": [
            "", "", "", "",
            "      ####      ",
            "     ######     ",
            "     #e##e#     ",
            " #   ######     ",
            " ##  ##y###  #  ",
            " ##  ######  ## ",
            " ##  ###y##  ## ",
            "  ########## ## ",
            "     ##y####### ",
            "     ######     ",
            "     ###y##     ",
            "     ######     ",
            "     ######     ",
            "     ##y###     ",
            "     ######     ",
            "    dddddddd    ",
            "     r rr r     ",
            "", "", "",
        ],
        "back_side": "top",
    },
    "chair": {
        "rows": [
            "", "", "", "", "",
            "   ####         ",
            "   #e#e         ",
            "   ####         ",
            "   ####         ",
            "   ####         ",
            "   ####         ",
            "   ##########   ",
            "   yyyyyyyyyy   ",
            "   ##########   ",
            "   dd      dd   ",
            "   dd      dd   ",
            "   dd      dd   ",
            "   dd      dd   ",
            "   dd      dd   ",
            "   dd      dd   ",
            "   dd      dd   ",
            "", "", "",
        ],
        "head": (3, 0),
        "neck": (4, 4, 5, 4),
        "arms": [(7, 9, "body"), (8, 9, "body"), (9, 9, "body"), (12, 9, "body"), (12, 10, "body")],
        "back_side": "left",
        "back_rows": (5, 11),
    },
    "table": {
        "rows": [
            "", "", "", "", "", "", "", "", "", "",
            "  ############  ",
            "  yyyyyyyyyyyy  ",
            "  ###e####e###  ",
            "  ############  ",
            "   dd      dd   ",
            "   dd      dd   ",
            "   dd      dd   ",
            "   dd      dd   ",
            "   dd      dd   ",
            "   dd      dd   ",
            "   dd      dd   ",
            "", "", "",
        ],
        "back_side": "top",
    },
    "door": {
        "rows": [
            "", "",
            "   ##########   ",
            "   #dddddddd#   ",
            "   #d######d#   ",
            "   #d#e##e#d#   ",
            "   #d######d#   ",
            "   #d######d#   ",
            "   #dddddddd#   ",
            "   #d######d#   ",
            "   #d######d#   ",
            "   #d####yyd#   ",
            "   #d######d#   ",
            "   #d######d#   ",
            "   #dddddddd#   ",
            "   #d######d#   ",
            "   #d######d#   ",
            "   #d######d#   ",
            "   #d######d#   ",
            "   #dddddddd#   ",
            "   ##########   ",
            "", "", "",
        ],
        "head": (6, 0),
        "neck": (7, 2, 8, 2),
        "back_side": "top",
    },
    "vessel": {
        "rows": [
            "", "", "", "", "", "",
            "     ######     ",
            "      ####      ",
            "     ######     ",
            "    ########    ",
            "   ##########   ",
            "   ###e##e###   ",
            "  ############  ",
            "  ####yyyy####  ",
            "  ############  ",
            "   ##########   ",
            "    ########    ",
            "     ######     ",
            "    dddddddd    ",
            "", "", "", "", "",
        ],
        "head": (6, 1),
        "neck": (7, 5, 8, 6),
        "arms": [(1, 10, "body"), (1, 11, "body"), (14, 10, "body"), (14, 11, "body")],
        "back_side": "top",
    },
}

for _plan, _tpl in _PLAN_TEMPLATES.items():
    _tpl["rows"] = [(r or "").ljust(16) for r in _tpl["rows"]]
    assert len(_tpl["rows"]) == 24, (_plan, len(_tpl["rows"]))
    assert all(len(r) == 16 for r in _tpl["rows"]), _plan

# Which vanilla anatomies draw with which plan. The game uses this first; for an
# anatomy it does not know (mods) it decides from the limbs, and between biped and
# quadruped the limbs always decide (3+ feet/legs = quadruped).
PLAN_ANATOMIES: Dict[str, Tuple[str, ...]] = {
    "biped": ("Humanoid", "TailedBiped", "WheeledCreature", "Svardym", "HumanoidRobot",
              "WoodenHumanoid", "HumanoidWithHandsFace", "BipedalRobot",
              "BipedalRobotWithArmatures", "BipedalMechMk3", "Bird"),
    "quadruped": ("Quadruped", "Hexapod", "Frog", "Insect", "Spider", "Crab",
                  "TripedalRobot", "QuadrupedalRobot", "HexapedalRobot"),
    "serpent": ("Snake", "Worm", "Slug", "SlugWithHands", "Snail"),
    "fish": ("Fish",),
    "blob": ("Ooze", "Jelly", "Clam", "Nest", "Motes", "Oddity"),
    "radial": ("Echinoid", "Star", "Three-Pointed Star", "Octohedron", "HumanoidOctohedron"),
    "robot": ("Turret", "TreadedRobot", "WheeledRobot", "HoverRobot", "HoverRobotWithFourArms",
              "WheelRobot", "VanedMechanism", "RailedMechanism"),
    "tree": ("Bush", "Tree", "Vine", "PlantWall"),
    "flower": ("Flower",),
    "fungus": ("Fungus", "FungusWall"),
    "cactus": ("Cactus",),
    "chair": ("Chair", "RockingChair", "PlasticChair", "MetalChair", "AnimalChair"),
    "table": ("Table", "Bed", "PlasticBed", "MetalBed", "AnimalBed", "Chalkboard", "Pillow"),
    "door": ("Door", "MetalDoor", "Wall", "WoodWall", "BoneWall", "LeatherWall", "ClothWall",
             "MetalWall", "GlassWall", "IronMaiden", "Mirror"),
    "vessel": ("Pottery", "AirWell"),
}
ALL_PLANS: Tuple[str, ...] = tuple(_PLAN_TEMPLATES)

_WING_SHAPE = [
    (2, 0, True), (1, 1, False), (2, 1, False), (3, 1, True),
    (0, 2, False), (1, 2, False), (2, 2, False), (3, 2, True),
    (0, 3, False), (1, 3, False), (2, 3, False), (3, 3, False), (4, 3, True),
    (0, 4, False), (1, 4, False), (2, 4, False), (3, 4, False),
    (1, 5, False), (2, 5, False),
]


def _clip(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _plan_anchors(plan: str) -> Dict[str, Any]:
    """Template anchors, filling in the ones a template leaves out from its silhouette."""
    tpl = dict(_PLAN_TEMPLATES[plan])
    pts = [(x, y) for y, row in enumerate(tpl["rows"]) for x, ch in enumerate(row) if ch in "#yde"]
    x0 = min(p[0] for p in pts)
    x1 = max(p[0] for p in pts)
    y0 = min(p[1] for p in pts)
    y1 = max(p[1] for p in pts)
    cx = (x0 + x1) // 2
    my = (y0 + y1) // 2
    hx, hy = tpl.get("head") or (_clip(cx - 1, 0, 12), _clip(y0 - 5, 0, 19))
    tpl["head"] = (hx, hy)
    tpl.setdefault("neck", (hx + 1, hy + 4, hx + 2, max(hy + 4, y0)))

    def neck(ox: int, oy: int) -> Tuple[int, int, int, int]:
        return (ox + 1, oy + 4, ox + 2, max(oy + 4, y0))

    if "heads" not in tpl:
        h2 = (_clip(hx - 4, 0, 12), _clip(hy + 1, 0, 19))
        h3 = (_clip(hx + 4, 0, 12), _clip(hy + 1, 0, 19))
        h4 = (hx, _clip(hy - 4, 0, 19))
        tpl["heads"] = {"head2": (h2, neck(*h2)), "head3": (h3, neck(*h3)), "head4": (h4, (hx + 1, h4[1] + 4, hx + 2, hy))}
    tpl.setdefault("bib", (x0, x1, y0, y1))
    tpl.setdefault("brood", (_clip(x0, 0, 13), _clip(y0 - 1, 0, 21)))
    tpl.setdefault("conjoin", [(_clip(x1 + 1, 0, 15), my), (_clip(x1 + 1, 0, 15), my + 1)])
    tpl.setdefault("claws", [(x0, y1), (x1, y1)])
    tpl.setdefault("tendril", (_clip(x1 - 2, 0, 11), _clip(y0 + 2, 0, 19)))
    tpl.setdefault("vortex", (_clip(x1 + 1, 0, 15), _clip(y0 + 1, 0, 22)))
    tpl.setdefault("wings", (_clip(x0 + 2, 4, 15), _clip(y0 - 3, 0, 18), -1))
    tpl.setdefault("back_side", "top")
    tpl.setdefault("back_rows", (y0, y1))
    side = [(x0 - 1, my, "body"), (x0 - 1, my + 1, "paw"), (x1 + 1, my, "body"), (x1 + 1, my + 1, "paw")]
    tpl.setdefault("arms", side)
    tpl.setdefault("arms2", [(x, y + 2, r) for x, y, r in side])
    tpl.setdefault("legs", [(x0 + 1, y1 + 1, "paw"), (cx, y1 + 1, "paw"), (x1 - 1, y1 + 1, "paw")])
    if not any("t" in r for r in tpl["rows"]):
        tpl.setdefault("tail_rows", [(x0 - 1, y1 - 1), (x0 - 2, y1)])
        tpl.setdefault("tail_tip", (x0 - 2, y1))
    tpl.setdefault("fin", [(cx, y0 - 1), (cx + 1, y0 - 1), (cx + 1, y0 - 2)])
    tpl.setdefault("fur", [(x0 - 1, y0 + 1), (x1 + 1, y0 + 1), (x0 - 1, y1 - 1), (x1 + 1, y1 - 1)])
    tpl.setdefault("tentacles", [(x0 + 1, y1 + 1), (x0 + 1, y1 + 2), (cx, y1 + 1), (cx, y1 + 2),
                                 (x1 - 1, y1 + 1), (x1 - 1, y1 + 2)])
    if not any("r" in r for r in tpl["rows"]):
        tpl.setdefault("roots", [(x0 + 1, y1 + 1), (x1 - 1, y1 + 1), (cx - 1, y1 + 2), (cx + 1, y1 + 2)])
    tpl["extent"] = {}
    for y, row in enumerate(tpl["rows"]):
        xs = [x for x, ch in enumerate(row) if ch in "#ye"]
        if xs:
            tpl["extent"][y] = (min(xs), max(xs))
    cols: Dict[int, int] = {}
    for x, y in pts:
        if x not in cols or y < cols[x]:
            cols[x] = y
    tpl["tops"] = cols
    return tpl


def _stamp_plain_head(put, ox: int, oy: int, *, blink: bool = False, spectacles: bool = False) -> None:
    """Round head for non-feline fighters, same 4×5 footprint as the cat head."""
    for x, y in ((1, 0), (2, 0), (0, 1), (3, 1), (0, 2), (0, 3), (3, 3), (1, 4), (2, 4)):
        put(ox + x, oy + y, "body")
    put(ox + 1, oy + 1, "spectacles" if spectacles else "body")
    put(ox + 2, oy + 1, "spectacles" if spectacles else "body")
    put(ox + 1, oy + 2, "body" if blink else "eye")
    put(ox + 2, oy + 2, "body")
    put(ox + 3, oy + 2, "eye" if not blink else "body")
    put(ox + 1, oy + 3, "muzzle")
    put(ox + 2, oy + 3, "muzzle")


# ---------------------------------------------------------------- head styles
#
# A head is a small grid stamped at the plan's head anchor (and at head2-4), facing
# right. Row 0 of "rows" sits at the anchor's y + "top" (-1 lets antennae, caps or
# leaves rise one pixel above the usual 4×5 footprint). Characters:
#   '#' body ("body" key overrides the role, e.g. bone for skulls)
#   'B' eye that shuts when blinking   'e' eye that never shuts
#   'S' spectacles slot (body unless spectacles are worn)
#   'm' muzzle  'n' nose  'E' ear  'i' inner ear  'b' beak  'h' bone/horn
#   's' stripe/dark line  'A' antenna (stripe)  'y' pale patch (belly colour)
#   'f' fang/teeth  'M' mandible  'l' leaf  'g' gill  '.' nothing
# "mouth" is where tongue and breath start, "fangs" where the fangs layer draws
# (both relative to the anchor). The cat and plain grids are the original stamps.
_HEAD_STYLES: Dict[str, Dict[str, Any]] = {
    "cat": {
        "rows": [".E.E", ".SS#", "#B#m", ".#mm", "..#."],
        "mouth": (4, 3), "fangs": [(3, 4), (4, 4)],
        "keywords": (),
    },
    "plain": {
        # Front-facing like Bright Qud's humanoids (2026-11-07); was a 4x5 side blob.
        "rows": [".###.", "#SSS#", "#B#B#", "##m##", ".###."],
        "mouth": (2, 4), "fangs": [(1, 3), (3, 3)],
        "keywords": (),
    },
    "canine": {
        "rows": ["E.E..", "#SS#.", "#B##m", ".#mmn", "..#.."],
        "mouth": (5, 3), "fangs": [(3, 4), (4, 4)],
        "keywords": ("dog", "dogs", "hound", "hounds", "wolf", "wolves", "jackal", "fox", "coyote",
                     "canine", "hyena", "mastiff", "goatfolk"),
    },
    "equine": {
        "rows": ["E.E..", "#SS#.", "#B###", ".##mm", "..mmn"],
        "mouth": (5, 4), "fangs": [(3, 5), (4, 5)],
        "keywords": ("horse", "pony", "donkey", "camel", "goat", "deer", "antelope", "equine", "ram",
                     "sheep", "cow", "bull", "ox", "dromad", "dromads", "hoofed"),
    },
    "avian": {
        "rows": [".##..", "#SS#.", "#B#bb", ".##b.", "..#.."],
        "mouth": (5, 2), "fangs": [(3, 4)],
        "keywords": ("bird", "birds", "avian", "falcon", "hawk", "owl", "crow", "raven", "eagle",
                     "feathered", "roc", "chicken", "batfolk", "chiromorph", "harpy"),
    },
    "reptile": {
        "rows": [".....", ".SS#.", "#B##n", "#sss.", ".##.."],
        "mouth": (4, 3), "fangs": [(3, 4)],
        "keywords": ("lizard", "snake", "serpent", "reptile", "reptilian", "dragon", "croc", "crocodile",
                     "gecko", "salamander", "newt", "frog", "toad", "saurian", "naga", "kobold"),
    },
    "insect": {
        "top": -1,
        "rows": ["..A.A", ".A#A.", "#SS#.", "#BB#.", ".##MM", "..#.."],
        "mouth": (5, 3), "fangs": [(4, 4)],
        "keywords": ("insect", "insects", "bug", "beetle", "ant", "ants", "spider", "arachnid", "mantis",
                     "moth", "wasp", "bee", "broodling", "centipede", "millipede", "scorpion", "tick",
                     "hive", "chitinous", "mandibore", "girshling"),
    },
    "fish": {
        "rows": [".....", "##SS.", "#g#B#", "#g##m", ".###."],
        "mouth": (5, 3), "fangs": [(4, 4)],
        "keywords": ("fish", "porpoise", "dolphin", "shark", "eel", "aquatic", "merfolk", "carp",
                     "piranha", "angler", "gilled"),
    },
    "robot": {
        "top": -1,
        "rows": ["..A..", ".###.", "#SSS#", "#BBB#", "#s#s#", ".###."],
        "mouth": (5, 3), "fangs": [(2, 5)],
        "keywords": ("robot", "robots", "android", "machine", "mechanical", "mech", "automaton",
                     "synth", "golem", "construct", "chromeling", "drone", "turret", "mechanimist"),
    },
    "skull": {
        "body": "horn",
        "rows": [".###.", "#SS##", "#B#B#", ".#s#.", ".f.f."],
        "mouth": (4, 3), "fangs": [(1, 4), (3, 4)],
        "keywords": ("skeleton", "skull", "undead", "lich", "ghoul", "zombie", "revenant", "bones",
                     "necromancer", "necromancy", "deathless", "husk"),
    },
    "fungal": {
        "top": -1,
        "rows": [".###.", "##y##", "#y##y", ".B#B.", ".#m#.", "..#.."],
        "mouth": (4, 3), "fangs": [(2, 4)],
        "keywords": ("fungus", "fungal", "mushroom", "myco", "mycologist", "spore", "spores", "mold",
                     "lichen", "shroom", "hypha"),
    },
    "plant": {
        "top": -1,
        "rows": ["l.l..", ".l#l.", "#SS#.", "#B#B.", ".mm#.", "..#.."],
        "mouth": (4, 3), "fangs": [(1, 4), (2, 4)],
        "keywords": ("plant", "plants", "flower", "vine", "tree", "dryad", "leaf", "leaves", "bloom",
                     "sapling", "briar", "photosynthetic", "barkflesh", "treant", "seedling"),
    },
}
HEAD_STYLES: Tuple[str, ...] = tuple(_HEAD_STYLES)
# Keyword order: the first style whose word appears wins (cat comes from feline fighters).
_HEAD_STYLE_ORDER = ("robot", "skull", "insect", "fish", "avian", "reptile", "canine", "equine",
                     "fungal", "plant")
_HEAD_CHAR_ROLES = {
    "#": "body", "B": "eye", "e": "eye", "S": "body", "m": "muzzle", "n": "nose", "E": "ear",
    "i": "inner_ear", "b": "beak", "h": "horn", "s": "stripe", "A": "stripe", "y": "belly",
    "f": "fang", "M": "mandible", "l": "leaf", "g": "gill",
}


def head_style(fighter: Dict[str, Any], flags: Optional[Dict[str, bool]] = None) -> str:
    """The fighter's head style: its "headStyle" field, cat for feline fighters, else the
    first style whose keyword is a word of its name, genotype, mutations or description,
    else plain."""
    want = str(fighter.get("headStyle") or "").strip().lower()
    if want in _HEAD_STYLES:
        return want
    flags = flags if flags is not None else _feature_flags(fighter)
    if flags.get("feline"):
        return "cat"
    text = " ".join(
        [_labels(fighter)]
        + [str(fighter.get(k) or "") for k in ("tile", "genotype", "subtype", "type_name", "name", "id",
                                               "description")]
    ).lower()
    words = set(re.findall(r"[a-z]+", text))
    for style in _HEAD_STYLE_ORDER:
        if any(k in words for k in _HEAD_STYLES[style]["keywords"]):
            return style
    return "plain"


def _head_grid(style: str) -> List[Tuple[int, int, str]]:
    spec = _HEAD_STYLES.get(style) or _HEAD_STYLES["plain"]
    top = int(spec.get("top", 0))
    return [(x, y + top, ch) for y, row in enumerate(spec["rows"]) for x, ch in enumerate(row) if ch != "."]


def _stamp_styled_head(style: str):
    """A stamp with the signature of _stamp_cat_head for one head style."""
    spec = _HEAD_STYLES.get(style) or _HEAD_STYLES["plain"]
    body_role = spec.get("body", "body")
    cells = _head_grid(style)

    def stamp(put, ox: int, oy: int, *, blink: bool = False, spectacles: bool = False) -> None:
        for x, y, ch in cells:
            if ch == "B":
                role = body_role if blink else "eye"
            elif ch == "S":
                role = "spectacles" if spectacles else body_role
            elif ch == "#":
                role = body_role
            else:
                role = _HEAD_CHAR_ROLES[ch]
            put(ox + x, oy + y, role)

    return stamp


def _style_of(flags: Dict[str, Any]) -> str:
    style = flags.get("head_style")
    if style in _HEAD_STYLES:
        return style
    return "cat" if flags.get("feline") else "plain"


def _kitty_roles(
    fighter: Dict[str, Any],
    flags: Dict[str, bool],
    frame: int,
    total_frames: int,
    layer: Optional[str] = None,
    plan: str = "quadruped",
) -> Dict[Tuple[int, int], str]:
    """Roles for one body plan of _PLAN_TEMPLATES.

    layer=None draws the whole fighter from its flags (the classic single bake, on
    the sitting-cat quadruped). layer="base" draws just the plan's body; any other
    layer id one feature (a limb, a mutation, a worn item), whatever the fighter has,
    so the game can stack what matches the player's body at the time.
    """
    tpl = _plan_anchors(plan if plan in _PLAN_TEMPLATES else "quadruped")
    style = _style_of(flags)
    stamp_head = _stamp_cat_head if style == "cat" else _stamp_styled_head(style)
    roles: Dict[Tuple[int, int], str] = {}
    tail_up = 1 if frame % 4 >= 2 else 0
    pulse = 1 if frame % 2 == 0 and (flags.get("brood") or layer == "brood") else 0
    heads = _head_count(fighter, flags)
    blink_i = (frame % heads) if flags.get("blink") and heads > 1 else -1
    full = layer is None

    def on(name: str, flag: bool = False) -> bool:
        return layer == name or (full and flag)

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
                "horn",
                "beak",
                "stinger",
                "chitin",
                "chitin_hi",
                "mandible",
                "fang",
                "leaf",
                "gill",
            ):
                if role == "body":
                    return
            roles[(x, y)] = role

    def shade(x: int, y: int, yy: int) -> None:
        if tpl.get("shading") == "side" and layer != "astral":
            # Bright Qud style: flat material, the right-hand edge of each row in shadow.
            span = tpl["extent"].get(y)
            put(x, yy, "stripe" if span and x == span[1] and span[1] > span[0] else "body")
            return
        h = (x * 7 + y * 13 + frame) % 14
        if layer == "astral":
            if h == 1:
                put(x, yy, "vortex")
            return
        if h == 0:
            put(x, yy, "stripe")
        elif h == 1 and full and flags.get("astral"):
            put(x, yy, "vortex")
        else:
            put(x, yy, "body")

    bx0, bx1, by0, by1 = tpl["bib"]
    draw_tail = on("tail", bool(flags.get("tail")))
    if full or layer in ("base", "apron", "astral", "tail", "arms", "roots"):
        for y, row in enumerate(tpl["rows"]):
            for x, ch in enumerate(row):
                if ch == " ":
                    continue
                if ch == "t":
                    if draw_tail:  # the tail bobs on the idle beat
                        shade(x, y, y - tail_up)
                    continue
                if ch == "a":
                    if full or layer == "arms":
                        shade(x, y, y)
                    continue
                if ch == "r":
                    if on("roots", True):
                        put(x, y, "stripe")
                    continue
                if layer in ("tail", "arms", "roots"):
                    continue
                if ch == "y":
                    bib = by0 <= y <= by1 and bx0 <= x <= bx1
                    if full:
                        put(x, y, "apron" if flags.get("worn_gear") and bib else "belly")
                    elif layer == "base":
                        put(x, y, "belly")
                    elif layer == "apron" and bib:
                        put(x, y, "apron")
                    continue
                if layer == "apron":
                    continue
                if ch in "pde":
                    if full or layer == "base":
                        put(x, y, {"p": "paw", "d": "stripe", "e": "eye"}[ch])
                    continue
                shade(x, y, y)
    if draw_tail:
        for x, y in tpl.get("tail_rows", []):
            shade(x, y, y - tail_up)
    if layer == "roots":
        for x, y in tpl.get("roots", []):
            put(x, y, "stripe")

    # Main head (Head part 1), with its neck.
    hx, hy = tpl["head"]
    if on("head1", True):
        stamp_head(put, hx, hy, blink=full and blink_i == 0, spectacles=full)
        _fill_neck(put, *tpl["neck"])
    if layer == "spectacles":
        for x, y in _head_spectacles(hx, hy, style):
            put(x, y, "spectacles")
    if layer == "blink" and frame % 4 == 3:
        # Blinking Tic: the main head's eyes shut every fourth frame.
        lid = (_HEAD_STYLES.get(style) or {}).get("body", "body")
        for x, y in _head_blink_eyes(hx, hy, style):
            put(x, y, lid)

    for i, lid in enumerate(("head2", "head3", "head4")):
        if on(lid, heads >= i + 2):
            (ox, oy), nk = tpl["heads"][lid]
            stamp_head(put, ox, oy, blink=(blink_i == i + 1))
            _fill_neck(put, *nk)

    if on("brood", flags.get("brood", False)):
        hi = "sack_hi" if pulse else "sack"
        sx, sy = tpl["brood"]
        # Brood sack on the rump / back, not floating mid-air.
        for dx, dy, role in (
            (1, 0, "sack"), (2, 0, hi),
            (0, 1, "sack"), (1, 1, hi), (2, 1, "sack"),
            (1, 2, "sack"),
        ):
            put(sx + dx, sy + dy, role)

    conjoin_lvl = _mutation_level(fighter, "conjoin") or 1
    if on("conjoined", flags.get("conjoined", False)):
        put(*tpl["conjoin"][0], "conjoin")
    if on("conjoined2", flags.get("conjoined", False) and conjoin_lvl >= 2):
        put(*tpl["conjoin"][1], "conjoin")

    if on("claws", bool(flags.get("claws") or flags.get("astral") or flags.get("overlay_claws"))):
        for x, y in tpl["claws"]:
            put(x, y, "claw")

    oral = tpl.get("oral_arms")
    if on("tendril", flags.get("slime", False)):
        # One oral-arm tendril (Gelatinous Form), not extra legs. Plans with drawn oral
        # arms reuse the first one, so the tendril and the limb layer never make two.
        if oral:
            _stamp_oral_arm(put, oral[0], frame, 1)
        else:
            _stamp_tendril_arm(put, *tpl["tendril"], frame)

    if oral:
        for i, lid in enumerate(("tentacles", "tentacles2")):
            if layer == lid and i < len(oral):
                _stamp_oral_arm(put, oral[i], frame, 1)
    elif layer == "tentacles":
        for i, (x, y) in enumerate(tpl["tentacles"]):
            put(x + ((frame // 2 + i) % 2 if y % 2 else 0), y, "tendril_tip" if i % 2 else "tendril")

    if on("vortex", flags.get("vortex", False)):
        vx, vy = tpl["vortex"]
        put(vx, vy + (frame % 2), "vortex")

    for base_id, kind in (("horns", "pair"), ("unihorn", "single"), ("antlers", "antlers"), ("casque", "casque")):
        for n in range(1, 5):
            lid = base_id if n == 1 else f"{base_id}{n}"
            want = on(lid, flags.get("horns", False)) if lid == "horns" else layer == lid
            if not want:
                continue
            if n == 1:
                ox, oy = hx, hy
            elif f"head{n}" in tpl.get("heads", {}):
                (ox, oy), _neck = tpl["heads"][f"head{n}"]
            else:
                continue
            for x, y in _horn_shape(kind, ox, oy):
                put(x, y, "horn")

    if layer == "foot_paws":
        # Clawed paws: the body's lowest row widened by a pixel each side, claw tips under it.
        base = _kitty_roles(fighter, flags, frame, total_frames, "base", plan)
        if base:
            ymax = max(y for _, y in base)
            xs = sorted(x for x, y in base if y == ymax)
            runs: List[List[int]] = []
            for x in xs:
                if runs and x == runs[-1][-1] + 1:
                    runs[-1].append(x)
                else:
                    runs.append([x])
            for run in runs:
                for x in range(run[0] - 1, run[-1] + 2):
                    put(x, ymax, "paw")
                cy = ymax + 1 if ymax + 1 < 24 else ymax
                for x in range(run[0] - 1, run[-1] + 2, 2):
                    put(x, cy, "claw")

    if on("wings", flags.get("wings", False)):
        # Folded wing rising behind the back (a back layer: drawn under the body).
        lift = 1 if frame % 4 >= 2 else 0
        ax, ay, d = tpl["wings"]
        for dx, dy, edge in _WING_SHAPE:
            put(ax + d * dx, ay + dy - lift, "wing_edge" if edge else "wing")

    ext = tpl["extent"]
    r0, r1 = tpl["back_rows"]
    side = tpl["back_side"]
    if on("carapace", flags.get("shell", False)):
        # Chitin plates along the back.
        if side == "top":
            for x, y in tpl["tops"].items():
                for yy in (y, y + 1):
                    put(x, yy, "chitin_hi" if (x + yy) % 3 == 0 else "chitin")
        else:
            for y in range(r0 + 1, r1 + 1):
                if y not in ext:
                    continue
                x0, x1 = ext[y]
                cols = range(max(x0, x1 - 3), x1) if side == "right" else range(x0 + 1, min(x1, x0 + 4))
                for x in cols:
                    put(x, y, "chitin_hi" if (x + y) % 3 == 0 else "chitin")

    if on("quills", flags.get("quills", False)):
        # Spines standing off the back edge.
        if side == "top":
            for x, y in tpl["tops"].items():
                if x % 2 == 0:
                    put(x, y - 1, "quill")
        else:
            for y in range(r0, r1):
                if y in ext:
                    put(ext[y][1] + 1 if side == "right" else ext[y][0] - 1, y - 1, "quill")

    if layer == "fin":
        for x, y in tpl["fin"]:
            put(x, y, "chitin")

    # First arm pair: drawn by the template ('a') or, if it has none, stamped beside
    # the body (a cat with arms). The second pair needs a third arm.
    if on("arms", flags.get("arms", False)) and not any("a" in r for r in tpl["rows"]):
        for x, y, role in tpl.get("arms", []):
            put(x, y, role)
    if layer == "arms2":
        for x, y, role in tpl.get("arms2", []):
            put(x, y, role)

    if on("legs", flags.get("legs", False)):
        for x, y, role in tpl["legs"]:
            put(x, y, role)

    if on("stinger", flags.get("stinger", False)):
        tx, ty = tpl.get("tail_tip", (0, 0))
        for x, y in ((tx, ty - 1), (tx - 1, ty - 2), (tx - 1, ty - 3)):
            put(x, y - tail_up, "stinger")

    if on("beak", flags.get("beak", False)):
        mx, my_ = _HEAD_STYLES[style]["mouth"]
        for x, y in ((mx, my_ - 1), (mx, my_), (mx + 1, my_)):
            put(hx + x, hy + y, "beak")

    if on("fur", flags.get("fur", False)):
        for x, y in tpl["fur"]:
            put(x, y, "fur")

    if layer in _MUTATION_LAYER_IDS:
        _draw_mutation_layer(put, roles, tpl, layer, frame, style)

    return roles


def _silhouette(tpl: Dict[str, Any]) -> Tuple[set, List[Tuple[int, int]]]:
    """Body pixels of a plan (no tail, arms or roots) and the empty ring around them."""
    body = {(x, y) for y, row in enumerate(tpl["rows"]) for x, ch in enumerate(row) if ch in "#ydep"}
    ring = sorted(
        {
            (x + dx, y + dy)
            for x, y in body
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            if (x + dx, y + dy) not in body and 0 <= x + dx < 16 and 0 <= y + dy < 24
        },
        key=lambda p: (p[1], p[0]),
    )
    return body, ring


def _head_eyes(hx: int, hy: int, style: str) -> List[Tuple[int, int]]:
    """Eye pixels of a head style."""
    return [(hx + x, hy + y) for x, y, ch in _head_grid(style) if ch in "Be"]


def _head_blink_eyes(hx: int, hy: int, style: str) -> List[Tuple[int, int]]:
    """Eye pixels that shut when blinking."""
    return [(hx + x, hy + y) for x, y, ch in _head_grid(style) if ch == "B"]


def _head_spectacles(hx: int, hy: int, style: str) -> List[Tuple[int, int]]:
    """Where spectacles sit: the style's slots, else just above its eyes."""
    slots = [(hx + x, hy + y) for x, y, ch in _head_grid(style) if ch == "S"]
    return slots or [(x, y - 1) for x, y in _head_eyes(hx, hy, style)]


def _head_cells(hx: int, hy: int, style: str) -> List[Tuple[int, int]]:
    """Every pixel a head style covers."""
    return sorted((hx + x, hy + y) for x, y, _ch in _head_grid(style))


def _draw_mutation_layer(put, roles, tpl: Dict[str, Any], layer: str, frame: int, style: str) -> None:
    """Mutation layers beyond the original set (vanilla and modded mutations).

    Every animation repeats every 8 frames, so a template sheet with 8 columns
    serves fighters of any frame count. Layers marked requires=head1 draw on the
    main head's anchor.
    """
    f8 = frame % 8
    body, ring = _silhouette(tpl)
    xs = [x for x, _ in body]
    ys = [y for _, y in body]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    cx, my = (x0 + x1) // 2, (y0 + y1) // 2
    hx, hy = tpl["head"]
    tops = tpl["tops"]
    ext = tpl["extent"]

    def scatter(role: str, every: int, seed: int, *, lower: bool = False, upper: bool = False, drift: int = 0) -> None:
        for x, y in ring:
            if lower and y < my:
                continue
            if upper and y > my:
                continue
            if (x * 31 + y * 17 + seed + f8 * 5) % every == 0:
                put(x, y - drift, role)

    if layer in ("gas_toxic", "gas_mind", "gas_steam"):
        # Clouds seeping from the lower body, rising on the idle beat.
        rise = (f8 // 2) % 2
        scatter(layer, 3, {"gas_toxic": 1, "gas_mind": 5, "gas_steam": 9}[layer], lower=True, drift=rise)
        for i in range(3):
            put(x0 - 1 - (i % 2), my - 2 * i - rise, layer)
    elif layer == "breath":
        puff = f8 % 2
        mx, my_ = _HEAD_STYLES[style]["mouth"]
        bx, by = hx + mx, hy + my_
        for x, y in ((bx, by), (bx + 1, by - 1 + puff), (bx + 2, by), (bx + 1, by + 1 - puff),
                     (bx + 3, by - 1 + puff)):
            put(x, y, "breath")
    elif layer == "sparks":
        scatter("spark", 7, 3)
        scatter("spark_hi", 11, 8)
    elif layer == "flames":
        for x, y in tops.items():
            if (x + f8) % 3 == 0:
                put(x, y - 1, "flame")
            if (x + f8) % 6 == 0:
                put(x, y - 2, "flame_hi")
        scatter("flame", 6, 7)
        scatter("flame_hi", 13, 2, upper=True)
    elif layer == "frost":
        scatter("frost", 6, 2)
        for x, y in tops.items():
            if x % 3 == 1:
                put(x, y, "frost_hi")
    elif layer == "leaves":
        for x, y in sorted(body):
            h = (x * 7 + y * 11) % 9
            if h == 0:
                put(x, y, "leaf")
            elif h == 4:
                put(x, y, "leaf_hi")
    elif layer == "slime":
        bottoms: Dict[int, int] = {}
        for x, y in body:
            if y > bottoms.get(x, -1):
                bottoms[x] = y
        for x, y in sorted(bottoms.items()):
            if x % 3 == f8 % 3:
                put(x, y + 1, "slime")
                if (x + f8) % 2 == 0:
                    put(x, y + 2, "slime")
        for x, y in sorted(body):
            if (x * 5 + y * 3) % 13 == 0:
                put(x, y, "slime")
    elif layer == "webs":
        for i in range(5):
            put(x0 - 1 - i, y0 + i, "web")
            put(x0 - 1 - i, y0 + 2 + 2 * i, "web")
        for i in range(3):
            put(x0 - 2 - i, y0 + 3, "web")
    elif layer == "ears":
        for x, y, role in ((hx, hy - 1, "ear"), (hx + 1, hy - 1, "inner_ear"), (hx + 1, hy - 2, "ear"),
                           (hx + 3, hy - 1, "ear"), (hx + 4, hy - 1, "inner_ear"), (hx + 4, hy - 2, "ear")):
            put(x, y, role)
    elif layer == "glow_eyes":
        for x, y in _head_eyes(hx, hy, style):
            put(x, y, "glow_eye")
            if f8 % 4 < 2:
                put(x - 1, y, "glow_eye_dim")
    elif layer == "third_eye":
        put(hx + 2, hy + 1, "third_eye")
        if f8 == 3:
            put(hx + 2, hy + 1, "body")  # it blinks too
    elif layer == "fangs":
        for x, y in _HEAD_STYLES[style]["fangs"]:
            put(hx + x, hy + y, "fang")
    elif layer == "tongue":
        lick = f8 % 4 >= 2
        mx, my_ = _HEAD_STYLES[style]["mouth"]
        tx, ty = hx + mx, hy + my_
        put(tx, ty, "tongue")
        put(tx + 1, ty + (1 if lick else 0), "tongue")
        if lick:
            put(tx + 2, ty + 1, "tongue")
    elif layer == "gills":
        nx0, ny0, nx1, ny1 = tpl["neck"]
        for x, y in ((min(nx0, nx1), min(ny0, ny1)), (max(nx0, nx1), min(ny0, ny1)), (hx + 1, hy + 4)):
            put(x, y, "gill")
    elif layer == "scales":
        for x, y in sorted(body):
            k = (x + 2 * y) % 4
            if k == 0:
                put(x, y, "scale")
            elif k == 2 and (x + y) % 3 == 0:
                put(x, y, "scale_hi")
    elif layer == "muscle":
        # Bulging shoulders: two pixels out on both sides of the upper body.
        for i, y in enumerate(sorted(ext)[:4]):
            a, b = ext[y]
            out = 2 if i in (1, 2) else 1
            for d in range(1, out + 1):
                put(a - d, y, "muscle")
                put(b + d, y, "muscle")
            put(a, y, "stripe")
            put(b, y, "stripe")
    elif layer == "humps":
        # Humps rise from the back: the top edge, or the left/right side the plan's
        # back faces (a sitting quadruped's back is its right edge).
        side = tpl["back_side"]
        r0, r1 = tpl["back_rows"]
        if side == "top":
            mid = sorted(tops)
            span = mid[len(mid) // 3: len(mid) - len(mid) // 3] or mid
            for x in span:
                y = tops[x]
                put(x, y - 1, "muscle")
                put(x, y - 2, "stripe" if x in (span[0], span[-1]) else "muscle")
        else:
            rows = [y for y in range(r0, r1 + 1) if y in ext]
            span = rows[len(rows) // 4: len(rows) - len(rows) // 4] or rows
            for y in span:
                a, b = ext[y]
                edge, step = (b, 1) if side == "right" else (a, -1)
                put(edge + step, y, "muscle")
                put(edge + 2 * step, y, "stripe" if y in (span[0], span[-1]) else "muscle")
    elif layer == "speed":
        shift = f8 % 2
        for y in range(my - 2, my + 3, 2):
            for d in (2, 3, 5):
                put(x0 - d - shift, y, "speed")
    elif layer == "hooks":
        for x, y in tpl["claws"]:
            put(x + 1, y, "hook")
            put(x + 1, y - 1, "hook")
    elif layer == "heart":
        bx0, bx1, by0, by1 = tpl["bib"]
        hxc, hyc = (bx0 + bx1) // 2, by0 + 1
        beat = f8 % 4 == 0
        for x, y in ((hxc, hyc), (hxc + 1, hyc), (hxc, hyc + 1)) + (((hxc - 1, hyc),) if beat else ()):
            put(x, y, "heart")
    elif layer == "regen":
        if ring:
            for k in (0, 3):
                x, y = ring[((f8 + k) * 7) % len(ring)]
                for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                    put(x + dx, y + dy, "regen")
    elif layer == "psi":
        cells = _head_cells(hx, hy, style)
        around = sorted({(x + dx, y + dy) for x, y in cells for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))}
                        - set(cells))
        for i, (x, y) in enumerate(around):
            if (i + f8) % 3 == 0:
                put(x, y, "psi")
    elif layer == "halo":
        for x in range(hx, hx + 4):
            put(x, hy - 2, "halo_hi" if x in (hx + 1, hx + 2) else "halo")
    elif layer == "force":
        rx, ry = (x1 - x0) // 2 + 2, (y1 - y0) // 2 + 2
        for i in range(48):
            t = 2 * math.pi * i / 48
            if (i + f8) % 2:
                continue
            put(int(round(cx + rx * math.cos(t))), int(round(my + ry * math.sin(t))), "force")
    elif layer == "shadow":
        scatter("shadow", 4, 6, lower=True)
        scatter("shadow", 9, 1, upper=True)
    elif layer == "light":
        scatter("light", 9, 4)
    elif layer == "orbit":
        rx, ry = (x1 - x0) // 2 + 2, (y1 - y0) // 2 + 2
        for k in (0, 4):
            t = 2 * math.pi * ((f8 + k) % 8) / 8
            ox, oy = int(round(cx + rx * math.cos(t))), int(round(my + ry * 0.5 * math.sin(t)))
            put(ox, oy, "orbit")
            put(ox + 1, oy, "orbit")
    elif layer == "levitate":
        for x in range(x0 + 1, x1):
            if (x + f8) % 2 == 0:
                put(x, y1 + 2, "hover")
    elif layer == "feathers":
        for x, y in tops.items():
            if x % 2 == 0:
                put(x, y - 1, "feather_hi" if x % 4 == 0 else "feather")
                put(x, y, "feather")
    elif layer == "albino":
        for x, y in sorted(body):
            put(x, y, "albino")
    elif layer == "antenna":
        # Sensor mast on the top of the body (robot scanners, targeting, radar).
        top = min(tops.values())
        ax = min((x for x, y in tops.items() if y == top), key=lambda x: abs(x - cx))
        for d in (1, 2, 3):
            put(ax, top - d, "antenna")
        put(ax, top - 4, "antenna_tip" if f8 % 4 < 2 else "antenna")
    elif layer == "albino_head":
        for x, y in _head_cells(hx, hy, style):
            put(x, y, "albino")
        for x, y in _head_eyes(hx, hy, style):
            put(x, y, "albino_eye")


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
    layer: Optional[str] = None,
) -> Image.Image:
    """Classic luminance: sw_kitty silhouette + extra heads + sack on back."""
    small = Image.new("L", (16, 24), 0)
    px = small.load()
    for (x, y), role in _kitty_roles(fighter, flags, frame, total_frames, layer).items():
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
    layer: Optional[str] = None,
) -> Image.Image:
    """Truecolor sitting-cat layout. Each role keeps its own color.

    layer: None = the whole fighter; otherwise one layer of the layer set (see
    _kitty_roles). Phasing translucency is a whole-fighter effect, so layers stay
    opaque and the game fades the base when the player phases.
    """
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
        if "body" in palette and "fur" not in palette:
            # Shaggy fur tufts: the sampled body colour, lifted toward white.
            pal["fur"] = tuple(min(255, int(c + (255 - c) * 0.35)) for c in pal["body"])
    phase = flags.get("phase") and layer is None
    body_a = 210 if phase else 255
    small = Image.new("RGBA", (16, 24), (0, 0, 0, 0))
    px = small.load()
    for (x, y), role in _kitty_roles(fighter, flags, frame, total_frames, layer).items():
        rgb = pal.get(role) or _FELINE_RGB.get(role, pal["body"])
        a = body_a if role in ("body", "ear", "stripe", "tendril") and phase else 255
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


# ---------------------------------------------------------------- layered fighters
#
# A layered fighter ships, per body plan, one sprite sheet: row 0 the plan's base
# body, then one row per layer; columns are animation frames (a row that does not
# animate has one). Arendeth_CYFTiles picks the plan from the player's anatomy and
# limbs and stacks the layers whose conditions match, so a limb or mutation gained or
# lost later shows without a re-bake. Body plans cover creatures, plants and the
# furniture/walls/doors that Animate Object brings to life (PLAN_ANATOMIES).
#
# Layer conditions (any match turns a layer on):
#   mutations / equipped / effects  lowercase letter/digit substrings of the player's
#       mutation class + display name, worn item blueprint + name, effect class name
#   limbs   "#class:N" = at least N limbs of that class (#head, #arm, #leg, #tail,
#       #fin, #tentacle, #roots, #wing; decided from each part's own variant name,
#       so modded parts such as Spider-Leg or Hypha Head count), or "Part Type:N" =
#       at least N parts of that type or variant
#   minLevel  a matching mutation must be at least this level
#   requires  another layer of the plan that must be on too (horns need a head)
#   covers    mutation tokens this layer stands for, so Bright Qud does not add its
#             own layer for the same thing
# z: "back" under the base body, "front" over it, "fade" = no image, the base's
# alpha is scaled to fade/255. List order is stacking order within a z.
# Mutation tokens cover vanilla and the mods scanned by cyf_scan_content.py
# (CYFTemplates/coverage.md lists which mutation lands on which layer).
# Horn variant tokens (mutation class + variant + display name, lowercase letters/digits).
_HORN_SINGLE = ("hornssingle", "hornsplussingle", "hornsspiral", "hornsplusspiral", "spiralhorn", "unicorn")
_HORN_ANTLERS = ("antler",)
_HORN_CASQUE = ("casque",)
_HORN_NOT_PAIR = _HORN_SINGLE + _HORN_ANTLERS + _HORN_CASQUE

_LAYER_DEFS: List[Dict[str, Any]] = [
    # ---- behind the body
    {"id": "wings", "z": "back", "mutations": ("wing",), "limbs": ("#wing:1",)},
    {"id": "gas_toxic", "z": "back", "mutations": (
        "corrosivegas", "poisongas", "defoliant", "fungicide", "slogglands", "bilgesphincter",
        "sporepuff", "corrosivebreath", "poisonbreath", "stinkybreath", "sulfur")},
    {"id": "gas_mind", "z": "back", "mutations": (
        "sleepgas", "confusiongas", "normalitygas", "sleepbreath", "confusingbreath",
        "confusionbreath", "normalitybreath", "shamebreath", "stunbreath", "glitter")},
    {"id": "gas_steam", "z": "back", "mutations": (
        "steamgeneration", "steamvents", "steambreath", "steamglands", "freezinggas",
        "plasmagas", "plasmageneration", "plasmaemission", "heatvent", "wizsteam")},
    # The darkness around the figure shows only while it surrounds the character: Umbrameum / Light Occlusion's
    # "shade self" puts the Darkening effect on it (user, 2026-11-19). Obfuscate, invisibility, fear aura, lich and
    # Sciophagia are not darkness and drew it on characters without Light Occlusion.
    {"id": "shadow", "z": "back", "mutations": (
        "shadowking", "darklord", "longnight", "witchinghour", "abyssal"), "effects": ("darkening",)},
    {"id": "speed", "z": "back", "mutations": (
        "heightenedspeed", "heightenedquickness", "adrenal", "rundown", "rushdown")},
    {"id": "levitate", "z": "back", "mutations": ("levitat", "gravityfield")},
    {"id": "webs", "z": "back", "mutations": ("spinneret", "spiderweb", "frostweb")},
    {"id": "tail", "z": "back", "limbs": ("#tail:1",), "mutations": ("tail",)},
    {"id": "roots", "z": "back", "limbs": ("#roots:1",), "mutations": ("fibrousroots", "roottrap")},
    {"id": "humps", "z": "back", "mutations": ("hump",)},
    {"id": "quills", "z": "back", "mutations": ("quill", "thorn", "burs", "urchin", "bonyprotrusion")},
    {"id": "legs", "z": "back", "covers": ("multipleleg",)},
    {"id": "arms2", "z": "back", "limbs": ("#arm:3",), "covers": ("multiplearm",)},
    # ---- over the body
    {"id": "arms", "z": "front", "limbs": ("#arm:1",)},
    {"id": "fin", "z": "front", "limbs": ("#fin:1",), "mutations": ("fins",)},
    {"id": "astral", "z": "front", "mutations": ("astral", "incorporeal")},
    {"id": "carapace", "z": "front", "mutations": ("carapace", "exoskeleton")},
    {"id": "scales", "z": "front", "mutations": (
        "scale", "coldblooded", "chitinousskin", "crystallin", "crystalgrow", "calcif")},
    {"id": "leaves", "z": "front", "mutations": (
        "photosynthetic", "barkflesh", "fruitingbod", "dendrovox", "xylem", "burgeoning")},
    {"id": "fur", "z": "front", "mutations": ("thickfur",)},
    {"id": "feathers", "z": "front", "mutations": ("feather",)},
    {"id": "muscle", "z": "front", "mutations": ("heightenedstrength", "doublemuscled")},
    {"id": "slime", "z": "front", "mutations": (
        "slimeglands", "soggyglands", "waterglands", "acidglands", "convalessence", "liquidfont",
        "hydropartum", "acidicblood", "gelatinous")},
    {"id": "heart", "z": "front", "mutations": ("twohearted",)},
    {"id": "antenna", "z": "front", "mutations": ("targeting", "radar", "scanner", "idspoof")},
    {"id": "apron", "z": "front", "equipped": ("apron", "vest", "robe", "tunic")},
    {"id": "brood", "z": "front", "mutations": ("broodmother", "ovipositor"), "equipped": ("broodlingsack", "broodsack")},
    # Tentacles / oral-arm tips over the brood sack (the sack rides on the back). A second
    # tentacle or pseudopod shows on plans that draw oral arms as limbs (biped).
    {"id": "tentacles", "z": "front", "limbs": ("#tentacle:1",), "mutations": ("tentacle",)},
    {"id": "tentacles2", "z": "front", "limbs": ("#tentacle:2",)},
    # The Conjoinment rope: one per Conjoinment body part (Conjoined adds one per mate), keyed on the part
    # and not the mutation, so a severed Conjoinment drops its rope until the limb regenerates.
    {"id": "conjoined", "z": "front", "limbs": ("Conjoinment:1",)},
    {"id": "conjoined2", "z": "front", "limbs": ("Conjoinment:2",)},
    {"id": "claws", "z": "front", "mutations": ("claw", "talon", "astralpaw", "elongatedpaw"), "equipped": ("claw",)},
    {"id": "hooks", "z": "front", "mutations": ("hooksforfeet", "hooves", "hoof")},
    # Clawed paws for feet (Peculiar Pedestrians' Pedestrian_Paws and the like): the
    # feet widened into paws with claw tips. Worn footwear is tinted onto this shape in
    # game, so the claws still show.
    {"id": "foot_paws", "z": "front", "mutations": ("pedestrianpaws", "pawfeet", "pawedfeet")},
    {"id": "tendril", "z": "front", "mutations": ("gelatinous", "oralarm", "pseudopod")},
    {"id": "stinger", "z": "front", "mutations": ("stinger",), "requires": "tail"},
    {"id": "head1", "z": "front", "limbs": ("#head:1",)},
    {"id": "head2", "z": "front", "limbs": ("#head:2",), "covers": ("twohead", "multiplehead", "hydrahead")},
    {"id": "head3", "z": "front", "limbs": ("#head:3",)},
    {"id": "head4", "z": "front", "limbs": ("#head:4",)},
    {"id": "albino", "z": "front", "mutations": ("albino",)},
    {"id": "albino_head", "z": "front", "mutations": ("albino",), "requires": "head1"},
    {"id": "ears", "z": "front", "mutations": ("heightenedhearing",), "requires": "head1"},
    # Horns grow on every head (Improved Mutations' Horns; Gigantism Plus Extended 1.5.0).
    # The variant picks the shape (vanilla Horns / Gigantism Plus UD_HornsPlus variants:
    # pair, Single, Spiral, Casque, Antlers); "unless" keeps the pair off for the others.
    {"id": "horns", "z": "front", "mutations": ("horns",), "unless": _HORN_NOT_PAIR, "requires": "head1"},
    {"id": "horns2", "z": "front", "mutations": ("horns",), "unless": _HORN_NOT_PAIR, "requires": "head2"},
    {"id": "horns3", "z": "front", "mutations": ("horns",), "unless": _HORN_NOT_PAIR, "requires": "head3"},
    {"id": "horns4", "z": "front", "mutations": ("horns",), "unless": _HORN_NOT_PAIR, "requires": "head4"},
    {"id": "unihorn", "z": "front", "mutations": _HORN_SINGLE, "requires": "head1"},
    {"id": "unihorn2", "z": "front", "mutations": _HORN_SINGLE, "requires": "head2"},
    {"id": "unihorn3", "z": "front", "mutations": _HORN_SINGLE, "requires": "head3"},
    {"id": "unihorn4", "z": "front", "mutations": _HORN_SINGLE, "requires": "head4"},
    {"id": "antlers", "z": "front", "mutations": _HORN_ANTLERS, "requires": "head1"},
    {"id": "antlers2", "z": "front", "mutations": _HORN_ANTLERS, "requires": "head2"},
    {"id": "antlers3", "z": "front", "mutations": _HORN_ANTLERS, "requires": "head3"},
    {"id": "antlers4", "z": "front", "mutations": _HORN_ANTLERS, "requires": "head4"},
    {"id": "casque", "z": "front", "mutations": _HORN_CASQUE, "requires": "head1"},
    {"id": "casque2", "z": "front", "mutations": _HORN_CASQUE, "requires": "head2"},
    {"id": "casque3", "z": "front", "mutations": _HORN_CASQUE, "requires": "head3"},
    {"id": "casque4", "z": "front", "mutations": _HORN_CASQUE, "requires": "head4"},
    {"id": "beak", "z": "front", "mutations": ("beak",), "requires": "head1"},
    {"id": "gills", "z": "front", "mutations": ("gills", "amphibious"), "requires": "head1"},
    {"id": "fangs", "z": "front", "mutations": (
        "fang", "maw", "jaw", "carnivorous", "vampir", "bite", "muzzle", "leadsnout"), "requires": "head1"},
    {"id": "tongue", "z": "front", "mutations": ("tongue",), "requires": "head1"},
    {"id": "glow_eyes", "z": "front", "mutations": (
        "darkvision", "nightvision", "umbraleyes", "umbralsight", "uvvision", "gaze", "glareburst",
        "irisdual", "dwellerssight"), "requires": "head1"},
    {"id": "third_eye", "z": "front", "mutations": (
        "thirdeye", "clairvoyance", "precognition", "prescience", "haruspicy", "evileye", "witness",
        "psychometry", "sensepsychic"), "requires": "head1"},
    {"id": "spectacles", "z": "front", "mutations": ("myopia",), "equipped": ("spectacle", "glasses", "goggles"), "requires": "head1"},
    {"id": "blink", "z": "front", "mutations": ("blinkingtic",), "requires": "head1"},
    {"id": "breath", "z": "front", "mutations": (
        "breath", "breather", "liquidspitter", "spitsulfur", "urchinbelch"), "requires": "head1"},
    {"id": "halo", "z": "front", "mutations": (
        "halo", "seraph", "paladin", "dawnknight", "martyr", "fontofmercy", "smite", "paradise"), "requires": "head1"},
    {"id": "psi", "z": "front", "mutations": (
        "esper", "telepathy", "massmind", "presence", "focuspsi", "ascension", "domination", "beguiling",
        "egoprojection", "willforce", "sunder", "mentalconduit"), "requires": "head1"},
    # ---- auras on top of everything
    {"id": "flames", "z": "front", "mutations": (
        "flamingray", "firebreath", "pyrokinesis", "kindle", "ignite", "combustion", "thermokinesis",
        "flamingsword", "phoenix", "choirofembers", "feyfire", "hellmouth", "lastember", "firstcandle")},
    {"id": "frost", "z": "front", "mutations": ("freez", "cryo", "icebreath", "frost", "heatabsorption")},
    {"id": "sparks", "z": "front", "mutations": (
        "electricalgeneration", "electromagnetic", "magneticpulse", "psychiclightning", "capacitors",
        "dynakine", "jacobsladder")},
    {"id": "light", "z": "front", "mutations": (
        "lightmanipulation", "glimmer", "aurora", "lantern", "morningbell", "chromatophore", "fallingstar")},
    {"id": "regen", "z": "front", "mutations": ("regenerat", "autorepair", "vitaintuita")},
    {"id": "orbit", "z": "front", "mutations": (
        "telekine", "psychokinesis", "animateweapon", "orbitingblades", "psychicblades", "barrage", "fingerguns")},
    {"id": "force", "z": "front", "mutations": (
        "forcebubble", "forcewall", "forceaegis", "forcearmor", "repellingforce", "stunningforce", "shieldwall")},
    {"id": "vortex", "z": "front", "mutations": (
        "vortex", "spacetime", "timedilation", "fugue", "teleport", "wefttear", "leyshift", "quantumjitter")},
    {"id": "phase", "z": "fade", "mutations": ("incorporeal",), "effects": ("phased",), "fade": 210},
]

# Layers drawn by _draw_mutation_layer (the others live in _kitty_roles itself).
_MUTATION_LAYER_IDS = frozenset((
    "gas_toxic", "gas_mind", "gas_steam", "breath", "sparks", "flames", "frost", "leaves", "slime", "webs",
    "ears", "glow_eyes", "third_eye", "fangs", "tongue", "gills", "scales", "muscle", "humps", "speed",
    "hooks", "heart", "regen", "psi", "halo", "force", "shadow", "light", "orbit", "levitate", "feathers",
    "albino", "albino_head", "antenna",
))

# Arendeth_CYFTiles 1.4.0 keeps the shown layers of a plan in a mask of 64-bit words
# (the tile path joins them with '-'); earlier versions read only the first 64.
MAX_LAYERS_PER_PLAN = 256

# Extra legs: more than the plan already shows (limb class #leg).
_LEG_LIMBS = {
    "biped": ("#leg:3",),
    "quadruped": ("#leg:5",),
    "chair": ("#leg:5",),
    "table": ("#leg:5",),
}
_DEFAULT_LEG_LIMBS = ("#leg:1",)

# Game palette -> Bright Qud palette (BrightQud.cs Recolor.Bright / art/src/colors.py).
BRIGHT_QUD_PALETTE = [
    ("a64a2e", "c8503a"), ("d74200", "f05a28"), ("f15f22", "ff7030"), ("e99f10", "ffb020"),
    ("98875f", "b08a5a"), ("cfc041", "ffd23a"), ("009403", "3fae3a"), ("00c420", "6fe04a"),
    ("0048bd", "2a62d6"), ("0096ff", "3fb4ff"), ("40a4b9", "4fc8d8"), ("77bfcf", "8fe4f0"),
    ("b154cf", "c04ad8"), ("da5bd6", "ff7ae8"), ("0f3b3a", "1a4a48"), ("155352", "2e6a68"),
    ("b1c9c3", "d0dcd8"), ("ffffff", "f8f8f0"),
]


def _hex_rgb(h: str) -> Tuple[int, int, int]:
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


_BRIGHT_PAIRS = [(_hex_rgb(a), _hex_rgb(b)) for a, b in BRIGHT_QUD_PALETTE]


def brighten_image(img: Image.Image) -> Image.Image:
    """Swap game-palette colours for Bright Qud's (same ±3 tolerance as Bright Qud).

    Bright Qud keeps another mod's truecolor pixels as they are and only adds its
    outline and shadow, so a fighter meant to sit in a Bright Qud world is baked in
    its palette up front.
    """
    out = img.convert("RGBA").copy()
    px = out.load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            for src, dst in _BRIGHT_PAIRS:
                if abs(r - src[0]) <= 3 and abs(g - src[1]) <= 3 and abs(b - src[2]) <= 3:
                    px[x, y] = (*dst, a)
                    break
    return out


def _shift(rgb: Tuple[int, int, int], k: float) -> Tuple[int, int, int]:
    """k < 0 darkens toward black, k > 0 lightens toward white."""
    if k < 0:
        return tuple(int(c * (1 + k)) for c in rgb)  # type: ignore[return-value]
    return tuple(min(255, int(c + (255 - c) * k)) for c in rgb)  # type: ignore[return-value]


def _plan_palette(
    fighter: Dict[str, Any],
    flags: Dict[str, bool],
    palette: Optional[Dict[str, Tuple[int, int, int]]],
) -> Dict[str, Tuple[int, int, int]]:
    pal = dict(_FELINE_RGB)
    # "ownColors": keep the fighter's foreground/detail for the body even when the
    # feline/slime look would recolour it (layered fighters show slime as a layer).
    own = bool(fighter.get("ownColors"))
    if flags.get("feline") and not own:
        if flags.get("slime"):
            pal.update(
                {
                    "body": (0x2E, 0xA8, 0x4A), "stripe": (0x1A, 0x5C, 0x32),
                    "belly": (0x8F, 0xE0, 0x9A), "ear": (0x2E, 0xA8, 0x4A),
                    "muzzle": (0xB8, 0xF0, 0xC0), "paw": (0x8F, 0xE0, 0x9A),
                    "vortex": (0xDA, 0x5B, 0xD6),
                }
            )
    else:
        fg_c, det_c = suggest_colors(fighter)
        fg = PALETTE_RGB.get(fg_c, (64, 164, 185))
        det = PALETTE_RGB.get(det_c, (177, 201, 195))
        pal.update({"body": fg, "ear": fg, "stripe": _shift(fg, -0.45),
                    "belly": det, "muzzle": det, "paw": det})
    if palette:
        pal.update(palette)
    if not palette or "fur" not in palette:
        pal["fur"] = _shift(pal["body"], 0.35)
    if not palette or "scale" not in palette:
        pal["scale"] = _shift(pal["body"], -0.35)
        pal["scale_hi"] = _shift(pal["body"], 0.3)
    if not palette or "muscle" not in palette:
        pal["muscle"] = _shift(pal["body"], 0.18)
    return pal


def _render_plan_layer(
    fighter: Dict[str, Any],
    flags: Dict[str, bool],
    frame: int,
    total: int,
    layer: str,
    plan: str,
    color_mode: str,
    pal: Dict[str, Tuple[int, int, int]],
) -> Image.Image:
    roles = _kitty_roles(fighter, flags, frame, total, layer, plan)
    if color_mode == "classic":
        small = Image.new("L", (16, 24), 0)
        px = small.load()
        for (x, y), role in roles.items():
            px[x, y] = _FELINE_LUMA.get(role, 72)
        return mask_to_classic(small)
    img = Image.new("RGBA", (16, 24), (0, 0, 0, 0))
    px = img.load()
    for (x, y), role in roles.items():
        px[x, y] = (*(pal.get(role) or pal["body"]), _ROLE_ALPHA.get(role, 255))
    return img


# ---------------------------------------------------------------- layer templates
#
# CYFTemplates/ (next to this script) holds editable art for every body plan and
# layer: <style>/<plan>.png, one folder per head style (HEAD_STYLES). Each sheet has
# the same rows as a fighter's layer sheet would (row 0 the body, then one row per
# entry of _LAYER_DEFS except fade layers, see templates.json "rows"), 8 frame
# columns of 16x24. Pixels are painted in key colours, one per role
# (templates.json "roles", legend.png): a baked fighter maps every key colour to
# its own palette colour for that role and keeps the pixel's alpha; any other
# colour is used as it is. Untouched templates bake exactly like the built-in
# drawing; paint over a cell (or a row the built-in drawing leaves empty) and
# every fighter baked afterwards uses it.
#
# content_map.json (cyf_scan_content.py) assigns every anatomy found in vanilla
# and the enabled mods to a plan; the layer manifest lists them per plan.

TEMPLATE_DIR = Path(__file__).resolve().parent / "CYFTemplates"
TEMPLATE_FRAMES = 8
TEMPLATE_STYLES = HEAD_STYLES


def _template_rows() -> List[str]:
    return ["base"] + [d["id"] for d in _LAYER_DEFS if d["z"] != "fade"]


def _template_roles() -> List[str]:
    return sorted(set(_FELINE_LUMA) | set(_FELINE_RGB))


def _template_keys(roles: Sequence[str]) -> Dict[str, Tuple[int, int, int]]:
    """One distinct, saturated key colour per role (golden-angle hues, two values)."""
    import colorsys

    keys: Dict[str, Tuple[int, int, int]] = {}
    used = set()
    for i, role in enumerate(roles):
        k = 0
        while True:
            h = ((i + k * 7) * 0.618033988749895) % 1.0
            v = 0.95 if (i + k) % 2 == 0 else 0.62
            s = 0.85 if (i // 2 + k) % 2 == 0 else 0.55
            rgb = tuple(int(round(c * 255)) for c in colorsys.hsv_to_rgb(h, s, v))
            if rgb not in used:
                break
            k += 1
        used.add(rgb)
        keys[role] = rgb  # type: ignore[assignment]
    return keys


def write_templates(out: Path = TEMPLATE_DIR, *, force: bool = False) -> Dict[str, Any]:
    """Write the template pack from the built-in drawing; existing sheets are kept unless force."""
    out = Path(out)
    roles = _template_roles()
    keys = _template_keys(roles)
    rows = _template_rows()
    written, kept = [], []
    for style in TEMPLATE_STYLES:
        flags = {"feline": style == "cat", "head_style": style}
        fighter = {"name": "template"}
        (out / style).mkdir(parents=True, exist_ok=True)
        for plan in ALL_PLANS:
            path = out / style / f"{plan}.png"
            if path.exists() and not force:
                kept.append(str(path))
                continue
            sheet = Image.new("RGBA", (16 * TEMPLATE_FRAMES, 24 * len(rows)), (0, 0, 0, 0))
            px = sheet.load()
            for r, lid in enumerate(rows):
                for fr in range(TEMPLATE_FRAMES):
                    for (x, y), role in _kitty_roles(fighter, flags, fr, TEMPLATE_FRAMES, lid, plan).items():
                        px[fr * 16 + x, r * 24 + y] = (*keys[role], _ROLE_ALPHA.get(role, 255))
            sheet.save(path, "PNG")
            written.append(str(path))
    info_path = out / "templates.json"
    old_keys: Dict[str, Any] = {}
    if info_path.exists() and not force:
        try:
            old_keys = json.loads(info_path.read_text(encoding="utf-8")).get("roles") or {}
        except ValueError:
            old_keys = {}
    # Keep the key colours sheets on disk were painted with; new roles get new keys.
    merged = {r: list(old_keys.get(r) or keys[r]) for r in roles}
    taken = {tuple(v) for r, v in merged.items() if r in old_keys}
    for r in roles:
        if r not in old_keys and tuple(merged[r]) in taken:
            raise ValueError(f"key colour for new role {r} clashes; rewrite the pack with force")
    info = {
        "note": "Key colours (roles) of CYFTemplates/<style>/<plan>.png. Paint with these colours; "
                "a bake maps each to the fighter's colour for that role and keeps the alpha. "
                "Other colours are used as they are.",
        "tileSize": [16, 24],
        "frames": TEMPLATE_FRAMES,
        "styles": list(TEMPLATE_STYLES),
        "plans": list(ALL_PLANS),
        "rows": rows,
        "roles": merged,
        "alpha": dict(_ROLE_ALPHA),
    }
    info_path.write_text(json.dumps(info, indent=1), encoding="utf-8")
    _template_previews(out, info)
    return {"written": written, "kept": kept, "info": str(info_path)}


def _template_previews(out: Path, info: Dict[str, Any], scale: int = 4) -> None:
    """legend.png (role key colours) and preview/<style>_<plan>.png (labelled, game colours)."""
    from PIL import ImageDraw

    roles = info["roles"]
    pal = dict(_FELINE_RGB)
    key_to_role = {tuple(v): r for r, v in roles.items()}
    names = sorted(roles)
    cols = 3
    lh = 18
    leg = Image.new("RGBA", (cols * 190, ((len(names) + cols - 1) // cols) * lh + 8), (24, 28, 36, 255))
    d = ImageDraw.Draw(leg)
    for i, r in enumerate(names):
        x, y = (i % cols) * 190 + 6, (i // cols) * lh + 4
        d.rectangle((x, y, x + 14, y + 14), fill=tuple(roles[r]) + (255,))
        d.text((x + 20, y + 2), f"{r}  #{''.join(f'{c:02x}' for c in roles[r])}", fill=(230, 230, 230, 255))
    leg.save(out / "legend.png", "PNG")

    (out / "preview").mkdir(exist_ok=True)
    rows = info["rows"]
    label_w = 90
    for style in info["styles"]:
        for plan in info["plans"]:
            path = out / style / f"{plan}.png"
            if not path.exists():
                continue
            sheet = Image.open(path).convert("RGBA")
            spx = sheet.load()
            img = Image.new("RGBA", (label_w + 16 * TEMPLATE_FRAMES * scale + TEMPLATE_FRAMES * 2,
                                     len(rows) * (24 * scale + 2)), (24, 28, 36, 255))
            d = ImageDraw.Draw(img)
            for r, lid in enumerate(rows):
                y0 = r * (24 * scale + 2)
                d.text((4, y0 + 4), lid, fill=(230, 230, 230, 255))
                for fr in range(TEMPLATE_FRAMES):
                    cell = Image.new("RGBA", (16, 24), (0, 0, 0, 0))
                    cpx = cell.load()
                    for y in range(24):
                        for x in range(16):
                            if r > 0:
                                # Faint body underneath, to show where the layer sits.
                                b = spx[fr * 16 + x, y]
                                if b[3]:
                                    cpx[x, y] = (90, 96, 110, 90)
                            c = spx[fr * 16 + x, r * 24 + y]
                            if c[3] == 0:
                                continue
                            role = key_to_role.get(c[:3])
                            cpx[x, y] = (*(pal.get(role) or c[:3]), c[3]) if role else c
                    img.alpha_composite(cell.resize((16 * scale, 24 * scale), Image.Resampling.NEAREST),
                                        (label_w + fr * (16 * scale + 2), y0))
            img.save(out / "preview" / f"{style}_{plan}.png", "PNG")


class LayerTemplates:
    """Template sheets of one head style, read for a bake."""

    def __init__(self, root: Path, style: str) -> None:
        self.root = Path(root)
        info = json.loads((self.root / "templates.json").read_text(encoding="utf-8"))
        self.rows = {lid: i for i, lid in enumerate(info["rows"])}
        self.frames = int(info.get("frames", TEMPLATE_FRAMES))
        self.key_to_role = {tuple(v): r for r, v in (info.get("roles") or {}).items()}
        self.style = style if (self.root / style).is_dir() else (
            "plain" if (self.root / "plain").is_dir() else TEMPLATE_STYLES[0])
        self._sheets: Dict[str, Optional[Image.Image]] = {}

    @staticmethod
    def available(root: Optional[Path]) -> bool:
        return bool(root) and (Path(root) / "templates.json").is_file()

    def _sheet(self, plan: str) -> Optional[Image.Image]:
        if plan not in self._sheets:
            path = self.root / self.style / f"{plan}.png"
            self._sheets[plan] = Image.open(path).convert("RGBA") if path.is_file() else None
        return self._sheets[plan]

    def cell(self, plan: str, layer: str, frame: int) -> Optional[Image.Image]:
        sheet = self._sheet(plan)
        row = self.rows.get(layer)
        if sheet is None or row is None or (row + 1) * 24 > sheet.height:
            return None
        col = frame % self.frames
        if (col + 1) * 16 > sheet.width:
            col = 0
        return sheet.crop((col * 16, row * 24, col * 16 + 16, row * 24 + 24))

    def render(self, plan: str, layer: str, frame: int, color_mode: str,
               pal: Dict[str, Tuple[int, int, int]]) -> Optional[Image.Image]:
        """The cell in the fighter's colours, or None when the pack has no such cell."""
        cell = self.cell(plan, layer, frame)
        if cell is None:
            return None
        cpx = cell.load()
        if color_mode == "classic":
            small = Image.new("L", (16, 24), 0)
            spx = small.load()
            for y in range(24):
                for x in range(16):
                    c = cpx[x, y]
                    if c[3] == 0:
                        continue
                    role = self.key_to_role.get(c[:3])
                    spx[x, y] = _FELINE_LUMA.get(role, 72) if role else max(1, int(
                        0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]))
            return mask_to_classic(small)
        img = Image.new("RGBA", (16, 24), (0, 0, 0, 0))
        px = img.load()
        for y in range(24):
            for x in range(16):
                c = cpx[x, y]
                if c[3] == 0:
                    continue
                role = self.key_to_role.get(c[:3])
                px[x, y] = (*(pal.get(role) or pal["body"]), c[3]) if role else c
        return img


def plan_anatomies(plan: str, content_map: Optional[Path] = None) -> List[str]:
    """Anatomies drawn with a plan: vanilla's, plus every scanned one the content map assigns to it."""
    path = Path(content_map) if content_map else TEMPLATE_DIR / "content_map.json"
    names = list(PLAN_ANATOMIES.get(plan, ()))
    if not path.is_file():
        return names
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return names
    mapped = doc.get("anatomyPlans") or {}
    names = [n for n in names if (mapped.get(n) or {}).get("plan", plan) == plan]
    for n, a in mapped.items():
        if a.get("plan") == plan and n not in names:
            names.append(n)
    return names


def generate_layer_set(
    fighter: Dict[str, Any],
    out_dir: Path,
    name: str,
    width: int,
    height: int,
    color_mode: str,
    frames: int,
    palette: Optional[Dict[str, Tuple[int, int, int]]] = None,
    bright: bool = False,
    plans: Sequence[str] = ALL_PLANS,
    templates: Optional[Path] = None,
) -> Dict[str, Any]:
    """Write Textures/Layers/<name>/<plan>.png sheets into out_dir; return the layer manifest.

    Cells come from the template pack (templates, see CYFTemplates) when one is
    given, else from the built-in drawing; sizes above 16×24 are
    nearest-neighbour scaled.
    """
    flags = _feature_flags(fighter)
    style = head_style(fighter, flags)
    flags["head_style"] = style
    n = max(1, int(frames))
    pal = _plan_palette(fighter, flags, palette)
    tpl_pack = LayerTemplates(Path(templates), style) if LayerTemplates.available(templates) else None
    sheet_dir = Path(out_dir) / "Textures" / "Layers" / name
    sheet_dir.mkdir(parents=True, exist_ok=True)
    sx, sy = width / 16.0, height / 24.0

    def render(lid: str, plan: str, fr: int) -> Image.Image:
        img = tpl_pack.render(plan, lid, fr, color_mode, pal) if tpl_pack else None
        if img is None:
            img = _render_plan_layer(fighter, flags, fr, n, lid, plan, color_mode, pal)
        if bright and color_mode == "truecolor":
            img = brighten_image(img)
        return _scale_tile(img, width, height)

    plan_entries: List[Dict[str, Any]] = []
    for plan in plans:
        rows: List[List[Image.Image]] = []
        base = [render("base", plan, i) for i in range(n)]
        rows.append(base if not _same_frames(base) else base[:1])
        layers: List[Dict[str, Any]] = []
        for d in _LAYER_DEFS:
            lid = d["id"]
            limbs = d.get("limbs")
            if lid == "legs":
                limbs = _LEG_LIMBS.get(plan, _DEFAULT_LEG_LIMBS)
            entry: Dict[str, Any] = {
                "id": lid,
                "z": d["z"],
                "mutations": list(d.get("mutations", ())),
                "equipped": list(d.get("equipped", ())),
                "effects": list(d.get("effects", ())),
                "limbs": list(limbs or ()),
                "minLevel": int(d.get("minLevel", 0)),
                "requires": d.get("requires"),
                "covers": list(d.get("covers", ())),
                "unless": list(d.get("unless", ())),
            }
            if d["z"] == "fade":
                entry["fade"] = int(d.get("fade", 0))
                layers.append(entry)
                continue
            imgs = [render(lid, plan, i) for i in range(n)]
            if all(_is_empty(im) for im in imgs):
                continue
            entry["row"] = len(rows)
            entry["frames"] = 1 if _same_frames(imgs) else n
            rows.append(imgs[: entry["frames"]])
            layers.append(entry)
        if len(layers) > MAX_LAYERS_PER_PLAN:
            raise ValueError(f"plan {plan}: {len(layers)} layers; Arendeth_CYFTiles reads at most "
                             f"{MAX_LAYERS_PER_PLAN} per plan (merge some in _LAYER_DEFS)")
        sheet = Image.new("RGBA", (width * n, height * len(rows)), (0, 0, 0, 0))
        for r, imgs in enumerate(rows):
            for c, im in enumerate(imgs):
                sheet.alpha_composite(im, (c * width, r * height))
        path = sheet_dir / f"{plan}.png"
        sheet.save(path, "PNG")
        plan_entries.append(
            {
                "id": plan,
                "sheet": f"Layers/{name}/{plan}.png",
                "anatomies": plan_anatomies(plan),
                "base": {"row": 0, "frames": len(rows[0])},
                "grips": [list(g) for g in _PLAN_TEMPLATES.get(plan, {}).get("grips", ())],
                "layers": layers,
            }
        )
    _log(f"  [layers] {len(plan_entries)} body plans, {len(_LAYER_DEFS)} layer kinds"
         f"{' from templates ' + str(tpl_pack.root / tpl_pack.style) if tpl_pack else ''} -> {sheet_dir}")
    return {
        "headStyle": style,
        "templates": str(tpl_pack.root / tpl_pack.style) if tpl_pack else None,
        "palette": "brightqud" if bright and color_mode == "truecolor" else "game",
        "brightQudFallback": True,
        # Layers this fighter never shows, whatever matches (fighter json "hideLayers").
        "hideLayers": [str(x) for x in (fighter.get("hideLayers") or []) if str(x).strip()],
        # Layers kept off the map tile only; the layered portrait still follows them
        # (fighter json "tileHideLayers").
        "tileHideLayers": [str(x) for x in (fighter.get("tileHideLayers") or []) if str(x).strip()],
        "tileSize": [width, height],
        "frameCount": n,
        "plans": plan_entries,
    }


def _is_empty(img: Image.Image) -> bool:
    return img.convert("RGBA").getbbox() is None


def _same_frames(imgs: Sequence[Image.Image]) -> bool:
    first = imgs[0].tobytes()
    return all(im.tobytes() == first for im in imgs[1:])


def layer_preview(out_dir: Path, layer_set: Dict[str, Any], out_path: Path, scale: int = 5) -> Path:
    """Sheet: one column per body plan; top = base only, bottom = every layer on."""
    w, h = layer_set["tileSize"]
    cols = []
    for plan in layer_set["plans"]:
        sheet = Image.open(Path(out_dir) / "Textures" / plan["sheet"]).convert("RGBA")

        def cell(row: int) -> Image.Image:
            return sheet.crop((0, row * h, w, row * h + h))

        base = cell(0)
        full = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        drawn = [l for l in plan["layers"] if "row" in l and l["id"] not in ("arms2", "head4")]
        for l in drawn:
            if l["z"] == "back":
                full.alpha_composite(cell(l["row"]))
        full.alpha_composite(base)
        for l in drawn:
            if l["z"] == "front":
                full.alpha_composite(cell(l["row"]))
        # Plain body + its natural parts (head, arms, tail), as most creatures look.
        natural = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        for l in plan["layers"]:
            if "row" in l and l["id"] in ("tail", "roots") and l["z"] == "back":
                natural.alpha_composite(cell(l["row"]))
        natural.alpha_composite(base)
        for l in plan["layers"]:
            if "row" in l and l["id"] in ("head1", "arms"):
                natural.alpha_composite(cell(l["row"]))
        cols.append((base, natural, full))
    pad = 2
    out = Image.new("RGBA", ((w + pad) * len(cols) * scale, (h + pad) * 3 * scale), (24, 28, 36, 255))
    for i, trio in enumerate(cols):
        for j, im in enumerate(trio):
            out.alpha_composite(im.resize((w * scale, h * scale), Image.Resampling.NEAREST),
                                (i * (w + pad) * scale, j * (h + pad) * scale))
    out.save(out_path, "PNG")
    return out_path


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
    layered: bool = False,
    bright_palette: bool = False,
    layer_templates: Optional[Path] = None,
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
    # Classic mode is procedural-by-design (use_sd defaults off). If the caller explicitly asked
    # for SD (use_sd=True) and it produced nothing, do NOT silently stamp a silhouette.
    if not sources and color_mode == "classic" and not use_sd:
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
        layer_pal: Optional[Dict[str, Tuple[int, int, int]]] = None

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
        layer_pal = _palette_from_detail(identity)
        if gear_im is not None:
            layer_pal.update(_palette_from_gear(gear_im))
        layer_pal.update(extra_pal)

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

    if bright_palette and color_mode == "truecolor":
        game_bake = bake

        def bake(frame_i: int, total: int) -> Image.Image:
            return brighten_image(game_bake(frame_i, total))

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

    layer_set: Optional[Dict[str, Any]] = None
    layer_preview_path: Optional[Path] = None
    if layered:
        layer_set = generate_layer_set(
            fighter,
            out_dir,
            name,
            width,
            height,
            color_mode,
            max(2, int(frames)) if animated else 1,
            palette=layer_pal if color_mode == "truecolor" else None,
            bright=bright_palette,
            templates=layer_templates,
        )
        try:
            layer_preview_path = layer_preview(out_dir, layer_set, out_dir / f"{name}_layers_preview.png")
        except Exception as e:
            _log(f"  [layers] preview skipped: {e}")

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
        "brightPalette": bool(bright_palette and color_mode == "truecolor"),
        "layerSet": layer_set,
        "layerPreview": str(layer_preview_path) if layer_preview_path else None,
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
            "--layered also writes Textures/Layers/<id>/<plan>.png, one sprite sheet per body plan (creatures, plants, animated furniture/doors/walls): row 0 the plan's body, then a row per layer. Arendeth_CYFTiles picks the plan from the player's anatomy and limbs and stacks the layers that match their limbs (heads, arms, legs, tail, fins, tentacles, roots), mutations, worn items and effects.",
            "--bright-palette swaps game colours for Bright Qud's; Bright Qud keeps truecolor tiles and adds its outline and shadow.",
        ],
    }
    man_path = out_dir / f"{name}.tile.json"
    man_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["manifestPath"] = str(man_path)
    return manifest


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Generate CoQ player tiles from detailed art (not silhouettes)")
    p.add_argument("fighter_json", nargs="?", type=Path, default=None)
    p.add_argument("-o", "--out", type=Path, default=None)
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
    p.add_argument("--layered", action="store_true",
                   help="Also write per-body-plan layer sheets; the game builds the body from the player's anatomy, limbs and mutations")
    p.add_argument("--head-style", choices=("auto",) + HEAD_STYLES, default="auto",
                   help="Head drawn on --layered sheets (auto: the fighter's headStyle field, cat for "
                        "feline fighters, else picked from its name, genotype, mutations and description)")
    p.add_argument("--templates", type=Path, default=None,
                   help=f"Layer template pack for --layered (default {TEMPLATE_DIR} when it exists)")
    p.add_argument("--no-templates", action="store_true",
                   help="--layered: draw every layer with the built-in drawing, ignoring templates")
    p.add_argument("--write-templates", action="store_true",
                   help="Write the layer template pack (--templates or the default folder) and exit; "
                        "sheets already there are kept unless --force-templates")
    p.add_argument("--force-templates", action="store_true",
                   help="With --write-templates: overwrite existing (possibly edited) template sheets")
    p.add_argument("--bright-palette", action="store_true",
                   help="Truecolor only: bake in Bright Qud's palette so the fighter matches a Bright Qud world")
    p.add_argument("--allow-silhouette", action="store_true",
                   help="Permit the old 2-color stamp if no detailed source exists")
    args = p.parse_args(argv)
    if args.write_templates:
        print(json.dumps(write_templates(args.templates or TEMPLATE_DIR, force=args.force_templates), indent=2))
        return 0
    if args.out is None:
        p.error("-o/--out is required")
    if args.list_overlays:
        print(json.dumps(list_overlay_catalog(args.out), indent=2))
        return 0
    if not args.fighter_json:
        raise SystemExit("fighter_json is required unless --list-overlays")

    fighter = json.loads(Path(args.fighter_json).read_text(encoding="utf-8"))
    if args.head_style != "auto":
        fighter["headStyle"] = args.head_style
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
        layered=args.layered,
        bright_palette=args.bright_palette,
        layer_templates=None if args.no_templates else (args.templates or (
            TEMPLATE_DIR if LayerTemplates.available(TEMPLATE_DIR) else None)),
    )
    print(json.dumps(man, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
