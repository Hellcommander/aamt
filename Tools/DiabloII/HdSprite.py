"""Diablo II: Resurrected `.sprite` files (interface pictures) <-> PNG.

Header, 40 bytes, little endian; pixels start at 0x28. Surveyed on all 3,032 sprites.

  0x00  "SpA1"
  0x04  u16 pixel format, the same codes as `.texture` (HdTexture.py):
            31 (0x1F) RGBA8, straight alpha            3,028 files
            61 (0x3D) BC3 / DXT5                       loadingscreen_blank (2 files)
            50 (0x32) RGBA, 16-bit float per channel   hdr_calibration (2 files)
  0x06  u16 width of one frame as drawn
  0x08  u32 width of the whole sheet
  0x0C  u32 height
  0x10  u32 0, except cursors: u16 x, u16 y (taken to be the hot spot)
  0x14  u32 frame count
  0x18  u32 0
  0x1C  3 bytes 0, then one byte that is not 0 in 578 files (0x3F in 248, 0x3E in 141, 0x3D in
        102, about 25 other values). It matches nothing tried in the picture (alpha at the
        corners, largest, smallest, mean); taken to be leftover memory. `from-png` writes 0.
  0x20  u32 pixel data size
  0x24  u32 4

Rows run top to bottom and frames left to right in one row. A frame's cell is
often wider than the frame field (1 or 2 extra pixels per frame), so frame i is
cut at round(i * sheet width / count). `<name>.lowend.sprite` is the same
picture at half the size. The `hd/ui/**.params` files ("-frames N") are the
frame counts the sheets were built with.

usage:
  HdSprite.py info     <file> [--game <D2R folder>]
  HdSprite.py to-png   <file> <out.png> [--frame N] [--game <D2R folder>]   (default: the whole sheet)
  HdSprite.py from-png <in.png> <out.sprite> [--frames N] [--lowend <out.lowend.sprite>]

`from-png` writes RGBA8 with frames side by side and no gaps; the picture's
width must divide by the frame count. Needs Pillow; float sprites need numpy.
"""
import argparse
import io
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FORMATS = {31: 'RGBA8', 61: 'BC3', 50: 'RGBA16F'}


def header(data):
    if data[:4] != b'SpA1':
        raise ValueError('not a .sprite file')
    fmt, frame_width = struct.unpack_from('<HH', data, 4)
    width, height, spot, frames, _, unknown, size, _ = struct.unpack_from('<4IIf2I', data, 8)
    return {'format': fmt, 'frame_width': frame_width, 'width': width, 'height': height, 'frames': frames,
            'spot': (spot & 0xFFFF, spot >> 16), 'unknown': unknown, 'size': size}


def to_image(data):
    """The whole sheet as a Pillow RGBA image (float sprites are tone-mapped for viewing)."""
    from PIL import Image
    h = header(data)
    pixels = data[0x28:0x28 + h['size']]
    size = (h['width'], h['height'])
    if h['format'] == 31:
        return Image.frombytes('RGBA', size, pixels)
    if h['format'] == 61:
        dds = b'DDS ' + struct.pack('<7I', 124, 0x1007 | 0x80000, size[1], size[0], len(pixels), 0, 1) + b'\0' * 44
        dds += struct.pack('<2I4s5I', 32, 4, b'DXT5', 0, 0, 0, 0, 0) + struct.pack('<5I', 0x1000, 0, 0, 0, 0)
        img = Image.open(io.BytesIO(dds + pixels))
        img.load()
        return img.convert('RGBA')
    if h['format'] == 50:
        import numpy as np
        a = np.frombuffer(pixels, '<f2').reshape(size[1], size[0], 4).astype(float)
        rgb = np.clip(a[..., :3] / max(1.0, float(a[..., :3].max())), 0, 1) ** (1 / 2.2)
        out = np.dstack([rgb, np.clip(a[..., 3:], 0, 1)])
        return Image.fromarray((out * 255).astype('uint8'), 'RGBA')
    raise ValueError(f"sprite pixel format {h['format']} is not known")


def frame_box(h, index):
    """(left, top, right, bottom) of frame `index` in the sheet."""
    left = round(index * h['width'] / h['frames'])
    return (left, 0, min(left + h['frame_width'], h['width']), h['height'])


def from_image(img, frames=1):
    """A Pillow image holding `frames` equal frames side by side -> RGBA8 sprite bytes."""
    img = img.convert('RGBA')
    if img.width % frames:
        raise ValueError(f'the picture is {img.width} wide, which does not divide into {frames} frames')
    pixels = img.tobytes()
    return b'SpA1' + struct.pack('<HH4IIf2I', 31, img.width // frames, img.width, img.height, 0, frames, 0, 0.0,
                                 len(pixels), 4) + pixels


def load(path, game=None):
    if os.path.isfile(path):
        with open(path, 'rb') as f:
            return f.read()
    if game:
        from d2r_casc import D2RArchive
        with D2RArchive(game.replace('/', '\\')) as archive:
            data = archive.read(path.replace('\\', '/'))
        if data is not None:
            return data
    raise SystemExit(f'no such file: {path}' + ('' if game else ' (pass --game to read from the game archive)'))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['info', 'to-png', 'from-png'])
    ap.add_argument('args', nargs='+')
    ap.add_argument('--game', default=os.environ.get('D2R_PATH'))
    ap.add_argument('--frame', type=int)
    ap.add_argument('--frames', type=int, default=1)
    ap.add_argument('--lowend')
    a = ap.parse_args()
    if a.command == 'info':
        h = header(load(a.args[0], a.game))
        print(f"{FORMATS.get(h['format'], h['format'])}, sheet {h['width']} x {h['height']}, {h['frames']} frame(s) of "
              f"{h['frame_width']} px, cell {h['width'] / h['frames']:g} px, spot {h['spot']}, field 0x1C = {h['unknown']:g}")
    elif a.command == 'to-png':
        data = load(a.args[0], a.game)
        img = to_image(data)
        if a.frame is not None:
            img = img.crop(frame_box(header(data), a.frame))
        img.save(a.args[1])
        print(f'{a.args[1]}: {img.width} x {img.height}')
    else:
        from PIL import Image
        img = Image.open(a.args[0])
        with open(a.args[1], 'wb') as f:
            f.write(from_image(img, a.frames))
        print(f'{a.args[1]}: {img.width} x {img.height}, {a.frames} frame(s)')
        if a.lowend:
            small = img.convert('RGBA').resize((max(a.frames, img.width // 2 // a.frames * a.frames), max(1, img.height // 2)),
                                               Image.LANCZOS)
            with open(a.lowend, 'wb') as f:
                f.write(from_image(small, a.frames))
            print(f'{a.lowend}: {small.width} x {small.height}')


if __name__ == '__main__':
    main()
