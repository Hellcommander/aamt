"use strict";

// Guards for weak local models: no text edits on binary files, a syntax check after JSON / XML
// edits, thinking switched off after it ate the output budget, the check nudge limited to the
// project it belongs to, and the Ollama "this model cannot call tools" advice.

const fs = require("fs");
const os = require("os");
const http = require("http");
const path = require("path");
const assert = require("assert");
const { test, after, EXT } = require("./harness");
const { ToolContext, execTool, syntaxProblem } = require(path.join(EXT, "lib", "agent-tools"));
const llm = require(path.join(EXT, "lib", "llm"));
const { runAgent } = require(path.join(EXT, "lib", "agent"));

const ws = fs.mkdtempSync(path.join(os.tmpdir(), "agent-local-"));
const outside = fs.mkdtempSync(path.join(os.tmpdir(), "agent-mods-"));
const realChat = llm.chat;
after(() => {
  llm.chat = realChat;
  fs.rmSync(ws, { recursive: true, force: true });
  fs.rmSync(outside, { recursive: true, force: true });
});
const ctx = new ToolContext({ roots: [ws], writableRoots: [outside], requireRead: false });

test("Write / StrReplace refuse binary files", async () => {
  fs.writeFileSync(path.join(ws, "plugin.dll"), Buffer.from([0x4d, 0x5a, 0, 0, 1, 2]));
  fs.writeFileSync(path.join(ws, "blob.cfg"), Buffer.from([0x61, 0, 0x62]));
  assert.match(await execTool(ctx, "Write", { path: "plugin.dll", contents: "patched" }), /binary file.*Copy-Item/);
  assert.match(await execTool(ctx, "Write", { path: "new.dll", contents: "x" }), /binary file/, "a new .dll is refused too");
  assert.match(await execTool(ctx, "StrReplace", { path: "blob.cfg", old_string: "a", new_string: "c" }), /binary file/, "NUL bytes mark a binary");
  assert.deepStrictEqual([...fs.readFileSync(path.join(ws, "plugin.dll"))], [0x4d, 0x5a, 0, 0, 1, 2]);
  assert.match(await execTool(ctx, "Write", { path: "ok.js", contents: "let a = 1;\n" }), /^created/);
});

test("JSON and XML edits that break the file say so", async () => {
  assert.strictEqual(syntaxProblem("a.json", '{ "a": 1 }'), "");
  assert.strictEqual(syntaxProblem("tsconfig.json", '{ // c\n "a": [1, 2,], }'), "", "comments and trailing commas pass");
  assert.match(syntaxProblem("a.json", '{ "a": 1,\n "b" }'), /no longer valid JSON/);
  assert.strictEqual(syntaxProblem("t.xml", '<?xml version="1.0"?>\n<a x="1"><b/><!-- <c> --><c>t</c></a>'), "");
  assert.match(syntaxProblem("t.xml", "<skilltree>\n</skill>"), /<\/skill> on line 2 closes <skilltree> from line 1/);
  assert.match(syntaxProblem("t.xml", "<a>\n<b>\n</a>"), /closes <b>/);
  assert.match(syntaxProblem("t.xml", "<a><b></b>"), /<a> on line 1 is never closed/);
  fs.writeFileSync(path.join(ws, "tree.xml"), '<skilltree name="x">\n  <skill/>\n</skilltree>\n');
  const r = await execTool(ctx, "StrReplace", { path: "tree.xml", old_string: '<skilltree name="x">', new_string: "</skilltree>" });
  assert.match(r, /\[check\] XML/);
});

/** Scripted model: each step gets the request and returns a reply. */
function script(steps) {
  const seen = [];
  llm.chat = async (req) => {
    seen.push(req);
    const step = steps[Math.min(seen.length - 1, steps.length - 1)];
    return typeof step === "function" ? step(req) : step;
  };
  return seen;
}
const call = (name, args) => ({ content: "", tool_calls: [{ id: "c" + Math.random().toString(36).slice(2), type: "function", function: { name, arguments: JSON.stringify(args) } }] });

test("Ollama: thinking that fills the output budget is switched off for the rest of the turn", async () => {
  const events = [];
  const seen = script([
    { content: "", reasoning: "hmm ".repeat(500), truncated: true },
    call("attempt_completion", { summary: "answered" }),
  ]);
  const r = await runAgent({
    backend: { provider: "ollama", baseUrl: "http://x" },
    model: "qwen3:8b",
    prompt: "what does this repo do?",
    tools: new ToolContext({ roots: [ws] }),
    env: {},
    onEvent: (e) => events.push(e),
  });
  assert.strictEqual(r.text, "answered");
  assert.strictEqual(seen[0].think, undefined);
  assert.strictEqual(seen[1].think, false);
  assert.ok(events.some((e) => e.type === "status" && /thinking is off/.test(e.text)));
});

test("a 'token repeat limit reached' abort retries the step with a repetition penalty", async () => {
  const events = [];
  let n = 0;
  const seen = script([
    () => {
      n++;
      throw new Error("prediction aborted, token repeat limit reached");
    },
    call("attempt_completion", { summary: "recovered" }),
  ]);
  const r = await runAgent({
    backend: { provider: "ollama", baseUrl: "http://x" },
    model: "qwen3:8b",
    prompt: "what does this repo do?",
    tools: new ToolContext({ roots: [ws] }),
    env: {},
    onEvent: (e) => events.push(e),
  });
  assert.strictEqual(r.text, "recovered");
  assert.strictEqual(n, 1);
  assert.strictEqual(seen[0].repeatPenalty, undefined);
  assert.ok(seen[1].repeatPenalty > 1 && seen[1].temperature > 0.2);
  assert.ok(events.some((e) => e.type === "status" && /stuck repeating/.test(e.text)));
});

test("check nudge only for files inside the project the check belongs to", async () => {
  const run = async (file) => {
    const events = [];
    script([call("Write", { path: file, contents: "let x = 1;\n" }), call("attempt_completion", { summary: "done" }), call("attempt_completion", { summary: "done" })]);
    await runAgent({
      backend: { provider: "ollama", baseUrl: "http://x" },
      model: "m",
      prompt: "make the change",
      tools: new ToolContext({ roots: [ws], writableRoots: [outside] }),
      env: { roots: [ws], checks: ["npm test"] },
      onEvent: (e) => events.push(e),
    });
    return events.some((e) => e.type === "status" && /Completion rejected .*npm test/.test(e.text));
  };
  assert.strictEqual(await run(path.join(outside, "mod.js")), false, "a mod folder outside the workspace is not checked with npm test");
  assert.strictEqual(await run(path.join(ws, "src.js")), true, "a workspace file is");
});

test("Ollama advice names tool-capable models when the chosen one cannot call tools", async () => {
  const caps = { "bakllava:latest": ["completion", "vision"], "qwen3:8b": ["completion", "tools", "thinking"], "nomic-embed-text:latest": ["embedding"], "qwen2.5-coder:14b": ["completion", "tools"] };
  const server = http.createServer((req, res) => {
    const chunks = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", () => {
      res.writeHead(200, { "Content-Type": "application/json" });
      if (req.url === "/api/tags") return res.end(JSON.stringify({ models: Object.keys(caps).map((name) => ({ name })) }));
      const body = JSON.parse(Buffer.concat(chunks).toString("utf8"));
      res.end(JSON.stringify({ capabilities: caps[body.model] || [] }));
    });
  });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const base = "http://127.0.0.1:" + server.address().port;
  try {
    const advice = await llm.ollamaToolAdvice(base, "bakllava:latest");
    assert.match(advice, /bakllava:latest cannot call tools/);
    assert.match(advice, /qwen2\.5-coder:14b, qwen3:8b/);
    assert.doesNotMatch(advice, /nomic/);
    assert.strictEqual(await llm.ollamaToolAdvice(base, "qwen3:8b"), "");
  } finally {
    server.close();
  }
});
