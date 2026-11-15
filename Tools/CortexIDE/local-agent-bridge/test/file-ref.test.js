"use strict";

// lib/file-ref.js: finding file paths in chat text for the panel's right-click / Ctrl+click "open file".

const path = require("path");
const assert = require("assert");
const { test, EXT } = require("./harness");
const F = require(path.join(EXT, "lib", "file-ref"));

const refs = (t) => F.all(t).map((r) => [r.path, r.line, r.col]);

test("Windows paths, including folders with spaces, and line suffixes", () => {
  assert.deepStrictEqual(refs("Edited D:\\games\\Ai assisted toolkit\\Tools\\x.js and more"), [["D:\\games\\Ai assisted toolkit\\Tools\\x.js", 0, 0]]);
  assert.deepStrictEqual(refs("D:\\a b\\lib\\agent.js:142:function toolLabel(c) {"), [["D:\\a b\\lib\\agent.js", 142, 0]]);
  assert.deepStrictEqual(refs("C:\\Users\\Arend\\.claude"), [["C:\\Users\\Arend\\.claude", 0, 0]]);
  assert.deepStrictEqual(refs("\\\\server\\share\\a.txt"), [["\\\\server\\share\\a.txt", 0, 0]]);
});

test("relative paths, grep lines, (line,col), #L, file:// and ~", () => {
  assert.deepStrictEqual(refs("lib/agent.js:222:    const label"), [["lib/agent.js", 222, 0]]);
  assert.deepStrictEqual(refs("foo(lib/x.ts(3,4))"), [["lib/x.ts", 3, 4]]);
  assert.deepStrictEqual(refs("~/notes.md#L5"), [["~/notes.md", 5, 0]]);
  assert.deepStrictEqual(refs("see `test/run.js`."), [["test/run.js", 0, 0]]);
  assert.deepStrictEqual(refs("file:///D:/a%20b/c.png)."), [["D:/a b/c.png", 0, 0]]);
  assert.deepStrictEqual(refs("Cursor_Bp5QOImi3d.png"), [["Cursor_Bp5QOImi3d.png", 0, 0]]);
});

test("not files: URLs, e-mail, versions, abbreviations", () => {
  assert.deepStrictEqual(refs("see https://github.com/a/b.js now"), []);
  assert.deepStrictEqual(refs("user@host.com"), []);
  assert.deepStrictEqual(refs("version 2.10.0 done"), []);
  assert.deepStrictEqual(refs("e.g. this"), []);
});

test("find() picks the path under the pointer; whole() wants nothing else", () => {
  const line = "changed a.js and lib/b.ts:7 today";
  assert.strictEqual(F.find(line, line.indexOf("b.ts")).path, "lib/b.ts");
  assert.strictEqual(F.find(line, line.indexOf("a.js") + 1).path, "a.js");
  assert.strictEqual(F.find(line, 1), null, "pointer on a plain word");
  assert.strictEqual(F.find(line).path, "a.js", "no pointer: the first path");
  assert.strictEqual(F.find(line, line.indexOf("today") + 2), null);
  assert.strictEqual(F.whole("D:\\games\\Ai assisted toolkit\\README.md").path, "D:\\games\\Ai assisted toolkit\\README.md");
  assert.strictEqual(F.whole("src/x.js (3 edits)"), null, "a MultiEdit label is not one path");
  assert.strictEqual(F.whole("npm test"), null);
});

test("resolve(): absolute, ~, then the first workspace root that has it", () => {
  const have = new Set([path.join("C:\\ws2", "lib", "x.js"), "D:\\abs\\y.md", path.join("C:\\home", "n.md")]);
  const o = { exists: (p) => have.has(p), home: "C:\\home", join: path.join };
  assert.strictEqual(F.resolve("lib/x.js", ["C:\\ws1", "C:\\ws2"], o), path.join("C:\\ws2", "lib", "x.js"));
  assert.strictEqual(F.resolve("./lib/x.js", ["C:\\ws2"], o), path.join("C:\\ws2", "lib", "x.js"));
  assert.strictEqual(F.resolve("D:\\abs\\y.md", [], o), "D:\\abs\\y.md");
  assert.strictEqual(F.resolve("D:\\abs\\missing.md", ["C:\\ws2"], o), null);
  assert.strictEqual(F.resolve("~/n.md", [], o), path.join("C:\\home", "n.md"));
  assert.strictEqual(F.resolve("nope.js", ["C:\\ws1"], o), null);
});
