#!/usr/bin/env python3
"""
Start/stop the local SD3.5 server (:1338) around generation jobs.

Default policy: start on demand, stop when the job finishes.
Set AAMT_SD_KEEP_SERVER=1 (or pass keep_server=True) to leave it running.
The server also auto-exits after SD_IDLE_SHUTDOWN_SEC (default 180s) idle.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

TOOLS_ROOT = Path(__file__).resolve().parent.parent
START_PS1 = TOOLS_ROOT / "Start-StableDiffusionServer.ps1"
STOP_PS1 = TOOLS_ROOT / "Stop-StableDiffusionServer.ps1"


def _sd_port() -> int:
    try:
        from tool_paths import sd_port

        return int(sd_port())
    except Exception:
        return 1338


def _sd_base_url() -> str:
    return f"http://127.0.0.1:{_sd_port()}"


def _sd_base_urls() -> list:
    """IPv4 and IPv6 loopback bases (the server listens on both)."""
    port = _sd_port()
    hosts = []
    override = (os.environ.get("AAMT_SD_HOST") or "").strip().strip("[]")
    if override:
        hosts.append(override)
    for h in ("127.0.0.1", "::1"):
        if h == "::1" and os.environ.get("AAMT_SD_IPV6", "1").strip() == "0":
            continue
        if h not in hosts:
            hosts.append(h)
    return [f"http://[{h}]:{port}" if ":" in h else f"http://{h}:{port}" for h in hosts]


# Kept for callers that import them (IPv4 form).
PING_URL = f"{_sd_base_url()}/ping"
SHUTDOWN_URL = f"{_sd_base_url()}/shutdown"

# Never send loopback probes through a system proxy.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PING_TIMEOUT = float(os.environ.get("AAMT_SD_PING_TIMEOUT_SEC") or 4.0)


def _env_truthy(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def sd_status(timeout: float = PING_TIMEOUT) -> Optional[Dict[str, Any]]:
    """GET /ping JSON over IPv4 then IPv6, or None if the server is down.

    A timeout is retried once (busy server); a refused connection is not.
    """
    for base in _sd_base_urls():
        for attempt in range(2):
            try:
                with _OPENER.open(base + "/ping", timeout=timeout) as resp:
                    if resp.status != 200:
                        break
                    return json.loads(resp.read().decode("utf-8", errors="replace"))
            except Exception as exc:
                reason = getattr(exc, "reason", None)
                if isinstance(exc, ConnectionRefusedError) or isinstance(reason, ConnectionRefusedError):
                    break
                if attempt == 0:
                    time.sleep(0.3)
    return None


def sd_ping(timeout: float = PING_TIMEOUT) -> bool:
    return sd_status(timeout=timeout) is not None


def sd_loaded(timeout: float = 2.0) -> bool:
    st = sd_status(timeout=timeout)
    return bool(st and st.get("loaded") and is_aamt_status(st))


def is_aamt_status(st: Optional[Dict[str, Any]]) -> bool:
    """True for Tools/Shared/sd35_server.py. SFMAG/Starfield sd_server.py is not."""
    if not st:
        return False
    return str(st.get("version") or "").startswith("aamt-1338")


def _wait_for_ping_and_load(deadline: float) -> bool:
    saw_ping = False
    while time.time() < deadline:
        st = sd_status()
        if st and is_aamt_status(st):
            saw_ping = True
            if st.get("loaded"):
                print("[SD] server ready (pipeline loaded)")
                return True
        time.sleep(2.0)
    if saw_ping:
        print("[SD] /ping ok; pipeline still loading (first generate will wait)")
        return True
    return False


def stop_sd_server(*, force: bool = True) -> bool:
    """Ask the server to shut down; optionally kill listeners if still up."""
    for base in _sd_base_urls():
        try:
            _OPENER.open(base + "/shutdown", timeout=3).read()
            break
        except Exception:
            continue
    time.sleep(1.0)
    if not sd_ping(timeout=1.5):
        return True
    if not force or not STOP_PS1.exists():
        return not sd_ping(timeout=1.5)
    try:
        subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(STOP_PS1),
            ],
            check=False,
            timeout=60,
        )
    except Exception as exc:
        print(f"[SD] stop script failed: {exc}", file=sys.stderr)
    time.sleep(1.0)
    return not sd_ping(timeout=1.5)


def ensure_sd_server(
    *,
    timeout_sec: float = 180.0,
    start_if_needed: bool = True,
) -> bool:
    """Return True if :1338 is responding. Optionally launch Start-*.ps1.

    Prefers ``loaded: true`` (preload finished) so the first generate is not a
    cold 401 against a gated repo. Ping-only is accepted if preload is off.
    """
    if start_if_needed:
        # Server startup loads SD3.5 onto the GPU outside any request lock: wait
        # until no other batch holds the GPU job (one CUDA job at a time).
        try:
            from gpu_hub import hold_gpu_job
        except ImportError:
            pass
        else:
            hold_gpu_job("SD server start")
    deadline = time.time() + timeout_sec
    st = sd_status()
    if st and not is_aamt_status(st):
        print("[SD] foreign process on :1338 (not aamt-1338); replacing...")
        stop_sd_server(force=True)
        st = None
    if is_aamt_status(st) and sd_loaded():
        return True
    if is_aamt_status(st):
        return _wait_for_ping_and_load(deadline)
    if not start_if_needed:
        return False
    if not START_PS1.exists():
        print(f"[SD] missing start script: {START_PS1}", file=sys.stderr)
        return False
    print("[SD] starting server on demand...")
    env = os.environ.copy()
    # Generators own the lifecycle; keep default idle shutdown armed.
    env.setdefault("SD_IDLE_SHUTDOWN_SEC", "180")
    env.setdefault("SD_STATUS_GUI", "0")
    try:
        subprocess.Popen(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(START_PS1),
                "-NoStatusGui",
                "-WaitSec",
                str(int(min(timeout_sec, 240))),
            ],
            cwd=str(TOOLS_ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        print(f"[SD] failed to launch start script: {exc}", file=sys.stderr)
        return False

    if _wait_for_ping_and_load(deadline):
        return True
    print("[SD] timed out waiting for :1338", file=sys.stderr)
    return False


def require_sd_server(*, timeout_sec: float = 2400.0) -> str:
    """Wait for aamt-1338 and return its API URL.

    Call this whenever SD pixels were requested. Do **not** silently stamp
    procedural rings / noise — those look worse than leaving placeholders.
    Explicit ``--no-sd`` / ``use_sd=False`` is the only opt-in for placeholders.

    Override wait with ``AAMT_SD_WAIT_SEC``.
    """
    try:
        from sd_http_client import detect_server
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"sd_http_client unavailable: {exc}") from exc

    wait_sec = float(os.environ.get("AAMT_SD_WAIT_SEC") or timeout_sec)
    wait_sec = max(120.0, wait_sec)
    deadline = time.time() + wait_sec
    print(f"[SD] waiting for image stage (up to {wait_sec:.0f}s)...", file=sys.stderr)
    while time.time() < deadline:
        chunk = min(300.0, max(30.0, deadline - time.time()))
        if ensure_sd_server(timeout_sec=chunk, start_if_needed=True):
            url = detect_server(verbose=False)
            if url:
                print(f"[SD] ready at {url}", file=sys.stderr)
                return url
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        print(f"[SD] not ready yet; waiting ({remaining:.0f}s left)...", file=sys.stderr)
        time.sleep(min(15.0, remaining))
    raise RuntimeError(
        "SD server not reachable after waiting; refusing procedural image fallback. "
        "Start Tools\\Start-StableDiffusionServer.ps1, free the GPU lock, "
        "or pass an explicit --no-sd / use_sd=False only for placeholders."
    )


@contextmanager
def managed_sd_server(
    *,
    keep: Optional[bool] = None,
    timeout_sec: float = 180.0,
) -> Iterator[bool]:
    """
    Ensure SD is up for the block; stop it afterward unless keep is set.

    keep defaults from AAMT_SD_KEEP_SERVER (false).
    Yields True if the server is reachable inside the block.
    """
    if keep is None:
        keep = _env_truthy("AAMT_SD_KEEP_SERVER", False)
    started_here = False
    ready = sd_ping()
    if not ready:
        ready = ensure_sd_server(timeout_sec=timeout_sec, start_if_needed=True)
        started_here = ready
    try:
        yield ready
    finally:
        if ready and not keep:
            # Always stop after a managed job so VRAM is freed for games/Ollama.
            print("[SD] stopping server (job finished)")
            stop_sd_server(force=True)
        elif started_here and keep:
            print("[SD] leaving server running (--keep-server / AAMT_SD_KEEP_SERVER=1)")
