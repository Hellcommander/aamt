#!/usr/bin/env python3
"""Shared asset-aware audio generation stage.

Retrieve clips from the purchased/made library (D:\\assets\\audio), then either
condition Stable Audio 3 on those references or fall back to a library mix.

  python audio_pipeline.py status
  python audio_pipeline.py ingest --fast
  python audio_pipeline.py search --query "crunchy sci-fi UI click"
  python audio_pipeline.py generate --prompt "short plasma vent burst" --out vent.wav --archetype laser
  python audio_pipeline.py check "path\\to\\mod\\Sound"
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from audio_asset_library import (  # noqa: E402
    NOISE_ALCHEMY_CREDIT,
    OWN_DIR,
    AudioLibrary,
    RetrievalHit,
    blend_waveforms,
    load_asset_audio,
)

DEFAULT_NEGATIVE = (
    "music, singing, speech, lyrics, low quality, muffled, distortion, silence, hiss"
)

# Pack ToS: "reference" tier packs (Noise Alchemy incl. its Dark Fantasy Studio packs, unknown)
# are DNA only — unique SA3 mode. "direct" tier packs (Function Loops bt25, Tao &
# Sound bundle) may also go through close-copy. No tier ships an original: every
# output is altered until its source_corr against each raw reference clip is
# under UNIQUE_MAX_CORR, so a pack file cannot be recovered from a mod.
# "own" tier clips (D:\assets\audio\made, filled by --keep) are ours: they ship
# and are reused as-is, and never count toward source_corr.
# Unique mode blends several refs, mutates that mix, then SA3 with high init noise;
# copy_corr is the "altered enough" bar (must stay under the cap after retries).
UNIQUE_STRENGTH_CAP = 0.28
UNIQUE_MIN_K = 10
UNIQUE_MAX_CORR = 0.22
# Extra SA3 retries with escalating noise when the first pass stays too close.
UNIQUE_CORR_RETRIES = 3
UNIQUE_NOISE_BUMP = 0.18
# How hard unique mode mutates the reference mix *before* SA3 sees it (0–1).
UNIQUE_DNA_MUTATE = float(os.environ.get("AAMT_AUDIO_DNA_MUTATE", "0.72"))
# Escalating DSP alteration for close-copy / blend output (stops once distinct).
ADJUST_AMOUNTS = (0.45, 0.65, 0.85)
# Formats `check` can read (soundfile); Bethesda .xwm/.fuz must be decoded first.
CHECK_EXTS = {".wav", ".ogg", ".flac", ".mp3", ".aif", ".aiff"}


def _env_flag(name: str, default: str = "1") -> bool:
    return os.environ.get(name, default).strip().lower() not in ("0", "false", "no", "off", "")


def _lib(library: Optional[Path] = None, index_dir: Optional[Path] = None) -> AudioLibrary:
    return AudioLibrary(library=library, index_dir=index_dir)


def status(library: Optional[Path] = None) -> Dict[str, Any]:
    info = _lib(library).status()
    sa3: Dict[str, Any] = {"ready": False, "error": ""}
    try:
        import aamt_stable_audio_backend as backend

        sa3["ready"] = bool(backend.is_available())
        sa3["error"] = backend.last_error() or ""
        sa3["model"] = os.environ.get("AAMT_STABLE_AUDIO_MODEL", "medium")
    except Exception as exc:
        sa3["error"] = str(exc)
    info["stable_audio"] = sa3
    info["stage"] = "audio"
    info["ready"] = bool(info.get("library_exists")) and (sa3["ready"] or int(info.get("assets") or 0) > 0)
    return info


def ingest(
    *,
    src: Optional[Path] = None,
    fast: bool = False,
    clap: bool = True,
    whisper: bool = True,
    pack: str = "",
    limit: int = 0,
) -> Dict[str, Any]:
    lib = _lib(src)
    print(f"[audio] ingest {lib.library} → {lib.index_dir}")
    return lib.ingest(src=src, fast=fast, clap=clap, whisper=whisper, pack_glob=pack, limit=limit)


def backfill_clap(
    *,
    src: Optional[Path] = None,
    resume: bool = True,
    save_every: int = 100,
) -> Dict[str, Any]:
    lib = _lib(src)
    print(f"[audio] backfill CLAP {lib.library} → {lib.index_dir}")
    return lib.backfill_clap(resume=resume, save_every=save_every)


def rebuild_tags(*, src: Optional[Path] = None) -> Dict[str, Any]:
    lib = _lib(src)
    print(f"[audio] rebuild tag vectors {lib.index_dir}")
    return lib.rebuild_tags()


def search(
    query: str = "",
    *,
    audio: Optional[Path] = None,
    k: int = 8,
    archetype: str = "",
    tags: Optional[Sequence[str]] = None,
    library: Optional[Path] = None,
    license: str = "",
) -> List[RetrievalHit]:
    lib = _lib(library)
    lib.load()
    if audio:
        wav, sr = _read_wav(Path(audio))
        return lib.search_audio(wav, sr, k=k, archetype=archetype, license=license)
    if not query:
        raise ValueError("search needs --query or --audio")
    return lib.search_text(query, k=k, archetype=archetype, tags=tags, license=license)


def generate_audio(
    prompt: str,
    output: Path,
    *,
    duration: float = 2.5,
    k: int = 4,
    strength: float = 0.65,
    archetype: str = "",
    tags: Optional[Sequence[str]] = None,
    seed: Optional[int] = None,
    model_name: Optional[str] = None,
    no_refs: bool = False,
    example: Optional[Path] = None,
    library: Optional[Path] = None,
    engine: str = "auto",
    unique: Optional[bool] = None,
    direct_only: bool = False,
    keep: bool = False,
) -> Path:
    """Retrieve library DNA, generate a new clip, write WAV.

    strength 0 = text-only SA3; 1 = stay close to retrieved references.
    unique (default on) caps strength, mixes several refs, skips filename
    style prompts and envelope matching, and refuses a library-mix fallback
    so shipped clips are not raw or near copies of D:\\assets\\audio packs.
    direct_only restricts references to "direct" and "own" tier clips, which
    makes close-copy (unique=False) output shippable. keep copies shippable
    output into D:\\assets\\audio\\made as a reusable own-tier clip.
    """
    if unique is None:
        unique = _env_flag("AAMT_AUDIO_UNIQUE", "1")
    if unique and engine == "library":
        raise RuntimeError("unique mode refuses engine=library (would ship a pack mix)")
    if unique:
        strength = min(float(strength), UNIQUE_STRENGTH_CAP)
        k = max(int(k), UNIQUE_MIN_K)

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    hits: List[RetrievalHit] = []
    init_audio = None
    used_ids: List[str] = []
    lib = _lib(library)
    lic = ("direct", "own") if direct_only else ""
    if not no_refs:
        lib.load()
        if example:
            wav, sr = _read_wav(Path(example))
            hits = lib.search_audio(wav, sr, k=k, archetype=archetype, license=lic)
        elif lib.records:
            hits = lib.search_text(prompt, k=k, archetype=archetype, tags=tags, license=lic)
            # Unique mode must use pack DNA. Archetype/tag filters can wipe the
            # index; widen the search rather than falling through to text-only.
            if unique and not hits:
                hits = lib.search_text(prompt, k=k, archetype=archetype, license=lic)
            if unique and not hits:
                hits = lib.search_text(prompt, k=k, license=lic)
        if unique and not no_refs and not hits:
            raise RuntimeError(
                "unique mode needs pack DNA hits (ToS: modify/mix/transform); "
                "search returned nothing"
            )
        if hits:
            mix, mix_sr, used_ids = lib.mix_references(hits, max_seconds=max(duration, 0.5), sr=48000)
            # Unique: scramble the mix so SA3 never conditions on a near-raw pack clip.
            if unique and UNIQUE_DNA_MUTATE > 0:
                mix = _mutate_reference_dna(
                    mix,
                    mix_sr,
                    amount=UNIQUE_DNA_MUTATE,
                    seed=seed if seed is not None else abs(hash(prompt)) % (2**31),
                )
                print(f"[audio] mutated reference DNA amount={UNIQUE_DNA_MUTATE:.2f}")
            init_audio = (mix_sr, mix)
            print("[audio] refs:")
            for hit in hits:
                print(f"    {hit.score:6.3f}  {hit.via:14}  {hit.record.label()}")

    conditioned = _condition_prompt(prompt, hits, archetype=archetype, unique=unique)
    # Unique stays noisier so the DiT rewrites spectral shape instead of echoing DNA.
    noise_keep = 0.45 if unique else 0.70
    init_noise = 1.0 - noise_keep * float(np.clip(strength, 0.0, 1.0))
    if unique:
        init_noise = max(init_noise, 0.78)
    if init_audio is None or strength <= 0:
        init_audio = None
        init_noise = 1.0

    arr: Optional[np.ndarray] = None
    sr = 48000
    engine_used = "library-mix"
    copy_corr = 0.0
    if engine != "library":
        try:
            import aamt_stable_audio_backend as backend

            def _sa3(noise: float, run_seed: Optional[int]) -> Optional[Tuple[np.ndarray, int]]:
                return backend.maybe_generate(
                    engine=engine,
                    model_name=model_name,
                    prompt=conditioned,
                    duration=float(duration),
                    seed=run_seed if run_seed is not None else backend.seed_from_text(conditioned),
                    init_audio=init_audio,
                    init_noise_level=noise,
                    steps=backend.unique_steps() if unique else None,
                    negative_prompt=backend.unique_negative() if unique else None,
                )

            base_seed = seed if seed is not None else None
            result = _sa3(init_noise, base_seed)
            if result is not None:
                arr, sr = result
                engine_used = "stable-audio"
                if unique and init_audio is not None:
                    # Compare against the *unmutated* search mix when available via used refs;
                    # init_audio is already mutated, so corr vs that understates pack leakage.
                    copy_corr = _copy_corr(arr, init_audio[1])
                    attempt = 0
                    while copy_corr > UNIQUE_MAX_CORR and attempt < UNIQUE_CORR_RETRIES:
                        attempt += 1
                        retry_noise = min(1.0, init_noise + UNIQUE_NOISE_BUMP * attempt)
                        retry_seed = (
                            (base_seed + 7919 * attempt) if base_seed is not None else None
                        )
                        print(
                            f"[audio] copy-corr {copy_corr:.3f} > {UNIQUE_MAX_CORR:.2f}; "
                            f"retry {attempt}/{UNIQUE_CORR_RETRIES} noise={retry_noise:.2f}",
                            flush=True,
                        )
                        retry = _sa3(retry_noise, retry_seed)
                        if retry is None:
                            break
                        arr2, sr2 = retry
                        corr2 = _copy_corr(arr2, init_audio[1])
                        if corr2 < copy_corr:
                            arr, sr = arr2, sr2
                            copy_corr = corr2
                            init_noise = retry_noise
        except Exception as exc:
            if unique or engine == "stable-audio":
                raise RuntimeError(
                    f"Stable Audio 3 failed ({exc}); refusing library-mix"
                ) from exc
            print(f"[audio] SA3 failed ({exc}); using library mix")

    if arr is None:
        if unique or engine == "stable-audio":
            raise RuntimeError("Stable Audio 3 produced nothing; refusing library-mix")
        if init_audio is None:
            raise RuntimeError(
                "audio stage has nothing to generate from — ingest the library "
                "(python audio_pipeline.py ingest --fast) or install Stable Audio 3"
            )
        sr, arr = init_audio
        arr = _fit_duration(arr, sr, duration)
        engine_used = "library-mix"

    # Unique never envelope-matches pack DNA; apply a second DSP morph after SA3.
    if unique:
        arr = _unique_post_morph(
            arr,
            sr,
            seed=seed if seed is not None else abs(hash(conditioned)) % (2**31),
        )
        arr = _postprocess(arr, reference=None)
    else:
        ref = init_audio[1] if init_audio else None
        arr = _postprocess(arr, reference=ref)
    source_corr = 0.0
    if hits:
        refs = [h.record for h in hits]
        if unique:
            source_corr = _source_corr(lib, refs, arr, sr)
        else:
            arr, source_corr = _adjust_until_distinct(
                lib,
                refs,
                arr,
                sr,
                seed=seed if seed is not None else abs(hash(conditioned)) % (2**31),
            )
    _write_wav(output, arr, sr)

    reference_tier = any(h.record.license_tier() == "reference" for h in hits)
    shippable = source_corr <= UNIQUE_MAX_CORR and (bool(unique) or not reference_tier)
    if not shippable:
        why = (
            "close-copy of reference-tier packs; use unique mode or --direct-only"
            if reference_tier and not unique
            else f"source-corr {source_corr:.3f} > {UNIQUE_MAX_CORR:.2f}"
        )
        print(f"[audio] WARNING: not shippable ({why}) — do not add it to a mod")
    meta = {
        "prompt": prompt,
        "conditioned_prompt": conditioned,
        "duration": duration,
        "strength": strength,
        "init_noise_level": init_noise,
        "engine": engine_used,
        "unique": bool(unique),
        "copy_corr": copy_corr,
        "source_corr": source_corr,
        "archetype": archetype,
        "shippable": shippable,
        "attribution": _attribution(lib, [h.record for h in hits]),
        "references": [
            {
                "id": h.record.id,
                "score": h.score,
                "via": h.via,
                "pack": h.record.pack,
                "inner": h.record.inner,
                "license": h.record.license_tier(),
                "tags": h.record.tags,
                "archetypes": h.record.archetypes,
            }
            for h in hits
        ],
        "used_ids": used_ids,
        "output": str(output),
        "sample_rate": sr,
    }
    output.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[audio] wrote {output} ({engine_used}, {duration:.2f}s)")
    if keep:
        _keep(lib, output, meta)
    return output


def blend_assets(
    id_a: str,
    id_b: str,
    output: Path,
    *,
    alpha: float = 0.5,
    library: Optional[Path] = None,
    duration: float = 0.0,
    keep: bool = False,
) -> Path:
    lib = _lib(library)
    lib.load()
    rec_a = lib.get(id_a)
    rec_b = lib.get(id_b)
    if rec_a is None or rec_b is None:
        raise RuntimeError(f"unknown asset id: {id_a if rec_a is None else id_b}")
    wav_a, sr = load_asset_audio(rec_a, lib.library)
    wav_b, _sr_b = load_asset_audio(rec_b, lib.library, sr=sr)
    mixed = blend_waveforms(wav_a, wav_b, alpha)
    if duration > 0:
        mixed = _fit_duration(mixed, sr, duration)
    mixed = _postprocess(mixed)
    mixed, source_corr = _adjust_until_distinct(
        lib, [rec_a, rec_b], mixed, sr, seed=int(id_a[:8], 16) ^ int(id_b[:8], 16)
    )
    output = Path(output)
    _write_wav(output, mixed, sr)
    print(f"[audio] blend {rec_a.label()} × {rec_b.label()} α={alpha} → {output}")
    reference_tier = "reference" in (rec_a.license_tier(), rec_b.license_tier())
    shippable = source_corr <= UNIQUE_MAX_CORR and not reference_tier
    if reference_tier:
        print("[audio] WARNING: blend uses reference-tier clips — do not add it to a mod")
    elif not shippable:
        print(f"[audio] WARNING: source-corr {source_corr:.3f} still too close — do not add it to a mod")
    if keep:
        meta = {
            "prompt": f"blend {rec_a.name} {rec_b.name}",
            "archetype": next(iter(rec_a.archetypes or rec_b.archetypes), ""),
            "alpha": alpha,
            "source_corr": source_corr,
            "shippable": shippable,
            "attribution": _attribution(lib, [rec_a, rec_b]),
            "references": [{"id": r.id, "pack": r.pack, "inner": r.inner, "license": r.license_tier()} for r in (rec_a, rec_b)],
            "output": str(output),
            "sample_rate": sr,
        }
        _keep(lib, output, meta)
    return output


def _attribution(lib: AudioLibrary, records: Sequence[Any]) -> str:
    """Credit owed by clips built from `records` (own clips carry theirs in a sidecar meta)."""
    for rec in records:
        tier = rec.license_tier()
        if tier == "reference":
            return NOISE_ALCHEMY_CREDIT
        if tier == "own" and rec.source == "file":
            try:
                side = json.loads((lib.library / Path(rec.inner).with_suffix(".meta.json")).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if side.get("attribution"):
                return str(side["attribution"])
    return ""


def _keep(lib: AudioLibrary, wav: Path, meta: Dict[str, Any]) -> Optional[Path]:
    """Copy a shippable output into the own tier (made/<archetype>/) and index it."""
    if not meta.get("shippable"):
        print("[audio] --keep skipped: output is not shippable")
        return None
    dest = lib.library / OWN_DIR / (meta.get("archetype") or "misc") / Path(wav).name
    if dest.exists():
        print(f"[audio] --keep skipped: {dest} already exists")
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(wav, dest)
    dest.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    rec = lib.add_file(dest)
    print(f"[audio] kept as own-tier clip {rec.id}: {dest}")
    return dest


def check_files(
    paths: Sequence[Path],
    *,
    library: Optional[Path] = None,
    k: int = 5,
) -> List[Dict[str, Any]]:
    """Flag sound files (e.g. a mod's Sound tree) that are near copies of library clips."""
    lib = _lib(library)
    lib.load()
    files: List[Path] = []
    for p in map(Path, paths):
        if p.is_dir():
            files.extend(sorted(f for f in p.rglob("*") if f.suffix.lower() in CHECK_EXTS))
        else:
            files.append(p)
    rows: List[Dict[str, Any]] = []
    for f in files:
        try:
            wav, sr = _read_wav(f)
        except Exception as exc:
            rows.append({"file": str(f), "ok": None, "error": str(exc)})
            continue
        hits = lib.search_audio(wav[: int(8.0 * sr)], sr, k=k)
        best, closest = 0.0, ""
        for hit in hits:
            corr = _source_corr(lib, [hit.record], wav, sr)
            if corr > best:
                best, closest = corr, hit.record.label()
        rows.append(
            {"file": str(f), "ok": best <= UNIQUE_MAX_CORR, "source_corr": round(best, 3), "closest": closest}
        )
    return rows


def _source_corr(lib: AudioLibrary, records: Sequence[Any], arr: np.ndarray, sr: int) -> float:
    """Highest copy_corr of `arr` against the raw (unmixed, unmutated) source clips.

    Fails closed: a source that cannot be decoded counts as 1.0 (too close), since
    it cannot be proven distinct. `pip install av` decodes the library's MP3s.
    """
    best = 0.0
    for rec in records:
        if rec.license_tier() == "own":
            continue
        try:
            raw, _ = load_asset_audio(rec, lib.library, max_seconds=30.0, sr=sr)
        except Exception as exc:
            print(f"  [audio] cannot verify against {rec.label()} (treated as too close): {exc}")
            return 1.0
        best = max(best, _copy_corr(arr, raw))
    return best


def _adjust_until_distinct(
    lib: AudioLibrary,
    records: Sequence[Any],
    arr: np.ndarray,
    sr: int,
    *,
    seed: int = 0,
) -> Tuple[np.ndarray, float]:
    """Alter a close-copy clip until no raw source clip can be recovered from it."""
    best_arr, best_corr = arr, float("inf")
    for amount in ADJUST_AMOUNTS:
        y = _mutate_reference_dna(arr, sr, amount=amount, seed=seed)
        y = _postprocess(_unique_post_morph(y, sr, seed=seed), reference=None)
        corr = _source_corr(lib, records, y, sr)
        print(f"[audio] adjust amount={amount:.2f} source-corr={corr:.3f}")
        if corr < best_corr:
            best_arr, best_corr = y, corr
        if corr <= UNIQUE_MAX_CORR:
            break
    return best_arr, best_corr


def _condition_prompt(
    prompt: str,
    hits: Sequence[RetrievalHit],
    *,
    archetype: str = "",
    unique: bool = False,
) -> str:
    bits = ["high quality game sound effect"]
    if archetype:
        bits.append(f"{archetype} sound")
    bits.append(prompt.strip())
    if hits:
        tags: List[str] = []
        for hit in hits[:3]:
            if not unique:
                tags.extend(hit.record.tags[:6])
            tags.extend(hit.record.archetypes)
        seen = set()
        extra = []
        for t in tags:
            if t in seen:
                continue
            seen.add(t)
            extra.append(t)
        if extra:
            bits.append("timbre of " + ", ".join(extra[:12]))
        if not unique:
            top = hits[0].record
            bits.append(f"in the style of {top.name} from {_pack_hint(top.pack)}")
    if unique:
        bits.append(
            "heavily redesigned original synthesized game sfx, "
            "transformed timbre and envelope, not a commercial pack preview, "
            "not a lightly edited sample"
        )
        if archetype == "bodily":
            bits.append(
                "abstracted bodily gas / waste event for a game, "
                "new character and pitch contour, tasteful not crude comedy sting"
            )
    bits.append("clean, punchy, game-ready, no music vocals, stereo")
    return ", ".join(b for b in bits if b)


def _mutate_reference_dna(
    arr: np.ndarray,
    sr: int,
    *,
    amount: float = 0.72,
    seed: int = 0,
) -> np.ndarray:
    """Scramble pack-mix DNA before SA3 so init_audio is already non-shippable.

    amount 0 = identity; 1 = aggressive pitch/time/EQ/waveshape/noise. This is
    the licensed modify/mix step — the model then rewrites further.
    """
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    x = np.asarray(arr, dtype=np.float32)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    a = float(np.clip(amount, 0.0, 1.0))
    if a < 1e-3 or x.size == 0:
        return x

    # Pitch via resample (semitones ±).
    semis = float(rng.uniform(-5.5, 5.5) * a)
    rate = float(2.0 ** (semis / 12.0))
    n = x.shape[0]
    new_n = max(16, int(round(n / rate)))
    t_old = np.linspace(0.0, 1.0, n, dtype=np.float64)
    t_new = np.linspace(0.0, 1.0, new_n, dtype=np.float64)
    pitched = np.stack(
        [np.interp(t_new, t_old, x[:, c]).astype(np.float32) for c in range(x.shape[1])],
        axis=1,
    )

    # Time pad/crop back to original length (also warps envelope).
    if pitched.shape[0] >= n:
        start = int(rng.integers(0, max(1, pitched.shape[0] - n + 1)))
        y = pitched[start : start + n]
    else:
        y = np.pad(pitched, ((0, n - pitched.shape[0]), (0, 0)))

    # Spectral tilt: gentle 1st-order shelf via cumulative EMA.
    tilt = float(rng.uniform(-0.55, 0.55) * a)
    alpha = float(np.clip(0.08 + 0.35 * abs(tilt), 0.05, 0.45))
    for c in range(y.shape[1]):
        z = y[:, c].copy()
        acc = 0.0
        out = np.empty_like(z)
        for i, s in enumerate(z):
            acc = alpha * s + (1.0 - alpha) * acc
            out[i] = s + tilt * (s - acc)
        y[:, c] = out

    # Soft waveshape for harmonic character change.
    drive = 1.0 + 1.8 * a * float(rng.uniform(0.4, 1.0))
    y = np.tanh(y * drive).astype(np.float32)

    # Reverse a random middle slice and crossfade it back (structure break).
    if a > 0.35 and n > sr // 4:
        w = int(rng.integers(n // 8, max(n // 8 + 1, n // 3)))
        i0 = int(rng.integers(0, max(1, n - w)))
        frag = y[i0 : i0 + w][::-1].copy()
        fade = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(-1, 1)
        mix = 0.35 + 0.45 * a
        y[i0 : i0 + w] = y[i0 : i0 + w] * (1.0 - mix * fade) + frag * (mix * fade)

    # Seeded noise bed so SA3 cannot cling to silence gaps in the pack mix.
    noise = rng.normal(0.0, 0.012 * a, size=y.shape).astype(np.float32)
    y = y + noise

    peak = float(np.max(np.abs(y)))
    if peak > 1e-8:
        y = (y / peak) * 0.95
    return y


def _unique_post_morph(arr: np.ndarray, sr: int, *, seed: int = 0) -> np.ndarray:
    """Second-pass DSP after SA3 — final distance from pack DNA without envelope match."""
    rng = np.random.default_rng((int(seed) ^ 0xA5A5) & 0x7FFFFFFF)
    x = np.asarray(arr, dtype=np.float32)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    n = x.shape[0]
    if n < 64:
        return x

    # Micro pitch (±1.5 st) so even a stubborn SA3 pass drifts.
    semis = float(rng.uniform(-1.5, 1.5))
    rate = float(2.0 ** (semis / 12.0))
    new_n = max(16, int(round(n / rate)))
    t_old = np.linspace(0.0, 1.0, n, dtype=np.float64)
    t_new = np.linspace(0.0, 1.0, new_n, dtype=np.float64)
    y = np.stack(
        [np.interp(t_new, t_old, x[:, c]).astype(np.float32) for c in range(x.shape[1])],
        axis=1,
    )
    if y.shape[0] >= n:
        y = y[:n]
    else:
        y = np.pad(y, ((0, n - y.shape[0]), (0, 0)))

    # One-pole highpass (kill shared rumble fingerprint).
    hp = float(rng.uniform(0.02, 0.08))
    for c in range(y.shape[1]):
        z = y[:, c]
        out = np.empty_like(z)
        prev_x = prev_y = 0.0
        for i, s in enumerate(z):
            prev_y = hp * (prev_y + s - prev_x)
            prev_x = float(s)
            out[i] = prev_y
        y[:, c] = out

    # Soft bit of odd harmonic.
    y = (y + 0.18 * np.tanh(y * 2.4)).astype(np.float32)
    return y


def _copy_corr(generated: np.ndarray, reference: np.ndarray) -> float:
    """Absolute cosine similarity of downsampled mono clips (0 = distinct)."""

    def _mono(x: np.ndarray) -> np.ndarray:
        y = np.asarray(x, dtype=np.float32)
        if y.ndim > 1:
            y = y.mean(axis=1)
        if y.size > 24000:
            y = y[:: max(1, y.size // 12000)]
        y = y - float(y.mean())
        n = float(np.linalg.norm(y) + 1e-8)
        return y / n

    a = _mono(generated)
    b = _mono(reference)
    n = min(a.size, b.size)
    if n < 64:
        return 0.0
    return float(np.abs(np.dot(a[:n], b[:n])))


def _pack_hint(pack: str) -> str:
    from audio_asset_library import _pack_stem

    return _pack_stem(pack) or pack


def _fit_duration(arr: np.ndarray, sr: int, seconds: float) -> np.ndarray:
    n = max(1, int(seconds * sr))
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    if arr.shape[0] >= n:
        return arr[:n]
    return np.pad(arr, ((0, n - arr.shape[0]), (0, 0)))


def _postprocess(arr: np.ndarray, reference: Optional[np.ndarray] = None) -> np.ndarray:
    """Peak normalize, light limiter, optional RMS envelope match to the mix."""
    x = np.asarray(arr, dtype=np.float32)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    if reference is not None:
        x = _match_envelope(x, np.asarray(reference, dtype=np.float32))
    peak = float(np.max(np.abs(x)))
    if peak > 1e-8:
        x = x / peak
    # Soft limiter
    x = np.tanh(x * 1.15).astype(np.float32)
    peak = float(np.max(np.abs(x)))
    if peak > 1e-8:
        x = (x / peak) * 0.97
    return x


def _match_envelope(generated: np.ndarray, reference: np.ndarray, win: int = 512) -> np.ndarray:
    n = min(generated.shape[0], reference.shape[0])
    if n < win * 2:
        return generated
    g = generated[:n]
    r = reference[:n]
    if r.ndim == 1:
        r = r.reshape(-1, 1)
    if r.shape[1] != g.shape[1]:
        r = np.repeat(r.mean(axis=1, keepdims=True), g.shape[1], axis=1)
    out = g.copy()
    for c in range(g.shape[1]):
        ge = _rms_env(g[:, c], win)
        re = _rms_env(r[:, c], win)
        scale = re / (ge + 1e-4)
        scale = np.clip(scale, 0.35, 2.8)
        # upsample envelope to sample rate
        env = np.interp(np.arange(n), np.linspace(0, n - 1, scale.size), scale).astype(np.float32)
        out[:, c] = g[:, c] * env
    return out


def _rms_env(x: np.ndarray, win: int) -> np.ndarray:
    pad = (-x.size) % win
    if pad:
        x = np.pad(x, (0, pad))
    frames = x.reshape(-1, win)
    return np.sqrt(np.mean(frames * frames, axis=1) + 1e-12).astype(np.float32)


def _read_wav(path: Path) -> Tuple[np.ndarray, int]:
    import soundfile as sf

    arr, sr = sf.read(str(path), dtype="float32", always_2d=True)
    return np.asarray(arr, dtype=np.float32), int(sr)


def _write_wav(path: Path, arr: np.ndarray, sr: int) -> None:
    import soundfile as sf

    path = Path(path)
    if path.suffix.lower() != ".wav":
        path = path.with_suffix(".wav")
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), arr, int(sr))


def _print_hits(hits: Sequence[RetrievalHit]) -> None:
    if not hits:
        print("(no hits — ingest the library first)")
        return
    for hit in hits:
        rec = hit.record
        print(f"{hit.score:6.3f}  {hit.via:14}  [{','.join(rec.archetypes) or '-':12}]  {rec.label()}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Shared asset-aware audio pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="Library + Stable Audio probe")

    p_ing = sub.add_parser("ingest", help="Index D:\\assets\\audio (zips + loose files)")
    p_ing.add_argument("--src", default="", help="Library root (default: D:\\assets\\audio)")
    p_ing.add_argument("--fast", action="store_true", help="Tags + spectral only (no CLAP/Whisper)")
    p_ing.add_argument("--no-clap", action="store_true")
    p_ing.add_argument("--no-whisper", action="store_true")
    p_ing.add_argument("--pack", default="", help="Substring filter on zip name")
    p_ing.add_argument("--limit", type=int, default=0)

    p_clap = sub.add_parser("backfill-clap", help="Build CLAP embeddings for indexed clips")
    p_clap.add_argument("--src", default="", help="Library root (default: D:\\assets\\audio)")
    p_clap.add_argument("--no-resume", action="store_true", help="Rebuild CLAP from scratch")
    p_clap.add_argument("--save-every", type=int, default=100)

    p_rt = sub.add_parser("rebuild-tags", help="Re-embed tag vectors after the tag embedder changes")
    p_rt.add_argument("--src", default="", help="Library root (default: D:\\assets\\audio)")

    p_s = sub.add_parser("search", help="Retrieve similar assets")
    p_s.add_argument("--query", "-q", default="")
    p_s.add_argument("--audio", default="", help="Query by example wav")
    p_s.add_argument("--k", type=int, default=8)
    p_s.add_argument("--archetype", default="")
    p_s.add_argument("--tags", default="")
    p_s.add_argument("--direct-only", action="store_true", help="Only direct + own tier clips")

    p_g = sub.add_parser("generate", help="Generate a new clip from library DNA")
    p_g.add_argument("--prompt", "-p", required=True)
    p_g.add_argument("--out", "-o", required=True)
    p_g.add_argument("--duration", type=float, default=2.5)
    p_g.add_argument("--k", type=int, default=4)
    p_g.add_argument("--strength", type=float, default=0.65, help="0=text only, 1=stay on refs")
    p_g.add_argument("--archetype", default="", help="laser | ui | alien | mech | ship | magic | ...")
    p_g.add_argument("--tags", default="")
    p_g.add_argument("--seed", type=int, default=None)
    p_g.add_argument("--model", default="")
    p_g.add_argument("--no-refs", action="store_true")
    p_g.add_argument("--example", default="")
    p_g.add_argument("--engine", default="auto", choices=("auto", "stable-audio", "library"))
    p_g.add_argument(
        "--close-copy",
        action="store_true",
        help="Opt out of unique mode (only shippable with --direct-only)",
    )
    p_g.add_argument(
        "--direct-only",
        action="store_true",
        help="Only reference direct + own tier clips (Function Loops bt25, Tao & Sound, made/)",
    )
    p_g.add_argument("--keep", action="store_true", help="Save shippable output to made/ as an own-tier clip")

    p_c = sub.add_parser("check", help="Flag sound files that are near copies of library clips")
    p_c.add_argument("paths", nargs="+", help="Files or folders (e.g. a mod's Sound dir)")
    p_c.add_argument("--k", type=int, default=5)

    p_b = sub.add_parser("blend", help="Mix two catalogued assets")
    p_b.add_argument("--a", required=True, help="Asset id")
    p_b.add_argument("--b", required=True)
    p_b.add_argument("--out", "-o", required=True)
    p_b.add_argument("--alpha", type=float, default=0.5)
    p_b.add_argument("--duration", type=float, default=0.0)
    p_b.add_argument("--keep", action="store_true", help="Save shippable output to made/ as an own-tier clip")

    args = parser.parse_args(argv)

    if args.cmd == "status":
        info = status()
        print(json.dumps(info, indent=2))
        return 0 if info.get("library_exists") else 1

    if args.cmd == "ingest":
        src = Path(args.src) if args.src else None
        report = ingest(
            src=src,
            fast=bool(args.fast),
            clap=not args.no_clap and not args.fast,
            whisper=not args.no_whisper and not args.fast,
            pack=args.pack,
            limit=args.limit,
        )
        print(json.dumps(report, indent=2))
        return 0 if report.get("total") else 1

    if args.cmd == "backfill-clap":
        src = Path(args.src) if args.src else None
        report = backfill_clap(
            src=src,
            resume=not args.no_resume,
            save_every=max(1, int(args.save_every)),
        )
        print(json.dumps(report, indent=2))
        return 0 if report.get("clap") else 1

    if args.cmd == "rebuild-tags":
        report = rebuild_tags(src=Path(args.src) if args.src else None)
        print(json.dumps(report, indent=2))
        return 0 if report.get("rebuilt") else 1

    if args.cmd == "search":
        tag_list = [t.strip() for t in args.tags.split(",") if t.strip()]
        hits = search(
            args.query,
            audio=Path(args.audio) if args.audio else None,
            k=args.k,
            archetype=args.archetype,
            tags=tag_list or None,
            license=("direct", "own") if args.direct_only else "",
        )
        _print_hits(hits)
        return 0 if hits else 1

    if args.cmd == "generate":
        tag_list = [t.strip() for t in args.tags.split(",") if t.strip()]
        generate_audio(
            args.prompt,
            Path(args.out),
            duration=args.duration,
            k=args.k,
            strength=args.strength,
            archetype=args.archetype,
            tags=tag_list or None,
            seed=args.seed,
            model_name=args.model or None,
            no_refs=bool(args.no_refs),
            example=Path(args.example) if args.example else None,
            engine=args.engine,
            unique=not bool(args.close_copy),
            direct_only=bool(args.direct_only),
            keep=bool(args.keep),
        )
        return 0

    if args.cmd == "check":
        rows = check_files([Path(p) for p in args.paths], k=args.k)
        for row in rows:
            if row["ok"] is None:
                print(f"  skip  {row['file']}: {row['error']}")
            elif row["ok"]:
                print(f"  ok    {row['source_corr']:.3f}  {row['file']}")
            else:
                print(f"  COPY  {row['source_corr']:.3f}  {row['file']}  <- {row['closest']}")
        return 0 if all(row["ok"] is not False for row in rows) else 1

    if args.cmd == "blend":
        blend_assets(
            args.a, args.b, Path(args.out), alpha=args.alpha, duration=args.duration, keep=bool(args.keep)
        )
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
