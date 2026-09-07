#!/usr/bin/env python3
"""
Procedural Dwarf Fortress Premium-style creature tiles.

32x32 part layers (head/body/RH/LH/RF/LF/tail) plus 96x96 portraits.
Original pixel art — not a copy of vanilla sheets. Heuristic silhouettes
from documented ANIMAL_PEOPLE layer slots.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Sequence, Tuple

RGBA = Tuple[int, int, int, int]
RGB = Tuple[int, int, int]

TILE = 32
COLS = 7
ROWS = 5
PARTS = ["head", "body", "RH", "LH", "RF", "LF", "tail"]
STATES = ["default", "child", "animated", "corpse", "list_icon"]

# DF color index 0-7 mapped to earthy Premium-ish accents (not vanilla assets).
DF_INDEX_RGB: List[RGB] = [
    (42, 36, 32),
    (62, 92, 148),
    (78, 118, 64),
    (56, 128, 132),
    (148, 62, 48),
    (128, 64, 118),
    (156, 118, 52),
    (168, 158, 142),
]


def _clamp(v: int) -> int:
    return 0 if v < 0 else 255 if v > 255 else v


def _mix(a: RGB, b: RGB, t: float) -> RGB:
    return (
        _clamp(int(a[0] + (b[0] - a[0]) * t)),
        _clamp(int(a[1] + (b[1] - a[1]) * t)),
        _clamp(int(a[2] + (b[2] - a[2]) * t)),
    )


def _shade(c: RGB, mul: float) -> RGB:
    return (_clamp(int(c[0] * mul)), _clamp(int(c[1] * mul)), _clamp(int(c[2] * mul)))


def _sat_shift(c: RGB, d: int) -> RGB:
    return (_clamp(c[0] + d), _clamp(c[1] + d // 2), _clamp(c[2] - d // 3))


def features_from_spec(spec: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    spec = spec or {}
    frags = [str(f).upper() for f in (spec.get("body_fragments") or [])]
    joined = " ".join(frags)
    preset = str(spec.get("preset") or "").lower()
    from df_creature_schema import PRESET_INFO

    plan = None
    if preset in PRESET_INFO:
        plan = str(PRESET_INFO[preset].get("plan") or "")
    if not plan and (spec.get("body_mode") or "").lower() == "custom":
        plan = "hematophyte"
    if not plan:
        if "SPIDER" in joined or "CRAB_BODY" in joined:
            plan = "arachnid"
        elif "INSECT" in joined:
            plan = "insectoid"
        elif "BASIC_1PARTBODY_THOUGHT" in joined:
            plan = "amorphous"
        elif "SIDE_FINS" in joined or "SIDE_FLIPPERS" in joined or "FRONT_BODY_FINS" in joined:
            plan = "aquatic"
        elif "TENTACLE" in joined:
            plan = "tentacled"
        elif "CENTAUR" in joined:
            plan = "centaur"
        elif "SHELL" in joined:
            plan = "shelled"
        elif "BEAK" in joined or "BILL" in joined:
            plan = "avian"
        elif "HOOF" in joined:
            plan = "hoofed"
        elif "BASIC_1PARTBODY" in joined:
            plan = "serpentine"
        elif "QUADRUPED" in joined:
            plan = "quadruped"
        elif "WING" in joined:
            plan = "winged"
        else:
            plan = "humanoid"
    culture = str(spec.get("culture_preset") or "none")
    beard_ok = plan in ("humanoid", "winged", "hoofed", "centaur")
    return {
        "plan": plan,
        "has_tail": any("TAIL" in f for f in frags),
        "has_wings": any("WING" in f for f in frags),
        "has_antennae": any("ANTENNA" in f for f in frags),
        "has_beak": any(x in joined for x in ("BEAK", "BILL")),
        "has_shell": "SHELL" in joined,
        "has_horns": any("HORN" in f or "ANTLER" in f for f in frags),
        "has_hooves": "HOOF" in joined,
        "has_fins": any("FIN" in f or "FLIPPER" in f for f in frags),
        "has_hands": (
            any(x in joined for x in ("5FINGERS", "4FINGERS", "3FINGERS", "CLUBBED_TENTACLE"))
            or ("HUMANOID" in joined and "ARMLESS" not in joined)
        ),
        "culture": culture,
        "beard": culture == "dwarf_industry" and beard_ok,
        "profile": str(spec.get("graphics_profile") or "humanoid"),
        "prompt": str(spec.get("art_prompt") or ""),
        "id": str(spec.get("id") or "CREATURE"),
        "preset": preset,
    }


def accent_from_spec(spec: Dict[str, Any]) -> RGB:
    color_raw = spec.get("color") or [3, 0, 0]
    try:
        base = DF_INDEX_RGB[int(color_raw[0]) % len(DF_INDEX_RGB)]
    except Exception:
        base = DF_INDEX_RGB[4]
    prompt = str(spec.get("art_prompt") or "")
    cid = str(spec.get("id") or "")
    h = hashlib.md5(f"{cid}:{prompt}".encode("utf-8")).hexdigest()
    jitter = (int(h[0:2], 16) % 24) - 12
    return _sat_shift(base, jitter)


def _palette(accent: RGB, state: str, culture: str = "dwarf_industry") -> Dict[str, RGB]:
    mid = accent
    if state == "corpse":
        mid = _mix(accent, (70, 72, 64), 0.65)
        mid = _shade(mid, 0.55)
    elif state == "child":
        mid = _mix(accent, (240, 210, 180), 0.22)
    elif state == "animated":
        mid = _mix(accent, (255, 230, 140), 0.12)
    outline = _mix(_shade(mid, 0.28), (12, 10, 8), 0.4)
    shadow = _shade(mid, 0.62)
    hi = _mix(mid, (255, 245, 220), 0.28)
    cloth = _mix(mid, (48, 56, 72), 0.35)
    cloth_hi = _mix(cloth, (200, 190, 160), 0.25)
    hair = {
        "dwarf_industry": (92, 58, 32),
        "elf_nature": (186, 168, 72),
        "goblin_raid": (52, 68, 42),
        "aerie": (210, 180, 90),
        "hive": (40, 48, 28),
        "depths": (36, 48, 72),
        "none": (70, 62, 52),
    }.get(culture, (70, 62, 52))
    if state == "corpse":
        hair = _shade(hair, 0.55)
    return {
        "outline": outline,
        "shadow": shadow,
        "mid": mid,
        "hi": hi,
        "cloth": cloth,
        "cloth_hi": cloth_hi,
        "hair": hair,
        "eye": (18, 16, 14),
        "sclera": (232, 224, 208),
        "iris": _mix(mid, (40, 80, 120), 0.45),
        "bone": (196, 186, 160),
        "chitin": _mix(mid, (32, 48, 28), 0.2),
        "buckle": (196, 164, 72),
    }


class Pix:
    def __init__(self, w: int = TILE, h: int = TILE) -> None:
        self.w = w
        self.h = h
        self.data: List[RGBA] = [(0, 0, 0, 0)] * (w * h)

    def _i(self, x: int, y: int) -> int:
        return y * self.w + x

    def inb(self, x: int, y: int) -> bool:
        return 0 <= x < self.w and 0 <= y < self.h

    def set(self, x: int, y: int, rgb: RGB, a: int = 255) -> None:
        if self.inb(x, y):
            self.data[self._i(x, y)] = (rgb[0], rgb[1], rgb[2], a)

    def get(self, x: int, y: int) -> RGBA:
        if not self.inb(x, y):
            return (0, 0, 0, 0)
        return self.data[self._i(x, y)]

    def opaque(self, x: int, y: int) -> bool:
        return self.get(x, y)[3] > 0

    def fill_ellipse(self, x0: int, y0: int, x1: int, y1: int, rgb: RGB) -> None:
        if x1 < x0:
            x0, x1 = x1, x0
        if y1 < y0:
            y0, y1 = y1, y0
        cx = (x0 + x1) / 2.0
        cy = (y0 + y1) / 2.0
        rx = max(0.5, (x1 - x0) / 2.0)
        ry = max(0.5, (y1 - y0) / 2.0)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                nx = (x + 0.5 - cx) / rx
                ny = (y + 0.5 - cy) / ry
                if nx * nx + ny * ny <= 1.05:
                    self.set(x, y, rgb)

    def fill_rect(self, x0: int, y0: int, x1: int, y1: int, rgb: RGB) -> None:
        if x1 < x0:
            x0, x1 = x1, x0
        if y1 < y0:
            y0, y1 = y1, y0
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.set(x, y, rgb)

    def fill_poly(self, pts: Sequence[Tuple[int, int]], rgb: RGB) -> None:
        if len(pts) < 3:
            return
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        n = len(pts)
        for y in range(miny, maxy + 1):
            for x in range(minx, maxx + 1):
                inside = False
                j = n - 1
                for i in range(n):
                    xi, yi = pts[i]
                    xj, yj = pts[j]
                    if ((yi > y) != (yj > y)) and (
                        x < (xj - xi) * (y - yi) / float(yj - yi or 1) + xi
                    ):
                        inside = not inside
                    j = i
                if inside:
                    self.set(x, y, rgb)

    def line(self, x0: int, y0: int, x1: int, y1: int, rgb: RGB) -> None:
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            self.set(x, y, rgb)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def outline(self, color: RGB) -> None:
        snap = [p[3] > 0 for p in self.data]
        for y in range(self.h):
            for x in range(self.w):
                if not snap[self._i(x, y)]:
                    continue
                edge = False
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nx, ny = x + dx, y + dy
                    if not self.inb(nx, ny) or not snap[self._i(nx, ny)]:
                        edge = True
                        break
                if edge:
                    self.set(x, y, color)

    def light(self, pal: Dict[str, RGB]) -> None:
        snap = [p[3] > 0 for p in self.data]
        for y in range(self.h):
            for x in range(self.w):
                if not snap[self._i(x, y)]:
                    continue
                cur = self.get(x, y)
                if cur[:3] == pal["outline"]:
                    continue
                up = y == 0 or not snap[self._i(x, y - 1)]
                left = x == 0 or not snap[self._i(x - 1, y)]
                down = y == self.h - 1 or not snap[self._i(x, y + 1)]
                if up and left:
                    self.set(x, y, pal["hi"])
                elif down:
                    self.set(x, y, pal["shadow"])

    def to_image(self):
        from PIL import Image  # type: ignore

        im = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        im.putdata(self.data)
        return im

    def blit(self, other: "Pix", ox: int, oy: int) -> None:
        for y in range(other.h):
            for x in range(other.w):
                p = other.get(x, y)
                if p[3] > 0:
                    self.set(x + ox, y + oy, p[:3], p[3])


def _eyes(p: Pix, cx: int, cy: int, pal: Dict[str, RGB], wide: bool = False) -> None:
    gap = 5 if wide else 4
    for ox in (-gap, gap):
        p.set(cx + ox - 1, cy, pal["sclera"])
        p.set(cx + ox, cy, pal["iris"])
        p.set(cx + ox + 1, cy, pal["sclera"])
        p.set(cx + ox, cy - 1, pal["eye"])


def _draw_hematophyte_head(p: Pix, pal: Dict[str, RGB], feat: Dict[str, Any], child: bool) -> None:
    pad = 6 if child else 4
    # Stem-head with maw
    p.fill_ellipse(pad + 4, pad, 26 - pad, 18, pal["mid"])
    p.fill_poly([(10, 14), (22, 14), (20, 22), (12, 22)], pal["shadow"])  # maw cavity
    p.fill_rect(11, 16, 14, 20, pal["outline"])  # tooth
    p.fill_rect(17, 16, 20, 20, pal["outline"])
    # Proboscis needle
    p.fill_poly([(22, 12), (30, 10), (28, 14)], pal["bone"])
    p.set(14, 8, pal["iris"])
    p.set(18, 8, pal["iris"])
    p.light(pal)
    p.outline(pal["outline"])


def _draw_hematophyte_body(p: Pix, pal: Dict[str, RGB], feat: Dict[str, Any], child: bool) -> None:
    # Serpentine trunk
    p.fill_ellipse(8, 4, 24, 28, pal["mid"])
    p.fill_ellipse(10, 8, 22, 24, pal["hi"])
    # Dorsal fronds
    p.fill_poly([(12, 2), (16, 10), (8, 10)], pal["cloth"])
    p.fill_poly([(20, 2), (24, 10), (16, 10)], pal["cloth"])
    # Root-pads
    p.fill_ellipse(6, 24, 14, 30, pal["shadow"])
    p.fill_ellipse(18, 24, 26, 30, pal["shadow"])
    if feat.get("has_wings"):
        pass
    p.light(pal)
    p.outline(pal["outline"])


def _draw_hematophyte_vine(p: Pix, pal: Dict[str, RGB], right: bool) -> None:
    # Thorned vine arm
    if right:
        p.fill_poly([(8, 6), (26, 10), (24, 16), (10, 20)], pal["mid"])
        p.fill_poly([(22, 8), (28, 4), (26, 12)], pal["bone"])  # thorn
        p.fill_ellipse(22, 14, 28, 22, pal["hi"])  # tip grasp
    else:
        p.fill_poly([(24, 6), (6, 10), (8, 16), (22, 20)], pal["mid"])
        p.fill_poly([(10, 8), (4, 4), (6, 12)], pal["bone"])
        p.fill_ellipse(4, 14, 10, 22, pal["hi"])
    p.light(pal)
    p.outline(pal["outline"])


def _draw_humanoid_head(p: Pix, pal: Dict[str, RGB], feat: Dict[str, Any], child: bool) -> None:
    pad = 6 if child else 4
    # hair cap, then face, then beard so face isn't swallowed
    p.fill_ellipse(pad + 1, pad - 1, 30 - pad, pad + 10, pal["hair"])
    p.fill_ellipse(pad + 2, pad + 2, 29 - pad, 22, pal["mid"])
    p.fill_ellipse(pad, 11, pad + 5, 17, pal["mid"])
    p.fill_ellipse(27 - pad, 11, 31 - pad, 17, pal["mid"])
    _eyes(p, 16, 11, pal)
    p.set(15, 10, pal["hair"])  # brows
    p.set(17, 10, pal["hair"])
    p.set(16, 14, pal["shadow"])  # nose
    p.set(15, 15, pal["shadow"])
    p.set(17, 15, pal["shadow"])
    p.set(15, 17, pal["outline"])
    p.set(16, 17, pal["outline"])
    p.set(17, 17, pal["outline"])
    if feat.get("beard") and not child:
        p.fill_ellipse(10, 17, 21, 28, pal["hair"])
        p.fill_rect(13, 24, 18, 29, pal["hair"])
    if feat.get("culture") == "elf_nature":
        p.fill_poly([(3, 7), (7, 12), (6, 18)], pal["mid"])
        p.fill_poly([(28, 7), (24, 12), (25, 18)], pal["mid"])
    p.light(pal)
    p.outline(pal["outline"])


def _draw_insect_head(p: Pix, pal: Dict[str, RGB], feat: Dict[str, Any], child: bool) -> None:
    pad = 6 if child else 4
    p.fill_ellipse(pad + 3, pad + 2, 28 - pad, 24 - pad, pal["chitin"])
    p.fill_ellipse(7, 10, 13, 18, pal["hi"])
    p.fill_ellipse(18, 10, 24, 18, pal["hi"])
    p.set(10, 13, pal["eye"])
    p.set(21, 13, pal["eye"])
    p.fill_poly([(12, 22), (15, 28), (16, 22)], pal["shadow"])
    p.fill_poly([(19, 22), (16, 28), (15, 22)], pal["shadow"])
    if feat.get("has_antennae"):
        p.line(11, 6, 8, 1, pal["outline"])
        p.line(20, 6, 23, 1, pal["outline"])
        p.set(8, 1, pal["hi"])
        p.set(23, 1, pal["hi"])
    p.light(pal)
    p.outline(pal["outline"])


def _draw_quad_head(p: Pix, pal: Dict[str, RGB], child: bool) -> None:
    pad = 5 if child else 3
    p.fill_ellipse(pad, pad + 4, 26, 24, pal["mid"])
    p.fill_ellipse(18, 12, 30, 22, pal["mid"])  # snout
    p.fill_rect(26, 16, 30, 18, pal["shadow"])
    _eyes(p, 14, 12, pal, wide=True)
    p.fill_ellipse(6, 6, 12, 12, pal["mid"])
    p.fill_ellipse(16, 5, 22, 11, pal["mid"])
    p.light(pal)
    p.outline(pal["outline"])


def _draw_snake_head(p: Pix, pal: Dict[str, RGB], child: bool) -> None:
    pad = 6 if child else 4
    p.fill_ellipse(pad, pad + 2, 28 - pad, 22, pal["mid"])
    p.fill_poly([(22, 14), (30, 16), (22, 18)], pal["mid"])
    _eyes(p, 14, 12, pal)
    p.line(24, 16, 28, 20, (180, 50, 50))
    p.line(24, 16, 28, 12, (180, 50, 50))
    p.light(pal)
    p.outline(pal["outline"])


def _draw_humanoid_body(p: Pix, pal: Dict[str, RGB], feat: Dict[str, Any], child: bool) -> None:
    pad = 7 if child else 5
    p.fill_poly(
        [(9, pad + 3), (22, pad + 3), (25, 28 - pad // 2), (6, 28 - pad // 2)],
        pal["cloth"],
    )
    p.fill_rect(12, pad, 19, pad + 5, pal["mid"])  # neck
    p.fill_rect(10, pad + 3, 21, pad + 6, pal["cloth_hi"])  # collar
    p.fill_rect(10, 17, 21, 19, pal["outline"])  # belt
    p.fill_rect(14, 17, 17, 19, pal["buckle"])
    if feat.get("has_wings"):
        p.fill_poly([(1, 7), (10, 12), (3, 24)], pal["hi"])
        p.fill_poly([(30, 7), (21, 12), (28, 24)], pal["hi"])
    p.light(pal)
    p.outline(pal["outline"])


def _draw_insect_body(p: Pix, pal: Dict[str, RGB], child: bool) -> None:
    pad = 6 if child else 4
    p.fill_ellipse(8, pad, 23, 14, pal["chitin"])
    p.fill_ellipse(7, 12, 24, 28 - pad, pal["chitin"])
    p.line(10, 16, 21, 16, pal["outline"])
    p.line(10, 20, 21, 20, pal["outline"])
    p.light(pal)
    p.outline(pal["outline"])


def _draw_quad_body(p: Pix, pal: Dict[str, RGB], child: bool) -> None:
    pad = 6 if child else 4
    p.fill_ellipse(pad, 8, 30 - pad, 24, pal["mid"])
    p.fill_rect(6, 14, 26, 18, pal["shadow"])
    p.light(pal)
    p.outline(pal["outline"])


def _draw_snake_body(p: Pix, pal: Dict[str, RGB], child: bool) -> None:
    p.fill_ellipse(8, 4, 24, 16, pal["mid"])
    p.fill_ellipse(6, 12, 22, 26, pal["mid"])
    p.fill_ellipse(10, 20, 26, 30, pal["shadow"])
    if child:
        p.fill_ellipse(10, 8, 22, 22, pal["mid"])
    p.light(pal)
    p.outline(pal["outline"])


def _draw_hand(p: Pix, pal: Dict[str, RGB], right: bool, child: bool, insect: bool) -> None:
    ox = 2 if right else -2
    if insect:
        p.fill_poly([(16 + ox, 6), (22 + ox * 2, 18), (12, 22), (10, 10)], pal["chitin"])
    else:
        p.fill_ellipse(11, 8, 21, 20, pal["mid"])
        # fingers
        base_y = 19
        for i, fx in enumerate((12, 15, 18, 21)):
            p.fill_rect(fx - 1 + ox // 2, base_y, fx + ox // 2, base_y + 5 + (i % 2), pal["mid"])
        thumb_x = 22 if right else 9
        p.fill_ellipse(thumb_x - 2, 12, thumb_x + 2, 17, pal["mid"])
    if child:
        p.fill_ellipse(12, 10, 20, 20, pal["mid"])
    p.light(pal)
    p.outline(pal["outline"])


def _draw_foot(p: Pix, pal: Dict[str, RGB], right: bool, child: bool, plan: str) -> None:
    if plan in ("insectoid", "arachnid"):
        p.fill_poly([(16, 6), (22, 26), (10, 26)], pal["chitin"])
    elif plan in ("quadruped", "centaur", "hoofed", "shelled"):
        p.fill_ellipse(8, 10, 24, 24, pal["mid"])
        p.fill_rect(10, 22, 22, 26, pal["outline"])
    elif plan in ("serpentine", "amorphous", "tentacled"):
        return
    elif plan in ("aquatic",):
        _draw_fin(p, pal, right)
        return
    elif plan == "avian":
        p.fill_poly([(16, 8), (12, 26), (22, 26)], pal["mid"])
        p.fill_rect(10, 24, 22, 28, pal["outline"])
    else:
        p.fill_rect(11, 8, 20, 22, pal["cloth"])
        p.fill_ellipse(8, 18, 24, 28, pal["cloth"])
        p.fill_rect(8, 25, 24, 29, pal["outline"])  # sole
        cap = (20, 18, 26, 26) if right else (5, 18, 11, 26)
        p.fill_rect(*cap, pal["shadow"])
    if child:
        p.fill_ellipse(11, 12, 21, 24, pal["mid"])
    p.light(pal)
    p.outline(pal["outline"])


def _draw_tail(p: Pix, pal: Dict[str, RGB], feat: Dict[str, Any], child: bool) -> None:
    if feat.get("has_wings") and not feat.get("has_tail"):
        p.fill_poly([(6, 8), (16, 4), (26, 10), (20, 26), (12, 24)], pal["hi"])
        p.line(16, 6, 16, 24, pal["outline"])
        p.light(pal)
        p.outline(pal["outline"])
        return
    if not feat.get("has_tail") and feat.get("plan") in ("humanoid", "hoofed"):
        return
    p.fill_poly([(14, 4), (22, 12), (16, 28), (10, 16)], pal["mid"])
    if feat.get("plan") in ("serpentine", "aquatic"):
        p.fill_ellipse(8, 8, 24, 26, pal["mid"])
    if feat.get("plan") == "tentacled":
        p.fill_poly([(8, 6), (24, 10), (16, 28), (6, 16)], pal["mid"])
    if child:
        p.fill_poly([(14, 8), (20, 14), (16, 24), (12, 16)], pal["mid"])
    p.light(pal)
    p.outline(pal["outline"])


def _draw_avian_head(p: Pix, pal: Dict[str, RGB], feat: Dict[str, Any], child: bool) -> None:
    pad = 6 if child else 4
    p.fill_ellipse(pad + 3, pad, 26 - pad, 20, pal["mid"])
    p.fill_poly([(20, 12), (30, 16), (20, 18)], pal["buckle"])
    _eyes(p, 14, 11, pal)
    if feat.get("has_horns"):
        p.fill_poly([(12, 4), (14, 8), (10, 8)], pal["bone"])
    p.light(pal)
    p.outline(pal["outline"])


def _draw_avian_body(p: Pix, pal: Dict[str, RGB], feat: Dict[str, Any], child: bool) -> None:
    p.fill_ellipse(8, 8, 23, 26, pal["mid"])
    if feat.get("has_wings"):
        p.fill_poly([(2, 10), (10, 14), (4, 24)], pal["hi"])
        p.fill_poly([(29, 10), (21, 14), (27, 24)], pal["hi"])
    p.light(pal)
    p.outline(pal["outline"])


def _draw_fish_head(p: Pix, pal: Dict[str, RGB], child: bool) -> None:
    pad = 5 if child else 3
    p.fill_ellipse(pad, 8, 24, 24, pal["mid"])
    p.fill_poly([(22, 14), (30, 16), (22, 18)], pal["mid"])
    p.set(12, 14, pal["sclera"])
    p.set(13, 14, pal["iris"])
    p.light(pal)
    p.outline(pal["outline"])


def _draw_fish_body(p: Pix, pal: Dict[str, RGB], child: bool) -> None:
    p.fill_ellipse(4, 8, 26, 24, pal["mid"])
    p.fill_poly([(14, 4), (18, 10), (10, 10)], pal["hi"])
    p.light(pal)
    p.outline(pal["outline"])


def _draw_spider_head(p: Pix, pal: Dict[str, RGB], feat: Dict[str, Any], child: bool) -> None:
    p.fill_ellipse(8, 8, 23, 24, pal["chitin"])
    for ox, oy in ((12, 12), (19, 12), (10, 16), (21, 16), (14, 14), (17, 14)):
        p.set(ox, oy, pal["hi"])
    if feat.get("has_antennae"):
        p.line(12, 8, 8, 2, pal["outline"])
        p.line(19, 8, 23, 2, pal["outline"])
    p.light(pal)
    p.outline(pal["outline"])


def _draw_spider_body(p: Pix, pal: Dict[str, RGB], child: bool) -> None:
    p.fill_ellipse(6, 6, 25, 26, pal["chitin"])
    p.fill_ellipse(10, 8, 21, 16, pal["shadow"])
    p.light(pal)
    p.outline(pal["outline"])


def _draw_blob(p: Pix, pal: Dict[str, RGB], child: bool) -> None:
    pad = 8 if child else 4
    p.fill_ellipse(pad, pad, 31 - pad, 31 - pad, pal["mid"])
    p.fill_ellipse(pad + 4, pad + 3, 22, 16, pal["hi"])
    p.set(12, 14, pal["eye"])
    p.set(18, 14, pal["eye"])
    p.light(pal)
    p.outline(pal["outline"])


def _draw_tentacle_arm(p: Pix, pal: Dict[str, RGB], right: bool) -> None:
    ox = 2 if right else -2
    p.fill_poly([(16 + ox, 4), (22 + ox * 3, 16), (14, 28), (10, 12)], pal["mid"])
    p.light(pal)
    p.outline(pal["outline"])


def _draw_fin(p: Pix, pal: Dict[str, RGB], right: bool) -> None:
    if right:
        p.fill_poly([(10, 10), (26, 8), (22, 24), (12, 22)], pal["mid"])
    else:
        p.fill_poly([(22, 10), (6, 8), (10, 24), (20, 22)], pal["mid"])
    p.light(pal)
    p.outline(pal["outline"])


def _draw_shell_body(p: Pix, pal: Dict[str, RGB], child: bool) -> None:
    p.fill_ellipse(5, 8, 26, 26, pal["bone"])
    p.fill_ellipse(8, 10, 23, 22, pal["cloth"])
    p.light(pal)
    p.outline(pal["outline"])


def _draw_centaur_body(p: Pix, pal: Dict[str, RGB], feat: Dict[str, Any], child: bool) -> None:
    p.fill_poly([(10, 4), (21, 4), (23, 14), (8, 14)], pal["cloth"])
    p.fill_ellipse(4, 12, 28, 26, pal["mid"])
    if feat.get("has_tail"):
        p.fill_poly([(24, 18), (30, 14), (28, 24)], pal["mid"])
    p.light(pal)
    p.outline(pal["outline"])


def _draw_humanoid_head_horned(p: Pix, pal: Dict[str, RGB], feat: Dict[str, Any], child: bool) -> None:
    _draw_humanoid_head(p, pal, feat, child)
    p.fill_poly([(8, 2), (12, 8), (6, 10)], pal["bone"])
    p.fill_poly([(23, 2), (19, 8), (25, 10)], pal["bone"])
    p.outline(pal["outline"])


def _apply_state(p: Pix, state: str, pal: Dict[str, RGB]) -> Pix:
    if state == "list_icon":
        for x in range(p.w):
            p.set(x, 0, (236, 228, 200))
            p.set(x, p.h - 1, (236, 228, 200))
        for y in range(p.h):
            p.set(0, y, (236, 228, 200))
            p.set(p.w - 1, y, (236, 228, 200))
        return p
    if state == "animated":
        shifted = Pix(p.w, p.h)
        for y in range(p.h):
            for x in range(p.w):
                src = p.get(x, y)
                if src[3]:
                    shifted.set(x, y - 1 if y > 0 else y, src[:3], src[3])
        return shifted
    if state == "corpse":
        slumped = Pix(p.w, p.h)
        for y in range(p.h):
            for x in range(p.w):
                src = p.get(x, y)
                if src[3]:
                    nx = x + (y // 8)
                    ny = min(p.h - 1, y + 2)
                    slumped.set(nx, ny, src[:3], src[3])
        return slumped
    return p


def render_part_tile(
    part: str,
    state: str,
    accent: RGB,
    features: Optional[Dict[str, Any]] = None,
    tile: int = TILE,
) -> Any:
    """Return a 32x32 RGBA PIL image for one ANIMAL_PEOPLE layer cell."""
    feat = dict(features or {})
    culture = str(feat.get("culture") or "dwarf_industry")
    if state == "list_icon" and part != "head":
        return Pix(tile, tile).to_image()
    draw_state = "default" if state == "list_icon" else state
    pal = _palette(accent, draw_state, culture)
    p = Pix(tile, tile)
    plan = feat.get("plan") or "humanoid"
    child = draw_state == "child"

    if part == "head":
        if plan == "insectoid":
            _draw_insect_head(p, pal, feat, child)
        elif plan == "arachnid":
            _draw_spider_head(p, pal, feat, child)
        elif plan == "quadruped":
            _draw_quad_head(p, pal, child)
        elif plan == "serpentine":
            _draw_snake_head(p, pal, child)
        elif plan == "avian":
            _draw_avian_head(p, pal, feat, child)
        elif plan == "aquatic":
            _draw_fish_head(p, pal, child)
        elif plan == "amorphous":
            _draw_blob(p, pal, child)
        elif plan == "tentacled":
            _draw_blob(p, pal, child)
        elif plan == "hematophyte":
            _draw_hematophyte_head(p, pal, feat, child)
        elif plan == "hoofed":
            _draw_humanoid_head_horned(p, pal, feat, child)
        elif plan == "shelled":
            _draw_avian_head(p, pal, feat, child)
        else:
            _draw_humanoid_head(p, pal, feat, child)
    elif part == "body":
        if plan == "insectoid":
            _draw_insect_body(p, pal, child)
        elif plan == "arachnid":
            _draw_spider_body(p, pal, child)
        elif plan == "quadruped":
            _draw_quad_body(p, pal, child)
        elif plan == "serpentine":
            _draw_snake_body(p, pal, child)
        elif plan == "avian" or plan == "winged":
            _draw_avian_body(p, pal, feat, child) if plan == "avian" else _draw_humanoid_body(p, pal, feat, child)
        elif plan == "aquatic":
            _draw_fish_body(p, pal, child)
        elif plan == "amorphous":
            _draw_blob(p, pal, child)
        elif plan == "tentacled":
            _draw_blob(p, pal, child)
        elif plan == "hematophyte":
            _draw_hematophyte_body(p, pal, feat, child)
        elif plan == "centaur":
            _draw_centaur_body(p, pal, feat, child)
        elif plan == "shelled":
            _draw_shell_body(p, pal, child)
        else:
            _draw_humanoid_body(p, pal, feat, child)
    elif part in ("RH", "LH"):
        if plan == "hematophyte":
            _draw_hematophyte_vine(p, pal, part == "RH")
        elif plan == "tentacled":
            _draw_tentacle_arm(p, pal, part == "RH")
        elif plan in ("serpentine", "amorphous"):
            pass
        elif plan == "aquatic":
            _draw_fin(p, pal, part == "RH")
        elif plan == "avian" and not feat.get("has_hands"):
            _draw_fin(p, pal, part == "RH")
        elif plan in ("insectoid", "arachnid"):
            _draw_hand(p, pal, part == "RH", child, True)
        else:
            _draw_hand(p, pal, part == "RH", child, False)
    elif part in ("RF", "LF"):
        if plan == "hematophyte":
            _draw_hematophyte_vine(p, pal, part == "RF")
        else:
            _draw_foot(p, pal, part == "RF", child, plan)
    elif part == "tail":
        if plan == "hematophyte":
            _draw_hematophyte_body(p, pal, feat, child)
        else:
            _draw_tail(p, pal, feat, child)

    p = _apply_state(p, state, pal)
    return p.to_image()


def render_sheet(
    accent: RGB,
    features: Optional[Dict[str, Any]] = None,
) -> Any:
    from PIL import Image  # type: ignore

    sheet = Image.new("RGBA", (TILE * COLS, TILE * ROWS), (0, 0, 0, 0))
    for row, state in enumerate(STATES):
        for col, part in enumerate(PARTS):
            tile = render_part_tile(part, state, accent, features)
            sheet.paste(tile, (col * TILE, row * TILE), tile)
    return sheet


def render_assembled_tile(accent: RGB, features: Optional[Dict[str, Any]] = None) -> Any:
    """One compact 32x32 creature (GUI preview), not the ANIMAL_PEOPLE layer cells."""
    feat = dict(features or {})
    pal = _palette(accent, "default", str(feat.get("culture") or "dwarf_industry"))
    p = Pix(32, 32)
    plan = feat.get("plan") or "humanoid"
    if plan == "insectoid":
        p.fill_ellipse(10, 4, 21, 14, pal["chitin"])
        p.fill_ellipse(8, 12, 23, 26, pal["chitin"])
        p.fill_poly([(6, 8), (10, 14), (7, 22)], pal["chitin"])
        p.fill_poly([(25, 8), (21, 14), (24, 22)], pal["chitin"])
        p.set(13, 8, pal["eye"])
        p.set(18, 8, pal["eye"])
        if feat.get("has_antennae"):
            p.line(12, 4, 9, 1, pal["outline"])
            p.line(19, 4, 22, 1, pal["outline"])
    elif plan == "arachnid":
        p.fill_ellipse(8, 6, 23, 18, pal["chitin"])
        p.fill_ellipse(7, 16, 24, 28, pal["chitin"])
        p.fill_poly([(4, 10), (8, 16), (3, 22)], pal["chitin"])
        p.fill_poly([(27, 10), (23, 16), (28, 22)], pal["chitin"])
        p.set(12, 10, pal["hi"])
        p.set(19, 10, pal["hi"])
    elif plan == "quadruped":
        p.fill_ellipse(4, 10, 26, 22, pal["mid"])
        p.fill_ellipse(20, 8, 30, 18, pal["mid"])
        p.fill_rect(6, 20, 9, 28, pal["shadow"])
        p.fill_rect(12, 20, 15, 28, pal["shadow"])
        p.fill_rect(18, 20, 21, 28, pal["shadow"])
        p.fill_rect(23, 20, 26, 28, pal["shadow"])
        p.set(24, 12, pal["eye"])
        if feat.get("has_tail"):
            p.fill_poly([(4, 14), (1, 10), (5, 18)], pal["mid"])
    elif plan == "serpentine":
        p.fill_ellipse(10, 2, 22, 12, pal["mid"])
        p.fill_ellipse(8, 10, 20, 20, pal["mid"])
        p.fill_ellipse(12, 18, 24, 28, pal["shadow"])
        p.set(14, 6, pal["sclera"])
        p.set(18, 6, pal["sclera"])
    elif plan == "avian":
        p.fill_ellipse(10, 2, 21, 14, pal["mid"])
        p.fill_poly([(19, 8), (28, 12), (19, 14)], pal["buckle"])
        p.fill_ellipse(8, 12, 23, 26, pal["mid"])
        p.fill_poly([(2, 10), (10, 14), (4, 22)], pal["hi"])
        p.fill_poly([(29, 10), (21, 14), (27, 22)], pal["hi"])
        p.set(13, 7, pal["iris"])
        p.set(16, 7, pal["iris"])
        if feat.get("has_hands"):
            p.fill_ellipse(4, 14, 9, 20, pal["mid"])
            p.fill_ellipse(22, 14, 27, 20, pal["mid"])
    elif plan == "aquatic":
        p.fill_ellipse(4, 10, 24, 24, pal["mid"])
        p.fill_poly([(22, 14), (30, 10), (30, 22)], pal["mid"])
        p.fill_poly([(12, 6), (16, 12), (8, 12)], pal["hi"])
        p.set(10, 14, pal["iris"])
    elif plan == "amorphous":
        p.fill_ellipse(4, 6, 27, 28, pal["mid"])
        p.fill_ellipse(8, 8, 20, 16, pal["hi"])
        p.set(12, 14, pal["eye"])
        p.set(18, 14, pal["eye"])
    elif plan == "tentacled":
        p.fill_ellipse(8, 4, 23, 18, pal["mid"])
        p.fill_poly([(6, 16), (4, 28), (10, 20)], pal["mid"])
        p.fill_poly([(14, 18), (12, 30), (18, 20)], pal["mid"])
        p.fill_poly([(22, 16), (26, 28), (20, 20)], pal["mid"])
        p.set(13, 10, pal["iris"])
        p.set(18, 10, pal["iris"])
    elif plan == "hematophyte":
        # Serpentine trunk + radiating thorned vines + maw/fronds
        p.fill_ellipse(10, 6, 22, 28, pal["mid"])
        p.fill_poly([(12, 2), (16, 8), (8, 8)], pal["cloth"])
        p.fill_poly([(20, 2), (24, 8), (16, 8)], pal["cloth"])
        p.fill_poly([(2, 10), (10, 14), (4, 22)], pal["mid"])
        p.fill_poly([(30, 10), (22, 14), (28, 22)], pal["mid"])
        p.fill_poly([(6, 8), (2, 4), (8, 10)], pal["bone"])
        p.fill_poly([(26, 8), (30, 4), (24, 10)], pal["bone"])
        p.fill_poly([(12, 10), (20, 10), (18, 16), (14, 16)], pal["shadow"])
        p.fill_poly([(20, 12), (28, 10), (26, 14)], pal["bone"])
        p.set(13, 8, pal["iris"])
        p.set(17, 8, pal["iris"])
        p.fill_ellipse(8, 26, 14, 30, pal["shadow"])
        p.fill_ellipse(18, 26, 24, 30, pal["shadow"])
    elif plan == "shelled":
        p.fill_ellipse(6, 8, 25, 26, pal["bone"])
        p.fill_ellipse(18, 4, 28, 14, pal["mid"])
        p.set(22, 8, pal["iris"])
    elif plan == "centaur":
        p.fill_ellipse(10, 2, 20, 12, pal["mid"])
        p.fill_poly([(11, 10), (20, 10), (21, 16), (10, 16)], pal["cloth"])
        p.fill_ellipse(4, 14, 28, 24, pal["mid"])
        p.fill_rect(6, 22, 9, 30, pal["shadow"])
        p.fill_rect(12, 22, 15, 30, pal["shadow"])
        p.fill_rect(18, 22, 21, 30, pal["shadow"])
        p.fill_rect(23, 22, 26, 30, pal["shadow"])
        p.set(13, 6, pal["iris"])
        p.set(17, 6, pal["iris"])
    else:
        p.fill_poly([(10, 12), (21, 12), (23, 26), (8, 26)], pal["cloth"])
        p.fill_rect(11, 10, 20, 14, pal["mid"])
        p.fill_ellipse(9, 2, 22, 16, pal["mid"])
        p.fill_ellipse(10, 1, 21, 8, pal["hair"])
        if feat.get("beard"):
            p.fill_ellipse(11, 11, 20, 18, pal["hair"])
        if plan == "hoofed":
            p.fill_poly([(8, 1), (11, 7), (6, 8)], pal["bone"])
            p.fill_poly([(23, 1), (20, 7), (25, 8)], pal["bone"])
        p.fill_rect(8, 24, 13, 30, pal["cloth"])
        p.fill_rect(18, 24, 23, 30, pal["cloth"])
        p.fill_ellipse(4, 14, 10, 22, pal["mid"])
        p.fill_ellipse(21, 14, 27, 22, pal["mid"])
        p.set(13, 8, pal["sclera"])
        p.set(14, 8, pal["iris"])
        p.set(17, 8, pal["sclera"])
        p.set(18, 8, pal["iris"])
        if feat.get("has_wings"):
            p.fill_poly([(2, 10), (9, 14), (3, 22)], pal["hi"])
            p.fill_poly([(29, 10), (22, 14), (28, 22)], pal["hi"])
        if feat.get("has_tail"):
            p.fill_poly([(20, 22), (28, 18), (24, 28)], pal["mid"])
    p.light(pal)
    p.outline(pal["outline"])
    return p.to_image()


def compose_preview(
    accent: RGB,
    features: Optional[Dict[str, Any]] = None,
    *,
    size: int = 96,
) -> Any:
    from PIL import Image  # type: ignore

    tile = render_assembled_tile(accent, features)
    return tile.resize((size, size), Image.Resampling.NEAREST)


def render_portrait(
    accent: RGB,
    features: Optional[Dict[str, Any]] = None,
    *,
    size: int = 96,
) -> Any:
    from PIL import Image  # type: ignore

    feat = dict(features or {})
    pal = _palette(accent, "default", str(feat.get("culture") or "dwarf_industry"))
    frame = Pix(size, size)
    stone = (92, 86, 74)
    stone_d = (58, 52, 44)
    stone_h = (140, 132, 112)
    frame.fill_rect(0, 0, size - 1, size - 1, stone_d)
    frame.fill_rect(4, 4, size - 5, size - 5, stone)
    frame.fill_rect(8, 8, size - 9, size - 9, (28, 26, 24))
    for i in range(0, size, 6):
        frame.set(i, 2, stone_h)
        frame.set(2, i, stone_h)
    head = render_part_tile("head", "default", accent, feat)
    body = render_part_tile("body", "default", accent, feat)
    head_big = head.resize((64, 64), Image.Resampling.NEAREST)
    body_big = body.resize((56, 56), Image.Resampling.NEAREST)
    im = frame.to_image()
    im.paste(body_big, (20, 48), body_big)
    im.paste(head_big, (16, 10), head_big)
    # vignette corners stay stone
    return im
