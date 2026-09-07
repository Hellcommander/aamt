#!/usr/bin/env python3
"""
Unique Transcendence ship ArmorDisplay / ShieldDisplay asset export.

Builds Sapphire-layout HUD art from the ship hero (or sketch), styled by
armor/shield ItemType families from base game + DLC + Extensions (via
tx_item_alt_mesh). Seeds Source/Models/Alt for user touch-ups.

Disable with unique_hud=False / --no-unique-hud.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tx_item_alt_mesh import (
    catalog_armor_shield_items,
    family_color,
    pick_default_items,
    resolve_alt_mesh,
    seed_alt_mesh_pool,
)
from ship_hud_alt_textures import resolve_alt_texture


HUD_SIZE = 136
SHIELD_LEVELS = 6  # maxValue 0,24,49,74,99,100 — stacked top=full

# Sapphire ArmorHUD.bmp segment atlas rects + paint positions
SEGMENTS: List[Dict[str, Any]] = [
    {
        "name": "forward",
        "segment": 0,
        "x": 0,
        "y": 0,
        "w": 52,
        "h": 29,
        "destX": 42,
        "destY": 15,
        "hpX": 55,
        "hpY": 14,
        "nameY": 8,
        "nameBreakWidth": 200,
        "nameDestX": 0,
        "nameDestY": 10,
    },
    {
        "name": "starboard",
        "segment": 3,
        "x": 52,
        "y": 0,
        "w": 22,
        "h": 59,
        "destX": 92,
        "destY": 45,
        "hpX": 95,
        "hpY": 60,
        "nameY": 30,
        "nameBreakWidth": 360,
        "nameDestX": 12,
        "nameDestY": 0,
    },
    {
        "name": "port",
        "segment": 1,
        "x": 142,
        "y": 0,
        "w": 22,
        "h": 59,
        "destX": 22,
        "destY": 45,
        "hpX": 15,
        "hpY": 60,
        "nameY": 52,
        "nameBreakWidth": 200,
        "nameDestX": 0,
        "nameDestY": 8,
    },
    {
        "name": "aft",
        "segment": 2,
        "x": 74,
        "y": 0,
        "w": 68,
        "h": 14,
        "destX": 34,
        "destY": 103,
        "hpX": 55,
        "hpY": 105,
        "nameY": 74,
        "nameBreakWidth": 360,
        "nameDestX": 12,
        "nameDestY": 0,
    },
]
ATLAS_W = 164
ATLAS_H = 59


def _load_rgba(path: Path, size: Tuple[int, int]) -> Any:
    from PIL import Image

    im = Image.open(path).convert("RGBA")
    return im.resize(size, Image.Resampling.LANCZOS)


def _silhouette(src: Any, tint: Tuple[int, int, int], bg: Tuple[int, int, int] = (8, 10, 14)) -> Any:
    from PIL import Image

    rgba = src.convert("RGBA")
    px = rgba.load()
    w, h = rgba.size
    out = Image.new("RGBA", (w, h), (*bg, 255))
    op = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 24:
                continue
            lum = (r + g + b) / 3.0
            # Treat near-black JPG hero as empty
            if a == 255 and lum < 12:
                continue
            strength = max(0.25, min(1.0, (lum / 180.0) if a == 255 else (a / 255.0)))
            op[x, y] = (
                int(tint[0] * strength + bg[0] * (1 - strength)),
                int(tint[1] * strength + bg[1] * (1 - strength)),
                int(tint[2] * strength + bg[2] * (1 - strength)),
                255,
            )
    return out


def _mask_bmp(rgba: Any, path: Path) -> None:
    from PIL import Image

    a = rgba.split()[3] if rgba.mode == "RGBA" else rgba.convert("L")
    # Bitmask: white = solid
    bw = a.point(lambda v: 255 if v > 20 else 0).convert("1")
    bw.save(path)


def _save_jpg(rgba: Any, path: Path, quality: int = 92) -> None:
    from PIL import Image

    rgb = Image.new("RGB", rgba.size, (0, 0, 0))
    if rgba.mode == "RGBA":
        rgb.paste(rgba, mask=rgba.split()[3])
    else:
        rgb.paste(rgba)
    rgb.save(path, "JPEG", quality=quality)


def _build_armor_hud_ship(hero: Any, tint: Tuple[int, int, int], overlay: Optional[Any] = None) -> Any:
    base = _silhouette(hero, tint)
    if overlay is None:
        return base
    from PIL import Image

    ov = overlay.convert("RGBA").resize(base.size, Image.Resampling.LANCZOS)
    return Image.blend(base, Image.alpha_composite(base, ov), 0.45)


def _load_overlay(path: Optional[Path], size: int) -> Optional[Any]:
    if not path or not Path(path).is_file():
        return None
    from PIL import Image

    return Image.open(path).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)


def _build_segments(ship_hud: Any) -> Any:
    from PIL import Image

    atlas = Image.new("RGBA", (ATLAS_W, ATLAS_H), (0, 0, 0, 0))
    for seg in SEGMENTS:
        crop = ship_hud.crop(
            (seg["destX"], seg["destY"], seg["destX"] + seg["w"], seg["destY"] + seg["h"])
        )
        atlas.paste(crop, (seg["x"], seg["y"]), crop if crop.mode == "RGBA" else None)
    rgb = Image.new("RGB", atlas.size, (0, 0, 0))
    rgb.paste(atlas, mask=atlas.split()[3])
    return rgb


def _build_shield_strip(
    ship_hud: Any,
    tint: Tuple[int, int, int],
    overlay: Optional[Any] = None,
) -> Tuple[Any, Any]:
    """6×136 stacked; index 0 at top = 100%, index 5 at bottom = 0% (HUD.xml order)."""
    from PIL import Image, ImageDraw, ImageFilter

    strip = Image.new("RGBA", (HUD_SIZE, HUD_SIZE * SHIELD_LEVELS), (0, 0, 0, 0))
    mask_strip = Image.new("L", strip.size, 0)
    base = ship_hud.convert("RGBA")
    for i in range(SHIELD_LEVELS):
        level = [100, 99, 74, 49, 24, 0][i]
        frame = Image.new("RGBA", (HUD_SIZE, HUD_SIZE), (0, 0, 0, 255))
        frame.paste(base, (0, 0))
        if level > 0:
            if overlay is not None:
                ov = overlay.copy()
                a = ov.split()[3].point(lambda v, lv=level: int(v * (lv / 100.0)))
                ov.putalpha(a)
                frame = Image.alpha_composite(frame, ov)
            glow = Image.new("RGBA", (HUD_SIZE, HUD_SIZE), (0, 0, 0, 0))
            d = ImageDraw.Draw(glow)
            pad = 8
            alpha = int(40 + (level / 100.0) * 140)
            d.ellipse(
                [pad, pad, HUD_SIZE - pad, HUD_SIZE - pad],
                outline=(*tint, alpha),
                width=max(2, int(2 + level / 25)),
            )
            fill = Image.new("RGBA", (HUD_SIZE, HUD_SIZE), (0, 0, 0, 0))
            fd = ImageDraw.Draw(fill)
            fd.ellipse(
                [pad + 4, pad + 4, HUD_SIZE - pad - 4, HUD_SIZE - pad - 4],
                fill=(*tint, int(alpha * 0.35)),
            )
            fill = fill.filter(ImageFilter.GaussianBlur(radius=3))
            frame = Image.alpha_composite(frame, fill)
            frame = Image.alpha_composite(frame, glow)
        y0 = i * HUD_SIZE
        strip.paste(frame, (0, y0))
        m = frame.split()[3].point(lambda v: 255 if v > 10 else 0)
        mask_strip.paste(m, (0, y0))
    return strip, mask_strip


def export_unique_ship_hud(
    out_dir: Path,
    name: str,
    *,
    hero: Optional[Path] = None,
    sketch: Optional[Path] = None,
    base_mesh: Optional[Path] = None,
    spec: Optional[Dict[str, Any]] = None,
    unique_hud: bool = True,
    tx_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Write unique hull/shield HUD assets. Returns manifest fragment.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    spec = dict(spec or {})

    if not unique_hud or spec.get("no_unique_hud"):
        return {"uniqueHud": {"enabled": False}, "files": {}}

    src = None
    for cand in (hero, sketch, out_dir / f"{name}Large.jpg", out_dir / f"{name}_sketch.png"):
        if cand and Path(cand).is_file():
            src = Path(cand)
            break
    if src is None:
        print("[ship_hud] no hero/sketch; skipping unique HUD", file=sys.stderr)
        return {"uniqueHud": {"enabled": False, "reason": "no_source"}, "files": {}}

    ship_level = int(spec.get("level") or 5)
    catalog = catalog_armor_shield_items(tx_root)
    armor_rec, shield_rec = pick_default_items(
        catalog,
        armor_entity=spec.get("armorItem") or spec.get("armor"),
        shield_entity=spec.get("shieldItem") or spec.get("shield"),
        ship_level=ship_level,
    )

    mesh = base_mesh
    if mesh is None:
        for p in (
            out_dir / "Source" / "Models" / f"{name}.fbx",
            out_dir / "Meshes" / f"{name}.fbx",
        ):
            if p.is_file():
                mesh = p
                break

    alt_meta = seed_alt_mesh_pool(
        out_dir,
        name,
        base_mesh=mesh,
        catalog=catalog,
        ship_level=ship_level,
        tx_root=tx_root,
    )

    armor_mesh = None
    shield_mesh = None
    try:
        armor_mesh = resolve_alt_mesh(
            out_dir,
            kind="armor",
            entity=armor_rec["entity"],
            family=armor_rec.get("family") or "default",
            ship_mesh=mesh,
        )
    except FileNotFoundError:
        pass
    try:
        shield_mesh = resolve_alt_mesh(
            out_dir,
            kind="shield",
            entity=shield_rec["entity"],
            family=shield_rec.get("family") or "default",
            ship_mesh=mesh,
        )
    except FileNotFoundError:
        pass

    hull_tint = family_color(armor_rec.get("family") or "default")
    shield_tint = family_color(shield_rec.get("family") or "deflector")

    # Prefer AI/content alt textures when present (run Generate-AamtShipHudAltTextures to fill)
    armor_tex = resolve_alt_texture(
        out_dir,
        kind="armor",
        entity=armor_rec["entity"],
        family=armor_rec.get("family") or "default",
    )
    shield_tex = resolve_alt_texture(
        out_dir,
        kind="shield",
        entity=shield_rec["entity"],
        family=shield_rec.get("family") or "default",
    )
    # Generate missing textures for the equipped pair only (cheap incremental)
    if spec.get("ensure_alt_textures", True) and (armor_tex is None or shield_tex is None):
        try:
            from ship_hud_alt_textures import generate_alt_hud_textures

            generate_alt_hud_textures(
                out_dir,
                ship_name=name,
                hero=src,
                base_mesh=mesh,
                catalog=catalog,
                tx_root=tx_root,
                only_missing=True,
                no_sd=bool(spec.get("no_sd", False)),
                use_ollama=bool(spec.get("ollama_alt_textures", False)),
                max_per_kind=int(spec.get("alt_texture_max", 32)),
                seed_meshes=False,
            )
            armor_tex = resolve_alt_texture(
                out_dir,
                kind="armor",
                entity=armor_rec["entity"],
                family=armor_rec.get("family") or "default",
            )
            shield_tex = resolve_alt_texture(
                out_dir,
                kind="shield",
                entity=shield_rec["entity"],
                family=shield_rec.get("family") or "default",
            )
        except Exception as exc:
            print(f"[WARN] alt texture ensure failed: {exc}", file=sys.stderr)

    hero_im = _load_rgba(src, (HUD_SIZE, HUD_SIZE))
    armor_ov = _load_overlay(armor_tex, HUD_SIZE)
    shield_ov = _load_overlay(shield_tex, HUD_SIZE)
    ship_hud = _build_armor_hud_ship(hero_im, hull_tint, overlay=armor_ov)


    armor_ship = out_dir / f"{name}ArmorHUDShip.jpg"
    armor_ship_mask = out_dir / f"{name}ArmorHUDShipMask.bmp"
    armor_seg = out_dir / f"{name}ArmorHUDSegments.bmp"
    shield_jpg = out_dir / f"{name}ShieldsHUD.jpg"
    shield_mask = out_dir / f"{name}ShieldsHUDMask.bmp"

    _save_jpg(ship_hud, armor_ship)
    _mask_bmp(ship_hud, armor_ship_mask)

    segments_rgb = _build_segments(ship_hud)
    segments_rgb.save(armor_seg)

    strip, smask = _build_shield_strip(ship_hud, shield_tint, overlay=shield_ov)
    _save_jpg(strip, shield_jpg)
    smask.convert("1").save(shield_mask)

    hud = {
        "enabled": True,
        "size": HUD_SIZE,
        "segments": SEGMENTS,
        "atlas": {"width": ATLAS_W, "height": ATLAS_H},
        "armor": armor_rec,
        "shield": shield_rec,
        "altTextures": {
            "armor": str(armor_tex) if armor_tex else None,
            "shield": str(shield_tex) if shield_tex else None,
        },
        "altMesh": {
            "armor": str(armor_mesh) if armor_mesh else None,
            "shield": str(shield_mesh) if shield_mesh else None,
            "catalog": alt_meta.get("armorCount"),
            "shieldCatalog": alt_meta.get("shieldCount"),
        },
        "shieldLevels": [
            {"maxValue": 0, "imageY": HUD_SIZE * 5},
            {"maxValue": 24, "imageY": HUD_SIZE * 4},
            {"maxValue": 49, "imageY": HUD_SIZE * 3},
            {"maxValue": 74, "imageY": HUD_SIZE * 2},
            {"maxValue": 99, "imageY": HUD_SIZE * 1},
            {"maxValue": 100, "imageY": 0},
        ],
    }
    hud_json = out_dir / f"{name}_hud.json"
    hud_json.write_text(json.dumps(hud, indent=2), encoding="utf-8")

    files = {
        "armorHudShip": str(armor_ship),
        "armorHudShipMask": str(armor_ship_mask),
        "armorHudSegments": str(armor_seg),
        "shieldsHud": str(shield_jpg),
        "shieldsHudMask": str(shield_mask),
        "hudJson": str(hud_json),
        "altModelsDir": str(out_dir / "Source" / "Models" / "Alt"),
    }
    print(
        f"[ship_hud] unique HUD for {name}: armor={armor_rec['entity']} "
        f"shield={shield_rec['entity']} "
        f"(catalog armor={alt_meta.get('armorCount')} shield={alt_meta.get('shieldCount')})",
        file=sys.stderr,
    )
    return {"uniqueHud": hud, "files": files}


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Export unique ship hull/shield HUD")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--hero", default="")
    ap.add_argument("--sketch", default="")
    ap.add_argument("--mesh", default="")
    ap.add_argument("--no-unique-hud", action="store_true")
    ap.add_argument("--tx-root", default="")
    ap.add_argument(
        "--sd",
        action="store_true",
        help="Use local Stable Diffusion for alt textures (slow; default procedural)",
    )
    args = ap.parse_args()
    result = export_unique_ship_hud(
        Path(args.out_dir),
        args.name,
        hero=Path(args.hero) if args.hero else None,
        sketch=Path(args.sketch) if args.sketch else None,
        base_mesh=Path(args.mesh) if args.mesh else None,
        # Standalone CLI defaults to fast procedural textures; SD can take
        # 300-500s per image on this box and stalls smoke tests.
        spec={"no_sd": not args.sd},
        unique_hud=not args.no_unique_hud,
        tx_root=Path(args.tx_root) if args.tx_root else None,
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("uniqueHud", {}).get("enabled") or args.no_unique_hud else 1


if __name__ == "__main__":
    raise SystemExit(main())
