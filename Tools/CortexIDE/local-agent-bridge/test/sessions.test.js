"use strict";

// Chat history cache (lib/sessions.js): per-chat files + index, per-chat model, crash recovery,
// pruning, search, and the Claude Code session listing.

const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { test, after, EXT } = require("./harness");
const { SessionStore, slug, titleFrom, listClaudeCodeSessions, readMaster, listWorkspaces, readForeignChat } = require(path.join(EXT, "lib", "sessions"));

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "sessions-test-"));
after(() => fs.rmSync(tmp, { recursive: true, force: true }));
let n = 0;
const store = (opts = {}) => new SessionStore({ root: path.join(tmp, "r" + n++), workspace: "D:\\games\\proj", ...opts });

test("slug matches Claude Code's project folder naming", () => {
  assert.strictEqual(slug("D:\\games\\Ai assisted toolkit"), "D--games-Ai-assisted-toolkit");
  assert.strictEqual(slug(""), "no-workspace");
});

test("titleFrom: first non-empty line, markdown stripped, capped", () => {
  assert.strictEqual(titleFrom("\n\n## Fix the *build*\nmore"), "Fix the build");
  assert.strictEqual(titleFrom(""), "New chat");
  const long = titleFrom("word ".repeat(40));
  assert.ok(long.length <= 60 && long.endsWith("…"), long);
});

test("create / get / save: each chat keeps its own model and log", () => {
  const s = store();
  const a = s.create({ provider: "anthropic", model: "claude-opus-5-5", title: "A" });
  const b = s.create({ provider: "ollama", model: "qwen3:32b", title: "B" });
  a.log.push({ cls: "user", text: "hello from a" });
  s.save(a);
  assert.strictEqual(s.get(a.id).model, "claude-opus-5-5");
  assert.strictEqual(s.get(b.id).model, "qwen3:32b");
  assert.strictEqual(s.get(a.id).turns, 1);
  assert.deepStrictEqual(s.get(b.id).log, []);
  // one folder per chat: session.json + sub-index
  assert.ok(fs.existsSync(path.join(s.dir, "sessions", a.id, "session.json")));
  assert.strictEqual(JSON.parse(fs.readFileSync(path.join(s.dir, "sessions", a.id, "index.json"), "utf8")).model, "claude-opus-5-5");
  // index.json holds metadata only, never the log
  const idx = JSON.parse(fs.readFileSync(path.join(s.dir, "index.json"), "utf8"));
  assert.strictEqual(idx.sessions.length, 2);
  assert.ok(!("log" in idx.sessions[0]));
  assert.strictEqual(s.get("nope"), null);
});

test("update patches index and file; list puts pinned first then newest", () => {
  const s = store();
  const a = s.create({ title: "old" });
  const b = s.create({ title: "new" });
  s.update(b.id, { updated: Date.now() + 1000 });
  assert.deepStrictEqual(s.list().map((e) => e.id), [b.id, a.id]);
  s.update(a.id, { pinned: true, title: "renamed" });
  assert.deepStrictEqual(s.list().map((e) => e.id), [a.id, b.id]);
  // a fresh store reads the same thing back from disk
  const again = new SessionStore({ root: s.root, workspace: s.workspace });
  assert.strictEqual(again.get(a.id).title, "renamed");
  assert.strictEqual(again.get(a.id).pinned, true);
});

test("a chat left running when the editor closed loads as stopped", () => {
  const s = store();
  const a = s.create({ status: "running" });
  const again = new SessionStore({ root: s.root, workspace: s.workspace });
  assert.strictEqual(again.meta(a.id).status, "stopped");
});

test("a missing or damaged index.json is rebuilt from the session files", () => {
  const s = store();
  const a = s.create({ title: "survivor", model: "m1" });
  fs.writeFileSync(path.join(s.dir, "index.json"), "{ not json");
  const again = new SessionStore({ root: s.root, workspace: s.workspace });
  assert.deepStrictEqual(again.list().map((e) => [e.id, e.title, e.model]), [[a.id, "survivor", "m1"]]);
});

test("remove deletes the file and the entry", () => {
  const s = store();
  const a = s.create({});
  assert.strictEqual(s.remove(a.id), true);
  assert.strictEqual(s.remove(a.id), false);
  assert.ok(!fs.existsSync(s.file(a.id)));
  assert.strictEqual(s.list().length, 0);
});

test("prune drops the oldest closed, unpinned, idle chats past the limit", () => {
  const s = store({ limit: 10 });
  const keep = s.create({ open: false, pinned: true });
  s.update(keep.id, { updated: 1 });
  const running = s.create({ open: false });
  s.update(running.id, { status: "running", updated: 2 });
  const ids = [];
  for (let i = 0; i < 12; i++) {
    const c = s.create({ open: false });
    s.update(c.id, { updated: 100 + i });
    ids.push(c.id);
  }
  s.prune();
  const left = s.list().map((e) => e.id);
  assert.strictEqual(left.length, 10);
  assert.ok(left.includes(keep.id), "pinned survives");
  assert.ok(left.includes(running.id), "running survives");
  assert.ok(!left.includes(ids[0]) && !left.includes(ids[3]), "oldest go first");
  assert.ok(left.includes(ids[11]));
});

test("search matches title, model and user/assistant text; all words must match", () => {
  const s = store();
  const a = s.create({ title: "Fix build", model: "claude-opus-5-5" });
  a.log.push({ cls: "user", text: "the linker fails" }, { cls: "tool", text: "secret tool output" });
  s.save(a);
  s.create({ title: "Docs", model: "qwen3" });
  assert.deepStrictEqual(s.search("linker opus").map((e) => e.id), [a.id]);
  assert.strictEqual(s.search("secret").length, 0, "tool output is not indexed");
  assert.strictEqual(s.search("").length, 2);
});

test("master index lists every workspace folder; rebuilt when damaged", () => {
  const root = path.join(tmp, "master");
  const a = new SessionStore({ root, workspace: "D:\\one" });
  const b = new SessionStore({ root, workspace: "D:\\two" });
  a.create({ title: "x" });
  a.create({ title: "y" });
  b.create({ title: "z" });
  const m = readMaster(root);
  const by = Object.fromEntries(m.workspaces.map((w) => [w.slug, w]));
  assert.strictEqual(by[slug("D:\\one")].chats, 2);
  assert.strictEqual(by[slug("D:\\two")].chats, 1);
  assert.strictEqual(by[slug("D:\\one")].workspace, "D:\\one");
  assert.strictEqual(by[slug("D:\\one")].dir, a.dir);
  fs.writeFileSync(path.join(root, "index.json"), "garbage");
  assert.strictEqual(readMaster(root).workspaces.length, 2);
});

test("sidebar tree: every folder with chats, current folders first (empty ones too), deleted chats left out", () => {
  const root = path.join(tmp, "tree");
  const a = new SessionStore({ root, workspace: "D:\\one" });
  const b = new SessionStore({ root, workspace: "D:\\two" });
  const a1 = a.create({ title: "a1", model: "m1", group: "g" });
  const a2 = a.create({ title: "a2", group: "g" });
  const gone = a.create({ title: "gone" });
  a.remove(gone.id);
  const b1 = b.create({ title: "b1", pinned: true });
  b.update(b1.id, { updated: Date.now() + 1000 }); // b is the newest folder
  // a1 "running" in a window that is gone (written straight into the main index)
  const mainA = JSON.parse(fs.readFileSync(a.mainFile(), "utf8"));
  Object.assign(mainA.sessions.find((e) => e.id === a1.id), { status: "running", pid: 999999 });
  fs.writeFileSync(a.mainFile(), JSON.stringify(mainA));
  const t = listWorkspaces({ root, current: ["D:\\three", "D:\\one"] });
  assert.deepStrictEqual(t.map((w) => w.name), ["three", "one", "two"], "current folders in window order, then newest");
  assert.strictEqual(t[0].chats.length, 0, "an open folder without chats is listed (No agents yet)");
  assert.ok(t[0].current && t[1].current && !t[2].current);
  assert.deepStrictEqual(t[1].chats.map((c) => c.title).sort(), ["a1", "a2"], "the deleted chat is not listed");
  assert.strictEqual(t[1].chats.find((c) => c.id === a1.id).group, "g");
  assert.strictEqual(t[2].chats[0].pinned, true);
  assert.strictEqual(t[2].workspace, "D:\\two");
  const other = new SessionStore({ root, workspace: "D:\\one" });
  other.update(a2.id, { status: "running" }); // stamped with this (live) process
  const t2 = listWorkspaces({ root });
  const one = t2.find((w) => w.name === "one");
  assert.strictEqual(one.running, 1, "a live running chat counts; the dead window's does not");
  // read-only access to another folder's chat
  b.save({ ...b.get(b1.id), log: [{ cls: "user", text: "hello" }] });
  const f = readForeignChat(root, slug("D:\\two"), b1.id);
  assert.strictEqual(f.workspace, "D:\\two");
  assert.strictEqual(f.log[0].text, "hello");
  assert.strictEqual(readForeignChat(root, slug("D:\\two"), "nope"), null);
});

test("legacy flat sessions/<id>.json moves into its own chat folder", () => {
  const s = store();
  const a = s.create({ title: "old style" });
  // Fake a 2.7.0 layout: the chat as one flat file, no folder.
  const flat = path.join(s.dir, "sessions", a.id + ".json");
  fs.writeFileSync(flat, fs.readFileSync(s.file(a.id)));
  fs.rmSync(s.chatDir(a.id), { recursive: true });
  fs.unlinkSync(path.join(s.dir, "index.json"));
  const again = new SessionStore({ root: s.root, workspace: s.workspace });
  assert.strictEqual(again.get(a.id).title, "old style");
  assert.ok(fs.existsSync(again.file(a.id)));
  assert.ok(!fs.existsSync(flat));
});

test("claims: a running chat holds its files; others are refused until it finishes", () => {
  const s = store();
  const a = s.create({ title: "Refactor", model: "qwen3", status: "running" });
  const b = s.create({ title: "Docs", status: "running" });
  const file = path.join(tmp, "shared.js");
  assert.strictEqual(s.claim(a.id, file), null);
  assert.strictEqual(s.claim(a.id, file), null, "owner may keep editing");
  // Windows paths are case-insensitive: the same file in other case is the same claim.
  const o = s.claim(b.id, process.platform === "win32" ? file.toUpperCase() : file);
  assert.ok(o && o.id === a.id && o.title === "Refactor" && o.model === "qwen3", JSON.stringify(o));
  // the main index on disk carries the claim, so other windows see it
  const main = JSON.parse(fs.readFileSync(s.mainFile(), "utf8"));
  assert.strictEqual(Object.values(main.claims)[0].id, a.id);
  assert.deepStrictEqual(s.claimsOf(a.id), [path.resolve(file)]);
  // the sub-index of the owner records the file, not the refused chat's
  assert.strictEqual(Object.values(s.subIndex(a.id).files)[0].edits, 2);
  assert.deepStrictEqual(s.subIndex(b.id).files, {});
  assert.deepStrictEqual(s.release(a.id), [path.resolve(file)]);
  assert.strictEqual(s.claim(b.id, file), null, "free once released");
});

test("claims of a chat that is no longer running, or of a dead process, do not block", () => {
  const s = store();
  const a = s.create({ status: "running" });
  const b = s.create({ status: "running" });
  const file = path.join(tmp, "f.js");
  s.claim(a.id, file);
  s.update(a.id, { status: "done" }); // finished without releasing
  assert.strictEqual(s.claim(b.id, file), null);
  // a claim written by another editor process that has exited
  const g = path.join(tmp, "g.js");
  const main = JSON.parse(fs.readFileSync(s.mainFile(), "utf8"));
  main.claims["ghost"] = { id: "other", path: g, pid: 999999, since: 1 };
  fs.writeFileSync(s.mainFile(), JSON.stringify(main));
  assert.strictEqual(s.claim(b.id, g), null);
  const fresh = new SessionStore({ root: s.root, workspace: s.workspace });
  fresh.load();
  assert.ok(!fresh.claims.ghost, "dead claims are dropped on load");
});

test("per-chat progress.md, turns and overlaps live in each chat's own folder", () => {
  const s = store();
  const a = s.create({ title: "A", model: "m-a", status: "running" });
  const b = s.create({ title: "B", status: "running" });
  const pa = s.writeProgress(a.id, "did A");
  const pb = s.writeProgress(b.id, "did B");
  assert.notStrictEqual(pa, pb);
  assert.ok(fs.readFileSync(pa, "utf8").includes("did A") && fs.readFileSync(pa, "utf8").includes("m-a"));
  assert.ok(!fs.readFileSync(pb, "utf8").includes("did A"));
  assert.strictEqual(s.subIndex(a.id).progress, pa);
  s.recordTurn(a.id, { prompt: "go", files: ["x"] });
  assert.strictEqual(s.subIndex(a.id).turns[0].prompt, "go");
  // Saving the chat writes its header (with a numeric turn count) into the sub-index; the list stays.
  const full = s.get(a.id);
  full.log = [{ cls: "user", text: "go" }];
  s.save(full);
  s.update(a.id, { status: "done" });
  assert.strictEqual(s.subIndex(a.id).turns.length, 1, "header writes keep the list of turns");
  assert.strictEqual(s.subIndex(a.id).turnCount, 1);
  s.touchFile(a.id, path.join(tmp, "one.js"));
  s.touchFile(b.id, path.join(tmp, "one.js"));
  s.touchFile(b.id, path.join(tmp, "two.js"));
  const ov = s.overlaps(a.id);
  assert.deepStrictEqual(ov.map((o) => [o.id, o.files.map((f) => path.basename(f))]), [[b.id, ["one.js"]]]);
  s.remove(a.id);
  assert.ok(!fs.existsSync(s.chatDir(a.id)), "remove deletes the whole chat folder");
});

// ---- two windows on one workspace ------------------------------------------------------------
// Window B is a second store in this process, stamped with another live pid (our parent), so it
// behaves like a second CortexIDE window: each keeps its own in-memory copy of the main index.
const twoWindows = () => {
  const root = path.join(tmp, "win" + n++);
  const ws = "D:\\games\\shared";
  const a = new SessionStore({ root, workspace: ws });
  const b = new SessionStore({ root, workspace: ws, pid: process.ppid });
  a.load();
  b.load();
  return { a, b, fresh: () => new SessionStore({ root, workspace: ws }) };
};
const ids = (st) => st.list().map((e) => e.id).sort();

test("two windows: chats created in both survive; neither write drops the other's", () => {
  const { a, b, fresh } = twoWindows();
  const a1 = a.create({ title: "A1" });
  const b1 = b.create({ title: "B1" }); // B's copy was loaded before A1 existed
  const a2 = a.create({ title: "A2" });
  const b2 = b.create({ title: "B2" });
  const all = [a1.id, a2.id, b1.id, b2.id].sort();
  assert.deepStrictEqual(ids(fresh()), all, "main index on disk");
  assert.deepStrictEqual(ids(a), all, "window A sees B's chats");
  assert.deepStrictEqual(ids(b), all, "window B sees A's chats");
  // Saving a long-loaded chat object in B does not bring back A's view of the world either.
  const s = b.get(b1.id);
  s.log.push({ cls: "user", text: "hi" });
  b.save(s);
  assert.deepStrictEqual(ids(fresh()), all);
});

test("two windows: a chat deleted in one stays deleted (tombstone), even if the other saves", () => {
  const { a, b, fresh } = twoWindows();
  const x = a.create({ title: "doomed" });
  const y = a.create({ title: "kept" });
  assert.deepStrictEqual(ids(b), [x.id, y.id].sort());
  const held = b.get(y.id); // B still holds its copy of the list with x in it
  assert.strictEqual(a.remove(x.id), true);
  b.save(held);
  b.create({ title: "new in B" });
  assert.ok(!ids(fresh()).includes(x.id), "deleted chat came back");
  assert.ok(!ids(b).includes(x.id));
  assert.ok(JSON.parse(fs.readFileSync(a.mainFile(), "utf8")).removed[x.id], "tombstone written");
});

test("two windows: a rename/pin in one is kept when the other saves its running copy", () => {
  const { a, b, fresh } = twoWindows();
  const s = b.create({ title: "Run", status: "running" });
  a.update(s.id, { pinned: true, title: "Renamed in A" });
  s.log.push({ cls: "user", text: "still working" }); // B's live object knows nothing of the pin
  b.save(s);
  const e = fresh().meta(s.id);
  assert.strictEqual(e.pinned, true);
  assert.strictEqual(e.title, "Renamed in A");
  assert.strictEqual(e.turns, 1, "B's own progress is kept too");
});

test("two windows: claims are checked and taken under one lock; B's claims survive A's writes", () => {
  const { a, b } = twoWindows();
  const file = path.join(tmp, "both.js");
  const sb = b.create({ title: "B edits", status: "running" });
  const sa = a.create({ title: "A edits", status: "running" });
  assert.strictEqual(b.claim(sb.id, file), null);
  a.create({ title: "noise" }); // A writes the main index from its own copy
  a.update(sa.id, { pinned: true });
  const o = a.claim(sa.id, file);
  assert.ok(o && o.id === sb.id && o.title === "B edits", JSON.stringify(o));
  assert.strictEqual(a.remove(sb.id), false, "A may not delete a chat B is running");
  assert.deepStrictEqual(b.release(sb.id), [path.resolve(file)]);
  assert.strictEqual(a.claim(sa.id, file), null, "free once B released it");
});

test("a chat folder missing from the main index is listed again from its sub-index", () => {
  const { a, fresh } = twoWindows();
  const x = a.create({ title: "orphan", model: "m-x" });
  const y = a.create({ title: "listed" });
  const main = JSON.parse(fs.readFileSync(a.mainFile(), "utf8"));
  main.sessions = main.sessions.filter((e) => e.id !== x.id); // a write that lost the race (pre-2.7.2)
  fs.writeFileSync(a.mainFile(), JSON.stringify(main));
  const f = fresh();
  assert.deepStrictEqual(ids(f), [x.id, y.id].sort());
  assert.strictEqual(f.meta(x.id).model, "m-x", "header comes from the sub-index");
});

test("a lock left by a dead process does not block writes", () => {
  const { a } = twoWindows();
  a.create({ title: "first" });
  fs.writeFileSync(a.mainFile() + ".lock", "999999");
  const t = Date.now();
  a.create({ title: "second" });
  assert.ok(Date.now() - t < 1000, "waited on a dead lock");
  assert.ok(!fs.existsSync(a.mainFile() + ".lock"), "lock released");
  assert.strictEqual(a.list().length, 2);
});

test("listClaudeCodeSessions reads ~/.claude/projects/<slug>/*.jsonl newest first", () => {
  const home = path.join(tmp, "home");
  const dir = path.join(home, ".claude", "projects", slug("D:\\w"));
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "old.jsonl"), "{}");
  fs.writeFileSync(path.join(dir, "new.jsonl"), "{}");
  fs.writeFileSync(path.join(dir, "notes.txt"), "x");
  const t = Date.now() / 1000;
  fs.utimesSync(path.join(dir, "old.jsonl"), t - 100, t - 100);
  const got = listClaudeCodeSessions("D:\\w", { home });
  assert.deepStrictEqual(got.map((x) => x.sessionId), ["new", "old"]);
  assert.strictEqual(got[0].project, slug("D:\\w"));
  assert.deepStrictEqual(listClaudeCodeSessions("D:\\elsewhere", { home }), []);
});
