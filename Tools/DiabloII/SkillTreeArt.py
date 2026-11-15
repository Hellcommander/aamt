"""Draw a skill tree page picture for a custom skill page: a frame in every occupied cell and
arrows for the page's own prerequisites, in the stock art's style.

A class's tree picture (`hd/global/ui/spells/skill_trees/<cls>skilltree.sprite`) is a transparent
overlay with three pages side by side (one per tab): the tab strip on top, then skill frames,
level boxes and prerequisite arrows on a clear background. Each page only has frames where that
tab has skills, so skills of another page put in other cells sit on bare background.

This tool takes the stock picture, keeps each page's tab strip, clears the grid and draws it
again from pieces cut out of the stock art:
  - a cell (big frame + level box), from a stock cell with no arrow touching it,
  - an arrow, as a shaft slice tiled to any length plus the stock arrowhead, rotated to any
    direction.
An arrow that would cross another occupied cell is left out (and reported): drawn through, it
would look like a chain through the skill in between. Move one of the cells to get it drawn.

    python SkillTreeArt.py draw --game <D2R> --class dr --page 1 --spec page.json --out <mod>/hd [--name qrskilltree]

page.json: {"cells": [[row, col], ...], "arrows": [[[row, col], [row, col]], ...]}   (from -> to, 1-based)
Writes <out>/global/ui/spells/skill_trees/<name>.sprite and <name>.lowend.sprite (same size and
pages as the stock picture; only the grid of every page is replaced), and <name>.png to look at.
A layout refers to it as `Spells\\Skill_Trees\\<name>`.

Sprite format (version 31): "SpA1", u16 31, u16 ?, u32 width, u32 height, u32 0, u32 pages,
u32 0, u32 0, u32 data size, u32 4, then width x height RGBA bytes; pages are side by side.
"""
import argparse
import json
import math
import os
import struct
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Icon top-left of each column and row in a page (the layout's skillColumn / skillRow minus the picture's
# position 132, 160 in skillstreepanelhd.json).
COLUMNS = [121, 383, 643]
ROWS = [136, 318, 494, 674, 854, 1030]
ICON = 128
STRIP = 88          # tab strip height
PAD = 14            # frame border outside the icon
CELL_W = 210        # frame + level box, from the icon's left edge
ANCHOR_Y = 58       # arrows aim at this height in the icon (the stock arrows keep clear of the level box)


def read_sprite(data):
    magic, version, _, width, height, _, pages = struct.unpack_from('<4sHHIIII', data, 0)
    if magic != b'SpA1' or version != 31:
        raise ValueError(f'only uncompressed (version 31) sprites are handled, this is {magic} {version}')
    header = data[:40]
    pixels = np.frombuffer(data, dtype=np.uint8, count=width * height * 4, offset=40).reshape(height, width, 4).copy()
    return header, pixels, pages


def write_sprite(header, pixels):
    h, w = pixels.shape[:2]
    head = bytearray(header)
    struct.pack_into('<I', head, 8, w)
    struct.pack_into('<I', head, 12, h)
    struct.pack_into('<I', head, 32, w * h * 4)
    return bytes(head) + pixels.astype(np.uint8).tobytes()


def cell_template(page_img):
    """Frame + level box, cut from two stock cells: the top half of the page-3 cell at row 1 column 3
    (an arrow leaves its bottom) and the bottom half of the page-3 cell at row 6 column 2 (an arrow
    enters its top). The stock cells are pixel copies of one another, so the halves meet cleanly."""
    def cut(img, r, c):
        x, y = COLUMNS[c - 1], ROWS[r - 1]
        return img[y - PAD - 4:y + ICON + PAD + 6, x - PAD - 4:x + CELL_W]
    top = cut(page_img, 1, 3)
    bottom = cut(page_img, 6, 2)
    out = bottom.copy()
    half = (ICON // 2) + PAD + 4
    out[:half] = top[:half]
    return out


def arrow_pieces(page_img):
    """(shaft slice, arrowhead) pointing down, from the long stock arrow in page 3 under row 1 column 3."""
    x = COLUMNS[2] + ICON // 2
    region = page_img[ROWS[0] + ICON + PAD + 2:ROWS[2] - PAD, x - 40:x + 40]
    alpha = region[:, :, 3].astype(int)
    width_per_row = (alpha > 30).sum(1)
    shaft_w = int(np.median(width_per_row[10:40]))
    head_start = int(np.argmax(width_per_row > shaft_w + 6))
    shaft = region[20:30]
    head = region[head_start:]
    cols = np.nonzero((head[:, :, 3] > 10).any(0))[0]
    head = head[:, cols.min():cols.max() + 1]
    scols = np.nonzero((shaft[:, :, 3] > 10).any(0))[0]
    shaft = shaft[:, scols.min():scols.max() + 1]
    return shaft, head


def draw_arrow(canvas, start, end, shaft, head):
    """Pastes an arrow from start to end (x, y) onto an RGBA canvas (PIL Image)."""
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = int(round(math.hypot(dx, dy)))
    if length < 8:
        return
    hh = head.shape[0]
    head_img = Image.fromarray(head)
    if length < hh:
        head_img = head_img.resize((head.shape[1], max(1, length)), Image.LANCZOS)
        hh = length
    width = max(shaft.shape[1], head.shape[1])
    arrow = Image.new('RGBA', (width, length), (0, 0, 0, 0))
    shaft_img = Image.fromarray(shaft)
    y = 0
    while y < length - hh:
        piece = shaft_img.crop((0, 0, shaft.shape[1], min(shaft.shape[0], length - hh - y)))
        arrow.alpha_composite(piece, ((width - shaft.shape[1]) // 2, y))
        y += shaft.shape[0]
    arrow.alpha_composite(head_img, ((width - head_img.width) // 2, length - hh))
    angle = math.degrees(math.atan2(dx, dy))        # 0 = pointing down
    rotated = arrow.rotate(angle, resample=Image.BICUBIC, expand=True)
    cx, cy = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
    canvas.alpha_composite(rotated, (int(round(cx - rotated.width / 2)), int(round(cy - rotated.height / 2))))


def box_exit(center, toward, half_w, half_h):
    """Where a line from a box's centre towards a point leaves the box."""
    dx, dy = toward[0] - center[0], toward[1] - center[1]
    scale = min(half_w / abs(dx) if dx else math.inf, half_h / abs(dy) if dy else math.inf)
    return center[0] + dx * scale, center[1] + dy * scale


def blocked(arrow, cells):
    """The occupied cells (other than its ends) a straight arrow would cross."""
    (r0, c0), (r1, c1) = arrow
    a = (COLUMNS[c0 - 1] + ICON / 2, ROWS[r0 - 1] + ANCHOR_Y)
    b = (COLUMNS[c1 - 1] + ICON / 2, ROWS[r1 - 1] + ANCHOR_Y)
    hit = []
    for r, c in cells:
        if (r, c) in ((r0, c0), (r1, c1)):
            continue
        x0, y0 = COLUMNS[c - 1] - PAD, ROWS[r - 1] - PAD
        x1, y1 = COLUMNS[c - 1] + ICON + PAD, ROWS[r - 1] + ICON + PAD
        for t in np.linspace(0.0, 1.0, 200):
            x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            if x0 < x < x1 and y0 < y < y1:
                hit.append((r, c))
                break
    return hit


def draw_page(page_img, cells, arrows, template, shaft, head):
    h, w = page_img.shape[:2]
    canvas = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    canvas.paste(Image.fromarray(page_img[:STRIP + 2]), (0, 0))
    layer = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    half = ICON / 2 + PAD
    for (r0, c0), (r1, c1) in arrows:
        a = (COLUMNS[c0 - 1] + ICON / 2, ROWS[r0 - 1] + ANCHOR_Y)
        b = (COLUMNS[c1 - 1] + ICON / 2, ROWS[r1 - 1] + ANCHOR_Y)
        start = box_exit(a, b, half, half)
        end = box_exit(b, a, half, half)
        draw_arrow(layer, start, end, shaft, head)
    # The frames are see-through inside, so no arrow may run under a cell: cut them away there.
    arrows_px = np.asarray(layer).copy()
    cover = template[:, :, 3] > 0
    for r, c in cells:
        x, y = COLUMNS[c - 1] - PAD - 4, ROWS[r - 1] - PAD - 4
        th, tw = cover.shape
        arrows_px[y:y + th, x:x + tw][cover[:min(th, h - y), :min(tw, w - x)]] = 0
    canvas.alpha_composite(Image.fromarray(arrows_px))
    tile = Image.fromarray(template)
    for r, c in cells:
        canvas.alpha_composite(tile, (COLUMNS[c - 1] - PAD - 4, ROWS[r - 1] - PAD - 4))
    return np.asarray(canvas)


def build(stock, cells, arrows):
    header, pixels, pages = read_sprite(stock)
    pw = pixels.shape[1] // pages
    ref = pixels[:, 2 * pw:3 * pw] if pages >= 3 else pixels[:, :pw]
    template = cell_template(ref)
    shaft, head = arrow_pieces(ref)
    out = pixels.copy()
    for p in range(pages):
        out[:, p * pw:(p + 1) * pw] = draw_page(pixels[:, p * pw:(p + 1) * pw], cells, arrows, template, shaft, head)
    return header, out, pages


def lowend(header_low, hd, pages):
    """The low-detail copy: each HD page scaled to the stock low-detail page size."""
    _, w, h = struct.unpack_from('<4sII', header_low, 4)[0], struct.unpack_from('<I', header_low, 8)[0], struct.unpack_from('<I', header_low, 12)[0]
    pw_hd = hd.shape[1] // pages
    pw = w // pages
    out = np.zeros((h, w, 4), dtype=np.uint8)
    for p in range(pages):
        page = Image.fromarray(hd[:, p * pw_hd:(p + 1) * pw_hd]).resize((pw, h), Image.LANCZOS)
        out[:, p * pw:(p + 1) * pw] = np.asarray(page)
    return out


def main(argv):
    parser = argparse.ArgumentParser(description='Draw a skill tree page picture.')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('draw')
    p.add_argument('--game', default=os.environ.get('D2R_PATH'))
    p.add_argument('--class', dest='cls', default='dr')
    p.add_argument('--spec', required=True)
    p.add_argument('--out', required=True, help='the mod\'s hd folder')
    p.add_argument('--name', default='qrskilltree')
    args = parser.parse_args(argv)
    spec = json.load(open(args.spec, encoding='utf-8'))
    cells = [tuple(c) for c in spec['cells']]
    arrows = []
    for a, b in spec.get('arrows', []):
        arrow = (tuple(a), tuple(b))
        crossing = blocked(arrow, cells)
        if crossing:
            print(f'arrow {arrow[0]} -> {arrow[1]} left out: a straight arrow would cross the cell(s) {crossing}')
        else:
            arrows.append(arrow)
    from d2r_casc import D2RArchive
    with D2RArchive(args.game) as archive:
        stock = archive.read(f'hd/global/ui/spells/skill_trees/{args.cls}skilltree.sprite')
        stock_low = archive.read(f'hd/global/ui/spells/skill_trees/{args.cls}skilltree.lowend.sprite')
    header, pixels, pages = build(stock, cells, arrows)
    folder = os.path.join(args.out, 'global', 'ui', 'spells', 'skill_trees')
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, f'{args.name}.sprite'), 'wb') as f:
        f.write(write_sprite(header, pixels))
    header_low = stock_low[:40]
    with open(os.path.join(folder, f'{args.name}.lowend.sprite'), 'wb') as f:
        f.write(write_sprite(header_low, lowend(header_low, pixels, pages)))
    preview = Image.new('RGBA', (pixels.shape[1], pixels.shape[0]), (40, 30, 26, 255))
    preview.alpha_composite(Image.fromarray(pixels))
    preview.convert('RGB').save(os.path.join(os.path.dirname(os.path.abspath(args.spec)), f'{args.name}.png'))
    print(f'{len(cells)} cells, {len(arrows)} arrows -> {folder}\\{args.name}.sprite (+ .lowend.sprite)')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
