#!/usr/bin/env python3
"""
Choose Your Fighter — character import for Caves of Qud.

Reads:
  1) Recur: New Game EX exports  (%LocalLow%/Freehold Games/CavesOfQud/Characters/*.xml)
  2) CoQ save folders            (Synced/Saves/<id>/Primary.json + Primary.sav.gz)

Produces a fighter dict (mutations, cybernetics/implants, equipment, stats, meta)
suitable for portrait prompts and fighter-card generation.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


DEFAULT_COQ_USERDATA = (
    Path.home()
    / "AppData"
    / "LocalLow"
    / "Freehold Games"
    / "CavesOfQud"
)

MARKUP_RE = re.compile(r"\{\{[^{}|]*\|([^{}]*)\}\}")
MARKUP_STRIP_RE = re.compile(r"\{\{|\}}")
# Binary saves glue a length prefix before the next type (`DarkVision` + `3` + `XRL...`).
# Non-greedy name + lookahead keeps real trailing digits (e.g. AdrenalControl2).
MUTATION_TYPE_RE = re.compile(
    r"XRL\.World\.Parts\.Mutation\.([A-Za-z_][A-Za-z0-9_]*?)"
    r"(?=\d+XRL\.|[^A-Za-z0-9_]|$)"
)
BODY_MUT_MARKER_RE = re.compile(r"::([A-Za-z_][A-Za-z0-9_]*)::")
NOISE_MUTATION_PREFIXES = (
    "MutationEntry",
    "Mutations",
    "MutationFactory",
)


@dataclass
class FighterItem:
    blueprint: str
    number: int = 1
    mods: List[str] = field(default_factory=list)
    equipped: bool = False
    implant: bool = False
    natural: bool = False

    def label(self) -> str:
        base = humanize_token(self.blueprint)
        if self.mods:
            return f"{base} ({', '.join(humanize_token(m) for m in self.mods)})"
        return base


@dataclass
class FighterMutation:
    name: str
    level: int = 1
    variant: Optional[str] = None
    rapid_level: int = 0

    def label(self) -> str:
        text = humanize_token(self.name)
        if self.variant:
            text = f"{text} [{humanize_token(self.variant)}]"
        if self.level and self.level != 1:
            text = f"{text} L{self.level}"
        if self.rapid_level:
            text = f"{text} (+{self.rapid_level} rapid)"
        return text


@dataclass
class FighterCompanion:
    name: str
    blueprint: str = ""
    level: int = 1
    mutations: List[FighterMutation] = field(default_factory=list)
    description: str = ""
    gender: str = ""
    tile: str = ""
    source: str = ""  # Recur Source attr (Beguile, Proselytize, …)
    role: str = "follower"  # broodling | conjoined | follower

    def mutation_labels(self) -> List[str]:
        return [m.label() for m in self.mutations]

    def prompt_description(self) -> str:
        bits = [f"A Caves of Qud {self.role} named {self.name}"]
        if self.blueprint:
            bits.append(f"species/blueprint {humanize_token(self.blueprint)}")
        if self.level:
            bits.append(f"level {self.level}")
        if self.description:
            bits.append(self.description.strip())
        muts = self.mutation_labels()
        if muts:
            bits.append("Mutations: " + ", ".join(muts[:16]))
        if self.role == "broodling":
            bits.append(
                "This is an arthropod broodling minion loyal to its Broodmother matriarch"
            )
        elif self.role == "conjoined":
            bits.append(
                "This creature is physically conjoined/fused to its host's body "
                "(body-horror attachment, shared flesh connection)"
            )
        else:
            bits.append("This is a loyal follower / party companion of the player")
        return ". ".join(bits) + "."


@dataclass
class Fighter:
    id: str
    name: str
    source: str  # recur | save | unknown
    source_path: str = ""
    level: int = 1
    genotype: str = ""
    subtype: str = ""
    type_name: str = ""
    tile: str = ""
    foreground: str = ""
    detail: str = ""
    description: str = ""
    gender: str = ""
    location: str = ""
    game_mode: str = ""
    game_version: str = ""
    stats: Dict[str, int] = field(default_factory=dict)
    mutations: List[FighterMutation] = field(default_factory=list)
    cybernetics: List[FighterItem] = field(default_factory=list)
    equipment: List[FighterItem] = field(default_factory=list)
    inventory: List[FighterItem] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    companions: List[FighterCompanion] = field(default_factory=list)
    fidelity: str = "full"  # full | partial | metadata
    notes: List[str] = field(default_factory=list)

    def mutation_labels(self) -> List[str]:
        return [m.label() for m in self.mutations]

    def cybernetic_labels(self) -> List[str]:
        return [c.label() for c in self.cybernetics]

    def has_mutation_named(self, *needles: str) -> bool:
        blob = " ".join(m.name for m in self.mutations).lower()
        labels = " ".join(self.mutation_labels()).lower()
        text = blob + " " + labels
        return any(n.lower() in text for n in needles)

    def companions_by_role(self, role: str) -> List[FighterCompanion]:
        return [c for c in self.companions if c.role == role]

    def broodlings(self) -> List[FighterCompanion]:
        return self.companions_by_role("broodling")

    def conjoined(self) -> List[FighterCompanion]:
        return self.companions_by_role("conjoined")

    def followers(self) -> List[FighterCompanion]:
        return self.companions_by_role("follower")

    def equipment_labels(self, include_inventory: bool = False, limit: int = 40) -> List[str]:
        items = list(self.equipment)
        if include_inventory:
            items.extend(self.inventory)
        # Prefer equipped / implants already separated; de-dupe by blueprint+mods
        seen = set()
        out: List[str] = []
        for it in items:
            key = (it.blueprint, tuple(it.mods), it.implant, it.equipped)
            if key in seen:
                continue
            seen.add(key)
            out.append(it.label())
            if len(out) >= limit:
                break
        return out

    def prompt_description(self) -> str:
        bits = [f"A Caves of Qud character named {self.name}"]
        if self.type_name:
            bits.append(f"({self.type_name})")
        if self.level:
            bits.append(f"level {self.level}")
        if self.genotype or self.subtype:
            bits.append(
                "genotype "
                + " / ".join(
                    x for x in (humanize_token(self.genotype), humanize_token(self.subtype)) if x
                )
            )
        if self.description:
            bits.append(self.description.strip())
        muts = self.mutation_labels()
        if muts:
            bits.append("Mutations: " + ", ".join(muts[:24]))
        chrome = self.cybernetic_labels()
        if chrome:
            bits.append("Cybernetics: " + ", ".join(chrome[:16]))
        gear = self.equipment_labels(include_inventory=False, limit=16)
        if gear:
            bits.append("Equipped: " + ", ".join(gear))
        if self.companions:
            bits.append(
                "Companions: "
                + ", ".join(f"{c.name} ({c.role})" for c in self.companions[:8])
            )
        return ". ".join(bits) + "."

    def detailed_art_description(self, *, include_broodlings: bool = True, include_conjoined: bool = True, broodling_limit: int = 3) -> str:
        """Rich scene description for UncensoredCharacterImageGenerator."""
        parts: List[str] = []
        parts.append(
            f"Detailed full-body portrait of the Caves of Qud character {self.name}, "
            "science-fantasy, bizarre mutations, vibrant colors, high detail."
        )
        if self.type_name:
            parts.append(f"They appear as a {self.type_name}.")
        if self.description and self.description.strip().lower() not in {"it's you.", "its you."}:
            parts.append(self.description.strip())

        muts = self.mutation_labels()
        if muts:
            parts.append("Visible mutations and body features: " + ", ".join(muts[:28]) + ".")

        chrome = self.cybernetic_labels()
        if chrome:
            parts.append("Visible cybernetics and implants: " + ", ".join(chrome[:16]) + ".")

        gear = self.equipment_labels(include_inventory=False, limit=12)
        if gear:
            parts.append("Wearing and wielding: " + ", ".join(gear) + ".")

        if include_conjoined and (self.conjoined() or self.has_mutation_named("Conjoined")):
            conj = self.conjoined()
            if conj:
                bits = []
                for c in conj[:4]:
                    extra = ""
                    cl = c.mutation_labels()
                    if cl:
                        extra = " with " + ", ".join(cl[:6])
                    bits.append(
                        f"{c.name} ({humanize_token(c.blueprint) or 'creature'}){extra}"
                    )
                parts.append(
                    "Physically conjoined to their body (body-horror fusion, shared flesh, "
                    "creatures attached at Conjoinment sites): " + "; ".join(bits) + "."
                )
            else:
                parts.append(
                    "Has the Conjoined mutation: one or more creatures are physically fused "
                    "to their body with visible attachment points and symbiotic body horror."
                )

        if include_broodlings and (self.broodlings() or self.has_mutation_named("Broodmother", "Broodling")):
            brood = self.broodlings()
            parts.append(
                "Broodmother arthropod matriarch presence: pulsating chitinous broodling sack "
                "fused to the back when applicable."
            )
            if brood:
                shown = brood[: max(1, broodling_limit)]
                bits = []
                for c in shown:
                    bits.append(
                        f"{c.name} the {humanize_token(c.blueprint) or 'broodling'}"
                        + (f" ({', '.join(c.mutation_labels()[:4])})" if c.mutation_labels() else "")
                    )
                more = len(brood) - len(shown)
                tail = f" and {more} more in the swarm" if more > 0 else ""
                parts.append(
                    f"A few distinct broodling minions visible nearby in the scene: "
                    + "; ".join(bits)
                    + tail
                    + "."
                )
            else:
                parts.append(
                    "A few arthropod broodling minions (insect/arachnid drones) cluster near them."
                )

        followers = self.followers()
        if followers:
            parts.append(
                "Loyal non-fused followers also associated with them: "
                + ", ".join(c.name for c in followers[:6])
                + " (may appear at the edge of the scene or omitted if crowded)."
            )

        parts.append(
            "Show what the character really looks like in detail — accurate to mutations, "
            "chrome, conjoined attachments, and broodlings — not a simplified icon."
        )
        return " ".join(parts)

    def detailed_art_mutations(self) -> List[str]:
        labels = list(self.mutation_labels())
        # Tags the unfiltered generator already understands
        if self.has_mutation_named("Broodmother"):
            for tag in ("Broodmother", "Broodling Sack", "Insect Broodlings", "Hero Broodlings"):
                if tag not in labels:
                    labels.append(tag)
        if self.has_mutation_named("Conjoined") or self.conjoined():
            for tag in ("Conjoined", "Conjoined Creatures", "Conjoined Body Horror"):
                if tag not in labels:
                    labels.append(tag)
        return labels

    def detailed_art_traits(self) -> List[str]:
        traits: List[str] = []
        if self.broodlings() or self.has_mutation_named("Broodmother"):
            traits.extend(["Arthropod Matriarch", "Broodling Nest"])
        if self.conjoined() or self.has_mutation_named("Conjoined"):
            traits.append("Conjoined Fusion")
        if self.cybernetics:
            traits.append("Body Modder")
        return traits

    def art_payload(self, *, include_broodlings: bool = True, include_conjoined: bool = True, broodling_limit: int = 3) -> Dict[str, Any]:
        return {
            "kind": "fighter",
            "characterName": self.name,
            "gameType": "Qud",
            "description": self.detailed_art_description(
                include_broodlings=include_broodlings,
                include_conjoined=include_conjoined,
                broodling_limit=broodling_limit,
            ),
            "mutations": self.detailed_art_mutations(),
            "traits": self.detailed_art_traits(),
            "broodlings": [
                {"name": c.name, "blueprint": c.blueprint, "level": c.level}
                for c in self.broodlings()
            ],
            "conjoined": [
                {"name": c.name, "blueprint": c.blueprint, "level": c.level}
                for c in self.conjoined()
            ],
            "followers": [
                {"name": c.name, "blueprint": c.blueprint, "level": c.level, "role": c.role}
                for c in self.followers()
            ],
        }

    def minion_art_payloads(
        self,
        *,
        include_broodlings: bool = True,
        include_conjoined: bool = True,
        include_followers: bool = True,
        limit: int = 12,
    ) -> List[Dict[str, Any]]:
        """Separate unfiltered-art jobs for each minion / follower / conjoined mate."""
        out: List[Dict[str, Any]] = []
        pool: List[FighterCompanion] = []
        if include_broodlings:
            pool.extend(self.broodlings())
        if include_conjoined:
            pool.extend(self.conjoined())
        if include_followers:
            pool.extend(self.followers())
        for c in pool[: max(0, limit)]:
            muts = c.mutation_labels()
            traits: List[str] = []
            if c.role == "broodling":
                muts = list(muts) + ["Broodling Drones", "Insect Broodlings"]
                traits.append("Insect Broodlings")
            elif c.role == "conjoined":
                muts = list(muts) + ["Conjoined Creature", "Conjoined Body Horror"]
                traits.append("Conjoined Attachment")
            else:
                traits.append("Loyal Follower")
            # de-dupe preserving order
            seen = set()
            muts_u = []
            for m in muts:
                if m not in seen:
                    seen.add(m)
                    muts_u.append(m)
            out.append(
                {
                    "kind": "minion",
                    "role": c.role,
                    "characterName": c.name,
                    "gameType": "Qud",
                    "description": c.prompt_description()
                    + f" Associated with host character {self.name}.",
                    "mutations": muts_u,
                    "traits": traits,
                    "blueprint": c.blueprint,
                    "level": c.level,
                    "host": self.name,
                }
            )
        return out

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["mutationLabels"] = self.mutation_labels()
        d["cyberneticLabels"] = self.cybernetic_labels()
        d["equipmentLabels"] = self.equipment_labels(include_inventory=False)
        d["inventoryLabels"] = self.equipment_labels(include_inventory=True, limit=60)
        d["promptDescription"] = self.prompt_description()
        d["detailedArtDescription"] = self.detailed_art_description()
        d["artPayload"] = self.art_payload()
        d["minionArtPayloads"] = self.minion_art_payloads()
        d["broodlingCount"] = len(self.broodlings())
        d["conjoinedCount"] = len(self.conjoined())
        d["followerCount"] = len(self.followers())
        return d


def strip_qud_markup(text: str) -> str:
    if not text:
        return ""
    prev = None
    cur = text
    while prev != cur:
        prev = cur
        cur = MARKUP_RE.sub(r"\1", cur)
    cur = MARKUP_STRIP_RE.sub("", cur)
    # Color codes like &y / &C / ^k
    cur = re.sub(r"[&^][A-Za-z0-9]", "", cur)
    return cur.strip()


def humanize_token(token: str) -> str:
    if not token:
        return ""
    t = strip_qud_markup(token)
    t = t.replace("_", " ")
    # CamelCase / PascalCase → spaces, keep acronyms mostly intact
    t = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", t)
    t = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    # Drop common class prefixes that slip in from save scrapes
    for prefix in ("Mod ", "Cybernetics "):
        if t.startswith(prefix) and len(t) > len(prefix) + 2:
            # Keep cybernetics readable: "Cybernetics Gun Rack" ok
            pass
    if t.startswith("Mod ") and " " in t[4:]:
        t = t[4:]
    return t


def coq_userdata(root: Optional[Path] = None) -> Path:
    return Path(root) if root else DEFAULT_COQ_USERDATA


def characters_dir(userdata: Optional[Path] = None) -> Path:
    return coq_userdata(userdata) / "Characters"


def save_roots(userdata: Optional[Path] = None) -> List[Path]:
    base = coq_userdata(userdata)
    return [
        base / "Synced" / "Saves",
        base / "Saves",
        base / "Local" / "Saves",
    ]


# ---------------------------------------------------------------------------
# Recur XML
# ---------------------------------------------------------------------------

def _parse_item_element(el: ET.Element, *, equipped: bool = False, implant: bool = False, natural: bool = False) -> FighterItem:
    mods = []
    for mod in el.findall("Mod"):
        name = mod.get("Name") or ""
        if name:
            mods.append(name)
    number = 1
    try:
        number = int(el.get("Number") or "1")
    except ValueError:
        number = 1
    return FighterItem(
        blueprint=el.get("Blueprint") or "",
        number=number,
        mods=mods,
        equipped=equipped,
        implant=implant,
        natural=natural,
    )


def _walk_body_parts(
    part: ET.Element,
    equipment: List[FighterItem],
    cybernetics: List[FighterItem],
) -> None:
    for item in part.findall("Item"):
        if item.get("Blueprint"):
            equipment.append(_parse_item_element(item, equipped=True))
    for implant in part.findall("Implant"):
        if implant.get("Blueprint"):
            cybernetics.append(_parse_item_element(implant, implant=True, equipped=True))
    for behavior in part.findall("Behavior"):
        if behavior.get("Blueprint"):
            equipment.append(
                _parse_item_element(behavior, equipped=True, natural=True)
            )
    for child in part.findall("Part"):
        _walk_body_parts(child, equipment, cybernetics)


def _parse_game_object(go: ET.Element) -> Tuple[Dict[str, Any], List[FighterMutation], List[str], List[FighterItem], List[FighterItem], List[FighterItem], Dict[str, int]]:
    render = go.find("Render")
    desc = go.find("Description")
    name = ""
    tile = ""
    if render is not None:
        name = strip_qud_markup(render.get("DisplayName") or "")
        tile = render.get("Tile") or ""
    description = ""
    if desc is not None:
        description = strip_qud_markup(desc.get("Short") or "")

    gender_el = go.find("Gender")
    gender = gender_el.get("Name") if gender_el is not None else ""

    mutations: List[FighterMutation] = []
    for mut in go.findall("Mutation"):
        try:
            level = int(mut.get("Level") or "1")
        except ValueError:
            level = 1
        try:
            rapid = int(mut.get("RapidLevel") or "0")
        except ValueError:
            rapid = 0
        mutations.append(
            FighterMutation(
                name=mut.get("Name") or "",
                level=level,
                variant=mut.get("Variant") or None,
                rapid_level=rapid,
            )
        )

    skills = [s.get("Name") or "" for s in go.findall("Skill") if s.get("Name")]

    stats: Dict[str, int] = {}
    for st in go.findall("Statistic"):
        n = st.get("Name")
        if not n:
            continue
        try:
            stats[n] = int(st.get("Value") or "0")
        except ValueError:
            continue

    props = {p.get("Name"): p.get("Value") for p in go.findall("Property") if p.get("Name")}

    equipment: List[FighterItem] = []
    cybernetics: List[FighterItem] = []
    inventory: List[FighterItem] = []

    body = go.find("Body")
    if body is not None:
        for item in body.findall("Item"):
            if item.get("Blueprint"):
                equipment.append(_parse_item_element(item, equipped=True))
        for part in body.findall("Part"):
            _walk_body_parts(part, equipment, cybernetics)

    for item in go.findall("Item"):
        if item.get("Blueprint"):
            inventory.append(_parse_item_element(item))

    # Deduplicate cybernetics that also appear as Body/Item
    cyber_bps = {c.blueprint for c in cybernetics}
    equipment = [e for e in equipment if e.blueprint not in cyber_bps or e.natural]

    meta = {
        "name": name,
        "tile": tile,
        "description": description,
        "gender": gender or "",
        "genotype": props.get("Genotype") or "",
        "subtype": props.get("Subtype") or "",
        "blueprint": go.get("Blueprint") or "",
        "character": go.get("Character") or "",
    }
    return meta, mutations, skills, equipment, cybernetics, inventory, stats


def parse_recur_export(path: Path) -> Fighter:
    raw = path.read_text(encoding="utf-8", errors="replace")
    # Recur writes an XML fragment (no single root).
    wrapped = f"<RecurExport>\n{raw}\n</RecurExport>"
    root = ET.fromstring(wrapped)

    meta_el = root.find("Meta")
    meta_attrs = meta_el.attrib if meta_el is not None else {}

    game_objects = root.find("GameObjects")
    player_el = None
    companion_els: List[ET.Element] = []
    if game_objects is not None:
        for go in game_objects.findall("GameObject"):
            role = (go.get("Character") or "").lower()
            if role == "player" and player_el is None:
                player_el = go
            elif role == "companion":
                companion_els.append(go)

    if player_el is None and game_objects is not None:
        objs = game_objects.findall("GameObject")
        if objs:
            player_el = objs[0]

    if player_el is None:
        raise ValueError(f"No GameObject found in Recur export: {path}")

    pmeta, mutations, skills, equipment, cybernetics, inventory, stats = _parse_game_object(player_el)
    player_has_conjoined, player_has_brood = _player_mutation_flags(mutations)

    companions: List[FighterCompanion] = []
    for go in companion_els:
        cmeta, cmuts, _, _, _, _, cstats = _parse_game_object(go)
        bp = go.get("Blueprint") or ""
        src = go.get("Source") or ""
        cname = cmeta["name"] or bp or "Companion"
        companions.append(
            FighterCompanion(
                name=cname,
                blueprint=bp,
                level=cstats.get("Level", 1),
                mutations=cmuts,
                description=cmeta.get("description") or "",
                gender=cmeta.get("gender") or "",
                tile=cmeta.get("tile") or "",
                source=src,
                role=classify_companion_role(
                    name=cname,
                    blueprint=bp,
                    source=src,
                    mutations=cmuts,
                    player_has_conjoined=player_has_conjoined,
                    player_has_broodmother=player_has_brood,
                ),
            )
        )

    name = strip_qud_markup(meta_attrs.get("Name") or pmeta["name"] or path.stem)
    try:
        level = int(meta_attrs.get("Level") or stats.get("Level") or 1)
    except ValueError:
        level = stats.get("Level", 1)

    fighter = Fighter(
        id=slugify(name),
        name=name,
        source="recur",
        source_path=str(path),
        level=level,
        genotype=meta_attrs.get("Genotype") or pmeta["genotype"],
        subtype=meta_attrs.get("Subtype") or pmeta["subtype"],
        type_name=strip_qud_markup(meta_attrs.get("Type") or ""),
        tile=meta_attrs.get("Tile") or pmeta["tile"],
        foreground=meta_attrs.get("Foreground") or "",
        detail=meta_attrs.get("Detail") or "",
        description=pmeta["description"],
        gender=pmeta["gender"],
        stats=stats,
        mutations=mutations,
        cybernetics=cybernetics,
        equipment=equipment,
        inventory=inventory,
        skills=skills,
        companions=companions,
        fidelity="full",
        notes=[f"Imported from Recur export ({path.name})"],
    )
    return fighter


def list_recur_exports(userdata: Optional[Path] = None) -> List[Path]:
    d = characters_dir(userdata)
    if not d.is_dir():
        return []
    return sorted(d.glob("*.xml"), key=lambda p: p.stat().st_mtime, reverse=True)


# ---------------------------------------------------------------------------
# Save folders
# ---------------------------------------------------------------------------

def list_saves(userdata: Optional[Path] = None) -> List[Path]:
    found: List[Path] = []
    seen = set()
    for root in save_roots(userdata):
        if not root.is_dir():
            continue
        for child in root.iterdir():
            if not child.is_dir():
                continue
            primary = child / "Primary.json"
            if not primary.is_file():
                continue
            key = child.name.lower()
            if key in seen:
                continue
            seen.add(key)
            found.append(child)
    found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return found


def _load_primary_json(save_dir: Path) -> Dict[str, Any]:
    path = save_dir / "Primary.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def _read_sav_bytes(save_dir: Path) -> Optional[bytes]:
    for name in ("Primary.sav.gz", "Checkpoint.sav.gz", "Primary.sav", "Checkpoint.sav"):
        path = save_dir / name
        if not path.is_file():
            continue
        data = path.read_bytes()
        if name.endswith(".gz"):
            try:
                return gzip.decompress(data)
            except OSError:
                continue
        return data
    return None


def _clean_mutation_token(token: str) -> Optional[str]:
    if not token:
        return None
    token = re.split(r"[^A-Za-z0-9_]", token, maxsplit=1)[0]
    # Guard against rare leftover glue (e.g. Name3XRL)
    token = re.sub(r"\d+XRL$", "", token)
    if token.endswith("XRL") and len(token) > 3:
        token = token[:-3]
    if not token or token in NOISE_MUTATION_PREFIXES:
        return None
    if token.startswith("Mutation"):
        return None
    if len(token) < 3:
        return None
    return token


def _scrape_player_from_sav(blob: bytes) -> Tuple[List[FighterMutation], List[FighterItem], List[str]]:
    """Best-effort scrape of player mutations/cybernetics from binary save."""
    text = blob.decode("latin-1", errors="ignore")

    # Prefer the type-graph window that lists parts on the player object.
    muts: List[FighterMutation] = []
    seen_mut: set = set()
    idx = text.find("XRL.World.Parts.Mutations")
    if idx >= 0:
        window = text[idx : idx + 12000]
        # Stop before overworld/terrain part spam if present
        cut = window.find("XRL.World.Parts.TerrainTravel")
        if cut > 500:
            window = window[:cut]
        for m in MUTATION_TYPE_RE.finditer(window):
            name = _clean_mutation_token(m.group(1))
            if not name or name in seen_mut:
                continue
            seen_mut.add(name)
            muts.append(FighterMutation(name=name, level=1))

    # Body markers near OriginalPlayerBody / PlayerBody (limb managers)
    for anchor in ("OriginalPlayerBody", "PlayerBody"):
        pidx = text.find(anchor)
        if pidx < 0:
            continue
        body_window = text[max(0, pidx - 500) : pidx + 25000]
        for m in BODY_MUT_MARKER_RE.finditer(body_window):
            name = _clean_mutation_token(m.group(1))
            if not name or name in seen_mut:
                continue
            # Skip anatomy noise
            if name.lower() in {"change", "add", "remove", "multipleheads"} and name != "MultipleHeads":
                pass
            if name in {"Change", "Add", "Remove"}:
                continue
            seen_mut.add(name)
            muts.append(FighterMutation(name=name, level=1))

        # Ability titles sometimes embed mutation display names
        for label in (
            "Broodmother",
            "Carapace",
            "Multiple Heads",
            "Multiple Arms",
            "Fluffy Tail",
            "Electrical Generation",
            "Stinger",
            "Teleportation",
            "Domination",
            "Precognition",
            "Phasing",
            "Burgeoning",
            "Light Manipulation",
            "Temporal Fugue",
        ):
            if label in body_window:
                key = label.replace(" ", "")
                # Map a few display → class guesses
                class_guess = {
                    "MultipleHeads": "MultipleHeads",
                    "MultipleArms": "MultipleArms",
                    "FluffyTail": "FluffyTail",
                    "ElectricalGeneration": "ElectricalGeneration",
                    "LightManipulation": "LightManipulation",
                    "TemporalFugue": "TemporalFugue",
                    "Broodmother": "Arendeth_Broodmother",
                }.get(key, key)
                if class_guess not in seen_mut and key.replace(" ", "") not in seen_mut:
                    # only add if something mutation-like nearby
                    if "Mutation" in body_window or "Command" in body_window:
                        seen_mut.add(class_guess)
                        muts.append(FighterMutation(name=class_guess, level=1))

    cyber: List[FighterItem] = []
    # Cybernetic blueprints in .sav.gz sit in a global type table and are not reliably
    # attributable to the player. Prefer Recur exports for implants/gear.
    notes = []
    if muts:
        notes.append(f"save-scrape mutations={len(muts)}")
    notes.append("save cybernetics/equipment require a Recur export for reliable data")
    return muts, cyber, notes


def parse_save_folder(save_dir: Path) -> Fighter:
    save_dir = Path(save_dir)
    meta = _load_primary_json(save_dir)
    name = strip_qud_markup(meta.get("Name") or save_dir.name)
    level = int(meta.get("Level") or 1)
    geno = meta.get("GenoSubType") or ""
    genotype, subtype = "", ""
    if isinstance(geno, str) and geno:
        # Sometimes "Mutated Human/Apostle", sometimes empty
        if "/" in geno:
            genotype, subtype = geno.split("/", 1)
        else:
            genotype = geno

    fighter = Fighter(
        id=slugify(name) or save_dir.name,
        name=name,
        source="save",
        source_path=str(save_dir),
        level=level,
        genotype=genotype,
        subtype=subtype,
        tile=meta.get("CharIcon") or "",
        location=meta.get("Location") or "",
        game_mode=meta.get("GameMode") or "",
        game_version=meta.get("GameVersion") or "",
        fidelity="metadata",
        notes=[f"Save metadata from Primary.json ({save_dir.name})"],
    )

    blob = _read_sav_bytes(save_dir)
    if blob:
        muts, cyber, scrape_notes = _scrape_player_from_sav(blob)
        fighter.mutations = muts
        fighter.cybernetics = cyber
        fighter.notes.extend(scrape_notes)
        if muts or cyber:
            fighter.fidelity = "partial"
            fighter.notes.append(
                "Binary save scrape is best-effort; prefer a Recur export for full gear/levels."
            )
        else:
            fighter.notes.append(
                "Could not scrape mutations/cybernetics from .sav.gz; export via Recur for full fidelity."
            )
    else:
        fighter.notes.append("No Primary.sav.gz found beside Primary.json.")

    return fighter


def slugify(name: str) -> str:
    s = strip_qud_markup(name).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "fighter"


def classify_companion_role(
    *,
    name: str,
    blueprint: str,
    source: str,
    mutations: Sequence[FighterMutation],
    player_has_conjoined: bool,
    player_has_broodmother: bool,
) -> str:
    """Classify Recur companions as broodling / conjoined / follower."""
    blob = " ".join(
        [
            name or "",
            blueprint or "",
            source or "",
            " ".join(m.name for m in mutations),
        ]
    ).lower()

    brood_keys = (
        "broodling",
        "brood_ling",
        "broodmother",
        "arendeth_brood",
        "brooddrone",
        "broodsoldier",
    )
    if any(k in blob.replace(" ", "") or k in blob for k in brood_keys):
        return "broodling"

    conj_keys = (
        "conjoin",
        "conjoined",
        "conjoinment",
        "fusedmate",
        "bodyhorror",
    )
    if any(k in blob for k in conj_keys):
        return "conjoined"

    # Heuristic: when host has Conjoined and companion isn't clearly a broodling,
    # Recur often lists fused mates as normal Companions — treat small set as conjoined
    # only if Source is empty/unknown and blueprint looks like a creature (not item).
    if player_has_conjoined and not player_has_broodmother:
        # Prefer explicit; otherwise leave as follower unless Source hints domination/etc.
        pass

    if player_has_broodmother and ("ant" in blob or "beetle" in blob or "spider" in blob or "scorpion" in blob):
        # Common broodling base creatures when named generically
        if "maxatony" not in blob and "companion" not in blob:
            return "broodling"

    return "follower"


def _player_mutation_flags(mutations: Sequence[FighterMutation]) -> Tuple[bool, bool]:
    names = " ".join(m.name for m in mutations).lower()
    return ("conjoined" in names, "broodmother" in names or "broodling" in names)


# ---------------------------------------------------------------------------
# Discovery / CLI
# ---------------------------------------------------------------------------

def discover_sources(userdata: Optional[Path] = None) -> Dict[str, List[Dict[str, Any]]]:
    recur = []
    for p in list_recur_exports(userdata):
        try:
            meta_name = p.stem
            # Cheap peek without full parse
            head = p.read_text(encoding="utf-8", errors="replace")[:800]
            m = re.search(r'<Meta\s+Name="([^"]+)"', head)
            level_m = re.search(r'Level="(\d+)"', head)
            recur.append(
                {
                    "kind": "recur",
                    "path": str(p),
                    "name": strip_qud_markup(m.group(1)) if m else meta_name,
                    "level": int(level_m.group(1)) if level_m else None,
                    "mtime": p.stat().st_mtime,
                }
            )
        except OSError:
            continue

    saves = []
    for d in list_saves(userdata):
        try:
            meta = _load_primary_json(d)
            saves.append(
                {
                    "kind": "save",
                    "path": str(d),
                    "name": strip_qud_markup(meta.get("Name") or d.name),
                    "level": meta.get("Level"),
                    "location": meta.get("Location"),
                    "mtime": d.stat().st_mtime,
                }
            )
        except (OSError, json.JSONDecodeError):
            continue

    return {"recur": recur, "saves": saves}


def import_any(path: Path) -> Fighter:
    path = Path(path)
    if path.is_file() and path.suffix.lower() == ".xml":
        return parse_recur_export(path)
    if path.is_dir() and (path / "Primary.json").is_file():
        return parse_save_folder(path)
    if path.is_file() and path.name.lower() in {"primary.json", "checkpoint.json"}:
        return parse_save_folder(path.parent)
    if path.is_file() and path.suffix.lower() == ".json":
        return fighter_from_dict(json.loads(path.read_text(encoding="utf-8")))
    raise ValueError(f"Unrecognized character source: {path}")


def fighter_from_dict(data: Dict[str, Any]) -> Fighter:
    """Rehydrate a Fighter from exported .fighter.json (best-effort)."""
    def muts(raw):
        out = []
        for m in raw or []:
            if isinstance(m, dict):
                out.append(
                    FighterMutation(
                        name=m.get("name") or "",
                        level=int(m.get("level") or 1),
                        variant=m.get("variant"),
                        rapid_level=int(m.get("rapid_level") or 0),
                    )
                )
        return out

    def items(raw, **flags):
        out = []
        for it in raw or []:
            if isinstance(it, dict):
                out.append(
                    FighterItem(
                        blueprint=it.get("blueprint") or "",
                        number=int(it.get("number") or 1),
                        mods=list(it.get("mods") or []),
                        equipped=bool(it.get("equipped", flags.get("equipped", False))),
                        implant=bool(it.get("implant", flags.get("implant", False))),
                        natural=bool(it.get("natural", False)),
                    )
                )
        return out

    companions = []
    for c in data.get("companions") or []:
        if not isinstance(c, dict):
            continue
        companions.append(
            FighterCompanion(
                name=c.get("name") or "Companion",
                blueprint=c.get("blueprint") or "",
                level=int(c.get("level") or 1),
                mutations=muts(c.get("mutations")),
                description=c.get("description") or "",
                gender=c.get("gender") or "",
                tile=c.get("tile") or "",
                source=c.get("source") or "",
                role=c.get("role") or "follower",
            )
        )

    return Fighter(
        id=data.get("id") or slugify(data.get("name") or "fighter"),
        name=data.get("name") or "Fighter",
        source=data.get("source") or "unknown",
        source_path=data.get("source_path") or "",
        level=int(data.get("level") or 1),
        genotype=data.get("genotype") or "",
        subtype=data.get("subtype") or "",
        type_name=data.get("type_name") or "",
        tile=data.get("tile") or "",
        foreground=data.get("foreground") or "",
        detail=data.get("detail") or "",
        description=data.get("description") or "",
        gender=data.get("gender") or "",
        location=data.get("location") or "",
        game_mode=data.get("game_mode") or "",
        game_version=data.get("game_version") or "",
        stats=dict(data.get("stats") or {}),
        mutations=muts(data.get("mutations")),
        cybernetics=items(data.get("cybernetics"), implant=True, equipped=True),
        equipment=items(data.get("equipment"), equipped=True),
        inventory=items(data.get("inventory")),
        skills=list(data.get("skills") or []),
        companions=companions,
        fidelity=data.get("fidelity") or "partial",
        notes=list(data.get("notes") or []),
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Import CoQ Recur exports or saves into fighter JSON")
    parser.add_argument("--userdata", type=Path, default=None, help="CoQ LocalLow userdata root")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List Recur exports and saves")
    p_list.add_argument("--json", action="store_true")

    p_imp = sub.add_parser("import", help="Import one source to fighter JSON")
    p_imp.add_argument("path", type=Path)
    p_imp.add_argument("-o", "--output", type=Path, default=None)
    p_imp.add_argument("--pretty", action="store_true")

    p_art = sub.add_parser(
        "art",
        help="Build unfiltered-art payloads (fighter scene + optional per-minion jobs)",
    )
    p_art.add_argument("path", type=Path, help="Recur XML, save folder, or .fighter.json")
    p_art.add_argument("-o", "--output", type=Path, default=None)
    p_art.add_argument("--pretty", action="store_true")
    p_art.add_argument("--no-broodlings", action="store_true")
    p_art.add_argument("--no-conjoined", action="store_true")
    p_art.add_argument("--broodling-limit", type=int, default=3)
    p_art.add_argument(
        "--minions",
        action="store_true",
        help="Include separate art payloads for broodlings/conjoined/followers",
    )
    p_art.add_argument("--minion-limit", type=int, default=12)
    p_art.add_argument("--followers-only", action="store_true", help="Minion jobs: followers only")
    p_art.add_argument("--broodlings-only", action="store_true", help="Minion jobs: broodlings only")
    p_art.add_argument("--conjoined-only", action="store_true", help="Minion jobs: conjoined only")

    args = parser.parse_args(argv)

    if args.cmd == "list":
        data = discover_sources(args.userdata)
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print("Recur exports:")
            if not data["recur"]:
                print("  (none)")
            for r in data["recur"]:
                print(f"  [recur] L{r.get('level') or '?':>2}  {r['name']}  ::  {r['path']}")
            print("Saves:")
            if not data["saves"]:
                print("  (none)")
            for s in data["saves"]:
                loc = f" @ {s['location']}" if s.get("location") else ""
                print(f"  [save ] L{s.get('level') or '?':>2}  {s['name']}{loc}  ::  {s['path']}")
        return 0

    if args.cmd == "import":
        fighter = import_any(args.path)
        payload = fighter.to_dict()
        text = json.dumps(payload, indent=2 if args.pretty else None)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
            print(str(args.output))
        else:
            print(text)
        return 0

    if args.cmd == "art":
        fighter = import_any(args.path)
        include_b = not args.no_broodlings
        include_c = not args.no_conjoined
        payload = {
            "fighter": fighter.art_payload(
                include_broodlings=include_b,
                include_conjoined=include_c,
                broodling_limit=args.broodling_limit,
            ),
            "minions": [],
        }
        if args.minions:
            if args.followers_only:
                ib, ic, iff = False, False, True
            elif args.broodlings_only:
                ib, ic, iff = True, False, False
            elif args.conjoined_only:
                ib, ic, iff = False, True, False
            else:
                ib, ic, iff = include_b, include_c, True
            payload["minions"] = fighter.minion_art_payloads(
                include_broodlings=ib,
                include_conjoined=ic,
                include_followers=iff,
                limit=args.minion_limit,
            )
        text = json.dumps(payload, indent=2 if args.pretty else None)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
            print(str(args.output))
        else:
            print(text)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
