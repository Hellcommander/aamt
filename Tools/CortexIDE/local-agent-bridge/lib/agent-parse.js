"use strict";

// Recover tool calls that small local models emit as text instead of native tool_calls:
//   <tool_call>{"name": ..., "arguments": {...}}</tool_call>   (Qwen / Hermes template)
//   <function=Read><parameter=path>a.js</parameter></function> (Qwen3-Coder XML template)
//   <function=Read>{"path": "a.js"}</function>                 (Llama 3.x custom tool format)
//   [TOOL_CALLS] [{"name": ..., "arguments": {...}}]           (Mistral)
//   <|python_tag|>{"name": ..., "parameters": {...}}           (Llama 3.1)
//   ```json {"name": ..., "arguments": {...}} ```             (fenced)
//   {"name": "Read", "arguments": {...}}                      (bare JSON — Ollama qwen2.5-coder)
// JSON is parsed leniently: raw newlines / tabs inside strings (code in "contents"), trailing
// commas, and a final call cut off by the output limit are repaired.
// <think>…</think> reasoning is removed first, so calls a model only considered are not run.

const { canonName, NAMES } = require("./agent-tools");

/** Escape raw control characters inside JSON strings and drop trailing commas. */
function repairJson(s) {
  let out = "";
  let inStr = false;
  let esc = false;
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (inStr) {
      if (esc) {
        esc = false;
        // Models copying code write \' or regex escapes like \d, which JSON rejects.
        if ('"\\/bfnrtu'.includes(c)) out += "\\" + c;
        else if (c === "'") out += "'";
        else out += "\\\\" + c;
        continue;
      }
      if (c === "\\") {
        esc = true;
        continue;
      }
      if (c === '"') inStr = false;
      if (c === "\n") out += "\\n";
      else if (c === "\r") out += "\\r";
      else if (c === "\t") out += "\\t";
      else if (c < " ") out += "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0");
      else out += c;
      continue;
    }
    if (c === '"') inStr = true;
    out += c;
  }
  if (esc) out += "\\\\";
  return out.replace(/,(\s*[}\]])/g, "$1");
}

/** Close a JSON value cut off mid-way (string, objects, arrays). "" when it cannot be closed. */
function closeJson(s) {
  const stack = [];
  let inStr = false;
  let esc = false;
  for (const c of s) {
    if (inStr) {
      if (esc) esc = false;
      else if (c === "\\") esc = true;
      else if (c === '"') inStr = false;
      continue;
    }
    if (c === '"') inStr = true;
    else if (c === "{") stack.push("}");
    else if (c === "[") stack.push("]");
    else if (c === "}" || c === "]") stack.pop();
  }
  if (!stack.length && !inStr) return "";
  return s.replace(/\\$/, "") + (inStr ? '"' : "") + stack.reverse().join("");
}

function tryJson(raw) {
  const s = String(raw || "").trim().replace(/^```(?:json)?/i, "").replace(/```$/, "").trim();
  if (!s) return null;
  for (const cand of [s, repairJson(s)]) {
    try {
      return JSON.parse(cand);
    } catch {
      /* next */
    }
  }
  return null;
}

/** Every balanced top-level {...} span in text (string-aware). With `tail`, also an unclosed final span. */
function jsonObjects(text, tail = false) {
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
  if (tail && depth > 0 && start >= 0) out.push(s.slice(start));
  return out;
}

function asCall(obj) {
  if (!obj || typeof obj !== "object" || Array.isArray(obj)) return null;
  const fn = obj.function && typeof obj.function === "object" ? obj.function : obj;
  const name = canonName(fn.name || fn.tool || fn.tool_name || fn.action || (typeof obj.function === "string" ? obj.function : ""));
  if (!NAMES.has(name)) return null;
  let args = fn.arguments != null ? fn.arguments : fn.parameters != null ? fn.parameters : fn.args != null ? fn.args : fn.input != null ? fn.input : fn.action_input;
  if (typeof args === "string") args = tryJson(args) || { path: args };
  if (args == null) {
    // Flat form: {"name": "Read", "path": "a.js"}
    args = {};
    for (const [k, v] of Object.entries(fn)) if (!["name", "tool", "tool_name", "action", "type", "id", "function"].includes(k)) args[k] = v;
  }
  if (!args || typeof args !== "object" || Array.isArray(args)) args = {};
  return { name, args };
}

/** `<parameter=path>a.js</parameter>` pairs (Qwen3-Coder) → object; JSON-looking values are parsed. */
function xmlParams(body) {
  const args = {};
  for (const m of String(body).matchAll(/<parameter=([\w.-]+)>\n?([\s\S]*?)\n?<\/parameter>/g)) {
    const v = m[2];
    const t = v.trim();
    if (/^(\{|\[)/.test(t) || /^(true|false|null|-?\d+(\.\d+)?)$/.test(t)) {
      const parsed = tryJson(t);
      args[m[1]] = parsed !== null || t === "null" ? parsed : v;
    } else args[m[1]] = v;
  }
  return args;
}

/** Remove reasoning: <think>…</think>, an unclosed leading <think>, or text before a stray </think>. */
function stripThinking(text) {
  let s = String(text || "").replace(/<(think|thinking|reasoning)>[\s\S]*?<\/\1>/gi, "");
  // Template opened <think> itself, so only the closing tag is in the output.
  const close = s.search(/<\/(think|thinking|reasoning)>/i);
  if (close >= 0) s = s.slice(close).replace(/^<\/(think|thinking|reasoning)>/i, "");
  // Cut off while still thinking: nothing after it is an answer.
  s = s.replace(/<(think|thinking|reasoning)>[\s\S]*$/i, "");
  return s;
}

function parseTextCalls(text) {
  const src = stripThinking(text);
  const calls = [];
  const seen = new Set();
  const push = (c) => {
    if (!c) return;
    const k = c.name + JSON.stringify(c.args);
    if (seen.has(k)) return;
    seen.add(k);
    calls.push(c);
  };
  const fromSpan = (span) => {
    const obj = tryJson(span) || tryJson(closeJson(span));
    if (Array.isArray(obj)) obj.forEach((o) => push(asCall(o)));
    else push(asCall(obj));
  };

  for (const m of src.matchAll(/<tool_call>\s*([\s\S]*?)\s*(?:<\/tool_call>|$)/gi)) {
    const body = m[1];
    const fn = body.match(/^<function=([\w.-]+)>([\s\S]*?)(?:<\/function>|$)/);
    if (fn) {
      const name = canonName(fn[1]);
      if (NAMES.has(name)) push({ name, args: /<parameter=/.test(fn[2]) ? xmlParams(fn[2]) : tryJson(fn[2]) || {} });
      continue;
    }
    const spans = jsonObjects(body, true);
    spans.forEach(fromSpan);
  }
  if (calls.length) return calls;

  for (const m of src.matchAll(/<function=([\w.-]+)>([\s\S]*?)(?:<\/function>|$)/g)) {
    const name = canonName(m[1]);
    if (NAMES.has(name)) push({ name, args: /<parameter=/.test(m[2]) ? xmlParams(m[2]) : tryJson(m[2]) || tryJson(closeJson(m[2].trim())) || {} });
  }
  if (calls.length) return calls;

  const tagged = src.match(/(?:\[TOOL_CALLS\]|<\|python_tag\|>)\s*([\s\S]*)$/);
  if (tagged) {
    const t = tagged[1].trim();
    const arr = t.startsWith("[") ? tryJson(t) || tryJson(closeJson(t)) : null;
    if (Array.isArray(arr)) arr.forEach((o) => push(asCall(o)));
    else jsonObjects(t, true).forEach(fromSpan);
  }
  if (calls.length) return calls;

  for (const m of src.matchAll(/```(?:json|tool_call|tool)?\s*([\s\S]*?)```/gi)) {
    if (/"(name|tool|function)"\s*:/.test(m[1])) fromSpan(m[1].trim());
  }
  if (calls.length) return calls;

  for (const span of jsonObjects(src, true)) {
    if (/"(name|tool|function)"\s*:/.test(span)) fromSpan(span);
  }
  return calls;
}

/** Strip reasoning and call markup so only the model's narration is shown. */
function narration(text) {
  let s = stripThinking(text)
    .replace(/<tool_call>[\s\S]*?(<\/tool_call>|$)/gi, "")
    .replace(/<function=[\w.-]+>[\s\S]*?(<\/function>|$)/g, "")
    .replace(/(\[TOOL_CALLS\]|<\|python_tag\|>)[\s\S]*$/, "")
    .replace(/```(?:json|tool_call|tool)?\s*\{[\s\S]*?"(?:name|tool)"[\s\S]*?```/gi, "");
  for (const span of jsonObjects(s, true)) {
    if (/"(name|tool)"\s*:/.test(span) && asCall(tryJson(span) || tryJson(closeJson(span)))) s = s.replace(span, "");
  }
  return s.trim();
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

module.exports = { parseTextCalls, narration, stripThinking, isTutor, looksLikeWork, announcesAction, wantsEdit, wantsVerify, jsonObjects, repairJson, closeJson };
