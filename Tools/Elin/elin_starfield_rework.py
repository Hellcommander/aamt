#!/usr/bin/env python3
"""Rework Elin MagicPlus spells for Starfield Arcane Conduit.

Elin is tile / turn-based. Conduit is a real-time gun projector. This tool:

  1. Remaps each Elin spell onto rich Conduit deliveries (Flight shapes,
     Field, Bloom, Beam, Cloak, Dragon Breath, …) — not blank payloads.
  2. Gives every spell a unique MaterialID + stem + HAZD EditorID.
  3. Registers unique TRELLIS projectile (and optional FX) jobs.
  4. Patches build.py HAZD factory / mesh table so compile can wire art.
  5. Can kick an overnight SD→TRELLIS batch (one GPU).

  python elin_starfield_rework.py rework --system druidic
  python elin_starfield_rework.py register-meshes --system druidic
  python elin_starfield_rework.py start-batch --system druidic --kind projectile
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

_ELIN = Path(__file__).resolve().parent
_CATALOG_PATH = _ELIN / "elin_asset_catalog.json"
_DEFAULT_SF_CATALOG = Path(
    r"F:\SteamLibrary\steamapps\common\Starfield\ArcaneConduit\spells\catalog.json"
)
_FX_CATALOG = Path(
    r"F:\SteamLibrary\steamapps\common\Starfield\ArcaneConduit\tools\fx_catalog.json"
)
_BUILD_PY = Path(
    r"F:\SteamLibrary\steamapps\common\Starfield\ArcaneConduit\tools\build.py"
)
_BATCH = Path(
    r"F:\SteamLibrary\steamapps\common\Starfield\ArcaneConduit\tools\run_fx_batch.py"
)
_SEGMENTS = Path(
    r"F:\SteamLibrary\steamapps\common\Starfield\Data\SFSE\Plugins\MadScience\Segments"
)
_SEGMENTS_SRC = Path(
    r"F:\SteamLibrary\steamapps\common\Starfield\SFCoreFixes\plugins\FluidProbe\Segments"
)
_ROOT = Path(r"F:\SteamLibrary\steamapps\common\Starfield")
_SHARED_MESHES = Path(
    r"D:\games\Ai assisted toolkit\Tools\Shared\Concepts\meshes"
)

# Same stems as elin_starfield_spell_bridge.SYSTEM_ASSET — existing TRELLIS GLBs.
_SYSTEM_GLB = {
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


def _existing_glb(spell: dict) -> Optional[Path]:
    """Reuse the already-built system TRELLIS mesh. Do not remesh."""
    hint = spell.get("asset_hint") or ""
    if hint:
        p = _SHARED_MESHES / f"{hint}.glb"
        if p.is_file():
            return p
    sys_id = (spell.get("elin_system") or "").lower()
    stem = _SYSTEM_GLB.get(sys_id)
    if stem:
        p = _SHARED_MESHES / f"{stem}.glb"
        if p.is_file():
            return p
    name = (spell.get("name") or "").lower()
    fallback = "elinNecromancy" if any(
        w in name for w in ("wraith", "skeleton", "thrall", "specter", "bone")
    ) else "elinDruidicMagic"
    p = _SHARED_MESHES / f"{fallback}.glb"
    return p if p.is_file() else None

# begin/end markers so rework can refresh without hand-editing forever
_HAZD_MESH_BEGIN = "# --- ELIN_HAZD_MESH_BEGIN ---"
_HAZD_MESH_END = "# --- ELIN_HAZD_MESH_END ---"
_HAZD_FACT_BEGIN = "# --- ELIN_HAZD_FACTORY_BEGIN ---"
_HAZD_FACT_END = "# --- ELIN_HAZD_FACTORY_END ---"

T_HAZD = {
    "motes": "T_HAZD_MOTES",
    "flame": "T_HAZD_FLAME",
    "warp": "T_HAZD_WARP",
    "well": "T_HAZD_WELL",
    "sink": "T_HAZD_SINK",
    "swirl": "T_HAZD_SWIRL",
}


def _load_paths() -> Path:
    sf = _DEFAULT_SF_CATALOG
    if _CATALOG_PATH.is_file():
        try:
            cfg = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
            p = ((cfg.get("starfield") or {}).get("spellCatalog")) or ""
            if p:
                sf = Path(p)
        except Exception:
            pass
    return sf


def _has_word(blob: str, token: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", blob) is not None


def _has_any(blob: str, tokens: Iterable[str]) -> bool:
    return any(_has_word(blob, t) for t in tokens)


def _blob(spell: dict) -> str:
    tags = " ".join(spell.get("tags") or [])
    return f"{spell.get('name', '')} {spell.get('desc', '')} {tags} {spell.get('elin_id', '')}".lower()


def _pascal(name: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", name)
    return "".join(p[:1].upper() + p[1:] for p in parts) or "Spell"


def _stem(spell: dict) -> str:
    eid = (spell.get("elin_id") or spell.get("id") or "spell").lower()
    eid = re.sub(r"^tmpl_", "", eid)
    eid = re.sub(r"[^a-z0-9]+", "_", eid).strip("_")
    if not eid.startswith("elin_"):
        eid = f"elin_{eid}"
    return eid[:48]


def _hazard_edid(spell: dict) -> str:
    stem = _stem(spell)
    # Arc_Hazd_ElinDruidHealNature
    body = _pascal(stem.replace("elin_", "elin "))
    return f"Arc_Hazd_{body}"


def _is_creature_summon(blob: str, name: str) -> bool:
    """Living companion, not Elin copy like 'Summon rain' or 'Summon a fist'."""
    if _has_any(blob, ("rain", "blizzard", "weather", "storm", "lightning")):
        return False
    creatures = (
        "golem",
        "guardian",
        "familiar",
        "wraith",
        "drake",
        "sentinel",
        "demon",
        "death knight",
        "bone golem",
        "stone warrior",
        "familiar",
    )
    if _has_any(blob, creatures):
        # 'Summon a giant stone fist' mentions smash, not a persistent golem.
        if _has_any(blob, ("fist", "smash")) and not _has_any(blob, ("golem", "sentinel", "warrior")):
            return False
        return True
    n = name.lower().strip()
    return (n.startswith("summon ") or n.startswith("call ")) and _has_any(n, creatures)


def starfield_map(spell: dict, available: Set[str]) -> Tuple[str, List[str], str, str]:
    """Return archetype, behaviors, material, hazd template const name."""
    blob = _blob(spell)
    behaviors: List[str] = []

    def take(b: str) -> None:
        if b in available and b not in behaviors and len(behaviors) < 3:
            behaviors.append(b)

    # --- archetype ---
    if _has_any(blob, ("heal", "regen", "mend", "restore", "transfusion", "commune")):
        arch = "mend"
    elif _has_any(blob, ("poison", "venom", "toxic", "blight", "rot", "decay", "corrupt", "fungal")):
        arch = "decay"
    elif _has_any(blob, ("slow", "entangle", "grasp", "snare", "restrain", "root", "net", "trap", "strangl")):
        arch = "slow"
    elif _has_any(blob, ("shield", "armor", "barrier", "ward", "hide", "fortify", "wall")):
        arch = "fortify"
    elif _has_any(blob, ("haste", "quick", "rage", "berserk", "wildform", "wolf", "cat", "bear", "boost")):
        arch = "boost"
    elif _has_any(blob, ("lightning", "thunder", "shock", "storm")):
        arch = "em"
    elif _has_any(blob, ("fear", "daze", "blind", "dazzle")):
        arch = "dazzle"
    elif _has_any(blob, ("phase", "dream", "spirit", "ghost", "wraith")):
        arch = "phase"
    else:
        arch = "contact"

    # --- primary Starfield delivery (real-time gun, not tile turn) ---
    # Prefer exactly one delivery module keyword, then optional payload tags.
    if _has_any(blob, ("breath", "exhale", "cone")):
        take("dragon_breath")
    elif _has_any(blob, ("venus", "flytrap")) or "venus_maw" in (
        spell.get("elin_id") or ""
    ):
        # Conduit Flytrap was based on Elin Venus Maw. Vine Orb is unrelated
        # (original Conduit, not an Elin port).
        take("flytrap")
    elif _has_any(blob, ("storm", "tempest", "hurricane", "twister")) and "storm" in available:
        take("storm")
    elif _has_any(blob, ("cloud", "mist", "fog", "gas", "zone", "grove", "field", "puddle", "carpet", "wall of", "aura")):
        take("field")
    elif _has_any(blob, ("nova", "burst", "blast", "explode", "erupt")):
        take("bloom")
    elif _has_any(blob, ("channel", "ritual", "commune", "sustain", "stream", "beam")):
        take("beam")
    elif arch == "fortify" and _has_any(blob, ("armor", "shield", "hide", "skin")):
        take("cloak")
    elif arch == "fortify":
        take("ward")
    elif arch == "boost" and _has_any(blob, ("wildform", "form", "wolf", "cat", "bear", "shape")):
        take("cloak")  # living aura while "shaped"
        take("boost")
    elif arch == "mend" and _has_any(blob, ("area", "aoe", "radius", "zone", "allies", "party", "grove")):
        take("field")
    elif arch == "mend":
        take("homing")
        take("seeking")
    elif arch == "slow" or _has_any(blob, ("entangle", "vine net", "grasp", "root", "snare", "trap")):
        take("field")
        take("restrain")
    elif _is_creature_summon(blob, spell.get("name") or ""):
        take("drone")
    elif _has_any(blob, ("rain", "blizzard", "weather")):
        take("field")
    elif _has_any(blob, ("spore", "seed", "scatter", "shard", "fragment")):
        take("cluster")
        take("bounce")
    elif _has_any(blob, ("lance", "spear", "arrow", "bolt", "dart", "spike", "thorn", "lash", "strike", "touch")):
        take("pierce")
        if _has_any(blob, ("seek", "homing", "guided", "chase")):
            take("seeking")
    elif _has_any(blob, ("vine orb", "vessel", "flask", "bomb", "grenade")):
        take("vine_orb")
    else:
        # Default combat round: seeking pierce bolt (gun-shaped, not a tile step).
        take("pierce")
        take("seeking")

    # Payload tags (never alone).
    if _has_any(blob, ("homing", "seek", "guided")) and "homing" not in behaviors:
        take("homing")
    if _has_any(blob, ("pierce", "penetrat", "through")) and "pierce" not in behaviors:
        take("pierce")
    if _has_any(blob, ("ground", "terrain", "earth", "root")) and "groundburst" in available:
        take("groundburst")
    if _has_any(blob, ("rune", "sigil")):
        take("charged_runes")
    if _has_any(blob, ("seed", "spore", "grow")) and "seed" in available and "cluster" not in behaviors:
        take("seed")

    # Guarantee a dispatchable delivery.
    delivery_keys = {
        "flytrap",
        "chain", "bloom", "field", "well", "flail", "spiral", "homing", "orbit",
        "pierce", "bounce", "cluster", "beam", "pull", "push", "pulse", "ward",
        "cloak", "slowtime", "dash", "cellg", "air", "portal", "saw", "liquid",
        "host", "amalgam", "vine_orb", "dragon_breath", "flame_lance", "magma_orb",
        "electric_orb", "mini_twister", "storm", "burgeoning_growth", "drone",
        "meteorite", "frostwall", "spiral_cold", "dim_rift", "repair",
        "voltspike", "conductor_stream", "horror", "telekinesis", "angel_seraph",
        "chaos_balls", "lightning_orb", "rat_swarm", "host_of_chains",
        "shadow_vortex", "electric_charge", "needle_shower", "magnetic_twister",
        "shrinkwarp", "catch_projectile", "boost",
    }
    if not any(b in delivery_keys for b in behaviors):
        take("pierce")
        take("seeking")

    # --- material (unique-ish by theme) ---
    if _has_any(blob, ("poison", "venom", "toxic", "blight", "fungal")):
        mat = "slime"
        hazd = "motes"
    elif _has_any(blob, ("vine", "thorn", "plant", "verdant", "grove", "root", "leaf")):
        mat = "gel"
        hazd = "motes"
    elif _has_any(blob, ("heal", "regen", "mend", "life", "growth")):
        mat = "mist"
        hazd = "motes"
    elif _has_any(blob, ("storm", "thunder", "lightning")):
        mat = "plasma"
        hazd = "warp"
    elif _has_any(blob, ("dream", "spirit", "phase", "echo")):
        mat = "prismatic_solvent"
        hazd = "warp"
    elif _has_any(blob, ("fire", "flame", "ember", "burn")):
        mat = "ember"
        hazd = "flame"
    elif _has_any(blob, ("ice", "frost", "cold")):
        mat = "slush"
        hazd = "swirl"
    elif _has_any(blob, ("stone", "earth", "terrain", "rock")):
        mat = "iron"
        hazd = "sink"
    elif _has_any(blob, ("blood")):
        mat = "tar"
        hazd = "flame"
    else:
        mat = "gel"
        hazd = "motes"

    if "dragon_breath" in behaviors:
        hazd = "flame"
    if "field" in behaviors and hazd == "motes" and arch == "decay":
        hazd = "motes"
    if "bloom" in behaviors:
        hazd = "flame" if mat == "ember" else "well"

    return arch, behaviors, mat, T_HAZD[hazd]


def _profile_mode(mapped: List[str]) -> str:
    if "dragon_breath" in mapped:
        return "breath"
    if "beam" in mapped:
        return "beam"
    if "field" in mapped:
        return "field"
    if "bloom" in mapped:
        return "bloom"
    if "cloak" in mapped:
        return "cloak"
    if "ward" in mapped:
        return "ward"
    if "drone" in mapped:
        return "summon"
    return "bolt"


def write_profiles(system: Optional[str]) -> int:
    cat = json.loads(_load_paths().read_text(encoding="utf-8"))
    doc: Dict[str, Any] = {}
    for spell in cat.get("spells") or []:
        if spell.get("source") != "elin":
            continue
        if system and (spell.get("elin_system") or "") != system:
            continue
        mapped = list((spell.get("starfield") or {}).get("mapped") or [])
        mode = _profile_mode(mapped)
        mat = spell.get("material") or "gel"
        life = float(spell.get("life") or 2.4)
        mag = float(spell.get("magnitude") or 10.0)
        area = float(spell.get("area") or 0.0)
        duration = float(spell.get("duration") or 0.0)
        if mode == "summon":
            life = max(8.0, duration if duration > 0.0 else life, float(spell.get("life") or 8.0))
        row: Dict[str, Any] = {
            "mode": mode,
            "material": mat,
            "mass": 18.0 if mode == "summon" else (10.0 if mode == "bolt" else 16.0),
            "speed": 480.0 if mode == "summon" else (2600.0 if "pierce" in mapped else 2100.0),
            "radius": 38.0 if mode == "summon" else 24.0,
            "life": max(0.8, min(life, 18.0 if mode == "summon" else 4.0)),
            "pierce": 1 if "pierce" in mapped and mode == "bolt" else 0,
            "homing": True if mode == "summon" else bool({"homing", "seeking"} & set(mapped)),
            "cluster": "cluster" in mapped,
            "groundburst": "groundburst" in mapped,
            "fieldRadius": max(180.0, area * 40.0 if area else 280.0),
            "fieldDuration": max(6.0 if mode == "summon" else 3.0, duration or 6.0),
            "coneDegrees": 32.0 if mode == "breath" else 18.0,
            "coneRange": 1100.0 if mode == "breath" else 1600.0,
            "leash": 1400.0 if mode == "summon" else 1600.0,
            "summons": 2 if mode == "summon" and "cluster" in mapped else 1,
            "damageScale": max(0.35, min(mag / 20.0, 1.8)),
            "essencePerSecond": 5.0 if mode == "beam" else 0.0,
        }
        doc[f"Arc_Spell_{spell['id']}"] = row
    dests = [
        Path(r"F:\SteamLibrary\steamapps\common\Starfield\ArcaneConduit\spells\ElinProfiles.json"),
        Path(r"F:\SteamLibrary\steamapps\common\Starfield\Data\SFSE\Plugins\MadScience\ElinProfiles.json"),
    ]
    merged: Dict[str, Any] = {}
    for dest in dests:
        if dest.is_file():
            try:
                prev = json.loads(dest.read_text(encoding="utf-8"))
                if isinstance(prev, dict):
                    merged.update(prev)
                    break
            except json.JSONDecodeError:
                pass
    merged.update(doc)
    body = json.dumps(merged, indent=2) + "\n"
    for dest in dests:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body, encoding="utf-8")
        print(f"profiles {len(merged)} ({len(doc)} this pass) -> {dest}")
    return len(doc)


# Per-system default silhouettes so Elin spells are not one CAD bolt.
_SYSTEM_BODY = {
    "druidic": "living bark-seed bolt with thorn ridges and a sealed growth slit",
    "bardic": "machined resonator capsule with ribbed sound-slots, not an instrument",
    "dragon": "scale-plated elemental lance with a horned collar and hard ridges",
    "necromancy": "fused bone-shard dart with a rib-lattice collar",
    "etherwind": "twisted wind-glass helix dart with stacked disks",
    "blood": "coagulated tar teardrop dart with crusted vein ridges",
    "element": "faceted elemental crystal slug with a metal collar",
    "dream": "thin smoked-glass phase dart with a machined ring",
    "wisp": "hollow lantern-orb with radial fins, sealed solid volume",
    "weather": "storm-glass spear with stacked conductive disks",
    "spirit": "polished reliquary capsule with a sealed window",
    "spectre": "translucent smoked-glass wedge dart",
    "golemancy": "riveted stone-block cube core with a carved socket",
    "technomancy": "hex-lattice tech slug with contact pins",
    "pact": "wax-rimmed contract-seal disk, solid reconstructable",
    "rune": "carved rune-stone wedge, solid stone not floating glyphs",
    "summon": "faceted totem-seed core with bark ridges, not a creature",
    "crossmagic": "twinned two-material bolt split down the middle",
}

_NAME_BODY = (
    (("venus", "maw", "flytrap"), "compact carnivorous-plant seed pod with fused jaw ridges, not an open mouth, not a creature"),
    (("vine", "lash", "thorn", "root", "entangle"), "elongated living vine-thorn spear with hard plant ridges"),
    (("spore", "seed", "fungal"), "ribbed seed-spore pod"),
    (("lullaby", "sleep", "slumber"), "closed oval sleep-bell with a sealed slit"),
    (("melody", "hymn", "carol", "song"), "hollow bell-capsule with slotted sound-ribs"),
    (("anthem", "march", "battle"), "wedge war-horn bolt with stacked rings"),
    (("quickstep", "haste"), "swept chevron speed-fin dart"),
    (("blast", "sonic", "cacophony"), "flared shock-funnel slug"),
    (("breath", "exhale"), "short stubby exhalation capsule with hard molten ridges"),
    (("lance", "spear", "arrow"), "elongated tapered spear core"),
    (("nova", "explosion", "burst"), "compact burst-seed sphere with crack seams, intact not exploded"),
    (("heal", "mend", "regen", "lifebloom", "grove"), "smooth translucent life-orb capsule with equatorial ring"),
    (("shield", "ward", "wall", "armor", "bark"), "compact reinforced plate-bolt with overlapping scales"),
    (("golem", "sentinel", "warrior", "thrall", "familiar"), "compact living-construct totem core, faceted seed, not an animal"),
    (("wisp",), "hollow lantern-orb with radial fins"),
    (("rune", "sigil"), "carved rune-stone wedge"),
    (("blood",), "coagulated tar teardrop"),
    (("phase", "ghost", "ethereal", "wraith", "specter"), "thin glass phase-dart with a machined ring"),
    (("storm", "thunder", "lightning"), "segmented conductive storm lance"),
    (("poison", "venom", "toxic", "acid"), "faceted toxic crystal dart"),
    (("turret", "trap", "grenade"), "compact deployable tech canister with latch ribs"),
    (("node", "beacon", "sluice", "anchor"), "stacked-disk field node with a sealed core window"),
)

_SILHOUETTES = (
    "elongated teardrop",
    "short faceted prism",
    "ribbed capsule",
    "stacked-disk slug",
    "twisted helix dart",
    "wedge chevron",
    "seed-pod oval",
    "barbed spear",
    "ringed collar bolt",
    "latticed cube-core",
    "flared funnel slug",
    "split-body twin slug",
)


def _stable_pick(key: str, items: Tuple[str, ...]) -> str:
    h = int(hashlib.md5(key.encode("utf-8")).hexdigest()[:8], 16)
    return items[h % len(items)]


def _proj_body(spell: dict) -> str:
    """Unique reconstructable silhouette — never a generic energy bolt."""
    name = spell.get("name") or spell.get("elin_id") or "spell"
    blob = _blob(spell)
    system = (spell.get("elin_system") or "").lower()
    stem = spell.get("stem") or _stem(spell)
    mode = (spell.get("starfield") or {}).get("mode") or ""
    for tokens, body in _NAME_BODY:
        if _has_any(blob, tokens):
            return f"{body} for {name}"
    if mode == "summon":
        return (
            f"compact living-construct totem core for {name}, faceted seed-body "
            f"with plant-bark ridges, not an animal not a creature"
        )
    sys_body = _SYSTEM_BODY.get(system)
    sil = _stable_pick(stem, _SILHOUETTES)
    if sys_body:
        return f"{sys_body} for {name}, {sil} silhouette"
    return f"solid condensed {sil} for {name}"


def _elin_kit(spell: dict) -> str:
    """MULTI_MESH exporter family, or empty for a unique single body.

    Elin Venus Maw → Flytrap kit (maw + vine + gas). Vine Orb is a Conduit
    original and is not used for Elin plant ports.
    """
    blob = _blob(spell)
    eid = (spell.get("elin_id") or "").lower()
    mapped = [
        (x or "").lower()
        for x in ((spell.get("starfield") or {}).get("mapped") or [])
    ]
    mset = set(mapped)
    if "venus" in blob or "flytrap" in blob or "venus_maw" in eid or "flytrap" in mset:
        return "flytrap"
    if "burgeoning_growth" in mset or "burgeon" in blob:
        return "burgeoning"
    if "host_of_chains" in mset or _has_any(blob, ("chain", "shackle")):
        return "hostofchains"
    if "electric_orb" in mset:
        return "electricorb"
    if _has_any(blob, ("grenade", "bomb", "flask", "mine")):
        return "lobbinggrenade"
    # Vine Orb is original Conduit. Elin grenades were mapped to vine_orb as
    # a throwable-vessel analog — never use that MULTI_MESH kit for Elin.
    return ""


def _solid_prompt(spell: dict, kind: str) -> str:
    """TRELLIS still: solid reconstructable body only — no glow/trail."""
    name = spell.get("name") or spell.get("elin_id") or "spell"
    school = spell.get("school") or "Vitalics"
    mat = spell.get("material") or "gel"
    blob = _blob(spell)
    body = _proj_body(spell)
    if kind == "fx":
        shape = f"cracked lingering husk of ({body})"
        if _has_any(blob, ("vine", "plant", "grove", "maw", "venus")):
            shape = "scorched woven vine-root hazard shell"
        elif _has_any(blob, ("poison", "fungal", "mist", "cloud", "acid")):
            shape = "cracked spore-pocked toxin shell"
        elif _has_any(blob, ("storm", "thunder", "lightning")):
            shape = "fractured storm-glass hazard shell"
        elif _has_any(blob, ("bone", "corpse", "skull")):
            shape = "cracked fused-bone cage shell"
        elif _has_any(blob, ("blood",)):
            shape = "ruptured coagulated-tar crust shell"
        elif _has_any(blob, ("golem", "stone", "clay", "iron sentinel")):
            shape = "split riveted stone-block husk"
        return (
            f"single {shape} for {name}, solid reconstructable volume, "
            f"{mat} material read, {school} fantasy spell residue, "
            f"studio product photo, orthographic view, centered, plain solid grey "
            f"background, no creature, no hand, no fog plume, no glow, no trail"
        )
    return (
        f"single {body}, hard surface, CAD product render, "
        f"{mat} material silhouette, {school} Conduit projectile, "
        f"studio product photo, orthographic three-quarter view, centered, "
        f"plain solid grey background, no glow, no trail, no hand, no aura, no smoke, no creature"
    )


def _sf_note(desc: str) -> str:
    note = " Starfield Conduit: real-time gun delivery (not Elin tile turns)."
    if "Starfield Conduit:" in desc:
        return desc
    if not desc.endswith("."):
        desc += "."
    return desc + note


def rework_catalog(system: Optional[str]) -> Tuple[dict, int]:
    path = _load_paths()
    cat = json.loads(path.read_text(encoding="utf-8"))
    available = set((cat.get("behaviors") or {}).keys())
    n = 0
    for spell in cat.get("spells") or []:
        if spell.get("source") != "elin":
            continue
        if system and (spell.get("elin_system") or "") != system:
            continue
        arch, mapped, mat, hazd_tpl = starfield_map(spell, available)
        stem = _stem(spell)
        haz = _hazard_edid(spell)
        spell["archetype"] = arch
        # C++ ElinRuntime claims Arc_Behavior_Elin. Delivery richness lives in
        # ElinProfiles.json so Flight/VineOrb keywords cannot steal the SPEL.
        spell["behaviors"] = ["elin"]
        spell["material"] = mat
        spell["stem"] = stem
        spell["hazard"] = haz
        spell["hazd_tpl"] = hazd_tpl
        sys_id = (spell.get("elin_system") or "").lower()
        spell["asset_hint"] = _SYSTEM_GLB.get(sys_id) or (
            _existing_glb(spell).stem if _existing_glb(spell) else "elinDruidicMagic"
        )
        spell["proj_prompt"] = _solid_prompt(spell, "projectile")
        spell["fx_prompt"] = _solid_prompt(spell, "fx")
        spell["desc"] = _sf_note(spell.get("desc") or spell.get("name") or "")
        spell["starfield"] = {
            "delivery": mapped[0] if mapped else "bolt",
            "mapped": mapped,
            "from": "elin_tile_turn",
            "mode": _profile_mode(mapped),
            "runtime": "ElinRuntime",
        }
        n += 1
    path.write_text(json.dumps(cat, indent=2) + "\n", encoding="utf-8")
    meta = cat.setdefault("meta", {})
    meta["elin_bridge"] = {
        "imported": len([s for s in cat["spells"] if s.get("source") == "elin"]),
        "tool": "Tools/Elin/elin_starfield_spell_bridge.py",
        "rework": "Tools/Elin/elin_starfield_rework.py",
        "reworked": n,
    }
    path.write_text(json.dumps(cat, indent=2) + "\n", encoding="utf-8")
    return cat, n


def register_meshes(system: Optional[str]) -> int:
    cat_path = _load_paths()
    cat = json.loads(cat_path.read_text(encoding="utf-8"))
    fx = json.loads(_FX_CATALOG.read_text(encoding="utf-8"))
    have = {j.get("id") for j in fx.get("jobs") or []}
    insert_at = 0
    for i, j in enumerate(fx["jobs"]):
        if str(j.get("id", "")).startswith("fb_"):
            insert_at = i
            break
    new_jobs: List[dict] = []
    hazd_rows: List[Tuple[str, str, str]] = []  # edid, tpl_const, name
    mesh_rows: List[Tuple[str, str]] = []  # edid, nif

    for spell in cat.get("spells") or []:
        if spell.get("source") != "elin":
            continue
        if system and (spell.get("elin_system") or "") != system:
            continue
        stem = spell.get("stem") or _stem(spell)
        school = spell.get("school") or "Vitalics"
        mat = spell.get("material") or "gel"
        haz = spell.get("hazard") or _hazard_edid(spell)
        hazd_tpl = spell.get("hazd_tpl") or "T_HAZD_MOTES"
        for kind, length_key, length_val in (
            ("projectile", "length", 0.48),
            ("fx", "diameter", 2.4),
        ):
            jid = f"{'proj' if kind == 'projectile' else 'fx'}_{stem}"
            if jid in have:
                continue
            glb = None
            kit = _elin_kit(spell)
            job: Dict[str, Any] = {
                "id": jid,
                "kind": kind,
                "name": jid,
                "school": school,
                "prompt": spell.get("proj_prompt" if kind == "projectile" else "fx_prompt")
                or _solid_prompt(spell, kind),
                "spell": spell["id"],
                "material_id": mat,
                "material": f"Materials/ArcaneConduit/{jid}.mat",
                "elin": True,
                "unique_mesh": True,
            }
            if kit:
                job["kit"] = kit
            if kind == "projectile":
                job["length"] = length_val
                job["surface"] = "organic" if mat in ("gel", "slime", "mist") else "hard"
                if job["surface"] == "organic":
                    job["organic"] = True
            else:
                job["diameter"] = length_val
                job["anchor"] = "center"
            new_jobs.append(job)
            have.add(jid)
        mesh_rows.append((haz, f"fx_{stem}.nif"))
        hazd_rows.append((haz, hazd_tpl, spell.get("name") or stem))

        # FLP sidecar stubs (absorb soft plant / poison family)
        absorb = "water,acid,lava,ember"
        if mat == "slime":
            absorb = "water,slime,gel,flesh"
        body = {
            "comment": f"Elin Starfield rework sidecar for {spell.get('name')} ({stem}).",
            "segments": [
                {
                    "id": stem,
                    "node": "*",
                    "mat": mat,
                    "absorb": absorb,
                    "hp": 40,
                    "break": "hide",
                }
            ],
        }
        text = json.dumps(body, indent=2) + "\n"
        for prefix in ("proj", "fx"):
            for dest in (_SEGMENTS, _SEGMENTS_SRC):
                dest.mkdir(parents=True, exist_ok=True)
                (dest / f"{prefix}_{stem}.flp.json").write_text(text, encoding="utf-8")

    if new_jobs:
        fx["jobs"][insert_at:insert_at] = new_jobs
        _FX_CATALOG.write_text(json.dumps(fx, indent=2) + "\n", encoding="utf-8")

    _patch_build_py(mesh_rows, hazd_rows)
    print(f"fx_catalog +{len(new_jobs)} jobs")
    print(f"HAZD rows {len(hazd_rows)}")
    return len(new_jobs)


def _patch_build_py(
    mesh_rows: List[Tuple[str, str]],
    hazd_rows: List[Tuple[str, str, str]],
) -> None:
    text = _BUILD_PY.read_text(encoding="utf-8")

    mesh_block = (
        f"    {_HAZD_MESH_BEGIN}\n"
        + "".join(f'    "{edid}": "{nif}",\n' for edid, nif in sorted(set(mesh_rows)))
        + f"    {_HAZD_MESH_END}\n"
    )
    fact_block = (
        f"        {_HAZD_FACT_BEGIN}\n"
        + "".join(
            f'        ("{edid}", {tpl}, "{name.replace(chr(34), "")}"),\n'
            for edid, tpl, name in sorted(set(hazd_rows), key=lambda r: r[0])
        )
        + f"        {_HAZD_FACT_END}\n"
    )

    if _HAZD_MESH_BEGIN in text and _HAZD_MESH_END in text:
        text = re.sub(
            re.escape(_HAZD_MESH_BEGIN) + r".*?" + re.escape(_HAZD_MESH_END),
            mesh_block.strip(),
            text,
            count=1,
            flags=re.S,
        )
    else:
        # Insert before closing of HAZD_MESH dict — after Magma Orb line.
        anchor = '"Arc_Hazd_MagmaOrb": "fx_magmaorb.nif",'
        if anchor not in text:
            raise SystemExit("build.py HAZD_MESH anchor missing")
        text = text.replace(anchor, anchor + "\n" + mesh_block.rstrip())

    if _HAZD_FACT_BEGIN in text and _HAZD_FACT_END in text:
        text = re.sub(
            re.escape(_HAZD_FACT_BEGIN) + r".*?" + re.escape(_HAZD_FACT_END),
            fact_block.strip(),
            text,
            count=1,
            flags=re.S,
        )
    else:
        anchor = '("Arc_Hazd_MagmaOrb", T_HAZD_FLAME, "Magma Orb"),'
        if anchor not in text:
            raise SystemExit("build.py HAZD factory anchor missing")
        text = text.replace(anchor, anchor + "\n" + fact_block.rstrip())

    _BUILD_PY.write_text(text, encoding="utf-8")
    print(f"patched {_BUILD_PY}")


def start_batch(system: Optional[str], kind: str) -> int:
    cat = json.loads(_load_paths().read_text(encoding="utf-8"))
    ids = []
    for spell in cat.get("spells") or []:
        if spell.get("source") != "elin":
            continue
        if system and (spell.get("elin_system") or "") != system:
            continue
        stem = spell.get("stem") or _stem(spell)
        if kind in ("projectile", "both"):
            ids.append(f"proj_{stem}")
        if kind in ("fx", "both"):
            ids.append(f"fx_{stem}")
    if not ids:
        print("no jobs to batch")
        return 1
    # Write a job list file for resume
    list_path = _ELIN / f"overnight_{system or 'all'}_{kind}.txt"
    list_path.write_text("\n".join(ids) + "\n", encoding="utf-8")
    print(f"batch list {len(ids)} -> {list_path}")
    # Launch sequential overnight runner (detached)
    runner = _ELIN / "elin_overnight_mesh_run.py"
    runner.write_text(
        f'''#!/usr/bin/env python3
import subprocess, sys
from pathlib import Path
ROOT = Path(r"{_ROOT}")
BATCH = Path(r"{_BATCH}")
IDS = Path(r"{list_path}").read_text(encoding="utf-8").split()
py = sys.executable
log = Path(r"{_ELIN}") / "overnight_mesh.log"
with log.open("a", encoding="utf-8") as fh:
    fh.write(f"start {{len(IDS)}} jobs\\n")
for i, jid in enumerate(IDS, 1):
    print(f"[{{i}}/{{len(IDS)}}] {{jid}}", flush=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"[{{i}}/{{len(IDS)}}] {{jid}}\\n")
    r = subprocess.run(
        [py, str(BATCH), "run", "--id", jid, "--force"],
        cwd=str(ROOT),
    )
    if r.returncode != 0:
        with log.open("a", encoding="utf-8") as fh:
            fh.write(f"FAIL {{jid}} code={{r.returncode}}\\n")
        # continue overnight rather than abort the whole set
        continue
print("done")
''',
        encoding="utf-8",
    )
    # Start detached on Windows
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS  # type: ignore[attr-defined]
    log = _ELIN / "overnight_mesh.log"
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"\n=== launching {len(ids)} ===\n")
    subprocess.Popen(
        [sys.executable, str(runner)],
        cwd=str(_ROOT),
        creationflags=creationflags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"overnight runner launched ({len(ids)} jobs). log: {log}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("rework", "register-meshes", "profiles", "start-batch", "all"):
        p = sub.add_parser(name)
        p.add_argument("--system", default="all")
        if name in ("start-batch", "all"):
            p.add_argument(
                "--kind",
                default="projectile",
                choices=("projectile", "fx", "both"),
            )
    args = ap.parse_args()
    system = args.system.strip().lower() or None
    if system == "all":
        system = None

    if args.cmd in ("rework", "all"):
        _, n = rework_catalog(system)
        print(f"reworked {n} Elin spells (system={system or 'all'})")
        nprof = write_profiles(system)
        print(f"ElinRuntime profiles {nprof}")
    if args.cmd == "profiles":
        write_profiles(system)
    if args.cmd in ("register-meshes", "all"):
        register_meshes(system)
    if args.cmd in ("start-batch", "all"):
        return start_batch(system, args.kind)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
