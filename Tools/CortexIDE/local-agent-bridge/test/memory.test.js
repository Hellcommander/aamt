"use strict";

// Memory between chats (lib/memory.js) and its agent tools: files + index per scope, the prompt
// section, generation operations, searching and reading past chats, import and export.

const fs = require("fs");
const os = require("os");
const path = require("path");
const zlib = require("zlib");
const assert = require("assert");
const { test, after, EXT } = require("./harness");
const mem = require(path.join(EXT, "lib", "memory"));
const { ToolContext, execTool } = require(path.join(EXT, "lib", "agent-tools"));
const llm = require(path.join(EXT, "lib", "llm"));
const { runAgent } = require(path.join(EXT, "lib", "agent"));

const root = fs.mkdtempSync(path.join(os.tmpdir(), "mem-root-"));
const projectDir = path.join(root, "projects", "d-games-Toolkit");
after(() => fs.rmSync(root, { recursive: true, force: true }));
const store = new mem.MemoryStore({ root, projectDir });

test("write / list / find / remove keep one file per fact and an index per scope", () => {
  const f1 = store.write({ scope: "user", name: "Prefers PowerShell", description: "shell examples in PowerShell", type: "feedback", body: "Use PowerShell.\nWhy: Windows.\nHow to apply: Shell examples." });
  assert.strictEqual(path.basename(f1), "prefers-powershell.md");
  store.write({ scope: "project", name: "no-commit-to-main", description: "branch first", type: "project", body: "Never commit to main." });
  assert.deepStrictEqual(store.list().map((m) => m.scope + "/" + m.name).sort(), ["project/no-commit-to-main", "user/prefers-powershell"]);
  assert.match(fs.readFileSync(path.join(root, "memory", "MEMORY.md"), "utf8"), /\[prefers-powershell\]\(prefers-powershell\.md\) \(feedback\) — shell examples/);
  store.write({ scope: "user", name: "prefers-powershell", description: "updated", type: "feedback", body: "PowerShell 7." });
  assert.strictEqual(store.list("user").length, 1, "same name replaces");
  assert.ok(store.remove("no-commit-to-main", "project"));
  assert.ok(!fs.existsSync(path.join(projectDir, "memory", "MEMORY.md")), "an empty index is removed");
  assert.strictEqual(store.remove("nope"), null);
});

test("the prompt section lists both scopes within its budget", () => {
  store.write({ scope: "project", name: "game-moved", type: "project", description: "Starfield now on D:", body: "Starfield moved from F:\\SteamLibrary to D:\\games\\Steam." });
  const p = store.promptText();
  assert.match(p, /About the user \(.*\):\n- prefers-powershell \(feedback\): PowerShell 7\./);
  assert.match(p, /About this project .*\n- game-moved \(project\): Starfield moved/);
  assert.ok(store.promptText({ maxChars: 200 }).length <= 200);
  assert.strictEqual(new mem.MemoryStore({ root: path.join(root, "empty") }).promptText(), "");
});

test("Claude Code memory files import as they are; existing names are kept", () => {
  const cc = path.join(root, "cc-memory");
  fs.mkdirSync(cc);
  fs.writeFileSync(path.join(cc, "MEMORY.md"), "- index");
  fs.writeFileSync(path.join(cc, "no-cursor-branding.md"), "---\nname: no-cursor-branding\ndescription: never put Cursor in tool names\nmetadata:\n  type: feedback\n---\n\nNever use Cursor in names.\n");
  fs.writeFileSync(path.join(cc, "game-moved.md"), "---\nname: game-moved\ndescription: other text\ntype: project\n---\nOTHER");
  const r = store.importFolder(cc, "project");
  assert.deepStrictEqual(r, { added: 1, skipped: 1 });
  const m = store.find("no-cursor-branding", "project");
  assert.strictEqual(m.type, "feedback");
  assert.strictEqual(m.body, "Never use Cursor in names.");
  assert.match(store.find("game-moved").body, /Starfield moved/, "not overwritten");
});

test("an answer pasted from another assistant becomes one memory per bullet", () => {
  const facts = mem.parsePasted("## About me\n- Works on game mods in C++ and Python\n- x\n## How I want you to respond\n1. Short answers, no emoji\n\nloose text is ignored");
  assert.strictEqual(facts.length, 2);
  assert.strictEqual(facts[0].type, "user");
  assert.match(facts[0].description, /^About me: Works on game mods/);
  assert.strictEqual(facts[1].type, "feedback");
  assert.match(mem.IMPORT_PROMPT, /Markdown/);
});

test("generation: operations are validated, secrets dropped, then applied", () => {
  const msgs = mem.extractionMessages({ transcript: "User: I always want tests run with node test/run.js", existing: store.list(), includeSensitive: false });
  assert.match(msgs[1].content, /Do not remember sensitive personal topics/);
  assert.match(msgs[1].content, /user\/prefers-powershell/);
  assert.match(mem.extractionMessages({ transcript: "", existing: [], includeSensitive: true })[1].content, /may be remembered/);
  const ops = mem.parseOperations('<think>x</think>Here: [{"op":"add","scope":"project","name":"Run Tests","type":"feedback","description":"how to test","body":"node test/run.js"},' +
    '{"op":"add","name":"key","body":"api key sk-ant-abcdefghijklmnop"},{"op":"delete","name":"game-moved","scope":"project"},{"op":"bogus","name":"x"}]');
  assert.deepStrictEqual(ops.map((o) => o.op + ":" + o.name), ["add:run-tests", "delete:game-moved"], "the secret and the bad op are dropped");
  const done = mem.applyOperations(store, ops);
  assert.deepStrictEqual(done, { added: ["run-tests"], updated: [], deleted: ["game-moved"] });
  assert.deepStrictEqual(mem.parseOperations("no json here"), []);
  assert.deepStrictEqual(mem.parseOperations("[]"), []);
});

test("export is a valid zip of the Markdown files", () => {
  const { zip, count } = store.exportZip();
  assert.strictEqual(count, store.list().length);
  // Walk the local headers and inflate each entry.
  const names = [];
  for (let at = 0; zip.readUInt32LE(at) === 0x04034b50; ) {
    const comp = zip.readUInt32LE(at + 18);
    const nlen = zip.readUInt16LE(at + 26);
    const name = zip.slice(at + 30, at + 30 + nlen).toString("utf8");
    const data = zlib.inflateRawSync(zip.slice(at + 30 + nlen, at + 30 + nlen + comp));
    assert.strictEqual(mem.crc32(data), zip.readUInt32LE(at + 14), name);
    names.push(name);
    at += 30 + nlen + comp;
  }
  assert.ok(names.includes("user/prefers-powershell.md") && names.includes("project/run-tests.md") && names.includes("user/MEMORY.md"), names.join(", "));
  assert.strictEqual(zip.readUInt32LE(zip.length - 22), 0x06054b50);
  assert.strictEqual(mem.crc32(Buffer.from("123456789")).toString(16), "cbf43926");
});

// Saved chats, laid out as the history cache does.
function saveChat(folder, id, title, log) {
  const dir = path.join(root, "projects", folder, "sessions", id);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "session.json"), JSON.stringify({ id, title, model: "qwen3:8b", log, history: [] }));
}
saveChat("d-games-Toolkit", "mw1aaaaa-x1", "Seal D2R audio", [{ cls: "user", text: "seal the d2r sounds with the game key" }, { cls: "assistant", text: "Sealed 12 sounds into test.mtsa with d2r.key." }]);
saveChat("d-games-Toolkit", "mw2bbbbb-x2", "Fix warlock crash", [{ cls: "user", text: "warlock crash on hit" }, { cls: "assistant", text: "srvdofunc 27 pointed at a missing missile" }]);
saveChat("f-Starfield", "mw3ccccc-x3", "Shadow vortex canvas", [{ cls: "user", text: "make a canvas for shadow vortex" }, { cls: "assistant", text: "canvas written" }]);

test("searching and reading past chats", () => {
  const h = mem.searchChats(root, "sealed d2r", { folder: "d-games-Toolkit" });
  assert.strictEqual(h.length, 1);
  assert.strictEqual(h[0].id, "mw1aaaaa-x1");
  assert.match(h[0].snippet, /Sealed 12 sounds/);
  assert.strictEqual(mem.searchChats(root, "canvas", { folder: "d-games-Toolkit" }).length, 0, "other workspaces only when asked");
  assert.strictEqual(mem.searchChats(root, "canvas").length, 1);
  assert.strictEqual(mem.searchChats(root, "warlock", { exclude: "mw2bbbbb-x2" }).length, 0, "the current chat is left out");
  assert.strictEqual(mem.findChat(root, "mw2bbb").id, "mw2bbbbb-x2", "an id prefix finds it");
});

test("agent tools: ChatSearch, ChatRead, MemoryWrite, MemoryDelete", async () => {
  const ctx = new ToolContext({ roots: [root] });
  assert.match(await execTool(ctx, "ChatSearch", { query: "warlock" }), /turned off/);
  ctx.chats = { root, folder: "d-games-Toolkit", current: "" };
  ctx.memory = store;
  let changed = 0;
  ctx.onMemory = () => changed++;
  const found = await execTool(ctx, "search_chats", { query: "warlock crash" });
  assert.match(found, /mw2bbbbb-x2 · \d{4}-\d\d-\d\d · Fix warlock crash/);
  assert.match(await execTool(ctx, "ChatSearch", { query: "shadow" }), /try all_workspaces/);
  assert.match(await execTool(ctx, "ChatSearch", { query: "shadow", all_workspaces: true }), /f-Starfield/);
  const read = await execTool(ctx, "ChatRead", { id: "mw2bbbbb" });
  assert.match(read, /Chat mw2bbbbb-x2 · Fix warlock crash/);
  assert.match(read, /srvdofunc 27/);
  assert.match(await execTool(ctx, "remember", { name: "likes-short-answers", body: "Keep answers short.", type: "feedback", scope: "user" }), /^saved memory .*likes-short-answers\.md/);
  assert.match(await execTool(ctx, "MemoryWrite", { name: "likes-short-answers", body: "Very short." }), /^updated memory/);
  assert.match(await execTool(ctx, "MemoryWrite", { name: "k", body: "token ghp_abcdefghijklmnopqrstuvwxyz123456" }), /looks like a secret/);
  assert.match(await execTool(ctx, "forget", { name: "likes-short-answers" }), /^deleted memory user\/likes-short-answers/);
  assert.match(await execTool(ctx, "MemoryDelete", { name: "nope" }), /^error: no memory named nope/);
  assert.strictEqual(changed, 3);
});

test("the agent loop offers memory and chat tools only when they are on, and puts memory in the prompt", async () => {
  const real = llm.chat;
  after(() => (llm.chat = real));
  const seen = [];
  llm.chat = async (req) => (seen.push(req), { content: "", tool_calls: [{ id: "c", type: "function", function: { name: "attempt_completion", arguments: '{"summary":"ok"}' } }] });
  const names = (req) => req.tools.map((t) => t.function.name);
  await runAgent({ backend: { provider: "vllm", baseUrl: "x" }, model: "m", prompt: "hi", tools: new ToolContext({ roots: [root] }), env: {} });
  assert.ok(!names(seen[0]).some((n) => /^(Memory|Chat)/.test(n)), names(seen[0]).join(","));
  const t = new ToolContext({ roots: [root] });
  t.memory = store;
  t.chats = { root, folder: "d-games-Toolkit" };
  await runAgent({ backend: { provider: "vllm", baseUrl: "x" }, model: "m", prompt: "hi", tools: t, env: { memory: store.promptText(), memoryOn: true, chatSearch: true } });
  assert.ok(["MemoryWrite", "MemoryDelete", "ChatSearch", "ChatRead"].every((n) => names(seen[1]).includes(n)));
  const sys = seen[1].messages[0].content;
  assert.match(sys, /Memory \(facts kept from earlier chats/);
  assert.match(sys, /prefers-powershell/);
  assert.match(sys, /save it with MemoryWrite/);
  assert.match(sys, /find it with ChatSearch/);
});
