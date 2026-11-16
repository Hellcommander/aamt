#!/usr/bin/env node
// ModOrder: sorts a D2RMM mod list and checks it, like LOOT does for Bethesda games.
//
// It reads the list D2RMM keeps (its localStorage, read straight from disk, so D2RMM may be open
// or closed), the masterlist (masterlist.json next to this file: what is known about each mod) and
// your own rules (<D2RMM>\modorder-userlist.json), scans every mod folder for what the masterlist
// does not cover, and then:
//   - sorts the ticked mods: groups (top ... final), then the after/before rules, keeping your own
//     order wherever no rule says otherwise (only what a rule needs moves);
//   - reports missing mods and D2RLoader plugins (and too old plugin versions), mods that break
//     each other, known problems, versions newer than the masterlist knows, and mods it does not
//     know (with what the scan guessed about them).
//
//   node ModOrder.js [check]            report + the sorted order (changes nothing)
//   node ModOrder.js apply              put the sorted order into D2RMM (old list saved first)
//   node ModOrder.js restore <file>     put a saved list back
//   node ModOrder.js gui                the same in a browser window (http://127.0.0.1:8767)
//   node ModOrder.js audit [--sorted]   run the toolkit's ModHarness on the list and show what
//                                       each mod's changes lose to mods below it (slow)
//   node ModOrder.js bestof-rules       write the masterlist's rules into Best Of's mod.js
// Options: --d2rmm <folder>  --json  --from <saved list.json>  --port <n>  --no-browser
//          --restart (apply: close a D2RMM that runs without remote debugging and start it again)
//
// apply talks to D2RMM over Chrome remote debugging (port 9333): it starts D2RMM with
// --remote-debugging-port=9333 when D2RMM is closed, writes the list, reloads the window and reads
// the list back. Nothing else in D2RMM's storage is read or written (it also holds your Nexus key).
// Needs Node 22 or later, nothing else.
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');
const { spawn, spawnSync, execFileSync } = require('child_process');

const HERE = __dirname;
const VERSION = '1.0.0';
const CDP_PORT = 9333;
const STOCK_LAST_LEVEL = 136; // the plain game's levels.txt ends at Id 136

// ------------------------------------------------------------------------------ small helpers
const readJson = (p, fallback) => {
  try {
    return JSON.parse(fs.readFileSync(p, 'utf8').replace(/^\uFEFF/, ''));
  } catch (e) {
    return fallback;
  }
};
const readText = (p) => {
  try {
    return fs.readFileSync(p, 'utf8');
  } catch (e) {
    return '';
  }
};
const lc = (s) => String(s == null ? '' : s).toLowerCase();
const verParts = (v) => String(v || '').split(/[^0-9]+/).filter((x) => x !== '').map(Number);
function verCmp(a, b) {
  const x = verParts(a);
  const y = verParts(b);
  for (let i = 0; i < Math.max(x.length, y.length); i++) {
    const d = (x[i] || 0) - (y[i] || 0);
    if (d) return d;
  }
  return 0;
}
function args() {
  const a = process.argv.slice(2);
  const opt = {};
  const rest = [];
  for (let i = 0; i < a.length; i++) {
    if (a[i].startsWith('--')) {
      const k = a[i].slice(2);
      if (['json', 'apply', 'restart', 'no-browser', 'sorted', 'all'].includes(k)) opt[k] = true;
      else opt[k] = a[++i];
    } else rest.push(a[i]);
  }
  return { cmd: rest[0] || 'check', rest: rest.slice(1), opt };
}

// ------------------------------------------------------------------------------ folders
function findD2rmm(given) {
  const isD2rmm = (p) => p && fs.existsSync(path.join(p, 'mods')) && fs.readdirSync(p).some((f) => /^D2RMM.*\.exe$/i.test(f));
  const saved = readJson(path.join(process.env.LOCALAPPDATA || os.homedir(), 'D2RModAssets', 'paths.json'), {});
  const tries = [given, process.env.D2RMM_PATH, saved.d2rmm, saved.D2RMM];
  // beside this toolkit's usual game folders, and the folder this is run from
  const game = process.env.D2R_PATH || saved.game;
  if (game && fs.existsSync(game)) fs.readdirSync(game).forEach((f) => /d2rmm/i.test(f) && tries.push(path.join(game, f)));
  tries.push(process.cwd(), path.resolve(process.cwd(), '..'), path.resolve(process.cwd(), '..', '..'));
  const found = tries.find(isD2rmm);
  if (!found) throw new Error('D2RMM folder not found: pass --d2rmm <folder> (the one with D2RMM*.exe and mods\\) or set D2RMM_PATH.');
  return path.resolve(found);
}

// ------------------------------------------------------- D2RMM's localStorage (Chromium LevelDB)
// Read-only, and only the keys asked for. Copies the files first (D2RMM may hold them open).
function varint(b, i) {
  let r = 0;
  let s = 0;
  for (;;) {
    const c = b[i++];
    r += (c & 0x7f) * 2 ** s;
    s += 7;
    if (c < 0x80) return [r, i];
  }
}
function unsnappy(b) {
  let [n, i] = varint(b, 0);
  const out = Buffer.alloc(n);
  let o = 0;
  while (i < b.length) {
    const t = b[i++];
    const k = t & 3;
    if (k === 0) {
      let l = t >> 2;
      if (l >= 60) {
        const nb = l - 59;
        l = b.readUIntLE(i, nb);
        i += nb;
      }
      l += 1;
      b.copy(out, o, i, i + l);
      o += l;
      i += l;
      continue;
    }
    let l;
    let off;
    if (k === 1) {
      l = ((t >> 2) & 7) + 4;
      off = ((t >> 5) << 8) | b[i++];
    } else if (k === 2) {
      l = (t >> 2) + 1;
      off = b.readUInt16LE(i);
      i += 2;
    } else {
      l = (t >> 2) + 1;
      off = b.readUInt32LE(i);
      i += 4;
    }
    for (let j = 0; j < l; j++, o++) out[o] = out[o - off];
  }
  return out;
}
function* blockEntries(d) {
  const nrest = d.readUInt32LE(d.length - 4);
  const end = d.length - 4 - 4 * nrest;
  let i = 0;
  let last = Buffer.alloc(0);
  while (i < end) {
    let sh;
    let ns;
    let vl;
    [sh, i] = varint(d, i);
    [ns, i] = varint(d, i);
    [vl, i] = varint(d, i);
    const key = Buffer.concat([last.subarray(0, sh), d.subarray(i, i + ns)]);
    i += ns;
    const val = d.subarray(i, i + vl);
    i += vl;
    last = key;
    yield [key, val];
  }
}
function readLevelDb(dir, wanted) {
  const want = new Map(wanted.map((k) => [k, null])); // key -> [seq, value|null]
  const note = (seq, key, val) => {
    const z = key.indexOf(Buffer.from([0, 1]));
    if (z < 0 || !key.subarray(0, z).toString('latin1').startsWith('_')) return;
    const name = key.subarray(z + 2).toString('latin1');
    if (!want.has(name)) return;
    const cur = want.get(name);
    if (!cur || seq > cur[0]) want.set(name, [seq, val]);
  };
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'modorder-'));
  try {
    for (const f of fs.readdirSync(dir)) {
      if (!/\.(ldb|log)$/.test(f)) continue;
      const p = path.join(tmp, f);
      fs.copyFileSync(path.join(dir, f), p);
      const data = fs.readFileSync(p);
      if (f.endsWith('.ldb')) {
        const block = (off, size) => {
          const raw = data.subarray(off, off + size);
          return data[off + size] === 1 ? unsnappy(raw) : raw;
        };
        const foot = data.subarray(data.length - 48);
        let i = 0;
        let io;
        let isz;
        [, i] = varint(foot, i);
        [, i] = varint(foot, i);
        [io, i] = varint(foot, i);
        [isz, i] = varint(foot, i);
        for (const [, h] of blockEntries(block(io, isz))) {
          const [o, j] = varint(h, 0);
          const [s] = varint(h, j);
          for (const [k, v] of blockEntries(block(o, s))) {
            const tag = k.readBigUInt64LE(k.length - 8);
            note(Number(tag >> 8n), k.subarray(0, k.length - 8), (tag & 0xffn) === 1n ? v : null);
          }
        }
      } else {
        // log: 32 KiB blocks of records (crc 4, length 2, type 1), FULL/FIRST/MIDDLE/LAST
        const recs = [];
        let buf = null;
        let i = 0;
        while (i + 7 <= data.length) {
          const left = 32768 - (i % 32768);
          if (left < 7) {
            i += left;
            continue;
          }
          const len = data.readUInt16LE(i + 4);
          const type = data[i + 6];
          const frag = data.subarray(i + 7, i + 7 + len);
          i += 7 + len;
          if (type === 0) {
            i += (32768 - (i % 32768)) % 32768;
            continue;
          }
          if (type === 1) recs.push(frag);
          else if (type === 2) buf = Buffer.from(frag);
          else if (type === 3 && buf) buf = Buffer.concat([buf, frag]);
          else if (type === 4 && buf) {
            recs.push(Buffer.concat([buf, frag]));
            buf = null;
          }
        }
        for (const r of recs) {
          if (r.length < 12) continue;
          const seq = Number(r.readBigUInt64LE(0));
          const n = r.readUInt32LE(8);
          let j = 12;
          for (let c = 0; c < n && j < r.length; c++) {
            const t = r[j++];
            let kl;
            [kl, j] = varint(r, j);
            const k = r.subarray(j, j + kl);
            j += kl;
            let v = null;
            if (t === 1) {
              let vl;
              [vl, j] = varint(r, j);
              v = r.subarray(j, j + vl);
              j += vl;
            }
            note(seq + c, k, v);
          }
        }
      }
    }
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
  const out = {};
  for (const [k, cur] of want) {
    if (!cur || !cur[1] || !cur[1].length) {
      out[k] = undefined;
      continue;
    }
    const v = cur[1];
    const text = v[0] === 1 ? v.subarray(1).toString('latin1') : v.subarray(1).toString('utf16le');
    try {
      out[k] = JSON.parse(text);
    } catch (e) {
      out[k] = text;
    }
  }
  return out;
}
const LIST_KEYS = ['enabled-mods', 'mods-order', 'installed-mods', 'd2rloader-plugin-preferences'];
function readD2rmmList() {
  const dir = path.join(process.env.APPDATA || path.join(os.homedir(), 'AppData', 'Roaming'), 'd2rmm', 'Local Storage', 'leveldb');
  if (!fs.existsSync(dir)) throw new Error(`D2RMM's storage not found (${dir}); start D2RMM once, or pass --from <saved list.json>`);
  const v = readLevelDb(dir, LIST_KEYS);
  return {
    enabledMods: v['enabled-mods'] || {},
    modsOrder: v['mods-order'] || [],
    installed: Array.isArray(v['installed-mods']) ? v['installed-mods'].map((m) => m && m.id).filter(Boolean) : null,
    pluginPrefs: v['d2rloader-plugin-preferences'] || {},
  };
}

// ------------------------------------------------------------------------------ the mods folder
function dllVersion(file) {
  try {
    const b = fs.readFileSync(file);
    for (const key of ['FileVersion', 'ProductVersion']) {
      const k = Buffer.from(key + '\0', 'utf16le');
      let at = b.indexOf(k);
      while (at >= 0) {
        let i = at + k.length;
        while (i < b.length - 1 && b[i] === 0 && b[i + 1] === 0) i += 2; // padding
        let s = '';
        for (; i < b.length - 1; i += 2) {
          const c = b.readUInt16LE(i);
          if (!c) break;
          s += String.fromCharCode(c);
        }
        if (/\d/.test(s)) return s.trim().replace(/(\.0)+$/, (m) => (s.trim().split('.').length > 3 ? m.slice(0, -2) : m));
        at = b.indexOf(k, at + 1);
      }
    }
    // plugins built with the D2RLoader plugin SDK keep their version as a plain string
    const text = b.toString('latin1');
    const base = lc(path.basename(file, '.dll'));
    const named = new RegExp(`${base.replace(/[^a-z0-9]/g, '.')}:? v?(\\d+\\.\\d+\\.\\d+)`, 'i').exec(text);
    if (named) return named[1];
    const lone = /\0(\d{1,3}\.\d{1,3}\.\d{1,3})\0/.exec(text);
    if (lone) return lone[1];
  } catch (e) {
    /* no version */
  }
  return null;
}
function scanPlugins(d2rmm, prefs) {
  const root = path.join(d2rmm, 'd2rloader');
  const plugins = new Map(); // dll base name (lower case) -> {name, package, version, enabled, staged}
  if (!fs.existsSync(root)) return plugins;
  for (const f of fs.readdirSync(root, { withFileTypes: true })) {
    const p = path.join(root, f.name);
    if (f.isDirectory()) {
      const man = readJson(path.join(p, 'manifest.json'), null);
      if (!man || !Array.isArray(man.files)) continue;
      man.files.filter((x) => /\.dll$/i.test(x.sourcePath || '')).forEach((x) => {
        const base = lc(path.basename(x.sourcePath || '', '.dll'));
        if (!base) return;
        const pref = prefs[man.name] !== undefined ? prefs[man.name] : prefs[f.name];
        plugins.set(base, {
          name: base,
          package: man.name || f.name,
          version: dllVersion(path.join(p, 'source', x.sourcePath)),
          enabled: pref !== false && !(pref && pref.enabled === false),
          staged: false,
        });
      });
    } else if (/\.(dll|zip)$/i.test(f.name)) {
      // dropped here, imported by D2RMM on its next start
      const base = lc(f.name.replace(/\.(dll|zip)$/i, '').replace(/[-_ ]?v?\d+(\.\d+)+.*$/, ''));
      if (!plugins.has(base)) plugins.set(base, { name: base, package: f.name, version: null, enabled: true, staged: true });
    }
  }
  return plugins;
}
function modConfig(dir, modJson) {
  const cfg = {};
  (modJson.config || []).forEach(function walk(c) {
    if (c && c.id !== undefined && c.defaultValue !== undefined) cfg[c.id] = c.defaultValue;
    if (c && Array.isArray(c.children)) c.children.forEach(walk);
  });
  return Object.assign(cfg, readJson(path.join(dir, 'config.json'), {}));
}
function walkFiles(dir, base = dir, out = [], depth = 0) {
  if (depth > 8 || out.length > 20000) return out;
  for (const f of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, f.name);
    if (f.isDirectory()) {
      if (/^(d2rmm|dev|node_modules|\.git)$/i.test(f.name) || /\.mpq$/i.test(f.name)) continue;
      walkFiles(p, base, out, depth + 1);
    } else out.push(path.relative(base, p));
  }
  return out;
}
function convertedLevels(dir, convert) {
  // the levels a converted data mod adds past the plain game's last one
  const data = convert && convert.data ? path.join(dir, convert.data) : null;
  if (!data) return [];
  const file = ['global/excel/levels.txt', 'global\\excel\\levels.txt'].map((p) => path.join(data, p)).find((p) => fs.existsSync(p));
  if (!file) return [];
  const rows = readText(file).split(/\r?\n/).map((l) => l.split('\t'));
  const h = rows[0] || [];
  const id = h.indexOf('Id');
  const name = h.indexOf('LevelName') >= 0 ? h.indexOf('LevelName') : 0;
  if (id < 0) return [];
  return rows.slice(1).filter((r) => Number(r[id]) > STOCK_LAST_LEVEL).map((r) => ({ id: Number(r[id]), name: r[name] || r[0] }));
}
// What a mod says about itself in mod.json / README / mod.js; used for mods the masterlist does
// not know (and to cross-check the ones it does).
function scanMod(d2rmm, id) {
  const dir = path.join(d2rmm, 'mods', id);
  const modJson = readJson(path.join(dir, 'mod.json'), null);
  if (!modJson) return null;
  const readme = readText(path.join(dir, 'README.md')) || readText(path.join(dir, 'README.txt'));
  const text = `${modJson.description || ''}\n${readme}`;
  const js = readText(path.join(dir, 'mod.js'));
  const convert = readJson(path.join(dir, 'd2rmm', 'convert.json'), null);
  const s = {
    id,
    dir,
    name: modJson.name || id,
    version: modJson.version || '',
    author: modJson.author || '',
    config: modConfig(dir, modJson),
    converted: convert ? { rows: convert.rows, data: convert.data } : null,
    levels: convert ? convertedLevels(dir, convert) : [],
    hints: [],
    wholeFiles: [],
    plugins: [],
  };
  if (convert && convert.rows === 'rebuild') s.hints.push({ group: 'top', why: 'converted with rows "rebuild" (it lays the tables out in its own order)' });
  else if (convert) s.hints.push({ group: 'top', why: 'a converted data mod (its README says: top of the list)' });
  if (/\b(install|put|place|keep)\s+(it\s+|this mod\s+)?(LAST|at the BOTTOM)|\bLAST in the (mod )?list\b/i.test(text)) s.hints.push({ group: 'late', why: 'its description says to put it last' });
  else if (/\b(put|place|install)\s+(it\s+|this mod\s+)?(at the )?(TOP|FIRST)\b/i.test(text) && !convert) s.hints.push({ group: 'early', why: 'its description says to put it at the top' });
  // whole tables / string files shipped in the folder and copied over the game's
  if (!convert && /copyFile\s*\(/.test(js) && fs.existsSync(dir)) {
    s.wholeFiles = walkFiles(dir).map((f) => f.replace(/\//g, '\\')).filter((f) => /(^|\\)global\\excel\\(base\\)?[^\\]+\.txt$|(^|\\)local\\lng\\strings(-legacy)?\\[^\\]+\.json$/i.test(f))
      .map((f) => f.replace(/^.*?(global\\excel|local\\lng)/i, '$1')).filter((f, i, a) => a.findIndex((x) => lc(x) === lc(f)) === i);
  }
  // "Needs the X D2RLoader plugin" / "D2RLoader plugin **X**"
  const re = /(?:needs?|requires?)\s+(?:the\s+)?(?:D2RLoader\s+plugins?\s+)?\**([A-Z][A-Za-z0-9]+)\**(?:\s+D2RLoader)?\s+plugin|D2RLoader plugins?\s+\*\*([A-Z][A-Za-z0-9]+)/g;
  let m;
  while ((m = re.exec(text))) {
    const n = lc(m[1] || m[2]);
    if (n && !['d2rloader', 'the', 'a'].includes(n) && !s.plugins.includes(n)) s.plugins.push(n);
  }
  return s;
}

// ------------------------------------------------------------------------------ the masterlist
function loadLists(d2rmm) {
  const master = readJson(path.join(HERE, 'masterlist.json'), null);
  if (!master) throw new Error(`masterlist.json missing or broken next to ${__filename}`);
  const userFile = path.join(d2rmm, 'modorder-userlist.json');
  const user = readJson(userFile, { mods: [] });
  const groups = master.groups;
  const entries = [];
  const byKey = new Map();
  const add = (e, from) => {
    const ids = e.ids || (e.id ? [e.id] : []);
    const known = ids.map((i) => byKey.get(lc(i))).find(Boolean);
    if (known) {
      // the userlist adds to (and for single values replaces) the masterlist entry
      for (const [k, v] of Object.entries(e)) {
        if (Array.isArray(v) && Array.isArray(known[k])) known[k] = known[k].concat(v);
        else known[k] = v;
      }
      known.from = known.from === from ? from : `${known.from}+${from}`;
      ids.forEach((i) => byKey.set(lc(i), known));
      return;
    }
    const c = Object.assign({ from }, e, { ids });
    entries.push(c);
    ids.forEach((i) => byKey.set(lc(i), c));
    (e.names || []).forEach((n) => byKey.set(`name:${lc(n)}`, c));
  };
  master.mods.forEach((e) => add(e, 'masterlist'));
  (user.mods || []).forEach((e) => add(e, 'userlist'));
  return { master, groups, byKey, entries, userFile, userExists: fs.existsSync(userFile) };
}

// ------------------------------------------------------------------------------ evaluation
function evaluate({ d2rmm, list, lists }) {
  const msgs = [];
  const say = (level, mod, text) => msgs.push({ level, mod: mod || null, text });
  const modsDir = path.join(d2rmm, 'mods');
  const present = new Set(fs.readdirSync(modsDir).filter((f) => fs.existsSync(path.join(modsDir, f, 'mod.json'))));
  const ticked = list.modsOrder.filter((id) => list.enabledMods[id]);
  const missing = ticked.filter((id) => !present.has(id));
  missing.forEach((id) => say('warn', id, 'ticked in D2RMM but its folder is not in mods\\ (left out of the sort)'));
  const tickedHere = ticked.filter((id) => present.has(id));

  const scans = new Map();
  tickedHere.forEach((id) => scans.set(id, scanMod(d2rmm, id)));
  const entryOf = (id) => {
    const s = scans.get(id);
    return lists.byKey.get(lc(id)) || (s && lists.byKey.get(`name:${lc(s.name)}`)) || null;
  };
  // masterlist ids -> the folder that is ticked for them
  const tickedFor = new Map();
  tickedHere.forEach((id) => {
    const e = entryOf(id);
    (e ? e.ids : [id]).forEach((k) => tickedFor.has(lc(k)) || tickedFor.set(lc(k), id));
    tickedFor.set(lc(id), id);
  });
  const isTicked = (k) => tickedFor.get(lc(k));
  const nameOf = (id) => (scans.get(id) ? scans.get(id).name : id);
  const tagged = (tag) => tickedHere.filter((id) => {
    const e = entryOf(id);
    if (e && (e.tags || []).includes(tag)) return true;
    return tag === 'conversion' && scans.get(id) && scans.get(id).converted;
  });
  const holds = (cond, id) => {
    if (!cond) return true;
    if (cond.ticked && !cond.ticked.every(isTicked)) return false;
    if (cond.anyTicked && !cond.anyTicked.some(isTicked)) return false;
    if (cond.notTicked && cond.notTicked.some(isTicked)) return false;
    if (cond.config) {
      const cfg = (scans.get(id) || {}).config || {};
      if (!Object.entries(cond.config).every(([k, v]) => cfg[k] === v)) return false;
    }
    return true;
  };

  const plugins = scanPlugins(d2rmm, list.pluginPrefs || {});
  const groupRank = (g) => {
    const i = lists.groups.indexOf(g || 'default');
    return i < 0 ? lists.groups.indexOf('default') : i;
  };
  const group = new Map();
  const before = new Map(tickedHere.map((id) => [id, new Map()])); // id -> Map(pred -> why)
  const edge = (a, b, why) => a !== b && before.get(b) && !before.get(b).has(a) && before.get(b).set(a, why);
  const unknown = [];

  for (const id of tickedHere) {
    const s = scans.get(id);
    const e = entryOf(id);
    let g = e && e.group;
    if (!e) {
      unknown.push(id);
      const hint = s.hints[0];
      if (hint) g = hint.group;
      say('info', id, `not in the masterlist${hint ? `; sorted into "${hint.group}" because ${hint.why}` : '; sorted where you put it'}`);
      s.plugins.forEach((p) => {
        if (!plugins.has(p)) say('warn', id, `its description names a D2RLoader plugin "${p}" that is not in D2RMM's d2rloader folder (check its README)`);
      });
    } else if (e.checked && s.version && verCmp(s.version, e.checked) !== 0) {
      say('info', id, `version ${s.version}; the masterlist was written for ${e.checked}, so its rules may be out of date`);
    }
    if (s.wholeFiles.length && !(e && e.group === 'whole-file')) {
      say('warn', id, `copies whole game files over what the mods above it wrote: ${s.wholeFiles.slice(0, 6).join(', ')}${s.wholeFiles.length > 6 ? ', ...' : ''}${e ? '' : ' (if those are tables, put it high in the list or add it to the userlist as group "whole-file")'}`);
    }
    group.set(id, g || 'default');
    if (!e) continue;
    if (e.notes) say('note', id, e.notes);
    const resolve = (r) => (r.mod ? [isTicked(r.mod)].filter(Boolean) : r.tag ? tagged(r.tag) : []);
    (e.after || []).forEach((r) => holds(r.if, id) && resolve(r).forEach((p) => edge(p, id, r.why || '')));
    (e.before || []).forEach((r) => holds(r.if, id) && resolve(r).forEach((n) => edge(id, n, r.why || '')));
    (e.requires || []).forEach((r) => {
      if (!holds(r.if, id)) return;
      const level = r.level || 'error';
      const why = r.why ? ` (${r.why})` : '';
      if (r.mod) {
        if (!isTicked(r.mod)) say(level, id, `needs "${r.mod}"${present.has(r.mod) ? ' ticked' : ', which is not in the mods folder'}${why}`);
        return;
      }
      const p = plugins.get(lc(r.plugin));
      if (!p) say(level, id, `needs the D2RLoader plugin ${r.plugin}${r.min ? ` ${r.min}+` : ''}${why}; it is not in D2RMM's d2rloader folder`);
      else if (p.staged) say('info', id, `plugin ${r.plugin} is dropped in d2rloader\\ (${p.package}); D2RMM imports it on its next start`);
      else if (!p.enabled) say(level, id, `the D2RLoader plugin ${r.plugin} is turned off in D2RMM's Plugins tab${why}`);
      else if (r.min && p.version && verCmp(p.version, r.min) < 0) say(level, id, `needs ${r.plugin} ${r.min} or later; ${p.version} is imported${why}`);
    });
    (e.incompatible || []).forEach((r) => {
      const other = isTicked(r.mod);
      if (other && holds(r.if, id)) say(r.level || 'error', id, `breaks with "${nameOf(other)}": ${r.why}`);
    });
    (e.messages || []).forEach((m) => holds(m.if, id) && say(m.level || 'info', id, m.text));
  }

  // the same mod ticked twice under two folder names
  const byName = new Map();
  tickedHere.forEach((id) => {
    const n = lc(scans.get(id).name);
    if (byName.has(n)) say('warn', id, `ticked twice: "${byName.get(n)}" is the same mod (${scans.get(id).name})`);
    else byName.set(n, id);
  });

  // ---------------------------------------------------------------------------- the sort
  const place = new Map(tickedHere.map((id, i) => [id, i]));
  const rank = (id) => groupRank(group.get(id));
  for (const [b, preds] of before) {
    for (const [a, why] of preds) {
      if (rank(a) > rank(b)) {
        say('warn', b, `rule "${nameOf(a)}" before "${nameOf(b)}" (${why}) cannot be kept: "${nameOf(a)}" is in group "${group.get(a)}", lower than "${group.get(b)}"`);
        preds.delete(a);
      }
    }
  }
  const cmp = (x, y) => rank(x) - rank(y) || place.get(x) - place.get(y);
  const order = [];
  const done = new Set();
  const visiting = new Set();
  const reasons = new Map(); // id -> why it moved up
  const emit = (id) => {
    if (done.has(id)) return;
    if (visiting.has(id)) {
      say('warn', id, 'its rules go in a circle; it keeps its place');
      return;
    }
    visiting.add(id);
    [...before.get(id).keys()].sort(cmp).forEach((p) => {
      if (!done.has(p) && place.get(p) > place.get(id)) reasons.set(p, `before "${nameOf(id)}": ${before.get(id).get(p)}`);
      emit(p);
    });
    visiting.delete(id);
    if (done.has(id)) return;
    order.push(id);
    done.add(id);
  };
  tickedHere.slice().sort(cmp).forEach(emit);

  // Converted mods that add levels on the same numbers, whether the masterlist knows them or not.
  // One converted with rows 'keep' (its Load order setting) moves its new levels behind those of
  // the mods above it at install time, so the pair only clashes when the lower one is 'rebuild'.
  const rowsOf = (id) => {
    const s = scans.get(id);
    const v = s.config && s.config.loadorderRows;
    return v === 'keep' || v === 'rebuild' ? v : s.converted && s.converted.rows;
  };
  const conv = order.filter((id) => scans.get(id).levels.length);
  for (let i = 0; i < conv.length; i++) {
    for (let j = i + 1; j < conv.length; j++) {
      const a = scans.get(conv[i]);
      const b = scans.get(conv[j]);
      const ids = new Set(a.levels.map((l) => l.id));
      const both = b.levels.filter((l) => ids.has(l.id)).map((l) => l.id);
      if (!both.length) continue;
      const span = `${Math.min(...both)}-${Math.max(...both)}`;
      if (rowsOf(conv[j]) === 'keep') {
        say('info', conv[j], `its new levels ${span} are numbers "${a.name}" uses too; with rows 'keep' below it they move behind its levels at install time`);
        continue;
      }
      const known = msgs.some((m) => m.level === 'error' && [conv[i], conv[j]].includes(m.mod) && m.text.includes('level numbers'));
      if (!known) say('error', conv[j], `breaks with "${a.name}": both add levels on level numbers ${span} (${both.length} shared); converted with rows 'rebuild' it cannot move them (set its Load order > Rows to 'keep')`);
    }
  }
  const moves = describeMoves(tickedHere, order).map((m) => {
    const why = reasons.get(m.id) || (rank(m.id) !== lists.groups.indexOf('default') ? `group "${group.get(m.id)}"` : 'made room for a mod that moved');
    return Object.assign(m, { name: nameOf(m.id), why });
  });

  // the list D2RMM last installed is not this one
  if (list.installed) {
    const same = list.installed.length === tickedHere.length && list.installed.every((id, i) => id === tickedHere[i]);
    if (!same) say('info', null, 'the ticked list is not the one D2RMM last installed: click Install Mods after changing it');
  }
  const levelOrder = { error: 0, warn: 1, info: 2, note: 3 };
  msgs.sort((a, b) => levelOrder[a.level] - levelOrder[b.level]);
  return {
    version: VERSION,
    d2rmm,
    masterlist: { updated: lists.master.updated, entries: lists.entries.length },
    userlist: lists.userExists ? lists.userFile : null,
    ticked: tickedHere,
    order,
    moves,
    messages: msgs,
    unknown,
    groups: Object.fromEntries(order.map((id) => [id, group.get(id)])),
    names: Object.fromEntries(order.map((id) => [id, nameOf(id)])),
    plugins: [...plugins.values()],
  };
}
function describeMoves(oldList, newList) {
  // the mods outside the longest run both orders share
  const a = oldList;
  const b = newList;
  const L = Array.from({ length: a.length + 1 }, () => new Array(b.length + 1).fill(0));
  for (let i = a.length - 1; i >= 0; i--) for (let j = b.length - 1; j >= 0; j--) L[i][j] = a[i] === b[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
  const stay = new Set();
  for (let i = 0, j = 0; i < a.length && j < b.length;) {
    if (a[i] === b[j]) {
      stay.add(a[i]);
      i++;
      j++;
    } else if (L[i + 1][j] >= L[i][j + 1]) i++;
    else j++;
  }
  return b.filter((id) => !stay.has(id)).map((id) => ({ id, from: a.indexOf(id) + 1, to: b.indexOf(id) + 1 }));
}

function printReport(r) {
  const mark = { error: 'ERROR', warn: 'warn ', info: 'info ', note: 'note ' };
  console.log(`ModOrder ${r.version}: ${r.ticked.length} ticked mods, masterlist ${r.masterlist.updated} (${r.masterlist.entries} mods)${r.userlist ? ', userlist ' + r.userlist : ''}`);
  const shown = r.messages.filter((m) => m.level !== 'note');
  if (shown.length) {
    console.log('');
    shown.forEach((m) => console.log(`${mark[m.level]} ${m.mod ? (r.names[m.mod] || m.mod) + ': ' : ''}${m.text}`));
  }
  console.log('');
  if (r.moves.length) {
    console.log('Sorted order moves (place now -> sorted):');
    r.moves.forEach((m) => console.log(`  ${String(m.from).padStart(3)} -> ${String(m.to).padStart(3)}  ${m.name}  (${m.why})`));
    console.log('\nRun "ModOrder apply" to put the sorted order into D2RMM.');
  } else console.log('The order already keeps every rule.');
  const counts = ['error', 'warn'].map((l) => `${r.messages.filter((m) => m.level === l).length} ${l === 'error' ? 'error(s)' : 'warning(s)'}`);
  console.log(`\n${counts.join(', ')}, ${r.unknown.length} mod(s) not in the masterlist.`);
}

// ------------------------------------------------------------------------------ D2RMM over CDP
async function cdpTarget() {
  const list = await (await fetch(`http://127.0.0.1:${CDP_PORT}/json`)).json();
  const page = list.find((t) => t.type === 'page' && !/devtools/i.test(t.url));
  if (!page) throw new Error('no D2RMM window');
  return page;
}
async function cdp(expression) {
  const page = await cdpTarget();
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => {
    ws.addEventListener('open', res);
    ws.addEventListener('error', rej);
  });
  const result = await new Promise((res) => {
    ws.addEventListener('message', (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id === 1) res(msg.result);
    });
    ws.send(JSON.stringify({ id: 1, method: 'Runtime.evaluate', params: { expression, returnByValue: true, awaitPromise: true } }));
  });
  ws.close();
  if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails).slice(0, 400));
  return result.result.value;
}
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
function d2rmmRunning() {
  try {
    const out = execFileSync('tasklist', ['/FO', 'CSV', '/NH'], { encoding: 'utf8' });
    return /"D2RMM[^"]*\.exe"/i.test(out);
  } catch (e) {
    return false;
  }
}
async function connectD2rmm(d2rmm, restart) {
  try {
    await cdpTarget();
    return;
  } catch (e) {
    /* not reachable */
  }
  if (d2rmmRunning()) {
    if (!restart) throw new Error(`D2RMM is open without remote debugging. Close it and run apply again (ModOrder starts it with --remote-debugging-port=${CDP_PORT}), or add --restart to let ModOrder close it.`);
    spawnSync('taskkill', ['/IM', 'D2RMM Custom.exe', '/T'], { stdio: 'ignore' });
    spawnSync('taskkill', ['/IM', 'D2RMM.exe', '/T'], { stdio: 'ignore' });
    for (let i = 0; i < 20 && d2rmmRunning(); i++) await wait(500);
  }
  const exe = fs.readdirSync(d2rmm).find((f) => /^D2RMM.*\.exe$/i.test(f));
  if (!exe) throw new Error('no D2RMM*.exe in ' + d2rmm);
  // through cmd's start, so D2RMM does not close when this console does
  spawn('cmd.exe', ['/c', 'start', '""', path.join(d2rmm, exe), `--remote-debugging-port=${CDP_PORT}`], { cwd: d2rmm, detached: true, stdio: 'ignore', windowsVerbatimArguments: false }).unref();
  for (let i = 0; i < 60; i++) {
    await wait(1000);
    try {
      await cdpTarget();
      await wait(2000); // let the window load its state
      return;
    } catch (e) {
      /* starting */
    }
  }
  throw new Error('D2RMM did not open its debugging port in 60 s');
}
const READ_EXPR = "JSON.stringify({ enabledMods: JSON.parse(localStorage.getItem('enabled-mods') || '{}'), modsOrder: JSON.parse(localStorage.getItem('mods-order') || '[]') })";
async function applyOrder(d2rmm, newTicked, opt, note) {
  await connectD2rmm(d2rmm, opt.restart);
  const live = JSON.parse(await cdp(READ_EXPR));
  const backupDir = path.join(d2rmm, 'modorder-backups');
  fs.mkdirSync(backupDir, { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const backup = path.join(backupDir, `mod-list.${stamp}.json`);
  fs.writeFileSync(backup, JSON.stringify(Object.assign({ savedAt: new Date().toISOString(), by: `ModOrder ${VERSION}${note ? ' ' + note : ''}` }, live), null, 1) + '\n');
  const enabled = Object.assign({}, live.enabledMods);
  newTicked.forEach((id) => (enabled[id] = true));
  const order = newTicked.concat(live.modsOrder.filter((id) => !newTicked.includes(id)));
  await cdp(`localStorage.setItem('enabled-mods', ${JSON.stringify(JSON.stringify(enabled))}); localStorage.setItem('mods-order', ${JSON.stringify(JSON.stringify(order))}); location.reload(); true`);
  await wait(3000);
  const back = JSON.parse(await cdp(READ_EXPR));
  const ok = back.modsOrder.filter((id) => back.enabledMods[id]).join('|') === order.filter((id) => enabled[id]).join('|');
  if (!ok) throw new Error(`D2RMM did not keep the new list (read back differs). The old list is in ${backup}`);
  return backup;
}

// ------------------------------------------------------------------------------ Best Of rules
function bestOfRules(lists) {
  const js = (v) => JSON.stringify(v).replace(/'/g, "\\'").replace(/"/g, "'");
  const entries = lists.entries;
  const first = (e) => e.ids[0];
  const tag = (t) => entries.filter((e) => (e.tags || []).includes(t)).map(first);
  const order = [];
  const pair = (a, b, why) => !order.some((o) => o[0] === a && o[1] === b) && order.push([a, b, why || '']);
  entries.forEach((e) => {
    const res = (r) => (r.mod ? [r.mod] : r.tag ? tag(r.tag) : []);
    (e.after || []).filter((r) => !r.if).forEach((r) => res(r).forEach((p) => pair(p, first(e), r.why)));
    (e.before || []).filter((r) => !r.if).forEach((r) => res(r).forEach((n) => pair(first(e), n, r.why)));
  });
  const clashes = [];
  entries.forEach((e) => (e.incompatible || []).filter((r) => !r.if).forEach((r) => {
    if (!clashes.some((c) => c[0].includes(first(e)) && c[0].includes(r.mod))) clashes.push([[first(e), r.mod], r.why]);
  }));
  const inGroup = (g) => entries.filter((e) => e.group === g);
  // The top group in the order its own before/after rules give (Necromancer_V1.6 above the
  // conversions, Rebirth below Reimagined...), the masterlist's order where none says otherwise.
  const topOrder = () => {
    const top = inGroup('top');
    const ids = new Set(top.map(first));
    const pre = new Map(top.map((e) => [first(e), new Set()]));
    top.forEach((e) => {
      const res = (r) => (r.mod ? [r.mod] : r.tag ? tag(r.tag) : []).filter((x) => ids.has(x));
      (e.after || []).filter((r) => !r.if).forEach((r) => res(r).forEach((p) => p !== first(e) && pre.get(first(e)).add(p)));
      (e.before || []).filter((r) => !r.if).forEach((r) => res(r).forEach((n) => n !== first(e) && pre.get(n).add(first(e))));
    });
    const out = [];
    const seen = new Set();
    const visit = (id, stack = new Set()) => {
      if (seen.has(id) || stack.has(id)) return;
      stack.add(id);
      [...pre.get(id)].forEach((p) => visit(p, stack));
      seen.add(id);
      out.push(top.find((e) => first(e) === id));
    };
    top.forEach((e) => visit(first(e)));
    return out;
  };
  const early = [];
  entries.forEach((e) => (e.before || []).filter((r) => r.if && r.if.ticked && first(e) === 'BestOfEarly').forEach((r) => early.push([r.mod, r.if.ticked, r.why])));
  return [
    `// Generated by ModOrder.js bestof-rules from the ModOrder masterlist (${lists.master.updated}); edit the masterlist, not this block.`,
    `const CONVERSIONS = ${js(tag('conversion'))};`,
    `const PAGE_MODS = ${js(tag('skill-pages'))};`,
    '// [first, second, why]: when both are ticked, `first` has to come before `second`.',
    'const ORDER = [',
    ...order.map((o) => `  ${js(o)},`),
    '];',
    '// Ticked together they break each other.',
    'const CLASHES = [',
    ...clashes.map((c) => `  ${js(c)},`),
    '];',
    '// Mods that have to be at the very top (in this order).',
    `const FIRST = ${js(topOrder().map((e) => [first(e), e.notes || 'the masterlist puts it at the top']))};`,
    '// Mods that copy WHOLE tables or string files over what is there; they go above everything else.',
    `const WHOLE_FILE = ${js(inGroup('whole-file').map((e) => [first(e), (e.files || []).map((f) => f.split('\\').pop()), e.notes || '']))};`,
    '// Mods that may run after Best Of.',
    `const AFTER_BEST_OF = ${js(inGroup('final').map(first))};`,
    '// Best Of\'s early part: goes right above these mods when one of the mods named with it is ticked.',
    `const EARLY = ${js(early)};`,
  ].join('\n');
}
function writeBestOfRules(d2rmm, lists) {
  const file = path.join(d2rmm, 'mods', 'BestOf', 'mod.js');
  const src = readText(file);
  const re = /(\/\/ RULES-BEGIN[^\n]*\n)[\s\S]*?(\/\/ RULES-END)/;
  if (!re.test(src)) throw new Error(`no RULES-BEGIN/RULES-END block in ${file}`);
  const out = src.replace(re, (m, a, b) => `${a}${bestOfRules(lists)}\n${b}`);
  fs.writeFileSync(file, out);
  return file;
}

// ------------------------------------------------------------------------------ audit (harness)
function audit(d2rmm, ids, opt) {
  const harness = process.env.MOD_HARNESS || path.join(HERE, '..', 'ModHarness.js');
  if (!fs.existsSync(harness)) throw new Error(`ModHarness.js not found (${harness}); set MOD_HARNESS`);
  const game = path.resolve(d2rmm, '..');
  const out = fs.mkdtempSync(path.join(os.tmpdir(), 'modorder-audit-'));
  const trace = path.join(out, 'trace.json');
  console.log(`Running ModHarness on ${ids.length} mods (a few minutes)...`);
  const r = spawnSync('node', ['--max-old-space-size=8192', harness, '--game', game, '--max-page', '126', '--keep-going', '--trace', trace,
    ...ids.map((id) => path.join(d2rmm, 'mods', id))], { encoding: 'utf8', maxBuffer: 1 << 30 });
  fs.writeFileSync(path.join(out, 'harness.log'), `${r.stdout || ''}\n--- stderr\n${r.stderr || ''}`);
  (r.stdout || '').split('\n').filter((l) => /^\s+FAILED: /.test(l)).forEach((l) => console.log(`ERROR ${l.trim().slice(8)}`));
  if (!fs.existsSync(trace)) throw new Error(`no trace written (exit ${r.status}); see ${path.join(out, 'harness.log')}`);
  const rep = JSON.parse(readText(trace));
  console.log(`${rep.changedUnits} changed values, ${rep.overwrittenUnits} overwritten by a mod below. Biggest losses (lost -> overwritten by):`);
  rep.losses.slice(0, opt.all ? 1e9 : 40).forEach((l) => console.log(`  ${l.lost} -> ${l.to}  ${l.file}  ${l.count}`));
  console.log(`Full report: ${trace}`);
}

// ------------------------------------------------------------------------------ the window
function gui(d2rmm, opt) {
  const port = Number(opt.port) || 8767;
  const page = readText(path.join(HERE, 'ModOrder.html'));
  let last = null;
  const report = () => {
    const lists = loadLists(d2rmm);
    const list = opt.from ? Object.assign({ installed: null, pluginPrefs: {} }, readJson(opt.from)) : readD2rmmList();
    last = evaluate({ d2rmm, list, lists });
    return last;
  };
  const server = http.createServer(async (req, res) => {
    const send = (code, body, type = 'application/json') => {
      res.writeHead(code, { 'Content-Type': `${type}; charset=utf-8`, 'Cache-Control': 'no-store' });
      res.end(typeof body === 'string' ? body : JSON.stringify(body));
    };
    try {
      if (req.method === 'GET' && (req.url === '/' || req.url === '/index.html')) return send(200, page, 'text/html');
      if (req.method === 'GET' && req.url === '/api/report') return send(200, report());
      if (req.method === 'POST' && req.url === '/api/apply') {
        if (opt.from) return send(400, { error: 'started with --from: nothing to apply to' });
        const r = last || report();
        const backup = await applyOrder(d2rmm, r.order, { restart: false }, '(window)');
        return send(200, { backup, report: report() });
      }
      send(404, { error: 'not found' });
    } catch (e) {
      send(500, { error: e.message || String(e) });
    }
  });
  server.listen(port, '127.0.0.1', () => {
    const url = `http://127.0.0.1:${port}/`;
    console.log(`ModOrder window: ${url}  (Ctrl+C to stop)`);
    if (!opt['no-browser']) spawn('cmd.exe', ['/c', 'start', '""', url], { detached: true, stdio: 'ignore' }).unref();
  });
}

// ------------------------------------------------------------------------------ main
async function main() {
  const { cmd, rest, opt } = args();
  const d2rmm = findD2rmm(opt.d2rmm);
  if (cmd === 'gui') return gui(d2rmm, opt);
  const lists = loadLists(d2rmm);
  if (cmd === 'bestof-rules') {
    console.log(`Best Of rules written to ${writeBestOfRules(d2rmm, lists)}`);
    return;
  }
  if (cmd === 'restore') {
    const saved = readJson(rest[0], null);
    if (!saved || !Array.isArray(saved.modsOrder)) throw new Error('usage: ModOrder restore <a saved mod-list.*.json>');
    const ticked = saved.modsOrder.filter((id) => saved.enabledMods[id]);
    await connectD2rmm(d2rmm, opt.restart);
    await cdp(`localStorage.setItem('enabled-mods', ${JSON.stringify(JSON.stringify(saved.enabledMods))}); localStorage.setItem('mods-order', ${JSON.stringify(JSON.stringify(saved.modsOrder))}); location.reload(); true`);
    console.log(`Restored ${ticked.length} ticked mods from ${rest[0]}.`);
    return;
  }
  const list = opt.from ? Object.assign({ installed: null, pluginPrefs: {} }, readJson(opt.from, null)) : readD2rmmList();
  if (!list || !Array.isArray(list.modsOrder)) throw new Error('could not read a mod list');
  const r = evaluate({ d2rmm, list, lists });
  if (cmd === 'audit') return audit(d2rmm, opt.sorted ? r.order : r.ticked, opt);
  if (opt.json) console.log(JSON.stringify(r, null, 1));
  else printReport(r);
  if (cmd === 'apply') {
    if (opt.from) throw new Error('apply works on the list in D2RMM, not with --from');
    if (!r.moves.length) return;
    const backup = await applyOrder(d2rmm, r.order, opt);
    console.log(`\nD2RMM list set (${r.order.length} ticked). The list before is saved in ${backup}`);
    console.log('Click Install Mods in D2RMM (game closed).');
  }
}
if (require.main === module) {
  main().catch((e) => {
    console.error(`ModOrder: ${e.message || e}`);
    process.exit(1);
  });
}
module.exports = { readLevelDb, readD2rmmList, scanMod, scanPlugins, loadLists, evaluate, bestOfRules, describeMoves };
