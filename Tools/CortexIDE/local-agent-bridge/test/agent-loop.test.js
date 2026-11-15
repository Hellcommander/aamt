"use strict";

// Drives runAgent against a scripted fake model (llm.chat is replaced), so the loop's own
// behaviour is tested: parallel look-ups, todo-gated completion, and the Task sub-agent.

const fs = require("fs");
const os = require("os");
const path = require("path");
const assert = require("assert");
const { test, after, EXT } = require("./harness");
const llm = require(path.join(EXT, "lib", "llm"));
const { runAgent, SUBAGENT_RULES } = require(path.join(EXT, "lib", "agent"));
const { ToolContext } = require(path.join(EXT, "lib", "agent-tools"));
const agentsLib = require(path.join(EXT, "lib", "agents"));

const realChat = llm.chat;
after(() => {
  llm.chat = realChat;
});

const ws = fs.mkdtempSync(path.join(os.tmpdir(), "agent-loop-"));
after(() => fs.rmSync(ws, { recursive: true, force: true }));
fs.writeFileSync(path.join(ws, "a.js"), "const a = 1;\n");
fs.writeFileSync(path.join(ws, "b.js"), "const b = 2;\n");

let n = 0;
const call = (name, args) => ({ id: "c" + ++n, type: "function", function: { name, arguments: JSON.stringify(args) } });
const say = (content, ...calls) => ({ content, tool_calls: calls });

/** Each step gets ({messages, tools}) and returns a reply; the loop must use them all. */
function script(steps) {
  let i = 0;
  llm.chat = async (req) => {
    if (i >= steps.length) throw new Error("model called more often than scripted (" + (i + 1) + ")");
    return steps[i++](req);
  };
  return { done: () => assert.strictEqual(i, steps.length, "model calls used: " + i + "/" + steps.length) };
}

function run(prompt, extra = {}) {
  const events = [];
  const tools = new ToolContext({ roots: [ws], rgPath: "missing-rg" });
  return runAgent({
    backend: { provider: "vllm" },
    model: "fake",
    contextTokens: 32000,
    prompt,
    tools,
    env: { roots: [ws] },
    onEvent: (e) => events.push(e),
    ...extra,
  }).then((r) => ({ r, events, tools }));
}

test("independent reads run in parallel, then edit and complete", async () => {
  const s = script([
    () => say("Reading both files.", call("Read", { path: "a.js" }), call("Read", { path: "b.js" })),
    ({ messages }) => {
      const results = messages.filter((m) => m.role === "tool");
      assert.strictEqual(results.length, 2);
      assert.ok(results[0].content.includes("const a") && results[1].content.includes("const b"));
      return say("Fixing a.js.", call("StrReplace", { path: "a.js", old_string: "= 1", new_string: "= 3" }));
    },
    () => say("", call("attempt_completion", { summary: "Changed a to 3" })),
  ]);
  const { r, events } = await run("change a to 3");
  s.done();
  assert.strictEqual(r.text, "Changed a to 3");
  const reads = events.filter((e) => e.type === "tool" && e.name === "Read");
  // Both started before either finished.
  assert.deepStrictEqual(reads.map((e) => e.status), ["start", "start", "done", "done"]);
  assert.strictEqual(fs.readFileSync(path.join(ws, "a.js"), "utf8"), "const a = 3;\n");
});

/** A steering queue the way the panel hands it to runAgent. */
function steering() {
  const q = new (require(path.join(EXT, "lib", "steer")).SteerQueue)();
  return { q, steer: { has: () => q.hasSteer(), take: () => q.takeSteer() } };
}

test("steering sent during a round reaches the model at its next step and extends the task", async () => {
  const { q, steer } = steering();
  const s = script([
    () => {
      q.push("also make b equal 5", "steer", { from: "other window" });
      return say("Reading.", call("Read", { path: "b.js" }));
    },
    ({ messages }) => {
      const last = messages[messages.length - 1];
      assert.strictEqual(last.role, "user", "steering follows the tool result as a user message");
      assert.ok(/New message from the user while you were working \(sent from other window\)/.test(last.content), last.content);
      assert.ok(last.content.endsWith("also make b equal 5"));
      return say("", call("attempt_completion", { summary: "noted" }));
    },
  ]);
  const { r, events } = await run("read b.js", { steer });
  s.done();
  assert.strictEqual(r.text, "noted");
  assert.deepStrictEqual(r.steered, [{ text: "also make b equal 5", from: "other window" }]);
  assert.ok(events.some((e) => e.type === "steered" && e.text === "also make b equal 5"));
  assert.strictEqual(q.size, 0);
});

test("a completion is held back while a steering message waits, then the model answers it", async () => {
  const { q, steer } = steering();
  const s = script([
    () => {
      q.push("wait, also explain why", "steer");
      return say("", call("attempt_completion", { summary: "first answer" }));
    },
    ({ messages }) => {
      assert.ok(messages.some((m) => m.role === "user" && /also explain why/.test(String(m.content))), "the steer reached the model");
      return say("", call("attempt_completion", { summary: "answer with the why" }));
    },
  ]);
  const { r } = await run("say hi", { steer });
  s.done();
  assert.strictEqual(r.text, "answer with the why");
  assert.strictEqual(r.steered.length, 1);
});

test("completion is refused while the todo list has open items", async () => {
  const s = script([
    () => say("Planning.", call("TodoWrite", { todos: [{ content: "Look", status: "in_progress" }, { content: "Report", status: "pending" }] })),
    () => say("", call("attempt_completion", { summary: "early" })),
    ({ messages }) => {
      const last = messages[messages.length - 1];
      assert.ok(/cannot complete yet.*todo list/.test(last.content), last.content);
      return say("All done.", call("TodoWrite", { todos: [{ content: "Look", status: "completed" }, { content: "Report", status: "completed" }] }));
    },
    () => say("", call("attempt_completion", { summary: "finished" })),
  ]);
  const { r, events } = await run("look around the project");
  s.done();
  assert.strictEqual(r.text, "finished");
  assert.ok(events.some((e) => e.type === "todos" && e.todos.length === 2));
  assert.ok(r.todos.every((t) => t.status === "completed"));
});

test("Task runs a read-only sub-agent and returns its report", async () => {
  const s = script([
    () => say("Asking a sub-agent.", call("Task", { description: "find b", prompt: "Where is b defined?" })),
    // Sub-agent: own system prompt, no edit tools, no history.
    ({ messages, tools }) => {
      assert.ok(messages[0].content.startsWith(SUBAGENT_RULES.slice(0, 40)));
      const names = tools.map((t) => t.function.name);
      assert.ok(names.includes("Grep") && !names.includes("StrReplace") && !names.includes("Task") && !names.includes("Shell"), names.join(","));
      assert.strictEqual(messages[1].content, "Where is b defined?");
      return say("", call("Grep", { pattern: "const b" }));
    },
    () => say("b is defined in b.js line 1."),
    ({ messages }) => {
      const res = messages.filter((m) => m.role === "tool").pop();
      assert.ok(/^Sub-agent report \(1 tool calls\):\nb is defined in b\.js line 1\./.test(res.content), res.content);
      return say("", call("attempt_completion", { summary: "b.js:1" }));
    },
  ]);
  const { r } = await run("where is b defined?");
  s.done();
  assert.strictEqual(r.text, "b.js:1");
});

test("a sub-agent cannot edit even if it asks to", async () => {
  const s = script([
    () => say("", call("Task", { prompt: "Change b" })),
    () => say("", call("Write", { path: "b.js", contents: "hacked" })),
    ({ messages }) => {
      const res = messages.filter((m) => m.role === "tool").pop();
      assert.ok(/Write is not available here/.test(res.content), res.content);
      return say("I can only read; b.js holds const b = 2.");
    },
    () => say("Done looking.", call("attempt_completion", { summary: "reported" })),
  ]);
  await run("tell me about b", {});
  s.done();
  assert.strictEqual(fs.readFileSync(path.join(ws, "b.js"), "utf8"), "const b = 2;\n");
});

test("Plan agent: no edit tools offered, an edit call is refused, a text plan is accepted", async () => {
  const before = fs.readFileSync(path.join(ws, "a.js"), "utf8");
  const s = script([
    ({ messages, tools }) => {
      const names = tools.map((t) => t.function.name);
      assert.ok(!names.some((n) => ["StrReplace", "MultiEdit", "Write", "Delete"].includes(n)), names.join(","));
      assert.ok(names.includes("Read") && names.includes("Shell"));
      assert.ok(messages[0].content.includes("You are in Plan mode"));
      return say("", call("Write", { path: "a.js", contents: "hacked" }));
    },
    ({ messages }) => {
      const res = messages.filter((m) => m.role === "tool").pop();
      assert.ok(/Write is not available here/.test(res.content), res.content);
      return say("Plan: 1. change a in a.js to 3. 2. run node check.js.");
    },
  ]);
  const { r } = await run("change a to 3", { agent: agentsLib.BUILTIN.plan });
  s.done();
  assert.ok(r.text.startsWith("Plan:"), "a read-only agent is not pushed to edit");
  assert.strictEqual(fs.readFileSync(path.join(ws, "a.js"), "utf8"), before);
});

test("a permission prompt answered Deny reaches the model; the file stays as it was", async () => {
  const asked = [];
  const tools = new ToolContext({
    roots: [ws],
    rgPath: "missing-rg",
    rules: [{ action: "edit", resource: "*", effect: "ask" }],
    confirmPermission: async (req) => {
      asked.push(req);
      return "reject";
    },
  });
  const s = script([
    () => say("", call("Read", { path: "b.js" })),
    () => say("", call("StrReplace", { path: "b.js", old_string: "= 2", new_string: "= 5" })),
    ({ messages }) => {
      const res = messages.filter((m) => m.role === "tool").pop();
      assert.ok(/the user denied StrReplace/.test(res.content), res.content);
      return say("The edit to b.js was refused, so b is still 2.");
    },
  ]);
  const { r } = await run("look at b.js and tell me b", { tools });
  s.done();
  assert.strictEqual(asked.length, 1);
  assert.strictEqual(asked[0].action, "edit");
  assert.ok(/refused/.test(r.text));
  assert.strictEqual(fs.readFileSync(path.join(ws, "b.js"), "utf8"), "const b = 2;\n");
});

test("Task runs a named sub-agent with its own prompt and tools; an unknown name lists the choices", async () => {
  const reviewer = { name: "reviewer", mode: "subagent", description: "Reviews code", prompt: "Review strictly.", allowTools: new Set(["read"]), denyTools: new Set(), rules: [], steps: 0 };
  const list = [...Object.values(agentsLib.BUILTIN), reviewer];
  const s = script([
    ({ messages }) => {
      assert.ok(/Sub-agents for the Task tool[\s\S]*- reviewer: Reviews code/.test(messages[0].content));
      return say("", call("Task", { prompt: "Review a.js", agent: "nobody" }));
    },
    ({ messages }) => {
      const res = messages.filter((m) => m.role === "tool").pop();
      assert.ok(/no sub-agent named nobody\. Available: .*reviewer/.test(res.content), res.content);
      return say("", call("Task", { prompt: "Review a.js", agent: "reviewer" }));
    },
    ({ messages, tools }) => {
      assert.ok(messages[0].content.includes("Review strictly."));
      const names = tools.map((t) => t.function.name);
      assert.ok(names.includes("Read") && !names.includes("Grep") && !names.includes("Shell") && !names.includes("Write"), names.join(","));
      return say("", call("Read", { path: "a.js" }));
    },
    () => say("a.js looks fine."),
    ({ messages }) => {
      const res = messages.filter((m) => m.role === "tool").pop();
      assert.ok(/a\.js looks fine/.test(res.content), res.content);
      return say("", call("attempt_completion", { summary: "reviewed" }));
    },
  ]);
  const { r, events } = await run("review a.js", { agents: list });
  s.done();
  assert.strictEqual(r.text, "reviewed");
  assert.ok(events.some((e) => e.type === "tool" && e.name === "Task"));
});

test("allowTask false hides the Task tool", async () => {
  const s = script([
    ({ tools }) => {
      assert.ok(!tools.some((t) => t.function.name === "Task"));
      return say("The answer is 42.");
    },
  ]);
  const { r } = await run("what is the answer?", { allowTask: false });
  s.done();
  assert.strictEqual(r.text, "The answer is 42.");
});

test("a mutating call cut off at the output limit is dropped, not run", async () => {
  const s = script([
    () => ({ content: '<tool_call>{"name": "Write", "arguments": {"path": "half.js", "contents": "function a() {\n  retu', tool_calls: [], truncated: true }),
    ({ messages }) => {
      const last = messages[messages.length - 1];
      assert.ok(/Write call was not run/.test(last.content) && /in parts/.test(last.content), last.content);
      return say("Nothing to do.");
    },
  ]);
  const { events } = await run("tell me about half.js");
  s.done();
  assert.ok(!fs.existsSync(path.join(ws, "half.js")), "partial file must not be written");
  assert.ok(events.some((e) => e.type === "status" && /Dropped a Write call/.test(e.text)));
});

test("reasoning is kept out of the history and the final answer", async () => {
  const s = script([
    () => ({ content: "<think>" + "long deliberation ".repeat(200) + "</think>Listing.", tool_calls: [call("LS", { path: "." })] }),
    ({ messages }) => {
      const a = messages.find((m) => m.role === "assistant");
      assert.strictEqual(a.content, "Listing.");
      return { content: "<think>done</think>There are two js files.", tool_calls: [] };
    },
  ]);
  const { r } = await run("what files are here?");
  s.done();
  assert.strictEqual(r.text, "There are two js files.");
});

test("repeated failed edits on one file escalate the advice", async () => {
  const bad = () => say("", call("StrReplace", { path: "b.js", old_string: "const zzz = 99;", new_string: "x" }));
  const s = script([
    () => say("", call("Read", { path: "b.js" })),
    bad,
    ({ messages }) => {
      assert.ok(!/Second failed edit/.test(messages[messages.length - 1].content));
      return bad();
    },
    ({ messages }) => {
      assert.ok(/Second failed edit/.test(messages[messages.length - 1].content), messages[messages.length - 1].content);
      return say("I could not find it; b.js only defines b.");
    },
  ]);
  await run("where is zzz?");
  s.done();
});

test("completion after an unchecked code change is sent back once to run the project check", async () => {
  const s = script([
    () => say("", call("StrReplace", { path: "b.js", old_string: "const b = 2;", new_string: "const b = 20;" })),
    () => say("", call("attempt_completion", { summary: "changed b" })),
    ({ messages }) => {
      const last = messages[messages.length - 1];
      assert.ok(/not checked it\. Run node check\.js/.test(last.content), last.content);
      return say("", call("attempt_completion", { summary: "changed b; no check needed" }));
    },
  ]);
  const { r } = await run("set b to 20", { env: { roots: [ws], checks: ["node check.js"] } });
  s.done();
  assert.strictEqual(r.text, "changed b; no check needed");
  fs.writeFileSync(path.join(ws, "b.js"), "const b = 2;\n");
});

test("an edit task that only keeps looking gets told to act after 6 rounds", async () => {
  const look = (k) => () => say("Looking more.", call("Grep", { pattern: "const " + k }));
  const s = script([
    look(1), look(2), look(3), look(4), look(5),
    ({ messages }) => {
      assert.ok(!/\[Agent note\]/.test(messages[messages.length - 1].content));
      return look(6)();
    },
    ({ messages }) => {
      const last = messages[messages.length - 1];
      assert.ok(/\[Agent note\] 6 rounds of looking/.test(last.content), last.content);
      return say("", call("StrReplace", { path: "b.js", old_string: "const b = 2;", new_string: "const b = 3;" }));
    },
    () => say("", call("attempt_completion", { summary: "b is 3" })),
  ]);
  const { events } = await run("fix b so it is 3");
  s.done();
  assert.ok(events.some((e) => e.type === "status" && /Stalled for 6 rounds/.test(e.text)));
  fs.writeFileSync(path.join(ws, "b.js"), "const b = 2;\n");
});
