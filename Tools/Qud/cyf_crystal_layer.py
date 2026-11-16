"""Crystal Delight body layer for Character Looks (Arendeth_CYFTiles) biped sheets.

Crystal Delight rebuilds the eater as a crystalline body (wiki): 8 Smooth Faces, 4 Crystal Prism arms, 4 Quincunx
hands with Crystalline Points, 2 Hardpoints, no head, no feet, no back; the root Body slot stays, as on every plan.
Its anatomy sits on the biped plan, so the person drawn by the sheet must be covered: this layer draws a faceted
crown where the head was, four prisms over the arms ending in quincunx points, a shard base over the legs and
feet, and two floating hardpoint gems. The torso stays open so worn body armour still tints it.

8 frames: a glint runs over the facets, the hardpoints bob. Keyed on limbs "Quincunx:1" (only that body has
quincunx hands; Crystallinity from character creation keeps a human body). Drawn last (appended layer).

    python cyf_crystal_layer.py <fighter work dir> [...]   # appends the row + layer once (idempotent)
    python cyf_crystal_layer.py --mod-fighter <id>         # same for a fighter that only lives in the mod
"""
import json
import sys
from pathlib import Path
from PIL import Image

MOD = Path(r"C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Arendeth_CYFTiles")
P = {
    "L": (214, 240, 250), "M": (150, 204, 232), "D": (92, 132, 184), "V": (172, 144, 222), "W": (255, 255, 255),
}
BASE = [
    "................",
    "......L..L......",
    ".....LMDLMD.....",
    "....LMVMMVMD....",
    "....MLMDLMDM....",
    "....DMVMMVMD....",
    ".....DMLMMD.....",
    "......DMMD......",
    "...LM......ML...",
    "..LMD......DML..",
    "..MDL......LDM..",
    ".LMD........DML.",
    ".MDL........LDM.",
    ".MD..........DM.",
    ".D.LM......ML.D.",
    "...VV......VV...",
    ".....LMMMMD.....",
    ".....MDVVDD.....",
    ".....DMLLMD.....",
    ".....DMVVMD.....",
    "....DDMMMMDD....",
    "....DMMLLMMD....",
    ".....DMMMMD.....",
    "................",
]
GLINT = [(6, 1), (7, 3), (8, 4), (9, 5), (3, 9), (12, 11), (7, 17), (8, 21)]   # one bright facet per frame
BOB = [0, 0, -1, -1, 0, 0, 1, 1]
LAYER = {"id": "crystal", "z": "front", "mutations": [], "equipped": [], "effects": [], "limbs": ["Quincunx:1"],
         "minLevel": 0, "requires": None, "covers": [], "unless": [], "frames": 8}


def frame(k):
    assert all(len(r) == 16 for r in BASE) and len(BASE) == 24
    im = Image.new("RGBA", (16, 24), (0, 0, 0, 0))
    for y, row in enumerate(BASE):
        for x, ch in enumerate(row):
            if ch != ".":
                im.putpixel((x, y), P[ch] + (255,))
    gx, gy = GLINT[k]
    if im.getpixel((gx, gy))[3]:
        im.putpixel((gx, gy), P["W"] + (255,))
    for hx in (0, 15):  # the two hardpoints: gems floating beside the prisms
        y = 10 + BOB[k]
        im.putpixel((hx, y), P["V"] + (255,))
        im.putpixel((hx, y + 1), P["D"] + (255,))
    return im


def row():
    r = Image.new("RGBA", (16 * 8, 24), (0, 0, 0, 0))
    for k in range(8):
        r.paste(frame(k), (16 * k, 0))
    return r


def apply(sheet: Path, tile_json: Path):
    t = json.loads(tile_json.read_text(encoding="utf-8"))
    plan = next(p for p in t["layerSet"]["plans"] if p["id"] == "biped")
    if any(l["id"] == "crystal" for l in plan["layers"]):
        print("already has crystal:", tile_json)
        return
    im = Image.open(sheet).convert("RGBA")
    n = im.height // 24
    out = Image.new("RGBA", (max(im.width, 128), im.height + 24), (0, 0, 0, 0))
    out.paste(im, (0, 0))
    out.paste(row(), (0, n * 24))
    out.save(sheet)
    layer = dict(LAYER, row=n)
    # Before "phase" (a row-less effect) if present, so it is the last drawn image layer.
    at = next((i for i, l in enumerate(plan["layers"]) if l.get("row") is None), len(plan["layers"]))
    plan["layers"].insert(at, layer)
    tile_json.write_text(json.dumps(t, indent=2, ensure_ascii=False), encoding="utf-8")
    print("crystal row", n, "->", sheet)


def main(argv):
    if argv[:1] == ["--mod-fighter"]:
        fid = argv[1]
        apply(MOD / "Textures" / "Layers" / fid / "biped.png", next((MOD / "Fighters" / fid).glob("*.tile.json")))
        return
    for d in map(Path, argv):
        fid = next(d.glob("*.tile.json")).name.split(".")[0]
        apply(d / "Textures" / "Layers" / fid / "biped.png", d / f"{fid}.tile.json")


if __name__ == "__main__":
    main(sys.argv[1:])
