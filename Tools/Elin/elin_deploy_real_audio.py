#!/usr/bin/env python3
"""Generate Workshop-style Sound/ clips for CustomRaceClassCreator.

Retrieves matching SFX from D:\\assets\\audio (Dark Fantasy Studio packs, etc.)
then conditions Stable Audio 3 (`init_audio`) so every clip is new audio,
not a raw library copy and not a numpy sine.

Writes:
  <mod>/Sound/<id>.wav          CWL + ModSoundLoader
  <mod>/Sound/<id>.json         CWL SoundData sidecar
  Tools/Elin/Output/Audio/*.meta.json

  python elin_deploy_real_audio.py
  python elin_deploy_real_audio.py --skip-existing
  python elin_deploy_real_audio.py --only ab_firebreath,DragonMagic_cast
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_ELIN_TOOLS = Path(__file__).resolve().parent
_SHARED = _ELIN_TOOLS.parent / "Shared"
if _SHARED.is_dir() and str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

_DEFAULT_MOD = Path(r"E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator")
_CATALOG = _ELIN_TOOLS / "elin_asset_catalog.json"
_OUTPUT = _ELIN_TOOLS / "Output" / "Audio"

SIDECAR = {
    "id": -1,
    "allowMultiple": True,
    "chance": 1.0,
    "pitch": 1.0,
    "reverbMix": 1.0,
    "volume": 0.55,
}

# Prompts tuned to Dark Fantasy Studio spell/creature/impact packs.
SYSTEM_AUDIO: Dict[str, Dict[str, Any]] = {
    "DragonMagic": {
        "archetype": "organic",
        "tags": ["dragon", "fire", "spell"],
        "cast": "short dragon fire-breath roar whoosh, fantasy spell cast, ember crackle, punchy game SFX",
        "impact": "heavy dragon flame impact burst, scorching hit, short game SFX",
    },
    "DreamMagic": {
        "archetype": "magic",
        "tags": ["ghostly", "spell", "portal"],
        "cast": "ethereal dream chime whoosh, soft indigo magic cast, glassy shimmer, short game SFX",
        "impact": "dreamy magic pop impact, soft crystal shatter, short game SFX",
    },
    "ElementMagic": {
        "archetype": "magic",
        "tags": ["spell", "electric", "fire"],
        "cast": "four-element spell cast, fire ice stone wind layered whoosh, short game SFX",
        "impact": "elemental collision impact, crackling burst, short game SFX",
    },
    "WispMagic": {
        "archetype": "magic",
        "tags": ["spell", "electric"],
        "cast": "tiny wisp spirit whoosh, airy lantern flare, high glassy sparkle, short game SFX",
        "impact": "wisp burst ping, luminous pop, short game SFX",
    },
    "DruidicMagic": {
        "archetype": "organic",
        "tags": ["spell", "wood", "earth"],
        "cast": "living vines grow whoosh, druid nature magic cast, leaves and bark, short game SFX",
        "impact": "root slam impact, wooden thud with leaves, short game SFX",
    },
    "Crossmagic": {
        "archetype": "magic",
        "tags": ["spell", "chaos", "portal"],
        "cast": "fused schools prism cast, overlapping magic whooshes, short game SFX",
        "impact": "rune prism shatter impact, layered magic hit, short game SFX",
    },
    "RiverMagic": {
        "archetype": "water",
        "tags": ["water", "spell"],
        "cast": "rushing river current spell cast, water whoosh, short game SFX",
        "impact": "water splash impact, wet burst, short game SFX",
    },
    "Pollution": {
        "archetype": "horror",
        "tags": ["slime", "spell", "horror"],
        "cast": "toxic sludge gurgle spell cast, bubbling acid fumes, short game SFX",
        "impact": "poison sludge splat impact, corrosive burst, short game SFX",
    },
    "ArcaneSaturation": {
        "archetype": "magic",
        "tags": ["spell", "power"],
        "cast": "overflowing mana flask surge, violet energy swell, short game SFX",
        "impact": "mana overflow pop, arcane burst, short game SFX",
    },
    "BardicMagic": {
        "archetype": "magic",
        "tags": ["bell", "spell"],
        "cast": "fantasy lute strum with magic shimmer, bardic spell cast, short game SFX",
        "impact": "magical chord resolve hit, lute impact, short game SFX",
    },
    "SpiritMagic": {
        "archetype": "horror",
        "tags": ["ghostly", "spell"],
        "cast": "ancestral spirit whisper whoosh, pale ethereal cast, short game SFX",
        "impact": "spirit strike, cold ghostly hit, short game SFX",
    },
    "Geomancy": {
        "archetype": "impact",
        "tags": ["earth", "rocks", "spell"],
        "cast": "stone grinding earth spell cast, rumbling rock whoosh, short game SFX",
        "impact": "boulder slam impact, rock crush, short game SFX",
    },
    "Necromancy": {
        "archetype": "horror",
        "tags": ["ghostly", "flesh", "spell"],
        "cast": "bone phylactery necromancy cast, soulfire hiss, short game SFX",
        "impact": "bone crack soul burst impact, dark magic hit, short game SFX",
    },
    "BloodMagic": {
        "archetype": "organic",
        "tags": ["flesh", "blood", "spell"],
        "cast": "visceral blood magic cast, wet crimson whoosh, short game SFX",
        "impact": "blood burst impact, fleshy splat, short game SFX",
    },
    "Golemancy": {
        "archetype": "mech",
        "tags": ["metallic", "earth", "spell"],
        "cast": "clay golem rune ignite, stone mechanism grind, short game SFX",
        "impact": "golem fist slam, heavy stone hit, short game SFX",
    },
    "SpectreMagic": {
        "archetype": "horror",
        "tags": ["ghostly", "spell"],
        "cast": "cold spectre veil whoosh, pale blue ghost cast, short game SFX",
        "impact": "chill ghost strike, icy spectral hit, short game SFX",
    },
    "Technomancy": {
        "archetype": "mech",
        "tags": ["electric", "metallic", "spell"],
        "cast": "arcane clockwork gadget spin-up, brass spark spell, short game SFX",
        "impact": "steam-crystal shock hit, mechanical magic impact, short game SFX",
    },
    "TerrainMagic": {
        "archetype": "impact",
        "tags": ["earth", "rocks", "spell"],
        "cast": "terrain shift rumble, mountain shrine spell, short game SFX",
        "impact": "cliff slam impact, earth crack, short game SFX",
    },
    "WeatherMagic": {
        "archetype": "magic",
        "tags": ["thunder", "wind", "spell"],
        "cast": "storm bottle lightning swell, wind and thunder spell cast, short game SFX",
        "impact": "thunderclap impact, weather strike, short game SFX",
    },
    "RuneMagic": {
        "archetype": "magic",
        "tags": ["spell", "power"],
        "cast": "carved rune tablet ignite, ancient sigil hum, short game SFX",
        "impact": "rune detonate impact, carved stone magic hit, short game SFX",
    },
    "EtherwindMagic": {
        "archetype": "magic",
        "tags": ["wind", "spell", "portal"],
        "cast": "ether crystal wind trail whoosh, translucent gust spell, short game SFX",
        "impact": "ether gust slap, air magic hit, short game SFX",
    },
    "Geoscience": {
        "archetype": "impact",
        "tags": ["earth", "rocks", "spell"],
        "cast": "geological core sample resonate, survey crystal hum, short game SFX",
        "impact": "core sample crack impact, mineral hit, short game SFX",
    },
    "DynamicSpells": {
        "archetype": "magic",
        "tags": ["chaos", "spell", "portal"],
        "cast": "morphing spell orb shifting forms, unstable magic whoosh, short game SFX",
        "impact": "unstable magic snap impact, form-shift hit, short game SFX",
    },
    "SlotMagic": {
        "archetype": "ui",
        "tags": ["interface", "spell"],
        "cast": "enchanted slot-reel spin magic, mystical click-whoosh, short game SFX",
        "impact": "reel lock ding with magic spark, short game SFX",
    },
    "PactMagic": {
        "archetype": "horror",
        "tags": ["spell", "horror"],
        "cast": "demonic contract seal slam, chain rattle magic, short game SFX",
        "impact": "pact brand burn impact, wax seal crack, short game SFX",
    },
    "RitualMagic": {
        "archetype": "magic",
        "tags": ["spell", "bell"],
        "cast": "ritual candle circle ignite, chalk rune hum, short game SFX",
        "impact": "ritual complete chime hit, short game SFX",
    },
    "SlotMachine": {
        "archetype": "ui",
        "tags": ["interface", "metallic"],
        "cast": "ornate fantasy slot machine lever pull, gem reels spin whoosh, short game SFX",
        "impact": "slot reels lock with gold ding and coin clink, short game SFX",
    },
    "AIAssistant": {
        "archetype": "magic",
        "tags": ["spell", "electric", "interface"],
        "cast": "crystal thinking orb ignite, delicate circuit chime, short game SFX",
        "impact": "AI insight ping, glassy crystal confirm, short game SFX",
    },
    "PCCMutation": {
        "archetype": "organic",
        "tags": ["flesh", "spell", "slime"],
        "cast": "mutation vial swirl, biomorphic essence gurgle, short game SFX",
        "impact": "mutation take hold, wet morph snap, short game SFX",
    },
    "QuestPlus": {
        "archetype": "ui",
        "tags": ["interface", "paper"],
        "cast": "quest scroll unfurl, wax seal crack, parchment rustle, short game SFX",
        "impact": "quest stamp confirm, compass tick, short game SFX",
    },
    "SpriteAlter": {
        "archetype": "magic",
        "tags": ["spell", "interface"],
        "cast": "magic paintbrush stroke, pigment gem sparkle, short game SFX",
        "impact": "sprite paint splash, color shift pop, short game SFX",
    },
    "CombatPlus": {
        "archetype": "impact",
        "tags": ["metallic", "combat"],
        "cast": "crossed weapons clash ready, battle crest ring, short game SFX",
        "impact": "heavy weapon hit, steel impact, short game SFX",
    },
}

ABILITY_JOBS: List[Dict[str, Any]] = [
    {"id": "ab_firebreath", "archetype": "fire", "tags": ["fire", "dragon", "spell"],
     "prompt": "dragon fire breath blast, roaring flame whoosh, short fantasy game SFX", "duration": 1.15},
    {"id": "ab_icebreath", "archetype": "water", "tags": ["ice", "spell", "dragon"],
     "prompt": "freezing ice breath blast, crystalline frost whoosh, short fantasy game SFX", "duration": 1.15},
    {"id": "ab_poisonbreath", "archetype": "organic", "tags": ["slime", "spell"],
     "prompt": "toxic poison breath hiss cloud, noxious spray, short fantasy game SFX", "duration": 1.1},
    {"id": "ab_lightningbreath", "archetype": "laser", "tags": ["electric", "spell", "thunder"],
     "prompt": "lightning breath crackle roar, electric dragon blast, short fantasy game SFX", "duration": 1.0},
    {"id": "ab_acidbreath", "archetype": "organic", "tags": ["slime", "spell"],
     "prompt": "acid breath sizzle spray, corrosive hiss, short fantasy game SFX", "duration": 1.1},
    {"id": "ab_elementalstorm", "archetype": "magic", "tags": ["thunder", "spell", "chaos"],
     "prompt": "elemental storm swirl, fire ice lightning colliding, short fantasy game SFX", "duration": 1.4},
    {"id": "ab_necromancy", "archetype": "horror", "tags": ["ghostly", "flesh", "spell"],
     "prompt": "necromancy soul bind, bone rattle and green fire, short fantasy game SFX", "duration": 1.2},
    {"id": "ab_summon", "archetype": "magic", "tags": ["portal", "spell"],
     "prompt": "creature summon portal open, dimensional whoosh, short fantasy game SFX", "duration": 1.2},
    {"id": "ab_conjure", "archetype": "magic", "tags": ["spell", "power"],
     "prompt": "conjuration sparkle whoosh, materializing magic, short fantasy game SFX", "duration": 0.95},
    {"id": "ab_ether", "archetype": "magic", "tags": ["portal", "spell", "glitch"],
     "prompt": "ether magic warp, glassy dimensional shimmer, short fantasy game SFX", "duration": 1.0},
    {"id": "ab_etherbind", "archetype": "magic", "tags": ["portal", "spell"],
     "prompt": "ether bind chains latch, spatial lock, short fantasy game SFX", "duration": 0.9},
    {"id": "ab_ethershroud", "archetype": "ambience", "tags": ["wind", "ghostly", "spell"],
     "prompt": "ether shroud wrap, muffled veil whoosh, short fantasy game SFX", "duration": 1.2},
    {"id": "ab_etheranchor", "archetype": "impact", "tags": ["metallic", "spell"],
     "prompt": "ether anchor slam, heavy spatial lock thud, short fantasy game SFX", "duration": 0.85},
    {"id": "ab_etherrift", "archetype": "magic", "tags": ["portal", "spell", "rip"],
     "prompt": "ether rift tear open, ripping dimensional burst, short fantasy game SFX", "duration": 1.15},
    {"id": "ab_web", "archetype": "organic", "tags": ["insects", "spell"],
     "prompt": "spider web shoot and stick, silk snap, short fantasy game SFX", "duration": 0.75},
    {"id": "ab_trap", "archetype": "mech", "tags": ["metallic", "spell"],
     "prompt": "magical trap snap shut, mechanical click and bind, short fantasy game SFX", "duration": 0.7},
    {"id": "ab_wrap", "archetype": "organic", "tags": ["spell", "wood"],
     "prompt": "vines wrap and constrict, tight squeeze whoosh, short fantasy game SFX", "duration": 0.85},
    {"id": "ab_swarm", "archetype": "alien", "tags": ["insects", "spell"],
     "prompt": "insect swarm burst, buzzing wings rush, short fantasy game SFX", "duration": 1.1},
    {"id": "ward", "archetype": "magic", "tags": ["spell", "power"],
     "prompt": "protective ward shield form, magic barrier hum, short fantasy game SFX", "duration": 0.9},
    {"id": "transmute", "archetype": "magic", "tags": ["spell", "glitch"],
     "prompt": "alchemical transmute morph, bubbling material shift, short fantasy game SFX", "duration": 0.95},
    {"id": "vine_grow", "archetype": "organic", "tags": ["wood", "spell"],
     "prompt": "rapid vine growth, leaves unfurling loopable whoosh, short fantasy game SFX", "duration": 1.3},
    {"id": "maw_eruption", "archetype": "organic", "tags": ["flesh", "spell"],
     "prompt": "giant plant maw erupts from ground, wet earth burst, short fantasy game SFX", "duration": 1.2},
    {"id": "maw_chomp", "archetype": "organic", "tags": ["flesh", "spell"],
     "prompt": "giant plant maw chomp bite, wet snap, short fantasy game SFX", "duration": 0.55},
    {"id": "acid_hiss", "archetype": "organic", "tags": ["slime", "spell"],
     "prompt": "acid pool hiss and bubble, corrosive steam, short fantasy game SFX", "duration": 1.4},
    {"id": "spit_launch", "archetype": "organic", "tags": ["slime", "spell"],
     "prompt": "acid spit launch, wet projectile whoosh, short fantasy game SFX", "duration": 0.55},
    {"id": "spit_impact", "archetype": "organic", "tags": ["slime", "spell"],
     "prompt": "acid spit splat impact, corrosive splash, short fantasy game SFX", "duration": 0.45},
    {"id": "ui_click", "archetype": "ui", "tags": ["interface"],
     "prompt": "fantasy RPG UI click, wood and brass button, short game SFX", "duration": 0.22},
    {"id": "ui_confirm", "archetype": "ui", "tags": ["interface", "bell"],
     "prompt": "fantasy RPG UI confirm chime, warm brass, short game SFX", "duration": 0.35},
    {"id": "ui_error", "archetype": "ui", "tags": ["interface"],
     "prompt": "fantasy RPG UI error thunk, muted brass deny, short game SFX", "duration": 0.3},
]


def load_heroes() -> List[Dict[str, Any]]:
    if _CATALOG.is_file():
        return json.loads(_CATALOG.read_text(encoding="utf-8")).get("heroes") or []
    return []


def build_jobs() -> List[Dict[str, Any]]:
    jobs: List[Dict[str, Any]] = []
    seen = set()

    def add(job: Dict[str, Any]) -> None:
        jid = job["id"]
        if jid in seen:
            return
        seen.add(jid)
        jobs.append(job)

    for hid, spec in SYSTEM_AUDIO.items():
        add({
            "id": f"{hid}_cast",
            "archetype": spec["archetype"],
            "tags": spec.get("tags") or [],
            "prompt": spec["cast"],
            "duration": 1.05,
        })
        add({
            "id": f"{hid}_impact",
            "archetype": spec.get("impact_archetype") or "impact",
            "tags": spec.get("tags") or [],
            "prompt": spec["impact"],
            "duration": 0.7,
        })

    for job in ABILITY_JOBS:
        add(job)
    return jobs


def write_sidecar(path: Path, sound_id: str, volume: float = 0.55) -> None:
    data = dict(SIDECAR)
    data["$id"] = sound_id
    data["volume"] = volume
    if sound_id.startswith("ui_"):
        data["volume"] = 0.4
        data["reverbMix"] = 0.15
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def deploy_clip(wav_src: Path, sound_dir: Path, sound_id: str) -> None:
    dest_wav = sound_dir / f"{sound_id}.wav"
    shutil.copy2(wav_src, dest_wav)
    write_sidecar(sound_dir / f"{sound_id}.json", sound_id)
    # Optional OGG sibling for smaller Workshop copies — skip; same ID would collide.


def generate_one(job: Dict[str, Any], *, engine: str, model: Optional[str], strength: float) -> Path:
    from audio_pipeline import generate_audio

    out = _OUTPUT / f"{job['id']}.wav"
    tags = job.get("tags") or []
    return generate_audio(
        job["prompt"],
        out,
        duration=float(job.get("duration") or 1.0),
        k=4,
        strength=strength,
        archetype=str(job.get("archetype") or "magic"),
        tags=tags,
        seed=None,
        model_name=model,
        engine=engine,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mod-path", default=str(_DEFAULT_MOD))
    ap.add_argument("--engine", default=os.environ.get("AAMT_AUDIO_ENGINE", "auto"),
                    choices=("auto", "stable-audio", "library"))
    ap.add_argument("--model", default=os.environ.get("AAMT_STABLE_AUDIO_MODEL", "small-sfx"))
    ap.add_argument("--strength", type=float, default=0.7)
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--only", default="", help="Comma-separated sound ids")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    if args.status:
        from audio_pipeline import status
        print(json.dumps(status(), indent=2))
        return 0

    mod = Path(args.mod_path)
    sound_dir = mod / "Sound"
    sound_dir.mkdir(parents=True, exist_ok=True)
    _OUTPUT.mkdir(parents=True, exist_ok=True)

    jobs = build_jobs()
    if args.only:
        want = {x.strip() for x in args.only.split(",") if x.strip()}
        jobs = [j for j in jobs if j["id"] in want]
    if args.limit > 0:
        jobs = jobs[: args.limit]

    print(f"[elin-audio] jobs={len(jobs)} engine={args.engine} model={args.model} strength={args.strength}")
    print(f"[elin-audio] library=D:\\assets\\audio  dest={sound_dir}")

    ok = 0
    skip = 0
    fail = 0
    for i, job in enumerate(jobs, 1):
        dest = sound_dir / f"{job['id']}.wav"
        if args.skip_existing and dest.is_file() and dest.stat().st_size > 2048:
            print(f"[{i}/{len(jobs)}] skip {job['id']}")
            skip += 1
            continue
        print(f"[{i}/{len(jobs)}] {job['id']}  {job['archetype']}  {job['duration']}s", flush=True)
        try:
            wav = generate_one(job, engine=args.engine, model=args.model or None, strength=args.strength)
            if not wav or not Path(wav).is_file():
                raise RuntimeError("no wav written")
            deploy_clip(Path(wav), sound_dir, job["id"])
            ok += 1
            print(f"    wrote Sound/{job['id']}.wav", flush=True)
        except Exception as exc:
            fail += 1
            print(f"    FAIL {job['id']}: {exc}", flush=True)

    summary = {"ok": ok, "skipped": skip, "failed": fail, "jobs": len(jobs), "soundDir": str(sound_dir)}
    (sound_dir / "_deploy_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[elin-audio] DONE {summary}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
