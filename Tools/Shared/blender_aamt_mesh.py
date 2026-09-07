#!/usr/bin/env python3
"""
Blender script: build a skinned mesh from AAMT PBR maps and export FBX/OBJ.

Invoked by mesh_skin_export.py:
  blender --background --python blender_aamt_mesh.py -- <cfg.json>

cfg.json keys:
  name, skin_dir, maps, fbx, [obj], [sketch], shape, subdivisions,
  displace_strength, solidify_thickness, bevel_amount, apply_modifiers,
  alpha_threshold, silhouette_res

Shapes: displaced, organic, armor_panel, extruded, silhouette/sketch/cutout
  (alpha/luma cutout grid), heightmap, plus primitives.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy


def _argv_cfg() -> dict:
    argv = sys.argv
    argv = argv[argv.index("--") + 1 :] if "--" in argv else []
    if not argv:
        raise SystemExit("usage: blender --background --python blender_aamt_mesh.py -- cfg.json")
    return json.loads(Path(argv[0]).read_text(encoding="utf-8"))


def _clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def _select_only(obj: bpy.types.Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def _add_tex(nodes, links, path: Path, *, label: str, y: float, colorspace: str = "sRGB"):
    if not path or not path.exists():
        return None
    n = nodes.new("ShaderNodeTexImage")
    n.location = (-500, y)
    n.label = label
    n.image = bpy.data.images.load(str(path))
    if hasattr(n.image, "colorspace_settings"):
        n.image.colorspace_settings.name = colorspace
    return n


def build_principled_material(name: str, skin_dir: Path, maps: dict) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name + "_Mat")
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (500, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (100, 0)

    diffuse = _add_tex(nodes, links, skin_dir / maps.get("diffuse", ""), label="diffuse", y=200, colorspace="sRGB")
    if diffuse:
        links.new(diffuse.outputs["Color"], bsdf.inputs["Base Color"])

    normal = _add_tex(nodes, links, skin_dir / maps.get("normal", ""), label="normal", y=-50, colorspace="Non-Color")
    if normal:
        nmap = nodes.new("ShaderNodeNormalMap")
        nmap.location = (-150, -50)
        links.new(normal.outputs["Color"], nmap.inputs["Color"])
        links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

    rough = _add_tex(nodes, links, skin_dir / maps.get("roughness", ""), label="rough", y=-200, colorspace="Non-Color")
    if rough and "Roughness" in bsdf.inputs:
        links.new(rough.outputs["Color"], bsdf.inputs["Roughness"])

    metal = _add_tex(nodes, links, skin_dir / maps.get("metallic", ""), label="metal", y=-350, colorspace="Non-Color")
    if metal and "Metallic" in bsdf.inputs:
        links.new(metal.outputs["Color"], bsdf.inputs["Metallic"])

    emission_path = skin_dir / maps.get("emission", "")
    emission = _add_tex(nodes, links, emission_path, label="emission", y=350, colorspace="sRGB")
    surface = bsdf.outputs[0]
    if emission:
        # Soft emission mix when emission map is non-black
        em = nodes.new("ShaderNodeEmission")
        em.location = (100, 250)
        em.inputs["Strength"].default_value = 1.5
        links.new(emission.outputs["Color"], em.inputs["Color"])
        mix = nodes.new("ShaderNodeMixShader")
        mix.location = (320, 80)
        # Use emission luminance as mix factor via RGB->BW
        rgb2bw = nodes.new("ShaderNodeRGBToBW")
        rgb2bw.location = (-150, 350)
        links.new(emission.outputs["Color"], rgb2bw.inputs["Color"])
        links.new(rgb2bw.outputs["Val"], mix.inputs["Fac"])
        links.new(bsdf.outputs[0], mix.inputs[1])
        links.new(em.outputs["Emission"], mix.inputs[2])
        surface = mix.outputs["Shader"]

    links.new(surface, out.inputs["Surface"])
    return mat


def _subdivide(obj: bpy.types.Object, levels: int) -> None:
    if levels <= 0:
        return
    _select_only(obj)
    mod = obj.modifiers.new(name="AamtSubsurf", type="SUBSURF")
    mod.levels = max(1, min(levels, 4))
    mod.render_levels = mod.levels
    bpy.ops.object.modifier_apply(modifier=mod.name)


def _displace_from_image(obj: bpy.types.Object, image_path: Path, strength: float) -> None:
    if not image_path.exists() or strength == 0:
        return
    _select_only(obj)
    # Ensure UVs
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")

    tex = bpy.data.textures.new(name="AamtDisplaceTex", type="IMAGE")
    tex.image = bpy.data.images.load(str(image_path))
    mod = obj.modifiers.new(name="AamtDisplace", type="DISPLACE")
    mod.texture = tex
    mod.texture_coords = "UV"
    mod.strength = float(strength)
    mod.mid_level = 0.5
    bpy.ops.object.modifier_apply(modifier=mod.name)


def _solidify(obj: bpy.types.Object, thickness: float) -> None:
    if thickness <= 0:
        return
    _select_only(obj)
    mod = obj.modifiers.new(name="AamtSolidify", type="SOLIDIFY")
    mod.thickness = float(thickness)
    mod.offset = 0.0
    bpy.ops.object.modifier_apply(modifier=mod.name)


def _bevel(obj: bpy.types.Object, amount: float) -> None:
    if amount <= 0:
        return
    _select_only(obj)
    mod = obj.modifiers.new(name="AamtBevel", type="BEVEL")
    mod.width = float(amount)
    mod.segments = 2
    mod.limit_method = "ANGLE"
    bpy.ops.object.modifier_apply(modifier=mod.name)


def create_silhouette_mesh(
    image_path: Path,
    *,
    threshold: float = 0.12,
    max_res: int = 72,
    size: float = 2.0,
) -> bpy.types.Object:
    """
    Build a real silhouette mesh from image alpha/luma (not a fake plane extrude).
    Opaque pixels become a heightfield grid; transparent holes are omitted.
    """
    import bmesh

    if not image_path.exists():
        raise FileNotFoundError(image_path)

    img = bpy.data.images.load(str(image_path))
    w, h = img.size
    pixels = list(img.pixels)  # flat RGBA floats 0..1
    step = max(1, int(max(w, h) / max(8, max_res)))
    xs = list(range(0, w, step))
    ys = list(range(0, h, step))

    bm = bmesh.new()
    grid = {}
    for yi, y in enumerate(ys):
        for xi, x in enumerate(xs):
            i = (y * w + x) * 4
            r, g, b, a = pixels[i : i + 4]
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            if a < threshold and lum < threshold:
                continue
            vx = (x / max(1, w - 1)) * size - size * 0.5
            vy = (y / max(1, h - 1)) * size - size * 0.5
            grid[(xi, yi)] = bm.verts.new((vx, vy, 0.0))

    bm.verts.ensure_lookup_table()
    for yi in range(len(ys) - 1):
        for xi in range(len(xs) - 1):
            keys = ((xi, yi), (xi + 1, yi), (xi + 1, yi + 1), (xi, yi + 1))
            if all(k in grid for k in keys):
                try:
                    bm.faces.new([grid[k] for k in keys])
                except ValueError:
                    pass

    if not bm.faces:
        bm.free()
        # Fallback: full plane so pipeline never hard-fails on blank images
        bpy.ops.mesh.primitive_plane_add(size=size)
        obj = bpy.context.active_object
        obj.name = "AamtMesh"
        print("[WARN] silhouette empty; fell back to plane")
        return obj

    mesh = bpy.data.meshes.new("AamtSilhouette")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("AamtMesh", mesh)
    bpy.context.collection.objects.link(obj)
    _select_only(obj)
    bpy.ops.object.shade_smooth()
    print(f"[OK] silhouette mesh from {image_path.name} ({len(mesh.polygons)} faces)")
    return obj


def create_base_mesh(shape: str) -> bpy.types.Object:
    shape = (shape or "displaced").lower()
    if shape in ("cube", "box"):
        bpy.ops.mesh.primitive_cube_add(size=2)
    elif shape in ("sphere", "organic"):
        bpy.ops.mesh.primitive_ico_sphere_add(radius=1.0, subdivisions=3)
    elif shape in ("cylinder", "capsule"):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.6, depth=2.0, vertices=32)
    elif shape in ("plane", "panel", "armor", "armor_panel", "displaced", "extruded", "heightmap"):
        bpy.ops.mesh.primitive_plane_add(size=2)
    else:
        bpy.ops.mesh.primitive_plane_add(size=2)
    obj = bpy.context.active_object
    obj.name = "AamtMesh"
    return obj


def _resolve_source_image(cfg: dict, skin_dir: Path, maps: dict) -> Path | None:
    sketch = cfg.get("sketch") or cfg.get("sketch_path") or cfg.get("height_image")
    if sketch:
        p = Path(sketch)
        if p.exists():
            return p
    for key in ("height", "diffuse", "emission"):
        name = maps.get(key)
        if name:
            p = skin_dir / name
            if p.exists():
                return p
    return None


def build_mesh(cfg: dict) -> bpy.types.Object:
    shape = str(cfg.get("shape") or "displaced").lower()
    skin_dir = Path(cfg["skin_dir"])
    maps = cfg.get("maps") or {}
    source = _resolve_source_image(cfg, skin_dir, maps)

    silhouette_shapes = ("silhouette", "sketch", "cutout")
    displace_shapes = ("displaced", "organic", "armor", "armor_panel", "heightmap")
    panel_shapes = ("panel", "armor", "armor_panel", "extruded", "silhouette", "sketch", "cutout")

    subdiv = int(
        cfg.get(
            "subdivisions",
            3 if shape in displace_shapes or shape in silhouette_shapes else 1,
        )
    )
    displace = float(
        cfg.get(
            "displace_strength",
            0.35 if shape in displace_shapes else (0.15 if shape in silhouette_shapes else 0.0),
        )
    )
    solidify = float(
        cfg.get(
            "solidify_thickness",
            0.15 if shape in panel_shapes else 0.0,
        )
    )
    bevel = float(
        cfg.get(
            "bevel_amount",
            0.02 if shape in ("panel", "armor", "armor_panel", "cube", "silhouette", "extruded") else 0.0,
        )
    )
    threshold = float(cfg.get("alpha_threshold", 0.12))
    max_res = int(cfg.get("silhouette_res", 72))

    if shape in silhouette_shapes:
        if not source:
            raise FileNotFoundError("silhouette shape requires sketch/diffuse image")
        obj = create_silhouette_mesh(source, threshold=threshold, max_res=max_res)
        # Mild smooth + optional height displace from same image
        if subdiv > 0:
            _subdivide(obj, min(subdiv, 2))
        if displace != 0 and source:
            _displace_from_image(obj, source, displace)
    else:
        obj = create_base_mesh(shape)
        _subdivide(obj, subdiv)
        height_path = source
        if height_path and displace != 0:
            _displace_from_image(obj, height_path, displace)

    if solidify > 0:
        _solidify(obj, solidify)
    if bevel > 0:
        _bevel(obj, bevel)

    # Final UVs after deformation
    _select_only(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    try:
        bpy.ops.mesh.normals_make_consistent(inside=False)
    except Exception:
        pass
    bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")

    mat = build_principled_material(cfg["name"], skin_dir, maps)
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    return obj


def export_mesh(obj: bpy.types.Object, cfg: dict) -> None:
    _select_only(obj)
    fbx = cfg.get("fbx")
    # Pack images into .blend so ortho spritesheet export keeps PBR
    # (FBX often greys out Principled maps — same fix as CrossMod ships).
    for img in bpy.data.images:
        try:
            img.pack()
        except Exception:
            pass
    blend = cfg.get("blend")
    if not blend and fbx:
        blend = str(Path(fbx).with_suffix(".blend"))
    if blend:
        Path(blend).parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        print("[OK] exported BLEND", blend)

    if fbx:
        Path(fbx).parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.export_scene.fbx(
            filepath=str(fbx),
            use_selection=True,
            apply_scale_options="FBX_SCALE_ALL",
            mesh_smooth_type="FACE",
            path_mode="COPY",
            embed_textures=True,
        )
        print("[OK] exported FBX", fbx)

    obj_path = cfg.get("obj")
    if obj_path:
        Path(obj_path).parent.mkdir(parents=True, exist_ok=True)
        # Blender 4+/5: wm.obj_export; older: export_scene.obj
        try:
            bpy.ops.wm.obj_export(filepath=str(obj_path), export_selected_objects=True)
        except Exception:
            bpy.ops.export_scene.obj(filepath=str(obj_path), use_selection=True)
        print("[OK] exported OBJ", obj_path)


def main() -> None:
    cfg = _argv_cfg()
    _clear_scene()
    obj = build_mesh(cfg)
    export_mesh(obj, cfg)
    print("[OK] blender_aamt_mesh done")


if __name__ == "__main__":
    main()
