#!/usr/bin/env python3
"""Fix Brood gear, add missing race weapons, correct LHL race cameras, update elemd."""
from __future__ import annotations

import json
import re
import struct
from pathlib import Path

from PIL import Image, ImageDraw

from build_armor_xml import build_item
from er_harden_units import harden_mod_units

ROOT = Path(__file__).resolve().parent
CFG_PATH = ROOT / "monster_race_config.json"
MOD = Path(r"D:\User_Directories\Documents\My Games\ElementalReforged\Mods\LH_Legacy_Expansion")
ELEMD = MOD / "LH Legacy Expansion.elemd"


WEAPONS = {
    "Brood": {
        "itemName": "Venom Blade",
        "model": "gfx/hkb/Weapons/W_Dagger_Venomous_01.hkb",
        "texture": "K_Weapons_Basic_Texture_01",
        "textureChannel": "Texture_All",
        "attachment": "hand_right_Lcf",
        "weaponType": "OneHanded",
        "weaponUpgradeType": "Blade",
        "attack": 9,
        "iconStyle": "dagger",
    },
    "Shrill": {
        "itemName": "Chorus Stinger",
        "model": "gfx/hkb/Weapons/W_Dagger_Toxic_01.hkb",
        "texture": "K_Weapons_Basic_Texture_01",
        "textureChannel": "Texture_All",
        "attachment": "hand_right_Lcf",
        "weaponType": "OneHanded",
        "weaponUpgradeType": "Blade",
        "attack": 8,
        "iconStyle": "dagger",
    },
    "Drake": {
        "itemName": "Drake Talon",
        "model": "gfx/hkb/Weapons/W_Axe_01.hkb",
        "texture": "K_Weapons_Basic_Texture_01",
        "textureChannel": "Texture_All",
        "attachment": "hand_right_Lcf",
        "weaponType": "OneHanded",
        "weaponUpgradeType": "Axe",
        "attack": 10,
        "iconStyle": "axe",
    },
    "Dragon": {
        "itemName": "Ashwake Cleaver",
        "model": "gfx/hkb/Weapons/M_GiantGolem_Weapon_Sword_01.hkb",
        "texture": "K_Weapons_Basic_Texture_01",
        "textureChannel": "Texture_All",
        "attachment": "hand_right_Lcf",
        "weaponType": "OneHanded",
        "weaponUpgradeType": "Blade",
        "attack": 12,
        "iconStyle": "sword",
    },
    "Warg": {
        "itemName": "Pack Fang",
        "model": "gfx/hkb/Weapons/W_Dagger_01.hkb",
        "texture": "K_Weapons_Basic_Texture_01",
        "textureChannel": "Texture_All",
        "attachment": "hand_right_Lcf",
        "weaponType": "OneHanded",
        "weaponUpgradeType": "Blade",
        "attack": 8,
        "iconStyle": "dagger",
    },
    "Darkling": {
        "itemName": "Umbral Blade",
        "model": "gfx/hkb/Weapons/W_Dagger_Shadow_01.hkb",
        "texture": "K_Weapons_Basic_Texture_01",
        "textureChannel": "Texture_All",
        "attachment": "hand_right_Lcf",
        "weaponType": "OneHanded",
        "weaponUpgradeType": "Blade",
        "attack": 8,
        "iconStyle": "dagger",
    },
    "FireElemental": {
        "itemName": "Ember Brand",
        "model": "gfx/hkb/Weapons/W_Axe_Burning_01.hkb",
        "texture": "K_Weapons_Basic_Texture_01",
        "textureChannel": "Texture_All",
        "attachment": "hand_right_Lcf",
        "weaponType": "OneHanded",
        "weaponUpgradeType": "Axe",
        "attack": 9,
        "iconStyle": "axe",
    },
    "EarthElemental": {
        "itemName": "Stone Maul",
        "model": "gfx/hkb/Weapons/M_GiantGolem_Weapon_Mace_01.hkb",
        "texture": "K_Weapons_Basic_Texture_01",
        "textureChannel": "Texture_All",
        "attachment": "hand_right_Lcf",
        "weaponType": "Blunt",
        "weaponUpgradeType": "Blunt",
        "attack": 10,
        "iconStyle": "mace",
    },
    "AirElemental": {
        "itemName": "Zephyr Spear",
        "model": "gfx/hkb/Weapons/K_Spear_BoarSpear_Basic_01.hkb",
        "texture": "K_Weapons_Basic_Texture_01",
        "textureChannel": "Texture_All",
        "attachment": "hand_right_Lcf",
        "weaponType": "OneHanded",
        "weaponUpgradeType": "Spear",
        "attack": 8,
        "iconStyle": "spear",
    },
    "IceElemental": {
        "itemName": "Rime Staff",
        "model": "gfx/hkb/Weapons/F_Staff_01.hkb",
        "texture": "K_Weapons_Basic_Texture_01",
        "textureChannel": "Texture_All",
        "attachment": "hand_right_Lcf",
        "weaponType": "Staff",
        "weaponUpgradeType": "Staff",
        "attack": 7,
        "iconStyle": "staff",
    },
}

CAMERA = {
    "Demon": ("AssassinDemonChooseSovereign", "AssassinDemonChooseSovereign"),
    "Darkling": ("SandCrawlerChooseSovereign", "M_DarklingWarrior_UnitDetails"),
    "FireElemental": ("Elemental_ChooseSovereign", "Elemental_ChooseSovereign"),
    "EarthElemental": ("Elemental_ChooseSovereign", "M_EarthElemental_UnitDetails"),
    "AirElemental": ("Elemental_ChooseSovereign", "M_AirElemental_UnitDetails"),
    "IceElemental": ("MinorElemental_ChooseSovereign", "MinorElemental_ChooseSovereign"),
    # BigOgre scene has corrupt FOV (660270); Troll scene is framed for the base
    # Troll mesh; Shrill scene is tuned for 0.5-scale shrills (leader is 2.0);
    # Golem scene is a face cam at 0,50,-40. Use scenes tuned for the actual
    # leader mesh + scale.
    "Ogre": ("OgreChooseSovereign", "M_RegularOgre_UnitDetails"),
    "Troll": ("TrollWarriorChooseSovereign", "TrollWarriorChooseSovereign"),
    "Golem": ("ObsidianGolemChooseSovereign", "M_GuardianStatue_UnitDetails"),
    "Drake": ("BigDrakeChooseSovereign", "M_Drake_UnitDetails"),
    "Brood": ("LargeSpider_ChooseSovereign", "M_LargeSpider_UnitDetails"),
    "Dragon": ("Dragon_ChooseSovereign", "M_Dragon_UnitDetails"),
    "Skath": ("WargChooseSovereign", "M_MireSkath_UnitDetails"),
    "Warg": ("WargChooseSovereign", "M_IceWarg_UnitDetails"),
    "Shrill": ("ShrillLordChooseSovereign", "M_ShrillUnit_Details"),
}


def pack_xml(name: str, choose: str, details: str) -> str:
    scenes = [
        ("ChooseSovereignScene", choose),
        ("CreateSovereignScene_Skin", choose),
        ("CreateSovereignScene_Head", choose),
        ("CreateSovereignScene_Clothes", choose),
        ("CreateSovereignScene_Equipment", choose),
        ("ConversationPopupScene", details),
        ("CustomizeFactionScene", choose),
        ("Diplomacy_K_Hall_1", "Default_Diplomacy"),
        ("Diplomacy_F_Hall_1", "Default_Diplomacy_F"),
        ("DynastyCutScene", "Default_Dynasty"),
        ("FamilyTree", "Default_FamilyTree"),
        ("InfoCardCutScene", details),
        ("ItemShop_K_LowLevel", "Default_ItemShop"),
        ("LevelUpScene", details),
        ("UnitDesign_Close", choose),
        ("UnitDesign_Far", choose),
        ("UnitDetailsEquipmentWnd", details),
        ("RecruitWnd", details),
        ("AIDialogScene", "Default_AIDialogScene"),
        ("TradeEquipmentWndScene", details),
        ("IntroBookCutScene", "IntroBookCutSceneCamera"),
        ("ResearchWnd_LevelUp", "Default_ResearchLevelUp"),
    ]
    body = "\n".join(
        f"""    <CutSceneDataSubPack>
      <Type>{typ}</Type>
      <CutSceneName>{scene}</CutSceneName>
    </CutSceneDataSubPack>"""
        for typ, scene in scenes
    )
    return f"""  <CutSceneDataPack InternalName="{name}">
{body}
  </CutSceneDataPack>
"""


def replace_model(internal: str, new_model: str, content: str) -> str:
    pat = rf'(<GameItemType InternalName="{re.escape(internal)}">[\s\S]*?<ModelFile>)([^<]+)(</ModelFile>)'
    m = re.search(pat, content)
    if not m:
        print("missing", internal)
        return content
    return content[: m.start(2)] + new_model + content[m.end(2) :]


def rewrite_elemd(path: Path, extra_files: list[str]) -> None:
    raw = path.read_bytes()
    marker = "LH_Legacy_Banner.png".encode("utf-16-le")
    idx = raw.find(marker)
    if idx < 0:
        raise SystemExit("banner marker missing")
    after = idx + len(marker)
    count_off = after + 8
    old_count = struct.unpack_from("<I", raw, count_off)[0]
    files_off = count_off + 8
    i = files_off
    files: list[str] = []
    while i + 8 <= len(raw):
        nchars, typ = struct.unpack_from("<II", raw, i)
        if typ != 2:
            break
        s = raw[i + 8 : i + 8 + nchars * 2].decode("utf-16-le")
        files.append(s)
        i = i + 8 + nchars * 2
    for f in extra_files:
        if f not in files:
            files.append(f)
    files = sorted(set(files))
    out = bytearray(raw[:count_off])
    out += struct.pack("<II", len(files), 0)
    for f in files:
        out += struct.pack("<II", len(f), 2)
        out += f.encode("utf-16-le")
    out += struct.pack("<IIII", 1, 0, 0, 0)
    path.write_bytes(bytes(out))
    print(f"elemd files {old_count} -> {len(files)}")


def main() -> None:
    cfg = json.loads(CFG_PATH.read_text(encoding="utf-8"))

    # Brood spider meshes
    cfg["races"]["Brood"]["clothes"]["model"] = "gfx/hkb/Monsters/M_Spider_Mesh_01.hkb"
    cfg["races"]["Brood"]["clothes"]["texture"] = "M_Spider_Texture_01.dds"
    cfg["races"]["Brood"]["armor"]["model"] = "gfx/hkb/Monsters/M_Spider_Poison_Mesh_01.hkb"
    cfg["races"]["Brood"]["armor"]["texture"] = "M_Spider_Texture_02.dds"

    for rk, w in WEAPONS.items():
        if "weapon" not in cfg["races"][rk]:
            cfg["races"][rk]["weapon"] = w

    packs = []
    for rk, (choose, details) in CAMERA.items():
        pname = f"LHL_{rk}UnitCutscenePack"
        packs.append(pack_xml(pname, choose, details))
        cfg["races"][rk].setdefault("presentation", {})["cutSceneDataPack"] = pname

    CFG_PATH.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print("config updated")

    cut_dir = MOD / "Data" / "CutScenes"
    cut_dir.mkdir(parents=True, exist_ok=True)
    cut_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<!-- LHL race camera packs: Unit Design / Details use race-framed cameras -->
<CutScenes>
  <DataChecksum NoParse="1">
    <Ignore></Ignore>
  </DataChecksum>
{chr(10).join(packs)}
</CutScenes>
"""
    (cut_dir / "LHL_CutscenePacks.xml").write_text(cut_xml, encoding="utf-8")
    print("wrote cutscene packs", len(packs))

    armor_path = MOD / "Data" / "GameCore" / "LHL_GeneratedMonsterArmor.xml"
    text = armor_path.read_text(encoding="utf-8")
    text = replace_model("LHL_Clothes_Brood_Torso", "gfx/hkb/Monsters/M_Spider_Mesh_01.hkb", text)
    text = replace_model("LHL_Clothes_Brood_Torso_Alt", "gfx/hkb/Monsters/M_Spider_Rock_Mesh_01.hkb", text)
    text = replace_model("LHL_Armor_Brood_Torso", "gfx/hkb/Monsters/M_Spider_Poison_Mesh_01.hkb", text)
    text = replace_model("LHL_Armor_Brood_Torso_Alt", "gfx/hkb/Monsters/M_Spider_Demon_Mesh_01.hkb", text)

    items_dir = MOD / "Gfx" / "Items"
    armor_tex_dir = MOD / "Gfx" / "HKB" / "Armor"
    items_dir.mkdir(parents=True, exist_ok=True)
    armor_tex_dir.mkdir(parents=True, exist_ok=True)

    new_chunks: list[str] = []
    for rk in WEAPONS:
        for alt in (False, True):
            internal = f"LHL_Weapon_{rk}_Main" + ("_Alt" if alt else "")
            if f'InternalName="{internal}"' in text:
                continue
            icon = f"{internal}_Icon.png"
            pal = cfg["races"][rk].get("palette") or ["#444", "#888", "#ccc", "#222"]
            img = Image.new("RGBA", (128, 128), (20, 20, 24, 255))
            d = ImageDraw.Draw(img)
            d.polygon([(64, 16), (72, 70), (64, 112), (56, 70)], fill=pal[2])
            d.rectangle([58, 90, 70, 118], fill=pal[1])
            img.save(items_dir / icon)
            tex = Image.new("RGB", (64, 64), pal[0])
            tex.save(armor_tex_dir / f"{internal}_Texture.png")
            pack = dict(cfg["races"][rk]["weapon"])
            chunk = build_item(cfg, rk, "weapon", icon, pack=pack, alt=alt)
            new_chunks.append(chunk)
            print("added", internal)

    if new_chunks:
        text = text.replace("</GameItemTypes>", "\n".join(new_chunks) + "\n</GameItemTypes>")
    armor_path.write_text(text, encoding="utf-8")
    print("armor xml updated, new weapons", len(new_chunks))

    rewrite_elemd(
        ELEMD,
        [
            r"Data\GameCore\LHL_ExpandedTraits.xml",
            r"Data\CutScenes\LHL_CutscenePacks.xml",
        ],
    )

    report = harden_mod_units(MOD, cfg)
    print("harden", report["totals"])
    print("done")


if __name__ == "__main__":
    main()
