#!/usr/bin/env python3
"""AAMT policy for Stable Diffusion art: procedural placeholders are never silent.

Generators whose intended pixels come from the SD3.5 server (:1338) must not quietly
draw procedural rings/noise when SD is down or a result fails QA - that art is useless
and hides the failure. Call ``procedural_fallback(reason)`` at the exact point where the
code would otherwise fall back:

    from sd_policy import procedural_fallback
    ...
    except Exception as exc:
        procedural_fallback(f"SD failed for {name}: {exc}", allow=args.allow_procedural)
        img = render_procedural(...)

It raises ``SdUnavailable`` unless procedural stand-ins were explicitly allowed (a CLI
flag passed as ``allow=True``, or AAMT_SD_STRICT=0 in the environment).
PowerShell scripts use the same switch: ``$sdStrict = ($env:AAMT_SD_STRICT -ne '0')``.
"""
from __future__ import annotations

import os
import sys


class SdUnavailable(RuntimeError):
    """SD art was required but could not be produced."""


def sd_strict() -> bool:
    """True (default): SD problems abort. AAMT_SD_STRICT=0 allows procedural stand-ins."""
    return os.environ.get("AAMT_SD_STRICT", "1").strip() != "0"


def procedural_fallback(reason: str, *, allow: bool = False) -> None:
    """Return only when a procedural stand-in is explicitly allowed; otherwise raise."""
    if allow or not sd_strict():
        print(
            f"[SD] WARNING: {reason}; using a procedural placeholder (explicitly allowed)",
            file=sys.stderr,
            flush=True,
        )
        return
    raise SdUnavailable(
        f"{reason}. Refusing procedural placeholder art - fix the SD server/prompt, pass the "
        "tool's explicit procedural/--no-sd option, or set AAMT_SD_STRICT=0."
    )
