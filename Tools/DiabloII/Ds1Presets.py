"""List or move the monster spots of a .ds1 map (see README.md, "Monster spots in a map").

A map places a monster by number: the how-many-th row of the map's own act in
`global\\excel\\monpreset.txt` (the act is in the map's header, not the level's).
A map editor numbers the monsters it adds from the plain game's row count
(Act 3 has 39 rows, so the first added one is 39). A mod that adds rows to the
same act (Reimagined: Act 3 ids 39-42, Act 4 ids 28-33) uses the same numbers,
and D2RMM has no way to rewrite a map at install time. So the map's added
monsters are moved to high, fixed ids once, and the mod's mod.js fills the act
up to them with `place_nothing` rows.

    python Ds1Presets.py map.ds1 [map2.ds1 ...]     # what the maps use
    python Ds1Presets.py map.ds1 --move 39:64       # ids 39-63 go up by 25, in place

`--move FROM:TO` only touches ids from FROM up to TO - 1, so running it twice
changes nothing the second time. The file keeps its size; keep your own backup.
"""
import argparse
import collections
import struct
import sys

MONSTER = 1  # object type 1 = monpreset.txt, 2 = objpreset.txt


def read_objects(data):
    """Return (version, act, [(offset of the id, type, id, x, y), ...])."""
    pos = 0

    def i32():
        nonlocal pos
        value = struct.unpack_from('<i', data, pos)[0]
        pos += 4
        return value

    version = i32()
    width, height = i32() + 1, i32() + 1
    act = i32() + 1 if version >= 8 else 1
    tag_type = i32() if version >= 10 else 0
    if version >= 3:
        for _ in range(i32()):  # the map's tile files
            pos = data.index(b'\0', pos) + 1
    if 9 <= version <= 13:
        pos += 8
    walls = floors = 1
    if version >= 4:
        walls = i32()
        if version >= 16:
            floors = i32()
    # per wall layer its tiles and their orientations, the floors, the shadows, maybe the tags
    layers = walls * 2 + floors + 1 + (1 if tag_type in (1, 2) else 0)
    pos += layers * width * height * 4
    if version < 2:
        return version, act, []
    count = i32()
    size = 20 if version > 5 else 16
    if count < 0 or pos + count * size > len(data):
        raise ValueError('not a .ds1 this script understands (object list does not fit)')
    objects = []
    for _ in range(count):
        kind, number, x, y = struct.unpack_from('<4i', data, pos)
        objects.append((pos + 4, kind, number, x, y))
        pos += size
    return version, act, objects


def main():
    parser = argparse.ArgumentParser(description='List or move the monster spots of .ds1 maps.')
    parser.add_argument('maps', nargs='+', help='.ds1 files')
    parser.add_argument('--move', metavar='FROM:TO', help='move monster ids FROM..TO-1 up by TO-FROM, in place')
    args = parser.parse_args()

    move = None
    if args.move:
        try:
            first, target = (int(part) for part in args.move.split(':'))
        except ValueError:
            parser.error('--move takes FROM:TO, e.g. 39:64')
        if first < 0 or target <= first:
            parser.error('--move: TO has to be higher than FROM')
        move = (first, target)

    for path in args.maps:
        with open(path, 'rb') as handle:
            data = bytearray(handle.read())
        version, act, objects = read_objects(data)
        monsters = collections.Counter(number for _, kind, number, _, _ in objects if kind == MONSTER)
        print(f'{path}: version {version}, act {act}, {len(objects)} objects, {sum(monsters.values())} monster spots')
        print('  monster id x spots: ' + (', '.join(f'{number} x{monsters[number]}' for number in sorted(monsters)) or 'none'))
        if not move:
            continue
        first, target = move
        moving = [(offset, number) for offset, kind, number, _, _ in objects if kind == MONSTER and first <= number < target]
        taken = sorted({number + target - first for _, number in moving} & {number for number in monsters if number >= target})
        if taken:
            sys.exit(f'  not moved: id(s) {taken} are already used by this map')
        for offset, number in moving:
            struct.pack_into('<i', data, offset, number + target - first)
        if moving:
            with open(path, 'wb') as handle:
                handle.write(data)
        moved = sorted({number for _, number in moving})
        print(f'  moved {len(moving)} spot(s): ' + (', '.join(f'{number} -> {number + target - first}' for number in moved) or 'nothing in that range'))


if __name__ == '__main__':
    main()
