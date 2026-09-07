#!/usr/bin/env python3
"""Write custom [BODY:] and [BODY_DETAIL_PLAN:] objects from creature.json custom_body.

Uses only documented DF body / body-detail-plan tokens (archived wiki):
BP, CATEGORY, CON, CON_CAT, CONTYPE, DEFAULT_RELSIZE, NUMBER, INDIVIDUAL_NAME,
and BP flags; detail plans: BP_LAYERS[_OVER|_UNDER], BP_POSITION, BP_RELATION,
BP_RELSIZE, ADD_MATERIAL, ADD_TISSUE.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from df_body_parser import (
    BP_FLAGS,
    BP_POSITION_VALUES,
    BP_RELATION_VALUES,
    CONTYPE_VALUES,
    DETAIL_PLAN_ROW_KINDS,
    BodyGraph,
    compose_body,
    load_body_catalog,
)
from df_tissue import (
    AAMT_PLANT_SURFACE_TEMPLATE,
    known_layer_tissues,
    plant_surface_template_raw,
)

# Wiki / vanilla tissue ids usable in BP_LAYERS (never invent names).
KNOWN_TISSUES = known_layer_tissues()

SELECTOR_KINDS = frozenset({"BY_CATEGORY", "BY_TYPE", "BY_TOKEN"})


def is_custom_body(spec: Dict[str, Any]) -> bool:
    return (spec.get("body_mode") or "").lower() == "custom" and bool(spec.get("custom_body"))


def custom_object_id(spec: Dict[str, Any]) -> str:
    cb = spec.get("custom_body") or {}
    oid = str(cb.get("object_id") or "").strip().upper()
    if oid:
        return oid
    return f"AAMT_{str(spec.get('id') or 'CREATURE').upper()}"


def sanitize_part_flags(flags: Sequence[str]) -> List[str]:
    out: List[str] = []
    for f in flags or []:
        u = str(f).upper()
        if u in BP_FLAGS and u not in out:
            out.append(u)
    return out


def sanitize_contype(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    u = str(value).upper()
    return u if u in CONTYPE_VALUES else None


def compose_custom_body(spec: Dict[str, Any]) -> BodyGraph:
    """Build a BodyGraph from custom_body.parts (no vanilla fragments required)."""
    cb = spec.get("custom_body") or {}
    parts = list(cb.get("parts") or [])
    oid = custom_object_id(spec)
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, str]] = []
    flags_present: Dict[str, List[str]] = {}
    warnings: List[str] = []
    seen_ids: set[str] = set()
    categories: set[str] = set()

    for raw in parts:
        if not isinstance(raw, dict):
            warnings.append("Ignoring non-object custom body part")
            continue
        pid = str(raw.get("id") or "").strip().upper()
        if not pid:
            warnings.append("Custom body part missing id")
            continue
        if pid in seen_ids:
            warnings.append(f"Duplicate BP id '{pid}' in custom body")
        seen_ids.add(pid)
        flags = sanitize_part_flags(raw.get("flags") or [])
        dropped = {str(f).upper() for f in (raw.get("flags") or [])} - set(flags)
        for d in sorted(dropped):
            warnings.append(f"Dropped unknown BP flag '{d}' on {pid}")

        contype_raw = raw.get("contype")
        contype = sanitize_contype(contype_raw)
        if contype_raw and not contype:
            warnings.append(
                f"Dropped invalid CONTYPE '{contype_raw}' on {pid} "
                f"(allowed: {', '.join(sorted(CONTYPE_VALUES))})"
            )

        category = str(raw["category"]).upper() if raw.get("category") else None
        if category:
            categories.add(category)

        number = None
        if raw.get("number") is not None:
            try:
                number = max(1, min(32, int(raw["number"])))  # wiki: capped at 32
            except (TypeError, ValueError):
                warnings.append(f"Invalid NUMBER on {pid}; ignored")

        node = {
            "id": pid,
            "name": str(raw.get("name") or pid.lower()),
            "plural": str(raw.get("plural") or "STP"),
            "flags": flags,
            "category": category,
            "default_relsize": int(raw["relsize"]) if raw.get("relsize") is not None else None,
            "fragment": oid,
            "con": (str(raw["con"]).upper() if raw.get("con") else None),
            "contype": contype,
            "con_cat": (str(raw["con_cat"]).upper() if raw.get("con_cat") else None),
            "number": number,
            "individual_name": raw.get("individual_name"),
            "individual_plural": raw.get("individual_plural"),
        }
        nodes.append(node)
        for fl in flags:
            flags_present.setdefault(fl, []).append(pid)
        if node["con"]:
            edges.append({"from": pid, "to": node["con"], "type": "CON"})
        if node["contype"]:
            edges.append({"from": pid, "to": node["contype"], "type": "CONTYPE"})
        if node["con_cat"]:
            edges.append({"from": pid, "to": node["con_cat"], "type": "CON_CAT"})

    ids = {n["id"] for n in nodes}
    for e in edges:
        if e["type"] == "CON" and e["to"] not in ids:
            warnings.append(f"Dangling CON: {e['from']} -> {e['to']}")
        if e["type"] == "CON_CAT" and e["to"] not in categories:
            warnings.append(f"CON_CAT target category '{e['to']}' not present on any part ({e['from']})")

    return BodyGraph(
        fragments=[oid],
        nodes=nodes,
        edges=edges,
        flags_present=flags_present,
        warnings=warnings,
    )


def compose_spec_body(spec: Dict[str, Any]) -> BodyGraph:
    if is_custom_body(spec):
        return compose_custom_body(spec)
    return compose_body(list(spec.get("body_fragments") or []), load_body_catalog())


def _format_token(args: Sequence[str]) -> str:
    return "[" + ":".join(str(a) for a in args) + "]"


def _write_bp_block(part: Dict[str, Any]) -> List[str]:
    pid = str(part["id"]).upper()
    name = str(part.get("name") or pid.lower())
    plural = str(part.get("plural") or "STP")
    lines = [f"\t[BP:{pid}:{name}:{plural}]"]
    tags: List[str] = []
    for fl in sanitize_part_flags(part.get("flags") or []):
        tags.append(fl)
    if part.get("con"):
        tags.append(f"CON:{str(part['con']).upper()}")
    contype = sanitize_contype(part.get("contype"))
    if contype:
        tags.append(f"CONTYPE:{contype}")
    if part.get("con_cat"):
        tags.append(f"CON_CAT:{str(part['con_cat']).upper()}")
    if part.get("category"):
        tags.append(f"CATEGORY:{str(part['category']).upper()}")
    if tags:
        lines[0] = lines[0] + "".join(f"[{t}]" for t in tags)

    number = part.get("number")
    if number is not None:
        try:
            n = max(1, min(32, int(number)))
            lines.append(f"\t\t[NUMBER:{n}]")
        except (TypeError, ValueError):
            pass
    ind = part.get("individual_name")
    if ind:
        ind_pl = part.get("individual_plural") or ind
        lines.append(f"\t\t[INDIVIDUAL_NAME:{ind}:{ind_pl}]")

    rel = part.get("relsize")
    if rel is None:
        rel = part.get("default_relsize")
    if rel is not None:
        lines.append(f"\t\t[DEFAULT_RELSIZE:{int(rel)}]")
    return lines


def _extra_tissues_from_cb(cb: Dict[str, Any]) -> set:
    """Tissue ids introduced via ADD_TISSUE rows in custom_body."""
    extra: set = set()
    for row in cb.get("add_tissues") or []:
        args = [str(x) for x in row]
        if not args:
            continue
        if args[0].upper() == "ADD_TISSUE" and len(args) >= 2:
            extra.add(args[1].upper())
        elif len(args) >= 1:
            extra.add(args[0].upper())
    return extra


def _sanitize_layer_row(
    row: Sequence[str],
    *,
    allowed: Optional[frozenset] = None,
) -> Optional[List[str]]:
    """Sanitize BP_LAYERS / BP_LAYERS_OVER / BP_LAYERS_UNDER rows."""
    allowed = allowed or KNOWN_TISSUES
    if not row:
        return None
    args = [str(x) for x in row]
    kind = args[0].upper()
    if kind not in ("BP_LAYERS", "BP_LAYERS_OVER", "BP_LAYERS_UNDER"):
        # Assume bare tissue list meant as BP_LAYERS
        if kind in SELECTOR_KINDS:
            args = ["BP_LAYERS"] + args
            kind = "BP_LAYERS"
        else:
            return None
    if len(args) < 2:
        return None
    sel = args[1].upper()
    if sel not in SELECTOR_KINDS:
        sel = "BY_CATEGORY"
        # shift: treat args[1] as category
        args = [kind, "BY_CATEGORY"] + args[1:]
    out = [kind, sel]
    if len(args) > 2:
        out.append(args[2].upper())
    i = 3
    while i < len(args):
        tissue = args[i].upper()
        # ARG1..ARG5 are legal variable tissue slots in detail plans
        if tissue.startswith("ARG") and tissue[3:].isdigit() and 1 <= int(tissue[3:]) <= 5:
            out.append(tissue)
            if i + 1 < len(args):
                out.append(args[i + 1])
                i += 2
                continue
        pct = args[i + 1] if i + 1 < len(args) else "100"
        if tissue in allowed:
            out.append(tissue)
            out.append(pct)
            i += 2
            continue
        i += 1
    if len(out) < 4:
        return None
    return out


def _sanitize_position_row(row: Sequence[str]) -> Optional[List[str]]:
    args = [str(x) for x in row]
    if not args:
        return None
    if args[0].upper() != "BP_POSITION":
        args = ["BP_POSITION"] + args
    if len(args) < 4:
        return None
    sel = args[1].upper()
    if sel not in SELECTOR_KINDS:
        return None
    pos = args[3].upper()
    if pos not in BP_POSITION_VALUES:
        return None
    return ["BP_POSITION", sel, args[2].upper(), pos]


def _sanitize_relation_row(row: Sequence[str]) -> Optional[List[str]]:
    # BP_RELATION:BY_CATEGORY:part:RELATION:BY_CATEGORY:parent:coverage
    args = [str(x) for x in row]
    if not args:
        return None
    if args[0].upper() != "BP_RELATION":
        args = ["BP_RELATION"] + args
    if len(args) < 7:
        return None
    sel1, part, rel, sel2, parent, cov = (
        args[1].upper(),
        args[2].upper(),
        args[3].upper(),
        args[4].upper(),
        args[5].upper(),
        args[6],
    )
    if sel1 not in SELECTOR_KINDS or sel2 not in SELECTOR_KINDS:
        return None
    if rel not in BP_RELATION_VALUES:
        return None
    return ["BP_RELATION", sel1, part, rel, sel2, parent, str(cov)]


def _sanitize_relsize_row(row: Sequence[str]) -> Optional[List[str]]:
    args = [str(x) for x in row]
    if not args:
        return None
    if args[0].upper() != "BP_RELSIZE":
        args = ["BP_RELSIZE"] + args
    if len(args) < 4:
        return None
    sel = args[1].upper()
    if sel not in SELECTOR_KINDS:
        return None
    return ["BP_RELSIZE", sel, args[2].upper(), str(args[3])]


def _sanitize_add_row(row: Sequence[str]) -> Optional[List[str]]:
    """ADD_MATERIAL / ADD_TISSUE: identifier + template."""
    args = [str(x) for x in row]
    if len(args) < 3:
        return None
    kind = args[0].upper()
    if kind not in ("ADD_MATERIAL", "ADD_TISSUE"):
        return None
    return [kind, args[1].upper(), args[2].upper()]


def write_custom_body_raws(spec: Dict[str, Any], out_dir: Path) -> List[Path]:
    """Emit body_*.txt and b_detail_plan_*.txt for a custom_body spec."""
    if not is_custom_body(spec):
        return []
    cb = spec["custom_body"]
    oid = custom_object_id(spec)
    cid = str(spec.get("id") or "creature").lower()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []

    body_lines = [
        "body_aamt_custom",
        "",
        "[OBJECT:BODY]",
        "",
        f"[BODY:{oid}]",
    ]
    for part in cb.get("parts") or []:
        body_lines.extend(_write_bp_block(part))
    body_path = out_dir / f"body_{cid}.txt"
    body_path.write_text("\n".join(body_lines) + "\n", encoding="latin-1", errors="replace")
    written.append(body_path)

    layer_name = str(cb.get("layer_plan") or f"{oid}_LAYERS")
    rel_name = str(cb.get("relsize_plan") or f"{oid}_RELSIZES")
    pos_name = str(cb.get("position_plan") or f"{oid}_POSITIONS")
    allowed = known_layer_tissues(_extra_tissues_from_cb(cb))

    plan_lines = [
        "b_detail_plan_aamt_custom",
        "",
        "[OBJECT:BODY_DETAIL_PLAN]",
        "",
        f"[BODY_DETAIL_PLAN:{layer_name}]",
    ]
    needs_plant_template = False
    for row in cb.get("add_materials") or []:
        cleaned = _sanitize_add_row(["ADD_MATERIAL"] + list(row) if row and str(row[0]).upper() != "ADD_MATERIAL" else row)
        if cleaned:
            plan_lines.append("\t" + _format_token(cleaned))
    for row in cb.get("add_tissues") or []:
        cleaned = _sanitize_add_row(["ADD_TISSUE"] + list(row) if row and str(row[0]).upper() != "ADD_TISSUE" else row)
        if cleaned:
            plan_lines.append("\t" + _format_token(cleaned))
            if cleaned[2] == AAMT_PLANT_SURFACE_TEMPLATE:
                needs_plant_template = True
    for row in cb.get("layers") or []:
        cleaned = _sanitize_layer_row(row, allowed=allowed)
        if cleaned:
            plan_lines.append("\t" + _format_token(cleaned))

    plan_lines += ["", f"[BODY_DETAIL_PLAN:{rel_name}]"]
    for row in cb.get("relsizes") or []:
        cleaned = _sanitize_relsize_row(row)
        if cleaned:
            plan_lines.append("\t" + _format_token(cleaned))

    plan_lines += ["", f"[BODY_DETAIL_PLAN:{pos_name}]"]
    for row in cb.get("positions") or []:
        kind = str(row[0]).upper() if row else ""
        if kind == "BP_RELATION" or (len(row) >= 6 and str(row[2]).upper() in BP_RELATION_VALUES):
            cleaned = _sanitize_relation_row(row)
        else:
            cleaned = _sanitize_position_row(row)
        if cleaned:
            plan_lines.append("\t" + _format_token(cleaned))

    plan_path = out_dir / f"b_detail_plan_{cid}.txt"
    plan_path.write_text("\n".join(plan_lines) + "\n", encoding="latin-1", errors="replace")
    written.append(plan_path)

    if needs_plant_template or cb.get("emit_plant_surface_template"):
        tissue_path = out_dir / "tissue_template_aamt.txt"
        tissue_path.write_text(plant_surface_template_raw(), encoding="latin-1", errors="replace")
        written.append(tissue_path)

    return written


def custom_detail_plans_for_spec(spec: Dict[str, Any]) -> List[str]:
    cb = spec.get("custom_body") or {}
    oid = custom_object_id(spec)
    return [
        "STANDARD_MATERIALS",
        "STANDARD_TISSUES",
        str(cb.get("layer_plan") or f"{oid}_LAYERS"),
        str(cb.get("relsize_plan") or f"{oid}_RELSIZES"),
        str(cb.get("position_plan") or f"{oid}_POSITIONS"),
    ]
