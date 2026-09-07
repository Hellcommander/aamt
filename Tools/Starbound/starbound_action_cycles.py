#!/usr/bin/env python3
"""
Starbound / OpenStarbound action-cycle renderer.

Turns a single still into named frame sequences that match vanilla
.animation state machines (wand charge, monster walk/jump/fall/hurt,
mech movement+fire, object idle/open/close/working).

Frame names follow unpacked basegame assets:
  monsters/walkers/bobot/body/default.frames
  items/active/weapons/wand/wand.animation
  vehicles/mech/mech.animation
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple
import sys

from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
from libs.spritesheet_assembler import (
    pack_named_rows as _pack_named_rows,
    pack_strip as _pack_strip_lib,
    write_starbound_frames,
)

Vec2 = Tuple[float, float]


@dataclass(frozen=True)
class Cycle:
    name: str
    frames: int
    vanilla_prefix: str  # written as prefix.1 .. prefix.N
    mode: str = "loop"  # loop | transition | end
    cycle_sec: float = 0.8


# Recommended sets from OpenStarbound gameplay states.
ACTIVE_ITEM = [
    Cycle("idle", 8, "idle", "loop", 1.2),
    Cycle("charge", 8, "charging", "transition", 0.9),
    Cycle("spark", 3, "spark", "transition", 0.3),
    Cycle("charged", 4, "loop", "loop", 0.5),
    Cycle("fire", 6, "fire", "transition", 0.25),
    Cycle("discharge", 3, "discharge", "transition", 0.3),
    Cycle("cooldown", 4, "cooldown", "transition", 0.4),
    Cycle("altFire", 6, "altFire", "transition", 0.28),
]

MONSTER = [
    Cycle("idle", 8, "idle", "loop", 1.5),
    Cycle("walk", 8, "walk", "loop", 0.7),
    Cycle("run", 8, "run", "loop", 0.45),
    Cycle("jump", 4, "jump", "end", 0.4),
    Cycle("fall", 4, "fall", "loop", 0.35),
    Cycle("attack", 8, "attack", "transition", 0.55),
    Cycle("hurt", 2, "hurt", "transition", 0.15),
    Cycle("death", 6, "death", "end", 0.7),
]

VEHICLE = [
    Cycle("idle", 8, "idle", "loop", 1.0),
    Cycle("move", 10, "walk", "loop", 1.0),  # vanilla mech uses walk frames
    Cycle("boost", 6, "boost", "loop", 0.35),
    Cycle("damage", 4, "hurt", "transition", 0.2),
    Cycle("jump", 4, "jump", "end", 0.5),
    Cycle("fall", 4, "fall", "end", 0.5),
    Cycle("fire", 3, "fire", "transition", 0.15),
]

OBJECT = [
    Cycle("idle", 8, "default", "loop", 2.0),  # orientations use <color>.<frame>
    Cycle("open", 6, "open", "end", 0.45),
    Cycle("close", 6, "close", "end", 0.45),
    Cycle("working", 8, "working", "loop", 0.8),
]

TECH = [
    Cycle("activate", 6, "activate", "transition", 0.4),
    Cycle("loop", 8, "loop", "loop", 1.0),
    Cycle("deactivate", 6, "deactivate", "transition", 0.4),
]

BATCH_TO_SET = {
    "weapon": ACTIVE_ITEM,
    "grenade": ACTIVE_ITEM,
    "mech": MONSTER + [
        Cycle("boost", 6, "boost", "loop", 0.35),
        Cycle("fire", 6, "fire", "transition", 0.2),
        Cycle("move", 10, "move", "loop", 1.0),
        Cycle("swim", 8, "swim", "loop", 1.0),
        Cycle("dash", 6, "dash", "transition", 0.35),
        Cycle("dodge", 4, "dodge", "transition", 0.25),
        Cycle("charge", 8, "charging", "transition", 0.8),
        Cycle("deploy", 6, "deploy", "end", 0.5),
    ],
    "minion": MONSTER,
    "station": OBJECT,
    "spellstone": [ACTIVE_ITEM[0], Cycle("fire", 6, "fire", "transition", 0.35)],
    "ingredient": [ACTIVE_ITEM[0]],
    "reagent": [ACTIVE_ITEM[0]],
    "misc_icon": [ACTIVE_ITEM[0]],
}


def _glow_layer(base: Image.Image) -> Image.Image:
    glow = base.filter(ImageFilter.GaussianBlur(radius=max(1, base.width // 20)))
    glow = ImageEnhance.Brightness(glow).enhance(1.65)
    return ImageEnhance.Color(glow).enhance(1.2)


def _apply_glow(base: Image.Image, glow: Image.Image, amount: float) -> Image.Image:
    if amount <= 0:
        return base
    r, g, b, a = glow.split()
    a = a.point(lambda v, p=amount: int(v * min(1.0, p)))
    return Image.alpha_composite(base, Image.merge("RGBA", (r, g, b, a)))


def _tint(img: Image.Image, rgb: Tuple[int, int, int], amount: float) -> Image.Image:
    if amount <= 0:
        return img
    overlay = Image.new("RGBA", img.size, (*rgb, int(255 * min(1.0, amount))))
    return Image.alpha_composite(img, overlay)


def place(
    base: Image.Image,
    *,
    scale_xy: Vec2 = (1.0, 1.0),
    angle: float = 0.0,
    dx: float = 0.0,
    dy: float = 0.0,
    brightness: float = 1.0,
    glow: float = 0.0,
    glow_img: Optional[Image.Image] = None,
    alpha: float = 1.0,
    tint: Optional[Tuple[Tuple[int, int, int], float]] = None,
    smear: int = 0,
    smear_dx: float = 0.0,
) -> Image.Image:
    """Composite a posed copy of `base` onto a same-sized transparent canvas."""
    tw, th = base.size
    canvas = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    img = base
    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)
    if glow_img is not None and glow > 0:
        img = _apply_glow(img, glow_img, glow)
    if tint:
        img = _tint(img, tint[0], tint[1])
    if alpha < 1.0:
        r, g, b, a = img.split()
        a = a.point(lambda v, p=alpha: int(v * p))
        img = Image.merge("RGBA", (r, g, b, a))

    sx, sy = scale_xy
    nw = max(1, int(round(tw * abs(sx))))
    nh = max(1, int(round(th * abs(sy))))
    posed = img.resize((nw, nh), Image.Resampling.BICUBIC)
    if sx < 0:
        posed = ImageOps.mirror(posed)
    if angle:
        posed = posed.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)

    def paste_at(target: Image.Image, sprite: Image.Image, ox: float, oy: float) -> None:
        x = int(round((tw - sprite.width) / 2 + ox))
        y = int(round((th - sprite.height) / 2 + oy))
        layer = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        layer.paste(sprite, (x, y), sprite)
        return Image.alpha_composite(target, layer)

    if smear > 0 and smear_dx:
        for i in range(smear, 0, -1):
            fade = 0.18 * (i / smear)
            ghost = posed.copy()
            gr, gg, gb, ga = ghost.split()
            ga = ga.point(lambda v, p=fade: int(v * p))
            ghost = Image.merge("RGBA", (gr, gg, gb, ga))
            canvas = paste_at(canvas, ghost, dx - smear_dx * i, dy)
    return paste_at(canvas, posed, dx, dy)


def _t(i: int, n: int) -> float:
    return i / max(1, n)


def _tau(i: int, n: int) -> float:
    return _t(i, n) * 2.0 * math.pi


def render_cycle(base: Image.Image, cycle: Cycle) -> List[Image.Image]:
    glow = _glow_layer(base)
    w, h = base.size
    n = cycle.frames
    name = cycle.name
    out: List[Image.Image] = []

    for i in range(n):
        t = _t(i, n)
        tau = _tau(i, n)
        if name == "idle" or name == "loop" or cycle.vanilla_prefix == "default":
            pulse = 0.5 + 0.5 * math.sin(tau)
            out.append(place(base, brightness=0.96 + 0.10 * pulse, glow=0.18 + 0.40 * pulse, glow_img=glow))
        elif name == "walk" or name == "move":
            bob = math.sin(tau) * h * 0.07
            lean = math.sin(tau) * 7.0
            squash = 1.0 + math.sin(tau * 2) * 0.05
            out.append(place(base, angle=lean, dy=bob, scale_xy=(1.0 / squash, squash), glow=0.12, glow_img=glow))
        elif name == "run":
            bob = math.sin(tau) * h * 0.10
            lean = math.sin(tau) * 12.0
            squash = 1.0 + math.sin(tau * 2) * 0.08
            out.append(place(
                base, angle=lean, dy=bob, dx=math.cos(tau) * w * 0.04,
                scale_xy=(1.05 / squash, squash * 0.96), glow=0.2, glow_img=glow,
                smear=2, smear_dx=w * 0.06,
            ))
        elif name == "jump":
            # squash → stretch launch → hang → start fall
            keys = [(0.92, 1.12, 0, 2, 0.0), (1.08, 0.88, -8, -h * 0.18, 0.2),
                    (1.02, 0.96, 0, -h * 0.22, 0.15), (1.0, 1.04, 6, -h * 0.08, 0.05)]
            sx, sy, ang, dy, g = keys[min(i, len(keys) - 1)]
            out.append(place(base, scale_xy=(sx, sy), angle=ang, dy=dy, glow=g, glow_img=glow, brightness=1.05))
        elif name == "fall":
            stretch = 1.0 + 0.08 * t
            out.append(place(base, scale_xy=(1.0 / stretch, stretch), angle=4 + 6 * t, dy=h * 0.04 * t, glow=0.08, glow_img=glow))
        elif name in ("charge", "charging"):
            grow = 1.0 + 0.08 * t
            out.append(place(base, scale_xy=(grow, grow), brightness=1.0 + 0.25 * t, glow=0.2 + 0.7 * t, glow_img=glow))
        elif name == "spark":
            flash = 1.0 if i % 2 == 0 else 0.45
            out.append(place(base, brightness=1.15, glow=0.9 * flash, glow_img=glow, scale_xy=(1.06, 1.06)))
        elif name == "charged":
            pulse = 0.5 + 0.5 * math.sin(tau)
            out.append(place(base, brightness=1.08 + 0.08 * pulse, glow=0.55 + 0.35 * pulse, glow_img=glow))
        elif name in ("fire", "discharge", "altFire"):
            # wind-up is short; peak flash then recoil
            peak = 1.0 - abs((t - 0.35) * 2.2)
            peak = max(0.0, min(1.0, peak))
            recoil = (1.0 if name != "altFire" else -1.0) * w * 0.10 * peak
            kick = -8.0 if name != "altFire" else 8.0
            out.append(place(
                base,
                angle=kick * peak,
                dx=recoil,
                brightness=1.0 + 0.45 * peak,
                glow=0.3 + 0.85 * peak,
                glow_img=glow,
                smear=3 if peak > 0.4 else 0,
                smear_dx=recoil * 0.4,
            ))
        elif name == "cooldown":
            settle = 1.0 - t
            out.append(place(base, angle=-4 * settle, dx=w * 0.04 * settle, glow=0.15 * settle, glow_img=glow))
        elif name == "attack":
            # windup / fire / cooldown packed into one monster cycle
            if t < 0.35:
                u = t / 0.35
                out.append(place(base, angle=18 * u, dx=-w * 0.08 * u, scale_xy=(1.0, 0.96), glow=0.2 * u, glow_img=glow))
            elif t < 0.6:
                u = (t - 0.35) / 0.25
                out.append(place(base, angle=-22 * u, dx=w * 0.12 * u, brightness=1.2, glow=0.9, glow_img=glow, smear=3, smear_dx=w * 0.08))
            else:
                u = (t - 0.6) / 0.4
                out.append(place(base, angle=-8 * (1 - u), glow=0.2 * (1 - u), glow_img=glow))
        elif name in ("hurt", "damage"):
            out.append(place(
                base, dx=w * (0.08 if i == 0 else -0.03), angle=8 if i == 0 else -4,
                brightness=1.4, tint=((255, 80, 80), 0.35 if i == 0 else 0.12),
            ))
        elif name == "death":
            out.append(place(
                base, angle=12 * t, dy=h * 0.18 * t, scale_xy=(1.0 + 0.1 * t, 1.0 - 0.15 * t),
                alpha=1.0 - 0.85 * t, brightness=0.85, tint=((20, 20, 40), 0.25 * t),
            ))
        elif name == "open":
            out.append(place(base, scale_xy=(0.85 + 0.15 * t, 0.85 + 0.15 * t), glow=0.15 + 0.5 * t, glow_img=glow, brightness=0.9 + 0.2 * t))
        elif name == "close":
            u = 1.0 - t
            out.append(place(base, scale_xy=(0.85 + 0.15 * u, 0.85 + 0.15 * u), glow=0.15 + 0.5 * u, glow_img=glow))
        elif name == "working":
            pulse = 0.5 + 0.5 * math.sin(tau * 2)
            out.append(place(base, angle=math.sin(tau) * 3, brightness=1.0 + 0.15 * pulse, glow=0.25 + 0.55 * pulse, glow_img=glow))
        elif name == "boost" or name == "dash":
            stretch = 1.08 if name == "dash" else 1.12
            out.append(place(
                base, scale_xy=(stretch, 0.92), dx=w * (0.10 if name == "dash" else 0.06),
                glow=0.4, glow_img=glow, smear=4, smear_dx=w * 0.10, brightness=1.1,
            ))
        elif name == "swim":
            bob = math.sin(tau) * h * 0.10
            roll = math.sin(tau) * 6.0
            out.append(place(base, angle=roll, dy=bob, dx=math.cos(tau) * w * 0.05, glow=0.22, glow_img=glow))
        elif name == "dodge":
            out.append(place(
                base, dx=w * (0.14 if i % 2 == 0 else -0.10), angle=-10 if i == 0 else 6,
                alpha=0.55 + 0.45 * (1.0 - t), glow=0.35, glow_img=glow,
            ))
        elif name in ("deploy", "open"):
            out.append(place(base, scale_xy=(0.85 + 0.15 * t, 0.85 + 0.15 * t), glow=0.15 + 0.5 * t, glow_img=glow, brightness=0.9 + 0.2 * t))
        elif name == "activate":
            out.append(place(base, alpha=0.25 + 0.75 * t, glow=0.8 * t, glow_img=glow, scale_xy=(0.9 + 0.1 * t, 0.9 + 0.1 * t)))
        elif name == "deactivate":
            u = 1.0 - t
            out.append(place(base, alpha=0.25 + 0.75 * u, glow=0.8 * u, glow_img=glow))
        else:
            pulse = 0.5 + 0.5 * math.sin(tau)
            out.append(place(base, glow=0.2 * pulse, glow_img=glow))
    return out


def pack_named_atlas(
    cycles: Dict[str, List[Image.Image]],
    prefixes: Dict[str, str],
    dest_png: Path,
    dest_frames: Path,
) -> Tuple[int, int]:
    """Dense row-per-cycle atlas with vanilla `prefix.N` names."""
    packed = _pack_named_rows(cycles, dest_png, dest_frames, prefixes)
    return packed.tile


def pack_strip(frames: Sequence[Image.Image], dest: Path) -> None:
    _pack_strip_lib(frames, dest)


def write_strip_frames(path: Path, tw: int, th: int, prefix: str, n: int) -> None:
    names = [f"{prefix}.{i + 1}" for i in range(n)]
    write_starbound_frames(path, tw, th, names, alias=prefix, extra_aliases={"default": names[0]})


def build_active_item_animation(part: str, sheet_rel: str, cycles: Iterable[Cycle]) -> dict:
    """Vanilla wand.animation shape: charge state machine + fire/cooldown/altFire."""
    by = {c.name: c for c in cycles}
    def st(name: str, transition: Optional[str] = None) -> Optional[dict]:
        c = by.get(name)
        if c is None:
            return None
        d = {"frames": c.frames, "cycle": c.cycle_sec, "mode": c.mode}
        if transition and transition in by:
            d["transition"] = transition
        return d

    def states(*pairs):
        out = {}
        for name, spec in pairs:
            if spec is not None:
                out[name] = spec
        return out

    # Vanilla wand/staff use stateType "charge". Magi-Tech also exposes
    # "weapon" for fire / cooldown / altFire (recommended active-item set).
    charge_states = {"idle": {}}
    for key, spec in (
        ("charge", st("charge", "spark")),
        ("spark", st("spark", "charged")),
        ("charged", st("charged")),
        ("discharge", st("discharge", "idle")),
    ):
        if spec is not None:
            charge_states[key] = spec

    weapon_states = {}
    for key, spec in (
        ("idle", st("idle")),
        ("fire", st("fire", "cooldown")),
        ("cooldown", st("cooldown", "idle")),
        ("altFire", st("altFire", "cooldown")),
    ):
        if spec is not None:
            weapon_states[key] = spec
    if "idle" not in weapon_states:
        weapon_states["idle"] = {}
    return {
        "animatedParts": {
            "stateTypes": {
                "charge": {
                    "default": "idle",
                    "states": charge_states,
                },
                "weapon": {
                    "default": "idle",
                    "states": weapon_states,
                },
            },
            "parts": {
                part: {
                    "properties": {
                        "zLevel": 0,
                        "centered": True,
                        "image": f"{sheet_rel}:idle.<frame>",
                        "transformationGroups": ["weapon"],
                    },
                    "partStates": {
                        "charge": {
                            "idle": {"properties": {"image": f"{sheet_rel}:idle.<frame>"}},
                            "charge": {"properties": {"image": f"{sheet_rel}:charging.<frame>"}},
                            "spark": {"properties": {"image": f"{sheet_rel}:spark.<frame>"}},
                            "charged": {"properties": {"image": f"{sheet_rel}:loop.<frame>"}},
                            "discharge": {"properties": {"image": f"{sheet_rel}:discharge.<frame>"}},
                        },
                        "weapon": {
                            "idle": {"properties": {"image": f"{sheet_rel}:idle.<frame>"}},
                            "fire": {"properties": {"image": f"{sheet_rel}:fire.<frame>"}},
                            "cooldown": {"properties": {"image": f"{sheet_rel}:cooldown.<frame>"}},
                            "altFire": {"properties": {"image": f"{sheet_rel}:altFire.<frame>"}},
                        },
                    },
                }
            },
        },
        "transformationGroups": {"weapon": {}},
        "sounds": {
            "fire": ["/sfx/melee/laser_weapon_swing1.ogg"],
            "charge": ["/sfx/melee/staff_charge1.ogg"],
        },
    }


def build_object_animation(part: str, sheet_rel: str) -> dict:
    """idle / open / close / working plus workbench Lua states basic/improved/advanced."""
    img = lambda tag: f"{sheet_rel}:{tag}.<frame>"
    working = {"properties": {"image": img("working")}}
    idle = {"properties": {"image": img("default")}}
    return {
        "animatedParts": {
            "stateTypes": {
                "interact": {
                    "default": "idle",
                    "states": {
                        "idle": {"frames": 8, "cycle": 2.0, "mode": "loop"},
                        "open": {"frames": 6, "cycle": 0.45, "mode": "transition", "transition": "working"},
                        "close": {"frames": 6, "cycle": 0.45, "mode": "transition", "transition": "idle"},
                        "working": {"frames": 8, "cycle": 0.8, "mode": "loop"},
                    },
                },
                "workbench": {
                    "default": "basic",
                    "states": {
                        "basic": {"frames": 8, "cycle": 2.0, "mode": "loop"},
                        "improved": {"frames": 8, "cycle": 1.2, "mode": "loop"},
                        "advanced": {"frames": 8, "cycle": 0.8, "mode": "loop"},
                    },
                },
            },
            "parts": {
                part: {
                    "properties": {"centered": True, "image": img("default")},
                    "partStates": {
                        "interact": {
                            "idle": idle,
                            "open": {"properties": {"image": img("open")}},
                            "close": {"properties": {"image": img("close")}},
                            "working": working,
                        },
                        "workbench": {
                            "basic": idle,
                            "improved": working,
                            "advanced": working,
                        },
                    },
                }
            },
        }
    }


def build_mech_animation(sheet_rel: str) -> dict:
    """Vanilla vehicles/mech/mech.animation movement + firing."""
    def body(tag: str) -> dict:
        return {"properties": {"image": f"{sheet_rel}:{tag}.<frame>"}}

    return {
        "animatedParts": {
            "stateTypes": {
                "movement": {
                    "default": "idle",
                    "states": {
                        "idle": {"frames": 8, "cycle": 1.2, "mode": "loop"},
                        "walk": {"frames": 8, "cycle": 0.7, "mode": "loop"},
                        "run": {"frames": 8, "cycle": 0.45, "mode": "loop"},
                        "jump": {"frames": 4, "cycle": 0.4, "mode": "end"},
                        "fall": {"frames": 4, "cycle": 0.35, "mode": "loop"},
                        "boost": {"frames": 6, "cycle": 0.35, "mode": "loop"},
                        "swim": {"frames": 8, "cycle": 1.0, "mode": "loop"},
                        "dash": {"frames": 6, "cycle": 0.35, "mode": "transition", "transition": "idle"},
                        "dodge": {"frames": 4, "cycle": 0.25, "mode": "transition", "transition": "idle"},
                        "deploy": {"frames": 6, "cycle": 0.5, "mode": "end"},
                    },
                },
                "attack": {
                    "default": "off",
                    "states": {
                        "off": {},
                        "fire": {"frames": 6, "cycle": 0.2, "mode": "transition", "transition": "off"},
                        "windup": {"frames": 3, "cycle": 0.2, "mode": "transition", "transition": "fire"},
                        "cooldown": {"frames": 4, "cycle": 0.3, "mode": "transition", "transition": "off"},
                    },
                },
                "damage": {
                    "priority": 3,
                    "default": "none",
                    "states": {
                        "none": {},
                        "hit": {"frames": 2, "cycle": 0.15, "mode": "transition", "transition": "none"},
                        "death": {"frames": 6, "cycle": 0.7, "mode": "end"},
                    },
                },
            },
            "parts": {
                "body": {
                    "properties": {
                        "centered": True,
                        "zLevel": 3,
                        "image": f"{sheet_rel}:idle.<frame>",
                        "transformationGroups": ["body"],
                    },
                    "partStates": {
                        "movement": {
                            "idle": body("idle"),
                            "walk": body("walk"),
                            "run": body("run"),
                            "jump": body("jump"),
                            "fall": body("fall"),
                            "boost": body("boost"),
                            "swim": body("swim"),
                            "dash": body("dash"),
                            "dodge": body("dodge"),
                            "deploy": body("deploy"),
                        },
                        "attack": {
                            "fire": body("fire"),
                            "windup": body("attack"),
                            "cooldown": body("idle"),
                        },
                        "damage": {
                            "hit": body("hurt"),
                            "death": body("death"),
                        },
                    },
                }
            },
        },
        "transformationGroups": {"body": {}},
    }


def cycles_for_batch(batch: str) -> List[Cycle]:
    return list(BATCH_TO_SET.get(batch, [ACTIVE_ITEM[0]]))
