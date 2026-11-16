"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const assert = require("assert");
const { test, after, EXT } = require("./harness");
const { ToolContext, execTool, defaultRgPath, canonName, normArgs, clip } = require(path.join(EXT, "lib", "agent-tools"));

const WIN = process.platform === "win32";
const NOT_WIN = WIN ? undefined : "Shell tool runs PowerShell on Windows";
const appRoot = process.env.CORTEXIDE_APP || "D:\\tools\\CortexIDE\\resources\\app";

const ws = fs.mkdtempSync(path.join(os.tmpdir(), "agent-ws-"));
const outside = fs.mkdtempSync(path.join(os.tmpdir(), "agent-out-"));
after(() => {
  fs.rmSync(ws, { recursive: true, force: true });
  fs.rmSync(outside, { recursive: true, force: true });
});
fs.mkdirSync(path.join(ws, "src", "Mutations"), { recursive: true });
fs.writeFileSync(path.join(ws, "src", "Mutations", "Gelatinous.cs"), "class Gelatinous {\r\n    int Level = 1;\r\n    void Apply() { }\r\n}\r\n");
fs.writeFileSync(path.join(ws, "src", "util.js"), "function add(a, b) {\n  return a - b;\n}\nmodule.exports = { add };\n");
fs.writeFileSync(path.join(ws, "dup.txt"), "x\nx\n");
fs.writeFileSync(path.join(outside, "secret.txt"), "outside");

const rg = defaultRgPath(appRoot);
const ctx = new ToolContext({
  roots: [ws],
  rgPath: rg,
  requireRead: false, // the edit tests below predate the read-before-edit guard; it has its own tests
  skills: () => [{ name: "canvas", description: "Make canvases", instructions: "Step 1…", file: "x", dir: "y" }],
});

test("canonName maps aliases and keeps unknown names", () => {
  assert.strictEqual(canonName("read_file"), "Read");
  assert.strictEqual(canonName("run_terminal_cmd"), "Shell");
  assert.strictEqual(canonName("EDIT_FILE"), "StrReplace");
  assert.strictEqual(canonName("StrReplace"), "StrReplace");
  assert.strictEqual(canonName("nope"), "nope");
});

test("normArgs maps Cursor / Claude argument names", () => {
  const a = normArgs("Write", { target_file: "a.txt", content: "hi" });
  assert.strictEqual(a.path, "a.txt");
  assert.strictEqual(a.contents, "hi");
  assert.strictEqual(normArgs("Glob", { name: "Foo" }).pattern, "Foo");
  assert.strictEqual(normArgs("Shell", { cmd: "dir", working_directory: "C:\\" }).cwd, "C:\\");
});

test("clip keeps head and tail", () => {
  const s = "a".repeat(100) + "b".repeat(100);
  const c = clip(s, 50);
  assert.ok(c.startsWith("aaa") && c.endsWith("bbb") && c.includes("chars omitted"), c);
});

test("rg resolved from the CortexIDE bundle", () => assert.ok(/ripgrep-win32-x64/.test(rg), rg), {
  skip: fs.existsSync(appRoot) ? undefined : "no CortexIDE at " + appRoot,
});

test("Read relative path with line window", async () => {
  const r = await execTool(ctx, "read_file", { target_file: "src/util.js", offset: 2, limit: 1 });
  assert.ok(r.includes("lines 2-2 of 5") && r.includes("return a - b"), r);
});

test("Read missing file suggests near names", async () => {
  const r = await execTool(ctx, "Read", { path: "src/utils.js" });
  assert.ok(r.startsWith("error: not found") && r.includes("util.js"), r);
});

test("LS lists folders first", async () => {
  const r = await execTool(ctx, "LS", { path: "." });
  assert.ok(/src\/[\s\S]*dup\.txt/.test(r), r);
});

test("Glob **/*.cs", async () => {
  const r = await execTool(ctx, "Glob", { glob_pattern: "**/*.cs" });
  assert.ok(r.includes("Gelatinous.cs"), r);
});

test("Glob bare name becomes contains-match", async () => {
  const r = await execTool(ctx, "find_file", { name: "Gelatinous" });
  assert.ok(r.includes("Gelatinous.cs"), r);
});

test("Glob falls back to the JS walker without ripgrep", async () => {
  const noRg = new ToolContext({ roots: [ws], rgPath: path.join(ws, "missing-rg.exe") });
  const r = await execTool(noRg, "Glob", { pattern: "**/*.js" });
  assert.ok(r.includes("util.js"), r);
});

test("Grep regex with glob filter", async () => {
  const r = await execTool(ctx, "Grep", { pattern: "int\\s+Level", glob: "*.cs" });
  assert.ok(/Gelatinous\.cs:2:/.test(r), r);
});

test("Grep invalid regex falls back to literal", async () => {
  const r = await execTool(ctx, "grep", { query: "add(a," });
  assert.ok(r.includes("util.js:1:"), r);
});

test("StrReplace on CRLF file with LF old_string keeps CRLF", async () => {
  const r = await execTool(ctx, "StrReplace", { path: "src/Mutations/Gelatinous.cs", old_string: "int Level = 1;\n    void", new_string: "int Level = 2;\n    void" });
  assert.ok(r.startsWith("edited"), r);
  assert.ok(fs.readFileSync(path.join(ws, "src", "Mutations", "Gelatinous.cs"), "utf8").includes("int Level = 2;\r\n"), "CRLF kept");
});

test("StrReplace ambiguous match refused", async () => {
  const r = await execTool(ctx, "StrReplace", { path: "dup.txt", old_string: "x", new_string: "y" });
  assert.ok(/matches 2 places/.test(r), r);
});

test("StrReplace not-found reports error", async () => {
  const r = await execTool(ctx, "edit_file", { path: "src/util.js", old_str: "return a -  b;", new_str: "return a + b;" });
  assert.ok(r.startsWith("error: old_string not found"), r);
});

test("Write creates nested file", async () => {
  const r = await execTool(ctx, "Write", { path: "out/new/file.txt", content: "hi" });
  assert.ok(r.startsWith("created") && fs.existsSync(path.join(ws, "out", "new", "file.txt")), r);
});

test("Write outside workspace denied", async () => {
  const r = await execTool(ctx, "Write", { path: path.join(outside, "x.txt"), contents: "no" });
  assert.ok(/outside the folders/.test(r) && /localAgentBridge\.agent\.writableRoots/.test(r), r);
  assert.ok(!fs.existsSync(path.join(outside, "x.txt")));
});

test("writableRoots allows writing outside the workspace", async () => {
  const c2 = new ToolContext({ roots: [ws], writableRoots: [outside] });
  const r = await execTool(c2, "Write", { path: path.join(outside, "ok.txt"), contents: "yes" });
  assert.ok(r.startsWith("created"), r);
});

test("Read outside workspace allowed (readAnywhere)", async () => {
  const r = await execTool(ctx, "Read", { path: path.join(outside, "secret.txt") });
  assert.ok(r.includes("outside"), r);
});

test("Read outside workspace refused with readAnywhere off", async () => {
  const c2 = new ToolContext({ roots: [ws], readAnywhere: false });
  const r = await execTool(c2, "Read", { path: path.join(outside, "secret.txt") });
  assert.ok(r.startsWith("error: reading outside"), r);
});

test("Shell exit code + output", async () => {
  const r = await execTool(ctx, "Shell", { command: "Write-Output hello; cmd /c exit 3" });
  assert.ok(r.startsWith("exit 3") && r.includes("hello"), r);
}, { skip: NOT_WIN });

test("Shell quoted exe gets & call operator", async () => {
  const r = await execTool(ctx, "run_terminal_cmd", { command: '"' + process.execPath + '" -e "console.log(6*7)"' });
  assert.ok(r.startsWith("exit 0") && r.includes("42"), r);
}, { skip: NOT_WIN });

test("Shell multi-line script + here-string", async () => {
  const r = await execTool(ctx, "Shell", { command: "$x = @'\nline one\nline two\n'@\nif ($x) {\n  ($x -split \"`n\").Count\n}" });
  assert.ok(r.startsWith("exit 0") && /\b2\b/.test(r), r);
}, { skip: NOT_WIN });

test("Shell failing cmdlet gives non-zero exit", async () => {
  const r = await execTool(ctx, "Shell", { command: "Get-Item C:\\definitely\\missing\\x -ErrorAction Stop" });
  assert.ok(!r.startsWith("exit 0"), r);
}, { skip: NOT_WIN });

test("Shell destructive command blocked", async () => {
  const r = await execTool(ctx, "Shell", { command: "Remove-Item C:\\ -Recurse -Force" });
  assert.ok(/blocked/.test(r), r);
});

test("Shell off / confirm-declined", async () => {
  const off = new ToolContext({ roots: [ws], shellMode: "off" });
  assert.ok(/Shell is disabled \(localAgentBridge\.agent\.shell = off\)/.test(await execTool(off, "Shell", { command: "dir" })));
  const confirm = new ToolContext({ roots: [ws], shellMode: "confirm", confirmShell: async () => false });
  assert.ok(/declined/.test(await execTool(confirm, "Shell", { command: "dir" })));
});

test("Shell cwd outside writable roots denied", async () => {
  const r = await execTool(ctx, "Shell", { command: "dir", cwd: outside });
  assert.ok(/outside the folders/.test(r), r);
});

test("Delete file", async () => {
  const r = await execTool(ctx, "Delete", { path: "dup.txt" });
  assert.ok(r.startsWith("deleted") && !fs.existsSync(path.join(ws, "dup.txt")), r);
});

test("list_skills / read_skill", async () => {
  assert.ok((await execTool(ctx, "list_skills", {})).includes("canvas"));
  assert.ok((await execTool(ctx, "read_skill", { name: "/canvas" })).includes("Step 1"));
  assert.ok((await execTool(ctx, "read_skill", { name: "nope" })).startsWith("error: no skill"));
});

test("unknown tool lists the available ones", async () => {
  const r = await execTool(ctx, "teleport", {});
  assert.ok(r.startsWith("error: unknown tool teleport") && r.includes("Read"), r);
});

// ---- 2.3: read-before-edit, line numbers, MultiEdit, TodoWrite, Grep modes, checkpoints ----

function fresh(files) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "agent-ws23-"));
  after(() => fs.rmSync(dir, { recursive: true, force: true }));
  for (const [rel, text] of Object.entries(files)) {
    fs.mkdirSync(path.dirname(path.join(dir, rel)), { recursive: true });
    fs.writeFileSync(path.join(dir, rel), text);
  }
  return { dir, ctx: new ToolContext({ roots: [dir], rgPath: rg }) };
}

test("Read numbers its lines", async () => {
  const { ctx: c } = fresh({ "a.js": "one\ntwo\nthree\n" });
  const r = await execTool(c, "Read", { path: "a.js", offset: 2, limit: 1 });
  assert.ok(/\n\s+2\ttwo\n/.test(r), r);
});

test("edits need a Read first, and a fresh one after the file changes", async () => {
  const { dir, ctx: c } = fresh({ "a.js": "function f() {\n  let x = 1;\n  return x;\n}\n" });
  // Unread file: a loose (re-indented) match is refused, a whole-file Write too ...
  let r = await execTool(c, "StrReplace", { path: "a.js", old_string: "let x = 1;\nreturn x;", new_string: "let x = 5;\nreturn x;" });
  assert.ok(/not found exactly .* not Read this file/.test(r), r);
  r = await execTool(c, "Write", { path: "a.js", contents: "boom" });
  assert.ok(/before overwriting it/.test(r), r);
  // ... but an exact unique match (e.g. copied from Grep output) is enough.
  r = await execTool(c, "StrReplace", { path: "a.js", old_string: "let x = 1;", new_string: "let x = 0;" });
  assert.ok(r.startsWith("edited"), r);
  fs.writeFileSync(path.join(dir, "a.js"), "let x = 1;\n");
  fs.utimesSync(path.join(dir, "a.js"), Date.now() / 1000 + 2, Date.now() / 1000 + 2);
  await execTool(c, "Read", { path: "a.js" });
  r = await execTool(c, "StrReplace", { path: "a.js", old_string: "1", new_string: "2" });
  assert.ok(r.startsWith("edited") && /\n\s+1\tlet x = 2;/.test(r), r);
  // Our own edit keeps the stamp current: a second edit needs no new Read.
  r = await execTool(c, "StrReplace", { path: "a.js", old_string: "2", new_string: "3" });
  assert.ok(r.startsWith("edited"), r);
  const later = Date.now() / 1000 + 5;
  fs.writeFileSync(path.join(dir, "a.js"), "let x = 9;\n");
  fs.utimesSync(path.join(dir, "a.js"), later, later);
  r = await execTool(c, "StrReplace", { path: "a.js", old_string: "9", new_string: "4" });
  assert.ok(/changed on disk since you last read it/.test(r), r);
  // New files need no Read.
  r = await execTool(c, "Write", { path: "new.txt", contents: "hi" });
  assert.ok(r.startsWith("created"), r);
});

test("StrReplace forgives copied line-number prefixes", async () => {
  const { dir, ctx: c } = fresh({ "m.py": "def f():\n    return 1\n" });
  await execTool(c, "Read", { path: "m.py" });
  const r = await execTool(c, "StrReplace", { path: "m.py", old_string: "   1\tdef f():\n   2\t    return 1", new_string: "   1\tdef f():\n   2\t    return 2" });
  assert.ok(r.startsWith("edited"), r);
  assert.strictEqual(fs.readFileSync(path.join(dir, "m.py"), "utf8"), "def f():\n    return 2\n");
});

test("MultiEdit applies all edits or none", async () => {
  const { dir, ctx: c } = fresh({ "c.cs": "int a = 1;\nint b = 2;\nint c = 3;\n" });
  await execTool(c, "Read", { path: "c.cs" });
  let r = await execTool(c, "MultiEdit", { path: "c.cs", edits: [{ old_string: "a = 1", new_string: "a = 10" }, { old_string: "nope", new_string: "x" }] });
  assert.ok(/^error: edit 2 of 2/.test(r) && /No edits were applied/.test(r), r);
  assert.ok(fs.readFileSync(path.join(dir, "c.cs"), "utf8").includes("a = 1;"));
  r = await execTool(c, "multi_edit", { file_path: "c.cs", edits: JSON.stringify([{ old_string: "a = 1", new_string: "a = 10" }, { old_str: "c = 3", new_str: "c = 30" }]) });
  assert.ok(r.startsWith("edited") && /2 edits/.test(r), r);
  assert.strictEqual(fs.readFileSync(path.join(dir, "c.cs"), "utf8"), "int a = 10;\nint b = 2;\nint c = 30;\n");
});

test("checkpoint keeps the pre-agent contents of every touched file", async () => {
  const { dir, ctx: c } = fresh({ "k.txt": "orig\n", "gone.txt": "bye\n" });
  await execTool(c, "Read", { path: "k.txt" });
  await execTool(c, "StrReplace", { path: "k.txt", old_string: "orig", new_string: "v1" });
  await execTool(c, "StrReplace", { path: "k.txt", old_string: "v1", new_string: "v2" });
  await execTool(c, "Write", { path: "made.txt", contents: "new" });
  await execTool(c, "Delete", { path: "gone.txt" });
  assert.strictEqual(c.checkpoint.get(path.join(dir, "k.txt")).before, "orig\n");
  assert.strictEqual(c.checkpoint.get(path.join(dir, "made.txt")).before, null);
  assert.strictEqual(c.checkpoint.get(path.join(dir, "gone.txt")).before, "bye\n");
});

test("TodoWrite normalises statuses and renders the list", async () => {
  const { ctx: c } = fresh({});
  const r = await execTool(c, "todo_write", { todos: [{ content: "Find bug", status: "done" }, { content: "Fix it", status: "in-progress" }, "Run tests"] });
  assert.deepStrictEqual(c.todos.map((t) => t.status), ["completed", "in_progress", "pending"]);
  assert.ok(/1\/3 done/.test(r) && r.includes("[>] Fix it"), r);
  assert.ok((await execTool(c, "TodoWrite", { todos: "not json" })).startsWith("error"));
});

test("Grep output modes, context and case", async () => {
  const { ctx: c } = fresh({ "x.txt": "alpha\nBeta\ngamma\n", "y.txt": "beta\n" });
  const files = await execTool(c, "Grep", { pattern: "beta", output_mode: "files_with_matches" });
  assert.ok(files.includes("x.txt") && files.includes("y.txt") && !/txt:\d/.test(files), files);
  const strict = await execTool(c, "Grep", { pattern: "beta", case_sensitive: true, output_mode: "files_with_matches" });
  assert.ok(strict.includes("y.txt") && !strict.includes("x.txt"), strict);
  const ctxOut = await execTool(c, "Grep", { pattern: "Beta", path: "x.txt", "-C": 1 });
  assert.ok(ctxOut.includes("alpha") && ctxOut.includes("gamma"), ctxOut);
  const noRg = new ToolContext({ roots: [c.roots[0]], rgPath: path.join(c.roots[0], "missing-rg.exe") });
  const counts = await execTool(noRg, "Grep", { pattern: "beta", output_mode: "count" });
  assert.ok(/x\.txt:1/.test(counts) && /y\.txt:1/.test(counts), counts);
});

test("StrReplace forgives wrong indentation and re-indents new_string", async () => {
  const { dir, ctx: c } = fresh({ "w.py": "class A:\n    def f(self):\n        x = 1\n        return x\n" });
  await execTool(c, "Read", { path: "w.py" });
  const r = await execTool(c, "StrReplace", { path: "w.py", old_string: "x = 1\nreturn x", new_string: "x = 2\nif x:\n    x += 1\nreturn x" });
  assert.ok(r.startsWith("edited") && /matched ignoring whitespace/.test(r), r);
  assert.strictEqual(fs.readFileSync(path.join(dir, "w.py"), "utf8"), "class A:\n    def f(self):\n        x = 2\n        if x:\n            x += 1\n        return x\n");
});

test("indentation-tolerant match refuses ambiguous or tiny anchors", async () => {
  const { ctx: c } = fresh({ "d.js": "if (a) {\n  go();\n}\nif (b) {\n    go();\n}\n" });
  await execTool(c, "Read", { path: "d.js" });
  let r = await execTool(c, "StrReplace", { path: "d.js", old_string: "go();\n}", new_string: "stop();\n}" });
  assert.ok(/several places/.test(r) || /matches 2 places/.test(r), r);
  r = await execTool(c, "StrReplace", { path: "d.js", old_string: "     go();", new_string: "x();" });
  assert.ok(r.startsWith("error"), r);
  // Spacing inside a line still has to match.
  r = await execTool(c, "StrReplace", { path: "d.js", old_string: "if (a)  {\n go();", new_string: "if (a) {\n  run();" });
  assert.ok(r.startsWith("error: old_string not found"), r);
});
