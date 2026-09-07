#!/usr/bin/env python3
"""
Generate Mawborn Astromancer corruption talent icons via SD3.5 (:1338).

  python generate_astro_corruption_assets.py
  python generate_astro_corruption_assets.py --install-mod --wire-images
  python generate_astro_corruption_assets.py --limit 5
  python generate_astro_corruption_assets.py --install-mod --skip-generate --wire-images
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS))

from tome_sd_pipeline import generate_tome_icon, ollama_ready, sd_ready  # noqa: E402

_SHARED = Path(__file__).resolve().parents[2] / "Shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
from sd_server_lifecycle import managed_sd_server  # noqa: E402

MOD = Path(
    r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\addons\tome-mawborn-astromancer-corruptions"
)
OUTPUT = Path(r"D:\games\Ai assisted toolkit\Tools\Output\AstromancerCorruptions")
TALENTS_LUA = MOD / "data" / "talents" / "astromancer_corruptions.lua"

ART = (
    "twisted eldritch body-horror, bloated flesh, jagged teeth, green bile, "
    "void-purple hunger, visceral demented cult, corrupted celestial planet magic"
)

# short_name, display name, theme, subject description
ICONS: List[Dict[str, str]] = [
    {"id": "MAWBORN_ASTRO_GWELGOROTH", "name": "Devouring Gale", "theme": "acid",
     "desc": "ravenous bile air elemental horror with a toothy maw in a green gale"},
    {"id": "MAWBORN_ASTRO_VOLTAIC_CHAIN", "name": "Digestive Chain", "theme": "lightning",
     "desc": "chain of acidic lightning linking toothy maws, green-gold sparks"},
    {"id": "MAWBORN_ASTRO_VOLTAIC_STORM", "name": "Bile Storm", "theme": "acid",
     "desc": "swirling storm of digestive bile bolts around a hungry silhouette"},
    {"id": "MAWBORN_ASTRO_SHIVGOROTH", "name": "Frozen Maw", "theme": "ice",
     "desc": "armored ice horror with a frozen gaping maw dripping green bile"},
    {"id": "MAWBORN_ASTRO_GLACIAL_PATH", "name": "Digestive Path", "theme": "acid",
     "desc": "cone of slime-ice path with a skate of teeth and bile"},
    {"id": "MAWBORN_ASTRO_FAEROS", "name": "Consuming Flame", "theme": "fire",
     "desc": "dark hungry fire elemental with a maw of green-black flame"},
    {"id": "MAWBORN_ASTRO_VOLCANO", "name": "Bile Geyser", "theme": "acid",
     "desc": "terrain geyser spewing digestive acid, toothy crater"},
    {"id": "MAWBORN_ASTRO_METEOR_STORM", "name": "Bile Rain", "theme": "acid",
     "desc": "rain of bile meteors falling from a hungry star-maw sky"},
    {"id": "MAWBORN_ASTRO_STARSTRIKE", "name": "Maw Strike", "theme": "dark",
     "desc": "concentrated falling maw-meteor crushing the ground in acid"},
    {"id": "MAWBORN_ASTRO_HARMONIC_FEEDBACK", "name": "Hunger Feedback", "theme": "dark",
     "desc": "orbiting planetary rings bitten into by a central endless maw"},
    {"id": "MAWBORN_ASTRO_ELEMENTAL_TRANSPOSITION", "name": "Consumption Swap", "theme": "dark",
     "desc": "two silhouettes swapping through a dimensional mouth"},
    {"id": "MAWBORN_ASTRO_NENAGOROTH", "name": "Digestive Tide", "theme": "acid",
     "desc": "bloated water horror dissolving prey in digestive tide"},
    {"id": "MAWBORN_ASTRO_WHIRLPOOL", "name": "Stomach Vortex", "theme": "acid",
     "desc": "vortex of stomach acid pulling figures into a central maw"},
    {"id": "MAWBORN_ASTRO_CHILL", "name": "Numbing Bile", "theme": "acid",
     "desc": "sphere of numbing green bile with frost-teeth rim"},
    {"id": "MAWBORN_ASTRO_TECTONIC_FISSURE", "name": "Bile Fissure", "theme": "acid",
     "desc": "cracked ground fissure vomiting digestive bile"},
    {"id": "MAWBORN_ASTRO_FIERY_PURGE", "name": "Bile Purge", "theme": "healing",
     "desc": "figure purging afflictions as a spray of cleansing bile"},
    {"id": "MAWBORN_ASTRO_EVASIVE_GUST", "name": "Digestive Wind", "theme": "acid",
     "desc": "miasma wind of bile slowing arrows around a hungry silhouette"},
    {"id": "MAWBORN_ASTRO_BRIGHT_LIGHTNING", "name": "Corrupted Lightning", "theme": "lightning",
     "desc": "beam of acid-green lightning mixed with hunger-purple sparks"},
    {"id": "MAWBORN_ASTRO_ICE_STORM", "name": "Acid Storm", "theme": "acid",
     "desc": "furious acid ice-storm ring around a caster"},
    {"id": "MAWBORN_ASTRO_ICY_BLOCK", "name": "Digestive Shield", "theme": "acid",
     "desc": "protective shell of digestive acid with retaliating teeth"},
    {"id": "MAWBORN_ASTRO_UNDERTOW", "name": "Digestive Pull", "theme": "acid",
     "desc": "tendril of acid undertow dragging a figure toward a maw"},
    {"id": "MAWBORN_ASTRO_WATER_WHIP", "name": "Acid Whip", "theme": "acid",
     "desc": "lash of acidic water-whip ending in a small biting maw"},
    {"id": "MAWBORN_ASTRO_FLASH_FLOOD", "name": "Bile Flood", "theme": "acid",
     "desc": "flood of bile covering a ruined tile, slow green tide"},
    {"id": "MAWBORN_ASTRO_DANCING_WAVES", "name": "Hunger Waves", "theme": "healing",
     "desc": "rippling hunger-waves of bile around a moving figure, life-steal glow"},
    {"id": "MAWBORN_ASTRO_DROWNING_DEPTHS", "name": "Digestive Depths", "theme": "dark",
     "desc": "summon vanishing into a pit-maw dragging enemies down"},
    {"id": "MAWBORN_ASTRO_FLAME_BOLTS", "name": "Bile Bolts", "theme": "acid",
     "desc": "volley of bile-fire bolts from a hungry caster"},
    {"id": "MAWBORN_ASTRO_PLANETARY_CONVERGENCE", "name": "Hunger Convergence", "theme": "dark",
     "desc": "three corrupted planets aligning into a single hungry maw-eclipse"},
    {"id": "MAWBORN_ASTRO_CORROSIVE_VAPOUR", "name": "Digestive Miasma", "theme": "acid",
     "desc": "lingering cloud of digestive miasma with tooth-shaped vapours"},
    {"id": "MAWBORN_ASTRO_ICE_VAPOR", "name": "Hungering Frost", "theme": "ice",
     "desc": "frost vapour mixed with green bile, hungry ice crystals"},
    {"id": "MAWBORN_ASTRO_ICE_SPEED", "name": "Digestive Skate", "theme": "acid",
     "desc": "figure skating a bile-ice corridor leaving an acid trail"},
    {"id": "MAWBORN_ASTRO_BLIGHTED_MANAWORM", "name": "Gutworm", "theme": "acid",
     "desc": "parasitic gut-worm of bile and stolen mana, coiled and toothy"},
    {"id": "MAWBORN_ASTRO_VOID_SUMMONS", "name": "Maw Void Riders", "theme": "dark",
     "desc": "tiny void-hunger horrors riding a falling bile meteor"},
    {"id": "MAWBORN_ASTRO_MICROMETEOR", "name": "Bile Needle", "theme": "acid",
     "desc": "tiny falling bile meteorite needle striking from above"},
    {"id": "MAWBORN_ASTRO_BOMBARDMENT", "name": "Bile Bombardment", "theme": "acid",
     "desc": "spellburst synchronized with a shower of tiny bile meteors"},
    {"id": "MAWBORN_ASTRO_METEOR_SHOWER", "name": "Bile Shower", "theme": "acid",
     "desc": "wilder extra bile meteor falling beside a larger rain"},
    {"id": "MAWBORN_ASTRO_PAEAN_KOLAL", "name": "Hymn of Gastric Fire", "theme": "fire",
     "desc": "close-combat hymn shield of gastric fire and biting teeth"},
    {"id": "MAWBORN_ASTRO_PAEAN_LUXAM", "name": "Hymn of Frozen Maw", "theme": "ice",
     "desc": "icy hymn-shield with a frozen maw swallowing a critical star"},
    {"id": "MAWBORN_ASTRO_PAEAN_PONX", "name": "Hymn of Digestive Wind", "theme": "healing",
     "desc": "cleansing digestive wind hymn, green gale around a surviving silhouette"},
    {"id": "MAWBORN_ASTRO_PAEAN_ACOLYTE", "name": "Hymn Acolyte", "theme": "dark",
     "desc": "three hymn-planets as bitten celestial discs around a singing maw"},
    {"id": "MAWBORN_ASTRO_PAEAN_ORATOR", "name": "Hymn Herald", "theme": "acid",
     "desc": "orator cloak of elemental bile, retaliating acid sparks"},
    {"id": "MAWBORN_ASTRO_PAEAN_ADEPT", "name": "Hymn Adept", "theme": "dark",
     "desc": "adept hymn cloak extending into planetary acid affinities"},
    {"id": "MAWBORN_ASTRO_PAEAN_MAELSTROM", "name": "Hymn Maelstrom", "theme": "acid",
     "desc": "maelstrom of bile penetrating planetary resists, spinning maw"},
    {"id": "MAWBORN_ASTRO_SWIFT_ARRIVAL", "name": "Swift Gorge", "theme": "dark",
     "desc": "multiple hungry summons bursting from a single swallowing gesture"},
    {"id": "MAWBORN_ASTRO_TELUVORATA", "name": "Hungering Chronomaul", "theme": "dark",
     "desc": "time-storm horror with a clock-maw eating seconds, acid-purple"},
    {"id": "MAWBORN_ASTRO_TIME_SLIDE", "name": "Stomach Exile", "theme": "dark",
     "desc": "enemy vanishing into a stomach-pocket of future digestion"},
    {"id": "MAWBORN_ASTRO_TIME_BOOST", "name": "Hunger Threads", "theme": "dark",
     "desc": "braided hunger-threads of bile time speeding allied horrors"},
    {"id": "MAWBORN_ASTRO_TIME_FLOOD", "name": "Hunger Flood", "theme": "dark",
     "desc": "flood of raw hunger-time energy rushing through a caster"},
]


def icon_stem(talent_id: str) -> str:
    return talent_id.lower()


def image_path(talent_id: str) -> str:
    return f"talents/{icon_stem(talent_id)}.png"


def talent_has_image(file_path: Path, talent_id: str) -> bool:
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError:
        return False
    parts = re.split(r"newTalent\s*\{", text)
    for part in parts[1:]:
        if re.search(rf'short_name\s*=\s*"{re.escape(talent_id)}"', part):
            head = part[:8000]
            return bool(re.search(r"(?m)^\s*image\s*=", head))
    return False


def wire_image_into_lua(file_path: Path, talent_id: str, rel_image: str) -> bool:
    text = file_path.read_text(encoding="utf-8")
    pat_existing = re.compile(
        rf'(?m)^([ \t]*)(.*\bshort_name\s*=\s*"{re.escape(talent_id)}"\s*,?\s*)\n([ \t]*)image\s*=\s*"[^"]+"\s*,?'
    )

    def repl_existing(m: re.Match) -> str:
        return f'{m.group(1)}{m.group(2)}\n{m.group(3)}image = "{rel_image}",'

    new_text, n = pat_existing.subn(repl_existing, text, count=1)
    if n:
        file_path.write_text(new_text, encoding="utf-8")
        return True

    def repl_line(m: re.Match) -> str:
        indent = m.group(1)
        rest = m.group(2)
        return f'{indent}{rest}\n{indent}image = "{rel_image}",'

    pat_short = re.compile(
        rf'(?m)^([ \t]*)(.*\bshort_name\s*=\s*"{re.escape(talent_id)}"\s*,?\s*)$'
    )
    new_text, n = pat_short.subn(repl_line, text, count=1)
    if n == 0:
        return False
    file_path.write_text(new_text, encoding="utf-8")
    return True


def install_pngs(src_root: Path, mod: Path) -> int:
    copied = 0
    for png in src_root.rglob("*.png"):
        if png.name.startswith("_"):
            continue
        rel = png.relative_to(src_root)
        for base in (mod / "data" / "gfx", mod / "overload" / "data" / "gfx"):
            dst = base / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(png, dst)
            meta = png.with_suffix(".meta.json")
            if meta.exists():
                shutil.copy2(meta, dst.with_suffix(".meta.json"))
            copied += 1
    return copied


def main() -> int:
    ap = argparse.ArgumentParser(description="Astromancer Maw corruption SD talent icons")
    ap.add_argument("--install-mod", action="store_true")
    ap.add_argument("--wire-images", action="store_true")
    ap.add_argument("--skip-generate", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--seed", type=int, default=91000)
    ap.add_argument("--ollama-prompt", action="store_true")
    ap.add_argument("--keep-server", action="store_true")
    args = ap.parse_args()

    print("Astromancer Maw corruption asset pipeline (SD3.5 :1338)")
    print(f"  Ollama ready: {ollama_ready()}")
    print(f"  SD ready:     {sd_ready()}")
    print(f"  Icons:        {len(ICONS)}")

    targets = list(ICONS)
    budget = args.limit if args.limit > 0 else 10**9
    made = 0
    failed = 0
    seed = args.seed

    if not args.skip_generate:
        with managed_sd_server(keep=args.keep_server) as ready:
            if not ready:
                print("ERROR: could not start SD server on :1338.")
                return 1
            tdir = OUTPUT / "talents"
            tdir.mkdir(parents=True, exist_ok=True)
            for t in targets:
                if made + failed >= budget:
                    break
                tid = t["id"]
                stem = icon_stem(tid)
                out = tdir / f"{stem}.png"
                print(f"\n=== {tid} ({t['name']}) [{t['theme']}] ===")
                meta = generate_tome_icon(
                    stem,
                    out,
                    kind="talent",
                    theme=t["theme"],
                    description=f"{t['name']}: {t['desc']}. {ART}",
                    seed=seed,
                    require_sd=True,
                    use_ollama_prompt=args.ollama_prompt,
                )
                seed += 17
                if meta.get("ok"):
                    made += 1
                    print(f"  OK -> {out.name}")
                else:
                    failed += 1
                    print(f"  FAIL: {meta.get('error')}")

            print("\n" + "=" * 60)
            print(f"Drafts written: {made}  failed: {failed}")
            print(f"Output: {OUTPUT}")

    copied = 0
    if args.install_mod:
        copied = install_pngs(OUTPUT, MOD)
        print(f"Installed {copied} files into addon data/ + overload/")

    wired = 0
    if args.wire_images and TALENTS_LUA.exists():
        for t in targets:
            tid = t["id"]
            stem = icon_stem(tid)
            out_png = OUTPUT / "talents" / f"{stem}.png"
            mod_png = MOD / "data" / "gfx" / "talents" / f"{stem}.png"
            if not out_png.exists() and not mod_png.exists():
                continue
            if wire_image_into_lua(TALENTS_LUA, tid, image_path(tid)):
                wired += 1
                print(f"  wired image= for {tid}")
        print(f"Wired {wired} talent image= lines")

    print("Done.")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
