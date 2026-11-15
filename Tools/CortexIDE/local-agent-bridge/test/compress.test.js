"use strict";

// /compress (lib/compress.js): command parsing, the graded transcript (recent turns in full,
// older ones shortened, an earlier summary carried forward) and the summary history entry.

const path = require("path");
const assert = require("assert");
const { test, EXT } = require("./harness");
const c = require(path.join(EXT, "lib", "compress"));

function turn(i, big) {
  return [
    { cls: "user", text: "task " + i + " " + "u".repeat(big ? 3000 : 10) },
    { cls: "tool", name: "Read", label: "Read file" + i + ".js", ok: true, text: "RESULT" + i + " " + "r".repeat(big ? 2000 : 10) },
    { cls: "changes", files: [{ path: "file" + i + ".js", kind: "modified", added: 3, removed: 1 }] },
    { cls: "assistant", text: "answer " + i + " " + "a".repeat(big ? 4000 : 10) },
  ];
}

test("parseCommand: /compress and /compact with an optional focus", () => {
  assert.deepStrictEqual(c.parseCommand("/compress"), { focus: "" });
  assert.deepStrictEqual(c.parseCommand("  /compact keep the API notes "), { focus: "keep the API notes" });
  assert.strictEqual(c.parseCommand("/compressor"), null);
  assert.strictEqual(c.parseCommand("please /compress"), null);
});

test("recent turns are detailed, older turns are outlined", () => {
  const log = [];
  for (let i = 1; i <= 12; i++) log.push(...turn(i, true));
  const t = c.buildTranscript({ log }, { recentTurns: 3, maxChars: 1e9 });
  assert.strictEqual(t.turns, 12);
  assert.ok(/### Turn 12 \(recent\)/.test(t.text) && /### Turn 10 \(recent\)/.test(t.text) && !/### Turn 9 \(recent\)/.test(t.text));
  assert.ok(t.text.includes("RESULT12"), "recent tool results kept");
  assert.ok(!t.text.includes("RESULT1 "), "oldest tool results left out");
  assert.ok(/Tools: Read file1\.js/.test(t.text), "oldest turn still lists its tools");
  assert.ok(/Files changed: file1\.js \(modified \+3\/−1\)/.test(t.text));
  const recent = t.text.split("### Turn 12")[1].length;
  const old = t.text.split("### Turn 1\n")[1].split("### Turn 2")[0].length;
  assert.ok(recent > old * 3, "recent " + recent + " vs old " + old);
});

test("a message steered into a running turn joins that turn instead of starting a new one", () => {
  const log = [...turn(1), { cls: "user", text: "task 2" }, { cls: "tool", name: "Read", label: "Read a.js", ok: true, text: "x" }, { cls: "user", text: "also fix b.js", steered: true }, { cls: "assistant", text: "done 2" }];
  const t = c.buildTranscript({ log }, { recentTurns: 3, maxChars: 1e9 });
  assert.strictEqual(t.turns, 2);
  assert.ok(/User: task 2\n\n\[Added while working\] also fix b\.js/.test(t.text), t.text);
  assert.ok(t.text.includes("done 2"));
});

test("a long transcript shrinks from the oldest end and keeps the latest turn", () => {
  const log = [];
  for (let i = 1; i <= 30; i++) log.push(...turn(i, true));
  const t = c.buildTranscript({ log }, { recentTurns: 3, maxChars: 12000 });
  assert.ok(t.text.length <= 12000, t.text.length);
  assert.ok(t.text.includes("task 30"), "latest turn kept");
  assert.ok(/oldest turns? left out/.test(t.text));
});

test("an earlier summary is carried forward and replaces what it covered; failed /compress entries are skipped", () => {
  const log = [...turn(1), { cls: "sys", compressed: true, summary: "EARLIER SUMMARY" }, ...turn(2), { cls: "user", text: "/compress", command: true }, { cls: "err", text: "Could not compress" }, ...turn(3)];
  const t = c.buildTranscript({ log }, {});
  assert.ok(t.hadSummary && t.text.includes("EARLIER SUMMARY"));
  assert.ok(!t.text.includes("task 1"), "covered turn not repeated");
  assert.strictEqual(t.turns, 2);
  assert.ok(!/Could not compress/.test(t.text));
  // Log trimmed past the marker: the summary is found in the history instead.
  const h = c.summaryHistory("FROM HISTORY", 4);
  assert.ok(h[0].summary && h[0].content.includes("4 earlier turns"));
  const t2 = c.buildTranscript({ log: turn(5), history: h }, {});
  assert.ok(t2.text.includes("## Summary from an earlier /compress\nFROM HISTORY"), t2.text.slice(0, 200));
});

test("summaryMessages asks for brief old work and detailed recent work, with the focus", () => {
  const m = c.summaryMessages("TRANSCRIPT", "the build script");
  assert.strictEqual(m.length, 2);
  assert.ok(/most recent turns in much greater detail/.test(m[1].content));
  assert.ok(m[1].content.includes("TRANSCRIPT") && m[1].content.includes("the build script"));
});
