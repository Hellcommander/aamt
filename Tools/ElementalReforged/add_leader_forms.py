#!/usr/bin/env python3
"""Add leader form choices (Male/Female sovereign templates) + Player archetypes."""
from __future__ import annotations

import re
import struct
from pathlib import Path

MOD = Path(r"D:\User_Directories\Documents\My Games\ElementalReforged\Mods\LH_Legacy_Expansion")
GC = MOD / "Data" / "GameCore"
ELEMD = MOD / "LH Legacy Expansion.elemd"

# Female form = alternate leader mesh. Other = third body for unit/sovereign Other slot.
FORMS = {
    "Demon": {
        "file": "LHL_ExoticUnits.xml",
        "race": "Race_Type_Demon",
        "male_name": "Infernal Warlord",
        "female_name": "Bloodbinder",
        "other_name": "Pit Tyrant",
        # Leaders use AssassinDemon body + Infernal Carapace (Fire Demon mesh as armor).
        "female_model": "gfx/hkb/Monsters/M_Demon_Mesh_01.hkb",
        "female_skin": "M_Demon_Texture_01.png",
        "other_model": "gfx/hkb/Monsters/M_Demon_Mesh_01.hkb",
        "other_skin": "M_Demon_Texture_01.png",
        "medallion": "M_AssassinDemon_01_Card.png",
    },
    "FireElemental": {
        "file": "LHL_ExoticUnits.xml",
        "race": "Race_Type_FireElemental",
        "male_name": "Flame Tyrant",
        "female_name": "Embersage",
        "other_name": "Cinderward",
        # Fire Demon (Delin) is a DEMON — elementals only get elemental bodies.
        # Female form = BurningWraith-style resoln texture variant.
        "female_model": "gfx/hkb/Monsters/M_Fire_Elemental_Mesh_01.hkb",
        "female_skin": "M_Fire_Elemental_Resoln_Texture_01.dds",
        "other_model": "gfx/hkb/Monsters/M_Fire_Elemental_Mesh_01.hkb",
        "other_skin": "M_Fire_Elemental_Texture_01.png",
        "medallion": None,
    },
    "EarthElemental": {
        "file": "LHL_ExoticUnits.xml",
        "race": "Race_Type_EarthElemental",
        "male_name": "Stonelord",
        "female_name": "Quakebringer",
        "other_name": "Crystal Seer",
        "female_model": "gfx/hkb/Monsters/M_Golem_Mesh_02.hkb",
        "female_skin": "M_Golem_Texture_01.png",
        "other_model": "gfx/hkb/Monsters/M_EarthElemental_Mesh_01.hkb",
        "other_skin": "M_EarthElemental_Texture_01.dds",
        "medallion": None,
    },
    "AirElemental": {
        "file": "LHL_ExoticUnits.xml",
        "race": "Race_Type_AirElemental",
        "male_name": "Storm Herald",
        "female_name": "Zephyr Sage",
        "other_name": "Galewarden",
        "female_model": "gfx/hkb/Monsters/M_AirElemental_Mesh_01.hkb",
        "female_skin": "M_AirElemental_Texture_01.dds",
        "other_model": "gfx/hkb/Monsters/M_Demon_Elemental_Mesh_01.hkb",
        "other_skin": "M_Demon_Elemental_Texture_02.png",
        "medallion": None,
    },
    "IceElemental": {
        "file": "LHL_ExoticUnits.xml",
        "race": "Race_Type_IceElemental",
        "male_name": "Frost Tyrant",
        "female_name": "Glacier Warden",
        "other_name": "Rime Sage",
        "female_model": "gfx/hkb/Monsters/M_Demon_Elemental_Mesh_01.hkb",
        "female_skin": "M_Demon_Elemental_Texture_03.png",
        "other_model": "gfx/hkb/Monsters/M_AirElemental_Mesh_01.hkb",
        "other_skin": "M_AirElemental_Texture_01.dds",
        "medallion": None,
    },
    "Drake": {
        "file": "LHL_MoreExoticUnits.xml",
        "race": "Race_Type_Drake",
        "male_name": "Pack Alpha",
        "female_name": "Slag Broodmother",
        "other_name": "Sky Hunter",
        "female_model": "gfx/hkb/Monsters/M_Drake_Slag_Mesh_01.hkb",
        "female_skin": "M_Drake_Slag_Texture_01.png",
        "other_model": "gfx/hkb/Monsters/M_Drake_Mesh_01.hkb",
        "other_skin": "M_Drake_Texture_01.png",
        "other_scale": "0.7",
        "medallion": "M_Drake_Slag_Card_01.png",
    },
    "Golem": {
        "file": "LHL_MoreExoticUnits.xml",
        "race": "Race_Type_Golem",
        "male_name": "Forge Warden",
        "female_name": "Runecore",
        "other_name": "Siege Colossus",
        "female_model": "gfx/hkb/Monsters/M_Golem_Mesh_02.hkb",
        "female_skin": "M_Golem_Texture_01.png",
        "other_model": "gfx/hkb/Units/K_IronGolem_Mesh_01.hkb",
        "other_skin": "IronGolem.png",
        "medallion": "M_Golem_Card_01.png",
    },
    "Brood": {
        "file": "LHL_MoreExoticUnits.xml",
        "race": "Race_Type_Brood",
        "male_name": "Silkweaver Ambusher",
        "female_name": "Broodmother",
        "other_name": "Venom Matriarch",
        "female_model": "gfx/hkb/Monsters/M_Spider_Rock_Mesh_01.hkb",
        "female_skin": "M_Spider_Texture_01.png",
        "other_model": "gfx/hkb/Monsters/M_Spider_Poison_Mesh_01.hkb",
        "other_skin": "M_Spider_Texture_02.png",
        "medallion": "M_AlbinoRockSpider_Giant_Card_01.png",
        "other_medallion": "M_Ravenous Harridan_Giant_Card_01.png",
    },
    "Dragon": {
        "file": "LHL_MoreExoticUnits.xml",
        "race": "Race_Type_Dragon",
        "male_name": "Elder Wyrm",
        "female_name": "Ashwing Tyrant",
        "other_name": "Sky Sovereign",
        "female_model": "gfx/hkb/Monsters/M_Drake_Slag_Mesh_01.hkb",
        "female_skin": "M_Drake_Slag_Texture_01.png",
        "other_model": "gfx/hkb/Monsters/M_Drake_Mesh_01.hkb",
        "other_skin": "M_Drake_Texture_01.png",
        "medallion": "M_Drake_Slag_Card_01.png",
    },
    "Darkling": {
        "file": "LHL_Wave2Units.xml",
        "race": "Race_Type_Darkling",
        "male_name": "Umbral Warlock",
        "female_name": "Shadow Prince",
        "other_name": "Night Reaver",
        "female_model": "gfx/hkb/Monsters/M_Darkling_Mesh_01.hkb",
        "female_skin": "M_Darkling_Texture_01.png",
        "other_model": "gfx/hkb/Monsters/M_Darkling_Armored_Mesh_01.hkb",
        "other_skin": "M_Darkling_Texture_01.png",
        "medallion": "M_Darkling_Card.png",
    },
    "Skath": {
        "file": "LHL_Wave2Units.xml",
        "race": "Race_Type_Skath",
        "male_name": "Tidecaller",
        "female_name": "Coastal Raider",
        "other_name": "Mire Warlord",
        "female_model": "gfx/hkb/Monsters/M_Warg_Skath_Mesh_01.hkb",
        "female_skin": "M_Warg_Skath_Texture_01.png",
        "other_model": "gfx/hkb/Monsters/M_Warg_Rock_Mesh_01.hkb",
        "other_skin": None,
        "medallion": "M_Warg_IceWarg_Card.png",
    },
    "Ogre": {
        "file": "LHL_Wave2Units.xml",
        "race": "Race_Type_Ogre",
        "male_name": "War Chief",
        "female_name": "Bonehide Bruiser",
        "other_name": "Feast Shaman",
        "female_model": "gfx/hkb/Monsters/M_Giant_Ogre_Mesh_01.hkb",
        "female_skin": "M_Demon_Texture_01.png",
        "other_model": "gfx/hkb/Monsters/M_Giant_Warrior_Mesh_01.hkb",
        "other_skin": "M_Giant_Texture_01.png",
        "medallion": None,
    },
    "Warg": {
        "file": "LHL_Wave2Units.xml",
        "race": "Race_Type_Warg",
        "male_name": "Pack Leader",
        "female_name": "Alpha Predator",
        "other_name": "Frostfur Warden",
        "female_model": "gfx/hkb/Monsters/M_Warg_SandBrute_Mesh_01.hkb",
        "female_skin": "M_Warg_SandBrute_Texture_01.png",
        "other_model": "gfx/hkb/Monsters/M_Warg_Mesh_01.hkb",
        "other_skin": "M_Warg_Texture_01.png",
        "medallion": "M_Warg_PlainsWarg_Card.png",
    },
    "Shrill": {
        "file": "LHL_Wave2Units.xml",
        "race": "Race_Type_Shrill",
        "male_name": "Screechlord",
        "female_name": "Chorus Matron",
        "other_name": "Cave Warden",
        "female_model": "gfx/hkb/Monsters/M_Spider_Demon_Mesh_01.hkb",
        "female_skin": "M_Spider_Texture_02.png",
        "other_model": "gfx/hkb/Monsters/K_SpiderMan_Mesh.hkb",
        "other_skin": "M_Spider_Texture_02.png",
        "medallion": "M_Spider_Corps_Card_01.png",
    },
    "Troll": {
        "file": "LHL_Wave2Units.xml",
        "race": "Race_Type_Troll",
        "male_name": "Mossbound Elder",
        "female_name": "War Troll",
        "other_name": "Stone Shaman",
        "female_model": "gfx/hkb/Monsters/M_Giant_Warrior_Mesh_01.hkb",
        "female_skin": "M_Giant_Texture_01.png",
        "other_model": "gfx/hkb/Monsters/M_Giant_Ogre_Mesh_01.hkb",
        "other_skin": "M_Demon_Texture_01.png",
        "medallion": None,
    },
}

RACE_TYPE_FILES = {
    "Demon": "LHL_ExoticRaceTypes.xml",
    "FireElemental": "LHL_ExoticRaceTypes.xml",
    "EarthElemental": "LHL_ExoticRaceTypes.xml",
    "AirElemental": "LHL_ExoticRaceTypes.xml",
    "IceElemental": "LHL_ExoticRaceTypes.xml",
    "Drake": "LHL_MoreExoticRaceTypes.xml",
    "Golem": "LHL_MoreExoticRaceTypes.xml",
    "Brood": "LHL_MoreExoticRaceTypes.xml",
    "Dragon": "LHL_MoreExoticRaceTypes.xml",
    "Darkling": "LHL_Wave2RaceTypes.xml",
    "Skath": "LHL_Wave2RaceTypes.xml",
    "Ogre": "LHL_Wave2RaceTypes.xml",
    "Warg": "LHL_Wave2RaceTypes.xml",
    "Shrill": "LHL_Wave2RaceTypes.xml",
    "Troll": "LHL_Wave2RaceTypes.xml",
}


def clone_sovereign(base: str, new_name: str, display: str, gender: str, model: str, skin: str, cfg: dict) -> str:
    body = base
    body = re.sub(
        r'InternalName="Generic_Sovereign_[^"]+"',
        lambda _m: f'InternalName="{new_name}"',
        body,
        count=1,
    )
    body = re.sub(
        r"<DisplayName>[^<]*</DisplayName>",
        lambda _m: f"<DisplayName>{display}</DisplayName>",
        body,
        count=1,
    )
    body = re.sub(
        r"<Gender>[^<]*</Gender>",
        lambda _m: f"<Gender>{gender}</Gender>",
        body,
        count=1,
    )
    body = re.sub(
        r"<ModelPath>[^<]*</ModelPath>",
        lambda _m: f"<ModelPath>{model}</ModelPath>",
        body,
        count=1,
    )
    if skin and re.search(r"<Texture_Skin>[^<]*</Texture_Skin>", body):
        body = re.sub(
            r"<Texture_Skin>[^<]*</Texture_Skin>",
            lambda _m: f"<Texture_Skin>{skin}</Texture_Skin>",
            body,
            count=1,
        )
    if cfg.get("medallion"):
        med = cfg["medallion"]
        body = re.sub(
            r"<Medallions>\s*<All>[^<]*</All>\s*</Medallions>",
            lambda _m: f"<Medallions>\n\t\t\t<All>{med}</All>\n\t\t</Medallions>",
            body,
            count=1,
        )
    if cfg.get("other_scale") and "Other" in new_name:
        scale = cfg["other_scale"]
        body = re.sub(
            r"<ModelScale>[^<]*</ModelScale>",
            lambda _m: f"<ModelScale>{scale}</ModelScale>",
            body,
            count=1,
        )
    return body


def rewrite_elemd(extra: list[str]) -> None:
    raw = ELEMD.read_bytes()
    marker = "LH_Legacy_Banner.png".encode("utf-16-le")
    idx = raw.find(marker)
    after = idx + len(marker)
    count_off = after + 8
    old = struct.unpack_from("<I", raw, count_off)[0]
    i = count_off + 8
    files: list[str] = []
    while i + 8 <= len(raw):
        n, typ = struct.unpack_from("<II", raw, i)
        if typ != 2:
            break
        files.append(raw[i + 8 : i + 8 + n * 2].decode("utf-16-le"))
        i += 8 + n * 2
    for f in extra:
        if f not in files:
            files.append(f)
    files = sorted(set(files))
    out = bytearray(raw[:count_off])
    out += struct.pack("<II", len(files), 0)
    for f in files:
        out += struct.pack("<II", len(f), 2)
        out += f.encode("utf-16-le")
    out += struct.pack("<IIII", 1, 0, 0, 0)
    ELEMD.write_bytes(bytes(out))
    print(f"elemd {old} -> {len(files)}")


def write_archetypes() -> Path:
    path = GC / "LHL_LeaderOptions.xml"
    path.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<!-- Leader form note: use Male/Female (and Other where available) on race to pick sovereign body.
     These Player options set the leader's combat role. -->
<AbilityBonuses>
	<DataChecksum NoParse="1">
		<Ignore>DispName</Ignore>
		<Translate>DisplayName,Description</Translate>
	</DataChecksum>
	<AbilityBonus InternalName="LHL_LeaderArchetypeAbility">
		<AbilityBonusType>Player</AbilityBonusType>
		<AbilityBonusOption InternalName="LHL_LeaderWarlord">
			<DisplayName>Warlord</DisplayName>
			<Description>A battle-hardened leader: stronger melee, tougher hide, slower casting.</Description>
			<Icon>Ability_PathOfTheWarrior_Icon.dds</Icon>
			<GameModifier>
				<ModType>Unit</ModType>
				<Attribute>AdjustUnitStat</Attribute>
				<StrVal>UnitStat_Attack_Pierce</StrVal>
				<Value>4</Value>
				<Provides>+4 Pierce Attack</Provides>
			</GameModifier>
			<GameModifier>
				<ModType>Unit</ModType>
				<Attribute>AdjustUnitStat</Attribute>
				<StrVal>UnitStat_HitPoints</StrVal>
				<Value>8</Value>
				<Provides>+8 Hit Points</Provides>
			</GameModifier>
			<GameModifier>
				<ModType>Unit</ModType>
				<Attribute>AdjustUnitStat</Attribute>
				<StrVal>UnitStat_Defense_Pierce</StrVal>
				<Value>2</Value>
				<Provides>+2 Pierce Defense</Provides>
			</GameModifier>
			<GameModifier>
				<ModType>Unit</ModType>
				<Attribute>AdjustUnitStat</Attribute>
				<StrVal>UnitStat_Essence</StrVal>
				<Value>-2</Value>
				<Provides>-2 Essence</Provides>
			</GameModifier>
			<Cost>1</Cost>
		</AbilityBonusOption>
		<AbilityBonusOption InternalName="LHL_LeaderSpellweaver">
			<DisplayName>Spellweaver</DisplayName>
			<Description>A sovereign steeped in lore: more essence and initiative, softer in the crush of melee.</Description>
			<Icon>Ability_PathOfTheMage_Icon.dds</Icon>
			<GameModifier>
				<ModType>Unit</ModType>
				<Attribute>AdjustUnitStat</Attribute>
				<StrVal>UnitStat_Essence</StrVal>
				<Value>6</Value>
				<Provides>+6 Essence</Provides>
			</GameModifier>
			<GameModifier>
				<ModType>Unit</ModType>
				<Attribute>AdjustUnitStat</Attribute>
				<StrVal>UnitStat_CombatSpeed</StrVal>
				<Value>3</Value>
				<Provides>+3 Initiative</Provides>
			</GameModifier>
			<GameModifier>
				<ModType>Unit</ModType>
				<Attribute>CanCastSpells</Attribute>
				<Provides>Can Cast Spells</Provides>
			</GameModifier>
			<GameModifier>
				<ModType>Unit</ModType>
				<Attribute>AdjustUnitStat</Attribute>
				<StrVal>UnitStat_HitPoints</StrVal>
				<Value>-4</Value>
				<Provides>-4 Hit Points</Provides>
			</GameModifier>
			<Cost>1</Cost>
		</AbilityBonusOption>
		<AbilityBonusOption InternalName="LHL_LeaderSkirmisher">
			<DisplayName>Skirmisher</DisplayName>
			<Description>A swift raider-chief: more moves and dodge, lighter blows.</Description>
			<Icon>Ability_PathOfTheRogue_Icon.dds</Icon>
			<GameModifier>
				<ModType>Unit</ModType>
				<Attribute>AdjustUnitStat</Attribute>
				<StrVal>UnitStat_Moves</StrVal>
				<Value>1</Value>
				<Provides>+1 Moves</Provides>
			</GameModifier>
			<GameModifier>
				<ModType>Unit</ModType>
				<Attribute>AdjustUnitStat</Attribute>
				<StrVal>UnitStat_Dodge</StrVal>
				<Value>15</Value>
				<Provides>+15 Dodge</Provides>
			</GameModifier>
			<GameModifier>
				<ModType>Unit</ModType>
				<Attribute>AdjustUnitStat</Attribute>
				<StrVal>UnitStat_CombatSpeed</StrVal>
				<Value>4</Value>
				<Provides>+4 Initiative</Provides>
			</GameModifier>
			<GameModifier>
				<ModType>Unit</ModType>
				<Attribute>AdjustUnitStat</Attribute>
				<StrVal>UnitStat_Attack_Pierce</StrVal>
				<Value>-2</Value>
				<Provides>-2 Pierce Attack</Provides>
			</GameModifier>
			<Cost>1</Cost>
		</AbilityBonusOption>
		<AbilityBonusOption InternalName="LHL_LeaderWarden">
			<DisplayName>Warden</DisplayName>
			<Description>A defensive sovereign: shields and endurance over raw offense.</Description>
			<Icon>Ability_PathOfTheDefender_Icon.dds</Icon>
			<GameModifier>
				<ModType>Unit</ModType>
				<Attribute>AdjustUnitStat</Attribute>
				<StrVal>UnitStat_Defense_Pierce</StrVal>
				<Value>4</Value>
				<Provides>+4 Pierce Defense</Provides>
			</GameModifier>
			<GameModifier>
				<ModType>Unit</ModType>
				<Attribute>AdjustUnitStat</Attribute>
				<StrVal>UnitStat_Defense_Blunt</StrVal>
				<Value>3</Value>
				<Provides>+3 Blunt Defense</Provides>
			</GameModifier>
			<GameModifier>
				<ModType>Unit</ModType>
				<Attribute>AdjustUnitStat</Attribute>
				<StrVal>UnitStat_HitPoints</StrVal>
				<Value>6</Value>
				<Provides>+6 Hit Points</Provides>
			</GameModifier>
			<GameModifier>
				<ModType>Unit</ModType>
				<Attribute>AdjustUnitStat</Attribute>
				<StrVal>UnitStat_CombatSpeed</StrVal>
				<Value>-2</Value>
				<Provides>-2 Initiative</Provides>
			</GameModifier>
			<Cost>1</Cost>
		</AbilityBonusOption>
	</AbilityBonus>
</AbilityBonuses>
""",
        encoding="utf-8",
    )
    return path


def main() -> None:
    # Patch unit files: rename male display, add female+other clones
    by_file: dict[str, list[str]] = {}
    for key, cfg in FORMS.items():
        by_file.setdefault(cfg["file"], []).append(key)

    for fname, keys in by_file.items():
        path = GC / fname
        text = path.read_text(encoding="utf-8")
        for key in keys:
            cfg = FORMS[key]
            base_name = f"Generic_Sovereign_{key}"
            m = re.search(
                rf'(<UnitType InternalName="{re.escape(base_name)}">[\s\S]*?</UnitType>)',
                text,
            )
            if not m:
                print("missing base", base_name)
                continue
            base = m.group(1)
            # Update male display name
            updated = re.sub(
                r"<DisplayName>[^<]*</DisplayName>",
                f"<DisplayName>{cfg['male_name']}</DisplayName>",
                base,
                count=1,
            )
            text = text[: m.start()] + updated + text[m.end() :]

            female_name = f"Generic_Sovereign_{key}_Female"
            other_name = f"Generic_Sovereign_{key}_Other"
            if f'InternalName="{female_name}"' not in text:
                fem = clone_sovereign(
                    updated,
                    female_name,
                    cfg["female_name"],
                    "Female",
                    cfg["female_model"],
                    cfg["female_skin"],
                    {**cfg, "medallion": cfg.get("medallion")},
                )
                # insert after male block
                m2 = re.search(
                    rf'(<UnitType InternalName="{re.escape(base_name)}">[\s\S]*?</UnitType>)',
                    text,
                )
                text = text[: m2.end()] + "\n\t" + fem + text[m2.end() :]
                print("added", female_name)

            if f'InternalName="{other_name}"' not in text:
                oth_cfg = dict(cfg)
                if cfg.get("other_medallion"):
                    oth_cfg["medallion"] = cfg["other_medallion"]
                oth = clone_sovereign(
                    updated,
                    other_name,
                    cfg["other_name"],
                    "Male",
                    cfg["other_model"],
                    cfg["other_skin"],
                    oth_cfg,
                )
                m3 = re.search(
                    rf'(<UnitType InternalName="{re.escape(female_name)}">[\s\S]*?</UnitType>)',
                    text,
                )
                if not m3:
                    m3 = re.search(
                        rf'(<UnitType InternalName="{re.escape(base_name)}">[\s\S]*?</UnitType>)',
                        text,
                    )
                text = text[: m3.end()] + "\n\t" + oth + text[m3.end() :]
                print("added", other_name)

        path.write_text(text, encoding="utf-8")
        print("wrote", fname)

    # Patch race types: MaleUnitType + FemaleUnitType only.
    # Wire GenericUnitType_Other to Generic_Sovereign_*_Other (Ironeer Other-body pattern).
    for key, cfg in FORMS.items():
        rfile = GC / RACE_TYPE_FILES[key]
        rt = rfile.read_text(encoding="utf-8")
        race = cfg["race"]
        block_m = re.search(
            rf'(<RaceType InternalName="{re.escape(race)}">[\s\S]*?</RaceType>)',
            rt,
        )
        if not block_m:
            print("missing race", race)
            continue
        block = block_m.group(1)
        block = re.sub(
            r"<FemaleUnitType>[^<]*</FemaleUnitType>",
            f"<FemaleUnitType>Generic_Sovereign_{key}_Female</FemaleUnitType>",
            block,
            count=1,
        )
        # Ensure GenericUnitType_Other stays a peasant (restore if previously miswired)
        block = re.sub(
            r"<GenericUnitType_Other>[^<]*</GenericUnitType_Other>",
            f"<GenericUnitType_Other>Generic_Sovereign_{key}_Other</GenericUnitType_Other>",
            block,
            count=1,
        )
        block = re.sub(
            r"<MaleUnitType>[^<]*</MaleUnitType>",
            f"<MaleUnitType>Generic_Sovereign_{key}</MaleUnitType>",
            block,
            count=1,
        )
        rt = rt[: block_m.start()] + block + rt[block_m.end() :]
        rfile.write_text(rt, encoding="utf-8")
        print("race patched", race)

    write_archetypes()
    print("wrote LHL_LeaderOptions.xml")
    rewrite_elemd([r"Data\GameCore\LHL_LeaderOptions.xml"])
    print("done")


if __name__ == "__main__":
    main()
