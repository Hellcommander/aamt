"""Blender side of the Elin creature paperdoll pipeline (elin_creature_paperdolls.py).

Renders one creature mesh from the four map directions Elin's paperdoll actor uses:

    S  the creature walking toward the viewer (down the screen)   -> its front
    W  walking to the left                                        -> its left flank, head to the left
    E  walking to the right                                       -> its right flank, head to the right
    N  walking away from the viewer (up the screen)               -> its back

A mesh made from a game tile (TRELLIS / SF3D) comes out as the tile shows the creature: seen from its front-left
three-quarter side, at whatever angle the artist drew. So the worker first finds where the creature is heading:

  1. the vertical mirror plane of the body (creatures are left/right symmetric): the yaw whose mirror image
     overlaps the body best, on a voxel grid;
  2. of the two directions in that plane, the one that points more toward the camera the tile was drawn from
     (tiles show faces, not backs); a pure side view keeps the artist's convention, heading left.

`--heading DEG` overrides the estimate (degrees, counter-clockwise seen from above, 0 = toward the tile camera).
All four views share one orthographic framing (same scale, feet on one baseline), so sprites cut from them line up.

  blender -b -P blender_creature_views.py -- --model body.glb --out views_dir
      [--size 768] [--pitch 22] [--heading DEG] [--probe] [--shade 0.35] [--action NAME --frames 4 --tag walk]

Writes view_S.png, view_W.png, view_E.png, view_N.png (RGBA) and views.json (heading, symmetry score, framing).
With --probe it writes probe_000.png .. probe_315.png (every 45 degrees of camera yaw) instead.
With --action it renders FRAMES evenly spaced poses of that animation of a rigged .glb per direction:
<tag>_S_0.png ... (the pose-less views are not written).
"""
import argparse
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--jobs", default="", help="JSON list of jobs (model, out and any of the options below by name): "
                                                "many bodies in one Blender start")
    ap.add_argument("--size", type=int, default=768)
    ap.add_argument("--pitch", type=float, default=22.0, help="camera elevation in degrees (Elin tiles are drawn from slightly above)")
    ap.add_argument("--heading", type=float, default=None)
    ap.add_argument("--front-prior", type=float, default=None,
                    help="camera yaw where the mesh generator usually puts the front (TRELLIS: 0). Of the two ends of "
                         "the mirror plane the one nearer this yaw is the front; if neither is within 50 degrees, the "
                         "prior itself is used")
    ap.add_argument("--tile-yaw", type=float, default=0.0,
                    help="camera yaw that shows the body as the tile does (found by the driver from a --probe pass)")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--probe-step", type=float, default=45.0)
    ap.add_argument("--min-depth", type=float, default=0.0,
                    help="stretch the body along the tile camera's axis until it is at least this deep, as a share of "
                         "its longest side (single-image meshes come out as shallow reliefs)")
    ap.add_argument("--lit", action="store_true",
                    help="write lit.png only: the body from the tile's view, shaded by a key light on white. A shaded "
                         "picture of a body is what an image-to-3D model needs to build volume; a pixel tile is not")
    ap.add_argument("--shaded", action="store_true",
                    help="light the faces softly instead of showing plain texture colours: a full body made from a "
                         "smooth concept has one colour per part and needs the shading to read as a body")
    ap.add_argument("--max-turn", type=float, default=90.0,
                    help="no face looks at the body from more than this many degrees off the picture's plane normal "
                         "(front or back). A single-image mesh is a relief: seen edge-on it is a slab, so the side "
                         "faces of such a body are turned views instead (55 is a good value); 90 = true side views")
    ap.add_argument("--action", default="")
    ap.add_argument("--frames", type=int, default=4)
    ap.add_argument("--phase", type=float, default=0.0,
                    help="where in each of the FRAMES slices of the action the pose is taken, 0..1: 0 for a loop, 0.5 "
                         "for a one-shot (which starts and ends at rest)")
    ap.add_argument("--tag", default="walk")
    ap.add_argument("--fit", type=float, default=0.0, help="shared framing radius (so clips line up with the still views)")
    return ap.parse_args(argv)


def import_model(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
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
    pivot = bpy.data.objects.new("CREATURE_PIVOT", None)
    bpy.context.scene.collection.objects.link(pivot)
    for o in list(bpy.context.scene.objects):
        if o.parent is None and o is not pivot:
            o.parent = pivot
    return pivot, meshes


def rest_pose():
    """A rigged .glb comes in with one of its actions playing. The framing (centre, radius) and the rest views are
    taken with no action and every bone at rest, so they are the same for every clip of the model."""
    for o in bpy.context.scene.objects:
        if o.type != "ARMATURE":
            continue
        if o.animation_data:
            o.animation_data.action = None
        for pb in o.pose.bones:
            pb.location = (0.0, 0.0, 0.0)
            pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            pb.rotation_euler = (0.0, 0.0, 0.0)
            pb.scale = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()


def world_points(meshes, limit=60000):
    """Vertices of every mesh in world space (evaluated, so a posed armature counts)."""
    deps = bpy.context.evaluated_depsgraph_get()
    out = []
    for o in meshes:
        ev = o.evaluated_get(deps)
        me = ev.to_mesh()
        n = len(me.vertices)
        co = np.empty(n * 3, dtype=np.float64)
        me.vertices.foreach_get("co", co)
        co = co.reshape(n, 3)
        m = np.array(ev.matrix_world)
        out.append(co @ m[:3, :3].T + m[:3, 3])
        ev.to_mesh_clear()
    pts = np.concatenate(out)
    if len(pts) > limit:
        pts = pts[np.random.default_rng(7).choice(len(pts), limit, replace=False)]
    return pts


def symmetry_heading(pts):
    """Yaw (degrees, CCW from above, 0 = +Y... see below) of the body's mirror plane normal, and the overlap score.

    Blender is Z up. A glTF import turns the model so that the view it was made from looks along +Y (the camera sits
    at -Y looking toward +Y). Angles here are measured in the ground plane from the direction toward that camera
    (-Y), counter-clockwise seen from above.
    """
    c = (pts.min(axis=0) + pts.max(axis=0)) / 2
    p = pts - c
    r = float(np.abs(p).max()) or 1.0
    g = 40
    best = (-1.0, 0.0)
    scores = []
    for deg in range(0, 180, 3):
        a = math.radians(deg)
        # side axis s (the mirror plane's normal) and forward axis f, both in the ground plane
        s = np.array([math.cos(a), math.sin(a), 0.0])
        f = np.array([-math.sin(a), math.cos(a), 0.0])
        u = p @ s
        v = p @ f
        w = p[:, 2]

        def grid(uu):
            idx = np.clip(((np.stack([uu, v, w], axis=1) / r) * 0.5 + 0.5) * (g - 1), 0, g - 1).astype(int)
            occ = np.zeros((g, g, g), dtype=bool)
            occ[idx[:, 0], idx[:, 1], idx[:, 2]] = True
            return occ

        a_occ, b_occ = grid(u), grid(-u)
        inter = np.logical_and(a_occ, b_occ).sum()
        union = np.logical_or(a_occ, b_occ).sum()
        score = inter / max(1, union)
        scores.append((deg, score))
        if score > best[0]:
            best = (score, deg)
    score, side_deg = best
    # forward axis is perpendicular to the side axis: two candidates, 180 degrees apart
    fwd = side_deg + 90.0
    return fwd, score, scores


def pick_forward(fwd_deg, tile_yaw):
    """Of fwd and fwd+180 (world angles), the heading that points more toward the tile camera; a pure side view
    keeps the artist's convention and heads to the left of the tile."""
    def vec(deg):
        a = math.radians(deg)
        return np.array([math.cos(a), math.sin(a), 0.0])

    cam = tile_yaw - 90.0                      # world angle of the tile camera's position (see place_camera)
    to_cam, left = vec(cam), vec(cam - 90.0)   # for a camera at angle c, screen-left is the direction c - 90
    cands = [fwd_deg % 360.0, (fwd_deg + 180.0) % 360.0]
    return sorted(cands, key=lambda d: -(vec(d) @ to_cam + 0.25 * (vec(d) @ left)))[0]


def heading_to_tile_angle(world_deg, tile_yaw):
    """World angle (CCW from +X) -> angle from the tile camera's direction, CCW seen from above."""
    return (world_deg - (tile_yaw - 90.0)) % 360.0


def setup_render(size, lit=False):
    """Orthographic camera, transparent film, and every material turned into its plain texture colour: a sprite is
    recoloured to the tile's palette afterwards, so lighting would only wash the colours out. lit=True keeps the
    surfaces and lights them softly instead (for a concept picture)."""
    sc = bpy.context.scene
    engines = {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
    sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
    sc.render.resolution_x = sc.render.resolution_y = size
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    try:
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.look = "None"
    except Exception:
        pass
    world = bpy.data.worlds.new("dark")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.55 if lit else 0.0
    world.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
    sc.world = world
    if lit:
        key = bpy.data.lights.new("key", "SUN")
        key.energy = 2.4
        key_ob = bpy.data.objects.new("key", key)
        sc.collection.objects.link(key_ob)
        key_ob.rotation_euler = (math.radians(55), 0, math.radians(-35))
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        if lit:
            for nd in mat.node_tree.nodes:
                if nd.type == "BSDF_PRINCIPLED":
                    for name, val in (("Metallic", 0.0), ("Roughness", 0.9)):
                        if name in nd.inputs:
                            for l in list(nd.inputs[name].links):
                                mat.node_tree.links.remove(l)
                            nd.inputs[name].default_value = val
            continue
        nt = mat.node_tree
        out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
        bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if out is None or bsdf is None:
            continue
        emit = nt.nodes.new("ShaderNodeEmission")
        emit.inputs["Strength"].default_value = 1.0
        base = bsdf.inputs["Base Color"]
        if base.links:
            nt.links.new(base.links[0].from_socket, emit.inputs["Color"])
        else:
            emit.inputs["Color"].default_value = base.default_value
        nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
        try:
            mat.blend_method = "OPAQUE"
        except Exception:
            pass
    cam = bpy.data.cameras.new("cam")
    cam.type = "ORTHO"
    cam_ob = bpy.data.objects.new("cam", cam)
    sc.collection.objects.link(cam_ob)
    sc.camera = cam_ob
    return cam_ob


def deepen(pivot, pts, tile_yaw, min_depth):
    """Stretch the body along the tile camera's axis, about its middle, until it is min_depth of its longest side deep."""
    a = math.radians(tile_yaw - 90.0)
    n = np.array([math.cos(a), math.sin(a), 0.0])
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    centre = (lo + hi) / 2
    along = (pts - centre) @ n
    depth = float(along.max() - along.min())
    longest = float((hi - lo).max())
    if depth <= 1e-6 or depth >= min_depth * longest:
        return 1.0
    f = min_depth * longest / depth
    stretch = np.eye(4)
    stretch[:3, :3] += (f - 1.0) * np.outer(n, n)
    to_c, from_c = np.eye(4), np.eye(4)
    to_c[:3, 3], from_c[:3, 3] = -centre, centre
    pivot.matrix_world = Matrix((from_c @ stretch @ to_c).tolist()) @ pivot.matrix_world
    bpy.context.view_layer.update()
    return f


def place_camera(cam_ob, centre, radius, pitch_deg, yaw_deg):
    """Camera on a circle around the body. yaw 0 = where the tile was drawn from (-Y side), CCW seen from above."""
    a = math.radians(yaw_deg - 90.0)          # 0 -> -Y
    p = math.radians(pitch_deg)
    d = radius * 6
    pos = Vector((centre[0] + d * math.cos(a) * math.cos(p), centre[1] + d * math.sin(a) * math.cos(p), centre[2] + d * math.sin(p)))
    cam_ob.location = pos
    look = Vector(centre) - pos
    cam_ob.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
    cam_ob.data.ortho_scale = radius * 2.3
    cam_ob.data.clip_start = 0.01
    cam_ob.data.clip_end = radius * 20


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def main():
    a = parse()
    if a.jobs:
        with open(a.jobs, encoding="utf-8") as fh:
            jobs = json.load(fh)
        for job in jobs:
            one = argparse.Namespace(**vars(a))
            for k, v in job.items():
                setattr(one, k.replace("-", "_"), v)
            try:
                run_one(one)
            except BaseException as exc:      # SystemExit included: one bad mesh must not end the batch
                os.makedirs(one.out, exist_ok=True)
                with open(os.path.join(one.out, "error.txt"), "w", encoding="utf-8") as fh:
                    fh.write(str(exc))
                print("JOB FAILED", one.model, exc)
        return
    run_one(a)


def run_one(a):
    os.makedirs(a.out, exist_ok=True)
    pivot, meshes = import_model(a.model)
    rest_pose()
    bpy.context.view_layer.update()
    pts = world_points(meshes)
    stretched = 1.0
    if a.min_depth > 0 and not a.probe:
        stretched = deepen(pivot, pts, a.tile_yaw, a.min_depth)
        pts = world_points(meshes)
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    centre = (lo + hi) / 2
    radius = a.fit if a.fit > 0 else float(np.linalg.norm(hi - lo)) / 2
    cam = setup_render(a.size, a.lit or a.shaded)

    if a.lit:
        place_camera(cam, centre, radius, 0.0, a.tile_yaw)
        render(os.path.join(a.out, "lit.png"))
        return

    if a.probe:
        yaw = 0.0
        while yaw < 359.9:
            place_camera(cam, centre, radius, 0.0, yaw)
            render(os.path.join(a.out, f"probe_{int(round(yaw * 10)):04d}.png"))
            yaw += a.probe_step
        ext = sorted(float(x) for x in (hi - lo))
        with open(os.path.join(a.out, "probe.json"), "w", encoding="utf-8") as fh:
            json.dump({"extents": [float(x) for x in (hi - lo)], "depth_ratio": ext[0] / max(1e-6, ext[2])}, fh)
        return

    fwd_world, score, scores = symmetry_heading(pts)
    world_heading = pick_forward(fwd_world, a.tile_yaw)
    if a.front_prior is not None and a.heading is None:
        # the camera yaw that looks the creature in the face is world heading + 90 (see heading_to_tile_angle)
        def off(w):
            return abs((w + 90.0 - a.front_prior + 180.0) % 360.0 - 180.0)
        world_heading = min([fwd_world % 360.0, (fwd_world + 180.0) % 360.0], key=off)
        if off(world_heading) > 50.0:
            world_heading = (a.front_prior - 90.0) % 360.0
    heading = heading_to_tile_angle(world_heading, a.tile_yaw) if a.heading is None else a.heading % 360.0
    # The camera yaw that looks the creature in the face is where it is heading: seen from there it walks toward the
    # viewer (S). A camera a quarter turn counter-clockwise of that (seen from above) has the creature heading to the
    # left of the screen (W); the opposite quarter turn gives E, and from behind it walks away (N).
    # T is the view the tile was drawn from: the sprite stage scales by it and it is the check against the tile.
    t = a.tile_yaw

    def turned(rel):
        """rel = camera yaw from the tile's view. Keep it within max_turn of the relief's front (0) or back (180)."""
        rel = (rel + 180.0) % 360.0 - 180.0                 # -180 .. 180
        if a.max_turn >= 90.0:
            return rel
        off = abs(rel)
        if off <= a.max_turn or off >= 180.0 - a.max_turn:
            return rel
        side = 1.0 if rel >= 0 else -1.0
        return side * (a.max_turn if off <= 90.0 else 180.0 - a.max_turn)

    # A face that would land exactly edge-on (a side-view body seen from its head or its tail) goes to the front of
    # the relief for S and to its back for N.
    rel = {"S": heading, "W": heading + 90.0, "E": heading - 90.0, "N": heading + 180.0}
    nudge = {"S": 0.5, "N": -0.5, "W": 0.0, "E": 0.0}
    yaws = {}
    for d, r in rel.items():
        r = (r + 180.0) % 360.0 - 180.0
        if abs(abs(r) - 90.0) < 1.0:
            r = (89.0 if r > 0 else -89.0) if d == "S" else (91.0 if r > 0 else -91.0) if d == "N" else r
        yaws[d] = t + turned(r)
    yaws["T"] = t
    ext = sorted(float(x) for x in (hi - lo))

    info = {
        "model": a.model, "heading": round(heading, 1), "estimated": a.heading is None,
        "symmetry": round(float(score), 3), "radius": radius, "pitch": a.pitch, "size": a.size,
        "extents": [float(x) for x in (hi - lo)], "yaws": {k: round(v % 360.0, 1) for k, v in yaws.items()},
        "tile_yaw": t, "depth_ratio": round(ext[0] / max(1e-6, ext[2]), 3), "stretched": round(stretched, 3),
    }

    if a.action:
        acts = {act.name: act for act in bpy.data.actions}
        act = acts.get(a.action) or next((v for k, v in acts.items() if a.action.lower() in k.lower()), None)
        if act is None:
            raise SystemExit(f"no action '{a.action}' in {list(acts)}")
        arm = next((o for o in bpy.context.scene.objects if o.type == "ARMATURE"), None)
        if arm is None:
            raise SystemExit("model has no armature")
        arm.animation_data_create()
        arm.animation_data.action = act
        ad = arm.animation_data          # Blender 4.4+: an action plays through one of its slots
        if hasattr(ad, "action_slot") and ad.action_slot is None and len(getattr(act, "slots", [])):
            ad.action_slot = act.slots[0]
        f0, f1 = act.frame_range
        info["action"] = act.name
        for i in range(a.frames):
            bpy.context.scene.frame_set(int(round(f0 + (f1 - f0) * (i + a.phase) / a.frames)))
            for d, yaw in yaws.items():
                place_camera(cam, centre, radius, a.pitch, yaw)
                render(os.path.join(a.out, f"{a.tag}_{d}_{i}.png"))
    else:
        for d, yaw in yaws.items():
            # T is the calibration view: level with the body, exactly where the tile was drawn from
            place_camera(cam, centre, radius, 0.0 if d == "T" else a.pitch, yaw)
            render(os.path.join(a.out, f"view_{d}.png"))

    with open(os.path.join(a.out, "views.json"), "w", encoding="utf-8") as fh:
        json.dump(info, fh, indent=2)
    print("VIEWS", json.dumps(info))


main()
