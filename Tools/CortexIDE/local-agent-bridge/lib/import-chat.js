"use strict";

const fs = require("fs");
const path = require("path");
const os = require("os");

const MAX_PROMPT = 12000;
const MAX_TURNS_IN_PROMPT = 24;

function home() {
  return process.env.USERPROFILE || os.homedir();
}

function slugFromName(name) {
  return String(name || "imported-chat")
    .replace(/\.(md|jsonl|json)$/i, "")
    .replace(/^cursor[_-]?/i, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 72) || "imported-chat";
}

function flattenContent(content) {
  if (content == null) return "";
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((part) => {
        if (!part) return "";
        if (typeof part === "string") return part;
        if (part.type === "text" || part.type === "output_text") return part.text || "";
        if (part.text) return part.text;
        if (part.type === "tool_use" || part.type === "functionCall") {
          return `[tool ${part.name || part.toolName || "call"}]`;
        }
        return "";
      })
      .filter(Boolean)
      .join("\n");
  }
  if (typeof content === "object") {
    if (content.text) return flattenContent(content.text);
    if (content.content) return flattenContent(content.content);
  }
  return "";
}

function roleOf(raw) {
  const r = String(raw || "").toLowerCase();
  if (r === "user" || r === "human") return "user";
  if (r === "assistant" || r === "cursor" || r === "model" || r === "bot") return "assistant";
  if (r === "system") return "system";
  return "";
}

function parseCursorMarkdown(text) {
  const turns = [];
  const re = /(?:^|\n)#{0,3}\s*\*{0,2}(User|Cursor|Assistant|Human|System)\*{0,2}\s*\n([\s\S]*?)(?=(?:\n#{0,3}\s*\*{0,2}(?:User|Cursor|Assistant|Human|System)\*{0,2}\s*\n)|$)/gi;
  let m;
  while ((m = re.exec(text))) {
    const role = roleOf(m[1]);
    const body = m[2].replace(/^\s*---\s*$/gm, "").trim();
    if (role && body) turns.push({ role, text: body });
  }
  return turns;
}

function parseJsonl(text) {
  const turns = [];
  for (const line of text.split(/\r?\n/)) {
    const t = line.trim();
    if (!t.startsWith("{")) continue;
    let obj;
    try {
      obj = JSON.parse(t);
    } catch {
      continue;
    }
    const role = roleOf(obj.role || obj.type || obj.author);
    const payload = obj.message || obj;
    const body = flattenContent(payload.content || payload.text || payload.message);
    if (role && body) turns.push({ role, text: body });
  }
  return turns;
}

function parseJsonChat(text) {
  let obj;
  try {
    obj = JSON.parse(text);
  } catch {
    return [];
  }
  const list = obj.messages || obj.turns || obj.conversation || (Array.isArray(obj) ? obj : []);
  const turns = [];
  for (const item of list) {
    const role = roleOf(item.role || item.type);
    const body = flattenContent(item.content || item.text || (item.message && item.message.content));
    if (role && body) turns.push({ role, text: body });
  }
  return turns;
}

function looksLikeChat(turns, raw) {
  if (turns.length >= 1) return true;
  return /Exported on .* from Cursor/i.test(raw) || /\*\*User\*\*/.test(raw);
}

function parseChatFile(filePath, raw) {
  const ext = path.extname(filePath).toLowerCase();
  let turns = [];
  if (ext === ".jsonl") turns = parseJsonl(raw);
  else if (ext === ".json") turns = parseJsonChat(raw);
  else {
    turns = parseCursorMarkdown(raw);
    if (!turns.length) turns = parseJsonl(raw);
  }
  return turns;
}

function lastUserText(turns) {
  for (let i = turns.length - 1; i >= 0; i--) {
    if (turns[i].role === "user") return turns[i].text;
  }
  return "";
}

function renderTranscript(turns) {
  return turns
    .map((t) => `### ${t.role === "user" ? "User" : t.role === "system" ? "System" : "Assistant"}\n\n${t.text}`)
    .join("\n\n---\n\n");
}

function agentPrompt(importedPath, turns, extraNote) {
  const last = lastUserText(turns).trim();
  const recent = turns.slice(-MAX_TURNS_IN_PROMPT);
  let history = renderTranscript(recent);
  if (history.length > MAX_PROMPT) history = history.slice(-MAX_PROMPT);
  return [
    "You are CortexIDE in **Agent** mode. Continue this imported Cursor chat as a **coding agent** (tools, file edits, verification).",
    "Do **not** behave as an instructor or chatbot. Do not recap the whole history. Resume the unfinished work.",
    "",
    `Read the full transcript with read_file: \`${importedPath.replace(/\\/g, "/")}\``,
    extraNote ? extraNote : "",
    "",
    "## Recent turns",
    history,
    "",
    "## Last user message",
    last || "(none — continue the last assistant task)",
    "",
    "Start with a tool call. Call attempt_completion only after the work is actually done.",
  ]
    .filter((line) => line !== "")
    .join("\n");
}

function importChatFile(filePath, workspaceRoot) {
  const raw = fs.readFileSync(filePath, "utf8");
  const turns = parseChatFile(filePath, raw);
  if (!looksLikeChat(turns, raw)) {
    throw new Error("That file does not look like a Cursor chat export (.md with User/Cursor headings, or .jsonl transcript).");
  }
  const destRoot = workspaceRoot
    ? path.join(workspaceRoot, ".cortexide", "imported-chats")
    : path.join(home(), ".cortexide", "imported-chats");
  fs.mkdirSync(destRoot, { recursive: true });
  const slug = slugFromName(path.basename(filePath));
  const dest = path.join(destRoot, `${slug}.md`);
  const header = [
    `# Imported Cursor chat: ${slug}`,
    "",
    `_Source: ${filePath}_`,
    `_Imported: ${new Date().toISOString()}_`,
    "",
    "Continue in CortexIDE **Agent** mode. This file is the transcript.",
    "",
  ].join("\n");
  fs.writeFileSync(dest, `${header}${renderTranscript(turns)}\n`, "utf8");
  const prompt = agentPrompt(dest, turns);
  return {
    slug,
    source: filePath,
    dest,
    turns: turns.length,
    lastUser: lastUserText(turns),
    prompt,
  };
}

function listImported(workspaceRoot) {
  const dir = workspaceRoot
    ? path.join(workspaceRoot, ".cortexide", "imported-chats")
    : path.join(home(), ".cortexide", "imported-chats");
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((n) => /\.md$/i.test(n))
    .map((n) => {
      const file = path.join(dir, n);
      const st = fs.statSync(file);
      return { name: n.replace(/\.md$/i, ""), file, mtime: st.mtimeMs };
    })
    .sort((a, b) => b.mtime - a.mtime);
}

module.exports = {
  importChatFile,
  listImported,
  parseChatFile,
  agentPrompt,
  slugFromName,
  home,
};
