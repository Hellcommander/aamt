"""Diablo II: Resurrected .texture files <-> images.

Header (little endian): "<DE(", u8 format, u8 0, u8 2, u8 mip count, u32 width, u32 height,
u32 depth (1), u32 0, u32 0, u32 mip count, u32 4, then per mip (u32 size, u32 offset
relative to the offset field itself), then the pixel data.

Formats seen in the game's effect textures (2026-11-13, 1474 files):
  0x1F  RGBA8, uncompressed
  0x39  BC1 (DXT1)            data maps (a fur flow map), 8 bytes per 4x4 block
  0x3A  BC1 (DXT1), sRGB      colour, 8 bytes per 4x4 block
  0x3D  BC3 (DXT5)            colour + alpha, 16 bytes per block
  0x3E  BC3 (DXT5), sRGB      albedo textures
  0x3F  BC4                   one channel (masks, noise), 8 bytes per block
  0x41  BC5                   two channels (distortion, normals), 16 bytes per block
The block formats were identified by decoding samples of each and looking at them.

What the model textures hold (channel statistics of samples, 2026-11-26):
  *_nrm  BC3 (0x3D). Red is 1 and blue 0 everywhere; the normal's x is in ALPHA and its y in
         GREEN, z is left out (z = sqrt(1 - x^2 - y^2)). Which reading makes the map the slope
         of one height field was tested on 40 maps: alpha = x, green = y in all 40, and, if x
         points right, green pointing UP the picture in 34.
         What the models say (116 meshes, 786,000 triangles): the stored Tangent runs along
         +u (x does point right); there is no Binormal, only the Tangent's fourth value
         (+1 or -1), and Normal x Tangent times that value runs along +v. Texture
         coordinate v runs DOWN the picture (UV outlines laid over 60 item normal maps: 24
         fit that way, 4 the other, 32 no difference). The model pixel shader (disassembled,
         see HdShader.py) uses sign x cross(Tangent, Normal) as the green axis, which is the
         opposite of the above, so it points up the picture. GREEN IS UP (OpenGL style):
         a glTF or Blender normal map goes in without flipping green.
  *_orm  BC3 (0x3D). Red occlusion, green roughness, blue metal, alpha 1.
  *_alb  BC3 sRGB (0x3E).

`hd/texture_desc_cache.json` lists every texture except hd/debug (31,073 entries): the header
fields (`type` = byte 6, `format`, `width`, `height`, `depth`, `levels`, `layoutType` and
`layoutData` = the two zero words) and `thumbnailBase64`, the texture's smallest mips from
level `thumbnailMip` on, stored like the header's own mip table (u32 count, u32 4, then
size + relative offset per mip, then the data). 500 entries were compared with their
textures: all equal. `thumbnailMip` is the first level whose longer side is 16 or less; for
names holding `_orm` it is the last level; one-level textures have no thumbnail. That rule
gives the stored number for all entries. Mods add textures without touching this file.

Reading needs Pillow (it decodes the block formats). Writing makes RGBA8 with one mip,
the layout of the game's own gradient textures; the game accepts it in any texture slot
tried so far.

usage:
  HdTexture.py info <file.texture>
  HdTexture.py to-png <file.texture> <out.png>
  HdTexture.py from-png <in.png> <out.texture> [--size N]   (N: resize to N x N; default keep)
  HdTexture.py cache-entry <file.texture> <data/hd/... name>   the texture_desc_cache.json entry, as JSON
"""
import io
import struct
import sys

MAGIC = b'<DE('
FORMATS = {0x1F: 'RGBA8', 0x39: 'BC1', 0x3A: 'BC1 sRGB', 0x3D: 'BC3', 0x3E: 'BC3 sRGB', 0x3F: 'BC4', 0x41: 'BC5'}
_FOURCC = {0x39: b'DXT1', 0x3A: b'DXT1', 0x3D: b'DXT5', 0x3E: b'DXT5', 0x3F: b'ATI1', 0x41: b'ATI2'}


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


def from_image_bc3(img, srgb=True, size=None):
    """A Pillow image -> BC3 (DXT5) .texture bytes with a full mip chain, the layout of the
    game's own character textures (albedo: sRGB, format 0x3E; other maps: 0x3D).
    size: resize to size x size first (a power of two); otherwise the sides are rounded down to
    powers of two. Needs a Pillow that writes DXT5 DDS files (10.3 or newer; checked with 12.3.0)."""
    from PIL import Image
    img = img.convert('RGBA')
    w, h = (size, size) if size else (1 << (img.width.bit_length() - 1), 1 << (img.height.bit_length() - 1))
    if (w, h) != img.size:
        img = img.resize((w, h), Image.LANCZOS)
    levels = []
    level = img
    while True:
        buffer = io.BytesIO()
        level.save(buffer, 'DDS', pixel_format='DXT5')
        levels.append(buffer.getvalue()[128:])
        if level.width == 1 and level.height == 1:
            break
        level = level.resize((max(1, level.width // 2), max(1, level.height // 2)), Image.BOX)
    count = len(levels)
    head = MAGIC + bytes([0x3E if srgb else 0x3D, 0x00, 0x02, count]) + struct.pack('<IIIIII', w, h, 1, 0, 0, count) + struct.pack('<I', 4)
    table_at = len(head)
    data_at = table_at + 8 * count
    table = b''
    for k, pixels in enumerate(levels):
        offset_field = table_at + 8 * k + 4
        table += struct.pack('<II', len(pixels), data_at - offset_field)
        data_at += len(pixels)
    return head + table + b''.join(levels)


def mip_table(data, at):
    """The mips of a table at `at` (u32 count, u32 relative offset of the entries): a list of bytes."""
    count, rel = struct.unpack_from('<II', data, at)
    table = at + 4 + rel
    out = []
    for k in range(count):
        size, r = struct.unpack_from('<II', data, table + 8 * k)
        start = table + 8 * k + 4 + r
        out.append(data[start:start + size])
    return out


def thumbnail_level(name, width, height, levels):
    if levels == 1:
        return 1
    if '_orm' in name.lower().rsplit('/', 1)[-1]:
        return levels - 1
    level = 0
    while max(width, height) >> level > 16 and level < levels - 1:
        level += 1
    return level


def cache_entry(name, data):
    """The `hd/texture_desc_cache.json` entry of a texture. name: 'data/hd/.../x.texture'."""
    import base64
    width, height, depth, layout_type, layout_data = struct.unpack_from('<5I', data, 8)
    levels = data[7]
    first = thumbnail_level(name, width, height, levels)
    mips = mip_table(data, 28)[first:]
    blob = struct.pack('<II', len(mips), 4)
    at = 8 + 8 * len(mips)
    for k, mip in enumerate(mips):
        blob += struct.pack('<II', len(mip), at - (8 + 8 * k + 4))
        at += len(mip)
    blob += b''.join(mips)
    return {'filename': name, 'treatAsDecal': False, 'type': data[6], 'width': width, 'height': height, 'depth': depth,
            'levels': levels, 'format': data[4], 'layoutType': layout_type, 'layoutData': layout_data,
            'thumbnailMip': first, 'thumbnailBase64': base64.b64encode(blob).decode('ascii')}


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        return 2
    cmd = args[0]
    if cmd == 'cache-entry' and len(args) == 3:
        import json
        print(json.dumps(cache_entry(args[2], open(args[1], 'rb').read())))
        return 0
    from PIL import Image
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
