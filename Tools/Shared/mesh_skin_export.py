#!/usr/bin/env python3
"""
AAMT Unity mesh export from PBR skins (real Blender pipeline).

Replaces the old plane/cube stub with Shared/blender_aamt_mesh.py:
  - displaced / organic / armor_panel / extruded meshes from diffuse height
  - silhouette / sketch / cutout from alpha or luma
  - solidify + bevel + subdivision
  - full Principled PBR (diffuse/normal/roughness/metallic/emission)
  - FBX (+ optional OBJ) with Unity .meta

Examples:
  python mesh_skin_export.py --skin-dir out --name armor --fbx armor.fbx --shape displaced
  python mesh_skin_export.py --skin-dir out --name armor --fbx armor.fbx --generate-skin --theme "obsidian plate"
  python mesh_skin_export.py --skin-dir out --name icon --fbx icon.fbx --shape silhouette --sketch icon.png
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

BLENDER_SCRIPT = _SHARED / "blender_aamt_mesh.py"

SHAPE_CHOICES = (
    "plane",
    "cube",
    "sphere",
    "cylinder",
    "panel",
    "armor",
    "armor_panel",
    "displaced",
    "organic",
    "extruded",
    "silhouette",
    "sketch",
    "cutout",
    "heightmap",
)


def find_blender(explicit: str | None = None) -> str | None:
    """Resolve blender.exe via Tools/TranscendenceTools.ini (see Shared/tool_paths.py)."""
    try:
        from tool_paths import find_blender as _ini_find_blender

        return _ini_find_blender(explicit)
    except Exception:
        pass
    # Minimal fallback if tool_paths is unavailable
    if explicit and Path(explicit).exists():
        return explicit
    for key in ("BLENDER", "BLENDER_PATH", "BLENDER_EXE"):
        raw = (os.environ.get(key) or "").strip().strip('"')
        if not raw:
            continue
        p = Path(raw)
        if p.is_file() and p.name.lower() == "blender.exe":
            return str(p)
        if p.is_dir():
            exe = p / "blender.exe"
            if exe.exists():
                return str(exe)
    which = shutil.which("blender")
    return which


def _default_maps(name: str) -> dict:
    return {
        "diffuse": f"{name}_diffuse.png",
        "normal": f"{name}_normal.png",
        "roughness": f"{name}_roughness.png",
        "metallic": f"{name}_metallic.png",
        "metallicgloss": f"{name}_metallicgloss.png",
        "emission": f"{name}_emission.png",
    }


def _load_maps(skin_dir: Path, name: str) -> dict:
    reg = skin_dir / f"{name}_pbr.json"
    if reg.exists():
        data = json.loads(reg.read_text(encoding="utf-8-sig"))
        maps = data.get("maps") or {}
        if maps:
            return maps
    return _default_maps(name)


def _shape_from_spec(spec: dict, fallback: str) -> str:
    for key in ("shape", "meshShape", "mesh"):
        val = spec.get(key)
        if isinstance(val, str) and val.strip():
            s = val.strip().lower().replace(" ", "_")
            if s in SHAPE_CHOICES:
                return s
            if s in ("ico", "icosphere"):
                return "organic"
            if s in ("box",):
                return "cube"
    return fallback


def export_mesh_from_spec(
    *,
    skin_dir: Path | str,
    name: str,
    fbx: Path | str,
    spec: dict | None = None,
    shape: str = "displaced",
    quality: str = "standard",
    use_sd: bool = True,
    blender: str | None = None,
    subdivisions: int | None = None,
    displace_strength: float | None = None,
    solidify_thickness: float | None = None,
    bevel_amount: float | None = None,
    obj: Path | str | None = None,
) -> int:
    """
    Ollama/JSON-friendly entry: build PBR maps from a design spec, then real FBX mesh.
    """
    skin_dir = Path(skin_dir)
    fbx = Path(fbx)
    spec = dict(spec or {})
    theme = str(spec.get("theme") or spec.get("material") or name)
    from pbr_skin_generator import generate_pbr_skin_set

    generate_pbr_skin_set(
        skin_dir,
        name,
        {**spec, "theme": theme},
        quality=quality,
        use_sd=use_sd,
    )
    shape = _shape_from_spec(spec, shape)
    sketch = spec.get("sketch") or spec.get("sketchPath") or spec.get("heightImage")
    return run_blender_export(
        skin_dir=skin_dir,
        name=name,
        fbx=fbx,
        shape=shape,
        blender=blender,
        subdivisions=subdivisions if subdivisions is not None else int(spec.get("subdivisions", -1)),
        displace_strength=displace_strength
        if displace_strength is not None
        else float(spec.get("displaceStrength", spec.get("displacementStrength", -1))),
        solidify_thickness=solidify_thickness
        if solidify_thickness is not None
        else float(spec.get("solidifyThickness", spec.get("extrudeDepth", -1))),
        bevel_amount=bevel_amount
        if bevel_amount is not None
        else float(spec.get("bevelAmount", -1)),
        obj=Path(obj) if obj else None,
        sketch=Path(sketch) if sketch else None,
        alpha_threshold=float(spec.get("alphaThreshold", -1)),
        silhouette_res=int(spec.get("silhouetteRes", -1)),
    )


def run_blender_export(
    *,
    skin_dir: Path,
    name: str,
    fbx: Path,
    shape: str = "displaced",
    blender: str | None = None,
    subdivisions: int = -1,
    displace_strength: float = -1.0,
    solidify_thickness: float = -1.0,
    bevel_amount: float = -1.0,
    obj: Path | None = None,
    sketch: Path | None = None,
    alpha_threshold: float = -1.0,
    silhouette_res: int = -1,
) -> int:
    if not BLENDER_SCRIPT.exists():
        print(f"[ERROR] Missing Blender script: {BLENDER_SCRIPT}", file=sys.stderr)
        return 1

    maps = _load_maps(skin_dir, name)
    diffuse = skin_dir / maps.get("diffuse", "")
    if not diffuse.exists() and not (sketch and Path(sketch).exists()):
        print(f"[ERROR] Diffuse map missing: {diffuse}", file=sys.stderr)
        return 1

    blender_exe = find_blender(blender)
    if not blender_exe:
        print("[WARN] Blender not found — wrote/used skins only; skip FBX.", file=sys.stderr)
        return 2

    # Pack PBR into .blend (ortho path) — FBX alone often greys Principled textures.
    blend = fbx.with_suffix(".blend")
    # Negative means "use blender_aamt_mesh.py defaults for this shape"
    cfg: dict = {
        "name": name,
        "shape": shape if shape in SHAPE_CHOICES else "displaced",
        "skin_dir": str(skin_dir.resolve()),
        "maps": maps,
        "fbx": str(fbx.resolve()),
        "blend": str(blend.resolve()),
    }
    if obj:
        cfg["obj"] = str(Path(obj).resolve())
    if sketch and Path(sketch).exists():
        cfg["sketch"] = str(Path(sketch).resolve())
    if subdivisions is not None and subdivisions >= 0:
        cfg["subdivisions"] = int(subdivisions)
    if displace_strength is not None and displace_strength >= 0:
        cfg["displace_strength"] = float(displace_strength)
    if solidify_thickness is not None and solidify_thickness >= 0:
        cfg["solidify_thickness"] = float(solidify_thickness)
    if bevel_amount is not None and bevel_amount >= 0:
        cfg["bevel_amount"] = float(bevel_amount)
    if alpha_threshold is not None and alpha_threshold >= 0:
        cfg["alpha_threshold"] = float(alpha_threshold)
    if silhouette_res is not None and silhouette_res > 0:
        cfg["silhouette_res"] = int(silhouette_res)

    fbx.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        cfg_path = Path(td) / "cfg.json"
        cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        cmd = [
            blender_exe,
            "--background",
            "--python",
            str(BLENDER_SCRIPT),
            "--",
            str(cfg_path),
        ]
        print("[Blender]", " ".join(cmd))
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.stdout:
            print(proc.stdout[-3000:])
        if proc.returncode != 0:
            print(proc.stderr[-3000:], file=sys.stderr)
            return proc.returncode

    if not fbx.exists():
        print(f"[ERROR] FBX not written: {fbx}", file=sys.stderr)
        return 1
    if blend.exists():
        print(f"[OK] BLEND: {blend}")
    else:
        print(f"[WARN] BLEND not written (ortho may grey out): {blend}", file=sys.stderr)

    try:
        from unity_meta import write_model_meta

        write_model_meta(fbx)
        if obj and Path(obj).exists():
            write_model_meta(obj)
    except Exception as exc:
        print(f"[WARN] mesh .meta skipped: {exc}", file=sys.stderr)

    print(f"[OK] FBX: {fbx}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Export a skinned mesh FBX for Unity (real Blender pipeline)")
    ap.add_argument("--skin-dir", required=True, help="Folder with {name}_diffuse.png etc.")
    ap.add_argument("--name", required=True)
    ap.add_argument("--fbx", required=True, help="Output .fbx path")
    ap.add_argument("--obj", default=None, help="Optional OBJ export path")
    ap.add_argument("--shape", choices=SHAPE_CHOICES, default="displaced")
    ap.add_argument("--blender", default=None)
    ap.add_argument("--generate-skin", action="store_true", help="Also run pbr_skin_generator first")
    ap.add_argument("--theme", default="fantasy material")
    ap.add_argument("--quality", default="standard")
    ap.add_argument("--no-sd", action="store_true")
    ap.add_argument("--spec", default=None, help="Optional Ollama/JSON design spec; implies skin generation")
    ap.add_argument("--subdivisions", type=int, default=-1)
    ap.add_argument("--displace-strength", type=float, default=-1.0)
    ap.add_argument("--solidify-thickness", type=float, default=-1.0)
    ap.add_argument("--bevel-amount", type=float, default=-1.0)
    ap.add_argument("--sketch", default=None, help="Optional sketch/silhouette source image")
    ap.add_argument("--alpha-threshold", type=float, default=-1.0)
    ap.add_argument("--silhouette-res", type=int, default=-1)
    args = ap.parse_args()

    skin_dir = Path(args.skin_dir)
    skin_dir.mkdir(parents=True, exist_ok=True)

    if args.spec:
        spec_path = Path(args.spec)
        spec = json.loads(spec_path.read_text(encoding="utf-8-sig")) if spec_path.exists() else {}
        if args.sketch:
            spec["sketch"] = args.sketch
        return export_mesh_from_spec(
            skin_dir=skin_dir,
            name=args.name,
            fbx=args.fbx,
            spec=spec,
            shape=args.shape,
            quality=args.quality,
            use_sd=not args.no_sd,
            blender=args.blender,
            subdivisions=args.subdivisions,
            displace_strength=args.displace_strength,
            solidify_thickness=args.solidify_thickness,
            bevel_amount=args.bevel_amount,
            obj=args.obj,
        )

    if args.generate_skin:
        from pbr_skin_generator import generate_pbr_skin_set

        generate_pbr_skin_set(
            skin_dir,
            args.name,
            {"theme": args.theme},
            quality=args.quality,
            use_sd=not args.no_sd,
        )

    return run_blender_export(
        skin_dir=skin_dir,
        name=args.name,
        fbx=Path(args.fbx),
        shape=args.shape,
        blender=args.blender,
        subdivisions=args.subdivisions,
        displace_strength=args.displace_strength,
        solidify_thickness=args.solidify_thickness,
        bevel_amount=args.bevel_amount,
        obj=Path(args.obj) if args.obj else None,
        sketch=Path(args.sketch) if args.sketch else None,
        alpha_threshold=args.alpha_threshold,
        silhouette_res=args.silhouette_res,
    )


if __name__ == "__main__":
    raise SystemExit(main())
