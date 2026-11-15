"use strict";

const vscode = require("vscode");
const fs = require("fs");
const path = require("path");
const os = require("os");
const { spawnSync } = require("child_process");
const llm = require("./llm");
const { runAgent } = require("./agent");
const { ToolContext, defaultRgPath } = require("./agent-tools");
const { Progress } = require("./agent-context");
const { projectChecks, repoMap } = require("./agent-env");
const { parseChatFile } = require("./import-chat");
const claudeCode = require("./claude-code");

const STATE_KEY = "localAgentBridge.agent.conversation";
const SECRET_KEY = "localAgentBridge.anthropicApiKey";
const MAX_LOG = 400;
const MAX_HISTORY_TURNS = 12;
const MAX_CHECKPOINTS = 10;
const BEFORE_SCHEME = "local-agent-before";

function cfg() {
  return vscode.workspace.getConfiguration("localAgentBridge.agent");
}

function folders() {
  return (vscode.workspace.workspaceFolders || []).map((f) => f.uri.fsPath);
}

function emptyConv() {
  return { log: [], history: [], progress: null, importedFrom: "", todos: [] };
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

function editorEnv() {
  const ed = vscode.window.activeTextEditor;
  const roots = folders();
  return {
    roots,
    activeFile: ed ? ed.document.uri.fsPath : "",
    activeLine: ed ? ed.selection.active.line + 1 : 0,
    openFiles: vscode.window.visibleTextEditors.map((e) => e.document.uri.fsPath),
    selection: ed && !ed.selection.isEmpty ? ed.document.getText(ed.selection) : "",
    rules: readRules(roots[0]),
    git: gitSummary(roots[0]),
    checks: projectChecks(roots[0]),
    tree: repoMap(roots[0]),
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

function cleanTurnText(text) {
  return String(text || "")
    .replace(/<(timestamp|available_subagent_types|system_reminder|external_links)>[\s\S]*?<\/\1>/g, "")
    .replace(/<\/?user_query>/g, "")
    .replace(/<uploaded_documents>[\s\S]*?<\/uploaded_documents>/g, "[uploaded documents]")
    .trim();
}

class AgentViewProvider {
  constructor(context, getState) {
    this.context = context;
    this.getState = getState;
    this.views = new Set();
    this.running = null;
    this.backend = null;
    this.model = "";
    this.ctxTokens = 0;
    /** Per-turn file snapshots, newest last: { id, files: [{ path, before, after }] }. Memory only. */
    this.checkpoints = [];
  }

  static register(context, getState) {
    const provider = new AgentViewProvider(context, getState);
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

  conv() {
    const c = this.context.workspaceState.get(STATE_KEY);
    return c && Array.isArray(c.log) ? c : emptyConv();
  }

  async saveConv(c) {
    c.log = (c.log || []).slice(-MAX_LOG);
    c.history = (c.history || []).slice(-MAX_HISTORY_TURNS * 2);
    await this.context.workspaceState.update(STATE_KEY, c);
  }

  resolveWebviewView(view) {
    this.views.add(view);
    view.onDidDispose(() => this.views.delete(view));
    view.webview.options = { enableScripts: true };
    view.webview.html = html(this.context.extensionPath);
    view.webview.onDidReceiveMessage((m) => this.onMessage(m));
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
        const conv = this.conv();
        this.post({ type: "restore", log: conv.log, todos: conv.todos || [] });
        await this.refreshBackend(false);
        this.postInfo(true);
      } else if (m.type === "cmd") await this.command(m.id);
      else if (m.type === "copy") await vscode.env.clipboard.writeText(String(m.text || ""));
      else if (m.type === "send") await this.send(m.text);
      else if (m.type === "stop") this.stop();
      else if (m.type === "new") await this.newChat();
      else if (m.type === "model") await this.pickModel();
      else if (m.type === "import") await this.importChat();
      else if (m.type === "progress") await this.openProgress();
      else if (m.type === "undo") await this.undoTurn(m.id);
      else if (m.type === "diff") await this.showDiff(m.id, m.path);
    } catch (e) {
      this.post({ type: "error", text: String((e && e.message) || e) });
    }
  }

  async refreshBackend(force) {
    if (this.backend && !force) {
      this.postHeader();
      return this.backend;
    }
    const c = cfg();
    if (c.get("provider", "auto") === "claude-code") {
      // The Claude Code engine: the installed CLI runs the whole agent, not the bridge's loop.
      const found = claudeCode.findExecutable(c.get("claudeCodePath", ""));
      const ver = found.exe ? claudeCode.version(found.exe) : "";
      if (!found.exe || !ver) {
        this.backend = null;
        this.post({
          type: "header",
          ok: false,
          text: "No backend · Claude Code CLI " + (found.exe ? "did not answer (" + found.exe + ")" : "not found") + ". Install it from claude.com/claude-code or set localAgentBridge.agent.claudeCodePath.",
        });
        return null;
      }
      this.backend = { provider: "claude-code", label: "Claude Code " + ver, baseUrl: found.exe, exe: found.exe, version: ver, models: claudeCode.MODELS };
      this.model = c.get("model", "");
      if (/[/:]/.test(this.model)) this.model = ""; // a local model id left over from another backend
      this.ctxTokens = 0;
      this.postHeader();
      return this.backend;
    }
    try {
      this.backend = await llm.discover({
        provider: c.get("provider", "auto"),
        baseUrl: c.get("baseUrl", ""),
        apiKey: c.get("apiKey", ""),
        anthropicApiKey: await this.secret(),
        anthropicWorkspaceId: c.get("claudeWorkspaceId", ""),
      });
      this.model = llm.pickModel(this.backend.models, c.get("model", ""), this.backend.provider);
      this.ctxTokens = await llm.contextWindow(this.backend, this.model, {
        override: c.get("contextTokens", 0),
        ollamaNumCtx: c.get("ollamaNumCtx", 16384),
      });
    } catch (e) {
      this.backend = null;
      const lines = String(e.message || e).split("\n").filter(Boolean);
      this.post({ type: "header", ok: false, text: "No backend · " + (lines.length > 1 && c.get("provider", "auto") !== "auto" ? lines[1] : lines[0]) });
      return null;
    }
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

  stop() {
    if (this.running) this.running.abort();
  }

  async send(text) {
    text = String(text || "").trim();
    if (!text) return;
    if (this.running) {
      vscode.window.showWarningMessage("The agent is still working. Stop it first.");
      return;
    }
    // Claim the run before the first await, so a second quick send sees it and is refused.
    const controller = new AbortController();
    this.running = controller;
    // New Chat / Import bump this; a run from an older chat must not save over the new one.
    const gen = this.chatGen || 0;
    let backend;
    try {
      backend = await this.refreshBackend(!this.backend);
    } catch (e) {
      this.running = null;
      throw e;
    }
    if (controller.signal.aborted || gen !== (this.chatGen || 0)) {
      this.running = null;
      this.post({ type: "idle" });
      return;
    }
    if (!backend) {
      this.running = null;
      this.post({ type: "error", text: "No model backend reachable. Start vLLM (:30000 / :8000) or Ollama (:11434), pick Claude under Model (needs an Anthropic API key), or set localAgentBridge.agent.baseUrl." });
      this.post({ type: "idle" });
      return;
    }
    const c = this.conv();
    await this.log(c, "user", text);
    c.todos = []; // each turn plans afresh
    this.post({ type: "busy" });
    this.post({ type: "todos", todos: [] });
    const a = cfg();
    const env = editorEnv();
    const tools = new ToolContext({
      roots: env.roots,
      writableRoots: a.get("writableRoots", []),
      readAnywhere: a.get("readAnywhere", true),
      shellMode: a.get("shell", "auto"),
      shellTimeoutSec: a.get("shellTimeoutSec", 120),
      rgPath: defaultRgPath(vscode.env.appRoot),
      skills: () => this.getState().skills || [],
      requireRead: a.get("requireReadBeforeEdit", true),
      diagnosticsAfterEdit: a.get("diagnosticsAfterEdit", true),
      signal: controller.signal,
      confirmShell: async (command, cwd) => {
        const pick = await vscode.window.showWarningMessage("Agent wants to run in " + cwd + ":\n\n" + command, { modal: true }, "Run");
        return pick === "Run";
      },
    });
    const onEvent = (ev) => {
      if (ev.type === "tool" && ev.status === "done") {
        c.log.push({ cls: "tool", name: ev.name, label: ev.label, ok: ev.ok, text: String(ev.result || "").slice(0, 2000) });
      } else if (ev.type === "thought") c.log.push({ cls: "thought", text: ev.text });
      else if (ev.type === "status" && !ev.transient) c.log.push({ cls: "sys", text: ev.text });
      else if (ev.type === "assistant") c.log.push({ cls: "assistant", text: ev.text });
      else if (ev.type === "todos") c.todos = ev.todos;
      this.post(ev);
    };
    try {
      const result = backend.provider === "claude-code" ? await this.runClaudeCode({ backend, text, c, env, tools, signal: controller.signal, onEvent }) : await runAgent({
        backend,
        model: this.model,
        contextTokens: this.ctxTokens,
        maxOutputTokens: backend.provider === "anthropic" ? a.get("claudeMaxOutputTokens", 16000) : a.get("maxOutputTokens", 2048),
        effort: backend.provider === "anthropic" ? a.get("claudeEffort", "default") : "",
        maxRounds: a.get("maxRounds", 30),
        temperature: a.get("temperature", 0.2),
        allowTask: a.get("subagents", true),
        prompt: text,
        history: c.history,
        prior: c.progress,
        tools,
        env,
        skills: this.getState().skills || [],
        signal: controller.signal,
        onEvent,
      });
      c.history.push({ role: "user", content: text }, { role: "assistant", content: result.text });
      if (result.sessionId) c.ccSession = result.sessionId; // Claude Code keeps the conversation itself
      if (result.progress) {
        c.progress = result.progress;
        const file = new Progress(result.progress).persist(env.roots[0]);
        if (file) this.post({ type: "status", text: "Progress index: " + file });
      }
    } catch (e) {
      const msg = String((e && e.message) || e);
      c.log.push({ cls: msg === "stopped" ? "sys" : "err", text: msg === "stopped" ? "Stopped." : msg });
      this.post({ type: msg === "stopped" ? "status" : "error", text: msg === "stopped" ? "Stopped." : msg });
      if (msg !== "stopped") this.backend = null;
    } finally {
      // Even a stopped or failed turn keeps its snapshot, so its partial edits can be undone.
      const card = this.recordCheckpoint(tools);
      if (card) {
        c.log.push(card);
        this.post({ type: "changes", ...card });
      }
      if (this.running === controller) this.running = null;
      // After New Chat (or an import) during this run, c is the old conversation: saving it
      // would bring the cleared history back.
      if (gen === (this.chatGen || 0)) await this.saveConv(c);
      this.post({ type: "idle" });
    }
  }

  /** One turn through the installed Claude Code CLI (provider "claude-code"). */
  async runClaudeCode({ backend, text, c, env, tools, signal, onEvent }) {
    const a = cfg();
    const auth = a.get("claudeCodeAuth", "auto");
    const saved = (await this.secret()) || (/^sk-ant-/i.test(a.get("apiKey", "")) ? a.get("apiKey", "") : "");
    const cred = auth === "login" ? null : llm.anthropic.credentials({ apiKey: saved, workspaceId: a.get("claudeWorkspaceId", ""), useCli: false });
    if (auth === "apiKey" && !cred) throw new Error("claudeCodeAuth is apiKey but no Anthropic key is set. Run “Agent: Set Claude API Key”, or switch claudeCodeAuth to login.");
    const ctx = [];
    if (env.activeFile) ctx.push("Active file in the editor: " + env.activeFile + (env.activeLine ? " (cursor at line " + env.activeLine + ")" : ""));
    if (env.selection) ctx.push("Selected text:\n```\n" + String(env.selection).slice(0, 4000) + "\n```");
    const prompt = ctx.length ? text + "\n\n<editor-context>\n" + ctx.join("\n") + "\n</editor-context>" : text;
    const turn = (resume) =>
      claudeCode.run({
        exe: backend.exe,
        cwd: env.roots[0] || os.homedir(),
        prompt,
        env: claudeCode.buildEnv({ cred, auth }),
        args: claudeCode.buildArgs({
          model: this.model,
          permissionMode: a.get("claudeCodePermissionMode", "acceptEdits"),
          effort: a.get("claudeEffort", "default"),
          resume,
          shell: a.get("shell", "auto"),
          addDirs: [...env.roots.slice(1), ...(a.get("writableRoots", []) || [])],
        }),
        signal,
        onEvent,
        // For the changed-files card and Undo: keep what a file looked like when Claude Code read
        // it (it reads before it edits), and use that as the "before" once an edit is announced.
        // Reading at announce time is only the fallback: the write may already have landed.
        onRead: (p) => {
          if (!seen.has(p)) seen.set(p, readNow(p));
        },
        onEdit: (p) => {
          if (tools.checkpoint && !tools.checkpoint.has(p)) tools.checkpoint.set(p, { before: seen.has(p) ? seen.get(p) : readNow(p) });
        },
      });
    if (!this.ccSeen) this.ccSeen = new Map();
    const seen = this.ccSeen;
    const settle = () => {
      // Next turn's "before" is this turn's result.
      for (const p of tools.checkpoint ? tools.checkpoint.keys() : []) seen.set(p, readNow(p));
      if (seen.size > 400) this.ccSeen = new Map();
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

  /** Snapshot what this turn changed; returns the log card for it, or null if nothing changed. */
  recordCheckpoint(tools) {
    if (!tools || !tools.checkpoint || !tools.checkpoint.size) return null;
    const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    const files = [];
    for (const [p, { before }] of tools.checkpoint) {
      const after = readNow(p);
      if (after === before) continue; // edited and changed back
      files.push({ path: p, before, after });
    }
    if (!files.length) return null;
    this.checkpoints.push({ id, files });
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

  /** Put back every file the given turn (default: the latest) changed. */
  async undoTurn(id) {
    const cp = id ? this.checkpoints.find((x) => x.id === id) : this.checkpoints[this.checkpoints.length - 1];
    if (!cp) {
      vscode.window.showInformationMessage("Nothing to undo. Snapshots of agent edits last until CortexIDE restarts.");
      return false;
    }
    if (this.running) {
      vscode.window.showWarningMessage("Stop the agent before undoing its edits.");
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
    const c = this.conv();
    const card = c.log.find((r) => r.cls === "changes" && r.id === cp.id);
    if (card) card.undone = true;
    c.log.push({ cls: "sys", text: msg });
    c.history.push({ role: "user", content: "(I reverted your changes to " + names + ".)" }, { role: "assistant", content: "Understood — those files are back to how they were before that turn." });
    await this.saveConv(c);
    this.post({ type: "status", text: msg });
    this.post({ type: "undone", id: cp.id });
    return !failed.length;
  }

  async newChat() {
    this.chatGen = (this.chatGen || 0) + 1;
    this.stop();
    await this.saveConv(emptyConv());
    this.post({ type: "restore", log: [], todos: [] });
  }

  async openProgress() {
    const root = folders()[0];
    const file = root && path.join(root, ".cortexide", "agent", "progress.md");
    if (file && fs.existsSync(file)) await vscode.window.showTextDocument(vscode.Uri.file(file), { preview: true });
    else vscode.window.showInformationMessage("No progress index yet — it is written after the first agent turn.");
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
    const p = await vscode.window.showQuickPick(providers, { placeHolder: "Model backend for the CortexIDE Agent" });
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
    await this.refreshBackend(true);
  }

  /** Menu / button actions from the panel. */
  async command(id) {
    if (id === "model") await this.pickModel();
    else if (id === "key") await this.setClaudeApiKey();
    else if (id === "effort") await this.pickEffort();
    else if (id === "perms") await this.pickPermissions();
    else if (id === "signin") await this.signIn();
    else if (id === "signout") await this.signOut();
    else if (id === "undo") await this.undoTurn();
    else if (id === "import") await this.importChat();
    else if (id === "progress") await this.openProgress();
    else if (id === "retry") await this.refreshBackend(true);
    else if (id === "settings") await vscode.commands.executeCommand("workbench.action.openSettings", "localAgentBridge");
    else if (id === "skills") await vscode.commands.executeCommand("localAgentBridge.showCatalog");
    else if (id === "sync") await vscode.commands.executeCommand("localAgentBridge.sync");
    this.postInfo(id === "signin" || id === "signout");
  }

  /** What the panel's chips, menu and account card show. `account` re-reads the sign-in state. */
  postInfo(account) {
    const c = cfg();
    const provider = this.backend ? this.backend.provider : c.get("provider", "auto");
    const claude = provider === "anthropic" || provider === "claude-code";
    if (account || !this.account) {
      const found = claudeCode.findExecutable(c.get("claudeCodePath", ""));
      this.account = found.exe ? { cli: true, ...claudeCode.authStatus(found.exe) } : { cli: false, loggedIn: false, email: "", plan: "" };
    }
    this.post({
      type: "info",
      provider,
      shell: c.get("shell", "auto"),
      mode: provider === "claude-code" ? c.get("claudeCodePermissionMode", "acceptEdits") : "",
      effort: claude ? c.get("claudeEffort", "default") : "",
      account: this.account,
    });
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
    const pick = await vscode.window.showQuickPick(items, { placeHolder: "Claude reasoning effort (Claude backends only)" });
    if (pick) await c.update("claudeEffort", pick.id, vscode.ConfigurationTarget.Global);
  }

  async pickPermissions() {
    const c = cfg();
    const G = vscode.ConfigurationTarget.Global;
    const shell = c.get("shell", "auto");
    const mode = c.get("claudeCodePermissionMode", "acceptEdits");
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
    ].filter((x) => x.kind !== undefined || x.key);
    const pick = await vscode.window.showQuickPick(items, { placeHolder: "What the agent may do without asking" });
    if (pick && pick.key) {
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
    vscode.window.showInformationMessage(v ? "Claude API key saved. Pick Claude under Model in the Agent panel." : "Claude API key cleared.");
    return true;
  }

  async importChat(fileArg) {
    let file = fileArg;
    if (!file) {
      const pick = await vscode.window.showQuickPick(
        [
          { label: "$(history) Cursor agent transcript", id: "transcript", description: "~/.cursor/projects/*/agent-transcripts" },
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
    const c = emptyConv();
    c.importedFrom = file;
    c.history = turns.slice(-MAX_HISTORY_TURNS * 2).map((t) => ({ role: t.role, content: t.content.slice(0, 3000) }));
    const userAsks = turns.filter((t) => t.role === "user").map((t) => t.content.replace(/\s+/g, " ").slice(0, 200));
    c.progress = new Progress({
      notes: ["Imported " + turns.length + " turns from " + file, "User requests in that chat:\n" + userAsks.slice(-15).map((u) => "  • " + u).join("\n")],
    }).toJSON();
    c.log.push({ cls: "sys", text: "Imported " + turns.length + " turns from " + file + ". The last " + c.history.length + " are in context; older requests are in the progress index." });
    for (const t of turns.slice(-8)) c.log.push({ cls: t.role === "user" ? "user" : "assistant", text: t.content.slice(0, 1500) });
    this.chatGen = (this.chatGen || 0) + 1;
    this.stop();
    await this.saveConv(c);
    await this.focus();
    this.post({ type: "restore", log: c.log, todos: [] });
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
}

/** The panel page lives in media/agent-panel.html (markup, styles and script in one file). */
function html(extPath) {
  try {
    return fs.readFileSync(path.join(extPath || path.join(__dirname, ".."), "media", "agent-panel.html"), "utf8");
  } catch (e) {
    return "<!DOCTYPE html><html><body><p>Agent panel page is missing: " + String((e && e.message) || e).replace(/[<&]/g, "") + "</p><script>acquireVsCodeApi();</" + "script></body></html>";
  }
}

module.exports = { AgentViewProvider };
