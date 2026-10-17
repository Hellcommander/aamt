"use strict";

// Recover tool calls that small local models emit as text instead of native tool_calls:
//   <tool_call>{"name": ..., "arguments": {...}}</tool_call>   (Qwen / Hermes template)
//   ```json {"name": ..., "arguments": {...}} ```             (fenced)
//   {"name": "Read", "arguments": {...}}                      (bare JSON — Ollama qwen2.5-coder)

const { canonName, NAMES } = require("./agent-tools");

function tryJson(raw) {
  const s = String(raw || "").trim().replace(/^```(?:json)?/i, "").replace(/```$/, "").trim();
  if (!s) return null;
  try {
    return JSON.parse(s);
  } catch {
    return null;
  }
}

/** Every balanced top-level {...} span in text (string-aware). */
function jsonObjects(text) {
  const out = [];
  const s = String(text || "");
  let depth = 0;
  let start = -1;
  let inStr = false;
  let esc = false;
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (inStr) {
      if (esc) esc = false;
      else if (c === "\\") esc = true;
      else if (c === '"') inStr = false;
      continue;
    }
    if (c === '"') inStr = true;
    else if (c === "{") {
      if (depth === 0) start = i;
      depth++;
    } else if (c === "}" && depth > 0) {
      depth--;
      if (depth === 0 && start >= 0) {
        out.push(s.slice(start, i + 1));
        start = -1;
      }
    }
  }
  return out;
}

function asCall(obj) {
  if (!obj || typeof obj !== "object" || Array.isArray(obj)) return null;
  const fn = obj.function && typeof obj.function === "object" ? obj.function : obj;
  const name = canonName(fn.name || fn.tool || fn.tool_name || (typeof obj.function === "string" ? obj.function : ""));
  if (!NAMES.has(name)) return null;
  let args = fn.arguments != null ? fn.arguments : fn.parameters != null ? fn.parameters : fn.args != null ? fn.args : fn.input;
  if (typeof args === "string") args = tryJson(args) || { path: args };
  if (!args || typeof args !== "object") args = {};
  return { name, args };
}

function parseTextCalls(text) {
  const src = String(text || "");
  const calls = [];
  const seen = new Set();
  const push = (c) => {
    if (!c) return;
    const k = c.name + JSON.stringify(c.args);
    if (seen.has(k)) return;
    seen.add(k);
    calls.push(c);
  };
  for (const m of src.matchAll(/<tool_call>\s*([\s\S]*?)\s*<\/tool_call>/gi)) {
    for (const span of jsonObjects(m[1])) push(asCall(tryJson(span)));
  }
  if (calls.length) return calls;
  for (const m of src.matchAll(/```(?:json|tool_call|tool)?\s*([\s\S]*?)```/gi)) {
    const obj = tryJson(m[1]);
    if (Array.isArray(obj)) obj.forEach((o) => push(asCall(o)));
    else if (obj) push(asCall(obj));
  }
  if (calls.length) return calls;
  for (const span of jsonObjects(src)) {
    if (/"(name|tool|function)"\s*:/.test(span)) push(asCall(tryJson(span)));
  }
  return calls;
}

/** Strip the call markup so only the model's narration is shown. */
function narration(text) {
  let s = String(text || "")
    .replace(/<tool_call>[\s\S]*?<\/tool_call>/gi, "")
    .replace(/```(?:json|tool_call|tool)?\s*\{[\s\S]*?"(?:name|tool)"[\s\S]*?```/gi, "");
  for (const span of jsonObjects(s)) {
    if (/"(name|tool)"\s*:/.test(span) && asCall(tryJson(span))) s = s.replace(span, "");
  }
  return s.replace(/<\/?think>/gi, "").trim();
}

const TUTOR = [
  /\bi (?:don't|do not|can't|cannot|am unable to) (?:have the (?:ability|capability)|directly|access|run|execute|open|operate)/i,
  /\bas an ai\b/i,
  /\bhere(?:'s| is) (?:a )?(?:brief |step-by-step )?guide\b/i,
  /\byou(?:'ll| will)? (?:need to|can|should) (?:open|run|navigate|click|create)\b/i,
  /\bwould you like (?:me )?to\b/i,
  /\bshall i\b/i,
  /\b(?:could|can) you (?:please )?(?:provide|specify|confirm|share|verify)\b/i,
  /\blet me know if\b/i,
  /\bplease provide (?:more )?details\b/i,
];

function isTutor(text) {
  const t = String(text || "");
  return t.trim() !== "" && TUTOR.some((re) => re.test(t));
}

/** "I will fix this…", "Let me read…", "Next, I'll run…" — intent stated instead of acted on. */
function announcesAction(text) {
  return /\b(i will|i'll|i am going to|i'm going to|let me|let's|let us|next,? i|now,? i|first,? i|i need to|i should|we need to|we will|we'll)\b/i.test(
    String(text || "")
  );
}

function wantsEdit(text) {
  return /\b(fix|implement|add|create|write|edit|update|change|refactor|rename|remove|delete|patch|port|migrate|replace|convert)\b/i.test(String(text || ""));
}

function wantsVerify(text) {
  return /\b(run|test|tests|build|compile|verify|check that|make sure)\b/i.test(String(text || ""));
}

function looksLikeWork(text) {
  return /\b(fix|implement|add|create|write|edit|update|change|refactor|rename|remove|delete|build|compile|run|test|find|search|read|open|look|check|investigate|debug|port|migrate|install|continue|make|generate)\b/i.test(
    String(text || "")
  );
}

module.exports = { parseTextCalls, narration, isTutor, looksLikeWork, announcesAction, wantsEdit, wantsVerify, jsonObjects };
