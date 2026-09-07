#!/usr/bin/env python3
"""Procedural icon / texture templates for Elemental Reforged monster gear."""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
except ImportError as exc:
    raise SystemExit("Pillow required: python -m pip install Pillow") from exc


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _palette(palette: list[str]) -> list[tuple[int, int, int]]:
    colors = [hex_to_rgb(c) for c in palette]
    while len(colors) < 4:
        colors.append(colors[-1])
    return colors


def make_icon(size: int, palette: list[str], seed: int, style: str = "armor") -> Image.Image:
    rng = random.Random(seed)
    colors = _palette(palette)

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = size // 12
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=(*colors[3], 255),
    )

    cx, cy = size // 2, size // 2
    style = (style or "armor").lower()

    if style == "robe":
        pts = [
            (cx - size * 0.22, cy - size * 0.28),
            (cx + size * 0.22, cy - size * 0.28),
            (cx + size * 0.30, cy + size * 0.32),
            (cx - size * 0.30, cy + size * 0.32),
        ]
        draw.polygon(pts, fill=(*colors[0], 255), outline=(*colors[2], 255))
    elif style == "plate":
        pts = [
            (cx - size * 0.28, cy - size * 0.18),
            (cx, cy - size * 0.32),
            (cx + size * 0.28, cy - size * 0.18),
            (cx + size * 0.26, cy + size * 0.28),
            (cx, cy + size * 0.34),
            (cx - size * 0.26, cy + size * 0.28),
        ]
        draw.polygon(pts, fill=(*colors[0], 255), outline=(*colors[2], 255))
    elif style in ("weapon", "blade", "sword"):
        # Vertical blade + crossguard + pommel
        blade = [
            (cx, cy - size * 0.34),
            (cx + size * 0.08, cy - size * 0.05),
            (cx + size * 0.05, cy + size * 0.12),
            (cx - size * 0.05, cy + size * 0.12),
            (cx - size * 0.08, cy - size * 0.05),
        ]
        draw.polygon(blade, fill=(*colors[2], 255), outline=(*colors[1], 255))
        draw.rectangle(
            [cx - size * 0.18, cy + size * 0.10, cx + size * 0.18, cy + size * 0.16],
            fill=(*colors[0], 255),
        )
        draw.rectangle(
            [cx - size * 0.04, cy + size * 0.16, cx + size * 0.04, cy + size * 0.30],
            fill=(*colors[1], 255),
        )
        draw.ellipse(
            [cx - size * 0.06, cy + size * 0.28, cx + size * 0.06, cy + size * 0.36],
            fill=(*colors[0], 255),
        )
    elif style in ("axe", "cleaver"):
        haft = [
            (cx - size * 0.04, cy - size * 0.28),
            (cx + size * 0.04, cy - size * 0.28),
            (cx + size * 0.05, cy + size * 0.32),
            (cx - size * 0.05, cy + size * 0.32),
        ]
        draw.polygon(haft, fill=(*colors[1], 255))
        head = [
            (cx + size * 0.02, cy - size * 0.26),
            (cx + size * 0.30, cy - size * 0.18),
            (cx + size * 0.28, cy + size * 0.02),
            (cx + size * 0.02, cy - size * 0.02),
        ]
        draw.polygon(head, fill=(*colors[0], 255), outline=(*colors[2], 255))
    elif style in ("bow", "longbow"):
        draw.arc(
            [cx - size * 0.28, cy - size * 0.32, cx + size * 0.12, cy + size * 0.32],
            start=270,
            end=90,
            fill=(*colors[0], 255),
            width=max(3, size // 28),
        )
        draw.line(
            [(cx - size * 0.08, cy - size * 0.30), (cx - size * 0.08, cy + size * 0.30)],
            fill=(*colors[2], 220),
            width=max(2, size // 48),
        )
        draw.line(
            [(cx - size * 0.08, cy), (cx + size * 0.22, cy)],
            fill=(*colors[1], 255),
            width=max(2, size // 40),
        )
    elif style in ("club", "mace", "blunt"):
        draw.rectangle(
            [cx - size * 0.04, cy - size * 0.08, cx + size * 0.04, cy + size * 0.34],
            fill=(*colors[1], 255),
        )
        draw.ellipse(
            [cx - size * 0.18, cy - size * 0.34, cx + size * 0.18, cy - size * 0.02],
            fill=(*colors[0], 255),
            outline=(*colors[2], 255),
        )
        for _ in range(6):
            x = int(cx + rng.uniform(-0.12, 0.12) * size)
            y = int(cy - size * 0.18 + rng.uniform(-0.08, 0.08) * size)
            r = max(2, size // 36)
            draw.ellipse([x - r, y - r, x + r, y + r], fill=(*colors[2], 230))
    else:
        pts = [
            (cx - size * 0.26, cy - size * 0.22),
            (cx + size * 0.26, cy - size * 0.22),
            (cx + size * 0.30, cy + size * 0.10),
            (cx + size * 0.18, cy + size * 0.30),
            (cx - size * 0.18, cy + size * 0.30),
            (cx - size * 0.30, cy + size * 0.10),
        ]
        draw.polygon(pts, fill=(*colors[0], 255), outline=(*colors[2], 255))
        accent = (*colors[2], 230)
        for _ in range(10):
            x = int(cx + rng.uniform(-0.22, 0.22) * size)
            y = int(cy + rng.uniform(-0.22, 0.22) * size)
            r = max(2, size // 40)
            draw.ellipse([x - r, y - r, x + r, y + r], fill=accent)

    draw.arc(
        [margin + 4, margin + 4, size - margin - 4, size - margin - 4],
        start=200,
        end=340,
        fill=(*colors[1], 180),
        width=max(2, size // 48),
    )

    # Soft drop shadow behind the shape for depth (uses the alpha silhouette).
    alpha = img.split()[-1]
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    solid = Image.new("RGBA", (size, size), (0, 0, 0, 170))
    shadow = Image.composite(solid, shadow, alpha)
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(1, size / 40)))
    off = max(1, size // 44)
    backing = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    backing.paste(shadow, (off, off), shadow)
    return Image.alpha_composite(backing, img)


def render_icon(size: int, palette: list, seed: int, style: str = "armor") -> "Image.Image":
    """Supersample x3 (capped) then Lanczos-downscale for clean anti-aliased edges."""
    ss = min(size * 3, 768)
    big = make_icon(ss, palette, seed, style)
    if ss != size:
        big = big.resize((size, size), Image.Resampling.LANCZOS)
    # Split/rejoin so we sharpen color without haloing the alpha edge.
    alpha = big.split()[-1]
    rgb = big.convert("RGB").filter(
        ImageFilter.UnsharpMask(radius=1.0, percent=90, threshold=2)
    )
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    return out


def make_texture(size: int, palette: list[str], seed: int) -> Image.Image:
    """Fast seamless-ish texture via small noise upsample (not per-pixel Python loops)."""
    rng = random.Random(seed)
    colors = _palette(palette)

    # Build a small noise map then upscale — orders of magnitude faster than px loops.
    small = max(32, min(96, size // 8))
    noise = Image.new("RGB", (small, small))
    npx = noise.load()
    for y in range(small):
        for x in range(small):
            n = (
                math.sin(x * 0.35 + seed * 0.01) * 0.45
                + math.cos(y * 0.28 + seed * 0.02) * 0.45
                + rng.random() * 0.35
            )
            t = max(0.0, min(1.0, (n + 1.1) / 2.2))
            if t < 0.33:
                c0, c1, u = colors[0], colors[1], t / 0.33
            elif t < 0.66:
                c0, c1, u = colors[1], colors[2], (t - 0.33) / 0.33
            else:
                c0, c1, u = colors[2], colors[3], (t - 0.66) / 0.34
            npx[x, y] = tuple(int(lerp(c0[i], c1[i], u)) for i in range(3))

    img = noise.resize((size, size), Image.Resampling.BICUBIC)

    # Soft mid band for team-color friendliness
    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle([0, size // 3, size, 2 * size // 3], fill=(*colors[1], 36))
    # Subtle diagonal grain
    for i in range(0, size, max(8, size // 64)):
        od.line([(0, i), (size, i + size // 5)], fill=(*colors[3], 18), width=1)

    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    # Make it seamless: blend the image with a half-tile-offset copy so the
    # wrap edges cross-fade. Feather mask avoids a visible centre seam.
    try:
        from PIL import ImageChops

        offset = ImageChops.offset(img, size // 2, size // 2)
        mask = Image.new("L", (size, size), 0)
        md = ImageDraw.Draw(mask)
        band = max(4, size // 8)
        md.rectangle([size // 2 - band, 0, size // 2 + band, size], fill=120)
        md.rectangle([0, size // 2 - band, size, size // 2 + band], fill=120)
        mask = mask.filter(ImageFilter.GaussianBlur(band / 2))
        img = Image.composite(offset, img, mask)
    except Exception:
        pass

    img = ImageEnhance.Contrast(img).enhance(1.12)
    img = ImageEnhance.Color(img).enhance(1.05)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=80, threshold=3))
    return img


def main() -> None:
    ap = argparse.ArgumentParser(description="Procedural ER monster gear assets")
    ap.add_argument("--mode", choices=["icon", "texture", "both"], default="both")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--palette", required=True, help="Comma-separated hex colors")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--icon-size", type=int, default=128)
    ap.add_argument("--texture-size", type=int, default=512)
    ap.add_argument(
        "--style",
        default="armor",
        help="armor|plate|robe|weapon|axe|bow|club|blade",
    )
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    palette = [p.strip() for p in args.palette.split(",") if p.strip()]
    seed = args.seed or (sum(ord(c) for c in args.name) % 100000)

    result: dict[str, str] = {}
    if args.mode in ("icon", "both"):
        icon = render_icon(args.icon_size, palette, seed, args.style)
        icon_path = out / f"{args.name}_Icon.png"
        icon.save(icon_path)
        result["icon"] = str(icon_path)

    if args.mode in ("texture", "both"):
        tex = make_texture(args.texture_size, palette, seed + 17)
        tex_path = out / f"{args.name}_Texture.png"
        tex.save(tex_path)
        result["texture"] = str(tex_path)

    print(json.dumps(result))


if __name__ == "__main__":
    main()
