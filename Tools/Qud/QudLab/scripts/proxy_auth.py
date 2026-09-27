"""Long GPU-proxy key. Cloudflare URL is not a secret; this key is.

Stored in %LOCALAPPDATA%\\QudLab\\vllm-proxy-key.txt (not git).
Cursor Settings → OpenAI API Key must be this value.
"""
from __future__ import annotations

import hmac
import os
import secrets
import threading
import time

# 48 bytes → 64 url-safe chars. Brute force over HTTPS is not realistic.
KEY_BYTES = 48
MIN_CHARS = 48
WEAK = frozenset(
    {
        "",
        "local-vllm",
        "sk-local",
        "sk-dummy",
        "changeme",
        "password",
        "secret",
        "vllm",
        "qwen",
        "test",
        "1234",
        "admin",
    }
)
KEY_PATH = os.environ.get(
    "QUDLAB_PROXY_KEY_FILE",
    os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "QudLab", "vllm-proxy-key.txt"),
)
FAIL_LIMIT = 8
FAIL_WINDOW = 300
LOCK_SECS = 900

_lock = threading.Lock()
_fails: dict[str, list[float]] = {}
_locked: dict[str, float] = {}


def _key_path() -> str:
    return KEY_PATH


def generate_key() -> str:
    return secrets.token_urlsafe(KEY_BYTES)


def is_strong(key: str) -> bool:
    k = (key or "").strip()
    if len(k) < MIN_CHARS or k.lower() in WEAK:
        return False
    return True


def load_or_create_key() -> tuple[str, str, bool]:
    """Return (key, path, created). Env QUDLAB_PROXY_KEY wins if it is long enough."""
    env = (os.environ.get("QUDLAB_PROXY_KEY") or "").strip()
    if is_strong(env):
        return env, "env:QUDLAB_PROXY_KEY", False
    path = _key_path()
    created = False
    try:
        with open(path, encoding="utf-8") as fh:
            existing = fh.read().strip()
    except OSError:
        existing = ""
    if not is_strong(existing):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        existing = generate_key()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(existing + "\n")
        created = True
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    return existing, path, created


def presented_key(headers) -> str:
    if not headers:
        return ""
    auth = str(headers.get("Authorization") or headers.get("authorization") or "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    for name in ("x-api-key", "X-Api-Key", "api-key", "Api-Key", "x-openai-api-key"):
        val = headers.get(name)
        if val:
            return str(val).strip()
    return ""


def is_tunnel_request(headers) -> bool:
    if not headers:
        return False
    host = str(headers.get("Host") or headers.get("host") or "").lower()
    if "trycloudflare.com" in host or "ngrok" in host or "cloudflare" in host:
        return True
    for name in (
        "Cf-Ray",
        "cf-ray",
        "CF-Connecting-IP",
        "Cf-Connecting-Ip",
        "cf-connecting-ip",
        "CF-Visitor",
        "cf-visitor",
    ):
        if headers.get(name):
            return True
    return False


def client_id(headers, address) -> str:
    for name in ("CF-Connecting-IP", "Cf-Connecting-Ip", "cf-connecting-ip", "X-Forwarded-For"):
        val = headers.get(name) if headers else None
        if val:
            return str(val).split(",")[0].strip()[:80]
    if address:
        return str(address[0])
    return "unknown"


def locked(cid: str) -> bool:
    now = time.monotonic()
    with _lock:
        until = _locked.get(cid) or 0.0
        if until > now:
            return True
        _locked.pop(cid, None)
        return False


def note_failure(cid: str) -> None:
    now = time.monotonic()
    with _lock:
        hits = [t for t in _fails.get(cid, []) if now - t < FAIL_WINDOW]
        hits.append(now)
        _fails[cid] = hits
        if len(hits) >= FAIL_LIMIT:
            _locked[cid] = now + LOCK_SECS
            _fails[cid] = []


def note_success(cid: str) -> None:
    with _lock:
        _fails.pop(cid, None)
        _locked.pop(cid, None)


def check_key(presented: str, expected: str) -> bool:
    got = (presented or "").strip().encode("utf-8")
    want = (expected or "").strip().encode("utf-8")
    if not got or not want or len(got) != len(want):
        return False
    return hmac.compare_digest(got, want)
