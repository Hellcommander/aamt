#!/usr/bin/env python3
"""
CrossMod ships — 3D mesh first, then Transcendence 2.5D facings.

  1. 3D concept (References/*.png, three-quarter sculpt) → TRELLIS GLB
     The same GLB is copied to Shared/Concepts/meshes for Starfield.
  2. PBR skins via Shared/pbr_skin_generator + Ucupaint bake onto UVs
  3. Orthographic 120-facings via Common/blender_ship_spritesheet_export.py
     (that is the Transcendence 2.5D step — not a 2D concept drawing)

Usage:
  python generate_crossmod_ship_skins.py --out-dir C:\\Output\\SpaceWhale120Facings
  python generate_crossmod_ship_skins.py --out-dir C:\\Output\\SpaceWhale120Facings --ship-id scSpaceWhale
  python generate_crossmod_ship_skins.py --skins-only --out-dir C:\\Output\\SpaceWhale120Facings
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_TOOLS_TX = Path(__file__).resolve().parent
_TOOLS = _TOOLS_TX.parent
_SHARED = _TOOLS / "Shared"
_COMMON = _TOOLS / "Common"
_MESH_SCRIPT = _TOOLS_TX / "blender_crossmod_ship_mesh.py"
_SHEET_SCRIPT = _COMMON / "blender_ship_spritesheet_export.py"
_REGISTRY_FILE = _TOOLS_TX / "crossmod_ship_skins_registry.json"

if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
if str(_TOOLS_TX) not in sys.path:
    sys.path.insert(0, str(_TOOLS_TX))

try:
    import tx_ai_pipeline as tx  # type: ignore
except Exception:
    tx = None  # type: ignore


def _default_ships() -> List[Dict[str, Any]]:
    if _REGISTRY_FILE.is_file():
        data = json.loads(_REGISTRY_FILE.read_text(encoding="utf-8"))
        ships = data.get("ships") or []
        if ships:
            return list(ships)
    return []


DEFAULT_SHIPS: List[Dict[str, Any]] = _default_ships()


def _load_registry(path: Optional[Path]) -> List[Dict[str, Any]]:
    defaults = _default_ships()
    if not path or not path.is_file():
        return list(defaults)
    data = json.loads(path.read_text(encoding="utf-8"))
    ships = data.get("ships") or data
    if not isinstance(ships, list):
        raise ValueError(f"Bad registry: {path}")
    by_id = {s["id"]: s for s in defaults if s.get("id")}
    out = []
    for s in ships:
        base = dict(by_id.get(s.get("id"), {}))
        base.update(s)
        if "name" not in base:
            base["name"] = base.get("id")
        out.append(base)
    return out


def _find_blender(explicit: Optional[str] = None) -> Optional[str]:
    if tx:
        hit = tx.find_blender(explicit)
        if hit:
            return hit
    from mesh_skin_export import find_blender

    return find_blender(explicit)


def generate_skins_for_ship(
    ship: Dict[str, Any],
    skin_dir: Path,
    *,
    quality: str = "standard",
    use_sd: bool = True,
) -> Dict[str, Any]:
    name = ship["name"]
    skin_dir.mkdir(parents=True, exist_ok=True)
    spec = {
        "theme": ship.get("theme") or name,
        "colors": ship.get("colors") or [],
        "pattern": ship.get("pattern") or "organic",
        "style": ship.get("style") or "stylized",
        "description": ship.get("description") or "",
        "glow": True,
    }
    print(f"[skin] {name} quality={quality} use_sd={use_sd} (Shared via tx_ai_pipeline)")
    if tx:
        return tx.generate_pbr_skins(
            skin_dir, name, spec, quality=quality, use_sd=use_sd, glow=True
        )
    from pbr_skin_generator import generate_pbr_skin_set

    paths = generate_pbr_skin_set(
        skin_dir,
        name,
        spec,
        quality=quality,
        use_sd=use_sd,
        glow=True,
    )
    return {k: str(v) for k, v in paths.items()}


def _expand_pose_ships(ships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Expand each hull into per-pose export jobs (pack name = id_pose)."""
    out: List[Dict[str, Any]] = []
    for ship in ships:
        poses = ship.get("poses") or ["idle"]
        base_id = ship.get("id") or ship.get("name")
        base_name = ship.get("name") or base_id
        for pose in poses:
            job = dict(ship)
            job["pose"] = pose
            job["baseId"] = base_id
            job["skinName"] = base_name  # share PBR skins across poses
            job["id"] = f"{base_id}_{pose}" if pose != "idle" else base_id
            job["name"] = f"{base_name}_{pose}" if pose != "idle" else base_name
            out.append(job)
    return out


def build_mesh_fbx(
    ship: Dict[str, Any],
    skin_dir: Path,
    fbx: Path,
    *,
    blender: Optional[str] = None,
) -> int:
    blender_exe = _find_blender(blender)
    if not blender_exe:
        print("[ERROR] Blender not found")
        return 127
    if not _MESH_SCRIPT.is_file():
        print(f"[ERROR] Missing {_MESH_SCRIPT}")
        return 1
    fbx.parent.mkdir(parents=True, exist_ok=True)
    ship_id = str(ship.get("baseId") or ship.get("id") or ship["name"])
    skin_name = str(ship.get("skinName") or ship.get("name"))
    pose = str(ship.get("pose") or "idle")
    args = [
        blender_exe,
        "--background",
        "--python",
        str(_MESH_SCRIPT),
        "--",
        "--ship-id",
        ship_id,
        "--name",
        skin_name,
        "--pose",
        pose,
        "--skin-dir",
        str(skin_dir.resolve()),
        "--fbx",
        str(fbx.resolve()),
    ]
    print(f"[mesh] 3D plate mesh + PBR pose={pose} -> {fbx.name}")
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        # Blender dumps noise to stderr; keep last lines useful
        tail = "\n".join(proc.stderr.strip().splitlines()[-40:])
        if tail:
            print(tail)
    return 0 if fbx.is_file() else (proc.returncode or 1)


def render_120_facings(
    *,
    model_path: Path,
    sheet_path: Path,
    hero_path: Path,
    params: Dict[str, int],
    blender: Optional[str] = None,
) -> int:
    """Same exporter as Export-AamtShipSpritesheet / Commonwealth HD ships."""
    from ship_spritesheet_export import _run_blender_spritesheet

    if not _SHEET_SCRIPT.is_file():
        print(f"[ERROR] Missing {_SHEET_SCRIPT}")
        return 1
    print(
        f"[sheet] Common/blender_ship_spritesheet_export "
        f"{params['facings']} facings @ {params['frame_width']}px"
    )
    return _run_blender_spritesheet(
        model_path=model_path,
        sheet_path=sheet_path,
        hero_path=hero_path,
        params=params,
        blender=blender,
    )


def export_ship_pack(
    ship: Dict[str, Any],
    out_root: Path,
    *,
    quality: str = "standard",
    use_sd: bool = True,
    skins_only: bool = False,
    blender: Optional[str] = None,
    skin_cache: Optional[Dict[str, Path]] = None,
    mesh_source: str = "auto",
) -> Dict[str, Any]:
    name = ship["name"]
    skin_name = str(ship.get("skinName") or name)
    pose = str(ship.get("pose") or "idle")
    pack_dir = out_root / name
    pack_dir.mkdir(parents=True, exist_ok=True)
    # Share skins across poses of the same hull
    if skin_cache is not None and skin_name in skin_cache:
        skin_dir = skin_cache[skin_name]
        skin_meta = {"sharedFrom": str(skin_dir)}
    else:
        skin_dir = pack_dir / "Skins" if pose == "idle" else (out_root / skin_name / "Skins")
        if not (skin_dir / f"{skin_name}_diffuse.png").is_file():
            skin_dir = pack_dir / "Skins"
            skin_meta = generate_skins_for_ship(
                {**ship, "name": skin_name}, skin_dir, quality=quality, use_sd=use_sd
            )
        else:
            skin_meta = {"reused": str(skin_dir)}
        if skin_cache is not None:
            skin_cache[skin_name] = skin_dir

    result: Dict[str, Any] = {
        "id": ship.get("id"),
        "baseId": ship.get("baseId") or ship.get("id"),
        "name": name,
        "pose": pose,
        "skins": skin_meta,
        "pack": str(pack_dir),
        "method": "mesh_pbr_ortho120",  # vanilla path, not sketch
    }
    if skins_only:
        result["ok"] = True
        return result

    mesh_dir = pack_dir / "Meshes"
    mesh_dir.mkdir(parents=True, exist_ok=True)
    fbx = mesh_dir / f"{name}.fbx"
    blend = mesh_dir / f"{name}.blend"
    glb = mesh_dir / f"{name}.glb"
    model_for_sheet: Optional[Path] = None
    want_trellis = mesh_source in ("trellis", "auto") and tx is not None
    if want_trellis:
        theme = ship.get("theme") or name
        desc = ship.get("description") or ""
        prompt = (
            f"{theme}, {desc}, complete 3D capital-ship sculpt, "
            f"three-quarter studio view, single object, organic hull"
        )
        print(f"[mesh] TRELLIS 3D concept→GLB ({name}) — TX 2.5D is 120-facings later")
        concept = tx.resolve_concept_art(ship) if tx else None
        hit = tx.concept_mesh(
            prompt,
            glb,
            concept=concept or (mesh_dir / f"{name}_concept.png"),
            autostart_mesh=True,
            seed=abs(hash(name)) % 10_000_000,
            asset_id=str(ship.get("baseId") or ship.get("id") or name),
        )
        if hit and hit.is_file():
            model_for_sheet = hit
            result["method"] = "trellis_pbr_ortho120"
    if model_for_sheet is None:
        if mesh_source == "trellis":
            result["ok"] = False
            result["error"] = "TRELLIS mesh failed"
            return result
        mesh_code = build_mesh_fbx(ship, Path(skin_dir), fbx, blender=blender)
        result["mesh_exit"] = mesh_code
        # Prefer packed .blend for ortho export so PBR maps survive (FBX often greys out)
        model_for_sheet = blend if blend.is_file() else fbx
    if not model_for_sheet.is_file():
        result["ok"] = False
        result["error"] = "mesh build failed (no .blend/.fbx/.glb)"
        return result
    result["mesh"] = str(model_for_sheet)
    result["blend"] = str(blend) if blend.is_file() else None
    result["glb"] = str(glb) if glb.is_file() else None
    result["skin_dir"] = str(skin_dir)

    if tx and Path(skin_dir).is_dir():
        try:
            baked = tx.bake_onto_mesh(
                model_for_sheet,
                mesh_dir / "Ucupaint",
                skin_dir=skin_dir,
                name=skin_name,
                blender=blender,
                stop_servers=True,
            )
            result["ucupaint"] = baked
            baked_mesh = baked.get("glb") or baked.get("blend")
            if baked_mesh and Path(baked_mesh).is_file():
                model_for_sheet = Path(baked_mesh)
                result["mesh"] = str(model_for_sheet)
                result["method"] = str(result.get("method") or "") + "+ucupaint"
        except Exception as exc:  # noqa: BLE001
            print(f"[ucupaint] bake skipped for {name}: {exc}", file=sys.stderr)

    from ship_spritesheet_export import _resolve_tx_params, preserve_final_model

    fw = int(ship.get("frameWidth") or ship.get("frame_width") or 128)
    columns = int(ship.get("columns") or 12)
    params = _resolve_tx_params(
        {
            "facings": int(ship.get("facings") or 120),
            "columns": columns,
            "frameWidth": fw,
            "frameHeight": fw,
        }
    )
    sheet_path = pack_dir / f"{name}.jpg"
    hero_path = pack_dir / f"{name}Large.jpg"
    mask_path = pack_dir / f"{name}Mask.bmp"

    code = render_120_facings(
        model_path=model_for_sheet,
        sheet_path=sheet_path,
        hero_path=hero_path,
        params=params,
        blender=blender,
    )
    result["spritesheet_exit"] = code
    sheet_ok = code == 0 and sheet_path.is_file()
    if sheet_ok:
        try:
            preserve_final_model(
                pack_dir,
                name,
                blend if blend.is_file() else fbx,
                params=params,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] Source/Models preserve: {exc}")

    result["ok"] = sheet_ok
    files: Dict[str, Any] = {}
    if fbx.is_file():
        files["mesh"] = str(fbx)
    if blend.is_file():
        files["blend"] = str(blend)
    if sheet_path.is_file():
        files["spritesheet"] = str(sheet_path)
    if mask_path.is_file():
        files["spritesheetMask"] = str(mask_path)
    if hero_path.is_file():
        files["hero"] = str(hero_path)
    result["files"] = files

    for key, dest_name in (
        ("spritesheet", f"{name}_120facings.jpg"),
        ("spritesheetMask", f"{name}_120facingsMask.bmp"),
        ("hero", f"{name}Large.jpg"),
    ):
        src = files.get(key)
        if src and Path(src).is_file():
            dest = out_root / dest_name
            shutil.copy2(src, dest)
            result.setdefault("previews", {})[key] = str(dest)

    return result


def run(
    out_dir: Path,
    *,
    ships: List[Dict[str, Any]],
    quality: str = "standard",
    use_sd: bool = True,
    skins_only: bool = False,
    blender: Optional[str] = None,
    expand_poses: bool = True,
    mesh_source: str = "auto",
) -> List[Dict[str, Any]]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = _expand_pose_ships(ships) if expand_poses else list(ships)
    results = []
    skin_cache: Dict[str, Path] = {}
    for ship in jobs:
        sid = ship.get("id") or ship.get("name")
        print(f"\n=== {sid} (pose={ship.get('pose', 'idle')}) ===")
        try:
            results.append(
                export_ship_pack(
                    ship,
                    out_dir,
                    quality=quality,
                    use_sd=use_sd,
                    skins_only=skins_only,
                    blender=blender,
                    skin_cache=skin_cache,
                    mesh_source=mesh_source,
                )
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] {sid}: {exc}")
            results.append({"id": sid, "ok": False, "error": str(exc)})

    manifest = out_dir / "crossmod_ship_skins_manifest.json"
    manifest.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\n[OK] manifest {manifest}")
    return results


def deploy_to_mod_resources(
    out_dir: Path,
    resources_dir: Path,
    results: List[Dict[str, Any]],
) -> int:
    """Copy generated JPG + Mask.bmp into CrossMod Resources/OrganicHulls/."""
    resources_dir = Path(resources_dir)
    resources_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for r in results:
        if not r.get("ok"):
            continue
        files = r.get("files") or {}
        name = r.get("name")
        sheet = files.get("spritesheet")
        mask = files.get("spritesheetMask")
        if sheet and Path(sheet).is_file():
            dest = resources_dir / f"{name}.jpg"
            shutil.copy2(sheet, dest)
            n += 1
        if mask and Path(mask).is_file():
            dest = resources_dir / f"{name}Mask.bmp"
            shutil.copy2(mask, dest)
            n += 1
        hero = files.get("hero")
        if hero and Path(hero).is_file():
            shutil.copy2(hero, resources_dir / f"{name}Large.jpg")
            n += 1
    print(f"[OK] deployed {n} files -> {resources_dir}")
    return n


def main() -> int:
    ap = argparse.ArgumentParser(
        description="CrossMod ships: PBR skins → 3D mesh → ortho 120-facings (no sketches)"
    )
    ap.add_argument("--out-dir", default=r"C:\Output\SpaceWhale120Facings")
    ap.add_argument("--registry", default=str(_REGISTRY_FILE))
    ap.add_argument("--ship-id", action="append", default=[])
    ap.add_argument(
        "--quality",
        choices=("draft", "standard", "high", "ultra"),
        default="standard",
    )
    ap.add_argument(
        "--use-sd",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Use local SD for diffuse skins when server is up (default: true)",
    )
    ap.add_argument("--skins-only", action="store_true")
    ap.add_argument("--blender", default=None)
    ap.add_argument(
        "--mesh-source",
        choices=("auto", "blender", "trellis"),
        default="auto",
        help="auto uses TRELLIS if already up, else blender_crossmod_ship_mesh",
    )
    ap.add_argument(
        "--deploy-resources",
        default="",
        help="Copy sheets into this Resources folder after generate",
    )
    ap.add_argument("--no-expand-poses", action="store_true")
    args = ap.parse_args()

    ships = _load_registry(Path(args.registry) if args.registry else None)
    if args.ship_id:
        want = set(args.ship_id)
        ships = [
            s
            for s in ships
            if s.get("id") in want
            or s.get("name") in want
            or any(f"{s.get('id')}_{p}" in want for p in (s.get("poses") or []))
        ]
    if not ships:
        print("[ERROR] No ships in registry")
        return 1

    if tx:
        tx.print_probe()
    session_cm = tx.session() if (tx and args.use_sd) else None
    try:
        if session_cm:
            session_cm.__enter__()
        results = run(
            Path(args.out_dir),
            ships=ships,
            quality=args.quality,
            use_sd=args.use_sd,
            skins_only=args.skins_only,
            blender=args.blender,
            expand_poses=not args.no_expand_poses,
            mesh_source=args.mesh_source,
        )
    finally:
        if session_cm:
            session_cm.__exit__(None, None, None)
    if args.deploy_resources:
        deploy_to_mod_resources(Path(args.out_dir), Path(args.deploy_resources), results)
    ok = sum(1 for r in results if r.get("ok"))
    print(f"Done: {ok}/{len(results)} ok (mesh+PBR+ortho120)")
    return 0 if ok == len(results) and results else 1


if __name__ == "__main__":
    raise SystemExit(main())
