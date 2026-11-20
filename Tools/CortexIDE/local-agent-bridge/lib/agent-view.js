"use strict";

const vscode = require("vscode");
const fs = require("fs");
const path = require("path");
const os = require("os");
const { spawnSync } = require("child_process");
const llm = require("./llm");
const { runAgent } = require("./agent");
const { ToolContext, defaultRgPath, promptImages, execTool } = require("./agent-tools");
const { Progress } = require("./agent-context");
const { projectChecks, repoMap } = require("./agent-env");
const { parseChatFile } = require("./import-chat");
const claudeCode = require("./claude-code");
const { SessionStore, titleFrom, listClaudeCodeSessions, listWorkspaces, readForeignChat } = require("./sessions");
const sessionLimits = require("./session-limits");
const memoryLib = require("./memory");
const mcpClient = require("./mcp-client");
const compress = require("./compress");
const fileRef = require("./file-ref");
const steer = require("./steer");
const composer = require("./composer");
const { scanCanvases, cursorProjectSlug } = require("./scan");
const agentsLib = require("./agents");
const commandsLib = require("./commands");
const instructions = require("./instructions");

/** Opened with vscode.open (image preview, PDF, or the binary prompt) instead of as a text document. */
const NON_TEXT = /\.(png|jpe?g|gif|webp|bmp|ico|tiff?|tga|dds|psd|pdf|zip|7z|rar|gz|tar|exe|dll|so|dylib|bin|dat|pak|mpq|bsa|ba2|esp|esm|esl|wasm|class|jar|mp3|wav|ogg|flac|mp4|webm|mkv|ttf|otf|woff2?)$/i;

/** Pre-2.7 single conversation; moved into the history cache on first use. */
const STATE_KEY = "localAgentBridge.agent.conversation";
const ACTIVE_KEY = "localAgentBridge.agent.activeSession";
/** Chats of other workspace folders attached to this window (they run in their own folder). */
const ATTACHED_KEY = "localAgentBridge.agent.attachedChats";
const SECRET_KEY = "localAgentBridge.anthropicApiKey";
const MAX_LOG = 400;
const MAX_HISTORY_TURNS = 12;
const MAX_CHECKPOINTS = 10;
const BEFORE_SCHEME = "local-agent-before";
/** Permission patterns saved with "Allow always" (this workspace). */
const APPROVALS_KEY = "localAgentBridge.agent.approvals";

function cfg() {
  return vscode.workspace.getConfiguration("localAgentBridge.agent");
}

/** A chat as a read-only Markdown transcript (prompts, answers, tool lines, notes). */
function transcript(s, where) {
  const out = ["# " + (s.title || "New chat"), "", "_" + [where, s.model || s.provider || "", s.updated ? new Date(s.updated).toLocaleString() : ""].filter(Boolean).join(" · ") + "_", ""];
  for (const r of s.log || []) {
    if (!r) continue;
    if (r.cls === "user") out.push("## You", "", String(r.text || ""), "");
    else if (r.cls === "assistant") out.push("## Agent", "", String(r.text || ""), "");
    else if (r.cls === "tool") out.push("- `" + (r.name || "tool") + "` " + String(r.label || "").replace(/\s+/g, " ").slice(0, 160) + (r.ok === false ? " (failed)" : ""));
    else if (r.cls === "changes") out.push("", "**Changed:** " + (r.files || []).map((f) => "`" + (f.path || f) + "`").join(", "), "");
    else if (r.cls === "err") out.push("", "> Error: " + String(r.text || "").split("\n")[0], "");
  }
  return out.join("\n") + "\n";
}

function folders() {
  return (vscode.workspace.workspaceFolders || []).map((f) => f.uri.fsPath);
}

function sameDir(a, b) {
  if (!a || !b) return !a && !b;
  return path.resolve(a).toLowerCase().replace(/[\\/]+$/, "") === path.resolve(b).toLowerCase().replace(/[\\/]+$/, "");
}

/** The model's own output cap as discovered (Claude's max_tokens), 0 = unknown. */
function modelMaxOut(backend, model) {
  const m = backend && Array.isArray(backend.models) ? backend.models.find((x) => x && x.id === model) : null;
  return (m && Number(m.maxOut)) || 0;
}

function beforeUri(turn, file) {
  return vscode.Uri.from({
    scheme: BEFORE_SCHEME,
    path: "/" + path.basename(file),
    query: new URLSearchParams({ turn, path: file }).toString(),
  });
}

function readRules(root) {
  if (!root) return "";
  const out = [];
  for (const name of ["AGENTS.md", ".cursorrules", "CLAUDE.md"]) {
    const p = path.join(root, name);
    try {
      if (fs.existsSync(p)) out.push(name + ":\n" + fs.readFileSync(p, "utf8").slice(0, 2000));
    } catch {
      /* optional */
    }
  }
  const dir = path.join(root, ".cursor", "rules");
  try {
    for (const n of fs.readdirSync(dir)) {
      if (!/\.mdc?$/i.test(n)) continue;
      const text = fs.readFileSync(path.join(dir, n), "utf8");
      if (/alwaysApply:\s*true/i.test(text)) out.push(n + ":\n" + text.replace(/^---[\s\S]*?---\s*/, "").slice(0, 1500));
    }
  } catch {
    /* no cursor rules */
  }
  return out.join("\n\n");
}

/** Handoffs from one window's sidebar tree to the window it opens ("start a chat in that folder"). */
const HANDOFF_FILE = "handoff.json";
const HANDOFF_TTL_MS = 3 * 60 * 1000;

function writeHandoff(root, h) {
  const file = path.join(root, HANDOFF_FILE);
  let list = [];
  try {
    list = JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    list = [];
  }
  const now = Date.now();
  list = (Array.isArray(list) ? list : []).filter((x) => x && now - (x.at || 0) < HANDOFF_TTL_MS && String(x.workspace).toLowerCase() !== String(h.workspace).toLowerCase());
  list.push({ ...h, at: now });
  fs.mkdirSync(root, { recursive: true });
  fs.writeFileSync(file, JSON.stringify(list));
}

/** The fresh handoff for one of these folders, removed from the file; null when there is none. */
function takeHandoffFor(root, roots) {
  const file = path.join(root, HANDOFF_FILE);
  if (!fs.existsSync(file)) return null;
  let list = [];
  try {
    list = JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    list = [];
  }
  const now = Date.now();
  const mine = new Set((roots || []).map((r) => path.resolve(r).toLowerCase()));
  const live = (Array.isArray(list) ? list : []).filter((x) => x && now - (x.at || 0) < HANDOFF_TTL_MS);
  const hit = live.find((x) => mine.has(path.resolve(String(x.workspace || "")).toLowerCase())) || null;
  const rest = live.filter((x) => x !== hit);
  if (rest.length) fs.writeFileSync(file, JSON.stringify(rest));
  else fs.rmSync(file, { force: true });
  return hit;
}

/** "branch main…origin/main; 3 changed: M src/a.cs, ?? b.txt" — or "" outside a git repo. */
function gitSummary(root) {
  if (!root) return "";
  try {
    const r = spawnSync("git", ["status", "--porcelain=v1", "-b", "--untracked-files=normal"], { cwd: root, timeout: 3000, windowsHide: true, encoding: "utf8" });
    if (r.status !== 0 || !r.stdout) return "";
    const lines = r.stdout.split(/\r?\n/).filter(Boolean);
    const head = (lines[0] || "").replace(/^##\s*/, "");
    const changed = lines.slice(1);
    if (!changed.length) return "branch " + head + "; working tree clean";
    return "branch " + head + "; " + changed.length + " changed: " + changed.slice(0, 25).map((l) => l.trim()).join(", ") + (changed.length > 25 ? ", …" : "");
  } catch {
    return "";
  }
}

function editorEnv(forRoots) {
  const roots = forRoots && forRoots.length ? forRoots : folders();
  // The editor's state belongs to this window's folder; a chat working in another folder does not get it.
  const ed = sameDir(roots[0] || "", folders()[0] || "") ? vscode.window.activeTextEditor : null;
  // AGENTS.md / CLAUDE.md / .cursorrules of every folder and its parents up to the repo root, a global
  // ~/.cortexide/AGENTS.md, Cursor alwaysApply rules and localAgentBridge.agent.instructions.
  let ins = { text: "", files: [] };
  try {
    ins = instructions.collect({ roots, extra: cfg().get("instructions", []) });
  } catch {
    ins = { text: readRules(roots[0]), files: [] };
  }
  return {
    instructionFiles: ins.files,
    roots,
    activeFile: ed ? ed.document.uri.fsPath : "",
    activeLine: ed ? ed.selection.active.line + 1 : 0,
    openFiles: vscode.window.visibleTextEditors.map((e) => e.document.uri.fsPath),
    selection: ed && !ed.selection.isEmpty ? ed.document.getText(ed.selection) : "",
    rules: ins.text,
    git: gitSummary(roots[0]),
    checks: projectChecks(roots[0]),
    tree: repoMap(roots[0]),
    canvasDir: roots[0] ? require("./canvas-link").projectCanvasDir(roots[0]) : "",
  };
}

/** Rough +added / −removed line counts between two texts (multiset of lines; fine for a summary). */
function lineDelta(before, after) {
  const count = (t) => {
    const m = new Map();
    for (const l of String(t || "").split(/\r?\n/)) m.set(l, (m.get(l) || 0) + 1);
    return m;
  };
  const a = count(before);
  const b = count(after);
  let add = 0;
  let del = 0;
  for (const [l, n] of b) add += Math.max(0, n - (a.get(l) || 0));
  for (const [l, n] of a) del += Math.max(0, n - (b.get(l) || 0));
  if (before == null) del = 0;
  if (after == null) add = 0;
  return { add, del };
}

/** The tool result an agent gets when a chat running beside it holds the file it wants to change. */
function heldMessage(abs, o) {
  const mins = o.since ? Math.max(0, Math.round((Date.now() - o.since) / 60000)) : 0;
  return (
    abs + " is being changed by another chat that is still running: “" + o.title + "”" + (o.model ? " (" + o.model + ")" : "") +
    ", since " + (mins ? mins + " min ago" : "just now") + ". Do not change this file in this turn. " +
    "Work on other files, or finish and tell the user what you would change here once that chat is done."
  );
}

function readNow(file) {
  try {
    return fs.existsSync(file) ? fs.readFileSync(file, "utf8") : null;
  } catch {
    return null;
  }
}

function listCursorTranscripts() {
  const root = path.join(process.env.USERPROFILE || os.homedir(), ".cursor", "projects");
  const found = [];
  let projects = [];
  try {
    projects = fs.readdirSync(root);
  } catch {
    return [];
  }
  for (const proj of projects) {
    const dir = path.join(root, proj, "agent-transcripts");
    let ids = [];
    try {
      ids = fs.readdirSync(dir);
    } catch {
      continue;
    }
    for (const id of ids) {
      const file = path.join(dir, id, id + ".jsonl");
      try {
        found.push({ file, project: proj, mtime: fs.statSync(file).mtimeMs });
      } catch {
        /* flat layout or missing */
      }
    }
  }
  return found.sort((a, b) => b.mtime - a.mtime).slice(0, 40);
}

function firstUserLine(file) {
  try {
    const raw = fs.readFileSync(file, "utf8");
    const m = raw.match(/<user_query>\\n?([^<]{1,200})/) || raw.match(/<user_query>\s*([^<]{1,200})/);
    return m ? m[1].replace(/\\n/g, " ").trim().slice(0, 90) : "";
  } catch {
    return "";
  }
}

/** First real request in a Claude Code session file (reads only the start of large files). */
function firstClaudeLine(file) {
  try {
    const fd = fs.openSync(file, "r");
    const buf = Buffer.alloc(256 * 1024);
    const n = fs.readSync(fd, buf, 0, buf.length, 0);
    fs.closeSync(fd);
    let raw = buf.toString("utf8", 0, n);
    if (n === buf.length) raw = raw.slice(0, raw.lastIndexOf("\n") + 1);
    for (const t of parseChatFile(file, raw)) {
      if (t.role !== "user") continue;
      const line = cleanTurnText(t.text).replace(/\s+/g, " ").trim();
      if (line && !/^\[tool |^<|^Caveat:/.test(line)) return line.slice(0, 90);
    }
  } catch {
    /* unreadable */
  }
  return "";
}

function cleanTurnText(text) {
  return String(text || "")
    .replace(/<(timestamp|available_subagent_types|system_reminder|system-reminder|external_links|local-command-stdout|command-message)>[\s\S]*?<\/\1>/g, "")
    .replace(/<\/?user_query>/g, "")
    .replace(/<uploaded_documents>[\s\S]*?<\/uploaded_documents>/g, "[uploaded documents]")
    .trim();
}

class AgentViewProvider {
  constructor(context, getState) {
    this.context = context;
    this.getState = getState;
    this.views = new Set();
    /** Chats that are working now: session id → { controller, s }. Several run side by side. */
    this.runs = new Map();
    /** Messages sent to a chat while it works (steer / queue / now): session id → SteerQueue. */
    this.queues = new Map();
    /** Discovered backends shared by chats on the same server: "provider|baseUrl" → backend. */
    this.backends = new Map();
    this.ctxCache = new Map();
    /** Claude Code: what each file looked like when read, per chat. */
    this.ccSeen = new Map();
    /** The chat on screen, and its resolved backend/model (for the header). */
    this.activeId = "";
    this.backend = null;
    this.model = "";
    this.ctxTokens = 0;
    /** Per-turn file snapshots, newest last: { id, sid, files: [{ path, before, after }] }. Memory only. */
    this.checkpoints = [];
    /** MCP servers shared by every chat; rebuilt when their settings or the workspace folders change. */
    this.mcpHub = null;
    this.mcpKey = "";
  }

  /** The MCP hub for the current settings (null when no server is configured or found). */
  mcp() {
    const a = cfg();
    const roots = folders();
    const o = {
      configured: a.get("mcpServers", {}) || {},
      imports: a.get("mcpImport", []) || [],
      autoRea: a.get("mcpAutoRea", true),
      node: a.get("mcpNodePath", "") || "node",
      thirdParty: mcpClient.thirdPartyDirs(a.get("thirdPartyDir", ""), roots),
    };
    const key = JSON.stringify([o, roots, a.get("mcpTimeoutSec", 300)]);
    if (key === this.mcpKey) return this.mcpHub;
    if (this.mcpHub) this.mcpHub.close();
    const { specs, skipped } = mcpClient.resolveServers(o);
    this.mcpKey = key;
    this.mcpHub = Object.keys(specs).length ? new mcpClient.McpHub(specs, { roots, skipped, timeoutMs: a.get("mcpTimeoutSec", 300) * 1000 }) : null;
    return this.mcpHub;
  }

  dispose() {
    if (this.mcpHub) this.mcpHub.close();
    this.mcpHub = null;
    this.mcpKey = "";
  }

  /** True while any chat runs (older callers and tests). */
  get running() {
    return this.runs.size ? [...this.runs.values()][0].controller : null;
  }

  static register(context, getState) {
    const provider = new AgentViewProvider(context, getState);
    context.subscriptions.push(provider);
    context.subscriptions.push(
      vscode.window.registerWebviewViewProvider("localAgentBridge.agent", provider, {
        webviewOptions: { retainContextWhenHidden: true },
      })
    );
    if (vscode.workspace.registerTextDocumentContentProvider) {
      // Read-only "before the agent's turn" side of the diff view.
      context.subscriptions.push(
        vscode.workspace.registerTextDocumentContentProvider(BEFORE_SCHEME, {
          provideTextDocumentContent: (uri) => {
            const q = new URLSearchParams(uri.query);
            const cp = provider.checkpoints.find((x) => x.id === q.get("turn"));
            const f = cp && cp.files.find((x) => x.path === q.get("path"));
            return f && f.before != null ? f.before : "";
          },
        })
      );
    }
    return provider;
  }

  /** The history cache for the open workspace (re-created when the folder or the setting changes). */
  store() {
    const ws = folders()[0] || "";
    const root = cfg().get("historyDir", "") || "";
    if (!this.sessions || this.sessions.workspace !== ws || this.sessionsRoot !== root) {
      this.sessions = new SessionStore({ root: root || undefined, workspace: ws, limit: cfg().get("historyLimit", 200) });
      this.sessionsRoot = root;
      this.migrate(this.sessions);
      this.watchIndex(this.sessions);
    }
    return this.sessions;
  }

  /**
   * The history store of any workspace folder (same history root). This window's own folder is
   * store(); other folders' stores serve chats attached to this window, which run in their folder.
   */
  storeOf(ws) {
    const w = String(ws || "");
    const mine = this.store();
    if (!w || sameDir(w, mine.workspace)) return mine;
    this.otherStores = this.otherStores || new Map();
    const key = path.resolve(w).toLowerCase() + "|" + (this.sessionsRoot || "");
    if (!this.otherStores.has(key)) this.otherStores.set(key, new SessionStore({ root: this.sessionsRoot || undefined, workspace: w, limit: cfg().get("historyLimit", 200) }));
    return this.otherStores.get(key);
  }

  /** The store a chat belongs to (its own workspace folder). */
  storeFor(s) {
    return s && s.workspace ? this.storeOf(s.workspace) : this.store();
  }

  /** The folders a chat works in: its own folder when it belongs to another one, else this window's. */
  rootsFor(s) {
    const mine = folders();
    if (!s || !s.workspace || mine.some((f) => sameDir(f, s.workspace))) return mine;
    return [s.workspace];
  }

  /** Chats of other folders shown and run in this window: id → folder (kept per window). */
  attached() {
    if (!this.attachedMap) {
      const saved = (this.context && this.context.workspaceState.get(ATTACHED_KEY)) || [];
      this.attachedMap = new Map((Array.isArray(saved) ? saved : []).filter((x) => x && x.id && x.workspace).map((x) => [x.id, x.workspace]));
    }
    return this.attachedMap;
  }

  setAttached(id, ws) {
    const m = this.attached();
    if (ws) m.set(id, ws);
    else m.delete(id);
    Promise.resolve(this.context.workspaceState.update(ATTACHED_KEY, [...m].map(([i, w]) => ({ id: i, workspace: w })))).catch(() => {});
  }

  /**
   * Another CortexIDE window on this workspace writes the same main index: when it changes on disk,
   * merge it in and redraw the tabs and history (new chats, renames, deletions, its running chats).
   */
  watchIndex(st) {
    if (this.unwatchIndex) this.unwatchIndex();
    const file = st.mainFile();
    const onChange = () => {
      try {
        if (this.sessions === st && st.sync()) this.postSessions();
      } catch {
        /* half-written; the next change catches up */
      }
    };
    try {
      fs.watchFile(file, { interval: 1500, persistent: false }, onChange);
    } catch {
      return;
    }
    this.unwatchIndex = () => {
      fs.unwatchFile(file, onChange);
      this.unwatchIndex = null;
    };
    if (this.context && Array.isArray(this.context.subscriptions) && !this.indexWatchDisposer) {
      this.indexWatchDisposer = { dispose: () => this.unwatchIndex && this.unwatchIndex() };
      this.context.subscriptions.push(this.indexWatchDisposer);
    }
  }

  /** Before 2.7 the panel kept one chat in workspaceState: move it into the history cache once. */
  migrate(st) {
    const old = this.context.workspaceState.get(STATE_KEY);
    if (!old || !Array.isArray(old.log)) return;
    if (old.log.length) {
      const first = old.log.find((r) => r.cls === "user");
      const s = st.create({ ...old, title: first ? titleFrom(first.text) : old.importedFrom ? "Imported chat" : "New chat", open: true });
      if (!this.activeId) this.activeId = s.id;
    }
    Promise.resolve(this.context.workspaceState.update(STATE_KEY, undefined)).catch(() => {});
  }

  /** A chat by id: the live object while it runs, otherwise read from the cache. */
  session(id) {
    if (!id) return null;
    const r = this.runs.get(id);
    if (r) return r.s;
    const own = this.store().get(id);
    if (own) return own;
    const ws = this.attached().get(id);
    return ws ? this.storeOf(ws).get(id) : null;
  }

  /** The chat on screen; falls back to the most recent open chat, or a new one. */
  active() {
    const st = this.store();
    let s = this.session(this.activeId) || this.session(this.context.workspaceState.get(ACTIVE_KEY));
    if (!s) {
      const list = st.list();
      const e = list.find((x) => x.open) || list[0];
      s = e ? this.session(e.id) : null;
    }
    if (!s) s = this.createSession();
    this.activeId = s.id;
    return s;
  }

  /** Kept for older callers: the chat on screen. */
  conv() {
    return this.active();
  }

  async saveConv(s, opts) {
    if (!s || s.deleted) return; // deleted while it ran
    s.log = (s.log || []).slice(-MAX_LOG);
    // Keep a /compress summary (and its reply) ahead of the newest turns: it stands in for the rest.
    const h = s.history || [];
    const at = h.findIndex((e) => e && e.summary);
    const head = at >= 0 && h.length - at > MAX_HISTORY_TURNS * 2 ? h.slice(at, at + 2) : [];
    s.history = [...head, ...h.slice(-MAX_HISTORY_TURNS * 2)];
    this.storeFor(s).save(s, opts);
    this.postSessions();
  }

  /** A new chat on the default backend and model (the last one picked), unless init says otherwise. */
  createSession(init = {}) {
    const c = cfg();
    // A chat may be started in another folder: it lives in that folder's history and runs there.
    const ws = init.workspace && !folders().some((f) => sameDir(f, init.workspace)) ? init.workspace : "";
    const st = ws ? this.storeOf(ws) : this.store();
    if (ws) init = { ...init };
    delete init.workspace;
    const s = st.create({
      provider: c.get("provider", "auto"),
      baseUrl: c.get("baseUrl", ""),
      model: c.get("model", ""),
      limits: sessionLimits.normalize({ preset: c.get("defaultSessionLimits", "standard") }),
      ...init,
    });
    if (ws) this.setAttached(s.id, ws);
    return s;
  }

  /** Show a chat in the panel. Other chats keep running in the background. */
  async setActive(id) {
    const s = this.session(id);
    if (!s) return null;
    this.activeId = s.id;
    await this.context.workspaceState.update(ACTIVE_KEY, s.id);
    if (s.unread || s.open === false) {
      s.unread = false;
      s.open = true;
      this.storeFor(s).update(s.id, { unread: false, open: true });
    }
    const elsewhere = s.workspace && !folders().some((f) => sameDir(f, s.workspace)) ? s.workspace : "";
    this.post({ type: "restore", sid: s.id, title: s.title, log: s.log || [], todos: s.todos || [], busy: this.runs.has(s.id), pending: this.queues.has(s.id) ? this.queues.get(s.id).list() : [], workspace: elsewhere });
    this.postSessions();
    await this.refreshBackend(false);
    this.postInfo();
    return s;
  }

  /** The chat list for the history drawer and the tab strip. */
  postSessions() {
    const own = this.store().list();
    const extra = [];
    for (const [id, ws] of this.attached()) {
      try {
        const e = this.storeOf(ws).meta(id);
        if (e) extra.push({ ...e, workspace: ws });
        else this.setAttached(id, "");
      } catch {
        /* folder gone */
      }
    }
    const items = [...own, ...extra]
      .map((e) => ({
        folder: e.workspace ? path.basename(e.workspace) || e.workspace : "",
        workspace: e.workspace || "",
        id: e.id,
        title: e.title || "New chat",
        created: e.created || 0,
        updated: e.updated || 0,
        provider: e.provider || "",
        model: e.model || "",
        status: this.runs.has(e.id) ? "running" : e.status || "idle",
        unread: !!e.unread,
        pinned: !!e.pinned,
        open: e.open !== false,
        group: e.group || "",
        turns: e.turns || 0,
      }));
    this.post({ type: "sessions", active: this.activeId, items, running: this.runs.size });
  }

  async renameSession(id) {
    const s = this.session(id || this.activeId);
    if (!s) return;
    const t = await vscode.window.showInputBox({ prompt: "Chat title", value: s.title || "", ignoreFocusOut: true });
    if (t === undefined || !t.trim()) return;
    s.title = t.trim().slice(0, 120);
    this.storeFor(s).update(s.id, { title: s.title });
    this.postSessions();
  }

  togglePin(id) {
    const s = this.session(id);
    if (!s) return;
    s.pinned = !s.pinned;
    this.storeFor(s).update(s.id, { pinned: s.pinned });
    this.postSessions();
  }

  /** Take a chat off the tab strip. It stays in history, and keeps running if it is. */
  async closeSession(id) {
    const s = this.session(id);
    if (!s) return;
    s.open = false;
    this.storeFor(s).update(s.id, { open: false });
    // An attached chat of another folder leaves this window when its tab closes (it stays in its folder's history).
    if (this.attached().has(s.id) && !this.runs.has(s.id)) this.setAttached(s.id, "");
    if (s.id === this.activeId) await this.switchAway(s.id);
    else this.postSessions();
  }

  async switchAway(id) {
    const next = this.store()
      .list()
      .find((e) => e.open !== false && e.id !== id);
    await this.setActive(next ? next.id : this.createSession().id);
  }

  async deleteSession(id) {
    const s = this.session(id);
    if (!s) return;
    const running = this.runs.get(s.id);
    const pick = await vscode.window.showWarningMessage(
      "Delete the chat “" + (s.title || "New chat") + "” from history?" + (running ? " It is still running and will be stopped." : ""),
      { modal: true },
      "Delete"
    );
    if (pick !== "Delete") return;
    if (running) {
      s.deleted = true;
      running.controller.abort();
    }
    if (!this.storeFor(s).remove(s.id)) {
      if (this.storeFor(s).runningElsewhere(s.id)) vscode.window.showWarningMessage("That chat is running in another CortexIDE window; stop it there first.");
      this.postSessions();
      return;
    }
    this.ccSeen.delete(s.id);
    this.setAttached(s.id, "");
    if (s.id === this.activeId) await this.switchAway(s.id);
    else this.postSessions();
  }

  /**
   * The sidebar tree: every workspace folder that has chats (from the master index), this window's
   * folders first. The panel draws this window's folder from the live `sessions` list and the
   * others from here. Read-only: other folders' indexes are only read.
   */
  postTree() {
    const st = this.store();
    let items = [];
    try {
      items = listWorkspaces({ root: st.root, current: folders() });
    } catch {
      /* unreadable history folder: the drawer shows this folder only */
    }
    for (const w of items) w.here = w.slug === st.slug;
    this.post({ type: "tree", items });
  }

  /** A chat of another workspace folder was clicked in the tree: open its folder, copy it here, or read it. */
  async openForeign(folderSlug, id) {
    const st = this.store();
    const s = readForeignChat(st.root, folderSlug, id);
    if (!s) {
      vscode.window.showWarningMessage("That chat is no longer in its folder's history.");
      this.postTree();
      return;
    }
    const ws = s.workspace || "";
    const name = ws ? path.basename(ws) || ws : folderSlug;
    const items = [];
    if (ws && fs.existsSync(ws)) {
      items.push({ label: "$(comment-discussion) Open it here", description: "it keeps working in “" + name + "”: its tools, git, checks and project memory are that folder's", act: "attach" });
      items.push({ label: "$(empty-window) Open “" + name + "” in a new window", description: "the chat is in that window's Agent history", act: "window" });
      items.push({ label: "$(folder-opened) Switch this window to “" + name + "”", act: "here" });
    }
    items.push({ label: "$(copy) Continue it in this workspace", description: "copies the chat (log, history, plan) into a new chat here", act: "copy" });
    items.push({ label: "$(markdown) Read it", description: "read-only Markdown transcript", act: "read" });
    const pick = await vscode.window.showQuickPick(items, { title: "“" + (s.title || "New chat") + "” · " + name, placeHolder: ws || folderSlug });
    if (!pick) return;
    if (pick.act === "attach") {
      await this.attachChat(id, ws);
    } else if (pick.act === "window" || pick.act === "here") {
      await vscode.commands.executeCommand("vscode.openFolder", vscode.Uri.file(ws), { forceNewWindow: pick.act === "window" });
    } else if (pick.act === "copy") {
      const c = this.createSession({
        title: s.title || "New chat",
        provider: s.provider || cfg().get("provider", "auto"),
        baseUrl: s.baseUrl || "",
        model: s.model || "",
        ...(s.limits ? { limits: s.limits } : {}),
        log: [...(s.log || []), { cls: "sys", text: "Copied from the workspace “" + name + "” (" + (ws || folderSlug) + "). File paths in it may point at that folder." }],
        history: s.history || [],
        todos: s.todos || [],
        importedFrom: ws || folderSlug,
      });
      await this.setActive(c.id);
    } else {
      const doc = await vscode.workspace.openTextDocument({ language: "markdown", content: transcript(s, ws || folderSlug) });
      await vscode.window.showTextDocument(doc, { preview: true });
    }
  }

  /** Show a chat of another folder in this window; it keeps working in its own folder. */
  async attachChat(id, ws) {
    if (!ws || !fs.existsSync(ws)) {
      vscode.window.showWarningMessage("The folder no longer exists: " + ws);
      return;
    }
    const st = this.storeOf(ws);
    if (st.runningElsewhere(id)) {
      vscode.window.showWarningMessage("That chat is running in another CortexIDE window; it can be opened here when it stops.");
      return;
    }
    if (!folders().some((f) => sameDir(f, ws))) this.setAttached(id, ws);
    st.update(id, { open: true });
    await this.setActive(id);
    await this.focus();
  }

  /** Agent: New Chat in Folder… — a chat that works in any folder, without opening it in a window. */
  async newChatInFolder(folder) {
    let ws = typeof folder === "string" ? folder : folder && folder.fsPath ? folder.fsPath : "";
    if (!ws) {
      const known = [];
      try {
        for (const w of listWorkspaces({ root: this.store().root, current: folders() })) if (w.workspace && w.exists !== false) known.push(w.workspace);
      } catch {
        /* no master index yet */
      }
      const items = [...new Set([...folders(), ...known])].map((w) => ({ label: path.basename(w) || w, description: w, ws: w }));
      items.push({ label: "$(folder) Choose a folder…", ws: "" });
      const pick = await vscode.window.showQuickPick(items, { placeHolder: "Folder the new chat works in (it opens in this window)" });
      if (!pick) return;
      ws = pick.ws;
      if (!ws) {
        const got = await vscode.window.showOpenDialog({ canSelectFolders: true, canSelectFiles: false, openLabel: "Chat in this folder" });
        if (!got || !got.length) return;
        ws = got[0].fsPath;
      }
    }
    const c = this.createSession({ workspace: ws });
    await this.setActive(c.id);
    await this.focus();
    return c;
  }

  /**
   * Start a new chat in a folder of the sidebar tree. This window's folder: a new chat here. Another
   * folder: it is opened (new window or this one) with a handoff note, so that window starts a new chat.
   */
  async startChatIn(folder, here) {
    const ws = String(folder || "");
    const mine = folders().some((f) => path.resolve(f).toLowerCase() === path.resolve(ws || ".").toLowerCase());
    if (here || !ws || mine) {
      await this.newChat();
      await this.focus();
      return;
    }
    if (!fs.existsSync(ws)) {
      vscode.window.showWarningMessage("The folder no longer exists: " + ws);
      return;
    }
    const name = path.basename(ws) || ws;
    const pick = await vscode.window.showQuickPick(
      [
        { label: "$(comment-discussion) Here, working in “" + name + "”", description: "no window change: the chat's tools, git, checks and memory use that folder", act: "attach" },
        { label: "$(empty-window) New window", description: "open “" + name + "” beside this one and start a chat there", act: "window" },
        { label: "$(folder-opened) Switch this window", description: "switch this window to “" + name + "”", act: "here" },
      ],
      { title: "Start a chat in “" + name + "”", placeHolder: ws }
    );
    if (!pick) return;
    if (pick.act === "attach") {
      const c = this.createSession({ workspace: ws });
      await this.setActive(c.id);
      await this.focus();
      return;
    }
    writeHandoff(this.store().root, { workspace: ws, action: "newChat" });
    await vscode.commands.executeCommand("vscode.openFolder", vscode.Uri.file(ws), { forceNewWindow: pick.act === "window" });
  }

  /**
   * One !`command` block of a custom command, run in the first folder (the command file is trusted, as
   * in opencode; localAgentBridge.agent.shell = off still turns them off). Returns its output.
   */
  async commandShell(command, roots) {
    const a = cfg();
    if (a.get("shell", "auto") === "off") return "(not run: localAgentBridge.agent.shell = off)";
    const ctx = new ToolContext({ roots: roots && roots.length ? roots : folders(), writableRoots: a.get("writableRoots", []), shellMode: "auto", shellTimeoutSec: 60, rgPath: defaultRgPath(vscode.env.appRoot) });
    const out = await execTool(ctx, "Shell", { command });
    return String(out).replace(/^exit 0 \(cwd [^\n]*\)\n/, "").replace(/^\(no output\)$/, "");
  }

  /** On startup: a window opened from another window's tree to start a chat opens the Agent with a new chat. */
  async takeHandoff() {
    let h = null;
    try {
      h = takeHandoffFor(this.store().root, folders());
    } catch {
      h = null;
    }
    if (!h) return false;
    await this.focus();
    await this.newChat();
    return true;
  }

  /** Pin or unpin a chat of another workspace folder (written through that folder's own locked index). */
  pinForeign(folderSlug, id) {
    const st = this.store();
    const w = listWorkspaces({ root: st.root }).find((x) => x.slug === folderSlug);
    if (!w || !w.workspace) return;
    const other = new SessionStore({ root: st.root, workspace: w.workspace, limit: cfg().get("historyLimit", 200) });
    const e = other.meta(id);
    if (e) other.update(id, { pinned: !e.pinned });
    this.postTree();
  }

  /** Full-text search of the history; the panel already filters titles as you type. */
  searchSessions(q) {
    this.post({ type: "found", q: String(q || ""), ids: this.store().search(q).map((e) => e.id) });
  }

  /** Change a chat's backend and model; a running chat uses it from its next turn. */
  async setSessionModel(s, { provider, baseUrl, model }) {
    if (!s) return;
    s.provider = provider;
    s.baseUrl = baseUrl || "";
    s.model = model || "";
    this.storeFor(s).update(s.id, { provider: s.provider, baseUrl: s.baseUrl, model: s.model });
    this.postSessions();
  }

  resolveWebviewView(view) {
    this.views.add(view);
    view.onDidDispose(() => this.views.delete(view));
    view.webview.options = { enableScripts: true };
    view.webview.html = html(this.context.extensionPath);
    view.webview.onDidReceiveMessage((m) => this.onMessage(m));
    // Opening or focusing the Local Agent shows the New Tab page in the editor area instead of Welcome.
    const showHome = () => {
      if (this.home && view.visible !== false) Promise.resolve().then(() => this.home.onAgentShown()).catch(() => {});
    };
    showHome();
    if (view.onDidChangeVisibility) view.onDidChangeVisibility(showHome);
    // The panels an empty chat shows follow the open tabs and the panels setting.
    let timer = 0;
    const later = () => {
      clearTimeout(timer);
      timer = setTimeout(() => this.postPanels(), 300);
    };
    const subs = [];
    try {
      if (vscode.window.tabGroups && vscode.window.tabGroups.onDidChangeTabs) subs.push(vscode.window.tabGroups.onDidChangeTabs(later));
      if (vscode.workspace.onDidChangeConfiguration) subs.push(vscode.workspace.onDidChangeConfiguration((e) => e.affectsConfiguration("localAgentBridge.agent.panels") && later()));
    } catch {
      /* older host */
    }
    view.onDidDispose(() => {
      clearTimeout(timer);
      for (const d of subs) d.dispose();
    });
  }

  post(msg) {
    for (const v of this.views) {
      try {
        v.webview.postMessage(msg);
      } catch {
        /* disposed */
      }
    }
  }

  async onMessage(m) {
    try {
      if (m.type === "ready") {
        await this.setActive(this.active().id);
        this.postInfo(true);
        this.postPanels();
      } else if (m.type === "cmd") await this.command(m.id);
      else if (m.type === "copy") await vscode.env.clipboard.writeText(String(m.text || ""));
      else if (m.type === "send") await this.send(m.text, m.sid, m.mode);
      else if (m.type === "stop") this.stop(m.sid);
      else if (m.type === "unqueue") this.unqueue(m.sid, m.id);
      else if (m.type === "requeue") this.requeue(m.sid, m.id, m.mode);
      else if (m.type === "new") await this.newChat();
      else if (m.type === "newIn") await this.startChatIn(m.path, m.here);
      else if (m.type === "switch") await this.setActive(m.id);
      else if (m.type === "rename") await this.renameSession(m.id);
      else if (m.type === "pin") this.togglePin(m.id);
      else if (m.type === "close") await this.closeSession(m.id);
      else if (m.type === "delete") await this.deleteSession(m.id);
      else if (m.type === "search") this.searchSessions(m.q);
      else if (m.type === "tree") this.postTree();
      else if (m.type === "foreign") await this.openForeign(m.slug, m.id);
      else if (m.type === "attach") await this.attachChat(m.id, m.workspace || (readForeignChat(this.store().root, m.slug, m.id) || {}).workspace || "");
      else if (m.type === "pinForeign") this.pinForeign(m.slug, m.id);
      else if (m.type === "openFolder" && m.path) await vscode.commands.executeCommand("vscode.openFolder", vscode.Uri.file(String(m.path)), { forceNewWindow: true });
      else if (m.type === "multi") await this.runOnModels(m.text);
      else if (m.type === "model") await this.pickModel();
      else if (m.type === "import") await this.importChat();
      else if (m.type === "progress") await this.openProgress();
      else if (m.type === "undo") await this.undoTurn(m.id);
      else if (m.type === "diff") await this.showDiff(m.id, m.path);
      else if (m.type === "openCanvas") await this.showCanvas(m.file, { force: true });
      else if (m.type === "canvasSource") await vscode.commands.executeCommand("localAgentBridge.openCanvasSource", vscode.Uri.file(String(m.file || "")));
      else if (m.type === "file") await this.fileAction(m);
      else if (m.type === "attach") await this.attach(m);
      else if (m.type === "panel") await this.panelAction(m);
      else if (m.type === "panels") this.postPanels();
    } catch (e) {
      this.post({ type: "error", text: String((e && e.message) || e) });
    }
  }

  /**
   * Backend, model and context window for one chat. Each chat keeps its own provider/baseUrl/model
   * (no provider = the settings); a discovered backend is shared by every chat on that server.
   * Throws with e.header set to a one-line reason.
   */
  async resolveFor(s, force) {
    const c = cfg();
    const own = !!(s && s.provider);
    const provider = own ? s.provider : c.get("provider", "auto");
    const baseUrl = own ? s.baseUrl || "" : c.get("baseUrl", "");
    const want = own ? s.model || "" : c.get("model", "");
    const key = provider + "|" + baseUrl;
    let backend = force ? null : this.backends.get(key);
    if (provider === "claude-code") {
      if (!backend) {
        // The Claude Code engine: the installed CLI runs the whole agent, not the bridge's loop.
        const found = claudeCode.findExecutable(c.get("claudeCodePath", ""));
        const ver = found.exe ? claudeCode.version(found.exe) : "";
        if (!found.exe || !ver) {
          const e = new Error("Claude Code CLI " + (found.exe ? "did not answer (" + found.exe + ")" : "not found") + ". Install it from claude.com/claude-code or set localAgentBridge.agent.claudeCodePath.");
          e.header = e.message;
          throw e;
        }
        backend = { provider: "claude-code", label: "Claude Code " + ver, baseUrl: found.exe, exe: found.exe, version: ver, models: claudeCode.MODELS };
        this.backends.set(key, backend);
      }
      // A local model id left over from another backend means Claude Code's default model.
      return { key, backend, model: /[/:]/.test(want) ? "" : want, ctxTokens: 0 };
    }
    if (!backend) {
      try {
        backend = await llm.discover({
          provider,
          baseUrl,
          apiKey: c.get("apiKey", ""),
          anthropicApiKey: await this.secret(),
          anthropicWorkspaceId: c.get("claudeWorkspaceId", ""),
        });
      } catch (e) {
        const lines = String((e && e.message) || e).split("\n").filter(Boolean);
        const err = e instanceof Error ? e : new Error(String(e));
        err.header = lines.length > 1 && provider !== "auto" ? lines[1] : lines[0];
        throw err;
      }
      this.backends.set(key, backend);
    }
    const model = llm.pickModel(backend.models, want, backend.provider);
    const ck = key + "|" + model;
    if (force || !this.ctxCache.has(ck)) {
      this.ctxCache.set(ck, await llm.contextWindow(backend, model, { override: c.get("contextTokens", 0), ollamaNumCtx: c.get("ollamaNumCtx", 16384) }));
    }
    return { key, backend, model, ctxTokens: this.ctxCache.get(ck), maxOut: modelMaxOut(backend, model) };
  }

  /** Resolve the backend of the chat on screen and show it in the header. */
  async refreshBackend(force) {
    const s = this.active();
    let r;
    try {
      r = await this.resolveFor(s, force);
    } catch (e) {
      if (s.id !== this.activeId) return null; // switched chats meanwhile
      this.backend = null;
      this.post({ type: "header", ok: false, text: "No backend · " + (e.header || String((e && e.message) || e)) });
      return null;
    }
    if (s.id !== this.activeId) return this.backend;
    this.backend = r.backend;
    this.model = r.model;
    this.ctxTokens = r.ctxTokens;
    this.postHeader();
    return this.backend;
  }

  postHeader() {
    if (!this.backend) return;
    this.postInfo();
    if (this.backend.provider === "claude-code") {
      const auth = cfg().get("claudeCodeAuth", "auto");
      this.post({
        type: "header",
        ok: true,
        text: this.backend.label + " · " + (this.model || "default model") + " · " + cfg().get("claudeCodePermissionMode", "acceptEdits"),
        title: this.backend.exe + " · auth: " + auth + " · same engine as the Claude app; its own tools, skills, CLAUDE.md and MCP servers apply",
      });
      return;
    }
    this.post({
      type: "header",
      ok: true,
      text: this.backend.label + " · " + this.model + " · " + Math.round(this.ctxTokens / 1024) + "k ctx",
      title: this.backend.baseUrl + (this.backend.credSource ? " · credentials: " + this.backend.credSource : ""),
    });
  }

  async log(c, cls, text, extra) {
    c.log.push({ cls, text: String(text || "").slice(0, 8000), ...(extra || {}) });
  }

  /** Stop one chat's run (default: the chat on screen). */
  stop(sid) {
    const r = this.runs.get(sid || this.activeId);
    if (r) r.controller.abort();
  }

  /** The steering queue of one chat (created on first use). */
  queueOf(sid) {
    let q = this.queues.get(sid);
    if (!q) this.queues.set(sid, (q = new steer.SteerQueue()));
    return q;
  }

  /** Show a chat's waiting messages above the composer. */
  postPending(sid) {
    const q = this.queues.get(sid);
    this.post({ type: "pending", sid, items: q ? q.list() : [] });
  }

  unqueue(sid, id) {
    const q = this.queues.get(sid || this.activeId);
    const it = q && q.remove(id);
    if (it) {
      this.post({ type: "unsent", sid: sid || this.activeId, text: it.text });
      this.postPending(sid || this.activeId);
    }
  }

  /** Turn a waiting message into steer / queue / now ("now" stops the turn to send it). */
  requeue(sid, id, mode) {
    sid = sid || this.activeId;
    const q = this.queues.get(sid);
    const it = q && q.setMode(id, mode);
    if (!it) return;
    this.postPending(sid);
    if (mode === "now" && this.runs.has(sid)) this.stop(sid);
  }

  /**
   * A message for chat `s` while it works here. steer: taken into the running turn at its next
   * step; queue: the next turn; now: stop this turn and send it. Returns the queued item.
   */
  async steerRunning(s, text, mode, from = "") {
    const run = this.runs.get(s.id);
    if (!run) return null;
    const post = (m) => this.post({ ...m, sid: s.id });
    mode = steer.modeFor(text, steer.MODES.includes(mode) ? mode : cfg().get("steerDefault", "steer"));
    // /compress itself is running: nothing can be steered into it, so the message waits for it
    // ("stop & send" still stops the compression first).
    if (!run.steerable && mode === "steer") mode = "queue";
    const extra = { from };
    let body = text;
    // Images linked in a steering message go to the model with it (Claude Code opens them itself).
    if (mode === "steer" && run.tools && run.provider !== "claude-code") {
      try {
        const pi = await promptImages(run.tools, text, cfg().get("maxImages", 6));
        if (pi.images.length) {
          extra.images = pi.images;
          body = text + "\n\n[Images linked in this message]\n" + pi.notes.map((n) => "- " + n).join("\n");
        }
      } catch {
        /* sent without them */
      }
    }
    if (this.runs.get(s.id) !== run) return this.send(text, s.id); // the turn ended meanwhile: a new turn
    const it = this.queueOf(s.id).push(body, mode, extra);
    if (!it) return null;
    this.postPending(s.id);
    if (mode === "now") {
      post({ type: "status", text: "Stopping this turn to send your message…" });
      this.stop(s.id);
    } else if (it.command) post({ type: "status", text: text.split(/\s/)[0] + " queued: it runs as soon as this turn ends (Stop & send runs it now)." });
    else post({ type: "status", transient: true, text: mode === "queue" ? (run.steerable ? "Queued: runs as the next turn when this one ends" : "Queued: runs when /compress finishes") : "Steering: the agent takes your message in at its next step" });
    return it;
  }

  /** Messages other windows or outside tools left in a running chat's inbox. */
  pullInbox(s) {
    let got = [];
    try {
      got = steer.takeInbox(this.storeFor(s).chatDir(s.id));
    } catch {
      return 0;
    }
    if (!got.length) return 0;
    const q = this.queueOf(s.id);
    let stopNow = false;
    for (const m of got) {
      q.push(m.text, m.mode, { from: m.from || "outside" });
      if (m.mode === "now") stopNow = true;
    }
    this.postPending(s.id);
    this.post({ type: "status", sid: s.id, text: "Received " + (got.length > 1 ? got.length + " messages" : "a message") + " for this chat from " + (got[0].from || "outside this window") });
    if (stopNow && this.runs.has(s.id)) this.stop(s.id);
    return got.length;
  }

  /**
   * After a turn: what runs next. Steering that arrived too late and "stop & send" messages run as
   * one new turn, then queued messages one turn each. A turn stopped with Stop, or failed, runs
   * nothing by itself: the unsent messages go back into the input box. Returns the next text or "".
   */
  nextFollowUp(s, run, status = s.status) {
    this.pullInbox(s);
    const q = this.queues.get(s.id);
    if (!q || !q.size) return "";
    const post = (m) => this.post({ ...m, sid: s.id });
    const items = q.drain();
    if (s.deleted) return "";
    const now = items.filter((i) => i.mode === "now");
    const late = items.filter((i) => i.mode === "steer");
    const queued = items.filter((i) => i.mode === "queue");
    if (!(status === "done" || (status === "stopped" && now.length))) {
      post({ type: "unsent", text: items.map((i) => i.text).join("\n\n") });
      const note = items.length + " message" + (items.length > 1 ? "s" : "") + " sent while it worked " + (items.length > 1 ? "were" : "was") + " not run (the turn " + (s.status === "stopped" ? "was stopped" : "failed") + "); " + (items.length > 1 ? "they are" : "it is") + " back in the input box.";
      s.log.push({ cls: "sys", text: note });
      post({ type: "status", text: note });
      this.postPending(s.id);
      return "";
    }
    if (now.length && status === "stopped" && run && run.text) {
      // The interrupted turn is not in the history yet: the next turn should know it happened.
      const files = run.changed && run.changed.length ? " Files changed before the stop: " + run.changed.join(", ") + "." : "";
      (s.history = s.history || []).push({ role: "user", content: steer.withSteering(run.text, run.steered) }, { role: "assistant", content: "[Stopped by the user to send a new message before this turn finished." + files + "]" });
    }
    // A command (/compress) runs on its own, never joined with other text. A "stop & send" command
    // goes first; otherwise commands keep their place among the queued turns.
    const nowCmd = now.find((i) => i.command);
    let next;
    let rest;
    if (nowCmd) {
      next = nowCmd.text;
      rest = items.filter((i) => i !== nowCmd).map((i) => (i.mode === "queue" ? i : { ...i, mode: "queue" }));
    } else {
      const first = [...now, ...late].filter((i) => !i.command);
      if (first.length) next = first.map((i) => i.text).join("\n\n");
      else next = queued.shift().text;
      rest = [...now, ...late].filter((i) => i.command).map((i) => ({ ...i, mode: "queue" })).concat(queued);
    }
    for (const i of rest) q.items.push(i);
    this.postPending(s.id);
    return next;
  }

  /** Agent: Steer Running Chat — any chat running in this window, another window or workspace. */
  async steerCommand() {
    const root = cfg().get("historyDir", "") || undefined;
    const here = [...this.runs.values()].filter((r) => r.steerable).map((r) => ({ id: r.s.id, title: r.s.title || "New chat", model: r.s.model || "", workspace: folders()[0] || "", here: true }));
    let others = [];
    try {
      others = steer.listRunning({ root }).filter((c) => !this.runs.has(c.id));
    } catch {
      others = [];
    }
    const all = [...here, ...others];
    if (!all.length) {
      vscode.window.showInformationMessage("No chat is running. Send a normal message instead.");
      return null;
    }
    let c = all[0];
    if (all.length > 1) {
      const pick = await vscode.window.showQuickPick(
        all.map((x) => ({ label: x.title, description: [x.model, x.here ? "this window" : path.basename(x.workspace || "") + " · another window"].filter(Boolean).join(" · "), c: x })),
        { placeHolder: "Steer which running chat?" }
      );
      if (!pick) return null;
      c = pick.c;
    }
    const text = await vscode.window.showInputBox({ prompt: "Message for “" + c.title + "” (it keeps working)", placeHolder: "e.g. also update the README, or: skip the tests for now" });
    if (!text || !text.trim()) return null;
    const m = await vscode.window.showQuickPick(
      [
        { label: "Steer now", description: "taken into the running turn at its next step", mode: "steer" },
        { label: "Queue", description: "runs as the next turn when this one ends", mode: "queue" },
        { label: "Stop & send", description: "stops the running turn, then sends this", mode: "now" },
      ],
      { placeHolder: "How should the chat take it?" }
    );
    if (!m) return null;
    if (c.here) {
      const s = this.session(c.id);
      return s ? this.steerRunning(s, text.trim(), m.mode) : null;
    }
    const r = steer.sendExternal({ root, id: c.id, text: text.trim(), mode: m.mode, from: "another window" });
    vscode.window.showInformationMessage("Sent to “" + r.title + "”. The window running it takes it in within a second or two.");
    return r;
  }

  /**
   * One turn in one chat (default: the chat on screen). Each chat has its own run, so several
   * chats — on different models — can work at the same time. Events carry the chat id (sid);
   * the panel shows those of the chat on screen, the rest land in each chat's log.
   */
  async send(text, sid, mode, opts = {}) {
    text = String(text || "").trim();
    if (!text) return;
    const s = sid ? this.session(sid) : this.active();
    if (!s) return;
    const post = (m) => this.post({ ...m, sid: s.id });
    // /commands, /agents: list them. /name args: a custom command from a Markdown file, expanded first.
    if (/^\/(commands|help|agents)\s*$/i.test(text)) {
      const roots = this.rootsFor(s);
      const list = /agents/i.test(text)
        ? agentsLib.loadAgents(roots).filter((x) => !x.hidden).map((x) => "@" + x.name + " (" + x.mode + ") — " + (x.description || "") + (x.file ? " · " + x.file : "")).join("\n")
        : "/compress [focus] — summarise this chat\n/agents — list agents (@name at the start of a message picks one)\n" + commandsLib.listing(commandsLib.loadCommands(roots));
      post({ type: "status", text: list });
      if (!this.runs.has(s.id)) post({ type: "idle" });
      return;
    }
    let cmdAgent = "";
    const custom = !compress.parseCommand(text) ? commandsLib.match(text, commandsLib.loadCommands(this.rootsFor(s))) : null;
    if (custom) {
      post({ type: "status", transient: true, text: "Expanding /" + custom.command.name + "…" });
      const ex = await commandsLib.expand(custom.command, custom.args, (c) => this.commandShell(c, this.rootsFor(s)));
      cmdAgent = ex.agent;
      text = (cmdAgent ? "@" + cmdAgent + " " : "") + ex.prompt;
      if (!ex.prompt) return;
    }
    if (this.runs.has(s.id)) {
      // Conversation steering: the chat keeps working and takes the message in (or queues it).
      // /compress waits for the turn to end (or, with Stop & send, stops it and runs at once).
      await this.steerRunning(s, text, mode);
      post({ type: "busy" });
      return;
    }
    if (this.storeFor(s).runningElsewhere(s.id)) {
      // The window running it reads the chat's inbox and takes the message in there.
      try {
        steer.postInbox(this.storeFor(s).chatDir(s.id), { text, mode: steer.modeFor(text, steer.MODES.includes(mode) ? mode : cfg().get("steerDefault", "steer")), from: "another window" });
        post({ type: "status", text: "Sent to this chat in the other CortexIDE window that runs it: “" + text.slice(0, 120) + "”" + (steer.isCommand(text) ? " (runs there when its turn ends)" : "") + ". Its log there shows the reply." });
      } catch (e) {
        vscode.window.showWarningMessage("Could not send to the other window: " + ((e && e.message) || e));
      }
      post({ type: "idle" });
      return;
    }
    // /compress [focus] (or /compact): summarise this chat's history instead of running a turn.
    const cmd = compress.parseCommand(text);
    if (cmd) return this.compressChat(s, cmd.focus);
    // Auto-compact: when the carried-over history would fill too much of the context window, the
    // chat is compacted first and this message then runs on the summary.
    if (!opts.noAutoCompact && !this.runs.has(s.id) && (await this.autoCompactDue(s))) {
      return this.compressChat(s, "", { auto: true, then: text });
    }
    const limit = cfg().get("maxParallel", 4);
    if (limit > 0 && this.runs.size >= limit) {
      vscode.window.showWarningMessage(this.runs.size + " chats are already running (localAgentBridge.agent.maxParallel = " + limit + "). Stop one or wait for it to finish.");
      post({ type: "idle" });
      return;
    }
    // Claim the run before the first await, so a second quick send to this chat is refused.
    const controller = new AbortController();
    const run = { controller, s, steerable: true, text, steered: [], changed: [] };
    this.runs.set(s.id, run);
    // Other windows and outside tools (MCP server, steer CLI) drop messages in the chat's inbox.
    run.poll = setInterval(() => this.pullInbox(s), 1000);
    const finish = async () => {
      if (this.runs.get(s.id) === run) this.runs.delete(s.id);
      clearInterval(run.poll);
      const next = this.nextFollowUp(s, run);
      // The turn is over: other chats may change its files again.
      try {
        if (!s.deleted) this.storeFor(s).release(s.id);
      } catch {
        /* index unwritable; claims of a stopped chat are ignored anyway */
      }
      if (s.id !== this.activeId && !s.deleted) s.unread = true;
      await this.saveConv(s);
      post({ type: "idle" });
      if (next) {
        post({ type: "status", transient: true, text: "Sending your next message…" });
        setTimeout(() => this.send(next, s.id).catch((e) => post({ type: "error", text: String((e && e.message) || e) })), 0);
      }
    };
    if (!s.title || s.title === "New chat") s.title = titleFrom(text);
    s.status = "running";
    s.todos = []; // each turn plans afresh
    await this.log(s, "user", text);
    post({ type: "user", text });
    post({ type: "busy" });
    post({ type: "todos", todos: [] });
    await this.saveConv(s);
    let r = null;
    let why = "";
    try {
      r = await this.resolveFor(s, false);
    } catch (e) {
      why = e.header || String((e && e.message) || e);
      if (s.id === this.activeId) {
        this.backend = null;
        this.post({ type: "header", ok: false, text: "No backend · " + why });
      }
    }
    if (!r || controller.signal.aborted) {
      const msg = r ? "Stopped." : "No model backend reachable for this chat (" + why + "). Start vLLM (:30000 / :8000) or Ollama (:11434), pick Claude under Model (needs an Anthropic API key), or set localAgentBridge.agent.baseUrl.";
      s.log.push({ cls: r ? "sys" : "err", text: msg });
      s.status = r ? "stopped" : "error";
      post({ type: r ? "status" : "error", text: msg });
      await finish();
      return;
    }
    const { backend, model, ctxTokens, key } = r;
    const c = s;
    const a = cfg();
    // This chat's own limits (Standard = the settings; Extended / Maximum / Custom raise them).
    const lim = sessionLimits.resolve({ limits: s.limits, provider: backend.provider, get: (k, d) => a.get(k, d), modelMaxOut: r.maxOut, ctxTokens });
    if (!sessionLimits.isStandard(s.limits) || lim.notes.length) {
      const parts = [lim.maxOutputTokens + " output tokens"];
      if (backend.provider !== "claude-code") parts.push(lim.maxRounds + " rounds");
      if (lim.effort) parts.push("effort " + lim.effort);
      post({ type: "status", transient: true, text: "Limits for this chat: " + lim.label + " · " + parts.join(" · ") + (lim.notes.length ? " (" + lim.notes.join("; ") + ")" : "") });
    }
    const env = editorEnv(this.rootsFor(s));
    // The agent that runs this turn: "@name" at the start, the composer mode (Plan / Ask), else build.
    let agentList = [];
    try {
      agentList = agentsLib.loadAgents(env.roots);
    } catch {
      agentList = Object.values(agentsLib.BUILTIN);
    }
    const picked = agentsLib.forMessage(agentList, text);
    if (picked.agent && picked.agent.name !== "build") {
      const why = picked.agent.name + (picked.agent.readOnly ? " — no edits" + (picked.agent.name === "ask" ? ", no commands" : "; commands that change things ask first") : "");
      post({ type: "status", text: "Agent: " + why + (backend.provider === "claude-code" ? " (Claude Code runs its own agent; only the instructions apply)" : "") });
    } else if (picked.via) post({ type: "status", transient: true, text: "Asking the agent to use the sub-agent @" + picked.via });
    // Whether this chat's model can look at images (ReadImage / AnalyzeFile / linked images attach them).
    let vision = false;
    try {
      vision = await llm.supportsVision(backend, model, a.get("vision", "auto"));
    } catch {
      vision = false;
    }
    if (backend.provider === "ollama" && typeof llm.ollamaToolAdvice === "function") {
      // A vision or chat-only model (llava, bakllava, gemma2, …) picked as the agent drives it badly: say so up front.
      try {
        const advice = await llm.ollamaToolAdvice(backend.baseUrl, model);
        if (advice) post({ type: "status", text: advice });
      } catch {
        /* advice only */
      }
    }
    const tools = new ToolContext({
      roots: env.roots,
      owner: s.id,
      vision,
      imageMaxEdge: a.get("imageMaxEdge", 1568),
      model,
      mcp: this.mcp(),
      mcpMode: a.get("mcpMode", "auto"),
      mcpTimeoutSec: a.get("mcpTimeoutSec", 300),
      confirmMcp: async (label) => {
        const pick = await vscode.window.showWarningMessage("Agent (" + (s.title || "chat") + ") wants to run the MCP tool:\n\n" + label, { modal: true }, "Run");
        return pick === "Run";
      },
      writableRoots: a.get("writableRoots", []),
      readAnywhere: a.get("readAnywhere", true),
      shellMode: a.get("shell", "auto"),
      shellTimeoutSec: a.get("shellTimeoutSec", 120),
      rgPath: defaultRgPath(vscode.env.appRoot),
      skills: () => this.getState().skills || [],
      requireRead: a.get("requireReadBeforeEdit", true),
      diagnosticsAfterEdit: a.get("diagnosticsAfterEdit", true),
      signal: controller.signal,
      // Files edited by this chat are claimed in the folder's main index while it runs, so a
      // chat running beside it cannot overwrite them.
      claim: (abs, kind) => {
        const o = this.storeFor(s).claim(s.id, abs, kind);
        if (!o) return "";
        post({ type: "status", text: "Held back an edit to " + path.basename(abs) + ": chat “" + o.title + "” is changing it." });
        return heldMessage(abs, o);
      },
      confirmShell: async (command, cwd) => {
        const pick = await vscode.window.showWarningMessage("Agent (" + (s.title || "chat") + ") wants to run in " + cwd + ":\n\n" + command, { modal: true }, "Run");
        return pick === "Run";
      },
      // Permission rules (opencode-style): settings, then the agent's own; "ask" shows this prompt.
      rules: a.get("permissions", []),
      approved: this.context.workspaceState.get(APPROVALS_KEY, []),
      confirmPermission: async (req) => {
        const what = req.resources.map((x) => "  " + x).join("\n").slice(0, 900);
        const always = "Allow always";
        const pick = await vscode.window.showWarningMessage(
          "Agent (" + (s.title || "chat") + ") asks permission: " + req.action + " (" + req.tool + ")\n\n" + what + (req.suggest.length ? "\n\n“Allow always” saves for this workspace: " + req.suggest.map((x) => req.action + " " + x).join(", ") : ""),
          { modal: true },
          "Allow once",
          always,
          "Deny"
        );
        return pick === "Allow once" ? "once" : pick === always ? "always" : "reject";
      },
      saveApproval: (rules) => {
        const cur = this.context.workspaceState.get(APPROVALS_KEY, []);
        Promise.resolve(this.context.workspaceState.update(APPROVALS_KEY, [...cur, ...rules].slice(-200))).catch(() => {});
      },
      instructionFiles: env.instructionFiles,
    });
    // Memory (what the agent keeps between chats) and searching earlier chats, as in Claude.
    const memOn = a.get("memory", true);
    if (memOn) {
      tools.memory = this.memory(s);
      tools.onMemory = () => this.postPanelsSoon && this.postPanelsSoon();
      env.memory = tools.memory.promptText({ maxChars: a.get("memoryPromptChars", 6000) });
      env.memoryOn = true;
    }
    if (a.get("memorySearchChats", true)) {
      tools.chats = { root: this.store().root, folder: path.basename(this.storeFor(s).dir), current: s.id };
      env.chatSearch = true;
    }
    if (picked.agent && picked.agent.rules) tools.withAgentRules(picked.agent.rules);
    run.tools = tools;
    run.provider = backend.provider;
    const q = this.queueOf(s.id);
    const take = () => {
      this.pullInbox(s);
      const items = q.takeSteer();
      if (items.length) this.postPending(s.id);
      return items;
    };
    // What the agent loop (between rounds) and Claude Code (its input stream) read steering from.
    const steerSource = {
      take,
      has: () => {
        this.pullInbox(s);
        return q.hasSteer();
      },
      onPush: (fn) => q.onPush(fn),
    };
    const onEvent = (ev) => {
      if (ev.type === "steered") {
        run.steered.push({ text: ev.text, from: ev.from || "" });
        c.log.push({ cls: "user", text: ev.text, steered: true, from: ev.from || "" });
        post(ev);
        return;
      }
      if (ev.type === "tool" && ev.status === "done") {
        c.log.push({ cls: "tool", name: ev.name, label: ev.label, ok: ev.ok, text: String(ev.result || "").slice(0, 2000) });
      } else if (ev.type === "thought") c.log.push({ cls: "thought", text: ev.text });
      else if (ev.type === "status" && !ev.transient) c.log.push({ cls: "sys", text: ev.text });
      else if (ev.type === "assistant") c.log.push({ cls: "assistant", text: ev.text });
      else if (ev.type === "todos") c.todos = ev.todos;
      post(ev);
    };
    // Images linked in the prompt go to the model with it (Claude Code opens linked images itself).
    let images = [];
    let prompt = picked.text || text;
    if (backend.provider !== "claude-code") {
      try {
        const pi = await promptImages(tools, text, a.get("maxImages", 6));
        images = pi.images;
        if (pi.notes.length) {
          prompt = text + "\n\n[Images linked in this message]\n" + pi.notes.map((n) => "- " + n).join("\n");
          const msg = images.length
            ? "Attached " + images.length + " linked image" + (images.length > 1 ? "s" : "") + " for " + model
            : "Linked images not attached: " + model + " cannot see images (localAgentBridge.agent.vision)";
          c.log.push({ cls: "sys", text: msg });
          post({ type: "status", text: msg });
        }
      } catch (e) {
        post({ type: "status", text: "Could not load linked images: " + ((e && e.message) || e) });
      }
    }
    try {
      // Auto-switch: on Ollama, a model that clearly struggles with the request hands it to a stronger
      // installed model, which gets the chat so far plus what the first model tried.
      const switchMode = a.get("autoSwitch", "ollama");
      const canSwitch = backend.provider === "ollama" && switchMode !== "off";
      const turnStart = c.log.length;
      const runOpts = {
        backend,
        model,
        contextTokens: ctxTokens,
        switchOnStruggle: canSwitch,
        maxOutputTokens: lim.maxOutputTokens,
        effort: backend.provider === "anthropic" ? lim.effort : "",
        maxRounds: lim.maxRounds,
        limitLabel: lim.label,
        temperature: a.get("temperature", 0.2),
        allowTask: a.get("subagents", true),
        agent: picked.agent && picked.agent.name !== "build" ? picked.agent : null,
        agents: agentList,
        prompt,
        images,
        maxImages: a.get("maxImages", 6),
        history: c.history,
        prior: c.progress,
        tools,
        env,
        skills: this.getState().skills || [],
        signal: controller.signal,
        steer: steerSource,
        onEvent,
      };
      let result = backend.provider === "claude-code" ? await this.runClaudeCode({ backend, model, text, c, env, tools, lim, signal: controller.signal, onEvent, steer: steerSource }) : await runAgent(runOpts);
      const tried = [model];
      while (result && result.struggling && canSwitch && tried.length <= Math.max(0, a.get("autoSwitchMax", 2))) {
        const from = tried[tried.length - 1];
        const cands = await llm.ollamaSwitchCandidates(backend.baseUrl, from, { prefer: a.get("autoSwitchModels", []) || [], exclude: tried });
        if (!cands.length) {
          const none = "No other installed Ollama model can call tools, so " + from + " could not hand this over. Pull a stronger coding model (e.g. ollama pull qwen2.5-coder:14b) or list one in localAgentBridge.agent.autoSwitchModels.";
          c.log.push({ cls: "sys", text: none });
          post({ type: "status", text: none });
          break;
        }
        const next = cands[0];
        tried.push(next);
        // What the struggling model did this turn, for the next one to read first.
        const attempt = compress.turnText({ user: text, items: c.log.slice(turnStart) }, 1, 2).replace(/^### Turn 1 \(recent\)\n/, "");
        const note = "Switched " + from + " → " + next + ": " + result.struggling + ". " + next + " gets this chat and " + from + "'s attempt, and takes the request over.";
        c.log.push({ cls: "sys", text: note, switched: { from, to: next, why: result.struggling } });
        post({ type: "status", text: note });
        await this.setSessionModel(s, { provider: backend.provider, baseUrl: s.baseUrl || "", model: next });
        const r2 = await this.resolveFor(s, false);
        const lim2 = sessionLimits.resolve({ limits: s.limits, provider: backend.provider, get: (k, d) => a.get(k, d), modelMaxOut: r2.maxOut, ctxTokens: r2.ctxTokens });
        tools.model = next;
        try {
          tools.vision = await llm.supportsVision(backend, next, a.get("vision", "auto"));
        } catch {
          /* keep */
        }
        if (s.id === this.activeId) {
          this.model = next;
          this.ctxTokens = r2.ctxTokens;
          this.postHeader();
        }
        const handoff =
          "\n\n[Handoff] Another model (" + from + ") worked on this request first and was switched out because " + result.struggling + ". " +
          "Read what it did below; reuse what it found, do not repeat what failed, and finish the request. Files it changed are already changed on disk.\n" +
          "<previous_attempt>\n" + attempt.slice(-12000) + "\n</previous_attempt>";
        result = await runAgent({
          ...runOpts,
          model: next,
          contextTokens: r2.ctxTokens,
          maxOutputTokens: lim2.maxOutputTokens,
          maxRounds: lim2.maxRounds,
          prompt: prompt + handoff,
          prior: result.progress || c.progress,
          switchOnStruggle: tried.length <= Math.max(0, a.get("autoSwitchMax", 2)),
        });
      }
      if (result && result.struggling) {
        result.text = "Stopped early: " + result.struggling + ". " + (tried.length > 1 ? "Tried " + tried.join(" → ") + "." : "") + " Try a stronger model or narrow the request.";
        c.log.push({ cls: "assistant", text: result.text });
        post({ type: "assistant", text: result.text });
      }
      // Messages taken in while it worked are part of this turn's request.
      c.history.push({ role: "user", content: steer.withSteering(text, run.steered) }, { role: "assistant", content: result.text });
      if (result.sessionId) c.ccSession = result.sessionId; // Claude Code keeps the conversation itself
      if (result.progress) {
        c.progress = result.progress;
        // Each chat has its own progress.md in its session folder: parallel chats never share one.
        const file = this.storeFor(s).writeProgress(s.id, new Progress(result.progress).toText());
        if (file) post({ type: "status", text: "Progress index: " + file });
      }
      c.status = "done";
    } catch (e) {
      const msg = String((e && e.message) || e);
      c.log.push({ cls: msg === "stopped" ? "sys" : "err", text: msg === "stopped" ? "Stopped." : msg });
      post({ type: msg === "stopped" ? "status" : "error", text: msg === "stopped" ? "Stopped." : msg });
      c.status = msg === "stopped" ? "stopped" : "error";
      if (msg !== "stopped") {
        // Rediscover next time: the server may have gone away.
        this.backends.delete(key);
        if (s.id === this.activeId) this.backend = null;
      }
    } finally {
      // Even a stopped or failed turn keeps its snapshot, so its partial edits can be undone.
      const card = this.recordCheckpoint(tools, s.id);
      if (card) {
        run.changed = card.files.map((f) => f.path);
        c.log.push(card);
        post({ type: "changes", ...card });
        // A canvas the turn made or changed gets its own card (as in Cursor), and opens beside the editor.
        for (const f of card.files) {
          if (f.kind === "deleted" || !/\.canvas\.tsx$/i.test(f.path)) continue;
          const row = { cls: "canvas", file: f.path, name: path.basename(f.path).replace(/\.canvas\.tsx$/i, ""), kind: f.kind };
          c.log.push(row);
          post({ type: "canvas", ...row });
          this.showCanvas(f.path, { created: f.kind === "created" }).catch(() => {});
        }
      }
      if (!s.deleted) {
        try {
          const st = this.storeFor(s);
          st.recordTurn(s.id, { prompt: text.slice(0, 300), provider: backend.provider, model, status: c.status, files: card ? card.files.map((f) => f.path) : [] });
          if (card) {
            const shared = st.overlaps(s.id).filter((o) => o.status === "running");
            if (shared.length) {
              const note = "Files this chat changed are also being changed by: " + shared.map((o) => "“" + o.title + "” (" + o.files.map((f) => path.basename(f)).join(", ") + ")").join("; ");
              c.log.push({ cls: "sys", text: note });
              post({ type: "status", text: note });
            }
          }
        } catch {
          /* the sub-index is a convenience */
        }
      }
      if (c.status === "done" && backend.provider !== "claude-code") this.generateMemorySoon(s, { backend, model: s.model || model });
      await finish();
    }
  }

  /** One turn through the installed Claude Code CLI (provider "claude-code"). */
  async runClaudeCode({ backend, model, text, c, env, tools, lim, signal, onEvent, steer: steerSource }) {
    const a = cfg();
    const auth = a.get("claudeCodeAuth", "auto");
    const saved = (await this.secret()) || (/^sk-ant-/i.test(a.get("apiKey", "")) ? a.get("apiKey", "") : "");
    const cred = auth === "login" ? null : llm.anthropic.credentials({ apiKey: saved, workspaceId: a.get("claudeWorkspaceId", ""), useCli: false });
    if (auth === "apiKey" && !cred) throw new Error("claudeCodeAuth is apiKey but no Anthropic key is set. Run “Agent: Set Claude API Key”, or switch claudeCodeAuth to login.");
    const ctx = [];
    if (env.activeFile) ctx.push("Active file in the editor: " + env.activeFile + (env.activeLine ? " (cursor at line " + env.activeLine + ")" : ""));
    if (env.selection) ctx.push("Selected text:\n```\n" + String(env.selection).slice(0, 4000) + "\n```");
    let prompt = ctx.length ? text + "\n\n<editor-context>\n" + ctx.join("\n") + "\n</editor-context>" : text;
    // After /compress the old Claude Code session is dropped: its first new turn gets the summary.
    const sum = !c.ccSession && (c.history || []).find((h) => h && h.summary);
    if (sum) prompt = "<conversation-summary>\n" + sum.content + "\n</conversation-summary>\n\n" + prompt;
    const turn = (resume) =>
      claudeCode.run({
        exe: backend.exe,
        cwd: env.roots[0] || os.homedir(),
        prompt,
        // A chat raised above Standard passes its output cap on (CLAUDE_CODE_MAX_OUTPUT_TOKENS).
        env: claudeCode.buildEnv({ cred, auth, maxOutputTokens: lim && !sessionLimits.isStandard(c.limits) ? lim.maxOutputTokens : 0 }),
        args: claudeCode.buildArgs({
          model,
          permissionMode: a.get("claudeCodePermissionMode", "acceptEdits"),
          effort: lim ? lim.effort : a.get("claudeEffort", "default"),
          resume,
          shell: a.get("shell", "auto"),
          addDirs: [...env.roots.slice(1), ...(a.get("writableRoots", []) || [])],
        }),
        signal,
        onEvent,
        steer: steerSource,
        // For the changed-files card and Undo: keep what a file looked like when Claude Code read
        // it (it reads before it edits), and use that as the "before" once an edit is announced.
        // Reading at announce time is only the fallback: the write may already have landed.
        onRead: (p) => {
          if (!seen.has(p)) seen.set(p, readNow(p));
        },
        onEdit: (p) => {
          if (tools.checkpoint && !tools.checkpoint.has(p)) tools.checkpoint.set(p, { before: seen.has(p) ? seen.get(p) : readNow(p) });
          // Claude Code edits through its own tools, so the claim can only be recorded (and a
          // clash reported) after the fact.
          try {
            const o = this.storeFor(c).claim(c.id, p, "edit");
            if (o) onEvent({ type: "status", text: "Warning: Claude Code changed " + path.basename(p) + ", which chat “" + o.title + "” is also changing. Check both before keeping either." });
          } catch {
            /* index unwritable */
          }
        },
      });
    let seen = this.ccSeen.get(c.id);
    if (!seen) this.ccSeen.set(c.id, (seen = new Map()));
    const settle = () => {
      // Next turn's "before" is this turn's result.
      for (const p of tools.checkpoint ? tools.checkpoint.keys() : []) seen.set(p, readNow(p));
      if (seen.size > 400) this.ccSeen.set(c.id, new Map());
    };
    try {
      let res;
      try {
        res = await turn(c.ccSession || "");
      } catch (e) {
        if (!c.ccSession || !/no conversation found|session.*not found|could not resume/i.test(String(e.message || e))) throw e;
        onEvent({ type: "status", text: "The earlier Claude Code session is gone — starting a new one" });
        c.ccSession = "";
        res = await turn("");
      }
      onEvent({ type: "assistant", text: res.text });
      return res;
    } finally {
      settle();
    }
  }

  /**
   * /compress [focus]: replace a chat's history with a summary written by the chat's own model,
   * brief on older turns and detailed on the recent ones. Shown and stoppable like a turn.
   */
  // ---- memory -------------------------------------------------------------------------------

  /** User memory (every workspace) and this workspace's project memory. */
  memory(s) {
    const st = s ? this.storeFor(s) : this.store();
    return new memoryLib.MemoryStore({ root: st.root, projectDir: st.dir });
  }

  /**
   * Generate memory from a chat: every localAgentBridge.agent.memoryGenerateEvery turns, the model
   * reads the turns since the last pass and proposes memory updates. Runs in the background, after
   * the turn; a failure is only noted.
   */
  generateMemorySoon(s, { backend, model, force = false } = {}) {
    const a = cfg();
    if (!a.get("memory", true) || (!force && !a.get("memoryGenerate", true))) return;
    const every = Math.max(1, Number(a.get("memoryGenerateEvery", 3)) || 3);
    const log = s.log || [];
    const from = Math.min(Number(s.memoryAt) || 0, log.length);
    const turns = log.slice(from).filter((e) => e && e.cls === "user" && !e.command).length;
    if (!force && turns < every) return;
    if (this.memoryBusy && this.memoryBusy.has(s.id)) return;
    (this.memoryBusy = this.memoryBusy || new Set()).add(s.id);
    const post = (m) => this.post({ ...m, sid: s.id });
    (async () => {
      try {
        const r = backend ? { backend, model } : await this.resolveFor(s, false);
        if (!r.backend || r.backend.provider === "claude-code") return;
        const tr = compress.buildTranscript({ log: log.slice(from) }, { recentTurns: 6, maxChars: 16000 });
        if (!tr.turns) return;
        const store = this.memory(s);
        const messages = memoryLib.extractionMessages({ transcript: tr.text, existing: store.list(), includeSensitive: a.get("memoryIncludeSensitive", false) });
        const res = await llm.chat({ backend: r.backend, model: r.model || model, messages, maxTokens: 1500, temperature: 0.1 });
        const ops = memoryLib.parseOperations(res.content);
        s.memoryAt = log.length;
        this.storeFor(s).update(s.id, { memoryAt: s.memoryAt });
        if (!ops.length) {
          if (force) post({ type: "status", text: "Memory: nothing new worth remembering in this chat." });
          return;
        }
        const done = memoryLib.applyOperations(store, ops);
        const parts = [];
        if (done.added.length) parts.push("added " + done.added.join(", "));
        if (done.updated.length) parts.push("updated " + done.updated.join(", "));
        if (done.deleted.length) parts.push("forgot " + done.deleted.join(", "));
        const note = "Memory " + parts.join("; ") + " (Agent: Manage Memory to review)";
        (s.log || []).push({ cls: "sys", text: note });
        post({ type: "status", text: note });
        await this.saveConv(s);
      } catch (e) {
        if (force) post({ type: "status", text: "Memory could not be generated: " + ((e && e.message) || e) });
      } finally {
        this.memoryBusy.delete(s.id);
      }
    })();
  }

  /** Agent: Manage Memory — every memory with open / delete, plus add, import, export, settings. */
  async manageMemory() {
    const store = this.memory();
    const qp = vscode.window.createQuickPick();
    qp.title = "Memory";
    qp.matchOnDescription = true;
    qp.matchOnDetail = true;
    const del = { iconPath: new vscode.ThemeIcon("trash"), tooltip: "Delete this memory" };
    const edit = { iconPath: new vscode.ThemeIcon("edit"), tooltip: "Edit the file" };
    const fill = () => {
      const all = store.list();
      const actions = [
        { label: "$(add) Add a memory…", act: "add" },
        { label: "$(cloud-download) Import memory…", act: "import", description: "from Claude Code or another assistant" },
        { label: "$(archive) Export memory…", act: "export", description: ".zip of Markdown files" },
        { label: "$(sparkle) Generate memory from this chat now", act: "generate" },
        { label: "$(folder-opened) Open the memory folders", act: "folders" },
        { label: "$(settings-gear) Memory settings", act: "settings" },
      ];
      const mem = all.map((m) => ({
        label: (m.scope === "user" ? "$(account) " : "$(repo) ") + m.name,
        description: m.type + " · " + (m.scope === "user" ? "about you" : "this project"),
        detail: m.description,
        buttons: [edit, del],
        mem: m,
      }));
      qp.items = [...actions, { label: all.length ? all.length + " memories" : "No memories yet", kind: vscode.QuickPickItemKind ? vscode.QuickPickItemKind.Separator : undefined }, ...mem];
    };
    fill();
    qp.onDidTriggerItemButton(async (e) => {
      const m = e.item.mem;
      if (!m) return;
      if (e.button === del) {
        store.remove(m.name, m.scope);
        fill();
      } else {
        qp.hide();
        await vscode.window.showTextDocument(vscode.Uri.file(m.file));
      }
    });
    qp.onDidAccept(async () => {
      const it = qp.selectedItems[0];
      if (!it) return;
      qp.hide();
      if (it.mem) return vscode.window.showTextDocument(vscode.Uri.file(it.mem.file));
      if (it.act === "add") return this.addMemory();
      if (it.act === "import") return this.importMemory();
      if (it.act === "export") return this.exportMemory();
      if (it.act === "generate") return this.generateMemorySoon(this.active(), { force: true });
      if (it.act === "settings") return vscode.commands.executeCommand("workbench.action.openSettings", "localAgentBridge.agent.memory");
      if (it.act === "folders") {
        for (const sc of store.scopes()) fs.mkdirSync(store.dir(sc), { recursive: true });
        return vscode.commands.executeCommand("revealFileInOS", vscode.Uri.file(store.dir("user")));
      }
    });
    qp.onDidHide(() => qp.dispose());
    qp.show();
  }

  async addMemory() {
    const body = await vscode.window.showInputBox({ prompt: "What should the agent remember?", placeHolder: "e.g. I prefer PowerShell examples; never commit to main" });
    if (!body) return;
    const scope = await vscode.window.showQuickPick(
      [
        { label: "About me", description: "every workspace", scope: "user" },
        { label: "About this project", description: path.basename(folders()[0] || "") || "this workspace", scope: "project" },
      ],
      { placeHolder: "Where does it apply?" }
    );
    if (!scope) return;
    const type = await vscode.window.showQuickPick(
      [
        { label: "user", description: "who you are, how you work" },
        { label: "feedback", description: "how the agent should work" },
        { label: "project", description: "goals and constraints not in the code" },
        { label: "reference", description: "where something lives" },
      ],
      { placeHolder: "Kind of memory" }
    );
    if (!type) return;
    const file = this.memory().write({ scope: scope.scope, name: body.split(/\s+/).slice(0, 6).join(" "), description: body, type: type.label, body });
    vscode.window.showInformationMessage("Saved to memory: " + path.basename(file));
  }

  /** Import memory: Claude Code memory folders, a folder of Markdown files, or another assistant's answer. */
  async importMemory() {
    const store = this.memory();
    const ws = folders()[0] || "";
    const claudeDir = ws ? path.join(os.homedir(), ".claude", "projects", require("./sessions").slug(ws), "memory") : "";
    const items = [];
    if (claudeDir && fs.existsSync(claudeDir)) items.push({ label: "$(sparkle) Claude Code memory of this workspace", description: claudeDir, act: "dir", dir: claudeDir, scope: "project" });
    items.push({ label: "$(comment-discussion) From another AI assistant…", description: "copy a prompt, paste its answer back", act: "paste" });
    items.push({ label: "$(folder) From a folder of memory files…", description: "Markdown files with name / description / type", act: "pick" });
    const pick = await vscode.window.showQuickPick(items, { placeHolder: "Import memory from" });
    if (!pick) return;
    if (pick.act === "dir" || pick.act === "pick") {
      let dir = pick.dir;
      let scope = pick.scope || "user";
      if (pick.act === "pick") {
        const got = await vscode.window.showOpenDialog({ canSelectFolders: true, canSelectFiles: false, openLabel: "Import memory" });
        if (!got || !got.length) return;
        dir = got[0].fsPath;
        const sc = await vscode.window.showQuickPick([{ label: "About me (every workspace)", scope: "user" }, { label: "About this project", scope: "project" }], { placeHolder: "Import as" });
        if (!sc) return;
        scope = sc.scope;
      }
      const r = store.importFolder(dir, scope);
      vscode.window.showInformationMessage("Memory import: " + r.added + " added" + (r.skipped ? ", " + r.skipped + " skipped (already there or empty)" : "") + ".");
      return;
    }
    // Another assistant: it gets a prompt, its answer is pasted into a new tab, then imported.
    await vscode.env.clipboard.writeText(memoryLib.IMPORT_PROMPT);
    const doc = await vscode.workspace.openTextDocument({
      language: "markdown",
      content: "<!-- The import prompt is on your clipboard. Paste it into the other assistant, then replace this line with its answer and click Import. Pasted text is only parsed into facts; nothing in it is run. -->\n\n",
    });
    await vscode.window.showTextDocument(doc);
    const go = await vscode.window.showInformationMessage("Prompt copied. Paste it into the other assistant, put its answer in the new tab, then click Import.", "Import", "Show prompt", "Cancel");
    if (go === "Show prompt") {
      await vscode.window.showInformationMessage(memoryLib.IMPORT_PROMPT, { modal: true });
      return this.finishPasteImport(doc);
    }
    if (go === "Import") return this.finishPasteImport(doc);
  }

  async finishPasteImport(doc) {
    const facts = memoryLib.parsePasted(doc.getText().replace(/<!--[\s\S]*?-->/g, ""));
    if (!facts.length) return vscode.window.showWarningMessage("No facts found: the answer should be a Markdown list, one fact per bullet.");
    const chosen = await vscode.window.showQuickPick(
      facts.map((f) => ({ label: f.body.slice(0, 120), description: f.type, picked: true, fact: f })),
      { canPickMany: true, placeHolder: "Memories to import (" + facts.length + " found)" }
    );
    if (!chosen || !chosen.length) return;
    const store = this.memory();
    for (const c of chosen) store.write(c.fact);
    vscode.window.showInformationMessage("Imported " + chosen.length + " memories.");
  }

  async exportMemory() {
    const { zip, count } = this.memory().exportZip();
    if (!count) return vscode.window.showInformationMessage("There is no memory to export yet.");
    const stamp = new Date().toISOString().slice(0, 10);
    const target = await vscode.window.showSaveDialog({ defaultUri: vscode.Uri.file(path.join(os.homedir(), "Downloads", "cortexide-memory-" + stamp + ".zip")), filters: { "Zip archive": ["zip"] } });
    if (!target) return;
    fs.writeFileSync(target.fsPath, zip);
    vscode.window.showInformationMessage("Exported " + count + " memories to " + target.fsPath);
  }

  /** localAgentBridge.agent.autoCompactPercent of the context window is filled by the history alone. */
  async autoCompactDue(s) {
    const pct = Number(cfg().get("autoCompactPercent", 60)) || 0;
    if (pct <= 0 || !s || !(s.history || []).length) return false;
    try {
      const r = await this.resolveFor(s, false);
      // Claude Code compacts its own sessions.
      if (!r || !r.backend || r.backend.provider === "claude-code") return false;
      return compress.autoCompactDue(s.history, r.ctxTokens, pct);
    } catch {
      return false;
    }
  }

  async compressChat(s, focus, opts = {}) {
    if (!s) return;
    const post = (m) => this.post({ ...m, sid: s.id });
    if (this.runs.has(s.id) || this.storeFor(s).runningElsewhere(s.id)) {
      // From the menu or command palette while it works: queue it like a typed /compress.
      return this.send("/compress" + (focus ? " " + focus : ""), s.id, "queue");
    }
    const preview = compress.buildTranscript(s, { maxChars: 1e9 });
    if (!preview.turns && !preview.hadSummary) {
      post({ type: "status", text: "Nothing to compress yet: this chat has no turns." });
      post({ type: "idle" });
      return;
    }
    const controller = new AbortController();
    const run = { controller, s, steerable: false };
    this.runs.set(s.id, run);
    run.poll = setInterval(() => this.pullInbox(s), 1000);
    let outcome = "done";
    const was = s.status;
    const label = opts.auto ? "" : "/compress" + (focus ? " " + focus : "");
    if (label) {
      s.log.push({ cls: "user", text: label, command: true });
      post({ type: "user", text: label });
    } else post({ type: "status", text: "Auto-compacting: this chat's history is nearing the context limit (localAgentBridge.agent.autoCompactPercent). Your message runs right after." });
    post({ type: "busy" });
    const a = cfg();
    try {
      const r = await this.resolveFor(s, false);
      const { backend, model, ctxTokens } = r;
      // Leave room for the instructions and the summary: about 60% of the window, ~3.5 chars/token.
      const maxChars = Math.max(8000, Math.min(200000, Math.floor((ctxTokens || 16384) * 0.6 * 3.5)));
      const tr = compress.buildTranscript(s, { recentTurns: a.get("compressRecentTurns", 3), maxChars });
      post({ type: "status", transient: true, text: "Compressing " + tr.turns + " turn" + (tr.turns === 1 ? "" : "s") + " with " + model + "…" });
      // "Compact instructions" in AGENTS.md / CLAUDE.md / project rules shape every summary.
      let instructions = "";
      try {
        instructions = compress.compactInstructions(editorEnv().rules);
      } catch {
        instructions = "";
      }
      const messages = compress.summaryMessages(tr.text, focus, { instructions });
      const maxTokens = Math.max(1024, Math.min(8000, Math.floor((ctxTokens || 16384) / 4)));
      let summary = "";
      if (backend.provider === "claude-code") {
        const auth = a.get("claudeCodeAuth", "auto");
        const saved = (await this.secret()) || (/^sk-ant-/i.test(a.get("apiKey", "")) ? a.get("apiKey", "") : "");
        const cred = auth === "login" ? null : llm.anthropic.credentials({ apiKey: saved, workspaceId: a.get("claudeWorkspaceId", ""), useCli: false });
        const env = editorEnv();
        const res = await claudeCode.run({
          exe: backend.exe,
          cwd: env.roots[0] || os.homedir(),
          prompt: messages[0].content + "\n\nDo not use any tools.\n\n" + messages[1].content,
          env: claudeCode.buildEnv({ cred, auth, maxOutputTokens: 0 }),
          args: claudeCode.buildArgs({ model, permissionMode: "plan", shell: "off" }),
          signal: controller.signal,
          onEvent: () => {},
        });
        summary = compress.extractSummary(res.text);
      } else {
        const res = await llm.chat({ backend, model, messages, maxTokens, temperature: 0.2, numCtx: ctxTokens, signal: controller.signal });
        summary = compress.extractSummary(res.content);
      }
      if (controller.signal.aborted) throw new Error("stopped");
      if (!summary) throw new Error("The model returned an empty summary; the history was left as it was.");
      const before = (s.history || []).reduce((n, h) => n + String(h.content || "").length, 0);
      this.generateMemorySoon(s, { backend, model, force: false });
      const files = compress.workingFiles(s.progress);
      s.history = compress.summaryHistory(summary, tr.turns, { todos: s.todos || [], files, auto: !!opts.auto });
      s.ccSession = ""; // Claude Code chats start a fresh session that is handed the summary
      // The progress index's per-turn notes, searches and errors repeat what the summary now
      // covers; keep only its file and command index.
      if (s.progress) {
        s.progress = { ...s.progress, notes: [], searched: [], errors: [] };
        try {
          this.storeFor(s).writeProgress(s.id, new Progress(s.progress).toText());
        } catch {
          /* progress.md is a convenience */
        }
      }
      // One boundary row: the turns above it are no longer sent to the model; the summary is.
      const row = { cls: "compact", compressed: true, summary, turns: tr.turns, auto: !!opts.auto, model, before, after: summary.length, files: files.length };
      s.log.push(row);
      post({ type: "compact", ...row });
      s.status = was === "running" ? "done" : was || "done";
    } catch (e) {
      const msg = String((e && e.message) || e);
      const stopped = msg === "stopped" || controller.signal.aborted;
      outcome = stopped ? "stopped" : "error";
      const text = stopped ? "Compression stopped; the history was left as it was." : "Could not compress: " + (e.header || msg);
      s.log.push({ cls: stopped ? "sys" : "err", text });
      post({ type: stopped ? "status" : "error", text });
    } finally {
      if (this.runs.get(s.id) === run) this.runs.delete(s.id);
      clearInterval(run.poll);
      // Messages sent while it compressed run now, on the compressed history.
      const next = this.nextFollowUp(s, null, outcome);
      await this.saveConv(s);
      post({ type: "idle" });
      if (opts.then && outcome !== "stopped") {
        // The message that triggered the auto-compact runs first, then anything queued meanwhile.
        if (outcome === "error") post({ type: "status", text: "Auto-compact failed; sending your message on the full history." });
        const fail = (e) => post({ type: "error", text: String((e && e.message) || e) });
        setTimeout(() => this.send(opts.then, s.id, undefined, { noAutoCompact: true }).then(() => next && this.send(next, s.id)).catch(fail), 0);
        return;
      }
      // Stopped: the message was not sent; it goes back into the input box.
      if (opts.then) post({ type: "unsent", text: opts.then });
      if (next) {
        post({ type: "status", transient: true, text: "Sending your next message…" });
        setTimeout(() => this.send(next, s.id).catch((e) => post({ type: "error", text: String((e && e.message) || e) })), 0);
      }
    }
  }

  /** Snapshot what this turn changed; returns the log card for it, or null if nothing changed. */
  recordCheckpoint(tools, sid) {
    if (!tools || !tools.checkpoint || !tools.checkpoint.size) return null;
    const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    const files = [];
    for (const [p, { before }] of tools.checkpoint) {
      const after = readNow(p);
      if (after === before) continue; // edited and changed back
      files.push({ path: p, before, after });
    }
    if (!files.length) return null;
    this.checkpoints.push({ id, sid: sid || this.activeId, files });
    this.checkpoints = this.checkpoints.slice(-MAX_CHECKPOINTS);
    return {
      cls: "changes",
      id,
      files: files.map((f) => ({
        path: f.path,
        kind: f.before == null ? "created" : f.after == null ? "deleted" : "modified",
        ...lineDelta(f.before, f.after),
      })),
    };
  }

  async showDiff(id, file) {
    const cp = this.checkpoints.find((x) => x.id === id);
    const f = cp && cp.files.find((x) => x.path === file);
    if (!f) {
      if (fs.existsSync(file)) await vscode.window.showTextDocument(vscode.Uri.file(file), { preview: true });
      return;
    }
    if (f.before == null || !fs.existsSync(file)) {
      await vscode.window.showTextDocument(fs.existsSync(file) ? vscode.Uri.file(file) : beforeUri(id, file), { preview: true });
      return;
    }
    await vscode.commands.executeCommand("vscode.diff", beforeUri(id, file), vscode.Uri.file(file), path.basename(file) + " (before agent ↔ now)");
  }

  /**
   * Absolute path of a file named in the chat: absolute as is, else under a workspace folder,
   * else a search of the workspace by that relative path or name (a pick when several match).
   * @returns {Promise<string|null>}
   */
  async locateFile(p) {
    p = String(p || "").trim();
    if (!p) return null;
    const roots = (vscode.workspace.workspaceFolders || []).map((f) => f.uri.fsPath);
    const hit = fileRef.resolve(p, roots, { exists: (x) => fs.existsSync(x), home: os.homedir(), join: path.join });
    if (hit) return hit;
    if (fileRef.isAbs(p) || /^~[\\/]/.test(p) || typeof vscode.workspace.findFiles !== "function") return null;
    const rel = p.replace(/\\/g, "/").replace(/^(\.\/)+/, "").replace(/^\/+/, "").replace(/[[\]{}]/g, "?");
    let found = [];
    try {
      found = await vscode.workspace.findFiles("**/" + rel, "**/{node_modules,.git}/**", 30);
    } catch {
      return null;
    }
    if (found.length <= 1) return found.length ? found[0].fsPath : null;
    const items = found.map((u) => ({ label: path.basename(u.fsPath), description: vscode.workspace.asRelativePath ? vscode.workspace.asRelativePath(u, true) : u.fsPath, file: u.fsPath }));
    const pick = await vscode.window.showQuickPick(items, { placeHolder: found.length + " files match “" + p + "”. Which one?" });
    return pick ? pick.file : null;
  }

  /** Files with uncommitted changes, from the built-in Git extension (empty when it is off). */
  gitChanges() {
    try {
      const ext = vscode.extensions && vscode.extensions.getExtension("vscode.git");
      const api = ext && ext.isActive && ext.exports && ext.exports.getAPI(1);
      if (!api) return [];
      const out = new Set();
      for (const r of api.repositories || []) {
        const st = r.state || {};
        for (const c of [].concat(st.workingTreeChanges || [], st.indexChanges || [], st.mergeChanges || [])) if (c && c.uri) out.add(c.uri.fsPath);
      }
      return [...out];
    } catch {
      return [];
    }
  }

  /**
   * What an empty chat shows, as in Cursor: the open tabs, this workspace's panels (Changes, Browser,
   * Terminal, Files, Canvas, Side Chat), its canvases, and extra panels from localAgentBridge.agent.panels.
   */
  postPanels() {
    const d = this.panelData();
    this.post({ type: "panels", ...d });
    if (this.home) this.home.refresh(d);
  }

  /** Everything the empty chat and the New Tab page list (tabs, panels, canvases, recent chats). */
  panelData() {
    const tabs = [];
    try {
      for (const g of (vscode.window.tabGroups && vscode.window.tabGroups.all) || []) {
        for (const t of g.tabs || []) {
          const u = t.input && (t.input.uri || t.input.modified);
          if (!u || !u.toString) continue;
          tabs.push({ label: t.label, uri: u.toString(), path: u.scheme === "file" ? u.fsPath : "", dirty: !!t.isDirty, active: !!(t.isActive && g.isActive) });
        }
      }
    } catch {
      /* no tab API */
    }
    const roots = folders();
    const mine = new Set(roots.flatMap((f) => [path.basename(f), cursorProjectSlug(f)]));
    let canvases = [];
    try {
      canvases = scanCanvases(roots)
        .filter((c) => mine.has(c.project))
        .map((c) => ({ name: c.name, file: c.file, project: c.project }))
        .slice(0, 30);
    } catch {
      /* unreadable folder */
    }
    const custom = (cfg().get("panels", []) || [])
      .map((p, i) => ({ p, i }))
      .filter(({ p }) => p && p.label)
      .map(({ p, i }) => ({ label: String(p.label), icon: String(p.icon || ""), hint: String(p.hint || ""), index: i }));
    const ws = vscode.workspace.name || (roots[0] ? path.basename(roots[0]) : "");
    // Custom /commands and named @agents for the ＋ / @ picker.
    let commands = [];
    let agents = [];
    try {
      commands = commandsLib.loadCommands(roots).map((c) => ({ name: c.name, description: c.description, hint: c.hint }));
      agents = agentsLib.loadAgents(roots).filter((x) => !x.hidden && !x.builtin).map((x) => ({ name: x.name, mode: x.mode, description: x.description }));
    } catch {
      /* unreadable folders */
    }
    let recent = [];
    try {
      recent = this.store()
        .list()
        .slice(0, 8)
        .map((e) => ({ id: e.id, title: e.title || "New chat", model: e.model || "", updated: e.updated || 0, pinned: !!e.pinned, status: this.runs.has(e.id) ? "running" : e.status || "idle" }));
    } catch {
      /* no history yet */
    }
    const backend = this.backend ? this.backend.label + " · " + (this.model || "default model") : "";
    let otherCanvases = 0;
    try {
      otherCanvases = require("./canvas-link").otherCanvases(roots).length;
    } catch {
      /* unreadable */
    }
    return { tabs, canvases, custom, ws, changes: this.gitChanges().length, commands, agents, recent, backend, otherCanvases };
  }

  /**
   * Open a canvas in its preview beside the editor. An open preview already re-renders when the
   * file changes, so after a turn it is only opened when it is not showing (and
   * localAgentBridge.canvas.autoOpen allows); force opens it anyway.
   */
  async showCanvas(file, { force = false, created = false } = {}) {
    if (!file) return;
    const uri = vscode.Uri.file(String(file));
    if (!force) {
      const mode = cfg().get("canvasAutoOpen", "always");
      if (mode === "off" || (mode === "created" && !created)) return;
      try {
        const open = vscode.window.tabGroups.all.some((g) => g.tabs.some((t) => t.input && t.input.uri && t.input.uri.fsPath.toLowerCase() === uri.fsPath.toLowerCase() && t.input.viewType === "localAgentBridge.canvasPreview"));
        if (open) return;
      } catch {
        /* no tab API */
      }
    }
    await vscode.commands.executeCommand("vscode.openWith", uri, "localAgentBridge.canvasPreview", { viewColumn: vscode.ViewColumn.Beside, preserveFocus: !force });
  }

  /**
   * A request about a canvas from its toolbar: the chat on screen takes it when it is idle, else a
   * new chat does.
   */
  async askAboutCanvas(text) {
    const t = String(text || "").trim();
    if (!t) return;
    await this.focus();
    let s = this.active();
    if (!s || this.runs.has(s.id)) s = await this.newChat({});
    else await this.setActive(s.id);
    this.send(t, s.id).catch((e) => vscode.window.showErrorMessage("Agent: " + ((e && e.message) || e)));
  }

  /** A prompt typed on the New Tab page: a new chat in the Agent panel runs it. */
  async startFromHome(text, mode) {
    const t = String(text || "").trim();
    if (!t) return;
    await this.focus();
    const s = await this.newChat();
    const body = /^\//.test(t) ? t : require("./composer").compose(t, mode || "agent", []);
    this.send(body, s.id).catch((e) => vscode.window.showErrorMessage("Agent: " + ((e && e.message) || e)));
  }

  /** Open a chat from the New Tab page's recent list. */
  async openChatFromHome(id) {
    await this.focus();
    if (id && this.session(id)) await this.setActive(id);
  }

  /**
   * A panel picked in an empty chat.
   * @param {{id:string, uri?:string, file?:string, index?:number}} m
   *   id: tab | changes | browser | terminal | files | canvas | openCanvas | side | custom
   */
  async panelAction(m) {
    const run = (c, ...args) => vscode.commands.executeCommand(c, ...args);
    const id = String(m.id || "");
    if (id === "tab" && m.uri) return run("vscode.open", vscode.Uri.parse(String(m.uri)));
    if (id === "changes") return run("workbench.view.scm");
    if (id === "files") return run("workbench.view.explorer");
    if (id === "terminal") return run("workbench.action.terminal.focus");
    if (id === "side") {
      await this.focus();
      return this.newChat();
    }
    if (id === "browser") return this.openBrowser("");
    if (id === "openCanvas" && m.file) return run("localAgentBridge.openCanvas", String(m.file));
    if (id === "canvas") {
      // No canvas yet: start one with the canvas skill; else pick one to open.
      let any = false;
      try {
        any = scanCanvases(folders()).length > 0;
      } catch {
        /* none */
      }
      if (any) return run("localAgentBridge.openCanvas");
      this.post({ type: "seed", text: "Follow the canvas skill and make a canvas (.canvas.tsx in the workspace canvases folder) that shows " });
      return;
    }
    if (id === "custom") {
      const p = (cfg().get("panels", []) || [])[Number(m.index)];
      if (!p) return;
      if (p.command) return run(String(p.command), ...(Array.isArray(p.args) ? p.args : p.args != null ? [p.args] : []));
      if (p.url) return this.openBrowser(String(p.url));
      if (p.file) {
        const f = (await this.locateFile(String(p.file))) || String(p.file);
        return /\.canvas\.tsx$/i.test(f) ? run("localAgentBridge.openCanvas", f) : run("vscode.open", vscode.Uri.file(f));
      }
      if (p.prompt) this.post({ type: "seed", text: String(p.prompt) });
    }
  }

  /** The built-in Simple Browser beside the editor (asks for the address when none is given). */
  async openBrowser(url) {
    let u = url;
    if (!u) {
      u = await vscode.window.showInputBox({ prompt: "Address to open in the browser panel", value: this.lastUrl || "http://127.0.0.1:3000" });
      if (!u) return;
    }
    if (!/^[a-z]+:\/\//i.test(u)) u = "http://" + u;
    this.lastUrl = u;
    try {
      await vscode.commands.executeCommand("simpleBrowser.show", u);
    } catch {
      await vscode.env.openExternal(vscode.Uri.parse(u));
    }
  }

  /** Folder for files pasted or dropped from outside (no path of their own), beside the chat history. */
  attachDir() {
    const dir = path.join(this.store().root, "attachments");
    fs.mkdirSync(dir, { recursive: true });
    return dir;
  }

  /**
   * Context for the composer: dropped files, pasted images, or a pick from the @ menu. Answers the
   * panel with {type:"attached", items}, items being {path} or {label, text}.
   * @param {{kind:string, uris?:string[], name?:string, data?:string, id?:string}} m
   *   kind: uris | data | pick | active | tabs | files | changes | problems | chat
   */
  async attach(m) {
    const kind = String(m.kind || "");
    const items = [];
    const rel = (p) => (vscode.workspace.asRelativePath ? vscode.workspace.asRelativePath(p, true) : p);
    const addPath = (p) => p && items.push({ path: p });
    if (kind === "uris") {
      for (const s of m.uris || []) {
        try {
          const u = /^[a-z][\w+.-]+:/i.test(s) && !/^[A-Za-z]:[\\/]/.test(s) ? vscode.Uri.parse(s) : vscode.Uri.file(s);
          if (u.scheme === "file") addPath(u.fsPath);
          else if (/^https?$/.test(u.scheme)) items.push({ label: "Link", text: u.toString() });
        } catch {
          /* not a URI */
        }
      }
    } else if (kind === "data") {
      const buf = Buffer.from(String(m.data || "").replace(/^data:[^,]*,/, ""), "base64");
      if (!buf.length) throw new Error("The dropped file was empty or could not be read.");
      if (buf.length > 25 * 1024 * 1024) throw new Error("Attachments are limited to 25 MB (" + composer.safeName(m.name) + " is " + Math.round(buf.length / 1048576) + " MB).");
      const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\..*/, "").replace("T", "-");
      const file = path.join(this.attachDir(), stamp + "-" + composer.safeName(m.name || "pasted.png"));
      fs.writeFileSync(file, buf);
      addPath(file);
    } else if (kind === "pick") {
      const root = folders()[0];
      const got = await vscode.window.showOpenDialog({ canSelectMany: true, canSelectFolders: true, openLabel: "Attach", defaultUri: root ? vscode.Uri.file(root) : undefined });
      for (const u of got || []) addPath(u.fsPath);
    } else if (kind === "active") {
      const ed = vscode.window.activeTextEditor;
      if (!ed) throw new Error("No editor is active.");
      const sel = ed.selection;
      const f = ed.document.uri.scheme === "file" ? ed.document.uri.fsPath : ed.document.uri.toString();
      if (sel && !sel.isEmpty) {
        const a = sel.start.line + 1, b = sel.end.line + (sel.end.character === 0 && sel.end.line > sel.start.line ? 0 : 1);
        items.push({ label: "Selection " + rel(f) + ":" + a + (b > a ? "-" + b : ""), text: ed.document.getText(sel).slice(0, 40000) });
      } else addPath(f);
    } else if (kind === "tabs") {
      for (const g of (vscode.window.tabGroups && vscode.window.tabGroups.all) || []) {
        for (const t of g.tabs || []) {
          const u = t.input && (t.input.uri || t.input.modified);
          if (u && u.scheme === "file") addPath(u.fsPath);
        }
      }
      if (!items.length) throw new Error("No files are open in tabs.");
    } else if (kind === "files") {
      const found = await vscode.workspace.findFiles("**/*", "**/{node_modules,.git,bin,obj,dist,out}/**", 5000);
      const pick = await vscode.window.showQuickPick(
        found.map((u) => ({ label: path.basename(u.fsPath), description: rel(u.fsPath), file: u.fsPath })),
        { canPickMany: true, matchOnDescription: true, placeHolder: "Files to attach" }
      );
      for (const p of pick || []) addPath(p.file);
    } else if (kind === "changes") {
      const ch = this.gitChanges();
      if (!ch.length) throw new Error("No uncommitted changes found (needs the built-in Git extension).");
      ch.forEach(addPath);
    } else if (kind === "problems") {
      const lines = [];
      for (const [u, ds] of vscode.languages.getDiagnostics()) {
        for (const d of ds) {
          if (d.severity > vscode.DiagnosticSeverity.Warning) continue;
          lines.push(rel(u.fsPath) + ":" + (d.range.start.line + 1) + ":" + (d.range.start.character + 1) + " " + (d.severity === vscode.DiagnosticSeverity.Error ? "error" : "warning") + " " + d.message.split("\n")[0] + (d.source ? " [" + d.source + "]" : ""));
        }
      }
      if (!lines.length) throw new Error("The Problems view has no errors or warnings.");
      items.push({ label: "Problems (" + lines.length + ")", text: lines.slice(0, 300).join("\n") });
    } else if (kind === "chat" && m.id) {
      const s = this.session(String(m.id));
      if (!s) throw new Error("That chat is not in this workspace's history.");
      items.push({ label: "Chat “" + (s.title || m.id) + "”", text: transcript(s, "").slice(-30000) });
    }
    if (items.length) this.post({ type: "attached", items });
  }

  /**
   * The panel's right-click menu on a file named in the chat.
   * @param {{action:string, path:string, line?:number, col?:number, id?:string}} m
   *   action: open | side | diff | reveal | os | copy | copyRel
   */
  async fileAction(m) {
    const action = String(m.action || "open");
    if (action === "diff" && m.id) return this.showDiff(m.id, m.path);
    const ref = fileRef.whole(m.path) || { path: String(m.path || ""), line: 0, col: 0 };
    const file = await this.locateFile(ref.path);
    if (!file) {
      vscode.window.showWarningMessage("Agent: can't find “" + ref.path + "” in this workspace.");
      return false;
    }
    const uri = vscode.Uri.file(file);
    const isDir = (() => {
      try {
        return fs.statSync(file).isDirectory();
      } catch {
        return false;
      }
    })();
    if (action === "copy" || action === "copyRel") {
      const text = action === "copyRel" && vscode.workspace.asRelativePath ? vscode.workspace.asRelativePath(uri, false) : file;
      await vscode.env.clipboard.writeText(text);
      return true;
    }
    if (action === "os") {
      await vscode.commands.executeCommand("revealFileInOS", uri);
      return true;
    }
    if (action === "reveal" || isDir) {
      await vscode.commands.executeCommand("revealInExplorer", uri);
      return true;
    }
    const column = action === "side" ? vscode.ViewColumn.Beside : undefined;
    if (NON_TEXT.test(file)) {
      await vscode.commands.executeCommand("vscode.open", uri, column ? { viewColumn: column } : undefined);
      return true;
    }
    const line = Math.max(0, (Number(m.line) || ref.line || 1) - 1);
    const col = Math.max(0, (Number(m.col) || ref.col || 1) - 1);
    const opts = { preview: action !== "side", viewColumn: column };
    if ((m.line || ref.line) && vscode.Range) opts.selection = new vscode.Range(line, col, line, col);
    try {
      await vscode.window.showTextDocument(uri, opts);
    } catch {
      await vscode.commands.executeCommand("vscode.open", uri, column ? { viewColumn: column } : undefined);
    }
    return true;
  }

  /** Put back every file the given turn (default: the latest) changed. */
  async undoTurn(id) {
    // Default: the latest turn of the chat on screen, else the latest turn of any chat.
    const mine = this.checkpoints.filter((x) => x.sid === this.activeId);
    const cp = id ? this.checkpoints.find((x) => x.id === id) : mine[mine.length - 1] || this.checkpoints[this.checkpoints.length - 1];
    if (!cp) {
      vscode.window.showInformationMessage("Nothing to undo. Snapshots of agent edits last until CortexIDE restarts.");
      return false;
    }
    if (this.runs.has(cp.sid)) {
      vscode.window.showWarningMessage("Stop that chat before undoing its edits.");
      return false;
    }
    const later = this.checkpoints.slice(this.checkpoints.indexOf(cp) + 1);
    const changedSince = cp.files.filter((f) => readNow(f.path) !== f.after || later.some((l) => l.files.some((x) => x.path === f.path)));
    const names = cp.files.map((f) => path.basename(f.path)).join(", ");
    const warn = changedSince.length
      ? "\n\nChanged again since that turn (your edits or a later turn would be lost): " + changedSince.map((f) => path.basename(f.path)).join(", ")
      : "";
    const pick = await vscode.window.showWarningMessage("Revert the agent's changes to " + cp.files.length + " file(s): " + names + "?" + warn, { modal: true }, "Revert");
    if (pick !== "Revert") return false;
    const failed = [];
    for (const f of cp.files) {
      try {
        if (f.before == null) {
          if (fs.existsSync(f.path)) await vscode.workspace.fs.delete(vscode.Uri.file(f.path), { useTrash: true });
        } else {
          const doc = vscode.workspace.textDocuments.find((d) => d.uri.fsPath.toLowerCase() === f.path.toLowerCase());
          if (doc && doc.isDirty) {
            const edit = new vscode.WorkspaceEdit();
            edit.replace(doc.uri, new vscode.Range(doc.positionAt(0), doc.positionAt(doc.getText().length)), f.before);
            await vscode.workspace.applyEdit(edit);
            await doc.save();
          } else {
            fs.mkdirSync(path.dirname(f.path), { recursive: true });
            fs.writeFileSync(f.path, f.before, "utf8");
          }
        }
      } catch (e) {
        failed.push(path.basename(f.path) + " (" + (e.message || e) + ")");
      }
    }
    this.checkpoints = this.checkpoints.filter((x) => x !== cp);
    const msg = failed.length ? "Reverted with errors: " + failed.join("; ") : "Reverted " + cp.files.length + " file(s) to before that agent turn.";
    const c = this.session(cp.sid) || this.active();
    const post = (m) => this.post({ ...m, sid: c.id });
    const card = c.log.find((r) => r.cls === "changes" && r.id === cp.id);
    if (card) card.undone = true;
    c.log.push({ cls: "sys", text: msg });
    c.history.push({ role: "user", content: "(I reverted your changes to " + names + ".)" }, { role: "assistant", content: "Understood — those files are back to how they were before that turn." });
    await this.saveConv(c, { touch: false });
    post({ type: "status", text: msg });
    post({ type: "undone", id: cp.id });
    return !failed.length;
  }

  /** Open a new chat. A chat that is still working keeps running in the background. */
  async newChat(init) {
    const cur = this.activeId ? this.session(this.activeId) : null;
    // Reuse an untouched chat instead of piling up empty ones.
    const reuse = !init && cur && !(cur.log || []).length && !this.runs.has(cur.id);
    const s = reuse ? cur : this.createSession(init);
    await this.setActive(s.id);
    return s;
  }

  /**
   * Send one prompt to several models at once: one new chat per model, all running side by side.
   * Good for comparing answers, reviews and plans; they share the workspace, so parallel edits
   * to the same files can collide.
   */
  async runOnModels(text) {
    text = String(text || "").trim();
    if (!text) {
      vscode.window.showInformationMessage("Type the prompt in the composer first, then choose Run on several models.");
      return [];
    }
    const items = await this.modelCandidates();
    if (!items.some((x) => x.provider)) {
      vscode.window.showErrorMessage("No model backend reachable. Start vLLM or Ollama, set a Claude API key, or install Claude Code.");
      return [];
    }
    const picks = await vscode.window.showQuickPick(items, {
      canPickMany: true,
      placeHolder: "Models to run this prompt on (one chat each, at the same time). They share the workspace: best for questions, reviews and plans.",
    });
    const chosen = (picks || []).filter((p) => p.provider);
    if (!chosen.length) return [];
    const limit = cfg().get("maxParallel", 4);
    const free = limit > 0 ? limit - this.runs.size : chosen.length;
    if (chosen.length > free) {
      vscode.window.showWarningMessage("Only " + Math.max(0, free) + " more chat(s) may run now (localAgentBridge.agent.maxParallel = " + limit + "). Pick fewer models or raise the limit.");
      return [];
    }
    const group = Date.now().toString(36);
    const title = titleFrom(text);
    const sessions = chosen.map((p) => this.createSession({ provider: p.provider, baseUrl: p.baseUrl || "", model: p.model || "", title, group }));
    this.post({ type: "seed", text: "" });
    await this.setActive(sessions[0].id);
    await Promise.all(sessions.map((s) => this.send(text, s.id).catch((e) => this.post({ type: "error", sid: s.id, text: String((e && e.message) || e) }))));
    return sessions;
  }

  /** Every model the panel can reach right now, grouped by backend, for the multi-model pick. */
  async modelCandidates() {
    const c = cfg();
    const sep = (label) => (vscode.QuickPickItemKind ? { label, kind: vscode.QuickPickItemKind.Separator } : null);
    const probes = [{ provider: "vllm" }, { provider: "ollama" }, { provider: "anthropic" }];
    if (c.get("baseUrl", "")) probes.push({ provider: "openai", baseUrl: c.get("baseUrl", "") });
    const key = await this.secret();
    const cur = this.session(this.activeId) || {};
    const results = await Promise.allSettled(
      probes.map((p) =>
        llm
          .discover({ provider: p.provider, baseUrl: p.baseUrl || "", apiKey: c.get("apiKey", ""), anthropicApiKey: key, anthropicWorkspaceId: c.get("claudeWorkspaceId", "") })
          .then((b) => ({ p, b }))
      )
    );
    const items = [];
    for (const res of results) {
      if (res.status !== "fulfilled") continue;
      const { p, b } = res.value;
      this.backends.set(p.provider + "|" + (p.baseUrl || ""), b);
      items.push(sep(b.label + " · " + b.baseUrl));
      for (const m of b.models || []) {
        items.push({
          label: m.id,
          description: [b.label, m.ctx ? Math.round(m.ctx / 1024) + "k ctx" : ""].filter(Boolean).join(" · "),
          picked: cur.provider === p.provider && cur.model === m.id,
          provider: p.provider,
          baseUrl: p.baseUrl || "",
          model: m.id,
        });
      }
    }
    const found = claudeCode.findExecutable(c.get("claudeCodePath", ""));
    if (found.exe) {
      items.push(sep("Claude Code engine"));
      for (const m of claudeCode.MODELS) items.push({ label: "Claude Code · " + (m.id || "default"), description: m.display, provider: "claude-code", model: m.id || "" });
    }
    return items.filter(Boolean);
  }

  /** The progress digest of the chat on screen (each chat has its own). */
  async openProgress() {
    const s = this.active();
    const file = s && this.storeFor(s).progressFile(s.id);
    if (file && fs.existsSync(file)) await vscode.window.showTextDocument(vscode.Uri.file(file), { preview: true });
    else vscode.window.showInformationMessage("No progress index for this chat yet — it is written after its first agent turn.");
  }

  /** Open one of the three index levels: master (all folders), this folder's main index, this chat's sub-index. */
  async openIndexes() {
    const st = this.store();
    st.load();
    const s = this.active();
    const held = Object.values(st.claims || {});
    const items = [
      { label: "Master index", description: "every workspace folder with chats", file: st.masterFile() },
      { label: "Main index of this folder", description: st.list().length + " chats · " + held.length + " file(s) claimed by running chats", file: st.mainFile() },
      { label: "Sub-index of this chat", description: (s.title || "New chat") + " · files it touched, its turns", file: st.subFile(s.id) },
      { label: "Progress of this chat", description: "progress.md", file: st.progressFile(s.id) },
    ];
    const pick = await vscode.window.showQuickPick(items, { placeHolder: "Session indexes (" + st.root + ")" });
    if (!pick) return;
    if (!fs.existsSync(pick.file)) {
      vscode.window.showInformationMessage(pick.label + " is not written yet.");
      return;
    }
    await vscode.window.showTextDocument(vscode.Uri.file(pick.file), { preview: true });
  }

  async pickModel() {
    const providers = [
      { label: "Auto", description: "vLLM if running, else Ollama", id: "auto" },
      { label: "vLLM / SGLang router", description: ":30000 → :8000", id: "vllm" },
      { label: "Ollama", description: ":11434", id: "ollama" },
      { label: "Claude (Anthropic API)", description: "api.anthropic.com · key from Secret Storage, ANTHROPIC_API_KEY or ant auth login", id: "anthropic" },
      { label: "Claude Code (same engine as the Claude app)", description: "the installed claude CLI runs the agent: its tools, skills, CLAUDE.md, MCP, subagents", id: "claude-code" },
      { label: "OpenAI-compatible URL…", description: "LM Studio, llama.cpp, a tunnel, …", id: "openai" },
    ];
    const p = await vscode.window.showQuickPick(providers, { placeHolder: "Model backend for this chat (new chats start on your last pick)" });
    if (!p) return;
    const c = cfg();
    if (p.id === "claude-code") {
      const found = claudeCode.findExecutable(c.get("claudeCodePath", ""));
      if (!found.exe) {
        vscode.window.showErrorMessage("Claude Code CLI not found. Install it from claude.com/claude-code, or set localAgentBridge.agent.claudeCodePath.");
        return;
      }
      const pick = await vscode.window.showQuickPick(
        claudeCode.MODELS.map((x) => ({ label: x.id || "default", description: x.display, id: x.id })),
        { placeHolder: "Model for Claude Code (" + found.exe + ")" }
      );
      if (!pick) return;
      const T = vscode.ConfigurationTarget.Global;
      await c.update("provider", "claude-code", T);
      await c.update("baseUrl", "", T);
      await c.update("model", pick.id, T);
      await this.setSessionModel(this.active(), { provider: "claude-code", baseUrl: "", model: pick.id });
      await this.refreshBackend(true);
      return;
    }
    let baseUrl = "";
    if (p.id === "openai") {
      baseUrl = (await vscode.window.showInputBox({ prompt: "Base URL (ending in /v1)", value: c.get("baseUrl", "") || "http://127.0.0.1:1234/v1", ignoreFocusOut: true })) || "";
      if (!baseUrl) return;
    }
    if (p.id === "anthropic" && !llm.anthropic.credentials({ apiKey: (await this.secret()) || c.get("apiKey", "") })) {
      const ok = await this.setClaudeApiKey();
      if (!ok) return;
    }
    let backend;
    try {
      backend = await llm.discover({ provider: p.id, baseUrl, apiKey: c.get("apiKey", ""), anthropicApiKey: await this.secret(), anthropicWorkspaceId: c.get("claudeWorkspaceId", "") });
    } catch (e) {
      vscode.window.showErrorMessage(String(e.message || e));
      return;
    }
    const m = await vscode.window.showQuickPick(
      backend.models.map((x) => ({
        label: x.id,
        description: [x.display && x.display !== x.id ? x.display : "", x.ctx ? Math.round(x.ctx / 1024) + "k ctx" : ""].filter(Boolean).join(" · "),
        id: x.id,
      })),
      { placeHolder: backend.label + " models at " + backend.baseUrl }
    );
    if (!m) return;
    const G = vscode.ConfigurationTarget.Global;
    await c.update("provider", p.id, G);
    await c.update("baseUrl", p.id === "openai" ? baseUrl : "", G);
    await c.update("model", m.id, G);
    const s = this.active();
    await this.setSessionModel(s, { provider: p.id, baseUrl: p.id === "openai" ? baseUrl : "", model: m.id });
    if (this.runs.has(s.id)) this.post({ type: "status", sid: s.id, text: "Model changed to " + m.id + ": used from this chat's next turn." });
    await this.refreshBackend(true);
  }

  /** Menu / button actions from the panel. */
  async command(id) {
    if (id === "model") await this.pickModel();
    else if (id === "key") await this.setClaudeApiKey();
    else if (id === "effort") await this.pickEffort();
    else if (id === "limits") await this.pickLimits();
    else if (id === "compress") await this.compressChat(this.active(), "");
    else if (id === "steer") await this.steerCommand();
    else if (id === "perms") await this.pickPermissions();
    else if (id === "signin") await this.signIn();
    else if (id === "signout") await this.signOut();
    else if (id === "undo") await this.undoTurn();
    else if (id === "import") await this.importChat();
    else if (id === "progress") await this.openProgress();
    else if (id === "indexes") await this.openIndexes();
    else if (id === "retry") await this.refreshBackend(true);
    else if (id === "settings") await vscode.commands.executeCommand("workbench.action.openSettings", "localAgentBridge");
    else if (id === "mcp") await vscode.commands.executeCommand("workbench.action.openSettings", "localAgentBridge.agent.mcp");
    else if (id === "skills") await vscode.commands.executeCommand("localAgentBridge.showCatalog");
    else if (id === "newIn") await this.newChatInFolder();
    else if (id === "memory") await this.manageMemory();
    else if (id === "memoryAdd") await this.addMemory();
    else if (id === "memoryImport") await this.importMemory();
    else if (id === "memoryExport") await this.exportMemory();
    else if (id === "sync") await vscode.commands.executeCommand("localAgentBridge.sync");
    this.postInfo(id === "signin" || id === "signout");
  }

  /** What the panel's chips, menu and account card show. `account` re-reads the sign-in state. */
  postInfo(account) {
    const c = cfg();
    const provider = this.backend ? this.backend.provider : c.get("provider", "auto");
    const claude = provider === "anthropic" || provider === "claude-code";
    // The chat on screen may run above the settings (its own output limits).
    const s = this.activeId ? this.session(this.activeId) : null;
    const lim = s && this.backend ? sessionLimits.resolve({ limits: s.limits, provider, get: (k, d) => c.get(k, d), modelMaxOut: modelMaxOut(this.backend, this.model), ctxTokens: this.ctxTokens }) : null;
    if (account || !this.account) {
      const found = claudeCode.findExecutable(c.get("claudeCodePath", ""));
      this.account = found.exe ? { cli: true, ...claudeCode.authStatus(found.exe) } : { cli: false, loggedIn: false, email: "", plan: "" };
    }
    this.post({
      type: "info",
      provider,
      shell: c.get("shell", "auto"),
      mode: provider === "claude-code" ? c.get("claudeCodePermissionMode", "acceptEdits") : "",
      effort: claude ? (lim ? lim.effort : c.get("claudeEffort", "default")) : "",
      // Where this chat's effort comes from: the claudeEffort setting, or its own limits (which win).
      effortFrom: claude && lim && lim.effortFrom !== "setting" ? (lim.effortFrom === "preset" ? lim.label : "Custom") : "",
      effortSetting: claude ? c.get("claudeEffort", "default") : "",
      limits: s ? sessionLimits.chipText(s.limits, lim) : "",
      limitsPreset: s ? sessionLimits.normalize(s.limits).preset : "standard",
      model: this.backend ? this.model || "default" : "",
      running: this.runs.size,
      steerDefault: c.get("steerDefault", "steer") === "queue" ? "queue" : "steer",
      account: this.account,
    });
  }

  /** Output limits for one chat (default: the chat on screen). Other chats keep theirs. */
  async pickLimits(sid) {
    const s = sid ? this.session(sid) : this.active();
    if (!s) return;
    const a = cfg();
    const get = (k, d) => a.get(k, d);
    const here = s.id === this.activeId && this.backend;
    const provider = here ? this.backend.provider : s.provider || a.get("provider", "auto");
    const claude = provider === "anthropic" || provider === "claude-code";
    const at = { provider, get, modelMaxOut: here ? modelMaxOut(this.backend, this.model) : 0, ctxTokens: here ? this.ctxTokens : 0 };
    const now = sessionLimits.normalize(s.limits).preset;
    const items = Object.keys(sessionLimits.PRESETS).map((id) => {
      const p = sessionLimits.PRESETS[id];
      let description = p.detail;
      if (id !== "custom") {
        const r = sessionLimits.resolve({ ...at, limits: { preset: id } });
        description = r.maxOutputTokens + " output tokens · " + (provider === "claude-code" ? "" : r.maxRounds + " rounds · ") + (r.effort ? "effort " + r.effort + " · " : "") + p.detail;
      }
      return { label: (id === now ? "$(check) " : "") + p.label, description, id };
    });
    const pick = await vscode.window.showQuickPick(items, { placeHolder: "Output limits for “" + (s.title || "this chat") + "” only (other chats keep theirs)" });
    if (!pick) return;
    let limits = { preset: pick.id };
    if (pick.id === "custom") {
      const cur = sessionLimits.resolve({ ...at, limits: s.limits });
      const whole = (v) => (/^\s*\d*\s*$/.test(String(v)) ? null : "A whole number (0 or empty = the setting)");
      const out = await vscode.window.showInputBox({ prompt: "Max output tokens per reply in this chat (0 = the setting)", value: String(cur.maxOutputTokens), validateInput: whole, ignoreFocusOut: true });
      if (out === undefined) return;
      let rounds = "0";
      if (provider !== "claude-code") {
        rounds = await vscode.window.showInputBox({ prompt: "Max tool rounds per turn in this chat (0 = the setting)", value: String(cur.maxRounds), validateInput: whole, ignoreFocusOut: true });
        if (rounds === undefined) return;
      }
      let effort = "";
      if (claude) {
        const e = await vscode.window.showQuickPick(
          [{ label: "(the claudeEffort setting)", id: "" }, ...sessionLimits.EFFORTS.map((x) => ({ label: (x === cur.effort ? "$(check) " : "") + x, id: x }))],
          { placeHolder: "Claude reasoning effort in this chat" }
        );
        if (!e) return;
        effort = e.id;
      }
      limits = { preset: "custom", maxOutputTokens: Number(out) || 0, maxRounds: Number(rounds) || 0, effort };
    }
    await this.setSessionLimits(s, limits);
  }

  /** Store a chat's limits; a running chat uses them from its next turn. */
  async setSessionLimits(s, limits) {
    if (!s) return;
    s.limits = sessionLimits.normalize(limits);
    this.storeFor(s).update(s.id, { limits: s.limits });
    if (this.runs.has(s.id)) this.post({ type: "status", sid: s.id, text: "Limits changed to " + sessionLimits.PRESETS[s.limits.preset].label + ": used from this chat's next turn." });
    this.postSessions();
    this.postInfo();
  }

  async pickEffort() {
    const c = cfg();
    const now = c.get("claudeEffort", "default");
    const items = [
      { id: "default", description: "the model's own default" },
      { id: "low", description: "fastest and cheapest" },
      { id: "medium", description: "" },
      { id: "high", description: "" },
      { id: "xhigh", description: "hard coding and long tasks" },
      { id: "max", description: "correctness over cost" },
    ].map((x) => ({ label: (x.id === now ? "$(check) " : "") + x.id, description: x.description, id: x.id }));
    const pick = await vscode.window.showQuickPick(items, { placeHolder: "Claude reasoning effort, the setting for chats on Standard limits (Claude backends only)" });
    if (!pick) return;
    await c.update("claudeEffort", pick.id, vscode.ConfigurationTarget.Global);
    // The chat on screen may have its own effort (Extended / Maximum raise it, Custom sets it): say so
    // instead of letting the change look ignored.
    const s = this.active();
    const provider = this.backend ? this.backend.provider : c.get("provider", "auto");
    if (!s || (provider !== "anthropic" && provider !== "claude-code")) return;
    const lim = sessionLimits.resolve({ limits: s.limits, provider, get: (k, d) => (k === "claudeEffort" ? pick.id : c.get(k, d)) });
    if (lim.effortFrom === "setting") return;
    const why = lim.effortFrom === "preset" ? "its " + lim.label + " limits raise effort to at least " + lim.effort : "its Custom limits set effort " + lim.effort;
    const act = await vscode.window.showInformationMessage(
      "Effort setting is now " + pick.id + ", but this chat keeps " + lim.effort + ": " + why + ". The setting applies to chats on Standard limits.",
      "Use " + pick.id + " in this chat",
      "Chat limits…"
    );
    if (act === "Chat limits…") await this.pickLimits(s.id);
    else if (act && act.startsWith("Use ")) {
      const l = sessionLimits.normalize(s.limits);
      const keep = sessionLimits.resolve({ limits: s.limits, provider, get: (k, d) => c.get(k, d) });
      // Custom with the same numbers and this effort: everything else about the chat's limits stays.
      await this.setSessionLimits(s, { preset: "custom", maxOutputTokens: l.preset === "custom" ? l.maxOutputTokens : keep.maxOutputTokens, maxRounds: l.preset === "custom" ? l.maxRounds : keep.maxRounds, effort: pick.id });
    }
  }

  async pickPermissions() {
    const c = cfg();
    const G = vscode.ConfigurationTarget.Global;
    const shell = c.get("shell", "auto");
    const mode = c.get("claudeCodePermissionMode", "acceptEdits");
    const approved = this.context.workspaceState.get(APPROVALS_KEY, []) || [];
    const mark = (on) => (on ? "$(check) " : "");
    const items = [
      { label: "Shell commands", kind: vscode.QuickPickItemKind ? vscode.QuickPickItemKind.Separator : undefined },
      { label: mark(shell === "auto") + "Run commands without asking", description: "destructive ones are always blocked", key: "shell", value: "auto" },
      { label: mark(shell === "confirm") + "Ask before each command", description: "Claude Code engine: denied instead of asked", key: "shell", value: "confirm" },
      { label: mark(shell === "off") + "Never run commands", key: "shell", value: "off" },
      { label: "Claude Code engine", kind: vscode.QuickPickItemKind ? vscode.QuickPickItemKind.Separator : undefined },
      { label: mark(mode === "acceptEdits") + "Apply file edits directly", description: "acceptEdits", key: "claudeCodePermissionMode", value: "acceptEdits" },
      { label: mark(mode === "auto") + "Let Claude Code's classifier decide", description: "auto", key: "claudeCodePermissionMode", value: "auto" },
      { label: mark(mode === "plan") + "Plan only, change nothing", description: "plan", key: "claudeCodePermissionMode", value: "plan" },
      { label: mark(mode === "manual") + "Deny anything that needs approval", description: "manual", key: "claudeCodePermissionMode", value: "manual" },
      { label: "Permission rules", kind: vscode.QuickPickItemKind ? vscode.QuickPickItemKind.Separator : undefined },
      { label: "Edit permission rules…", description: Object.keys(c.get("permissions", []) || {}).length ? "allow / ask / deny per tool and pattern" : "none set; .env reads ask", key: "rules" },
      { label: "Forget “Allow always” answers", description: approved.length + " saved for this workspace", key: "forget" },
    ].filter((x) => x.kind !== undefined || x.key);
    const pick = await vscode.window.showQuickPick(items, { placeHolder: "What the agent may do without asking" });
    if (pick && pick.key === "rules") {
      await vscode.commands.executeCommand("workbench.action.openSettings", "localAgentBridge.agent.permissions");
    } else if (pick && pick.key === "forget") {
      await this.context.workspaceState.update(APPROVALS_KEY, []);
      vscode.window.showInformationMessage("Forgot " + approved.length + " “Allow always” answer(s) for this workspace.");
    } else if (pick && pick.key) {
      await c.update(pick.key, pick.value, G);
      this.postHeader();
    }
  }

  /**
   * Browser sign-in for the Claude Code engine. The official CLI runs the whole flow
   * (`claude auth login`): it opens the browser, and the credentials stay in Claude Code's own
   * store. This extension never sees a password or token; it only polls `claude auth status`.
   */
  async signIn() {
    const c = cfg();
    const found = claudeCode.findExecutable(c.get("claudeCodePath", ""));
    if (!found.exe) {
      const pick = await vscode.window.showErrorMessage("Signing in needs the Claude Code CLI, which was not found.", "Get Claude Code", "Set path");
      if (pick === "Get Claude Code") await vscode.env.openExternal(vscode.Uri.parse("https://claude.com/claude-code"));
      else if (pick === "Set path") await vscode.commands.executeCommand("workbench.action.openSettings", "localAgentBridge.agent.claudeCodePath");
      return false;
    }
    if (claudeCode.authStatus(found.exe).loggedIn) return this.useSignedIn(found.exe, "You are already signed in.");
    if (!vscode.window.createTerminal) {
      vscode.window.showErrorMessage("This CortexIDE build cannot open a terminal. Run `claude auth login` in a terminal yourself.");
      return false;
    }
    const kind = await vscode.window.showQuickPick(
      [
        { label: "Claude account", description: "your Claude subscription (Pro, Max, Team, Enterprise)", args: ["auth", "login", "--claudeai"] },
        { label: "Anthropic Console", description: "API usage billing", args: ["auth", "login", "--console"] },
      ],
      { placeHolder: "Sign in with… (your browser opens; nothing is typed into this panel)" }
    );
    if (!kind) return false;
    if (this.signInTerminal) this.signInTerminal.dispose();
    const term = vscode.window.createTerminal({ name: "Claude sign-in", shellPath: found.exe, shellArgs: kind.args });
    this.signInTerminal = term;
    term.show(false);
    this.post({ type: "status", text: "Sign-in started: finish it in your browser. If the terminal asks for a code, paste it there.", transient: true });
    const ok = await vscode.window.withProgress(
      { location: vscode.ProgressLocation.Notification, title: "Waiting for Claude sign-in in your browser…", cancellable: true },
      async (_p, token) => {
        const until = Date.now() + 5 * 60 * 1000;
        while (Date.now() < until && !token.isCancellationRequested) {
          await new Promise((r) => setTimeout(r, 2000));
          if (claudeCode.authStatus(found.exe).loggedIn) return true;
        }
        return false;
      }
    );
    if (!ok) {
      this.post({ type: "status", text: "Sign-in was not completed." });
      return false;
    }
    try {
      term.dispose();
    } catch {
      /* already closed */
    }
    return this.useSignedIn(found.exe, "Signed in.");
  }

  /** After a successful sign-in: run the panel on the Claude Code engine with that login. */
  async useSignedIn(exe, lead) {
    const c = cfg();
    const G = vscode.ConfigurationTarget.Global;
    await c.update("claudeCodeAuth", "login", G);
    await c.update("provider", "claude-code", G);
    if (/[/:]|^claude-/.test(c.get("model", ""))) await c.update("model", "", G);
    await this.setSessionModel(this.active(), { provider: "claude-code", baseUrl: "", model: c.get("model", "") });
    await this.refreshBackend(true);
    const who = claudeCode.authStatus(exe);
    const msg = lead + " The Agent panel now runs on Claude Code" + (who.email ? " as " + who.email : "") + ".";
    this.post({ type: "status", text: msg });
    vscode.window.showInformationMessage(msg);
    return true;
  }

  async signOut() {
    const c = cfg();
    const found = claudeCode.findExecutable(c.get("claudeCodePath", ""));
    if (!found.exe) return false;
    const pick = await vscode.window.showWarningMessage("Sign out of Claude Code on this computer? This also signs out the claude command in your terminal.", { modal: true }, "Sign out");
    if (pick !== "Sign out") return false;
    spawnSync(found.exe, ["auth", "logout"], { encoding: "utf8", timeout: 20000, windowsHide: true });
    this.backend = null;
    await this.refreshBackend(true);
    this.post({ type: "status", text: "Signed out of Claude Code." });
    return true;
  }

  /** Anthropic API key saved with "Agent: Set Claude API Key" (CortexIDE Secret Storage). */
  async secret() {
    const store = this.context.secrets;
    if (!store) return "";
    try {
      return (await store.get(SECRET_KEY)) || "";
    } catch {
      return "";
    }
  }

  /** Prompt for (or take) an Anthropic API key and keep it in Secret Storage; empty clears it. */
  async setClaudeApiKey(value) {
    if (value === undefined) {
      value = await vscode.window.showInputBox({
        prompt: "Anthropic API key for the Claude backend (kept in CortexIDE Secret Storage; leave empty to clear). Get one at console.anthropic.com/settings/keys, or run 'ant auth login' and leave this empty.",
        password: true,
        ignoreFocusOut: true,
        placeHolder: "sk-ant-…",
      });
      if (value === undefined) return false;
    }
    const store = this.context.secrets;
    if (!store) {
      vscode.window.showErrorMessage("Secret Storage is not available in this CortexIDE build. Set ANTHROPIC_API_KEY in the environment instead.");
      return false;
    }
    const v = String(value || "").trim();
    if (v) await store.store(SECRET_KEY, v);
    else await store.delete(SECRET_KEY);
    this.backend = null;
    this.backends.clear();
    vscode.window.showInformationMessage(v ? "Claude API key saved. Pick Claude under Model in the Agent panel." : "Claude API key cleared.");
    return true;
  }

  async importChat(fileArg) {
    let file = fileArg;
    let resume = "";
    if (!file) {
      const pick = await vscode.window.showQuickPick(
        [
          { label: "$(history) Cursor agent transcript", id: "transcript", description: "~/.cursor/projects/*/agent-transcripts" },
          { label: "$(debug-continue) Claude Code session", id: "claude", description: "~/.claude/projects — resumes it on the Claude Code engine" },
          { label: "$(file) Exported chat file…", id: "file", description: ".md export, .jsonl or .json" },
        ],
        { placeHolder: "Import a chat so the agent can continue it" }
      );
      if (!pick) return;
      if (pick.id === "transcript") {
        const items = listCursorTranscripts().map((t) => ({
          label: firstUserLine(t.file) || path.basename(t.file),
          description: new Date(t.mtime).toLocaleString(),
          detail: t.project,
          file: t.file,
        }));
        if (!items.length) {
          vscode.window.showErrorMessage("No Cursor agent transcripts found.");
          return;
        }
        const t = await vscode.window.showQuickPick(items, { placeHolder: "Cursor agent chats (newest first)", matchOnDetail: true });
        if (!t) return;
        file = t.file;
      } else if (pick.id === "claude") {
        let list = listClaudeCodeSessions(folders()[0]);
        if (!list.length) list = listClaudeCodeSessions("");
        const items = list.map((t) => ({
          label: firstClaudeLine(t.file) || t.sessionId,
          description: new Date(t.mtime).toLocaleString(),
          detail: t.project + " · " + t.sessionId,
          file: t.file,
          sessionId: t.sessionId,
        }));
        if (!items.length) {
          vscode.window.showErrorMessage("No Claude Code sessions found under ~/.claude/projects.");
          return;
        }
        const t = await vscode.window.showQuickPick(items, { placeHolder: "Claude Code sessions (newest first)", matchOnDetail: true });
        if (!t) return;
        file = t.file;
        resume = t.sessionId;
      } else {
        const picked = await vscode.window.showOpenDialog({
          canSelectMany: false,
          filters: { Chats: ["md", "jsonl", "json"] },
          title: "Import chat",
        });
        if (!picked || !picked.length) return;
        file = picked[0].fsPath;
      }
    }
    const turns = parseChatFile(file, fs.readFileSync(file, "utf8"))
      .map((t) => ({ role: t.role === "user" ? "user" : "assistant", content: cleanTurnText(t.text) }))
      .filter((t) => t.content && t.role !== "system");
    if (!turns.length) {
      vscode.window.showErrorMessage("No chat turns found in " + file);
      return;
    }
    const cc = resume && claudeCode.findExecutable(cfg().get("claudeCodePath", "")).exe;
    const firstAsk = turns.find((t) => t.role === "user");
    // A new chat in the history; a Claude Code session continues on that engine with --resume.
    const c = this.createSession({
      title: (resume ? "↪ " : "") + titleFrom(firstAsk ? firstAsk.content : path.basename(file)),
      ...(cc ? { provider: "claude-code", baseUrl: "", model: "", ccSession: resume } : {}),
    });
    c.importedFrom = file;
    c.history = turns.slice(-MAX_HISTORY_TURNS * 2).map((t) => ({ role: t.role, content: t.content.slice(0, 3000) }));
    const userAsks = turns.filter((t) => t.role === "user").map((t) => t.content.replace(/\s+/g, " ").slice(0, 200));
    c.progress = new Progress({
      notes: ["Imported " + turns.length + " turns from " + file, "User requests in that chat:\n" + userAsks.slice(-15).map((u) => "  • " + u).join("\n")],
    }).toJSON();
    c.log.push({ cls: "sys", text: "Imported " + turns.length + " turns from " + file + ". The last " + c.history.length + " are in context; older requests are in the progress index." });
    for (const t of turns.slice(-8)) c.log.push({ cls: t.role === "user" ? "user" : "assistant", text: t.content.slice(0, 1500) });
    if (cc) c.log.push({ cls: "sys", text: "This chat resumes Claude Code session " + resume + " on the Claude Code engine." });
    await this.saveConv(c);
    await this.focus();
    await this.setActive(c.id);
    this.post({ type: "seed", text: "Continue the unfinished work from the imported chat. Check the current state of the files first." });
  }

  async focus() {
    try {
      await vscode.commands.executeCommand("localAgentBridge.agent.focus");
    } catch {
      await vscode.commands.executeCommand("workbench.view.extension.local-agent-bridge");
    }
  }

  async ask(text) {
    await this.focus();
    this.post({ type: "seed", text });
  }

  /** Open the history drawer in the panel. */
  async showHistory() {
    await this.focus();
    this.postSessions();
    this.post({ type: "history", open: true });
  }

  /** Command palette: the panel answers with its composer text as a "multi" message. */
  async runOnModelsFromComposer() {
    await this.focus();
    this.post({ type: "wantMulti" });
  }
}

/** The panel page lives in media/agent-panel.html (markup, styles and script in one file). */
function html(extPath) {
  try {
    const page = fs.readFileSync(path.join(extPath || path.join(__dirname, ".."), "media", "agent-panel.html"), "utf8");
    // The page finds file paths with the same code as the extension (lib/file-ref.js).
    const shared = fs.readFileSync(path.join(__dirname, "file-ref.js"), "utf8").replace(/<\/script/gi, "<\\/script");
    const comp = fs.readFileSync(path.join(__dirname, "composer.js"), "utf8").replace(/<\/script/gi, "<\\/script");
    return page.replace("/*@file-ref*/", () => shared).replace("/*@composer*/", () => comp);
  } catch (e) {
    return "<!DOCTYPE html><html><body><p>Agent panel page is missing: " + String((e && e.message) || e).replace(/[<&]/g, "") + "</p><script>acquireVsCodeApi();</" + "script></body></html>";
  }
}

module.exports = { AgentViewProvider, html, writeHandoff, takeHandoffFor };
