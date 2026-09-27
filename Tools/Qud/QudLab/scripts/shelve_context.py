"""Shelve task/context to disk, swap to a high-context vLLM model, then reload.

11GB can hold only one weights set. When the small model (32k) is too tight:
  1) write a shelf file (chat index + task + compact transcript)
  2) swap GPU to Coder-7B-AWQ (64k + RAM swap)
  3) next proxy turn injects the shelf into the system prompt
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
import uuid
from typing import Any

CACHE_DIR = os.path.join(os.environ.get("LOCALAPPDATA", "."), "QudLab", "cache")
SHELF_DIR = os.path.join(CACHE_DIR, "shelves")
PENDING_PATH = os.path.join(SHELF_DIR, "pending-unshelve.json")
INDEX_DIR = os.path.join(CACHE_DIR, "chat-index")

HIGH_CTX_MODEL = os.environ.get(
    "QUDLAB_HIGH_CTX_MODEL", "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"
)
LOW_CTX_MODEL = os.environ.get("QUDLAB_LOW_CTX_MODEL", "Qwen/Qwen2.5-3B-Instruct")
HIGH_CTX_LEN = int(os.environ.get("QUDLAB_HIGH_CTX_LEN", "65536"))
LOW_CTX_LEN = int(os.environ.get("QUDLAB_LOW_CTX_LEN", "32768"))


def _log(msg: str) -> None:
    try:
        from paid_api import log_proxy

        log_proxy(msg)
    except Exception:
        sys_stderr = __import__("sys").stderr
        sys_stderr.write(time.strftime("%H:%M:%S") + " " + msg + "\n")


def ensure_shelf_dir() -> str:
    os.makedirs(SHELF_DIR, exist_ok=True)
    return SHELF_DIR


def read_latest_index() -> dict:
    path = os.path.join(INDEX_DIR, "latest.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _clip_messages(messages: list, max_chars: int = 48000) -> list:
    out = []
    size = 0
    for m in reversed(list(messages or [])):
        if not isinstance(m, dict):
            continue
        role = str(m.get("role") or "?")
        content = m.get("content")
        if isinstance(content, list):
            text = "\n".join(
                str(p.get("text") or "")
                for p in content
                if isinstance(p, dict) and p.get("type") in (None, "text", "thinking")
            )
        else:
            text = str(content or "")
        if len(text) > 4000:
            text = text[:2000] + "\n...[shelved trunc]...\n" + text[-1500:]
        rec = {"role": role, "content": text}
        if m.get("tool_calls"):
            # Keep tool names only — args are low-value for shelf reload.
            names = []
            for c in m.get("tool_calls") or []:
                if isinstance(c, dict):
                    fn = c.get("function") or {}
                    names.append(str(fn.get("name") or c.get("name") or "tool"))
            rec["tool_calls_brief"] = names[:8]
        size += len(text)
        out.insert(0, rec)
        if size >= max_chars or len(out) >= 40:
            break
    return out


_IMPORTANT_RE = re.compile(
    r"(?i)(?:error|exception|failed|CS\d{4}|MODERROR|TODO|FIXME|path|file|"
    r"compile|migrate|api_migrate|remaining|fix|bug|crash)"
)


def summarize_low_value_text(blob: str, max_chars: int = 900) -> str:
    """Worst-case: keep important lines, collapse the rest into a short note."""
    blob = (blob or "").strip()
    if not blob:
        return ""
    if len(blob) <= max_chars:
        return blob
    keep = []
    drop_n = 0
    for line in blob.replace("\r\n", "\n").split("\n"):
        s = line.strip()
        if not s:
            continue
        if _IMPORTANT_RE.search(s) or s.startswith("- ") or s.startswith("user:"):
            keep.append(s[:240])
        else:
            drop_n += 1
    if not keep:
        return blob[: max_chars // 2] + "\n...[summarized low-value mid]...\n" + blob[-max_chars // 3 :]
    body = "\n".join(keep[-40:])
    note = "\n[%s low-value lines summarized away]" % drop_n if drop_n else ""
    out = body + note
    if len(out) > max_chars:
        out = out[: max_chars - 20] + "\n...[truncated]"
    return out


def compress_chat_index(idx: dict, aggressive: bool = False) -> dict:
    """Keep paths/errors/queries; shrink narrative and tool noise."""
    if not isinstance(idx, dict):
        return {}
    out = {
        "id": idx.get("id") or "",
        "workspaces": list(idx.get("workspaces") or [])[: (4 if aggressive else 8)],
        "queries": list(idx.get("queries") or [])[-(3 if aggressive else 8) :],
        "errors": list(idx.get("errors") or [])[-(4 if aggressive else 8) :],
        "tools": [],
        "files": {},
        "narrative": "",
    }
    # Prefer files with real flags over mere "mentioned".
    files = idx.get("files") or {}
    ranked = []
    for path, rec in files.items():
        flags = list((rec or {}).get("flags") or [])
        score = 0
        for f in flags:
            fl = str(f).lower()
            if fl in ("read", "edited", "error", "compile", "written"):
                score += 3
            elif fl != "mentioned":
                score += 1
        ranked.append((score, path, {"flags": flags[:6] or ["mentioned"]}))
    ranked.sort(key=lambda x: (-x[0], x[1]))
    limit = 18 if aggressive else 40
    out["files"] = {p: rec for _, p, rec in ranked[:limit]}
    # Tools: names only, last few
    for t in (idx.get("tools") or [])[-(4 if aggressive else 10) :]:
        out["tools"].append(str(t)[:120])
    narr = str(idx.get("narrative") or "")
    if narr:
        out["narrative"] = summarize_low_value_text(narr, 500 if aggressive else 900)
    return out


def compress_shelf(shelf: dict, aggressive: bool = False) -> dict:
    """Worst-case shelf shrink before inject / disk write."""
    if not isinstance(shelf, dict):
        return {}
    out = dict(shelf)
    out["task"] = str(shelf.get("task") or "")[: (2500 if aggressive else 8000)]
    out["workspaces"] = list(shelf.get("workspaces") or [])[: (3 if aggressive else 8)]
    out["chat_index"] = compress_chat_index(shelf.get("chat_index") or {}, aggressive=aggressive)
    msgs = []
    budget = 8000 if aggressive else 24000
    size = 0
    for m in reversed(list(shelf.get("messages") or [])):
        if not isinstance(m, dict):
            continue
        role = str(m.get("role") or "?")
        text = str(m.get("content") or "")
        # Drop long assistant lectures; keep user + short plans + tool briefs.
        if role == "assistant" and len(text) > 600 and not m.get("tool_calls_brief"):
            text = summarize_low_value_text(text, 280)
        elif len(text) > (800 if aggressive else 2000):
            text = summarize_low_value_text(text, 500 if aggressive else 900)
        rec = {"role": role, "content": text}
        if m.get("tool_calls_brief"):
            rec["tool_calls_brief"] = m["tool_calls_brief"][:6]
        size += len(text)
        msgs.insert(0, rec)
        if size >= budget or len(msgs) >= (8 if aggressive else 16):
            break
    out["messages"] = msgs
    out["compressed"] = "aggressive" if aggressive else "normal"
    return out


def create_shelf(
    *,
    task: str = "",
    messages: list | None = None,
    reason: str = "manual",
    from_model: str = "",
    to_model: str = "",
    workspaces: list | None = None,
    extra: dict | None = None,
) -> dict:
    ensure_shelf_dir()
    idx = read_latest_index()
    sid = time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    shelf = {
        "id": sid,
        "created": int(time.time()),
        "reason": reason,
        "from_model": from_model or LOW_CTX_MODEL,
        "to_model": to_model or HIGH_CTX_MODEL,
        "high_ctx_len": HIGH_CTX_LEN,
        "task": (task or "")[:8000],
        "workspaces": workspaces
        or list(idx.get("workspaces") or [])[:8],
        "chat_index": idx,
        "messages": _clip_messages(messages or []),
        "extra": extra or {},
    }
    if not shelf["task"]:
        qs = idx.get("queries") or []
        if qs:
            shelf["task"] = str(qs[-1])[:8000]
    # Always compress low-value detail before write (worst-case context saver).
    shelf = compress_shelf(shelf, aggressive=reason in ("context_pressure", "need_higher_context"))
    path = os.path.join(SHELF_DIR, sid + ".json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(shelf, fh, ensure_ascii=False, indent=2)
    md = format_shelf_prompt(shelf)
    with open(os.path.join(SHELF_DIR, sid + ".md"), "w", encoding="utf-8") as fh:
        fh.write(md)
    with open(os.path.join(SHELF_DIR, "latest.json"), "w", encoding="utf-8") as fh:
        json.dump(shelf, fh, ensure_ascii=False, indent=2)
    _log(
        "shelved id=%s reason=%s chars=%s compressed=%s"
        % (sid, reason, len(md), shelf.get("compressed"))
    )
    return shelf


def load_shelf(shelf_id: str = "latest") -> dict | None:
    ensure_shelf_dir()
    if shelf_id in ("", "latest", "pending"):
        path = os.path.join(SHELF_DIR, "latest.json")
        if shelf_id == "pending" and os.path.isfile(PENDING_PATH):
            try:
                with open(PENDING_PATH, encoding="utf-8") as fh:
                    pend = json.load(fh)
                shelf_id = str(pend.get("shelf_id") or "latest")
            except (OSError, ValueError, TypeError):
                shelf_id = "latest"
        if shelf_id == "latest":
            path = os.path.join(SHELF_DIR, "latest.json")
        else:
            path = os.path.join(SHELF_DIR, shelf_id + ".json")
    else:
        path = os.path.join(SHELF_DIR, shelf_id + ".json")
        if not os.path.isfile(path) and not shelf_id.endswith(".json"):
            path = os.path.join(SHELF_DIR, shelf_id)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError, TypeError):
        return None


def format_shelf_prompt(shelf: dict, max_chars: int = 12000) -> str:
    if not isinstance(shelf, dict):
        return ""
    # Worst case: compress low-value detail before formatting.
    if len(json.dumps(shelf, ensure_ascii=False)) > max_chars * 2:
        shelf = compress_shelf(shelf, aggressive=True)
    elif shelf.get("compressed") != "aggressive":
        shelf = compress_shelf(shelf, aggressive=False)

    lines = [
        "SHELVED CONTEXT (restored after high-context model swap).",
        "Continue this task. Prefer tools on listed paths; do not ask the user to re-paste.",
        "Low-value chatter was summarized away to save context.",
        "shelf_id=" + str(shelf.get("id") or "?"),
        "reason=" + str(shelf.get("reason") or ""),
        "compressed=" + str(shelf.get("compressed") or "normal"),
        "from_model=" + str(shelf.get("from_model") or ""),
        "to_model=" + str(shelf.get("to_model") or ""),
    ]
    if shelf.get("workspaces"):
        lines.append("workspaces:")
        for ws in shelf["workspaces"][:6]:
            lines.append("- " + str(ws))
    if shelf.get("task"):
        lines.append("USER TASK:\n" + str(shelf["task"])[:3000])
    idx = shelf.get("chat_index") or {}
    if isinstance(idx, dict):
        if idx.get("errors"):
            lines.append("errors:")
            for e in idx["errors"][-6:]:
                lines.append("- " + str(e)[:200])
        files = idx.get("files") or {}
        if files:
            lines.append("files:")
            for path, rec in list(files.items())[-30:]:
                flags = ",".join((rec or {}).get("flags") or []) or "mentioned"
                lines.append("- %s [%s]" % (path, flags))
        if idx.get("queries"):
            lines.append("prior_queries:")
            for q in idx["queries"][-5:]:
                lines.append("- " + str(q)[:200])
        if idx.get("narrative"):
            lines.append("narrative:\n" + summarize_low_value_text(str(idx["narrative"]), 700))
    msgs = shelf.get("messages") or []
    if msgs:
        lines.append("transcript_tail:")
        for m in msgs[-10:]:
            role = str((m or {}).get("role") or "?")
            text = str((m or {}).get("content") or "").replace("\n", " ")
            brief = (m or {}).get("tool_calls_brief") or []
            line = "%s: %s" % (role, text[:320])
            if brief:
                line += " | tools=" + ",".join(str(x) for x in brief[:6])
            lines.append(line)
    text = "\n".join(lines)
    if len(text) > max_chars:
        # Last resort: keep task + files + last 4 transcript lines only.
        shelf2 = compress_shelf(shelf, aggressive=True)
        lines2 = [
            "SHELVED CONTEXT (aggressive compress).",
            "shelf_id=" + str(shelf2.get("id") or "?"),
            "USER TASK:\n" + str(shelf2.get("task") or "")[:2000],
        ]
        files = (shelf2.get("chat_index") or {}).get("files") or {}
        if files:
            lines2.append("files:")
            for path, rec in list(files.items())[-20:]:
                lines2.append("- " + path)
        for m in (shelf2.get("messages") or [])[-4:]:
            lines2.append(
                "%s: %s"
                % (
                    (m or {}).get("role"),
                    str((m or {}).get("content") or "").replace("\n", " ")[:220],
                )
            )
        text = "\n".join(lines2)
        if len(text) > max_chars:
            text = text[: max_chars - 20] + "\n...[shelf truncated]"
    return text


def set_pending_unshelve(shelf_id: str, to_model: str = "") -> None:
    ensure_shelf_dir()
    payload = {
        "shelf_id": shelf_id,
        "to_model": to_model or HIGH_CTX_MODEL,
        "set_at": int(time.time()),
    }
    with open(PENDING_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def clear_pending_unshelve() -> None:
    try:
        if os.path.isfile(PENDING_PATH):
            os.remove(PENDING_PATH)
    except OSError:
        pass


def consume_pending_shelf_prompt(max_chars: int = 12000) -> str:
    """If a pending unshelve exists, return prompt text and clear the flag."""
    if not os.path.isfile(PENDING_PATH):
        return ""
    try:
        with open(PENDING_PATH, encoding="utf-8") as fh:
            pend = json.load(fh)
    except (OSError, ValueError, TypeError):
        return ""
    shelf = load_shelf(str(pend.get("shelf_id") or "latest"))
    if not shelf:
        clear_pending_unshelve()
        return ""
    text = format_shelf_prompt(shelf, max_chars=max_chars)
    clear_pending_unshelve()
    _log("unshelved id=%s into prompt chars=%s" % (shelf.get("id"), len(text)))
    return text


def list_shelves(limit: int = 20) -> list:
    ensure_shelf_dir()
    rows = []
    for name in os.listdir(SHELF_DIR):
        if not name.endswith(".json") or name in ("latest.json", "pending-unshelve.json"):
            continue
        path = os.path.join(SHELF_DIR, name)
        try:
            st = os.stat(path)
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            rows.append(
                {
                    "id": data.get("id") or name[:-5],
                    "mtime": st.st_mtime,
                    "reason": data.get("reason"),
                    "task": str(data.get("task") or "")[:120],
                    "to_model": data.get("to_model"),
                }
            )
        except (OSError, ValueError, TypeError):
            continue
    rows.sort(key=lambda r: r["mtime"], reverse=True)
    return rows[:limit]


def find_lab_scripts() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return here


def escalate(
    *,
    task: str = "",
    messages: list | None = None,
    reason: str = "need_higher_context",
    from_model: str = "",
    to_model: str = "",
    restart_frontend: bool = True,
    do_swap: bool = True,
) -> dict:
    """Shelve current work, optionally swap GPU to high-ctx model, mark pending unshelve."""
    to_model = to_model or HIGH_CTX_MODEL
    shelf = create_shelf(
        task=task,
        messages=messages,
        reason=reason,
        from_model=from_model or LOW_CTX_MODEL,
        to_model=to_model,
    )
    set_pending_unshelve(str(shelf["id"]), to_model)
    result = {
        "shelf_id": shelf["id"],
        "shelf_path": os.path.join(SHELF_DIR, shelf["id"] + ".json"),
        "to_model": to_model,
        "swapped": False,
        "pending": True,
    }
    if not do_swap:
        return result

    script = os.path.join(find_lab_scripts(), "Swap-VllmModel.ps1")
    if not os.path.isfile(script):
        result["error"] = "missing Swap-VllmModel.ps1"
        return result

    args = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        script,
        "swap",
        "-Model",
        to_model,
    ]
    if restart_frontend:
        args.append("-RestartFrontend")
    _log("escalate swap -> %s" % to_model)
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=900)
        result["swapped"] = proc.returncode == 0
        result["swap_exit"] = proc.returncode
        tail = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()[-2000:]
        result["swap_log"] = tail
        # Keep pending even if swap failed — user can retry swap.
        if proc.returncode != 0:
            set_pending_unshelve(str(shelf["id"]), to_model)
    except Exception as exc:
        result["error"] = str(exc)
        set_pending_unshelve(str(shelf["id"]), to_model)
    return result


def maybe_shelve_overflow(
    messages: list,
    *,
    est_tokens: int,
    max_ctx: int,
    model: str = "",
    task: str = "",
) -> dict | None:
    """If prompt is still huge for a low-ctx model, shelve and set pending (no auto-swap)."""
    # Only auto-shelve when clearly on a low window or overflowing hard.
    low = max_ctx <= LOW_CTX_LEN + 1024 or "3B" in (model or "")
    if not low and est_tokens < int(max_ctx * 0.85):
        return None
    if est_tokens < int(max_ctx * 0.92) and not low:
        return None
    if est_tokens < 12000 and max_ctx >= HIGH_CTX_LEN // 2:
        return None
    shelf = create_shelf(
        task=task,
        messages=messages,
        reason="context_pressure",
        from_model=model or LOW_CTX_MODEL,
        to_model=HIGH_CTX_MODEL,
    )
    set_pending_unshelve(str(shelf["id"]), HIGH_CTX_MODEL)
    return shelf
