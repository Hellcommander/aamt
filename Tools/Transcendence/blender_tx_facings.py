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
    ap.add_argument("--orient", default="bbox", choices=["bbox", "pca"],
                    help="bbox: thinnest bounding-box axis is the view axis (axis-aligned meshes). "
                         "pca: principal axes (image-to-3D meshes come out tilted; the bounding box then lies)")
    ap.add_argument("--flip", action="store_true", help="pca: look at the other side of the hull")
    ap.add_argument("--view-axis", type=int, default=0, choices=[0, 1, 2],
                    help="pca: which principal axis the camera looks along (0 = flattest, 1 = middle, 2 = longest). "
                         "A fish is flattest sideways, so its back view is axis 1.")
    ap.add_argument("--skin", default="own", choices=["own", "biometal"],
                    help="own: the mesh's own texture. biometal: procedural living-metal dermis (plates on ridges, "
                         "dark creases, glowing seams) for clay sculpts that have no colour of their own")
    ap.add_argument("--deep-glow", type=float, default=1.0,
                    help="biometal: how strongly broad hollows glow (1 = like seams; lower when a big concave "
                         "area turns into a solid glowing patch)")
    ap.add_argument("--palette", default="#4a5a6a,#c8d4e0,#0a3a44,#40e0ff",
                    help="biometal: plate, highlight, crease, glow")
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


def hex_rgb(h):
    h = h.strip().lstrip("#")
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple((v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4) for v in c) + (1.0,)   # sRGB -> linear


def cavity_attribute(meshes, name="tx_cavity"):
    """Per-vertex concavity as a float attribute: 0 = ridge, 0.5 = flat, 1 = crease.
    Clay sculpts carry their design in the surface, not in colour; this is what lets a shader put plates on the
    raised parts and glow in the grooves."""
    import bmesh
    import numpy as np
    for o in meshes:
        me = o.data
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)     # glTF splits vertices at UV seams
        bm.normal_update()
        bm.to_mesh(me)
        bm.free()
        nv, ne = len(me.vertices), len(me.edges)
        co = np.empty(nv * 3, dtype=np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(nv, 3)
        no = np.empty(nv * 3, dtype=np.float32)
        me.vertices.foreach_get("normal", no)
        no = no.reshape(nv, 3)
        ev = np.empty(ne * 2, dtype=np.int32)
        me.edges.foreach_get("vertices", ev)
        ev = ev.reshape(ne, 2)
        a, b = ev[:, 0], ev[:, 1]
        d = co[b] - co[a]
        d /= (np.linalg.norm(d, axis=1)[:, None] + 1e-12)
        acc = np.zeros(nv)
        cnt = np.zeros(nv)
        np.add.at(acc, a, np.einsum("ij,ij->i", no[a], d))      # neighbour above the tangent plane = concave
        np.add.at(acc, b, np.einsum("ij,ij->i", no[b], -d))
        np.add.at(cnt, a, 1)
        np.add.at(cnt, b, 1)
        cnt = np.maximum(cnt, 1)
        cav = acc / cnt
        for _ in range(2):
            s = np.zeros(nv)
            np.add.at(s, a, cav[b])
            np.add.at(s, b, cav[a])
            cav = 0.5 * cav + 0.5 * s / cnt
        val = np.clip(0.5 + cav / (4.0 * (cav.std() + 1e-9)), 0.0, 1.0).astype(np.float32)
        attr = me.attributes.get(name) or me.attributes.new(name, "FLOAT", "POINT")
        attr.data.foreach_set("value", val)
        me.update()


def apply_biometal(meshes, palette, deep_glow=1.0):
    """Living-metal dermis for clay sculpts: slate plates, pale ridges, dark creases, glowing seams."""
    plate, light, crease, glow = [hex_rgb(c) for c in palette.split(",")]
    cavity_attribute(meshes)
    m = bpy.data.materials.new("TX_BIOMETAL")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N = nt.nodes.new
    out = N("ShaderNodeOutputMaterial")
    bsdf = N("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    cav = N("ShaderNodeAttribute")
    cav.attribute_name = "tx_cavity"
    tc = N("ShaderNodeTexCoord")

    # plate network: cells = plates, cell borders = seams
    vor = N("ShaderNodeTexVoronoi")
    vor.voronoi_dimensions = "3D"
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = 9.0
    nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
    seam = N("ShaderNodeMapRange")                      # 1 on a seam, 0 inside a plate
    seam.inputs["From Min"].default_value = 0.0
    seam.inputs["From Max"].default_value = 0.035
    seam.inputs["To Min"].default_value = 1.0
    seam.inputs["To Max"].default_value = 0.0
    nt.links.new(vor.outputs["Distance"], seam.inputs["Value"])

    noise = N("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.0
    noise.inputs["Detail"].default_value = 6.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])

    # colour by surface shape: ridge -> highlight, flat -> plate, crease -> dark
    ramp = N("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.22, light
    cr.elements[1].position, cr.elements[1].color = 0.50, plate
    e = cr.elements.new(0.72)
    e.color = crease
    nt.links.new(cav.outputs["Fac"], ramp.inputs["Fac"])
    patina = N("ShaderNodeMixRGB")                      # large soft variation so the hull is not one flat tone
    patina.blend_type = "MULTIPLY"
    patina.inputs["Color2"].default_value = (0.72, 0.78, 0.84, 1.0)
    nt.links.new(noise.outputs["Fac"], patina.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], patina.inputs["Color1"])
    seamdark = N("ShaderNodeMixRGB")
    seamdark.blend_type = "MIX"
    seamdark.inputs["Color2"].default_value = crease
    nt.links.new(seam.outputs["Result"], seamdark.inputs["Fac"])
    nt.links.new(patina.outputs["Color"], seamdark.inputs["Color1"])
    nt.links.new(seamdark.outputs["Color"], bsdf.inputs["Base Color"])

    # glow: deep creases, plus the seams where they run through low ground
    deep = N("ShaderNodeMapRange")
    deep.inputs["From Min"].default_value = 0.62
    deep.inputs["From Max"].default_value = 0.85
    nt.links.new(cav.outputs["Fac"], deep.inputs["Value"])
    low = N("ShaderNodeMapRange")
    low.inputs["From Min"].default_value = 0.45
    low.inputs["From Max"].default_value = 0.60
    nt.links.new(cav.outputs["Fac"], low.inputs["Value"])
    seamglow = N("ShaderNodeMath")
    seamglow.operation = "MULTIPLY"
    nt.links.new(seam.outputs["Result"], seamglow.inputs[0])
    nt.links.new(low.outputs["Result"], seamglow.inputs[1])
    deepk = N("ShaderNodeMath")
    deepk.operation = "MULTIPLY"
    deepk.inputs[1].default_value = deep_glow
    nt.links.new(deep.outputs["Result"], deepk.inputs[0])
    gl = N("ShaderNodeMath")
    gl.operation = "MAXIMUM"
    nt.links.new(deepk.outputs["Value"], gl.inputs[0])
    nt.links.new(seamglow.outputs["Value"], gl.inputs[1])
    ec = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
    ec.default_value = glow
    es = N("ShaderNodeMath")
    es.operation = "MULTIPLY"
    es.inputs[1].default_value = 3.0
    nt.links.new(gl.outputs["Value"], es.inputs[0])
    nt.links.new(es.outputs["Value"], bsdf.inputs["Emission Strength"])

    bsdf.inputs["Metallic"].default_value = 0.55
    rough = N("ShaderNodeMapRange")
    rough.inputs["To Min"].default_value = 0.28
    rough.inputs["To Max"].default_value = 0.55
    nt.links.new(noise.outputs["Fac"], rough.inputs["Value"])
    nt.links.new(rough.outputs["Result"], bsdf.inputs["Roughness"])
    bump = N("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.01
    nt.links.new(vor.outputs["Distance"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    for o in meshes:
        o.data.materials.clear()
        o.data.materials.append(m)
        for p in o.data.polygons:
            p.use_smooth = True


def orient_pca(pivot, meshes, flip, view_axis=0):
    """Rotate so the hull's flattest direction is the view axis (Z) and its longest is Y.
    Image-to-3D meshes (TRELLIS) are tilted in their box, so the bounding-box test picks a slanted view."""
    import numpy as np
    bpy.context.view_layer.update()
    pts = world_points(meshes, step=max(1, sum(len(m.data.vertices) for m in meshes) // 40000))
    arr = np.array([[p.x, p.y, p.z] for p in pts])
    arr = arr - arr.mean(axis=0)
    w, v = np.linalg.eigh(np.cov(arr.T))        # ascending eigenvalues
    zi = view_axis
    yi = 2 if zi != 2 else 1                    # the longest axis that is left points up the screen
    z = v[:, zi]
    y = v[:, yi]
    x = np.cross(y, z)
    if flip:
        z, x = -z, -x
    m = Matrix(((x[0], x[1], x[2]), (y[0], y[1], y[2]), (z[0], z[1], z[2])))   # rows: new axes in old coords
    pivot.matrix_world = m.to_4x4() @ pivot.matrix_world
    bpy.context.view_layer.update()


def lay_flat_and_center(pivot, meshes, orient="bbox", flip=False, view_axis=0):
    """TRELLIS/glTF meshes come Y-up; Blender's importer converts to Z-up.
    The thinnest axis becomes Z (view axis) so the top-down camera sees the
    hull's plan view."""
    bpy.context.view_layer.update()
    pts = world_points(meshes, step=max(1, sum(len(m.data.vertices) for m in meshes) // 20000))
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    span = mx - mn
    thin = min(range(3), key=lambda i: span[i])
    if orient == "pca":
        orient_pca(pivot, meshes, flip, view_axis)
    elif thin == 0:
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
    # main() has already turned the nose to world +Y, so every pose works in world space along the real
    # nose axis (the mesh's own axes are arbitrary for image-to-3D models).
    if pose == "bodyCompress":
        pivot.matrix_world = Matrix.Diagonal((1.06, 0.88, 1.0, 1.0)) @ pivot.matrix_world
        bpy.context.view_layer.update()
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
                        ec = n.inputs.get("Emission Color") or n.inputs.get("Emission")
                        if s is None:
                            continue
                        if ec is not None and ec.is_linked:
                            # the material has its own glow map: make it brighter
                            s.default_value = max(0.6, s.default_value) * mult
                        elif pose == "bellyGlow" or glow != 1.0:
                            # No glow map (raw image-to-3D meshes): the default emission colour is white, so raising
                            # the strength turns the whole hull into a white silhouette. Let the hull's own colours
                            # glow instead.
                            bc = n.inputs.get("Base Color")
                            if ec is not None and bc is not None and bc.is_linked:
                                m.node_tree.links.new(bc.links[0].from_socket, ec)
                                s.default_value = 0.2 * mult
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
        # Watts for a hull about one unit across (image-to-3D meshes are normalised); 900/600 burned the
        # hull out to white.
        ld.energy = 45.0 if pose == "bellyGlow" else 35.0
        ld.color = (1.0, 0.75, 0.55) if pose == "bellyGlow" else (0.55, 0.95, 1.0)
        lo = bpy.data.objects.new("TX_CORE", ld)
        bpy.context.scene.collection.objects.link(lo)
        bpy.context.view_layer.update()
        pts = world_points(meshes, step=max(1, sum(len(m.data.vertices) for m in meshes) // 20000))
        nose_y = max(p.y for p in pts)
        # Placed in world space (core / nose tip), then carried along by the pivot when the hull turns.
        lo.parent = pivot
        lo.matrix_parent_inverse = pivot.matrix_world.inverted()
        lo.location = (0.0, 0.0, 0.4) if pose == "bellyGlow" else (0.0, nose_y, 0.4)


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
        bg.inputs[0].default_value = (0.10, 0.13, 0.17, 1)     # something for metal to reflect
        bg.inputs[1].default_value = 1.0
    sc.world = w


def main():
    a = args()
    reset()
    pivot, meshes = import_mesh(a.model)
    if a.skin == "biometal":
        apply_biometal(meshes, a.palette, a.deep_glow)
    radius = lay_flat_and_center(pivot, meshes, a.orient, a.flip, a.view_axis)
    # Nose to world +Y (screen up) before the poses, so "front third" and "along the nose" mean the real nose.
    pivot.matrix_world = Matrix.Rotation(math.radians(a.nose_yaw), 4, "Z") @ pivot.matrix_world
    bpy.context.view_layer.update()
    apply_pose(pivot, meshes, a.pose, a.glow)
    fit = a.fit_radius if a.fit_radius > 0 else radius
    setup_scene(a.size, fit, a.engine, a.samples)
    os.makedirs(a.out, exist_ok=True)
    base = pivot.rotation_euler.copy()

    # Spin around the world Z axis, applied after the lay-flat rotation.
    flat = pivot.matrix_world.copy()
    yaws = [0, 90, 180, 270] if a.probe else [i * 360.0 / a.frames for i in range(a.frames)]
    for i, cw in enumerate(yaws):
        ang = math.radians(-cw)  # clockwise on screen = negative Z (the nose yaw is already applied)
        pivot.matrix_world = Matrix.Rotation(ang, 4, "Z") @ flat
        bpy.context.scene.render.filepath = os.path.join(a.out, f"f{i:03d}.png")
        bpy.ops.render.render(write_still=True)
    pivot.rotation_euler = base
    with open(os.path.join(a.out, "render.json"), "w") as fh:
        json.dump({"model": a.model, "frames": len(yaws), "size": a.size, "noseYaw": a.nose_yaw,
                   "pose": a.pose, "radius": radius, "fitRadius": fit, "probe": a.probe}, fh, indent=2)
    print(f"TX_FACINGS_DONE radius={radius:.4f} fit={fit:.4f}")


main()
