"""Enable third leader form via Other gender (Ironeer GenericUnitType_Other pattern)."""
from __future__ import annotations

import re
from pathlib import Path

MOD = Path(r"D:\User_Directories\Documents\My Games\ElementalReforged\Mods\LH_Legacy_Expansion")
GC = MOD / "Data" / "GameCore"
TOOLS = Path(r"D:\games\Steam\steamapps\common\Transcendence\Tools\ElementalReforged")

RACES = {
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


def wire_other_forms() -> None:
    for key, fname in RACES.items():
        path = GC / fname
        text = path.read_text(encoding="utf-8")
        race = f"Race_Type_{key}"
        m = re.search(rf'(<RaceType InternalName="{re.escape(race)}">[\s\S]*?</RaceType>)', text)
        if not m:
            print("missing", race)
            continue
        block = m.group(1)
        target = f"Generic_Sovereign_{key}_Other"
        block2 = re.sub(
            r"<GenericUnitType_Other>[^<]*</GenericUnitType_Other>",
            f"<GenericUnitType_Other>{target}</GenericUnitType_Other>",
            block,
            count=1,
        )
        if block2 == block:
            print("no Other tag?", race)
            continue
        text = text[: m.start()] + block2 + text[m.end() :]
        path.write_text(text, encoding="utf-8")
        print("Other ->", target)


def enable_design_on_other_sovereigns() -> None:
    """Ironeer Iron Golem is CanBeDesigned=1; make third forms usable the same way."""
    for fname in ("LHL_ExoticUnits.xml", "LHL_MoreExoticUnits.xml", "LHL_Wave2Units.xml"):
        path = GC / fname
        text = path.read_text(encoding="utf-8")
        count = 0

        def fix(m: re.Match[str]) -> str:
            nonlocal count
            body = m.group(0)
            body2 = re.sub(
                r"<CanBeDesigned>0</CanBeDesigned>",
                "<CanBeDesigned>1</CanBeDesigned>",
                body,
            )
            # Keep Gender Other
            body2 = re.sub(r"<Gender>[^<]+</Gender>", "<Gender>Other</Gender>", body2, count=1)
            if body2 != body:
                count += 1
            return body2

        new = re.sub(
            r'<UnitType InternalName="Generic_Sovereign_[^"]+_Other">[\s\S]*?</UnitType>',
            fix,
            text,
        )
        if new != text:
            path.write_text(new, encoding="utf-8")
        print(fname, "patched Other templates:", count)


def fix_fire_icons() -> None:
    for fname in ("LHL_ExpandedTraits.xml", "LHL_UnitDesignTraits.xml"):
        path = GC / fname
        text = path.read_text(encoding="utf-8")
        n = text.count("Ability_Fire_Icon.dds")
        if n:
            path.write_text(
                text.replace("Ability_Fire_Icon.dds", "Ability_FireBreath_Icon.dds"),
                encoding="utf-8",
            )
        print(fname, "fire icons fixed:", n)


def update_leader_options_comment() -> None:
    path = GC / "LHL_LeaderOptions.xml"
    text = path.read_text(encoding="utf-8")
    old = (
        "<!-- Leader body: Create Sovereign Male/Female pick MaleUnitType / FemaleUnitType (distinct meshes).\n"
        "     These Player options (Warlord / Spellweaver / Skirmisher / Warden) set combat role.\n"
        "     Generic_Sovereign_*_Other unit defs exist as spare forms but are not wired to GenericUnitType_Other\n"
        "     (that slot must stay peasant so Unit Design Other gender works). -->"
    )
    new = (
        "<!-- Leader body: Create Sovereign Male / Female / Other pick distinct meshes\n"
        "     (MaleUnitType / FemaleUnitType / GenericUnitType_Other — Ironeer golem pattern).\n"
        "     These Player options (Warlord / Spellweaver / Skirmisher / Warden) set combat role. -->"
    )
    if old in text:
        path.write_text(text.replace(old, new), encoding="utf-8")
        print("updated LeaderOptions comment")
    else:
        print("LeaderOptions comment already different")


def update_add_leader_forms_script() -> None:
    path = TOOLS / "add_leader_forms.py"
    text = path.read_text(encoding="utf-8")
    # Prefer Other form wiring over peasant restore if present
    text2 = text.replace(
        "Do NOT overwrite GenericUnitType_Other (must remain peasant for Unit Design).",
        "Wire GenericUnitType_Other to Generic_Sovereign_*_Other (Ironeer Other-body pattern).",
    )
    text2 = text2.replace(
        f'<GenericUnitType_Other>Unit_Peasant_{{key}}</GenericUnitType_Other>',
        f'<GenericUnitType_Other>Generic_Sovereign_{{key}}_Other</GenericUnitType_Other>',
    )
    # The f-string in source is built with f"..." so look for that pattern
    text2 = text2.replace(
        'f"<GenericUnitType_Other>Unit_Peasant_{key}</GenericUnitType_Other>"',
        'f"<GenericUnitType_Other>Generic_Sovereign_{key}_Other</GenericUnitType_Other>"',
    )
    if text2 != text:
        path.write_text(text2, encoding="utf-8")
        print("updated add_leader_forms.py")
    else:
        print("add_leader_forms.py unchanged (patterns not found)")


def main() -> None:
    wire_other_forms()
    enable_design_on_other_sovereigns()
    fix_fire_icons()
    update_leader_options_comment()
    update_add_leader_forms_script()
    print("done")


if __name__ == "__main__":
    main()
