#!/usr/bin/env python3
"""Stable Diffusion game-art helper: one call -> a finished sprite / tile sheet PNG.

Used by generators that used to draw placeholder rectangles with System.Drawing / PIL.
Pixels come from the local SD3.5 server (:1338); it is started on demand. There is no
procedural fallback here: if SD cannot deliver, this exits non-zero.

  sprite : one image, optionally with the background knocked out to alpha
  sheet  : COUNT images packed into a grid (tile variants / animation frames)

Examples:
  python sd_art.py sprite --prompt "ruined stone tower" --width 64 --height 96 \
      --transparent --pixel --output tower.png
  python sd_art.py sheet --prompt "mossy cobblestone floor texture" --width 8 --height 8 \
      --count 5 --columns 5 --pixel --output cobble.png
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Optional

SHARED_DIR = Path(__file__).resolve().parent
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

from PIL import Image, ImageDraw  # noqa: E402

from sd_policy import SdUnavailable  # noqa: E402

DEFAULT_NEGATIVE = (
    "text, letters, watermark, logo, signature, frame, border, photograph, photorealistic, "
    "blurry, low quality, cluttered, multiple objects, collage, UI chrome"
)
LOOK = "hand-painted 2D game art, crisp readable silhouette, high contrast, no text"


def _cache_dir() -> Path:
    d = Path(os.environ.get("AAMT_SD_ART_CACHE") or (Path(tempfile.gettempdir()) / "aamt_sd_art"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def ensure_server(timeout_sec: float = 600.0) -> str:
    """Return the SD API URL, starting the server when needed. Raises SdUnavailable."""
    from sd_http_client import detect_server
    from sd_server_lifecycle import ensure_sd_server

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if ensure_sd_server(timeout_sec=min(300.0, max(30.0, deadline - time.time())), start_if_needed=True):
            url = detect_server(verbose=False)
            if url:
                return url
        time.sleep(5.0)
    raise SdUnavailable("SD3.5 server (:1338) could not be started or reached")


def _knockout_background(img: Image.Image, tolerance: int = 70) -> Image.Image:
    """Make the flat background that touches the frame transparent (flood fill).

    The background colour is measured from the frame border (SD sometimes ignores
    "black background" and paints white/grey). Raises ValueError when the border is not a
    uniform colour, so the caller can retry with another seed instead of keeping a box."""
    import numpy as np

    rgba = img.convert("RGBA")
    w, h = rgba.size
    arr = np.asarray(rgba)[..., :3].astype(np.int32)
    border = np.concatenate([arr[0], arr[-1], arr[:, 0], arr[:, -1]])
    bg_colour = np.median(border, axis=0)
    border_dist = np.abs(border - bg_colour).sum(axis=1)
    if float((border_dist <= tolerance).mean()) < 0.6:
        raise ValueError("background is not a uniform colour (cannot knock it out cleanly)")
    near = np.abs(arr - bg_colour).sum(axis=2) <= tolerance
    dark = Image.fromarray((near * 255).astype(np.uint8))
    # Flood from every background-coloured border pixel so interior detail of the same
    # colour survives.
    marker = 128
    work = dark.copy()
    for x in range(w):
        for y in (0, h - 1):
            if work.getpixel((x, y)) == 255:
                ImageDraw.floodfill(work, (x, y), marker)
    for y in range(h):
        for x in (0, w - 1):
            if work.getpixel((x, y)) == 255:
                ImageDraw.floodfill(work, (x, y), marker)
    bg = work.point(lambda v: 255 if v == marker else 0)
    alpha = rgba.getchannel("A")
    alpha = Image.composite(Image.new("L", (w, h), 0), alpha, bg)
    rgba.putalpha(alpha)
    return rgba


def _fit_subject(rgba: Image.Image, out_w: int, out_h: int, margin: float = 0.08) -> Image.Image:
    """Crop to the subject's alpha bbox and scale it to fill the cell (keeps aspect).

    Without this a small subject on a large black frame ends up a few pixels at 16-48px."""
    bbox = rgba.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if not bbox:
        return rgba
    sub = rgba.crop(bbox)
    inner_w = max(1, int(round(out_w * (1.0 - 2.0 * margin))))
    inner_h = max(1, int(round(out_h * (1.0 - 2.0 * margin))))
    scale = min(inner_w / sub.width, inner_h / sub.height)
    nw, nh = max(1, int(round(sub.width * scale))), max(1, int(round(sub.height * scale)))
    sub = sub.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 0))
    canvas.paste(sub, ((out_w - nw) // 2, (out_h - nh) // 2))
    return canvas


def _finish(
    img: Image.Image,
    out_w: int,
    out_h: int,
    *,
    transparent: bool,
    pixel: bool,
    colors: int,
    fit: bool = False,
) -> Image.Image:
    rgba = _knockout_background(img) if transparent else img.convert("RGBA")
    if transparent and fit:
        rgba = _fit_subject(rgba, out_w, out_h)
    if rgba.size != (out_w, out_h):
        rgba = rgba.resize((out_w, out_h), Image.Resampling.LANCZOS if not pixel else Image.Resampling.BOX)
    if pixel:
        alpha = rgba.getchannel("A")
        q = rgba.convert("RGB").quantize(colors=max(4, colors), method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        out = q.convert("RGBA")
        # Hard alpha edges for pixel art.
        out.putalpha(alpha.point(lambda v: 255 if v >= 128 else 0))
        return out
    return rgba


def render(
    prompt: str,
    out_w: int,
    out_h: int,
    *,
    api_url: str,
    kind: str = "icon",
    transparent: bool = False,
    pixel: bool = False,
    colors: int = 24,
    seed: int = 0,
    negative: str = DEFAULT_NEGATIVE,
    steps: Optional[int] = None,
    attempts: int = 3,
    fit: bool = False,
    reference: Optional[Path] = None,
    strength: float = 0.6,
    return_raw: bool = False,
):
    """Generate one finished image of exactly out_w x out_h. Raises SdUnavailable.

    fit: crop to the subject and fill the cell (sprites). reference/strength: img2img from
    an earlier raw SD image (keeps animation frames on the same subject). return_raw: also
    return the raw SD image path as (img, raw_path)."""
    from sd_http_client import generate_image, plan_sd_size

    gw, gh, plan_steps = plan_sd_size(out_w, out_h, kind=kind)
    bg_clause = "isolated on a pure black background, centered, " if transparent else "fills the whole frame, "
    full_prompt = f"{prompt.strip()}, {bg_clause}{LOOK}"
    last_err: Optional[Exception] = None
    for attempt in range(max(1, attempts)):
        s = ((seed or 1) + attempt * 7919) % 1_000_000 or 1
        ref_tag = reference.name if reference else ""
        key = hashlib.md5(
            f"{full_prompt}|{gw}x{gh}|{s}|{steps or plan_steps}|{ref_tag}|{strength}".encode()
        ).hexdigest()
        raw = _cache_dir() / f"{key}.png"
        try:
            if not raw.exists():
                generate_image(
                    full_prompt,
                    raw,
                    api_url=api_url,
                    negative_prompt=negative,
                    width=gw,
                    height=gh,
                    steps=int(steps or plan_steps),
                    guidance_scale=4.5,
                    seed=s,
                    reference_image=str(reference) if reference else None,
                    image_strength=float(strength),
                )
            with Image.open(raw) as src:
                src.load()
                img = _finish(src, out_w, out_h, transparent=transparent, pixel=pixel, colors=colors, fit=fit)
            if transparent:
                alpha_ch = img.getchannel("A")
                a = alpha_ch.getextrema()[1]
                covered = 1.0 - alpha_ch.histogram()[0] / float(out_w * out_h)
                if a == 0 or covered < 0.02:
                    raise RuntimeError("subject was knocked out entirely (blank result)")
            return (img, raw) if return_raw else img
        except Exception as exc:  # noqa: BLE001 - try the next seed
            last_err = exc
            print(f"[sd_art] attempt {attempt + 1} failed: {exc}", file=sys.stderr, flush=True)
    raise SdUnavailable(f"SD could not produce usable art for {prompt[:60]!r}: {last_err}")


def pack_grid(tiles: List[Image.Image], cols: int, cell_w: int, cell_h: int) -> Image.Image:
    cols = max(1, cols)
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cell_w, rows * cell_h), (0, 0, 0, 0))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * cell_w, (i // cols) * cell_h))
    return sheet


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Stable Diffusion game-art helper")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("sprite", "sheet"):
        p = sub.add_parser(name)
        p.add_argument("--prompt", required=True)
        p.add_argument("--output", required=True, type=Path)
        p.add_argument("--width", type=int, required=True, help="Delivery width of one cell")
        p.add_argument("--height", type=int, required=True, help="Delivery height of one cell")
        p.add_argument("--kind", default="icon", help="plan_sd_size kind: icon|sprite|texture|banner|hud")
        p.add_argument("--transparent", action="store_true", help="Knock the black background out to alpha")
        p.add_argument("--pixel", action="store_true", help="Quantize to a small palette with hard alpha")
        p.add_argument("--colors", type=int, default=24)
        p.add_argument("--seed", type=int, default=0)
        p.add_argument("--negative", default=DEFAULT_NEGATIVE)
        p.add_argument("--steps", type=int, default=0)
        p.add_argument("--attempts", type=int, default=3)
        p.add_argument(
            "--fit",
            action="store_true",
            help="Crop to the subject and fill the cell (use for sprites; with --transparent)",
        )
        if name == "sheet":
            p.add_argument(
                "--consistent",
                action="store_true",
                help="Animation frames: cell 1 is txt2img, later cells are img2img from it so the "
                "subject stays the same (use --variants for the motion phases)",
            )
            p.add_argument("--strength", type=float, default=0.72, help="img2img strength for --consistent")
            p.add_argument("--count", type=int, default=1)
            p.add_argument("--columns", type=int, default=0, help="0 = all in one row")
            p.add_argument(
                "--variants",
                default="",
                help="'|'-separated per-cell prompt suffixes (cycled), e.g. 'worn|cracked|mossy'",
            )
    args = ap.parse_args(argv)

    try:
        api = ensure_server()
        common = dict(
            api_url=api,
            kind=args.kind,
            transparent=args.transparent,
            pixel=args.pixel,
            colors=args.colors,
            negative=args.negative,
            steps=args.steps or None,
            attempts=args.attempts,
        )
        common["fit"] = bool(args.fit)
        if args.cmd == "sprite":
            img = render(args.prompt, args.width, args.height, seed=args.seed, **common)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            img.save(args.output, "PNG")
            print(f"[OK] {args.output} ({args.width}x{args.height})")
            return 0

        suffixes = [s.strip() for s in args.variants.split("|") if s.strip()]
        cells: List[Image.Image] = []
        first_raw: Optional[Path] = None
        base_seed = args.seed or 1
        for i in range(max(1, args.count)):
            p = args.prompt + (f", {suffixes[i % len(suffixes)]}" if suffixes else "")
            if args.consistent:
                # One subject across frames: same seed everywhere, later cells img2img from cell 1.
                img, raw = render(
                    p, args.width, args.height, seed=base_seed, return_raw=True,
                    reference=first_raw, strength=args.strength, **common,
                )
                if first_raw is None:
                    first_raw = raw
                cells.append(img)
            else:
                cells.append(render(p, args.width, args.height, seed=base_seed + i * 101, **common))
            print(f"[sd_art] cell {i + 1}/{args.count} done", flush=True)
        cols = args.columns if args.columns > 0 else len(cells)
        sheet = pack_grid(cells, cols, args.width, args.height)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(args.output, "PNG")
        print(f"[OK] {args.output} ({sheet.width}x{sheet.height}, {len(cells)} cells)")
        return 0
    except SdUnavailable as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
