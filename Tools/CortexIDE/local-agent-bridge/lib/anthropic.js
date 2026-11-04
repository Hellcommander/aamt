"use strict";

// Claude backend: the Anthropic Messages API, the same API Claude Code and claude.ai are built on.
// The extension ships without node_modules (vsce --no-dependencies), so this is a thin raw
// HTTPS client rather than @anthropic-ai/sdk; request shapes follow platform.claude.com/docs
// (anthropic-version 2026-10-21).
//
// What the agent loop gets:
// - the OpenAI-shaped messages / tool_calls it already uses, converted both ways
// - streaming (SSE), so a long Claude turn never hits an HTTP timeout
// - prompt caching: a breakpoint on the system prompt plus top-level automatic caching
// - adaptive thinking on models that take it; the thinking blocks are replayed while the
//   history is append-only and dropped once compaction has rewritten it ("preserved thinking")
// - credentials from Secret Storage, ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN or `ant auth login`

const { spawnSync } = require("child_process");
const { request, errText } = require("./http");

const API_VERSION = "2026-10-21";
const DEFAULT_URL = "https://api.anthropic.com";
const OAUTH_BETA = "oauth-2025-04-20";
const PREFERRED = ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5", "claude-opus-4-8", "claude-sonnet-4-6"];
const EFFORTS = ["low", "medium", "high", "xhigh", "max"];
/** Planning window when contextTokens is 0. Claude models take up to 1M tokens, but every round
 *  resends the whole conversation, so compaction should start well before that. */
const DEFAULT_CTX = 200000;
const RETRIES = 3;

/** The API refused a replayed `thinking` block because the history before it changed. */
class ThinkingMismatch extends Error {}

function root(baseUrl) {
  return String(baseUrl || DEFAULT_URL).trim().replace(/\/+$/, "").replace(/\/v1$/, "");
}

/** Models that take `thinking: {type: "adaptive"}` and `output_config.effort`: the 4.6+ and 5.x families. */
function supportsAdaptive(model) {
  const m = String(model || "");
  if (/^claude-(fable|mythos)-/.test(m)) return true;
  const v = m.match(/^claude-(?:opus|sonnet|haiku)-(\d+)(?:-(\d{1,2}))?(?:-\d{8})?$/);
  if (!v) return false;
  const major = Number(v[1]);
  const minor = v[2] ? Number(v[2]) : 0;
  return major >= 5 || (major === 4 && minor >= 6);
}

/**
 * How to authenticate, first match wins:
 * 1. a key saved with "Agent: Set Claude API Key" (Secret Storage), or localAgentBridge.agent.apiKey
 * 2. ANTHROPIC_API_KEY
 * 3. ANTHROPIC_AUTH_TOKEN (OAuth bearer token)
 * 4. the profile from `ant auth login` (Anthropic CLI), via `ant auth print-credentials --access-token`
 * A user-scoped key (sk-ant-usr-...) also needs a workspace: localAgentBridge.agent.claudeWorkspaceId or
 * ANTHROPIC_WORKSPACE_ID, sent as the anthropic-workspace-id header.
 * @returns {{kind:"api_key"|"bearer", token:string, source:string, workspaceId:string}|null}
 */
function credentials({ apiKey = "", workspaceId = "", env = process.env, useCli = true } = {}) {
  const ws = cleanKey(workspaceId) || cleanKey(env.ANTHROPIC_WORKSPACE_ID);
  const done = (c) => (c ? { ...c, workspaceId: ws } : null);
  const key = cleanKey(apiKey);
  if (key) return done({ kind: /^sk-ant-oat/i.test(key) ? "bearer" : "api_key", token: key, source: "saved key" });
  const envKey = cleanKey(env.ANTHROPIC_API_KEY);
  if (envKey) return done({ kind: "api_key", token: envKey, source: "ANTHROPIC_API_KEY" });
  const envTok = cleanKey(env.ANTHROPIC_AUTH_TOKEN);
  if (envTok) return done({ kind: "bearer", token: envTok, source: "ANTHROPIC_AUTH_TOKEN" });
  if (useCli) {
    const t = cliToken();
    if (t) return done({ kind: "bearer", token: t, source: "ant auth login" });
  }
  return null;
}

/** A pasted key, minus whitespace and the quotes / angle brackets people copy along with it. */
function cleanKey(v) {
  let k = String(v == null ? "" : v).trim();
  for (let i = 0; i < 3; i++) {
    const m = k.match(/^(?:<(.*)>|"(.*)"|'(.*)'|`(.*)`)$/s);
    if (!m) break;
    k = (m[1] ?? m[2] ?? m[3] ?? m[4] ?? "").trim();
  }
  return k;
}

function cliToken() {
  try {
    const r = spawnSync("ant", ["auth", "print-credentials", "--access-token"], { encoding: "utf8", timeout: 10000, windowsHide: true });
    if (r.status !== 0) return "";
    const t = String(r.stdout || "").trim();
    return /^[\w.~+/=-]{20,}$/.test(t) ? t : "";
  } catch {
    return "";
  }
}

function headers(cred, betas) {
  const h = { "anthropic-version": API_VERSION };
  const b = [...(betas || [])];
  if (cred.kind === "bearer") {
    h.Authorization = "Bearer " + cred.token;
    b.push(OAUTH_BETA);
  } else h["x-api-key"] = cred.token;
  if (cred.workspaceId) h["anthropic-workspace-id"] = cred.workspaceId;
  if (b.length) h["anthropic-beta"] = b.join(",");
  return h;
}

/** GET /v1/models (paginated). ctx is the model's context window (max_input_tokens). */
async function listModels(baseUrl, cred) {
  const out = [];
  let after = "";
  for (let page = 0; page < 10; page++) {
    const url = root(baseUrl) + "/v1/models?limit=100" + (after ? "&after_id=" + encodeURIComponent(after) : "");
    const res = await request(url, { timeout: 15000, headers: headers(cred) });
    if (res.status >= 400 || !res.json) throw new Error(errText(res));
    for (const m of res.json.data || []) {
      if (!m || !m.id) continue;
      out.push({
        id: m.id,
        ctx: Number(m.max_input_tokens) || 200000,
        maxOut: Number(m.max_tokens) || 0,
        display: m.display_name || m.id,
        created: m.created_at || "",
      });
    }
    if (!res.json.has_more || !res.json.last_id) break;
    after = res.json.last_id;
  }
  return out;
}

function nonEmpty(s) {
  const t = String(s == null ? "" : s);
  return t.trim() ? t : "(empty)";
}

function parseArgs(a) {
  if (a && typeof a === "object") return a;
  try {
    const v = JSON.parse(a || "{}");
    return v && typeof v === "object" ? v : {};
  } catch {
    return {};
  }
}

/**
 * OpenAI-shaped loop messages → Messages API { system, messages }.
 * - consecutive same-role messages are merged (all tool results of a round share one user turn)
 * - every tool_use gets a tool_result; a stray tool_result becomes text
 * - an assistant turn replays the blocks Claude produced (thinking included) when `replayThinking`;
 *   otherwise it is rebuilt from its text and tool_calls
 */
function toMessages(messages, { replayThinking = true } = {}) {
  const system = [];
  const out = [];
  const push = (role, blocks) => {
    const last = out[out.length - 1];
    if (last && last.role === role) last.content.push(...blocks);
    else out.push({ role, content: [...blocks] });
  };
  let pending = new Set(); // tool_use ids still waiting for their tool_result
  const settle = () => {
    if (!pending.size) return;
    push("user", [...pending].map((id) => ({ type: "tool_result", tool_use_id: id, content: "(no result recorded)" })));
    pending = new Set();
  };
  for (const m of messages || []) {
    if (!m) continue;
    if (m.role === "system") {
      system.push(String(m.content || ""));
      continue;
    }
    if (m.role === "tool") {
      if (pending.has(m.tool_call_id)) {
        pending.delete(m.tool_call_id);
        push("user", [{ type: "tool_result", tool_use_id: m.tool_call_id, content: nonEmpty(m.content) }]);
      } else push("user", [{ type: "text", text: "[" + (m.name || "tool") + " result]\n" + nonEmpty(m.content) }]);
      continue;
    }
    settle();
    if (m.role === "user") {
      push("user", [{ type: "text", text: nonEmpty(m.content) }]);
      continue;
    }
    if (m.role !== "assistant") continue;
    let blocks = null;
    if (Array.isArray(m.blocks) && m.blocks.length) {
      blocks = m.blocks.filter((b) => b && typeof b === "object");
      if (!replayThinking) blocks = blocks.filter((b) => b.type !== "thinking" && b.type !== "redacted_thinking");
      blocks = blocks.filter((b) => b.type !== "text" || String(b.text || "").trim());
    }
    if (!blocks || !blocks.length) {
      blocks = [];
      if (m.content && String(m.content).trim()) blocks.push({ type: "text", text: String(m.content) });
      for (const tc of m.tool_calls || []) {
        if (!tc || !tc.function || !tc.function.name) continue;
        blocks.push({ type: "tool_use", id: tc.id, name: tc.function.name, input: parseArgs(tc.function.arguments) });
      }
      if (!blocks.length) blocks.push({ type: "text", text: "(empty)" });
    }
    for (const b of blocks) if (b.type === "tool_use") pending.add(b.id);
    push("assistant", blocks);
  }
  settle();
  if (!out.length || out[0].role !== "user") out.unshift({ role: "user", content: [{ type: "text", text: "(conversation continues)" }] });
  return { system: system.join("\n\n"), messages: out };
}

function toTools(tools) {
  return (tools || []).map((t) => ({
    name: t.function.name,
    description: t.function.description || "",
    input_schema: t.function.parameters || { type: "object", properties: {} },
  }));
}

function emptyReply() {
  return { content: "", tool_calls: [], blocks: [], usage: {}, stop: "", stopDetails: null, model: "", truncated: false };
}

/** Fold one SSE event into the reply being assembled. */
function collect(reply, blocks, event, d, onText) {
  if (event === "error" || (d && d.type === "error")) {
    throw new Error((d && d.error && (d.error.message || d.error.type)) || "stream error");
  }
  if (!d || typeof d !== "object") return;
  if (d.type === "message_start") {
    const msg = d.message || {};
    reply.model = msg.model || "";
    Object.assign(reply.usage, msg.usage || {});
  } else if (d.type === "content_block_start") {
    blocks[d.index] = { ...(d.content_block || {}), _json: "" };
  } else if (d.type === "content_block_delta") {
    const b = blocks[d.index];
    const delta = d.delta || {};
    if (!b) return;
    if (delta.type === "text_delta") {
      b.text = (b.text || "") + (delta.text || "");
      if (onText && delta.text) onText(delta.text);
    } else if (delta.type === "input_json_delta") b._json += delta.partial_json || "";
    else if (delta.type === "thinking_delta") b.thinking = (b.thinking || "") + (delta.thinking || "");
    else if (delta.type === "signature_delta") b.signature = (b.signature || "") + (delta.signature || "");
  } else if (d.type === "message_delta") {
    const delta = d.delta || {};
    if (delta.stop_reason) reply.stop = delta.stop_reason;
    if (delta.stop_details) reply.stopDetails = delta.stop_details;
    Object.assign(reply.usage, d.usage || {});
  }
}

function fromBlocks(reply, content) {
  const blocks = [];
  for (const b of content) {
    if (!b || typeof b !== "object") continue;
    const { _json, ...clean } = b;
    if (clean.type === "tool_use" && _json) {
      try {
        clean.input = JSON.parse(_json);
      } catch {
        clean.input = {};
      }
    }
    if (clean.type === "tool_use" && !clean.input) clean.input = {};
    blocks.push(clean);
  }
  reply.blocks = blocks;
  reply.content = blocks.filter((b) => b.type === "text").map((b) => b.text || "").join("\n");
  reply.tool_calls = blocks
    .filter((b) => b.type === "tool_use")
    .map((b) => ({ id: b.id, type: "function", function: { name: b.name, arguments: JSON.stringify(b.input || {}) } }));
  const u = reply.usage || {};
  reply.usage = {
    prompt_tokens: (u.input_tokens || 0) + (u.cache_read_input_tokens || 0) + (u.cache_creation_input_tokens || 0),
    completion_tokens: u.output_tokens || 0,
    cache_read: u.cache_read_input_tokens || 0,
    cache_write: u.cache_creation_input_tokens || 0,
  };
  if (reply.stop === "refusal") {
    const sd = reply.stopDetails || {};
    throw new Error("Claude declined this request" + (sd.explanation || sd.category ? ": " + (sd.explanation || sd.category) : "") + ".");
  }
  if (reply.stop === "max_tokens") {
    reply.truncated = true;
    if (!reply.tool_calls.length && !reply.content.trim()) {
      reply.content = "(Claude hit the output token limit before writing anything. Raise localAgentBridge.agent.claudeMaxOutputTokens.)";
    }
  }
  return reply;
}

function fromMessage(json) {
  const r = emptyReply();
  r.model = json.model || "";
  r.stop = json.stop_reason || "";
  r.stopDetails = json.stop_details || null;
  r.usage = json.usage || {};
  return fromBlocks(r, json.content || []);
}

function sleep(ms, signal) {
  return new Promise((resolve, reject) => {
    const t = setTimeout(resolve, ms);
    if (signal) signal.addEventListener("abort", () => (clearTimeout(t), reject(new Error("stopped"))), { once: true });
  });
}

/**
 * One streamed Messages API call. Same return shape as llm.chat(): { content, tool_calls, usage },
 * plus `blocks` (the raw assistant content to replay) and `truncated`.
 * Retries 429 / 529 / 5xx and connection drops; throws ThinkingMismatch when the API rejects a
 * replayed thinking block (the loop then retries without them).
 */
async function chat({ baseUrl, cred, model, messages, tools, maxTokens = 16000, effort = "", replayThinking = true, signal, onText }) {
  const conv = toMessages(messages, { replayThinking });
  const body = { model, max_tokens: maxTokens, stream: true, messages: conv.messages, cache_control: { type: "ephemeral" } };
  if (conv.system) body.system = [{ type: "text", text: conv.system, cache_control: { type: "ephemeral" } }];
  if (tools && tools.length) body.tools = toTools(tools);
  if (supportsAdaptive(model)) {
    body.thinking = { type: "adaptive" };
    if (EFFORTS.includes(effort)) body.output_config = { effort };
  }
  for (let attempt = 0; ; attempt++) {
    if (signal && signal.aborted) throw new Error("stopped");
    const reply = emptyReply();
    const blocks = [];
    let res;
    try {
      res = await request(root(baseUrl) + "/v1/messages", {
        method: "POST",
        body,
        timeout: 600000,
        headers: headers(cred),
        signal,
        onEvent: (ev, d) => collect(reply, blocks, ev, d, onText),
      });
    } catch (e) {
      const msg = String((e && e.message) || e);
      if (msg !== "stopped" && attempt < RETRIES && /ECONNRESET|ETIMEDOUT|EAI_AGAIN|ENOTFOUND|socket hang up|timeout talking/i.test(msg)) {
        await sleep(1000 * (attempt + 1), signal);
        continue;
      }
      throw e;
    }
    if (res.status === 200 && res.events) return fromBlocks(reply, blocks);
    if (res.status === 200 && res.json && res.json.type === "message") return fromMessage(res.json); // proxy that ignored `stream`
    const msg = errText(res);
    if (/thinking.*(signature|bound to a different conversation)|bound to a different conversation/i.test(msg)) throw new ThinkingMismatch(msg);
    if ((res.status === 429 || res.status === 529 || res.status >= 500) && attempt < RETRIES) {
      const ra = Number(res.headers && res.headers["retry-after"]);
      await sleep(Number.isFinite(ra) && ra >= 0 ? Math.min(ra, 60) * 1000 : 2000 * (attempt + 1), signal);
      continue;
    }
    throw new Error("Claude API " + res.status + ": " + msg);
  }
}

module.exports = {
  API_VERSION,
  DEFAULT_URL,
  DEFAULT_CTX,
  PREFERRED,
  EFFORTS,
  ThinkingMismatch,
  root,
  supportsAdaptive,
  credentials,
  cleanKey,
  headers,
  listModels,
  toMessages,
  toTools,
  chat,
  fromMessage,
};
