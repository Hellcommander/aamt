# blender_fit_armor.py
"""
Blender scaffold: export a race-fit armor/clothes FBX for Havok Content Tools 7.1.

Usage (from shell):
  blender --background --python blender_fit_armor.py -- ^
    --armature-fbx "path/to/race_or_proxy.fbx" ^
    --reference-fbx "path/to/kingdom_armor_ref.fbx" ^
    --out "Output/fbx/LHL_Darkling_Armor.fbx" ^
    --name LHL_Darkling_Armor

Notes:
  - Elemental .hkb cannot be imported directly in Blender; export/convert a
    proxy armature (or rebuild bone names to match UnitModelType) first.
  - This script binds the reference mesh to the target armature with automatic
    weights, then exports FBX for Softimage/Max/Maya → HCT Packfile → .hkb.
  - Bone names must match the race skeleton the game uses for that UnitModelType.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _argv_after_double_dash() -> list[str]:
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1 :]
    return sys.argv[1:]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Fit reference armor mesh to race armature and export FBX")
    ap.add_argument("--armature-fbx", required=True, help="FBX containing the race/target armature")
    ap.add_argument("--reference-fbx", required=True, help="FBX containing clothes/armor mesh to retarget")
    ap.add_argument("--out", required=True, help="Output FBX path")
    ap.add_argument("--name", default="LHL_FitArmor", help="Object name prefix")
    ap.add_argument("--clear", action="store_true", default=True, help="Clear scene first")
    return ap.parse_args(_argv_after_double_dash())


def main() -> int:
    import bpy  # type: ignore

    args = parse_args()
    armature_fbx = Path(args.armature_fbx)
    reference_fbx = Path(args.reference_fbx)
    out = Path(args.out)

    if not armature_fbx.is_file():
        print(f"Missing armature FBX: {armature_fbx}", file=sys.stderr)
        return 1
    if not reference_fbx.is_file():
        print(f"Missing reference FBX: {reference_fbx}", file=sys.stderr)
        return 1

    if args.clear:
        bpy.ops.wm.read_factory_settings(use_empty=True)

    # Import target armature
    bpy.ops.import_scene.fbx(filepath=str(armature_fbx))
    armatures = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    if not armatures:
        print("No armature found in --armature-fbx", file=sys.stderr)
        return 1
    target_arm = armatures[0]
    target_arm.name = f"{args.name}_Armature"

    # Import reference mesh (ignore its armature if present)
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=str(reference_fbx))
    imported = [o for o in bpy.context.scene.objects if o not in before]
    meshes = [o for o in imported if o.type == "MESH"]
    if not meshes:
        print("No mesh found in --reference-fbx", file=sys.stderr)
        return 1

    # Parent + automatic weights onto race armature
    for mesh in meshes:
        mesh.name = f"{args.name}_{mesh.name}"
        # Clear old armature modifiers
        for mod in list(mesh.modifiers):
            if mod.type == "ARMATURE":
                mesh.modifiers.remove(mod)
        mesh.parent = target_arm
        mesh.parent_type = "OBJECT"
        bpy.ops.object.select_all(action="DESELECT")
        mesh.select_set(True)
        target_arm.select_set(True)
        bpy.context.view_layer.objects.active = target_arm
        try:
            bpy.ops.object.parent_set(type="ARMATURE_AUTO")
        except Exception as exc:
            print(f"[WARN] ARMATURE_AUTO failed for {mesh.name}: {exc}")
            mod = mesh.modifiers.new(name="Armature", type="ARMATURE")
            mod.object = target_arm

    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    target_arm.select_set(True)
    for mesh in meshes:
        mesh.select_set(True)
    bpy.context.view_layer.objects.active = target_arm

    bpy.ops.export_scene.fbx(
        filepath=str(out),
        use_selection=True,
        apply_scale_options="FBX_SCALE_ALL",
        armature_nodetype="NULL",
        add_leaf_bones=False,
        bake_anim=False,
        path_mode="COPY",
        embed_textures=False,
    )
    print(f"Wrote FBX: {out}")
    print("Next: import into Softimage/Max/Maya -> HCT 7.1 -> Write to Platform -> Packfile -> .hkb")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
