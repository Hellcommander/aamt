#!/usr/bin/env python3
"""Soulash 2 animation particle ``flags`` bitmask, by name.

Decoded 2026-11-06 from Soulash 2.exe (0.10.5.x): the F3 animation editor fills a
map ``{key: label}`` with keys 1..23 and each checkbox toggles bit ``key - 1``.
Cross-checked against core_2 particles that still carry the legacy boolean keys
(``elevation_drop`` = bit 15, ``elevation_parable`` = 16, ``orbit_opposite`` = 19,
``on_impact_reverse_path`` = 21) and against an editor save with every box ticked
(``flags`` 8388607 = 2**23 - 1).

Only ``flags`` matters to the engine; the legacy booleans are read for old files.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

# (bit, key, editor label, short note)
FLAGS: Tuple[Tuple[int, str, str, str], ...] = (
    (0, "repeat_every_square", "Repeat every square", "spawn a copy on every tile of the path (lightning)"),
    (1, "linear_progress", "Linear progress", "travel the path tile by tile (rays, bolts)"),
    (2, "spread_random_direction", "Spread in random direction", "scatter outward in random directions"),
    (3, "fade", "Fade while life is ending", "alpha fades out near end of life"),
    (4, "random_color_every_frame", "Random color every frame", "cycle through the color list each frame"),
    (5, "leave_copy_in_path", "Leave copy in path", "trail: leaves a copy on tiles it passed"),
    (6, "break_on_block_light", "Break on block light component", "stops at walls / light blockers"),
    (7, "rotate_toward_target", "Rotate toward target", "glyph faces the travel direction"),
    (8, "between_glyph_and_background", "Between glyph and background", "draw under entity glyphs"),
    (9, "ignore_target_position", "Ignore target position", "plays at origin regardless of target"),
    (10, "move_entity", "Move entity", "carries the caster/entity along (dash, throw)"),
    (11, "filled_explosion", "Filled explosion", "fill the whole explosion_range area"),
    (12, "random_furthest_target", "Random furthest target", "pick a random far tile in range"),
    (13, "orbit_clockwise", "Orbit target clockwise", "circle around the target"),
    (14, "reverse_path", "Reverse path", "travel target -> origin"),
    (15, "elevation_drop", "Elevation drop", "fall from `elevation` to the ground (rain, meteors)"),
    (16, "elevation_parable", "Elevation parable", "arc up and down along the path (lobbed)"),
    (17, "elevation_rise", "Elevation rise", "rise upward over life (dust, smoke)"),
    (18, "height_rise", "Height rise", "grow in `height` over life (waves, pillars)"),
    (19, "orbit_counterclockwise", "Orbit target counterclockwise", "circle the other way"),
    (20, "rotate_around", "Rotate around", "spin around the origin"),
    (21, "reverse_path_of_impact", "Reverse path of impact", "on_impact animation travels back"),
    (22, "area_filled_traverse", "Area filled traverse", "sweep across the whole area"),
)

ALL_BITS = (1 << len(FLAGS)) - 1  # 8388607
BY_KEY: Dict[str, int] = {key: bit for bit, key, _label, _note in FLAGS}
BY_LABEL: Dict[str, int] = {label.lower(): bit for bit, _key, label, _note in FLAGS}
ALIASES: Dict[str, str] = {
    "fade_out": "fade",
    "fade_while_life_is_ending": "fade",
    "repeat": "repeat_every_square",
    "linear": "linear_progress",
    "spread": "spread_random_direction",
    "random_color": "random_color_every_frame",
    "trail": "leave_copy_in_path",
    "break_on_wall": "break_on_block_light",
    "rotate": "rotate_toward_target",
    "under_glyph": "between_glyph_and_background",
    "filled": "filled_explosion",
    "orbit": "orbit_clockwise",
    "orbit_ccw": "orbit_counterclockwise",
    "orbit_opposite": "orbit_counterclockwise",
    "drop": "elevation_drop",
    "parable": "elevation_parable",
    "arc": "elevation_parable",
    "rise": "elevation_rise",
    "elevation_raise": "elevation_rise",
    "height_raise": "height_rise",
    "on_impact_reverse_path": "reverse_path_of_impact",
    "traverse": "area_filled_traverse",
}

# Legacy boolean particle keys the engine still reads (string pool next to the labels).
LEGACY_BOOL_KEYS: Dict[str, int] = {
    "elevation_drop": 15,
    "elevation_parable": 16,
    "elevation_raise": 17,
    "height_raise": 18,
    "orbit_opposite": 19,
    "rotate_around": 20,
    "on_impact_reverse_path": 21,
}

FlagSpec = Union[int, str, Iterable[Union[int, str]], None]


def flag_bit(name: Union[int, str]) -> int:
    """Bit index for a key, alias, editor label, bit number, or power-of-two value."""
    if isinstance(name, int):
        if 0 <= name < len(FLAGS):
            return name
        if name > 0 and name & (name - 1) == 0 and name.bit_length() - 1 < len(FLAGS):
            return name.bit_length() - 1
        raise KeyError(f"Not a particle flag bit: {name}")
    raw = str(name).strip()
    if raw.isdigit():
        return flag_bit(int(raw))
    low = raw.lower()
    if low in BY_LABEL:
        return BY_LABEL[low]
    key = low.replace("-", "_").replace(" ", "_")
    key = ALIASES.get(key, key)
    if key in BY_KEY:
        return BY_KEY[key]
    raise KeyError(f"Unknown particle flag '{name}'. Known: {', '.join(BY_KEY)}")


def _names(spec: FlagSpec) -> List[Union[int, str]]:
    if spec is None:
        return []
    if isinstance(spec, int):
        return [spec]
    if isinstance(spec, str):
        return [p for p in (s.strip() for s in spec.replace(";", ",").replace("|", ",").split(",")) if p]
    out: List[Union[int, str]] = []
    for item in spec:
        out.extend(_names(item))
    return out


def to_value(spec: FlagSpec) -> int:
    """Names / bits -> flags int. A lone integer string >= 23 is taken as a raw value."""
    if isinstance(spec, int) and spec >= len(FLAGS):
        return spec & ALL_BITS
    if isinstance(spec, str) and spec.strip().isdigit() and int(spec.strip()) >= len(FLAGS):
        return int(spec.strip()) & ALL_BITS
    value = 0
    for item in _names(spec):
        value |= 1 << flag_bit(item)
    return value


def decode(value: Optional[int]) -> List[str]:
    v = int(value or 0)
    return [key for bit, key, _l, _n in FLAGS if v & (1 << bit)]


def describe(value: Optional[int], *, labels: bool = False) -> str:
    v = int(value or 0)
    parts = [label if labels else key for bit, key, label, _n in FLAGS if v & (1 << bit)]
    unknown = v & ~ALL_BITS
    if unknown:
        parts.append(f"unknown(0x{unknown:x})")
    return ", ".join(parts) if parts else "(none)"


def legacy_bits(part: Dict) -> int:
    v = 0
    for key, bit in LEGACY_BOOL_KEYS.items():
        if part.get(key) is True:
            v |= 1 << bit
    return v


def apply_flags(
    part: Dict,
    *,
    set_flags: FlagSpec = None,
    clear_flags: FlagSpec = None,
    toggle_flags: FlagSpec = None,
    value: Optional[int] = None,
    drop_legacy: bool = True,
) -> int:
    """Edit one particle dict in place; returns the new flags value.

    Legacy booleans are folded into ``flags`` first, then removed (``drop_legacy``) so
    a cleared bit is not resurrected by a stale ``elevation_drop: true``.
    """
    current = int(part.get("flags") or 0) | legacy_bits(part)
    if value is not None:
        current = to_value(value) if not isinstance(value, int) else value & ALL_BITS
    current |= to_value(set_flags) if set_flags is not None else 0
    current &= ~(to_value(clear_flags) if clear_flags is not None else 0)
    current ^= to_value(toggle_flags) if toggle_flags is not None else 0
    part["flags"] = current
    if drop_legacy:
        for key in LEGACY_BOOL_KEYS:
            part.pop(key, None)
    return current


def select_particles(anim: Dict, which: Union[None, str, int, Sequence[int]] = None) -> List[Tuple[int, Dict]]:
    """1-based particle numbers as shown in the editor ('Particle 1', ...). None/'all' = every particle."""
    parts = [p for p in (anim.get("particles") or []) if isinstance(p, dict)]
    if which in (None, "", "all", "*"):
        return list(enumerate(parts, 1))
    if isinstance(which, int):
        nums = [which]
    elif isinstance(which, str):
        nums = [int(s) for s in which.replace(";", ",").split(",") if s.strip()]
    else:
        nums = [int(n) for n in which]
    out = []
    for n in nums:
        if not 1 <= n <= len(parts):
            raise IndexError(f"Particle {n} out of range (animation has {len(parts)})")
        out.append((n, parts[n - 1]))
    return out


def table_text() -> str:
    rows = [f"{'bit':>3} {'value':>8}  {'key':30s} editor label / note"]
    for bit, key, label, note in FLAGS:
        rows.append(f"{bit:>3} {1 << bit:>8}  {key:30s} {label} — {note}")
    return "\n".join(rows)


def summarize_animation(anim: Dict) -> List[str]:
    lines = []
    for n, part in select_particles(anim):
        v = int(part.get("flags") or 0) | legacy_bits(part)
        lines.append(f"particle {n}: tile {part.get('tile_id')} flags {v} = {describe(v)}")
    return lines
