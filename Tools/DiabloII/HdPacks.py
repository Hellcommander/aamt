"""Diablo II: Resurrected pack files that hold many small legacy files in one:

`global/tiles/<act>/combined_ds1.bin`   every .ds1 map of an act (act1-4, expansion)
    u32 count, then count x (u32 offset, u32 size, char[40] name relative to the act folder,
    zero padded), then the files end to end in table order. Each body is byte for byte the
    loose .ds1 of that name (80 of 80 compared).

`global/allcofs.bin`                    every .cof (3,616)
    u32 count, then count x (u32 key, u32 offset), then the files end to end; a file runs to
    the next offset. key = FNV-1a (32 bit) of the file's base name in lower case without
    ".cof" ("hbonhth"). The table is sorted by key. Every body equals the loose .cof (3,616 of
    3,616); files with the same base name in different folders share a key and are both stored.

`global/chars_cof.d2`, `global/cmncof_a1.d2` ... `_a7.d2`   older .cof packs (8 files)
    records end to end: i32 -1, i32 0, i32 size, char[8] name (7 characters, no ".cof"),
    i32 -1, then the .cof of that size. Some bodies differ from today's loose file of the
    same name (older copies).

`global/expfield.d2` is not a pack: 10 header bytes, then a 256 x 256 grid of bytes 0-7 (8 at
the centre): which of eight directions each point lies in as seen from the centre.

Whether the game reads these packs or the loose files when a mod changes a map or a
.cof has not been tested.

usage:
  HdPacks.py list    <pack> [--game <D2R folder>]
  HdPacks.py extract <pack> <out folder> [--game <D2R folder>]
  HdPacks.py build-ds1 <folder of .ds1 files> <out.bin>
allcofs entries carry no name, so `extract` names them by key (`<key>_<n>.cof`).
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from HdPhysics import load  # noqa: E402


def fnv1a(text):
    h = 0x811C9DC5
    for ch in text.encode('latin1'):
        h = ((h ^ ch) * 0x01000193) & 0xFFFFFFFF
    return h


def cof_key(path):
    return fnv1a(os.path.basename(path).lower().rsplit('.', 1)[0])


def read_ds1_pack(data):
    """-> [(name, bytes)]"""
    count = struct.unpack_from('<I', data, 0)[0]
    out = []
    for k in range(count):
        offset, size, name = struct.unpack_from('<II40s', data, 4 + 48 * k)
        out.append((name.split(b'\0')[0].decode('latin1'), data[offset:offset + size]))
    return out


def build_ds1_pack(files):
    """files: [(name, bytes)] in the order to store."""
    at = 4 + 48 * len(files)
    table = b''
    for name, body in files:
        raw = name.replace('\\', '/').encode('latin1')
        if len(raw) > 39:
            raise ValueError(f'{name}: the name field holds 39 characters')
        table += struct.pack('<II40s', at, len(body), raw)
        at += len(body)
    return struct.pack('<I', len(files)) + table + b''.join(body for _, body in files)


def read_cof_pack(data):
    """-> [(key, bytes)]"""
    count = struct.unpack_from('<I', data, 0)[0]
    table = [struct.unpack_from('<II', data, 4 + 8 * k) for k in range(count)]
    ends = sorted(offset for _, offset in table) + [len(data)]
    end = {ends[k]: ends[k + 1] for k in range(count)}
    return [(key, data[offset:end[offset]]) for key, offset in table]


def build_cof_pack(files):
    """files: [(key, bytes)]; stored sorted by key (equal keys keep their order)."""
    files = sorted(files, key=lambda f: f[0])
    at = 4 + 8 * len(files)
    table = b''
    for key, body in files:
        table += struct.pack('<II', key, at)
        at += len(body)
    return struct.pack('<I', len(files)) + table + b''.join(body for _, body in files)


def read_old_cof_pack(data):
    """-> [(name, bytes)] of a chars_cof.d2 / cmncof_aN.d2 file."""
    out, at = [], 0
    while at < len(data):
        first, zero, size, name, second = struct.unpack_from('<3i8si', data, at)
        if first != -1 or second != -1 or zero != 0 or at + 24 + size > len(data):
            raise ValueError(f'unexpected record at {at}')
        out.append((name.split(b'\0')[0].decode('latin1') + '.cof', data[at + 24:at + 24 + size]))
        at += 24 + size
    return out


def kind(data):
    if data[:8] == b'\xff\xff\xff\xff\0\0\0\0':
        return 'oldcof'
    count = struct.unpack_from('<I', data, 0)[0]
    return 'ds1' if 4 + 48 * count <= len(data) and struct.unpack_from('<I', data, 4)[0] == 4 + 48 * count else 'cof'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['list', 'extract', 'build-ds1'])
    ap.add_argument('args', nargs='+')
    ap.add_argument('--game', default=os.environ.get('D2R_PATH'))
    a = ap.parse_args()
    if a.command == 'build-ds1':
        folder = a.args[0]
        files = []
        for base, _, names in os.walk(folder):
            for name in names:
                if name.lower().endswith('.ds1'):
                    path = os.path.join(base, name)
                    with open(path, 'rb') as f:
                        files.append((os.path.relpath(path, folder).replace('\\', '/'), f.read()))
        files.sort(key=lambda f: f[0].lower())
        with open(a.args[1], 'wb') as f:
            f.write(build_ds1_pack(files))
        print(f'{a.args[1]}: {len(files)} files')
        return
    data = load(a.args[0], a.game)
    if kind(data) == 'ds1':
        files = read_ds1_pack(data)
    elif kind(data) == 'oldcof':
        seen, files = {}, []
        for name, body in read_old_cof_pack(data):
            seen[name] = seen.get(name, 0) + 1
            files.append((name if seen[name] == 1 else f'{name[:-4]}_{seen[name]}.cof', body))
    else:
        seen = {}
        files = []
        for key, body in read_cof_pack(data):
            seen[key] = seen.get(key, 0) + 1
            files.append((f'{key:08x}_{seen[key]}.cof', body))
    if a.command == 'list':
        for name, body in files:
            print(f'{len(body):8d}  {name}')
        print(f'{len(files)} files')
    else:
        if len(a.args) != 2:
            raise SystemExit('extract needs <pack> <out folder>')
        for name, body in files:
            path = os.path.join(a.args[1], name.replace('/', os.sep))
            os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
            with open(path, 'wb') as f:
                f.write(body)
        print(f'{a.args[1]}: {len(files)} files')


if __name__ == '__main__':
    main()
