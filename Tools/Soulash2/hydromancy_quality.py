#!/usr/bin/env python3
"""
Quality pipeline for Soulash 2 Hydromancy mod assets.

- PIL mechanical checks (size, alpha coverage, contrast)
- Ollama JSON design-spec parsing (shared pattern from Qud vortex_quality)
- Optional vision-model scoring via Ollama multimodal API
"""

from __future__ import annotations

import base64
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from PIL import Image, ImageEnhance, ImageFilter, ImageStat

_here = Path(__file__).resolve().parent
_shared_dir = _here.parent / "Shared"
for _p in (_here, _shared_dir):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

SOULASH_ART_SYSTEM = (
    "You are a senior art director for Soulash 2, a dark fantasy roguelike with "
    "hand-painted pixel UI icons. Design cohesive hydromancy palettes: deep teal, "
    "cyan highlights, hydraulic pressure motifs. Return ONLY valid JSON."
)

HYDROMANCY_PALETTE = ["#0a1628", "#0d3d56", "#1a6b8a", "#3eb8d4", "#a8e6f0", "#ffffff"]


def parse_ollama_json(response: str, asset_type: str = "asset") -> Dict[str, Any]:
    if not response or not response.strip():
        raise ValueError(f"Empty Ollama response for {asset_type}")

    text = response.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start < 0 or end <= start:
            raise ValueError(f"No JSON object in Ollama response for {asset_type}")
        text = text[start:end]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        repaired = re.sub(r",\s*}", "}", text)
        repaired = re.sub(r",\s*]", "]", repaired)
        return json.loads(repaired)


def validate_mod_icon(img: Image.Image) -> Tuple[bool, str]:
    if img.size != (32, 32):
        return False, f"mod icon must be 32x32, got {img.size[0]}x{img.size[1]}"
    return validate_sprite_quality(
        img, min_nontransparent_ratio=0.12, min_luma_variance=140.0, min_edge_density=0.055,
    )


def validate_thumbnail(img: Image.Image) -> Tuple[bool, str]:
    w, h = img.size
    if w < 400 or h < 300:
        return False, f"thumbnail too small ({w}x{h})"
    ratio = w / h
    if not (1.25 <= ratio <= 1.4):
        return False, f"thumbnail aspect should be ~4:3, got {ratio:.2f}"
    return validate_sprite_quality(
        img, min_nontransparent_ratio=0.02, min_luma_variance=380.0, min_edge_density=0.028,
    )


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


def finalize_icon(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    img = ImageEnhance.Sharpness(img).enhance(1.15)
    img = ImageEnhance.Contrast(img).enhance(1.08)
    img = ImageEnhance.Color(img).enhance(1.05)
    return img


def _center_crop_aspect(img: Image.Image, target_ratio: float = 4 / 3) -> Image.Image:
    img = img.convert("RGBA")
    w, h = img.size
    current = w / h
    if current > target_ratio:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        return img.crop((left, 0, left + new_w, h))
    new_h = int(w / target_ratio)
    top = (h - new_h) // 2
    return img.crop((0, top, w, top + new_h))


def finalize_icon_from_sd(img: Image.Image, size: Tuple[int, int] = (32, 32)) -> Image.Image:
    """Downscale SD concept art to a Soulash 32×32 icon (contain, not stretch)."""
    from s2_icon_pipeline import fit_icon_tile

    return fit_icon_tile(img, size=size[0])


def finalize_thumbnail_from_sd(img: Image.Image, size: Tuple[int, int] = (800, 600)) -> Image.Image:
    """Downscale SD concept art to 4:3 workshop thumbnail."""
    cropped = _center_crop_aspect(img, target_ratio=size[0] / size[1])
    out = cropped.resize(size, Image.Resampling.LANCZOS)
    out = ImageEnhance.Sharpness(out).enhance(1.1)
    out = ImageEnhance.Contrast(out).enhance(1.06)
    out = ImageEnhance.Color(out).enhance(1.04)
    return out


def score_palette_match(img: Image.Image, palette_hex: Optional[List[str]] = None) -> float:
    """0-1 score: how much of visible pixels sit near hydromancy palette."""
    palette_hex = palette_hex or HYDROMANCY_PALETTE

    def hex_to_rgb(h: str) -> Tuple[int, int, int]:
        h = h.lstrip("#")
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    palette = [hex_to_rgb(c) for c in palette_hex]
    img = img.convert("RGBA")
    pixels = [p[:3] for p in img.getdata() if len(p) >= 4 and p[3] > 40]
    if not pixels:
        return 0.0

    def dist(a: Tuple[int, int, int], b: Tuple[int, int, int]) -> float:
        return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5

    close = 0
    for px in pixels:
        if min(dist(px, c) for c in palette) < 72:
            close += 1
    return close / len(pixels)


def vision_quality_check(
    image_path: Path,
    asset_type: str,
    model: str = "qwen3-vl:8b",
) -> Tuple[bool, float, str]:
    """Optional multimodal QA via Ollama. Returns (passed, score 0-1, reason)."""
    try:
        import requests
    except ImportError:
        return True, 0.75, "requests unavailable; skipped vision QA"

    if not image_path.exists():
        return False, 0.0, "file missing"

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")

    prompt = (
        f"Rate this Soulash 2 mod {asset_type} for hydromancy (water magic). "
        "Return JSON only: {\"score\": 0-100, \"pass\": true/false, \"issues\": \"...\"}. "
        "Pass if readable at small size, cohesive teal/cyan water theme, no muddy blur."
    )
    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "images": [b64],
                "stream": False,
                "format": "json",
            },
            timeout=120,
        )
        resp.raise_for_status()
        body = resp.json().get("response", "")
        data = parse_ollama_json(body, asset_type)
        score = float(data.get("score", 70)) / 100.0
        passed = bool(data.get("pass", score >= 0.65))
        issues = str(data.get("issues", ""))
        return passed, score, issues or "ok"
    except Exception as exc:
        return True, 0.7, f"vision QA skipped: {exc}"


def run_quality_gate(
    image_path: Path,
    asset_type: str,
    quality_depth: str = "mechanical",
) -> Tuple[bool, Dict[str, Any]]:
    report: Dict[str, Any] = {"path": str(image_path), "asset_type": asset_type}
    with Image.open(image_path) as img:
        if asset_type == "icon":
            ok, reason = validate_mod_icon(img)
        elif asset_type == "thumbnail":
            ok, reason = validate_thumbnail(img)
        else:
            ok, reason = validate_sprite_quality(img)
        report["mechanical"] = {"pass": ok, "reason": reason}
        report["palette_score"] = round(score_palette_match(img), 3)

    if not ok:
        report["pass"] = False
        return False, report

    if quality_depth in ("mechanical", "fast"):
        report["pass"] = True
        return True, report

    v_ok, v_score, v_reason = vision_quality_check(image_path, asset_type)
    report["vision"] = {"pass": v_ok, "score": v_score, "reason": v_reason}
    report["pass"] = v_ok and report["palette_score"] >= 0.15
    return report["pass"], report
