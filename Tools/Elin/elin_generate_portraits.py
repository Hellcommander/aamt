#!/usr/bin/env python3
"""Portraits for the magic systems that have none.

Every system in elin_asset_catalog.json has a patron face, UN_crcc_<system>.png (240x320 in the mod's Portrait
folder). The first 32 were drawn by hand in Cursor; this makes the missing ones with the toolkit's SD3.5 server, in
the same look: an anime bust portrait on plain white, dressed in the system's colours and carrying its relic.

A source picture (832x1216) goes to the catalog's cursorAssetsDir, where elin_deploy_portraits.py looks for it, and
that script then cuts it to 240x320 into the mod. Existing sources and existing portraits are kept.

  python elin_generate_portraits.py                 # every system without a source portrait
  python elin_generate_portraits.py --id ManaMagic  # only these (comma separated)
  python elin_generate_portraits.py --redo --id ManaMagic --seed 3   # draw it again with another seed
  python elin_generate_portraits.py --list          # which are missing; starts nothing

The SD server is started and stopped by the toolkit (sd_server_lifecycle) and every picture goes through the GPU
guard (sd_http_client), so this queues behind any other model job.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

_ELIN = Path(__file__).resolve().parent
_SHARED = _ELIN.parent / "Shared"
for _p in (_ELIN, _SHARED, _ELIN.parent / "Common"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

CATALOG = _ELIN / "elin_asset_catalog.json"

# Who the patron of a system is. Systems not named here get a patron made from the catalog's relic and kind.
PATRONS: Dict[str, str] = {
    "AnimatedServant": "a calm golem-maker, a young woman with clay-dusted hands and short ash-grey hair, brass "
                       "clockwork pauldron, a glowing amber soul-gem pendant on fine chains",
    "VisionSystem": "a sharp-eyed seer, a young man with dark navy hair, an ornate brass scrying monocle over one "
                    "eye with a glowing cyan lens, high-collared dark coat with brass trim",
    "NoiseSystem": "a resonance tuner, a young woman with copper-brown hair in a loose braid, twin brass tuning-fork "
                   "earrings, a dark leather collar with cyan sound-ring embroidery, one hand cupped to her ear",
    "ManaMagic": "a serene mana keeper, a young woman with long pale-blue hair, sapphire crystal circlet, flowing "
                 "robe in sky blue and violet, soft glow of liquid mana at her collar",
    "SpellFusion": "a daring fusion mage, a young man whose hair is flame-orange on one side and frost-blue on the "
                   "other, brass clamps on a split red and blue coat, a small fused crystal at his throat",
}
STYLE = ("anime style fantasy character portrait, bust shot from the chest up, facing the viewer, detailed face, "
         "soft cel shading with fine linework, painterly colours, plain pure white background, no text, no frame")
NEGATIVE = ("text, watermark, signature, frame, border, background scenery, full body, multiple people, extra limbs, "
            "deformed hands, blurry, photo, 3d render, cropped head")


def prompt_for(hero: Dict[str, Any]) -> str:
    who = PATRONS.get(hero["id"]) or (f"the patron of {hero['id']}, a fantasy "
                                      f"{'mage' if hero.get('kind') == 'magic' else 'artisan'} carrying {hero.get('prop', 'a relic')}")
    colours = ", ".join(hero.get("colors") or [])
    return f"{STYLE}, {who}, colour scheme {colours}" if colours else f"{STYLE}, {who}"


def main() -> int:
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", default="", help="system ids, comma separated (default: every system without a source)")
    ap.add_argument("--assets-dir", type=Path, default=Path(cat["cursorAssetsDir"]))
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--steps", type=int, default=28)
    ap.add_argument("--redo", action="store_true", help="draw again even if the source picture exists")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--no-deploy", action="store_true", help="only make the source pictures")
    a = ap.parse_args()

    want = {x.strip().lower() for x in a.id.split(",") if x.strip()}
    heroes: List[Dict[str, Any]] = [h for h in cat["heroes"] if not want or h["id"].lower() in want]
    src = lambda h: a.assets_dir / f"UN_crcc_{h['id'].lower()}.png"   # noqa: E731
    todo = [h for h in heroes if a.redo or not src(h).is_file()]
    print(f"systems {len(heroes)}, without a source portrait {len([h for h in heroes if not src(h).is_file()])}: "
          + ", ".join(h["id"] for h in heroes if not src(h).is_file()))
    if a.list:
        return 0
    failed = 0
    if todo:
        from sd_http_client import generate_image
        from sd_server_lifecycle import managed_sd_server
        a.assets_dir.mkdir(parents=True, exist_ok=True)
        with managed_sd_server(timeout_sec=2400.0) as ready:
            if not ready:
                print("the SD server did not come up; nothing drawn")
                return 1
            for n, h in enumerate(todo, 1):
                out = src(h)
                tmp = out.with_name(out.stem + ".new.png")
                try:
                    generate_image(prompt=prompt_for(h), output_path=tmp, negative_prompt=NEGATIVE, width=832,
                                   height=1216, steps=a.steps, seed=a.seed + n * 101)
                    if out.is_file():      # --redo: keep the old one beside it
                        out.replace(out.with_name(out.stem + ".old.png"))
                    tmp.replace(out)
                    print(f"[{n}/{len(todo)}] {h['id']} -> {out}", flush=True)
                except Exception as exc:
                    failed += 1
                    print(f"[{n}/{len(todo)}] {h['id']} FAILED: {str(exc).splitlines()[-1][:200]}", flush=True)
    if not a.no_deploy:
        cmd = [sys.executable, str(_ELIN / "elin_deploy_portraits.py"), "--assets-dir", str(a.assets_dir)]
        if a.redo and want:
            # only the redrawn ones are replaced in the mod: remove them first, the deploy keeps everything else
            mod = Path(cat["modPath"]) / "Portrait"
            for h in todo:
                old = mod / f"UN_crcc_{h['id'].lower()}.png"
                if old.is_file():
                    old.replace(old.with_name(old.stem + ".old.png.bak"))
        subprocess.run(cmd)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
