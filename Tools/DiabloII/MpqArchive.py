"""Reads MPQ archives (the packed form of a D2R / D2RLoader data mod) and extracts them.

    python MpqArchive.py list <archive.mpq>
    python MpqArchive.py extract <archive.mpq> <out folder>

D2RLoader can load a mod packed as a real MPQ file (<Name>.mpq, a file, not a folder). D2RMM
only takes loose files (an .mpq folder), so such a mod has to be extracted first; then
ConvertDataMod.py can turn the folder into a D2RMM mod. `extract` writes
<out>\\<Name>.mpq\\data\\... with a modinfo.json, which is the folder layout D2RMM and the
converter expect, when the archive's files start with data\\ (or are game paths without it).

Written from the published MPQ format description (header, encrypted hash and block tables,
sector offset tables, compression masks). Supported: format versions 0-1, encrypted and
fix-key files, single-unit files, sector CRCs (skipped), zlib (0x02), bzip2 (0x10) and
uncompressed data. Others (PKWARE implode, Huffman, ADPCM, LZMA, sparse) stop with a message
naming the file. Names come from the archive's (listfile); files it does not name cannot be
extracted and are counted.
"""
import bz2
import json
import struct
import sys
import zlib
from pathlib import Path

MASK = 0xFFFFFFFF


def _crypt_table():
    seed = 0x00100001
    table = [0] * 0x500
    for i in range(0x100):
        index = i
        for _ in range(5):
            seed = (seed * 125 + 3) % 0x2AAAAB
            high = (seed & 0xFFFF) << 16
            seed = (seed * 125 + 3) % 0x2AAAAB
            table[index] = high | (seed & 0xFFFF)
            index += 0x100
    return table


CRYPT = _crypt_table()
HASH_OFFSET, HASH_A, HASH_B, HASH_KEY = 0, 1, 2, 3


def hash_string(text, kind):
    """Names are hashed as written (upper case); Mpq.find also tries them with backslashes."""
    seed1, seed2 = 0x7FED7FED, 0xEEEEEEEE
    for ch in text.upper().encode('latin-1'):
        seed1 = (CRYPT[(kind << 8) + ch] ^ ((seed1 + seed2) & MASK)) & MASK
        seed2 = (ch + seed1 + seed2 + (seed2 << 5) + 3) & MASK
    return seed1


def decrypt(data, key):
    n = len(data) // 4
    words = struct.unpack('<%dI' % n, data[:n * 4])
    out = []
    seed = 0xEEEEEEEE
    for w in words:
        seed = (seed + CRYPT[0x400 + (key & 0xFF)]) & MASK
        value = (w ^ ((key + seed) & MASK)) & MASK
        out.append(value)
        key = ((((~key) << 21) + 0x11111111) & MASK) | (key >> 11)
        seed = (value + seed + (seed << 5) + 3) & MASK
    return struct.pack('<%dI' % n, *out) + data[n * 4:]


FILE_IMPLODE = 0x00000100
FILE_COMPRESS = 0x00000200
FILE_ENCRYPTED = 0x00010000
FILE_FIX_KEY = 0x00020000
FILE_SINGLE_UNIT = 0x01000000
FILE_DELETE_MARKER = 0x02000000
FILE_SECTOR_CRC = 0x04000000
FILE_EXISTS = 0x80000000


class MpqError(Exception):
    pass


class Mpq:
    def __init__(self, path):
        self.path = Path(path)
        self.f = open(self.path, 'rb')
        data = self.f.read(0x200)
        start = data.find(b'MPQ\x1a')
        while start < 0:  # the header may sit at any 512-byte boundary
            more = self.f.read(0x200)
            if not more:
                raise MpqError('no MPQ header')
            data += more
            start = data.find(b'MPQ\x1a')
        self.base = start
        self.f.seek(start)
        (_, header_size, _, version, shift, hash_pos, block_pos,
         hash_count, block_count) = struct.unpack('<4sIIHHIIII', self.f.read(32))
        if version > 1:
            raise MpqError('MPQ format version %d is not supported' % version)
        hi_hash = hi_block = 0
        self.hi_block_table = None
        if version == 1:
            hi_block_pos, hi_hash, hi_block = struct.unpack('<QHH', self.f.read(12))
            if hi_block_pos:
                self.f.seek(self.base + hi_block_pos)
                self.hi_block_table = struct.unpack('<%dH' % block_count, self.f.read(2 * block_count))
        self.sector_size = 512 << shift
        self.hashes = self._table(hash_pos | (hi_hash << 32), hash_count, '(hash table)')
        self.blocks = self._table(block_pos | (hi_block << 32), block_count, '(block table)')

    def _table(self, pos, count, name):
        self.f.seek(self.base + pos)
        raw = decrypt(self.f.read(count * 16), hash_string(name, HASH_KEY))
        return [struct.unpack_from('<4I', raw, i * 16) for i in range(count)]

    def find(self, name):
        # Packers differ: some hash "data/global/x.txt" as written (D2RLoader packages seen so),
        # Blizzard's tools hash it with backslashes.
        for variant in dict.fromkeys((name, name.replace('/', '\\'))):
            block = self._find(variant)
            if block is not None:
                return block
        return None

    def _find(self, name):
        n = len(self.hashes)
        start = hash_string(name, HASH_OFFSET) % n
        a, b = hash_string(name, HASH_A), hash_string(name, HASH_B)
        for k in range(n):
            ha, hb, _locale_platform, block = self.hashes[(start + k) % n]
            if block == 0xFFFFFFFF:
                return None
            if ha == a and hb == b and block != 0xFFFFFFFE:
                return block
        return None

    def read(self, name):
        index = self.find(name)
        if index is None:
            raise KeyError(name)
        offset, csize, fsize, flags = self.blocks[index]
        if self.hi_block_table:
            offset |= self.hi_block_table[index] << 32
        if not flags & FILE_EXISTS or flags & FILE_DELETE_MARKER:
            raise KeyError(name)
        if fsize == 0:
            return b''  # empty files have no sector table
        packed = FILE_COMPRESS | FILE_IMPLODE
        key = 0
        if flags & FILE_ENCRYPTED:
            key = hash_string(name.replace('/', '\\').split('\\')[-1], HASH_KEY)
            if flags & FILE_FIX_KEY:
                key = ((key + offset) ^ fsize) & MASK
        self.f.seek(self.base + offset)
        raw = self.f.read(csize)
        if flags & FILE_SINGLE_UNIT or not flags & packed and not flags & FILE_ENCRYPTED and csize == fsize:
            if flags & FILE_ENCRYPTED:
                raw = decrypt(raw, key)
            return self._unpack(raw, fsize, flags, name) if flags & packed else raw[:fsize]
        sectors = (fsize + self.sector_size - 1) // self.sector_size
        if flags & packed:
            count = sectors + 1 + (1 if flags & FILE_SECTOR_CRC else 0)
            table = raw[:count * 4]
            if flags & FILE_ENCRYPTED:
                table = decrypt(table, (key - 1) & MASK)
            offsets = struct.unpack('<%dI' % count, table)
        else:
            offsets = [min(i * self.sector_size, csize) for i in range(sectors + 1)]
        out = bytearray()
        for i in range(sectors):
            chunk = raw[offsets[i]:offsets[i + 1]]
            if flags & FILE_ENCRYPTED:
                chunk = decrypt(chunk, (key + i) & MASK)
            want = min(self.sector_size, fsize - i * self.sector_size)
            out += self._unpack(chunk, want, flags, name) if flags & packed else chunk[:want]
        return bytes(out)

    @staticmethod
    def _unpack(chunk, want, flags, name):
        if len(chunk) >= want:
            return chunk[:want]
        if flags & FILE_IMPLODE:  # the old IMPLODE flag: no compression-type byte
            return explode(chunk, want)
        mask, body = chunk[0], chunk[1:]
        if mask == 0x08:
            return explode(body, want)
        if mask == 0x02:
            return zlib.decompress(body)
        if mask == 0x10:
            return bz2.decompress(body)
        if mask == 0x12:
            raise MpqError('%s: LZMA is not supported' % name)
        raise MpqError('%s: compression mask 0x%02X is not supported' % (name, mask))

    def names(self):
        try:
            text = self.read('(listfile)').decode('utf-8', 'replace')
        except KeyError:
            return []
        out = []
        for line in text.replace(';', '\n').replace('\r', '\n').split('\n'):
            line = line.strip()
            if line and line not in out:
                out.append(line)
        return out

    def live_blocks(self):
        return sum(1 for o, c, s, fl in self.blocks if fl & FILE_EXISTS and not fl & FILE_DELETE_MARKER)


# --------------------------------------------------------------------- PKWARE DCL "implode"
# Decoder written from the published description of the PKWARE Data Compression Library format
# (as used inside MPQ archives): a byte telling whether literals are Huffman coded, a byte with
# the dictionary size (4-6 = 1024-4096 bytes), then a bit stream read from the low bit up: 1 =
# a length/distance pair, 0 = a literal. The three Huffman code tables are fixed; they are
# stored below as (count - 1) << 4 | bit length runs, codes are sent bit-inverted.
_DCL_LIT = bytes([
    11, 124, 8, 7, 28, 7, 188, 13, 76, 4, 10, 8, 12, 10, 12, 10, 8, 23, 8, 9, 7, 6, 7, 8, 7, 6, 55, 8, 23, 24,
    12, 11, 7, 9, 11, 12, 6, 7, 22, 5, 7, 24, 6, 11, 9, 6, 7, 22, 7, 11, 38, 7, 9, 8, 25, 11, 8, 11, 9, 12, 8,
    12, 5, 38, 5, 38, 5, 11, 7, 5, 6, 21, 6, 10, 53, 8, 7, 24, 10, 27, 44, 253, 253, 253, 252, 252, 252, 13, 12,
    45, 12, 45, 12, 61, 12, 45, 44, 173])
_DCL_LEN = bytes([2, 35, 36, 53, 38, 23])
_DCL_DIST = bytes([2, 20, 53, 230, 247, 151, 248])
_DCL_BASE = (3, 2, 4, 5, 6, 7, 8, 9, 10, 12, 16, 24, 40, 72, 136, 264)
_DCL_EXTRA = (0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8)


def _dcl_table(runs, n):
    lengths = []
    for b in runs:
        lengths += [b & 15] * ((b >> 4) + 1)
    if len(lengths) != n:
        raise ValueError('bad DCL table')
    count = [0] * 14
    for ln in lengths:
        count[ln] += 1
    offs = [0] * 14
    for ln in range(1, 13):
        offs[ln + 1] = offs[ln] + count[ln]
    symbols = [0] * n
    for sym, ln in enumerate(lengths):
        if ln:
            symbols[offs[ln]] = sym
            offs[ln] += 1
    return count, symbols


_DCL_TABLES = None


class _Bits:
    __slots__ = ('data', 'pos', 'buf', 'cnt')

    def __init__(self, data):
        self.data, self.pos, self.buf, self.cnt = data, 0, 0, 0

    def bits(self, need):
        while self.cnt < need:
            if self.pos >= len(self.data):
                raise MpqError('PKWARE implode: data ends early')
            self.buf |= self.data[self.pos] << self.cnt
            self.pos += 1
            self.cnt += 8
        v = self.buf & ((1 << need) - 1)
        self.buf >>= need
        self.cnt -= need
        return v

    def decode(self, table):
        count, symbols = table
        code = first = index = 0
        for ln in range(1, 14):
            code |= self.bits(1) ^ 1
            c = count[ln]
            if code < first + c:
                return symbols[index + code - first]
            index += c
            first = (first + c) << 1
            code <<= 1
        raise MpqError('PKWARE implode: bad code')


def explode(data, want):
    global _DCL_TABLES
    if _DCL_TABLES is None:
        _DCL_TABLES = (_dcl_table(_DCL_LIT, 256), _dcl_table(_DCL_LEN, 16), _dcl_table(_DCL_DIST, 64))
    lit_t, len_t, dist_t = _DCL_TABLES
    s = _Bits(data)
    coded = s.bits(8)
    dict_bits = s.bits(8)
    if coded > 1 or not 4 <= dict_bits <= 6:
        raise MpqError('PKWARE implode: bad header')
    out = bytearray()
    while len(out) < want:
        if s.bits(1):
            sym = s.decode(len_t)
            length = _DCL_BASE[sym] + s.bits(_DCL_EXTRA[sym])
            if length == 519:
                break
            low = 2 if length == 2 else dict_bits
            dist = (s.decode(dist_t) << low) + s.bits(low) + 1
            if dist > len(out):
                raise MpqError('PKWARE implode: distance too far back')
            start = len(out) - dist
            for k in range(length):
                out.append(out[start + k])
        else:
            out.append(s.decode(lit_t) if coded else s.bits(8))
    return bytes(out[:want])


def extract(archive, out):
    mpq = Mpq(archive)
    names = [n for n in mpq.names() if not n.startswith('(')]
    named = {}
    for n in names:
        b = mpq.find(n)
        if b is not None:
            named[b] = n
    specials = sum(1 for n in ('(listfile)', '(attributes)', '(signature)') if mpq.find(n) is not None)
    unnamed = mpq.live_blocks() - len(named) - specials
    root = Path(out) / (Path(archive).stem + '.mpq')
    data_names = [n for n in named.values()]
    has_data = any(n.lower().replace('/', '\\').startswith('data\\') for n in data_names)
    written = 0
    for n in sorted(named.values()):
        rel = n.replace('\\', '/')
        if rel.lower() == 'modinfo.json':
            target = root / 'modinfo.json'
        elif has_data:
            target = root / rel
        else:
            target = root / 'data' / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(mpq.read(n))
        written += 1
    if not (root / 'modinfo.json').exists():
        (root / 'modinfo.json').write_text(json.dumps({'name': Path(archive).stem, 'savepath': Path(archive).stem + '/'},
                                                      indent=1), encoding='utf-8')
    return root, written, unnamed


def main(argv):
    if len(argv) >= 2 and argv[0] == 'list':
        mpq = Mpq(argv[1])
        names = mpq.names()
        print('%d named in (listfile), %d live blocks, sector size %d' % (len(names), mpq.live_blocks(), mpq.sector_size))
        kinds = {}
        for o, c, s, fl in mpq.blocks:
            if fl & FILE_EXISTS:
                kinds[fl & 0xFFFF0300] = kinds.get(fl & 0xFFFF0300, 0) + 1
        print('flags:', {hex(k): v for k, v in kinds.items()})
        for n in names[:40]:
            print('  ' + n)
    elif len(argv) == 3 and argv[0] == 'extract':
        root, written, unnamed = extract(argv[1], argv[2])
        print('%s: %d files written%s' % (root, written, '' if not unnamed else ', %d files not named in (listfile) left out' % unnamed))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
