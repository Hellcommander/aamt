#!/usr/bin/env python3
"""Blender: import TRELLIS GLB, export FBX, dump embedded textures as PNG skins.

  blender --background --python blender_glb_to_unity.py -- cfg.json

cfg.json: {glb, fbx, skin_dir, name}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy


def _cfg() -> dict:
    argv = sys.argv
    argv = argv[argv.index("--") + 1 :] if "--" in argv else []
    if not argv:
        raise SystemExit("usage: blender --background --python blender_glb_to_unity.py -- cfg.json")
    return json.loads(Path(argv[0]).read_text(encoding="utf-8"))


def main() -> None:
    cfg = _cfg()
    glb = Path(cfg["glb"])
    fbx = Path(cfg["fbx"])
    skin_dir = Path(cfg["skin_dir"])
    name = cfg.get("name") or glb.stem
    skin_dir.mkdir(parents=True, exist_ok=True)
    fbx.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))

    # Dump images
    saved = {}
    for i, img in enumerate(list(bpy.data.images)):
        if not img.pixels and not img.filepath:
            continue
        label = (img.name or f"tex{i}").lower()
        if "normal" in label:
            key = "normal"
        elif "emiss" in label:
            key = "emission"
        elif "metal" in label:
            key = "metallic"
        elif "rough" in label:
            key = "roughness"
        elif "occlusion" in label or "ao" == label:
            key = "ao"
        else:
            key = "diffuse" if "diffuse" not in saved else f"map{i}"
        out = skin_dir / f"{name}_{key}.png"
        try:
            # pack then save
            if img.filepath and Path(bpy.path.abspath(img.filepath)).is_file() and not img.packed_file:
                img.pack()
            img.filepath_raw = str(out)
            img.file_format = "PNG"
            img.save()
            saved[key] = str(out)
            print("[OK] skin", out)
        except Exception as exc:
            print("[WARN] texture save failed", img.name, exc)

    # Export selected meshes
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        if obj.type in {"MESH", "EMPTY", "ARMATURE"}:
            obj.select_set(True)
    bpy.ops.export_scene.fbx(
        filepath=str(fbx),
        use_selection=True,
        apply_scale_options="FBX_SCALE_ALL",
        path_mode="COPY",
        embed_textures=True,
        add_leaf_bones=False,
    )
    print("[OK] exported FBX", fbx)
    manifest = {
        "name": name,
        "glb": str(glb),
        "fbx": str(fbx),
        "maps": saved,
    }
    (skin_dir / f"{name}_pbr.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
