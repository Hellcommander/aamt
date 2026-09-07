#!/usr/bin/env python3
"""
GPU hub: a cross-process mutex so local AI tools take turns on the GPU.

SD3.5 image generation and Ollama model loads together exhaust the RTX
2080 Ti's 11 GB VRAM, and generations run 300+ seconds — so independent tool
processes (Transcendence AAMT and ElementalReforged AAMT) must serialize
GPU-heavy work. Wrap each SD generation request and each GPU-bound Ollama
generation in:

    from gpu_hub import acquire_gpu

    with acquire_gpu("SD banner 768x640"):
        ...one generation request...

Properties:
  - File-lock based (atomic O_CREAT|O_EXCL create) — works across independent
    Python processes with no third-party deps.
  - Lock file lives in %LOCALAPPDATA%\\AamtGpuHub\\gpu.lock (override with
    AAMT_GPU_HUB_DIR), never inside a git-managed tools folder.
  - Holder metadata (pid, label, timestamp) is written into the lock file for
    diagnostics; waiters log "waiting for GPU: <holder label>" every ~30 s.
  - Stale-lock recovery: if the holder pid is dead, the lock is broken.
  - Re-entrant per thread: nested acquire_gpu() calls in the same thread are
    no-ops, so wrapped helpers can call each other safely.
  - Long-running server startup should NOT hold the lock — only individual
    generation requests.

Set AAMT_GPU_HUB_DISABLE=1 to bypass locking entirely (debugging).
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional

_DEFAULT_DIR = Path(
    os.environ.get("AAMT_GPU_HUB_DIR")
    or Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    / "AamtGpuHub"
)
LOCK_FILE = _DEFAULT_DIR / "gpu.lock"

DEFAULT_POLL = 2.0
WAIT_LOG_INTERVAL = 30.0
# A lock file that cannot be parsed and hasn't changed for this long is
# treated as garbage (e.g. holder died mid-write) and broken.
UNREADABLE_STALE_SEC = 120.0

_tls = threading.local()


def _log(msg: str) -> None:
    print(f"[GPU-HUB] {msg}", file=sys.stderr, flush=True)


def _pid_alive(pid: int) -> bool:
    """True if `pid` refers to a live process. Never signals/kills anything."""
    if pid <= 0:
        return False
    if os.name == "nt":
        # NOTE: os.kill(pid, 0) on Windows TERMINATES the process — use Win32.
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        ERROR_ACCESS_DENIED = 5
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            # Access denied means the process exists but we can't open it.
            return ctypes.get_last_error() == ERROR_ACCESS_DENIED
        try:
            exit_code = wintypes.DWORD()
            if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return exit_code.value == STILL_ACTIVE
            return True
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _read_lock_raw() -> Optional[bytes]:
    try:
        return LOCK_FILE.read_bytes()
    except OSError:
        return None


def _parse_holder(raw: Optional[bytes]) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    try:
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _break_lock_if_unchanged(seen_raw: bytes, reason: str) -> bool:
    """
    Delete the lock only if its content still matches what we inspected —
    guards against deleting a lock that another process just (re)acquired.
    """
    current = _read_lock_raw()
    if current is None or current != seen_raw:
        return False
    try:
        LOCK_FILE.unlink()
        _log(f"broke stale GPU lock ({reason})")
        return True
    except OSError:
        return False


def _try_acquire(label: str) -> bool:
    """One atomic attempt to create the lock file with our metadata."""
    try:
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    payload = json.dumps(
        {
            "pid": os.getpid(),
            "label": label,
            "acquired": time.strftime("%Y-%m-%d %H:%M:%S"),
            "acquired_epoch": time.time(),
            "argv0": sys.argv[0] if sys.argv else "",
        },
        indent=2,
    ).encode("utf-8")
    try:
        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    except OSError:
        return False
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)
    return True


def _release(label: str) -> None:
    """Remove the lock, but only if this process still owns it."""
    holder = _parse_holder(_read_lock_raw())
    if holder is not None and holder.get("pid") != os.getpid():
        _log(f"release skipped: lock now held by pid {holder.get('pid')} (not ours)")
        return
    try:
        LOCK_FILE.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        _log(f"release failed for '{label}': {exc}")


@contextmanager
def acquire_gpu(
    label: str,
    timeout: Optional[float] = None,
    poll: float = DEFAULT_POLL,
    enabled: bool = True,
):
    """
    Context manager: block until this process holds the exclusive GPU lock.

    label   -- short description shown to other waiting processes.
    timeout -- max seconds to wait (None = wait forever). Raises TimeoutError.
    poll    -- seconds between lock attempts while waiting.
    enabled -- pass False for calls that don't touch the GPU (e.g. Ollama with
               num_gpu=0 running purely on CPU) to skip locking.
    """
    if not enabled or os.environ.get("AAMT_GPU_HUB_DISABLE") == "1":
        yield
        return

    # Re-entrant within a thread: nested wrapped helpers don't deadlock.
    depth = getattr(_tls, "depth", 0)
    if depth > 0:
        _tls.depth = depth + 1
        try:
            yield
        finally:
            _tls.depth -= 1
        return

    start = time.monotonic()
    last_wait_log = 0.0
    while True:
        if _try_acquire(label):
            break

        raw = _read_lock_raw()
        if raw is None:
            continue  # holder released between attempts; retry immediately
        holder = _parse_holder(raw)
        if holder is None:
            # Unparsable lock: break it only once it is demonstrably abandoned.
            try:
                age = time.time() - LOCK_FILE.stat().st_mtime
            except OSError:
                age = 0.0
            if age > UNREADABLE_STALE_SEC:
                _break_lock_if_unchanged(raw, "unreadable metadata")
            else:
                time.sleep(poll)
            continue

        holder_pid = int(holder.get("pid") or 0)
        if not _pid_alive(holder_pid):
            if _break_lock_if_unchanged(raw, f"holder pid {holder_pid} is dead"):
                continue

        waited = time.monotonic() - start
        if timeout is not None and waited >= timeout:
            raise TimeoutError(
                f"GPU lock not acquired after {waited:.0f}s "
                f"(held by pid {holder_pid}: {holder.get('label')!r})"
            )
        if waited - last_wait_log >= WAIT_LOG_INTERVAL:
            last_wait_log = waited
            _log(
                f"waiting for GPU: {holder.get('label')!r} "
                f"(pid {holder_pid}, since {holder.get('acquired')}) — "
                f"'{label}' has waited {waited:.0f}s"
            )
        time.sleep(poll)

    _tls.depth = 1
    _log(f"acquired for '{label}' (pid {os.getpid()})")
    try:
        yield
    finally:
        _tls.depth = 0
        _release(label)
        _log(f"released by '{label}'")


def current_holder() -> Optional[Dict[str, Any]]:
    """Diagnostics: metadata of the current lock holder, or None if free."""
    return _parse_holder(_read_lock_raw())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="GPU hub lock diagnostics/testing")
    parser.add_argument("--status", action="store_true", help="show current holder")
    parser.add_argument("--hold", type=float, default=0.0, metavar="SEC",
                        help="acquire the lock and hold it for SEC seconds")
    parser.add_argument("--label", default="gpu_hub-cli")
    parser.add_argument("--timeout", type=float, default=None)
    args = parser.parse_args()

    if args.status or not args.hold:
        holder = current_holder()
        if holder:
            alive = _pid_alive(int(holder.get("pid") or 0))
            print(json.dumps({**holder, "pid_alive": alive}, indent=2))
        else:
            print("GPU lock is free")
        sys.exit(0)

    with acquire_gpu(args.label, timeout=args.timeout):
        print(f"holding GPU lock for {args.hold}s...", flush=True)
        time.sleep(args.hold)
    print("done")
