#!/usr/bin/env python3
"""
Spritesheet swapouts via masking: hull plating + shield effect overlays.

Uses the ship Mask.bmp so overlays only affect the hull silhouette (armor) or
a ring around it (shield). Outputs:

  Source/Models/Alt/Sheets/Hull/{family}.jpg[+Mask]
  Source/Models/Alt/Sheets/Shield/{family}.jpg[+Mask]   # ring-only overlay sheet
  {Name}.jpg  (optional apply) = base hull masked with armor, then shield ring

Re-run after generating alt textures / adding content.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ship_hud_alt_textures import resolve_alt_texture
from tx_item_alt_mesh import (
    FAMILY_COLORS,
    alt_models_dir,
    catalog_armor_shield_items,
    family_color,
    pick_default_items,
)

SHEETS_REL = Path("Sheets")


def sheets_dir(pack_dir: Path) -> Path:
    return alt_models_dir(pack_dir) / SHEETS_REL


def _load_mask_sheet(path: Path, size: Tuple[int, int]) -> Any:
    from PIL import Image

    m = Image.open(path).convert("L")
    if m.size != size:
        m = m.resize(size, Image.Resampling.NEAREST)
    return m


def _cell_grid(facings: int, columns: int, fw: int, fh: int) -> List[Tuple[int, int, int, int]]:
    rows = max(1, (facings + columns - 1) // columns)
    cells = []
    for i in range(facings):
        c = i % columns
        r = i // columns
        if r >= rows:
            break
        x, y = c * fw, r * fh
        cells.append((x, y, x + fw, y + fh))
    return cells


def _infer_grid(sheet_w: int, sheet_h: int, facings: int = 120, columns: int = 12) -> Tuple[int, int, int, int]:
    fw = sheet_w // columns
    rows = max(1, (facings + columns - 1) // columns)
    fh = sheet_h // rows if rows else sheet_h
    if fw <= 0 or fh <= 0:
        fw = fh = min(sheet_w, sheet_h)
        columns = 1
        facings = 1
    return facings, columns, fw, fh


def _dilate_mask(mask: Any, pixels: int) -> Any:
    from PIL import ImageFilter

    if pixels <= 0:
        return mask
    # MaxFilter size must be odd
    k = pixels * 2 + 1
    return mask.filter(ImageFilter.MaxFilter(size=k))


def _tint_under_mask(
    base_rgb: Any,
    mask_l: Any,
    tint: Tuple[int, int, int],
    *,
    strength: float = 0.55,
    overlay: Optional[Any] = None,
) -> Any:
    """Blend tint (and optional overlay texture) into base where mask is bright."""
    from PIL import Image, ImageChops

    base = base_rgb.convert("RGB")
    m = mask_l.convert("L")
    if overlay is not None:
        ov = overlay.convert("RGB").resize(base.size, Image.Resampling.LANCZOS)
        tint_img = Image.new("RGB", base.size, tint)
        ov = Image.blend(tint_img, ov, 0.5)
    else:
        ov = Image.new("RGB", base.size, tint)
    blended = Image.blend(base, ov, strength)
    # Use mask as alpha: only hull pixels change
    return Image.composite(blended, base, m)


def _shield_ring_layer(
    cell_size: Tuple[int, int],
    hull_mask: Any,
    tint: Tuple[int, int, int],
    *,
    ring_px: int = 6,
    overlay: Optional[Any] = None,
) -> Tuple[Any, Any]:
    """RGBA ring + L mask outside hull (dilate - hull)."""
    from PIL import Image, ImageChops, ImageFilter

    w, h = cell_size
    hm = hull_mask.convert("L").resize((w, h), Image.Resampling.NEAREST)
    outer = _dilate_mask(hm, ring_px)
    # ring = outer AND NOT hull
    inv_hull = ImageChops.invert(hm)
    ring = ImageChops.multiply(outer, inv_hull)
    ring = ring.point(lambda v: v if v > 40 else 0)

    if overlay is not None:
        ov = overlay.convert("RGBA").resize((w, h), Image.Resampling.LANCZOS)
        tint_img = Image.new("RGBA", (w, h), (*tint, 200))
        colored = Image.blend(tint_img, ov, 0.45)
    else:
        colored = Image.new("RGBA", (w, h), (*tint, 190))
    # apply ring alpha
    ra = ring.point(lambda v: int(v * 0.85))
    colored.putalpha(ra)
    colored = colored.filter(ImageFilter.GaussianBlur(radius=0.8))
    return colored, ring


def _apply_sheet_masked(
    sheet: Any,
    mask_sheet: Any,
    *,
    facings: int,
    columns: int,
    fw: int,
    fh: int,
    mode: str,
    tint: Tuple[int, int, int],
    overlay: Optional[Any] = None,
    strength: float = 0.55,
    ring_px: int = 6,
) -> Tuple[Any, Any]:
    from PIL import Image

    out = sheet.convert("RGB").copy()
    mask_out = Image.new("L", sheet.size, 0)
    cells = _cell_grid(facings, columns, fw, fh)
    for box in cells:
        cell = out.crop(box)
        mcell = mask_sheet.crop(box)
        if mode == "hull":
            tinted = _tint_under_mask(cell, mcell, tint, strength=strength, overlay=overlay)
            out.paste(tinted, box)
            mask_out.paste(mcell, box)
        else:
            ring_rgba, ring_m = _shield_ring_layer(
                (fw, fh), mcell, tint, ring_px=ring_px, overlay=overlay
            )
            base = cell.convert("RGBA")
            comp = Image.alpha_composite(base, ring_rgba)
            out.paste(comp.convert("RGB"), box)
            mask_out.paste(ring_m, box)
    return out, mask_out


def _composite_shield_onto_hull(hull_rgb: Any, shield_rgb: Any, shield_mask_l: Any) -> Any:
    from PIL import Image, ImageChops

    hull = hull_rgb.convert("RGBA")
    sh = shield_rgb.convert("RGB")
    sm = shield_mask_l.convert("L")
    if sm.size != sh.size:
        sm = sm.resize(sh.size, Image.Resampling.NEAREST)
    sh_rgba = sh.convert("RGBA")
    lum = sh.convert("L")
    a = ImageChops.multiply(
        sm.point(lambda v: v if v > 20 else 0),
        lum.point(lambda v: 255 if v > 12 else 0),
    )
    sh_rgba.putalpha(a)
    if hull.size != sh_rgba.size:
        sh_rgba = sh_rgba.resize(hull.size, Image.Resampling.NEAREST)
    return Image.alpha_composite(hull, sh_rgba).convert("RGB")


def generate_spritesheet_swapouts(
    pack_dir: Path,
    name: str,
    *,
    sheet: Optional[Path] = None,
    mask: Optional[Path] = None,
    facings: int = 120,
    columns: int = 12,
    armor_family: Optional[str] = None,
    shield_family: Optional[str] = None,
    armor_entity: Optional[str] = None,
    shield_entity: Optional[str] = None,
    families: Optional[Sequence[str]] = None,
    apply_active: bool = True,
    only_missing: bool = True,
    force: bool = False,
    tx_root: Optional[Path] = None,
    ring_px: int = 6,
) -> Dict[str, Any]:
    from PIL import Image

    pack_dir = Path(pack_dir)
    sheet_path = Path(sheet) if sheet else pack_dir / f"{name}.jpg"
    mask_path = Path(mask) if mask else pack_dir / f"{name}Mask.bmp"
    if not sheet_path.is_file():
        raise FileNotFoundError(f"spritesheet missing: {sheet_path}")
    if not mask_path.is_file():
        raise FileNotFoundError(f"mask missing: {mask_path} (required for masked overlays)")

    base = Image.open(sheet_path).convert("RGB")
    facings, columns, fw, fh = _infer_grid(base.size[0], base.size[1], facings, columns)
    mask_sheet = _load_mask_sheet(mask_path, base.size)

    cat = catalog_armor_shield_items(tx_root)
    armor_rec, shield_rec = pick_default_items(
        cat,
        armor_entity=armor_entity,
        shield_entity=shield_entity,
        ship_level=5,
    )
    armor_fam = armor_family or armor_rec.get("family") or "reactive"
    shield_fam = shield_family or shield_rec.get("family") or "deflector"

    # Prefer families that already have alt textures; always include active + default
    def _fams_from_textures(kind: str, fallback: Sequence[str], active: str) -> List[str]:
        tex = Path(pack_dir) / "Source" / "Models" / "Alt" / "Textures" / (
            "Armor" if kind == "armor" else "Shield"
        )
        found = []
        if tex.is_dir():
            for p in tex.glob("family_*.png"):
                found.append(p.stem.replace("family_", "", 1))
        out = []
        for f in [active, "default", *found, *fallback]:
            if f and f not in out:
                out.append(f)
        return out[:12]

    hull_fams = list(families) if families else _fams_from_textures(
        "armor",
        ["reactive", "heavy", "ceramic", "light", "organic", "meteor"],
        armor_fam,
    )
    shield_fams = list(families) if families else _fams_from_textures(
        "shield",
        ["deflector", "plasma", "military", "gravitic", "organic"],
        shield_fam,
    )

    hull_dir = sheets_dir(pack_dir) / "Hull"
    shield_dir = sheets_dir(pack_dir) / "Shield"
    hull_dir.mkdir(parents=True, exist_ok=True)
    shield_dir.mkdir(parents=True, exist_ok=True)

    readme = sheets_dir(pack_dir) / "README.txt"
    if not readme.is_file():
        readme.write_text(
            "Masked spritesheet swapouts\n"
            "===========================\n"
            "Hull/*.jpg  — armor plating composited under ship Mask.bmp\n"
            "Shield/*.jpg — shield ring overlay (mask = ring only)\n"
            "Active ship sheet is hull+shield for equipped items when apply_active=true.\n"
            "Regenerate: Generate-AamtShipSpritesheetSwapouts.ps1 -PackDir <pack>\n",
            encoding="utf-8",
        )

    created: List[str] = []
    skipped = 0
    only_missing = only_missing and not force

    def _need(p: Path) -> bool:
        nonlocal skipped
        if only_missing and p.is_file():
            skipped += 1
            return False
        return True

    hull_files: Dict[str, str] = {}
    for fam in hull_fams:
        dest = hull_dir / f"{fam}.jpg"
        dest_m = hull_dir / f"{fam}Mask.bmp"
        hull_files[fam] = str(dest)
        if not _need(dest):
            continue
        tint = family_color(fam)
        ov_path = resolve_alt_texture(pack_dir, kind="armor", entity=f"family_{fam}", family=fam)
        ov = Image.open(ov_path).convert("RGBA") if ov_path else None
        sheet_out, mask_out = _apply_sheet_masked(
            base,
            mask_sheet,
            facings=facings,
            columns=columns,
            fw=fw,
            fh=fh,
            mode="hull",
            tint=tint,
            overlay=ov,
            strength=0.5,
        )
        sheet_out.save(dest, "JPEG", quality=92)
        mask_out.point(lambda v: 255 if v > 20 else 0).convert("1").save(dest_m)
        created.append(str(dest))
        print(f"[swapout] hull/{fam}", file=sys.stderr)

    shield_files: Dict[str, str] = {}
    for fam in shield_fams:
        dest = shield_dir / f"{fam}.jpg"
        dest_m = shield_dir / f"{fam}Mask.bmp"
        shield_files[fam] = str(dest)
        if not _need(dest):
            continue
        tint = family_color(fam if fam in FAMILY_COLORS else "deflector")
        ov_path = resolve_alt_texture(pack_dir, kind="shield", entity=f"family_{fam}", family=fam)
        ov = Image.open(ov_path).convert("RGBA") if ov_path else None
        # shield sheet: transparent black base + rings only (for overlay Image)
        blank = Image.new("RGB", base.size, (0, 0, 0))
        sheet_out, mask_out = _apply_sheet_masked(
            blank,
            mask_sheet,
            facings=facings,
            columns=columns,
            fw=fw,
            fh=fh,
            mode="shield",
            tint=tint,
            overlay=ov,
            ring_px=ring_px,
        )
        sheet_out.save(dest, "JPEG", quality=92)
        mask_out.point(lambda v: 255 if v > 20 else 0).convert("1").save(dest_m)
        created.append(str(dest))
        print(f"[swapout] shield/{fam}", file=sys.stderr)

    active: Dict[str, Any] = {
        "armorFamily": armor_fam,
        "shieldFamily": shield_fam,
        "armorEntity": armor_rec.get("entity"),
        "shieldEntity": shield_rec.get("entity"),
    }
    if apply_active:
        hull_src = hull_dir / f"{armor_fam}.jpg"
        if not hull_src.is_file():
            hull_src = hull_dir / "default.jpg"
        if not hull_src.is_file():
            hull_src = sheet_path
        hull_im = Image.open(hull_src).convert("RGB")
        sh_sheet = shield_dir / f"{shield_fam}.jpg"
        sh_mask_p = shield_dir / f"{shield_fam}Mask.bmp"
        if sh_sheet.is_file() and sh_mask_p.is_file():
            composed = _composite_shield_onto_hull(
                hull_im, Image.open(sh_sheet), Image.open(sh_mask_p)
            )
        else:
            composed = hull_im

        active_path = pack_dir / f"{name}.jpg"
        pristine = pack_dir / f"{name}_base.jpg"
        if not pristine.is_file():
            Image.open(sheet_path).convert("RGB").save(pristine, "JPEG", quality=92)
        composed.save(active_path, "JPEG", quality=92)
        active["spritesheet"] = str(active_path)
        active["basePreserved"] = str(pristine)
        active["hullSheet"] = str(hull_src)
        active["shieldSheet"] = str(sh_sheet) if sh_sheet.is_file() else None
        active["shieldMask"] = str(sh_mask_p) if sh_mask_p.is_file() else None
        print(
            f"[swapout] applied active hull={armor_fam} shield={shield_fam} -> {active_path}",
            file=sys.stderr,
        )

    meta = {
        "ship": name,
        "facings": facings,
        "columns": columns,
        "frame": [fw, fh],
        "created": created,
        "skippedExisting": skipped,
        "hullSheets": hull_files,
        "shieldSheets": shield_files,
        "active": active,
        "method": "mask_overlay",
    }
    (sheets_dir(pack_dir) / "manifest.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pack-dir", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--sheet", default="")
    ap.add_argument("--mask", default="")
    ap.add_argument("--facings", type=int, default=120)
    ap.add_argument("--columns", type=int, default=12)
    ap.add_argument("--armor-family", default="")
    ap.add_argument("--shield-family", default="")
    ap.add_argument("--armor-item", default="")
    ap.add_argument("--shield-item", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-apply", action="store_true")
    ap.add_argument("--tx-root", default="")
    ap.add_argument("--ring-px", type=int, default=6)
    args = ap.parse_args()
    meta = generate_spritesheet_swapouts(
        Path(args.pack_dir),
        args.name,
        sheet=Path(args.sheet) if args.sheet else None,
        mask=Path(args.mask) if args.mask else None,
        facings=args.facings,
        columns=args.columns,
        armor_family=args.armor_family or None,
        shield_family=args.shield_family or None,
        armor_entity=args.armor_item or None,
        shield_entity=args.shield_item or None,
        apply_active=not args.no_apply,
        force=args.force,
        only_missing=not args.force,
        tx_root=Path(args.tx_root) if args.tx_root else None,
        ring_px=args.ring_px,
    )
    print(
        json.dumps(
            {
                "ship": meta["ship"],
                "createdCount": len(meta["created"]),
                "skippedExisting": meta["skippedExisting"],
                "active": meta["active"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
