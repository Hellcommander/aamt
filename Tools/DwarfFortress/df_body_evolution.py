#!/usr/bin/env python3
"""
Evolutionary reuse / plausibility hints for body fragment lists.

Heuristic fantasy-evolution model: prefers incremental fragment reuse from
vanilla BODY tokens. Does not invent new BODY tokens.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

# fragment -> expected prerequisite fragments (any of)
_REQUIRES_ANY: Dict[str, Sequence[str]] = {
    "5FINGERS": ("HUMANOID_NECK", "HUMANOID", "BASIC_3PARTARMS", "HUMANOID_NECK_FLIER"),
    "4FINGERS": ("HUMANOID_NECK", "HUMANOID", "BASIC_3PARTARMS"),
    "5TOES": ("HUMANOID_NECK", "HUMANOID", "BASIC_3PARTLEGS", "HUMANOID_NECK_FLIER"),
    "2WINGS": ("HUMANOID_NECK", "HUMANOID", "BASIC_2PARTBODY", "BASIC_1PARTBODY"),
    "FACIAL_FEATURES": ("HUMANOID_NECK", "HUMANOID", "BASIC_HEAD"),
    "TEETH": ("MOUTH", "HUMANOID_NECK", "HUMANOID", "BASIC_HEAD"),
    "BRAIN": ("HUMANOID_NECK", "HUMANOID", "BASIC_HEAD", "BASIC_1PARTBODY_THOUGHT"),
    "SKULL": ("BRAIN", "HUMANOID_NECK", "HUMANOID", "BASIC_HEAD"),
}

# Mutually awkward mixes (warning, not error)
_MIX_WARNINGS: Sequence[tuple[Sequence[str], Sequence[str], str]] = (
    (("HUMANOID", "HUMANOID_NECK"), ("INSECT", "SPIDER", "ANT", "BEETLE"), "Insectoid + humanoid mix is an evolutionary jump"),
    (("HUMANOID", "HUMANOID_NECK"), ("SNAKE", "WORM", "SERPENT"), "Serpentine + humanoid mix is an evolutionary jump"),
)


def _frag_set(frags: Sequence[str]) -> set[str]:
    return {str(f).upper() for f in frags}


def _has_any(frags: set[str], options: Sequence[str]) -> bool:
    for o in options:
        ou = o.upper()
        if ou in frags:
            return True
        if any(f.startswith(ou) for f in frags):
            return True
    return False


def analyze_evolution(spec: Dict[str, Any]) -> Dict[str, Any]:
    frags = list(spec.get("body_fragments") or [])
    fset = _frag_set(frags)
    warnings: List[Dict[str, str]] = []
    suggestions: List[str] = []

    for frag, reqs in _REQUIRES_ANY.items():
        if frag in fset and not _has_any(fset, reqs):
            warnings.append(
                {
                    "code": "EVO_PREREQ",
                    "severity": "warning",
                    "message": f"{frag} usually reuses structure from {', '.join(reqs)}",
                    "suggestion": f"Add one of: {', '.join(reqs)}",
                }
            )
            suggestions.append(reqs[0])

    for group_a, group_b, msg in _MIX_WARNINGS:
        if _has_any(fset, group_a) and _has_any(fset, group_b):
            warnings.append(
                {
                    "code": "EVO_JUMP",
                    "severity": "warning",
                    "message": msg,
                    "suggestion": "Prefer a single body lineage, or accept as deliberate chimera fantasy.",
                }
            )

    if "2WINGS" in fset:
        suggestions.append("Document wings as modified upper limbs / flier kit")

    # Incremental path blurb
    path: List[str] = []
    if _has_any(fset, ("HUMANOID_NECK", "HUMANOID")):
        path.append("vertebrate humanoid core")
        if "2WINGS" in fset:
            path.append("forelimb -> wing specialization")
        if "5FINGERS" in fset:
            path.append("digit differentiation on grasp hands")
    elif _has_any(fset, ("QUADRUPED",)):
        path.append("quadruped stance core")
        if _has_any(fset, ("QUADRUPED_NECK_FRONT_GRASP",)) or "BASIC_3PARTARMS" in fset:
            path.append("front limb grasp specialization")

    return {
        "warnings": warnings,
        "suggested_fragments": sorted(set(suggestions)),
        "evolutionary_path": path,
        "notes": "Heuristic fantasy-evolution model; not DF engine rules.",
    }
