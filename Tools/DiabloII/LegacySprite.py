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
    python LegacySprite.py dc6test [--game <D2R>] [files]
        self-test of the DC6 reader and writer (Dc6, encode_dc6): random frames, and with --game
        the game's interface pictures decoded and written back

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


# --- writing -------------------------------------------------------------------------------

class BitWriter:
    """Collects bits, least significant first."""

    def __init__(self):
        self.bits = []

    def write(self, value, count):
        value &= (1 << count) - 1 if count else 0
        self.bits.extend((value >> i) & 1 for i in range(count))

    def __len__(self):
        return len(self.bits)

    def extend(self, other):
        self.bits.extend(other.bits)

    def to_bytes(self):
        padded = self.bits + [0] * (-len(self.bits) % 8)
        return np.packbits(np.array(padded, dtype=np.uint8), bitorder='little').tobytes()


def _width_code(values, signed):
    """The smallest field width (as its code in WIDTHS) that holds every value."""
    for code, width in enumerate(WIDTHS):
        if signed:
            fits = all(-(1 << (width - 1)) <= v < (1 << (width - 1)) for v in values) if width else all(v == 0 for v in values)
        else:
            fits = all(0 <= v < (1 << width) for v in values)
        if fits:
            return code
    raise ValueError('a frame value does not fit in 32 bits')


def dc6_size(pixels):
    """Bytes the frame takes in the older DC6 run-length coding; DCC headers carry that number."""
    total = 0
    for row in pixels:
        solid = np.flatnonzero(row)
        if len(solid):
            edges = np.flatnonzero(np.diff(np.concatenate([[0], (row != 0).astype(np.int8), [0]])))
            position = 0
            for start, end in zip(edges[::2], edges[1::2]):
                gap = start - position
                total += -(-gap // 127) if gap else 0
                run = end - start
                total += run + -(-run // 127)
                position = end
        total += 1                                   # end of line
    return total


def limit_cell_colours(pixels, palette, columns=None, rows=None):
    """Changes pixels so that no cell has more than four different values, transparent included:
    all a DCC cell can hold. The most used values of a cell stay; the others turn into the
    nearest of them by colour. columns / rows: the cell sizes along each axis (default: 4 x 4
    cells counted from the top left). Returns a new array."""
    out = pixels.copy()
    rgb = np.asarray(palette)[:, :3].astype(np.int32)
    xs = np.concatenate([[0], np.cumsum(columns)]) if columns is not None else np.arange(0, out.shape[1] + 4, 4)
    ys = np.concatenate([[0], np.cumsum(rows)]) if rows is not None else np.arange(0, out.shape[0] + 4, 4)
    for y0, y1 in zip(ys[:-1], ys[1:]):
        for x0, x1 in zip(xs[:-1], xs[1:]):
            cell = out[y0:y1, x0:x1]
            values, counts = np.unique(cell, return_counts=True)
            if len(values) <= 4:
                continue
            order = values[np.argsort(-counts, kind='stable')]
            keep = list(order[:4])
            if 0 in values and 0 not in keep:
                keep[-1] = 0
            solid = [v for v in keep if v != 0] or keep
            for v in values:
                if v not in keep:
                    nearest = min(solid, key=lambda k: int(((rgb[k] - rgb[v]) ** 2).sum()))
                    cell[cell == v] = nearest
    return out


def _encode_direction(frames, origin, palette=None):
    """frames: equal-sized H x W arrays of palette indices (0 = transparent); origin (x, y): where
    the unit stands on them. palette: given, cells with more than four values are reduced.
    Returns the direction's bytes and its size in the DC6 coding."""
    stack = np.stack(frames)
    solid = np.argwhere(stack.any(0))
    if not len(solid):
        solid = np.array([[origin[1], origin[0]]])
    (top, left), (bottom, right) = solid.min(0), solid.max(0)
    stack = stack[:, top:bottom + 1, left:right + 1]
    height, width = stack.shape[1:]
    xoffset, yoffset = int(left - origin[0]), int(bottom - origin[1])
    columns, rows = _cells(0, width), _cells(0, height)
    if palette is not None:
        stack = np.stack([limit_cell_colours(f, palette, columns, rows) for f in stack])
    coded = [dc6_size(f) for f in stack]
    used = sorted(set(np.unique(stack).tolist()) | {0})
    compact = np.zeros(256, dtype=np.int64)
    compact[used] = np.arange(len(used))
    stack = compact[stack]
    xs, ys = np.concatenate([[0], np.cumsum(columns)]), np.concatenate([[0], np.cumsum(rows)])
    equal, mask, encoding, codes, pixels = BitWriter(), BitWriter(), BitWriter(), BitWriter(), BitWriter()
    for index in range(len(stack)):
        for y in range(len(rows)):
            for x in range(len(columns)):
                cell = stack[index, ys[y]:ys[y + 1], xs[x]:xs[x + 1]]
                if index:
                    same = np.array_equal(cell, stack[index - 1, ys[y]:ys[y + 1], xs[x]:xs[x + 1]])
                    equal.write(1 if same else 0, 1)
                    if same:
                        continue
                    mask.write(15, 4)
                encoding.write(0, 1)
                colours = [int(v) for v in np.unique(cell) if v]
                if len(colours) > 4 or (len(colours) == 4 and (cell == 0).any()):
                    raise ValueError('a cell has more than four values; pass the palette so they can be reduced')
                last = 0
                for value in colours:
                    step = value - last
                    while step >= 15:
                        codes.write(15, 4)
                        step -= 15
                    codes.write(step, 4)
                    last = value
                if len(colours) < 4:
                    codes.write(0, 4)
                # The decoder lists the values highest first, then zeros.
                if colours:
                    values = colours[::-1] + [0] * (4 - len(colours))
                    bits = 1 if len(colours) == 1 else 2
                    lookup = {v: i for i, v in reversed(list(enumerate(values)))}
                    for value in cell.reshape(-1):
                        pixels.write(lookup[int(value)], bits)
    head = BitWriter()
    head.write(sum(coded) + 35 * len(stack), 32)
    head.write(3, 2)
    widths = [0, _width_code([width], False), _width_code([height], False), _width_code([xoffset], True),
              _width_code([yoffset], True), 0, _width_code(coded, False)]
    for code in widths:
        head.write(code, 4)
    for size in coded:
        head.write(width, WIDTHS[widths[1]])
        head.write(height, WIDTHS[widths[2]])
        head.write(xoffset, WIDTHS[widths[3]])
        head.write(yoffset, WIDTHS[widths[4]])
        head.write(size, WIDTHS[widths[6]])
        head.write(0, 1)                             # stored top down
    head.write(len(equal), 20)
    head.write(len(mask), 20)
    head.write(len(encoding), 20)
    head.write(0, 20)                                # no raw pixel stream
    for value in range(256):
        head.write(1 if value in used else 0, 1)
    for stream in (equal, mask, encoding, codes, pixels):
        head.extend(stream)
    return head.to_bytes(), sum(coded) + 35 * len(stack)


def encode(directions, origin, palette=None):
    """A DCC file from frames.

    directions: one list of frames per stored direction (see VIEW_ORDER for which is which);
    every frame an H x W array of palette indices, 0 transparent, all the same size.
    origin: (x, y) of the unit's standing point on those arrays (the same for all).
    palette: 256 x 3 or 4 colours; given, cells with more than four values are reduced
    (limit_cell_colours), otherwise such a cell is an error.
    Each direction is cropped to what its frames use. Every frame of a direction is stored on
    that one box, a cell that did not change since the frame before costs one bit.
    """
    count = len(directions[0])
    if any(len(d) != count for d in directions):
        raise ValueError('every direction needs the same number of frames')
    parts, sizes = [], []
    for frames in directions:
        frames = [np.asarray(f, dtype=np.uint8) for f in frames]
        data, size = _encode_direction(frames, origin, palette)
        parts.append(data)
        sizes.append(size)
    total = 24 + 4 * count * len(directions) + sum(sizes)
    head = struct.pack('<BBBIII', 0x74, 6, len(directions), count, 1, total)
    offset = len(head) + 4 * len(directions)
    table = b''
    for data in parts:
        table += struct.pack('<I', offset)
        offset += len(data)
    return head + table + b''.join(parts)


LAYER_NAMES = ['hd', 'tr', 'lg', 'ra', 'la', 'rh', 'lh', 'sh', 's1', 's2', 's3', 's4', 's5', 's6', 's7', 's8']


def encode_cof(frames, directions, box, speed=256, layers=('tr',), triggers=None, weapon='hth'):
    """An animation descriptor (.cof) for layers that are all drawn in every frame.

    box: (xmin, ymin, xmax, ymax) of the sprite around the unit's standing point; speed: 256 is
    one frame per game frame (25 a second). triggers: {frame: 1..4}: 1 marks the frame an attack
    hits on, 2 a missile is released, 3 a sound, 4 a skill takes effect.
    """
    out = bytearray(struct.pack('<4B4B', len(layers), frames, directions, 20, 0, 0, 0, 0))
    out += struct.pack('<4i', box[0], box[2], box[1], box[3])
    out += struct.pack('<HH', speed, 0)
    for name in layers:
        out += struct.pack('<5B4s', LAYER_NAMES.index(name), 1, 1, 0, 0, weapon.encode('ascii'))
    marks = bytearray(frames)
    for frame, kind in (triggers or {}).items():
        marks[int(frame)] = kind
    out += marks
    out += bytes(LAYER_NAMES.index(name) for name in layers) * (frames * directions)
    return bytes(out)


# --- DC6 (interface pictures: skill icons, portraits, panels, inventory pictures) -------------

class Dc6Frame:
    """One DC6 frame. pixels: H x W int16 palette indices, -1 where nothing is drawn (top row
    first). data: the frame's coded bytes as they were in the file (None for a new frame)."""
    __slots__ = ('flip', 'width', 'height', 'xoffset', 'yoffset', 'unknown', 'pixels', 'data')


def _decode_dc6_rows(data, width, height, flip):
    img = np.full((height, width), -1, dtype=np.int16)
    x, y = 0, (height - 1 if flip == 0 else 0)
    step = -1 if flip == 0 else 1
    pos, end = 0, len(data)
    while pos < end and 0 <= y < height:
        b = data[pos]
        pos += 1
        if b == 0x80:
            x = 0
            y += step
        elif b & 0x80:
            x += b & 0x7F
        else:
            n = max(0, min(b, width - x, end - pos))
            img[y, x:x + n] = np.frombuffer(data, dtype=np.uint8, count=n, offset=pos)
            pos += b
            x += b
    return img


class Dc6:
    """A DC6 file: frames[direction][index] -> Dc6Frame. Rows are run-length coded: a byte
    below 0x80 is a count of pixels that follow, 0x80 ends the row, above 0x80 skips
    (byte & 0x7F) pixels; with flip 0 the rows are stored bottom row first."""

    def __init__(self, data):
        version, self.flags, self.encoding, termination, directions, per_direction = struct.unpack_from('<6I', data, 0)
        if version != 6:
            raise ValueError('not a DC6 file')
        self.termination = struct.pack('<I', termination)
        self.directions, self.frames_per_direction = directions, per_direction
        pointers = struct.unpack_from(f'<{directions * per_direction}I', data, 24)
        self.frames = []
        for d in range(directions):
            row = []
            for i in range(per_direction):
                p = pointers[d * per_direction + i]
                f = Dc6Frame()
                f.flip, f.width, f.height, f.xoffset, f.yoffset, f.unknown, _next, length = struct.unpack_from('<8i', data, p)
                f.data = bytes(data[p + 32:p + 32 + length])
                f.pixels = _decode_dc6_rows(f.data, f.width, f.height, f.flip)
                row.append(f)
            self.frames.append(row)


def encode_dc6_frame(pixels):
    """The coded rows of a frame, bottom row first (flip 0). pixels: H x W, negative = not drawn."""
    pixels = np.asarray(pixels)
    out = bytearray()
    width = pixels.shape[1]
    for row in pixels[::-1]:
        solid = row >= 0
        edges = np.flatnonzero(np.diff(np.concatenate([[0], solid.astype(np.int8), [0]])))
        position = 0
        for start, end in zip(edges[::2].tolist(), edges[1::2].tolist()):
            gap = start - position
            while gap > 0:
                n = min(gap, 127)
                out.append(0x80 | n)
                gap -= n
            while start < end:
                n = min(end - start, 127)
                out.append(n)
                out += row[start:start + n].astype(np.uint8).tobytes()
                start += n
            position = end
        out.append(0x80)
    return bytes(out)


def encode_dc6(directions, offsets=(0, 0), termination=b'\xcd\xcd\xcd\xcd', flags=1):
    """A DC6 file. directions: one list of frames per direction; a frame is an H x W array of
    palette indices (negative = not drawn; every value from 0 up is a drawn pixel) or a Dc6Frame,
    which is written back with its own coded bytes, offsets and all (frames taken from another
    file stay byte for byte what they were). offsets: (x, y) of new frames."""
    count = len(directions[0])
    if any(len(d) != count for d in directions):
        raise ValueError('every direction needs the same number of frames')
    blocks = []
    for frames in directions:
        for f in frames:
            if isinstance(f, Dc6Frame) and f.data is not None:
                head = (f.flip, f.width, f.height, f.xoffset, f.yoffset, f.unknown)
                body = f.data
            else:
                pixels = f.pixels if isinstance(f, Dc6Frame) else np.asarray(f)
                head = (0, pixels.shape[1], pixels.shape[0], offsets[0], offsets[1], 0)
                body = encode_dc6_frame(pixels)
            blocks.append((head, body))
    out = bytearray(struct.pack('<4I', 6, flags, 0, struct.unpack('<I', termination)[0]) + struct.pack('<2I', len(directions), count))
    position = len(out) + 4 * len(blocks)
    starts = []
    for head, body in blocks:
        starts.append(position)
        position += 32 + len(body) + 3
    out += struct.pack(f'<{len(blocks)}I', *starts)
    for (head, body), start in zip(blocks, starts):
        out += struct.pack('<8i', *head, start + 32 + len(body) + 3, len(body)) + body + termination[:3]
    return bytes(out)


def dc6_self_test(archive=None, names=()):
    """Random frames must survive encode -> decode; with an archive, the named files must decode
    and encode back (returns how many came back byte for byte, of how many)."""
    rng = np.random.default_rng(6)
    for width, height in ((1, 1), (48, 48), (300, 7), (129, 3)):
        frames = [np.where(rng.random((height, width)) < 0.4, -1, rng.integers(0, 256, (height, width))).astype(np.int16) for _ in range(3)]
        back = Dc6(encode_dc6([frames, frames[::-1]]))
        assert back.directions == 2 and back.frames_per_direction == 3
        for d, wanted in enumerate((frames, frames[::-1])):
            for f, w in zip(back.frames[d], wanted):
                assert np.array_equal(f.pixels, w), 'DC6 round trip changed a frame'
    same = total = 0
    for name in names:
        data = archive.read(name)
        if data is None:
            continue
        dc6 = Dc6(data)
        kept = encode_dc6(dc6.frames, termination=dc6.termination, flags=dc6.flags)
        again = Dc6(kept)
        fresh = []
        for d in range(dc6.directions):
            for a, b in zip(dc6.frames[d], again.frames[d]):
                assert np.array_equal(a.pixels, b.pixels), f'{name}: kept frame changed'
                recoded = encode_dc6_frame(a.pixels) if a.flip == 0 else None
                if recoded is not None:
                    assert np.array_equal(_decode_dc6_rows(recoded, a.width, a.height, 0), a.pixels), f'{name}: recoded frame differs'
                fresh.append(recoded == a.data)
        total += 1
        same += 1 if all(fresh) else 0
    return same, total


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
    p = sub.add_parser('dc6test')
    p.add_argument('--game', default=os.environ.get('D2R_PATH'))
    p.add_argument('files', nargs='*')
    args = parser.parse_args(argv)
    from d2r_casc import D2RArchive
    if args.command == 'dc6test':
        if not args.game:
            dc6_self_test()
            print('DC6 round trip of random frames: ok')
            return 0
        with D2RArchive(args.game) as archive:
            names = args.files or [n for n in archive.list() if n.endswith('.dc6') and n.startswith('global/ui/')]
            same, total = dc6_self_test(archive, names)
        print(f'DC6 round trip ok; {total} game files decoded and written back, {same} of them recoded byte for byte')
        return 0
    from PIL import Image
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
