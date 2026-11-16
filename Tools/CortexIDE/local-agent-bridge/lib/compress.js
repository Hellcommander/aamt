"use strict";

// /compress (alias /compact): replace a chat's history with a model-written summary, written so
// the work can go on in a fresh context. The behaviour takes inspiration from Claude Code's /compact
// (a structured summary that keeps every user message, the current work and the next step; auto-compact
// near the context limit; the working set carried over); the wording and code are this extension's own. The transcript handed to the model is graded: the most recent turns go in nearly in
// full (prompts, tool calls with results, answers, changed files), older turns are shortened, and
// an earlier /compress summary is carried forward. The summary prompt asks for the same shape:
// brief on old work, detailed on recent work, so the next turn can continue without the history.

const COMMAND = /^\/(compress|compact)\b\s*([\s\S]*)$/i;

/** `/compress [focus]` → { focus } ; anything else → null. */
function parseCommand(text) {
  const m = COMMAND.exec(String(text || "").trim());
  return m ? { focus: m[2].trim() } : null;
}

function clip(s, n) {
  s = String(s == null ? "" : s);
  return s.length > n ? s.slice(0, n) + " …[" + (s.length - n) + " more chars]" : s;
}

/**
 * Split a chat log into turns. A turn starts at a "user" entry. Everything before the latest
 * /compress marker is replaced by that marker's summary.
 * @returns {{ earlier: string, turns: {user:string, items:object[]}[] }}
 */
function turnsFromLog(log, history) {
  log = Array.isArray(log) ? log : [];
  let start = 0;
  let earlier = "";
  for (let i = log.length - 1; i >= 0; i--) {
    if (log[i] && log[i].compressed) {
      earlier = String(log[i].summary || "");
      start = i + 1;
      break;
    }
  }
  // The panel log is capped; if its marker was trimmed away the history still holds the summary.
  if (!earlier && Array.isArray(history)) {
    const h = history.find((x) => x && x.summary);
    if (h) earlier = h.raw != null ? String(h.raw) : String(h.content || "").replace(/^\[Conversation compressed[^\n]*\]\n\n/, "");
  }
  const turns = [];
  let skip = false;
  for (const e of log.slice(start)) {
    if (!e) continue;
    // A /compress that failed or was stopped is not part of the conversation.
    // A message steered into a running turn belongs to that turn, it is not a new one.
    if (e.cls === "user" && e.steered && turns.length && !skip) {
      turns[turns.length - 1].user += "\n\n[Added while working] " + String(e.text || "");
    } else if (e.cls === "user") {
      skip = !!e.command;
      if (!skip) turns.push({ user: String(e.text || ""), items: [] });
    } else if (!skip && turns.length) turns[turns.length - 1].items.push(e);
  }
  // A chat with no panel log (e.g. imported, or the log was trimmed away): use the text history.
  if (!turns.length && Array.isArray(history)) {
    for (const h of history) {
      if (h.summary) earlier = h.raw != null ? String(h.raw) : String(h.content || "");
      else if (h.role === "user") turns.push({ user: String(h.content || ""), items: [] });
      else if (h.role === "assistant" && turns.length) turns[turns.length - 1].items.push({ cls: "assistant", text: h.content });
    }
  }
  return { earlier, turns };
}

/** One turn as text. `detail` 2 = recent (full), 1 = middle, 0 = old (outline only). */
function turnText(t, n, detail) {
  const lim = [{ user: 400, answer: 500, tool: 0 }, { user: 1500, answer: 1500, tool: 160 }, { user: 4000, answer: 5000, tool: 900 }][detail];
  const out = ["### Turn " + n + (detail === 2 ? " (recent)" : ""), "User: " + clip(t.user, lim.user)];
  const tools = [];
  for (const e of t.items) {
    if (e.cls === "tool") {
      const head = (e.ok === false ? "✗ " : "") + (e.label || e.name || "tool");
      tools.push(lim.tool ? "- " + head + (e.text ? "\n  → " + clip(String(e.text).replace(/\n/g, "\n    "), lim.tool) : "") : head);
    } else if (e.cls === "changes" && Array.isArray(e.files)) {
      out.push("Files changed: " + e.files.map((f) => f.path + " (" + (f.kind || "modified") + (f.added != null ? " +" + f.added + "/−" + (f.removed || 0) : "") + ")").join(", "));
    } else if (e.cls === "err") out.push("Error: " + clip(e.text, lim.answer ? 400 : 160));
    else if (e.cls === "assistant") out.push("Assistant: " + clip(e.text, lim.answer));
    // What the model said while working (recent turns only): its reasoning and plans for the next step.
    else if (e.cls === "thought" && detail === 2 && e.text) out.push("Assistant (working): " + clip(e.text, 600));
    else if (e.cls === "sys" && detail === 2 && e.text && !/^Progress index:/.test(e.text)) out.push("Note: " + clip(e.text, 300));
  }
  if (tools.length) out.splice(2, 0, lim.tool ? "Tool calls:\n" + tools.join("\n") : "Tools: " + tools.slice(0, 40).join(", ") + (tools.length > 40 ? ", … (" + tools.length + " total)" : ""));
  return out.join("\n");
}

/**
 * The transcript for the summariser, within `maxChars`: recent turns in full, older ones shorter.
 * If it is still too long, older turns drop a detail level, then the oldest are left out.
 */
function buildTranscript({ log, history, progress }, { recentTurns = 3, maxChars = 60000 } = {}) {
  const { earlier, turns } = turnsFromLog(log, history);
  const level = turns.map((_, i) => (i >= turns.length - recentTurns ? 2 : i >= turns.length - recentTurns * 3 ? 1 : 0));
  const render = () => {
    const parts = [];
    if (earlier) parts.push("## Summary from an earlier /compress\n" + earlier);
    const skipped = level.filter((l) => l < 0).length;
    if (skipped) parts.push("(" + skipped + " oldest turn" + (skipped > 1 ? "s" : "") + " left out for length)");
    turns.forEach((t, i) => {
      if (level[i] >= 0) parts.push(turnText(t, i + 1, level[i]));
    });
    // Every user message, so the summary can keep what was asked and every correction.
    const asked = turns.map((t, i) => "- (" + (i + 1) + ") " + clip(t.user.replace(/\s+/g, " ").trim(), 1200)).filter((l) => l.length > 8);
    if (asked.length) {
      let list = asked.join("\n");
      const cap = Math.min(12000, Math.floor(maxChars * 0.2));
      if (list.length > cap) list = "…\n" + list.slice(list.length - cap);
      parts.push("## Every message from the user (oldest first)\n" + list);
    }
    if (progress && ((progress.edited || []).length || (progress.commands || []).length)) {
      const p = { edited: progress.edited || [], commands: progress.commands || [], errors: progress.errors || [] };
      parts.push("## Tracked progress (files changed, commands run)\n" + JSON.stringify(p).slice(0, 3000));
    }
    return parts.join("\n\n");
  };
  let text = render();
  // Shrink from the oldest end: lower one level at a time, recent turns last.
  for (let guard = 0; text.length > maxChars && guard < turns.length * 3 + 3; guard++) {
    let i = level.findIndex((l) => l >= 0);
    if (i < 0) break;
    const floor = i >= turns.length - 1 ? 1 : -1; // never drop the latest turn entirely
    if (level[i] > floor) level[i]--;
    else break;
    text = render();
  }
  if (text.length > maxChars) text = text.slice(text.length - maxChars);
  return { text, turns: turns.length, hadSummary: !!earlier };
}

/** The request that turns the transcript into a summary. */
function summaryMessages(transcript, focus, { instructions = "" } = {}) {
  const system =
    "You compact a coding-agent conversation so the same agent can continue the work in a fresh context, " +
    "without the user repeating anything. Be faithful: never invent files, results or decisions. Keep exact " +
    "file paths, function and setting names, commands, error messages and numbers from the transcript.";
  const ask = [
    "Write a summary of the conversation below. Older turns briefly; the most recent turns in much greater detail.",
    "",
    "First think in <analysis>…</analysis>: walk through the conversation in order and note each request, what was done, " +
      "the files and code involved, errors and how they were fixed, and anything the user corrected. Then write the summary " +
      "in <summary>…</summary> with these sections:",
    "",
    "1. **Request and intent**: what the user wants overall, in detail, with their stated preferences and constraints.",
    "2. **Technical context**: languages, frameworks, tools, conventions and project facts that matter for the work.",
    "3. **Files and code**: every file read, created or changed that still matters: why it matters, what changed, and a short exact snippet where the next step depends on it.",
    "4. **Errors and fixes**: errors met and how each was resolved, including every correction or complaint from the user.",
    "5. **Approaches**: what was tried, what worked, what did not, and decisions taken.",
    "6. **User messages**: every message from the user, in order, nearly word for word (short ones in full). These carry intent; do not drop any.",
    "7. **Pending tasks**: work the user asked for that is not finished.",
    "8. **Current work**: precisely what was being done right before this summary, with file paths and code.",
    "9. **Next step**: only if it follows directly from the user's latest request; quote that request. Leave it out if the last task was finished.",
    focus ? "\nThe user asked the summary to focus on: " + focus : "",
    instructions ? "\nProject instructions for compacting:\n" + instructions : "",
    "",
    "Reply with the <analysis> and <summary> blocks only.",
    "",
    "<transcript>",
    transcript,
    "</transcript>",
  ].join("\n");
  return [
    { role: "system", content: system },
    { role: "user", content: ask },
  ];
}

/** The summary out of the model's reply: the <summary> block, without reasoning or <analysis>. */
function extractSummary(raw) {
  let t = String(raw || "").replace(/<think>[\s\S]*?<\/think>/gi, "").trim();
  const m = /<summary>([\s\S]*?)(<\/summary>|$)/i.exec(t);
  if (m && m[1].trim()) return m[1].trim();
  return t.replace(/<analysis>[\s\S]*?(<\/analysis>|$)/i, "").replace(/<\/?summary>/gi, "").trim();
}

/**
 * "Compact instructions" from project rules (AGENTS.md / CLAUDE.md): the section under a heading
 * like "## Compact instructions", up to the next heading of the same or a higher level.
 */
function compactInstructions(rules) {
  const lines = String(rules || "").split(/\r?\n/);
  const at = lines.findIndex((l) => /^#{1,6}\s*(compact|compaction|compress)(ion)?\s+instructions\b/i.test(l.trim()));
  if (at < 0) return "";
  const level = (/^#+/.exec(lines[at].trim()) || ["#"])[0].length;
  const out = [];
  for (const l of lines.slice(at + 1)) {
    const h = /^(#{1,6})\s/.exec(l.trim());
    if (h && h[1].length <= level) break;
    out.push(l);
  }
  return out.join("\n").trim().slice(0, 3000);
}

/** The files a chat was working with, newest edits first, then reads (from its progress index). */
function workingFiles(progress, max = 12) {
  const p = progress || {};
  const edited = (p.edited || []).map((e) => (Array.isArray(e) ? e[0] : e)).filter(Boolean).reverse();
  const read = (p.read || []).filter(Boolean).reverse();
  const seen = new Set();
  const out = [];
  for (const f of [...edited, ...read]) {
    const k = String(f).toLowerCase();
    if (seen.has(k)) continue;
    seen.add(k);
    out.push(String(f));
    if (out.length >= max) break;
  }
  return out;
}

/**
 * History entry that stands in for everything before the compaction, plus what carries over:
 * the open todo list and the files the chat was working with.
 */
function summaryHistory(summary, turns, { todos = [], files = [], auto = false } = {}) {
  const parts = [
    "[Conversation compressed" + (auto ? " automatically (the history was nearing the context limit)" : " with /compress") + ": " + turns + " earlier turn" + (turns === 1 ? "" : "s") + " replaced by this summary]",
    "This chat continues from an earlier conversation that was compacted. The summary below covers it. Pick up where it left off, without asking the user to repeat anything.",
    summary,
  ];
  const open = (todos || []).filter((t) => t && t.content && t.status !== "completed");
  if (open.length) parts.push("Open todo list at the time of compaction:\n" + open.map((t) => "- [" + (t.status === "in_progress" ? ">" : " ") + "] " + t.content).join("\n"));
  if (files && files.length) parts.push("Files this chat was working with (Read them again before editing; their contents are not in this summary):\n" + files.map((f) => "- " + f).join("\n"));
  return [
    { role: "user", content: parts.join("\n\n"), summary: true, raw: summary },
    { role: "assistant", content: "Understood. I have the summary of our earlier conversation and will continue from it." },
  ];
}

/**
 * Whether a chat's carried-over history should be compacted before its next turn: when it would
 * fill more than `percent` of the context window (history only; the turn itself needs the rest).
 * Mirrors what the agent loop sends: each message clipped to 3000 chars, a summary to 24000.
 */
function historyTokens(history) {
  let chars = 0;
  for (const h of history || []) if (h && h.content) chars += Math.min(String(h.content).length, h.summary ? 24000 : 3000);
  return Math.ceil(chars / 3.5);
}
function autoCompactDue(history, contextTokens, percent) {
  if (!percent || percent <= 0 || !contextTokens) return false;
  const turns = (history || []).filter((h) => h && h.role === "user" && !h.summary).length;
  if (turns < 2) return false; // nothing worth summarising yet
  return historyTokens(history) > (contextTokens * Math.min(95, percent)) / 100;
}

module.exports = { parseCommand, turnsFromLog, turnText, buildTranscript, summaryMessages, extractSummary, compactInstructions, workingFiles, summaryHistory, historyTokens, autoCompactDue };
