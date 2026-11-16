"""Scan vanilla Caves of Qud and every enabled mod for mutations and anatomies.

Writes, for the Choose Your Fighter layered tiles (qud_fighter_tile_generator.py
--layered, Arendeth_CYFTiles):

  CYFTemplates/content_map.json  anatomy -> body plan for every anatomy found
                                 (vanilla and mods), and mutation -> layers
  CYFTemplates/coverage.md       which mutation shows on which layer, and which
                                 ones have no picture

The generator reads content_map.json so a fighter's Fighters.xml lists modded
anatomies under the right plan. Anatomies you want on another plan go into the
"manual" block of content_map.json ({"AnatomyName": "plan"}); a rescan keeps it.

Usage:
  python cyf_scan_content.py
  python cyf_scan_content.py --userdata "C:/Users/<you>/AppData/LocalLow/Freehold Games/CavesOfQud"
      --workshop "D:/games/Steam/steamapps/workshop/content/333640"
      --game "D:/games/Steam/steamapps/common/Caves of Qud"
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import qud_fighter_tile_generator as gen  # noqa: E402

DEFAULT_USERDATA = Path(os.environ.get("USERPROFILE", "")) / "AppData/LocalLow/Freehold Games/CavesOfQud"
DEFAULT_WORKSHOP = Path("D:/games/Steam/steamapps/workshop/content/333640")
DEFAULT_GAME = Path("D:/games/Steam/steamapps/common/Caves of Qud")
TEMPLATES = HERE / "CYFTemplates"


# ------------------------------------------------------------------ mods

def _mod_id(d: Path) -> Tuple[str, str]:
    p = d / "manifest.json"
    if p.is_file():
        try:
            m = json.loads(p.read_text(encoding="utf-8-sig"))
            mid = m.get("ID") or m.get("id")
            if mid:
                return str(mid), str(m.get("Title") or m.get("title") or d.name)
        except (ValueError, OSError):
            pass
    return d.name, d.name


def enabled_mods(userdata: Path, workshop: Path) -> List[Tuple[str, str, Path]]:
    """(id, title, folder) for every mod the game would load; local copies shadow Workshop."""
    try:
        settings = json.loads((userdata / "ModSettings.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        settings = {}
    mods: List[Tuple[str, str, Path]] = []
    seen = set()
    for root in (userdata / "Mods", workshop):
        if not root.is_dir():
            continue
        for d in sorted(root.iterdir()):
            if not d.is_dir():
                continue
            mid, title = _mod_id(d)
            ent = settings.get(mid) or settings.get(d.name)
            if isinstance(ent, dict) and ent.get("Enabled") is False:
                continue
            if mid in seen:
                continue
            seen.add(mid)
            mods.append((mid, title, d))
    return mods


# ------------------------------------------------------------------ XML

def _tag(el: ET.Element) -> str:
    return el.tag.split("}")[-1].lower()


def _read_xml(path: Path) -> Optional[ET.Element]:
    try:
        raw = path.read_bytes().decode("utf-8-sig", "replace")
        start = raw.find("<")
        return ET.fromstring(raw[start:] if start >= 0 else raw)
    except (ET.ParseError, OSError, ValueError):
        return None


class Content:
    def __init__(self) -> None:
        self.mutations: Dict[str, Dict[str, Any]] = {}
        self.anatomies: Dict[str, Dict[str, Any]] = {}
        self.variant_of: Dict[str, str] = {}

    def scan(self, path: Path, source: str) -> None:
        root = _read_xml(path)
        if root is None:
            return
        tag = _tag(root)
        if tag == "mutations":
            for cat in root.iter():
                if _tag(cat) != "category":
                    continue
                for m in cat:
                    if _tag(m) != "mutation":
                        continue
                    cls = m.get("Class")
                    if not cls or (m.get("Load") or "").lower() == "remove":
                        continue
                    self.mutations.setdefault(cls, {
                        "name": m.get("Name") or cls,
                        "category": cat.get("Name") or "",
                        "variants": m.get("Variants") or "",
                        "source": source,
                    })
        elif tag == "bodies":
            for el in root.iter():
                t = _tag(el)
                if t == "anatomy" and el.get("Name"):
                    parts = [p.get("Type") for p in el.iter() if _tag(p) == "part" and p.get("Type")]
                    a = self.anatomies.setdefault(el.get("Name"), {"source": source, "parts": parts})
                    if parts and not a["parts"]:
                        a["parts"] = parts
                elif t == "bodyparttypevariant" and el.get("Type") and el.get("VariantOf"):
                    self.variant_of.setdefault(el.get("Type"), el.get("VariantOf"))


# ------------------------------------------------------------------ limbs (mirrors CYFLayers.cs)

_PAIR_SLOT_WORDS = ("feet", "legs", "foot", "paws", "hoofs", "claws")
_NOT_ROOT_WORDS = ("mulch", "gravel", "stakes")


def base_type(name: str, variant_of: Dict[str, str]) -> str:
    seen = set()
    while name in variant_of and name not in seen:
        seen.add(name)
        name = variant_of[name]
    return name


def limb_counts(parts: List[str], variant_of: Dict[str, str]) -> Dict[str, int]:
    """Same limb classes the mod computes from BodyPart.Type / VariantType."""
    counts: Dict[str, int] = {}

    def add(k: str, n: int = 1) -> None:
        counts[k] = counts.get(k, 0) + n

    # Legs come two ways: foot parts with paired foot slots (humanoid "Feet",
    # quadruped "Foot" x4 + "Feet" x2) and leg parts with "Legs" slots (insects,
    # spiders); the same legs are counted by both members of a way, so each way
    # takes its larger count and the two ways add up (uplifted horse: two front
    # "Leg" + rear "Hoofs" = 4).
    feet = foot_pairs = legs_single = legs_pairs = 0
    for name in parts:
        b = base_type(name, variant_of).lower()
        n = name.lower()
        add(name)
        if (("head" in n and "header" not in n) or ("skull" in n and "face" not in n)):
            add("#head")
        if any(w in n for w in ("tentacle", "pseudopod", "oral arm", "cilium")):
            add("#tentacle")
            continue
        if "wing" in n:
            add("#wing")
            continue
        if b == "fin":
            add("#fin")
            continue
        if b == "roots":
            if not any(w in n for w in _NOT_ROOT_WORDS):
                add("#roots")
            continue
        if (b == "tail" and "foot" not in n) or "tail" in n:
            add("#tail")
            continue
        if b == "feet":
            if n.endswith("legs"):
                legs_pairs += 1
            elif any(w in n for w in _PAIR_SLOT_WORDS):
                foot_pairs += 1
            continue
        if b == "foot":
            feet += 1
            continue
        if "leg" in n and not n.endswith("legs"):
            legs_single += 1
            continue
        if (("arm" in n and "stump" not in n and "forearm" not in n and "armor" not in n)
                or (("palp" in n or "cheliped" in n) and b == "arm")):
            add("#arm")
    legs = max(feet, 2 * foot_pairs) + max(legs_single, 2 * legs_pairs)
    if legs:
        counts["#leg"] = legs
    return counts


_NAME_RULES: List[Tuple[str, Tuple[str, ...]]] = [
    ("tree", ("tree", "vine", "bush", "plant", "lattice", "trellis", "rootling")),
    ("flower", ("flower", "fractus", "blossom")),
    ("fungus", ("fungus", "mushy", "hypha", "mushroom", "smallproblems")),
    ("vessel", ("oven", "pottery", "airwell")),
    ("door", ("wall", "door", "mirror")),
    ("chair", ("chair",)),
    ("table", ("bed", "table", "chalkboard", "pillow")),
    ("radial", ("star", "octohedron")),
    ("blob", ("planula", "jelly", "ooze", "medusa", "mote", "moss", "sponge", "hampster", "mockette",
              "oddity", "nest", "clam")),
    ("robot", ("robot", "mech", "drone", "motorbike", "turret", "cube", "pyramid", "bot")),
    ("serpent", ("serpent", "snake", "worm", "slug", "snail", "dyofidi", "vermis", "sawtilus", "eel")),
    ("fish", ("fish", "porpoise")),
]


def plan_for(name: str, parts: List[str], variant_of: Dict[str, str]) -> Tuple[str, str]:
    """(plan, reason) for an anatomy the vanilla table does not list."""
    low = name.lower().replace("_", "").replace(" ", "")
    for plan, words in _NAME_RULES:
        for w in words:
            if w in low:
                return plan, f"name has '{w}'"
    c = limb_counts(parts, variant_of)
    legs = c.get("#leg", 0)
    if c.get("#roots"):
        return "tree", "roots"
    if legs >= 3:
        return "quadruped", f"{legs} legs"
    if c.get("#arm") or legs:
        return "biped", f"{c.get('#arm', 0)} arms, {legs} legs"
    if c.get("#fin"):
        return "fish", "fins"
    if c.get("#head") and c.get("#tail"):
        return "serpent", "head and tail"
    if c.get("Chassis") or c.get("Control Unit"):
        return "robot", "chassis"
    return "blob", "no limbs that pick a plan"


# ------------------------------------------------------------------ mutations

# Mutations that change the body itself: the tile follows them through the limb
# layers or the body plan, not through a mutation layer of their own.
_BODY_TOKENS = ("multipleleg", "multiplearm", "twohead", "multiplehead", "hydrahead", "armless",
                "animallegs", "serpentineform", "shapeshift", "metamorphosis", "robotarms",
                "extraarmature", "gigantism")
# Shown while their effect is on (the "phase" fade layer keys on the Phased effect).
_EFFECT_TOKENS = ("phasing",)


def mutation_shown_by(cls: str, info: Dict[str, Any]) -> str:
    blob = gen_normalize(cls + " " + info.get("name", "") + " " + info.get("variants", ""))
    if any(t in blob for t in _BODY_TOKENS):
        return "body"
    if any(t in blob for t in _EFFECT_TOKENS):
        return "effect"
    return ""


def mutation_layers(cls: str, info: Dict[str, Any]) -> List[str]:
    blob = gen_normalize(cls + " " + info.get("name", "") + " " + info.get("variants", ""))
    hits = []
    for d in gen._LAYER_DEFS:
        if any(tok in blob for tok in d.get("mutations", ())):
            hits.append(d["id"])
    return hits


def gen_normalize(s: str) -> str:
    return "".join(c for c in s.lower() if c.isascii() and c.isalnum())


# ------------------------------------------------------------------ main

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--userdata", type=Path, default=DEFAULT_USERDATA)
    ap.add_argument("--workshop", type=Path, default=DEFAULT_WORKSHOP)
    ap.add_argument("--game", type=Path, default=DEFAULT_GAME)
    ap.add_argument("--out", type=Path, default=TEMPLATES)
    args = ap.parse_args(argv)

    base = args.game / "CoQ_Data" / "StreamingAssets" / "Base"
    if not (base / "Bodies.xml").is_file():
        raise SystemExit(f"No Bodies.xml under {base}; pass --game")
    content = Content()
    for fn in ("Mutations.xml", "HiddenMutations.xml", "Bodies.xml"):
        content.scan(base / fn, "vanilla")
    mods = enabled_mods(args.userdata, args.workshop)
    for mid, _title, d in mods:
        for dp, dns, fns in os.walk(d):
            dns[:] = [x for x in dns if not x.startswith((".", "_"))]
            for fn in fns:
                if fn.lower().endswith(".xml"):
                    content.scan(Path(dp) / fn, mid)

    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    map_path = out / "content_map.json"
    manual: Dict[str, str] = {}
    if map_path.is_file():
        try:
            manual = dict(json.loads(map_path.read_text(encoding="utf-8")).get("manual") or {})
        except ValueError:
            manual = {}

    vanilla_plan = {a: p for p, names in gen.PLAN_ANATOMIES.items() for a in names}
    anatomy_plans: Dict[str, Dict[str, Any]] = {}
    for name, a in sorted(content.anatomies.items(), key=lambda kv: kv[0].lower()):
        if name in manual and manual[name] in gen.ALL_PLANS:
            plan, why = manual[name], "manual"
        elif name in vanilla_plan:
            plan, why = vanilla_plan[name], "vanilla table"
        else:
            plan, why = plan_for(name, a["parts"], content.variant_of)
        anatomy_plans[name] = {"plan": plan, "source": a["source"], "why": why,
                               "limbs": {k: v for k, v in limb_counts(a["parts"], content.variant_of).items()
                                         if k.startswith("#")}}

    mutations: Dict[str, Dict[str, Any]] = {}
    for cls, info in sorted(content.mutations.items(), key=lambda kv: kv[0].lower()):
        mutations[cls] = dict(info, layers=mutation_layers(cls, info), shownBy=mutation_shown_by(cls, info))

    doc = {
        "generated": _dt.datetime.now().isoformat(timespec="seconds"),
        "note": "anatomyPlans and mutations are rewritten on every scan; edit 'manual' "
                "({\"AnatomyName\": \"plan\"}) to move an anatomy to another plan.",
        "plans": list(gen.ALL_PLANS),
        "mods": len(mods),
        "manual": manual,
        "anatomyPlans": anatomy_plans,
        "mutations": mutations,
    }
    map_path.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    write_coverage(out / "coverage.md", doc)
    shown = sum(1 for m in mutations.values() if m["layers"])
    body = sum(1 for m in mutations.values() if not m["layers"] and m["shownBy"])
    print(f"{len(mods)} enabled mods; {len(anatomy_plans)} anatomies; {shown}/{len(mutations)} mutations "
          f"shown on a layer, {body} through the body or an effect -> {map_path}")
    return 0


def write_coverage(path: Path, doc: Dict[str, Any]) -> None:
    muts = doc["mutations"]
    lines = [
        "# CYF layered tiles: content coverage",
        "",
        f"Scanned {doc['generated']}: vanilla plus {doc['mods']} enabled mods "
        "(`cyf_scan_content.py`). A mutation shows when a layer token is part of its class or "
        "name; limbs (heads, arms, legs, tails, fins, tentacles, roots, wings) show from the "
        "body itself, whatever mutation or mod added them.",
        "",
        "## Body plans",
        "",
        "| Plan | Anatomies |",
        "|---|---|",
    ]
    by_plan: Dict[str, List[str]] = {}
    for name, a in doc["anatomyPlans"].items():
        tag = name if a["source"] == "vanilla" else f"{name} ({a['source']}; {a['why']})"
        by_plan.setdefault(a["plan"], []).append(tag)
    for plan in doc["plans"]:
        lines.append(f"| {plan} | {', '.join(by_plan.get(plan, [])) or '-'} |")
    lines += ["", "## Mutation layers", "", "| Layer | Mutations |", "|---|---|"]
    by_layer: Dict[str, List[str]] = {}
    for cls, m in muts.items():
        for lid in m["layers"]:
            label = m["name"] if m["source"].startswith("vanilla") else f"{m['name']} ({m['source']})"
            by_layer.setdefault(lid, []).append(label)
    for d in gen._LAYER_DEFS:
        if d.get("mutations"):
            lines.append(f"| {d['id']} | {', '.join(sorted(set(by_layer.get(d['id'], [])))) or '-'} |")
    lines += ["", "## Shown through the body or an effect", "",
              "These add or remove limbs or change the anatomy (the limb layers and the body plan "
              "follow), or show while their effect is on.", ""]
    via = sorted({(m["shownBy"], m["name"] if m["source"].startswith("vanilla") else f"{m['name']} ({m['source']})")
                  for m in muts.values() if not m["layers"] and m["shownBy"]})
    for kind, label in via:
        lines.append(f"- {label}: {'body / limbs' if kind == 'body' else 'while its effect is on'}")
    lines += ["", "## Mutations with no picture", "",
              "These change stats, senses, actions or the mind; nothing a tile can show, or no "
              "layer yet. Add a token to a layer in `_LAYER_DEFS` (or a new layer) to draw one.", ""]
    none_by_cat: Dict[str, List[str]] = {}
    for cls, m in muts.items():
        if not m["layers"] and not m["shownBy"]:
            label = m["name"] if m["source"].startswith("vanilla") else f"{m['name']} ({m['source']})"
            none_by_cat.setdefault(m["category"] or "?", []).append(label)
    for cat in sorted(none_by_cat):
        lines.append(f"- **{cat}** ({len(none_by_cat[cat])}): {', '.join(sorted(set(none_by_cat[cat])))}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
