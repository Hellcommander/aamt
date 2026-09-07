#!/usr/bin/env python3
"""
Build 120-facing OrganicHull JPG + Mask.bmp sheets from concept sketches.

Uses space_whale_topdown_sketches.render_part (no Blender / SD required).
Packs 12 columns x 10 rows (Transcendence facing sheet convention).

Usage:
  python build_organic_hull_sheets.py
  python build_organic_hull_sheets.py --ship-id scSpaceWhale --deploy
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image

from space_whale_topdown_sketches import POSE_BY_ROLE, SKETCHERS, render_part

_TOOLS_TX = Path(__file__).resolve().parent
_REGISTRY = _TOOLS_TX / "crossmod_ship_skins_registry.json"
_DEFAULT_OUT = Path(r"C:\Output\SpaceWhale120Facings")
_DEFAULT_DEPLOY = Path(
    r"D:\games\Steam\steamapps\common\Transcendence\Extensions"
    r"\ZZZ_CrossModCompatibility\Resources\OrganicHulls"
)

# Match OrganicHullAssets.xml Image frame sizes
FRAME_SIZES: Dict[str, int] = {
    "scSpaceWhale": 256,
    "scSpaceWhaleSegment": 128,
    "scSpaceWhaleFluke": 128,
    "scSpaceWhaleDrone": 64,
    "scLeviathanBase": 192,
    "scLeviathanSegment": 96,
}

COLUMNS = 12
FACINGS = 120
ROWS = FACINGS // COLUMNS  # 10


def _load_frame_sizes() -> Dict[str, int]:
    sizes = dict(FRAME_SIZES)
    if _REGISTRY.is_file():
        data = json.loads(_REGISTRY.read_text(encoding="utf-8"))
        for ship in data.get("ships") or []:
            sid = ship.get("id")
            fw = ship.get("frameWidth")
            if sid and fw:
                sizes[sid] = int(fw)
    return sizes


def _asset_name(ship_id: str, pose: str) -> str:
    return ship_id if pose == "idle" else f"{ship_id}_{pose}"


def make_facing_sheet(
    rgba: Image.Image,
    frame_size: int,
    *,
    facings: int = FACINGS,
    columns: int = COLUMNS,
) -> Tuple[Image.Image, Image.Image]:
    """
    Rotate source (nose = +X / right) into Transcendence facing order.
    Facing 0 = up (nose toward -Y after rotate), progressing clockwise.
    """
    rows = facings // columns
    sheet = Image.new("RGBA", (columns * frame_size, rows * frame_size), (0, 0, 0, 0))
    # Crop to opaque content, then fit into frame (avoid scaling empty canvas)
    src = rgba.convert("RGBA")
    alpha = src.split()[3]
    # Ignore soft glow halo when framing (high alpha = solid body)
    bbox = alpha.point(lambda v: 255 if v > 96 else 0).getbbox()
    if bbox:
        pad_px = max(2, int(max(bbox[2] - bbox[0], bbox[3] - bbox[1]) * 0.06))
        x0 = max(0, bbox[0] - pad_px)
        y0 = max(0, bbox[1] - pad_px)
        x1 = min(src.size[0], bbox[2] + pad_px)
        y1 = min(src.size[1], bbox[3] + pad_px)
        src = src.crop((x0, y0, x1, y1))
    pad = int(frame_size * 0.88)
    scale = pad / max(src.size)
    new_w = max(1, int(src.size[0] * scale))
    new_h = max(1, int(src.size[1] * scale))
    fitted = src.resize((new_w, new_h), Image.Resampling.LANCZOS)

    for i in range(facings):
        # Transcendence: facing 0 up, increasing clockwise
        # Source nose +X; rotate CCW by (90 - i*3) deg to point up at i=0
        deg = 90.0 - (i * (360.0 / facings))
        rotated = fitted.rotate(deg, resample=Image.Resampling.BICUBIC, expand=True)
        # Letterbox into frame
        frame = Image.new("RGBA", (frame_size, frame_size), (0, 0, 0, 0))
        ox = (frame_size - rotated.size[0]) // 2
        oy = (frame_size - rotated.size[1]) // 2
        frame.paste(rotated, (ox, oy), rotated)
        col = i % columns
        row = i // columns
        sheet.paste(frame, (col * frame_size, row * frame_size), frame)

    # JPG: composite on black
    rgb = Image.new("RGB", sheet.size, (0, 0, 0))
    rgb.paste(sheet, mask=sheet.split()[3])

    # Mask: white where opaque
    alpha = sheet.split()[3]
    mask = Image.new("RGB", sheet.size, (0, 0, 0))
    white = Image.new("L", sheet.size, 255)
    mask_l = Image.composite(white, Image.new("L", sheet.size, 0), alpha.point(lambda v: 255 if v > 24 else 0))
    mask = Image.merge("RGB", (mask_l, mask_l, mask_l))
    return rgb, mask


def build_all(
    out_dir: Path,
    *,
    ship_ids: Optional[List[str]] = None,
    deploy_dir: Optional[Path] = None,
) -> List[dict]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    sizes = _load_frame_sizes()
    wanted = set(ship_ids) if ship_ids else set(SKETCHERS.keys())
    results = []

    for ship_id in SKETCHERS:
        if ship_id not in wanted:
            continue
        frame = sizes.get(ship_id, 128)
        for pose in POSE_BY_ROLE.get(ship_id, ["idle"]):
            name = _asset_name(ship_id, pose)
            print(f"[sheet] {name} @ {frame}px")
            # Render oversized for quality, then pack
            render_size = max(512, frame * 4)
            rgba = render_part(ship_id, pose=pose, size=render_size)
            jpg, mask = make_facing_sheet(rgba, frame)

            pack = out_dir / name
            pack.mkdir(parents=True, exist_ok=True)
            jpg_path = pack / f"{name}.jpg"
            mask_path = pack / f"{name}Mask.bmp"
            root_jpg = out_dir / f"{name}_120facings.jpg"
            root_mask = out_dir / f"{name}_120facingsMask.bmp"

            jpg.save(jpg_path, "JPEG", quality=92)
            mask.save(mask_path, "BMP")
            jpg.save(root_jpg, "JPEG", quality=92)
            mask.save(root_mask, "BMP")

            # Facing-0 preview
            preview = jpg.crop((0, 0, frame, frame))
            preview.save(out_dir / f"_preview_{name}_f0.png")

            entry = {
                "id": ship_id,
                "pose": pose,
                "name": name,
                "ok": True,
                "frame": frame,
                "files": {
                    "spritesheet": str(jpg_path),
                    "spritesheetMask": str(mask_path),
                },
            }
            results.append(entry)

            # Facing-0 hero (also overwrites stale Blender hexagon Large.jpg)
            large = jpg.crop((0, 0, frame, frame))
            large_path = pack / f"{name}Large.jpg"
            large.save(large_path, "JPEG", quality=92)
            entry["files"]["large"] = str(large_path)

            if deploy_dir:
                deploy_dir = Path(deploy_dir)
                deploy_dir.mkdir(parents=True, exist_ok=True)
                jpg.save(deploy_dir / f"{name}.jpg", "JPEG", quality=92)
                mask.save(deploy_dir / f"{name}Mask.bmp", "BMP")
                large.save(deploy_dir / f"{name}Large.jpg", "JPEG", quality=92)

    manifest = out_dir / "organic_hull_sheets_manifest.json"
    manifest.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"[OK] {len(results)} sheets -> {out_dir}")
    if deploy_dir:
        print(f"[OK] deployed -> {deploy_dir}")
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="Build OrganicHull 120-facing sheets from concept sketches")
    ap.add_argument("--out-dir", default=str(_DEFAULT_OUT))
    ap.add_argument("--ship-id", action="append", default=[])
    ap.add_argument("--deploy", action="store_true", help=f"Copy into {_DEFAULT_DEPLOY}")
    ap.add_argument("--deploy-dir", default=str(_DEFAULT_DEPLOY))
    args = ap.parse_args()
    results = build_all(
        Path(args.out_dir),
        ship_ids=args.ship_id or None,
        deploy_dir=Path(args.deploy_dir) if args.deploy else None,
    )
    ok = sum(1 for r in results if r.get("ok"))
    return 0 if ok == len(results) and results else 1


if __name__ == "__main__":
    raise SystemExit(main())
