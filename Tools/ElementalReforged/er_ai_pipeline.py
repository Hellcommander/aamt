#!/usr/bin/env python3
"""
AI asset pipeline for Elemental Reforged monster gear.

Uses AAMT Shared tools:
  - ollama_integration.py  → prompt enhancement
  - sd_http_client.py      → Stable Diffusion 3.5 image generation
  - ImageMagick (magick)   → icon resize / cleanup
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent
SHARED = ROOT.parent / "Shared"
TOOLS = ROOT.parent

if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

# ---- optional Shared imports ----
try:
    from ollama_integration import call_ollama, test_ollama_connection

    OLLAMA_OK = True
except Exception:
    OLLAMA_OK = False
    call_ollama = None  # type: ignore
    test_ollama_connection = None  # type: ignore

try:
    from sd_http_client import detect_server, generate_image, plan_sd_size

    SD_OK = True
except Exception:
    SD_OK = False
    detect_server = None  # type: ignore
    generate_image = None  # type: ignore
    plan_sd_size = None  # type: ignore

# Cross-process GPU turn-taking (shared with SD): see Tools\Common\gpu_hub.py.
try:
    from gpu_hub import acquire_gpu
except Exception:  # hub is optional — never block generation on its absence
    import contextlib

    def acquire_gpu(label, timeout=None, poll=2.0, enabled=True):  # type: ignore
        return contextlib.nullcontext()


def sd_plan(delivery_w: int, delivery_h: int, kind: str) -> tuple[int, int, int]:
    """Right-sized SD dims/steps for a delivery target (fallback if client missing)."""
    if plan_sd_size:
        return plan_sd_size(delivery_w, delivery_h, kind)
    return 512, 512, 24

try:
    from PIL import Image, ImageOps, ImageEnhance, ImageFilter

    PIL_OK = True
except Exception:
    PIL_OK = False
    Image = None  # type: ignore
    ImageEnhance = None  # type: ignore
    ImageFilter = None  # type: ignore


# ---------------------------------------------------------------------------
# CLIP token budgeting (shared by icon/texture/weapon and banner backends)
#
# SD3.5's CLIP encoders hard-cap at 77 tokens (incl. ~2 special tokens). Anything
# past that is silently truncated by the model, which historically dropped the
# "no text / no watermark" tail of prompts. We fit to 72 content tokens and
# front-load the constraints so they always survive.
# ---------------------------------------------------------------------------
CLIP_TOKEN_BUDGET = 72

_clip_tokenizer = None
_clip_tokenizer_failed = False


def _get_clip_tokenizer():
    """Prefer the real CLIP tokenizer SD3.5 uses; fall back to a heuristic."""
    global _clip_tokenizer, _clip_tokenizer_failed
    if _clip_tokenizer is not None or _clip_tokenizer_failed:
        return _clip_tokenizer
    try:
        from transformers import CLIPTokenizer

        _clip_tokenizer = CLIPTokenizer.from_pretrained(
            "openai/clip-vit-large-patch14",
            local_files_only=False,
        )
        return _clip_tokenizer
    except Exception as exc:
        print(f"[CLIP] tokenizer unavailable ({exc}); using estimate", flush=True)
        _clip_tokenizer_failed = True
        return None


def estimate_clip_tokens(text: str) -> int:
    """Exact CLIP token count when the tokenizer is available (no special tokens)."""
    tok = _get_clip_tokenizer()
    if tok is not None:
        return len(tok.encode(text, add_special_tokens=False))
    import re

    parts = re.findall(r"[A-Za-z0-9]+|[^A-Za-z0-9\s]", text)
    return max(1, int(len(parts) * 1.35) + 2)


def clip_fit_prompt(text: str, budget: int = CLIP_TOKEN_BUDGET) -> str:
    """Trim to the front of the prompt so CLIP never truncates critical tokens."""
    text = " ".join(text.replace("\u2014", ",").replace("\u2013", "-").split())
    if estimate_clip_tokens(text) <= budget:
        return text
    chunks = [c.strip() for c in text.split(",") if c.strip()]
    kept: list[str] = []
    for chunk in chunks:
        trial = ", ".join(kept + [chunk]) if kept else chunk
        if estimate_clip_tokens(trial) > budget:
            break
        kept.append(chunk)
    if kept:
        return ", ".join(kept)
    out: list[str] = []
    for w in text.split():
        trial = " ".join(out + [w])
        if estimate_clip_tokens(trial) > budget:
            break
        out.append(w)
    return " ".join(out)


KNOWN_MAGICK = [
    Path(r"E:\tools\ImageMagick\magick.exe"),
    Path(r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"),
    Path(r"C:\Program Files\ImageMagick-7.1.1-Q16\magick.exe"),
]


def find_magick() -> Optional[Path]:
    which = shutil.which("magick")
    if which:
        return Path(which)
    for p in KNOWN_MAGICK:
        if p.is_file():
            return p
    return None


def find_blender(cfg: Optional[dict[str, Any]] = None) -> Optional[Path]:
    if cfg:
        raw = cfg.get("blenderPath")
        if raw and Path(raw).is_file():
            return Path(raw)
    try:
        shared = Path(__file__).resolve().parents[1] / "Shared"
        if str(shared) not in sys.path:
            sys.path.insert(0, str(shared))
        from tool_paths import find_blender as _tp_find

        hit = _tp_find()
        if hit:
            return Path(hit)
    except Exception:
        pass
    which = shutil.which("blender")
    return Path(which) if which else None


def _tcp_open(host: str, port: int, timeout: float = 0.5) -> bool:
    import socket

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def probe_tools(
    start_sd: bool = False,
    wait_sd_sec: float = 120.0,
    cfg: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Return availability snapshot for doctor / generate."""
    ollama = False
    if OLLAMA_OK and test_ollama_connection:
        try:
            # Fast path: tags endpoint before full Shared probe
            import urllib.request

            urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2)
            ollama = True
        except Exception:
            try:
                ollama = bool(test_ollama_connection())
            except Exception:
                ollama = False

    sd_url = None
    if _tcp_open("127.0.0.1", 1338):
        if SD_OK and detect_server:
            try:
                sd_url = detect_server(verbose=False)
            except Exception:
                sd_url = "http://127.0.0.1:1338/v1/images/generations"
        else:
            sd_url = "http://127.0.0.1:1338/v1/images/generations"
    elif SD_OK and detect_server:
        try:
            sd_url = detect_server(verbose=False)
        except Exception:
            sd_url = None

    if start_sd and not sd_url:
        started = start_sd_server(wait_sec=wait_sd_sec)
        if started:
            if SD_OK and detect_server:
                try:
                    sd_url = detect_server(verbose=False)
                except Exception:
                    sd_url = None
            if not sd_url and _tcp_open("127.0.0.1", 1338, timeout=1.0):
                sd_url = "http://127.0.0.1:1338/v1/images/generations"

    magick = find_magick()
    blender = find_blender(cfg)
    havok: dict[str, Any] = {}
    softimage: dict[str, Any] = {}
    try:
        from er_havok import probe_havok

        havok = probe_havok(cfg)
    except Exception as exc:
        havok = {"ok": False, "notes": [str(exc)]}
    try:
        from er_softimage import probe_softimage

        softimage = probe_softimage(cfg)
    except Exception as exc:
        softimage = {"ok": False, "notes": [str(exc)]}

    return {
        "ollama": ollama,
        "sd": bool(sd_url),
        "sd_url": sd_url,
        "magick": str(magick) if magick else None,
        "blender": str(blender) if blender else None,
        "havok": havok,
        "softimage": softimage,
        "pillow": PIL_OK,
        "shared": SHARED.is_dir(),
    }


def start_sd_server(wait_sec: float = 90.0) -> bool:
    """Launch Start-StableDiffusionServer.ps1 if SD is down."""
    ps1 = TOOLS / "Start-StableDiffusionServer.ps1"
    bat = TOOLS / "Start-StableDiffusionServer.bat"
    if not ps1.exists() and not bat.exists():
        print("[WARN] Start-StableDiffusionServer script not found", file=sys.stderr)
        return False

    print("[AI] Starting Stable Diffusion server...", flush=True)
    # Detach the launcher from our console: otherwise the SD server inherits
    # this tool's console and dies when that console closes (e.g. a wrapping
    # batch file's "Press any key to continue" being dismissed) or when
    # Ctrl+C is sent to this tool.
    creationflags = 0
    if sys.platform == "win32":
        # BREAKAWAY so the SD launcher/server are not killed when this tool's
        # job/console ends. Do not TerminateProcess on wait_sec timeout.
        creationflags = (
            subprocess.CREATE_NO_WINDOW
            | subprocess.CREATE_NEW_PROCESS_GROUP
            | getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0x01000000)
        )
    try:
        if ps1.exists():
            subprocess.Popen(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(ps1),
                ],
                cwd=str(TOOLS),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
        else:
            subprocess.Popen(
                ["cmd", "/c", str(bat)],
                cwd=str(TOOLS),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
    except Exception as exc:
        print(f"[WARN] Failed to launch SD server: {exc}", file=sys.stderr)
        return False

    deadline = time.time() + wait_sec
    while time.time() < deadline:
        if SD_OK and detect_server:
            try:
                url = detect_server(verbose=False)
                if url:
                    print(f"[AI] SD ready: {url}", flush=True)
                    return True
            except Exception:
                pass
        time.sleep(3.0)
    print("[WARN] SD server did not become ready in time", file=sys.stderr)
    return False


def base_prompt(kind: str, race: dict[str, Any], pack: dict[str, Any]) -> str:
    """
    CLIP-safe prompt. 'no text/no logo/no watermark' is front-loaded so SD3.5's
    77-token CLIP cap can never truncate the constraint (the old failure mode).
    Detail after the constraints is carried by the T5 encoder server-side.
    """
    theme = race.get("theme") or race.get("display") or "fantasy monster"
    name = pack.get("itemName") or kind
    display = race.get("display") or "monster"
    if kind == "texture":
        prompt = (
            f"no text, no logo, no watermark, seamless tileable fantasy material texture, "
            f"{theme}, armor surface for {display} {name}, "
            f"fabric metal scale weave, team-color friendly midtones, top-down flat lighting, "
            f"Fallen Enchantress / Elemental aesthetic, high detail, physically based"
        )
        return clip_fit_prompt(prompt)
    if kind == "weapon":
        prompt = (
            f"no text, no logo, no watermark, game item icon, centered {name}, "
            f"single weapon on dark background, {theme}, for {display}, "
            f"clean crisp silhouette, rim light, painterly Elemental Reforged UI icon, sharp detail"
        )
        return clip_fit_prompt(prompt)
    # clothes / armor icons
    prompt = (
        f"no text, no logo, no watermark, fantasy game item icon, centered {name}, "
        f"{kind} worn by {display}, {theme}, single object on dark background, "
        f"clean silhouette, rim light, painterly Elemental / Fallen Enchantress UI icon, sharp detail"
    )
    return clip_fit_prompt(prompt)


def enhance_prompt_with_ollama(prompt: str, kind: str, timeout_sec: float = 45.0) -> str:
    """Fast Ollama enhance via /api/generate (avoids heavy Shared model-swap hangs)."""
    import urllib.error
    import urllib.request

    # Prefer models the user actually has (visual-capable first)
    models = [
        "llama3.1:8b",
        "wizardlm-uncensored:latest",
        "deepseek-r1:7b",
        "qwen2.5-coder:7b",
        "llama3.2:1b",
        "qwen2.5:1.5b",
        "mistral:7b",
    ]
    # Discover installed tags quickly
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3) as resp:
            tags = json.loads(resp.read().decode("utf-8")).get("models") or []
            names = [m.get("name", "") for m in tags]
    except Exception:
        names = []

    model = next((m for m in models if any(m in n or n.startswith(m.split(":")[0]) for n in names)), None)
    if not model and names:
        model = names[0]
    if not model:
        print("  [Ollama] no models found — using base prompt", flush=True)
        return prompt

    instruction = (
        f"Rewrite this Elemental Reforged {kind} prompt for SD3.5. "
        f"HARD LIMIT: 45 words. Start with: no text, no logo, no watermark. "
        f"Then the subject and lighting. Keep dark fantasy. Return ONLY the prompt.\n\n{prompt}"
    )
    # num_gpu=0: SD3.5 owns most of the 11GB 2080 Ti; run Ollama on CPU.
    # num_ctx=4096: small context keeps RAM estimate under free memory.
    options = {"num_predict": 90, "temperature": 0.6, "num_gpu": 0, "num_ctx": 4096}
    body = json.dumps(
        {
            "model": model,
            "prompt": instruction,
            "stream": False,
            "options": options,
        }
    ).encode("utf-8")

    print(f"  [Ollama] enhance via {model}...", flush=True)
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # GPU turn-taking: CPU-only calls (num_gpu=0) skip the shared lock.
        with acquire_gpu(f"Ollama enhance {model}", enabled=options.get("num_gpu") != 0):
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        text = (data.get("response") or "").strip().strip('"').strip("'")
        for prefix in ("Enhanced prompt:", "Prompt:", "Here is"):
            if text.lower().startswith(prefix.lower()):
                text = text.split(":", 1)[-1].strip()
        if len(text) > 20:
            fitted = clip_fit_prompt(text)
            print(f"  [Ollama] ok (~{estimate_clip_tokens(fitted)} CLIP tokens)", flush=True)
            return fitted
    except Exception as exc:
        print(f"  [Ollama] enhance skipped: {exc}", flush=True)
    return clip_fit_prompt(prompt)


def _polish_icon_rgb(im: "Image.Image") -> "Image.Image":
    """Icon/weapon polish: small readable UI art benefits from crisp edges + pop."""
    if ImageEnhance is None or ImageFilter is None:
        return im
    im = ImageEnhance.Contrast(im).enhance(1.08)
    im = ImageEnhance.Color(im).enhance(1.06)
    im = im.filter(ImageFilter.UnsharpMask(radius=1.1, percent=110, threshold=2))
    return im


def _polish_texture_rgb(im: "Image.Image") -> "Image.Image":
    """
    Texture polish is deliberately gentle: material maps must stay flat, neutral,
    and tileable. No contrast/histogram stretch (shifts tiling color + seams),
    no saturation bump (breaks team-color midtones) — only a whisper of sharpen.
    """
    if ImageFilter is None:
        return im
    return im.filter(ImageFilter.UnsharpMask(radius=1.0, percent=55, threshold=3))


def postprocess_icon(path: Path, size: int = 128) -> bool:
    """
    High-quality downscale to the UI icon size. Generating at 512 and Lanczos-
    downsampling to 128 supersamples away SD noise; unsharp restores crispness.
    Alpha is preserved (PNG32) for transparent-friendly icons.
    """
    magick = find_magick()
    if magick:
        tmp = path.with_suffix(".tmp.png")
        try:
            subprocess.run(
                [
                    str(magick),
                    str(path),
                    "-colorspace",
                    "sRGB",
                    "-filter",
                    "Lanczos",
                    "-resize",
                    f"{size}x{size}>",
                    "-background",
                    "none",
                    "-gravity",
                    "center",
                    "-extent",
                    f"{size}x{size}",
                    "-unsharp",
                    "0x0.8+0.7+0.02",
                    "-modulate",
                    "100,106,100",
                    "PNG32:" + str(tmp),
                ],
                check=True,
                capture_output=True,
            )
            if tmp.exists():
                tmp.replace(path)
                return True
        except Exception as exc:
            print(f"[WARN] ImageMagick failed: {exc}", file=sys.stderr)
            if tmp.exists():
                tmp.unlink(missing_ok=True)

    if PIL_OK and Image:
        try:
            im = Image.open(path).convert("RGBA")
            im.thumbnail((size, size), Image.Resampling.LANCZOS)
            # Polish RGB, then re-attach the (downscaled) alpha channel.
            alpha = im.split()[-1]
            rgb = _polish_rgb(im.convert("RGB")).convert("RGBA")
            rgb.putalpha(alpha)
            canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            canvas.paste(rgb, ((size - rgb.size[0]) // 2, (size - rgb.size[1]) // 2))
            canvas.save(path)
            return True
        except Exception as exc:
            print(f"[WARN] Pillow postprocess failed: {exc}", file=sys.stderr)
    return False


def postprocess_texture(path: Path, size: int = 512) -> bool:
    """Square, sRGB, Lanczos-scaled material texture with a gentle sharpen/contrast."""
    magick = find_magick()
    if magick:
        tmp = path.with_suffix(".tmp.png")
        try:
            subprocess.run(
                [
                    str(magick),
                    str(path),
                    "-colorspace",
                    "sRGB",
                    "-filter",
                    "Lanczos",
                    "-resize",
                    f"{size}x{size}!",
                    "-unsharp",
                    "0x0.7+0.6+0.02",
                    "-contrast-stretch",
                    "0.2%x0.2%",
                    str(tmp),
                ],
                check=True,
                capture_output=True,
            )
            if tmp.exists():
                tmp.replace(path)
                return True
        except Exception as exc:
            print(f"[WARN] ImageMagick texture failed: {exc}", file=sys.stderr)
            if tmp.exists():
                tmp.unlink(missing_ok=True)

    if PIL_OK and Image:
        try:
            im = Image.open(path).convert("RGB")
            im = im.resize((size, size), Image.Resampling.LANCZOS)
            im = _polish_rgb(im)
            im.save(path)
            return True
        except Exception:
            return False
    return False


def generate_ai_image(
    *,
    prompt: str,
    output: Path,
    negative: str,
    width: int,
    height: int,
    steps: int,
    seed: int,
    api_url: Optional[str] = None,
    enhance: bool = True,
    kind: str = "icon",
    guidance_scale: float = 7.0,
) -> bool:
    """Enhance prompt (Ollama) + generate (SD) + postprocess (ImageMagick/Pillow)."""
    final_prompt = enhance_prompt_with_ollama(prompt, kind) if enhance else prompt
    if final_prompt != prompt:
        print(f"  [Ollama] using enhanced prompt", flush=True)

    # Final safety: never send >72 CLIP tokens (banner backend does the same).
    final_prompt = clip_fit_prompt(final_prompt)
    negative = clip_fit_prompt(negative) if negative else negative

    if not (SD_OK and generate_image):
        print("  [SD] client unavailable", file=sys.stderr)
        return False

    output.parent.mkdir(parents=True, exist_ok=True)
    ai_raw = output.with_name(output.stem + "_AI_raw.png")
    print(
        f"  [SD] generating {width}x{height} @ {steps} steps "
        f"cfg={guidance_scale} (~{estimate_clip_tokens(final_prompt)} CLIP tok) -> {ai_raw.name} ...",
        flush=True,
    )
    try:
        generate_image(
            prompt=final_prompt,
            output_path=ai_raw,
            api_url=api_url,
            negative_prompt=negative,
            width=width,
            height=height,
            steps=steps,
            guidance_scale=guidance_scale,
            seed=seed or 0,
        )
    except Exception as exc:
        print(f"  [SD] failed: {exc}", file=sys.stderr, flush=True)
        return False

    if not ai_raw.exists():
        return False

    print(f"  [SD] ok, postprocessing...", flush=True)
    shutil.copy2(ai_raw, output)
    if kind == "texture":
        postprocess_texture(output, size=min(width, height, 512))
    elif kind == "banner":
        # Workshop banner crop/resize is handled by er_banner.postprocess_banner.
        pass
    else:
        postprocess_icon(output, size=128)
    return output.exists()


def ai_assets_for_item(
    *,
    cfg: dict[str, Any],
    race: dict[str, Any],
    kind: str,
    pack: dict[str, Any],
    icon_path: Path,
    texture_path: Path,
    source_dir: Path,
    tools: dict[str, Any],
    enhance: bool = True,
    force: bool = False,
    steps: int = 28,
    gen_icon: bool = True,
    gen_texture: bool = True,
) -> dict[str, Any]:
    """Generate AI icon and/or texture for one gear item. Falls back silently."""
    negative = cfg.get("negativePrompt") or (
        "blurry, low quality, watermark, text, logo, photograph, modern clothing"
    )
    seed = sum(ord(c) for c in (pack.get("itemName") or kind)) % 100000
    result = {"icon": False, "texture": False, "prompt_icon": "", "prompt_tex": ""}

    if not tools.get("sd"):
        return result

    api = tools.get("sd_url")
    source_dir.mkdir(parents=True, exist_ok=True)

    if gen_icon:
        prompt = base_prompt(kind if kind != "armor" else "armor", race, pack)
        result["prompt_icon"] = prompt
        out = Path(icon_path)
        ai_copy = source_dir / (out.stem + "_AI.png")
        # Icons deliver at 128x128 — plan the smallest SD-friendly size (512
        # short-side floor) instead of oversizing.
        icon_w, icon_h, icon_steps = sd_plan(128, 128, "icon")
        ok = generate_ai_image(
            prompt=prompt,
            output=ai_copy,
            negative=negative,
            width=icon_w,
            height=icon_h,
            steps=min(steps, icon_steps) if steps else icon_steps,
            seed=seed,
            api_url=api,
            enhance=enhance,
            kind="icon" if kind != "weapon" else "weapon",
        )
        if ok:
            shutil.copy2(ai_copy, out)
            result["icon"] = True

    if gen_texture and kind in ("clothes", "armor"):
        prompt = base_prompt("texture", race, pack)
        result["prompt_tex"] = prompt
        out = Path(texture_path)
        ai_copy = source_dir / (out.stem + "_AI.png")
        # Material textures deliver at 512 — generate at delivery size directly.
        tex_w, tex_h, _tex_steps = sd_plan(512, 512, "texture")
        ok = generate_ai_image(
            prompt=prompt,
            output=ai_copy,
            negative=negative,
            width=tex_w,
            height=tex_h,
            steps=max(20, steps - 4),
            seed=seed + 17,
            api_url=api,
            enhance=enhance,
            kind="texture",
        )
        if ok:
            shutil.copy2(ai_copy, out)
            result["texture"] = True

    return result


if __name__ == "__main__":
    # quick self-check
    info = probe_tools(start_sd=False)
    print(json.dumps(info, indent=2))
