// Runs a mod.js made by ConvertDataMod.py with a mock D2RMM (used by ConvertDataMod.py --check).
//
//   node ConvertDataModCheck.js <mod folder> <game file cache> <out folder> [config json] [earlier folder]
//
// Load-order tests: [config json] is the mod's settings ('{"loadorderCells":"earlier"}'), and
// [earlier folder] stands for what mods above it left: its files are read before the game's, and
// count as already in the output (copyFile without overwrite skips them, listed in copies.skipped).
//
// Game files come from the cache ConvertDataMod.py filled (ModAssets.py). Files the mod writes
// (patched tables, merged strings) land in <out>; copies are only recorded, in <out>\copies.json
// ({data: [...], loader: [...]}), since a converted mod copies gigabytes.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const [modDir, cache, out, configJson, earlier] = process.argv.slice(2);
if (!out) {
  console.error('usage: node ConvertDataModCheck.js <mod folder> <game file cache> <out folder>');
  process.exit(2);
}
fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(out, { recursive: true });

const posix = (p) => p.split('\\').join('/');
const mem = new Map(); // posix data path -> { text } | { file }
const copies = { data: [], loader: [], skipped: [] };
const earlierFile = (key) => (earlier && fs.existsSync(path.join(earlier, key)) ? path.join(earlier, key) : null);

function load(p) {
  const key = posix(p);
  const m = mem.get(key);
  let text;
  if (m) text = m.text != null ? m.text : fs.readFileSync(m.file, 'utf8');
  else if (earlierFile(key)) text = fs.readFileSync(earlierFile(key), 'utf8');
  else {
    const f = path.join(cache, key);
    if (!fs.existsSync(f)) throw new Error('not in the game: ' + key);
    text = fs.readFileSync(f, 'utf8');
  }
  return text.replace(/^\uFEFF/, '');
}

function walk(src, dst, visit) {
  if (fs.statSync(src).isDirectory()) {
    for (const name of fs.readdirSync(src)) walk(path.join(src, name), dst + '/' + name, visit);
  } else visit(src, dst);
}

const D2RMM = {
  getVersion: () => 1.8,
  // CHECK_MODLIST='[{"id":"Other"},{"id":"Rebirth"}]' tests the load-order warnings
  getModList: () => (process.env.CHECK_MODLIST ? JSON.parse(process.env.CHECK_MODLIST) : []),
  getNextStringID: (() => {
    let n = 90000;
    return () => ++n;
  })(),
  readTsv(p, options) {
    let text = load(p);
    if (options && options.removeCarriageReturns) text = text.replace(/\r\n/g, '\n');
    const lines = text.split('\n');
    while (lines.length && lines[lines.length - 1] === '') lines.pop();
    const headers = lines[0].split('\t');
    const rows = lines.slice(1).map((line) => {
      const cells = line.split('\t');
      const row = {};
      headers.forEach((h, i) => (row[h] = cells[i] == null ? '' : cells[i]));
      return row;
    });
    return { headers, rows };
  },
  writeTsv(p, data) {
    const lines = [data.headers.join('\t')].concat(
      data.rows.map((r) => data.headers.map((h) => (r[h] == null ? '' : r[h])).join('\t'))
    );
    mem.set(posix(p), { text: lines.join('\n') + '\n', written: true });
  },
  readJson: (p) => JSON.parse(load(p)),
  writeJson: (p, data) => mem.set(posix(p), { text: JSON.stringify(data, null, 2), written: true }),
  readTxt: (p) => load(p),
  writeTxt: (p, text) => mem.set(posix(p), { text, written: true, scratch: true }),
  copyFile(src, dst, overwrite) {
    const from = path.join(modDir, src);
    if (!fs.existsSync(from)) throw new Error('copyFile: no ' + src);
    const d = posix(dst);
    if (d.startsWith('d2rmm-convert/')) {
      mem.set(d, { file: from });
      return;
    }
    walk(from, d, (file, target) => {
      if (target.startsWith('../../')) copies.loader.push(target.slice(6));
      else if (!overwrite && (mem.has(target) || earlierFile(target))) copies.skipped.push(target);
      else {
        copies.data.push(target);
        mem.set(target, { file });
      }
    });
  },
};

const code = fs.readFileSync(path.join(modDir, 'mod.js'), 'utf8');
const logs = [];
const console2 = {
  log: (...a) => logs.push(a.join(' ')),
  warn: (...a) => logs.push('warning: ' + a.join(' ')),
  error: (...a) => logs.push('error: ' + a.join(' ')),
  debug: () => {},
};
vm.runInNewContext(`(function(){const config = ${configJson || '{}'};\n${code}\n})()`, { D2RMM, console: console2 }, { filename: 'mod.js' });

for (const [key, m] of mem) {
  if (!m.written || m.scratch) continue;
  const f = path.join(out, key);
  fs.mkdirSync(path.dirname(f), { recursive: true });
  fs.writeFileSync(f, m.text);
}
fs.writeFileSync(path.join(out, 'copies.json'), JSON.stringify(copies));
console.log(logs.join('\n'));
