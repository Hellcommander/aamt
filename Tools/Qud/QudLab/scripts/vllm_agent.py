"""Force a local tool loop so Instruct models cannot stay blind in Chat.

The Windows frontend (:30000) tunes vLLM (:8000): aliases, system prompt,
workspace from the Cursor plugin, and synthesized tool calls.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from glob import glob as glob_files

WIN_PATH = re.compile(
    r"[A-Za-z]:[\\/](?:[^\\/:*?\"<>|\r\n]+[\\/])*[^\\/:*?\"<>|\r\n]+"
)
FILE_RE = re.compile(
    r"\b([\w./\\-]+\.(?:js|ts|py|cs|cpp|h|hpp|json|md|xml|ps1|java|dll|exe))\b"
)
TUTOR_SNIPS = (
    "don't have the capability",
    "dont have the capability",
    "cannot directly operate",
    "can't directly operate",
    "i can guide you",
    "here's a brief guide",
    "here's a step-by-step",
    "would you like to proceed",
    "feel free to share",
    "i cannot access",
    "i don't have access",
    "i cannot run tools",
    "file you were trying to locate",
    "provide the path again",
    "confirm the filename",
    "could you please provide",
    "was not found",
    "unable to locate",
    "i don't see any files",
    "i do not see any files",
)
AGENT_SYS = (
    "You are a coding agent, not a tutor. Pipeline: (1) gather with tools, "
    "(2) change only files that exist unless creating a new one, "
    "(3) quote tool results, never invent missing paths. "
    "Keep conversation summaries and prior tool results; continue from them. "
    "Never ask the user to confirm a Windows path that already appears in the message. "
    "Never say a path does not exist unless a tool result said so. "
    "If the user mentions todos, read TODO.md in the last folder. "
    "Do not ask what they want to do with todos. Start with a tool call. "
    "Do not ask clarifying questions when a file path is already given. "
    "Never say you cannot operate Ghidra or the filesystem until a tool result failed."
)

CURSOR_TOOLS = {
    "Read",
    "Grep",
    "Glob",
    "Shell",
    "StrReplace",
    "Write",
    "Delete",
    "ReadLints",
    "WebFetch",
    "WebSearch",
    "Task",
    "AskQuestion",
    "EditNotebook",
    "TodoWrite",
    "SwitchMode",
}

SUMMARY_MARKERS = (
    "conversation summary",
    "summary of the conversation",
    "summary of conversation",
    "prior work",
    "what i've done",
    "what i have done",
    "here's what i've done",
    "here's what i did",
    "<summary>",
    "</summary>",
    "previous conversation",
    "so far i have",
    "in this session",
    "continuing from",
)
LOCAL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file from disk.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List a directory.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "Search file contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                },
                "required": ["pattern"],
            },
        },
    },
]

ALLOWED = (
    os.path.normcase(r"D:\games"),
    os.path.normcase(r"C:\Users\Arend"),
    os.path.normcase(r"D:\decompilers"),
    os.path.normcase(r"D:\tools"),
)


def _norm(p: str) -> str:
    return os.path.normpath(p.strip().strip("\"'`"))


def allowed_path(p: str) -> bool:
    n = os.path.normcase(_norm(p))
    return any(n == a or n.startswith(a + os.sep) for a in ALLOWED)


def message_text(msg: dict) -> str:
    c = msg.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(
            p.get("text", "") if isinstance(p, dict) else str(p) for p in c
        )
    return str(c or "")


def last_user_text(messages: list) -> str:
    chunks = []
    for m in messages:
        if str(m.get("role", "")).lower() == "user":
            chunks.append(message_text(m))
    return "\n".join(chunks)


def qudlab_ctx(data: dict) -> dict:
    q = data.get("qudlab") if isinstance(data, dict) else None
    return q if isinstance(q, dict) else {}


def workspace_of(data: dict) -> str:
    q = qudlab_ctx(data)
    ws = q.get("workspace") or ""
    return _norm(str(ws)) if ws else ""


def wants_tools(text: str) -> bool:
    t = (text or "").lower()
    if WIN_PATH.search(text or "") or FILE_RE.search(text or ""):
        return True
    return any(
        w in t
        for w in (
            "todo",
            "read the",
            "open the",
            "fix",
            "crash",
            ".cpp",
            ".dll",
            "rivet",
            "continue",
            "file",
            "plugin",
            "ghidra",
            "improve",
            "implement",
            "overlay",
            "hook",
            "tool",
            "decompile",
            "patch",
        )
    )


def is_tutor(text: str) -> bool:
    t = (text or "").lower()
    return any(s in t for s in TUTOR_SNIPS)


def resolve_todo(text: str) -> str | None:
    paths = [_norm(p.rstrip(".,);")) for p in WIN_PATH.findall(text or "")]
    if not re.search(r"\btodos?\b", text or "", re.I):
        return None
    for p in reversed(paths):
        if os.path.isdir(p):
            for name in ("TODO.md", "todo.md", "TODO.txt"):
                cand = os.path.join(p, name)
                if os.path.isfile(cand):
                    return cand
        parent = os.path.dirname(p) if os.path.isfile(p) else p
        cand = os.path.join(parent, "TODO.md")
        if os.path.isfile(cand):
            return cand
    return None


def guess_path(text: str, workspace: str = "") -> tuple[str, str] | None:
    todo = resolve_todo(text)
    if todo:
        return "read_file", todo
    paths = [_norm(p.rstrip(".,);")) for p in WIN_PATH.findall(text or "")]
    if paths:
        p = paths[-1]
        if os.path.isdir(p):
            return "list_dir", p
        return "read_file", p
    names = FILE_RE.findall(text or "")
    ws = _norm(workspace) if workspace else ""
    for n in reversed(names):
        cand = n if os.path.isabs(n) else (os.path.join(ws, n) if ws else n)
        cand = _norm(cand)
        if os.path.isfile(cand):
            return "read_file", cand
        if ws and os.path.isdir(ws):
            hits = glob_files(os.path.join(ws, "**", os.path.basename(n)), recursive=True)
            if hits:
                return "read_file", hits[0]
    if ws and os.path.isdir(ws):
        return "list_dir", ws
    return None


def keyword(text: str) -> str:
    stop = {
        "this", "that", "with", "from", "have", "want", "please", "make", "just",
        "your", "what", "when", "them", "they", "will", "into", "about", "like",
        "cursor", "would", "could", "should", "using", "here", "there",
    }
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text or "")
    for w in words:
        if w.lower() not in stop:
            return w
    return "TODO"


def exec_tool(name: str, args: dict) -> str:
    p = _norm(str(args.get("path") or args.get("target_file") or args.get("file_path") or ""))
    if name == "grep":
        if not p:
            p = str(args.get("cwd") or "")
        if not p:
            return "error: missing path"
        if not allowed_path(p):
            return "error: path not allowed: " + p
        pat = str(args.get("pattern") or args.get("query") or "")
        hits = []
        for fn in glob_files(os.path.join(p, "**", "*"), recursive=True)[:80]:
            if not os.path.isfile(fn):
                continue
            try:
                body = open(fn, "r", encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            if pat.lower() in body.lower():
                hits.append(fn)
        return "\n".join(hits[:40]) or "(no matches)"
    if not p:
        return "error: missing path"
    if not allowed_path(p):
        return "error: path not allowed: " + p
    try:
        if name in ("read_file", "read", "Read"):
            if not os.path.isfile(p):
                if os.path.isdir(p):
                    return exec_tool("list_dir", {"path": p})
                return "error: file not found: " + p
            data = open(p, "r", encoding="utf-8", errors="replace").read()
            if len(data) > 80000:
                data = data[:80000] + "\n...[truncated]"
            return data
        if name in ("list_dir", "list_files", "glob_files", "Glob"):
            if not os.path.isdir(p):
                return "error: not a directory: " + p
            names = os.listdir(p)
            return "\n".join(names[:200]) or "(empty)"
    except OSError as exc:
        return "error: " + str(exc)
    return "error: unknown tool " + name


def _fn_args(tc: dict) -> tuple[str, dict]:
    fn = tc.get("function") or tc
    name = str(fn.get("name") or "")
    raw = fn.get("arguments") or {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw) if raw else {}
        except ValueError:
            raw = {"path": raw}
    return name, raw if isinstance(raw, dict) else {}


def has_prior_work(messages: list) -> bool:
    msgs = messages or []
    if len(msgs) >= 4:
        return True
    for m in msgs:
        if not isinstance(m, dict):
            continue
        role = str(m.get("role") or "").lower()
        if role == "tool" or m.get("tool_calls"):
            return True
        text = message_text(m).lower()
        if any(s in text for s in SUMMARY_MARKERS):
            return True
    return False


def is_cursor_openai_client(data: dict) -> bool:
    """Cursor Agent already sent the paid-API payload. Forward it; do not replace it."""
    if not isinstance(data, dict):
        return False
    names = set(tool_names(data.get("tools") or []))
    if names & CURSOR_TOOLS:
        return True
    msgs = data.get("messages") or []
    if has_prior_work(msgs):
        return True
    if msgs and str(msgs[0].get("role") or "").lower() == "system" and len(message_text(msgs[0])) > 1500:
        return True
    return False


def inject_system(messages: list) -> list:
    out = list(messages)
    if not out or str(out[0].get("role", "")).lower() != "system":
        out.insert(0, {"role": "system", "content": AGENT_SYS})
    elif AGENT_SYS[:40] not in message_text(out[0]):
        out[0] = {
            "role": "system",
            "content": AGENT_SYS + "\n\n" + message_text(out[0]),
        }
    return out


def tool_names(tools: list) -> list[str]:
    names = []
    for t in tools or []:
        if not isinstance(t, dict):
            continue
        fn = t.get("function") if isinstance(t.get("function"), dict) else t
        n = (fn or {}).get("name")
        if n:
            names.append(str(n))
    return names


def pick_client_tool(tools: list, kind: str) -> str:
    names = tool_names(tools)
    aliases = {
        "read_file": ("read_file", "read", "Read", "ReadFile", "read_text_file", "get_file"),
        "list_dir": ("list_dir", "list_files", "ListDir", "list_directory", "Glob"),
        "glob_files": ("glob_files", "Glob", "glob", "glob_file_search", "file_search"),
        "grep": ("grep", "Grep", "codebase_search", "search"),
    }
    want = aliases.get(kind, (kind,))
    for n in names:
        if n in want:
            return n
    return names[0] if names else kind


def arg_field(tools: list, tool_name: str, prefer: tuple[str, ...] = ()) -> str:
    for t in tools or []:
        fn = t.get("function") if isinstance(t, dict) else None
        if not isinstance(fn, dict) or fn.get("name") != tool_name:
            continue
        props = (fn.get("parameters") or {}).get("properties") or {}
        for cand in prefer + ("path", "target_file", "file_path", "file", "pattern", "query"):
            if cand in props:
                return cand
    return prefer[0] if prefer else "path"


def forced_tool_call(tools: list, kind: str, args: dict | str) -> dict:
    if isinstance(args, str):
        args = {"path": args}
    name = pick_client_tool(tools, kind)
    payload = dict(args)
    if "path" in payload:
        field = arg_field(tools, name, ("path", "target_file", "file_path", "file"))
        if field != "path":
            payload[field] = payload.pop("path")
    if "pattern" in payload:
        field = arg_field(tools, name, ("pattern", "query", "glob_pattern"))
        if field != "pattern" and field in ("query", "glob_pattern"):
            payload[field] = payload.pop("pattern")
    return {
        "id": "call_" + uuid.uuid4().hex[:12],
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(payload),
        },
    }


def fallback_gather(user: str, tools: list, workspace: str) -> tuple[str, dict] | None:
    names = set(tool_names(tools))
    if any(n in names for n in ("grep", "Grep", "codebase_search")):
        args = {"pattern": keyword(user)}
        if workspace:
            args["path"] = workspace
        return "grep", args
    if any(n in names for n in ("glob_files", "Glob", "glob", "file_search")):
        return "glob_files", {"pattern": "**/*.{js,ts,py,cs,cpp,h,json}"}
    if workspace:
        return "list_dir", {"path": workspace}
    return None


def prepare_request(data: dict) -> dict:
    if is_cursor_openai_client(data):
        return data
    messages = data.get("messages")
    if not isinstance(messages, list):
        return data
    data = dict(data)
    data["messages"] = inject_system(messages)
    user = last_user_text(data["messages"])
    tools = data.get("tools")
    last_role = str((data["messages"][-1] or {}).get("role", "")).lower() if data["messages"] else ""
    if tools and last_role != "tool" and wants_tools(user) and not has_prior_work(data["messages"]):
        data["tool_choice"] = "required"
    return data


def inject_missing_tool_calls(req: dict, payload: bytes) -> bytes:
    """If the 3B lectures instead of calling tools, emit a Cursor tool call.

    Cursor Agent will then Read/Grep locally. Skipping this for hosted BYOK
    is why the model said files were missing.
    """
    try:
        data = json.loads(payload.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return payload
    if not isinstance(data, dict):
        return payload
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return payload
    msg = choices[0].get("message") or {}
    if msg.get("tool_calls"):
        return payload
    tools = req.get("tools") or []
    if not tools:
        return payload
    messages = req.get("messages") or []
    last_role = str((messages[-1] or {}).get("role") or "").lower() if messages else ""
    content = message_text(msg)
    user = last_user_text(messages)
    blob = "\n".join(message_text(m) for m in messages)
    ws = workspace_of(req)
    hosted = is_cursor_openai_client(req)
    blind = is_tutor(content) or (not content)
    if last_role == "tool" and not blind:
        return payload
    if last_role not in ("user", "tool") and not hosted:
        return payload
    if last_role == "user" and hosted:
        blind = True
    elif content and not blind and not wants_tools(user):
        return payload
    guess = guess_path(user + "\n" + blob, ws)
    kind_args = None
    if guess:
        kind_args = (guess[0], {"path": guess[1]})
    elif hosted or is_tutor(content) or wants_tools(user):
        kind_args = fallback_gather(user, tools, ws)
    if not kind_args:
        return payload
    kind, args = kind_args
    msg = dict(msg)
    msg["tool_calls"] = [forced_tool_call(tools, kind, args)]
    msg["content"] = None
    choices[0]["message"] = msg
    choices[0]["finish_reason"] = "tool_calls"
    data["choices"] = choices
    from paid_api import log_proxy

    log_proxy("injected %s %s (hosted=%s last=%s)" % (kind, args, hosted, last_role))
    return json.dumps(data).encode("utf-8")


def should_local_loop(data: dict) -> bool:
    if is_cursor_openai_client(data):
        return False
    if data.get("tools"):
        return False
    if has_prior_work(data.get("messages") or []):
        return False
    return wants_tools(last_user_text(data.get("messages") or []))


def synthesize_tool_completion(req: dict) -> dict | None:
    if is_cursor_openai_client(req):
        return None
    tools = req.get("tools") or []
    messages = req.get("messages") or []
    last_role = str((messages[-1] or {}).get("role", "")).lower() if messages else ""
    if not tools or last_role == "tool" or has_prior_work(messages):
        return None
    user = last_user_text(messages)
    ws = workspace_of(req)
    guess = guess_path(user, ws)
    if guess:
        kind, path = guess
        call = forced_tool_call(tools, kind, {"path": path})
    else:
        if not wants_tools(user):
            return None
        fb = fallback_gather(user, tools, ws)
        if not fb:
            return None
        kind, args = fb
        call = forced_tool_call(tools, kind, args)
    return {
        "id": "chatcmpl-forced",
        "object": "chat.completion",
        "model": req.get("model") or "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": None, "tool_calls": [call]},
                "finish_reason": "tool_calls",
            }
        ],
    }


def run_local_loop(data: dict, forward_json) -> dict:
    messages = inject_system(list(data.get("messages") or []))
    user = last_user_text(messages)
    ws = workspace_of(data)
    guess = guess_path(user, ws)
    if guess:
        kind, path = guess
        cid = "call_" + uuid.uuid4().hex[:12]
        out = exec_tool(kind, {"path": path})
        messages.append(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": cid,
                        "type": "function",
                        "function": {"name": kind, "arguments": json.dumps({"path": path})},
                    }
                ],
            }
        )
        messages.append({"role": "tool", "tool_call_id": cid, "content": out})

    model = data.get("model") or "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"
    req = {
        "model": model,
        "messages": messages,
        "stream": False,
        "temperature": 0.2,
        "max_tokens": 1024,
    }
    return forward_json(req)


def to_sse(obj: dict) -> bytes:
    msg = ((obj.get("choices") or [{}])[0].get("message")) or {}
    calls = msg.get("tool_calls") or []
    if calls:
        chunk = {
            "id": obj.get("id") or "chatcmpl-local",
            "object": "chat.completion.chunk",
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "tool_calls": calls},
                    "finish_reason": "tool_calls",
                }
            ],
        }
        return ("data: " + json.dumps(chunk) + "\n\ndata: [DONE]\n\n").encode("utf-8")
    content = msg.get("content") or ""
    chunk = {
        "id": obj.get("id") or "chatcmpl-local",
        "object": "chat.completion.chunk",
        "choices": [{"index": 0, "delta": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
    }
    return ("data: " + json.dumps(chunk) + "\n\ndata: [DONE]\n\n").encode("utf-8")
