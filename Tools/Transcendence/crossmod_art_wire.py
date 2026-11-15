#!/usr/bin/env python3
"""Install engine-correct 120-facing sheets from Output/Facings into CrossMod (ZZZ_CrossModCompatibility).

  python crossmod_art_wire.py [--dry-run]

Organic hulls (Space Whale family, Leviathan): sheets replace the files in Resources/OrganicHulls one for one
(same names, same cell sizes the XML already uses); old files are backed up.

Evolved ships: sheets go to Resources/EvolvedShips; the Living Weapon library gets an rsEvolved* entity per ship
(LivingWeaponSystem.xml DOCTYPE), an image resource in LivingWeaponSystem_Parts/LivingWeaponSystem_EvolvedShipArt.xml
(new module), and each ShipClass gets rotationCount 120 + an <Image>. Ships whose sheet does not exist yet are left
as they are, so the script can be re-run as more hulls are rendered. Every replaced or edited file is backed up to
<game>/_mod_backups/crossmod_art_<date>/.
"""
from __future__ import annotations

import argparse
import re
import shutil
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
FACINGS = HERE / "Output" / "Facings"
GAME = Path(r"D:\games\Steam\steamapps\common\Transcendence")
CM = GAME / "Extensions" / "ZZZ_CrossModCompatibility"
BK = GAME / "_mod_backups" / f"crossmod_art_{date.today():%Y%m%d}"

ORGANIC = {   # facings asset -> poses whose sheets replace Resources/OrganicHulls/<asset>[_pose].jpg
    "scSpaceWhale": ["idle", "mawOpen", "bodyCompress", "bellyGlow"],
    "scSpaceWhaleSegment": ["idle", "bodyCompress"],
    "scSpaceWhaleFluke": ["idle", "bodyCompress"],
    "scSpaceWhaleDrone": ["idle", "bodyCompress"],
    "scLeviathanBase": ["idle", "mawOpen", "bodyCompress", "bellyGlow"],
    "scLeviathanSegment": ["idle", "bodyCompress"],
}

#  ship class        facings asset            entity value   cell
EVOLVED = {
    "scEvolvedFirefly": ("scEvolvedFirefly", "0xE127E00D", 96),
    "scEvolvedWolfen": ("scEvolvedWolfen", "0xE127E00E", 96),
    "scEvolvedSapphire": ("scEvolvedSapphire", "0xE127E00F", 96),
    "scEvolvedCenturion": ("scEvolvedCenturion", "0xE127E010", 128),
    "scCarrierSwarmConstruct": ("scCarrierSwarmConstruct", "0xE127E011", 48),
    "scEvolvedCarrier": ("lwCarrierShip", "0xE127E012", 192),
    "scArchitectConstruct": ("scArchitectConstruct", "0xE127E013", 64),
    "scEvolvedArchitect": ("scEvolvedArchitect", "0xE127E014", 192),
    "scEvolvedSpectre": ("scEvolvedSpectre", "0xE127E015", 96),
    "scEvolvedHullbreaker": ("scEvolvedHullbreaker", "0xE127E016", 128),
    "scEvolvedSentinel": ("lwSentinelShip", "0xE127E017", 128),
    "scEvolvedViper": ("lwViperShip", "0xE127E018", 128),
    "scEvolvedBattery": ("scEvolvedBattery", "0xE127E019", 128),
    "scEvolvedCourser": ("scEvolvedCourser", "0xE127E01A", 128),
}

ART_MODULE = "LivingWeaponSystem_Parts/LivingWeaponSystem_EvolvedShipArt.xml"


def rd(p: Path):
    raw = p.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    return raw[3 if bom else 0:].decode("utf-8"), bom


def wr(p: Path, t: str, bom: bool, dry: bool):
    if not dry:
        p.write_bytes((b"\xef\xbb\xbf" if bom else b"") + t.encode("utf-8"))


def backup(p: Path, dry: bool):
    if p.exists() and not dry:
        dst = BK / p.relative_to(CM)
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)


def sheet(asset: str, pose: str = "idle"):
    name = asset if pose == "idle" else f"{asset}_{pose}"
    jpg, bmp = FACINGS / asset / f"{name}.jpg", FACINGS / asset / f"{name}Mask.bmp"
    return (jpg, bmp) if jpg.is_file() and bmp.is_file() else None


def organic(dry: bool) -> list[str]:
    done = []
    dest = CM / "Resources" / "OrganicHulls"
    for asset, poses in ORGANIC.items():
        for pose in poses:
            s = sheet(asset, pose)
            if not s:
                continue
            for src in s:
                backup(dest / src.name, dry)
                if not dry:
                    shutil.copy2(src, dest / src.name)
            done.append(s[0].stem)
    return done


def evolved(dry: bool) -> list[str]:
    ready = {cls: v for cls, v in EVOLVED.items() if sheet(v[0])}
    if not ready:
        return []
    dest = CM / "Resources" / "EvolvedShips"
    if not dry:
        dest.mkdir(parents=True, exist_ok=True)
    for cls, (asset, _, _) in ready.items():
        for src, name in zip(sheet(asset), (f"{cls}.jpg", f"{cls}Mask.bmp")):
            backup(dest / name, dry)
            if not dry:
                shutil.copy2(src, dest / name)

    # 1. entities in the library root
    root = CM / "LivingWeaponSystem.xml"
    t, bom = rd(root)
    add = "".join(f'\t<!ENTITY rs{cls[2:]}\t\t\t"{v[1]}">\n' for cls, v in ready.items() if f"ENTITY rs{cls[2:]}\t" not in t)
    if add:
        backup(root, dry)
        t = re.sub(r"(\]>)", lambda m: "\t<!-- evolved ship 120-facing art (crossmod_art_wire.py) -->\n" + add + m.group(1), t, count=1)
    if ART_MODULE.split("/")[-1] not in t:
        backup(root, dry)
        t = re.sub(r'(\n[ \t]*<Module filename="LivingWeaponSystem_Parts/LivingWeaponSystem_EvolvedShips\.xml"\s*/>)',
                   lambda m: m.group(1) + f'\n\t<Module filename="{ART_MODULE}"/>', t, count=1)
        assert ART_MODULE in t, "could not register the art module"
    wr(root, t, bom, dry)

    # 2. image resources module (rewritten from the full ready list each run)
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<TranscendenceModule>",
             "\t<!-- Evolved ship 120-facing sheets: engine-correct (column-major, frame 0 nose up, clockwise).",
             "\t     Written by crossmod_art_wire.py from Tools/Transcendence/Output/Facings; tested with tx_image_tester.py. -->"]
    for cls in ready:
        lines.append(f'\t<Image UNID="&rs{cls[2:]};" bitmap="..\\Resources\\EvolvedShips\\{cls}.jpg" '
                     f'bitmask="..\\Resources\\EvolvedShips\\{cls}Mask.bmp" loadOnUse="true"/>')
    lines.append("</TranscendenceModule>")
    mod = CM / ART_MODULE
    backup(mod, dry)
    if not dry:
        mod.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 3. ship classes
    ships = CM / "LivingWeaponSystem_Parts" / "LivingWeaponSystem_EvolvedShips.xml"
    t, bom = rd(ships)
    backup(ships, dry)
    for cls, (_, _, cell) in ready.items():
        m = re.search(r'<ShipClass\b[^>]*?UNID\s*=\s*"&' + cls + r';"[^>]*>', t, re.S)
        assert m, cls
        head = m.group(0)
        if "<Image" in t[m.end():t.find("</ShipClass>", m.end())]:
            continue
        new_head = re.sub(r'rotationCount\s*=\s*"\d+"', 'rotationCount ="120"', head)
        img = (f'\n\t\t<Image imageID="&rs{cls[2:]};" imageWidth="{cell}" imageHeight="{cell}" '
               f'rotationCount="120" rotationColumns="12"/>')
        t = t[:m.start()] + new_head + img + t[m.end():]
    wr(ships, t, bom, dry)
    return list(ready)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    o = organic(a.dry_run)
    e = evolved(a.dry_run)
    print(f"organic sheets installed: {len(o)} {o}")
    print(f"evolved ships wired: {len(e)} {e}")
    print(f"backups: {BK}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
