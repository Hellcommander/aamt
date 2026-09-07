#!/usr/bin/env python3
"""
Mathematical 16x24 truecolor tiles for Improved Space-Time Vortex.

Vanilla spacetime_vortex is a crisp hooked spiral at 16x24. Draw at native
resolution with hard pixels (no blur / LANCZOS) so map tiles stay readable.
"""

from __future__ import annotations

import argparse
import math
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw

QUD_TILE = (16, 24)
RGB = Tuple[int, int, int]
RGBA = Tuple[int, int, int, int]


def _rgb(hex_color: str, default: RGB) -> RGB:
    h = (hex_color or "").strip().lstrip("#")
    if len(h) != 6:
        return default
    try:
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore
    except ValueError:
        return default


def _put(px, x: int, y: int, w: int, h: int, color: RGBA) -> None:
    if 0 <= x < w and 0 <= y < h:
        r, g, b, a = color
        if a <= 0:
            return
        or_, og, ob, oa = px[x, y]
        if oa == 0:
            px[x, y] = color
            return
        # Overwrite if incoming is more opaque / brighter body
        if a >= oa:
            px[x, y] = color


def _disk(px, cx: int, cy: int, r: int, color: RGBA, w: int, h: int) -> None:
    rr = max(0, r)
    for dy in range(-rr, rr + 1):
        for dx in range(-rr, rr + 1):
            if dx * dx + dy * dy <= rr * rr:
                _put(px, cx + dx, cy + dy, w, h, color)


# Opaque pixels from vanilla spacetime_vortex (dual-tone: white=body, black=detail).
# Truecolor tiles paint both as visible silhouette.
VANILLA_BODY_XY = [  # white channel
    (7, 7), (8, 7), (9, 7), (10, 7), (11, 7),
    (6, 8), (7, 8), (8, 8), (9, 8), (10, 8), (11, 8), (12, 8),
    (5, 9), (6, 9), (11, 9), (12, 9), (13, 9),
    (5, 10), (12, 10), (13, 10),
    (5, 11), (12, 11), (13, 11),
    (5, 12), (12, 12), (13, 12),
    (6, 13), (12, 13), (13, 13),
    (12, 14), (13, 14),
    (12, 15),
    (11, 16), (12, 16),
    (11, 17),
    (10, 18),
    (9, 19),
    (8, 20),
    (6, 21),
    (3, 22),
]
VANILLA_DETAIL_XY = [  # black channel (trail / inner hook)
    (12, 1), (9, 2), (7, 3), (6, 4), (5, 5), (4, 6),
    (3, 7), (4, 7), (3, 8),
    (2, 9), (3, 9),
    (2, 10), (3, 10), (9, 10),
    (2, 11), (3, 11), (10, 11),
    (2, 12), (3, 12), (10, 12),
    (2, 13), (3, 13), (10, 13),
    (2, 14), (3, 14), (4, 14), (9, 14), (10, 14),
    (3, 15), (4, 15), (5, 15), (6, 15), (7, 15), (8, 15), (9, 15),
    (4, 16), (5, 16), (6, 16), (7, 16), (8, 16),
]


def paint_vanilla_hook(
    img: Image.Image,
    *,
    color: RGB,
    rotation: float = 0.0,
    detail: Optional[RGB] = None,
    glow: Optional[RGB] = None,
    mirror: bool = False,
    dual_tone: bool = False,
) -> Image.Image:
    """Stamp vanilla hooked-spiral pixels (body+detail), optionally rotated.

    Default is truecolor (needs modconfig.json shadermode=1 on the mod).
    dual_tone=True writes white body + black detail for 3-color shader mods.
    """
    w, h = img.size
    px = img.load()
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    cos_a, sin_a = math.cos(rotation), math.sin(rotation)
    if dual_tone:
        body_c: RGB = (255, 255, 255)
        detail_c: RGB = (0, 0, 0)
        glow = None
    else:
        body_c = color
        detail_c = detail or tuple(max(0, c // 2) for c in color)  # type: ignore

    def stamp(x0: int, y0: int, col: RGB) -> None:
        x1 = (w - 1 - x0) if mirror else x0
        dx, dy = x1 - cx, y0 - cy
        x = int(round(cx + dx * cos_a - dy * sin_a))
        y = int(round(cy + dx * sin_a + dy * cos_a))
        if glow:
            for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                _put(px, x + ox, y + oy, w, h, (*glow, 35))
        _put(px, x, y, w, h, (*col, 255))

    for x0, y0 in VANILLA_DETAIL_XY:
        stamp(x0, y0, detail_c)
    for x0, y0 in VANILLA_BODY_XY:
        stamp(x0, y0, body_c)
    return img


def _hooked_spiral_points(
    *,
    rotation: float,
    turns: float = 1.05,
    steps: int = 56,
    outward: bool = False,
) -> List[Tuple[float, float, float]]:
    """Fallback parametric spiral for particles / non-map accents."""
    pts: List[Tuple[float, float, float]] = []
    for i in range(steps):
        t = i / max(1, steps - 1)
        if outward:
            ang = rotation - (0.15 + 0.85 * t) * turns * 2 * math.pi
            rad = 0.20 + 0.70 * t
        else:
            ang = rotation + math.pi * 0.15 + t * turns * 2 * math.pi
            rad = 0.88 - 0.55 * t
        pts.append((rad * math.cos(ang), rad * math.sin(ang) * 1.25, t))
    return pts


def paint_hooked_spiral(
    img: Image.Image,
    *,
    rotation: float,
    color: RGB,
    glow: Optional[RGB] = None,
    outward: bool = False,
    thick0: int = 0,
    trail_dots: bool = True,
    void_core: bool = False,
) -> Image.Image:
    """Thin parametric spiral (particles / accents). Map tiles use paint_vanilla_hook."""
    w, h = img.size
    px = img.load()
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    sx, sy = w * 0.42, h * 0.40
    for x_n, y_n, t in _hooked_spiral_points(rotation=rotation, outward=outward):
        x = int(round(cx + x_n * sx))
        y = int(round(cy + y_n * sy))
        if t >= 0.78:
            if not trail_dots or int(t * 28) % 2:
                continue
            _put(px, x, y, w, h, (*color, int(200 * (1.0 - t))))
            continue
        thick = 1 if (thick0 > 0 and 0.25 < t < 0.45) else 0
        if glow and t < 0.55:
            _disk(px, x, y, thick, (*glow, 40), w, h)
        _disk(px, x, y, thick, (*color, 255), w, h)
    return img


def new_tile(size: Tuple[int, int] = QUD_TILE) -> Image.Image:
    return Image.new("RGBA", size, (0, 0, 0, 0))


def render_black_hole(frame: int, total: int = 16, design: Optional[Dict] = None) -> Image.Image:
    cs = (design or {}).get("colorScheme", {})
    accretion = _rgb(cs.get("accretionDisk", "#3a6ab0"), (58, 106, 176))
    glow = _rgb(cs.get("glow", "#6aa0e0"), (106, 160, 224))
    img = new_tile()
    rot = (frame / total) * 2 * math.pi
    paint_vanilla_hook(img, color=accretion, glow=glow, rotation=rot, detail=(20, 40, 70))
    return img


def render_white_hole(frame: int, total: int = 16, design: Optional[Dict] = None) -> Image.Image:
    cs = (design or {}).get("colorScheme", {})
    arm = _rgb(cs.get("rays", "#ffd080"), (255, 208, 128))
    glow = _rgb(cs.get("glow", "#ffb040"), (255, 176, 64))
    core = _rgb(cs.get("core", "#fff4c8"), (255, 244, 200))
    img = new_tile()
    px = img.load()
    w, h = img.size
    rot = -(frame / total) * 2 * math.pi
    paint_vanilla_hook(img, color=arm, glow=glow, rotation=rot, mirror=True, detail=(180, 120, 40))
    _disk(px, w // 2, h // 2, 1, (*core, 255), w, h)
    _put(px, w // 2, h // 2, w, h, (255, 255, 255, 255))
    return img


def render_mutation_icon(design: Optional[Dict] = None) -> Image.Image:
    cs = (design or {}).get("colorScheme", {})
    primary = _rgb(cs.get("primary", "#7a5cff"), (122, 92, 255))
    glow = _rgb(cs.get("glow", "#a0c8ff"), (160, 200, 255))
    img = new_tile()
    paint_vanilla_hook(img, color=primary, glow=glow, rotation=-0.35)
    return img


def render_ability(is_aggressive: bool, design: Optional[Dict] = None) -> Image.Image:
    cs = (design or {}).get("colorScheme", {})
    if is_aggressive:
        fill = _rgb(cs.get("primary", "#ff8020"), (255, 128, 32))
        glow = _rgb(cs.get("outline", "#cc4000"), (204, 64, 0))
    else:
        fill = _rgb(cs.get("primary", "#4090ff"), (64, 144, 255))
        glow = _rgb(cs.get("outline", "#1050cc"), (16, 80, 204))
    img = new_tile()
    paint_vanilla_hook(
        img,
        color=fill,
        glow=glow,
        rotation=0.2 if is_aggressive else -0.3,
        mirror=is_aggressive,
    )
    return img


def render_warning(design: Optional[Dict] = None) -> Image.Image:
    cs = (design or {}).get("colorScheme", {})
    primary = _rgb(cs.get("primary", "#ffc800"), (255, 200, 0))
    img = new_tile()
    px = img.load()
    w, h = img.size
    cx, cy = w // 2, h // 2 - 2
    for dy, xs in (
        (-3, range(-1, 2)),
        (-2, range(-2, 3)),
        (-1, range(-1, 2)),
        (0, range(0, 1)),
        (2, range(0, 1)),
        (3, range(0, 1)),
    ):
        for dx in xs:
            _put(px, cx + dx, cy + dy, w, h, (*primary, 255))
    return img


def render_spacetime_anomaly(frame: int, total: int = 16) -> Image.Image:
    """Quantum Jitters / vanilla Space-Time Vortex — color-cycling hooked spiral."""
    palettes = [
        ((80, 180, 255), (160, 220, 255)),
        ((255, 90, 90), (255, 160, 140)),
        ((80, 230, 230), (160, 255, 255)),
        ((255, 220, 80), (255, 240, 160)),
        ((180, 180, 200), (220, 220, 230)),
    ]
    color, glow = palettes[frame % len(palettes)]
    img = new_tile()
    rot = (frame / total) * 2 * math.pi
    paint_vanilla_hook(
        img,
        color=color,
        glow=glow,
        rotation=rot,
        detail=tuple(max(0, c // 3) for c in color),  # type: ignore
    )
    return img


def render_particle(kind: str, color: RGB, frame: int, total: int = 8) -> Image.Image:
    size = (16, 16)
    img = new_tile(size)
    px = img.load()
    w, h = size
    cx = cy = w // 2
    t = frame / total
    if kind == "spark":
        ang = t * math.pi
        for arm in range(4):
            a = ang + arm * math.pi / 2
            for dist in range(1, 5):
                x = int(round(cx + dist * math.cos(a)))
                y = int(round(cy + dist * math.sin(a)))
                _put(px, x, y, w, h, (*color, 255))
        _disk(px, cx, cy, 1, (*color, 255), w, h)
    elif kind == "swirl":
        paint_hooked_spiral(img, rotation=t * 2 * math.pi, color=color, thick0=1, trail_dots=False)
    else:
        r = 1 + int(2 * abs(math.sin(t * math.pi)))
        _disk(px, cx, cy, r, (*color, 255), w, h)
    return img


def generate(mod_path: Path) -> None:
    textures = mod_path / "Textures"
    visuals = mod_path / "Visuals"
    textures.mkdir(parents=True, exist_ok=True)
    visuals.mkdir(parents=True, exist_ok=True)

    print(f"Generating crisp math tiles {QUD_TILE[0]}x{QUD_TILE[1]} -> {textures}")

    icon = render_mutation_icon()
    # Mutations.xml uses Textures/Space-Time Vortex_icon.png; keep SpaceTime alias too.
    icon.save(textures / "Space-Time Vortex_icon.png")
    icon.save(textures / "SpaceTimeVortex_icon.png")
    icon.save(visuals / "Space-Time Vortex_icon.png")
    print("  [OK] mutation icon (truecolor; requires modconfig.json shadermode=1)")

    bh_frames = [render_black_hole(i) for i in range(16)]
    for i, fr in enumerate(bh_frames):
        fr.save(textures / f"BlackHole_frame{i:02d}.png")
    bh_frames[8].save(textures / "BlackHole_visual.png")
    bh_frames[8].save(visuals / "BlackHole_visual.png")
    shutil.copy2(textures / "BlackHole_frame00.png", textures / "BlackHole_frame.png")
    print("  [OK] black hole 16 frames")

    wh_frames = [render_white_hole(i) for i in range(16)]
    for i, fr in enumerate(wh_frames):
        fr.save(textures / f"WhiteHole_frame{i:02d}.png")
    wh_frames[8].save(textures / "WhiteHole_visual.png")
    wh_frames[8].save(visuals / "WhiteHole_visual.png")
    shutil.copy2(textures / "WhiteHole_frame00.png", textures / "WhiteHole_frame.png")
    print("  [OK] white hole 16 frames")

    render_ability(True).save(textures / "VortexAbility_Aggressive.png")
    render_ability(False).save(textures / "VortexAbility_Defensive.png")
    print("  [OK] ability icons")

    render_warning().save(textures / "VortexWarning_marker.png")
    print("  [OK] warning marker")

    stv_frames = [render_spacetime_anomaly(i) for i in range(16)]
    for i, fr in enumerate(stv_frames):
        fr.save(textures / f"SpaceTimeVortex_frame{i:02d}.png")
    stv_frames[8].save(textures / "SpaceTimeVortex_visual.png")
    shutil.copy2(textures / "SpaceTimeVortex_frame00.png", textures / "SpaceTimeVortex_frame.png")
    print("  [OK] Space-Time Vortex anomaly 16 frames")

    particles = [
        ("spark", "blue", (80, 160, 255)),
        ("spark", "cyan", (80, 220, 230)),
        ("spark", "purple", (180, 100, 255)),
        ("swirl", "blue", (90, 140, 220)),
        ("swirl", "purple", (170, 110, 230)),
        ("swirl", "white", (230, 230, 240)),
        ("dot", "yellow", (240, 210, 60)),
        ("dot", "orange", (255, 150, 40)),
        ("dot", "magenta", (230, 80, 200)),
    ]
    for kind, name, col in particles:
        frames = [render_particle(kind, col, i) for i in range(8)]
        for i, fr in enumerate(frames):
            fr.save(textures / f"VortexParticle_{kind}_{name}_frame{i:02d}.png")
        frames[0].save(textures / f"VortexParticle_{kind}_{name}.png")
    print("  [OK] particles")

    for i in range(3):
        img = new_tile()
        px = img.load()
        for y in range(24):
            phase = math.sin((y / 24.0) * math.pi * 2 + i)
            x0 = int(4 + 4 * phase)
            for x in range(x0, min(16, x0 + 3)):
                _put(px, x, y, 16, 24, (100, 160, 220, 80))
        img.save(textures / f"VortexDistortion_{i:02d}.png")
    print("  [OK] distortion overlays")
    print("Done.")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate crisp 16x24 math Space-Time Vortex tiles")
    parser.add_argument(
        "mod_path",
        nargs="?",
        default=r"C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Improved and Rebalanced Space Time Vortex",
    )
    args = parser.parse_args(argv)
    mod = Path(args.mod_path)
    if not mod.is_dir():
        print(f"ERROR: mod not found: {mod}")
        return 1
    generate(mod)
    try:
        from vortex_mod_integration import apply_mod_integration

        _found, messages = apply_mod_integration(mod)
        print("Integration:")
        for m in messages:
            print(f"  - {m}")
    except Exception as e:
        print(f"[WARN] integration: {e}")

    tex = mod / "Textures"
    bad = []
    must_tile = [
        "Space-Time Vortex_icon.png",
        "BlackHole_frame00.png",
        "WhiteHole_frame00.png",
        "SpaceTimeVortex_frame00.png",
        "VortexAbility_Aggressive.png",
        "VortexAbility_Defensive.png",
        "VortexWarning_marker.png",
    ]
    for name in must_tile:
        p = tex / name
        im = Image.open(p)
        if im.size != QUD_TILE:
            bad.append(f"{name}={im.size}")
    if bad:
        print("SIZE FAIL:", ", ".join(bad))
        return 1
    print(f"Verified: core tiles are {QUD_TILE[0]}x{QUD_TILE[1]} truecolor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
