"use strict";

// Claude Code engine (lib/claude-code.js): argument / environment building, the stream-json
// translator, and a full run against a fake CLI (a node script that speaks the same protocol).

const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { test, after, EXT } = require("./harness");
const cc = require(path.join(EXT, "lib", "claude-code"));

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "cc-test-"));
after(() => fs.rmSync(tmp, { recursive: true, force: true }));

const init = { type: "system", subtype: "init", session_id: "sess-1234abcd", model: "claude-opus-5-5", claude_code_version: "2.1.301" };
const usage = { input_tokens: 10, cache_read_input_tokens: 900, cache_creation_input_tokens: 90, output_tokens: 40 };
function script(file) {
  return [
    init,
    { type: "stream_event", event: { type: "content_block_delta", delta: { type: "text_delta", text: "x".repeat(350) } } },
    { type: "assistant", message: { content: [{ type: "text", text: "Planning the fix." }, { type: "tool_use", id: "t0", name: "TodoWrite", input: { todos: [{ content: "Fix add", status: "in_progress" }, { content: "Run tests", status: "pending" }] } }] } },
    { type: "user", message: { content: [{ type: "tool_result", tool_use_id: "t0", content: "ok" }] } },
    { type: "assistant", message: { content: [{ type: "tool_use", id: "t1", name: "Read", input: { file_path: file } }] } },
    { type: "user", message: { content: [{ type: "tool_result", tool_use_id: "t1", content: [{ type: "text", text: "1\treturn a - b;" }] }] } },
    { type: "assistant", parent_tool_use_id: "t9", message: { content: [{ type: "text", text: "subagent chatter" }] } },
    { type: "assistant", message: { content: [{ type: "tool_use", id: "t2", name: "Edit", input: { file_path: file, old_string: "a - b", new_string: "a + b" } }] } },
    { type: "user", message: { content: [{ type: "tool_result", tool_use_id: "t2", content: "File updated" }] } },
    { type: "assistant", message: { content: [{ type: "tool_use", id: "t3", name: "Bash", input: { command: "node test.js" } }] } },
    { type: "user", message: { content: [{ type: "tool_result", tool_use_id: "t3", content: "boom", is_error: true }] } },
    { type: "assistant", message: { content: [{ type: "text", text: "Fixed add()." }] } },
    { type: "result", subtype: "success", is_error: false, result: "Fixed add().", session_id: "sess-1234abcd", num_turns: 5, total_cost_usd: 0.0123, usage, permission_denials: [{ tool_name: "Bash" }] },
  ];
}

test("buildArgs: headless stream-json, permission mode, model, effort, resume, shell mapping, add-dir", () => {
  const a = cc.buildArgs({ model: "opus", permissionMode: "plan", effort: "xhigh", resume: "sess-1", shell: "auto", addDirs: ["D:\\x", ""] });
  for (const flag of ["-p", "--verbose", "--include-partial-messages"]) assert.ok(a.includes(flag), flag);
  const val = (f) => a[a.indexOf(f) + 1];
  assert.strictEqual(val("--output-format"), "stream-json");
  assert.strictEqual(val("--input-format"), "stream-json");
  assert.strictEqual(val("--permission-prompts"), "none");
  assert.strictEqual(val("--permission-mode"), "plan");
  assert.strictEqual(val("--model"), "opus");
  assert.strictEqual(val("--effort"), "xhigh");
  assert.strictEqual(val("--resume"), "sess-1");
  assert.deepStrictEqual(a.slice(a.indexOf("--allowedTools"), a.indexOf("--allowedTools") + 3), ["--allowedTools", "Bash", "PowerShell"]);
  assert.strictEqual(a.filter((x) => x === "--add-dir").length, 1);

  const b = cc.buildArgs({ permissionMode: "bypassPermissions", effort: "default", shell: "off" });
  assert.strictEqual(b[b.indexOf("--permission-mode") + 1], "acceptEdits", "unknown / unsafe mode falls back");
  assert.ok(!b.includes("--model") && !b.includes("--effort") && !b.includes("--resume") && !b.includes("--allowedTools"));
  assert.ok(b.includes("--disallowedTools"));
  const c = cc.buildArgs({ shell: "confirm" });
  assert.ok(!c.includes("--allowedTools") && !c.includes("--disallowedTools"));
});

test("buildEnv: api key + workspace header, bearer token, login strips credentials", () => {
  const base = { PATH: "p", ANTHROPIC_API_KEY: "<stale>", ANTHROPIC_AUTH_TOKEN: "old" };
  const k = cc.buildEnv({ base, cred: { kind: "api_key", token: "sk-ant-k", workspaceId: "wrkspc_1" } });
  assert.strictEqual(k.ANTHROPIC_API_KEY, "sk-ant-k");
  assert.ok(!("ANTHROPIC_AUTH_TOKEN" in k));
  assert.strictEqual(k.ANTHROPIC_CUSTOM_HEADERS, "anthropic-workspace-id: wrkspc_1");
  assert.strictEqual(k.PATH, "p");
  const merged = cc.buildEnv({ base: { ANTHROPIC_CUSTOM_HEADERS: "x-a: 1" }, cred: { kind: "api_key", token: "k", workspaceId: "w" } });
  assert.strictEqual(merged.ANTHROPIC_CUSTOM_HEADERS, "x-a: 1\nanthropic-workspace-id: w");
  const t = cc.buildEnv({ base, cred: { kind: "bearer", token: "tok", workspaceId: "" } });
  assert.strictEqual(t.ANTHROPIC_AUTH_TOKEN, "tok");
  assert.ok(!("ANTHROPIC_API_KEY" in t) && !("ANTHROPIC_CUSTOM_HEADERS" in t));
  const l = cc.buildEnv({ base, cred: { kind: "api_key", token: "sk-ant-k" }, auth: "login" });
  assert.ok(!("ANTHROPIC_API_KEY" in l) && !("ANTHROPIC_AUTH_TOKEN" in l));
  const none = cc.buildEnv({ base });
  assert.strictEqual(none.ANTHROPIC_API_KEY, "<stale>", "no bridge credential: environment passes through");
  assert.strictEqual(base.ANTHROPIC_API_KEY, "<stale>", "base is not mutated");
});

test("findExecutable: explicit path wins, PATH is searched, missing reports nothing", () => {
  const exe = path.join(tmp, process.platform === "win32" ? "claude.exe" : "claude");
  fs.writeFileSync(exe, "");
  assert.strictEqual(cc.findExecutable(exe).exe, exe);
  assert.strictEqual(cc.findExecutable(path.join(tmp, "nope.exe")).exe, "");
  assert.strictEqual(cc.findExecutable("", { PATH: ["Z:\\none", tmp].join(path.delimiter), USERPROFILE: "Z:\\none", HOME: "Z:\\none" }).exe, exe);
  assert.strictEqual(cc.findExecutable("", { PATH: "", USERPROFILE: path.join(tmp, "empty"), HOME: path.join(tmp, "empty") }).exe, "");
});

test("Translator: narration, tools, todos, edits, subagent traffic hidden, usage and denials", () => {
  const events = [];
  const edits = [];
  const file = path.join(tmp, "math.js");
  const tr = new cc.Translator({ emit: (e) => events.push(e), cwd: tmp, onEdit: (p) => edits.push(p) });
  for (const m of script("math.js")) tr.feed(m);
  const res = tr.finish({ exitCode: 0 });
  assert.deepStrictEqual(res, { text: "Fixed add().", sessionId: "sess-1234abcd", costUsd: 0.0123, toolsUsed: 4 });
  assert.deepStrictEqual(edits, [file], "relative edit path is resolved against cwd");

  const thoughts = events.filter((e) => e.type === "thought").map((e) => e.text);
  assert.deepStrictEqual(thoughts, ["Planning the fix."], "the final text is not repeated as a thought; subagent text is hidden");
  assert.deepStrictEqual(events.find((e) => e.type === "todos").todos, [{ content: "Fix add", status: "in_progress" }, { content: "Run tests", status: "pending" }]);
  const done = events.filter((e) => e.type === "tool" && e.status === "done");
  assert.deepStrictEqual(done.map((e) => [e.name, e.label, e.ok]), [["TodoWrite", "", true], ["Read", "math.js", true], ["Edit", "math.js", true], ["Bash", "node test.js", false]]);
  assert.strictEqual(done[1].result, "1\treturn a - b;");
  assert.ok(events.some((e) => e.type === "status" && e.transient && /Writing… 350 chars/.test(e.text)));
  const sum = events.filter((e) => e.type === "status" && !e.transient).map((e) => e.text);
  assert.ok(sum.some((t) => /5 turns · 1,000 input tokens \(900 from cache\) · 40 output · \$0\.0123/.test(t)), sum.join(" | "));
  assert.ok(sum.some((t) => /1 tool call\(s\) were denied/.test(t)));
});

test("Translator.finish: error results carry Claude Code's text plus a hint", () => {
  const mk = (r) => {
    const tr = new cc.Translator({});
    tr.feed(init);
    if (r) tr.feed(r);
    return tr;
  };
  assert.throws(() => mk({ type: "result", subtype: "success", is_error: true, result: "Not logged in · Please run /login" }).finish(), /Not logged in.*claudeCodeAuth/);
  assert.throws(() => mk({ type: "result", subtype: "success", is_error: true, result: "Credit balance is too low" }).finish(), /Credit balance is too low.*credit/i);
  assert.throws(() => mk({ type: "result", subtype: "error_max_turns", is_error: true, errors: ["hit 50 turns"] }).finish(), /turn limit.*hit 50 turns/);
  assert.throws(() => mk(null).finish({ exitCode: 3, stderr: "a\nfatal: boom" }), /Claude Code: a fatal: boom/);
});

// ---- a fake CLI speaking the protocol ----------------------------------------------------

const fake = path.join(tmp, "fake-claude.js");
fs.writeFileSync(
  fake,
  `const fs = require("fs");
const mode = process.env.FAKE_MODE || "ok";
let buf = "";
process.stdin.on("data", (d) => {
  buf += d;
  if (!buf.includes("\\n")) return;
  const first = JSON.parse(buf.split("\\n")[0]);
  fs.writeFileSync(process.env.FAKE_LOG, JSON.stringify({ argv: process.argv.slice(2), prompt: first, cwd: process.cwd(), key: process.env.ANTHROPIC_API_KEY || "" }));
  if (mode === "hang") return;
  const lines = JSON.parse(fs.readFileSync(process.env.FAKE_SCRIPT, "utf8"));
  // Like the real CLI, events arrive over time, and an edit lands right as it is announced
  // (so only the earlier Read is a safe moment to snapshot the file).
  let i = 0;
  const next = () => {
    if (i >= lines.length) return;
    const l = lines[i++];
    process.stdout.write(JSON.stringify(l) + "\\n");
    if (l.type === "assistant" && JSON.stringify(l).includes('"Edit"')) fs.writeFileSync(process.env.FAKE_FILE, "return a + b;\\n");
    setTimeout(next, 10);
  };
  next();
});
process.stdin.on("end", () => process.exit(mode === "fail" ? 1 : 0));
`
);

function fakeRun(extra = {}) {
  const file = path.join(tmp, "math.js");
  fs.writeFileSync(file, "return a - b;\n");
  const scriptFile = path.join(tmp, "script.json");
  fs.writeFileSync(scriptFile, JSON.stringify(extra.lines || script(file)));
  const log = path.join(tmp, "log.json");
  const events = [];
  const snaps = new Map();
  const seen = new Map();
  const p = cc.run({
    exe: process.execPath,
    exeArgs: [fake],
    cwd: tmp,
    prompt: "fix math.js",
    env: { ...process.env, FAKE_SCRIPT: scriptFile, FAKE_LOG: log, FAKE_FILE: file, FAKE_MODE: extra.mode || "ok", ANTHROPIC_API_KEY: "sk-ant-fake" },
    args: cc.buildArgs({ model: "sonnet", resume: "sess-0" }),
    onEvent: (e) => events.push(e),
    onRead: (f) => seen.set(f, fs.readFileSync(f, "utf8")),
    onEdit: (f) => snaps.set(f, seen.has(f) ? seen.get(f) : fs.readFileSync(f, "utf8")),
    signal: extra.signal,
  });
  return { p, events, snaps, file, log };
}

test("run: spawns the CLI, sends the prompt on stdin, translates the stream, snapshots before the edit", async () => {
  const r = fakeRun();
  const res = await r.p;
  assert.strictEqual(res.text, "Fixed add().");
  assert.strictEqual(res.sessionId, "sess-1234abcd");
  const log = JSON.parse(fs.readFileSync(r.log, "utf8"));
  assert.deepStrictEqual(log.prompt, { type: "user", message: { role: "user", content: [{ type: "text", text: "fix math.js" }] }, parent_tool_use_id: null });
  assert.strictEqual(fs.realpathSync(log.cwd), fs.realpathSync(tmp));
  assert.strictEqual(log.key, "sk-ant-fake");
  assert.ok(log.argv.includes("--resume") && log.argv.includes("sess-0") && log.argv.includes("stream-json"));
  assert.strictEqual(r.snaps.get(r.file), "return a - b;\n", "snapshot holds the content from before the edit");
  assert.strictEqual(fs.readFileSync(r.file, "utf8"), "return a + b;\n");
  assert.ok(r.events.some((e) => e.type === "tool" && e.name === "Edit" && e.status === "done"));
});

test("run: an error result rejects with the CLI's message; stop kills the process", async () => {
  const bad = fakeRun({ mode: "fail", lines: [init, { type: "result", subtype: "success", is_error: true, result: "Credit balance is too low", session_id: "s" }] });
  await assert.rejects(bad.p, /Claude Code: Credit balance is too low/);
  const ctrl = new AbortController();
  const hung = fakeRun({ mode: "hang", signal: ctrl.signal });
  setTimeout(() => ctrl.abort(), 300);
  await assert.rejects(hung.p, /^Error: stopped$/);
  await assert.rejects(cc.run({ exe: path.join(tmp, "missing.exe"), cwd: tmp, prompt: "x" }), /Could not start Claude Code/);
});
