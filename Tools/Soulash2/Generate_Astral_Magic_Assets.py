#!/usr/bin/env python3
"""
Generate Soulash 2 Astral Magic asset grids:

- abilities.png
- amplifiers.png
- passive_skills.png
- skills.png
- stackers.png
- entities.png

Each grid is a packed tilesheet (e.g. 64x64 tiles) suitable for tilemap.json
and glyph indices. Tiles are Stable Diffusion art (SD3.5 on :1338): every tile is
generated on a pure black background and the brightness becomes alpha, so glow
falls off to true transparency. There is NO silent procedural fallback in SD mode:
if SD is unreachable or a tile cannot be produced the run aborts (set
AAMT_SD_STRICT=0 to allow procedural stand-ins for failed tiles). `--mode
procedural` is an explicit opt-in for placeholder rings.

Raw SD images are cached under <mod>/DesignDrafts/astral_tile_raw so an
interrupted run resumes instead of regenerating.

Transparency: sheets are true RGBA with NO background. Every tile is rendered on a
transparent canvas (4x supersampled, then downscaled with premultiplied alpha), so
edges and glow fall off smoothly to alpha 0. Fully transparent pixels carry the accent
colour instead of black ("alpha bleed"), so in-engine bilinear filtering does not
produce dark halos. Output is deterministic: same inputs give byte-identical PNGs.

Semi-transparency: every grid has an opacity (GRID_DEFS["opacity"], 0..1) that scales the
whole tile's alpha, so even the brightest core is see-through. Entities are the most
ghostly. Override per grid with --opacity, e.g. --opacity entities=0.4,skills=0.9
"""

from __future__ import annotations

import argparse
import hashlib
import os
import random
import sys
import time
import zlib
from pathlib import Path
from typing import Dict, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFilter

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_DIR = SCRIPT_DIR.parent / "Shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

# If you later want quality gates or Ollama/SD, you can mirror hydromancy_quality here.
TILE_SIZE = 64  # astral looks good at 64x64

# opacity: peak alpha of the grid as a fraction (1.0 = fully opaque core, 0.5 = half see-through).
GRID_DEFS: Dict[str, Dict[str, object]] = {
    "abilities":   {"file": "abilities.png",      "cols": 8, "count": 32, "opacity": 0.80},
    "amplifiers":  {"file": "amplifiers.png",     "cols": 8, "count": 32, "opacity": 0.80},
    "passives":    {"file": "passive_skills.png", "cols": 8, "count": 32, "opacity": 0.80},
    "skills":      {"file": "skills.png",         "cols": 8, "count": 32, "opacity": 0.80},
    "stackers":    {"file": "stackers.png",       "cols": 8, "count": 32, "opacity": 0.80},
    "entities":    {"file": "entities.png",       "cols": 8, "count": 32, "opacity": 0.50},
}

ASTRAL_ACCENT = (120, 200, 255)
ASTRAL_CORE = (180, 230, 255)

SUPERSAMPLE = 4  # tiles are drawn at 4x and downscaled for smooth alpha edges


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Soulash 2 Astral Magic asset grid generator")
    p.add_argument(
        "--mod-path",
        type=Path,
        default=Path(r"E:\SteamLibrary\steamapps\common\Soulash 2\data\mods\arendeth_astral_magic"),
    )
    p.add_argument(
        "--mode",
        choices=["procedural", "sd", "ollama", "all"],
        default="sd",
        help="sd/all (default): Stable Diffusion tiles. procedural/ollama: placeholder rings "
        "(explicit opt-in only).",
    )
    p.add_argument("--sd-steps", type=int, default=28, help="SD steps per tile (default 28).")
    p.add_argument(
        "--sd-attempts",
        type=int,
        default=3,
        help="Seeds to try per tile when a result is unusable (default 3).",
    )
    p.add_argument(
        "--quality",
        choices=["fast", "mechanical", "full"],
        default="mechanical",
    )
    p.add_argument(
        "--grids",
        default="abilities,amplifiers,passives,skills,stackers,entities",
        help="Comma-separated list of grids to generate.",
    )
    p.add_argument(
        "--opacity",
        default="",
        help="Per-grid opacity overrides 0..1, e.g. 'entities=0.4,skills=0.9', or a single "
        "number for all grids (e.g. '0.6'). Defaults are set in GRID_DEFS.",
    )
    p.add_argument(
        "--preview-dir",
        type=Path,
        default=None,
        help="Also write previews composited on a checkerboard (so transparency is visible). "
        "Kept outside the mod's tiles folder; the real sheets never contain a background.",
    )
    p.add_argument("--use-sd", action="store_true")
    p.add_argument("--sd-drafts-dir", type=Path, default=None)
    p.add_argument("--sd-draft-icon", type=Path, default=None)
    p.add_argument("--sd-draft-thumbnail", type=Path, default=None)
    return p.parse_args()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _layer(mask: Image.Image, rgb: Tuple[int, int, int], max_alpha: int = 255) -> Image.Image:
    """Solid colour layer whose alpha is `mask` (scaled so its peak is max_alpha)."""
    if max_alpha != 255:
        mask = mask.point(lambda v: v * max_alpha // 255)
    layer = Image.new("RGBA", mask.size, rgb + (0,))
    layer.putalpha(mask)
    return layer


def _bleed_transparent(tile: Image.Image, rgb: Tuple[int, int, int]) -> Image.Image:
    """Give fully transparent pixels a real colour instead of black.

    Premultiplied resampling leaves alpha-0 pixels as (0,0,0,0). Engines that filter
    textures without premultiplying then blend that black into the glow edge (dark halo).
    """
    r, g, b, a = tile.split()
    transparent = a.point(lambda v: 255 if v == 0 else 0)
    solid = Image.new("RGB", tile.size, rgb)
    colour = Image.composite(solid, Image.merge("RGB", (r, g, b)), transparent)
    out = colour.convert("RGBA")
    out.putalpha(a)
    return out


def draw_astral_motif(seed: int = 0) -> Image.Image:
    """Astral wisp / spark motif on a transparent canvas (RGBA, TILE_SIZE square)."""
    rng = random.Random(seed)
    ss = SUPERSAMPLE
    size = TILE_SIZE * ss
    cx = size / 2 + rng.randint(-4, 4) * ss
    cy = size / 2 + rng.randint(-4, 4) * ss
    r_outer = size * 0.42
    r_inner = size * 0.22

    def ellipse_box(r: float) -> Tuple[float, float, float, float]:
        return (cx - r, cy - r, cx + r, cy + r)

    # Soft outer glow: filled disc, heavily blurred, low peak alpha.
    glow = Image.new("L", (size, size), 0)
    ImageDraw.Draw(glow).ellipse(ellipse_box(r_outer * 0.9), fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(r_outer * 0.35))

    # Orbit rings. Rings never overlap, so one mask can hold their different alphas.
    rings = Image.new("L", (size, size), 0)
    ring_draw = ImageDraw.Draw(rings)
    for i in range(4):
        r = r_outer * (0.4 + i * 0.12)
        ring_draw.ellipse(ellipse_box(r), outline=60 + i * 30, width=2 * ss)

    # Directional streaks.
    streaks = Image.new("L", (size, size), 0)
    streak_draw = ImageDraw.Draw(streaks)
    for _ in range(5):
        dx = rng.uniform(-r_outer * 0.6, r_outer * 0.6)
        dy = rng.uniform(-r_outer * 0.6, r_outer * 0.6)
        streak_draw.line((cx + dx * 0.4, cy + dy * 0.4, cx + dx, cy + dy), fill=220, width=int(1.5 * ss))

    # Core spark with a soft rim instead of a hard cut-off.
    core = Image.new("L", (size, size), 0)
    ImageDraw.Draw(core).ellipse(ellipse_box(r_inner), fill=255)
    core = core.filter(ImageFilter.GaussianBlur(0.8 * ss))

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for layer in (
        _layer(glow, ASTRAL_ACCENT, 90),
        _layer(rings, ASTRAL_ACCENT),
        _layer(streaks, ASTRAL_ACCENT),
        _layer(core, ASTRAL_CORE),
    ):
        canvas = Image.alpha_composite(canvas, layer)

    # Keep everything inside a circle within the cell: the blurred glow has an endless
    # faint tail, and it must reach exactly alpha 0 before the tile edge so neighbouring
    # tiles in the sheet never pick up each other's glow.
    clip = Image.new("L", (size, size), 0)
    ImageDraw.Draw(clip).ellipse((size * 0.07, size * 0.07, size * 0.93, size * 0.93), fill=255)
    clip = clip.filter(ImageFilter.GaussianBlur(1.5 * ss))
    r, g, b, a = canvas.split()
    canvas = Image.merge("RGBA", (r, g, b, ImageChops.multiply(a, clip)))

    # Pillow resamples RGBA with premultiplied alpha, so edges stay colour-correct.
    tile = canvas.resize((TILE_SIZE, TILE_SIZE), Image.Resampling.LANCZOS)
    # Floor imperceptible alpha (<4/255) to exactly 0 so "transparent" really is 0.
    r, g, b, a = tile.split()
    tile = Image.merge("RGBA", (r, g, b, a.point(lambda v: 0 if v < 4 else v)))
    return _bleed_transparent(tile, ASTRAL_ACCENT)


def parse_opacity_overrides(text: str) -> Dict[str, float]:
    """'entities=0.4,skills=0.9' or '0.6' (all grids) -> {grid: opacity}. Raises on bad input."""
    text = (text or "").strip()
    if not text:
        return {}

    def as_opacity(raw: str) -> float:
        try:
            value = float(raw)
        except ValueError:
            raise SystemExit(f"--opacity: '{raw}' is not a number")
        if not 0.0 < value <= 1.0:
            raise SystemExit(f"--opacity: {value} is out of range (must be > 0 and <= 1)")
        return value

    if "=" not in text:
        value = as_opacity(text)
        return {name: value for name in GRID_DEFS}
    out: Dict[str, float] = {}
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        name, _, raw = part.partition("=")
        name = name.strip()
        if name not in GRID_DEFS:
            raise SystemExit(f"--opacity: unknown grid '{name}' (valid: {', '.join(GRID_DEFS)})")
        out[name] = as_opacity(raw.strip())
    return out


def apply_opacity(tile: Image.Image, opacity: float) -> Image.Image:
    """Scale the whole tile's alpha so it is semi-transparent (colours are untouched)."""
    if opacity >= 1.0:
        return tile
    r, g, b, a = tile.split()
    a = a.point(lambda v: int(round(v * opacity)))
    return _bleed_transparent(Image.merge("RGBA", (r, g, b, a)), ASTRAL_ACCENT)


def stable_seed(grid_name: str, index: int) -> int:
    """Deterministic across runs and machines (str hash() is salted per process)."""
    return (zlib.crc32(grid_name.encode("utf-8")) + index * 7919) & 0xFFFFFFFF


def generate_tile(grid_name: str, index: int, mode: str, opacity: float | None = None) -> Image.Image:
    """
    Tile generator (always returns RGBA with real alpha). Later you can branch on mode:
    - procedural: draw_astral_motif
    - sd: crop from SD drafts
    - ollama: use design spec + procedural
    """
    if opacity is None:
        opacity = float(GRID_DEFS[grid_name]["opacity"])
    # For now, all grids share the same astral motif style; you can specialize per-grid later.
    return apply_opacity(draw_astral_motif(seed=stable_seed(grid_name, index)), opacity)


# ---------------------------------------------------------------------------
# Stable Diffusion tiles
# ---------------------------------------------------------------------------
SD_NEGATIVE = (
    "text, letters, watermark, logo, signature, frame, border, photograph, photorealistic, "
    "white background, gray background, colored background, multiple objects, collage, "
    "cluttered scene, blurry, low quality"
)

SD_ROLE = {
    "abilities": "active ability icon",
    "amplifiers": "amplifier rune icon",
    "passives": "passive skill sigil icon",
    "skills": "skill technique icon",
    "stackers": "stacking charge icon built from layered glowing orbs",
    "entities": "ghostly spectral astral creature silhouette",
}

SD_MOTIFS = (
    "swirling astral wisp spiral",
    "frost-crystal starburst",
    "orbiting comet with glowing rings",
    "crescent moon wrapped in constellation lines",
    "nebula vortex",
    "jagged shard of shatterfrost ice",
    "floating eye made of stars",
    "astral lotus bloom",
    "twin orbiting moons",
    "prismatic star core with radiating beams",
    "sweeping comet trail arc",
    "runed halo ring",
    "falling meteor shower",
    "cosmic hourglass of drifting sparks",
    "spectral hand releasing stardust",
    "crystal lattice constellation",
)

SD_VARIANTS = ("cyan dominant glow", "violet dominant glow")


def sd_tile_prompt(grid_name: str, index: int) -> str:
    offset = zlib.crc32(grid_name.encode("utf-8"))
    motif = SD_MOTIFS[(offset + index) % len(SD_MOTIFS)]
    variant = SD_VARIANTS[(index // len(SD_MOTIFS)) % len(SD_VARIANTS)]
    return (
        f"{SD_ROLE.get(grid_name, 'magic icon')}, {motif}, {variant}, glowing astral energy, "
        "shatterfrost sparks, violet and cyan palette, a single centered emblem filling the frame, "
        "isolated on a pure black background, high contrast, crisp readable silhouette, "
        "hand-painted game icon art, no text"
    )


def sd_raw_to_tile(raw: Image.Image) -> Image.Image | None:
    """SD image on black -> 64px RGBA tile whose alpha is the glow brightness.

    Returns None when the image is unusable (blank, or the background was not black)."""
    import numpy as np

    rgb = np.asarray(raw.convert("RGB"), dtype=np.float32) / 255.0
    lum = rgb.max(axis=2)
    alpha = np.clip((lum - 0.08) / 0.92, 0.0, 1.0) ** 0.85
    coverage = float((alpha > 0.5).mean())
    if float(alpha.max()) < 0.35 or coverage > 0.80 or coverage < 0.004:
        return None
    alpha = alpha / float(alpha.max())
    colour = np.clip(rgb / np.maximum(lum, 1e-3)[..., None], 0.0, 1.0)
    rgba = (np.dstack([colour, alpha]) * 255.0 + 0.5).astype(np.uint8)
    tile = Image.fromarray(rgba).resize((TILE_SIZE, TILE_SIZE), Image.Resampling.LANCZOS)

    # Same guarantee as the procedural motif: nothing may reach the cell edge.
    clip = Image.new("L", (TILE_SIZE, TILE_SIZE), 0)
    ImageDraw.Draw(clip).ellipse(
        (TILE_SIZE * 0.07, TILE_SIZE * 0.07, TILE_SIZE * 0.93, TILE_SIZE * 0.93), fill=255
    )
    clip = clip.filter(ImageFilter.GaussianBlur(1.5))
    r, g, b, a = tile.split()
    a = ImageChops.multiply(a, clip).point(lambda v: 0 if v < 4 else v)
    hi = a.getextrema()[1]
    if hi == 0:
        return None
    a = a.point(lambda v: min(255, int(round(v * 255 / hi))))
    return _bleed_transparent(Image.merge("RGBA", (r, g, b, a)), ASTRAL_ACCENT)


class SdTileSource:
    """Produces SD-generated tiles; raw SD output is cached so runs can resume."""

    def __init__(self, api_url: str, raw_dir: Path, *, steps: int = 28, attempts: int = 3) -> None:
        self.api_url = api_url
        self.raw_dir = raw_dir
        self.steps = steps
        self.attempts = max(1, attempts)
        ensure_dir(raw_dir)

    def tile(self, grid_name: str, index: int, opacity: float) -> Image.Image:
        from sd_http_client import generate_image

        prompt = sd_tile_prompt(grid_name, index)
        tag = hashlib.md5(f"{prompt}|{self.steps}".encode("utf-8")).hexdigest()[:8]
        for attempt in range(self.attempts):
            seed = (stable_seed(grid_name, index) + attempt * 7919) % 1_000_000 or 1
            raw_path = self.raw_dir / f"{grid_name}_{index:02d}_{tag}_{attempt}.png"
            cached = raw_path.exists()
            t0 = time.time()
            if not cached:
                generate_image(
                    prompt,
                    raw_path,
                    api_url=self.api_url,
                    negative_prompt=SD_NEGATIVE,
                    width=512,
                    height=512,
                    steps=self.steps,
                    guidance_scale=4.5,
                    seed=seed,
                )
            with Image.open(raw_path) as raw:
                raw.load()
                tile = sd_raw_to_tile(raw)
            state = "cached" if cached else f"generated {time.time() - t0:.0f}s"
            if tile is not None:
                print(f"    {grid_name} {index + 1:02d}: {state}", flush=True)
                return apply_opacity(tile, opacity)
            print(f"    {grid_name} {index + 1:02d}: unusable result ({state}); next seed", flush=True)
        raise RuntimeError(
            f"{grid_name} tile {index}: no usable SD image after {self.attempts} attempts"
        )


def verify_sheet(path: Path, grid_name: str, cols: int, count: int, opacity: float = 1.0) -> Tuple[float, int]:
    """Re-open the written PNG and prove it really is (semi-)transparent. Raises on failure.

    Returns (transparent_fraction, peak_alpha) over the whole sheet.
    """
    with Image.open(path) as im:
        im.load()
        if im.mode != "RGBA":
            raise RuntimeError(f"{grid_name}: saved sheet is {im.mode}, expected RGBA")
        alpha = im.getchannel("A")
        lo, hi = alpha.getextrema()
        if lo != 0:
            raise RuntimeError(f"{grid_name}: no fully transparent pixels (min alpha {lo})")
        if hi == 0:
            raise RuntimeError(f"{grid_name}: sheet is completely empty")
        expected_peak = int(round(255 * opacity))
        if hi > expected_peak + 1:
            raise RuntimeError(f"{grid_name}: peak alpha {hi} exceeds the configured opacity ({opacity:.0%} = {expected_peak})")
        if hi < expected_peak - 6:
            raise RuntimeError(f"{grid_name}: peak alpha {hi} is far below the configured opacity ({opacity:.0%} = {expected_peak})")
        last = TILE_SIZE - 1
        for idx in range(count):
            x0 = (idx % cols) * TILE_SIZE
            y0 = (idx // cols) * TILE_SIZE
            # The whole 1px border of every tile must be fully transparent.
            for box in (
                (x0, y0, x0 + TILE_SIZE, y0 + 1),
                (x0, y0 + last, x0 + TILE_SIZE, y0 + TILE_SIZE),
                (x0, y0, x0 + 1, y0 + TILE_SIZE),
                (x0 + last, y0, x0 + TILE_SIZE, y0 + TILE_SIZE),
            ):
                if alpha.crop(box).getextrema()[1] != 0:
                    raise RuntimeError(f"{grid_name}: tile {idx} touches its cell edge (glow would bleed into neighbours)")
            if alpha.crop((x0, y0, x0 + TILE_SIZE, y0 + TILE_SIZE)).getextrema()[1] == 0:
                raise RuntimeError(f"{grid_name}: tile {idx} is empty")
        hist = alpha.histogram()
        return hist[0] / (im.width * im.height), hi


def write_preview(sheet: Image.Image, dest: Path) -> None:
    """Checkerboard preview so transparency is visible (never used as the real sheet)."""
    cell = 8
    board = Image.new("RGBA", sheet.size, (70, 70, 78, 255))
    draw = ImageDraw.Draw(board)
    for y in range(0, sheet.height, cell):
        for x in range(0, sheet.width, cell):
            if ((x // cell) + (y // cell)) % 2:
                draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(105, 105, 115, 255))
    ensure_dir(dest.parent)
    Image.alpha_composite(board, sheet).convert("RGB").save(dest, "PNG")


def pack_grid(
    mod_path: Path,
    grid_name: str,
    mode: str,
    preview_dir: Path | None = None,
    opacity_overrides: Dict[str, float] | None = None,
    sd_source: "SdTileSource | None" = None,
    strict: bool = True,
) -> Path:
    grid_def = GRID_DEFS[grid_name]
    opacity = float((opacity_overrides or {}).get(grid_name, grid_def["opacity"]))
    out_dir = mod_path / "tiles"
    ensure_dir(out_dir)

    count = int(grid_def["count"])
    cols = int(grid_def["cols"])
    rows = (count + cols - 1) // cols

    # No background colour: the sheet starts fully transparent.
    sheet = Image.new("RGBA", (cols * TILE_SIZE, rows * TILE_SIZE), (0, 0, 0, 0))

    for idx in range(count):
        if sd_source is not None:
            try:
                tile = sd_source.tile(grid_name, idx, opacity)
            except Exception as exc:  # noqa: BLE001
                if strict:
                    raise
                print(f"    [WARN] {grid_name} {idx + 1:02d}: SD failed ({exc}); procedural stand-in")
                tile = generate_tile(grid_name, idx, mode, opacity)
        else:
            tile = generate_tile(grid_name, idx, mode, opacity)
        x = (idx % cols) * TILE_SIZE
        y = (idx // cols) * TILE_SIZE
        # Plain copy, NOT paste(tile, pos, tile): using the tile as its own mask on an
        # RGBA sheet squares the alpha (a*a) and corrupts soft edges. Cells are disjoint,
        # so a straight copy is exact.
        sheet.paste(tile, (x, y))

    out_path = out_dir / str(grid_def["file"])
    sheet.save(out_path, "PNG")
    transparent, peak = verify_sheet(out_path, grid_name, cols, count, opacity)
    if preview_dir is not None:
        write_preview(sheet, preview_dir / str(grid_def["file"]))
    print(f"  [OK] {grid_name} -> {out_path}  (RGBA, opacity {opacity:.0%}, peak alpha {peak}, {transparent:.0%} fully transparent)")
    return out_path


def main() -> int:
    args = parse_args()
    mod_path = args.mod_path.resolve()

    grids = [g.strip() for g in args.grids.split(",") if g.strip()]
    opacity_overrides = parse_opacity_overrides(args.opacity)
    print(f"Astral Magic asset grids for mod: {mod_path}")
    print(f"  Mode:    {args.mode}")
    print(f"  Quality: {args.quality}")
    print(f"  Grids:   {', '.join(grids)}")
    print("")
    use_sd_tiles = args.use_sd or args.mode in ("sd", "all")
    strict = os.environ.get("AAMT_SD_STRICT", "1").strip() != "0"
    preview_dir = args.preview_dir.resolve() if args.preview_dir else None

    def build_all(sd_source: "SdTileSource | None") -> None:
        for grid in grids:
            if grid not in GRID_DEFS:
                print(f"  [WARN] Unknown grid '{grid}', skipping")
                continue
            print(f"  {grid}:", flush=True)
            pack_grid(mod_path, grid, args.mode, preview_dir, opacity_overrides, sd_source, strict)

    if use_sd_tiles:
        # Starts the SD3.5 server if it is down, waits for it, and stops it afterwards
        # (unless AAMT_SD_KEEP_SERVER=1). Raises instead of falling back to procedural art.
        from s2_icon_pipeline import sd_session

        print("  Tiles: Stable Diffusion (raw images cached for resume)")
        print("")
        raw_dir = mod_path / "DesignDrafts" / "astral_tile_raw"
        try:
            with sd_session(use_sd=True) as api_url:
                build_all(SdTileSource(api_url, raw_dir, steps=args.sd_steps, attempts=args.sd_attempts))
        except Exception as exc:  # noqa: BLE001
            print(f"\n  [ERROR] SD tile generation failed: {exc}", file=sys.stderr)
            print("          No procedural fallback was written. Re-run to resume from the cache.", file=sys.stderr)
            return 1
    else:
        print("  Tiles: PROCEDURAL placeholder rings (explicit --mode procedural/ollama)")
        print("")
        build_all(None)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
