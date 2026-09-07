#!/usr/bin/env python3
"""
Generate Glutton Remade talent icons via SD3.5 (:1338).

Targets talents that have no `image =` in their Lua definitions (~72 core trees).
Writes drafts to Tools\\Output\\GluttonAssets, then optionally installs + wires image=.

  python generate_glutton_assets.py
  python generate_glutton_assets.py --install-mod --wire-images
  python generate_glutton_assets.py --limit 5
  python generate_glutton_assets.py --install-mod --skip-generate --wire-images
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS))

from tome_sd_pipeline import generate_tome_icon, ollama_ready, sd_ready  # noqa: E402

_SHARED = Path(__file__).resolve().parents[2] / "Shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
from sd_server_lifecycle import managed_sd_server  # noqa: E402

MOD = Path(r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\addons\tome-glutton-remade")
OUTPUT = Path(r"D:\games\Steam\steamapps\common\Transcendence\Tools\Output\GluttonAssets")
TALENTS_JSON = Path(__file__).resolve().parent / "glutton_remade_talents.json"
EXTRACT = Path(__file__).resolve().parent / "extract_glutton_talents.py"

ART = (
    "twisted eldritch body-horror, bloated flesh, jagged teeth, green bile, "
    "void-purple hunger, visceral demented cult"
)


def theme_for_talent(name: str, talent_id: str) -> str:
    low = f"{name} {talent_id}".lower()
    if any(k in low for k in ("bile", "acid", "corros", "dissolv", "spit", "vomit")):
        return "acid"
    if any(k in low for k in ("fire", "flame", "inferno", "burn")):
        return "fire"
    if any(k in low for k in ("ice", "frost", "cold")):
        return "ice"
    if any(k in low for k in ("lightning", "thunder", "shock")):
        return "lightning"
    if any(k in low for k in ("heal", "regenerat", "resilien", "sated")):
        return "healing"
    return "dark"


def icon_stem(talent_id: str) -> str:
    return talent_id.lower()


def image_path(talent_id: str) -> str:
    return f"talents/{icon_stem(talent_id)}.png"


def refresh_talent_list() -> List[Dict[str, Any]]:
    if EXTRACT.exists():
        import runpy

        runpy.run_path(str(EXTRACT))
    if not TALENTS_JSON.exists():
        return []
    return json.loads(TALENTS_JSON.read_text(encoding="utf-8"))


def talent_has_image(file_path: Path, talent_id: str) -> bool:
    """True if the newTalent block for short_name/id already sets image=."""
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError:
        return False
    # Split roughly on newTalent{; scan the block containing this short_name
    parts = re.split(r"newTalent\s*\{", text)
    for part in parts[1:]:
        if re.search(
            rf'short_name\s*=\s*"{re.escape(talent_id)}"|id\s*=\s*"{re.escape(talent_id)}"',
            part,
        ):
            # End of block at matching depth is hard; stop at next top-level-ish cue
            # Use content until a blank line after a closing `}` near the start of next talent
            head = part[:8000]
            return bool(re.search(r"(?m)^\s*image\s*=", head))
    return False


def missing_image_talents(talents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for t in talents:
        tid = t["id"]
        fpath = Path(t["file"])
        if not fpath.exists():
            continue
        if talent_has_image(fpath, tid):
            continue
        out.append(t)
    return out


def wire_image_into_lua(file_path: Path, talent_id: str, rel_image: str) -> bool:
    """Insert `image = "..."` after the short_name/id line for the talent. Returns True if edited."""
    text = file_path.read_text(encoding="utf-8")
    if talent_has_image(file_path, talent_id):
        return False

    def repl_line(m: re.Match) -> str:
        indent = m.group(1)
        rest = m.group(2)
        return f'{indent}{rest}\n{indent}image = "{rel_image}",'

    # short_name may share the line with name= (common in this mod)
    pat_short = re.compile(
        rf'(?m)^([ \t]*)(.*\bshort_name\s*=\s*"{re.escape(talent_id)}"\s*,?\s*)$'
    )
    new_text, n = pat_short.subn(repl_line, text, count=1)
    if n == 0:
        pat_id = re.compile(
            rf'(?m)^([ \t]*)(.*\bid\s*=\s*"{re.escape(talent_id)}"\s*,?\s*)$'
        )
        new_text, n = pat_id.subn(repl_line, text, count=1)
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
    ap = argparse.ArgumentParser(description="Glutton Remade SD talent icon pipeline")
    ap.add_argument("--install-mod", action="store_true", help="Copy Output PNGs into the addon")
    ap.add_argument("--wire-images", action="store_true", help="Add image= to talent Lua for missing icons")
    ap.add_argument("--skip-generate", action="store_true", help="Do not call SD; only install/wire")
    ap.add_argument("--all-talents", action="store_true", help="Generate for every talent, not only missing image=")
    ap.add_argument("--limit", type=int, default=0, help="Max icons to generate (0=all missing)")
    ap.add_argument("--seed", type=int, default=85000)
    ap.add_argument("--ollama-prompt", action="store_true")
    ap.add_argument(
        "--keep-server",
        action="store_true",
        help="Leave SD server running after this job (default: stop to free GPU)",
    )
    args = ap.parse_args()

    print("Glutton Remade asset pipeline (SD3.5 :1338)")
    print(f"  Ollama ready: {ollama_ready()}")
    print(f"  SD ready:     {sd_ready()}")

    talents = refresh_talent_list()
    print(f"  Talents in JSON: {len(talents)}")
    targets = talents if args.all_talents else missing_image_talents(talents)
    print(f"  Targets (missing image= unless --all-talents): {len(targets)}")

    made = 0
    failed = 0
    seed = args.seed
    budget = args.limit if args.limit > 0 else 10**9

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
                name = t.get("name") or tid
                stem = icon_stem(tid)
                out = tdir / f"{stem}.png"
                theme = theme_for_talent(name, tid)
                print(f"\n=== {tid} ({name}) [{theme}] ===")
                meta = generate_tome_icon(
                    stem,
                    out,
                    kind="talent",
                    theme=theme,
                    description=f"{name}: {ART}",
                    seed=seed,
                    require_sd=True,
                    use_ollama_prompt=args.ollama_prompt,
                )
                seed += 13
                if meta.get("ok"):
                    made += 1
                    print(f"  OK -> {out.name}")
                else:
                    failed += 1
                    print(f"  FAIL: {meta.get('error')}")

            print("\n" + "=" * 60)
            print(f"Drafts written: {made}  failed: {failed}")
            print(f"Output: {OUTPUT}")

    wired = 0
    if args.wire_images:
        # Wire any target that has a PNG in Output or already in mod
        for t in targets:
            tid = t["id"]
            stem = icon_stem(tid)
            out_png = OUTPUT / "talents" / f"{stem}.png"
            mod_png = MOD / "data" / "gfx" / "talents" / f"{stem}.png"
            if not out_png.exists() and not mod_png.exists():
                continue
            fpath = Path(t["file"])
            if wire_image_into_lua(fpath, tid, image_path(tid)):
                wired += 1
                print(f"  wired image= for {tid}")
        print(f"Wired image= on {wired} talents")

    if args.install_mod:
        if not (OUTPUT / "talents").exists():
            print("Nothing in Output/talents to install.")
            return 1 if made == 0 and not args.skip_generate else 0
        n = install_pngs(OUTPUT, MOD)
        print(f"Installed {n} PNG copies into data/gfx + overload/data/gfx")
    elif not args.skip_generate:
        print("Tip: re-run with --install-mod --wire-images after review.")

    print("=" * 60)
    return 0 if (made or args.skip_generate or args.install_mod) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Interrupted")
        sys.exit(1)
