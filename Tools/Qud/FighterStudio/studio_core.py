#!/usr/bin/env python3
"""Fighter Studio core: character -> picture prompt -> portrait layers -> 16x24 tile -> install.

No window code here. The window (fighter_studio.py) and the command line both use this.
It does not replace the Choose Your Fighter scripts in the folder above; it reads a character
export, writes the files those scripts expect, and builds the commands that run them:

  qud_fighter_import.py         the character (Recur export) -> <id>.fighter.json
  (in here)                     base art -> base.png + portrait.xml (background keyed, CPU)
  Shared/refart_client.py       layers: named parts cut into their own layers (GPU)
  cyf_portrait_items.py         --fitted: worn gear painted onto the portrait (GPU)
  qud_fighter_tile_generator.py --layered: the 16x24 layer sheets (CPU)
  cyf_compose_fighter.py        the tile as this character shows it
  ChooseYourFighter.ps1         -Action Install into Mods/Arendeth_CYFTiles

  python studio_core.py list
  (a character is a Characters export .xml, a build code .txt, or a fighter file .json made from one)
  python studio_core.py prompt <Characters/Name.date.xml> [--concept TEXT] [--target designer|sdxl]
                               [--picture base|dressed] [--outfit bare|wrap] [--backdrop "dark teal"]
  python studio_core.py traits <Characters/Name.date.xml>
"""
from __future__ import annotations

import argparse
import colorsys
import json
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
QUD = HERE.parent
TOOLS = QUD.parent
SHARED = TOOLS / "Shared"
for _p in (str(QUD), str(SHARED)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cyf_compose_fighter as comp  # noqa: E402
import qud_fighter_import as imp  # noqa: E402

USERDATA = imp.DEFAULT_COQ_USERDATA
CHARACTERS = USERDATA / "Characters"
OUTPUT = TOOLS / "Output" / "Fighters"
MOD = USERDATA / "Mods" / "Arendeth_CYFTiles"
MOD_BACKUPS = USERDATA / "_backups"
TRAITS_FILE = HERE / "traits.json"
CONTENT_MAP = QUD / "CYFTemplates" / "content_map.json"
REFART_PY = Path(r"E:\tools\refart\.venv\Scripts\python.exe")
DESIGNER_URL = "https://designer.microsoft.com/image-creator"
DESIGNER_LIMIT = 800     # Designer cut a prompt off at about 1,500 characters; the user's rule is about 800
PY = sys.executable

BACKDROPS = {"dark teal": (12, 53, 59), "black": (0, 0, 0), "light grey": (200, 200, 200), "white": (255, 255, 255)}
HEAD_STYLES = ("auto", "cat", "plain", "canine", "equine", "avian", "reptile", "insect", "fish", "robot", "skull",
               "fungal", "plant")
NUM = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight"}
INK = (12, 14, 18, 255)
# Layers that are auras, emissions or tics, not body. On a 16x24 tile several of them at once read as confetti,
# so the Tile tab can move them to the portrait only (the fighter's "tileHideLayers").
EFFECT_LAYERS = {"shadow", "speed", "levitate", "webs", "astral", "sparks", "psi", "regen", "vortex", "flames", "frost", "breath",
                 "orbit", "third_eye", "heart", "antenna", "glow", "aura", "tendril"}


def is_effect_layer(layer_id: str) -> bool:
    return layer_id.startswith("gas_") or layer_id in EFFECT_LAYERS

norm = comp.norm


def stamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


# ---------------------------------------------------------------------------------------------
# Character
# ---------------------------------------------------------------------------------------------
@dataclass
class Character:
    path: Path
    name: str
    id: str
    level: int = 1
    genotype: str = ""
    subtype: str = ""
    fg: str = ""
    detail: str = ""
    species: str = ""
    date: str = ""
    mutations: List[Tuple[str, str, int]] = field(default_factory=list)   # name, variant, level
    stats: Dict[str, int] = field(default_factory=dict)
    parts: List[Dict[str, Any]] = field(default_factory=list)             # the body tree
    naturals: List[Tuple[str, str]] = field(default_factory=list)         # (part type, natural item blueprint)
    items: List[Tuple[str, str]] = field(default_factory=list)            # (slot, blueprint), equipped only
    companions: List[str] = field(default_factory=list)
    limbs: Dict[str, int] = field(default_factory=dict)                   # "#head": 1, "#arm": 2, ...
    source: str = "export"          # export (Characters/*.xml) | buildcode (a build code or a fighter file made from one)
    anatomy: str = ""               # build codes only: the chosen body plan

    def limb(self, cls: str) -> int:
        return int(self.limbs.get("#" + cls, 0))

    def tile_info(self) -> Dict[str, Any]:
        """What the layered tile is picked from (cyf_compose_fighter.read_character's dict)."""
        if self.source == "export":
            return comp.read_character(self.path)
        limbs = dict(self.limbs)
        if any("conjoin" in norm(n) for n, _, _ in self.mutations):   # the tile's conjoined layers key on this body part
            limbs.setdefault("Conjoinment", 1)
        return {"limbs": limbs, "anatomy": self.anatomy or None, "name": self.name, "items": list(self.items),
                "mutations": [(norm(n + " " + v), lv) for n, v, lv in self.mutations],
                "worn": [norm(b) for _, b in self.items] + [norm(b) for _, b in self.naturals]}

    def label(self) -> str:
        if self.source == "buildcode":
            return f"{self.name}  L{self.level}  {self.genotype} / {self.subtype}  (build code: {self.path.name})"
        d = self.date
        when = f"{d[0:4]}-{d[4:6]}-{d[6:8]} {d[8:10]}:{d[10:12]}" if len(d) >= 12 else d
        return f"{self.name}  L{self.level}  {self.genotype} / {self.subtype}  ({when})"


def _root(path: Path) -> ET.Element:
    return ET.fromstring("<r>" + path.read_text(encoding="utf-8-sig") + "</r>")


def parse_character(path: Path) -> Character:
    """Read a Recur export (Characters/<Name>.<date>.xml)."""
    path = Path(path)
    root = _root(path)
    meta = root.find("Meta")
    if meta is None:
        raise ValueError(f"{path.name}: no <Meta> element, not a character export")
    go = root.find("GameObjects/GameObject[@Character='Player']")
    if go is None:
        go = root.find("GameObjects/GameObject")
    if go is None:
        raise ValueError(f"{path.name}: no player object")
    name = meta.get("Name") or path.stem.split(".")[0]
    ch = Character(path=path, name=name, id=imp.slugify(name), level=int(meta.get("Level") or 1),
                   genotype=meta.get("Genotype") or "", subtype=meta.get("Subtype") or "",
                   fg=meta.get("Foreground") or "", detail=meta.get("Detail") or "", date=meta.get("Date") or "")
    for p in go.findall("Property"):
        if p.get("Name") == "Species":
            ch.species = p.get("Value") or ""
    ch.mutations = [(m.get("Name") or "", m.get("Variant") or "", int(m.get("Level") or 1)) for m in go.findall("Mutation")]
    for s in go.findall("Statistic"):
        try:
            ch.stats[s.get("Name") or ""] = int(s.get("Value") or 0)
        except ValueError:
            pass

    def walk(node: ET.Element) -> List[Dict[str, Any]]:
        out = []
        for part in node.findall("Part"):
            t = part.get("Type") or ""
            d = {"type": t, "side": part.get("Laterality") or "", "gone": part.get("Dismembered") == "Yes",
                 "items": [i.get("Blueprint") or "" for i in part.findall("Item")],
                 "natural": [b.get("Blueprint") or "" for b in part.findall("Behavior")],
                 "children": walk(part)}
            ch.naturals += [(t, b) for b in d["natural"]]
            out.append(d)
        return out

    body = go.find("Body")
    if body is not None:
        ch.parts = walk(body)
        try:
            info = comp.read_character(path)
            ch.limbs = {k: v for k, v in info["limbs"].items() if k.startswith("#")}
            ch.items = [(s, b) for s, b in info["items"]]
        except Exception:  # the tile-side reader is stricter than this one; the prompt works without it
            ch.limbs = {}
    ch.companions = [strip_markup((g.find("Render").get("DisplayName") if g.find("Render") is not None else "")
                                  or g.get("Blueprint") or "")
                     for g in root.findall("GameObjects/GameObject") if g.get("Character") == "Companion"]
    return ch


def parse_build_source(path: Path) -> Character:
    """A character that was never exported: a build code (lastcharacter.txt or a saved code) or a fighter file made
    from one. A build code holds the choices only, so the body comes from the chosen anatomy, there are no stats
    worth reading, and gear is whatever the fighter file lists."""
    path = Path(path)
    if path.suffix.lower() == ".json":
        d = json.loads(path.read_text(encoding="utf-8"))
    elif imp.is_build_code(path):
        d = imp.parse_build_code(path).to_dict()
    else:
        raise ValueError(f"{path.name}: not a build code or fighter file")
    anatomy = d.get("anatomy") or next((n.split(":", 1)[1].strip() for n in d.get("notes") or []
                                        if str(n).startswith("Body plan:")), "")
    try:
        plans = json.loads(CONTENT_MAP.read_text(encoding="utf-8")).get("anatomyPlans", {})
    except (OSError, ValueError):
        plans = {}
    limbs = dict((plans.get(anatomy) or {}).get("limbs") or {"#head": 1, "#arm": 2, "#leg": 2})
    gear = [e for e in d.get("equipment") or [] if isinstance(e, dict)]
    # A build code lists no body parts, so parts a mutation or natural item grows (a Seed Cannon or Ovipositor
    # tail, wings) are added from the table's "covers", or the tile would miss its tail layer.
    table = load_table()
    grown = [norm((m.get("name") or "") + " " + (m.get("variant") or "")) for m in d.get("mutations") or []]
    grown += [norm(e.get("blueprint") or "") for e in gear if e.get("natural")]
    for blob in grown:
        for cls in (_best(table, blob) or {}).get("covers") or []:
            if cls in ("tail", "wing"):
                limbs["#" + cls] = max(1, int(limbs.get("#" + cls, 0)))
    name = d.get("name") or path.stem
    return Character(
        path=path, name=name, id=d.get("id") or imp.slugify(name), level=int(d.get("level") or 1),
        genotype=d.get("genotype") or "", subtype=d.get("subtype") or "", fg=d.get("foreground") or "", detail=d.get("detail") or "",
        mutations=[(m.get("name") or "", m.get("variant") or "", int(m.get("level") or 1)) for m in d.get("mutations") or []],
        naturals=[("", e.get("blueprint") or "") for e in gear if e.get("natural")],
        items=[("-", e.get("blueprint") or "") for e in gear if not e.get("natural")],
        limbs=limbs, source="buildcode", anatomy=anatomy)


def strip_markup(s: str) -> str:
    s = imp.strip_qud_markup(s or "")
    out, i = [], 0
    while i < len(s):                      # &Y / ^k colour codes
        if s[i] in "&^" and i + 1 < len(s):
            i += 2
            continue
        out.append(s[i])
        i += 1
    return "".join(out).strip()


def list_characters(folder: Optional[Path] = None) -> List[Character]:
    """Every readable export in Characters/, newest first."""
    out = []
    for f in sorted((folder or CHARACTERS).glob("*.xml")):
        try:
            out.append(parse_character(f))
        except Exception:
            continue
    out.sort(key=lambda c: c.date, reverse=True)
    if folder is None:      # characters that were never exported: fighter files made from a build code, then the last build
        seen = {c.id for c in out}
        extra = [f for f in sorted(OUTPUT.glob("*/*.fighter.json")) if f.stem == f.parent.name + ".fighter"]
        for f in extra + [USERDATA / "lastcharacter.txt"]:
            try:
                if f.suffix == ".json" and json.loads(f.read_text(encoding="utf-8")).get("source") != "buildcode":
                    continue
                c = parse_build_source(f)
            except Exception:
                continue
            if c.id not in seen:
                seen.add(c.id)
                out.append(c)
    return out


# ---------------------------------------------------------------------------------------------
# Traits: what the build looks like
# ---------------------------------------------------------------------------------------------
@dataclass
class Trait:
    key: str
    sources: List[str]
    phrase: str
    kind: str                      # body | part | effect | none
    separate: bool = False
    color: str = ""
    short: str = ""
    brief: str = ""                # shorter wording for compact prompts; cleared when the phrase is edited
    layer: Optional[Dict[str, Any]] = None
    follow: str = ""
    known: bool = True
    include: bool = True
    note: str = ""


def load_table() -> Dict[str, Any]:
    t = json.loads(TRAITS_FILE.read_text(encoding="utf-8"))
    for e in t.get("traits", []):
        e["match"] = [norm(m) for m in e.get("match", []) if norm(m)]
    return t


def load_content_map() -> Dict[str, Any]:
    try:
        return json.loads(CONTENT_MAP.read_text(encoding="utf-8")).get("mutations", {})
    except (OSError, ValueError):
        return {}


def _best(table: Dict[str, Any], blob: str) -> Optional[Dict[str, Any]]:
    best, size = None, 0
    for e in table.get("traits", []):
        for tok in e["match"]:
            if tok in blob and len(tok) > size:
                best, size = e, len(tok)
    return best


def _side(lat: str) -> str:
    lat = (lat or "").lower()
    if "right" in lat:
        return "right (the viewer's left)"
    if "left" in lat:
        return "left (the viewer's right)"
    return "upper"


def _join(xs: List[str]) -> str:
    xs = [x for x in xs if x]
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1] if xs else ""


def resolve_traits(ch: Character, table: Optional[Dict[str, Any]] = None, cmap: Optional[Dict[str, Any]] = None,
                   overrides: Optional[Dict[str, Dict[str, Any]]] = None, hidden: Optional[List[str]] = None) -> List[Trait]:
    """hidden: tile layers the fighter never shows (fighter json "hideLayers"); traits on them start unticked."""
    table = table or load_table()
    cmap = load_content_map() if cmap is None else cmap
    fmt = {"heads": NUM.get(ch.limb("head"), str(ch.limb("head"))), "arms": NUM.get(ch.limb("arm"), str(ch.limb("arm"))),
           "legs": NUM.get(ch.limb("leg"), str(ch.limb("leg"))), "onhead": " on each head" if ch.limb("head") > 1 else ""}
    hidden = set(hidden or [])
    by_key: Dict[str, Trait] = {}
    covered: set = set()

    def add(entry: Dict[str, Any], source: str) -> None:
        t = by_key.get(entry["id"])
        if t:
            if source not in t.sources:
                t.sources.append(source)
            return
        lay = entry.get("layer")
        by_key[entry["id"]] = Trait(
            key=entry["id"], sources=[source], phrase=(entry.get("phrase") or "").format(n="", side="", children="", **fmt),
            kind=entry.get("kind", "body"), separate=bool(entry.get("separate")), color=entry.get("color", ""),
            brief=(entry.get("brief") or "").format(n="", side="", children="", **fmt),
            short=entry.get("short") or (lay or {}).get("phrase") or entry["id"].replace("_", " "),
            layer=dict(lay) if lay else None, follow=entry.get("follow") or (lay or {}).get("follow", ""))
        covered.update(entry.get("covers") or [])

    for name, variant, level in ch.mutations:
        label = imp.humanize_token(name) + (f" ({imp.humanize_token(variant)})" if variant and variant != name else "")
        if level > 1:
            label += f" {level}"
        e = _best(table, norm(name + " " + variant))
        if e:
            add(e, label)
            continue
        info = cmap.get(name) or {}
        cat = info.get("category", "")
        shown = info.get("name") or imp.humanize_token(name)
        if cat.startswith("Mental"):
            by_key["unknown:" + name] = Trait("unknown:" + name, [label], "", "none", known=False, include=False,
                                              note="mental mutation, taken as not visible")
        else:
            by_key["unknown:" + name] = Trait(
                "unknown:" + name, [label], shown.lower(), "body", known=False, include=False,
                follow=",".join(info.get("layers") or []),
                note="not in the table: say how it looks, then tick it" + (f" (from {info['source']})" if info.get("source") else ""))
    for part_type, bp in ch.naturals:
        e = _best(table, norm(bp))
        if e:
            add(e, f"{imp.humanize_token(bp)} ({part_type.lower() or 'natural item'})")

    def walk(nodes: List[Dict[str, Any]], counter: Dict[str, int]) -> None:
        for p in nodes:
            rule = table.get("parts", {}).get(p["type"].lower())
            kids = [c for c in p["children"] if not c["gone"]]
            if rule and not p["gone"] and not (rule.get("needs_children") and not kids):
                i = counter[p["type"]] = counter.get(p["type"], 0) + 1
                tally: Dict[str, int] = {}
                for c in kids:
                    tally[c["type"].lower()] = tally.get(c["type"].lower(), 0) + 1
                words = []
                for kind, cnt in tally.items():
                    one, many = rule.get("children", {}).get(kind) or ["a " + kind, kind + "s"]
                    words.append(one if cnt == 1 else f"{NUM.get(cnt, str(cnt))} {many}")
                key = f"part:{p['type'].lower()}:{i}"
                by_key[key] = Trait(key, [f"{p['side']} {p['type']}".strip() + " (body part)"],
                                    rule["phrase"].format(side=_side(p["side"]), children=_join(words), n="", **fmt),
                                    "part", separate=bool(rule.get("separate")), short=rule.get("short") or p["type"].lower(),
                                    brief=(rule.get("brief") or "").format(
                                        side="right" if "right" in p["side"].lower() else "left" if "left" in p["side"].lower()
                                        else "upper", children=_join(words), n="", **fmt),
                                    layer=dict(rule["layer"]) if rule.get("layer") else None,
                                    follow="part:" + p["type"].lower())
                covered.update(rule.get("covers") or [])
            walk(p["children"], counter)

    walk(ch.parts, {})

    for cls, rule in table.get("limbs", {}).items():
        n = ch.limb(cls)
        if n >= int(rule.get("min", 1)) and cls not in covered:
            lay = rule.get("layer")
            by_key["limb:" + cls] = Trait(
                "limb:" + cls, [f"{n} x {cls} (body parts)"], rule["phrase"].format(n=NUM.get(n, str(n)), side="", children="", **fmt),
                "part", separate=bool(rule.get("separate")), short=(lay or {}).get("phrase") or cls,
                brief=(rule.get("brief") or "").format(n=NUM.get(n, str(n)), side="", children="", **fmt),
                layer=dict(lay) if lay else None, follow=(lay or {}).get("follow", ""))

    if not any(k in by_key for k in ("double_muscled", "gigantism")):
        st, to = ch.stats.get("Strength", 16), ch.stats.get("Toughness", 16)
        if st >= 26:
            by_key["build"] = Trait("build", [f"Strength {st}"], "a powerful, muscular build", "body")
        elif st <= 12 and to <= 12:
            by_key["build"] = Trait("build", [f"Strength {st}, Toughness {to}"], "a slight, narrow frame", "body")

    for t in by_key.values():
        if t.follow and t.follow in hidden:
            t.include, t.note = False, f"layer '{t.follow}' is hidden on this fighter"
    for key, o in (overrides or {}).items():
        t = by_key.get(key)
        if not t:
            continue
        if "phrase" in o and o["phrase"] != t.phrase:
            t.brief = ""
        for f in ("phrase", "kind", "separate", "include"):
            if f in o:
                setattr(t, f, o[f])
        if o.get("phrase") and not t.known:
            t.note = "your description"
    rank = {"body": 0, "part": 1, "effect": 2, "none": 3}
    return sorted(by_key.values(), key=lambda t: (rank.get(t.kind, 9), not t.include))


def save_trait_to_table(source_name: str, trait: Trait) -> None:
    """Append a description to traits.json so the next character with this mutation gets it (backup first)."""
    raw = json.loads(TRAITS_FILE.read_text(encoding="utf-8"))
    tok = norm(source_name)
    if not tok:
        raise ValueError("nothing to match on")
    bdir = HERE / "_backup"
    bdir.mkdir(exist_ok=True)
    shutil.copy2(TRAITS_FILE, bdir / f"traits.{stamp()}.json")
    entry = {"id": "user_" + tok, "match": [tok], "kind": trait.kind, "phrase": trait.phrase}
    if trait.separate:
        entry["separate"] = True
    raw["traits"] = [e for e in raw["traits"] if e.get("id") != entry["id"]] + [entry]
    TRAITS_FILE.write_text(json.dumps(raw, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------------------------
@dataclass
class PromptOptions:
    concept: str = ""
    target: str = "designer"        # designer | sdxl
    picture: str = "base"           # base (bare body, gear layered on later) | dressed (one picture with gear)
    outfit: str = "bare"            # bare | wrap      (picture = base)
    backdrop: str = "dark teal"
    tile_colors: bool = True
    subject: str = ""               # empty = subject_of(character)
    compact: bool = False           # shorter wording for prompt boxes with a low character limit


@dataclass
class PromptResult:
    prompt: str
    negative: str
    subject: str
    separate: List[str]
    effects: List[str]
    unknown: List[str]


def subject_of(ch: Character) -> str:
    heads = ch.limb("head")
    geno = ch.genotype.lower()
    if "mutat" in geno:
        kind = "mutant humanoid"
    elif "true kin" in geno:
        kind = "human"
    else:   # modded genotypes: their names are class names, so go by the body
        words = [w for w in imp.humanize_token(ch.subtype).lower().split()
                 if not w.startswith("uplift") and w not in ("subtype", "genotype")] if "uplift" in geno else []
        if ch.limb("leg") >= 3:
            shape = "many-legged humanoid creature" if ch.limb("arm") else "four-legged creature"
        else:
            shape = "humanoid creature" if ch.limb("arm") else "creature"
        kind = (" ".join(words) + " " if words else "") + shape
    return (f"{NUM.get(heads, str(heads))}-headed " if heads > 1 else "") + kind


def _a(s: str) -> str:
    return ("an " if s[:1].lower() in "aeiou" else "a ") + s


def build_prompt(ch: Character, traits: List[Trait], opt: PromptOptions, table: Optional[Dict[str, Any]] = None) -> PromptResult:
    table = table or load_table()
    shown = [t for t in traits if t.include and t.kind in ("body", "part") and t.phrase.strip()]
    body = [t.phrase.strip().rstrip(".") for t in shown]
    separate = [t.short for t in shown if t.separate]
    effects = [f"{t.phrase or t.key} ({', '.join(t.sources)})" + (f" -> layer '{t.follow}'" if t.follow else "")
               for t in traits if t.kind == "effect"]
    unknown = [", ".join(t.sources) for t in traits if not t.known and t.kind != "none" and not t.include]
    subject = opt.subject.strip() or subject_of(ch)
    colours = table.get("colors", {})
    scheme = ""
    if opt.tile_colors and not any(t.color for t in shown) and colours.get(ch.fg):
        scheme = colours[ch.fg] + (f" with {colours[ch.detail]} accents" if colours.get(ch.detail) and ch.detail != ch.fg else "")
    gear = [imp.humanize_token(b) for _, b in ch.items]
    style, world = table.get("style", ""), table.get("world", "")
    concept = opt.concept.strip().rstrip(".")
    has_hands = ch.limb("arm") > 0 or not ch.limbs
    # The user's rule: shaved heads only for oozes; everyone else short cropped hair; no beards on anyone.
    ooze = any(t.key.startswith("gelatinous") or t.key == "slime_glands" for t in shown)
    hair = "" if not has_hands else "bald shaved head, no beard" if ooze else "short cropped hair, no beard"

    if opt.target == "sdxl":
        bits = ["full body character", subject] + ([concept] if concept else []) + body
        if scheme:
            bits.append(scheme + " colour scheme")
        bits += [hair, "front view", "symmetrical standing pose", "arms away from the body"]
        if opt.picture == "dressed":
            bits += gear
        else:
            bits.append("bare smooth featureless body, no clothing" if opt.outfit == "bare" else "plain cloth wrap around the hips only")
        bits += [style, f"plain flat {opt.backdrop} background", "whole figure in frame"]
        neg = ["cropped", "close-up", "side view", "back view", "scenery", "ground shadow", "text", "watermark", "border",
               "multiple characters", "photo", "realistic", "blurry", "pixel art"]
        if opt.picture == "base":
            neg += ["armor", "weapon", "jewelry", "cloak", "hat"]
        return PromptResult(", ".join(b for b in bits if b), ", ".join(neg), subject, separate, effects, unknown)

    if opt.compact:
        s = [f"Full-body portrait of {_a(subject)}" + (f", {concept}" if concept else "") + "."]
        short_body = [(t.brief or t.phrase).strip().rstrip(".") for t in shown]
        if short_body:
            s.append(", ".join(short_body).capitalize() + ".")
        if scheme:
            s.append(f"{scheme.capitalize()}.")
        if hair:
            s.append(hair.capitalize() + ".")
        if separate:
            s.append(f"{_join(separate).capitalize()} held clear of the body.")
        s.append("Front view, symmetrical standing pose" + (", arms away from body, open five-fingered hands" if has_hands else "")
                 + ", whole figure in frame.")
        if opt.picture == "dressed":
            s.append(("Wearing " + _join(gear) + ".") if gear else "")
        else:
            s.append("Plain hip wrap only, no gear." if opt.outfit == "wrap" else "Bare smooth featureless body, no clothes or gear.")
        s.append(f"{(table.get('style_brief') or style).capitalize()}. Plain flat {opt.backdrop} background, no scenery, "
                 "text or shadow. 3:4 portrait.")
        return PromptResult(" ".join(x for x in s if x), "", subject, separate, effects, unknown)

    s = [f"Full-body character portrait of {ch.name}, {_a(subject)} from {world}."]
    if concept:
        s.append(concept[0].upper() + concept[1:] + ".")
    if body:
        s.append("Body: " + "; ".join(body) + ".")
    if scheme:
        s.append(f"Colour scheme: {scheme}.")
    if hair:
        s.append(hair.capitalize() + ".")
    if separate:
        it = "it" if len(separate) == 1 else "them"
        s.append(f"Keep the {_join(separate)} clear of the torso and the other limbs, with open background around {it}, "
                 "so nothing overlaps.")
    s.append("Standing upright facing the viewer in a straight symmetrical pose"
             + (", arms held a little away from the body, open empty hands with five fingers each" if has_hands else "")
             + ", feet apart. The whole figure is in frame from head to feet with a small margin, centred.")
    if opt.picture == "dressed":
        s.append(("Wearing and carrying: " + _join(gear) + ".") if gear else "Wearing simple travelling clothes.")
    elif opt.outfit == "wrap":
        s.append("Wearing only a plain cloth wrap around the hips: no armour, no jewellery, nothing held.")
    else:
        s.append("No clothing, armour, jewellery or held items: a bare body, smooth and featureless like a toy figure.")
    s.append(f"Style: {style}.")
    s.append(f"Plain flat {opt.backdrop} background and nothing else in the picture: no scenery, no ground shadow, "
             "no text, no border, no other characters.")
    s.append("Portrait orientation, 3:4.")
    return PromptResult(" ".join(s), "", subject, separate, effects, unknown)


# ---------------------------------------------------------------------------------------------
# Project: one fighter's work folder (Tools/Output/Fighters/<id>)
# ---------------------------------------------------------------------------------------------
PRESERVE = ("headStyle", "hideLayers", "tileHideLayers", "ownColors", "anatomy", "infections", "conceptNotes", "designerPrompt")


class Project:
    def __init__(self, ch: Character, out_root: Optional[Path] = None):
        self.ch = ch
        self.dir = (out_root or OUTPUT) / ch.id
        self.state_path = self.dir / f"{ch.id}.studio.json"
        self.state: Dict[str, Any] = {"overrides": {}, "options": {}, "prompt": ""}
        if self.state_path.exists():
            try:
                self.state.update(json.loads(self.state_path.read_text(encoding="utf-8")))
            except ValueError:
                pass

    # paths the other scripts fix
    @property
    def fighter_json(self) -> Path:
        return self.dir / f"{self.ch.id}.fighter.json"

    @property
    def tile_json(self) -> Path:
        return self.dir / f"{self.ch.id}.tile.json"

    @property
    def portrait_dir(self) -> Path:
        return self.dir / "Textures" / "Portraits" / self.ch.id

    @property
    def layers_dir(self) -> Path:
        return self.dir / "Textures" / "Layers" / self.ch.id

    @property
    def pinned_base(self) -> Path:
        return self.dir / "base" / f"{self.ch.id}_base.png"

    def hidden_layers(self) -> List[str]:
        """Tile layers the fighter file switches off everywhere (hideLayers)."""
        try:
            return [str(x) for x in json.loads(self.fighter_json.read_text(encoding="utf-8")).get("hideLayers") or []]
        except (OSError, ValueError):
            return []

    def approved(self) -> Tuple[List[str], str]:
        """(conceptNotes, designerPrompt) from the fighter file: the user's wording rules for this character and
        the exact Designer text that made the approved base. Read only: the Studio keeps them, never rewrites them."""
        try:
            d = json.loads(self.fighter_json.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return [], ""
        notes = d.get("conceptNotes") or []
        return [str(n) for n in (notes if isinstance(notes, list) else [notes])], str(d.get("designerPrompt") or "")

    def hand_spec(self) -> Optional[Path]:
        """A portrait cut spec someone made by hand for this fighter (cyf_portrait_layers.py format)."""
        for name in ("portrait_spec.json", f"{self.ch.id}.portrait.json"):
            if (self.dir / name).exists():
                return self.dir / name
        return None

    def source_art(self) -> Optional[Path]:
        hits = sorted(self.dir.glob(f"{self.ch.id}_portrait_src.*"))
        return hits[0] if hits else None

    def save_state(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state["character"] = str(self.ch.path)
        self.state_path.write_text(json.dumps(self.state, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    def backup(self, path: Path) -> Optional[Path]:
        """Copy a file or folder into <work>/_backup before it is replaced."""
        if not path.exists():
            return None
        b = self.dir / "_backup"
        b.mkdir(parents=True, exist_ok=True)
        dst = b / f"{path.name}.{stamp()}"
        if path.is_dir():
            shutil.copytree(path, dst)
        else:
            shutil.copy2(path, dst)
        return dst

    def save_fighter_json(self, head_style: str = "", description: str = "") -> Path:
        """Write <id>.fighter.json from the export. Hand-set fields of an existing file are kept."""
        if self.ch.path.resolve() == self.fighter_json.resolve():   # the fighter file is the source: only touch our fields
            fighter = json.loads(self.fighter_json.read_text(encoding="utf-8"))
            self.backup(self.fighter_json)
            if description.strip():
                fighter["description"] = description.strip()
            if head_style and head_style != "auto":
                fighter["headStyle"] = head_style
            self.fighter_json.write_text(json.dumps(fighter, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return self.fighter_json
        fighter = imp.import_any(self.ch.path).to_dict()
        if self.ch.anatomy:
            fighter.setdefault("anatomy", self.ch.anatomy)
        old: Dict[str, Any] = {}
        if self.fighter_json.exists():
            try:
                old = json.loads(self.fighter_json.read_text(encoding="utf-8"))
            except ValueError:
                old = {}
            self.backup(self.fighter_json)
        for k in PRESERVE:
            if k in old and old[k] not in (None, "", []):
                fighter[k] = old[k]
        desc = description.strip() or old.get("description") or ""
        if desc:
            fighter["description"] = desc
        if head_style and head_style != "auto":
            fighter["headStyle"] = head_style
        self.dir.mkdir(parents=True, exist_ok=True)
        self.fighter_json.write_text(json.dumps(fighter, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return self.fighter_json

    def status(self) -> List[Tuple[str, bool, str]]:
        """(stage, done, detail) for the Install tab."""
        pd, ld = self.portrait_dir, self.layers_dir
        src = self.source_art()
        n_layers = len(list(pd.glob("*.png"))) if pd.exists() else 0
        n_items = len(list((pd / "items").glob("*.png"))) if (pd / "items").exists() else 0
        sheets = sorted(p.stem for p in ld.glob("*.png")) if ld.exists() else []
        static = self.dir / "Textures" / "Creatures" / f"{self.ch.id}.png"
        return [
            ("Fighter file", self.fighter_json.exists(), self.fighter_json.name),
            ("Base art", src is not None, src.name if src else "no picture imported yet"),
            ("Portrait layers", (pd / "portrait.xml").exists(), f"{n_layers} layer pictures" if n_layers else "not split yet"),
            ("Fitted gear", n_items > 0, f"{n_items} item pictures" if n_items else "none (the game falls back to item tiles)"),
            ("Layer sheets (16x24)", bool(sheets), f"{len(sheets)} body plans" if sheets else "not baked yet"),
            ("Tile for this character", static.exists(), static.name if static.exists() else "not composed yet"),
        ]

    # ---- art
    def import_art(self, picture: Path) -> Path:
        """Keep the picture as <id>_portrait_src.<ext> (the name the layer specs use)."""
        self.dir.mkdir(parents=True, exist_ok=True)
        old = self.source_art()
        dst = self.dir / f"{self.ch.id}_portrait_src{picture.suffix.lower()}"
        if old and old.resolve() != Path(picture).resolve():
            self.backup(old)
            if old != dst:
                old.unlink()
        if dst.resolve() != Path(picture).resolve():
            shutil.copy2(picture, dst)
        return dst

    def make_base_portrait(self, info: Dict[str, Any]) -> Path:
        """Key the backdrop out of the imported picture and write the one-layer portrait:
        Textures/Portraits/<id>/base.png + portrait.xml, and a preview on the backdrop colour.

        A backdrop whose colour is far from the ink outline is keyed everywhere (pockets between arm and body
        included). A black or near-black backdrop is only keyed where it is joined to the picture's edge, so
        dark lines inside the figure are not punched out."""
        import numpy as np
        from PIL import Image
        from scipy import ndimage

        src = self.source_art()
        rgb = np.asarray(Image.open(src).convert("RGB")).astype(np.float32)
        d = np.abs(rgb - np.array(info["background"], np.float32)).sum(2)
        lo, hi = 28.0, 60.0
        bgish = d < hi
        if info.get("ink_backdrop"):
            lab, _ = ndimage.label(bgish)
            edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
            bgish = np.isin(lab, edge[edge > 0])
        alpha = np.where(bgish, np.clip((d - lo) / (hi - lo), 0, 1), 1.0)
        solid = alpha > 0.5
        lab, n = ndimage.label(solid)
        if n:   # specks in the backdrop drop out; parts held clear of the body stay
            sizes = ndimage.sum(solid, lab, range(1, n + 1))
            keep = np.isin(lab, 1 + np.flatnonzero(sizes >= 400))
            alpha = alpha * ndimage.binary_dilation(keep, iterations=2)
        x0, y0, x1, y1 = info["crop"]
        rgba = np.dstack([rgb, alpha * 255.0])[y0:y1, x0:x1].round().clip(0, 255).astype(np.uint8)
        ys, xs = np.nonzero(rgba[..., 3] > 4)
        if not len(xs):
            raise ValueError("nothing left after keying the background")
        bx0, bx1, by0, by1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
        pd = self.portrait_dir
        pd.mkdir(parents=True, exist_ok=True)
        Image.fromarray(rgba[by0:by1, bx0:bx1], "RGBA").save(pd / "base.png", optimize=True)
        (pd / "portrait.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            f'<portrait Fighter="{self.ch.id}" Width="{x1 - x0}" Height="{y1 - y0}">\n'
            f'  <layer File="base.png" X="{bx0}" Y="{by0}" />\n</portrait>\n', encoding="utf-8")
        prev = self.dir / "preview"
        prev.mkdir(parents=True, exist_ok=True)
        flat = Image.new("RGBA", (x1 - x0, y1 - y0), BACKDROPS["dark teal"] + (255,))
        flat.alpha_composite(Image.fromarray(rgba, "RGBA"))
        flat.save(prev / f"{self.ch.id}_portrait_all.png")
        return pd / "base.png"

    def auto_spec(self, traits: List[Trait], info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """A starting refart layers spec: every included trait that names a cuttable part."""
        heads = max(1, self.ch.limb("head"))
        mid = (heads - 1) // 2
        ids = [1 if i == mid else (i + 2 if i < mid else i + 1) for i in range(heads)]   # left to right; 1 = own head
        parts: List[Dict[str, Any]] = []
        for t in traits:
            lay = t.layer
            if not (t.include and lay and t.kind == "part"):
                continue
            fol = lay.get("follow", "")
            p: Dict[str, Any] = {"phrase": lay["phrase"], "z": lay.get("z", "front"), "fill": lay.get("fill", "transparent")}
            for k in ("only", "grow", "within", "stump", "fill_prompt"):
                if k in lay:
                    p[k] = lay[k]
            if "{i}" in fol:                                   # extra heads
                p.update(count=heads, assign="x", files=[None if i == 1 else f"head{i}.png" for i in ids],
                         follow=[None if i == 1 else fol.format(i=i) for i in ids])
            elif lay.get("within") == "head" or lay.get("group") == "head":   # horns, eye glow: one file per head
                stem = fol.split(",")[0]
                per = 2 if ("pair" in t.phrase or "eye" in lay["phrase"]) else 1
                p.update(count=per * heads, assign="group:head", files=[f"{stem}{'' if i == 1 else i}.png" for i in ids],
                         follow=[fol if i == 1 else f"{fol},head{i}" for i in ids])
            else:
                p.update(count=int(lay.get("count", 1)), files=[f"{fol or norm(t.short)}.png"], follow=[fol or norm(t.short)])
            parts.append(p)
        src = self.source_art()
        return {"fighter": self.ch.id, "source": src.name if src else "", "subject": subject_of(self.ch),
                "crop": (info or {}).get("crop", "auto"), "parts": parts}

    # ---- commands (argv lists; the window runs them one at a time)
    def cmd_auto_layers(self, spec: Path) -> List[str]:
        return [PY, str(SHARED / "refart_client.py"), "layers", "--spec", str(spec), "--out-dir", str(self.dir / "autolayers"),
                "--preview", str(self.dir / "autolayers_preview")]

    def cmd_generate(self, prompt: str, negative: str, out: Path, seed: int = 0) -> List[str]:
        return [PY, str(SHARED / "refart_client.py"), "generate", "--prompt", prompt, "--negative", negative, "--out", str(out),
                "--width", "832", "--height", "1216", "--seed", str(seed)]

    def cmd_gear(self, subject: str, force: bool = False) -> List[str]:
        """Fitted gear. This always paints (GPU): the script's --dry-run only covers its standalone-item mode."""
        c = [PY, str(QUD / "cyf_portrait_items.py"), str(self.dir), "--fitted", str(self.portrait_dir),
             "--character", str(self.ch.path), "--subject", subject]
        return c + (["--force"] if force else [])

    def gear_status(self) -> List[Tuple[str, str, bool]]:
        """(slot, blueprint, has fitted art) for each equipped item, from the portrait's own portrait.xml."""
        have: set = set()
        try:
            root = ET.parse(self.portrait_dir / "portrait.xml").getroot()
            have = {i.get("Blueprint") for i in root.iter("item")}
        except (OSError, ET.ParseError):
            pass
        return [(slot, bp, bp in have) for slot, bp in self.ch.items]

    def cmd_bake(self, head_style: str = "auto", bright: bool = False) -> List[str]:
        c = [PY, str(QUD / "qud_fighter_tile_generator.py"), str(self.fighter_json), "-o", str(self.dir), "--size", "vanilla",
             "--color-mode", "truecolor", "--animated", "--layered", "--no-sd"]
        c += ["--base-image", str(self.pinned_base)] if self.pinned_base.exists() else ["--allow-silhouette"]
        if head_style and head_style != "auto":
            c += ["--head-style", head_style]
        return c + (["--bright-palette"] if bright else [])

    def cmd_compose(self) -> List[str]:
        return [PY, str(QUD / "cyf_compose_fighter.py"), str(self.dir), str(self.ch.path), "--static",
                "--preview", str(self.dir / "preview")]

    def cmd_install(self) -> List[str]:
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(QUD / "ChooseYourFighter.ps1"),
                "-Action", "Install", "-Path", str(self.dir), "-UserData", str(USERDATA)]

    def backup_installed(self) -> Optional[Path]:
        """Copy what the mod holds for this fighter into CavesOfQud/_backups before an install replaces it."""
        fid = self.ch.id
        picks = [MOD / "Textures" / "Portraits" / fid, MOD / "Textures" / "Layers" / fid, MOD / "Fighters" / fid,
                 MOD / "Fighters.xml", MOD / "ChooseYourFighter.xml"]
        picks += sorted((MOD / "Textures" / "Creatures").glob(f"{fid}*.png")) if (MOD / "Textures" / "Creatures").exists() else []
        picks = [p for p in picks if p.exists()]
        if not picks:
            return None
        dst = MOD_BACKUPS / f"Arendeth_CYFTiles_{time.strftime('%Y-%m-%d')}studio_{time.strftime('%H%M%S')}"
        for p in picks:
            to = dst / p.relative_to(MOD)
            to.parent.mkdir(parents=True, exist_ok=True)
            if p.is_dir():
                shutil.copytree(p, to)
            else:
                shutil.copy2(p, to)
        return dst


# ---------------------------------------------------------------------------------------------
# Art: find the figure and the backdrop in an imported picture
# ---------------------------------------------------------------------------------------------
def analyze_art(path: Path) -> Dict[str, Any]:
    import numpy as np
    from PIL import Image
    from scipy import ndimage

    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(np.int16)
    h, w = a.shape[:2]
    border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    bg = np.median(border, axis=0)
    spread = float(np.abs(border - bg).sum(1).mean())
    mask = np.abs(a - bg).sum(2) > 55
    lab, n = ndimage.label(mask)
    warn: List[str] = []
    if not n:
        return {"size": [w, h], "background": [int(v) for v in bg], "figure": [0, 0, w, h], "crop": [0, 0, w, h],
                "ink_backdrop": False, "warnings": ["no figure found: the picture is one flat colour"]}
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    keep = np.isin(lab, 1 + np.flatnonzero(sizes >= max(400, sizes.max() * 0.02)))   # the figure and parts held clear of it
    ys, xs = np.nonzero(keep)
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
    m = max(8, round(h * 0.02))
    cy0, cy1 = max(0, y0 - m), min(h, y1 + m)
    cw = max(x1 - x0 + 2 * m, round((cy1 - cy0) * 3 / 4))
    cw = min(cw, w)
    cx0 = min(max(0, (x0 + x1) // 2 - cw // 2), w - cw)
    if spread > 30:
        warn.append(f"the background is not flat (border varies by {spread:.0f}): keying will leave a rough edge")
    if x0 <= 1 or x1 >= w - 1 or y0 <= 1 or y1 >= h - 1:
        warn.append("the figure touches the picture's edge: a part may be cut off")
    if (y1 - y0) < h * 0.6:
        warn.append("the figure fills under 60% of the height: the portrait will be small")
    ink = float(np.abs(bg - np.array(INK[:3])).sum()) < 60
    if ink:
        warn.append("the backdrop is as dark as the ink outline, so the outer line merges with it and pockets of backdrop "
                    "enclosed by the body stay in; a dark teal backdrop keys cleanly")
    return {"size": [w, h], "background": [int(v) for v in bg], "figure": [x0, y0, x1, y1],
            "crop": [int(cx0), int(cy0), int(cx0 + cw), int(cy1)], "ink_backdrop": ink, "warnings": warn}


# ---------------------------------------------------------------------------------------------
# Tile: compose, preview and recolour the 16x24 layers
# ---------------------------------------------------------------------------------------------
class Tile:
    """The baked layer set as this character shows it (the mod's own pick, mirrored by cyf_compose_fighter)."""

    def __init__(self, project: Project):
        from PIL import Image
        self.project = project
        man = json.loads(project.tile_json.read_text(encoding="utf-8"))
        ls = man["layerSet"]
        self.w, self.h = ls["tileSize"]
        self.n = int(ls.get("frameCount") or 1)
        info = project.ch.tile_info()
        self.plan = comp.choose_plan(ls["plans"], info["limbs"], info["anatomy"])
        self.never = [str(x) for x in ls.get("hideLayers") or []]
        self.off_tile = [str(x) for x in ls.get("tileHideLayers") or []]
        self.hidden = self.never + self.off_tile
        self.matched = comp.pick_layers(self.plan, info, self.never)     # what the build has, on the tile or not
        self.layers = comp.pick_layers(self.plan, info, self.hidden)
        self.sheet_path = project.dir / "Textures" / self.plan["sheet"]
        self.sheet = Image.open(self.sheet_path).convert("RGBA")

    def frames(self, outline: bool = False):
        out = [comp.compose(self.sheet, self.plan, self.layers, i, self.w, self.h) for i in range(self.n)]
        return [ink_outline(f) for f in out] if outline else out

    def write_static(self) -> Path:
        """The composite as the fighter's plain tile and frames (what cyf_compose_fighter.py --static writes).
        Used for build-code characters, which have no export for that script to read."""
        cre = self.project.dir / "Textures" / "Creatures"
        cre.mkdir(parents=True, exist_ok=True)
        fid = self.project.ch.id
        frames = self.frames()
        frames[0].save(cre / f"{fid}.png")
        for i, im in enumerate(frames):
            im.save(cre / f"{fid}_frame{i:02d}.png")
        return cre

    def rows(self) -> List[Tuple[int, int]]:
        """(row, frames) of the body and of every layer shown."""
        return [(0, int(self.plan["base"]["frames"]))] + [(l["row"], int(l["frames"])) for l in self.layers if "row" in l]

    def palette(self, top: int = 14) -> List[Tuple[Tuple[int, int, int], int]]:
        counts: Dict[Tuple[int, int, int], int] = {}
        for row, fr in self.rows():
            cell = self.sheet.crop((0, row * self.h, max(1, fr) * self.w, row * self.h + self.h))
            for n, (r, g, b, a) in cell.getcolors(self.w * self.h * 64) or []:
                if a >= 128:
                    counts[(r, g, b)] = counts.get((r, g, b), 0) + n
        return sorted(counts.items(), key=lambda kv: -kv[1])[:top]

    def set_off_tile(self, ids: List[str]) -> None:
        """Layers drawn on the portrait only. Written to the tile manifest (what Install reads) and to the
        fighter file (so a later bake keeps it); both are backed up first."""
        ids = sorted(set(ids))
        pr = self.project
        for path, edit in ((pr.tile_json, lambda d: d["layerSet"].__setitem__("tileHideLayers", ids)),
                           (pr.fighter_json, lambda d: d.__setitem__("tileHideLayers", ids))):
            if not path.exists():
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            pr.backup(path)
            edit(data)
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def apply_palette(self, mapping: Dict[Tuple[int, int, int], Tuple[int, int, int]]) -> Optional[Path]:
        """Swap exact colours on the rows this character shows. The sheet is backed up first."""
        mapping = {k: v for k, v in mapping.items() if k != v}
        if not mapping:
            return None
        bak = self.project.backup(self.sheet_path)
        px = self.sheet.load()
        for row, fr in self.rows():
            for y in range(row * self.h, row * self.h + self.h):
                for x in range(0, min(self.sheet.width, max(1, fr) * self.w)):
                    r, g, b, a = px[x, y]
                    if a and (r, g, b) in mapping:
                        px[x, y] = mapping[(r, g, b)] + (a,)
        self.sheet.save(self.sheet_path)
        return bak


def ink_outline(im):
    """Roughly what Arendeth_CYFTiles adds in game for Bright Qud: a dark ink line on the 4 neighbours."""
    from PIL import Image
    w, h = im.size
    src = im.load()
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.alpha_composite(im)
    dst = out.load()
    for y in range(h):
        for x in range(w):
            if src[x, y][3] >= 128:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and src[nx, ny][3] >= 128:
                    dst[x, y] = INK
                    break
    return out


def portrait_palette(png: Path, k: int = 8) -> List[Tuple[Tuple[int, int, int], int]]:
    """The main colours of the portrait's body, most used first (outline-dark pixels left out)."""
    from PIL import Image
    im = Image.open(png).convert("RGBA")
    im.thumbnail((256, 256))
    px = [(r, g, b) for r, g, b, a in im.getdata() if a > 200 and (r * 299 + g * 587 + b * 114) / 1000 > 45]
    if not px:
        return []
    flat = Image.new("RGB", (len(px), 1))
    flat.putdata(px)
    q = flat.quantize(k, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    return sorted(((tuple(pal[i * 3:i * 3 + 3]), n) for n, i in q.getcolors()), key=lambda kv: -kv[1])


def _hsv(c):
    return colorsys.rgb_to_hsv(c[0] / 255, c[1] / 255, c[2] / 255)


def _rgb(h, s, v):
    return tuple(int(round(max(0.0, min(1.0, x)) * 255)) for x in colorsys.hsv_to_rgb(h % 1.0, max(0.0, min(1.0, s)), max(0.0, min(1.0, v))))


def _hue_gap(a: float, b: float) -> float:
    d = abs(a - b) % 1.0
    return min(d, 1 - d)


def suggest_palette(sheet_cols, portrait_cols) -> Dict[Tuple[int, int, int], Tuple[int, int, int]]:
    """Move the tile's two main colour families onto the portrait's two main colours, keeping each
    tile colour's own light/dark step, so the flat two-tone shading survives."""
    def chroma(c):
        h, s, v = _hsv(c)
        return s > 0.22 and v > 0.18

    tile = [c for c, _ in sheet_cols if chroma(c)]
    art = [c for c, _ in portrait_cols if chroma(c)] or [c for c, _ in portrait_cols]
    if not tile or not art:
        return {}
    out: Dict[Tuple[int, int, int], Tuple[int, int, int]] = {}
    t1 = tile[0]
    fam1 = [c for c in tile if _hue_gap(_hsv(c)[0], _hsv(t1)[0]) < 0.11]
    rest = [c for c in tile if c not in fam1]
    a1 = art[0]
    a2 = next((c for c in art[1:] if _hue_gap(_hsv(c)[0], _hsv(a1)[0]) > 0.11), None)
    pairs = [(fam1, t1, a1)]
    if rest and a2:
        t2 = rest[0]
        pairs.append(([c for c in rest if _hue_gap(_hsv(c)[0], _hsv(t2)[0]) < 0.11], t2, a2))
    for fam, lead, target in pairs:
        lh, ls_, lv = _hsv(lead)
        th, ts, tv = _hsv(target)
        for c in fam:
            h, s, v = _hsv(c)
            out[c] = _rgb(th, ts * min(1.5, max(0.5, s / max(ls_, 0.01))), v * tv / max(lv, 0.01))
    return {k: v for k, v in out.items() if k != v}


# ---------------------------------------------------------------------------------------------
# Environment checks
# ---------------------------------------------------------------------------------------------
def game_running() -> bool:
    try:
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq CoQ.exe", "/NH"], capture_output=True, text=True, timeout=10,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return "CoQ.exe" in r.stdout
    except (OSError, subprocess.SubprocessError):
        return False


def refart_ready() -> bool:
    return REFART_PY.exists()


# ---------------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    for name in ("prompt", "traits"):
        p = sub.add_parser(name)
        p.add_argument("character", type=Path, help="Characters export (.xml), build code (.txt) or fighter file (.json)")
        if name == "prompt":
            p.add_argument("--concept", default="")
            p.add_argument("--target", choices=["designer", "sdxl"], default="designer")
            p.add_argument("--picture", choices=["base", "dressed"], default="base")
            p.add_argument("--outfit", choices=["bare", "wrap"], default="bare")
            p.add_argument("--backdrop", default="dark teal")
            p.add_argument("--subject", default="")
            p.add_argument("--compact", action="store_true")
    a = ap.parse_args()
    if a.cmd == "list":
        for c in list_characters():
            print(f"{c.path.name:42} {c.label()}")
        return 0
    ch = parse_character(a.character) if a.character.suffix.lower() == ".xml" else parse_build_source(a.character)
    proj = Project(ch)
    traits = resolve_traits(ch, overrides=proj.state.get("overrides"), hidden=proj.hidden_layers())
    if a.cmd == "traits":
        print("limbs:", dict(sorted(ch.limbs.items())), " subject:", subject_of(ch))
        for t in traits:
            print(f"[{'x' if t.include else ' '}] {t.kind:6} {'sep ' if t.separate else '    '}{', '.join(t.sources):44} "
                  f"{t.phrase or '-'}" + (f"   ({t.note})" if t.note else ""))
        return 0
    r = build_prompt(ch, traits, PromptOptions(a.concept, a.target, a.picture, a.outfit, a.backdrop, subject=a.subject, compact=a.compact))
    print(r.prompt)
    if r.negative:
        print("\nNEGATIVE: " + r.negative)
    if r.effects:
        print("\nEffect layers (not in the base picture):\n  " + "\n  ".join(r.effects))
    if r.unknown:
        print("\nLeft out, no description yet:\n  " + "\n  ".join(r.unknown))
    return 0


if __name__ == "__main__":
    sys.exit(main())
