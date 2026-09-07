#!/usr/bin/env python3
"""Rich spec-driven procedural rendering for Elin assets."""

from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFilter

from elin_quality import finalize_rgba, finalize_texture

Color = Tuple[int, int, int]
Palette = List[Color]

DEFAULT_PALETTE = [
    (18, 28, 48),
    (36, 58, 92),
    (74, 120, 168),
    (120, 176, 220),
    (200, 228, 248),
    (255, 255, 255),
]


def hex_to_rgb(hex_color: str) -> Color:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def lerp(c1: Color, c2: Color, t: float) -> Color:
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))  # type: ignore[return-value]


def parse_palette(spec: Dict[str, Any]) -> Palette:
    raw = spec.get("palette") or spec.get("colors") or []
    pal: Palette = []
    for c in raw:
        if isinstance(c, str):
            pal.append(hex_to_rgb(c))
        elif isinstance(c, (list, tuple)) and len(c) >= 3:
            pal.append((int(c[0]), int(c[1]), int(c[2])))
    if len(pal) < 2:
        pal = list(DEFAULT_PALETTE)
    while len(pal) < 6:
        pal.append(lerp(pal[-1], (255, 255, 255), 0.35))
    return pal


def _radial_bg(size: Tuple[int, int], inner: Color, outer: Color) -> Image.Image:
    w, h = size
    img = Image.new("RGBA", size)
    px = img.load()
    cx, cy = w / 2, h / 2
    maxd = math.hypot(cx, cy) or 1.0
    for y in range(h):
        for x in range(w):
            t = min(1.0, math.hypot(x - cx, y - cy) / maxd)
            r, g, b = lerp(inner, outer, t ** 1.25)
            px[x, y] = (r, g, b, 255)
    return img


def _add_noise(img: Image.Image, strength: float = 0.12, seed: int = 0) -> Image.Image:
    rng = random.Random(seed)
    w, h = img.size
    noise = Image.new("RGBA", (w, h))
    npx = noise.load()
    for y in range(h):
        for x in range(w):
            n = int((rng.random() - 0.5) * strength * 255)
            npx[x, y] = (n, n, n, 40)
    return Image.alpha_composite(img.convert("RGBA"), noise)


def _vignette(img: Image.Image, strength: float = 0.35) -> Image.Image:
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = overlay.load()
    cx, cy = w / 2, h / 2
    maxd = math.hypot(cx, cy) or 1.0
    for y in range(h):
        for x in range(w):
            t = min(1.0, math.hypot(x - cx, y - cy) / maxd)
            alpha = int(255 * strength * (t ** 1.8))
            px[x, y] = (0, 0, 0, alpha)
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def _pressure_rings(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    radius: float,
    color: Color,
    count: int = 4,
) -> None:
    for i in range(count, 0, -1):
        r = radius * (0.32 + i * 0.17)
        alpha = 55 + i * 18
        width = max(1, int(radius * 0.05))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color + (alpha,), width=width)


def _draw_gem(
    draw: ImageDraw.ImageDraw, cx: float, cy: float, radius: float, pal: Palette
) -> None:
    deep, mid, accent, hi, rim = pal[1], pal[2], pal[3], pal[4], pal[5]
    _pressure_rings(draw, cx, cy, radius * 1.05, accent, count=3)
    pts = [
        (cx, cy - radius * 0.9),
        (cx + radius * 0.55, cy - radius * 0.15),
        (cx + radius * 0.45, cy + radius * 0.75),
        (cx - radius * 0.45, cy + radius * 0.75),
        (cx - radius * 0.55, cy - radius * 0.15),
    ]
    draw.polygon(pts, fill=mid + (255,))
    draw.polygon(pts, outline=deep + (220,), width=max(1, int(radius * 0.08)))
    facet = [
        (cx, cy - radius * 0.55),
        (cx + radius * 0.25, cy - radius * 0.05),
        (cx, cy + radius * 0.35),
        (cx - radius * 0.25, cy - radius * 0.05),
    ]
    draw.polygon(facet, fill=hi + (190,))
    draw.line(
        [(cx - radius * 0.2, cy - radius * 0.35), (cx + radius * 0.15, cy + radius * 0.2)],
        fill=rim + (210,),
        width=max(1, int(radius * 0.1)),
    )


def _draw_flame(
    draw: ImageDraw.ImageDraw, cx: float, cy: float, radius: float, pal: Palette
) -> None:
    deep, mid, accent, hi = pal[1], pal[2], pal[3], pal[4]
    _pressure_rings(draw, cx, cy + radius * 0.1, radius, accent, count=2)
    body = [
        (cx, cy - radius),
        (cx + radius * 0.55, cy + radius * 0.35),
        (cx, cy + radius * 0.65),
        (cx - radius * 0.55, cy + radius * 0.35),
    ]
    draw.polygon(body, fill=mid + (255,))
    draw.polygon(body, outline=deep + (200,), width=max(1, int(radius * 0.07)))
    core = [
        (cx, cy - radius * 0.55),
        (cx + radius * 0.22, cy + radius * 0.05),
        (cx, cy + radius * 0.35),
        (cx - radius * 0.22, cy + radius * 0.05),
    ]
    draw.polygon(core, fill=hi + (220,))
    draw.ellipse(
        [cx - radius * 0.12, cy - radius * 0.35, cx + radius * 0.05, cy - radius * 0.12],
        fill=(255, 255, 255, 180),
    )


def _draw_leaf(
    draw: ImageDraw.ImageDraw, cx: float, cy: float, radius: float, pal: Palette
) -> None:
    deep, mid, accent, hi = pal[1], pal[2], pal[3], pal[4]
    pts = []
    for angle in range(0, 360, 12):
        r = radius * (0.55 + 0.45 * abs(math.sin(math.radians(angle * 2))))
        x = cx + r * math.cos(math.radians(angle - 90))
        y = cy + r * 1.2 * math.sin(math.radians(angle - 90))
        pts.append((x, y))
    draw.polygon(pts, fill=mid + (255,))
    draw.polygon(pts, outline=deep + (210,), width=max(1, int(radius * 0.06)))
    draw.line(
        [(cx, cy - radius * 0.9), (cx, cy + radius * 0.85)],
        fill=accent + (200,),
        width=max(1, int(radius * 0.08)),
    )
    draw.line(
        [(cx - radius * 0.35, cy - radius * 0.1), (cx + radius * 0.4, cy + radius * 0.25)],
        fill=hi + (160,),
        width=max(1, int(radius * 0.05)),
    )


def _draw_star(
    draw: ImageDraw.ImageDraw, cx: float, cy: float, radius: float, pal: Palette
) -> None:
    deep, mid, accent, hi = pal[1], pal[2], pal[3], pal[4]
    _pressure_rings(draw, cx, cy, radius * 1.1, accent, count=3)
    pts = []
    for i in range(10):
        angle = math.radians(i * 36 - 90)
        r = radius if i % 2 == 0 else radius * 0.42
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(pts, fill=mid + (255,))
    draw.polygon(pts, outline=deep + (230,), width=max(1, int(radius * 0.07)))
    draw.line(
        [(cx - radius * 0.25, cy - radius * 0.15), (cx + radius * 0.3, cy + radius * 0.2)],
        fill=hi + (200,),
        width=max(1, int(radius * 0.1)),
    )


def _draw_rune(
    draw: ImageDraw.ImageDraw, cx: float, cy: float, radius: float, pal: Palette
) -> None:
    deep, mid, accent, hi = pal[1], pal[2], pal[3], pal[4]
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        fill=mid + (40,),
        outline=accent + (220,),
        width=max(1, int(radius * 0.1)),
    )
    w = max(2, int(radius * 0.12))
    draw.line([(cx, cy - radius * 0.65), (cx, cy + radius * 0.55)], fill=hi + (240,), width=w)
    draw.line([(cx - radius * 0.45, cy), (cx + radius * 0.45, cy)], fill=accent + (220,), width=w)
    draw.line([(cx - radius * 0.3, cy - radius * 0.35), (cx, cy)], fill=deep + (200,), width=max(1, w - 1))
    draw.line([(cx, cy), (cx + radius * 0.35, cy + radius * 0.35)], fill=deep + (200,), width=max(1, w - 1))


def _draw_orb(
    draw: ImageDraw.ImageDraw, cx: float, cy: float, radius: float, pal: Palette
) -> None:
    deep, mid, accent, hi, rim = pal[1], pal[2], pal[3], pal[4], pal[5]
    _pressure_rings(draw, cx, cy, radius * 1.15, accent, count=4)
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=mid + (255,))
    draw.ellipse(
        [cx - radius * 0.75, cy - radius * 0.75, cx + radius * 0.75, cy + radius * 0.75],
        fill=accent + (120,),
    )
    draw.ellipse(
        [cx - radius * 0.35, cy - radius * 0.4, cx - radius * 0.05, cy - radius * 0.1],
        fill=rim + (230,),
    )
    draw.arc(
        [cx - radius * 0.9, cy - radius * 0.9, cx + radius * 0.9, cy + radius * 0.9],
        start=200,
        end=340,
        fill=hi + (180,),
        width=max(1, int(radius * 0.08)),
    )


def _motif_key(spec: Dict[str, Any]) -> str:
    text = " ".join(
        str(spec.get(k, ""))
        for k in ("motif", "shape", "pattern", "theme", "style", "element")
    ).lower()
    if any(k in text for k in ("leaf", "nature", "vine", "organic")):
        return "leaf"
    if any(k in text for k in ("flame", "fire", "ember", "burn")):
        return "flame"
    if any(k in text for k in ("gem", "crystal", "shard", "diamond")):
        return "gem"
    if any(k in text for k in ("rune", "sigil", "symbol", "glyph")):
        return "rune"
    if any(k in text for k in ("orb", "ball", "sphere")):
        return "orb"
    if any(k in text for k in ("star", "burst", "spark")):
        return "star"
    if "geometric" in text:
        return "gem"
    return "rune"


def _draw_motif(draw: ImageDraw.ImageDraw, cx: float, cy: float, radius: float, pal: Palette, spec: Dict[str, Any]) -> None:
    key = _motif_key(spec)
    if key == "leaf":
        _draw_leaf(draw, cx, cy, radius, pal)
    elif key == "flame":
        _draw_flame(draw, cx, cy, radius, pal)
    elif key == "gem":
        _draw_gem(draw, cx, cy, radius, pal)
    elif key == "star":
        _draw_star(draw, cx, cy, radius, pal)
    elif key == "orb":
        _draw_orb(draw, cx, cy, radius, pal)
    else:
        _draw_rune(draw, cx, cy, radius, pal)


def _apply_rim_light(img: Image.Image, color: Color, intensity: float = 0.28) -> Image.Image:
    w, h = img.size
    rim = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(rim)
    cx, cy = w / 2, h / 2
    for angle in range(0, 360, 8):
        x = cx + (w * 0.42) * math.cos(math.radians(angle))
        y = cy + (h * 0.42) * math.sin(math.radians(angle))
        draw.ellipse([x - 2, y - 2, x + 2, y + 2], fill=color + (int(255 * intensity),))
    rim = rim.filter(ImageFilter.GaussianBlur(radius=max(2, w // 32)))
    return Image.alpha_composite(img.convert("RGBA"), rim)


def _supersample_downscale(img: Image.Image, target_size: int, blur_radius: float) -> Image.Image:
    factor = 8 if target_size <= 64 else 4
    big = max(target_size * factor, target_size)
    hi = img.resize((big, big), Image.Resampling.LANCZOS)
    hi = hi.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    return hi.resize((target_size, target_size), Image.Resampling.LANCZOS)


def render_rich_icon(size: int, spec: Dict[str, Any], seed: int = 0) -> Image.Image:
    pal = parse_palette(spec)
    rng = random.Random(seed)
    hi_size = size * (8 if size <= 64 else 4)
    blur = (8 if size <= 64 else 4) * 0.22

    img = _radial_bg((hi_size, hi_size), lerp(pal[2], pal[1], 0.4), pal[0])
    img = _add_noise(img, strength=0.08 + rng.random() * 0.06, seed=seed + 1)
    draw = ImageDraw.Draw(img, "RGBA")
    cx = hi_size / 2 + rng.uniform(-hi_size * 0.02, hi_size * 0.02)
    cy = hi_size / 2 + hi_size * 0.03
    _draw_motif(draw, cx, cy, hi_size * 0.34, pal, spec)

    effects = [str(e).lower() for e in spec.get("effects", [])]
    effects_text = " ".join(effects + [str(spec.get("lighting", "")).lower()])
    if any(k in effects_text for k in ("rim", "rim-light", "rim light")):
        img = _apply_rim_light(img, pal[4])

    img = _vignette(img, strength=0.22)
    img = img.filter(ImageFilter.GaussianBlur(radius=blur))
    img = img.resize((size, size), Image.Resampling.LANCZOS)

    style = str(spec.get("style", "")).lower()
    if style == "pixel-art":
        small = img.resize((max(1, size // 4), max(1, size // 4)), Image.Resampling.NEAREST)
        img = small.resize((size, size), Image.Resampling.NEAREST)
    else:
        img = finalize_rgba(img)

    return img


def _texture_cells(size: int, pal: Palette, pattern: str, seed: int) -> Image.Image:
    rng = random.Random(seed)
    img = Image.new("RGB", (size, size), pal[0])
    px = img.load()
    cell = max(4, size // 16)
    for y in range(0, size, cell):
        for x in range(0, size, cell):
            nx = (x + seed * 13) / size
            ny = (y + seed * 17) / size
            if "organic" in pattern:
                t = 0.5 + 0.5 * math.sin(nx * 9 + ny * 7) + rng.random() * 0.15
            elif "geometric" in pattern:
                t = ((x // cell) + (y // cell)) % 4 / 3.0
            else:
                t = nx * 0.6 + ny * 0.4 + rng.random() * 0.2
            t = max(0.0, min(1.0, t))
            idx = int(t * (len(pal) - 1))
            c1, c2 = pal[idx], pal[min(idx + 1, len(pal) - 1)]
            local = t * (len(pal) - 1) - idx
            color = lerp(c1, c2, local)
            for yy in range(y, min(y + cell, size)):
                for xx in range(x, min(x + cell, size)):
                    n = int((rng.random() - 0.5) * 18)
                    px[xx, yy] = tuple(max(0, min(255, c + n)) for c in color)
    return img


def render_rich_texture(size: int, spec: Dict[str, Any], seed: int = 0) -> Image.Image:
    pal = parse_palette(spec)
    pattern = str(spec.get("pattern", "noise")).lower()
    rng = random.Random(seed)

    base = _texture_cells(size, pal, pattern, seed)
    rgba = base.convert("RGBA")
    rgba = _add_noise(rgba, strength=0.06 + rng.random() * 0.05, seed=seed + 3)

    accent = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(accent)
    for _ in range(12 + seed % 6):
        x = rng.randint(0, size)
        y = rng.randint(0, size)
        r = rng.randint(max(2, size // 64), max(4, size // 24))
        c = pal[rng.randint(2, min(4, len(pal) - 1))]
        draw.ellipse([x - r, y - r, x + r, y + r], fill=c + (35,))
    rgba = Image.alpha_composite(rgba, accent.filter(ImageFilter.GaussianBlur(radius=max(1, size // 128))))

    style = str(spec.get("style", "")).lower()
    out = rgba.convert("RGB")
    if style == "pixel-art":
        small = out.resize((max(1, size // 2), max(1, size // 2)), Image.Resampling.NEAREST)
        out = small.resize((size, size), Image.Resampling.NEAREST)
    else:
        out = finalize_texture(out.filter(ImageFilter.SMOOTH_MORE))
    return out


def render_fx_frame(
    size: int,
    frame: int,
    frames: int,
    spec: Dict[str, Any],
    seed: int = 0,
) -> Image.Image:
    pal = parse_palette(spec)
    progress = frame / max(1, frames - 1)
    hi = size * 4
    img = Image.new("RGBA", (hi, hi), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = cy = hi / 2
    motion = str(spec.get("motion", "expanding")).lower()

    if "rotat" in motion:
        for i in range(6):
            angle = math.radians(progress * 360 + i * 60)
            x = cx + hi * 0.28 * math.cos(angle)
            y = cy + hi * 0.28 * math.sin(angle)
            r = hi * 0.08
            c = pal[2 + (i % 3)]
            draw.ellipse([x - r, y - r, x + r, y + r], fill=c + (220,))
    else:
        for ring in range(3, 0, -1):
            radius = hi * (0.12 + progress * 0.35) * ring * 0.45
            alpha = int(180 * (1 - progress * 0.6) / ring)
            draw.ellipse(
                [cx - radius, cy - radius, cx + radius, cy + radius],
                outline=pal[3] + (alpha,),
                width=max(1, int(hi * 0.02)),
            )
        _draw_motif(draw, cx, cy, hi * (0.18 + progress * 0.08), pal, spec)

    img = img.filter(ImageFilter.GaussianBlur(radius=hi * 0.04))
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    return finalize_rgba(img)


def render_projectile_frame(
    size: int,
    frame: int,
    frames: int,
    spec: Dict[str, Any],
    seed: int = 0,
) -> Image.Image:
    pal = parse_palette(spec)
    hi = size * 4
    img = Image.new("RGBA", (hi, hi), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = cy = hi / 2
    offset = (frame - (frames - 1) / 2) * (hi * 0.04)
    motif = _motif_key(spec)
    if motif in ("gem", "shard"):
        _draw_gem(draw, cx + offset, cy, hi * 0.28, pal)
    elif motif == "orb":
        _draw_orb(draw, cx + offset, cy, hi * 0.26, pal)
    else:
        _draw_flame(draw, cx + offset, cy, hi * 0.3, pal)
    img = img.filter(ImageFilter.GaussianBlur(radius=hi * 0.03))
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    return finalize_rgba(img)
