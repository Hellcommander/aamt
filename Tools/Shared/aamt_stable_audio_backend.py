#!/usr/bin/env python3
"""
Shared Stable Audio 3 backend for AAMT game-asset audio producers.

Used by Transcendence / Qud / Elin / Terraria / Starbound generators.
Prefers SA3 when installed; callers keep procedural fallbacks.
Caches the model once per process (do not multithread SA3).

Default placement is hybrid: weights load into system RAM first, then
DiT (and usually the autoencoder) move to GPU. The text conditioner (T5)
stays in RAM. Set AAMT_STABLE_AUDIO_OFFLOAD_AE=1 to keep the autoencoder
in RAM as well (encode/decode bounce through CPU). GPU VRAM is capped so
the desktop keeps headroom.
Override with AAMT_STABLE_AUDIO_DEVICE=cuda|cpu|hybrid,
AAMT_STABLE_AUDIO_GPU_FRACTION=0.0-1.0, AAMT_STABLE_AUDIO_OFFLOAD_AE=0|1.
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Prefer expandable CUDA segments so peaks don't permanently fragment VRAM.
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

def _sa3_root() -> Path:
    try:
        from tool_paths import stable_audio_dir

        return stable_audio_dir()
    except Exception:
        return Path(os.environ.get("AAMT_STABLE_AUDIO_DIR", r"E:\tools\stable-audio"))


_SA3_ROOT = _sa3_root()
_REPO = _SA3_ROOT / "stable-audio-3"
if _REPO.is_dir() and str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

# Weights on E: — do NOT set HF_HOME (that hides the login token under %USERPROFILE%)
_HF_HUB = _SA3_ROOT / "hub"
_HF_HUB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(_HF_HUB))
os.environ.setdefault("HF_HUB_CACHE", str(_HF_HUB))

# Auto-select media download token (SD3.5 Token) when available
try:
    _shared_dir = Path(__file__).resolve().parent
    if str(_shared_dir) not in sys.path:
        sys.path.insert(0, str(_shared_dir))
    from hf_token_switch import use_media_token

    use_media_token(quiet=True)
except Exception:
    pass

DEFAULT_MODEL = os.environ.get("AAMT_STABLE_AUDIO_MODEL", "medium")
DEFAULT_ENGINE = os.environ.get("AAMT_AUDIO_ENGINE", "auto")  # auto | stable-audio | procedural
# hybrid (default) | cuda | gpu | cpu | mps
DEFAULT_DEVICE = os.environ.get("AAMT_STABLE_AUDIO_DEVICE", "hybrid").strip().lower() or "hybrid"
# Cap process VRAM so hybrid leaves headroom for the desktop / other apps.
DEFAULT_GPU_FRACTION = float(os.environ.get("AAMT_STABLE_AUDIO_GPU_FRACTION", "0.60"))
# Keep the autoencoder in RAM (CPU encode/decode). Helps medium fit an 11 GB card.
DEFAULT_OFFLOAD_AE = os.environ.get("AAMT_STABLE_AUDIO_OFFLOAD_AE", "0").strip().lower() in (
	"1",
	"true",
	"yes",
	"on",
)

_MODEL = None
_MODEL_ID: Optional[str] = None
_MODEL_MODE: Optional[str] = None
_AVAILABLE: Optional[bool] = None
_LAST_ERROR: str = ""


def resolve_engine(requested: Optional[str] = None) -> str:
	"""Return 'stable-audio' or 'procedural'."""
	eng = (requested or DEFAULT_ENGINE or "auto").strip().lower()
	if eng in ("procedural", "proc", "synth"):
		return "procedural"
	if eng in ("stable-audio", "sa3", "stableaudio", "ai"):
		return "stable-audio" if is_available() else "procedural"
	# auto
	return "stable-audio" if is_available() else "procedural"


def is_available() -> bool:
	global _AVAILABLE, _LAST_ERROR
	if _AVAILABLE is not None:
		return _AVAILABLE
	try:
		from stable_audio_3 import StableAudioModel  # noqa: F401

		_AVAILABLE = True
		return True
	except Exception as e:
		_LAST_ERROR = str(e)
		_AVAILABLE = False
		return False


def last_error() -> str:
	return _LAST_ERROR


def _resolve_placement(requested: Optional[str] = None) -> str:
	"""Return hybrid | cuda | cpu | mps."""
	raw = (requested or DEFAULT_DEVICE or "hybrid").strip().lower()
	if raw in ("gpu", "full", "full-gpu"):
		raw = "cuda"
	if raw in ("hybrid", "offload", "medvram", "auto"):
		try:
			import torch

			return "hybrid" if torch.cuda.is_available() else "cpu"
		except Exception:
			return "cpu"
	if raw in ("cuda", "cpu", "mps"):
		if raw == "cuda":
			try:
				import torch

				if not torch.cuda.is_available():
					return "cpu"
			except Exception:
				return "cpu"
		return raw
	return "hybrid"


def _move_tree(obj: Any, device: str) -> Any:
	import torch

	if isinstance(obj, torch.Tensor):
		return obj.to(device, non_blocking=(device == "cuda"))
	if isinstance(obj, dict):
		return {k: _move_tree(v, device) for k, v in obj.items()}
	if isinstance(obj, list):
		return [_move_tree(v, device) for v in obj]
	if isinstance(obj, tuple):
		return tuple(_move_tree(v, device) for v in obj)
	return obj


def _cap_gpu_fraction(fraction: float) -> None:
	try:
		import torch

		if not torch.cuda.is_available():
			return
		frac = float(max(0.15, min(1.0, fraction)))
		# Leave a slice of VRAM for the OS / compositor / other tools.
		torch.cuda.set_per_process_memory_fraction(frac, device=0)
		print(f"[SA3] GPU VRAM cap {frac:.0%} (AAMT_STABLE_AUDIO_GPU_FRACTION)", flush=True)
	except Exception as exc:
		print(f"[SA3] GPU VRAM cap skipped ({exc})", flush=True)


def _clear_cuda() -> None:
	try:
		import gc
		import torch

		gc.collect()
		if torch.cuda.is_available():
			torch.cuda.empty_cache()
	except Exception:
		pass


def _module_to(module: Any, device: str) -> bool:
	"""Move a module; on OOM pull it back to CPU and return False."""
	if module is None:
		return False
	try:
		module.to(device)
		return True
	except Exception as exc:
		print(f"[SA3] {type(module).__name__} → {device} failed ({exc})", flush=True)
		try:
			module.to("cpu")
		except Exception:
			pass
		_clear_cuda()
		return False


def _pin_conditioner_cpu(cond: Any, gpu_device: str) -> None:
	"""T5 stays in RAM; embeddings ship to the DiT device after encode."""
	cond.to("cpu")
	for module in cond.modules():
		# Stop T5GemmaConditioner from yanking itself onto CUDA on first forward.
		if hasattr(module, "_device_initialized"):
			module._device_initialized = True

	original_forward = cond.forward

	def _hybrid_forward(batch_metadata, device=None):
		out = original_forward(batch_metadata, "cpu")
		target = gpu_device if device is None else str(device)
		if target != "cpu":
			out = _move_tree(out, target)
		return out

	cond.forward = _hybrid_forward  # type: ignore[method-assign]


def _bounce_ae_through_ram(pre: Any, gpu_device: str) -> None:
	"""AE lives in RAM; encode/decode bounce tensors CPU ↔ GPU."""
	import torch

	if pre is None or getattr(pre, "_aamt_ae_ram", False):
		return
	orig_encode = pre.encode
	orig_decode = pre.decode

	def _to_ae(x: Any) -> Any:
		if not isinstance(x, torch.Tensor):
			return x
		p = next(pre.parameters())
		return x.to(device=p.device, dtype=p.dtype)

	def encode(*args: Any, **kwargs: Any):
		args = tuple(_to_ae(a) for a in args)
		kwargs = {k: _to_ae(v) for k, v in kwargs.items()}
		out = orig_encode(*args, **kwargs)
		if isinstance(out, torch.Tensor) and gpu_device != "cpu":
			return out.to(gpu_device, non_blocking=True)
		return out

	def decode(*args: Any, **kwargs: Any):
		args = tuple(_to_ae(a) for a in args)
		kwargs = {k: _to_ae(v) for k, v in kwargs.items()}
		out = orig_decode(*args, **kwargs)
		if isinstance(out, torch.Tensor) and gpu_device != "cpu":
			return out.to(gpu_device, non_blocking=True)
		return out

	pre.encode = encode  # type: ignore[method-assign]
	pre.decode = decode  # type: ignore[method-assign]
	pre._aamt_ae_ram = True


def _apply_hybrid_offload(sa_model: Any, gpu_device: str = "cuda") -> None:
	"""Weights start in RAM. DiT (and AE unless offloaded) go to GPU; T5 stays in RAM."""
	import torch

	if getattr(sa_model, "_aamt_hybrid", False):
		return

	inner = getattr(sa_model, "model", None)
	dit = getattr(inner, "model", None) if inner is not None else None
	pre = getattr(inner, "pretransform", None) if inner is not None else None
	cond = getattr(inner, "conditioner", None) if inner is not None else None

	want_ae_ram = DEFAULT_OFFLOAD_AE
	ae_on_gpu = False
	dit_on_gpu = False

	if dit is not None:
		dit_on_gpu = _module_to(dit, gpu_device)
	if pre is not None and not want_ae_ram:
		ae_on_gpu = _module_to(pre, gpu_device)
		if not ae_on_gpu:
			want_ae_ram = True
			print("[SA3] autoencoder did not fit on GPU — keeping it in RAM", flush=True)
	if pre is not None and want_ae_ram:
		_module_to(pre, "cpu")
		_bounce_ae_through_ram(pre, gpu_device if dit_on_gpu else "cpu")
	if cond is not None:
		_pin_conditioner_cpu(cond, gpu_device if dit_on_gpu else "cpu")

	sa_model._aamt_hybrid = True
	sa_model.device = gpu_device if dit_on_gpu else "cpu"
	place = []
	place.append("DiT on GPU" if dit_on_gpu else "DiT on CPU/RAM")
	place.append("AE on CPU/RAM" if want_ae_ram or not ae_on_gpu else "AE on GPU")
	place.append("T5 conditioner on CPU/RAM")
	print(f"[SA3] hybrid placement: {', '.join(place)}", flush=True)
	if torch.cuda.is_available():
		torch.cuda.empty_cache()


def get_model(model_name: Optional[str] = None, device: Optional[str] = None):
	"""Lazy-load and cache StableAudioModel (hybrid GPU+RAM by default)."""
	global _MODEL, _MODEL_ID, _MODEL_MODE, _LAST_ERROR
	mid = (model_name or DEFAULT_MODEL or "medium").strip()
	aliases = {
		"stabilityai/stable-audio-3-medium": "medium",
		"stabilityai/stable-audio-3-small-sfx": "small-sfx",
		"stabilityai/stable-audio-3-small-music": "small-music",
	}
	mid = aliases.get(mid, mid)
	mode = _resolve_placement(device)

	if _MODEL is not None and _MODEL_ID == mid and _MODEL_MODE == mode:
		return _MODEL

	if _MODEL is not None:
		_MODEL = None
		_MODEL_ID = None
		_MODEL_MODE = None
		_clear_cuda()

	from stable_audio_3 import StableAudioModel

	load_device = "cpu" if mode == "cpu" else ("mps" if mode == "mps" else "cuda")
	if mode == "cpu" and mid in ("medium", "medium-base"):
		print(
			f"[SA3] device=cpu — using small-sfx instead of '{mid}' (medium is GPU-oriented).",
			flush=True,
		)
		mid = "small-sfx"

	if load_device == "cuda":
		_cap_gpu_fraction(DEFAULT_GPU_FRACTION)

	# Hybrid loads into RAM first so T5 never occupies VRAM, then places DiT/AE.
	load_on = "cpu" if mode == "hybrid" else load_device
	print(f"[SA3] Loading model '{mid}' on {load_on} (mode={mode})...", flush=True)
	try:
		_MODEL = StableAudioModel.from_pretrained(mid, device=load_on)
		_MODEL_ID = mid
		_MODEL_MODE = mode
		if mode == "hybrid":
			_apply_hybrid_offload(_MODEL, gpu_device=load_device)
		return _MODEL
	except Exception as e:
		_LAST_ERROR = str(e)
		# Medium often needs flash-attn / more VRAM; fall back to small-sfx for game SFX
		if mid == "medium":
			print(f"[SA3] medium failed ({e}); trying small-sfx...")
			_MODEL = None
			_clear_cuda()
			try:
				sfx_on = "cpu" if mode == "hybrid" else load_device
				_MODEL = StableAudioModel.from_pretrained("small-sfx", device=sfx_on)
				_MODEL_ID = "small-sfx"
				_MODEL_MODE = mode
				if mode == "hybrid":
					_apply_hybrid_offload(_MODEL, gpu_device=load_device)
				return _MODEL
			except Exception as e2:
				_LAST_ERROR = str(e2)
				raise
		raise


def build_prompt(
    *,
    name: str = "",
    description: str = "",
    sound_type: str = "",
    channel: str = "",
    game: str = "",
    extra: str = "",
) -> str:
    """Build a Stable Audio prompt tuned for short game SFX."""
    bits = []
    if game:
        bits.append(f"{game} game sound effect")
    else:
        bits.append("high quality game sound effect")
    if name:
        bits.append(name)
    if sound_type:
        bits.append(f"{sound_type} sound")
    if channel:
        channel_hints = {
            "em": "electromagnetic whale song, ethereal sci-fi chirps, space vacuum resonance",
            "plasma": "ionized plasma harmonics, aurora-like shimmer, magnetosonic waves",
            "acoustic": "muffled pressure wave in nebula gas, deep boom, underwater-like",
            "mechanical": "metal hull impact, tactile rumble, ship structure vibration",
        }
        bits.append(channel_hints.get(channel.lower(), channel))
    if description:
        bits.append(description)
    if extra:
        bits.append(extra)
    bits.append("clean, punchy, game-ready, no music vocals, stereo")
    # De-dupe empties
    text = ", ".join(b.strip() for b in bits if b and str(b).strip())
    return text


def _tensor_to_numpy(audio) -> "np.ndarray":
    import numpy as np
    import torch

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
    # soundfile wants (samples, channels)
    arr = wav.numpy().T
    return np.asarray(arr, dtype=np.float32)


def _to_init_audio(audio, sample_rate: int):
    """Pack numpy/tensor audio as SA3 init_audio: (sr, [channels, samples])."""
    import torch

    if hasattr(audio, "detach"):
        wav = audio.detach().float().cpu()
    else:
        wav = torch.as_tensor(audio).float()
    if wav.ndim == 3:
        wav = wav[0]
    if wav.ndim == 1:
        wav = wav.unsqueeze(0)
    elif wav.shape[0] > wav.shape[-1] and wav.shape[-1] <= 8:
        # [samples, channels] -> [channels, samples]
        wav = wav.T.contiguous()
    return int(sample_rate), wav


def generate_array(
    prompt: str,
    *,
    duration: float = 3.0,
    seed: Optional[int] = None,
    model_name: Optional[str] = None,
    negative_prompt: str = "music, singing, speech, low quality, muffled, distortion, silence",
    init_audio: Optional[Tuple[int, Any]] = None,
    init_noise_level: float = 1.0,
    steps: Optional[int] = None,
) -> Tuple["np.ndarray", int]:
    """
    Generate audio samples.
    Returns (array shaped [samples, channels], sample_rate).

    init_audio is (sample_rate, waveform) where waveform is [channels, samples]
    or [samples, channels]. init_noise_level 1.0 = ignore the reference (txt2audio);
    lower values keep more of the reference's spectral DNA.
    """
    model = get_model(model_name)
    duration = float(max(0.25, min(duration, 120.0 if (_MODEL_ID or "").startswith("small") else 380.0)))
    kwargs: Dict[str, Any] = {
        "prompt": prompt,
        "duration": duration,
        # Lower peak VRAM on the AE decode step (hybrid default).
        "chunked_decode": True,
    }
    if seed is not None:
        kwargs["seed"] = int(seed)
    if steps is not None:
        kwargs["steps"] = int(steps)
    if init_audio is not None:
        sr0, wav0 = init_audio
        kwargs["init_audio"] = _to_init_audio(wav0, sr0)
        kwargs["init_noise_level"] = float(max(0.05, min(1.0, init_noise_level)))
    if negative_prompt:
        kwargs["negative_prompt"] = negative_prompt

    def _run():
        try:
            return model.generate(**kwargs)
        except TypeError:
            slim = {
                k: v
                for k, v in kwargs.items()
                if k
                in (
                    "prompt",
                    "duration",
                    "init_audio",
                    "init_noise_level",
                    "negative_prompt",
                    "seed",
                    "steps",
                    "chunked_decode",
                )
            }
            try:
                return model.generate(**slim)
            except TypeError:
                return model.generate(prompt=prompt, duration=duration)

    try:
        from gpu_hub import acquire_gpu
    except Exception:
        acquire_gpu = None  # type: ignore

    if acquire_gpu is not None:
        with acquire_gpu(f"SA3 {prompt[:48]}"):
            audio = _run()
    else:
        audio = _run()

    sr = int(
        getattr(model, "sample_rate", None)
        or getattr(getattr(model, "model", None), "sample_rate", None)
        or 44100
    )
    return _tensor_to_numpy(audio), sr


def generate_to_file(
    prompt: str,
    output_path: str | Path,
    *,
    duration: float = 3.0,
    seed: Optional[int] = None,
    model_name: Optional[str] = None,
    fmt: Optional[str] = None,
    init_audio: Optional[Tuple[int, Any]] = None,
    init_noise_level: float = 1.0,
    steps: Optional[int] = None,
) -> Path:
    """Generate and write WAV or OGG. Returns output path."""
    import soundfile as sf

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    arr, sr = generate_array(
        prompt,
        duration=duration,
        seed=seed,
        model_name=model_name,
        init_audio=init_audio,
        init_noise_level=init_noise_level,
        steps=steps,
    )

    suffix = (fmt or out.suffix or ".wav").lower()
    if not suffix.startswith("."):
        suffix = "." + suffix
    if out.suffix.lower() != suffix:
        out = out.with_suffix(suffix)

    if suffix == ".ogg":
        sf.write(str(out), arr, sr, format="OGG", subtype="VORBIS")
    else:
        sf.write(str(out), arr, sr)
    return out


def seed_from_text(text: str, variation: int = 0) -> int:
    h = hashlib.md5(f"{text}:{variation}".encode()).hexdigest()[:8]
    return int(h, 16) % (2**31)


def duration_from_config(cfg: Dict, default: float = 3.0) -> float:
    dur = cfg.get("duration", default)
    if isinstance(dur, dict):
        # Prefer short game-usable clips for SA3 cost/VRAM
        return float(dur.get("max", dur.get("min", default)))
    try:
        return float(dur)
    except (TypeError, ValueError):
        return default


def maybe_generate(
    *,
    engine: str = "auto",
    model_name: Optional[str] = None,
    prompt: str = "",
    duration: float = 2.0,
    seed: Optional[int] = None,
    init_audio: Optional[Tuple[int, Any]] = None,
    init_noise_level: float = 1.0,
    steps: Optional[int] = None,
) -> Optional[Tuple["np.ndarray", int]]:
    """
    Try Stable Audio 3. Returns (array, sample_rate) or None to signal procedural fallback.
    """
    if resolve_engine(engine) != "stable-audio":
        return None
    if not is_available():
        return None
    try:
        return generate_array(
            prompt,
            duration=duration,
            seed=seed,
            model_name=model_name,
            init_audio=init_audio,
            init_noise_level=init_noise_level,
            steps=steps,
        )
    except Exception as e:
        global _LAST_ERROR
        _LAST_ERROR = str(e)
        print(f"  [SA3->procedural] {e}")
        return None


# Shared path helper so sibling packages can import this module
def ensure_shared_on_path():
    shared = Path(__file__).resolve().parent
    if str(shared) not in sys.path:
        sys.path.insert(0, str(shared))
