#!/usr/bin/env python3
"""Shared Soulash 2 icon / tilesheet pipeline.

This is the downscale + pack path that SkillCreator `generate-icons` uses.
Standalone generators (reactive crafting sheets, branding SD drafts) should
call these helpers instead of stretching a 512px SD image onto a cell.

Pixels come from Tools/Shared SD3.5 (`sd_http_client` / `ai_resources`), not
Cursor's image generator.

  1. Generate at SD3.5's quality floor via ``plan_sd_size(..., kind="icon")``.
  2. Knock out near-black to alpha so the emblem sits on a dark canvas.
  3. Contrast bump, then ``ImageOps.contain`` (never stretch) into 128px cells
     (`s2_assets.SHEET_TILE`). ``icon.png`` stays 32×32.
  4. Pack sheets with index 0 at the **bottom left** (docs §5).
"""

from __future__ import annotations

import hashlib
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List, Optional, Sequence, Tuple

TILE = 32
SHEET_COLS = 8
DARK_KNOCKOUT = 28
CANVAS_BG = (22, 22, 26, 255)
CONTRAST = 1.12

NEGATIVE = (
    "text, letters, watermark, logo, signature, photograph, photorealistic, "
    "realistic 3d render, soft airbrush, anime, chibi, cluttered scene, "
    "extra objects, UI chrome, frame, border, collage, white background, "
    "light gray backdrop, paper, studio backdrop, nested diamonds, gem cluster"
)

PROMPT_LOOK = (
    "Soulash 2 vanilla core_2 ability icon, detailed 128x128 pixel-art game sprite, "
    "dark near-black cell, one unique high-contrast silhouette with internal shading, "
    "saturated fantasy colors, hard pixel edges, directional top-left light, "
    "like official Soulash 2 skills.png but sharper and more detailed, "
    "no text, no gem frames, no repeating the same symbol as neighboring cells"
)


def _pil():
    try:
        from PIL import Image, ImageEnhance, ImageOps
    except ImportError as exc:
        raise RuntimeError("Pillow is required (pip install pillow)") from exc
    return Image, ImageEnhance, ImageOps


def compose_icon_prompt(*, role: str, subject: str, extra: str = "") -> str:
    """Soulash 2 UI-icon prompt. Keep the look suffix identical across generators."""
    parts = [f"Soulash 2 fantasy RPG {role}", subject.strip(), extra.strip(), PROMPT_LOOK]
    return ", ".join(p for p in parts if p)


def knockout_near_black(img, threshold: int = DARK_KNOCKOUT):
    Image, _, _ = _pil()
    rgba = img.convert("RGBA")
    orig = rgba.copy()
    px = rgba.load()
    kept = 0
    knocked = 0
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = px[x, y]
            if a < 12:
                continue
            # Only punch true gray-black; keep navy / violet / maroon subjects.
            chroma = max(r, g, b) - min(r, g, b)
            if r <= threshold and g <= threshold and b <= threshold and chroma < 14:
                px[x, y] = (0, 0, 0, 0)
                knocked += 1
            else:
                kept += 1
    # Dark meteors / gravity wells were becoming blank tiles.
    if kept + knocked and kept < max(24, (kept + knocked) // 8):
        return orig
    return rgba


def knockout_edge_canvas(img, *, dark: int = 40, light: int = 220):
    """Drop near-black / paper / gray that touches the frame so gems keep their highlights."""
    from collections import deque

    Image, _, _ = _pil()
    rgba = img.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()

    paper_refs = []
    for cx, cy in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        r, g, b, a = px[cx, cy]
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        if a >= 12 and lum >= 55:
            paper_refs.append((r, g, b))

    def is_canvas(x: int, y: int) -> bool:
        r, g, b, a = px[x, y]
        if a < 12:
            return True
        chroma = max(r, g, b) - min(r, g, b)
        if r <= dark and g <= dark and b <= dark and chroma < 14:
            return True
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        chroma = max(r, g, b) - min(r, g, b)
        if lum >= light:
            return True
        if lum >= 95 and chroma < 55:
            return True
        if min(r, g, b) >= 120 and chroma < 80:
            return True
        for pr, pg, pb in paper_refs:
            if abs(r - pr) + abs(g - pg) + abs(b - pb) <= 72:
                return True
        return False

    seen = [[False] * w for _ in range(h)]
    q: deque = deque()
    for x in range(w):
        q.append((x, 0))
        q.append((x, h - 1))
    for y in range(h):
        q.append((0, y))
        q.append((w - 1, y))
    while q:
        x, y = q.popleft()
        if x < 0 or y < 0 or x >= w or y >= h or seen[y][x]:
            continue
        seen[y][x] = True
        if not is_canvas(x, y):
            continue
        px[x, y] = (0, 0, 0, 0)
        q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return rgba


def restamp_sheet_dark_bg(path, tile: int = TILE) -> None:
    """Replace white/gray tile canvases on an existing sheet with the standard dark fill."""
    Image, _, _ = _pil()
    src = Image.open(path).convert("RGBA")
    cols, rows = src.width // tile, src.height // tile
    out = Image.new("RGBA", src.size, (0, 0, 0, 0))
    for ty in range(rows):
        for tx in range(cols):
            box = (tx * tile, ty * tile, (tx + 1) * tile, (ty + 1) * tile)
            cell = knockout_edge_canvas(knockout_near_black(src.crop(box)))
            canvas = Image.new("RGBA", (tile, tile), CANVAS_BG)
            canvas.paste(cell, (0, 0), cell)
            out.paste(canvas, box[:2])
    out.save(path)


def fit_icon_tile(
    img,
    size: int = TILE,
    *,
    bg: Tuple[int, int, int, int] = CANVAS_BG,
    contrast: float = CONTRAST,
):
    """Downscale an SD (or procedural) image onto a square game tile without stretching."""
    Image, ImageEnhance, ImageOps = _pil()
    rgba = knockout_edge_canvas(knockout_near_black(img))
    if contrast and contrast != 1.0:
        rgba = ImageEnhance.Contrast(rgba).enhance(contrast)
    fitted = ImageOps.contain(rgba, (size, size), method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), bg)
    canvas.paste(fitted, ((size - fitted.width) // 2, (size - fitted.height) // 2), fitted)
    return canvas


def fit_icon_tile_bytes(img, size: int = TILE, **kwargs) -> bytes:
    return fit_icon_tile(img, size=size, **kwargs).tobytes()


def sheet_rows_for(count: int, cols: int = SHEET_COLS) -> int:
    if count <= 0:
        return 1
    return max(1, (count + cols - 1) // cols)


def empty_tile_bytes(size: int = TILE, bg: Tuple[int, int, int, int] = CANVAS_BG) -> bytes:
    Image, _, _ = _pil()
    return Image.new("RGBA", (size, size), bg).tobytes()


def pack_bottom_left(tiles: Sequence[bytes], cols: int, rows: int, tile: int = TILE) -> Tuple[int, int, bytes]:
    """Pack RGBA tiles. Game index 0 is the bottom-left cell. Short lists leave empty cells."""
    w, h = cols * tile, rows * tile
    canvas = bytearray(w * h * 4)
    for index, raw in enumerate(tiles):
        if index >= cols * rows:
            break
        gx = index % cols
        gy_from_bottom = index // cols
        py = (rows - 1 - gy_from_bottom) * tile
        px = gx * tile
        for y in range(tile):
            src = y * tile * 4
            dst = ((py + y) * w + px) * 4
            canvas[dst : dst + tile * 4] = raw[src : src + tile * 4]
    return w, h, bytes(canvas)


def unpack_bottom_left(path, tile: Optional[int] = None, *, cols: Optional[int] = None):
    """Split a packed sheet into tiles. Index 0 is the bottom-left cell.

    Pass ``cols`` to infer cell size from an older sheet (vanilla/mod 23–32px).
    """
    Image, _, _ = _pil()
    src = Image.open(path).convert("RGBA")
    if cols:
        tile = max(1, src.width // max(1, int(cols)))
    elif tile is None:
        tile = TILE
    cols = max(1, src.width // tile)
    rows = max(1, src.height // tile)
    tiles = []
    for i in range(cols * rows):
        gx = i % cols
        gy = i // cols
        px = gx * tile
        py = (rows - 1 - gy) * tile
        tiles.append(src.crop((px, py, px + tile, py + tile)))
    return tiles


def pack_bottom_left_image(tiles: Sequence, cols: int, tile: int = TILE, *, bg=(0, 0, 0, 0)):
    Image, _, _ = _pil()
    n = max(1, len(tiles))
    rows = sheet_rows_for(n, cols)
    canvas = Image.new("RGBA", (cols * tile, rows * tile), bg)
    for i, src in enumerate(tiles):
        cell = src.convert("RGBA") if hasattr(src, "convert") else Image.frombytes("RGBA", (tile, tile), src)
        if cell.size != (tile, tile):
            cell = fit_icon_tile(cell, size=tile)
        gx = i % cols
        gy_from_bottom = i // cols
        py = (rows - 1 - gy_from_bottom) * tile
        canvas.paste(cell, (gx * tile, py))
    return canvas


def seed_from_name(name: str) -> int:
    return int(hashlib.md5(str(name).encode("utf-8")).hexdigest()[:8], 16) % 1_000_000


def generate_sd_tile(
    prompt: str,
    *,
    work: Path,
    api_url: str,
    seed: Optional[int] = None,
    steps: int = 24,
    size: int = TILE,
    name: str = "tile",
    negative_prompt: str = NEGATIVE,
    bg: Tuple[int, int, int, int] = CANVAS_BG,
    init_image=None,
    strength: float = 0.58,
    native: bool = False,
):
    """Generate one game-size icon tile via the local SD3.5 server.

    ``native=True`` requests the delivery size (no 512 floor / Lanczos crush).
    Pass ``init_image`` to restyle an existing tile (server img2img).
    Delivery ``size`` is ``SHEET_TILE`` (128) for atlas cells, ``TILE`` (32) for icon.png.
    """
    from sd_http_client import generate_image, plan_sd_size

    Image, _, _ = _pil()
    gw, gh, plan_steps = plan_sd_size(size, size, kind="icon", native=native)
    Path(work).mkdir(parents=True, exist_ok=True)
    digest = hashlib.md5(name.encode("utf-8")).hexdigest()
    raw_path = Path(work) / f"{digest}_raw.png"
    ref_path = None
    if init_image is not None:
        ref_path = Path(work) / f"{digest}_init.png"
        init = init_image.convert("RGBA") if hasattr(init_image, "convert") else Image.frombytes("RGBA", (size, size), init_image)
        if init.size != (gw, gh):
            init = init.resize((gw, gh), Image.Resampling.NEAREST)
        init.save(ref_path)
    generate_image(
        prompt,
        raw_path,
        api_url=api_url,
        negative_prompt=negative_prompt,
        width=gw,
        height=gh,
        steps=max(int(steps), int(plan_steps)),
        guidance_scale=7.0,
        seed=int(seed if seed is not None else seed_from_name(name)),
        reference_image=str(ref_path) if ref_path else None,
        image_strength=float(strength),
    )
    img = Image.open(raw_path).convert("RGBA")
    if native:
        if img.size != (size, size):
            img = img.resize((size, size), Image.Resampling.NEAREST)
        return img
    return fit_icon_tile(img, size=size, bg=bg)


@contextmanager
def sd_session(*, use_sd: bool = True, timeout_sec: float = 2400.0) -> Iterator[Optional[str]]:
    """Yield the SD API URL, starting :1338 if needed.

    With ``use_sd=True`` this **waits** for a healthy aamt-1338 server (GPU lock /
    cold start included) and never falls back to procedural art. Pass
    ``use_sd=False`` (CLI ``--no-sd``) only for explicit placeholder rings.

    Override wait with ``AAMT_SD_WAIT_SEC``. Keep the process alive after the
    batch with ``AAMT_SD_KEEP_SERVER=1``.
    """
    if not use_sd:
        yield None
        return
    import os
    import time

    from sd_http_client import detect_server
    from sd_server_lifecycle import ensure_sd_server, stop_sd_server

    wait_sec = float(os.environ.get("AAMT_SD_WAIT_SEC") or timeout_sec)
    wait_sec = max(120.0, wait_sec)
    keep = str(os.environ.get("AAMT_SD_KEEP_SERVER") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    deadline = time.time() + wait_sec
    print(f"[icons] waiting for SD server (up to {wait_sec:.0f}s)...", file=sys.stderr)
    url: Optional[str] = None
    while time.time() < deadline:
        chunk = min(300.0, max(30.0, deadline - time.time()))
        if ensure_sd_server(timeout_sec=chunk, start_if_needed=True):
            url = detect_server()
            if url:
                print(f"[icons] SD ready at {url}", file=sys.stderr)
                break
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        print(
            f"[icons] SD not ready yet; waiting ({remaining:.0f}s left)...",
            file=sys.stderr,
        )
        time.sleep(min(15.0, remaining))
    if not url:
        raise RuntimeError(
            "SD server not reachable after waiting; refusing procedural icon tiles. "
            "Start Tools\\Start-StableDiffusionServer.ps1, free the GPU lock, "
            "or pass --no-sd only if you explicitly want placeholder rings."
        )
    try:
        yield url
    finally:
        if not keep:
            print("[SD] stopping server (job finished)", file=sys.stderr)
            stop_sd_server(force=True)


def planned_sd_settings(
    kind: str,
    delivery_w: int,
    delivery_h: int,
    *,
    seed: int = 0,
    guidance_scale: float = 7.0,
) -> dict:
    """Right-size an SD request the way generate-icons does (no 1024-default waste)."""
    from sd_http_client import plan_sd_size

    w, h, steps = plan_sd_size(delivery_w, delivery_h, kind=kind)
    return {
        "width": w,
        "height": h,
        "steps": steps,
        "guidance_scale": guidance_scale,
        "seed": seed,
    }
