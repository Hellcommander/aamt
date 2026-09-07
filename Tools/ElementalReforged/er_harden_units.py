#!/usr/bin/env python3
"""Harden LHL unit XML with presentation fields needed for Unit Design Create Unit."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


RACE_TYPE_TO_KEY = {
    "Race_Type_Demon": "Demon",
    "Race_Type_Darkling": "Darkling",
    "Race_Type_FireElemental": "FireElemental",
    "Race_Type_EarthElemental": "EarthElemental",
    "Race_Type_AirElemental": "AirElemental",
    "Race_Type_IceElemental": "IceElemental",
    "Race_Type_Ogre": "Ogre",
    "Race_Type_Troll": "Troll",
    "Race_Type_Golem": "Golem",
    "Race_Type_Drake": "Drake",
    "Race_Type_Brood": "Brood",
    "Race_Type_Dragon": "Dragon",
    "Race_Type_Skath": "Skath",
    "Race_Type_Warg": "Warg",
    "Race_Type_Shrill": "Shrill",
}

# Bare or wrong-folder skeleton filenames -> canonical Monsters path
SKELETON_FIXES = {
    r"Gfx\HKB\Units\M_SuperDemon_Skeleton_01.hkb": r"Gfx\HKB\Monsters\M_SuperDemon_Skeleton_01.hkb",
    r"Gfx/HKB/Units/M_SuperDemon_Skeleton_01.hkb": r"Gfx\HKB\Monsters\M_SuperDemon_Skeleton_01.hkb",
    "M_SuperDemon_Skeleton_01.hkb": r"Gfx\HKB\Monsters\M_SuperDemon_Skeleton_01.hkb",
    "M_EarthElemental_Skeleton_01.hkb": r"Gfx\HKB\Monsters\M_EarthElemental_Skeleton_01.hkb",
}

# Mesh filename (lower) -> leader-safe presentation from vanilla refs.
# pose=True keeps UnitModelType + ClothPoseIndex for Appearance poses/gear.
# pose=False: match skel/anim for idle; clear UnitModelType so Create Sovereign
# does not hang humanoid clothes/poses on a monster morph.
MESH_LEADER_PRESENTATION: dict[str, dict[str, Any]] = {
    "m_superdemon_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_SuperDemon_Skeleton_01.hkb",
        "animationPack": "SuperDemonAnimationPack",
        "cutSceneDataPack": "DeathDemonUnitCutscenePack",
        "pose": False,
    },
    "m_fire_demon_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_SuperDemon_Skeleton_01.hkb",
        "animationPack": "DelinAnimationPack",
        "cutSceneDataPack": "DelinUnitCutscenePack",
        "pose": False,
    },
    "m_demon_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Units\K_Male_Skeleton_01.hkb",
        "animationPack": "DemonAnimationPack",
        # LHL pack uses AssassinDemon cameras for Create Sovereign (not DeathDemon crotch cam)
        "cutSceneDataPack": "LHL_DemonUnitCutscenePack",
        "unitModelType": "WraithMale",
        "clothPoseIndex": 0,
        "pose": True,
    },
    "m_fire_elemental_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_SuperDemon_Skeleton_01.hkb",
        # Must use FireEle idle — WraithAnimationPack starts with M_Wraith_Idle (broken feet).
        "animationPack": "FireEleAnimationPack",
        "cutSceneDataPack": "LHL_FireElementalUnitCutscenePack",
        "pose": False,
    },
    "m_earthelemental_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_EarthElemental_Skeleton_01.hkb",
        "animationPack": "EarthElementalAnimationPack",
        "cutSceneDataPack": "EarthElementalUnitCutscenePack",
        "pose": False,
    },
    "m_airelemental_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_SuperDemon_Skeleton_01.hkb",
        "animationPack": "AirElementalAnimationPack",
        "cutSceneDataPack": "AirElementalUnitCutscenePack",
        "pose": False,
    },
    "m_demon_elemental_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Units\K_Male_Skeleton_01.hkb",
        "animationPack": "CragspawnAnimationPack",
        "cutSceneDataPack": "MinorElementalUnitCutscenePack",
        "pose": False,
    },
    "m_golem_mesh_02.hkb": {
        "skeletonPath": r"Gfx\HKB\Units\K_Male_Skeleton_01.hkb",
        "animationPack": "GolemAnimationPack",
        "cutSceneDataPack": "GolemUnitCutscenePack",
        "unitModelType": "WraithMale",
        "clothPoseIndex": 0,
        "pose": True,
    },
    "k_irongolem_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Units\K_IronGolem_Skeleton_01.hkb",
        "animationPack": "IronGolemAnimationPack",
        "cutSceneDataPack": "IronGolemUnitCutscenePack",
        "unitModelType": "IronGolem",
        "clothPoseIndex": 1,
        "pose": True,
    },
    "m_drake_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_Drake_Skeleton_01.hkb",
        "animationPack": "GiantBeastAnimationPack",
        "cutSceneDataPack": "BigDrakeUnitCutscenePack",
        "pose": False,
    },
    "m_drake_slag_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_Drake_Skeleton_01.hkb",
        "animationPack": "GiantBeastAnimationPack",
        "cutSceneDataPack": "RiverSlagUnitScenePack",
        "pose": False,
    },
    "d_dragon_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Dragons\D_Dragon_Skeleton_01.hkb",
        "animationPack": "DragonAnimationPack",
        "cutSceneDataPack": "DragonUnitCutscenePack",
        "pose": False,
    },
    "m_spider_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_Spider_Skeleton_01.hkb",
        "animationPack": "SpiderAnimationPack",
        "cutSceneDataPack": "LargeSpiderUnitCutscenePack",
        "pose": False,
    },
    "m_spider_rock_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_Spider_Skeleton_01.hkb",
        "animationPack": "SpiderAnimationPack",
        "cutSceneDataPack": "LargeSpiderUnitCutscenePack",
        "pose": False,
    },
    "m_spider_poison_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_Spider_Skeleton_01.hkb",
        "animationPack": "SpiderAnimationPack",
        "cutSceneDataPack": "LargeSpiderUnitCutscenePack",
        "pose": False,
    },
    "m_spider_demon_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_Spider_Skeleton_01.hkb",
        "animationPack": "SpiderAnimationPack",
        "cutSceneDataPack": "LargeSpiderUnitCutscenePack",
        "pose": False,
    },
    "k_spiderman_mesh.hkb": {
        "skeletonPath": r"Gfx\HKB\Units\K_Male_Skeleton_01.hkb",
        "animationPack": "DarklingAnimationPack",
        "cutSceneDataPack": "BroodUnitCutscenePack",
        "unitModelType": "DarklingMale",
        "clothPoseIndex": 0,
        "pose": True,
    },
    "m_darkling_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Units\K_Male_Skeleton_01.hkb",
        "animationPack": "DarklingAnimationPack",
        "cutSceneDataPack": "LurkUnitCutscenePack",
        "unitModelType": "DarklingMale",
        "clothPoseIndex": 0,
        "pose": True,
    },
    "m_darkling_armored_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Units\K_Male_Skeleton_01.hkb",
        "animationPack": "DarklingSpearAnimationPack",
        "cutSceneDataPack": "DarklingWarriorUnitCutscenePack",
        "unitModelType": "DarklingMale",
        "clothPoseIndex": 0,
        "pose": True,
    },
    "m_warg_skath_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_Warg_Skeleton_01.hkb",
        "animationPack": "SkathAnimationPack",
        "cutSceneDataPack": "UmberdrothUnitCutscenePack",
        "pose": False,
    },
    "m_warg_rock_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_Warg_Skeleton_01.hkb",
        "animationPack": "WargAnimationPack",
        "cutSceneDataPack": "UmberdrothUnitCutscenePack",
        "pose": False,
    },
    "m_warg_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_Warg_Skeleton_01.hkb",
        "animationPack": "WargAnimationPack",
        "cutSceneDataPack": "WargUnitCutscenePack",
        "pose": False,
    },
    "m_wolf_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_Warg_Skeleton_01.hkb",
        "animationPack": "WargAnimationPack",
        "cutSceneDataPack": "WargUnitCutscenePack",
        "pose": False,
    },
    "m_warg_sandbrute_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_Warg_Skeleton_01.hkb",
        "animationPack": "WargAnimationPack",
        "cutSceneDataPack": "UmberdrothUnitCutscenePack",
        "pose": False,
    },
    "m_giant_ogre_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_Giant_Skeleton_01.hkb",
        "animationPack": "OgreAnimationPack",
        "cutSceneDataPack": "BoneOgreUnitCutscenePack",
        "unitModelType": "JuggernautMale",
        "clothPoseIndex": 1,
        "pose": True,
    },
    "m_giant_warrior_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_Giant_Skeleton_01.hkb",
        "animationPack": "TrollWarriorAnimationPack",
        "cutSceneDataPack": "TrollWarriorUnitCutscenePack",
        "unitModelType": "JuggernautMale",
        "clothPoseIndex": 1,
        "pose": True,
    },
    # Elite troop meshes (LHL_EliteUnits.xml) — keep distinct skel/anim/cutscene on harden.
    "m_superdemon_rock_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_SuperDemon_Rock_Skeleton_01.hkb",
        "animationPack": "RockGolemAnimationPack",
        "cutSceneDataPack": "EarthElementalUnitCutscenePack",
        "pose": False,
    },
    "m_abeix_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Units\M_Ignys_Skeleton_01.hkb",
        "animationPack": "AbeixAnimationPack",
        "cutSceneDataPack": "AbeixUnitCutscenePack",
        "pose": False,
    },
    "m_fallen_guardian_ward_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Units\K_Male_Skeleton_01.hkb",
        "animationPack": "ScrapGolemAnimationPack",
        "cutSceneDataPack": "GolemUnitCutscenePack",
        "pose": False,
    },
    "m_giant_shaman_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_Giant_Skeleton_01.hkb",
        "animationPack": "GiantAnimationPack",
        "cutSceneDataPack": "TrollShamanUnitCutscenePack",
        "pose": False,
    },
    "k_juggernaut_mesh_01.hkb": {
        "skeletonPath": "K_Juggernaut_Skeleton_01.hkb",
        "animationPack": "JuggernautAnimationPack",
        "cutSceneDataPack": "JuggernautUnitCutscenePack",
        "pose": False,
    },
    "m_ignys_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_Ignys_Skeleton_01.hkb",
        "animationPack": "SandSerpantAnimationPack",
        "cutSceneDataPack": "IgnysUnitCutscenePack",
        "pose": False,
    },
    "m_torax_mesh_01.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_Torax_Skeleton_01.hkb",
        "animationPack": "ToraxAnimationPack",
        "cutSceneDataPack": "ToraxUnitCutScenePack",
        "pose": False,
    },
    "m_squamatego_male_mesh.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_Warg_Skeleton_01.hkb",
        "animationPack": "GaragoxAnimationPack",
        "cutSceneDataPack": "WargUnitCutscenePack",
        "pose": False,
    },
    "m_squamatego_female_mesh.hkb": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_Warg_Skeleton_01.hkb",
        "animationPack": "GaragoxAnimationPack",
        "cutSceneDataPack": "WargUnitCutscenePack",
        "pose": False,
    },
}

# Per-unit overrides when a mesh is shared with basic troops (different anim/cutscene).
ELITE_UNIT_PRESENTATION: dict[str, dict[str, Any]] = {
    "LHL_Unit_FireDemon": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_SuperDemon_Skeleton_01.hkb",
        "animationPack": "DelinAnimationPack",
        "cutSceneDataPack": "DelinUnitCutscenePack",
        "pose": False,
    },
    "LHL_Unit_ShrillLord": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_Spider_Skeleton_01.hkb",
        "animationPack": "ShrillLordAnimationPack",
        "cutSceneDataPack": "ShrillLordUnitCutscenePack",
        "pose": False,
    },
    "LHL_Unit_BoneOgreElder": {
        "skeletonPath": r"Gfx\HKB\Monsters\M_Giant_Skeleton_01.hkb",
        "animationPack": "OgreAnimationPack",
        "cutSceneDataPack": "BoneOgreUnitCutscenePack",
        "pose": False,
    },
}

# Demon leaders must never stay on SuperDemon/DeathDemon — that camera + no UMT = naked crotch shot.
LEADER_FORCE_POSE: dict[str, dict[str, Any]] = {
    "Demon": {
        "modelPath": "gfx/hkb/Monsters/M_Demon_Mesh_01.hkb",
        # Hero-quality skin from vanilla AssassinDemon_Hero (CoreMonsters.xml)
        "textureSkin": "DLC02_AssassinDemon_Texture_01.png",
        "clothMapScale": "1.5",
        "skeletonPath": r"Gfx\HKB\Units\K_Male_Skeleton_01.hkb",
        "animationPack": "DemonAnimationPack",
        "cutSceneDataPack": "LHL_DemonUnitCutscenePack",
        "unitModelType": "WraithMale",
        "clothPoseIndex": 0,
        "pose": True,
        "equipment": ["LHL_Armor_Demon_Torso", "LHL_Weapon_Demon_Main"],
        "medallion": "M_AssassinDemon_01_Card.png",
    },
}


def _set_or_insert_tag(block: str, tag: str, value: str, after_tags: list[str]) -> str:
    """Replace existing tag or insert after the first matching after_tag."""
    pat = re.compile(rf"<{tag}>[^<]*</{tag}>")
    repl = f"<{tag}>{value}</{tag}>"
    if pat.search(block):
        # Lambda avoids re.sub treating backslashes in Windows paths as escapes
        return pat.sub(lambda _m: repl, block, count=1)
    insert = f"\t\t{repl}\n"
    for after in after_tags:
        m = re.search(rf"(</{after}>\s*\n)", block)
        if m:
            return block[: m.end()] + insert + block[m.end() :]
    m = re.search(r"(</ModelPath>\s*\n)", block)
    if m:
        return block[: m.end()] + insert + block[m.end() :]
    return block + insert


def _remove_tag(block: str, tag: str) -> str:
    return re.sub(rf"[ \t]*<{tag}>[^<]*</{tag}>\r?\n", "", block)


def presentation_for_race(race: dict[str, Any]) -> dict[str, Any]:
    pres = dict(race.get("presentation") or {})
    primary = race.get("unitModelTypePrimary") or (race.get("unitModelTypes") or [None])[0]
    if primary:
        pres.setdefault("unitModelType", primary)
    if race.get("baseSkeletonPath") and "skeletonPath" not in pres:
        pres["skeletonPath"] = race["baseSkeletonPath"]
    return pres


def is_leader_unit(name: str) -> bool:
    return name.startswith("Generic_Sovereign_") or name.startswith("Sovereign_LHL_")


def mesh_key_from_body(body: str) -> str | None:
    m = re.search(r"<ModelPath>([^<]+)</ModelPath>", body)
    if not m:
        return None
    return Path(m.group(1).replace("\\", "/")).name.lower()


def _ensure_autocreate_equipment(block: str, items: list[str]) -> str:
    """Add AutoCreateEquipment tags if missing (armor/weapons for leaders)."""
    for item in items:
        tag = f"<AutoCreateEquipment>{item}</AutoCreateEquipment>"
        if tag in block:
            continue
        insert = f"\t\t{tag}\n"
        m = re.search(r"(</ClothPoseIndex>\s*\n)", block)
        if not m:
            m = re.search(r"(</CutSceneDataPack>\s*\n)", block)
        if not m:
            m = re.search(r"(</UnitModelType>\s*\n)", block)
        if m:
            block = block[: m.end()] + insert + block[m.end() :]
        else:
            block = block + insert
    return block


def harden_leader_block(block: str, race_key: str | None = None) -> str:
    """Mesh-matched skeleton/anim/cutscene; pose UMT only when the morph supports it."""
    force = LEADER_FORCE_POSE.get(race_key or "")
    if force:
        block = _set_or_insert_tag(block, "ModelPath", str(force["modelPath"]), ["SelectedAbilityBonusOption"])
        if force.get("textureSkin"):
            block = _set_or_insert_tag(
                block, "Texture_Skin", str(force["textureSkin"]), ["AnimationPack", "SkeletonPath", "ModelPath"]
            )
        if force.get("clothMapScale"):
            block = _set_or_insert_tag(
                block, "ClothMapScale", str(force["clothMapScale"]), ["ModelScale", "Texture_Skin"]
            )
        if force.get("medallion"):
            block = re.sub(
                r"(<Medallions>\s*<All>)[^<]*(</All>)",
                lambda m: f"{m.group(1)}{force['medallion']}{m.group(2)}",
                block,
                count=1,
            )
        # Apply forced presentation via mesh key after model rewrite
        key = Path(str(force["modelPath"]).replace("\\", "/")).name.lower()
        # Merge force fields over mesh map entry
        pres = dict(MESH_LEADER_PRESENTATION.get(key) or {})
        for k, v in force.items():
            if k in ("equipment", "medallion", "modelPath", "textureSkin"):
                continue
            pres[k] = v
    else:
        key = mesh_key_from_body(block)
        if not key:
            return block
        pres = MESH_LEADER_PRESENTATION.get(key)
        if not pres:
            return block

    for bad, good in SKELETON_FIXES.items():
        block = block.replace(f"<SkeletonPath>{bad}</SkeletonPath>", f"<SkeletonPath>{good}</SkeletonPath>")

    block = _set_or_insert_tag(block, "SkeletonPath", str(pres["skeletonPath"]), ["ModelPath"])
    block = _set_or_insert_tag(block, "AnimationPack", str(pres["animationPack"]), ["SkeletonPath", "ModelPath"])
    block = _set_or_insert_tag(
        block,
        "CutSceneDataPack",
        str(pres["cutSceneDataPack"]),
        ["SoundPack", "UnitModelType", "AnimationPack", "Texture_Skin"],
    )

    if pres.get("pose"):
        umt = str(pres.get("unitModelType") or "")
        if umt:
            block = _set_or_insert_tag(
                block,
                "UnitModelType",
                umt,
                ["Texture_Skin", "AnimationPack", "SkeletonPath", "ModelPath"],
            )
        pose_idx = int(pres.get("clothPoseIndex", 0))
        block = _set_or_insert_tag(
            block,
            "ClothPoseIndex",
            str(pose_idx),
            ["ClothMapScale", "ModelScale", "TacticalModelScale", "UnitModelType", "CutSceneDataPack"],
        )
    else:
        # Monster morph: idle via AnimationPack; no humanoid pose/clothes UMT.
        block = _remove_tag(block, "UnitModelType")
        block = _remove_tag(block, "ClothPoseIndex")

    # Pose morphs can visually wear skinned clothes/armor — attach race kits
    # (same items generate --install creates as LHL_Armor_<Race>_Torso / LHL_Weapon_*).
    if force and force.get("equipment"):
        block = _ensure_autocreate_equipment(block, list(force["equipment"]))
    elif pres.get("pose") and race_key:
        block = _ensure_autocreate_equipment(
            block,
            [f"LHL_Armor_{race_key}_Torso", f"LHL_Weapon_{race_key}_Main"],
        )

    return block


def harden_unit_block(block: str, race: dict[str, Any], unit_name: str | None = None) -> str:
    """Apply presentation fields to a single UnitType body."""
    pres = presentation_for_race(race)
    if not pres:
        return block

    # Always fix known bad skeleton paths first
    for bad, good in SKELETON_FIXES.items():
        block = block.replace(f"<SkeletonPath>{bad}</SkeletonPath>", f"<SkeletonPath>{good}</SkeletonPath>")

    # Never hang humanoid ClothPose / UMT on a monster-body mesh: the engine
    # then paints the mesh with the flat race UnitSkinColor instead of its real
    # texture (black warg leader / solid-red map units). Vanilla beasts have no
    # UnitModelType. Decide per-mesh when known, else per bodyTier.
    mesh = mesh_key_from_body(block)
    mesh_pres = MESH_LEADER_PRESENTATION.get(mesh) if mesh else None
    elite_pres = ELITE_UNIT_PRESENTATION.get(unit_name or "")
    if elite_pres is not None:
        supports_pose = bool(elite_pres.get("pose"))
        for k in ("skeletonPath", "animationPack", "cutSceneDataPack"):
            if elite_pres.get(k):
                pres[k] = elite_pres[k]
    elif mesh_pres is not None:
        supports_pose = bool(mesh_pres.get("pose"))
        # A known monster mesh needs its own skeleton/anim/cutscene, not the
        # race's humanoid defaults (e.g. Fire Demon troop rides the SuperDemon
        # skeleton + DelinAnimationPack, never K_Male + DemonAnimationPack).
        for k in ("skeletonPath", "animationPack", "cutSceneDataPack"):
            if mesh_pres.get(k):
                pres[k] = mesh_pres[k]
    else:
        supports_pose = str(race.get("bodyTier") or "") not in ("elemental", "beast")
    if not supports_pose:
        block = _remove_tag(block, "UnitModelType")
        block = _remove_tag(block, "ClothPoseIndex")
    else:
        umt = pres.get("unitModelType") or race.get("unitModelTypePrimary")
        if umt:
            block = _set_or_insert_tag(
                block,
                "UnitModelType",
                str(umt),
                ["Texture_Skin", "AnimationPack", "SkeletonPath", "ModelPath"],
            )

        if "clothPoseIndex" in pres:
            block = _set_or_insert_tag(
                block,
                "ClothPoseIndex",
                str(int(pres["clothPoseIndex"])),
                ["ClothMapScale", "ModelScale", "TacticalModelScale", "UnitModelType", "CutSceneDataPack"],
            )

    if pres.get("skeletonPath"):
        block = _set_or_insert_tag(
            block,
            "SkeletonPath",
            str(pres["skeletonPath"]),
            ["ModelPath"],
        )

    if pres.get("animationPack"):
        block = _set_or_insert_tag(
            block,
            "AnimationPack",
            str(pres["animationPack"]),
            ["SkeletonPath", "ModelPath"],
        )

    if pres.get("cutSceneDataPack"):
        block = _set_or_insert_tag(
            block,
            "CutSceneDataPack",
            str(pres["cutSceneDataPack"]),
            ["SoundPack", "UnitModelType", "AnimationPack", "Texture_Skin"],
        )

    if pres.get("soundPack"):
        block = _set_or_insert_tag(
            block,
            "SoundPack",
            str(pres["soundPack"]),
            ["Texture_Skin", "AnimationPack", "UnitModelType"],
        )

    if pres.get("eyeTexture"):
        block = _set_or_insert_tag(
            block,
            "EyeTexture",
            str(pres["eyeTexture"]),
            ["Medallions", "InfoCardBackground", "CutSceneDataPack"],
        )

    return block


def race_key_from_unit(name: str, body: str, cfg: dict[str, Any]) -> str | None:
    m = re.search(r"<RaceType>([^<]+)</RaceType>", body)
    if m:
        mapped = RACE_TYPE_TO_KEY.get(m.group(1).strip())
        if mapped and mapped in cfg.get("races", {}):
            return mapped
    # Fallback: InternalName suffix
    for key in cfg.get("races", {}):
        if name.endswith(f"_{key}") or name.endswith(f"Sovereign_{key}"):
            return key
    return None


def harden_units_file(path: Path, cfg: dict[str, Any]) -> dict[str, int]:
    text = path.read_text(encoding="utf-8")
    stats = {"patched": 0, "units": 0, "skipped": 0, "leaders": 0}

    def repl(m: re.Match[str]) -> str:
        name, body = m.group(1), m.group(2)
        stats["units"] += 1
        key = race_key_from_unit(name, body, cfg)
        if not key:
            stats["skipped"] += 1
            return m.group(0)
        new_body = harden_unit_block(body, cfg["races"][key], unit_name=name)
        if is_leader_unit(name):
            new_body = harden_leader_block(new_body, race_key=key)
            stats["leaders"] += 1
        if new_body != body:
            stats["patched"] += 1
        return f'<UnitType InternalName="{name}">{new_body}</UnitType>'

    new_text = re.sub(
        r'<UnitType InternalName="([^"]+)">(.*?)</UnitType>',
        repl,
        text,
        flags=re.S,
    )
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
    return stats


def harden_mod_units(mod: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    gc = mod / "Data" / "GameCore"
    report: dict[str, Any] = {
        "files": {},
        "totals": {"patched": 0, "units": 0, "skipped": 0, "leaders": 0},
    }
    for path in sorted(gc.glob("LHL_*Units.xml")):
        st = harden_units_file(path, cfg)
        report["files"][path.name] = st
        for k in ("patched", "units", "skipped", "leaders"):
            report["totals"][k] += st.get(k, 0)
    return report


def validate_designable_units(mod: Path) -> list[str]:
    """Return error strings for designable units missing required presentation."""
    errors: list[str] = []
    gc = mod / "Data" / "GameCore"
    for path in sorted(gc.glob("LHL_*Units.xml")):
        text = path.read_text(encoding="utf-8")
        for name, body in re.findall(
            r'<UnitType InternalName="([^"]+)">(.*?)</UnitType>', text, re.S
        ):
            designed = re.search(r"<CanBeDesigned>\s*1\s*</CanBeDesigned>", body)
            if not designed:
                continue
            mesh = mesh_key_from_body(body) or ""
            leader_pres = MESH_LEADER_PRESENTATION.get(mesh)
            elite_pres = ELITE_UNIT_PRESENTATION.get(name)
            race_m = re.search(r"<RaceType>([^<]+)</RaceType>", body)
            race_key = RACE_TYPE_TO_KEY.get(race_m.group(1).strip()) if race_m else None
            # Elemental morphs + non-pose leader morphs: no humanoid UMT/ClothPose.
            elemental_race = race_key in (
                "FireElemental",
                "EarthElemental",
                "AirElemental",
                "IceElemental",
            )
            # Mesh-aware, mirroring harden_unit_block: known monster meshes only
            # need UMT/ClothPose when they support humanoid poses; unknown
            # meshes are assumed humanoid unless the race is elemental.
            if elite_pres is not None:
                pose_ok = bool(elite_pres.get("pose"))
            elif leader_pres is not None:
                pose_ok = bool(leader_pres.get("pose"))
            elif elemental_race:
                pose_ok = False
            else:
                pose_ok = True
            required = ["SkeletonPath", "AnimationPack", "CutSceneDataPack"]
            if pose_ok:
                required = ["UnitModelType", "ClothPoseIndex", *required]
            for tag in required:
                if not re.search(rf"<{tag}>[^<]+</{tag}>", body):
                    errors.append(f"{path.name}:{name}: missing {tag}")
            sk = re.search(r"<SkeletonPath>([^<]+)</SkeletonPath>", body)
            if sk:
                s = sk.group(1).strip()
                bare_ok = s.lower() in {"k_juggernaut_skeleton_01.hkb"}
                if s in SKELETON_FIXES or (
                    not bare_ok
                    and not s.lower().startswith("gfx")
                    and "\\" not in s
                    and "/" not in s
                ):
                    errors.append(f"{path.name}:{name}: bad SkeletonPath {s}")
                if r"Units\M_SuperDemon" in s or "Units/M_SuperDemon" in s:
                    errors.append(f"{path.name}:{name}: SuperDemon skeleton in Units folder")
            if is_leader_unit(name) and leader_pres and sk:
                want = Path(str(leader_pres["skeletonPath"]).replace("\\", "/")).name.lower()
                have = Path(sk.group(1).replace("\\", "/")).name.lower()
                if have != want:
                    errors.append(f"{path.name}:{name}: leader skeleton {have} != {want}")
                anim = re.search(r"<AnimationPack>([^<]+)</AnimationPack>", body)
                if anim and anim.group(1) != leader_pres["animationPack"]:
                    errors.append(
                        f"{path.name}:{name}: leader anim {anim.group(1)} != {leader_pres['animationPack']}"
                    )
    return errors


def validate_leader_units(mod: Path) -> list[str]:
    """All Generic_Sovereign_* / Sovereign_LHL_* must match mesh presentation map."""
    errors: list[str] = []
    gc = mod / "Data" / "GameCore"
    for path in sorted(gc.glob("LHL_*Units.xml")):
        text = path.read_text(encoding="utf-8")
        for name, body in re.findall(
            r'<UnitType InternalName="([^"]+)">(.*?)</UnitType>', text, re.S
        ):
            if not is_leader_unit(name):
                continue
            race_m = re.search(r"<RaceType>([^<]+)</RaceType>", body)
            race_type = race_m.group(1).strip() if race_m else ""
            race_key = RACE_TYPE_TO_KEY.get(race_type)
            mesh = mesh_key_from_body(body)
            if race_key in LEADER_FORCE_POSE:
                force = LEADER_FORCE_POSE[race_key]
                want_mesh = Path(str(force["modelPath"]).replace("\\", "/")).name.lower()
                if mesh != want_mesh:
                    errors.append(f"{path.name}:{name}: demon leader mesh {mesh} != {want_mesh}")
                if not re.search(r"<UnitModelType>WraithMale</UnitModelType>", body):
                    errors.append(f"{path.name}:{name}: forced pose leader missing WraithMale")
                if "DeathDemonUnitCutscenePack" in body or "DelinUnitCutscenePack" in body:
                    errors.append(f"{path.name}:{name}: wrong cutscene (Death/Delin) for armored demon")
                for item in force.get("equipment") or []:
                    if f"<AutoCreateEquipment>{item}</AutoCreateEquipment>" not in body:
                        errors.append(f"{path.name}:{name}: missing AutoCreateEquipment {item}")
                continue
            if not mesh:
                errors.append(f"{path.name}:{name}: missing ModelPath")
                continue
            if mesh not in MESH_LEADER_PRESENTATION:
                errors.append(f"{path.name}:{name}: unmapped leader mesh {mesh}")
                continue
            pres = MESH_LEADER_PRESENTATION[mesh]
            sk = re.search(r"<SkeletonPath>([^<]+)</SkeletonPath>", body)
            anim = re.search(r"<AnimationPack>([^<]+)</AnimationPack>", body)
            umt = re.search(r"<UnitModelType>([^<]+)</UnitModelType>", body)
            want_sk = Path(str(pres["skeletonPath"]).replace("\\", "/")).name.lower()
            have_sk = Path(sk.group(1).replace("\\", "/")).name.lower() if sk else ""
            if have_sk != want_sk:
                errors.append(f"{path.name}:{name}: skel {have_sk} != {want_sk}")
            if not anim or anim.group(1) != pres["animationPack"]:
                errors.append(f"{path.name}:{name}: anim mismatch")
            if pres.get("pose"):
                if not umt:
                    errors.append(f"{path.name}:{name}: pose morph missing UnitModelType")
            elif umt:
                errors.append(f"{path.name}:{name}: monster morph still has UnitModelType {umt.group(1)}")
    return errors
