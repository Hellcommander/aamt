"use strict";

// Keeps an agent run inside the model's context window without losing track of the work.
// Progress is tracked programmatically from tool calls (not by asking the model to summarise),
// so it survives compaction and is persisted for the next turn / the next session.

const fs = require("fs");
const path = require("path");

const CHARS_PER_TOKEN = 3.3;

function estimateTokens(messages) {
  let chars = 0;
  for (const m of messages) {
    chars += 12;
    if (m.content) chars += String(m.content).length;
    if (m.tool_calls) chars += JSON.stringify(m.tool_calls).length;
  }
  return Math.ceil(chars / CHARS_PER_TOKEN);
}

function short(s, n) {
  const t = String(s == null ? "" : s).replace(/\s+/g, " ").trim();
  return t.length > n ? t.slice(0, n - 1) + "…" : t;
}

class Progress {
  constructor(seed) {
    const s = seed || {};
    this.task = s.task || "";
    this.read = new Set(s.read || []);
    this.searched = s.searched || [];
    this.edited = new Map(s.edited || []);
    this.commands = s.commands || [];
    this.errors = s.errors || [];
    this.notes = s.notes || [];
  }

  record(name, args, result) {
    const a = args || {};
    const r = String(result || "");
    const failed = /^error:/i.test(r);
    if (name === "Read" && !failed) this.read.add(String(a.path));
    else if ((name === "Grep" || name === "Glob") && !failed) {
      const hits = /^\(no /.test(r) ? 0 : r.split("\n").filter(Boolean).length;
      this.searched.push(name + " " + short(a.pattern, 60) + (a.path ? " in " + short(a.path, 80) : "") + " → " + hits + " hits");
    } else if ((name === "StrReplace" || name === "Write" || name === "Delete") && !failed) {
      const first = r.split("\n")[0];
      const detail = (first.match(/\(([^)]*)\)\s*$/) || [])[1];
      this.edited.set(String(a.path), first.split(" ")[0] + (detail ? ", " + detail : ""));
    } else if (name === "Shell") {
      const exit = (r.match(/^exit (-?\d+)/) || [])[1];
      const tail = r.split("\n").filter((l) => /error|fail|exception|warn/i.test(l)).slice(-3).join(" | ");
      this.commands.push(short(a.command, 140) + " → exit " + (exit == null ? "?" : exit) + (tail ? " · " + short(tail, 200) : ""));
    }
    if (failed) this.errors.push(name + ": " + short(r, 220));
    this.searched = this.searched.slice(-12);
    this.commands = this.commands.slice(-10);
    this.errors = this.errors.slice(-8);
  }

  empty() {
    return !this.read.size && !this.edited.size && !this.commands.length && !this.searched.length && !this.notes.length;
  }

  toText() {
    const out = [];
    if (this.task) out.push("Task: " + short(this.task, 600));
    if (this.edited.size) out.push("Files changed:\n" + [...this.edited].map(([p, d]) => "- " + p + " (" + d + ")").join("\n"));
    if (this.read.size) out.push("Files read: " + [...this.read].slice(-25).join("; "));
    if (this.searched.length) out.push("Searches:\n" + this.searched.map((s) => "- " + s).join("\n"));
    if (this.commands.length) out.push("Commands:\n" + this.commands.map((s) => "- " + s).join("\n"));
    if (this.errors.length) out.push("Errors hit:\n" + this.errors.map((s) => "- " + s).join("\n"));
    if (this.notes.length) out.push("Notes:\n" + this.notes.slice(-6).map((s) => "- " + short(s, 400)).join("\n"));
    return out.join("\n");
  }

  toJSON() {
    return {
      task: this.task,
      read: [...this.read].slice(-40),
      searched: this.searched,
      edited: [...this.edited],
      commands: this.commands,
      errors: this.errors,
      notes: this.notes.slice(-10),
    };
  }

  /** Write a human/agent-readable index of the session to <workspace>/.cortexide/agent/progress.md */
  persist(workspaceRoot) {
    if (!workspaceRoot) return "";
    try {
      const dir = path.join(workspaceRoot, ".cortexide", "agent");
      fs.mkdirSync(dir, { recursive: true });
      const file = path.join(dir, "progress.md");
      fs.writeFileSync(file, "# Agent progress (auto-generated)\n\n_Updated " + new Date().toISOString() + "_\n\n" + this.toText() + "\n", "utf8");
      return file;
    } catch {
      return "";
    }
  }
}

/**
 * Shrink `messages` to fit `budget` tokens. messages[0] is the system prompt and
 * messages[firstUser] is the current task; both are always kept.
 * Returns the level applied (0 = untouched).
 */
function compact(messages, budget, progress, { firstUser = 1, keepRecent = 8 } = {}) {
  if (estimateTokens(messages) <= budget) return 0;
  const recentStart = Math.max(firstUser + 1, messages.length - keepRecent);

  // Level 1: old tool output → head + pointer to re-read.
  for (let i = firstUser + 1; i < recentStart; i++) {
    const m = messages[i];
    if (m.role === "tool" && String(m.content || "").length > 500 && !m._compacted) {
      const c = String(m.content);
      m.content = c.slice(0, 350) + "\n…[compacted " + c.length + " chars — call the tool again if you still need this]";
      m._compacted = true;
    }
  }
  if (estimateTokens(messages) <= budget) return 1;

  // Level 2: replace the middle of the conversation with the programmatic progress digest.
  let cut = recentStart;
  while (cut < messages.length && messages[cut].role === "tool") cut++; // never orphan tool results
  const removed = messages.splice(firstUser + 1, Math.max(0, cut - firstUser - 1));
  if (removed.length) {
    messages.splice(firstUser + 1, 0, {
      role: "user",
      content:
        "[Context compacted — " + removed.length + " earlier messages removed. Progress so far, tracked from your tool calls:]\n" +
        (progress && !progress.empty() ? progress.toText() : "(nothing recorded)") +
        "\nContinue the task from here. Do not repeat work listed above unless it failed.",
    });
  }
  if (estimateTokens(messages) <= budget) return 2;

  // Level 3: hard-trim whatever is still large in the recent window.
  for (let i = firstUser + 1; i < messages.length; i++) {
    const m = messages[i];
    const lim = m.role === "tool" ? 1500 : 2500;
    if (m.content && String(m.content).length > lim) {
      const c = String(m.content);
      m.content = c.slice(0, Math.floor(lim * 0.7)) + "\n…[trimmed]…\n" + c.slice(-Math.floor(lim * 0.3));
    }
  }
  if (estimateTokens(messages) <= budget) return 3;

  // Level 4: system prompt is too big on its own (huge skill / history) — trim it.
  const sys = messages[0];
  const over = (estimateTokens(messages) - budget) * CHARS_PER_TOKEN + 500;
  if (sys && String(sys.content).length > over + 2000) {
    sys.content = String(sys.content).slice(0, String(sys.content).length - over) + "\n…[system context trimmed to fit]";
  }
  return 4;
}

module.exports = { Progress, compact, estimateTokens, short };
