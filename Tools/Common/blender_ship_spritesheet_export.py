#!/usr/bin/env python3
"""
Blender Script: Export Ship Model as Transcendence Rotation Spritesheet

Matches vanilla HD ship art conventions (EarthSlaverHD / Centurion-class quality bar):
  - True top-down orthographic camera
  - 120 facings, 12 columns
  - Full-sheet JPG + full-sheet Mask.bmp (white ship / black void)
  - 2× supersample then downscale for crisp edges
  - Studio lighting tuned for metallic hull readability

Usage:
    blender --background --python blender_ship_spritesheet_export.py -- \\
        --model ship.fbx --output ship.jpg --facings 120 --columns 12 --rows 10 \\
        --frame-width 128 --frame-height 128 --game-format Transcendence --generate-mask
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from math import radians

import bpy


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for material in list(bpy.data.materials):
        bpy.data.materials.remove(material)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    for img in list(bpy.data.images):
        if img.name.startswith("_AAMT_"):
            bpy.data.images.remove(img)


def _remove_lights():
    for obj in list(bpy.data.objects):
        if obj.type == "LIGHT":
            bpy.data.objects.remove(obj, do_unlink=True)


def setup_camera(_frame_width=None, _frame_height=None):
    """Top-down orthographic camera (Transcendence ship facing convention)."""
    if bpy.context.scene.camera:
        bpy.data.objects.remove(bpy.context.scene.camera, do_unlink=True)

    bpy.ops.object.camera_add(location=(0.0, 0.0, 12.0))
    camera = bpy.context.active_object
    camera.name = "SpritesheetCamera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 5.0
    # Identity rotation: camera looks down -Z → top-down on XY plane
    camera.rotation_euler = (0.0, 0.0, 0.0)
    camera.data.clip_start = 0.01
    camera.data.clip_end = 1000.0
    bpy.context.scene.camera = camera
    return camera


def setup_lighting():
    """Studio key/fill/rim for readable metallic hulls on black void."""
    _remove_lights()
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("AAMTWorld")
        bpy.context.scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    bg = nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    bg.inputs["Strength"].default_value = 0.0
    out = nodes.new("ShaderNodeOutputWorld")
    links.new(bg.outputs["Background"], out.inputs["Surface"])

    def add_sun(name, energy, rot, loc):
        bpy.ops.object.light_add(type="SUN", location=loc)
        light = bpy.context.active_object
        light.name = name
        light.data.energy = energy
        light.rotation_euler = rot
        if hasattr(light.data, "angle"):
            light.data.angle = radians(2.5)
        return light

    # Key from upper-forward (nose lighting)
    add_sun("KeyLight", 4.2, (radians(45), radians(15), radians(25)), (4, -3, 10))
    # Soft fill opposite
    add_sun("FillLight", 1.4, (radians(55), radians(-25), radians(-40)), (-5, 2, 8))
    # Rim for silhouette edge against black
    add_sun("RimLight", 2.0, (radians(25), radians(180), radians(10)), (0, 6, 6))


def setup_render_settings(frame_width, frame_height, output_format="PNG", game_format="Transcendence"):
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        try:
            scene.render.engine = "BLENDER_EEVEE"
        except Exception:
            scene.render.engine = "CYCLES"

    scene.render.resolution_x = int(frame_width)
    scene.render.resolution_y = int(frame_height)
    scene.render.resolution_percentage = 100
    scene.render.use_border = False
    scene.render.film_transparent = True

    # Anti-aliasing / filter
    if hasattr(scene.render, "filter_size"):
        scene.render.filter_size = 1.5
    if hasattr(scene.render, "use_high_quality_normals"):
        scene.render.use_high_quality_normals = True

    engine = scene.render.engine
    if engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        eevee = getattr(scene, "eevee", None)
        if eevee:
            for attr, val in (
                ("taa_render_samples", 64),
                ("taa_samples", 64),
                ("use_raytracing", True),
                ("use_shadows", True),
                ("use_bloom", False),
            ):
                if hasattr(eevee, attr):
                    try:
                        setattr(eevee, attr, val)
                    except Exception:
                        pass
    elif engine == "CYCLES":
        scene.cycles.samples = 64
        scene.cycles.use_denoising = True

    # Intermediate frames always PNG/RGBA; final sheet converts
    if game_format == "Transcendence" and output_format.upper() in ("JPG", "JPEG"):
        # Still render intermediates as PNG for mask accuracy
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGBA"
        scene.render.film_transparent = True
    elif output_format.upper() == "PNG" or game_format in ("Terraria", "Starbound"):
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGBA"
        scene.render.film_transparent = True
    else:
        scene.render.image_settings.file_format = output_format
        scene.render.image_settings.color_mode = "RGBA"
        scene.render.film_transparent = True


def ensure_ship_material(objects):
    """Guarantee a readable metallic Principled material if FBX lost mats."""
    for obj in objects:
        if obj.type != "MESH":
            continue
        if obj.data.materials and any(obj.data.materials):
            # Boost metallic/specular slightly for top-down readability
            for mat in obj.data.materials:
                if not mat or not mat.use_nodes:
                    continue
                for node in mat.node_tree.nodes:
                    if node.type == "BSDF_PRINCIPLED":
                        if "Metallic" in node.inputs and node.inputs["Metallic"].default_value < 0.35:
                            node.inputs["Metallic"].default_value = 0.55
                        if "Roughness" in node.inputs and node.inputs["Roughness"].default_value > 0.55:
                            node.inputs["Roughness"].default_value = 0.38
            continue
        mat = bpy.data.materials.new(name=f"{obj.name}_AAMTShip")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.22, 0.25, 0.30, 1.0)
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = 0.7
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.35
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = 0.55
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)


def load_ship_model(model_path):
    if not os.path.exists(model_path):
        print(f"Error: Model file not found: {model_path}")
        return None

    file_ext = os.path.splitext(model_path)[1].lower()
    try:
        if file_ext == ".blend":
            with bpy.data.libraries.load(model_path) as (data_from, data_to):
                data_to.objects = data_from.objects
            for obj in data_to.objects:
                if obj is not None:
                    bpy.context.collection.objects.link(obj)
            bpy.ops.object.select_all(action="SELECT")
            return list(bpy.context.selected_objects)

        if file_ext == ".obj":
            bpy.ops.wm.obj_import(filepath=model_path) if hasattr(bpy.ops.wm, "obj_import") else bpy.ops.import_scene.obj(filepath=model_path)
        elif file_ext == ".fbx":
            bpy.ops.import_scene.fbx(filepath=model_path)
        elif file_ext in (".glb", ".gltf"):
            bpy.ops.import_scene.gltf(filepath=model_path)
        elif file_ext == ".dae":
            bpy.ops.wm.collada_import(filepath=model_path)
        elif file_ext == ".3ds":
            bpy.ops.import_scene.autodesk_3ds(filepath=model_path)
        else:
            print(f"Error: Unsupported file format: {file_ext}")
            return None

        bpy.ops.object.select_all(action="SELECT")
        return [o for o in bpy.context.selected_objects if o.type == "MESH"] or list(bpy.context.selected_objects)
    except Exception as exc:
        print(f"Error loading model: {exc}")
        return None


def center_ship_objects(objects):
    """Center hull at origin and fit top-down ortho framing with padding."""
    if not objects:
        return

    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="MEDIAN")
    bpy.ops.object.location_clear()

    # Lay flat in XY if mesh is predominantly vertical (from armor_panel)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if meshes:
        from mathutils import Vector

        min_v = Vector((1e9, 1e9, 1e9))
        max_v = Vector((-1e9, -1e9, -1e9))
        for obj in meshes:
            for corner in obj.bound_box:
                world = obj.matrix_world @ Vector(corner)
                min_v.x = min(min_v.x, world.x)
                min_v.y = min(min_v.y, world.y)
                min_v.z = min(min_v.z, world.z)
                max_v.x = max(max_v.x, world.x)
                max_v.y = max(max_v.y, world.y)
                max_v.z = max(max_v.z, world.z)
        span = Vector((max_v.x - min_v.x, max_v.y - min_v.y, max_v.z - min_v.z))
        # If thickness in Z is the largest axis, rotate to flat top-down
        if span.z >= span.x and span.z >= span.y and span.z > 0.01:
            for obj in meshes:
                obj.rotation_euler = (radians(-90), 0.0, 0.0)
            bpy.context.view_layer.update()
            min_v = Vector((1e9, 1e9, 1e9))
            max_v = Vector((-1e9, -1e9, -1e9))
            for obj in meshes:
                for corner in obj.bound_box:
                    world = obj.matrix_world @ Vector(corner)
                    min_v.x = min(min_v.x, world.x)
                    min_v.y = min(min_v.y, world.y)
                    min_v.z = min(min_v.z, world.z)
                    max_v.x = max(max_v.x, world.x)
                    max_v.y = max(max_v.y, world.y)
                    max_v.z = max(max_v.z, world.z)

        # Re-center after possible rotate
        mid = (min_v + max_v) * 0.5
        for obj in meshes:
            obj.location -= mid
        bpy.context.view_layer.update()

        span_x = max_v.x - min_v.x
        span_y = max_v.y - min_v.y
        span_xy = max(span_x, span_y, 0.5)
        if bpy.context.scene.camera:
            # ~12% padding — vanilla ships fill most of the cell without clipping
            bpy.context.scene.camera.data.ortho_scale = span_xy * 1.18


def render_rotation_frame(angle, output_path):
    ship_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    for obj in ship_objects:
        # Keep base XY orientation; spin around world Z for turntable
        base = getattr(obj, "_aamt_base_rot", None)
        if base is None:
            obj["_aamt_base_rot"] = tuple(obj.rotation_euler)
            base = obj["_aamt_base_rot"]
        obj.rotation_euler = (base[0], base[1], base[2] + radians(angle))
    bpy.context.view_layer.update()
    bpy.context.scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)
    return output_path


def _load_bpy_image(path):
    name = os.path.basename(path)
    if name in bpy.data.images:
        img = bpy.data.images[name]
        img.filepath = path
        img.reload()
        return img
    return bpy.data.images.load(path, check_existing=True)


def _frame_pixels_rgba(img, width, height, *, flip_y=True):
    """RGBA floats; flip_y converts Blender bottom-left to top-left."""
    px = list(img.pixels)
    channels = img.channels
    needed = width * height * channels
    if len(px) < needed:
        return [0.0] * (width * height * 4)
    out = [0.0] * (width * height * 4)
    for y in range(height):
        src_y = (height - 1 - y) if flip_y else y
        for x in range(width):
            si = (src_y * width + x) * channels
            di = (y * width + x) * 4
            if channels >= 4:
                out[di : di + 4] = px[si : si + 4]
            elif channels == 3:
                out[di] = px[si]
                out[di + 1] = px[si + 1]
                out[di + 2] = px[si + 2]
                out[di + 3] = 1.0
            else:
                v = px[si]
                out[di : di + 4] = [v, v, v, 1.0]
    return out


def _downscale_rgba(src, sw, sh, dw, dh):
    """Box-filter downsample (supersample → final frame size)."""
    if sw == dw and sh == dh:
        return src
    out = [0.0] * (dw * dh * 4)
    x_ratio = sw / float(dw)
    y_ratio = sh / float(dh)
    for y in range(dh):
        for x in range(dw):
            x0 = int(x * x_ratio)
            y0 = int(y * y_ratio)
            x1 = min(sw, int((x + 1) * x_ratio))
            y1 = min(sh, int((y + 1) * y_ratio))
            if x1 <= x0:
                x1 = min(sw, x0 + 1)
            if y1 <= y0:
                y1 = min(sh, y0 + 1)
            acc = [0.0, 0.0, 0.0, 0.0]
            count = 0
            for yy in range(y0, y1):
                for xx in range(x0, x1):
                    i = (yy * sw + xx) * 4
                    for c in range(4):
                        acc[c] += src[i + c]
                    count += 1
            di = (y * dw + x) * 4
            if count:
                out[di : di + 4] = [v / count for v in acc]
    return out


def _blit_rgba(sheet, sheet_w, sheet_h, frame, frame_w, frame_h, dst_x, dst_y):
    for fy in range(frame_h):
        for fx in range(frame_w):
            si = ((dst_y + fy) * sheet_w + (dst_x + fx)) * 4
            fi = (fy * frame_w + fx) * 4
            a = frame[fi + 3]
            if a <= 0.001:
                continue
            if a >= 0.999:
                sheet[si : si + 4] = frame[fi : fi + 4]
            else:
                for c in range(3):
                    sheet[si + c] = frame[fi + c] * a + sheet[si + c] * (1.0 - a)
                sheet[si + 3] = min(1.0, sheet[si + 3] + a)


def _contrast_boost(pixels, amount=1.12):
    """Mild contrast toward mid-gray for punchier JPG on black."""
    out = list(pixels)
    for i in range(0, len(out), 4):
        a = out[i + 3]
        if a <= 0.001:
            continue
        for c in range(3):
            v = out[i + c]
            out[i + c] = max(0.0, min(1.0, (v - 0.5) * amount + 0.5))
    return out


def _save_bpy_image(path, pixels, width, height, file_format):
    name = "_AAMT_SheetTmp"
    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])
    img = bpy.data.images.new(name, width, height, alpha=True)
    # Blender expects bottom-left; our buffers are top-left — flip on write
    flipped = [0.0] * len(pixels)
    for y in range(height):
        src_y = height - 1 - y
        for x in range(width):
            si = (src_y * width + x) * 4
            di = (y * width + x) * 4
            flipped[di : di + 4] = pixels[si : si + 4]
    img.pixels = flipped
    img.file_format = file_format
    if file_format == "JPEG":
        img.filepath_raw = path
        try:
            bpy.context.scene.render.image_settings.quality = 100
        except Exception:
            pass
    img.filepath_raw = path
    img.save()
    bpy.data.images.remove(img)


def create_spritesheet(
    facings,
    columns,
    rows,
    frame_width,
    frame_height,
    output_path,
    output_format="PNG",
    game_format="Transcendence",
    generate_mask=False,
    supersample=2,
):
    """Render N facings with supersampling; emit JPG + full-sheet Mask.bmp."""
    ss = max(1, int(supersample))
    render_w = frame_width * ss
    render_h = frame_height * ss
    spritesheet_width = columns * frame_width
    spritesheet_height = rows * frame_height
    sheet_pixels = [0.0] * (spritesheet_width * spritesheet_height * 4)
    mask_pixels = [0.0] * (spritesheet_width * spritesheet_height * 4)

    temp_dir = tempfile.mkdtemp()
    setup_render_settings(render_w, render_h, "PNG", "Starbound")
    try:
        for frame_index in range(facings):
            angle = (360.0 / facings) * frame_index
            col = frame_index % columns
            row = frame_index // columns
            frame_path = os.path.join(temp_dir, f"frame_{frame_index:03d}.png")
            render_rotation_frame(angle, frame_path)

            frame_img = _load_bpy_image(frame_path)
            hi = _frame_pixels_rgba(frame_img, render_w, render_h, flip_y=True)
            frame_px = _downscale_rgba(hi, render_w, render_h, frame_width, frame_height)
            frame_px = _contrast_boost(frame_px, 1.10)

            _blit_rgba(
                sheet_pixels,
                spritesheet_width,
                spritesheet_height,
                frame_px,
                frame_width,
                frame_height,
                col * frame_width,
                row * frame_height,
            )
            # Full-sheet mask (white where ship alpha > threshold)
            for fy in range(frame_height):
                for fx in range(frame_width):
                    fi = (fy * frame_width + fx) * 4
                    a = frame_px[fi + 3]
                    lum = frame_px[fi] + frame_px[fi + 1] + frame_px[fi + 2]
                    on = 1.0 if (a > 0.08 or lum > 0.12) else 0.0
                    mi = ((row * frame_height + fy) * spritesheet_width + (col * frame_width + fx)) * 4
                    mask_pixels[mi : mi + 4] = [on, on, on, 1.0]

            print(f"Rendered frame {frame_index + 1}/{facings} (angle: {angle:.1f}°)")

        save_format = "JPEG" if game_format == "Transcendence" else output_format
        if save_format == "JPEG":
            rgb_pixels = []
            for i in range(0, len(sheet_pixels), 4):
                a = sheet_pixels[i + 3]
                rgb_pixels.extend(
                    [
                        sheet_pixels[i] * a,
                        sheet_pixels[i + 1] * a,
                        sheet_pixels[i + 2] * a,
                        1.0,
                    ]
                )
            _save_bpy_image(output_path, rgb_pixels, spritesheet_width, spritesheet_height, "JPEG")
        else:
            _save_bpy_image(output_path, sheet_pixels, spritesheet_width, spritesheet_height, "PNG")

        print(f"Spritesheet saved: {output_path} (format: {save_format})")

        if game_format == "Transcendence" or generate_mask:
            mask_path = output_path.replace(".jpg", "Mask.bmp").replace(".png", "Mask.bmp")
            _save_bpy_image(mask_path, mask_pixels, spritesheet_width, spritesheet_height, "BMP")
            print(f"Spritesheet mask saved: {mask_path} ({spritesheet_width}x{spritesheet_height})")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return output_path


def main():
    argv = sys.argv
    argv = [] if "--" not in argv else argv[argv.index("--") + 1 :]

    parser = argparse.ArgumentParser(description="Export ship model as Transcendence rotation spritesheet")
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--facings", type=int, default=120)
    parser.add_argument("--columns", type=int, default=12)
    parser.add_argument("--rows", type=int, default=10)
    parser.add_argument("--frame-width", type=int, default=128)
    parser.add_argument("--frame-height", type=int, default=128)
    parser.add_argument("--output-format", choices=["PNG", "JPG", "BMP"], default="JPG")
    parser.add_argument("--game-format", choices=["Transcendence", "Terraria", "Starbound", "Generic"], default="Transcendence")
    parser.add_argument("--hero-image")
    parser.add_argument("--hero-width", type=int, default=320)
    parser.add_argument("--hero-height", type=int, default=320)
    parser.add_argument("--generate-mask", action="store_true")
    parser.add_argument("--supersample", type=int, default=2, help="Render scale factor before downscale (2=HD, 4=ultra)")
    parser.add_argument(
        "--save-blend",
        default="",
        help="Write the imported/centered scene to this .blend before rendering facings",
    )
    args = parser.parse_args(argv)

    if args.facings != args.columns * args.rows:
        print(
            f"Warning: facings ({args.facings}) != columns×rows "
            f"({args.columns}×{args.rows}={args.columns * args.rows})"
        )

    print("=" * 60)
    print("Blender Ship Spritesheet Exporter (HD / Transcendence)")
    print("=" * 60)
    print(f"Model: {args.model}")
    print(f"Output: {args.output}")
    print(f"Facings: {args.facings} | Grid: {args.columns}×{args.rows}")
    print(f"Frame: {args.frame_width}×{args.frame_height} | SS×{args.supersample}")
    print("=" * 60)

    clear_scene()
    setup_render_settings(args.frame_width, args.frame_height, args.output_format, args.game_format)
    setup_camera()
    setup_lighting()

    print(f"Loading model: {args.model}")
    ship_objects = load_ship_model(args.model)
    if not ship_objects:
        print("Error: Failed to load ship model")
        return 1

    ensure_ship_material(ship_objects)
    center_ship_objects(ship_objects)
    # Snapshot base rotations after lay-flat/center
    for obj in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
        obj["_aamt_base_rot"] = tuple(obj.rotation_euler)

    if args.save_blend:
        blend_path = os.path.abspath(args.save_blend)
        os.makedirs(os.path.dirname(blend_path) or ".", exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
        print(f"Backup blend saved: {blend_path}")

    print("Creating spritesheet...")
    create_spritesheet(
        args.facings,
        args.columns,
        args.rows,
        args.frame_width,
        args.frame_height,
        args.output,
        args.output_format,
        args.game_format,
        args.generate_mask,
        supersample=args.supersample,
    )

    if args.hero_image:
        try:
            print("Generating hero image...")
            ss = max(1, int(args.supersample))
            hw, hh = args.hero_width * ss, args.hero_height * ss
            setup_render_settings(hw, hh, "PNG", "Starbound")
            setup_camera()
            # Re-fit camera for hero (same hull)
            center_ship_objects([o for o in bpy.context.scene.objects if o.type == "MESH"])
            for obj in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
                base = getattr(obj, "_aamt_base_rot", tuple(obj.rotation_euler))
                obj.rotation_euler = (base[0], base[1], base[2])
            bpy.context.view_layer.update()
            temp_hero = args.hero_image.replace(".jpg", "_temp.png").replace(".png", "_temp.png")
            bpy.context.scene.render.filepath = temp_hero
            bpy.ops.render.render(write_still=True)
            hero_img = _load_bpy_image(temp_hero)
            hi = _frame_pixels_rgba(hero_img, hw, hh, flip_y=True)
            hero_px = _downscale_rgba(hi, hw, hh, args.hero_width, args.hero_height)
            hero_px = _contrast_boost(hero_px, 1.10)
            rgb = []
            mask = []
            for i in range(0, len(hero_px), 4):
                a = hero_px[i + 3]
                rgb.extend([hero_px[i] * a, hero_px[i + 1] * a, hero_px[i + 2] * a, 1.0])
                on = 1.0 if (a > 0.08) else 0.0
                mask.extend([on, on, on, 1.0])
            _save_bpy_image(args.hero_image, rgb, args.hero_width, args.hero_height, "JPEG")
            hero_mask = args.hero_image.replace(".jpg", "Mask.bmp").replace(".png", "Mask.bmp")
            _save_bpy_image(hero_mask, mask, args.hero_width, args.hero_height, "BMP")
            if os.path.exists(temp_hero):
                os.remove(temp_hero)
            print(f"Hero image saved: {args.hero_image}")
        except Exception as exc:
            print(f"Warning: hero image export failed (spritesheet OK): {exc}")

    print("Done!")
    return 0 if os.path.exists(args.output) else 1


if __name__ == "__main__":
    sys.exit(main())
