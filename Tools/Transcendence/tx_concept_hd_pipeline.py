#!/usr/bin/env python3
"""Cursor 3D concept → TRELLIS mesh → backup .blend → Transcendence HD 120-facings.

Transcendence is 2.5D: the game consumes a rotation spritesheet (JPG + Mask.bmp),
not the mesh. Highest practical HD here matches the capital-whale bar already in
this toolset: 256×256 cells × 120 facings × 12 columns (3072×2560 sheet), which
stays under a 4096 texture cap. EarthSlaverHD is 128; this pipeline is one step
above that. Use --frame-size 320 if you want to push width to 3840.

Starfield can reuse the same GLB from Shared/Concepts/meshes.

  python tx_concept_hd_pipeline.py --id scSpaceWhale
  python tx_concept_hd_pipeline.py --all
  python tx_concept_hd_pipeline.py --concept References/scHornRam.png --id scHornRam
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_TX = Path(__file__).resolve().parent
_TOOLS = _TX.parent
_SHARED = _TOOLS / "Shared"
_COMMON = _TOOLS / "Common"
for _p in (_TX, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import tx_ai_pipeline as tx  # noqa: E402

CONCEPT_INDEX = _SHARED / "Concepts" / "index.json"
EXPORT_SCRIPT = _COMMON / "blender_ship_spritesheet_export.py"

# Transcendence ship HD: JPG sheet + BMP mask. 256px cells = capital-whale HD.
HD_DEFAULTS = {
    "facings": 120,
    "columns": 12,
    "frame": 256,
    "hero": 512,
    "supersample": 4,
}


def _load_index() -> Dict[str, str]:
    if not CONCEPT_INDEX.is_file():
        return {}
    data = json.loads(CONCEPT_INDEX.read_text(encoding="utf-8"))
    raw = data.get("concepts") or {}
    return {str(k): str(v) for k, v in raw.items()}


def resolve_concept(asset_id: str, explicit: str = "") -> Path:
    if explicit:
        hit = tx.resolve_concept_art(path=explicit)
        if hit:
            return hit
        p = Path(explicit)
        if p.is_file():
            return p.resolve()
        raise FileNotFoundError(f"concept not found: {explicit}")
    indexed = _load_index().get(asset_id)
    if indexed:
        hit = tx.resolve_concept_art(path=indexed)
        if hit:
            return hit
    hit = tx.resolve_concept_art(path=f"References/{asset_id}.png")
    if hit:
        return hit
    raise FileNotFoundError(
        f"no 3D concept for {asset_id}; pass --concept or add it to Shared/Concepts/index.json"
    )


def _viewport_ratio(frame: int) -> float:
    return max(0.004, min(0.05, frame * (0.01375 / 128.0)))


def _rows(facings: int, columns: int) -> int:
    return max(1, math.ceil(facings / columns))


def _write_image_xml(out_dir: Path, asset_id: str, frame: int, facings: int) -> Path:
    xml = out_dir / f"{asset_id}_ImageReference.xml"
    xml.write_text(
        (
            f'<!-- HD 120-facings from Cursor 3D concept → TRELLIS → Blender -->\n'
            f'<Image imageID="&rs{asset_id}Image;" '
            f'bitmask="{asset_id}_120facingsMask.bmp" '
            f'imageWidth="{frame}" imageHeight="{frame}" '
            f'rotationCount="{facings}" viewportRatio="{_viewport_ratio(frame):.6f}" '
            f'rotationOffset="17" />\n'
        ),
        encoding="utf-8",
    )
    return xml


def _run_blender_hd(
    *,
    model: Path,
    sheet: Path,
    hero: Path,
    blend_backup: Path,
    frame: int,
    facings: int,
    columns: int,
    supersample: int,
    hero_size: int,
    blender: Optional[str] = None,
) -> int:
    blender_exe = blender or tx.find_blender()
    if not blender_exe:
        raise RuntimeError("Blender not found")
    if not EXPORT_SCRIPT.is_file():
        raise RuntimeError(f"missing {EXPORT_SCRIPT}")
    blend_backup.parent.mkdir(parents=True, exist_ok=True)
    sheet.parent.mkdir(parents=True, exist_ok=True)
    args = [
        blender_exe,
        "--background",
        "--python",
        str(EXPORT_SCRIPT),
        "--",
        "--model",
        str(model),
        "--output",
        str(sheet),
        "--facings",
        str(facings),
        "--columns",
        str(columns),
        "--rows",
        str(_rows(facings, columns)),
        "--frame-width",
        str(frame),
        "--frame-height",
        str(frame),
        "--output-format",
        "JPG",
        "--game-format",
        "Transcendence",
        "--generate-mask",
        "--hero-image",
        str(hero),
        "--hero-width",
        str(hero_size),
        "--hero-height",
        str(hero_size),
        "--supersample",
        str(supersample),
        "--save-blend",
        str(blend_backup),
    ]
    print("[hd] Blender facings:", " ".join(args[:6]), "...")
    proc = subprocess.run(args, capture_output=False)
    return int(proc.returncode)


def run_one(
    asset_id: str,
    *,
    concept: str = "",
    out_root: Path,
    backup_root: Path,
    frame: int = HD_DEFAULTS["frame"],
    facings: int = HD_DEFAULTS["facings"],
    columns: int = HD_DEFAULTS["columns"],
    supersample: int = HD_DEFAULTS["supersample"],
    hero_size: int = HD_DEFAULTS["hero"],
    skip_trellis: bool = False,
    glb_in: str = "",
) -> Dict[str, Any]:
    concept_path = resolve_concept(asset_id, concept)
    pack = out_root / asset_id
    mesh_dir = pack / "Meshes"
    mesh_dir.mkdir(parents=True, exist_ok=True)
    glb = Path(glb_in) if glb_in else mesh_dir / f"{asset_id}.glb"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_dir = backup_root / asset_id
    backup_dir.mkdir(parents=True, exist_ok=True)
    blend_latest = backup_dir / f"{asset_id}.blend"
    blend_stamp = backup_dir / f"{asset_id}_{stamp}.blend"

    result: Dict[str, Any] = {
        "id": asset_id,
        "concept": str(concept_path),
        "pack": str(pack),
        "backupDir": str(backup_dir),
    }
    shutil.copy2(concept_path, backup_dir / concept_path.name)

    if skip_trellis and glb.is_file():
        print(f"[hd] reusing mesh {glb}")
    elif skip_trellis:
        result["ok"] = False
        result["error"] = f"--skip-trellis but no GLB at {glb}"
        return result
    else:
        print(f"[hd] TRELLIS from Cursor 3D concept {concept_path.name}")
        with tx.session(image=False, mesh=True):
            hit = tx.concept_mesh(
                tx.TRELLIS_CONCEPT_PROMPT,
                glb,
                concept=concept_path,
                asset_id=asset_id,
                publish_starfield=True,
            )
        if not hit or not hit.is_file():
            result["ok"] = False
            result["error"] = "TRELLIS did not write a GLB"
            return result
        glb = hit

    tx.release(force=True)

    sheet = pack / f"{asset_id}_120facings.jpg"
    hero = pack / f"{asset_id}Large.jpg"
    code = _run_blender_hd(
        model=glb,
        sheet=sheet,
        hero=hero,
        blend_backup=blend_latest,
        frame=frame,
        facings=facings,
        columns=columns,
        supersample=supersample,
        hero_size=hero_size,
    )
    if blend_latest.is_file():
        shutil.copy2(blend_latest, blend_stamp)

    xml = _write_image_xml(pack, asset_id, frame, facings)
    manifest = {
        "id": asset_id,
        "concept": str(concept_path),
        "glb": str(glb),
        "blend": str(blend_latest) if blend_latest.is_file() else None,
        "blendStamp": str(blend_stamp) if blend_stamp.is_file() else None,
        "spritesheet": str(sheet) if sheet.is_file() else None,
        "mask": str(sheet.with_name(sheet.stem + "Mask.bmp")) if sheet.is_file() else None,
        "hero": str(hero) if hero.is_file() else None,
        "xml": str(xml),
        "facings": facings,
        "frame": frame,
        "columns": columns,
        "supersample": supersample,
        "format": "JPG+BMP (Transcendence HD)",
        "starfieldMesh": str(tx.STARFIELD_MESH_DIR / f"{asset_id}.glb"),
        "blenderExit": code,
    }
    (pack / "hd_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (backup_dir / "hd_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    result.update(manifest)
    result["ok"] = bool(sheet.is_file() and blend_latest.is_file() and code == 0)
    if not result["ok"] and code != 0:
        result["error"] = f"Blender spritesheet exit {code}"
    return result


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Cursor 3D concept → TRELLIS → backup .blend → Transcendence HD 120-facings"
    )
    ap.add_argument("--id", action="append", default=[], help="Asset id from Shared/Concepts/index.json")
    ap.add_argument("--all", action="store_true", help="Every id in the concept index")
    ap.add_argument("--concept", default="", help="Override concept PNG for a single --id")
    ap.add_argument(
        "--out-dir",
        default=str(_TX / "Output" / "HdPipeline"),
        help="Spritesheet / GLB output root",
    )
    ap.add_argument(
        "--backup-dir",
        default=str(_TX / "Output" / "HdPipeline" / "Backup"),
        help="Folder for dated .blend backups",
    )
    ap.add_argument("--frame-size", type=int, default=HD_DEFAULTS["frame"])
    ap.add_argument("--facings", type=int, default=HD_DEFAULTS["facings"])
    ap.add_argument("--columns", type=int, default=HD_DEFAULTS["columns"])
    ap.add_argument("--supersample", type=int, default=HD_DEFAULTS["supersample"])
    ap.add_argument("--hero-size", type=int, default=HD_DEFAULTS["hero"])
    ap.add_argument("--skip-trellis", action="store_true", help="Reuse existing Meshes/{id}.glb")
    ap.add_argument("--glb", default="", help="Existing GLB (implies --skip-trellis)")
    args = ap.parse_args(argv)

    ids: List[str] = list(args.id)
    if args.all:
        ids = list(_load_index().keys())
    if not ids:
        ap.error("pass --id ASSET or --all")
    if args.concept and len(ids) != 1:
        ap.error("--concept requires exactly one --id")

    out_root = Path(args.out_dir)
    backup_root = Path(args.backup_dir)
    reports = []
    for asset_id in ids:
        print("=" * 64)
        print(f"[hd] {asset_id}")
        try:
            reports.append(
                run_one(
                    asset_id,
                    concept=args.concept,
                    out_root=out_root,
                    backup_root=backup_root,
                    frame=args.frame_size,
                    facings=args.facings,
                    columns=args.columns,
                    supersample=args.supersample,
                    hero_size=args.hero_size,
                    skip_trellis=bool(args.skip_trellis or args.glb),
                    glb_in=args.glb,
                )
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[hd] FAIL {asset_id}: {exc}", file=sys.stderr)
            reports.append({"id": asset_id, "ok": False, "error": str(exc)})

    summary = {"ok": sum(1 for r in reports if r.get("ok")), "fail": sum(1 for r in reports if not r.get("ok")), "jobs": reports}
    print(json.dumps(summary, indent=2))
    return 0 if all(r.get("ok") for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
