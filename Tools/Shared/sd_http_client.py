#!/usr/bin/env python3
"""HTTP client for the local SD3.5 Diffusers API (HTTP/1.1, :1338).

This is the image stage of the shared AAMT pipeline (see AI_ASSET_RESOURCES.md).
Game tools and agents must call this (or ai_resources.make_image / ensure("image"))
instead of Cursor's image generator. SD3.5 Medium owns pixel production.

  python sd_http_client.py --detect-only
  python ai_resources.py --ensure image

POST path is /v1/images/generations (alias /generate). Do not POST / on :1338.
Weights are gated: the server applies hf_token_switch profile "media"
(display name "SD3.5 Token"). plan_sd_size(..., kind="icon") for tiles.

Every generation takes the shared GPU lock (gpu_hub.py).
"""

from __future__ import annotations

import argparse
import base64
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

def _known_ports() -> list[int]:
    ports: list[int] = []
    try:
        from tool_paths import sd_port

        ports.append(int(sd_port()))
    except Exception:
        ports.append(1338)
    for p in (1338, 1337, 7860, 8188, 8000, 9090):
        if p not in ports:
            ports.append(p)
    return ports


KNOWN_PORTS = _known_ports()
HEALTH_PATHS = ("/ping", "/health", "/")

# Cross-process GPU turn-taking: SD + Ollama together exhaust the 11 GB card,
# so each generation request takes the shared GPU lock (see Common\gpu_hub.py).
try:
    from gpu_hub import acquire_gpu
except Exception:  # hub is optional — never block generation on its absence
    import contextlib

    def acquire_gpu(label, timeout=None, poll=2.0, enabled=True):  # type: ignore
        return contextlib.nullcontext()

# ---------------------------------------------------------------------------
# Right-sized generation planning
#
# SD3.5 on this box takes ~330-490s per large image, so every call site should
# request the smallest SD-friendly size for its delivery target instead of a
# huge default. Sizes must be multiples of 64; SD3.5 Medium degrades below
# ~512px on the short side, so we clamp there and never supersample more than
# the per-kind factor over the delivery size.
# ---------------------------------------------------------------------------
SD_SIZE_STEP = 64
SD_MIN_SIDE = 512   # SD3.5 Medium quality floor (short side)
SD_MAX_SIDE = 1536

SD_KIND_PROFILES: Dict[str, Dict[str, float]] = {
    # supersample: MAX upscale over delivery size (headroom for Lanczos
    # downscale) — small targets are clamped up to SD_MIN_SIDE regardless,
    # so only targets near/above 512 actually supersample.
    # steps: default step count for the asset class.
    "banner":  {"supersample": 1.5,  "steps": 40},  # flagship art keeps high steps
    "icon":    {"supersample": 1.5,  "steps": 24},
    "hud":     {"supersample": 1.25, "steps": 18},
    "texture": {"supersample": 1.0,  "steps": 24},  # material maps: gen at delivery size
    "sprite":  {"supersample": 1.25, "steps": 20},
    "default": {"supersample": 1.25, "steps": 28},
}


def plan_sd_size(
    delivery_w: int,
    delivery_h: int,
    kind: str = "default",
    *,
    min_side: int = SD_MIN_SIDE,
    max_side: int = SD_MAX_SIDE,
    native: bool = False,
) -> Tuple[int, int, int]:
    """
    Right-size an SD3.5 request for a delivery target.

    Returns (gen_width, gen_height, steps). Dimensions are multiples of 64,
    the short side is clamped up to `min_side` (SD3.5 quality floor), the size
    is otherwise at most `supersample`x the delivery size, and the long side
    is capped at `max_side`. Example: a 512x439 banner plans as 768x640
    instead of a wasteful 1344x1152.

    When native=True (or SD_NATIVE_RESOLUTION=1), generate at the delivery size
    snapped to SD_SIZE_STEP with no supersample / quality-floor upscale. Use
    this for game spritesheets that must match final pixel dimensions.
    """
    if native or (os.environ.get("SD_NATIVE_RESOLUTION", "").strip().lower() in ("1", "true", "yes", "on")):
        return plan_native_size(delivery_w, delivery_h, kind=kind)

    prof = SD_KIND_PROFILES.get(kind) or SD_KIND_PROFILES["default"]
    ss = float(prof["supersample"])
    w = max(1, int(delivery_w)) * ss
    h = max(1, int(delivery_h)) * ss
    short = min(w, h)
    if short < min_side:
        factor = min_side / short
        w *= factor
        h *= factor
    # Extreme aspect ratios (e.g. 360x80 HUD strips) would explode the long
    # side when the short side gets clamped to 512. SD3.5 also degrades past
    # ~2:1, so cap the aspect; callers cover-crop/downscale to delivery anyway.
    short, longest = min(w, h), max(w, h)
    if longest > short * 2.0:
        if w >= h:
            w = short * 2.0
        else:
            h = short * 2.0
    longest = max(w, h)
    if longest > max_side:
        factor = max_side / longest
        w *= factor
        h *= factor

    def _snap(v: float) -> int:
        return max(min_side, int(round(v / SD_SIZE_STEP)) * SD_SIZE_STEP)

    return _snap(w), _snap(h), int(prof["steps"])


def plan_native_size(
    delivery_w: int,
    delivery_h: int,
    kind: str = "default",
    *,
    step: int = 16,
    min_side: int = 32,
    max_side: int = SD_MAX_SIDE,
) -> Tuple[int, int, int]:
    """
    Plan generation at the final asset resolution (no crush-down later).

    Snaps to `step` (default 16, matching the SD server VAE grid) and clamps to
    [min_side, max_side]. Steps come from the kind profile.
    """
    prof = SD_KIND_PROFILES.get(kind) or SD_KIND_PROFILES["default"]
    step = max(8, int(os.environ.get("SD_DIM_STEP", step) or step))
    min_side = max(step, int(os.environ.get("SD_MIN_DIM", min_side) or min_side))
    max_side = max(min_side, int(os.environ.get("SD_MAX_DIM", max_side) or max_side))

    def _snap(v: int) -> int:
        v = max(1, int(v))
        v = int(round(v / float(step))) * step
        return max(min_side, min(max_side, v))

    return _snap(delivery_w), _snap(delivery_h), int(prof["steps"])
def _default_sd_outputs() -> Path:
    try:
        from tool_paths import sd_outputs_dir

        return sd_outputs_dir()
    except Exception:
        return Path(r"E:\tools\sd3.5\sd3.5\outputs")


_DEFAULT_SD_OUTPUTS = _default_sd_outputs()
SD_OUTPUTS_DIR = Path(os.environ.get("AAMT_SD_OUTPUTS_DIR") or _DEFAULT_SD_OUTPUTS)
DEFAULT_CONNECT_TIMEOUT = 30.0
DEFAULT_READ_TIMEOUT = 9000.0  # 2.5h — SD3.5 Medium + CPU offload can exceed 1h


def http_get(url: str, timeout: float = 3.0) -> tuple[int, str, dict[str, str]]:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        headers = {k.lower(): v for k, v in resp.headers.items()}
        return resp.status, body, headers


def looks_like_sd_health(body: str) -> bool:
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return False
    if isinstance(data, dict):
        if data.get("status") == "ok":
            return True
        if "stable-diffusion" in json.dumps(data).lower():
            return True
        if isinstance(data.get("data"), list) and data["data"]:
            return True
    return False


def looks_like_aamt_sd(body: str) -> bool:
    """True only for Tools/Shared/sd35_server.py (version aamt-1338*)."""
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return False
    return isinstance(data, dict) and str(data.get("version") or "").startswith("aamt-1338")


def detect_server(verbose: bool = False) -> Optional[str]:
    """Return the AAMT generate URL, or None.

    A foreign SD process on :1338 (Starfield SFMAG) is not treated as ready.
    """
    for port in KNOWN_PORTS:
        foreign_on_port = False
        for host in ("127.0.0.1",):
            for path in HEALTH_PATHS:
                url = f"http://{host}:{port}{path}"
                try:
                    status, body, headers = http_get(url, timeout=0.6)
                    server = headers.get("server", "")
                    if status == 426 or "websocket" in server.lower():
                        if verbose:
                            print(f"[SKIP] {url} requires HTTP/2 or is WebSocket++ ({server})", file=sys.stderr)
                        foreign_on_port = True
                        break
                    if status == 200 and looks_like_aamt_sd(body):
                        api = f"http://{host}:{port}/v1/images/generations"
                        if verbose:
                            print(f"[OK] Detected AAMT SD server at {api}", file=sys.stderr)
                        return api
                    if status == 200 and looks_like_sd_health(body):
                        if verbose:
                            print(
                                f"[SKIP] {url} is a foreign SD process (not aamt-1338). "
                                "AAMT will replace it on ensure/start.",
                                file=sys.stderr,
                            )
                        foreign_on_port = True
                        break
                except Exception as exc:
                    if verbose:
                        print(f"[SKIP] {url}: {exc}", file=sys.stderr)
                    continue
        if foreign_on_port:
            return None
    return None


def extract_images(response: Dict[str, Any]) -> List[str]:
    images: List[str] = []
    if response.get("images"):
        images.extend(response["images"])
    for item in response.get("data") or []:
        if item.get("b64_json"):
            images.append(item["b64_json"])
    if not images:
        raise RuntimeError(f"No image data in SD response keys: {list(response.keys())}")
    cleaned = []
    for raw in images:
        s = str(raw).strip()
        if "," in s and s.lower().startswith("data:"):
            s = s.split(",", 1)[1]
        cleaned.append("".join(s.split()))
    return cleaned


def build_request_body(
    prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    steps: int,
    guidance_scale: float,
    seed: int,
    reference_image: Optional[str] = None,
    image_strength: float = 0.65,
) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "size": f"{width}x{height}",
        "steps": steps,
        "guidance_scale": guidance_scale,
        "n": 1,
    }
    if negative_prompt:
        body["negative_prompt"] = negative_prompt
    if seed:
        body["seed"] = seed
    if reference_image:
        ref = Path(reference_image)
        if not ref.exists():
            raise RuntimeError(f"Reference image missing: {ref}")
        b64 = base64.b64encode(ref.read_bytes()).decode("ascii")
        body["image"] = b64
        body["strength"] = image_strength
    return body


def _parse_api_url(api_url: str) -> Tuple[str, int, str]:
    from urllib.parse import urlparse

    parsed = urlparse(api_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 1338
    path = parsed.path or ""
    if path in ("", "/"):
        path = "/v1/images/generations"
    return host, port, path


def salvage_server_output(
    output_path: Path,
    *,
    started_at: float,
    width: Optional[int] = None,
    height: Optional[int] = None,
    max_age_sec: float = 14400.0,
) -> Optional[Path]:
    """
    Recover a finished SD image from the server's on-disk cache when the HTTP
    client timed out but generation completed server-side.
    """
    candidates: List[Path] = []
    latest = SD_OUTPUTS_DIR / "latest.png"
    if latest.exists():
        candidates.append(latest)
    if SD_OUTPUTS_DIR.is_dir():
        candidates.extend(sorted(SD_OUTPUTS_DIR.glob("gen_*.png"), key=lambda p: p.stat().st_mtime, reverse=True))

    seen: set[str] = set()
    for src in candidates:
        key = str(src.resolve())
        if key in seen:
            continue
        seen.add(key)
        try:
            age = time.time() - src.stat().st_mtime
            if age > max_age_sec:
                continue
            if src.stat().st_mtime < started_at - 5.0:
                continue
            from PIL import Image

            with Image.open(src) as img:
                if width and height and img.size != (width, height):
                    continue
            output_path.parent.mkdir(parents=True, exist_ok=True)
            import shutil

            shutil.copy2(src, output_path)
            print(f"[OK] Salvaged SD output from server cache: {src} -> {output_path}", file=sys.stderr)
            return output_path
        except Exception as exc:
            print(f"[WARN] Salvage candidate {src} unusable: {exc}", file=sys.stderr)
    return None


def _post_json_long_read(
    api_url: str,
    body: Dict[str, Any],
    *,
    connect_timeout: float,
    read_timeout: float,
) -> str:
    host, port, path = _parse_api_url(api_url)
    payload = json.dumps(body).encode("utf-8")
    conn = http.client.HTTPConnection(host, port, timeout=read_timeout)
    try:
        conn.request(
            "POST",
            path,
            body=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        resp = conn.getresponse()
        # Read the FULL body. The timeout is enforced by the socket (set on the
        # HTTPConnection above); HTTPResponse.read(amt) treats its arg as a byte
        # count, so passing a timeout here truncated the image / raised TypeError
        # and forced every call onto the on-disk salvage path (which breaks
        # parallel facing/animation batches that share latest.png).
        raw = resp.read()
        if resp.status >= 400:
            detail = raw.decode("utf-8", errors="replace")[:500]
            if resp.status == 426:
                raise RuntimeError(
                    f"SD API at {api_url} returned HTTP 426 (not the SD3.5 Diffusers server). "
                    "Use Start-StableDiffusionServer.ps1 and ensure port 1338 is free."
                )
            raise RuntimeError(f"SD API HTTP {resp.status}: {detail}")
        return raw.decode("utf-8")
    finally:
        conn.close()


def generate_image(
    prompt: str,
    output_path: Path,
    api_url: Optional[str] = None,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    steps: int = 28,
    guidance_scale: float = 7.0,
    seed: int = 0,
    timeout: float = DEFAULT_READ_TIMEOUT,
    connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
    reference_image: Optional[str] = None,
    image_strength: float = 0.65,
) -> Path:
    api_url = api_url or detect_server(verbose=True)
    if not api_url:
        raise RuntimeError(
            "No Stable Diffusion server detected. Start SD3.5 with "
            "Tools\\Start-StableDiffusionServer.ps1 (default port 1338). "
            "Port 1337 may be occupied by another service (WebSocket++)."
        )

    body = build_request_body(
        prompt, negative_prompt, width, height, steps, guidance_scale, seed,
        reference_image=reference_image, image_strength=image_strength,
    )
    started = time.monotonic()
    started_wall = time.time()
    print(
        f"[SD] POST {width}x{height} @ {steps} steps (connect={int(connect_timeout)}s "
        f"read={int(timeout)}s)...",
        file=sys.stderr,
    )
    # Hold the shared GPU lock only for the generation request itself (server
    # startup/detection above must not hold it).
    with acquire_gpu(f"SD {width}x{height} {output_path.name}"):
        # Re-stamp after any lock wait so salvage never grabs an image another
        # process finished while we were queued.
        started_wall = time.time()
        try:
            raw = _post_json_long_read(
                api_url, body, connect_timeout=connect_timeout, read_timeout=timeout,
            )
        except (TimeoutError, urllib.error.URLError, http.client.HTTPException, OSError) as exc:
            # Server may finish AFTER client timeout — salvage any recent on-disk output.
            salvaged = salvage_server_output(
                output_path, started_at=started_wall - 300.0, width=width, height=height,
            )
            if salvaged:
                print(f"[OK] Salvaged after client timeout ({time.monotonic() - started:.1f}s)", file=sys.stderr)
                return salvaged
            elapsed = time.monotonic() - started
            raise RuntimeError(f"timed out after {elapsed:.1f}s: {exc}") from exc
        except Exception as exc:
            salvaged = salvage_server_output(
                output_path, started_at=started_wall, width=width, height=height,
            )
            if salvaged:
                return salvaged
            raise

    response = json.loads(raw)
    b64 = extract_images(response)[0]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(base64.b64decode(b64))
    elapsed = time.monotonic() - started
    seeds = response.get("seeds")
    seed_note = f" seed={seeds[0]}" if isinstance(seeds, list) and seeds else ""
    print(f"[OK] SD image saved ({elapsed:.1f}s){seed_note}: {output_path}", file=sys.stderr)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate image via local SD3.5 HTTP API")
    parser.add_argument("--prompt", default="")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--api-url", default=None)
    parser.add_argument("--negative-prompt", default="")
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--steps", type=int, default=28)
    parser.add_argument("--guidance-scale", type=float, default=7.0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--timeout", type=float, default=DEFAULT_READ_TIMEOUT)
    parser.add_argument("--detect-only", action="store_true")
    parser.add_argument("--reference-image", default="")
    parser.add_argument("--image-strength", type=float, default=0.65)
    args = parser.parse_args()

    try:
        if args.detect_only:
            url = detect_server(verbose=True)
            if url:
                print(url)
                return 0
            return 1
        out = generate_image(
            prompt=args.prompt,
            output_path=args.output,
            api_url=args.api_url,
            negative_prompt=args.negative_prompt,
            width=args.width,
            height=args.height,
            steps=args.steps,
            guidance_scale=args.guidance_scale,
            seed=args.seed,
            timeout=args.timeout,
            reference_image=(args.reference_image or None),
            image_strength=args.image_strength,
        )
        print(f"[OK] {out}")
        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
