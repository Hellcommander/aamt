"use strict";

// The New Tab page: it replaces the Welcome page when the Local Agent is shown, stays out of the
// way when files are open, follows localAgentBridge.newTab, and routes its buttons to the agent.

const fs = require("fs");
const os = require("os");
const path = require("path");
const assert = require("assert");
const { test, after, EXT } = require("./harness");
const { install } = require("./vscode-stub");

const ws = fs.mkdtempSync(path.join(os.tmpdir(), "home-ws-"));
after(() => fs.rmSync(ws, { recursive: true, force: true }));
const settings = {};
const stub = install({ workspace: ws, settings });
const { vscode } = stub;

// Tabs and webview panels, just enough for HomeTab.
let groups = [{ tabs: [] }];
const closed = [];
const panels = [];
vscode.window.tabGroups = {
  get all() {
    return groups;
  },
  close: async (tabs) => {
    closed.push(...tabs);
    for (const g of groups) g.tabs = g.tabs.filter((t) => !tabs.includes(t));
  },
};
vscode.ViewColumn = { One: 1, Beside: -2 };
vscode.window.createWebviewPanel = (viewType, title) => {
  const listeners = { msg: [], dispose: [] };
  const p = {
    viewType,
    title,
    visible: true,
    viewColumn: 1,
    posted: [],
    revealed: 0,
    webview: { options: {}, html: "", postMessage: (m) => p.posted.push(m), onDidReceiveMessage: (f) => listeners.msg.push(f) },
    reveal() {
      p.revealed++;
    },
    onDidChangeViewState: () => stub.disposable,
    onDidDispose: (f) => listeners.dispose.push(f),
    send: (m) => Promise.all(listeners.msg.map((f) => f(m))),
    dispose: () => listeners.dispose.forEach((f) => f()),
  };
  groups[0].tabs.push({ label: title, input: { viewType: "mainThreadWebview-" + viewType } });
  panels.push(p);
  return p;
};

const { HomeTab, page } = require(path.join(EXT, "lib", "home-tab"));
const calls = [];
const agent = {
  panelData: () => ({ tabs: [], canvases: [{ name: "Dash", file: "c.canvas.tsx" }], custom: [], recent: [{ id: "s1", title: "Fix build" }], ws: "Toolkit", changes: 2, backend: "Ollama · qwen3:8b" }),
  startFromHome: async (text, mode) => calls.push(["send", text, mode]),
  panelAction: async (m) => calls.push(["panel", m.id]),
  openChatFromHome: async (id) => calls.push(["chat", id]),
  focus: async () => calls.push(["focus"]),
  showHistory: async () => calls.push(["history"]),
  pickModel: async () => calls.push(["model"]),
  newChat: async () => calls.push(["new"]),
  post: (m) => calls.push(["post", m.type]),
};
const context = stub.makeContext(EXT);
const home = HomeTab.register(context, agent);
const welcome = () => ({ label: "Welcome", input: undefined });
const file = () => ({ label: "a.js", input: { uri: vscode.Uri.file(path.join(ws, "a.js")) } });
const reset = (tabs) => {
  if (home.panel) home.panel.dispose();
  groups = [{ tabs }];
  closed.length = 0;
};

test("the page loads with the composer inlined and no Cursor branding", () => {
  const html = page(EXT);
  assert.match(html, /Plan, search, build anything/);
  assert.match(html, /var Composer|const Composer|Composer =/);
  assert.doesNotMatch(fs.readFileSync(path.join(EXT, "media", "home.html"), "utf8"), /Cursor/);
});

test("showing the agent replaces the Welcome page", async () => {
  reset([welcome()]);
  await home.onAgentShown();
  assert.ok(home.panel, "page opened");
  assert.strictEqual(closed.length, 1);
  assert.strictEqual(closed[0].label, "Welcome");
});

test("an empty editor area gets the page; open files are left alone", async () => {
  reset([]);
  await home.onAgentShown();
  assert.ok(home.panel);
  reset([file()]);
  await home.onAgentShown();
  assert.strictEqual(home.panel, null, "not opened over the user's files");
  reset([file(), welcome()]);
  await home.onAgentShown();
  assert.ok(home.panel, "Welcome beside files is still swapped");
  assert.strictEqual(closed.length, 1);
});

test("newTab setting: always / off", async () => {
  settings["localAgentBridge.newTab"] = "off";
  reset([welcome()]);
  await home.onAgentShown();
  assert.strictEqual(home.panel, null);
  assert.strictEqual(closed.length, 0);
  settings["localAgentBridge.newTab"] = "always";
  reset([file()]);
  await home.onAgentShown();
  assert.ok(home.panel);
  delete settings["localAgentBridge.newTab"];
});

test("a second show reuses the page; the command reveals it", async () => {
  reset([]);
  await home.onAgentShown();
  const first = home.panel;
  await home.onAgentShown();
  assert.strictEqual(home.panel, first);
  await stub.commands.get("localAgentBridge.openHome")();
  assert.ok(first.revealed >= 1);
});

test("page messages reach the agent; data is posted on ready", async () => {
  reset([]);
  await home.open();
  const p = home.panel;
  await p.send({ type: "ready" });
  const d = p.posted.find((m) => m.type === "data");
  assert.strictEqual(d.ws, "Toolkit");
  assert.strictEqual(d.recent[0].title, "Fix build");
  calls.length = 0;
  await p.send({ type: "send", text: "add a test", mode: "plan" });
  await p.send({ type: "panel", id: "terminal" });
  await p.send({ type: "chat", id: "s1" });
  await p.send({ type: "history" });
  await p.send({ type: "newCanvas" });
  assert.deepStrictEqual(calls.map((c) => c.join(":")), ["send:add a test:plan", "panel:terminal", "chat:s1", "focus", "history", "focus", "new", "post:seed"]);
});
