"""Magi-Tech asset-generation libraries hosted in Transcendence Tools/Starbound.

These used to live inside the OpenStarbound mod (GeneratorAgent, MeshToSprite,
Lua scripts/tools, MechHitboxGenerator). Offline packing and baking belong here;
the mod keeps thin shims for in-game compile/require.
"""

from .spritesheet_assembler import (
    Layout,
    PackedSheet,
    SpritesheetAssembler,
    pack_grid,
    pack_named_rows,
    pack_strip,
    write_starbound_frames,
)
from .hitbox_generator import HitboxGenerator, analyze_spritesheet

__all__ = [
    "Layout",
    "PackedSheet",
    "SpritesheetAssembler",
    "pack_grid",
    "pack_named_rows",
    "pack_strip",
    "write_starbound_frames",
    "HitboxGenerator",
    "analyze_spritesheet",
]
