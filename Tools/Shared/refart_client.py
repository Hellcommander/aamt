#!/usr/bin/env python3
"""refart: reference-image art generation, instruction edits, inpainting, and automatic layer splitting.

Runs Shared/refart/refart_cli.py inside its own venv (AAMT_REFART_HOME, default E:\\tools\\refart\\.venv) so the
SD3.5 server's environment is never touched. See Shared/REFART.md.

  python refart_client.py --status
  python refart_client.py generate --prompt "..." --ref char.png --out new.png
  python refart_client.py edit --image char.png --instruction "make the character wear a filthy toga" --out toga.png
  python refart_client.py inpaint --image char.png --mask mask.png --prompt "..." --out fixed.png
  python refart_client.py segment --image char.png --phrase head --phrase horn --out-dir masks/
  python refart_client.py layers --spec art.autolayers.json --out-dir layers/ --preview prev/
  python refart_client.py overlay --base base.png --instruction "..." --phrase toga --out toga_layer.png

From Python: from refart_client import run, status; run("edit", image=..., instruction=..., out=...)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

HERE = Path(__file__).resolve().parent
CLI = HERE / "refart" / "refart_cli.py"


def home() -> Path:
    return Path(os.environ.get("AAMT_REFART_HOME") or r"E:\tools\refart")


def _py() -> Path:
    return home() / ".venv" / "Scripts" / "python.exe"


def _env() -> Dict[str, str]:
    env = dict(os.environ)
    env.setdefault("HF_HOME", r"D:\hf-cache")
    env.setdefault("HF_HUB_OFFLINE", "1")  # weights are installed by setup; never fetch mid-run
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def status() -> Dict[str, Any]:
    if not _py().exists():
        return {"venv": False}
    r = subprocess.run([str(_py()), str(CLI), "status"], env=_env(), capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        s = json.loads(r.stdout)
    except ValueError:
        s = {"error": (r.stderr or "")[-400:]}
    s["venv"] = True
    return s


def run(cmd: str, **kw: Any) -> Any:
    """run("edit", image=Path, instruction=str, out=Path) -> the CLI's JSON result. Lists repeat the flag."""
    args = [str(_py()), str(CLI), cmd]
    for k, v in kw.items():
        if v is None or v is False:
            continue
        flag = "--" + k.replace("_", "-")
        for item in (v if isinstance(v, (list, tuple)) else [v]):
            args += [flag] if item is True else [flag, str(item)]
    r = subprocess.run(args, env=_env(), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        # The GPU hub logs its lease release after the traceback, so the stderr's last line is not the
        # error. Put the exception line last: callers that print only the last line then show the cause.
        err = r.stderr or ""
        exc = [l for l in err.splitlines() if re.match(r"^[A-Za-z_][\w.]*(Error|Exception)\b", l)]
        raise RuntimeError(f"refart {cmd} failed:\n{err[-2000:]}" + (f"\n{exc[-1]}" if exc else ""))
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    return json.loads(lines[-1]) if lines else None


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        print(json.dumps(status(), indent=1))
        return 0
    return subprocess.call([str(_py()), str(CLI), *sys.argv[1:]], env=_env())


if __name__ == "__main__":
    sys.exit(main())
