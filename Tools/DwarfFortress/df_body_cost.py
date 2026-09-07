#!/usr/bin/env python3
"""
Heuristic biological / gameplay cost model for DF body plans.

Uses the composed body graph (flags, categories, relsizes) — not hidden DF rules.
Scores are 0-100 game-design axes for modders.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from df_body_balance import balance_notes, pick_role
from df_body_evolution import analyze_evolution
from df_body_function import annotate_nodes, summarize_functions
from df_body_parser import BodyCatalog, BodyGraph, compose_body, load_body_catalog
from df_body_raw_writer import compose_spec_body

AXES = (
    "complexity",
    "energy",
    "vulnerability",
    "specialization",
    "offense",
    "defense",
    "mobility",
    "utility",
)


def _clamp(n: float, lo: float = 0.0, hi: float = 100.0) -> int:
    return int(max(lo, min(hi, round(n))))


def _layout_warnings(nodes: Sequence[Dict[str, Any]], flags: Dict[str, List[str]], spec: Dict[str, Any]) -> List[Dict[str, str]]:
    warnings: List[Dict[str, str]] = []
    by_id = {str(n.get("id")): n for n in nodes}
    flagset = {k.upper(): v for k, v in flags.items()}

    # THOUGHT should be INTERNAL
    for pid in flagset.get("THOUGHT") or []:
        n = by_id.get(pid) or {}
        fl = {str(f).upper() for f in (n.get("flags") or [])}
        if "INTERNAL" not in fl:
            warnings.append(
                {
                    "code": "THOUGHT_EXPOSED",
                    "severity": "warning",
                    "message": f"THOUGHT part {pid} is not INTERNAL (vanilla BRAIN is).",
                }
            )

    # HEART category INTERNAL and not LIMB
    for n in nodes:
        if (n.get("category") or "").upper() == "HEART":
            fl = {str(f).upper() for f in (n.get("flags") or [])}
            if "INTERNAL" not in fl:
                warnings.append(
                    {
                        "code": "HEART_EXPOSED",
                        "severity": "warning",
                        "message": f"HEART {n.get('id')} is not INTERNAL.",
                    }
                )
            if "LIMB" in fl:
                warnings.append(
                    {
                        "code": "HEART_ON_LIMB",
                        "severity": "warning",
                        "message": f"HEART {n.get('id')} is on a LIMB — vitals should cluster on torso.",
                    }
                )

    # SIGHT on/near HEAD
    for pid in flagset.get("SIGHT") or []:
        n = by_id.get(pid) or {}
        cat = (n.get("category") or "").upper()
        fl = {str(f).upper() for f in (n.get("flags") or [])}
        if "HEAD" not in fl and cat not in ("EYE", "HEAD"):
            # check parent via con
            parent = n.get("con")
            pn = by_id.get(parent) if parent else None
            pfl = {str(f).upper() for f in ((pn or {}).get("flags") or [])}
            pcat = ((pn or {}).get("category") or "").upper()
            if "HEAD" not in pfl and pcat != "HEAD":
                warnings.append(
                    {
                        "code": "SIGHT_NOT_ON_HEAD",
                        "severity": "warning",
                        "message": f"SIGHT part {pid} is not on/under HEAD.",
                    }
                )

    has_stance = bool(flagset.get("STANCE"))
    has_flier = bool(flagset.get("FLIER"))
    if not has_stance and not has_flier:
        warnings.append(
            {
                "code": "NO_WEIGHT_BEARING",
                "severity": "warning",
                "message": "No STANCE and no FLIER — no weight-bearing locomotion.",
            }
        )

    grasp = set(flagset.get("GRASP") or [])
    stance = set(flagset.get("STANCE") or [])
    if grasp and stance and grasp == stance:
        preset = str(spec.get("preset") or "")
        if preset != "quadruped_grasp":
            warnings.append(
                {
                    "code": "GRASP_ONLY_STANCE",
                    "severity": "info",
                    "message": "GRASP parts are the only STANCE parts (manipulation = support tradeoff).",
                }
            )

    # Attacks on SMALL only
    offense_parts = []
    for n in nodes:
        fl = {str(f).upper() for f in (n.get("flags") or [])}
        cat = (n.get("category") or "").upper()
        if "GRASP" in fl or cat in ("TOOTH", "HORN", "TUSK", "TAIL", "HAND"):
            offense_parts.append(n)
    if offense_parts and all("SMALL" in {str(f).upper() for f in (n.get("flags") or [])} for n in offense_parts):
        warnings.append(
            {
                "code": "OFFENSE_ALL_SMALL",
                "severity": "info",
                "message": "All offense-capable parts are SMALL — fragile weapon appendages.",
            }
        )

    return warnings


def _score_axes(graph: BodyGraph, spec: Dict[str, Any], annotated: List[Dict[str, Any]]) -> Dict[str, int]:
    nodes = annotated
    n = max(1, len(nodes))
    cats = {(x.get("category") or "") for x in nodes if x.get("category")}
    flags = graph.flags_present
    limbs = len(flags.get("LIMB") or [])
    grasp = len(flags.get("GRASP") or [])
    stance = len(flags.get("STANCE") or [])
    flier = 1 if flags.get("FLIER") else 0
    thought = 1 if flags.get("THOUGHT") else 0
    sight = len(flags.get("SIGHT") or [])
    internal = sum(1 for x in nodes if "INTERNAL" in {str(f).upper() for f in (x.get("flags") or [])})
    small = sum(1 for x in nodes if "SMALL" in {str(f).upper() for f in (x.get("flags") or [])})
    total_rel = sum(int(x.get("default_relsize") or 0) for x in nodes) or 1
    exposed_vital = 0
    for x in nodes:
        tags = set(x.get("function_tags") or [])
        fl = {str(f).upper() for f in (x.get("flags") or [])}
        if "vital" in tags and "INTERNAL" not in fl:
            exposed_vital += 1

    body_size = 0
    for key in ("body_size_adult", "body_size"):
        if spec.get(key):
            try:
                body_size = int(spec[key])
            except (TypeError, ValueError):
                body_size = 0
            break

    complexity = 20 + n * 1.2 + len(cats) * 2.5 + limbs * 1.5
    energy = 15 + limbs * 4 + flier * 25 + (body_size / 5000.0) + grasp * 3 + sight * 2
    vulnerability = 10 + exposed_vital * 18 + small * 1.5 - internal * 1.2
    specialization = 10 + flier * 20 + (15 if grasp and thought else 0) + (10 if "2WINGS" in {str(f).upper() for f in (spec.get("body_fragments") or [])} else 0)
    offense = 10 + grasp * 12 + sum(8 for x in nodes if (x.get("category") or "").upper() in ("TOOTH", "HORN", "TUSK", "TAIL"))
    defense = 10 + internal * 2 + sum(6 for x in nodes if (x.get("category") or "").upper() in ("SKULL", "RIBCAGE", "SHELL"))
    mobility = 10 + stance * 10 + flier * 30 + limbs * 3
    utility = 5 + grasp * 15 + thought * 25 + (20 if spec.get("intelligent") else 0) + (15 if spec.get("equips") else 0) + (10 if spec.get("site_controllable") else 0)

    # Soft size influence
    if total_rel > 8000:
        energy += 10
        defense += 5
        mobility -= 5

    return {k: _clamp(v) for k, v in {
        "complexity": complexity,
        "energy": energy,
        "vulnerability": max(0, vulnerability),
        "specialization": specialization,
        "offense": offense,
        "defense": defense,
        "mobility": mobility,
        "utility": utility,
    }.items()}


def _part_costs(annotated: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for n in annotated:
        rel = int(n.get("default_relsize") or 50)
        tags = n.get("function_tags") or []
        cost = rel / 20.0
        notes: List[str] = []
        if "vital" in tags:
            cost += 8
            notes.append("vital")
        if "locomotion" in tags:
            cost += 4
        if "manipulation" in tags:
            cost += 5
        if "offense" in tags:
            cost += 3
        if "INTERNAL" not in {str(f).upper() for f in (n.get("flags") or [])} and "vital" in tags:
            cost += 6
            notes.append("exposed vital")
        out.append(
            {
                "id": n.get("id"),
                "category": n.get("category"),
                "relsize": rel,
                "cost": _clamp(cost, 0, 100),
                "function_tags": tags,
                "notes": ", ".join(notes) if notes else "",
            }
        )
    out.sort(key=lambda x: -int(x["cost"]))
    return out


def analyze_costs(
    spec: Dict[str, Any],
    catalog: Optional[BodyCatalog] = None,
    *,
    full: bool = True,
) -> Dict[str, Any]:
    """
    Return a JSON-serializable CostReport.

    Heuristic model — not DF engine biology.
    """
    cat = catalog or load_body_catalog()
    graph = compose_spec_body(spec)
    annotated = annotate_nodes(graph.nodes)
    axes = _score_axes(graph, spec, annotated)
    site = bool(spec.get("site_controllable"))
    flier = bool(graph.flags_present.get("FLIER"))
    role = pick_role(axes, site=site, flier=flier)
    layout = _layout_warnings(annotated, graph.flags_present, spec)
    part_costs = _part_costs(annotated)

    report: Dict[str, Any] = {
        "model": "aamt_heuristic_v1",
        "notes": "Game-design cost axes from body graph flags/categories — not hidden DF rules.",
        "axes": axes,
        "role": role,
        "part_costs": part_costs[:40],
        "warnings": layout,
        "functions": summarize_functions(annotated),
        "node_count": len(annotated),
        "fragment_count": len(graph.fragments),
    }

    if full:
        evo = analyze_evolution(spec)
        bal = balance_notes(axes, role)
        report["evolution"] = evo
        report["balance"] = bal
        report["placement"] = layout
        # Merge evolution warnings into warnings list (dedupe by code+message)
        for w in evo.get("warnings") or []:
            report["warnings"].append(w)

    return report


def save_cost_report(spec: Dict[str, Any], out_path: Path, catalog: Optional[BodyCatalog] = None) -> Path:
    import json

    report = analyze_costs(spec, catalog, full=True)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return out_path
