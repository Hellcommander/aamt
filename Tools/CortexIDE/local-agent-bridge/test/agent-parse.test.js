"use strict";

const path = require("path");
const assert = require("assert");
const { test, EXT } = require("./harness");
const { parseTextCalls, narration, isTutor, announcesAction, wantsEdit, wantsVerify, looksLikeWork, jsonObjects } = require(path.join(EXT, "lib", "agent-parse"));

test("bare JSON call (Ollama qwen2.5-coder)", () => {
  const c = parseTextCalls('{"name": "Read", "arguments": {"path": "C:\\\\temp\\\\a.txt"}}');
  assert.deepStrictEqual(c, [{ name: "Read", args: { path: "C:\\temp\\a.txt" } }]);
});

test("<tool_call> Hermes block with alias name", () => {
  const c = parseTextCalls('Let me look.\n<tool_call>\n{"name": "read_file", "arguments": {"path": "x.cs"}}\n</tool_call>');
  assert.strictEqual(c.length, 1);
  assert.strictEqual(c[0].name, "Read");
});

test("fenced json with nested braces in args", () => {
  const c = parseTextCalls('```json\n{"name": "Write", "arguments": {"path": "a.js", "contents": "function f() { return {a:1}; }"}}\n```');
  assert.strictEqual(c[0].args.contents, "function f() { return {a:1}; }");
});

test("fenced array of calls", () => {
  const c = parseTextCalls('```json\n[{"name": "LS", "arguments": {"path": "."}}, {"name": "Grep", "arguments": {"pattern": "x"}}]\n```');
  assert.deepStrictEqual(c.map((x) => x.name), ["LS", "Grep"]);
});

test("OpenAI-style function object and string arguments", () => {
  const c = parseTextCalls('{"function": {"name": "Shell", "arguments": "{\\"command\\": \\"dir\\"}"}}');
  assert.deepStrictEqual(c, [{ name: "Shell", args: { command: "dir" } }]);
});

test("duplicate calls collapse", () => {
  const one = '{"name": "LS", "arguments": {"path": "."}}';
  assert.strictEqual(parseTextCalls("<tool_call>" + one + "</tool_call><tool_call>" + one + "</tool_call>").length, 1);
});

test("ordinary JSON in prose is not a call", () => {
  assert.strictEqual(parseTextCalls('The config is {"name": "my-mod", "version": "1.0"}').length, 0);
});

test("jsonObjects ignores braces inside strings", () => {
  assert.deepStrictEqual(jsonObjects('a {"s": "}{"} b {"t": 1}'), ['{"s": "}{"}', '{"t": 1}']);
});

test("narration strips call markup and think tags", () => {
  assert.strictEqual(narration('Let me look.\n<tool_call>{"name":"Read","arguments":{}}</tool_call>'), "Let me look.");
  assert.strictEqual(narration('<think>Checking.</think> {"name": "LS", "arguments": {"path": "."}}'), "Checking.");
});

test("tutor detection", () => {
  assert.ok(isTutor("I don't have the capability to directly operate Ghidra. Here's a brief guide"));
  assert.ok(isTutor("Could you please provide more details?"));
  assert.ok(isTutor("Would you like me to apply this?"));
  assert.ok(!isTutor("Fixed the subtraction in util.js and the test passes."));
  assert.ok(!isTutor(""));
});

test("intent classifiers", () => {
  assert.ok(announcesAction("I'll fix the bug next."));
  assert.ok(!announcesAction("Fixed the bug."));
  assert.ok(wantsEdit("Fix the bug in math.js"));
  assert.ok(!wantsEdit("What does this file do?"));
  assert.ok(wantsVerify("then run the tests"));
  assert.ok(looksLikeWork("investigate the crash"));
  assert.ok(!looksLikeWork("hello there"));
});
