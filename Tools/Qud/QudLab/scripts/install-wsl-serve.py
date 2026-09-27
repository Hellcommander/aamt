"""Copy wsl-vllm-serve.sh into WSL with Unix (LF) newlines."""
from __future__ import annotations

import pathlib
import subprocess
import sys

src = pathlib.Path(__file__).with_name("wsl-vllm-serve.sh")
if len(sys.argv) > 1:
    src = pathlib.Path(sys.argv[1])
data = src.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
if not data.startswith(b"#!/"):
    raise SystemExit(f"refusing to install: {src} is not a shell script")
subprocess.run(
    [
        "wsl",
        "-d",
        "Ubuntu",
        "-u",
        "arendeth",
        "--",
        "bash",
        "-c",
        "cat > /home/arendeth/vllm/serve.sh && chmod +x /home/arendeth/vllm/serve.sh",
    ],
    input=data,
    check=True,
)
print("installed LF serve.sh into WSL")
