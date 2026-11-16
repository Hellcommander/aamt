"use strict";

// Permission rules for agent tool calls.
// Design follows opencode's permissions (https://github.com/anomalyco/opencode, MIT,
// Copyright (c) 2025 opencode): an ordered list of { action, resource, effect } rules where the
// LAST matching rule wins; `*` / `?` wildcards over the whole value; a shell pattern ending in " *"
// also matches the bare command; a call that checks several resources is denied if any is denied,
// else asked if any is asked; "Allow always" saves an allow rule that never overrides a deny.
// Written from the documented behaviour; no opencode source is copied.

const path = require("path");

const EFFECTS = new Set(["allow", "ask", "deny"]);

/** Tool → permission action. Tools not listed (TodoWrite, ReadLints, list_skills, McpTools, attempt_completion) are always allowed. */
const TOOL_ACTION = {
  Read: "read",
  ReadImage: "read",
  AnalyzeFile: "read",
  LS: "read",
  Glob: "glob",
  Grep: "grep",
  Shell: "shell",
  StrReplace: "edit",
  MultiEdit: "edit",
  Write: "edit",
  Delete: "edit",
  WebFetch: "webfetch",
  Task: "subagent",
  McpCall: "mcp",
  read_skill: "skill",
};

/** Accepted spellings of actions (opencode V1 names, tool names). */
const ACTION_ALIAS = { bash: "shell", powershell: "shell", task: "subagent", write: "edit", patch: "edit", list: "read", ls: "read", fetch: "webfetch" };

/**
 * Asked before reading secrets, as in opencode's default policy. Configured rules come after
 * these, so `{ "action": "read", "resource": "*.env", "effect": "allow" }` turns the prompt off.
 */
const DEFAULT_RULES = [
  { action: "read", resource: "*.env", effect: "ask" },
  { action: "read", resource: "*.env.*", effect: "ask" },
  { action: "read", resource: "*.env.example", effect: "allow" },
  { action: "read", resource: "*.env.sample", effect: "allow" },
];

const reCache = new Map();
function wildcard(pattern) {
  const key = String(pattern);
  let re = reCache.get(key);
  if (!re) {
    const src = key.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, "[\\s\\S]*").replace(/\?/g, "[\\s\\S]");
    re = new RegExp("^" + src + "$", "i");
    reCache.set(key, re);
  }
  return re;
}

function canonAction(a) {
  const s = String(a == null ? "" : a).trim().toLowerCase();
  return ACTION_ALIAS[s] || s;
}

/**
 * Normalize rules from settings or agent files. Accepts the V2 list form
 * [{action, resource, effect}] and opencode's V1 map form { edit: "deny", bash: { "git *": "allow" } }.
 */
function normalize(rules) {
  const out = [];
  const add = (action, resource, effect) => {
    const e = String(effect || "").trim().toLowerCase();
    if (!EFFECTS.has(e)) return;
    out.push({ action: canonAction(action || "*"), resource: String(resource == null || resource === "" ? "*" : resource), effect: e });
  };
  if (Array.isArray(rules)) {
    for (const r of rules) {
      if (r && typeof r === "object") add(r.action || r.permission || r.tool, r.resource != null ? r.resource : r.pattern, r.effect || r.decision);
      else if (typeof r === "string") {
        // "shell:git push *=deny"
        const m = /^\s*([^:=]+?)(?::(.*?))?\s*=\s*(allow|ask|deny)\s*$/i.exec(r);
        if (m) add(m[1], m[2] == null ? "*" : m[2], m[3]);
      }
    }
  } else if (rules && typeof rules === "object") {
    for (const [action, v] of Object.entries(rules)) {
      if (typeof v === "string") add(action, "*", v);
      else if (v && typeof v === "object") for (const [res, eff] of Object.entries(v)) add(action, res, eff);
    }
  }
  return out;
}

function slash(p) {
  return String(p || "").replace(/\\/g, "/");
}

/** The forms a path resource is matched in: absolute, and relative to each workspace folder. */
function pathForms(abs, roots) {
  const forms = [slash(abs)];
  for (const r of roots || []) {
    const rel = path.relative(r, abs);
    if (rel && !rel.startsWith("..") && !path.isAbsolute(rel)) forms.push(slash(rel));
    else if (!rel) forms.push(".");
  }
  return forms;
}

function expandHome(p) {
  const home = process.env.USERPROFILE || process.env.HOME || "";
  return String(p).replace(/^(~|\$HOME)(?=$|[\\/])/, home.replace(/\\/g, "/"));
}

/** Does one rule's resource pattern match the value (in any of its forms)? */
function resourceMatch(rule, action, forms) {
  const pat = action === "shell" ? rule.resource : slash(expandHome(rule.resource));
  const re = wildcard(pat);
  for (const f of forms) {
    if (re.test(f)) return true;
    // "git status *" also matches a bare "git status"
    if (action === "shell" && / \*$/.test(pat) && wildcard(pat.slice(0, -2)).test(f)) return true;
  }
  return false;
}

/** The effect of the last matching rule for one resource, or null when none matches. */
function decide(rules, action, forms) {
  let effect = null;
  let rule = null;
  for (const r of rules) {
    if (!wildcard(r.action).test(action)) continue;
    if (!resourceMatch(r, action, forms)) continue;
    effect = r.effect;
    rule = r;
  }
  return { effect, rule };
}

/**
 * Split a shell command into the commands it runs (&&, ||, ;, |, newlines), outside quotes.
 * Leading PowerShell call operators ("& ") and env assignments are dropped so "git push" is seen as such.
 */
function splitShell(cmd) {
  const parts = [];
  let cur = "";
  let q = "";
  const s = String(cmd || "");
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    if (q) {
      cur += ch;
      if (ch === q) q = "";
      continue;
    }
    if (ch === '"' || ch === "'") {
      q = ch;
      cur += ch;
      continue;
    }
    const two = s.slice(i, i + 2);
    if (two === "&&" || two === "||") {
      parts.push(cur);
      cur = "";
      i++;
      continue;
    }
    if (ch === ";" || ch === "|" || ch === "\n" || ch === "\r") {
      parts.push(cur);
      cur = "";
      continue;
    }
    cur += ch;
  }
  parts.push(cur);
  return parts
    .map((p) => p.trim().replace(/^&\s+/, "").replace(/^(?:\$env:\w+\s*=\s*\S+\s*;?\s*)+/i, "").replace(/^(?:\w+=\S+\s+)+/, "").trim())
    .filter(Boolean);
}

/** The pattern "Allow always" saves for a shell command: its first two words, then " *" ("git status *"). */
function shellPrefix(cmd) {
  const words = String(cmd).trim().split(/\s+/);
  const keep = words.length > 1 && !/^[-/]/.test(words[1]) && !/[\\/.:"']/.test(words[1]) ? 2 : 1;
  return words.slice(0, keep).join(" ") + " *";
}

/**
 * What a tool call asks permission for.
 * @returns {{action:string, resources:{value:string, forms:string[]}[], suggest:string[]}|null} null = not subject to rules
 */
function requestFor(tool, args, { roots = [], resolve } = {}) {
  const action = TOOL_ACTION[tool];
  if (!action) return null;
  const a = args || {};
  const abs = (p) => (resolve ? resolve(p) : path.resolve(String(p)));
  if (action === "read" || action === "edit") {
    const p = a.path || a.file_path || a.target_file;
    if (!p) return null;
    if (/^https?:\/\//i.test(String(p))) return { action: "webfetch", resources: [{ value: String(p), forms: [String(p)] }], suggest: [String(p)] };
    const file = abs(p);
    const forms = pathForms(file, roots);
    const rel = forms.length > 1 ? forms[1] : forms[0];
    const dir = rel.includes("/") ? rel.slice(0, rel.lastIndexOf("/")) + "/*" : "*";
    return { action, resources: [{ value: slash(file), forms }], suggest: [dir] };
  }
  if (action === "shell") {
    const cmds = splitShell(a.command);
    if (!cmds.length) return null;
    return { action, resources: cmds.map((c) => ({ value: c, forms: [c] })), suggest: [...new Set(cmds.map(shellPrefix))] };
  }
  if (action === "mcp") {
    const id = String(a.server || "").replace(/[^\w-]/g, "_") + "_" + String(a.tool || a.name || "").replace(/[^\w-]/g, "_");
    return { action, resources: [{ value: id, forms: [id] }], suggest: [id] };
  }
  const v = String((action === "glob" || action === "grep" ? a.pattern : action === "webfetch" ? a.url : action === "subagent" ? a.agent || a.subagent_type || "explore" : a.name) || "");
  return { action, resources: [{ value: v, forms: [v] }], suggest: [action === "glob" || action === "grep" ? "*" : v] };
}

/**
 * Evaluate a tool call against ordered rules.
 * @param {object[]} rules normalized rules (defaults + settings + agent), in order
 * @param {object[]} [approved] rules saved by "Allow always" — they turn an ask into allow, never a deny
 * @param {string} [fallback] effect when no rule matches (default "allow")
 * @returns {{effect:"allow"|"ask"|"deny", action?:string, resources?:string[], rule?:object, suggest?:string[]}}
 */
function evaluate(rules, tool, args, { roots, resolve, approved = [], fallback = "allow" } = {}) {
  const req = requestFor(tool, args, { roots, resolve });
  if (!req) return { effect: "allow" };
  let worst = "allow";
  let why = null;
  const asked = [];
  for (const res of req.resources) {
    let { effect, rule } = decide(rules, req.action, res.forms);
    if (!effect) effect = fallback;
    if (effect === "ask" && approved.length && decide(approved, req.action, res.forms).effect === "allow") effect = "allow";
    if (effect === "deny") {
      worst = "deny";
      why = rule;
      break;
    }
    if (effect === "ask") {
      worst = "ask";
      why = why || rule;
      asked.push(res.value);
    }
  }
  return { effect: worst, action: req.action, resources: req.resources.map((r) => r.value), asked, rule: why, suggest: req.suggest };
}

function describeRule(r) {
  return r ? r.action + " " + JSON.stringify(r.resource) + " → " + r.effect : "default";
}

module.exports = { DEFAULT_RULES, TOOL_ACTION, normalize, evaluate, requestFor, splitShell, shellPrefix, wildcard, describeRule, canonAction };
