"use strict";

// "Claude Code" engine: instead of the bridge's own agent loop, drive the installed Claude Code
// CLI — the same runtime the Claude desktop app and terminal client use — in headless mode
// (`claude -p --output-format stream-json --input-format stream-json`) and translate its event
// stream into the panel's events. Claude Code brings its own tools, system prompt, context
// management, CLAUDE.md handling, skills, MCP servers and subagents.
//
// No dependency: the CLI is spawned directly, like the other backends speak raw HTTP.

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn, spawnSync } = require("child_process");
const { steerMessage } = require("./steer");

const MODELS = [
  { id: "", display: "Claude Code's default model" },
  { id: "opus", display: "latest Opus" },
  { id: "sonnet", display: "latest Sonnet" },
  { id: "haiku", display: "latest Haiku" },
  { id: "fable", display: "latest Fable" },
];
const PERMISSION_MODES = ["acceptEdits", "auto", "plan", "manual"];
const EFFORTS = ["low", "medium", "high", "xhigh", "max"];
const EDIT_TOOLS = new Set(["Edit", "Write", "MultiEdit", "NotebookEdit"]);

/** Locate the Claude Code CLI: explicit setting, then PATH, then the native installer's folder. */
function findExecutable(setting, env = process.env) {
  const tried = [];
  const ok = (p) => {
    if (!p) return false;
    tried.push(p);
    try {
      return fs.statSync(p).isFile();
    } catch {
      return false;
    }
  };
  const explicit = String(setting || "").trim().replace(/^"|"$/g, "");
  if (explicit) return ok(explicit) ? { exe: explicit, tried } : { exe: "", tried };
  const win = process.platform === "win32";
  const names = win ? ["claude.exe", "claude.cmd"] : ["claude"];
  for (const dir of String(env.PATH || env.Path || "").split(path.delimiter)) {
    if (!dir) continue;
    for (const n of names) {
      const p = path.join(dir, n);
      if (ok(p)) return { exe: p, tried };
    }
  }
  const home = env.USERPROFILE || env.HOME || os.homedir();
  for (const n of names) {
    const p = path.join(home, ".local", "bin", n);
    if (ok(p)) return { exe: p, tried };
  }
  return { exe: "", tried };
}

/** `claude --version` → "2.1.301", or "" when the binary does not answer. */
function version(exe) {
  try {
    const r = spawnSync(exe, ["--version"], { encoding: "utf8", timeout: 15000, windowsHide: true, shell: /\.cmd$/i.test(exe) });
    const m = String(r.stdout || "").match(/\d+\.\d+\.\d+/);
    return m ? m[0] : "";
  } catch {
    return "";
  }
}

/**
 * Claude Code's own sign-in state (`claude auth status`), ignoring API keys in the environment.
 * @returns {{loggedIn:boolean, method:string, email:string, plan:string}}
 */
function authStatus(exe) {
  const out = { loggedIn: false, method: "none", email: "", plan: "" };
  try {
    const env = { ...process.env };
    delete env.ANTHROPIC_API_KEY;
    delete env.ANTHROPIC_AUTH_TOKEN;
    const r = spawnSync(exe, ["auth", "status"], { encoding: "utf8", timeout: 15000, windowsHide: true, env, shell: /\.cmd$/i.test(exe) });
    const j = JSON.parse(String(r.stdout || "").slice(String(r.stdout || "").indexOf("{")));
    out.loggedIn = !!j.loggedIn;
    out.method = String(j.authMethod || "none");
    out.email = String(j.email || j.emailAddress || "");
    out.plan = String(j.subscriptionType || j.orgName || "");
  } catch {
    /* not installed, or no JSON: treated as signed out */
  }
  return out;
}

/**
 * Environment for the CLI.
 * auth "login": drop API credentials so Claude Code uses its own login (claude.ai subscription).
 * auth "apiKey" / "auto": pass the bridge's Anthropic credential when there is one; a workspace id
 * rides along as an extra request header (user-scoped keys need it).
 * maxOutputTokens > 0: a chat raised above its standard limits sets CLAUDE_CODE_MAX_OUTPUT_TOKENS.
 */
function buildEnv({ base = process.env, cred = null, auth = "auto", maxOutputTokens = 0 } = {}) {
  const env = { ...base };
  if (maxOutputTokens > 0) env.CLAUDE_CODE_MAX_OUTPUT_TOKENS = String(Math.floor(maxOutputTokens));
  if (auth === "login") {
    delete env.ANTHROPIC_API_KEY;
    delete env.ANTHROPIC_AUTH_TOKEN;
    return env;
  }
  if (cred && cred.token) {
    delete env.ANTHROPIC_API_KEY;
    delete env.ANTHROPIC_AUTH_TOKEN;
    if (cred.kind === "bearer") env.ANTHROPIC_AUTH_TOKEN = cred.token;
    else env.ANTHROPIC_API_KEY = cred.token;
    if (cred.workspaceId) {
      const extra = "anthropic-workspace-id: " + cred.workspaceId;
      const have = String(env.ANTHROPIC_CUSTOM_HEADERS || "");
      if (!/anthropic-workspace-id\s*:/i.test(have)) env.ANTHROPIC_CUSTOM_HEADERS = have ? have + "\n" + extra : extra;
    }
  }
  return env;
}

/**
 * CLI arguments for one headless turn.
 * shell: the bridge's shell setting. "auto" pre-approves the command tools, "off" removes them,
 * "confirm" leaves them to the permission mode (headless: a call that would prompt is denied).
 */
function buildArgs({ model = "", permissionMode = "acceptEdits", effort = "", resume = "", shell = "auto", addDirs = [], appendSystemPrompt = "" } = {}) {
  const args = ["-p", "--output-format", "stream-json", "--input-format", "stream-json", "--verbose", "--include-partial-messages", "--permission-prompts", "none"];
  args.push("--permission-mode", PERMISSION_MODES.includes(permissionMode) ? permissionMode : "acceptEdits");
  if (model) args.push("--model", model);
  if (EFFORTS.includes(effort)) args.push("--effort", effort);
  if (resume) args.push("--resume", resume);
  if (shell === "auto") args.push("--allowedTools", "Bash", "PowerShell");
  else if (shell === "off") args.push("--disallowedTools", "Bash", "PowerShell");
  for (const d of addDirs || []) if (d) args.push("--add-dir", d);
  if (appendSystemPrompt) args.push("--append-system-prompt", appendSystemPrompt);
  return args;
}

function toolLabel(input) {
  const a = input || {};
  return String(a.file_path || a.path || a.notebook_path || a.pattern || a.command || a.url || a.query || a.description || a.skill || "");
}

function resultText(content) {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) return content.map((b) => (b && b.type === "text" ? b.text || "" : b && b.type ? "[" + b.type + "]" : "")).join("\n");
  return content == null ? "" : JSON.stringify(content);
}

/**
 * Turns Claude Code's stream-json messages into the panel's events
 * ({type:"thought"|"tool"|"todos"|"status"|...}). Pure: feed it parsed lines.
 */
class Translator {
  constructor({ emit, cwd = "", onEdit, onRead } = {}) {
    this.emit = emit || (() => {});
    this.cwd = cwd;
    this.onEdit = onEdit;
    this.onRead = onRead;
    this.sessionId = "";
    this.model = "";
    this.version = "";
    this.calls = new Map(); // tool_use id → { name, label }
    this.pendingText = ""; // assistant text not yet known to be the final answer
    this.streamed = 0;
    this.shown = 0;
    this.result = null;
    this.toolsUsed = 0;
    this.apiError = "";
  }

  flushText() {
    if (this.pendingText.trim()) this.emit({ type: "thought", text: this.pendingText.trim() });
    this.pendingText = "";
  }

  feed(m) {
    if (!m || typeof m !== "object") return;
    if (m.session_id && !this.sessionId) this.sessionId = m.session_id;
    if (m.type === "system") return this.system(m);
    if (m.type === "stream_event") return this.partial(m);
    if (m.parent_tool_use_id) return; // a subagent's inner traffic; its Task call is shown instead
    if (m.type === "assistant") return this.assistant(m);
    if (m.type === "user") return this.user(m);
    if (m.type === "result") {
      // A steering message Claude Code ran as a turn of its own ends with a second result: the
      // earlier answer is kept as a note, the last one is the turn's answer.
      if (this.result && this.result.result) this.emit({ type: "thought", text: String(this.result.result) });
      this.result = m;
    }
  }

  system(m) {
    if (m.subtype === "init") {
      this.model = m.model || "";
      this.version = m.claude_code_version || "";
      this.emit({ type: "status", text: "Claude Code " + this.version + " · " + this.model + " · session " + String(m.session_id || "").slice(0, 8), transient: true });
    } else if (m.subtype === "api_retry") {
      this.emit({ type: "status", text: "API retry" + (m.attempt ? " " + m.attempt : "") + "…", transient: true });
    } else if (m.subtype === "permission_denied") {
      this.emit({ type: "status", text: "Permission denied: " + (m.tool_name || m.tool || "tool") + (m.message ? " — " + m.message : "") });
    } else if (m.subtype === "compact_boundary") {
      this.emit({ type: "status", text: "Claude Code compacted the conversation" });
    }
  }

  partial(m) {
    const ev = m.event || {};
    const d = ev.delta || {};
    if (m.parent_tool_use_id || ev.type !== "content_block_delta" || d.type !== "text_delta") return;
    this.streamed += String(d.text || "").length;
    if (this.streamed - this.shown >= 300) {
      this.shown = this.streamed;
      this.emit({ type: "status", text: "Writing… " + this.streamed + " chars", transient: true });
    }
  }

  assistant(m) {
    const msg = m.message || {};
    const blocks = Array.isArray(msg.content) ? msg.content : [];
    if (m.error || m.is_api_error_message) this.apiError = blocks.map((b) => b.text || "").join(" ").trim() || String(m.error);
    const text = blocks.filter((b) => b.type === "text").map((b) => b.text || "").join("\n");
    const uses = blocks.filter((b) => b.type === "tool_use");
    if (text.trim()) {
      this.flushText(); // an earlier text turned out not to be the last one
      this.pendingText = text;
    }
    if (!uses.length) return;
    this.flushText();
    for (const u of uses) {
      const label = toolLabel(u.input);
      this.calls.set(u.id, { name: u.name, label });
      if (u.name === "TodoWrite" && u.input && Array.isArray(u.input.todos)) {
        this.emit({ type: "todos", todos: u.input.todos.map((t) => ({ content: String(t.content || t.activeForm || ""), status: t.status || "pending" })) });
      }
      const p = (u.input && (u.input.file_path || u.input.notebook_path || u.input.path)) || "";
      const abs = p ? (path.isAbsolute(p) ? p : path.resolve(this.cwd || ".", p)) : "";
      // Claude Code reads a file before it edits it, so the Read is the safe moment to snapshot;
      // by the time an edit is announced the write may already have happened.
      if (abs && u.name === "Read" && this.onRead) this.onRead(abs);
      if (abs && EDIT_TOOLS.has(u.name) && this.onEdit) this.onEdit(abs);
      this.emit({ type: "tool", name: u.name, label, status: "start" });
    }
  }

  user(m) {
    const content = m.message && m.message.content;
    if (!Array.isArray(content)) return;
    for (const b of content) {
      if (!b || b.type !== "tool_result") continue;
      const call = this.calls.get(b.tool_use_id) || { name: "tool", label: "" };
      this.calls.delete(b.tool_use_id);
      this.toolsUsed++;
      this.emit({ type: "tool", name: call.name, label: call.label, status: "done", ok: !b.is_error, result: resultText(b.content).slice(0, 4000) });
    }
  }

  /** After the stream ended: the final answer, or throws with Claude Code's own error text. */
  finish({ exitCode = 0, stderr = "" } = {}) {
    const r = this.result;
    if (!r) {
      const why = this.apiError || String(stderr || "").trim().split(/\r?\n/).slice(-3).join(" ") || "no result (exit " + exitCode + ")";
      throw new Error("Claude Code: " + why);
    }
    const text = String(r.result || (Array.isArray(r.errors) ? r.errors.join("; ") : "") || this.pendingText || "");
    if (r.is_error || (r.subtype && r.subtype !== "success")) {
      let msg = text || r.subtype || "failed";
      if (/not logged in|\/login/i.test(msg)) msg += " — run `claude` in a terminal and use /login, or give the bridge an Anthropic API key and set claudeCodeAuth to apiKey.";
      else if (/credit balance/i.test(msg)) msg += " — the API key's organisation has no usable credit for Claude Code. Add credit, or log the CLI in (`claude`, then /login) and set claudeCodeAuth to login.";
      else if (r.subtype === "error_max_turns") msg = "Claude Code stopped at its turn limit. " + msg;
      throw new Error("Claude Code: " + msg);
    }
    const u = r.usage || {};
    const input = (u.input_tokens || 0) + (u.cache_read_input_tokens || 0) + (u.cache_creation_input_tokens || 0);
    const cost = typeof r.total_cost_usd === "number" ? " · $" + r.total_cost_usd.toFixed(4) : "";
    this.emit({
      type: "status",
      text: "Claude Code: " + (r.num_turns || 0) + " turns · " + input.toLocaleString() + " input tokens (" + (u.cache_read_input_tokens || 0).toLocaleString() + " from cache) · " + (u.output_tokens || 0).toLocaleString() + " output" + cost,
    });
    const denials = Array.isArray(r.permission_denials) ? r.permission_denials.length : 0;
    if (denials) this.emit({ type: "status", text: denials + " tool call(s) were denied by the permission mode (localAgentBridge.agent.claudeCodePermissionMode / shell)" });
    return { text: text || "Done.", sessionId: r.session_id || this.sessionId, costUsd: r.total_cost_usd || 0, toolsUsed: this.toolsUsed };
  }
}

/**
 * Run one turn through Claude Code.
 * @param {object} o
 * @param {string} o.exe            path to the CLI
 * @param {string[]} [o.exeArgs]    arguments placed before the CLI's own (tests run a script with node)
 * @param {string} o.cwd            workspace folder
 * @param {string} o.prompt
 * @param {object} [o.env]          from buildEnv()
 * @param {string[]} [o.args]       from buildArgs()
 * @param {(ev:object)=>void} [o.onEvent]
 * @param {(file:string)=>void} [o.onRead]  absolute path, when Claude Code reads a file (snapshot it here)
 * @param {(file:string)=>void} [o.onEdit]  absolute path, when an edit tool call is announced
 * @param {{take:()=>{text:string,from?:string}[], onPush:(fn:Function)=>Function}} [o.steer]
 *   messages the user sends while the turn runs: written to Claude Code's input while it is open
 * @param {AbortSignal} [o.signal]
 * @returns {Promise<{text:string, sessionId:string, costUsd:number, toolsUsed:number, steered:object[]}>}
 */
function run(o) {
  return new Promise((resolve, reject) => {
    const emit = (ev) => o.onEvent && o.onEvent(ev);
    const tr = new Translator({ emit, cwd: o.cwd, onEdit: o.onEdit, onRead: o.onRead });
    let child;
    try {
      child = spawn(o.exe, [...(o.exeArgs || []), ...(o.args || buildArgs())], { cwd: o.cwd || undefined, env: o.env || process.env, windowsHide: true, shell: /\.cmd$/i.test(o.exe) });
    } catch (e) {
      return reject(new Error("Could not start Claude Code (" + o.exe + "): " + (e.message || e)));
    }
    let stderr = "";
    let buf = "";
    let stopped = false;
    let settled = false;
    let inputOpen = true; // Claude Code still reads user messages from stdin
    const steered = [];
    let unsub = null;
    const done = (fn, v) => {
      if (settled) return;
      settled = true;
      if (o.signal) o.signal.removeEventListener("abort", onAbort);
      if (unsub) unsub();
      if (v && typeof v === "object" && !(v instanceof Error)) v.steered = steered;
      fn(v);
    };
    const userLine = (text) => JSON.stringify({ type: "user", message: { role: "user", content: [{ type: "text", text: String(text || "") }] }, parent_tool_use_id: null }) + "\n";
    /** Pass waiting steering messages to Claude Code; after its input closed they stay queued for the next turn. */
    const pump = () => {
      if (!inputOpen || !o.steer || settled) return;
      const items = (o.steer.take() || []).filter((i) => i && String(i.text || "").trim());
      if (!items.length) return;
      try {
        child.stdin.write(userLine(steerMessage(items)));
      } catch {
        return;
      }
      for (const i of items) {
        steered.push({ text: i.text, from: i.from || "" });
        emit({ type: "steered", text: i.text, from: i.from || "" });
      }
      emit({ type: "status", text: "Steered: passed " + (items.length > 1 ? items.length + " new messages" : "your new message") + " to Claude Code" });
    };
    const onAbort = () => {
      stopped = true;
      try {
        child.kill();
      } catch {
        /* already gone */
      }
    };
    if (o.signal) {
      if (o.signal.aborted) onAbort();
      else o.signal.addEventListener("abort", onAbort, { once: true });
    }
    const line = (l) => {
      const s = l.trim();
      if (!s) return;
      let m;
      try {
        m = JSON.parse(s);
      } catch {
        return; // not a protocol line
      }
      try {
        tr.feed(m);
      } catch (e) {
        emit({ type: "status", text: "Claude Code event ignored: " + (e.message || e) });
      }
      if (m.type === "result") {
        inputOpen = false;
        try {
          child.stdin.end(); // one turn per process; the session id carries the conversation
        } catch {
          /* closed */
        }
      }
    };
    child.stdout.setEncoding("utf8");
    child.stdout.on("data", (d) => {
      buf += d;
      let at;
      while ((at = buf.indexOf("\n")) >= 0) {
        line(buf.slice(0, at));
        buf = buf.slice(at + 1);
      }
    });
    child.stderr.setEncoding("utf8");
    child.stderr.on("data", (d) => (stderr = (stderr + d).slice(-4000)));
    child.on("error", (e) => done(reject, new Error("Could not start Claude Code (" + o.exe + "): " + (e.message || e))));
    child.on("close", (code) => {
      if (buf) line(buf);
      if (stopped) return done(reject, new Error("stopped"));
      try {
        done(resolve, tr.finish({ exitCode: code, stderr }));
      } catch (e) {
        done(reject, e);
      }
    });
    child.stdin.on("error", () => {});
    child.stdin.write(userLine(o.prompt));
    if (o.steer) {
      unsub = o.steer.onPush(() => setImmediate(pump));
      pump();
    }
  });
}

module.exports = { MODELS, PERMISSION_MODES, findExecutable, version, authStatus, buildEnv, buildArgs, Translator, run, toolLabel };
