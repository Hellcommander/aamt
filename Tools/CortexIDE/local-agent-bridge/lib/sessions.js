"use strict";

// Chat history cache for the Agent panel, laid out like Claude Code's ~/.claude/projects, with
// three levels of index so chats that run side by side never share a progress file:
//
//   <root>/index.json                                   MASTER index: every workspace folder that has chats
//   <root>/projects/<workspace-slug>/index.json         MAIN index for that folder: one entry per chat
//                                                       (title, model, status, …) + live file claims
//   <root>/projects/<workspace-slug>/sessions/<id>/
//       session.json                                    the chat itself (log, history, todos, progress)
//       index.json                                      SUB-index: files this chat touched, its turns
//       progress.md                                     this chat's progress digest (human readable)
//
// File claims: while a chat runs, every file it edits is claimed in the main index. Another
// running chat that tries to edit a claimed file gets a refusal naming the owner, instead of
// silently overwriting its work. Claims are dropped when the owning turn ends, and claims of a
// process that is gone (editor closed or crashed) are ignored.
//
// Several windows, one folder: the sub-indexes are the source of truth for each chat's header; the
// main index is a merged cache of them. Every write of the main index happens under a lock file
// (index.json.lock) and is read-disk → merge → write: chats this process changed win, chats other
// windows added or changed are taken in, chats deleted anywhere leave a tombstone (`removed`) so
// no window brings them back. A lost or damaged main index is rebuilt from the sub-indexes.
//
// <root> defaults to %USERPROFILE%\.cortexide\agent. Plain node (no vscode) so it is testable.

const fs = require("fs");
const os = require("os");
const path = require("path");

const INDEX_VERSION = 2;
const MAX_SUB_TURNS = 50;
const TOMBSTONE_MS = 30 * 24 * 3600 * 1000;
/** Fields kept in the main index; everything else lives only in the chat's session.json. */
const META = ["id", "title", "created", "updated", "provider", "baseUrl", "model", "status", "unread", "pinned", "open", "group", "turns", "importedFrom", "ccSession", "limits", "pid", "metaAt"];
/** Fields the user changes from any window (rename, pin, close tab); a running chat's save keeps the newest. */
const USER_FIELDS = ["title", "pinned", "open", "group", "limits"];

function defaultRoot() {
  return path.join(process.env.USERPROFILE || os.homedir(), ".cortexide", "agent");
}

/** Same scheme as Claude Code's project folders: D:\games\x → D--games-x. */
function slug(workspace) {
  return String(workspace || "no-workspace").replace(/[^A-Za-z0-9]/g, "-").slice(0, 120) || "no-workspace";
}

function newId() {
  return Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 8);
}

function safeId(id) {
  return String(id).replace(/[^\w.-]/g, "_");
}

/** Claim key for a file: one per file, case-insensitive where the file system is. */
function fileKey(abs) {
  const p = path.resolve(String(abs));
  return process.platform === "win32" || process.platform === "darwin" ? p.toLowerCase() : p;
}

function pidAlive(pid) {
  if (!pid) return false;
  if (pid === process.pid) return true;
  try {
    process.kill(pid, 0);
    return true;
  } catch (e) {
    return e.code === "EPERM"; // exists, owned by someone else
  }
}

/** A short chat title from the first request: first line, no markdown noise, at most 60 chars. */
function titleFrom(text) {
  const line = String(text || "")
    .replace(/<[^>]+>/g, " ")
    .split(/\r?\n/)
    .map((l) => l.replace(/[#*`>_]+/g, " ").replace(/\s+/g, " ").trim())
    .find(Boolean);
  if (!line) return "New chat";
  return line.length > 60 ? line.slice(0, 57).replace(/\s+\S*$/, "") + "…" : line;
}

function writeAtomic(file, data) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = file + "." + process.pid + ".tmp";
  try {
    fs.writeFileSync(tmp, data, "utf8");
    fs.renameSync(tmp, file);
  } catch {
    // A virus scanner holding the target can make the rename fail on Windows: write in place.
    try {
      fs.unlinkSync(tmp);
    } catch {
      /* already gone */
    }
    fs.writeFileSync(file, data, "utf8");
  }
}

function sleepMs(ms) {
  try {
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
  } catch {
    const end = Date.now() + ms;
    while (Date.now() < end) {
      /* spin */
    }
  }
}

/**
 * Run fn while holding <file>.lock (created exclusively). A lock of a dead process, of this process
 * (left by a crash: our code never holds it across an await) or older than `stale` ms is broken.
 * After `wait` ms fn runs anyway: a slow disk must not hang the editor.
 */
function withLock(file, fn, { wait = 3000, stale = 10000 } = {}) {
  const lock = file + ".lock";
  let fd = null;
  try {
    fs.mkdirSync(path.dirname(lock), { recursive: true });
  } catch {
    /* the open below reports it */
  }
  const until = Date.now() + wait;
  for (;;) {
    try {
      fd = fs.openSync(lock, "wx");
      fs.writeSync(fd, String(process.pid));
      break;
    } catch (e) {
      if (e.code !== "EEXIST") break; // cannot lock here (read-only?): go on without
      let holder = 0;
      let age = 0;
      try {
        holder = parseInt(fs.readFileSync(lock, "utf8"), 10) || 0;
        age = Date.now() - fs.statSync(lock).mtimeMs;
      } catch {
        continue; // released meanwhile
      }
      if (age > stale || (holder && (holder === process.pid || !pidAlive(holder)))) {
        try {
          fs.unlinkSync(lock);
        } catch {
          /* someone else broke it */
        }
        continue;
      }
      if (Date.now() > until) break;
      sleepMs(15);
    }
  }
  try {
    return fn();
  } finally {
    if (fd !== null) {
      try {
        fs.closeSync(fd);
      } catch {
        /* closed */
      }
      try {
        fs.unlinkSync(lock);
      } catch {
        /* gone */
      }
    }
  }
}

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return null;
  }
}

function pickMeta(s) {
  const m = {};
  for (const k of META) if (s[k] !== undefined) m[k] = s[k];
  return m;
}

/** The master index; rebuilt from projects/*\/index.json when it is missing or damaged. */
function readMaster(root) {
  root = root || defaultRoot();
  const raw = readJson(path.join(root, "index.json"));
  if (raw && Array.isArray(raw.workspaces)) return raw;
  const out = { version: INDEX_VERSION, workspaces: [] };
  let names = [];
  try {
    names = fs.readdirSync(path.join(root, "projects"));
  } catch {
    return out;
  }
  for (const n of names) {
    const dir = path.join(root, "projects", n);
    const main = readJson(path.join(dir, "index.json"));
    if (!main || !Array.isArray(main.sessions)) continue;
    out.workspaces.push({
      slug: n,
      workspace: main.workspace || "",
      dir,
      chats: main.sessions.length,
      running: main.sessions.filter((e) => e.status === "running").length,
      updated: main.updated || Math.max(0, ...main.sessions.map((e) => e.updated || 0)),
    });
  }
  if (out.workspaces.length) writeAtomic(path.join(root, "index.json"), JSON.stringify(out, null, 1));
  return out;
}

class SessionStore {
  /**
   * @param {{ root?: string, workspace?: string, limit?: number }} opts
   *   limit: keep at most this many chats; the oldest unpinned, idle ones are dropped first.
   */
  constructor({ root, workspace, limit = 200, pid } = {}) {
    this.pid = pid || process.pid; // the owner stamped on running chats and claims (tests fake a second window)
    this.root = root || defaultRoot();
    this.workspace = workspace || "";
    this.slug = slug(workspace);
    this.dir = path.join(this.root, "projects", this.slug);
    this.limit = Math.max(10, limit || 200);
    this.index = null;
    this.claims = null; // fileKey → { id, path, pid, since, title, model }
    this.removed = {}; // id → time it was deleted (tombstones, shared between windows)
    this.dirty = new Set(); // ids this process changed since its last write of the main index
    this.gone = new Set(); // ids this process deleted since its last write
    this.seen = ""; // mtime:size of the main index as this process last read or wrote it
  }

  /** The folder of one chat: session.json, index.json (sub-index), progress.md. */
  chatDir(id) {
    return path.join(this.dir, "sessions", safeId(id));
  }

  file(id) {
    return path.join(this.chatDir(id), "session.json");
  }

  subFile(id) {
    return path.join(this.chatDir(id), "index.json");
  }

  progressFile(id) {
    return path.join(this.chatDir(id), "progress.md");
  }

  mainFile() {
    return path.join(this.dir, "index.json");
  }

  masterFile() {
    return path.join(this.root, "index.json");
  }

  /** Before 2.7.1 a chat was one flat sessions/<id>.json: move it into its own folder on first read. */
  legacyFile(id) {
    return path.join(this.dir, "sessions", safeId(id) + ".json");
  }

  readSession(id) {
    const s = readJson(this.file(id));
    if (s) return s;
    const old = readJson(this.legacyFile(id));
    if (!old) return null;
    writeAtomic(this.file(id), JSON.stringify(old));
    try {
      fs.unlinkSync(this.legacyFile(id));
    } catch {
      /* keep it; the folder copy wins from now on */
    }
    return old;
  }

  stamp() {
    try {
      const st = fs.statSync(this.mainFile());
      return st.mtimeMs + ":" + st.size;
    } catch {
      return "";
    }
  }

  load() {
    if (this.index) {
      this.sync();
      return this.index;
    }
    const raw = readJson(this.mainFile());
    this.seen = this.stamp();
    if (raw && Array.isArray(raw.sessions)) {
      this.index = raw.sessions.filter((e) => e && e.id);
      this.claims = raw.claims && typeof raw.claims === "object" ? raw.claims : {};
      this.removed = raw.removed && typeof raw.removed === "object" ? raw.removed : {};
    } else {
      this.claims = {};
      this.removed = {};
      this.index = this.rebuild();
    }
    // The sub-indexes are the truth: a chat folder the main index does not list (a write that lost
    // a race before 2.7.2, or a crash between the two writes) is listed again, unless tombstoned.
    let fixed = false;
    const known = new Set(this.index.map((e) => e.id));
    for (const m of this.scanSubs()) {
      if (known.has(m.id) || this.removed[m.id]) continue;
      this.index.push(m);
      this.dirty.add(m.id);
      fixed = true;
    }
    // A chat that was "running" in an editor that is gone did not finish. One that runs in
    // another, still open window of the same workspace is left alone.
    for (const e of this.index) {
      if (e.status === "running" && (!e.pid || e.pid === this.pid || !pidAlive(e.pid))) {
        e.status = "stopped";
        delete e.pid;
        this.dirty.add(e.id);
        fixed = true;
      }
    }
    for (const [k, c] of Object.entries(this.claims)) {
      if (!this.claimLive(c)) {
        delete this.claims[k];
        fixed = true;
      }
    }
    if (fixed) this.flush();
    return this.index;
  }

  /**
   * The main index is missing or damaged: rebuild it from the chats' sub-indexes (their headers),
   * falling back to session.json for chats without one and to pre-2.7.1 flat files.
   */
  rebuild() {
    const out = this.scanSubs().filter((m) => !this.removed[m.id]);
    for (const m of out) this.dirty.add(m.id);
    this.index = out;
    if (out.length) this.flush();
    return out;
  }

  /** Index entries read from every chat folder's sub-index (session.json / flat file as fallback). */
  scanSubs() {
    const out = [];
    let names = [];
    try {
      names = fs.readdirSync(path.join(this.dir, "sessions"), { withFileTypes: true });
    } catch {
      return out;
    }
    const seen = new Set();
    for (const d of names) {
      let s = null;
      if (d.isDirectory()) {
        const sub = readJson(path.join(this.dir, "sessions", d.name, "index.json"));
        if (sub && sub.id && sub.created) s = { ...sub, turns: typeof sub.turnCount === "number" ? sub.turnCount : 0 };
        else s = readJson(path.join(this.dir, "sessions", d.name, "session.json"));
      } else if (d.name.endsWith(".json")) s = readJson(path.join(this.dir, "sessions", d.name));
      if (s && s.id && !seen.has(s.id)) {
        seen.add(s.id);
        out.push(pickMeta(s));
      }
    }
    return out;
  }

  /** Another window may have written the main index since this process read it: take its changes in. */
  sync() {
    const st = this.stamp();
    if (!st || st === this.seen) return false;
    const disk = readJson(this.mainFile());
    if (!disk || !Array.isArray(disk.sessions)) return false; // half-written or damaged: keep ours
    this.merge(disk);
    this.seen = st;
    return true;
  }

  /**
   * Merge the disk copy of the main index into memory. Chats this process changed (dirty) keep its
   * version; every other chat takes the disk version; tombstoned chats go; claims of this process
   * stay, claims of other live processes come from disk.
   */
  merge(disk) {
    const now = Date.now();
    const removed = { ...(disk.removed && typeof disk.removed === "object" ? disk.removed : {}), ...this.removed };
    for (const id of this.gone) removed[id] = removed[id] || now;
    for (const id of this.dirty) if (!this.gone.has(id)) delete removed[id];
    for (const [id, t] of Object.entries(removed)) if (now - t > TOMBSTONE_MS) delete removed[id];
    const mine = new Map((this.index || []).map((e) => [e.id, e]));
    const out = [];
    const seen = new Set();
    for (const d of disk.sessions || []) {
      if (!d || !d.id || seen.has(d.id) || removed[d.id]) continue;
      seen.add(d.id);
      const m = mine.get(d.id);
      let e = m && this.dirty.has(d.id) ? m : d;
      if (e === d && e.status === "running" && e.pid !== this.pid && !pidAlive(e.pid)) {
        e = { ...d, status: "stopped" }; // its window closed mid-run
        delete e.pid;
        this.dirty.add(e.id);
      }
      out.push(e);
    }
    for (const e of this.index || []) {
      if (seen.has(e.id) || removed[e.id]) continue;
      // Not on disk: created here and not written yet, or the disk index was rebuilt without it.
      if (this.dirty.has(e.id) || fs.existsSync(this.chatDir(e.id))) {
        out.push(e);
        seen.add(e.id);
      }
    }
    this.index = out;
    this.removed = removed;
    const next = {};
    for (const [k, c] of Object.entries(this.claims || {})) if (c && c.pid === this.pid) next[k] = c;
    const theirs = disk.claims && typeof disk.claims === "object" ? disk.claims : {};
    for (const [k, c] of Object.entries(theirs)) if (c && c.pid !== this.pid && pidAlive(c.pid) && !next[k]) next[k] = c;
    this.claims = next;
  }

  /** Under the lock: merge with the disk copy, run `fn` (may return false to skip the write), write. */
  commit(fn) {
    let wrote = false;
    const out = withLock(this.mainFile(), () => {
      const disk = readJson(this.mainFile());
      // Unreadable (damaged, or caught mid-write by a non-atomic fallback): the chat folders' sub-indexes stand in.
      this.merge(disk && Array.isArray(disk.sessions) ? disk : { sessions: this.scanSubs(), claims: {}, removed: {} });
      const r = fn ? fn() : undefined;
      if (r === false) return r;
      this.writeMain();
      wrote = true;
      return r;
    });
    if (wrote) this.registerMaster();
    return out;
  }

  writeMain() {
    writeAtomic(
      this.mainFile(),
      JSON.stringify(
        { version: INDEX_VERSION, workspace: this.workspace, slug: this.slug, updated: Date.now(), sessions: this.index || [], claims: this.claims || {}, removed: this.removed || {} },
        null,
        1
      )
    );
    this.dirty.clear();
    this.gone.clear();
    this.seen = this.stamp();
  }

  /** Write the main index (merged with what other windows wrote), then this folder's master line. */
  flush() {
    if (!this.claims) this.claims = {};
    this.commit();
  }

  registerMaster() {
    withLock(this.masterFile(), () => this.writeMaster());
  }

  writeMaster(now = Date.now()) {
    const master = readMaster(this.root);
    const list = this.index || [];
    const entry = {
      slug: this.slug,
      workspace: this.workspace,
      dir: this.dir,
      chats: list.length,
      running: list.filter((e) => e.status === "running").length,
      claims: Object.keys(this.claims || {}).length,
      updated: now,
    };
    const i = master.workspaces.findIndex((w) => w.slug === this.slug);
    if (i >= 0) master.workspaces[i] = entry;
    else master.workspaces.push(entry);
    master.version = INDEX_VERSION;
    master.workspaces.sort((a, b) => (b.updated || 0) - (a.updated || 0));
    writeAtomic(this.masterFile(), JSON.stringify(master, null, 1));
  }

  /** Index entries: pinned first, then most recently updated. */
  list() {
    return [...this.load()].sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0) || (b.updated || 0) - (a.updated || 0));
  }

  meta(id) {
    return this.load().find((e) => e.id === id) || null;
  }

  get(id) {
    if (!id || !this.meta(id)) return null;
    const s = this.readSession(id);
    if (!s) return null;
    // `workspace`: the folder this chat works in (its store's folder), so a window can run chats of other folders.
    return { log: [], history: [], todos: [], progress: null, importedFrom: "", ...s, ...this.meta(id), workspace: this.workspace };
  }

  /** A new chat. `init` may carry provider/baseUrl/model, title, group, log, history, … */
  create(init = {}) {
    const now = Date.now();
    const s = {
      log: [],
      history: [],
      todos: [],
      progress: null,
      importedFrom: "",
      title: "New chat",
      provider: "",
      baseUrl: "",
      model: "",
      limits: { preset: "standard" }, // per-chat output limits, see session-limits.js
      status: "idle",
      unread: false,
      pinned: false,
      open: true,
      turns: 0,
      ...init,
      workspace: this.workspace,
      id: init.id || newId(),
      created: now,
      updated: now,
    };
    this.load().push(pickMeta(s));
    this.save(s, { touch: false });
    this.prune();
    return s;
  }

  /** Write the chat, its sub-index header and its main-index entry. touch=false keeps its place in the list. */
  save(s, { touch = true } = {}) {
    if (!s || !s.id) return;
    if (touch) s.updated = Date.now();
    s.turns = (s.log || []).filter((r) => r.cls === "user" && !r.steered).length; // steered messages join a running turn
    if (s.status === "running") s.pid = this.pid;
    else delete s.pid;
    const list = this.load();
    // Renamed, pinned or closed in another window (or by update()) after this copy was loaded: keep that.
    const cur = list.find((e) => e.id === s.id);
    if (cur && (cur.metaAt || 0) > (s.metaAt || 0)) {
      for (const k of USER_FIELDS) if (cur[k] !== undefined) s[k] = cur[k];
      s.metaAt = cur.metaAt;
    }
    writeAtomic(this.file(s.id), JSON.stringify(s));
    this.writeSub(s.id, pickMeta(s));
    const i = list.findIndex((e) => e.id === s.id);
    if (i >= 0) list[i] = pickMeta(s);
    else list.push(pickMeta(s));
    this.dirty.add(s.id);
    this.flush();
  }

  /** Change index fields (title, pinned, open, unread, status, model, …) without loading the log. */
  update(id, patch) {
    const e = this.meta(id);
    if (!e) return null;
    patch = { ...patch };
    if (USER_FIELDS.some((k) => k in patch)) patch.metaAt = Date.now();
    Object.assign(e, patch);
    if ("status" in patch) {
      if (patch.status === "running") e.pid = patch.pid = this.pid;
      else delete e.pid;
    }
    const s = this.readSession(id);
    if (s) writeAtomic(this.file(id), JSON.stringify({ ...s, ...patch }));
    this.writeSub(id, pickMeta(e));
    this.dirty.add(id);
    this.flush();
    return e;
  }

  /** The chat runs in another, still open window of this workspace: its index entry, else null. */
  runningElsewhere(id) {
    const e = this.meta(id);
    return e && e.status === "running" && e.pid && e.pid !== this.pid && pidAlive(e.pid) ? e : null;
  }

  /** Delete a chat everywhere (tombstoned for other windows). Refused while another window runs it. */
  remove(id) {
    const list = this.load();
    const i = list.findIndex((e) => e.id === id);
    if (i < 0 || this.runningElsewhere(id)) return false;
    list.splice(i, 1);
    this.gone.add(id);
    this.dirty.delete(id);
    for (const [k, c] of Object.entries(this.claims || {})) if (c.id === id) delete this.claims[k];
    try {
      fs.rmSync(this.chatDir(id), { recursive: true, force: true });
    } catch {
      /* in use; the index no longer points at it */
    }
    try {
      fs.unlinkSync(this.legacyFile(id));
    } catch {
      /* none */
    }
    this.flush();
    return true;
  }

  /** Over the limit: drop the oldest chats that are not pinned, open or running. */
  prune() {
    const list = this.load();
    if (list.length <= this.limit) return [];
    const drop = list
      .filter((e) => !e.pinned && !e.open && e.status !== "running")
      .sort((a, b) => (a.updated || 0) - (b.updated || 0))
      .slice(0, list.length - this.limit)
      .map((e) => e.id);
    for (const id of drop) this.remove(id);
    return drop;
  }

  /** Chats whose title or text contains every word of the query (case-insensitive). */
  search(query) {
    const words = String(query || "").toLowerCase().split(/\s+/).filter(Boolean);
    if (!words.length) return this.list();
    return this.list().filter((e) => {
      let hay = String(e.title || "") + " " + (e.model || "");
      const s = this.readSession(e.id);
      if (s && Array.isArray(s.log)) hay += " " + s.log.map((r) => (r.cls === "user" || r.cls === "assistant" ? r.text : "")).join(" ");
      hay = hay.toLowerCase();
      return words.every((w) => hay.includes(w));
    });
  }

  // ---- per-chat sub-index ------------------------------------------------------------------

  /** A chat's sub-index: its header (id, title, model, …), files it touched, its turns. */
  subIndex(id) {
    const raw = readJson(this.subFile(id));
    const sub = raw && typeof raw === "object" ? raw : {};
    return { ...sub, id, files: sub.files && typeof sub.files === "object" ? sub.files : {}, turns: Array.isArray(sub.turns) ? sub.turns : [] };
  }

  writeSub(id, patch) {
    if (!this.meta(id) && !(patch && patch.id)) return null;
    patch = { ...patch };
    // The header's `turns` is the main index's count of user turns; the sub-index's `turns` is the
    // list of finished turns. Keep the count under its own name so a header write never wipes the list.
    if (patch.turns != null && !Array.isArray(patch.turns)) {
      patch.turnCount = patch.turns;
      delete patch.turns;
    }
    const sub = { ...this.subIndex(id), ...patch, id, version: INDEX_VERSION };
    writeAtomic(this.subFile(id), JSON.stringify(sub, null, 1));
    return sub;
  }

  /** Note in the chat's sub-index that it changed a file (kind: edit, write, delete, …). */
  touchFile(id, abs, kind = "edit") {
    const sub = this.subIndex(id);
    const k = fileKey(abs);
    const now = Date.now();
    const f = sub.files[k] || { path: path.resolve(String(abs)), first: now, edits: 0 };
    f.edits = (f.edits || 0) + 1;
    f.last = now;
    f.kind = kind;
    sub.files[k] = f;
    return this.writeSub(id, { files: sub.files });
  }

  /** Append one finished turn to the chat's sub-index (prompt, model, status, files changed). */
  recordTurn(id, turn) {
    const sub = this.subIndex(id);
    sub.turns.push({ at: Date.now(), ...turn });
    return this.writeSub(id, { turns: sub.turns.slice(-MAX_SUB_TURNS) });
  }

  /** Write this chat's own progress.md (no other chat writes it). Returns its path, or "". */
  writeProgress(id, body) {
    const e = this.meta(id) || {};
    const file = this.progressFile(id);
    try {
      writeAtomic(
        file,
        "# Agent progress — " + (e.title || "chat " + id) + " (auto-generated)\n\n" +
          "_Chat " + id + (e.model ? " · " + e.model : "") + " · updated " + new Date().toISOString() + "_\n\n" +
          String(body || "(nothing recorded)") + "\n"
      );
      this.writeSub(id, { progress: file });
      return file;
    } catch {
      return "";
    }
  }

  /** Other chats in this folder that also touched files this chat touched. */
  overlaps(id) {
    const mine = this.subIndex(id).files;
    const keys = Object.keys(mine);
    if (!keys.length) return [];
    const out = [];
    for (const e of this.load()) {
      if (e.id === id) continue;
      const theirs = this.subIndex(e.id).files;
      const shared = keys.filter((k) => theirs[k]).map((k) => mine[k].path);
      if (shared.length) out.push({ id: e.id, title: e.title || "New chat", model: e.model || "", status: e.status || "idle", files: shared });
    }
    return out;
  }

  // ---- file claims (main index) ------------------------------------------------------------

  /** A claim still counts while its process lives and (in this process) its chat is running. */
  claimLive(c) {
    if (!c || !pidAlive(c.pid)) return false;
    const e = (this.index || []).find((x) => x.id === c.id);
    // Another window's chat that its index entry shows as finished no longer holds anything.
    if (c.pid !== this.pid) return !e || e.status === "running";
    return !!e && e.status === "running";
  }

  /** Claims written by other windows of this workspace: the disk copy is their source of truth. */
  refreshClaims() {
    this.load();
    const disk = readJson(this.mainFile());
    if (disk && Array.isArray(disk.sessions)) this.merge(disk);
    return this.claims;
  }

  /**
   * Chat `id` wants to change `abs`. Returns null when it may (and records the claim and the touch
   * in its sub-index), or the owner { id, title, model, path, since } when another running chat
   * holds the file.
   */
  claim(id, abs, kind = "edit") {
    this.load();
    const k = fileKey(abs);
    let owner = null;
    // Check and take the claim under the lock, so two windows cannot both win the same file.
    this.commit(() => {
      const c = this.claims[k];
      if (c && c.id !== id && this.claimLive(c)) {
        const o = (this.index || []).find((x) => x.id === c.id) || {};
        owner = { id: c.id, title: o.title || c.title || "another chat", model: o.model || c.model || "", path: c.path, since: c.since };
        return false;
      }
      const me = this.meta(id) || {};
      const fresh = !c || c.id !== id;
      this.claims[k] = { id, path: path.resolve(String(abs)), pid: this.pid, since: fresh ? Date.now() : c.since, title: me.title || "", model: me.model || "" };
      return fresh ? undefined : false;
    });
    if (owner) return owner;
    this.touchFile(id, abs, kind);
    return null;
  }

  /** Files chat `id` holds right now. */
  claimsOf(id) {
    this.load();
    return Object.values(this.claims).filter((c) => c.id === id).map((c) => c.path);
  }

  /** Drop every claim of chat `id` (its turn ended). Returns the released paths. */
  release(id) {
    this.load();
    const out = [];
    this.commit(() => {
      for (const [k, c] of Object.entries(this.claims)) {
        if (c.id === id && c.pid === this.pid) {
          out.push(c.path);
          delete this.claims[k];
        }
      }
      return out.length ? undefined : false;
    });
    return out;
  }
}

/** Index fields the sidebar tree shows for one chat. */
function treeItem(e) {
  let status = e.status || "idle";
  if (status === "running" && (!e.pid || !pidAlive(e.pid))) status = "stopped"; // its window is gone
  return {
    id: e.id,
    title: e.title || "New chat",
    created: e.created || 0,
    updated: e.updated || 0,
    provider: e.provider || "",
    model: e.model || "",
    status,
    unread: !!e.unread,
    pinned: !!e.pinned,
    group: e.group || "",
    turns: e.turns || 0,
  };
}

/**
 * Every workspace folder with chats, for the sidebar tree (like Cursor's per-repository agent list).
 * Read-only: each folder's main index is read without a lock and nothing is written, so it is safe
 * while other windows work in those folders. `current` folders are always listed (empty ones show
 * "No agents yet") and come first; the rest are sorted by their newest chat.
 * @returns {{ slug, workspace, name, current, exists, updated, running, chats: object[] }[]}
 */
function listWorkspaces({ root, current = [], max = 60 } = {}) {
  root = root || defaultRoot();
  const master = readMaster(root);
  const fromMaster = new Map((master.workspaces || []).map((w) => [w.slug, w]));
  const cur = (Array.isArray(current) ? current : [current]).filter(Boolean);
  const curSlugs = new Map(cur.map((w, i) => [slug(w), i]));
  const out = new Map();
  let names = [];
  try {
    names = fs.readdirSync(path.join(root, "projects"), { withFileTypes: true }).filter((d) => d.isDirectory()).map((d) => d.name);
  } catch {
    /* no chats anywhere yet */
  }
  for (const n of names) {
    const main = readJson(path.join(root, "projects", n, "index.json"));
    if (!main || !Array.isArray(main.sessions)) continue;
    const removed = main.removed && typeof main.removed === "object" ? main.removed : {};
    const chats = main.sessions.filter((e) => e && e.id && !removed[e.id]).map(treeItem);
    if (!chats.length && !curSlugs.has(n)) continue;
    chats.sort((a, b) => (b.updated || 0) - (a.updated || 0));
    const ws = main.workspace || (fromMaster.get(n) || {}).workspace || "";
    out.set(n, {
      slug: n,
      workspace: ws,
      name: ws ? path.basename(ws) || ws : n,
      current: curSlugs.has(n),
      exists: ws ? fs.existsSync(ws) : false,
      updated: Math.max(0, ...chats.map((c) => c.updated || 0)),
      running: chats.filter((c) => c.status === "running").length,
      chats,
    });
  }
  for (const w of cur) {
    const n = slug(w);
    if (!out.has(n)) out.set(n, { slug: n, workspace: w, name: path.basename(w) || w, current: true, exists: true, updated: 0, running: 0, chats: [] });
  }
  return [...out.values()]
    .sort((a, b) => (a.current === b.current ? 0 : a.current ? -1 : 1) || (a.current ? curSlugs.get(a.slug) - curSlugs.get(b.slug) : (b.updated || 0) - (a.updated || 0)))
    .slice(0, Math.max(cur.length, max));
}

/** One chat of any workspace folder, read-only (session.json merged with its index entry), or null. */
function readForeignChat(root, folderSlug, id) {
  root = root || defaultRoot();
  const dir = path.join(root, "projects", safeId(folderSlug));
  const main = readJson(path.join(dir, "index.json"));
  const meta = main && Array.isArray(main.sessions) ? main.sessions.find((e) => e && e.id === id) : null;
  const s = readJson(path.join(dir, "sessions", safeId(id), "session.json")) || readJson(path.join(dir, "sessions", safeId(id) + ".json"));
  if (!s) return null;
  return { log: [], history: [], todos: [], ...s, ...(meta || {}), workspace: (main && main.workspace) || "" };
}

/** Claude Code sessions for a workspace: ~/.claude/projects/<slug>/<sessionId>.jsonl, newest first. */
function listClaudeCodeSessions(workspace, { home, max = 40 } = {}) {
  const base = path.join(home || process.env.USERPROFILE || os.homedir(), ".claude", "projects");
  const dirs = [];
  if (workspace) dirs.push(path.join(base, slug(workspace)));
  else {
    try {
      for (const d of fs.readdirSync(base)) dirs.push(path.join(base, d));
    } catch {
      return [];
    }
  }
  const out = [];
  for (const dir of dirs) {
    let names = [];
    try {
      names = fs.readdirSync(dir);
    } catch {
      continue;
    }
    for (const n of names) {
      if (!n.endsWith(".jsonl")) continue;
      const file = path.join(dir, n);
      try {
        out.push({ file, sessionId: n.slice(0, -6), project: path.basename(dir), mtime: fs.statSync(file).mtimeMs });
      } catch {
        /* vanished */
      }
    }
  }
  return out.sort((a, b) => b.mtime - a.mtime).slice(0, max);
}

module.exports = { SessionStore, slug, titleFrom, defaultRoot, readMaster, listWorkspaces, readForeignChat, fileKey, listClaudeCodeSessions, META, pidAlive };
