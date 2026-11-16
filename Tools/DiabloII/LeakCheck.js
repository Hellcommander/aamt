// Finds what a total conversion changes in the rows that other mods add (template leaks).
//
//   node LeakCheck.js --game <D2R folder> --conversion <mod folder> [options] <mod folder> [<mod folder> ...]
//
// Runs the mods twice with ModHarness.js: on the plain game, and with the conversion installed
// first. Every row the mods add (a key the game's own table does not have) is compared cell by
// cell between the two runs. A mod that copies stock rows as templates and fills in only its own
// columns picks up whatever the conversion did to those stock rows; StockRows.py fixes that.
//
// Options:
//   --python <exe>      python for ModAssets.py (default "python")
//   --max-page <n>      passed to the harness (default 23)
//   --ignore <cols>     comma-separated columns to leave out (default: tree placement and the
//                       columns conversions legitimately change: reqlevel, reqskill1-3, SkillRow,
//                       SkillColumn, IconCel, maxlvl, InTown)
//   --keep <folder>     keep both harness outputs there (default: a temp folder, removed)
//   --config k=v        passed to the harness (repeatable)
//
// Comment columns (starting with '*') are never compared. Columns that hold row numbers computed
// from the installed tables (weapons.txt missiletype, states.txt gfxclass...) differ legitimately
// when the conversion adds rows; the report names them like any other cell.
// Exit code 0 = no differences, 1 = differences, 2 = a harness run failed or a mod threw.
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const opt = { python: 'python', maxPage: '23', ignore: null, keep: null, config: [], mods: [] };
for (let i = 2; i < process.argv.length; i++) {
  const a = process.argv[i];
  const next = () => process.argv[++i];
  if (a === '--game') opt.game = next();
  else if (a === '--conversion') opt.conversion = next();
  else if (a === '--python') opt.python = next();
  else if (a === '--max-page') opt.maxPage = next();
  else if (a === '--ignore') opt.ignore = next();
  else if (a === '--keep') opt.keep = next();
  else if (a === '--config') opt.config.push(next());
  else opt.mods.push(a);
}
if (!opt.game || !opt.conversion || !opt.mods.length) {
  console.error('usage: node LeakCheck.js --game <D2R folder> --conversion <mod folder> [options] <mod folder> [...]');
  process.exit(2);
}
const IGNORE = new Set((opt.ignore !== null ? opt.ignore : 'reqlevel,reqskill1,reqskill2,reqskill3,SkillRow,SkillColumn,IconCel,maxlvl,InTown').split(',').filter(Boolean));
const KEYS = {
  'skills.txt': 'skill', 'skilldesc.txt': 'skilldesc', 'missiles.txt': 'Missile', 'states.txt': 'state',
  'monstats.txt': 'Id', 'monstats2.txt': 'Id', 'pettype.txt': 'pet type', 'sounds.txt': 'Sound',
  'monsounds.txt': 'Id', 'itemtypes.txt': 'Code', 'weapons.txt': 'code', 'armor.txt': 'code', 'misc.txt': 'code',
  'overlay.txt': 'overlay', 'itemstatcost.txt': 'Stat', 'properties.txt': 'code',
};
const VANILLA = path.join(process.env.LOCALAPPDATA || os.tmpdir(), 'D2RModAssets', 'vanilla');
const work = opt.keep || fs.mkdtempSync(path.join(os.tmpdir(), 'leakcheck-'));

function harness(name, mods) {
  const out = path.join(work, name);
  fs.rmSync(out, { recursive: true, force: true });
  const args = [path.join(__dirname, 'ModHarness.js'), '--game', opt.game, '--python', opt.python, '--max-page', opt.maxPage, '--keep-going', '--out', out];
  opt.config.forEach((c) => args.push('--config', c));
  const r = spawnSync(process.execPath, args.concat(mods), { encoding: 'utf8', maxBuffer: 1 << 28 });
  const log = (r.stdout || '') + (r.stderr || '');
  fs.writeFileSync(out + '.log', log);
  const threw = log.split('\n').filter((l) => /the script threw|FAILED \(rolled back/.test(l));
  if (r.status === 2 || r.status === null || threw.length) {
    console.log(`${name} run: a mod failed (log ${out}.log)`);
    threw.forEach((l) => console.log('  ' + l.trim().slice(0, 200)));
    return null;
  }
  return out;
}
function read(file) {
  if (!fs.existsSync(file)) return null;
  const lines = fs.readFileSync(file, 'latin1').split(/\r?\n/);
  const h = lines[0].split('\t');
  return lines.slice(1).filter((l) => l !== '').map((l) => {
    const c = l.split('\t');
    const r = {};
    h.forEach((k, i) => (r[k] = c[i] === undefined ? '' : c[i]));
    return r;
  });
}

const plain = harness('plain', opt.mods);
const conv = harness('conversion', [opt.conversion].concat(opt.mods));
if (!plain || !conv) process.exit(2);
let total = 0;
for (const set of ['', 'base']) {
  for (const t of Object.keys(KEYS)) {
    const p = read(path.join(plain, 'global', 'excel', set, t));
    if (!p) continue;
    const stock = read(path.join(VANILLA, 'global', 'excel', set, t)) || [];
    const k = KEYS[t];
    const isStock = new Set(stock.map((r) => String(r[k]).toLowerCase()));
    const c = read(path.join(conv, 'global', 'excel', set, t)) || stock;
    const byKey = new Map();
    c.forEach((r) => { const n = String(r[k]).toLowerCase(); if (!byKey.has(n)) byKey.set(n, r); });
    const out = [];
    p.forEach((r) => {
      const n = String(r[k]).toLowerCase();
      if (!n || isStock.has(n)) return;
      const g = byKey.get(n);
      if (!g) { out.push(`${r[k]}: not there with the conversion`); return; }
      const d = Object.keys(r).filter((col) => col[0] !== '*' && !IGNORE.has(col) && col in g && r[col] !== g[col]);
      if (d.length) out.push(`${r[k]}: ` + d.map((col) => `${col} "${r[col]}" -> "${g[col]}"`).join(', '));
    });
    if (out.length) {
      console.log(`${set ? 'base/' : ''}${t}: ${out.length} added row(s) differ`);
      out.forEach((o) => console.log('  ' + o));
      total += out.length;
    }
  }
}
console.log(total ? `${total} added row(s) differ with ${path.basename(path.resolve(opt.conversion))} first` : `no added row differs with ${path.basename(path.resolve(opt.conversion))} first (ignoring ${[...IGNORE].join(', ')})`);
if (!opt.keep) fs.rmSync(work, { recursive: true, force: true });
process.exit(total ? 1 : 0);
