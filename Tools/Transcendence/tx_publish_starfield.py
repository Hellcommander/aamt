#!/usr/bin/env python3
"""Copy Transcendence concept assets into ArcaneConduit for Starfield reuse.

Same destinations as the original 24-hull pass:
  ArcaneConduit/Assets/Transcendence/{id}.glb + .json
  ArcaneConduit/Assets/Transcendence/Concepts/{png}
  ArcaneConduit/Assets/Transcendence/Textures/{id}/  (if SD skins exist)
  ArcaneConduit/art/transcendence/                   (design docs)
  ArcaneConduit/Assets/Transcendence/catalog.json

  python tx_publish_starfield.py
  python tx_publish_starfield.py --id scSpaceManta --id scBiometalDragon
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_TX = Path(__file__).resolve().parent
_TOOLS = _TX.parent
_SHARED = _TOOLS / "Shared"
_REF = _TX / "References"
_CONCEPTS = _SHARED / "Concepts"
_MESH_DIR = _CONCEPTS / "meshes"
_INDEX = _CONCEPTS / "index.json"
_OUT = _TX / "Output" / "HdPipeline"
_SF_ROOT = Path(r"F:\SteamLibrary\steamapps\common\Starfield")
_SF_ASSETS = _SF_ROOT / "ArcaneConduit" / "Assets" / "Transcendence"
_SF_CONCEPTS = _SF_ASSETS / "Concepts"
_SF_ART = _SF_ROOT / "ArcaneConduit" / "art" / "transcendence"
_SF_DATA_TEX = _SF_ROOT / "Data" / "Textures" / "ArcaneConduit" / "NovaDrift"
_SF_DATA_MAT = _SF_ROOT / "Data" / "Materials" / "ArcaneConduit"
_REGISTRY = _TX / "crossmod_ship_skins_registry.json"
_WEAPON_REG = _TX / "crossmod_living_weapon_registry.json"
DOCS = (
    "BIOMETAL_DRAGON.md",
    "SPACE_SHARK.md",
    "SPACE_MANTA.md",
)
MIN_GLB = 400_000
SETUP_MD = """# Transcendence → ArcaneConduit asset pack

Reusable living-hull / living-weapon assets from the Transcendence AAMT pipeline.

## Layout

| Path | Contents |
|---|---|
| `Assets/Transcendence/{id}.glb` | TRELLIS 1024 mesh (Starfield in-game / convert to NIF) |
| `Assets/Transcendence/{id}.json` | Sidecar: source path, bytes, concept |
| `Assets/Transcendence/Concepts/*.png` | 3D studio concepts (re-run TRELLIS if needed) |
| `Assets/Transcendence/Textures/{id}/*.png` | SD PBR skins (diffuse/normal/rough/metal/emission) |
| `Assets/Transcendence/Baked/{id}_baked.glb` | Ucupaint-baked mesh when available |
| `Assets/Transcendence/index.json` | Concept → PNG map |
| `Assets/Transcendence/ship_registry.json` | Roles, organs, combat kit, physics |
| `Assets/Transcendence/catalog.json` | Full inventory of published assets |
| `art/transcendence/*.md` | Design docs (Dragon / Shark / Manta) |
| `Data/Textures/ArcaneConduit/NovaDrift/{id}_*.dds` | Runtime DDS (when texture batch finished) |
| `Data/Materials/ArcaneConduit/{id}.mat` | Runtime materials |
| `Data/Sound/ArcaneConduit/nd_{id}_*.wav` | SA3 clips (when audio batch finished) |

## New biometal lines

- **Dragon (apex):** `scBiometalDragon` + Segment / Tail / Drone
- **Shark (predator):** `scSpaceShark` Scout / Hunter / Apex + Segment / Tail / Drone
- **Manta (support):** `scSpaceManta` Scout / Guardian / Rift + Wing / Tail / Drone

## Produce / refresh meshes

Concepts are already remeshed. To regenerate one hull:

```
python Tools/Shared/trellis_http_client.py --image Concepts/<png> --output <id>.glb --resolution 1024 --steps 28 --guidance-scale 8.0 --mesh-simplify 120 --texture-size 1024
```

Or from Tools: `python Transcendence/tx_concept_remesh_batch.py --id <id> --force`

Republish into this folder: `python Transcendence/tx_publish_starfield.py`
"""


def _load_index() -> Dict[str, str]:
    data = json.loads(_INDEX.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in (data.get("concepts") or {}).items()}


def _resolve_concept(name: str) -> Optional[Path]:
    for base in (_REF, _CONCEPTS):
        hit = base / name
        if hit.is_file():
            return hit.resolve()
    for base in (_REF, _CONCEPTS):
        hit = base / f"{Path(name).stem}.png"
        if hit.is_file():
            return hit.resolve()
    return None


def _registry_entry(asset_id: str) -> Optional[Dict[str, Any]]:
    for path in (_REGISTRY, _WEAPON_REG):
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in ("ships", "items", "weapons", "modules"):
            for entry in data.get(key) or []:
                if isinstance(entry, dict) and str(entry.get("id") or "") == asset_id:
                    return entry
    return None


def publish_one(asset_id: str, concept_name: str = "") -> Dict[str, Any]:
    row: Dict[str, Any] = {"id": asset_id}
    _SF_ASSETS.mkdir(parents=True, exist_ok=True)
    _SF_CONCEPTS.mkdir(parents=True, exist_ok=True)

    if not concept_name:
        try:
            concept_name = _load_index().get(asset_id, "")
        except Exception:
            concept_name = ""
    concept = _resolve_concept(concept_name) if concept_name else None
    if not concept:
        concept = _resolve_concept(f"{asset_id}.png")
    if concept:
        dest = _SF_CONCEPTS / concept.name
        shutil.copy2(concept, dest)
        row["concept"] = str(dest)

    glb = _MESH_DIR / f"{asset_id}.glb"
    if glb.is_file() and glb.stat().st_size >= MIN_GLB:
        sf = _SF_ASSETS / f"{asset_id}.glb"
        shutil.copy2(glb, sf)
        meta = {
            "id": asset_id,
            "glb": str(glb),
            "starfieldProject": str(sf),
            "bytes": glb.stat().st_size,
            "consumers": [
                "Transcendence: Blender 120-facing spritesheet (2.5D)",
                "Starfield ArcaneConduit: in-game mesh (this GLB)",
            ],
        }
        if row.get("concept"):
            meta["concept"] = row["concept"]
        sidecar = _MESH_DIR / f"{asset_id}.json"
        if sidecar.is_file():
            try:
                extra = json.loads(sidecar.read_text(encoding="utf-8"))
                if isinstance(extra, dict):
                    meta = {**extra, **meta}
            except Exception:
                pass
        sf.with_suffix(".json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        sidecar.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        row["glb"] = str(sf)
        row["bytes"] = glb.stat().st_size

    skins = _OUT / asset_id / "skins"
    if skins.is_dir():
        tex_dest = _SF_ASSETS / "Textures" / asset_id
        tex_dest.mkdir(parents=True, exist_ok=True)
        copied: List[str] = []
        for png in skins.glob("*.png"):
            shutil.copy2(png, tex_dest / png.name)
            copied.append(png.name)
        if copied:
            row["skins"] = copied

    baked = _OUT / asset_id / "bake" / f"{asset_id}_baked.glb"
    if baked.is_file() and baked.stat().st_size >= MIN_GLB:
        bake_dest_dir = _SF_ASSETS / "Baked"
        bake_dest_dir.mkdir(parents=True, exist_ok=True)
        bake_dest = bake_dest_dir / baked.name
        shutil.copy2(baked, bake_dest)
        row["baked"] = str(bake_dest)

    entry = _registry_entry(asset_id)
    if entry:
        row["registry"] = {
            k: entry.get(k)
            for k in (
                "role",
                "family",
                "variant",
                "line",
                "theme",
                "colors",
                "combatKit",
                "organs",
                "swarm",
                "physics",
                "frameWidth",
            )
            if k in entry
        }
    return row


def publish_docs() -> List[str]:
    _SF_ART.mkdir(parents=True, exist_ok=True)
    out: List[str] = []
    for name in DOCS:
        src = _TX / name
        if src.is_file():
            dest = _SF_ART / name
            shutil.copy2(src, dest)
            out.append(str(dest))
    setup = _SF_ASSETS / "README.md"
    setup.write_text(SETUP_MD, encoding="utf-8")
    out.append(str(setup))
    return out


def publish_meta() -> List[str]:
    """Copy index + ship registry so Starfield can wire organs / physics / combat kits."""
    _SF_ASSETS.mkdir(parents=True, exist_ok=True)
    out: List[str] = []
    if _INDEX.is_file():
        dest = _SF_ASSETS / "index.json"
        shutil.copy2(_INDEX, dest)
        out.append(str(dest))
    if _REGISTRY.is_file():
        dest = _SF_ASSETS / "ship_registry.json"
        shutil.copy2(_REGISTRY, dest)
        out.append(str(dest))
    if _WEAPON_REG.is_file():
        dest = _SF_ASSETS / "weapon_registry.json"
        shutil.copy2(_WEAPON_REG, dest)
        out.append(str(dest))
    return out


def write_catalog(rows: List[Dict[str, Any]]) -> Path:
    catalog = {
        "purpose": (
            "Transcendence 3D concepts + TRELLIS GLBs reused by ArcaneConduit. "
            "TX renders 120 facings from the same mesh. Starfield uses GLBs / skins / registry to set up living hulls."
        ),
        "meshDir": str(_SF_ASSETS),
        "conceptDir": str(_SF_CONCEPTS),
        "textureDir": str(_SF_ASSETS / "Textures"),
        "bakedDir": str(_SF_ASSETS / "Baked"),
        "dataTextures": str(_SF_DATA_TEX),
        "dataMaterials": str(_SF_DATA_MAT),
        "docs": [str(_SF_ART / n) for n in DOCS],
        "index": str(_SF_ASSETS / "index.json"),
        "shipRegistry": str(_SF_ASSETS / "ship_registry.json"),
        "assets": rows,
    }
    path = _SF_ASSETS / "catalog.json"
    path.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    return path


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Publish TX concept assets to Starfield ArcaneConduit")
    ap.add_argument("--id", action="append", default=[], help="Asset id (repeatable); default = full index")
    args = ap.parse_args(argv)

    index = _load_index()
    ids = args.id or list(index.keys())
    rows = []
    for asset_id in ids:
        row = publish_one(asset_id, index.get(asset_id, ""))
        rows.append(row)
        bits = []
        if row.get("concept"):
            bits.append("concept")
        if row.get("glb"):
            bits.append(f"glb {row.get('bytes', 0)}")
        if row.get("skins"):
            bits.append(f"skins {len(row['skins'])}")
        if row.get("baked"):
            bits.append("baked")
        print(f"[sf] {asset_id}: {', '.join(bits) or 'no files yet'}", flush=True)

    docs = publish_docs()
    for d in docs:
        print(f"[sf] doc {d}", flush=True)
    for m in publish_meta():
        print(f"[sf] meta {m}", flush=True)
    # Catalog always covers the full index so a --id run does not wipe other entries.
    catalog_rows = rows
    if args.id:
        catalog_rows = [publish_one(i, index.get(i, "")) for i in index]
    cat = write_catalog(catalog_rows)
    glb_n = sum(1 for r in catalog_rows if r.get("glb"))
    concept_n = sum(1 for r in catalog_rows if r.get("concept"))
    skin_n = sum(1 for r in catalog_rows if r.get("skins"))
    print(
        f"[sf] catalog {cat} — {concept_n} concepts, {glb_n}/{len(catalog_rows)} GLBs, {skin_n} with skins"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
