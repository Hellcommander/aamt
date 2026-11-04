#!/usr/bin/env python3
"""
Overnight sequential branding runner.

Asset policy: every asset is Stable Diffusion art, generated sequentially (one GPU job
at a time). There is no procedural fallback: if the SD server cannot be brought up or a
draft fails QA the job fails and the run reports it.

Order:
  1. hemohydraulic icon (SD)
  2. water magic icon (SD)
  3. hemohydraulic thumbnail (SD)
  4. water magic thumbnail (SD)

Single SD server on port 1338; do NOT start a second instance.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from s2_game_paths import mods_dir  # noqa: E402

MODS = mods_dir()
SD_SERVER = Path(r"E:\tools\sd3.5\sd3.5\server.py")
GEN = TOOLS / "generate_mod_branding_assets.py"
SD_PORT = 1338
PING_URL = f"http://127.0.0.1:{SD_PORT}/ping"
PAUSE_BETWEEN_JOBS_SEC = 5

# Phase 1 — SD icons (drafts rendered at SD's quality floor, then downscaled to 32x32)
ICON_JOBS = [
    {"mod": MODS / "arendeth_hemohydraulic_magic", "theme": "hemohydraulic", "mode": "icon",
     "prefer_keep_backup": False, "backup": True, "use_sd": True},
    {"mod": MODS / "arendeth_water_magic", "theme": "hydromancy", "mode": "icon",
     "prefer_keep_backup": True, "backup": True, "use_sd": True},
]

# Phase 2 — SD thumbnails (sequential, one GPU job at a time)
THUMB_JOBS = [
    {"mod": MODS / "arendeth_hemohydraulic_magic", "theme": "hemohydraulic", "mode": "thumbnail",
     "prefer_keep_backup": False, "backup": False, "use_sd": True},
    {"mod": MODS / "arendeth_water_magic", "theme": "hydromancy", "mode": "thumbnail",
     "prefer_keep_backup": True, "backup": False, "use_sd": True},
]

ALL_JOBS = ICON_JOBS + THUMB_JOBS


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return False
        except OSError:
            return True


def ping_sd(timeout: float = 10.0) -> bool:
    try:
        with urllib.request.urlopen(PING_URL, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status == 200 and "ok" in body.lower()
    except Exception:
        return False


def sd_generation_works() -> bool:
    """Ping is not enough — verify model can actually generate."""
    if not ping_sd():
        return False
    body = json.dumps({
        "prompt": "tiny red dot",
        "width": 512,
        "height": 512,
        "steps": 2,
        "seed": 99,
    }).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{SD_PORT}/v1/images/generations",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            return resp.status == 200
    except Exception as exc:
        log(f"SD generation probe failed: {exc}")
        return False


def start_sd_server() -> subprocess.Popen:
    env = os.environ.copy()
    env["SD_ALLOW_NONADMIN"] = "1"
    log(f"Starting SD server on port {SD_PORT} (model_cpu_offload, ~7GB headroom)...")
    return subprocess.Popen(
        [sys.executable, str(SD_SERVER), "--host", "127.0.0.1", "--port", str(SD_PORT)],
        cwd=str(SD_SERVER.parent),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )


def ensure_sd_server() -> bool:
    """Ensure exactly one healthy SD server; restart if ping OK but model broken."""
    if ping_sd() and sd_generation_works():
        log("SD server healthy and model loads.")
        return True

    if port_in_use(SD_PORT):
        log("SD port bound but model broken — need fresh server (close broken instance).")
        log("Waiting 30s for port to free (user may close broken console)...")
        for _ in range(6):
            time.sleep(5)
            if not port_in_use(SD_PORT):
                break
        if port_in_use(SD_PORT):
            log("ABORT: port 1338 still bound. Close the broken SD server console.")
            return False

    proc = start_sd_server()
    deadline = time.monotonic() + 25 * 60
    while time.monotonic() < deadline:
        if ping_sd():
            log("SD /ping OK; probing model load (first load may take several minutes)...")
            if sd_generation_works():
                log("SD server ready.")
                return True
        if proc.poll() is not None:
            log(f"SD server exited with code {proc.returncode}")
            return False
        time.sleep(15)
    log("Timed out waiting for SD server model load.")
    return False


def run_image_job(job: dict, job_index: int, total_jobs: int) -> dict:
    mod_path: Path = job["mod"]
    cmd = [
        sys.executable, str(GEN),
        "--mod-path", str(mod_path),
        "--theme", job["theme"],
        "--mode", job["mode"],
        "--quality", "mechanical",
        "--max-attempts", "2",
    ]
    if not job.get("use_sd", True):
        cmd.append("--no-sd")
    if job.get("prefer_keep_backup"):
        cmd.append("--prefer-keep-backup")
    if not job.get("backup", False):
        cmd.append("--skip-backup")

    label = f"{mod_path.name} / {job['mode']}"
    source = f"SD {job['mode']}" if job.get("use_sd", True) else f"procedural {job['mode']} (--no-sd)"
    log(f"=== JOB {job_index + 1}/{total_jobs}: {label} ({job['theme']}, {source}) ===")
    t0 = time.monotonic()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.monotonic() - t0
    print(proc.stdout, flush=True)
    if proc.stderr:
        log(f"STDERR: {proc.stderr}")

    result = {
        "job": job_index + 1,
        "mod": mod_path.name,
        "theme": job["theme"],
        "mode": job["mode"],
        "source": source,
        "exit_code": proc.returncode,
        "elapsed_sec": round(elapsed, 1),
        "stdout_tail": (proc.stdout or "")[-6000:],
    }
    try:
        summary_start = (proc.stdout or "").rfind("{")
        if summary_start >= 0:
            result["summary"] = json.loads((proc.stdout or "")[summary_start:])
    except Exception:
        pass

    log(f"=== DONE JOB {job_index + 1}/{total_jobs}: {label} exit={proc.returncode} elapsed={elapsed:.0f}s ===")
    time.sleep(PAUSE_BETWEEN_JOBS_SEC)
    return result


def verify_assets() -> list:
    from PIL import Image

    mods = {j["mod"].name for j in ALL_JOBS}
    report = []
    for mod_name in sorted(mods):
        mod = MODS / mod_name
        for name, exp_size in (("S.png", (32, 32)), ("thumbnail2.png", (800, 600))):
            path = mod / name
            entry = {"mod": mod_name, "file": name, "exists": path.exists()}
            if path.exists():
                with Image.open(path) as img:
                    entry["size"] = list(img.size)
                    entry["bytes"] = path.stat().st_size
                    entry["dimensions_ok"] = img.size == exp_size
            report.append(entry)
    return report


def main() -> int:
    log("Sequential overnight branding runner starting.")
    log("Policy: all assets are SD art; no procedural fallback.")
    log("Order: hemo icon -> water icon -> hemo thumb -> water thumb (all SD)")

    results = []
    total = len(ALL_JOBS)

    if not ensure_sd_server():
        log("ABORT: SD server unavailable. No procedural placeholders were written.")
        return 1

    # Phase 1: SD icons (one at a time)
    log("=== PHASE 1: SD icons (sequential) ===")
    for i, job in enumerate(ICON_JOBS):
        if not job["mod"].exists():
            log(f"SKIP missing mod: {job['mod']}")
            continue
        results.append(run_image_job(job, i, total))

    # Phase 2: SD thumbnails (one at a time)
    log("=== PHASE 2: SD thumbnails (sequential) ===")
    for i, job in enumerate(THUMB_JOBS, start=len(ICON_JOBS)):
        if not job["mod"].exists():
            log(f"SKIP missing mod: {job['mod']}")
            continue
        results.append(run_image_job(job, i, total))

    verification = verify_assets()
    log("=== VERIFICATION ===")
    log(json.dumps(verification, indent=2))

    out_log = TOOLS / "overnight_branding_report.json"
    report = {
        "finished": datetime.now().isoformat(),
        "policy": {
            "icons": "SD (rendered at the SD quality floor, downscaled to 32x32)",
            "thumbnails": "SD; no procedural fallback (job fails instead)",
        },
        "constraints": {
            "sequential": True,
            "sd_jobs": "icons and thumbnails",
            "offload": "model_cpu_offload (sequential on OOM)",
            "thumb_settings": "1024x768 @ 24 steps",
            "oom_fallback": "reduced resolution once, then the job fails",
        },
        "jobs": results,
        "verification": verification,
    }
    out_log.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log(f"Report saved: {out_log}")

    failed = [r for r in results if r.get("exit_code", 1) != 0]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
