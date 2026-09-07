#!/usr/bin/env python3
"""
Top-down organic hull sketches for Space Whale / Leviathan.

Goal: read as a *creature* (concept: lavender plated whale / Nova Drift serpent),
not a handful of giant hexagon primitives.
"""

from __future__ import annotations

import argparse
import math
import random
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFilter

Point = Tuple[float, float]

# Space Whale — concept lavender plates / violet fins / neon rim
VIOLET_DEEP = (70, 35, 130)
VIOLET_MID = (150, 100, 215)
LAVENDER = (225, 195, 255)
LAVENDER_DIM = (180, 140, 230)
NEON = (250, 225, 255)
FIN_DARK = (90, 45, 150)
STAR = (230, 235, 255)
CORE = (255, 245, 255)

# Leviathan — Nova Drift white / cyan
LEV_CORE = (245, 250, 255)
LEV_MID = (180, 220, 255)
LEV_CYAN = (90, 190, 255)
LEV_CYAN_DEEP = (40, 120, 200)
LEV_GLOW = (160, 230, 255)


def _poly(draw: ImageDraw.ImageDraw, pts: Sequence[Point], fill) -> None:
    draw.polygon([(float(x), float(y)) for x, y in pts], fill=fill)


def _ellipse(draw: ImageDraw.ImageDraw, cx: float, cy: float, rx: float, ry: float, fill) -> None:
    draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=fill)


def _lerp_rgb(a: Tuple[int, ...], b: Tuple[int, ...], t: float, alpha: int = 255) -> Tuple[int, int, int, int]:
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
        alpha,
    )


def _starfield(im: Image.Image, mask: Image.Image, rng: random.Random, density: float = 0.004) -> None:
    w, h = im.size
    px = im.load()
    m = mask.load()
    n = int(w * h * density)
    for _ in range(n):
        x = rng.randrange(w)
        y = rng.randrange(h)
        if m[x, y] < 40:
            continue
        bright = rng.choice([STAR, CORE, LAVENDER, NEON])
        a = 160 + rng.randrange(90)
        r, g, b = bright[:3]
        or_, og, ob, oa = px[x, y]
        t = a / 255.0 * 0.85
        px[x, y] = (
            min(255, int(or_ * (1 - t) + r * t)),
            min(255, int(og * (1 - t) + g * t)),
            min(255, int(ob * (1 - t) + b * t)),
            max(oa, min(255, a)),
        )


def _glow_pass(im: Image.Image, color: Tuple[int, int, int], radius: float, strength: float) -> Image.Image:
    alpha = im.split()[3]
    glow = alpha.filter(ImageFilter.GaussianBlur(radius=radius))
    glow_rgb = Image.new("RGBA", im.size, (*color, 0))
    glow_rgb.putalpha(glow.point(lambda v: int(v * strength)))
    return Image.alpha_composite(glow_rgb, im)


def _finish_whale(im: Image.Image, rng: random.Random, *, star_density: float, glow: float = 10.0) -> Image.Image:
    alpha = im.split()[3]
    _starfield(im, alpha, rng, density=star_density)
    soft = alpha.filter(ImageFilter.GaussianBlur(radius=max(1, im.size[0] // 220)))
    im.putalpha(ImageChops.lighter(soft, alpha.point(lambda v: int(v * 0.92))))
    return _glow_pass(im, NEON, glow, 0.48)


def _finish_lev(im: Image.Image, rng: random.Random, *, glow: float = 14.0) -> Image.Image:
    alpha = im.split()[3]
    _starfield(im, alpha, rng, density=0.0015)
    soft = alpha.filter(ImageFilter.GaussianBlur(radius=max(1, im.size[0] // 280)))
    im.putalpha(ImageChops.lighter(soft, alpha.point(lambda v: int(v * 0.95))))
    return _glow_pass(im, LEV_GLOW, glow, 0.58)


def _body_outline_pts(
    cx: float,
    cy: float,
    length: float,
    width: float,
    *,
    nose_sharp: float = 0.55,
) -> List[Point]:
    """Smooth elongated whale body outline, nose toward +X."""
    pts: List[Point] = []
    n = 64
    for i in range(n):
        ang = (i / n) * math.pi * 2.0 - math.pi
        u = math.cos(ang)
        v = math.sin(ang)
        if u > 0:
            x = cx + length * (0.06 + 0.42 * (u**nose_sharp))
            y_scale = width * (0.38 + 0.32 * (1.0 - u) ** 0.85)
        else:
            x = cx + length * (0.06 + 0.40 * u)
            y_scale = width * (0.36 + 0.20 * (1.0 + u))
        pts.append((x, cy + v * y_scale))
    return pts


def _fill_body_gradient(
    im: Image.Image,
    body: Sequence[Point],
    *,
    cx: float,
    cy: float,
    length: float,
    width: float,
) -> None:
    """Solid organic fill with nose-bright / edge-dark shading (fast layered ellipses)."""
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).polygon([(float(x), float(y)) for x, y in body], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=max(1, im.size[0] // 180)))

    # Solid opaque body first (never overwrite alpha with translucent fills)
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    _poly(ld, body, (*LAVENDER, 255))
    mid = [(cx + (x - cx) * 0.90, cy + (y - cy) * 0.90) for x, y in body]
    _poly(ld, mid, (*NEON, 255))
    _ellipse(ld, cx + length * 0.06, cy, length * 0.38, width * 0.28, (*LAVENDER, 255))
    _ellipse(ld, cx + length * 0.18, cy, length * 0.22, width * 0.18, (*CORE, 255))
    _ellipse(ld, cx - length * 0.10, cy, length * 0.20, width * 0.22, (*VIOLET_MID, 255))
    # Restore crisp body alpha from mask (ignore draw-order alpha damage)
    layer.putalpha(mask)
    im.alpha_composite(layer)


def _plate_seams(
    im: Image.Image,
    cx: float,
    cy: float,
    length: float,
    width: float,
    *,
    rows: int = 4,
    cols: int = 8,
) -> None:
    """Subtle plate seams via proper alpha composite (ImageDraw alpha overwrites)."""
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    seam = (*VIOLET_DEEP, 255)
    for row in range(1, rows):
        yy = cy + (row - rows * 0.5) * (width * 0.22)
        pts = []
        for i in range(12):
            t = i / 11.0
            x = cx - length * 0.35 + t * length * 0.70
            y = yy + math.sin(t * math.pi) * width * 0.03 * (1 if row % 2 else -1)
            pts.append((x, y))
        draw.line(pts, fill=seam, width=max(1, int(length * 0.01)))
    for col in range(1, cols):
        xx = cx - length * 0.32 + col * (length * 0.64 / cols)
        pts = []
        for i in range(10):
            t = i / 9.0
            y = cy - width * 0.38 + t * width * 0.76
            x = xx + math.sin(t * math.pi) * length * 0.015
            pts.append((x, y))
        draw.line(pts, fill=seam, width=max(1, int(length * 0.008)))
    # Keep seams faint
    r, g, b, a = overlay.split()
    overlay = Image.merge("RGBA", (r, g, b, a.point(lambda v: int(v * 0.22) if v else 0)))
    im.alpha_composite(overlay)


def _soft_scales(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    length: float,
    width: float,
    rng: random.Random,
    *,
    rows: int = 4,
    cols: int = 7,
) -> None:
    """Large overlapping soft ellipses — mosaic without sharp diamonds."""
    for row in range(rows):
        yy = cy + (row - (rows - 1) * 0.5) * (width * 0.26)
        offset = (row % 2) * 0.45
        for col in range(cols):
            xx = cx - length * 0.30 + (col + offset) * (length * 0.62 / max(1, cols - 1))
            nx = (xx - cx) / max(1e-3, length * 0.40)
            ny = (yy - cy) / max(1e-3, width * 0.40)
            if nx * nx + ny * ny * 1.25 > 1.05:
                continue
            rx = length * (0.09 + rng.random() * 0.02)
            ry = width * (0.11 + rng.random() * 0.02)
            t = 0.4 + 0.5 * ((col / max(1, cols - 1)) ** 0.7)
            fill = _lerp_rgb(VIOLET_MID, NEON, t, 255)
            # Soften via color only — keep opaque so JPG doesn't punch black holes
            _ellipse(draw, xx, yy, rx, ry, fill)


def draw_space_whale_head(
    size: int = 1024,
    seed: int = 42,
    pose: str = "idle",
) -> Image.Image:
    """Capital head: elongated plated whale + starfield pectorals (top-down, nose +X)."""
    rng = random.Random(seed)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = cy = size * 0.5
    s = float(size)

    ls = 0.80 if pose == "bodyCompress" else 1.0
    ws = 1.16 if pose == "bodyCompress" else 1.0
    maw_open = pose == "mawOpen"
    belly = pose == "bellyGlow"

    # Body dominates the frame (fins stay short so bbox isn't fin-only)
    length = s * 0.78 * ls
    width = s * 0.42 * ws
    bx = cx - s * 0.02

    # Compact luminous pectorals (concept starfield membranes, not black spikes)
    for sign in (-1.0, 1.0):
        fin = []
        for i in range(14):
            t = i / 13.0
            x = bx + length * (0.12 - t * 0.28)
            y = cy + sign * width * (0.35 + t * 0.55 + 0.08 * math.sin(t * math.pi))
            fin.append((x, y))
        for i in range(14):
            t = 1.0 - i / 13.0
            x = bx + length * (0.18 - t * 0.22)
            y = cy + sign * width * (0.28 + t * 0.40)
            fin.append((x, y))
        _poly(d, fin, (*VIOLET_MID, 255))
        _poly(d, [(bx + (x - bx) * 0.82, cy + (y - cy) * 0.82) for x, y in fin], (*LAVENDER, 255))

    body = _body_outline_pts(bx, cy, length, width, nose_sharp=0.58)
    _fill_body_gradient(im, body, cx=bx, cy=cy, length=length, width=width)
    d = ImageDraw.Draw(im)
    d = ImageDraw.Draw(im)
    hx = bx + length * 0.30
    # Nose highlight (opaque — no stacked scale ovals)
    _ellipse(d, hx + length * 0.02, cy, length * 0.10, width * 0.12, (*NEON, 255))

    if maw_open:
        gap = [
            (hx + length * 0.12, cy - width * 0.10),
            (hx + length * 0.20, cy - width * 0.03),
            (hx + length * 0.20, cy + width * 0.03),
            (hx + length * 0.12, cy + width * 0.10),
            (hx + length * 0.04, cy),
        ]
        _poly(d, gap, (18, 6, 36, 230))
        _ellipse(d, hx + length * 0.08, cy, length * 0.045, width * 0.07, (*CORE, 220))
    else:
        for dy in (-0.08, -0.03, 0.03, 0.08):
            _ellipse(
                d,
                hx + length * 0.13,
                cy + width * dy * 1.5,
                length * 0.025,
                width * 0.035,
                (*NEON, 200),
            )

    if belly:
        for t in range(7):
            _ellipse(
                d,
                bx + length * (0.20 - t * 0.06),
                cy,
                length * 0.04,
                width * 0.055,
                (*CORE, 190 - t * 16),
            )

    _ellipse(d, hx, cy - width * 0.18, length * 0.022, width * 0.035, (*CORE, 255))
    _ellipse(d, hx, cy + width * 0.18, length * 0.022, width * 0.035, (*CORE, 255))

    rim = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rim)
    big = [(bx + (x - bx) * 1.03, cy + (y - cy) * 1.03) for x, y in body]
    _poly(rd, big, (*NEON, 70))
    hole = Image.new("L", (size, size), 0)
    ImageDraw.Draw(hole).polygon([(float(x), float(y)) for x, y in body], fill=255)
    ra = rim.split()[3]
    rim.putalpha(ImageChops.subtract(ra, hole))
    im = Image.alpha_composite(im, rim)

    return _finish_whale(im, rng, star_density=0.008, glow=max(6.0, size / 120.0))


def draw_whale_segment(
    size: int = 768,
    seed: int = 7,
    pose: str = "idle",
) -> Image.Image:
    """Body plate for spine chain — rounded capsule with soft plating."""
    rng = random.Random(seed)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cx = cy = size * 0.5
    s = float(size)
    ls = 0.84 if pose == "bodyCompress" else 1.0
    ws = 1.18 if pose == "bodyCompress" else 1.0
    length = s * 0.70 * ls
    width = s * 0.48 * ws

    body = _body_outline_pts(cx, cy, length, width, nose_sharp=0.75)
    _fill_body_gradient(im, body, cx=cx, cy=cy, length=length, width=width)
    d = ImageDraw.Draw(im)
    _ellipse(d, cx + length * 0.22, cy, length * 0.12, width * 0.14, (*NEON, 255))

    if pose == "bellyGlow":
        _ellipse(d, cx, cy, length * 0.12, width * 0.10, (*CORE, 255))

    return _finish_whale(im, rng, star_density=0.010, glow=9.0)


def draw_whale_fluke(
    size: int = 768,
    seed: int = 99,
    pose: str = "idle",
) -> Image.Image:
    """Top-down fluke: peduncle + crescent lobes with starfield tip."""
    rng = random.Random(seed)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = cy = size * 0.5
    s = float(size)
    ls = 0.88 if pose == "bodyCompress" else 1.0
    ws = 1.12 if pose == "bodyCompress" else 1.0

    ped = _body_outline_pts(cx + s * 0.10 * ls, cy, s * 0.36 * ls, s * 0.22 * ws, nose_sharp=0.9)
    _fill_body_gradient(
        im, ped, cx=cx + s * 0.10 * ls, cy=cy, length=s * 0.36 * ls, width=s * 0.22 * ws
    )
    d = ImageDraw.Draw(im)

    for sign in (-1.0, 1.0):
        lobe = []
        for i in range(14):
            t = i / 13.0
            x = cx + s * (0.04 - t * 0.48) * ls
            y = cy + sign * s * (0.04 + t * 0.30 + 0.06 * math.sin(t * math.pi)) * ws
            lobe.append((x, y))
        for i in range(14):
            t = 1.0 - i / 13.0
            x = cx + s * (0.00 - t * 0.36) * ls
            y = cy + sign * s * (0.02 + t * 0.18) * ws
            lobe.append((x, y))
        _poly(d, lobe, (*VIOLET_MID, 255))
        _poly(d, [(cx + (x - cx) * 0.85, cy + (y - cy) * 0.85) for x, y in lobe], (*LAVENDER, 255))

    notch = [
        (cx - s * 0.05 * ls, cy),
        (cx - s * 0.32 * ls, cy - s * 0.06 * ws),
        (cx - s * 0.40 * ls, cy),
        (cx - s * 0.32 * ls, cy + s * 0.06 * ws),
    ]
    _poly(d, notch, (*VIOLET_DEEP, 255))

    return _finish_whale(im, rng, star_density=0.014, glow=12.0)


def draw_whale_drone(
    size: int = 512,
    seed: int = 3,
    pose: str = "idle",
) -> Image.Image:
    """Mini escort — same plated whale language, smaller."""
    rng = random.Random(seed)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = cy = size * 0.5
    s = float(size)
    ls = 0.88 if pose == "bodyCompress" else 1.0
    ws = 1.12 if pose == "bodyCompress" else 1.0

    for sign in (-1.0, 1.0):
        fin = []
        for i in range(10):
            t = i / 9.0
            x = cx + s * (0.10 - t * 0.28) * ls
            y = cy + sign * s * (0.04 + t * 0.26) * ws
            fin.append((x, y))
        for i in range(10):
            t = 1.0 - i / 9.0
            x = cx + s * (0.12 - t * 0.20) * ls
            y = cy + sign * s * (0.03 + t * 0.14) * ws
            fin.append((x, y))
        _poly(d, fin, (*VIOLET_MID, 255))

    body = _body_outline_pts(cx, cy, s * 0.55 * ls, s * 0.28 * ws, nose_sharp=0.7)
    _fill_body_gradient(im, body, cx=cx, cy=cy, length=s * 0.55 * ls, width=s * 0.28 * ws)
    d = ImageDraw.Draw(im)
    _ellipse(d, cx + s * 0.12 * ls, cy - s * 0.04, s * 0.025, s * 0.018, (*CORE, 255))
    _ellipse(d, cx + s * 0.12 * ls, cy + s * 0.04, s * 0.025, s * 0.018, (*CORE, 255))
    return _finish_whale(im, rng, star_density=0.009, glow=8.0)


def _lev_spike(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    *,
    length: float,
    sign: float,
    aft: float = 0.35,
) -> None:
    tip_x = cx - length * aft
    tip_y = cy + sign * length
    base_fore = (cx + length * 0.18, cy + sign * length * 0.06)
    base_aft = (cx - length * 0.22, cy + sign * length * 0.10)
    _poly(draw, [base_fore, (tip_x, tip_y), base_aft], (*LEV_CYAN, 235))
    mid = (
        (base_fore[0] * 0.35 + tip_x * 0.65, base_fore[1] * 0.35 + tip_y * 0.65),
        (tip_x, tip_y),
        (base_aft[0] * 0.35 + tip_x * 0.65, base_aft[1] * 0.35 + tip_y * 0.65),
    )
    _poly(draw, mid, (*LEV_MID, 210))


def _lev_vertebra(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    length: float,
    width: float,
    *,
    with_spikes: bool = True,
    spike_scale: float = 1.0,
) -> None:
    """Bright rounded segment with soft inner hex hint (concept vertebra)."""
    if with_spikes:
        _lev_spike(draw, cx, cy, length=width * 1.15 * spike_scale, sign=-1.0, aft=0.38)
        _lev_spike(draw, cx, cy, length=width * 1.15 * spike_scale, sign=1.0, aft=0.38)

    # Soft outer capsule
    _ellipse(draw, cx, cy, length * 0.52, width * 0.52, (*LEV_CYAN, 230))
    _ellipse(draw, cx, cy, length * 0.42, width * 0.42, (*LEV_MID, 245))
    _ellipse(draw, cx, cy, length * 0.30, width * 0.30, (*LEV_CORE, 255))

    # Subtle inner hex ring (detail, not the whole silhouette)
    hl, hw = length * 0.28, width * 0.28
    ring = [
        (cx + hl * 0.9, cy),
        (cx + hl * 0.4, cy - hw),
        (cx - hl * 0.4, cy - hw),
        (cx - hl * 0.9, cy),
        (cx - hl * 0.4, cy + hw),
        (cx + hl * 0.4, cy + hw),
    ]
    draw.line(ring + [ring[0]], fill=(*LEV_CYAN_DEEP, 160), width=max(1, int(length * 0.04)))


def draw_leviathan(
    size: int = 1024,
    seed: int = 11,
    pose: str = "idle",
) -> Image.Image:
    """Nova Drift capital: luminous head + cyan crystal fins + many small vertebrae."""
    rng = random.Random(seed)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = cy = size * 0.5
    s = float(size)
    ls = 0.84 if pose == "bodyCompress" else 1.0
    ws = 1.12 if pose == "bodyCompress" else 1.0
    maw_open = pose == "mawOpen"
    belly = pose == "bellyGlow"

    # Large crystalline head fins (aft of head, under spine)
    for sign in (-1.0, 1.0):
        shard = [
            (cx + s * 0.10 * ls, cy + sign * s * 0.04),
            (cx - s * 0.02 * ls, cy + sign * s * 0.10),
            (cx - s * 0.18 * ls, cy + sign * s * 0.42 * ws),
            (cx - s * 0.02 * ls, cy + sign * s * 0.32 * ws),
            (cx + s * 0.16 * ls, cy + sign * s * 0.14),
        ]
        _poly(d, shard, (*LEV_CYAN_DEEP, 210))
        _poly(d, [(cx + (x - cx) * 0.80, cy + (y - cy) * 0.80) for x, y in shard], (*LEV_CYAN, 170))
        # Extra long tip
        tip = [
            (cx - s * 0.10 * ls, cy + sign * s * 0.28 * ws),
            (cx - s * 0.28 * ls, cy + sign * s * 0.48 * ws),
            (cx - s * 0.08 * ls, cy + sign * s * 0.36 * ws),
        ]
        _poly(d, tip, (*LEV_MID, 200))

    # Spine chain of many small vertebrae trailing aft (−X)
    n_seg = 7 if pose == "bodyCompress" else 9
    for i in range(n_seg):
        t = (i + 0.5) / n_seg
        # Slight serpentine offset
        wave = math.sin(t * math.pi * 1.6) * s * 0.04 * ws
        x = cx - s * (0.02 + t * 0.38) * ls
        sc = 1.0 - t * 0.35
        _lev_vertebra(
            d,
            x,
            cy + wave,
            s * 0.10 * sc * ls,
            s * 0.09 * sc * ws,
            with_spikes=True,
            spike_scale=0.85 + 0.15 * (1.0 - t),
        )

    # Head mass (forward) — rounded luminous cluster, not a lone hex
    hx = cx + s * 0.22 * ls
    if maw_open:
        head = [
            (hx + s * 0.18 * ls, cy - s * 0.08 * ws),
            (hx + s * 0.06 * ls, cy - s * 0.14 * ws),
            (hx - s * 0.08 * ls, cy - s * 0.08 * ws),
            (hx - s * 0.12 * ls, cy),
            (hx - s * 0.08 * ls, cy + s * 0.08 * ws),
            (hx + s * 0.06 * ls, cy + s * 0.14 * ws),
            (hx + s * 0.18 * ls, cy + s * 0.08 * ws),
            (hx + s * 0.10 * ls, cy + s * 0.025),
            (hx + s * 0.10 * ls, cy - s * 0.025),
        ]
        _poly(d, head, (*LEV_CYAN, 250))
        _ellipse(d, hx + s * 0.06 * ls, cy, s * 0.05, s * 0.035, (20, 40, 80, 230))
    else:
        _ellipse(d, hx, cy, s * 0.16 * ls, s * 0.12 * ws, (*LEV_CYAN, 250))
        _ellipse(d, hx + s * 0.02 * ls, cy, s * 0.12 * ls, s * 0.09 * ws, (*LEV_CORE, 255))
        _ellipse(d, hx + s * 0.04 * ls, cy, s * 0.07 * ls, s * 0.055 * ws, (255, 255, 255, 255))

    # Head side blades
    for sign in (-1.0, 1.0):
        blade = [
            (hx + s * 0.02 * ls, cy + sign * s * 0.05),
            (hx - s * 0.04 * ls, cy + sign * s * 0.08),
            (hx - s * 0.02 * ls, cy + sign * s * 0.22 * ws),
            (hx + s * 0.10 * ls, cy + sign * s * 0.10),
        ]
        _poly(d, blade, (*LEV_CYAN, 235))

    if belly:
        for t in range(6):
            _ellipse(d, cx - s * t * 0.05 * ls, cy, s * 0.03, s * 0.014, (255, 255, 255, 220 - t * 22))

    _ellipse(d, hx + s * 0.06 * ls, cy - s * 0.045 * ws, s * 0.018, s * 0.012, (*LEV_CYAN, 255))
    _ellipse(d, hx + s * 0.06 * ls, cy + s * 0.045 * ws, s * 0.018, s * 0.012, (*LEV_CYAN, 255))

    return _finish_lev(im, rng, glow=max(12.0, size / 65.0))


def draw_leviathan_segment(
    size: int = 640,
    seed: int = 13,
    pose: str = "idle",
) -> Image.Image:
    """Single Nova Drift vertebra: soft white core + paired aft spikes."""
    rng = random.Random(seed)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = cy = size * 0.5
    ls = 0.88 if pose == "bodyCompress" else 1.0
    ws = 1.18 if pose == "bodyCompress" else 1.0

    _lev_vertebra(
        d,
        cx,
        cy,
        size * 0.55 * ls,
        size * 0.42 * ws,
        with_spikes=True,
        spike_scale=1.05,
    )
    if pose == "bellyGlow":
        _ellipse(d, cx, cy, size * 0.10, size * 0.05, (255, 255, 255, 230))

    return _finish_lev(im, rng, glow=12.0)


SKETCHERS = {
    "scSpaceWhale": ("space_whale", draw_space_whale_head, 1024),
    "scSpaceWhaleSegment": ("space_whale_segment", draw_whale_segment, 768),
    "scSpaceWhaleFluke": ("space_whale_fluke", draw_whale_fluke, 768),
    "scSpaceWhaleDrone": ("space_whale_drone", draw_whale_drone, 512),
    "scLeviathanBase": ("leviathan", draw_leviathan, 1024),
    "scLeviathanSegment": ("leviathan_segment", draw_leviathan_segment, 640),
}

POSE_BY_ROLE = {
    "scSpaceWhale": ["idle", "mawOpen", "bodyCompress", "bellyGlow"],
    "scSpaceWhaleSegment": ["idle", "bodyCompress"],
    "scSpaceWhaleFluke": ["idle", "bodyCompress"],
    "scSpaceWhaleDrone": ["idle", "bodyCompress"],
    "scLeviathanBase": ["idle", "mawOpen", "bodyCompress", "bellyGlow"],
    "scLeviathanSegment": ["idle", "bodyCompress"],
}


def render_part(ship_id: str, pose: str = "idle", size: int | None = None) -> Image.Image:
    if ship_id not in SKETCHERS:
        raise KeyError(f"Unknown ship id: {ship_id}")
    _stem, fn, default_size = SKETCHERS[ship_id]
    return fn(size or default_size, pose=pose)


def write_sketches(
    out_dir: Path,
    ship_ids: Iterable[str] | None = None,
    *,
    poses: bool = False,
) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    wanted = set(ship_ids) if ship_ids else set(SKETCHERS.keys())
    written = {}
    for sid, (stem, fn, size) in SKETCHERS.items():
        if sid not in wanted:
            continue
        pose_list = POSE_BY_ROLE.get(sid, ["idle"]) if poses else ["idle"]
        for pose in pose_list:
            name = f"{stem}_topdown.png" if pose == "idle" else f"{stem}_{pose}_topdown.png"
            path = out_dir / name
            fn(size, pose=pose).save(path, "PNG")
            written[f"{sid}:{pose}"] = str(path)
            print(f"[sketch] {sid}/{pose} -> {path}")
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description="Concept-style Space Whale / Leviathan top-down sketches")
    ap.add_argument("--out-dir", default=r"C:\Output\SpaceWhale120Facings\Sketches")
    ap.add_argument("--ship-id", action="append", default=[])
    ap.add_argument("--poses", action="store_true", help="Also write pose variants")
    args = ap.parse_args()
    write_sketches(Path(args.out_dir), args.ship_id or None, poses=args.poses)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
