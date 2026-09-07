#!/usr/bin/env python3
"""
Transcendence ship rotation spritesheet export.

Dev workflow (matches game_and_dlc_source CommonwealthShips / Sapphire):
  1. Build a 3D mesh from the top-down sketch (mesh_skin_export / blender_aamt_mesh)
  2. Render N orthographic facings in Blender (Common/blender_ship_spritesheet_export.py)
  3. Emit JPG sheet + Mask.bmp + optional hero JPG (320×320)

Falls back to a procedural 2D rotation sheet when Blender is unavailable.
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SHARED = Path(__file__).resolve().parent
_TOOLS = _SHARED.parent
_BLENDER_SHIP_SCRIPT = _TOOLS / "Common" / "blender_ship_spritesheet_export.py"

# Canonical folder for the mesh that produced the final spritesheet (user touch-ups).
SOURCE_MODELS_REL = Path("Source") / "Models"
MODEL_EXTS = (".fbx", ".obj", ".blend", ".dae")

# HD bar matches EarthSlaverHD / Sung HD (128×128 × 120 / 12 cols), exceeds Sapphire 62
TX_SHIP_DEFAULTS: Dict[str, int] = {
    "facings": 120,
    "columns": 12,
    "frame_width": 128,
    "frame_height": 128,
    "hero_width": 320,
    "hero_height": 320,
    "supersample": 2,
}


def _rows(facings: int, columns: int) -> int:
    return max(1, math.ceil(facings / columns))


def _viewport_ratio(frame_size: int) -> float:
    # EarthSlaverHD: 128px → 0.01375; Sapphire: 62px → 0.00475
    return max(0.004, min(0.04, frame_size * (0.01375 / 128.0)))


def _resolve_tx_params(spec: Optional[Dict[str, Any]]) -> Dict[str, int]:
    s = spec or {}
    facings = int(s.get("facings") or s.get("shipFacings") or TX_SHIP_DEFAULTS["facings"])
    columns = int(s.get("columns") or s.get("rotationColumns") or TX_SHIP_DEFAULTS["columns"])
    fw = int(s.get("frameWidth") or s.get("frame_width") or TX_SHIP_DEFAULTS["frame_width"])
    fh = int(s.get("frameHeight") or s.get("frame_height") or fw)
    return {
        "facings": facings,
        "columns": columns,
        "rows": _rows(facings, columns),
        "frame_width": fw,
        "frame_height": fh,
        "hero_width": int(s.get("heroWidth") or TX_SHIP_DEFAULTS["hero_width"]),
        "hero_height": int(s.get("heroHeight") or TX_SHIP_DEFAULTS["hero_height"]),
        "supersample": int(s.get("supersample") or TX_SHIP_DEFAULTS["supersample"]),
    }


def _export_mesh_from_sketch(
    *,
    out_dir: Path,
    name: str,
    theme: str,
    sketch: Path,
    spec: Dict[str, Any],
    blender: Optional[str] = None,
    no_sd: bool = True,
) -> Tuple[Optional[Path], int]:
    from mesh_skin_export import run_blender_export
    from pbr_skin_generator import generate_pbr_skin_set

    skin_dir = out_dir / "Skins"
    fbx = out_dir / "Meshes" / f"{name}.fbx"
    # Silhouette extrusion from top-down sketch reads clearly at every facing
    shape = str(spec.get("shape") or "silhouette")
    generate_pbr_skin_set(
        skin_dir,
        name,
        {"theme": theme, "shape": shape},
        quality="standard",
        use_sd=not no_sd,
    )
    code = run_blender_export(
        skin_dir=skin_dir,
        name=name,
        fbx=fbx,
        shape=shape,
        blender=blender,
        sketch=sketch,
        subdivisions=2,
        displace_strength=0.08,
        solidify_thickness=0.22,
        silhouette_res=int(spec.get("silhouetteRes") or 128),
        alpha_threshold=0.10,
    )
    return (fbx if fbx.is_file() else None), code


def _run_blender_spritesheet(
    *,
    model_path: Path,
    sheet_path: Path,
    hero_path: Path,
    params: Dict[str, int],
    blender: Optional[str] = None,
) -> int:
    from mesh_skin_export import find_blender

    blender_exe = find_blender(blender)
    if not blender_exe or not _BLENDER_SHIP_SCRIPT.is_file():
        return 127
    if not model_path.is_file():
        return 126

    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    args = [
        blender_exe,
        "--background",
        "--python",
        str(_BLENDER_SHIP_SCRIPT),
        "--",
        "--model",
        str(model_path),
        "--output",
        str(sheet_path),
        "--facings",
        str(params["facings"]),
        "--columns",
        str(params["columns"]),
        "--rows",
        str(params["rows"]),
        "--frame-width",
        str(params["frame_width"]),
        "--frame-height",
        str(params["frame_height"]),
        "--output-format",
        "JPG",
        "--game-format",
        "Transcendence",
        "--generate-mask",
        "--hero-image",
        str(hero_path),
        "--hero-width",
        str(params["hero_width"]),
        "--hero-height",
        str(params["hero_height"]),
        "--supersample",
        str(params.get("supersample") or 2),
    ]
    print(f"[ship_spritesheet] Blender: {' '.join(args[:4])} ...", file=sys.stderr)
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout, file=sys.stderr)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    if proc.returncode != 0 and not sheet_path.is_file():
        return proc.returncode
    return 0 if sheet_path.is_file() else 1


def _proc_rotation_sheet(
    sketch: Path,
    sheet_path: Path,
    *,
    params: Dict[str, int],
) -> bool:
    """2D fallback: padded anti-aliased rotation into HD JPG + full-sheet mask."""
    try:
        from PIL import Image, ImageFilter, ImageEnhance
    except ImportError:
        return False

    facings = params["facings"]
    columns = params["columns"]
    rows = params["rows"]
    fw = params["frame_width"]
    fh = params["frame_height"]

    src = Image.open(sketch).convert("RGBA")
    # Fit with ~12% padding like Blender ortho framing
    pad = int(min(fw, fh) * 0.12)
    box = max(1, fw - 2 * pad), max(1, fh - 2 * pad)
    src = src.resize(box, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
    ox = (fw - src.width) // 2
    oy = (fh - src.height) // 2
    canvas.paste(src, (ox, oy), src)
    src = canvas

    sheet = Image.new("RGB", (columns * fw, rows * fh), (0, 0, 0))
    mask_sheet = Image.new("RGB", (columns * fw, rows * fh), (0, 0, 0))

    for i in range(facings):
        angle = (360.0 / facings) * i
        frame = src.rotate(-angle, resample=Image.Resampling.BICUBIC, expand=False)
        frame = ImageEnhance.Contrast(frame).enhance(1.08)
        col = i % columns
        row = i // columns
        rgb = Image.new("RGB", (fw, fh), (0, 0, 0))
        rgb.paste(frame, mask=frame.split()[3])
        sheet.paste(rgb, (col * fw, row * fh))
        alpha = frame.split()[3]
        m = Image.new("RGB", (fw, fh), (0, 0, 0))
        m.paste((255, 255, 255), mask=alpha.point(lambda v: 255 if v > 20 else 0))
        mask_sheet.paste(m, (col * fw, row * fh))

    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(sheet_path, "JPEG", quality=95)
    mask_path = sheet_path.with_name(sheet_path.stem + "Mask.bmp")
    mask_sheet.save(mask_path, "BMP")
    return sheet_path.is_file()


def models_dir(out_dir: Path) -> Path:
    return Path(out_dir) / SOURCE_MODELS_REL


def _write_models_readme(models_root: Path) -> None:
    readme = models_root / "README.txt"
    if readme.exists():
        return
    readme.write_text(
        "AAMT Source/Models — final meshes used for Transcendence ship spritesheets\n"
        "=========================================================================\n"
        "Edit the .fbx / .obj / .blend here (scale, panels, materials), then re-export:\n"
        "\n"
        "  powershell -File Tools\\Transcendence\\Export-AamtShipSpritesheet.ps1 `\n"
        "    -ReexportFrom .\\Source\\Models -OutDir . -Defs -DeployTx\n"
        "\n"
        "Or Python:\n"
        "  python Tools\\Shared\\ship_spritesheet_export.py --reexport-from Source\\Models --out-dir .\n"
        "\n"
        "Re-export does NOT regenerate the mesh — it only renders facings from these files.\n"
        "Sidecar *.export.json stores last frame size / facings / columns used.\n",
        encoding="utf-8",
    )


def preserve_final_model(
    out_dir: Path,
    name: str,
    model_path: Path,
    *,
    params: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Copy the mesh that drove the final spritesheet into Source/Models/ for touch-ups.
    Also writes {name}.export.json with render params for re-export.
    """
    dest_root = models_dir(out_dir)
    dest_root.mkdir(parents=True, exist_ok=True)
    _write_models_readme(dest_root)

    src = Path(model_path)
    if not src.is_file():
        raise FileNotFoundError(src)

    dest = dest_root / f"{name}{src.suffix.lower()}"
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)

    # Companion formats in Meshes/ (OBJ) if present
    for ext in (".obj", ".fbx", ".blend"):
        sibling = src.with_suffix(ext)
        if sibling.is_file() and sibling.resolve() != dest.resolve():
            alt = dest_root / f"{name}{ext}"
            if not alt.exists() or alt.stat().st_mtime < sibling.stat().st_mtime:
                shutil.copy2(sibling, alt)

    meta = {
        "name": name,
        "model": dest.name,
        "params": dict(params or TX_SHIP_DEFAULTS),
        "note": "Re-export sprites with Export-AamtShipSpritesheet.ps1 -ReexportFrom Source\\Models",
    }
    (dest_root / f"{name}.export.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return dest


def find_models(models_root: Path, *, name: Optional[str] = None) -> List[Path]:
    root = Path(models_root)
    if root.is_file() and root.suffix.lower() in MODEL_EXTS:
        return [root]
    if not root.is_dir():
        return []
    found: List[Path] = []
    for ext in MODEL_EXTS:
        found.extend(sorted(root.glob(f"*{ext}")))
        found.extend(sorted(root.glob(f"**/*{ext}")))
    # de-dupe
    uniq: List[Path] = []
    seen = set()
    for p in found:
        key = p.resolve()
        if key in seen:
            continue
        if name and p.stem.lower() != name.lower():
            continue
        seen.add(key)
        uniq.append(p)
    return uniq


def _load_export_params(models_root: Path, name: str, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, int]:
    params = dict(TX_SHIP_DEFAULTS)
    sidecar = Path(models_root) / f"{name}.export.json"
    if not sidecar.is_file():
        # pack-level sidecar next to model
        pass
    else:
        try:
            data = json.loads(sidecar.read_text(encoding="utf-8"))
            stored = data.get("params") or {}
            params.update({k: stored[k] for k in TX_SHIP_DEFAULTS if k in stored})
        except Exception as exc:
            print(f"[WARN] could not read {sidecar}: {exc}", file=sys.stderr)
    if overrides:
        params.update(_resolve_tx_params(overrides))
    else:
        params = _resolve_tx_params(params)
    return params


def _pack_root_from_models_path(model_path: Path) -> Path:
    """.../Pack/Source/Models/file.fbx → Pack."""
    resolved = model_path.resolve()
    if resolved.is_file():
        # .../Pack/Source/Models/name.fbx
        if resolved.parent.name == "Models" and resolved.parent.parent.name == "Source":
            return resolved.parent.parent.parent
        return resolved.parent
    # directory
    if resolved.name == "Models" and resolved.parent.name == "Source":
        return resolved.parent.parent
    if (resolved / "Source" / "Models").is_dir():
        return resolved
    return resolved

def reexport_ship_from_model(
    model_path: Path,
    *,
    out_dir: Optional[Path] = None,
    name: Optional[str] = None,
    spec: Optional[Dict[str, Any]] = None,
    blender: Optional[str] = None,
    rewrite_defs: bool = False,
    theme: str = "",
) -> Dict[str, Any]:
    """
    Re-render spritesheet/hero/mask from an existing Source/Models mesh.
    Does not rebuild the mesh.
    """
    model_path = Path(model_path)
    if not model_path.is_file():
        raise FileNotFoundError(model_path)

    ship_name = name or model_path.stem
    if out_dir is None:
        out_dir = _pack_root_from_models_path(model_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    models_root = model_path.parent
    params = _load_export_params(models_root, ship_name, spec)
    sheet_path = out_dir / f"{ship_name}.jpg"
    hero_path = out_dir / f"{ship_name}Large.jpg"
    mask_path = out_dir / f"{ship_name}Mask.bmp"

    result: Dict[str, Any] = {
        "shipRotation": {
            **params,
            "viewportRatio": _viewport_ratio(params["frame_width"]),
            "source": "reexport",
        },
        "files": {"mesh": str(model_path), "finalModel": str(model_path)},
        "spritesheet_exit": None,
    }

    code = _run_blender_spritesheet(
        model_path=model_path,
        sheet_path=sheet_path,
        hero_path=hero_path,
        params=params,
        blender=blender,
    )
    result["spritesheet_exit"] = code
    if code != 0 or not sheet_path.is_file():
        result["ok"] = False
        return result

    result["shipRotation"]["source"] = "blender3d_reexport"
    result["files"]["spritesheet"] = str(sheet_path)
    result["files"]["sprite"] = str(sheet_path)
    if mask_path.is_file():
        result["files"]["spritesheetMask"] = str(mask_path)
    if hero_path.is_file():
        result["files"]["hero"] = str(hero_path)

    preserved = preserve_final_model(out_dir, ship_name, model_path, params=params)
    result["files"]["finalModel"] = str(preserved)
    result["files"]["modelsDir"] = str(models_dir(out_dir))

    if not (spec or {}).get("no_unique_hud"):
        try:
            from ship_hud_export import export_unique_ship_hud

            hud = export_unique_ship_hud(
                out_dir,
                ship_name,
                hero=hero_path if hero_path.is_file() else None,
                base_mesh=preserved,
                spec=dict(spec or {}),
                unique_hud=True,
            )
            result["files"].update(hud.get("files") or {})
            if hud.get("uniqueHud") is not None:
                result["uniqueHud"] = hud["uniqueHud"]
        except Exception as exc:
            print(f"[WARN] unique ship HUD reexport failed: {exc}", file=sys.stderr)

    if not (spec or {}).get("no_sheet_swapouts"):
        try:
            from ship_spritesheet_swapouts import generate_spritesheet_swapouts

            base_sheet = out_dir / f"{ship_name}_base.jpg"
            src_sheet = base_sheet if base_sheet.is_file() else sheet_path
            sw = generate_spritesheet_swapouts(
                out_dir,
                ship_name,
                sheet=src_sheet,
                mask=mask_path if mask_path.is_file() else None,
                facings=int(params["facings"]),
                columns=int(params["columns"]),
                armor_entity=(spec or {}).get("armorItem") or (spec or {}).get("armor"),
                shield_entity=(spec or {}).get("shieldItem") or (spec or {}).get("shield"),
                apply_active=True,
                force=bool((spec or {}).get("force_swapouts")),
                only_missing=not bool((spec or {}).get("force_swapouts")),
            )
            result["sheetSwapouts"] = sw
            if (sw.get("active") or {}).get("spritesheet"):
                result["files"]["spritesheet"] = sw["active"]["spritesheet"]
                result["files"]["sprite"] = sw["active"]["spritesheet"]
            if (sw.get("active") or {}).get("shieldSheet"):
                result["files"]["shieldOverlaySheet"] = sw["active"]["shieldSheet"]
            if (sw.get("active") or {}).get("shieldMask"):
                result["files"]["shieldOverlayMask"] = sw["active"]["shieldMask"]
            if (sw.get("active") or {}).get("hullSheet"):
                result["files"]["hullSwapSheet"] = sw["active"]["hullSheet"]
        except Exception as exc:
            print(f"[WARN] spritesheet swapouts reexport failed: {exc}", file=sys.stderr)

    if rewrite_defs:
        from game_asset_defs import rewrite_ship_defs_from_pack

        theme_s = theme or ship_name
        xml = rewrite_ship_defs_from_pack(
            out_dir,
            ship_name,
            theme=theme_s,
            spec=dict(spec or {}),
        )
        result["files"]["transcendence"] = str(xml)

    result["ok"] = True
    return result


def reexport_ships_from_folder(
    models_dir_path: Path,
    *,
    out_dir: Optional[Path] = None,
    name: Optional[str] = None,
    spec: Optional[Dict[str, Any]] = None,
    blender: Optional[str] = None,
    rewrite_defs: bool = False,
    theme: str = "",
) -> List[Dict[str, Any]]:
    """Re-export all (or one named) models under Source/Models."""
    root = Path(models_dir_path)
    # Allow passing pack root or Source/Models
    if root.is_dir() and (root / SOURCE_MODELS_REL).is_dir() and not find_models(root, name=name):
        root = root / SOURCE_MODELS_REL
    models = find_models(root, name=name)
    if not models:
        raise FileNotFoundError(f"No ship models (.fbx/.obj/.blend) under {models_dir_path}")
    pack_out = out_dir
    if pack_out is None and root.name == "Models" and root.parent.name == "Source":
        pack_out = root.parent.parent
    results = []
    for model in models:
        print(f"[reexport] {model}", file=sys.stderr)
        results.append(
            reexport_ship_from_model(
                model,
                out_dir=pack_out,
                name=model.stem if not name else name,
                spec=spec,
                blender=blender,
                rewrite_defs=rewrite_defs,
                theme=theme or model.stem,
            )
        )
    return results

def export_ship_rotation_sheet(
    out_dir: Path,
    name: str,
    *,
    theme: str,
    sketch: Path,
    spec: Optional[Dict[str, Any]] = None,
    blender: Optional[str] = None,
    ensure_mesh: bool = True,
) -> Dict[str, Any]:
    """
    Build mesh → Blender 120-facings sheet (or 2D rotation fallback).
    Preserves the final mesh under Source/Models/ for user touch-ups.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    spec = dict(spec or {})
    params = _resolve_tx_params(spec)

    sheet_path = out_dir / f"{name}.jpg"
    hero_path = out_dir / f"{name}Large.jpg"
    mask_path = out_dir / f"{name}Mask.bmp"

    result: Dict[str, Any] = {
        "shipRotation": {
            **params,
            "viewportRatio": _viewport_ratio(params["frame_width"]),
            "source": "unknown",
        },
        "files": {},
        "mesh_exit": None,
        "spritesheet_exit": None,
    }

    model_path: Optional[Path] = None
    if ensure_mesh and sketch.is_file():
        model_path, mesh_code = _export_mesh_from_sketch(
            out_dir=out_dir,
            name=name,
            theme=theme,
            sketch=sketch,
            spec=spec,
            blender=blender,
            no_sd=bool(spec.get("no_sd", True)),
        )
        result["mesh_exit"] = mesh_code
        if model_path:
            result["files"]["mesh"] = str(model_path)

    sheet_ok = False
    if model_path:
        code = _run_blender_spritesheet(
            model_path=model_path,
            sheet_path=sheet_path,
            hero_path=hero_path,
            params=params,
            blender=blender,
        )
        result["spritesheet_exit"] = code
        sheet_ok = code == 0 and sheet_path.is_file()
        if sheet_ok:
            result["shipRotation"]["source"] = "blender3d"
            try:
                final = preserve_final_model(out_dir, name, model_path, params=params)
                result["files"]["finalModel"] = str(final)
                result["files"]["modelsDir"] = str(models_dir(out_dir))
            except Exception as exc:
                print(f"[WARN] Source/Models preserve failed: {exc}", file=sys.stderr)

    if not sheet_ok and sketch.is_file():
        print("[ship_spritesheet] Blender unavailable or failed; using 2D rotation fallback", file=sys.stderr)
        if _proc_rotation_sheet(sketch, sheet_path, params=params):
            sheet_ok = True
            result["shipRotation"]["source"] = "2d_rotation"
            result["spritesheet_exit"] = 0
            try:
                from PIL import Image

                hero = Image.open(sketch).convert("RGBA")
                hero = hero.resize(
                    (params["hero_width"], params["hero_height"]),
                    Image.Resampling.LANCZOS,
                )
                rgb = Image.new("RGB", hero.size, (0, 0, 0))
                rgb.paste(hero, mask=hero.split()[3])
                rgb.save(hero_path, "JPEG", quality=92)
            except Exception:
                pass

    if sheet_ok:
        result["files"]["spritesheet"] = str(sheet_path)
        result["files"]["sprite"] = str(sheet_path)
        if mask_path.is_file():
            result["files"]["spritesheetMask"] = str(mask_path)
        if hero_path.is_file():
            result["files"]["hero"] = str(hero_path)

        # Unique Armor/Shield HUD (disable via spec no_unique_hud)
        if not spec.get("no_unique_hud"):
            try:
                from ship_hud_export import export_unique_ship_hud

                hud = export_unique_ship_hud(
                    out_dir,
                    name,
                    hero=hero_path if hero_path.is_file() else None,
                    sketch=sketch if sketch.is_file() else None,
                    base_mesh=Path(result["files"].get("finalModel") or result["files"].get("mesh") or "")
                    if (result["files"].get("finalModel") or result["files"].get("mesh"))
                    else None,
                    spec=spec,
                    unique_hud=True,
                )
                result["files"].update(hud.get("files") or {})
                if hud.get("uniqueHud") is not None:
                    result["uniqueHud"] = hud["uniqueHud"]
            except Exception as exc:
                print(f"[WARN] unique ship HUD export failed: {exc}", file=sys.stderr)

        # Masked hull/shield spritesheet swapouts from alt textures + Mask.bmp
        if not spec.get("no_sheet_swapouts"):
            try:
                from ship_spritesheet_swapouts import generate_spritesheet_swapouts

                sw = generate_spritesheet_swapouts(
                    out_dir,
                    name,
                    sheet=sheet_path,
                    mask=mask_path if mask_path.is_file() else None,
                    facings=int(params["facings"]),
                    columns=int(params["columns"]),
                    armor_entity=(spec.get("armorItem") or spec.get("armor")),
                    shield_entity=(spec.get("shieldItem") or spec.get("shield")),
                    apply_active=True,
                    force=bool(spec.get("force_swapouts")),
                    only_missing=not bool(spec.get("force_swapouts")),
                )
                result["sheetSwapouts"] = sw
                if (sw.get("active") or {}).get("spritesheet"):
                    result["files"]["spritesheet"] = sw["active"]["spritesheet"]
                    result["files"]["sprite"] = sw["active"]["spritesheet"]
                if (sw.get("active") or {}).get("shieldSheet"):
                    result["files"]["shieldOverlaySheet"] = sw["active"]["shieldSheet"]
                if (sw.get("active") or {}).get("shieldMask"):
                    result["files"]["shieldOverlayMask"] = sw["active"]["shieldMask"]
                if (sw.get("active") or {}).get("hullSheet"):
                    result["files"]["hullSwapSheet"] = sw["active"]["hullSheet"]
            except Exception as exc:
                print(f"[WARN] spritesheet swapouts failed: {exc}", file=sys.stderr)

    return result


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="Export / re-export Transcendence ship rotation spritesheets from mesh or sketch"
    )
    ap.add_argument("--out-dir", default="", help="Pack output folder (sheet + Source/Models)")
    ap.add_argument("--name", default="", help="Ship name (defaults to model stem on reexport)")
    ap.add_argument("--theme", default="")
    ap.add_argument("--sketch", default="", help="Top-down sketch for full generate path")
    ap.add_argument("--blender", default=None)
    ap.add_argument("--facings", type=int, default=TX_SHIP_DEFAULTS["facings"])
    ap.add_argument("--columns", type=int, default=TX_SHIP_DEFAULTS["columns"])
    ap.add_argument("--frame-width", type=int, default=TX_SHIP_DEFAULTS["frame_width"])
    ap.add_argument(
        "--reexport-from",
        default="",
        help="Source/Models folder (or single .fbx) — only re-render sprites, no mesh regen",
    )
    ap.add_argument("--defs", action="store_true", help="Rewrite *_ship_transcendence.xml after reexport")
    args = ap.parse_args()

    spec = {
        "facings": args.facings,
        "columns": args.columns,
        "frameWidth": args.frame_width,
        "frameHeight": args.frame_width,
    }

    if args.reexport_from:
        models_path = Path(args.reexport_from)
        out_dir = Path(args.out_dir) if args.out_dir else None
        results = reexport_ships_from_folder(
            models_path,
            out_dir=out_dir,
            name=args.name or None,
            spec=spec,
            blender=args.blender,
            rewrite_defs=args.defs,
            theme=args.theme,
        )
        print(json.dumps(results, indent=2))
        return 0 if all(r.get("ok") for r in results) else 1

    if not args.out_dir or not args.name or not args.sketch:
        ap.error("--out-dir, --name, and --sketch are required unless using --reexport-from")

    out = export_ship_rotation_sheet(
        Path(args.out_dir),
        args.name,
        theme=args.theme or args.name,
        sketch=Path(args.sketch),
        spec=spec,
        blender=args.blender,
    )
    print(out)
    return 0 if out.get("files", {}).get("spritesheet") else 1


if __name__ == "__main__":
    raise SystemExit(main())