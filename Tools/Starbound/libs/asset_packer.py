#!/usr/bin/env python3
"""Offline ports of Magi-Tech Lua scripts/tools (assetPacker, generateManifest, jsonToBinary, chunkJson).

Canonical location: Transcendence/Tools/Starbound/libs
The mod keeps Lua copies that run inside Starbound (sb.* APIs).
"""
from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Union

SKIP_DIR_NAMES = {".git", "cpp_backend", "vendor", "images", "node_modules", "__pycache__"}


def find_files(root: Path, skip_dirs: Optional[Iterable[str]] = None) -> List[Path]:
    skip = set(skip_dirs or SKIP_DIR_NAMES)
    out: List[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in skip for part in p.parts):
            continue
        out.append(p)
    return out


def pack_directory(input_dir: Union[str, Path], output_file: Union[str, Path]) -> Dict:
    """Pack files into index-prefixed blob (Lua assetPacker.lua format)."""
    root = Path(input_dir)
    dest = Path(output_file)
    files = find_files(root)
    index: Dict[str, Dict[str, int]] = {}
    blobs: List[bytes] = []
    offset = 0
    for path in files:
        rel = path.relative_to(root).as_posix()
        data = path.read_bytes()
        index[rel] = {"offset": offset, "size": len(data)}
        blobs.append(data)
        offset += len(data)
    index_json = json.dumps(index, separators=(",", ":")).encode("utf-8")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(struct.pack(">I", len(index_json)) + index_json + b"".join(blobs))
    return {"files": len(files), "output": str(dest), "bytes": dest.stat().st_size}


def generate_mod_manifest(mod_root: Union[str, Path], output: Optional[Union[str, Path]] = None) -> Dict:
    root = Path(mod_root)
    configs = [
        ("lua_script", "scripts", ".lua"),
        ("config", ".", ".config"),
        ("json_config", ".", ".json"),
        ("patch", ".", ".patch"),
        ("image", "interface", ".png"),
        ("gui", "interface", ".gui"),
        ("frames", ".", ".frames"),
        ("animation", ".", ".animation"),
        ("item", "items", ".item"),
        ("activeitem", "items", ".activeitem"),
        ("object", "objects", ".object"),
    ]
    manifest = {"version": "1.0", "files": []}
    seen = set()
    for ftype, rel, ext in configs:
        base = (root / rel).resolve() if rel != "." else root.resolve()
        if not base.exists():
            continue
        for path in base.rglob(f"*{ext}"):
            if not path.is_file():
                continue
            if any(part in SKIP_DIR_NAMES for part in path.relative_to(root).parts):
                continue
            rel_path = path.relative_to(root).as_posix()
            if rel_path in seen:
                continue
            seen.add(rel_path)
            manifest["files"].append({
                "path": rel_path,
                "type": ftype,
                "size": path.stat().st_size,
            })
    dest = Path(output) if output else root / "modManifest.json"
    dest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    manifest["output"] = str(dest)
    return manifest


def _serialize(value) -> str:
    t = type(value)
    if isinstance(value, dict):
        parts = ["T"]
        for k, v in value.items():
            parts.append(_serialize(k))
            parts.append(_serialize(v))
        parts.append("E")
        return "".join(parts)
    if isinstance(value, list):
        parts = ["A"]
        for item in value:
            parts.append(_serialize(item))
        parts.append("E")
        return "".join(parts)
    if isinstance(value, str):
        return f"S{len(value)}:{value}"
    if isinstance(value, bool):
        return "B1" if value else "B0"
    if isinstance(value, (int, float)):
        return f"N{value}\0"
    if value is None:
        return "L"
    return "L"


def json_to_binary(input_json: Union[str, Path], output_bin: Union[str, Path]) -> Path:
    data = json.loads(Path(input_json).read_text(encoding="utf-8"))
    dest = Path(output_bin)
    dest.write_bytes(_serialize(data).encode("utf-8"))
    return dest


def chunk_json_array(input_json: Union[str, Path], output_dir: Union[str, Path], num_chunks: int) -> List[Path]:
    data = json.loads(Path(input_json).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("input must be a JSON array")
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    n = max(1, int(num_chunks))
    total = len(data)
    per = max(1, (total + n - 1) // n)
    base = Path(input_json).stem
    written = []
    for i in range(n):
        start = i * per
        if start >= total:
            break
        chunk = data[start:start + per]
        dest = out_dir / f"{base}.part_{i + 1}.json"
        dest.write_text(json.dumps(chunk, indent=2) + "\n", encoding="utf-8")
        written.append(dest)
    return written


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Magi-Tech asset packer / manifest tools")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pack")
    p.add_argument("input_dir")
    p.add_argument("output_file")
    m = sub.add_parser("manifest")
    m.add_argument("mod_root")
    m.add_argument("--output")
    j = sub.add_parser("json-bin")
    j.add_argument("input_json")
    j.add_argument("output_bin")
    c = sub.add_parser("chunk")
    c.add_argument("input_json")
    c.add_argument("output_dir")
    c.add_argument("--chunks", type=int, default=5)
    args = ap.parse_args()
    if args.cmd == "pack":
        print(json.dumps(pack_directory(args.input_dir, args.output_file), indent=2))
    elif args.cmd == "manifest":
        print(json.dumps(generate_mod_manifest(args.mod_root, args.output), indent=2)[:500], "...")
    elif args.cmd == "json-bin":
        print(json_to_binary(args.input_json, args.output_bin))
    else:
        print([str(p) for p in chunk_json_array(args.input_json, args.output_dir, args.chunks)])
