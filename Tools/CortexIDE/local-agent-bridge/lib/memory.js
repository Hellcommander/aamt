"use strict";
// Memory: what the agent remembers between chats, as plain Markdown files the user can read and edit.
// The design takes inspiration from the memory features of Claude and Claude Code (memory generated
// from chats, searching past chats, managing, importing and exporting memory); the code and wording
// are this extension's own.
//
// Two scopes, each a folder of one-fact Markdown files plus a MEMORY.md index:
//   user     <history root>/memory                     about the user, shared by every workspace
//   project  <history root>/projects/<slug>/memory     about this workspace
// A memory file:
//   ---
//   name: prefers-powershell
//   description: one line, used to decide relevance
//   type: user | feedback | project | reference
//   ---
//   the fact (feedback / project: followed by Why: and How to apply: lines)

const fs = require("fs");
const path = require("path");
const zlib = require("zlib");

const TYPES = ["user", "feedback", "project", "reference"];
const SCOPES = ["user", "project"];
const INDEX = "MEMORY.md";

function slugName(name) {
  return String(name || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60) || "memory";
}

function oneLine(s, n = 200) {
  const t = String(s == null ? "" : s).replace(/\s+/g, " ").trim();
  return t.length > n ? t.slice(0, n - 1) + "…" : t;
}

/** Frontmatter + body → { name, description, type, body }. */
function parseFile(text) {
  const t = String(text || "").replace(/^﻿/, "");
  const m = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/.exec(t);
  const meta = {};
  if (m) {
    for (const line of m[1].split(/\r?\n/)) {
      const kv = /^\s*([A-Za-z_]+)\s*:\s*(.*)$/.exec(line);
      if (kv) meta[kv[1].toLowerCase()] = kv[2].replace(/^["']|["']$/g, "").trim();
    }
  }
  // Claude Code memory files nest the type under `metadata:`; it is picked up as `type:` above too.
  return { name: meta.name || "", description: meta.description || "", type: TYPES.includes(meta.type) ? meta.type : "user", body: (m ? m[2] : t).trim() };
}

function formatFile({ name, description, type, body }) {
  return ["---", "name: " + slugName(name), "description: " + oneLine(description, 240), "type: " + (TYPES.includes(type) ? type : "user"), "---", "", String(body || "").trim(), ""].join("\n");
}

class MemoryStore {
  /** @param {{root:string, projectDir?:string}} o root = history root (~/.cortexide/agent) */
  constructor({ root, projectDir = "" }) {
    this.root = root;
    this.projectDir = projectDir;
  }

  dir(scope) {
    if (scope === "project") return this.projectDir ? path.join(this.projectDir, "memory") : "";
    return path.join(this.root, "memory");
  }

  scopes() {
    return SCOPES.filter((s) => this.dir(s));
  }

  /** Every memory, both scopes, newest first. */
  list(scope) {
    const out = [];
    for (const sc of scope ? [scope] : this.scopes()) {
      const dir = this.dir(sc);
      let names = [];
      try {
        names = fs.readdirSync(dir).filter((f) => /\.md$/i.test(f) && f !== INDEX);
      } catch {
        continue;
      }
      for (const f of names) {
        const file = path.join(dir, f);
        try {
          const p = parseFile(fs.readFileSync(file, "utf8"));
          out.push({ scope: sc, name: p.name || f.replace(/\.md$/i, ""), description: p.description, type: p.type, body: p.body, file, updated: fs.statSync(file).mtimeMs });
        } catch {
          /* unreadable */
        }
      }
    }
    return out.sort((a, b) => b.updated - a.updated);
  }

  find(name, scope) {
    const n = slugName(name);
    return this.list(scope).find((m) => slugName(m.name) === n) || null;
  }

  /** Add or replace a memory; returns its file. */
  write({ scope = "user", name, description, type, body }) {
    const sc = SCOPES.includes(scope) && this.dir(scope) ? scope : "user";
    if (!String(body || "").trim()) throw new Error("memory body is empty");
    const dir = this.dir(sc);
    fs.mkdirSync(dir, { recursive: true });
    const file = path.join(dir, slugName(name || description || body) + ".md");
    fs.writeFileSync(file, formatFile({ name: name || description || body, description: description || oneLine(body, 120), type, body }), "utf8");
    this.writeIndex(sc);
    return file;
  }

  remove(name, scope) {
    const m = this.find(name, scope);
    if (!m) return null;
    fs.unlinkSync(m.file);
    this.writeIndex(m.scope);
    return m;
  }

  /** MEMORY.md: one line per memory, the part that goes into every prompt. */
  writeIndex(scope) {
    const dir = this.dir(scope);
    if (!dir) return "";
    const items = this.list(scope).sort((a, b) => a.name.localeCompare(b.name));
    const file = path.join(dir, INDEX);
    if (!items.length) {
      try {
        fs.unlinkSync(file);
      } catch {
        /* none */
      }
      return "";
    }
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(file, items.map((m) => "- [" + m.name + "](" + path.basename(m.file) + ") (" + m.type + ") — " + oneLine(m.description, 160)).join("\n") + "\n", "utf8");
    return file;
  }

  /**
   * The memory section of the system prompt: both indexes plus the full text of the most recent
   * memories, within `maxChars`.
   */
  promptText({ maxChars = 6000 } = {}) {
    const all = this.list();
    if (!all.length) return "";
    const head = [
      "Memory (facts kept from earlier chats; they may be out of date — check names and paths before relying on them):",
    ];
    let text = head.join("\n");
    for (const sc of this.scopes()) {
      const mine = all.filter((m) => m.scope === sc);
      if (!mine.length) continue;
      const heading = "\n\n" + (sc === "user" ? "About the user (" : "About this project (") + this.dir(sc) + "):";
      if (text.length + heading.length >= maxChars) break;
      text += heading;
      for (const m of mine) {
        const full = "\n- " + m.name + " (" + m.type + "): " + oneLine(m.body, 400);
        const short = "\n- " + m.name + " (" + m.type + "): " + oneLine(m.description, 160);
        if (text.length + full.length < maxChars) text += full;
        else if (text.length + short.length < maxChars) text += short;
      }
    }
    return text;
  }

  /** A .zip of every memory as Markdown (user/…, project/…). */
  exportZip() {
    const files = [];
    for (const sc of this.scopes()) {
      let names = [];
      try {
        names = fs.readdirSync(this.dir(sc)).filter((f) => /\.md$/i.test(f));
      } catch {
        continue;
      }
      for (const f of names) files.push({ name: sc + "/" + f, data: fs.readFileSync(path.join(this.dir(sc), f)) });
    }
    return { zip: zipFiles(files), count: files.filter((f) => !f.name.endsWith("/" + INDEX)).length };
  }

  /**
   * Import memory files from a folder (e.g. a Claude Code ~/.claude/projects/<slug>/memory).
   * Existing memories with the same name are kept unless `overwrite`.
   */
  importFolder(dir, scope, { overwrite = false } = {}) {
    let names = [];
    try {
      names = fs.readdirSync(dir).filter((f) => /\.md$/i.test(f) && f !== INDEX);
    } catch {
      return { added: 0, skipped: 0 };
    }
    let added = 0;
    let skipped = 0;
    for (const f of names) {
      const p = parseFile(fs.readFileSync(path.join(dir, f), "utf8"));
      const name = p.name || f.replace(/\.md$/i, "");
      if (!p.body || (!overwrite && this.find(name, scope))) {
        skipped++;
        continue;
      }
      this.write({ scope, name, description: p.description, type: p.type, body: p.body });
      added++;
    }
    return { added, skipped };
  }
}

/**
 * Memory pasted back from another assistant: a Markdown list, one fact per bullet, optionally
 * under headings. Each bullet becomes a user-scope memory; the heading goes into its description.
 */
function parsePasted(text) {
  const out = [];
  let heading = "";
  for (const raw of String(text || "").split(/\r?\n/)) {
    const line = raw.trim();
    const h = /^#{1,6}\s+(.*)$/.exec(line);
    if (h) {
      heading = h[1].replace(/[*_`]/g, "").trim();
      continue;
    }
    const b = /^(?:[-*•]|\d+[.)])\s+(.*)$/.exec(line);
    if (!b) continue;
    const fact = b[1].replace(/\*\*/g, "").trim();
    if (fact.length < 4) continue;
    const type = /instruction|respond|style|prefer|feedback|tone/i.test(heading) ? "feedback" : /project|work|code|repo/i.test(heading) ? "project" : "user";
    out.push({ scope: "user", name: slugName(fact.split(/\s+/).slice(0, 6).join(" ")), description: (heading ? heading + ": " : "") + oneLine(fact, 140), type, body: fact });
  }
  return out;
}

/** What to paste into another assistant to get its memory of you back as a list. */
const IMPORT_PROMPT = [
  "Please list everything you have stored or remember about me from our past conversations, so I can move it to another assistant.",
  "Write it as Markdown: a short heading per group (About me, Preferences, How I want you to respond, Work and projects, Tools and setup),",
  "and under each heading one bullet per fact, in plain words. Include only facts and preferences, no commentary, and leave out passwords, keys and other secrets.",
].join(" ");

// ---- generating memory from a chat ------------------------------------------------------------

/** The request that turns recent chat turns into memory updates (a JSON array). */
function extractionMessages({ transcript, existing, includeSensitive = false }) {
  const system =
    "You maintain a coding agent's long-term memory about its user and project. From the conversation, pick out only facts worth " +
    "remembering in future chats, and reply with a JSON array of operations and nothing else.";
  const rules = [
    "Remember durable things: who the user is and how they work; their preferences and corrections to how the agent works (type feedback, with Why: and How to apply: lines);",
    "project goals, constraints and decisions that are not visible in the code (type project); where things live outside the code: dashboards, docs, tools (type reference).",
    "Do not remember: what the code, file layout or git history already shows; details only this task needed; anything from tool output that is not a user's statement or decision.",
    "Never store passwords, API keys, tokens or other secrets, even if they appear in the conversation.",
    includeSensitive
      ? "Sensitive topics (health, religion, politics, sexuality, finances) may be remembered when the user shared them and they are relevant."
      : "Do not remember sensitive personal topics (health, religion, politics, sexuality, finances, other private matters).",
    "Prefer updating an existing memory over adding a near-duplicate; delete a memory the conversation shows is wrong.",
    "Use scope user for facts about the person, project for facts about this workspace. At most 5 operations; an empty array [] is a fine answer.",
    "",
    'Format: [{"op":"add"|"update"|"delete","scope":"user"|"project","name":"short-kebab-name","type":"user"|"feedback"|"project"|"reference","description":"one line","body":"the fact"}]',
  ].join("\n");
  const have = existing.length ? existing.map((m) => "- " + m.scope + "/" + m.name + " (" + m.type + "): " + oneLine(m.description, 140)).join("\n") : "(none yet)";
  return [
    { role: "system", content: system },
    { role: "user", content: rules + "\n\nMemory now:\n" + have + "\n\n<conversation>\n" + transcript + "\n</conversation>\n\nReply with the JSON array only." },
  ];
}

/** Model reply → validated operations (bad entries dropped). */
function parseOperations(text) {
  const t = String(text || "").replace(/<think>[\s\S]*?<\/think>/gi, "");
  const a = t.indexOf("[");
  const b = t.lastIndexOf("]");
  if (a < 0 || b <= a) return [];
  let arr;
  try {
    arr = JSON.parse(t.slice(a, b + 1));
  } catch {
    return [];
  }
  if (!Array.isArray(arr)) return [];
  const SECRET = /(sk-[a-z0-9-]{10,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{12,}|-----BEGIN [A-Z ]*PRIVATE KEY|password\s*[:=]\s*\S+)/i;
  return arr
    .filter((o) => o && typeof o === "object" && ["add", "update", "delete"].includes(o.op) && o.name)
    .filter((o) => o.op === "delete" || (String(o.body || "").trim() && !SECRET.test(String(o.body) + " " + String(o.description || ""))))
    .slice(0, 5)
    .map((o) => ({ op: o.op, scope: o.scope === "project" ? "project" : "user", name: slugName(o.name), type: TYPES.includes(o.type) ? o.type : "user", description: oneLine(o.description || o.body, 200), body: String(o.body || "").trim() }));
}

/** Apply operations; returns a short report like "added 2, updated 1". */
function applyOperations(store, ops) {
  const done = { added: [], updated: [], deleted: [] };
  for (const o of ops) {
    if (o.op === "delete") {
      if (store.remove(o.name, o.scope) || store.remove(o.name)) done.deleted.push(o.name);
      continue;
    }
    const had = store.find(o.name, o.scope);
    store.write(o);
    (had ? done.updated : done.added).push(o.name);
  }
  return done;
}

// ---- searching past chats ---------------------------------------------------------------------

/** Every saved chat under the history root: { id, title, model, updated, workspace, file }. */
function allChats(root) {
  const out = [];
  let projects = [];
  try {
    projects = fs.readdirSync(path.join(root, "projects"));
  } catch {
    return out;
  }
  for (const p of projects) {
    const dir = path.join(root, "projects", p, "sessions");
    let ids = [];
    try {
      ids = fs.readdirSync(dir);
    } catch {
      continue;
    }
    for (const id of ids) {
      const file = path.join(dir, id, "session.json");
      try {
        const st = fs.statSync(file);
        out.push({ id, folder: p, file, updated: st.mtimeMs });
      } catch {
        /* no session file */
      }
    }
  }
  return out.sort((a, b) => b.updated - a.updated);
}

function readChat(file) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return null;
  }
}

function chatText(s) {
  const rows = Array.isArray(s.log) && s.log.length ? s.log : (s.history || []).map((h) => ({ cls: h.role, text: h.content }));
  return rows.filter((r) => r && (r.cls === "user" || r.cls === "assistant" || r.cls === "compact")).map((r) => (r.cls === "compact" ? String(r.summary || "") : String(r.text || ""))).join("\n");
}

/**
 * Search saved chats for all the words of `query`; best matches first, each with a snippet.
 * `folder` limits the search to one workspace's chats (its history folder name).
 */
function searchChats(root, query, { folder = "", limit = 8, exclude = "" } = {}) {
  const words = String(query || "").toLowerCase().split(/\s+/).filter((w) => w.length > 1);
  if (!words.length) return [];
  const hits = [];
  for (const c of allChats(root)) {
    if (folder && c.folder !== folder) continue;
    if (exclude && c.id === exclude) continue;
    const s = readChat(c.file);
    if (!s) continue;
    const text = chatText(s);
    const hay = (String(s.title || "") + "\n" + text).toLowerCase();
    if (!words.every((w) => hay.includes(w))) continue;
    const score = words.reduce((n, w) => n + hay.split(w).length - 1, 0) + (words.every((w) => String(s.title || "").toLowerCase().includes(w)) ? 20 : 0);
    const at = Math.max(0, text.toLowerCase().indexOf(words[0]));
    hits.push({ id: c.id, folder: c.folder, title: s.title || "Untitled chat", model: s.model || "", updated: c.updated, score, snippet: oneLine(text.slice(Math.max(0, at - 120), at + 280), 360) });
  }
  return hits.sort((a, b) => b.score - a.score || b.updated - a.updated).slice(0, limit);
}

function findChat(root, id) {
  const want = String(id || "").trim();
  return allChats(root).find((c) => c.id === want || (want.length >= 6 && c.id.startsWith(want))) || null;
}

// ---- zip (stored + deflate, no dependencies) --------------------------------------------------

const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

function crc32(buf) {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) c = CRC_TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

/** @param {{name:string, data:Buffer}[]} files */
function zipFiles(files) {
  const parts = [];
  const central = [];
  let offset = 0;
  const now = new Date();
  const dosTime = ((now.getHours() << 11) | (now.getMinutes() << 5) | (now.getSeconds() >> 1)) & 0xffff;
  const dosDate = (((now.getFullYear() - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate()) & 0xffff;
  for (const f of files) {
    const name = Buffer.from(f.name, "utf8");
    const data = Buffer.isBuffer(f.data) ? f.data : Buffer.from(String(f.data), "utf8");
    const comp = zlib.deflateRawSync(data);
    const crc = crc32(data);
    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4);
    local.writeUInt16LE(0x0800, 6); // UTF-8 names
    local.writeUInt16LE(8, 8); // deflate
    local.writeUInt16LE(dosTime, 10);
    local.writeUInt16LE(dosDate, 12);
    local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(comp.length, 18);
    local.writeUInt32LE(data.length, 22);
    local.writeUInt16LE(name.length, 26);
    local.writeUInt16LE(0, 28);
    parts.push(local, name, comp);
    const cen = Buffer.alloc(46);
    cen.writeUInt32LE(0x02014b50, 0);
    cen.writeUInt16LE(20, 4);
    cen.writeUInt16LE(20, 6);
    cen.writeUInt16LE(0x0800, 8);
    cen.writeUInt16LE(8, 10);
    cen.writeUInt16LE(dosTime, 12);
    cen.writeUInt16LE(dosDate, 14);
    cen.writeUInt32LE(crc, 16);
    cen.writeUInt32LE(comp.length, 20);
    cen.writeUInt32LE(data.length, 24);
    cen.writeUInt16LE(name.length, 28);
    cen.writeUInt32LE(offset, 42);
    central.push(cen, name);
    offset += local.length + name.length + comp.length;
  }
  const cenBuf = Buffer.concat(central);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(files.length, 8);
  end.writeUInt16LE(files.length, 10);
  end.writeUInt32LE(cenBuf.length, 12);
  end.writeUInt32LE(offset, 16);
  return Buffer.concat([...parts, cenBuf, end]);
}

module.exports = {
  MemoryStore,
  TYPES,
  SCOPES,
  slugName,
  parseFile,
  formatFile,
  parsePasted,
  IMPORT_PROMPT,
  extractionMessages,
  parseOperations,
  applyOperations,
  searchChats,
  findChat,
  readChat,
  chatText,
  allChats,
  zipFiles,
  crc32,
};
