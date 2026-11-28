"""Diablo II legacy map tiles, `.dt1` (`global/tiles/**`, 266 files): read and draw.

Little endian. 260 of the 266 files of build 3.4.95041 read and pass `check`; the other six
(act1 barracks.dt1, gargtrap.dt1, catacombs.dt1, cathedrl.dt1, court.dt1, outdoor1.dt1) are an
older layout (version 4.1) that this tool does not read.

  header, 276 bytes   i32 7, i32 6, 260 x 0, i32 tile count, i32 offset of the tile table (276)
  tile, 96 bytes      i32 direction, i16 roof height, u8 sound, u8 animated, i32 height,
                      i32 width, i32 0, i32 orientation (0 floor, 1-12 and 14 walls and corners,
                      13 shadow, 15 roof, 16-19 lower walls), i32 main index, i32 sub index,
                      i32 rarity (frame number when animated), 4 bytes, 25 x u8 walk flags of
                      the 5 x 5 sub-squares, 7 x 0, i32 offset of the tile's blocks,
                      i32 size of the tile's blocks (headers and pixels), i32 block count, 12 x 0
  block, 20 bytes     i16 x, i16 y, i16 0, u8 grid x, u8 grid y, i16 format, i32 length, i16 0,
                      i32 offset of the pixels from the tile's first block header
  pixels              format 1: a 32 x 15 diamond, 256 bytes, rows of 4, 8 ... 32 ... 8, 4 pixels,
                      centred. Other formats: 32 pixels wide, run-length coded rows: (skip, count)
                      then count palette indices; (0, 0) ends a row.
Orientation, main index and sub index are what a .ds1 cell names a tile by.

usage:
  LegacyTiles.py info   <file.dt1> [--game <D2R folder>]
  LegacyTiles.py to-png <file.dt1> <out folder> [--palette <pal.dat>] [--game <D2R folder>]
  LegacyTiles.py check  <file.dt1> ... [--game <D2R folder>]
`to-png` writes one picture per tile, `<orientation>_<main>_<sub>_<n>.png`. The palette defaults
to the act's own (`global/palette/<act>/pal.dat`, act1 when the path names none). Needs numpy, Pillow.
"""
import argparse
import os
import re
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from HdPhysics import load  # noqa: E402

DIAMOND = [4, 8, 12, 16, 20, 24, 28, 32, 28, 24, 20, 16, 12, 8, 4]


def read(data):
    """-> list of tiles: dict of the header fields plus `blocks` [(x, y, format, pixels 2-D int16, -1 = empty)]."""
    one, two = struct.unpack_from('<2i', data, 0)
    count, table = struct.unpack_from('<2i', data, 268)
    if (one, two) != (7, 6):
        raise ValueError(f'not a .dt1 this tool knows (version {one}.{two})')
    tiles = []
    for k in range(count):
        at = table + 96 * k
        direction, roof, sound, animated, height, width, _, orientation, main, sub, rarity = struct.unpack_from('<ihBB7i', data, at)
        blocks_at, blocks_size, block_count = struct.unpack_from('<3i', data, at + 72)
        tile = {'direction': direction, 'roof_height': roof, 'sound': sound, 'animated': animated, 'height': height, 'width': width,
                'orientation': orientation, 'main': main, 'sub': sub, 'rarity': rarity,
                'flags': list(data[at + 40:at + 65]), 'blocks': [], 'blocks_size': blocks_size, 'problems': []}
        used = 20 * block_count
        for b in range(block_count):
            x, y, _, grid_x, grid_y, fmt, length, _, offset = struct.unpack_from('<3hBBhihi', data, blocks_at + 20 * b)
            body = data[blocks_at + offset:blocks_at + offset + length]
            used += length
            if fmt == 1:
                pixels = np.full((15, 32), -1, np.int16)
                if length != 256:
                    tile['problems'].append('a diamond block is not 256 bytes')
                else:
                    p = 0
                    for row, n in enumerate(DIAMOND):
                        pixels[row, 16 - n // 2:16 + n // 2] = np.frombuffer(body, 'u1', n, p)
                        p += n
            else:
                rows, row, x0, p = [], np.full(32, -1, np.int16), 0, 0
                while p + 1 < len(body):
                    skip, n = body[p], body[p + 1]
                    p += 2
                    if skip == 0 and n == 0:
                        rows.append(row)
                        row, x0 = np.full(32, -1, np.int16), 0
                        continue
                    x0 += skip
                    if x0 + n > 32 or p + n > len(body):
                        tile['problems'].append('a run leaves the block')
                        break
                    row[x0:x0 + n] = np.frombuffer(body, 'u1', n, p)
                    x0 += n
                    p += n
                pixels = np.array(rows, np.int16).reshape(-1, 32) if rows else np.full((0, 32), -1, np.int16)
            tile['blocks'].append((x, y, fmt, pixels))
        if used != blocks_size:
            tile['problems'].append('block sizes do not add up to the tile size')
        tiles.append(tile)
    return tiles


def picture(tile):
    """The tile's blocks put together: (H x W int16 palette indices, -1 = empty), or None without pixels."""
    blocks = [b for b in tile['blocks'] if b[3].size]
    if not blocks:
        return None
    left = min(b[0] for b in blocks)
    top = min(b[1] for b in blocks)
    right = max(b[0] + 32 for b in blocks)
    bottom = max(b[1] + b[3].shape[0] for b in blocks)
    out = np.full((bottom - top, right - left), -1, np.int16)
    for x, y, _, pixels in blocks:
        view = out[y - top:y - top + pixels.shape[0], x - left:x - left + 32]
        view[pixels >= 0] = pixels[pixels >= 0]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['info', 'to-png', 'check'])
    ap.add_argument('args', nargs='+')
    ap.add_argument('--game', default=os.environ.get('D2R_PATH'))
    ap.add_argument('--palette')
    a = ap.parse_args()
    if a.command == 'check':
        failed = 0
        for path in a.args:
            try:
                bad = sorted({p for t in read(load(path, a.game)) for p in t['problems']})
            except (ValueError, struct.error) as error:
                bad = [str(error)]
            failed += bool(bad)
            print(('FAIL ' + '; '.join(bad) if bad else 'ok  ') + ' ' + path)
        sys.exit(1 if failed else 0)
    tiles = read(load(a.args[0], a.game))
    if a.command == 'info':
        print(f'{len(tiles)} tiles')
        for t in tiles:
            print(f"  orientation {t['orientation']:2d}  main {t['main']:3d}  sub {t['sub']:3d}  {t['width']} x {abs(t['height'])}  "
                  f"{len(t['blocks'])} blocks  rarity {t['rarity']}" + ('  animated' if t['animated'] else ''))
        return
    if len(a.args) != 2:
        raise SystemExit('to-png needs <file.dt1> <out folder>')
    from PIL import Image
    import LegacySprite
    act = re.search(r'tiles[\\/](act\d)', a.args[0].lower())
    palette_path = a.palette or f"global/palette/{act.group(1) if act else 'act1'}/pal.dat"
    if 'expansion' in a.args[0].lower() and not a.palette:
        palette_path = 'global/palette/act5/pal.dat'
    palette = np.asarray(LegacySprite.load_palette(load(palette_path, a.game)), 'u1')
    os.makedirs(a.args[1], exist_ok=True)
    written = 0
    for n, t in enumerate(tiles):
        indices = picture(t)
        if indices is None:
            continue
        rgba = np.zeros(indices.shape + (4,), 'u1')
        drawn = indices >= 0
        rgba[drawn] = palette[indices[drawn]]       # index 0 stays see-through, as the palette has it
        Image.fromarray(rgba, 'RGBA').save(os.path.join(a.args[1], f"{t['orientation']}_{t['main']}_{t['sub']}_{n}.png"))
        written += 1
    print(f'{a.args[1]}: {written} pictures of {len(tiles)} tiles')


if __name__ == '__main__':
    main()
