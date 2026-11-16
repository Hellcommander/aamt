"use strict";

// Cheap facts about the workspace for the system prompt: how to check a change (build / test /
// lint commands detected from project files) and a compact top-level map, so a small model can
// orient itself and verify without spending rounds on LS.

const fs = require("fs");
const path = require("path");

const SKIP = new Set(["node_modules", ".git", "bin", "obj", ".venv", "venv", "__pycache__", "dist", "out", "build", "target", "Library", "Temp", ".cortexide", ".vs", ".idea", ".vscode"]);

function exists(p) {
  try {
    fs.accessSync(p);
    return true;
  } catch {
    return false;
  }
}

function list(dir) {
  try {
    return fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return [];
  }
}

/** Shell commands that check a change in this project, most useful first. */
function projectChecks(root) {
  if (!root) return [];
  const out = [];
  const pkgFile = path.join(root, "package.json");
  if (exists(pkgFile)) {
    try {
      const scripts = JSON.parse(fs.readFileSync(pkgFile, "utf8")).scripts || {};
      const runner = exists(path.join(root, "pnpm-lock.yaml")) ? "pnpm" : exists(path.join(root, "yarn.lock")) ? "yarn" : "npm";
      for (const s of ["test", "typecheck", "lint", "build"]) {
        if (scripts[s] && !/no test specified/.test(scripts[s])) out.push(s === "test" && runner === "npm" ? "npm test" : runner + " run " + s);
      }
    } catch {
      /* unreadable package.json */
    }
  }
  const top = list(root);
  const names = top.map((e) => e.name);
  const sln = names.find((n) => /\.sln$/i.test(n));
  const csproj = names.find((n) => /\.csproj$/i.test(n));
  if (sln || csproj) {
    out.push("dotnet build " + (sln || csproj));
    if (names.some((n) => /test/i.test(n)) || /Tests?\.csproj$/i.test(csproj || "")) out.push("dotnet test " + (sln || csproj));
  } else if (top.some((e) => e.isDirectory() && list(path.join(root, e.name)).some((f) => /\.csproj$/i.test(f.name)))) {
    out.push("dotnet build (in the project folder)");
  }
  if (names.includes("pyproject.toml") || names.includes("setup.py") || names.includes("pytest.ini") || names.includes("tests")) {
    if (names.includes("pytest.ini") || names.includes("tests") || names.includes("pyproject.toml")) out.push("python -m pytest -q");
  }
  if (names.includes("Cargo.toml")) out.push("cargo build", "cargo test");
  if (names.includes("go.mod")) out.push("go build ./...", "go test ./...");
  if (names.includes("CMakeLists.txt")) out.push("cmake --build build");
  if (names.includes("Makefile")) out.push("make");
  const testRunner = names.find((n) => /^(run[-_]?tests?|test)\.(ps1|bat|cmd|sh|js|py)$/i.test(n));
  if (testRunner) out.push(testRunner.endsWith(".ps1") ? "& .\\" + testRunner : testRunner.endsWith(".js") ? "node " + testRunner : testRunner.endsWith(".py") ? "python " + testRunner : ".\\" + testRunner);
  return [...new Set(out)].slice(0, 6);
}

/** Two-level map of the workspace: folders with their direct children, capped. */
function repoMap(root, maxLines = 40) {
  if (!root) return "";
  const rows = [];
  const visible = (e) => !e.name.startsWith(".") && !SKIP.has(e.name);
  const sorted = (dir) =>
    list(dir)
      .filter(visible)
      .sort((a, b) => (a.isDirectory() === b.isDirectory() ? a.name.localeCompare(b.name) : a.isDirectory() ? -1 : 1));
  const top = sorted(root);
  for (const e of top) {
    if (rows.length >= maxLines) {
      rows.push("… (" + (top.length - top.indexOf(e)) + " more entries)");
      break;
    }
    if (!e.isDirectory()) {
      rows.push(e.name);
      continue;
    }
    const kids = sorted(path.join(root, e.name));
    const shown = kids.slice(0, 8).map((k) => k.name + (k.isDirectory() ? "/" : ""));
    rows.push(e.name + "/" + (kids.length ? "  " + shown.join(", ") + (kids.length > 8 ? ", … (" + kids.length + " entries)" : "") : "  (empty)"));
  }
  return rows.join("\n");
}

module.exports = { projectChecks, repoMap };
