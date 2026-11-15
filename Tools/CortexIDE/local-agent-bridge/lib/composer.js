// Composer helpers shared by the extension (require) and the Agent panel (agent-view.js inlines
// this file into the page, like file-ref.js): what a drop carries, the chat modes, and how
// attachments and a mode are written into the prompt. No require() here: it also runs in the webview.
var Composer = (function () {
  "use strict";

  // Modes, as in Cursor's composer menu. "agent" is the normal turn; the others prefix an instruction.
  var MODES = {
    agent: { label: "Agent", hint: "Plan, edit and run: the normal agent", text: "" },
    plan: {
      label: "Plan",
      hint: "Generate an implementation plan",
      text: "[Mode: Plan] Do not edit files and do not run commands that change anything. Read and search as much as you need, then answer with a step-by-step implementation plan: the files to change, what changes in each, risks, and how to verify. Wait for me to approve the plan before implementing it.",
    },
    debug: {
      label: "Debug",
      hint: "Pinpoint the root cause of an issue",
      text: "[Mode: Debug] Find the root cause before changing code: reproduce the problem, read the actual error, form hypotheses and confirm one with evidence (logs, a failing test, a minimal repro). Then make the smallest fix, verify it, and report the cause, the fix and the evidence.",
    },
    multitask: {
      label: "Multitask",
      hint: "Orchestrate multiple subagents in parallel",
      text: "[Mode: Multitask] Split the work into independent parts and hand each to a subagent (the Task tool), several at once where they do not touch the same files. Collect their reports, resolve conflicts, verify the combined result, and summarise what each part did.",
    },
    ask: {
      label: "Ask",
      hint: "Answer questions without making edits",
      text: "[Mode: Ask] Answer the question only. Do not edit, create or delete files and do not run commands that change anything; reading and searching is fine.",
    },
  };

  /** URIs in a drag from VS Code (Explorer, editor tabs; hold Shift) or another app. `get(type)` reads dataTransfer. */
  function dropUris(get) {
    var out = [];
    var add = function (u) {
      u = String(u || "").trim();
      if (u && u.charAt(0) !== "#" && out.indexOf(u) < 0) out.push(u);
    };
    var raw = get("application/vnd.code.uri-list") || get("text/uri-list") || "";
    raw.split(/\r?\n/).forEach(add);
    try {
      var list = JSON.parse(get("resourceurls") || "[]");
      if (Array.isArray(list)) list.forEach(add);
    } catch (e) {
      /* not JSON */
    }
    if (!out.length) {
      // Plain text that is only file URIs or absolute paths (some file managers send that).
      var lines = String(get("text/plain") || "").split(/\r?\n/).map(function (l) { return l.trim(); }).filter(Boolean);
      if (lines.length && lines.every(function (l) { return /^file:\/\//i.test(l) || /^(?:[A-Za-z]:[\\/]|\\\\|\/)\S/.test(l); })) lines.forEach(add);
    }
    return out;
  }

  /**
   * The text sent for one message: the mode's instruction, the message, then the attachments.
   * items: { path } (a file or folder; images among them are attached for vision models)
   *     or { label, text } (pasted context such as Problems or a selection).
   */
  function compose(text, mode, items) {
    var parts = [];
    var m = MODES[mode];
    if (m && m.text) parts.push(m.text);
    if (String(text || "").trim()) parts.push(String(text).trim());
    var paths = [], blocks = [];
    (items || []).forEach(function (it) {
      if (it && it.path) { if (paths.indexOf(it.path) < 0) paths.push(it.path); }
      else if (it && it.text) blocks.push("[" + (it.label || "Context") + "]\n```\n" + String(it.text).replace(/```/g, "``\u200b`") + "\n```");
    });
    if (paths.length) parts.push("[Attached files]\n" + paths.map(function (p) { return "- " + p; }).join("\n"));
    return parts.concat(blocks).join("\n\n");
  }

  /** A file name that is safe to write in the attachments folder. */
  function safeName(name) {
    var n = String(name || "").split(/[\\/]/).pop().replace(/[<>:"|?*\u0000-\u001f]/g, "_").replace(/^\.+/, "").slice(-120);
    return n || "attachment";
  }

  var IMAGE = /\.(png|jpe?g|gif|webp|bmp)$/i;
  return { MODES: MODES, dropUris: dropUris, compose: compose, safeName: safeName, IMAGE: IMAGE };
})();
if (typeof module === "object" && module.exports) module.exports = Composer;
