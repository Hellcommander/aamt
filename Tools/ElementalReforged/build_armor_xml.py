#!/usr/bin/env python3
"""Build Elemental Reforged GameItemType XML for monster race clothes, armor, and weapons.

Clothes/armor: race-specific HKB meshes + textures (Juggernaut_Gear / Banshee_Shirt pattern).
Weapons: alternate oversized/monster ModelFile on hand attachment when needed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

KIND_META = {
    "clothes": {"tag": "Clothes", "slot_key": "Clothes", "slot_name": "Torso"},
    "armor": {"tag": "Armor", "slot_key": "Armor", "slot_name": "Torso"},
    "weapon": {"tag": "Weapon", "slot_key": "Weapon", "slot_name": "Main"},
}


def _texture_line(pack: dict) -> str:
    tex = pack.get("texture")
    if not tex:
        return ""
    channel = pack.get("textureChannel") or "Texture_All"
    return f"          <{channel}>{tex}</{channel}>\n"


_STAT_PROVIDES = {
    "UnitStat_ResistFire": "+{v} Fire Resist",
    "UnitStat_ResistCold": "+{v} Cold Resist",
    "UnitStat_ResistLightning": "+{v} Lightning Resist",
    "UnitStat_ResistPoison": "+{v} Poison Resist",
    "UnitStat_Defense_Pierce": "+{v} Pierce Defense",
    "UnitStat_Defense_Blunt": "+{v} Blunt Defense",
    "UnitStat_Dodge": "+{v} Dodge",
    "UnitStat_CombatSpeed": "+{v} Initiative",
    "UnitStat_HitPoints": "+{v} Hit Points",
    "UnitStat_Attack_Fire": "+{v} Fire Attack",
    "UnitStat_Attack_Cold": "+{v} Cold Attack",
    "UnitStat_Attack_Lightning": "+{v} Lightning Attack",
    "UnitStat_Attack_Poison": "+{v} Poison Attack",
    "UnitStat_Attack_Pierce": "+{v} Pierce Attack",
    "UnitStat_Accuracy": "+{v} Accuracy",
}


def _provides_for(stat: str, val) -> str:
    tmpl = _STAT_PROVIDES.get(stat)
    if tmpl:
        return tmpl.format(v=val)
    nice = stat.replace("UnitStat_", "").replace("_", " ")
    return f"+{val} {nice}"


def _resist_xml(resist: dict | None) -> str:
    if not resist:
        return ""
    out = ""
    for stat, val in resist.items():
        out += f"""
    <GameModifier>
      <ModType>Unit</ModType>
      <Attribute>AdjustUnitStat</Attribute>
      <StrVal>{stat}</StrVal>
      <Value>{val}</Value>
      <Provides>{_provides_for(stat, val)}</Provides>
    </GameModifier>"""
    return out


def internal_name(cfg: dict, race_key: str, kind: str, *, alt: bool = False) -> str:
    meta = KIND_META[kind]
    prefix = cfg.get("prefix", "LHL_")
    suffix = "_Alt" if alt else ""
    return f"{prefix}{meta['tag']}_{race_key}_{meta['slot_name']}{suffix}"


def build_item(
    cfg: dict,
    race_key: str,
    kind: str,
    icon_file: str,
    *,
    pack: dict | None = None,
    alt: bool = False,
) -> str:
    race = cfg["races"][race_key]
    pack = pack if pack is not None else race[kind]
    meta = KIND_META[kind]
    slot_cfg = cfg["slots"][meta["slot_key"]]
    internal = internal_name(cfg, race_key, kind, alt=alt)
    art = f"{internal}_ArtDef"
    pack_name = f"{internal}_Default"
    models = race.get("unitModelTypes") or ["WraithMale"]
    model_lines = "\n".join(
        f"        <SupportedUnitModelType>{m}</SupportedUnitModelType>" for m in models
    )
    type_lines = "\n".join(f"    <Type>{t}</Type>" for t in slot_cfg["types"])
    item_name = pack.get("itemName") or f"{race['display']} {meta['tag']}"
    if alt and "(Alt)" not in item_name:
        item_name = f"{item_name} (Alt)"

    if kind == "weapon":
        return _build_weapon(
            race=race,
            pack=pack,
            slot_cfg=slot_cfg,
            internal=internal,
            art=art,
            pack_name=pack_name,
            model_lines=model_lines,
            type_lines=type_lines,
            item_name=item_name,
            icon_file=icon_file,
        )

    defense = int(pack.get("defense") or slot_cfg["defense"])
    subtype = slot_cfg.get("subtype") or "Clothes"
    resist = pack.get("resist") or race.get("resist")
    rarity = "Common" if kind == "clothes" else "Uncommon"
    if alt:
        rarity = "Uncommon" if kind == "clothes" else "Rare"
    likelihood = "55" if kind == "clothes" else "40"
    if alt:
        likelihood = "35" if kind == "clothes" else "25"
    theme = (race.get("theme") or "").strip().rstrip(".")
    if kind == "clothes":
        desc = f"{item_name} - light garb of the {race['display']}. {theme}."
    else:
        desc = f"{item_name} - battle plate of the {race['display']}. {theme}."

    return f"""  <GameItemType InternalName="{internal}">
    <DisplayName>{item_name}</DisplayName>
    <Description>{desc}</Description>
{type_lines}
    <Subtype>{subtype}</Subtype>
    <CanBeEquipped>1</CanBeEquipped>
    <IsAvailableForSovereignCustomization>1</IsAvailableForSovereignCustomization>
    <IsAvailableForUnitDesign>1</IsAvailableForUnitDesign>
    <CustomizationPointCost>{slot_cfg['cost']}</CustomizationPointCost>
    <ShopValue>{int(slot_cfg['shopValue']) + (20 if alt else 0)}</ShopValue>
    <RarityDisplay>{rarity}</RarityDisplay>
    <Likelihood>{likelihood}</Likelihood>
    <GameModifier>
      <ModType>Unit</ModType>
      <Attribute>AdjustUnitStat</Attribute>
      <StrVal>UnitStat_Defense_Pierce</StrVal>
      <Value>{defense}</Value>
      <Provides>+{defense} Pierce Defense</Provides>
    </GameModifier>{_resist_xml(resist)}
    <ArtDef>{art}</ArtDef>
    <GameItemTypeArtDef InternalName="{art}">
      <GameItemTypeModelPack InternalName="{pack_name}">
        <IconFile>{icon_file}</IconFile>
{model_lines}
        <GameItemTypeModel>
          <ModelFile>{pack['model']}</ModelFile>
{_texture_line(pack)}          <AttachmentType>Skinned</AttachmentType>
        </GameItemTypeModel>
      </GameItemTypeModelPack>
    </GameItemTypeArtDef>
  </GameItemType>
"""


def _build_weapon(
    *,
    race: dict,
    pack: dict,
    slot_cfg: dict,
    internal: str,
    art: str,
    pack_name: str,
    model_lines: str,
    type_lines: str,
    item_name: str,
    icon_file: str,
) -> str:
    attack = int(pack.get("attack") or 8)
    accuracy = int(pack.get("accuracy") or 0)
    weapon_type = pack.get("weaponType") or "OneHanded"
    upgrade = pack.get("weaponUpgradeType") or "Blade"
    attachment = pack.get("attachment") or "hand_right_Lcf"
    theme = (race.get("theme") or "").strip().rstrip(".")
    custom_desc = (pack.get("description") or "").strip()
    wdesc = custom_desc or f"{item_name} - signature armament of the {race['display']}. {theme}."
    accuracy_mod = ""
    if accuracy:
        accuracy_mod = f"""
    <GameModifier>
      <ModType>Unit</ModType>
      <Attribute>AdjustUnitStat</Attribute>
      <StrVal>UnitStat_Accuracy</StrVal>
      <Value>{accuracy}</Value>
      <Provides>+{accuracy} Accuracy</Provides>
    </GameModifier>"""
    return f"""  <GameItemType InternalName="{internal}">
    <DisplayName>{item_name}</DisplayName>
    <Description>{wdesc}</Description>
{type_lines}
    <WeaponType>{weapon_type}</WeaponType>
    <WeaponUpgradeType>{upgrade}</WeaponUpgradeType>
    <CanBeEquipped>1</CanBeEquipped>
    <IsAvailableForSovereignCustomization>1</IsAvailableForSovereignCustomization>
    <IsAvailableForUnitDesign>1</IsAvailableForUnitDesign>
    <CustomizationPointCost>{slot_cfg['cost']}</CustomizationPointCost>
    <ShopValue>{slot_cfg['shopValue']}</ShopValue>
    <RarityDisplay>Uncommon</RarityDisplay>
    <Likelihood>35</Likelihood>
    <GameModifier>
      <ModType>Unit</ModType>
      <Attribute>AdjustUnitStat</Attribute>
      <StrVal>UnitStat_Attack_Pierce</StrVal>
      <Value>{attack}</Value>
      <Provides>+{attack} Pierce Attack</Provides>
    </GameModifier>{accuracy_mod}
    <ArtDef>{art}</ArtDef>
    <GameItemTypeArtDef InternalName="{art}">
      <GameItemTypeModelPack InternalName="{pack_name}">
        <IconFile>{icon_file}</IconFile>
        <AttackSFX>Hit_Sword_01</AttackSFX>
        <AttackSFX>Hit_Sword_02</AttackSFX>
        <EquipSFX>Equip_Sword_01</EquipSFX>
{model_lines}
        <GameItemTypeModel>
          <ModelFile>{pack['model']}</ModelFile>
{_texture_line(pack)}          <Attachment>{attachment}</Attachment>
        </GameItemTypeModel>
      </GameItemTypeModelPack>
    </GameItemTypeArtDef>
  </GameItemType>
"""


def wrap(items: list[str]) -> str:
    body = "\n".join(items)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!-- Generated by ElementalReforged MonsterRaceAssetGenerator (AAMT) -->
<!-- Clothes/armor: race alternate mesh+texture (Skinned). Weapons: alt ModelFile when needed. -->
<GameItemTypes>
  <DataChecksum NoParse="1">
    <Ignore>DispName</Ignore>
    <Translate>DisplayName,Description</Translate>
  </DataChecksum>
{body}
</GameItemTypes>
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--race", action="append", dest="races")
    ap.add_argument("--all-races", action="store_true")
    ap.add_argument("--kinds", default="clothes,armor,weapon")
    ap.add_argument("--icon-pattern", default="{internal}_Icon.png")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fragment-dir")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    keys = list(cfg["races"]) if args.all_races else (args.races or [])
    kinds = [k.strip().lower() for k in args.kinds.split(",") if k.strip()]
    want_alts = bool(cfg.get("altItems", True))
    chunks: list[str] = []
    for key in keys:
        for kind in kinds:
            if kind not in KIND_META or kind not in cfg["races"][key]:
                continue
            for alt in ((False, True) if want_alts else (False,)):
                internal = internal_name(cfg, key, kind, alt=alt)
                icon = args.icon_pattern.format(internal=internal, race=key, kind=kind)
                chunk = build_item(cfg, key, kind, icon, alt=alt)
                chunks.append(chunk)
                if args.fragment_dir:
                    frag = Path(args.fragment_dir) / key
                    frag.mkdir(parents=True, exist_ok=True)
                    (frag / f"{internal}.xml").write_text(chunk, encoding="utf-8")

    Path(args.out).write_text(wrap(chunks), encoding="utf-8")
    print(json.dumps({"races": keys, "kinds": kinds, "out": args.out, "count": len(chunks), "altItems": want_alts}))


if __name__ == "__main__":
    main()
