#!/usr/bin/env python3
"""SpritesheetAssembler — Python port of Magi-Tech ImageGenerator packing.

The C++ SpritesheetAssembler listed in GeneratorAgent/CMakeLists.txt was never
implemented (ImageGenerator.cpp still has TODOs). This is the working library:

  Layout.HORIZONTAL  animation strips (Starbound default)
  Layout.GRID        equal tiles in row-major order
  Layout.CUSTOM      rectpack bin packing for mixed sizes (AtlasAssetFactory)

Writes Starbound .frames JSON (frameGrid + aliases).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

from PIL import Image

try:
    import rectpack
except ImportError:  # pragma: no cover
    rectpack = None

Vec2 = Tuple[int, int]
FrameName = Optional[str]


class Layout(str, Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    GRID = "grid"
    CUSTOM = "custom"


@dataclass
class PackedSheet:
    image: Image.Image
    tile: Vec2
    dimensions: Vec2  # columns, rows
    names: List[List[FrameName]]
    aliases: Dict[str, object]
    rects: List[Dict] = field(default_factory=list)

    def save_png(self, dest: Union[str, Path]) -> Path:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        self.image.save(dest, "PNG")
        return dest

    def frames_dict(self) -> Dict:
        return {
            "frameGrid": {
                "size": [self.tile[0], self.tile[1]],
                "dimensions": [self.dimensions[0], self.dimensions[1]],
                "names": self.names,
            },
            "aliases": self.aliases,
        }

    def save_frames(self, dest: Union[str, Path]) -> Path:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(self.frames_dict(), indent=2) + "\n", encoding="utf-8")
        return dest


def _next_power_of_two(n: int) -> int:
    if n <= 1:
        return 1
    return 1 << (n - 1).bit_length()


def _normalize_frames(frames: Sequence[Image.Image], tile: Optional[Vec2] = None) -> Tuple[List[Image.Image], Vec2]:
    if not frames:
        raise ValueError("no frames to pack")
    tw, th = tile or frames[0].size
    out = []
    for fr in frames:
        img = fr.convert("RGBA")
        if img.size != (tw, th):
            canvas = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
            x = max(0, (tw - img.width) // 2)
            y = max(0, (th - img.height) // 2)
            canvas.paste(img, (x, y), img)
            img = canvas
        out.append(img)
    return out, (tw, th)


class SpritesheetAssembler:
    """Pack equal-size or mixed-size frames into a Starbound spritesheet."""

    def __init__(
        self,
        padding: int = 0,
        power_of_two: bool = False,
        background: Tuple[int, int, int, int] = (0, 0, 0, 0),
    ):
        self.padding = max(0, int(padding))
        self.power_of_two = power_of_two
        self.background = background

    def assemble(
        self,
        frames: Sequence[Image.Image],
        *,
        layout: Layout = Layout.HORIZONTAL,
        tile: Optional[Vec2] = None,
        columns: Optional[int] = None,
        names: Optional[Sequence[str]] = None,
        alias: str = "default",
        extra_aliases: Optional[Dict[str, object]] = None,
    ) -> PackedSheet:
        layout = Layout(layout)
        if layout == Layout.CUSTOM:
            return self._pack_custom(frames, names=names, alias=alias, extra_aliases=extra_aliases)
        imgs, (tw, th) = _normalize_frames(frames, tile)
        n = len(imgs)
        labels = list(names) if names is not None else [str(i) for i in range(n)]
        if len(labels) != n:
            raise ValueError("names length must match frames")

        if layout == Layout.HORIZONTAL:
            cols, rows = n, 1
        elif layout == Layout.VERTICAL:
            cols, rows = 1, n
        else:
            cols = columns or max(1, math.ceil(math.sqrt(n)))
            rows = max(1, math.ceil(n / cols))

        pad = self.padding
        width = cols * tw + max(0, cols - 1) * pad
        height = rows * th + max(0, rows - 1) * pad
        if self.power_of_two:
            width = _next_power_of_two(width)
            height = _next_power_of_two(height)

        sheet = Image.new("RGBA", (width, height), self.background)
        grid: List[List[FrameName]] = [[None] * cols for _ in range(rows)]
        rects = []
        for i, img in enumerate(imgs):
            c, r = (0, i) if layout == Layout.VERTICAL else (i % cols, i // cols)
            x = c * (tw + pad)
            y = r * (th + pad)
            sheet.paste(img, (x, y), img)
            grid[r][c] = labels[i]
            rects.append({"name": labels[i], "x": x, "y": y, "width": tw, "height": th})

        aliases: Dict[str, object] = {"default": labels[0], alias: labels}
        if extra_aliases:
            aliases.update(extra_aliases)
        return PackedSheet(sheet, (tw, th), (cols, rows), grid, aliases, rects)

    def assemble_named_rows(
        self,
        cycles: Dict[str, Sequence[Image.Image]],
        prefixes: Optional[Dict[str, str]] = None,
    ) -> PackedSheet:
        """One row per cycle, vanilla `prefix.N` names (wand/mech/object sheets)."""
        if not cycles:
            raise ValueError("no cycles")
        prefixes = prefixes or {}
        sample = next(iter(cycles.values()))[0]
        tw, th = sample.size
        cols = max(len(fr) for fr in cycles.values())
        rows = len(cycles)
        pad = self.padding
        width = cols * tw + max(0, cols - 1) * pad
        height = rows * th + max(0, rows - 1) * pad
        if self.power_of_two:
            width = _next_power_of_two(width)
            height = _next_power_of_two(height)
        sheet = Image.new("RGBA", (width, height), self.background)
        names: List[List[FrameName]] = []
        aliases: Dict[str, object] = {}
        rects = []
        for r, (cname, frames) in enumerate(cycles.items()):
            prefix = prefixes.get(cname, cname)
            row: List[FrameName] = []
            frame_names = []
            for c, fr in enumerate(frames):
                img = fr.convert("RGBA")
                if img.size != (tw, th):
                    canvas = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
                    canvas.paste(img, (0, 0), img)
                    img = canvas
                x = c * (tw + pad)
                y = r * (th + pad)
                sheet.paste(img, (x, y), img)
                label = f"{prefix}.{c + 1}"
                row.append(label)
                frame_names.append(label)
                rects.append({"name": label, "x": x, "y": y, "width": tw, "height": th})
            while len(row) < cols:
                row.append(None)
            names.append(row)
            aliases[cname] = frame_names
            aliases[prefix] = frame_names
        aliases["default"] = (
            aliases.get("idle") or aliases.get("default") or next(iter(aliases.values()))
        )
        return PackedSheet(sheet, (tw, th), (cols, rows), names, aliases, rects)

    def _pack_custom(
        self,
        frames: Sequence[Image.Image],
        names: Optional[Sequence[str]] = None,
        alias: str = "default",
        extra_aliases: Optional[Dict[str, object]] = None,
    ) -> PackedSheet:
        imgs = [fr.convert("RGBA") for fr in frames]
        labels = list(names) if names is not None else [str(i) for i in range(len(imgs))]
        pad = self.padding
        sizes = [(im.width + pad, im.height + pad) for im in imgs]

        if rectpack is None:
            # Fallback: horizontal strip of heterogeneous widths
            width = sum(s[0] for s in sizes)
            height = max(s[1] for s in sizes)
            placements = []
            x = 0
            for i, (w, h) in enumerate(sizes):
                placements.append((i, x, 0, w, h))
                x += w
        else:
            packer = rectpack.newPacker(rotation=False)
            max_side = max(max(w, h) for w, h in sizes)
            bin_w = _next_power_of_two(max(max_side, int(math.sqrt(sum(w * h for w, h in sizes)))))
            bin_h = bin_w
            for attempt in range(8):
                packer = rectpack.newPacker(rotation=False)
                packer.add_bin(bin_w, bin_h)
                for i, (w, h) in enumerate(sizes):
                    packer.add_rect(w, h, rid=i)
                packer.pack()
                packed_ids = {rect[5] for rect in packer.rect_list()}
                if len(packed_ids) == len(imgs):
                    break
                bin_w *= 2
                bin_h *= 2
            placements = []
            for _bin, x, y, w, h, rid in packer.rect_list():
                placements.append((rid, x, y, w, h))
            if not placements:
                raise RuntimeError("rectpack failed to place frames")
            width = max(x + w for _, x, y, w, h in placements)
            height = max(y + h for _, x, y, w, h in placements)

        if self.power_of_two:
            width = _next_power_of_two(width)
            height = _next_power_of_two(height)
        sheet = Image.new("RGBA", (width, height), self.background)
        rects = []
        max_tw = max(im.width for im in imgs)
        max_th = max(im.height for im in imgs)
        for rid, x, y, w, h in sorted(placements, key=lambda t: t[0]):
            img = imgs[rid]
            sheet.paste(img, (x, y), img)
            rects.append({"name": labels[rid], "x": x, "y": y, "width": img.width, "height": img.height})
        aliases: Dict[str, object] = {"default": labels[0], alias: labels}
        if extra_aliases:
            aliases.update(extra_aliases)
        # Mixed sizes: frameGrid uses max tile; rects hold true bounds
        grid = [[labels[i] if i < len(labels) else None] for i in range(len(labels))]
        packed = PackedSheet(sheet, (max_tw, max_th), (1, len(labels)), grid, aliases, rects)
        return packed


def pack_strip(
    frames: Sequence[Image.Image],
    dest: Union[str, Path],
    *,
    names: Optional[Sequence[str]] = None,
    alias: str = "default",
    extra_aliases: Optional[Dict[str, object]] = None,
    frames_path: Optional[Union[str, Path]] = None,
    padding: int = 0,
) -> PackedSheet:
    packed = SpritesheetAssembler(padding=padding).assemble(
        frames, layout=Layout.HORIZONTAL, names=names, alias=alias, extra_aliases=extra_aliases
    )
    packed.save_png(dest)
    if frames_path:
        packed.save_frames(frames_path)
    return packed


def pack_grid(
    frames: Sequence[Image.Image],
    dest: Union[str, Path],
    *,
    columns: Optional[int] = None,
    names: Optional[Sequence[str]] = None,
    frames_path: Optional[Union[str, Path]] = None,
    padding: int = 0,
) -> PackedSheet:
    packed = SpritesheetAssembler(padding=padding).assemble(
        frames, layout=Layout.GRID, columns=columns, names=names
    )
    packed.save_png(dest)
    if frames_path:
        packed.save_frames(frames_path)
    return packed


def pack_named_rows(
    cycles: Dict[str, Sequence[Image.Image]],
    dest_png: Union[str, Path],
    dest_frames: Union[str, Path],
    prefixes: Optional[Dict[str, str]] = None,
    padding: int = 0,
) -> PackedSheet:
    packed = SpritesheetAssembler(padding=padding).assemble_named_rows(cycles, prefixes)
    packed.save_png(dest_png)
    packed.save_frames(dest_frames)
    return packed


def write_starbound_frames(
    path: Union[str, Path],
    tw: int,
    th: int,
    names: Sequence[str],
    *,
    alias: str = "default",
    extra_aliases: Optional[Dict[str, object]] = None,
) -> None:
    labels = list(names)
    aliases: Dict[str, object] = {"default": labels[0], alias: labels}
    if extra_aliases:
        aliases.update(extra_aliases)
    Path(path).write_text(json.dumps({
        "frameGrid": {
            "size": [tw, th],
            "dimensions": [len(labels), 1],
            "names": [labels],
        },
        "aliases": aliases,
    }, indent=2) + "\n", encoding="utf-8")
