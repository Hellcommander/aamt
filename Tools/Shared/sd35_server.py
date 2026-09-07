#!/usr/bin/env python3
"""AAMT SD3.5 HTTP API (diffusers + CUDA). Canonical copy: Tools/Shared/sd35_server.py.

Start-StableDiffusionServer.ps1 copies this file to E:\\tools\\sd3.5\\sd3.5\\server.py
before launch. Do not treat the E:\\tools copy as the source of truth.

Compatible with Tools/Shared/sd_http_client.py:
  GET  /ping /health /          -> {status, loaded, loading, generating, threaded, ...}
  GET  /shutdown
  POST /v1/images/generations   (alias: /generate)
       body: prompt, negative_prompt, width, height, steps, guidance_scale, seed
             optional image (b64) + strength  -> img2img
             optional max_sequence_length (T5; default SD_MAX_SEQ_LEN)
       reply: {data: [{b64_json}]}

Uses ThreadingHTTPServer so /ping stays responsive during preload/generate.
CUDA load + generate are serialized with an RLock.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

HOST = "127.0.0.1"
PORT = 1338
MODEL_ID = "stabilityai/stable-diffusion-3.5-medium"
SERVER_VERSION = "aamt-1338.5"

_pipe = None
_pipe_i2i = None
_pipe_error: Optional[str] = None
# Serialize CUDA load/generate. ThreadingHTTPServer keeps /ping alive during that work.
_lock = threading.RLock()
_last_used = time.time()
_httpd: Optional[HTTPServer] = None
_token_ok = False
_token_name: Optional[str] = None
_loading = False
_generating = False

_AUTH_MARKERS = (
    "401",
    "GatedRepo",
    "Unauthorized",
    "Invalid username or password",
    "cannot find the requested files",
)

_GENERATE_PATHS = ("/v1/images/generations", "/generate")


def _env_truthy(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


def _max_seq_len(body: Optional[dict] = None) -> int:
    """T5 prompt length (CLIP stays at 77). Default SD_MAX_SEQ_LEN=256."""
    raw = None
    if body:
        raw = body.get("max_sequence_length") or body.get("max_seq_len")
    if raw in (None, ""):
        raw = os.environ.get("SD_MAX_SEQ_LEN") or "256"
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = 256
    return max(77, min(512, n))


def _idle_sec() -> float:
    try:
        return float(os.environ.get("SD_IDLE_SHUTDOWN_SEC") or "180")
    except ValueError:
        return 180.0


def _shared_dir() -> Path:
    here = Path(__file__).resolve().parent
    if (here / "hf_token_switch.py").is_file():
        return here
    return Path(r"D:\games\Ai assisted toolkit\Tools\Shared")


def _apply_hf_token() -> None:
    """Activate the media (SD3.5) HF token before from_pretrained."""
    global _token_ok, _token_name
    shared = _shared_dir()
    if shared.is_dir() and str(shared) not in sys.path:
        sys.path.insert(0, str(shared))
    try:
        from hf_token_switch import use_media_token

        _token_name = use_media_token(quiet=True)
        _token_ok = True
        print(f"[SD] HF token profile media -> {_token_name}", flush=True)
    except Exception as exc:
        _token_ok = False
        _token_name = None
        print(f"[SD] HF token not applied: {exc}", flush=True)


def _is_auth_error(exc: BaseException) -> bool:
    msg = f"{type(exc).__name__}: {exc}"
    return any(m.lower() in msg.lower() for m in _AUTH_MARKERS)


def load_pipeline():
    global _pipe, _pipe_error, _loading
    with _lock:
        if _pipe is not None:
            return _pipe
        _loading = True
        _apply_hf_token()
        try:
            import torch
            from diffusers import StableDiffusion3Pipeline

            if not torch.cuda.is_available():
                raise RuntimeError("CUDA is not available on this Python")
            skip_t5 = _env_truthy("SD_SKIP_T5", "1")
            t5_ram = _env_truthy("SD_ALLOW_T5_RAM", "0")
            seq_len = _max_seq_len()
            kwargs: dict[str, Any] = {"torch_dtype": torch.float16}
            token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
            if token:
                kwargs["token"] = token
            if skip_t5:
                kwargs["text_encoder_3"] = None
                kwargs["tokenizer_3"] = None
            print(
                f"[SD] loading {MODEL_ID} skip_t5={skip_t5} "
                f"t5_ram={t5_ram} max_seq_len={seq_len} ...",
                flush=True,
            )
            stop_hb = threading.Event()

            def _hb():
                global _last_used
                while not stop_hb.wait(15.0):
                    _last_used = time.time()

            threading.Thread(target=_hb, daemon=True).start()
            try:
                try:
                    pipe = StableDiffusion3Pipeline.from_pretrained(
                        MODEL_ID, local_files_only=True, **kwargs
                    )
                    print("[SD] loaded from local HF cache", flush=True)
                except Exception as local_exc:
                    print(f"[SD] local cache miss ({local_exc}); trying hub...", flush=True)
                    hub_kwargs = dict(kwargs)
                    hub_kwargs.pop("local_files_only", None)
                    pipe = StableDiffusion3Pipeline.from_pretrained(MODEL_ID, **hub_kwargs)
            finally:
                stop_hb.set()
            # T5 + full GPU OOM on 11GB. model_cpu_offload keeps T5 off VRAM and
            # moves modules correctly during encode (manual .to("cpu") on T5 alone
            # breaks encode_prompt: inputs on cuda, weights on cpu).
            if (not skip_t5) and t5_ram and hasattr(pipe, "enable_model_cpu_offload"):
                pipe.enable_model_cpu_offload()
                print("[SD] model_cpu_offload (T5 + longer prompts, 11GB-safe)", flush=True)
            else:
                pipe = pipe.to("cuda")
                print("[SD] full pipeline on CUDA", flush=True)
            if hasattr(pipe, "enable_attention_slicing"):
                pipe.enable_attention_slicing()
            _pipe = pipe
            _pipe_error = None
            print("[SD] pipeline ready", flush=True)
            return _pipe
        except Exception as exc:
            traceback.print_exc()
            # Auth / gated-repo failures must not poison the process: the next
            # request can retry after stored_tokens is readable.
            if _is_auth_error(exc):
                _pipe_error = None
            else:
                _pipe_error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            _loading = False


def load_img2img():
    global _pipe_i2i
    txt = load_pipeline()
    with _lock:
        if _pipe_i2i is not None:
            return _pipe_i2i
        from diffusers import StableDiffusion3Img2ImgPipeline

        _pipe_i2i = StableDiffusion3Img2ImgPipeline(**txt.components)
        # Match txt2img placement when T5 is enabled via cpu offload.
        if (
            _env_truthy("SD_SKIP_T5", "1") is False
            and _env_truthy("SD_ALLOW_T5_RAM", "0")
            and hasattr(_pipe_i2i, "enable_model_cpu_offload")
        ):
            try:
                _pipe_i2i.enable_model_cpu_offload()
            except Exception as exc:
                print(f"[SD] img2img cpu_offload note: {exc}", flush=True)
        print("[SD] img2img pipeline ready", flush=True)
        return _pipe_i2i


def _decode_init_image(body: dict, width: int, height: int):
    raw = body.get("image") or body.get("init_image")
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip()
    if "," in s and s.lower().startswith("data:"):
        s = s.split(",", 1)[1]
    from PIL import Image

    img = Image.open(BytesIO(base64.b64decode(s))).convert("RGB")
    if img.size != (width, height):
        img = img.resize((width, height))
    return img


def generate_png(body: dict) -> bytes:
    global _last_used, _generating
    _last_used = time.time()
    prompt = str(body.get("prompt") or "")
    negative = str(body.get("negative_prompt") or "")
    width = int(body.get("width") or 512)
    height = int(body.get("height") or 512)
    steps = int(body.get("steps") or 24)
    guidance = float(body.get("guidance_scale") or 7.0)
    seed = body.get("seed")
    generator = None
    if seed not in (None, "", -1):
        import torch

        generator = torch.Generator(device="cuda").manual_seed(int(seed))
    init = _decode_init_image(body, width, height)
    seq_len = _max_seq_len(body)
    skip_t5 = _env_truthy("SD_SKIP_T5", "1")
    print(
        f"[SD] generate {width}x{height} steps={steps} seed={seed} "
        f"img2img={'yes' if init is not None else 'no'} "
        f"max_seq_len={seq_len} skip_t5={skip_t5}",
        flush=True,
    )
    call_kw: dict[str, Any] = {
        "prompt": prompt,
        "negative_prompt": negative or None,
        "width": width,
        "height": height,
        "num_inference_steps": steps,
        "guidance_scale": guidance,
        "generator": generator,
    }
    # Only meaningful when T5 is loaded; CLIP encoders stay at 77 regardless.
    if not skip_t5:
        call_kw["max_sequence_length"] = seq_len
    # One CUDA job at a time; other request threads can still serve /ping.
    with _lock:
        _generating = True
        try:
            if init is not None:
                strength = float(body.get("strength") or body.get("image_strength") or 0.7)
                strength = max(0.05, min(1.0, strength))
                i2i = load_img2img()
                image = i2i(image=init, strength=strength, **call_kw).images[0]
            else:
                pipe = load_pipeline()
                image = pipe(**call_kw).images[0]
        finally:
            _generating = False
    buf = BytesIO()
    image.save(buf, format="PNG")
    _last_used = time.time()
    return buf.getvalue()


def _status_payload() -> dict:
    skip_t5 = _env_truthy("SD_SKIP_T5", "1")
    return {
        "status": "ok",
        "model": MODEL_ID,
        "loaded": _pipe is not None,
        "loading": bool(_loading),
        "generating": bool(_generating),
        "threaded": True,
        "version": SERVER_VERSION,
        "skip_t5": skip_t5,
        "t5_ram": _env_truthy("SD_ALLOW_T5_RAM", "0"),
        "max_sequence_length": 77 if skip_t5 else _max_seq_len(),
        "token_ok": _token_ok,
        "token_name": _token_name,
        "img2img": True,
        "generate": list(_GENERATE_PATHS),
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        print(f"[SD] {self.address_string()} {fmt % args}", flush=True)

    def _json(self, code: int, payload: dict) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path in ("/", "/ping", "/health"):
            self._json(200, _status_payload())
            return
        if path == "/v1/models":
            self._json(200, {"data": [{"id": MODEL_ID, "object": "model"}]})
            return
        if path == "/shutdown":
            self._json(200, {"status": "shutting_down"})
            threading.Thread(target=_stop, daemon=True).start()
            return
        self._json(404, {"error": f"unknown GET {path}"})

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        if path not in _GENERATE_PATHS:
            self._json(404, {"error": f"unknown POST {path}; use {_GENERATE_PATHS}"})
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
            png = generate_png(body)
            b64 = base64.b64encode(png).decode("ascii")
            self._json(200, {"data": [{"b64_json": b64, "url": None}]})
        except Exception as exc:
            traceback.print_exc()
            self._json(500, {"error": f"Image generation failed: {exc}"})


def _stop() -> None:
    time.sleep(0.2)
    if _httpd is not None:
        print("[SD] shutdown", flush=True)
        threading.Thread(target=_httpd.shutdown, daemon=True).start()


def _idle_watch() -> None:
    limit = _idle_sec()
    if limit <= 0:
        return
    while True:
        time.sleep(5.0)
        if time.time() - _last_used >= limit:
            print(f"[SD] idle {limit:.0f}s — shutting down", flush=True)
            _stop()
            return


def main() -> int:
    global _httpd, _last_used
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()
    host = "127.0.0.1" if args.host in ("localhost", "127.0.0.1") else args.host
    # Threaded accept so /ping stays responsive while T5 loads or a generate runs.
    # CUDA work remains serialized under _lock.
    class _SdServer(ThreadingHTTPServer):
        daemon_threads = True
        allow_reuse_address = True

    _httpd = _SdServer((host, int(args.port)), Handler)
    _last_used = time.time()
    print(
        f"SD3.5 API Server starting on http://{host}:{args.port} "
        f"({SERVER_VERSION}, threaded)",
        flush=True,
    )
    if _env_truthy("SD_PRELOAD", "1"):
        threading.Thread(target=lambda: load_pipeline(), daemon=True).start()
    threading.Thread(target=_idle_watch, daemon=True).start()
    try:
        _httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
