#!/usr/bin/env python3
"""SD PBR skins → Ucupaint bake → Starfield DDS/MAT for concept meshes.

Phases (one GPU):
  1) SD skins for all ids (KEEP_SERVER)
  2) Stop SD
  3) Ucupaint bake onto each GLB
  4) texconv DDS + clone .mat into Starfield

  python tx_concept_texture_batch.py
  python tx_concept_texture_batch.py --id scSpaceWhale --skip-bake
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional

_TX = Path(__file__).resolve().parent
_TOOLS = _TX.parent
_SHARED = _TOOLS / "Shared"
_MESH_DIR = _SHARED / "Concepts" / "meshes"
_INDEX = _SHARED / "Concepts" / "index.json"
_OUT = _TX / "Output" / "HdPipeline"
_SF_ROOT = Path(r"F:\SteamLibrary\steamapps\common\Starfield")
_SF_ASSETS = _SF_ROOT / "ArcaneConduit" / "Assets" / "Transcendence"
_SF_TEX = _SF_ROOT / "Data" / "Textures" / "ArcaneConduit" / "NovaDrift"
_SF_MAT = _SF_ROOT / "Data" / "Materials" / "ArcaneConduit"
_MAT_TEMPLATE = _SF_MAT / "proj_dragonbreath.mat"

for _p in (_TX, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import tx_ai_pipeline as tx  # noqa: E402

DDS = {
    "diffuse": ("color", "BC7_UNORM_SRGB", ["-srgb", "-dx10"]),
    "normal": ("normal", "BC5_SNORM", ["-dx10"]),
    "roughness": ("rough", "BC4_UNORM", ["-dx10"]),
    "emission": ("emissive", "BC7_UNORM_SRGB", ["-srgb", "-dx10"]),
}


def _load_index() -> Dict[str, str]:
    data = json.loads(_INDEX.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in (data.get("concepts") or {}).items()}


def _load_specs(index: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    specs: Dict[str, Dict[str, Any]] = {}
    for path in (
        _TX / "crossmod_ship_skins_registry.json",
        _TX / "crossmod_living_weapon_registry.json",
    ):
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in ("ships", "items", "weapons", "modules"):
            for entry in data.get(key) or []:
                if not isinstance(entry, dict):
                    continue
                aid = str(entry.get("id") or "").strip()
                if not aid:
                    art = Path(str(entry.get("conceptArt") or "")).stem
                    for known, concept in index.items():
                        if Path(concept).stem == art:
                            aid = known
                            break
                if not aid:
                    continue
                specs[aid] = {
                    "theme": entry.get("theme") or aid,
                    "colors": entry.get("colors") or ["#6e37af", "#be8cff", "#ffffff"],
                    "pattern": entry.get("pattern") or "organic techno plate",
                    "style": "seamless tileable PBR albedo, flat lighting",
                    "description": entry.get("description")
                    or f"seamless material matching {aid} concept art",
                    "glow": True,
                }
    return specs


def _texconv(png: Path, dest_dir: Path, dds_format: str, extra: List[str]) -> Path:
    from tool_paths import texconv_exe

    exe = texconv_exe()
    if not exe:
        raise RuntimeError("texconv not found")
    dest_dir.mkdir(parents=True, exist_ok=True)
    cmd = [str(exe), "-y", "-nologo", "-f", dds_format, *extra, "-o", str(dest_dir), str(png)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"texconv failed: {(proc.stderr or proc.stdout)[-400:]}")
    out = dest_dir / (png.stem + ".DDS")
    if not out.is_file():
        alt = dest_dir / (png.stem + ".dds")
        if alt.is_file():
            alt.rename(out)
    if not out.is_file():
        raise RuntimeError(f"texconv produced no DDS for {png.name}")
    return out


def _clone_mat(stem: str) -> Path:
    if not _MAT_TEMPLATE.is_file():
        raise RuntimeError(f"missing mat template {_MAT_TEMPLATE}")
    template = json.loads(_MAT_TEMPLATE.read_text(encoding="utf-8"))
    token_old = "proj_dragonbreath"

    def walk(obj: Any, mapping: Dict[str, str]) -> Any:
        if isinstance(obj, dict):
            return {k: walk(v, mapping) for k, v in obj.items()}
        if isinstance(obj, list):
            return [walk(v, mapping) for v in obj]
        if isinstance(obj, str):
            return mapping.get(obj, obj)
        return obj

    local_ids: List[str] = []
    for entry in template.get("Objects", []):
        eid = entry.get("ID")
        if isinstance(eid, str) and eid.startswith("res:"):
            local_ids.append(eid)
    salt = stem.encode("utf-8")
    id_map = {}
    for i, old in enumerate(local_ids):
        parts = old.split(":")
        new_hi = zlib.crc32(salt + bytes([i])) & 0xFFFFFFFF
        id_map[old] = f"res:{new_hi:08X}:{parts[2]}:{parts[3]}" if len(parts) >= 4 else old
    cloned = walk(template, id_map)
    cloned["Filename"] = f"MATERIALS\\ArcaneConduit\\{stem}.mat"
    color = f"Data\\Textures\\ArcaneConduit\\NovaDrift\\{stem}_color.dds"
    normal = f"Data\\Textures\\ArcaneConduit\\NovaDrift\\{stem}_normal.dds"
    rough = f"Data\\Textures\\ArcaneConduit\\NovaDrift\\{stem}_rough.dds"
    summary = cloned.get("Summary", {}).get("Layer1", {}).get("Textures", {})
    for key, path in (("Albedo", color), ("Normal", normal), ("Roughness", rough)):
        if key in summary:
            summary[key]["File"] = path
            summary[key]["UseReplacement"] = False
    for entry in cloned.get("Objects", []):
        for comp in entry.get("Components", []):
            if comp.get("Type") == "BSComponentDB::CTName":
                name = comp.get("Data", {}).get("Name", "")
                comp["Data"]["Name"] = name.replace(token_old, stem)
            if comp.get("Type") == "BSMaterial::MRTextureFile":
                idx = comp.get("Index", 0)
                if idx == 0:
                    comp["Data"]["FileName"] = color
                elif idx == 1:
                    comp["Data"]["FileName"] = normal
                elif idx == 3:
                    comp["Data"]["FileName"] = rough
    _SF_MAT.mkdir(parents=True, exist_ok=True)
    dest = _SF_MAT / f"{stem}.mat"
    dest.write_text(json.dumps(cloned, indent=2), encoding="utf-8")
    return dest


def _default_spec(asset_id: str) -> Dict[str, Any]:
    return {
        "theme": f"{asset_id} organic techno hull plate",
        "colors": ["#30145c", "#6e37af", "#be8cff", "#ffffff"],
        "pattern": "mosaic bioluminescent plate",
        "style": "seamless tileable PBR albedo, flat lighting",
        "description": f"seamless material for {asset_id}",
        "glow": True,
    }


def make_skins(
    asset_id: str,
    concept_name: str,
    spec: Dict[str, Any],
    *,
    quality: str,
) -> Dict[str, Any]:
    glb = _MESH_DIR / f"{asset_id}.glb"
    if not glb.is_file():
        return {"id": asset_id, "ok": False, "error": f"missing mesh {glb}"}
    concept = tx.resolve_concept_art(path=concept_name)
    pack = _OUT / asset_id
    skin_dir = pack / "skins"
    skin_dir.mkdir(parents=True, exist_ok=True)
    skin_spec = dict(spec)
    if concept:
        skin_spec["referenceImage"] = str(concept)
        skin_spec["imageStrength"] = 0.45
    print(f"[tex] SD PBR {asset_id}", flush=True)
    skins = tx.generate_pbr_skins(
        skin_dir,
        asset_id,
        skin_spec,
        quality=quality,
        use_sd=True,
        seed=17 + zlib.crc32(asset_id.encode()) % 1000,
        glow=bool(skin_spec.get("glow")),
    )
    tex_assets = _SF_ASSETS / "Textures" / asset_id
    tex_assets.mkdir(parents=True, exist_ok=True)
    for key in ("diffuse", "normal", "roughness", "metallic", "emission"):
        src = Path(skins[key]) if key in skins else None
        if src and src.is_file():
            shutil.copy2(src, tex_assets / src.name)
    return {"id": asset_id, "ok": True, "skins": skins, "glb": str(glb), "pack": str(pack)}


_BLENDER_UCUPAINT = Path(r"D:\tools\Blender Foundation\Blender 5.0\blender.exe")


def bake_one(row: Dict[str, Any]) -> Dict[str, Any]:
    asset_id = row["id"]
    pack = Path(row["pack"])
    bake_dir = pack / "bake"
    print(f"[tex] Ucupaint bake {asset_id}", flush=True)
    blender = str(_BLENDER_UCUPAINT) if _BLENDER_UCUPAINT.is_file() else None
    bake = tx.bake_onto_mesh(
        row["glb"],
        bake_dir,
        skin_dir=pack / "skins",
        name=asset_id,
        size=1024,
        ao=False,
        blender=blender,
        stop_servers=True,
    )
    row["bake"] = {k: (str(v) if not isinstance(v, dict) else v) for k, v in bake.items()}
    return row


def publish_dds_mat(row: Dict[str, Any]) -> Dict[str, Any]:
    asset_id = row["id"]
    pack = Path(row["pack"])
    skins = {k: Path(v) for k, v in row["skins"].items() if k != "registry"}
    bake_dir = pack / "bake"
    color_src = bake_dir / f"{asset_id}_color.png"
    if not color_src.is_file():
        # ucupaint may name diffuse differently
        for cand in bake_dir.glob(f"{asset_id}*color*.png"):
            color_src = cand
            break
        else:
            color_src = skins["diffuse"]
    map_files = {
        "diffuse": color_src,
        "normal": skins["normal"],
        "roughness": skins["roughness"],
        "emission": skins.get("emission") or skins["diffuse"],
    }
    stage = pack / "dds_stage"
    stage.mkdir(parents=True, exist_ok=True)
    _SF_TEX.mkdir(parents=True, exist_ok=True)
    dds_out: Dict[str, str] = {}
    for key, (suffix, fmt, extra) in DDS.items():
        staged = stage / f"{asset_id}_{suffix}.png"
        shutil.copy2(map_files[key], staged)
        dds = _texconv(staged, _SF_TEX, fmt, extra)
        final = _SF_TEX / f"{asset_id}_{suffix}.dds"
        if dds.resolve() != final.resolve():
            if final.is_file():
                final.unlink()
            dds.rename(final)
        dds_out[suffix] = str(final)
    row["dds"] = dds_out
    row["mat"] = str(_clone_mat(asset_id))
    (pack / "texture_manifest.json").write_text(json.dumps(row, indent=2), encoding="utf-8")
    return row


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", action="append", default=[])
    ap.add_argument("--skip-bake", action="store_true")
    ap.add_argument(
        "--resume-skins",
        action="store_true",
        help="Reuse Output/HdPipeline/*/skins (skip SD); still publish DDS/MAT",
    )
    ap.add_argument("--quality", default="standard")
    args = ap.parse_args(argv)

    index = _load_index()
    specs = _load_specs(index)
    ids = args.id or list(index.keys())
    report: List[Dict[str, Any]] = []

    if args.resume_skins:
        for asset_id in ids:
            pack = _OUT / asset_id
            skin_dir = pack / "skins"
            glb = _MESH_DIR / f"{asset_id}.glb"
            diffuse = skin_dir / f"{asset_id}_diffuse.png"
            if not diffuse.is_file() or not glb.is_file():
                report.append(
                    {
                        "id": asset_id,
                        "ok": False,
                        "error": f"missing skins or glb for resume ({diffuse})",
                    }
                )
                continue
            skins = {
                key: str(skin_dir / f"{asset_id}_{key}.png")
                for key in ("diffuse", "normal", "roughness", "metallic", "emission")
                if (skin_dir / f"{asset_id}_{key}.png").is_file()
            }
            report.append(
                {"id": asset_id, "ok": True, "skins": skins, "glb": str(glb), "pack": str(pack)}
            )
            print(f"[tex] resume skins {asset_id}", flush=True)
    else:
        os.environ["AAMT_SD_KEEP_SERVER"] = "1"
        try:
            from trellis_http_client import stop_server

            stop_server(force=True)
        except Exception:
            pass
        print("[tex] starting SD...", flush=True)
        prep = tx.prepare(image=True, mesh=False, keep_server=True)
        if not (prep.get("image") or {}).get("ready"):
            print(json.dumps(prep, indent=2))
            return 1
        try:
            for asset_id in ids:
                print(f"\n==== SD skins {asset_id} ====", flush=True)
                row = make_skins(
                    asset_id,
                    index[asset_id],
                    specs.get(asset_id) or _default_spec(asset_id),
                    quality=args.quality,
                )
                report.append(row)
                print(
                    json.dumps(
                        {"id": row["id"], "ok": row.get("ok"), "error": row.get("error")},
                        indent=2,
                    )
                )
        finally:
            print("[tex] stopping SD before bake...", flush=True)
            tx.release(force=True)

    ok_rows = [r for r in report if r.get("ok")]
    if not args.skip_bake:
        for row in ok_rows:
            try:
                bake_one(row)
            except Exception as exc:  # noqa: BLE001
                # Keep skins usable for DDS even when Ucupaint/Blender 5.x headless fails.
                row["bakeError"] = str(exc)
                print(f"[tex] bake FAIL {row['id']} (continuing with SD skins): {exc}", file=sys.stderr)

    for row in list(ok_rows):
        if not row.get("ok"):
            continue
        try:
            publish_dds_mat(row)
            print(f"[tex] published DDS+MAT {row['id']}", flush=True)
        except Exception as exc:  # noqa: BLE001
            row["ok"] = False
            row["error"] = f"dds/mat failed: {exc}"
            print(f"[tex] dds FAIL {row['id']}: {exc}", file=sys.stderr)

    out = _OUT / "_texture_batch_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    ok = sum(1 for r in report if r.get("ok"))
    print(f"\n[tex] done {ok}/{len(report)} -> {out}")
    return 0 if ok == len(report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
