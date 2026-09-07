#!/usr/bin/env python3
"""
Rich procedural PIL rendering helpers for Qud asset fallbacks.

Supersample → GaussianBlur → LANCZOS downscale → sharpen/contrast finalize.
Used when SD is unavailable or for small UI sprites that need readable detail.
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

RGB = Tuple[int, int, int]
RGBA = Tuple[int, int, int, int]


def hex_to_rgb(hex_color: str, default: RGB = (128, 128, 128)) -> RGB:
    h = str(hex_color or "").lstrip("#").lower()
    if len(h) == 6:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    return default


def lerp(c1: RGB, c2: RGB, t: float) -> RGB:
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))  # type: ignore[return-value]


def radial_background(size: Tuple[int, int], inner: RGB, outer: RGB, power: float = 1.2) -> Image.Image:
    w, h = size
    img = Image.new("RGBA", size)
    px = img.load()
    cx, cy = w / 2, h / 2
    maxd = max(1.0, math.hypot(cx, cy))
    for y in range(h):
        for x in range(w):
            t = min(1.0, math.hypot(x - cx, y - cy) / maxd) ** power
            r, g, b = lerp(inner, outer, t)
            px[x, y] = (r, g, b, 255)
    return img


def draw_pressure_rings(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    radius: float,
    color: RGB,
    count: int = 4,
    width_scale: float = 0.04,
) -> None:
    for i in range(count, 0, -1):
        r = radius * (0.32 + i * 0.16)
        alpha = 70 + i * 18
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            outline=color + (alpha,),
            width=max(1, int(radius * width_scale)),
        )


def apply_vignette(img: Image.Image, strength: float = 0.35) -> Image.Image:
    img = img.convert("RGBA")
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = overlay.load()
    cx, cy = w / 2, h / 2
    maxd = math.hypot(cx, cy)
    for y in range(h):
        for x in range(w):
            t = (math.hypot(x - cx, y - cy) / maxd) ** 1.4
            alpha = int(255 * strength * t)
            px[x, y] = (0, 0, 0, alpha)
    return Image.alpha_composite(img, overlay)


def add_noise_grain(img: Image.Image, amount: float = 0.06, seed: int = 0) -> Image.Image:
    img = img.convert("RGBA")
    rng = random.Random(seed)
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 8:
                continue
            n = int((rng.random() - 0.5) * 255 * amount)
            px[x, y] = (
                max(0, min(255, r + n)),
                max(0, min(255, g + n)),
                max(0, min(255, b + n)),
                a,
            )
    return img


def supersample_finalize(
    img: Image.Image,
    target_size: Tuple[int, int],
    *,
    blur_radius: float = 0.55,
    sharpen: float = 1.28,
    contrast: float = 1.10,
    saturation: float = 1.06,
) -> Image.Image:
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    if blur_radius > 0:
        img = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    if img.size != target_size:
        img = img.resize(target_size, Image.Resampling.LANCZOS)
    img = ImageEnhance.Sharpness(img).enhance(sharpen)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = ImageEnhance.Color(img).enhance(saturation)
    return img


def render_at_scale(
    draw_fn,
    target_size: Tuple[int, int],
    scale: int = 8,
    **kwargs,
) -> Image.Image:
    """Render draw_fn at scale× resolution, then downscale."""
    big = (target_size[0] * scale, target_size[1] * scale)
    img = draw_fn(big, **kwargs)
    return supersample_finalize(img, target_size, blur_radius=scale * 0.07)


def _palette_from_design(design: Dict, defaults: Dict[str, str]) -> Dict[str, RGB]:
    cs = design.get("colorScheme") or {}
    out: Dict[str, RGB] = {}
    for key, default_hex in defaults.items():
        out[key] = hex_to_rgb(cs.get(key, default_hex))
    return out


def render_rich_mutation_icon(
    design: Dict,
    mutation_type: str,
    size: Tuple[int, int],
    seed: int = 7,
) -> Image.Image:
    """Layered mutation icon: radial bg, motif spiral, pressure rings, rim highlight."""
    pal = _palette_from_design(
        design,
        {
            "primary": "#4a90e2",
            "secondary": "#7bb3f0",
            "glow": "#00ffff",
            "void": "#000033",
            "outline": "#1a1a4a",
        },
    )
    scale = 8 if max(size) <= 48 else 4

    def _draw(big: Tuple[int, int]) -> Image.Image:
        w, h = big
        cx, cy = w / 2, h / 2
        img = radial_background(big, lerp(pal["void"], pal["primary"], 0.25), pal["void"])
        draw = ImageDraw.Draw(img, "RGBA")
        draw_pressure_rings(draw, cx, cy, min(w, h) * 0.42, pal["glow"], count=5)

        arms = 2 if "mental" in mutation_type.lower() else 3
        max_r = min(w, h) * 0.38
        for arm in range(arms):
            arm_angle = (math.pi * arm / max(1, arms - 1)) if arms > 1 else 0.0
            for i in range(180):
                t = i / 180
                angle = arm_angle + t * 7 * math.pi
                radius = t * max_r * math.exp(t * 0.35)
                x = cx + radius * math.cos(angle)
                y = cy + radius * math.sin(angle)
                color = lerp(pal["primary"], pal["secondary"], t)
                thick = max(1, int((1 - t * 0.75) * w * 0.018))
                draw.ellipse([x - thick, y - thick, x + thick, y + thick], fill=color + (220,))

        core_r = max_r * 0.22
        draw.ellipse(
            [cx - core_r, cy - core_r, cx + core_r, cy + core_r],
            fill=pal["void"] + (255,),
            outline=pal["outline"] + (255,),
            width=max(1, int(w * 0.012)),
        )
        inner = core_r * 0.55
        draw.ellipse(
            [cx - inner, cy - inner, cx + inner, cy + inner],
            fill=(0, 0, 0, 255),
            outline=pal["glow"] + (180,),
            width=max(1, int(w * 0.006)),
        )
        # Rim highlight (upper-left)
        highlight = lerp(pal["glow"], (255, 255, 255), 0.35)
        draw.arc(
            [cx - core_r * 1.1, cy - core_r * 1.1, cx + core_r * 0.3, cy + core_r * 0.2],
            start=200,
            end=320,
            fill=highlight + (140,),
            width=max(1, int(w * 0.008)),
        )
        img = apply_vignette(img, 0.28)
        return add_noise_grain(img, 0.05, seed=seed)

    return render_at_scale(_draw, size, scale=scale)


def render_rich_ability_icon(
    design: Optional[Dict],
    is_aggressive: bool,
    size: Tuple[int, int],
    seed: int = 11,
) -> Image.Image:
    defaults = (
        {"primary": "#ff8000", "secondary": "#ff4000", "glow": "#ffa040", "outline": "#cc0000", "void": "#1a0800"}
        if is_aggressive
        else {"primary": "#3280ff", "secondary": "#50a0ff", "glow": "#78c0ff", "outline": "#1a50cc", "void": "#000818"}
    )
    pal = _palette_from_design(design or {}, defaults)
    shape_type = "diamond"
    if design:
        shape_type = (design.get("shape") or {}).get("type", "diamond" if is_aggressive else "circle")
    scale = 8

    def _draw(big: Tuple[int, int]) -> Image.Image:
        w, h = big
        cx, cy = w / 2, h / 2
        img = radial_background(big, lerp(pal["void"], pal["primary"], 0.3), pal["void"])
        draw = ImageDraw.Draw(img, "RGBA")
        draw_pressure_rings(draw, cx, cy, min(w, h) * 0.4, pal["glow"], count=4)

        r = min(w, h) * 0.28
        if shape_type == "diamond" or is_aggressive:
            points = [
                (cx, cy - r),
                (cx + r, cy),
                (cx, cy + r),
                (cx - r, cy),
            ]
            # Faceted fill
            mid = lerp(pal["primary"], pal["secondary"], 0.5)
            draw.polygon(points, fill=pal["primary"] + (230,))
            facet = [
                (cx, cy - r),
                (cx + r * 0.15, cy - r * 0.15),
                (cx, cy),
                (cx - r * 0.15, cy - r * 0.15),
            ]
            draw.polygon(facet, fill=mid + (200,))
            draw.polygon(points, outline=pal["outline"] + (255,), width=max(1, int(w * 0.012)))
            # Inner chevron for aggression
            chev = r * 0.35
            draw.polygon(
                [(cx, cy - chev), (cx + chev, cy + chev * 0.2), (cx - chev, cy + chev * 0.2)],
                fill=pal["glow"] + (200,),
                outline=pal["outline"] + (180,),
            )
        else:
            draw.ellipse(
                [cx - r, cy - r, cx + r, cy + r],
                fill=pal["primary"] + (220,),
                outline=pal["outline"] + (255,),
                width=max(1, int(w * 0.014)),
            )
            inner = r * 0.62
            draw.ellipse(
                [cx - inner, cy - inner, cx + inner, cy + inner],
                fill=lerp(pal["secondary"], pal["glow"], 0.4) + (180,),
                outline=pal["glow"] + (160,),
                width=max(1, int(w * 0.008)),
            )
            # Shield cross
            bar = r * 0.55
            bw = max(1, int(w * 0.018))
            draw.rectangle([cx - bw, cy - bar, cx + bw, cy + bar], fill=pal["glow"] + (200,))
            draw.rectangle([cx - bar, cy - bw, cx + bar, cy + bw], fill=pal["glow"] + (200,))

        for i in range(3):
            glow_r = r + i * w * 0.012
            alpha = int(55 * (1 - i / 3))
            draw.ellipse(
                [cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r],
                outline=pal["glow"] + (alpha,),
                width=max(1, int(w * 0.006)),
            )
        return add_noise_grain(apply_vignette(img, 0.22), 0.04, seed=seed)

    return render_at_scale(_draw, size, scale=scale)


def render_rich_warning_marker(design: Optional[Dict], size: Tuple[int, int], seed: int = 13) -> Image.Image:
    pal = _palette_from_design(
        design or {},
        {"primary": "#ffc800", "secondary": "#ff9000", "glow": "#ffe040", "outline": "#cc8000", "void": "#1a1000"},
    )
    scale = 8 if max(size) <= 64 else 4

    def _draw(big: Tuple[int, int]) -> Image.Image:
        w, h = big
        cx, cy = w / 2, h / 2
        img = radial_background(big, lerp(pal["secondary"], pal["primary"], 0.2), pal["void"])
        draw = ImageDraw.Draw(img, "RGBA")
        r = min(w, h) * 0.42
        for i in range(4, 0, -1):
            ring_r = r * (0.55 + i * 0.11)
            alpha = int(90 + i * 25)
            draw.ellipse(
                [cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r],
                outline=lerp(pal["outline"], pal["glow"], i / 5) + (alpha,),
                width=max(1, int(w * 0.01)),
            )
        # Triangle warning body
        tri_h = r * 1.05
        tri_w = r * 0.95
        tri = [(cx, cy - tri_h * 0.55), (cx + tri_w, cy + tri_h * 0.45), (cx - tri_w, cy + tri_h * 0.45)]
        draw.polygon(tri, fill=pal["primary"] + (210,), outline=pal["outline"] + (255,), width=max(1, int(w * 0.012)))
        # Exclamation
        ex_w = max(2, int(w * 0.035))
        ex_top = cy - tri_h * 0.2
        draw.rectangle([cx - ex_w, ex_top, cx + ex_w, cy + tri_h * 0.05], fill=pal["void"] + (255,))
        dot_r = ex_w * 1.2
        draw.ellipse([cx - dot_r, cy + tri_h * 0.15, cx + dot_r, cy + tri_h * 0.15 + dot_r * 2], fill=pal["void"] + (255,))
        return add_noise_grain(apply_vignette(img, 0.25), 0.05, seed=seed)

    return render_at_scale(_draw, size, scale=scale)


def render_rich_particle(
    kind: str,
    color: RGB,
    frame: int,
    total_frames: int,
    size: Tuple[int, int],
    seed: int = 0,
) -> Image.Image:
    """Rich spark / swirl / dot particle at native size with mild polish."""
    scale = 4
    big = (size[0] * scale, size[1] * scale)

    def _draw_spark(w: int, h: int) -> Image.Image:
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx, cy = w / 2, h / 2
        rotation = (frame / total_frames) * 2 * math.pi
        pulse = 0.65 + 0.35 * math.sin(frame * math.pi / max(1, total_frames / 2))
        glow_c = tuple(min(255, int(c * 1.25)) for c in color)
        for i in range(8):
            angle = rotation + i * math.pi / 4
            length = w * 0.22 * pulse
            for t in range(12):
                frac = t / 12
                x = cx + length * frac * math.cos(angle)
                y = cy + length * frac * math.sin(angle)
                alpha = int(255 * (1 - frac * 0.65))
                thick = max(1, int((1 - frac) * w * 0.04))
                draw.ellipse([x - thick, y - thick, x + thick, y + thick], fill=color + (alpha,))
        draw.ellipse([cx - w * 0.06, cy - w * 0.06, cx + w * 0.06, cy + w * 0.06], fill=glow_c + (255,))
        return img

    def _draw_swirl(w: int, h: int) -> Image.Image:
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx, cy = w / 2, h / 2
        rotation = (frame / total_frames) * 2 * math.pi
        for i in range(48):
            t = i / 48
            angle = rotation + t * 5 * math.pi
            radius = t * w * 0.28
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            alpha = int(255 * (1 - t * 0.75))
            thick = max(1, int((1 - t * 0.5) * w * 0.025))
            draw.ellipse([x - thick, y - thick, x + thick, y + thick], fill=color + (alpha,))
        draw.ellipse([cx - w * 0.05, cy - w * 0.05, cx + w * 0.05, cy + w * 0.05], fill=color + (255,))
        return img

    def _draw_dot(w: int, h: int) -> Image.Image:
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx, cy = w / 2, h / 2
        pulse = 0.45 + 0.55 * math.sin(frame * math.pi / max(1, total_frames / 2))
        r = w * 0.12 * pulse
        for i in range(4, 0, -1):
            gr = r + i * w * 0.02
            draw.ellipse([cx - gr, cy - gr, cx + gr, cy + gr], fill=color + (int(40 * (1 - i / 4)),))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color + (255,))
        return img

    drawers = {"spark": _draw_spark, "swirl": _draw_swirl, "dot": _draw_dot}
    fn = drawers.get(kind, _draw_dot)
    big_img = fn(big[0], big[1])
    return supersample_finalize(big_img, size, blur_radius=0.35, sharpen=1.2)


def render_rich_distortion_overlay(
    design: Optional[Dict],
    variant: int,
    size: Tuple[int, int],
    seed: int = 17,
) -> Image.Image:
    pal = _palette_from_design(
        design or {},
        {"primary": "#6496c8", "secondary": "#8cb4e0", "glow": "#a0c0f0", "void": "#081018"},
    )
    alpha_base = int((design or {}).get("colorScheme", {}).get("alpha", 80))
    scale = 4
    big = (size[0] * scale, size[1] * scale)
    w, h = big
    img = radial_background(big, lerp(pal["void"], pal["primary"], 0.15), (0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")
    rng = random.Random(seed + variant)
    for y in range(0, h, max(1, scale // 2)):
        wave1 = math.sin((y + variant * 5) * math.pi / (h * 0.12))
        wave2 = math.cos((y + variant * 3) * math.pi / (h * 0.2))
        cx = w / 2 + wave1 * w * 0.08 + wave2 * w * 0.04
        t = abs(math.sin(y * math.pi / h))
        color = lerp(pal["primary"], pal["glow"], t)
        alpha = int(alpha_base * (0.35 + 0.65 * t))
        x0 = int(cx - w * 0.02)
        x1 = int(cx + w * 0.02)
        draw.line([(x0, y), (x1, y)], fill=color + (alpha,), width=max(1, scale // 2))
        if rng.random() < 0.08:
            px = int(cx + rng.uniform(-w * 0.15, w * 0.15))
            draw.ellipse([px - 2, y - 2, px + 2, y + 2], fill=pal["glow"] + (int(alpha * 0.8),))
    img = add_noise_grain(img, 0.07, seed=seed + variant)
    return supersample_finalize(img, size, blur_radius=0.4, sharpen=1.15)
