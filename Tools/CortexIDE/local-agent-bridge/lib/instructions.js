"use strict";

// Project instructions for the system prompt, and AGENTS.md files found while the agent reads.
// Design follows opencode's instructions (https://github.com/anomalyco/opencode, MIT, Copyright (c)
// 2025 opencode): a global AGENTS.md first, then each workspace folder's AGENTS.md and those of its
// parent folders up to the repository root, then configured extra files or globs; AGENTS.md files in
// sub-folders are added once, when the agent first reads something below them.
// Written from the documented behaviour; no opencode source is copied.

const fs = require("fs");
const path = require("path");
const os = require("os");

const PROJECT_FILES = ["AGENTS.md", "CLAUDE.md", ".cursorrules"];
const PER_FILE = 2000;

function read(p, max = PER_FILE) {
  try {
    const st = fs.statSync(p);
    if (!st.isFile()) return "";
    return fs.readFileSync(p, "utf8").replace(/^\uFEFF/, "").slice(0, max).trim();
  } catch {
    return "";
  }
}

/** The repository root above dir (a folder with .git), or "" when there is none within 8 levels. */
function repoRoot(dir) {
  let d = path.resolve(dir);
  for (let i = 0; i < 8; i++) {
    if (fs.existsSync(path.join(d, ".git"))) return d;
    const up = path.dirname(d);
    if (up === d) break;
    d = up;
  }
  return "";
}

/** dir and its parents up to (and including) stop, nearest first. */
function upTo(dir, stop) {
  const out = [];
  let d = path.resolve(dir);
  const s = path.resolve(stop).toLowerCase();
  for (let i = 0; i < 12; i++) {
    out.push(d);
    if (d.toLowerCase() === s) break;
    const up = path.dirname(d);
    if (up === d) break;
    d = up;
  }
  return out;
}

function cursorRules(root) {
  const out = [];
  const dir = path.join(root, ".cursor", "rules");
  let names = [];
  try {
    names = fs.readdirSync(dir);
  } catch {
    return out;
  }
  for (const n of names) {
    if (!/\.mdc?$/i.test(n)) continue;
    const text = read(path.join(dir, n), 20000);
    if (/alwaysApply:\s*true/i.test(text)) out.push({ file: path.join(dir, n), label: n, text: text.replace(/^---[\s\S]*?---\s*/, "").slice(0, 1500) });
  }
  return out;
}

const globRe = (s) => new RegExp("^" + s.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*").replace(/\?/g, ".") + "$", "i");

/** Files for one configured entry: a path or a glob in its last segment; relative ones per workspace folder. */
function configured(entry, roots, home) {
  let e = String(entry || "").trim();
  if (!e || /^https?:\/\//i.test(e)) return []; // URLs are not fetched
  e = e.replace(/^(~|\$HOME)(?=$|[\\/])/, home);
  const bases = path.isAbsolute(e) ? [""] : roots;
  const out = [];
  for (const b of bases) {
    const full = b ? path.join(b, e) : e;
    const dir = path.dirname(full);
    const leaf = path.basename(full);
    if (/[*?]/.test(leaf)) {
      let names = [];
      try {
        names = fs.readdirSync(dir).sort();
      } catch {
        continue;
      }
      const re = globRe(leaf);
      for (const n of names) if (re.test(n)) out.push(path.join(dir, n));
    } else out.push(full);
  }
  return out;
}

/**
 * Instructions for the system prompt, in order: global, each folder (nearest first, up to its repo
 * root), Cursor alwaysApply rules, configured extras.
 * @returns {{ text: string, files: string[] }} files: every file included (for nested de-duplication)
 */
function collect({ roots = [], home = os.homedir(), extra = [], maxTotal = 8000 } = {}) {
  const seen = new Set();
  const parts = [];
  const add = (file, label, text) => {
    const key = path.resolve(file).toLowerCase();
    if (seen.has(key) || !text) return;
    seen.add(key);
    parts.push(label + ":\n" + text);
  };
  for (const g of [path.join(home, ".cortexide", "AGENTS.md"), path.join(home, ".config", "opencode", "AGENTS.md")]) add(g, "Global " + path.basename(g) + " (" + g + ")", read(g));
  for (const root of roots) {
    if (!root) continue;
    const repo = repoRoot(root);
    const chain = repo ? upTo(root, repo) : [path.resolve(root)];
    for (const d of chain) {
      for (const n of PROJECT_FILES) {
        const p = path.join(d, n);
        const rel = path.relative(root, p) || n;
        add(p, roots.length > 1 || d !== path.resolve(root) ? rel.replace(/\\/g, "/") + " (" + path.basename(root) + ")" : n, read(p));
      }
    }
    for (const r of cursorRules(root)) add(r.file, r.label, r.text);
  }
  for (const entry of extra || []) for (const p of configured(entry, roots, home)) add(p, path.basename(p), read(p));
  let text = parts.join("\n\n");
  if (text.length > maxTotal) text = text.slice(0, maxTotal) + "\n…[instructions cut at " + maxTotal + " chars]";
  return { text, files: [...seen] };
}

/**
 * AGENTS.md files between a file the agent read and the workspace folder holding it, nearest first,
 * that have not been added yet (`loaded` holds lower-case paths and is updated).
 * @returns {{file:string, text:string}[]}
 */
function nested(abs, roots, loaded) {
  const file = path.resolve(abs);
  const root = (roots || []).map((r) => path.resolve(r)).find((r) => file.toLowerCase().startsWith(r.toLowerCase() + path.sep));
  if (!root) return [];
  const out = [];
  let d = path.dirname(file);
  while (d.length > root.length && d.toLowerCase().startsWith(root.toLowerCase())) {
    const p = path.join(d, "AGENTS.md");
    const key = p.toLowerCase();
    if (!loaded.has(key)) {
      const text = read(p);
      if (text) {
        loaded.add(key);
        out.push({ file: p, text });
      }
    }
    d = path.dirname(d);
  }
  return out;
}

module.exports = { collect, nested, repoRoot, configured };
