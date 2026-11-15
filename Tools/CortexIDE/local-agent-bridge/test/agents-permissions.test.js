"use strict";

// Unit tests for the opencode-style pieces: front matter, permission rules, named agents,
// custom slash commands, project instructions and saved tool output.

const fs = require("fs");
const os = require("os");
const path = require("path");
const assert = require("assert");
const { test, after, EXT } = require("./harness");
const fm = require(path.join(EXT, "lib", "frontmatter"));
const perms = require(path.join(EXT, "lib", "permissions"));
const agents = require(path.join(EXT, "lib", "agents"));
const commands = require(path.join(EXT, "lib", "commands"));
const instructions = require(path.join(EXT, "lib", "instructions"));
const toolOutput = require(path.join(EXT, "lib", "tool-output"));
const { ToolContext, execTool } = require(path.join(EXT, "lib", "agent-tools"));

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "agents-perms-"));
after(() => fs.rmSync(tmp, { recursive: true, force: true }));

function put(rel, text) {
  const p = path.join(tmp, rel);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, text);
  return p;
}

// ---- front matter -------------------------------------------------------------------------

test("frontmatter: scalars, inline and block lists, quoted keys, nested maps, | blocks", () => {
  const { data, body } = fm.parse(
    [
      "---",
      "description: Reviews code  # a comment",
      "mode: subagent",
      "steps: 12",
      "hidden: true",
      "tools: [Read, Grep]",
      "list:",
      "  - one",
      "  - 'two words'",
      "permission:",
      "  edit: deny",
      "  bash:",
      '    "git *": allow',
      "    rm *: deny",
      "rules:",
      "  - action: shell",
      "    resource: git push *",
      "    effect: ask",
      "note: |",
      "  line one",
      "  line two",
      "---",
      "",
      "Body text.",
    ].join("\n"),
  );
  assert.strictEqual(data.description, "Reviews code");
  assert.strictEqual(data.mode, "subagent");
  assert.strictEqual(data.steps, 12);
  assert.strictEqual(data.hidden, true);
  assert.deepStrictEqual(data.tools, ["Read", "Grep"]);
  assert.deepStrictEqual(data.list, ["one", "two words"]);
  assert.deepStrictEqual(data.permission, { edit: "deny", bash: { "git *": "allow", "rm *": "deny" } });
  assert.deepStrictEqual(data.rules, [{ action: "shell", resource: "git push *", effect: "ask" }]);
  assert.strictEqual(data.note, "line one\nline two");
  assert.strictEqual(body, "Body text.");
});

test("frontmatter: no block → empty data and the whole text as body; toolList forms", () => {
  assert.deepStrictEqual(fm.parse("\uFEFFjust text\n"), { data: {}, body: "just text" });
  const a = fm.toolList("Read, Grep Glob");
  assert.deepStrictEqual([...a.allow].sort(), ["glob", "grep", "read"]);
  const b = fm.toolList({ write: false, bash: false, read: true });
  assert.strictEqual(b.allow, null);
  assert.deepStrictEqual([...b.deny].sort(), ["bash", "write"]);
  assert.strictEqual(fm.toolList(undefined).allow, null);
});

// ---- permission rules -----------------------------------------------------------------------

const ws = path.join(tmp, "ws");
fs.mkdirSync(ws, { recursive: true });
const ev = (rules, tool, args, extra = {}) => perms.evaluate([...perms.DEFAULT_RULES, ...perms.normalize(rules)], tool, args, { roots: [ws], resolve: (p) => path.resolve(ws, p), ...extra });

test("permissions: normalize accepts the list, string and map forms (with aliases)", () => {
  const r = perms.normalize([{ action: "bash", resource: "git *", effect: "allow" }, "shell:rm *=deny", "edit=ask", { permission: "write", pattern: "*.md", decision: "allow" }, { action: "read", effect: "maybe" }]);
  assert.deepStrictEqual(r, [
    { action: "shell", resource: "git *", effect: "allow" },
    { action: "shell", resource: "rm *", effect: "deny" },
    { action: "edit", resource: "*", effect: "ask" },
    { action: "edit", resource: "*.md", effect: "allow" },
  ]);
  assert.deepStrictEqual(perms.normalize({ edit: "deny", bash: { "git *": "allow" } }), [
    { action: "edit", resource: "*", effect: "deny" },
    { action: "shell", resource: "git *", effect: "allow" },
  ]);
});

test("permissions: the last matching rule wins; no match falls back to allow", () => {
  assert.strictEqual(ev([], "Read", { path: "a.js" }).effect, "allow");
  assert.strictEqual(ev([{ action: "edit", resource: "*", effect: "deny" }, { action: "edit", resource: "docs/*", effect: "allow" }], "Write", { path: "docs/x.md" }).effect, "allow");
  assert.strictEqual(ev([{ action: "edit", resource: "docs/*", effect: "allow" }, { action: "edit", resource: "*", effect: "deny" }], "Write", { path: "docs/x.md" }).effect, "deny");
  assert.strictEqual(ev([{ action: "*", resource: "*", effect: "ask" }], "Grep", { pattern: "x" }).effect, "ask");
  // Tools outside the rules (TodoWrite, attempt_completion) are always allowed.
  assert.strictEqual(ev([{ action: "*", resource: "*", effect: "deny" }], "TodoWrite", { todos: [] }).effect, "allow");
});

test("permissions: reading .env asks by default; .env.example does not; a rule can turn it off", () => {
  assert.strictEqual(ev([], "Read", { path: ".env" }).effect, "ask");
  assert.strictEqual(ev([], "Read", { path: "cfg/.env.local" }).effect, "ask");
  assert.strictEqual(ev([], "Read", { path: ".env.example" }).effect, "allow");
  assert.strictEqual(ev([{ action: "read", resource: "*.env", effect: "allow" }], "Read", { path: ".env" }).effect, "allow");
});

test("permissions: chained shell commands are checked part by part; 'cmd *' matches the bare command", () => {
  const rules = [{ action: "shell", resource: "*", effect: "allow" }, { action: "shell", resource: "git push *", effect: "deny" }, { action: "shell", resource: "rm *", effect: "ask" }];
  assert.strictEqual(ev(rules, "Shell", { command: "git status && git push origin main" }).effect, "deny");
  assert.strictEqual(ev(rules, "Shell", { command: "git push" }).effect, "deny");
  const asked = ev(rules, "Shell", { command: "ls; rm -rf build | cat" });
  assert.strictEqual(asked.effect, "ask");
  assert.deepStrictEqual(asked.asked, ["rm -rf build"]);
  assert.strictEqual(ev(rules, "Shell", { command: 'echo "a && git push"' }).effect, "allow", "quoted text is not split");
  assert.deepStrictEqual(perms.splitShell('& "C:\\x y\\t.exe" a; $env:X=1; FOO=1 git log'), ['"C:\\x y\\t.exe" a', "git log"]);
  assert.strictEqual(perms.shellPrefix("git status --short"), "git status *");
  assert.strictEqual(perms.shellPrefix("npm -v"), "npm *");
  assert.strictEqual(perms.shellPrefix("node test/run.js"), "node *");
});

test("permissions: 'Allow always' approvals turn ask into allow but never override a deny", () => {
  const approved = perms.normalize([{ action: "shell", resource: "rm *", effect: "allow" }, { action: "shell", resource: "git push *", effect: "allow" }]);
  const rules = [{ action: "shell", resource: "rm *", effect: "ask" }, { action: "shell", resource: "git push *", effect: "deny" }];
  assert.strictEqual(ev(rules, "Shell", { command: "rm x" }, { approved }).effect, "allow");
  assert.strictEqual(ev(rules, "Shell", { command: "git push" }, { approved }).effect, "deny");
});

test("permissions: paths match absolute or workspace-relative; ~ expands; MCP and Task resources", () => {
  const abs = path.join(ws, "src", "a.js");
  assert.strictEqual(ev([{ action: "edit", resource: "src/*", effect: "deny" }], "Write", { path: abs }).effect, "deny");
  assert.strictEqual(ev([{ action: "edit", resource: abs.replace(/\\/g, "/"), effect: "deny" }], "Write", { path: "src/a.js" }).effect, "deny");
  const home = process.env.USERPROFILE || process.env.HOME;
  assert.strictEqual(ev([{ action: "read", resource: "~/secret/*", effect: "deny" }], "Read", { path: path.join(home, "secret", "k.txt") }).effect, "deny");
  assert.strictEqual(ev([{ action: "mcp", resource: "rea_*", effect: "ask" }], "McpCall", { server: "rea", tool: "decompile" }).effect, "ask");
  assert.strictEqual(ev([{ action: "subagent", resource: "reviewer", effect: "deny" }], "Task", { agent: "reviewer" }).effect, "deny");
  const r = ev([], "Write", { path: "src/a.js" });
  assert.deepStrictEqual(r.suggest, ["src/*"]);
});

test("ToolContext.permit: deny returns an error, ask prompts, 'always' is saved and not asked again", async () => {
  fs.writeFileSync(path.join(ws, "keep.txt"), "hello\n");
  fs.writeFileSync(path.join(ws, ".env"), "SECRET=1\n");
  const asks = [];
  const saved = [];
  let answer = "reject";
  const ctx = new ToolContext({
    roots: [ws],
    rgPath: "missing-rg",
    rules: [{ action: "edit", resource: "keep.txt", effect: "deny" }],
    confirmPermission: async (req) => {
      asks.push(req);
      return answer;
    },
    saveApproval: (add) => saved.push(...add),
  });
  const denied = await execTool(ctx, "Write", { path: "keep.txt", contents: "x" });
  assert.ok(/denied by the permission rule edit "keep.txt"/.test(denied), denied);
  assert.strictEqual(fs.readFileSync(path.join(ws, "keep.txt"), "utf8"), "hello\n");

  const refused = await execTool(ctx, "Read", { path: ".env" });
  assert.ok(/user denied Read/.test(refused), refused);
  assert.strictEqual(asks.length, 1);
  assert.strictEqual(asks[0].action, "read");

  answer = "always";
  const read = await execTool(ctx, "Read", { path: ".env" });
  assert.ok(read.includes("SECRET=1"), read);
  assert.deepStrictEqual(saved, [{ action: "read", resource: "*", effect: "allow" }]);
  await execTool(ctx, "Read", { path: ".env" });
  assert.strictEqual(asks.length, 2, "an approved pattern is not asked again");

  // An agent's own rules come after the settings' rules and win.
  ctx.withAgentRules([{ action: "read", resource: "keep.txt", effect: "deny" }]);
  assert.ok(/denied/.test(await execTool(ctx, "Read", { path: "keep.txt" })));
});

// ---- named agents ---------------------------------------------------------------------------

test("agents: built-ins, project files override global ones, disabled removes, built-in overrides merge", () => {
  const home = path.join(tmp, "home");
  const root = path.join(tmp, "proj");
  put("home/.cortexide/agents/reviewer.md", "---\ndescription: Global reviewer\nmode: subagent\n---\nGlobal prompt");
  put("proj/.cortexide/agents/reviewer.md", "---\ndescription: Project reviewer\nmode: subagent\ntools: Read, Grep\nsteps: 5\n---\nProject prompt");
  put("proj/.opencode/agents/explore.md", "---\ndisabled: true\n---\n");
  put("proj/.claude/agents/docs-writer.md", "---\nname: Docs Writer\ndescription: Writes docs\n---\nWrite docs.");
  put("proj/.opencode/agents/plan.md", "---\npermission:\n  bash:\n    \"npm test\": allow\n---\n");
  const list = agents.loadAgents([root], { home });
  const names = list.map((a) => a.name).sort();
  assert.deepStrictEqual(names, ["ask", "build", "docs-writer", "plan", "reviewer"]);
  const rev = agents.find(list, "@Reviewer");
  assert.strictEqual(rev.description, "Project reviewer");
  assert.strictEqual(rev.prompt, "Project prompt");
  assert.strictEqual(rev.steps, 5);
  assert.deepStrictEqual([...rev.allowTools].sort(), ["grep", "read"]);
  assert.strictEqual(agents.find(list, "docs-writer").mode, "subagent", ".claude/agents files are sub-agents");
  const plan = agents.find(list, "plan");
  assert.deepStrictEqual(plan.deny, agents.EDIT_TOOLS, "the override keeps the built-in's tool limits");
  assert.ok(plan.prompt.includes("Plan mode"), "an empty body keeps the built-in prompt");
  assert.deepStrictEqual(plan.rules[plan.rules.length - 1], { action: "shell", resource: "npm test", effect: "allow" });
  assert.deepStrictEqual(agents.subagentCatalog(list).sort(), ["- docs-writer: Writes docs", "- reviewer: Project reviewer"]);
});

test("agents: toolNames narrows (never widens) the set; opencode tool switches map to edit tools / Shell", () => {
  const all = ["Read", "Grep", "Shell", "StrReplace", "MultiEdit", "Write", "Delete", "TodoWrite", "attempt_completion"];
  assert.deepStrictEqual(agents.toolNames(agents.BUILTIN.plan, all), ["Read", "Grep", "Shell", "TodoWrite", "attempt_completion"]);
  assert.deepStrictEqual(agents.toolNames(agents.BUILTIN.ask, all), ["Read", "Grep", "TodoWrite", "attempt_completion"]);
  assert.deepStrictEqual(agents.toolNames(agents.BUILTIN.build, all), all);
  assert.deepStrictEqual(agents.toolNames({ allowTools: new Set(["read", "webfetch"]) }, all), ["Read", "TodoWrite", "attempt_completion"]);
  assert.deepStrictEqual(agents.toolNames({ denyTools: new Set(["write", "bash"]) }, all), ["Read", "Grep", "TodoWrite", "attempt_completion"]);
});

test("agents: forMessage picks @primary, routes @subagent through Task, else the composer mode", () => {
  const list = [...Object.values(agents.BUILTIN), { name: "reviewer", mode: "subagent", description: "r" }];
  const a = agents.forMessage(list, "@plan how should I split this?");
  assert.strictEqual(a.agent.name, "plan");
  assert.strictEqual(a.text, "how should I split this?");
  const b = agents.forMessage(list, "@reviewer check lib/");
  assert.strictEqual(b.agent.name, "build");
  assert.strictEqual(b.via, "reviewer");
  assert.ok(/Task tool with agent "reviewer"/.test(b.text));
  assert.strictEqual(agents.forMessage(list, "[Mode: Ask]\nwhat is this?").agent.name, "ask");
  assert.strictEqual(agents.forMessage(list, "fix it", "plan").agent.name, "plan");
  assert.strictEqual(agents.forMessage(list, "@nobody fix it").agent.name, "build");
});

// ---- slash commands -------------------------------------------------------------------------

test("commands: files load as /name (nested dir/name), project replaces global, reserved names skipped", () => {
  const home = path.join(tmp, "chome");
  const root = path.join(tmp, "cproj");
  put("chome/.cortexide/commands/review.md", "Global review $ARGUMENTS");
  put("cproj/.cortexide/commands/review.md", "---\ndescription: Review a file\nargument-hint: <file>\nagent: plan\n---\nReview $1 carefully.");
  put("cproj/.claude/commands/git/sum.md", "Summarise !`git log -1`");
  put("cproj/.opencode/commands/compress.md", "not allowed");
  put("cproj/.opencode/commands/empty.md", "---\ndescription: x\n---\n");
  const list = commands.loadCommands([root], { home });
  assert.deepStrictEqual(list.map((c) => c.name), ["git/sum", "review"]);
  const rev = list.find((c) => c.name === "review");
  assert.strictEqual(rev.description, "Review a file");
  assert.strictEqual(rev.hint, "<file>");
  assert.strictEqual(rev.agent, "plan");
  assert.strictEqual(commands.match("/git:sum", list).command.name, "git/sum");
  assert.strictEqual(commands.match("/review a.js b", list).args, "a.js b");
  assert.strictEqual(commands.match("/unknown x", list), null);
  assert.ok(commands.listing(list).includes("/review <file> — Review a file (agent: plan)"));
  assert.ok(/No custom commands/.test(commands.listing([])));
});

test("commands: $ARGUMENTS, $1..$n (last takes the rest, quotes group), appended args, !`cmd` output", async () => {
  assert.strictEqual(commands.fill("Fix $ARGUMENTS now", "the bug"), "Fix the bug now");
  assert.strictEqual(commands.fill("Move $1 to $2", 'a.js "new dir/b.js" extra'), "Move a.js to new dir/b.js extra");
  assert.strictEqual(commands.fill("Use $1 and $3", "x"), "Use x and ");
  assert.strictEqual(commands.fill("Review the code.", "focus on lib"), "Review the code.\n\nfocus on lib");
  assert.strictEqual(commands.fill("Review the code.", ""), "Review the code.");
  const cmd = { template: "Diff:\n!`git diff`\nLog: !`git log -1`\nFor $ARGUMENTS", agent: "plan" };
  const seen = [];
  const r = await commands.expand(cmd, "lib", async (c) => {
    seen.push(c);
    if (c === "git log -1") throw new Error("not a repo");
    return "+added\n";
  });
  assert.deepStrictEqual(seen, ["git diff", "git log -1"]);
  assert.strictEqual(r.prompt, "Diff:\n+added\nLog: (failed: not a repo)\nFor lib");
  assert.strictEqual(r.agent, "plan");
  assert.ok((await commands.expand(cmd, "", null)).prompt.includes("!`git diff`"), "without a runner the blocks stay");
});

// ---- instructions ---------------------------------------------------------------------------

test("instructions: global, repo chain (nearest first), .cursor/rules alwaysApply, configured globs, cap", () => {
  const home = path.join(tmp, "ihome");
  put("ihome/.cortexide/AGENTS.md", "GLOBAL RULES");
  put("irepo/.git/HEAD", "ref: x");
  put("irepo/AGENTS.md", "REPO RULES");
  put("irepo/pkg/AGENTS.md", "PKG RULES");
  put("irepo/pkg/CLAUDE.md", "PKG CLAUDE");
  put("irepo/pkg/.cursor/rules/a.mdc", "---\nalwaysApply: true\n---\nALWAYS RULE");
  put("irepo/pkg/.cursor/rules/b.mdc", "---\nalwaysApply: false\n---\nOPTIONAL RULE");
  put("irepo/pkg/docs/agent/style.md", "STYLE GUIDE");
  put("irepo/pkg/docs/agent/notes.txt", "NOT MATCHED");
  const root = path.join(tmp, "irepo", "pkg");
  const r = instructions.collect({ roots: [root], home, extra: ["docs/agent/*.md", "https://example.com/x.md"] });
  const order = ["GLOBAL RULES", "PKG RULES", "PKG CLAUDE", "REPO RULES", "ALWAYS RULE", "STYLE GUIDE"].map((s) => r.text.indexOf(s));
  assert.ok(order.every((i) => i >= 0), r.text);
  assert.deepStrictEqual([...order].sort((a, b) => a - b), order, "order: " + order);
  assert.ok(!r.text.includes("OPTIONAL RULE") && !r.text.includes("NOT MATCHED"));
  assert.ok(r.files.includes(path.join(root, "AGENTS.md").toLowerCase()));
  const cut = instructions.collect({ roots: [root], home, maxTotal: 20 });
  assert.ok(/instructions cut at 20 chars/.test(cut.text));
  assert.strictEqual(instructions.repoRoot(root), path.join(tmp, "irepo"));
});

test("instructions: nested AGENTS.md between a read file and its folder are added once, nearest first", () => {
  put("nws/AGENTS.md", "TOP");
  put("nws/a/AGENTS.md", "A RULES");
  put("nws/a/b/AGENTS.md", "B RULES");
  put("nws/a/b/file.js", "x");
  const root = path.join(tmp, "nws");
  const loaded = new Set([path.join(root, "AGENTS.md").toLowerCase()]);
  const first = instructions.nested(path.join(root, "a", "b", "file.js"), [root], loaded);
  assert.deepStrictEqual(first.map((n) => n.text), ["B RULES", "A RULES"]);
  assert.deepStrictEqual(instructions.nested(path.join(root, "a", "b", "file.js"), [root], loaded), []);
  assert.deepStrictEqual(instructions.nested(path.join(tmp, "elsewhere.js"), [root], loaded), []);
});

test("Read adds a sub-folder's AGENTS.md to its result once", async () => {
  put("rws/sub/AGENTS.md", "SUB RULES");
  put("rws/sub/x.js", "const x = 1;\n");
  const root = path.join(tmp, "rws");
  const ctx = new ToolContext({ roots: [root], rgPath: "missing-rg" });
  const first = await execTool(ctx, "Read", { path: "sub/x.js" });
  assert.ok(/\[Instructions from .*AGENTS\.md[^\]]*\]\nSUB RULES/.test(first), first);
  const again = await execTool(ctx, "Read", { path: "sub/x.js" });
  assert.ok(!again.includes("SUB RULES"));
});

// ---- saved tool output ----------------------------------------------------------------------

test("tool-output: short output is unchanged; cut output is saved whole and the note says where", () => {
  const clip = (t, max) => t.slice(0, max) + "…[cut]";
  assert.strictEqual(toolOutput.clipSaved("short", 100, clip, "x"), "short");
  const long = Array.from({ length: 500 }, (_, i) => "line " + i).join("\n");
  const out = toolOutput.clipSaved(long, 50, clip, "shell run");
  const m = /saved to (.+?\.txt)\./.exec(out);
  assert.ok(m, out);
  assert.ok(out.startsWith(long.slice(0, 50) + "…[cut]"));
  assert.ok(out.includes("(" + long.length + " chars, 500 lines)"));
  assert.strictEqual(fs.readFileSync(m[1], "utf8"), long);
  assert.ok(toolOutput.isOutputFile(m[1]));
  assert.ok(/shell_run/.test(path.basename(m[1])));
  assert.ok(!toolOutput.isOutputFile(path.join(tmp, "x.txt")));
  fs.rmSync(m[1], { force: true });
});
