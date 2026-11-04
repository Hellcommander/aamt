"use strict";

const fs = require("fs");
const path = require("path");
const { home, exists, cursorProjectSlug } = require("./scan");

const MARKER_BEGIN = "# BEGIN LOCAL-AGENT-BRIDGE";
const MARKER_END = "# END LOCAL-AGENT-BRIDGE";
const GENERATED = ".agent-bridge-generated";
// Written by builds before the rename (<= 2.0.0); cleaned up on sync.
const LEGACY_SECTION = /# BEGIN CURSOR-AGENT-BRIDGE[\s\S]*?# END CURSOR-AGENT-BRIDGE\n?/;
const LEGACY_GENERATED = ".cursor-bridge-generated";
const LEGACY_FILES = [["agents", "cursor-agent.md"], ["rules", "00-cursor-agent.md"]];
const MAX_SKILL_BYTES = 60 * 1024;

function mkdirp(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function writeFile(file, contents) {
  mkdirp(path.dirname(file));
  fs.writeFileSync(file, contents, "utf8");
}

function upsertMarkedSection(file, section) {
  let existing = "";
  if (exists(file)) {
    try {
      existing = fs.readFileSync(file, "utf8");
    } catch {
      existing = "";
    }
  }
  existing = existing.replace(LEGACY_SECTION, "");
  const block = `${MARKER_BEGIN}\n${section.trim()}\n${MARKER_END}\n`;
  const re = new RegExp(`${MARKER_BEGIN}[\\s\\S]*?${MARKER_END}\\n?`);
  const next = existing.match(re) ? existing.replace(re, block) : (existing.trimEnd() + (existing ? "\n\n" : "") + block);
  writeFile(file, next);
}

function skillBody(skill) {
  const header = [
    `> Bridged from skill \`${skill.name}\` (${skill.source}).`,
    `> Source: ${skill.file}`,
    `> Supporting files (sdk, references, scripts) live in: ${skill.dir}`,
    `> If this body is truncated, call read_file on the source path.`,
    "",
  ].join("\n");
  const max = MAX_SKILL_BYTES - Buffer.byteLength(header, "utf8") - 80;
  let body = skill.instructions;
  if (Buffer.byteLength(body, "utf8") > max) {
    body = body.slice(0, Math.max(0, max - 80)) + "\n\n[truncated — read the source SKILL.md for the rest]";
  }
  return `${header}${body}\n`;
}

function pinChatSkills(skills) {
  const pin = new Set(["import-chat"]);
  const pinned = [];
  const rest = [];
  for (const skill of skills || []) {
    if (pin.has(skill.name)) pinned.push(skill);
    else rest.push(skill);
  }
  return [...pinned, ...rest];
}

function syncSkills(workspaceRoot, skills, maxSkills) {
  const destRoot = path.join(workspaceRoot, ".cortexide", "skills");
  mkdirp(destRoot);
  const mine = new Set();
  if (exists(destRoot)) {
    for (const name of fs.readdirSync(destRoot)) {
      if (exists(path.join(destRoot, name, GENERATED)) || exists(path.join(destRoot, name, LEGACY_GENERATED))) {
        fs.rmSync(path.join(destRoot, name), { recursive: true, force: true });
      }
    }
  }
  const ordered = pinChatSkills(skills);
  const cap = Math.max(1, Math.min(64, maxSkills || 64));
  const written = [];
  for (const skill of ordered.slice(0, cap)) {
    const dir = path.join(destRoot, skill.name);
    mkdirp(dir);
    writeFile(path.join(dir, GENERATED), `${skill.file}\n`);
    writeFile(
      path.join(dir, "SKILL.md"),
      `---\nname: ${skill.name}\ndescription: ${JSON.stringify(skill.description || skill.name)}\n---\n\n${skillBody(skill)}`
    );
    mine.add(skill.name);
    written.push(skill);
  }
  return written;
}

function agentMarkdown() {
  return `---
name: local-agent
description: Proper coding agent. Use for any task that needs tools, skills, file edits, verification, or canvases. Prefer this over chat-only replies.
tools: glob_files, grep_search, read_file, edit_file, multi_edit, get_diagnostics, todo_write, run_command, run_subagent, attempt_completion
---

You are a coding agent, not a chatbot.

## Loop
1. If the user asked you to DO something, start with a tool call. Do not narrate the plan first.
2. Discover with glob_files / grep_search / read_file.
3. If a skill matches, read its SKILL.md (slash \`/skill-name\` or read_file on the Source path) before acting.
4. Edit with edit_file or multi_edit. After edits, read_file the result and call get_diagnostics.
5. Keep going until the task is actually finished. Do not stop after two or three tools.
6. Call attempt_completion with a specific summary only after verify steps.

## Skills
Local Agent Bridge synced SKILL.md files (Cursor, Claude, Agents folders) into \`.cortexide/skills\`. Invoke with \`/skill-name\`. MCP tools list_skills / read_skill / match_skills can load bodies that did not fit the 64-skill cap.

## Canvases
Canvases are single \`.canvas.tsx\` files (Cursor's canvas format). Write them under the user's Cursor project canvases folder (see the Local Agent Bridge rule). Import only from \`cursor/canvas\`. Default-export one component. No fetch. No empty states. Link the absolute path in chat.

## Tools
Use CortexIDE Agent mode tools. Never claim a file changed unless a tool wrote it.
`;
}

function rulesMarkdown(skills, canvases, workspaceRoot) {
  const slug = cursorProjectSlug(workspaceRoot);
  const cursorCanvases = path.join(home(), ".cursor", "projects", slug, "canvases");
  const catalog = skills
    .slice(0, 80)
    .map((s) => `- \`/${s.name}\` — ${s.description || s.name}`)
    .join("\n");
  const canvasList = canvases.slice(0, 40).map((c) => `- ${c.name} — ${c.file}`).join("\n") || "(none found yet)";
  return `# Local Agent Bridge

Always apply. You are CortexIDE running as a **coding agent**.

## Mode
Work in **Agent** mode (not Gather, not plain chat) whenever the user wants code, files, searches, or canvases changed. Start with tools. Do not early-stop. Finish with \`attempt_completion\`.

## Skills
Read a skill before using its workflow. Slash-commands: \`/skill-name\`. Full bodies live in \`.cortexide/skills/<name>/SKILL.md\` (bridged) and at the Source path in that file.

Catalog:
${catalog}

## Canvases
Cursor canvas files are \`.canvas.tsx\` (not the Code Canvas infinite-board extension).

Cursor's canvas host is proprietary and is not a VSIX CortexIDE can import. Local Agent Bridge registers a custom editor that transpiles \`.canvas.tsx\` and renders it with a local \`cursor/canvas\` runtime. Open the file beside chat to preview; use **Open Canvas Source** to edit the TSX.

Write new canvases to:
\`${cursorCanvases.replace(/\\/g, "/")}\`

Also copy or write to the workspace \`canvases/\` folder so CortexIDE can open them.

Rules from the canvas skill:
- One \`.canvas.tsx\` file, default-export, import only \`cursor/canvas\`
- Embed data inline. No network. Omit empty sections.
- Mention the canvas with a markdown link to its absolute path.
- Docs canvases may use CortexIDE extras: \`DocsShell\`, \`TableOfContents\`, \`DocSection\`, \`CodeBlock\`, \`References\`.

Existing canvases:
${canvasList}

MCP tools: list_canvases, read_canvas, import_cursor_chat, list_imported_chats.

Imported Cursor chats live in \`.cortexide/imported-chats\`. Continue them with **Local Agent Bridge: Import Chat** / **Continue Imported Chat in Agent**. Do not treat those transcripts as instructor Q&A — resume as an agent.
`;
}

function writeUserImportSkill() {
  const src = path.join(__dirname, "..", "skills", "import-chat", "SKILL.md");
  if (!exists(src)) return;
  const destDir = path.join(home(), ".cortexide", "skills", "import-chat");
  mkdirp(destDir);
  writeFile(path.join(destDir, "SKILL.md"), fs.readFileSync(src, "utf8"));
}

function voidrulesSection(skillCount, canvasCount) {
  return `CortexIDE is running as a coding agent via Local Agent Bridge.
- Use Agent mode tools for any real work. Do not stop after a few calls. Call attempt_completion when done.
- Skills are slash-commands under .cortexide/skills (${skillCount} synced). Read a matching SKILL.md before following it.
- Canvases are .canvas.tsx files (${canvasCount} found). Use the canvas skill before writing one.
- MCP server local-agent-bridge exposes list_skills, read_skill, match_skills, list_canvases, read_canvas, import_cursor_chat, list_imported_chats.
- Imported Cursor chats are in .cortexide/imported-chats. Continue them in Agent mode; do not answer as an instructor.`;
}

function syncWorkspace(workspaceRoot, skills, canvases, options) {
  const maxSkills = options && options.maxSkills != null ? options.maxSkills : 64;
  const writtenSkills = syncSkills(workspaceRoot, skills, maxSkills);
  writeUserImportSkill();
  for (const [dir, name] of LEGACY_FILES) fs.rmSync(path.join(workspaceRoot, ".cortexide", dir, name), { force: true });
  writeFile(path.join(workspaceRoot, ".cortexide", "agents", "local-agent.md"), agentMarkdown());
  writeFile(path.join(workspaceRoot, ".cortexide", "rules", "00-local-agent.md"), rulesMarkdown(skills, canvases, workspaceRoot));
  upsertMarkedSection(path.join(workspaceRoot, ".voidrules"), voidrulesSection(skills.length, canvases.length));
  mkdirp(path.join(workspaceRoot, "canvases"));
  const slug = cursorProjectSlug(workspaceRoot);
  mkdirp(path.join(home(), ".cursor", "projects", slug, "canvases"));
  return { writtenSkills, slug };
}

module.exports = {
  syncWorkspace,
  MARKER_BEGIN,
  MARKER_END,
};
