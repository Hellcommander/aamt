"use strict";

// OpenAI-compatible client for local backends (vLLM / SGLang router, Ollama, LM Studio, ...).
// Ollama goes through its native /api/chat so we can raise num_ctx; its /v1 endpoint is
// stuck at the server default context, which is what kept truncating long agent turns.

const http = require("http");
const https = require("https");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { URL } = require("url");

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

function request(url, { method = "GET", body, timeout = 300000, apiKey, signal } = {}) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const lib = parsed.protocol === "https:" ? https : http;
    const payload = body ? JSON.stringify(body) : null;
    const headers = { Accept: "application/json" };
    if (payload) {
      headers["Content-Type"] = "application/json";
      headers["Content-Length"] = Buffer.byteLength(payload);
    }
    if (apiKey) headers.Authorization = "Bearer " + apiKey;
    const req = lib.request(
      {
        hostname: parsed.hostname,
        port: parsed.port || (parsed.protocol === "https:" ? 443 : 80),
        path: parsed.pathname + (parsed.search || ""),
        method,
        family: parsed.hostname === "localhost" || /^\d+\.\d+\.\d+\.\d+$/.test(parsed.hostname) ? 4 : undefined,
        timeout,
        headers,
      },
      (res) => {
        const chunks = [];
        res.on("data", (c) => chunks.push(c));
        res.on("end", () => {
          const raw = Buffer.concat(chunks).toString("utf8");
          let json = null;
          try {
            json = JSON.parse(raw);
          } catch {
            /* non-JSON body */
          }
          resolve({ status: res.statusCode || 0, json, raw });
        });
      }
    );
    const onAbort = () => req.destroy(new Error("stopped"));
    if (signal) {
      if (signal.aborted) return onAbort();
      signal.addEventListener("abort", onAbort, { once: true });
    }
    req.on("error", reject);
    req.on("timeout", () => req.destroy(new Error("timeout talking to " + url)));
    req.on("close", () => signal && signal.removeEventListener("abort", onAbort));
    if (payload) req.write(payload);
    req.end();
  });
}

function errText(res) {
  const j = res.json;
  if (j && j.error) return typeof j.error === "string" ? j.error : j.error.message || JSON.stringify(j.error);
  return "HTTP " + res.status + " " + String(res.raw || "").slice(0, 300);
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

/** Find a live backend. provider "auto" tries vLLM, then Ollama. */
async function discover({ provider = "auto", baseUrl = "", apiKey = "" } = {}) {
  const order = provider === "auto" ? ["vllm", "ollama"] : [provider];
  const errors = [];
  for (const id of order) {
    const spec = providerOf(id);
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
  throw new Error("No local model backend reachable.\n" + errors.join("\n"));
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
 * One chat completion. Returns { content, tool_calls, usage } with OpenAI-shaped tool_calls.
 * Throws ToolsUnsupported when the backend rejects the tools field (vLLM without
 * --enable-auto-tool-choice, Ollama models without the tools capability).
 */
async function chat({ backend, model, messages, tools, maxTokens = 2048, temperature = 0.2, numCtx, signal }) {
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
  providerOf,
  discover,
  listModels,
  pickModel,
  contextWindow,
  chat,
  qudlabKey,
  newId,
};
