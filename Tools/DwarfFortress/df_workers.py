#!/usr/bin/env python3
"""
AAMT-side worker pool for DF creature analysis.

Workers compute on frozen snapshots (spec dict / graph dicts).
File writes and DF memory mutations stay on the caller thread.
Does NOT multithread Dwarf Fortress itself.
"""

from __future__ import annotations

import copy
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


def worker_count(override: Optional[int] = None) -> int:
    if override is not None and override > 0:
        return override
    env = (os.environ.get("AAMT_DF_WORKERS") or "").strip()
    if env.isdigit() and int(env) > 0:
        return int(env)
    return max(1, min(8, (os.cpu_count() or 4)))


def snapshot_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    return copy.deepcopy(spec)


def _task_analyze(spec: Dict[str, Any]) -> Dict[str, Any]:
    from df_body_cost import analyze_costs

    return analyze_costs(snapshot_spec(spec), full=True)


def _task_police(spec: Dict[str, Any], validation: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    from df_ollama_police import police_body_plan

    return police_body_plan(snapshot_spec(spec), validation=validation)


def _task_validate(spec: Dict[str, Any]) -> Dict[str, Any]:
    from df_body_logic import validate

    return validate(snapshot_spec(spec)).to_dict()


def run_parallel(
    jobs: List[tuple],
    *,
    workers: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Run named jobs in a thread pool. Returns {name: result_or_error}.
    Callers must perform any disk writes after this returns.
    """
    n = worker_count(workers)
    results: Dict[str, Any] = {}
    if n <= 1 or len(jobs) <= 1:
        for name, fn, args, kwargs in jobs:
            try:
                results[name] = fn(*args, **kwargs)
            except Exception as exc:
                results[name] = {"error": str(exc)}
        return results

    with ThreadPoolExecutor(max_workers=n) as pool:
        futs = {pool.submit(fn, *args, **kwargs): name for name, fn, args, kwargs in jobs}
        for fut in as_completed(futs):
            name = futs[fut]
            try:
                results[name] = fut.result()
            except Exception as exc:
                results[name] = {"error": str(exc)}
    return results


def analyze_async(spec: Dict[str, Any], *, workers: Optional[int] = None, police: bool = False) -> Dict[str, Any]:
    jobs = [
        ("validate", _task_validate, (spec,), {}),
        ("cost", _task_analyze, (spec,), {}),
    ]
    out = run_parallel(jobs, workers=workers)
    if police:
        val = out.get("validate") if isinstance(out.get("validate"), dict) else None
        out["police"] = _task_police(spec, val)
    return out


def _task_art_cell(
    part: str,
    state: str,
    color: tuple,
    tile: int = 32,
    features: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Pillow-draw one 32x32 cell; returns PNG bytes. Caller pastes on main thread."""
    from io import BytesIO

    from df_pixel_art import render_part_tile

    img = render_part_tile(part, state, color, features, tile=tile)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return {"part": part, "state": state, "png": buf.getvalue()}


def generate_art_sheet_parallel(
    creature_id: str,
    art_prompt: str = "",
    color: Optional[tuple] = None,
    *,
    workers: Optional[int] = None,
    features: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Draw 7x5 part-sheet cells in worker threads; assemble on caller thread.
    Does not write files.
    """
    from df_tile_generator import COLS, PARTS, ROWS, STATES, TILE, _color_from_id, _try_pillow

    Image, _ = _try_pillow()
    if Image is None:
        raise RuntimeError("Pillow required for art_sheet")
    col = color or _color_from_id(creature_id, art_prompt)
    feat = dict(features or {})
    jobs = []
    for state in STATES:
        for part in PARTS:
            name = f"{state}:{part}"
            jobs.append((name, _task_art_cell, (part, state, col, TILE, feat), {}))
    cells = run_parallel(jobs, workers=workers)
    sheet = Image.new("RGBA", (TILE * COLS, TILE * ROWS), (0, 0, 0, 0))
    from io import BytesIO

    for row, state in enumerate(STATES):
        for col_i, part in enumerate(PARTS):
            key = f"{state}:{part}"
            payload = cells.get(key) or {}
            raw = payload.get("png") if isinstance(payload, dict) else None
            if not raw:
                continue
            tile_im = Image.open(BytesIO(raw)).convert("RGBA")
            sheet.paste(tile_im, (col_i * TILE, row * TILE), tile_im)
    return {"sheet": sheet, "cell_count": len(cells), "workers": worker_count(workers)}
