"""Gives mod content that has no HD art the HD art of the vanilla content it looks like.

The D2R port of D2NX's "match classic sprites to HD art by content". D2R picks HD art through
name tables, and a mod row missing from them is drawn with its legacy 256-colour sprite even
when its graphics are vanilla ones:

  hd/character/monsters.json  monstats Id -> HD monster definition
  hd/items/items.json         base item code -> HD inventory sprite
  hd/items/uniques.json       unique name -> HD sprite (normal / uber / ultra)
  hd/items/sets.json          set item name -> HD sprite

This writes a D2RMM mod (default name HdArtMatch) that, when D2RMM installs it after every
other mod, fills in the missing entries:

  monsters   a row without HD whose animation token (monstats Code) is shared with a row
             that has HD art gets that art. A token the mod brought itself (its own
             global/monsters/<token> DCC files) is compared with the vanilla monsters' sprites;
             a copy or recolour gets the vanilla monster's HD art.
  items      a base item, unique or set item without HD whose inventory picture (invfile) is
             one a vanilla item with HD art uses gets that art. A picture the mod brought itself
             (global/items/<invfile>.dc6) is compared with the vanilla pictures the same way.

The name-based part runs inside D2RMM at install time, so it follows changes to the mod list.
The picture comparison runs here, once, and is stored in the mod as two alias tables; run this
again after adding mods that bring their own sprites.

  python HdMatch.py report --game <D2R> [--data <merged mod data>]
  python HdMatch.py build  --game <D2R> [--data <merged mod data>] [--out <D2RMM mods folder>\\HdArtMatch]

--data defaults to <D2R>\\mods\\D2RMM\\D2RMM.mpq\\data (what D2RMM last installed); vanilla
files come from the game archive. Nothing in the game folder is written by `report`.

Match rule for pictures: same size (within 2 pixels), the opaque pixels overlap by at least
92% (intersection over union), after lining the boxes up. That accepts copies and recolours and
rejects new art. Placeholder tokens (xx, and any token whose sprites are empty) are never matched.
"""
import argparse
import csv
import io
import json
import os
import re
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from d2r_casc import D2RArchive  # noqa: E402
import LegacySprite  # noqa: E402

PLACEHOLDER_TOKENS = {'xx', ''}
MIN_IOU = 0.92


# ---------------------------------------------------------------- sources

class Sources:
    """Merged mod data first, then the game archive."""

    def __init__(self, game, data):
        self.archive = D2RArchive(game)
        self.data = data

    def mod_has(self, path):
        return bool(self.data) and os.path.isfile(os.path.join(self.data, path.replace('/', os.sep)))

    def read(self, path, vanilla=False):
        if not vanilla and self.mod_has(path):
            with open(os.path.join(self.data, path.replace('/', os.sep)), 'rb') as f:
                return f.read()
        try:
            return self.archive.read(path)
        except Exception:
            return None

    def tsv(self, path, vanilla=False):
        raw = self.read(path, vanilla)
        if raw is None:
            return []
        text = raw.decode('latin1').replace('\r', '')
        rows = list(csv.reader(io.StringIO(text), delimiter='\t', quoting=csv.QUOTE_NONE))
        head = rows[0]
        return [dict(zip(head, r)) for r in rows[1:] if r and any(r)]

    def json(self, path, vanilla=False):
        raw = self.read(path, vanilla)
        if raw is None:
            return None
        text = re.sub(r',(\s*[}\]])', r'\1', raw.decode('utf-8-sig'))
        return json.loads(text)


def unique_key(name):
    """D2R's key for a unique or set item in hd/items/uniques.json and sets.json."""
    return re.sub(r'[^a-z0-9]+', '_', name.lower().replace("'", '')).strip('_')


def list_entries(doc):
    """[{"key": value}, ...] -> {key: value}"""
    out = {}
    for entry in doc or []:
        for k, v in entry.items():
            out[k] = v
    return out


# ---------------------------------------------------------------- DC6 (inventory pictures)

def dc6_first_frame(data):
    """Decodes frame 0 of a DC6 file into an H x W array of palette indices (-1 = transparent)."""
    if data is None or len(data) < 24:
        return None
    version, _flags, _enc, _term, dirs, frames = struct.unpack_from('<6I', data, 0)
    if version != 6 or dirs * frames == 0:
        return None
    ptr = struct.unpack_from('<I', data, 24)[0]
    flip, width, height, _ox, _oy, _unk, _next, length = struct.unpack_from('<8I', data, ptr)
    if width == 0 or height == 0 or width > 4096 or height > 4096:
        return None
    img = np.full((height, width), -1, dtype=np.int16)
    pos, end = ptr + 32, ptr + 32 + length
    x, y = 0, height - 1 if flip == 0 else 0
    step = -1 if flip == 0 else 1
    while pos < end and 0 <= y < height:
        b = data[pos]
        pos += 1
        if b == 0x80:
            x = 0
            y += step
        elif b & 0x80:
            x += b & 0x7F
        else:
            run = data[pos:pos + b]
            pos += b
            n = max(0, min(b, width - x))
            img[y, x:x + n] = np.frombuffer(run[:n], dtype=np.uint8)
            x += b
    return img


# ---------------------------------------------------------------- DCC (monster sprites)

def monster_picture(sources, token, vanilla):
    """A picture of the monster standing: mode NU (or A1, WL), direction 0, frame 0, all layers
    found for the token stacked. Returns an H x W index array (-1 transparent) or None."""
    for mode in ('nu', 'a1', 'wl'):
        layers = []
        for layer in ('tr', 'hd', 'lg', 'ra', 'la', 'rh', 'lh', 'sh', 's1', 's2', 's3', 's4'):
            for weapon in ('hth', '1hs', '1ht', '2hs', '2ht', 'bow', 'xbw', 'stf'):
                for comp in ('lit', 'med', 'hvy'):
                    path = f'global/monsters/{token}/{layer}/{token}{layer}{comp}{mode}{weapon}.dcc'
                    raw = sources.read(path, vanilla)
                    if raw is None:
                        continue
                    try:
                        dcc = LegacySprite.Dcc(raw)
                        frame = dcc.frames[0][0]
                    except Exception:
                        continue
                    layers.append(frame)
                    break
                else:
                    continue
                break
        if layers:
            x0 = min(f.box[0] for f in layers)
            y0 = min(f.box[1] for f in layers)
            x1 = max(f.box[2] for f in layers)
            y1 = max(f.box[3] for f in layers)
            img = np.full((y1 - y0 + 1, x1 - x0 + 1), -1, dtype=np.int16)
            for f in layers:
                px = np.asarray(f.pixels)
                h, w = px.shape
                sub = img[f.box[1] - y0:f.box[1] - y0 + h, f.box[0] - x0:f.box[0] - x0 + w]
                mask = px > 0
                sub[mask] = px[mask]
            return img
    return None


# ---------------------------------------------------------------- comparing pictures

def crop(img):
    if img is None:
        return None
    ys, xs = np.nonzero(img >= 0)
    if len(xs) < 8:
        return None
    return img[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def iou(a, b):
    """Overlap of the opaque pixels of two cropped pictures (top-left aligned, sizes within 2 px)."""
    if a is None or b is None:
        return 0.0
    if abs(a.shape[0] - b.shape[0]) > 2 or abs(a.shape[1] - b.shape[1]) > 2:
        return 0.0
    h, w = max(a.shape[0], b.shape[0]), max(a.shape[1], b.shape[1])
    ma = np.zeros((h, w), bool)
    mb = np.zeros((h, w), bool)
    ma[:a.shape[0], :a.shape[1]] = a >= 0
    mb[:b.shape[0], :b.shape[1]] = b >= 0
    union = np.logical_or(ma, mb).sum()
    return float(np.logical_and(ma, mb).sum()) / union if union else 0.0


def best_match(picture, candidates):
    """candidates: {name: cropped picture}. Returns (name, score) of the best one above MIN_IOU."""
    best, score = None, 0.0
    for name, other in candidates.items():
        s = iou(picture, other)
        if s > score:
            best, score = name, s
    return (best, score) if score >= MIN_IOU else (None, score)


# ---------------------------------------------------------------- analysis

def analyse(sources, log=print):
    vanilla_mon = {k.lower(): v for k, v in (sources.json('hd/character/monsters.json', vanilla=True) or {}).items()}
    merged_mon = {k.lower(): v for k, v in (sources.json('hd/character/monsters.json') or {}).items()}
    rows = sources.tsv('global/excel/monstats.txt')
    vanilla_rows = sources.tsv('global/excel/monstats.txt', vanilla=True)

    # tokens that have HD art (vanilla rows, so a mod remapping cannot mislead us)
    token_hd = {}
    for r in vanilla_rows:
        tok = r.get('Code', '').lower()
        if tok not in PLACEHOLDER_TOKENS and r.get('Id', '').lower() in vanilla_mon:
            token_hd.setdefault(tok, vanilla_mon[r['Id'].lower()])

    missing = [r for r in rows if r.get('Id') and r['Id'].lower() not in merged_mon]
    new_tokens = sorted({r.get('Code', '').lower() for r in missing} - set(token_hd) - PLACEHOLDER_TOKENS)
    alias_tokens = {}
    report = {'monsters': [], 'items': []}
    if new_tokens:
        log(f'monsters: comparing {len(new_tokens)} token(s) with the sprites of {len(token_hd)} HD monsters ...')
        vanilla_pics = {}
        for tok in token_hd:
            pic = crop(monster_picture(sources, tok, vanilla=True))
            if pic is not None:
                vanilla_pics[tok] = pic
        for tok in new_tokens:
            pic = crop(monster_picture(sources, tok, vanilla=False))
            if pic is None:
                report['monsters'].append({'token': tok, 'result': 'no sprite found'})
                continue
            match, score = best_match(pic, vanilla_pics)
            if match:
                alias_tokens[tok] = match
            report['monsters'].append({'token': tok, 'match': match, 'overlap': round(score, 3)})
    for r in missing:
        tok = r.get('Code', '').lower()
        target = token_hd.get(alias_tokens.get(tok, tok))
        report['monsters'].append({'id': r['Id'], 'token': tok, 'hd': target})

    # items: inventory pictures with HD art, from vanilla tables
    items = list_entries(sources.json('hd/items/items.json', vanilla=True))
    uniques = list_entries(sources.json('hd/items/uniques.json', vanilla=True))
    sets = list_entries(sources.json('hd/items/sets.json', vanilla=True))
    inv_asset = {}
    for table in ('weapons', 'armor', 'misc'):
        for r in sources.tsv(f'global/excel/{table}.txt', vanilla=True):
            code, inv = r.get('code', ''), r.get('invfile', '').lower()
            if code in items and inv:
                inv_asset.setdefault(inv, items[code]['asset'])
    for table, hd in (('uniqueitems', uniques), ('setitems', sets)):
        for r in sources.tsv(f'global/excel/{table}.txt', vanilla=True):
            inv, key = r.get('invfile', '').lower(), unique_key(r.get('index', ''))
            if inv and key in hd:
                inv_asset.setdefault(inv, hd[key]['normal'])

    merged_items = list_entries(sources.json('hd/items/items.json'))
    merged_uniques = list_entries(sources.json('hd/items/uniques.json'))
    merged_sets = list_entries(sources.json('hd/items/sets.json'))
    wanted = []  # (kind, name, invfile)
    for table in ('weapons', 'armor', 'misc'):
        for r in sources.tsv(f'global/excel/{table}.txt'):
            if r.get('code') and r['code'] not in merged_items and r.get('invfile'):
                wanted.append(('item', r['code'], r['invfile'].lower()))
    for table, hd, kind in (('uniqueitems', merged_uniques, 'unique'), ('setitems', merged_sets, 'set')):
        for r in sources.tsv(f'global/excel/{table}.txt'):
            if r.get('index') and r.get('invfile') and unique_key(r['index']) not in hd:
                wanted.append((kind, r['index'], r['invfile'].lower()))
    new_inv = sorted({inv for _, _, inv in wanted if inv not in inv_asset and sources.mod_has(f'global/items/{inv}.dc6')})
    alias_inv = {}
    if new_inv:
        log(f'items: comparing {len(new_inv)} picture(s) with {len(inv_asset)} vanilla pictures that have HD art ...')
        vanilla_pics = {}
        for inv in inv_asset:
            pic = crop(dc6_first_frame(sources.read(f'global/items/{inv}.dc6', vanilla=True)))
            if pic is not None:
                vanilla_pics[inv] = pic
        for inv in new_inv:
            pic = crop(dc6_first_frame(sources.read(f'global/items/{inv}.dc6')))
            match, score = best_match(pic, vanilla_pics)
            if match:
                alias_inv[inv] = match
            report['items'].append({'invfile': inv, 'match': match, 'overlap': round(score, 3)})
    for kind, name, inv in wanted:
        report['items'].append({'kind': kind, 'name': name, 'invfile': inv, 'hd': inv_asset.get(alias_inv.get(inv, inv))})
    return alias_tokens, alias_inv, report


# ---------------------------------------------------------------- the D2RMM mod

MOD_JS = r"""// HdArtMatch: gives mod content without HD art the HD art of the vanilla content it looks like.
// Generated by HdMatch.py (the D2R port of D2NX's content matching). Install it LAST.
// The alias tables below come from comparing pictures; the rest is worked out here at install time.
const ALIAS_TOKENS = __ALIAS_TOKENS__;   // mod animation token -> vanilla token with the same look
const ALIAS_INV = __ALIAS_INV__;         // mod inventory picture -> vanilla picture with the same look
const PLACEHOLDER = { xx: true, '': true };

function key(name) {
  return name.toLowerCase().replace(/'/g, '').replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
}
function entries(list) {
  const out = {};
  for (const e of list) for (const k of Object.keys(e)) out[k] = e[k];
  return out;
}
let added = { monsters: 0, items: 0, uniques: 0, sets: 0 };

if (config.monsters) {
  const path = 'hd\\character\\monsters.json';
  const hd = D2RMM.readJson(path);
  const lower = {};
  for (const k of Object.keys(hd)) lower[k.toLowerCase()] = hd[k];
  const rows = D2RMM.readTsv('global\\excel\\monstats.txt').rows;
  const tokenHd = {};
  for (const r of rows) {
    const tok = (r.Code || '').toLowerCase();
    if (!PLACEHOLDER[tok] && r.Id && lower[r.Id.toLowerCase()] && !tokenHd[tok]) tokenHd[tok] = lower[r.Id.toLowerCase()];
  }
  for (const r of rows) {
    if (!r.Id || lower[r.Id.toLowerCase()]) continue;
    const tok = (r.Code || '').toLowerCase();
    if (PLACEHOLDER[tok]) continue;
    const target = tokenHd[ALIAS_TOKENS[tok] || tok];
    if (target) { hd[r.Id.toLowerCase()] = target; lower[r.Id.toLowerCase()] = target; added.monsters++; }
  }
  D2RMM.writeJson(path, hd);
}

if (config.items) {
  const itemsPath = 'hd\\items\\items.json', uniquesPath = 'hd\\items\\uniques.json', setsPath = 'hd\\items\\sets.json';
  const items = D2RMM.readJson(itemsPath), uniques = D2RMM.readJson(uniquesPath), sets = D2RMM.readJson(setsPath);
  const itemMap = entries(items), uniqueMap = entries(uniques), setMap = entries(sets);
  const invAsset = {};
  const bases = [];
  for (const t of ['weapons', 'armor', 'misc']) {
    for (const r of D2RMM.readTsv(`global\\excel\\${t}.txt`).rows) {
      if (!r.code) continue;
      bases.push(r);
      const inv = (r.invfile || '').toLowerCase();
      if (inv && itemMap[r.code] && !invAsset[inv]) invAsset[inv] = itemMap[r.code].asset;
    }
  }
  const uniqueRows = D2RMM.readTsv('global\\excel\\uniqueitems.txt').rows;
  const setRows = D2RMM.readTsv('global\\excel\\setitems.txt').rows;
  for (const [rows, map] of [[uniqueRows, uniqueMap], [setRows, setMap]]) {
    for (const r of rows) {
      const inv = (r.invfile || '').toLowerCase();
      const e = r.index && map[key(r.index)];
      if (inv && e && e.normal && !invAsset[inv]) invAsset[inv] = e.normal;
    }
  }
  const assetFor = (inv) => invAsset[ALIAS_INV[inv] || inv];
  for (const r of bases) {
    const inv = (r.invfile || '').toLowerCase();
    const a = !itemMap[r.code] && inv && assetFor(inv);
    if (a) { items.push({ [r.code]: { asset: a } }); itemMap[r.code] = { asset: a }; added.items++; }
  }
  for (const [rows, map, list, kind] of [[uniqueRows, uniqueMap, uniques, 'uniques'], [setRows, setMap, sets, 'sets']]) {
    for (const r of rows) {
      if (!r.index || !r.invfile) continue;
      const k = key(r.index);
      const a = !map[k] && assetFor(r.invfile.toLowerCase());
      if (a) { list.push({ [k]: { normal: a, uber: a, ultra: a } }); map[k] = { normal: a }; added[kind]++; }
    }
  }
  D2RMM.writeJson(itemsPath, items);
  D2RMM.writeJson(uniquesPath, uniques);
  D2RMM.writeJson(setsPath, sets);
}

console.log(`HdArtMatch: HD art given to ${added.monsters} monsters, ${added.items} base items, ${added.uniques} uniques, ${added.sets} set items`);
"""

MOD_JSON = {
    'name': 'HD Art Match',
    'description': 'Gives mod monsters and items that have no HD art the HD art of the vanilla content '
                   'they look like (same animation token or inventory picture, or a copy/recolour of one). '
                   'Install it LAST. Re-run HdMatch.py build after adding mods with their own sprites.',
    'author': 'D2NX',
    'version': '1.0.0',
    'config': [
        {'id': 'monsters', 'type': 'checkbox', 'name': 'Monsters', 'description': 'Monsters without an HD model get the model of the matching vanilla monster.', 'defaultValue': True},
        {'id': 'items', 'type': 'checkbox', 'name': 'Items', 'description': 'Items, uniques and set items without HD art get the HD picture of the matching vanilla item.', 'defaultValue': True},
    ],
}


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('command', choices=['report', 'build'])
    p.add_argument('--game', required=True)
    p.add_argument('--data', help='merged mod data folder (default: what D2RMM last installed)')
    p.add_argument('--out', help='D2RMM mod folder to write (build)')
    a = p.parse_args(argv)
    data = a.data or os.path.join(a.game, 'mods', 'D2RMM', 'D2RMM.mpq', 'data')
    if not os.path.isdir(data):
        data = None
    sources = Sources(a.game, data)
    alias_tokens, alias_inv, report = analyse(sources)

    mons = [m for m in report['monsters'] if 'id' in m]
    items = [i for i in report['items'] if 'kind' in i]
    print(f"monsters without HD art: {len(mons)}, of which HD art found: {sum(1 for m in mons if m['hd'])}")
    for m in mons:
        print(f"  {m['id']:28} token {m['token']:4} -> {m['hd'] or '(none: new art or placeholder)'}")
    print(f"items without HD art: {len(items)}, of which HD art found: {sum(1 for i in items if i['hd'])}")
    for i in items:
        print(f"  {i['kind']:6} {i['name'][:40]:40} {i['invfile']:12} -> {i['hd'] or '(none: new art)'}")
    for m in report['monsters']:
        if 'id' not in m:
            print(f"  picture match, token {m['token']}: {m.get('match') or m.get('result')} ({m.get('overlap', '-')})")
    for i in report['items']:
        if 'kind' not in i:
            print(f"  picture match, invfile {i['invfile']}: {i['match']} ({i['overlap']})")

    if a.command == 'build':
        out = a.out or os.path.join(a.game, 'D2RMM Custom 2.0.2', 'mods', 'HdArtMatch')
        os.makedirs(out, exist_ok=True)
        js = MOD_JS.replace('__ALIAS_TOKENS__', json.dumps(alias_tokens, sort_keys=True)) \
                   .replace('__ALIAS_INV__', json.dumps(alias_inv, sort_keys=True))
        with open(os.path.join(out, 'mod.js'), 'w', newline='\n', encoding='utf-8') as f:
            f.write(js)
        with open(os.path.join(out, 'mod.json'), 'w', newline='\n', encoding='utf-8') as f:
            json.dump(MOD_JSON, f, indent=2)
        with open(os.path.join(out, 'hdmatch.report.json'), 'w', newline='\n', encoding='utf-8') as f:
            json.dump({'alias_tokens': alias_tokens, 'alias_inv': alias_inv, **report}, f, indent=1)
        print(f'wrote {out} (install it last in D2RMM)')


if __name__ == '__main__':
    main(sys.argv[1:])
