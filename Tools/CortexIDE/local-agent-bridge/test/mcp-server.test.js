"use strict";

// Drives mcp-server.js over stdio the way MCP clients do (newline-delimited JSON),
// plus the legacy Content-Length framing it still answers.

const fs = require("fs");
const os = require("os");
const path = require("path");
const assert = require("assert");
const { spawn } = require("child_process");
const { test, after, EXT } = require("./harness");

const home = fs.mkdtempSync(path.join(os.tmpdir(), "mcp-home-"));
const ws = fs.mkdtempSync(path.join(os.tmpdir(), "mcp-ws-"));
fs.mkdirSync(path.join(ws, ".cursor", "skills", "demo"), { recursive: true });
fs.writeFileSync(path.join(ws, ".cursor", "skills", "demo", "SKILL.md"), "---\nname: demo\ndescription: Demo skill for tests\n---\n\nDo the demo thing.\n");
fs.mkdirSync(path.join(ws, "canvases"));
fs.writeFileSync(path.join(ws, "canvases", "board.canvas.tsx"), "export default function Board() { return null; }\n");

const servers = [];
after(() => {
  for (const s of servers) s.child.kill();
  fs.rmSync(home, { recursive: true, force: true });
  fs.rmSync(ws, { recursive: true, force: true });
});

function startServer() {
  const child = spawn(process.execPath, [path.join(EXT, "mcp-server.js")], {
    env: { ...process.env, USERPROFILE: home, HOME: home, AGENT_BRIDGE_WORKSPACE: ws },
    stdio: ["pipe", "pipe", "pipe"],
  });
  const s = { child, raw: "", waiters: [] };
  child.stdout.on("data", (c) => {
    s.raw += c.toString("utf8");
    s.waiters.splice(0).forEach((w) => w());
  });
  servers.push(s);
  return s;
}

/** Resolve once `pick(raw)` returns a value, re-checking on each stdout chunk. */
function waitFor(s, pick, ms = 5000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("timed out; stdout so far: " + JSON.stringify(s.raw))), ms);
    const check = () => {
      const v = pick();
      if (v !== undefined) {
        clearTimeout(timer);
        resolve(v);
      } else s.waiters.push(check);
    };
    check();
  });
}

/** Next newline-delimited message. */
function nextLine(s) {
  return waitFor(s, () => {
    const nl = s.raw.indexOf("\n");
    if (nl < 0) return undefined;
    const line = s.raw.slice(0, nl);
    s.raw = s.raw.slice(nl + 1);
    return JSON.parse(line);
  });
}

/** Next Content-Length framed message. */
function nextFramed(s) {
  return waitFor(s, () => {
    const m = /^Content-Length: (\d+)\r\n\r\n/.exec(s.raw);
    if (!m) return undefined;
    const body = Buffer.from(s.raw.slice(m[0].length), "utf8");
    const len = Number(m[1]);
    if (body.length < len) return undefined;
    s.raw = body.slice(len).toString("utf8");
    return JSON.parse(body.slice(0, len).toString("utf8"));
  });
}

let id = 0;
function send(s, method, params) {
  const msg = { jsonrpc: "2.0", id: ++id, method, params };
  s.child.stdin.write(JSON.stringify(msg) + "\n");
  return msg.id;
}

async function call(s, method, params) {
  const sent = send(s, method, params);
  const reply = await nextLine(s);
  assert.strictEqual(reply.id, sent, "reply id");
  return reply;
}

const text = (reply) => reply.result.content.map((c) => c.text).join("\n");

const nd = startServer();

test("initialize handshake (newline-delimited)", async () => {
  const sent = send(nd, "initialize", { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "test", version: "0" } });
  await waitFor(nd, () => (nd.raw.includes("\n") ? true : undefined));
  assert.ok(!nd.raw.startsWith("Content-Length"), "no LSP header on ndjson replies: " + nd.raw);
  const r = await nextLine(nd);
  assert.strictEqual(r.id, sent);
  assert.strictEqual(r.result.protocolVersion, "2025-06-18");
  assert.deepStrictEqual(r.result.serverInfo, { name: "local-agent-bridge", version: "2.1.0" });
  assert.ok(r.result.capabilities.tools);
});

test("notifications get no reply", async () => {
  nd.child.stdin.write(JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" }) + "\n");
  const r = await call(nd, "ping", {});
  assert.deepStrictEqual(r.result, {});
});

test("tools/list", async () => {
  const r = await call(nd, "tools/list", {});
  assert.deepStrictEqual(r.result.tools.map((t) => t.name).sort(), [
    "import_cursor_chat", "list_canvases", "list_imported_chats", "list_skills", "match_skills", "read_canvas", "read_skill",
  ]);
  for (const t of r.result.tools) assert.strictEqual(t.inputSchema.type, "object", t.name);
});

test("tools/call list_skills / read_skill / match_skills", async () => {
  assert.ok(JSON.parse(text(await call(nd, "tools/call", { name: "list_skills", arguments: {} }))).some((s) => s.name === "demo"));
  assert.ok(text(await call(nd, "tools/call", { name: "read_skill", arguments: { name: "DEMO" } })).includes("Do the demo thing."));
  const miss = await call(nd, "tools/call", { name: "read_skill", arguments: { name: "nope" } });
  assert.strictEqual(miss.result.isError, true);
  assert.strictEqual(JSON.parse(text(await call(nd, "tools/call", { name: "match_skills", arguments: { query: "demo" } })))[0].name, "demo");
});

test("tools/call list_canvases / read_canvas", async () => {
  const list = JSON.parse(text(await call(nd, "tools/call", { name: "list_canvases", arguments: {} })));
  assert.ok(list.some((c) => c.name === "board"), JSON.stringify(list));
  assert.ok(text(await call(nd, "tools/call", { name: "read_canvas", arguments: { name: "board" } })).includes("function Board"));
});

test("tools/call list_imported_chats on an empty workspace", async () => {
  assert.deepStrictEqual(JSON.parse(text(await call(nd, "tools/call", { name: "list_imported_chats", arguments: {} }))), []);
});

test("unknown method and unknown tool", async () => {
  const r = await call(nd, "resources/list", {});
  assert.strictEqual(r.error.code, -32601);
  const t = await call(nd, "tools/call", { name: "teleport", arguments: {} });
  assert.strictEqual(t.result.isError, true);
});

test("message split across chunks", async () => {
  const line = JSON.stringify({ jsonrpc: "2.0", id: ++id, method: "ping" }) + "\n";
  nd.child.stdin.write(line.slice(0, 10));
  await new Promise((r) => setTimeout(r, 100));
  nd.child.stdin.write(line.slice(10));
  assert.strictEqual((await nextLine(nd)).id, id);
});

test("two messages in one chunk, CRLF line ends", async () => {
  const a = ++id;
  const b = ++id;
  nd.child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id: a, method: "ping" }) + "\r\n" + JSON.stringify({ jsonrpc: "2.0", id: b, method: "ping" }) + "\r\n");
  assert.strictEqual((await nextLine(nd)).id, a);
  assert.strictEqual((await nextLine(nd)).id, b);
});

test("Content-Length framed client gets framed replies", async () => {
  const lsp = startServer();
  const body = JSON.stringify({ jsonrpc: "2.0", id: 1, method: "initialize", params: {} });
  lsp.child.stdin.write("Content-Length: " + Buffer.byteLength(body) + "\r\n\r\n" + body);
  const r = await nextFramed(lsp);
  assert.strictEqual(r.id, 1);
  assert.strictEqual(r.result.protocolVersion, "2024-11-05");
  const list = JSON.stringify({ jsonrpc: "2.0", id: 2, method: "tools/list" });
  lsp.child.stdin.write("Content-Length: " + Buffer.byteLength(list) + "\r\n\r\n" + list);
  assert.strictEqual((await nextFramed(lsp)).result.tools.length, 7);
});
