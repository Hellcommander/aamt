#!/usr/bin/env python3
"""Versioned creature.json schema, presets, load/save helpers."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from df_paths import templates_dir
from df_tissue import hematophyte_tissue_addons

SCHEMA_VERSION = 1

# Shared organ / sensory addons for vertebrate civs
_VERTEBRATE_ORGANS = [
    "2EYES",
    "2EARS",
    "NOSE",
    "2LUNGS",
    "HEART",
    "GUTS",
    "ORGANS",
    "THROAT",
    "NECK",
    "SPINE",
    "BRAIN",
    "SKULL",
    "MOUTH",
    "TONGUE",
    "FACIAL_FEATURES",
    "TEETH",
    "RIBCAGE",
]

BODY_PRESETS: Dict[str, Dict[str, Any]] = {
    "humanoid_civ": {
        "body_fragments": [
            "HUMANOID_NECK",
            "2EYES",
            "2EARS",
            "NOSE",
            "2LUNGS",
            "HEART",
            "GUTS",
            "ORGANS",
            "HUMANOID_JOINTS",
            "THROAT",
            "NECK",
            "SPINE",
            "BRAIN",
            "SKULL",
            "5FINGERS",
            "5TOES",
            "MOUTH",
            "TONGUE",
            "FACIAL_FEATURES",
            "TEETH",
            "RIBCAGE",
        ],
        "detail_plans": [
            "STANDARD_MATERIALS",
            "STANDARD_TISSUES",
            "VERTEBRATE_TISSUE_LAYERS:SKIN:FAT:MUSCLE:BONE:CARTILAGE",
            "HEAD_HAIR_TISSUE_LAYERS",
            "FACIAL_HAIR_TISSUES",
            "STANDARD_HEAD_POSITIONS",
            "HUMANOID_HEAD_POSITIONS",
            "HUMANOID_RIBCAGE_POSITIONS",
            "HUMANOID_RELSIZES",
        ],
        "graphics_profile": "humanoid",
        "intelligent": True,
        "equips": True,
        "can_open_doors": True,
        "site_controllable": True,
        "culture_preset": "dwarf_industry",
    },
    "winged_humanoid": {
        "body_fragments": [
            "HUMANOID_NECK",
            "2WINGS",
            "2EYES",
            "2EARS",
            "NOSE",
            "2LUNGS",
            "HEART",
            "GUTS",
            "ORGANS",
            "HUMANOID_JOINTS",
            "THROAT",
            "NECK",
            "SPINE",
            "BRAIN",
            "SKULL",
            "5FINGERS",
            "5TOES",
            "MOUTH",
            "TONGUE",
            "FACIAL_FEATURES",
            "TEETH",
            "RIBCAGE",
        ],
        "detail_plans": [
            "STANDARD_MATERIALS",
            "STANDARD_TISSUES",
            "VERTEBRATE_TISSUE_LAYERS:SKIN:FAT:MUSCLE:BONE:CARTILAGE",
            "STANDARD_HEAD_POSITIONS",
            "HUMANOID_HEAD_POSITIONS",
            "HUMANOID_RIBCAGE_POSITIONS",
            "HUMANOID_RELSIZES",
        ],
        "graphics_profile": "humanoid",
        "intelligent": True,
        "equips": True,
        "can_open_doors": True,
        "site_controllable": True,
        "culture_preset": "elf_nature",
    },
    "quadruped_grasp": {
        "body_fragments": [
            "QUADRUPED_NECK_FRONT_GRASP",
            "2EYES",
            "2EARS",
            "NOSE",
            "2LUNGS",
            "HEART",
            "GUTS",
            "ORGANS",
            "THROAT",
            "NECK",
            "SPINE",
            "BRAIN",
            "SKULL",
            "MOUTH",
            "TONGUE",
            "TEETH",
            "RIBCAGE",
            "TAIL",
        ],
        "detail_plans": [
            "STANDARD_MATERIALS",
            "STANDARD_TISSUES",
            "VERTEBRATE_TISSUE_LAYERS:SKIN:FAT:MUSCLE:BONE:CARTILAGE",
            "STANDARD_HEAD_POSITIONS",
        ],
        "graphics_profile": "simple",
        "intelligent": True,
        "equips": True,
        "can_open_doors": True,
        "site_controllable": True,
        "culture_preset": "none",
    },
    "insectoid": {
        "body_fragments": [
            "INSECT_4LEGS_2ARMS",
            "UPPERBODY_PINCERS",
            "2EYES",
            "HEART",
            "GUTS",
            "BRAIN",
            "MOUTH",
            "2_ANTENNAE",
        ],
        "detail_plans": [
            "CHITIN_MATERIALS",
            "CHITIN_TISSUES",
            "EXOSKELETON_TISSUE_LAYERS:CHITIN:FAT:MUSCLE",
        ],
        "graphics_profile": "simple",
        "intelligent": True,
        "equips": True,
        "can_open_doors": True,
        "site_controllable": True,
        "culture_preset": "hive",
    },
    "serpentine": {
        "body_fragments": [
            "BASIC_1PARTBODY",
            "BASIC_HEAD_NECK",
            "2EYES",
            "NOSE",
            "HEART",
            "GUTS",
            "ORGANS",
            "SPINE",
            "BRAIN",
            "SKULL",
            "MOUTH",
            "FORKED_TONGUE",
            "TEETH",
            "RIBCAGE",
            "TAIL",
        ],
        "detail_plans": [
            "STANDARD_MATERIALS",
            "STANDARD_TISSUES",
            "VERTEBRATE_TISSUE_LAYERS:SKIN:FAT:MUSCLE:BONE:CARTILAGE",
            "STANDARD_HEAD_POSITIONS",
        ],
        "graphics_profile": "simple",
        "intelligent": True,
        "equips": False,
        "can_open_doors": True,
        "site_controllable": False,
        "culture_preset": "none",
        "body_size_adult": 40000,
    },
    "avian_folk": {
        "body_fragments": [
            "HUMANOID_NECK",
            "2WINGS",
            "2EYES",
            "2EARS",
            "2LUNGS",
            "HEART",
            "GUTS",
            "ORGANS",
            "GIZZARD",
            "HUMANOID_JOINTS",
            "THROAT",
            "NECK",
            "SPINE",
            "BRAIN",
            "SKULL",
            "5FINGERS",
            "4TOES",
            "BEAK",
            "TONGUE",
            "RIBCAGE",
        ],
        "detail_plans": [
            "STANDARD_MATERIALS",
            "STANDARD_TISSUES",
            "VERTEBRATE_TISSUE_LAYERS:SKIN:FAT:MUSCLE:BONE:CARTILAGE",
            "STANDARD_HEAD_POSITIONS",
            "HUMANOID_HEAD_POSITIONS",
            "HUMANOID_RIBCAGE_POSITIONS",
            "HUMANOID_RELSIZES",
        ],
        "graphics_profile": "humanoid",
        "intelligent": True,
        "equips": True,
        "can_open_doors": True,
        "site_controllable": True,
        "culture_preset": "aerie",
        "body_size_adult": 50000,
        "color": [6, 0, 1],
    },
    "avian": {
        "body_fragments": [
            "HUMANOID_ARMLESS_NECK",
            "2WINGS",
            "2EYES",
            "2LUNGS",
            "HEART",
            "GUTS",
            "ORGANS",
            "GIZZARD",
            "THROAT",
            "NECK",
            "SPINE",
            "BRAIN",
            "SKULL",
            "4TOES",
            "BEAK",
            "TONGUE",
            "RIBCAGE",
        ],
        "detail_plans": [
            "STANDARD_MATERIALS",
            "STANDARD_TISSUES",
            "VERTEBRATE_TISSUE_LAYERS:SKIN:FAT:MUSCLE:BONE:CARTILAGE",
            "STANDARD_HEAD_POSITIONS",
        ],
        "graphics_profile": "simple",
        "intelligent": False,
        "equips": False,
        "can_open_doors": False,
        "site_controllable": False,
        "culture_preset": "aerie",
        "body_size_adult": 8000,
        "color": [6, 0, 0],
    },
    "aquatic": {
        "body_fragments": [
            "BASIC_2PARTBODY",
            "BASIC_HEAD",
            "SIDE_FINS",
            "DORSAL_FIN",
            "TAIL",
            "2EYES",
            "HEART",
            "GUTS",
            "ORGANS",
            "SPINE",
            "BRAIN",
            "SKULL",
            "MOUTH",
            "RIBCAGE",
            "GENERIC_TEETH",
        ],
        "detail_plans": [
            "STANDARD_MATERIALS",
            "STANDARD_TISSUES",
            "VERTEBRATE_TISSUE_LAYERS:SKIN:FAT:MUSCLE:BONE:CARTILAGE",
            "STANDARD_HEAD_POSITIONS",
        ],
        "graphics_profile": "simple",
        "intelligent": False,
        "equips": False,
        "can_open_doors": False,
        "site_controllable": False,
        "culture_preset": "depths",
        "body_size_adult": 30000,
        "color": [1, 0, 1],
    },
    "arachnid": {
        "body_fragments": [
            "SPIDER",
            "2EYES",
            "HEART",
            "GUTS",
            "BRAIN",
            "MOUTH",
            "2_ANTENNAE",
        ],
        "detail_plans": [
            "CHITIN_MATERIALS",
            "CHITIN_TISSUES",
            "EXOSKELETON_TISSUE_LAYERS:CHITIN:FAT:MUSCLE",
        ],
        "graphics_profile": "simple",
        "intelligent": True,
        "equips": False,
        "can_open_doors": True,
        "site_controllable": False,
        "culture_preset": "hive",
        "body_size_adult": 20000,
        "color": [0, 0, 1],
    },
    "amorphous": {
        "body_fragments": [
            "BASIC_1PARTBODY_THOUGHT",
            "MOUTH",
        ],
        "detail_plans": [
            "STANDARD_MATERIALS",
            "STANDARD_TISSUES",
            "VERTEBRATE_TISSUE_LAYERS:SKIN:FAT:MUSCLE:BONE:CARTILAGE",
        ],
        "graphics_profile": "simple",
        "intelligent": True,
        "equips": False,
        "can_open_doors": True,
        "site_controllable": False,
        "culture_preset": "none",
        "body_size_adult": 20000,
        "color": [5, 0, 0],
    },
    "centauroid": {
        "body_fragments": [
            "HAND_FOOT_CENTAUR_NECK",
            "TAIL",
            "2EYES",
            "2EARS",
            "NOSE",
            "2LUNGS",
            "HEART",
            "GUTS",
            "ORGANS",
            "THROAT",
            "NECK",
            "SPINE",
            "BRAIN",
            "SKULL",
            "4FINGERS",
            "4TOES",
            "MOUTH",
            "TONGUE",
            "TEETH",
            "RIBCAGE",
        ],
        "detail_plans": [
            "STANDARD_MATERIALS",
            "STANDARD_TISSUES",
            "VERTEBRATE_TISSUE_LAYERS:SKIN:FAT:MUSCLE:BONE:CARTILAGE",
            "STANDARD_HEAD_POSITIONS",
            "HUMANOID_HEAD_POSITIONS",
        ],
        "graphics_profile": "humanoid",
        "intelligent": True,
        "equips": True,
        "can_open_doors": True,
        "site_controllable": True,
        "culture_preset": "none",
        "body_size_adult": 120000,
        "color": [4, 0, 0],
    },
    "hoofed_humanoid": {
        "body_fragments": [
            "HUMANOID_NECK_HOOF",
            "2EYES",
            "2EARS",
            "NOSE",
            "2LUNGS",
            "HEART",
            "GUTS",
            "ORGANS",
            "HUMANOID_JOINTS",
            "THROAT",
            "NECK",
            "SPINE",
            "BRAIN",
            "SKULL",
            "5FINGERS",
            "MOUTH",
            "TONGUE",
            "FACIAL_FEATURES",
            "TEETH",
            "RIBCAGE",
            "2HEAD_HORN",
        ],
        "detail_plans": [
            "STANDARD_MATERIALS",
            "STANDARD_TISSUES",
            "VERTEBRATE_TISSUE_LAYERS:SKIN:FAT:MUSCLE:BONE:CARTILAGE",
            "STANDARD_HEAD_POSITIONS",
            "HUMANOID_HEAD_POSITIONS",
            "HUMANOID_RIBCAGE_POSITIONS",
            "HUMANOID_RELSIZES",
        ],
        "graphics_profile": "humanoid",
        "intelligent": True,
        "equips": True,
        "can_open_doors": True,
        "site_controllable": True,
        "culture_preset": "none",
        "body_size_adult": 80000,
        "color": [6, 0, 0],
    },
    "tentacled": {
        "body_fragments": [
            "BASIC_2PARTBODY",
            "BASIC_HEAD",
            "2_HEAD_CLUBBED_TENTACLES",
            "2EYES",
            "HEART",
            "GUTS",
            "ORGANS",
            "BRAIN",
            "SKULL",
            "MOUTH",
            "TONGUE",
        ],
        "detail_plans": [
            "STANDARD_MATERIALS",
            "STANDARD_TISSUES",
            "VERTEBRATE_TISSUE_LAYERS:SKIN:FAT:MUSCLE:BONE:CARTILAGE",
            "STANDARD_HEAD_POSITIONS",
        ],
        "graphics_profile": "simple",
        "intelligent": True,
        "equips": True,
        "can_open_doors": True,
        "site_controllable": True,
        "culture_preset": "depths",
        "body_size_adult": 70000,
        "color": [5, 0, 1],
    },
    "shelled_quadruped": {
        "body_fragments": [
            "QUADRUPED_NECK",
            "TAIL",
            "2EYES",
            "NOSE",
            "2LUNGS",
            "HEART",
            "GUTS",
            "ORGANS",
            "THROAT",
            "NECK",
            "SPINE",
            "BRAIN",
            "SKULL",
            "BEAK",
            "RIBCAGE",
            "SHELL",
        ],
        "detail_plans": [
            "STANDARD_MATERIALS",
            "STANDARD_TISSUES",
            "VERTEBRATE_TISSUE_LAYERS:SKIN:FAT:MUSCLE:BONE:CARTILAGE",
            "STANDARD_HEAD_POSITIONS",
        ],
        "graphics_profile": "simple",
        "intelligent": False,
        "equips": False,
        "can_open_doors": False,
        "site_controllable": False,
        "culture_preset": "none",
        "body_size_adult": 40000,
        "color": [2, 0, 0],
    },
    # Placeholder: real custom_body is built by hematophyte_custom_body(creature_id)
    "hematophyte": {
        "body_mode": "custom",
        "body_fragments": [],
        "detail_plans": [],
        "bodygloss": ["MAW"],
        "graphics_profile": "simple",
        "intelligent": True,
        "equips": True,
        "can_open_doors": True,
        "site_controllable": True,
        "culture_preset": "elf_nature",
        "body_size_adult": 90000,
        "color": [2, 0, 1],
    },
}


def _part(
    pid: str,
    name: str,
    plural: str,
    *,
    flags: Optional[List[str]] = None,
    category: Optional[str] = None,
    con: Optional[str] = None,
    contype: Optional[str] = None,
    con_cat: Optional[str] = None,
    relsize: int = 100,
    number: Optional[int] = None,
    individual_name: Optional[str] = None,
    individual_plural: Optional[str] = None,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "id": pid,
        "name": name,
        "plural": plural,
        "flags": list(flags or []),
        "category": category,
        "con": con,
        "contype": contype,
        "con_cat": con_cat,
        "relsize": relsize,
    }
    if number is not None:
        out["number"] = number
    if individual_name:
        out["individual_name"] = individual_name
        out["individual_plural"] = individual_plural or individual_name
    return out


def hematophyte_custom_body(creature_id: str) -> Dict[str, Any]:
    """Original vine-serpent plant–animal body (not a vanilla fragment mash).

    Uses documented BP / BODY_DETAIL_PLAN tokens only (archived DF wiki).
    """
    oid = f"AAMT_{creature_id.strip().upper()}"
    parts: List[Dict[str, Any]] = [
        # Root of body tree: UPPERBODY+LOWERBODY (wiki: multiple UPPERBODY redundant; both on trunk is intentional for serpentine).
        _part("TRUNK", "trunk", "trunks", flags=["UPPERBODY", "LOWERBODY"], category="TRUNK", relsize=2000),
        _part("HD", "head", "STP", flags=["HEAD"], category="HEAD", con="TRUNK", relsize=300),
        # Mouth on head: EMBEDDED + APERTURE like vanilla MOUTH.
        _part(
            "MAW",
            "mouth",
            "mouths",
            flags=["MOUTH", "SMALL", "EMBEDDED", "APERTURE"],
            category="MOUTH",
            con="HD",
            relsize=40,
        ),
        # Stacked teeth (wiki NUMBER capped at 32) with SOCKET for knock-out.
        _part(
            "TOOTH",
            "tooth",
            "teeth",
            flags=["SMALL", "SOCKET"],
            category="TOOTH",
            con="MAW",
            relsize=1,
            number=32,
            individual_name="tooth",
            individual_plural="teeth",
        ),
        _part("PROBOSCIS", "proboscis", "proboscises", flags=[], category="PROBOSCIS", con="HD", relsize=80),
        _part("RE", "right eye", "STP", flags=["SIGHT", "EMBEDDED", "SMALL", "RIGHT"], category="EYE", con="HD", relsize=5),
        _part("LE", "left eye", "STP", flags=["SIGHT", "EMBEDDED", "SMALL", "LEFT"], category="EYE", con="HD", relsize=5),
        # Thought center is INTERNAL brain (wiki THOUGHT); trunk is not a thought hub.
        _part(
            "BRAIN",
            "brain",
            "STP",
            flags=["THOUGHT", "INTERNAL", "SMALL"],
            category="BRAIN",
            contype="HEAD",
            relsize=200,
        ),
        _part(
            "HEART",
            "heart",
            "STP",
            flags=["CIRCULATION", "INTERNAL", "SMALL"],
            category="HEART",
            contype="UPPERBODY",
            relsize=100,
        ),
        _part(
            "GUTS",
            "guts",
            "guts",
            flags=["GUTS", "INTERNAL", "SMALL", "UNDER_PRESSURE"],
            category="GUTS",
            contype="LOWERBODY",
            relsize=600,
        ),
        # Six vine hydrostats + grasp tips + thorns
        _part("RV1", "right fore vine", "STP", flags=["LIMB", "RIGHT"], category="VINE", con="TRUNK", relsize=500),
        _part("LV1", "left fore vine", "STP", flags=["LIMB", "LEFT"], category="VINE", con="TRUNK", relsize=500),
        _part("RV2", "right mid vine", "STP", flags=["LIMB", "RIGHT"], category="VINE", con="TRUNK", relsize=450),
        _part("LV2", "left mid vine", "STP", flags=["LIMB", "LEFT"], category="VINE", con="TRUNK", relsize=450),
        _part("RV3", "right hind vine", "STP", flags=["LIMB", "RIGHT"], category="VINE", con="TRUNK", relsize=400),
        _part("LV3", "left hind vine", "STP", flags=["LIMB", "LEFT"], category="VINE", con="TRUNK", relsize=400),
        _part("RVT1", "right fore vine tip", "STP", flags=["GRASP", "RIGHT"], category="VINE_TIP", con="RV1", relsize=40),
        _part("LVT1", "left fore vine tip", "STP", flags=["GRASP", "LEFT"], category="VINE_TIP", con="LV1", relsize=40),
        _part("RVT2", "right mid vine tip", "STP", flags=["GRASP", "RIGHT"], category="VINE_TIP", con="RV2", relsize=40),
        _part("LVT2", "left mid vine tip", "STP", flags=["GRASP", "LEFT"], category="VINE_TIP", con="LV2", relsize=40),
        # Thorns EMBEDDED on vines (wiki: surface of parent; not severable as whole limbs).
        _part("TH1", "fore thorn", "STP", flags=["SMALL", "EMBEDDED"], category="THORN", con="RV1", relsize=15),
        _part("TH2", "mid thorn", "STP", flags=["SMALL", "EMBEDDED"], category="THORN", con="LV2", relsize=15),
        _part("TH3", "hind thorn", "STP", flags=["SMALL", "EMBEDDED"], category="THORN", con="RV3", relsize=15),
        _part("STH1", "sensory thorn", "STP", flags=["SMALL", "EMBEDDED"], category="THORN", con="LV1", relsize=10),
        # Fronds EMBEDDED on trunk (spike-layout style surface growths).
        _part("FROND1", "dorsal frond", "STP", flags=["EMBEDDED"], category="FROND", con="TRUNK", relsize=200),
        _part("FROND2", "rear frond", "STP", flags=["EMBEDDED"], category="FROND", con="TRUNK", relsize=180),
        _part("RP1", "fore root-pad", "STP", flags=["EMBEDDED"], category="ROOTPAD", con="TRUNK", relsize=120),
        _part("RP2", "hind root-pad", "STP", flags=["EMBEDDED"], category="ROOTPAD", con="TRUNK", relsize=120),
    ]
    # Fronds use PLANT_SURFACE (wiki tissue tokens via AAMT plant template + STRUCTURAL_PLANT mat).
    # Thorns use NAIL (vanilla NAIL_TEMPLATE; not in STANDARD_TISSUES — added below).
    layers = [
        ["BP_LAYERS", "BY_CATEGORY", "TRUNK", "MUSCLE", "50", "FAT", "5", "SKIN", "1"],
        ["BP_LAYERS", "BY_CATEGORY", "HEAD", "MUSCLE", "50", "FAT", "5", "SKIN", "1"],
        ["BP_LAYERS", "BY_CATEGORY", "MOUTH", "MUSCLE", "10", "SKIN", "1"],
        ["BP_LAYERS", "BY_CATEGORY", "TOOTH", "TOOTH", "100"],
        ["BP_LAYERS", "BY_CATEGORY", "PROBOSCIS", "CARTILAGE", "4", "SKIN", "1"],
        ["BP_LAYERS", "BY_CATEGORY", "EYE", "EYE", "100"],
        ["BP_LAYERS", "BY_CATEGORY", "BRAIN", "BRAIN", "100"],
        ["BP_LAYERS", "BY_CATEGORY", "HEART", "HEART", "100"],
        ["BP_LAYERS", "BY_CATEGORY", "GUTS", "GUT", "100"],
        ["BP_LAYERS", "BY_CATEGORY", "VINE", "MUSCLE", "50", "SKIN", "1"],
        ["BP_LAYERS", "BY_CATEGORY", "VINE_TIP", "MUSCLE", "25", "SKIN", "1"],
        ["BP_LAYERS", "BY_CATEGORY", "THORN", "NAIL", "100"],
        ["BP_LAYERS", "BY_CATEGORY", "FROND", "PLANT_SURFACE", "100"],
        ["BP_LAYERS", "BY_CATEGORY", "ROOTPAD", "MUSCLE", "30", "SKIN", "1"],
    ]
    relsizes = [
        ["BP_RELSIZE", "BY_CATEGORY", "TRUNK", "2000"],
        ["BP_RELSIZE", "BY_CATEGORY", "HEAD", "300"],
        ["BP_RELSIZE", "BY_CATEGORY", "MOUTH", "40"],
        ["BP_RELSIZE", "BY_CATEGORY", "TOOTH", "1"],
        ["BP_RELSIZE", "BY_CATEGORY", "PROBOSCIS", "80"],
        ["BP_RELSIZE", "BY_CATEGORY", "EYE", "5"],
        ["BP_RELSIZE", "BY_CATEGORY", "BRAIN", "200"],
        ["BP_RELSIZE", "BY_CATEGORY", "HEART", "100"],
        ["BP_RELSIZE", "BY_CATEGORY", "GUTS", "600"],
        ["BP_RELSIZE", "BY_CATEGORY", "VINE", "450"],
        ["BP_RELSIZE", "BY_CATEGORY", "VINE_TIP", "40"],
        ["BP_RELSIZE", "BY_CATEGORY", "THORN", "15"],
        ["BP_RELSIZE", "BY_CATEGORY", "FROND", "190"],
        ["BP_RELSIZE", "BY_CATEGORY", "ROOTPAD", "120"],
    ]
    # Wiki BP_POSITION: FRONT BACK LEFT RIGHT TOP BOTTOM
    # Wiki BP_RELATION: AROUND SURROUNDED_BY ABOVE BELOW IN_FRONT BEHIND CLEANS CLEANED_BY
    positions = [
        ["BP_POSITION", "BY_CATEGORY", "FROND", "TOP"],
        ["BP_POSITION", "BY_CATEGORY", "ROOTPAD", "BOTTOM"],
        ["BP_POSITION", "BY_CATEGORY", "PROBOSCIS", "FRONT"],
        ["BP_POSITION", "BY_CATEGORY", "MOUTH", "FRONT"],
        ["BP_RELATION", "BY_CATEGORY", "FROND", "ABOVE", "BY_CATEGORY", "TRUNK", "50"],
        ["BP_RELATION", "BY_CATEGORY", "ROOTPAD", "BELOW", "BY_CATEGORY", "TRUNK", "50"],
        ["BP_RELATION", "BY_CATEGORY", "MOUTH", "IN_FRONT", "BY_CATEGORY", "HEAD", "100"],
        ["BP_RELATION", "BY_CATEGORY", "PROBOSCIS", "IN_FRONT", "BY_CATEGORY", "HEAD", "80"],
        ["BP_RELATION", "BY_CATEGORY", "THORN", "AROUND", "BY_CATEGORY", "VINE", "30"],
    ]
    addons = hematophyte_tissue_addons()
    return {
        "object_id": oid,
        "parts": parts,
        "layers": layers,
        "relsizes": relsizes,
        "positions": positions,
        "add_materials": addons["add_materials"],
        "add_tissues": addons["add_tissues"],
        "emit_plant_surface_template": True,
        "layer_plan": f"{oid}_LAYERS",
        "relsize_plan": f"{oid}_RELSIZES",
        "position_plan": f"{oid}_POSITIONS",
    }


# GUI labels. playable = grasp + thought + typical civ flags (heuristic).
PRESET_INFO: Dict[str, Dict[str, Any]] = {
    "humanoid_civ": {"label": "Humanoid folk", "playable": True, "plan": "humanoid"},
    "winged_humanoid": {"label": "Winged humanoid", "playable": True, "plan": "winged"},
    "hoofed_humanoid": {"label": "Hoofed humanoid", "playable": True, "plan": "hoofed"},
    "avian_folk": {"label": "Avian folk (beak + hands + wings)", "playable": True, "plan": "avian"},
    "centauroid": {"label": "Centauroid", "playable": True, "plan": "centaur"},
    "quadruped_grasp": {"label": "Quadruped with front grasp", "playable": True, "plan": "quadruped"},
    "insectoid": {"label": "Insectoid (4 legs + 2 arms)", "playable": True, "plan": "insectoid"},
    "tentacled": {"label": "Tentacled (clubbed grasp)", "playable": True, "plan": "tentacled"},
    "hematophyte": {
        "label": "Hematophyte (custom plant–animal vines + maw)",
        "playable": True,
        "plan": "hematophyte",
        "body_mode": "custom",
    },
    "arachnid": {"label": "Arachnid", "playable": False, "plan": "arachnid"},
    "avian": {"label": "Bird (armless)", "playable": False, "plan": "avian"},
    "aquatic": {"label": "Aquatic / fish", "playable": False, "plan": "aquatic"},
    "serpentine": {"label": "Serpentine", "playable": False, "plan": "serpentine"},
    "amorphous": {"label": "Amorphous blob", "playable": False, "plan": "amorphous"},
    "shelled_quadruped": {"label": "Shelled quadruped", "playable": False, "plan": "shelled"},
}

CULTURE_PRESETS = ("none", "dwarf_industry", "elf_nature", "goblin_raid", "aerie", "hive", "depths")
PHONOLOGY_PRESETS = ("harsh", "liquid", "guttural")
GRAPHICS_PROFILES = ("humanoid", "simple")


def _pluralize(name: str) -> str:
    n = name.strip().lower()
    if not n:
        return "creatures"
    if n.endswith("s"):
        return n
    if n.endswith("y") and len(n) > 1 and n[-2] not in "aeiou":
        return n[:-1] + "ies"
    if n.endswith(("ch", "sh", "x", "z")):
        return n + "es"
    return n + "s"


def _adjective(name: str) -> str:
    n = name.strip().lower()
    if not n:
        return "strange"
    if n.endswith("f"):
        return n + "ish"
    return n + "ish"


def default_detail_plans() -> List[str]:
    return list(BODY_PRESETS["humanoid_civ"]["detail_plans"])


def new_spec(
    creature_id: str,
    name: str,
    preset: str = "humanoid_civ",
    **overrides: Any,
) -> Dict[str, Any]:
    cid = creature_id.strip().upper().replace(" ", "_")
    if not cid:
        raise ValueError("creature id required")
    preset_key = preset if preset in BODY_PRESETS else "humanoid_civ"
    pdata = BODY_PRESETS[preset_key]
    singular = name.strip().lower() or cid.lower()
    plural = _pluralize(singular)
    adj = _adjective(singular)

    spec: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "id": cid,
        "name_singular": singular,
        "name_plural": plural,
        "name_adj": adj,
        "description": f"A custom {singular} shaped by the AAMT creature tool.",
        "prefstring": f"{plural}",
        "body_mode": pdata.get("body_mode") or "fragments",
        "body_fragments": list(pdata.get("body_fragments") or []),
        "detail_plans": list(pdata.get("detail_plans") or default_detail_plans()),
        "bodygloss": list(pdata.get("bodygloss") or []),
        "custom_body": None,
        "intelligent": bool(pdata.get("intelligent", True)),
        "equips": bool(pdata.get("equips", True)),
        "can_open_doors": bool(pdata.get("can_open_doors", True)),
        "site_controllable": bool(pdata.get("site_controllable", True)),
        "culture_preset": pdata.get("culture_preset") or "none",
        "biomes": [],
        "graphics_profile": pdata.get("graphics_profile", "humanoid"),
        "art_prompt": f"fantasy {singular} creature, dwarf fortress style pixel art",
        "phonology": "harsh",
        "custom_reactions": [],
        "custom_workshop": False,
        "include_native_lua": False,
        "color": list(pdata.get("color") or [3, 0, 0]),
        "tile_char": 1,
        "body_size_adult": int(pdata.get("body_size_adult") or 60000),
        "flags": {},
        "preset": preset_key,
    }
    if preset_key == "hematophyte" or pdata.get("body_mode") == "custom":
        cb = hematophyte_custom_body(cid) if preset_key == "hematophyte" else copy.deepcopy(pdata.get("custom_body") or {})
        if preset_key == "hematophyte":
            spec["description"] = (
                f"A photo-metabolic mobile {singular}: serpentine trunk, thorned vine-limbs, "
                f"maw and blood-drawing proboscis. Custom body object, not a vanilla fragment mash."
            )
            spec["art_prompt"] = (
                f"fantasy plant-animal hematophyte {singular}, vine serpent with thorns and fronds, "
                f"dwarf fortress style pixel art"
            )
        spec["body_mode"] = "custom"
        spec["custom_body"] = cb
        oid = cb.get("object_id") or f"AAMT_{cid}"
        spec["detail_plans"] = [
            "STANDARD_MATERIALS",
            "STANDARD_TISSUES",
            cb.get("layer_plan") or f"{oid}_LAYERS",
            cb.get("relsize_plan") or f"{oid}_RELSIZES",
            cb.get("position_plan") or f"{oid}_POSITIONS",
        ]
        if not spec["bodygloss"] and pdata.get("bodygloss"):
            spec["bodygloss"] = list(pdata["bodygloss"])
    for k, v in overrides.items():
        if v is not None:
            spec[k] = v
    return spec


def apply_preset(spec: Dict[str, Any], preset: str) -> Dict[str, Any]:
    """Swap body plan / civ flags from a named preset onto an existing spec."""
    if preset not in BODY_PRESETS:
        raise ValueError(f"Unknown preset: {preset}")
    pdata = BODY_PRESETS[preset]
    out = copy.deepcopy(spec)
    out["preset"] = preset
    out["body_mode"] = pdata.get("body_mode") or "fragments"
    out["body_fragments"] = list(pdata.get("body_fragments") or [])
    out["detail_plans"] = list(pdata.get("detail_plans") or default_detail_plans())
    out["bodygloss"] = list(pdata.get("bodygloss") or [])
    out["graphics_profile"] = pdata.get("graphics_profile", "simple")
    out["intelligent"] = bool(pdata.get("intelligent", True))
    out["equips"] = bool(pdata.get("equips", True))
    out["can_open_doors"] = bool(pdata.get("can_open_doors", True))
    out["site_controllable"] = bool(pdata.get("site_controllable", False))
    if "culture_preset" in pdata:
        out["culture_preset"] = pdata["culture_preset"]
    if "body_size_adult" in pdata:
        out["body_size_adult"] = pdata["body_size_adult"]
    if "color" in pdata:
        out["color"] = list(pdata["color"])
    cid = str(out.get("id") or "CREATURE").upper()
    if preset == "hematophyte" or pdata.get("body_mode") == "custom":
        cb = hematophyte_custom_body(cid) if preset == "hematophyte" else copy.deepcopy(pdata.get("custom_body") or {})
        out["body_mode"] = "custom"
        out["custom_body"] = cb
        oid = cb.get("object_id") or f"AAMT_{cid}"
        out["detail_plans"] = [
            "STANDARD_MATERIALS",
            "STANDARD_TISSUES",
            cb.get("layer_plan") or f"{oid}_LAYERS",
            cb.get("relsize_plan") or f"{oid}_RELSIZES",
            cb.get("position_plan") or f"{oid}_POSITIONS",
        ]
        out["body_fragments"] = []
    else:
        out["custom_body"] = None
        out["body_mode"] = "fragments"
    return out


def load_spec(path: Path | str) -> Dict[str, Any]:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("creature spec must be a JSON object")
    if "id" not in data:
        raise ValueError("creature spec missing id")
    data.setdefault("schema_version", SCHEMA_VERSION)
    data.setdefault("body_mode", "custom" if data.get("custom_body") else "fragments")
    data.setdefault("body_fragments", [])
    data.setdefault("detail_plans", default_detail_plans())
    data.setdefault("custom_reactions", [])
    data.setdefault("flags", {})
    data.setdefault("bodygloss", [])
    return data


def save_spec(spec: Dict[str, Any], path: Path | str) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    out = copy.deepcopy(spec)
    out["schema_version"] = out.get("schema_version", SCHEMA_VERSION)
    p.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def load_presets_file() -> Dict[str, Any]:
    path = templates_dir() / "presets.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"body_presets": BODY_PRESETS}


def write_presets_file(path: Optional[Path] = None) -> Path:
    out = path or (templates_dir() / "presets.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "body_presets": BODY_PRESETS,
        "culture_presets": list(CULTURE_PRESETS),
        "phonology_presets": list(PHONOLOGY_PRESETS),
        "graphics_profiles": list(GRAPHICS_PROFILES),
        "preset_info": PRESET_INFO,
    }
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out
