#!/usr/bin/env python3
"""120-facing HD spritesheets from already-baked TRELLIS GLBs.

Prefers Output/HdPipeline/{id}/bake/{id}_baked.glb, else Shared/Concepts/meshes/{id}.glb.

  python tx_concept_spritesheet_batch.py
  python tx_concept_spritesheet_batch.py --id scSpaceWhale
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

_TX = Path(__file__).resolve().parent
_TOOLS = _TX.parent
_SHARED = _TOOLS / "Shared"
_OUT = _TX / "Output" / "HdPipeline"
_MESH = _SHARED / "Concepts" / "meshes"
_INDEX = _SHARED / "Concepts" / "index.json"

if str(_TX) not in sys.path:
    sys.path.insert(0, str(_TX))

import tx_ai_pipeline as tx  # noqa: E402
import tx_concept_hd_pipeline as hd  # noqa: E402


def _glb_for(asset_id: str) -> Optional[Path]:
    baked = _OUT / asset_id / "bake" / f"{asset_id}_baked.glb"
    if baked.is_file():
        return baked
    shared = _MESH / f"{asset_id}.glb"
    if shared.is_file():
        return shared
    pack = _OUT / asset_id / "Meshes" / f"{asset_id}.glb"
    return pack if pack.is_file() else None


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", action="append", default=[])
    args = ap.parse_args(argv)

    # Blender needs the GPU; keep SD/TRELLIS down.
    try:
        tx.release(force=True)
    except Exception:
        pass

    index = hd._load_index()
    ids = args.id or list(index.keys())
    reports = []
    for asset_id in ids:
        glb = _glb_for(asset_id)
        print("=" * 64, flush=True)
        print(f"[sheet] {asset_id} <- {glb}", flush=True)
        if not glb:
            reports.append({"id": asset_id, "ok": False, "error": "no GLB"})
            continue
        try:
            reports.append(
                hd.run_one(
                    asset_id,
                    out_root=_OUT,
                    backup_root=_OUT / "Backup",
                    skip_trellis=True,
                    glb_in=str(glb),
                )
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[sheet] FAIL {asset_id}: {exc}", file=sys.stderr)
            reports.append({"id": asset_id, "ok": False, "error": str(exc)})

    summary = {
        "ok": sum(1 for r in reports if r.get("ok")),
        "fail": sum(1 for r in reports if not r.get("ok")),
        "jobs": reports,
    }
    out = _OUT / "_spritesheet_batch_report.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"ok": summary["ok"], "fail": summary["fail"], "report": str(out)}, indent=2))
    return 0 if summary["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
