#!/usr/bin/env python3
"""Apply diagnosed LH_Legacy_Expansion bugfixes that never hit disk."""
from __future__ import annotations

import json
import re
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
MOD = Path(r"D:\User_Directories\Documents\My Games\ElementalReforged\Mods\LH_Legacy_Expansion")
GC = MOD / "Data" / "GameCore"
CUT = MOD / "Data" / "CutScenes" / "LHL_CutscenePacks.xml"
ALIGN = TOOLS / "align_caste_bodies.py"
CFG = TOOLS / "monster_race_config.json"

TEXTURE_BY_ITEM = {
    "LHL_Clothes_Demon_Torso": ("Texture_All", "M_Demon_Texture_01.dds"),
    "LHL_Clothes_Demon_Torso_Alt": ("Texture_All", "M_Demon_Elemental_Texture_01.dds"),
    "LHL_Armor_Demon_Torso": ("Texture_All", "M_Demon_Texture_01.dds"),
    "LHL_Armor_Demon_Torso_Alt": ("Texture_All", "M_Demon_Elemental_Texture_02.dds"),
    "LHL_Weapon_Demon_Main": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Weapon_Demon_Main_Alt": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Clothes_Darkling_Torso": ("Texture_All", "M_Darkling_Texture_01.dds"),
    "LHL_Clothes_Darkling_Torso_Alt": ("Texture_All", "M_Darkling_Texture_01.dds"),
    "LHL_Armor_Darkling_Torso": ("Texture_All", "M_Darkling_Texture_01.dds"),
    "LHL_Armor_Darkling_Torso_Alt": ("Texture_All", "M_Darkling_Texture_01.dds"),
    "LHL_Weapon_Darkling_Main": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Weapon_Darkling_Main_Alt": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Clothes_FireElemental_Torso": ("Texture_All", "M_Fire_Elemental_Texture_01.dds"),
    "LHL_Clothes_FireElemental_Torso_Alt": ("Texture_All", "M_Fire_Elemental_Texture_01.dds"),
    "LHL_Armor_FireElemental_Torso": ("Texture_All", "M_Fire_Elemental_Texture_01.dds"),
    "LHL_Armor_FireElemental_Torso_Alt": ("Texture_All", "M_SuperDemon_FireGiant_Texture_01.dds"),
    "LHL_Weapon_FireElemental_Main": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Weapon_FireElemental_Main_Alt": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Clothes_EarthElemental_Torso": ("Texture_All", "M_EarthElemental_Texture_01.dds"),
    "LHL_Clothes_EarthElemental_Torso_Alt": ("Texture_All", "M_EarthElemental_Texture_01.dds"),
    "LHL_Armor_EarthElemental_Torso": ("Texture_All", "M_EarthElemental_Texture_01.dds"),
    "LHL_Armor_EarthElemental_Torso_Alt": ("Texture_All", "M_SuperDemon_Rock_Texture_01.dds"),
    "LHL_Weapon_EarthElemental_Main": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Weapon_EarthElemental_Main_Alt": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Clothes_AirElemental_Torso": ("Texture_All", "M_AirElemental_Texture_01.dds"),
    "LHL_Clothes_AirElemental_Torso_Alt": ("Texture_All", "M_AirElemental_Texture_01.dds"),
    "LHL_Armor_AirElemental_Torso": ("Texture_All", "M_AirElemental_Texture_01.dds"),
    "LHL_Armor_AirElemental_Torso_Alt": ("Texture_All", "M_SuperDemon_StormLord_Texture_01.dds"),
    "LHL_Weapon_AirElemental_Main": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Weapon_AirElemental_Main_Alt": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Clothes_IceElemental_Torso": ("Texture_All", "M_Demon_Elemental_Texture_03.dds"),
    "LHL_Clothes_IceElemental_Torso_Alt": ("Texture_All", "M_Demon_Elemental_Texture_03.dds"),
    "LHL_Armor_IceElemental_Torso": ("Texture_All", "M_SuperDemon_Yeti_Texture_01.dds"),
    "LHL_Armor_IceElemental_Torso_Alt": ("Texture_All", "M_Demon_Elemental_Texture_03.dds"),
    "LHL_Weapon_IceElemental_Main": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Weapon_IceElemental_Main_Alt": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Clothes_Ogre_Torso": ("Texture_All", "M_Giant_Texture_01.dds"),
    "LHL_Clothes_Ogre_Torso_Alt": ("Texture_All", "M_Giant_Texture_01.dds"),
    "LHL_Armor_Ogre_Torso": ("Texture_All", "M_Giant_Texture_01.dds"),
    "LHL_Armor_Ogre_Torso_Alt": ("Texture_All", "M_Giant_Texture_01.dds"),
    "LHL_Weapon_Ogre_Main": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Weapon_Ogre_Main_Alt": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Clothes_Troll_Torso": ("Texture_All", "M_Giant_Texture_01.dds"),
    "LHL_Clothes_Troll_Torso_Alt": ("Texture_All", "M_Giant_Texture_01.dds"),
    "LHL_Armor_Troll_Torso": ("Texture_All", "M_Giant_Texture_01.dds"),
    "LHL_Armor_Troll_Torso_Alt": ("Texture_All", "M_Giant_Texture_01.dds"),
    "LHL_Weapon_Troll_Main": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Weapon_Troll_Main_Alt": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Clothes_Golem_Torso": ("Texture_All", "M_ScrapGolem_Texture_01.dds"),
    "LHL_Clothes_Golem_Torso_Alt": ("Texture_All", "M_Golem_Texture_01.dds"),
    "LHL_Armor_Golem_Torso": ("Texture_All", "M_Golem_Texture_01.dds"),
    "LHL_Armor_Golem_Torso_Alt": ("Texture_All", "M_Golem_Texture_01.dds"),
    "LHL_Weapon_Golem_Main": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Weapon_Golem_Main_Alt": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Clothes_Drake_Torso": ("Texture_All", "M_Drake_Texture_01.dds"),
    "LHL_Clothes_Drake_Torso_Alt": ("Texture_All", "M_Drake_Slag_Texture_01.dds"),
    "LHL_Armor_Drake_Torso": ("Texture_All", "M_Drake_Slag_Texture_01.dds"),
    "LHL_Armor_Drake_Torso_Alt": ("Texture_All", "M_Drake_Texture_01.dds"),
    "LHL_Weapon_Drake_Main": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Weapon_Drake_Main_Alt": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Clothes_Brood_Torso": ("Texture_All", "M_Spider_Texture_01.dds"),
    "LHL_Clothes_Brood_Torso_Alt": ("Texture_All", "M_Spider_Texture_02.dds"),
    "LHL_Armor_Brood_Torso": ("Texture_All", "M_Spider_Texture_02.dds"),
    "LHL_Armor_Brood_Torso_Alt": ("Texture_All", "M_Spider_Texture_01.dds"),
    "LHL_Weapon_Brood_Main": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Weapon_Brood_Main_Alt": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Clothes_Dragon_Torso": ("Texture_All", "M_Drake_Texture_01.dds"),
    "LHL_Clothes_Dragon_Torso_Alt": ("Texture_All", "M_Drake_Slag_Texture_01.dds"),
    "LHL_Armor_Dragon_Torso": ("Texture_All", "M_Drake_Slag_Texture_01.dds"),
    "LHL_Armor_Dragon_Torso_Alt": ("Texture_All", "M_Drake_Texture_01.dds"),
    "LHL_Weapon_Dragon_Main": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Weapon_Dragon_Main_Alt": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Clothes_Skath_Torso": ("Texture_All", "M_Warg_Skath_Texture_01.dds"),
    "LHL_Clothes_Skath_Torso_Alt": ("Texture_All", "M_Warg_Skath_Texture_01.dds"),
    "LHL_Armor_Skath_Torso": ("Texture_All", "M_Warg_Texture_01.dds"),
    "LHL_Armor_Skath_Torso_Alt": ("Texture_All", "M_Warg_Skath_Texture_01.dds"),
    "LHL_Weapon_Skath_Main": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Weapon_Skath_Main_Alt": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Clothes_Warg_Torso": ("Texture_All", "M_Warg_Texture_01.dds"),
    "LHL_Clothes_Warg_Torso_Alt": ("Texture_All", "M_Warg_Texture_01.dds"),
    "LHL_Armor_Warg_Torso": ("Texture_All", "M_Warg_Texture_01.dds"),
    "LHL_Armor_Warg_Torso_Alt": ("Texture_All", "M_Warg_Texture_01.dds"),
    "LHL_Weapon_Warg_Main": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Weapon_Warg_Main_Alt": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Clothes_Shrill_Torso": ("Texture_All", "M_Spider_Texture_01.dds"),
    "LHL_Clothes_Shrill_Torso_Alt": ("Texture_All", "M_Spider_Texture_02.dds"),
    "LHL_Armor_Shrill_Torso": ("Texture_All", "M_Spider_Texture_02.dds"),
    "LHL_Armor_Shrill_Torso_Alt": ("Texture_All", "M_Spider_Texture_01.dds"),
    "LHL_Weapon_Shrill_Main": ("Texture_All", "K_Weapons_Basic_Texture_01"),
    "LHL_Weapon_Shrill_Main_Alt": ("Texture_All", "K_Weapons_Basic_Texture_01"),
}

MESH_BY_ITEM = {
    "LHL_Armor_Demon_Torso": "gfx/hkb/Monsters/M_Demon_Mesh_01.hkb",
    "LHL_Armor_Demon_Torso_Alt": "gfx/hkb/Monsters/M_Demon_Elemental_Mesh_01.hkb",
    "LHL_Armor_FireElemental_Torso": "gfx/hkb/Monsters/M_Fire_Elemental_Mesh_01.hkb",
    "LHL_Armor_FireElemental_Torso_Alt": "gfx/hkb/Monsters/M_Fire_Elemental_Mesh_01.hkb",
    "LHL_Clothes_FireElemental_Torso_Alt": "gfx/hkb/Monsters/M_Fire_Elemental_Mesh_01.hkb",
    "LHL_Armor_Ogre_Torso": "gfx/hkb/Monsters/M_Giant_Ogre_Mesh_01.hkb",
    "LHL_Armor_Ogre_Torso_Alt": "gfx/hkb/Monsters/M_Giant_Warrior_Mesh_01.hkb",
    "LHL_Armor_Troll_Torso_Alt": "gfx/hkb/Monsters/M_Giant_Warrior_Mesh_01.hkb",
    "LHL_Clothes_Golem_Torso_Alt": "gfx/hkb/Monsters/M_Golem_Mesh_02.hkb",
    "LHL_Armor_Golem_Torso_Alt": "gfx/hkb/Monsters/M_Golem_Mesh_02.hkb",
    "LHL_Clothes_EarthElemental_Torso_Alt": "gfx/hkb/Monsters/M_EarthElemental_Mesh_01.hkb",
    "LHL_Armor_EarthElemental_Torso": "gfx/hkb/Monsters/M_EarthElemental_Mesh_01.hkb",
    "LHL_Armor_EarthElemental_Torso_Alt": "gfx/hkb/Monsters/M_EarthElemental_Mesh_01.hkb",
    "LHL_Armor_AirElemental_Torso_Alt": "gfx/hkb/Monsters/M_AirElemental_Mesh_01.hkb",
    "LHL_Clothes_AirElemental_Torso_Alt": "gfx/hkb/Monsters/M_AirElemental_Mesh_01.hkb",
    "LHL_Armor_IceElemental_Torso_Alt": "gfx/hkb/Monsters/M_Demon_Elemental_Mesh_01.hkb",
    "LHL_Clothes_IceElemental_Torso_Alt": "gfx/hkb/Monsters/M_Demon_Elemental_Mesh_01.hkb",
    "LHL_Armor_Drake_Torso_Alt": "Gfx\\HKB\\Monsters\\M_Drake_Mesh_01.hkb",
    "LHL_Armor_Dragon_Torso_Alt": "Gfx\\HKB\\Monsters\\M_Drake_Mesh_01.hkb",
    "LHL_Clothes_Skath_Torso_Alt": "gfx/hkb/Monsters/M_Warg_Skath_Mesh_01.hkb",
    "LHL_Armor_Skath_Torso_Alt": "gfx/hkb/Monsters/M_Warg_Skath_Mesh_01.hkb",
    "LHL_Armor_Warg_Torso_Alt": "gfx/hkb/Monsters/M_Warg_Mesh_01.hkb",
    "LHL_Clothes_Brood_Torso_Alt": "gfx/hkb/Monsters/M_Spider_Mesh_01.hkb",
    "LHL_Armor_Brood_Torso_Alt": "gfx/hkb/Monsters/M_Spider_Poison_Mesh_01.hkb",
    "LHL_Clothes_Shrill_Torso_Alt": "gfx/hkb/Monsters/K_SpiderMan_Mesh.hkb",
    "LHL_Armor_Shrill_Torso_Alt": "gfx/hkb/Monsters/M_Spider_Demon_Mesh_01.hkb",
}

CREATE_UNITDESIGN_DEFAULTS = {
    "CreateSovereignScene_Skin": "Default_ChooseSovereign_Skin",
    "CreateSovereignScene_Head": "Default_ChooseSovereign_Head",
    "CreateSovereignScene_Clothes": "Default_ChooseSovereign_Clothes",
    "CreateSovereignScene_Equipment": "Default_ChooseSovereign_Equipment",
    "CustomizeFactionScene": "Default_CustomizeFaction",
    "InfoCardCutScene": "Default_InfoCard",
    "LevelUpScene": "Default_LevelUp",
    "UnitDesign_Close": "Default_UnitDesign_List",
    "UnitDesign_Far": "Default_UnitDesign_Edit",
    "UnitDetailsEquipmentWnd": "Default_UnitDetails",
}

LEADER_OPTS = [
    "LHL_LeaderWarlord",
    "LHL_LeaderSpellweaver",
    "LHL_LeaderSkirmisher",
    "LHL_LeaderWarden",
]


def _mutex_prereqs(siblings: list[str]) -> str:
    chunks = []
    for sib in siblings:
        chunks.append(
            "\t\t\t<Prereq>\n"
            "\t\t\t\t<Type>RestrictedAbilityBonusOption</Type>\n"
            f"\t\t\t\t<Attribute>{sib}</Attribute>\n"
            "\t\t\t</Prereq>"
        )
    return "\n".join(chunks)


def fix_castes() -> None:
    path = GC / "LHL_CasteTraits.xml"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "<!-- LHL leader Caste traits: Champion_History (sovereign History tab), NOT faction traits. -->",
        "<!-- LHL leader Caste traits: Champion_Talent (Talent tab), Type=Ability. NOT Profession/History. -->",
    )
    text = text.replace(
        "<AbilityBonusType>Champion_History</AbilityBonusType>",
        "<AbilityBonusType>Champion_Talent</AbilityBonusType>",
    )

    def patch_parent(m: re.Match[str]) -> str:
        head, body, tail = m.group(1), m.group(2), m.group(3)
        opts = list(
            re.finditer(
                r'(<AbilityBonusOption InternalName="([^"]+)">)([\s\S]*?)(</AbilityBonusOption>)',
                body,
            )
        )
        names = [o.group(2) for o in opts]
        out: list[str] = []
        cursor = 0
        for o in opts:
            out.append(body[cursor : o.start()])
            opt_head, name, opt_body, opt_tail = o.group(1), o.group(2), o.group(3), o.group(4)
            siblings = [n for n in names if n != name]
            opt_body = re.sub(r"<Cost>\d+</Cost>", "<Cost>1</Cost>", opt_body, count=1)
            opt_body = re.sub(
                r"<Type>(?:Aggressive|Spell|Defensive|Army|Ability)</Type>",
                "<Type>Ability</Type>",
                opt_body,
                count=1,
            )
            opt_body = re.sub(
                r"\s*<Prereq>\s*<Type>RestrictedAbilityBonusOption</Type>\s*"
                r"<Attribute>LHL_Caste_[^<]+</Attribute>\s*</Prereq>",
                "",
                opt_body,
            )
            mutex = _mutex_prereqs(siblings)
            if "<Prereq>" in opt_body:
                opt_body = opt_body.replace("<Prereq>", mutex + "\n\t\t\t<Prereq>", 1)
            else:
                opt_body = opt_body.rstrip() + "\n" + mutex + "\n"
            out.append(opt_head + opt_body + opt_tail)
            cursor = o.end()
        out.append(body[cursor:])
        return head + "".join(out) + tail

    text2 = re.sub(
        r'(<AbilityBonus InternalName="LHL_Caste_[^"]+">)([\s\S]*?)(</AbilityBonus>)',
        patch_parent,
        text,
    )
    path.write_text(text2, encoding="utf-8")
    print("fixed castes", path.name)


def fix_leader_mutex() -> None:
    path = GC / "LHL_LeaderOptions.xml"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "Race-gated Caste traits live in LHL_CasteTraits.xml as Champion_History\n"
        "     (History tab — not faction traits).",
        "Race-gated Caste traits live in LHL_CasteTraits.xml as Champion_Talent\n"
        "     (Talent tab — Type=Ability; pairwise mutex).",
    )

    def patch_opt(m: re.Match[str]) -> str:
        head, name, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        siblings = [n for n in LEADER_OPTS if n != name]
        body = re.sub(
            r"\s*<Prereq>\s*<Type>RestrictedAbilityBonusOption</Type>\s*"
            r"<Attribute>LHL_Leader[^<]+</Attribute>\s*</Prereq>",
            "",
            body,
        )
        body = re.sub(
            r"<Type>(?:Aggressive|Spell|Defensive|Army)</Type>",
            "<Type>Ability</Type>",
            body,
            count=1,
        )
        mutex = _mutex_prereqs(siblings)
        if "<Cost>" in body:
            body = re.sub(r"(<Cost>\d+</Cost>)", r"\1\n" + mutex, body, count=1)
        else:
            body = body.rstrip() + "\n" + mutex + "\n"
        return head + body + tail

    text2 = re.sub(
        r'(<AbilityBonusOption InternalName="(LHL_Leader(?:Warlord|Spellweaver|Skirmisher|Warden))">)'
        r"([\s\S]*?)(</AbilityBonusOption>)",
        patch_opt,
        text,
    )
    path.write_text(text2, encoding="utf-8")
    print("fixed leader mutex", path.name)


def fix_armor_rebinds() -> None:
    path = GC / "LHL_GeneratedMonsterArmor.xml"
    text = path.read_text(encoding="utf-8")

    def patch_item(m: re.Match[str]) -> str:
        name, body = m.group(1), m.group(2)
        if name in MESH_BY_ITEM:
            mesh = MESH_BY_ITEM[name]
            body = re.sub(
                r"<ModelFile>[^<]+</ModelFile>",
                lambda _m, v=mesh: f"<ModelFile>{v}</ModelFile>",
                body,
                count=1,
            )
        if name in TEXTURE_BY_ITEM:
            ch, tex = TEXTURE_BY_ITEM[name]
            if re.search(r"<Texture_\w+>[^<]+</Texture_\w+>", body):
                body = re.sub(
                    r"<Texture_\w+>[^<]+</Texture_\w+>",
                    lambda _m, c=ch, t=tex: f"<{c}>{t}</{c}>",
                    body,
                    count=1,
                )
            else:
                body = body.replace(
                    "</ModelFile>",
                    f"</ModelFile>\n          <{ch}>{tex}</{ch}>",
                    1,
                )
        return f'<GameItemType InternalName="{name}">{body}</GameItemType>'

    text2 = re.sub(
        r'<GameItemType InternalName="([^"]+)">(.*?)</GameItemType>',
        patch_item,
        text,
        flags=re.S,
    )
    left = sorted(set(re.findall(r"LHL_[A-Za-z0-9_]+_Texture\.dds", text2)))
    path.write_text(text2, encoding="utf-8")
    print("fixed armor rebinds", path.name, "leftover LHL textures:", len(left))
    for x in left[:20]:
        print("  leftover", x)


def fix_cutscenes() -> None:
    text = CUT.read_text(encoding="utf-8")
    for scene_type, cut_name in CREATE_UNITDESIGN_DEFAULTS.items():
        pat = (
            rf"(<CutSceneDataSubPack>\s*<Type>{re.escape(scene_type)}</Type>\s*"
            rf"<CutSceneName>)[^<]+(</CutSceneName>)"
        )
        text, n = re.subn(pat, rf"\g<1>{cut_name}\g<2>", text)
        print(f"  cutscene {scene_type}: {n}")
    CUT.write_text(text, encoding="utf-8")
    print("fixed cutscenes", CUT.name)


def fix_troll_other() -> None:
    path = GC / "LHL_Wave2Units.xml"
    text = path.read_text(encoding="utf-8")
    m = re.search(
        r'(<UnitType InternalName="Generic_Sovereign_Troll_Other">)([\s\S]*?)(</UnitType>)',
        text,
    )
    if not m:
        print("WARN: Generic_Sovereign_Troll_Other missing")
        return
    body = m.group(2)
    replacements = {
        "ModelPath": r"gfx/hkb/Monsters/M_Giant_Warrior_Mesh_01.hkb",
        "SkeletonPath": r"Gfx\HKB\Monsters\M_Giant_Skeleton_01.hkb",
        "AnimationPack": "TrollWarriorAnimationPack",
        "Texture_Skin": "M_Giant_Texture_01.png",
        "CutSceneDataPack": "TrollWarriorUnitCutscenePack",
    }
    for tag, val in replacements.items():
        body, n = re.subn(
            rf"<{tag}>[^<]*</{tag}>",
            lambda _m, t=tag, v=val: f"<{t}>{v}</{t}>",
            body,
            count=1,
        )
        print(f"  troll other {tag}: {n}")
    text = text[: m.start()] + m.group(1) + body + m.group(3) + text[m.end() :]
    path.write_text(text, encoding="utf-8")
    print("fixed Generic_Sovereign_Troll_Other")


def strip_armor_autocreate() -> None:
    pat = re.compile(
        r"[ \t]*<AutoCreateEquipment>LHL_Armor_[A-Za-z0-9]+_Torso(?:_Alt)?</AutoCreateEquipment>\r?\n"
    )
    total = 0
    for path in sorted(GC.glob("LHL_*.xml")):
        text = path.read_text(encoding="utf-8")
        text2, n = pat.subn("", text)
        if n:
            path.write_text(text2, encoding="utf-8")
            print(f"  stripped {n} AutoCreateEquipment armor from {path.name}")
            total += n
    print("stripped AutoCreateEquipment armor total", total)


def fix_align_generator() -> None:
    text = ALIGN.read_text(encoding="utf-8")
    old_hist = (
        "# History-tab subcategory (Champion_History uses these, not faction Army).\n"
        "HISTORY_TYPE = {\n"
        '    "warrior": "Aggressive",\n'
        '    "mage": "Spell",\n'
        '    "defender": "Defensive",\n'
        '    "skirmisher": "Aggressive",\n'
        '    "beast": "Army",\n'
        '    "fire": "Aggressive",\n'
        "}"
    )
    new_hist = (
        "# Talent-tab subcategory (Champion_Talent uses Type=Ability).\n"
        'TALENT_TYPE = "Ability"'
    )
    if old_hist not in text:
        if "Champion_History" in text or "HISTORY_TYPE" in text:
            raise SystemExit("align_caste_bodies.py: expected HISTORY_TYPE block not found; abort")
        print("align_caste_bodies.py already patched")
        return
    text = text.replace(old_hist, new_hist)
    text = text.replace(
        '        "<!-- LHL leader Caste traits: Champion_History (sovereign History tab), NOT faction traits. -->",\n'
        '        "<!-- Each caste matches one physical body morph (Male / Female / Other). -->",',
        '        "<!-- LHL leader Caste traits: Champion_Talent (Talent tab), Type=Ability. -->",\n'
        '        "<!-- Each caste matches one physical body morph (Male / Female / Other). -->",',
    )
    text = text.replace(
        '        lines.append("\\t\\t<AbilityBonusType>Champion_History</AbilityBonusType>")',
        '        lines.append("\\t\\t<AbilityBonusType>Champion_Talent</AbilityBonusType>")',
    )
    old_tail = (
        '            lines.append("\\t\\t\\t<Cost>0</Cost>")\n'
        '            lines.append(f"\\t\\t\\t<Type>{HISTORY_TYPE[role]}</Type>")\n'
        '            lines.append("\\t\\t\\t<Prereq>")\n'
        '            lines.append("\\t\\t\\t\\t<Type>Race</Type>")\n'
        '            lines.append(f"\\t\\t\\t\\t<Attribute>{race_type}</Attribute>")\n'
        '            lines.append("\\t\\t\\t</Prereq>")\n'
        '            lines.append("\\t\\t</AbilityBonusOption>")'
    )
    new_tail = (
        '            lines.append("\\t\\t\\t<Cost>1</Cost>")\n'
        '            lines.append(f"\\t\\t\\t<Type>{TALENT_TYPE}</Type>")\n'
        "            siblings = [\n"
        "                option_name(race, s)\n"
        "                for s, *_rest in castes\n"
        "                if s != suffix\n"
        "            ]\n"
        "            for sib in siblings:\n"
        '                lines.append("\\t\\t\\t<Prereq>")\n'
        '                lines.append("\\t\\t\\t\\t<Type>RestrictedAbilityBonusOption</Type>")\n'
        '                lines.append(f"\\t\\t\\t\\t<Attribute>{sib}</Attribute>")\n'
        '                lines.append("\\t\\t\\t</Prereq>")\n'
        '            lines.append("\\t\\t\\t<Prereq>")\n'
        '            lines.append("\\t\\t\\t\\t<Type>Race</Type>")\n'
        '            lines.append(f"\\t\\t\\t\\t<Attribute>{race_type}</Attribute>")\n'
        '            lines.append("\\t\\t\\t</Prereq>")\n'
        '            lines.append("\\t\\t</AbilityBonusOption>")'
    )
    if old_tail not in text:
        raise SystemExit("align_caste_bodies.py: expected Cost/Type block not found; abort")
    text = text.replace(old_tail, new_tail)
    ALIGN.write_text(text, encoding="utf-8")
    print("updated", ALIGN.name)


def fix_config_meshes() -> None:
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    races = cfg["races"]
    updates = {
        ("Demon", "armor"): {
            "model": "gfx/hkb/Monsters/M_Demon_Mesh_01.hkb",
            "texture": "M_Demon_Texture_01.dds",
        },
        ("FireElemental", "armor"): {
            "model": "gfx/hkb/Monsters/M_Fire_Elemental_Mesh_01.hkb",
            "texture": "M_Fire_Elemental_Texture_01.dds",
        },
        ("Ogre", "armor"): {
            "model": "gfx/hkb/Monsters/M_Giant_Ogre_Mesh_01.hkb",
            "texture": "M_Giant_Texture_01.dds",
            "textureChannel": "Texture_All",
        },
        ("Troll", "armor"): {
            "model": "gfx/hkb/Monsters/M_Giant_Warrior_Mesh_01.hkb",
            "texture": "M_Giant_Texture_01.dds",
        },
        ("Golem", "armor"): {
            "model": "gfx/hkb/Monsters/M_Golem_Mesh_02.hkb",
            "texture": "M_Golem_Texture_01.dds",
        },
    }
    for (race, kind), patch in updates.items():
        pack = races[race][kind]
        pack.update(patch)
        print(f"  config {race}.{kind} -> {pack['model']}")
    CFG.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print("updated", CFG.name)


def main() -> None:
    print("=== patch_lhl_reported_bugs ===")
    fix_align_generator()
    fix_castes()
    fix_leader_mutex()
    fix_armor_rebinds()
    fix_cutscenes()
    fix_troll_other()
    strip_armor_autocreate()
    fix_config_meshes()
    print("=== done ===")


if __name__ == "__main__":
    main()
