#!/usr/bin/env python3
"""
Procedural Terraria content art — real PNGs for weapons, projectiles, items, creatures.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFilter


def _parse_color(s: str) -> Tuple[int, int, int]:
    named = {
        "void": (80, 140, 255),
        "fire": (255, 90, 40),
        "ice": (140, 220, 255),
        "nature": (80, 200, 100),
        "shadow": (120, 60, 180),
        "light": (255, 240, 160),
        "electric": (255, 230, 80),
    }
    key = (s or "").strip().lower()
    if key in named:
        return named[key]
    h = s.strip().lstrip("#")
    if len(h) == 6:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (180, 180, 200)


def _ensure(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_weapon(path: Path, size: int, color: str, style: str = "sword") -> None:
    rgb = _parse_color(color)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    style_l = (style or "sword").lower()
    c = size / 2
    if style_l in ("bow", "ranged"):
        d.arc([size * 0.2, size * 0.15, size * 0.55, size * 0.85], 90, 270, fill=(*rgb, 255), width=max(2, size // 16))
        d.line([(c * 0.7, size * 0.2), (c * 0.7, size * 0.8)], fill=(200, 180, 120, 255), width=max(1, size // 24))
        d.line([(c * 0.7, c), (size * 0.85, c)], fill=(*rgb, 230), width=max(1, size // 20))
    elif style_l in ("staff", "magic", "wand"):
        d.line([(c * 0.55, size * 0.85), (c * 1.1, size * 0.2)], fill=(160, 120, 70, 255), width=max(2, size // 14))
        d.ellipse([size * 0.62, size * 0.08, size * 0.88, size * 0.34], fill=(*rgb, 230), outline=(255, 255, 255, 180))
        d.ellipse([size * 0.68, size * 0.14, size * 0.78, size * 0.24], fill=(255, 255, 255, 160))
    else:  # sword / melee
        d.polygon(
            [
                (c, size * 0.08),
                (c + size * 0.1, size * 0.55),
                (c + size * 0.04, size * 0.55),
                (c + size * 0.04, size * 0.78),
                (c - size * 0.04, size * 0.78),
                (c - size * 0.04, size * 0.55),
                (c - size * 0.1, size * 0.55),
            ],
            fill=(*rgb, 240),
        )
        d.rectangle([c - size * 0.14, size * 0.52, c + size * 0.14, size * 0.58], fill=(180, 160, 80, 255))
        d.rectangle([c - size * 0.03, size * 0.58, c + size * 0.03, size * 0.9], fill=(120, 80, 40, 255))
    _ensure(path)
    im.save(path, "PNG")


def write_projectile(path: Path, size: int, color: str, frames: int = 1) -> None:
    rgb = _parse_color(color)
    frames = max(1, frames)
    w = size * frames
    im = Image.new("RGBA", (w, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i in range(frames):
        ox = i * size
        phase = i / max(1, frames)
        glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        pad = int(size * (0.25 - 0.05 * math.sin(phase * math.pi)))
        gd.ellipse([pad, pad, size - pad, size - pad], fill=(*rgb, 90))
        inner = int(size * 0.32)
        gd.ellipse([inner, inner, size - inner, size - inner], fill=(*rgb, 255))
        tip = [
            (size * 0.75, size * 0.5),
            (size * 0.35, size * 0.28),
            (size * 0.35, size * 0.72),
        ]
        gd.polygon(tip, fill=(255, 255, 255, 200))
        glow = glow.filter(ImageFilter.GaussianBlur(radius=max(1, size // 20)))
        base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        base = Image.alpha_composite(base, glow)
        core = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ImageDraw.Draw(core).ellipse([inner, inner, size - inner, size - inner], fill=(*rgb, 255))
        base = Image.alpha_composite(base, core)
        im.paste(base, (ox, 0), base)
    _ensure(path)
    im.save(path, "PNG")


def write_item(path: Path, size: int, color: str, kind: str = "material") -> None:
    rgb = _parse_color(color)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    kind_l = (kind or "material").lower()
    if kind_l in ("accessory", "ring"):
        d.ellipse([size * 0.2, size * 0.2, size * 0.8, size * 0.8], outline=(*rgb, 255), width=max(2, size // 12))
        d.ellipse([size * 0.38, size * 0.38, size * 0.62, size * 0.62], fill=(*rgb, 200))
    elif kind_l in ("potion", "consumable"):
        d.polygon(
            [
                (size * 0.35, size * 0.2),
                (size * 0.65, size * 0.2),
                (size * 0.72, size * 0.45),
                (size * 0.72, size * 0.85),
                (size * 0.28, size * 0.85),
                (size * 0.28, size * 0.45),
            ],
            fill=(*rgb, 210),
            outline=(255, 255, 255, 160),
        )
        d.rectangle([size * 0.38, size * 0.12, size * 0.62, size * 0.22], fill=(200, 200, 220, 255))
    else:
        d.rectangle(
            [int(size * 0.2), int(size * 0.2), int(size * 0.8), int(size * 0.8)],
            fill=(*rgb, 230),
            outline=(255, 255, 255, 120),
        )
        d.line([(size * 0.3, size * 0.35), (size * 0.7, size * 0.35)], fill=(255, 255, 255, 140), width=2)
    _ensure(path)
    im.save(path, "PNG")


def write_creature(path: Path, size: int, color: str, frames: int = 4) -> None:
    """Horizontal walk strip (frames * size wide)."""
    rgb = _parse_color(color)
    frames = max(1, frames)
    w = size * frames
    im = Image.new("RGBA", (w, size), (0, 0, 0, 0))
    for i in range(frames):
        ox = i * size
        cell = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(cell)
        bob = math.sin(i / frames * math.tau) * (size * 0.04)
        # body
        d.ellipse(
            [size * 0.22, size * 0.35 + bob, size * 0.78, size * 0.85 + bob],
            fill=(*rgb, 240),
        )
        # head
        d.ellipse(
            [size * 0.32, size * 0.12 + bob, size * 0.68, size * 0.48 + bob],
            fill=tuple(min(255, c + 30) for c in rgb) + (255,),
        )
        # eye
        d.ellipse(
            [size * 0.48, size * 0.24 + bob, size * 0.58, size * 0.34 + bob],
            fill=(20, 20, 30, 255),
        )
        # legs (alternate)
        leg = size * (0.08 if i % 2 == 0 else -0.08)
        d.rectangle(
            [size * 0.32 + leg, size * 0.78 + bob, size * 0.42 + leg, size * 0.95 + bob],
            fill=tuple(max(0, c - 40) for c in rgb) + (255,),
        )
        d.rectangle(
            [size * 0.58 - leg, size * 0.78 + bob, size * 0.68 - leg, size * 0.95 + bob],
            fill=tuple(max(0, c - 40) for c in rgb) + (255,),
        )
        im.paste(cell, (ox, 0), cell)
    _ensure(path)
    im.save(path, "PNG")


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("weapon")
    p.add_argument("--path", required=True)
    p.add_argument("--size", type=int, default=40)
    p.add_argument("--color", default="#c8c8ff")
    p.add_argument("--style", default="sword")

    p = sub.add_parser("projectile")
    p.add_argument("--path", required=True)
    p.add_argument("--size", type=int, default=32)
    p.add_argument("--color", default="#88ccff")
    p.add_argument("--frames", type=int, default=1)

    p = sub.add_parser("item")
    p.add_argument("--path", required=True)
    p.add_argument("--size", type=int, default=32)
    p.add_argument("--color", default="#88ffaa")
    p.add_argument("--kind", default="material")

    p = sub.add_parser("creature")
    p.add_argument("--path", required=True)
    p.add_argument("--size", type=int, default=40)
    p.add_argument("--color", default="#66aa66")
    p.add_argument("--frames", type=int, default=4)

    args = ap.parse_args()
    path = Path(args.path)
    if args.cmd == "weapon":
        write_weapon(path, args.size, args.color, args.style)
    elif args.cmd == "projectile":
        write_projectile(path, args.size, args.color, args.frames)
    elif args.cmd == "item":
        write_item(path, args.size, args.color, args.kind)
    elif args.cmd == "creature":
        write_creature(path, args.size, args.color, args.frames)
    print(f"OK {args.cmd} -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
