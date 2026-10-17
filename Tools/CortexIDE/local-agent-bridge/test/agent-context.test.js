"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const assert = require("assert");
const { test, after, EXT } = require("./harness");
const { compact, Progress, estimateTokens, short } = require(path.join(EXT, "lib", "agent-context"));

function bigRun(n) {
  const msgs = [{ role: "system", content: "S".repeat(2000) }, { role: "user", content: "fix it" }];
  for (let i = 0; i < n; i++) {
    msgs.push({ role: "assistant", content: null, tool_calls: [{ id: "c" + i, type: "function", function: { name: "Read", arguments: "{}" } }] });
    msgs.push({ role: "tool", tool_call_id: "c" + i, content: "R".repeat(3000) });
  }
  return msgs;
}

test("short collapses whitespace and truncates", () => {
  assert.strictEqual(short("a\n  b", 10), "a b");
  assert.strictEqual(short("abcdefghij", 5), "abcd…");
});

test("Progress.record tracks reads, searches, edits, commands, errors", () => {
  const p = new Progress({ task: "fix it" });
  p.record("Read", { path: "a.cs" }, "a.cs (lines 1-3 of 3)");
  p.record("Grep", { pattern: "Level", path: "src" }, "a.cs:1:x\nb.cs:2:y");
  p.record("StrReplace", { path: "a.cs" }, "edited a.cs (1 replacement, at line 2)");
  p.record("Shell", { command: "dotnet build" }, "exit 1 (cwd x)\nerror CS0103: The name 'foo' does not exist");
  p.record("Read", { path: "missing.cs" }, "error: not found: missing.cs");
  const t = p.toText();
  assert.ok(/Files changed:\n- a\.cs \(edited, 1 replacement, at line 2\)/.test(t), t);
  assert.ok(/Grep Level in src → 2 hits/.test(t), t);
  assert.ok(/dotnet build → exit 1 · error CS0103/.test(t), t);
  assert.ok(/Errors hit:\n- Read: error: not found/.test(t), t);
  assert.ok(!t.includes("missing.cs;"), "failed reads are not listed as read");
});

test("Progress survives a JSON round trip", () => {
  const p = new Progress({ task: "t" });
  p.record("Write", { path: "x.txt" }, "created x.txt (1 lines)");
  const q = new Progress(JSON.parse(JSON.stringify(p.toJSON())));
  assert.strictEqual(q.toText(), p.toText());
  assert.ok(new Progress().empty());
  assert.ok(!q.empty());
});

test("Progress.persist writes .cortexide/agent/progress.md", () => {
  const ws = fs.mkdtempSync(path.join(os.tmpdir(), "agent-ctx-"));
  after(() => fs.rmSync(ws, { recursive: true, force: true }));
  const p = new Progress({ task: "persist me" });
  const file = p.persist(ws);
  assert.strictEqual(file, path.join(ws, ".cortexide", "agent", "progress.md"));
  assert.ok(fs.readFileSync(file, "utf8").includes("Task: persist me"));
  assert.strictEqual(p.persist(""), "");
});

test("compact leaves a small conversation alone", () => {
  const msgs = bigRun(1);
  assert.strictEqual(compact(msgs, 1e6, new Progress()), 0);
  assert.strictEqual(msgs.length, 4);
});

test("compact level 1 shortens old tool output only", () => {
  const msgs = bigRun(12);
  const level = compact(msgs, estimateTokens(msgs) - 1000, new Progress(), { keepRecent: 8 });
  assert.strictEqual(level, 1);
  assert.ok(String(msgs[3].content).includes("[compacted"), "old tool output compacted");
  assert.strictEqual(msgs[msgs.length - 1].content.length, 3000, "recent tool output untouched");
});

test("compact keeps task + recent, injects progress digest", () => {
  const p = new Progress({ task: "fix it" });
  p.record("Read", { path: "a.cs" }, "ok");
  p.record("StrReplace", { path: "a.cs" }, "edited a.cs (1 replacement)");
  p.record("Shell", { command: "dotnet build" }, "exit 1 (cwd x)\nerror CS0103: The name 'foo' does not exist");
  const msgs = bigRun(30);
  const before = estimateTokens(msgs);
  const level = compact(msgs, 6000, p, { firstUser: 1 });
  assert.ok(level >= 2, "level " + level);
  assert.ok(estimateTokens(msgs) <= 6000, "still " + estimateTokens(msgs) + " (was " + before + ")");
  assert.strictEqual(msgs[1].content, "fix it");
  assert.ok(/Context compacted[\s\S]*a\.cs[\s\S]*dotnet build → exit 1[\s\S]*CS0103/.test(msgs[2].content), msgs[2].content);
  assert.notStrictEqual(msgs[3].role, "tool", "tool result orphaned after cut");
});

test("compact level 4 trims an oversized system prompt", () => {
  const msgs = [{ role: "system", content: "S".repeat(60000) }, { role: "user", content: "go" }];
  const level = compact(msgs, 5000, new Progress());
  assert.strictEqual(level, 4);
  assert.ok(msgs[0].content.endsWith("[system context trimmed to fit]"));
  assert.ok(estimateTokens(msgs) <= 5000, "tokens " + estimateTokens(msgs));
});
