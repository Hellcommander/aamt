"use strict";

// /compress (alias /compact, as in Claude Code): replace a chat's history with a model-written
// summary. The transcript handed to the model is graded: the most recent turns go in nearly in
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
    if (h) earlier = String(h.content || "").replace(/^\[Conversation compressed[^\n]*\]\n\n/, "");
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
      if (h.summary) earlier = String(h.content || "");
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
function summaryMessages(transcript, focus) {
  const system =
    "You compress a coding-agent conversation so the work can continue in a fresh context. " +
    "Write a faithful summary; never invent files, results or decisions. Use exact file paths, " +
    "function names, commands, error messages and setting names from the transcript.";
  const ask = [
    "Summarise the conversation below. Older turns briefly; the most recent turns in much greater detail.",
    "",
    "Use these sections:",
    "1. **Goal**: what the user wants overall, and their stated preferences or constraints.",
    "2. **Earlier work** (brief): what was done and decided in older turns, one or two lines each.",
    "3. **Recent work** (detailed): for the last turns, what was asked, what was changed (file paths and what changed in them), commands run and their results, errors met and how they were resolved.",
    "4. **Files**: files created or changed, each with a short note.",
    "5. **Current state**: what is verified (tests/builds that passed) and what is not.",
    "6. **Open items**: unfinished work, known bugs and next steps, in order.",
    focus ? "\nThe user asked the summary to focus on: " + focus : "",
    "",
    "Reply with the summary only.",
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

/** History entry that stands in for everything before the compression. */
function summaryHistory(summary, turns) {
  return [
    { role: "user", content: "[Conversation compressed with /compress: " + turns + " earlier turn" + (turns === 1 ? "" : "s") + " replaced by this summary]\n\n" + summary, summary: true },
    { role: "assistant", content: "Understood. I have the summary of our earlier conversation and will continue from it." },
  ];
}

module.exports = { parseCommand, turnsFromLog, buildTranscript, summaryMessages, summaryHistory };
