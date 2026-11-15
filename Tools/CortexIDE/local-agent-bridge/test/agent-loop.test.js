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
