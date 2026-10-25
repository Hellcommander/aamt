#!/usr/bin/env python3
"""Package AAMT Sprite Forge as a Pixelorama extension (.zip of text GDScript/.tscn).

No Godot editor export step: Pixelorama loads extensions with
ProjectSettings.load_resource_pack(), which accepts .zip packs, and the
runtime compiles text .gd / loads text .tscn from them.

  python build.py                 # -> dist/AAMTSpriteForge.zip
  python build.py --install       # + copy to %APPDATA%/pixelorama/extensions
  python build.py --install --enable   # + set [extensions] AAMTSpriteForge=true

Pixelorama only instantiates an installed extension when config.ini has
[extensions] <name>=true (what Preferences > Extensions > Enable writes).
--enable makes that edit (one-time backup: config.ini.pre_spriteforge.bak).
Do not run --enable while the Pixelorama GUI is open: it rewrites config.ini
from memory on exit.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "extension"
NAME = "AAMTSpriteForge"
PACK_ROOT = f"src/Extensions/{NAME}"
USER_DIR = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / "pixelorama"
INCLUDE = {".gd", ".tscn", ".json", ".tres", ".png", ".gdshader", ".txt"}


def build(out: Path) -> dict:
    files = sorted(p for p in SRC.rglob("*") if p.is_file() and p.suffix.lower() in INCLUDE)
    meta = json.loads((SRC / "extension.json").read_text(encoding="utf-8"))
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".zip.tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            zf.write(p, f"{PACK_ROOT}/{p.relative_to(SRC).as_posix()}")
    os.replace(tmp, out)
    return {"zip": str(out), "files": [p.relative_to(SRC).as_posix() for p in files],
            "version": meta.get("version"), "api": meta.get("supported_api_versions")}


def install(zip_path: Path) -> str:
    dest_dir = USER_DIR / "extensions"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{NAME}.zip"
    shutil.copy2(zip_path, dest)
    return str(dest)


def enable() -> dict:
    cfg = USER_DIR / "config.ini"
    text = cfg.read_text(encoding="utf-8") if cfg.is_file() else ""
    backup = USER_DIR / "config.ini.pre_spriteforge.bak"
    if cfg.is_file() and not backup.exists():
        shutil.copy2(cfg, backup)
    line = f"{NAME}=true"
    m = re.search(r"(?m)^\[extensions\]\s*$", text)
    if m:
        start = m.end()
        nxt = re.search(r"(?m)^\[", text[start:])
        end = start + nxt.start() if nxt else len(text)
        body = text[start:end]
        if re.search(rf"(?m)^{NAME}=", body):
            body = re.sub(rf"(?m)^{NAME}=.*$", line, body)
        else:
            body = "\n" + line + body
        text = text[:start] + body + text[end:]
    else:
        text = text.rstrip("\n") + f"\n\n[extensions]\n\n{line}\n"
    cfg.write_text(text, encoding="utf-8")
    return {"config": str(cfg), "backup": str(backup)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build/install AAMT Sprite Forge")
    ap.add_argument("--out", type=Path, default=HERE / "dist" / f"{NAME}.zip")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--enable", action="store_true")
    args = ap.parse_args()
    info = build(args.out)
    if args.install:
        info["installed"] = install(args.out)
    if args.enable:
        info["enabled"] = enable()
    print(json.dumps({"ok": True, **info}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
