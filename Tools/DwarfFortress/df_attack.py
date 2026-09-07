#!/usr/bin/env python3
"""Attack part selectors + ATTACK_* / SPECIALATTACK tokens (DF wiki).

Part selectors (all documented; base game uses all except TISSUE_LAYER often):
  BODYPART / TISSUE_LAYER / CHILD_BODYPART_GROUP / CHILD_TISSUE_LAYER_GROUP
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Set

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from df_body_raw_writer import compose_spec_body

ATTACK_PART_SELECTORS = frozenset(
    {
        "BODYPART",
        "TISSUE_LAYER",
        "CHILD_BODYPART_GROUP",
        "CHILD_TISSUE_LAYER_GROUP",
    }
)

SELECTOR_KINDS = frozenset({"BY_TYPE", "BY_TOKEN", "BY_CATEGORY"})

ATTACK_PRIORITIES = frozenset({"MAIN", "SECOND"})

ATTACK_SUBTOKENS = frozenset(
    {
        "ATTACK_SKILL",
        "ATTACK_VERB",
        "ATTACK_CONTACT_PERC",
        "ATTACK_PENETRATION_PERC",
        "ATTACK_PRIORITY",
        "ATTACK_VELOCITY_MODIFIER",
        "ATTACK_FLAG_CANLATCH",
        "ATTACK_FLAG_WITH",
        "ATTACK_FLAG_EDGE",
        "ATTACK_PREPARE_AND_RECOVER",
        "ATTACK_FLAG_BAD_MULTIATTACK",
        "ATTACK_FLAG_INDEPENDENT_MULTIATTACK",
        "SPECIALATTACK_INJECT_EXTRACT",
        "SPECIALATTACK_INTERACTION",
        "SPECIALATTACK_SUCK_BLOOD",
    }
)

# Common skill tokens used by vanilla attack variations.
ATTACK_SKILLS = frozenset(
    {
        "GRASP_STRIKE",
        "STANCE_STRIKE",
        "BITE",
    }
)


def _categories(graph) -> Set[str]:
    out: Set[str] = set()
    for n in graph.nodes:
        c = n.get("category")
        if c:
            out.add(str(c).upper())
    return out


def _fmt(args: Sequence[str]) -> str:
    return "[" + ":".join(str(a) for a in args) + "]"


def _attack_block(header: Sequence[str], body: Sequence[Sequence[str]]) -> List[str]:
    lines = [f"\t{_fmt(header)}"]
    for row in body:
        lines.append(f"\t\t{_fmt(row)}")
    return lines


def derive_attack_lines(spec: Dict[str, Any]) -> List[str]:
    """Build ATTACK raw lines from anatomy flags / custom categories (wiki tokens only)."""
    graph = compose_spec_body(spec)
    flags = graph.flags_present
    frags = {f.upper() for f in (spec.get("body_fragments") or [])}
    cats = _categories(graph)
    lines: List[str] = []

    if flags.get("GRASP"):
        lines += _attack_block(
            ["ATTACK", "PUNCH", "BODYPART", "BY_TYPE", "GRASP"],
            [
                ["ATTACK_SKILL", "GRASP_STRIKE"],
                ["ATTACK_VERB", "punch", "punches"],
                ["ATTACK_CONTACT_PERC", "100"],
                ["ATTACK_PREPARE_AND_RECOVER", "3", "3"],
                ["ATTACK_FLAG_WITH"],
                ["ATTACK_PRIORITY", "MAIN"],
            ],
        )
        if any(x in frags for x in ("5FINGERS", "4FINGERS", "3FINGERS")):
            # Wiki CHILD_TISSUE_LAYER_GROUP: parent grasp → child finger → NAIL tissue.
            lines += _attack_block(
                [
                    "ATTACK",
                    "SCRATCH",
                    "CHILD_TISSUE_LAYER_GROUP",
                    "BY_TYPE",
                    "GRASP",
                    "BY_CATEGORY",
                    "FINGER",
                    "NAIL",
                ],
                [
                    ["ATTACK_SKILL", "GRASP_STRIKE"],
                    ["ATTACK_VERB", "scratch", "scratches"],
                    ["ATTACK_CONTACT_PERC", "100"],
                    ["ATTACK_PENETRATION_PERC", "100"],
                    ["ATTACK_FLAG_EDGE"],
                    ["ATTACK_PREPARE_AND_RECOVER", "3", "3"],
                    ["ATTACK_PRIORITY", "SECOND"],
                ],
            )

    if flags.get("STANCE"):
        lines += _attack_block(
            ["ATTACK", "KICK", "BODYPART", "BY_TYPE", "STANCE"],
            [
                ["ATTACK_SKILL", "STANCE_STRIKE"],
                ["ATTACK_VERB", "kick", "kicks"],
                ["ATTACK_CONTACT_PERC", "100"],
                ["ATTACK_PREPARE_AND_RECOVER", "4", "4"],
                ["ATTACK_FLAG_WITH"],
                ["ATTACK_PRIORITY", "SECOND"],
                ["ATTACK_FLAG_BAD_MULTIATTACK"],
            ],
        )

    if "PROBOSCIS" in cats:
        # Vanilla PROBOSCIS_SUCK_ATTACK.
        lines += _attack_block(
            ["ATTACK", "BITE", "BODYPART", "BY_CATEGORY", "PROBOSCIS"],
            [
                ["ATTACK_SKILL", "BITE"],
                ["ATTACK_VERB", "bite", "bites"],
                ["ATTACK_CONTACT_PERC", "100"],
                ["ATTACK_FLAG_EDGE"],
                ["ATTACK_PREPARE_AND_RECOVER", "3", "3"],
                ["ATTACK_PRIORITY", "MAIN"],
                ["ATTACK_FLAG_CANLATCH"],
                ["SPECIALATTACK_SUCK_BLOOD", "25", "50"],
            ],
        )

    if any("BEAK" in f or "BILL" in f for f in frags) or "BEAK" in cats:
        lines += _attack_block(
            ["ATTACK", "BITE", "BODYPART", "BY_CATEGORY", "BEAK"],
            [
                ["ATTACK_SKILL", "BITE"],
                ["ATTACK_VERB", "bite", "bites"],
                ["ATTACK_CONTACT_PERC", "100"],
                ["ATTACK_PENETRATION_PERC", "100"],
                ["ATTACK_FLAG_EDGE"],
                ["ATTACK_PREPARE_AND_RECOVER", "3", "3"],
                ["ATTACK_PRIORITY", "MAIN"],
                ["ATTACK_FLAG_CANLATCH"],
            ],
        )
    elif "TEETH" in frags or "GENERIC_TEETH" in frags or any("TEETH" in f for f in frags) or "TOOTH" in cats:
        # Prefer HEAD parent (vanilla); fall back to MOUTH when headless maws.
        parent = "HEAD" if ("HEAD" in cats or flags.get("HEAD")) else "MOUTH"
        lines += _attack_block(
            [
                "ATTACK",
                "BITE",
                "CHILD_BODYPART_GROUP",
                "BY_CATEGORY",
                parent,
                "BY_CATEGORY",
                "TOOTH",
            ],
            [
                ["ATTACK_SKILL", "BITE"],
                ["ATTACK_VERB", "bite", "bites"],
                ["ATTACK_CONTACT_PERC", "100"],
                ["ATTACK_PENETRATION_PERC", "100"],
                ["ATTACK_FLAG_EDGE"],
                ["ATTACK_PREPARE_AND_RECOVER", "3", "3"],
                ["ATTACK_PRIORITY", "MAIN" if "PROBOSCIS" not in cats else "SECOND"],
                ["ATTACK_FLAG_CANLATCH"],
            ],
        )
    elif "PROBOSCIS" not in cats and (flags.get("HEAD") or "MOUTH" in frags or "MOUTH" in cats):
        lines += _attack_block(
            ["ATTACK", "BITE", "BODYPART", "BY_CATEGORY", "MOUTH"],
            [
                ["ATTACK_SKILL", "BITE"],
                ["ATTACK_VERB", "bite", "bites"],
                ["ATTACK_CONTACT_PERC", "100"],
                ["ATTACK_PREPARE_AND_RECOVER", "3", "3"],
                ["ATTACK_PRIORITY", "SECOND"],
                ["ATTACK_FLAG_CANLATCH"],
            ],
        )

    if any("HORN" in f or "ANTLER" in f for f in frags) or "HORN" in cats:
        lines += _attack_block(
            ["ATTACK", "GORE", "BODYPART", "BY_CATEGORY", "HORN"],
            [
                ["ATTACK_SKILL", "BITE"],
                ["ATTACK_VERB", "gore", "gores"],
                ["ATTACK_CONTACT_PERC", "100"],
                ["ATTACK_PREPARE_AND_RECOVER", "3", "3"],
                ["ATTACK_FLAG_WITH"],
                ["ATTACK_PRIORITY", "MAIN"],
            ],
        )

    # Thorn / stinger: prefer TISSUE_LAYER when NAIL layer is present (wiki selector).
    if "THORN" in cats:
        lines += _attack_block(
            ["ATTACK", "STING", "TISSUE_LAYER", "BY_CATEGORY", "THORN", "NAIL"],
            [
                ["ATTACK_SKILL", "STANCE_STRIKE"],
                ["ATTACK_VERB", "sting", "stings"],
                ["ATTACK_CONTACT_PERC", "5"],
                ["ATTACK_PENETRATION_PERC", "100"],
                ["ATTACK_FLAG_EDGE"],
                ["ATTACK_PREPARE_AND_RECOVER", "4", "4"],
                ["ATTACK_PRIORITY", "SECOND"],
                ["ATTACK_FLAG_WITH"],
            ],
        )
    elif "STINGER" in cats:
        # Vanilla TAIL_STING pattern (BODYPART).
        lines += _attack_block(
            ["ATTACK", "STING", "BODYPART", "BY_CATEGORY", "STINGER"],
            [
                ["ATTACK_SKILL", "STANCE_STRIKE"],
                ["ATTACK_VERB", "sting", "stings"],
                ["ATTACK_CONTACT_PERC", "5"],
                ["ATTACK_PENETRATION_PERC", "100"],
                ["ATTACK_FLAG_EDGE"],
                ["ATTACK_PREPARE_AND_RECOVER", "4", "4"],
                ["ATTACK_PRIORITY", "SECOND"],
            ],
        )

    return lines


def derive_attacks(spec: Dict[str, Any]) -> str:
    return "\n".join(derive_attack_lines(spec))


def derive_tissue_layer_overrides(spec: Dict[str, Any]) -> str:
    """Creature-level SELECT_TISSUE_LAYER / TL_* (wiki tissue layer tokens)."""
    graph = compose_spec_body(spec)
    flags = graph.flags_present
    cats = _categories(graph)
    lines: List[str] = []

    if "HEART" in cats:
        lines.append("\t[SELECT_TISSUE_LAYER:HEART:BY_CATEGORY:HEART]")
        if "THROAT" in cats or flags.get("THROAT"):
            lines.append("\t [PLUS_TISSUE_LAYER:SKIN:BY_CATEGORY:THROAT]")
        lines.append("\t\t[TL_MAJOR_ARTERIES]")

    return "\n".join(lines)
