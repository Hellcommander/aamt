#!/usr/bin/env python3
"""Elin + Starfield dual asset pipeline (Cursor concepts -> TRELLIS -> Unity/SF).

Stages:
  1. Stage Cursor-generated PNGs from the chat assets folder into
     Tools/Elin/Output/Concepts/{Hero,Icons,UI}
  2. Copy hero concepts into Shared/Concepts and Starfield ArcaneConduit Concepts
  3. TRELLIS image->GLB (Shared/Concepts/meshes/elin{System}.glb)
  4. Publish GLB to Starfield ArcaneConduit Assets/Transcendence
  5. Convert GLB->FBX via Blender and install under Elin Assets/Resources/{System}
  6. Write Unity .meta files

  python elin_trellis_unity.py stage
  python elin_trellis_unity.py publish-concepts
  python elin_trellis_unity.py trellis --id DragonMagic
  python elin_trellis_unity.py trellis --all --keep
  python elin_trellis_unity.py deploy-elin --id DragonMagic
  python elin_trellis_unity.py deploy-ui
  python elin_trellis_unity.py status
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_ELIN = Path(__file__).resolve().parent
_TOOLS = _ELIN.parent
_SHARED = _TOOLS / "Shared"
for _p in (_ELIN, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

_CATALOG = _ELIN / "elin_asset_catalog.json"
_BLENDER_GLB = _ELIN / "blender_glb_to_unity.py"


def load_catalog() -> Dict[str, Any]:
    return json.loads(_CATALOG.read_text(encoding="utf-8"))


def cfg_paths(cat: Dict[str, Any]) -> Dict[str, Path]:
    sf = cat.get("starfield") or {}
    return {
        "mod": Path(cat["modPath"]),
        "out": Path(cat["outputRoot"]),
        "cursor": Path(cat.get("cursorAssetsDir") or ""),
        "sf_assets": Path(sf["assets"]),
        "sf_concepts": Path(sf["concepts"]),
        "shared_meshes": Path(sf["sharedMeshes"]),
        "shared_concepts": Path(sf["sharedConcepts"]),
    }


def asset_id(system_id: str) -> str:
    return "elin" + system_id


def stage_cursor_assets(cat: Dict[str, Any]) -> Dict[str, int]:
    paths = cfg_paths(cat)
    src = paths["cursor"]
    out = paths["out"]
    hero_dir = out / "Concepts" / "Hero"
    icon_dir = out / "Concepts" / "Icons"
    ui_dir = out / "Concepts" / "UI"
    for d in (hero_dir, icon_dir, ui_dir):
        d.mkdir(parents=True, exist_ok=True)
    counts = {"hero": 0, "icon": 0, "ui": 0, "other": 0}
    if not src.is_dir():
        print(f"[stage] cursor assets dir missing: {src}")
        return counts
    for png in src.glob("elin_*.png"):
        name = png.name
        if "_concept" in name:
            dest = hero_dir / name
            kind = "hero"
        elif "_ui_" in name or name.startswith("elin_ui_"):
            dest = ui_dir / name
            kind = "ui"
        elif name.endswith("_icon.png") or "_icon." in name:
            dest = icon_dir / name
            kind = "icon"
        else:
            dest = out / "Concepts" / name
            kind = "other"
        shutil.copy2(png, dest)
        counts[kind] = counts.get(kind, 0) + 1
        print(f"[stage] {kind}: {dest.name}")
    return counts


def publish_concepts(cat: Dict[str, Any], system_ids: Optional[List[str]] = None) -> int:
    paths = cfg_paths(cat)
    hero_dir = paths["out"] / "Concepts" / "Hero"
    paths["shared_concepts"].mkdir(parents=True, exist_ok=True)
    paths["sf_concepts"].mkdir(parents=True, exist_ok=True)
    n = 0
    heroes = cat.get("heroes") or []
    for h in heroes:
        hid = h["id"]
        if system_ids and hid not in system_ids:
            continue
        src = hero_dir / f"elin_{hid}_concept.png"
        if not src.is_file():
            # also accept without elin_ prefix
            alt = hero_dir / f"{hid}_concept.png"
            src = alt if alt.is_file() else src
        if not src.is_file():
            print(f"[concepts] missing {hid}")
            continue
        aid = asset_id(hid)
        shared = paths["shared_concepts"] / f"{aid}.png"
        sf = paths["sf_concepts"] / f"{aid}.png"
        shutil.copy2(src, shared)
        shutil.copy2(src, sf)
        # keep a sidecar for spell bridge asset_hint
        meta = {
            "id": aid,
            "system": hid,
            "elinSystem": h.get("elinSystem"),
            "sfSchool": h.get("sfSchool"),
            "prop": h.get("prop"),
            "concept": str(shared),
            "consumers": ["Elin CustomRaceClassCreator", "Starfield ArcaneConduit"],
        }
        (paths["shared_concepts"] / f"{aid}.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        print(f"[concepts] {aid} -> Shared + Starfield")
        n += 1
    # update Shared Concepts index if present
    index = paths["shared_concepts"] / "index.json"
    concepts_map: Dict[str, str] = {}
    if index.is_file():
        try:
            concepts_map = dict((json.loads(index.read_text(encoding="utf-8")).get("concepts") or {}))
        except Exception:
            concepts_map = {}
    for h in heroes:
        aid = asset_id(h["id"])
        if (paths["shared_concepts"] / f"{aid}.png").is_file():
            concepts_map[aid] = f"{aid}.png"
    index.write_text(json.dumps({"concepts": concepts_map}, indent=2), encoding="utf-8")
    return n


def run_trellis(cat: Dict[str, Any], system_id: str, *, keep: bool = False) -> Optional[Path]:
    paths = cfg_paths(cat)
    aid = asset_id(system_id)
    concept = paths["shared_concepts"] / f"{aid}.png"
    if not concept.is_file():
        local = paths["out"] / "Concepts" / "Hero" / f"elin_{system_id}_concept.png"
        if local.is_file():
            paths["shared_concepts"].mkdir(parents=True, exist_ok=True)
            shutil.copy2(local, concept)
        else:
            print(f"[trellis] no concept for {system_id}")
            return None
    out_glb = paths["shared_meshes"] / f"{aid}.glb"
    out_glb.parent.mkdir(parents=True, exist_ok=True)
    if out_glb.is_file() and out_glb.stat().st_size >= 400_000:
        print(f"[trellis] skip existing {out_glb.name} ({out_glb.stat().st_size} bytes)")
        sf_glb = paths["sf_assets"] / f"{aid}.glb"
        paths["sf_assets"].mkdir(parents=True, exist_ok=True)
        shutil.copy2(out_glb, sf_glb)
        return out_glb
    if keep:
        os.environ["AAMT_TRELLIS_KEEP_SERVER"] = "1"
    from ai_resources import ensure, make_mesh

    print(f"[trellis] ensure mesh stage for {aid}")
    ensure("mesh", wait=2400.0)
    print(f"[trellis] {concept.name} -> {out_glb}")
    make_mesh(concept, out_glb, resolution=512, mesh_simplify=80, texture_size=1024)
    if not out_glb.is_file():
        return None
    # Starfield publish
    paths["sf_assets"].mkdir(parents=True, exist_ok=True)
    sf_glb = paths["sf_assets"] / f"{aid}.glb"
    shutil.copy2(out_glb, sf_glb)
    meta = {
        "id": aid,
        "glb": str(out_glb),
        "starfieldProject": str(sf_glb),
        "bytes": out_glb.stat().st_size,
        "system": system_id,
        "consumers": [
            "Elin CustomRaceClassCreator Unity FBX",
            "Starfield ArcaneConduit mesh/NIF convert",
        ],
    }
    out_glb.with_suffix(".json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    sf_glb.with_suffix(".json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[trellis] published Starfield {sf_glb}")
    return out_glb


def _find_blender() -> Optional[str]:
    from tool_paths import find_blender

    return find_blender()


def glb_to_fbx_and_skins(glb: Path, fbx: Path, skin_dir: Path, name: str) -> bool:
    blender = _find_blender()
    if not blender:
        print("[deploy] Blender not found")
        return False
    skin_dir.mkdir(parents=True, exist_ok=True)
    fbx.parent.mkdir(parents=True, exist_ok=True)
    cfg = {
        "glb": str(glb),
        "fbx": str(fbx),
        "skin_dir": str(skin_dir),
        "name": name,
    }
    cfg_path = fbx.with_suffix(".aamt_glb.json")
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    script = _BLENDER_GLB
    if not script.is_file():
        print(f"[deploy] missing {script}")
        return False
    cmd = [blender, "--background", "--python", str(script), "--", str(cfg_path)]
    print(f"[deploy] blender glb->fbx {name}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stdout[-800:] if proc.stdout else "")
        print(proc.stderr[-800:] if proc.stderr else "", file=sys.stderr)
        return False
    return fbx.is_file()


def deploy_elin_system(cat: Dict[str, Any], system_id: str) -> bool:
    paths = cfg_paths(cat)
    aid = asset_id(system_id)
    mod = paths["mod"]
    glb = paths["shared_meshes"] / f"{aid}.glb"
    if not glb.is_file():
        print(f"[deploy-elin] missing GLB {glb}")
        return False
    res = mod / "Assets" / "Resources" / system_id
    mesh_dir = res / "Meshes"
    skin_dir = res / "Textures" / "Skins"
    concept_dir = res / "Concepts"
    icon_dir = res / "Icons"
    tex_dir = res / "Textures"
    for d in (mesh_dir, skin_dir, concept_dir, icon_dir, tex_dir):
        d.mkdir(parents=True, exist_ok=True)

    # concept
    concept_src = paths["shared_concepts"] / f"{aid}.png"
    if concept_src.is_file():
        shutil.copy2(concept_src, concept_dir / f"{system_id}_concept.png")
        shutil.copy2(concept_src, icon_dir / f"{system_id}_icon.png")

    fbx = mesh_dir / f"{system_id}.fbx"
    ok = glb_to_fbx_and_skins(glb, fbx, skin_dir, system_id)
    # also keep glb for tooling
    shutil.copy2(glb, mesh_dir / f"{system_id}.glb")

    try:
        from unity_meta import write_model_meta, write_texture_meta

        if fbx.is_file():
            write_model_meta(fbx, overwrite=True)
        for png in list(skin_dir.glob("*.png")) + list(icon_dir.glob("*.png")) + list(concept_dir.glob("*.png")):
            kind = "sprite" if "icon" in png.name.lower() or "concept" in png.name.lower() else "default"
            if "normal" in png.name.lower():
                kind = "normal"
            write_texture_meta(png, kind=kind, overwrite=True)
    except Exception as exc:
        print(f"[deploy-elin] meta warn: {exc}")
    print(f"[deploy-elin] {system_id} ok={ok}")
    return ok


def deploy_ui(cat: Dict[str, Any]) -> int:
    paths = cfg_paths(cat)
    ui_src = paths["out"] / "Concepts" / "UI"
    dest = paths["mod"] / "Assets" / "Resources" / "UI" / "Textures" / "Chrome"
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for png in ui_src.glob("elin_ui_*.png"):
        target = dest / png.name.replace("elin_", "", 1)
        shutil.copy2(png, target)
        try:
            from unity_meta import write_texture_meta

            write_texture_meta(target, kind="gui", overwrite=True)
        except Exception:
            pass
        n += 1
        print(f"[ui] {target.name}")
    # also publish UI concepts to Starfield art folder for reference
    sf_ui = paths["sf_concepts"] / "ElinUI"
    sf_ui.mkdir(parents=True, exist_ok=True)
    for png in ui_src.glob("elin_ui_*.png"):
        shutil.copy2(png, sf_ui / png.name)
    return n


def deploy_icons(cat: Dict[str, Any]) -> int:
    """Copy Cursor system icons into each Elin Resources/{System}/Icons folder."""
    paths = cfg_paths(cat)
    icon_src = paths["out"] / "Concepts" / "Icons"
    n = 0
    if not icon_src.is_dir():
        return 0
    for png in icon_src.glob("elin_*_icon.png"):
        # elin_DragonMagic_icon.png -> DragonMagic
        stem = png.stem  # elin_DragonMagic_icon
        parts = stem.split("_")
        if len(parts) < 3:
            continue
        system = parts[1]
        # handle multi-part? elin_ArcaneSaturation_icon -> ArcaneSaturation
        # filename pattern elin_{System}_icon
        system = stem[len("elin_") : -len("_icon")]
        dest_dir = paths["mod"] / "Assets" / "Resources" / system / "Icons"
        dest_dir.mkdir(parents=True, exist_ok=True)
        target = dest_dir / f"{system}_icon.png"
        shutil.copy2(png, target)
        try:
            from unity_meta import write_texture_meta

            write_texture_meta(target, kind="sprite", overwrite=True)
        except Exception:
            pass
        # Starfield reference copy beside concept
        aid = asset_id(system)
        sf_icon = paths["sf_concepts"] / f"{aid}_icon.png"
        shutil.copy2(png, sf_icon)
        n += 1
        print(f"[icon] {system} -> {target}")
    return n


def status(cat: Dict[str, Any]) -> None:
    paths = cfg_paths(cat)
    heroes = cat.get("heroes") or []
    print(f"heroes catalogued: {len(heroes)}")
    for h in heroes:
        hid = h["id"]
        aid = asset_id(hid)
        concept = (paths["out"] / "Concepts" / "Hero" / f"elin_{hid}_concept.png").is_file()
        shared = (paths["shared_concepts"] / f"{aid}.png").is_file()
        glb = (paths["shared_meshes"] / f"{aid}.glb").is_file()
        fbx = (paths["mod"] / "Assets" / "Resources" / hid / "Meshes" / f"{hid}.fbx").is_file()
        print(f"  {hid:<20} concept={int(concept)} shared={int(shared)} glb={int(glb)} fbx={int(fbx)}")
    ui_n = len(list((paths["out"] / "Concepts" / "UI").glob("*.png"))) if (paths["out"] / "Concepts" / "UI").is_dir() else 0
    print(f"staged UI pngs: {ui_n}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("stage")
    sub.add_parser("publish-concepts")
    sub.add_parser("status")
    sub.add_parser("deploy-ui")
    sub.add_parser("deploy-icons")
    p_t = sub.add_parser("trellis")
    p_t.add_argument("--id", action="append", default=[])
    p_t.add_argument("--all", action="store_true")
    p_t.add_argument("--keep", action="store_true", help="keep TRELLIS server between jobs")
    p_d = sub.add_parser("deploy-elin")
    p_d.add_argument("--id", action="append", default=[])
    p_d.add_argument("--all", action="store_true")
    args = ap.parse_args()
    cat = load_catalog()

    if args.cmd == "stage":
        print(stage_cursor_assets(cat))
        return 0
    if args.cmd == "publish-concepts":
        print("published", publish_concepts(cat))
        return 0
    if args.cmd == "status":
        status(cat)
        return 0
    if args.cmd == "deploy-ui":
        print("ui", deploy_ui(cat))
        return 0
    if args.cmd == "deploy-icons":
        print("icons", deploy_icons(cat))
        return 0
    if args.cmd == "trellis":
        ids = list(args.id)
        if args.all:
            ids = [h["id"] for h in cat.get("heroes") or []]
        if not ids:
            print("provide --id or --all")
            return 1
        if args.keep:
            os.environ["AAMT_TRELLIS_KEEP_SERVER"] = "1"
        ok = 0
        try:
            for hid in ids:
                if run_trellis(cat, hid, keep=args.keep):
                    ok += 1
        finally:
            if args.keep:
                try:
                    from trellis_http_client import stop_server

                    stop_server(force=True)
                except Exception:
                    pass
                os.environ.pop("AAMT_TRELLIS_KEEP_SERVER", None)
        print(f"trellis done {ok}/{len(ids)}")
        return 0 if ok else 1
    if args.cmd == "deploy-elin":
        ids = list(args.id)
        if args.all:
            ids = [h["id"] for h in cat.get("heroes") or []]
        ok = sum(1 for hid in ids if deploy_elin_system(cat, hid))
        print(f"deploy-elin {ok}/{len(ids)}")
        return 0 if ok else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
