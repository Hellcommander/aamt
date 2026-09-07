#!/usr/bin/env python3
"""
Generate Smog Devil gfx drafts via Ollama (11434) + SD3.5 (1338).

By default writes ONLY to Tools\\Output\\SmogDevilAssets for review.
Does NOT copy Pillow placeholders into the live mod.

  python generate_smog_devil_assets.py
  python generate_smog_devil_assets.py --install-mod   # after you approve quality
  python generate_smog_devil_assets.py --main-only
  python generate_smog_devil_assets.py --limit 3
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS))

from tome_sd_pipeline import generate_tome_icon, ollama_ready, sd_ready  # noqa: E402

_SHARED = TOOLS.parent / "Shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
from sd_server_lifecycle import managed_sd_server  # noqa: E402

MOD = Path(r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\addons\tome-smog-devil-class")
OUTPUT = Path(r"D:\games\Steam\steamapps\common\Transcendence\Tools\Output\SmogDevilAssets")
TALENTS_JSON = Path(__file__).resolve().parent / "smog_devil_talents.json"

MAIN_ASSETS = [
    {"name": "steam_staff", "kind": "item", "theme": "steam", "outdir": "objects",
     "description": "brass and iron steamtech wizard staff with pressure gauges and vents"},
    {"name": "steam_overload", "kind": "effect", "theme": "steam", "outdir": "effects",
     "description": "bursting pressurized steam overload aura"},
    {"name": "steam_mana_converter", "kind": "effect", "theme": "arcane", "outdir": "effects",
     "description": "steam pipes converting violet mana into white vapor"},
    {"name": "steam_mana_symphony", "kind": "effect", "theme": "arcane", "outdir": "effects",
     "description": "harmonized steam and arcane rings"},
    {"name": "smog_devil_apotheosis", "kind": "effect", "theme": "dark", "outdir": "effects",
     "description": "demonic smog apotheosis silhouette with brass halo"},
    {"name": "smog_condenser", "kind": "effect", "theme": "steam", "outdir": "effects",
     "description": "condensing green-gray smog into droplets"},
    {"name": "smog_focal_mark", "kind": "effect", "theme": "arcane", "outdir": "effects",
     "description": "focus lens targeting mark through toxic haze"},
    {"name": "smog_trajectory", "kind": "effect", "theme": "steam", "outdir": "effects",
     "description": "curving trajectory gears through smog"},
    {"name": "refined_arcane_gem", "kind": "item", "theme": "arcane", "outdir": "objects",
     "description": "faceted arcane gem refined for steam staff ammo"},
]


def theme_for_talent(name: str) -> str:
    low = name.lower()
    if any(k in low for k in ("corrupt", "vim", "dark", "soul", "hell", "blood", "demonic")):
        return "dark"
    if any(k in low for k in ("arcane", "mana", "prism", "focal", "gauge", "lens")):
        return "arcane"
    if any(k in low for k in ("acid", "ooze", "corros")):
        return "nature"
    return "steam"


def copy_tree_into_mod(src_root: Path, mod_gfx: Path) -> int:
    copied = 0
    for png in src_root.rglob("*.png"):
        rel = png.relative_to(src_root)
        dst = mod_gfx / rel
        # ToME object/ path is singular
        if rel.parts and rel.parts[0] == "objects":
            alt = mod_gfx / "object" / Path(*rel.parts[1:])
            alt.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(png, alt)
            meta = png.with_suffix(".meta.json")
            if meta.exists():
                shutil.copy2(meta, alt.with_suffix(".meta.json"))
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(png, dst)
        meta = png.with_suffix(".meta.json")
        if meta.exists():
            shutil.copy2(meta, dst.with_suffix(".meta.json"))
        copied += 1
    return copied


def main() -> int:
    ap = argparse.ArgumentParser(description="Smog Devil Ollama+SD asset drafts")
    ap.add_argument("--install-mod", action="store_true",
                    help="Copy approved drafts from Output into the live addon")
    ap.add_argument("--main-only", action="store_true", help="Skip talent icons")
    ap.add_argument("--talents-only", action="store_true", help="Skip main assets")
    ap.add_argument("--limit", type=int, default=0, help="Max assets to generate (0=all)")
    ap.add_argument("--seed", type=int, default=42000)
    ap.add_argument(
        "--ollama-prompt",
        action="store_true",
        help="Ask Ollama for SD prompts (slow/VRAM-heavy while SD is loaded; default=off)",
    )
    ap.add_argument(
        "--keep-server",
        action="store_true",
        help="Leave SD server running after this job (default: stop to free GPU)",
    )
    args = ap.parse_args()

    print("Smog Devil asset pipeline (Ollama :11434 -> SD3.5 :1338)")
    print(f"  Ollama ready: {ollama_ready()}")
    print(f"  SD ready:     {sd_ready()}")

    # Refresh talent list
    extract = Path(__file__).resolve().parent / "extract_smog_devil_talents.py"
    if extract.exists() and not args.main_only:
        import runpy
        runpy.run_path(str(extract))

    OUTPUT.mkdir(parents=True, exist_ok=True)
    made = 0
    failed = 0
    seed = args.seed
    budget = args.limit if args.limit > 0 else 10**9

    with managed_sd_server(keep=args.keep_server) as ready:
        if not ready:
            print("ERROR: could not start SD server on :1338.")
            return 1

        if not args.talents_only:
            for spec in MAIN_ASSETS:
                if made >= budget:
                    break
                out = OUTPUT / spec["outdir"] / f"{spec['name']}.png"
                print(f"\n=== {spec['name']} ===")
                meta = generate_tome_icon(
                    spec["name"],
                    out,
                    kind=spec["kind"],
                    theme=spec["theme"],
                    description=spec["description"],
                    seed=seed,
                    require_sd=True,
                    use_ollama_prompt=args.ollama_prompt,
                )
                seed += 17
                if meta.get("ok"):
                    made += 1
                    print(f"  OK -> {out}")
                else:
                    failed += 1
                    print(f"  FAIL: {meta.get('error')}")

        if not args.main_only and made < budget and TALENTS_JSON.exists():
            talents = json.loads(TALENTS_JSON.read_text(encoding="utf-8"))
            tdir = OUTPUT / "talents"
            tdir.mkdir(parents=True, exist_ok=True)
            for t in talents:
                if made >= budget:
                    break
                sid = t.get("short_name") or t["id"].replace("T_", "", 1)
                icon_name = (t.get("icon") or f"t_{sid.lower()}.png").replace(".png", "")
                name = t.get("name") or sid
                print(f"\n=== Talent {t['id']} ===")
                meta = generate_tome_icon(
                    icon_name,
                    tdir / f"{icon_name}.png",
                    kind="talent",
                    theme=theme_for_talent(name),
                    description=name,
                    seed=seed,
                    require_sd=True,
                    use_ollama_prompt=args.ollama_prompt,
                )
                seed += 13
                if meta.get("ok"):
                    made += 1
                    print(f"  OK -> {icon_name}.png")
                else:
                    failed += 1
                    print(f"  FAIL: {meta.get('error')}")

    print("\n" + "=" * 60)
    print(f"Drafts written: {made}  failed: {failed}")
    print(f"Output: {OUTPUT}")
    print("Review PNGs before installing into the mod.")

    if args.install_mod:
        if failed and made == 0:
            print("Nothing good to install.")
            return 1
        n = copy_tree_into_mod(OUTPUT, MOD / "data" / "gfx")
        print(f"Installed {n} PNGs into {MOD / 'data' / 'gfx'}")
        print("Wire image= paths only for assets that clearly beat vanilla refs.")
    else:
        print("Tip: re-run with --install-mod after visual review.")
    print("=" * 60)
    return 0 if made else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Interrupted")
        sys.exit(1)
