"use strict";

// MCP client: lets the agent use tools from Model Context Protocol servers (stdio transport,
// newline-delimited JSON-RPC 2.0). Servers start on first use and are shared by every chat.
//
// The model does not get each server's tools as its own tool definitions (REA alone has ~140 tools
// and ~2 MB of schemas, more than a local model's whole context). It gets McpTools (list / search /
// show one schema) and McpCall (run one tool) instead; see agent-tools.js.

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");

const PROTOCOL = "2025-06-18";
const INIT_TIMEOUT_MS = 60000;
const MAX_LINE = 64 * 1024 * 1024;

/** Quote one argument for cmd.exe (used only when the command has to go through a shell, e.g. npx.cmd). */
function winQuote(a) {
  const s = String(a);
  return /[\s"&|<>^()%!]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}

/** Windows cannot spawn npx / npm / uvx (.cmd shims) without a shell; node and .exe paths can. */
function needsShell(command) {
  if (process.platform !== "win32") return false;
  const ext = path.extname(command).toLowerCase();
  if (ext === ".exe" || ext === ".com") return false;
  if (ext === ".cmd" || ext === ".bat") return true;
  return !/^(node|python|python3|py|dotnet|java|uv)$/i.test(path.basename(command));
}

class McpServer {
  /**
   * @param {string} name
   * @param {{command:string,args?:string[],env?:object,cwd?:string}} spec
   * @param {{roots?:string[], log?:(s:string)=>void, timeoutMs?:number}} [o]
   */
  constructor(name, spec, o = {}) {
    this.name = name;
    this.spec = spec;
    this.roots = o.roots || [];
    this.log = o.log || (() => {});
    this.timeoutMs = o.timeoutMs || 120000;
    this.proc = null;
    this.ready = null;
    this.nextId = 1;
    this.pending = new Map();
    this.buf = "";
    this.stderr = "";
    this.tools = null;
    this.info = null;
    this.instructions = "";
  }

  start() {
    if (this.ready) return this.ready;
    this.ready = new Promise((resolve, reject) => {
      const { command, args = [], env = {}, cwd } = this.spec;
      const shell = needsShell(command);
      const opts = {
        cwd: cwd || this.roots[0] || os.homedir(),
        env: { ...process.env, ...env },
        stdio: ["pipe", "pipe", "pipe"],
        windowsHide: true,
      };
      let p;
      try {
        p = shell ? spawn([command, ...args].map(winQuote).join(" "), { ...opts, shell: true }) : spawn(command, args, opts);
      } catch (e) {
        reject(new Error("could not start MCP server " + this.name + ": " + (e.message || e)));
        return;
      }
      this.proc = p;
      p.stdout.setEncoding("utf8");
      p.stdout.on("data", (d) => this._onData(d));
      p.stderr.setEncoding("utf8");
      p.stderr.on("data", (d) => {
        this.stderr = (this.stderr + d).slice(-4000);
      });
      p.on("error", (e) => this._fail(new Error("MCP server " + this.name + ": " + (e.message || e))));
      p.on("exit", (code) => {
        const tail = this.stderr.trim().split(/\r?\n/).slice(-5).join("\n");
        this._fail(new Error("MCP server " + this.name + " exited (code " + code + ")" + (tail ? ":\n" + tail : "")));
      });
      this._request("initialize", { protocolVersion: PROTOCOL, capabilities: { roots: {} }, clientInfo: { name: "cortexide-local-agent-bridge", version: "1" } }, INIT_TIMEOUT_MS)
        .then((r) => {
          this.info = (r && r.serverInfo) || { name: this.name };
          this.instructions = (r && r.instructions) || "";
          this._send({ jsonrpc: "2.0", method: "notifications/initialized" });
          resolve(this);
        })
        .catch((e) => {
          this.close();
          reject(e);
        });
    });
    // A failed start may be retried on the next call.
    this.ready.catch(() => {
      this.ready = null;
    });
    return this.ready;
  }

  _send(msg) {
    if (!this.proc || !this.proc.stdin.writable) throw new Error("MCP server " + this.name + " is not running");
    this.proc.stdin.write(JSON.stringify(msg) + "\n");
  }

  _request(method, params, timeoutMs, signal) {
    return new Promise((resolve, reject) => {
      const id = this.nextId++;
      const done = (fn, v) => {
        clearTimeout(timer);
        if (signal) signal.removeEventListener("abort", onAbort);
        this.pending.delete(id);
        fn(v);
      };
      const onAbort = () => {
        try {
          this._send({ jsonrpc: "2.0", method: "notifications/cancelled", params: { requestId: id, reason: "stopped by user" } });
        } catch {
          /* gone */
        }
        done(reject, new Error("stopped"));
      };
      const timer = setTimeout(() => done(reject, new Error(this.name + " " + method + " timed out after " + Math.round((timeoutMs || this.timeoutMs) / 1000) + " s")), timeoutMs || this.timeoutMs);
      if (signal) {
        if (signal.aborted) return onAbort();
        signal.addEventListener("abort", onAbort, { once: true });
      }
      this.pending.set(id, { resolve: (v) => done(resolve, v), reject: (e) => done(reject, e) });
      try {
        this._send({ jsonrpc: "2.0", id, method, params: params || {} });
      } catch (e) {
        done(reject, e);
      }
    });
  }

  _onData(chunk) {
    this.buf += chunk;
    if (this.buf.length > MAX_LINE) {
      this._fail(new Error("MCP server " + this.name + " sent a message over 64 MB"));
      return;
    }
    let i;
    while ((i = this.buf.indexOf("\n")) >= 0) {
      const line = this.buf.slice(0, i).trim();
      this.buf = this.buf.slice(i + 1);
      if (!line) continue;
      let m;
      try {
        m = JSON.parse(line);
      } catch {
        this.log("[mcp " + this.name + "] non-JSON output: " + line.slice(0, 200));
        continue;
      }
      this._onMessage(m);
    }
  }

  _onMessage(m) {
    if (m.id != null && (m.result !== undefined || m.error)) {
      const p = this.pending.get(m.id);
      if (!p) return;
      if (m.error) p.reject(new Error(this.name + ": " + (m.error.message || JSON.stringify(m.error))));
      else p.resolve(m.result);
      return;
    }
    if (m.id != null && m.method) {
      // Requests from the server.
      let result = null;
      if (m.method === "ping") result = {};
      else if (m.method === "roots/list") result = { roots: this.roots.map((r) => ({ uri: "file:///" + r.replace(/\\/g, "/"), name: path.basename(r) })) };
      try {
        if (result) this._send({ jsonrpc: "2.0", id: m.id, result });
        else this._send({ jsonrpc: "2.0", id: m.id, error: { code: -32601, message: "not supported by this client: " + m.method } });
      } catch {
        /* gone */
      }
      return;
    }
    if (m.method === "notifications/tools/list_changed") this.tools = null;
  }

  _fail(err) {
    for (const p of [...this.pending.values()]) p.reject(err);
    this.pending.clear();
    this.proc = null;
    this.ready = null;
    this.tools = null;
  }

  async listTools() {
    await this.start();
    if (this.tools) return this.tools;
    const all = [];
    let cursor;
    for (let page = 0; page < 50; page++) {
      const r = await this._request("tools/list", cursor ? { cursor } : {});
      all.push(...((r && r.tools) || []));
      cursor = r && r.nextCursor;
      if (!cursor) break;
    }
    this.tools = all;
    return all;
  }

  async callTool(tool, args, { signal, timeoutMs } = {}) {
    await this.start();
    return this._request("tools/call", { name: tool, arguments: args || {} }, timeoutMs, signal);
  }

  close() {
    const p = this.proc;
    this._fail(new Error("MCP server " + this.name + " was closed"));
    if (p) {
      try {
        p.stdin.end();
        p.kill();
      } catch {
        /* gone */
      }
    }
  }
}

/** Every configured server; each one starts the first time a chat uses it. */
class McpHub {
  /**
   * @param {Record<string, object>} specs name → {command, args, env, cwd, description}
   * @param {{roots?:string[], log?:(s:string)=>void, timeoutMs?:number, skipped?:string[]}} [o]
   */
  constructor(specs, o = {}) {
    this.specs = specs || {};
    this.o = o;
    this.skipped = o.skipped || [];
    this.servers = new Map();
  }

  names() {
    return Object.keys(this.specs);
  }

  get size() {
    return this.names().length;
  }

  server(name) {
    const key = this.names().find((n) => n.toLowerCase() === String(name || "").toLowerCase());
    if (!key) return null;
    if (!this.servers.has(key)) this.servers.set(key, new McpServer(key, this.specs[key], this.o));
    return this.servers.get(key);
  }

  /** One line per server for the system prompt (does not start anything). */
  summary() {
    return this.names().map((n) => {
      const s = this.specs[n];
      const loaded = this.servers.get(n);
      const count = loaded && loaded.tools ? " (" + loaded.tools.length + " tools)" : "";
      return "- " + n + count + (s.description ? ": " + s.description : "");
    });
  }

  close() {
    for (const s of this.servers.values()) s.close();
    this.servers.clear();
  }
}

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8").replace(/^\uFEFF/, "")); // hand-edited files may carry a BOM
  } catch {
    return null;
  }
}

/**
 * REA under one of the third-party folders: a built source checkout (the git clone made by
 * Tools\Fetch-ThirdParty.ps1 -AgentBridge, after `npm ci && npm run build`) first, then the
 * prebuilt rea-agents npm package. An unbuilt checkout (no dist\) is skipped.
 */
function findRea(dirs) {
  for (const d of dirs || []) {
    if (!d) continue;
    for (const name of ["Reverse-Engineer-anything", "rea"]) {
      const root = path.join(d, name);
      const f = path.join(root, "scripts", "rea.mjs");
      if (fs.existsSync(f) && fs.existsSync(path.join(root, "dist")) && fs.existsSync(path.join(root, "node_modules"))) return f;
    }
  }
  for (const d of dirs || []) {
    if (!d) continue;
    for (const rel of [["node", "node_modules", "rea-agents", "scripts", "rea.mjs"], ["node_modules", "rea-agents", "scripts", "rea.mjs"]]) {
      const f = path.join(d, ...rel);
      if (fs.existsSync(f)) return f;
    }
  }
  return "";
}

/** Folders that may hold Tools\Shared\third_party: the setting first, then each workspace's. */
function thirdPartyDirs(setting, roots) {
  const out = [];
  if (setting) out.push(setting);
  for (const r of roots || []) {
    out.push(path.join(r, "Tools", "Shared", "third_party"));
    out.push(path.join(r, "Shared", "third_party"));
    out.push(path.join(r, "third_party"));
  }
  return out.filter((d) => d && fs.existsSync(d));
}

/**
 * The servers a chat may use.
 * @param {object} o
 * @param {Record<string, object>} [o.configured] localAgentBridge.agent.mcpServers (Cursor / Claude format)
 * @param {string[]} [o.imports] "cursor" (~/.cursor/mcp.json) and / or "claude" (~/.claude.json)
 * @param {string[]} [o.thirdParty] folders searched for the REA package
 * @param {boolean} [o.autoRea] add REA when it is installed there (default true)
 * @param {string} [o.home]
 * @param {string} [o.node] node executable for REA (default "node"; REA needs Node 22.19+)
 * @returns {{specs: Record<string, object>, skipped: string[]}}
 */
function resolveServers(o = {}) {
  const home = o.home || os.homedir();
  const specs = {};
  const skipped = [];
  const add = (from, servers) => {
    for (const [name, s] of Object.entries(servers || {})) {
      if (!s || typeof s !== "object") continue;
      if (s.disabled === true || s.enabled === false) {
        delete specs[name];
        continue;
      }
      if (!s.command) {
        skipped.push(name + " (" + from + "): " + (s.url ? "HTTP/SSE servers are not supported yet, only stdio" : "no command"));
        continue;
      }
      specs[name] = {
        command: String(s.command),
        args: Array.isArray(s.args) ? s.args.map(String) : [],
        env: s.env && typeof s.env === "object" ? s.env : {},
        cwd: s.cwd || undefined,
        description: s.description || "",
        from,
      };
    }
  };
  const imports = (o.imports || []).map((s) => String(s).toLowerCase());
  if (imports.includes("claude")) add("~/.claude.json", (readJson(path.join(home, ".claude.json")) || {}).mcpServers);
  if (imports.includes("cursor")) add("~/.cursor/mcp.json", (readJson(path.join(home, ".cursor", "mcp.json")) || {}).mcpServers);
  add("settings", o.configured);
  if (o.autoRea !== false && !Object.keys(specs).some((n) => n.toLowerCase() === "rea") && !(o.configured && o.configured.rea)) {
    const rea = findRea(o.thirdParty);
    if (rea) {
      specs.rea = {
        command: o.node || "node",
        args: [rea, "mcp"],
        env: {},
        description: "REA, Reverse Engineer Anything: native binaries (via Ghidra / Hopper / IDA when installed), .NET assemblies, JavaScript / Electron apps, websites, firmware",
        from: rea,
      };
    }
  }
  return { specs, skipped };
}

function firstLine(s, n = 140) {
  const t = String(s || "").trim().split(/\r?\n/)[0];
  return t.length > n ? t.slice(0, n - 1) + "…" : t;
}

/** Compact "name(arg, opt?)" signature from a JSON schema. */
function signature(t) {
  const sch = t.inputSchema || {};
  const req = new Set(sch.required || []);
  const args = Object.keys(sch.properties || {}).map((k) => k + (req.has(k) ? "" : "?"));
  return t.name + "(" + args.join(", ") + ")";
}

/**
 * Turn a tools/call result into agent tool output.
 * @returns {{text:string, images:object[]}}
 */
function formatResult(server, tool, res) {
  const texts = [];
  const images = [];
  for (const c of (res && res.content) || []) {
    if (c.type === "text") texts.push(String(c.text || ""));
    else if (c.type === "image" && c.data) images.push({ mime: c.mimeType || "image/png", data: c.data, path: server + "." + tool, width: 0, height: 0 });
    else if (c.type === "resource" && c.resource) texts.push(c.resource.text != null ? String(c.resource.text) : "[resource " + (c.resource.uri || "") + (c.resource.mimeType ? ", " + c.resource.mimeType : "") + "]");
    else if (c.type === "resource_link") texts.push("[resource " + (c.uri || "") + (c.name ? " " + c.name : "") + "]");
    else if (c.type === "audio") texts.push("[audio, " + (c.mimeType || "unknown type") + "]");
  }
  if (!texts.length && res && res.structuredContent != null) texts.push(JSON.stringify(res.structuredContent, null, 1));
  let text = texts.join("\n") || (images.length ? "" : "(no output)");
  if (res && res.isError) text = "error: " + server + "." + tool + " failed: " + text;
  return { text, images };
}

module.exports = { McpServer, McpHub, resolveServers, thirdPartyDirs, findRea, formatResult, signature, firstLine, needsShell, PROTOCOL };
