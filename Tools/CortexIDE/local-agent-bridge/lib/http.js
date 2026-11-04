"use strict";

// HTTP helper shared by the model backends: JSON requests, plus Server-Sent Events for the
// Claude Messages API. No dependencies, like the rest of the extension.

const http = require("http");
const https = require("https");
const { URL } = require("url");

/**
 * @param {string} url
 * @param {object} [o]
 * @param {string} [o.method]
 * @param {object} [o.body]       JSON body
 * @param {number} [o.timeout]    ms of socket inactivity before giving up
 * @param {string} [o.apiKey]     sent as Authorization: Bearer
 * @param {object} [o.headers]    extra headers
 * @param {AbortSignal} [o.signal]
 * @param {(event:string, data:any)=>void} [o.onEvent]
 *   When set and the server answers 200 text/event-stream, each SSE event is passed here and the
 *   promise resolves with { status: 200, events } once the stream ends. Any other response
 *   (an error, or a plain JSON message) is buffered and returned as { status, json, raw }.
 * @returns {Promise<{status:number, json:any, raw:string, headers:object, events?:number}>}
 */
function request(url, { method = "GET", body, timeout = 300000, apiKey, headers: extra, signal, onEvent } = {}) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const lib = parsed.protocol === "https:" ? https : http;
    const payload = body ? JSON.stringify(body) : null;
    const headers = { Accept: onEvent ? "text/event-stream, application/json" : "application/json", ...(extra || {}) };
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
        res.on("error", reject);
        const ct = String(res.headers["content-type"] || "");
        if (onEvent && res.statusCode === 200 && /text\/event-stream/i.test(ct)) {
          let buf = "";
          let events = 0;
          let failed = false;
          const fail = (e) => {
            failed = true;
            reject(e);
            res.destroy();
          };
          const deliver = (block) => {
            const ev = parseSse(block);
            if (!ev) return;
            events++;
            onEvent(ev.event, ev.data);
          };
          res.setEncoding("utf8");
          res.on("data", (chunk) => {
            buf += chunk;
            let at;
            try {
              while ((at = buf.search(/\r?\n\r?\n/)) >= 0) {
                const sep = buf.slice(at).match(/^\r?\n\r?\n/)[0].length;
                const block = buf.slice(0, at);
                buf = buf.slice(at + sep);
                deliver(block);
              }
            } catch (e) {
              fail(e);
            }
          });
          res.on("end", () => {
            if (failed) return;
            try {
              deliver(buf);
            } catch (e) {
              return fail(e);
            }
            resolve({ status: 200, json: null, raw: "", headers: res.headers, events });
          });
          return;
        }
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
          resolve({ status: res.statusCode || 0, json, raw, headers: res.headers });
        });
      }
    );
    // Handlers first: destroying the request with an error before "error" is attached would throw
    // an unhandled error event and leave this promise pending.
    const onAbort = () => req.destroy(new Error("stopped"));
    req.on("error", reject);
    req.on("timeout", () => req.destroy(new Error("timeout talking to " + url)));
    req.on("close", () => signal && signal.removeEventListener("abort", onAbort));
    if (signal) {
      if (signal.aborted) return onAbort();
      signal.addEventListener("abort", onAbort, { once: true });
    }
    if (payload) req.write(payload);
    req.end();
  });
}

/** One SSE block ("event: x\ndata: {...}") → { event, data } with data JSON-parsed when possible. */
function parseSse(block) {
  const lines = String(block || "").replace(/\r/g, "").split("\n");
  let event = "message";
  const data = [];
  for (const l of lines) {
    if (l.startsWith("event:")) event = l.slice(6).trim();
    else if (l.startsWith("data:")) data.push(l.slice(5).replace(/^ /, ""));
  }
  if (!data.length) return null;
  const text = data.join("\n");
  let parsed = text;
  try {
    parsed = JSON.parse(text);
  } catch {
    /* keep text */
  }
  return { event, data: parsed };
}

function errText(res) {
  const j = res.json;
  if (j && j.error) return typeof j.error === "string" ? j.error : j.error.message || JSON.stringify(j.error);
  return "HTTP " + res.status + " " + String(res.raw || "").slice(0, 300);
}

module.exports = { request, parseSse, errText };
