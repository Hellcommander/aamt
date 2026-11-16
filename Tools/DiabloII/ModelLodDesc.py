"""Read and extend `hd/model_lod_desc.bin`, the HD client's index of every model.

The game looks a model up here before it loads it (D2Render model_asset_cache:
"Binary desc cache"). A model whose path is not in the index is never drawn, so
a mod that adds a model at a new path has to ship an index that lists it. A
model that replaces a stock file at the stock path needs nothing.

The index belongs to one game build: a patch that adds or changes stock models
changes it, and a mod that still ships the old one hides the patch's new
models. So nothing here is tied to a build:

- The layout is worked out from the file itself. The header gives three tables
  (models, LOD rows, mesh rows) and from them the record sizes. The fields this
  tool has to touch are found by what must be true of them:
    models  the hash is the one strictly rising column; the LOD count is the
            column that adds up to the number of LOD rows; the link to the LOD
            rows is the column whose values land on rows; the bounding box is
            six floats with min <= max
    lods    mesh count adds up to the number of mesh rows; link lands on rows
    meshes  six floats with min <= max
  Every other byte of a record is carried along untouched and, for a new model,
  copied from its donor. If a patch moves, adds or drops fields, the same rules
  find them again; if a rule no longer finds exactly one answer, the tool stops
  and says which.
- The path hash (FNV-1a 32 of "data/hd/.../torso.model", lower case, no _lodN)
  is checked against the game's own file list: if the stock models are no longer
  found under it, the tool stops instead of writing entries the game cannot find.
- A mod does not store a finished index as its source of truth. It stores
  `model_index.json`: which models it adds and each one's donor. `update`
  rebuilds `hd/model_lod_desc.bin` from the game's current index, the donor's
  current entry and the bounding boxes in the mod's own model files, and records
  which stock index it was built from. `check` says whether that is still the
  game's.

Layout seen in build 95032, for reference (little endian):
    header   3 x { u32 count, i32 offset relative to the offset field }
    models   44 bytes: u32 hash, f32 bbMin[3], bbMax[3], u32 flags, u32 lodCount, i32 lods, u32 ?
    lods     12 bytes: u32 ?, u32 meshCount, i32 meshes
    meshes   32 bytes: f32 bbMin[3], bbMax[3], u32 layer, u16 ?, u16 ?
    Links are relative to their own field.

Command line:
    python ModelLodDesc.py show   <index file> <data/hd/...model> [...]
    python ModelLodDesc.py layout <index file>
    python ModelLodDesc.py update --game <game folder> --mod <mod folder>
    python ModelLodDesc.py check  --game <game folder> --mod <mod folder>     (exit 1 = rebuild needed)
"""
import argparse
import hashlib
import json
import os
import struct
import sys

import numpy as np

MANIFEST = 'model_index.json'
INDEX = 'hd/model_lod_desc.bin'


class LayoutError(ValueError):
    pass


def path_hash(path):
    h = 0x811C9DC5
    for c in path.replace('\\', '/').lower().encode('utf-8'):
        h = ((h ^ c) * 0x01000193) & 0xFFFFFFFF
    return h


def _one(candidates, what):
    if len(candidates) != 1:
        found = 'none' if not candidates else f'{len(candidates)} (at bytes {candidates})'
        raise LayoutError(f'model index: expected one column for {what}, found {found}. '
                          'The file format changed in a way this tool cannot follow.')
    return candidates[0]


def _box_column(words_f, what):
    """Offset (in 4-byte words) of six floats that hold min x,y,z then max x,y,z."""
    rows, columns = words_f.shape
    best = []
    for k in range(columns - 5):
        with np.errstate(all='ignore'):
            block = words_f[:, k:k + 6].astype(np.float64)
            ok = np.isfinite(block).all(1) & (np.abs(block) < 1e7).all(1) & (block[:, :3] <= block[:, 3:] + 1e-4).all(1)
            # A real box column also has size: rule out columns of small integers read as floats.
            sized = (block[:, 3:] - block[:, :3]).max(1) > 1e-6
        if ok.mean() > 0.995 and (ok & sized).mean() > 0.5:
            best.append(k * 4)
    # Overlapping matches cannot both be right: a box is found once.
    return _one(best, what)


class ModelLodDesc:
    def __init__(self, data):
        if len(data) < 24:
            raise LayoutError('model index: file is too short')
        counts, offsets = [], []
        for k in range(3):
            count, rel = struct.unpack_from('<Ii', data, k * 8)
            counts.append(count)
            offsets.append(k * 8 + 4 + rel)
        ends = offsets[1:] + [len(data)]
        sizes = []
        for count, start, end in zip(counts, offsets, ends):
            if count == 0 or start < 24 or end <= start or (end - start) % count or ((end - start) // count) % 4:
                raise LayoutError('model index: the header no longer describes three tables of fixed-size records')
            sizes.append((end - start) // count)
        self.header_size = offsets[0]
        self.header = bytes(data[24:offsets[0]])        # anything a later build puts after the three table entries
        self.sizes = sizes
        raw = [np.frombuffer(data, dtype=np.uint8, count=c * s, offset=o).reshape(c, s).copy()
               for c, s, o in zip(counts, sizes, offsets)]
        self.models, self.lods, self.meshes = raw
        n0, n1, n2 = counts
        a0, a1, a2 = offsets

        def columns(table):
            return table.view('<u4'), table.view('<i4'), table.view('<f4')

        mu, mi, mf = columns(self.models)
        lu, li, lf = columns(self.lods)
        _, _, sf = columns(self.meshes)
        words0, words1 = sizes[0] // 4, sizes[1] // 4

        rising = [k * 4 for k in range(words0) if (np.diff(mu[:, k].astype(np.int64)) > 0).all()]
        self.f_hash = _one(rising, 'the path hash (the sorted column)')

        def links(signed, record_addr, target_start, target_size, target_count, counts_column):
            out = []
            for k in range(signed.shape[1]):
                target = record_addr + k * 4 + signed[:, k].astype(np.int64) - target_start
                used = counts_column > 0
                if not used.any():
                    continue
                t = target[used]
                if (t % target_size == 0).all() and (t >= 0).all() and ((t // target_size + counts_column[used]) <= target_count).all():
                    out.append(k * 4)
            return out

        count_columns = [k * 4 for k in range(words0) if k * 4 != self.f_hash and int(mu[:, k].astype(np.int64).sum()) == n1]
        self.f_lod_count = _one(count_columns, 'the LOD count (adds up to the number of LOD rows)')
        lod_counts = mu[:, self.f_lod_count // 4].astype(np.int64)
        addr0 = a0 + np.arange(n0, dtype=np.int64) * sizes[0]
        self.f_lod_link = _one(links(mi, addr0, a1, sizes[1], n1, lod_counts), 'the link to the LOD rows')

        mesh_columns = [k * 4 for k in range(words1) if int(lu[:, k].astype(np.int64).sum()) == n2]
        self.f_mesh_count = _one(mesh_columns, 'the mesh count (adds up to the number of mesh rows)')
        mesh_counts = lu[:, self.f_mesh_count // 4].astype(np.int64)
        addr1 = a1 + np.arange(n1, dtype=np.int64) * sizes[1]
        self.f_mesh_link = _one(links(li, addr1, a2, sizes[2], n2, mesh_counts), 'the link to the mesh rows')

        self.f_model_box = _box_column(mf, "the model's bounding box")
        self.f_mesh_box = _box_column(sf, "the mesh's bounding box")

        # Links become row numbers, so rows can be added freely.
        self.first_lod = (addr0 + self.f_lod_link + mi[:, self.f_lod_link // 4] - a1) // sizes[1]
        self.first_mesh = (addr1 + self.f_mesh_link + li[:, self.f_mesh_link // 4] - a2) // sizes[2]

    # --- views on the fields this tool understands ---
    def _u32(self, table, field):
        return table.view('<u4')[:, field // 4]

    @property
    def hashes(self):
        return self._u32(self.models, self.f_hash)

    def layout(self):
        return {
            'records': {'model': self.sizes[0], 'lod': self.sizes[1], 'mesh': self.sizes[2]},
            'model': {'hash': self.f_hash, 'box': self.f_model_box, 'lodCount': self.f_lod_count, 'lodLink': self.f_lod_link},
            'lod': {'meshCount': self.f_mesh_count, 'meshLink': self.f_mesh_link},
            'mesh': {'box': self.f_mesh_box},
            'counts': {'models': len(self.models), 'lods': len(self.lods), 'meshes': len(self.meshes)},
        }

    def check_hash(self, model_paths, need=0.9):
        """Stops if the stock models are not found under FNV-1a any more.

        model_paths: definition-style paths of models the game ships
        ("data/hd/.../torso.model"). Returns the share that was found.
        """
        paths = sorted(set(model_paths))
        if not paths:
            return None
        wanted = np.array([path_hash(p) for p in paths], dtype=np.uint32)
        share = float(np.isin(wanted, self.hashes).mean())
        if share < need:
            raise LayoutError(f'model index: only {share:.0%} of the game\'s models are found by their path hash. '
                              'The hash or the path form changed; entries written now would not be found by the game.')
        return share

    def find(self, path):
        h = path_hash(path)
        i = int(np.searchsorted(self.hashes, h))
        return i if i < len(self.models) and self.hashes[i] == h else None

    def _lod_rows(self, model):
        count = int(self._u32(self.models, self.f_lod_count)[model])
        start = int(self.first_lod[model])
        return range(start, start + count)

    def _mesh_rows(self, lod):
        count = int(self._u32(self.lods, self.f_mesh_count)[lod])
        start = int(self.first_mesh[lod])
        return range(start, start + count)

    def _box(self, table, field, row):
        return [float(v) for v in table.view('<f4')[row, field // 4:field // 4 + 6]]

    def describe(self, path):
        i = self.find(path)
        if i is None:
            return None
        return {'hash': int(self.hashes[i]), 'box': self._box(self.models, self.f_model_box, i),
                'record': self.models[i].tobytes().hex(),
                'lods': [[{'box': self._box(self.meshes, self.f_mesh_box, m), 'record': self.meshes[m].tobytes().hex()}
                          for m in self._mesh_rows(lod)] for lod in self._lod_rows(i)]}

    def clone(self, donor_path, new_path, boxes=None):
        """Adds (or replaces) an entry for new_path that copies donor_path's.

        boxes[lod][mesh] = (bbMin, bbMax) replaces a mesh's bounding box and the
        model's box becomes their union. Without boxes the donor's are kept.
        """
        d = self.find(donor_path)
        if d is None:
            raise KeyError(f'{donor_path} is not in the game\'s model index')
        lod_rows = list(self._lod_rows(d))
        if boxes is not None and len(boxes) != len(lod_rows):
            raise ValueError(f'{new_path}: {len(boxes)} LOD files, but its donor has {len(lod_rows)} in this game build')
        new_lods = self.lods[lod_rows].copy()
        new_meshes = []
        new_first_mesh = []
        total = len(self.meshes)
        for k, lod in enumerate(lod_rows):
            rows = self.meshes[list(self._mesh_rows(lod))].copy()
            if boxes is not None:
                if len(boxes[k]) != len(rows):
                    raise ValueError(f'{new_path} LOD {k}: {len(boxes[k])} meshes, but its donor has {len(rows)} in this game build')
                floats = rows.view('<f4')
                for r, (low, high) in enumerate(boxes[k]):
                    floats[r, self.f_mesh_box // 4:self.f_mesh_box // 4 + 6] = list(low) + list(high)
            new_first_mesh.append(total)
            total += len(rows)
            new_meshes.append(rows)
        entry = self.models[d:d + 1].copy()
        entry.view('<u4')[0, self.f_hash // 4] = path_hash(new_path)
        if boxes is not None and total > len(self.meshes):
            every = np.concatenate(new_meshes).view('<f4')[:, self.f_mesh_box // 4:self.f_mesh_box // 4 + 6]
            box = entry.view('<f4')[0, self.f_model_box // 4:self.f_model_box // 4 + 6]
            box[:3] = every[:, :3].min(0)
            box[3:] = every[:, 3:].max(0)
        old = self.find(new_path)
        if old is not None:
            # The old entry's LOD and mesh rows stay behind unused; they are a few dozen bytes.
            self.models = np.delete(self.models, old, axis=0)
            self.first_lod = np.delete(self.first_lod, old)
        at = int(np.searchsorted(self.hashes, path_hash(new_path)))
        self.models = np.insert(self.models, at, entry, axis=0)
        self.first_lod = np.insert(self.first_lod, at, len(self.lods))
        self.lods = np.concatenate([self.lods, new_lods])
        self.first_mesh = np.concatenate([self.first_mesh, np.array(new_first_mesh, dtype=np.int64)])
        if new_meshes:
            self.meshes = np.concatenate([self.meshes] + new_meshes)

    def to_bytes(self):
        n0, n1, n2 = len(self.models), len(self.lods), len(self.meshes)
        a0 = self.header_size
        a1 = a0 + n0 * self.sizes[0]
        a2 = a1 + n1 * self.sizes[1]
        models = self.models.copy()
        lods = self.lods.copy()
        models.view('<i4')[:, self.f_lod_link // 4] = (a1 + self.first_lod * self.sizes[1]) - (a0 + np.arange(n0, dtype=np.int64) * self.sizes[0] + self.f_lod_link)
        lods.view('<i4')[:, self.f_mesh_link // 4] = (a2 + self.first_mesh * self.sizes[2]) - (a1 + np.arange(n1, dtype=np.int64) * self.sizes[1] + self.f_mesh_link)
        head = struct.pack('<IiIiIi', n0, a0 - 4, n1, a1 - 12, n2, a2 - 20) + self.header
        return head + models.tobytes() + lods.tobytes() + self.meshes.tobytes()


# --- a mod's additions ---

def stock_model_paths(archive_files):
    """Definition-style model paths from the archive's file list (LOD suffix removed)."""
    out = set()
    for f in archive_files:
        if not f.endswith('.model') or not f.startswith('hd/'):
            continue
        stem = f[:-len('.model')]
        cut = stem.rfind('_lod')
        if cut != -1 and stem[cut + 4:].isdigit():
            stem = stem[:cut]
        out.add(f'data/{stem}.model')
    return out


def model_boxes(mod_dir, model_path):
    """[[(bbMin, bbMax) per mesh] per LOD] read from a mod's own model files."""
    import GrannyMesh
    stem = os.path.join(mod_dir, *model_path[len('data/'):-len('.model')].split('/'))
    files = []
    if os.path.isfile(stem + '.model'):
        files.append(stem + '.model')
    k = 0
    while os.path.isfile(f'{stem}_lod{k}.model'):
        files.append(f'{stem}_lod{k}.model')
        k += 1
    if not files:
        raise FileNotFoundError(f'{model_path}: no model files under {mod_dir}')
    return [[mesh.bounds() for mesh in GrannyMesh.Model(f).meshes] for f in files]


def read_manifest(mod_dir):
    path = os.path.join(mod_dir, MANIFEST)
    if not os.path.isfile(path):
        return None
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def build_for_mod(archive, mod_dir, additions=None, game_build=None, write=True):
    """Rebuilds <mod>/hd/model_lod_desc.bin from the game's current index.

    additions: [{"model": "data/hd/.../x.model", "donor": "data/hd/.../y.model"}];
    read from the mod's model_index.json when not given. Returns the manifest.
    """
    if additions is None:
        manifest = read_manifest(mod_dir)
        if manifest is None:
            raise FileNotFoundError(f'{os.path.join(mod_dir, MANIFEST)} not found: this mod adds no models to the index')
        additions = manifest['models']
    stock = archive.read(INDEX)
    desc = ModelLodDesc(stock)
    found = desc.check_hash(stock_model_paths(archive.list()))
    for item in additions:
        # "source": another mod's folder (relative to this one) that holds the model files: its
        # entries are carried in this mod's index too, because the index installed last wins.
        files_dir = os.path.normpath(os.path.join(mod_dir, item['source'])) if item.get('source') else mod_dir
        desc.clone(item['donor'], item['model'], model_boxes(files_dir, item['model']))
    built = desc.to_bytes()
    sources = sorted({a['source'] for a in additions if a.get('source')})
    manifest = {
        'about': 'Models this mod adds to hd/model_lod_desc.bin. Rebuild the index after a game patch: '
                 'python ModelLodDesc.py update --game <game> --mod <this folder>'
                 + (('. Also carries the models of ' + ', '.join(sources) + ' (entries with "source"), whose own '
                     'index it replaces: install this mod after them, and rebuild when their models change') if sources else ''),
        'models': [dict({'model': a['model'], 'donor': a['donor']}, **({'source': a['source']} if a.get('source') else {}))
                   for a in additions],
        'builtFrom': {'gameBuild': game_build, 'stockIndexBytes': len(stock), 'stockIndexSha256': hashlib.sha256(stock).hexdigest(),
                      'stockModelsFoundByHash': round(found, 4) if found is not None else None, 'layout': desc.layout()},
        'indexSha256': hashlib.sha256(built).hexdigest(),
    }
    if write:
        target = os.path.join(mod_dir, *INDEX.split('/'))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'wb') as f:
            f.write(built)
        with open(os.path.join(mod_dir, MANIFEST), 'w', encoding='utf-8', newline='\n') as f:
            json.dump(manifest, f, indent=2)
    return manifest


def check_mod(archive, mod_dir):
    """Problems that mean the mod's index must be rebuilt (empty list = up to date)."""
    manifest = read_manifest(mod_dir)
    if manifest is None:
        return []
    problems = []
    stock = archive.read(INDEX)
    built_from = manifest.get('builtFrom', {})
    if hashlib.sha256(stock).hexdigest() != built_from.get('stockIndexSha256'):
        problems.append('the game\'s model index changed since this mod\'s index was built (a game patch): '
                        'models the patch added would be invisible')
    target = os.path.join(mod_dir, *INDEX.split('/'))
    if not os.path.isfile(target):
        problems.append(f'{INDEX} is missing from the mod: its new models would be invisible')
    else:
        with open(target, 'rb') as f:
            shipped = f.read()
        if hashlib.sha256(shipped).hexdigest() != manifest.get('indexSha256'):
            problems.append(f'{INDEX} is not the file the manifest describes')
        try:
            desc = ModelLodDesc(shipped)
            for item in manifest['models']:
                if desc.find(item['model']) is None:
                    problems.append(f"{item['model']} is not listed in the mod's index")
        except LayoutError as error:
            problems.append(str(error))
    return problems


def _game_build(game):
    info = os.path.join(game, '.build.info')
    if not os.path.isfile(info):
        return None
    with open(info, encoding='latin1') as f:
        lines = f.read().splitlines()
    if len(lines) < 2:
        return None
    head = [h.split('!')[0] for h in lines[0].split('|')]
    return lines[1].split('|')[head.index('Version')] if 'Version' in head else None


def main(argv):
    parser = argparse.ArgumentParser(description='The HD model index (hd/model_lod_desc.bin).')
    sub = parser.add_subparsers(dest='command', required=True)
    show = sub.add_parser('show')
    show.add_argument('index')
    show.add_argument('paths', nargs='+')
    layout = sub.add_parser('layout')
    layout.add_argument('index')
    for name in ('update', 'check'):
        p = sub.add_parser(name)
        p.add_argument('--game', default=os.environ.get('D2R_PATH'), help='folder that contains D2R.exe (or set D2R_PATH)')
        p.add_argument('--casclib', default=os.environ.get('D2R_CASCLIB'))
        p.add_argument('--mod', required=True, help='the mod folder that holds model_index.json')
    args = parser.parse_args(argv)
    try:
        if args.command in ('show', 'layout'):
            with open(args.index, 'rb') as f:
                desc = ModelLodDesc(f.read())
            if args.command == 'layout':
                print(json.dumps(desc.layout(), indent=2))
                return 0
            for path in args.paths:
                info = desc.describe(path)
                if info is None:
                    print(f'{path}: not listed (hash {path_hash(path):08x})')
                    continue
                print(f"{path}: hash {info['hash']:08x} box {[round(v, 3) for v in info['box']]}")
                for k, meshes in enumerate(info['lods']):
                    for mesh in meshes:
                        print(f"  lod {k}: box {[round(v, 3) for v in mesh['box']]}")
            return 0
        if not args.game:
            parser.error('--game or D2R_PATH is needed')
        from d2r_casc import D2RArchive
        with D2RArchive(args.game, args.casclib) as archive:
            if args.command == 'check':
                problems = check_mod(archive, args.mod)
                if read_manifest(args.mod) is None:
                    print('This mod adds no models to the index.')
                    return 0
                for problem in problems:
                    print('REBUILD NEEDED: ' + problem)
                if not problems:
                    print('The mod\'s model index matches this game build.')
                return 1 if problems else 0
            manifest = build_for_mod(archive, args.mod, game_build=_game_build(args.game))
            built = manifest['builtFrom']
            print(f"Rebuilt {INDEX} for game build {built['gameBuild']}: {len(manifest['models'])} model(s) added, "
                  f"{built['stockModelsFoundByHash']:.1%} of stock models found by hash.")
            print('Layout found: ' + json.dumps(built['layout']['model']) + ' ' + json.dumps(built['layout']['lod']))
            return 0
    except (LayoutError, KeyError, FileNotFoundError, ValueError) as error:
        print('ERROR: ' + str(error).strip('"\''), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
