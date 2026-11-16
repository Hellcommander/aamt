// Runs D2RMM mod scripts without the game and checks what they produce.
//
//   node ModHarness.js --game <D2R folder> [options] <mod folder> [<mod folder> ...]
//
// The mods run in the order given against the game's own files, with a mock D2RMM. Every game
// file a mod reads is taken from the archive the moment it is asked for (ModAssets.py) and kept
// in a cache folder, so there is no list of "files this mod needs" to maintain: the run finds it
// out, and --manifest writes it down. Rows a mod adds are found by comparing with the game's
// tables, so the checks need no naming convention either.
//
// Options:
//   --game <folder>      folder that contains D2R.exe (or D2R_PATH)
//   --cache <folder>     where fetched game files are kept (default %LOCALAPPDATA%\D2RModAssets\vanilla)
//   --refresh            fetch again instead of using the cache (after a game update)
//   --config k=v         override a mod option for every mod given (repeatable), e.g. testMode=true
//   --max-page <n>       highest skilldesc SkillPage the SkillTab4 plugin draws (default 126, SkillTab4 0.7.0+)
//   --manifest <file>    write what was read, written, copied and depended on (JSON)
//   --dump [base]        print the non-empty columns of every row the mods added
//   --out <folder>       save every file the mods wrote there (compare two runs byte for byte)
//   --python <exe>       python to run ModAssets.py with (default "python")
//   --keep-going         like D2RMM: a mod that throws is rolled back and the next mod runs
//   --trace <file>       record every table cell, string field and file each mod changes, and write
//                        (JSON) which of them a later mod overwrote: the features a mod order loses
//
// Exit code 0 = no problems, 1 = problems, 2 = a mod script threw (with --keep-going: after
// every mod ran; the failed ones are listed).
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { spawnSync } = require('child_process');

// ---------------------------------------------------------------------------
// Arguments
// ---------------------------------------------------------------------------
const opt = { game: process.env.D2R_PATH, cache: null, refresh: false, config: {}, maxPage: 126, manifest: null, dump: null, python: 'python', mods: [] };
for (let i = 2; i < process.argv.length; i++) {
  const a = process.argv[i];
  const next = () => process.argv[++i];
  if (a === '--game') opt.game = next();
  else if (a === '--cache') opt.cache = next();
  else if (a === '--refresh') opt.refresh = true;
  else if (a === '--config') {
    const [k, ...v] = next().split('=');
    const text = v.join('=');
    opt.config[k] = text === 'true' ? true : text === 'false' ? false : /^-?\d+(\.\d+)?$/.test(text) ? Number(text) : text;
  } else if (a === '--max-page') opt.maxPage = Number(next());
  else if (a === '--manifest') opt.manifest = next();
  else if (a === '--out') opt.out = next();
  else if (a === '--dump') opt.dump = process.argv[i + 1] === 'base' ? next() : 'main';
  else if (a === '--python') opt.python = next();
  else if (a === '--keep-going') opt.keepGoing = true;
  else if (a === '--trace') opt.trace = next();
  else opt.mods.push(a);
}
if (!opt.game || !fs.existsSync(opt.game)) {
  console.error('Pass --game (or set D2R_PATH) to the folder that contains D2R.exe.');
  process.exit(2);
}
if (!opt.mods.length) {
  console.error('usage: node ModHarness.js --game <D2R folder> [options] <mod folder> [<mod folder> ...]');
  process.exit(2);
}
if (!opt.cache) opt.cache = path.join(process.env.LOCALAPPDATA || require('os').tmpdir(), 'D2RModAssets', 'vanilla');
fs.mkdirSync(opt.cache, { recursive: true });

// ---------------------------------------------------------------------------
// Game files, on demand
// ---------------------------------------------------------------------------
const ASSETS = path.join(__dirname, 'ModAssets.py');
const norm = (p) => p.replace(/\\/g, '/').replace(/^data\//i, '').toLowerCase();
const lower = (s) => String(s === undefined || s === null ? '' : s).toLowerCase();
const fetched = {}; // path -> true (in the cache) / false (not in the archive)
function assets(command, paths, extra) {
  const r = spawnSync(opt.python, [ASSETS, command, '--game', opt.game, ...(extra || []), '-'], { input: paths.join('\n'), encoding: 'utf8', maxBuffer: 1 << 26 });
  if (r.status !== 0) throw new Error(`ModAssets.py ${command} failed: ${r.stderr || r.error}`);
  return JSON.parse(r.stdout);
}
function fetchVanilla(paths) {
  const need = paths.map(norm).filter((p) => fetched[p] === undefined && (opt.refresh || !fs.existsSync(path.join(opt.cache, p))));
  paths.map(norm).forEach((p) => { if (fetched[p] === undefined && !need.includes(p)) fetched[p] = true; });
  if (!need.length) return;
  const result = assets('fetch', need, ['--out', opt.cache]);
  need.forEach((p) => { fetched[p] = result[p] !== null && result[p] !== undefined; });
}
function parseJsonc(text) {
  let out = '';
  let inStr = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inStr) {
      out += c;
      if (c === '\\') out += text[++i];
      else if (c === '"') inStr = false;
    } else if (c === '"') {
      inStr = true;
      out += c;
    } else if (c === '/' && text[i + 1] === '/') {
      while (i < text.length && text[i] !== '\n') i++;
      out += '\n';
    } else if (c === '/' && text[i + 1] === '*') {
      i = text.indexOf('*/', i) + 1;
    } else out += c;
  }
  return JSON.parse(out.replace(/,(\s*[}\]])/g, '$1'));
}
function parseTsv(text) {
  const lines = text.split(/\r?\n/);
  const headers = lines[0].split('\t');
  return {
    headers,
    rows: lines.slice(1).filter((l) => l !== '').map((l) => {
      const cells = l.split('\t');
      const row = {};
      headers.forEach((h, i) => { row[h] = cells[i] === undefined ? '' : cells[i]; });
      return row;
    }),
  };
}
// The game's own version of a file, parsed fresh on every call. null when the archive has none.
function vanilla(p, kind) {
  const key = norm(p);
  fetchVanilla([key]);
  if (!fetched[key]) return null;
  const full = path.join(opt.cache, key);
  if (kind === 'json') return parseJsonc(fs.readFileSync(full, 'utf8').replace(/^﻿/, ''));
  if (kind === 'tsv') return parseTsv(fs.readFileSync(full, 'latin1'));
  return fs.readFileSync(full, 'utf8');
}

// ---------------------------------------------------------------------------
// Mock D2RMM
// ---------------------------------------------------------------------------
const files = {}; // path -> current content (parsed)
const record = { read: new Set(), missing: new Set(), written: new Set(), copied: {} };
// --keep-going: what each file looked like before the running mod first touched it, so a mod
// that throws can be undone the way D2RMM rolls back its transaction.
let txn = null;
function touch(key) {
  if (!txn || txn.files.has(key)) return;
  txn.files.set(key, files[key] === undefined ? undefined : structuredClone(files[key]));
  if (!txn.copied.has(key)) txn.copied.set(key, record.copied[key]);
}
// Like D2RMM's file manager: a mod that writes or copies over a file another mod wrote, without
// having read or written that file itself first, gets D2RMM's "modifying ... without reading it
// first" warning (the earlier mods' changes are lost).
const fileOps = new Map(); // key -> { touched: Set of mod indexes, writers: [mod names] }
const opsOf = (key) => fileOps.get(key) || fileOps.set(key, { touched: new Set(), writers: [] }).get(key);
function noteWrite(key) {
  const ops = opsOf(key);
  const name = path.basename(currentMod || '');
  if (!ops.touched.has(modIndex)) {
    const others = ops.writers.filter((w) => w !== name);
    if (others.length) warn(`${name} is modifying ${key} without reading it first; ${[...new Set(others)].join(', ')} wrote it before and those changes are lost (D2RMM warns the same)`);
  }
  ops.touched.add(modIndex);
  ops.writers.push(name);
}
function load(p, kind) {
  const key = norm(p);
  opsOf(key).touched.add(modIndex);
  touch(key);
  if (files[key] !== undefined) return files[key];
  if (record.copied[key]) {
    // D2RMM reads a copied file back like any other (a mod may copy a whole table that later
    // mods edit, or copy its own data file in and read it).
    const text = fs.readFileSync(record.copied[key], kind === 'tsv' ? 'latin1' : 'utf8').replace(/^﻿/, '');
    files[key] = kind === 'json' ? parseJsonc(text) : kind === 'tsv' ? parseTsv(text) : text;
    record.read.add(key);
    return files[key];
  }
  const content = vanilla(key, kind);
  if (content === null) {
    record.missing.add(key);
    throw new Error(`no such file: ${p}`);
  }
  record.read.add(key);
  files[key] = content;
  return content;
}
// Like D2RMM, which writes a file out and parses it again for the next mod: a table keeps only
// its header columns (a mod may leave helper fields on rows, e.g. Remove Monster Immunities'
// "ResDm_Original"), every value becomes text, and no object is shared with the mod that wrote it.
function written(v) {
  if (v && Array.isArray(v.headers) && Array.isArray(v.rows)) {
    const headers = v.headers.map(String);
    return { headers, rows: v.rows.map((r) => Object.fromEntries(headers.map((h) => [h, r[h] === undefined || r[h] === null ? '' : String(r[h])]))) };
  }
  return typeof v === 'string' ? v : JSON.parse(JSON.stringify(v));
}
const write = (p, v) => { noteWrite(norm(p)); touch(norm(p)); files[norm(p)] = written(v); record.written.add(norm(p)); if (txn) txn.wrote.add(norm(p)); };
let nextId = 90000;
let currentMod = null;
function walk(dir, out, rel) {
  fs.readdirSync(dir, { withFileTypes: true }).forEach((e) => {
    const r = rel ? `${rel}/${e.name}` : e.name;
    if (e.isDirectory()) walk(path.join(dir, e.name), out, r);
    else out.push(r);
  });
  return out;
}
const D2RMM = {
  readTsv: (p) => load(p, 'tsv'),
  writeTsv: write,
  readTxt: (p) => load(p, 'txt'),
  writeTxt: write,
  readJson: (p) => load(p, 'json'),
  writeJson: write,
  getNextStringID: () => nextId++,
  copyFile: (src, dst, overwrite) => {
    const from = path.join(currentMod, src);
    if (!fs.existsSync(from)) {
      // D2RMM's copyFile returns without copying when the source is missing; do the same, but say so
      warn(`copyFile: ${src} is not in the mod folder (D2RMM copies nothing)`);
      return;
    }
    const list = fs.statSync(from).isDirectory() ? walk(from, [], '') : [''];
    list.forEach((rel) => {
      const key = norm(rel ? `${dst}/${rel}` : dst);
      // Like D2RMM: without overwrite a file that is already there stays.
      if (!overwrite && (files[key] !== undefined || record.copied[key])) return;
      noteWrite(key);
      touch(key);
      if (txn) txn.wrote.add(key);
      record.copied[key] = path.join(from, rel);
      delete files[key];
    });
  },
  // The D2RMM this install runs (D2RMM Custom 2.0.2).
  getVersion: () => 2.0,
  getFullVersion: () => [2, 0, 2],
  // The mods given, in install order; `installed` = already ran (as D2RMM reports it).
  getModList: () => modList.map((m, i) => ({ id: m.id, name: m.name, version: m.version, installed: i < modIndex && !failedMods.has(i), config: m.config })),
  error: (m) => { throw new Error(m); },
};
// --trace: every unit a mod changes (a table cell, a row's presence, a string's field, a layout's
// top-level entry, a whole other file) with the value it left there, in install order.
const traced = new Map(); // "file\u0000unit" -> [[mod index, value], ...]
const traceNames = [];
const PARSED = (k) => /^global\/excel\/.*\.txt$/.test(k) ? 'tsv'
  : /^local\/lng\/strings[^/]*\/.*\.json$/.test(k) || /^global\/ui\/layouts\/.*\.json$/.test(k) || k === 'hd/missiles/missiles.json' || k === 'hd/character/monsters.json' ? 'json' : null;
const digest = (text) => require('crypto').createHash('sha1').update(text).digest('hex').slice(0, 12);
// What a file holds given its parsed content (or undefined) and the mod file copied there (or undefined).
function stateOf(key, content, copiedFrom) {
  const kind = PARSED(key);
  if (content === undefined && copiedFrom) {
    if (!kind) return { whole: `copy of ${copiedFrom}` };
    const text = fs.readFileSync(copiedFrom, kind === 'tsv' ? 'latin1' : 'utf8').replace(/^\uFEFF/, '');
    try {
      content = kind === 'tsv' ? parseTsv(text) : parseJsonc(text);
    } catch (e) {
      return { whole: `copy of ${copiedFrom}` };
    }
  }
  if (content === undefined) content = kind ? vanilla(key, kind) : null;
  if (content === null || content === undefined) return { units: new Map() };
  if (typeof content === 'string' || !kind) return { whole: digest(typeof content === 'string' ? content : JSON.stringify(content)) };
  const units = new Map();
  if (Array.isArray(content.headers) && Array.isArray(content.rows)) {
    const seen = {};
    const id = content.headers[0];
    content.rows.forEach((r) => {
      const name = lower(r[id]);
      const row = `${name}#${(seen[name] = (seen[name] || 0) + 1)}`;
      units.set(`${row}\u0001*`, 'row');
      content.headers.forEach((h) => { if (h && r[h] !== undefined && r[h] !== '') units.set(`${row}\u0001${h}`, String(r[h])); });
    });
  } else if (Array.isArray(content)) {
    content.forEach((e, i) => {
      if (!e || typeof e !== 'object') return;
      const k = e.Key !== undefined ? `Key ${e.Key}` : `#${i}`;
      Object.keys(e).forEach((f) => { if (f !== 'id') units.set(`${k}\u0001${f}`, JSON.stringify(e[f])); });
    });
  } else {
    Object.keys(content).forEach((k) => units.set(k, JSON.stringify(content[k])));
  }
  return { units };
}
function diffInto(file, before, after, modIndexValue) {
  const add = (unit, value) => {
    const k = `${file}\u0000${unit}`;
    if (!traced.has(k)) traced.set(k, []);
    traced.get(k).push([modIndexValue, value]);
  };
  if (after.whole !== undefined || before.whole !== undefined) {
    if (after.whole !== before.whole) add('(whole file)', after.whole === undefined ? 'parsed' : after.whole);
    return;
  }
  after.units.forEach((v, u) => { if (before.units.get(u) !== v) add(u, v); });
  before.units.forEach((v, u) => { if (!after.units.has(u)) add(u, null); });
}
function traceMod(index, name, t) {
  traceNames[index] = name;
  t.files.forEach((pre, key) => {
    if (!t.wrote.has(key)) return;
    const preCopied = t.copied.has(key) ? t.copied.get(key) : record.copied[key];
    const before = stateOf(key, pre, pre === undefined ? preCopied : undefined);
    const after = stateOf(key, files[key], files[key] === undefined ? record.copied[key] : undefined);
    diffInto(key, before, after, index);
  });
}
function traceReport() {
  const finals = new Map(); // file -> final state
  const losses = new Map(); // "loser\u0000winner\u0000file" -> { count, examples }
  let units = 0;
  traced.forEach((setters, k) => {
    if (setters.length < 2) return;
    const [file, unit] = k.split('\u0000');
    if (!finals.has(file)) finals.set(file, stateOf(file, files[file], files[file] === undefined ? record.copied[file] : undefined));
    const fin = finals.get(file);
    const finalValue = unit === '(whole file)' ? fin.whole : fin.units ? (fin.units.has(unit) ? fin.units.get(unit) : null) : null;
    setters.forEach(([m, v], i) => {
      if (i === setters.length - 1 || v === finalValue || (unit === '(whole file)' && v === 'parsed')) return;
      // The last mod after this one that set the unit to what it ends as.
      const later = setters.slice(i + 1).filter(([, w]) => w === finalValue || unit === '(whole file)');
      const winner = later.length ? later[later.length - 1][0] : setters[setters.length - 1][0];
      if (winner === m) return;
      units++;
      const lk = `${m}\u0000${winner}\u0000${file}`;
      if (!losses.has(lk)) losses.set(lk, { count: 0, examples: [] });
      const l = losses.get(lk);
      l.count++;
      if (l.examples.length < 8) l.examples.push({ unit: unit.replace('\u0001', ' / '), lost: v, final: finalValue });
    });
  });
  const list = [...losses.entries()].map(([lk, l]) => {
    const [m, w, file] = lk.split('\u0000');
    return { lost: traceNames[m], to: traceNames[w], lostIndex: Number(m), toIndex: Number(w), file, count: l.count, examples: l.examples };
  }).sort((a, b) => a.lostIndex - b.lostIndex || b.count - a.count);
  fs.writeFileSync(opt.trace, `${JSON.stringify({ mods: traceNames, changedUnits: traced.size, overwrittenUnits: units, losses: list }, null, 1)}\n`);
  console.log(`trace: ${traced.size} changed units, ${units} overwritten by a later mod (${list.length} mod/file pairs), written to ${opt.trace}`);
}

// A mod's options as D2RMM hands them over: mod.json defaults, then config.json, then --config.
function modConfig(dir, meta) {
  const config = {};
  (meta.config || []).forEach(function each(c) {
    if (c.id) config[c.id] = c.defaultValue;
    (c.children || []).forEach(each);
  });
  const cfgFile = path.join(dir, 'config.json');
  if (fs.existsSync(cfgFile)) Object.assign(config, JSON.parse(fs.readFileSync(cfgFile, 'utf8')));
  Object.keys(opt.config).forEach((k) => { config[k] = opt.config[k]; });
  return config;
}
const modList = opt.mods.map((dir) => {
  const meta = JSON.parse(fs.readFileSync(path.join(dir, 'mod.json'), 'utf8'));
  return { id: path.basename(path.resolve(dir)), name: meta.name, version: meta.version, config: modConfig(dir, meta) };
});
let modIndex = 0;
const failedMods = new Map(); // index -> message (--keep-going)

// One archive call for the files nearly every run needs; anything else is fetched when asked for.
fetchVanilla([
  ...['skills', 'skilldesc', 'missiles', 'monstats', 'states', 'pettype'].flatMap((t) => [`global/excel/${t}.txt`, `global/excel/base/${t}.txt`]),
  'global/excel/itemstatcost.txt', 'hd/missiles/missiles.json', 'hd/character/monsters.json', 'global/ui/layouts/skillstreepanelhd.json',
  'local/lng/strings/skills.json', 'local/lng/strings/monsters.json', 'local/lng/strings/ui.json', 'local/lng/strings/item-modifiers.json',
]);

let problems = 0;
let warnings = 0;
const bad = (msg) => { problems++; console.log('  PROBLEM:', msg); };
const warn = (msg) => { warnings++; console.log('  warning:', msg); };

const ran = [];
for (const [index, dir] of opt.mods.entries()) {
  currentMod = dir;
  modIndex = index;
  const meta = JSON.parse(fs.readFileSync(path.join(dir, 'mod.json'), 'utf8'));
  const config = modConfig(dir, meta);
  try {
    // D2RMM runs a mod.js inside a function (so a top-level `return` is allowed); do the same.
    // The wrapper sits on the first line, so line numbers in errors stay the file's own.
    // A mod.ts (D2RMM compiles it) gets its types stripped by Node; one-file mods only, since
    // `import`s of other .ts files are not followed.
    let file = path.join(dir, 'mod.js');
    let source;
    if (fs.existsSync(file)) source = fs.readFileSync(file, 'utf8');
    else {
      file = path.join(dir, 'mod.ts');
      if (!fs.existsSync(file)) throw new Error('no mod.js or mod.ts');
      source = require('module').stripTypeScriptTypes(fs.readFileSync(file, 'utf8'));
    }
    const code = `(function(){${source}\n})()`;
    if (opt.keepGoing || opt.trace) txn = { files: new Map(), copied: new Map(), written: new Set(record.written), nextId, wrote: new Set() };
    vm.runInNewContext(code, { D2RMM, config, console }, { filename: file });
    if (opt.trace) traceMod(index, meta.name, txn);
    txn = null;
  } catch (e) {
    console.log(`${meta.name}: the script threw: ${e.stack || e}`);
    if (!opt.keepGoing) process.exit(2);
    // Undo what the mod changed, as D2RMM's transaction does, and go on with the next mod.
    txn.files.forEach((pre, key) => { if (pre === undefined) delete files[key]; else files[key] = pre; });
    txn.copied.forEach((pre, key) => { if (pre === undefined) delete record.copied[key]; else record.copied[key] = pre; });
    record.written.clear();
    txn.written.forEach((k) => record.written.add(k));
    nextId = txn.nextId;
    txn = null;
    failedMods.set(index, `${meta.name}: ${String(e && e.message ? e.message : e).split('\n')[0]}`);
    console.log(`FAILED (rolled back, going on): ${meta.name}`);
    continue;
  }
  ran.push(`${meta.name} ${meta.version}`);
  console.log(`ran ${meta.name} ${meta.version}  config ${JSON.stringify(config)}`);
}

// ---------------------------------------------------------------------------
// Checks. "New" = not in the game's own table.
// ---------------------------------------------------------------------------
const now = (p, kind) => {
  try { return load(p, kind); } catch (e) { return null; }
};
const strings = new Set();
const stringText = {};
['local/lng/strings/skills.json', 'local/lng/strings/monsters.json', 'local/lng/strings/ui.json', 'local/lng/strings/item-modifiers.json'].forEach((p) => {
  const list = now(p, 'json');
  if (!list) return;
  // The game's own files have a few doubles; only a double that involves a new entry counts.
  const stock = record.written.has(norm(p)) ? vanilla(p, 'json') || [] : null;
  const stockIds = new Set((stock || []).map((e) => e.id));
  const stockKeys = new Set((stock || []).map((e) => e.Key));
  const ids = new Set();
  const keys = new Set();
  list.forEach((e, i) => {
    if (stock && i >= stock.length) {
      if (ids.has(e.id) || stockIds.has(e.id)) bad(`${p}: string id ${e.id} is used twice (${e.Key})`);
      if (keys.has(e.Key) || stockKeys.has(e.Key)) bad(`${p}: string key ${e.Key} is defined twice`);
    }
    ids.add(e.id);
    keys.add(e.Key);
    strings.add(e.Key);
    stringText[e.Key] = e.enUS;
  });
});
const stats = new Set(now('global/excel/itemstatcost.txt', 'tsv').rows.map((r) => lower(r.Stat)));
const hdMissiles = now('hd/missiles/missiles.json', 'json') || {};
const layout = now('global/ui/layouts/skillstreepanelhd.json', 'json');
// The tree picture a page's Tab<page> widget shows: 'own' when a mod ships it (SkillTreeArt.py draws
// a frame in every cell of the page), 'stock' for a class picture, null when the widget has none.
const STOCK_TREE_ART = /^spells\/skill_trees\/(am|as|ba|dr|ne|pa|so|wa)skilltree$/;
const pageArtSeen = new Map();
const pageArt = (page) => {
  if (!pageArtSeen.has(String(page))) pageArtSeen.set(String(page), findPageArt(page));
  return pageArtSeen.get(String(page));
};
const findPageArt = (page) => {
  const tab = layout && layout.children.find((c) => c.name === `Tab${page}`);
  const img = tab && (tab.children || []).find((c) => c.type === 'ImageWidget' && c.fields && c.fields.filename);
  if (!img) return null;
  const name = norm(img.fields.filename);
  const key = `hd/global/ui/${name}.sprite`;
  if (record.copied[key] || files[key] !== undefined) return 'own';
  if (STOCK_TREE_ART.test(name)) return 'stock';
  bad(`layout Tab${page} shows ${img.fields.filename}, which no mod ships (${key}) and is no class tree picture`);
  return 'missing';
};
const SKILL_MISSILE_COLS = ['srvmissile', 'srvmissilea', 'srvmissileb', 'srvmissilec', 'cltmissile', 'cltmissilea', 'cltmissileb', 'cltmissilec', 'cltmissiled'];
const SUB_MISSILE_COLS = ['ExplosionMissile', 'SubMissile1', 'SubMissile2', 'SubMissile3', 'HitSubMissile1', 'HitSubMissile2', 'HitSubMissile3', 'HitSubMissile4', 'CltSubMissile1', 'CltSubMissile2', 'CltSubMissile3', 'CltHitSubMissile1', 'CltHitSubMissile2', 'CltHitSubMissile3', 'CltHitSubMissile4'];
const calcRefs = (v, fn) => (String(v).match(new RegExp(`${fn}\\('([^']+)'`, 'g')) || []).map((m) => m.slice(fn.length + 2, -1));
const missileRows = {};
const pagesByClass = {}; // page -> Set of classes that use it
const newMonsters = new Set();
const DIRS = ['global/excel/', 'global/excel/base/'];

DIRS.forEach((dir) => {
  const skills = now(`${dir}skills.txt`, 'tsv');
  if (!skills) return;
  console.log(`== ${dir}`);
  const get = (name) => now(`${dir}${name}.txt`, 'tsv') || { headers: [], rows: [] };
  const old = (name, col) => new Set(((vanilla(`${dir}${name}.txt`, 'tsv') || { rows: [] }).rows).map((r) => lower(r[col])));
  const desc = get('skilldesc');
  const missiles = get('missiles');
  const monstats = get('monstats');
  const states = get('states');
  const pettype = get('pettype');
  const oldSkills = old('skills', 'skill');
  const oldMissiles = old('missiles', 'Missile');
  const oldMonsters = old('monstats', 'Id');
  const oldPets = old('pettype', 'pet type');
  // AI names are code, the same for both rule sets.
  const oldAi = new Set(DIRS.flatMap((d) => ((vanilla(`${d}monstats.txt`, 'tsv') || { rows: [] }).rows).map((r) => lower(r.AI))));
  const skillBy = {};
  skills.rows.forEach((r) => { skillBy[lower(r.skill)] = r; });
  const missileBy = {};
  missiles.rows.forEach((r) => { missileBy[lower(r.Missile)] = r; });
  const monsterIds = new Set(monstats.rows.map((r) => lower(r.Id)));
  const stateIds = new Set(states.rows.map((r) => lower(r.state)));
  const pets = new Set(pettype.rows.map((r) => lower(r['pet type'])));
  const descBy = {};
  desc.rows.forEach((r) => {
    if (descBy[lower(r.skilldesc)]) bad(`skilldesc ${r.skilldesc} is defined twice`);
    descBy[lower(r.skilldesc)] = r;
  });
  if (Object.keys(skillBy).length !== skills.rows.length) bad('duplicate skill names');
  if (Object.keys(missileBy).length !== missiles.rows.length) bad('duplicate missile names');
  missileRows[dir] = missiles.rows.map((r) => r.Missile);

  const fresh = skills.rows.filter((r) => !oldSkills.has(lower(r.skill)));
  const freshNames = new Set(fresh.map((r) => lower(r.skill)));
  const added = missiles.rows.filter((r) => !oldMissiles.has(lower(r.Missile)));
  const addedNames = new Set(added.map((r) => lower(r.Missile)));
  console.log(`  skills ${skills.rows.length} (new ${fresh.length}), missiles ${missiles.rows.length} (new ${added.length})`);

  // Stock cells of each class tab, for "sits in a stock skill's cell".
  const stockCells = {};
  skills.rows.forEach((r) => {
    const d = descBy[lower(r.skilldesc)];
    if (r.charclass && d && oldSkills.has(lower(r.skill))) stockCells[`${r.charclass}/${d.SkillPage}/${d.SkillRow}/${d.SkillColumn}`] = r;
  });

  const grid = {};
  skills.rows.forEach((r, i) => { if (freshNames.has(lower(r.skill)) && '*Id' in r && r['*Id'] !== String(i)) bad(`skill ${r.skill} has *Id ${r['*Id']} at row ${i}`); });
  // Skill ID limits: the table itself takes 16-bit IDs (plugins check 0x7FFF), but the item stats
  // that name a skill (item_singleskill "+N to <skill>", item_nonclassskill oskills, item_aura) save
  // it in 9 bits (itemstatcost Save Param Bits), so a class skill past ID 511 cannot be named on
  // items unless the SkillLimits plugin (or a mod that raises those bits) widens them. Characters
  // saved with one width need the same width to read their items.
  const skillLimit = now('global/excel/itemstatcost.txt', 'tsv').rows.find((x) => lower(x.Stat) === 'item_singleskill');
  const paramBits = skillLimit && Number(skillLimit['Save Param Bits']) > 0 ? Number(skillLimit['Save Param Bits']) : 9;
  const itemMax = (1 << paramBits) - 1;
  skills.rows.forEach((r, i) => {
    if (!freshNames.has(lower(r.skill))) return;
    if (i > 0x7FFF) bad(`skill ${r.skill} is row ${i}, above 32767 (skill IDs are 16-bit)`);
    else if (r.charclass && r.skilldesc && i > itemMax) warn(`class skill ${r.skill} is row ${i}: items name skills in ${paramBits} bits (item_singleskill, oskills, auras; max ${itemMax}), so +skills need the SkillLimits plugin (or put class skills before hidden rows)`);
  });
  // State limits: the game reports an error past 511 states.txt rows (StateLimits lifts that to
  // 32768 once D2RCore's wide-state code is in place; per-unit state bits hold 32768), and the item
  // property `state` (stat 98) names its state in 8 bits (itemstatcost Save Param Bits; StateLimits
  // 0.2.0 widens it), so an item that sets a state past 255 gets the wrong state after a save.
  if (states.rows.length > 0x8000) bad(`states.txt has ${states.rows.length} rows; units hold at most 32768 states`);
  else if (states.rows.length > 511) warn(`states.txt has ${states.rows.length} rows (the game's limit is 511): needs D2RCore and the StateLimits plugin`);
  const stateStat = now('global/excel/itemstatcost.txt', 'tsv').rows.find((x) => lower(x.Stat) === 'state');
  const stateBits = stateStat && Number(stateStat['Save Param Bits']) > 0 ? Number(stateStat['Save Param Bits']) : 8;
  const stateMax = (1 << stateBits) - 1;
  const stateRow = {};
  states.rows.forEach((r, i) => { stateRow[lower(r.state)] = i; });
  ['uniqueitems', 'setitems', 'sets', 'runes', 'magicprefix', 'magicsuffix', 'automagic', 'cubemain'].forEach((t) => {
    if (!record.written.has(norm(`${dir}${t}.txt`))) return;
    const table = now(`${dir}${t}.txt`, 'tsv');
    if (!table) return;
    table.rows.forEach((r) => {
      table.headers.forEach((h, k) => {
        if (lower(r[h]) !== 'state' || !/code|prop|^mod \d+$/i.test(h)) return;
        // The parameter column: "mod 1 param" in cubemain, otherwise the next column (par1, PParam2a, T1Param1, mod1param...).
        const parCol = table.headers.includes(`${h} param`) ? `${h} param` : table.headers[k + 1];
        const par = String(r[parCol] || '').trim();
        if (!par) return;
        const id = /^\d+$/.test(par) ? Number(par) : stateRow[lower(par)];
        const who = `${t}.txt ${r[table.headers[0]]}.${h}`;
        if (id === undefined) bad(`${who}: state ${par} is not in states.txt`);
        else if (id > stateMax) warn(`${who}: state ${par} is row ${id}, but items name states in ${stateBits} bits (max ${stateMax}): needs StateLimits 0.2.0+ (state_param_bits)`);
      });
    });
  });
  fresh.forEach((r) => {
    const who = r.skill;
    ['reqskill1', 'reqskill2', 'reqskill3'].forEach((c) => {
      if (!r[c]) return;
      const need = skillBy[lower(r[c])];
      if (!need) return bad(`${who}.${c} = ${r[c]}: no such skill`);
      if (need.charclass !== r.charclass) bad(`${who}.${c} = ${r[c]} belongs to another class`);
      const a = descBy[lower(need.skilldesc)];
      const b = descBy[lower(r.skilldesc)];
      if (a && b && a.SkillPage !== b.SkillPage) bad(`${who}.${c} = ${r[c]} is on another skill page (${a.SkillPage} / ${b.SkillPage})`);
    });
    SKILL_MISSILE_COLS.forEach((c) => {
      if (!r[c]) return;
      const m = missileBy[lower(r[c])];
      if (!m) return bad(`${who}.${c} = ${r[c]}: no such missile`);
      if (m.Skill && lower(m.Skill) !== lower(who)) warn(`${who}.${c} = ${r[c]} takes its damage from the skill ${m.Skill}`);
    });
    if (r.summon && !monsterIds.has(lower(r.summon))) bad(`${who}.summon = ${r.summon}: no such monster`);
    if (r.pettype && !pets.has(lower(r.pettype))) bad(`${who}.pettype = ${r.pettype}: no such pet type`);
    if (r.summon && !r.pettype) warn(`${who} summons ${r.summon} without a pet type`);
    ['aurastate', 'auratargetstate', 'passivestate', 'State1', 'State2', 'State3'].forEach((c) => { if (r[c] && !stateIds.has(lower(r[c]))) bad(`${who}.${c} = ${r[c]}: no such state`); });
    for (let n = 1; n <= 6; n++) {
      ['aurastat', 'passivestat'].forEach((p) => { const v = r[`${p}${n}`]; if (v && !stats.has(lower(v))) bad(`${who}.${p}${n} = ${v}: no such stat`); });
      const calcOnly = (p, c) => { if (!r[`${p}${n}`] && r[`${c}${n}`]) bad(`${who}.${c}${n} has a calc but no stat`); };
      calcOnly('aurastat', 'aurastatcalc');
      calcOnly('passivestat', 'passivecalc');
    }
    for (let n = 1; n <= 5; n++) if (r[`sumskill${n}`] && !skillBy[lower(r[`sumskill${n}`])]) bad(`${who}.sumskill${n} = ${r[`sumskill${n}`]}: no such skill`);
    Object.keys(r).forEach((c) => {
      if (c.startsWith('*')) return;
      calcRefs(r[c], 'skill').concat(calcRefs(r[c], 'sksrc')).forEach((s) => { if (!skillBy[lower(s)]) bad(`${who}.${c} refers to unknown skill ${s}`); });
      calcRefs(r[c], 'miss').forEach((s) => { if (!missileBy[lower(s)]) bad(`${who}.${c} refers to unknown missile ${s}`); });
      calcRefs(r[c], 'stat').forEach((s) => { if (!stats.has(lower(s))) bad(`${who}.${c} refers to unknown stat ${s}`); });
    });
    if (!r.charclass) return;
    const d = descBy[lower(r.skilldesc)];
    if (!d) return bad(`${who}: no skilldesc row "${r.skilldesc}"`);
    const page = Number(d.SkillPage);
    const cell = `${r.charclass}/${d.SkillPage}/${d.SkillRow}/${d.SkillColumn}`;
    if (grid[cell]) bad(`${who} and ${grid[cell]} share the tree cell ${cell}`);
    if (stockCells[cell]) bad(`${who} sits on the stock skill ${stockCells[cell].skill} (cell ${cell})`);
    grid[cell] = who;
    if (!(Number(d.SkillRow) >= 1 && Number(d.SkillRow) <= 6 && Number(d.SkillColumn) >= 1 && Number(d.SkillColumn) <= 3)) bad(`${who}: tree cell row ${d.SkillRow} column ${d.SkillColumn} is outside 6 x 3`);
    if (page > 3) {
      (pagesByClass[page] = pagesByClass[page] || new Set()).add(r.charclass);
      if (page > opt.maxPage) bad(`${who}: SkillPage ${page} is above the plugin's highest page (${opt.maxPage})`);
      if (!['1', '2', '3'].includes(d.ListRow)) bad(`${who}: ListRow ${d.ListRow} must name the parent tab's page (1-3)`);
      else {
        const stock = stockCells[`${r.charclass}/${d.ListRow}/${d.SkillRow}/${d.SkillColumn}`];
        if (!stock && pageArt(page) !== 'own') warn(`${who} is in a cell (row ${d.SkillRow}, column ${d.SkillColumn}) where the parent tab has no skill, so the tab picture has no frame for it`);
      }
    } else if (!(page >= 1)) bad(`${who}: SkillPage ${d.SkillPage}`);
    ['str name', 'str short', 'str long', 'str alt'].forEach((c) => { if (!strings.has(d[c])) bad(`${who} skilldesc ${c} = ${d[c]}: no such string`); });
    Object.keys(d).forEach((c) => {
      const v = d[c];
      if (/^(desc|dsc2|dsc3)text[ab]\d+$/.test(c) && v && !strings.has(v)) bad(`${who} skilldesc ${c} = ${v}: no such string`);
      if (/^(desc|dsc2|dsc3)line\d+$/.test(c) && v && !d[c.replace('line', 'texta')]) bad(`${who} skilldesc ${c} has no text`);
      calcRefs(v, 'skill').concat(calcRefs(v, 'sksrc')).forEach((s) => { if (!skillBy[lower(s)]) bad(`${who} skilldesc ${c} refers to unknown skill ${s}`); });
      calcRefs(v, 'miss').forEach((s) => { if (!missileBy[lower(s)]) bad(`${who} skilldesc ${c} refers to unknown missile ${s}`); });
    });
    ['descmissile1', 'descmissile2', 'descmissile3'].forEach((c) => { if (d[c] && !missileBy[lower(d[c])]) bad(`${who} skilldesc ${c} = ${d[c]}: no such missile`); });
  });

  // Missiles.
  const noHd = [];
  missiles.rows.forEach((r, i) => { if (addedNames.has(lower(r.Missile)) && '*ID' in r && r['*ID'] !== String(i)) bad(`missile ${r.Missile} has *ID ${r['*ID']} at row ${i}`); });
  added.forEach((r) => {
    if (/\d$| /.test(r.Missile)) bad(`missile name "${r.Missile}" ends in a digit or has a space (the HD lookup rewrites those)`);
    if (r.Skill && !skillBy[lower(r.Skill)]) bad(`missile ${r.Missile}.Skill = ${r.Skill}: no such skill`);
    SUB_MISSILE_COLS.forEach((c) => {
      if (!r[c]) return;
      const sub = missileBy[lower(r[c])];
      if (!sub) return bad(`missile ${r.Missile}.${c} = ${r[c]}: no such missile`);
      if (r.Skill && sub.Skill && lower(sub.Skill) !== lower(r.Skill)) warn(`missile ${r.Missile}.${c} = ${r[c]} takes its damage from the skill ${sub.Skill}, not ${r.Skill}`);
    });
    Object.keys(r).forEach((c) => {
      calcRefs(r[c], 'skill').concat(calcRefs(r[c], 'sksrc')).forEach((s) => { if (!skillBy[lower(s)]) bad(`missile ${r.Missile}.${c} refers to unknown skill ${s}`); });
      calcRefs(r[c], 'miss').forEach((s) => { if (!missileBy[lower(s)]) bad(`missile ${r.Missile}.${c} refers to unknown missile ${s}`); });
    });
    // Padding rows only keep the two tables the same length.
    if (hdMissiles[r.Missile] === undefined && !/pad[a-z]*$/.test(r.Missile)) noHd.push(r.Missile);
  });
  if (noHd.length) console.log(`  new missiles without an HD entry (drawn with no effect): ${noHd.join(', ')}`);

  // Monsters and pets.
  const freshMon = monstats.rows.filter((r) => !oldMonsters.has(lower(r.Id)));
  const counted = monstats.rows.filter((r) => r.Id !== 'Expansion');
  freshMon.forEach((r) => {
    newMonsters.add(r.Id);
    if ('*hcIdx' in r && r['*hcIdx'] !== String(counted.indexOf(r))) bad(`monster ${r.Id} has *hcIdx ${r['*hcIdx']} but is row ${counted.indexOf(r)}`);
    if (r.AI && !oldAi.has(lower(r.AI))) bad(`monster ${r.Id}.AI = ${r.AI}: no stock monster uses that AI`);
    if (r.NameStr && !strings.has(r.NameStr)) bad(`monster ${r.Id}.NameStr = ${r.NameStr}: no such string`);
    for (let n = 1; n <= 8; n++) if (r[`Skill${n}`] && !skillBy[lower(r[`Skill${n}`])]) bad(`monster ${r.Id}.Skill${n} = ${r[`Skill${n}`]}: no such skill`);
    ['MissA1', 'MissA2', 'MissS1', 'MissS2', 'MissS3', 'MissS4', 'MissC', 'MissSQ'].forEach((c) => { if (r[c] && !missileBy[lower(r[c])]) bad(`monster ${r.Id}.${c} = ${r[c]}: no such missile`); });
    if (r.BaseId && !monsterIds.has(lower(r.BaseId))) bad(`monster ${r.Id}.BaseId = ${r.BaseId}: no such monster`);
    if (r.NextInClass && !monsterIds.has(lower(r.NextInClass))) bad(`monster ${r.Id}.NextInClass = ${r.NextInClass}: no such monster`);
  });
  if (monsterIds.size !== monstats.rows.length) bad('duplicate monster ids');
  pettype.rows.filter((r) => !oldPets.has(lower(r['pet type']))).forEach((r) => { if (r.name && !strings.has(r.name)) bad(`pet type ${r['pet type']}.name = ${r.name}: no such string`); });
  if (pets.size !== pettype.rows.length) bad('duplicate pet types');

  // Trees.
  const classes = [...new Set(fresh.map((r) => r.charclass).filter(Boolean))];
  classes.forEach((cls) => {
    const pages = [...new Set(Object.keys(grid).filter((k) => k.startsWith(`${cls}/`)).map((k) => k.split('/')[1]))].sort((a, b) => a - b);
    pages.forEach((page) => {
      console.log(`  ${cls} page ${page}:`);
      for (let row = 1; row <= 6; row++) console.log(`    ${[1, 2, 3].map((col) => (grid[`${cls}/${page}/${row}/${col}`] || '.').padEnd(20)).join(' ')}`);
    });
    console.log(`  ${cls} class skills: ${skills.rows.filter((r) => r.charclass === cls).length}`);
  });
  if (dir === DIRS[0]) {
    fresh.forEach((r) => {
      const d = descBy[lower(r.skilldesc)] || {};
      const req = [r.reqskill1, r.reqskill2, r.reqskill3].filter(Boolean).join(' + ');
      const mis = SKILL_MISSILE_COLS.map((c) => r[c]).filter(Boolean);
      console.log(`  ${r['*Id']} ${r.skill} | ${r.charclass || 'no class'} lvl ${r.reqlevel} | needs ${req || '-'} | page ${d.SkillPage} of tab ${d.ListRow} icon ${d.IconCel} | ${r.EType || (r.MinDam ? 'phys' : '-')} | ${[...new Set(mis)].join(',') || (r.summon ? `summons ${r.summon}` : '-')}`);
    });
  }
  if (opt.dump && (opt.dump === 'base') === (dir === DIRS[1])) {
    const show = (r, skip) => Object.keys(r).filter((k) => r[k] !== '' && k[0] !== '*' && !skip.includes(k)).map((k) => `${k}=${r[k]}`).join(' ');
    fresh.forEach((r) => console.log(`SKILL ${r.skill}: ${show(r, ['skill', 'cost mult', 'cost add', 'InGame', 'enhanceable', 'maxlvl'])}`));
    added.filter((r) => !/pad[a-z]*$/.test(r.Missile)).forEach((r) => console.log(`MISSILE ${r.Missile}: ${show(r, ['Missile', 'animrate', 'AnimSpeed', 'Red', 'Green', 'Blue', 'InitSteps'])}`));
    freshMon.forEach((r) => console.log(`MONSTER ${r.Id}: ${show(r, ['Id'])}`));
  }
});

// New missile rows must have the same row number in both tables (the HD client looks effects
// up by the main table's row number, also in a classic-rules game).
const a = missileRows[DIRS[0]];
const b = missileRows[DIRS[1]];
if (a && b) {
  const stock = new Set((vanilla(`${DIRS[0]}missiles.txt`, 'tsv') || { rows: [] }).rows.map((r) => lower(r.Missile)));
  a.forEach((n, i) => { if (!stock.has(lower(n)) && b[i] !== n) bad(`missile ${n} is row ${i} in the main table but ${b[i] === undefined ? 'nothing' : b[i]} is there in the base table`); });
  if (a.length !== b.length && a.some((n) => !stock.has(lower(n)))) bad(`missile tables differ in length: ${a.length} / ${b.length}`);
}

// Extra skill pages: one class per page number, and a tab and a label in the layout for each.
Object.keys(pagesByClass).forEach((page) => {
  const classes = [...pagesByClass[page]];
  if (classes.length > 1) bad(`SkillPage ${page} is used by more than one class (${classes.join(', ')}); the layout is shared, so every page number can be used once`);
  ['Tab', 'TextTab'].forEach((w) => { if (!layout || !layout.children.some((c) => c.name === `${w}${page}`)) bad(`the skill tree layout has no ${w}${page} for SkillPage ${page} (${classes.join(', ')})`); });
});
if (layout) {
  const seen = new Set();
  layout.children.forEach((c) => {
    if (seen.has(c.name)) bad(`the skill tree layout has two widgets named ${c.name}`);
    seen.add(c.name);
    const m = /^TextTab(\d+)$/.exec(c.name || '');
    if (!m || Number(m[1]) < 4) return;
    const key = String(c.fields.text || '').replace(/^@/, '');
    const r = c.fields.rect || {};
    console.log(`layout ${c.name}: "${stringText[key]}" at x ${r.x}, y ${r.y}${pagesByClass[m[1]] ? ` (${[...pagesByClass[m[1]]].join(', ')})` : ''}`);
    if (!strings.has(key)) bad(`layout ${c.name} text ${key}: no such string`);
    if (!pagesByClass[m[1]]) warn(`layout has ${c.name} but no skill is on SkillPage ${m[1]}`);
    pageArt(m[1]);
  });
}

// Extra tab labels, per class: the layout is shared, but SkillTab4 hides every page a class has
// no skills on, so only one class's labels are ever on screen together. Each label (its text box,
// its click area Tab<N>.activationRect and a SkillTabLayout plate TabPlate<N>) must stay clear of
// the class's other labels, the stock tabs, the tree picture, the skill counter's text and the
// right hinge, and must stay on screen. Coordinates are local to the right panel: it is 1162 x
// 1507 and its right edge is 232 left of the screen's right edge (RightPanelRect x -1394).
if (layout) {
  const SCREEN_RIGHT = 1394;
  const FIXED = [
    { what: 'stock tab strip', x: 130, y: 160, width: 888, height: 99 },
    { what: 'tree picture', x: 132, y: 260, width: 897, height: 1065 },
    { what: "skill counter's text", x: 91 + 972 * 0.3, y: 1388, width: 972 * 0.4, height: 60, soft: true },
    { what: 'right hinge', x: 1076, y: 630, width: 331, height: 297 },
  ];
  const PLATES = { 'panel\\waypoints\\waypoints_tab': { width: 174, height: 82 } };
  const byName = Object.fromEntries(layout.children.filter((c) => c.name).map((c) => [c.name, c]));
  // Fields may name a _profilehd variable ("$SkillTabClick22", SkillTabLayout); the HD profile is checked.
  const profile = now('global/ui/layouts/_profilehd.json', 'json') || {};
  const v = (x) => (typeof x === 'string' && x[0] === '$' && profile[x.slice(1)] !== undefined ? v(profile[x.slice(1)]) : x);
  const boxesOf = (page) => {
    const out = [];
    const text = byName[`TextTab${page}`];
    const tab = byName[`Tab${page}`];
    const plate = byName[`TabPlate${page}`];
    const box = (r) => (r && typeof r === 'object' && Number.isFinite(r.x) && Number.isFinite(r.y) ? r : null);
    [text && text.fields.rect, text && text.fields.style, tab && tab.fields.activationRect, plate && plate.fields.rect, plate && plate.fields.filename].forEach((f) => {
      if (typeof f === 'string' && f[0] === '$' && typeof v(f) === 'string' && v(f)[0] === '$' && !/^\$Style/.test(v(f))) bad(`layout page ${page}: ${f} is not defined in _profilehd.json`);
    });
    if (text && box(v(text.fields.rect))) out.push({ what: 'label', ...v(text.fields.rect) });
    if (tab && box(v(tab.fields.activationRect))) out.push({ what: 'click area', ...v(tab.fields.activationRect) });
    if (plate && box(v(plate.fields.rect))) {
      const r = v(plate.fields.rect);
      const size = PLATES[lower(v(plate.fields.filename))];
      const s = r.scale || 1;
      if (size) out.push({ what: 'plate', x: r.x, y: r.y, width: size.width * s, height: size.height * s });
    }
    return out;
  };
  const SLACK = 4; // stock labels touch the tree picture's bottom edge by a pixel or two
  const hit = (a, b) => a.x + SLACK < b.x + b.width && b.x + SLACK < a.x + a.width && a.y + SLACK < b.y + b.height && b.y + SLACK < a.y + a.height;
  const classPages = {};
  Object.keys(pagesByClass).forEach((page) => pagesByClass[page].forEach((cls) => (classPages[cls] = classPages[cls] || []).push(page)));
  Object.keys(classPages).sort().forEach((cls) => {
    const pages = classPages[cls].sort((x, y) => x - y);
    const label = (p) => `${stringText[String((byName[`TextTab${p}`] || { fields: {} }).fields.text || '').replace(/^@/, '')] || `page ${p}`} (TextTab${p})`;
    pages.forEach((p, i) => {
      const mine = boxesOf(p);
      mine.forEach((b) => {
        if (b.x < 0 || b.x + b.width > SCREEN_RIGHT || b.y < 0 || b.y + b.height > 1507) bad(`${cls}: ${label(p)} ${b.what} at x ${b.x}, y ${b.y}, ${b.width} x ${b.height} is off screen (panel 0..1507 high, screen edge at x ${SCREEN_RIGHT})`);
        // The counter's text is centred and its width depends on the number, so only a warning.
        FIXED.forEach((f) => { if (hit(b, f)) (f.soft ? warn : bad)(`${cls}: ${label(p)} ${b.what} at x ${b.x}, y ${b.y} ${f.soft ? 'may cover' : 'covers'} the ${f.what}`); });
      });
      pages.slice(i + 1).forEach((q) => {
        const theirs = boxesOf(q);
        if (mine.some((a) => theirs.some((b) => hit(a, b)))) bad(`${cls}: ${label(p)} and ${label(q)} overlap`);
      });
      // The label's text has to fit: 22 pt, about 12 px a letter, lines of 27 px (lineWrap is on).
      const text = mine.find((b) => b.what === 'label');
      const words = String(stringText[String((byName[`TextTab${p}`] || { fields: {} }).fields.text || '').replace(/^@/, '')] || '');
      const size = (v((byName[`TextTab${p}`] || { fields: {} }).fields.style) || {}).pointSize;
      const pt = Number.isFinite(size) ? size : 22;
      if (text && words) {
        const perLine = Math.max(1, Math.floor((text.width - 8) / (pt * 0.55)));
        let lines = 1;
        let used = 0;
        words.split(/\s+/).forEach((w) => {
          if (used && used + 1 + w.length > perLine) { lines++; used = w.length; } else used += (used ? 1 : 0) + w.length;
          if (w.length > perLine) lines += Math.ceil(w.length / perLine) - 1;
        });
        if (lines * pt * 1.2 > text.height + 2) warn(`${cls}: ${label(p)} needs about ${lines} line(s) of ${pt} pt but its box is ${text.width} x ${text.height}`);
      }
    });
    console.log(`tabs ${cls}: ${pages.length} extra page(s): ${pages.map((p) => { const t = byName[`TextTab${p}`]; const r = (t && t.fields.rect) || {}; const at = v(r) || {}; return `${p}@${at.x},${at.y}`; }).join(' ')}`);
  });
}

// HD: every file an HD definition written by a mod depends on must be in a mod folder or in the archive.
const toCheck = new Set();
const owners = {};
const need = (p, owner) => {
  const key = norm(p);
  // Animations and skeletons are stored under other names than the definitions give; not checked.
  if (!/\.(texture|particles|model|json)$/.test(key)) return;
  if (record.copied[key] || record.written.has(key)) return;
  // A model named without its level of detail is stored as <name>_lod0.model (the game's own
  // files are stored that way too; ModAssets.py reads the archive with the same rule).
  const lod0 = key.endsWith('.model') && !key.endsWith('_lod0.model') ? `${key.slice(0, -6)}_lod0.model` : null;
  if (lod0 && (record.copied[lod0] || record.written.has(lod0))) return;
  toCheck.add(key);
  (owners[key] = owners[key] || []).push(owner);
};
[...record.written].filter((k) => k.startsWith('hd/') && k.endsWith('.json')).forEach((k) => {
  const def = files[k];
  if (!def || typeof def !== 'object' || Array.isArray(def)) return;
  Object.keys(def.dependencies || {}).forEach((kind) => (def.dependencies[kind] || []).forEach((d) => { if (d && d.path) need(d.path, k); }));
  (def.entities || []).forEach((e) => (e.components || []).forEach((c) => { if (c.type === 'VfxDefinitionComponent' && c.filename) need(c.filename, k); }));
});
const vanillaHdMissiles = vanilla('hd/missiles/missiles.json', 'json') || {};
Object.keys(hdMissiles).forEach((name) => { if (typeof hdMissiles[name] === 'string' && vanillaHdMissiles[name] !== hdMissiles[name] && hdMissiles[name]) need(`hd/missiles/${hdMissiles[name]}.json`, `missiles.json entry ${name}`); });
const hdMon = now('hd/character/monsters.json', 'json') || {};
newMonsters.forEach((id) => { if (!hdMon[id]) warn(`monster ${id} has no HD body in hd/character/monsters.json`); });
// Files copied from a mod folder that name game files inside (recoloured particle files name their textures).
const EMBEDDED = /data\/hd\/[A-Za-z0-9_/-]+?\.(?:texture|particles|model)/g;
Object.keys(record.copied).filter((k) => k.endsWith('.particles')).forEach((k) => {
  (fs.readFileSync(record.copied[k], 'latin1').match(EMBEDDED) || []).forEach((p) => need(p, k));
});
if (toCheck.size) {
  const exists = assets('exists', [...toCheck]);
  Object.keys(exists).forEach((p) => { if (!exists[p]) bad(`${owners[p][0]} needs ${p}, which is neither in a mod folder nor in the game archive`); });
}
console.log(`HD: ${[...record.written].filter((k) => /^hd\/missiles\/.+\.json$/.test(k) && k !== 'hd/missiles/missiles.json').length} own missile definitions, ${Object.keys(record.copied).length} files copied from mod folders, ${toCheck.size} game files they depend on checked`);

// PetAI plugin tables (<game>\mods\PetAI): all four, checked the way the plugin (0.6.0) reads them.
// Format: plain line-feed text, final line feed, a header with exactly the plugin's columns (the
// loader rejects a file that lacks one), numbers only. Values: what the plugin would skip or
// misread, and rows that do not point at what they mean to (monster rows, skill slots, routines).
{
  const PETAI_TABLES = {
    rules: ['monster', 'slot', 'skillid', 'chance', 'enemy', 'maxdist', 'attarget', 'cooldown'],
    nearrules: ['monster', 'near', 'dist', 'slot', 'cooldown'],
    springrules: ['monster', 'trigger', 'dist', 'skill', 'levelskill', 'count'],
    commandrules: ['skill', 'monster', 'slot', 'range', 'window', 'attarget'],
  };
  const PETAI_MAX_ROWS = 1024; // per table and folder since 0.6.0 (0.5.0: 256, commands 1024)
  DIRS.forEach((dir) => {
    const read = (name) => {
      const text = files[`${dir}d2rloader/petai/${name}.txt`];
      if (typeof text !== 'string') return null;
      const where = `${dir}d2rloader/petai/${name}.txt`;
      if (!text.endsWith('\n') || /[^\x20-\x7E\t\n]/.test(text)) bad(`${where}: not plain line-feed text ending with a line feed (the loader rejects it)`);
      const lines = text.replace(/\n$/, '').split('\n').map((l) => l.split('\t'));
      const head = lines[0].map((h) => h.trim().toLowerCase());
      const want = PETAI_TABLES[name];
      const missing = want.filter((c) => !head.includes(c));
      const extra = head.filter((c) => !want.includes(c));
      if (missing.length || extra.length) bad(`${where}: header must be exactly ${want.join(', ')}${missing.length ? ` (missing ${missing.join(', ')})` : ''}${extra.length ? ` (unknown ${extra.join(', ')})` : ''}`);
      const rows = [];
      lines.slice(1).forEach((cells, i) => {
        if (cells.length !== head.length || cells.some((c) => !/^\d+$/.test(c))) return bad(`${where}: row ${i + 1} is malformed (numbers only, one per column)`);
        rows.push({ n: i + 1, ...Object.fromEntries(head.map((h, k) => [h, Number(cells[k])])) });
      });
      if (rows.length > PETAI_MAX_ROWS) bad(`${where}: ${rows.length} rows; PetAI reads at most ${PETAI_MAX_ROWS} per folder and ignores the whole table beyond that`);
      else if (name !== 'commandrules' && rows.length > 256) warn(`${where}: ${rows.length} rows need PetAI 0.6.0 (0.5.0 ignores a table over 256 rows)`);
      return { where, rows };
    };
    const monsters = now(`${dir}monstats.txt`, 'tsv').rows.filter((r) => r.Id !== 'Expansion');
    const skillRows = now(`${dir}skills.txt`, 'tsv').rows.filter((r) => r.skill !== 'Expansion');
    const slotSkill = (mon, slot) => (mon && slot >= 1 && slot <= 8 && mon[`Skill${slot}`] && mon[`Sk${slot}mode`] ? mon[`Skill${slot}`] : null);

    const rules = read('rules');
    (rules ? rules.rows : []).forEach((r) => {
      const mon = monsters[r.monster];
      const skill = skillRows[r.skillid];
      if (r.slot < 1 || r.slot > 8 || r.chance === 0) return bad(`${rules.where}: row ${r.n}: slot must be 1-8 and chance above 0 (the plugin skips it)`);
      if (!mon || !skill || lower(slotSkill(mon, r.slot)) !== lower(skill.skill)) return bad(`${rules.where}: row ${r.n} does not match its monster (Skill${r.slot} of monster row ${r.monster} must be skill row ${r.skillid}, with a mode)`);
      if (r.chance > 100) warn(`${rules.where}: row ${r.n}: chance ${r.chance} is over 100`);
      if (r.attarget > 1) warn(`${rules.where}: row ${r.n}: attarget ${r.attarget} reads as 1`);
      const when = r.enemy >= 2 ? `with ${r.enemy}+ enemies within ${r.maxdist || 10} (PetAI 0.6.0+; older: any target)` : r.enemy === 1 ? `with a target${r.maxdist ? ` within ${r.maxdist}` : ''}` : 'any turn';
      console.log(`  ${dir} PetAI rule: ${mon.Id} uses ${skill.skill} (Skill${r.slot}, ${mon[`Sk${r.slot}mode`]}) ${when}, chance ${r.chance}, cooldown ${r.cooldown}`);
    });

    const near = read('nearrules');
    (near ? near.rows : []).forEach((r) => {
      const mon = monsters[r.monster];
      const other = monsters[r.near];
      if (r.dist === 0 || r.slot > 8) return bad(`${near.where}: row ${r.n}: dist must be above 0 and slot 0-8 (the plugin skips it)`);
      if (!mon || !other) return bad(`${near.where}: row ${r.n}: monster row ${!mon ? r.monster : r.near} does not exist`);
      if (r.slot > 0 && !slotSkill(mon, r.slot)) return bad(`${near.where}: row ${r.n}: ${mon.Id} has no Skill${r.slot} with a mode`);
      if (!mon.AI) warn(`${near.where}: row ${r.n}: ${mon.Id} has no AI, so it never gets the turn the rule needs`);
      console.log(`  ${dir} PetAI near rule: ${mon.Id} near ${other.Id} (within ${r.dist}): ${r.slot === 0 ? 'dies' : `uses ${slotSkill(mon, r.slot)}`}`);
    });

    const spring = read('springrules');
    (spring ? spring.rows : []).forEach((r) => {
      const mon = monsters[r.monster];
      const skill = skillRows[r.skill];
      const level = r.levelskill ? skillRows[r.levelskill] : skill;
      if (r.trigger < 1 || r.trigger > 3 || ((r.trigger & 1) && r.dist === 0) || r.count < 1 || r.count > 20) return bad(`${spring.where}: row ${r.n}: trigger 1-3, dist above 0 for touch, count 1-20 (the plugin skips it)`);
      if (!mon) return bad(`${spring.where}: row ${r.n}: monster row ${r.monster} does not exist`);
      if (!skill || !skill.summon || !skill.pettype) return bad(`${spring.where}: row ${r.n}: skill row ${r.skill} must have summon and pettype`);
      if (!level) return bad(`${spring.where}: row ${r.n}: levelskill row ${r.levelskill} does not exist`);
      console.log(`  ${dir} PetAI spring: ${mon.Id} (${['', 'touch', 'death', 'touch or death'][r.trigger]}) summons ${r.count} x ${skill.summon} via ${skill.skill} at ${level.skill}'s level`);
    });

    const commands = read('commandrules');
    const bySkill = {};
    (commands ? commands.rows : []).forEach((r) => {
      const mon = monsters[r.monster];
      const skill = skillRows[r.skill];
      if (r.skill === 0 || r.slot > 10 || r.window > 750) return bad(`${commands.where}: row ${r.n}: skill above 0, slot 0-10, window at most 750 (the plugin skips it)`);
      if (!skill || String(skill.srvdofunc) !== '179') return bad(`${commands.where}: row ${r.n}: skill row ${r.skill} ${skill ? `(${skill.skill}) has srvdofunc ${skill.srvdofunc || 'empty'}, not 179` : 'does not exist'}`);
      if (!mon) return bad(`${commands.where}: row ${r.n}: monster row ${r.monster} does not exist`);
      if (r.slot >= 1 && r.slot <= 8 && !slotSkill(mon, r.slot)) return bad(`${commands.where}: row ${r.n}: ${mon.Id} has no Skill${r.slot} with a mode`);
      if (r.attarget > 1) warn(`${commands.where}: row ${r.n}: attarget ${r.attarget} reads as 1`);
      (bySkill[skill.skill] = bySkill[skill.skill] || []).push(r);
    });
    Object.keys(bySkill).forEach((name) => {
      const rows = bySkill[name];
      const seen = new Set();
      rows.forEach((r) => {
        if (seen.has(r.monster)) warn(`${commands.where}: ${name} lists monster row ${r.monster} twice; only the first row is used`);
        seen.add(r.monster);
      });
      const what = (r) => (r.slot === 0 ? 'burst' : r.slot === 9 ? 'strike' : r.slot === 10 ? 'shoot' : slotSkill(monsters[r.monster], r.slot));
      const sample = rows.slice(0, 6).map((r) => `${monsters[r.monster].Id} ${what(r)}`).join(', ');
      console.log(`  ${dir} PetAI command ${name}: ${rows.length} pet kind(s)${rows.length > 64 ? ' (PetAI 0.6.0+: 0.5.0 lost most of these orders)' : ''}: ${sample}${rows.length > 6 ? ', ...' : ''}`);
    });
  });
}

// ---------------------------------------------------------------------------
// AssetMerge plugin fragments (<game>\mods\AssetMerge): rows the plugin merges into the game's
// hd/model_lod_desc.bin and global/animdata.d2 at load. Checked here the way the plugin reads
// them; a mod that still ships one of the two whole files is pointed at the fragments.
// ---------------------------------------------------------------------------
{
  const vanillaBytes = (p) => {
    const key = norm(p);
    fetchVanilla([key]);
    return fetched[key] ? fs.readFileSync(path.join(opt.cache, key)) : null;
  };
  ['hd/model_lod_desc.bin', 'global/animdata.d2'].forEach((key) => {
    if (record.copied[key] || record.written.has(key)) {
      warn(`${key} is replaced whole by a mod; with the AssetMerge plugin a mod adds rows to global/excel/d2rloader/assetmerge/${key.endsWith('.bin') ? 'models' : 'animdata'}.txt instead (toolkit AssetMerge.py), and whole copies hide the other mods' entries`);
    }
  });
  const fragmentText = (file) => {
    const key = norm(`global/excel/d2rloader/assetmerge/${file}`);
    return typeof files[key] === 'string' ? files[key] : null;
  };
  const tsvRows = (text) => {
    const lines = text.replace(/\r/g, '').split('\n').filter((l) => l.trim() && !l.startsWith('#'));
    const header = (lines[0] || '').split('\t').map((h) => h.trim().toLowerCase());
    return { header, rows: lines.slice(1).map((l, i) => ({ line: i + 2, cell: (name) => { const c = header.indexOf(name); return c < 0 ? '' : ((l.split('\t')[c]) || '').trim(); } })) };
  };
  const models = fragmentText('models.txt');
  if (models !== null) {
    const index = vanillaBytes('hd/model_lod_desc.bin');
    const { header, rows } = tsvRows(models);
    if (!['model', 'donor'].every((h) => header.includes(h))) bad('AssetMerge models.txt has no model/donor column');
    // The game's index: models sorted by FNV-1a 32 of the lower-case path; 44-byte records.
    const fnv = (s) => { let h = 0x811c9dc5; for (const ch of Buffer.from(s.replace(/\\/g, '/').toLowerCase())) h = Math.imul(h ^ ch, 0x01000193) >>> 0; return h; };
    const pathOf = (s) => { const p = s.replace(/\\/g, '/').toLowerCase(); return p.startsWith('data/') ? p : `data/${p}`; };
    let byHash = null;
    if (index) {
      const n0 = index.readUInt32LE(0);
      const a0 = 4 + index.readInt32LE(4);
      const a1 = 12 + index.readInt32LE(12);
      byHash = new Map();
      for (let i = 0; i < n0; i++) {
        const r = a0 + i * 44;
        const lodCount = index.readUInt32LE(r + 32);
        const firstLod = r + 36 + index.readInt32LE(r + 36);
        const meshes = [];
        for (let k = 0; k < lodCount; k++) meshes.push(index.readUInt32LE(firstLod + k * 12 + 4));
        byHash.set(index.readUInt32LE(r), meshes);
        if (firstLod < a1) { byHash = null; warn("AssetMerge: the game's model index is not the expected layout; donors not checked"); break; }
      }
    }
    const added = new Map(); // model -> meshes per LOD (from its donor)
    rows.forEach(({ line, cell }) => {
      const model = pathOf(cell('model'));
      if (!/\.model$/.test(model) || /_lod\d/.test(model)) return bad(`AssetMerge models.txt line ${line}: ${cell('model')} is not a model path (data/hd/.../name.model, no _lodN)`);
      if (cell('donor')) {
        const donor = pathOf(cell('donor'));
        const meshes = byHash ? byHash.get(fnv(donor)) || added.get(donor) : [];
        if (!meshes) return bad(`AssetMerge models.txt line ${line}: donor ${donor} is not in the game's model index`);
        added.set(model, meshes);
      }
      if (cell('lod') === '' && cell('mesh') === '') return;
      const lod = Number(cell('lod'));
      const mesh = Number(cell('mesh'));
      const box = ['minx', 'miny', 'minz', 'maxx', 'maxy', 'maxz'].map((h) => Number(cell(h)));
      const meshes = added.get(model);
      if (!meshes) return bad(`AssetMerge models.txt line ${line}: ${model} has no donor`);
      if (byHash && !(lod < meshes.length && mesh < meshes[lod])) return bad(`AssetMerge models.txt line ${line}: ${model} LOD ${lod} mesh ${mesh}, but its donor has ${JSON.stringify(meshes)} meshes per LOD`);
      if (box.some((v) => !Number.isFinite(v)) || box[0] > box[3] || box[1] > box[4] || box[2] > box[5]) bad(`AssetMerge models.txt line ${line}: ${model} needs six box values with min <= max`);
    });
    if (!index) warn('AssetMerge models.txt: the game\'s hd/model_lod_desc.bin could not be read, donors not checked');
    console.log(`AssetMerge models.txt: ${rows.length} row(s), ${added.size} model(s) (needs the AssetMerge plugin)`);
  }
  const anims = fragmentText('animdata.txt');
  if (anims !== null) {
    const table = vanillaBytes('global/animdata.d2');
    const names = new Set();
    if (table) {
      for (let o = 0, b = 0; b < 256 && o + 4 <= table.length; b++) {
        const count = table.readUInt32LE(o);
        o += 4;
        for (let i = 0; i < count; i++, o += 160) names.add(table.toString('latin1', o, o + 8).replace(/\0.*$/s, '').toUpperCase());
      }
    }
    const { header, rows } = tsvRows(anims);
    if (!header.includes('name')) bad('AssetMerge animdata.txt has no name column');
    const seen = new Map();
    rows.forEach(({ line, cell }) => {
      const name = cell('name').toUpperCase();
      if (!/^[A-Z0-9_]{1,7}$/.test(name)) return bad(`AssetMerge animdata.txt line ${line}: "${cell('name')}" is not a COF name (1-7 letters/digits)`);
      const source = cell('source').toUpperCase();
      if (source && !names.has(source) && !seen.has(source)) return bad(`AssetMerge animdata.txt line ${line}: ${name} copies ${source}, which is not in animdata.d2`);
      if (!source && !(Number(cell('frames')) > 0)) return bad(`AssetMerge animdata.txt line ${line}: ${name} needs frames or a source`);
      const ev = cell('events');
      if (ev && ev !== '-' && ev !== '0' && !ev.split(/[, ]+/).filter(Boolean).every((p) => /^\d+:\d+$/.test(p) && Number(p.split(':')[0]) < 144)) bad(`AssetMerge animdata.txt line ${line}: ${name} events "${ev}" are not "-" or frame:code pairs (frame 0-143)`);
      if (seen.has(name)) warn(`AssetMerge animdata.txt line ${line}: ${name} again (line ${seen.get(name)}); the later row wins`);
      if (names.has(name)) warn(`AssetMerge animdata.txt line ${line}: ${name} is already in the game's animdata.d2; the row replaces it`);
      seen.set(name, line);
    });
    console.log(`AssetMerge animdata.txt: ${rows.length} row(s) (needs the AssetMerge plugin)`);
  }
}

// ---------------------------------------------------------------------------
// What it took: the files needed to produce the mods' output.
// ---------------------------------------------------------------------------
console.log(`files: ${record.read.size} read from the game, ${record.written.size} written, ${record.missing.size} asked for but not in the game`);
if (opt.manifest) {
  const manifest = {
    mods: ran,
    game: opt.game,
    readFromGame: [...record.read].sort(),
    askedButMissing: [...record.missing].sort(),
    written: [...record.written].sort(),
    copiedFromModFolder: Object.keys(record.copied).sort(),
    gameFilesDependedOn: [...toCheck].sort(),
  };
  fs.writeFileSync(opt.manifest, `${JSON.stringify(manifest, null, 2)}\n`);
  console.log(`manifest written to ${opt.manifest}`);
}
if (opt.trace) traceReport();
if (opt.out) {
  // Every file the mods wrote, as they left it (tables as TSV, JSON pretty-printed), so two runs
  // can be compared byte for byte, e.g. before and after a refactor.
  [...record.written].sort().forEach((key) => {
    const v = files[key];
    const text = typeof v === 'string' ? v
      : v && Array.isArray(v.headers) && Array.isArray(v.rows)
        ? [v.headers.join('\t'), ...v.rows.map((r) => v.headers.map((h) => (r[h] === undefined ? '' : r[h])).join('\t'))].join('\n') + '\n'
        : `${JSON.stringify(v, null, 1)}\n`;
    const target = path.join(opt.out, key.startsWith('../') ? key.replace(/^(\.\.\/)+/, '_outside/') : key);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, text);
  });
  console.log(`${record.written.size} written files saved under ${opt.out}`);
}
console.log(problems ? `\n${problems} PROBLEM(S), ${warnings} warning(s)` : `\nno problems found (${warnings} warning(s))`);
if (failedMods.size) {
  console.log(`\n${failedMods.size} mod(s) threw and were rolled back:`);
  failedMods.forEach((msg) => console.log(`  FAILED: ${msg}`));
  process.exit(2);
}
process.exit(problems ? 1 : 0);
