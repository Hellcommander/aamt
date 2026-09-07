#!/usr/bin/env python3
"""Mech hitbox generator — full implementation of the C++ stub.

C++ MagiTech::Mech::HitboxGenerator (cpp_backend/core/modules/mech) logs
"not fully implemented - requires image loading library". This library loads
PNG sheets with Pillow and traces opaque-pixel bounds per frame.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

from PIL import Image

Vec2 = Tuple[float, float]


@dataclass
class Hitbox:
    vertices: List[Vec2]
    center: Vec2
    min: Vec2
    max: Vec2
    area: float
    is_valid: bool = False
    pixel_min: Tuple[int, int] = (0, 0)
    pixel_max: Tuple[int, int] = (0, 0)

    def collision_box(self) -> List[Vec2]:
        if not self.is_valid:
            return [(-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0)]
        return [
            (self.min[0], self.min[1]),
            (self.max[0], self.min[1]),
            (self.max[0], self.max[1]),
            (self.min[0], self.max[1]),
        ]


@dataclass
class FrameHitbox:
    frame_index: int
    hitbox: Hitbox
    name: str = ""


@dataclass
class SpritesheetAnalysis:
    spritesheet_path: str
    frame_width: int
    frame_height: int
    frames_per_row: int
    frames_per_column: int
    total_frames: int
    frame_hitboxes: List[FrameHitbox] = field(default_factory=list)
    average_hitbox: Optional[Hitbox] = None
    max_hitbox: Optional[Hitbox] = None

    def to_dict(self) -> Dict:
        def hb(h: Optional[Hitbox]):
            if h is None:
                return None
            d = asdict(h)
            d["collisionBox"] = h.collision_box()
            return d

        return {
            "spritesheetPath": self.spritesheet_path,
            "frameWidth": self.frame_width,
            "frameHeight": self.frame_height,
            "framesPerRow": self.frames_per_row,
            "framesPerColumn": self.frames_per_column,
            "totalFrames": self.total_frames,
            "averageHitbox": hb(self.average_hitbox),
            "maxHitbox": hb(self.max_hitbox),
            "frames": [
                {
                    "frameIndex": fh.frame_index,
                    "name": fh.name,
                    "hitbox": hb(fh.hitbox),
                    "collisionBox": fh.hitbox.collision_box(),
                }
                for fh in self.frame_hitboxes
            ],
        }


def _detect_hitbox(
    pixels,
    img_w: int,
    img_h: int,
    offset_x: int,
    offset_y: int,
    frame_w: int,
    frame_h: int,
    alpha_threshold: int,
) -> Hitbox:
    min_x, min_y = frame_w, frame_h
    max_x, max_y = -1, -1
    found = False
    for y in range(frame_h):
        py = offset_y + y
        if py >= img_h:
            continue
        for x in range(frame_w):
            px = offset_x + x
            if px >= img_w:
                continue
            a = pixels[px, py][3] if len(pixels[px, py]) > 3 else 255
            if a >= alpha_threshold:
                found = True
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
    empty = Hitbox([], (0.0, 0.0), (0.0, 0.0), (0.0, 0.0), 0.0, False)
    if not found:
        return empty
    cx = (min_x + max_x) / 2.0 - frame_w / 2.0
    cy = (min_y + max_y) / 2.0 - frame_h / 2.0
    mn = (min_x - frame_w / 2.0, min_y - frame_h / 2.0)
    mx = (max_x - frame_w / 2.0, max_y - frame_h / 2.0)
    verts = [(mn[0], mn[1]), (mx[0], mn[1]), (mx[0], mx[1]), (mn[0], mx[1])]
    return Hitbox(
        vertices=verts,
        center=(cx, cy),
        min=mn,
        max=mx,
        area=float((max_x - min_x) * (max_y - min_y)),
        is_valid=True,
        pixel_min=(min_x, min_y),
        pixel_max=(max_x, max_y),
    )


class HitboxGenerator:
    def analyze_spritesheet(
        self,
        spritesheet_path: Union[str, Path],
        frame_width: int,
        frame_height: int,
        alpha_threshold: int = 128,
        frame_names: Optional[Sequence[str]] = None,
        max_frames: Optional[int] = None,
    ) -> SpritesheetAnalysis:
        path = Path(spritesheet_path)
        with Image.open(path) as im:
            img = im.convert("RGBA")
            w, h = img.size
            pixels = img.load()
            cols = max(1, w // frame_width)
            rows = max(1, h // frame_height)
            total = cols * rows
            if max_frames is not None:
                total = min(total, max_frames)
            analysis = SpritesheetAnalysis(
                str(path), frame_width, frame_height, cols, rows, total
            )
            union_min = [frame_width, frame_height]
            union_max = [0, 0]
            sum_min = [0.0, 0.0]
            sum_max = [0.0, 0.0]
            valid_n = 0
            for i in range(total):
                c = i % cols
                r = i // cols
                hb = _detect_hitbox(
                    pixels, w, h, c * frame_width, r * frame_height,
                    frame_width, frame_height, alpha_threshold,
                )
                name = frame_names[i] if frame_names and i < len(frame_names) else str(i)
                analysis.frame_hitboxes.append(FrameHitbox(i, hb, name))
                if hb.is_valid:
                    valid_n += 1
                    union_min[0] = min(union_min[0], hb.pixel_min[0])
                    union_min[1] = min(union_min[1], hb.pixel_min[1])
                    union_max[0] = max(union_max[0], hb.pixel_max[0])
                    union_max[1] = max(union_max[1], hb.pixel_max[1])
                    sum_min[0] += hb.min[0]
                    sum_min[1] += hb.min[1]
                    sum_max[0] += hb.max[0]
                    sum_max[1] += hb.max[1]
            if valid_n:
                avg_min = (sum_min[0] / valid_n, sum_min[1] / valid_n)
                avg_max = (sum_max[0] / valid_n, sum_max[1] / valid_n)
                analysis.average_hitbox = Hitbox(
                    vertices=[
                        (avg_min[0], avg_min[1]),
                        (avg_max[0], avg_min[1]),
                        (avg_max[0], avg_max[1]),
                        (avg_min[0], avg_max[1]),
                    ],
                    center=((avg_min[0] + avg_max[0]) / 2, (avg_min[1] + avg_max[1]) / 2),
                    min=avg_min,
                    max=avg_max,
                    area=abs((avg_max[0] - avg_min[0]) * (avg_max[1] - avg_min[1])),
                    is_valid=True,
                )
                # max = union of opaque pixels, centered like C++ detectHitbox
                mn = (union_min[0] - frame_width / 2.0, union_min[1] - frame_height / 2.0)
                mx = (union_max[0] - frame_width / 2.0, union_max[1] - frame_height / 2.0)
                analysis.max_hitbox = Hitbox(
                    vertices=[(mn[0], mn[1]), (mx[0], mn[1]), (mx[0], mx[1]), (mn[0], mx[1])],
                    center=((mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2),
                    min=mn,
                    max=mx,
                    area=float((union_max[0] - union_min[0]) * (union_max[1] - union_min[1])),
                    is_valid=True,
                    pixel_min=tuple(union_min),
                    pixel_max=tuple(union_max),
                )
            return analysis

    def generate_collision_box_from_spritesheet(
        self,
        spritesheet_path: Union[str, Path],
        frame_width: int,
        frame_height: int,
        use_max_hitbox: bool = True,
        alpha_threshold: int = 128,
    ) -> List[Vec2]:
        analysis = self.analyze_spritesheet(
            spritesheet_path, frame_width, frame_height, alpha_threshold
        )
        hb = analysis.max_hitbox if use_max_hitbox else analysis.average_hitbox
        if hb is None:
            return Hitbox([], (0, 0), (0, 0), (0, 0), 0, False).collision_box()
        return hb.collision_box()


def analyze_spritesheet(*args, **kwargs) -> SpritesheetAnalysis:
    return HitboxGenerator().analyze_spritesheet(*args, **kwargs)


def write_hitbox_json(analysis: SpritesheetAnalysis, dest: Union[str, Path]) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(analysis.to_dict(), indent=2) + "\n", encoding="utf-8")
    return dest
