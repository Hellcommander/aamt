"""Map Cursor's paid-API shapes onto vLLM /v1/chat/completions.

Cursor Agent already sends OpenAI Chat, Anthropic Messages, or OpenAI
Responses. The frontend must keep the client's messages (including
conversation summaries and tool results) and only rewrite the model id.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid

CHAT_KEYS = {
    "model",
    "messages",
    "tools",
    "tool_choice",
    "temperature",
    "top_p",
    "max_tokens",
    "stream",
    "stop",
    "presence_penalty",
    "frequency_penalty",
    "n",
    "seed",
    "logit_bias",
    "user",
    "logprobs",
    "top_logprobs",
    "response_format",
    "parallel_tool_calls",
}

# SGLang openai-backend workers report this; rewrite, never list it.
FAKE_MODEL_IDS = frozenset({"unknown", "vllm-backend", "vllm", "openai"})
# Do not advertise gpt-4o / Grok / Claude. Cursor owns those names and
# sends them to cloud instead of this proxy.
PAID_MODEL_ALIASES = ()
# Neutral id for Cursor BYOK — avoids Qwen/gpt/claude name collisions.
CURSOR_BYOK_MODEL_ID = "local-qwen-3b"
ADVERTISE_MODEL_IDS = (CURSOR_BYOK_MODEL_ID,)


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, str):
                parts.append(p)
            elif isinstance(p, dict):
                parts.append(str(p.get("text") or p.get("content") or ""))
        return "\n".join(x for x in parts if x)
    return str(content or "")


VLLM_MAX_CTX = int(os.environ.get("QUDLAB_VLLM_MAX_CTX", "65536"))
VLLM_MIN_OUT = 256
VLLM_DEFAULT_OUT = 1024
# Qwen tokenizes code denser than 4 chars/token; 3 is still optimistic, 2.5 is safer.
CHARS_PER_TOKEN = 2
SAFETY_TOKENS = 256

DEFAULT_HF_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"


def _est_tokens(text) -> int:
    n = len(str(text or ""))
    return max(1, (n + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN) if n else 0


def _msg_blob(m: dict) -> str:
    if not isinstance(m, dict):
        return ""
    bits = [_text_of(m.get("content"))]
    if m.get("tool_calls"):
        bits.append(json.dumps(m.get("tool_calls"), ensure_ascii=False))
    if m.get("name"):
        bits.append(str(m.get("name")))
    return "\n".join(x for x in bits if x)


def _est_json(obj) -> int:
    try:
        return _est_tokens(json.dumps(obj, ensure_ascii=False))
    except (TypeError, ValueError):
        return 0


PATH_RE = re.compile(
    r"(?:[A-Za-z]:[\\/]|\\\\)(?:[^\\/:*?\"<>|\r\n]+[\\/])*[^\\/:*?\"<>|\r\n]{1,240}"
    r"|(?:(?:[\w.-]+[\\/])+[\w.-]+\.[A-Za-z0-9]{1,8})"
    r"|(?:[\w.-]+\.(?:cs|py|json|xml|md|ps1|js|ts|tsx|txt|bat|csproj))\b"
)

CACHE_DIR = os.path.join(os.environ.get("LOCALAPPDATA", "."), "QudLab", "cache")
PROXY_LOG = os.environ.get("QUDLAB_PROXY_LOG", os.path.join(CACHE_DIR, "openai-proxy.log"))
INDEX_DIR = os.path.join(CACHE_DIR, "chat-index")


def log_proxy(msg: str) -> None:
    line = time.strftime("%H:%M:%S") + " " + msg + "\n"
    sys.stderr.write(line)
    try:
        os.makedirs(os.path.dirname(PROXY_LOG), exist_ok=True)
        with open(PROXY_LOG, "a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError:
        pass


def _ok_index_path(p: str) -> bool:
    s = str(p or "").strip()
    if len(s) < 8:
        return False
    if s.startswith("\\\\"):
        return s.count("\\") >= 3 and not s.startswith("\\\\n")
    if len(s) >= 4 and s[1:3] in (":\\", ":/"):
        return True
    base = s.replace("\\", "/").rsplit("/", 1)[-1]
    return ("/" in s or "\\" in s) and "." in base


def extract_paths(text: str, limit: int = 50) -> list:
    seen = []
    for m in PATH_RE.finditer(text or ""):
        p = m.group(0).rstrip(".,;:)\"'")
        if not _ok_index_path(p) or p in seen:
            continue
        seen.append(p)
        if len(seen) >= limit:
            break
    return seen


def _slim_params(fn: dict) -> dict:
    params = fn.get("parameters") or fn.get("input_schema") or {}
    if not isinstance(params, dict):
        params = {}
    props_in = params.get("properties") or {}
    slim_props = {}
    if isinstance(props_in, dict):
        for k, v in list(props_in.items())[:16]:
            t = "string"
            if isinstance(v, dict):
                t = v.get("type") or "string"
                if isinstance(t, list):
                    t = t[0] if t else "string"
            slim_props[str(k)] = {"type": t if isinstance(t, str) else "string"}
    out = {"type": "object", "properties": slim_props}
    req = params.get("required") or []
    if isinstance(req, list) and req:
        out["required"] = [str(x) for x in req if str(x) in slim_props][:12]
    return out


def _slim_tools(tools) -> list:
    slim = []
    for t in tools or []:
        if not isinstance(t, dict):
            continue
        fn = t.get("function") if isinstance(t.get("function"), dict) else t
        name = (fn or {}).get("name") if isinstance(fn, dict) else None
        if not name:
            continue
        slim.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": (fn.get("description") or "")[:120],
                    "parameters": _slim_params(fn if isinstance(fn, dict) else {}),
                },
            }
        )
    return slim


def fit_vllm_context(data: dict, max_ctx: int = VLLM_MAX_CTX) -> dict:
    """Keep Cursor Agent prompts under the served max-model-len (default 64k).

    Cursor Agent does not compact BYOK dumps; the proxy still hard-caps here.
    Cursor often sends max_tokens=0 and a prompt larger than the model.
    """
    if not isinstance(data, dict):
        return {}
    data = dict(data)
    raw_out = data.get("max_tokens")
    if raw_out is None:
        raw_out = data.get("max_completion_tokens")
    try:
        out_n = int(raw_out)
    except (TypeError, ValueError):
        out_n = 0
    if out_n < VLLM_MIN_OUT:
        out_n = VLLM_DEFAULT_OUT
    if out_n > 1024:
        out_n = 1024
    data["max_tokens"] = out_n
    data.pop("max_completion_tokens", None)

    input_budget = max(2048, max_ctx - out_n - SAFETY_TOKENS)
    tools = data.get("tools") or []
    if tools:
        slim = _slim_tools(tools)
        if slim:
            data["tools"] = slim
            tools = slim

    messages = list(data.get("messages") or [])
    if not messages:
        return data

    def clip_msg(m: dict, cap_chars: int, keep_tail: bool = False) -> dict:
        m = dict(m)
        text = _text_of(m.get("content"))
        if len(text) <= cap_chars:
            return m
        pin = ""
        paths = extract_paths(text, 40)
        if paths:
            pin = "KNOWN PATHS:\n" + "\n".join(paths) + "\n\n"
        room = max(200, cap_chars - len(pin) - 24)
        if keep_tail:
            m["content"] = pin + "...[truncated]\n" + text[-room:]
        else:
            m["content"] = pin + text[:room] + "\n...[truncated]"
        return m

    def pack(msgs) -> int:
        return _est_json(tools) + sum(_est_tokens(_msg_blob(m)) for m in msgs)

    last = dict(messages[-1])
    last_is_tool = str(last.get("role") or "").lower() == "tool"
    head = []
    mid = messages[:-1]
    if mid and str(messages[0].get("role") or "").lower() == "system":
        head = [dict(messages[0])]
        mid = messages[1:-1]

    kept_mid = []
    for m in reversed(mid):
        trial = head + list(reversed(kept_mid)) + [m, last]
        if pack(trial) <= input_budget:
            kept_mid.append(m)
        else:
            break
    kept_mid.reverse()

    assembled = head + kept_mid + [last]
    while pack(assembled) > input_budget and assembled:
        overflow = pack(assembled) - input_budget
        target = assembled[-1] if len(assembled) == 1 else assembled[0]
        blob = _msg_blob(target)
        cut = max(400, len(blob) - overflow * CHARS_PER_TOKEN - 64)
        if len(blob) <= 500:
            if len(assembled) > 1 and assembled[0] is not last:
                assembled.pop(0)
                if head and assembled and assembled[0] is not last:
                    head = [assembled[0]] if str(assembled[0].get("role")) == "system" else []
                continue
            target["content"] = _text_of(target.get("content"))[:400] + "\n...[truncated]"
            break
        idx = assembled.index(target)
        assembled[idx] = clip_msg(
            target,
            cut,
            keep_tail=str(target.get("role") or "").lower() == "tool",
        )
        if head and assembled[0] is assembled[idx]:
            head = [assembled[0]]
        if assembled[-1] is assembled[idx]:
            last = assembled[-1]
        if pack(assembled) <= input_budget:
            break
        if len(assembled) > 2:
            # drop oldest non-system, non-last
            drop_at = 1 if str(assembled[0].get("role") or "").lower() == "system" else 0
            if drop_at < len(assembled) - 1:
                assembled.pop(drop_at)
                continue
        break

    if pack(assembled) > input_budget:
        data["max_tokens"] = VLLM_MIN_OUT
        input_budget = max(2048, max_ctx - VLLM_MIN_OUT - SAFETY_TOKENS)
        last = clip_msg(
            assembled[-1],
            max(800, input_budget * CHARS_PER_TOKEN // 2),
            keep_tail=last_is_tool,
        )
        assembled = ([assembled[0]] if str(assembled[0].get("role") or "").lower() == "system" and len(assembled) > 1 else []) + [last]
        while pack(assembled) > input_budget:
            last = clip_msg(
                assembled[-1],
                max(200, len(_text_of(assembled[-1].get("content"))) // 2),
                keep_tail=last_is_tool,
            )
            assembled[-1] = last
            if len(_text_of(last.get("content"))) < 200:
                break

    data["messages"] = assembled
    try:
        from shelve_context import maybe_shelve_overflow

        est = pack(assembled)
        shelf = maybe_shelve_overflow(
            assembled,
            est_tokens=est,
            max_ctx=max_ctx,
            model=str(data.get("model") or ""),
            task="",
        )
        if shelf:
            note = (
                "\n\n[QUDLAB] Context pressure — shelved id=%s. "
                "Escalate: qudlab vllm escalate  (or GUI Escalate context). "
                "Next turn after swap will unshelve automatically."
                % shelf.get("id")
            )
            # Attach to last user/system so the agent/UI sees it.
            last_m = assembled[-1]
            role = str(last_m.get("role") or "").lower()
            if role == "user":
                last_m = dict(last_m)
                last_m["content"] = _text_of(last_m.get("content")) + note
                assembled[-1] = last_m
                data["messages"] = assembled
            log_proxy("auto-shelved id=%s est=%s max_ctx=%s" % (shelf.get("id"), est, max_ctx))
    except Exception as exc:
        log_proxy("auto-shelve skipped: %s" % exc)
    return data


USER_QUERY_RE = re.compile(r"<user_query>\s*(.*?)\s*</user_query>", re.S | re.I)
PATH_TAG_RE = re.compile(
    r"<path>\s*([^<]{3,400})\s*</path>"
    r"|<(?:file(?:_contents)?|code_selection)[^>]*\bpath=\"([^\"]+)\"",
    re.I,
)
WORKSPACE_RE = re.compile(
    r"(?im)Workspace Paths?:\s*((?:\n-\s*.+)+)"
)
ERROR_LINE_RE = re.compile(
    r"(?im)^.*(?:\berror\b|\bexception\b|traceback|failed|CS\d{4}|\bnot found\b).{0,180}$"
)


def describe_messages(msgs) -> str:
    bits = []
    for m in msgs or []:
        role = str((m or {}).get("role") or "?")
        bits.append("%s:%s" % (role, len(_msg_blob(m))))
    return ",".join(bits) or "none"


def extract_user_task(text: str) -> str:
    found = USER_QUERY_RE.findall(text or "")
    if found:
        return "\n\n".join(x.strip() for x in found if x.strip())
    return ""


def extract_tagged_paths(text: str) -> list:
    out = []
    for m in PATH_TAG_RE.finditer(text or ""):
        p = (m.group(1) or m.group(2) or "").strip()
        if p and p not in out:
            out.append(p)
    return out


def extract_workspaces(text: str) -> list:
    out = []
    m = WORKSPACE_RE.search(text or "")
    block = m.group(1) if m else (text or "")
    for line in block.splitlines():
        s = line.strip().lstrip("-").strip()
        if len(s) > 4 and (s[1:3] in (":\\", ":/") or s.startswith("\\\\")):
            if s not in out:
                out.append(s)
    return out[:12]


def _tool_args(call: dict) -> dict:
    fn = (call or {}).get("function") if isinstance(call, dict) else {}
    raw = (fn or {}).get("arguments") if isinstance(fn, dict) else ""
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError):
        return {}


def _uniq(seq, limit: int) -> list:
    seen = []
    for x in seq or []:
        s = str(x or "").strip()
        if not s or s in seen:
            continue
        seen.append(s)
        if len(seen) >= limit:
            break
    return seen


def empty_index() -> dict:
    return {
        "id": "",
        "updated": 0,
        "workspaces": [],
        "queries": [],
        "files": {},
        "tools": [],
        "errors": [],
        "narrative": "",
    }


def _mark_file(files: dict, path: str, flag: str) -> None:
    p = str(path or "").strip()
    if not _ok_index_path(p):
        return
    rec = files.setdefault(p, {"flags": []})
    if flag not in rec["flags"]:
        rec["flags"].append(flag)


def build_chat_index(messages: list) -> dict:
    """Programmatic codex: paths, tasks, tool log, errors. No LLM required."""
    idx = empty_index()
    files = idx["files"]
    for m in messages or []:
        if not isinstance(m, dict):
            continue
        role = str(m.get("role") or "").lower()
        text = _text_of(m.get("content"))
        blob = _msg_blob(m)
        for q in USER_QUERY_RE.findall(text):
            q = " ".join(q.split())
            if q and q not in idx["queries"]:
                idx["queries"].append(q)
        for ws in extract_workspaces(text):
            if ws not in idx["workspaces"]:
                idx["workspaces"].append(ws)
        for p in extract_tagged_paths(blob) + extract_paths(blob):
            _mark_file(files, p, "mentioned")
        for call in m.get("tool_calls") or []:
            if not isinstance(call, dict):
                continue
            fn = call.get("function") or {}
            name = str((fn or {}).get("name") or call.get("name") or "tool")
            args = _tool_args(call)
            path = str(
                args.get("path")
                or args.get("target_file")
                or args.get("file_path")
                or args.get("target_directory")
                or ""
            )
            flag = "edited" if name in ("StrReplace", "Write", "Delete") else "read"
            if name in ("Grep", "Glob", "Read", "ReadLints"):
                flag = "read"
            if path:
                _mark_file(files, path, flag)
            short = path or str(args.get("pattern") or args.get("command") or "")[:120]
            idx["tools"].append("%s %s" % (name, short))
        if role == "tool":
            for p in extract_tagged_paths(text) + extract_paths(text):
                _mark_file(files, p, "read")
            for line in ERROR_LINE_RE.findall(text or ""):
                s = " ".join(line.split())
                if s and s not in idx["errors"] and "never say a file" not in s.lower():
                    idx["errors"].append(s[:220])
                    if len(idx["errors"]) >= 12:
                        break
    idx["workspaces"] = _uniq(idx["workspaces"], 8)
    idx["queries"] = _uniq(idx["queries"], 12)
    idx["tools"] = idx["tools"][-24:]
    idx["errors"] = _uniq(idx["errors"], 10)
    if len(files) > 60:
        keep = list(files.keys())[-60:]
        idx["files"] = {k: files[k] for k in keep}
    return idx


def merge_chat_index(old: dict, new: dict) -> dict:
    out = empty_index()
    if not isinstance(old, dict):
        old = empty_index()
    if not isinstance(new, dict):
        new = empty_index()
    out["workspaces"] = _uniq(list(old.get("workspaces") or []) + list(new.get("workspaces") or []), 8)
    out["queries"] = _uniq(list(old.get("queries") or []) + list(new.get("queries") or []), 12)
    out["errors"] = _uniq(list(old.get("errors") or []) + list(new.get("errors") or []), 10)
    out["tools"] = list(old.get("tools") or []) + list(new.get("tools") or [])
    out["tools"] = out["tools"][-24:]
    files = {}
    for src in (old.get("files") or {}, new.get("files") or {}):
        if not isinstance(src, dict):
            continue
        for path, rec in src.items():
            if not _ok_index_path(path):
                continue
            flags = list((files.get(path) or {}).get("flags") or [])
            extra = rec.get("flags") if isinstance(rec, dict) else []
            for f in extra or []:
                if f not in flags:
                    flags.append(f)
            files[path] = {"flags": flags}
    if len(files) > 60:
        files = {k: files[k] for k in list(files.keys())[-60:]}
    out["files"] = files
    out["narrative"] = new.get("narrative") or old.get("narrative") or ""
    return out


def index_slug(idx: dict) -> str:
    ws = ((idx.get("workspaces") or ["workspace"])[0] if idx else "workspace")
    safe = re.sub(r"[^A-Za-z0-9]+", "-", str(ws)).strip("-")[:72] or "workspace"
    return safe.lower()


def load_chat_index(slug: str) -> dict:
    path = os.path.join(INDEX_DIR, slug + ".json")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else empty_index()
    except (OSError, ValueError, TypeError):
        return empty_index()


def save_chat_index(idx: dict) -> dict:
    idx = dict(idx or empty_index())
    idx["updated"] = int(time.time())
    slug = index_slug(idx)
    idx["id"] = slug
    try:
        os.makedirs(INDEX_DIR, exist_ok=True)
        raw = json.dumps(idx, ensure_ascii=False, indent=2)
        with open(os.path.join(INDEX_DIR, slug + ".json"), "w", encoding="utf-8") as fh:
            fh.write(raw)
        with open(os.path.join(INDEX_DIR, "latest.json"), "w", encoding="utf-8") as fh:
            fh.write(raw)
        md = format_chat_index(idx)
        with open(os.path.join(INDEX_DIR, "latest.md"), "w", encoding="utf-8") as fh:
            fh.write(md)
        with open(os.path.join(INDEX_DIR, slug + ".md"), "w", encoding="utf-8") as fh:
            fh.write(md)
    except OSError as exc:
        log_proxy("chat-index save failed: %s" % exc)
    return idx


def persist_chat_index(fresh: dict) -> dict:
    slug = index_slug(fresh)
    merged = merge_chat_index(load_chat_index(slug), fresh)
    return save_chat_index(merged)


def format_chat_index(idx: dict) -> str:
    """Short block the 3B can keep in context and look up paths from."""
    if not isinstance(idx, dict):
        return ""
    lines = [
        "CHAT INDEX - look up files and prior turns here. Call Read/Grep on listed paths.",
        "Do not say a file is missing if it is listed. Index id: " + str(idx.get("id") or "latest") + ".",
    ]
    if idx.get("workspaces"):
        lines.append("workspaces:")
        for ws in idx["workspaces"][:6]:
            lines.append("- " + ws)
    if idx.get("queries"):
        lines.append("user_queries:")
        for i, q in enumerate(idx["queries"][-8:], 1):
            lines.append("%s. %s" % (i, q[:240]))
    files = idx.get("files") or {}
    if files:
        lines.append("files:")
        for path, rec in list(files.items())[-40:]:
            flags = ",".join((rec or {}).get("flags") or []) or "mentioned"
            lines.append("- %s [%s]" % (path, flags))
    if idx.get("tools"):
        lines.append("recent_tools:")
        for t in idx["tools"][-12:]:
            lines.append("- " + str(t)[:200])
    if idx.get("errors"):
        lines.append("errors:")
        for e in idx["errors"][-6:]:
            lines.append("- " + e)
    if idx.get("narrative"):
        lines.append("narrative:\n" + str(idx["narrative"])[:1200])
    text = "\n".join(lines)
    if len(text) > 3500:
        text = text[:3400] + "\n...[index truncated]"
    return text


def read_latest_index() -> dict:
    return load_chat_index("latest") if os.path.isfile(os.path.join(INDEX_DIR, "latest.json")) else empty_index()


_AGENT_PATTERNS_CACHE = {"t": 0.0, "text": "", "n": 0}


def cursor_projects_root() -> str:
    return os.path.join(os.path.expanduser("~"), ".cursor", "projects")


def _walk_agent_jsonl(root: str, found: list) -> None:
    try:
        entries = os.listdir(root)
    except OSError:
        return
    for name in entries:
        path = os.path.join(root, name)
        if name == "subagents":
            continue
        if os.path.isdir(path):
            _walk_agent_jsonl(path, found)
        elif name.endswith(".jsonl"):
            try:
                found.append((os.path.getmtime(path), path))
            except OSError:
                pass


def list_agent_transcripts(limit: int = 12) -> list:
    root = cursor_projects_root()
    found: list = []
    try:
        projects = os.listdir(root)
    except OSError:
        return []
    for proj in projects:
        _walk_agent_jsonl(os.path.join(root, proj, "agent-transcripts"), found)
    found.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in found[:limit]]


def _jsonl_part_text(part) -> str:
    if not isinstance(part, dict):
        return ""
    t = str(part.get("type") or "")
    if t in ("text", "thinking", "reasoning", "redacted_thinking"):
        return str(part.get("text") or part.get("thinking") or part.get("content") or "")
    return ""


def _jsonl_tool_line(part: dict) -> str:
    name = str(part.get("name") or "tool")
    inp = part.get("input") if isinstance(part.get("input"), dict) else {}
    bits = []
    for key in ("path", "target_directory", "glob_pattern", "pattern", "query", "command", "file_path"):
        if key in inp and inp[key] is not None:
            bits.append("%s=%s" % (key, str(inp[key])[:160]))
            if len(bits) >= 2:
                break
    if not bits and inp:
        # first short arg
        for k, v in list(inp.items())[:2]:
            bits.append("%s=%s" % (k, str(v)[:120]))
    return name + ("(" + ", ".join(bits) + ")" if bits else "()")


def extract_agent_patterns(path: str, max_turns: int = 5, max_chars: int = 2200) -> str:
    """Pull user queries + plan text + tool_use from a Cursor agent JSONL.

    Private chain-of-thought is usually absent from these files; the visible
    plan sentence before tools is the usable 'thinking' pattern for a 3B.
    """
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return ""
    turns = []
    pending_user = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except (ValueError, TypeError):
            continue
        role = str(ev.get("role") or "")
        msg = ev.get("message") if isinstance(ev.get("message"), dict) else {}
        content = msg.get("content")
        if role == "user":
            text = ""
            if isinstance(content, list):
                text = "\n".join(_jsonl_part_text(p) for p in content if isinstance(p, dict))
            elif isinstance(content, str):
                text = content
            m = USER_QUERY_RE.search(text or "")
            pending_user = " ".join((m.group(1) if m else text).split())[:280]
            continue
        if role != "assistant":
            continue
        plan = ""
        tools = []
        thinking = ""
        if isinstance(content, list):
            for part in content:
                if not isinstance(part, dict):
                    continue
                t = str(part.get("type") or "")
                if t in ("thinking", "reasoning", "redacted_thinking"):
                    chunk = _jsonl_part_text(part).strip()
                    if chunk and not thinking:
                        thinking = " ".join(chunk.split())[:400]
                elif t == "text":
                    chunk = _jsonl_part_text(part).strip()
                    if chunk and not plan:
                        plan = " ".join(chunk.split())[:320]
                elif t == "tool_use":
                    tools.append(_jsonl_tool_line(part))
        if not tools and not plan and not thinking:
            continue
        block = []
        if pending_user:
            block.append("user: " + pending_user)
            pending_user = ""
        if thinking:
            block.append("thinking: " + thinking)
        if plan:
            block.append("plan: " + plan)
        if tools:
            block.append("tools: " + "; ".join(tools[:8]))
        turns.append("\n".join(block))
    if not turns:
        return ""
    # Prefer recent tool-using turns (patterns to follow).
    chosen = turns[-max_turns:]
    out = "--- from " + os.path.basename(path) + " ---\n" + "\n\n".join(chosen)
    if len(out) > max_chars:
        # Keep newest complete turns, not a mid-line clip.
        while len(chosen) > 1 and len("\n\n".join(chosen)) > max_chars - 80:
            chosen = chosen[1:]
        out = "--- from " + os.path.basename(path) + " ---\n" + "\n\n".join(chosen)
        if len(out) > max_chars:
            out = out[: max_chars - 20] + "\n...[truncated]"
    return out


def load_prior_agent_patterns(task: str = "", workspaces=None, max_chars: int = 2800) -> str:
    """Always-on exemplars from disk agent transcripts (not a fake SUMMARY)."""
    now = time.monotonic()
    task_l = (task or "").lower()
    tokens = [w for w in re.split(r"[^a-z0-9_.-]+", task_l) if len(w) >= 4][:10]
    ws_bits = [str(w).lower() for w in (workspaces or []) if w]
    cache_key = "|".join(tokens[:6] + ws_bits[:3])
    if (
        _AGENT_PATTERNS_CACHE.get("key") == cache_key
        and _AGENT_PATTERNS_CACHE["text"]
        and now - float(_AGENT_PATTERNS_CACHE["t"]) < 20.0
    ):
        return str(_AGENT_PATTERNS_CACHE["text"])[:max_chars]

    paths = list_agent_transcripts(16)
    if not paths:
        return ""

    def score(p: str) -> int:
        s = 0
        pl = p.lower().replace("\\", "/")
        for ws in ws_bits:
            slug = re.sub(r"[^a-z0-9]+", "-", ws.lower()).strip("-")
            if slug and slug in pl:
                s += 5
        if "tools-qud" in pl or "cavesofqud" in pl or "ai-assisted-toolkit" in pl:
            s += 2
        if tokens:
            try:
                # Cheap: title/snippet from path + last 40KB
                with open(p, "rb") as fh:
                    fh.seek(0, os.SEEK_END)
                    size = fh.tell()
                    fh.seek(max(0, size - 40000))
                    tail = fh.read().decode("utf-8", "replace").lower()
                hits = sum(1 for t in tokens if t in tail)
                s += hits
            except OSError:
                pass
        return s

    ranked = sorted(paths, key=score, reverse=True)
    chunks = []
    total = 0
    used = 0
    for p in ranked[:4]:
        block = extract_agent_patterns(p, max_turns=4, max_chars=1200)
        if not block:
            continue
        if total + len(block) > max_chars and chunks:
            break
        chunks.append(block)
        total += len(block)
        used += 1
    text = ""
    if chunks:
        text = (
            "PRIOR AGENT PATTERNS — copy this style. "
            "Short plan, then call tools (Read/Grep/Glob/Shell). "
            "Do not lecture; do not invent missing files.\n\n"
            + "\n\n".join(chunks)
        )
    _AGENT_PATTERNS_CACHE["t"] = now
    _AGENT_PATTERNS_CACHE["text"] = text
    _AGENT_PATTERNS_CACHE["n"] = used
    _AGENT_PATTERNS_CACHE["key"] = cache_key
    if text:
        log_proxy("agent-patterns files=%s chars=%s" % (used, len(text)))
    return text[:max_chars]


def tool_name_list(tools) -> list:
    names = []
    for t in tools or []:
        if not isinstance(t, dict):
            continue
        fn = t.get("function") if isinstance(t.get("function"), dict) else t
        n = (fn or {}).get("name") if isinstance(fn, dict) else None
        if n:
            names.append(str(n))
    return names


def _transcript_line(m: dict) -> str:
    role = str(m.get("role") or "?")
    text = _text_of(m.get("content"))
    if m.get("tool_calls"):
        names = []
        for c in m.get("tool_calls") or []:
            if isinstance(c, dict):
                fn = c.get("function") or {}
                names.append(str(fn.get("name") or c.get("name") or "tool"))
        text = (text + "\n[tool_calls: " + ", ".join(names) + "]").strip()
    if len(text) > 1500:
        text = text[:1500] + "\n...[truncated]"
    return role.upper() + ":\n" + text


def _live_tail(messages: list) -> tuple:
    """Keep the current user turn (or tool-call pair). Compact the rest."""
    if not messages:
        return [], []
    last = dict(messages[-1])
    role = str(last.get("role") or "").lower()
    if role == "tool" and len(messages) >= 2:
        return list(messages[:-2]), [dict(messages[-2]), last]
    return list(messages[:-1]), [last]


def _is_cursor_dump(messages: list, tools) -> bool:
    names = set(tool_name_list(tools))
    if names & {"Read", "Grep", "Glob", "Shell", "StrReplace"}:
        return True
    if messages and str(messages[0].get("role") or "").lower() == "system":
        return len(_text_of(messages[0].get("content"))) > 1500
    return False


def _llm_summarize(forward_json, model: str, blob: str) -> str:
    """Always ask vLLM to summarize; chunk if the dump is bigger than one pass."""
    blob = (blob or "").strip()
    if not blob or not callable(forward_json):
        return ""
    step = 10000
    chunks = []
    for i in range(0, len(blob), step):
        chunks.append(blob[i : i + step])
        if len(chunks) >= 4:
            break
    sys_prompt = (
        "Compress this coding-agent transcript for a small context window. "
        "KEEP: user task, file paths, errors/CS codes, decisions, open TODOs. "
        "SUMMARIZE or DROP: long lectures, repeated tool dumps, fluff, greetings. "
        "250 words max. No tools. Never invent missing files."
    )
    pieces = []
    for i, chunk in enumerate(chunks):
        try:
            out = forward_json(
                {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": chunk},
                    ],
                    "max_tokens": 400,
                    "temperature": 0.1,
                    "stream": False,
                }
            )
            text = _text_of(((out.get("choices") or [{}])[0].get("message") or {}).get("content")).strip()
            if text:
                pieces.append(text)
                log_proxy("compact llm chunk %s/%s chars=%s" % (i + 1, len(chunks), len(text)))
        except Exception as exc:
            log_proxy("compact llm chunk %s failed: %s" % (i + 1, exc))
            pieces.append(chunk[:800])
    if not pieces:
        return ""
    merged = "\n\n".join(pieces)
    if len(pieces) == 1:
        return merged
    try:
        out = forward_json(
            {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Merge these chunk summaries into one. Keep every file path "
                            "and the user's task. 300 words. Never say a file was not found."
                        ),
                    },
                    {"role": "user", "content": merged[:12000]},
                ],
                "max_tokens": 450,
                "temperature": 0.1,
                "stream": False,
            }
        )
        text = _text_of(((out.get("choices") or [{}])[0].get("message") or {}).get("content")).strip()
        if text:
            log_proxy("compact llm merge chars=%s" % len(text))
            return text
    except Exception as exc:
        log_proxy("compact llm merge failed: %s" % exc)
    return merged[:2500]


def compact_history(data: dict, forward_json, model: str) -> dict:
    """Replace Cursor's uncompacted BYOK dump with task + paths + a short summary.

    Cursor Agent does not summarize. First turns are 1–2 huge messages (system
    dump + user XML), so turn-count gates never fire. We always rebuild those.
    """
    if not isinstance(data, dict):
        return data
    messages = list(data.get("messages") or [])
    if not messages:
        return data
    tools = data.get("tools") or []
    older, live = _live_tail(messages)
    last = dict(live[-1])
    last_role = str(last.get("role") or "").lower()
    last_text = _text_of(last.get("content"))
    all_text = "\n".join(_msg_blob(m) for m in messages)
    paths = extract_tagged_paths(all_text) + extract_paths(all_text)
    seen = []
    for p in paths:
        if p not in seen:
            seen.append(p)
    paths = seen[:50]
    task = extract_user_task(all_text)
    if not task and last_role == "user" and len(last_text) < 4000:
        task = last_text.strip()
    idx = persist_chat_index(build_chat_index(messages))
    if task and task not in (idx.get("queries") or []):
        idx["queries"] = _uniq(list(idx.get("queries") or []) + [task], 12)
        idx = save_chat_index(idx)
    total = _est_json(messages) + _est_json(tools)
    dump = _is_cursor_dump(messages, tools)
    oversized = (
        dump
        or total >= 4000
        or len(last_text) > 4000
        or any(len(_msg_blob(m)) > 8000 for m in older)
    )
    if not oversized:
        log_proxy(
            "compact skip msgs=%s est=%s paths=%s index=%s %s"
            % (len(messages), total, len(idx.get("files") or {}), idx.get("id"), describe_messages(messages))
        )
        return data

    work_msgs = [
        m
        for m in older
        if str(m.get("role") or "").lower() in ("assistant", "tool", "user") or m.get("tool_calls")
    ]
    work_msgs = [
        m
        for m in work_msgs
        if not (
            str(m.get("role") or "").lower() == "system"
            and len(_text_of(m.get("content"))) > 1500
        )
    ]
    # Real prior work = assistant/tool turns. A lone new user prompt is not "history".
    prior_work = [
        m
        for m in work_msgs
        if str(m.get("role") or "").lower() in ("assistant", "tool") or m.get("tool_calls")
    ]
    has_prior = len(prior_work) > 0

    summary = ""
    if has_prior and callable(forward_json):
        to_summarize = "\n\n".join(_transcript_line(m) for m in work_msgs)
        if last_role == "user":
            head = last_text if len(last_text) <= 5000 else (last_text[:2500] + "\n...\n" + last_text[-1500:])
            to_summarize = (to_summarize + "\n\nCURRENT USER:\n" + head).strip()
        if task:
            to_summarize = ("USER TASK:\n" + task[:2000] + "\n\n" + to_summarize).strip()
        if paths:
            to_summarize = ("PATHS:\n" + "\n".join(paths[:40]) + "\n\n" + to_summarize).strip()
        summary = _llm_summarize(forward_json, model, to_summarize)
        if not summary and to_summarize:
            summary = to_summarize[:1500]
            log_proxy("compact llm empty; using transcript clip")
        if summary:
            idx["narrative"] = summary
            idx = save_chat_index(idx)
    else:
        log_proxy(
            "compact no-summary (nothing to summarize) msgs=%s prior=%s task=%s paths=%s"
            % (len(messages), len(prior_work), "yes" if task else "no", len(paths))
        )

    names = tool_name_list(tools)
    parts = [
        "You are Cursor's coding agent on a small local model. "
        "You cannot run the big AI toolset (Task/subagents/ollama-suggest). "
        "For CoQ mods under LocalLow/Workshop: Shell-run ApiMigrate-Compact.ps1, then compile diagnostics, then Read/Grep only listed paths. "
        "Call a tool before talking about files. "
        "Never say a file was not found until a tool result said so. "
        "Never ask the user to re-provide a path listed below. "
        "Available tools: " + (", ".join(names[:24]) or "Read, Grep, Glob, Shell") + ". "
        "Start with Shell ApiMigrate-Compact or Read/Grep on a path from CHAT INDEX or USER TASK.",
    ]
    index_block = format_chat_index(idx)
    # First turn: keep index lean — paths/task only, no fake narrative.
    if not has_prior and idx.get("narrative"):
        idx = dict(idx)
        idx["narrative"] = ""
        index_block = format_chat_index(idx)
    if index_block.strip():
        parts.append(index_block)
    if task:
        parts.append("USER TASK:\n" + task[:4000])
    unshelved = ""
    try:
        from shelve_context import consume_pending_shelf_prompt

        unshelved = consume_pending_shelf_prompt(max_chars=10000) or ""
        if unshelved:
            parts.append(unshelved)
    except Exception as exc:
        log_proxy("unshelve skipped: %s" % exc)
    # Prior Cursor agent chats (plan + tools). Not a SUMMARY of an empty turn —
    # these are exemplars so the 3B has patterns to follow.
    patterns = load_prior_agent_patterns(task=task or "", workspaces=idx.get("workspaces") or [])
    if patterns:
        parts.append(patterns)
    if summary:
        parts.append("SUMMARY:\n" + summary)
    elif not has_prior and not unshelved:
        parts.append(
            "No prior turns in THIS chat to summarize. "
            "Follow PRIOR AGENT PATTERNS above; call tools the same way."
        )

    # Worst-case: drop / shrink low-value blocks so task+paths+errors survive.
    parts = _shrink_compact_parts(parts, hard_chars=14000)

    if last_role == "user":
        last = {
            "role": "user",
            "content": (task or last_text[:3500]) or "Continue. Call Read on a file in CHAT INDEX.",
        }
    elif len(last_text) > 6000:
        last = dict(last)
        last["content"] = last_text[:3000] + "\n...[truncated]\n" + last_text[-2000:]

    compacted = [{"role": "system", "content": "\n\n".join(parts)}]
    if live and str(live[0].get("role") or "").lower() == "assistant" and live[0].get("tool_calls"):
        compacted.append(live[0])
        compacted.append(last)
    else:
        compacted.append(last)
    data = dict(data)
    if last_role == "user" and tools:
        data["tool_choice"] = "required"
    data["messages"] = compacted
    log_proxy(
            "compacted msgs %s->%s est=%s files=%s summary=%s index=%s %s"
            % (
                len(messages),
                len(compacted),
                total,
                len(idx.get("files") or {}),
                "yes" if summary else "no",
                idx.get("id"),
                describe_messages(compacted),
            )
    )
    return data


def _shrink_compact_parts(parts: list, hard_chars: int = 14000) -> list:
    """Drop least-important system blocks first; summarize fat ones."""
    if not parts:
        return parts
    parts = list(parts)
    total = sum(len(p) for p in parts)
    if total <= hard_chars:
        return parts

    def kind(p: str) -> str:
        if p.startswith("PRIOR AGENT PATTERNS"):
            return "patterns"
        if p.startswith("SUMMARY:"):
            return "summary"
        if p.startswith("SHELVED CONTEXT"):
            return "shelf"
        if p.startswith("CHAT INDEX"):
            return "index"
        if p.startswith("USER TASK:"):
            return "task"
        if p.startswith("You are Cursor"):
            return "sys"
        return "other"

    # 1) Drop patterns entirely (exemplars are nice-to-have).
    parts = [p for p in parts if kind(p) != "patterns"]
    total = sum(len(p) for p in parts)
    if total <= hard_chars:
        log_proxy("compact shrink: dropped PRIOR AGENT PATTERNS")
        return parts

    # 2) Summarize SUMMARY / shelf / other fat blocks programmatically.
    try:
        from shelve_context import summarize_low_value_text
    except Exception:
        summarize_low_value_text = lambda s, m=900: (s[:m] if s else "")  # noqa: E731

    new_parts = []
    for p in parts:
        k = kind(p)
        if k in ("summary", "shelf", "other") and len(p) > 1200:
            head = p.split("\n", 1)[0]
            body = p.split("\n", 1)[1] if "\n" in p else p
            new_parts.append(head + "\n" + summarize_low_value_text(body, 700))
        elif k == "index" and len(p) > 2500:
            # Keep file lines; drop long narrative inside index.
            lines = p.split("\n")
            keep = []
            for line in lines:
                if line.startswith("narrative:"):
                    break
                keep.append(line)
                if len(keep) >= 55:
                    break
            new_parts.append("\n".join(keep))
        else:
            new_parts.append(p)
    parts = new_parts
    total = sum(len(p) for p in parts)
    if total <= hard_chars:
        log_proxy("compact shrink: summarized low-value blocks chars=%s" % total)
        return parts

    # 3) Keep sys + task + index (+ shelf if present); drop the rest.
    priority = {"sys": 0, "task": 1, "index": 2, "shelf": 3, "summary": 4, "other": 5}
    ranked = sorted(parts, key=lambda p: priority.get(kind(p), 9))
    kept = []
    size = 0
    for p in ranked:
        if kind(p) in ("sys", "task", "index") or size + len(p) <= hard_chars:
            kept.append(p)
            size += len(p)
        if size >= hard_chars:
            break
    # Restore roughly original order among kept
    order = {id(p): i for i, p in enumerate(parts)}
    kept.sort(key=lambda p: order.get(id(p), 99))
    log_proxy("compact shrink: hard-trim kept=%s chars=%s" % (len(kept), size))
    return kept


def sanitize_chat(data: dict) -> dict:
    """Keep conversation + tools; drop vendor fields vLLM 400s on."""
    if not isinstance(data, dict):
        return {}
    out = {k: data[k] for k in CHAT_KEYS if k in data}
    if "max_tokens" not in out and data.get("max_completion_tokens"):
        out["max_tokens"] = data["max_completion_tokens"]
    if "messages" not in out and data.get("input") is not None:
        out["messages"] = responses_input_to_messages(data.get("input"), data.get("instructions"))
    return out


def anthropic_to_openai(body: dict) -> dict:
    messages = []
    system = body.get("system")
    if system:
        messages.append({"role": "system", "content": _text_of(system)})
    for m in body.get("messages") or []:
        if not isinstance(m, dict):
            continue
        role = str(m.get("role") or "user")
        content = m.get("content")
        if isinstance(content, str):
            messages.append({"role": role, "content": content})
            continue
        texts = []
        tool_calls = []
        if isinstance(content, list):
            for p in content:
                if not isinstance(p, dict):
                    continue
                kind = p.get("type")
                if kind in (None, "text"):
                    texts.append(p.get("text") or "")
                elif kind == "tool_use":
                    tool_calls.append(
                        {
                            "id": p.get("id") or ("call_" + uuid.uuid4().hex[:12]),
                            "type": "function",
                            "function": {
                                "name": p.get("name"),
                                "arguments": json.dumps(p.get("input") or {}),
                            },
                        }
                    )
                elif kind == "tool_result":
                    raw = p.get("content")
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": p.get("tool_use_id") or "",
                            "content": raw if isinstance(raw, str) else _text_of(raw),
                        }
                    )
        msg = {"role": role, "content": "\n".join(t for t in texts if t) or None}
        if tool_calls:
            msg["tool_calls"] = tool_calls
            if not msg.get("content"):
                msg["content"] = None
        if msg.get("content") or msg.get("tool_calls"):
            messages.append(msg)
    tools = []
    for t in body.get("tools") or []:
        if not isinstance(t, dict):
            continue
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": t.get("name"),
                    "description": t.get("description") or "",
                    "parameters": t.get("input_schema") or t.get("parameters") or {"type": "object", "properties": {}},
                },
            }
        )
    out = {
        "model": body.get("model"),
        "messages": messages,
        "max_tokens": body.get("max_tokens") or 2048,
        "stream": bool(body.get("stream")),
        "temperature": body.get("temperature", 0.2),
    }
    if tools:
        out["tools"] = tools
    if body.get("tool_choice"):
        out["tool_choice"] = body["tool_choice"]
    return out


def openai_to_anthropic(oa: dict, model: str) -> dict:
    msg = ((oa.get("choices") or [{}])[0].get("message")) or {}
    content = []
    text = msg.get("content")
    if text:
        content.append({"type": "text", "text": text})
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or {}
        try:
            inp = json.loads(fn.get("arguments") or "{}")
        except (ValueError, TypeError):
            inp = {}
        content.append(
            {
                "type": "tool_use",
                "id": tc.get("id") or ("toolu_" + uuid.uuid4().hex[:12]),
                "name": fn.get("name"),
                "input": inp if isinstance(inp, dict) else {},
            }
        )
    if not content:
        content.append({"type": "text", "text": ""})
    stop = "tool_use" if msg.get("tool_calls") else "end_turn"
    return {
        "id": "msg_" + (oa.get("id") or uuid.uuid4().hex[:12]),
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content,
        "stop_reason": stop,
        "usage": {"input_tokens": 0, "output_tokens": 0},
    }


def responses_input_to_messages(inp, instructions=None) -> list:
    messages = []
    if instructions:
        messages.append({"role": "system", "content": _text_of(instructions)})
    if isinstance(inp, str):
        messages.append({"role": "user", "content": inp})
        return messages
    for item in inp or []:
        if isinstance(item, str):
            messages.append({"role": "user", "content": item})
            continue
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or item.get("type") or "user")
        if role in ("input_text", "message"):
            role = item.get("role") or "user"
        if role == "system" or item.get("type") == "instruction":
            messages.append({"role": "system", "content": _text_of(item.get("content") or item.get("text"))})
            continue
        if item.get("type") == "function_call_output":
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": item.get("call_id") or "",
                    "content": _text_of(item.get("output") or item.get("content")),
                }
            )
            continue
        messages.append({"role": role if role in ("user", "assistant", "system", "tool") else "user", "content": _text_of(item.get("content") or item.get("text"))})
    return messages


def openai_to_responses(oa: dict, model: str) -> dict:
    msg = ((oa.get("choices") or [{}])[0].get("message")) or {}
    output = []
    if msg.get("content"):
        output.append({"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": msg["content"]}]})
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or {}
        output.append(
            {
                "type": "function_call",
                "id": tc.get("id"),
                "call_id": tc.get("id"),
                "name": fn.get("name"),
                "arguments": fn.get("arguments") or "{}",
            }
        )
    return {
        "id": "resp_" + uuid.uuid4().hex[:12],
        "object": "response",
        "created_at": int(time.time()),
        "model": model,
        "status": "completed",
        "output": output,
    }


def path_kind(path: str) -> str:
    p = (path or "").split("?", 1)[0]
    if "chat/completions" in p:
        return "chat"
    if p.rstrip("/").endswith("/messages") or "/v1/messages" in p:
        return "anthropic"
    if "/responses" in p:
        return "responses"
    return ""
