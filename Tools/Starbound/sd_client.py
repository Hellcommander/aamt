#!/usr/bin/env python3
"""Minimal SD3.5 HTTP client (img2img via optional reference PNG)."""
from __future__ import annotations

import argparse
import base64
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional


def ping(api: str = "http://127.0.0.1:1338", timeout: float = 8.0) -> bool:
    """True if /ping answers. Longer default — threaded server may be loading T5."""
    try:
        with urllib.request.urlopen(api.rstrip("/") + "/ping", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def status(api: str = "http://127.0.0.1:1338", timeout: float = 8.0) -> Dict[str, Any]:
    try:
        with urllib.request.urlopen(api.rstrip("/") + "/ping", timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as exc:
        return {"status": "down", "error": str(exc)}


def wait_until_up(
    api: str = "http://127.0.0.1:1338",
    *,
    wait_sec: float = 300.0,
    want_loaded: bool = False,
) -> bool:
    """Poll /ping until the server answers (and optionally until the model is loaded)."""
    deadline = time.time() + wait_sec
    while time.time() < deadline:
        st = status(api, timeout=10.0)
        if st.get("status") == "ok":
            if not want_loaded or st.get("loaded"):
                return True
            # Threaded server: loading=true means preload in progress — keep waiting.
        time.sleep(2.0)
    return False


def _clean_b64(raw: str) -> bytes:
    s = str(raw).strip()
    if "," in s and s.lower().startswith("data:"):
        s = s.split(",", 1)[1]
    s = "".join(s.split())
    return base64.b64decode(s)


def generate(
    prompt: str,
    output: Path,
    *,
    api: str = "http://127.0.0.1:1338",
    negative: str = "",
    width: int = 512,
    height: int = 512,
    steps: int = 24,
    guidance: float = 7.0,
    seed: int = 0,
    reference: Optional[Path] = None,
    strength: float = 0.65,
    timeout: float = 3600.0,
    max_sequence_length: Optional[int] = None,
) -> Path:
    body: Dict[str, Any] = {
        "prompt": prompt,
        "negative_prompt": negative,
        "width": width,
        "height": height,
        "size": f"{width}x{height}",
        "steps": steps,
        "guidance_scale": guidance,
        "n": 1,
    }
    if seed:
        body["seed"] = seed
    if max_sequence_length:
        body["max_sequence_length"] = int(max_sequence_length)
    if reference and reference.exists():
        body["image"] = base64.b64encode(reference.read_bytes()).decode("ascii")
        body["strength"] = strength
    url = api.rstrip("/") + "/v1/images/generations"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    images = list(payload.get("images") or [])
    for item in payload.get("data") or []:
        if isinstance(item, dict) and item.get("b64_json"):
            images.append(item["b64_json"])
    if not images:
        raise RuntimeError(f"No image in SD response keys: {list(payload.keys())}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(_clean_b64(images[0]))
    return output


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default="")
    ap.add_argument("--output", default="")
    ap.add_argument("--negative", default="")
    ap.add_argument("--width", type=int, default=512)
    ap.add_argument("--height", type=int, default=512)
    ap.add_argument("--steps", type=int, default=24)
    ap.add_argument("--reference", default="")
    ap.add_argument("--strength", type=float, default=0.65)
    ap.add_argument("--detect-only", action="store_true")
    args = ap.parse_args()
    if args.detect_only:
        up = ping()
        print("up" if up else "down")
        return 0 if up else 1
    if not args.prompt or not args.output:
        raise SystemExit("--prompt and --output are required unless --detect-only")
    generate(
        args.prompt,
        Path(args.output),
        negative=args.negative,
        width=args.width,
        height=args.height,
        steps=args.steps,
        reference=Path(args.reference) if args.reference else None,
        strength=args.strength,
    )
    print(f"[OK] {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
