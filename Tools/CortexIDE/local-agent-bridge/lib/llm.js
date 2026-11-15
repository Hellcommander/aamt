"use strict";

// Model backends behind one chat() call:
// - OpenAI-compatible local servers (vLLM / SGLang router, LM Studio, llama.cpp, ...)
// - Ollama through its native /api/chat, so num_ctx can be raised (its /v1 endpoint is stuck at
//   the server default context, which is what kept truncating long agent turns)
// - Claude through the Anthropic Messages API (lib/anthropic.js)

const fs = require("fs");
const os = require("os");
const path = require("path");
const { request, errText } = require("./http");
const anthropic = require("./anthropic");

const PROVIDERS = {
  vllm: {
    id: "vllm",
    label: "vLLM",
    urls: ["http://127.0.0.1:30000/v1", "http://127.0.0.1:8000/v1"],
    preferred: ["local-qwen-3b", "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ", "Qwen/Qwen2.5-3B-Instruct"],
    defaultCtx: 32768,
  },
  ollama: {
    id: "ollama",
    label: "Ollama",
    urls: ["http://127.0.0.1:11434/v1"],
    preferred: ["qwen2.5-coder:7b", "qwen3:8b", "qwen2.5-coder:14b", "llama3.1:8b"],
    defaultCtx: 16384,
  },
  openai: {
    id: "openai",
    label: "OpenAI-compatible",
    urls: [],
    preferred: [],
    defaultCtx: 32768,
  },
  anthropic: {
    id: "anthropic",
    label: "Claude",
    urls: [anthropic.DEFAULT_URL],
    preferred: anthropic.PREFERRED,
    defaultCtx: anthropic.DEFAULT_CTX,
  },
};

class ToolsUnsupported extends Error {}

function providerOf(id) {
  return PROVIDERS[id] || PROVIDERS.vllm;
}

function trimBase(u) {
  return String(u || "").trim().replace(/\/+$/, "").replace(/\/chat\/completions$/, "").replace(/\/models$/, "");
}

function ollamaRoot(base) {
  return trimBase(base).replace(/\/v1$/, "");
}

function qudlabKey() {
  const env = String(process.env.QUDLAB_PROXY_KEY || "").trim();
  if (env.length >= 32) return env;
  const file = path.join(process.env.LOCALAPPDATA || os.homedir(), "QudLab", "vllm-proxy-key.txt");
  try {
    return fs.readFileSync(file, "utf8").trim();
  } catch {
    return "";
  }
}

async function listModels(baseUrl, apiKey) {
  const res = await request(trimBase(baseUrl) + "/models", { timeout: 4000, apiKey });
  if (res.status >= 400 || !res.json) throw new Error(errText(res));
  return (res.json.data || [])
    .filter((d) => d && d.id)
    .map((d) => ({ id: d.id, ctx: Number(d.max_model_len || d.context_length || d.context_window || 0) || 0 }));
}

async function ollamaContextLength(baseUrl, model) {
  try {
    const res = await request(ollamaRoot(baseUrl) + "/api/show", { method: "POST", body: { model }, timeout: 5000 });
    const info = (res.json && res.json.model_info) || {};
    for (const k of Object.keys(info)) {
      if (/\.context_length$/.test(k)) return Number(info[k]) || 0;
    }
  } catch {
    /* optional */
  }
  return 0;
}

/**
 * Find a live backend. provider "auto" tries vLLM, then Ollama, then Claude when credentials exist.
 * anthropicApiKey is the key from Secret Storage; the generic apiKey setting also counts for Claude
 * when it looks like an Anthropic key.
 */
async function discover({ provider = "auto", baseUrl = "", apiKey = "", anthropicApiKey = "", anthropicWorkspaceId = "" } = {}) {
  const order = provider === "auto" ? ["vllm", "ollama", "anthropic"] : [provider];
  const errors = [];
  for (const id of order) {
    const spec = providerOf(id);
    if (id === "anthropic") {
      const cred = anthropic.credentials({ apiKey: anthropicApiKey || (/^sk-ant-/i.test(apiKey) ? apiKey : ""), workspaceId: anthropicWorkspaceId });
      if (!cred) {
        errors.push("Claude: no credentials (run \u201cAgent: Set Claude API Key\u201d, set ANTHROPIC_API_KEY, or `ant auth login`)");
        continue;
      }
      const u = anthropic.root(provider === "anthropic" && baseUrl ? baseUrl : spec.urls[0]);
      try {
        const models = await anthropic.listModels(u, cred);
        return { provider: "anthropic", label: spec.label, baseUrl: u, models, cred, credSource: cred.source };
      } catch (e) {
        let msg = String((e && e.message) || e);
        if (/anthropic-workspace-id/i.test(msg)) msg += " Set localAgentBridge.agent.claudeWorkspaceId (or ANTHROPIC_WORKSPACE_ID) to the wrkspc_... id from console.anthropic.com → Settings → Workspaces.";
        errors.push("Claude " + u + ": " + msg);
      }
      continue;
    }
    const urls = [];
    if (baseUrl) urls.push(trimBase(baseUrl));
    for (const u of spec.urls) if (!urls.includes(u)) urls.push(u);
    for (const u of urls) {
      const key = apiKey || (id === "vllm" ? qudlabKey() : "");
      try {
        const models = await listModels(u, key);
        return { provider: spec.id, label: spec.label, baseUrl: u, models, apiKey: key };
      } catch (e) {
        errors.push(spec.label + " " + u + ": " + (e.message || e));
      }
    }
  }
  throw new Error("No model backend reachable.\n" + errors.join("\n"));
}

function pickModel(models, requested, provider) {
  const ids = (models || []).map((m) => m.id);
  if (requested && ids.includes(requested)) return requested;
  for (const p of providerOf(provider).preferred) if (ids.includes(p)) return p;
  return ids[0] || requested || "";
}

/** Usable prompt window for the chosen model. */
async function contextWindow(backend, model, { override = 0, ollamaNumCtx = 16384 } = {}) {
  if (override > 0) return override;
  if (backend.provider === "anthropic") {
    // Plan for 200k unless the user asks for more: the whole conversation is resent every round.
    const m = (backend.models || []).find((x) => x.id === model);
    return Math.min((m && m.ctx) || anthropic.DEFAULT_CTX, anthropic.DEFAULT_CTX);
  }
  if (backend.provider === "ollama") {
    const native = await ollamaContextLength(backend.baseUrl, model);
    return native ? Math.min(native, ollamaNumCtx) : ollamaNumCtx;
  }
  const m = (backend.models || []).find((x) => x.id === model);
  return (m && m.ctx) || providerOf(backend.provider).defaultCtx;
}

/** Model names of OpenAI-compatible / local models that take images. */
const VISION_RE = /(^|[\/:_.-])(vl|vlm|vision|llava|bakllava|pixtral|minicpm-?v|moondream|internvl|cogvlm|idefics|smolvlm|paligemma|molmo|gemma-?3|gemma3n|llama-?3\.2-?\d*b?-?vision|llama-?4|mistral-small-3\.[1-9]|qwen2(\.5)?-?(vl|omni)|qwen3-?(vl|omni)|qvq|kimi-vl|glm-4(\.\d)?v|phi-?3\.5-vision|phi-?4-multimodal|granite-vision|gpt-4o|gpt-4\.1|gpt-5|o3|o4|claude|gemini)/i;
const visionCache = new Map();

/**
 * Whether the model can take images. mode "on"/"off" overrides; "auto": Claude and Claude Code yes,
 * Ollama from /api/show capabilities (or a vision projector), others from the model name.
 */
async function supportsVision(backend, model, mode = "auto") {
  if (mode === "on") return true;
  if (mode === "off") return false;
  if (!backend) return false;
  if (backend.provider === "anthropic" || backend.provider === "claude-code") return true;
  const key = backend.provider + "|" + backend.baseUrl + "|" + model;
  if (visionCache.has(key)) return visionCache.get(key);
  let yes = VISION_RE.test(String(model || ""));
  if (backend.provider === "ollama") {
    try {
      const res = await request(ollamaRoot(backend.baseUrl) + "/api/show", { method: "POST", body: { model }, timeout: 5000 });
      const j = res.json || {};
      if (Array.isArray(j.capabilities)) yes = j.capabilities.includes("vision");
      else if (j.projector_info || Object.keys(j.model_info || {}).some((k) => /\.vision\./.test(k))) yes = true;
    } catch {
      /* keep the name guess */
    }
  }
  visionCache.set(key, yes);
  return yes;
}

function imageNote(img) {
  return "[image" + (img.path ? ": " + img.path : "") + (img.width ? " (" + img.width + "x" + img.height + ")" : "") + "]";
}

/**
 * Loop messages → OpenAI chat format. A user message with images becomes a content array with
 * image_url parts. Tool messages must stay text there, so the images of a round's tool results go
 * in one user message right after that round's results.
 */
function toOpenAIMessages(messages) {
  const out = [];
  let pending = [];
  const flush = () => {
    if (!pending.length) return;
    out.push({
      role: "user",
      content: [{ type: "text", text: "Images from the tool results above:" }, ...pending.flatMap((img) => [{ type: "text", text: imageNote(img) }, { type: "image_url", image_url: { url: "data:" + img.mime + ";base64," + img.data } }])],
    });
    pending = [];
  };
  for (const m of messages) {
    if (m.role !== "tool") flush();
    const { images, blocks, ...rest } = m;
    const imgs = Array.isArray(images) ? images : [];
    if (m.role === "tool") {
      out.push(rest);
      pending.push(...imgs);
    } else if (m.role === "user" && imgs.length) {
      out.push({ ...rest, content: [{ type: "text", text: String(m.content == null ? "" : m.content) }, ...imgs.map((img) => ({ type: "image_url", image_url: { url: "data:" + img.mime + ";base64," + img.data } }))] });
    } else out.push(rest);
  }
  flush();
  return out;
}

function toOllamaMessages(messages) {
  const out = [];
  let pending = [];
  const flush = () => {
    if (!pending.length) return;
    out.push({ role: "user", content: "Images from the tool results above: " + pending.map(imageNote).join(" "), images: pending.map((i) => i.data) });
    pending = [];
  };
  for (const m of messages) {
    if (m.role !== "tool") flush();
    const imgs = Array.isArray(m.images) ? m.images : [];
    const conv = toOllamaMessage(m);
    if (m.role === "tool") pending.push(...imgs);
    else if (imgs.length) conv.images = imgs.map((i) => i.data);
    out.push(conv);
  }
  flush();
  return out;
}

function toOllamaMessage(m) {
  return ((m) => {
    if (m.role === "assistant" && Array.isArray(m.tool_calls) && m.tool_calls.length) {
      return {
        role: "assistant",
        content: m.content || "",
        tool_calls: m.tool_calls.map((tc) => {
          let args = tc.function && tc.function.arguments;
          if (typeof args === "string") {
            try {
              args = JSON.parse(args);
            } catch {
              args = {};
            }
          }
          return { function: { name: tc.function.name, arguments: args || {} } };
        }),
      };
    }
    if (m.role === "tool") return { role: "tool", content: String(m.content || ""), tool_name: m.name };
    return { role: m.role, content: String(m.content == null ? "" : m.content) };
  })(m);
}

let callSeq = 0;
function newId() {
  callSeq += 1;
  return "call_" + Date.now().toString(36) + "_" + callSeq;
}

/**
 * One chat completion. Returns { content, tool_calls, usage } with OpenAI-shaped tool_calls
 * (Claude adds `blocks`, the raw assistant content to replay, and `truncated`).
 * Throws ToolsUnsupported when the backend rejects the tools field (vLLM without
 * --enable-auto-tool-choice, Ollama models without the tools capability), and
 * ThinkingMismatch when Claude rejects replayed thinking blocks after the history changed.
 * effort / replayThinking / onText are Claude-only; temperature is not sent to Claude.
 */
/** Socket idle limit for local backends: a big prompt on a CPU-offloaded model can take minutes before its first token. */
const LOCAL_TIMEOUT = 15 * 60 * 1000;

async function chat({ backend, model, messages, tools, maxTokens = 2048, temperature = 0.2, numCtx, signal, effort = "", replayThinking = true, onText, onReasoning }) {
  if (backend.provider === "anthropic") {
    return anthropic.chat({ baseUrl: backend.baseUrl, cred: backend.cred, model, messages, tools, maxTokens, effort, replayThinking, signal, onText });
  }
  const isOllama = backend.provider === "ollama";
  const say = (t) => {
    if (t && onText) onText(t);
  };
  const think = (t) => {
    if (t && onReasoning) onReasoning(t);
  };
  // Streamed, so a slow (CPU-offloaded) model never idles the socket into a timeout and the panel
  // can show progress. A server that ignores `stream` answers with plain JSON, handled below.
  let res;
  const acc = { content: "", reasoning: "", calls: [], usage: null, done: "", error: "" };
  if (isOllama) {
    const body = {
      model,
      messages: toOllamaMessages(messages),
      stream: true,
      options: { temperature, num_predict: maxTokens, ...(numCtx ? { num_ctx: numCtx } : {}) },
    };
    if (tools && tools.length) body.tools = tools;
    res = await request(ollamaRoot(backend.baseUrl) + "/api/chat", {
      method: "POST",
      body,
      signal,
      timeout: LOCAL_TIMEOUT,
      onEvent: (_e, chunk) => {
        if (!chunk || typeof chunk !== "object") return;
        if (chunk.error) acc.error = typeof chunk.error === "string" ? chunk.error : JSON.stringify(chunk.error);
        const m = chunk.message || {};
        if (m.content) {
          acc.content += m.content;
          say(m.content);
        }
        if (m.thinking) {
          acc.reasoning += m.thinking;
          think(m.thinking);
        }
        for (const tc of m.tool_calls || []) acc.calls.push(tc);
        if (chunk.done) {
          acc.done = chunk.done_reason || "stop";
          acc.usage = { prompt_tokens: chunk.prompt_eval_count || 0, completion_tokens: chunk.eval_count || 0 };
        }
      },
    });
  } else {
    const body = { model, messages: toOpenAIMessages(messages), stream: true, stream_options: { include_usage: true }, temperature, max_tokens: maxTokens };
    if (tools && tools.length) {
      body.tools = tools;
      body.tool_choice = "auto";
    }
    const byIndex = new Map();
    res = await request(trimBase(backend.baseUrl) + "/chat/completions", {
      method: "POST",
      body,
      signal,
      apiKey: backend.apiKey,
      timeout: LOCAL_TIMEOUT,
      onEvent: (_e, data) => {
        if (!data || typeof data !== "object") return; // "[DONE]"
        if (data.error) acc.error = typeof data.error === "string" ? data.error : data.error.message || JSON.stringify(data.error);
        if (data.usage) acc.usage = data.usage;
        const ch = (data.choices || [])[0];
        if (!ch) return;
        const d = ch.delta || ch.message || {};
        if (d.content) {
          acc.content += d.content;
          say(d.content);
        }
        const r = d.reasoning_content || d.reasoning;
        if (r) {
          acc.reasoning += r;
          think(r);
        }
        for (const tc of d.tool_calls || []) {
          // Tool calls arrive in fragments keyed by index: the name once, the arguments in pieces.
          const k = tc.index != null ? tc.index : byIndex.size;
          const cur = byIndex.get(k) || { id: "", type: "function", function: { name: "", arguments: "" } };
          if (tc.id) cur.id = tc.id;
          if (tc.function && tc.function.name) cur.function.name += tc.function.name;
          if (tc.function && tc.function.arguments != null) {
            cur.function.arguments += typeof tc.function.arguments === "string" ? tc.function.arguments : JSON.stringify(tc.function.arguments);
          }
          byIndex.set(k, cur);
        }
        if (ch.finish_reason) acc.done = ch.finish_reason;
      },
    });
    acc.calls = [...byIndex.values()];
  }
  const streamed = res.status === 200 && res.events != null;
  if (!streamed && (res.status >= 400 || !res.json)) {
    const msg = errText(res);
    if (tools && tools.length && /tool|function/i.test(msg)) throw new ToolsUnsupported(msg);
    throw new Error(msg);
  }
  if (acc.error) {
    if (tools && tools.length && /tool|function/i.test(acc.error) && !acc.content) throw new ToolsUnsupported(acc.error);
    throw new Error(acc.error);
  }
  if (!streamed) {
    // The server ignored `stream` and sent one JSON answer.
    if (isOllama) {
      const m = res.json.message || {};
      acc.content = m.content || "";
      acc.reasoning = m.thinking || "";
      acc.calls = m.tool_calls || [];
      acc.done = res.json.done_reason || "stop";
      acc.usage = { prompt_tokens: res.json.prompt_eval_count || 0, completion_tokens: res.json.eval_count || 0 };
    } else {
      const choice = (res.json.choices || [])[0] || {};
      const m = choice.message || {};
      acc.content = m.content || "";
      acc.reasoning = m.reasoning_content || m.reasoning || "";
      acc.calls = m.tool_calls || [];
      acc.done = choice.finish_reason || "";
      acc.usage = res.json.usage || {};
    }
  }
  const tool_calls = acc.calls
    .filter((tc) => tc && tc.function && tc.function.name)
    .map((tc) => ({
      id: tc.id || newId(),
      type: "function",
      function: {
        name: tc.function.name,
        arguments: typeof tc.function.arguments === "string" ? tc.function.arguments : JSON.stringify(tc.function.arguments || {}),
      },
    }));
  return { content: acc.content, reasoning: acc.reasoning, tool_calls, usage: acc.usage || {}, truncated: acc.done === "length" };
}

module.exports = {
  PROVIDERS,
  ToolsUnsupported,
  ThinkingMismatch: anthropic.ThinkingMismatch,
  anthropic,
  request,
  providerOf,
  discover,
  listModels,
  pickModel,
  contextWindow,
  supportsVision,
  toOpenAIMessages,
  toOllamaMessages,
  VISION_RE,
  chat,
  qudlabKey,
  newId,
};
