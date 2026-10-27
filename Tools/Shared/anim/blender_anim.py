"""Blender (headless) side of the animation pipeline (anim_client.py drives it):

  blender -b --factory-startup -P blender_anim.py -- prep   <in.glb> <work>      normalise -> work/norm.glb + work/mesh.npz
  blender -b --factory-startup -P blender_anim.py -- render <work> [W H [AZ EL]] work/frame0.png, cam.json, visible.npy
  blender -b --factory-startup -P blender_anim.py -- build  <work> <out.glb>     armature + skin (rig.npz) + clips (clips/*.npz)
  blender -b --factory-startup -P blender_anim.py -- preview <in.glb> <out.png>  contact sheet: each clip at 4 moments

Conventions: Blender Z up; the creature faces -Y (glTF +Z, Unity +Z); feet on z = 0; longest side 1 unit.
prep expects a mesh that already faces -Y (orientation is the caller's: e.g. Chimera's rig_creature.py <plan>:norig).
mesh.npz holds the vertices exactly as `render` and `build` see them after importing norm.glb, so per-vertex data
(weights, tracks) lines up across stages.

rig.npz: joints (J,3), tails (J,3), parents (J,) int (-1 = root), names (J,), weights (N,J) over mesh.npz's vertices.
clips/<name>.npz: fps, rot (F,J,4) wxyz rest-relative joint rotations about each joint (armature axes, parent-relative,
i.e. D_j = D_parent @ T(p_j) R_j T(-p_j)), trans (F,3) root offset (armature axes). Exported as named glTF animations.
"""
import json, math, os, sys
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
MODE = argv[0]


def log(*a):
    print("ANIM:", *a, flush=True)


def fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_body(path):
    bpy.ops.import_scene.gltf(filepath=path)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        raise SystemExit("no mesh in " + path)
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    body = bpy.context.view_layer.objects.active
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in list(bpy.context.scene.objects):
        if o != body:
            bpy.data.objects.remove(o, do_unlink=True)
    return body


def verts(body):
    me = body.data
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


def export_glb(path, animations=False):
    kw = dict(filepath=path, export_format="GLB", use_selection=False, export_yup=True, export_apply=False,
              export_draco_mesh_compression_enable=False, export_morph=False)
    if animations:
        kw.update(export_skins=True, export_animations=True)
        try:
            bpy.ops.export_scene.gltf(**kw, export_animation_mode="NLA_TRACKS", export_force_sampling=True, export_frame_step=1)
            return
        except TypeError as e:
            log("exporter options:", e)
    bpy.ops.export_scene.gltf(**kw)


# ---- prep: normalise ------------------------------------------------------------------------------------------------

def prep(src, work):
    os.makedirs(work, exist_ok=True)
    fresh()
    body = import_body(src)
    co = verts(body)
    lo, hi = co.min(0), co.max(0)
    k = 1.0 / float((hi - lo).max())
    centre = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]))
    body.data.transform(Matrix.Scale(k, 4) @ Matrix.Translation(-centre))
    body.data.update()
    norm = os.path.join(work, "norm.glb")
    export_glb(norm)
    # what later stages will see: re-import and record the vertex order
    fresh()
    body = import_body(norm)
    me = body.data
    me.calc_loop_triangles()
    tris = np.empty(len(me.loop_triangles) * 3, np.int32)
    me.loop_triangles.foreach_get("vertices", tris)
    co = verts(body)
    np.savez(os.path.join(work, "mesh.npz"), verts=co, faces=tris.reshape(-1, 3))
    log(f"prep: {len(co)} vertices, {len(tris) // 3} triangles, size {np.ptp(co, 0).round(3).tolist()}")


# ---- render: the first frame for the video model, and the camera that took it ---------------------------------------

def camera_for(co, w, h, azimuth=35.0, elevation=16.0, fill=0.6, lens=50.0):
    """A front-three-quarter camera (from the creature's right-front) framing the body so its projected box takes
    `fill` of the frame (height or width, whichever binds), leaving room around it for the motion."""
    lo, hi = co.min(0), co.max(0)
    target = Vector(((lo + hi) / 2).tolist())
    sensor = 36.0
    f_px = lens / sensor * max(w, h)
    az, el = math.radians(azimuth), math.radians(elevation)
    back = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    pts = co[np.random.default_rng(0).choice(len(co), min(4000, len(co)), replace=False)]
    dist = float(np.linalg.norm(hi - lo)) * 2
    for _ in range(4):  # perspective: re-measure at the new distance
        pos = target + back * dist
        fwd = (target - pos).normalized()
        right = fwd.cross(Vector((0, 0, 1))).normalized()
        up = right.cross(fwd)
        rel = pts - np.array(pos)
        z = rel @ np.array(fwd)
        u = f_px * (rel @ np.array(right)) / z
        v = f_px * (rel @ np.array(up)) / z
        k = max(np.ptp(u) / (fill * w), np.ptp(v) / (fill * h))
        dist *= k
    pos = target + back * dist
    return pos, target, lens, sensor


def cv_projection(cam, w, h):
    """3x4 P (OpenCV: pixels, y down) for a Blender perspective camera: x_pix ~ P @ [X,Y,Z,1]."""
    cd = cam.data
    f_px = cd.lens / cd.sensor_width * max(w, h) if cd.sensor_fit in ("AUTO", "HORIZONTAL") else cd.lens / cd.sensor_height * h
    K = np.array([[f_px, 0, w / 2], [0, f_px, h / 2], [0, 0, 1]])
    m = np.array(cam.matrix_world.inverted())  # world -> Blender camera (looks down -Z, Y up)
    flip = np.diag([1, -1, -1, 1])            # -> OpenCV camera (looks down +Z, Y down)
    Rt = (flip @ m)[:3]
    return K @ Rt, K, Rt


def render(work, w=640, h=352, azimuth=35.0, elevation=16.0):
    fresh()
    sc = bpy.context.scene
    body = import_body(os.path.join(work, "norm.glb"))
    co = verts(body)
    pos, target, lens, sensor = camera_for(co, w, h, azimuth=azimuth, elevation=elevation)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.location = pos
    cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens, cam.data.sensor_width = lens, sensor
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    # EEVEE with soft studio light on plain white: what the video model saw in its i2v training more than a flat render
    sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys() else "BLENDER_EEVEE"
    sc.world = bpy.data.worlds.new("w")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (1, 1, 1, 1)
    bg.inputs[1].default_value = 0.9
    for name, rot, energy in (("key", (50, 0, 35), 3.5), ("fill", (60, 0, -120), 1.2), ("rim", (120, 0, 180), 2.0)):
        L = bpy.data.objects.new(name, bpy.data.lights.new(name, "SUN"))
        L.data.energy = energy
        L.rotation_euler = [math.radians(v) for v in rot]
        sc.collection.objects.link(L)
    for m in body.data.materials:  # generated PBR comes back metallic and renders near black under a white world
        if m and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == "BSDF_PRINCIPLED":
                    n.inputs["Metallic"].default_value = 0.0
                    for l in list(n.inputs["Metallic"].links):
                        m.node_tree.links.remove(l)
    sc.view_settings.view_transform = "Standard"
    sc.render.filepath = os.path.join(work, "frame0.png")
    bpy.ops.render.render(write_still=True)
    P, K, Rt = cv_projection(cam, w, h)
    json.dump({"width": w, "height": h, "P": P.tolist(), "K": K.tolist(), "Rt": Rt.tolist(), "azimuth": azimuth,
               "elevation": elevation, "cam": list(pos), "target": list(target)}, open(os.path.join(work, "cam.json"), "w"), indent=1)
    # which vertices the camera sees in that frame (the tracker can only follow those)
    dg = bpy.context.evaluated_depsgraph_get()
    vis = np.zeros(len(co), bool)
    eye = cam.matrix_world.translation
    for i, p in enumerate(co):
        v = Vector(p.tolist())
        d = v - eye
        hit, loc, *_ = sc.ray_cast(dg, eye, d.normalized(), distance=d.length + 1e-3)
        vis[i] = (not hit) or (loc - v).length < 0.006
    np.save(os.path.join(work, "visible.npy"), vis)
    log(f"render: frame0 {w}x{h}, {int(vis.sum())}/{len(co)} vertices visible")


# ---- build: armature, skin, clips -----------------------------------------------------------------------------------

def build(work, out):
    fresh()
    sc = bpy.context.scene
    sc.render.fps = 30
    body = import_body(os.path.join(work, "norm.glb"))
    rig = np.load(os.path.join(work, "rig.npz"), allow_pickle=True)
    J, T, par, names, W = rig["joints"], rig["tails"], rig["parents"], [str(n) for n in rig["names"]], rig["weights"]
    co = verts(body)
    if W.shape[0] != len(co):
        raise SystemExit(f"rig weights are for {W.shape[0]} vertices, mesh has {len(co)}")
    arm_data = bpy.data.armatures.new("Rig")
    arm = bpy.data.objects.new("Rig", arm_data)
    sc.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    for j, n in enumerate(names):
        b = arm_data.edit_bones.new(n)
        h, t = Vector(J[j].tolist()), Vector(T[j].tolist())
        if (t - h).length < 1e-3:
            t = h + Vector((0, 0, 0.02))
        b.head, b.tail = h, t
        b.use_connect = False
    for j, n in enumerate(names):
        if par[j] >= 0:
            arm_data.edit_bones[n].parent = arm_data.edit_bones[names[par[j]]]
    bpy.ops.object.mode_set(mode="OBJECT")
    # four strongest influences per vertex (what Unity skins with), renormalised
    top = np.argsort(-W, axis=1)[:, :4]
    groups = [body.vertex_groups.new(name=n) for n in names]
    for i in range(len(co)):
        ws = W[i, top[i]]
        s = float(ws.sum())
        if s <= 1e-8:
            continue
        for j, w in zip(top[i], ws / s):
            if w > 1e-3:
                groups[j].add([i], float(w), "REPLACE")
    body.parent = arm
    body.modifiers.new("Armature", "ARMATURE").object = arm

    clip_dir = os.path.join(work, "clips")
    clips = sorted(f for f in os.listdir(clip_dir) if f.endswith(".npz")) if os.path.isdir(clip_dir) else []
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm.pose.bones
    for p in pb:
        p.rotation_mode = "QUATERNION"
    rest = {p.name: p.bone.matrix_local.to_quaternion() for p in pb}
    arm.animation_data_create()
    root_names = [names[j] for j in range(len(names)) if par[j] < 0]
    for fn in clips:
        c = np.load(os.path.join(clip_dir, fn))
        name = os.path.splitext(fn)[0]
        rot, trans = c["rot"], c["trans"]
        act = bpy.data.actions.new(name)
        arm.animation_data.action = act
        for f in range(rot.shape[0]):
            for j, n in enumerate(names):
                r = rest[n]
                q = Quaternion(rot[f, j].tolist())
                p = pb[n]
                p.rotation_quaternion = r.inverted() @ q @ r      # armature-axes rotation -> the bone's own
                p.keyframe_insert("rotation_quaternion", frame=f)
                if n in root_names:
                    p.location = r.inverted() @ Vector(trans[f].tolist())
                    p.keyframe_insert("location", frame=f)
        act.use_fake_user = True
        tr = arm.animation_data.nla_tracks.new()
        tr.name = name
        tr.strips.new(name, 0, act)
        arm.animation_data.action = None
        log(f"clip {name}: {rot.shape[0]} frames")
    bpy.ops.object.mode_set(mode="OBJECT")
    for p in pb:
        p.rotation_quaternion = Quaternion()
        p.location = Vector()
    bpy.ops.object.select_all(action="SELECT")
    export_glb(out, animations=True)
    log("wrote", out)


# ---- preview --------------------------------------------------------------------------------------------------------

def preview(src, out_png, size=240):
    fresh()
    sc = bpy.context.scene
    sc.render.fps = 30  # glTF keys are in seconds; import at the clips' rate so frames line up
    bpy.ops.import_scene.gltf(filepath=src)
    arm = next((o for o in sc.objects if o.type == "ARMATURE"), None)
    body = next(o for o in sc.objects if o.type == "MESH")
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "TEXTURE"
    sc.render.resolution_x = sc.render.resolution_y = size
    sc.world = bpy.data.worlds.new("w")
    sc.world.color = (0.16, 0.17, 0.2)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.location = Vector((1.05, -1.55, 0.95))
    cam.rotation_euler = (Vector((0, 0, 0.3)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 40
    tmp = os.path.splitext(out_png)[0] + "_frames"
    os.makedirs(tmp, exist_ok=True)
    rows = []
    acts = list(bpy.data.actions) if arm else []
    if arm:
        arm.animation_data_create()
        for tr in list(arm.animation_data.nla_tracks):
            arm.animation_data.nla_tracks.remove(tr)
    for act in acts or [None]:
        row = []
        if act:
            arm.animation_data.action = act
            try:
                if hasattr(arm.animation_data, "action_slot") and act.slots:
                    arm.animation_data.action_slot = act.slots[0]
            except Exception:
                pass
            f0, f1 = act.frame_range
        else:
            f0 = f1 = 0
        for i, frac in enumerate((0.0, 0.33, 0.66, 1.0)):
            sc.frame_set(int(round(f0 + (f1 - f0) * frac)))
            sc.render.filepath = os.path.join(tmp, f"{act.name if act else 'rest'}_{i}.png")
            bpy.ops.render.render(write_still=True)
            row.append(sc.render.filepath)
        rows.append((act.name if act else "rest", row))
    json.dump(rows, open(os.path.join(tmp, "rows.json"), "w"))
    log("preview frames", tmp)


if MODE == "prep":
    prep(argv[1], argv[2])
elif MODE == "render":
    render(argv[1], *(int(x) for x in argv[2:4]), *(float(x) for x in argv[4:6]))
elif MODE == "build":
    build(argv[1], argv[2])
elif MODE == "preview":
    preview(argv[1], argv[2])
else:
    raise SystemExit("unknown mode " + MODE)
