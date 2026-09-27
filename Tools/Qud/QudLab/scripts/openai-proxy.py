#!/usr/bin/env python3
"""Windows-native OpenAI frontend that forwards /v1 to a remote engine (vLLM).

SGLang's `sglang serve` does not take `--remote`. This stdlib proxy is the
Windows frontend so Cursor / CortexIDE / Qud Lab / LM Studio can speak
http://127.0.0.1:30000/v1 while vLLM does GPU inference on :8000.

Cursor Agent traffic is passed through (full messages + summaries + tools)
to vLLM. A gather-then-answer loop is only for Cortex/LM Studio chats that
did not send tools. SSE is streamed so Cortex does not abort.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from http.client import HTTPConnection, HTTPSConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paid_api import (
    ADVERTISE_MODEL_IDS,
    CURSOR_BYOK_MODEL_ID,
    FAKE_MODEL_IDS,
    INDEX_DIR,
    PAID_MODEL_ALIASES,
    anthropic_to_openai,
    compact_history,
    describe_messages,
    fit_vllm_context,
    format_chat_index,
    load_prior_agent_patterns,
    log_proxy,
    openai_to_anthropic,
    openai_to_responses,
    path_kind,
    read_latest_index,
    sanitize_chat,
)
from shelve_context import (
    HIGH_CTX_MODEL,
    consume_pending_shelf_prompt,
    create_shelf,
    escalate,
    format_shelf_prompt,
    list_shelves,
    load_shelf,
    set_pending_unshelve,
)
from vllm_agent import (
    inject_missing_tool_calls,
    is_cursor_openai_client,
    prepare_request,
    run_local_loop,
    should_local_loop,
    synthesize_tool_completion,
    to_sse,
)
from proxy_auth import (
    check_key,
    client_id,
    is_tunnel_request,
    load_or_create_key,
    locked,
    note_failure,
    note_success,
    presented_key,
)

HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
    "authorization",
    "x-api-key",
    "api-key",
    "x-openai-api-key",
}

CLIENT_GONE = (
    ConnectionAbortedError,
    ConnectionResetError,
    BrokenPipeError,
    TimeoutError,
)


def normalize_openai_path(path: str) -> str:
    """Collapse Cursor/Cortex ``/v1/v1/models`` when the client base URL already ends in /v1."""
    raw = path or "/"
    query = ""
    if "?" in raw:
        raw, query = raw.split("?", 1)
        query = "?" + query
    while "/v1/v1" in raw:
        raw = raw.replace("/v1/v1", "/v1", 1)
    if raw in ("/v1", "/v1/"):
        raw = "/v1/models"
    return raw + query


def split_backend(url: str) -> tuple[str, int, bool, str]:
    raw = url.strip() or "http://127.0.0.1:8000/v1"
    if "://" not in raw:
        raw = "http://" + raw
    parsed = urlparse(raw)
    host = parsed.hostname or "127.0.0.1"
    https = parsed.scheme == "https"
    port = parsed.port or (443 if https else 80)
    prefix = parsed.path.rstrip("/")
    if prefix in ("", "/"):
        prefix = "/v1"
    return host, port, https, prefix


def main() -> int:
    p = argparse.ArgumentParser(description="OpenAI reverse proxy to vLLM")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=30000)
    p.add_argument("--remote", default="http://127.0.0.1:8000/v1")
    p.add_argument(
        "--models-from",
        default="",
        help="GET /v1/models from this OpenAI URL instead of --remote (vLLM :8000). sglang_router openai backend always lists id=unknown.",
    )
    p.add_argument("--model-name", default="")
    p.add_argument(
        "--print-key",
        action="store_true",
        help="Print the GPU proxy key path and length, then exit (does not print the key).",
    )
    args = p.parse_args()
    expected_key, key_file, key_created = load_or_create_key()
    if args.print_key:
        print("GPU proxy key file: %s" % key_file)
        print("chars: %s (min 48; Cursor OpenAI API Key must match this file)" % len(expected_key))
        return 0

    b_host, b_port, https, prefix = split_backend(args.remote)
    listen = (args.host, args.port)
    netloc = "%s:%s" % (b_host, b_port)
    aliases = ADVERTISE_MODEL_IDS
    backend_ids: list[str] = []
    models_cache: dict = {"t": 0.0, "payload": b""}

    def fetch_backend_ids() -> list[str]:
        srcs = []
        if args.models_from:
            srcs.append(args.models_from)
        srcs.append(args.remote)
        seen_src = set()
        for src in srcs:
            if not src or src in seen_src:
                continue
            seen_src.add(src)
            mh, mp, mhttps, mprefix = split_backend(src)
            conn = (HTTPSConnection if mhttps else HTTPConnection)(mh, port=mp, timeout=10)
            try:
                conn.request(
                    "GET",
                    mprefix + "/models",
                    headers={"Host": "%s:%s" % (mh, mp), "Accept": "application/json"},
                )
                res = conn.getresponse()
                payload = res.read()
                if res.status >= 400:
                    continue
                data = json.loads(payload.decode("utf-8"))
                ids = []
                for item in data.get("data") or []:
                    mid = item.get("id") if isinstance(item, dict) else None
                    if isinstance(mid, str) and mid:
                        ids.append(mid)
                honest = args.model_name or "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"
                out = []
                have = set()
                for mid in ids:
                    name = honest if mid.lower() in FAKE_MODEL_IDS else mid
                    if not name or name.lower() in have:
                        continue
                    have.add(name.lower())
                    out.append(name)
                if out:
                    return out
            except Exception:
                continue
            finally:
                conn.close()
        if args.model_name:
            return [args.model_name]
        return ["Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"]

    def real_model() -> str:
        if args.model_name and args.model_name.lower() not in FAKE_MODEL_IDS:
            return args.model_name
        if not backend_ids:
            backend_ids[:] = fetch_backend_ids()
        for mid in backend_ids:
            if mid and mid.lower() not in FAKE_MODEL_IDS:
                return mid
        return "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"

    def rewrite_request_model(path: str, body: bytes) -> bytes:
        kind = path_kind(path)
        if not body or (kind not in ("chat", "anthropic", "responses") and "/completions" not in path and "/embeddings" not in path):
            return body
        try:
            data = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return body
        if not isinstance(data, dict):
            return body
        honest = real_model()
        name = data.get("model")
        if isinstance(name, str) and name == honest:
            return body
        data["model"] = honest
        return json.dumps(data).encode("utf-8")

    def decorate_models(payload: bytes) -> bytes:
        try:
            data = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return payload
        if not isinstance(data, dict) or not isinstance(data.get("data"), list):
            return payload
        honest = real_model()
        cleaned = []
        have = set()
        for item in data["data"]:
            if not isinstance(item, dict):
                continue
            mid = str(item.get("id") or "")
            if mid.lower() in FAKE_MODEL_IDS:
                mid = honest
            key = mid.lower()
            if not mid or key in have:
                continue
            have.add(key)
            row = dict(item)
            row["id"] = mid
            cleaned.append(row)
        for mid in [honest, *aliases]:
            if not mid or mid.lower() in FAKE_MODEL_IDS or mid.lower() in have:
                continue
            cleaned.append({"id": mid, "object": "model"})
            have.add(mid.lower())
        cleaned.sort(key=lambda row: 0 if row.get("id") == honest else 1)
        data["data"] = cleaned
        return json.dumps(data).encode("utf-8")

    def rewrite_chat_model_field(payload: bytes) -> bytes:
        honest = real_model().encode("utf-8")
        for fake in FAKE_MODEL_IDS:
            b = fake.encode("utf-8")
            payload = payload.replace(b'"model":"' + b + b'"', b'"model":"' + honest + b'"')
            payload = payload.replace(b'"model": "' + b + b'"', b'"model": "' + honest + b'"')
        return payload

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *a) -> None:
            msg = fmt % a
            if "GET /v1/models" in msg:
                return
            sys.stderr.write("%s - %s\n" % (self.address_string(), msg))

        def do_GET(self) -> None:
            self._proxy()

        def do_POST(self) -> None:
            self._proxy()

        def do_PUT(self) -> None:
            self._proxy()

        def do_DELETE(self) -> None:
            self._proxy()

        def do_OPTIONS(self) -> None:
            try:
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Headers", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.end_headers()
            except CLIENT_GONE:
                return

        def _upstream_path(self) -> str:
            path = normalize_openai_path(self.path or "/")
            if path in ("/", "/health", "/healthz"):
                return "/health"
            if path_kind(path) in ("anthropic", "responses"):
                return prefix + "/chat/completions"
            if path.startswith("/v1"):
                rest = path[3:] or "/"
                if not rest.startswith("/"):
                    rest = "/" + rest
                return prefix + rest
            return prefix + (path if path.startswith("/") else "/" + path)

        def _reply_bytes(self, status: int, payload: bytes, content_type: str) -> None:
            try:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("X-QudLab-Frontend", "1")
                self.end_headers()
                if payload:
                    self.wfile.write(payload)
                    self.wfile.flush()
            except CLIENT_GONE:
                return

        def _frontend_status(self) -> dict:
            ids = fetch_backend_ids()
            if ids:
                backend_ids[:] = ids
            return {
                "ok": True,
                "role": "frontend",
                "frontend": "http://%s:%s/v1" % listen,
                "backend": args.remote,
                "backend_up": bool(ids),
                "model": real_model(),
                "models": ids,
                "aliases": list(aliases),
                "tool_loop": "cortex-only",
                "cursor_passthrough": True,
                "cursor_model": CURSOR_BYOK_MODEL_ID,
                "chat_index": os.path.join(INDEX_DIR, "latest.md"),
                "auth": "bearer",
                "key_file": key_file,
            }

        def _forward_json(self, data: dict) -> dict:
            raw = json.dumps(data).encode("utf-8")
            conn_cls = HTTPSConnection if https else HTTPConnection
            conn = conn_cls(b_host, port=b_port, timeout=600)
            try:
                conn.request(
                    "POST",
                    prefix + "/chat/completions",
                    body=raw,
                    headers={
                        "Host": netloc,
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                )
                res = conn.getresponse()
                payload = res.read()
                try:
                    parsed = json.loads(payload.decode("utf-8"))
                except (ValueError, UnicodeDecodeError) as exc:
                    raise RuntimeError("vLLM returned non-JSON (%s): %s" % (res.status, payload[:200])) from exc
                if res.status >= 400:
                    raise RuntimeError(parsed.get("error", payload[:300]))
                if not isinstance(parsed, dict):
                    raise RuntimeError("vLLM chat completion was not an object")
                if str(parsed.get("model") or "").lower() in FAKE_MODEL_IDS:
                    parsed["model"] = real_model()
                return parsed
            finally:
                conn.close()

        def _pipe_stream(self, res) -> None:
            self.send_response(res.status, res.reason)
            for k, v in res.getheaders():
                if k.lower() in HOP:
                    continue
                self.send_header(k, v)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            while True:
                chunk = res.read(8192)
                if not chunk:
                    break
                self.wfile.write(rewrite_chat_model_field(chunk))
                self.wfile.flush()

        def _auth_error(self, status: int, message: str) -> None:
            payload = json.dumps(
                {
                    "error": {
                        "message": message,
                        "type": "invalid_request_error",
                        "code": "invalid_api_key" if status == 401 else "rate_limit_exceeded",
                    }
                }
            ).encode("utf-8")
            self._reply_bytes(status, payload, "application/json")

        def _require_key(self, public: bool) -> bool:
            cid = client_id(self.headers, self.client_address)
            if locked(cid):
                log_proxy("auth locked cid=%s" % cid)
                self._auth_error(429, "Too many invalid API key attempts. Try later.")
                return False
            presented = presented_key(self.headers)
            if check_key(presented, expected_key):
                note_success(cid)
                return True
            note_failure(cid)
            log_proxy("auth fail cid=%s tunnel=%s has_header=%s" % (cid, public, bool(presented)))
            msg = "Invalid API key"
            if not public:
                msg += ". Cursor OpenAI API Key must match %s" % key_file
            self._auth_error(401, msg)
            return False

        def _proxy(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            headers = {
                k: v
                for k, v in self.headers.items()
                if k.lower() not in HOP
            }
            headers["Host"] = netloc
            headers["Accept"] = self.headers.get("Accept") or "*/*"
            path_only = normalize_openai_path(self.path or "").split("?", 1)[0]
            status_path = (self.path or "/").split("?", 1)[0].rstrip("/")
            public = is_tunnel_request(self.headers)
            local_status = (
                self.command == "GET"
                and status_path in ("/status", "/v1/status", "/frontend", "/v1/frontend", "/health", "/healthz")
                and not public
            )
            if not local_status and not self._require_key(public):
                return
            if self.command == "GET" and status_path in (
                "/status",
                "/v1/status",
                "/frontend",
                "/v1/frontend",
            ):
                payload = json.dumps(self._frontend_status()).encode("utf-8")
                self._reply_bytes(200, payload, "application/json")
                return
            if self.command == "GET" and status_path in (
                "/chat-index",
                "/v1/chat-index",
            ):
                idx = read_latest_index()
                self._reply_bytes(200, json.dumps(idx, ensure_ascii=False).encode("utf-8"), "application/json")
                return
            if self.command == "GET" and status_path in (
                "/chat-index.md",
                "/v1/chat-index.md",
            ):
                self._reply_bytes(200, format_chat_index(read_latest_index()).encode("utf-8"), "text/markdown; charset=utf-8")
                return
            if self.command == "GET" and status_path in (
                "/agent-patterns",
                "/v1/agent-patterns",
            ):
                text = load_prior_agent_patterns(task="", workspaces=[])
                self._reply_bytes(200, (text or "(no agent transcripts found)\n").encode("utf-8"), "text/plain; charset=utf-8")
                return
            if self.command == "GET" and status_path in ("/shelves", "/v1/shelves"):
                self._reply_bytes(
                    200,
                    json.dumps({"shelves": list_shelves(), "high_ctx_model": HIGH_CTX_MODEL}, indent=2).encode("utf-8"),
                    "application/json",
                )
                return
            if self.command == "GET" and status_path in ("/shelve/latest", "/v1/shelve/latest"):
                shelf = load_shelf("latest")
                if not shelf:
                    self._reply_bytes(404, b'{"error":"no shelf"}\n', "application/json")
                    return
                self._reply_bytes(200, json.dumps(shelf, ensure_ascii=False).encode("utf-8"), "application/json")
                return
            if self.command == "POST" and status_path in ("/shelve", "/v1/shelve"):
                try:
                    body_obj = json.loads(body.decode("utf-8") or "{}") if body else {}
                except (ValueError, UnicodeDecodeError):
                    body_obj = {}
                shelf = create_shelf(
                    task=str(body_obj.get("task") or ""),
                    messages=body_obj.get("messages") if isinstance(body_obj.get("messages"), list) else None,
                    reason=str(body_obj.get("reason") or "manual"),
                    from_model=str(body_obj.get("from_model") or ""),
                    to_model=str(body_obj.get("to_model") or HIGH_CTX_MODEL),
                )
                if body_obj.get("pending", True):
                    set_pending_unshelve(str(shelf["id"]), str(shelf.get("to_model") or HIGH_CTX_MODEL))
                self._reply_bytes(200, json.dumps(shelf, ensure_ascii=False).encode("utf-8"), "application/json")
                return
            if self.command == "POST" and status_path in ("/escalate", "/v1/escalate"):
                try:
                    body_obj = json.loads(body.decode("utf-8") or "{}") if body else {}
                except (ValueError, UnicodeDecodeError):
                    body_obj = {}
                result = escalate(
                    task=str(body_obj.get("task") or ""),
                    messages=body_obj.get("messages") if isinstance(body_obj.get("messages"), list) else None,
                    reason=str(body_obj.get("reason") or "need_higher_context"),
                    from_model=str(body_obj.get("from_model") or ""),
                    to_model=str(body_obj.get("to_model") or HIGH_CTX_MODEL),
                    restart_frontend=bool(body_obj.get("frontend", True)),
                    do_swap=bool(body_obj.get("swap", True)),
                )
                self._reply_bytes(200, json.dumps(result, ensure_ascii=False).encode("utf-8"), "application/json")
                return
            if self.command == "POST" and status_path in ("/unshelve", "/v1/unshelve"):
                text = consume_pending_shelf_prompt() or format_shelf_prompt(load_shelf("latest") or {})
                self._reply_bytes(200, (text or "(empty)\n").encode("utf-8"), "text/plain; charset=utf-8")
                return
            is_models = path_only.rstrip("/").endswith("/models")
            kind = path_kind(path_only)
            is_chat = self.command == "POST" and kind in ("chat", "anthropic", "responses")
            req_obj = None
            want_stream = False
            client_stream = False
            hosted = False
            reply_kind = "chat"

            if is_models and self.command == "GET":
                now = time.monotonic()
                if models_cache["payload"] and now - models_cache["t"] < 5.0:
                    self._reply_bytes(200, models_cache["payload"], "application/json")
                    return
                src = args.models_from or args.remote
                mh, mp, mhttps, mprefix = split_backend(src)
                mconn = (HTTPSConnection if mhttps else HTTPConnection)(mh, port=mp, timeout=10)
                try:
                    mconn.request(
                        "GET",
                        mprefix + "/models",
                        headers={"Host": "%s:%s" % (mh, mp), "Accept": "application/json"},
                    )
                    mres = mconn.getresponse()
                    payload = decorate_models(mres.read())
                    models_cache["t"] = now
                    models_cache["payload"] = payload
                    self._reply_bytes(200, payload, "application/json")
                    return
                except Exception:
                    payload = decorate_models(
                        json.dumps({"object": "list", "data": [{"id": real_model(), "object": "model"}]}).encode("utf-8")
                    )
                    self._reply_bytes(200, payload, "application/json")
                    return
                finally:
                    mconn.close()

            if self.command in ("POST", "PUT") and body:
                body = rewrite_request_model(self.path or "", body)
                if is_chat:
                    try:
                        req_obj = json.loads(body.decode("utf-8"))
                    except (ValueError, UnicodeDecodeError):
                        req_obj = None
                    if isinstance(req_obj, dict):
                        reply_kind = kind or "chat"
                        if kind == "anthropic":
                            req_obj = anthropic_to_openai(req_obj)
                        elif kind == "responses":
                            req_obj = sanitize_chat(req_obj)
                        hosted = is_cursor_openai_client(req_obj)
                        client_stream = bool(req_obj.get("stream")) and kind == "chat"
                        if kind != "chat" or hosted:
                            req_obj["stream"] = False
                        want_stream = client_stream and not hosted
                        log_proxy(
                            "in %s hosted=%s stream=%s msgs=%s tools=%s %s"
                            % (
                                kind,
                                hosted,
                                client_stream,
                                len(req_obj.get("messages") or []),
                                len(req_obj.get("tools") or []),
                                describe_messages(req_obj.get("messages") or []),
                            )
                        )
                        if hosted:
                            req_obj = sanitize_chat(req_obj)
                            req_obj["model"] = real_model()
                        else:
                            req_obj = prepare_request(req_obj)
                            try:
                                forced = synthesize_tool_completion(req_obj)
                                if forced:
                                    payload = to_sse(forced) if want_stream else json.dumps(forced).encode("utf-8")
                                    ctype = "text/event-stream" if want_stream else "application/json"
                                    self._reply_bytes(200, payload, ctype)
                                    return
                                if should_local_loop(req_obj):
                                    result = run_local_loop(req_obj, self._forward_json)
                                    payload = to_sse(result) if want_stream else json.dumps(result).encode("utf-8")
                                    ctype = "text/event-stream" if want_stream else "application/json"
                                    self._reply_bytes(200, payload, ctype)
                                    return
                            except CLIENT_GONE:
                                return
                            except Exception as exc:
                                err = json.dumps(
                                    {
                                        "error": {
                                            "message": "local agent loop failed (%s)" % exc,
                                            "type": "agent_loop_error",
                                        }
                                    }
                                ).encode("utf-8")
                                self._reply_bytes(502, err, "application/json")
                                return
                            req_obj = sanitize_chat(req_obj)
                        req_obj["model"] = real_model()
                        before = len(req_obj.get("messages") or [])
                        try:
                            req_obj = compact_history(req_obj, self._forward_json, real_model())
                        except Exception as exc:
                            log_proxy("compact_history skipped: %s" % exc)
                        after = len(req_obj.get("messages") or [])
                        sys.stderr.write(
                            "compact msgs %s->%s tools=%s\n"
                            % (before, after, len(req_obj.get("tools") or []))
                        )
                        req_obj = fit_vllm_context(req_obj)
                        body = json.dumps(req_obj).encode("utf-8")

            conn_cls = HTTPSConnection if https else HTTPConnection
            conn = conn_cls(b_host, port=b_port, timeout=600)
            try:
                conn.request(self.command, self._upstream_path(), body=body or None, headers=headers)
                res = conn.getresponse()
                if want_stream and is_chat:
                    self._pipe_stream(res)
                    return
                payload = res.read()
                if is_models and payload:
                    payload = decorate_models(payload)
                    models_cache["t"] = time.monotonic()
                    models_cache["payload"] = payload
                elif is_chat and payload:
                    payload = rewrite_chat_model_field(payload)
                if is_chat and req_obj and req_obj.get("tools") and payload:
                    payload = inject_missing_tool_calls(req_obj, payload)
                if is_chat and payload and reply_kind in ("anthropic", "responses") and res.status < 400:
                    try:
                        oa = json.loads(payload.decode("utf-8"))
                        if reply_kind == "anthropic":
                            payload = json.dumps(openai_to_anthropic(oa, real_model())).encode("utf-8")
                        else:
                            payload = json.dumps(openai_to_responses(oa, real_model())).encode("utf-8")
                    except (ValueError, UnicodeDecodeError, TypeError):
                        pass
                ctype = "application/json"
                if hosted and client_stream and is_chat and payload and res.status < 400:
                    try:
                        payload = to_sse(json.loads(payload.decode("utf-8")))
                        ctype = "text/event-stream"
                    except (ValueError, UnicodeDecodeError, TypeError):
                        pass
                else:
                    for k, v in res.getheaders():
                        if k.lower() == "content-type" and v:
                            ctype = v
                            break
                self._reply_bytes(res.status, payload, ctype)
            except CLIENT_GONE:
                return
            except Exception as exc:
                err = json.dumps(
                    {
                        "error": {
                            "message": "vLLM backend unreachable at %s (%s). Start: qudlab vllm serve --model Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"
                            % (args.remote, exc),
                            "type": "backend_error",
                        }
                    }
                ).encode("utf-8")
                self._reply_bytes(502, err, "application/json")
            finally:
                conn.close()

    print("SGLang-style OpenAI frontend  http://%s:%s/v1" % listen, flush=True)
    print("vLLM backend                  %s" % args.remote, flush=True)
    print("status                       http://%s:%s/status" % listen, flush=True)
    print("GPU proxy key file          %s" % key_file, flush=True)
    print("GPU proxy key chars         %s (Bearer / Cursor OpenAI API key)" % len(expected_key), flush=True)
    if key_created:
        print("generated new key           replace dummy local-vllm in Cursor Settings", flush=True)
    print("Cursor Agent                 pass-through (summaries + tools kept)", flush=True)
    print("Cortex/LM Studio loop        only when the client sent no tools", flush=True)
    print("Cursor Models URL            http://%s:%s/v1  (not :8000)" % listen, flush=True)
    httpd = ThreadingHTTPServer(listen, Handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nfrontend stopped", flush=True)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
