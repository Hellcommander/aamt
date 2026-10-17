"use strict";

// node test/run.js            run every test/*.test.js
// node test/run.js mcp        only files whose name contains "mcp"
// node test/run.js --e2e [model]  drive the Agent panel against a live local model (see e2e.js)

const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const args = process.argv.slice(2);
if (args[0] === "--e2e") {
  const r = spawnSync(process.execPath, [path.join(__dirname, "e2e.js"), ...args.slice(1)], { stdio: "inherit" });
  process.exit(r.status == null ? 1 : r.status);
}

const filter = args[0] || "";
const files = fs
  .readdirSync(__dirname)
  .filter((f) => f.endsWith(".test.js") && f.includes(filter))
  .sort();
if (!files.length) {
  console.error("no test files match " + JSON.stringify(filter));
  process.exit(1);
}

const failed = [];
for (const f of files) {
  console.log("\n== " + f);
  const r = spawnSync(process.execPath, [path.join(__dirname, f)], { stdio: "inherit", timeout: 120000 });
  if (r.status !== 0) failed.push(f + (r.error ? " (" + r.error.message + ")" : ""));
}
console.log("\n" + (files.length - failed.length) + "/" + files.length + " test files passed" + (failed.length ? "; failed: " + failed.join(", ") : ""));
process.exit(failed.length ? 1 : 0);
