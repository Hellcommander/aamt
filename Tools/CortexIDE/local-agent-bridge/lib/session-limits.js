"use strict";

// Per-chat output limits. Every chat carries a `limits` choice in its session (and in the folder's
// main index), so one chat can be raised for complex work — long files, many tool rounds, more
// thinking — while the chats beside it stay on the cheap defaults from settings.
//
//   { preset: "standard" }                      the settings (maxOutputTokens / claudeMaxOutputTokens,
//                                               maxRounds, claudeEffort); also what a missing value means
//   { preset: "extended" } / { preset: "max" }  raise those values; a preset never lowers a setting
//   { preset: "custom", maxOutputTokens, maxRounds, effort }   exact values (0 / "" = the setting)
//
// The result is capped to what the model allows: Claude to the model's own max_tokens, local models
// to half their context window (the prompt needs the other half). Plain node, so it is testable.

const PRESETS = {
  standard: { label: "Standard", detail: "the localAgentBridge.agent settings" },
  extended: { label: "Extended", detail: "longer replies, more rounds", local: 8192, claude: 32000, rounds: 80, effort: "high" },
  max: { label: "Maximum", detail: "long agentic work; costs more and holds more VRAM", local: 16384, claude: 64000, rounds: 150, effort: "xhigh" },
  custom: { label: "Custom", detail: "your own numbers for this chat" },
};
const EFFORTS = ["default", "low", "medium", "high", "xhigh", "max"];
// "default" is the model's own choice, about medium-to-high: a preset only raises effort above it.
const EFFORT_RANK = { low: 1, medium: 2, default: 2.5, high: 3, xhigh: 4, max: 5 };
const MIN_OUTPUT = 256;
const MAX_ROUNDS = 1000;

/** A chat's stored limits, cleaned up (unknown preset → standard). */
function normalize(limits) {
  const l = limits && typeof limits === "object" ? limits : {};
  const preset = PRESETS[l.preset] ? l.preset : "standard";
  if (preset !== "custom") return { preset };
  const int = (v, hi) => Math.max(0, Math.min(hi, Math.floor(Number(v) || 0)));
  return {
    preset,
    maxOutputTokens: int(l.maxOutputTokens, 1000000),
    maxRounds: int(l.maxRounds, MAX_ROUNDS),
    effort: EFFORTS.includes(l.effort) ? l.effort : "",
  };
}

function isStandard(limits) {
  return normalize(limits).preset === "standard";
}

/**
 * The limits one turn of a chat runs with.
 * @param {object} o
 * @param {object} [o.limits] the chat's stored choice
 * @param {string} o.provider backend provider: anthropic, claude-code, vllm, ollama, openai, …
 * @param {(key:string, def:any)=>any} o.get reads localAgentBridge.agent.<key>
 * @param {number} [o.modelMaxOut] the model's own output cap (Claude's max_tokens), 0 = unknown
 * @param {number} [o.ctxTokens] the context window planned for, 0 = unknown
 * @returns {{preset:string, label:string, provider:string, maxOutputTokens:number, maxRounds:number, effort:string, effortFrom:string, notes:string[]}}
 *   effortFrom: "setting" (claudeEffort), "preset" (raised by Extended / Maximum) or "custom" (this chat's own)
 */
function resolve({ limits, provider, get, modelMaxOut = 0, ctxTokens = 0 }) {
  const l = normalize(limits);
  const p = PRESETS[l.preset];
  const claude = provider === "anthropic" || provider === "claude-code";
  const notes = [];
  const baseOut = claude ? Number(get("claudeMaxOutputTokens", 16000)) || 16000 : Number(get("maxOutputTokens", 2048)) || 2048;
  const baseRounds = Number(get("maxRounds", 30)) || 30;
  const baseEffort = claude ? String(get("claudeEffort", "default") || "default") : "";
  let out = baseOut;
  let rounds = baseRounds;
  let effort = baseEffort;
  let effortFrom = "setting";
  if (l.preset === "custom") {
    if (l.maxOutputTokens) out = l.maxOutputTokens;
    if (l.maxRounds) rounds = l.maxRounds;
    if (claude && l.effort && l.effort !== baseEffort) {
      effort = l.effort;
      effortFrom = "custom";
    }
  } else if (l.preset !== "standard") {
    out = Math.max(baseOut, claude ? p.claude : p.local);
    rounds = Math.max(baseRounds, p.rounds);
    if (claude && (EFFORT_RANK[p.effort] || 0) > (EFFORT_RANK[baseEffort] || 0)) {
      effort = p.effort;
      effortFrom = "preset";
    }
  }
  if (claude && modelMaxOut > 0 && out > modelMaxOut) {
    notes.push("output capped at the model's limit of " + modelMaxOut + " tokens");
    out = modelMaxOut;
  }
  if (!claude && ctxTokens > 0 && out > Math.floor(ctxTokens / 2)) {
    const cap = Math.max(MIN_OUTPUT, Math.floor(ctxTokens / 2));
    notes.push("output capped at " + cap + " tokens, half the " + Math.round(ctxTokens / 1024) + "k context (raise contextTokens / ollamaNumCtx for more)");
    out = cap;
  }
  out = Math.max(MIN_OUTPUT, Math.floor(out));
  rounds = Math.max(1, Math.min(MAX_ROUNDS, Math.floor(rounds)));
  if (provider === "claude-code" && rounds !== baseRounds) notes.push("Claude Code runs its own tool loop: rounds do not apply");
  return { preset: l.preset, label: p.label, provider, maxOutputTokens: out, maxRounds: rounds, effort, effortFrom: claude ? effortFrom : "", notes };
}

/** Short text for the composer chip: "" for standard, else e.g. "Extended · 32k out · 80 rounds". */
function chipText(limits, r) {
  if (isStandard(limits)) return "";
  if (!r) return PRESETS[normalize(limits).preset].label; // no backend yet: the numbers are unknown
  const k = r.maxOutputTokens >= 1000 ? Math.round(r.maxOutputTokens / 1000) + "k" : String(r.maxOutputTokens);
  return r.label + " · " + k + " out" + (r.provider === "claude-code" ? "" : " · " + r.maxRounds + " rounds");
}

module.exports = { PRESETS, EFFORTS, normalize, isStandard, resolve, chipText };
