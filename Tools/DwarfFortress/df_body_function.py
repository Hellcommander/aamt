#!/usr/bin/env python3
"""
Tag body-graph parts with functional roles.

Heuristic game-design labels derived from documented DF body flags/categories —
not hidden engine rules.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

# category / flag -> function tags
_CATEGORY_TAGS = {
    "BRAIN": ("vital", "sensory"),
    "HEART": ("vital",),
    "LUNG": ("vital",),
    "GUTS": ("vital",),
    "LIVER": ("vital",),
    "STOMACH": ("vital",),
    "SPLEEN": ("vital",),
    "KIDNEY": ("vital",),
    "PANCREAS": ("vital",),
    "SPINE": ("vital", "defense"),
    "SKULL": ("defense", "armor_candidate"),
    "RIBCAGE": ("defense", "armor_candidate"),
    "HEAD": ("sensory",),
    "EYE": ("sensory",),
    "EAR": ("sensory",),
    "NOSE": ("sensory",),
    "HAND": ("manipulation", "offense"),
    "FINGER": ("manipulation",),
    "FOOT": ("locomotion",),
    "LEG_UPPER": ("locomotion",),
    "LEG_LOWER": ("locomotion",),
    "LEG_FRONT": ("locomotion",),
    "LEG_REAR": ("locomotion",),
    "ARM_UPPER": ("manipulation", "offense"),
    "ARM_LOWER": ("manipulation", "offense"),
    "WING": ("locomotion",),
    "TAIL": ("offense", "locomotion"),
    "HORN": ("offense",),
    "TUSK": ("offense",),
    "TOOTH": ("offense",),
    "MOUTH": ("offense",),
    "SHELL": ("defense", "armor_candidate"),
    "CHITIN": ("defense", "armor_candidate"),
}

_FLAG_TAGS = {
    "THOUGHT": ("vital", "sensory"),
    "GRASP": ("manipulation",),
    "STANCE": ("locomotion",),
    "FLIER": ("locomotion",),
    "SIGHT": ("sensory",),
    "HEARING": ("sensory",),
    "SMELL": ("sensory",),
    "LIMB": ("locomotion",),
}


def tag_part(node: Dict[str, Any]) -> List[str]:
    tags: set[str] = set()
    cat = (node.get("category") or "").upper()
    if cat in _CATEGORY_TAGS:
        tags.update(_CATEGORY_TAGS[cat])
    for fl in node.get("flags") or []:
        fu = str(fl).upper()
        if fu in _FLAG_TAGS:
            tags.update(_FLAG_TAGS[fu])
    if "INTERNAL" in {str(f).upper() for f in (node.get("flags") or [])} and "vital" not in tags:
        if cat in ("BRAIN", "HEART", "LUNG", "GUTS", "LIVER", "STOMACH", "SPLEEN", "KIDNEY"):
            tags.add("vital")
    return sorted(tags)


def annotate_nodes(nodes: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for n in nodes:
        nn = dict(n)
        nn["function_tags"] = tag_part(n)
        out.append(nn)
    return out


def summarize_functions(nodes: Sequence[Dict[str, Any]]) -> Dict[str, List[str]]:
    summary: Dict[str, List[str]] = {}
    for n in nodes:
        for t in n.get("function_tags") or tag_part(n):
            summary.setdefault(t, []).append(str(n.get("id") or "?"))
    return summary
