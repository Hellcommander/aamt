"""Decode Diablo II legacy monster sprites (DCC files) into images.

A sprite monster is a set of DCC files, one per body layer and animation mode
(`global/monsters/<token>/<layer>/<token><layer>lit<mode>hth.dcc`), each holding
every frame for every view direction, as indices into the act palette
(`global/palette/act1/pal.dat`, 256 x blue, green, red).

    dcc = LegacySprite.Dcc(data)                 # directions x frames
    frame = dcc.frames[direction][index]         # Frame: box (xmin, ymin, xmax, ymax), pixels (H x W palette indices)
    image = LegacySprite.to_image(frame, palette, box=dcc.box)   # PIL RGBA, index 0 transparent

Command line:
    python LegacySprite.py sheet  --game <D2R> <token> <mode> <out.png> [--layer tr] [--scale 4]
        every direction (rows) and frame (columns) of one animation
    python LegacySprite.py views  --game <D2R> <token> <mode> <out folder> [--frame 0] [--scale 8]
        one PNG per view direction, in turn-table order, for image-to-3D tools

The view directions of an 8-direction file are stored in the order
SW, NW, NE, SE, S, W, N, E (the screen direction the monster faces, seen on the
Quill Bear / Spike Giant sprites); `VIEW_ORDER` lists them going round from S.

Written from the published description of the format; no decoder source was
used.
"""
import argparse
import os
import struct
import sys

import numpy as np

WIDTHS = [0, 1, 2, 4, 6, 8, 10, 12, 14, 16, 20, 24, 26, 28, 30, 32]
# Stored index of each direction when going round the monster: facing S, SW, W, NW, N, NE, E, SE.
VIEW_ORDER = {8: [4, 0, 5, 1, 6, 2, 7, 3], 16: [0, 8, 4, 9, 1, 10, 5, 11, 2, 12, 6, 13, 3, 14, 7, 15], 4: [0, 1, 2, 3], 1: [0]}


class Bits:
    """Reads bits, least significant first, from a byte string starting at a bit position."""

    def __init__(self, data, position=0, size=None):
        self.data, self.position = data, position
        self.end = None if size is None else position + size

    def read(self, count):
        value = 0
        for i in range(count):
            byte = self.data[self.position >> 3]
            value |= ((byte >> (self.position & 7)) & 1) << i
            self.position += 1
        return value

    def signed(self, count):
        value = self.read(count)
        if count and value & (1 << (count - 1)):
            value -= 1 << count
        return value


class Frame:
    __slots__ = ('width', 'height', 'xoffset', 'yoffset', 'bottom_up', 'box', 'pixels', 'optional')


def _cells(start, length):
    """Sizes of the cells a frame (or the direction box) is cut into along one axis, given its offset in the grid."""
    first = 4 - (start % 4)
    if length - first <= 1:
        return [length]
    rest = length - first - 1
    count = 2 + rest // 4
    if rest % 4 == 0:
        count -= 1
    sizes = [first] + [4] * (count - 2)
    sizes.append(length - sum(sizes))
    return sizes


class Dcc:
    def __init__(self, data):
        signature, version, directions, per_direction, tag, total = struct.unpack_from('<BBBIII', data, 0)
        if signature != 0x74:
            raise ValueError('not a DCC file')
        self.directions, self.frames_per_direction = directions, per_direction
        offsets = list(struct.unpack_from(f'<{directions}I', data, 15)) + [len(data)]
        self.frames = []
        self.boxes = []
        for d in range(directions):
            frames, box = self._direction(data, offsets[d], offsets[d + 1])
            self.frames.append(frames)
            self.boxes.append(box)
        self.box = (min(b[0] for b in self.boxes), min(b[1] for b in self.boxes),
                    max(b[2] for b in self.boxes), max(b[3] for b in self.boxes))

    def _direction(self, data, start, end):
        bits = Bits(data, start * 8)
        bits.read(32)                                   # size of the decoded direction
        compression = bits.read(2)
        sizes = [WIDTHS[bits.read(4)] for _ in range(7)]    # variable0, width, height, xoffset, yoffset, optional, coded
        frames = []
        for _ in range(self.frames_per_direction):
            f = Frame()
            bits.read(sizes[0])
            f.width, f.height = bits.read(sizes[1]), bits.read(sizes[2])
            f.xoffset, f.yoffset = bits.signed(sizes[3]), bits.signed(sizes[4])
            f.optional = bits.read(sizes[5])
            bits.read(sizes[6])
            f.bottom_up = bits.read(1)
            xmin = f.xoffset
            if f.bottom_up:
                ymin = f.yoffset
            else:
                ymin = f.yoffset - f.height + 1
            f.box = (xmin, ymin, xmin + f.width - 1, ymin + f.height - 1)
            frames.append(f)
        box = (min(f.box[0] for f in frames), min(f.box[1] for f in frames),
               max(f.box[2] for f in frames), max(f.box[3] for f in frames))
        width, height = box[2] - box[0] + 1, box[3] - box[1] + 1
        optional = sum(f.optional for f in frames)
        if optional:
            bits.position = (bits.position + 7) // 8 * 8 + optional * 8
        equal_size = bits.read(20) if compression & 2 else 0
        mask_size = bits.read(20)
        encoding_size = raw_size = 0
        if compression & 1:
            encoding_size, raw_size = bits.read(20), bits.read(20)
        palette_entries = [i for i in range(256) if bits.read(1)]
        position = bits.position
        equal = Bits(data, position)
        position += equal_size
        mask = Bits(data, position)
        position += mask_size
        encoding = Bits(data, position)
        position += encoding_size
        raw = Bits(data, position)
        position += raw_size
        codes = Bits(data, position)

        # Stage 1: one entry of four colours per changed cell, in frame order.
        grid_w, grid_h = 1 + (width - 1) // 4, 1 + (height - 1) // 4
        current = [None] * (grid_w * grid_h)
        entries = []                                   # [values[4], frame index, cell index in the frame]
        layouts = []
        for index, f in enumerate(frames):
            x0, y0 = f.box[0] - box[0], f.box[1] - box[1]
            columns, rows = _cells(x0, f.width), _cells(y0, f.height)
            layouts.append((x0, y0, columns, rows))
            cell_x, cell_y = x0 // 4, y0 // 4
            for y in range(len(rows)):
                for x in range(len(columns)):
                    slot = cell_x + x + (cell_y + y) * grid_w
                    old = current[slot]
                    if old is not None:
                        if equal_size and equal.read(1):
                            continue
                        pixel_mask = mask.read(4)
                    else:
                        pixel_mask = 15
                    count = bin(pixel_mask).count('1')
                    raw_pixels = bool(count and encoding_size and encoding.read(1))
                    read = []
                    last = 0
                    for _ in range(count):
                        if raw_pixels:
                            value = raw.read(8)
                        else:
                            value = last
                            while True:
                                step = codes.read(4)
                                value += step
                                if step != 15:
                                    break
                        if value == last:
                            break
                        read.append(value)
                        last = value
                    values = [0, 0, 0, 0]
                    k = len(read) - 1
                    for i in range(4):
                        if pixel_mask & (1 << i):
                            if k >= 0:
                                values[i] = read[k]
                                k -= 1
                        elif old is not None:
                            values[i] = old[0][i]
                    entry = [values, index, x + y * len(columns)]
                    entries.append(entry)
                    current[slot] = entry
        for entry in entries:
            entry[0] = [palette_entries[v] if v < len(palette_entries) else 0 for v in entry[0]]

        # Stage 2: draw the frames on one canvas; a cell that did not change is copied from where it last was.
        canvas = np.zeros((height, width), dtype=np.uint8)
        last_cell = [None] * (grid_w * grid_h)
        cursor = 0
        for index, f in enumerate(frames):
            x0, y0, columns, rows = layouts[index]
            before = canvas.copy()
            frame_pixels = np.zeros((f.height, f.width), dtype=np.uint8)
            cy = y0
            for y, h in enumerate(rows):
                cx = x0
                for x, w in enumerate(columns):
                    slot = cx // 4 + (cy // 4) * grid_w
                    cell = x + y * len(columns)
                    entry = entries[cursor] if cursor < len(entries) else None
                    if entry is None or entry[1] != index or entry[2] != cell:
                        previous = last_cell[slot]
                        if previous is not None and previous[2] == w and previous[3] == h:
                            block = before[previous[1]:previous[1] + h, previous[0]:previous[0] + w]
                        else:
                            block = 0
                        canvas[cy:cy + h, cx:cx + w] = block
                    else:
                        values = entry[0]
                        if values[0] == values[1]:
                            canvas[cy:cy + h, cx:cx + w] = values[0]
                        else:
                            width_bits = 1 if values[1] == values[2] else 2
                            for py in range(h):
                                for px in range(w):
                                    canvas[cy + py, cx + px] = values[codes.read(width_bits)]
                        cursor += 1
                    last_cell[slot] = (cx, cy, w, h)
                    cx += w
                cy += h
            f.pixels = canvas[y0:y0 + f.height, x0:x0 + f.width].copy()
        return frames, box


def load_palette(data):
    """pal.dat: 256 x (blue, green, red) -> 256 x 4 RGBA with index 0 transparent."""
    rgb = np.frombuffer(data[:768], dtype=np.uint8).reshape(256, 3)[:, ::-1]
    out = np.concatenate([rgb, np.full((256, 1), 255, dtype=np.uint8)], axis=1)
    out[0, 3] = 0
    return out


def to_image(frame, palette, box=None, scale=1):
    """A frame as a PIL RGBA image; with `box` every frame is placed on the same canvas so they line up."""
    from PIL import Image
    if box is None:
        box = frame.box
    canvas = np.zeros((box[3] - box[1] + 1, box[2] - box[0] + 1), dtype=np.uint8)
    x, y = frame.box[0] - box[0], frame.box[1] - box[1]
    canvas[y:y + frame.height, x:x + frame.width] = frame.pixels
    image = Image.fromarray(palette[canvas], 'RGBA')
    if scale != 1:
        image = image.resize((image.width * scale, image.height * scale), Image.NEAREST)
    return image


def sprite_path(token, layer, mode, weapon='hth'):
    token = token.lower()
    return f'global/monsters/{token}/{layer}/{token}{layer}lit{mode}{weapon}.dcc'


def load(archive, token, mode, layer='tr'):
    data = archive.read(sprite_path(token, layer.lower(), mode.lower()))
    if data is None:
        raise FileNotFoundError(sprite_path(token, layer, mode))
    return Dcc(data), load_palette(archive.read('global/palette/act1/pal.dat'))


def main(argv):
    parser = argparse.ArgumentParser(description='Legacy monster sprites to images.')
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('sheet', 'views'):
        p = sub.add_parser(name)
        p.add_argument('--game', default=os.environ.get('D2R_PATH'))
        p.add_argument('--layer', default='tr')
        p.add_argument('--scale', type=int, default=4 if name == 'sheet' else 8)
        p.add_argument('--frame', type=int, default=0)
        p.add_argument('token')
        p.add_argument('mode')
        p.add_argument('out')
    args = parser.parse_args(argv)
    from PIL import Image
    from d2r_casc import D2RArchive
    with D2RArchive(args.game) as archive:
        dcc, palette = load(archive, args.token, args.mode, args.layer)
    order = VIEW_ORDER.get(dcc.directions, list(range(dcc.directions)))
    if args.command == 'sheet':
        w, h = (dcc.box[2] - dcc.box[0] + 1) * args.scale, (dcc.box[3] - dcc.box[1] + 1) * args.scale
        sheet = Image.new('RGBA', (w * dcc.frames_per_direction, h * dcc.directions), (40, 44, 52, 255))
        for row, d in enumerate(order):
            for column, frame in enumerate(dcc.frames[d]):
                image = to_image(frame, palette, dcc.box, args.scale)
                sheet.paste(image, (column * w, row * h), image)
        sheet.save(args.out)
        print(f'{dcc.directions} directions x {dcc.frames_per_direction} frames, box {dcc.box} -> {args.out}')
    else:
        os.makedirs(args.out, exist_ok=True)
        for turn, d in enumerate(order):
            to_image(dcc.frames[d][args.frame], palette, dcc.box, args.scale).save(os.path.join(args.out, f'view_{turn:02d}.png'))
        print(f'{len(order)} views written to {args.out}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
