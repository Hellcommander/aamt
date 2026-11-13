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
//   --python <exe>       python to run ModAssets.py with (default "python")
//
// Exit code 0 = no problems, 1 = problems, 2 = a mod script threw.
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
  else if (a === '--dump') opt.dump = process.argv[i + 1] === 'base' ? next() : 'main';
  else if (a === '--python') opt.python = next();
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
function load(p, kind) {
  const key = norm(p);
  if (files[key] !== undefined) return files[key];
  const content = vanilla(key, kind);
  if (content === null) {
    record.missing.add(key);
    throw new Error(`no such file: ${p}`);
  }
  record.read.add(key);
  files[key] = content;
  return content;
}
const write = (p, v) => { files[norm(p)] = v; record.written.add(norm(p)); };
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
  copyFile: (src, dst) => {
    const from = path.join(currentMod, src);
    if (!fs.existsSync(from)) throw new Error(`copyFile: ${src} is not in the mod folder`);
    const list = fs.statSync(from).isDirectory() ? walk(from, [], '') : [''];
    list.forEach((rel) => { record.copied[norm(rel ? `${dst}/${rel}` : dst)] = path.join(from, rel); });
  },
  getVersion: () => 1.7,
  error: (m) => { throw new Error(m); },
};

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
for (const dir of opt.mods) {
  currentMod = dir;
  const meta = JSON.parse(fs.readFileSync(path.join(dir, 'mod.json'), 'utf8'));
  let config = {};
  (meta.config || []).forEach(function each(c) {
    if (c.id) config[c.id] = c.defaultValue;
    (c.children || []).forEach(each);
  });
  const cfgFile = path.join(dir, 'config.json');
  if (fs.existsSync(cfgFile)) config = Object.assign(config, JSON.parse(fs.readFileSync(cfgFile, 'utf8')));
  Object.keys(opt.config).forEach((k) => { config[k] = opt.config[k]; });
  try {
    vm.runInNewContext(fs.readFileSync(path.join(dir, 'mod.js'), 'utf8'), { D2RMM, config, console }, { filename: path.join(dir, 'mod.js') });
  } catch (e) {
    console.log(`${meta.name}: the script threw: ${e.stack || e}`);
    process.exit(2);
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
console.log(problems ? `\n${problems} PROBLEM(S), ${warnings} warning(s)` : `\nno problems found (${warnings} warning(s))`);
process.exit(problems ? 1 : 0);
