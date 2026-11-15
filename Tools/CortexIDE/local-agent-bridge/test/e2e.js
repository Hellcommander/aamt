"use strict";

// Live end-to-end run (not part of `node test/run.js`; needs a running local model):
//   node test/run.js --e2e [model]          default model qwen2.5-coder:7b
//   AGENT_PROVIDER=vllm node test/e2e.js Qwen/Qwen2.5-Coder-32B-Instruct
//   IMPORT_FILE=C:\path\chat.md node test/e2e.js   also exercises chat import
// Activates the extension under the vscode stub, asks the Agent panel to fix a bug,
// and checks that the fix landed and `node test.js` passes.

const fs = require("fs");
const os = require("os");
const path = require("path");
const { execSync } = require("child_process");
const { install } = require("./vscode-stub");

const EXT = path.resolve(__dirname, "..");
const MODEL = process.argv[2] || "qwen2.5-coder:7b";
const home = fs.mkdtempSync(path.join(os.tmpdir(), "agent-home-"));
const ws = fs.mkdtempSync(path.join(os.tmpdir(), "agent-e2e-"));
process.env.USERPROFILE = home;

fs.writeFileSync(path.join(ws, "math.js"), "// Basic math helpers\nfunction add(a, b) {\n  return a - b;\n}\n\nfunction mul(a, b) {\n  return a * b;\n}\n\nmodule.exports = { add, mul };\n");
fs.writeFileSync(path.join(ws, "test.js"), "const assert = require('assert');\nconst { add, mul } = require('./math');\nassert.strictEqual(add(2, 3), 5, 'add(2,3) should be 5');\nassert.strictEqual(mul(2, 3), 6);\nconsole.log('all tests passed');\n");

const settings = { "localAgentBridge.agent.model": MODEL, "localAgentBridge.agent.maxRounds": 12 };
if (process.env.AGENT_PROVIDER) settings["localAgentBridge.agent.provider"] = process.env.AGENT_PROVIDER;
if (process.env.AGENT_BASEURL) settings["localAgentBridge.agent.baseUrl"] = process.env.AGENT_BASEURL;
const stub = install({ workspace: ws, settings });

(async () => {
  const ext = require(path.join(EXT, "extension.js"));
  ext.activate(stub.makeContext(EXT));
  const provider = stub.webviewProviders.get("localAgentBridge.agent");
  console.log("activated: " + stub.commands.size + " commands; agent view registered: " + !!provider);

  let onMsg;
  const view = {
    webview: {
      options: {},
      html: "",
      onDidReceiveMessage: (f) => {
        onMsg = f;
        return stub.disposable;
      },
      postMessage: (m) => {
        if (m.type === "header") console.log("[header] " + m.text);
        else if (m.type === "thought") console.log("[thought] " + m.text.replace(/\s+/g, " ").slice(0, 200));
        else if (m.type === "tool" && m.status === "done") console.log("[tool " + (m.ok ? "ok" : "ERR") + "] " + m.name + " " + m.label + " → " + String(m.result).split("\n")[0].slice(0, 120));
        else if (m.type === "status" && !m.transient) console.log("[status] " + m.text);
        else if (m.type === "assistant") console.log("[assistant] " + m.text);
        else if (m.type === "error") console.log("[ERROR] " + m.text);
        else if (m.type === "idle") view.idle();
        return Promise.resolve(true);
      },
    },
    onDidDispose: stub.noop,
    onDidChangeVisibility: stub.noop,
  };
  const done = new Promise((resolve) => (view.idle = resolve));
  provider.resolveWebviewView(view);
  await onMsg({ type: "ready" });
  const t0 = Date.now();
  await onMsg({ type: "send", text: "test.js fails. Fix the bug in math.js, then run `node test.js` to verify it passes." });
  await done;
  console.log("--- took " + ((Date.now() - t0) / 1000).toFixed(1) + "s");

  const fixed = /return a \+ b/.test(fs.readFileSync(path.join(ws, "math.js"), "utf8"));
  let testOut;
  try {
    testOut = execSync("node test.js", { cwd: ws }).toString().trim();
  } catch (e) {
    testOut = "FAILED: " + e.message.split("\n")[0];
  }
  // Since 2.7 each chat is its own folder in the history cache (USERPROFILE\.cortexide\agent\projects\…),
  // and since 2.7.1 its progress.md lives there too.
  const st = provider.store();
  const conv = st.get(provider.activeId);
  const progress = st.progressFile(conv.id);
  console.log("math.js fixed: " + fixed + " | node test.js: " + testOut + " | progress.md: " + fs.existsSync(progress));
  if (fs.existsSync(progress)) console.log(fs.readFileSync(progress, "utf8"));
  console.log("sub-index files: " + Object.values(st.subIndex(conv.id).files).map((f) => path.basename(f.path)).join(", ") + " | claims left: " + Object.keys(st.claims || {}).length);
  console.log("history cache: " + st.dir + " | chats: " + st.list().length);
  console.log("chat '" + conv.title + "' model=" + (conv.model || "(default)") + " status=" + conv.status + " | log rows: " + conv.log.length + ", history turns: " + conv.history.length);

  if (process.env.IMPORT_FILE) {
    await stub.commands.get("localAgentBridge.continueImportedChat")(process.env.IMPORT_FILE);
    const c2 = st.get(provider.activeId);
    console.log("import (chat " + (c2.id === conv.id ? "REUSED" : "new") + ", " + st.list().length + " chats): history=" + c2.history.length + " log=" + c2.log.length + " notes=" + c2.progress.notes.length);
  }
  fs.rmSync(ws, { recursive: true, force: true });
  fs.rmSync(home, { recursive: true, force: true });
  process.exit(fixed && /passed/.test(testOut) ? 0 : 1);
})().catch((e) => {
  console.error("HARNESS ERROR", e);
  process.exit(2);
});
