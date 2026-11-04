"use strict";

// Activates extension.js under the vscode stub: every contributed command/view is
// registered, and the startup sync writes workspace files and mcp.json (replacing
// the pre-rename "cursor-bridge" entry).

const fs = require("fs");
const os = require("os");
const path = require("path");
const assert = require("assert");
const { test, after, EXT } = require("./harness");
const { install } = require("./vscode-stub");

const home = fs.mkdtempSync(path.join(os.tmpdir(), "ext-home-"));
const ws = fs.mkdtempSync(path.join(os.tmpdir(), "ext-ws-"));
process.env.USERPROFILE = home;
after(() => {
  fs.rmSync(home, { recursive: true, force: true });
  fs.rmSync(ws, { recursive: true, force: true });
});

// State a 2.0.0 (pre-rename) install leaves behind.
const mcpPath = path.join(home, ".cortexide", "mcp.json");
fs.mkdirSync(path.dirname(mcpPath), { recursive: true });
fs.writeFileSync(mcpPath, JSON.stringify({
  mcpServers: {
    "cursor-bridge": { command: "node", args: ["C:\\x\\.cortexide\\extensions\\arend.cursor-agent-bridge-1.0.0\\mcp-server.js"] },
    other: { command: "other-server" },
  },
}, null, 2));
fs.writeFileSync(path.join(ws, ".voidrules"), "my own rule\n\n# BEGIN CURSOR-AGENT-BRIDGE\nold section\n# END CURSOR-AGENT-BRIDGE\n");
fs.mkdirSync(path.join(ws, ".cortexide", "agents"), { recursive: true });
fs.writeFileSync(path.join(ws, ".cortexide", "agents", "cursor-agent.md"), "old");
fs.mkdirSync(path.join(ws, ".cortexide", "skills", "old-skill"), { recursive: true });
fs.writeFileSync(path.join(ws, ".cortexide", "skills", "old-skill", ".cursor-bridge-generated"), "x");

const stub = install({ workspace: ws });
const pkg = JSON.parse(fs.readFileSync(path.join(EXT, "package.json"), "utf8"));
const ext = require(path.join(EXT, "extension.js"));
ext.activate(stub.makeContext(EXT));

function waitFor(cond, ms = 5000) {
  const t0 = Date.now();
  return new Promise((resolve, reject) => {
    const tick = () => {
      if (cond()) resolve();
      else if (Date.now() - t0 > ms) reject(new Error("timed out"));
      else setTimeout(tick, 25);
    };
    tick();
  });
}

test("package.json identity", () => {
  assert.strictEqual(pkg.name, "local-agent-bridge");
  assert.strictEqual(pkg.displayName, "Local Agent Bridge");
  assert.strictEqual(pkg.publisher, "arend");
});

test("every contributed command is registered", () => {
  const missing = pkg.contributes.commands.map((c) => c.command).filter((id) => !stub.commands.has(id));
  assert.deepStrictEqual(missing, []);
});

test("every registered command is contributed", () => {
  const contributed = new Set(pkg.contributes.commands.map((c) => c.command));
  assert.deepStrictEqual([...stub.commands.keys()].filter((id) => !contributed.has(id)), []);
});

test("menus only reference contributed commands", () => {
  const contributed = new Set(pkg.contributes.commands.map((c) => c.command));
  for (const [menu, items] of Object.entries(pkg.contributes.menus)) {
    for (const it of items) assert.ok(contributed.has(it.command), menu + " → " + it.command);
  }
});

test("views and custom editor are registered under the contributed ids", () => {
  const views = pkg.contributes.views["local-agent-bridge"].map((v) => v.id);
  for (const id of views) assert.ok(stub.webviewProviders.has(id) || stub.treeProviders.has(id), id);
  assert.ok(stub.customEditors.has(pkg.contributes.customEditors[0].viewType));
  assert.ok(pkg.contributes.viewsContainers.activitybar.some((c) => c.id === "local-agent-bridge"));
});

test("settings read by the code are all contributed", () => {
  const props = Object.keys(pkg.contributes.configuration.properties);
  assert.ok(props.every((p) => p.startsWith("localAgentBridge.")), props.join(", "));
  const src = ["extension.js", "lib/agent-view.js"].map((f) => fs.readFileSync(path.join(EXT, f), "utf8")).join("\n");
  const agentKeys = [...src.matchAll(/(?:c|cfg\(\))\.get\("([\w.]+)"/g)].map((m) => m[1]);
  assert.ok(agentKeys.length > 5, "found keys " + agentKeys);
  for (const k of agentKeys) {
    assert.ok(props.includes("localAgentBridge." + k) || props.includes("localAgentBridge.agent." + k), k);
  }
});

test("no Cursor branding left in names, titles or ids", () => {
  const walk = (v, at) => {
    if (typeof v === "string") {
      // Allowed: factual references to Cursor's file formats and chat exports.
      if (/cursor/i.test(v) && !/import_cursor_chat|Cursor export|from Cursor|Cursor exports|\.cursor[\\/]|Cursor built-in|a Cursor chat/i.test(v)) {
        throw new Error(at + ": " + v);
      }
    } else if (v && typeof v === "object") for (const [k, x] of Object.entries(v)) walk(x, at + "." + k);
  };
  walk(pkg, "package");
});

test("startup sync writes mcp.json and drops the pre-rename entry", async () => {
  await waitFor(() => JSON.parse(fs.readFileSync(mcpPath, "utf8")).mcpServers["local-agent-bridge"]);
  const servers = JSON.parse(fs.readFileSync(mcpPath, "utf8")).mcpServers;
  assert.deepStrictEqual(Object.keys(servers).sort(), ["local-agent-bridge", "other"]);
  assert.deepStrictEqual(servers["local-agent-bridge"].args, [path.join(EXT, "mcp-server.js")]);
  assert.strictEqual(servers["local-agent-bridge"].env.AGENT_BRIDGE_WORKSPACE, ws);
});

test("startup sync replaces pre-rename workspace files", () => {
  const rules = fs.readFileSync(path.join(ws, ".voidrules"), "utf8");
  assert.ok(rules.startsWith("my own rule"), rules);
  assert.ok(!rules.includes("CURSOR-AGENT-BRIDGE") && rules.includes("# BEGIN LOCAL-AGENT-BRIDGE"), rules);
  assert.ok(!fs.existsSync(path.join(ws, ".cortexide", "agents", "cursor-agent.md")));
  assert.ok(fs.existsSync(path.join(ws, ".cortexide", "agents", "local-agent.md")));
  assert.ok(fs.existsSync(path.join(ws, ".cortexide", "rules", "00-local-agent.md")));
  assert.ok(!fs.existsSync(path.join(ws, ".cortexide", "skills", "old-skill")), "legacy generated skill removed");
  assert.ok(fs.existsSync(path.join(ws, ".cortexide", "skills", "import-chat", ".agent-bridge-generated")), "bundled skill synced");
});

test("second sync keeps a single managed .voidrules section", async () => {
  await stub.commands.get("localAgentBridge.sync")();
  const rules = fs.readFileSync(path.join(ws, ".voidrules"), "utf8");
  assert.strictEqual(rules.split("# BEGIN LOCAL-AGENT-BRIDGE").length, 2, rules);
});

test("Agent webview renders", () => {
  const provider = stub.webviewProviders.get("localAgentBridge.agent");
  const view = {
    webview: { options: {}, html: "", onDidReceiveMessage: stub.noop, postMessage: async () => true, asWebviewUri: (u) => u, cspSource: "self" },
    onDidDispose: stub.noop,
    onDidChangeVisibility: stub.noop,
  };
  provider.resolveWebviewView(view);
  assert.ok(/acquireVsCodeApi/.test(view.webview.html));
});
