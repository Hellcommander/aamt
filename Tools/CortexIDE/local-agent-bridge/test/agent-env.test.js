"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const assert = require("assert");
const { test, after, EXT } = require("./harness");
const { projectChecks, repoMap } = require(path.join(EXT, "lib", "agent-env"));
const { systemPrompt } = require(path.join(EXT, "lib", "agent"));

function project(files) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "agent-env-"));
  after(() => fs.rmSync(dir, { recursive: true, force: true }));
  for (const [rel, text] of Object.entries(files)) {
    fs.mkdirSync(path.dirname(path.join(dir, rel)), { recursive: true });
    if (rel.endsWith("/")) fs.mkdirSync(path.join(dir, rel), { recursive: true });
    else fs.writeFileSync(path.join(dir, rel), text);
  }
  return dir;
}

test("npm scripts become checks; the placeholder test script is ignored", () => {
  const a = project({ "package.json": JSON.stringify({ scripts: { test: "node test.js", lint: "eslint .", build: "tsc" } }) });
  assert.deepStrictEqual(projectChecks(a), ["npm test", "npm run lint", "npm run build"]);
  const b = project({ "package.json": JSON.stringify({ scripts: { test: 'echo "Error: no test specified" && exit 1' } }), "yarn.lock": "" });
  assert.deepStrictEqual(projectChecks(b), []);
  const c = project({ "package.json": JSON.stringify({ scripts: { test: "vitest" } }), "pnpm-lock.yaml": "" });
  assert.deepStrictEqual(projectChecks(c), ["pnpm run test"]);
});

test("dotnet, python, cargo, go and test runner scripts", () => {
  assert.deepStrictEqual(projectChecks(project({ "Mod.csproj": "<Project/>" })), ["dotnet build Mod.csproj"]);
  assert.deepStrictEqual(projectChecks(project({ "App.sln": "", "App.Tests/": "" })), ["dotnet build App.sln", "dotnet test App.sln"]);
  assert.deepStrictEqual(projectChecks(project({ "src/Mod/Mod.csproj": "" })), []); // two levels down: not guessed
  assert.deepStrictEqual(projectChecks(project({ "Mod/Mod.csproj": "" })), ["dotnet build (in the project folder)"]);
  assert.deepStrictEqual(projectChecks(project({ "pyproject.toml": "" })), ["python -m pytest -q"]);
  assert.deepStrictEqual(projectChecks(project({ "Cargo.toml": "" })), ["cargo build", "cargo test"]);
  assert.deepStrictEqual(projectChecks(project({ "go.mod": "" })), ["go build ./...", "go test ./..."]);
  assert.deepStrictEqual(projectChecks(project({ "run-tests.ps1": "" })), ["& .\\run-tests.ps1"]);
  assert.deepStrictEqual(projectChecks(""), []);
});

test("repoMap lists folders first with their children and skips noise", () => {
  const dir = project({ "README.md": "", "src/a.js": "", "src/lib/b.js": "", "node_modules/x/i.js": "", ".git/HEAD": "", "test/t.js": "" });
  const map = repoMap(dir);
  assert.strictEqual(map, "src/  lib/, a.js\ntest/  t.js\nREADME.md");
  const many = project(Object.fromEntries(Array.from({ length: 50 }, (_, i) => ["f" + String(i).padStart(2, "0") + ".txt", ""])));
  const capped = repoMap(many, 10).split("\n");
  assert.strictEqual(capped.length, 11);
  assert.ok(/40 more entries/.test(capped[10]), capped[10]);
});

test("system prompt carries checks and layout", () => {
  const s = systemPrompt({ env: { roots: ["D:/p"], checks: ["npm test", "npm run lint"], tree: "src/  a.js" }, skills: [], task: "x", prior: "", textMode: false });
  assert.ok(s.includes("Check a change with: npm test | npm run lint"), s);
  assert.ok(s.includes("Workspace layout (top two levels):\nsrc/  a.js"), s);
});
