#!/usr/bin/env python3
"""
Gameplay balance notes from cost axes.

Compares offense vs defense vs energy etc. Heuristic role labeling only.
"""

from __future__ import annotations

from typing import Any, Dict, List


def pick_role(axes: Dict[str, int], *, site: bool, flier: bool) -> str:
    off = axes.get("offense", 0)
    de = axes.get("defense", 0)
    mob = axes.get("mobility", 0)
    util = axes.get("utility", 0)
    energy = axes.get("energy", 0)
    vuln = axes.get("vulnerability", 0)

    if site and util >= 55 and off <= 70:
        return "sapient_civ"
    if flier and mob >= 60 and de < 55:
        return "flyer_skirmisher"
    if off >= 65 and de <= 40 and vuln >= 50:
        return "glass_cannon"
    if de >= 60 and mob <= 45:
        return "fortress_guardian"
    if off >= 55 and mob >= 55 and util < 50:
        return "ambush_predator"
    if energy >= 75 and util < 40:
        return "unbalanced"
    if abs(off - de) >= 35 and energy >= 60:
        return "unbalanced"
    if site:
        return "sapient_civ"
    return "ambush_predator" if off > de else "fortress_guardian"


def balance_notes(axes: Dict[str, int], role: str) -> List[Dict[str, str]]:
    notes: List[Dict[str, str]] = []
    off = axes.get("offense", 0)
    de = axes.get("defense", 0)
    energy = axes.get("energy", 0)
    util = axes.get("utility", 0)
    mob = axes.get("mobility", 0)
    vuln = axes.get("vulnerability", 0)

    if off >= de + 25:
        notes.append(
            {
                "code": "OFFENSE_OVER_DEFENSE",
                "severity": "info",
                "message": f"Offense ({off}) far exceeds defense ({de}) -> glass-cannon leaning.",
            }
        )
    if de >= off + 25:
        notes.append(
            {
                "code": "DEFENSE_OVER_OFFENSE",
                "severity": "info",
                "message": f"Defense ({de}) far exceeds offense ({off}) -> guardian leaning.",
            }
        )
    if energy >= 70 and util < 45:
        notes.append(
            {
                "code": "ENERGY_WITHOUT_UTILITY",
                "severity": "warning",
                "message": "High metabolic/energy cost without matching utility (grasp/sapience/tools).",
            }
        )
    if vuln >= 65 and de < 40:
        notes.append(
            {
                "code": "EXPOSED_VITALS",
                "severity": "warning",
                "message": "High vulnerability with low defense — exposed vitals or fragile sensors.",
            }
        )
    if mob >= 70 and energy < 40:
        notes.append(
            {
                "code": "MOBILITY_CHEAP",
                "severity": "info",
                "message": "High mobility at modest energy — efficient locomotion layout.",
            }
        )
    notes.append(
        {
            "code": "ROLE",
            "severity": "info",
            "message": f"Suggested gameplay role: {role}",
        }
    )
    return notes
