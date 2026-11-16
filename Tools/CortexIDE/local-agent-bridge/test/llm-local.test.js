"use strict";

// Local backends (Ollama native /api/chat, OpenAI-compatible /chat/completions) against mock
// servers: streaming (NDJSON / SSE), split tool-call fragments, reasoning kept apart from the
// answer, plain-JSON fallback, truncation, and the ToolsUnsupported switch.

const assert = require("assert");
const http = require("http");
const path = require("path");
const { test, after, EXT } = require("./harness");
const llm = require(path.join(EXT, "lib", "llm"));
const { TOOL_DEFS } = require(path.join(EXT, "lib", "agent-tools"));

let handler = null; // (body, req, res) => void
const bodies = [];
const server = http.createServer((req, res) => {
  const chunks = [];
  req.on("data", (c) => chunks.push(c));
  req.on("end", () => {
    const body = chunks.length ? JSON.parse(Buffer.concat(chunks).toString("utf8")) : null;
    bodies.push({ url: req.url, body });
    handler(body, req, res);
  });
});
let base = "";
const ready = new Promise((r) => server.listen(0, "127.0.0.1", () => {
  base = "http://127.0.0.1:" + server.address().port;
  r();
}));
after(() => server.close());

function ndjson(res, objs) {
  res.writeHead(200, { "Content-Type": "application/x-ndjson" });
  for (const o of objs) res.write(JSON.stringify(o) + "\n");
  res.end();
}
function sse(res, objs) {
  res.writeHead(200, { "Content-Type": "text/event-stream" });
  for (const o of objs) res.write("data: " + (typeof o === "string" ? o : JSON.stringify(o)) + "\n\n");
  res.end();
}
function json(res, status, o) {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(o));
}

const msgs = [{ role: "system", content: "S" }, { role: "user", content: "fix it" }];

test("Ollama: streamed content, separate thinking, tool call, usage", async () => {
  await ready;
  handler = (body, req, res) =>
    ndjson(res, [
      { message: { role: "assistant", content: "", thinking: "Hmm, " } },
      { message: { role: "assistant", content: "", thinking: "math.js." } },
      { message: { role: "assistant", content: "Reading " } },
      { message: { role: "assistant", content: "it.", tool_calls: [{ function: { name: "Read", arguments: { path: "math.js" } } }] } },
      { message: { role: "assistant", content: "" }, done: true, done_reason: "stop", prompt_eval_count: 321, eval_count: 12 },
    ]);
  let text = "";
  let thought = "";
  const r = await llm.chat({
    backend: { provider: "ollama", baseUrl: base + "/v1" },
    model: "qwen3:8b",
    messages: msgs,
    tools: TOOL_DEFS,
    numCtx: 16384,
    onText: (t) => (text += t),
    onReasoning: (t) => (thought += t),
  });
  const sent = bodies[bodies.length - 1];
  assert.strictEqual(sent.url, "/api/chat");
  assert.strictEqual(sent.body.stream, true);
  assert.strictEqual(sent.body.options.num_ctx, 16384);
  assert.strictEqual(r.content, "Reading it.");
  assert.strictEqual(text, "Reading it.");
  assert.strictEqual(r.reasoning, "Hmm, math.js.");
  assert.strictEqual(thought, "Hmm, math.js.");
  assert.strictEqual(r.tool_calls.length, 1);
  assert.deepStrictEqual(JSON.parse(r.tool_calls[0].function.arguments), { path: "math.js" });
  assert.deepStrictEqual(r.usage, { prompt_tokens: 321, completion_tokens: 12 });
  assert.strictEqual(r.truncated, false);
});

test("Ollama: done_reason length marks the reply truncated", async () => {
  handler = (b, q, res) => ndjson(res, [{ message: { content: "partial" } }, { done: true, done_reason: "length", eval_count: 2048 }]);
  const r = await llm.chat({ backend: { provider: "ollama", baseUrl: base + "/v1" }, model: "m", messages: msgs });
  assert.strictEqual(r.truncated, true);
});

test("Ollama: a model without tool support raises ToolsUnsupported", async () => {
  handler = (b, q, res) => json(res, 400, { error: "registry.ollama.ai/library/llava does not support tools" });
  await assert.rejects(
    llm.chat({ backend: { provider: "ollama", baseUrl: base + "/v1" }, model: "llava", messages: msgs, tools: TOOL_DEFS }),
    (e) => e instanceof llm.ToolsUnsupported
  );
});

test("Ollama: an error object mid-stream rejects", async () => {
  handler = (b, q, res) => ndjson(res, [{ message: { content: "a" } }, { error: "model runner has unexpectedly stopped" }]);
  await assert.rejects(llm.chat({ backend: { provider: "ollama", baseUrl: base + "/v1" }, model: "m", messages: msgs }), /unexpectedly stopped/);
});

test("OpenAI-compatible: SSE deltas, fragmented tool-call arguments, reasoning_content, usage", async () => {
  handler = (body, req, res) =>
    sse(res, [
      { choices: [{ index: 0, delta: { role: "assistant", reasoning_content: "think " } }] },
      { choices: [{ index: 0, delta: { content: "Fixing " } }] },
      { choices: [{ index: 0, delta: { content: "now." } }] },
      { choices: [{ index: 0, delta: { tool_calls: [{ index: 0, id: "call_a", type: "function", function: { name: "StrReplace", arguments: "" } }] } }] },
      { choices: [{ index: 0, delta: { tool_calls: [{ index: 0, function: { arguments: '{"path": "math.js", ' } }] } }] },
      { choices: [{ index: 0, delta: { tool_calls: [{ index: 0, function: { arguments: '"old_string": "a - b", "new_string": "a + b"}' } }] } }] },
      { choices: [{ index: 0, delta: { tool_calls: [{ index: 1, id: "call_b", function: { name: "Shell", arguments: '{"command": "node test.js"}' } }] } }] },
      { choices: [{ index: 0, delta: {}, finish_reason: "tool_calls" }] },
      { choices: [], usage: { prompt_tokens: 900, completion_tokens: 40 } },
      "[DONE]",
    ]);
  let text = "";
  const r = await llm.chat({ backend: { provider: "vllm", baseUrl: base + "/v1", apiKey: "k" }, model: "qwen", messages: msgs, tools: TOOL_DEFS, onText: (t) => (text += t) });
  const sent = bodies[bodies.length - 1];
  assert.strictEqual(sent.url, "/v1/chat/completions");
  assert.strictEqual(sent.body.stream, true);
  assert.strictEqual(sent.body.tool_choice, "auto");
  assert.strictEqual(r.content, "Fixing now.");
  assert.strictEqual(text, "Fixing now.");
  assert.strictEqual(r.reasoning, "think ");
  assert.deepStrictEqual(r.tool_calls.map((t) => [t.id, t.function.name]), [["call_a", "StrReplace"], ["call_b", "Shell"]]);
  assert.deepStrictEqual(JSON.parse(r.tool_calls[0].function.arguments), { path: "math.js", old_string: "a - b", new_string: "a + b" });
  assert.strictEqual(r.usage.prompt_tokens, 900);
});

test("OpenAI-compatible: a server that ignores stream and answers JSON still works", async () => {
  handler = (b, q, res) =>
    json(res, 200, { choices: [{ message: { role: "assistant", content: "ok", tool_calls: [{ id: "x", type: "function", function: { name: "LS", arguments: '{"path": "."}' } }] }, finish_reason: "length" }], usage: { prompt_tokens: 5 } });
  const r = await llm.chat({ backend: { provider: "openai", baseUrl: base + "/v1" }, model: "m", messages: msgs });
  assert.strictEqual(r.content, "ok");
  assert.strictEqual(r.tool_calls[0].function.name, "LS");
  assert.strictEqual(r.truncated, true);
});

test("OpenAI-compatible: vLLM without auto tool choice raises ToolsUnsupported", async () => {
  handler = (b, q, res) => json(res, 400, { object: "error", message: '"auto" tool choice requires --enable-auto-tool-choice and --tool-call-parser to be set', type: "BadRequestError" });
  await assert.rejects(
    llm.chat({ backend: { provider: "vllm", baseUrl: base + "/v1" }, model: "m", messages: msgs, tools: TOOL_DEFS }),
    (e) => e instanceof llm.ToolsUnsupported
  );
});

test("local backends retry a 503 / dropped connection before anything streamed", async () => {
  llm.retry.baseMs = 10;
  let calls = 0;
  const retries = [];
  handler = (b, q, res) => {
    calls++;
    if (calls === 1) return json(res, 503, { error: "model is loading" });
    if (calls === 2) return q.socket.destroy();
    sse(res, [{ choices: [{ delta: { content: "back" } }] }, { choices: [{ delta: {}, finish_reason: "stop" }] }, "[DONE]"]);
  };
  const r = await llm.chat({ backend: { provider: "vllm", baseUrl: base + "/v1" }, model: "m", messages: msgs, onRetry: (x) => retries.push(x.attempt) });
  assert.strictEqual(r.content, "back");
  assert.strictEqual(calls, 3);
  assert.deepStrictEqual(retries, [1, 2]);
});

test("local backends do not retry a 400 or a stream that already produced text", async () => {
  llm.retry.baseMs = 10;
  let calls = 0;
  handler = (b, q, res) => {
    calls++;
    json(res, 400, { error: "bad request" });
  };
  await assert.rejects(llm.chat({ backend: { provider: "vllm", baseUrl: base + "/v1" }, model: "m", messages: msgs }));
  assert.strictEqual(calls, 1);
  calls = 0;
  handler = (b, q, res) => {
    calls++;
    res.writeHead(200, { "Content-Type": "text/event-stream" });
    res.write("data: " + JSON.stringify({ choices: [{ delta: { content: "half" } }] }) + "\n\n");
    setTimeout(() => q.socket.destroy(), 20);
  };
  let shown = "";
  await assert.rejects(llm.chat({ backend: { provider: "vllm", baseUrl: base + "/v1" }, model: "m", messages: msgs, onText: (t) => (shown += t) }));
  assert.strictEqual(calls, 1, "no second request once text was shown");
  assert.strictEqual(shown, "half");
});
