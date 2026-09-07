#!/usr/bin/env python3
"""Generate per-biomod inventory tiles and wire Tile= into BroodlingSackMods.xml.

Outputs:
  Textures/Items/Biomod/<id>.png          (16x24) — CoQ Tile= path
  Assets/Resources/Textures/Items/Biomod/<id>.png  — Unity/Resources mirror
  DesignDrafts/BiomodIcons/manifest.json
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

MOD = Path(r"c:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Broodmother Mutation")
XML_PATH = MOD / "BroodlingSackMods.xml"
OUT_DIRS = [
    MOD / "Textures" / "Items" / "Biomod",
    MOD / "Assets" / "Resources" / "Textures" / "Items" / "Biomod",
]
DRAFT_DIR = MOD / "DesignDrafts" / "BiomodIcons"
W, H = 16, 24

# CoQ ColorString (XML-escaped) -> RGB accent
COLOR_MAP = {
    "&amp;C": (90, 210, 230),   # cyan
    "&amp;c": (70, 170, 190),
    "&amp;G": (90, 200, 110),   # green
    "&amp;g": (70, 160, 90),
    "&amp;Y": (220, 200, 70),   # yellow
    "&amp;y": (190, 170, 50),
    "&amp;M": (218, 91, 214),   # magenta
    "&amp;m": (180, 70, 175),
    "&amp;W": (230, 230, 230),  # white
    "&amp;w": (190, 190, 190),
    "&amp;R": (220, 70, 70),    # red
    "&amp;r": (180, 55, 55),
    "&amp;K": (90, 90, 100),    # dark gray
    "&amp;k": (60, 60, 70),
    "&amp;B": (90, 140, 240),   # blue
    "&amp;b": (70, 110, 200),
    "&amp;O": (230, 140, 50),   # orange
    "&amp;o": (200, 110, 40),
}

# Motif shapes keyed by keyword in biomod id / display name
MOTIF_KEYWORDS = [
    ("gestation", "egg"),
    ("nutrition", "drop"),
    ("storage", "box"),
    ("expansion", "box"),
    ("armor", "shield"),
    ("carapace", "shield"),
    ("plating", "shield"),
    ("streamlined", "wing"),
    ("metabolic", "drop"),
    ("corpse", "skull"),
    ("regenerat", "cross"),
    ("quality", "gem"),
    ("stat", "bar"),
    ("combat", "blade"),
    ("night", "eye"),
    ("vision", "eye"),
    ("optical", "eye"),
    ("spawn", "egg"),
    ("birth", "egg"),
    ("resistance", "shield"),
    ("toxin", "drop"),
    ("venom", "drop"),
    ("poison", "drop"),
    ("acid", "drop"),
    ("thermal", "flame"),
    ("heat", "flame"),
    ("cold", "flake"),
    ("electric", "bolt"),
    ("psychic", "mind"),
    ("neural", "mind"),
    ("hive", "hex"),
    ("swarm", "hex"),
    ("pheromone", "wave"),
    ("sonic", "wave"),
    ("gravity", "orb"),
    ("phase", "orb"),
    ("void", "orb"),
    ("time", "clock"),
    ("chrono", "clock"),
    ("temporal", "clock"),
    ("crystal", "gem"),
    ("magnetic", "ring"),
    ("claw", "blade"),
    ("mandible", "blade"),
    ("blood", "drop"),
    ("nest", "hex"),
    ("molt", "shell"),
    ("camouflage", "wave"),
    ("parasite", "tendril"),
    ("tendril", "tendril"),
    ("spore", "cloud"),
    ("fungi", "cloud"),
    ("bomb", "burst"),
    ("explosive", "burst"),
    ("resurrection", "cross"),
    ("soul", "mind"),
    ("memory", "mind"),
    ("dream", "mind"),
    ("rider", "wing"),
    ("jump", "wing"),
    ("mobility", "wing"),
    ("reflex", "bolt"),
    ("speed", "bolt"),
    ("sense", "eye"),
    ("scent", "wave"),
    ("echo", "wave"),
]


def decode_color(cs: str | None) -> tuple[int, int, int]:
    if not cs:
        return (218, 91, 214)
    # ElementTree unescapes &amp; -> &; XML source may still use &amp;
    if cs in COLOR_MAP:
        return COLOR_MAP[cs]
    amp = cs.replace("&", "&amp;") if cs.startswith("&") and not cs.startswith("&amp;") else cs
    if amp in COLOR_MAP:
        return COLOR_MAP[amp]
    raw = cs.replace("&amp;", "&")
    if len(raw) >= 2 and raw[0] == "&":
        key = "&amp;" + raw[1]
        if key in COLOR_MAP:
            return COLOR_MAP[key]
    return (218, 91, 214)


def motif_for(mod_id: str, display: str) -> str:
    blob = (mod_id + " " + display).lower().replace("_", " ")
    for key, motif in MOTIF_KEYWORDS:
        if key in blob:
            return motif
    # stable fallback from hash
    h = int(hashlib.md5(mod_id.encode()).hexdigest()[:8], 16)
    motifs = ["gem", "hex", "drop", "blade", "eye", "orb", "bolt", "cross", "ring", "shell"]
    return motifs[h % len(motifs)]


def shade(rgb: tuple[int, int, int], factor: float) -> tuple[int, int, int, int]:
    r, g, b = rgb
    return (
        max(0, min(255, int(r * factor))),
        max(0, min(255, int(g * factor))),
        max(0, min(255, int(b * factor))),
        255,
    )


def draw_motif(draw: ImageDraw.ImageDraw, motif: str, accent: tuple[int, int, int], seed: int) -> None:
    a = shade(accent, 1.15)
    a_dim = shade(accent, 0.55)
    cx, cy = W // 2, H // 2 - 1

    if motif == "egg":
        draw.ellipse((cx - 3, cy - 5, cx + 3, cy + 4), fill=a_dim, outline=a)
        draw.point((cx, cy - 2), fill=shade(accent, 1.4))
    elif motif == "drop":
        draw.polygon([(cx, cy - 5), (cx + 3, cy), (cx, cy + 4), (cx - 3, cy)], fill=a)
        draw.point((cx - 1, cy - 1), fill=(255, 255, 255, 200))
    elif motif == "box":
        draw.rectangle((cx - 4, cy - 3, cx + 4, cy + 3), outline=a, fill=a_dim)
        draw.line((cx - 4, cy, cx + 4, cy), fill=a)
    elif motif == "shield":
        draw.polygon(
            [(cx, cy - 5), (cx + 4, cy - 2), (cx + 3, cy + 3), (cx, cy + 5), (cx - 3, cy + 3), (cx - 4, cy - 2)],
            fill=a_dim,
            outline=a,
        )
    elif motif == "wing":
        draw.polygon([(cx, cy), (cx - 5, cy - 4), (cx - 5, cy + 2)], fill=a)
        draw.polygon([(cx, cy), (cx + 5, cy - 4), (cx + 5, cy + 2)], fill=a_dim)
    elif motif == "skull":
        draw.ellipse((cx - 3, cy - 4, cx + 3, cy + 1), fill=a)
        draw.rectangle((cx - 2, cy + 1, cx + 2, cy + 3), fill=a_dim)
        draw.point((cx - 1, cy - 1), fill=(20, 20, 25, 255))
        draw.point((cx + 1, cy - 1), fill=(20, 20, 25, 255))
    elif motif == "cross":
        draw.rectangle((cx - 1, cy - 5, cx + 1, cy + 5), fill=a)
        draw.rectangle((cx - 4, cy - 1, cx + 4, cy + 1), fill=a)
    elif motif == "gem":
        draw.polygon([(cx, cy - 5), (cx + 4, cy), (cx, cy + 5), (cx - 4, cy)], fill=a, outline=shade(accent, 0.4))
        draw.point((cx - 1, cy - 1), fill=(255, 255, 255, 220))
    elif motif == "bar":
        for i, f in enumerate((0.5, 0.8, 1.1)):
            y = cy - 4 + i * 3
            draw.rectangle((cx - 4, y, cx - 4 + 3 + i * 2, y + 1), fill=shade(accent, f))
    elif motif == "blade":
        draw.polygon([(cx, cy - 6), (cx + 2, cy + 2), (cx, cy + 5), (cx - 2, cy + 2)], fill=a)
        draw.rectangle((cx - 1, cy + 4, cx + 1, cy + 6), fill=a_dim)
    elif motif == "eye":
        draw.ellipse((cx - 4, cy - 2, cx + 4, cy + 2), fill=a_dim, outline=a)
        draw.ellipse((cx - 1, cy - 1, cx + 1, cy + 1), fill=(20, 20, 30, 255))
        draw.point((cx, cy), fill=a)
    elif motif == "flame":
        draw.polygon([(cx, cy - 6), (cx + 3, cy), (cx + 1, cy + 4), (cx - 1, cy + 4), (cx - 3, cy)], fill=a)
        draw.point((cx, cy - 1), fill=(255, 240, 160, 255))
    elif motif == "flake":
        for ang in range(0, 360, 60):
            rad = math.radians(ang)
            x2 = cx + int(4 * math.cos(rad))
            y2 = cy + int(4 * math.sin(rad))
            draw.line((cx, cy, x2, y2), fill=a)
        draw.point((cx, cy), fill=(255, 255, 255, 255))
    elif motif == "bolt":
        draw.polygon([(cx + 1, cy - 6), (cx - 2, cy), (cx + 1, cy), (cx - 1, cy + 6), (cx + 3, cy), (cx, cy)], fill=a)
    elif motif == "mind":
        draw.ellipse((cx - 4, cy - 4, cx + 4, cy + 3), fill=a_dim, outline=a)
        draw.arc((cx - 3, cy - 2, cx + 3, cy + 2), 200, 340, fill=a)
    elif motif == "hex":
        pts = []
        for i in range(6):
            rad = math.radians(60 * i - 30)
            pts.append((cx + int(4 * math.cos(rad)), cy + int(4 * math.sin(rad))))
        draw.polygon(pts, fill=a_dim, outline=a)
    elif motif == "wave":
        for x in range(cx - 5, cx + 6):
            y = cy + int(2 * math.sin((x + seed % 7) * 0.9))
            draw.point((x, y), fill=a)
            draw.point((x, y + 2), fill=a_dim)
    elif motif == "orb":
        draw.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=a_dim, outline=a)
        draw.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), outline=shade(accent, 1.3))
    elif motif == "clock":
        draw.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), outline=a, fill=a_dim)
        draw.line((cx, cy, cx, cy - 3), fill=a)
        draw.line((cx, cy, cx + 2, cy + 1), fill=a)
    elif motif == "ring":
        draw.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), outline=a)
        draw.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), outline=a_dim)
    elif motif == "shell":
        draw.arc((cx - 5, cy - 3, cx + 5, cy + 5), 200, 340, fill=a)
        draw.arc((cx - 3, cy - 1, cx + 3, cy + 4), 200, 340, fill=a_dim)
    elif motif == "tendril":
        draw.line((cx, cy - 5, cx - 2, cy), fill=a)
        draw.line((cx - 2, cy, cx + 2, cy + 2), fill=a)
        draw.line((cx + 2, cy + 2, cx - 1, cy + 5), fill=a_dim)
    elif motif == "cloud":
        draw.ellipse((cx - 4, cy - 1, cx, cy + 3), fill=a_dim)
        draw.ellipse((cx - 1, cy - 3, cx + 4, cy + 2), fill=a)
        draw.ellipse((cx - 2, cy, cx + 3, cy + 4), fill=a_dim)
    elif motif == "burst":
        for i in range(8):
            rad = math.radians(i * 45 + (seed % 20))
            x2 = cx + int(5 * math.cos(rad))
            y2 = cy + int(5 * math.sin(rad))
            draw.line((cx, cy, x2, y2), fill=a if i % 2 == 0 else a_dim)
        draw.point((cx, cy), fill=(255, 220, 120, 255))
    else:
        draw.rectangle((cx - 3, cy - 3, cx + 3, cy + 3), outline=a, fill=a_dim)


def make_icon(mod_id: str, display: str, color_string: str) -> Image.Image:
    seed = int(hashlib.md5(mod_id.encode()).hexdigest()[:8], 16)
    accent = decode_color(color_string)
    motif = motif_for(mod_id, display)

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Body: living biometal hex-chip silhouette (matches ui_biomod_chip vibe)
    body = shade((15, 45, 42), 1.0)
    rim = shade(accent, 0.85)
    vein = shade(accent, 0.45)

    # Hex-ish chip frame
    pts = [
        (2, 4), (W - 3, 4), (W - 2, 8), (W - 2, H - 6),
        (W - 4, H - 3), (3, H - 3), (1, H - 6), (1, 8),
    ]
    draw.polygon(pts, fill=body, outline=rim)

    # Inner plate
    draw.rectangle((3, 6, W - 4, H - 5), fill=shade((12, 35, 34), 1.0), outline=vein)

    # Circuit veins (deterministic noise)
    rng = seed
    for i in range(10):
        rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
        x = 3 + (rng % (W - 6))
        rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
        y = 7 + (rng % (H - 12))
        draw.point((x, y), fill=shade(accent, 0.7 + (i % 3) * 0.15))

    # Magenta membrane vein across mid
    draw.line((3, H // 2, W - 4, H // 2 + ((seed % 3) - 1)), fill=shade((218, 91, 214), 0.7))

    draw_motif(draw, motif, accent, seed)

    # Soft edge glow
    glow = img.filter(ImageFilter.MaxFilter(3))
    glow = Image.blend(img, glow, 0.25)
    return glow


def parse_biomods(xml_text: str) -> list[dict]:
    # Strip encoding declaration issues; parse with ElementTree
    # Handle &amp; in attributes by keeping as-is in XML
    root = ET.fromstring(xml_text)
    out = []
    for obj in root.findall("object"):
        name = obj.get("Name") or ""
        if not name.startswith("ModBroodSack_"):
            continue
        render = None
        for part in obj.findall("part"):
            if part.get("Name") == "Render":
                render = part
                break
        if render is None:
            continue
        out.append(
            {
                "id": name,
                "short": name.replace("ModBroodSack_", ""),
                "display": render.get("DisplayName") or name,
                "color": render.get("ColorString") or "&amp;m",
                "render": render,
                "obj": obj,
            }
        )
    return out


def wire_tiles(xml_text: str, biomods: list[dict]) -> str:
    """Inject Tile= into each Render part via regex for stable formatting."""
    result = xml_text
    for b in biomods:
        tile = f"Items/Biomod/{b['short']}.png"
        # Match this object's Render part opening tag
        pattern = (
            rf'(<object Name="{re.escape(b["id"])}"[^>]*>\s*'
            rf'<part Name="Render"[^>]*?)(/?>)'
        )

        def repl(m: re.Match) -> str:
            tag = m.group(1)
            close = m.group(2)
            if re.search(r'\bTile="', tag):
                tag = re.sub(r'Tile="[^"]*"', f'Tile="{tile}"', tag)
            else:
                # Insert Tile before closing
                tag = tag.rstrip() + f' Tile="{tile}"'
            # Also ensure RenderString for inventory fallback
            if "RenderString=" not in tag:
                tag += ' RenderString="*"'
            return tag + close

        new_result, n = re.subn(pattern, repl, result, count=1, flags=re.DOTALL)
        if n == 0:
            # Fallback: looser match on DisplayName line alone within object
            print(f"WARN: could not wire Tile for {b['id']}")
        else:
            result = new_result
    return result


def main() -> None:
    xml_text = XML_PATH.read_text(encoding="utf-8")
    biomods = parse_biomods(xml_text)
    print(f"Found {len(biomods)} biomods")

    for d in OUT_DIRS:
        d.mkdir(parents=True, exist_ok=True)
    DRAFT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = []
    for b in biomods:
        img = make_icon(b["id"], b["display"], b["color"])
        fname = f"{b['short']}.png"
        for d in OUT_DIRS:
            img.save(d / fname)
        manifest.append(
            {
                "id": b["id"],
                "file": fname,
                "tile": f"Items/Biomod/{fname}",
                "display": b["display"],
                "color": b["color"],
                "motif": motif_for(b["id"], b["display"]),
            }
        )

    # Also write a shared base chip for BaseBiomod if useful
    base = make_icon("ModBroodSack_Base", "biomod chip", "&amp;m")
    for d in OUT_DIRS:
        base.save(d / "_base_chip.png")

    # Wire BaseBiomod render if present
    if 'Name="BaseBiomod"' in xml_text and "Tile=" not in xml_text.split('Name="BaseBiomod"', 1)[1][:400]:
        xml_text = xml_text.replace(
            '<object Name="BaseBiomod" Inherits="Item">',
            '<object Name="BaseBiomod" Inherits="Item">',
            1,
        )

    # Ensure BaseBiomod has a default tile via a synthetic Render if none — skip; kids override.

    wired = wire_tiles(xml_text, biomods)
    XML_PATH.write_text(wired, encoding="utf-8")

    (DRAFT_DIR / "manifest.json").write_text(
        json.dumps({"count": len(manifest), "size": [W, H], "icons": manifest}, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(manifest)} icons to Textures/Items/Biomod and Assets mirror")
    print(f"Updated {XML_PATH.name} with Tile= paths")
    print(f"Manifest: {DRAFT_DIR / 'manifest.json'}")


if __name__ == "__main__":
    main()
