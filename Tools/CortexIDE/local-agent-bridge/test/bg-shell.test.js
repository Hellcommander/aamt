"use strict";

// Background shells: Shell { run_in_background } returns at once, ShellOutput reads new output
// (wait / until / filter), ShellKill stops the process tree, shells are listed per chat.

const fs = require("fs");
const os = require("os");
const path = require("path");
const assert = require("assert");
const { test, after, EXT } = require("./harness");
const { ToolContext, execTool, canonName, normArgs, TOOL_DEFS } = require(path.join(EXT, "lib", "agent-tools"));
const bg = require(path.join(EXT, "lib", "bg-shell"));
const agentsLib = require(path.join(EXT, "lib", "agents"));

const WIN = process.platform === "win32";
const SKIP = WIN ? undefined : "Shell tool runs PowerShell on Windows";
const ws = fs.mkdtempSync(path.join(os.tmpdir(), "agent-bg-"));
after(() => {
  bg.killAll();
  fs.rmSync(ws, { recursive: true, force: true });
});
const ctxA = new ToolContext({ roots: [ws], owner: "chatA" });
const ctxB = new ToolContext({ roots: [ws], owner: "chatB" });

test("aliases and argument spellings", () => {
  assert.strictEqual(canonName("BashOutput"), "ShellOutput");
  assert.strictEqual(canonName("kill_shell"), "ShellKill");
  assert.strictEqual(normArgs("Shell", { command: "x", background: "true" }).run_in_background, true);
  assert.strictEqual(normArgs("ShellOutput", { bash_id: "bg3" }).id, "bg3");
  assert.ok(TOOL_DEFS.some((t) => t.function.name === "ShellOutput"));
});

test("an agent without Shell loses ShellOutput and ShellKill too", () => {
  const names = agentsLib.toolNames(agentsLib.BUILTIN.ask, ["Read", "Shell", "ShellOutput", "ShellKill"]);
  assert.deepStrictEqual(names, ["Read"]);
});

test("background shell: starts at once, reads new output, waits for a line, lists per chat, kills", async () => {
  const t0 = Date.now();
  const r = await execTool(ctxA, "Shell", {
    command: "Write-Output 'booting'; Start-Sleep -Milliseconds 1500; Write-Output 'listening on 5000'; while ($true) { Write-Output tick; Start-Sleep -Milliseconds 300 }",
    run_in_background: true,
  });
  assert.ok(Date.now() - t0 < 8000, "returned without waiting for the command");
  const id = /background shell (bg\d+)/.exec(r)[1];
  assert.match(r, /booting/);
  assert.match(r, /running/);

  const ready = await execTool(ctxA, "ShellOutput", { id, until: "listening", wait: 20 });
  assert.match(ready, /listening on 5000/);
  assert.doesNotMatch(ready, /booting/, "already-read output is not repeated");

  const ticks = await execTool(ctxA, "ShellOutput", { id, wait: 3, filter: "^tick$" });
  assert.match(ticks, /tick/);
  assert.doesNotMatch(ticks, /listening/);

  assert.match(await execTool(ctxA, "ShellOutput", {}), new RegExp(id + " +running"));
  assert.strictEqual(await execTool(ctxB, "ShellOutput", {}), "(no background shells in this chat)");

  assert.match(await execTool(ctxA, "ShellKill", { id }), new RegExp("stopped " + id));
  const s = bg.get(id);
  for (let i = 0; i < 200 && s.exitCode == null; i++) await new Promise((res) => setTimeout(res, 100));
  assert.notStrictEqual(s.exitCode, null, "process tree was killed");
  assert.match(await execTool(ctxA, "ShellOutput", { id, wait: 0 }), /exited with code/);
}, { skip: SKIP });

test("background shell that fails at once shows its exit; bad regex is an error", async () => {
  const r = await execTool(ctxA, "Shell", { command: "Write-Output 'nope'; exit 7", run_in_background: true });
  const id = /background shell (bg\d+)/.exec(r)[1];
  // Usually it has exited within the first 3 s; on a loaded machine PowerShell can take longer to start.
  const done = /exited with code/.test(r) ? r : await execTool(ctxA, "ShellOutput", { id, wait: 30, until: "\\bnope\\b" }).then(() => execTool(ctxA, "ShellOutput", { id, wait: 5 }));
  assert.match(done, /exited with code 7/);
  assert.match(await execTool(ctxA, "ShellOutput", { id, until: "(" }), /^error: bad until regex/);
  assert.match(await execTool(ctxA, "ShellOutput", { id: "bg999" }), /^error: no background shell/);
}, { skip: SKIP });

test("foreground timeout suggests run_in_background", async () => {
  const r = await execTool(ctxA, "Shell", { command: "Start-Sleep -Seconds 5", timeout: 1 });
  assert.match(r, /run_in_background: true/);
}, { skip: SKIP });
