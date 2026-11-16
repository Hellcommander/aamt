"use strict";

// Named agents: a system-prompt addition, a tool set, permission rules and a step limit under a name.
// Design follows opencode's agents (https://github.com/anomalyco/opencode, MIT, Copyright (c) 2025
// opencode): built-in primary agents (build, plan) and sub-agents (explore), Markdown agent files whose
// front matter sets description / mode / tools / permissions / steps and whose body is the prompt,
// project files overriding global ones, and permission rules appended after the global rules.
// Claude Code's `.claude/agents/*.md` (name, description, tools: "Read, Grep") load the same way.
// Written from the documented behaviour; no opencode source is copied.

const fs = require("fs");
const path = require("path");
const os = require("os");
const fm = require("./frontmatter");
const perms = require("./permissions");

const EDIT_TOOLS = ["StrReplace", "MultiEdit", "Write", "Delete"];
/** Commands a planning agent may run without asking: they only look. */
const LOOK_COMMANDS = [
  "git status *", "git diff *", "git log *", "git show *", "git branch *", "git blame *", "git ls-files *", "git rev-parse *",
  "ls *", "dir *", "Get-ChildItem *", "gci *", "Get-Content *", "gc *", "cat *", "type *", "Get-Item *", "Test-Path *",
  "Select-String *", "sls *", "rg *", "findstr *", "where *", "where.exe *", "Get-Command *", "node --version", "dotnet --info",
];

/**
 * Built-in agents. mode: primary (runs a turn), subagent (only through Task), all (both).
 * tools: null = every tool; deny: tools removed from the set.
 */
const BUILTIN = {
  build: { name: "build", mode: "primary", description: "Default coding agent: plans, edits, runs and verifies.", builtin: true },
  plan: {
    name: "plan",
    mode: "primary",
    builtin: true,
    description: "Explores and plans without editing files; commands that only look run, others ask first.",
    deny: EDIT_TOOLS,
    rules: [{ action: "shell", resource: "*", effect: "ask" }, ...LOOK_COMMANDS.map((c) => ({ action: "shell", resource: c, effect: "allow" }))],
    prompt:
      "You are in Plan mode. Do not edit, create or delete files (those tools are not available). Read and search as much as you need, then answer with a step-by-step implementation plan: the files to change, what changes in each, risks, and how to verify. Do not call attempt_completion to claim work was done; give the plan as your answer.",
    readOnly: true,
  },
  ask: {
    name: "ask",
    mode: "primary",
    builtin: true,
    description: "Answers questions about the code; no edits and no commands.",
    deny: [...EDIT_TOOLS, "Shell"],
    prompt: "You are in Ask mode. Answer the question from the code: read and search as needed. You cannot edit files or run commands.",
    readOnly: true,
  },
  explore: {
    name: "explore",
    mode: "subagent",
    builtin: true,
    description: "Read-only research: searches and reads code or web pages and reports what it found (the default for Task).",
  },
};

/** Composer modes (lib/composer.js) → the agent that runs the turn. */
const MODE_AGENT = { agent: "build", debug: "build", multitask: "build", plan: "plan", ask: "ask" };

function dirsFor(roots, home) {
  const h = home || os.homedir();
  const global = [path.join(h, ".config", "opencode", "agents"), path.join(h, ".config", "opencode", "agent"), path.join(h, ".claude", "agents"), path.join(h, ".cortexide", "agents")];
  const project = [];
  for (const r of roots || []) {
    if (!r) continue;
    project.push(path.join(r, ".opencode", "agents"), path.join(r, ".opencode", "agent"), path.join(r, ".claude", "agents"), path.join(r, ".cortexide", "agents"));
  }
  return [...global, ...project]; // later wins
}

function walkMd(dir, base = dir, depth = 0, out = []) {
  let ents = [];
  try {
    ents = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return out;
  }
  for (const e of ents) {
    const p = path.join(dir, e.name);
    if (e.isDirectory() && depth < 2) walkMd(p, base, depth + 1, out);
    else if (e.isFile() && /\.md$/i.test(e.name)) out.push({ file: p, id: path.relative(base, p).replace(/\\/g, "/").replace(/\.md$/i, "") });
  }
  return out;
}

/** One agent file → agent definition (null for a disabled or unreadable one). */
function fromFile(file, id) {
  let text;
  try {
    text = fs.readFileSync(file, "utf8");
  } catch {
    return null;
  }
  const { data, body } = fm.parse(text);
  const name = String(data.name || id).trim().toLowerCase().replace(/\s+/g, "-");
  if (!name) return null;
  const tools = fm.toolList(data.tools);
  const rules = perms.normalize(data.permissions || data.permission || []);
  const steps = Number(data.steps || data.maxSteps || data.max_steps) || 0;
  let mode = String(data.mode || "").toLowerCase();
  // Claude Code agent files are sub-agents; opencode's default for a new agent is primary.
  if (!["primary", "subagent", "all"].includes(mode)) mode = /[\\/]\.claude[\\/]agents[\\/]/i.test(file) ? "subagent" : "primary";
  return {
    name,
    file,
    mode,
    description: String(data.description || "").trim(),
    prompt: body,
    allowTools: tools.allow,
    denyTools: tools.deny,
    rules,
    steps,
    hidden: data.hidden === true,
    disabled: data.disabled === true || data.disable === true,
  };
}

/** Built-ins merged with agent files (global, then project; a later file with the same name replaces it). */
function loadAgents(roots, { home } = {}) {
  const map = new Map(Object.values(BUILTIN).map((a) => [a.name, { ...a }]));
  for (const dir of dirsFor(roots, home)) {
    for (const { file, id } of walkMd(dir)) {
      const a = fromFile(file, id);
      if (!a) continue;
      if (a.disabled) {
        map.delete(a.name);
        continue;
      }
      const prev = map.get(a.name);
      // Overriding a built-in keeps what the file does not set (opencode merges agent config the same way).
      map.set(a.name, prev && prev.builtin ? { ...prev, ...a, rules: [...(prev.rules || []), ...a.rules], prompt: a.prompt || prev.prompt, builtin: false } : a);
    }
  }
  return [...map.values()];
}

function find(agents, name) {
  const n = String(name || "").trim().toLowerCase().replace(/^@/, "");
  return (agents || []).find((a) => a.name === n) || null;
}

const isPrimary = (a) => a && (a.mode === "primary" || a.mode === "all");
const isSub = (a) => a && (a.mode === "subagent" || a.mode === "all");

/** Tool names this agent may use, out of `names`. */
function toolNames(agent, names) {
  if (!agent) return names;
  const lower = (s) => String(s).toLowerCase();
  let out = names;
  if (agent.allowTools && agent.allowTools.size) out = out.filter((n) => agent.allowTools.has(lower(n)) || n === "attempt_completion" || n === "TodoWrite");
  const deny = new Set([...(agent.deny || []).map(lower), ...[...(agent.denyTools || [])].map(lower)]);
  // opencode's V1 tool switches: write/edit/patch cover every edit tool, bash the shell.
  if (deny.has("edit") || deny.has("write") || deny.has("patch")) EDIT_TOOLS.forEach((t) => deny.add(lower(t)));
  if (deny.has("bash")) deny.add("shell");
  // Background shells are part of the shell: no Shell, no reading or stopping them either.
  if (deny.has("shell")) ["shelloutput", "shellkill"].forEach((t) => deny.add(t));
  return out.filter((n) => !deny.has(lower(n)));
}

/** The primary agent for a message: "@name rest" picks a primary agent, else the composer mode's agent. */
function forMessage(agents, text, mode) {
  const m = /^\s*@([\w./-]+)\s+([\s\S]*)$/.exec(String(text || ""));
  if (m) {
    const a = find(agents, m[1]);
    if (a && isPrimary(a)) return { agent: a, text: m[2] };
    if (a && isSub(a)) return { agent: find(agents, "build"), text: m[2] + "\n\n(Use the Task tool with agent \"" + a.name + "\" for this.)", via: a.name };
  }
  const fromPrefix = /^\[Mode: (\w+)\]/.exec(String(text || ""));
  const id = MODE_AGENT[String(mode || (fromPrefix ? fromPrefix[1].toLowerCase() : "agent"))] || "build";
  return { agent: find(agents, id) || BUILTIN.build, text };
}

/** "- name: description" lines of the agents Task may launch. */
function subagentCatalog(agents) {
  return (agents || []).filter((a) => isSub(a) && !a.hidden).map((a) => "- " + a.name + ": " + (a.description || "(no description)"));
}

module.exports = { BUILTIN, MODE_AGENT, EDIT_TOOLS, LOOK_COMMANDS, loadAgents, fromFile, find, isPrimary, isSub, toolNames, forMessage, subagentCatalog, dirsFor };
