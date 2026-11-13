"""Diablo II: Resurrected .texture files <-> images.

Header (little endian): "<DE(", u8 format, u8 0, u8 2, u8 mip count, u32 width, u32 height,
u32 depth (1), u32 0, u32 0, u32 mip count, u32 4, then per mip (u32 size, u32 offset
relative to the offset field itself), then the pixel data.

Formats seen in the game's effect textures (2026-11-13, 1474 files):
  0x1F  RGBA8, uncompressed
  0x3A  BC1 (DXT1)            colour, 8 bytes per 4x4 block
  0x3D  BC3 (DXT5)            colour + alpha, 16 bytes per block
  0x3E  BC3 (DXT5), sRGB      albedo textures
  0x3F  BC4                   one channel (masks, noise), 8 bytes per block
  0x41  BC5                   two channels (distortion, normals), 16 bytes per block
The block formats were identified by decoding samples of each and looking at them.

Reading needs Pillow (it decodes the block formats). Writing makes RGBA8 with one mip,
the layout of the game's own gradient textures; the game accepts it in any texture slot
tried so far.

usage:
  HdTexture.py info <file.texture>
  HdTexture.py to-png <file.texture> <out.png>
  HdTexture.py from-png <in.png> <out.texture> [--size N]   (N: resize to N x N; default keep)
"""
import io
import struct
import sys

MAGIC = b'<DE('
FORMATS = {0x1F: 'RGBA8', 0x3A: 'BC1', 0x3D: 'BC3', 0x3E: 'BC3 sRGB', 0x3F: 'BC4', 0x41: 'BC5'}
_FOURCC = {0x3A: b'DXT1', 0x3D: b'DXT5', 0x3E: b'DXT5', 0x3F: b'ATI1', 0x41: b'ATI2'}


def header(data):
    if data[:4] != MAGIC:
        raise ValueError('not a .texture file')
    width, height = struct.unpack_from('<II', data, 8)
    mips = struct.unpack_from('<I', data, 28)[0]
    size, rel = struct.unpack_from('<II', data, 36)
    return {'format': data[4], 'width': width, 'height': height, 'mips': mips, 'offset': 40 + rel, 'size': size}


def to_image(data):
    """The largest mip as a Pillow RGBA image."""
    from PIL import Image
    h = header(data)
    pixels = data[h['offset']:h['offset'] + h['size']]
    w, ht = h['width'], h['height']
    if h['format'] == 0x1F:
        return Image.frombytes('RGBA', (w, ht), pixels)
    fourcc = _FOURCC.get(h['format'])
    if fourcc is None:
        raise ValueError('texture format 0x%02X is not known' % h['format'])
    # A minimal DDS file around the block data; Pillow decodes it.
    dds = b'DDS ' + struct.pack('<7I', 124, 0x1007 | 0x80000, ht, w, len(pixels), 0, 1) + b'\0' * 44
    dds += struct.pack('<2I4s5I', 32, 4, fourcc, 0, 0, 0, 0, 0) + struct.pack('<5I', 0x1000, 0, 0, 0, 0)
    img = Image.open(io.BytesIO(dds + pixels))
    img.load()
    if h['format'] == 0x3F:      # one channel: show it as grey with itself as alpha
        g = img.convert('L')
        return Image.merge('RGBA', (g, g, g, g))
    if h['format'] == 0x41:      # two channels: red and green
        r, g = img.convert('RGB').split()[:2]
        return Image.merge('RGBA', (r, g, Image.new('L', img.size, 128), Image.new('L', img.size, 255)))
    return img.convert('RGBA')


def from_image(img):
    """A Pillow image -> RGBA8 .texture bytes with one mip."""
    img = img.convert('RGBA')
    w, h = img.size
    pixels = img.tobytes()
    head = MAGIC + bytes([0x1F, 0x00, 0x02, 0x01]) + struct.pack('<IIIIII', w, h, 1, 0, 0, 1)
    return head + struct.pack('<III', 4, len(pixels), 4) + pixels


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        return 2
    from PIL import Image
    cmd = args[0]
    if cmd == 'info':
        h = header(open(args[1], 'rb').read())
        print('%dx%d, %s, %d mips' % (h['width'], h['height'], FORMATS.get(h['format'], 'format 0x%02X' % h['format']), h['mips']))
    elif cmd == 'to-png':
        to_image(open(args[1], 'rb').read()).save(args[2])
    elif cmd == 'from-png':
        img = Image.open(args[1])
        if '--size' in args:
            n = int(args[args.index('--size') + 1])
            img = img.convert('RGBA').resize((n, n), Image.LANCZOS)
        open(args[2], 'wb').write(from_image(img))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
