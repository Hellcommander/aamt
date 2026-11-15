"""Extract the game's own tiles (PNG) from its Unity asset files.

Caves of Qud packs its tiles into prebuilt "Kobold" atlases; each tile is an ex2D exTextureInfo
(MonoBehaviour) naming its atlas texture and rect. The type trees are stripped, so the entries are
read by hand in exTextureInfo's field order (decompiled source):
  base MonoBehaviour (m_GameObject, m_Enabled, m_Script, m_Name), rawTextureGUID, rawAtlasGUID,
  texture (PPtr), rotated, trim, trimThreshold, trim_x, trim_y, rawWidth, rawHeight, x, y, width,
  height, border L/R/T/B, ShaderMode.
Names look like "Assets_Content_Textures_Items_sw_plate_mail.bmp"; the tile is written to
<out>/items/sw_plate_mail.png (lower case, the Render Tile path with .png), as the game's
two-tone tile (black = ColorString, white = DetailColor).

  python qud_extract_tiles.py [--out DIR] [--game DIR]      (needs UnityPy)
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

GAME = Path("D:/games/Steam/steamapps/common/Caves of Qud")
OUT = Path(__file__).resolve().parent / "_cache" / "vanilla_tiles"
PREFIX = "Assets_Content_Textures_"


class _R:
    def __init__(self, b: bytes):
        self.b, self.p = b, 0

    def i32(self) -> int:
        v = struct.unpack_from("<i", self.b, self.p)[0]
        self.p += 4
        return v

    def i64(self) -> int:
        v = struct.unpack_from("<q", self.b, self.p)[0]
        self.p += 8
        return v

    def align(self) -> None:
        self.p = (self.p + 3) & ~3

    def u8(self) -> int:
        v = self.b[self.p]
        self.p += 1
        self.align()
        return v

    def string(self) -> str:
        n = self.i32()
        if n < 0 or n > 4096:
            raise ValueError("not a string")
        v = self.b[self.p:self.p + n].decode("utf-8", "replace")
        self.p += n
        self.align()
        return v

    def pptr(self):
        return self.i32(), self.i64()


def parse_texinfo(b: bytes) -> dict:
    r = _R(b)
    r.pptr(); r.u8(); r.pptr()
    name = r.string()
    r.string(); r.string()
    tex = r.pptr()
    rotated = r.u8()
    r.u8()  # trim
    v = [r.i32() for _ in range(14)]
    return {"name": name, "tex": tex[1], "rotated": rotated, "x": v[5], "y": v[6], "w": v[7], "h": v[8]}


def tile_path(name: str) -> str:
    """'Assets_Content_Textures_Items_sw_plate_mail.bmp' -> 'items/sw_plate_mail.png'. The first
    underscore after the prefix separates the folder (game tile folders have no underscores)."""
    rest = name[len(PREFIX):]
    folder, _, file = rest.partition("_")
    stem = file.rsplit(".", 1)[0]
    return f"{folder}/{stem}.png".lower()


def extract(game: Path, out: Path) -> int:
    import UnityPy
    data = game / "CoQ_Data"
    made = 0
    for asset in ("resources.assets", "sharedassets0.assets"):
        env = UnityPy.load(str(data / asset))
        textures = {}
        entries = []
        for o in env.objects:
            if o.type.name == "Texture2D":
                textures[o.path_id] = o
            elif o.type.name == "MonoBehaviour":
                try:
                    d = parse_texinfo(o.get_raw_data())
                except Exception:
                    continue
                if d["name"].startswith(PREFIX) and 0 < d["w"] <= 256 and 0 < d["h"] <= 256:
                    entries.append(d)
        images = {}
        for d in entries:
            t = textures.get(d["tex"])
            if t is None:
                continue
            if d["tex"] not in images:
                images[d["tex"]] = t.read().image.convert("RGBA")
            atlas = images[d["tex"]]
            w, h = (d["h"], d["w"]) if d["rotated"] else (d["w"], d["h"])
            top = atlas.height - d["y"] - h  # rects are measured from the bottom
            tile = atlas.crop((d["x"], top, d["x"] + w, top + h))
            if d["rotated"]:
                tile = tile.rotate(-90, expand=True)
            dst = out / tile_path(d["name"])
            dst.parent.mkdir(parents=True, exist_ok=True)
            tile.save(dst)
            made += 1
        print(f"{asset}: {len(entries)} tiles from {len(images)} atlases")
    return made


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--game", type=Path, default=GAME)
    a = ap.parse_args()
    n = extract(a.game, a.out)
    print(f"{n} tiles -> {a.out}")
    return 0 if n else 1


if __name__ == "__main__":
    sys.exit(main())
