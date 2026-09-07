#!/usr/bin/env python3
"""Export Nova Drift–inspired living weapons / shields / mods for Starfield.

Ships are already imported and reworked on the Starfield side — this pack is
only the living-weapon chambers, living shields, projectile art, and mod icons
(plus combat / iconAssignment JSON from the TX living-weapon registry).

  python tx_export_nova_drift_option.py
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

_TX = Path(__file__).resolve().parent
_TOOLS = _TX.parent
_SHARED = _TOOLS / "Shared"
_CONCEPTS = _SHARED / "Concepts"
_MESH = _CONCEPTS / "meshes"
_INDEX = _CONCEPTS / "index.json"
_OUT = _TX / "Output" / "HdPipeline"
_WEP_REG = _TX / "crossmod_living_weapon_registry.json"
_REF = _TX / "References"
_SF = Path(r"F:\SteamLibrary\steamapps\common\Starfield")
_SF_TX = _SF / "ArcaneConduit" / "Assets" / "Transcendence"
_SF_DDS = _SF / "Data" / "Textures" / "ArcaneConduit" / "NovaDrift"
_SF_MAT = _SF / "Data" / "Materials" / "ArcaneConduit"
_SF_SND = _SF / "Data" / "Sound" / "ArcaneConduit"
_DEFAULT_OUT = _SF / "ArcaneConduit" / "assets" / "NovaDriftOption"
_DOCS_SRC = (_SF / "ArcaneConduit" / "docs" / "DESIGN-INSPIRATION.md",)

README = """# Nova Drift–inspired living weapons option (Starfield)

Optional pack: **living weapons**, **living shields**, and **mods** whose
moodboards / combat habits were inspired by
[Nova Drift](https://store.steampowered.com/app/858210/Nova_Drift/).
**Original generated art** — not affiliated with or endorsed by that game.

**Ships / hulls are not in this pack** — they are already imported and reworked
in MadScience / Arcane Conduit. Use this for chambers, shields, projectiles, and
mod icons (+ registry combat notes / `iconAssignments`).

## Buckets

| Bucket | Examples |
|--------|----------|
| Living weapon chambers | Blaster, Blade, Sword, Torrent, Thermal Lance, Railgun, Dart, Flak, Pulse, Vortex |
| Living shields | Siphon, Halo, Aegis-family shield module icons |
| Mods | Fire / Blade / Sword modules, Tier, Wild, Evolved-Ship (ES) mod icons |
| Projectiles / FX | `ptLiving*`, Discord orb, level FX |
| Registry glue | Full combat notes + `iconAssignments` → `itIWL*` / `itES*` item ids |

## Layout

```
manifest.json
option.ini                 # [NovaDriftOption] bEnabled=0|1
README.md
REWRITE_NOTES.md
docs/
registry/
  weapon_registry.json     # living-weapon registry with ships stripped
  index.json               # concept map for included asset ids
  iconAssignments.json     # itIWL* / itES* → lw* icon id
assets/
  Concepts/                # PNGs (re-TRELLIS / UI)
  Meshes/                  # GLB when present
  Textures/{id}/           # SD PBR skins
  Baked/
Data/                      # merge into Starfield Data/
  Textures/ArcaneConduit/NovaDrift/
  Materials/ArcaneConduit/
  Sound/ArcaneConduit/
```

## Enable

1. Keep under `ArcaneConduit/assets/NovaDriftOption/`
2. Set `bEnabled=1` in `option.ini` (or copy into `ArcaneConduit.ini` when wired)
3. Merge `Data/` or pack BA2 from those paths
4. Register `itIWL*` / `itES*` items using `registry/iconAssignments.json` + meshes

Refresh:

```
python Tools/Transcendence/tx_export_nova_drift_option.py
```
"""

REWRITE = """# Rework notes

1. Soft-load when `bEnabled=1` — do not re-import biometal hulls from this pack.
2. Optional BA2: `ArcaneConduitLivingWeapons - Main/Textures.ba2`.
3. Rename Data texture folder off `NovaDrift` for release branding if desired.
4. Ships stay in the main biometal / Transcendence import — do not merge ship
   GLBs back into this option.
"""

OPTION_INI = """; Living weapons / living shields / mods option (ships already imported elsewhere).
[NovaDriftOption]
bEnabled=0
bRegisterWeapons=1
bRegisterShields=1
bRegisterMods=1
bRegisterShips=0
sAssetRoot=ArcaneConduit/assets/NovaDriftOption
bUseDataTextures=1
"""

SHIP_KINDS = {"ship"}
SHIP_ROLES = {"ship"}
SHIP_ID_PREFIXES = ()  # explicit denylist by id below
SHIP_IDS = {
    "lwViperShip",
    "lwCarrierShip",
    "lwSentinelShip",
}


def _is_ship(entry: Dict[str, Any]) -> bool:
    aid = str(entry.get("id") or "")
    if aid in SHIP_IDS or aid.endswith("Ship"):
        return True
    kind = str(entry.get("kind") or "").lower()
    role = str(entry.get("role") or "").lower()
    return kind in SHIP_KINDS or role in SHIP_ROLES


def _copy_file(src: Path, dest: Path) -> bool:
    if not src.is_file():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return True


def _resolve_concept(name: str) -> Optional[Path]:
    raw = Path(str(name))
    for base in (_REF, _CONCEPTS, _SF_TX / "Concepts"):
        for cand in (base / raw.name, base / raw):
            if cand.is_file():
                return cand.resolve()
    return None


def _wanted_asset_ids(reg: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for e in reg.get("assets") or []:
        if isinstance(e, dict) and e.get("id") and not _is_ship(e):
            out.append(str(e["id"]))
    return out


def _extra_concept_files(reg: Dict[str, Any]) -> List[Path]:
    """Pull every References PNG named in registry metadata (actions, sprays, etc.)."""
    found: List[Path] = []
    seen: Set[str] = set()

    def consider(val: Any) -> None:
        if not isinstance(val, str):
            return
        if not (val.endswith(".png") or val.endswith(".jpg") or val.endswith(".jpeg")):
            return
        p = _resolve_concept(val)
        if p and p.name not in seen:
            seen.add(p.name)
            found.append(p)

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if "Art" in k or k.endswith("Tile") or k in ("conceptArt", "actionArt"):
                    consider(v)
                walk(v)
        elif isinstance(obj, list):
            for x in obj:
                walk(x)

    walk(reg)
    return found


def export_one(root: Path, asset_id: str, concept_name: str = "") -> Dict[str, Any]:
    row: Dict[str, Any] = {"id": asset_id}
    concept = _resolve_concept(concept_name) if concept_name else None
    if not concept:
        for cand in (f"{asset_id}.png", f"{asset_id}_3d.png"):
            concept = _resolve_concept(cand)
            if concept:
                break
    if concept and _copy_file(concept, root / "assets" / "Concepts" / concept.name):
        row["concept"] = f"assets/Concepts/{concept.name}"

    for glb_src in (_MESH / f"{asset_id}.glb", _SF_TX / f"{asset_id}.glb"):
        if glb_src.is_file() and glb_src.stat().st_size >= 50_000:
            if _copy_file(glb_src, root / "assets" / "Meshes" / f"{asset_id}.glb"):
                row["glb"] = f"assets/Meshes/{asset_id}.glb"
                row["bytes"] = glb_src.stat().st_size
            side = glb_src.with_suffix(".json")
            if side.is_file():
                _copy_file(side, root / "assets" / "Meshes" / f"{asset_id}.json")
            break

    for skin_dir in (_OUT / asset_id / "skins", _SF_TX / "Textures" / asset_id):
        if not skin_dir.is_dir():
            continue
        dest = root / "assets" / "Textures" / asset_id
        copied: List[str] = []
        for png in skin_dir.glob("*.png"):
            if _copy_file(png, dest / png.name):
                copied.append(png.name)
        if copied:
            row["skins"] = copied
            break

    baked = _OUT / asset_id / "bake" / f"{asset_id}_baked.glb"
    if not baked.is_file():
        baked = _SF_TX / "Baked" / f"{asset_id}_baked.glb"
    if baked.is_file() and baked.stat().st_size >= 50_000:
        if _copy_file(baked, root / "assets" / "Baked" / baked.name):
            row["baked"] = f"assets/Baked/{baked.name}"

    dds_copied: List[str] = []
    if _SF_DDS.is_dir():
        for dds in _SF_DDS.glob(f"{asset_id}_*.dds"):
            rel = Path("Data") / "Textures" / "ArcaneConduit" / "NovaDrift" / dds.name
            if _copy_file(dds, root / rel):
                dds_copied.append(dds.name)
    if dds_copied:
        row["dds"] = dds_copied

    mat = _SF_MAT / f"{asset_id}.mat"
    if mat.is_file():
        rel = Path("Data") / "Materials" / "ArcaneConduit" / mat.name
        if _copy_file(mat, root / rel):
            row["mat"] = str(rel).replace("\\", "/")

    wavs: List[str] = []
    if _SF_SND.is_dir():
        for wav in _SF_SND.glob(f"nd_{asset_id}_*.wav"):
            rel = Path("Data") / "Sound" / "ArcaneConduit" / wav.name
            if _copy_file(wav, root / rel):
                wavs.append(wav.name)
    if wavs:
        row["sound"] = wavs
    return row


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=_DEFAULT_OUT)
    args = ap.parse_args(argv)
    root: Path = args.out
    if root.exists():
        for child in root.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    root.mkdir(parents=True, exist_ok=True)

    if not _WEP_REG.is_file():
        print(f"missing {_WEP_REG}", file=sys.stderr)
        return 2
    reg = json.loads(_WEP_REG.read_text(encoding="utf-8"))
    asset_ids = _wanted_asset_ids(reg)
    id_set = set(asset_ids)

    concepts_map: Dict[str, str] = {}
    if _INDEX.is_file():
        concepts_map = {
            str(k): str(v)
            for k, v in (json.loads(_INDEX.read_text(encoding="utf-8")).get("concepts") or {}).items()
        }
    # Prefer per-asset conceptArt from registry
    for e in reg.get("assets") or []:
        if isinstance(e, dict) and e.get("id") in id_set and e.get("conceptArt"):
            concepts_map[str(e["id"])] = str(e["conceptArt"])

    rows: List[Dict[str, Any]] = []
    for asset_id in asset_ids:
        print(f"[nd-opt] {asset_id}", flush=True)
        rows.append(export_one(root, asset_id, concepts_map.get(asset_id, "")))

    # Extra reference PNGs (action / spray / inventory) named in registry
    extras = _extra_concept_files(reg)
    extra_copied = 0
    for src in extras:
        if _copy_file(src, root / "assets" / "Concepts" / src.name):
            extra_copied += 1
    print(f"[nd-opt] extra concepts {extra_copied}", flush=True)

    # Registry: strip ship assets only; keep combat notes + iconAssignments
    filtered = {k: v for k, v in reg.items() if k != "assets"}
    filtered["_export"] = "NovaDriftOption"
    filtered["_scope"] = "living_weapons_shields_mods"
    filtered["_shipsExcluded"] = sorted(SHIP_IDS)
    filtered["assets"] = [
        e for e in (reg.get("assets") or []) if isinstance(e, dict) and not _is_ship(e)
    ]
    reg_dir = root / "registry"
    reg_dir.mkdir(parents=True, exist_ok=True)
    (reg_dir / "weapon_registry.json").write_text(
        json.dumps(filtered, indent=2), encoding="utf-8"
    )
    icons = reg.get("iconAssignments") or {}
    (reg_dir / "iconAssignments.json").write_text(
        json.dumps(icons, indent=2), encoding="utf-8"
    )
    slim_index = {
        "purpose": "Nova Drift option — living weapons / shields / mods only",
        "option": "nova_drift_living_weapons",
        "concepts": {i: concepts_map[i] for i in asset_ids if i in concepts_map},
    }
    (reg_dir / "index.json").write_text(json.dumps(slim_index, indent=2), encoding="utf-8")

    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    for src in _DOCS_SRC:
        if src.is_file():
            shutil.copy2(src, docs / src.name)

    (root / "README.md").write_text(README, encoding="utf-8")
    (root / "REWRITE_NOTES.md").write_text(REWRITE, encoding="utf-8")
    (root / "option.ini").write_text(OPTION_INI, encoding="utf-8")

    weapons = [r["id"] for r in rows if "Chamber" in r["id"] or r["id"].endswith("Module") and "Shield" not in r["id"] and "Mod" not in r["id"]]
    shields = [r["id"] for r in rows if "Shield" in r["id"] or r["id"] == "lwHaloShield"]
    mods = [r["id"] for r in rows if r["id"].endswith("Mod") or r["id"] in ("lwFireModule", "lwBladeModule", "lwSwordModule")]

    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "option": "nova_drift_living_weapons",
        "reworkable": True,
        "export_root": str(root),
        "scope": "living_weapons_shields_mods",
        "shipsExcluded": sorted(SHIP_IDS),
        "disclaimer": (
            "Original generated art. Nova Drift is a trademark of its owners; "
            "fan inspiration only, not affiliated or endorsed."
        ),
        "buckets": {
            "weapons": weapons,
            "shields": shields,
            "mods": mods,
            "other": [
                r["id"]
                for r in rows
                if r["id"] not in weapons and r["id"] not in shields and r["id"] not in mods
            ],
        },
        "iconAssignmentCount": len(icons),
        "counts": {
            "ids": len(rows),
            "with_glb": sum(1 for r in rows if r.get("glb")),
            "with_concept": sum(1 for r in rows if r.get("concept")),
            "with_skins": sum(1 for r in rows if r.get("skins")),
            "with_baked": sum(1 for r in rows if r.get("baked")),
            "with_dds": sum(1 for r in rows if r.get("dds")),
            "with_mat": sum(1 for r in rows if r.get("mat")),
            "with_sound": sum(1 for r in rows if r.get("sound")),
            "extra_concepts": extra_copied,
        },
        "assets": rows,
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest["counts"], indent=2))
    print(f"[nd-opt] done -> {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
