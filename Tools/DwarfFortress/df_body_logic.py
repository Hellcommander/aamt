#!/usr/bin/env python3
"""Validate composed body + creature spec; apply auto-fixes."""

from __future__ import annotations

import copy
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from df_body_parser import BodyCatalog, compose_body, load_body_catalog
from df_body_raw_writer import compose_spec_body, is_custom_body

VERTEBRATE_ORGANS = ["HEART", "GUTS", "ORGANS", "SPINE", "BRAIN", "SKULL"]


@dataclass
class Issue:
    code: str
    message: str
    severity: str = "error"  # error | warning | info
    fix: Optional[str] = None


@dataclass
class ValidationResult:
    ok: bool
    issues: List[Issue] = field(default_factory=list)
    flags_present: Dict[str, List[str]] = field(default_factory=dict)
    graph_warnings: List[str] = field(default_factory=list)
    cost: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "ok": self.ok,
            "issues": [
                {
                    "code": i.code,
                    "message": i.message,
                    "severity": i.severity,
                    "fix": i.fix,
                }
                for i in self.issues
            ],
            "flags_present": self.flags_present,
            "graph_warnings": self.graph_warnings,
        }
        if self.cost is not None:
            payload["cost"] = self.cost
        return payload


def _has_fragment(frags: Sequence[str], name: str) -> bool:
    return any(f.upper() == name.upper() for f in frags)


def _ensure_fragment(frags: List[str], name: str, after: Optional[str] = None) -> bool:
    if _has_fragment(frags, name):
        return False
    if after:
        for i, f in enumerate(frags):
            if f.upper() == after.upper():
                frags.insert(i + 1, name)
                return True
    frags.append(name)
    return True


def validate(
    spec: Dict[str, Any],
    catalog: Optional[BodyCatalog] = None,
) -> ValidationResult:
    cat = catalog or load_body_catalog()
    frags = list(spec.get("body_fragments") or [])
    graph = compose_spec_body(spec)
    issues: List[Issue] = []
    flags = graph.flags_present

    for w in graph.warnings:
        code = "GRAPH"
        if "Duplicate" in w:
            code = "DUP_BP"
        elif "Dangling" in w:
            code = "DANGLING_CON"
        elif "Unknown" in w:
            code = "UNKNOWN_FRAGMENT"
        elif "Dropped unknown BP flag" in w:
            code = "UNKNOWN_BP_FLAG"
        issues.append(
            Issue(
                code,
                w,
                "warning" if code in ("GRAPH", "UNKNOWN_BP_FLAG") else "error",
            )
        )

    if is_custom_body(spec):
        cb = spec.get("custom_body") or {}
        if not cb.get("parts"):
            issues.append(Issue("CUSTOM_EMPTY", "custom_body has no parts", "error"))
        if not cb.get("layers"):
            issues.append(Issue("CUSTOM_NO_LAYERS", "custom_body missing BP_LAYERS rows", "error"))
        if not cb.get("relsizes"):
            issues.append(Issue("CUSTOM_NO_RELSIZES", "custom_body missing BP_RELSIZE rows", "warning"))
        try:
            from df_tissue import known_layer_tissues

            extras: set = set()
            for row in cb.get("add_tissues") or []:
                args = [str(x) for x in row]
                if args and args[0].upper() == "ADD_TISSUE" and len(args) >= 2:
                    extras.add(args[1].upper())
                elif args:
                    extras.add(args[0].upper())
            allowed = known_layer_tissues(extras)
            for row in cb.get("layers") or []:
                args = [str(x).upper() for x in row]
                if not args:
                    continue
                if args[0] in ("BP_LAYERS", "BP_LAYERS_OVER", "BP_LAYERS_UNDER"):
                    i = 3
                elif args[0] in ("BY_CATEGORY", "BY_TYPE", "BY_TOKEN"):
                    i = 2
                else:
                    continue
                while i + 1 < len(args):
                    tissue, pct = args[i], args[i + 1]
                    if tissue.startswith("ARG") and tissue[3:].isdigit():
                        i += 2
                        continue
                    if not pct.isdigit():
                        i += 1
                        continue
                    if tissue not in allowed:
                        issues.append(
                            Issue(
                                "UNKNOWN_TISSUE",
                                f"BP_LAYERS references unknown tissue '{tissue}'",
                                "warning",
                            )
                        )
                    i += 2
        except Exception:
            pass

    intelligent = bool(spec.get("intelligent"))
    equips = bool(spec.get("equips"))
    site = bool(spec.get("site_controllable"))
    can_doors = bool(spec.get("can_open_doors"))

    has_grasp = bool(flags.get("GRASP"))
    has_thought = bool(flags.get("THOUGHT"))
    has_stance = bool(flags.get("STANCE"))
    has_flier = bool(flags.get("FLIER")) or _has_fragment(frags, "2WINGS")

    needs_grasp = site or equips
    if needs_grasp and not has_grasp:
        issues.append(
            Issue(
                "NO_GRASP",
                "Site-controllable/equips creature lacks GRASP parts",
                "error",
                fix="add_grasp_fragment",
            )
        )
    elif intelligent and not has_grasp:
        issues.append(
            Issue(
                "NO_GRASP",
                "Intelligent creature has no GRASP parts (cannot pick up items)",
                "warning",
                fix="add_grasp_fragment",
            )
        )

    if not has_thought:
        issues.append(
            Issue(
                "NO_THOUGHT",
                "No THOUGHT body part (brain); creature cannot think",
                "error",
                fix="add_BRAIN",
            )
        )

    joined = " ".join(frags).upper()
    cats = " ".join(str(n.get("category") or "") for n in graph.nodes).upper()
    has_alt_loco = has_flier or any(
        x in joined for x in ("FIN", "FLIPPER", "BASIC_1PARTBODY", "TENTACLE")
    ) or any(x in cats for x in ("VINE", "TRUNK", "ROOTPAD", "TENTACLE"))
    if not has_stance and not has_alt_loco:
        issues.append(
            Issue(
                "NO_STANCE",
                "Walker has no STANCE parts and is not a flier/swimmer/crawler",
                "error" if site else "warning",
                fix="ensure_legs",
            )
        )

    # 5FINGERS without HAND category / GRASP
    if _has_fragment(frags, "5FINGERS") and not has_grasp:
        issues.append(
            Issue(
                "FINGERS_NO_HAND",
                "5FINGERS present but no GRASP/HAND parent",
                "error",
                fix="add_arms_before_fingers",
            )
        )

    # Vertebrate organs
    vertebrate_like = any(
        _has_fragment(frags, x)
        for x in ("HUMANOID", "HUMANOID_NECK", "QUADRUPED", "QUADRUPED_NECK", "QUADRUPED_NECK_FRONT_GRASP")
    ) or any(f.upper().startswith("HUMANOID") or f.upper().startswith("QUADRUPED") for f in frags)
    if vertebrate_like:
        missing = [o for o in VERTEBRATE_ORGANS if not _has_fragment(frags, o)]
        if missing:
            issues.append(
                Issue(
                    "MISSING_ORGANS",
                    f"Vertebrate organs missing: {', '.join(missing)}",
                    "warning",
                    fix="add_vertebrate_organs",
                )
            )

    if site:
        if not (intelligent and equips and can_doors):
            issues.append(
                Issue(
                    "SITE_FLAGS",
                    "SITE_CONTROLLABLE needs INTELLIGENT + EQUIPS + CANOPENDOORS",
                    "error",
                    fix="enable_site_flags",
                )
            )

    profile = (spec.get("graphics_profile") or "humanoid").lower()
    humanoidish = any(
        f.upper().startswith("HUMANOID") or f.upper() in ("BASIC_3PARTARMS",)
        for f in frags
    )
    if profile == "humanoid" and not humanoidish and not has_grasp:
        issues.append(
            Issue(
                "GRAPHICS_MISMATCH",
                "graphics_profile=humanoid but body is not humanoid-like",
                "warning",
                fix="set_graphics_simple_or_add_humanoid",
            )
        )
    if profile == "simple" and humanoidish and site:
        issues.append(
            Issue(
                "GRAPHICS_MISMATCH",
                "Playable humanoid civ with graphics_profile=simple may look wrong",
                "info",
                fix="set_graphics_humanoid",
            )
        )

    # Cost scores are informational — they do not flip ok by themselves.
    cost_report: Optional[Dict[str, Any]] = None
    try:
        from df_body_cost import analyze_costs

        cost_report = analyze_costs(spec, cat, full=True)
        for w in cost_report.get("warnings") or []:
            if isinstance(w, dict) and w.get("code") in (
                "THOUGHT_EXPOSED",
                "HEART_EXPOSED",
                "HEART_ON_LIMB",
                "NO_WEIGHT_BEARING",
            ):
                issues.append(
                    Issue(
                        str(w.get("code") or "COST"),
                        str(w.get("message") or ""),
                        str(w.get("severity") or "warning"),
                    )
                )
    except Exception:
        cost_report = None

    errors = [i for i in issues if i.severity == "error"]
    return ValidationResult(
        ok=len(errors) == 0,
        issues=issues,
        flags_present=flags,
        graph_warnings=list(graph.warnings),
        cost=cost_report,
    )


def apply_fixes(spec: Dict[str, Any], catalog: Optional[BodyCatalog] = None) -> Dict[str, Any]:
    """Return a new spec with auto-fixes applied for known validation issues."""
    cat = catalog or load_body_catalog()
    out = copy.deepcopy(spec)
    if is_custom_body(out):
        result = validate(out, cat)
        codes = {i.code for i in result.issues}
        if "SITE_FLAGS" in codes or out.get("site_controllable"):
            out["intelligent"] = True
            out["equips"] = True
            out["can_open_doors"] = True
        if "GRAPHICS_MISMATCH" in codes:
            out["graphics_profile"] = "simple"
        return out

    frags: List[str] = list(out.get("body_fragments") or [])
    result = validate(out, cat)
    codes = {i.code for i in result.issues}

    joined_fix = " ".join(frags).upper()
    keep_plan = any(
        x in joined_fix
        for x in (
            "INSECT",
            "SPIDER",
            "BASIC_1PARTBODY",
            "TENTACLE",
            "SIDE_FINS",
            "ARMLESS",
            "CENTAUR",
        )
    )

    if "NO_GRASP" in codes or "FINGERS_NO_HAND" in codes:
        if "INSECT" in joined_fix and "PINCER" not in joined_fix:
            _ensure_fragment(frags, "UPPERBODY_PINCERS")
        elif not keep_plan and not any(f.upper().startswith("HUMANOID") for f in frags):
            if not any(f.upper().startswith("QUADRUPED") and "GRASP" in f.upper() for f in frags):
                _ensure_fragment(frags, "BASIC_3PARTARMS", after=None)
                if "BASIC_3PARTARMS" in frags:
                    frags.remove("BASIC_3PARTARMS")
                    frags.insert(0, "BASIC_3PARTARMS")

    has_thought_already = bool(compose_body(frags, cat).flags_present.get("THOUGHT"))
    if "NO_THOUGHT" in codes and not has_thought_already:
        if "BASIC_1PARTBODY" in joined_fix:
            _ensure_fragment(frags, "BASIC_1PARTBODY_THOUGHT")
        else:
            _ensure_fragment(frags, "BRAIN")

    if "NO_STANCE" in codes and not keep_plan:
        if not any(f.upper().startswith("HUMANOID") for f in frags):
            _ensure_fragment(frags, "BASIC_3PARTLEGS")
        out["body_fragments"] = frags
        g2 = compose_body(frags, cat)
        if not g2.flags_present.get("STANCE") and not g2.flags_present.get("FLIER"):
            _ensure_fragment(frags, "BASIC_3PARTLEGS")

    vertebrate_like_fix = any(
        f.upper().startswith("HUMANOID") or f.upper().startswith("QUADRUPED") for f in frags
    )
    if vertebrate_like_fix and ("MISSING_ORGANS" in codes or "NO_THOUGHT" in codes):
        for org in VERTEBRATE_ORGANS:
            _ensure_fragment(frags, org)
    # Sapient layout kit: vanilla HEART / BRAIN fragments only (never invent BPs)
    if out.get("site_controllable") or out.get("intelligent"):
        g3 = compose_body(frags, cat)
        if not g3.flags_present.get("THOUGHT") and not _has_fragment(frags, "BRAIN"):
            if "BASIC_1PARTBODY" in " ".join(frags).upper():
                _ensure_fragment(frags, "BASIC_1PARTBODY_THOUGHT")
            else:
                _ensure_fragment(frags, "BRAIN")
        if not _has_fragment(frags, "HEART") and vertebrate_like_fix:
            _ensure_fragment(frags, "HEART")

    if "SITE_FLAGS" in codes or out.get("site_controllable"):
        out["intelligent"] = True
        out["equips"] = True
        out["can_open_doors"] = True

    if "GRAPHICS_MISMATCH" in codes:
        g = compose_body(frags, cat)
        humanoidish = any(f.upper().startswith("HUMANOID") for f in frags)
        if out.get("graphics_profile") == "humanoid" and not humanoidish and not g.flags_present.get("GRASP"):
            out["graphics_profile"] = "simple"
        elif out.get("site_controllable") and humanoidish:
            out["graphics_profile"] = "humanoid"

    # Deduplicate fragments preserving order
    seen = set()
    deduped: List[str] = []
    for f in frags:
        key = f.upper()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(f)
    out["body_fragments"] = deduped
    return out
