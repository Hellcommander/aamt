#!/usr/bin/env python3
"""Port Elin MagicPlus spell templates into Starfield ArcaneConduit catalog.

Reads CustomRaceClassCreator MagicPlus/Data/*.xml and appends Starfield
catalog entries with source=\"elin\". Does not invent new behaviors — only
uses keywords already defined in catalog.json.

  python elin_starfield_spell_bridge.py preview
  python elin_starfield_spell_bridge.py import --dry-run
  python elin_starfield_spell_bridge.py import
  python elin_starfield_spell_bridge.py import --system dragon,blood

After import, compile in ArcaneConduit:
  python tools/spell_design.py validate
  python tools/spell_design.py compile
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

_ELIN = Path(__file__).resolve().parent
_CATALOG_PATH = _ELIN / "elin_asset_catalog.json"
_DEFAULT_ELIN_DATA = Path(
    r"E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator\MagicPlus\Data"
)
_DEFAULT_SF_CATALOG = Path(
    r"F:\SteamLibrary\steamapps\common\Starfield\ArcaneConduit\spells\catalog.json"
)

# Elin magicSystem id / filename hints -> ArcaneConduit school
SYSTEM_SCHOOL = {
    "dragon": "Pyrolysis",
    "blood": "Abyssal",
    "necromancy": "Entropy",
    "dream": "Phasics",
    "wisp": "Photonics",
    "weather": "Atmospherics",
    "spirit": "Celestial",
    "spectre": "Phasics",
    "golemancy": "Synthetics",
    "technomancy": "Synthetics",
    "pact": "Bindings",
    "rune": "Bindings",
    "element": "Voltaics",
    "bardic": "Photonics",
    "druidic": "Vitalics",
    "river": "Osmotics",
    "pollution": "Entropy",
    "geomancy": "Gravitics",
    "terrain": "Gravitics",
    "geoscience": "Gravitics",
    "etherwind": "Atmospherics",
    "crossmagic": "Bindings",
    "arcanesaturation": "Phasics",
    "slot": "Bindings",
    "ritual": "Bindings",
    "summon": "Synthetics",
}

ELEMENT_SCHOOL = {
    "fire": "Pyrolysis",
    "flame": "Pyrolysis",
    "heat": "Pyrolysis",
    "ice": "Cryonics",
    "cold": "Cryonics",
    "frost": "Cryonics",
    "lightning": "Voltaics",
    "shock": "Voltaics",
    "electric": "Voltaics",
    "poison": "Entropy",
    "acid": "Entropy",
    "necrotic": "Entropy",
    "blood": "Abyssal",
    "holy": "Celestial",
    "light": "Photonics",
    "dark": "Abyssal",
    "earth": "Gravitics",
    "stone": "Gravitics",
    "wind": "Atmospherics",
    "water": "Osmotics",
    "nature": "Vitalics",
    "arcane": "Phasics",
}

# Prefer existing ArcaneConduit spells when Elin maps to the same idea.
SKIP_ELIN_IDS = {
    "tmpl_dragon_fire_breath": "DragonBreath",  # already authored in SF
}

# asset_hint must match Tools/Shared/Concepts/meshes/elin*.glb stems.
SYSTEM_ASSET = {
    "dragon": "elinDragonMagic",
    "blood": "elinBloodMagic",
    "necromancy": "elinNecromancy",
    "dream": "elinDreamMagic",
    "wisp": "elinWispMagic",
    "weather": "elinWeatherMagic",
    "spirit": "elinSpiritMagic",
    "spectre": "elinSpectreMagic",
    "golemancy": "elinGolemancy",
    "technomancy": "elinTechnomancy",
    "pact": "elinPactMagic",
    "rune": "elinRuneMagic",
    "element": "elinElementMagic",
    "bardic": "elinBardicMagic",
    "druidic": "elinDruidicMagic",
    "river": "elinRiverMagic",
    "pollution": "elinPollution",
    "geomancy": "elinGeomancy",
    "terrain": "elinTerrainMagic",
    "geoscience": "elinGeoscience",
    "etherwind": "elinEtherwindMagic",
    "crossmagic": "elinCrossmagic",
    "arcanesaturation": "elinArcaneSaturation",
    "slot": "elinSlotMagic",
    "ritual": "elinRitualMagic",
    "summon": "elinPactMagic",
    "dynamic": "elinDynamicSpells",
    "mana": "elinManaMagic",
    "animatedservant": "elinAnimatedServant",
    "vision": "elinVisionSystem",
    "noise": "elinNoiseSystem",
    "spellfusion": "elinSpellFusion",
}


def _load_paths() -> Tuple[Path, Path]:
    elin_data = _DEFAULT_ELIN_DATA
    sf_catalog = _DEFAULT_SF_CATALOG
    if _CATALOG_PATH.is_file():
        try:
            cfg = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
            mod = Path(cfg.get("modPath") or "")
            if mod.is_dir():
                elin_data = mod / "MagicPlus" / "Data"
            sf = ((cfg.get("starfield") or {}).get("spellCatalog")) or ""
            if sf:
                sf_catalog = Path(sf)
        except Exception:
            pass
    return elin_data, sf_catalog


def _tags(node: ET.Element) -> List[str]:
    tags_el = node.find("tags")
    if tags_el is None:
        return []
    kids = list(tags_el.findall("tag"))
    if kids:
        return [(x.text or "").strip().lower() for x in kids if (x.text or "").strip()]
    text = (tags_el.text or "").strip().lower()
    if not text:
        return []
    return [t.strip() for t in re.split(r"[;,]", text) if t.strip()]


def _text(node: Optional[ET.Element], path: str, default: str = "") -> str:
    if node is None:
        return default
    hit = node.find(path)
    if hit is None:
        want = path.lower()
        for child in list(node):
            if child.tag.lower() == want:
                hit = child
                break
    if hit is None or hit.text is None:
        return default
    return hit.text.strip()


def _range_mid(attr: Optional[str], default: float = 0.0) -> float:
    if not attr:
        return default
    m = re.match(r"^\s*([0-9.]+)\s*-\s*([0-9.]+)", attr)
    if m:
        return (float(m.group(1)) + float(m.group(2))) / 2.0
    try:
        return float(attr)
    except ValueError:
        return default


def _pascal(name: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", name)
    return "".join(p[:1].upper() + p[1:] for p in parts) or "Spell"


def _sf_id(elin_id: str, name: str) -> str:
    # Stable EditorID suffix: Elin + PascalCase display name
    base = "Elin" + _pascal(name or elin_id)
    if not base.isidentifier():
        base = "Elin" + re.sub(r"[^A-Za-z0-9_]", "", base)
    if base[0].isdigit():
        base = "Elin_" + base
    return base


def _child(node: ET.Element, *names: str) -> Optional[ET.Element]:
    want = {n.lower() for n in names}
    for child in list(node):
        if child.tag.lower() in want:
            return child
    return None


def _float_text(node: Optional[ET.Element], default: float) -> float:
    if node is None:
        return default
    if node.text and node.text.strip():
        try:
            return float(node.text.strip())
        except ValueError:
            pass
    if node.get("amount"):
        try:
            return float(node.get("amount") or default)
        except ValueError:
            pass
    lo, hi = node.get("min"), node.get("max")
    if lo and hi:
        try:
            return (float(lo) + float(hi)) / 2.0
        except ValueError:
            pass
    if node.get("range"):
        return _range_mid(node.get("range"), default)
    return default


def _mana_any(node: ET.Element, default: float = 20.0) -> float:
    if node.find("resourceCosts") is not None:
        return _mana_from_resource_costs(node, default)
    for tag in ("manaCost", "ManaCost", "manaCostRange"):
        hit = _child(node, tag)
        if hit is not None:
            return _float_text(hit, default)
    for wrapper_name in ("cost", "requirements", "upkeepCost", "upkeepCosts"):
        wrap = _child(node, wrapper_name)
        if wrap is None:
            continue
        mana = _child(wrap, "mana", "Mana")
        if mana is not None:
            return _float_text(mana, default)
        for cost in wrap.findall("cost"):
            if (cost.get("resource") or "").strip().lower() == "mana":
                try:
                    return float(cost.get("amount") or default)
                except ValueError:
                    return default
    return default


def _guess_system(path: Path, template: ET.Element) -> str:
    ms = template.find("magicSystem")
    if ms is not None and ms.get("id"):
        return ms.get("id", "").strip().lower()
    stem = path.stem.lower()
    for key in SYSTEM_SCHOOL:
        if key in stem:
            return key
    return ""


def _school(system: str, tags: List[str], elements: List[str]) -> str:
    for e in elements:
        e = e.lower()
        for key, school in ELEMENT_SCHOOL.items():
            if key in e:
                return school
    joined = " ".join(tags)
    for key, school in ELEMENT_SCHOOL.items():
        if key in joined:
            return school
    return SYSTEM_SCHOOL.get(system, "Phasics")


def _has_word(blob: str, token: str) -> bool:
    """Whole-word / tag match so short tokens like 'em' do not hit 'enemy'."""
    return re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", blob) is not None


def _has_any(blob: str, tokens: Iterable[str]) -> bool:
    return any(_has_word(blob, t) for t in tokens)


def _archetype_and_behaviors(
    tags: List[str],
    name: str,
    desc: str,
    shape: Optional[ET.Element],
    available: Set[str],
) -> Tuple[str, List[str]]:
    tag_blob = " ".join(tags)
    text_blob = f"{name.lower()} {desc.lower()}"
    blob = f"{tag_blob} {text_blob}"
    behaviors: List[str] = []

    def take(b: str) -> None:
        if b in available and b not in behaviors:
            behaviors.append(b)

    # Prefer tags, then description words (word-boundary safe).
    if _has_any(blob, ("heal", "regen", "transfusion", "mend")):
        arch = "mend"
    elif _has_any(tag_blob, ("buff", "defense", "self")) and _has_any(blob, ("shield", "barrier", "hide", "ward", "fortify")):
        arch = "fortify"
        take("ward")
    elif _has_any(blob, ("shield", "barrier", "fortify", "ward")):
        arch = "fortify"
        take("ward")
    elif _has_any(blob, ("slow", "freeze", "frostbite", "restrain", "control", "puppet", "fear")):
        arch = "slow"
        take("restrain")
    elif _has_any(blob, ("phase", "ghost", "spectre", "wraith", "shadow")):
        arch = "phase"
        take("wraith")
        take("shadowphase")
    elif _has_any(blob, ("float", "levitate", "fly")):
        arch = "float"
        take("lift")
    elif _has_any(blob, ("poison", "decay", "corrupt", "rot", "bleed", "dot", "necrotic")):
        arch = "decay"
    elif _has_any(blob, ("lightning", "shock", "electric", "voltaic")):
        arch = "em"
        take("electric_orb")
    elif _has_any(blob, ("toxic", "pollution", "irradiate", "radiation")):
        arch = "rad"
        take("irradiate")
    elif _has_any(blob, ("dazzle", "blind", "flash")):
        arch = "dazzle"
    elif _has_any(blob, ("boost", "haste", "quickstep", "rage", "berserk")):
        arch = "boost"
        take("frenzy")
    else:
        arch = "contact"

    # Shape / delivery behaviors
    shape_type = (shape.get("type") if shape is not None else "") or ""
    if _has_word(blob, "breath") or shape_type == "cone":
        take("dragon_breath")
        take("beam")
    if shape_type == "circle" or _has_any(blob, ("nova", "aoe", "blast")):
        take("bloom")
        take("field")
    if _has_word(blob, "line") or shape_type == "line":
        take("beam")
    if _has_any(blob, ("projectile", "bolt", "lance")):
        take("seeking")
    if _has_word(blob, "chain"):
        take("chain")
    if _has_word(blob, "homing"):
        take("homing")
    if _has_word(blob, "pierce"):
        take("pierce")
    if _has_any(blob, ("summon", "golem", "drake", "call")):
        take("drone")
        take("mass")
    if _has_any(blob, ("vine orb", "caustic vessel")):
        take("vine_orb")
        take("seed")
    if _has_any(blob, ("storm", "weather", "thunder")):
        take("storm")
        take("mini_twister")
    if _has_word(blob, "blood"):
        take("weave")
        take("flesh")
    if _has_word(blob, "rune"):
        take("charged_runes")
    if _has_any(blob, ("portal", "rift")):
        take("portal")
        take("rift")
    if _has_word(blob, "pull"):
        take("pull")
    if _has_word(blob, "push"):
        take("push")
    if _has_any(blob, ("fire", "flame", "ember", "immolate")) and arch == "contact":
        take("pierce")

    if "elin" in available:
        return arch, ["elin"]
    return arch, behaviors[:3]


def _mana_from_resource_costs(node: ET.Element, default: float = 20.0) -> float:
    costs = node.find("resourceCosts")
    if costs is None:
        return default
    for cost in costs.findall("cost"):
        if (cost.get("resource") or "").strip().lower() == "mana":
            try:
                return float(cost.get("amount") or default)
            except ValueError:
                return default
    return default


def _effects_as_tags(node: ET.Element) -> List[str]:
    out: List[str] = []
    effects = node.find("effects")
    if effects is not None:
        for eff in effects.findall("effect"):
            if eff.text and eff.text.strip():
                out.append(eff.text.strip().lower())
    for eff in node.findall("effect"):
        if eff.text and eff.text.strip():
            out.append(eff.text.strip().lower())
    return out


def _parse_template_node(
    t: ET.Element,
    path: Path,
    data_dir: Path,
    *,
    system_override: str = "",
) -> Optional[Dict[str, Any]]:
    elin_id = (t.get("id") or "").strip()
    if not elin_id:
        return None
    name = _text(t, "name") or elin_id
    desc = _text(t, "description") or name
    tags = _tags(t)
    tags.extend(_effects_as_tags(t))
    type_text = _text(t, "type") or _text(t, "SpellType")
    if type_text:
        tags.append(type_text.lower())
    tags.append(t.tag.lower())
    system = system_override or _guess_system(path, t)
    if not system:
        stem = path.stem.lower()
        if "wildform" in stem or "venus" in stem:
            system = "druidic"
        elif "bond" in stem:
            system = "crossmagic"
        elif "anchor" in stem or stem.startswith("ether"):
            system = "etherwind"
    elements: List[str] = []
    ae = t.find("allowedElements")
    if ae is not None:
        for el in ae.findall("element"):
            if el.text:
                elements.append(el.text.strip())
        if ae.text and not elements:
            elements = [x.strip() for x in re.split(r"[;,]", ae.text) if x.strip()]
    mana = _mana_any(t, 20.0)
    power = _float_text(_child(t, "power", "Power", "powerRange", "intensity"), 30.0)
    rng = _float_text(_child(t, "range", "Range", "radius", "durationSeconds"), 0.0)
    shape = t.find("shape")
    return {
        "elin_id": elin_id,
        "name": name,
        "desc": desc,
        "tags": tags,
        "system": system,
        "elements": elements,
        "mana": mana,
        "power": power,
        "range": rng,
        "shape": shape,
        "source_file": str(path.relative_to(data_dir)).replace("\\", "/"),
    }


def parse_elin_templates(data_dir: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    def push(row: Optional[Dict[str, Any]]) -> None:
        if not row:
            return
        eid = row["elin_id"]
        if eid in seen:
            return
        seen.add(eid)
        out.append(row)

    for path in sorted(data_dir.rglob("*.xml")):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        for t in root.iter("Template"):
            push(_parse_template_node(t, path, data_dir))

        # Druidic MagicPlus uses <DruidicSpell>, not <Template>.
        if root.tag == "DruidicSpells" or path.name.startswith("druidic_"):
            for t in root.iter("DruidicSpell"):
                push(_parse_template_node(t, path, data_dir, system_override="druidic"))

        # Extra schemas the first pass skipped (Spell / Wildform / Hybrid / Field / Ritual / Anchor).
        extra: List[Tuple[str, str]] = []
        stem = path.stem.lower()
        parent = path.parent.name.lower()
        if root.tag in ("SpellTemplates", "Spells", "NecromancySpells") or stem.endswith("_spells"):
            sys_name = ""
            if "etherwind" in stem:
                sys_name = "etherwind"
            elif "summon" in stem:
                sys_name = "summon"
            elif "necromancy" in stem or parent == "necromancy":
                sys_name = "necromancy"
            extra.append(("Spell", sys_name))
        if root.tag == "WildformTemplates" or "wildform" in stem:
            extra.append(("WildformTemplate", "druidic"))
        if root.tag == "HybridTemplates":
            extra.append(("HybridTemplate", "druidic" if "druidic" in stem else "crossmagic"))
        if root.tag == "EtherFieldTemplates":
            extra.append(("Field", "etherwind"))
        if root.tag in ("BloodRituals", "Rituals", "StabilizationRitualTemplates"):
            rit_sys = "etherwind" if "etherwind" in stem else (
                "blood" if "blood" in stem else (
                    "crossmagic" if "bond" in stem else (
                        "summon" if "summon" in stem else ""
                    )
                )
            )
            extra.append(("Ritual", rit_sys))
        if root.tag == "AnchorTemplates":
            extra.append(("Anchor", "etherwind"))
        for tag, sys_name in extra:
            for t in root.iter(tag):
                push(_parse_template_node(t, path, data_dir, system_override=sys_name))

    return out


def map_to_starfield(
    row: Dict[str, Any],
    *,
    available_behaviors: Set[str],
    existing_ids: Set[str],
) -> Optional[Dict[str, Any]]:
    elin_id = row["elin_id"]
    if elin_id in SKIP_ELIN_IDS:
        return None
    # Skip empty bardic stubs without names/descriptions of substance
    if not row.get("desc") and not row.get("name"):
        return None

    sid = _sf_id(elin_id, row["name"])
    # Avoid colliding with existing non-Elin ids; suffix if needed
    if sid in existing_ids and not sid.startswith("Elin"):
        sid = "Elin" + sid
    n = 2
    base = sid
    while sid in existing_ids:
        sid = f"{base}{n}"
        n += 1

    school = _school(row["system"], row["tags"], row["elements"])
    arch, behaviors = _archetype_and_behaviors(
        row["tags"], row["name"], row["desc"], row.get("shape"), available_behaviors
    )

    # Scale Elin mana/power into SF cost/magnitude ranges used by existing catalog
    cost = max(8.0, min(48.0, round(float(row["mana"]) * 0.55, 1)))
    magnitude = max(8.0, min(60.0, round(float(row["power"]) * 0.45, 1)))
    area = 0
    duration = 0
    tags = set(row["tags"])
    if any(t in tags for t in ("aoe", "nova", "breath", "cone")) or (
        row.get("shape") is not None and (row["shape"].get("type") in ("circle", "cone"))
    ):
        area = 120 if "breath" in tags or (row.get("shape") is not None and row["shape"].get("type") == "cone") else 80
    if arch in ("decay", "slow", "fortify", "mend", "boost", "phase", "float"):
        duration = 8

    inspired = f"Elin {row['system'] or 'magic'}: {row['name']} ({elin_id})"
    desc = row["desc"]
    if not desc.endswith("."):
        desc = desc + "."
    desc = f"{desc} Ported from Elin CustomRaceClassCreator spell design."

    return {
        "id": sid,
        "name": row["name"] if len(row["name"]) <= 28 else row["name"][:28],
        "school": school,
        "inspired_by": inspired,
        "archetype": arch,
        "magnitude": magnitude,
        "area": area,
        "duration": duration,
        "cost": cost,
        "behaviors": behaviors,
        "desc": desc,
        "source": "elin",
        "elin_id": elin_id,
        "elin_system": row["system"],
        "elin_file": row["source_file"],
        "asset_hint": SYSTEM_ASSET.get(
            (row["system"] or "").lower(),
            "elin" + (_pascal(row["system"]) + "Magic" if row.get("system") else "DruidicMagic"),
        ),
    }


def build_candidates(
    elin_data: Path,
    sf_catalog: Path,
    systems: Optional[Set[str]] = None,
) -> Tuple[dict, List[Dict[str, Any]]]:
    cat = json.loads(sf_catalog.read_text(encoding="utf-8"))
    available = set((cat.get("behaviors") or {}).keys())
    existing = {s.get("id") for s in cat.get("spells") or [] if s.get("id")}
    # Also treat already-imported Elin ids as present
    existing_elin = {
        s.get("elin_id")
        for s in cat.get("spells") or []
        if s.get("source") == "elin" and s.get("elin_id")
    }
    rows = parse_elin_templates(elin_data)
    mapped: List[Dict[str, Any]] = []
    for row in rows:
        if systems and row["system"] and row["system"] not in systems:
            # also allow filename-based filter via empty system
            if row["system"] not in systems:
                continue
        if row["elin_id"] in existing_elin:
            continue
        spec = map_to_starfield(row, available_behaviors=available, existing_ids=existing)
        if not spec:
            continue
        existing.add(spec["id"])
        mapped.append(spec)
    return cat, mapped


def cmd_preview(args: argparse.Namespace) -> int:
    elin_data, sf_catalog = _load_paths()
    if args.elin_data:
        elin_data = Path(args.elin_data)
    if args.catalog:
        sf_catalog = Path(args.catalog)
    systems = {s.strip().lower() for s in (args.system or "").split(",") if s.strip()} or None
    _, mapped = build_candidates(elin_data, sf_catalog, systems)
    print(f"{len(mapped)} Elin templates would become Starfield spells\n")
    by_school: Dict[str, int] = {}
    for s in mapped:
        by_school[s["school"]] = by_school.get(s["school"], 0) + 1
        beh = ",".join(s["behaviors"]) or "-"
        print(
            f"  {s['id']:<28} {s['name']:<22} {s['school']:<14} "
            f"arch={s['archetype']:<8} {beh}  <- {s['elin_id']}"
        )
    print("\nby school:")
    for k in sorted(by_school):
        print(f"  {k}: {by_school[k]}")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    elin_data, sf_catalog = _load_paths()
    if args.elin_data:
        elin_data = Path(args.elin_data)
    if args.catalog:
        sf_catalog = Path(args.catalog)
    systems = {s.strip().lower() for s in (args.system or "").split(",") if s.strip()} or None
    cat, mapped = build_candidates(elin_data, sf_catalog, systems)
    if not mapped:
        print("nothing new to import")
        return 0

    # Fill life using ArcaneConduit helper when available
    sys.path.insert(0, str(sf_catalog.parent.parent / "tools"))
    try:
        import spell_design as sd  # type: ignore

        for s in mapped:
            if "life" not in s:
                s["life"] = round(sd.default_life_for(s), 2)
        probe = {"archetypes": cat["archetypes"], "behaviors": cat["behaviors"], "spells": cat["spells"] + mapped}
        problems = sd.validate(probe)
    except Exception as exc:
        print(f"[warn] spell_design validate unavailable ({exc}); basic checks only")
        problems = []
        for s in mapped:
            s.setdefault("life", 4.0)
            if not s["id"].isidentifier():
                problems.append(f"{s['id']}: bad id")

    if problems:
        print(f"refusing import: {len(problems)} problem(s)")
        for p in problems[:40]:
            print(f"  - {p}")
        return 1

    print(f"importing {len(mapped)} Elin-designed spells into {sf_catalog}")
    if args.dry_run:
        for s in mapped[:20]:
            print(f"  [dry] {s['id']} ({s['school']}) <- {s['elin_id']}")
        if len(mapped) > 20:
            print(f"  ... +{len(mapped) - 20} more")
        return 0

    cat["spells"].extend(mapped)
    # Track Elin bridge in meta
    meta = cat.setdefault("meta", {})
    sources = meta.setdefault("sources", [])
    note = "Elin CustomRaceClassCreator MagicPlus/Data spell templates"
    if note not in sources:
        sources.append(note)
    meta["elin_bridge"] = {
        "imported": len([s for s in cat["spells"] if s.get("source") == "elin"]),
        "tool": "Tools/Elin/elin_starfield_spell_bridge.py",
    }
    sf_catalog.write_text(json.dumps(cat, indent=2) + "\n", encoding="utf-8")
    print(f"saved. run: python tools/spell_design.py validate && python tools/spell_design.py compile")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("preview", "import"):
        p = sub.add_parser(name)
        p.add_argument("--elin-data", default="")
        p.add_argument("--catalog", default="")
        p.add_argument("--system", default="", help="comma-separated Elin systems, e.g. dragon,blood")
        if name == "import":
            p.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.cmd == "preview":
        return cmd_preview(args)
    return cmd_import(args)


if __name__ == "__main__":
    raise SystemExit(main())
