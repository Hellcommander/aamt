"use strict";

// Per-chat output limits (lib/session-limits.js): presets raise the settings and never lower them,
// custom values are exact, and the result is capped to the model (Claude) or the context (local).

const path = require("path");
const assert = require("assert");
const { test, EXT } = require("./harness");
const L = require(path.join(EXT, "lib", "session-limits"));

const settings = (o = {}) => (k, d) => (k in o ? o[k] : d);

test("normalize: unknown or missing → standard; custom values are cleaned", () => {
  assert.deepStrictEqual(L.normalize(undefined), { preset: "standard" });
  assert.deepStrictEqual(L.normalize({ preset: "huge" }), { preset: "standard" });
  assert.deepStrictEqual(L.normalize({ preset: "max", maxRounds: 9 }), { preset: "max" });
  assert.deepStrictEqual(L.normalize({ preset: "custom", maxOutputTokens: "12000.7", maxRounds: -3, effort: "loud" }), { preset: "custom", maxOutputTokens: 12000, maxRounds: 0, effort: "" });
  assert.ok(L.isStandard(null) && !L.isStandard({ preset: "extended" }));
});

test("standard follows the settings, per backend", () => {
  const get = settings({ maxOutputTokens: 3000, claudeMaxOutputTokens: 20000, maxRounds: 40, claudeEffort: "medium" });
  const local = L.resolve({ limits: null, provider: "vllm", get, ctxTokens: 32768 });
  assert.deepStrictEqual([local.maxOutputTokens, local.maxRounds, local.effort, local.notes.length], [3000, 40, "", 0]);
  const claude = L.resolve({ limits: { preset: "standard" }, provider: "anthropic", get });
  assert.deepStrictEqual([claude.maxOutputTokens, claude.maxRounds, claude.effort], [20000, 40, "medium"]);
});

test("presets raise, never lower, the settings", () => {
  const ext = L.resolve({ limits: { preset: "extended" }, provider: "anthropic", get: settings() });
  assert.deepStrictEqual([ext.maxOutputTokens, ext.maxRounds, ext.effort, ext.label], [32000, 80, "high", "Extended"]);
  // Settings already above the preset stay.
  const big = L.resolve({ limits: { preset: "extended" }, provider: "anthropic", get: settings({ claudeMaxOutputTokens: 50000, maxRounds: 200, claudeEffort: "max" }) });
  assert.deepStrictEqual([big.maxOutputTokens, big.maxRounds, big.effort], [50000, 200, "max"]);
  // "default" effort counts as about medium-high: extended raises it to high.
  const local = L.resolve({ limits: { preset: "max" }, provider: "ollama", get: settings(), ctxTokens: 65536 });
  assert.deepStrictEqual([local.maxOutputTokens, local.maxRounds, local.effort], [16384, 150, ""]);
});

test("custom is exact, and 0 / empty means the setting", () => {
  const get = settings({ maxOutputTokens: 2048, maxRounds: 30, claudeEffort: "high" });
  const lower = L.resolve({ limits: { preset: "custom", maxOutputTokens: 1024, maxRounds: 10 }, provider: "vllm", get, ctxTokens: 32768 });
  assert.deepStrictEqual([lower.maxOutputTokens, lower.maxRounds], [1024, 10]);
  const keep = L.resolve({ limits: { preset: "custom", maxOutputTokens: 0, maxRounds: 0, effort: "" }, provider: "anthropic", get });
  assert.deepStrictEqual([keep.maxOutputTokens, keep.maxRounds, keep.effort], [16000, 30, "high"]);
  const eff = L.resolve({ limits: { preset: "custom", effort: "low" }, provider: "anthropic", get });
  assert.strictEqual(eff.effort, "low");
});

test("capped to the Claude model's max_tokens and to half a local context", () => {
  const claude = L.resolve({ limits: { preset: "max" }, provider: "anthropic", get: settings(), modelMaxOut: 32000 });
  assert.strictEqual(claude.maxOutputTokens, 32000);
  assert.match(claude.notes.join(), /model's limit of 32000/);
  const local = L.resolve({ limits: { preset: "max" }, provider: "vllm", get: settings(), ctxTokens: 16384 });
  assert.strictEqual(local.maxOutputTokens, 8192);
  assert.match(local.notes.join(), /half the 16k context/);
  const tiny = L.resolve({ limits: { preset: "custom", maxOutputTokens: 5 }, provider: "vllm", get: settings(), ctxTokens: 100 });
  assert.strictEqual(tiny.maxOutputTokens, 256, "never below the floor");
});

test("Claude Code: rounds do not apply; chip text", () => {
  const cc = L.resolve({ limits: { preset: "extended" }, provider: "claude-code", get: settings() });
  assert.match(cc.notes.join(), /Claude Code runs its own tool loop/);
  assert.strictEqual(L.chipText({ preset: "extended" }, cc), "Extended · 32k out");
  const v = L.resolve({ limits: { preset: "extended" }, provider: "vllm", get: settings(), ctxTokens: 65536 });
  assert.strictEqual(L.chipText({ preset: "extended" }, v), "Extended · 8k out · 80 rounds");
  assert.strictEqual(L.chipText({ preset: "standard" }, v), "");
  assert.strictEqual(L.chipText({ preset: "max" }, null), "Maximum");
});

test("claude-code buildEnv passes a raised output cap on", () => {
  const cc = require(path.join(EXT, "lib", "claude-code"));
  assert.strictEqual(cc.buildEnv({ base: {}, maxOutputTokens: 32000 }).CLAUDE_CODE_MAX_OUTPUT_TOKENS, "32000");
  assert.strictEqual(cc.buildEnv({ base: {} }).CLAUDE_CODE_MAX_OUTPUT_TOKENS, undefined);
});
