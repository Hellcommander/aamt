"""Blender side of the engine-correct Transcendence facing renderer.

Renders N top-down RGBA frames of one mesh. Frame i shows the hull turned
CLOCKWISE by i*360/N from nose-up, which is exactly what the engine expects
(CIntegralRotationDesc::InitFacingsData: frame i faces 90 - i*360/N degrees).
Sheet assembly, masks and testing happen outside Blender (tx_build_facings.py).

  blender -b -P blender_tx_facings.py -- --model hull.glb --out frames_dir
      --frames 120 --size 1024 [--nose-yaw 0] [--pose idle|bodyCompress|bellyGlow|mawOpen]
      [--fit-radius R]  (shared framing so pose sheets line up with idle)

--nose-yaw: degrees (CCW, seen from above) that turn the imported mesh so its
nose points to screen-up. Found once per mesh with --probe, stored in the
registry.
"""
import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Vector, Matrix


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", type=int, default=120)
    ap.add_argument("--size", type=int, default=1024, help="render px per frame (supersampled)")
    ap.add_argument("--nose-yaw", type=float, default=0.0)
    ap.add_argument("--pose", default="idle")
    ap.add_argument("--fit-radius", type=float, default=0.0)
    ap.add_argument("--probe", action="store_true", help="render 4 yaws (0/90/180/270) only")
    ap.add_argument("--engine", default="EEVEE", choices=["EEVEE", "CYCLES"])
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--glow", type=float, default=1.0, help="emission multiplier (bellyGlow uses more)")
    return ap.parse_args(argv)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_mesh(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path)
    else:
        raise SystemExit(f"unsupported mesh: {path}")
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        raise SystemExit("no meshes imported")
    # One pivot so every part turns together.
    pivot = bpy.data.objects.new("TX_PIVOT", None)
    bpy.context.scene.collection.objects.link(pivot)
    for o in bpy.context.scene.objects:
        if o.parent is None and o is not pivot:
            o.parent = pivot
    return pivot, meshes


def world_points(meshes, step=1):
    pts = []
    for o in meshes:
        mw = o.matrix_world
        vs = o.data.vertices
        for i in range(0, len(vs), step):
            pts.append(mw @ vs[i].co)
    return pts


def lay_flat_and_center(pivot, meshes):
    """TRELLIS/glTF meshes come Y-up; Blender's importer converts to Z-up.
    The thinnest axis becomes Z (view axis) so the top-down camera sees the
    hull's plan view."""
    bpy.context.view_layer.update()
    pts = world_points(meshes, step=max(1, sum(len(m.data.vertices) for m in meshes) // 20000))
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    span = mx - mn
    thin = min(range(3), key=lambda i: span[i])
    if thin == 0:
        pivot.rotation_euler = (0.0, math.radians(90), 0.0)
    elif thin == 1:
        pivot.rotation_euler = (math.radians(90), 0.0, 0.0)
    bpy.context.view_layer.update()
    pts = world_points(meshes, step=max(1, len(pts) // 20000 or 1))
    c = Vector((sum(p.x for p in pts) / len(pts), sum(p.y for p in pts) / len(pts), 0.0))
    zmid = (min(p.z for p in pts) + max(p.z for p in pts)) / 2
    pivot.location = pivot.location - Vector((c.x, c.y, zmid))
    bpy.context.view_layer.update()
    pts = world_points(meshes, step=max(1, len(pts) // 20000 or 1))
    # Radius in the view plane: the frame must hold every rotation without clipping.
    return max(math.hypot(p.x, p.y) for p in pts)


def apply_pose(pivot, meshes, pose, glow):
    """Poses as hull-level transforms the overlay system can show cleanly.

    bodyCompress: the ram wind-up -- hull shortens 12% along the nose axis and
                  swells 6% across it (squash before the lunge).
    bellyGlow:    metabolism -- emission x3 and a warm core light.
    mawOpen:      swallow telegraph -- front third spreads 18% sideways and
                  a bright maw light sits at the nose.
    """
    if pose == "bodyCompress":
        for o in meshes:
            o.scale = (o.scale[0] * 1.06, o.scale[1] * 0.88, o.scale[2])
    if pose in ("bellyGlow", "mawOpen") or glow != 1.0:
        mult = glow * (3.0 if pose == "bellyGlow" else 1.0)
        for o in meshes:
            for slot in o.material_slots:
                m = slot.material
                if not m or not m.use_nodes:
                    continue
                for n in m.node_tree.nodes:
                    if n.type == "BSDF_PRINCIPLED":
                        s = n.inputs.get("Emission Strength")
                        if s is not None:
                            s.default_value = max(0.6, s.default_value) * mult
    if pose == "mawOpen":
        bpy.context.view_layer.update()
        for o in meshes:
            me = o.data
            mw = o.matrix_world
            inv = mw.inverted()
            ys = [(mw @ v.co).y for v in me.vertices]
            ymax, ymin = max(ys), min(ys)
            front = ymax - (ymax - ymin) / 3
            for v, y in zip(me.vertices, ys):
                if y > front:
                    t = (y - front) / max(1e-6, ymax - front)
                    w = mw @ v.co
                    w.x *= 1.0 + 0.18 * t
                    v.co = inv @ w
    if pose in ("bellyGlow", "mawOpen"):
        ld = bpy.data.lights.new("TX_CORE", "POINT")
        ld.energy = 900.0 if pose == "bellyGlow" else 600.0
        ld.color = (1.0, 0.75, 0.55) if pose == "bellyGlow" else (0.55, 0.95, 1.0)
        lo = bpy.data.objects.new("TX_CORE", ld)
        bpy.context.scene.collection.objects.link(lo)
        lo.parent = pivot
        lo.location = (0.0, 0.0, 0.4) if pose == "bellyGlow" else (0.0, 1.0, 0.4)


def setup_scene(size, radius, engine, samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES" if engine == "CYCLES" else (
        "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in
        [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
        else "BLENDER_EEVEE")
    if sc.render.engine == "CYCLES":
        sc.cycles.samples = samples
        sc.cycles.use_denoising = True
    else:
        for attr in ("taa_render_samples",):
            if hasattr(sc.eevee, attr):
                setattr(sc.eevee, attr, samples)
    sc.render.resolution_x = sc.render.resolution_y = size
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"

    cam_d = bpy.data.cameras.new("TX_CAM")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = radius * 2.0 * 1.04
    cam_d.clip_start, cam_d.clip_end = 0.01, max(100.0, radius * 20)
    cam = bpy.data.objects.new("TX_CAM", cam_d)
    sc.collection.objects.link(cam)
    cam.location = (0.0, 0.0, radius * 6)
    cam.rotation_euler = (0.0, 0.0, 0.0)
    sc.camera = cam

    # Vanilla-style lighting: key from upper-left (screen), soft fill, rim.
    def sun(name, energy, rot, color=(1, 1, 1)):
        d = bpy.data.lights.new(name, "SUN")
        d.energy, d.color = energy, color
        if hasattr(d, "angle"):
            d.angle = math.radians(4)
        o = bpy.data.objects.new(name, d)
        sc.collection.objects.link(o)
        o.rotation_euler = rot
    sun("KEY", 3.2, (math.radians(35), math.radians(-30), 0))
    sun("FILL", 0.9, (math.radians(-40), math.radians(35), 0), (0.75, 0.85, 1.0))
    sun("TOP", 0.8, (0, 0, 0))
    w = bpy.data.worlds.new("TX_W")
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.02, 0.02, 0.03, 1)
        bg.inputs[1].default_value = 0.6
    sc.world = w


def main():
    a = args()
    reset()
    pivot, meshes = import_mesh(a.model)
    radius = lay_flat_and_center(pivot, meshes)
    apply_pose(pivot, meshes, a.pose, a.glow)
    fit = a.fit_radius if a.fit_radius > 0 else radius
    setup_scene(a.size, fit, a.engine, a.samples)
    os.makedirs(a.out, exist_ok=True)
    base = pivot.rotation_euler.copy()

    # Spin around the world Z axis, applied after the lay-flat rotation.
    flat = pivot.matrix_world.copy()
    yaws = [0, 90, 180, 270] if a.probe else [i * 360.0 / a.frames for i in range(a.frames)]
    for i, cw in enumerate(yaws):
        ang = math.radians(a.nose_yaw - cw)  # clockwise on screen = negative Z
        pivot.matrix_world = Matrix.Rotation(ang, 4, "Z") @ flat
        bpy.context.scene.render.filepath = os.path.join(a.out, f"f{i:03d}.png")
        bpy.ops.render.render(write_still=True)
    pivot.rotation_euler = base
    with open(os.path.join(a.out, "render.json"), "w") as fh:
        json.dump({"model": a.model, "frames": len(yaws), "size": a.size, "noseYaw": a.nose_yaw,
                   "pose": a.pose, "radius": radius, "fitRadius": fit, "probe": a.probe}, fh, indent=2)
    print(f"TX_FACINGS_DONE radius={radius:.4f} fit={fit:.4f}")


main()
