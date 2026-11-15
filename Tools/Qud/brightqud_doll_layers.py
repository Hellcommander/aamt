"""Extra Bright Qud paper-doll layers for Arendeth_BrightQudCompat (DollExtras.cs).

Bright Qud draws the player as a 16x24 paper doll stacked from layers named brightquddoll/<group>/<name>
(Textures/brightquddoll_<group>_<name>.png) plus a mask in Textures/BrightQudMask/ of the same name. A mask
pixel with red < 150 takes the character's colour, red >= 150 the detail colour, green = shade; an empty mask
keeps the layer's own colours. These layers keep their own colours, so their masks are empty.

Body of the doll (Bright Qud's body_base): head rows 3-7, neck row 8, torso + sleeves rows 9-14 at cols 4-11
(the character's right arm is the viewer's left, col 4), hands row 15 (col 4 right, col 11 left), hips row 16,
legs rows 16-22. Layer names must not contain '_' (the game turns it into '/').

    python brightqud_doll_layers.py            # writes into Mods/Arendeth_BrightQudCompat/Textures
"""
from pathlib import Path
from PIL import Image

OUT = Path(r"C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Arendeth_BrightQudCompat\Textures")

P = {
    "C": (156, 108, 74), "c": (108, 70, 46),          # tail
    "R": (186, 138, 98), "K": (38, 24, 18),           # seed-cannon rim, bore
    "P": (218, 132, 146), "p": (160, 84, 100),        # conjoinment rope
    "B": (232, 222, 198), "b": (180, 166, 140),       # ribcage bone
    "r": (150, 44, 40),                               # gill slits
    "W": (240, 228, 170), "w": (198, 182, 118),       # waxflab
    "G": (172, 236, 246), "g": (96, 188, 210),        # glowcrust
    "M": (222, 44, 92), "m": (128, 22, 52),           # mumble mouths
    "F": (112, 200, 72), "f": (68, 138, 40), "Y": (236, 220, 96),  # fickle gill + spores
    "A": (245, 245, 231), "a": (224, 181, 98),        # horn ivory, gold spiral (Bright Qud's horn colours)
    "T": (214, 186, 140), "t": (160, 130, 92), "k": (246, 240, 222),  # pedestrian paws: fur, shade, claws
    "O": (122, 92, 120), "o": (84, 60, 86), "E": (236, 226, 196),     # ovipositor segments, egg
    "S": (226, 176, 170), "s": (170, 116, 112),       # broodling sack
    "H": (250, 184, 130), "h": (209, 124, 82), "D": (15, 19, 32),  # hydra heads: Bright Qud's doll skin + eyes
    "N": (78, 158, 176), "n": (44, 104, 122),         # fins
    "Z": (104, 160, 92), "z": (64, 112, 60),          # scales
    "V": (96, 176, 64), "v": (56, 120, 40),           # leaves
    "Q": (126, 92, 60), "q": (84, 60, 38),            # roots
}

LAYERS = {
    # Behind the body ("mutback/..." sorts with Bright Qud's back mutations).
    "mutback/seedtail": (4, [  # Seed Cannon in the tail slot: up the right side, flared cannon mouth on top
        "............RKKR",
        ".............CCc",
        "..............Cc",
        "..............Cc",
        "..............Cc",
        "..............Cc",
        "..............Cc",
        "..............Cc",
        "..............Cc",
        "..............Cc",
        ".............Cc.",
        "............Cc..",
        "...........Cc...",
    ]),
    "mutback/tail": (16, [  # any other tail: a curl from the right hip to the ground
        "...........Cc...",
        "............Cc..",
        ".............Cc.",
        ".............Cc.",
        "............Cc..",
        "...........cC...",
    ]),
    "mutback/ropel": (16, [  # Conjoinment toward a mate on the viewer's left (west)
        "....P...........",
        "...Pp...........",
        "...P............",
        "..pP............",
        "..P.............",
        ".PP.............",
        "Pp..............",
    ]),
    "mutback/roper": (16, [  # ... toward a mate on the right (east), or no side known
        "...........P....",
        "...........pP...",
        "............P...",
        "............Pp..",
        ".............P..",
        ".............PP.",
        "..............pP",
    ]),
    "mutback/waxflab": (8, [  # waxflab on the back: crust heaped on both shoulders, below the face
        "...W........W...",
        "..WwW......WwW..",
        "..wW........Ww..",
        "...w........w...",
    ]),
    # In front of the body.
    "mutfront/ribcage": (10, [  # Evolving Exoskeleton's Ribcage Chestplate (worn on the body)
        "......bBBb......",
        ".......BB.......",
        ".....bBBBBb.....",
        ".......BB.......",
        ".....bBBBBb.....",
    ]),
    "muthead/gills": (8, [  # Amphibious / Gills: slits on the sides of the neck
        "......r..r......",
    ]),
    "mutfront/glowcrustr": (9, [  # glowcrust on the right arm (viewer's left sleeve)
        "...Gg...........",
        "...gG...........",
        "...Gg...........",
        "....G...........",
        "...Gg...........",
        "...gG...........",
    ]),
    "mutfront/mumblesr": (15, [  # mumble mouth on the right hand
        "...MM...........",
        "...mM...........",
    ]),
    "muthead/fickle": (4, [  # fickle gill on the face: frills on both cheeks, a few spores
        "....Y......Y....",
        "....F......F....",
        "....Ff....fF....",
    ]),
    "muthead/unihorn": (0, [  # a single spiral horn (UD Horns Plus Spiral/Single) on the main head
        "........A.......",
        ".......aA.......",
        ".......Aa.......",
    ]),
    "mutfront/unihornr": (0, [  # ... on the extra head on the viewer's right shoulder (Bright Qud's twoheads)
        ".............A..",
        "............aA..",
        "............Aa..",
    ]),
    "mutfront/paws": (21, [  # Pedestrian Paws: clawed paws over the feet
        ".....TT..TT.....",
        "....kTTt.tTTk...",
    ]),
    "mutback/ovipositor": (15, [  # Ovipositor tail: segmented, an egg sac swelling near the tip
        "...........Oo...",
        "............Oo..",
        ".............Oo.",
        ".............oO.",
        "............OOOo",
        "............OEEo",
        ".............oo.",
        "..............E.",
    ]),
    # Hydra (any 4+ heads; the main head and the two shoulder heads are separate layers): extra heads on necks
    # behind, above the shoulders. 6+ heads gets a crown of four small heads instead: "many", not a count.
    "mutback/hydra": (0, [
        "..HHH......HHH..",
        "..DHD......DHD..",
        "...Hh......hH...",
        "....h......h....",
        "....Hh....hH....",
        ".....h....h.....",
    ]),
    "mutback/hydramany": (0, [
        "HH..HHH..HHH..HH",
        "DH..DHD..DHD..HD",
        ".h...Hh..hH...h.",
        ".h....h..h....h.",
        "..h...hh.h...h..",
        "...h.........h..",
    ]),
    "mutback/fins": (7, [  # fins (body parts or fin mutations): flared out on both sides of the back
        "...N........N...",
        "..NN........NN..",
        ".NNn........nNN.",
        "..Nn........nN..",
    ]),
    "mutfront/scales": (9, [  # scales: on the sleeves, hands and legs (the shirt stays)
        "....Z......z....",
        "....z......Z....",
        "....Z......z....",
        "....z......Z....",
        "................",
        "................",
        "....Z......z....",
        "................",
        ".....Z....z.....",
        ".....z....Z.....",
        ".....Z....z.....",
    ]),
    "mutfront/leaves": (8, [  # leaves / bark / photosynthetic skin: leaf clusters at the shoulders and hips
        "...VV......VV...",
        "...vV......Vv...",
        "................",
        "................",
        "................",
        "................",
        "................",
        "....V......V....",
        "....vV....Vv....",
    ]),
    "muthead/gloweyes": (5, [  # glowing / dark-sight eyes
        "......Y..Y......",
    ]),
    "mutfront/roots": (20, [  # roots: spreading from the feet
        "................",
        "................",
        "....qQ....Qq....",
        "...Q..Q..Q..Q...",
    ]),
    "mutback/broodsack": (8, [  # Broodling Sack on the back: a pale sack bulging past both sides
        "....sSSSSSSs....",
        "...sSSSSSSSSs...",
        "..sSSSSSSSSSSs..",
        "..SSSSSSSSSSSS..",
        "..SSSSSSSSSSSS..",
        "..sSSSSSSSSSSs..",
        "...sSSSSSSSSs...",
        "....ssSSSSss....",
    ]),
}
MIRROR = {"mutfront/glowcrustl": "mutfront/glowcrustr", "mutfront/mumblesl": "mutfront/mumblesr",
          "mutfront/unihornl": "mutfront/unihornr"}

BRIGHTQUD = Path("C:/Users/Arend/AppData/LocalLow/Freehold Games/CavesOfQud/Mods/BrightQud/Textures")


def extra_layers():
    """Layers made from Bright Qud's own art: extra heads (its twoheads head, mirrored for the left shoulder)
    and the gelatinous slime coats (its body silhouette, washed in slime)."""
    out = {}
    twin = Image.open(BRIGHTQUD / "brightquddoll_mutfront_twoheads.png").convert("RGBA")
    out["mutfront/headr"] = twin
    out["mutfront/headl"] = twin.transpose(Image.FLIP_LEFT_RIGHT)
    body = Image.open(BRIGHTQUD / "brightquddoll_body_base.png").convert("RGBA")
    for key, rgb, gloss in (("mutfront/slimepoison", (70, 196, 84), (190, 250, 170)),
                            ("mutfront/slime", (84, 170, 200), (200, 240, 250))):
        im = Image.new("RGBA", (16, 24), (0, 0, 0, 0))
        for y in range(24):
            for x in range(16):
                if body.getpixel((x, y))[3] == 0:
                    continue
                # a translucent wash; glossy streaks down the left of the torso and the legs
                glossy = (x in (5, 6) and y in (10, 11, 17)) or (x == 9 and y == 12)
                im.putpixel((x, y), gloss + (220,) if glossy else rgb + (120,))
        # drips under the hem and the hands
        for x, y in ((4, 16), (11, 16), (6, 23), (10, 23)):
            if y < 24:
                im.putpixel((x, y), rgb + (200,))
        out[key] = im
    out.update(infection_layers())
    return out


# Mycologist infections are equipment: they can sit on any slot, and the doll shows each on the slot it is on
# now. "<infection><slot>" for every slot; back sits behind the body, the rest in front. Region pixels are
# (x, y, main/dark) on the doll body (arms are its outer columns, hands row 15-16, feet row 21-22).
SLOTS = {
    "armr": [(3, 9, 1), (4, 9, 0), (3, 10, 0), (4, 10, 1), (3, 11, 1), (4, 11, 0), (4, 12, 1), (3, 13, 1), (4, 13, 0), (3, 14, 0), (4, 14, 1)],
    "handr": [(3, 15, 1), (4, 15, 1), (3, 16, 0), (4, 16, 1)],
    "back": [(2, 8, 1), (3, 8, 1), (2, 9, 0), (3, 9, 1), (3, 10, 0), (12, 8, 1), (13, 8, 1), (12, 9, 1), (13, 9, 0), (12, 10, 0)],
    "face": [(4, 5, 1), (4, 6, 0), (11, 5, 1), (11, 6, 0), (5, 4, 1), (10, 4, 1)],
    "head": [(6, 2, 1), (7, 2, 0), (8, 2, 1), (9, 2, 1), (7, 1, 1)],
    "feet": [(4, 21, 0), (4, 22, 1), (6, 22, 0), (7, 22, 1), (8, 22, 1), (9, 22, 0), (11, 21, 0), (11, 22, 1)],
    "body": [(6, 11, 1), (7, 12, 0), (8, 11, 1), (9, 13, 1), (6, 13, 0)],
}
SLOTS["arml"] = [(15 - x, y, s) for x, y, s in SLOTS["armr"]]
SLOTS["handl"] = [(15 - x, y, s) for x, y, s in SLOTS["handr"]]
INFECTIONS = {  # name: (main, dark, accent or None)
    "glowcrust": (P["G"], P["g"], None),
    "waxflab": (P["W"], P["w"], None),
    "mumbles": (P["M"], P["m"], None),
    "fickle": (P["F"], P["f"], P["Y"]),
}


def infection_layers():
    out = {}
    for inf, (main, dark, accent) in INFECTIONS.items():
        for slot, px in SLOTS.items():
            im = Image.new("RGBA", (16, 24), (0, 0, 0, 0))
            for i, (x, y, s) in enumerate(px):
                c = main if s else dark
                if accent is not None and s and i % 3 == 0:
                    c = accent  # fickle gill sheds spores
                im.putpixel((x, y), c + (255,))
            group = "mutback/" if slot == "back" else "mutfront/"
            out[group + inf + slot] = im
    return out


def render(y0, lines, mirror=False):
    im = Image.new("RGBA", (16, 24), (0, 0, 0, 0))
    for j, line in enumerate(lines):
        for x, ch in enumerate(line):
            if ch != ".":
                im.putpixel((15 - x if mirror else x, y0 + j), P[ch] + (255,))
    return im


# ---------------------------------------------------------------- animation
# Our layers run their own FRAMES-frame cycle (DollExtras puts a phase marker in the doll description every
# 250 ms, Bright Qud's fastest doll refresh; Compose swaps "<key>" for "<key>f<k>"). This is our own motion,
# not Bright Qud's two-frame idle beat: drips run, fall and splash; tails and ropes sway a full arc; glows
# breathe; eyes blink; mouths chatter; spores rise and fade; hydra heads weave. Frame 0 is the plain layer.
FRAMES = 8
WAVE = [0, 1, 1, 1, 0, -1, -1, -1]          # a full sway, one pixel each way
LIFT = [0, 0, -1, -1, -1, 0, 0, 0]          # rise and settle
PULSE = [1.0, 1.08, 1.18, 1.28, 1.18, 1.08, 1.0, 0.94]


def _move(im, pick, dx, dy, keep_joint=False):
    """Moves the pixels pick(x, y, px) selects by (dx, dy); the rest stay. keep_joint leaves a copy behind."""
    out = im.copy()
    src = im.load()
    moved = []
    for y in range(24):
        for x in range(16):
            p = src[x, y]
            if p[3] and pick(x, y, p):
                moved.append((x, y, p))
                if not keep_joint:
                    out.putpixel((x, y), (0, 0, 0, 0))
    for x, y, p in moved:
        if 0 <= x + dx < 16 and 0 <= y + dy < 24:
            out.putpixel((x + dx, y + dy), p)
    return out


def _tint(im, pick, f):
    out = im.copy()
    for y in range(24):
        for x in range(16):
            p = out.getpixel((x, y))
            if p[3] and pick(x, y, p):
                out.putpixel((x, y), f(p))
    return out


def _bright(k):
    return lambda p: tuple(max(0, min(255, int(c * k))) for c in p[:3]) + (p[3],)


def _swap(a, b):
    a, b = P[a], P[b]
    return lambda p: (b + (p[3],)) if p[:3] == a else (a + (p[3],)) if p[:3] == b else p


def _put(im, x, y, rgb, a=255):
    if 0 <= x < 16 and 0 <= y < 24:
        im.putpixel((x, y), tuple(rgb) + (a,))


def _drips(im, k, rgb, sources):
    """Poison / slime dripping: from each source a drop swells, runs down, falls and splashes.
    sources = (x, y, start phase, fall rows)."""
    out = im.copy()
    hi = tuple(min(255, c + 70) for c in rgb)
    for x, y, start, fall in sources:
        t = (k - start) % FRAMES
        if t <= 2:                       # swelling and running
            for d in range(t + 1):
                _put(out, x, y + d, rgb, 210)
            _put(out, x, y + t, hi, 235)
        elif t <= 4:                     # the drop lets go and falls
            _put(out, x, y, rgb, 150)
            _put(out, x, y + 2 + (t - 2) * max(1, fall // 3), hi, 235)
        elif t == 5:                     # splash at the ground
            gy = min(23, y + fall)
            _put(out, x - 1, gy, rgb, 200)
            _put(out, x + 1, gy, rgb, 200)
            _put(out, x, gy, hi, 220)
        else:                            # a puddle that soaks away
            gy = min(23, y + fall)
            _put(out, x, gy, rgb, 150 if t == 6 else 90)
    return out


def _slime(im, k, rgb):
    # the glossy streaks slide slowly down the coat
    out = im if k % 4 < 2 else _move(im, lambda x, y, p: p[3] == 220, 0, 1)
    # drips off both hands, the hem and one leg, out of step with each other
    return _drips(out, k, rgb, [(4, 16, 0, 7), (11, 16, 4, 7), (6, 18, 2, 5), (10, 21, 6, 2)])


def _blink(im, k):
    if k == 5:
        return Image.new("RGBA", (16, 24), (0, 0, 0, 0))     # eyes shut: the doll's own dark eyes show
    return _tint(im, lambda x, y, p: True, _bright(PULSE[k]) if k != 3 else (lambda p: (255, 252, 210, 255)))


def _spores(im, k):
    out = _tint(im, lambda x, y, p: p[:3] == P["Y"], lambda p: (0, 0, 0, 0))
    for sx, start in ((4, 0), (11, 3), (5, 5), (10, 1)):
        t = (k - start) % FRAMES
        if t < 4:
            _put(out, sx + (1 if t == 3 and sx < 8 else -1 if t == 3 else 0), 4 - t, P["Y"], 255 - t * 50)
    return out


ANIM = {
    "mutback/seedtail": lambda im, k: _move(im, lambda x, y, p: y <= 13, 0, LIFT[k], keep_joint=True) if LIFT[k] else
        _move(im, lambda x, y, p: y <= 6, WAVE[(k + 2) % 8], 0),
    "mutback/tail": lambda im, k: _move(_move(im, lambda x, y, p: y >= 19, WAVE[k], 0), lambda x, y, p: y >= 21, WAVE[(k + 1) % 8], 0),
    "mutback/ovipositor": lambda im, k: _tint(_move(im, lambda x, y, p: y >= 19, -WAVE[k], 0),
        lambda x, y, p: p[:3] == P["E"], _bright(PULSE[k])),
    "mutback/ropel": lambda im, k: _move(_move(im, lambda x, y, p: y >= 19, WAVE[k], 0), lambda x, y, p: y >= 21, WAVE[(k + 1) % 8], 0),
    "mutback/roper": lambda im, k: _move(_move(im, lambda x, y, p: y >= 19, -WAVE[k], 0), lambda x, y, p: y >= 21, -WAVE[(k + 1) % 8], 0),
    "mutback/fins": lambda im, k: _move(im, lambda x, y, p: True, 0, LIFT[k]),
    "mutback/hydra": lambda im, k: _move(_move(im, lambda x, y, p: y <= 2 and x < 8, WAVE[k], 0),
        lambda x, y, p: y <= 2 and x >= 8, WAVE[(k + 4) % 8], 0),
    "mutback/hydramany": lambda im, k: _move(_move(im, lambda x, y, p: y <= 2 and x < 8, WAVE[(k + 2) % 8], LIFT[k]),
        lambda x, y, p: y <= 2 and x >= 8, WAVE[(k + 6) % 8], LIFT[(k + 4) % 8]),
    "mutback/broodsack": lambda im, k: _move(im, lambda x, y, p: y >= 14, 0, 1, keep_joint=True) if k in (2, 3, 4) else im,
    "mutfront/glowcrustr": lambda im, k: _tint(im, lambda x, y, p: True, _bright(PULSE[k])),
    "mutfront/glowcrustl": lambda im, k: _tint(im, lambda x, y, p: True, _bright(PULSE[k])),
    "muthead/gloweyes": _blink,
    "mutfront/mumblesr": lambda im, k: _tint(im, lambda x, y, p: True, _swap("M", "m")) if k in (1, 2, 5) else im,
    "mutfront/mumblesl": lambda im, k: _tint(im, lambda x, y, p: True, _swap("M", "m")) if k in (2, 3, 6) else im,
    "muthead/fickle": _spores,
    "mutfront/leaves": lambda im, k: _move(_move(im, lambda x, y, p: y in (8, 9), WAVE[k], 0), lambda x, y, p: y in (15, 16), WAVE[(k + 3) % 8], 0),
    "muthead/gills": lambda im, k: _tint(im, lambda x, y, p: True, _bright(1.25 if k in (2, 6) else 1.0)),
    "mutfront/slimepoison": lambda im, k: _slime(im, k, (70, 196, 84)),
    "mutfront/slime": lambda im, k: _slime(im, k, (84, 170, 200)),
}


def infection_anim(key):
    """Slot variants of the infections: glowcrust pulses, mumble mouths chatter, fickle spores drift up."""
    name = key.split("/", 1)[1]
    if name.startswith("glowcrust"):
        return lambda im, k: _tint(im, lambda x, y, p: True, _bright(PULSE[k]))
    if name.startswith("mumbles"):
        return lambda im, k: _tint(im, lambda x, y, p: True, _swap("M", "m")) if k in (1, 2, 5) else im
    if name.startswith("fickle"):
        return lambda im, k: _move(im, lambda x, y, p: p[:3] == P["Y"], 0, -LIFT[k] * -1 - (1 if k in (3, 4) else 0))
    return None


def save(key, im):
    name = "brightquddoll_" + key.replace("/", "_") + ".png"
    im.save(OUT / name)
    Image.new("RGBA", (16, 24), (0, 0, 0, 0)).save(OUT / "BrightQudMask" / name)  # own colours


def main():
    (OUT / "BrightQudMask").mkdir(parents=True, exist_ok=True)
    jobs = {k: (v, False) for k, v in LAYERS.items()}
    jobs.update({k: (LAYERS[src], True) for k, src in MIRROR.items()})
    made = {}
    for key, ((y0, lines), mirror) in jobs.items():
        assert "_" not in key, key
        made[key] = render(y0, lines, mirror)
    made.update(extra_layers())
    frames = 0
    for key, im in made.items():
        save(key, im)
        anim = ANIM.get(key) or infection_anim(key)
        if anim is not None:
            for k in range(1, FRAMES):
                save(key + "f" + str(k), anim(im, k))
                frames += 1
    print(len(made), "layers +", frames, "animation frames ->", OUT)


if __name__ == "__main__":
    main()
