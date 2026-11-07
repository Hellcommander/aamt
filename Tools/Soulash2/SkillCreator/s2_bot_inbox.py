#!/usr/bin/env python3
"""Drive a running Soulash 2 TestBot through its inbox (TestBot build bb6c00f8+, Inbox=1).

  python s2_bot_inbox.py status                 # state, job, step, screen, log tail
  python s2_bot_inbox.py send FILE [--name N]   # drop a script into the inbox (tmp + rename)
  python s2_bot_inbox.py run FILE [--timeout S] # send, wait for that job, print result + log tail
  python s2_bot_inbox.py wait NAME [--timeout S]
  python s2_bot_inbox.py live [--out PNG]       # copy the current live.png
  python s2_bot_inbox.py stop                   # abort the running job

Writes only into <game>/SoulashExtender/TestBot/inbox (the extender's own folder).
Scripts sent here must never press the editor's Accept (1710,1035).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Optional

GAME_DIR = Path(r"D:\games\Steam\steamapps\common\Soulash 2")
DONE_STATES = {"finished", "aborted", "stopped", "idle", "not_running", "exited"}


def bot_dir(game_dir: Path = GAME_DIR) -> Path:
    return Path(game_dir) / "SoulashExtender" / "TestBot"


def read_status(game_dir: Path = GAME_DIR) -> Optional[dict]:
    p = bot_dir(game_dir) / "status.json"
    for _ in range(5):
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (json.JSONDecodeError, PermissionError):
            time.sleep(0.1)
    return None


def status_age_s(st: dict) -> Optional[float]:
    import datetime as dt

    try:
        t = dt.datetime.fromisoformat(str(st["updated_utc"]).replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return None
    return (dt.datetime.now(dt.timezone.utc) - t).total_seconds()


def format_status(st: Optional[dict], tail: int = 8) -> str:
    if st is None:
        return "no status.json (game not started with the live-feedback bot)"
    job = st.get("job") or {}
    step = st.get("step") or {}
    age = status_age_s(st)
    lines = [
        f"state={st.get('state')} result={st.get('result')} screen={st.get('screen')} "
        f"age={'?' if age is None else f'{age:.1f}s'} pid={st.get('pid')}",
        f"job={job.get('index')}:{job.get('name')} ({job.get('source')}) steps {st.get('steps_done')}/{st.get('steps_total')} "
        f"checks={st.get('checks')} failures={st.get('failures')}",
    ]
    if step:
        lines.append(f"step {step.get('index')} line {step.get('line')}: {step.get('command')} ({step.get('elapsed_ms')} ms)")
    if st.get("waiting_for"):
        lines.append(f"waiting_for: {st['waiting_for']}")
    if st.get("last_failure"):
        lines.append(f"last_failure: {st['last_failure']}")
    if st.get("reason"):
        lines.append(f"reason: {st['reason']}")
    inbox = st.get("inbox") or {}
    if inbox.get("last_error"):
        lines.append(f"inbox error: {inbox['last_error']}")
    if st.get("run_dir"):
        lines.append(f"run_dir: {st['run_dir']}")
    for ln in (st.get("log_tail") or [])[-tail:]:
        lines.append(f"  | {ln}")
    return "\n".join(lines)


def send(text: str, name: str, game_dir: Path = GAME_DIR) -> str:
    """Write the script under a temp name, then rename so the bot never sees half a file."""
    inbox = bot_dir(game_dir) / "inbox"
    if not inbox.is_dir():
        raise SystemExit(f"inbox not found: {inbox} (start the game with Inbox=1 first)")
    if "1710 1035" in text:
        raise SystemExit("refusing: script clicks the editor's Accept button (1710,1035)")
    stem = "".join(c if c.isalnum() or c in "_-." else "_" for c in name)
    if stem.endswith(".script"):
        stem = stem[: -len(".script")]
    stem = f"{time.strftime('%H%M%S')}_{stem}"
    tmp = inbox / f"{stem}.tmp"
    tmp.write_text(text if text.endswith("\n") else text + "\n", encoding="ascii")
    final = inbox / f"{stem}.script"
    tmp.replace(final)
    return final.name


def wait(name: str, timeout: float = 300.0, game_dir: Path = GAME_DIR, quiet: bool = False) -> Optional[dict]:
    """Wait until the job named exactly `name` (as returned by send()) has run to an end state."""
    deadline = time.time() + timeout
    started = False
    last = ""
    st = None
    while time.time() < deadline:
        st = read_status(game_dir)
        if st:
            job = st.get("job") or {}
            jname = str(job.get("name") or "")
            mine = jname == name  # exact: every send() name is unique (time prefix)
            if mine:
                started = True
            step = (st.get("step") or {}).get("command")
            line = f"{st.get('state')} {jname} {step or ''}"
            if not quiet and line != last:
                print(f"  .. {line}", flush=True)
                last = line
            if mine and st.get("state") in DONE_STATES:
                return st
            if st.get("state") == "exited":
                print("game exited")
                return st
            err = (st.get("inbox") or {}).get("last_error")
            if not started and err and name.split(".")[0] in str(err):
                print(f"inbox rejected the script: {err}")
                return st
        time.sleep(0.5)
    print(f"timeout after {timeout:.0f}s waiting for {name}")
    return st


def copy_live(out: Path, game_dir: Path = GAME_DIR) -> Path:
    src = bot_dir(game_dir) / "live.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, out)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game-dir", default=str(GAME_DIR))
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    s = sub.add_parser("send")
    s.add_argument("file")
    s.add_argument("--name")
    r = sub.add_parser("run")
    r.add_argument("file")
    r.add_argument("--name")
    r.add_argument("--timeout", type=float, default=300)
    w = sub.add_parser("wait")
    w.add_argument("name")
    w.add_argument("--timeout", type=float, default=300)
    lv = sub.add_parser("live")
    lv.add_argument("--out", default="live.png")
    sub.add_parser("stop")
    a = ap.parse_args(argv)
    gd = Path(a.game_dir)

    if a.cmd == "status":
        print(format_status(read_status(gd), tail=16))
    elif a.cmd in ("send", "run"):
        text = Path(a.file).read_text(encoding="utf-8")
        name = send(text, a.name or Path(a.file).stem, gd)
        print(f"sent {name}")
        if a.cmd == "run":
            st = wait(name, a.timeout, gd)
            print(format_status(st, tail=12))
            return 0 if st and st.get("result") == "PASS" else 1
    elif a.cmd == "wait":
        print(format_status(wait(a.name, a.timeout, gd), tail=12))
    elif a.cmd == "live":
        print(copy_live(Path(a.out), gd))
    elif a.cmd == "stop":
        (bot_dir(gd) / "inbox" / "stop").write_text("stop\n", encoding="ascii")
        print("stop requested")
    return 0


if __name__ == "__main__":
    sys.exit(main())
