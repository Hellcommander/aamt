#!/usr/bin/env python3
"""Write creature RAW files from a creature.json spec + dwarf skeleton template."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from df_attack import derive_attacks, derive_tissue_layer_overrides
from df_body_raw_writer import (
    custom_detail_plans_for_spec,
    is_custom_body,
)
from df_paths import templates_dir


def _body_line(fragments: Sequence[str]) -> str:
    return "BODY:" + ":".join(fragments)


def _derive_attacks(spec: Dict[str, Any]) -> str:
    """Build ATTACK raw block from anatomy flags / custom categories."""
    return derive_attacks(spec)


def _strip_humanoid_tl_cosmetics(text: str) -> str:
    """Remove dwarf hair/beard/nail SET_TL_GROUP cosmetics (wiki TL tokens left for skin/eyes)."""
    # From first hair SET_TL_GROUP through broken nail stubs, stop before ALL:SKIN.
    text = re.sub(
        r"\t\t\[SET_TL_GROUP:BY_CATEGORY:HEAD:HAIR\].*?(?=\t\t\[SET_TL_GROUP:BY_CATEGORY:ALL:SKIN\])",
        "",
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"\t\tSET_TL_GROUP:BY_CATEGORY:FINGER:NAIL\].*?(?=\t\t\[SET_TL_GROUP:BY_CATEGORY:ALL:SKIN\])",
        "",
        text,
        count=1,
        flags=re.DOTALL,
    )
    return text


def _append_plant_surface_colors(text: str, spec: Dict[str, Any]) -> str:
    """Optional SET_TL_GROUP colors for PLANT_SURFACE fronds (wiki TL_COLOR_MODIFIER)."""
    cb = spec.get("custom_body") or {}
    tissues = set()
    for row in cb.get("add_tissues") or []:
        args = [str(x).upper() for x in row]
        if args and args[0] == "ADD_TISSUE" and len(args) >= 2:
            tissues.add(args[1])
        elif args:
            tissues.add(args[0])
    if "PLANT_SURFACE" not in tissues:
        return text
    block = (
        "\t\t[SET_TL_GROUP:BY_CATEGORY:FROND:PLANT_SURFACE]\n"
        "\t\t\t[TL_COLOR_MODIFIER:GREEN:1:EMERALD:1:FERN_GREEN:1:MOSS_GREEN:1:OLIVE:1]\n"
        "\t\t\t\t[TLCM_NOUN:fronds:PLURAL]\n"
    )
    # Insert before eye color group if present, else append before end of file.
    m = re.search(r"\t\t\[SET_TL_GROUP:BY_CATEGORY:EYE:EYE\]", text)
    if m:
        return text[: m.start()] + block + "\n" + text[m.start() :]
    return text.rstrip() + "\n" + block



def _replace_token_line(text: str, token: str, new_line: str) -> str:
    """Replace the first line containing [TOKEN:...] with new_line (may include tabs)."""
    pattern = re.compile(rf"^([ \t]*)\[{re.escape(token)}:[^\]]*\][^\n]*$", re.MULTILINE)
    m = pattern.search(text)
    if not m:
        return text
    return text[: m.start()] + new_line + text[m.end() :]


def _set_flag(text: str, flag: str, enabled: bool) -> str:
    """Ensure [FLAG] present or remove it."""
    pattern = re.compile(rf"^[ \t]*\[{re.escape(flag)}\][ \t]*\r?\n", re.MULTILINE)
    has = pattern.search(text) is not None
    if enabled and not has:
        # Insert after CREATURE header block near INTELLIGENT area
        text = text.replace("[CREATURE:", f"[CREATURE:", 1)
        insert_after = re.search(r"\[CREATURE:[^\]]+\]\r?\n", text)
        if insert_after:
            pos = insert_after.end()
            text = text[:pos] + f"\t[{flag}]\n" + text[pos:]
        return text
    if not enabled and has:
        text = pattern.sub("", text)
    return text


def write_creature_raw(
    spec: Dict[str, Any],
    out_dir: Path,
    *,
    template_path: Optional[Path] = None,
) -> Path:
    tpl = template_path or (templates_dir() / "creature_dwarf_skeleton.txt")
    text = tpl.read_text(encoding="latin-1", errors="replace")

    cid = str(spec["id"]).upper()
    singular = str(spec.get("name_singular") or cid.lower())
    plural = str(spec.get("name_plural") or singular + "s")
    adj = str(spec.get("name_adj") or singular + "ish")
    desc = str(spec.get("description") or f"A {singular}.")
    pref = str(spec.get("prefstring") or plural)
    frags = list(spec.get("body_fragments") or [])
    color = spec.get("color") or [3, 0, 0]
    if len(color) < 3:
        color = list(color) + [0] * (3 - len(color))
    tile = int(spec.get("tile_char") or 1)
    adult_size = int(spec.get("body_size_adult") or 60000)

    # Strip leading template label line if present
    if text.startswith("creature_template"):
        text = text.split("\n", 1)[1] if "\n" in text else text

    text = text.replace("[CREATURE:DWARF]", f"[CREATURE:{cid}]")
    text = _replace_token_line(text, "DESCRIPTION", f"\t[DESCRIPTION:{desc}]")
    text = _replace_token_line(text, "NAME", f"\t[NAME:{singular}:{plural}:{adj}]")
    text = _replace_token_line(text, "CASTE_NAME", f"\t[CASTE_NAME:{singular}:{plural}:{adj}]")
    text = _replace_token_line(
        text,
        "CREATURE_TILE",
        f"\t[CREATURE_TILE:{tile}][COLOR:{color[0]}:{color[1]}:{color[2]}]",
    )
    # COLOR may already be on same line — also fix standalone COLOR if present
    text = re.sub(
        r"\[COLOR:\d+:\d+:\d+\]",
        f"[COLOR:{color[0]}:{color[1]}:{color[2]}]",
        text,
        count=1,
    )
    text = _replace_token_line(text, "PREFSTRING", f"\t[PREFSTRING:{pref}]")
    if is_custom_body(spec):
        from df_body_raw_writer import custom_object_id

        oid = custom_object_id(spec)
        text = _replace_token_line(text, "BODY", f"\t[BODY:{oid}]")
        detail_plans = custom_detail_plans_for_spec(spec)
        # Drop leftover dwarf facial-hair / nail / eyebrow layers (nails come via ADD_TISSUE).
        text = re.sub(
            r"\t\[(?:BODY_DETAIL_PLAN:(?:HEAD_HAIR|FACIAL_HAIR|HUMANOID_|STANDARD_HEAD)[^\]]*|USE_MATERIAL_TEMPLATE:NAIL[^\]]*|USE_TISSUE_TEMPLATE:NAIL[^\]]*|USE_TISSUE_TEMPLATE:EYEBROW[^\]]*|USE_TISSUE_TEMPLATE:EYELASH[^\]]*|TISSUE_LAYER:BY_CATEGORY:(?:FINGER|TOE|HAIR|HEAD|EYELID)[^\]]*|RELSIZE:BY_CATEGORY:LIVER[^\]]*)\]\r?\n",
            "",
            text,
        )
        # Rewrite heart/throat artery TL block for this anatomy (wiki SELECT_TISSUE_LAYER / TL_*).
        tl_block = derive_tissue_layer_overrides(spec)
        text = re.sub(
            r"\t\[SELECT_TISSUE_LAYER:HEART:BY_CATEGORY:HEART\]\r?\n"
            r"(?:\t ?\[PLUS_TISSUE_LAYER:[^\]]+\]\r?\n)?"
            r"\t\t\[TL_MAJOR_ARTERIES\]\r?\n",
            (tl_block + "\n") if tl_block else "",
            text,
            count=1,
        )
        text = _strip_humanoid_tl_cosmetics(text)
        text = _append_plant_surface_colors(text, spec)
    else:
        text = _replace_token_line(text, "BODY", f"\t[{_body_line(frags)}]")
        detail_plans = list(spec.get("detail_plans") or [])

    # BODY_SIZE adult entry (third BODY_SIZE line pattern year 12)
    text = re.sub(
        r"\[BODY_SIZE:12:0:\d+\]",
        f"[BODY_SIZE:12:0:{adult_size}]",
        text,
        count=1,
    )

    # Flags
    text = _set_flag(text, "INTELLIGENT", bool(spec.get("intelligent", True)))
    # EQUIPS is not a creature tag in DF — equipment comes from entity; keep CANOPENDOORS
    text = _set_flag(text, "CANOPENDOORS", bool(spec.get("can_open_doors", True)))

    # Detail plans: replace the first contiguous BODY_DETAIL_PLAN block
    if detail_plans:
        plan_block = "\n".join(f"\t[BODY_DETAIL_PLAN:{p}]" for p in detail_plans)
        m = re.search(
            r"(\t\[BODY_DETAIL_PLAN:[^\]]+\]\r?\n(?:\t\[BODY_DETAIL_PLAN:[^\]]+\]\r?\n)*)",
            text,
        )
        if m:
            text = text[: m.start()] + plan_block + "\n" + text[m.end() :]
        if is_custom_body(spec):
            # Remove any remaining BODY_DETAIL_PLAN lines from the dwarf skeleton.
            allowed = {p.split(":")[0].upper() for p in detail_plans}
            def _keep_plan(match: re.Match) -> str:
                name = match.group(1).split(":")[0].upper()
                return match.group(0) if name in allowed else ""

            text = re.sub(
                r"\t\[BODY_DETAIL_PLAN:([^\]]+)\]\r?\n",
                _keep_plan,
                text,
            )

    # Replace attack section (wiki ATTACK / SPECIALATTACK tokens).
    attacks = _derive_attacks(spec)
    m_att = re.search(r"\t\[ATTACK:", text)
    if m_att and attacks:
        m_child = re.search(
            r"\t\[(?:CHILDNAME|BABYNAME|GENERAL_BABY_NAME|GENERAL_CHILD_NAME)",
            text[m_att.start() :],
        )
        if m_child:
            end = m_att.start() + m_child.start()
            text = text[: m_att.start()] + attacks + "\n\n" + text[end:]
        else:
            # Strip through last attack-ish block before next blank+non-attack section
            m_end = re.search(r"\n\t\[(?!ATTACK)", text[m_att.start() :])
            if m_end:
                end = m_att.start() + m_end.start() + 1
                text = text[: m_att.start()] + attacks + "\n" + text[end:]

    # Bodygloss
    for gloss in spec.get("bodygloss") or []:
        if isinstance(gloss, (list, tuple)) and len(gloss) >= 2:
            text += f"\n\t[BODYGLOSS:{gloss[0]}:{gloss[1]}]"
        elif isinstance(gloss, str) and gloss.strip():
            text += f"\n\t[BODYGLOSS:{gloss.strip()}]"

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"creature_{cid.lower()}.txt"
    # Ensure OBJECT header
    if "[OBJECT:CREATURE]" not in text:
        text = "[OBJECT:CREATURE]\n\n" + text
    out_path.write_text(text, encoding="latin-1", errors="replace")
    return out_path
