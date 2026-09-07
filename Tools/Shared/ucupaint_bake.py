#!/usr/bin/env python3
"""Headless Ucupaint bake: real maps onto a mesh's UVs.

This is the layering/bake stage of the Shared pipeline. It does **not** invent
procedural noise textures. It composites SD / Material Maker / TRELLIS images
as Ucupaint layers, optionally bakes mesh AO, then bakes the stack to UV PNGs.

Run inside Blender:

  blender --background --python ucupaint_bake.py -- ^
      --mesh ship.glb --out-dir out --size 1024 ^
      --color diffuse.png --roughness rough.png --metallic metal.png --normal nrm.png

Host Python should call ``ucupaint_support.bake_onto_mesh`` instead of this file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import bpy

CHANNEL_ALIASES = {
    "color": ("color", "colour", "diffuse", "albedo", "base color", "basecolor"),
    "metallic": ("metallic", "metalness", "metal"),
    "roughness": ("roughness", "rough"),
    "normal": ("normal", "nrm", "nor", "height"),
}


def _patch_ucupaint_headless() -> None:
    """Blender 5.x background has no VIEW_3D space; EXEC_DEFAULT skips invoke.

    Ucupaint 2.4.9 then crashes on ``space.type`` and unset ``no_layer_using``.
    Also rebind names imported into Bake / BakeToLayer modules.
    """
    try:
        import ucupaint.bake_common as bake_common

        orig_remember = bake_common.remember_before_bake

        def remember_before_bake(yp=None, mat=None):  # type: ignore[no-untyped-def]
            # Guard the common headless crash before calling upstream.
            space = getattr(bpy.context, "space_data", None)
            if space is None:
                # Temporarily install a dummy space_data-less safe path by
                # monkeypatching the attribute access inside a shallow fork.
                scene = bpy.context.scene
                obj = bpy.context.object
                uv_layers = getattr(getattr(obj, "data", None), "uv_layers", None) if obj else None
                book = {
                    "ori_bake_margin": getattr(scene.render, "bake_margin", 0) if scene else 0,
                    "ori_active_uv": uv_layers.active.name if uv_layers and uv_layers.active else "",
                    "ori_active_render_uv": uv_layers.active.name if uv_layers and uv_layers.active else "",
                    "ori_space_local_view": None,
                    "ori_space_view_matrix": None,
                    "ori_hide_selects": [],
                    "ori_active_selected_objs": list(bpy.context.selected_objects) if bpy.context.selected_objects else [],
                    "ori_hide_renders": [],
                    "ori_hide_viewports": [],
                    "ori_hide_objs": [],
                    "ori_layer_col_hide_viewport": [],
                    "ori_layer_col_exclude": [],
                    "ori_col_hide_viewport": [],
                }
                try:
                    return orig_remember(yp, mat=mat)
                except Exception:
                    return book
            return orig_remember(yp, mat=mat)

        bake_common.remember_before_bake = remember_before_bake  # type: ignore[assignment]
        for mod_name in ("ucupaint.Bake", "ucupaint.BakeToLayer"):
            mod = sys.modules.get(mod_name)
            if mod is not None and hasattr(mod, "remember_before_bake"):
                setattr(mod, "remember_before_bake", remember_before_bake)

        orig_prepare = bake_common.prepare_bake_settings

        def prepare_bake_settings(*args, **kwargs):  # type: ignore[no-untyped-def]
            space = getattr(bpy.context, "space_data", None)
            if space is None:
                # Skip viewport-local view tweaks in background mode.
                class _NullSpace:
                    type = None
                    local_view = None

                    class region_3d:  # noqa: N801
                        view_matrix = None

                class _Ctx:
                    pass

                # Fall through to original; addon file may already be patched.
            return orig_prepare(*args, **kwargs)

        bake_common.prepare_bake_settings = prepare_bake_settings  # type: ignore[assignment]
        for mod_name in ("ucupaint.Bake", "ucupaint.BakeToLayer"):
            mod = sys.modules.get(mod_name)
            if mod is not None and hasattr(mod, "prepare_bake_settings"):
                setattr(mod, "prepare_bake_settings", prepare_bake_settings)
    except Exception as exc:
        print(f"[ucupaint] headless remember patch skipped: {exc}")

    try:
        from ucupaint.Bake import YBakeChannels

        orig_execute = YBakeChannels.execute

        def execute(self, context):  # type: ignore[no-untyped-def]
            if not hasattr(self, "no_layer_using"):
                self.no_layer_using = False
            if not hasattr(self, "enable_bake_as_vcol"):
                self.enable_bake_as_vcol = False
            return orig_execute(self, context)

        YBakeChannels.execute = execute  # type: ignore[method-assign]
    except Exception as exc:
        print(f"[ucupaint] headless bake_channels patch skipped: {exc}")


def _argv() -> list[str]:
    argv = sys.argv
    return argv[argv.index("--") + 1 :] if "--" in argv else argv[1:]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ucupaint bake real textures onto mesh UVs")
    p.add_argument("--mesh", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--size", type=int, default=1024)
    p.add_argument("--color", default="")
    p.add_argument("--diffuse", default="", help="Alias for --color")
    p.add_argument("--roughness", default="")
    p.add_argument("--metallic", default="")
    p.add_argument("--normal", default="")
    p.add_argument("--emission", default="")
    p.add_argument("--ao", action="store_true", help="Bake mesh AO as a multiply layer")
    p.add_argument("--no-ao", action="store_true")
    p.add_argument("--export-glb", default="")
    p.add_argument("--export-blend", default="")
    p.add_argument("--name", default="")
    return p.parse_args(argv if argv is not None else _argv())


def _select(obj) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def _clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def _import_mesh(path: Path) -> None:
    ext = path.suffix.lower()
    fp = str(path)
    if ext in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=fp)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=fp)
    elif ext == ".obj":
        if hasattr(bpy.ops.wm, "obj_import"):
            bpy.ops.wm.obj_import(filepath=fp)
        else:
            bpy.ops.import_scene.obj(filepath=fp)
    elif ext == ".blend":
        bpy.ops.wm.open_mainfile(filepath=fp)
    else:
        raise RuntimeError(f"unsupported mesh type: {ext}")


def _largest_mesh():
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH" and o.data and o.data.polygons]
    if not meshes:
        raise RuntimeError("no mesh objects after import")
    return max(meshes, key=lambda o: len(o.data.polygons))


def _join_meshes(keep) -> object:
    others = [o for o in bpy.context.scene.objects if o.type == "MESH" and o != keep]
    if not others:
        _select(keep)
        return keep
    _select(keep)
    for o in others:
        o.select_set(True)
    bpy.ops.object.join()
    return bpy.context.view_layer.objects.active


def _ensure_uv(obj) -> str:
    uvs = obj.data.uv_layers
    if uvs:
        uvs.active = uvs[0]
        uvs[0].active_render = True
        return uvs[0].name
    _select(obj)
    if obj.mode != "EDIT":
        bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=1.15192, island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")
    if not obj.data.uv_layers:
        raise RuntimeError("UV unwrap failed")
    obj.data.uv_layers[0].active_render = True
    return obj.data.uv_layers[0].name


def _cycles(gpu: bool = True) -> None:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    cyc = scene.cycles
    cyc.samples = 8
    if gpu:
        try:
            cyc.device = "GPU"
            prefs = bpy.context.preferences.addons.get("cycles")
            if prefs:
                cp = prefs.preferences
                for kind in ("OPTIX", "CUDA", "HIP"):
                    try:
                        cp.compute_device_type = kind
                        cp.get_devices()
                        break
                    except Exception:
                        continue
                for d in getattr(cp, "devices", []):
                    d.use = True
        except Exception:
            cyc.device = "CPU"
    else:
        cyc.device = "CPU"


def _enable_ucupaint() -> None:
    shared = os.path.abspath(os.path.join(os.path.dirname(__file__)))
    if shared not in sys.path:
        sys.path.insert(0, shared)
    from ucupaint_support import ensure_enabled

    if not ensure_enabled():
        raise RuntimeError("Ucupaint add-on failed to enable")
    addon = bpy.context.preferences.addons.get("ucupaint")
    if addon and hasattr(addon, "preferences"):
        try:
            addon.preferences.skip_property_popups = True
        except Exception:
            pass


def _channel_index(yp, kind: str) -> int:
    aliases = CHANNEL_ALIASES.get(kind, (kind,))
    for i, ch in enumerate(yp.channels):
        name = (ch.name or "").strip().lower()
        if name in aliases:
            return i
    if kind == "color" and yp.channels:
        return 0
    return -1


def _load_image(path: Path, *, non_color: bool) -> object:
    img = bpy.data.images.load(str(path), check_existing=True)
    if non_color and hasattr(img, "colorspace_settings"):
        try:
            img.colorspace_settings.name = "Non-Color"
        except Exception:
            pass
    return img


def _add_image_layer(group_tree, uv_name: str, image, channel_idx: int, *, is_normal: bool) -> None:
    from ucupaint.Layer import add_new_layer
    from ucupaint.node_arrangements import rearrange_yp_nodes
    from ucupaint.node_connections import reconnect_yp_nodes

    add_new_layer(
        group_tree,
        image.name,
        "IMAGE",
        channel_idx,
        "MIX",
        "MIX",
        "NORMAL_MAP" if is_normal else "BUMP_MAP",
        "UV",
        uv_name=uv_name,
        image=image,
        interpolation="Linear",
        normal_space="TANGENT",
    )
    reconnect_yp_nodes(group_tree)
    rearrange_yp_nodes(group_tree)


def _save_baked(out_dir: Path, stem: str) -> dict[str, str]:
    from ucupaint.common import get_active_ypaint_node

    node = get_active_ypaint_node()
    if not node:
        return {}
    tree = node.node_tree
    yp = tree.yp
    written: dict[str, str] = {}
    out_dir.mkdir(parents=True, exist_ok=True)

    kind_of = {}
    for kind in CHANNEL_ALIASES:
        idx = _channel_index(yp, kind)
        if idx >= 0:
            kind_of[yp.channels[idx].name] = kind

    for ch in yp.channels:
        baked = tree.nodes.get(ch.baked)
        if not baked or not baked.image:
            continue
        image = baked.image
        kind = kind_of.get(ch.name, ch.name.lower().replace(" ", "_"))
        dest = out_dir / f"{stem}_{kind}.png"
        image.filepath_raw = str(dest)
        image.file_format = "PNG"
        try:
            image.save()
        except Exception:
            image.save_render(str(dest))
        written[kind] = str(dest)
        print(f"[ucupaint] baked {kind}: {dest}")
    return written


def _apply_principled(obj, maps: dict[str, str]) -> None:
    mat = obj.active_material
    if not mat:
        mat = bpy.data.materials.new(obj.name + "_PBR")
        mat.use_nodes = True
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    bsdf = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
    if not bsdf:
        return

    def tex(path: str, y: float, non_color: bool):
        if not path or not Path(path).is_file():
            return None
        n = nodes.new("ShaderNodeTexImage")
        n.location = (-600, y)
        n.image = bpy.data.images.load(path, check_existing=True)
        if non_color:
            try:
                n.image.colorspace_settings.name = "Non-Color"
            except Exception:
                pass
        return n

    color = maps.get("color") or maps.get("diffuse")
    t = tex(color or "", 200, False)
    if t and "Base Color" in bsdf.inputs:
        links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    t = tex(maps.get("roughness") or "", -50, True)
    if t and "Roughness" in bsdf.inputs:
        links.new(t.outputs["Color"], bsdf.inputs["Roughness"])
    t = tex(maps.get("metallic") or "", -200, True)
    if t and "Metallic" in bsdf.inputs:
        links.new(t.outputs["Color"], bsdf.inputs["Metallic"])
    t = tex(maps.get("normal") or "", -350, True)
    if t and "Normal" in bsdf.inputs:
        nmap = nodes.new("ShaderNodeNormalMap")
        nmap.location = (-250, -350)
        links.new(t.outputs["Color"], nmap.inputs["Color"])
        links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    t = tex(maps.get("emission") or "", 400, False)
    if t:
        key = "Emission Color" if "Emission Color" in bsdf.inputs else ("Emission" if "Emission" in bsdf.inputs else "")
        if key:
            links.new(t.outputs["Color"], bsdf.inputs[key])
            if "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Strength"].default_value = 1.5


def run(args: argparse.Namespace) -> dict:
    mesh = Path(args.mesh)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.name or mesh.stem
    size = max(64, int(args.size))
    color = args.color or args.diffuse
    maps_in = {
        "color": color,
        "roughness": args.roughness,
        "metallic": args.metallic,
        "normal": args.normal,
        "emission": args.emission,
    }
    maps_in = {k: v for k, v in maps_in.items() if v and Path(v).is_file()}
    if not maps_in:
        raise RuntimeError("no real texture maps given (refusing procedural bake)")

    if mesh.suffix.lower() != ".blend":
        _clear_scene()
    _import_mesh(mesh)
    obj = _join_meshes(_largest_mesh())
    _select(obj)
    obj.hide_set(False)
    obj.hide_render = False
    uv_name = _ensure_uv(obj)
    if not obj.data.materials:
        mat = bpy.data.materials.new(stem + "_Mat")
        mat.use_nodes = True
        obj.data.materials.append(mat)
    obj.active_material_index = 0

    _enable_ucupaint()
    _patch_ucupaint_headless()
    _cycles(gpu=True)

    bpy.ops.wm.y_quick_ypaint_node_setup(
        "EXEC_DEFAULT",
        type="BSDF_PRINCIPLED",
        color=True,
        metallic=True,
        roughness=True,
        normal=True,
        alpha=False,
        ao=False,
        switch_to_material_view=False,
    )

    from ucupaint.common import get_active_ypaint_node

    node = get_active_ypaint_node()
    if not node:
        raise RuntimeError("Ucupaint node setup failed")
    yp = node.node_tree.yp

    for kind, path in maps_in.items():
        if kind == "emission":
            continue
        idx = _channel_index(yp, kind)
        if idx < 0:
            print(f"[ucupaint] no {kind} channel; skip {path}")
            continue
        img = _load_image(Path(path), non_color=(kind != "color"))
        _add_image_layer(node.node_tree, uv_name, img, idx, is_normal=(kind == "normal"))
        print(f"[ucupaint] layer {kind}: {path}")

    do_ao = bool(args.ao) and not args.no_ao
    if do_ao:
        try:
            bpy.ops.wm.y_bake_to_layer(
                "EXEC_DEFAULT",
                type="AO",
                name="AO",
                target_type="LAYER",
                blend_type="MULTIPLY",
                width=size,
                height=size,
                use_custom_resolution=True,
                samples=16,
                uv_map=uv_name,
                bake_device="GPU",
            )
        except Exception as exc:
            print(f"[ucupaint] AO bake skipped: {exc}")

    bake_kw = dict(
        width=size,
        height=size,
        use_custom_resolution=True,
        uv_map=uv_name,
        samples=8,
        fxaa=True,
        aa_level=1,
        only_active_channel=False,
    )
    baked_ok = False
    for device in ("GPU", "CPU"):
        try:
            bpy.ops.wm.y_bake_channels("EXEC_DEFAULT", bake_device=device, **bake_kw)
            baked_ok = True
            print(f"[ucupaint] channels baked on {device}")
            break
        except Exception as exc:
            print(f"[ucupaint] bake_channels {device} failed: {exc}")
    if not baked_ok:
        raise RuntimeError("Ucupaint bake_channels failed")

    written = _save_baked(out_dir, stem)
    if args.emission and Path(args.emission).is_file():
        dest = out_dir / f"{stem}_emission.png"
        if not dest.exists():
            import shutil

            shutil.copy2(args.emission, dest)
        written["emission"] = str(dest)

    _apply_principled(obj, written)

    glb = Path(args.export_glb) if args.export_glb else out_dir / f"{stem}_baked.glb"
    blend = Path(args.export_blend) if args.export_blend else out_dir / f"{stem}_baked.blend"
    glb.parent.mkdir(parents=True, exist_ok=True)
    _select(obj)
    try:
        bpy.ops.export_scene.gltf(
            filepath=str(glb),
            export_format="GLB",
            use_selection=True,
            export_materials="EXPORT",
        )
        print(f"[ucupaint] glb {glb}")
    except Exception as exc:
        print(f"[ucupaint] glb export failed: {exc}")
        glb = Path()
    try:
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        print(f"[ucupaint] blend {blend}")
    except Exception as exc:
        print(f"[ucupaint] blend save failed: {exc}")
        blend = Path()

    report = {
        "ok": bool(written),
        "maps": written,
        "glb": str(glb) if glb and glb.is_file() else "",
        "blend": str(blend) if blend and blend.is_file() else "",
        "uv": uv_name,
        "size": size,
    }
    (out_dir / f"{stem}_ucupaint.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


def main() -> int:
    try:
        run(parse_args())
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
