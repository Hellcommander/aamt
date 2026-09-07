#!/usr/bin/env python3
"""Parse vanilla DF body and body-detail-plan RAWs into a composable catalog."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from df_paths import templates_dir, vanilla_bodies
from df_raw_parser import split_object_blocks, tokenize_text

BP_FLAGS = frozenset(
    {
        "GRASP",
        "STANCE",
        "THOUGHT",
        "HEAD",
        "UPPERBODY",
        "LOWERBODY",
        "LIMB",
        "LEFT",
        "RIGHT",
        "SIGHT",
        "EMBEDDED",
        "SMALL",
        "FLIER",
        "HEAR",
        "SMELL",
        "BREATHE",
        "UNDER_PRESSURE",
        "INTERNAL",
        "CIRCULATION",
        "GUTS",
        "JOINT",
        "SKELETON",
        "TOTEMABLE",
        "APERTURE",
        "DIGIT",
        "MOUTH",
        # Documented on the archived DF wiki body-token page:
        "THROAT",
        "NERVOUS",
        "CONNECTOR",
        "PREVENTS_PARENT_COLLAPSE",
        "GELDABLE",
        "SOCKET",
        "VERMIN_BUTCHER_ITEM",
    }
)

# CONTYPE only accepts these type tokens (wiki).
CONTYPE_VALUES = frozenset({"UPPERBODY", "LOWERBODY", "HEAD", "GRASP", "STANCE"})

# BP_POSITION tokens (wiki). SIDES is unverified — omit from whitelist.
BP_POSITION_VALUES = frozenset({"FRONT", "BACK", "LEFT", "RIGHT", "TOP", "BOTTOM"})

# BP_RELATION tokens (wiki).
BP_RELATION_VALUES = frozenset(
    {
        "AROUND",
        "SURROUNDED_BY",
        "ABOVE",
        "BELOW",
        "IN_FRONT",
        "BEHIND",
        "CLEANS",
        "CLEANED_BY",
    }
)

DETAIL_PLAN_ROW_KINDS = frozenset(
    {
        "BP_LAYERS",
        "BP_LAYERS_OVER",
        "BP_LAYERS_UNDER",
        "BP_POSITION",
        "BP_RELATION",
        "BP_RELSIZE",
        "ADD_MATERIAL",
        "ADD_TISSUE",
    }
)


@dataclass
class BodyPart:
    id: str
    name: str
    plural: str
    flags: List[str] = field(default_factory=list)
    category: Optional[str] = None
    default_relsize: Optional[int] = None
    con: Optional[str] = None  # parent BP id
    contype: Optional[str] = None
    con_cat: Optional[str] = None
    number: Optional[int] = None
    individual_name: Optional[str] = None
    individual_plural: Optional[str] = None


@dataclass
class BodyFragment:
    name: str
    parts: List[BodyPart] = field(default_factory=list)


@dataclass
class DetailPlan:
    name: str
    tokens: List[List[str]] = field(default_factory=list)  # raw arg rows after header


@dataclass
class BodyGraph:
    """Composed graph of body parts from multiple fragments."""

    fragments: List[str]
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, str]]
    flags_present: Dict[str, List[str]]  # flag → part ids
    warnings: List[str] = field(default_factory=list)


class BodyCatalog:
    def __init__(self) -> None:
        self.bodies: Dict[str, BodyFragment] = {}
        self.detail_plans: Dict[str, DetailPlan] = {}
        self.source_files: List[str] = []

    def to_json_dict(self) -> Dict[str, Any]:
        return {
            "bodies": {
                name: {
                    "name": frag.name,
                    "parts": [asdict(p) for p in frag.parts],
                }
                for name, frag in sorted(self.bodies.items())
            },
            "detail_plans": sorted(self.detail_plans.keys()),
            "source_files": self.source_files,
            "bp_flags": sorted(BP_FLAGS),
        }


def _parse_body_block(tokens: List[tuple]) -> BodyFragment:
    """Parse tokens starting with BODY header."""
    if not tokens or tokens[0][0].upper() != "BODY" or not tokens[0][1]:
        raise ValueError("Not a BODY block")
    name = tokens[0][1][0]
    parts: List[BodyPart] = []
    current: Optional[BodyPart] = None

    def flush() -> None:
        nonlocal current
        if current is not None:
            parts.append(current)
            current = None

    for tok, args in tokens[1:]:
        t = tok.upper()
        if t == "BP" and len(args) >= 2:
            flush()
            plural = args[2] if len(args) > 2 else args[1]
            current = BodyPart(id=args[0], name=args[1], plural=plural)
        elif current is None:
            continue
        elif t in BP_FLAGS:
            if t not in current.flags:
                current.flags.append(t)
        elif t == "CATEGORY" and args:
            current.category = args[0]
        elif t == "DEFAULT_RELSIZE" and args:
            try:
                current.default_relsize = int(args[0])
            except ValueError:
                current.default_relsize = None
        elif t == "CON" and args:
            current.con = args[0]
        elif t == "CONTYPE" and args:
            current.contype = args[0]
        elif t == "CON_CAT" and args:
            current.con_cat = args[0]
        elif t == "NUMBER" and args:
            try:
                current.number = int(args[0])
            except ValueError:
                current.number = None
        elif t == "INDIVIDUAL_NAME" and len(args) >= 1:
            current.individual_name = args[0]
            current.individual_plural = args[1] if len(args) > 1 else args[0]
        # Other body-part tokens ignored for catalog
    flush()
    return BodyFragment(name=name, parts=parts)


def load_body_catalog(df_root: Optional[Path] = None) -> BodyCatalog:
    catalog = BodyCatalog()
    bodies_dir = vanilla_bodies(df_root)
    files = [
        bodies_dir / "body_default.txt",
        bodies_dir / "b_detail_plan_default.txt",
    ]
    for path in files:
        if not path.is_file():
            continue
        catalog.source_files.append(str(path))
        text = path.read_text(encoding="latin-1", errors="replace")
        if path.name.startswith("body"):
            for block in split_object_blocks(text, object_kinds=("BODY",)):
                frag = _parse_body_block(block.tokens)
                catalog.bodies[frag.name] = frag
        else:
            for block in split_object_blocks(text, object_kinds=("BODY_DETAIL_PLAN",)):
                rows = [args for tok, args in block.tokens[1:]]
                catalog.detail_plans[block.id] = DetailPlan(name=block.id, tokens=rows)
    return catalog


def compose_body(
    fragment_names: Sequence[str],
    catalog: Optional[BodyCatalog] = None,
) -> BodyGraph:
    """Merge BODY fragments into a part graph (nodes + CON edges)."""
    cat = catalog or load_body_catalog()
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, str]] = []
    flags_present: Dict[str, List[str]] = {}
    warnings: List[str] = []
    seen_ids: Set[str] = set()

    for fname in fragment_names:
        frag = cat.bodies.get(fname)
        if frag is None:
            warnings.append(f"Unknown body fragment: {fname}")
            continue
        for part in frag.parts:
            if part.id in seen_ids:
                warnings.append(f"Duplicate BP id '{part.id}' from fragment {fname}")
            seen_ids.add(part.id)
            node = {
                "id": part.id,
                "name": part.name,
                "plural": part.plural,
                "flags": list(part.flags),
                "category": part.category,
                "default_relsize": part.default_relsize,
                "fragment": fname,
                "con": part.con,
                "contype": part.contype,
                "con_cat": part.con_cat,
            }
            nodes.append(node)
            for fl in part.flags:
                flags_present.setdefault(fl, []).append(part.id)
            if part.con:
                edges.append({"from": part.id, "to": part.con, "type": "CON"})
            if part.contype:
                edges.append({"from": part.id, "to": part.contype, "type": "CONTYPE"})
            if part.con_cat:
                edges.append({"from": part.id, "to": part.con_cat, "type": "CON_CAT"})

    # Dangling CON targets
    ids = {n["id"] for n in nodes}
    for e in edges:
        if e["type"] == "CON" and e["to"] not in ids:
            warnings.append(f"Dangling CON: {e['from']} -> {e['to']}")

    return BodyGraph(
        fragments=list(fragment_names),
        nodes=nodes,
        edges=edges,
        flags_present=flags_present,
        warnings=warnings,
    )


def export_catalog_json(path: Optional[Path] = None, catalog: Optional[BodyCatalog] = None) -> Path:
    cat = catalog or load_body_catalog()
    out = path or (templates_dir() / "body_catalog.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cat.to_json_dict(), indent=2), encoding="utf-8")
    return out


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Export DF body catalog JSON")
    ap.add_argument("-o", "--output", type=Path, default=None)
    args = ap.parse_args()
    out = export_catalog_json(args.output)
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
