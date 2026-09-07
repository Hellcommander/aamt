#!/usr/bin/env python3
"""Bake CWL custom-effect spritesheets into Texture/ and stamp XML sound/effect IDs.

CWL loads Texture/<id>.png as PlayEffect("<id>") when the PNG is a horizontal
strip of square frames. We animate existing concept art (not UnityFS bundles).

Also injects <soundAsset>/<effectAsset> into MagicPlus XML that the loaders already read.

  python elin_deploy_real_effects.py
"""
from __future__ import annotations

import argparse
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageEnhance, ImageFilter, ImageChops

_ELIN_TOOLS = Path(__file__).resolve().parent
_CATALOG = _ELIN_TOOLS / "elin_asset_catalog.json"
_DEFAULT_MOD = Path(r"E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator")

FRAME = 64
FRAMES = 8

# PlayEffect IDs used in C# that are not vanilla (do not override ab_swarm)
CUSTOM_FX: List[Tuple[str, str]] = [
    ("ab_ether", "EtherwindMagic"),
    ("ab_etherbind", "EtherwindMagic"),
    ("ab_ethershroud", "EtherwindMagic"),
    ("ab_etheranchor", "EtherwindMagic"),
    ("ab_etherrift", "EtherwindMagic"),
    ("ab_web", "DruidicMagic"),
    ("ab_wrap", "DruidicMagic"),
    ("ab_firebreath", "DragonMagic"),
    ("ab_icebreath", "DragonMagic"),
    ("ab_poisonbreath", "Pollution"),
    ("ab_lightningbreath", "WeatherMagic"),
    ("ab_acidbreath", "Pollution"),
    ("ab_elementalstorm", "ElementMagic"),
    ("ab_necromancy", "Necromancy"),
    ("ab_summon", "SpiritMagic"),
    ("ab_conjure", "RuneMagic"),
    ("vine_grow", "DruidicMagic"),
    ("maw_eruption", "DruidicMagic"),
    ("maw_chomp", "DruidicMagic"),
    ("ward", "RuneMagic"),
    ("transmute", "ArcaneSaturation"),
]


def load_catalog() -> Dict[str, Any]:
    if _CATALOG.is_file():
        return json.loads(_CATALOG.read_text(encoding="utf-8"))
    return {}


def src_icon(mod: Path, system_id: str) -> Optional[Path]:
    for p in (
        mod / "Texture" / f"{system_id}.png",
        _ELIN_TOOLS / "Output" / "Concepts" / "Hero" / f"elin_{system_id}_concept.png",
        _ELIN_TOOLS / "Output" / "Concepts" / "Icons" / f"elin_{system_id}_icon.png",
    ):
        if p.is_file():
            return p
    return None


def hex_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def make_frame(base: Image.Image, tint: Tuple[int, int, int], i: int, n: int) -> Image.Image:
    t = i / max(1, n - 1)
    pulse = 0.72 + 0.28 * math.sin(t * math.pi)
    angle = (t - 0.5) * 18.0
    glow = 0.85 + 0.45 * math.sin(t * math.pi)

    img = base.convert("RGBA")
    w, h = img.size
    canvas = Image.new("RGBA", (FRAME, FRAME), (0, 0, 0, 0))
    # fit
    side = min(w, h)
    img = img.crop(((w - side) // 2, (h - side) // 2, (w + side) // 2, (h + side) // 2))
    size = max(8, int(FRAME * pulse))
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    img = img.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False)
    img = ImageEnhance.Brightness(img).enhance(glow)
    # tint veil
    veil = Image.new("RGBA", img.size, (*tint, 50))
    img = Image.alpha_composite(img, veil)
    # soft bloom of the tint
    bloom = Image.new("RGBA", (FRAME, FRAME), (0, 0, 0, 0))
    ring = Image.new("RGBA", (FRAME, FRAME), (0, 0, 0, 0))
    from PIL import ImageDraw
    d = ImageDraw.Draw(ring)
    r = int(FRAME * (0.22 + 0.28 * math.sin(t * math.pi)))
    cx = cy = FRAME // 2
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(*tint, 90), width=2)
    ring = ring.filter(ImageFilter.GaussianBlur(1.4))
    canvas.paste(img, ((FRAME - size) // 2, (FRAME - size) // 2), img)
    canvas = Image.alpha_composite(canvas, ring)
    # punch a little extra alpha on the subject
    canvas = canvas.filter(ImageFilter.SMOOTH)
    return canvas


def write_sheet(src: Path, dest: Path, tint: Tuple[int, int, int]) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        frames = [make_frame(im, tint, i, FRAMES) for i in range(FRAMES)]
    sheet = Image.new("RGBA", (FRAME * FRAMES, FRAME), (0, 0, 0, 0))
    for i, fr in enumerate(frames):
        sheet.paste(fr, (i * FRAME, 0), fr)
    sheet.save(dest, format="PNG", optimize=True)


def deploy_fx(mod: Path, heroes: List[Dict[str, Any]]) -> int:
    tex = mod / "Texture"
    colors = {h["id"]: hex_rgb((h.get("colors") or ["#a855f7"])[0]) for h in heroes}
    n = 0
    for h in heroes:
        hid = h["id"]
        src = src_icon(mod, hid)
        if not src:
            print(f"[fx] missing {hid}")
            continue
        write_sheet(src, tex / f"{hid}_fx.png", colors.get(hid, (168, 85, 247)))
        n += 1
        print(f"[fx] {hid}_fx.png")
    by_id = {h["id"]: h for h in heroes}
    for fx_id, sys_id in CUSTOM_FX:
        src = src_icon(mod, sys_id)
        if not src:
            continue
        tint = colors.get(sys_id, (168, 85, 247))
        write_sheet(src, tex / f"{fx_id}.png", tint)
        n += 1
        print(f"[fx] {fx_id}.png <- {sys_id}")
    return n


def pick_druid_assets(spell_id: str, name: str) -> Tuple[str, str]:
    blob = f"{spell_id} {name}".lower()
    if any(k in blob for k in ("heal", "regen", "bless", "lifebloom", "grove")):
        return "heal", "DruidicMagic_cast"
    if any(k in blob for k in ("summon", "wolf", "bear", "treant", "wild call", "kinship")):
        return "DruidicMagic_fx", "ab_summon"
    if any(k in blob for k in ("vine", "entangle", "thorn", "net", "grasp", "wrap", "lash")):
        return "ab_wrap", "vine_grow"
    if any(k in blob for k in ("poison", "rot", "wither", "blight", "venom", "toxic", "decay", "fungal")):
        return "ab_poisonbreath", "acid_hiss"
    if "rain" in blob or "wind" in blob or "sun" in blob or "weather" in blob:
        return "WeatherMagic_fx", "WeatherMagic_cast"
    return "DruidicMagic_fx", "DruidicMagic_cast"


def inject_xml_assets(path: Path) -> int:
    if not path.is_file():
        return 0
    raw = path.read_text(encoding="utf-8")
    # Keep comments; operate per DruidicSpell block
    pattern = re.compile(r"(<DruidicSpell\s+id=\"([^\"]+)\"[^>]*>)(.*?)(</DruidicSpell>)", re.S)

    def repl(m: re.Match) -> str:
        open_tag, sid, body, close = m.group(1), m.group(2), m.group(3), m.group(4)
        name_m = re.search(r"<name>(.*?)</name>", body)
        name = name_m.group(1) if name_m else sid
        fx, snd = pick_druid_assets(sid, name)
        if "<soundAsset>" not in body:
            insert = f"\n        <effectAsset>{fx}</effectAsset>\n        <soundAsset>{snd}</soundAsset>"
            if "</description>" in body:
                body = body.replace("</description>", "</description>" + insert, 1)
            else:
                body = insert + body
        return open_tag + body + close

    new, n = pattern.subn(repl, raw)
    if n:
        path.write_text(new, encoding="utf-8")
    return n


def inject_venus(path: Path) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    text = text.replace("<soundAsset>spell_arrow</soundAsset>", "<soundAsset>vine_grow</soundAsset>")
    text = text.replace("<soundAsset>spell_earthquake</soundAsset>", "<soundAsset>maw_eruption</soundAsset>")
    if "<effectAsset>" not in text:
        text = text.replace("</description>", "</description>\n        <effectAsset>maw_eruption</effectAsset>", 1)
    path.write_text(text, encoding="utf-8")


def inject_templates(data_dir: Path, heroes: List[Dict[str, Any]]) -> int:
    """Stamp soundAsset/effectAsset onto MagicPlus <Template> nodes by magicSystem id."""
    sys_by_elin = {}
    for h in heroes:
        sys_by_elin[(h.get("elinSystem") or "").lower()] = h["id"]
        sys_by_elin[h["id"].lower()] = h["id"]

    file_defaults = {
        "summon_templates.xml": ("ab_summon", "ab_summon"),
        "hybrid_templates.xml": ("Crossmagic_fx", "Crossmagic_cast"),
        "bardic_spell_templates.xml": ("BardicMagic_fx", "BardicMagic_cast"),
        "spell_templates.xml": ("DreamMagic_fx", "DreamMagic_cast"),
    }

    n = 0
    for xml in data_dir.rglob("*.xml"):
        if xml.name.startswith("druidic"):
            continue
        raw = xml.read_text(encoding="utf-8")
        if "<Template" not in raw:
            continue
        file_fx, file_snd = file_defaults.get(xml.name, (None, None))

        def repl(m: re.Match) -> str:
            open_tag, body, close = m.group(1), m.group(2), m.group(3)
            if "<soundAsset>" in body:
                return m.group(0)
            ms = re.search(r'<magicSystem[^>]*id="([^"]+)"', body)
            if not ms:
                ms = re.search(r"<MagicSystemId>([^<]+)</MagicSystemId>", body)
            elin = (ms.group(1) if ms else "").lower()
            hid = sys_by_elin.get(elin) or sys_by_elin.get(elin.replace("magic", ""))
            if hid:
                fx, snd = f"{hid}_fx", f"{hid}_cast"
            elif file_fx:
                fx, snd = file_fx, file_snd
            else:
                fx, snd = "DragonMagic_fx", "DragonMagic_cast"
            insert = (
                f"\n        <effectAsset>{fx}</effectAsset>"
                f"\n        <soundAsset>{snd}</soundAsset>"
            )
            if "</description>" in body:
                body = body.replace("</description>", "</description>" + insert, 1)
            elif "</Description>" in body:
                body = body.replace("</Description>", "</Description>" + insert, 1)
            else:
                body = insert + body
            return open_tag + body + close

        new, count = re.subn(r"(<Template\b[^>]*>)(.*?)(</Template>)", repl, raw, flags=re.S)
        if count:
            xml.write_text(new, encoding="utf-8")
            n += count
            print(f"[xml] {xml.name}: {count} templates")
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mod-path", default=str(_DEFAULT_MOD))
    ap.add_argument("--skip-xml", action="store_true")
    args = ap.parse_args()
    mod = Path(args.mod_path)
    cat = load_catalog()
    heroes = cat.get("heroes") or []
    n = deploy_fx(mod, heroes)
    if not args.skip_xml:
        data = mod / "MagicPlus" / "Data"
        d = inject_xml_assets(data / "druidic_spells.xml")
        print(f"[xml] druidic_spells.xml spells touched={d}")
        inject_venus(data / "druidic_spell_venus_maw.xml")
        t = inject_templates(data, heroes)
        print(f"[xml] templates stamped={t}")
    print(f"DONE fx_sheets={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
