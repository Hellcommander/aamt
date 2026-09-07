#!/usr/bin/env python3
"""
Shim: re-export Tools\\Common\\gpu_hub.py for modules that import via the
Shared directory (Shared tools and ElementalReforged tools both put Shared on
sys.path already, so `from gpu_hub import acquire_gpu` works everywhere).
The real implementation lives in Tools\\Common\\gpu_hub.py.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_impl_path = Path(__file__).resolve().parent.parent / "Common" / "gpu_hub.py"
_spec = importlib.util.spec_from_file_location("_aamt_common_gpu_hub", _impl_path)
if _spec is None or _spec.loader is None:
    raise ImportError(f"gpu_hub implementation not found at {_impl_path}")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

acquire_gpu = _mod.acquire_gpu
current_holder = _mod.current_holder
LOCK_FILE = _mod.LOCK_FILE
