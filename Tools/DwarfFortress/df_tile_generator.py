#!/usr/bin/env python3
"""Generate DF creature part sheets (32x32 × 7 × 5) and 96x96 portraits."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from df_creature_schema import load_spec
from df_pixel_art import (
    COLS,
    PARTS,
    ROWS,
    STATES,
    TILE,
    accent_from_spec,
    compose_preview,
    features_from_spec,
    render_part_tile,
    render_portrait,
    render_sheet,
)
from df_sd_client import generate_sd_draft


def _color_from_id(creature_id: str, art_prompt: str = "") -> Tuple[int, int, int]:
    h = hashlib.md5(f"{creature_id}:{art_prompt}".encode("utf-8")).hexdigest()
    r = 40 + int(h[0:2], 16) % 180
    g = 40 + int(h[2:4], 16) % 180
    b = 40 + int(h[4:6], 16) % 180
    return r, g, b


def _try_pillow():
    try:
        from PIL import Image, ImageDraw  # type: ignore

        return Image, ImageDraw
    except ImportError:
        return None, None


def _draw_part_silhouette(
    draw,
    box,
    part: str,
    color: Tuple[int, int, int],
    state: str,
    features: Optional[Dict[str, Any]] = None,
) -> None:
    """Paste a procedural 32x32 part into an ImageDraw target (legacy worker path)."""
    x0, y0, _, _ = box
    tile = render_part_tile(part, state, color, features)
    im = getattr(draw, "_image", None) or getattr(draw, "im", None)
    if im is not None and hasattr(im, "paste"):
        im.paste(tile, (x0, y0), tile)
        return
    # Fallback: stamp opaque pixels via point draws
    px = tile.load()
    w, h = tile.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a:
                draw.point((x0 + x, y0 + y), fill=(r, g, b, a))


def generate_pillow_sheet(
    out_path: Path,
    creature_id: str,
    art_prompt: str = "",
    color: Optional[Tuple[int, int, int]] = None,
    features: Optional[Dict[str, Any]] = None,
) -> Path:
    Image, _ = _try_pillow()
    if Image is None:
        raise RuntimeError("Pillow (PIL) is required for procedural tile generation")

    feat = dict(features or {})
    feat.setdefault("id", creature_id)
    feat.setdefault("prompt", art_prompt)
    col = color or _color_from_id(creature_id, art_prompt)
    img = render_sheet(col, feat)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return out_path


def generate_pillow_portrait(
    out_path: Path,
    creature_id: str,
    art_prompt: str = "",
    color: Optional[Tuple[int, int, int]] = None,
    features: Optional[Dict[str, Any]] = None,
) -> Path:
    Image, _ = _try_pillow()
    if Image is None:
        raise RuntimeError("Pillow (PIL) is required for procedural tile generation")

    feat = dict(features or {})
    feat.setdefault("id", creature_id)
    feat.setdefault("prompt", art_prompt)
    col = color or _color_from_id(creature_id, art_prompt)
    img = render_portrait(col, feat)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return out_path


def _downscale_to_sheet(src: Path, dest: Path) -> Path:
    Image, _ = _try_pillow()
    if Image is None:
        raise RuntimeError("Pillow required to process SD output")
    im = Image.open(src).convert("RGBA")
    # Place scaled SD art into body cell and derive silhouettes for other parts
    sheet = Image.new("RGBA", (TILE * COLS, TILE * ROWS), (0, 0, 0, 0))
    body = im.resize((TILE, TILE), Image.Resampling.NEAREST)
    for row in range(ROWS):
        for col_i in range(COLS):
            # slight crop offsets per part
            ox = (col_i * 3) % max(1, im.width - TILE)
            oy = (row * 5) % max(1, im.height - TILE)
            crop = im.crop((ox, oy, ox + min(TILE * 4, im.width), oy + min(TILE * 4, im.height)))
            tile = crop.resize((TILE, TILE), Image.Resampling.NEAREST)
            sheet.paste(tile, (col_i * TILE, row * TILE), tile)
    # Ensure body column uses the main resize
    for row in range(ROWS):
        sheet.paste(body, (1 * TILE, row * TILE), body)
    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dest)
    return dest


def generate_art_for_spec(
    spec: Dict[str, Any],
    mod_root: Path,
    *,
    no_sd: bool = False,
    force: bool = False,
    workers: Optional[int] = None,
) -> Dict[str, Path]:
    cid = str(spec["id"]).upper()
    cid_l = cid.lower()
    images = Path(mod_root) / "graphics" / "images"
    images.mkdir(parents=True, exist_ok=True)
    body_path = images / f"{cid_l}_body.png"
    portrait_path = images / f"{cid_l}_portrait.png"
    preview_path = images / f"{cid_l}_preview.png"
    prompt = str(spec.get("art_prompt") or f"fantasy {spec.get('name_singular', cid)} pixel art")
    feat = features_from_spec(spec)
    rgb = accent_from_spec(spec)

    used_sd = False
    if not no_sd:
        draft = images / f"{cid_l}_sd_draft.png"
        result = generate_sd_draft(
            prompt=f"{prompt}, dwarf fortress tileset style, full body creature, pixel art",
            output_path=draft,
            negative_prompt="photo, blurry, text, watermark, 3d render",
            width=512,
            height=512,
            force=force,
            lock_label=f"df_art_{cid_l}",
        )
        if result.ok and result.output_path:
            try:
                _downscale_to_sheet(result.output_path, body_path)
                Image, _ = _try_pillow()
                if Image:
                    im = Image.open(result.output_path).convert("RGBA")
                    im.resize((96, 96), Image.Resampling.NEAREST).save(portrait_path)
                used_sd = True
            except Exception as exc:
                print(f"  [WARN] SD postprocess failed, falling back to Pillow: {exc}")

    if not used_sd or not body_path.exists():
        if workers and workers > 1:
            from df_workers import generate_art_sheet_parallel

            packed = generate_art_sheet_parallel(
                cid, prompt, rgb, workers=workers, features=feat
            )
            sheet = packed["sheet"]
            body_path.parent.mkdir(parents=True, exist_ok=True)
            sheet.save(body_path)
        else:
            generate_pillow_sheet(body_path, cid, prompt, rgb, features=feat)
    if not used_sd or not portrait_path.exists():
        generate_pillow_portrait(portrait_path, cid, prompt, rgb, features=feat)

    try:
        preview = compose_preview(rgb, feat, size=96)
        preview.save(preview_path)
    except Exception as exc:
        print(f"  [WARN] preview compose failed: {exc}")
        preview_path = portrait_path

    return {
        "body": body_path,
        "portrait": portrait_path,
        "preview": preview_path,
        "sd": used_sd,
    }


def generate_preview_for_spec(spec: Dict[str, Any], mod_root: Path) -> Dict[str, Path]:
    """Fast assembled preview + portrait for the Studio GUI (no full sheet)."""
    cid_l = str(spec["id"]).lower()
    images = Path(mod_root) / "graphics" / "images"
    images.mkdir(parents=True, exist_ok=True)
    feat = features_from_spec(spec)
    rgb = accent_from_spec(spec)
    preview_path = images / f"{cid_l}_preview.png"
    portrait_path = images / f"{cid_l}_portrait.png"
    compose_preview(rgb, feat, size=96).save(preview_path)
    generate_pillow_portrait(
        portrait_path,
        str(spec["id"]),
        str(spec.get("art_prompt") or ""),
        rgb,
        features=feat,
    )
    return {"preview": preview_path, "portrait": portrait_path}


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Generate DF creature tiles")
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--mod-root", type=Path, required=True)
    ap.add_argument("--no-sd", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    spec = load_spec(args.spec)
    paths = generate_art_for_spec(spec, args.mod_root, no_sd=args.no_sd, force=args.force)
    print(paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
