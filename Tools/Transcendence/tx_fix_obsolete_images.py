#!/usr/bin/env python3
"""
tx_fix_obsolete_images.py - find (and optionally fix) mod ShipClasses that still use retired TransCore ship images.

TransCore marks old sprite sheets (rsMediumShips1, rsAquila, ...) obsoleteVersion="45..52". An extension whose
apiVersion is at or past that number cannot see the image: the game logs "Unknown image: <unid>" and stops loading
the adventure. This happens a lot with old mods whose apiVersion was raised to 59 to get them to load.

The fix is the image vanilla uses today for the same ship:
  1. the mod overrides a vanilla ShipClass (same UNID)  -> that class's current <Image>
  2. the mod points at a cell of an old sheet            -> the vanilla ship that used that cell (2017 TransCore)
  3. the mod uses a whole retired single-ship image      -> the vanilla ship that used it
Replacement tags use literal hex UNIDs, so the mod needs no new entity declarations.

Usage:
  python tx_fix_obsolete_images.py <extension folder or xml> [...]          report only
  python tx_fix_obsolete_images.py <folder> --write                         patch (backs up each file first)
  python tx_fix_obsolete_images.py --build-map --old-core <2017 TransCore> --core <current TransCore>

The map (data/obsolete_ship_image_map.json) is built once from the upstream TransCore of commit a4953d3d^ (2017,
the last one with sheet-cell ship images) and the current TransCore; it ships with the toolkit.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import json
import os
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP_PATH = HERE / "data" / "obsolete_ship_image_map.json"
DEFAULT_CORE = Path(r"D:\games\Steam\steamapps\common\Transcendence\game_and_dlc_source\TranscendenceDev-master\Transcendence\TransCore")

ENTITY_RE = re.compile(r'<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"')
SHIP_RE = re.compile(r'<ShipClass\b[^>]*?\bUNID\s*=\s*"([^"]+)".*?</ShipClass>', re.S)
IMAGE_RE = re.compile(r'<Image\s+imageID="([^"]+)"[^>]*/>')
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def read(p) -> str:
    return open(p, "rb").read().decode("utf-8", errors="surrogateescape")


def entities(paths) -> dict[str, int]:
    out: dict[str, int] = {}
    for p in paths:
        for n, v in ENTITY_RE.findall(read(p)):
            out[n.lower()] = int(v, 16)
    return out


def resolve(ref: str, ent: dict[str, int]):
    ref = ref.strip()
    m = re.fullmatch(r"&(\w+);", ref)
    if m:
        return ent.get(m.group(1).lower())
    try:
        return int(ref, 16) if ref.lower().startswith("0x") else int(ref)
    except ValueError:
        return None


def attrs(tag: str) -> dict[str, str]:
    return dict(re.findall(r'(\w+)="([^"]*)"', tag))


def build_map(old_core: Path, core: Path) -> dict:
    core_files = glob.glob(str(core / "**" / "*.xml"), recursive=True)
    old_files = glob.glob(str(old_core / "**" / "*.xml"), recursive=True)
    ent = entities(core_files)
    old_ent = entities(old_files)

    obsolete = {}
    for p in core_files:
        for m in re.finditer(r'<Image\s+UNID="&(\w+);"[^>]*obsoleteVersion="(\d+)"', COMMENT_RE.sub("", read(p))):
            if m.group(1).lower() in ent:
                obsolete[ent[m.group(1).lower()]] = {"name": m.group(1), "obsoleteVersion": int(m.group(2))}

    current = {}   # ship unid -> current Image tag (imageID as hex)
    parent = {}    # ship unid -> inherited ship unid (ships that take their image from a base class)
    for p in core_files:
        for m in SHIP_RE.finditer(COMMENT_RE.sub("", read(p))):
            su = resolve(m.group(1), ent)
            if su is None:
                continue
            head = m.group(0)[:m.group(0).find(">") + 1]
            inh = re.search(r'\binherit\s*=\s*"([^"]+)"', head)
            im = IMAGE_RE.search(m.group(0))
            iu = resolve(im.group(1), ent) if im else None
            if iu is None or iu in obsolete:
                if inh:
                    pu = resolve(inh.group(1), ent)
                    if pu is not None:
                        parent[su] = pu
                continue
            a = attrs(im.group(0))
            a["imageID"] = f"0x{iu:08X}"
            current[su] = a
    for su, pu in parent.items():
        seen = set()
        while pu not in current and pu in parent and pu not in seen:
            seen.add(pu)
            pu = parent[pu]
        if pu in current and su not in current:
            current[su] = current[pu]

    cells = {}     # "imageunid:x:y" -> ship unid (2017)
    for p in old_files:
        for m in SHIP_RE.finditer(COMMENT_RE.sub("", read(p))):
            su = resolve(m.group(1), old_ent)
            im = IMAGE_RE.search(m.group(0))
            if su is None or not im:
                continue
            iu = resolve(im.group(1), old_ent)
            if iu not in obsolete:
                continue
            a = attrs(im.group(0))
            key = f"0x{iu:08X}:{a.get('imageX', '0')}:{a.get('imageY', '0')}"
            cells.setdefault(key, f"0x{su:08X}")
    # whole images / cells already gone by 2017 (last vanilla owner found in upstream git history)
    manual = {("rsLargeShips1", "1344", "0"): "scScarabFreighter", ("rsLargeShips2", "0", "0"): "scCSCTerra",
              ("rsMediumShips1", "768", "0"): "scWolfen", ("rsCorporateCruiser", "0", "0"): "scCorporateCruiser",
              ("rs1MAutonHD", "0", "0"): "sc1MBattleAuton", ("rsAutosentinelHD", "0", "0"): "scAutoSentinel",
              ("rsMediumAutonHD", "0", "0"): "sc200ADefenderAuton", ("rsTenhoveHD", "0", "0"): "scTenhoveSentinel"}
    for (img, x, y), ship in manual.items():
        if img.lower() in ent and ship.lower() in ent:
            cells[f"0x{ent[img.lower()]:08X}:{x}:{y}"] = f"0x{ent[ship.lower()]:08X}"

    names = {v: k for k, v in ent.items() if k.startswith("sc")}  # lowercased names
    return {
        "source": "obsolete = current TransCore obsoleteVersion images; cells = upstream TransCore a4953d3d^ (2017)",
        "obsolete": {f"0x{k:08X}": v for k, v in obsolete.items()},
        "current": {f"0x{k:08X}": {"ship": names.get(k, ""), "image": v} for k, v in current.items()},
        "cells": cells,
    }


def module_api(text: str):
    m = re.search(r'<Transcendence(?:Extension|Library|Adventure)\b[^>]*?\bapiVersion="(\d+)"', text, re.S)
    return int(m.group(1)) if m else None


def tag_from(a: dict[str, str]) -> str:
    order = ["imageID", "imageX", "imageY", "imageWidth", "imageHeight", "rotationOffset", "rotationCount",
             "rotationColumns", "viewportRatio", "imageFrameCount", "imageTicksPerFrame"]
    keys = [k for k in order if k in a] + [k for k in a if k not in order]
    return "<Image " + " ".join(f'{k}="{a[k]}"' for k in keys) + "/>"


def scan_file(path: str, mp: dict, core_ent: dict[str, int], parent_api):
    raw = read(path)
    text = COMMENT_RE.sub(lambda m: " " * len(m.group(0)), raw)   # keep offsets
    local = {n.lower(): int(v, 16) for n, v in ENTITY_RE.findall(raw)}
    ent = {**core_ent, **local}
    api = module_api(text) or parent_api
    found = []
    for sm in SHIP_RE.finditer(text):
        su = resolve(sm.group(1), ent)
        for im in IMAGE_RE.finditer(sm.group(0)):
            iu = resolve(im.group(1), ent)
            if iu is None:
                continue
            ob = mp["obsolete"].get(f"0x{iu:08X}")
            if not ob or (api is not None and api < ob["obsoleteVersion"]):
                continue
            a = attrs(im.group(0))
            how, rep = None, None
            if su is not None and f"0x{su:08X}" in mp["current"]:
                how, rep = "vanilla override", mp["current"][f"0x{su:08X}"]
            if not rep:
                # mod copy of a vanilla ship named after it: scFooNPC / scDSFoo -> scFoo
                nm = re.fullmatch(r"&(\w+);", sm.group(1).strip())
                if nm:
                    base = re.sub(r"NPC$", "", nm.group(1))
                    base = re.sub(r"^scDS(?=[A-Z])", "sc", base)
                    bu = core_ent.get(base.lower()) if base != nm.group(1) else None
                    if bu is not None and f"0x{bu:08X}" in mp["current"]:
                        how, rep = f"named after {base}", mp["current"][f"0x{bu:08X}"]
            if not rep:
                exact = f"0x{iu:08X}:{a.get('imageX', '0')}:{a.get('imageY', '0')}"
                keys = [exact]
                # a single-ship image used whole: only when the old core never cut it into cells
                if not any(k.startswith(f"0x{iu:08X}:") and k != f"0x{iu:08X}:0:0" for k in mp["cells"]):
                    keys.append(f"0x{iu:08X}:0:0")
                for key in keys:
                    ship = mp["cells"].get(key)
                    if ship and ship in mp["current"]:
                        how, rep = f"old sheet cell -> {mp['current'][ship]['ship'] or ship}", mp["current"][ship]
                        break
            if not rep and a.get("imageWidth") == "0":
                # deliberately invisible ship (0x0 cell): any live image keeps it invisible
                live = next(iter(mp["current"].values()))["image"]["imageID"]
                how, rep = "invisible 0x0 placeholder", {"image": {**a, "imageID": live}}
            if not rep:
                how = f"no vanilla equivalent (cell {a.get('imageX', '0')},{a.get('imageY', '0')} {a.get('imageWidth', '?')}px)"
            start = sm.start() + im.start()
            found.append({"file": path, "ship": sm.group(1), "image": im.group(1), "retired": ob["name"],
                          "obsoleteVersion": ob["obsoleteVersion"], "api": api, "how": how,
                          "old": im.group(0), "start": start, "end": start + len(im.group(0)),
                          "new": tag_from(rep["image"]) if rep else None})
    return found


def iter_xml(targets):
    for t in targets:
        p = Path(t)
        if p.is_file():
            yield p, None
        else:
            # modules inherit the API of the extension that includes them: use the folder's highest apiVersion
            files = sorted(p.rglob("*.xml"))
            apis = [module_api(read(f)) for f in files]
            folder_api = max([a for a in apis if a] or [None]) if any(apis) else None
            for f in files:
                yield f, folder_api


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="*")
    ap.add_argument("--write", action="store_true", help="patch the files (each backed up first)")
    ap.add_argument("--core", default=str(DEFAULT_CORE), help="current TransCore folder (for entity names)")
    ap.add_argument("--build-map", action="store_true")
    ap.add_argument("--old-core", help="2017 TransCore folder (with --build-map)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.build_map:
        mp = build_map(Path(a.old_core), Path(a.core))
        MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
        MAP_PATH.write_text(json.dumps(mp, indent=1), encoding="utf-8")
        print(f"map: {len(mp['obsolete'])} retired images, {len(mp['current'])} ships, {len(mp['cells'])} sheet cells -> {MAP_PATH}")
        return 0
    if not a.targets:
        ap.error("give an extension folder or xml")

    mp = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    core_ent = entities(glob.glob(str(Path(a.core) / "*.xml")))
    hits = []
    for f, api in iter_xml(a.targets):
        hits += scan_file(str(f), mp, core_ent, api)

    if a.json:
        print(json.dumps([{k: v for k, v in h.items() if k not in ("start", "end")} for h in hits], indent=1))
    else:
        for h in hits:
            mark = "FIX " if h["new"] else "MANUAL"
            print(f"{mark} {os.path.basename(h['file'])}  {h['ship']}  {h['image']} ({h['retired']}, retired at API {h['obsoleteVersion']}, mod API {h['api']})"
                  + f"  [{h['how']}]")
        fixable = sum(1 for h in hits if h["new"])
        print(f"{len(hits)} retired ship images, {fixable} fixable, {len(hits) - fixable} need a manual image")

    if a.write:
        stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        by_file: dict[str, list] = {}
        for h in hits:
            if h["new"]:
                by_file.setdefault(h["file"], []).append(h)
        for f, hs in by_file.items():
            raw = open(f, "rb").read()
            text = raw.decode("utf-8", errors="surrogateescape")
            shutil.copy2(f, f"{f}.bak_{stamp}_obsimg")
            for h in sorted(hs, key=lambda h: h["start"], reverse=True):
                assert text[h["start"]:h["end"]] == h["old"], f"offset drift in {f}"
                text = text[:h["start"]] + h["new"] + text[h["end"]:]
            open(f, "wb").write(text.encode("utf-8", errors="surrogateescape"))
            print(f"patched {len(hs)} in {f}  (backup .bak_{stamp}_obsimg)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
