#!/usr/bin/env python3
"""Port Magi-Tech spellshapes (rollable mutations) and unique spells into
Starfield ArcaneConduit.

Magi-Tech's identity is not a giant unique-spell roster. Most of its casts are
warped versions of existing content. What it *does* author is:

  * spellshapes — mutations the backend rolls onto a living shot
    (pierce, split, bounce, gravity funnel, quantum leap, …)
  * a short unique-spell list (chaos / temporal / quantum originals)

Starfield cannot rewrite .mesh collision hulls. MagiTechRuntime interprets the
exported MagiTechModifiers.json as per-shot mutation: Havok primitive radius
(scale), collision layer, pierce/bounce/homing, lifeScale morph, material, and
secondary spawn. Dual-cast hangs a MagiTech shape on any Conduit delivery.

  python magitech_starfield_spell_bridge.py preview
  python magitech_starfield_spell_bridge.py import
  python magitech_starfield_spell_bridge.py import --dry-run

Then in ArcaneConduit:
  python tools/spell_design.py validate
  python tools/spell_design.py compile
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_MOD = Path(r"F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery")
_SF_CATALOG = Path(
    r"F:\SteamLibrary\steamapps\common\Starfield\ArcaneConduit\spells\catalog.json"
)
_SF_SPELLS = _SF_CATALOG.parent
_EXPORT = Path(
    r"F:\SteamLibrary\steamapps\common\Starfield\ArcaneConduit\assets\MagiTechExport"
)

# Magi-Tech originals — not warped fireball/ice/lightning clones.
UNIQUE_SHAPE_IDS = {
    "quantumLeap",
    "slingshotTether",
    "chamberBounce",
    "massOscillator",
    "gravityFunnel",
    "podTrail",
    "orbitalShard",
    "velocityInvert",
    "darkMatterPull",
    "solarFlareImpulse",
    "cosmicWebTether",
    "nebulaDrag",
    "singularityPulse",
    "stellarShardBurst",
    "voidPhase",
    "cosmicSpin",
}

# Unique Magi-Tech *gun* deliveries (alchemical launcher). Segmented whip /
# flail / chain / nunchaku / rope are physical melee WEAPs, not SPELs — see
# PHYSICAL_WEAPONS. Do not hang Arc_Behavior_Flail or HostOfChains on those.
UNIQUE_WEAPONS = [
    {
        "id": "alchemical_launcher",
        "name": "Alchemical Launcher",
        "description": (
            "Magi-Tech alchemical grenade launcher: lobs a 3-slot reagent shell "
            "on a ballistic fuse (impact / timer / proximity). No spellstone. "
            "First Starfield pass is LobbingGrenade plus MagiTechRuntime ShotPatch. "
            "Dual-cast up to two specialized Magi-Tech grenades onto this launcher "
            "to mix reagents (synergy / opposition / planet temperature)."
        ),
        "family": "weapon",
        "school": "Synthetics",
        "delivery": "lobbing_grenade",
        "payloads": [],
        "behaviors_force": ["magitech", "lobbing_grenade"],
        "archetype": "contact",
        "material": "volatile",
        "hazard": "Arc_Hazd_LobbingGrenade",
        "cost": 18.0,
        "magnitude": 16.0,
        "area": 240,
        "duration": 0,
        "params": {"scale": 1.45, "bounceAdd": 1.0},
        "source_file": "items/weapons/alchemicalgrenadelauncher/",
    },
    {
        "id": "grenade_fire",
        "name": "Incendiary Grenade",
        "description": "Specialized Magi-Tech incendiary shell. Lobs, then blooms fire.",
        "family": "weapon",
        "school": "Pyrolysis",
        "delivery": "lobbing_grenade",
        "payloads": ["bloom"],
        "behaviors_force": ["magitech", "lobbing_grenade", "bloom"],
        "archetype": "contact",
        "material": "ember",
        "hazard": "Arc_Hazd_LobbingGrenade",
        "cost": 14.0,
        "magnitude": 14.0,
        "area": 200,
        "duration": 0,
        "params": {"scale": 1.35},
        "reagent": "fire",
        "source_file": "items/ammo/specializedgrenades/grenade_fire.item",
    },
    {
        "id": "grenade_frost",
        "name": "Frost Grenade",
        "description": "Specialized Magi-Tech frost shell. Lobs, then slows the blast volume.",
        "family": "weapon",
        "school": "Cryonics",
        "delivery": "lobbing_grenade",
        "payloads": ["slow"],
        "behaviors_force": ["magitech", "lobbing_grenade", "slow"],
        "archetype": "slow",
        "material": "slush",
        "hazard": "Arc_Hazd_LobbingGrenade",
        "cost": 14.0,
        "magnitude": 12.0,
        "area": 200,
        "duration": 4,
        "params": {"scale": 1.35},
        "reagent": "frost",
        "source_file": "items/ammo/specializedgrenades/grenade_frost.item",
    },
    {
        "id": "grenade_acid",
        "name": "Acid Grenade",
        "description": "Specialized Magi-Tech acid shell. Lobs, then stands a caustic field.",
        "family": "weapon",
        "school": "Osmotics",
        "delivery": "lobbing_grenade",
        "payloads": ["field"],
        "behaviors_force": ["magitech", "lobbing_grenade", "field"],
        "archetype": "contact",
        "material": "caustic_vapor",
        "hazard": "Arc_Hazd_LobbingGrenade",
        "cost": 15.0,
        "magnitude": 13.0,
        "area": 220,
        "duration": 6,
        "params": {"scale": 1.4},
        "reagent": "acid",
        "source_file": "items/ammo/specializedgrenades/grenade_acid.item",
    },
    {
        "id": "grenade_storm",
        "name": "Storm Grenade",
        "description": "Specialized Magi-Tech storm shell. Lobs, then chains lightning from the burst.",
        "family": "weapon",
        "school": "Voltaics",
        "delivery": "lobbing_grenade",
        "payloads": ["chain"],
        "behaviors_force": ["magitech", "lobbing_grenade", "chain"],
        "archetype": "em",
        "material": "plasma",
        "hazard": "Arc_Hazd_LobbingGrenade",
        "cost": 16.0,
        "magnitude": 15.0,
        "area": 240,
        "duration": 0,
        "params": {"scale": 1.4},
        "reagent": "storm",
        "source_file": "items/ammo/specializedgrenades/grenade_storm.item",
    },
    {
        "id": "grenade_shadow",
        "name": "Shadow Grenade",
        "description": "Specialized Magi-Tech shadow shell. Lobs, then phase-rips the burst volume.",
        "family": "weapon",
        "school": "Entropy",
        "delivery": "lobbing_grenade",
        "payloads": ["shadowphase"],
        "behaviors_force": ["magitech", "lobbing_grenade", "shadowphase"],
        "archetype": "phase",
        "material": "tar",
        "hazard": "Arc_Hazd_LobbingGrenade",
        "cost": 16.0,
        "magnitude": 14.0,
        "area": 220,
        "duration": 0,
        "params": {"scale": 1.35},
        "reagent": "shadow",
        "source_file": "items/ammo/specializedgrenades/grenade_shadow.item",
    },
    {
        "id": "flamelord_grenadegun",
        "name": "Flamelord Grenade Gun",
        "description": (
            "Legendary Magi-Tech Flamelord launcher. Faster lob, ember hull, "
            "bloom on fuse. Still LobbingGrenade plus magitech, not a new delivery."
        ),
        "family": "weapon",
        "school": "Pyrolysis",
        "delivery": "lobbing_grenade",
        "payloads": ["bloom"],
        "behaviors_force": ["magitech", "lobbing_grenade", "bloom"],
        "archetype": "contact",
        "material": "ember",
        "hazard": "Arc_Hazd_LobbingGrenade",
        "cost": 24.0,
        "magnitude": 22.0,
        "area": 280,
        "duration": 0,
        "params": {"scale": 1.6, "speedMult": 1.25, "damageMult": 1.35},
        "reagent": "fire",
        "source_file": "items/weapons/alchemicalgrenadelauncher/flamelord_grenadegun.item",
    },
]

# Physical Magi-Tech melee. Not SPELs. Whip and flail are different weapons.
DROP_PHYSICAL_WEAPON_SPELLS = {
    "segmented_whip",
    "segmented_flail",
    "segmented_chain",
}

PHYSICAL_WEAPONS = [
    {
        "id": "whip",
        "name": "Segmented Whip",
        "kind": "physical_weap",
        "starfield_form": "WEAP melee (one-handed, long reach)",
        "not": ["Arc_Behavior_Flail", "SPEL", "graviton core", "Host of Chains"],
        "identity": (
            "Flexible tapered lash. Damage is tip speed after a crack travels "
            "down thin leather/rope segments. Long reach, fast, light hits. "
            "High joint flexibility, many short thin segments, optional spike tip."
        ),
        "starbound": {
            "weaponType": "WHIP",
            "segmentCount": 20,
            "segmentRadius": 0.03,
            "jointFlexibility": 0.85,
            "taper": "LINEAR",
            "material": "LEATHER",
        },
        "starfield": {
            "first_pass": (
                "sfform.weap from scratch: Arc_Weap_MagitechWhip. One-hand sword "
                "type, reach 1.8, very fast. Not a clone, not a Flail SPEL."
            ),
            "edid": "Arc_Weap_MagitechWhip",
            "dnam": {
                "reach": 1.8,
                "speed": 1.25,
                "damage": 14.0,
                "stagger": 1,
                "hands": "one",
                "weapon_type": 1,
            },
        },
    },
    {
        "id": "flail",
        "name": "Segmented Flail",
        "kind": "physical_weap",
        "starfield_form": "WEAP melee (heavy, short chain + striking head)",
        "not": ["whip", "Arc_Behavior_Flail SPEL", "nunchaku"],
        "identity": (
            "Rigid handle, short chain, heavy striking head. Damage is mass times "
            "head speed after a wind-up. Slow, hard stagger. Few thick segments, "
            "weight at the free end. A whip cracks; a flail smashes."
        ),
        "starbound": {
            "weaponType": "FLAIL",
            "endAttachment": "WEIGHT",
            "material": "STEEL",
            "jointFlexibility": "low-medium",
        },
        "starfield": {
            "first_pass": (
                "sfform.weap from scratch: Arc_Weap_MagitechFlail. One-hand mace "
                "type, reach 1.05, slow, stagger 3. Physical item. "
                "Arc_Behavior_Flail is a magic graviton ball — do not reuse it."
            ),
            "edid": "Arc_Weap_MagitechFlail",
            "dnam": {
                "reach": 1.05,
                "speed": 0.75,
                "damage": 28.0,
                "stagger": 3,
                "hands": "one",
                "weapon_type": 4,
            },
        },
    },
    {
        "id": "nunchaku",
        "name": "Segmented Nunchaku",
        "kind": "physical_weap",
        "starfield_form": "WEAP melee (two short bars, one joint)",
        "not": ["whip", "flail"],
        "identity": (
            "Two handheld rigid bars linked by one short joint. Close-in and fast. "
            "Not a whip (no long lash) and not a flail (no free-flying heavy head)."
        ),
        "starbound": {"weaponType": "NUNCHAKU"},
        "starfield": {
            "first_pass": "sfform.weap: Arc_Weap_MagitechNunchaku. Dagger type, reach 0.55, very fast.",
            "edid": "Arc_Weap_MagitechNunchaku",
            "dnam": {
                "reach": 0.55,
                "speed": 1.4,
                "damage": 10.0,
                "stagger": 1,
                "hands": "one",
                "weapon_type": 2,
            },
        },
    },
    {
        "id": "rope",
        "name": "Segmented Rope",
        "kind": "physical_weap",
        "starfield_form": "WEAP melee (whip family, rope material)",
        "not": ["flail"],
        "identity": (
            "Flexible lash like a whip, rope instead of leather. Slower crack, "
            "more wrap. Same family as whip, still not a flail."
        ),
        "starbound": {"weaponType": "ROPE", "material": "ROPE"},
        "starfield": {
            "first_pass": "sfform.weap: Arc_Weap_MagitechRope. Whip-class, reach 1.7, medium speed.",
            "edid": "Arc_Weap_MagitechRope",
            "dnam": {
                "reach": 1.7,
                "speed": 1.0,
                "damage": 12.0,
                "stagger": 2,
                "hands": "one",
                "weapon_type": 1,
            },
        },
    },
    {
        "id": "chain",
        "name": "Segmented Chain",
        "kind": "physical_weap",
        "starfield_form": "WEAP melee (metal links, wrap/constrict)",
        "not": ["Arc_Behavior_HostOfChains", "SPEL", "whip", "flail"],
        "identity": (
            "Metal links you swing as a weapon. Heavier than a whip, no free-flying "
            "head like a flail. Host of Chains is a magic tether SPELL — not this."
        ),
        "starbound": {"weaponType": "CHAIN", "material": "CHAIN_METAL"},
        "starfield": {
            "first_pass": "sfform.weap: Arc_Weap_MagitechChain. Two-hand sword type, reach 1.4.",
            "edid": "Arc_Weap_MagitechChain",
            "dnam": {
                "reach": 1.4,
                "speed": 0.9,
                "damage": 22.0,
                "stagger": 2,
                "hands": "two",
                "weapon_type": 5,
            },
        },
    },
]

# Dual-cast Magi-Tech grenade mix. MagiTechRuntime reads this from
# MagiTechModifiers.json. Dual-cast up to 3 reagent shells onto the launcher.
MAGITECH_REAGENTS = {
    "fire": {
        "material": "ember",
        "tempBias": 1.0,
        "synergies": {"storm": 1.30, "acid": 1.20},
        "oppositions": {"frost": 0.30, "shadow": 0.20},
    },
    "frost": {
        "material": "slush",
        "tempBias": -1.0,
        "synergies": {"shadow": 1.15, "storm": 1.10},
        "oppositions": {"fire": 0.30, "acid": 0.15},
    },
    "acid": {
        "material": "caustic_vapor",
        "tempBias": 0.0,
        "synergies": {"fire": 1.20, "storm": 1.15},
        "oppositions": {"frost": 0.15},
    },
    "storm": {
        "material": "plasma",
        "tempBias": 0.2,
        "synergies": {"fire": 1.30, "shadow": 1.25, "acid": 1.15},
        "oppositions": {},
    },
    "shadow": {
        "material": "tar",
        "tempBias": -0.3,
        "synergies": {"storm": 1.25, "frost": 1.15},
        "oppositions": {"fire": 0.20},
    },
}

UNIQUE_SPELLS = [
    {
        "id": "chaos_bolt",
        "name": "Chaos Bolt",
        "description": "A Magi-Tech original: the shot tears a void rift as it flies.",
        "family": "megaform",
        "school": "Entropy",
        "delivery": "shadow_vortex",
        "payloads": ["devouring_chaos", "wildmagic"],
        "archetype": "contact",
        "material": "tar",
        "cost": 22.0,
        "magnitude": 18.0,
        "area": 280,
        "duration": 6,
    },
    {
        "id": "temporal_sphere",
        "name": "Temporal Sphere",
        "description": "A Magi-Tech original: a hanging bubble that freezes local time.",
        "family": "megaform",
        "school": "Phasics",
        "delivery": "slowtime",
        "payloads": ["shadowphase"],
        "archetype": "phase",
        "material": "prismatic_solvent",
        "cost": 24.0,
        "magnitude": 12.0,
        "area": 320,
        "duration": 8,
    },
    {
        "id": "quantum_wave",
        "name": "Quantum Wave",
        "description": "A Magi-Tech original: probability-shift wave that hops dimension on contact.",
        "family": "megaform",
        "school": "Phasics",
        "delivery": "pulse",
        "payloads": ["shadowphase", "forking"],
        "archetype": "phase",
        "material": "plasma",
        "cost": 20.0,
        "magnitude": 16.0,
        "area": 240,
        "duration": 0,
    },
]

SHAPE_CONFIGS = [
    ("quantumPhysicsSpellShapes.json", "quantum"),
    ("cosmicPhysicsSpellShapes.json", "cosmic"),
    ("meleeCombatSpellShapes.json", "melee"),
    ("exoticPhysicsSpellShapes.json", "exotic"),
    ("enhancedPhysicsSpellShapes.json", "enhanced"),
    ("advancedPhysicsSpellShapes.json", "advanced"),
    ("advancedPhysicsSpellShapesV2.json", "advanced_v2"),
    ("advancedPhysicsSpellShapesV3.json", "advanced_v3"),
    ("dynamicPhysicsSpellShapes.json", "dynamic_physics"),
    ("dynamicSpellShapes.json", "dynamic"),
    ("physicsOnlySpellShapes.json", "physics_only"),
    ("balancedSpellShapes.json", "balanced"),
]

# Skip vanilla-clone / example shapes.
SKIP_IDS = {
    "fireball",
    "ice_spike",
    "lightning_bolt",
    "earth_pillar",
    "magic_missile",
    "arcane_burst",
    "mystic_beam",
    "basic_projectile",
    "area_burst",
    "direct_beam",
}

FAMILY_SCHOOL = {
    "quantum": "Phasics",
    "cosmic": "Celestial",
    "melee": "Kinetics",
    "exotic": "Entropy",
    "enhanced": "Synthetics",
    "advanced": "Gravitics",
    "advanced_v2": "Gravitics",
    "advanced_v3": "Atmospherics",
    "dynamic_physics": "Kinetics",
    "dynamic": "Voltaics",
    "physics_only": "Kinetics",
    "balanced": "Bindings",
    "mods": "Bindings",
    "wild": "Entropy",
    "megaform": "Phasics",
}

TOKEN_BEHAVIOR = [
    (("pierce", "piercing", "rail"), ["piercing"]),
    (("split", "fork", "spread"), ["forking"]),
    (("homing", "seek", "guided"), ["seeking"]),
    (("bounce", "ricochet", "rebound"), ["bounce"]),
    (("orbit", "orbital"), ["orbit"]),
    (("spiral", "helix", "spin"), ["spirally"]),
    (("chain", "spark"), ["chain"]),
    (("explode", "burst", "impulse", "nova"), ["bloom"]),
    (("gravity", "well", "funnel", "pull", "singularity", "dark matter"), ["well", "gravity_matrix"]),
    (("vortex", "tornado", "centrifuge"), ["mini_twister"]),
    (("magnetic",), ["magnetic_twister"]),
    (("tether", "slingshot", "rope", "web"), ["flail"]),
    (("leap", "teleport", "phase", "void phase"), ["shrinkwarp", "shadowphase"]),
    (("slow", "temporal", "dilation", "time"), ["slowtime"]),
    (("freeze", "frost", "ice"), ["slow"]),
    (("echo", "duplicate"), ["forking"]),
    (("shatter", "fragment", "chip", "scatter"), ["cluster"]),
    (("hover", "float"), ["lift"]),
    (("shockwave", "stomp", "pulse"), ["pulse"]),
    (("beam", "net"), ["beam"]),
    (("imbue", "wield", "swing", "melee"), ["imbue"]),
    (("sticky", "stick", "surface"), ["embed"]),
    (("chaos", "wild", "chaotic"), ["wildmagic"]),
    (("overgrowth", "grow", "swell", "oscillat"), ["burgeoning_growth"]),
]


def _pascal(name: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", name)
    return "".join(p[:1].upper() + p[1:] for p in parts) or "Shape"


def _sf_id(raw_id: str, name: str) -> str:
    base = "Magitech" + _pascal(name or raw_id)
    if not base.isidentifier():
        base = "Magitech" + re.sub(r"[^A-Za-z0-9_]", "", base)
    if base[0].isdigit():
        base = "Mt_" + base
    return base


def _blob(*parts: str) -> str:
    return " ".join(p.lower() for p in parts if p)


def _has_any(blob: str, tokens: tuple[str, ...]) -> bool:
    return any(t in blob for t in tokens)


def _behaviors(blob: str, available: Set[str], extra: List[str]) -> List[str]:
    out: List[str] = []

    def take(b: str) -> None:
        if b in available and b not in out:
            out.append(b)

    take("magitech")
    for b in extra:
        take(b)
    for tokens, behs in TOKEN_BEHAVIOR:
        if _has_any(blob, tokens):
            for b in behs:
                take(b)
    return out[:4]


def _school(family: str, blob: str) -> str:
    if _has_any(blob, ("void", "chaos", "corrupt", "entropy")):
        return "Entropy"
    if _has_any(blob, ("ice", "freeze", "frost", "cold")):
        return "Cryonics"
    if _has_any(blob, ("fire", "solar", "flare", "heat")):
        return "Pyrolysis"
    if _has_any(blob, ("lightning", "shock", "spark", "chain")):
        return "Voltaics"
    if _has_any(blob, ("gravity", "mass", "orbit", "pull", "funnel")):
        return "Gravitics"
    if _has_any(blob, ("quantum", "phase", "temporal", "probability")):
        return "Phasics"
    if _has_any(blob, ("cosmic", "stellar", "nebula", "dark matter")):
        return "Celestial"
    if _has_any(blob, ("wind", "gust", "tornado", "vortex")):
        return "Atmospherics"
    return FAMILY_SCHOOL.get(family, "Bindings")


def _archetype(blob: str, kind: str) -> str:
    if kind == "modifier":
        if _has_any(blob, ("heal", "efficiency")):
            return "mend"
        if _has_any(blob, ("slow", "freeze", "temporal")):
            return "slow"
        if _has_any(blob, ("shock", "lightning", "spark")):
            return "em"
        if _has_any(blob, ("phase", "quantum", "void")):
            return "phase"
        return "contact"
    if _has_any(blob, ("temporal", "time", "slow")):
        return "slow"
    if _has_any(blob, ("phase", "quantum", "void")):
        return "phase"
    if _has_any(blob, ("shock", "lightning")):
        return "em"
    return "contact"


def _f(params: Dict[str, Any], *keys: str, default: Optional[float] = None) -> Optional[float]:
    for k in keys:
        if k in params and params[k] is not None:
            try:
                return float(params[k])
            except (TypeError, ValueError):
                continue
    return default


def _shot_patch(blob: str, params: Dict[str, Any], kind: str) -> Dict[str, Any]:
    """Map Magi-Tech shape params onto LiveProjectile ShotPatch fields.

    Starfield cannot mutate mesh hulls. MagiTechRuntime writes these onto the
    *instance*: collision radius (scale), layer, pierce, bounce, homing,
    lifeScale morph, speed, damage. Empty strings / -1 mean leave alone.
    """
    patch: Dict[str, Any] = {
        "material": "",
        "collisionLayer": "",
        "damageAV": "",
        "effect": "",
        "damage": -1.0,
        "speedMult": -1.0,
        "range": -1.0,
        "scale": -1.0,
        "pierceMult": -1.0,
        "damageMult": -1.0,
        "lifeScale": -1.0,
        "bounceAdd": -1.0,
        "knockBounce": -1.0,
        "homingBlend": -1.0,
        "ricochet": False,
    }
    size = _f(params, "sizeMultiplier", "scale", "radius")
    if size is not None:
        # Balanced piercing shrinks the visual/collision primitive.
        if size < 2.5:
            patch["scale"] = max(0.45, min(2.4, size if size > 0.2 else 1.0))
        else:
            # Magi-Tech radii are world units (~2–12). Map to Conduit scale.
            patch["scale"] = max(0.7, min(2.8, 0.55 + size * 0.12))
    extra_hits = _f(params, "extraHits", "pierceCount", "pierce")
    if extra_hits is not None and extra_hits > 0:
        patch["pierceMult"] = max(1.0, extra_hits)
    speed = _f(params, "speedMultiplier", "speed")
    if speed is not None and 0.2 < speed < 4.0:
        patch["speedMult"] = speed
    life = _f(params, "lifetimeMultiplier", "lifetime", "duration")
    if life is not None and 0.3 < life < 6.0 and life != 1.0:
        patch["lifeScale"] = max(0.5, min(2.2, 2.0 - life * 0.4 if life < 1.0 else life))
    dmg = _f(params, "damage", "splitDamage", "chainDamage", "explosionDamage")
    if dmg is not None and 0.3 < dmg < 3.0:
        patch["damageMult"] = dmg
    bounce = _f(params, "bounce", "bounceAdd", "restitution")
    if bounce is not None and bounce > 0:
        patch["bounceAdd"] = max(1.0, bounce)
        patch["ricochet"] = True
    if _has_any(blob, ("bounce", "ricochet", "rebound", "chamber bounce")):
        patch["ricochet"] = True
        if patch["bounceAdd"] < 0:
            patch["bounceAdd"] = 2.0
        if patch["knockBounce"] < 0:
            patch["knockBounce"] = 1.4
    if _has_any(blob, ("homing", "seek", "guided")):
        patch["homingBlend"] = 0.45
    if _has_any(blob, ("heavy", "mass", "gravity", "singularity", "dark matter")):
        patch["collisionLayer"] = "ActorProjectile"
        if patch["scale"] < 0:
            patch["scale"] = 1.55
    if _has_any(blob, ("void", "chaos", "corrupt")):
        patch["material"] = "tar"
    elif _has_any(blob, ("ice", "freeze", "frost")):
        patch["material"] = "slush"
    elif _has_any(blob, ("fire", "solar", "flare")):
        patch["material"] = "ember"
    elif _has_any(blob, ("lightning", "shock", "spark")):
        patch["material"] = "plasma"
    if kind == "unique" and patch["scale"] < 0:
        patch["scale"] = 1.25
    if kind == "unique" and patch["damageMult"] < 0:
        patch["damageMult"] = 1.15
    return patch


def _mesh_plan(blob: str, kind: str) -> Dict[str, Any]:
    """What MagiTechRuntime *would* swap if a module library exists.

    Today: scale + lifeScale + VisualFx tone. Later: BSGeometry module swap.
    """
    modules: List[str] = []
    if _has_any(blob, ("tendril", "tether", "web", "vine")):
        modules.append("tendril")
    if _has_any(blob, ("spike", "shard", "pierce", "needle")):
        modules.append("spikes")
    if _has_any(blob, ("plate", "armor", "shield")):
        modules.append("plates")
    if _has_any(blob, ("segment", "orbit", "orbital")):
        modules.append("segments")
    if _has_any(blob, ("void", "core", "singularity")):
        modules.append("void_core")
    if kind == "unique" and not modules:
        modules.append("core")
    morph = "pulse" if _has_any(blob, ("oscillat", "pulse", "swell")) else ""
    if _has_any(blob, ("leap", "phase", "warp")):
        morph = "warp"
    if _has_any(blob, ("grow", "overgrowth")):
        morph = "expand"
    return {
        "modules": modules,
        "morph": morph,
        "note": "Starfield cannot rewrite .mesh hulls. Modules/morphs are NiNode attach + morph weights; collision is Havok primitive scale/layer.",
    }


def _iter_config_shapes() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    cfg_dir = _MOD / "config"
    for fname, family in SHAPE_CONFIGS:
        path = cfg_dir / fname
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = None
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list) and v and isinstance(v[0], dict) and "id" in v[0]:
                    rows = v
                    break
        elif isinstance(data, list):
            rows = data
        if not rows:
            continue
        for row in rows:
            sid = str(row.get("id") or "").strip()
            if not sid or sid in SKIP_IDS or sid.lower().startswith("custom"):
                continue
            out.append(
                {
                    "magitech_id": sid,
                    "name": str(row.get("name") or sid),
                    "desc": str(row.get("description") or row.get("name") or sid),
                    "family": family,
                    "category": str(row.get("category") or ""),
                    "weight": row.get("weight", 1),
                    "params": dict(row.get("params") or {}),
                    "source_file": f"config/{fname}",
                    "kind": "unique" if sid in UNIQUE_SHAPE_IDS else "modifier",
                }
            )
    return out


def _iter_mod_shapes() -> List[Dict[str, Any]]:
    path = _MOD / "spellforms" / "base" / "spellshape_mods.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    out: List[Dict[str, Any]] = []
    for group, family in (("spellshapeMods", "mods"), ("wildMagicMods", "wild")):
        block = data.get(group) or {}
        if not isinstance(block, dict):
            continue
        for sid, row in block.items():
            if not isinstance(row, dict):
                continue
            params = dict(row.get("modifiers") or row.get("randomModifiers") or row.get("echoSettings") or {})
            # Flatten [lo, hi] wild rolls to the midpoint for ShotPatch.
            flat: Dict[str, Any] = {}
            for k, v in params.items():
                if isinstance(v, list) and len(v) == 2:
                    try:
                        flat[k] = (float(v[0]) + float(v[1])) / 2.0
                    except (TypeError, ValueError):
                        continue
                else:
                    flat[k] = v
            out.append(
                {
                    "magitech_id": str(row.get("id") or sid),
                    "name": str(row.get("name") or sid),
                    "desc": str(row.get("description") or sid),
                    "family": family,
                    "category": "mod",
                    "weight": row.get("mutationChance", 1),
                    "params": flat,
                    "source_file": "spellforms/base/spellshape_mods.json",
                    "kind": "modifier",
                }
            )
    return out


def _iter_unique_spells() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in UNIQUE_SPELLS:
        out.append(
            {
                "magitech_id": row["id"],
                "name": row["name"],
                "desc": row["description"],
                "family": row["family"],
                "category": "unique_spell",
                "weight": 1,
                "params": {},
                "source_file": "cpp_backend/agents/SpellBusAgent/MasterSpellSystemIntegration.cpp",
                "kind": "unique",
                "school": row["school"],
                "delivery": row["delivery"],
                "payloads": list(row["payloads"]),
                "archetype": row["archetype"],
                "material": row["material"],
                "cost": row["cost"],
                "magnitude": row["magnitude"],
                "area": row["area"],
                "duration": row["duration"],
            }
        )
    return out


def _iter_unique_weapons() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in UNIQUE_WEAPONS:
        out.append(
            {
                "magitech_id": row["id"],
                "name": row["name"],
                "desc": row["description"],
                "family": row["family"],
                "category": "unique_weapon",
                "weight": 1,
                "params": dict(row.get("params") or {}),
                "source_file": row.get("source_file") or "items/weapons/",
                "kind": "weapon",
                "school": row["school"],
                "delivery": row.get("delivery") or "",
                "payloads": list(row.get("payloads") or []),
                "behaviors_force": list(row.get("behaviors_force") or []),
                "archetype": row["archetype"],
                "material": row["material"],
                "hazard": row.get("hazard") or "",
                "cost": row["cost"],
                "magnitude": row["magnitude"],
                "area": row["area"],
                "duration": row["duration"],
                "reagent": str(row.get("reagent") or ""),
            }
        )
    return out


def map_row(row: Dict[str, Any], available: Set[str], existing: Set[str]) -> Dict[str, Any]:
    blob = _blob(row["name"], row["desc"], row["magitech_id"], row.get("category") or "")
    extra = []
    if row.get("delivery"):
        extra.append(row["delivery"])
    extra.extend(row.get("payloads") or [])
    if row.get("behaviors_force"):
        behaviors: List[str] = []

        def take(b: str) -> None:
            if b in available and b not in behaviors:
                behaviors.append(b)

        take("magitech")
        for b in row["behaviors_force"]:
            take(b)
    else:
        behaviors = _behaviors(blob, available, extra)
    sid = _sf_id(row["magitech_id"], row["name"])
    n = 2
    base = sid
    while sid in existing:
        sid = f"{base}{n}"
        n += 1
    school = row.get("school") or _school(row["family"], blob)
    arch = row.get("archetype") or _archetype(blob, row["kind"])
    kind = row["kind"]
    cost = float(row.get("cost") or (18.0 if kind == "unique" else 11.0))
    mag = float(row.get("magnitude") or (16.0 if kind == "unique" else 8.0))
    area = int(row.get("area") or (180 if kind == "unique" else 0))
    duration = int(row.get("duration") or (6 if kind == "unique" else 0))
    desc = row["desc"].rstrip(".")
    if kind == "modifier":
        desc = (
            f"{desc}. Magi-Tech spellshape mutation: dual-cast hangs this on any "
            "Conduit delivery. MagiTechRuntime mutates the live shot's Havok "
            "primitive (radius/layer), pierce/bounce/homing, and lifeScale morph — "
            "not the baked .mesh hull."
        )
    elif kind == "weapon":
        desc = (
            f"{desc} First Starfield pass hangs Arc_Behavior_LobbingGrenade "
            "plus MagiTechRuntime ShotPatch. Physical gun, Conduit ammo. "
            "Not a new plugin."
        )
    else:
        desc = (
            f"{desc} Magi-Tech original (not a warped clone). Starfield Conduit: "
            "real-time gun delivery; MagiTechRuntime still applies the shape's "
            "collision/mesh-module mutation on the live shot."
        )
    material = row.get("material") or (
        "tar" if school == "Entropy" else
        "plasma" if school in ("Phasics", "Voltaics") else
        "mist" if school in ("Celestial", "Atmospherics") else
        "alloy"
    )
    patch = _shot_patch(blob, row.get("params") or {}, "unique" if kind == "weapon" else kind)
    mesh = _mesh_plan(blob, "unique" if kind == "weapon" else kind)
    catalog = {
            "id": sid,
            "name": row["name"][:28],
            "school": school,
            "inspired_by": (
                f"Magi-Tech unique weapon: {row['name']} ({row['magitech_id']})"
                if kind == "weapon"
                else f"Magi-Tech {row['family']} spellshape: {row['name']} ({row['magitech_id']})"
            ),
            "archetype": arch,
            "magnitude": mag,
            "area": area,
            "duration": duration,
            "cost": cost,
            "behaviors": behaviors,
            "desc": desc,
            "source": "magitech",
            "magitech_id": row["magitech_id"],
            "magitech_family": row["family"],
            "magitech_kind": kind,
            "magitech_file": row["source_file"],
            "material": material,
            "life": 8.0 if duration else (5.0 if kind in ("unique", "weapon") else 3.5),
            "stem": f"magitech_{re.sub(r'[^a-z0-9]+', '_', row['magitech_id'].lower()).strip('_')}"[:48],
        }
    if row.get("hazard"):
        catalog["hazard"] = row["hazard"]
    return {
        "catalog": catalog,
        "modifier": {
            "id": sid,
            "magitech_id": row["magitech_id"],
            "kind": kind,
            "family": row["family"],
            "edid": f"Arc_Spell_{sid}",
            "shot": patch,
            "mesh": mesh,
            "params": row.get("params") or {},
            "weight": row.get("weight", 1),
            "reagent": str(row.get("reagent") or ""),
        },
    }


def collect(available: Set[str], existing: Set[str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    seen: Set[str] = set()
    catalog: List[Dict[str, Any]] = []
    modifiers: List[Dict[str, Any]] = []
    rows = _iter_unique_spells() + _iter_unique_weapons() + _iter_config_shapes() + _iter_mod_shapes()
    for row in rows:
        mid = row["magitech_id"]
        if mid in seen:
            continue
        seen.add(mid)
        mapped = map_row(row, available, existing)
        existing.add(mapped["catalog"]["id"])
        catalog.append(mapped["catalog"])
        modifiers.append(mapped["modifier"])
    return catalog, modifiers


_SF_PLUGIN_JSON = Path(
    r"F:\SteamLibrary\steamapps\common\Starfield\Data\SFSE\Plugins\MadScience"
)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _weapons_pack() -> Dict[str, Any]:
    """Unique Magi-Tech weapons → later Starfield Conduit rework.

    Alchemical launcher ammo is LobbingGrenade SPELs. Segmented whip / flail
    / chain / nunchaku / rope are physical melee WEAPs, not magic.
    """
    return {
        "meta": {
            "title": "Magi-Tech unique weapons for Starfield Arcane Conduit",
            "target": "Starfield / ArcaneConduit",
            "priority": [
                "alchemical_grenade_launcher",
                "segmented_weapons",
            ],
            "later": ["segmented_mechs_ship_deployable"],
            "note": (
                "Do not invent a new SFSE plugin. Launcher ammo is "
                "LobbingGrenade. Whip and flail are different physical melee "
                "WEAPs — not Arc_Behavior_Flail, not Host of Chains. Optional "
                "later: Imbue coats those WEAPs. Per-segment Havok later."
            ),
        },
        "weapons": [
            {
                "id": "alchemical_grenade_launcher",
                "name": "Alchemical Grenade Launcher",
                "priority": "high",
                "source": [
                    "items/weapons/alchemicalgrenadelauncher/",
                    "cpp_backend/core/modules/alchemy/EnhancedAlchemicalGrenadeLauncher.hpp",
                    "cpp_backend/core/modules/alchemical_grenade_generator/",
                    "cpp_backend/core/modules/alchemical_launcher_generator/",
                ],
                "starbound": {
                    "identity": (
                        "3-slot reagent mixer that lobs a chemical grenade. "
                        "No spellstone. Mixing chamber + reaction chamber. "
                        "Fuse / impact / proximity detonation. Alt-fire bouncing "
                        "alchemical sphere. Overheat, mana-per-shot, environmental "
                        "synergy/opposition."
                    ),
                    "tiers": [
                        {
                            "id": "chemicalgrenadelauncher",
                            "name": "Alchemical Grenade Launcher",
                            "rarity": "Rare",
                            "level": 6,
                            "fireTime": 1.2,
                            "magazine": 8,
                            "reload": 2.0,
                        },
                        {
                            "id": "chemicalgrenadelauncher_tech2",
                            "name": "Alchemical Launcher Mk II",
                            "rarity": "Epic",
                            "level": 8,
                            "fireTime": 1.0,
                        },
                        {
                            "id": "chemicalgrenadelauncher_tech3",
                            "name": "Alchemical Launcher Mk III",
                            "rarity": "Legendary",
                            "level": 10,
                        },
                        {
                            "id": "flamelord_grenadegun",
                            "name": "Flamelord's Grenade Gun",
                            "rarity": "Legendary",
                            "level": 12,
                            "fireTime": 0.6,
                            "element": "fire",
                        },
                    ],
                    "ammo": [
                        "chemicalgrenadeammo",
                        "chemicalgrenadeammo_mk2",
                        "chemicalgrenadeammo_mk3",
                    ],
                    "specialized_grenades": [
                        {"id": "grenade_fire", "material": "ember", "payload": "bloom"},
                        {"id": "grenade_frost", "material": "slush", "payload": "slow"},
                        {"id": "grenade_acid", "material": "caustic_vapor", "payload": "field"},
                        {"id": "grenade_storm", "material": "plasma", "payload": "chain"},
                        {"id": "grenade_shadow", "material": "tar", "payload": "shadowphase"},
                    ],
                    "reactions": [
                        "acid_base_neutralization",
                        "catalytic_explosion",
                        "precipitation_reaction",
                        "oxidation_reaction",
                    ],
                    "fuse": ["impact", "timer", "proximity"],
                    "slots": 3,
                },
                "starfield": {
                    "first_pass": (
                        "Hang Arc_Behavior_LobbingGrenade on a Conduit gun. "
                        "Fuse modes already exist (Impact / Timer / Proximity / "
                        "Airburst). Specialized grenades are ShotPatch material "
                        "+ hanging payload (bloom / slow / field / chain / "
                        "shadowphase), not new C++."
                    ),
                    "later": (
                        "3-slot reagent ammo as inventory sockets. MagiTechRuntime "
                        "picks ShotPatch + HAZD from the mix (synergy / opposition / "
                        "planet temperature as EnvironmentContext). Flamelord is "
                        "Pyrolysis + lobbing + bloom, not a unique delivery."
                    ),
                    "keywords": [
                        "Arc_Behavior_LobbingGrenade",
                        "Arc_Behavior_Magitech",
                    ],
                    "do_not": [
                        "New grenade plugin",
                        "Rewrite .mesh hulls for the shell",
                        "Per-reagent C++ modules that duplicate bloom/field/chain",
                    ],
                },
            },
            {
                "id": "segmented_weapons",
                "name": "Segmented Weapon System",
                "priority": "high",
                "kind": "physical_weap",
                "source": [
                    "cpp_backend/core/modules/segmented_weapon_generator/",
                    "scripts/BusPlugins/mtSegmentedWeaponBusPlugin.lua",
                    "cpp_backend/core/modules/LUA_INTEGRATION_README.md",
                ],
                "starbound": {
                    "identity": (
                        "Physical melee: procedural whip, flail, chain, nunchaku, "
                        "and rope with per-segment mesh and 2.5D joint physics. "
                        "Not spells."
                    ),
                    "types": ["WHIP", "FLAIL", "NUNCHAKU", "ROPE", "CHAIN"],
                },
                "weapons": PHYSICAL_WEAPONS,
                "starfield": {
                    "record": "sfform.weap from scratch, not clones, not SPELs",
                    "note": (
                        "Whip and flail are different physical weapons. A whip is "
                        "a long flexible lash (tip-speed crack). A flail is a short "
                        "chain with a heavy head (mass smash). Do not map either "
                        "to Arc_Behavior_Flail (magic graviton ball) or Host of "
                        "Chains (magic tether SPELL). Optional later: Imbue coats "
                        "the physical WEAP. Per-segment Havok stays later."
                    ),
                    "do_not": [
                        "Author these as Conduit SPELs",
                        "Reuse Arc_Behavior_Flail for the whip",
                        "Treat nunchaku as a flail or a whip",
                        "Port OpenStarbound per-segment rigidbodies as-is",
                    ],
                },
            },
            {
                "id": "spellstone_casters",
                "name": "Spellstone casters (wand / staff / orb / device)",
                "priority": "medium",
                "source": [
                    "items/active/weapons/wand/magitechbasicwand.activeitem",
                    "items/active/weapons/staff/magitechbasicstaff.activeitem",
                    "items/active/weapons/orb/magitechbasicorb.activeitem",
                    "items/active/weapons/magitech/magitechdevice.activeitem",
                ],
                "starbound": {
                    "identity": (
                        "Spellstone-socketed casters. Wand = single stone, staff = "
                        "combos/AoE, orb = area control, Magitech Spell Device = "
                        "swappable stone + amplify/stabilize/overcharge modes."
                    ),
                },
                "starfield": {
                    "first_pass": (
                        "These are already Conduit guns: dual-cast Magi-Tech "
                        "spellshape SPELs onto any delivery. The device's "
                        "amplify/stabilize/overcharge modes are MagiTechRuntime "
                        "ShotPatch presets, not new items."
                    ),
                    "later": "Inventory spellstone socket UI if you want the fantasy on a physical gun.",
                },
            },
        ],
    }


def _mechs_pack() -> Dict[str, Any]:
    return {
        "meta": {
            "title": "Magi-Tech segmented mechs — later Starfield ship-deployable",
            "priority": "low",
            "target": "Starfield / ArcaneConduit",
            "warning": (
                "Interesting, but much harder to scale. OpenStarbound mechs are "
                "multi-tile 2.5D segment chains. Starfield ship-deployable mechs "
                "would be per-segment Havok or ship-module stacks — both explode "
                "in cost once more than a handful are live."
            ),
        },
        "starbound": {
            "source": [
                "Data/Config/SegmentedMechs/SegmentedMechSystem.json",
                "cpp_backend/core/plugins/SegmentedMechBusPlugin.cpp",
                "cpp_backend/core/modules/locomotion/SegmentedHoverModule.hpp",
                "cpp_backend/core/modules/locomotion/SegmentedCrawlerModule.hpp",
                "cpp_backend/core/modules/locomotion/SegmentedRailModule.hpp",
            ],
            "archetypes": [
                {
                    "id": "serpentCoil",
                    "name": "Serpent-Class Coil Mech",
                    "locomotion": "hover_snake",
                    "segments": 12,
                },
                {
                    "id": "centipedeAssault",
                    "name": "Centipede-Class Assault Mech",
                    "locomotion": "ground_crawler",
                    "segments": 20,
                },
                {
                    "id": "modularWalker",
                    "name": "Modular Walker Mech (AT-Mech)",
                    "locomotion": "bipedal_stacked",
                    "segments": 8,
                },
                {
                    "id": "trainSiege",
                    "name": "Train-Class Siege Mech",
                    "locomotion": "rail_crawler",
                    "segments": 6,
                },
            ],
        },
        "starfield": {
            "maybe_later": (
                "Ship-deployable: one construct, visual NiNode segments, not "
                "independent Havok bodies per tile. CreatureMount / living-hull "
                "ship modules are the existing Starfield analog — do not merge "
                "blindly. Keep this pack as design notes until a single-body "
                "prototype exists."
            ),
            "do_not": [
                "Port 20-segment rigidbody crawlers into the player combat tick",
                "Treat mechs as extra Magi-Tech SPELs in this import",
            ],
        },
    }


def _write_weapons_export() -> None:
    weapons = _weapons_pack()
    mechs = _mechs_pack()
    weapons_dir = _EXPORT / "weapons"
    systems_dir = _EXPORT / "systems"
    _write_json(weapons_dir / "index.json", weapons)
    _write_json(
        weapons_dir / "alchemical_grenade_launcher.json",
        next(w for w in weapons["weapons"] if w["id"] == "alchemical_grenade_launcher"),
    )
    _write_json(
        weapons_dir / "segmented_weapons.json",
        next(w for w in weapons["weapons"] if w["id"] == "segmented_weapons"),
    )
    _write_json(
        weapons_dir / "spellstone_casters.json",
        next(w for w in weapons["weapons"] if w["id"] == "spellstone_casters"),
    )
    _write_json(weapons_dir / "physical_weapons.json", PHYSICAL_WEAPONS)
    _write_json(systems_dir / "segmented_mechs.json", mechs)
    notes = """# Magi-Tech → Starfield rework notes

Target is **Starfield Arcane Conduit** (SFSE MadScience.dll). Not a second
game, not a new plugin.

## Spellshapes (this import)

`Arc_Behavior_Magitech` is a payload tag. MagiTechRuntime merges
`MagiTechModifiers.json` ShotPatch onto the live Conduit shot.

## Alchemical grenade launcher (high)

Physical *gun* whose *ammo* is Conduit lobs. First-pass SPELs hang
`Arc_Behavior_LobbingGrenade` plus Magi-Tech ShotPatch. Dual-cast specialized
grenades to mix reagents. Not a new plugin.

## Segmented weapons (high) — physical melee, not magic

These are **WEAP** items. Whip and flail are different weapons. They are not
Conduit SPELs, not `Arc_Behavior_Flail` (magic graviton ball), and not Host
of Chains (magic tether SPELL). Optional later: Imbue coats the physical WEAP.

| Type | What it is | Starfield first pass |
| --- | --- | --- |
| Whip | Long flexible lash. Damage is tip speed after a crack. Fast, long reach, light. | `Arc_Weap_MagitechWhip` via sfform.weap (reach 1.8, very fast) |
| Flail | Short chain + heavy head. Damage is mass smash after a wind-up. Slow, high stagger. | `Arc_Weap_MagitechFlail` (reach 1.05, stagger 3) |
| Nunchaku | Two short bars, one joint. Close and fast. Not a whip, not a flail. | `Arc_Weap_MagitechNunchaku` (reach 0.55) |
| Rope | Whip family, rope material, more wrap. Still not a flail. | `Arc_Weap_MagitechRope` (reach 1.7) |
| Chain | Metal links you swing. Heavier than a whip, no flying head. | `Arc_Weap_MagitechChain` two-handed (reach 1.4) |

Craft at a weapon bench (`co_Arc_Weap_Magitech*`). Unique NIFs later.
Per-segment Havok stays later.

## Segmented mechs (low)

Serpent / centipede / walker / train. Ship-deployable later. Hard to scale.
"""
    (_EXPORT / "REWRITE_NOTES.md").write_text(notes, encoding="utf-8")


def _write_export(catalog: List[Dict[str, Any]], modifiers: List[Dict[str, Any]]) -> None:
    _EXPORT.mkdir(parents=True, exist_ok=True)
    _SF_SPELLS.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": {
            "title": "Magi-Tech spellshape mutations for Starfield Arcane Conduit",
            "target": "Starfield",
            "note": (
                "Spellshapes are the mutations Magi-Tech rolls onto living shots. "
                "Unique spells are the short original list. MagiTechRuntime applies "
                "Havok primitive collision, scale/lifeScale morph, material, and "
                "optional NiNode modules — it cannot rewrite .mesh hulls."
            ),
            "backend": str(_MOD / "cpp_backend"),
            "tool": "Tools/Starbound/magitech_starfield_spell_bridge.py",
            "unique": sum(1 for m in modifiers if m["kind"] == "unique"),
            "modifiers": sum(1 for m in modifiers if m["kind"] == "modifier"),
            "weapons": sum(1 for m in modifiers if m["kind"] == "weapon"),
            "mix": (
                "Dual-cast up to 3 Magi-Tech reagent grenades onto the alchemical "
                "launcher. MagiTechRuntime multiplies ShotPatch by synergy / "
                "opposition / PlanetContext temperature. Not a new plugin."
            ),
        },
        "reagents": MAGITECH_REAGENTS,
        "modifiers": modifiers,
    }
    text = json.dumps(payload, indent=2) + "\n"
    (_SF_SPELLS / "MagiTechModifiers.json").write_text(text, encoding="utf-8")
    (_EXPORT / "MagiTechModifiers.json").write_text(text, encoding="utf-8")
    _SF_PLUGIN_JSON.mkdir(parents=True, exist_ok=True)
    (_SF_PLUGIN_JSON / "MagiTechModifiers.json").write_text(text, encoding="utf-8")
    (_EXPORT / "spellshapes.json").write_text(
        json.dumps({"spells": catalog, "count": len(catalog)}, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_weapons_export()
    readme = """# Magi-Tech export (Starfield Arcane Conduit)

OpenStarbound Magi-Tech → **Starfield**. MagiTechRuntime is an SFSE payload
tag on Conduit guns (`Arc_Behavior_Magitech`). Not a new plugin.

## Spellshapes (compiled)

Magi-Tech rolls **spellshapes** onto existing spells. Those mutations plus a
short unique-spell list (chaos / temporal / quantum originals) become SPELs.

Starfield cannot rewrite `.mesh` collision hulls. MagiTechRuntime reads
`MagiTechModifiers.json` and patches the *live* shot:

- Havok primitive radius (`scale`) and collision layer
- pierce / bounce / homing / speed / damage
- `lifeScale` morph
- optional NiNode module attach later (tendrils, spikes, void core)

Dual-cast a MagiTech shape onto any Conduit delivery. Unique MagiTech SPELs
keep a real delivery keyword so they Fire on a root tap.

## Unique weapons

1. **Alchemical grenade launcher** — physical gun; ammo is Conduit lobs (`Arc_Behavior_LobbingGrenade`).
2. **Segmented weapons** — physical melee WEAPs, not SPELs. Whip != flail.
3. Spellstone wand / staff / orb / device — Conduit casters.

## Mechs (low priority)

`systems/segmented_mechs.json` — ship-deployable later. Hard to scale.
See `REWRITE_NOTES.md`.
"""
    (_EXPORT / "README.md").write_text(readme, encoding="utf-8")


def cmd_preview(args: argparse.Namespace) -> int:
    cat_path = Path(args.catalog) if args.catalog else _SF_CATALOG
    cat = json.loads(cat_path.read_text(encoding="utf-8"))
    available = set((cat.get("behaviors") or {}).keys()) | {"magitech"}
    existing = {s.get("id") for s in cat.get("spells") or [] if s.get("id")}
    mapped, mods = collect(available, existing)
    n_u = sum(1 for s in mapped if s["magitech_kind"] == "unique")
    n_m = sum(1 for s in mapped if s["magitech_kind"] == "modifier")
    n_w = sum(1 for s in mapped if s["magitech_kind"] == "weapon")
    print(f"{len(mapped)} Magi-Tech shapes -> Starfield  ({n_u} unique, {n_m} mutations, {n_w} weapons)\n")
    for s in mapped:
        beh = ",".join(s["behaviors"]) or "-"
        print(
            f"  {s['magitech_kind'][0].upper()} {s['id']:<32} {s['name']:<24} "
            f"{s['school']:<14} {beh}  <- {s['magitech_id']}"
        )
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    cat_path = Path(args.catalog) if args.catalog else _SF_CATALOG
    cat = json.loads(cat_path.read_text(encoding="utf-8"))
    behaviors = cat.setdefault("behaviors", {})
    if "magitech" not in behaviors:
        behaviors["magitech"] = {
            "keyword": "Arc_Behavior_Magitech",
            "note": (
                "Payload tag, not a delivery. Magi-Tech spellshape mutations from "
                "the OpenStarbound Magi-Tech backend into Starfield Arcane "
                "Conduit. Dual-cast hangs this on any live delivery. "
                "MagiTechRuntime mutates the instance: Havok primitive "
                "radius/layer, pierce/bounce/homing, lifeScale morph, material, "
                "optional NiNode modules. Cannot rewrite .mesh hulls. Unique "
                "Magi-Tech SPELs keep a real delivery keyword plus this tag. "
                "Not a delivery module and not a new plugin."
            ),
        }
    available = set(behaviors.keys())
    dropped = [
        s.get("id")
        for s in cat.get("spells") or []
        if s.get("magitech_id") in DROP_PHYSICAL_WEAPON_SPELLS
    ]
    if dropped:
        cat["spells"] = [
            s
            for s in cat["spells"]
            if s.get("magitech_id") not in DROP_PHYSICAL_WEAPON_SPELLS
        ]
        print(
            "dropped physical-weapon SPELs (whip/flail/chain are WEAPs, not magic): "
            + ", ".join(dropped)
        )
    existing = {s.get("id") for s in cat.get("spells") or [] if s.get("id")}
    existing_mt = {
        s.get("magitech_id")
        for s in cat.get("spells") or []
        if s.get("source") == "magitech" and s.get("magitech_id")
    }
    mapped, all_mods = collect(available, existing)
    new_mapped = [s for s in mapped if s["magitech_id"] not in existing_mt]
    if not new_mapped:
        if dropped:
            if args.dry_run:
                print(f"[dry] would drop {len(dropped)} physical-weapon SPEL(s)")
            else:
                cat_path.write_text(json.dumps(cat, indent=2) + "\n", encoding="utf-8")
                print(f"saved catalog without {len(dropped)} physical-weapon SPEL(s)")
        else:
            print("nothing new to import")
        if not args.dry_run:
            _write_export(
                [s for s in cat.get("spells") or [] if s.get("source") == "magitech"],
                all_mods,
            )
        return 0

    sys.path.insert(0, str(cat_path.parent.parent / "tools"))
    try:
        import spell_design as sd  # type: ignore

        for s in new_mapped:
            s["life"] = round(sd.default_life_for(s), 2)
        problems = sd.validate({**cat, "spells": list(cat["spells"]) + new_mapped})
    except Exception as exc:
        print(f"[warn] spell_design validate unavailable ({exc}); basic checks only")
        problems = []
        for s in new_mapped:
            if not s["id"].isidentifier():
                problems.append(f"{s['id']}: bad id")

    if problems:
        print(f"refusing import: {len(problems)} problem(s)")
        for p in problems[:40]:
            print(f"  - {p}")
        return 1

    n_u = sum(1 for s in new_mapped if s["magitech_kind"] == "unique")
    n_m = sum(1 for s in new_mapped if s["magitech_kind"] == "modifier")
    n_w = sum(1 for s in new_mapped if s["magitech_kind"] == "weapon")
    print(
        f"importing {len(new_mapped)} Magi-Tech shapes "
        f"({n_u} unique, {n_m} mutations, {n_w} weapons) into {cat_path}"
    )
    if args.dry_run:
        for s in new_mapped[:24]:
            print(f"  [dry] {s['id']} ({s['magitech_kind']}) <- {s['magitech_id']}")
        if len(new_mapped) > 24:
            print(f"  ... +{len(new_mapped) - 24} more")
        return 0

    cat["spells"].extend(new_mapped)
    meta = cat.setdefault("meta", {})
    sources = meta.setdefault("sources", [])
    note = "Magi-Tech Arcane Alchemy spellshapes (cpp_backend + config/*SpellShapes.json)"
    if note not in sources:
        sources.append(note)
    meta["magitech_bridge"] = {
        "imported": len([s for s in cat["spells"] if s.get("source") == "magitech"]),
        "unique": len([s for s in cat["spells"] if s.get("source") == "magitech" and s.get("magitech_kind") == "unique"]),
        "modifiers": len([s for s in cat["spells"] if s.get("source") == "magitech" and s.get("magitech_kind") == "modifier"]),
        "weapons": len([s for s in cat["spells"] if s.get("source") == "magitech" and s.get("magitech_kind") == "weapon"]),
        "tool": "Tools/Starbound/magitech_starfield_spell_bridge.py",
        "modifiers_file": "ArcaneConduit/spells/MagiTechModifiers.json",
    }
    cat_path.write_text(json.dumps(cat, indent=2) + "\n", encoding="utf-8")
    _write_export(
        [s for s in cat["spells"] if s.get("source") == "magitech"],
        all_mods,
    )
    print("saved MagiTechModifiers.json + catalog.")
    print("run: python tools/spell_design.py validate && python tools/spell_design.py compile")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_parser if False else ap.add_subparsers
    sp = ap.add_subparsers(dest="cmd", required=True)
    for name in ("preview", "import"):
        p = sp.add_parser(name)
        p.add_argument("--catalog", default="")
        if name == "import":
            p.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.cmd == "preview":
        return cmd_preview(args)
    if args.cmd == "import":
        return cmd_import(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
