"use strict";

// Steering (lib/steer.js): the per-chat queue, how commands are held back, the steering text,
// the cross-window inbox, finding running chats and sending to them, and the MCP tools
// list_running_chats / steer_chat. Also the composer helpers (lib/composer.js) behind drag and drop.

const fs = require("fs");
const os = require("os");
const path = require("path");
const assert = require("assert");
const { spawn } = require("child_process");
const { test, after, EXT } = require("./harness");
const steer = require(path.join(EXT, "lib", "steer"));
const Composer = require(path.join(EXT, "lib", "composer"));
const { SessionStore } = require(path.join(EXT, "lib", "sessions"));

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "lab-steer-"));
after(() => fs.rmSync(tmp, { recursive: true, force: true }));
let n = 0;

/** A history root with one running chat (owned by this process, so its pid is alive) and one idle chat. */
function rootWithChats() {
  const root = path.join(tmp, "r" + n++);
  const s = new SessionStore({ root, workspace: "D:\\games\\proj" });
  const run = s.create({ title: "Fix the build", model: "qwen3", status: "running" });
  s.save(run);
  const idle = s.create({ title: "Docs pass", model: "qwen3" });
  s.save(idle);
  return { root, s, run, idle };
}

test("modeFor: /compress and /compact sent as steer wait for the turn; other modes stay", () => {
  assert.strictEqual(steer.modeFor("fix b.js too", "steer"), "steer");
  assert.strictEqual(steer.modeFor("/compress keep API notes", "steer"), "queue");
  assert.strictEqual(steer.modeFor("/compact", "steer"), "queue");
  assert.strictEqual(steer.modeFor("/compress", "now"), "now");
  assert.strictEqual(steer.modeFor("hello", "bogus"), "steer");
  assert.ok(!steer.isCommand("/compressor") && !steer.isCommand("please /compress"));
});

test("SteerQueue: push, takeSteer only takes steering, setMode, remove, drain, listeners", () => {
  const q = new steer.SteerQueue();
  const seen = [];
  const off = q.onPush((it) => seen.push(it.text));
  assert.strictEqual(q.push("   "), null, "empty text is ignored");
  const a = q.push("use tabs", "steer", { from: "other window" });
  const b = q.push("then write docs", "queue");
  const c = q.push("/compress", "steer");
  assert.strictEqual(c.mode, "queue");
  assert.strictEqual(c.command, true);
  assert.deepStrictEqual(seen, ["use tabs", "then write docs", "/compress"]);
  assert.ok(q.hasSteer());
  const list = q.list();
  assert.deepStrictEqual(list.map((i) => [i.text, i.mode, i.from, i.command]), [["use tabs", "steer", "other window", false], ["then write docs", "queue", "", false], ["/compress", "queue", "", true]]);
  assert.deepStrictEqual(q.takeSteer().map((i) => i.id), [a.id]);
  assert.ok(!q.hasSteer() && q.size === 2);
  q.setMode(c.id, "steer");
  assert.strictEqual(q.list()[1].mode, "queue", "a command cannot be switched to steer");
  q.setMode(b.id, "steer");
  assert.ok(q.hasSteer());
  assert.strictEqual(q.remove(b.id).text, "then write docs");
  assert.strictEqual(q.remove("nope"), null);
  off();
  q.push("unheard");
  assert.strictEqual(seen.length, 3, "unsubscribed listener is not called");
  assert.strictEqual(q.drain().length, 2);
  assert.strictEqual(q.size, 0);
});

test("a listener that throws does not stop the push", () => {
  const q = new steer.SteerQueue();
  q.onPush(() => {
    throw new Error("boom");
  });
  assert.ok(q.push("still queued"));
  assert.strictEqual(q.size, 1);
});

test("steerMessage and withSteering describe what was added while working", () => {
  assert.strictEqual(steer.steerMessage([]), "");
  const m = steer.steerMessage([{ text: "also b.js" }, { text: "and c.js", from: "MCP" }]);
  assert.ok(/^\[New message from the user while you were working \(sent from MCP\)/.test(m), m);
  assert.ok(m.endsWith("also b.js\n\nand c.js"));
  assert.strictEqual(steer.withSteering("task", []), "task");
  assert.strictEqual(steer.withSteering("task", [{ text: "x" }, { text: " " }]), "task\n\n[Added while working] x");
});

test("inbox: messages are read oldest first, once, and bad files are dropped", () => {
  const dir = path.join(tmp, "chat" + n++);
  steer.postInbox(dir, { text: "first", mode: "queue", from: "w2" });
  steer.postInbox(dir, { text: "second", mode: "weird" });
  fs.writeFileSync(path.join(steer.inboxDir(dir), "00000000000000-bad.json"), "{not json");
  fs.writeFileSync(path.join(steer.inboxDir(dir), "half.json.tmp"), "{}");
  assert.throws(() => steer.postInbox(dir, { text: "  " }), /empty/);
  const got = steer.takeInbox(dir);
  assert.deepStrictEqual(got.map((m) => [m.text, m.mode, m.from]), [["first", "queue", "w2"], ["second", "steer", ""]]);
  assert.deepStrictEqual(steer.takeInbox(dir), [], "taken messages are gone");
  assert.ok(fs.existsSync(path.join(steer.inboxDir(dir), "half.json.tmp")), "a half-written message is left alone");
  assert.deepStrictEqual(steer.takeInbox(path.join(tmp, "missing")), []);
});

test("listRunning finds only running chats with a live owner, filtered by workspace", () => {
  const { root, run } = rootWithChats();
  const all = steer.listRunning({ root });
  assert.deepStrictEqual(all.map((c) => c.id), [run.id]);
  assert.strictEqual(all[0].title, "Fix the build");
  assert.strictEqual(steer.listRunning({ root, workspace: "d:\\games\\PROJ" }).length, 1, "workspace match ignores case");
  assert.strictEqual(steer.listRunning({ root, workspace: "D:\\other" }).length, 0);
  // A chat left "running" by a window that is gone does not count.
  const dead = new SessionStore({ root, workspace: "D:\\games\\proj", pid: 2147483000 });
  dead.save(dead.create({ title: "orphan", status: "running" }));
  assert.deepStrictEqual(steer.listRunning({ root }).map((c) => c.title), ["Fix the build"]);
});

test("sendExternal resolves id, id prefix, title or the only running chat, and posts to its inbox", () => {
  const { root, s, run } = rootWithChats();
  const r1 = steer.sendExternal({ root, id: run.id, text: "by id" });
  assert.strictEqual(r1.id, run.id);
  steer.sendExternal({ root, id: run.id.slice(0, 6), text: "by prefix", mode: "queue" });
  steer.sendExternal({ root, id: "the build", text: "by title" });
  steer.sendExternal({ root, text: "only one running", from: "cli" });
  const got = steer.takeInbox(s.chatDir(run.id));
  assert.deepStrictEqual(got.map((m) => [m.text, m.mode]), [["by id", "steer"], ["by prefix", "queue"], ["by title", "steer"], ["only one running", "steer"]]);
  assert.strictEqual(got[3].from, "cli");
  assert.throws(() => steer.sendExternal({ root, id: "Docs pass", text: "x" }), /No running chat matches “Docs pass”\. Running: /);
  s.save(s.create({ title: "Fix the tests", status: "running" }));
  assert.throws(() => steer.sendExternal({ root, id: "fix the", text: "x" }), /matches 2 running chats/);
  assert.throws(() => steer.sendExternal({ root, text: "x" }), /Name the chat: 2 are running/);
});

test("a steered message is not counted as a turn of its own", () => {
  const { s, idle } = rootWithChats();
  idle.log = [{ cls: "user", text: "task" }, { cls: "user", text: "also this", steered: true }, { cls: "assistant", text: "ok" }, { cls: "user", text: "next" }];
  s.save(idle);
  assert.strictEqual(idle.turns, 2);
});

/** Run the MCP server, send requests, return the replies by id. */
function mcp(env, requests) {
  return new Promise((resolve, reject) => {
    const p = spawn(process.execPath, [path.join(EXT, "mcp-server.js")], { env: { ...process.env, ...env }, stdio: ["pipe", "pipe", "pipe"] });
    const replies = {};
    let buf = "";
    const timer = setTimeout(() => {
      p.kill();
      reject(new Error("MCP server did not answer: " + buf));
    }, 15000);
    p.stdout.on("data", (d) => {
      buf += d;
      let i;
      while ((i = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, i).trim();
        buf = buf.slice(i + 1);
        if (!line) continue;
        const m = JSON.parse(line);
        replies[m.id] = m;
        if (Object.keys(replies).length === requests.length) {
          clearTimeout(timer);
          p.kill();
          resolve(replies);
        }
      }
    });
    p.on("error", reject);
    for (const r of requests) p.stdin.write(JSON.stringify({ jsonrpc: "2.0", ...r }) + "\n");
  });
}

test("MCP: list_running_chats and steer_chat reach a running chat's inbox", async () => {
  const { root, s, run } = rootWithChats();
  const r = await mcp({ AGENT_BRIDGE_HISTORY: root }, [
    { id: 1, method: "tools/list" },
    { id: 2, method: "tools/call", params: { name: "list_running_chats", arguments: {} } },
    { id: 3, method: "tools/call", params: { name: "steer_chat", arguments: { chat: "build", text: "also run the tests" } } },
    { id: 4, method: "tools/call", params: { name: "steer_chat", arguments: { text: "/compress", mode: "steer" } } },
    { id: 5, method: "tools/call", params: { name: "steer_chat", arguments: { chat: "zzz", text: "x" } } },
  ]);
  const names = r[1].result.tools.map((t) => t.name);
  assert.ok(names.includes("list_running_chats") && names.includes("steer_chat"), names.join(","));
  const listed = JSON.parse(r[2].result.content[0].text);
  assert.deepStrictEqual(listed.map((c) => c.id), [run.id]);
  assert.ok(/Sent to “Fix the build”.*next step/.test(r[3].result.content[0].text), r[3].result.content[0].text);
  assert.ok(/runs after the current turn/.test(r[4].result.content[0].text), "a command waits for the turn");
  assert.strictEqual(r[5].result.isError, true);
  assert.ok(/No running chat matches/.test(r[5].result.content[0].text));
  const got = steer.takeInbox(s.chatDir(run.id));
  assert.deepStrictEqual(got.map((m) => [m.text, m.mode, m.from]), [["also run the tests", "steer", "MCP"], ["/compress", "steer", "MCP"]]);
});

test("MCP: list_running_chats says so when nothing runs", async () => {
  const root = path.join(tmp, "empty" + n++);
  const r = await mcp({ AGENT_BRIDGE_HISTORY: root }, [{ id: 1, method: "tools/call", params: { name: "list_running_chats", arguments: {} } }]);
  assert.strictEqual(r[1].result.content[0].text, "No chat is running.");
});

test("composer: dropUris reads VS Code, uri-list, resourceurls and plain path drops", () => {
  const drop = (data) => Composer.dropUris((t) => data[t] || "");
  assert.deepStrictEqual(drop({ "application/vnd.code.uri-list": "file:///d%3A/a.js\r\nfile:///d%3A/b.js" }), ["file:///d%3A/a.js", "file:///d%3A/b.js"]);
  assert.deepStrictEqual(drop({ "text/uri-list": "# comment\nfile:///c/x.png\nfile:///c/x.png" }), ["file:///c/x.png"]);
  assert.deepStrictEqual(drop({ resourceurls: JSON.stringify(["file:///d/y.ts"]) }), ["file:///d/y.ts"]);
  assert.deepStrictEqual(drop({ "text/plain": "D:\\games\\a.txt\nC:/b.txt" }), ["D:\\games\\a.txt", "C:/b.txt"]);
  assert.deepStrictEqual(drop({ "text/plain": "just some words" }), [], "plain prose is not a file drop");
  assert.deepStrictEqual(drop({ resourceurls: "{not json" }), []);
});

test("composer: compose adds the mode, attached files once, and fenced context blocks", () => {
  assert.strictEqual(Composer.compose("hi", "agent", []), "hi");
  const t = Composer.compose(" fix it ", "plan", [{ path: "D:\\a.js" }, { path: "D:\\a.js" }, { path: "D:\\shot.png" }, { label: "Problems", text: "x ``` y" }]);
  const parts = t.split("\n\n");
  assert.ok(parts[0].startsWith("[Mode: Plan]"));
  assert.strictEqual(parts[1], "fix it");
  assert.strictEqual(parts[2], "[Attached files]\n- D:\\a.js\n- D:\\shot.png");
  assert.ok(parts[3].startsWith("[Problems]\n```\n") && !/x ``` y/.test(parts[3]), "a fence inside pasted text cannot close the block");
  assert.ok(Composer.IMAGE.test("shot.PNG") && !Composer.IMAGE.test("a.js"));
});

test("composer: safeName strips folders, reserved characters and leading dots", () => {
  assert.strictEqual(Composer.safeName("C:\\x\\..\\evil:name?.png"), "evil_name_.png");
  assert.strictEqual(Composer.safeName("../../.hidden"), "hidden");
  assert.strictEqual(Composer.safeName(""), "attachment");
  assert.ok(Composer.safeName("a".repeat(300) + ".png").length <= 120);
});
