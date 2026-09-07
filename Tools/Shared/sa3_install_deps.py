# Install stable-audio-3 project deps from pyproject.toml, skipping torch/torchaudio.
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

root = Path(__file__).resolve().parent
data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
deps = data.get("project", {}).get("dependencies", [])
skip = {"torch", "torchaudio"}
pkgs = []
for d in deps:
    name = (
        d.split(";", 1)[0]
        .split("[", 1)[0]
        .split(">", 1)[0]
        .split("<", 1)[0]
        .split("=", 1)[0]
        .split("~", 1)[0]
        .strip()
        .lower()
    )
    if name in skip:
        print(f"skip pinned: {d}")
        continue
    pkgs.append(d)

print(f"Installing {len(pkgs)} deps...")
if pkgs:
    raise SystemExit(subprocess.call([sys.executable, "-m", "pip", "install", *pkgs]))
