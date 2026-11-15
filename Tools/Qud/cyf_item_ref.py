"""Reference icons for detailed item art: how an item looks in game, drawn big.

Bright Qud (the local mod) ships two-tone role masks for item tiles (items_<tile>.png) and paperdoll
garment layers (brightquddoll_<slot>_<shape>.png), and a table (DollTable.cs) giving each blueprint its
doll shape and material. This draws, side by side on one picture:
  - the inventory icon, recoloured like Bright Qud does in game;
  - the worn look: the doll's linen body with the garment layer on top.
Colours: the DollTable material's colours, else the item's own ColorString/TileColor + DetailColor
(brightened like Bright Qud). refart's edit puts the picture beside the character so Kontext copies the
item's colours and shape instead of guessing them from the name.

  python cyf_item_ref.py "Fullerite Plate Mail" out.png [--slot body]
"""
from __future__ import annotations

import argparse
import colorsys
import re
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

from PIL import Image

MODS = Path.home() / "AppData/LocalLow/Freehold Games/CavesOfQud/Mods"
BQ = MODS / "BrightQud"
MASKS = BQ / "Textures" / "BrightQudMask"

# The game's palette (QudColor.ColorMap) and Bright Qud's brighter versions of it.
PALETTE = {
    "r": "a64a2e", "R": "d74200", "o": "f15f22", "O": "e99f10", "w": "98875f", "W": "cfc041",
    "g": "009403", "G": "00c420", "b": "0048bd", "B": "0096ff", "c": "40a4b9", "C": "77bfcf",
    "m": "b154cf", "M": "da5bd6", "k": "0f3b3a", "K": "155352", "y": "b1c9c3", "Y": "ffffff",
}
BRIGHT = {
    "a64a2e": "c8503a", "d74200": "f05a28", "f15f22": "ff7030", "e99f10": "ffb020", "98875f": "b08a5a",
    "cfc041": "ffd23a", "009403": "3fae3a", "00c420": "6fe04a", "0048bd": "2a62d6", "0096ff": "3fb4ff",
    "40a4b9": "4fc8d8", "77bfcf": "8fe4f0", "b154cf": "c04ad8", "da5bd6": "ff7ae8", "0f3b3a": "1a4a48",
    "155352": "2e6a68", "b1c9c3": "d0dcd8", "ffffff": "f8f8f0",
}
INK = (12, 14, 18)


def _rgb(h: str) -> Tuple[int, int, int]:
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


_table: Optional[Tuple[Dict[str, list], Dict[str, list]]] = None


def doll_table() -> Tuple[Dict[str, list], Dict[str, list]]:
    """(gear: blueprint -> [layer key, material, twohanded], materials: name -> [main, detail])."""
    global _table
    if _table is None:
        gear, mats = {}, {}
        try:
            src = (BQ / "DollTable.cs").read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(r'\{ "([^"]+)", new\[\] \{ "([^"]*)", "([^"]*)", "([^"]*)" \} \}', src):
                gear[m.group(1)] = [m.group(2), m.group(3), m.group(4)]
            for m in re.finditer(r'\{ "([^"]+)", new\[\] \{ "([0-9a-fA-F]{6})", "([0-9a-fA-F]{6})" \} \}', src):
                mats[m.group(1)] = [m.group(2).lower(), m.group(3).lower()]
        except OSError:
            pass
        _table = (gear, mats)
    return _table


def _ramp(c: Tuple[int, int, int], shade: int) -> Tuple[int, int, int]:
    h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in c))
    if shade == 0:
        s *= 0.85
        v = min(1.0, v * 1.2 + 0.06)
    elif shade == 2:
        s = min(1.0, s * 1.1)
        v *= 0.62
    return tuple(int(round(x * 255)) for x in colorsys.hsv_to_rgb(h, s, v))


def recolor(mask_file: Path, fg, det) -> Optional[Image.Image]:
    """A role mask (R < 150: main colour, else detail; G / 127: shade 0 light, 1 mid, 2 dark) -> RGBA."""
    if not mask_file.is_file():
        return None
    m = Image.open(mask_file).convert("RGBA")
    out = Image.new("RGBA", m.size, (0, 0, 0, 0))
    mp, op = m.load(), out.load()
    for y in range(m.height):
        for x in range(m.width):
            r, g, _b, a = mp[x, y]
            if a > 127:
                op[x, y] = (*_ramp(fg if r < 150 else det, round(g / 127)), 255)
    return out


WORKSHOP = Path("D:/games/Steam/steamapps/workshop/content/333640")
VANILLA = Path(__file__).resolve().parent / "_cache" / "vanilla_tiles"  # qud_extract_tiles.py
_tile_index: Optional[Dict[str, Path]] = None


def mod_tile(tile: str) -> Optional[Path]:
    """A mod's own tile PNG for a Render Tile path ("Items/foo.png"), from local and workshop mods."""
    global _tile_index
    if _tile_index is None:
        _tile_index = {}
        for root in (MODS, WORKSHOP):
            if not root.is_dir():
                continue
            for tex in root.glob("*/Textures"):
                for f in tex.rglob("*.png"):
                    rel = f.relative_to(tex).as_posix().lower()
                    _tile_index.setdefault(rel, f)
    t = re.sub(r"\.bmp$", ".png", tile.replace("\\", "/").lower())
    if t in _tile_index:
        return _tile_index[t]
    v = VANILLA / t  # the game's own tile, extracted from its asset files
    return v if v.is_file() else None


def vanilla_tile(path: Path, fg, det) -> Optional[Image.Image]:
    """A plain game-format tile coloured like the game's dual-colour shader: rgb = mix(fg, detail, tex.r)."""
    try:
        m = Image.open(path).convert("RGBA")
    except OSError:
        return None
    if m.size != (16, 24):
        return None
    out = Image.new("RGBA", m.size, (0, 0, 0, 0))
    mp, op = m.load(), out.load()
    for y in range(m.height):
        for x in range(m.width):
            r, _g, _b, a = mp[x, y]
            if a > 127:
                t = r / 255
                op[x, y] = (*(int(fg[i] * (1 - t) + det[i] * t) for i in range(3)), 255)
    return out


def outline(im: Image.Image) -> Image.Image:
    """One ink pixel around the shape, like every Bright Qud sprite."""
    w, h = im.size
    out = Image.new("RGBA", (w + 2, h + 2), (0, 0, 0, 0))
    src = im.load()
    op = out.load()
    for y in range(h):
        for x in range(w):
            if src[x, y][3] > 0:
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        op[x + 1 + dx, y + 1 + dy] = (*INK, 255)
    out.alpha_composite(im, (1, 1))
    return out


def item_colors(info: Dict, material: str = "") -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    _gear, mats = doll_table()
    if material and material in mats:
        return _rgb(mats[material][0]), _rgb(mats[material][1])
    r = info.get("parts", {}).get("Render", {})
    cs = r.get("TileColor") or r.get("ColorString") or "&y"
    amp = cs.rfind("&")
    fgc = cs[amp + 1] if 0 <= amp < len(cs) - 1 else "y"
    detc = (r.get("DetailColor") or "K")[:1]
    fg, det = PALETTE.get(fgc, "b1c9c3"), PALETTE.get(detc, "155352")
    return _rgb(BRIGHT.get(fg, fg)), _rgb(BRIGHT.get(det, det))


# Doll shapes for items Bright Qud's table does not list: by slot, then words in the name.
GUESS = {
    "body": [("chain", "body/chain"), ("ring", "body/chain"), ("mail", "body/plate"), ("plate", "body/plate"),
             ("hauberk", "body/chain"), ("lune", "body/plate"), ("carapace", "body/plate"), ("lamellar", "body/plate"),
             ("fur", "body/fur"), ("leather", "body/leather"), ("vest", "body/leather"), ("jerkin", "body/leather"),
             ("robe", "body/robe"), ("toga", "body/robe"), ("tunic", "body/tunic"), ("", "body/tunic")],
    "head": [("coif", "head/coif"), ("hood", "head/crimson_hood"), ("hat", "head/hat"), ("cap", "head/cap"),
             ("crown", "head/crown"), ("veil", "head/veil"), ("", "head/helmet")],
    "face": [("goggle", "face/goggles"), ("visor", "face/goggles"), ("shades", "face/mirrorshades"),
             ("veil", "face/issachari_sun_veil"), ("", "face/mask")],
    "back": [("banner", "back/banner"), ("pack", "back/pack"), ("", "back/cloak")],
    "hands": [("gauntlet", "hands/gauntlets"), ("", "hands/gloves")],
    "feet": [("sandal", "feet/sandals"), ("", "feet/boots")],
}


def doll_key(blueprint: str, name: str, slot: str) -> Optional[str]:
    gear, _ = doll_table()
    g = gear.get(blueprint)
    if g and not g[0].startswith(("right/", "left/", "two/")):
        return g[0]
    words = (blueprint + " " + name).lower()
    for w, key in GUESS.get(slot, []):
        if w in words:
            return key
    return None


def reference(bp, blueprint: str, slot: str, out: Path, scale: int = 12) -> Optional[Path]:
    """Write the reference picture (icon + worn look) for one item; None when there is nothing to show."""
    info = bp.resolve(blueprint)
    if not info.get("found"):
        return None
    gear, mats = doll_table()
    material = (gear.get(blueprint) or ["", "", ""])[1]
    fg, det = item_colors(info, material)
    name = info["parts"].get("Render", {}).get("DisplayName", blueprint)
    panels = []
    tile = (info["parts"].get("Render", {}).get("Tile") or "").replace("\\", "/")
    if tile:
        key = re.sub(r"\.(bmp|png)$", "", tile, flags=re.I).replace("/", "_").lower()
        # The item's own tile (mod art, else the game's), then Bright Qud's redraw of it when there is one.
        own = mod_tile(tile)
        icon = vanilla_tile(own, fg, det) if own is not None else None
        if icon is not None:
            panels.append(outline(icon))
        bq = recolor(MASKS / f"{key}.png", fg, det)
        if bq is not None:
            panels.append(outline(bq))
    dk = doll_key(blueprint, name, slot)
    if dk:
        layer = recolor(MASKS / f"brightquddoll_{dk.replace('/', '_')}.png", fg, det)
        if layer is not None:
            linen = mats.get("linen", ["d8c8a0", "9a8a68"])
            body = recolor(MASKS / "brightquddoll_body_base.png", _rgb(linen[0]), _rgb(linen[1]))
            doll = body if body is not None else Image.new("RGBA", layer.size, (0, 0, 0, 0))
            doll.alpha_composite(layer)
            panels.append(outline(doll))
    if not panels:
        return None
    gap = 3
    w = sum(p.width for p in panels) + gap * (len(panels) - 1)
    h = max(p.height for p in panels)
    sheet = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    x = 0
    for p in panels:
        sheet.alpha_composite(p, (x, (h - p.height) // 2))
        x += p.width + gap
    sheet = sheet.resize((w * scale, h * scale), Image.NEAREST)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out


def describe_colors(bp, blueprint: str) -> str:
    """Words for the item's colours, for the prompt ("dark slate with lavender trim")."""
    info = bp.resolve(blueprint)
    gear, _ = doll_table()
    material = (gear.get(blueprint) or ["", "", ""])[1]
    fg, det = item_colors(info, material)
    return f"main colour {_name(fg)}, trim colour {_name(det)}" + (f", made of {material}" if material else "")


def _name(c: Tuple[int, int, int]) -> str:
    h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in c))
    if s < 0.18:
        return "white" if v > 0.85 else "light grey" if v > 0.6 else "grey" if v > 0.35 else "near-black"
    hue = h * 360
    names = [(15, "red"), (40, "orange"), (65, "yellow"), (160, "green"), (195, "teal"), (250, "blue"),
             (290, "purple"), (335, "magenta"), (361, "red")]
    base = next(n for lim, n in names if hue < lim)
    if hue < 40 and v < 0.7 and s > 0.3:
        base = "brown"
    return ("dark " if v < 0.45 else "pale " if v > 0.85 and s < 0.45 else "") + base


def main() -> int:
    sys.path.insert(0, str(Path(__file__).parent))
    from cyf_portrait_items import Blueprints, DEFAULT_GAME, DEFAULT_USERDATA, DEFAULT_WORKSHOP  # type: ignore
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("blueprint")
    ap.add_argument("out", type=Path)
    ap.add_argument("--slot", default="body")
    a = ap.parse_args()
    bp = Blueprints(DEFAULT_GAME, DEFAULT_USERDATA, DEFAULT_WORKSHOP)
    r = reference(bp, a.blueprint, a.slot, a.out)
    print(r or "no reference", "|", describe_colors(bp, a.blueprint))
    return 0 if r else 1


if __name__ == "__main__":
    sys.exit(main())
