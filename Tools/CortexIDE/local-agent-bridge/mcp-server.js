"use strict";

const { scanSkills, scanCanvases, matchSkills } = require("./lib/scan");
const { importChatFile, listImported } = require("./lib/import-chat");

// MCP stdio is newline-delimited JSON. Older builds of this server used LSP-style
// Content-Length framing, which MCP clients never parse (-32001 request timed out).
// Reply in whichever framing the client used so both keep working.
let framing = "ndjson";

function writeMessage(obj) {
  const json = JSON.stringify(obj);
  if (framing === "lsp") {
    const payload = Buffer.from(json, "utf8");
    process.stdout.write(`Content-Length: ${payload.length}\r\n\r\n`);
    process.stdout.write(payload);
  } else {
    process.stdout.write(json + "\n");
  }
}

function sendResult(id, result) {
  writeMessage({ jsonrpc: "2.0", id, result });
}

function sendError(id, code, message) {
  writeMessage({ jsonrpc: "2.0", id, error: { code, message } });
}

function workspaceFolders() {
  const w = process.env.AGENT_BRIDGE_WORKSPACE || process.env.CORTEXIDE_WORKSPACE || "";
  return w ? w.split(";").map((s) => s.trim()).filter(Boolean) : [];
}

function load() {
  const folders = workspaceFolders();
  return {
    skills: scanSkills({
      workspaceFolders: folders,
      includeBuiltIn: true,
      includePlugin: process.env.AGENT_BRIDGE_PLUGINS === "1",
    }),
    canvases: scanCanvases(folders),
  };
}

const TOOLS = [
  {
    name: "list_skills",
    description: "List SKILL.md skills (Cursor / Claude / Agents folders) with name, description, source, and path.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "read_skill",
    description: "Read the full SKILL.md body for a skill by name. Call this before following a skill workflow.",
    inputSchema: {
      type: "object",
      properties: { name: { type: "string", description: "Skill name, e.g. canvas" } },
      required: ["name"],
    },
  },
  {
    name: "match_skills",
    description: "Find skills whose name or description match a task query.",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string" },
        limit: { type: "number" },
      },
      required: ["query"],
    },
  },
  {
    name: "list_canvases",
    description: "List .canvas.tsx canvases under ~/.cursor/projects/*/canvases and workspace canvases/.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "read_canvas",
    description: "Read a .canvas.tsx canvas by kebab-case name or absolute path.",
    inputSchema: {
      type: "object",
      properties: { name: { type: "string" } },
      required: ["name"],
    },
  },
  {
    name: "import_cursor_chat",
    description: "Import a Cursor chat export (.md) or agent transcript (.jsonl). Writes .cortexide/imported-chats and returns an Agent-mode continuation prompt.",
    inputSchema: {
      type: "object",
      properties: { path: { type: "string", description: "Absolute path to the Cursor export" } },
      required: ["path"],
    },
  },
  {
    name: "list_imported_chats",
    description: "List chats imported into .cortexide/imported-chats.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
];

function handleTool(name, args) {
  const { skills, canvases } = load();
  if (name === "list_skills") {
    return {
      content: [{
        type: "text",
        text: JSON.stringify(skills.map((s) => ({
          name: s.name, description: s.description, source: s.source, file: s.file,
        })), null, 2),
      }],
    };
  }
  if (name === "read_skill") {
    const skill = skills.find((s) => s.name.toLowerCase() === String(args.name || "").toLowerCase());
    if (!skill) return { content: [{ type: "text", text: `No skill named ${args.name}` }], isError: true };
    return {
      content: [{
        type: "text",
        text: `# ${skill.name}\n\n${skill.description}\n\nSource: ${skill.file}\nDir: ${skill.dir}\n\n${skill.instructions}`,
      }],
    };
  }
  if (name === "match_skills") {
    const hits = matchSkills(skills, args.query, args.limit || 8);
    return {
      content: [{
        type: "text",
        text: JSON.stringify(hits.map((s) => ({ name: s.name, description: s.description, file: s.file })), null, 2),
      }],
    };
  }
  if (name === "list_canvases") {
    return { content: [{ type: "text", text: JSON.stringify(canvases, null, 2) }] };
  }
  if (name === "read_canvas") {
    const q = String(args.name || "").replace(/\\/g, "/");
    const canvas = canvases.find((c) =>
      c.name === args.name || c.file.replace(/\\/g, "/") === q || c.file === args.name);
    if (!canvas) return { content: [{ type: "text", text: `No canvas named ${args.name}` }], isError: true };
    return { content: [{ type: "text", text: require("fs").readFileSync(canvas.file, "utf8") }] };
  }
  if (name === "import_cursor_chat") {
    const folders = workspaceFolders();
    const result = importChatFile(String(args.path || ""), folders[0]);
    return {
      content: [{
        type: "text",
        text: JSON.stringify({ dest: result.dest, turns: result.turns, lastUser: result.lastUser, prompt: result.prompt }, null, 2),
      }],
    };
  }
  if (name === "list_imported_chats") {
    return { content: [{ type: "text", text: JSON.stringify(listImported(workspaceFolders()[0]), null, 2) }] };
  }
  return { content: [{ type: "text", text: `Unknown tool ${name}` }], isError: true };
}

function handleMessage(msg) {
  if (!msg || typeof msg !== "object") return;
  if (msg.method === "initialize") {
    const asked = msg.params && msg.params.protocolVersion;
    sendResult(msg.id, {
      protocolVersion: asked || "2024-11-05",
      capabilities: { tools: {} },
      serverInfo: { name: "local-agent-bridge", version: "2.1.0" },
    });
  } else if (msg.method === "tools/list") {
    sendResult(msg.id, { tools: TOOLS });
  } else if (msg.method === "tools/call") {
    try {
      sendResult(msg.id, handleTool(msg.params.name, msg.params.arguments || {}));
    } catch (e) {
      sendError(msg.id, -32000, String(e && e.message ? e.message : e));
    }
  } else if (msg.method === "ping") {
    sendResult(msg.id, {});
  } else if (msg.id != null && msg.method) {
    sendError(msg.id, -32601, `Unknown method ${msg.method}`);
  }
}

function parseAndHandle(text) {
  let msg;
  try {
    msg = JSON.parse(text);
  } catch {
    return;
  }
  for (const m of Array.isArray(msg) ? msg : [msg]) handleMessage(m);
}

let buffer = Buffer.alloc(0);
process.stdin.on("data", (chunk) => {
  buffer = Buffer.concat([buffer, chunk]);
  while (buffer.length) {
    const head = buffer.slice(0, 32).toString("utf8").trimStart();
    if (/^Content-Length:/i.test(head)) {
      framing = "lsp";
      const headerEnd = buffer.indexOf("\r\n\r\n");
      if (headerEnd < 0) return;
      const match = /Content-Length:\s*(\d+)/i.exec(buffer.slice(0, headerEnd).toString("utf8"));
      const start = headerEnd + 4;
      const len = match ? Number(match[1]) : 0;
      if (buffer.length < start + len) return;
      const json = buffer.slice(start, start + len).toString("utf8");
      buffer = buffer.slice(start + len);
      parseAndHandle(json);
      continue;
    }
    const nl = buffer.indexOf("\n");
    if (nl < 0) return;
    const line = buffer.slice(0, nl).toString("utf8").trim();
    buffer = buffer.slice(nl + 1);
    if (line) {
      framing = "ndjson";
      parseAndHandle(line);
    }
  }
});
