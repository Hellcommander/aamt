#!/usr/bin/env python3
"""Mechanical quality gates for Elin procedural assets."""

from __future__ import annotations

from typing import Tuple

from PIL import Image, ImageEnhance, ImageFilter, ImageStat


def compute_edge_density(img: Image.Image) -> float:
    """Fraction of pixels with strong edges — rejects flat geometric fills."""
    gray = img.convert("RGB").convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    data = list(edges.getdata())
    if not data:
        return 0.0
    strong = sum(1 for p in data if p > 28)
    return strong / len(data)


def validate_sprite_quality(
    img: Image.Image,
    min_nontransparent_ratio: float = 0.04,
    min_luma_variance: float = 120.0,
    min_edge_density: float = 0.0,
) -> Tuple[bool, str]:
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    w, h = img.size
    if w < 4 or h < 4:
        return False, f"too small ({w}x{h})"

    alpha = img.split()[3]
    opaque = sum(1 for p in alpha.getdata() if p > 16)
    ratio = opaque / max(1, w * h)
    if ratio < min_nontransparent_ratio:
        return False, f"too transparent ({ratio:.1%} coverage)"

    luma = img.convert("RGB").convert("L")
    lstat = ImageStat.Stat(luma)
    if lstat.var[0] < min_luma_variance:
        return False, f"too flat (variance {lstat.var[0]:.1f})"

    if min_edge_density > 0:
        edge = compute_edge_density(img)
        if edge < min_edge_density:
            return False, f"too simple (edge density {edge:.3f} < {min_edge_density:.3f})"

    return True, "ok"


def validate_icon(img: Image.Image) -> Tuple[bool, str]:
    w, h = img.size
    min_var = 80.0 if max(w, h) <= 32 else 120.0
    min_edge = 0.045 if max(w, h) <= 32 else 0.035
    return validate_sprite_quality(
        img,
        min_nontransparent_ratio=0.08,
        min_luma_variance=min_var,
        min_edge_density=min_edge,
    )


def validate_texture(img: Image.Image) -> Tuple[bool, str]:
    if img.mode != "RGB":
        img = img.convert("RGB")
    lstat = ImageStat.Stat(img.convert("L"))
    if lstat.var[0] < 180.0:
        return False, f"texture too flat (variance {lstat.var[0]:.1f})"
    edge = compute_edge_density(img.convert("RGBA"))
    if edge < 0.02:
        return False, f"texture too simple (edge density {edge:.3f})"
    return True, "ok"


def finalize_rgba(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    img = ImageEnhance.Sharpness(img).enhance(1.15)
    img = ImageEnhance.Contrast(img).enhance(1.08)
    img = ImageEnhance.Color(img).enhance(1.05)
    return img


def finalize_texture(img: Image.Image) -> Image.Image:
    if img.mode != "RGB":
        img = img.convert("RGB")
    img = ImageEnhance.Sharpness(img).enhance(1.1)
    img = ImageEnhance.Contrast(img).enhance(1.06)
    img = ImageEnhance.Color(img).enhance(1.04)
    return img
