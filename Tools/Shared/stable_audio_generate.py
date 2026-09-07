#!/usr/bin/env python3
"""
Stable Audio 3 text-to-audio for AAMT / Transcendence asset SFX.

Uses Stability's stable-audio-3 library (not Stable Audio Open / diffusers).
Default model: medium (stabilityai/stable-audio-3-medium).
For short game SFX on limited VRAM, prefer small-sfx.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# Prefer the cloned SA3 install
def _sa3_root() -> Path:
    try:
        from tool_paths import stable_audio_dir

        return stable_audio_dir()
    except Exception:
        return Path(os.environ.get("AAMT_STABLE_AUDIO_DIR", r"E:\tools\stable-audio"))


_SA3_ROOT = _sa3_root()
_REPO = _SA3_ROOT / "stable-audio-3"
if _REPO.is_dir():
    sys.path.insert(0, str(_REPO))

# Weights on E: — do NOT set HF_HOME (that hides the login token under %USERPROFILE%)
_HF_HUB = _SA3_ROOT / "hub"
_HF_HUB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(_HF_HUB))
os.environ.setdefault("HF_HUB_CACHE", str(_HF_HUB))

try:
    _shared = Path(__file__).resolve().parent
    if str(_shared) not in sys.path:
        sys.path.insert(0, str(_shared))
    from hf_token_switch import use_media_token

    use_media_token(quiet=True)
except Exception:
    pass

DEFAULT_MODEL = os.environ.get("AAMT_STABLE_AUDIO_MODEL", "medium")
# Short SFX defaults for Transcendence / game assets
DEFAULT_SECONDS = 4.0
MODEL_ALIASES = {
    "medium": "medium",
    "stabilityai/stable-audio-3-medium": "medium",
    "small-sfx": "small-sfx",
    "stabilityai/stable-audio-3-small-sfx": "small-sfx",
    "small-music": "small-music",
    "stabilityai/stable-audio-3-small-music": "small-music",
}


def _normalize_model(name: str) -> str:
    key = (name or "medium").strip()
    return MODEL_ALIASES.get(key, key)


def _save_wav(audio, path: Path, sample_rate: int = 44100) -> Path:
    import torch
    import torchaudio

    path = Path(path)
    if path.suffix.lower() != ".wav":
        path = path.with_suffix(".wav")
    path.parent.mkdir(parents=True, exist_ok=True)

    # SA3 typically returns [batch, channels, samples] or [channels, samples]
    if hasattr(audio, "detach"):
        wav = audio.detach().float().cpu()
    else:
        wav = torch.as_tensor(audio).float()

    if wav.ndim == 3:
        wav = wav[0]
    if wav.ndim == 1:
        wav = wav.unsqueeze(0)

    peak = wav.abs().max().clamp_min(1e-8)
    wav = (wav / peak).clamp(-1, 1)
    torchaudio.save(str(path), wav, sample_rate)
    return path


def generate(
    prompt: str,
    output: Path,
    *,
    model_name: str = DEFAULT_MODEL,
    seconds: float = DEFAULT_SECONDS,
    steps: int | None = None,
    seed: int | None = None,
    negative_prompt: str = "",
    device: str | None = None,
) -> Path:
    from stable_audio_3 import StableAudioModel

    model_id = _normalize_model(model_name)
    print(f"Loading Stable Audio 3 model: {model_id} ...")
    load_kwargs = {}
    if device:
        load_kwargs["device"] = device
    model = StableAudioModel.from_pretrained(model_id, **load_kwargs)

    gen_kwargs = {
        "prompt": prompt,
        "duration": float(seconds),
    }
    if negative_prompt:
        # Some builds accept negative_prompt; ignore if not supported
        gen_kwargs["negative_prompt"] = negative_prompt
    if steps is not None:
        gen_kwargs["steps"] = int(steps)
    if seed is not None:
        gen_kwargs["seed"] = int(seed)

    print(f"Generating {seconds}s SFX: {prompt!r}")
    try:
        audio = model.generate(**gen_kwargs)
    except TypeError:
        # Older/narrower signature
        for drop in ("negative_prompt", "steps", "seed"):
            gen_kwargs.pop(drop, None)
        audio = model.generate(prompt=prompt, duration=float(seconds))

    sample_rate = getattr(model, "sample_rate", None) or 44100
    out = _save_wav(audio, Path(output), sample_rate=sample_rate)
    print(f"Wrote: {out} ({sample_rate} Hz)")

    meta = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "model": model_id,
        "hf_repo": f"stabilityai/stable-audio-3-{model_id}" if not model_id.startswith("stabilityai/") else model_id,
        "seconds": seconds,
        "steps": steps,
        "seed": seed,
        "sample_rate": sample_rate,
        "output": str(out),
    }
    out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate Transcendence/game SFX with Stable Audio 3"
    )
    parser.add_argument("--prompt", "-p", default="", help="Text prompt for the sound effect")
    parser.add_argument("--output", "-o", default="", help="Output .wav path")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="medium | small-sfx | small-music (default: medium)",
    )
    parser.add_argument("--seconds", type=float, default=DEFAULT_SECONDS)
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--negative-prompt", default="Low quality, muffled, distorted, silence")
    parser.add_argument("--device", default=None, help="cuda | cpu (optional)")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)

    if args.check_only:
        try:
            import torch
            from stable_audio_3 import StableAudioModel  # noqa: F401

            print(
                f"torch={torch.__version__} cuda={torch.cuda.is_available()} "
                f"stable_audio_3=OK model_default={_normalize_model(DEFAULT_MODEL)}"
            )
            if torch.cuda.is_available():
                print(f"gpu={torch.cuda.get_device_name(0)}")
            try:
                import flash_attn

                print(f"flash_attn={flash_attn.__version__}")
            except Exception:
                print("flash_attn=MISSING (required for medium on CUDA; small-sfx works without it)")
            return 0
        except Exception as e:
            print(f"CHECK FAILED: {e}", file=sys.stderr)
            print(
                "Run Setup-StableAudio.ps1 (clones Stability-AI/stable-audio-3).",
                file=sys.stderr,
            )
            return 1

    if not args.prompt or not args.output:
        parser.error("--prompt and --output are required unless --check-only")

    try:
        generate(
            args.prompt,
            Path(args.output),
            model_name=args.model,
            seconds=args.seconds,
            steps=args.steps,
            seed=args.seed,
            negative_prompt=args.negative_prompt,
            device=args.device,
        )
        return 0
    except Exception as e:
        msg = str(e).lower()
        print(f"ERROR: {e}", file=sys.stderr)
        if "401" in msg or "403" in msg or "gated" in msg or "restricted" in msg:
            print(
                "Accept the license and ensure your HF token can read the model:\n"
                "  https://huggingface.co/stabilityai/stable-audio-3-medium\n"
                "  (and small-sfx if you use --model small-sfx)\n"
                "  Then: hf auth login",
                file=sys.stderr,
            )
        if "flash" in msg or "flash_attn" in msg:
            print(
                "Medium needs Flash Attention 2. On RTX 2080 Ti that can be hard;\n"
                "for game SFX try: --model small-sfx",
                file=sys.stderr,
            )
        if "out of memory" in msg or "oom" in msg:
            print(
                "VRAM OOM: stop the SD image server, shorten --seconds,\n"
                "or use --model small-sfx",
                file=sys.stderr,
            )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
