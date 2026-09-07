#!/usr/bin/env python3
"""
ToME real-asset pipeline: Ollama (11434) prompt → SD3.5 (1338) → 64x64 RGBA icon.

Procedural Pillow art is NOT used here. Callers that need a draft when SD is down
should refuse to install into a live mod rather than ship placeholders.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

    _PIL_OK = True
except Exception:
    _PIL_OK = False

_TOOLS = Path(__file__).resolve().parent
_SHARED = _TOOLS.parent / "Shared"
for _p in (_TOOLS, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from tome_sd_client import generate_sd_image, get_sd_api_url  # noqa: E402

call_ollama = None
test_ollama_connection = None
try:
    from ollama_integration import call_ollama, test_ollama_connection  # type: ignore
except Exception:
    pass

TOME_ICON_SIZE = 64
DEFAULT_OLLAMA_MODEL = "wizardlm-uncensored:latest"
NEGATIVE = (
    "text, logo, watermark, letters, ui, frame, border, multiple objects, "
    "scene, landscape, cluttered background, gradient background, photograph, "
    "blurry, lowres, jpeg artifacts, 3d render plastic"
)


def sd_ready() -> bool:
    return get_sd_api_url(verbose=False) is not None


def ollama_ready() -> bool:
    if test_ollama_connection:
        try:
            return bool(test_ollama_connection())
        except Exception:
            return False
    try:
        import urllib.request

        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def _cutout_alpha(rgb: "Image.Image", tol: int = 42) -> "Image.Image":
    w, h = rgb.size
    work = rgb.convert("RGB").copy()
    sentinel = (255, 0, 255)
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
    alpha = alpha.filter(ImageFilter.MinFilter(3))
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.6))
    src.putalpha(alpha)
    return src


def _coverage(rgba: "Image.Image") -> float:
    data = rgba.split()[3].getdata()
    if not data:
        return 0.0
    return sum(1 for p in data if p > 24) / len(data)


def build_fallback_prompt(name: str, kind: str, theme: str, description: str = "") -> str:
    noun = {
        "item": "fantasy RPG item icon",
        "effect": "fantasy RPG status effect icon",
        "talent": "fantasy RPG talent skill icon",
        "vfx": "fantasy RPG spell effect icon",
        "spell": "fantasy RPG spell icon",
    }.get(kind, "fantasy RPG game icon")
    style = {
        "steam": "Tales of Maj'Eyal style, dark fantasy magictech steampunk",
        "arcane": "Tales of Maj'Eyal style, dark fantasy magictech steampunk",
        "dark": "Tales of Maj'Eyal style, twisted eldritch body-horror dark fantasy",
        "horror": "Tales of Maj'Eyal style, twisted eldritch body-horror dark fantasy",
        "acid": "Tales of Maj'Eyal style, corrosive bile-acid body-horror dark fantasy",
        "nature": "Tales of Maj'Eyal style, dark fantasy nature corruption",
        "fire": "Tales of Maj'Eyal style, dark fantasy fire magic",
        "ice": "Tales of Maj'Eyal style, dark fantasy frost magic",
        "lightning": "Tales of Maj'Eyal style, dark fantasy lightning magic",
        "healing": "Tales of Maj'Eyal style, dark fantasy flesh regeneration",
    }.get((theme or "").lower(), "Tales of Maj'Eyal style, dark fantasy")
    bits = [
        "no text, no logo, no watermark",
        noun,
        f"single centered {name.replace('_', ' ')}",
        theme,
        description,
        style,
        "clean crisp silhouette, rim light, on flat matte black background",
        "high detail, sharp, readable at 64 pixels",
    ]
    return ", ".join(b.strip() for b in bits if b and b.strip())


def _ollama_generate_http(
    prompt: str,
    *,
    model: str = DEFAULT_OLLAMA_MODEL,
    system: str = "",
    timeout: float = 45.0,
) -> Optional[str]:
    """
    Lightweight /api/generate call that does NOT take the Shared GPU lock.

    On an 11GB card SD3.5 already owns VRAM; locking + loading WizardLM stalls.
    Use this only when the user opts in (--ollama-prompt) and preferably when
    SD is unloaded. Always keep a short timeout + fallback.
    """
    try:
        import urllib.request

        body = {
            "model": model,
            "prompt": prompt if not system else f"{system}\n\n{prompt}",
            "stream": False,
            "options": {"num_predict": 120, "temperature": 0.7},
        }
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        return (data.get("response") or "").strip() or None
    except Exception as exc:
        print(f"  [WARN] Ollama HTTP prompt failed ({exc})")
        return None


def ollama_prompt_for_asset(
    name: str,
    kind: str,
    theme: str,
    description: str = "",
    *,
    model: str = DEFAULT_OLLAMA_MODEL,
    use_ollama: bool = False,
) -> str:
    """Build an SD prompt. Ollama is opt-in (VRAM contention with SD3.5)."""
    fallback = build_fallback_prompt(name, kind, theme, description)
    if not use_ollama:
        return fallback

    sys_prompt = (
        "You write Stable Diffusion prompts for Tales of Maj'Eyal 64x64 RPG icons. "
        "Return ONLY one prompt line. Require: single centered subject, flat matte "
        "black background, no text/logo/UI. Dark fantasy + steamtech when relevant."
    )
    user = (
        f"Asset name: {name}\nKind: {kind}\nTheme: {theme}\n"
        f"Description: {description or name.replace('_', ' ')}\n"
        "Write one SD prompt under 60 words."
    )
    raw = _ollama_generate_http(user, model=model, system=sys_prompt, timeout=45.0)
    if not raw and call_ollama and ollama_ready():
        # Last resort: Shared helper (takes GPU lock — may stall if SD is resident)
        try:
            raw = call_ollama(
                prompt=user,
                task_type="visual",
                response_length="brief",
                system_prompt=sys_prompt,
                model_name=model,
                verbose=False,
            )
        except Exception as exc:
            print(f"  [WARN] Ollama prompt failed ({exc}); using fallback")
            return fallback

    if not raw:
        return fallback
    line = raw.strip().strip('"').splitlines()[0].strip()
    line = re.sub(r"^(prompt\s*:)\s*", "", line, flags=re.I)
    if len(line) < 20:
        return fallback
    if "black background" not in line.lower():
        line += ", on flat matte black background"
    if "no text" not in line.lower():
        line = "no text, no logo, " + line
    return line


def generate_tome_icon(
    name: str,
    out_path: Path,
    *,
    kind: str = "talent",
    theme: str = "steam",
    description: str = "",
    seed: int = 0,
    size: int = TOME_ICON_SIZE,
    model: str = DEFAULT_OLLAMA_MODEL,
    require_sd: bool = True,
    use_ollama_prompt: bool = False,
) -> Dict[str, Any]:
    """
    Generate one ToME icon PNG via SD3.5 (optional Ollama prompt).
    Returns metadata dict with ok/path/prompt/error.
    """
    if not _PIL_OK:
        return {"ok": False, "error": "Pillow required"}
    if require_sd and not sd_ready():
        return {
            "ok": False,
            "error": "SD server not ready on :1338 — start Tools\\Start-StableDiffusionServer.ps1 (auto-stops when idle)",
        }

    prompt = ollama_prompt_for_asset(
        name, kind, theme, description, model=model, use_ollama=use_ollama_prompt
    )
    print(f"  [prompt] {prompt[:160]}{'...' if len(prompt) > 160 else ''}")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    raw_tmp = Path(tempfile.gettempdir()) / f"tome_sd_{name}_{seed}.png"
    if raw_tmp.exists():
        try:
            raw_tmp.unlink()
        except OSError:
            pass

    result = generate_sd_image(
        prompt,
        raw_tmp,
        negative_prompt=NEGATIVE,
        delivery_w=size,
        delivery_h=size,
        kind="icon",
        seed=seed,
        lock_label=f"tome_{name}",
    )
    if not result.ok or not result.output_path:
        return {
            "ok": False,
            "error": result.error or "SD generate failed",
            "prompt": prompt,
            "settings": result.settings,
        }

    try:
        rgb = Image.open(result.output_path).convert("RGB")
        rgba = _cutout_alpha(rgb)
        cov = _coverage(rgba)
        if cov < 0.06 or cov > 0.97:
            return {
                "ok": False,
                "error": f"cut-out coverage implausible ({cov:.0%})",
                "prompt": prompt,
            }
        if rgba.size != (size, size):
            rgba = rgba.resize((size, size), Image.Resampling.LANCZOS)
        rgba = ImageEnhance.Sharpness(rgba).enhance(1.1)
        rgba = ImageEnhance.Contrast(rgba).enhance(1.05)
        rgba.save(out_path)
    except Exception as exc:
        return {"ok": False, "error": f"post-process failed: {exc}", "prompt": prompt}
    finally:
        try:
            if raw_tmp.exists():
                raw_tmp.unlink()
        except OSError:
            pass

    meta = {
        "ok": True,
        "path": str(out_path),
        "prompt": prompt,
        "negative": NEGATIVE,
        "seed": seed,
        "size": size,
        "kind": kind,
        "theme": theme,
        "settings": result.settings,
        "pipeline": "ollama+sd3.5",
    }
    meta_path = out_path.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def generate_tome_icon_pair(
    name: str,
    out_dir: Path,
    **kwargs: Any,
) -> Tuple[Optional[Path], Dict[str, Any]]:
    out_dir = Path(out_dir)
    out_path = out_dir / f"{name}.png"
    meta = generate_tome_icon(name, out_path, **kwargs)
    return (out_path if meta.get("ok") else None, meta)
