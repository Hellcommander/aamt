#!/usr/bin/env python3
"""Remesh Shared/Concepts index through TRELLIS at a reasonable 1024 preset.

GPU rule: TRELLIS only. Do not start SD or SA3 while this runs.
Keep the server up with AAMT_TRELLIS_KEEP_SERVER=1.

  python tx_concept_remesh_batch.py
  python tx_concept_remesh_batch.py --id scHornRam --id scCeratotitan
  python tx_concept_remesh_batch.py --force
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_TX = Path(__file__).resolve().parent
_TOOLS = _TX.parent
_SHARED = _TOOLS / "Shared"
_REF = _TX / "References"
_CONCEPTS = _SHARED / "Concepts"
_MESH_DIR = _CONCEPTS / "meshes"
_INDEX = _CONCEPTS / "index.json"
_SF_ASSETS = Path(
    r"F:\SteamLibrary\steamapps\common\Starfield\ArcaneConduit\Assets\Transcendence"
)

for _p in (_TX, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# Reasonable 1024 on 11 GB with low_vram RAM offload (not the 512 draft preset).
HQ = {
    "resolution": 1024,
    "steps": 28,
    "guidance_scale": 8.0,
    "mesh_simplify": 120,
    "texture_size": 1024,
}
MIN_GLB_BYTES = 400_000
SEEDS = (4242, 7777, 13579)


def _load_index() -> Dict[str, str]:
    data = json.loads(_INDEX.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in (data.get("concepts") or {}).items()}


def _resolve_concept(name: str) -> Optional[Path]:
    for base in (_REF, _CONCEPTS):
        hit = base / name
        if hit.is_file():
            return hit.resolve()
    # bare id.png fallback
    for base in (_REF, _CONCEPTS):
        hit = base / f"{Path(name).stem}.png"
        if hit.is_file():
            return hit.resolve()
    return None


def _wait_idle(timeout: float = 7200.0) -> None:
    from trellis_http_client import detect_server, server_busy

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if detect_server() and not server_busy():
            return
        time.sleep(3.0)
    raise RuntimeError("TRELLIS stayed busy too long")


def _glb_ok(path: Path) -> bool:
    return path.is_file() and path.stat().st_size >= MIN_GLB_BYTES


def _publish(glb: Path, asset_id: str) -> Dict[str, str]:
    _MESH_DIR.mkdir(parents=True, exist_ok=True)
    shared = _MESH_DIR / f"{asset_id}.glb"
    if glb.resolve() != shared.resolve():
        shutil.copy2(glb, shared)
    _SF_ASSETS.mkdir(parents=True, exist_ok=True)
    sf = _SF_ASSETS / f"{asset_id}.glb"
    shutil.copy2(shared, sf)
    meta = {
        "id": asset_id,
        "glb": str(shared),
        "starfieldProject": str(sf),
        "preset": HQ,
        "bytes": shared.stat().st_size,
    }
    shared.with_suffix(".json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    sf.with_suffix(".json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[batch] published {asset_id} -> Shared + ArcaneConduit Assets")
    try:
        from tx_publish_starfield import publish_one

        publish_one(asset_id)
    except Exception as exc:  # noqa: BLE001
        print(f"[batch] starfield extra copy skipped {asset_id}: {exc}", file=sys.stderr)
    return {"shared": str(shared), "starfield": str(sf)}


def remesh_one(
    asset_id: str,
    concept_name: str,
    *,
    force: bool = False,
    max_attempts: int = 3,
) -> Dict[str, Any]:
    from trellis_http_client import generate_mesh, start_server

    result: Dict[str, Any] = {"id": asset_id, "ok": False}
    concept = _resolve_concept(concept_name)
    if not concept:
        result["error"] = f"concept missing: {concept_name}"
        return result
    result["concept"] = str(concept)

    out = _MESH_DIR / f"{asset_id}.glb"
    draft = _MESH_DIR / f"{asset_id}_draft512.glb"
    if not force and _glb_ok(out):
        side = out.with_suffix(".json")
        preset_res = None
        if side.is_file():
            try:
                preset_res = (json.loads(side.read_text(encoding="utf-8")).get("preset") or {}).get(
                    "resolution"
                )
            except Exception:
                preset_res = None
        # Keep a just-finished 1024 job (no sidecar yet) if a 512 draft was parked.
        looks_hq = (
            preset_res == 1024
            or (
                draft.is_file()
                and out.stat().st_size > draft.stat().st_size
                and out.stat().st_mtime >= draft.stat().st_mtime
            )
        )
        if looks_hq:
            result["ok"] = True
            result["skipped"] = True
            result["glb"] = str(out)
            result["bytes"] = out.stat().st_size
            _publish(out, asset_id)
            return result

    os.environ["AAMT_TRELLIS_KEEP_SERVER"] = "1"
    start_server()
    attempts: List[Dict[str, Any]] = []
    for i, seed in enumerate(SEEDS[: max(1, max_attempts)]):
        _wait_idle()
        attempt_path = _MESH_DIR / f"{asset_id}_try{i}_{seed}.glb"
        print(
            f"[batch] {asset_id} attempt {i + 1}/{max_attempts} "
            f"seed={seed} @ {HQ['resolution']}^3 / {HQ['steps']} steps"
        )
        try:
            generate_mesh(
                concept,
                attempt_path,
                seed=seed,
                resolution=int(HQ["resolution"]),
                steps=int(HQ["steps"]),
                guidance_scale=float(HQ["guidance_scale"]),
                mesh_simplify=int(HQ["mesh_simplify"]),
                texture_size=int(HQ["texture_size"]),
                apply_texture=True,
                autostart=True,
            )
        except Exception as exc:  # noqa: BLE001
            attempts.append({"seed": seed, "error": str(exc)})
            print(f"[batch] FAIL {asset_id} seed={seed}: {exc}", file=sys.stderr)
            continue
        size = attempt_path.stat().st_size if attempt_path.is_file() else 0
        attempts.append({"seed": seed, "bytes": size, "path": str(attempt_path)})
        if size < MIN_GLB_BYTES:
            print(f"[batch] too small ({size}); remesh")
            continue
        shutil.copy2(attempt_path, out)
        pubs = _publish(out, asset_id)
        result.update(
            {
                "ok": True,
                "glb": str(out),
                "bytes": out.stat().st_size,
                "seed": seed,
                "attempts": attempts,
                **pubs,
            }
        )
        return result

    result["error"] = "all attempts failed size/generation gate"
    result["attempts"] = attempts
    return result


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="TRELLIS 1024 remesh batch for concept index")
    ap.add_argument("--id", action="append", default=[], help="Asset id (repeatable)")
    ap.add_argument("--force", action="store_true", help="Remesh even if 1024 GLB exists")
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--wait-idle", action="store_true", help="Wait for current TRELLIS job first")
    args = ap.parse_args(argv)

    os.environ["AAMT_TRELLIS_KEEP_SERVER"] = "1"
    index = _load_index()
    ids = args.id or list(index.keys())
    missing = [i for i in ids if i not in index]
    if missing:
        print(f"[batch] unknown ids: {missing}", file=sys.stderr)
        return 2

    if args.wait_idle:
        print("[batch] waiting for TRELLIS idle...")
        _wait_idle()

    _MESH_DIR.mkdir(parents=True, exist_ok=True)
    report: List[Dict[str, Any]] = []
    for asset_id in ids:
        print(f"\n==== {asset_id} ====", flush=True)
        row = remesh_one(
            asset_id,
            index[asset_id],
            force=args.force,
            max_attempts=args.max_attempts,
        )
        report.append(row)
        print(json.dumps({k: row[k] for k in row if k != "attempts"}, indent=2), flush=True)

    out_report = _MESH_DIR / "_batch_1024_report.json"
    out_report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    ok = sum(1 for r in report if r.get("ok"))
    print(f"\n[batch] done {ok}/{len(report)} -> {out_report}")
    return 0 if ok == len(report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
