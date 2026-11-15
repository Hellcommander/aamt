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
//   --max-page <n>       highest skilldesc SkillPage the SkillTab4 plugin draws (default 15)
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
const opt = { game: process.env.D2R_PATH, cache: null, refresh: false, config: {}, maxPage: 15, manifest: null, dump: null, python: 'python', mods: [] };
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
function load(p, kind) {
  const key = norm(p);
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
const write = (p, v) => { touch(norm(p)); files[norm(p)] = written(v); record.written.add(norm(p)); if (txn) txn.wrote.add(norm(p)); };
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
        if (!stock) warn(`${who} is in a cell (row ${d.SkillRow}, column ${d.SkillColumn}) where the parent tab has no skill, so the tab picture has no frame for it`);
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

// PetAI plugin rules: strict format, and every rule must point at a monster whose Skill<slot> is that skill.
DIRS.forEach((dir) => {
  const text = files[`${dir}d2rloader/petai/rules.txt`];
  if (typeof text !== 'string') return;
  if (!text.endsWith('\n') || /[^\x20-\x7E\t\n]/.test(text)) bad(`${dir}: PetAI rules are not plain line-feed text`);
  const lines = text.slice(0, -1).split('\n').map((l) => l.split('\t'));
  const head = lines[0];
  const monsters = now(`${dir}monstats.txt`, 'tsv').rows.filter((r) => r.Id !== 'Expansion');
  const skillRows = now(`${dir}skills.txt`, 'tsv').rows.filter((r) => r.skill !== 'Expansion');
  lines.slice(1).forEach((cells, i) => {
    if (cells.length !== head.length || cells.some((c) => !/^\d+$/.test(c))) return bad(`${dir}: PetAI rule ${i + 1} is malformed`);
    const rule = Object.fromEntries(head.map((h, k) => [h, Number(cells[k])]));
    const mon = monsters[rule.monster];
    const skill = skillRows[rule.skillid];
    if (!mon || !skill || lower(mon[`Skill${rule.slot}`]) !== lower(skill.skill) || !mon[`Sk${rule.slot}mode`]) return bad(`${dir}: PetAI rule ${i + 1} does not match its monster`);
    console.log(`  ${dir} PetAI rule: ${mon.Id} uses ${skill.skill} (Skill${rule.slot}, ${mon[`Sk${rule.slot}mode`]}), chance ${rule.chance}, cooldown ${rule.cooldown}`);
  });
});

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
