"""Compose a layered CYF fighter for one character, offline.

Reads a baked layer set (<out>/<id>.tile.json + Textures/Layers/<id>/<plan>.png) and a
character export (Characters/<Name>.<date>.xml, the Recur format), picks the body plan
and layers the way Arendeth_CYFTiles (CYFLayers.cs) does in game, and writes:

  --static   the composite over Textures/Creatures/<id>.png and <id>_frameNN.png, so the
             fighter's plain tile (shown when layers are off) matches the character
  --preview  an enlarged PNG strip of the frames and an animated GIF
  --portrait the first frame enlarged nearest-neighbour (--portrait-scale, default 8) as
             Textures/Portraits/<id>.png: the character-sheet portrait Arendeth_CYFTiles
             shows for this fighter (classic fighters are recoloured in their own colours)

Worn items are drawn by the mod in game from each item's own tile; this preview shows
the layers only and lists the items the game would draw.

  python cyf_compose_fighter.py <out_dir> <character.xml> [--static] [--preview DIR] [--portrait]
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image

PAIR_SLOT_WORDS = ("feet", "legs", "foot", "paws", "hoofs", "claws")
NOT_ROOT_WORDS = ("mulch", "gravel", "stakes")
ITEM_SLOTS = {"Hand": "hand", "Head": "head", "Face": "face", "Body": "body", "Back": "back",
              "Feet": "feet", "Missile Weapon": "missile", "Floating Nearby": "float"}


def norm(s: str) -> str:
    return "".join(c for c in (s or "").lower() if c.isalnum())


def classify(counts: Dict[str, int], n: str, b: str, legs: List[int]) -> None:
    """Mirror of CYFLayers.ClassifyLimb (n = variant name, b = base type, lowercase)."""
    def add(k: str) -> None:
        counts[k] = counts.get(k, 0) + 1
    if ("head" in n and "header" not in n) or ("skull" in n and "face" not in n):
        add("#head")
    if "oral arm" in n:
        return  # a wrist slot (WM Gelatinous Form); its Tentacle / Pseudopod are the limbs
    if any(w in n for w in ("tentacle", "pseudopod", "cilium")):
        add("#tentacle")
        return
    if "wing" in n:
        add("#wing")
        return
    if b == "fin":
        add("#fin")
        return
    if b == "roots":
        if not any(w in n for w in NOT_ROOT_WORDS):
            add("#roots")
        return
    if (b == "tail" and "foot" not in n) or "tail" in n:
        add("#tail")
        return
    if b == "feet":
        if n.endswith("legs"):
            legs[3] += 1
        elif any(w in n for w in PAIR_SLOT_WORDS):
            legs[1] += 1
        return
    if b == "foot":
        legs[0] += 1
        return
    if "leg" in n and not n.endswith("legs"):
        legs[2] += 1
        return
    if ("arm" in n and "stump" not in n and "forearm" not in n and "armor" not in n) or (
            ("palp" in n or "cheliped" in n) and b == "arm"):
        add("#arm")


# Recur exports name each part by its variant ("Tentacle", "Oral Arm"); the base type
# is not saved, so the common variants are mapped back here.
BASE_OF = {"tentacle": "hand", "pseudopod": "hand", "oral arm": "arm", "paws": "feet", "hooves": "feet"}


def read_character(path: Path) -> Dict:
    text = path.read_text(encoding="utf-8-sig")
    root = ET.fromstring("<r>" + text + "</r>")
    go = root.find("GameObjects/GameObject")
    body = go.find("Body")
    counts: Dict[str, int] = {}
    legs = [0, 0, 0, 0]
    worn: List[str] = []
    items: List[Tuple[str, str]] = []

    def walk(node: ET.Element) -> None:
        for part in node.findall("Part"):
            t = part.get("Type") or ""
            counts[t] = counts.get(t, 0) + 1
            base = BASE_OF.get(t.lower(), t.lower())
            classify(counts, t.lower(), base, legs)
            for it in part.findall("Item"):
                worn.append(norm(it.get("Blueprint", "")))
                items.append((ITEM_SLOTS.get(t) or ITEM_SLOTS.get(base.title()) or "-", it.get("Blueprint", "")))
            walk(part)

    for it in body.findall("Item"):
        worn.append(norm(it.get("Blueprint", "")))
        items.append(("body", it.get("Blueprint", "")))
    walk(body)
    total = max(legs[0], 2 * legs[1]) + max(legs[2], 2 * legs[3])
    if total:
        counts["#leg"] = total
    muts = [(norm((m.get("Name") or "") + " " + (m.get("Variant") or "")), int(m.get("Level") or 1))
            for m in go.findall("Mutation")]
    anatomy = go.get("Blueprint")  # export has no anatomy name; plan falls back to limbs
    return {"limbs": counts, "mutations": muts, "worn": worn, "items": items, "anatomy": anatomy,
            "name": root.find("Meta").get("Name")}


def choose_plan(plans: List[Dict], limbs: Dict[str, int], anatomy: str) -> Dict:
    for p in plans:
        if anatomy and anatomy in (p.get("anatomies") or []):
            return p
    c = limbs.get
    if c("#roots", 0):
        want = "tree"
    elif c("#leg", 0) >= 3:
        want = "quadruped"
    elif c("#arm", 0) or c("#leg", 0):
        want = "biped"
    elif c("#fin", 0):
        want = "fish"
    elif c("#head", 0) and c("#tail", 0):
        want = "serpent"
    else:
        want = "blob"
    for wid in (want, "quadruped", "biped"):
        for p in plans:
            if p["id"] == wid:
                return p
    return plans[0]


def matches(layer: Dict, ch: Dict) -> bool:
    for spec in layer.get("limbs") or []:
        k, _, n = spec.rpartition(":")
        if ch["limbs"].get(k, 0) >= int(n or 1):
            return True
    for tok in layer.get("mutations") or []:
        for blob, lvl in ch["mutations"]:
            if tok in blob and (layer.get("minLevel", 0) <= 0 or lvl >= layer["minLevel"]):
                return True
    for tok in layer.get("equipped") or []:
        if any(tok in w for w in ch["worn"]):
            return True
    return False


def blocked(layer: Dict, ch: Dict) -> bool:
    """Mirror of CYFLayers.Blocked: an "unless" token in a mutation or worn item turns the layer off."""
    for tok in layer.get("unless") or []:
        if any(tok in blob for blob, _ in ch["mutations"]) or any(tok in w for w in ch["worn"]):
            return True
    return False


def pick_layers(plan: Dict, ch: Dict, hide: List[str]) -> List[Dict]:
    on = {l["id"]: (l["id"] not in hide and not blocked(l, ch) and matches(l, ch)) for l in plan["layers"]}
    changed = True
    while changed:
        changed = False
        for l in plan["layers"]:
            if on[l["id"]] and l.get("requires") and not on.get(l["requires"]):
                on[l["id"]] = False
                changed = True
    return [l for l in plan["layers"] if on[l["id"]]]


def compose(sheet: Image.Image, plan: Dict, layers: List[Dict], frame: int, w: int, h: int) -> Image.Image:
    def cell(row: int, frames: int) -> Image.Image:
        c = frame % max(1, frames)
        return sheet.crop((c * w, row * h, c * w + w, row * h + h))

    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    fade = 1.0
    for l in layers:
        if l["z"] == "back" and "row" in l:
            out.alpha_composite(cell(l["row"], l["frames"]))
    for l in layers:
        if l["z"] == "fade":
            fade = min(fade, l.get("fade", 255) / 255.0)
    base = cell(0, plan["base"]["frames"])
    if fade < 1:
        a = base.getchannel("A").point(lambda v: int(v * fade))
        base.putalpha(a)
    out.alpha_composite(base)
    for l in layers:
        if l["z"] == "front" and "row" in l:
            out.alpha_composite(cell(l["row"], l["frames"]))
    return out


# Qud's classic palette, for recolouring classic (black = foreground, white = detail) tiles.
QUD_COLORS = {
    "k": (15, 59, 58), "K": (21, 83, 82), "r": (166, 74, 46), "R": (215, 66, 0),
    "g": (0, 148, 3), "G": (0, 196, 32), "b": (0, 72, 189), "B": (0, 150, 255),
    "c": (64, 164, 185), "C": (119, 191, 207), "m": (177, 84, 207), "M": (218, 91, 214),
    "w": (152, 135, 95), "W": (207, 192, 65), "y": (177, 201, 195), "Y": (255, 255, 255),
    "o": (241, 95, 34), "O": (233, 159, 16),
}


def classic_recolor(im: Image.Image, fg: str, detail: str) -> Image.Image:
    """Classic tiles: luminance 0 is the foreground colour, 1 the detail colour."""
    f = QUD_COLORS.get(fg, QUD_COLORS["y"])
    d = QUD_COLORS.get(detail, QUD_COLORS["W"])
    out = im.copy()
    px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            t = (r * 299 + g * 587 + b * 114) / 255000.0
            px[x, y] = tuple(int(f[i] + (d[i] - f[i]) * t) for i in range(3)) + (a,)
    return out


def write_portrait(out_dir: Path, fid: str, man: Dict, frame: Image.Image, scale: int) -> Path:
    im = frame
    if str(man.get("colorMode", "classic")).lower() != "truecolor":
        im = classic_recolor(im, str(man.get("foreground") or "y"), str(man.get("detail") or "W"))
    s = max(1, scale)
    big = im.resize((im.width * s, im.height * s), Image.Resampling.NEAREST)
    dst = out_dir / "Textures" / "Portraits"
    dst.mkdir(parents=True, exist_ok=True)
    path = dst / f"{fid}.png"
    big.save(path)
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("character", type=Path)
    ap.add_argument("--static", action="store_true")
    ap.add_argument("--preview", type=Path, default=None)
    ap.add_argument("--scale", type=int, default=8)
    ap.add_argument("--portrait", action="store_true")
    ap.add_argument("--portrait-scale", type=int, default=8)
    a = ap.parse_args()

    man_path = next(a.out_dir.glob("*.tile.json"))
    fid = man_path.name[: -len(".tile.json")]
    man = json.loads(man_path.read_text(encoding="utf-8"))
    ls = man["layerSet"]
    w, h = ls["tileSize"]
    n = int(ls.get("frameCount") or 1)
    ch = read_character(a.character)
    plan = choose_plan(ls["plans"], ch["limbs"], ch["anatomy"])
    layers = pick_layers(plan, ch, (ls.get("hideLayers") or []) + (ls.get("tileHideLayers") or []))
    sheet = Image.open(a.out_dir / "Textures" / plan["sheet"]).convert("RGBA")
    frames = [compose(sheet, plan, layers, i, w, h) for i in range(n)]

    print(f"{ch['name']}: plan {plan['id']}, limbs {dict(sorted((k, v) for k, v in ch['limbs'].items() if k.startswith('#')))}")
    print("layers:", ", ".join(l["id"] for l in layers))
    if ls.get("hideLayers"):
        print("hidden:", ", ".join(ls["hideLayers"]))
    if ls.get("tileHideLayers"):
        print("tile-hidden (portrait only):", ", ".join(ls["tileHideLayers"]))
    print("items the game draws from their own tiles:",
          ", ".join(f"{b} ({s})" for s, b in ch["items"] if s not in ("-", "hand", "missile")) or "none")
    held = [f"{b} ({s})" for s, b in ch["items"] if s in ("hand", "missile")]
    if held:
        print("held items (portrait; on the tile only with OptionArendethCYFHeldItems):", ", ".join(held))

    if a.static:
        cre = a.out_dir / "Textures" / "Creatures"
        frames[0].save(cre / f"{fid}.png")
        for i, im in enumerate(frames):
            im.save(cre / f"{fid}_frame{i:02d}.png")
        print(f"static tile + {n} frames -> {cre}")
    if a.portrait:
        print(f"portrait -> {write_portrait(a.out_dir, fid, man, frames[0], a.portrait_scale)}")
    if a.preview:
        a.preview.mkdir(parents=True, exist_ok=True)
        s = a.scale
        bg = (21, 25, 30, 255)
        strip = Image.new("RGBA", (n * (w * s + 8) + 8, h * s + 16), bg)
        gif = []
        for i, im in enumerate(frames):
            big = im.resize((w * s, h * s), Image.Resampling.NEAREST)
            strip.alpha_composite(big, (8 + i * (w * s + 8), 8))
            g = Image.new("RGBA", (w * s, h * s), bg)
            g.alpha_composite(big)
            gif.append(g.convert("P", palette=Image.Palette.ADAPTIVE))
        strip.save(a.preview / f"{fid}_composite.png")
        gif[0].save(a.preview / f"{fid}_composite.gif", save_all=True, append_images=gif[1:], duration=160, loop=0)
        print(f"preview -> {a.preview}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
