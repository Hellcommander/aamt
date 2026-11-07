#!/usr/bin/env python3
"""Paints a StarCrawlers Chimera character's portrait through the SD3.5 stage.

The game's CharacterPortraits plugin starts this with a job file saying who the character is:
  { "name", "level", "appearance", "output",
    "classes": [ { "name", "rank", "description" } ],   best first
    "abilities": [ "name" ],
    "gear": [ { "slot", "name", "description", "icon", "colors" } ] }   "main hand", "off hand", "stowed" (the other weapon set), or Head, Torso, ...
  optional "effects": [ { "name", "debuff" } ]   what's on the character right now
  optional "form": { "name", "description" }     the transformation they're in

The picture appears at "output" only once it is whole. A <job>.log next to the job file holds the prompt and, last, why it
failed if it did; a non-zero exit means no picture.

Usage: python make_portrait.py <job.json>   (--print-prompt shows the prompt and stops, no GPU)
"""
from __future__ import annotations

import colorsys
import json
import os
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Shared"))

# SD3.5 can run CLIP-only, which reads about 77 tokens and drops the rest: what the character is goes first, mood last.
STYLE = "waist-up painterly sci-fi portrait, arms visible"
MOOD = ("dramatic rim lighting, detailed face, looking at the viewer, dark derelict space station corridor behind, "
        "neon teal and amber glow")
NEGATIVE = ("text, letters, words, numbers, watermark, logo, signature, frame, border, user interface, multiple people, "
            "crowd, blurry, cropped head, deformed face, extra limbs, extra fingers, photo collage")
# (centre x, centre y, size) of each item on the reference board; SD's strength is how far it may stray from it.
BOARD = {"Head": (384, 175, 215), "Torso": (384, 520, 420), "Hands": (384, 690, 150), "Neck": (384, 350, 80),
         "main hand": (105, 520, 230), "off hand": (660, 520, 230)}
REFERENCE_STRENGTH = 0.6
ARMOUR = {"Head": "headgear", "Neck": "necklace", "Torso": "armour", "Belt": "belt", "Hands": "gloves", "Legs": "legwear",
          "Feet": "boots", "Accessory": "accessory"}


def plain(text: str) -> str:
    """Game text without rich-text tags, stat icons and doubled spaces."""
    text = re.sub(r"<[^>]+>|\[[A-Z]{2,4}\]", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def flavour(description: str) -> str:
    """A class's first sentence, the one that says what it is: the rest is rules."""
    first = re.split(r"(?<=[.!?])\s", plain(description))[0]
    return first[:160]


def colour_word(gear: dict) -> str:
    """The item's main colour as a word, so 'Carapace' comes out the colour it is in the game."""
    colors = gear.get("colors") or []
    if not colors:
        return ""
    r, g, b = (int(colors[0][i:i + 2], 16) / 255 for i in (1, 3, 5))
    hue, sat, val = colorsys.rgb_to_hsv(r, g, b)
    if val < 0.2:
        return "black "
    if sat < 0.18:
        return "white " if val > 0.8 else "grey "
    names = ((15, "red"), (40, "orange"), (65, "gold"), (160, "green"), (195, "teal"), (255, "blue"), (290, "purple"), (340, "pink"), (361, "red"))
    return next(word for limit, word in names if hue * 360 < limit) + " "


def gear_board(job: dict, path: Path) -> Path | None:
    """The worn items' real game icons, placed where they sit on a body, as SD's reference image: it paints over this
    layout, so shapes and colours come from the items and not from their names alone. None when no item has an icon."""
    from PIL import Image, ImageDraw

    board = Image.new("RGB", (768, 768), (34, 52, 58))  # a dim station colour: pure black stays black in the painting
    body = ImageDraw.Draw(board)  # a figure to wear it all, or SD paints floating objects
    body.polygon([(250, 330), (518, 330), (560, 768), (208, 768)], fill=(58, 60, 66))
    body.rectangle([350, 260, 418, 340], fill=(150, 125, 105))
    body.ellipse([292, 70, 476, 300], fill=(170, 142, 118))
    if any("tentacle" in (e.get("name") or "").lower() for e in job.get("effects") or []):
        for side in (-1, 1):  # tentacle arms in place of the plain figure's shoulders
            body.line([(384 + side * 130, 380), (384 + side * 230, 300), (384 + side * 300, 120)], fill=(120, 80, 130), width=44, joint="curve")
    placed = False
    for g in job.get("gear") or []:
        spot = BOARD.get(g.get("slot"))
        icon = Path(g.get("icon") or "")
        if not spot or not icon.is_file():
            continue
        x, y, size = spot
        art = Image.open(icon).convert("RGBA").resize((size, size), Image.LANCZOS)
        board.paste(art, (x - size // 2, y - size // 2), art)
        placed = True
    if not placed:
        return None
    board.save(path)
    return path


def build_prompt(job: dict) -> str:
    classes = job.get("classes") or []
    names = [c["name"] for c in classes if c.get("name")]
    who = plain(job.get("appearance") or "") or "a hardened starship crawler"
    effects = job.get("effects") or []
    # A mutation changes the body, so like a transformation it comes before what they normally look like.
    mutations = [plain(e.get("name", "")).split(":", 1)[-1].strip() for e in effects if "mutation" in e.get("name", "").lower()]
    effects = [e for e in effects if "mutation" not in e.get("name", "").lower()]
    parts = [STYLE, f"{who}, a veteran {' and '.join(names[:3])}" if names else who]
    if mutations:
        parts.append("grotesquely mutated, clearly visible " + ", ".join(mutations[:3]))
    form = job.get("form") or {}
    if form.get("name"):  # the shape they're in comes before everything they normally look like
        parts.append(f"transformed into {plain(form['name'])}, {flavour(form.get('description', ''))}".rstrip(", "))
    worn, held, stowed = [], [], []
    for g in job.get("gear") or []:
        name = plain(g.get("name", ""))
        if not name:
            continue
        slot = g.get("slot", "")
        if slot == "stowed":
            stowed.append(name)
        elif slot in ARMOUR:
            worn.append(colour_word(g) + (f"{name} {ARMOUR[slot]}" if ARMOUR[slot] not in name.lower() else name))
        else:
            held.append(colour_word(g) + name)
    if worn:
        parts.append("wearing " + ", ".join(worn[:5]))
    described = [flavour(g.get("description", "")) for g in job.get("gear") or [] if g.get("slot") in ("Head", "Torso", "main hand")]
    parts += [d for d in described if d]
    if held:
        parts.append("holding " + " and ".join(held[:2]))
    if stowed:
        parts.append(" and ".join(stowed[:2]) + " stowed across the back")
    parts += [flavour(c.get("description", "")) for c in classes[:2] if c.get("description")]
    abilities = [plain(a) for a in job.get("abilities") or [] if plain(a)]
    if abilities:
        parts.append("the aura of " + ", ".join(abilities[:4]))
    buffs = [plain(e.get("name", "")) for e in effects if not e.get("debuff")]
    debuffs = [plain(e.get("name", "")) for e in effects if e.get("debuff")]
    if buffs:
        parts.append("visibly changed by " + ", ".join(b for b in buffs[:4] if b))
    if debuffs:
        parts.append("suffering from " + ", ".join(d for d in debuffs[:2] if d))
    if (job.get("level") or 1) >= 10:
        parts.append("battle-scarred")
    parts.append(MOOD)
    return ", ".join(p.rstrip(".") for p in parts)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    path = Path(args[0])
    job = json.loads(path.read_text(encoding="utf-8"))
    prompt = build_prompt(job)
    if "--print-prompt" in sys.argv:
        print(prompt)
        return 0

    log = path.with_suffix(".log").open("w", encoding="utf-8", buffering=1)
    sys.stdout = sys.stderr = log
    print("prompt:", prompt)
    try:
        import ai_resources

        output = Path(job["output"])
        partial = path.with_suffix(".png")
        # The game shares the GPU's 11 GB and shows pictures at 384: 1024 leaves SD too little memory to finish beside it.
        board = gear_board(job, path.with_suffix(".board.png"))
        print("reference:", board)
        ai_resources.make_image(prompt, partial, negative_prompt=NEGATIVE, width=768, height=768, steps=28,
                                seed=random.randrange(1, 2**31), ensure_wait=900.0, reference_image=str(board) if board else None,
                                image_strength=REFERENCE_STRENGTH)
        os.replace(partial, output)
        print("done:", output)
        return 0
    except Exception as exc:  # noqa: BLE001  the game shows this last line to the player
        import traceback

        traceback.print_exc()
        print(f"{type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
