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

GPU job lease (one CUDA job at a time):
  The request lock alone lets two batches interleave: between batch A's
  requests, batch B starts UniRig/Wan or (re)loads a server while A's resident
  models still hold CUDA contexts. Several CUDA jobs at once on the 2080 Ti
  crashed the display driver (2026-10-27). So the first acquire_gpu() in a
  process also takes a process-wide lease (job.lock next to gpu.lock) and keeps
  it until the process exits: a second batch waits at its first GPU call until
  the first batch is finished.
  - Child processes inherit the lease (AAMT_GPU_JOB_OWNER env var), so a batch
    whose subprocesses call acquire_gpu() does not wait on itself.
  - Dead holders are broken like the request lock.
  - AAMT_GPU_JOB_IDLE_SEC (default 1800) frees the lease after that long with
    no GPU request, so a long-lived GUI tool doesn't block batches forever;
    0 holds it until exit. release_gpu_job() frees it explicitly.
  - `python gpu_hub.py --status` shows both holders.

Set AAMT_GPU_HUB_DISABLE=1 to bypass locking entirely (debugging).
"""

from __future__ import annotations

import atexit
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
JOB_LOCK_FILE = _DEFAULT_DIR / "job.lock"
JOB_OWNER_ENV = "AAMT_GPU_JOB_OWNER"

DEFAULT_POLL = 2.0
WAIT_LOG_INTERVAL = 30.0
# A lock file that cannot be parsed and hasn't changed for this long is
# treated as garbage (e.g. holder died mid-write) and broken.
UNREADABLE_STALE_SEC = 120.0
JOB_IDLE_SEC = float(os.environ.get("AAMT_GPU_JOB_IDLE_SEC") or 1800)

_tls = threading.local()

# Process-wide lease state.
_job_mutex = threading.RLock()
_job_held = False
_job_active = 0          # requests in flight in this process
_job_last_use = 0.0
_job_timer: Optional[threading.Timer] = None


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


def _read_lock_raw(path: Path = LOCK_FILE) -> Optional[bytes]:
    try:
        return path.read_bytes()
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


def _break_lock_if_unchanged(path: Path, seen_raw: bytes, reason: str) -> bool:
    """
    Delete the lock only if its content still matches what we inspected —
    guards against deleting a lock that another process just (re)acquired.
    """
    current = _read_lock_raw(path)
    if current is None or current != seen_raw:
        return False
    # Compare-then-unlink is racy: move the lock aside atomically first, then re-check
    # what we actually took. Only one breaker can win the rename.
    aside = path.with_name(f"{path.name}.stale-{os.getpid()}-{time.time_ns()}")
    try:
        os.rename(str(path), str(aside))
    except OSError:
        return False
    try:
        if _read_lock_raw(aside) == seen_raw:
            _log(f"broke stale {path.name} ({reason})")
            return True
        # re-acquired in between: put the new holder's lock back (link never overwrites)
        try:
            os.link(str(aside), str(path))
        except OSError as exc:
            _log(f"could not restore {path.name} after a racing re-acquire: {exc}")
        return False
    finally:
        try:
            aside.unlink()
        except OSError:
            pass


def _try_acquire(path: Path, label: str) -> bool:
    """One atomic attempt to create the lock file with our metadata."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
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
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    except OSError:
        return False
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)
    return True


def _release(path: Path, label: str) -> None:
    """Remove the lock, but only if this process still owns it."""
    holder = _parse_holder(_read_lock_raw(path))
    if holder is not None and holder.get("pid") != os.getpid():
        _log(f"release skipped: {path.name} now held by pid {holder.get('pid')} (not ours)")
        return
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        _log(f"release of {path.name} failed for '{label}': {exc}")


def _wait_acquire(path: Path, label: str, what: str, timeout: Optional[float],
                  poll: float, start: float) -> None:
    """Block until `path` is ours; `timeout` counts from `start` (monotonic)."""
    last_wait_log = 0.0
    while True:
        if _try_acquire(path, label):
            return

        raw = _read_lock_raw(path)
        if raw is None:
            continue  # holder released between attempts; retry immediately
        holder = _parse_holder(raw)
        if holder is None:
            # Unparsable lock: break it only once it is demonstrably abandoned.
            try:
                age = time.time() - path.stat().st_mtime
            except OSError:
                age = 0.0
            if age > UNREADABLE_STALE_SEC:
                _break_lock_if_unchanged(path, raw, "unreadable metadata")
            else:
                time.sleep(poll)
            continue

        holder_pid = int(holder.get("pid") or 0)
        if not _pid_alive(holder_pid):
            if _break_lock_if_unchanged(path, raw, f"holder pid {holder_pid} is dead"):
                if path == JOB_LOCK_FILE:
                    global _broke_dead_job
                    _broke_dead_job = holder  # the hand-over gate cools down before CUDA work
                continue

        waited = time.monotonic() - start
        if timeout is not None and waited >= timeout:
            raise TimeoutError(
                f"{what} not acquired after {waited:.0f}s "
                f"(held by pid {holder_pid}: {holder.get('label')!r})"
            )
        if waited - last_wait_log >= WAIT_LOG_INTERVAL:
            last_wait_log = waited
            _log(
                f"waiting for {what}: {holder.get('label')!r} "
                f"(pid {holder_pid}, {holder.get('argv0')}, since {holder.get('acquired')}) — "
                f"'{label}' has waited {waited:.0f}s"
            )
        time.sleep(poll)


# --------------------------------------------------------------------------- GPU presence
# 2026-11-20 the RTX 2080 Ti fell off the bus during a UniRig job ("GPU is lost. Reboot the system
# to recover this GPU"); queued jobs then each started on the dead device and failed, and the
# display could not wake until a hard reset. Every GPU call now checks the card is still there
# (nvidia-smi -L, cached briefly) and stops with GpuLostError instead of queueing on a dead card.
# GpuWatchdog.ps1 (same folder) writes gpu_lost.json here while the card is gone; it counts too.
# AAMT_GPU_CHECK=0 skips the check.
GPU_LOST_FILE = _DEFAULT_DIR / "gpu_lost.json"
_GPU_CHECK_TTL = 10.0
_gpu_check_cache: Dict[str, Any] = {"at": 0.0, "ok": True, "detail": ""}


class GpuLostError(RuntimeError):
    """The GPU is gone (driver lost the card); every GPU job fails until it is back (usually a reboot)."""


def gpu_present(fresh: bool = False) -> tuple:
    """(ok, detail). ok is False when nvidia-smi reports the card lost / no device, or the watchdog's
    gpu_lost.json marker exists. A machine without nvidia-smi counts as ok (nothing to check)."""
    now = time.monotonic()
    marker = GPU_LOST_FILE.exists()  # cheap: always looked at, never cached
    if not marker and not fresh and now - _gpu_check_cache["at"] < _GPU_CHECK_TTL:
        return _gpu_check_cache["ok"], _gpu_check_cache["detail"]
    ok, detail = True, ""
    if marker:
        try:
            info = json.loads(GPU_LOST_FILE.read_text(encoding="utf-8-sig"))  # PowerShell 5 writes a BOM
            detail = f"watchdog: GPU lost since {info.get('since', '?')} ({info.get('detail', '')})"
        except Exception:  # noqa: BLE001
            detail = f"watchdog marker {GPU_LOST_FILE}"
        ok = False
    else:
        import shutil
        import subprocess

        exe = shutil.which("nvidia-smi")
        if exe:
            try:
                r = subprocess.run([exe, "-L"], capture_output=True, text=True, timeout=20,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                out = ((r.stdout or "") + (r.stderr or "")).strip()
                if r.returncode != 0 or "GPU " not in out or "lost" in out.lower():
                    ok, detail = False, out.splitlines()[0] if out else f"nvidia-smi exit {r.returncode}"
            except subprocess.TimeoutExpired:
                ok, detail = False, "nvidia-smi hung for 20 s (driver not answering)"
            except OSError as exc:
                detail = f"nvidia-smi not runnable: {exc}"  # can't tell; don't block
    _gpu_check_cache.update(at=now, ok=ok, detail=detail)
    return ok, detail


def check_gpu(label: str = "", fresh: bool = False) -> None:
    """Raise GpuLostError if the card is gone (see gpu_present)."""
    if os.environ.get("AAMT_GPU_CHECK") == "0":
        return
    ok, detail = gpu_present(fresh=fresh)
    if not ok:
        _log(f"GPU LOST - not starting '{label}': {detail}")
        raise GpuLostError(f"GPU lost, not starting '{label}': {detail}. Reboot the PC (or wait for "
                           f"GpuWatchdog to restart the driver) before any GPU job.")


# --------------------------------------------------------------------------- hand-over safety
# 2026-11-20 the lease alone did not keep the card to one CUDA job: model servers (SD :1338,
# TRELLIS, Ollama) keep weights on the GPU after the job that started them lets go of the lease,
# in-process models (Stable Audio, refart) stayed loaded when the idle timer gave the lease away,
# and a dead holder's lease went to the next job at once while the driver (and the dead job's
# children) were still busy. The card was lost twice that night, both times at a hand-over.
# So taking the lease now:
#   1. evicts every model server another job left running (shutdown, then kill the listener;
#      Ollama only unloads its models),
#   2. waits out a cool-down when the previous holder died,
#   3. waits until the card is clear: no game (AAMT_GPU_BLOCK_PROCESSES), no foreign python /
#      ollama process with a CUDA context, used VRAM under AAMT_GPU_IDLE_MIB, two polls in a row;
# and giving it up runs this process's unload hooks and stops the servers it started.
# AAMT_GPU_EVICT=0 keeps foreign servers (the gate then waits for them to go away by themselves).
SERVERS_DIR = _DEFAULT_DIR / "servers"
DEAD_COOLDOWN_SEC = float(os.environ.get("AAMT_GPU_DEAD_COOLDOWN_SEC") or 30)
IDLE_MIB = float(os.environ.get("AAMT_GPU_IDLE_MIB") or 3500)
GATE_POLL_SEC = 3.0
BLOCK_PROCESSES = [p.strip().lower() for p in
                   (os.environ.get("AAMT_GPU_BLOCK_PROCESSES") or "D2R.exe,D2RLoader.exe").split(",") if p.strip()]
FOREIGN_CUDA_NAMES = [p.strip().lower() for p in
                      (os.environ.get("AAMT_GPU_FOREIGN_NAMES")
                       or "python.exe,pythonw.exe,ollama.exe,ollama_llama_server.exe,llama-server.exe").split(",")
                      if p.strip()]
VRAM_FRACTION = float(os.environ.get("AAMT_GPU_VRAM_FRACTION") or 0.9)

_unload_hooks: Dict[str, Any] = {}
_broke_dead_job: Optional[Dict[str, Any]] = None


def _run(cmd: list, timeout: float = 20) -> str:
    import subprocess

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, errors="replace",
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return r.stdout or ""
    except Exception:  # noqa: BLE001
        return ""


def _shared_setting(fn_name: str, default: Any) -> Any:
    """Port settings live in Tools\\Shared\\tool_paths.py; fall back to the stock ports."""
    try:
        shared = str(Path(__file__).resolve().parent.parent / "Shared")
        if shared not in sys.path:
            sys.path.append(shared)
        import tool_paths  # type: ignore

        return getattr(tool_paths, fn_name)()
    except Exception:  # noqa: BLE001
        return default


def _known_servers() -> list:
    """Model servers that keep weights on the GPU between requests, plus registered ones."""
    servers = [
        {"name": "SD 3.5", "port": int(_shared_setting("sd_port", 1338)), "kind": "http", "shutdown": "/shutdown"},
        {"name": "TRELLIS", "port": int(_shared_setting("trellis_port", 7960)), "kind": "http",
         "shutdown": "/shutdown"},
    ]
    ollama = (os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
    try:
        servers.append({"name": "Ollama", "port": int(ollama.rsplit(":", 1)[1]), "kind": "ollama"})
    except (IndexError, ValueError):
        servers.append({"name": "Ollama", "port": 11434, "kind": "ollama"})
    owners: Dict[int, Dict[str, Any]] = {}
    if SERVERS_DIR.is_dir():
        for f in SERVERS_DIR.glob("*.json"):
            try:
                entry = json.loads(f.read_text(encoding="utf-8"))
                owners[int(entry["port"])] = {**entry, "file": str(f)}
            except Exception:  # noqa: BLE001
                continue
    for s in servers:
        if s["port"] in owners:
            s.update({k: v for k, v in owners.pop(s["port"]).items() if k not in ("kind", "shutdown")})
    servers.extend({"kind": "http", "shutdown": "/shutdown", **e} for e in owners.values())
    return servers


def _port_listening(port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _listener_pids(port: int) -> list:
    pids = set()
    for line in _run(["netstat", "-ano", "-p", "TCP"]).splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[1].endswith(f":{port}") and parts[3].upper() == "LISTENING":
            try:
                pids.add(int(parts[4]))
            except ValueError:
                pass
    pids.discard(0)
    return sorted(pids)


def register_server(name: str, port: int, shutdown: str = "/shutdown") -> None:
    """Record that this job started a model server on `port` (it is stopped when the lease ends,
    and evicted by the next job if this process died first)."""
    if os.environ.get("AAMT_GPU_HUB_DISABLE") == "1":
        return
    owner = os.environ.get(JOB_OWNER_ENV) or str(os.getpid())
    try:
        SERVERS_DIR.mkdir(parents=True, exist_ok=True)
        (SERVERS_DIR / f"{int(port)}.json").write_text(json.dumps(
            {"name": name, "port": int(port), "shutdown": shutdown, "owner": int(owner),
             "started": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=2), encoding="utf-8")
    except OSError as exc:
        _log(f"could not register server {name}:{port}: {exc}")


def _forget_server(port: int) -> None:
    try:
        (SERVERS_DIR / f"{int(port)}.json").unlink()
    except OSError:
        pass


def _stop_server(s: Dict[str, Any], why: str) -> None:
    import urllib.request

    port = int(s["port"])
    if not _port_listening(port):
        _forget_server(port)
        return
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    base = f"http://127.0.0.1:{port}"
    if s.get("kind") == "ollama":
        try:
            with opener.open(base + "/api/ps", timeout=5) as r:
                models = [m.get("name") or m.get("model") for m in json.loads(r.read()).get("models", [])]
        except Exception:  # noqa: BLE001
            models = []
        for m in filter(None, models):
            _log(f"unloading Ollama model {m} ({why})")
            try:
                req = urllib.request.Request(base + "/api/generate", method="POST",
                                             data=json.dumps({"model": m, "keep_alive": 0}).encode(),
                                             headers={"Content-Type": "application/json"})
                opener.open(req, timeout=30).read()
            except Exception as exc:  # noqa: BLE001
                _log(f"Ollama unload of {m} failed: {exc}")
        return
    _log(f"stopping {s['name']} on :{port} ({why})")
    try:
        opener.open(base + s.get("shutdown", "/shutdown"), timeout=5).read()
    except Exception:  # noqa: BLE001
        pass
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and _port_listening(port):
        time.sleep(1)
    if _port_listening(port):
        for pid in _listener_pids(port):
            _log(f"{s['name']} still up after /shutdown: taskkill pid {pid}")
            _run(["taskkill", "/F", "/T", "/PID", str(pid)], timeout=30)
        time.sleep(2)
    _forget_server(port)


def register_unload(name: str, fn: Any) -> None:
    """In-process models: `fn()` drops them from the GPU; it runs before this process gives up the lease."""
    _unload_hooks[name] = fn


def _run_unload_hooks() -> None:
    for name, fn in list(_unload_hooks.items()):
        try:
            fn()
            _log(f"unloaded {name} before giving up the GPU")
        except Exception as exc:  # noqa: BLE001
            _log(f"unload hook {name} failed: {exc}")


def _evict_foreign_servers(me: int) -> None:
    if os.environ.get("AAMT_GPU_EVICT") == "0":
        return
    for s in _known_servers():
        if int(s.get("owner") or 0) == me:
            continue
        if _port_listening(int(s["port"])):
            _stop_server(s, "left on the GPU by an earlier job")
        else:
            _forget_server(int(s["port"]))


def _stop_own_servers(me: int) -> None:
    if os.environ.get("AAMT_GPU_KEEP_SERVERS") == "1":
        return
    for s in _known_servers():
        if int(s.get("owner") or 0) == me:
            _stop_server(s, "job finished")


def _running_blockers() -> list:
    if not BLOCK_PROCESSES:
        return []
    found = []
    for line in _run(["tasklist", "/FO", "CSV", "/NH"]).splitlines():
        name = line.split(",", 1)[0].strip('"').lower()
        if name in BLOCK_PROCESSES:
            found.append(name)
    return sorted(set(found))


def _foreign_cuda_processes() -> list:
    """Other python / ollama processes holding a CUDA context (WDDM reports no per-process VRAM,
    but it does list the processes)."""
    import shutil

    exe = shutil.which("nvidia-smi")
    if not exe:
        return []
    mine = {os.getpid(), os.getppid()}
    out = []
    for line in _run([exe, "--query-compute-apps=pid,process_name", "--format=csv,noheader"]).splitlines():
        pid_s, _, path = line.partition(",")
        try:
            pid = int(pid_s.strip())
        except ValueError:
            continue
        name = Path(path.strip()).name.lower()
        if pid not in mine and name in FOREIGN_CUDA_NAMES:
            out.append(f"{pid} {path.strip()}")
    return out


def vram_used_mib() -> Optional[float]:
    import shutil

    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        return float(_run([exe, "--query-gpu=memory.used", "--format=csv,noheader,nounits"]).splitlines()[0])
    except (IndexError, ValueError):
        return None


def gpu_clear() -> tuple:
    """(clear, reasons). The card is clear when no game, no foreign CUDA python and little VRAM in use."""
    reasons = []
    games = _running_blockers()
    if games:
        reasons.append("game running: " + ", ".join(games))
    foreign = _foreign_cuda_processes()
    if foreign:
        reasons.append("other CUDA processes: " + "; ".join(foreign))
    used = vram_used_mib()
    if used is not None and used > IDLE_MIB:
        reasons.append(f"{used:.0f} MiB VRAM in use (idle limit {IDLE_MIB:.0f}, AAMT_GPU_IDLE_MIB)")
    return not reasons, reasons


def _handover_gate(label: str, timeout: Optional[float], start: float) -> None:
    """Run right after this process took the job lease, before any CUDA work."""
    global _broke_dead_job
    if os.environ.get("AAMT_GPU_GATE") == "0":
        return
    dead, _broke_dead_job = _broke_dead_job, None
    if dead:
        _log(f"previous GPU job died (pid {dead.get('pid')}: {dead.get('label')!r}); "
             f"cooling down {DEAD_COOLDOWN_SEC:.0f}s before '{label}'")
        time.sleep(DEAD_COOLDOWN_SEC)
    check_gpu(label, fresh=True)
    _evict_foreign_servers(os.getpid())
    clear_polls, last_log = 0, -WAIT_LOG_INTERVAL
    while True:
        clear, reasons = gpu_clear()
        clear_polls = clear_polls + 1 if clear else 0
        if clear_polls >= 2:
            break
        waited = time.monotonic() - start
        if not clear:
            if timeout is not None and waited >= timeout:
                raise TimeoutError(f"GPU not clear after {waited:.0f}s for '{label}': " + " | ".join(reasons))
            if waited - last_log >= WAIT_LOG_INTERVAL:
                last_log = waited
                _log(f"'{label}' has the lease but waits for a clear card: " + " | ".join(reasons))
        time.sleep(GATE_POLL_SEC)
    check_gpu(label, fresh=True)


def cap_torch_vram(fraction: Optional[float] = None) -> None:
    """Make PyTorch raise out-of-memory instead of spilling into shared memory (driver resets,
    bugcheck 0x116 on 2026-11-19). Only touches processes that already use CUDA."""
    torch = sys.modules.get("torch")
    if torch is None or os.environ.get("AAMT_GPU_VRAM_FRACTION") == "0":
        return
    try:
        if not torch.cuda.is_initialized() or getattr(torch.cuda, "_aamt_capped", False):
            return
        frac = float(fraction or VRAM_FRACTION)
        torch.cuda.set_per_process_memory_fraction(frac, 0)
        torch.cuda._aamt_capped = True
        _log(f"PyTorch VRAM cap {frac:.0%} for pid {os.getpid()}")
    except Exception as exc:  # noqa: BLE001
        _log(f"VRAM cap skipped: {exc}")


def _inherited_job() -> bool:
    """True if a parent process holds the lease and passed it down to us."""
    holder = _parse_holder(_read_lock_raw(JOB_LOCK_FILE))
    if holder is None:
        return False
    if holder.get("pid") == os.getpid():
        return True  # held by another copy of this module in our own process (Shared shim)
    owner = os.environ.get(JOB_OWNER_ENV)
    return bool(owner) and str(holder.get("pid")) == owner and _pid_alive(int(owner))


def _ensure_job(label: str, timeout: Optional[float], poll: float, start: float) -> None:
    """Take the process-wide GPU job lease if this process doesn't hold it yet."""
    global _job_held
    with _job_mutex:
        if _job_held:
            return
        if _inherited_job():
            return
        _wait_acquire(JOB_LOCK_FILE, f"{Path(sys.argv[0]).name if sys.argv else 'python'}: {label}",
                      "GPU job", timeout, poll, start)
        try:
            _handover_gate(label, timeout, start)
        except BaseException:
            _release(JOB_LOCK_FILE, "job")
            raise
        _job_held = True
        os.environ[JOB_OWNER_ENV] = str(os.getpid())
        _log(f"GPU job lease taken by pid {os.getpid()} ({label})")


def hold_gpu_job(label: str, timeout: Optional[float] = None, poll: float = DEFAULT_POLL) -> None:
    """Take the GPU job lease without the request lock — call before launching a
    model server (its startup loads weights onto the GPU outside any request)."""
    global _job_active
    if os.environ.get("AAMT_GPU_HUB_DISABLE") == "1":
        return
    check_gpu(label)
    with _job_mutex:
        _job_active += 1
    try:
        _ensure_job(label, timeout, poll, time.monotonic())
    finally:
        _job_request_done()


def release_gpu_job() -> None:
    """Give up the process-wide lease now (no-op if not held or a request is in flight)."""
    global _job_held, _job_timer
    with _job_mutex:
        if not _job_held or _job_active:
            return
        if _job_timer is not None:
            _job_timer.cancel()
            _job_timer = None
        # Nothing of ours may stay on the card once the next job (or the game) can start.
        _run_unload_hooks()
        try:
            _stop_own_servers(os.getpid())
        except Exception as exc:  # noqa: BLE001
            _log(f"stopping own servers failed: {exc}")
        _release(JOB_LOCK_FILE, "job")
        _job_held = False
        if os.environ.get(JOB_OWNER_ENV) == str(os.getpid()):
            del os.environ[JOB_OWNER_ENV]
        _log(f"GPU job lease released by pid {os.getpid()}")


def _idle_check() -> None:
    with _job_mutex:
        if _job_held and not _job_active and time.monotonic() - _job_last_use >= JOB_IDLE_SEC - 1:
            _log(f"GPU job idle for {JOB_IDLE_SEC:.0f}s")
            release_gpu_job()


def _job_request_done() -> None:
    global _job_active, _job_last_use, _job_timer
    with _job_mutex:
        _job_active -= 1
        _job_last_use = time.monotonic()
        if _job_held and not _job_active and JOB_IDLE_SEC > 0:
            if _job_timer is not None:
                _job_timer.cancel()
            _job_timer = threading.Timer(JOB_IDLE_SEC, _idle_check)
            _job_timer.daemon = True
            _job_timer.start()


atexit.register(release_gpu_job)


@contextmanager
def acquire_gpu(
    label: str,
    timeout: Optional[float] = None,
    poll: float = DEFAULT_POLL,
    enabled: bool = True,
):
    """
    Context manager: block until this process holds the GPU job lease and the
    exclusive per-request GPU lock.

    label   -- short description shown to other waiting processes.
    timeout -- max seconds to wait (None = wait forever). Raises TimeoutError.
    poll    -- seconds between lock attempts while waiting.
    enabled -- pass False for calls that don't touch the GPU (e.g. Ollama with
               num_gpu=0 running purely on CPU) to skip locking.
    """
    global _job_active
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

    check_gpu(label)
    start = time.monotonic()
    with _job_mutex:
        _job_active += 1
    try:
        _ensure_job(label, timeout, poll, start)
        _wait_acquire(LOCK_FILE, label, "GPU", timeout, poll, start)
    except BaseException:
        _job_request_done()
        raise
    # The card can drop out while we waited in the queue: look again before running.
    try:
        check_gpu(label, fresh=True)
    except GpuLostError:
        _release(LOCK_FILE, label)
        _job_request_done()
        release_gpu_job()
        raise

    cap_torch_vram()
    _tls.depth = 1
    _log(f"acquired for '{label}' (pid {os.getpid()})")
    try:
        yield
    finally:
        _tls.depth = 0
        _release(LOCK_FILE, label)
        _job_request_done()
        _log(f"released by '{label}'")


def current_holder() -> Optional[Dict[str, Any]]:
    """Diagnostics: metadata of the current request-lock holder, or None if free."""
    return _parse_holder(_read_lock_raw())


def current_job() -> Optional[Dict[str, Any]]:
    """Diagnostics: metadata of the current GPU job lease holder, or None if free."""
    return _parse_holder(_read_lock_raw(JOB_LOCK_FILE))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="GPU hub lock diagnostics/testing")
    parser.add_argument("--status", action="store_true", help="show current holders")
    parser.add_argument("--check", action="store_true", help="is the GPU still there? exit 0 yes, 3 lost")
    parser.add_argument("--hold", type=float, default=0.0, metavar="SEC",
                        help="acquire the lock and hold it for SEC seconds")
    parser.add_argument("--then", type=float, default=0.0, metavar="SEC",
                        help="after --hold, stay alive SEC more seconds (lease kept, request lock free)")
    parser.add_argument("--label", default="gpu_hub-cli")
    parser.add_argument("--timeout", type=float, default=None)
    args = parser.parse_args()

    if args.check:
        ok, detail = gpu_present(fresh=True)
        print(("GPU present" if ok else "GPU LOST") + (f": {detail}" if detail else ""))
        sys.exit(0 if ok else 3)

    if args.status or not args.hold:
        ok, detail = gpu_present(fresh=True)
        print("gpu: " + ("present" if ok else f"LOST ({detail})"))
        for name, holder in (("job", current_job()), ("request", current_holder())):
            if holder:
                alive = _pid_alive(int(holder.get("pid") or 0))
                print(f"{name}: " + json.dumps({**holder, "pid_alive": alive}, indent=2))
            else:
                print(f"{name}: free")
        clear, reasons = gpu_clear()
        print("card: " + ("clear" if clear else "BUSY - " + " | ".join(reasons)))
        for s in _known_servers():
            if _port_listening(int(s["port"])):
                print(f"server up: {s['name']} :{s['port']}" + (f" (owner pid {s['owner']})" if s.get("owner") else
                                                                 " (not registered)"))
        sys.exit(0)

    with acquire_gpu(args.label, timeout=args.timeout):
        print(f"holding GPU lock for {args.hold}s...", flush=True)
        time.sleep(args.hold)
    if args.then:
        print(f"between requests for {args.then}s (lease held)...", flush=True)
        time.sleep(args.then)
    print("done", flush=True)
