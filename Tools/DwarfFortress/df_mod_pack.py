#!/usr/bin/env python3
"""Assemble and install AAMT Dwarf Fortress creature/civ mods."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from df_body_raw_writer import write_custom_body_raws
from df_creature_schema import load_spec, save_spec
from df_entity_writer import write_entity_raw
from df_graphics_writer import write_graphics
from df_hack_writer import write_dfhack_scripts
from df_language_writer import write_language_raw
from df_lua_writer import write_lua_scripts
from df_paths import mods_dir, output_root
from df_raws_writer import write_creature_raw


def mod_id_for(spec: Dict[str, Any]) -> str:
    return f"aamt_{str(spec['id']).lower()}"


def staging_dir(spec: Dict[str, Any]) -> Path:
    return output_root() / str(spec["id"]).upper()


def write_info_txt(spec: Dict[str, Any], mod_root: Path) -> Path:
    mid = mod_id_for(spec)
    name = str(spec.get("name_singular") or spec["id"]).title()
    desc = str(spec.get("description") or f"AAMT custom civ: {name}")
    # Escape brackets in description lightly
    desc = desc.replace("[", "(").replace("]", ")")
    text = f"""[ID:{mid}]
[NUMERIC_VERSION:5316]
[DISPLAYED_VERSION:53.16]
[EARLIEST_COMPATIBLE_NUMERIC_VERSION:5001]
[EARLIEST_COMPATIBLE_DISPLAYED_VERSION:50.01]
[AUTHOR:AAMT]
[NAME:AAMT {name}]
[DESCRIPTION:{desc}]
"""
    path = Path(mod_root) / "info.txt"
    path.write_text(text, encoding="utf-8")
    return path


def assemble_mod(
    spec: Dict[str, Any],
    *,
    include_graphics_raws: bool = True,
    include_lua: Optional[bool] = None,
    adventure_kit: bool = False,
) -> Path:
    """Build full mod folder under Output/DwarfFortress/<ID>/."""
    root = staging_dir(spec)
    objects = root / "objects"
    objects.mkdir(parents=True, exist_ok=True)

    save_spec(spec, root / "creature.json")
    write_info_txt(spec, root)
    write_custom_body_raws(spec, objects)
    write_creature_raw(spec, objects)
    write_entity_raw(spec, objects)
    write_language_raw(
        str(spec["id"]).upper(),
        objects,
        phonology=str(spec.get("phonology") or "harsh"),
    )

    if include_graphics_raws:
        write_graphics(spec, root)

    do_lua = spec.get("include_native_lua") if include_lua is None else include_lua
    if do_lua:
        write_lua_scripts(spec, root, force=True)

    # Optional reaction object stub when custom_reactions defined
    reactions = spec.get("custom_reactions") or []
    if reactions or spec.get("custom_workshop"):
        _write_reaction_stub(spec, objects)

    try:
        from df_body_cost import save_cost_report

        save_cost_report(spec, root / "cost_report.json")
    except Exception as exc:
        print(f"[df_mod_pack] cost_report skipped: {exc}")

    if adventure_kit or spec.get("adventure_kit"):
        try:
            from df_adventure_kit import stage_adventure_kit

            stage_adventure_kit(spec, root)
        except Exception as exc:
            print(f"[df_mod_pack] adventure kit skipped: {exc}")

    return root


def _write_reaction_stub(spec: Dict[str, Any], objects: Path) -> Path:
    cid = str(spec["id"]).upper()
    lines = ["reaction_aamt_" + cid.lower(), "", "[OBJECT:REACTION]", ""]
    for r in spec.get("custom_reactions") or []:
        rid = str(r.get("id") or "CUSTOM").upper().replace(" ", "_")
        rname = str(r.get("name") or rid.lower().replace("_", " "))
        rtype = str(r.get("type") or "CUSTOM")
        lines += [
            f"[REACTION:{rid}]",
            f"\t[NAME:{rname}]",
            "\t[BUILDING:KILN:NONE]" if rtype.upper() != "SMELTER" else "\t[BUILDING:SMELTER:NONE]",
            "\t[REAGENT:A:150:NONE:NONE:NONE:NONE][ANY_RAW_MATERIAL]",
            "\t[PRODUCT:100:1:BAR:NONE:METAL:IRON][PRODUCT_DIMENSION:150]",
            "\t[SKILL:SMELT]",
            "\t[FUEL]",
            "",
        ]
    if spec.get("custom_workshop"):
        # Minimal custom workshop building token file pointer — keep as reaction-only for safety
        lines.append(f"# custom_workshop requested for {cid}; use vanilla kiln/smelter hooks above")
    path = objects / f"reaction_{cid.lower()}.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def install_mod(spec: Dict[str, Any], *, df_root: Optional[Path] = None) -> Path:
    """Copy staging mod into DF mods/ directory."""
    src = staging_dir(spec)
    if not src.is_dir():
        raise FileNotFoundError(f"Staging mod missing: {src}. Run generate first.")
    dest = mods_dir(df_root) / mod_id_for(spec)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    # DFHack scripts (optional)
    write_dfhack_scripts(spec, df_root=df_root, also_copy_to=dest / "hack_scripts")
    return dest


def pack_zip(spec: Dict[str, Any], zip_path: Optional[Path] = None) -> Path:
    root = staging_dir(spec)
    if not root.is_dir():
        raise FileNotFoundError(root)
    out = zip_path or (output_root() / f"{mod_id_for(spec)}.zip")
    out.parent.mkdir(parents=True, exist_ok=True)
    base = out.with_suffix("")
    archive = shutil.make_archive(str(base), "zip", root=str(root.parent), base_dir=root.name)
    return Path(archive)


def list_generated_files(mod_root: Path) -> List[str]:
    files: List[str] = []
    for p in sorted(Path(mod_root).rglob("*")):
        if p.is_file():
            files.append(str(p.relative_to(mod_root)).replace("\\", "/"))
    return files
