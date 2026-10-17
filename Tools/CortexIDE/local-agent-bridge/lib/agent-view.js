"use strict";

const vscode = require("vscode");
const fs = require("fs");
const path = require("path");
const os = require("os");
const llm = require("./llm");
const { runAgent } = require("./agent");
const { ToolContext, defaultRgPath } = require("./agent-tools");
const { Progress } = require("./agent-context");
const { parseChatFile } = require("./import-chat");

const STATE_KEY = "localAgentBridge.agent.conversation";
const MAX_LOG = 400;
const MAX_HISTORY_TURNS = 12;

function cfg() {
  return vscode.workspace.getConfiguration("localAgentBridge.agent");
}

function folders() {
  return (vscode.workspace.workspaceFolders || []).map((f) => f.uri.fsPath);
}

function emptyConv() {
  return { log: [], history: [], progress: null, importedFrom: "" };
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
  };
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
  }

  static register(context, getState) {
    const provider = new AgentViewProvider(context, getState);
    context.subscriptions.push(
      vscode.window.registerWebviewViewProvider("localAgentBridge.agent", provider, {
        webviewOptions: { retainContextWhenHidden: true },
      })
    );
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
    view.webview.html = html();
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
        this.post({ type: "restore", log: this.conv().log });
        await this.refreshBackend(false);
      } else if (m.type === "send") await this.send(m.text);
      else if (m.type === "stop") this.stop();
      else if (m.type === "new") await this.newChat();
      else if (m.type === "model") await this.pickModel();
      else if (m.type === "import") await this.importChat();
      else if (m.type === "progress") await this.openProgress();
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
    try {
      this.backend = await llm.discover({
        provider: c.get("provider", "auto"),
        baseUrl: c.get("baseUrl", ""),
        apiKey: c.get("apiKey", ""),
      });
      this.model = llm.pickModel(this.backend.models, c.get("model", ""), this.backend.provider);
      this.ctxTokens = await llm.contextWindow(this.backend, this.model, {
        override: c.get("contextTokens", 0),
        ollamaNumCtx: c.get("ollamaNumCtx", 16384),
      });
    } catch (e) {
      this.backend = null;
      this.post({ type: "header", ok: false, text: "No backend · " + String(e.message || e).split("\n")[0] });
      return null;
    }
    this.postHeader();
    return this.backend;
  }

  postHeader() {
    if (!this.backend) return;
    this.post({
      type: "header",
      ok: true,
      text: this.backend.label + " · " + this.model + " · " + Math.round(this.ctxTokens / 1024) + "k ctx",
      title: this.backend.baseUrl,
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
    const backend = await this.refreshBackend(!this.backend);
    if (!backend) {
      this.post({ type: "error", text: "No local model reachable. Start vLLM (:30000 / :8000) or Ollama (:11434), or set localAgentBridge.agent.baseUrl." });
      this.post({ type: "idle" });
      return;
    }
    const c = this.conv();
    await this.log(c, "user", text);
    this.post({ type: "busy" });
    const controller = new AbortController();
    this.running = controller;
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
      signal: controller.signal,
      confirmShell: async (command, cwd) => {
        const pick = await vscode.window.showWarningMessage("Agent wants to run in " + cwd + ":\n\n" + command, { modal: true }, "Run");
        return pick === "Run";
      },
    });
    try {
      const result = await runAgent({
        backend,
        model: this.model,
        contextTokens: this.ctxTokens,
        maxOutputTokens: a.get("maxOutputTokens", 2048),
        maxRounds: a.get("maxRounds", 30),
        temperature: a.get("temperature", 0.2),
        prompt: text,
        history: c.history,
        prior: c.progress,
        tools,
        env,
        skills: this.getState().skills || [],
        signal: controller.signal,
        onEvent: (ev) => {
          if (ev.type === "tool" && ev.status === "done") {
            c.log.push({ cls: "tool", name: ev.name, label: ev.label, ok: ev.ok, text: String(ev.result || "").slice(0, 2000) });
          } else if (ev.type === "thought") c.log.push({ cls: "thought", text: ev.text });
          else if (ev.type === "status" && !ev.transient) c.log.push({ cls: "sys", text: ev.text });
          else if (ev.type === "assistant") c.log.push({ cls: "assistant", text: ev.text });
          this.post(ev);
        },
      });
      c.history.push({ role: "user", content: text }, { role: "assistant", content: result.text });
      c.progress = result.progress;
      const file = new Progress(result.progress).persist(env.roots[0]);
      if (file) this.post({ type: "status", text: "Progress index: " + file });
    } catch (e) {
      const msg = String((e && e.message) || e);
      c.log.push({ cls: msg === "stopped" ? "sys" : "err", text: msg === "stopped" ? "Stopped." : msg });
      this.post({ type: msg === "stopped" ? "status" : "error", text: msg === "stopped" ? "Stopped." : msg });
      if (msg !== "stopped") this.backend = null;
    } finally {
      this.running = null;
      await this.saveConv(c);
      this.post({ type: "idle" });
    }
  }

  async newChat() {
    this.stop();
    await this.saveConv(emptyConv());
    this.post({ type: "restore", log: [] });
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
      { label: "OpenAI-compatible URL…", description: "LM Studio, llama.cpp, a tunnel, …", id: "openai" },
    ];
    const p = await vscode.window.showQuickPick(providers, { placeHolder: "Model backend for the CortexIDE Agent" });
    if (!p) return;
    const c = cfg();
    let baseUrl = "";
    if (p.id === "openai") {
      baseUrl = (await vscode.window.showInputBox({ prompt: "Base URL (ending in /v1)", value: c.get("baseUrl", "") || "http://127.0.0.1:1234/v1", ignoreFocusOut: true })) || "";
      if (!baseUrl) return;
    }
    let backend;
    try {
      backend = await llm.discover({ provider: p.id, baseUrl, apiKey: c.get("apiKey", "") });
    } catch (e) {
      vscode.window.showErrorMessage(String(e.message || e));
      return;
    }
    const m = await vscode.window.showQuickPick(
      backend.models.map((x) => ({ label: x.id, description: x.ctx ? Math.round(x.ctx / 1024) + "k ctx" : "", id: x.id })),
      { placeHolder: backend.label + " models at " + backend.baseUrl }
    );
    if (!m) return;
    const G = vscode.ConfigurationTarget.Global;
    await c.update("provider", p.id, G);
    await c.update("baseUrl", p.id === "openai" ? baseUrl : "", G);
    await c.update("model", m.id, G);
    await this.refreshBackend(true);
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
    await this.saveConv(c);
    await this.focus();
    this.post({ type: "restore", log: c.log });
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

function html() {
  return `<!DOCTYPE html>
<html><head><meta charset="UTF-8"/>
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline';"/>
<style>
  html,body{height:100%;margin:0;padding:0;background:var(--vscode-sideBar-background);color:var(--vscode-foreground);font-family:var(--vscode-font-family);font-size:var(--vscode-font-size)}
  #wrap{display:flex;flex-direction:column;height:100%}
  header{padding:6px 10px;border-bottom:1px solid var(--vscode-panel-border);display:flex;flex-wrap:wrap;gap:6px;align-items:center}
  #hdr{flex:1 1 100%;font-size:11px;color:var(--vscode-descriptionForeground);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  #hdr.bad{color:var(--vscode-errorForeground)}
  header button{background:var(--vscode-button-secondaryBackground);color:var(--vscode-button-secondaryForeground);border:0;border-radius:3px;padding:3px 8px;cursor:pointer;font:inherit;font-size:11px}
  header button:hover{background:var(--vscode-button-secondaryHoverBackground)}
  #log{flex:1;overflow:auto;padding:8px 10px}
  .m{margin:0 0 10px;white-space:pre-wrap;word-break:break-word;line-height:1.45}
  .user{background:var(--vscode-input-background);border:1px solid var(--vscode-input-border,transparent);border-radius:4px;padding:6px 8px}
  .thought{color:var(--vscode-descriptionForeground)}
  .sys{color:var(--vscode-descriptionForeground);font-size:11px;font-style:italic}
  .err{color:var(--vscode-errorForeground)}
  .assistant{border-left:2px solid var(--vscode-focusBorder);padding-left:8px}
  details.tool{margin:0 0 6px;font-size:12px}
  details.tool summary{cursor:pointer;color:var(--vscode-textLink-foreground);list-style:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  details.tool summary::-webkit-details-marker{display:none}
  details.tool.bad summary{color:var(--vscode-errorForeground)}
  details.tool pre,.m pre{background:var(--vscode-textCodeBlock-background);padding:6px;border-radius:3px;overflow:auto;max-height:22em;white-space:pre;margin:4px 0;font-family:var(--vscode-editor-font-family);font-size:12px}
  code{font-family:var(--vscode-editor-font-family);background:var(--vscode-textCodeBlock-background);padding:0 3px;border-radius:2px}
  #live{font-size:11px;color:var(--vscode-descriptionForeground);padding:0 10px 4px;min-height:14px}
  form{display:flex;flex-direction:column;gap:6px;padding:8px 10px;border-top:1px solid var(--vscode-panel-border)}
  textarea{min-height:60px;resize:vertical;background:var(--vscode-input-background);color:var(--vscode-input-foreground);border:1px solid var(--vscode-input-border,transparent);border-radius:3px;padding:6px;font:inherit}
  textarea:focus{outline:1px solid var(--vscode-focusBorder)}
  .row{display:flex;gap:6px;justify-content:flex-end;align-items:center}
  .row span{flex:1;font-size:11px;color:var(--vscode-descriptionForeground)}
  .row button{background:var(--vscode-button-background);color:var(--vscode-button-foreground);border:0;border-radius:3px;padding:4px 12px;cursor:pointer;font:inherit}
  .row button:hover{background:var(--vscode-button-hoverBackground)}
  #stop{display:none;background:var(--vscode-inputValidation-errorBackground,#a33)}
  .busy #stop{display:inline-block}.busy #go{display:none}
</style></head>
<body><div id="wrap">
<header>
  <div id="hdr">Connecting to local model…</div>
  <button id="model" title="Pick backend and model">Model</button>
  <button id="import" title="Import a Cursor chat to continue">Import chat</button>
  <button id="progress" title="Open the programmatic progress index">Progress</button>
  <button id="new" title="Start a new conversation">New</button>
</header>
<div id="log"></div>
<div id="live"></div>
<form id="f">
  <textarea id="q" placeholder="Tell the agent what to do. Enter to send, Shift+Enter for a newline."></textarea>
  <div class="row"><span>Tools run in this workspace. Edits save to disk.</span><button id="stop" type="button">Stop</button><button id="go" type="submit">Send</button></div>
</form>
</div>
<script>
const vs = acquireVsCodeApi();
const $ = (id) => document.getElementById(id);
const log = $("log"), q = $("q"), live = $("live");
function esc(s){return String(s).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));}
function md(s){
  let t = esc(s);
  t = t.replace(/\`\`\`[\\w.+-]*\\n?([\\s\\S]*?)\`\`\`/g, (_,c)=>"<pre>"+c+"</pre>");
  t = t.replace(/\`([^\`\\n]+)\`/g, "<code>$1</code>");
  t = t.replace(/\\*\\*([^*\\n]+)\\*\\*/g, "<b>$1</b>");
  return t;
}
function atBottom(){return log.scrollHeight - log.scrollTop - log.clientHeight < 40;}
function scroll(stick){ if(stick) log.scrollTop = log.scrollHeight; }
function add(row){
  const stick = atBottom();
  if(row.cls === "tool"){
    const d = document.createElement("details");
    d.className = "tool" + (row.ok === false ? " bad" : "");
    const s = document.createElement("summary");
    s.textContent = (row.ok === false ? "✗ " : "✓ ") + row.name + (row.label ? "  " + row.label : "");
    const pre = document.createElement("pre");
    pre.textContent = row.text || "";
    d.appendChild(s); d.appendChild(pre); log.appendChild(d);
  } else {
    const d = document.createElement("div");
    d.className = "m " + row.cls;
    if(row.cls === "assistant" || row.cls === "thought") d.innerHTML = md(row.text || "");
    else d.textContent = row.text || "";
    log.appendChild(d);
  }
  scroll(stick);
}
function busy(on){ document.body.classList.toggle("busy", !!on); if(!on) live.textContent = ""; }
$("f").addEventListener("submit", (e) => { e.preventDefault(); const t = q.value.trim(); if(!t) return; add({cls:"user", text:t}); scroll(true); q.value = ""; busy(true); vs.postMessage({type:"send", text:t}); });
q.addEventListener("keydown", (e) => { if(e.key === "Enter" && !e.shiftKey){ e.preventDefault(); $("f").requestSubmit(); } });
$("stop").onclick = () => vs.postMessage({type:"stop"});
$("new").onclick = () => vs.postMessage({type:"new"});
$("model").onclick = () => vs.postMessage({type:"model"});
$("import").onclick = () => vs.postMessage({type:"import"});
$("progress").onclick = () => vs.postMessage({type:"progress"});
window.addEventListener("message", (e) => {
  const m = e.data || {};
  if(m.type === "header"){ $("hdr").textContent = m.text; $("hdr").title = m.title || ""; $("hdr").className = m.ok ? "" : "bad"; }
  else if(m.type === "restore"){ log.innerHTML = ""; (m.log||[]).forEach(add); scroll(true); }
  else if(m.type === "busy") busy(true);
  else if(m.type === "idle") busy(false);
  else if(m.type === "status"){ if(m.transient) live.textContent = m.text; else add({cls:"sys", text:m.text}); }
  else if(m.type === "thought") add({cls:"thought", text:m.text});
  else if(m.type === "tool"){ if(m.status === "start") live.textContent = "→ " + m.name + " " + (m.label||""); else add({cls:"tool", name:m.name, label:m.label, ok:m.ok, text:m.result}); }
  else if(m.type === "assistant") add({cls:"assistant", text:m.text});
  else if(m.type === "error"){ add({cls:"err", text:m.text}); busy(false); }
  else if(m.type === "seed"){ q.value = m.text; q.focus(); }
});
vs.postMessage({type:"ready"});
</script></body></html>`;
}

module.exports = { AgentViewProvider };
