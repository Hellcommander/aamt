#!/usr/bin/env python3
"""Wire CustomRaceClassCreator C# systems into Starfield ArcaneConduit SPELs.

MagicPlus/Data XML is already imported. This pulls spell definitions that live
only in C# (Geomancy defaults, River/Terrain ops, Mana channels, signature
abilities, Vision/Noise, example wisps, spell fusion, dream/nightmare
rituals, altar/golem rituals). Feats stay on Elin classes/races — they are
never imported as SPELs.

  python elin_starfield_systems.py preview
  python elin_starfield_systems.py import
  python elin_starfield_systems.py import --then-rework
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_ELIN = Path(__file__).resolve().parent
_MOD = Path(
    r"E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator"
)
_CATALOG = Path(
    r"F:\SteamLibrary\steamapps\common\Starfield\ArcaneConduit\spells\catalog.json"
)
_REWORK = _ELIN / "elin_starfield_rework.py"

SYSTEM_SCHOOL = {
    "geomancy": "Gravitics",
    "river": "Osmotics",
    "terrain": "Gravitics",
    "mana": "Phasics",
    "pollution": "Entropy",
    "geoscience": "Gravitics",
    "element": "Pyrolysis",
    "animatedservant": "Synthetics",
    "golemancy": "Synthetics",
    "vision": "Photonics",
    "noise": "Atmospherics",
    "wisp": "Photonics",
    "spellfusion": "Bindings",
    "dream": "Phasics",
    "ritual": "Bindings",
    "summon": "Synthetics",
}

SYSTEM_ASSET = {
    "geomancy": "elinGeomancy",
    "river": "elinRiverMagic",
    "terrain": "elinTerrainMagic",
    "mana": "elinManaMagic",
    "pollution": "elinPollution",
    "geoscience": "elinGeoscience",
    "element": "elinElementMagic",
    "animatedservant": "elinAnimatedServant",
    "golemancy": "elinGolemancy",
    "vision": "elinVisionSystem",
    "noise": "elinNoiseSystem",
    "wisp": "elinWispMagic",
    "spellfusion": "elinSpellFusion",
    "dream": "elinDreamMagic",
    "ritual": "elinRitualMagic",
    "summon": "elinPactMagic",
}


def _pascal(name: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", name)
    return "".join(p[:1].upper() + p[1:] for p in parts) or "Spell"


def _sf_id(elin_id: str, name: str) -> str:
    body = _pascal(name) if name and name != elin_id else _pascal(elin_id)
    if not body.startswith("Elin"):
        body = "Elin" + body
    return body[:48]


def extract_geomancy() -> List[Dict[str, Any]]:
    """Parse InitializeDefaultGeomancy() DruidicSpell blocks from GeomancySystem.cs."""
    path = _MOD / "MagicPlus" / "GeomancySystem.cs"
    text = path.read_text(encoding="utf-8", errors="replace")
    # Isolate InitializeDefaultGeomancy body
    m = re.search(
        r"InitializeDefaultGeomancy\s*\(\s*\)\s*\{(.*?)"
        r"CustomRaceClassCreator\.Log\(\"GeomancySystem: Initialized",
        text,
        re.S,
    )
    body = m.group(1) if m else text
    rows: List[Dict[str, Any]] = []
    for block in re.finditer(
        r"SpellId\s*=\s*\"([^\"]+)\".*?"
        r"Name\s*=\s*\"([^\"]+)\".*?"
        r"Description\s*=\s*\"([^\"]+)\".*?"
        r"ManaCost\s*=\s*(\d+).*?"
        r"Power\s*=\s*(\d+)",
        body,
        re.S,
    ):
        elin_id, name, desc, mana, power = block.groups()
        tags = ["geomancy", "stone"]
        low = f"{name} {desc}".lower()
        for t in (
            "seismic",
            "earthquake",
            "tremor",
            "crystal",
            "petrif",
            "burrow",
            "wall",
            "spike",
            "pillar",
            "magnetic",
            "mineral",
            "ley",
        ):
            if t in low or t in elin_id:
                tags.append(t)
        rows.append(
            {
                "elin_id": elin_id,
                "name": name,
                "desc": desc,
                "system": "geomancy",
                "tags": tags,
                "mana": float(mana),
                "power": float(power),
                "source_file": "MagicPlus/GeomancySystem.cs",
            }
        )
    return rows


def extract_river() -> List[Dict[str, Any]]:
    ops = [
        ("river_carve_channel", "Carve Channel", "Cut a new river branch or canal through the terrain.", "field"),
        ("river_build_weir", "Build Weir", "Raise a low dam that pools water upstream.", "field"),
        ("river_construct_lock", "Construct Lock", "Gate a channel for controlled passage.", "ward"),
        ("river_divert_spring", "Divert Spring", "Reroute a water source into a new basin.", "field"),
        ("river_scour_bed", "Scour Bed", "Deepen the channel to increase flow speed.", "beam"),
        ("river_silt_deposit", "Silt Deposit", "Drop sediment to form banks and shoals.", "field"),
        ("river_whirlpool_call", "Whirlpool Call", "Summon a temporary whirling current.", "bloom"),
        ("river_blessing", "River Blessing", "Bind a river spirit to a stretch of water.", "cloak"),
    ]
    out = []
    for elin_id, name, desc, delivery in ops:
        out.append(
            {
                "elin_id": elin_id,
                "name": name,
                "desc": desc,
                "system": "river",
                "tags": ["river", "water", "hydro", delivery],
                "mana": 22.0,
                "power": 40.0,
                "delivery": delivery,
                "source_file": "MagicPlus/RiverMagic/RiverMagicDataModels.cs",
            }
        )
    return out


def extract_terrain() -> List[Dict[str, Any]]:
    ops = [
        ("terrain_sculpt", "Terrain Sculpt", "Raise or lower elevation in a sculpted patch.", "field"),
        ("terrain_channel", "Terrain Channel", "Carve ditches and waterways into the ground.", "field"),
        ("terrain_fill", "Terrain Fill", "Deposit soil, sand, or rubble to fill a volume.", "field"),
        ("terrain_surface_alter", "Surface Alter", "Rewrite surface tags across an area.", "field"),
        ("terrain_anchor", "Terrain Anchor", "Place a persistent terrain feature that holds shape.", "ward"),
        ("terrain_terraform_ritual", "Terraform Ritual", "Large-scale biome rewrite as a sustained ritual.", "beam"),
    ]
    out = []
    for elin_id, name, desc, delivery in ops:
        out.append(
            {
                "elin_id": elin_id,
                "name": name,
                "desc": desc,
                "system": "terrain",
                "tags": ["terrain", "earth", delivery],
                "mana": 24.0,
                "power": 45.0,
                "delivery": delivery,
                "source_file": "MagicPlus/TerrainMagic/TerrainMagicDataModels.cs",
            }
        )
    return out


def extract_mana() -> List[Dict[str, Any]]:
    """ManaMagic has no XML templates; wire the channel / cast archetypes."""
    ops = [
        ("mana_channel_stream", "Mana Channel Stream", "Hold to drain mana into a sustained stream.", "beam"),
        ("mana_burst", "Mana Burst", "Release a condensed mana pulse on impact.", "bloom"),
        ("mana_reserve_ward", "Mana Reserve Ward", "Hold a reserve shield fed by mana.", "ward"),
        ("mana_siphon_bolt", "Mana Siphon Bolt", "Bolt that steals mana on contact.", "bolt"),
    ]
    out = []
    for elin_id, name, desc, delivery in ops:
        out.append(
            {
                "elin_id": elin_id,
                "name": name,
                "desc": desc,
                "system": "mana",
                "tags": ["mana", "arcane", delivery],
                "mana": 18.0,
                "power": 35.0,
                "delivery": delivery,
                "source_file": "MagicPlus/ManaMagic/ManaMagicDataModels.cs",
            }
        )
    return out


def extract_pollution() -> List[Dict[str, Any]]:
    """Pollution is mostly a meter; expose castable residue effects."""
    ops = [
        ("pollution_dump", "Pollution Dump", "Dump toxic residue as a lingering hazard puddle.", "field"),
        ("pollution_purge", "Pollution Purge", "Burn off local pollution in a cleansing pulse.", "bloom"),
        ("pollution_smog_cloak", "Smog Cloak", "Wrap the caster in a choking smog aura.", "cloak"),
    ]
    out = []
    for elin_id, name, desc, delivery in ops:
        out.append(
            {
                "elin_id": elin_id,
                "name": name,
                "desc": desc,
                "system": "pollution",
                "tags": ["pollution", "toxic", "slime", delivery],
                "mana": 20.0,
                "power": 38.0,
                "delivery": delivery,
                "source_file": "MagicPlus/Pollution/ManaPollutionManager.cs",
            }
        )
    return out


def extract_geoscience() -> List[Dict[str, Any]]:
    ops = [
        ("geoscience_core_sample", "Core Sample", "Fire a dense geological core sample pellet.", "bolt"),
        ("geoscience_resonance_scan", "Resonance Scan", "Channel a scanning beam that marks mineral veins.", "beam"),
        ("geoscience_geode_burst", "Geode Burst", "Detonate a geode shell into a crystal field.", "bloom"),
        ("geoscience_stratum_wall", "Stratum Wall", "Raise a layered stone wall from the strata.", "ward"),
    ]
    out = []
    for elin_id, name, desc, delivery in ops:
        out.append(
            {
                "elin_id": elin_id,
                "name": name,
                "desc": desc,
                "system": "geoscience",
                "tags": ["geoscience", "earth", "crystal", delivery],
                "mana": 22.0,
                "power": 42.0,
                "delivery": delivery,
                "source_file": "MagicPlus/Geoscience/GeoscienceFacade.cs",
            }
        )
    return out


def _ops(
    system: str,
    source_file: str,
    extra_tags: List[str],
    rows: List[Tuple[str, str, str, str, float, float]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for elin_id, name, desc, delivery, mana, power in rows:
        out.append(
            {
                "elin_id": elin_id,
                "name": name,
                "desc": desc,
                "system": system,
                "tags": extra_tags + [delivery],
                "mana": mana,
                "power": power,
                "delivery": delivery,
                "source_file": source_file,
            }
        )
    return out


def extract_signature() -> List[Dict[str, Any]]:
    """Hardcoded defaults from SignatureAbilityRegistry + ElementContentExpansion."""
    rows = _ops(
        "element",
        "MagicPlus/ElementMagic/SignatureAbilityRegistry.cs",
        ["signature", "element"],
        [
            ("fire_inferno_burst", "Inferno Burst", "Explosive fire attack that deals area damage and applies burn.", "bloom", 40, 120),
            ("water_tidal_step", "Tidal Step", "Dash through a wet trail, healing as you go.", "dash", 30, 30),
            ("lightning_chain_bolt", "Chain Bolt", "Lightning that chains between targets on conductive surfaces.", "bolt", 35, 100),
            ("earth_terraform", "Terraform", "Raise earth walls as cover or obstacles.", "ward", 25, 40),
            ("wind_tempest_rush", "Tempest Rush", "Rush forward with wind force, knocking back enemies in your path.", "dash", 35, 80),
            ("ice_frost_barrier", "Frost Barrier", "Raise an ice wall that blocks shots and slows enemies.", "ward", 45, 50),
            ("light_radiant_burst", "Radiant Burst", "Light nova that heals allies and burns undead.", "bloom", 50, 100),
            ("dark_shadow_step", "Shadow Step", "Teleport through shadows, leaving a clone and gaining stealth.", "dash", 40, 40),
            ("earth_stone_shield", "Stone Shield", "Wrap the caster in a stone barrier that absorbs damage.", "cloak", 45, 45),
        ],
    )
    schools = {
        "fire_inferno_burst": "Pyrolysis",
        "water_tidal_step": "Osmotics",
        "lightning_chain_bolt": "Voltaics",
        "earth_terraform": "Gravitics",
        "wind_tempest_rush": "Atmospherics",
        "ice_frost_barrier": "Cryonics",
        "light_radiant_burst": "Celestial",
        "dark_shadow_step": "Abyssal",
        "earth_stone_shield": "Gravitics",
    }
    for row in rows:
        if row["elin_id"] in schools:
            row["school"] = schools[row["elin_id"]]
    return rows


def extract_vision() -> List[Dict[str, Any]]:
    return _ops(
        "vision",
        "VisionSystem/CompanionScoutingProfiles.cs",
        ["vision", "scout"],
        [
            ("vision_scry", "Scry", "Channel a scrying beam that marks what it sees.", "beam", 18, 20),
            ("vision_reveal", "Reveal Field", "Pulse a detection field that strips stealth.", "field", 22, 28),
            ("vision_mark", "Mark Target", "Tag a target with a lingering scout mark.", "bolt", 12, 18),
        ],
    )


def extract_noise() -> List[Dict[str, Any]]:
    return _ops(
        "noise",
        "NoiseSystem/NoiseSystemConfig.cs",
        ["noise", "sound"],
        [
            ("noise_sonar_pulse", "Sonar Pulse", "Emit a ringing pulse that reveals nearby bodies.", "bloom", 16, 22),
            ("noise_shout", "Shout", "Throw a loud shock that alerts and staggers.", "bloom", 20, 35),
            ("noise_silence_ward", "Silence Ward", "Dampen local sound inside a hush ward.", "ward", 18, 20),
        ],
    )


def extract_wisp_examples() -> List[Dict[str, Any]]:
    """ExampleWispTemplates.xml sits outside MagicPlus/Data; treat as summons."""
    return _ops(
        "wisp",
        "MagicPlus/WispMagic/ExampleWispTemplates.xml",
        ["wisp", "summon"],
        [
            ("wisp_scout", "Wisp Scout", "Nimble wisp that reveals hidden areas and marks enemies.", "summon", 5, 20),
            ("wisp_beacon", "Wisp Beacon", "Steady wisp that emits mana regen and stealth-dampen auras.", "summon", 10, 28),
            ("wisp_lumen_guard", "Lumen Guard", "Aggressive wisp that stuns and interrupts with light pulses.", "summon", 8, 32),
            ("wisp_echo", "Echo Wisp", "Mystical wisp that records and replays environmental memories.", "summon", 6, 22),
            ("wisp_ritual_conduit", "Ritual Conduit", "Altar-bound wisp that amplifies ritual potency.", "summon", 15, 40),
            ("wisp_scout_elite", "Elite Wisp Scout", "Advanced scout wisp with phase vision and tracking.", "summon", 12, 34),
        ],
    )


def extract_spellfusion() -> List[Dict[str, Any]]:
    """SpellFusion is a recipe mixer; expose the two castable fusion acts."""
    return _ops(
        "spellfusion",
        "MagicPlus/SpellFusionSystem.cs",
        ["fusion", "element"],
        [
            ("spellfusion_merge", "Spell Fusion Merge", "Fuse two elemental payloads into a hybrid burst.", "bloom", 32, 70),
            ("spellfusion_overclock", "Fusion Overclock", "Overclock a fused payload into a sustained stream.", "beam", 28, 55),
        ],
    )


def extract_nightmares() -> List[Dict[str, Any]]:
    """NightmareSystem hardcoded entity templates — summons, not feats."""
    return _ops(
        "dream",
        "MagicPlus/Dream/NightmareSystem.cs",
        ["nightmare", "summon"],
        [
            ("nightmare_shadow", "Shadow Nightmare", "Call a dark shadow out of the nightmare realm.", "summon", 22, 80),
            ("nightmare_corruption_horror", "Corruption Horror", "Call a corruption-born nightmare that blasts and fears.", "summon", 36, 200),
        ],
    )


def extract_dream_rituals() -> List[Dict[str, Any]]:
    return _ops(
        "dream",
        "MagicPlus/Dream/DreamRitualSystem.cs",
        ["dream", "ritual"],
        [
            ("ritual_nightmare_seed", "Nightmare Seed", "Plant a nightmare seed that blooms into a timed dream event.", "field", 50, 60),
        ],
    )


def extract_altar_rituals() -> List[Dict[str, Any]]:
    return _ops(
        "ritual",
        "MagicPlus/RitualAltarSystem.cs",
        ["ritual", "altar"],
        [
            ("ritual_summon_elemental", "Summon Elemental", "Complete an altar circle and call a fire elemental servant.", "summon", 50, 100),
            ("ritual_blessing", "Ritual of Blessing", "Altar blessing that fortifies nearby allies.", "cloak", 20, 50),
        ],
    )


def extract_golem_rituals() -> List[Dict[str, Any]]:
    return _ops(
        "golemancy",
        "MagicPlus/Golemancy/GolemRitualAlterations.cs",
        ["golem", "ritual"],
        [
            ("ritual_golem_enhancement", "Golem Enhancement", "Permanently enhance a bonded construct's strength and hide.", "cloak", 28, 50),
            ("ritual_golem_elemental_infusion", "Elemental Infusion", "Infuse a construct with fire, ice, and lightning.", "cloak", 32, 55),
            ("ritual_golem_masterwork", "Masterwork Transformation", "Rewrite a construct into a masterwork body.", "cloak", 40, 80),
        ],
    )


def extract_dream_fusion() -> List[Dict[str, Any]]:
    """DreamSpellFusionIntegration result SPELs (recipes are commented; results still named)."""
    rows = _ops(
        "dream",
        "MagicPlus/Dream/DreamSpellFusionIntegration.cs",
        ["dream", "fusion"],
        [
            ("dream_phantasmal_fire", "Phantasmal Fire", "Illusion fire that still burns.", "bolt", 24, 55),
            ("dream_lucid_dreamstep", "Lucid Dreamstep", "Enhanced dreamstep with lucid control.", "dash", 22, 40),
            ("dream_nightmare_bolt", "Nightmare Bolt", "Necrotic dream bolt that seeds fear.", "bolt", 26, 50),
            ("dream_nature_dream", "Nature Dream", "Dream of growth that unfolds as a living field.", "field", 24, 45),
        ],
    )
    schools = {
        "dream_phantasmal_fire": "Pyrolysis",
        "dream_lucid_dreamstep": "Phasics",
        "dream_nightmare_bolt": "Abyssal",
        "dream_nature_dream": "Vitalics",
    }
    for row in rows:
        if row["elin_id"] in schools:
            row["school"] = schools[row["elin_id"]]
    return rows


def extract_dream_servitors() -> List[Dict[str, Any]]:
    """Evolved dream servitor bodies as summons (evolution itself is not a feat)."""
    return _ops(
        "dream",
        "MagicPlus/Dream/DreamServitorEvolutionSystem.cs",
        ["dream", "summon"],
        [
            ("dream_guardian", "Dream Guardian", "Summon the evolved guardian form of a dream wisp.", "summon", 28, 70),
            ("dream_archon", "Dream Archon", "Summon a dream archon, the peak servitor form.", "summon", 40, 110),
        ],
    )


def extract_summon_fallbacks() -> List[Dict[str, Any]]:
    """SummoningSystem hardcoded templates not already in MagicPlus XML."""
    return _ops(
        "golemancy",
        "MagicPlus/SummoningSystem.cs",
        ["summon", "construct"],
        [
            ("tmpl_golem_construct", "Animated Construct", "Magically animated construct servant (summon template, not a class feat).", "summon", 30, 55),
        ],
    )


def all_system_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for extractor in (
        extract_geomancy,
        extract_river,
        extract_terrain,
        extract_mana,
        extract_pollution,
        extract_geoscience,
        extract_signature,
        extract_vision,
        extract_noise,
        extract_wisp_examples,
        extract_spellfusion,
        extract_nightmares,
        extract_dream_rituals,
        extract_altar_rituals,
        extract_golem_rituals,
        extract_dream_fusion,
        extract_dream_servitors,
        extract_summon_fallbacks,
    ):
        for row in extractor():
            if row["elin_id"] in seen:
                continue
            seen.add(row["elin_id"])
            rows.append(row)
    return rows


def row_to_spell(row: Dict[str, Any], existing: Set[str]) -> Dict[str, Any]:
    sid = _sf_id(row["elin_id"], row["name"])
    base = sid
    n = 2
    while sid in existing:
        sid = f"{base}{n}"
        n += 1
    existing.add(sid)
    school = row.get("school") or SYSTEM_SCHOOL[row["system"]]
    cost = max(8.0, min(48.0, round(float(row["mana"]) * 0.55, 1)))
    magnitude = max(8.0, min(60.0, round(float(row["power"]) * 0.45, 1)))
    delivery = row.get("delivery") or "bolt"
    # ElinRuntime owns delivery via profiles after rework; seed behaviors lightly.
    behaviors = ["elin"]
    return {
        "id": sid,
        "name": row["name"],
        "school": school,
        "inspired_by": f"CustomRaceClassCreator {row['system']} ({row['elin_id']})",
        "archetype": "contact",
        "magnitude": magnitude,
        "area": 180 if delivery in ("field", "bloom") else 0,
        "duration": 0,
        "cost": cost,
        "behaviors": behaviors,
        "desc": row["desc"]
        + " Starfield Conduit: real-time gun delivery (not Elin tile turns).",
        "source": "elin",
        "elin_id": row["elin_id"],
        "elin_system": row["system"],
        "elin_file": row["source_file"],
        "asset_hint": SYSTEM_ASSET[row["system"]],
        "tags": row.get("tags") or [],
        "life": 4.0,
        "starfield_seed": {"delivery": delivery},
    }


def build_new(cat: dict) -> List[Dict[str, Any]]:
    have_elin = {
        s.get("elin_id")
        for s in cat.get("spells") or []
        if s.get("source") == "elin" and s.get("elin_id")
    }
    existing = {s.get("id") for s in cat.get("spells") or [] if s.get("id")}
    new: List[Dict[str, Any]] = []
    for row in all_system_rows():
        if row["elin_id"] in have_elin:
            continue
        # Feats belong to Elin classes/races. Never SPELs.
        if str(row["elin_id"]).startswith("feat_"):
            continue
        new.append(row_to_spell(row, existing))
    return new


def cmd_preview(_: argparse.Namespace) -> int:
    cat = json.loads(_CATALOG.read_text(encoding="utf-8"))
    rows = all_system_rows()
    new = build_new(cat)
    print(f"system rows extractable: {len(rows)}")
    print(f"new SPELs to import: {len(new)}\n")
    by: Dict[str, int] = {}
    for s in new:
        by[s["elin_system"]] = by.get(s["elin_system"], 0) + 1
        print(
            f"  {s['id']:<28} {s['name']:<22} {s['school']:<14} "
            f"<- {s['elin_id']}"
        )
    print("\nby system:")
    for k in sorted(by):
        print(f"  {k}: {by[k]}")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    cat = json.loads(_CATALOG.read_text(encoding="utf-8"))
    new = build_new(cat)
    if not new:
        print("nothing new to import")
        return 0
    cat["spells"].extend(new)
    for spell in cat["spells"]:
        if spell.get("source") != "elin" or spell.get("elin_system"):
            continue
        eid = str(spell.get("elin_id") or "")
        if eid.startswith("hybrid_"):
            spell["elin_system"] = "necromancy"
        elif "dream" in eid:
            spell["elin_system"] = "dream"
    meta = cat.setdefault("meta", {})
    bridge = meta.setdefault("elin_bridge", {})
    bridge["systems_tool"] = "Tools/Elin/elin_starfield_systems.py"
    bridge["systems_imported"] = int(bridge.get("systems_imported") or 0) + len(new)
    bridge["imported"] = len([s for s in cat["spells"] if s.get("source") == "elin"])
    _CATALOG.write_text(json.dumps(cat, indent=2) + "\n", encoding="utf-8")
    print(f"imported {len(new)} system SPELs (elin total {bridge['imported']})")
    if args.then_rework:
        for cmd in (
            ["rework", "--system", "all"],
            ["profiles", "--system", "all"],
            ["register-meshes", "--system", "all"],
        ):
            print(">>", " ".join(cmd))
            r = subprocess.run([sys.executable, str(_REWORK), *cmd], cwd=str(_ELIN))
            if r.returncode != 0:
                return r.returncode
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("preview")
    p_imp = sub.add_parser("import")
    p_imp.add_argument(
        "--then-rework",
        action="store_true",
        help="run elin_starfield_rework rework+profiles+register-meshes after import",
    )
    args = ap.parse_args()
    if args.cmd == "preview":
        return cmd_preview(args)
    return cmd_import(args)


if __name__ == "__main__":
    raise SystemExit(main())
