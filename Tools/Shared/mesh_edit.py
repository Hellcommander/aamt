#!/usr/bin/env python3
"""Post-generation mesh fixing for agents: look at a generated .glb, then repair it, without Blender.

Generated meshes (SF3D, TRELLIS) often need clean-up: stray floating bits, a washed-out texture, the wrong way up,
too many triangles. This tool gives an agent eyes (info + a four-view preview sheet it can read as an image) and
hands (a chain of edits), so the loop is: generate -> preview -> fix -> preview again.

    python mesh_edit.py info  in.glb
    python mesh_edit.py preview in.glb sheet.png [--size 384]
    python mesh_edit.py fix in.glb out.glb [ops...] [--preview sheet.png]

Ops run in the order given:
    --drop-small F        remove loose pieces smaller than fraction F of the largest (0.02 is a good start)
    --keep-largest        keep only the largest connected piece
    --merge               weld duplicate vertices, drop degenerate/duplicate faces, fix winding and normals
    --fill-holes          close small holes
    --decimate N          reduce to about N triangles (fast-simplification if installed, else Blender)
    --remesh VOXEL        Blender voxel remesh (fuses shards into one shell; VOXEL ~0.01 of a 1 m mesh), texture rebaked
    --rotate AXIS:DEG     e.g. x:90 (repeatable)
    --mirror AXIS
    --scale F             uniform scale
    --squash AXIS:F       scale one axis about the centre, e.g. z:0.55 to thin a slab-deep vest
    --center              move the bounding-box centre to the origin
    --floor               sit the lowest point on y = 0
    --cut AXIS:KEEP:VALUE keep one side of a plane, e.g. y:above:0.1 or x:below:0 (split a pair of legs, trim a base)
    --brightness F        texture brightness x F (1.2 = 20% brighter)
    --contrast F          texture contrast x F
    --saturation F        texture saturation x F (wash-out fix: 1.3)
    --tint HEX:F          blend the texture toward a colour by F (0..1)
    --texture-size N      resize the texture to N x N
    --match-back F        recolour the back half (which single-image generators guess flat and pale) toward the
                          front's colours by F (0..1), keeping its shading detail

Runs with any Python that has trimesh, numpy and Pillow; if this one lacks trimesh it re-runs itself in the
Stable Fast 3D venv (AAMT_SF3D_HOME, default E:\\tools\\stable-fast-3d), so agents can call it from anywhere.
From Python: ai_resources.inspect_mesh / preview_mesh / edit_mesh.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _reexec_if_needed() -> None:
    try:
        import trimesh  # noqa: F401
    except ImportError:
        venv = Path(os.environ.get("AAMT_SF3D_HOME") or r"E:\tools\stable-fast-3d") / "venv" / "Scripts" / "python.exe"
        if not venv.exists() or Path(sys.executable).resolve() == venv.resolve():
            sys.exit("mesh_edit needs trimesh (install it, or set AAMT_SF3D_HOME to the Stable Fast 3D install)")
        env = dict(os.environ)
        env.pop("NoDefaultCurrentDirectoryInExePath", None)
        sys.exit(subprocess.call([str(venv), str(Path(__file__).resolve()), *sys.argv[1:]], env=env))


def load(path: Path):
    import trimesh
    m = trimesh.load(str(path), force="mesh", process=False)
    return m


def texture(m):
    v = getattr(m, "visual", None)
    mat = getattr(v, "material", None)
    if mat is None:
        return None
    return getattr(mat, "baseColorTexture", None) or getattr(mat, "image", None)


def set_texture(m, img) -> None:
    mat = m.visual.material
    if hasattr(mat, "baseColorTexture"):
        mat.baseColorTexture = img
    else:
        mat.image = img


def info(path: Path) -> dict:
    import numpy as np
    m = load(path)
    welded = m.copy(); welded.merge_vertices(merge_tex=True, merge_norm=True)  # UV seams split verts on export
    parts = welded.split(only_watertight=False)
    sizes = sorted((len(p.faces) for p in parts), reverse=True)
    tex = texture(m)
    out = {
        "file": str(path), "verts": int(len(m.vertices)), "tris": int(len(m.faces)),
        "bounds_min": [round(float(x), 4) for x in m.bounds[0]], "bounds_max": [round(float(x), 4) for x in m.bounds[1]],
        "extents": [round(float(x), 4) for x in m.extents], "watertight": bool(m.is_watertight),
        "pieces": len(parts), "largest_piece_share": round(sizes[0] / max(1, len(m.faces)), 3) if sizes else 0,
        "small_pieces": int(sum(1 for s in sizes[1:] if s < 0.02 * sizes[0])) if sizes else 0,
        "has_uv": getattr(m.visual, "uv", None) is not None,
        "texture": list(tex.size) if tex is not None else None,
    }
    if tex is not None:
        a = np.asarray(tex.convert("RGB").resize((64, 64))).astype(float) / 255.0
        hsv_s = (a.max(axis=2) - a.min(axis=2)) / np.maximum(a.max(axis=2), 1e-4)
        out["texture_mean_brightness"] = round(float(a.mean()), 3)
        out["texture_mean_saturation"] = round(float(hsv_s.mean()), 3)
        out["hint"] = []
        out["blender"] = BLENDER.exists()
        if out["texture_mean_saturation"] < 0.12:
            out["hint"].append("texture looks washed out: try --saturation 1.4 --contrast 1.2")
        if out["texture_mean_brightness"] > 0.75:
            out["hint"].append("texture very bright: try --brightness 0.8")
        if out["small_pieces"]:
            out["hint"].append(f"{out['small_pieces']} small floating pieces: try --drop-small 0.02")
        if len(m.faces) > 40000:
            out["hint"].append("heavy mesh for a game prop: try --decimate 12000")
    return out


def preview(path_or_mesh, out_png: Path, size: int = 384) -> Path:
    """Four views (front, right, back, top-ish) with a flat-shaded, texture-coloured software render."""
    import numpy as np
    from PIL import Image, ImageDraw
    m = load(path_or_mesh) if isinstance(path_or_mesh, (str, Path)) else path_or_mesh
    v = np.asarray(m.vertices, float)
    f = np.asarray(m.faces, int)
    centre = (m.bounds[0] + m.bounds[1]) / 2
    scale = 0.8 * size / max(1e-6, float(max(m.extents)))
    tex = texture(m)
    uv = getattr(m.visual, "uv", None)
    if tex is not None and uv is not None:
        t = np.asarray(tex.convert("RGB"))
        th, tw = t.shape[:2]
        fuv = np.asarray(uv)[f].mean(axis=1)
        tx = np.clip((fuv[:, 0] % 1.0) * (tw - 1), 0, tw - 1).astype(int)
        ty = np.clip((1 - fuv[:, 1] % 1.0) * (th - 1), 0, th - 1).astype(int)
        col = t[ty, tx].astype(float)
    else:
        col = np.full((len(f), 3), 180.0)
    light = np.array([0.4, 0.7, -0.6]); light /= np.linalg.norm(light)
    sheet = Image.new("RGB", (size * 4, size + 24), (24, 28, 34))
    d0 = ImageDraw.Draw(sheet)
    views = [("front", 0, 0), ("right", 90, 0), ("back", 180, 0), ("above", 35, 35)]
    for i, (name, yaw, pitch) in enumerate(views):
        cy, sy, cp, sp = np.cos(np.radians(yaw)), np.sin(np.radians(yaw)), np.cos(np.radians(pitch)), np.sin(np.radians(pitch))
        p = v - centre
        x, z = p[:, 0] * cy - p[:, 2] * sy, p[:, 0] * sy + p[:, 2] * cy
        y, z = p[:, 1] * cp - z * sp, p[:, 1] * sp + z * cp
        P = np.stack([x, y, z], axis=1)
        a, b, c = P[f[:, 0]], P[f[:, 1]], P[f[:, 2]]
        n = np.cross(b - a, c - a)
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
        front = n[:, 2] < 0  # camera looks down +z
        shade = 0.35 + 0.65 * np.clip(-(n @ light), 0, 1)
        depth = (a[:, 2] + b[:, 2] + c[:, 2]) / 3
        img = Image.new("RGB", (size, size), (24, 28, 34))
        d = ImageDraw.Draw(img)
        for k in np.argsort(-depth):
            if not front[k]:
                continue
            pts = [(size / 2 + q[0] * scale, size / 2 - q[1] * scale) for q in (a[k], b[k], c[k])]
            d.polygon(pts, fill=tuple(int(x) for x in col[k] * shade[k]))
        sheet.paste(img, (i * size, 24))
        d0.text((i * size + 6, 4), name, fill=(200, 210, 220))
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png)
    return out_png


def _find_blender() -> Path:
    """AAMT_BLENDER, else the newest blender.exe under the usual install roots."""
    if os.environ.get("AAMT_BLENDER"):
        return Path(os.environ["AAMT_BLENDER"])
    found = []
    for root in (r"D:/tools/Blender Foundation", r"C:/Program Files/Blender Foundation"):
        found += Path(root).glob("*/blender.exe") if Path(root).exists() else []
    return max(found, key=lambda p: p.stat().st_mtime) if found else Path("blender.exe")


BLENDER = _find_blender()

_BLENDER_SCRIPT = r"""
import bpy, sys
a = sys.argv[sys.argv.index("--") + 1:]
src, dst, op, val = a[0], a[1], a[2], float(a[3])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
obs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
bpy.context.view_layer.objects.active = obs[0]
for o in obs: o.select_set(True)
if len(obs) > 1: bpy.ops.object.join()
ob = bpy.context.view_layer.objects.active
if op == "decimate":
    m = ob.modifiers.new("d", "DECIMATE"); m.ratio = min(1.0, val / max(1, len(ob.data.polygons)))
    bpy.ops.object.modifier_apply(modifier=m.name)
elif op == "remesh":
    hi = ob.copy(); hi.data = ob.data.copy(); bpy.context.collection.objects.link(hi)
    for mt in hi.data.materials:  # a diffuse-colour bake of a metal comes out black
        for nd in mt.node_tree.nodes:
            if nd.type == "BSDF_PRINCIPLED":
                for l in list(nd.inputs["Metallic"].links): mt.node_tree.links.remove(l)
                nd.inputs["Metallic"].default_value = 0.0
    m = ob.modifiers.new("r", "REMESH"); m.mode = "VOXEL"; m.voxel_size = val; m.use_smooth_shade = True
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(island_margin=0.003); bpy.ops.object.mode_set(mode="OBJECT")
    img = bpy.data.images.new("bake", 1024, 1024)
    mat = bpy.data.materials.new("baked"); mat.use_nodes = True
    nt = mat.node_tree; tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; nt.nodes.active = tex
    ob.data.materials.clear(); ob.data.materials.append(mat)
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = 1
    sc.render.bake.use_pass_direct = sc.render.bake.use_pass_indirect = False
    sc.render.bake.use_selected_to_active = True; sc.render.bake.cage_extrusion = val * 6; sc.render.bake.max_ray_distance = val * 12
    hi.select_set(True); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, margin=4)
    img.pack()
    print("BAKE_MEAN", sum(img.pixels[::97]) / max(1, len(img.pixels[::97])))
    nt.links.new(tex.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    bpy.data.objects.remove(hi)
bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=dst, use_selection=True, export_format="GLB")
"""


def blender_op(m, op: str, val: float):
    """Runs one Blender op on a trimesh mesh via a headless Blender and loads the result."""
    import tempfile
    if not BLENDER.exists():
        raise RuntimeError(f"Blender not found at {BLENDER} (set AAMT_BLENDER)")
    with tempfile.TemporaryDirectory() as td:
        src, dst, scr = Path(td) / "in.glb", Path(td) / "out.glb", Path(td) / "op.py"
        m.export(str(src)); scr.write_text(_BLENDER_SCRIPT, encoding="utf-8")
        env = dict(os.environ); env.pop("NoDefaultCurrentDirectoryInExePath", None)
        r = subprocess.run([str(BLENDER), "-b", "--factory-startup", "-P", str(scr), "--", str(src), str(dst), op, str(val)],
                           capture_output=True, text=True, env=env, timeout=900)
        if not dst.exists():
            raise RuntimeError("Blender failed: " + (r.stderr or r.stdout)[-800:])
        for line in r.stdout.splitlines():
            if line.startswith("BAKE_MEAN"): print(line, file=sys.stderr)
        return load(dst)


def match_back(m, k: float):
    """Blends the texels under back-facing triangles toward the front's colours, keeping their light/dark detail."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter
    img = texture(m).convert("RGB"); W, H = img.size
    uv = np.asarray(m.visual.uv); f = np.asarray(m.faces); n = np.asarray(m.face_normals)
    centre_z = (m.bounds[0][2] + m.bounds[1][2]) / 2
    fz = np.asarray(m.vertices)[f].mean(axis=1)[:, 2]
    back = (n[:, 2] > 0.25) | ((fz > centre_z) & (np.abs(n[:, 2]) < 0.25)) | (np.abs(n[:, 0]) > 0.75)
    mask = Image.new("L", (W, H), 0); d = ImageDraw.Draw(mask)
    for tri in uv[f[back]]:
        d.polygon([(u * W, (1 - v) * H) for u, v in tri], fill=255)
    mask = mask.filter(ImageFilter.MaxFilter(5))
    a = np.asarray(img).astype(float); msk = np.asarray(mask) > 0
    front = Image.new("L", (W, H), 0); d = ImageDraw.Draw(front)
    for tri in uv[f[n[:, 2] < -0.25]]:
        d.polygon([(u * W, (1 - v) * H) for u, v in tri], fill=255)
    fm = (np.asarray(front) > 0) & ~msk
    if not fm.any() or not msk.any():
        return False
    fc = a[fm]; fmean = fc.mean(axis=0); flum = fc.mean()
    lum = a[msk].mean(axis=1, keepdims=True)
    detail = (lum - lum.mean()) / max(1e-3, lum.std()) * fc.mean(axis=1).std()
    target = np.clip(fmean * (1 + detail / max(1.0, flum)), 0, 255)
    a[msk] = a[msk] * (1 - k) + target * k
    set_texture(m, Image.fromarray(a.astype("uint8")))
    return True


def _axis(name: str):
    return {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}[name.lower()]


def fix(src: Path, dst: Path, ops: list) -> dict:
    """Applies ops [(name, value)] in order and writes dst. Returns info() of the result plus a log."""
    import numpy as np
    import trimesh
    from PIL import Image, ImageEnhance
    m = load(src)
    log = []
    for name, val in ops:
        before = len(m.faces)
        if name in ("drop_small", "keep_largest"):
            # find pieces on a welded copy (UV seams split verts) but keep the original faces and UVs
            import trimesh.graph
            w = m.copy(); w.merge_vertices(merge_tex=True, merge_norm=True)
            lab = trimesh.graph.connected_component_labels(w.face_adjacency, node_count=len(w.faces))
            cnt = np.bincount(lab)
            keep = cnt[lab] >= (cnt.max() if name == "keep_largest" else float(val) * cnt.max())
            m.update_faces(keep); m.remove_unreferenced_vertices()
        elif name == "merge":
            m.merge_vertices()
            m.update_faces(m.nondegenerate_faces())
            m.update_faces(m.unique_faces())
            m.remove_unreferenced_vertices()
            trimesh.repair.fix_normals(m)
        elif name == "fill_holes":
            trimesh.repair.fill_holes(m)
        elif name == "decimate":
            try:
                m = m.simplify_quadric_decimation(face_count=int(val))
            except Exception:  # noqa: BLE001
                m = blender_op(m, "decimate", float(val))
        elif name == "remesh":
            m = blender_op(m, "remesh", float(val))
        elif name == "match_back":
            if texture(m) is None or not match_back(m, float(val)):
                log.append("match_back skipped: no texture or no front/back split"); continue
        elif name == "rotate":
            ax, deg = str(val).split(":")
            m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(float(deg)), _axis(ax)))
        elif name == "mirror":
            s = np.eye(4); i = "xyz".index(str(val).lower()); s[i, i] = -1
            m.apply_transform(s)
            m.invert()
        elif name == "scale":
            m.apply_scale(float(val))
        elif name == "squash":
            ax, k = str(val).split(":"); i = "xyz".index(ax.lower()); c = (m.bounds[0] + m.bounds[1]) / 2
            S = np.eye(4); S[i, i] = float(k); S[i, 3] = c[i] * (1 - float(k)); m.apply_transform(S)
        elif name == "center":
            m.apply_translation(-(m.bounds[0] + m.bounds[1]) / 2)
        elif name == "floor":
            m.apply_translation([0, -m.bounds[0][1], 0])
        elif name == "cut":
            ax, keep, at = str(val).split(":")
            normal = np.array(_axis(ax), float) * (1 if keep == "above" else -1)
            origin = np.array(_axis(ax), float) * float(at)
            m = m.slice_plane(origin, normal, cap=False)
        elif name in ("brightness", "contrast", "saturation", "tint", "texture_size"):
            img = texture(m)
            if img is None:
                log.append(f"{name} skipped: no texture"); continue
            img = img.convert("RGB")
            if name == "brightness": img = ImageEnhance.Brightness(img).enhance(float(val))
            elif name == "contrast": img = ImageEnhance.Contrast(img).enhance(float(val))
            elif name == "saturation": img = ImageEnhance.Color(img).enhance(float(val))
            elif name == "tint":
                hexcol, k = str(val).split(":")
                c = tuple(int(hexcol.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
                img = Image.blend(img, Image.new("RGB", img.size, c), float(k))
            elif name == "texture_size": img = img.resize((int(val), int(val)), Image.LANCZOS)
            set_texture(m, img)
        else:
            log.append(f"unknown op {name}"); continue
        log.append(f"{name} {val if val is not True else ''}".strip() + f": {before} -> {len(m.faces)} tris")
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    m.export(str(dst))
    res = info(dst)
    res["log"] = log
    return res


def main() -> int:
    _reexec_if_needed()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("info"); s.add_argument("mesh", type=Path)
    s = sub.add_parser("preview"); s.add_argument("mesh", type=Path); s.add_argument("png", type=Path); s.add_argument("--size", type=int, default=384)
    s = sub.add_parser("fix"); s.add_argument("src", type=Path); s.add_argument("dst", type=Path); s.add_argument("--preview", type=Path); s.add_argument("--size", type=int, default=384)
    order = []

    class Ordered(argparse.Action):
        def __call__(self, parser, ns, values, option_string=None):
            order.append((self.dest, True if values is None or values == [] else values))

    for flag, has_val in [("drop-small", True), ("keep-largest", False), ("merge", False), ("fill-holes", False), ("decimate", True),
                          ("rotate", True), ("mirror", True), ("scale", True), ("squash", True), ("center", False), ("floor", False), ("cut", True), ("remesh", True), ("match-back", True),
                          ("brightness", True), ("contrast", True), ("saturation", True), ("tint", True), ("texture-size", True)]:
        s.add_argument("--" + flag, dest=flag.replace("-", "_"), action=Ordered, nargs=None if has_val else 0)
    a = ap.parse_args()
    if a.cmd == "info":
        print(json.dumps(info(a.mesh), indent=1))
    elif a.cmd == "preview":
        print(preview(a.mesh, a.png, a.size))
    else:
        res = fix(a.src, a.dst, order)
        if a.preview:
            res["preview"] = str(preview(a.dst, a.preview, a.size))
        print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
