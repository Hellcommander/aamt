#!/usr/bin/env python3
"""
Smog Devil custom talent icons (magictech / steampunk), SD3.5 on :1338.

Catalog: smog_devil_talent_icons.json  ->  [{short_name, name, category, subject}, ...]
Drafts:  Tools\\Output\\SmogDevilAssets\\talents\\smog_devil\\<short_name lower>.png
Install: <mod>/{data,overload/data}/gfx/talents/smog_devil/<short_name lower>.png

  python generate_smog_devil_talent_icons.py                    # all drafts
  python generate_smog_devil_talent_icons.py --only STEAM_OVERLOAD,ORB_OF_STEAM
  python generate_smog_devil_talent_icons.py --sheet            # contact sheet for review
  python generate_smog_devil_talent_icons.py --install-mod --skip-generate
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance

TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS))

from tome_sd_client import generate_sd_image, get_sd_api_url  # noqa: E402
from tome_sd_pipeline import NEGATIVE, _coverage, _cutout_alpha  # noqa: E402

_SHARED = TOOLS.parent / "Shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
from sd_server_lifecycle import managed_sd_server  # noqa: E402

MOD = Path(r"F:\SteamLibrary\steamapps\common\TalesMajEyal\game\addons\tome-smog-devil-class")
OUTPUT = TOOLS.parent / "Output" / "SmogDevilAssets" / "talents" / "smog_devil"
CATALOG = Path(__file__).resolve().parent / "smog_devil_talent_icons.json"
# --effects: timed-effect icons (cut-out on transparent, like the shipped effects/*.png)
EFFECT_OUTPUT = TOOLS.parent / "Output" / "SmogDevilAssets" / "effects"
EFFECT_CATALOG = Path(__file__).resolve().parent / "smog_devil_effect_icons.json"
EFFECT_MODE = False

STYLE = (
    "Tales of Maj'Eyal square talent icon painting, MAGICTECH STEAMPUNK dark fantasy, "
    "brass iron copper pipes pressure gauges glowing arcane crystals, "
    "toxic teal-green steam mixed with violet mana, bold dark outlines, painterly, "
    "single centered subject filling the frame, dark smoky background, high contrast, "
    "readable at 64px, no text no logo no border"
)

# Per-tree accent so each category reads as a set in the level-up screen.
CATEGORY_ACCENT = {
    "smog-devil-veil": "shadowy hooded figure, dark grey smog, faint teal glow",
    "steamstave-training": "brass steam-staff, polished gauges",
    "steam-staff-combat": "steam-staff firing, teal steam bolt",
    "corrupted-steam": "sickly green-black corrupted steam, demonic vim red sparks",
    "corrupted-nature": "acid green ooze, corroded vines and brass",
    "smog-devil": "horned smog devil, brass and violet",
    "steam-warlock": "warlock blood-red vim mixed with steam",
    "smog-ambush": "ambush from thick smog, glinting blade, stalking shadow",
    "acid-furnace": "bubbling acid furnace, molten green, corroding metal",
    "trinity-engine": "three intertwined energies: teal steam, violet mana, crimson vim",
    "steam-arcane": "violet arcane runes in white steam",
    "mana-vim-conversion": "violet mana turning into crimson vim through brass valves",
    "boiler-thaumaturgy": "glowing arcane boiler, red-hot rivets",
    "aetheric-pipeworks": "network of glowing aether pipes, blue-violet flow",
    "lenscraft": "brass focus lens, refracted beam through haze",
    "smog-homunculi": "living smog creatures, brass vats and boiler hearts, violet arcane spark",
    "prodigy": "epic apotheosis, golden-brass radiance, overwhelming power",
}

TALENT_NEGATIVE = NEGATIVE + (
    ", text, letters, frame, border, ui, watermark, photo, cute, cartoon, "
    "white background, plain background, paper, isolated on white"
)


def accent_for(category: str) -> str:
    leaf = (category or "").split("/")[-1]
    if (category or "").startswith("uber/"):
        leaf = "prodigy"
    return CATEGORY_ACCENT.get(leaf, "brass steamtech, teal steam")


def postprocess_effect(raw: Path, out: Path, max_cov: float = 0.97) -> bool:
    rgba = _cutout_alpha(Image.open(raw).convert("RGB"))
    cov = _coverage(rgba)
    if cov < 0.06 or cov > max_cov:
        print(f"  bad coverage {cov:.0%}")
        return False
    # a solid corner means the background wasn't black (e.g. a white patch) -> retry another seed
    w, h = rgba.size
    corners = [rgba.getpixel((x, y))[3] for x, y in ((2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3))]
    if sum(a > 200 for a in corners) >= 1:
        print("  opaque corner (background not cut out)")
        return False
    rgba = rgba.resize((64, 64), Image.Resampling.LANCZOS)
    rgba = ImageEnhance.Sharpness(rgba).enhance(1.15)
    out.parent.mkdir(parents=True, exist_ok=True)
    rgba.save(out)
    return True


def postprocess_talent(raw: Path, out: Path) -> bool:
    if EFFECT_MODE:
        # map sprites must be mostly transparent or they show as a square on the tile
        return postprocess_effect(raw, out, max_cov=0.70 if out.parent.name == "npc" else 0.97)
    img = Image.open(raw).convert("RGB")
    w, h = img.size
    side = min(w, h)
    img = img.crop(((w - side) // 2, (h - side) // 2, (w + side) // 2, (h + side) // 2))
    img = img.resize((64, 64), Image.Resampling.LANCZOS)
    img = ImageEnhance.Sharpness(img).enhance(1.2)
    img = ImageEnhance.Contrast(img).enhance(1.06)
    # reject near-empty renders
    from PIL import ImageStat
    lum = ImageStat.Stat(img.convert("L")).mean[0]
    if lum < 12:
        print(f"  too dark (mean luma {lum:.1f})")
        return False
    # reject white/paper backgrounds: ToME's talent UI is dark, bright corners look like a sticker
    gray = img.convert("L")
    corner_lum = [gray.getpixel((x, y)) for x, y in ((1, 1), (62, 1), (1, 62), (62, 62))]
    if sum(c > 170 for c in corner_lum) >= 2:
        print(f"  bright background corners {corner_lum}")
        return False
    out.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGBA").save(out)
    return True


def out_path(entry: dict) -> Path:
    # --effects entries may set "subdir" (e.g. "npc") to land next to effects/ instead of in it
    if EFFECT_MODE and entry.get("subdir"):
        return OUTPUT.parent / entry["subdir"] / f"{entry['short_name'].lower()}.png"
    return OUTPUT / f"{entry['short_name'].lower()}.png"


def generate_one(entry: dict, seed: int, force: bool) -> bool:
    sid = entry["short_name"]
    out = out_path(entry)
    if out.exists() and not force:
        print(f"  skip {sid} (exists)")
        return True
    if EFFECT_MODE and entry.get("subdir") == "npc":
        prompt = (
            f"no text, fantasy RPG creature sprite, full body, {entry['subject']}, "
            "MAGICTECH STEAMPUNK dark fantasy, brass, toxic teal-green smog, violet arcane glow, bold black outlines, "
            "single centered creature, three-quarter view, isolated on a pure flat black background with nothing else, "
            "no smoke in the background, no ground, readable at 64px, no text no logo"
        )
    elif EFFECT_MODE:
        prompt = (
            f"no text, fantasy RPG status effect icon, {entry['subject']}, "
            "MAGICTECH STEAMPUNK, brass and teal steam and violet mana, bold black outlines, "
            "single centered emblem, flat matte black background, readable at 64px, no text no logo"
        )
    else:
        prompt = (
            f"no text, fantasy RPG talent icon, {entry['subject']}, "
            f"{accent_for(entry.get('category', ''))}, {STYLE}"
        )
    raw = Path(tempfile.gettempdir()) / f"smog_talent_{sid}_{seed}.png"
    raw.unlink(missing_ok=True)
    print(f"\n=== {sid} ({entry.get('name')}) seed={seed} ===")
    res = generate_sd_image(
        prompt, raw,
        negative_prompt=TALENT_NEGATIVE,
        delivery_w=64, delivery_h=64, kind="icon",
        seed=seed, guidance_scale=7.0,
        lock_label=f"smog_talent_{sid}",
    )
    if not res.ok or not res.output_path:
        print("  FAIL", res.error)
        return False
    ok = postprocess_talent(Path(res.output_path), out)
    if ok:
        meta = {"ok": True, "short_name": sid, "name": entry.get("name"),
                "category": entry.get("category"), "seed": seed, "prompt": prompt,
                "art_direction": "magictech-steampunk"}
        out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(f"  OK -> {out}")
    raw.unlink(missing_ok=True)
    return ok


def contact_sheet(entries: list[dict]) -> Path:
    cols, cell = 8, 64
    have = [e for e in entries if out_path(e).exists()]
    rows = max(1, (len(have) + cols - 1) // cols)
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 12)), (24, 24, 28))
    d = ImageDraw.Draw(sheet)
    for i, e in enumerate(have):
        x, y = (i % cols) * cell, (i // cols) * (cell + 12)
        sheet.paste(Image.open(out_path(e)).convert("RGB"), (x, y))
        d.text((x + 1, y + cell), e["short_name"][:10], fill=(200, 200, 200))
    path = OUTPUT / "_contact_sheet.png"
    sheet = sheet.resize((sheet.width * 2, sheet.height * 2), Image.Resampling.NEAREST)
    sheet.save(path)
    return path


def install_mod(entries: list[dict]) -> int:
    n = 0
    for e in entries:
        src = out_path(e)
        if not src.exists():
            continue
        for base in (MOD / "data" / "gfx", MOD / "overload" / "data" / "gfx"):
            sub = Path(e.get("subdir") or "effects") if EFFECT_MODE else Path("talents") / "smog_devil"
            dst = base / sub / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description="Smog Devil talent icons")
    ap.add_argument("--only", default="", help="comma-separated short_names")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--seed", type=int, default=91000)
    ap.add_argument("--force", action="store_true", help="regenerate existing drafts")
    ap.add_argument("--skip-generate", action="store_true")
    ap.add_argument("--install-mod", action="store_true")
    ap.add_argument("--sheet", action="store_true")
    ap.add_argument("--effects", action="store_true", help="timed-effect icons instead of talents")
    ap.add_argument("--keep-server", action="store_true", help="leave SD running afterwards")
    args = ap.parse_args()

    global OUTPUT, CATALOG, EFFECT_MODE
    if args.effects:
        EFFECT_MODE, OUTPUT, CATALOG = True, EFFECT_OUTPUT, EFFECT_CATALOG

    entries = json.loads(CATALOG.read_text(encoding="utf-8"))
    if args.only:
        want = {s.strip().upper() for s in args.only.split(",")}
        entries = [e for e in entries if e["short_name"].upper() in want]
    if args.limit:
        entries = entries[: args.limit]

    failed = []
    if not args.skip_generate:
        with managed_sd_server(keep=args.keep_server) as ready:
            if not ready or not get_sd_api_url(verbose=False):
                print("SD server not ready on :1338")
                return 1
            for e in entries:
                # stable per-talent seed so reruns reproduce the same icon
                seed = args.seed + sum(ord(c) for c in e["short_name"]) * 7
                if not generate_one(e, seed, args.force):
                    # one retry with a different seed
                    if not generate_one(e, seed + 1, True):
                        failed.append(e["short_name"])
        print(f"\nGenerated {len(entries) - len(failed)}/{len(entries)}; failed: {failed or 'none'}")

    if args.sheet or not args.skip_generate:
        print(f"Contact sheet: {contact_sheet(json.loads(CATALOG.read_text(encoding='utf-8')))}")
    if args.install_mod:
        print(f"Installed {install_mod(entries)} talent icons into mod (data/ + overload/)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
