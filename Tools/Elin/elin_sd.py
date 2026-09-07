#!/usr/bin/env python3
"""
Local Stable Diffusion backend for Elin assets (optional, with procedural fallback).

The Elin generators (generate_asset_image.py) render everything procedurally from
Ollama-authored specs. That is reliable and offline, but the local SD3.5 server
produces far richer icons/sprites/textures with no cloud cost and no censorship.

This module bridges the two: when an SD server is reachable it renders the asset
from the spec, converts it to the shape Elin/Unity expects (RGBA cut-out sprites,
RGB tileable textures), and returns it. On ANY failure - server down, timeout,
bad cut-out, failed QA - the caller transparently falls back to the existing
procedural pipeline, so behaviour is never worse than before.

Enable/disable and tune entirely via env (so the PowerShell orchestrators need no
changes):
    ELIN_SD            auto|on|off   use SD if server up / require it / never (default auto)
    ELIN_SD_API_URL    explicit server URL (else auto-detect)
    ELIN_SD_QUALITY    draft|standard|high|ultra   sampling budget (default standard)
    ELIN_SD_STEPS      override sampling steps
    ELIN_SD_GUIDANCE   override guidance scale
    ELIN_SD_MIN_GEN    minimum generation size before downscale (default 512)
    ELIN_SD_MAX_GEN    generation size cap (default 1024)
    SD_TEXTURE_CONCURRENCY  max concurrent SD calls (server serializes) (default 1)
"""

from __future__ import annotations

import os
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
    _PIL_OK = True
except Exception:
    _PIL_OK = False

# The Shared SD client lives one level up (Tools/Shared). generate_asset_image.py
# already puts it on sys.path, but import defensively so this module is usable
# standalone too.
_SD_OK = False
try:
    _shared = Path(__file__).resolve().parent.parent / "Shared"
    if str(_shared) not in sys.path:
        sys.path.insert(0, str(_shared))
    from sd_http_client import detect_server, generate_image  # type: ignore
    _SD_OK = True
except Exception:
    detect_server = None  # type: ignore
    generate_image = None  # type: ignore

# Sampling budgets. Icons downscale from a larger render so even 32px sprites get
# real detail; textures stay VRAM/time friendly by default.
_QUALITY = {
    "draft":    {"steps": 18, "guidance": 6.5},
    "standard": {"steps": 26, "guidance": 7.0},
    "high":     {"steps": 32, "guidance": 7.0},
    "ultra":    {"steps": 40, "guidance": 7.5},
}

# Server serializes on one GPU; cap concurrent calls so batch runs don't hold
# dozens of sockets open against it.
_SD_SEMAPHORE = threading.Semaphore(max(1, int(os.environ.get("SD_TEXTURE_CONCURRENCY", "1"))))

_server_cache: Optional[str] = None
_server_probed = False


def _mode() -> str:
    return (os.environ.get("ELIN_SD", "auto") or "auto").strip().lower()


def sd_enabled() -> bool:
    """True if SD should be attempted (server reachable, unless mode forces it)."""
    if not (_PIL_OK and _SD_OK and generate_image):
        return _mode() == "on"  # 'on' will surface a clear error later
    if _mode() == "off":
        return False
    return _resolve_server() is not None or _mode() == "on"


def _resolve_server() -> Optional[str]:
    global _server_cache, _server_probed
    explicit = os.environ.get("ELIN_SD_API_URL")
    if explicit:
        return explicit
    if _server_probed:
        return _server_cache
    _server_probed = True
    try:
        _server_cache = detect_server() if detect_server else None
    except Exception:
        _server_cache = None
    return _server_cache


def _quality() -> Dict[str, float]:
    q = (os.environ.get("ELIN_SD_QUALITY", "standard") or "standard").strip().lower()
    base = dict(_QUALITY.get(q, _QUALITY["standard"]))
    if os.environ.get("ELIN_SD_STEPS"):
        try:
            base["steps"] = int(os.environ["ELIN_SD_STEPS"])
        except ValueError:
            pass
    if os.environ.get("ELIN_SD_GUIDANCE"):
        try:
            base["guidance"] = float(os.environ["ELIN_SD_GUIDANCE"])
        except ValueError:
            pass
    return base


def _snap16(n: int) -> int:
    return max(256, int(round(n / 16.0)) * 16)


def _gen_size(target: int) -> int:
    """SD render size for a target: upscale tiny icons, cap large ones."""
    lo = int(os.environ.get("ELIN_SD_MIN_GEN", "512"))
    hi = int(os.environ.get("ELIN_SD_MAX_GEN", "1024"))
    return _snap16(max(lo, min(hi, target if target >= lo else lo)))


# ---------------------------------------------------------------------------
# Prompt construction from an Ollama/Elin spec.
# ---------------------------------------------------------------------------

def _spec_text(spec: Dict[str, Any], *keys: str) -> str:
    out = []
    for k in keys:
        v = spec.get(k)
        if isinstance(v, (list, tuple)):
            out.extend(str(x) for x in v if x)
        elif v:
            out.append(str(v))
    return ", ".join(dict.fromkeys(out))  # de-dupe, preserve order


def _palette_hint(spec: Dict[str, Any]) -> str:
    raw = spec.get("palette") or spec.get("colors") or []
    hexes = [c for c in raw if isinstance(c, str)][:4]
    return ", ".join(hexes)


_NOUN = {"icon": "item icon", "sprite": "sprite", "spell_asset": "spell effect icon",
         "spellassets": "spell effect icon", "texture": "texture"}


def build_prompt(asset_type: str, spec: Dict[str, Any]) -> Tuple[str, str]:
    """Return (prompt, negative_prompt) tuned to the asset type."""
    noun = _NOUN.get(asset_type, "item icon")
    theme = _spec_text(spec, "theme", "system", "element", "motif", "shape", "details")
    style = str(spec.get("style", "stylized")).lower()
    effects = _spec_text(spec, "effects", "lighting")
    desc = str(spec.get("description", "")).strip()
    colors = _palette_hint(spec)

    is_texture = asset_type == "texture"
    if is_texture:
        pattern = str(spec.get("pattern", "organic")).lower()
        prompt = (
            f"no text, no logo, no watermark, seamless tileable game texture, "
            f"{pattern} {theme}, {desc}, colors {colors}, {style}, "
            f"even flat lighting, top-down, PBR base color map, high detail"
        )
        negative = (
            "text, logo, watermark, letters, ui, frame, border, seams, "
            "harsh shadows, directional light, vignette, single object, "
            "blurry, lowres, jpeg artifacts, photograph"
        )
    else:
        # icon / sprite / spell_asset -> single centered object we can cut out.
        prompt = (
            f"no text, no logo, no watermark, fantasy game {noun}, "
            f"single centered {theme}, {desc}, colors {colors}, {style}, "
            f"{effects}, clean crisp silhouette, rim light, on flat matte black "
            f"background, high detail, sharp"
        )
        negative = (
            "text, logo, watermark, letters, ui, multiple objects, scene, "
            "landscape, cluttered background, gradient background, tiled, "
            "blurry, lowres, jpeg artifacts, photograph, frame, border"
        )
    # Collapse whitespace / stray commas.
    prompt = ", ".join(p.strip() for p in prompt.split(",") if p.strip())
    return prompt, negative


# ---------------------------------------------------------------------------
# Background removal: SD renders on flat matte black; flood-fill from the
# corners to build an alpha mask so the sprite drops onto transparency for Unity.
# ---------------------------------------------------------------------------

def _cutout_alpha(rgb: "Image.Image", tol: int = 42) -> "Image.Image":
    """RGB (subject on ~black bg) -> RGBA with the background made transparent."""
    w, h = rgb.size
    work = rgb.convert("RGB").copy()
    sentinel = (255, 0, 255)  # magenta marker, unlikely in a matte-black render
    # Flood the connected background region from each corner within a tolerance.
    for corner in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        try:
            ImageDraw.floodfill(work, corner, sentinel, thresh=tol)
        except Exception:
            pass
    src = rgb.convert("RGBA")
    wpx = work.load()
    alpha = Image.new("L", (w, h), 255)
    apx = alpha.load()
    for y in range(h):
        for x in range(w):
            if wpx[x, y] == sentinel:
                apx[x, y] = 0
    # Erode 1px to kill the dark fringe, then feather for clean edges.
    alpha = alpha.filter(ImageFilter.MinFilter(3))
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.6))
    src.putalpha(alpha)
    return src


def _coverage(rgba: "Image.Image") -> float:
    a = rgba.split()[3]
    data = a.getdata()
    if not data:
        return 0.0
    return sum(1 for p in data if p > 24) / len(data)


# ---------------------------------------------------------------------------
# Public entry points (return None to signal "fall back to procedural").
# ---------------------------------------------------------------------------

def _render(prompt: str, negative: str, gen: int, seed: int) -> Optional["Image.Image"]:
    api = _resolve_server()
    if not api and _mode() != "on":
        return None
    q = _quality()
    tmp = Path(tempfile.gettempdir()) / f"elin_sd_{abs(seed) % 10_000_000}_{gen}.png"
    try:
        with _SD_SEMAPHORE:
            generate_image(
                prompt=prompt,
                output_path=tmp,
                api_url=api,
                negative_prompt=negative,
                width=gen,
                height=gen,
                steps=int(q["steps"]),
                guidance_scale=float(q["guidance"]),
                seed=seed,
            )
        if not tmp.exists():
            return None
        img = Image.open(tmp).convert("RGB")
        try:
            tmp.unlink()
        except OSError:
            pass
        return img
    except Exception as exc:
        print(f"  [SD] render failed; using procedural: {exc}", file=sys.stderr)
        return None


def generate_icon_sd(size: int, spec: Dict[str, Any], asset_type: str = "icon",
                     seed: int = 0) -> Optional["Image.Image"]:
    """SD icon/sprite as an RGBA cut-out at `size`, or None to fall back."""
    if not sd_enabled():
        return None
    gen = _gen_size(size)
    prompt, negative = build_prompt(asset_type, spec)
    rgb = _render(prompt, negative, gen, (abs(hash(prompt)) % 100000) + seed + 1)
    if rgb is None:
        return None
    try:
        rgba = _cutout_alpha(rgb)
        cov = _coverage(rgba)
        # Implausible cut-out (empty or full frame) -> let procedural handle it.
        if cov < 0.06 or cov > 0.97:
            print(f"  [SD] icon cut-out coverage {cov:.0%} implausible; procedural fallback",
                  file=sys.stderr)
            return None
        if rgba.size != (size, size):
            rgba = rgba.resize((size, size), Image.Resampling.LANCZOS)
        rgba = ImageEnhance.Sharpness(rgba).enhance(1.1)
        rgba = ImageEnhance.Contrast(rgba).enhance(1.05)
        return rgba
    except Exception as exc:
        print(f"  [SD] icon post-process failed; procedural fallback: {exc}", file=sys.stderr)
        return None


def generate_texture_sd(size: int, spec: Dict[str, Any], seed: int = 0) -> Optional["Image.Image"]:
    """SD tileable RGB texture at `size`, or None to fall back."""
    if not sd_enabled():
        return None
    gen = _gen_size(size)
    prompt, negative = build_prompt("texture", spec)
    rgb = _render(prompt, negative, gen, (abs(hash(prompt)) % 100000) + seed + 7)
    if rgb is None:
        return None
    try:
        if rgb.size != (size, size):
            rgb = rgb.resize((size, size), Image.Resampling.LANCZOS)
        rgb = ImageEnhance.Sharpness(rgb).enhance(1.08)
        rgb = ImageEnhance.Contrast(rgb).enhance(1.04)
        return rgb
    except Exception as exc:
        print(f"  [SD] texture post-process failed; procedural fallback: {exc}", file=sys.stderr)
        return None
