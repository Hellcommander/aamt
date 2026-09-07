#!/usr/bin/env python3
"""
Broodmother sequential quality loop: draft → gate → review → correct → retry.

Exclusive GPU ownership per phase (11GB cannot hold SD + Ollama together):
  draft  — SD only (Ollama unloaded)
  police — heuristic + one Ollama critic + SD regen of failures
  full   — sequential multi-model review + SD regen of failures

Speed tiers keep the slow full path opt-in.

Resource thrift (Vortex-like): exclusive GPU ownership per phase so overnight
runs stay slow-but-gentle — not SD+Ollama fighting for 11GB / pagefile. After
generation finishes, later toolkit polish can improve exports without a full regen.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from PIL import Image

_QUD_DIR = Path(__file__).resolve().parent
_TOOLS_DIR = _QUD_DIR.parent
_SHARED_DIR = _TOOLS_DIR / "Shared"

if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))
if str(_QUD_DIR) not in sys.path:
    sys.path.insert(0, str(_QUD_DIR))

try:
    from ollama_integration import unload_all_models, get_loaded_models  # type: ignore
except ImportError:
    def unload_all_models(verbose: bool = False) -> int:  # type: ignore
        return 0

    def get_loaded_models() -> List[str]:  # type: ignore
        return []

try:
    from vortex_quality import validate_sprite_quality, finalize_qud_sprite  # type: ignore
    VORTEX_QUALITY = True
except ImportError:
    VORTEX_QUALITY = False
    validate_sprite_quality = None  # type: ignore
    finalize_qud_sprite = None  # type: ignore

SD_PING_URL = "http://127.0.0.1:1338/ping"
START_SD_BAT = _QUD_DIR / "Start-BroodmotherSDServer.bat"
STOP_SD_PS1 = _QUD_DIR / "Stop-SdServer.ps1"
START_SD_PS1 = _TOOLS_DIR / "Start-StableDiffusionServer.ps1"


def _log(phase: str, owner: str, msg: str, model: str = "") -> None:
    model_bit = f" model={model}" if model else ""
    print(f"  [{phase}|{owner}{model_bit}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# SD lifecycle
# ---------------------------------------------------------------------------
def sd_ping(timeout: float = 3.0) -> Dict[str, Any]:
    """Return parsed /ping JSON, or {} if unreachable."""
    try:
        with urllib.request.urlopen(SD_PING_URL, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def sd_ready(timeout: float = 3.0) -> bool:
    data = sd_ping(timeout=timeout)
    if not data:
        return False
    if data.get("ready") is True:
        return True
    return str(data.get("model_state", "")).lower() == "ready" or str(data.get("status", "")).lower() == "ok"


def sd_listening(timeout: float = 2.0) -> bool:
    return bool(sd_ping(timeout=timeout))


def ensure_sd_running(
    *,
    verbose: bool = False,
    wait_sec: int = 150,
    allow_start: bool = True,
) -> bool:
    """Ping SD; if down and allow_start, launch Broodmother SD server and wait for ready."""
    if sd_ready():
        if verbose:
            ping = sd_ping()
            _log("sd", "SD", f"already ready offload={ping.get('offload')} free={ping.get('gpu_free_gb')}GB")
        return True
    if sd_listening() and not sd_ready():
        if verbose:
            _log("sd", "SD", "listening but still loading — waiting for ready...")
        deadline = time.time() + wait_sec
        while time.time() < deadline:
            if sd_ready():
                return True
            time.sleep(2)
        _log("sd", "SD", "timed out waiting for ready while listening")
        return False
    if not allow_start:
        _log("sd", "SD", "not running and auto-start disabled")
        return False

    _log("sd", "SD", "starting CLIP-only SD3.5 server...")
    # Prefer bat (sets SD_SKIP_T5 etc.); fall back to ps1 -Force -NoStatusGui
    try:
        if START_SD_BAT.exists():
            subprocess.run(
                [str(START_SD_BAT), "nopause"],
                cwd=str(_QUD_DIR),
                timeout=wait_sec + 60,
                check=False,
            )
        elif START_SD_PS1.exists():
            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(START_SD_PS1),
                    "-Force",
                    "-WaitSec",
                    str(wait_sec),
                    "-NoStatusGui",
                ],
                cwd=str(_TOOLS_DIR),
                timeout=wait_sec + 60,
                check=False,
            )
        else:
            _log("sd", "SD", "no Start-BroodmotherSDServer.bat / Start-StableDiffusionServer.ps1 found")
            return False
    except subprocess.TimeoutExpired:
        _log("sd", "SD", "start script timed out — checking ping anyway")

    deadline = time.time() + max(30, wait_sec)
    while time.time() < deadline:
        if sd_ready():
            if verbose:
                _log("sd", "SD", "ready")
            return True
        if sd_listening() and verbose:
            _log("sd", "SD", "loading...")
        time.sleep(2)
    _log("sd", "SD", "failed to become ready")
    return False


def stop_sd(*, verbose: bool = False) -> None:
    """Stop SD on :1338 so Ollama can own the GPU."""
    if not sd_listening():
        if verbose:
            _log("handoff", "none", "SD already stopped")
        return
    _log("handoff", "none", "stopping SD on :1338...")
    if STOP_SD_PS1.exists():
        try:
            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(STOP_SD_PS1),
                ],
                cwd=str(_QUD_DIR),
                timeout=60,
                check=False,
            )
        except Exception as exc:
            _log("handoff", "none", f"Stop-SdServer failed: {exc}")
    # Wait until port frees
    for _ in range(30):
        if not sd_listening():
            break
        time.sleep(1)
    if verbose:
        _log("handoff", "none", "SD stop done" if not sd_listening() else "WARN: SD still listening")


def unload_ollama(*, verbose: bool = False) -> None:
    try:
        n = unload_all_models(verbose=verbose)
        if verbose:
            _log("handoff", "none", f"unloaded {n} Ollama model(s)")
    except Exception as exc:
        if verbose:
            _log("handoff", "none", f"ollama unload: {exc}")


# ---------------------------------------------------------------------------
# Cheap heuristic gate (CPU) — from finish_low_quality_broodmother_drafts
# ---------------------------------------------------------------------------
def score_draft_heuristic(path: Path) -> Dict[str, Any]:
    if not path.exists() or path.stat().st_size <= 0:
        return {
            "path": str(path),
            "name": path.name,
            "low": True,
            "reasons": ["missing_or_empty"],
            "coverage": 0.0,
            "mean_luma": 0.0,
            "unique": 0,
            "dark_frac": 1.0,
        }
    with Image.open(path) as im:
        rgba = im.convert("RGBA")
        px = list(rgba.getdata())
    n = max(1, len(px))
    opaque = [(r, g, b) for r, g, b, a in px if a >= 16]
    if not opaque:
        return {
            "path": str(path),
            "name": path.name,
            "low": True,
            "reasons": ["no_opaque_pixels"],
            "coverage": 0.0,
            "mean_luma": 0.0,
            "unique": 0,
            "dark_frac": 1.0,
        }
    cov = len(opaque) / n
    mean = sum(r + g + b for r, g, b in opaque) / (3.0 * len(opaque))
    uniq = len(set(opaque))
    dark = sum(1 for r, g, b in opaque if (r + g + b) < 40) / len(opaque)
    reasons: List[str] = []
    # Slightly aggressive gates — broken CLIP drafts are often near-black / flat.
    if cov < 0.08:
        reasons.append(f"coverage={cov:.3f}<0.08")
    if mean < 22.0:
        reasons.append(f"mean_luma={mean:.1f}<22")
    if dark > 0.78:
        reasons.append(f"dark_frac={dark:.3f}>0.78")
    if uniq <= 4 and mean < 48.0:
        reasons.append(f"uniq={uniq}<=4 and mean={mean:.1f}<48")

    # Vortex-style pixel gate when available
    if VORTEX_QUALITY and validate_sprite_quality is not None:
        try:
            with Image.open(path) as im2:
                ok, reason = validate_sprite_quality(im2.convert("RGBA"), min_edge_density=0.03)
            if not ok:
                reasons.append(f"vortex:{reason}")
        except Exception:
            pass

    return {
        "path": str(path),
        "name": path.name,
        "coverage": round(cov, 4),
        "mean_luma": round(mean, 2),
        "unique": uniq,
        "dark_frac": round(dark, 4),
        "low": bool(reasons),
        "reasons": reasons,
    }


def heuristic_corrections(reasons: Sequence[str]) -> Tuple[str, str]:
    """Build prompt/negative addenda from cheap fail reasons (no Ollama)."""
    bits: List[str] = []
    neg: List[str] = []
    joined = " ".join(reasons).lower()
    if "dark" in joined or "mean_luma" in joined or "no_opaque" in joined:
        bits.append("brighter midtones, readable silhouette, lit organic detail, not near-black void fill")
        neg.append("almost black, underexposed, empty silhouette, pure void blob")
    if "coverage" in joined:
        bits.append("subject fills frame, clear creature/equipment form, not tiny speck")
        neg.append("tiny subject, empty canvas, mostly transparent")
    if "uniq" in joined or "flat" in joined or "vortex" in joined:
        bits.append("rich organic texture, veins membranes chitin detail, high visual complexity")
        neg.append("flat single color, simple geometric shapes, featureless blob")
    if not bits:
        bits.append("higher detail organic biotech, clearer form, game-ready readability")
        neg.append("blurry, low quality, simple shapes")
    return (", ".join(bits), ", ".join(neg))


# ---------------------------------------------------------------------------
# Review result normalization
# ---------------------------------------------------------------------------
@dataclass
class ReviewResult:
    quality_score: float
    needs_refinement: bool
    feedback: str
    refined_prompt: str
    refined_negative_prompt: str
    source: str = "none"


@dataclass
class AssetRetryState:
    asset_id: str
    iteration: int = 0
    best_score: float = -1.0
    best_path: Optional[Path] = None
    previous_feedback: Optional[str] = None
    last_reasons: List[str] = field(default_factory=list)


def polish_export(img: Image.Image, size: Tuple[int, int]) -> Image.Image:
    if VORTEX_QUALITY and finalize_qud_sprite is not None:
        return finalize_qud_sprite(img, target_size=size)
    return img.resize(size, Image.Resampling.LANCZOS)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
@dataclass
class QualityLoopConfig:
    mode: str  # draft | police | full
    quality_threshold: int = 75
    max_refinement_iterations: int = 3
    verbose: bool = False
    skip_sd35: bool = False
    skip_export: bool = False
    no_postprocess: bool = False
    auto_start_sd: bool = True
    sd_wait_sec: int = 150
    enable_vision_models: bool = True
    enable_preference_scorer: bool = True
    ollama_model: str = "wizardlm-uncensored:latest"


def run_quality_loop(
    jobs: Sequence[Any],
    *,
    draft_dir: Path,
    sd_module_path: Path,
    shared_dir: Path,
    config: QualityLoopConfig,
    run_sd_generate: Callable[..., bool],
    art_director_review: Callable[..., Dict],
    export_from_draft: Callable[..., bool],
    imagemagick_post: Optional[Callable[..., None]] = None,
    multi_agent_director: Any = None,
    cache: Any = None,
) -> Dict[str, Any]:
    """
    Sequential critique→correct→retry loop.

    jobs: sequence of AssetJob-like objects (asset_id, sd35, draft_path, export_paths, meta)
    """
    mode = (config.mode or "draft").strip().lower()
    if mode not in ("draft", "police", "full"):
        mode = "draft"

    results: Dict[str, Any] = {
        "quality_mode": mode,
        "drafts_created": 0,
        "drafts_skipped": 0,
        "exports_created": 0,
        "retries": 0,
        "reviews": 0,
        "jobs": [],
        "phase_log": [],
    }

    def phase(name: str, owner: str, msg: str, model: str = "") -> None:
        entry = {"phase": name, "owner": owner, "model": model, "msg": msg, "t": time.strftime("%H:%M:%S")}
        results["phase_log"].append(entry)
        _log(name, owner, msg, model=model)

    # --- Phase 1 is prompts (already done by caller before build_jobs) ---
    # --- Phase 2: SD drafts (batch while SD is up) ---
    if not config.skip_sd35:
        phase("draft", "SD", f"mode={mode}; ensuring SD, unloading Ollama first")
        unload_ollama(verbose=config.verbose)
        if not ensure_sd_running(
            verbose=config.verbose,
            wait_sec=config.sd_wait_sec,
            allow_start=config.auto_start_sd,
        ):
            phase("draft", "SD", "SD unavailable — drafts will be skipped")
        else:
            for i, job in enumerate(jobs, 1):
                if not job.sd35.prompt:
                    results["drafts_skipped"] += 1
                    continue
                phase("draft", "SD", f"[{i}/{len(jobs)}] {job.asset_id}")
                ok = run_sd_generate(
                    sd_module_path=sd_module_path,
                    params=job.sd35,
                    output_path=job.draft_path,
                    verbose=config.verbose,
                    cache=cache,
                )
                if ok:
                    results["drafts_created"] += 1
                else:
                    results["drafts_skipped"] += 1
    else:
        phase("draft", "none", "skipped (--skip-sd35)")

    if mode == "draft":
        # Export only — no review/retry
        if not config.skip_export:
            phase("export", "CPU", f"exporting {len(jobs)} job(s)")
            for job in jobs:
                job_result = {"asset_id": job.asset_id, "draft": str(job.draft_path), "exports": [], "quality": None}
                for out_path, size in job.export_paths:
                    ok = export_from_draft(
                        job.draft_path,
                        out_path,
                        size,
                        truecolor=bool(job.meta.get("truecolor", False)),
                    )
                    if ok and VORTEX_QUALITY and finalize_qud_sprite is not None and out_path.exists():
                        try:
                            with Image.open(out_path) as im:
                                polished = finalize_qud_sprite(im.convert("RGBA"), target_size=size)
                            polished.save(out_path, "PNG", optimize=True)
                        except Exception:
                            pass
                    job_result["exports"].append({"path": str(out_path), "size": list(size), "ok": ok})
                    if ok:
                        results["exports_created"] += 1
                        if imagemagick_post and not config.no_postprocess:
                            imagemagick_post(shared_dir=shared_dir, image_path=out_path)
                results["jobs"].append(job_result)
        return results

    # --- Phase 3: handoff — stop SD before Ollama review ---
    phase("handoff", "none", "stopping SD + clearing path for Ollama review")
    stop_sd(verbose=config.verbose)
    # Keep Ollama unloaded until first review call loads the critic

    # --- Phases 4–6: heuristic → review → batch SD retry ---
    states: Dict[str, AssetRetryState] = {
        job.asset_id: AssetRetryState(asset_id=job.asset_id) for job in jobs
    }
    # Mutable prompt overrides per asset
    prompt_override: Dict[str, Tuple[str, str]] = {}

    for iteration in range(config.max_refinement_iterations):
        failing: List[Any] = []
        phase("gate", "CPU", f"iteration {iteration + 1}/{config.max_refinement_iterations} heuristic gate")

        for job in jobs:
            if not job.draft_path.exists():
                failing.append(job)
                states[job.asset_id].last_reasons = ["missing_draft"]
                continue
            hs = score_draft_heuristic(job.draft_path)
            if hs["low"]:
                failing.append(job)
                states[job.asset_id].last_reasons = list(hs["reasons"])
                if config.verbose:
                    phase("gate", "CPU", f"{job.asset_id} FAIL: {', '.join(hs['reasons'])}")
            else:
                if config.verbose:
                    phase("gate", "CPU", f"{job.asset_id} pass heuristic")

        # Review passers with Ollama (police: single critic; full: multi-agent sequential)
        # Also review heuristic failures with cheap corrections only (no vision) on first pass;
        # still run Ollama critic on heuristic-pass assets that may be "pretty but wrong".
        to_review = [j for j in jobs if j.draft_path.exists() and j not in failing]
        review_failures: List[Any] = []

        if to_review:
            phase(
                "review",
                "Ollama",
                f"reviewing {len(to_review)} draft(s) mode={mode}",
                model=config.ollama_model if mode == "police" else "sequential-agents",
            )
            # Ensure SD stays down during review
            if sd_listening():
                stop_sd(verbose=config.verbose)

            for job in to_review:
                st = states[job.asset_id]
                asset_type = str(job.meta.get("type", "asset"))
                original_prompt = prompt_override.get(job.asset_id, (job.sd35.prompt, job.sd35.negative_prompt))[0]
                review = _do_review(
                    job.draft_path,
                    original_prompt=original_prompt,
                    asset_type=asset_type,
                    iteration=iteration,
                    previous_feedback=st.previous_feedback,
                    mode=mode,
                    config=config,
                    art_director_review=art_director_review,
                    multi_agent_director=multi_agent_director,
                    cache=cache,
                )
                results["reviews"] += 1
                st.iteration = iteration
                if review.quality_score > st.best_score:
                    st.best_score = review.quality_score
                    st.best_path = job.draft_path
                phase(
                    "review",
                    "Ollama",
                    f"{job.asset_id} score={review.quality_score:.0f} refine={review.needs_refinement} src={review.source}",
                    model=config.ollama_model if mode == "police" else review.source,
                )
                if review.needs_refinement and review.quality_score < config.quality_threshold:
                    review_failures.append(job)
                    st.previous_feedback = review.feedback
                    st.last_reasons = [f"score={review.quality_score:.0f}<{config.quality_threshold}"]
                    # Merge corrections into prompt override
                    base_p = job.sd35.prompt
                    base_n = job.sd35.negative_prompt
                    refined_p = review.refined_prompt or base_p
                    refined_n = review.refined_negative_prompt or base_n
                    if review.feedback and review.feedback not in refined_p:
                        refined_p = f"{refined_p}. CORRECTIONS: {review.feedback[:500]}"
                    prompt_override[job.asset_id] = (refined_p, refined_n)
                    if config.verbose and review.feedback:
                        phase("review", "Ollama", f"corrections: {review.feedback[:160]}...")

        # Heuristic failures → cheap corrections (no vision burn)
        for job in failing:
            add_p, add_n = heuristic_corrections(states[job.asset_id].last_reasons)
            base_p, base_n = prompt_override.get(
                job.asset_id, (job.sd35.prompt, job.sd35.negative_prompt)
            )
            prompt_override[job.asset_id] = (
                f"{base_p}. FIX: {add_p}",
                f"{base_n}, {add_n}" if base_n else add_n,
            )

        need_regen = list({j.asset_id: j for j in (failing + review_failures)}.values())
        if not need_regen:
            phase("review", "Ollama", "all drafts meet threshold — done refining")
            break

        if iteration >= config.max_refinement_iterations - 1:
            phase("retry", "none", f"{len(need_regen)} still failing but max iterations reached")
            break

        # --- Phase 6: batch SD regen while server stays up ---
        phase("retry", "SD", f"regenerating {len(need_regen)} failure(s) (batch)")
        unload_ollama(verbose=config.verbose)
        if not ensure_sd_running(
            verbose=config.verbose,
            wait_sec=config.sd_wait_sec,
            allow_start=config.auto_start_sd,
        ):
            phase("retry", "SD", "cannot start SD for retries — aborting refine loop")
            break

        for job in need_regen:
            p, n = prompt_override.get(job.asset_id, (job.sd35.prompt, job.sd35.negative_prompt))
            new_params = replace(
                job.sd35,
                prompt=p,
                negative_prompt=n,
                seed=int(job.sd35.seed) + iteration + 1,
                enhance_with_ollama=False,
                auto_start_server=False,
            )
            # Force overwrite
            try:
                if job.draft_path.exists():
                    job.draft_path.unlink()
            except OSError:
                pass
            ok = run_sd_generate(
                sd_module_path=sd_module_path,
                params=new_params,
                output_path=job.draft_path,
                verbose=config.verbose,
                cache=None,  # don't skip via cache
            )
            results["retries"] += 1
            if ok:
                results["drafts_created"] += 1
                phase("retry", "SD", f"{job.asset_id} regen OK")
            else:
                phase("retry", "SD", f"{job.asset_id} regen FAILED")

        # Handoff again before next review iteration
        phase("handoff", "none", "stop SD before next review pass")
        stop_sd(verbose=config.verbose)

    # Restore best drafts if we saved alternates (best_path is usually the draft itself)
    for job in jobs:
        st = states.get(job.asset_id)
        if st and st.best_path and st.best_path.exists() and st.best_path != job.draft_path:
            try:
                shutil.copy2(st.best_path, job.draft_path)
            except OSError:
                pass

    # --- Phase 7: export ---
    if not config.skip_export:
        phase("export", "CPU", f"exporting {len(jobs)} job(s)")
        for job in jobs:
            st = states.get(job.asset_id)
            job_result = {
                "asset_id": job.asset_id,
                "draft": str(job.draft_path),
                "exports": [],
                "quality": {
                    "best_score": st.best_score if st else None,
                    "iterations": st.iteration if st else 0,
                    "last_reasons": st.last_reasons if st else [],
                },
            }
            for out_path, size in job.export_paths:
                ok = export_from_draft(
                    job.draft_path,
                    out_path,
                    size,
                    truecolor=bool(job.meta.get("truecolor", False)),
                )
                if ok and VORTEX_QUALITY and finalize_qud_sprite is not None and out_path.exists():
                    try:
                        with Image.open(out_path) as im:
                            polished = finalize_qud_sprite(im.convert("RGBA"), target_size=size)
                        polished.save(out_path, "PNG", optimize=True)
                    except Exception:
                        pass
                job_result["exports"].append({"path": str(out_path), "size": list(size), "ok": ok})
                if ok:
                    results["exports_created"] += 1
                    if imagemagick_post and not config.no_postprocess:
                        imagemagick_post(shared_dir=shared_dir, image_path=out_path)
            results["jobs"].append(job_result)

    # Leave SD stopped after police/full so Ollama can reclaim VRAM; caller may restart
    if mode in ("police", "full") and sd_listening():
        phase("handoff", "none", "final stop SD (review modes leave GPU free)")
        stop_sd(verbose=config.verbose)

    report_path = draft_dir / "quality_loop_report.json"
    try:
        report_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        phase("export", "CPU", f"wrote {report_path.name}")
    except OSError:
        pass

    return results


def _do_review(
    image_path: Path,
    *,
    original_prompt: str,
    asset_type: str,
    iteration: int,
    previous_feedback: Optional[str],
    mode: str,
    config: QualityLoopConfig,
    art_director_review: Callable[..., Dict],
    multi_agent_director: Any,
    cache: Any,
) -> ReviewResult:
    if mode == "full" and multi_agent_director is not None:
        try:
            # Prefer sequential API if present
            if hasattr(multi_agent_director, "review_asset_sequential"):
                agg = multi_agent_director.review_asset_sequential(
                    image_path=image_path,
                    original_prompt=original_prompt,
                    asset_type=asset_type,
                    iteration=iteration,
                    previous_feedback=previous_feedback,
                    target_style="Caves of Qud roguelike pixel art, organic biotech aesthetic",
                )
            else:
                agg = multi_agent_director.review_asset(
                    image_path=image_path,
                    original_prompt=original_prompt,
                    asset_type=asset_type,
                    iteration=iteration,
                    previous_feedback=previous_feedback,
                    target_style="Caves of Qud roguelike pixel art, organic biotech aesthetic",
                )
            return ReviewResult(
                quality_score=float(getattr(agg, "overall_quality", 0) or 0),
                needs_refinement=bool(getattr(agg, "needs_refinement", True)),
                feedback=str(getattr(agg, "creative_director_notes", "") or ""),
                refined_prompt=str(getattr(agg, "refined_prompt", original_prompt) or original_prompt),
                refined_negative_prompt=str(getattr(agg, "refined_negative_prompt", "") or ""),
                source="multi-agent-sequential",
            )
        except Exception as exc:
            _log("review", "Ollama", f"multi-agent failed ({exc}); falling back to single critic")

    # police (and full fallback): single wizardlm critic via existing helper
    try:
        review = art_director_review(
            image_path=image_path,
            original_prompt=original_prompt,
            asset_type=asset_type,
            iteration=iteration,
            previous_feedback=previous_feedback,
            verbose=config.verbose,
            cache=cache,
        )
        return ReviewResult(
            quality_score=float(review.get("quality_score", 0) or 0),
            needs_refinement=bool(review.get("needs_refinement", True)),
            feedback=str(review.get("feedback", "") or ""),
            refined_prompt=str(review.get("refined_prompt", original_prompt) or original_prompt),
            refined_negative_prompt=str(review.get("refined_negative_prompt", "") or ""),
            source="art-director",
        )
    except Exception as exc:
        _log("review", "Ollama", f"art director failed: {exc}")
        return ReviewResult(
            quality_score=0,
            needs_refinement=True,
            feedback=f"review error: {exc}",
            refined_prompt=original_prompt,
            refined_negative_prompt="",
            source="error",
        )
