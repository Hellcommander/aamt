#!/usr/bin/env python3
"""
Per-mod Soulash 2 branding asset generator (icon S.png + thumbnail2.png).

Asset-size policy:
  - S.png (32×32 mod icon): ALWAYS procedural PIL (+ optional Ollama design spec).
  - thumbnail2.png (800×600 workshop banner): SD when --use-sd; sizes from
    ``s2_icon_pipeline.planned_sd_settings`` (same floor/contain path as
    SkillCreator generate-icons), then downscale. Procedural fallback on failure.

Supports themed palettes/prompts via --theme or auto-detection from --mod-path.

Themes: hemohydraulic, hydromancy, reactive_crafting

Pipeline:
  Icons: Ollama spec (optional) → procedural render → mechanical/vision QA
  Thumbnails: optional SD draft (1024×768) → downscale → QA → procedural fallback
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
import random
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

_shared = _here.parent / "Shared"
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from hydromancy_quality import (  # noqa: E402
    HYDROMANCY_PALETTE,
    finalize_icon,
    finalize_icon_from_sd,
    finalize_thumbnail_from_sd,
    parse_ollama_json,
    score_palette_match,
    validate_mod_icon,
    validate_thumbnail,
)
from s2_icon_pipeline import NEGATIVE, planned_sd_settings, sd_session  # noqa: E402

try:
    from sd_http_client import detect_server, generate_image  # noqa: E402
    SD_AVAILABLE = True
except Exception:
    SD_AVAILABLE = False

try:
    from ollama_integration import call_ollama, test_ollama_connection  # noqa: E402
    OLLAMA_AVAILABLE = True
except Exception:
    OLLAMA_AVAILABLE = False

DRAFT_ICON_NAME = "icon_design_draft.png"
DRAFT_THUMB_NAME = "thumbnail_design_draft.png"
SD_TIMEOUT_SEC = 14400.0  # 4h — ToS + CPU offload can exceed 1h per 1024x768@24
SD_LOCK_PATH = Path(os.environ.get("TEMP", ".")) / "soulash_sd_branding.lock"
SD_LOCK_STALE_SEC = 7200.0

SD_NEGATIVE_PROMPT = NEGATIVE + (
    ", low quality, pixelated, distorted, deformed, bad anatomy, "
    "oversaturated, muddy colors, unreadable, duplicate, cropped"
)

# Overnight-quality SD settings (RTX 2080 Ti + CPU offload; slow but high fidelity)
# Primary sizes come from s2_icon_pipeline.planned_sd_settings (same as generate-icons).
SD_ICON_FALLBACK = {"width": 512, "height": 512, "steps": 16, "guidance_scale": 7.0, "seed": 42}
SD_THUMB_FALLBACK = {"width": 640, "height": 512, "steps": 16, "guidance_scale": 7.0, "seed": 43}
SD_ICON_OOM = {"width": 512, "height": 512, "steps": 12, "guidance_scale": 7.0, "seed": 42}
SD_THUMB_OOM = {"width": 640, "height": 480, "steps": 12, "guidance_scale": 7.0, "seed": 43}

HEMOHYDRAULIC_PALETTE = ["#0a0408", "#1a0812", "#4a0a1a", "#8b1538", "#c41e3a", "#e85d6f", "#f0a0a8"]
REACTIVE_PALETTE = ["#120d0a", "#2c2015", "#5a3d22", "#a06a2c", "#e0b25e", "#f5e6c8"]

MOD_PATH_THEME = {
    "arendeth_hemohydraulic_magic": "hemohydraulic",
    "arendeth_water_magic": "hydromancy",
    "arendeth_reactive_crafting": "reactive_crafting",
}


@dataclass
class BrandingTheme:
    name: str
    display_name: str
    subtitle: str
    palette: List[str]
    sd_icon_prompt: str
    sd_thumb_prompt: str
    vision_rubric: str
    ollama_system: str
    ollama_prompt_hint: str
    sd_negative_extra: str = ""


THEMES: Dict[str, BrandingTheme] = {
    "hemohydraulic": BrandingTheme(
        name="hemohydraulic",
        display_name="HEMOHYDRAULICS",
        subtitle="Internal Pressure · Rupture · True Damage",
        palette=HEMOHYDRAULIC_PALETTE,
        sd_icon_prompt=(
            "Soulash 2 game mod icon, dark fantasy pixel RPG icon, biomechanical anatomical heart "
            "with glowing crimson arterial veins under extreme internal hydraulic pressure, dark "
            "venous purple background, rupture shockwave rings, visceral hemohydraulic magic, "
            "internal organ pressure sorcery NOT water NOT flask, centered composition, high "
            "contrast, hand-painted style, square concept art"
        ),
        sd_thumb_prompt=(
            "Soulash 2 mod workshop thumbnail, hemohydraulic magic school banner, internal body "
            "pressure rupture dark fantasy, crimson arterial veins bursting under magical hydraulic "
            "force inside a humanoid silhouette, dark venous purple biomechanical horror, "
            "dramatic implosion shockwaves and hemorrhage, cinematic 4:3 composition, empty title "
            "area at top, no text, concept art"
        ),
        vision_rubric=(
            "hemohydraulic internal pressure magic (crimson arteries, venous purple, rupture, "
            "NOT water jets, NOT teal hydromancy)"
        ),
        ollama_system=(
            "You are a senior art director for Soulash 2. Design hemohydraulic magic palettes: "
            "deep crimson arterial red, dark venous purple, high-pressure highlights. "
            "Internal rupture, NOT external water. Return ONLY valid JSON."
        ),
        ollama_prompt_hint="hemohydraulic internal pressure rupture magic",
        sd_negative_extra="water droplet, teal, cyan, ocean, flask, potion bottle, blue water",
    ),
    "hydromancy": BrandingTheme(
        name="hydromancy",
        display_name="HYDROMANCY",
        subtitle="Pressurized Water · Cut · Crush",
        palette=HYDROMANCY_PALETTE,
        sd_icon_prompt=(
            "Soulash 2 game mod icon, dark fantasy pixel RPG icon, razor-sharp high-pressure "
            "water jet cutting blade, pressurized hydraulic water stream slicing through air, "
            "deep teal cyan palette, external hydromancy force NOT blood NOT veins, concentric "
            "pressure ripples, centered composition, high contrast, hand-painted style, square "
            "concept art"
        ),
        sd_thumb_prompt=(
            "Soulash 2 mod workshop thumbnail, hydromancy water magic banner, devastating "
            "pressurized water cutting jets and crushing hydraulic waves, deep teal cyan palette, "
            "external water force slicing stone, cinematic 4:3 composition, empty title area at "
            "top, no text, concept art"
        ),
        vision_rubric="hydromancy pressurized water cutting magic (teal/cyan, jets, NOT blood)",
        ollama_system=(
            "You are a senior art director for Soulash 2. Design hydromancy palettes: deep teal, "
            "cyan highlights, hydraulic pressure water jets. Return ONLY valid JSON."
        ),
        ollama_prompt_hint="hydromancy pressurized water cutting magic",
        sd_negative_extra="blood, crimson, veins, heart, organs, gore, red arteries",
    ),
    "reactive_crafting": BrandingTheme(
        name="reactive_crafting",
        display_name="REACTIVE CRAFTING",
        subtitle="Terrain-altering throwables",
        palette=REACTIVE_PALETTE,
        sd_icon_prompt=(
            "Soulash 2 game mod icon, corked alchemical flask with amber liquid, four elemental "
            "terrain splashes in corners (mud brown, ember orange, snow pale blue, sand gold), "
            "dark fantasy pixel RPG icon, centered composition, high contrast, hand-painted style, "
            "square concept art"
        ),
        sd_thumb_prompt=(
            "Soulash 2 mod workshop thumbnail, reactive crafting mod banner, thrown flask bursting "
            "into four terrain quadrants (mud, ember, snow, sand), earthy warm palette, legible "
            "title area at top, dark fantasy game workshop thumbnail, cinematic 4:3 composition, "
            "no text, concept art"
        ),
        vision_rubric="reactive crafting thrown flasks altering terrain (mud, sand, ember, snow)",
        ollama_system=(
            "You are a senior art director for Soulash 2. Design earthy alchemical palettes for "
            "thrown terrain flasks. Return ONLY valid JSON."
        ),
        ollama_prompt_hint="reactive crafting terrain flask mod",
    ),
}


def resolve_theme(mod_path: Path, theme_arg: Optional[str]) -> BrandingTheme:
    if theme_arg:
        key = theme_arg.lower().replace("-", "_")
        if key in ("water", "water_magic"):
            key = "hydromancy"
        if key not in THEMES:
            raise ValueError(f"Unknown theme '{theme_arg}'. Choose: {', '.join(THEMES)}")
        return THEMES[key]
    folder = mod_path.name.lower()
    if folder in MOD_PATH_THEME:
        return THEMES[MOD_PATH_THEME[folder]]
    raise ValueError(
        f"Cannot auto-detect theme for '{mod_path.name}'. Pass --theme "
        f"({', '.join(THEMES.keys())})"
    )


def hex_to_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def lerp(c1: Tuple[int, int, int], c2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))  # type: ignore


def default_spec(theme: BrandingTheme) -> Dict[str, Any]:
    return {"motif": theme.ollama_prompt_hint, "palette": theme.palette, "composition": "centered"}


def fetch_design_spec(theme: BrandingTheme, asset_type: str) -> Dict[str, Any]:
    if not OLLAMA_AVAILABLE:
        return default_spec(theme)
    try:
        if not test_ollama_connection():
            return default_spec(theme)
    except Exception:
        return default_spec(theme)

    prompt = (
        f"Design a Soulash 2 mod {asset_type} for {theme.ollama_prompt_hint}. "
        "JSON fields: motif (string), palette (array of 6-7 #hex from darkest to lightest), "
        "composition (string). Dark fantasy pixel UI, readable at small size."
    )
    try:
        response = call_ollama(
            prompt=prompt,
            task_type="visual",
            response_length="standard",
            system_prompt=theme.ollama_system,
        )
        spec = parse_ollama_json(response, asset_type)
        pal = spec.get("palette")
        if not (isinstance(pal, list) and len(pal) >= 5):
            spec["palette"] = theme.palette
        return spec
    except Exception as exc:
        print(f"  [WARN] Ollama spec failed ({exc}); using default palette")
        return default_spec(theme)


def _radial_bg(size: Tuple[int, int], inner: Tuple[int, int, int], outer: Tuple[int, int, int]) -> Image.Image:
    w, h = size
    img = Image.new("RGBA", size)
    px = img.load()
    cx, cy = w / 2, h / 2
    maxd = math.hypot(cx, cy)
    for y in range(h):
        for x in range(w):
            t = min(1.0, math.hypot(x - cx, y - cy) / maxd)
            r, g, b = lerp(inner, outer, t ** 1.2)
            px[x, y] = (r, g, b, 255)
    return img


def _load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = [
        r"C:\Windows\Fonts\seguisb.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _draw_centered_text(draw: ImageDraw.ImageDraw, cx: float, y: float, text: str,
                        font: ImageFont.FreeTypeFont, fill, shadow=(0, 0, 0, 200)) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = cx - tw / 2
    draw.text((x + 2, y + 2), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=fill)


def _draw_pressure_rings(draw: ImageDraw.ImageDraw, cx: float, cy: float, radius: float,
                         color: Tuple[int, int, int], count: int = 4) -> None:
    for i in range(count, 0, -1):
        r = radius * (0.35 + i * 0.18)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color + (70 + i * 15,), width=max(1, int(radius * 0.04)))


def _layered_noise(size: Tuple[int, int], rng: random.Random, octaves: int = 4) -> Image.Image:
    """Multi-octave value noise for hand-painted grain/texture."""
    w, h = size
    accum = Image.new("L", size, 128)
    for o in range(octaves):
        scale = max(1, 2 ** (o + 1))
        lw, lh = max(2, w // scale), max(2, h // scale)
        layer = Image.new("L", (lw, lh))
        lp = layer.load()
        for y in range(lh):
            for x in range(lw):
                lp[x, y] = rng.randint(0, 255)
        layer = layer.resize(size, Image.Resampling.BILINEAR)
        accum = Image.blend(accum, layer, 0.34 / (o + 1))
    return accum.filter(ImageFilter.GaussianBlur(radius=max(1.0, min(w, h) * 0.006)))


def _apply_texture(img: Image.Image, rng: random.Random, strength: float = 0.16) -> Image.Image:
    """Overlay soft grain so surfaces read as painted, not flat fills."""
    noise = _layered_noise(img.size, rng, octaves=4).convert("RGBA")
    return Image.blend(img.convert("RGBA"), noise, strength)


def _directional_light(size: Tuple[int, int], strength: float = 0.2) -> Image.Image:
    """Warm top-left key light for shading/depth."""
    w, h = size
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    px = overlay.load()
    for y in range(h):
        for x in range(w):
            nx, ny = x / max(1, w - 1), y / max(1, h - 1)
            light = max(0.0, 1.0 - math.hypot(nx - 0.3, ny - 0.24) * 1.4)
            px[x, y] = (255, 244, 222, int(255 * light * strength))
    return overlay


def _vignette(img: Image.Image, strength: float = 0.4) -> Image.Image:
    w, h = img.size
    mask = Image.new("L", (w, h), 255)
    px = mask.load()
    cx, cy = w / 2, h / 2
    maxd = math.hypot(cx, cy)
    for y in range(h):
        for x in range(w):
            t = math.hypot(x - cx, y - cy) / maxd
            px[x, y] = int(255 * (1.0 - strength * (t ** 2.2)))
    dark = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    return Image.composite(img.convert("RGBA"), dark, mask)


def _glow(base: Image.Image, color: Tuple[int, int, int], radius: float, alpha: int) -> Image.Image:
    glow = base.copy().convert("RGBA").filter(ImageFilter.GaussianBlur(radius=radius))
    tint = Image.new("RGBA", glow.size, color + (alpha,))
    glow = ImageChops.multiply(glow, tint)
    return glow


def _spray(draw: ImageDraw.ImageDraw, cx: float, cy: float, radius: float,
           pal: List[Tuple[int, int, int]], rng: random.Random, count: int = 22) -> None:
    accent, highlight = pal[3], pal[4]
    for _ in range(count):
        ang = rng.uniform(0, math.tau)
        dist = rng.uniform(0.25, 1.05) * radius
        sx = cx + math.cos(ang) * dist
        sy = cy + math.sin(ang) * dist * 0.85
        r = rng.uniform(1.0, max(2.0, radius * 0.05))
        col = highlight if rng.random() > 0.5 else accent
        draw.ellipse([sx - r, sy - r, sx + r, sy + r], fill=col + (rng.randint(90, 200),))


def _water_blade(draw: ImageDraw.ImageDraw, x0: float, y0: float, x1: float, y1: float,
                 pal: List[Tuple[int, int, int]], width: float, rng: random.Random) -> None:
    """A tapered high-pressure water cutting jet with core highlight and spray."""
    deep, mid, accent, highlight = pal[1], pal[2], pal[3], pal[4]
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / length, dx / length
    body = [
        (x0 + nx * width, y0 + ny * width), (x1 + nx * width * 0.25, y1 + ny * width * 0.25),
        (x1 - nx * width * 0.25, y1 - ny * width * 0.25), (x0 - nx * width, y0 - ny * width),
    ]
    draw.polygon(body, fill=mid + (235,))
    draw.polygon([(x0 + nx * width * 0.45, y0 + ny * width * 0.45),
                  (x1, y1), (x0 - nx * width * 0.2, y0 - ny * width * 0.2)],
                 fill=highlight + (190,))
    draw.line([(x0, y0), (x1, y1)], fill=deep + (200,), width=max(1, int(width * 0.16)))
    for _ in range(6):
        t = rng.uniform(0.25, 0.95)
        px = x0 + dx * t + rng.uniform(-width, width)
        py = y0 + dy * t + rng.uniform(-width, width)
        r = rng.uniform(1.0, width * 0.3)
        draw.ellipse([px - r, py - r, px + r, py + r], fill=accent + (rng.randint(70, 150),))


def _draw_hydromancy_drop(draw: ImageDraw.ImageDraw, cx: float, cy: float, radius: float,
                          pal: List[Tuple[int, int, int]], rng: Optional[random.Random] = None) -> None:
    rng = rng or random.Random(int(cx * 7 + cy * 13 + radius))
    deep, mid, accent, highlight, rim = pal[1], pal[2], pal[3], pal[4], pal[5] if len(pal) > 5 else pal[4]
    _draw_pressure_rings(draw, cx, cy, radius, accent)
    # crossed pressurized water cutting blades behind the droplet
    _water_blade(draw, cx - radius * 0.9, cy + radius * 0.5, cx + radius * 0.95, cy - radius * 0.55,
                 pal, radius * 0.16, rng)
    _water_blade(draw, cx - radius * 0.7, cy - radius * 0.6, cx + radius * 0.8, cy + radius * 0.6,
                 pal, radius * 0.11, rng)
    drop_h, drop_w = radius * 1.1, radius * 0.66
    # drop shadow for depth
    draw.polygon([(cx + 2, cy - drop_h * 0.5), (cx + drop_w + 2, cy + drop_h * 0.18),
                  (cx + 2, cy + drop_h * 0.58), (cx - drop_w + 2, cy + drop_h * 0.18)],
                 fill=deep + (120,))
    drop = [(cx, cy - drop_h * 0.55), (cx + drop_w, cy + drop_h * 0.15),
            (cx, cy + drop_h * 0.55), (cx - drop_w, cy + drop_h * 0.15)]
    draw.polygon(drop, fill=mid + (255,))
    draw.polygon(drop, outline=deep + (200,), width=max(1, int(radius * 0.05)))
    # inner gradient bands for volume
    for k, t in enumerate((0.75, 0.5, 0.28)):
        col = lerp(mid, highlight, 1 - t)
        draw.polygon([(cx, cy - drop_h * 0.55 * t), (cx + drop_w * t, cy + drop_h * 0.15 * t),
                      (cx, cy + drop_h * 0.55 * t), (cx - drop_w * t, cy + drop_h * 0.15 * t)],
                     fill=col + (150,))
    draw.polygon([(cx - drop_w * 0.15, cy - drop_h * 0.35), (cx + drop_w * 0.25, cy - drop_h * 0.05),
                  (cx, cy + drop_h * 0.2), (cx - drop_w * 0.35, cy + drop_h * 0.05)],
                 fill=highlight + (190,))
    draw.ellipse([cx - drop_w * 0.35, cy - drop_h * 0.25, cx - drop_w * 0.05, cy + drop_h * 0.05],
                 fill=rim + (230,))
    _spray(draw, cx, cy, radius * 1.15, pal, rng, count=20)


def _branch_artery(draw: ImageDraw.ImageDraw, x0: float, y0: float, ang: float, length: float,
                   pal: List[Tuple[int, int, int]], rng: random.Random, depth: int = 0) -> None:
    if length < 3 or depth > 4:
        return
    x1 = x0 + math.cos(ang) * length
    y1 = y0 + math.sin(ang) * length
    col = pal[min(3 + depth, len(pal) - 1)]
    draw.line([(x0, y0), (x1, y1)], fill=col + (215,), width=max(1, int(length * 0.09)))
    if depth < 3:
        spread = 0.45 + rng.random() * 0.28
        _branch_artery(draw, x1, y1, ang - spread, length * 0.7, pal, rng, depth + 1)
        _branch_artery(draw, x1, y1, ang + spread, length * 0.66, pal, rng, depth + 1)


def _rupture_cracks(draw: ImageDraw.ImageDraw, cx: float, cy: float, radius: float,
                    pal: List[Tuple[int, int, int]], rng: random.Random, count: int = 7) -> None:
    deep, accent = pal[1], pal[4] if len(pal) > 4 else pal[-1]
    for _ in range(count):
        ang = rng.uniform(0, math.tau)
        x, y = cx, cy
        pts = [(x, y)]
        seg = radius * rng.uniform(0.2, 0.42)
        for _ in range(rng.randint(3, 5)):
            x += math.cos(ang + rng.uniform(-0.5, 0.5)) * seg
            y += math.sin(ang + rng.uniform(-0.5, 0.5)) * seg
            pts.append((x, y))
            seg *= 0.78
        draw.line(pts, fill=deep + (200,), width=max(1, int(radius * 0.04)))
        draw.line(pts, fill=accent + (130,), width=max(1, int(radius * 0.02)))


def _draw_hemohydraulic_heart(draw: ImageDraw.ImageDraw, cx: float, cy: float, radius: float,
                              pal: List[Tuple[int, int, int]], rng: Optional[random.Random] = None) -> None:
    rng = rng or random.Random(int(cx * 5 + cy * 11 + radius))
    deep, mid, accent, highlight = pal[1], pal[3], pal[4], pal[5] if len(pal) > 5 else pal[4]
    _draw_pressure_rings(draw, cx, cy, radius * 1.1, mid, count=3)
    hw, hh = radius * 0.95, radius * 0.85
    # arteries branching out first (behind the heart body)
    _branch_artery(draw, cx, cy - hh * 0.4, -math.pi / 2, radius * 0.6, pal, rng)
    _branch_artery(draw, cx - hw * 0.25, cy - hh * 0.1, math.pi * 0.85, radius * 0.5, pal, rng)
    _branch_artery(draw, cx + hw * 0.25, cy - hh * 0.1, math.pi * 0.15, radius * 0.48, pal, rng)
    # drop shadow
    draw.polygon([(cx + 3, cy - hh * 0.05), (cx - hw * 0.5, cy + 3), (cx + 3, cy + hh * 0.68)],
                 fill=deep + (110,))
    heart = [cx - hw * 0.55, cy - hh * 0.1, cx - hw * 0.1, cy - hh * 0.55,
             cx, cy - hh * 0.25, cx + hw * 0.1, cy - hh * 0.55, cx + hw * 0.55, cy - hh * 0.1,
             cx, cy + hh * 0.65]
    draw.polygon(heart, fill=accent + (255,))
    # inner shading bands for volume
    for t in (0.72, 0.46):
        col = lerp(accent, deep, 1 - t)
        inner = [cx - hw * 0.55 * t, cy - hh * 0.1 * t, cx - hw * 0.1 * t, cy - hh * 0.55 * t,
                 cx, cy - hh * 0.25 * t, cx + hw * 0.1 * t, cy - hh * 0.55 * t, cx + hw * 0.55 * t,
                 cy - hh * 0.1 * t, cx, cy + hh * 0.65 * t]
        draw.polygon(inner, fill=col + (90,))
    draw.polygon(heart, outline=deep + (255,), width=max(1, int(radius * 0.07)))
    draw.line([(cx - hw * 0.35, cy - hh * 0.05), (cx + hw * 0.4, cy + hh * 0.35)],
              fill=highlight + (205,), width=max(2, int(radius * 0.11)))
    draw.line([(cx - hw * 0.15, cy + hh * 0.05), (cx + hw * 0.55, cy + hh * 0.45)],
              fill=mid + (175,), width=max(1, int(radius * 0.07)))
    draw.ellipse([cx - hw * 0.2, cy - hh * 0.15, cx + hw * 0.05, cy + hh * 0.05], fill=highlight + (170,))
    _rupture_cracks(draw, cx, cy + hh * 0.1, radius * 0.75, pal, rng)
    _spray(draw, cx, cy, radius * 1.05, pal, rng, count=14)


def render_icon_procedural(theme: BrandingTheme, spec: Dict[str, Any], seed: int = 7) -> Image.Image:
    S = 16  # supersample 512px then downscale for crisp, dense pixel art
    W = 32 * S
    size = (W, W)
    rng = random.Random(seed)
    pal = [hex_to_rgb(c) for c in (spec.get("palette") or theme.palette)]
    img = _radial_bg(size, lerp(pal[2], pal[1], 0.42), pal[0])
    img = _apply_texture(img, rng, strength=0.14)
    draw = ImageDraw.Draw(img, "RGBA")
    cx, cy = W / 2, W / 2 + W * 0.02
    if theme.name == "hemohydraulic":
        _draw_hemohydraulic_heart(draw, cx, cy, W * 0.33, pal, rng)
        glow_col = pal[4]
    elif theme.name == "hydromancy":
        _draw_hydromancy_drop(draw, cx, cy, W * 0.36, pal, rng)
        glow_col = pal[3]
    else:
        from generate_reactive_crafting_assets import render_icon as reactive_icon  # noqa: WPS433
        return reactive_icon(spec, seed)

    img = Image.alpha_composite(img, _directional_light(size, strength=0.16))
    img = Image.alpha_composite(img, _glow(img, glow_col, radius=S * 0.85, alpha=48))
    img = _vignette(img, strength=0.35)
    img = img.filter(ImageFilter.GaussianBlur(radius=S * 0.10))
    img = img.resize((32, 32), Image.Resampling.LANCZOS)
    img = ImageEnhance.Sharpness(img).enhance(1.4)
    return finalize_icon(img)


def render_thumbnail_procedural(theme: BrandingTheme, spec: Dict[str, Any], seed: int = 11) -> Image.Image:
    if theme.name == "reactive_crafting":
        from generate_reactive_crafting_assets import render_thumbnail as reactive_thumb  # noqa: WPS433
        return reactive_thumb(spec, seed)

    rng = random.Random(seed)
    size = (800, 600)
    pal = [hex_to_rgb(c) for c in (spec.get("palette") or theme.palette)]
    img = _radial_bg(size, lerp(pal[2], pal[1], 0.33), pal[0])
    img = _apply_texture(img, rng, strength=0.12)
    draw = ImageDraw.Draw(img, "RGBA")

    if theme.name == "hydromancy":
        # background sweep of cutting jets for depth, then a dominant foreground blade
        for i in range(5):
            y = size[1] * (0.5 + i * 0.07)
            _water_blade(draw, size[0] * 0.06, y + rng.randint(-15, 15),
                         size[0] * 0.94, y - rng.randint(25, 70), pal, 10 + i * 2, rng)
        for i in range(6):
            cx = size[0] * (0.16 + i * 0.13) + rng.randint(-18, 18)
            cy = size[1] * (0.55 + (i % 3) * 0.08)
            _draw_hydromancy_drop(draw, cx, cy, 40 + i * 6, pal, rng)
        _water_blade(draw, size[0] * 0.32, size[1] * 0.88, size[0] * 0.6, size[1] * 0.36, pal, 26, rng)
        _draw_hydromancy_drop(draw, size[0] * 0.5, size[1] * 0.54, 135, pal, rng)
        _spray(draw, size[0] * 0.5, size[1] * 0.6, 260, pal, rng, count=55)
    else:
        for i in range(6):
            ang = rng.uniform(0, math.tau)
            dist = rng.uniform(70, 210)
            sx = size[0] / 2 + math.cos(ang) * dist
            sy = size[1] * 0.55 + math.sin(ang) * dist * 0.55
            _draw_hemohydraulic_heart(draw, sx, sy, 24 + i * 4, pal, rng)
        _draw_hemohydraulic_heart(draw, size[0] * 0.5, size[1] * 0.52, 140, pal, rng)
        _rupture_cracks(draw, size[0] * 0.5, size[1] * 0.55, 190, pal, rng, count=10)
        _spray(draw, size[0] * 0.5, size[1] * 0.55, 240, pal, rng, count=45)

    # darkened title banner for legibility
    banner_h = 132
    banner = Image.new("RGBA", size, (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(banner, "RGBA")
    for y in range(banner_h):
        alpha = int(205 * (1.0 - (y / banner_h) * 0.7))
        bdraw.line([(0, y), (size[0], y)], fill=pal[0] + (alpha,))
    img = Image.alpha_composite(img, banner)
    draw = ImageDraw.Draw(img, "RGBA")

    title_font = _load_font(66 if theme.name == "hemohydraulic" else 72, bold=True)
    sub_font = _load_font(28, bold=False)
    _draw_centered_text(draw, size[0] / 2, 30, theme.display_name, title_font, fill=(*pal[-1], 255))
    _draw_centered_text(draw, size[0] / 2, 106, theme.subtitle, sub_font,
                        fill=(*lerp(pal[4], pal[-1], 0.4), 255))

    img = Image.alpha_composite(img, _directional_light(size, strength=0.13))
    img = _vignette(img, strength=0.3)
    img = ImageEnhance.Contrast(img).enhance(1.08)
    img = ImageEnhance.Color(img).enhance(1.06)
    img = img.filter(ImageFilter.SHARPEN)
    return img.convert("RGBA")


def vision_qa(image_path: Path, asset_type: str, theme: BrandingTheme, model: str) -> Tuple[bool, float, str]:
    try:
        import requests
    except ImportError:
        return True, 0.75, "requests unavailable; skipped"
    if not image_path.exists():
        return False, 0.0, "file missing"
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    prompt = (
        f"Rate this Soulash 2 mod {asset_type} for {theme.vision_rubric}. "
        'Return JSON only: {"score": 0-100, "pass": true/false, "issues": "..."}. '
        "Pass if readable, on-theme palette, good contrast, not a muddy blur."
    )
    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "images": [b64], "stream": False, "format": "json"},
            timeout=180,
        )
        resp.raise_for_status()
        data = parse_ollama_json(resp.json().get("response", ""), asset_type)
        score = float(data.get("score", 70)) / 100.0
        passed = bool(data.get("pass", score >= 0.65))
        return passed, score, str(data.get("issues", "")) or "ok"
    except Exception as exc:
        return True, 0.7, f"vision QA skipped: {exc}"


def _drafts_dir(mod_path: Path) -> Path:
    return mod_path / "DesignDrafts"


def _negative_prompt(theme: BrandingTheme) -> str:
    extra = f", {theme.sd_negative_extra}" if theme.sd_negative_extra else ""
    return SD_NEGATIVE_PROMPT + extra


def _is_oom_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "out of memory" in msg or ("cuda" in msg and "memory" in msg)


def _generate_sd_draft(prompt: str, output_path: Path, settings: Dict[str, Any],
                       api_url: str, label: str, negative: str) -> Tuple[bool, float, Dict[str, Any], str]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"  [SD] {label}: {settings['width']}x{settings['height']} @ {settings['steps']} steps "
          f"(timeout {int(SD_TIMEOUT_SEC)}s)...")
    t0 = time.monotonic()
    err = ""
    try:
        generate_image(
            prompt=prompt, output_path=output_path, api_url=api_url,
            negative_prompt=negative, width=settings["width"], height=settings["height"],
            steps=settings["steps"], guidance_scale=settings.get("guidance_scale", 7.5),
            seed=settings.get("seed", 0), timeout=SD_TIMEOUT_SEC,
        )
        elapsed = time.monotonic() - t0
        ok = output_path.exists() and output_path.stat().st_size > 0
        print(f"  [{'OK' if ok else 'WARN'}] SD {label} ({elapsed:.1f}s)")
        return ok, elapsed, settings, err
    except Exception as exc:
        elapsed = time.monotonic() - t0
        err = str(exc)
        print(f"  [WARN] SD {label} failed after {elapsed:.1f}s: {exc}")
        return False, elapsed, settings, err


def _acquire_sd_lock(label: str) -> bool:
    """Exclusive lock so only one SD HTTP job runs cluster-wide."""
    SD_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SD_LOCK_PATH.exists():
        age = time.time() - SD_LOCK_PATH.stat().st_mtime
        if age < SD_LOCK_STALE_SEC:
            try:
                holder = SD_LOCK_PATH.read_text(encoding="utf-8").strip()
            except Exception:
                holder = "?"
            print(f"  [WAIT] SD lock held by {holder} ({age:.0f}s ago); waiting...")
            deadline = time.monotonic() + SD_TIMEOUT_SEC
            while time.monotonic() < deadline:
                time.sleep(10)
                if not SD_LOCK_PATH.exists():
                    break
                age = time.time() - SD_LOCK_PATH.stat().st_mtime
                if age >= SD_LOCK_STALE_SEC:
                    break
            if SD_LOCK_PATH.exists() and time.time() - SD_LOCK_PATH.stat().st_mtime < SD_LOCK_STALE_SEC:
                print("  [WARN] SD lock timeout; skipping SD for this image")
                return False
    SD_LOCK_PATH.write_text(f"{label} pid={os.getpid()}", encoding="utf-8")
    return True


def _release_sd_lock() -> None:
    try:
        if SD_LOCK_PATH.exists():
            SD_LOCK_PATH.unlink()
    except Exception:
        pass


def generate_single_sd_draft(
    theme: BrandingTheme,
    mod_path: Path,
    kind: str,
    api_url: Optional[str],
) -> Tuple[Optional[Path], List[Dict[str, Any]]]:
    """Generate exactly one SD draft (icon OR thumbnail). Strictly one GPU job."""
    log: List[Dict[str, Any]] = []
    if not SD_AVAILABLE:
        print("  [WARN] sd_http_client unavailable")
        return None, log

    lock_label = f"{mod_path.name}:{kind}"
    if not _acquire_sd_lock(lock_label):
        return None, log
    try:
        return _generate_single_sd_draft_locked(theme, mod_path, kind, api_url, log)
    finally:
        _release_sd_lock()


def _generate_single_sd_draft_locked(
    theme: BrandingTheme,
    mod_path: Path,
    kind: str,
    api_url: Optional[str],
    log: List[Dict[str, Any]],
) -> Tuple[Optional[Path], List[Dict[str, Any]]]:
    api_url = api_url or detect_server(verbose=True)
    if not api_url:
        print("  [WARN] No SD server detected")
        return None, log

    is_icon = kind == "icon"
    prompt = theme.sd_icon_prompt if is_icon else theme.sd_thumb_prompt
    out_path = _drafts_dir(mod_path) / (DRAFT_ICON_NAME if is_icon else DRAFT_THUMB_NAME)
    if is_icon:
        primary = planned_sd_settings("icon", 32, 32, seed=42, guidance_scale=7.0)
    else:
        primary = planned_sd_settings("banner", 800, 600, seed=43, guidance_scale=7.0)
    fallback = SD_ICON_FALLBACK if is_icon else SD_THUMB_FALLBACK
    oom_settings = SD_ICON_OOM if is_icon else SD_THUMB_OOM
    label = f"{kind} draft"
    negative = _negative_prompt(theme)

    ok, elapsed, used, err = _generate_sd_draft(prompt, out_path, primary, api_url, label, negative)
    entry = {"asset": label, "ok": ok, "elapsed_sec": round(elapsed, 1), "settings": used, "error": err}
    log.append(entry)
    if ok:
        return out_path, log

    if _is_oom_error(Exception(err)):
        print(f"  [SD] CUDA OOM on {label}; retrying at reduced resolution...")
        ok, elapsed2, used2, err2 = _generate_sd_draft(
            prompt, out_path, oom_settings, api_url, f"{label} (oom-reduced)", negative
        )
        log.append({"asset": f"{label} (oom-reduced)", "ok": ok, "elapsed_sec": round(elapsed2, 1),
                    "settings": used2, "error": err2, "oom_retry": True})
        if ok:
            return out_path, log

    print(f"  [SD] Retrying {label} with standard fallback settings...")
    ok, elapsed3, used3, err3 = _generate_sd_draft(
        prompt, out_path, fallback, api_url, f"{label} (fallback)", negative
    )
    log.append({"asset": f"{label} (fallback)", "ok": ok, "elapsed_sec": round(elapsed3, 1),
                "settings": used3, "error": err3})
    return (out_path if ok else None), log


def generate_sd_drafts(theme: BrandingTheme, mod_path: Path, api_url: Optional[str]) -> Tuple[Optional[Path], Optional[Path], List[Dict[str, Any]]]:
    """Legacy: generate both drafts sequentially (icon then thumbnail)."""
    log: List[Dict[str, Any]] = []
    icon, icon_log = generate_single_sd_draft(theme, mod_path, "icon", api_url)
    log.extend(icon_log)
    thumb, thumb_log = generate_single_sd_draft(theme, mod_path, "thumbnail", api_url)
    log.extend(thumb_log)
    return icon, thumb, log


def sd_allowed_for_kind(kind: str, use_sd: bool) -> bool:
    """SD only for thumbnails; 32x32 icons are always procedural."""
    return use_sd and kind == "thumbnail"


def generate_asset(
    kind: str,
    mod_path: Path,
    theme: BrandingTheme,
    quality: str,
    model: str,
    max_attempts: int,
    use_spec: bool,
    use_sd: bool,
    sd_draft_icon: Optional[Path],
    sd_draft_thumbnail: Optional[Path],
    sd_log: Optional[List[Dict[str, Any]]],
    prefer_keep_backup: bool = False,
    backup_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    is_icon = kind == "icon"
    out_name = "S.png" if is_icon else "thumbnail2.png"
    out_path = mod_path / out_name
    asset_type = "icon" if is_icon else "thumbnail"
    spec = fetch_design_spec(theme, asset_type) if use_spec else default_spec(theme)
    draft_path = sd_draft_icon if is_icon else sd_draft_thumbnail

    def _render_proc(seed: int) -> Image.Image:
        if is_icon:
            return render_icon_procedural(theme, spec, seed)
        return render_thumbnail_procedural(theme, spec, seed)

    def _render_sd(seed: int) -> Image.Image:
        assert draft_path is not None
        with Image.open(draft_path) as src:
            if is_icon:
                return finalize_icon_from_sd(src.copy())
            return finalize_thumbnail_from_sd(src.copy())

    # Policy: SD is only ever applied to thumbnails. 32x32 icons are ALWAYS
    # procedural, even if --use-sd is passed or a stray icon draft path exists.
    want_sd = sd_allowed_for_kind(kind, use_sd)
    render_fn: Callable[[int], Image.Image] = _render_proc
    source = "procedural"
    if want_sd and draft_path and draft_path.exists():
        render_fn = _render_sd
        source = "sd"

    backup_path = (backup_dir / out_name) if backup_dir and (backup_dir / out_name).exists() else None
    best_backup_score = 0.0
    if backup_path:
        with Image.open(backup_path) as old:
            best_backup_score = score_palette_match(old, theme.palette)

    best: Optional[Dict[str, Any]] = None
    for attempt in range(1, max_attempts + 1):
        seed = 7 + attempt * 13
        img = render_fn(seed)
        img.save(out_path)

        mech_ok, mech_reason = (validate_mod_icon(img) if is_icon else validate_thumbnail(img))
        pal_score = score_palette_match(img, theme.palette)
        report: Dict[str, Any] = {
            "attempt": attempt, "path": str(out_path), "source": source,
            "palette_score": round(pal_score, 3),
            "mechanical": {"pass": mech_ok, "reason": mech_reason},
        }
        if sd_log:
            report["sd_generation"] = sd_log
        print(f"  [{kind}] attempt {attempt} ({source}): mech={'PASS' if mech_ok else 'FAIL'} "
              f"palette={pal_score:.2f} ({mech_reason})")

        if not mech_ok:
            if source == "sd":
                render_fn = _render_proc
                source = "procedural"
                best = report
                continue
            best = report
            continue

        if quality == "full":
            v_ok, v_score, v_reason = vision_qa(out_path, asset_type, theme, model)
            report["vision"] = {"pass": v_ok, "score": round(v_score, 3), "reason": v_reason}
            report["pass"] = v_ok
            if not v_ok:
                if best is None or v_score > best.get("vision", {}).get("score", 0):
                    best = report
                if source == "sd":
                    render_fn = _render_proc
                    source = "procedural"
                continue
        else:
            report["pass"] = True

        if prefer_keep_backup and backup_path and pal_score < best_backup_score * 0.85:
            print(f"  [{kind}] New asset palette score {pal_score:.2f} < backup {best_backup_score:.2f}; keeping backup")
            shutil.copy2(backup_path, out_path)
            report["source"] = "backup_kept"
            report["pass"] = True
            report["final"] = True
            return report

        report["final"] = True
        return report

    if source == "sd" and draft_path:
        print(f"  [{kind}] SD exhausted; procedural fallback")
        img = _render_proc(7 + max_attempts * 13)
        img.save(out_path)
        mech_ok, mech_reason = (validate_mod_icon(img) if is_icon else validate_thumbnail(img))
        return {
            "attempt": max_attempts + 1, "path": str(out_path), "source": "procedural_fallback",
            "mechanical": {"pass": mech_ok, "reason": mech_reason}, "pass": mech_ok, "final": mech_ok,
            "sd_generation": sd_log,
        }

    if best:
        best["final"] = False
        return best
    return {"kind": kind, "pass": False, "reason": "no attempts"}


def backup_existing_assets(mod_path: Path) -> Optional[Path]:
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup_dir = mod_path / "asset_backups" / ts
    copied = False
    for name in ("S.png", "thumbnail2.png"):
        src = mod_path / name
        if src.exists():
            backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, backup_dir / name)
            copied = True
    return backup_dir if copied else None


def run_generation(
    mod_path: Path,
    theme: BrandingTheme,
    mode: str = "all",
    quality: str = "mechanical",
    use_sd: bool = False,
    api_url: Optional[str] = None,
    use_ollama_spec: bool = False,
    model: str = "qwen3-vl:8b",
    max_attempts: int = 3,
    prefer_keep_backup: bool = False,
    skip_backup: bool = False,
) -> Dict[str, Any]:
    mod_path = mod_path.resolve()
    backup_dir = None if skip_backup else backup_existing_assets(mod_path)
    if backup_dir:
        print(f"  [OK] Backed up existing assets to {backup_dir}")

    kinds = ["icon", "thumbnail"] if mode == "all" else [mode]
    results = []
    sd_icon: Optional[Path] = None
    sd_thumb: Optional[Path] = None

    def _run_kinds(session_url: Optional[str]) -> None:
        nonlocal sd_icon, sd_thumb
        for kind in kinds:
            sd_log: List[Dict[str, Any]] = []
            if sd_allowed_for_kind(kind, use_sd):
                print(f"\n-- SD {kind} draft (sequential, one job) --")
                draft, sd_log = generate_single_sd_draft(
                    theme, mod_path, kind, session_url or api_url
                )
                if kind == "thumbnail":
                    sd_thumb = draft

            print(f"\n-- generating {kind} ({theme.name}) --")
            results.append(generate_asset(
                kind, mod_path, theme, quality, model, max_attempts, use_ollama_spec, use_sd,
                sd_icon, sd_thumb, sd_log if sd_allowed_for_kind(kind, use_sd) else None,
                prefer_keep_backup=prefer_keep_backup, backup_dir=backup_dir,
            ))

    if use_sd and any(sd_allowed_for_kind(k, True) for k in kinds):
        with sd_session(use_sd=True) as session_url:
            _run_kinds(session_url)
    else:
        _run_kinds(api_url)
    return {"mod": str(mod_path), "theme": theme.name, "backup_dir": str(backup_dir) if backup_dir else None, "results": results}


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate themed Soulash 2 mod branding assets")
    ap.add_argument("--mod-path", type=Path, required=True)
    ap.add_argument("--theme", default=None, help="hemohydraulic | hydromancy | reactive_crafting")
    ap.add_argument("--mode", choices=["icon", "thumbnail", "all"], default="all")
    ap.add_argument("--quality", choices=["mechanical", "full"], default="mechanical")
    ap.add_argument("--model", default="qwen3-vl:8b")
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--use-ollama-spec", action="store_true")
    ap.add_argument("--use-sd", action="store_true",
                    help="SD concept drafts for thumbnails only (icons stay procedural)")
    ap.add_argument("--sd-api-url", default=None)
    ap.add_argument("--prefer-keep-backup", action="store_true",
                    help="Keep prior asset if new palette score is worse (water magic)")
    ap.add_argument("--skip-backup", action="store_true",
                    help="Do not backup existing assets (used between sequential jobs)")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    except Exception:
        pass

    mod_path = args.mod_path.resolve()
    if not mod_path.exists():
        print(f"[FAIL] mod path not found: {mod_path}")
        return 2

    try:
        theme = resolve_theme(mod_path, args.theme)
    except ValueError as exc:
        print(f"[FAIL] {exc}")
        return 2

    print(f"== Mod branding: {theme.display_name} ==")
    print(f"mod: {mod_path}")
    sd_note = "thumbnails only" if args.use_sd else "off"
    print(f"sd: {sd_note} | icons: procedural | quality: {args.quality}")

    summary = run_generation(
        mod_path, theme, args.mode, args.quality, args.use_sd, args.sd_api_url,
        args.use_ollama_spec, args.model, args.max_attempts, args.prefer_keep_backup,
        skip_backup=args.skip_backup,
    )

    print("\n== SUMMARY ==")
    all_pass = True
    for r in summary["results"]:
        ok = r.get("pass", False)
        all_pass = all_pass and ok
        tag = "PASS" if ok else "FAIL"
        print(f"  [{tag}] {r.get('path', '?')} source={r.get('source')} "
              f":: {r.get('mechanical', {}).get('reason', '')}")
    print(json.dumps(summary, indent=2))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
