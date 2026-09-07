#!/usr/bin/env python3
"""
Build real CrossMod ship meshes (geometric plate style) + apply Shared PBR skins,
then export FBX — same path as vanilla Transcendence ship art (mesh → ortho facings).

NOT a sketch/2D silhouette pipeline. Skins come from pbr_skin_generator / SD.

Usage (via Blender):
  blender --background --python blender_crossmod_ship_mesh.py -- \\
    --ship-id scSpaceWhale --skin-dir .../Skins --fbx .../Meshes/scSpaceWhale.fbx
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def _clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def _select(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def _apply_mods(obj):
    _select(obj)
    for mod in list(obj.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except Exception:
            pass


def _join(parts, name):
    bpy.ops.object.select_all(action="DESELECT")
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    try:
        bpy.ops.object.shade_smooth()
    except Exception:
        pass
    return obj


def _solidify_bevel(obj, thickness=0.18, bevel=0.02):
    _select(obj)
    s = obj.modifiers.new("Solidify", "SOLIDIFY")
    s.thickness = thickness
    s.offset = 0.0
    b = obj.modifiers.new("Bevel", "BEVEL")
    b.width = bevel
    b.segments = 2
    _apply_mods(obj)


def _mesh_from_xy(name, verts_xy, z=0.0):
    """Create a flat n-gon in XY (top-down plane), later solidified for thickness."""
    mesh = bpy.data.meshes.new(name)
    verts = [(float(x), float(y), z) for x, y in verts_xy]
    faces = [list(range(len(verts)))]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def _shield_xy(cx, cy, length, width):
    """Legacy 6-pt plate (kept for callers); prefer _teardrop_xy for organics."""
    hl, hw = length * 0.5, width * 0.5
    return [
        (cx + hl * 0.95, cy),
        (cx + hl * 0.25, cy - hw),
        (cx - hl * 0.55, cy - hw * 0.85),
        (cx - hl * 0.95, cy),
        (cx - hl * 0.55, cy + hw * 0.85),
        (cx + hl * 0.25, cy + hw),
    ]


def _teardrop_xy(cx, cy, length, width, *, n: int = 28, nose_sharp: float = 0.55):
    """Dense organic body outline, nose toward +X (top-down)."""
    pts = []
    for i in range(n):
        ang = (i / n) * math.pi * 2.0 - math.pi
        u, v = math.cos(ang), math.sin(ang)
        if u > 0:
            x = cx + length * (0.06 + 0.44 * (u**nose_sharp))
            y_scale = width * (0.36 + 0.34 * (1.0 - u) ** 0.85)
        else:
            x = cx + length * (0.06 + 0.42 * u)
            y_scale = width * (0.34 + 0.22 * (1.0 + u))
        pts.append((x, cy + v * y_scale))
    return pts


def _fin_xy(sign: float, *, root_x=0.5, tip_y=2.0, sweep=-0.4, n: int = 16):
    """Smooth pectoral / fluke lobe membrane (sign = ±1)."""
    pts = []
    for i in range(n):
        t = i / (n - 1)
        x = root_x + sweep * t - 0.15 * math.sin(t * math.pi)
        y = sign * (0.25 + (tip_y - 0.25) * (t**0.85))
        pts.append((x, y))
    for i in range(n - 2, 0, -1):
        t = i / (n - 1)
        x = root_x + 0.35 + (sweep * 0.55) * t
        y = sign * (0.18 + (tip_y * 0.55) * t)
        pts.append((x, y))
    return pts


def _organicize(obj, levels: int = 2, thickness: float = 0.22, bevel: float = 0.03):
    """Solidify + bevel + subdivision so plates read as smooth organisms, not hex tiles."""
    _solidify_bevel(obj, thickness, bevel)
    _select(obj)
    sub = obj.modifiers.new("Subsurf", "SUBSURF")
    sub.levels = levels
    sub.render_levels = levels
    _apply_mods(obj)
    try:
        bpy.ops.object.shade_smooth()
    except Exception:
        pass
    return obj


def build_space_whale_head(pose: str = "idle"):
    """Concept lavender whale: smooth elongated body + starfield pectorals."""
    parts = []
    ls = 0.82 if pose == "bodyCompress" else 1.0
    ws = 1.14 if pose == "bodyCompress" else 1.0

    body = _mesh_from_xy(
        "Body",
        _teardrop_xy(-0.1, 0.0, 4.2 * ls, 1.85 * ws, n=32, nose_sharp=0.58),
    )
    _organicize(body, levels=2, thickness=0.32 if pose != "bellyGlow" else 0.42, bevel=0.04)
    parts.append(body)

    # Slightly raised carapace ridge
    ridge = _mesh_from_xy(
        "Ridge",
        _teardrop_xy(0.15, 0.0, 2.8 * ls, 0.85 * ws, n=24, nose_sharp=0.7),
    )
    _organicize(ridge, levels=2, thickness=0.18, bevel=0.02)
    parts.append(ridge)

    tip_y = 2.15 * ws if pose != "bodyCompress" else 1.85 * ws
    for sign, name in ((-1.0, "FinL"), (1.0, "FinR")):
        fin = _mesh_from_xy(name, _fin_xy(sign, root_x=0.35 * ls, tip_y=tip_y, sweep=-0.55 * ls, n=18))
        _organicize(fin, levels=2, thickness=0.07, bevel=0.015)
        parts.append(fin)

    if pose == "mawOpen":
        # Split nose with a dark notch volume (separate thinner plate)
        notch = _mesh_from_xy(
            "Maw",
            [
                (2.05 * ls, 0.12 * ws),
                (2.55 * ls, 0.35 * ws),
                (2.55 * ls, -0.35 * ws),
                (2.05 * ls, -0.12 * ws),
            ],
        )
        _organicize(notch, levels=1, thickness=0.12, bevel=0.01)
        parts.append(notch)

    obj = _join(parts, "scSpaceWhale")
    return _apply_pose_scale(obj, pose)


def build_space_whale_segment(pose: str = "idle"):
    ls = 0.85 if pose == "bodyCompress" else 1.0
    ws = 1.16 if pose == "bodyCompress" else 1.0
    plate = _mesh_from_xy(
        "Segment",
        _teardrop_xy(0.0, 0.0, 2.4 * ls, 1.55 * ws, n=28, nose_sharp=0.75),
    )
    _organicize(plate, levels=2, thickness=0.26, bevel=0.03)
    tab = _mesh_from_xy(
        "Tab",
        _teardrop_xy(0.85 * ls, 0.0, 0.9 * ls, 0.7 * ws, n=16, nose_sharp=0.9),
    )
    _organicize(tab, levels=1, thickness=0.12, bevel=0.015)
    return _apply_pose_scale(_join([plate, tab], "scSpaceWhaleSegment"), pose)


def build_space_whale_fluke(pose: str = "idle"):
    parts = []
    ls = 0.88 if pose == "bodyCompress" else 1.0
    ws = 1.12 if pose == "bodyCompress" else 1.0
    ped = _mesh_from_xy(
        "Peduncle",
        _teardrop_xy(0.55 * ls, 0.0, 1.5 * ls, 0.95 * ws, n=22, nose_sharp=0.85),
    )
    _organicize(ped, levels=2, thickness=0.2, bevel=0.025)
    parts.append(ped)
    for sign, name in ((-1.0, "FlukeL"), (1.0, "FlukeR")):
        wing = _mesh_from_xy(
            name,
            _fin_xy(sign, root_x=-0.15 * ls, tip_y=1.55 * ws, sweep=-1.35 * ls, n=18),
        )
        _organicize(wing, levels=2, thickness=0.06, bevel=0.012)
        parts.append(wing)
    return _apply_pose_scale(_join(parts, "scSpaceWhaleFluke"), pose)


def build_space_whale_drone(pose: str = "idle"):
    parts = []
    ls = 0.9 if pose == "bodyCompress" else 1.0
    ws = 1.1 if pose == "bodyCompress" else 1.0
    body = _mesh_from_xy(
        "DroneBody",
        _teardrop_xy(0.0, 0.0, 1.55 * ls, 0.95 * ws, n=22, nose_sharp=0.7),
    )
    _organicize(body, levels=2, thickness=0.16, bevel=0.02)
    parts.append(body)
    for sign, name in ((-1.0, "DFinL"), (1.0, "DFinR")):
        fin = _mesh_from_xy(
            name,
            _fin_xy(sign, root_x=0.1 * ls, tip_y=0.85 * ws, sweep=-0.25 * ls, n=12),
        )
        _organicize(fin, levels=1, thickness=0.045, bevel=0.01)
        parts.append(fin)
    return _apply_pose_scale(_join(parts, "scSpaceWhaleDrone"), pose)


def build_leviathan_base(pose: str = "idle"):
    """Nova Drift–style luminous serpent: smooth head + many round vertebrae + cyan fins."""
    parts = []
    ls = 0.85 if pose == "bodyCompress" else 1.0
    ws = 1.12 if pose == "bodyCompress" else 1.0

    if pose == "mawOpen":
        head_xy = _teardrop_xy(1.7 * ls, 0.0, 2.4 * ls, 1.35 * ws, n=26, nose_sharp=0.45)
        # Open notch by pushing side verts (approx via wider mid)
        head_xy = _teardrop_xy(1.7 * ls, 0.0, 2.5 * ls, 1.55 * ws, n=26, nose_sharp=0.4)
    else:
        head_xy = _teardrop_xy(1.7 * ls, 0.0, 2.3 * ls, 1.2 * ws, n=26, nose_sharp=0.5)
    head = _mesh_from_xy("LevHead", head_xy)
    _organicize(head, levels=2, thickness=0.28 if pose == "bellyGlow" else 0.22, bevel=0.03)
    parts.append(head)

    for sign, name in ((-1.0, "CrystalL"), (1.0, "CrystalR")):
        shard = _mesh_from_xy(
            name,
            _fin_xy(sign, root_x=0.6 * ls, tip_y=2.0 * ws, sweep=-1.1 * ls, n=14),
        )
        _organicize(shard, levels=1, thickness=0.05, bevel=0.01)
        parts.append(shard)

    n_seg = 8 if pose != "bodyCompress" else 6
    for i in range(n_seg):
        t = (i + 0.5) / n_seg
        x = 0.35 * ls - t * 3.6 * ls
        y = math.sin(t * math.pi * 1.5) * 0.28 * ws
        sc = 1.0 - t * 0.35
        plate = _mesh_from_xy(
            f"LevPlate{i}",
            _teardrop_xy(x, y, 0.85 * sc * ls, 0.62 * sc * ws, n=18, nose_sharp=0.8),
        )
        _organicize(plate, levels=1, thickness=0.14 * sc, bevel=0.015)
        parts.append(plate)
        # Lateral spikes
        for sign in (-1.0, 1.0):
            spike = _mesh_from_xy(
                f"Spike{i}_{int(sign)}",
                [
                    (x + 0.1 * sc, y + sign * 0.08 * sc),
                    (x - 0.15 * sc, y + sign * 0.12 * sc),
                    (x - 0.35 * sc, y + sign * 0.55 * sc * ws),
                ],
            )
            _organicize(spike, levels=1, thickness=0.04, bevel=0.008)
            parts.append(spike)

    return _apply_pose_scale(_join(parts, "scLeviathanBase"), pose)


def build_leviathan_segment(pose: str = "idle"):
    ls = 0.88 if pose == "bodyCompress" else 1.0
    ws = 1.15 if pose == "bodyCompress" else 1.0
    plate = _mesh_from_xy(
        "LevSeg",
        _teardrop_xy(0.0, 0.0, 1.7 * ls, 1.05 * ws, n=20, nose_sharp=0.8),
    )
    _organicize(plate, levels=2, thickness=0.18, bevel=0.025)
    parts = [plate]
    for sign in (-1.0, 1.0):
        spike = _mesh_from_xy(
            f"SegSpike_{int(sign)}",
            [
                (0.15, sign * 0.1),
                (-0.2, sign * 0.15),
                (-0.35, sign * 0.85 * ws),
            ],
        )
        _organicize(spike, levels=1, thickness=0.045, bevel=0.01)
        parts.append(spike)
    return _apply_pose_scale(_join(parts, "scLeviathanSegment"), pose)


def _apply_pose_scale(obj, pose: str):
    """bodyCompress: elongate + pinch for ram windup telegraph."""
    if pose == "bodyCompress":
        _select(obj)
        obj.scale = (1.12, 0.82, 1.05)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


BUILDERS = {
    "scSpaceWhale": build_space_whale_head,
    "scSpaceWhaleSegment": build_space_whale_segment,
    "scSpaceWhaleFluke": build_space_whale_fluke,
    "scSpaceWhaleDrone": build_space_whale_drone,
    "scLeviathanBase": build_leviathan_base,
    "scLeviathanSegment": build_leviathan_segment,
}


def _load_maps(skin_dir: Path, name: str) -> dict:
    reg = skin_dir / f"{name}_pbr.json"
    if reg.is_file():
        data = json.loads(reg.read_text(encoding="utf-8"))
        maps = data.get("maps") or {}
        if maps:
            return {k: skin_dir / v for k, v in maps.items()}
    keys = ("diffuse", "normal", "roughness", "metallic", "emission")
    return {k: skin_dir / f"{name}_{k}.png" for k in keys}


def apply_pbr_material(obj, skin_dir: Path, name: str, pose: str = "idle"):
    """Principled PBR from Shared skin maps — never Blender default grey."""
    maps = _load_maps(skin_dir, name)
    mat = bpy.data.materials.new(name=f"{name}_PBR")
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (500, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (100, 0)

    def tex(path: Path, label: str, y: float, non_color=False):
        if not path or not Path(path).is_file():
            return None
        n = nodes.new("ShaderNodeTexImage")
        n.location = (-500, y)
        n.label = label
        n.image = bpy.data.images.load(str(path))
        if non_color and hasattr(n.image, "colorspace_settings"):
            n.image.colorspace_settings.name = "Non-Color"
        return n

    diff = tex(maps.get("diffuse"), "diffuse", 200)
    if diff:
        links.new(diff.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        # Fallback tint matching reference violet (still explicit, not default grey)
        bsdf.inputs["Base Color"].default_value = (0.35, 0.18, 0.55, 1.0)

    nrm = tex(maps.get("normal"), "normal", -50, non_color=True)
    if nrm:
        nmap = nodes.new("ShaderNodeNormalMap")
        nmap.location = (-150, -50)
        links.new(nrm.outputs["Color"], nmap.inputs["Color"])
        links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

    rough = tex(maps.get("roughness"), "rough", -200, non_color=True)
    if rough and "Roughness" in bsdf.inputs:
        links.new(rough.outputs["Color"], bsdf.inputs["Roughness"])
    elif "Roughness" in bsdf.inputs:
        bsdf.inputs["Roughness"].default_value = 0.35

    metal = tex(maps.get("metallic"), "metal", -350, non_color=True)
    if metal and "Metallic" in bsdf.inputs:
        links.new(metal.outputs["Color"], bsdf.inputs["Metallic"])
    elif "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = 0.15

    em = tex(maps.get("emission"), "emission", 350)
    surface = bsdf.outputs[0]
    emit_strength = 4.5 if pose == "bellyGlow" else 2.5
    if em:
        emis = nodes.new("ShaderNodeEmission")
        emis.location = (100, 250)
        emis.inputs["Strength"].default_value = emit_strength
        links.new(em.outputs["Color"], emis.inputs["Color"])
        mix = nodes.new("ShaderNodeMixShader")
        mix.location = (320, 80)
        bw = nodes.new("ShaderNodeRGBToBW")
        bw.location = (-150, 350)
        links.new(em.outputs["Color"], bw.inputs["Color"])
        links.new(bw.outputs["Val"], mix.inputs["Fac"])
        links.new(bsdf.outputs[0], mix.inputs[1])
        links.new(emis.outputs["Emission"], mix.inputs[2])
        surface = mix.outputs["Shader"]
    elif pose == "bellyGlow":
        emis = nodes.new("ShaderNodeEmission")
        emis.location = (100, 250)
        emis.inputs["Color"].default_value = (0.75, 0.45, 1.0, 1.0)
        emis.inputs["Strength"].default_value = 3.5
        mix = nodes.new("ShaderNodeMixShader")
        mix.location = (320, 80)
        mix.inputs["Fac"].default_value = 0.45
        links.new(bsdf.outputs[0], mix.inputs[1])
        links.new(emis.outputs["Emission"], mix.inputs[2])
        surface = mix.outputs["Shader"]

    links.new(surface, out.inputs["Surface"])

    _select(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")

    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def export_fbx(obj, fbx: Path):
    fbx = Path(fbx)
    fbx.parent.mkdir(parents=True, exist_ok=True)
    # Pack images into .blend so ortho export keeps PBR (FBX often drops maps)
    for img in bpy.data.images:
        try:
            img.pack()
        except Exception:
            pass
    blend = fbx.with_suffix(".blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    print(f"[OK] BLEND {blend}")

    _select(obj)
    bpy.ops.export_scene.fbx(
        filepath=str(fbx),
        use_selection=True,
        apply_scale_options="FBX_SCALE_ALL",
        mesh_smooth_type="FACE",
        path_mode="COPY",
        embed_textures=True,
    )
    print(f"[OK] FBX {fbx}")


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--ship-id", required=True)
    ap.add_argument("--skin-dir", required=True)
    ap.add_argument("--fbx", required=True)
    ap.add_argument("--name", default="")
    ap.add_argument("--pose", default="idle", choices=("idle", "mawOpen", "bodyCompress", "bellyGlow"))
    args = ap.parse_args(argv)

    ship_id = args.ship_id
    name = args.name or ship_id
    pose = args.pose or "idle"
    builder = BUILDERS.get(ship_id)
    if not builder:
        print(f"[ERROR] Unknown ship-id {ship_id}; known: {list(BUILDERS)}")
        sys.exit(2)

    _clear()
    obj = builder(pose)
    apply_pbr_material(obj, Path(args.skin_dir), name, pose=pose)
    export_fbx(obj, Path(args.fbx))
    # Also write OBJ sibling for tooling that prefers it
    obj_path = Path(args.fbx).with_suffix(".obj")
    try:
        _select(obj)
        if hasattr(bpy.ops.wm, "obj_export"):
            bpy.ops.wm.obj_export(filepath=str(obj_path), export_selected_objects=True)
        else:
            bpy.ops.export_scene.obj(filepath=str(obj_path), use_selection=True)
        print(f"[OK] OBJ {obj_path}")
    except Exception as exc:
        print(f"[WARN] OBJ export skipped: {exc}")


if __name__ == "__main__":
    main()
