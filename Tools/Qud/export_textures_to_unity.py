#!/usr/bin/env python3
"""
Bridge Qud Textures/ PNGs into Assets/Resources with Unity .meta files.

Does not require a Unity Editor. After this, run QudUnityAssetGenerator.ps1
(or Shared Invoke-AamtUnityAssetBundles) once the matching Editor is installed.

Optional --pbr / --mesh use the real Shared Blender pipeline (displaced,
armor_panel, silhouette, …) — not a plane/cube stub.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

_shared = Path(__file__).resolve().parent.parent / "Shared"
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from mesh_skin_export import SHAPE_CHOICES  # noqa: E402
from unity_meta import write_model_meta, write_texture_meta  # noqa: E402


def export_textures(
    mod_path: Path,
    *,
    overwrite_meta: bool = False,
    generate_pbr: bool = False,
    export_mesh: bool = False,
    mesh_shape: str = "displaced",
    sketch: Path | None = None,
    no_sd: bool = False,
    theme: str | None = None,
) -> int:
    textures = mod_path / "Textures"
    assets = mod_path / "Assets" / "Resources" / "Textures"
    if not textures.is_dir():
        print(f"[WARN] No Textures/ under {mod_path}", file=sys.stderr)
        return 0
    assets.mkdir(parents=True, exist_ok=True)
    count = 0
    for png in textures.rglob("*.png"):
        rel = png.relative_to(textures)
        dest = assets / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(png, dest)
        write_texture_meta(dest, kind="sprite", overwrite=overwrite_meta, root_for_guid=mod_path / "Assets")
        count += 1
        print(f"[OK] {dest}")
    print(f"[DONE] Exported {count} textures -> {assets}")

    if generate_pbr and count > 0:
        try:
            from pbr_skin_generator import generate_pbr_skin_set

            skin_name = "qud_mod"
            skin_dir = assets / "Skins"
            generate_pbr_skin_set(
                skin_dir,
                skin_name,
                {"theme": theme or mod_path.name, "shape": mesh_shape},
                quality="standard",
                use_sd=not no_sd,
            )
            print(f"[PBR] Skin set under {skin_dir}")
            if export_mesh:
                from mesh_skin_export import find_blender

                fbx = mod_path / "Assets" / "Resources" / "Meshes" / f"{skin_name}.fbx"
                fbx.parent.mkdir(parents=True, exist_ok=True)
                mesh_script = _shared / "mesh_skin_export.py"
                shape = mesh_shape if mesh_shape in SHAPE_CHOICES else "displaced"
                cmd = [
                    sys.executable,
                    str(mesh_script),
                    "--skin-dir",
                    str(skin_dir),
                    "--name",
                    skin_name,
                    "--fbx",
                    str(fbx),
                    "--shape",
                    shape,
                ]
                if sketch and Path(sketch).exists():
                    cmd += ["--sketch", str(Path(sketch).resolve())]
                print(f"[MESH] {' '.join(cmd)}")
                subprocess.run(cmd, check=False)
                if fbx.exists():
                    write_model_meta(fbx, overwrite=overwrite_meta, root_for_guid=mod_path / "Assets")
                    print(f"[MESH] FBX + ModelImporter .meta -> {fbx}")
                elif find_blender() is None:
                    print("[WARN] Blender missing — PBR skins only (no FBX)", file=sys.stderr)
        except Exception as exc:
            print(f"[WARN] PBR/mesh generation skipped: {exc}", file=sys.stderr)
    return count


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mod", required=True, help="Qud mod root (contains Textures/)")
    ap.add_argument("--overwrite-meta", action="store_true")
    ap.add_argument("--pbr", action="store_true", help="Also generate a PBR skin set under Assets/Resources/Textures/Skins")
    ap.add_argument(
        "--mesh",
        action="store_true",
        help="With --pbr, also export a real Blender FBX (displaced/armor_panel/silhouette/…)",
    )
    ap.add_argument("--mesh-shape", choices=list(SHAPE_CHOICES), default="displaced")
    ap.add_argument("--sketch", default=None, help="Optional silhouette/height source image")
    ap.add_argument("--theme", default=None, help="PBR theme override (default: mod folder name)")
    ap.add_argument("--no-sd", action="store_true", help="Procedural PBR only (no Stable Diffusion)")
    args = ap.parse_args()
    n = export_textures(
        Path(args.mod),
        overwrite_meta=args.overwrite_meta,
        generate_pbr=args.pbr,
        export_mesh=args.mesh,
        mesh_shape=args.mesh_shape,
        sketch=Path(args.sketch) if args.sketch else None,
        no_sd=args.no_sd,
        theme=args.theme,
    )
    return 0 if n >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
