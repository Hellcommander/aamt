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

function toOllamaMessages(messages) {
  return messages.map((m) => {
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
  });
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
async function chat({ backend, model, messages, tools, maxTokens = 2048, temperature = 0.2, numCtx, signal, effort = "", replayThinking = true, onText }) {
  if (backend.provider === "anthropic") {
    return anthropic.chat({ baseUrl: backend.baseUrl, cred: backend.cred, model, messages, tools, maxTokens, effort, replayThinking, signal, onText });
  }
  const isOllama = backend.provider === "ollama";
  let res;
  if (isOllama) {
    const body = {
      model,
      messages: toOllamaMessages(messages),
      stream: false,
      options: { temperature, num_predict: maxTokens, ...(numCtx ? { num_ctx: numCtx } : {}) },
    };
    if (tools && tools.length) body.tools = tools;
    res = await request(ollamaRoot(backend.baseUrl) + "/api/chat", { method: "POST", body, signal });
  } else {
    const body = { model, messages, stream: false, temperature, max_tokens: maxTokens };
    if (tools && tools.length) {
      body.tools = tools;
      body.tool_choice = "auto";
    }
    res = await request(trimBase(backend.baseUrl) + "/chat/completions", {
      method: "POST",
      body,
      signal,
      apiKey: backend.apiKey,
    });
  }
  if (res.status >= 400 || !res.json) {
    const msg = errText(res);
    if (tools && tools.length && /tool|function/i.test(msg)) throw new ToolsUnsupported(msg);
    throw new Error(msg);
  }
  if (isOllama) {
    const m = res.json.message || {};
    return {
      content: m.content || "",
      tool_calls: (m.tool_calls || []).map((tc) => ({
        id: newId(),
        type: "function",
        function: {
          name: tc.function && tc.function.name,
          arguments: JSON.stringify((tc.function && tc.function.arguments) || {}),
        },
      })),
      usage: { prompt_tokens: res.json.prompt_eval_count || 0, completion_tokens: res.json.eval_count || 0 },
    };
  }
  const choice = (res.json.choices || [])[0] || {};
  const m = choice.message || {};
  return {
    content: m.content || "",
    tool_calls: (m.tool_calls || []).map((tc) => ({ ...tc, id: tc.id || newId() })),
    usage: res.json.usage || {},
  };
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
  chat,
  qudlabKey,
  newId,
};
