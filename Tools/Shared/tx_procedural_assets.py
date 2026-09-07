#!/usr/bin/env python3
"""
Procedural Transcendence media writers — real PNG/JPG/WAV/OBJ, never .info.txt stubs.

Usage:
  python tx_procedural_assets.py icon --path out.png --size 96 --color "#ff4444"
  python tx_procedural_assets.py texture --path out.png --width 512 --height 512 --color "#2a2a3a"
  python tx_procedural_assets.py spritesheet --path out.png --columns 8 --rows 4 --cell 64 --color "#4488ff"
  python tx_procedural_assets.py planet --path out.png --size 256 --seed 1
  python tx_procedural_assets.py beacon --inactive inactive.png --active active.png --color Green
  python tx_procedural_assets.py power --path out.png --size 96 --style Crystal --color Green
  python tx_procedural_assets.py audio --path out.wav --duration 2 --rate 44100 --kind Effect
  python tx_procedural_assets.py model --path out.obj --name Ship
"""
from __future__ import annotations

import argparse
import colorsys
import math
import struct
import wave
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFilter


def _parse_color(s: str) -> Tuple[int, int, int]:
    named = {
        "green": (40, 220, 80),
        "yellow": (240, 220, 40),
        "blue": (40, 120, 255),
        "red": (240, 40, 40),
        "purple": (180, 60, 220),
        "orange": (240, 140, 40),
        "cyan": (40, 220, 220),
    }
    key = (s or "").strip().lower()
    if key in named:
        return named[key]
    h = s.strip().lstrip("#")
    if len(h) == 6:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (80, 140, 220)


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_icon(path: Path, size: int, color: str) -> None:
    rgb = _parse_color(color)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pad = max(2, size // 16)
    d.ellipse([pad, pad, size - pad, size - pad], fill=(*rgb, 90))
    inner = int(size * 0.2)
    d.ellipse([inner, inner, size - inner, size - inner], fill=(*rgb, 255))
    hi = int(size * 0.28)
    d.ellipse([hi, hi, hi + size // 5, hi + size // 5], fill=(255, 255, 255, 180))
    _ensure_parent(path)
    im.save(path, "PNG")


def write_texture(path: Path, width: int, height: int, color: str, seed: int = 0) -> None:
    rgb = _parse_color(color)
    im = Image.new("RGB", (width, height), rgb)
    d = ImageDraw.Draw(im)
    # Panel grid
    step = max(8, min(width, height) // 16)
    line = tuple(max(0, c - 30) for c in rgb)
    for x in range(0, width, step):
        d.line([(x, 0), (x, height)], fill=line, width=1)
    for y in range(0, height, step):
        d.line([(0, y), (width, y)], fill=line, width=1)
    # Accent rivets
    accent = tuple(min(255, c + 40) for c in rgb)
    rng = seed * 1103515245 + 12345
    for i in range(24):
        rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
        x = rng % width
        rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
        y = rng % height
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=accent)
    _ensure_parent(path)
    im.save(path, "PNG")


def write_spritesheet(
    path: Path, columns: int, rows: int, cell: int, color: str
) -> None:
    rgb = _parse_color(color)
    w, h = columns * cell, rows * cell
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    frames = columns * rows
    for i in range(frames):
        col, row = i % columns, i // columns
        ox, oy = col * cell, row * cell
        angle = (i / max(1, frames)) * math.tau
        cx, cy = ox + cell / 2, oy + cell / 2
        r = cell * 0.32
        pts = [
            (cx + r * math.cos(angle), cy + r * math.sin(angle)),
            (cx + r * 0.45 * math.cos(angle + 2.3), cy + r * 0.45 * math.sin(angle + 2.3)),
            (cx + r * 0.45 * math.cos(angle - 2.3), cy + r * 0.45 * math.sin(angle - 2.3)),
        ]
        d.polygon(pts, fill=(*rgb, 230))
        d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(255, 255, 255, 200))
    _ensure_parent(path)
    fmt = "JPEG" if path.suffix.lower() in (".jpg", ".jpeg") else "PNG"
    if fmt == "JPEG":
        im.convert("RGB").save(path, "JPEG", quality=92)
    else:
        im.save(path, "PNG")


def write_planet(path: Path, size: int, seed: int = 0) -> None:
    rng = seed * 1103515245 + 12345
    hue = ((rng >> 8) % 1000) / 1000.0
    base = colorsys.hsv_to_rgb(hue, 0.55, 0.75)
    rgb = tuple(int(c * 255) for c in base)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pad = size // 10
    # Atmosphere
    d.ellipse([pad // 2, pad // 2, size - pad // 2, size - pad // 2], fill=(*rgb, 60))
    d.ellipse([pad, pad, size - pad, size - pad], fill=(*rgb, 255))
    # Continents
    for _ in range(8):
        rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
        cx = pad + (rng % (size - 2 * pad))
        rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
        cy = pad + (rng % (size - 2 * pad))
        rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
        rr = 8 + (rng % max(8, size // 8))
        land = tuple(max(0, min(255, c + ((rng >> 3) % 40) - 20)) for c in rgb)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(*land, 220))
    # Limb darkening mask
    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([pad, pad, size - pad, size - pad], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=max(1, size // 40)))
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    # Specular highlight
    hd = ImageDraw.Draw(out)
    hx, hy = int(size * 0.32), int(size * 0.28)
    hd.ellipse([hx, hy, hx + size // 6, hy + size // 6], fill=(255, 255, 255, 70))
    _ensure_parent(path)
    out.save(path, "PNG")


def write_beacon(inactive: Path, active: Path, color: str, inactive_size: int = 32, active_size: int = 150) -> None:
    rgb = _parse_color(color)

    def inactive_img(size: int) -> Image.Image:
        im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        px = im.load()
        c = size // 2
        outer, inner = size // 2 - 2, max(2, size // 6)
        for y in range(size):
            for x in range(size):
                dist = math.hypot(x - c, y - c)
                if inner < dist <= outer:
                    px[x, y] = (40, 40, 40, 255)
                elif dist <= inner:
                    px[x, y] = (*rgb, 255)
        return im

    def active_img(size: int) -> Image.Image:
        im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        px = im.load()
        c = size // 2
        core, glow = max(2, size // 8), size // 2
        for y in range(size):
            for x in range(size):
                dist = math.hypot(x - c, y - c)
                if dist <= glow:
                    t = 1.0 - dist / glow
                    px[x, y] = (
                        int(rgb[0] * t),
                        int(rgb[1] * t),
                        int(rgb[2] * t),
                        int(200 * t),
                    )
                if dist <= core:
                    px[x, y] = (255, 255, 255, 255)
        return im

    _ensure_parent(inactive)
    _ensure_parent(active)
    inactive_img(inactive_size).save(inactive, "PNG")
    active_img(active_size).save(active, "PNG")


def write_power(path: Path, size: int, style: str, color: str) -> None:
    rgb = _parse_color(color)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = size / 2
    style_l = (style or "Crystal").lower()
    if style_l == "orb":
        d.ellipse([size * 0.15, size * 0.15, size * 0.85, size * 0.85], fill=(*rgb, 200))
        d.ellipse([size * 0.28, size * 0.28, size * 0.55, size * 0.55], fill=(255, 255, 255, 160))
    elif style_l == "spire":
        d.polygon([(c, size * 0.1), (size * 0.75, size * 0.85), (size * 0.25, size * 0.85)], fill=(*rgb, 230))
    elif style_l == "disk":
        d.ellipse([size * 0.1, size * 0.1, size * 0.9, size * 0.9], outline=(*rgb, 255), width=max(2, size // 16))
        for i in range(8):
            a = i * math.pi / 4
            d.line([(c, c), (c + size * 0.4 * math.cos(a), c + size * 0.4 * math.sin(a))], fill=(*rgb, 180), width=2)
    elif style_l == "radial":
        for i in range(12):
            a = i * math.pi / 6
            d.line([(c, c), (c + size * 0.42 * math.cos(a), c + size * 0.42 * math.sin(a))], fill=(*rgb, 200), width=3)
        d.ellipse([c - size * 0.12, c - size * 0.12, c + size * 0.12, c + size * 0.12], fill=(255, 255, 255, 220))
    elif style_l in ("cluster", "shell"):
        for i in range(6):
            a = i * math.pi / 3
            x, y = c + size * 0.22 * math.cos(a), c + size * 0.22 * math.sin(a)
            d.polygon(
                [(x, y - size * 0.12), (x + size * 0.1, y + size * 0.08), (x - size * 0.1, y + size * 0.08)],
                fill=(*rgb, 220),
            )
    else:  # Crystal default
        d.polygon(
            [
                (c, size * 0.08),
                (size * 0.72, c),
                (c, size * 0.92),
                (size * 0.28, c),
            ],
            fill=(*rgb, 230),
        )
        d.line([(c, size * 0.08), (c, size * 0.92)], fill=(255, 255, 255, 160), width=2)
    glow = im.filter(ImageFilter.GaussianBlur(radius=max(1, size // 24)))
    out = Image.alpha_composite(glow, im)
    _ensure_parent(path)
    out.save(path, "PNG")


def write_audio(path: Path, duration: float, rate: int, kind: str) -> None:
    _ensure_parent(path)
    n = max(1, int(duration * rate))
    # Simple procedural tones by kind
    freqs = {
        "weapon": 880.0,
        "engine": 110.0,
        "music": 220.0,
        "ambient": 55.0,
        "voice": 330.0,
        "effect": 440.0,
    }
    f0 = freqs.get((kind or "effect").lower(), 440.0)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = bytearray()
        for i in range(n):
            t = i / rate
            # Envelope + slight chirp
            env = min(1.0, t * 8) * max(0.0, 1.0 - t / max(0.01, duration))
            sample = int(16000 * env * math.sin(2 * math.pi * (f0 + 40 * t) * t))
            frames += struct.pack("<h", max(-32767, min(32767, sample)))
        w.writeframes(frames)


def write_model(path: Path, name: str) -> None:
    """Compact wedge frigate mesh (importable OBJ), not a single triangle stub."""
    _ensure_parent(path)
    verts = [
        (0.0, 0.0, 1.2),
        (-0.7, 0.0, -0.8),
        (0.7, 0.0, -0.8),
        (0.0, 0.35, -0.2),
        (0.0, -0.2, -0.2),
        (-0.9, 0.0, -0.2),
        (0.9, 0.0, -0.2),
    ]
    faces = [
        (1, 2, 4),
        (1, 4, 3),
        (1, 3, 5),
        (1, 5, 2),
        (4, 2, 3),
        (5, 3, 2),
        (2, 6, 4),
        (3, 4, 7),
        (2, 5, 6),
        (3, 7, 5),
    ]
    lines = [
        f"# Transcendence ship model: {name}",
        "# Generated by tx_procedural_assets.py",
        "o " + (name or "Ship"),
    ]
    for v in verts:
        lines.append(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}")
    for a, b, c in faces:
        lines.append(f"f {a} {b} {c}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Procedural TX media writers")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("icon")
    p.add_argument("--path", required=True)
    p.add_argument("--size", type=int, default=96)
    p.add_argument("--color", default="#4488ff")

    p = sub.add_parser("texture")
    p.add_argument("--path", required=True)
    p.add_argument("--width", type=int, default=512)
    p.add_argument("--height", type=int, default=512)
    p.add_argument("--color", default="#2a2a3a")
    p.add_argument("--seed", type=int, default=0)

    p = sub.add_parser("spritesheet")
    p.add_argument("--path", required=True)
    p.add_argument("--columns", type=int, default=8)
    p.add_argument("--rows", type=int, default=4)
    p.add_argument("--cell", type=int, default=64)
    p.add_argument("--color", default="#4488ff")

    p = sub.add_parser("planet")
    p.add_argument("--path", required=True)
    p.add_argument("--size", type=int, default=256)
    p.add_argument("--seed", type=int, default=0)

    p = sub.add_parser("beacon")
    p.add_argument("--inactive", required=True)
    p.add_argument("--active", required=True)
    p.add_argument("--color", default="Green")
    p.add_argument("--inactive-size", type=int, default=32)
    p.add_argument("--active-size", type=int, default=150)

    p = sub.add_parser("power")
    p.add_argument("--path", required=True)
    p.add_argument("--size", type=int, default=96)
    p.add_argument("--style", default="Crystal")
    p.add_argument("--color", default="Green")

    p = sub.add_parser("audio")
    p.add_argument("--path", required=True)
    p.add_argument("--duration", type=float, default=2.0)
    p.add_argument("--rate", type=int, default=44100)
    p.add_argument("--kind", default="Effect")

    p = sub.add_parser("model")
    p.add_argument("--path", required=True)
    p.add_argument("--name", default="Ship")

    args = ap.parse_args()
    if args.cmd == "icon":
        write_icon(Path(args.path), args.size, args.color)
    elif args.cmd == "texture":
        write_texture(Path(args.path), args.width, args.height, args.color, args.seed)
    elif args.cmd == "spritesheet":
        write_spritesheet(Path(args.path), args.columns, args.rows, args.cell, args.color)
    elif args.cmd == "planet":
        write_planet(Path(args.path), args.size, args.seed)
    elif args.cmd == "beacon":
        write_beacon(
            Path(args.inactive),
            Path(args.active),
            args.color,
            args.inactive_size,
            args.active_size,
        )
    elif args.cmd == "power":
        write_power(Path(args.path), args.size, args.style, args.color)
    elif args.cmd == "audio":
        write_audio(Path(args.path), args.duration, args.rate, args.kind)
    elif args.cmd == "model":
        write_model(Path(args.path), args.name)
    print(f"OK {args.cmd}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
