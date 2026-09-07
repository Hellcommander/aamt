#!/usr/bin/env python3
"""Shared asset-aware audio generation stage.

Retrieve clips from the purchased/made library (D:\\assets\\audio), then either
condition Stable Audio 3 on those references or fall back to a library mix.

  python audio_pipeline.py status
  python audio_pipeline.py ingest --fast
  python audio_pipeline.py search --query "crunchy sci-fi UI click"
  python audio_pipeline.py generate --prompt "short plasma vent burst" --out vent.wav --archetype laser
"""
from __future__ import annotations

import argparse
import json
import os
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
    AudioLibrary,
    RetrievalHit,
    blend_waveforms,
    load_asset_audio,
)

DEFAULT_NEGATIVE = (
    "music, singing, speech, lyrics, low quality, muffled, distortion, silence, hiss"
)


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


def search(
    query: str = "",
    *,
    audio: Optional[Path] = None,
    k: int = 8,
    archetype: str = "",
    tags: Optional[Sequence[str]] = None,
    library: Optional[Path] = None,
) -> List[RetrievalHit]:
    lib = _lib(library)
    lib.load()
    if audio:
        wav, sr = _read_wav(Path(audio))
        return lib.search_audio(wav, sr, k=k, archetype=archetype)
    if not query:
        raise ValueError("search needs --query or --audio")
    return lib.search_text(query, k=k, archetype=archetype, tags=tags)


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
) -> Path:
    """Retrieve library DNA, generate a new clip, write WAV.

    strength 0 = text-only SA3; 1 = stay close to retrieved references.
    """
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    hits: List[RetrievalHit] = []
    init_audio = None
    used_ids: List[str] = []
    lib = _lib(library)
    if not no_refs:
        lib.load()
        if example:
            wav, sr = _read_wav(Path(example))
            hits = lib.search_audio(wav, sr, k=k, archetype=archetype)
        elif lib.records:
            hits = lib.search_text(prompt, k=k, archetype=archetype, tags=tags)
        if hits:
            mix, mix_sr, used_ids = lib.mix_references(hits, max_seconds=max(duration, 0.5), sr=48000)
            init_audio = (mix_sr, mix)
            print("[audio] refs:")
            for hit in hits:
                print(f"    {hit.score:6.3f}  {hit.via:14}  {hit.record.label()}")

    conditioned = _condition_prompt(prompt, hits, archetype=archetype)
    init_noise = 1.0 - 0.7 * float(np.clip(strength, 0.0, 1.0))
    if init_audio is None or strength <= 0:
        init_audio = None
        init_noise = 1.0

    arr: Optional[np.ndarray] = None
    sr = 48000
    engine_used = "library-mix"
    if engine != "library":
        try:
            import aamt_stable_audio_backend as backend

            result = backend.maybe_generate(
                engine=engine,
                model_name=model_name,
                prompt=conditioned,
                duration=float(duration),
                seed=seed if seed is not None else backend.seed_from_text(conditioned),
                init_audio=init_audio,
                init_noise_level=init_noise,
            )
            if result is not None:
                arr, sr = result
                engine_used = "stable-audio"
        except Exception as exc:
            print(f"[audio] SA3 failed ({exc}); using library mix")

    if arr is None:
        if init_audio is None:
            raise RuntimeError(
                "audio stage has nothing to generate from — ingest the library "
                "(python audio_pipeline.py ingest --fast) or install Stable Audio 3"
            )
        sr, arr = init_audio
        arr = _fit_duration(arr, sr, duration)
        engine_used = "library-mix"

    arr = _postprocess(arr, reference=init_audio[1] if init_audio else None)
    _write_wav(output, arr, sr)

    meta = {
        "prompt": prompt,
        "conditioned_prompt": conditioned,
        "duration": duration,
        "strength": strength,
        "init_noise_level": init_noise,
        "engine": engine_used,
        "archetype": archetype,
        "references": [
            {
                "id": h.record.id,
                "score": h.score,
                "via": h.via,
                "pack": h.record.pack,
                "inner": h.record.inner,
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
    return output


def blend_assets(
    id_a: str,
    id_b: str,
    output: Path,
    *,
    alpha: float = 0.5,
    library: Optional[Path] = None,
    duration: float = 0.0,
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
    output = Path(output)
    _write_wav(output, mixed, sr)
    print(f"[audio] blend {rec_a.label()} × {rec_b.label()} α={alpha} → {output}")
    return output


def _condition_prompt(prompt: str, hits: Sequence[RetrievalHit], *, archetype: str = "") -> str:
    bits = ["high quality game sound effect"]
    if archetype:
        bits.append(f"{archetype} sound")
    bits.append(prompt.strip())
    if hits:
        tags: List[str] = []
        for hit in hits[:3]:
            tags.extend(hit.record.tags[:6])
            tags.extend(hit.record.archetypes)
        # unique, preserve order
        seen = set()
        extra = []
        for t in tags:
            if t in seen:
                continue
            seen.add(t)
            extra.append(t)
        if extra:
            bits.append("timbre of " + ", ".join(extra[:12]))
        top = hits[0].record
        bits.append(f"in the style of {top.name} from {_pack_hint(top.pack)}")
    bits.append("clean, punchy, game-ready, no music vocals, stereo")
    return ", ".join(b for b in bits if b)


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

    p_s = sub.add_parser("search", help="Retrieve similar assets")
    p_s.add_argument("--query", "-q", default="")
    p_s.add_argument("--audio", default="", help="Query by example wav")
    p_s.add_argument("--k", type=int, default=8)
    p_s.add_argument("--archetype", default="")
    p_s.add_argument("--tags", default="")

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

    p_b = sub.add_parser("blend", help="Mix two catalogued assets")
    p_b.add_argument("--a", required=True, help="Asset id")
    p_b.add_argument("--b", required=True)
    p_b.add_argument("--out", "-o", required=True)
    p_b.add_argument("--alpha", type=float, default=0.5)
    p_b.add_argument("--duration", type=float, default=0.0)

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

    if args.cmd == "search":
        tag_list = [t.strip() for t in args.tags.split(",") if t.strip()]
        hits = search(
            args.query,
            audio=Path(args.audio) if args.audio else None,
            k=args.k,
            archetype=args.archetype,
            tags=tag_list or None,
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
        )
        return 0

    if args.cmd == "blend":
        blend_assets(args.a, args.b, Path(args.out), alpha=args.alpha, duration=args.duration)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
