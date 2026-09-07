#!/usr/bin/env python3
"""
Adventure Mode parity kit — documented stopgap, not Classic engine restoration.

Emits ADVENTURE_MODE_ENABLED reaction wrappers for vanilla-permitted recipes,
lore text files, and optional DFHack helpers. Does not invent conversation,
magic, or site-building engines.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_HERE = Path(__file__).resolve().parent
ADV_DIR = _HERE / "AdventureParity"
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


def adventure_parity_root() -> Path:
    return ADV_DIR


def write_reaction_adv_kit(spec: Dict[str, Any], objects_dir: Path) -> Path:
    """Write adventure reactions cloned from documented vanilla patterns."""
    cid = str(spec["id"]).upper()
    # Patterns from vanilla MAKE_SHARP_ROCK and MAKE WOODEN CUP / chair style
    lines = [
        f"reaction_adv_{cid.lower()}",
        "",
        "[OBJECT:REACTION]",
        "",
        f"[REACTION:AAMT_{cid}_ADV_KNAP_STONE]",
        "\t[NAME:knap a sharp rock (aamt)]",
        "\t[ADVENTURE_MODE_ENABLED]",
        "\t[REAGENT:tool stone:1:ROCK:NONE:NONE:NONE][NO_EDGE_ALLOWED]",
        "\t[REAGENT:hammerstone:1:ROCK:NONE:NONE:NONE][PRESERVE_REAGENT][NO_EDGE_ALLOWED]",
        "\t[PRODUCT:100:1:ROCK:NONE:GET_MATERIAL_FROM_REAGENT:tool stone:NONE][FORCE_EDGE]",
        "\t[SKILL:KNAPPING]",
        "",
        f"[REACTION:AAMT_{cid}_ADV_MAKE_CUP]",
        "\t[NAME:make wooden cup (aamt)]",
        "\t[ADVENTURE_MODE_ENABLED]",
        "\t[BUILDING:CARPENTER:NONE]",
        "\t[REAGENT:log:1:WOOD:NONE:NONE:NONE]",
        "\t\t[ANY_PLANT_MATERIAL]",
        "\t[REAGENT:tool:1:NONE:NONE:NONE:NONE]",
        "\t\t[PRESERVE_REAGENT][HAS_EDGE]",
        "\t[PRODUCT:100:1:GOBLET:NONE:GET_MATERIAL_FROM_REAGENT:log:NONE]",
        "\t[SKILL:CARPENTRY]",
        "\t[CATEGORY:AAMT_ADV_CRAFT]",
        "\t[CATEGORY_NAME:AAMT adventure craft]",
        "\t[CATEGORY_DESCRIPTION:Documented adventure crafting patterns for this civ kit.]",
        "",
    ]
    objects_dir = Path(objects_dir)
    objects_dir.mkdir(parents=True, exist_ok=True)
    path = objects_dir / f"reaction_adv_{cid.lower()}.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_lore_files(spec: Dict[str, Any], kit_dir: Path) -> List[Path]:
    kit_dir = Path(kit_dir)
    kit_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    blurb = {
        "id": spec.get("id"),
        "name": spec.get("name_singular"),
        "description": spec.get("description"),
        "culture_preset": spec.get("culture_preset"),
        "note": "Lore text only — not Classic conversation trees.",
    }
    p1 = kit_dir / "civ_blurb.json"
    p1.write_text(json.dumps(blurb, indent=2) + "\n", encoding="utf-8")
    written.append(p1)
    rumors = kit_dir / "rumors.txt"
    name = spec.get("name_singular") or spec.get("id")
    rumors.write_text(
        "\n".join(
            [
                f"Travelers speak of the {name}.",
                f"The {name} keep to their own ways.",
                f"Some say the {name} craft strange tools.",
                "",
                "# These are static rumor lines for DFHack/scripts to print.",
                "# They do not restore Classic conversation branching.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    written.append(rumors)
    return written


LORE_LUA = '''-- {modid}_adv_lore.lua
-- AAMT Adventure parity: print civ blurb / rumor lines (main thread).
-- Usage: {modid}_adv_lore
-- Does NOT restore Classic conversation UI.

local modid = "{modid}"
local creature = "{creature_id}"
local name = "{name}"

local rumors = {{
{rumor_lines}
}}

local function show()
  local msg = string.format("[%s] Lore for %s (%s)", modid, name, creature)
  if dfhack and dfhack.gui and dfhack.gui.showAnnouncement then
    dfhack.gui.showAnnouncement(msg, COLOR_CYAN)
    for _, line in ipairs(rumors) do
      dfhack.gui.showAnnouncement(line, COLOR_WHITE)
    end
  else
    print(msg)
    for _, line in ipairs(rumors) do print("  " .. line) end
  end
end

show()
'''


def write_adv_dfhack_scripts(spec: Dict[str, Any], scripts_dir: Path) -> List[Path]:
    scripts_dir = Path(scripts_dir)
    scripts_dir.mkdir(parents=True, exist_ok=True)
    cid = str(spec["id"]).upper()
    modid = f"aamt_{cid.lower()}"
    name = str(spec.get("name_singular") or cid.lower()).replace('"', "")
    rumor_lines = "\n".join(
        [
            f'  "Travelers speak of the {name}.",',
            f'  "The {name} keep to their own ways.",',
        ]
    )
    text = LORE_LUA.format(modid=modid, creature_id=cid, name=name, rumor_lines=rumor_lines)
    path = scripts_dir / f"{modid}_adv_lore.lua"
    path.write_text(text, encoding="utf-8")
    readme = scripts_dir / "README.txt"
    readme.write_text(
        "\n".join(
            [
                "AAMT Adventure parity DFHack scripts",
                "- *_adv_lore.lua : print civ rumor lines (main thread)",
                "- Site/camp construction: use official Steam Adventure camp tools when present.",
                "- Secrets/magic: omitted — do not invent secret-learning APIs.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return [path, readme]


def stage_adventure_kit(spec: Dict[str, Any], mod_root: Path) -> List[str]:
    """Stage kit under mod_root. Returns relative paths written."""
    from df_paths import dfhack_present, dfhack_scripts

    mod_root = Path(mod_root)
    objects = mod_root / "objects"
    kit = mod_root / "AdventureParity"
    written: List[Path] = []

    # Ensure gap catalog is available in staging
    ADV_DIR.mkdir(parents=True, exist_ok=True)
    catalog = ADV_DIR / "CLASSIC_VS_STEAM.md"
    if not catalog.is_file():
        catalog.write_text(_DEFAULT_GAP_MD, encoding="utf-8")
    dest_cat = kit / "CLASSIC_VS_STEAM.md"
    dest_cat.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(catalog, dest_cat)
    written.append(dest_cat)

    written.append(write_reaction_adv_kit(spec, objects))
    written.extend(write_lore_files(spec, kit))

    # DFHack scripts: always stage a copy under mod; install to hack/scripts only if present
    staged_scripts = kit / "scripts"
    written.extend(write_adv_dfhack_scripts(spec, staged_scripts))
    if dfhack_present():
        hs = dfhack_scripts()
        if hs:
            written.extend(write_adv_dfhack_scripts(spec, hs))

    # Permit adventure reactions on entity file if present
    _append_entity_permits(spec, objects)

    return [str(p.relative_to(mod_root)).replace("\\", "/") for p in written]


def _append_entity_permits(spec: Dict[str, Any], objects: Path) -> None:
    cid = str(spec["id"]).upper()
    ent = objects / f"entity_{cid.lower()}.txt"
    if not ent.is_file():
        return
    text = ent.read_text(encoding="latin-1", errors="replace")
    extras = [
        f"\t[PERMITTED_REACTION:AAMT_{cid}_ADV_KNAP_STONE]",
        f"\t[PERMITTED_REACTION:AAMT_{cid}_ADV_MAKE_CUP]",
    ]
    for line in extras:
        if line.strip() not in text:
            text = text.rstrip() + "\n" + line + "\n"
    ent.write_text(text, encoding="latin-1", errors="replace")


_DEFAULT_GAP_MD = """# Classic vs Steam Adventure Mode (honest gap catalog)

This is a **documentation stopgap** for AAMT. It does not restore Classic systems.

| System | Steam status | AAMT kit |
|--------|--------------|----------|
| Movement / combat / inventory | Complete enough to play | None needed |
| Fast travel / sites | Complete | None needed |
| Companions | Present | None needed |
| Conversation depth | Partial vs Classic | Lore/rumor text only (not dialogue trees) |
| Crafting / reactions | Partial | `ADVENTURE_MODE_ENABLED` reactions using documented tokens |
| Magic / secrets | Missing / incomplete | Omitted (no invented APIs) |
| Site / camp building | Partial | Document official tools; do not fake construction |
| Quests | Basic | Not emulated |
| World politics | Missing | Not emulated |

## Rules

- Do not invent DF raw tokens.
- Do not invent DFHack conversation overlay APIs.
- Workers/scripts must not claim Classic parity.

## Sources

Player-facing Steam Adventure Mode status as of Premium development (feature-incomplete vs Classic ASCII UI era). Update this table when official patches land.
"""
