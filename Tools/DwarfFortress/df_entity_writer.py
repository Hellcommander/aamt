#!/usr/bin/env python3
"""Write entity RAW from mountain skeleton + culture preset."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from df_paths import templates_dir

CULTURE_BIOMES: Dict[str, Dict[str, Any]] = {
    "dwarf_industry": {
        "exclusive_start": "MOUNTAIN",
        "settlement": ["ANY_FOREST", "MOUNTAIN", "ANY_GRASSLAND", "ANY_SAVANNA", "ANY_SHRUBLAND"],
        "support": [
            ("ANY_FOREST", 1),
            ("MOUNTAIN", 3),
            ("ANY_GRASSLAND", 1),
            ("ANY_SAVANNA", 1),
            ("ANY_SHRUBLAND", 1),
            ("ANY_RIVER", 1),
        ],
    },
    "elf_nature": {
        "exclusive_start": "ANY_FOREST",
        "settlement": ["ANY_FOREST", "ANY_GRASSLAND", "ANY_SHRUBLAND", "MOUNTAIN"],
        "support": [
            ("ANY_FOREST", 3),
            ("ANY_GRASSLAND", 1),
            ("ANY_SHRUBLAND", 2),
            ("MOUNTAIN", 1),
            ("ANY_RIVER", 2),
        ],
    },
    "goblin_raid": {
        "exclusive_start": "ANY_GRASSLAND",
        "settlement": ["ANY_GRASSLAND", "ANY_SAVANNA", "ANY_SHRUBLAND", "MOUNTAIN", "ANY_FOREST"],
        "support": [
            ("ANY_GRASSLAND", 2),
            ("ANY_SAVANNA", 2),
            ("ANY_SHRUBLAND", 1),
            ("MOUNTAIN", 1),
            ("ANY_FOREST", 1),
            ("ANY_RIVER", 1),
        ],
    },
}


def _entity_id(spec: Dict[str, Any]) -> str:
    return f"{str(spec['id']).upper()}_CIV"


def _replace_biome_block(text: str, culture: str, biomes_override: Optional[Sequence[str]]) -> str:
    cfg = CULTURE_BIOMES.get(culture, CULTURE_BIOMES["dwarf_industry"])
    exclusive = cfg["exclusive_start"]
    settlements = list(cfg["settlement"])
    support = list(cfg["support"])
    if biomes_override:
        settlements = list(biomes_override)
        if settlements:
            exclusive = settlements[0]

    # Remove existing biome lines
    text = re.sub(r"^[ \t]*\[EXCLUSIVE_START_BIOME:[^\]]+\]\r?\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[ \t]*\[SETTLEMENT_BIOME:[^\]]+\]\r?\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[ \t]*\[BIOME_SUPPORT:[^\]]+\]\r?\n", "", text, flags=re.MULTILINE)

    block_lines = [f"\t[EXCLUSIVE_START_BIOME:{exclusive}]"]
    for b in settlements:
        block_lines.append(f"\t[SETTLEMENT_BIOME:{b}]")
    for b, w in support:
        block_lines.append(f"\t[BIOME_SUPPORT:{b}:{w}]")
    block = "\n".join(block_lines) + "\n"

    # Insert after TRANSLATION line
    m = re.search(r"\[TRANSLATION:[^\]]+\]\r?\n", text)
    if m:
        text = text[: m.end()] + block + text[m.end() :]
    else:
        text = block + text
    return text


def write_entity_raw(
    spec: Dict[str, Any],
    out_dir: Path,
    *,
    template_path: Optional[Path] = None,
) -> Path:
    tpl = template_path or (templates_dir() / "entity_mountain_skeleton.txt")
    text = tpl.read_text(encoding="latin-1", errors="replace")
    if text.startswith("entity_template"):
        text = text.split("\n", 1)[1] if "\n" in text else text

    cid = str(spec["id"]).upper()
    eid = _entity_id(spec)
    singular = str(spec.get("name_singular") or cid.lower())
    # DF name tokens tolerate spaces poorly in some contexts; prefer hyphenated unit names
    unit = re.sub(r"\s+", "-", singular.strip().lower()) or cid.lower()
    culture = str(spec.get("culture_preset") or "dwarf_industry")
    translation = cid  # language writer uses same id

    text = text.replace("[ENTITY:MOUNTAIN]", f"[ENTITY:{eid}]")
    text = re.sub(r"\[CREATURE:DWARF\]", f"[CREATURE:{cid}]", text)
    text = re.sub(r"\[TRANSLATION:DWARF\]", f"[TRANSLATION:{translation}]", text)

    if not spec.get("site_controllable", True):
        text = re.sub(r"^[ \t]*\[SITE_CONTROLLABLE\]\r?\n", "", text, flags=re.MULTILINE)
        text = re.sub(r"^[ \t]*\[ALL_MAIN_POPS_CONTROLLABLE\]\r?\n", "", text, flags=re.MULTILINE)

    text = _replace_biome_block(text, culture, spec.get("biomes") or None)

    # Light dwarf-specific renames
    text = text.replace("militia-dwarf", f"militia-{unit}")
    text = text.replace("militia-dwarves", f"militia-{unit}s")
    text = text.replace("CHIEF_MEDICAL_DWARF", "CHIEF_MEDICAL_OFFICER")
    text = re.sub(
        r"\[NAME:chief medical dwarf:chief medical dwarves\]",
        f"[NAME:chief medical {unit}:chief medical {unit}s]",
        text,
    )

    # Append custom reactions
    reactions: List[Dict[str, Any]] = list(spec.get("custom_reactions") or [])
    if reactions:
        # Insert before last line / end of file after existing PERMITTED_REACTION block
        extra = []
        for r in reactions:
            rid = str(r.get("id") or r.get("name") or "CUSTOM").upper().replace(" ", "_")
            extra.append(f"\t[PERMITTED_REACTION:{rid}]")
        # Append near end of entity (before closing isn't needed)
        text = text.rstrip() + "\n" + "\n".join(extra) + "\n"

    if "[OBJECT:ENTITY]" not in text:
        text = "[OBJECT:ENTITY]\n\n" + text

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"entity_{cid.lower()}.txt"
    out_path.write_text(text, encoding="latin-1", errors="replace")
    return out_path
