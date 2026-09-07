#!/usr/bin/env python3
"""HTTP client for the local TRELLIS.2 image-to-3D server.

Companion to sd_http_client.py: SD makes the reference image, this turns it
into a textured mesh. Any AAMT game toolset can call generate_mesh() to get a
GLB with real UVs, then bake/retarget it for its own engine.

Server is the IgorAherne StableProjectorz fork of microsoft/TRELLIS.2 (the
upstream repo is Linux-only and wants 24 GB; the fork runs the same 4B weights
on this 11 GB 2080 Ti). Start it with start_server() or its own .bat.

  python trellis_http_client.py --detect-only
  python trellis_http_client.py --image ref.png --output mesh.glb
  python trellis_http_client.py --start

Every generation takes the shared GPU lock (Common\\gpu_hub.py) because SD3.5,
Ollama and TRELLIS together will exhaust VRAM.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

try:
    from gpu_hub import acquire_gpu
except Exception:  # hub is optional — never block generation on its absence
    import contextlib

    def acquire_gpu(label, timeout=None, poll=2.0, enabled=True):  # type: ignore
        return contextlib.nullcontext()


def _port() -> int:
    try:
        from tool_paths import trellis_port

        return int(trellis_port())
    except Exception:
        return 7960


def _root() -> Path:
    try:
        from tool_paths import trellis_root

        return trellis_root()
    except Exception:
        return Path(r"D:\trellis2")


def _launcher() -> Optional[Path]:
    try:
        from tool_paths import trellis_launcher

        return trellis_launcher()
    except Exception:
        bat = _root() / "run-stableprojectorz" / "run-stableprojectorz.bat"
        return bat if bat.is_file() else None


DEFAULT_HOST = "127.0.0.1"
DEFAULT_READ_TIMEOUT = 3600.0  # 1536^3 on an 11 GB card is slow
STARTUP_TIMEOUT = 2400.0  # first run installs a venv + downloads weights

# Resolution -> pipeline tier. 512 is the safe default on 11 GB.
SAFE_RESOLUTION = 512


def _env_truthy(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def keep_server() -> bool:
    """Batch jobs set AAMT_TRELLIS_KEEP_SERVER=1 so remesh loops skip restart."""
    return _env_truthy("AAMT_TRELLIS_KEEP_SERVER", False)


def _port_open(host: str, port: int, timeout: float = 0.4) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def detect_server(verbose: bool = False) -> Optional[str]:
    """Return the base URL of a live TRELLIS server, or None."""
    port = _port()
    for host in (DEFAULT_HOST, "localhost"):
        if not _port_open(host, port):
            continue
        url = f"http://{host}:{port}"
        try:
            with urllib.request.urlopen(f"{url}/ping", timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") == "running":
                if verbose:
                    print(f"[OK] TRELLIS server at {url}", file=sys.stderr)
                return url
        except Exception as exc:
            if verbose:
                print(f"[SKIP] {url}: {exc}", file=sys.stderr)
    return None


def server_busy() -> bool:
    url = detect_server()
    if not url:
        return False
    try:
        with urllib.request.urlopen(f"{url}/status", timeout=5) as resp:
            return bool(json.loads(resp.read().decode("utf-8")).get("busy"))
    except Exception:
        return False


def start_server(wait_seconds: float = STARTUP_TIMEOUT, log_path: Optional[Path] = None) -> Optional[str]:
    """Launch the TRELLIS API server and wait for it to answer /ping."""
    existing = detect_server()
    if existing:
        return existing

    bat = _launcher()
    if not bat:
        raise RuntimeError(f"TRELLIS launcher not found under {_root()}")

    log_path = log_path or (_root() / "server.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    try:
        from tool_paths import hf_home

        env["HF_HOME"] = str(hf_home())
    except Exception:
        pass

    print(f"[TRELLIS] starting server (log: {log_path})...", file=sys.stderr)
    with open(log_path, "w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            ["cmd", "/c", str(bat)],
            cwd=str(bat.parent),
            stdout=log,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            env=env,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )

    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"TRELLIS server exited early (code {proc.returncode}); see {log_path}")
        url = detect_server()
        if url:
            print(f"[OK] TRELLIS ready at {url}", file=sys.stderr)
            return url
        time.sleep(5)
    raise RuntimeError(f"TRELLIS server did not respond within {wait_seconds:.0f}s; see {log_path}")


def _pids_on_port(port: int) -> list[int]:
    pids: list[int] = []
    try:
        out = subprocess.check_output(["netstat", "-ano"], text=True, errors="replace")
    except Exception:
        return pids
    needle = f":{port}"
    for line in out.splitlines():
        if needle not in line or "LISTENING" not in line.upper():
            continue
        parts = line.split()
        if not parts:
            continue
        try:
            pid = int(parts[-1])
        except ValueError:
            continue
        if pid > 0:
            pids.append(pid)
    return sorted(set(pids))


def stop_server(*, force: bool = True) -> bool:
    """Ask TRELLIS to shut down; kill the :7960 listener if it stays up."""
    url = detect_server()
    if url:
        try:
            urllib.request.urlopen(f"{url}/shutdown", timeout=3).read()
            time.sleep(1.5)
        except Exception:
            pass
    if detect_server() is None and not _port_open(DEFAULT_HOST, _port()):
        print("[TRELLIS] stopped", file=sys.stderr)
        return True
    if not force:
        return detect_server() is None
    for pid in _pids_on_port(_port()):
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                check=False,
                capture_output=True,
                timeout=30,
            )
        except Exception as exc:
            print(f"[TRELLIS] taskkill {pid} failed: {exc}", file=sys.stderr)
    time.sleep(1.0)
    down = detect_server() is None
    print("[TRELLIS] stopped" if down else "[TRELLIS] still listening after stop", file=sys.stderr)
    return down


@contextmanager
def managed_trellis_server(
    *,
    keep: Optional[bool] = None,
    wait_seconds: float = STARTUP_TIMEOUT,
    autostart: bool = True,
) -> Iterator[Optional[str]]:
    """
    Ensure TRELLIS is up for the block; stop it afterward unless keep is set.

    keep defaults from AAMT_TRELLIS_KEEP_SERVER (false). One 11 GB card: idle
    TRELLIS must not linger and starve Stable Audio / SD / the game.
    """
    if keep is None:
        keep = keep_server()
    url = detect_server()
    started_here = False
    if not url and autostart:
        url = start_server(wait_seconds=wait_seconds)
        started_here = bool(url)
    try:
        yield url
    finally:
        if url and not keep:
            print("[TRELLIS] stopping server (job finished)", file=sys.stderr)
            stop_server(force=True)
        elif started_here and keep:
            print(
                "[TRELLIS] leaving server running (AAMT_TRELLIS_KEEP_SERVER=1)",
                file=sys.stderr,
            )


def _multipart(fields: Dict[str, str], file_path: Path) -> tuple[bytes, str]:
    boundary = f"----AAMT{uuid.uuid4().hex}"
    parts: list[bytes] = []
    for key, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode("utf-8")
        )
    ctype = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="{file_path.name}"\r\nContent-Type: {ctype}\r\n\r\n'.encode("utf-8")
    )
    parts.append(file_path.read_bytes())
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def generate_mesh(
    image_path: Path,
    output_path: Path,
    *,
    base_url: Optional[str] = None,
    resolution: int = SAFE_RESOLUTION,
    steps: int = 12,
    guidance_scale: float = 7.5,
    seed: int = 1234,
    mesh_simplify: int = 50,
    apply_texture: bool = True,
    texture_size: int = 1024,
    timeout: float = DEFAULT_READ_TIMEOUT,
    autostart: bool = False,
) -> Path:
    """
    Image -> textured GLB.

    resolution    512 / 1024 / 1536 voxel tier (512 is safe on 11 GB).
    mesh_simplify decimation target in thousands of faces (50 => ~50k).
    texture_size  baked texture resolution; 1024 keeps VRAM headroom.

    Stops the TRELLIS server after the job unless AAMT_TRELLIS_KEEP_SERVER=1
    (batch remesh). Idle TRELLIS holds several GB and starves SA3 / SD.

    Returns the written GLB path. Raises RuntimeError on failure.
    """
    image_path = Path(image_path)
    output_path = Path(output_path)
    if not image_path.is_file():
        raise RuntimeError(f"Reference image missing: {image_path}")

    try:
        base_url = base_url or detect_server(verbose=True)
        if not base_url and autostart:
            base_url = start_server()
        if not base_url:
            raise RuntimeError(
                "No TRELLIS server detected. Start it with "
                "trellis_http_client.py --start (default port 7960)."
            )

        fields = {
            "seed": str(seed),
            "guidance_scale": str(guidance_scale),
            "num_inference_steps": str(steps),
            "resolution": str(resolution),
            "mesh_simplify": str(mesh_simplify),
            "apply_texture": "true" if apply_texture else "false",
            "texture_size": str(texture_size),
            "output_format": "glb",
        }
        body, content_type = _multipart(fields, image_path)

        started = time.monotonic()
        print(f"[TRELLIS] POST {image_path.name} @ {resolution}^3, {steps} steps...", file=sys.stderr)

        with acquire_gpu(f"TRELLIS {resolution} {output_path.name}"):
            req = urllib.request.Request(
                f"{base_url}/generate_no_preview", data=body, headers={"Content-Type": content_type}
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    payload: Dict[str, Any] = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:500]
                raise RuntimeError(f"TRELLIS HTTP {exc.code}: {detail}") from exc
            except Exception as exc:
                raise RuntimeError(
                    f"TRELLIS request failed after {time.monotonic() - started:.0f}s: {exc}"
                ) from exc

            if payload.get("status") != "COMPLETE":
                raise RuntimeError(f"TRELLIS generation failed: {payload.get('message')}")

            output_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with urllib.request.urlopen(f"{base_url}/download/model", timeout=600) as resp:
                    output_path.write_bytes(resp.read())
            except Exception as exc:
                raise RuntimeError(f"TRELLIS model download failed: {exc}") from exc

        elapsed = time.monotonic() - started
        print(f"[OK] TRELLIS mesh saved ({elapsed:.1f}s): {output_path}", file=sys.stderr)
        return output_path
    finally:
        if not keep_server():
            print("[TRELLIS] stopping server (job finished)", file=sys.stderr)
            stop_server(force=True)


def generate_mesh_from_prompt(
    prompt: str,
    output_path: Path,
    *,
    reference_path: Optional[Path] = None,
    sd_width: int = 1024,
    sd_height: int = 1024,
    seed: int = 1234,
    **mesh_kwargs: Any,
) -> Dict[str, Path]:
    """SD reference image -> TRELLIS mesh, the common two-stage asset path."""
    from sd_http_client import generate_image

    output_path = Path(output_path)
    reference_path = Path(reference_path) if reference_path else output_path.with_name(
        f"{output_path.stem}_ref.png"
    )
    generate_image(
        prompt=prompt,
        output_path=reference_path,
        width=sd_width,
        height=sd_height,
        seed=seed,
    )
    mesh = generate_mesh(reference_path, output_path, seed=seed, **mesh_kwargs)
    return {"reference": reference_path, "mesh": mesh}


def main() -> int:
    parser = argparse.ArgumentParser(description="TRELLIS.2 image-to-3D via local HTTP API")
    parser.add_argument("--image", type=Path, default=None)
    parser.add_argument("--prompt", default="", help="generate the reference with SD first")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--resolution", type=int, default=SAFE_RESOLUTION)
    parser.add_argument("--steps", type=int, default=12)
    parser.add_argument("--guidance-scale", type=float, default=7.5)
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--mesh-simplify", type=int, default=50)
    parser.add_argument("--texture-size", type=int, default=1024)
    parser.add_argument("--no-texture", action="store_true")
    parser.add_argument("--timeout", type=float, default=DEFAULT_READ_TIMEOUT)
    parser.add_argument("--autostart", action="store_true")
    parser.add_argument("--detect-only", action="store_true")
    parser.add_argument("--start", action="store_true", help="start the server and exit")
    parser.add_argument("--stop", action="store_true", help="stop the server and exit")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    try:
        if args.detect_only:
            url = detect_server(verbose=True)
            if url:
                print(url)
                return 0
            return 1

        if args.start:
            print(start_server())
            return 0

        if args.stop:
            return 0 if stop_server() else 1

        if args.status:
            url = detect_server()
            print(json.dumps({"url": url, "running": bool(url), "busy": server_busy()}, indent=2))
            return 0 if url else 1

        if not args.output:
            print("[ERROR] --output is required", file=sys.stderr)
            return 2

        if args.prompt:
            result = generate_mesh_from_prompt(
                args.prompt,
                args.output,
                reference_path=args.image,
                seed=args.seed,
                resolution=args.resolution,
                steps=args.steps,
                guidance_scale=args.guidance_scale,
                mesh_simplify=args.mesh_simplify,
                texture_size=args.texture_size,
                apply_texture=not args.no_texture,
                timeout=args.timeout,
                autostart=args.autostart,
            )
            print(f"[OK] reference={result['reference']} mesh={result['mesh']}")
            return 0

        if not args.image:
            print("[ERROR] pass --image or --prompt", file=sys.stderr)
            return 2

        out = generate_mesh(
            args.image,
            args.output,
            resolution=args.resolution,
            steps=args.steps,
            guidance_scale=args.guidance_scale,
            seed=args.seed,
            mesh_simplify=args.mesh_simplify,
            apply_texture=not args.no_texture,
            texture_size=args.texture_size,
            timeout=args.timeout,
            autostart=args.autostart,
        )
        print(f"[OK] {out}")
        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
