#!/usr/bin/env python3
"""Vanilla tissue template catalog + helpers (DF wiki tissue definition tokens).

Does not invent tissue flags. Tissue templates we emit must use documented tokens:
TISSUE_NAME, TISSUE_MATERIAL, RELATIVE_THICKNESS, HEALING_RATE, VASCULAR,
PAIN_RECEPTORS, TISSUE_SHAPE, CONNECTS, STRUCTURAL, FUNCTIONAL, MUSCULAR, etc.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from df_paths import vanilla_bodies

# Local tissue identifiers created by STANDARD_TISSUES / CHITIN_TISSUES / common USE_TISSUE_TEMPLATE.
# These are the names used in BP_LAYERS rows (not *_TEMPLATE ids).
STANDARD_TISSUE_IDS = frozenset(
    {
        "SKIN",
        "FAT",
        "MUSCLE",
        "BONE",
        "CARTILAGE",
        "HAIR",
        "TOOTH",
        "EYE",
        "NERVE",
        "BRAIN",
        "LUNG",
        "HEART",
        "LIVER",
        "GUT",
        "STOMACH",
        "GIZZARD",
        "PANCREAS",
        "SPLEEN",
        "KIDNEY",
        "CHITIN",
        # Common add-ons via USE_TISSUE_TEMPLATE / ADD_TISSUE (wiki default templates):
        "SHELL",
        "HORN",
        "HOOF",
        "NAIL",
        "CLAW",
        "TALON",
        "IVORY",
        "FEATHER",
        "SCALE",
        "SPINE",
        "SPONGE",
        "FLAME",
        "EYEBROW",
        "EYELASH",
        "MOUSTACHE",
        "SIDEBURNS",
        "CHEEK_WHISKERS",
        "CHIN_WHISKERS",
    }
)

# Template object ids from tissue_template_default.txt / wiki.
TISSUE_TEMPLATE_IDS = frozenset(
    {
        "SKIN_TEMPLATE",
        "FAT_TEMPLATE",
        "MUSCLE_TEMPLATE",
        "BONE_TEMPLATE",
        "SHELL_TEMPLATE",
        "HORN_TEMPLATE",
        "HOOF_TEMPLATE",
        "CARTILAGE_TEMPLATE",
        "HAIR_TEMPLATE",
        "CHEEK_WHISKERS_TEMPLATE",
        "CHIN_WHISKERS_TEMPLATE",
        "MOUSTACHE_TEMPLATE",
        "SIDEBURNS_TEMPLATE",
        "EYEBROW_TEMPLATE",
        "EYELASH_TEMPLATE",
        "FEATHER_TEMPLATE",
        "SCALE_TEMPLATE",
        "NAIL_TEMPLATE",
        "CLAW_TEMPLATE",
        "TALON_TEMPLATE",
        "TOOTH_TEMPLATE",
        "IVORY_TEMPLATE",
        "EYE_TEMPLATE",
        "NERVE_TEMPLATE",
        "BRAIN_TEMPLATE",
        "LUNG_TEMPLATE",
        "HEART_TEMPLATE",
        "LIVER_TEMPLATE",
        "GUT_TEMPLATE",
        "STOMACH_TEMPLATE",
        "GIZZARD_TEMPLATE",
        "PANCREAS_TEMPLATE",
        "SPLEEN_TEMPLATE",
        "KIDNEY_TEMPLATE",
        "FLAME_TEMPLATE",
        "CHITIN_TEMPLATE",
        "SPINE_TEMPLATE",
        "SPONGE_TEMPLATE",
    }
)

# Documented tissue definition flag tokens (wiki). Used only when emitting custom templates.
TISSUE_FLAG_TOKENS = frozenset(
    {
        "THICKENS_ON_STRENGTH",
        "THICKENS_ON_ENERGY_STORAGE",
        "ARTERIES",
        "SCARS",
        "STRUCTURAL",
        "CONNECTIVE_TISSUE_ANCHOR",
        "SETTABLE",
        "SPLINTABLE",
        "FUNCTIONAL",
        "NERVOUS",
        "THOUGHT",
        "MUSCULAR",
        "SMELL",
        "HEAR",
        "FLIGHT",
        "BREATHE",
        "SIGHT",
        "CONNECTS",
        "MAJOR_ARTERIES",
        "COSMETIC",
        "STYLEABLE",
        "TISSUE_LEAKS",
    }
)

# Documented creature-level tissue *layer* tokens (applications of tissues).
TISSUE_LAYER_CREATURE_TOKENS = frozenset(
    {
        "SELECT_TISSUE_LAYER",
        "PLUS_TISSUE_LAYER",
        "SET_TL_GROUP",
        "PLUS_TL_GROUP",
        "SET_LAYER_TISSUE",
        "SHEARABLE_TISSUE_LAYER",
        "TISSUE_LAYER_APPEARANCE_MODIFIER",
        "TISSUE_STYLE_UNIT",
        "TL_COLOR_MODIFIER",
        "TLCM_GENETIC_MODEL",
        "TLCM_IMPORTANCE",
        "TLCM_NOUN",
        "TLCM_TIMING",
        "TL_CONNECTS",
        "TL_HEALING_RATE",
        "TL_MAJOR_ARTERIES",
        "TL_PAIN_RECEPTORS",
        "TL_RELATIVE_THICKNESS",
        "TL_VASCULAR",
    }
)

# Detail-plan tissue layer overrides (wiki body detail plan / tissue layer page).
TL_DETAIL_PLAN_TOKENS = frozenset(
    {
        "SET_LAYER_TISSUE",
        "TL_RELATIVE_THICKNESS",
        "TL_CONNECTS",
        "TL_MAJOR_ARTERIES",
        "TL_HEALING_RATE",
        "TL_VASCULAR",
        "TL_PAIN_RECEPTORS",
    }
)

# AAMT custom tissue template for plant–animal surface (plump-helmet-man pattern).
AAMT_PLANT_SURFACE_TEMPLATE = "AAMT_PLANT_SURFACE_TEMPLATE"
AAMT_PLANT_MATERIAL = "PH_TISSUE"
AAMT_PLANT_TISSUE = "PLANT_SURFACE"


def load_vanilla_tissue_template_ids(df_root: Optional[Path] = None) -> Set[str]:
    bodies = vanilla_bodies(df_root)
    path = bodies / "tissue_template_default.txt"
    found: Set[str] = set()
    if not path.is_file():
        return set(TISSUE_TEMPLATE_IDS)
    text = path.read_text(encoding="latin-1", errors="replace")
    for m in re.finditer(r"\[TISSUE_TEMPLATE:([^\]]+)\]", text):
        found.add(m.group(1).upper())
    return found or set(TISSUE_TEMPLATE_IDS)


def known_layer_tissues(extra: Optional[Set[str]] = None) -> frozenset:
    base = set(STANDARD_TISSUE_IDS)
    base.add(AAMT_PLANT_TISSUE)
    if extra:
        base |= {x.upper() for x in extra}
    return frozenset(base)


def plant_surface_template_raw() -> str:
    """Tissue template mirroring plump helmet man tissue flags (wiki-legal tokens)."""
    return f"""tissue_template_aamt

[OBJECT:TISSUE_TEMPLATE]

[TISSUE_TEMPLATE:{AAMT_PLANT_SURFACE_TEMPLATE}]
	[TISSUE_NAME:plant tissue:NP]
	[TISSUE_MATERIAL:LOCAL_CREATURE_MAT:{AAMT_PLANT_MATERIAL}]
	[MUSCULAR]
	[FUNCTIONAL]
	[STRUCTURAL]
	[RELATIVE_THICKNESS:1]
	[CONNECTS]
	[TISSUE_SHAPE:LAYER]
"""


def hematophyte_tissue_addons() -> Dict[str, List[List[str]]]:
    """ADD_MATERIAL / ADD_TISSUE rows for hematophyte (beyond STANDARD_*)."""
    return {
        "add_materials": [
            ["ADD_MATERIAL", AAMT_PLANT_MATERIAL, "STRUCTURAL_PLANT_TEMPLATE"],
            ["ADD_MATERIAL", "NAIL", "NAIL_TEMPLATE"],
        ],
        "add_tissues": [
            ["ADD_TISSUE", AAMT_PLANT_TISSUE, AAMT_PLANT_SURFACE_TEMPLATE],
            ["ADD_TISSUE", "NAIL", "NAIL_TEMPLATE"],
        ],
    }
