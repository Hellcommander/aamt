#!/usr/bin/env python3
"""Author new particles32 glyphs instead of only recoloring vanilla frames.

The F2 editor Glyph picker and every animation particle ``tile_id`` resolve to
the tilesheet named ``particles32``. Particle JSON has no tilesheet field
(Soulash 2.exe lists ``tile_id`` / ``flags`` / delay / life / … — not a sheet
name). Workshop skill mods never ship this atlas.

Safe overlay: copy core_2 ``assets/gfx/particles.png`` (16×16 tiles, 16 columns,
**top-left** index 0 — not the bottom-left convention used by ability icons)
and append extra rows. New ``tile_id``s start at 1680. Vanilla ids 0–1679 stay
pixel-identical, so a global last-wins replace still keeps core FX working.

Do not invent a second atlas name. Do not run this from ``write``.
"""

from __future__ import annotations

import math
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from s2_assets import write_png
from s2_paths import core2_dir, staging_dir

PARTICLE_SHEET = "particles32"
PARTICLE_FILE = "assets/particles.png"
PARTICLE_TILE = 16
PARTICLE_COLS = 16
VANILLA_ROWS = 105
VANILLA_TILES = PARTICLE_COLS * VANILLA_ROWS  # 1680

THEMES: Dict[str, Dict[str, Any]] = {
    "steam": {
        "rgb": (210, 228, 236),
        "prompt": "white grey steam puff, wispy vapor cloud, not fire, not explosion",
    },
    "water": {
        "rgb": (70, 170, 230),
        "prompt": "cyan water splash droplet, liquid spray, not fire",
    },
    "blood": {
        "rgb": (180, 36, 48),
        "prompt": "crimson blood droplet splash, arterial spray, not water, not fire",
    },
    "ice": {
        "rgb": (180, 220, 255),
        "prompt": "pale ice crystal shard frost burst, not fire",
    },
    "lightning": {
        "rgb": (160, 210, 255),
        "prompt": "white cyan lightning bolt spark, jagged electricity, not fire",
    },
    "earth": {
        "rgb": (160, 130, 70),
        "prompt": "brown stone pebble dust burst, rock chips, not fire",
    },
    "generic": {
        "rgb": (200, 200, 210),
        "prompt": "magical spark particle, centered VFX glyph",
    },
    "fire": {
        "rgb": (255, 120, 40),
        "prompt": "orange fire ember spark, not water, not ice",
    },
    "poison": {
        "rgb": (80, 180, 60),
        "prompt": "toxic green droplet mist, not fire",
    },
    "arcane": {
        "rgb": (160, 90, 220),
        "prompt": "violet arcane sparkle, not fire",
    },
}

_THEME_ALIASES = {
    "smoke": "steam",
    "fog": "steam",
    "mist": "steam",
    "vapor": "steam",
    "baro": "steam",
    "baromancy": "steam",
    "frost": "ice",
    "freeze": "ice",
    "spark": "lightning",
    "electric": "lightning",
    "shock": "lightning",
    "bleed": "blood",
    "gore": "blood",
    "wave": "water",
    "tide": "water",
    "stone": "earth",
    "rock": "earth",
    "flame": "fire",
    "ember": "fire",
    "toxic": "poison",
    "acid": "poison",
    "magic": "arcane",
    "void": "arcane",
}


def _pil():
    from PIL import Image, ImageDraw

    return Image, ImageDraw


def vanilla_particles_png() -> Path:
    path = core2_dir() / "assets" / "gfx" / "particles.png"
    if not path.is_file():
        raise FileNotFoundError(f"core_2 particles.png not found: {path}")
    return path


def atlas_meta(spec: Dict[str, Any]) -> Dict[str, Any]:
    meta = spec.setdefault(
        "particle_atlas",
        {
            "name": PARTICLE_SHEET,
            "file": PARTICLE_FILE,
            "tile": PARTICLE_TILE,
            "cols": PARTICLE_COLS,
            "vanilla_tiles": VANILLA_TILES,
            "next_id": VANILLA_TILES,
            "frames": [],
        },
    )
    meta.setdefault("name", PARTICLE_SHEET)
    meta.setdefault("file", PARTICLE_FILE)
    meta.setdefault("tile", PARTICLE_TILE)
    meta.setdefault("cols", PARTICLE_COLS)
    meta.setdefault("vanilla_tiles", VANILLA_TILES)
    meta.setdefault("next_id", VANILLA_TILES)
    meta.setdefault("frames", [])
    return meta


def infer_theme(text: str, fallback: str = "generic") -> str:
    blob = (text or "").lower().replace("_", " ").replace("-", " ")
    for key, canon in {**{k: k for k in THEMES}, **_THEME_ALIASES}.items():
        if key in blob:
            return canon
    return fallback if fallback in THEMES else "generic"


def resolve_theme(theme: Optional[str], *, name: str = "", color: Optional[Sequence[int]] = None) -> str:
    if theme:
        key = str(theme).strip().lower()
        return _THEME_ALIASES.get(key, key if key in THEMES else infer_theme(key, "generic"))
    guessed = infer_theme(name)
    if guessed != "generic":
        return guessed
    if color and len(color) >= 3:
        r, g, b = int(color[0]), int(color[1]), int(color[2])
        if r > g + 40 and r > b + 40:
            return "blood"
        if b > r + 20 and g > r:
            return "water" if g > 140 else "ice"
        if r > 180 and g > 180 and b > 180:
            return "steam"
        if r > 140 and g > 100 and b < 90:
            return "earth"
    return "generic"


def theme_rgb(theme: str, color: Optional[Sequence[int]] = None) -> Tuple[int, int, int]:
    if color and len(color) >= 3:
        return (int(color[0]), int(color[1]), int(color[2]))
    return tuple(THEMES.get(theme, THEMES["generic"])["rgb"])  # type: ignore[return-value]


def theme_rgba(theme: str, color: Optional[Sequence[int]] = None, alpha: int = 255) -> List[int]:
    r, g, b = theme_rgb(theme, color)
    a = int(color[3]) if color and len(color) >= 4 else int(alpha)
    return [r, g, b, max(0, min(255, a))]


class AtlasCache:
    """core_2 particles.png tiles. Index 0 is top-left (not ability-icon bottom-left)."""

    def __init__(self) -> None:
        self._img = None
        self._cols = PARTICLE_COLS
        self.count = VANILLA_TILES

    def image(self):
        if self._img is None:
            Image, _ = _pil()
            self._img = Image.open(vanilla_particles_png()).convert("RGBA")
            self._cols = max(1, self._img.width // PARTICLE_TILE)
            self.count = self._cols * max(1, self._img.height // PARTICLE_TILE)
        return self._img

    def crop(self, tile_id: int):
        Image, _ = _pil()
        img = self.image()
        tid = max(0, int(tile_id)) % max(1, self.count)
        col = tid % self._cols
        row = tid // self._cols
        box = (
            col * PARTICLE_TILE,
            row * PARTICLE_TILE,
            (col + 1) * PARTICLE_TILE,
            (row + 1) * PARTICLE_TILE,
        )
        cell = img.crop(box)
        if cell.size != (PARTICLE_TILE, PARTICLE_TILE):
            canvas = Image.new("RGBA", (PARTICLE_TILE, PARTICLE_TILE), (0, 0, 0, 0))
            canvas.paste(cell, (0, 0))
            return canvas
        return cell

    def tinted(self, tile_id: int, rgba: Optional[Sequence[int]] = None, scale: int = 6):
        Image, _ = _pil()
        cell = self.crop(tile_id)
        if rgba and len(rgba) >= 3 and tuple(int(x) for x in rgba[:3]) != (255, 255, 255):
            cell = multiply_tint(cell, rgba)
        if scale and scale != 1:
            cell = cell.resize((PARTICLE_TILE * scale, PARTICLE_TILE * scale), Image.Resampling.NEAREST)
        return cell


def multiply_tint(img, rgba: Sequence[int]):
    Image, _ = _pil()
    src = img.convert("RGBA")
    tr, tg, tb = int(rgba[0]), int(rgba[1]), int(rgba[2])
    ta = int(rgba[3]) if len(rgba) >= 4 else 255
    px = src.load()
    for y in range(src.height):
        for x in range(src.width):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            px[x, y] = (
                (r * tr) // 255,
                (g * tg) // 255,
                (b * tb) // 255,
                (a * ta) // 255,
            )
    return src


def pil_to_photo(img, tk_module, bg=(12, 14, 16)):
    """Tk PhotoImage without ImageTk. Composites onto a dark RGB canvas (PPM has no alpha)."""
    from io import BytesIO

    Image, _ = _pil()
    rgba = img.convert("RGBA")
    canvas = Image.new("RGB", rgba.size, tuple(int(x) for x in bg[:3]))
    canvas.paste(rgba, mask=rgba.split()[3])
    buf = BytesIO()
    canvas.save(buf, format="PPM")
    return tk_module.PhotoImage(data=buf.getvalue())


def particle_rgba(part: Dict[str, Any]) -> List[int]:
    color = part.get("color") if isinstance(part, dict) else None
    if isinstance(color, list) and color:
        row = color[0] if isinstance(color[0], list) else color
        if isinstance(row, (list, tuple)) and len(row) >= 3:
            rgba = [int(row[0]), int(row[1]), int(row[2]), int(row[3] if len(row) > 3 else 255)]
            return [max(0, min(255, n)) for n in rgba]
    return [255, 255, 255, 255]


def set_particle_rgba(part: Dict[str, Any], rgba: Sequence[int]) -> None:
    color = [max(0, min(255, int(x))) for x in list(rgba)[:4]]
    while len(color) < 4:
        color.append(255)
    part["color"] = [color]


def playback_span(anim: Dict[str, Any]) -> float:
    end = 80.0
    for part in anim.get("particles") or []:
        if not isinstance(part, dict):
            continue
        delay = float(part.get("delay") or 0)
        life = float(part.get("life") or 60)
        end = max(end, delay + life)
    return end


def _ensure_sheet_row(spec: Dict[str, Any], rows: int) -> None:
    from s2_assets import default_assets

    assets = spec.get("assets") or default_assets()
    spec["assets"] = assets
    sheets = (assets.get("graphics") or {}).setdefault("tilesheets", [])
    for sheet in sheets:
        if sheet.get("name") == PARTICLE_SHEET:
            sheet["tiles"] = [PARTICLE_COLS, int(rows)]
            sheet["file"] = PARTICLE_FILE
            return
    sheets.append({"name": PARTICLE_SHEET, "tiles": [PARTICLE_COLS, int(rows)], "file": PARTICLE_FILE})


def load_or_copy_atlas(spec: Dict[str, Any], root: Path) -> Any:
    Image, _ = _pil()
    dest = root / PARTICLE_FILE
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file():
        img = Image.open(dest).convert("RGBA")
    else:
        shutil.copy2(vanilla_particles_png(), dest)
        img = Image.open(dest).convert("RGBA")
    rows = max(VANILLA_ROWS, img.height // PARTICLE_TILE)
    _ensure_sheet_row(spec, rows)
    meta = atlas_meta(spec)
    occupied = VANILLA_TILES
    for row in meta.get("frames") or []:
        try:
            occupied = max(occupied, int(row["tile_id"]) + 1)
        except (KeyError, TypeError, ValueError):
            continue
    meta["next_id"] = max(int(meta.get("next_id") or VANILLA_TILES), occupied)
    return img


def _grow_atlas(img, min_tiles: int):
    Image, _ = _pil()
    rows_needed = max(VANILLA_ROWS, math.ceil(min_tiles / PARTICLE_COLS))
    new_h = rows_needed * PARTICLE_TILE
    if img.height >= new_h and img.width >= PARTICLE_COLS * PARTICLE_TILE:
        return img
    canvas = Image.new("RGBA", (PARTICLE_COLS * PARTICLE_TILE, new_h), (0, 0, 0, 0))
    canvas.paste(img, (0, 0))
    return canvas


def stamp_frames(img, tile_ids: Sequence[int], frames: Sequence) -> Any:
    Image, _ = _pil()
    need = max(tile_ids) + 1 if tile_ids else VANILLA_TILES
    canvas = _grow_atlas(img, need)
    for tid, src in zip(tile_ids, frames):
        cell = src.convert("RGBA") if hasattr(src, "convert") else Image.frombytes("RGBA", (PARTICLE_TILE, PARTICLE_TILE), src)
        if cell.size != (PARTICLE_TILE, PARTICLE_TILE):
            cell = cell.resize((PARTICLE_TILE, PARTICLE_TILE), Image.Resampling.NEAREST)
        col = int(tid) % PARTICLE_COLS
        row = int(tid) // PARTICLE_COLS
        canvas.paste(cell, (col * PARTICLE_TILE, row * PARTICLE_TILE), cell)
    return canvas


def save_atlas(spec: Dict[str, Any], root: Path, img) -> str:
    dest = root / PARTICLE_FILE
    dest.parent.mkdir(parents=True, exist_ok=True)
    write_png(dest, img.width, img.height, img.tobytes())
    rows = img.height // PARTICLE_TILE
    _ensure_sheet_row(spec, rows)
    return PARTICLE_FILE


def allocate_tile_ids(spec: Dict[str, Any], count: int, reuse: Optional[Sequence[int]] = None) -> List[int]:
    meta = atlas_meta(spec)
    if reuse:
        reused = [int(x) for x in reuse]
        if len(reused) >= count:
            return reused[:count]
        extra = count - len(reused)
        start = int(meta["next_id"])
        ids = reused + list(range(start, start + extra))
        meta["next_id"] = max(int(meta["next_id"]), max(ids) + 1)
        return ids
    start = int(meta["next_id"])
    ids = list(range(start, start + count))
    meta["next_id"] = start + count
    return ids


def _put(px, x: int, y: int, rgb: Sequence[int], a: int) -> None:
    if not (0 <= x < PARTICLE_TILE and 0 <= y < PARTICLE_TILE) or a <= 0:
        return
    r, g, b, oa = px[x, y]
    na = min(255, int(a))
    if oa == 0:
        px[x, y] = (int(rgb[0]), int(rgb[1]), int(rgb[2]), na)
        return
    out_a = min(255, oa + na - (oa * na) // 255)
    t = na / 255.0
    px[x, y] = (
        int(r * (1 - t) + rgb[0] * t),
        int(g * (1 - t) + rgb[1] * t),
        int(b * (1 - t) + rgb[2] * t),
        out_a,
    )


def _disc(px, cx: float, cy: float, radius: float, rgb: Sequence[int], alpha: int) -> None:
    r = max(0.4, radius)
    lo_x, hi_x = max(0, int(cx - r - 1)), min(PARTICLE_TILE - 1, int(cx + r + 1))
    lo_y, hi_y = max(0, int(cy - r - 1)), min(PARTICLE_TILE - 1, int(cy + r + 1))
    for y in range(lo_y, hi_y + 1):
        for x in range(lo_x, hi_x + 1):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if d <= r:
                fade = 1.0 - (d / r) * 0.35
                _put(px, x, y, rgb, int(alpha * fade))


def _ring(px, cx: float, cy: float, radius: float, width: float, rgb: Sequence[int], alpha: int) -> None:
    r = max(0.6, radius)
    lo_x, hi_x = max(0, int(cx - r - width - 1)), min(PARTICLE_TILE - 1, int(cx + r + width + 1))
    lo_y, hi_y = max(0, int(cy - r - width - 1)), min(PARTICLE_TILE - 1, int(cy + r + width + 1))
    for y in range(lo_y, hi_y + 1):
        for x in range(lo_x, hi_x + 1):
            d = abs(math.hypot(x + 0.5 - cx, y + 0.5 - cy) - r)
            if d <= width:
                _put(px, x, y, rgb, int(alpha * (1.0 - d / max(width, 0.01))))


def draw_procedural_frame(
    *,
    theme: str,
    kind: str,
    index: int,
    count: int,
    rgb: Sequence[int],
):
    Image, _ = _pil()
    img = Image.new("RGBA", (PARTICLE_TILE, PARTICLE_TILE), (0, 0, 0, 0))
    px = img.load()
    t = (index + 1) / max(1, count)
    hi = (min(255, int(rgb[0] * 1.25)), min(255, int(rgb[1] * 1.25)), min(255, int(rgb[2] * 1.25)))
    lo = (max(0, int(rgb[0] * 0.55)), max(0, int(rgb[1] * 0.55)), max(0, int(rgb[2] * 0.55)))
    cx = cy = 7.5
    kind = (kind or "projectile").lower()

    if kind in ("aoe", "burst", "impact") and theme == "steam":
        rad = 1.4 + t * 4.8
        _disc(px, cx, cy, 1.0 + t * 1.4, hi, 110)
        puffs = 4 + index
        for k in range(puffs):
            ang = k * (2 * math.pi / puffs) + index * 0.35
            _disc(px, cx + math.cos(ang) * rad, cy + math.sin(ang) * rad * 0.85, 1.7 + t * 0.8, rgb, 200)
            _disc(px, cx + math.cos(ang) * rad * 0.55, cy + math.sin(ang) * rad * 0.5, 1.2, hi, 150)
    elif kind in ("aoe", "burst", "impact"):
        _ring(px, cx, cy, 1.2 + t * 5.2, 1.15, hi, 230)
        _disc(px, cx, cy, 0.8 + t * 2.2, rgb, 200 - int(70 * t))
        if t > 0.45:
            for ang in (0.4, 1.5, 2.6, 3.8, 5.1):
                _disc(px, cx + math.cos(ang) * 4.5 * t, cy + math.sin(ang) * 4.5 * t, 1.1, lo, 160)
    elif kind in ("cloud",):
        _disc(px, cx - 1.5, cy + 0.5, 2.0 + t * 3.0, rgb, 180)
        _disc(px, cx + 1.8, cy - 0.8, 1.6 + t * 2.6, hi, 170)
        _disc(px, cx, cy - 1.6 * t, 1.4 + t * 2.2, lo, 150)
    elif kind in ("wave",):
        y = 11 - t * 5
        _ring(px, cx, y, 2.0 + t * 4.0, 1.2, rgb, 220)
        _disc(px, cx, y - 1, 1.2 + t, hi, 180)
    elif kind in ("line",):
        length = 3 + int(t * 9)
        for i in range(length):
            _put(px, 2 + i, 7 + (i % 3) - 1, hi if i > length // 2 else rgb, 230)
            _put(px, 2 + i, 8 + (i % 3) - 1, lo, 160)
        _disc(px, 2 + length, 7.5, 1.3, hi, 240)
    elif kind in ("melee", "dash"):
        _ring(px, cx, cy, 2.0 + t * 3.5, 1.1, rgb, 210)
        _disc(px, cx + 2 * t, cy - 2 * t, 1.4, hi, 200)
    elif kind in ("self",):
        _disc(px, cx, cy, 1.2 + t * 2.0, hi, 220)
        _ring(px, cx, cy, 3.0 + t * 2.0, 0.9, rgb, 180)
    else:
        # projectile / bolt
        _disc(px, cx - 2 + t, cy, 1.4 + t * 1.6, rgb, 230)
        _disc(px, cx + 1 + t, cy, 1.0 + t, hi, 200)
        if t > 0.35:
            _disc(px, cx - 4, cy + 0.5, 1.1, lo, 140)
    return img


_KIND_SHOT = {
    "aoe": "expanding burst, each frame larger than the last",
    "burst": "impact explosion growing then fading",
    "impact": "hit spark then splash debris",
    "cloud": "wispy cloud puffs drifting and spreading",
    "wave": "traveling crest / splash, side view of a wave front",
    "line": "horizontal energy bolt or jet, point on the right, trail on the left",
    "projectile": "small flying bolt or orb, trailing particles",
    "melee": "spinning swirl around the center",
    "dash": "motion streak dash",
    "self": "aura sparkle around the caster",
}


def knockout_particle_bg(img, dark: int = 28, light: int = 232):
    """Particles overlay the world — knock out both near-black and near-white canvas."""
    Image, _ = _pil()
    rgba = img.convert("RGBA")
    px = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = px[x, y]
            if r <= dark and g <= dark and b <= dark:
                px[x, y] = (0, 0, 0, 0)
            elif r >= light and g >= light and b >= light:
                px[x, y] = (0, 0, 0, 0)
    return rgba


def fit_particle_tile(img):
    """512 SD frame → chunky 16×16 glyph (32px contain, then nearest)."""
    Image, _ = _pil()
    from PIL import ImageEnhance, ImageOps

    rgba = knockout_particle_bg(img)
    rgba = ImageEnhance.Contrast(rgba).enhance(1.2)
    mid = ImageOps.contain(rgba, (32, 32), method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    canvas.paste(mid, ((32 - mid.width) // 2, (32 - mid.height) // 2), mid)
    return canvas.resize((PARTICLE_TILE, PARTICLE_TILE), Image.Resampling.NEAREST)


def _particle_frame_prompt(theme: str, kind: str, index: int, count: int) -> str:
    subject = THEMES.get(theme, THEMES["generic"])["prompt"]
    if theme == "steam":
        shot = "soft rounded steam cloud puff, billowing white vapor, not spikes, not starburst, not fire"
    elif theme == "blood":
        shot = "wet crimson blood splash and droplets, not a geometric star"
    elif theme == "water" and kind in ("projectile", "line"):
        shot = "pressurized cyan water jet bolt, liquid spear, not lightning, not fire"
    else:
        shot = _KIND_SHOT.get(kind, _KIND_SHOT["projectile"])
    stages = (
        "tiny just starting",
        "growing",
        "full intensity peak",
        "breaking apart",
        "dissipating wisps",
        "last fading specks",
    )
    stage = stages[min(index, len(stages) - 1)]
    return (
        f"Soulash 2 single particle glyph, one {kind} VFX sprite only, {stage}, "
        f"{shot}, {subject}, centered on pure black, chunky 16-bit pixel art, "
        "no sprite sheet, no grid, no collage, no multiple objects, no text, no UI, no letters"
    )


def draw_sd_strip(
    *,
    theme: str,
    kind: str,
    count: int,
    api_url: str,
    work: Path,
    name: str,
    steps: int = 28,
):
    """One SD image per frame → 16×16 glyphs. Raises if a frame is empty."""
    from s2_icon_pipeline import NEGATIVE, seed_from_name
    from sd_http_client import generate_image, plan_sd_size

    Image, _ = _pil()
    count = max(1, int(count))
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    gw, gh, plan_steps = plan_sd_size(512, 512, kind="sprite")
    negative = (
        NEGATIVE
        + ", sprite sheet, contact sheet, collage, grid, multiple frames, "
        "UI icon, skill emblem, placeholder, checkerboard, text, letters"
    )
    frames = []
    base_seed = seed_from_name(f"{name}_{theme}")
    for i in range(count):
        raw_path = work / f"{name}_{theme}_{i}_raw.png"
        print(f"[anim-art] SD frame {i + 1}/{count} {name}")
        generate_image(
            _particle_frame_prompt(theme, kind, i, count),
            raw_path,
            api_url=api_url,
            negative_prompt=negative,
            width=gw,
            height=gh,
            steps=max(int(steps), int(plan_steps)),
            guidance_scale=7.2,
            seed=base_seed + i * 17,
        )
        tile = fit_particle_tile(Image.open(raw_path))
        extrema = tile.getextrema()
        alpha_max = extrema[3][1] if len(extrema) > 3 else 0
        if alpha_max < 20:
            raise RuntimeError(f"SD particle {name} frame {i + 1}/{count} was empty after knockout")
        frames.append(tile)
    return frames


def animation_kind(anim: Dict[str, Any], preset: Optional[str] = None) -> str:
    if preset:
        from s2_animations import PRESETS

        meta = PRESETS.get(str(preset).lower()) or {}
        if meta.get("kind"):
            return str(meta["kind"])
    name = str(anim.get("name") or anim.get("id") or "").lower()
    if any(w in name for w in ("nova", "burst", "explode", "erupt")):
        return "aoe"
    if any(w in name for w in ("wave", "tide", "surge")):
        return "wave"
    if any(w in name for w in ("fog", "cloud", "mist", "steam")):
        return "cloud"
    if any(w in name for w in ("hit", "impact", "splash")):
        return "impact"
    if any(w in name for w in ("bolt", "lance", "shot", "missile")):
        return "projectile"
    if anim.get("chain_particles"):
        return "projectile"
    return "projectile"


def apply_tile_ids(anim: Dict[str, Any], tile_ids: Sequence[int], *, keep_tint: bool = False) -> None:
    parts = [p for p in (anim.get("particles") or []) if isinstance(p, dict)]
    if not parts or not tile_ids:
        return
    n = len(tile_ids)
    last = n - 1
    for i, part in enumerate(parts):
        if n >= len(parts):
            part["tile_id"] = int(tile_ids[i])
        else:
            part["tile_id"] = int(tile_ids[min(i * n // len(parts), last)])
        if not keep_tint:
            part["color"] = [[255, 255, 255, 255]]


def paint_animation(
    spec: Dict[str, Any],
    anim: Dict[str, Any],
    *,
    root: Optional[Path] = None,
    theme: Optional[str] = None,
    kind: Optional[str] = None,
    color: Optional[Sequence[int]] = None,
    use_sd: bool = False,
    api_url: Optional[str] = None,
    overwrite: bool = True,
    keep_tint: bool = False,
    steps: int = 24,
) -> List[int]:
    """Generate glyphs for one animation, stamp them on the atlas, remap tile_id."""
    dest = Path(root) if root else staging_dir(spec)
    parts = [p for p in (anim.get("particles") or []) if isinstance(p, dict)]
    if not parts:
        return []
    theme_id = resolve_theme(theme, name=str(anim.get("name") or anim.get("id") or ""), color=color)
    rgb = theme_rgb(theme_id, color)
    motion = kind or animation_kind(anim)
    count = len(parts)
    if use_sd:
        if not api_url:
            raise RuntimeError("SD server not reachable; refusing placeholder particle circles")
        count = min(count, 4)
    prev = (anim.get("_art") or {}).get("tile_ids")
    tile_ids = allocate_tile_ids(spec, count, reuse=prev)
    work = dest / "_sd_work"
    name = str(anim.get("id") or "fx")
    if use_sd:
        print(f"[anim-art] SD {name} theme={theme_id} kind={motion} frames={count}")
        frames = draw_sd_strip(
            theme=theme_id,
            kind=motion,
            count=count,
            api_url=api_url,
            work=work,
            name=name,
            steps=max(int(steps), 28),
        )
    else:
        frames = [
            draw_procedural_frame(theme=theme_id, kind=motion, index=i, count=count, rgb=rgb)
            for i in range(count)
        ]
    atlas = load_or_copy_atlas(spec, dest)
    atlas = stamp_frames(atlas, tile_ids, frames)
    save_atlas(spec, dest, atlas)
    apply_tile_ids(anim, tile_ids, keep_tint=keep_tint)
    meta = atlas_meta(spec)
    kept = [row for row in meta["frames"] if row.get("animation") != anim.get("id")]
    for i, tid in enumerate(tile_ids):
        kept.append({"animation": anim.get("id"), "tile_id": tid, "theme": theme_id, "frame": i})
    meta["frames"] = kept
    anim["_art"] = {"theme": theme_id, "kind": motion, "tile_ids": tile_ids, "source": "sd" if (use_sd and api_url) else "procedural"}
    return list(tile_ids)


def paint_animations(
    spec: Dict[str, Any],
    anims: Iterable[Dict[str, Any]],
    *,
    root: Optional[Path] = None,
    theme: Optional[str] = None,
    color: Optional[Sequence[int]] = None,
    use_sd: bool = False,
    overwrite: bool = True,
    keep_tint: bool = False,
    steps: int = 24,
    dry_run: bool = False,
) -> List[str]:
    dest = Path(root) if root else staging_dir(spec)
    rows: List[str] = []
    wanted = [a for a in anims if isinstance(a, dict) and a.get("particles")]
    if dry_run:
        for anim in wanted:
            theme_id = resolve_theme(theme, name=str(anim.get("name") or anim.get("id") or ""), color=color)
            rows.append(f"{anim.get('id')} theme={theme_id} kind={animation_kind(anim)} frames={len(anim.get('particles') or [])}")
        return rows
    from s2_icon_pipeline import sd_session

    with sd_session(use_sd=use_sd, timeout_sec=600.0) as api_url:
        if use_sd and not api_url:
            raise RuntimeError(
                "SD server not reachable; refusing placeholder particle circles. "
                "Start the local SD server or pass --no-sd only if you want procedural art."
            )
        for anim in wanted:
            ids = paint_animation(
                spec,
                anim,
                root=dest,
                theme=theme,
                color=color,
                use_sd=bool(use_sd),
                api_url=api_url,
                overwrite=overwrite,
                keep_tint=keep_tint,
                steps=steps,
            )
            art = anim.get("_art") or {}
            rows.append(f"{anim.get('id')} {art.get('source')} {art.get('theme')} tiles={ids}")
    return rows


def strip_particle_overlay(spec: Dict[str, Any], *, root: Optional[Path] = None) -> List[str]:
    """Remove a per-skill particles32 overlay so later skills do not fight over the atlas."""
    spec.pop("particle_atlas", None)
    graphics = (spec.get("assets") or {}).setdefault("graphics", {})
    sheets = list(graphics.get("tilesheets") or [])
    graphics["tilesheets"] = [s for s in sheets if s.get("name") != PARTICLE_SHEET]
    for anim in spec.get("animations") or []:
        if isinstance(anim, dict):
            anim.pop("_art", None)
    removed: List[str] = []
    if root:
        dest = Path(root) / PARTICLE_FILE
        if dest.is_file():
            dest.unlink()
            removed.append(PARTICLE_FILE)
    return removed


def ensure_particle_sheet_on_write(spec: Dict[str, Any], root: Path) -> Optional[str]:
    """Copy vanilla particles.png if the spec registered particles32 but the file is missing."""
    sheets = ((spec.get("assets") or {}).get("graphics") or {}).get("tilesheets") or []
    if not any(s.get("name") == PARTICLE_SHEET for s in sheets) and not spec.get("particle_atlas"):
        return None
    dest = root / PARTICLE_FILE
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file():
        Image, _ = _pil()
        img = Image.open(dest)
        _ensure_sheet_row(spec, max(VANILLA_ROWS, img.height // PARTICLE_TILE))
        return None
    shutil.copy2(vanilla_particles_png(), dest)
    _ensure_sheet_row(spec, VANILLA_ROWS)
    return PARTICLE_FILE
