"use strict";

// The Agent panel's chats (lib/agent-view.js) under the vscode stub with a scripted fake model:
// migration of the pre-2.7 single chat, two chats running side by side on different models,
// the maxParallel limit, per-chat event routing (sid), unread flags and per-chat Stop.

const fs = require("fs");
const os = require("os");
const path = require("path");
const assert = require("assert");
const { test, after, EXT } = require("./harness");
const { install } = require("./vscode-stub");

const home = fs.mkdtempSync(path.join(os.tmpdir(), "view-home-"));
const ws = fs.mkdtempSync(path.join(os.tmpdir(), "view-ws-"));
process.env.USERPROFILE = home;
after(() => {
  fs.rmSync(home, { recursive: true, force: true });
  fs.rmSync(ws, { recursive: true, force: true });
});

const settings = { "localAgentBridge.agent.provider": "vllm", "localAgentBridge.agent.maxParallel": 2 };
const stub = install({ workspace: ws, settings });
// A chat saved by 2.6 (one conversation in workspaceState).
stub.workspaceState.set("localAgentBridge.agent.conversation", {
  log: [{ cls: "user", text: "Old question from 2.6" }, { cls: "assistant", text: "old answer" }],
  history: [{ role: "user", content: "Old question from 2.6" }, { role: "assistant", content: "old answer" }],
  todos: [],
  progress: null,
});

// Fake backend: every model exists; each chat call waits until the test releases that model.
const llm = require(path.join(EXT, "lib", "llm"));
const real = { discover: llm.discover, pickModel: llm.pickModel, contextWindow: llm.contextWindow, chat: llm.chat };
after(() => Object.assign(llm, real));
llm.discover = async () => ({ provider: "vllm", label: "Fake", baseUrl: "http://fake", models: ["m-a", "m-b", "m-c"] });
llm.pickModel = (models, want) => want || models[0];
llm.contextWindow = async () => 32000;
const waiting = new Map(); // model → [release]
const scripted = new Map(); // model → [(req) => reply], answered at once before falling back to waiting
llm.chat = (req) =>
  scripted.get(req.model) && scripted.get(req.model).length ? Promise.resolve(scripted.get(req.model).shift()(req)) : new Promise((resolve) => {
    const list = waiting.get(req.model) || [];
    list.push(() =>
      resolve({ content: "", tool_calls: [{ id: "c-" + req.model, type: "function", function: { name: "attempt_completion", arguments: JSON.stringify({ summary: "done by " + req.model }) } }] })
    );
    waiting.set(req.model, list);
  });
const release = (model) => {
  const list = waiting.get(model) || [];
  waiting.delete(model);
  list.forEach((f) => f());
};

const ext = require(path.join(EXT, "extension.js"));
ext.activate(stub.makeContext(EXT));
const provider = stub.webviewProviders.get("localAgentBridge.agent");
const posted = [];
let onMsg;
provider.resolveWebviewView({
  webview: {
    options: {},
    html: "",
    asWebviewUri: (u) => u,
    cspSource: "x",
    onDidReceiveMessage: (f) => {
      onMsg = f;
      return stub.disposable;
    },
    postMessage: (m) => {
      posted.push(m);
      return Promise.resolve(true);
    },
  },
  onDidDispose: stub.noop,
  onDidChangeVisibility: stub.noop,
});

function waitFor(cond, ms = 5000) {
  const t0 = Date.now();
  return new Promise((resolve, reject) => {
    const tick = () => {
      if (cond()) resolve();
      else if (Date.now() - t0 > ms) reject(new Error("timed out"));
      else setTimeout(tick, 10);
    };
    tick();
  });
}

test("the 2.6 single chat is migrated into the history cache once", async () => {
  if (onMsg) await onMsg({ type: "ready" });
  const st = provider.store();
  const old = st.list().find((e) => e.title === "Old question from 2.6");
  assert.ok(old, "migrated: " + JSON.stringify(st.list()));
  assert.strictEqual(st.get(old.id).history.length, 2);
  assert.strictEqual(stub.workspaceState.get("localAgentBridge.agent.conversation"), undefined, "old key cleared");
  assert.ok(st.dir.startsWith(path.join(home, ".cortexide", "agent", "projects")), st.dir);
});

test("two chats run side by side on their own models; a third is held by maxParallel", async () => {
  const a = provider.createSession({ model: "m-a" });
  const b = provider.createSession({ model: "m-b" });
  const c = provider.createSession({ model: "m-c" });
  await provider.setActive(a.id);
  posted.length = 0;

  const pa = provider.send("task for A", a.id);
  const pb = provider.send("task for B", b.id);
  await waitFor(() => waiting.has("m-a") && waiting.has("m-b"));
  assert.strictEqual(provider.runs.size, 2);
  assert.strictEqual(provider.store().meta(a.id).status, "running");
  assert.strictEqual(provider.store().meta(b.id).status, "running");

  const warnsBefore = stub.messages.filter((m) => m.kind === "warn").length;
  await provider.send("task for C", c.id);
  assert.ok(!waiting.has("m-c"), "third chat must not start");
  assert.ok(stub.messages.filter((m) => m.kind === "warn").length > warnsBefore, "user is told why");
  assert.strictEqual(provider.store().get(c.id).log.length, 0);

  release("m-b"); // B (in the background) finishes first, A keeps running
  await pb;
  assert.strictEqual(provider.runs.size, 1);
  assert.ok(provider.runs.has(a.id));
  release("m-a");
  await pa;

  const sa = provider.store().get(a.id);
  const sb = provider.store().get(b.id);
  assert.deepStrictEqual([sa.status, sb.status], ["done", "done"]);
  assert.strictEqual(sa.history[1].content, "done by m-a");
  assert.strictEqual(sb.history[1].content, "done by m-b");
  assert.strictEqual(sa.title, "task for A");
  assert.strictEqual(sb.unread, true, "background chat finished unseen");
  assert.strictEqual(sa.unread, false, "chat on screen is not unread");

  // Every per-run event carries its chat id, so the panel can keep them apart.
  const runEvents = posted.filter((m) => ["user", "busy", "idle", "assistant"].includes(m.type));
  assert.ok(runEvents.length >= 6);
  assert.ok(runEvents.every((m) => [a.id, b.id, c.id].includes(m.sid)), JSON.stringify(runEvents.filter((m) => ![a.id, b.id, c.id].includes(m.sid))));
  assert.deepStrictEqual(runEvents.filter((m) => m.sid === c.id).map((m) => m.type), ["idle"], "the refused chat only gets its idle");
  assert.ok(runEvents.some((m) => m.type === "user" && m.sid === b.id && m.text === "task for B"));

  // Opening B clears its unread flag.
  await provider.setActive(b.id);
  assert.strictEqual(provider.store().meta(b.id).unread, false);
});

test("Stop ends only the chat it is aimed at", async () => {
  const a = provider.createSession({ model: "m-a" });
  const b = provider.createSession({ model: "m-b" });
  const pa = provider.send("long A", a.id);
  const pb = provider.send("long B", b.id);
  await waitFor(() => waiting.has("m-a") && waiting.has("m-b"));
  provider.stop(a.id);
  release("m-a"); // the fake ignores the signal; the loop must notice it after the reply
  await pa;
  assert.strictEqual(provider.store().meta(a.id).status, "stopped");
  assert.ok(provider.runs.has(b.id), "B still running");
  release("m-b");
  await pb;
  assert.strictEqual(provider.store().meta(b.id).status, "done");
});

const callTool = (name, args) => ({ content: "", tool_calls: [{ id: "t" + Math.random(), type: "function", function: { name, arguments: JSON.stringify(args) } }] });

test("two running chats cannot overwrite each other's files; each has its own progress and sub-index", async () => {
  const shared = path.join(ws, "shared.txt");
  const a = provider.createSession({ model: "m-a" });
  const b = provider.createSession({ model: "m-b" });
  let bSaw = "";
  scripted.set("m-a", [() => callTool("Write", { path: shared, contents: "from A\n" })]); // then waits
  scripted.set("m-b", [
    () => callTool("Write", { path: shared, contents: "from B\n" }),
    (req) => {
      bSaw = JSON.stringify(req.messages);
      // Accepted at once: its only edit was refused by A's claim, so "make the change first" does not apply.
      return callTool("attempt_completion", { summary: "left shared.txt to the other chat" });
    },
  ]);
  const pa = provider.send("write shared", a.id);
  await waitFor(() => waiting.has("m-a")); // A wrote the file and is still running
  assert.strictEqual(fs.readFileSync(shared, "utf8"), "from A\n");
  const st = provider.store();
  assert.deepStrictEqual(st.claimsOf(a.id).map((p) => p.toLowerCase()), [path.resolve(shared).toLowerCase()]);

  await provider.send("also write shared", b.id);
  assert.strictEqual(fs.readFileSync(shared, "utf8"), "from A\n", "B must not overwrite A's file");
  assert.ok(bSaw.includes("being changed by another chat"), "B's model is told why: " + bSaw.slice(0, 400));
  assert.ok(bSaw.includes("write shared"), "the refusal names A's chat");
  assert.strictEqual(st.meta(b.id).status, "done");

  release("m-a");
  await pa;
  assert.deepStrictEqual(st.claimsOf(a.id), [], "claims released when the turn ends");
  // Each chat has its own progress.md and sub-index; the workspace gets no shared progress file.
  assert.notStrictEqual(st.progressFile(a.id), st.progressFile(b.id));
  assert.ok(fs.existsSync(st.progressFile(a.id)) && fs.existsSync(st.progressFile(b.id)));
  assert.ok(!fs.existsSync(path.join(ws, ".cortexide", "agent", "progress.md")));
  assert.deepStrictEqual(Object.values(st.subIndex(a.id).files).map((f) => path.basename(f.path)), ["shared.txt"]);
  assert.deepStrictEqual(st.subIndex(b.id).files, {});
  const lastTurn = st.subIndex(a.id).turns.slice(-1)[0];
  assert.ok(lastTurn, "A's turn is recorded in its sub-index: " + JSON.stringify(st.subIndex(a.id)));
  assert.strictEqual(lastTurn.files.length, 1);
  // The master index lists this workspace folder.
  const master = JSON.parse(fs.readFileSync(st.masterFile(), "utf8"));
  assert.ok(master.workspaces.some((w) => w.dir === st.dir && w.chats >= 2));
});

test("each chat runs with its own output limits, side by side, and keeps them in its index", async () => {
  const a = provider.createSession({ model: "m-a" });
  const b = provider.createSession({ model: "m-b" });
  assert.deepStrictEqual(a.limits, { preset: "standard" }, "new chats start on defaultSessionLimits");
  await provider.setSessionLimits(b, { preset: "max" });
  assert.deepStrictEqual(provider.store().meta(b.id).limits, { preset: "max" }, "stored in the main index");
  const seen = {};
  const grab = (model) => (req) => {
    seen[model] = req.maxTokens;
    return callTool("attempt_completion", { summary: "ok " + model });
  };
  scripted.set("m-a", [grab("m-a")]);
  scripted.set("m-b", [grab("m-b")]);
  posted.length = 0;
  await Promise.all([provider.send("small job", a.id), provider.send("big job", b.id)]);
  assert.strictEqual(seen["m-a"], 2048, "standard chat: the maxOutputTokens setting");
  // Maximum is 16384 for local models, capped to half the fake 32000-token context.
  assert.strictEqual(seen["m-b"], 16000, "raised chat: its own limit");
  const note = posted.find((m) => m.sid === b.id && m.type === "status" && /Limits for this chat: Maximum/.test(m.text));
  assert.ok(note && /150 rounds/.test(note.text) && /half the 31k context/.test(note.text), JSON.stringify(note));
  assert.ok(!posted.some((m) => m.sid === a.id && /Limits for this chat/.test(m.text || "")), "standard chats say nothing");
  // The limits survive a reload from disk (sub-index is the source of truth for the header).
  assert.deepStrictEqual(provider.store().subIndex(b.id).limits || provider.store().get(b.id).limits, { preset: "max" });
  await provider.setActive(b.id);
  const info = posted.filter((m) => m.type === "info").pop();
  assert.ok(info && info.limitsPreset === "max", JSON.stringify(info));
});

test("right-click menu: open (at a line, to the side), reveal, copy, diff, and search by name", async () => {
  const { vscode } = stub;
  fs.mkdirSync(path.join(ws, "src", "deep"), { recursive: true });
  fs.writeFileSync(path.join(ws, "src", "deep", "util.js"), "a\nb\nc\n");
  fs.writeFileSync(path.join(ws, "shot.png"), "x");
  const calls = [];
  const saved = { std: vscode.window.showTextDocument, cmd: vscode.commands.executeCommand, clip: vscode.env.clipboard.writeText, ff: vscode.workspace.findFiles, rel: vscode.workspace.asRelativePath };
  vscode.Range = class { constructor(a, b, c, d) { Object.assign(this, { a, b, c, d }); } };
  vscode.window.showTextDocument = async (u, o) => calls.push(["show", u.fsPath, o]);
  vscode.commands.executeCommand = async (id, u, o) => calls.push([id, u && u.fsPath, o]);
  vscode.env.clipboard.writeText = async (t) => calls.push(["clip", t]);
  vscode.workspace.findFiles = async (glob) => (glob === "**/util.js" ? [vscode.Uri.file(path.join(ws, "src", "deep", "util.js"))] : []);
  vscode.workspace.asRelativePath = (u) => path.relative(ws, u.fsPath);
  try {
    const util = path.join(ws, "src", "deep", "util.js");
    await onMsg({ type: "file", action: "open", path: "src/deep/util.js:2:3" });
    assert.deepStrictEqual(calls.pop(), ["show", util, { preview: true, viewColumn: undefined, selection: new vscode.Range(1, 2, 1, 2) }]);
    await onMsg({ type: "file", action: "side", path: util, line: 3 });
    const side = calls.pop();
    assert.strictEqual(side[2].viewColumn, vscode.ViewColumn.Beside);
    assert.strictEqual(side[2].selection.a, 2);
    await onMsg({ type: "file", action: "open", path: "util.js" }); // only a name: found by searching the workspace
    assert.strictEqual(calls.pop()[1], util);
    await onMsg({ type: "file", action: "open", path: "shot.png" });
    assert.deepStrictEqual(calls.pop().slice(0, 2), ["vscode.open", path.join(ws, "shot.png")]);
    await onMsg({ type: "file", action: "reveal", path: "src/deep/util.js" });
    assert.deepStrictEqual(calls.pop().slice(0, 2), ["revealInExplorer", util]);
    await onMsg({ type: "file", action: "os", path: "src/deep/util.js" });
    assert.deepStrictEqual(calls.pop().slice(0, 2), ["revealFileInOS", util]);
    await onMsg({ type: "file", action: "copy", path: "src/deep/util.js" });
    assert.deepStrictEqual(calls.pop(), ["clip", util]);
    await onMsg({ type: "file", action: "copyRel", path: util });
    assert.deepStrictEqual(calls.pop(), ["clip", path.join("src", "deep", "util.js")]);
    await onMsg({ type: "file", action: "open", path: "src" }); // a folder is revealed, not opened
    assert.deepStrictEqual(calls.pop().slice(0, 2), ["revealInExplorer", path.join(ws, "src")]);
    const before = stub.messages.length;
    await onMsg({ type: "file", action: "open", path: "missing/nowhere.js" });
    assert.ok(calls.length === 0 && /can't find “missing\/nowhere\.js”/.test(stub.messages.slice(before).map((m) => m.text).join("\n")));
    await onMsg({ type: "file", action: "diff", path: util, id: "no-such-turn" }); // unknown turn: shows the file
    assert.deepStrictEqual(calls.pop().slice(0, 2), ["show", util]);
  } finally {
    vscode.window.showTextDocument = saved.std;
    vscode.commands.executeCommand = saved.cmd;
    vscode.env.clipboard.writeText = saved.clip;
    vscode.workspace.findFiles = saved.ff;
    vscode.workspace.asRelativePath = saved.rel;
    delete vscode.Range;
  }
});

test("sidebar tree: other workspace folders are listed; their chats open there, copy here, read or pin", async () => {
  const { vscode } = stub;
  const { SessionStore } = require(path.join(EXT, "lib", "sessions"));
  const otherWs = fs.mkdtempSync(path.join(os.tmpdir(), "view-other-"));
  const other = new SessionStore({ root: provider.store().root, workspace: otherWs });
  const fc = other.create({ title: "Foreign chat", model: "m-b" });
  other.save({ ...other.get(fc.id), log: [{ cls: "user", text: "fix the loader" }, { cls: "assistant", text: "fixed it" }], history: [{ role: "user", content: "fix the loader" }] });
  const saved = { qp: vscode.window.showQuickPick, cmd: vscode.commands.executeCommand, otd: vscode.workspace.openTextDocument };
  const calls = [];
  let choose = "";
  vscode.window.showQuickPick = async (items) => items.find((i) => i.act === choose);
  vscode.commands.executeCommand = async (id, u, o) => calls.push([id, u && u.fsPath, o]);
  vscode.workspace.openTextDocument = async (o) => (calls.push(["doc", o.content]), {});
  try {
    posted.length = 0;
    await onMsg({ type: "tree" });
    const tree = posted.filter((m) => m.type === "tree").pop();
    assert.ok(tree, "tree posted");
    const here = tree.items.find((w) => w.here);
    const there = tree.items.find((w) => w.workspace === otherWs);
    assert.ok(here && here.current && tree.items[0] === here, "this window's folder first: " + JSON.stringify(tree.items.map((w) => w.name)));
    assert.ok(there && !there.here && there.chats[0].title === "Foreign chat");

    choose = "window";
    await onMsg({ type: "foreign", slug: there.slug, id: fc.id });
    assert.deepStrictEqual(calls.pop(), ["vscode.openFolder", otherWs, { forceNewWindow: true }]);

    choose = "read";
    await onMsg({ type: "foreign", slug: there.slug, id: fc.id });
    const doc = calls.pop();
    assert.ok(doc[0] === "doc" && /# Foreign chat/.test(doc[1]) && /fix the loader/.test(doc[1]) && /fixed it/.test(doc[1]), doc[1]);

    choose = "copy";
    const before = provider.store().list().length;
    await onMsg({ type: "foreign", slug: there.slug, id: fc.id });
    const st = provider.store();
    assert.strictEqual(st.list().length, before + 1);
    const copy = st.get(provider.activeId);
    assert.strictEqual(copy.title, "Foreign chat");
    assert.strictEqual(copy.model, "m-b");
    assert.strictEqual(copy.importedFrom, otherWs);
    assert.strictEqual(copy.history[0].content, "fix the loader");
    assert.ok(copy.limits && copy.limits.preset, "default limits kept");
    assert.ok(other.get(fc.id), "the original stays in its folder");

    await onMsg({ type: "pinForeign", slug: there.slug, id: fc.id });
    assert.strictEqual(new SessionStore({ root: st.root, workspace: otherWs }).meta(fc.id).pinned, true);

    await onMsg({ type: "openFolder", path: otherWs });
    assert.deepStrictEqual(calls.pop(), ["vscode.openFolder", otherWs, { forceNewWindow: true }]);
  } finally {
    Object.assign(vscode.window, { showQuickPick: saved.qp });
    vscode.commands.executeCommand = saved.cmd;
    vscode.workspace.openTextDocument = saved.otd;
    fs.rmSync(otherWs, { recursive: true, force: true });
  }
});

test("the panel page draws the sidebar tree (folders, More, No agents yet) and parses", () => {
  const page = require(path.join(EXT, "lib", "agent-view")).html(EXT);
  for (const s of ['type: "tree"', "No agents yet", "nodesOf(", '"hfold"', "More (", 'type: "foreign"', "Start a chat here", 'type: "newIn"']) assert.ok(page.includes(s), s);
  const script = page.slice(page.lastIndexOf("<script>") + 8, page.lastIndexOf("</script>"));
  new Function("acquireVsCodeApi", "document", "window", script); // syntax check only
});

test("a handoff from another window's tree is taken once, only by the folder it names, and expires", () => {
  const { writeHandoff, takeHandoffFor } = require(path.join(EXT, "lib", "agent-view"));
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lab-handoff-"));
  try {
    writeHandoff(root, { workspace: "D:\\Proj\\One", action: "newChat" });
    writeHandoff(root, { workspace: "D:\\Proj\\Two", action: "newChat" });
    assert.strictEqual(takeHandoffFor(root, ["D:\\Other"]), null, "another folder does not take it");
    const h = takeHandoffFor(root, ["d:\\proj\\one"]);
    assert.ok(h && h.action === "newChat", "case-insensitive folder match");
    assert.strictEqual(takeHandoffFor(root, ["D:\\Proj\\One"]), null, "taken only once");
    const file = path.join(root, "handoff.json");
    const list = JSON.parse(fs.readFileSync(file, "utf8"));
    list[0].at = Date.now() - 10 * 60 * 1000;
    fs.writeFileSync(file, JSON.stringify(list));
    assert.strictEqual(takeHandoffFor(root, ["D:\\Proj\\Two"]), null, "an old handoff has expired");
    assert.ok(!fs.existsSync(file), "the file is removed when empty");
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("the panel page gets lib/file-ref.js inlined", () => {
  const page = require(path.join(EXT, "lib", "agent-view")).html(EXT);
  assert.ok(page.includes("var FileRef = (function") && !page.includes("/*@file-ref*/"));
  assert.ok(/addEventListener\("contextmenu"/.test(page));
});

const userRows = (id) => provider.store().get(id).log.filter((r) => r.cls === "user");
const dump = (id) => JSON.stringify(provider.store().get(id).log.map((r) => [r.cls, String(r.text || "").slice(0, 80), r.steered || r.command || ""]));

test("a message sent while a chat works steers that turn; it does not start a second one", async () => {
  const a = provider.createSession({ model: "m-a" });
  const p1 = provider.send("first", a.id);
  await waitFor(() => waiting.has("m-a"));
  await provider.send("second", a.id); // Enter while working = steer (the default)
  assert.strictEqual(waiting.get("m-a").length, 1, "no second model call started");
  release("m-a"); // its completion is held: a steering message is waiting
  await waitFor(() => waiting.has("m-a")); // round 2, with the steering taken in
  assert.strictEqual(waiting.get("m-a").length, 1);
  release("m-a");
  await p1;
  await waitFor(() => !provider.runs.has(a.id));
  const rows = userRows(a.id);
  assert.strictEqual(rows[0].text, "first", dump(a.id));
  assert.ok(rows.some((r) => r.steered && /second/.test(r.text)), "steered row in the log: " + dump(a.id));
});

test("/compress sent while a chat works waits for the turn, then compresses", async () => {
  const c = provider.createSession({ model: "m-q" });
  const p1 = provider.send("build the thing in parser.js", c.id);
  await waitFor(() => waiting.has("m-q"));
  posted.length = 0;
  await provider.send("/compress keep parser notes", c.id); // Enter (steer) on a command = after this turn
  const pend = posted.filter((m) => m.type === "pending" && m.sid === c.id).pop();
  assert.ok(pend && pend.items.length === 1 && pend.items[0].mode === "queue" && pend.items[0].command, JSON.stringify(pend));
  assert.ok(!posted.some((m) => m.type === "unsent"), "not bounced back to the input box");
  let asked = null;
  scripted.set("m-q", [(req) => ((asked = req), { content: "## Goal\nparser work\n## Recent work\nparser.js built", tool_calls: [] })]);
  release("m-q");
  await p1;
  await waitFor(() => { const s = provider.store().get(c.id); return s && s.history && s.history[0] && s.history[0].summary; });
  await waitFor(() => !provider.runs.has(c.id));
  assert.ok(asked && /keep parser notes/.test(asked.messages[asked.messages.length - 1].content), "focus passed on");
  assert.ok(/build the thing in parser\.js/.test(asked.messages[asked.messages.length - 1].content), "the finished turn is in the transcript");
  assert.ok(userRows(c.id).some((r) => r.command && /^\/compress/.test(r.text)), dump(c.id));
});

test("Stop & send with /compress stops the turn and compresses at once; messages sent meanwhile run after", async () => {
  const d = provider.createSession({ model: "m-r" });
  const p1 = provider.send("a long task in lexer.js", d.id);
  await waitFor(() => waiting.has("m-r"));
  let asked = null;
  scripted.set("m-r", [
    (req) => ((asked = req), { content: "## Recent work\nlexer.js half done (stopped)", tool_calls: [] }),
    () => ({ content: "", tool_calls: [{ id: "c", type: "function", function: { name: "attempt_completion", arguments: JSON.stringify({ summary: "carried on" }) } }] }),
  ]);
  await provider.send("/compress", d.id, "now");
  await provider.send("then carry on", d.id, "queue");
  release("m-r"); // the aborted call returns; the turn ends as stopped
  await p1;
  await waitFor(() => { const s = provider.store().get(d.id); return s && s.history && s.history.some((h) => h.summary); });
  assert.ok(asked && /a long task in lexer\.js/.test(asked.messages[asked.messages.length - 1].content), "the stopped turn is summarised");
  await waitFor(() => userRows(d.id).some((r) => r.text === "then carry on") && !provider.runs.has(d.id));
  const rows = userRows(d.id).map((r) => r.text);
  assert.ok(rows.indexOf("/compress") < rows.indexOf("then carry on"), dump(d.id));
});

test("/compress replaces the chat's history with a summary; the next turn is sent that summary", async () => {
  const a = provider.createSession({ model: "m-z" });
  const done = (text) => () => ({ content: "", tool_calls: [{ id: "c", type: "function", function: { name: "attempt_completion", arguments: JSON.stringify({ summary: text }) } }] });
  scripted.set("m-z", [done("answer one"), done("answer two")]);
  await provider.send("first task about parser.js", a.id);
  await provider.send("second task about lexer.js", a.id);
  let asked = null;
  scripted.set("m-z", [(req) => ((asked = req), { content: "## Goal\nparser and lexer work\n## Recent work\nlexer.js fixed", tool_calls: [] })]);
  await provider.send("/compress keep the lexer details", a.id);
  assert.ok(asked && !asked.tools, "summary call has no tools");
  const ask = asked.messages[asked.messages.length - 1].content;
  assert.ok(/second task about lexer\.js/.test(ask) && /first task about parser\.js/.test(ask), "both turns in the transcript");
  assert.ok(/keep the lexer details/.test(ask), "focus passed on");
  assert.ok(/Turn 2 \(recent\)/.test(ask), "latest turn marked recent");
  const s = provider.store().get(a.id);
  assert.strictEqual(s.history.length, 2, JSON.stringify(s.history));
  assert.ok(s.history[0].summary && /lexer\.js fixed/.test(s.history[0].content));
  assert.ok(s.log.some((e) => e.compressed), "marker in the log");
  // The next turn starts from the summary only.
  let next = null;
  scripted.set("m-z", [(req) => ((next = req), done("answer three")())]);
  await provider.send("third task", a.id);
  const sent = next.messages.map((m) => String(m.content)).join("\n");
  assert.ok(/lexer\.js fixed/.test(sent) && !/answer one/.test(sent), "history replaced by the summary: " + next.messages.filter((m) => /answer one/.test(String(m.content))).map((m) => m.role + ": " + String(m.content).slice(0, 1500)).join("\n---\n"));
  // An empty chat has nothing to compress and makes no model call.
  const b = provider.createSession({ model: "m-y" });
  await provider.send("/compact", b.id);
  assert.ok(!waiting.has("m-y"));
  assert.strictEqual(provider.store().get(b.id) ? provider.store().get(b.id).history.length : 0, 0);
});

test("auto-compact: a history near the context limit is compacted first, then the message runs on the summary", async () => {
  const a = provider.createSession({ model: "m-q" });
  const done = (text) => () => ({ content: "", tool_calls: [{ id: "c", type: "function", function: { name: "attempt_completion", arguments: JSON.stringify({ summary: text }) } }] });
  scripted.set("m-q", [done("answer one " + "a".repeat(900)), done("answer two " + "b".repeat(900))]);
  await provider.send("first task about parser.js", a.id);
  await provider.send("second task about lexer.js", a.id);
  settings["localAgentBridge.agent.autoCompactPercent"] = 1; // 1% of 32k tokens: the two turns are over it
  const reqs = [];
  scripted.set("m-q", [
    (req) => (reqs.push(req), { content: "<analysis>notes</analysis><summary>AUTO SUMMARY of parser and lexer</summary>", tool_calls: [] }),
    (req) => (reqs.push(req), done("answer three")()),
  ]);
  await provider.send("third task", a.id);
  for (let i = 0; i < 50 && reqs.length < 2; i++) await new Promise((r) => setTimeout(r, 20));
  for (let i = 0; i < 50 && provider.runs.has(a.id); i++) await new Promise((r) => setTimeout(r, 20));
  delete settings["localAgentBridge.agent.autoCompactPercent"];
  assert.strictEqual(reqs.length, 2, "a summary call, then the turn");
  assert.ok(!reqs[0].tools && /<transcript>/.test(reqs[0].messages[1].content), "first call is the summary");
  const sent = reqs[1].messages.map((m) => String(m.content)).join("\n");
  assert.ok(/AUTO SUMMARY/.test(sent) && !/answer one/.test(sent) && !/<analysis>/.test(sent), "the turn gets the summary, not the old history");
  assert.ok(/third task/.test(sent));
  const s = provider.store().get(a.id);
  const row = s.log.find((e) => e.cls === "compact");
  assert.ok(row && row.auto && row.turns === 2, JSON.stringify(row));
  assert.ok(s.log.findIndex((e) => e.cls === "compact") < s.log.findIndex((e) => e.cls === "user" && e.text === "third task"), "boundary before the message");
});

test("auto-switch: a struggling Ollama model hands the request to a stronger one, which reads the chat and the attempt", async () => {
  const saved = { discover: llm.discover, cands: llm.ollamaSwitchCandidates, advice: llm.ollamaToolAdvice, vision: llm.supportsVision };
  llm.discover = async (o) => (o.provider === "ollama" ? { provider: "ollama", label: "Ollama", baseUrl: "http://oll", models: ["weak:8b", "strong:14b"] } : saved.discover(o));
  llm.ollamaSwitchCandidates = async (base, current, { exclude }) => ["strong:14b"].filter((m) => !exclude.includes(m));
  llm.ollamaToolAdvice = async () => "";
  llm.supportsVision = async () => false;
  try {
    const s0 = provider.createSession({ provider: "ollama", baseUrl: "http://oll", model: "weak:8b" });
    scripted.set("weak:8b", [() => ({ content: "parser.js tokenises the input with a hand-written lexer.", tool_calls: [] })]);
    await provider.send("what does parser.js do?", s0.id);
    // The edit request: the weak model only announces, so it is reminded until it counts as struggling.
    scripted.set("weak:8b", Array.from({ length: 8 }, () => () => ({ content: "I will fix the bug in parser.js now.", tool_calls: [] })));
    let handed = null;
    const target = path.join(ws, "parser-fix.js");
    scripted.set("strong:14b", [
      (req) => ((handed = req), { content: "", tool_calls: [{ id: "w", type: "function", function: { name: "Write", arguments: JSON.stringify({ path: target, contents: "fixed\n" }) } }] }),
      () => ({ content: "", tool_calls: [{ id: "d", type: "function", function: { name: "attempt_completion", arguments: JSON.stringify({ summary: "fixed by strong" }) } }] }),
    ]);
    await provider.send("fix the bug in parser.js", s0.id);
    for (let i = 0; i < 100 && provider.runs.has(s0.id); i++) await new Promise((r) => setTimeout(r, 20));
    assert.ok(handed, "the stronger model ran");
    const sent = handed.messages.map((m) => String(m.content)).join("\n");
    assert.ok(/hand-written lexer/.test(sent), "it reads the earlier chat");
    assert.ok(/\[Handoff\] Another model \(weak:8b\)/.test(sent) && /I will fix the bug/.test(sent), "and the weak model's attempt: " + sent.slice(-1500));
    const s = provider.store().get(s0.id);
    assert.strictEqual(s.model, "strong:14b", "the chat keeps the stronger model");
    assert.ok(s.log.some((e) => e.switched && e.switched.from === "weak:8b" && e.switched.to === "strong:14b"));
    assert.strictEqual(fs.readFileSync(target, "utf8"), "fixed\n");
    assert.ok(s.history.some((h) => /fixed by strong/.test(h.content)));
  } finally {
    Object.assign(llm, { discover: saved.discover, ollamaSwitchCandidates: saved.cands, ollamaToolAdvice: saved.advice, supportsVision: saved.vision });
  }
});

test("memory: generated in the background after N turns, then in the next turn's prompt with the memory tools", async () => {
  settings["localAgentBridge.agent.memoryGenerateEvery"] = 2;
  try {
    const a = provider.createSession({ model: "m-mem" });
    const done = (text) => () => ({ content: "", tool_calls: [{ id: "c", type: "function", function: { name: "attempt_completion", arguments: JSON.stringify({ summary: text }) } }] });
    let extract = null;
    scripted.set("m-mem", [
      done("answer one"),
      done("answer two"),
      (req) => ((extract = req), { content: '[{"op":"add","scope":"user","name":"tests-with-run-js","type":"feedback","description":"how the user runs tests","body":"Run tests with node test/run.js."}]', tool_calls: [] }),
    ]);
    await provider.send("what does run.js do?", a.id);
    assert.strictEqual(extract, null, "not after one turn");
    await provider.send("I always run tests with node test/run.js", a.id);
    for (let i = 0; i < 100 && !provider.memory().find("tests-with-run-js"); i++) await new Promise((r) => setTimeout(r, 20));
    assert.ok(extract && /long-term memory/.test(extract.messages[0].content) && /node test\/run\.js/.test(extract.messages[1].content), "the extraction call read the turns");
    assert.ok(!extract.tools, "no tools on the extraction call");
    const m = provider.memory().find("tests-with-run-js");
    assert.ok(m && m.scope === "user" && m.type === "feedback");
    for (let i = 0; i < 50 && !(provider.store().get(a.id).log || []).some((e) => /^Memory added tests-with-run-js/.test(e.text || "")); i++) await new Promise((r) => setTimeout(r, 20));
    assert.ok(provider.store().get(a.id).log.some((e) => /^Memory added tests-with-run-js/.test(e.text || "")), "the chat notes it");
    let next = null;
    scripted.set("m-mem", [(req) => ((next = req), done("three")())]);
    await provider.send("third", a.id);
    assert.match(next.messages[0].content, /tests-with-run-js \(feedback\): Run tests with node test\/run\.js/);
    assert.ok(next.tools.some((t) => t.function.name === "MemoryWrite") && next.tools.some((t) => t.function.name === "ChatSearch"));
    settings["localAgentBridge.agent.memory"] = false;
    scripted.set("m-mem", [(req) => ((next = req), done("four")())]);
    await provider.send("fourth", a.id);
    assert.ok(!/tests-with-run-js/.test(next.messages[0].content) && !next.tools.some((t) => t.function.name === "MemoryWrite"), "memory off: none of it");
  } finally {
    delete settings["localAgentBridge.agent.memoryGenerateEvery"];
    delete settings["localAgentBridge.agent.memory"];
  }
});

test("a chat can work in another folder from this window: its tools, prompt and history are that folder's", async () => {
  const other = fs.mkdtempSync(path.join(os.tmpdir(), "view-other-"));
  after(() => fs.rmSync(other, { recursive: true, force: true }));
  fs.writeFileSync(path.join(other, "AGENTS.md"), "OTHER FOLDER RULES: use tabs.");
  const c = await provider.newChatInFolder(other);
  assert.strictEqual(c.workspace, other);
  assert.strictEqual(provider.store().get(c.id), null, "not in this window's history");
  assert.ok(provider.storeOf(other).get(c.id), "in the other folder's history");
  const listed = [...posted].reverse().find((m) => m.type === "sessions");
  const item = listed.items.find((e) => e.id === c.id);
  assert.ok(item && item.folder === path.basename(other) && item.open, "its tab shows here, with its folder");
  const restore = [...posted].reverse().find((m) => m.type === "restore" && m.sid === c.id);
  assert.strictEqual(restore.workspace, other, "the panel says where it works");
  let req = null;
  scripted.set(c.model || "m-a", []);
  const model = provider.session(c.id).model || "m-a";
  scripted.set(model, [
    (r) => ((req = r), { content: "", tool_calls: [{ id: "w", type: "function", function: { name: "Write", arguments: JSON.stringify({ path: "made.txt", contents: "hi\n" }) } }] }),
    () => ({ content: "", tool_calls: [{ id: "d", type: "function", function: { name: "attempt_completion", arguments: '{"summary":"made it"}' } }] }),
  ]);
  await provider.send("create made.txt", c.id);
  assert.ok(fs.existsSync(path.join(other, "made.txt")), "a relative path lands in the chat's folder");
  assert.ok(!fs.existsSync(path.join(ws, "made.txt")));
  const sys = req.messages[0].content;
  assert.ok(sys.includes("Workspace folders: " + other) && !sys.includes("Workspace folders: " + ws), "the prompt's workspace is the chat's folder");
  assert.match(sys, /OTHER FOLDER RULES/, "its AGENTS.md applies");
  assert.ok(provider.storeOf(other).get(c.id).history.some((h) => /made it/.test(h.content)), "the turn is saved in that folder's history");
  // The attachment survives a reload of this window's list; closing the tab detaches it.
  provider.attachedMap = null;
  assert.ok(provider.session(c.id), "found again from workspaceState");
  await provider.closeSession(c.id);
  assert.ok(!provider.attached().has(c.id));
  assert.ok(provider.storeOf(other).get(c.id), "still in its folder's history");
  // Clicking it in the tree opens it here again.
  await onMsg({ type: "attach", workspace: other, id: c.id });
  assert.strictEqual(provider.activeId, c.id);
  assert.ok(provider.attached().has(c.id));
});
