"use strict";

const vscode = require("vscode");
const path = require("path");
const fs = require("fs");
const { scanSkills, scanCanvases, matchSkills, home, exists, cursorProjectSlug } = require("./lib/scan");
const { syncWorkspace } = require("./lib/sync");
const { CanvasEditorProvider } = require("./lib/canvas-editor");
const { importChatFile, listImported, agentPrompt } = require("./lib/import-chat");
const { AgentViewProvider } = require("./lib/agent-view");
const { HomeTab } = require("./lib/home-tab");

function folders() {
  return (vscode.workspace.workspaceFolders || []).map((f) => f.uri.fsPath);
}

function cfg() {
  return vscode.workspace.getConfiguration("localAgentBridge");
}

function scanAll(context) {
  const c = cfg();
  const workspaceFolders = folders();
  const extra = [...(c.get("extraSkillRoots", []) || [])];
  extra.push(path.join(context.extensionPath, "skills"));
  const skills = scanSkills({
    workspaceFolders,
    includeBuiltIn: c.get("includeBuiltInSkills", true),
    includePlugin: c.get("includePluginSkills", false),
    extraSkillRoots: extra,
  });
  const canvases = scanCanvases(workspaceFolders);
  return { skills, canvases };
}

function registerLmTools(context, getState) {
  if (!vscode.lm || typeof vscode.lm.registerTool !== "function") return;
  const mk = (name, cb) => vscode.lm.registerTool(name, {
    invoke: async (options) => {
      const text = await cb(options.input || {});
      return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(text)]);
    },
  });
  context.subscriptions.push(mk("list_skills", async () => {
    const { skills } = getState();
    return JSON.stringify(skills.map((s) => ({ name: s.name, description: s.description, source: s.source, file: s.file })), null, 2);
  }));
  context.subscriptions.push(mk("read_skill", async (input) => {
    const { skills } = getState();
    const skill = skills.find((s) => s.name.toLowerCase() === String(input.name || "").toLowerCase());
    if (!skill) return `No skill named ${input.name}`;
    return `# ${skill.name}\n\n${skill.description}\n\nSource: ${skill.file}\n\n${skill.instructions}`;
  }));
  context.subscriptions.push(mk("match_skills", async (input) => {
    const { skills } = getState();
    const hits = matchSkills(skills, input.query, input.limit || 8);
    return JSON.stringify(hits.map((s) => ({ name: s.name, description: s.description, file: s.file })), null, 2);
  }));
  context.subscriptions.push(mk("list_canvases", async () => JSON.stringify(getState().canvases, null, 2)));
  context.subscriptions.push(mk("read_canvas", async (input) => {
    const { canvases } = getState();
    const q = String(input.name || "").replace(/\\/g, "/");
    const canvas = canvases.find((c) => c.name === input.name || c.file.replace(/\\/g, "/") === q);
    if (!canvas) return `No canvas named ${input.name}`;
    return fs.readFileSync(canvas.file, "utf8");
  }));
  context.subscriptions.push(mk("import_cursor_chat", async (input) => {
    const root = folders()[0];
    const result = importChatFile(String(input.path || ""), root);
    return JSON.stringify({ dest: result.dest, turns: result.turns, prompt: result.prompt }, null, 2);
  }));
  context.subscriptions.push(mk("list_imported_chats", async () => {
    return JSON.stringify(listImported(folders()[0]), null, 2);
  }));
}

class CatalogTree {
  constructor(kind, getState) {
    this.kind = kind;
    this.getState = getState;
    this._onDidChangeTreeData = new vscode.EventEmitter();
    this.onDidChangeTreeData = this._onDidChangeTreeData.event;
  }
  refresh() {
    this._onDidChangeTreeData.fire();
  }
  getTreeItem(el) {
    const item = new vscode.TreeItem(el.label, vscode.TreeItemCollapsibleState.None);
    item.description = el.description;
    item.tooltip = el.file;
    item.command = {
      command: this.kind === "skills"
        ? "localAgentBridge.openSkill"
        : this.kind === "chats"
          ? "localAgentBridge.continueImportedChat"
          : "localAgentBridge.openCanvas",
      title: "Open",
      arguments: [el.file],
    };
    return item;
  }
  getChildren() {
    const { skills, canvases } = this.getState();
    if (this.kind === "skills") {
      return skills.map((s) => ({ label: s.name, description: s.source, file: s.file }));
    }
    if (this.kind === "chats") {
      return listImported(folders()[0]).map((c) => ({ label: c.name, description: "imported", file: c.file }));
    }
    return canvases.map((c) => ({ label: c.name, description: c.project, file: c.file }));
  }
}

async function doSync(context, getState, setState) {
  const state = scanAll(context);
  setState(state);
  if (!cfg().get("writeWorkspaceFiles", true)) {
    return state;
  }
  const roots = folders();
  if (!roots.length) {
    vscode.window.showWarningMessage("Local Agent Bridge: open a folder so skills can sync into .cortexide/skills.");
    return state;
  }
  // Register the MCP server first: it is what other chats need, and it must not depend on every
  // folder being writable (a read-only root used to abort the sync and leave a stale server path).
  const mcpPath = path.join(home(), ".cortexide", "mcp.json");
  const failed = [];
  try {
    mergeMcp(mcpPath, context.extensionPath, roots);
  } catch (e) {
    failed.push(`${mcpPath}: ${e.message || e}`);
  }
  let last;
  const skipped = [];
  for (const root of roots) {
    try {
      last = syncWorkspace(root, state.skills, state.canvases, { maxSkills: cfg().get("maxSkills", 64) });
    } catch (e) {
      // e.g. C:\Program Files\... or a locked Temp folder: skip it, keep syncing the rest.
      failed.push(`${root}: ${e.code || e.message || e}`);
      continue;
    }
    for (const s of last.skippedSkills || []) skipped.push(`${s.name} (${path.join(root, ".cortexide", "skills", s.name)})`);
  }
  if (skipped.length) {
    console.warn("Local Agent Bridge: kept native skills, bridged copies skipped: " + skipped.join(", "));
  }
  if (failed.length) console.warn("Local Agent Bridge: sync skipped: " + failed.join("; "));
  return { ...state, last, skipped, failed };
}

/** @param {string|string[]} workspaceRoots  every open root; mcp-server.js splits the env var on ";" */
function mergeMcp(mcpPath, extDir, workspaceRoots) {
  let json = { mcpServers: {} };
  if (exists(mcpPath)) {
    try {
      // Strip a UTF-8 BOM: PowerShell 5.1 (Set-Content -Encoding UTF8) writes one and JSON.parse rejects it.
      json = JSON.parse(fs.readFileSync(mcpPath, "utf8").replace(/^\uFEFF/, ""));
    } catch {
      json = { mcpServers: {} };
    }
  }
  json.mcpServers = json.mcpServers || {};
  // Entry written by builds before the rename; it points at the old extension folder.
  const legacy = json.mcpServers["cursor-bridge"];
  if (legacy && /cursor-agent-bridge/i.test(JSON.stringify(legacy.args || []))) delete json.mcpServers["cursor-bridge"];
  json.mcpServers["local-agent-bridge"] = {
    command: "node",
    args: [path.join(extDir, "mcp-server.js")],
    env: {
      AGENT_BRIDGE_WORKSPACE: [].concat(workspaceRoots || []).filter(Boolean).join(";"),
    },
  };
  fs.mkdirSync(path.dirname(mcpPath), { recursive: true });
  fs.writeFileSync(mcpPath, JSON.stringify(json, null, 2), "utf8");
}

function activate(context) {
  let state = { skills: [], canvases: [] };
  const getState = () => state;
  const setState = (s) => {
    state = s;
    skillsTree.refresh();
    canvasesTree.refresh();
    chatsTree.refresh();
    status.text = `$(hubot) ${s.skills.length} skills · ${s.canvases.length} canvases`;
  };

  const skillsTree = new CatalogTree("skills", getState);
  const canvasesTree = new CatalogTree("canvases", getState);
  const chatsTree = new CatalogTree("chats", getState);
  context.subscriptions.push(vscode.window.registerTreeDataProvider("localAgentBridge.skills", skillsTree));
  context.subscriptions.push(vscode.window.registerTreeDataProvider("localAgentBridge.canvases", canvasesTree));
  context.subscriptions.push(vscode.window.registerTreeDataProvider("localAgentBridge.chats", chatsTree));
  context.subscriptions.push(CanvasEditorProvider.register(context));
  const agent = AgentViewProvider.register(context, getState);
  // The New Tab page takes the Welcome page's place when the Local Agent is opened or focused.
  HomeTab.register(context, agent);

  const status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 50);
  status.command = "localAgentBridge.showCatalog";
  status.tooltip = "Local Agent Bridge — CortexIDE skills & canvases";
  status.show();
  context.subscriptions.push(status);

  const agentStatus = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 49);
  agentStatus.text = "$(hubot) Agent";
  agentStatus.command = "localAgentBridge.openAgent";
  agentStatus.tooltip = "Open the CortexIDE Agent (local model or Claude + coding tools)";
  agentStatus.show();
  context.subscriptions.push(agentStatus);

  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.openAgent", () => agent.focus()));
  // Memory between chats (lib/memory.js): manage, add, import, export, generate now.
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.memoryManage", () => agent.manageMemory()));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.memoryAdd", () => agent.addMemory()));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.memoryImport", () => agent.importMemory()));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.memoryExport", () => agent.exportMemory()));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.memoryGenerate", () => agent.generateMemorySoon(agent.active(), { force: true })));
  // Canvases of other workspaces (a moved project, a second checkout): hard-link them into this one.
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.linkCanvas", async (file) => {
    const link = require("./lib/canvas-link");
    const roots = (vscode.workspace.workspaceFolders || []).map((f) => f.uri.fsPath);
    if (!roots.length) return vscode.window.showWarningMessage("Open a folder first: canvases are linked to a workspace.");
    let picked = [];
    if (typeof file === "string" && file) picked = [file];
    else if (file && file.fsPath) picked = [file.fsPath];
    else {
      const others = link.otherCanvases(roots);
      if (!others.length) return vscode.window.showInformationMessage("No canvases in other workspaces to link.");
      const items = [];
      let last = "";
      for (const c of others.sort((a, b) => a.project.localeCompare(b.project) || a.name.localeCompare(b.name))) {
        if (c.project !== last) {
          items.push({ label: c.project, kind: vscode.QuickPickItemKind ? vscode.QuickPickItemKind.Separator : undefined });
          last = c.project;
        }
        items.push({ label: c.name, description: c.project, detail: c.file, file: c.file });
      }
      const sel = await vscode.window.showQuickPick(items.filter((i) => i.file || i.kind), { canPickMany: true, matchOnDescription: true, placeHolder: "Canvases to link to " + path.basename(roots[0]) + " (they stay in sync with the original)" });
      if (!sel || !sel.length) return;
      picked = sel.filter((i) => i.file).map((i) => i.file);
    }
    const done = { linked: 0, copied: 0, already: 0, exists: [] };
    let lastTarget = "";
    for (const f of picked) {
      const r = link.linkCanvas(f, roots[0]);
      lastTarget = r.target;
      if (r.how === "exists") done.exists.push(path.basename(f));
      else if (r.how === "already linked") done.already++;
      else done[r.how]++;
    }
    const parts = [];
    if (done.linked) parts.push(done.linked + " linked");
    if (done.copied) parts.push(done.copied + " copied (other drive)");
    if (done.already) parts.push(done.already + " already linked");
    if (done.exists.length) parts.push("skipped, a different canvas has the name: " + done.exists.join(", "));
    vscode.window.showInformationMessage("Canvases → " + link.projectCanvasDir(roots[0]) + ": " + parts.join("; "));
    agent.postPanels();
    if (picked.length === 1 && lastTarget && !done.exists.length) await vscode.commands.executeCommand("localAgentBridge.openCanvas", lastTarget);
  }));
  // Canvas toolbar / in-canvas buttons: the request goes to the chat on screen (or a new one when it is busy).
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.agentAskCanvas", async (text) => {
    let t = typeof text === "string" ? text : "";
    if (!t) {
      const tab = vscode.window.tabGroups.activeTabGroup.activeTab;
      const file = tab && tab.input && tab.input.uri ? tab.input.uri.fsPath : "";
      const ask = await vscode.window.showInputBox({ prompt: "What should the agent change" + (file ? " in " + require("path").basename(file) : "") + "?" });
      if (!ask) return;
      t = (file ? "Update the canvas " + file + ": " : "") + ask;
    }
    await agent.askAboutCanvas(t);
  }));
  // Opened from another window's sidebar tree ("Start a chat here"): open the Agent with a new chat.
  setTimeout(() => agent.takeHandoff().catch(() => {}), 1500);
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.agentPickModel", () => agent.pickModel()));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.agentNewChat", () => agent.newChat()));
  // A chat that works in any folder, opened in this window (no window switch).
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.agentNewChatInFolder", (folder) => agent.newChatInFolder(folder)));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.agentStop", () => agent.stop()));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.agentHistory", () => agent.showHistory()));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.agentRunOnModels", () => agent.runOnModelsFromComposer()));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.agentUndo", () => agent.undoTurn()));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.agentProgress", () => agent.openProgress()));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.agentIndexes", () => agent.openIndexes()));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.agentLimits", () => agent.command("limits")));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.agentCompress", () => agent.command("compress")));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.agentSteer", () => agent.command("steer")));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.setClaudeApiKey", () => agent.setClaudeApiKey()));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.signIn", () => agent.command("signin")));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.signOut", () => agent.command("signout")));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.askAgentAboutSelection", async () => {
    const ed = vscode.window.activeTextEditor;
    if (!ed) return agent.focus();
    const line = ed.selection.start.line + 1;
    await agent.ask(`In ${ed.document.uri.fsPath} (selection starts at line ${line}): `);
  }));

  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.sync", async () => {
    const result = await doSync(context, getState, setState);
    const kept = result.skipped && result.skipped.length
      ? ` Skipped ${result.skipped.length} bridged skill(s) whose name matches a native .cortexide/skills folder: ${result.skipped.map((s) => s.split(" (")[0]).join(", ")}.`
      : "";
    const off = result.failed && result.failed.length
      ? ` Not writable, skipped: ${result.failed.map((f) => f.split(": ")[0]).join(", ")}.`
      : "";
    vscode.window.showInformationMessage(
      `Local Agent Bridge: ${result.skills.length} skills, ${result.canvases.length} canvases.${kept}${off} Reload CortexIDE chat if MCP was just added.`
    );
  }));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.showCatalog", async () => {
    const { skills, canvases } = getState();
    const doc = await vscode.workspace.openTextDocument({
      content: `# Local Agent Bridge\n\n## Skills (${skills.length})\n${skills.map((s) => `- \`/${s.name}\` (${s.source}) — ${s.description}\n  ${s.file}`).join("\n")}\n\n## Canvases (${canvases.length})\n${canvases.map((c) => `- ${c.name} — ${c.file}`).join("\n")}\n`,
      language: "markdown",
    });
    await vscode.window.showTextDocument(doc, { preview: true });
  }));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.openSkill", async (file) => {
    const target = file || (await pickSkill(getState().skills));
    if (target) await vscode.window.showTextDocument(vscode.Uri.file(target));
  }));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.openCanvas", async (file) => {
    const target = file || (await pickCanvas(getState().canvases));
    if (!target) return;
    const uri = typeof target === "string" ? vscode.Uri.file(target) : target;
    await vscode.commands.executeCommand("vscode.openWith", uri, "localAgentBridge.canvasPreview");
  }));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.openCanvasSource", async (file) => {
    let target = file;
    if (target && target.uri) target = target.uri;
    if (!target) {
      const tab = vscode.window.tabGroups.activeTabGroup.activeTab;
      if (tab && tab.input && tab.input.uri) target = tab.input.uri;
    }
    if (!target) {
      const active = vscode.window.activeTextEditor;
      if (active && /\.canvas\.tsx$/i.test(active.document.fileName)) target = active.document.uri;
    }
    if (!target) target = await pickCanvas(getState().canvases);
    if (!target) return;
    const uri = typeof target === "string" ? vscode.Uri.file(target) : target;
    await vscode.commands.executeCommand("vscode.openWith", uri, "default");
  }));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.openCanvasFolder", async () => {
    const root = folders()[0];
    if (!root) return;
    const slug = cursorProjectSlug(root);
    const dir = path.join(home(), ".cursor", "projects", slug, "canvases");
    fs.mkdirSync(dir, { recursive: true });
    await vscode.commands.executeCommand("revealFileInOS", vscode.Uri.file(dir));
  }));
  // CortexIDE's built-in chat does not render extension chat contributions, so imports
  // land in our own Agent panel, which actually runs the tools.
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.importChat", async (uri) => {
    try {
      const file = uri && uri.fsPath ? uri.fsPath : typeof uri === "string" ? uri : "";
      if (file && folders()[0]) {
        importChatFile(file, folders()[0]);
        chatsTree.refresh();
      }
      await agent.importChat(file || undefined);
    } catch (e) {
      vscode.window.showErrorMessage(`Import chat failed: ${e.message || e}`);
    }
  }));
  context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.continueImportedChat", async (file) => {
    const target = file || (await pickImported());
    if (!target) return;
    const dest = typeof target === "string" ? target : target.fsPath || target;
    await agent.importChat(dest);
  }));

  registerLmTools(context, getState);

  if (vscode.chat && typeof vscode.chat.createChatParticipant === "function") {
    const participant = vscode.chat.createChatParticipant("local-agent-bridge.agent", async (request, _ctx, stream) => {
      if (request.command === "import" || /^\s*import\b/i.test(request.prompt)) {
        try {
          const result = await runImportChat();
          chatsTree.refresh();
          stream.markdown(`Imported **${result.turns}** turns to \`${result.dest}\`.\n\nPaste this into **Agent** mode (or send it now). Start with a tool call.\n\n`);
          stream.markdown("```\n" + result.prompt + "\n```\n");
          await openAgentPrompt(result.prompt);
        } catch (e) {
          stream.markdown(`Import failed: ${e.message || e}\n`);
        }
        return;
      }
      const { skills, canvases } = getState();
      const hits = matchSkills(skills, request.prompt, 4);
      stream.markdown(`Running as a **coding agent**. Matching skills: ${hits.map((s) => `\`/${s.name}\``).join(", ") || "none"}.\n\n`);
      if (!hits.length) {
        stream.markdown("Use CortexIDE **Agent** mode in the main chat for tools (read_file, edit_file, attempt_completion). Slash-commands like `/canvas` load bridged skills.\n");
      } else {
        for (const s of hits) {
          stream.markdown(`### /${s.name}\n${s.description}\n\n`);
        }
      }
      stream.markdown(`Canvases available: ${canvases.length}. Prefer CortexIDE Agent mode so tool calls actually run.\n`);
    });
    participant.iconPath = vscode.Uri.file(path.join(context.extensionPath, "media", "icon.svg"));
    context.subscriptions.push(participant);
  }

  if (cfg().get("syncOnStartup", true)) {
    doSync(context, getState, setState).catch((e) => {
      vscode.window.showErrorMessage(`Local Agent Bridge sync failed: ${e.message || e}`);
    });
  } else {
    setState(scanAll(context));
  }
}

async function runImportChat(uri) {
  let file;
  if (uri && uri.fsPath) file = uri.fsPath;
  else if (typeof uri === "string") file = uri;
  else if (vscode.window.activeTextEditor && /\.(md|jsonl|json)$/i.test(vscode.window.activeTextEditor.document.fileName)) {
    file = vscode.window.activeTextEditor.document.fileName;
  }
  if (!file) {
    const downloads = path.join(home(), "Downloads");
    const picked = await vscode.window.showOpenDialog({
      canSelectFiles: true,
      canSelectMany: false,
      defaultUri: exists(downloads) ? vscode.Uri.file(downloads) : undefined,
      filters: { "Cursor chats": ["md", "jsonl", "json"] },
      title: "Import Cursor chat export",
    });
    if (!picked || !picked.length) throw new Error("No file selected");
    file = picked[0].fsPath;
  }
  return importChatFile(file, folders()[0]);
}

async function openAgentPrompt(prompt) {
  await vscode.env.clipboard.writeText(prompt);
  const attempts = [
    ["workbench.action.chat.open", { query: prompt }],
    ["workbench.action.chat.open", prompt],
  ];
  for (const [cmd, arg] of attempts) {
    try {
      await vscode.commands.executeCommand(cmd, arg);
      return true;
    } catch {
      /* try next */
    }
  }
  return false;
}

async function pickImported() {
  const chats = listImported(folders()[0]);
  const pick = await vscode.window.showQuickPick(
    chats.map((c) => ({ label: c.name, detail: c.file, file: c.file })),
    { placeHolder: "Continue an imported chat in Agent mode" }
  );
  return pick && pick.file;
}

async function pickSkill(skills) {
  const pick = await vscode.window.showQuickPick(
    skills.map((s) => ({ label: s.name, description: s.source, detail: s.description, file: s.file })),
    { placeHolder: "Open a skill" }
  );
  return pick && pick.file;
}

async function pickCanvas(canvases) {
  const pick = await vscode.window.showQuickPick(
    canvases.map((c) => ({ label: c.name, description: c.project, detail: c.file, file: c.file })),
    { placeHolder: "Open a canvas" }
  );
  return pick && pick.file;
}

function deactivate() {
  // Servers and watchers the agent started in the background must not outlive CortexIDE.
  try {
    require("./lib/bg-shell").killAll();
  } catch {
    /* nothing running */
  }
}

module.exports = { activate, deactivate };
