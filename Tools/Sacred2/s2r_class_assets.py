#!/usr/bin/env python3
"""Sacred 2 Remaster - assets for S2X custom classes (combat-art icons and the class portrait).

A custom class is an s2mm mod `Mods/mods/class-<id>` in the game folder, built from its `class.json` by the game's
`Mods/s2x-classes.py`. This tool makes the pictures that mod is missing and puts them where the builder picks them up:

  art icons   one medallion per new combat art, in the look of the game's own (flat glowing emblem on a coloured
              disc, gold ring), packed into one DDS sheet + the small ringless version the game uses for buffs
  portrait    the class's picture for its button on the character creation screen

Pixels come from the shared SD3.5 stage (Tools/Shared, :1338) or from PNGs you supply (`import`). The ring, the
disc mask, the sheet layout and the DDS are done here. Nothing is copied out of the game's own textures.

  python s2r_class_assets.py plan     --class druid            what would be generated, with the prompts
  python s2r_class_assets.py icons    --class druid            generate missing art icons (SD), then pack
  python s2r_class_assets.py icons    --class druid --only enemy_pestball --seed 7 --overwrite     re-roll one
  python s2r_class_assets.py portrait --class druid            generate the class portrait (SD), then pack
  python s2r_class_assets.py import   --class druid --art enemy_pestball --png my.png      use your own picture
  python s2r_class_assets.py import   --class druid --portrait --png my_bust.png
  python s2r_class_assets.py pack     --class druid            rebuild sheet, DDS and manifest from what is there
  python s2r_class_assets.py all      --class druid            icons + portrait + pack

Afterwards, in the game folder:  Mods\\S2X-Classes.bat build <id>   and deploy (Mods\\S2ModManager.bat).

class.json fields this tool reads (all optional), per art object:
  "art":       what the emblem shows, e.g. "a bear paw print"        (default: derived from "name" and "text")
  "art_color": disc colour, e.g. "sickly green"                       (default: the tab's colour)
and at the top level:
  "art_colors": ["amber orange", "sickly green", "leaf green"]        one disc colour per aspect tab
  "portrait":   "a hooded druid woman with antlers and green eyes"    subject of the class portrait
Which arts get an icon: every art object that has "name" or "art" (new arts); plain borrowed arts keep the icon
of the art they were copied from. `--all-arts` includes those too.

Output: <game>/Mods/mods/class-<id>/files/Remaster/Textures/S2X/<id>_arts.dds, <id>_class.dds and
assets/icons.json (read by s2x-classes.py build). Working files: Tools/Output/Sacred2/<id>/ (raw SD images,
finished cells, preview.png) - look at preview.png after every run.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TOOLS = Path(__file__).resolve().parent.parent
SHARED = TOOLS / "Shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from PIL import Image, ImageChops, ImageDraw, ImageFilter  # noqa: E402

DEFAULT_GAME = Path(r"D:\games\Steam\steamapps\common\Sacred 2 Remaster")

# geometry of the game's combat-art sprites (Remaster/ui/Ingame/spells.rcss): a 278 x 272 cell, disc radius 103,
# gold ring 107-114, dark rim to 119, soft shadow to 133; buffs also have a 172 x 163 ringless cell
CELL_W, CELL_H = 278, 272
SMALL_W, SMALL_H = 172, 163
SHEET_W = 1024
DISC_R, RING_IN, RING_OUT, RIM_OUT, SHADOW_OUT = 103, 107, 114, 119, 133
SMALL_R = 62
PORTRAIT_W, PORTRAIT_H = 232, 264            # hero buttons of the character screen (mainMenuHeroElements.rcss)
TAB_COLORS = ["crimson red", "azure blue", "teal green"]
ICON_NEGATIVE = ("text, letters, numbers, watermark, logo, signature, frame, border, ring, photograph, photorealistic, "
                 "3d render, blurry, low quality, cluttered, busy background, scenery, landscape, multiple objects, collage, "
                 "gradient noise, UI chrome")
PORTRAIT_NEGATIVE = ("text, letters, watermark, logo, frame, border, photograph, 3d render, blurry, low quality, full body, "
                     "multiple people, collage, extra limbs, deformed face, cropped head")


class Stop(Exception):
    pass


# ------------------------------------------------------------------------------------------------- class files

def game_dir(arg: Optional[str]) -> Path:
    g = Path(arg or os.environ.get("S2R_GAME") or DEFAULT_GAME)
    if not (g / "Mods" / "mods").is_dir():
        raise Stop(f"{g} is not a Sacred 2 Remaster folder with the mod manager (no Mods\\mods); pass --game")
    return g


def find_class(game: Path, cid: str) -> Tuple[Path, Dict[str, Any]]:
    for d in sorted((game / "Mods" / "mods").iterdir()):
        p = d / "class.json"
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                raise Stop(f"{p}: {exc}")
            if str(data.get("id")) == cid:
                return d, data
    raise Stop(f'no class "{cid}" (looked for Mods\\mods\\*\\class.json with that id)')


def work_dir(cid: str) -> Path:
    d = TOOLS / "Output" / "Sacred2" / cid
    (d / "raw").mkdir(parents=True, exist_ok=True)
    (d / "cells").mkdir(parents=True, exist_ok=True)
    return d


def art_list(data: Dict[str, Any], all_arts: bool) -> List[Dict[str, Any]]:
    """Arts that get their own icon: key (the spell it is copied from), display name, emblem subject, colour."""
    colors = list(data.get("art_colors") or TAB_COLORS)
    out = []
    for tab, col in enumerate(data.get("aspects") or []):
        for art in col:
            a = {"from": art} if isinstance(art, str) else dict(art)
            if not (a.get("name") or a.get("art") or all_arts):
                continue
            name = a.get("name") or a["from"]
            subject = a.get("art")
            if not subject:
                text = (a.get("text") or "").strip()
                subject = f"{name}: {text}" if text else name
            out.append({"from": a["from"], "name": name, "subject": subject, "tab": tab,
                        "color": a.get("art_color") or colors[min(tab, len(colors) - 1)]})
    return out


def icon_prompt(a: Dict[str, Any]) -> str:
    return (f"game ability icon, a single bold glowing emblem that symbolises {a['subject']}, "
            f"flat vector style with thick clean outlines and a soft inner glow, "
            f"centered on a plain {a['color']} background with subtle radial shading, simple, iconic, symmetrical composition")


def portrait_prompt(data: Dict[str, Any]) -> str:
    subject = data.get("portrait") or f"a {data.get('name', data.get('id'))}, fantasy hero"
    return (f"painted fantasy character portrait bust of {subject}, head and shoulders, facing slightly to the side, "
            f"dramatic rim light, dark muted plain background, detailed face, classic action RPG character art")


# ------------------------------------------------------------------------------------------------- pixels

def _sd_api() -> str:
    import sd_art  # shared SD3.5 helper; starts :1338 on demand, raises when it cannot

    return sd_art.ensure_server()


def sd_square(prompt: str, out: Path, seed: int, negative: str, w: int = 512, h: int = 512) -> Path:
    import sd_art

    img = sd_art.render(prompt, w, h, api_url=_sd_api(), kind="icon", transparent=False, seed=seed, negative=negative)
    img.save(out)
    return out


def _circle_mask(size: int, radius: float, ss: int = 4) -> Image.Image:
    m = Image.new("L", (size * ss, size * ss), 0)
    c = size * ss / 2.0
    r = radius * ss
    ImageDraw.Draw(m).ellipse((c - r, c - r, c + r, c + r), fill=255)
    return m.resize((size, size), Image.Resampling.LANCZOS)


def _ring_layer(w: int, h: int, ss: int = 4) -> Image.Image:
    """Shadow, dark rim and gold ring of a combat-art medallion, drawn (not taken from the game)."""
    W, H = w * ss, h * ss
    cx, cy = W / 2.0, H / 2.0
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shadow).ellipse((cx - RIM_OUT * ss, cy - RIM_OUT * ss, cx + RIM_OUT * ss, cy + RIM_OUT * ss), fill=120)
    shadow = shadow.filter(ImageFilter.GaussianBlur(5 * ss))
    layer.paste((0, 0, 0, 255), (0, 0), shadow)
    d = ImageDraw.Draw(layer)

    def ring(r_out: float, r_in: float, fill: Tuple[int, int, int, int]) -> None:
        d.ellipse((cx - r_out * ss, cy - r_out * ss, cx + r_out * ss, cy + r_out * ss), fill=fill)
        d.ellipse((cx - r_in * ss, cy - r_in * ss, cx + r_in * ss, cy + r_in * ss), fill=(0, 0, 0, 0))

    ring(RIM_OUT, RING_OUT, (2, 8, 18, 252))
    steps = 7                                             # gold: darker edges, bright middle
    for i in range(steps):
        t = i / (steps - 1)
        r_out = RING_OUT - (RING_OUT - RING_IN) * t * 0.5
        r_in = RING_IN + (RING_OUT - RING_IN) * t * 0.5
        if r_out <= r_in:
            break
        g = 0.55 + 0.45 * t
        d.ellipse((cx - r_out * ss, cy - r_out * ss, cx + r_out * ss, cy + r_out * ss),
                  fill=(int(255 * g), int(222 * g), int(110 * g + 20 * t), 252))
    d.ellipse((cx - RING_IN * ss, cy - RING_IN * ss, cx + RING_IN * ss, cy + RING_IN * ss), fill=(8, 12, 30, 252))
    d.ellipse((cx - DISC_R * ss, cy - DISC_R * ss, cx + DISC_R * ss, cy + DISC_R * ss), fill=(0, 0, 0, 0))
    return layer.resize((w, h), Image.Resampling.LANCZOS)


def _disc(src: Image.Image, radius: int, keep: float = 0.9) -> Image.Image:
    """Centre crop of the picture as a disc of that radius (RGBA, anti-aliased edge)."""
    src = src.convert("RGB")
    side = int(min(src.size) * keep)
    left, top = (src.width - side) // 2, (src.height - side) // 2
    art = src.crop((left, top, left + side, top + side)).resize((radius * 2, radius * 2), Image.Resampling.LANCZOS)
    out = art.convert("RGBA")
    out.putalpha(_circle_mask(radius * 2, radius))
    return out


def make_cell(src: Image.Image) -> Image.Image:
    cell = _ring_layer(CELL_W, CELL_H)
    disc = _disc(src, DISC_R)
    # a little vignette so the emblem sits in the disc like the game's
    vig = Image.new("L", disc.size, 0)
    ImageDraw.Draw(vig).ellipse((6, 6, disc.width - 6, disc.height - 6), fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(10))
    shade = Image.composite(disc, Image.blend(disc, Image.new("RGBA", disc.size, (0, 0, 20, 255)), 0.45), vig)
    shade.putalpha(disc.getchannel("A"))
    cell.alpha_composite(shade, (CELL_W // 2 - DISC_R, CELL_H // 2 - DISC_R))
    return cell


def make_small(src: Image.Image) -> Image.Image:
    cell = Image.new("RGBA", (SMALL_W, SMALL_H), (0, 0, 0, 0))
    disc = _disc(src, SMALL_R)
    glow = Image.new("RGBA", (SMALL_W, SMALL_H), (0, 0, 0, 0))
    glow.alpha_composite(disc, (SMALL_W // 2 - SMALL_R, SMALL_H // 2 - SMALL_R))
    halo = glow.filter(ImageFilter.GaussianBlur(7))
    halo.putalpha(halo.getchannel("A").point(lambda v: int(v * 0.6)))
    cell.alpha_composite(halo)
    cell.alpha_composite(disc, (SMALL_W // 2 - SMALL_R, SMALL_H // 2 - SMALL_R))
    return cell


def make_portrait(src: Image.Image) -> Image.Image:
    """Bust in a round grey-olive frame, the way the seven hero buttons look."""
    ss = 4
    w, h = PORTRAIT_W, PORTRAIT_H
    cx, cy, r = w / 2.0, h - 108.0, 100.0
    cell = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    big = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)

    def circ(rad: float, fill: Tuple[int, int, int, int]) -> None:
        d.ellipse(((cx - rad) * ss, (cy - rad) * ss, (cx + rad) * ss, (cy + rad) * ss), fill=fill)

    circ(r + 6, (150, 150, 150, 150))
    circ(r + 3, (70, 72, 62, 255))
    circ(r, (150, 152, 120, 255))
    circ(r - 4, (60, 62, 52, 255))
    circ(r - 7, (20, 22, 26, 255))
    cell.alpha_composite(big.resize((w, h), Image.Resampling.LANCZOS))
    inner = int(r - 7)
    src = src.convert("RGB")
    # SD likes to put a bust on white paper; the game's portraits sit on a dark backdrop. A bright, even border is
    # flooded from the corners with the frame's dark tone.
    corners = [src.getpixel(p) for p in ((2, 2), (src.width - 3, 2), (2, src.height - 3), (src.width - 3, src.height - 3))]
    if sum(1 for c in corners if min(c) > 215) >= 3:
        w0, h0 = src.width, src.height
        seeds = [(2, 2), (w0 - 3, 2), (2, h0 - 3), (w0 - 3, h0 - 3)]
        seeds += [(int(w0 * k / 16), y) for k in range(1, 16) for y in (2, int(h0 * 0.06), int(h0 * 0.12))]   # pockets along the top
        seeds += [(x, int(h0 * k / 8)) for k in range(1, 8) for x in (2, w0 - 3)]
        for p in seeds:
            if min(src.getpixel(p)) > 215:
                ImageDraw.floodfill(src, p, (28, 32, 30), thresh=60)
    side = min(src.size)
    left = (src.width - side) // 2
    art = src.crop((left, 0, left + side, side)).resize((inner * 2, inner * 2), Image.Resampling.LANCZOS).convert("RGBA")
    art.putalpha(_circle_mask(inner * 2, inner))
    cell.alpha_composite(art, (int(cx) - inner, int(cy) - inner))
    return cell


# ------------------------------------------------------------------------------------------------- pack

def layout(n: int) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]], int]:
    """Positions of n big cells (3 per row) and n small cells (5 per row below them), and the sheet height."""
    big = [((i % 3) * CELL_W, (i // 3) * CELL_H) for i in range(n)]
    y0 = math.ceil(n / 3) * CELL_H
    small = [((i % 5) * SMALL_W, y0 + (i // 5) * SMALL_H) for i in range(n)]
    used = y0 + math.ceil(n / 5) * SMALL_H
    height = 256
    while height < used:
        height *= 2
    return big, small, height


def to_dds(png: Path, out_dir: Path) -> Path:
    from ai_resources import compress_texture

    compress_texture([png], out_dir, "BC3_UNORM", ["-m", "1"])       # DXT5, no mip chain: what the game's sheets are
    dds = out_dir / (png.stem + ".dds")
    if not dds.is_file():
        cand = [p for p in out_dir.iterdir() if p.stem.lower() == png.stem.lower() and p.suffix.lower() == ".dds"]
        if not cand:
            raise Stop(f"texconv did not write {dds}")
        cand[0].rename(dds)
    return dds


def pack(game: Path, cid: str, all_arts: bool) -> Dict[str, Any]:
    mod, data = find_class(game, cid)
    work = work_dir(cid)
    arts = [a for a in art_list(data, True) if (work / "cells" / f"{a['from']}.png").is_file()]
    tex_dir = mod / "files" / "Remaster" / "Textures" / "S2X"
    manifest: Dict[str, Any] = {"class": cid, "arts": {}, "tool": "AAMT Tools/Sacred2/s2r_class_assets.py"}
    previews: List[Tuple[str, Image.Image]] = []
    if arts:
        big, small, height = layout(len(arts))
        sheet = Image.new("RGBA", (SHEET_W, height), (0, 0, 0, 0))
        for i, a in enumerate(arts):
            cell = Image.open(work / "cells" / f"{a['from']}.png").convert("RGBA")
            sm = Image.open(work / "cells" / f"{a['from']}_small.png").convert("RGBA")
            sheet.paste(cell, big[i])
            sheet.paste(sm, small[i])
            manifest["arts"][a["from"]] = {"rect": [big[i][0], big[i][1], CELL_W, CELL_H],
                                           "small": [small[i][0], small[i][1], SMALL_W, SMALL_H], "name": a["name"]}
            previews.append((a["name"], cell))
        png = work / f"{cid}_arts.png"
        sheet.save(png)
        tex_dir.mkdir(parents=True, exist_ok=True)
        to_dds(png, tex_dir)
        manifest["sheet"] = f"Textures/S2X/{cid}_arts.dds"
        manifest["sheet_size"] = [SHEET_W, height]
    portrait = work / "cells" / "_portrait.png"
    if portrait.is_file():
        p = Image.open(portrait).convert("RGBA")
        sheet = Image.new("RGBA", (256, 512), (0, 0, 0, 0))
        sheet.paste(p, (0, 0))
        png = work / f"{cid}_class.png"
        sheet.save(png)
        tex_dir.mkdir(parents=True, exist_ok=True)
        to_dds(png, tex_dir)
        manifest["class_icon"] = {"sheet": f"Textures/S2X/{cid}_class.dds", "rect": [0, 0, PORTRAIT_W, PORTRAIT_H]}
        previews.append(("class portrait", p))
    (mod / "assets").mkdir(exist_ok=True)
    (mod / "assets" / "icons.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    if previews:                                           # contact sheet on the game's dark panel colour
        cols = min(5, len(previews))
        rows = math.ceil(len(previews) / cols)
        sheet = Image.new("RGBA", (cols * 290, rows * 300), (24, 26, 30, 255))
        d = ImageDraw.Draw(sheet)
        for i, (name, im) in enumerate(previews):
            x, y = (i % cols) * 290, (i // cols) * 300
            sheet.alpha_composite(im, (x + (290 - im.width) // 2, y + 4))
            d.text((x + 8, y + 280), name[:40], fill=(230, 220, 180, 255))
        sheet.convert("RGB").save(work / "preview.png")
    print(f"packed {len(manifest['arts'])} art icon(s){' + class portrait' if 'class_icon' in manifest else ''} into {mod.name}")
    print(f"  preview: {work / 'preview.png'}")
    print(f"  next, in the game folder: Mods\\S2X-Classes.bat build {cid}   then deploy")
    return manifest


# ------------------------------------------------------------------------------------------------- commands

def cmd_plan(game: Path, cid: str, all_arts: bool) -> None:
    mod, data = find_class(game, cid)
    work = work_dir(cid)
    arts = art_list(data, all_arts)
    print(f'class {cid} "{data.get("name", cid)}" in {mod.name}: {len(arts)} art(s) get their own icon')
    for a in arts:
        have = "have" if (work / "cells" / f"{a['from']}.png").is_file() else "MISSING"
        print(f"  [{have:7}] {a['name']} ({a['from']}, tab {a['tab'] + 1}, {a['color']})")
        print(f"            {icon_prompt(a)}")
    print(f"  [{'have' if (work / 'cells' / '_portrait.png').is_file() else 'MISSING':7}] class portrait")
    print(f"            {portrait_prompt(data)}")


def finish_art(work: Path, key: str, src: Image.Image) -> None:
    make_cell(src).save(work / "cells" / f"{key}.png")
    make_small(src).save(work / "cells" / f"{key}_small.png")


def cmd_icons(game: Path, cid: str, only: List[str], overwrite: bool, seed: int, all_arts: bool) -> None:
    mod, data = find_class(game, cid)
    work = work_dir(cid)
    arts = [a for a in art_list(data, all_arts) if not only or a["from"] in only or a["name"] in only]
    if only and not arts:
        raise Stop("no art matches --only (use the spell name it is copied from, or its display name)")
    todo = [a for a in arts if overwrite or not (work / "cells" / f"{a['from']}.png").is_file()]
    print(f"{len(todo)} of {len(arts)} art icon(s) to generate")
    for n, a in enumerate(todo, 1):
        raw = work / "raw" / f"{a['from']}.png"
        print(f"  [{n}/{len(todo)}] {a['name']}", flush=True)
        sd_square(icon_prompt(a), raw, seed + a["tab"] * 101 + n, ICON_NEGATIVE)
        finish_art(work, a["from"], Image.open(raw))


def cmd_portrait(game: Path, cid: str, overwrite: bool, seed: int) -> None:
    mod, data = find_class(game, cid)
    work = work_dir(cid)
    if (work / "cells" / "_portrait.png").is_file() and not overwrite:
        print("class portrait exists (use --overwrite to re-roll)")
        return
    raw = work / "raw" / "_portrait.png"
    sd_square(portrait_prompt(data), raw, seed + 5, PORTRAIT_NEGATIVE)
    make_portrait(Image.open(raw)).save(work / "cells" / "_portrait.png")


def cmd_import(game: Path, cid: str, art: Optional[str], portrait: bool, png: Path) -> None:
    mod, data = find_class(game, cid)
    work = work_dir(cid)
    if not png.is_file():
        raise Stop(f"{png} does not exist")
    src = Image.open(png)
    if portrait:
        if png.resolve() != (work / "raw" / "_portrait.png").resolve():
            shutil.copy(png, work / "raw" / "_portrait.png")
        make_portrait(src).save(work / "cells" / "_portrait.png")
        return
    keys = {a["from"]: a for a in art_list(data, True)}
    match = [k for k, a in keys.items() if art in (k, a["name"])]
    if not match:
        raise Stop(f"class {cid} has no art {art}; arts: {', '.join(keys)}")
    shutil.copy(png, work / "raw" / f"{match[0]}.png")
    finish_art(work, match[0], src)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["plan", "icons", "portrait", "import", "pack", "all"])
    ap.add_argument("--class", dest="cid", required=True, help="class id (from class.json)")
    ap.add_argument("--game", help="game folder (default: S2R_GAME or the Steam install)")
    ap.add_argument("--only", default="", help="comma-separated arts to (re)generate")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--all-arts", action="store_true", help="also arts without a name or art of their own")
    ap.add_argument("--art", help="import: which art")
    ap.add_argument("--portrait", action="store_true", help="import: the class portrait")
    ap.add_argument("--png", type=Path, help="import: picture to use (square for arts, bust for the portrait)")
    args = ap.parse_args(argv)
    try:
        game = game_dir(args.game)
        only = [x.strip() for x in args.only.split(",") if x.strip()]
        if args.command == "plan":
            cmd_plan(game, args.cid, args.all_arts)
            return 0
        if args.command in ("icons", "all"):
            cmd_icons(game, args.cid, only, args.overwrite, args.seed, args.all_arts)
        if args.command in ("portrait", "all"):
            cmd_portrait(game, args.cid, args.overwrite, args.seed)
        if args.command == "import":
            if not args.png or not (args.art or args.portrait):
                raise Stop("import needs --png and --art <art> or --portrait")
            cmd_import(game, args.cid, args.art, args.portrait, args.png)
        pack(game, args.cid, args.all_arts)
    except Stop as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
