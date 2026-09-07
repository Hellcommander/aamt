#!/usr/bin/env python3
"""Build LivingWeaponSystem.xml, convert parts to modules, retarget icons, fix library UNID."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(r"D:\games\Steam\steamapps\common\Transcendence\Extensions\ZZZ_CrossModCompatibility")
PARTS = ROOT / "LivingWeaponSystem_Parts"
MAP = json.loads((ROOT / "Resources" / "LivingWeapons" / "living_weapon_icon_map.json").read_text(encoding="utf-8"))

PART_FILES = [
    "LivingWeaponSystem_Other.xml",
    "LivingWeaponSystem_FireModules.xml",
    "LivingWeaponSystem_ShieldModules.xml",
    "LivingWeaponSystem_TierMods.xml",
    "LivingWeaponSystem_EvolvedShipMods.xml",
    "LivingWeaponSystem_WildMods.xml",
    "LivingWeaponSystem_EvolvedShips.xml",
    "LivingWeaponSystem_EventHandlers.xml",
]

EXTRAS = """
	<!-- Living weapon level overlays / Discord orb projectile art -->
	<!ENTITY efLivingWeaponLowLevel		"0xE1272000">
	<!ENTITY efLivingWeaponMidLevel		"0xE1272001">
	<!ENTITY efLivingWeaponHighLevel	"0xE1272002">
	<!ENTITY rsLWItemIcons			"0xE1272100">
	<!ENTITY rsLWLevelFX				"0xE1272101">
	<!ENTITY rsDiscordOrb			"0xE1272102">
	<!ENTITY efDiscordOrb			"0xE1272103">
"""


def to_module(text: str) -> str:
    text = re.sub(r"<!DOCTYPE\s+TranscendenceLibrary\s*\[[\s\S]*?\]>\s*", "", text, count=1)
    text = re.sub(r"<TranscendenceLibrary\b[^>]*>", "<TranscendenceModule>", text, count=1)
    text = re.sub(r"</TranscendenceLibrary>", "</TranscendenceModule>", text)
    return text


def retarget(text: str) -> tuple[str, int]:
    count = 0

    def repl_item(m: re.Match) -> str:
        nonlocal count
        block = m.group(0)
        unid = m.group(1)
        if unid not in MAP:
            return block
        c = MAP[unid]
        new_img = (
            f'<Image imageID="&rsLWItemIcons;" '
            f'imageX="{c["x"]}" imageY="{c["y"]}" '
            f'imageWidth="{c["w"]}" imageHeight="{c["h"]}" />'
        )
        nb, n = re.subn(r"<Image\b[^/]*/>", new_img, block, count=1)
        count += n
        return nb

    text = re.sub(
        r"<ItemType\b[^>]*UNID\s*=\s*\"&(it[^;]+);\"[^>]*>[\s\S]*?</ItemType>",
        repl_item,
        text,
    )
    return text, count


def build_library() -> None:
    src = (PARTS / "LivingWeaponSystem_EvolvedShips.xml").read_text(encoding="utf-8")
    # Prefer current file if already converted — fall back to reading from bak
    if "<!DOCTYPE" not in src:
        bak = PARTS / "LivingWeaponSystem_EvolvedShips.xml.bak"
        src = bak.read_text(encoding="utf-8")
    m = re.search(r"<!DOCTYPE\s+TranscendenceLibrary\s*\[([\s\S]*?)\]>", src)
    if not m:
        raise SystemExit("Could not find DOCTYPE entities for library")
    entities = m.group(1)
    entities = re.sub(
        r'(<!ENTITY\s+unidLivingWeaponSystem\s+)"0xE1274000"',
        r'\1"0xE1270000"',
        entities,
    )
    if "rsLWItemIcons" not in entities:
        entities = entities.rstrip() + "\n" + EXTRAS + "\n"

    lib = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TranscendenceLibrary [
{entities}
]>
<TranscendenceLibrary
		apiVersion="59"
		UNID       ="&unidLivingWeaponSystem;"
		name       ="Living Weapon System"
		credits    ="Living Weapon System / CrossMod"
		version    ="1.1">

	<!-- Shared icons, FX, Discord Orb, blade/sword chambers, Leviathan weapons -->
	<Module filename="LivingWeaponSystem_Parts/LivingWeaponSystem_Other.xml"/>
	<Module filename="LivingWeaponSystem_Parts/LivingWeaponSystem_FireModules.xml"/>
	<Module filename="LivingWeaponSystem_Parts/LivingWeaponSystem_ShieldModules.xml"/>
	<Module filename="LivingWeaponSystem_Parts/LivingWeaponSystem_TierMods.xml"/>
	<Module filename="LivingWeaponSystem_Parts/LivingWeaponSystem_EvolvedShipMods.xml"/>
	<Module filename="LivingWeaponSystem_Parts/LivingWeaponSystem_WildMods.xml"/>
	<Module filename="LivingWeaponSystem_Parts/LivingWeaponSystem_EvolvedShips.xml"/>
	<Module filename="LivingWeaponSystem_Parts/LivingWeaponSystem_EventHandlers.xml"/>

</TranscendenceLibrary>
"""
    (ROOT / "LivingWeaponSystem.xml").write_text(lib, encoding="utf-8", newline="\n")
    print("[OK] LivingWeaponSystem.xml")


def convert_parts() -> None:
    total = 0
    for name in PART_FILES:
        path = PARTS / name
        raw = path.read_text(encoding="utf-8")
        if "<TranscendenceLibrary" in raw:
            raw = to_module(raw)
        raw, n = retarget(raw)
        total += n
        path.write_text(raw, encoding="utf-8", newline="\n")
        print(f"[OK] {name}: {n} images")
    print(f"[OK] total images retargeted: {total}")


def fix_library_unid_refs() -> None:
    fixed = 0
    for p in ROOT.rglob("*.xml"):
        if p.name.endswith(".bak") or p.name.endswith(".backup"):
            continue
        t = p.read_text(encoding="utf-8")
        nt = re.sub(
            r'(<!ENTITY\s+unidLivingWeaponSystem\s+)"0xE1274000"',
            r'\1"0xE1270000"',
            t,
        )
        if nt != t:
            p.write_text(nt, encoding="utf-8", newline="\n")
            fixed += 1
            print(f"[OK] library UNID fix {p.relative_to(ROOT)}")
    print(f"[OK] files with library UNID fix: {fixed}")


def main() -> int:
    build_library()
    convert_parts()
    fix_library_unid_refs()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
