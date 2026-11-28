"""Diablo II legacy bitmap fonts (`local/font/<set>/`): glyph pictures, metrics, code map.

`<font>.dc6`   256 glyph frames, one per character code, palette indices (see LegacySprite.py).
`<font>.dh6`   (latin2 only, 14 files) the same frame table as a DC6 with header flags 5 and
               termination 0, but every frame body is raw colour: 3 bytes per pixel, top row
               first, no run-length coding (length = 3 x width x height in all 14 files).
               Smoothed glyphs; which byte is red has not been settled (glyphs are near grey).
`<font>.tbl`   metrics. "Woo!", u16 1, u16 0, u16 glyph count (256), u8 line height, u8 (cap
               height in some files), then per glyph 14 bytes:
               u16 character code, u8 0, u8 advance width, u8 height, u8 1, u16 0,
               u16 frame number in the picture file, 4 x 0.
`default.map`  "KAMAP\\nISO\\n\\x1a", u32 0, u16 count, u8 range count, the ranges (u8 first, u8 last
               character code), count x (u16 character code, u16 Unicode), count x u16 (an
               order number per entry). latin and chi: 191 codes mapped to themselves.
`default.tbl`  a Unicode consortium mapping text file, not a font table.

usage:
  LegacyFont.py info   <font.tbl> [--game <D2R folder>]
  LegacyFont.py to-png <font.dc6 | font.dh6> <out.png> [--palette <pal.dat>] [--game <D2R folder>]
`to-png` lays the 256 glyphs out 16 x 16. A .dc6 needs a palette (default: the game's
`global/palette/act1/pal.dat` through --game). Needs numpy and Pillow.
"""
import argparse
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from HdPhysics import load  # noqa: E402


def read_metrics(data):
    """-> (line height, [(code, advance, height, frame)])"""
    if data[:4] != b'Woo!':
        raise ValueError('not a font .tbl')
    count, line = struct.unpack_from('<HB', data, 8)
    glyphs = []
    for k in range(count):
        code, _, advance, height, _, _, frame = struct.unpack_from('<HBBBBHH', data, 12 + 14 * k)
        glyphs.append((code, advance, height, frame))
    return line, glyphs


def read_map(data):
    """-> [(character code, Unicode, order number)]"""
    if data[:11] != b'KAMAP\nISO\n\x1a':
        raise ValueError('not a font .map')
    count, ranges = struct.unpack_from('<HB', data, 15)
    at = 18 + 2 * ranges
    pairs = np.frombuffer(data, '<u2', count * 2, at).reshape(-1, 2)
    order = np.frombuffer(data, '<u2', count, at + 4 * count)
    return [(int(a), int(b), int(c)) for (a, b), c in zip(pairs, order)]


def read_dh6(data):
    """-> list of H x W x 3 uint8 arrays, one per frame."""
    version, flags, _, _, directions, per_direction = struct.unpack_from('<6I', data, 0)
    if version != 6 or flags != 5:
        raise ValueError('not a .dh6 file')
    frames = []
    for pointer in struct.unpack_from(f'<{directions * per_direction}I', data, 24):
        _, width, height, _, _, _, _, length = struct.unpack_from('<8i', data, pointer)
        if length != 3 * width * height:
            raise ValueError('a frame is not raw 24-bit colour')
        frames.append(np.frombuffer(data, 'u1', length, pointer + 32).reshape(height, width, 3))
    return frames


def sheet(frames, columns=16):
    """Frames (H x W x 3 or 4) side by side in rows of `columns`."""
    height = max(f.shape[0] for f in frames)
    width = max(f.shape[1] for f in frames)
    rows = -(-len(frames) // columns)
    out = np.zeros((rows * height, columns * width, frames[0].shape[2]), 'u1')
    for k, f in enumerate(frames):
        y, x = k // columns * height, k % columns * width
        out[y:y + f.shape[0], x:x + f.shape[1]] = f
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['info', 'to-png'])
    ap.add_argument('args', nargs='+')
    ap.add_argument('--game', default=os.environ.get('D2R_PATH'))
    ap.add_argument('--palette')
    a = ap.parse_args()
    data = load(a.args[0], a.game)
    if a.command == 'info':
        line, glyphs = read_metrics(data)
        print(f'{len(glyphs)} glyphs, line height {line}')
        for code, advance, height, frame in glyphs:
            if 32 < code < 127:
                print(f'  {chr(code)}  code {code}  advance {advance}  height {height}  frame {frame}')
        return
    from PIL import Image
    if struct.unpack_from('<I', data, 4)[0] == 5:
        picture = sheet(read_dh6(data))
        mode = 'RGB'
    else:
        import LegacySprite
        palette = LegacySprite.load_palette(load(a.palette or 'global/palette/act1/pal.dat', a.game))
        frames = []
        for frame in LegacySprite.Dc6(data).frames[0]:
            rgba = np.zeros(frame.pixels.shape + (4,), 'u1')
            drawn = frame.pixels >= 0
            rgba[drawn] = np.asarray(palette, 'u1')[frame.pixels[drawn]]     # index 0 stays see-through
            frames.append(rgba)
        picture = sheet(frames)
        mode = 'RGBA'
    Image.fromarray(picture, mode).save(a.args[1])
    print(f'{a.args[1]}: {picture.shape[1]} x {picture.shape[0]}')


if __name__ == '__main__':
    main()
