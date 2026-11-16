"""Diablo II: Resurrected `.skeleton` files <-> JSON.

A `.skeleton` is a Granny 3D file (see Granny.py) holding one skeleton (its
bones: name, parent, local transform, inverse world matrix, the Maya attributes
of the joint) and one model entry that names it. `.animations` files use the
same container and decode with the same commands.

usage:
  HdSkeleton.py info   <file> [--game <D2R folder>]
  HdSkeleton.py decode <file> <out.json> [--game <D2R folder>] [--strip]
  HdSkeleton.py encode <in.json> <out.skeleton>
  HdSkeleton.py check  <file> ... [--game <D2R folder>]

  info    prints the bone tree.
  decode  writes everything in the file as JSON: {"tag", "extra_tags", "type", "root"}.
          "type" is the file's own type description, "root" the data. --strip drops
          the Maya attribute dumps (ExtendedData), which are most of the file.
  encode  writes a JSON file from `decode` (edited or not) back as a .skeleton.
          Sections are stored unpacked, so the file is larger than the game's own.
  check   decodes, encodes and decodes again, and reports whether the data survived.

<file> is a file on disk or, with --game (or D2R_PATH), a path inside the game
archive such as hd/character/enemy/fallen1/skeleton/fallen1.skeleton.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import Granny  # noqa: E402


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


def strip_extended(node):
    """Removes ExtendedData values in place (the type keeps the member, so the file stays valid)."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == 'ExtendedData':
                node[key] = None
            else:
                strip_extended(value)
    elif isinstance(node, list):
        for value in node:
            strip_extended(value)


def to_document(data, strip=False):
    g = Granny.read(data)
    root = g.root()
    if strip:
        root = json.loads(json.dumps(root))      # own copy: shared objects must not be stripped twice over
        strip_extended(root)
    return {'tag': g.tag, 'extra_tags': list(g.extra_tags), 'type': g.describe(g.root_type), 'root': root}


def from_document(doc):
    return Granny.Writer(doc.get('tag', 0x80000039), tuple(doc.get('extra_tags', (0, 0, 0, 0)))) \
        .build(doc['type'], doc['root'])


def bones(root):
    """[(index, name, parent index, position, orientation)] of the first skeleton."""
    out = []
    for skeleton in root.get('Skeletons') or []:
        for i, b in enumerate(skeleton['Bones']):
            t = b['Transform']
            out.append((i, b['Name'], b['ParentIndex'], t['position'], t['orientation']))
        break
    return out


def same(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return a == b or (a != a and b != b)
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return list(a) == list(b) and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['info', 'decode', 'encode', 'check'])
    ap.add_argument('args', nargs='+')
    ap.add_argument('--game', default=os.environ.get('D2R_PATH'))
    ap.add_argument('--strip', action='store_true')
    a = ap.parse_args()

    if a.command == 'info':
        g = Granny.read(load(a.args[0], a.game))
        root = g.root()
        print(f"from   {root.get('FromFileName')}")
        tool = root.get('ArtToolInfo') or {}
        print(f"tool   {tool.get('FromArtToolName')}, {tool.get('UnitsPerMeter')} units per metre")
        print(f"packed {sum(len(s['data']) for s in g.sections)} bytes of data, checksum {'ok' if g.crc_ok else 'WRONG'}")
        rows = bones(root)
        depth = {}
        print(f'{len(rows)} bones')
        for i, name, parent, pos, _ in rows:
            depth[i] = depth.get(parent, -1) + 1
            print(f"{i:4} {'  ' * depth[i]}{name}   ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})")
    elif a.command == 'decode':
        if len(a.args) != 2:
            raise SystemExit('decode needs <file> <out.json>')
        doc = to_document(load(a.args[0], a.game), a.strip)
        with open(a.args[1], 'w', encoding='utf-8') as f:
            json.dump(doc, f, indent=1)
        print(f"{a.args[1]}: {len(bones(doc['root']))} bones")
    elif a.command == 'encode':
        if len(a.args) != 2:
            raise SystemExit('encode needs <in.json> <out.skeleton>')
        with open(a.args[0], encoding='utf-8') as f:
            data = from_document(json.load(f))
        Granny.read(data).root()                  # must read back
        with open(a.args[1], 'wb') as f:
            f.write(data)
        print(f'{a.args[1]}: {len(data)} bytes')
    else:
        failed = 0
        for path in a.args:
            data = load(path, a.game)
            doc = to_document(data)
            again = to_document(from_document(json.loads(json.dumps(doc))))
            ok = same(doc['root'], again['root']) and doc['type'] == again['type']
            failed += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {path}  {len(bones(doc['root']))} bones")
        sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
