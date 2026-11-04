"use strict";

// Claude backend (lib/anthropic.js + the llm.js routing) against a mock Messages API:
// message conversion, SSE parsing, caching / thinking fields, retries, credential precedence.

const assert = require("assert");
const http = require("http");
const path = require("path");
const { test, after, EXT } = require("./harness");
const anthropic = require(path.join(EXT, "lib", "anthropic"));
const llm = require(path.join(EXT, "lib", "llm"));
const { TOOL_DEFS } = require(path.join(EXT, "lib", "agent-tools"));

const CRED = { kind: "api_key", token: "sk-ant-test", source: "test" };

// ---- mock server -------------------------------------------------------------------------

const requests = [];
let onMessages = null; // (body, req, res) => void

function sse(res, events) {
  res.writeHead(200, { "Content-Type": "text/event-stream" });
  for (const [event, data] of events) res.write("event: " + event + "\ndata: " + JSON.stringify(data) + "\n\n");
  res.end();
}

/** A normal streamed reply: thinking + text + one Read tool call. */
function okStream(res) {
  sse(res, [
    ["message_start", { type: "message_start", message: { id: "msg_1", type: "message", role: "assistant", model: "claude-opus-5-5", content: [], usage: { input_tokens: 120, cache_creation_input_tokens: 100, cache_read_input_tokens: 0, output_tokens: 1 } } }],
    ["content_block_start", { type: "content_block_start", index: 0, content_block: { type: "thinking", thinking: "", signature: "" } }],
    ["content_block_delta", { type: "content_block_delta", index: 0, delta: { type: "signature_delta", signature: "sig123" } }],
    ["content_block_stop", { type: "content_block_stop", index: 0 }],
    ["content_block_start", { type: "content_block_start", index: 1, content_block: { type: "text", text: "" } }],
    ["content_block_delta", { type: "content_block_delta", index: 1, delta: { type: "text_delta", text: "Reading " } }],
    ["content_block_delta", { type: "content_block_delta", index: 1, delta: { type: "text_delta", text: "the file." } }],
    ["content_block_stop", { type: "content_block_stop", index: 1 }],
    ["content_block_start", { type: "content_block_start", index: 2, content_block: { type: "tool_use", id: "toolu_1", name: "Read", input: {} } }],
    ["content_block_delta", { type: "content_block_delta", index: 2, delta: { type: "input_json_delta", partial_json: '{"path": "ma' } }],
    ["content_block_delta", { type: "content_block_delta", index: 2, delta: { type: "input_json_delta", partial_json: 'th.js"}' } }],
    ["content_block_stop", { type: "content_block_stop", index: 2 }],
    ["message_delta", { type: "message_delta", delta: { stop_reason: "tool_use", stop_sequence: null }, usage: { output_tokens: 42 } }],
    ["message_stop", { type: "message_stop" }],
  ]);
}

const server = http.createServer((req, res) => {
  const chunks = [];
  req.on("data", (c) => chunks.push(c));
  req.on("end", () => {
    const raw = Buffer.concat(chunks).toString("utf8");
    const body = raw ? JSON.parse(raw) : null;
    requests.push({ method: req.method, url: req.url, headers: req.headers, body });
    if (req.url.startsWith("/v1/models")) {
      if (req.headers["x-api-key"] !== "sk-ant-test" && !req.headers.authorization) {
        res.writeHead(401, { "Content-Type": "application/json" });
        return res.end(JSON.stringify({ type: "error", error: { type: "authentication_error", message: "invalid x-api-key" } }));
      }
      const page2 = /after_id=claude-haiku-4-5/.test(req.url);
      res.writeHead(200, { "Content-Type": "application/json" });
      return res.end(
        JSON.stringify(
          page2
            ? { data: [{ id: "claude-3-haiku-20240307", display_name: "Claude 3 Haiku", max_input_tokens: 200000 }], has_more: false, first_id: "claude-3-haiku-20240307", last_id: "claude-3-haiku-20240307" }
            : {
                data: [
                  { id: "claude-opus-5-5", display_name: "Claude Opus 5.5", max_input_tokens: 1000000, max_tokens: 128000, created_at: "2026-04-01T00:00:00Z" },
                  { id: "claude-haiku-4-5", display_name: "Claude Haiku 4.5", max_input_tokens: 200000, max_tokens: 64000 },
                ],
                has_more: true,
                first_id: "claude-opus-5-5",
                last_id: "claude-haiku-4-5",
              }
        )
      );
    }
    if (req.url === "/v1/messages") {
      if (onMessages) return onMessages(body, req, res);
      return okStream(res);
    }
    res.writeHead(404);
    res.end();
  });
});

const ready = new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const base = () => "http://127.0.0.1:" + server.address().port;
after(() => server.close());

// ---- unit: model table / credentials / headers -------------------------------------------

test("supportsAdaptive: 4.6+ and 5.x families only", () => {
  const yes = ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5", "claude-opus-4-8", "claude-sonnet-4-6", "claude-fable-5-1"];
  const no = ["claude-haiku-4-5", "claude-haiku-4-5-20251001", "claude-opus-4-5-20251101", "claude-sonnet-4-20250514", "claude-opus-4-1-20250805", "claude-3-5-sonnet-20241022", "gpt-4o", ""];
  for (const m of yes) assert.ok(anthropic.supportsAdaptive(m), m);
  for (const m of no) assert.ok(!anthropic.supportsAdaptive(m), m);
});

test("credentials: saved key, then ANTHROPIC_API_KEY, then ANTHROPIC_AUTH_TOKEN, then nothing", () => {
  const none = {};
  assert.deepStrictEqual(anthropic.credentials({ apiKey: " sk-ant-abc ", env: { ANTHROPIC_API_KEY: "x" }, useCli: false }), { kind: "api_key", token: "sk-ant-abc", source: "saved key", workspaceId: "" });
  assert.strictEqual(anthropic.credentials({ apiKey: "sk-ant-oat01-zzz", env: none, useCli: false }).kind, "bearer");
  assert.deepStrictEqual(anthropic.credentials({ env: { ANTHROPIC_API_KEY: "k1", ANTHROPIC_AUTH_TOKEN: "t1" }, useCli: false }), { kind: "api_key", token: "k1", source: "ANTHROPIC_API_KEY", workspaceId: "" });
  assert.deepStrictEqual(anthropic.credentials({ env: { ANTHROPIC_API_KEY: "  ", ANTHROPIC_AUTH_TOKEN: "t1" }, useCli: false }), { kind: "bearer", token: "t1", source: "ANTHROPIC_AUTH_TOKEN", workspaceId: "" });
  assert.strictEqual(anthropic.credentials({ env: none, useCli: false }), null);
});

test("credentials: pasted wrappers (angle brackets, quotes, whitespace) are stripped", () => {
  assert.strictEqual(anthropic.cleanKey(" <sk-ant-abc> "), "sk-ant-abc");
  assert.strictEqual(anthropic.cleanKey("'sk-ant-abc'"), "sk-ant-abc");
  assert.strictEqual(anthropic.cleanKey('"<sk-ant-abc>"'), "sk-ant-abc");
  assert.strictEqual(anthropic.cleanKey("<>"), "");
  assert.strictEqual(anthropic.cleanKey(undefined), "");
  assert.strictEqual(anthropic.credentials({ env: { ANTHROPIC_API_KEY: "<sk-ant-env>" }, useCli: false }).token, "sk-ant-env");
  assert.strictEqual(anthropic.credentials({ env: { ANTHROPIC_API_KEY: "<>" }, useCli: false }), null);
});

test("credentials: workspace id from option or ANTHROPIC_WORKSPACE_ID becomes the anthropic-workspace-id header", () => {
  const c1 = anthropic.credentials({ apiKey: "sk-ant-usr-x", workspaceId: " <wrkspc_1> ", env: {}, useCli: false });
  assert.strictEqual(c1.workspaceId, "wrkspc_1");
  assert.strictEqual(anthropic.headers(c1)["anthropic-workspace-id"], "wrkspc_1");
  const c2 = anthropic.credentials({ env: { ANTHROPIC_API_KEY: "sk-ant-usr-x", ANTHROPIC_WORKSPACE_ID: "wrkspc_2" }, useCli: false });
  assert.strictEqual(c2.workspaceId, "wrkspc_2");
  const c3 = anthropic.credentials({ apiKey: "sk-ant-api03-x", env: {}, useCli: false });
  assert.strictEqual(c3.workspaceId, "");
  assert.ok(!("anthropic-workspace-id" in anthropic.headers(c3)));
});

test("headers: api key goes in x-api-key, bearer adds the oauth beta", () => {
  const a = anthropic.headers({ kind: "api_key", token: "k" });
  assert.strictEqual(a["x-api-key"], "k");
  assert.strictEqual(a["anthropic-version"], anthropic.API_VERSION);
  assert.ok(!a.Authorization && !a["anthropic-beta"]);
  const b = anthropic.headers({ kind: "bearer", token: "t" }, ["x-beta"]);
  assert.strictEqual(b.Authorization, "Bearer t");
  assert.strictEqual(b["anthropic-beta"], "x-beta,oauth-2025-04-20");
  assert.ok(!b["x-api-key"]);
});

// ---- unit: message conversion -----------------------------------------------------------

test("toMessages: system split out, tool results merged into one user turn, args parsed", () => {
  const conv = anthropic.toMessages([
    { role: "system", content: "RULES" },
    { role: "user", content: "fix it" },
    {
      role: "assistant",
      content: null,
      tool_calls: [
        { id: "t1", type: "function", function: { name: "Read", arguments: '{"path":"a.js"}' } },
        { id: "t2", type: "function", function: { name: "LS", arguments: "not json" } },
      ],
    },
    { role: "tool", tool_call_id: "t1", name: "Read", content: "line 1" },
    { role: "tool", tool_call_id: "t2", name: "LS", content: "" },
    { role: "user", content: "Continue." },
  ]);
  assert.strictEqual(conv.system, "RULES");
  assert.deepStrictEqual(conv.messages.map((m) => m.role), ["user", "assistant", "user"]);
  assert.deepStrictEqual(conv.messages[1].content, [
    { type: "tool_use", id: "t1", name: "Read", input: { path: "a.js" } },
    { type: "tool_use", id: "t2", name: "LS", input: {} },
  ]);
  assert.deepStrictEqual(conv.messages[2].content, [
    { type: "tool_result", tool_use_id: "t1", content: "line 1" },
    { type: "tool_result", tool_use_id: "t2", content: "(empty)" },
    { type: "text", text: "Continue." },
  ]);
});

test("toMessages: missing tool_result is synthesised, stray one becomes text, first turn is user, empty assistant is non-empty", () => {
  const conv = anthropic.toMessages([
    { role: "assistant", content: "" },
    { role: "assistant", content: null, tool_calls: [{ id: "t1", type: "function", function: { name: "Read", arguments: "{}" } }] },
    { role: "user", content: "[Context compacted]" },
    { role: "tool", tool_call_id: "ghost", name: "Grep", content: "old" },
  ]);
  assert.strictEqual(conv.messages[0].role, "user");
  assert.deepStrictEqual(conv.messages[1].content[0], { type: "text", text: "(empty)" });
  assert.deepStrictEqual(conv.messages[2].content, [
    { type: "tool_result", tool_use_id: "t1", content: "(no result recorded)" },
    { type: "text", text: "[Context compacted]" },
    { type: "text", text: "[Grep result]\nold" },
  ]);
});

test("toMessages: replays raw blocks with thinking, drops thinking once history was edited", () => {
  const blocks = [
    { type: "thinking", thinking: "", signature: "sig" },
    { type: "text", text: "Reading." },
    { type: "tool_use", id: "t1", name: "Read", input: { path: "a.js" } },
  ];
  const msgs = [
    { role: "user", content: "go" },
    { role: "assistant", content: "Reading.", blocks, tool_calls: [{ id: "t1", type: "function", function: { name: "Read", arguments: '{"path":"a.js"}' } }] },
    { role: "tool", tool_call_id: "t1", name: "Read", content: "x" },
  ];
  const replay = anthropic.toMessages(msgs, { replayThinking: true });
  assert.deepStrictEqual(replay.messages[1].content, blocks);
  const stripped = anthropic.toMessages(msgs, { replayThinking: false });
  assert.deepStrictEqual(stripped.messages[1].content.map((b) => b.type), ["text", "tool_use"]);
  assert.strictEqual(stripped.messages[2].content[0].tool_use_id, "t1");
});

test("toTools: OpenAI function defs become name/description/input_schema", () => {
  const tools = anthropic.toTools(TOOL_DEFS);
  assert.strictEqual(tools.length, TOOL_DEFS.length);
  const read = tools.find((t) => t.name === "Read");
  assert.ok(read.description.length > 10);
  assert.deepStrictEqual(read.input_schema.required, ["path"]);
  for (const t of tools) assert.ok(/^[a-zA-Z0-9_-]{1,64}$/.test(t.name), t.name);
});

// ---- integration: discover / chat against the mock ------------------------------------

test("discover + pickModel + contextWindow on the Claude provider (paginated model list, 200k planning cap)", async () => {
  await ready;
  const backend = await llm.discover({ provider: "anthropic", baseUrl: base(), anthropicApiKey: "sk-ant-test" });
  assert.strictEqual(backend.provider, "anthropic");
  assert.strictEqual(backend.label, "Claude");
  assert.strictEqual(backend.credSource, "saved key");
  assert.deepStrictEqual(backend.models.map((m) => m.id), ["claude-opus-5-5", "claude-haiku-4-5", "claude-3-haiku-20240307"]);
  assert.strictEqual(backend.models[0].display, "Claude Opus 5.5");
  const model = llm.pickModel(backend.models, "", "anthropic");
  assert.strictEqual(model, "claude-opus-5-5");
  assert.strictEqual(await llm.contextWindow(backend, model, {}), 200000);
  assert.strictEqual(await llm.contextWindow(backend, model, { override: 50000 }), 50000);
  const modelsReq = requests.filter((r) => r.url.startsWith("/v1/models"));
  assert.strictEqual(modelsReq.length, 2);
  assert.strictEqual(modelsReq[0].headers["x-api-key"], "sk-ant-test");
  assert.strictEqual(modelsReq[0].headers["anthropic-version"], anthropic.API_VERSION);
});

test("discover: no credentials is a clear error, generic apiKey counts when it is an Anthropic key", async () => {
  await ready;
  await assert.rejects(
    llm.discover({ provider: "anthropic", baseUrl: base(), apiKey: "some-vllm-key", anthropicApiKey: "" }),
    /no credentials/
  );
  const b = await llm.discover({ provider: "anthropic", baseUrl: base(), apiKey: "sk-ant-test" });
  assert.strictEqual(b.provider, "anthropic");
});

test("chat: request body has streaming, caching, adaptive thinking + effort, tools, no temperature; reply maps text/tool_use/usage/blocks", async () => {
  await ready;
  const backend = await llm.discover({ provider: "anthropic", baseUrl: base(), anthropicApiKey: "sk-ant-test" });
  requests.length = 0;
  let streamed = "";
  const reply = await llm.chat({
    backend,
    model: "claude-opus-5-5",
    messages: [{ role: "system", content: "RULES" }, { role: "user", content: "fix math.js" }],
    tools: TOOL_DEFS,
    maxTokens: 16000,
    temperature: 0.2,
    effort: "high",
    onText: (t) => (streamed += t),
  });
  const body = requests[0].body;
  assert.strictEqual(requests[0].url, "/v1/messages");
  assert.strictEqual(body.model, "claude-opus-5-5");
  assert.strictEqual(body.stream, true);
  assert.strictEqual(body.max_tokens, 16000);
  assert.deepStrictEqual(body.system, [{ type: "text", text: "RULES", cache_control: { type: "ephemeral" } }]);
  assert.deepStrictEqual(body.cache_control, { type: "ephemeral" });
  assert.deepStrictEqual(body.thinking, { type: "adaptive" });
  assert.deepStrictEqual(body.output_config, { effort: "high" });
  assert.strictEqual(body.tools.length, TOOL_DEFS.length);
  assert.ok(!("temperature" in body), "temperature must not be sent");
  assert.ok(!("tool_choice" in body));

  assert.strictEqual(reply.content, "Reading the file.");
  assert.strictEqual(streamed, "Reading the file.");
  assert.strictEqual(reply.tool_calls.length, 1);
  assert.strictEqual(reply.tool_calls[0].id, "toolu_1");
  assert.strictEqual(reply.tool_calls[0].function.name, "Read");
  assert.deepStrictEqual(JSON.parse(reply.tool_calls[0].function.arguments), { path: "math.js" });
  assert.deepStrictEqual(reply.blocks.map((b) => b.type), ["thinking", "text", "tool_use"]);
  assert.strictEqual(reply.blocks[0].signature, "sig123");
  assert.deepStrictEqual(reply.blocks[2].input, { path: "math.js" });
  assert.deepStrictEqual(reply.usage, { prompt_tokens: 220, completion_tokens: 42, cache_read: 0, cache_write: 100 });
  assert.strictEqual(reply.truncated, false);

  // Second round: the tool result goes back with the raw blocks replayed.
  requests.length = 0;
  await llm.chat({
    backend,
    model: "claude-opus-5-5",
    messages: [
      { role: "system", content: "RULES" },
      { role: "user", content: "fix math.js" },
      { role: "assistant", content: reply.content, blocks: reply.blocks, tool_calls: reply.tool_calls },
      { role: "tool", tool_call_id: "toolu_1", name: "Read", content: "function add(a, b) { return a - b; }" },
    ],
    tools: TOOL_DEFS,
    replayThinking: true,
  });
  const m = requests[0].body.messages;
  assert.deepStrictEqual(m.map((x) => x.role), ["user", "assistant", "user"]);
  assert.strictEqual(m[1].content[0].type, "thinking");
  assert.strictEqual(m[2].content[0].type, "tool_result");
  assert.strictEqual(m[2].content[0].tool_use_id, "toolu_1");
});

test("chat: models without adaptive thinking get no thinking/output_config", async () => {
  await ready;
  const backend = await llm.discover({ provider: "anthropic", baseUrl: base(), anthropicApiKey: "sk-ant-test" });
  requests.length = 0;
  await llm.chat({ backend, model: "claude-haiku-4-5", messages: [{ role: "user", content: "hi" }], effort: "max" });
  assert.ok(!("thinking" in requests[0].body));
  assert.ok(!("output_config" in requests[0].body));
  assert.ok(!("system" in requests[0].body));
});

test("chat: 429 is retried after retry-after, then succeeds", async () => {
  await ready;
  const backend = await llm.discover({ provider: "anthropic", baseUrl: base(), anthropicApiKey: "sk-ant-test" });
  requests.length = 0;
  let n = 0;
  onMessages = (body, req, res) => {
    n++;
    if (n === 1) {
      res.writeHead(429, { "Content-Type": "application/json", "retry-after": "0" });
      return res.end(JSON.stringify({ type: "error", error: { type: "rate_limit_error", message: "slow down" } }));
    }
    okStream(res);
  };
  try {
    const reply = await llm.chat({ backend, model: "claude-opus-5-5", messages: [{ role: "user", content: "hi" }] });
    assert.strictEqual(reply.content, "Reading the file.");
    assert.strictEqual(n, 2);
  } finally {
    onMessages = null;
  }
});

test("chat: 400 is not retried and carries the API message", async () => {
  await ready;
  const backend = await llm.discover({ provider: "anthropic", baseUrl: base(), anthropicApiKey: "sk-ant-test" });
  let n = 0;
  onMessages = (body, req, res) => {
    n++;
    res.writeHead(400, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ type: "error", error: { type: "invalid_request_error", message: "max_tokens: too large" } }));
  };
  try {
    await assert.rejects(llm.chat({ backend, model: "claude-opus-5-5", messages: [{ role: "user", content: "hi" }] }), /Claude API 400: max_tokens: too large/);
    assert.strictEqual(n, 1);
  } finally {
    onMessages = null;
  }
});

test("chat: rejected thinking signature surfaces as ThinkingMismatch", async () => {
  await ready;
  const backend = await llm.discover({ provider: "anthropic", baseUrl: base(), anthropicApiKey: "sk-ant-test" });
  onMessages = (body, req, res) => {
    res.writeHead(400, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ type: "error", error: { type: "invalid_request_error", message: "messages.1.content.0: Invalid `signature` in `thinking` block. The block is bound to a different conversation." } }));
  };
  try {
    await assert.rejects(llm.chat({ backend, model: "claude-opus-5-5", messages: [{ role: "user", content: "hi" }] }), (e) => e instanceof llm.ThinkingMismatch);
  } finally {
    onMessages = null;
  }
});

test("chat: refusal stop reason is an error; max_tokens with no text explains itself", async () => {
  await ready;
  const backend = await llm.discover({ provider: "anthropic", baseUrl: base(), anthropicApiKey: "sk-ant-test" });
  onMessages = (body, req, res) =>
    sse(res, [
      ["message_start", { type: "message_start", message: { id: "m", model: "claude-opus-5-5", usage: { input_tokens: 5 } } }],
      ["message_delta", { type: "message_delta", delta: { stop_reason: "refusal", stop_details: { type: "refusal", category: "cyber", explanation: "no" } }, usage: { output_tokens: 0 } }],
      ["message_stop", { type: "message_stop" }],
    ]);
  try {
    await assert.rejects(llm.chat({ backend, model: "claude-opus-5-5", messages: [{ role: "user", content: "hi" }] }), /Claude declined this request: no/);
    onMessages = (body, req, res) =>
      sse(res, [
        ["message_start", { type: "message_start", message: { id: "m", model: "claude-opus-5-5", usage: { input_tokens: 5 } } }],
        ["content_block_start", { type: "content_block_start", index: 0, content_block: { type: "thinking", thinking: "", signature: "" } }],
        ["message_delta", { type: "message_delta", delta: { stop_reason: "max_tokens" }, usage: { output_tokens: 9 } }],
        ["message_stop", { type: "message_stop" }],
      ]);
    const r = await llm.chat({ backend, model: "claude-opus-5-5", messages: [{ role: "user", content: "hi" }] });
    assert.strictEqual(r.truncated, true);
    assert.match(r.content, /output token limit/);
  } finally {
    onMessages = null;
  }
});

test("chat: a plain JSON message (proxy ignoring stream) is accepted too", async () => {
  await ready;
  const backend = await llm.discover({ provider: "anthropic", baseUrl: base(), anthropicApiKey: "sk-ant-test" });
  onMessages = (body, req, res) => {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ type: "message", model: "claude-opus-5-5", stop_reason: "end_turn", content: [{ type: "text", text: "Done." }], usage: { input_tokens: 3, output_tokens: 2 } }));
  };
  try {
    const r = await llm.chat({ backend, model: "claude-opus-5-5", messages: [{ role: "user", content: "hi" }] });
    assert.strictEqual(r.content, "Done.");
    assert.deepStrictEqual(r.tool_calls, []);
  } finally {
    onMessages = null;
  }
});

test("chat: stream error event rejects; abort signal stops the call", async () => {
  await ready;
  const backend = await llm.discover({ provider: "anthropic", baseUrl: base(), anthropicApiKey: "sk-ant-test" });
  onMessages = (body, req, res) => sse(res, [["error", { type: "error", error: { type: "overloaded_error", message: "Overloaded" } }]]);
  try {
    await assert.rejects(llm.chat({ backend, model: "claude-opus-5-5", messages: [{ role: "user", content: "hi" }] }), /Overloaded/);
  } finally {
    onMessages = null;
  }
  const ctrl = new AbortController();
  ctrl.abort();
  await assert.rejects(llm.chat({ backend, model: "claude-opus-5-5", messages: [{ role: "user", content: "hi" }], signal: ctrl.signal }), /stopped/);
});
