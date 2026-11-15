"use strict";

// MCP client: server resolution (settings, Cursor / Claude imports, REA auto-detect), a fake stdio
// server driven through McpTools / McpCall, and the agent loop offering those tools only when a
// server exists. The last test talks to the real REA server when Fetch-ThirdParty.ps1 installed it.

const fs = require("fs");
const os = require("os");
const path = require("path");
const assert = require("assert");
const { test, after, EXT } = require("./harness");
const mcpc = require(path.join(EXT, "lib", "mcp-client"));
const llm = require(path.join(EXT, "lib", "llm"));
const { runAgent, systemPrompt } = require(path.join(EXT, "lib", "agent"));
const { ToolContext, execToolRich } = require(path.join(EXT, "lib", "agent-tools"));

const realChat = llm.chat;
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "agent-mcp-"));
const hubs = [];
after(() => {
  llm.chat = realChat;
  for (const h of hubs) h.close();
  fs.rmSync(tmp, { recursive: true, force: true });
});

// A small MCP server: echo, an image tool, a failing tool, one that pings the client first, a slow one.
const FAKE = path.join(tmp, "fake-mcp.js");
fs.writeFileSync(
  FAKE,
  `
const tools = [
  { name: "echo", description: "Echo text back.\\nSecond line.", inputSchema: { type: "object", properties: { text: { type: "string" } }, required: ["text"] } },
  { name: "snap", description: "Return a picture", inputSchema: { type: "object", properties: {} } },
  { name: "boom", description: "Always fails", inputSchema: { type: "object", properties: {} } },
  { name: "roots", description: "Ask the client for its roots", inputSchema: { type: "object", properties: {} } },
  { name: "slow", description: "Never answers", inputSchema: { type: "object", properties: {} } },
];
let buf = "", waiting = null;
const send = (m) => process.stdout.write(JSON.stringify(m) + "\\n");
process.stdin.on("data", (d) => {
  buf += d;
  let i;
  while ((i = buf.indexOf("\\n")) >= 0) {
    const m = JSON.parse(buf.slice(0, i)); buf = buf.slice(i + 1);
    if (m.id === "srv1") { send({ jsonrpc: "2.0", id: waiting, result: { content: [{ type: "text", text: "roots: " + m.result.roots.map((r) => r.name).join(",") }] } }); continue; }
    if (m.method === "initialize") send({ jsonrpc: "2.0", id: m.id, result: { protocolVersion: m.params.protocolVersion, serverInfo: { name: "fake", version: "1" }, capabilities: { tools: {} } } });
    else if (m.method === "tools/list") send({ jsonrpc: "2.0", id: m.id, result: m.params.cursor ? { tools: tools.slice(3) } : { tools: tools.slice(0, 3), nextCursor: "p2" } });
    else if (m.method === "tools/call") {
      const n = m.params.name, a = m.params.arguments || {};
      if (n === "echo") send({ jsonrpc: "2.0", id: m.id, result: { content: [{ type: "text", text: "echo: " + a.text }] } });
      else if (n === "snap") send({ jsonrpc: "2.0", id: m.id, result: { content: [{ type: "text", text: "here" }, { type: "image", mimeType: "image/png", data: "QUJD" }] } });
      else if (n === "boom") send({ jsonrpc: "2.0", id: m.id, result: { isError: true, content: [{ type: "text", text: "kaput" }] } });
      else if (n === "roots") { waiting = m.id; send({ jsonrpc: "2.0", id: "srv1", method: "roots/list" }); }
      else if (n === "slow") {}
    }
  }
});
`
);

function hub(extra = {}) {
  const h = new mcpc.McpHub({ fake: { command: process.execPath, args: [FAKE], description: "test server" } }, { roots: [tmp], ...extra });
  hubs.push(h);
  return h;
}
const ctx = (o = {}) => new ToolContext({ roots: [tmp], rgPath: "missing-rg", mcp: hub(), ...o });

test("resolveServers: settings, imports, disabled, url-only and REA auto-detect", () => {
  const home = path.join(tmp, "home");
  fs.mkdirSync(path.join(home, ".cursor"), { recursive: true });
  fs.writeFileSync(path.join(home, ".cursor", "mcp.json"), JSON.stringify({ mcpServers: { cur: { command: "npx", args: ["-y", "x"] }, web: { url: "http://localhost:1/mcp" }, gone: { command: "a" } } }));
  fs.writeFileSync(path.join(home, ".claude.json"), JSON.stringify({ mcpServers: { cla: { command: "uvx", args: ["y"] } } }));
  const tp = path.join(tmp, "third_party");
  const rea = path.join(tp, "node", "node_modules", "rea-agents", "scripts", "rea.mjs");
  fs.mkdirSync(path.dirname(rea), { recursive: true });
  fs.writeFileSync(rea, "");

  const none = mcpc.resolveServers({ home, thirdParty: [] });
  assert.deepStrictEqual(Object.keys(none.specs), []);

  const r = mcpc.resolveServers({ home, imports: ["cursor", "claude"], configured: { mine: { command: "node", args: ["s.js"] }, gone: { disabled: true } }, thirdParty: [tp] });
  assert.deepStrictEqual(Object.keys(r.specs).sort(), ["cla", "cur", "mine", "rea"]);
  assert.deepStrictEqual(r.specs.rea.args, [rea, "mcp"]);
  assert.ok(r.skipped.some((s) => /^web .*HTTP/.test(s)), r.skipped.join("; "));

  const off = mcpc.resolveServers({ home, configured: { rea: { disabled: true } }, thirdParty: [tp] });
  assert.ok(!off.specs.rea, "rea: {disabled: true} turns off the auto-detected server");
  assert.ok(!mcpc.resolveServers({ home, autoRea: false, thirdParty: [tp] }).specs.rea);

  const dirs = mcpc.thirdPartyDirs("", [path.join(tmp, "nowhere"), path.dirname(tp)]);
  assert.ok(dirs.includes(tp));
});

test("findRea: a built source checkout wins over the npm package; an unbuilt one is skipped", () => {
  const tp = path.join(tmp, "tp-src");
  const pkg = path.join(tp, "node", "node_modules", "rea-agents", "scripts", "rea.mjs");
  const src = path.join(tp, "Reverse-Engineer-anything");
  fs.mkdirSync(path.dirname(pkg), { recursive: true });
  fs.writeFileSync(pkg, "");
  fs.mkdirSync(path.join(src, "scripts"), { recursive: true });
  fs.writeFileSync(path.join(src, "scripts", "rea.mjs"), "");
  assert.strictEqual(mcpc.findRea([tp]), pkg, "clone without dist / node_modules is not used");
  fs.mkdirSync(path.join(src, "dist"));
  assert.strictEqual(mcpc.findRea([tp]), pkg, "dist without node_modules is not used");
  fs.mkdirSync(path.join(src, "node_modules"));
  assert.strictEqual(mcpc.findRea([tp]), path.join(src, "scripts", "rea.mjs"));
});

test("needsShell: .cmd shims need a shell, node and .exe do not", () => {
  if (process.platform !== "win32") return;
  assert.strictEqual(mcpc.needsShell("npx"), true);
  assert.strictEqual(mcpc.needsShell("node"), false);
  assert.strictEqual(mcpc.needsShell("C:\\x\\tool.exe"), false);
});

test("McpTools: list servers, list tools across pages, search, show a schema", async () => {
  const c = ctx();
  const servers = (await execToolRich(c, "McpTools", {})).text;
  assert.match(servers, /- fake: test server/);
  const all = (await execToolRich(c, "McpTools", { server: "fake" })).text;
  for (const n of ["echo(text)", "snap()", "boom()", "roots()", "slow()"]) assert.ok(all.includes(n), all);
  assert.ok(!all.includes("Second line"), "listings show the first description line only");
  const hit = (await execToolRich(c, "mcp_tools", { query: "picture" })).text;
  assert.match(hit, /fake\.snap\(\)/);
  assert.ok(!/echo/.test(hit));
  const schema = (await execToolRich(c, "McpTools", { tool: "echo" })).text;
  assert.match(schema, /Server: fake/);
  assert.match(schema, /"required": \[\s*"text"\s*\]/);
  assert.match((await execToolRich(c, "McpTools", { tool: "ech" })).text, /^error: no tool named ech\. Similar: fake\.echo/);
});

test("McpCall: text, images (vision on / off), isError, missing args, unknown names", async () => {
  const c = ctx({ vision: true });
  assert.strictEqual((await execToolRich(c, "McpCall", { server: "fake", tool: "echo", arguments: { text: "hi" } })).text, "echo: hi");
  // Arguments sent as JSON text, and alias names, still work.
  assert.strictEqual((await execToolRich(c, "mcp_call", { server_name: "FAKE", tool_name: "echo", args: '{"text":"yo"}' })).text, "echo: yo");
  const pic = await execToolRich(c, "McpCall", { server: "fake", tool: "snap" });
  assert.strictEqual(pic.images.length, 1);
  assert.strictEqual(pic.images[0].mime, "image/png");
  assert.match(pic.text, /1 image\(s\) attached/);
  const blind = await execToolRich(ctx({ vision: false, model: "qwen2.5-coder" }), "McpCall", { server: "fake", tool: "snap" });
  assert.strictEqual(blind.images.length, 0);
  assert.match(blind.text, /qwen2\.5-coder cannot see images/);
  assert.match((await execToolRich(c, "McpCall", { server: "fake", tool: "boom" })).text, /^error: fake\.boom failed: kaput/);
  assert.match((await execToolRich(c, "McpCall", { server: "fake", tool: "echo", arguments: {} })).text, /^error: missing required argument\(s\) text/);
  assert.match((await execToolRich(c, "McpCall", { server: "nope", tool: "echo" })).text, /^error: no MCP server named nope\. Servers: fake/);
  assert.match((await execToolRich(c, "McpCall", { server: "fake", tool: "nope" })).text, /^error: fake has no tool nope/);
});

test("McpCall: answers the server's roots/list request; mcpMode off / confirm", async () => {
  assert.strictEqual((await execToolRich(ctx(), "McpCall", { server: "fake", tool: "roots" })).text, "roots: " + path.basename(tmp));
  assert.match((await execToolRich(ctx({ mcpMode: "off" }), "McpCall", { server: "fake", tool: "echo", arguments: { text: "x" } })).text, /turned off/);
  let asked = "";
  const no = ctx({ mcpMode: "confirm", confirmMcp: async (l) => ((asked = l), false) });
  assert.match((await execToolRich(no, "McpCall", { server: "fake", tool: "echo", arguments: { text: "x" } })).text, /declined/);
  assert.match(asked, /^fake\.echo \{"text":"x"\}/);
  const yes = ctx({ mcpMode: "confirm", confirmMcp: async () => true });
  assert.strictEqual((await execToolRich(yes, "McpCall", { server: "fake", tool: "echo", arguments: { text: "x" } })).text, "echo: x");
});

test("McpCall: Stop and timeouts end a call that never answers", async () => {
  const ac = new AbortController();
  const c = ctx({ signal: ac.signal });
  const p = execToolRich(c, "McpCall", { server: "fake", tool: "slow" });
  setTimeout(() => ac.abort(), 100);
  assert.match((await p).text, /^error: stopped/);
  const t = ctx({ mcpTimeoutSec: 5 });
  t.mcpTimeoutSec = 0.2; // below the setting's floor, to keep the test fast
  assert.match((await execToolRich(t, "McpCall", { server: "fake", tool: "slow" })).text, /timed out/);
});

test("a server that cannot start reports why, and a crashed one restarts", async () => {
  const bad = new mcpc.McpHub({ bad: { command: process.execPath, args: ["-e", "console.error('no license'); process.exit(3)"] } });
  hubs.push(bad);
  const c = new ToolContext({ roots: [tmp], rgPath: "missing-rg", mcp: bad });
  assert.match((await execToolRich(c, "McpCall", { server: "bad", tool: "x" })).text, /^error: MCP server bad exited \(code 3\):\nno license/);
  const h = hub();
  const s = h.server("fake");
  await s.listTools();
  s.proc.kill();
  await new Promise((r) => setTimeout(r, 200));
  const c2 = new ToolContext({ roots: [tmp], rgPath: "missing-rg", mcp: h });
  assert.strictEqual((await execToolRich(c2, "McpCall", { server: "fake", tool: "echo", arguments: { text: "back" } })).text, "echo: back");
});

test("agent loop: MCP tools are offered (and named in the prompt) only when a server exists", async () => {
  const seen = [];
  let i = 0;
  llm.chat = async (req) => {
    seen.push(req);
    i++;
    if (i === 1) return { content: "Asking the server.", tool_calls: [{ id: "m1", type: "function", function: { name: "McpCall", arguments: JSON.stringify({ server: "fake", tool: "echo", arguments: { text: "loop" } }) } }] };
    return { content: "", tool_calls: [{ id: "m2", type: "function", function: { name: "attempt_completion", arguments: '{"summary":"done"}' } }] };
  };
  const r = await runAgent({ backend: { provider: "vllm" }, model: "m", contextTokens: 32000, prompt: "what does the fake server say", tools: ctx(), env: { roots: [tmp] } });
  assert.strictEqual(r.text, "done");
  const names = seen[0].tools.map((t) => t.function.name);
  assert.ok(names.includes("McpTools") && names.includes("McpCall"));
  assert.match(seen[0].messages[0].content, /MCP servers \(find tools with McpTools[^\n]*\n- fake: test server/);
  const res = seen[1].messages.find((m) => m.role === "tool" && m.tool_call_id === "m1");
  assert.strictEqual(res.content, "echo: loop");

  i = 0;
  seen.length = 0;
  await runAgent({ backend: { provider: "vllm" }, model: "m", contextTokens: 32000, prompt: "hi", tools: new ToolContext({ roots: [tmp], rgPath: "missing-rg" }), env: { roots: [tmp] } });
  assert.ok(!seen[0].tools.some((t) => /^Mcp/.test(t.function.name)), "no MCP tools without servers");
  assert.ok(!/MCP servers/.test(systemPrompt({ env: {}, skills: [], task: "x", prior: "", textMode: false })));
});

test("REA (live, when Tools\\Shared\\third_party has it): starts and lists its tools", async () => {
  const tp = mcpc.thirdPartyDirs(process.env.AAMT_THIRD_PARTY || "", [path.resolve(EXT, "..", "..", "..")]);
  const { specs } = mcpc.resolveServers({ thirdParty: tp, home: tmp });
  if (!specs.rea) {
    console.log("    (skipped: REA not installed; run Tools\\Fetch-ThirdParty.ps1 -AgentBridge)");
    return;
  }
  const h = new mcpc.McpHub({ rea: specs.rea }, { roots: [tmp] });
  hubs.push(h);
  const c = new ToolContext({ roots: [tmp], rgPath: "missing-rg", mcp: h });
  const list = (await execToolRich(c, "McpTools", { server: "rea", query: "procedure" })).text;
  assert.match(list, /tool\(s\) on rea/, list.slice(0, 400));
  assert.ok((await h.server("rea").listTools()).length > 50);
});
