#!/usr/bin/env python3
"""
Ask Ollama for a mesh+skin design JSON, then run Shared mesh/PBR export.

Prefer small models when SD is also loaded (e.g. qwen2.5-coder:7b).

Example:
  python ollama_mesh_spec.py --theme "obsidian plate pauldron" --out-dir %TEMP%\\mesh --name pauldron --fbx %TEMP%\\mesh\\pauldron.fbx
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from mesh_skin_export import SHAPE_CHOICES, export_mesh_from_spec  # noqa: E402

# Cross-process GPU turn-taking (shared with SD): see Tools\Common\gpu_hub.py.
try:
    from gpu_hub import acquire_gpu
except Exception:  # hub is optional — never block generation on its absence
    import contextlib

    def acquire_gpu(label, timeout=None, poll=2.0, enabled=True):  # type: ignore
        return contextlib.nullcontext()

DEFAULT_MODEL = "qwen2.5-coder:7b"
FALLBACK_MODELS = ("qwen2.5-coder:7b", "codellama:7b-instruct", "llama3.1:8b")


def ollama_memory_options() -> Dict[str, Any]:
    """
    Per-request Ollama options so short prompt-gen calls survive VRAM pressure.

    The local SD3.5 server occupies most of the 2080 Ti's 11 GB, so Ollama
    falls back to CPU and must fit weights + KV cache in free system RAM.
    Default full-context estimates blew past free RAM ("model requires more
    system memory"); a small num_ctx + CPU inference keeps it under ~7 GiB.
    Override via AAMT_OLLAMA_NUM_GPU / AAMT_OLLAMA_NUM_CTX.
    """
    try:
        num_gpu = int(os.environ.get("AAMT_OLLAMA_NUM_GPU", "0"))
    except ValueError:
        num_gpu = 0
    try:
        num_ctx = int(os.environ.get("AAMT_OLLAMA_NUM_CTX", "4096"))
    except ValueError:
        num_ctx = 4096
    return {"num_gpu": num_gpu, "num_ctx": num_ctx}


def _ollama_generate(prompt: str, *, model: str, url: str, timeout: float = 180.0) -> str:
    options = ollama_memory_options()
    body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url.rstrip("/") + "/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    # CPU-only calls (num_gpu=0) skip the GPU lock and run alongside SD.
    with acquire_gpu(f"Ollama mesh-spec {model}", enabled=options.get("num_gpu") != 0):
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    return str(data.get("response") or "")


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in Ollama response")
    raw = text[start : end + 1]
    # Tolerate lightly unquoted keys
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        fixed = re.sub(r"(\w+)\s*:", r'"\1":', raw)
        fixed = re.sub(r",\s*}", "}", fixed)
        return json.loads(fixed)


def request_mesh_spec(
    theme: str,
    *,
    model: str = DEFAULT_MODEL,
    ollama_url: str = "http://127.0.0.1:11434",
) -> Dict[str, Any]:
    shapes = ", ".join(SHAPE_CHOICES)
    prompt = f"""Design a Unity-ready fantasy game mesh + PBR material for: {theme}
Return ONLY valid JSON (no markdown) with this schema:
{{
  "theme": "short material theme",
  "shape": one of [{shapes}],
  "pattern": "organic|plates|scales|crystal",
  "style": "stylized",
  "colors": ["#rrggbb", "#rrggbb"],
  "glow": false,
  "subdivisions": 3,
  "displaceStrength": 0.35,
  "solidifyThickness": 0.12,
  "bevelAmount": 0.02,
  "description": "one sentence"
}}
Prefer shape "armor_panel" for armor pieces, "organic" for creatures, "silhouette" for icon-like cutouts, "displaced" for general materials.
"""
    errors = []
    for candidate in (model, *FALLBACK_MODELS):
        try:
            text = _ollama_generate(prompt, model=candidate, url=ollama_url)
            spec = _extract_json(text)
            spec.setdefault("theme", theme)
            print(f"[OK] Ollama mesh spec via {candidate}")
            return spec
        except Exception as exc:
            errors.append(f"{candidate}: {exc}")
            continue
    raise RuntimeError("Ollama mesh spec failed: " + " | ".join(errors))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--theme", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out-dir", required=True, help="Skin/output directory")
    ap.add_argument("--fbx", required=True)
    ap.add_argument("--obj", default=None)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    ap.add_argument("--quality", default="draft")
    ap.add_argument("--no-sd", action="store_true")
    ap.add_argument("--shape", default=None, help="Override Ollama shape")
    ap.add_argument("--spec-out", default=None, help="Write resolved JSON here")
    ap.add_argument("--blender", default=None)
    args = ap.parse_args()

    try:
        spec = request_mesh_spec(args.theme, model=args.model, ollama_url=args.ollama_url)
    except Exception as exc:
        print(f"[WARN] {exc}; using fallback spec", file=sys.stderr)
        spec = {
            "theme": args.theme,
            "shape": "armor_panel",
            "pattern": "plates",
            "style": "stylized",
            "colors": ["#2a2a32", "#8a9098"],
            "glow": False,
            "subdivisions": 3,
            "displaceStrength": 0.3,
            "solidifyThickness": 0.12,
        }

    if args.shape:
        spec["shape"] = args.shape

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.spec_out:
        Path(args.spec_out).write_text(json.dumps(spec, indent=2), encoding="utf-8")
    else:
        (out_dir / f"{args.name}_mesh_spec.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")

    print("[SPEC]", json.dumps(spec, indent=2))
    code = export_mesh_from_spec(
        skin_dir=out_dir,
        name=args.name,
        fbx=args.fbx,
        spec=spec,
        shape=str(spec.get("shape") or "displaced"),
        quality=args.quality,
        use_sd=not args.no_sd,
        blender=args.blender,
        obj=args.obj,
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
