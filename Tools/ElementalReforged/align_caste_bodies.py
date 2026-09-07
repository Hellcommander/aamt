#!/usr/bin/env python3
"""Align leader body morphs (Male/Female/Other) with caste traits.

Each Generic_Sovereign_* form becomes the morphological body for one caste.
RaceConfigs pre-select only the caste that matches the preset sovereign's body
(so AI/presets do not stack all three 0-cost castes).
"""
from __future__ import annotations

import re
import struct
from pathlib import Path

MOD = Path(r"D:\User_Directories\Documents\My Games\ElementalReforged\Mods\LH_Legacy_Expansion")
GC = MOD / "Data" / "GameCore"
ELEMD = MOD / "LH Legacy Expansion.elemd"
OUT = GC / "LHL_CasteTraits.xml"
TOOLS = Path(__file__).resolve().parent

ICON = {
    "warrior": "Ability_PathOfTheWarrior_Icon.dds",
    "mage": "Ability_PathOfTheMage_Icon.dds",
    "defender": "Ability_PathOfTheDefender_Icon.dds",
    "skirmisher": "Ability_PathOfTheAssassin_Icon.dds",
    "beast": "Ability_Beastlord_Icon.dds",
    "fire": "Ability_FireBreath_Icon.dds",
}

# Talent-tab subcategory (Champion_Talent uses Type=Ability).
TALENT_TYPE = "Ability"

RACE_FILE = {
    "Demon": "LHL_ExoticRaceConfigs.xml",
    "FireElemental": "LHL_ExoticRaceConfigs.xml",
    "EarthElemental": "LHL_ExoticRaceConfigs.xml",
    "AirElemental": "LHL_ExoticRaceConfigs.xml",
    "IceElemental": "LHL_ExoticRaceConfigs.xml",
    "Drake": "LHL_MoreExoticRaceConfigs.xml",
    "Golem": "LHL_MoreExoticRaceConfigs.xml",
    "Brood": "LHL_MoreExoticRaceConfigs.xml",
    "Dragon": "LHL_MoreExoticRaceConfigs.xml",
    "Darkling": "LHL_Wave2RaceConfigs.xml",
    "Skath": "LHL_Wave2RaceConfigs.xml",
    "Ogre": "LHL_Wave2RaceConfigs.xml",
    "Warg": "LHL_Wave2RaceConfigs.xml",
    "Shrill": "LHL_Wave2RaceConfigs.xml",
    "Troll": "LHL_Wave2RaceConfigs.xml",
}

UNIT_FILE = {
    "Demon": "LHL_ExoticUnits.xml",
    "FireElemental": "LHL_ExoticUnits.xml",
    "EarthElemental": "LHL_ExoticUnits.xml",
    "AirElemental": "LHL_ExoticUnits.xml",
    "IceElemental": "LHL_ExoticUnits.xml",
    "Drake": "LHL_MoreExoticUnits.xml",
    "Golem": "LHL_MoreExoticUnits.xml",
    "Brood": "LHL_MoreExoticUnits.xml",
    "Dragon": "LHL_MoreExoticUnits.xml",
    "Darkling": "LHL_Wave2Units.xml",
    "Skath": "LHL_Wave2Units.xml",
    "Ogre": "LHL_Wave2Units.xml",
    "Warg": "LHL_Wave2Units.xml",
    "Shrill": "LHL_Wave2Units.xml",
    "Troll": "LHL_Wave2Units.xml",
}


def S(attr, val, txt):
    return ("stat", attr, val, txt)


def A(strval, val, txt):
    return ("army", strval, val, txt)


def M(spell, txt):
    return ("melee", spell, txt)


# form: Male / Female / Other — physical body the player picks via gender UI
# (Other is CanBeDesigned third morph). Each caste owns exactly one morph.
# Tuple: (suffix, display, form, icon_role, desc, mods)
# Preset primary = form matching Sovereign_LHL_* after morph fixes below.
CASTES: dict[str, list[tuple]] = {
    "Demon": [
        ("InfernalWarlord", "Infernal Warlord", "Male", "warrior",
         "Armored demon warlord body. Rules the horde through slaughter and terror.",
         [S("UnitStat_Attack_Pierce", 5, "+5 Attack"), S("UnitStat_HitPoints", 6, "+6 Hit Points"),
          A("A_MonsterAggression", 15, "+15% monster aggression")]),
        ("Bloodbinder", "Bloodbinder", "Female", "mage",
         "Armored demon pact-mage body. Binds demonkind with blood rites and deep fire.",
         [S("UnitStat_Essence", 6, "+6 Essence"),
          A("A_Mana", 30, "+30 starting mana")]),
        ("PitTyrant", "Pit Tyrant", "Other", "defender",
         "Classic pit-demon body. An immovable overlord holding the deep places.",
         [S("UnitStat_Defense_Pierce", 4, "+4 Defense"), S("UnitStat_HitPoints", 8, "+8 Hit Points"),
          A("A_UnitStat_HitPoints", 2, "+2 Hit Points to all units")]),
    ],
    "FireElemental": [
        ("FlameTyrant", "Flame Tyrant", "Male", "fire",
         "Living-flame elemental body. Leads the Embers in an unending advance of fire.",
         [S("UnitStat_Attack_Fire", 6, "+6 Fire Attack"), S("UnitStat_HitPoints", 4, "+4 Hit Points"),
          A("A_UnitStat_Accuracy", 5, "+5 Accuracy to all units")]),
        ("Embersage", "Embersage", "Female", "mage",
         "Magma-demon scholar body. Guides the Embers through study and rite.",
         [S("UnitStat_Essence", 6, "+6 Essence"),
          A("A_Research", 10, "+10% research")]),
        ("Cinderward", "Cinderward", "Other", "defender",
         "Banked-ember body. Near-impossible to snuff out; shields the host.",
         [S("UnitStat_ResistFire", 25, "+25 Fire Resistance"), S("UnitStat_HitPoints", 6, "+6 Hit Points"),
          A("A_UnitStat_MagicResist", 10, "+10 Magic Resist to all units")]),
    ],
    "EarthElemental": [
        ("Stonelord", "Stonelord", "Male", "defender",
         "Living-earth body. A mountain given a crown; endures every siege.",
         [S("UnitStat_Defense_Pierce", 5, "+5 Defense"), S("UnitStat_HitPoints", 10, "+10 Hit Points"),
          A("A_UnitStat_HitPoints", 3, "+3 Hit Points to all units")]),
        ("Quakebringer", "Quakebringer", "Female", "warrior",
         "Obsidian war-golem body. Every step cracks stone and rallies the host.",
         [S("UnitStat_Attack_Pierce", 6, "+6 Attack"), S("UnitStat_HitPoints", 8, "+8 Hit Points"),
          A("A_MaxArmySize", 1, "+1 max army size")]),
        ("CrystalSeer", "Crystal Seer", "Other", "mage",
         "Granite-veined seer body. Reads the deep patterns of soil and crystal.",
         [S("UnitStat_Essence", 6, "+6 Essence"),
          A("A_Research", 10, "+10% research")]),
    ],
    "AirElemental": [
        ("StormHerald", "Storm Herald", "Male", "skirmisher",
         "Gale-form body. Leads the Zephyrs in swift, sudden strikes.",
         [S("UnitStat_Moves", 1, "+1 Movement"), S("UnitStat_CombatSpeed", 4, "+4 Initiative"),
          A("A_UnitStat_CombatSpeed", 2, "+2 Initiative to all units")]),
        ("ZephyrSage", "Zephyr Sage", "Female", "mage",
         "High-wind scholar body. Weaves air into sorcery for the Zephyrs.",
         [S("UnitStat_Essence", 6, "+6 Essence"),
          A("A_Mana", 30, "+30 starting mana")]),
        ("Galewarden", "Galewarden", "Other", "defender",
         "Storm-demon warden body. Guardian of the open sky, hard to pin down.",
         [S("UnitStat_Dodge", 15, "+15 Dodge"), S("UnitStat_HitPoints", 6, "+6 Hit Points"),
          A("A_UnitStat_Dodge", 5, "+5 Dodge to all units")]),
    ],
    "IceElemental": [
        ("FrostTyrant", "Frost Tyrant", "Male", "warrior",
         "Killing-cold body. Sovereign of winter whose touch slows the enemy.",
         [S("UnitStat_Attack_Cold", 6, "+6 Cold Attack"), M("Slow_Effect", "Melee attacks slow the target"),
          A("A_UnitStat_Accuracy", 5, "+5 Accuracy to all units")]),
        ("GlacierWarden", "Glacier Warden", "Female", "defender",
         "Advancing glacier body. A wall of ice that shields the whole host.",
         [S("UnitStat_Defense_Pierce", 5, "+5 Defense"), S("UnitStat_HitPoints", 10, "+10 Hit Points"),
          A("A_UnitStat_HitPoints", 3, "+3 Hit Points to all units")]),
        ("RimeSage", "Rime Sage", "Other", "mage",
         "Rime-wind sage body. Patient intellect frozen sharp; glacial magic.",
         [S("UnitStat_Essence", 6, "+6 Essence"),
          A("A_Research", 10, "+10% research")]),
    ],
    "Drake": [
        ("PackAlpha", "Pack Alpha", "Male", "beast",
         "Pack-drake body. Dominant leader by tooth, claw, and strength.",
         [S("UnitStat_Moves", 1, "+1 Movement"), S("UnitStat_HitPoints", 6, "+6 Hit Points"),
          A("A_MonsterAggression", 15, "+15% monster aggression")]),
        ("SlagBroodmother", "Slag Broodmother", "Female", "fire",
         "Slag-drake matriarch body. Breeds and bloods the next generation.",
         [S("UnitStat_Attack_Fire", 6, "+6 Fire Attack"), S("UnitStat_HitPoints", 8, "+8 Hit Points"),
          A("A_RecruitedMonsterBonusLevels", 1, "+1 level to recruited monsters")]),
        ("SkyHunter", "Sky Hunter", "Other", "skirmisher",
         "Lean pack-hunter body. Marks prey for the whole flight.",
         [S("UnitStat_Accuracy", 8, "+8 Accuracy"), S("UnitStat_CombatSpeed", 4, "+4 Initiative"),
          A("A_UnitStat_Accuracy", 5, "+5 Accuracy to all units")]),
    ],
    "Golem": [
        ("ForgeWarden", "Forge Warden", "Male", "defender",
         "Prime forge-golem body. Plated anchor of the entire legion.",
         [S("UnitStat_Defense_Pierce", 6, "+6 Defense"), S("UnitStat_HitPoints", 12, "+12 Hit Points"),
          A("A_UnitStat_HitPoints", 3, "+3 Hit Points to all units")]),
        ("Runecore", "Runecore", "Female", "mage",
         "Rune-core construct body. Directs the others by living logic.",
         [S("UnitStat_Essence", 6, "+6 Essence"),
          A("A_Research", 10, "+10% research")]),
        ("SiegeColossus", "Siege Colossus", "Other", "warrior",
         "Iron colossus body. Walking siege-engine that leads from the front.",
         [S("UnitStat_Attack_Pierce", 7, "+7 Attack"), S("UnitStat_HitPoints", 10, "+10 Hit Points"),
          A("A_ArmyMaintenance", -15, "-15% army maintenance")]),
    ],
    "Brood": [
        ("SilkweaverAmbusher", "Silkweaver Ambusher", "Male", "skirmisher",
         "Webspinner hunter body. Directs the brood from threads of ambush.",
         [S("UnitStat_Dodge", 15, "+15 Dodge"), S("UnitStat_CombatSpeed", 4, "+4 Initiative"),
          A("A_UnitStat_Dodge", 5, "+5 Dodge to all units")]),
        ("Broodmother", "Broodmother", "Female", "mage",
         "Rock-brood queen body. Egg-queen at the heart of the web.",
         [S("UnitStat_Essence", 6, "+6 Essence"), S("UnitStat_HitPoints", 6, "+6 Hit Points"),
          A("A_MaxArmySize", 1, "+1 max army size")]),
        ("VenomMatriarch", "Venom Matriarch", "Other", "warrior",
         "Venom-harridan body. Fanged ruler whose bite cows the brood.",
         [S("UnitStat_Attack_Poison", 6, "+6 Poison Attack"), M("Poisoned1", "Melee attacks poison the target"),
          A("A_MonsterAggression", 10, "+10% monster aggression")]),
    ],
    "Dragon": [
        ("ElderWyrm", "Elder Wyrm", "Male", "mage",
         "True dragon body. Ancient wyrm whose hoarded lore commands deference.",
         [S("UnitStat_Essence", 8, "+8 Essence"), S("UnitStat_HitPoints", 8, "+8 Hit Points"),
          A("A_Research", 10, "+10% research")]),
        ("AshwingTyrant", "Ashwing Tyrant", "Female", "fire",
         "Slagwing tyrant body. Rules flame and sky by right of fire.",
         [S("UnitStat_Attack_Fire", 8, "+8 Fire Attack"), S("UnitStat_HitPoints", 6, "+6 Hit Points"),
          A("A_UnitStat_Accuracy", 5, "+5 Accuracy to all units")]),
        ("SkySovereign", "Sky Sovereign", "Other", "skirmisher",
         "Drakeblood flyer body. Leads the wyrms in lightning descents.",
         [S("UnitStat_Moves", 1, "+1 Movement"), S("UnitStat_CombatSpeed", 6, "+6 Initiative"),
          A("A_UnitStat_CombatSpeed", 2, "+2 Initiative to all units")]),
    ],
    "Darkling": [
        ("UmbralWarlock", "Umbral Warlock", "Male", "mage",
         "Armored umbral body. Shadow-warlock who binds the darklings.",
         [S("UnitStat_Essence", 6, "+6 Essence"),
          A("A_Mana", 30, "+30 starting mana")]),
        ("ShadowPrince", "Shadow Prince", "Female", "skirmisher",
         "Lean shadow body. Prince of whispers ruling from every umbra.",
         [S("UnitStat_Dodge", 20, "+20 Dodge"), S("UnitStat_CombatSpeed", 4, "+4 Initiative"),
          A("A_UnitStat_Dodge", 5, "+5 Dodge to all units")]),
        ("NightReaver", "Night Reaver", "Other", "warrior",
         "Armored raider body. Killer-lord who takes the first throat.",
         [S("UnitStat_Attack_Pierce", 6, "+6 Attack"), S("UnitStat_ChanceToCrit", 3, "+3 Critical Chance"),
          A("A_MonsterAggression", 10, "+10% monster aggression")]),
    ],
    "Skath": [
        ("Tidecaller", "Tidecaller", "Male", "mage",
         "Mire-skath shaman body. Reads the tides and speaks for deep waters.",
         [S("UnitStat_Essence", 6, "+6 Essence"),
          A("A_Research", 10, "+10% research")]),
        ("CoastalRaider", "Coastal Raider", "Female", "skirmisher",
         "Coastal skath body. Strikes from coast and current.",
         [S("UnitStat_Moves", 1, "+1 Movement"), S("UnitStat_Accuracy", 8, "+8 Accuracy"),
          A("A_UnitStat_Accuracy", 5, "+5 Accuracy to all units")]),
        ("MireWarlord", "Mire Warlord", "Other", "warrior",
         "Rock-skath warlord body. Venom-slick blade ruling the wetlands.",
         [S("UnitStat_Attack_Poison", 6, "+6 Poison Attack"), M("Poisoned1", "Melee attacks poison the target"),
          A("A_MonsterAggression", 10, "+10% monster aggression")]),
    ],
    "Ogre": [
        ("WarChief", "War Chief", "Male", "warrior",
         "Bonehide chieftain body. Biggest, meanest; strength is law.",
         [S("UnitStat_Attack_Pierce", 8, "+8 Attack"), S("UnitStat_HitPoints", 10, "+10 Hit Points"),
          A("A_MonsterAggression", 15, "+15% monster aggression")]),
        ("BonehideBruiser", "Bonehide Bruiser", "Female", "defender",
         "Giant ogre body. Scar-crusted bulk shielding the clan.",
         [S("UnitStat_Defense_Pierce", 5, "+5 Defense"), S("UnitStat_HitPoints", 14, "+14 Hit Points"),
          A("A_UnitStat_HitPoints", 4, "+4 Hit Points to all units")]),
        ("FeastShaman", "Feast Shaman", "Other", "mage",
         "War-ogre shaman body. Keeps the clan fed, fierce, and loyal.",
         [S("UnitStat_Essence", 5, "+5 Essence"),
          A("A_Additive_FoodPerGrain", 2, "+2 food per grain")]),
    ],
    "Warg": [
        ("PackLeader", "Pack Leader", "Male", "beast",
         "Pack-warg alpha body. Howl moves the whole pack as one.",
         [S("UnitStat_Moves", 1, "+1 Movement"), S("UnitStat_HitPoints", 8, "+8 Hit Points"),
          A("A_MonsterAggression", 15, "+15% monster aggression")]),
        ("AlphaPredator", "Alpha Predator", "Female", "warrior",
         "Sandbrute predator body. Leads every hunt to the kill.",
         [S("UnitStat_Attack_Pierce", 7, "+7 Attack"), S("UnitStat_ChanceToCrit", 3, "+3 Critical Chance"),
          A("A_UnitStat_Accuracy", 5, "+5 Accuracy to all units")]),
        ("FrostfurWarden", "Frostfur Warden", "Other", "defender",
         "Ice-warg warden body. Guards the pack through the harshest wilds.",
         [S("UnitStat_Defense_Pierce", 5, "+5 Defense"), S("UnitStat_HitPoints", 8, "+8 Hit Points"),
          A("A_UnitStat_HitPoints", 3, "+3 Hit Points to all units")]),
    ],
    "Shrill": [
        ("Screechlord", "Screechlord", "Male", "skirmisher",
         "Chorus screamer body. Sonic shrieks shatter the line before the swarm hits.",
         [S("UnitStat_Accuracy", 8, "+8 Accuracy"), S("UnitStat_CombatSpeed", 4, "+4 Initiative"),
          A("A_UnitStat_CombatSpeed", 2, "+2 Initiative to all units")]),
        ("ChorusMatron", "Chorus Matron", "Female", "mage",
         "Demon-shrill matron body. Her song is the will of the swarm.",
         [S("UnitStat_Essence", 6, "+6 Essence"),
          A("A_MaxArmySize", 1, "+1 max army size")]),
        ("CaveWarden", "Cave Warden", "Other", "defender",
         "Spiderling cave body. Leads the swarm through darkness untouched.",
         [S("UnitStat_Dodge", 15, "+15 Dodge"), S("UnitStat_HitPoints", 6, "+6 Hit Points"),
          A("A_UnitStat_Dodge", 5, "+5 Dodge to all units")]),
    ],
    "Troll": [
        ("MossboundElder", "Mossbound Elder", "Male", "defender",
         "Mossbound elder body. Slow, unstoppable endurance anchoring the clan.",
         [S("UnitStat_Defense_Pierce", 4, "+4 Defense"), S("UnitStat_HitPoints", 14, "+14 Hit Points"),
          A("A_UnitStat_HitPoints", 4, "+4 Hit Points to all units")]),
        ("WarTroll", "War Troll", "Female", "warrior",
         "Warrior-troll body. Rampaging front-liner hardest to stop.",
         [S("UnitStat_Attack_Pierce", 8, "+8 Attack"), S("UnitStat_HitPoints", 8, "+8 Hit Points"),
          A("A_MonsterAggression", 10, "+10% monster aggression")]),
        ("StoneShaman", "Stone Shaman", "Other", "mage",
         "Shaman-troll body. Mutters old stone-magic guiding the slow rise.",
         [S("UnitStat_Essence", 6, "+6 Essence"),
          A("A_Research", 10, "+10% research")]),
    ],
}

# Preset sovereigns whose named leader is morphologically Female-form caste.
PRESET_FORM_OVERRIDE = {
    "Brood": "Female",       # Harridan Queen Silth -> Broodmother
    "Darkling": "Female",    # Matriarch Veshka -> Shadow Prince (matriarch morph)
}

# Copy Female morph onto Sovereign_LHL_* for those overrides.
PRESET_COPY_FROM = {
    "Brood": "Generic_Sovereign_Brood_Female",
    "Darkling": "Generic_Sovereign_Darkling_Female",
}


def option_name(race: str, suffix: str) -> str:
    return f"LHL_Caste_{race}_{suffix}"


def caste_by_form(race: str, form: str) -> tuple:
    for c in CASTES[race]:
        if c[2] == form:
            return c
    raise KeyError((race, form))


def primary_form(race: str) -> str:
    return PRESET_FORM_OVERRIDE.get(race, "Male")


def render_modifier(mod) -> str:
    kind = mod[0]
    if kind == "stat":
        _, attr, val, txt = mod
        return (
            "\t\t\t<GameModifier>\n"
            "\t\t\t\t<ModType>Unit</ModType>\n"
            "\t\t\t\t<Attribute>AdjustUnitStat</Attribute>\n"
            f"\t\t\t\t<StrVal>{attr}</StrVal>\n"
            f"\t\t\t\t<Value>{val}</Value>\n"
            f"\t\t\t\t<Provides>{txt}</Provides>\n"
            "\t\t\t</GameModifier>"
        )
    if kind == "cast":
        return (
            "\t\t\t<GameModifier>\n"
            "\t\t\t\t<ModType>Unit</ModType>\n"
            "\t\t\t\t<Attribute>CanCastSpells</Attribute>\n"
            "\t\t\t\t<Value>1</Value>\n"
            "\t\t\t\t<Provides>Can cast spells</Provides>\n"
            "\t\t\t</GameModifier>"
        )
    if kind == "melee":
        _, spell, txt = mod
        return (
            "\t\t\t<GameModifier>\n"
            "\t\t\t\t<ModType>Unit</ModType>\n"
            "\t\t\t\t<Attribute>MeleeAppliesSpell</Attribute>\n"
            f"\t\t\t\t<StrVal>{spell}</StrVal>\n"
            f"\t\t\t\t<Provides>{txt}</Provides>\n"
            "\t\t\t</GameModifier>"
        )
    if kind == "army":
        _, strval, val, txt = mod
        return (
            "\t\t\t<GameModifier>\n"
            "\t\t\t\t<ModType>Player</ModType>\n"
            "\t\t\t\t<Attribute>AbilityBonus</Attribute>\n"
            f"\t\t\t\t<StrVal>{strval}</StrVal>\n"
            f"\t\t\t\t<Value>{val}</Value>\n"
            f"\t\t\t\t<Provides>{txt}</Provides>\n"
            "\t\t\t</GameModifier>"
        )
    raise ValueError(mod)


def build_xml() -> str:
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        "<!-- LHL leader Caste traits: Champion_Talent (Talent tab), Type=Ability. -->",
        "<!-- Each caste matches one physical body morph (Male / Female / Other). -->",
        "<AbilityBonuses>",
        '\t<DataChecksum NoParse="1">',
        "\t\t<Translate>DisplayName, Description</Translate>",
        "\t</DataChecksum>",
    ]
    for race, castes in CASTES.items():
        race_type = f"Race_Type_{race}"
        lines.append(f'\t<AbilityBonus InternalName="LHL_Caste_{race}">')
        lines.append("\t\t<AbilityBonusType>Champion_Talent</AbilityBonusType>")
        for suffix, display, form, role, desc, mods in castes:
            opt = option_name(race, suffix)
            full_desc = f"{desc} Body form: {form}."
            lines.append(f'\t\t<AbilityBonusOption InternalName="{opt}">')
            lines.append(f"\t\t\t<DisplayName>{display}</DisplayName>")
            lines.append(f"\t\t\t<Description>{full_desc}</Description>")
            lines.append(f"\t\t\t<Icon>{ICON[role]}</Icon>")
            for mod in mods:
                lines.append(render_modifier(mod))
            lines.append("\t\t\t<Cost>1</Cost>")
            lines.append(f"\t\t\t<Type>{TALENT_TYPE}</Type>")
            siblings = [
                option_name(race, s)
                for s, *_rest in castes
                if s != suffix
            ]
            for sib in siblings:
                lines.append("\t\t\t<Prereq>")
                lines.append("\t\t\t\t<Type>RestrictedAbilityBonusOption</Type>")
                lines.append(f"\t\t\t\t<Attribute>{sib}</Attribute>")
                lines.append("\t\t\t</Prereq>")
            lines.append("\t\t\t<Prereq>")
            lines.append("\t\t\t\t<Type>Race</Type>")
            lines.append(f"\t\t\t\t<Attribute>{race_type}</Attribute>")
            lines.append("\t\t\t</Prereq>")
            lines.append("\t\t</AbilityBonusOption>")
        lines.append("\t</AbilityBonus>")
    lines.append("</AbilityBonuses>")
    lines.append("")
    return "\n".join(lines)


def rename_generic_bodies() -> None:
    by_file: dict[str, list[str]] = {}
    for race in CASTES:
        by_file.setdefault(UNIT_FILE[race], []).append(race)

    for fname, races in by_file.items():
        path = GC / fname
        text = path.read_text(encoding="utf-8")
        for race in races:
            for suffix, display, form, *_rest in CASTES[race]:
                if form == "Male":
                    iname = f"Generic_Sovereign_{race}"
                elif form == "Female":
                    iname = f"Generic_Sovereign_{race}_Female"
                else:
                    iname = f"Generic_Sovereign_{race}_Other"
                pat = rf'(<UnitType InternalName="{re.escape(iname)}">\s*<DisplayName>)[^<]+(</DisplayName>)'
                text2, n = re.subn(pat, rf"\g<1>{display}\g<2>", text, count=1)
                if n != 1:
                    print("rename miss", iname)
                else:
                    text = text2
        path.write_text(text, encoding="utf-8")
        print("renamed bodies in", fname)


def copy_tags(src_block: str, dst_block: str, tags: list[str]) -> str:
    out = dst_block
    for tag in tags:
        m = re.search(rf"<{tag}>([^<]*)</{tag}>", src_block)
        if not m:
            continue
        val = m.group(1)
        out, n = re.subn(
            rf"<{tag}>[^<]*</{tag}>",
            lambda _m, t=tag, v=val: f"<{t}>{v}</{t}>",
            out,
            count=1,
        )
        if n != 1:
            print("copy tag miss", tag)
    return out


def fix_preset_morphs() -> None:
    """Make named queens/matriarchs use their Female commanding morph."""
    visual_tags = [
        "Gender",
        "ModelPath",
        "SkeletonPath",
        "AnimationPack",
        "Texture_Skin",
        "UnitModelType",
        "SoundPack",
        "CutSceneDataPack",
        "Scale",
    ]
    for race, src_name in PRESET_COPY_FROM.items():
        fname = UNIT_FILE[race]
        path = GC / fname
        text = path.read_text(encoding="utf-8")
        dst_name = f"Sovereign_LHL_{race}"
        src_m = re.search(rf'<UnitType InternalName="{re.escape(src_name)}">[\s\S]*?</UnitType>', text)
        dst_m = re.search(rf'<UnitType InternalName="{re.escape(dst_name)}">[\s\S]*?</UnitType>', text)
        if not src_m or not dst_m:
            print("preset morph miss", race)
            continue
        new_dst = copy_tags(src_m.group(0), dst_m.group(0), visual_tags)
        # Also copy first Medallions if present
        med = re.search(r"<Medallions>[\s\S]*?</Medallions>", src_m.group(0))
        if med:
            if "<Medallions>" in new_dst:
                new_dst = re.sub(r"<Medallions>[\s\S]*?</Medallions>", med.group(0), new_dst, count=1)
            else:
                new_dst = new_dst.replace("</UnitType>", f"\t\t{med.group(0)}\n\t</UnitType>")
        text = text[: dst_m.start()] + new_dst + text[dst_m.end() :]
        path.write_text(text, encoding="utf-8")
        print("preset morph", dst_name, "<-", src_name)


def rewrite_configs() -> None:
    """Strip caste refs from RaceConfigs — those slots are faction (Player) traits only."""
    for fname in sorted(set(RACE_FILE.values())):
        path = GC / fname
        text = path.read_text(encoding="utf-8")
        new, n = re.subn(
            r"[ \t]*<SelAbilityBonusOption>LHL_Caste_[^<]+</SelAbilityBonusOption>\r?\n",
            "",
            text,
        )
        if n:
            path.write_text(new, encoding="utf-8")
        print(f"stripped {n} caste SelAbilityBonusOption from {fname}")


def wire_preset_sovereigns() -> None:
    """Give each Sovereign_LHL_* its primary caste as a unit SelectedAbilityBonusOption."""
    by_file: dict[str, list[tuple[str, str]]] = {}
    for race in CASTES:
        form = primary_form(race)
        opt = option_name(race, caste_by_form(race, form)[0])
        by_file.setdefault(UNIT_FILE[race], []).append((race, opt))

    for fname, items in by_file.items():
        path = GC / fname
        text = path.read_text(encoding="utf-8")
        for race, opt in items:
            iname = f"Sovereign_LHL_{race}"
            m = re.search(rf'<UnitType InternalName="{re.escape(iname)}">([\s\S]*?)</UnitType>', text)
            if not m:
                print("missing sovereign", iname)
                continue
            body = m.group(1)
            # Drop any prior LHL_Caste_ SelectedAbilityBonusOption
            body2 = re.sub(
                r"[ \t]*<SelectedAbilityBonusOption>LHL_Caste_[^<]+</SelectedAbilityBonusOption>\r?\n",
                "",
                body,
            )
            if f"<SelectedAbilityBonusOption>{opt}</SelectedAbilityBonusOption>" not in body2:
                # Insert after first SelectedAbilityBonusOption if present, else after RaceType
                insert = f"\t\t<SelectedAbilityBonusOption>{opt}</SelectedAbilityBonusOption>\n"
                sab = re.search(r"(</SelectedAbilityBonusOption>\s*\n)", body2)
                if sab:
                    body2 = body2[: sab.end()] + insert + body2[sab.end() :]
                else:
                    rt = re.search(r"(</RaceType>\s*\n)", body2)
                    if rt:
                        body2 = body2[: rt.end()] + insert + body2[rt.end() :]
                    else:
                        print("no insert point", iname)
                        continue
            text = text[: m.start()] + f'<UnitType InternalName="{iname}">{body2}</UnitType>' + text[m.end() :]
            print("preset caste", iname, "->", opt)
        path.write_text(text, encoding="utf-8")


def sync_leader_forms_names() -> None:
    """Keep add_leader_forms.py display names in sync with caste body names."""
    path = TOOLS / "add_leader_forms.py"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    for race, castes in CASTES.items():
        names = {c[2]: c[1] for c in castes}
        # Replace male_name/female_name/other_name inside that race's FORMS entry.
        block_pat = rf'("{race}":\s*\{{[\s\S]*?\n    \}},)'
        m = re.search(block_pat, text)
        if not m:
            continue
        block = m.group(1)
        for key, form in (("male_name", "Male"), ("female_name", "Female"), ("other_name", "Other")):
            block = re.sub(
                rf'("{key}":\s*")[^"]*(")',
                rf"\g<1>{names[form]}\g<2>",
                block,
                count=1,
            )
        text = text[: m.start()] + block + text[m.end() :]
    path.write_text(text, encoding="utf-8")
    print("synced add_leader_forms.py names")


def main() -> None:
    OUT.write_text(build_xml(), encoding="utf-8")
    total = sum(len(v) for v in CASTES.values())
    print(f"wrote {OUT.name}: {len(CASTES)} races, {total} castes")
    rename_generic_bodies()
    fix_preset_morphs()
    rewrite_configs()
    wire_preset_sovereigns()
    sync_leader_forms_names()
    print("done")


if __name__ == "__main__":
    main()
