#!/usr/bin/env python3
"""Labeled PNG previews of Soulash 2 FX for vision-capable agents.

The engine only shows particles32 glyphs. These sheets let an AI *look* at the
tinted clone (strip + playback + optional preset compare) before committing it
to a skill spec. They are not shipped in the mod.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from s2_animations import PRESETS
from s2_assets import load_animation
from s2_particle_art import (
    PARTICLE_TILE,
    AtlasCache,
    infer_theme,
    particle_rgba,
    playback_span,
    resolve_theme,
    theme_rgba,
)
from s2_paths import output_root
from s2_schema import slug_name

_BG = (16, 18, 20)
_INK = (232, 228, 217)
_MUTED = (154, 149, 136)
_ACCENT = (122, 168, 196)
_PANEL = (30, 34, 38)
_COMPARE = ("bolt", "nova", "wave", "line", "burst", "fog", "rain", "geyser", "frost", "lunge")


def _pil():
    from PIL import Image, ImageDraw, ImageFont

    return Image, ImageDraw, ImageFont


def _font(size: int = 13):
    _, _, ImageFont = _pil()
    for name in ("segoeui.ttf", "SegoeUI.ttf", "arial.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def preview_root(spec_path: Optional[Path] = None) -> Path:
    """PNG manifests for vision. Never under a shippable mod folder.

    The game loads leftover JSON in ``data/mods/<id>/``. Putting ``manifest.json``
    with ``tile_id: null`` next to abilities/animations crashes the engine.
    """
    if spec_path:
        folder = Path(spec_path)
        if folder.is_file():
            folder = folder.parent
        sid = folder.name or "preview"
        return output_root() / "_fx_preview" / sid
    return output_root() / "_fx_preview"


def follow_preview_anim(anim: Dict[str, Any]) -> Dict[str, Any]:
    """Containers like Heavy Rain have no particles; preview the inner FX."""
    parts = [p for p in (anim.get("particles") or []) if isinstance(p, dict)]
    inner = anim.get("animation")
    if parts or not inner:
        return anim
    try:
        child = load_animation(str(inner))
    except FileNotFoundError:
        return anim
    return child


def particle_summary(anim: Dict[str, Any]) -> List[Dict[str, Any]]:
    src = follow_preview_anim(anim)
    rows = []
    for i, part in enumerate(src.get("particles") or []):
        if not isinstance(part, dict):
            continue
        rows.append(
            {
                "index": i,
                "tile_id": part.get("tile_id"),
                "delay": part.get("delay") or 0,
                "life": part.get("life"),
                "flags": part.get("flags"),
                "velocity": part.get("velocity"),
                "on_impact": part.get("on_impact") or "",
                "color": particle_rgba(part),
            }
        )
    return rows


def _text(draw, xy, text: str, fill=_INK, size: int = 13) -> None:
    draw.text(xy, text, fill=fill, font=_font(size))


def _composite_rgb(tile, bg=_BG):
    Image, _, _ = _pil()
    rgba = tile.convert("RGBA")
    canvas = Image.new("RGB", rgba.size, bg)
    canvas.paste(rgba, mask=rgba.split()[3])
    return canvas


def render_strip(
    anim: Dict[str, Any],
    *,
    atlas: Optional[AtlasCache] = None,
    scale: int = 5,
    caption: str = "",
) -> Any:
    """One labeled tile per particle, left to right. Captions are meant to be read by vision models."""
    Image, ImageDraw, _ = _pil()
    atlas = atlas or AtlasCache()
    src = follow_preview_anim(anim)
    parts = [p for p in (src.get("particles") or []) if isinstance(p, dict)]
    cell = PARTICLE_TILE * scale + 8
    label_h = 36
    head = 44
    n = max(1, len(parts))
    w = max(480, 16 + n * cell)
    h = head + cell + label_h + 12
    img = Image.new("RGB", (w, h), _BG)
    draw = ImageDraw.Draw(img)
    title = caption or f"{anim.get('name') or anim.get('id')}  id={anim.get('id')}"
    if src is not anim:
        title += f"  inner={src.get('id')}"
    _text(draw, (10, 8), title, _ACCENT, 14)
    _text(draw, (10, 26), "particles32 glyphs (top-left index 0). Labels: #  tile_id  delay", _MUTED, 11)
    if not parts:
        _text(draw, (10, head + 20), "(no particles — container FX only)", _MUTED, 13)
        return img
    for i, part in enumerate(parts):
        x = 8 + i * cell
        y = head
        tid = int(part.get("tile_id") or 0)
        tile = atlas.tinted(tid, particle_rgba(part), scale=scale)
        img.paste(_composite_rgb(tile, _PANEL), (x + 4, y + 4))
        delay = part.get("delay") or 0
        line = f"#{i}  t{tid}"
        _text(draw, (x + 4, y + cell - 2), line, _INK, 11)
        extra = f"d{int(delay)}"
        if part.get("on_impact"):
            extra += f" →{part['on_impact']}"
        _text(draw, (x + 4, y + cell + 14), extra, _MUTED, 10)
    return img


def render_playback(
    anim: Dict[str, Any],
    *,
    atlas: Optional[AtlasCache] = None,
    frames: int = 8,
    scale: int = 4,
) -> Any:
    """Time slices. Each row is a moment; living particles are drawn in that row."""
    Image, ImageDraw, _ = _pil()
    atlas = atlas or AtlasCache()
    src = follow_preview_anim(anim)
    parts = [p for p in (src.get("particles") or []) if isinstance(p, dict)]
    span = max(80.0, playback_span(src))
    cell = PARTICLE_TILE * scale + 6
    row_h = cell + 8
    head = 36
    w = max(420, 70 + max(1, len(parts)) * cell)
    h = head + frames * row_h + 8
    img = Image.new("RGB", (w, h), _BG)
    draw = ImageDraw.Draw(img)
    _text(draw, (10, 8), f"playback {anim.get('name') or anim.get('id')}  span={int(span)}", _ACCENT, 13)
    _text(draw, (10, 24), "each row = time; only particles whose delay..delay+life overlap that time", _MUTED, 10)
    if not parts:
        return img
    for f in range(frames):
        t = span * (f + 0.5) / frames
        y = head + f * row_h
        _text(draw, (6, y + 10), f"t={int(t)}", _MUTED, 11)
        x = 64
        for part in parts:
            delay = float(part.get("delay") or 0)
            life = float(part.get("life") or 80)
            if not (delay <= t < delay + max(life, 1)):
                x += cell
                continue
            tid = int(part.get("tile_id") or 0)
            tile = atlas.tinted(tid, particle_rgba(part), scale=scale)
            img.paste(_composite_rgb(tile, _PANEL), (x, y + 4))
            x += cell
    return img


def render_compare(
    *,
    name: str,
    theme: str,
    presets: Optional[Sequence[str]] = None,
    atlas: Optional[AtlasCache] = None,
    scale: int = 3,
) -> Any:
    """Grid of motion presets with the same tint so a vision model can pick the right choreography."""
    from s2_animations import compose_animation

    Image, ImageDraw, _ = _pil()
    atlas = atlas or AtlasCache()
    keys = list(presets or _COMPARE)
    rgba = theme_rgba(theme)
    cols = 5
    rows = (len(keys) + cols - 1) // cols
    thumb_n = 4
    cell_w = 16 + thumb_n * (PARTICLE_TILE * scale + 4)
    cell_h = 48 + PARTICLE_TILE * scale
    img = Image.new("RGB", (16 + cols * cell_w, 40 + rows * cell_h), _BG)
    draw = ImageDraw.Draw(img)
    _text(draw, (10, 8), f"preset compare  theme={theme}  name={name!r}  pick the motion that matches", _ACCENT, 14)
    _text(draw, (10, 24), "If color is wrong keep the preset and change --art. If motion is wrong change --preset.", _MUTED, 11)
    for i, key in enumerate(keys):
        meta = PRESETS.get(key) or {}
        col, row = i % cols, i // cols
        x = 8 + col * cell_w
        y = 40 + row * cell_h
        draw.rectangle((x, y, x + cell_w - 8, y + cell_h - 8), outline=_PANEL)
        try:
            anims = compose_animation(preset=key, new_id=f"cmp_{key}", name=name, color=rgba, clone_impact=False)
            src = follow_preview_anim(anims[0])
            parts = [p for p in (src.get("particles") or []) if isinstance(p, dict)][:thumb_n]
        except (FileNotFoundError, KeyError, ValueError):
            parts = []
        _text(draw, (x + 6, y + 4), f"--preset {key}", _INK, 12)
        _text(draw, (x + 6, y + 20), str(meta.get("look") or meta.get("blurb") or "")[:42], _MUTED, 10)
        px = x + 6
        py = y + 38
        for part in parts:
            tid = int(part.get("tile_id") or 0)
            tile = atlas.tinted(tid, particle_rgba(part), scale=scale)
            img.paste(_composite_rgb(tile, _PANEL), (px, py))
            px += PARTICLE_TILE * scale + 4
    return img


def save_png(path: Path, img) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(path, "PNG")
    return str(path)


def write_preview_pack(
    anim: Dict[str, Any],
    dest: Path,
    *,
    extras: Optional[Iterable[Dict[str, Any]]] = None,
    theme: str = "",
    plan: Optional[Dict[str, Any]] = None,
    compare: bool = False,
    name: str = "",
) -> Dict[str, Any]:
    """Write strip.png, playback.png, optional compare.png + manifest.json. Returns the manifest."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    atlas = AtlasCache()
    caption = f"{anim.get('name') or anim.get('id')}  theme={theme or '-'}  look={(plan or {}).get('look') or ''}"
    strip = render_strip(anim, atlas=atlas, caption=caption)
    playback = render_playback(anim, atlas=atlas)
    files = {
        "strip": save_png(dest / "strip.png", strip),
        "playback": save_png(dest / "playback.png", playback),
    }
    if compare:
        files["compare"] = save_png(
            dest / "compare.png",
            render_compare(name=name or str(anim.get("name") or ""), theme=theme or infer_theme(str(anim.get("name") or "")), atlas=atlas),
        )
    extra_files = []
    for extra in extras or []:
        eid = slug_name(str(extra.get("id") or "hit")).lower()
        extra_files.append(
            save_png(dest / f"impact_{eid}.png", render_strip(extra, atlas=atlas, caption=f"impact {extra.get('id')}"))
        )
    manifest = {
        "id": anim.get("id"),
        "name": anim.get("name"),
        "theme": theme,
        "plan": plan or {},
        "inner": None if follow_preview_anim(anim) is anim else follow_preview_anim(anim).get("id"),
        "particles": particle_summary(anim),
        "files": files,
        "impacts": extra_files,
        "how_to_retune": {
            "wrong_color": "produce-fx ... --art <theme>  (water/blood/steam/ice/lightning/earth/fire/poison/arcane)",
            "wrong_motion": "produce-fx ... --preset <key>  (see compare.png or list-anim-presets --json)",
            "wrong_impact": "add --clone-impact or --on-impact <id>",
            "do_not": "do not copy particles.png or invent a second atlas name",
        },
    }
    man_path = dest / "manifest.json"
    man_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    manifest["manifest"] = str(man_path)
    return manifest
