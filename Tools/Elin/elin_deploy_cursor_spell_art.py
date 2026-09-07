#!/usr/bin/env python3
"""Deploy Cursor-generated spell concept PNGs into Class Creator + Starfield.

Looks for {Act}_concept.png (and optional {Act}_icon.png) in the Cursor assets
folder, writes:
  - Texture/{Act}.png                 48x48 (Elin)
  - Output/Concepts/Spells/Concept/   full concept
  - Output/Concepts/Spells/Icon/      128x128
  - Starfield .../ElinExport/spell_art/

  python elin_deploy_cursor_spell_art.py
  python elin_deploy_cursor_spell_art.py --act ActBloodBolt
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image

_ELIN = Path(__file__).resolve().parent
_CAT = _ELIN / "spell_art_catalog.json"
_CFG = json.loads((_ELIN / "elin_asset_catalog.json").read_text(encoding="utf-8"))
_ASSETS = Path(_CFG["cursorAssetsDir"])
_MOD = Path(_CFG["modPath"])
_OUT = _ELIN / "Output" / "Concepts" / "Spells"
_SF = Path(_CFG["starfield"]["arcaneConduit"]) / "assets" / "ElinExport" / "spell_art"


def deploy_one(act: str, src: Path) -> None:
    im = Image.open(src).convert("RGBA")
    concept_dir = _OUT / "Concept"
    icon_dir = _OUT / "Icon"
    concept_dir.mkdir(parents=True, exist_ok=True)
    icon_dir.mkdir(parents=True, exist_ok=True)
    (_SF / "concepts").mkdir(parents=True, exist_ok=True)
    (_SF / "icons").mkdir(parents=True, exist_ok=True)

    concept_path = concept_dir / f"{act}_concept.png"
    im.save(concept_path, optimize=True)
    shutil.copy2(concept_path, _SF / "concepts" / concept_path.name)

    icon128 = im.resize((128, 128), Image.Resampling.LANCZOS)
    icon_path = icon_dir / f"{act}_icon.png"
    icon128.save(icon_path, optimize=True)
    shutil.copy2(icon_path, _SF / "icons" / icon_path.name)

    act_path = _MOD / "Texture" / f"{act}.png"
    act_path.parent.mkdir(parents=True, exist_ok=True)
    im.resize((48, 48), Image.Resampling.LANCZOS).save(act_path, optimize=True)
    print(f"[ok] {act} <- {src.name}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--act", action="append", default=[])
    args = ap.parse_args()
    cat = json.loads(_CAT.read_text(encoding="utf-8")) if _CAT.is_file() else {"spells": []}
    acts = args.act or [s["act"] for s in cat.get("spells") or []]
    n = 0
    for act in acts:
        src = _ASSETS / f"{act}_concept.png"
        if not src.is_file():
            # also accept bare ActBloodBolt.png
            alt = _ASSETS / f"{act}.png"
            src = alt if alt.is_file() else src
        if not src.is_file():
            continue
        deploy_one(act, src)
        n += 1
    print(f"deployed {n}/{len(acts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
