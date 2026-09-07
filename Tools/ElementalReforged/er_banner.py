#!/usr/bin/env python3
"""
Mod Manager banner art for LH_Legacy_Expansion.

Local AAMT only (no Cursor image credits / no hosted filters):
  Ollama (banner enhance) -> Stable Diffusion (high-res) -> quality downscale

Workshop delivery size is 512x439; we generate much larger then Lanczos+unsharp
downscale so the Mod Manager thumbnail keeps detail comparable to Cursor's tool.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

from er_ai_pipeline import (
    CLIP_TOKEN_BUDGET,
    acquire_gpu,
    clip_fit_prompt,
    estimate_clip_tokens,
    find_magick,
    generate_ai_image,
    probe_tools,
)

try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

    PIL_OK = True
except Exception:
    PIL_OK = False
    Image = None  # type: ignore

ROOT = Path(__file__).resolve().parent

# Elemental Reforged workshop banner size (Dogmar / Undead DLC / etc.)
DEFAULT_BANNER_W = 512
DEFAULT_BANNER_H = 439
# Right-sized SD frame: ~1.5x supersample over 512x439 delivery, multiples of
# 64, near the 512:439 aspect (~1.166). 768x640 cuts generation time roughly
# in half vs the old 1024x896 (and ~3x vs 1344x1152) with no visible loss
# after the Lanczos+unsharp downscale to 512x439.
DEFAULT_GEN_W = 768
DEFAULT_GEN_H = 640
DEFAULT_STEPS = 40
DEFAULT_GUIDANCE = 7.5
# CLIP token budgeting lives in er_ai_pipeline (shared with icon/texture backends).


def package_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    pkg = dict(cfg.get("modPackage") or {})
    pkg.setdefault("folderName", "LH_Legacy_Expansion")
    pkg.setdefault("title", "LH Legacy Expansion")
    pkg.setdefault("author", "Local")
    pkg.setdefault(
        "description",
        "Exotic races, designer options, mounts, and monster clothes/armor/"
        "weapon packs for Elemental Reforged. Prefix LHL_. Compatible with "
        "DEAD/Q&L undead mods.",
    )
    pkg.setdefault("bannerFile", "LH_Legacy_Banner.png")
    pkg.setdefault("bannerWidth", DEFAULT_BANNER_W)
    pkg.setdefault("bannerHeight", DEFAULT_BANNER_H)
    pkg.setdefault("genWidth", DEFAULT_GEN_W)
    pkg.setdefault("genHeight", DEFAULT_GEN_H)
    pkg.setdefault("bannerSteps", DEFAULT_STEPS)
    pkg.setdefault("bannerGuidance", DEFAULT_GUIDANCE)
    return pkg


def race_cast_line(cfg: dict[str, Any], limit: int = 3) -> str:
    names: list[str] = []
    for race in (cfg.get("races") or {}).values():
        display = (race.get("display") or "").strip()
        if display and display not in names:
            names.append(display)
        if len(names) >= limit:
            break
    if not names:
        return "monsters"
    return ", ".join(names)


def build_banner_prompt(cfg: dict[str, Any], override: str | None = None) -> str:
    """
    CLIP-safe banner prompt. Put subjects + no-text FIRST so CLIP truncation
    cannot drop the 'no text/logo' constraint (that was the 115>77 failure mode).
    """
    pkg = package_cfg(cfg)
    if override:
        return clip_fit_prompt(override.strip())
    if pkg.get("bannerPrompt"):
        return clip_fit_prompt(str(pkg["bannerPrompt"]).strip())

    cast = race_cast_line(cfg, limit=3)
    # Order matters: CLIP keeps the front. no-text early; lighting last.
    prompt = (
        f"cinematic fantasy banner, no text, no logo, no watermark, "
        f"{cast}, horned demon, stone golem, armored warg, darkling mist, "
        f"ruined towers, violet amber storm sky, torchlight, dramatic lighting, "
        f"painterly concept art, sharp detail"
    )
    return clip_fit_prompt(prompt)


def banner_negative(cfg: dict[str, Any]) -> str:
    # Short negative — CLIP truncates this too.
    return clip_fit_prompt(
        "blurry, low quality, text, logo, watermark, letters, UI, collage, "
        "panels, bad anatomy, extra limbs, lowres, plastic, child, chibi, "
        "photograph, modern clothing"
    )


def enhance_banner_prompt(prompt: str, timeout_sec: float = 60.0) -> str:
    """Banner Ollama enhance — must stay inside CLIP 77-token budget."""
    models = [
        "wizardlm-uncensored:latest",
        "llama3.1:8b",
        "deepseek-r1:7b",
        "mistral:7b",
        "llama3.2:1b",
    ]
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3) as resp:
            tags = json.loads(resp.read().decode("utf-8")).get("models") or []
            names = [m.get("name", "") for m in tags]
    except Exception:
        names = []

    model = next(
        (m for m in models if any(m in n or n.startswith(m.split(":")[0]) for n in names)),
        None,
    )
    if not model and names:
        model = names[0]
    if not model:
        return clip_fit_prompt(prompt)

    instruction = (
        "Rewrite this SD3.5 CLIP prompt. HARD LIMIT: 55 words max. "
        "Start with: no text, no logo, no watermark. "
        "Then subjects and lighting. Keep dark fantasy. "
        "Return ONLY the prompt.\n\n"
        f"{prompt}"
    )
    # num_gpu=0: SD3.5 owns most of the 11GB 2080 Ti; run Ollama on CPU.
    # num_ctx=4096: small context keeps RAM estimate under free memory.
    options = {"num_predict": 100, "temperature": 0.55, "num_gpu": 0, "num_ctx": 4096}
    body = json.dumps(
        {
            "model": model,
            "prompt": instruction,
            "stream": False,
            "options": options,
        }
    ).encode("utf-8")

    print(f"  [Ollama] banner enhance via {model}...", flush=True)
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # GPU turn-taking: CPU-only calls (num_gpu=0) skip the shared lock.
        with acquire_gpu(f"Ollama banner {model}", enabled=options.get("num_gpu") != 0):
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        text = (data.get("response") or "").strip().strip('"').strip("'")
        for prefix in ("Enhanced prompt:", "Prompt:", "Here is"):
            if text.lower().startswith(prefix.lower()):
                text = text.split(":", 1)[-1].strip()
        if len(text) > 20:
            fitted = clip_fit_prompt(text)
            print(
                f"  [Ollama] ok (~{estimate_clip_tokens(fitted)} CLIP tokens)",
                flush=True,
            )
            return fitted
    except Exception as exc:
        print(f"  [Ollama] banner enhance skipped: {exc}", flush=True)
    return clip_fit_prompt(prompt)


def _pillow_polish(im: "Image.Image") -> "Image.Image":
    """Mild contrast/color/sharpen after downscale — avoid crunchy oversharpen."""
    im = ImageEnhance.Contrast(im).enhance(1.08)
    im = ImageEnhance.Color(im).enhance(1.06)
    im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=110, threshold=2))
    return im


def postprocess_banner(
    path: Path,
    width: int = DEFAULT_BANNER_W,
    height: int = DEFAULT_BANNER_H,
    *,
    keep_hires: Path | None = None,
) -> bool:
    """
    Cover-crop / Lanczos downscale to workshop size with unsharp polish.

    Generating large then downscaling preserves more detail than native 512x439.
    """
    if keep_hires and path.exists():
        try:
            shutil.copy2(path, keep_hires)
        except Exception:
            pass

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
                    f"{width}x{height}^",
                    "-gravity",
                    "center",
                    "-extent",
                    f"{width}x{height}",
                    "-unsharp",
                    "0x0.9+0.8+0.02",
                    "-modulate",
                    "100,106,100",
                    "-contrast-stretch",
                    "0.2%x0.2%",
                    "PNG32:" + str(tmp),
                ],
                check=True,
                capture_output=True,
            )
            if tmp.exists():
                tmp.replace(path)
                return True
        except Exception as exc:
            print(f"[WARN] ImageMagick banner resize failed: {exc}", file=sys.stderr)
            if tmp.exists():
                tmp.unlink(missing_ok=True)

    if PIL_OK and Image:
        try:
            im = Image.open(path).convert("RGBA")
            tw, th = width, height
            sw, sh = im.size
            scale = max(tw / sw, th / sh)
            nw, nh = int(sw * scale + 0.5), int(sh * scale + 0.5)
            im = im.resize((nw, nh), Image.Resampling.LANCZOS)
            left = (nw - tw) // 2
            top = (nh - th) // 2
            im = im.crop((left, top, left + tw, top + th))
            rgb = _pillow_polish(im.convert("RGB")).convert("RGBA")
            rgb.save(path, "PNG", compress_level=6)
            return True
        except Exception as exc:
            print(f"[WARN] Pillow banner resize failed: {exc}", file=sys.stderr)
    return False


def procedural_banner(
    cfg: dict[str, Any],
    output: Path,
    width: int = DEFAULT_BANNER_W,
    height: int = DEFAULT_BANNER_H,
) -> bool:
    """Pillow fallback when SD is down — themed gradient + cast labels."""
    if not (PIL_OK and Image):
        return False

    pkg = package_cfg(cfg)
    img = Image.new("RGB", (width, height), (22, 16, 28))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        t = y / max(1, height - 1)
        r = int(24 + 40 * t)
        g = int(16 + 12 * (1 - t))
        b = int(32 + 20 * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    draw.rectangle([0, 0, width, 6], fill=(180, 120, 40))
    draw.rectangle([0, height - 48, width, height], fill=(48, 28, 20))

    races = list((cfg.get("races") or {}).values())[:8]
    chip_w = max(24, (width - 32) // max(1, len(races)))
    for i, race in enumerate(races):
        pal = race.get("palette") or ["#4a1010"]
        hex_c = str(pal[0]).lstrip("#")
        try:
            color = tuple(int(hex_c[j : j + 2], 16) for j in (0, 2, 4))
        except Exception:
            color = (80, 40, 40)
        x0 = 16 + i * chip_w
        draw.rounded_rectangle(
            [x0, 56, x0 + chip_w - 8, 120],
            radius=6,
            fill=color,
            outline=(200, 170, 120),
        )

    try:
        font = ImageFont.truetype("arial.ttf", 28)
        font2 = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        font = ImageFont.load_default()
        font2 = font

    draw.text((18, 140), pkg["title"], fill=(240, 220, 180), font=font)
    draw.text(
        (18, 180),
        "Exotic races / mounts / monster gear",
        fill=(180, 160, 140),
        font=font2,
    )
    draw.text(
        (18, height - 36),
        "Elemental Reforged / AAMT banner",
        fill=(200, 170, 120),
        font=font2,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    img.save(output, "PNG")
    return output.exists()


def generate_banner(
    cfg: dict[str, Any],
    *,
    output: Path,
    prompt: str | None = None,
    tools: dict[str, Any] | None = None,
    enhance: bool = True,
    force: bool = False,
    steps: int | None = None,
    guidance: float | None = None,
    allow_procedural: bool = True,
    start_sd: bool = False,
    sd_wait: float = 120.0,
) -> dict[str, Any]:
    """
    Generate workshop-sized banner PNG at Cursor-comparable quality.

    Pipeline: rich prompt -> optional uncensored Ollama enhance -> high-res SD
    -> Lanczos+unsharp downscale to 512x439 (keeps hi-res raw beside output).
    """
    pkg = package_cfg(cfg)
    tw = int(pkg["bannerWidth"])
    th = int(pkg["bannerHeight"])
    gw = int(pkg["genWidth"])
    gh = int(pkg["genHeight"])
    use_steps = int(steps if steps is not None else pkg.get("bannerSteps") or DEFAULT_STEPS)
    use_cfg = float(
        guidance if guidance is not None else pkg.get("bannerGuidance") or DEFAULT_GUIDANCE
    )

    result: dict[str, Any] = {
        "ok": False,
        "path": str(output),
        "source": None,
        "prompt": "",
        "width": tw,
        "height": th,
        "genWidth": gw,
        "genHeight": gh,
        "steps": use_steps,
        "guidance": use_cfg,
    }

    if output.exists() and not force:
        result["ok"] = True
        result["source"] = "existing"
        print(f"[Banner] exists (use --force to regenerate): {output}", flush=True)
        return result

    prompt_text = build_banner_prompt(cfg, prompt)
    if enhance:
        prompt_text = enhance_banner_prompt(prompt_text)
    # Final hard clip — never send >72 CLIP tokens to SD3.5.
    prompt_text = clip_fit_prompt(prompt_text)
    negative = clip_fit_prompt(banner_negative(cfg))
    n_tok = estimate_clip_tokens(prompt_text)
    print(f"[Banner] CLIP tokens={n_tok}/{CLIP_TOKEN_BUDGET}: {prompt_text}", flush=True)
    if n_tok > 77:
        print("[Banner] ERROR: prompt still over CLIP limit", file=sys.stderr)
        return result
    result["prompt"] = prompt_text
    result["clipTokens"] = n_tok
    seed = sum(ord(c) for c in pkg["title"]) % 100000

    if tools is None:
        tools = probe_tools(start_sd=start_sd, wait_sd_sec=sd_wait, cfg=cfg)

    output.parent.mkdir(parents=True, exist_ok=True)
    raw = output.with_name(output.stem + "_AI_raw.png")
    hires = output.with_name(output.stem + "_hires.png")

    if tools.get("sd"):
        print(
            f"[Banner] SD quality pass {gw}x{gh} @ {use_steps} steps "
            f"cfg={use_cfg} -> {output.name}",
            flush=True,
        )
        ok = generate_ai_image(
            prompt=prompt_text,
            output=raw,
            negative=negative,
            width=gw,
            height=gh,
            steps=use_steps,
            seed=seed,
            api_url=tools.get("sd_url"),
            enhance=False,  # already banner-enhanced above
            kind="banner",
            guidance_scale=use_cfg,
        )
        if ok and raw.exists():
            shutil.copy2(raw, output)
            if postprocess_banner(output, tw, th, keep_hires=hires):
                result["ok"] = True
                result["source"] = "sd"
                result["hires"] = str(hires) if hires.exists() else None
                print(
                    f"[Banner] OK (SD) {output} ({tw}x{th}) from {gw}x{gh}",
                    flush=True,
                )
                return result
            print("[Banner] SD produced file but resize failed", file=sys.stderr)

    if allow_procedural:
        print("[Banner] SD unavailable - procedural fallback", flush=True)
        if procedural_banner(cfg, output, tw, th):
            result["ok"] = True
            result["source"] = "procedural"
            print(f"[Banner] OK (procedural) {output}", flush=True)
            return result

    print("[Banner] FAILED", file=sys.stderr)
    return result


def install_banner(
    cfg: dict[str, Any],
    banner_path: Path,
    mod: Path | None = None,
) -> Path | None:
    """Copy banner into the packaged mod root (next to .elemd)."""
    from er_tool_lib import mod_path

    pkg = package_cfg(cfg)
    dest_mod = Path(mod) if mod else mod_path(cfg)
    if not dest_mod:
        print("[Banner] no mod path", file=sys.stderr)
        return None
    if not banner_path.exists():
        print(f"[Banner] missing source: {banner_path}", file=sys.stderr)
        return None

    dest_mod.mkdir(parents=True, exist_ok=True)
    dest = dest_mod / pkg["bannerFile"]
    if banner_path.resolve() != dest.resolve():
        shutil.copy2(banner_path, dest)
    print(f"[Banner] installed -> {dest}", flush=True)

    # Mirror into Output/ only when the source is elsewhere
    out_dir = ROOT / "Output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_mirror = out_dir / pkg["bannerFile"]
    try:
        if banner_path.resolve() != out_mirror.resolve():
            shutil.copy2(banner_path, out_mirror)
    except PermissionError as exc:
        print(f"[Banner] Output mirror skipped (locked): {exc}", flush=True)
    return dest


def write_banner_meta(cfg: dict[str, Any], result: dict[str, Any], out_dir: Path) -> Path:
    pkg = package_cfg(cfg)
    meta = {
        "title": pkg["title"],
        "author": pkg["author"],
        "description": pkg["description"],
        "bannerFile": pkg["bannerFile"],
        "width": result.get("width"),
        "height": result.get("height"),
        "genWidth": result.get("genWidth"),
        "genHeight": result.get("genHeight"),
        "steps": result.get("steps"),
        "guidance": result.get("guidance"),
        "source": result.get("source"),
        "hires": result.get("hires"),
        "prompt": result.get("prompt"),
    }
    path = out_dir / "banner_meta.json"
    path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return path


if __name__ == "__main__":
    from er_tool_lib import load_config

    cfg = load_config()
    out = ROOT / "Output" / package_cfg(cfg)["bannerFile"]
    info = generate_banner(cfg, output=out, force=True, allow_procedural=True)
    print(json.dumps(info, indent=2))
