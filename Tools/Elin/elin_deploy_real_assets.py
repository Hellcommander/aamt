#!/usr/bin/env python3
"""Bake Cursor/TRELLIS concepts into the real Elin mod layout.

Creates Workshop-style folders under CustomRaceClassCreator:
  Texture/          48x48 Act icons + 128x128 system icons + UI chrome
  Portrait/         optional (skipped unless portrait sources exist)
  LangMod/EN|JP/    Element.tsv + Element.xlsx (Ars-compatible columns)

  python elin_deploy_real_assets.py
  python elin_deploy_real_assets.py --mod-path "E:\\...\\CustomRaceClassCreator"
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from PIL import Image, ImageFilter, ImageOps

try:
    from openpyxl import Workbook
except ImportError as exc:  # pragma: no cover
    raise SystemExit("openpyxl required: pip install openpyxl") from exc

_ELIN_TOOLS = Path(__file__).resolve().parent
_DEFAULT_MOD = Path(
    r"E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator"
)
_CATALOG = _ELIN_TOOLS / "elin_asset_catalog.json"
_OUTPUT = _ELIN_TOOLS / "Output"

# Full Element columns (Ars Moriendi / vanilla SourceElement export shape)
ELEMENT_COLUMNS = [
    "id", "alias", "name_JP", "name", "altname_JP", "altname",
    "aliasParent", "aliasRef", "aliasMtp", "parentFactor", "lvFactor",
    "encFactor", "encSlot", "mtp", "LV", "chance", "value", "cost",
    "geneSlot", "sort", "target", "proc", "type", "group", "category",
    "categorySub", "abilityType", "tag", "thing", "eleP", "cooldown",
    "charge", "radius", "max", "req", "idTrainer", "partySkill",
    "tagTrainer", "levelBonus_JP", "levelBonus", "foodEffect", "note",
    "langAct", "detail_JP", "detail", "textPhase_JP", "textPhase",
    "textExtra_JP", "textExtra", "textInc_JP", "textInc", "textDec_JP",
    "textDec", "textAlt_JP", "textAlt", "adjective_JP", "adjective",
]

ELEMENT_TYPES = [
    "int", "string", "string", "string", "string", "string",
    "string", "string", "string", "float", "int",
    "int", "string", "int", "int", "int", "int", "int[]",
    "int", "int", "string", "string[]", "string", "string", "string",
    "string", "string[]", "string[]", "string", "int", "int",
    "int", "float", "int", "string[]", "string", "int",
    "string", "string", "string", "string[]", "",
    "string[]", "string", "string", "string", "string",
    "string", "string", "string", "string", "string",
    "string", "string", "string[]", "string[]", "string[]", "string[]",
]

# Default row used by vanilla/Ars as the schema defaults line
ELEMENT_DEFAULTS = {
    "lvFactor": "100",
    "mtp": "1",
    "LV": "1",
    "chance": "1000",
    "cost": "0",
    "geneSlot": "1",
    "group": "Element",
    "eleP": "50",
    "charge": "10",
    "radius": "5",
}


def load_catalog() -> Dict[str, Any]:
    if _CATALOG.is_file():
        return json.loads(_CATALOG.read_text(encoding="utf-8"))
    return {}


def concept_path(system_id: str) -> Optional[Path]:
    candidates = [
        _OUTPUT / "Concepts" / "Hero" / f"elin_{system_id}_concept.png",
        Path(
            r"C:\Users\Arend\.cursor\projects\e-SteamLibrary-steamapps-common-Elin-Package-Mod-CustomRaceClassCreator\assets"
        )
        / f"elin_{system_id}_concept.png",
        Path(r"D:\games\Ai assisted toolkit\Tools\Shared\Concepts") / f"elin{system_id}.png",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def icon_source(system_id: str) -> Optional[Path]:
    for p in (
        _OUTPUT / "Concepts" / "Icons" / f"elin_{system_id}_icon.png",
        Path(
            r"C:\Users\Arend\.cursor\projects\e-SteamLibrary-steamapps-common-Elin-Package-Mod-CustomRaceClassCreator\assets"
        )
        / f"elin_{system_id}_icon.png",
        concept_path(system_id),
    ):
        if p and p.is_file():
            return p
    return None


def _fit_square(im: Image.Image, size: int) -> Image.Image:
    """Center-crop to square and resize with a soft edge-aware downsample."""
    im = im.convert("RGBA")
    w, h = im.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    im = im.crop((left, top, left + side, top + side))
    # Prefer subject over empty void: trim near-black borders if present
    try:
        gray = ImageOps.grayscale(im)
        bbox = gray.point(lambda p: 255 if p > 18 else 0).getbbox()
        if bbox:
            # pad bbox a bit
            pad = max(4, side // 20)
            x0 = max(0, bbox[0] - pad)
            y0 = max(0, bbox[1] - pad)
            x1 = min(side, bbox[2] + pad)
            y1 = min(side, bbox[3] + pad)
            im = im.crop((x0, y0, x1, y1))
            # re-square
            w2, h2 = im.size
            side2 = max(w2, h2)
            canvas = Image.new("RGBA", (side2, side2), (0, 0, 0, 0))
            canvas.paste(im, ((side2 - w2) // 2, (side2 - h2) // 2), im)
            im = canvas
    except Exception:
        pass
    if size <= 64:
        im = im.filter(ImageFilter.SMOOTH_MORE)
    return im.resize((size, size), Image.Resampling.LANCZOS)


def write_png(src: Path, dest: Path, size: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        out = _fit_square(im, size)
        out.save(dest, format="PNG", optimize=True)


def pascal(name: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", name or "")
    return "".join(p[:1].upper() + p[1:] for p in parts) or "Spell"


def parse_existing_feats(tsv_path: Path) -> List[Dict[str, str]]:
    if not tsv_path.is_file():
        return []
    text = tsv_path.read_text(encoding="utf-8-sig")
    rows = list(csv.DictReader(text.splitlines(), delimiter="\t"))
    out = []
    for r in rows:
        if not r.get("id") or r.get("id") == "int":
            continue
        out.append(r)
    return out


def parse_spell_templates(data_dir: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for path in sorted(data_dir.rglob("*.xml")):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        for t in root.iter("Template"):
            tid = (t.get("id") or "").strip()
            if not tid:
                continue
            name = (t.findtext("name") or "").strip() or tid
            desc = (t.findtext("description") or "").strip() or name
            ms = t.find("magicSystem")
            system = (ms.get("id") if ms is not None else "") or ""
            tags_el = t.find("tags")
            tags: List[str] = []
            if tags_el is not None:
                kids = list(tags_el.findall("tag"))
                if kids:
                    tags = [(x.text or "").strip() for x in kids if (x.text or "").strip()]
                elif tags_el.text:
                    tags = [x.strip() for x in re.split(r"[;,]", tags_el.text) if x.strip()]
            # alias: actFireBreath style
            alias = "act" + pascal(name if name != tid else tid.replace("tmpl_", "").replace("_", " "))
            rows.append(
                {
                    "elin_id": tid,
                    "alias": alias,
                    "name": name,
                    "detail": desc,
                    "system": system,
                    "tags": ";".join(tags),
                    "file": str(path.relative_to(data_dir)).replace("\\", "/"),
                }
            )
    return rows


def system_for_spell(spell: Dict[str, str], heroes: List[Dict[str, Any]]) -> str:
    sys_id = (spell.get("system") or "").lower()
    for h in heroes:
        if (h.get("elinSystem") or "").lower() == sys_id:
            return h["id"]
        if sys_id and sys_id in h["id"].lower():
            return h["id"]
    # filename heuristics
    f = spell.get("file", "").lower()
    for h in heroes:
        key = (h.get("elinSystem") or h["id"]).lower()
        if key and key in f:
            return h["id"]
    return "DragonMagic"


def empty_element_row() -> Dict[str, str]:
    return {c: "" for c in ELEMENT_COLUMNS}


def feat_to_element(feat: Dict[str, str], sort_base: int) -> Dict[str, str]:
    row = empty_element_row()
    row.update(ELEMENT_DEFAULTS)
    row["id"] = str(feat.get("id") or "")
    row["alias"] = feat.get("alias") or ""
    row["name"] = feat.get("name") or row["alias"]
    row["name_JP"] = feat.get("name_JP") or row["name"]
    row["type"] = feat.get("type") or ""
    row["group"] = feat.get("group") or "feat"
    row["category"] = "feat"
    row["detail"] = feat.get("detail") or ""
    row["detail_JP"] = feat.get("detail_JP") or row["detail"]
    row["note"] = "CustomRaceClassCreator feat"
    try:
        row["sort"] = str(int(feat.get("id") or sort_base))
    except ValueError:
        row["sort"] = str(sort_base)
    return row


def spell_to_element(spell: Dict[str, str], elem_id: int) -> Dict[str, str]:
    row = empty_element_row()
    row.update(ELEMENT_DEFAULTS)
    row["id"] = str(elem_id)
    row["alias"] = spell["alias"]
    row["name"] = spell["name"]
    row["name_JP"] = spell["name"]
    # No discrete Act class for most MagicPlus XML spells — leave type blank.
    # Icons live in Texture/Act*.png; runtime casting stays on MagicPlus XML loaders.
    row["type"] = ""
    row["group"] = "SPELL"
    row["category"] = "ability"
    tags = spell.get("tags") or ""
    if "buff" in tags or "heal" in tags or "utility" in tags:
        row["categorySub"] = "util"
        row["target"] = "Self"
    else:
        row["categorySub"] = "attack"
        row["target"] = "Enemy"
    row["tag"] = "useMainElement"
    row["detail"] = spell["detail"]
    row["detail_JP"] = spell["detail"]
    row["note"] = f"elin:{spell['elin_id']}|{spell['file']}"
    row["cost"] = "10,6"
    row["cooldown"] = "0"
    row["charge"] = "15"
    row["radius"] = "1"
    row["sort"] = str(elem_id)
    row["lvFactor"] = "100"
    return row


def write_element_sheet(path_tsv: Path, path_xlsx: Path, rows: List[Dict[str, str]]) -> None:
    path_tsv.parent.mkdir(parents=True, exist_ok=True)
    with path_tsv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ELEMENT_COLUMNS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        # type row
        w.writerow({c: ELEMENT_TYPES[i] if i < len(ELEMENT_TYPES) else "" for i, c in enumerate(ELEMENT_COLUMNS)})
        # defaults row
        defaults = empty_element_row()
        defaults.update(ELEMENT_DEFAULTS)
        w.writerow(defaults)
        for r in rows:
            w.writerow({c: r.get(c, "") for c in ELEMENT_COLUMNS})

    wb = Workbook()
    ws = wb.active
    ws.title = "Element"
    ws.append(ELEMENT_COLUMNS)
    ws.append(ELEMENT_TYPES)
    defaults = empty_element_row()
    defaults.update(ELEMENT_DEFAULTS)
    ws.append([defaults.get(c, "") for c in ELEMENT_COLUMNS])
    for r in rows:
        ws.append([r.get(c, "") for c in ELEMENT_COLUMNS])
    wb.save(path_xlsx)


def deploy_textures(mod: Path, heroes: List[Dict[str, Any]], spells: List[Dict[str, str]]) -> Dict[str, int]:
    tex = mod / "Texture"
    ui_dir = tex / "UI"
    tex.mkdir(parents=True, exist_ok=True)
    counts = {"system128": 0, "system48": 0, "act48": 0, "ui": 0}

    # System icons
    for h in heroes:
        hid = h["id"]
        src = icon_source(hid) or concept_path(hid)
        if not src:
            print(f"[tex] missing concept for {hid}")
            continue
        write_png(src, tex / f"{hid}.png", 128)
        write_png(src, tex / f"{hid}_48.png", 48)
        counts["system128"] += 1
        counts["system48"] += 1
        print(f"[tex] {hid}.png + _48")

    # Spell Act icons — UNIQUE per spell (never reuse system hero concepts).
    # Prefer Output/Concepts/Spells/Icon/Act*_icon.png from elin_unique_spell_art.py
    spell_icon_dir = _OUTPUT / "Concepts" / "Spells" / "Icon"
    for sp in spells:
        act_name = "Act" + pascal(sp["name"])
        dest = tex / f"{act_name}.png"
        src = spell_icon_dir / f"{act_name}_icon.png"
        if not src.is_file():
            # leave existing unique Act icon alone; do not fall back to system art
            if dest.is_file():
                counts["act48"] += 1
            else:
                print(f"[tex] MISSING unique icon for {act_name} — run elin_unique_spell_art.py")
            continue
        write_png(src, dest, 48)
        counts["act48"] += 1
    print(f"[tex] wrote/kept {counts['act48']} unique Act*.png icons")

    # UI chrome from Cursor staging
    ui_src = _OUTPUT / "Concepts" / "UI"
    if ui_src.is_dir():
        for png in ui_src.glob("elin_ui_*.png"):
            name = png.name.replace("elin_", "", 1)
            dest = ui_dir / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            # keep native res for UI chrome; also emit 48 widget where useful
            shutil.copy2(png, dest)
            counts["ui"] += 1
        print(f"[tex] UI chrome {counts['ui']} -> Texture/UI/")
    return counts


def deploy_element(mod: Path, spells: List[Dict[str, str]]) -> int:
    en = mod / "LangMod" / "EN"
    jp = mod / "LangMod" / "JP"
    en.mkdir(parents=True, exist_ok=True)
    jp.mkdir(parents=True, exist_ok=True)

    feats = parse_existing_feats(en / "Element.tsv")
    rows: List[Dict[str, str]] = []
    for i, f in enumerate(feats):
        rows.append(feat_to_element(f, 2000 + i))

    # Spell id block: 110001+
    next_id = 110001
    for sp in spells:
        if not sp.get("name") or sp["name"] == sp.get("elin_id"):
            # skip nameless bardic stubs
            if not sp.get("detail"):
                continue
        rows.append(spell_to_element(sp, next_id))
        next_id += 1

    write_element_sheet(en / "Element.tsv", en / "Element.xlsx", rows)
    # JP mirror names for now (real JP can be filled later)
    write_element_sheet(jp / "Element.tsv", jp / "Element.xlsx", rows)
    # keep csv sync for tooling that reads it
    shutil.copy2(en / "Element.tsv", en / "Element.csv")
    print(f"[element] {len(rows)} rows (feats+spells) -> LangMod/EN|JP/Element.xlsx")
    return len(rows)


def write_layout_readme(mod: Path) -> None:
    text = """# Elin runtime asset layout (Workshop-compatible)

This mod now uses the same folders real Workshop mods use:

- `Texture/` — ability icons (`Act*.png` 48x48), system icons (`{System}.png` 128x128), `UI/` chrome, CWL FX strips (`{System}_fx.png`, `ab_*.png`)
- `LangMod/EN/Element.xlsx` — feats + SPELL rows (CWL / ModUtil import)
- `Sound/` — WAV + JSON sidecars (CWL sound ID = filename). Generated from D:\\assets\\audio + Stable Audio 3
- `Asset/` — reserved for UnityFS spell-particle bundles (like Ars Moriendi `ars_spell_particle`). Custom VFX currently ship as Texture/ spritesheets, which CWL loads as PlayEffect IDs.
- `Portrait/` — optional NPC portraits (`UN_*.png`)

Do **not** rely on `Assets/AssetBundles/Windows/*` for gameplay icons or SFX.
Those Unity Editor bundles are authoring leftovers; Elin loads `Texture/` PNGs, `Sound/` clips, and `Asset/` UnityFS FX.
"""
    (mod / "ASSET_LAYOUT.md").write_text(text, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mod-path", default=str(_DEFAULT_MOD))
    ap.add_argument("--skip-textures", action="store_true")
    ap.add_argument("--skip-element", action="store_true")
    args = ap.parse_args()
    mod = Path(args.mod_path)
    if not mod.is_dir():
        print(f"mod missing: {mod}")
        return 1

    cat = load_catalog()
    heroes = cat.get("heroes") or []
    if not heroes:
        # fallback: systems with concepts on disk
        heroes = [{"id": p.stem.replace("elin_", "").replace("_concept", ""), "elinSystem": ""}
                  for p in (_OUTPUT / "Concepts" / "Hero").glob("elin_*_concept.png")]

    data_dir = mod / "MagicPlus" / "Data"
    spells = parse_spell_templates(data_dir) if data_dir.is_dir() else []
    print(f"heroes={len(heroes)} spells={len(spells)}")

    # Ensure Workshop folders exist
    for d in ("Texture", "Portrait", "Sound", "Asset"):
        (mod / d).mkdir(parents=True, exist_ok=True)

    if not args.skip_textures:
        deploy_textures(mod, heroes, spells)
    if not args.skip_element:
        deploy_element(mod, spells)
    write_layout_readme(mod)

    # quick inventory
    tex_n = len(list((mod / "Texture").rglob("*.png")))
    print(f"DONE Texture pngs={tex_n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
