#!/usr/bin/env python3
"""
DF wrapper around Tools/Shared/sd_http_client.py (mirrors qud_sd_client.py).
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

_shared_dir = Path(__file__).resolve().parent.parent / "Shared"
if str(_shared_dir) not in sys.path:
    sys.path.insert(0, str(_shared_dir))

SD_AVAILABLE = False
detect_server = None  # type: ignore
generate_image = None  # type: ignore

try:
    from sd_http_client import detect_server, generate_image  # type: ignore

    SD_AVAILABLE = True
except ImportError:
    pass

SD_LOCK_PATH = Path(__file__).resolve().parent / ".sd_generation.lock"
SD_LOCK_STALE_SEC = 14400.0
SD_TIMEOUT_SEC = 9000.0

REDUCED_SD = {"width": 512, "height": 512, "steps": 6, "guidance_scale": 6.5}


@dataclass(frozen=True)
class SdGenerateResult:
    ok: bool
    output_path: Optional[Path]
    settings: Dict[str, Any]
    error: str = ""
    salvaged: bool = False


def is_oom_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "out of memory" in msg or ("cuda" in msg and "memory" in msg)


def acquire_sd_lock(label: str, wait_timeout: float = SD_TIMEOUT_SEC) -> bool:
    SD_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SD_LOCK_PATH.exists():
        age = time.time() - SD_LOCK_PATH.stat().st_mtime
        if age < SD_LOCK_STALE_SEC:
            print(f"  [WAIT] SD lock held ({age:.0f}s ago); waiting...")
            deadline = time.monotonic() + min(wait_timeout, 600.0)
            while time.monotonic() < deadline:
                time.sleep(10)
                if not SD_LOCK_PATH.exists():
                    break
                age = time.time() - SD_LOCK_PATH.stat().st_mtime
                if age >= SD_LOCK_STALE_SEC:
                    break
            if SD_LOCK_PATH.exists() and time.time() - SD_LOCK_PATH.stat().st_mtime < SD_LOCK_STALE_SEC:
                print("  [WARN] SD lock still held; skipping SD generation")
                return False
    SD_LOCK_PATH.write_text(f"{label} pid={os.getpid()}", encoding="utf-8")
    return True


def release_sd_lock() -> None:
    try:
        if SD_LOCK_PATH.exists():
            SD_LOCK_PATH.unlink()
    except OSError:
        pass


def get_sd_api_url(verbose: bool = False) -> Optional[str]:
    if not SD_AVAILABLE or detect_server is None:
        return None
    return detect_server(verbose=verbose)


def generate_sd_draft(
    prompt: str,
    output_path: Path,
    *,
    negative_prompt: str = "",
    width: int = 512,
    height: int = 512,
    steps: int = 8,
    guidance_scale: float = 6.5,
    seed: int = 0,
    api_url: Optional[str] = None,
    lock_label: str = "df_sd",
    timeout: float = SD_TIMEOUT_SEC,
    retry_on_oom: bool = True,
    force: bool = False,
) -> SdGenerateResult:
    if not SD_AVAILABLE or generate_image is None:
        return SdGenerateResult(False, None, {}, "sd_http_client unavailable")

    if not force and output_path.exists() and output_path.stat().st_size > 0:
        return SdGenerateResult(True, output_path, {"cached": True})

    url = api_url or get_sd_api_url(verbose=False)
    if not url:
        return SdGenerateResult(False, None, {}, "no SD server detected")

    if not acquire_sd_lock(lock_label):
        return SdGenerateResult(False, None, {}, "SD lock unavailable")

    settings = {
        "width": width,
        "height": height,
        "steps": steps,
        "guidance_scale": guidance_scale,
        "seed": seed,
    }
    started_at = time.time()
    try:
        try:
            generate_image(
                prompt=prompt,
                output_path=output_path,
                api_url=url,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                steps=steps,
                guidance_scale=guidance_scale,
                seed=seed,
                timeout=timeout,
            )
            ok = output_path.exists() and output_path.stat().st_size > 0
            return SdGenerateResult(ok, output_path if ok else None, settings)
        except Exception as exc:
            if retry_on_oom and is_oom_error(exc):
                print(f"  [WARN] SD OOM; retrying reduced settings: {exc}")
                rs = REDUCED_SD
                generate_image(
                    prompt=prompt,
                    output_path=output_path,
                    api_url=url,
                    negative_prompt=negative_prompt,
                    width=rs["width"],
                    height=rs["height"],
                    steps=rs["steps"],
                    guidance_scale=rs["guidance_scale"],
                    seed=seed,
                    timeout=timeout,
                )
                ok = output_path.exists() and output_path.stat().st_size > 0
                return SdGenerateResult(ok, output_path if ok else None, rs)
            try:
                from sd_http_client import salvage_server_output  # type: ignore

                salvaged_path = salvage_server_output(
                    output_path,
                    started_at=started_at,
                    width=width,
                    height=height,
                )
                if salvaged_path and Path(salvaged_path).exists():
                    return SdGenerateResult(
                        True, Path(salvaged_path), settings, str(exc), salvaged=True
                    )
            except Exception:
                pass
            salvaged = "salvaged" in str(exc).lower()
            return SdGenerateResult(False, None, settings, str(exc), salvaged=salvaged)
    finally:
        release_sd_lock()
