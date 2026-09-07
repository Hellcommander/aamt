#!/usr/bin/env python3
"""Wait for in-flight SD job, then run remaining branding jobs strictly sequentially."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

TOOLS = Path(r"D:\games\Steam\steamapps\common\Transcendence\Tools\Soulash2")
GEN = TOOLS / "generate_mod_branding_assets.py"
MODS = Path(r"E:\SteamLibrary\steamapps\common\Soulash 2\data\mods")
PING = "http://127.0.0.1:1338/ping"
LOCK = Path(__import__("os").environ.get("TEMP", ".")) / "soulash_sd_branding.lock"

JOBS = [
    {"mod": MODS / "arendeth_hemohydraulic_magic", "theme": "hemohydraulic", "mode": "icon",
     "backup": False, "prefer_keep_backup": False, "note": "redo icon with SD"},
    {"mod": MODS / "arendeth_water_magic", "theme": "hydromancy", "mode": "icon",
     "backup": True, "prefer_keep_backup": True},
    {"mod": MODS / "arendeth_water_magic", "theme": "hydromancy", "mode": "thumbnail",
     "backup": False, "prefer_keep_backup": True},
]


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def wait_for_sd_idle(max_wait: float = 7200.0) -> None:
    deadline = time.monotonic() + max_wait
    while time.monotonic() < deadline:
        if LOCK.exists() and time.time() - LOCK.stat().st_mtime < 7200:
            time.sleep(15)
            continue
        try:
            urllib.request.urlopen(PING, timeout=5)
            return
        except Exception:
            time.sleep(15)
    log("WARN: SD idle wait timed out")


def run_job(job: dict, idx: int) -> dict:
    cmd = [sys.executable, str(GEN), "--mod-path", str(job["mod"]), "--theme", job["theme"],
           "--mode", job["mode"], "--quality", "mechanical", "--use-sd", "--max-attempts", "2"]
    if job.get("prefer_keep_backup"):
        cmd.append("--prefer-keep-backup")
    if not job.get("backup", False):
        cmd.append("--skip-backup")
    label = f"{job['mod'].name}/{job['mode']}"
    log(f"JOB {idx}: {label} ({job.get('note', '')})")
    t0 = time.monotonic()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.monotonic() - t0
    print(proc.stdout, flush=True)
    if proc.stderr:
        log(f"STDERR: {proc.stderr[:2000]}")
    return {"job": label, "exit_code": proc.returncode, "elapsed_sec": round(elapsed, 1),
            "stdout_tail": (proc.stdout or "")[-4000:]}


def main() -> int:
    log("Waiting for current SD job to finish...")
    wait_for_sd_idle()
    log("SD idle; running remaining jobs sequentially.")
    results = []
    for i, job in enumerate(JOBS, 1):
        wait_for_sd_idle()
        results.append(run_job(job, i))
        time.sleep(5)
    report = TOOLS / "overnight_branding_report.json"
    existing = {}
    if report.exists():
        try:
            existing = json.loads(report.read_text(encoding="utf-8"))
        except Exception:
            pass
    existing["continuation_finished"] = datetime.now().isoformat()
    existing["continuation_jobs"] = results
    report.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    log(f"Report updated: {report}")
    return 0 if all(r["exit_code"] == 0 for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
