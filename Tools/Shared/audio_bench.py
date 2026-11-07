"""AAMT Audio Bench: programmatic mixing, blending and sound-effect shaping, driven by a recipe.

Everything here is plain, deterministic signal processing (numpy + scipy). No model generates or touches audio. An audio
agent decides WHAT a sound needs, from `analyze()` numbers and from listening with audio_listener, and hands the bench a
recipe (a dict / JSON) saying so; the bench renders it the same way every time (every random choice comes from the
recipe's seed). That keeps the agent read-only and the processing inspectable, like a transformation tool whose knobs
are set by hand, only the knobs are the recipe.

Recipe (JSON or dict):

    {
      "seed": 7,
      "sr": 44100,
      "length": "main",                     # "main" (first layer's source), "longest", or seconds
      "sources": {"main": "hit.wav", "tex": "gravel.wav"},        # paths, or arrays when used from Python
      "layers": [
        {"source": "main", "gain_db": 0,
         "chain": [{"fx": "pitch", "semitones": -5}, {"fx": "saturate", "drive": 0.4}, {"fx": "eq30", "preset": "rumble_cut"}]},
        {"source": "tex", "gain_db": -10, "fit": "grains", "band": [1500, 9000], "follow": {"layer": 0, "amount": 1.0},
         "chain": [{"fx": "decorrelate", "spread": 0.4}]}
      ],
      "blend": {"mode": "sum"},             # or crossfade / morph between the first two layers
      "master": [{"fx": "reverb", "room": 0.3, "mix": 0.15}, {"fx": "level", "rms_db": -19, "peak_db": -1}, {"fx": "fade", "in_ms": 3, "out_ms": 120}]
    }

Every effect, its parameters, ranges and defaults are in `catalog()`; `describe()` prints the whole thing as JSON for an
agent to read. `analyze()` returns the numbers an agent needs to decide (level, crest, centroid, attack, width, band
spectrum, and correlation / tone match against references). Presets are named chains for common jobs.

Command line:
  python audio_bench.py describe                       the catalog, presets and recipe schema as JSON
  python audio_bench.py analyze <wav> [--ref <wav>]    numbers for one sound (and how it relates to a reference)
  python audio_bench.py apply <recipe.json> <out.wav>  render a recipe
  python audio_bench.py preset <name> <in.wav> <out.wav> [--seed N]
  python audio_bench.py selftest                       run every effect on a synthetic sound and check the output
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy import signal

SR = 44100
EPS = 1e-9
# ISO 266 third-octave centres: the 30 bands of a graphic equaliser.
EQ30_HZ = [20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600,
           2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000]
EQ30_PRESETS = {
    "flat": [0.0] * 30,
    "rumble_cut": [-18, -15, -12, -9, -6, -3, -1.5] + [0.0] * 23,
    "hiss_cut": [0.0] * 23 + [-1.5, -3, -5, -7, -9, -12, -15],
    "presence": [0.0] * 17 + [1, 2, 3, 3.5, 3, 2, 1] + [0.0] * 6,
    "radio": [-24, -24, -24, -24, -20, -16, -12, -8, -4, -2, 0, 1, 2, 3, 3, 3, 3, 3, 2, 1, 0, -2, -6, -12, -18, -24, -24, -24, -24, -24],
    "bass_boost": [4, 5, 6, 6, 6, 5, 4, 3, 2, 1] + [0.0] * 20,
    "hollow": [0.0] * 8 + [-2, -4, -6, -8, -8, -6, -4, -2] + [0.0] * 14,
}


# ----------------------------------------------------------------------------------------------------------------------
# basics
# ----------------------------------------------------------------------------------------------------------------------

def to_stereo(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    if x.ndim == 1:
        x = x[:, None]
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    return np.ascontiguousarray(x[:, :2])


def load(path: str, sr: int = SR) -> Tuple[np.ndarray, int]:
    import soundfile as sf

    x, file_sr = sf.read(path, always_2d=True, dtype="float32")
    x = to_stereo(x)
    if int(file_sr) != sr:
        x = resample(x, int(file_sr), sr)
    return x, sr


def save(path: str, x: np.ndarray, sr: int = SR) -> None:
    import soundfile as sf

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    sf.write(path, np.clip(to_stereo(x), -1, 1), sr, subtype="PCM_16")


def resample(x: np.ndarray, sr_from: int, sr_to: int) -> np.ndarray:
    if sr_from == sr_to:
        return x
    g = math.gcd(sr_from, sr_to)
    return signal.resample_poly(x, sr_to // g, sr_from // g, axis=0).astype(np.float32)


def db(x: float) -> float:
    return 20 * math.log10(max(float(x), 1e-12))


def amp(db_value: float) -> float:
    return 10 ** (float(db_value) / 20)


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(x)))) if x.size else 0.0


def fit_length(x: np.ndarray, n: int) -> np.ndarray:
    return x[:n] if len(x) >= n else np.pad(x, ((0, n - len(x)), (0, 0)))


def envelope(x: np.ndarray, sr: int, ms: float = 5.0) -> np.ndarray:
    """Smoothed peak envelope (per sample, one value for both channels)."""
    size = max(3, int(sr * ms / 1000))
    return np.convolve(np.abs(x).max(axis=1), np.ones(size) / size, mode="same").astype(np.float32) + 1e-5


def one_pole_env(x: np.ndarray, sr: int, attack_ms: float, release_ms: float) -> np.ndarray:
    """Peak follower with separate attack and release, per sample (the loop runs in blocks, so it stays quick)."""
    a = math.exp(-1 / max(1.0, sr * attack_ms / 1000))
    r = math.exp(-1 / max(1.0, sr * release_ms / 1000))
    peak = np.abs(x).max(axis=1)
    out = np.empty_like(peak)
    e = 0.0
    for i, p in enumerate(peak):
        e = a * e + (1 - a) * p if p > e else r * e + (1 - r) * p
        out[i] = e
    return out


def _lfo(n: int, sr: int, hz: float, shape: str = "sine", phase: float = 0.0) -> np.ndarray:
    t = np.arange(n) / sr
    ph = 2 * np.pi * hz * t + phase
    if shape == "triangle":
        return (2 / np.pi) * np.arcsin(np.sin(ph))
    if shape == "square":
        return np.sign(np.sin(ph))
    return np.sin(ph)


def _delay_line(x: np.ndarray, delay_samples: np.ndarray) -> np.ndarray:
    """x read back by a (possibly time-varying) delay, linear interpolation, per channel."""
    n = len(x)
    pos = np.arange(n) - delay_samples
    pos = np.clip(pos, 0, n - 1)
    return np.stack([np.interp(pos, np.arange(n), x[:, c]) for c in range(x.shape[1])], axis=1).astype(np.float32)


def _biquad(x: np.ndarray, b: Sequence[float], a: Sequence[float]) -> np.ndarray:
    return signal.lfilter(b, a, x, axis=0).astype(np.float32)


def _rbj(kind: str, sr: int, hz: float, q: float = 0.707, gain_db: float = 0.0) -> Tuple[List[float], List[float]]:
    """Robert Bristow-Johnson's cookbook biquads."""
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * min(max(hz, 10.0), sr * 0.49) / sr
    cw, sw = math.cos(w0), math.sin(w0)
    alpha = sw / (2 * max(q, 0.05))
    if kind == "lowpass":
        b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]; a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "highpass":
        b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]; a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "peak":
        b = [1 + alpha * A, -2 * cw, 1 - alpha * A]; a = [1 + alpha / A, -2 * cw, 1 - alpha / A]
    elif kind == "lowshelf":
        s = 2 * math.sqrt(A) * alpha
        b = [A * ((A + 1) - (A - 1) * cw + s), 2 * A * ((A - 1) - (A + 1) * cw), A * ((A + 1) - (A - 1) * cw - s)]
        a = [(A + 1) + (A - 1) * cw + s, -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - s]
    elif kind == "highshelf":
        s = 2 * math.sqrt(A) * alpha
        b = [A * ((A + 1) + (A - 1) * cw + s), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - s)]
        a = [(A + 1) - (A - 1) * cw + s, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - s]
    elif kind == "allpass":
        b = [1 - alpha, -2 * cw, 1 + alpha]; a = [1 + alpha, -2 * cw, 1 - alpha]
    else:
        raise ValueError(kind)
    a0 = a[0]
    return [v / a0 for v in b], [v / a0 for v in a]


# ----------------------------------------------------------------------------------------------------------------------
# STFT helpers (spectral effects)
# ----------------------------------------------------------------------------------------------------------------------

def _stft(x: np.ndarray, n_fft: int = 2048, hop: int = 512) -> np.ndarray:
    """(frames, bins) complex, for one channel; the signal is padded so every sample is covered."""
    win = np.hanning(n_fft).astype(np.float32)
    pad = np.pad(x, (n_fft // 2, n_fft // 2 + hop))
    frames = 1 + (len(pad) - n_fft) // hop
    idx = np.arange(n_fft)[None, :] + hop * np.arange(frames)[:, None]
    return np.fft.rfft(pad[idx] * win, axis=1)


def _istft(S: np.ndarray, n: int, n_fft: int = 2048, hop: int = 512) -> np.ndarray:
    win = np.hanning(n_fft).astype(np.float32)
    frames = S.shape[0]
    out = np.zeros(n_fft + hop * (frames - 1), dtype=np.float64)
    norm = np.zeros_like(out)
    y = np.fft.irfft(S, n_fft, axis=1) * win
    for i in range(frames):
        out[i * hop:i * hop + n_fft] += y[i]
        norm[i * hop:i * hop + n_fft] += win ** 2
    out = out / np.maximum(norm, 1e-3)
    return out[n_fft // 2:n_fft // 2 + n].astype(np.float32)


def _spectral_gain(x: np.ndarray, sr: int, gain_fn: Callable[[np.ndarray], np.ndarray], n_fft: int = 2048) -> np.ndarray:
    """Apply a frequency-dependent gain (linear, from a function of Hz) with an STFT, per channel."""
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)
    g = gain_fn(freqs).astype(np.float32)
    out = np.empty_like(x)
    for c in range(x.shape[1]):
        out[:, c] = _istft(_stft(x[:, c], n_fft) * g[None, :], len(x), n_fft)
    return out


def _cepstral_envelope(mag: np.ndarray, lifter: int = 30) -> np.ndarray:
    """Smooth spectral envelope of a magnitude spectrum (frames, bins): the first `lifter` cepstral coefficients."""
    logm = np.log(mag + 1e-7)
    cep = np.fft.irfft(logm, axis=1)
    cep[:, lifter:-lifter] = 0.0
    return np.exp(np.fft.rfft(cep, axis=1).real)


# ----------------------------------------------------------------------------------------------------------------------
# effects: every function takes (x, sr, rng, **params) and returns (samples, 2) float32
# ----------------------------------------------------------------------------------------------------------------------

def fx_gain(x, sr, rng, db_value: float = 0.0):
    return (x * amp(db_value)).astype(np.float32)


def fx_level(x, sr, rng, rms_db: float = -19.0, peak_db: float = -1.0):
    """RMS to a target, then peak limited to a ceiling (plain gain, no compression)."""
    g = min(amp(rms_db) / max(rms(x), 1e-6), amp(peak_db) / max(float(np.abs(x).max()), 1e-6))
    return (x * g).astype(np.float32)


def fx_normalize(x, sr, rng, peak_db: float = -1.0):
    return (x * (amp(peak_db) / max(float(np.abs(x).max()), 1e-6))).astype(np.float32)


def fx_fade(x, sr, rng, in_ms: float = 3.0, out_ms: float = 120.0, curve: float = 2.0):
    y = x.copy()
    n = len(y)
    i = min(int(sr * in_ms / 1000), n // 2)
    o = min(int(sr * out_ms / 1000), n // 2)
    if i > 0:
        y[:i] *= (np.linspace(0, 1, i, dtype=np.float32) ** (1 / curve))[:, None]
    if o > 0:
        y[-o:] *= (np.linspace(1, 0, o, dtype=np.float32) ** curve)[:, None]
    return y


def fx_trim(x, sr, rng, threshold_db: float = -42.0, head_ms: float = 4.0):
    """Cut silence before the sound starts and after it ends."""
    env = np.abs(x).max(axis=1)
    thr = max(1e-4, env.max() * amp(threshold_db))
    nz = np.nonzero(env > thr)[0]
    if nz.size == 0:
        return x
    start = max(0, nz[0] - int(sr * head_ms / 1000))
    return x[start:nz[-1] + 1].copy()


def fx_length(x, sr, rng, seconds: float = 1.0):
    return fit_length(x, int(sr * seconds))


def fx_reverse(x, sr, rng):
    return x[::-1].copy()


def fx_dc(x, sr, rng):
    return (x - x.mean(axis=0, keepdims=True)).astype(np.float32)


def fx_lowcut(x, sr, rng, hz: float = 80.0, order: int = 2):
    sos = signal.butter(max(1, int(order)), min(max(hz, 10.0), sr * 0.49), "highpass", fs=sr, output="sos")
    return signal.sosfiltfilt(sos, x, axis=0).astype(np.float32)


def fx_highcut(x, sr, rng, hz: float = 12000.0, order: int = 2):
    sos = signal.butter(max(1, int(order)), min(max(hz, 10.0), sr * 0.49), "lowpass", fs=sr, output="sos")
    return signal.sosfiltfilt(sos, x, axis=0).astype(np.float32)


def fx_bandpass(x, sr, rng, low_hz: float = 300.0, high_hz: float = 3000.0, order: int = 2):
    lo, hi = min(max(low_hz, 10.0), sr * 0.48), min(max(high_hz, 20.0), sr * 0.49)
    if hi <= lo:
        hi = min(lo * 1.5, sr * 0.49)
    sos = signal.butter(max(1, int(order)), [lo, hi], "bandpass", fs=sr, output="sos")
    return signal.sosfiltfilt(sos, x, axis=0).astype(np.float32)


def fx_bass(x, sr, rng, gain_db: float = 0.0, hz: float = 150.0):
    return _biquad(x, *_rbj("lowshelf", sr, hz, 0.707, gain_db))


def fx_treble(x, sr, rng, gain_db: float = 0.0, hz: float = 5000.0):
    return _biquad(x, *_rbj("highshelf", sr, hz, 0.707, gain_db))


def fx_mid(x, sr, rng, hz: float = 1000.0, gain_db: float = 0.0, q: float = 1.0):
    return _biquad(x, *_rbj("peak", sr, hz, q, gain_db))


def fx_tilt(x, sr, rng, db_per_octave: float = 0.0, pivot_hz: float = 1000.0):
    """Darker or brighter overall: a straight slope across the spectrum around the pivot."""
    return _spectral_gain(x, sr, lambda f: 10 ** (db_per_octave * np.log2(np.maximum(f, 20.0) / pivot_hz) / 20))


def fx_eq30(x, sr, rng, gains_db: Optional[Sequence[float]] = None, preset: Optional[str] = None):
    """30-band graphic equaliser (ISO third-octave centres 20 Hz to 16 kHz), as a smooth curve."""
    g = list(EQ30_PRESETS[preset]) if preset else [0.0] * 30
    if gains_db:
        g = [a + float(b) for a, b in zip(g, list(gains_db) + [0.0] * 30)]
    centres = np.log2(np.array(EQ30_HZ))
    return _spectral_gain(x, sr, lambda f: 10 ** (np.interp(np.log2(np.maximum(f, 20.0)), centres, g) / 20))


def fx_pitch(x, sr, rng, semitones: float = 0.0, keep_length: bool = True):
    """Pitch up or down. keep_length stretches the result back to the original length (phase vocoder); without it
    the sound gets shorter when raised and longer when lowered, like a tape."""
    if abs(semitones) < 1e-6:
        return x
    rate = 2 ** (semitones / 12)
    n = len(x)
    t = np.linspace(0, n - 1, max(8, int(n / rate)))
    y = np.stack([np.interp(t, np.arange(n), x[:, c]) for c in range(2)], axis=1).astype(np.float32)
    return fit_length(fx_stretch(y, sr, rng, factor=n / len(y)), n) if keep_length else y


def fx_stretch(x, sr, rng, factor: float = 1.0, n_fft: int = 2048):
    """Longer (factor > 1) or shorter without changing pitch: a phase vocoder."""
    if abs(factor - 1) < 1e-4:
        return x
    hop = n_fft // 4
    out_n = int(len(x) * factor)
    out = np.zeros((out_n, 2), dtype=np.float32)
    for c in range(2):
        S = _stft(x[:, c], n_fft, hop)
        frames = S.shape[0]
        steps = np.arange(0, frames - 1, 1 / factor)
        mag, ph = np.abs(S), np.angle(S)
        omega = 2 * np.pi * np.arange(S.shape[1]) * hop / n_fft
        acc = ph[0].copy()
        Y = np.empty((len(steps), S.shape[1]), dtype=np.complex128)
        for k, p in enumerate(steps):
            i = int(p); frac = p - i
            m = (1 - frac) * mag[i] + frac * mag[min(i + 1, frames - 1)]
            d = ph[min(i + 1, frames - 1)] - ph[i] - omega
            d -= 2 * np.pi * np.round(d / (2 * np.pi))
            Y[k] = m * np.exp(1j * acc)
            acc = acc + omega + d
        out[:, c] = fit_length(_istft(Y, out_n, n_fft, hop)[:, None], out_n)[:, 0]
    return out


def fx_formant(x, sr, rng, semitones: float = 0.0, lifter: int = 30, n_fft: int = 2048):
    """Move the resonances (the body size) without moving the pitch: the spectral envelope is warped, the fine
    structure kept. Up sounds smaller, down sounds bigger."""
    if abs(semitones) < 1e-6:
        return x
    ratio = 2 ** (semitones / 12)
    out = np.empty_like(x)
    bins = np.arange(n_fft // 2 + 1)
    for c in range(2):
        S = _stft(x[:, c], n_fft)
        mag = np.abs(S)
        env = _cepstral_envelope(mag, lifter)
        fine = mag / (env + 1e-7)
        warped = np.stack([np.interp(bins / ratio, bins, e) for e in env])
        out[:, c] = _istft(fine * warped * np.exp(1j * np.angle(S)), len(x), n_fft)
    return out


def fx_tone_from(x, sr, rng, ref: Optional[np.ndarray] = None, amount: float = 1.0, lifter: int = 30, n_fft: int = 2048,
                 per_frame: bool = False):
    """Give x the overall colour of ref: the reference's average spectral envelope replaces x's, by `amount`.
    per_frame: ref is time-aligned with x (the same sound before processing), so each frame takes ref's colour AT THAT
    MOMENT; a hit keeps its bright attack and dark tail instead of one average colour smeared over both."""
    if ref is None:
        return x
    out = np.empty_like(x)
    r = fit_length(to_stereo(ref), len(x)) if per_frame else to_stereo(ref)
    for c in range(2):
        S = _stft(x[:, c], n_fft)
        mag = np.abs(S)
        own = _cepstral_envelope(mag, lifter)
        target = _cepstral_envelope(np.abs(_stft(r[:, c], n_fft)), lifter)
        if not per_frame or target.shape != own.shape:
            target = target.mean(axis=0, keepdims=True)
        new_env = own ** (1 - amount) * target ** amount
        out[:, c] = _istft(mag / (own + 1e-7) * new_env * np.exp(1j * np.angle(S)), len(x), n_fft)
    return (out * (rms(x) / max(rms(out), 1e-6))).astype(np.float32)


def fx_envelope_from(x, sr, rng, ref: Optional[np.ndarray] = None, amount: float = 1.0, ms: float = 5.0, max_gain_db: float = 18.0):
    """Give x the loudness shape of ref (its attack and decay) without touching its waveform or tone."""
    if ref is None:
        return x
    r = fit_length(to_stereo(ref), len(x))
    gain = np.clip(envelope(r, sr, ms) / envelope(x, sr, ms), amp(-max_gain_db), amp(max_gain_db)) ** amount
    return (x * gain[:, None]).astype(np.float32)


def fx_saturate(x, sr, rng, drive: float = 0.3, mix: float = 1.0, tone_hz: float = 0.0):
    """Soft clipping: warmth at low drive, grit at high. tone_hz > 0 rolls the top off the wet part afterwards."""
    k = 1 + 20 * max(drive, 0.0)
    wet = np.tanh(x * k) / math.tanh(min(k, 20.0) * 0.5) * 0.5
    wet = wet * (rms(x) / max(rms(wet), 1e-6))
    if tone_hz > 0:
        wet = fx_highcut(wet, sr, rng, tone_hz)
    return ((1 - mix) * x + mix * wet).astype(np.float32)


def fx_bitcrush(x, sr, rng, bits: float = 8.0, downsample: int = 1, mix: float = 1.0):
    levels = 2 ** max(float(bits), 1.0)
    wet = np.round(x * levels / 2) / (levels / 2)
    d = max(1, int(downsample))
    if d > 1:
        wet = np.repeat(wet[::d], d, axis=0)[:len(x)]
    return ((1 - mix) * x + mix * wet).astype(np.float32)


def fx_compress(x, sr, rng, threshold_db: float = -18.0, ratio: float = 4.0, attack_ms: float = 5.0, release_ms: float = 80.0, makeup_db: float = 0.0):
    env = one_pole_env(x, sr, attack_ms, release_ms)
    over = np.maximum(20 * np.log10(env + 1e-6) - threshold_db, 0.0)
    gain = 10 ** (-(over - over / max(ratio, 1.0)) / 20) * amp(makeup_db)
    return (x * gain[:, None]).astype(np.float32)


def fx_intensity(x, sr, rng, amount: float = 0.5):
    """One knob for 'more': compression plus a touch of saturation, level kept."""
    y = fx_compress(x, sr, rng, threshold_db=-24 + 10 * (1 - amount), ratio=2 + 6 * amount, attack_ms=3, release_ms=60)
    y = fx_saturate(y, sr, rng, drive=0.15 * amount, mix=0.6)
    return (y * (rms(x) / max(rms(y), 1e-6))).astype(np.float32)


def fx_transient(x, sr, rng, attack: float = 0.0, sustain: float = 0.0):
    """attack > 0 sharpens the hit, < 0 softens it; sustain > 0 lifts the tail, < 0 shortens it. Both -1..1."""
    fast, slow = envelope(x, sr, 1.0), envelope(x, sr, 40.0)
    trans = np.clip((fast - slow) / slow, 0.0, 4.0)
    gain = 1 + attack * trans * 0.75
    body = np.clip((slow - fast) / slow, 0.0, 1.0)
    gain = gain * (1 + sustain * body)
    return (x * np.clip(gain, 0.05, 6.0)[:, None]).astype(np.float32)


def fx_gate(x, sr, rng, threshold_db: float = -40.0, hold_ms: float = 30.0, release_ms: float = 40.0):
    env = one_pole_env(x, sr, 0.5, release_ms)
    peak = max(float(np.abs(x).max()), 1e-6)
    open_ = env > peak * amp(threshold_db)
    hold = max(1, int(sr * hold_ms / 1000))
    open_ = np.convolve(open_.astype(np.float32), np.ones(hold), mode="same") > 0
    g = np.convolve(open_.astype(np.float32), np.ones(max(3, int(sr * 0.005))) / max(3, int(sr * 0.005)), mode="same")
    return (x * g[:, None]).astype(np.float32)


def fx_tremolo(x, sr, rng, hz: float = 5.0, depth: float = 0.5, shape: str = "sine"):
    m = 1 - depth * (0.5 + 0.5 * _lfo(len(x), sr, hz, shape))
    return (x * m[:, None]).astype(np.float32)


def fx_flicker(x, sr, rng, hz: float = 9.0, depth: float = 0.3, stereo: float = 0.3):
    """Irregular loudness movement, like a flame or a crackling arc: smooth random gain points at about `hz` per
    second (never a steady wobble), each channel a little different by `stereo`. The seed decides the pattern."""
    n = len(x)
    rng = rng if rng is not None else np.random.default_rng(0)
    k = max(4, int(n / sr * hz) + 3)
    t = np.linspace(0, k - 1, n)
    common = rng.uniform(-1, 1, k)
    out = np.empty_like(x)
    for c in range(x.shape[1] if x.ndim == 2 else 1):
        pts = common * (1 - stereo) + rng.uniform(-1, 1, k) * stereo
        g = np.interp(t, np.arange(k), pts)
        g = np.convolve(g, np.hanning(max(3, int(sr / hz / 2))) / max(1.0, np.hanning(max(3, int(sr / hz / 2))).sum()), mode="same")
        m = 1 - depth * (0.5 + 0.5 * np.clip(g / max(float(np.abs(g).max()), 1e-6), -1, 1))
        out[:, c] = x[:, c] * m
    return (out * (rms(x) / max(rms(out), 1e-6))).astype(np.float32)


def fx_chop(x, sr, rng, hz: float = 8.0, duty: float = 0.5, depth: float = 1.0, ramp_ms: float = 4.0):
    """Rhythmic gating: on for `duty` of each cycle, off the rest, with soft edges."""
    t = np.arange(len(x)) / sr
    gate = ((t * hz) % 1.0 < duty).astype(np.float32)
    k = max(3, int(sr * ramp_ms / 1000))
    gate = np.convolve(gate, np.ones(k) / k, mode="same")
    return (x * (1 - depth + depth * gate)[:, None]).astype(np.float32)


def fx_ring(x, sr, rng, hz: float = 200.0, mix: float = 1.0):
    """Ring modulation: the robot / metallic sidebands."""
    m = np.sin(2 * np.pi * hz * np.arange(len(x)) / sr).astype(np.float32)
    return ((1 - mix) * x + mix * x * m[:, None]).astype(np.float32)


def fx_vibrato(x, sr, rng, hz: float = 5.0, depth_ms: float = 1.5):
    d = sr * depth_ms / 1000 * (0.5 + 0.5 * _lfo(len(x), sr, hz)) + 1
    return _delay_line(x, d)


def fx_chorus(x, sr, rng, voices: int = 3, hz: float = 0.8, depth_ms: float = 4.0, delay_ms: float = 18.0, mix: float = 0.5):
    wet = np.zeros_like(x)
    for v in range(max(1, int(voices))):
        ph = 2 * np.pi * v / max(1, voices)
        d = sr * (delay_ms + depth_ms * (0.5 + 0.5 * _lfo(len(x), sr, hz * (1 + 0.1 * v), phase=ph))) / 1000
        y = _delay_line(x, d)
        if voices > 1:   # spread voices across the stereo field
            pan = (v / (voices - 1)) * 2 - 1
            y = y * np.array([math.sqrt(0.5 - 0.5 * pan), math.sqrt(0.5 + 0.5 * pan)], dtype=np.float32)[None, :] * 1.4
        wet += y / math.sqrt(voices)
    return ((1 - mix) * x + mix * wet).astype(np.float32)


def fx_flanger(x, sr, rng, hz: float = 0.3, depth_ms: float = 2.0, delay_ms: float = 1.0, feedback: float = 0.4, mix: float = 0.5):
    d = sr * (delay_ms + depth_ms * (0.5 + 0.5 * _lfo(len(x), sr, hz))) / 1000 + 1
    y = x.copy()
    for _ in range(3 if abs(feedback) > 0.01 else 1):   # a few passes stand in for the feedback loop
        y = x + feedback * _delay_line(y, d)
    wet = _delay_line(y, d)
    return ((1 - mix) * x + mix * wet).astype(np.float32)


def fx_phaser(x, sr, rng, hz: float = 0.5, stages: int = 6, low_hz: float = 300.0, high_hz: float = 3000.0, feedback: float = 0.3, mix: float = 0.5, block: int = 128):
    """A cascade of all-pass filters whose centre sweeps with the LFO; coefficients change every `block` samples."""
    n = len(x)
    wet = np.empty_like(x)
    sweep = low_hz * (high_hz / low_hz) ** (0.5 + 0.5 * _lfo(n, sr, hz))
    states = [[None, None] for _ in range(stages)]
    fb = np.zeros(2, dtype=np.float32)
    for s in range(0, n, block):
        seg = x[s:s + block].copy()
        seg[0] += feedback * fb
        b, a = _rbj("allpass", sr, float(sweep[s]), 0.6)
        for st in range(stages):
            for c in range(2):
                zi = states[st][c] if states[st][c] is not None else signal.lfilter_zi(b, a) * 0
                seg[:, c], states[st][c] = signal.lfilter(b, a, seg[:, c], zi=zi)
        fb = seg[-1]
        wet[s:s + block] = seg
    return ((1 - mix) * x + mix * wet).astype(np.float32)


def fx_echo(x, sr, rng, time_ms: float = 300.0, feedback: float = 0.4, mix: float = 0.35, damping_hz: float = 5000.0, repeats: int = 8, stereo_ms: float = 0.0):
    """Repeats of the sound, each quieter and darker. Lengthens the output to hold the tail."""
    d = int(sr * time_ms / 1000)
    reps = max(1, int(repeats))
    out = np.zeros((len(x) + d * reps, 2), dtype=np.float32)
    out[:len(x)] = x * (1 - mix)
    tap = x.copy()
    for r in range(1, reps + 1):
        tap = fx_highcut(tap, sr, rng, damping_hz) * feedback
        off = d * r + int(sr * stereo_ms / 1000) * (r % 2)
        seg = out[off:off + len(tap)]
        seg += tap[:len(seg)] * mix
    return out


def fx_reverb(x, sr, rng, room: float = 0.5, decay: float = 0.6, damping: float = 0.4, mix: float = 0.25, predelay_ms: float = 10.0, width: float = 1.0):
    """A small Schroeder reverb: four combs and two all-passes, slightly different per channel for width.
    room scales the delays (0 small, 1 hall), decay the feedback, damping the darkness of the tail."""
    base = np.array([1116, 1188, 1277, 1356]) * (0.4 + 1.2 * room) * sr / 44100
    g = 0.5 + 0.48 * min(max(decay, 0.0), 1.0)
    tail = int(sr * (0.3 + 2.5 * decay * (0.3 + room)))
    n = len(x) + tail
    wet = np.zeros((n, 2), dtype=np.float32)
    dry = np.zeros((n, 2), dtype=np.float32)
    dry[:len(x)] = x
    pre = int(sr * predelay_ms / 1000)
    src = np.zeros((n, 2), dtype=np.float32)
    src[pre:pre + len(x)] = x
    lp = max(0.0, min(damping, 0.99))
    for c in range(2):
        acc = np.zeros(n, dtype=np.float32)
        for k, d0 in enumerate(base):
            d = int(d0 * (1 + 0.023 * c * (k + 1) * width))
            b = np.zeros(d + 1); b[0] = 1.0
            # comb with damped feedback: y[n] = x[n] + g*((1-lp)*y[n-d] + lp*y[n-d-1])
            a = np.zeros(d + 2); a[0] = 1.0; a[d] = -g * (1 - lp); a[d + 1] = -g * lp
            acc += signal.lfilter(b, a, src[:, c]).astype(np.float32)
        y = acc / len(base)
        for d in (int(556 * sr / 44100 * (1 + 0.03 * c)), int(441 * sr / 44100)):
            b = np.zeros(d + 1); b[0] = -0.5; b[d] = 1.0
            a = np.zeros(d + 1); a[0] = 1.0; a[d] = -0.5
            y = signal.lfilter(b, a, y).astype(np.float32)
        wet[:, c] = y
    wet *= rms(x) / max(rms(wet), 1e-6)
    return ((1 - mix) * dry + mix * wet).astype(np.float32)


def fx_width(x, sr, rng, amount: float = 1.0):
    """Stereo width: 0 mono, 1 as is, 2 twice the side signal."""
    mid, side = (x[:, 0] + x[:, 1]) / 2, (x[:, 0] - x[:, 1]) / 2 * amount
    return np.stack([mid + side, mid - side], axis=1).astype(np.float32)


def fx_pan(x, sr, rng, position: float = 0.0):
    """-1 left to 1 right, equal power."""
    p = (min(max(position, -1.0), 1.0) + 1) / 2
    return (x * np.array([math.cos(p * math.pi / 2), math.sin(p * math.pi / 2)], dtype=np.float32)[None, :] * math.sqrt(2)).astype(np.float32)


def fx_decorrelate(x, sr, rng, spread: float = 0.35, knots: int = 96, keep_attack: bool = True):
    """Random all-pass phase per channel: a new waveform with the same spectrum, wide stereo, attack kept."""
    n = len(x)
    size = int(2 ** np.ceil(np.log2(n + 2048)))
    bins = size // 2 + 1
    grid = np.log1p(np.arange(bins)) / np.log1p(bins - 1)
    shared = np.interp(grid, np.linspace(0, 1, knots), rng.uniform(-np.pi, np.pi, knots))
    out = np.zeros_like(x)
    for c in range(2):
        own = np.interp(grid, np.linspace(0, 1, knots), rng.uniform(-np.pi, np.pi, knots))
        out[:, c] = np.fft.irfft(np.fft.rfft(x[:, c], size) * np.exp(1j * (shared + own * spread)), size)[:n]
    return fx_envelope_from(out, sr, rng, ref=x, ms=4.0) if keep_attack else out


def fx_freq_shift(x, sr, rng, hz: float = 20.0):
    """Single-sideband frequency shift: every partial moves by the same `hz` (not a ratio, so harmonics stop lining up).
    A small shift leaves noise and hits sounding the same but breaks the waveform match of their tonal resonances,
    which no phase change can (a sine matches a sine of the same pitch at some lag, whatever its phase). Length kept."""
    x = to_stereo(x)
    n = len(x)
    size = int(2 ** np.ceil(np.log2(n + 1)))
    h = np.zeros(size); h[0] = 1; h[1:size // 2] = 2; h[size // 2] = 1          # analytic signal
    t = np.arange(n) / sr
    rot = np.exp(2j * np.pi * hz * t)
    out = np.empty_like(x)
    for c in range(2):
        a = np.fft.ifft(np.fft.fft(x[:, c], size) * h)[:n]
        out[:, c] = np.real(a * rot)
    return out.astype(np.float32)


def fx_side_from_mid(x, sr, rng, width: float = 0.3, knots: int = 48, low_hz: float = 150.0):
    """Widen a (near) mono sound the way a mix engineer does: the mid stays exactly as it is, and a side signal is made
    from an all-pass copy of the mid (same spectrum, own phase) at `width` times the mid's level. The mono sum is the
    original mid, so nothing cancels and the hit is untouched; below `low_hz` the side fades out (the low end stays mono)."""
    x = to_stereo(x)
    n = len(x)
    mid = (x[:, 0] + x[:, 1]) / 2
    size = int(2 ** np.ceil(np.log2(n + 2048)))
    freqs = np.fft.rfftfreq(size, 1 / sr)
    grid = np.log1p(np.arange(len(freqs))) / np.log1p(len(freqs) - 1)
    phase = np.interp(grid, np.linspace(0, 1, knots), rng.uniform(-np.pi, np.pi, knots))
    lowfade = np.clip((freqs - low_hz) / low_hz, 0.0, 1.0)
    side = np.fft.irfft(np.fft.rfft(mid, size) * lowfade * np.exp(1j * phase), size)[:n]
    side = fx_envelope_from(np.stack([side, side], axis=1), sr, rng, ref=np.stack([mid, mid], axis=1), ms=4.0)[:, 0]
    k = width * rms(mid) / max(rms(side), 1e-9)
    return np.stack([mid + k * side, mid - k * side], axis=1).astype(np.float32)


def fx_doubles(x, sr, rng, voices: int = 2, detune_cents: float = 12.0, delay_ms: float = 15.0, mix: float = 0.5):
    """Extra copies, slightly detuned and late, spread left and right: thicker, bigger."""
    wet = np.zeros_like(x)
    for v in range(max(1, int(voices))):
        sign = 1 if v % 2 == 0 else -1
        y = fx_pitch(x, sr, rng, sign * detune_cents * (1 + v // 2) / 100, keep_length=True)
        y = _delay_line(y, np.full(len(x), sr * delay_ms * (1 + v) / 1000))
        y = fx_pan(y, sr, rng, sign * (0.3 + 0.2 * (v // 2)))
        wet += y / math.sqrt(voices)
    return ((1 - mix) * x + mix * wet).astype(np.float32)


def fx_noise(x, sr, rng, color: str = "pink", level_db: float = -30.0, band: Optional[Sequence[float]] = None, follow: float = 1.0):
    """Add a noise bed (white, pink or brown), shaped by the sound's own envelope by `follow` (0 steady, 1 fully)."""
    n = len(x)
    w = rng.standard_normal((n, 2)).astype(np.float32)
    if color == "pink":
        w = np.stack([_spectral_gain(w[:, c:c + 1].repeat(2, axis=1), sr, lambda f: 1 / np.sqrt(np.maximum(f, 20.0)))[:, 0] for c in range(2)], axis=1)
    elif color == "brown":
        w = np.cumsum(w, axis=0); w -= w.mean(axis=0)
    if band:
        w = fx_bandpass(w, sr, rng, band[0], band[1])
    w *= amp(level_db) / max(rms(w), 1e-6)
    if follow > 0:
        e = envelope(x, sr, 10.0); e = (e / e.max()) ** follow
        w *= e[:, None]
    return (x + w).astype(np.float32)


def fx_glide(x, sr, rng, start_st: float = 0.0, end_st: float = -12.0, curve: float = 1.0):
    """Pitch glide across the sound, tape style (an impact's downward bend, a riser's climb). start/end in semitones,
    curve > 1 holds then bends, < 1 bends early. Length stays."""
    n = len(x)
    t = np.linspace(0, 1, n) ** max(curve, 0.05)
    rate = 2 ** ((start_st + (end_st - start_st) * t) / 12)
    pos = np.cumsum(rate); pos = pos / pos[-1] * (n - 1)
    return np.stack([np.interp(pos, np.arange(n), x[:, c]) for c in range(2)], axis=1).astype(np.float32)


def fx_sub(x, sr, rng, hz: float = 45.0, level_db: float = -12.0, decay: float = 0.6, drive: float = 0.2, glide_st: float = -7.0):
    """A synthesized sub-bass thump under the sound: a sine at hz that glides down and decays, shaped by the sound's own
    envelope so it hits when the sound hits. What boom and impact tools add for weight."""
    n = len(x)
    t = np.arange(n) / sr
    env = envelope(x, sr, 8.0); env = env / env.max()
    f = hz * 2 ** (glide_st * np.clip(t / max(0.3, decay), 0, 1) / 12)
    phase = 2 * np.pi * np.cumsum(f) / sr
    sine = np.sin(phase) * np.exp(-t / max(decay, 0.05)) * np.maximum(env, np.exp(-t / max(decay, 0.05)) * 0.5)
    sine = np.tanh(sine * (1 + 6 * drive))
    sine *= amp(level_db) / max(rms(sine[:, None]), 1e-6)
    out = (x + sine[:, None]).astype(np.float32)
    peak_in, peak_out = float(np.abs(x).max()), float(np.abs(out).max())
    return out * min(1.0, peak_in / max(peak_out, 1e-6)) if peak_out > peak_in else out


def fx_comb(x, sr, rng, hz: float = 220.0, feedback: float = 0.7, damping_hz: float = 6000.0, mix: float = 0.5):
    """A comb resonator tuned to hz: metallic ring, a pitch inside noise, a tube."""
    d = max(2, int(round(sr / max(hz, 20.0))))
    b = np.zeros(d + 1); b[0] = 1.0
    a = np.zeros(d + 1); a[0] = 1.0; a[d] = -min(max(feedback, -0.98), 0.98)
    wet = signal.lfilter(b, a, x, axis=0).astype(np.float32)
    wet = fx_highcut(wet, sr, rng, damping_hz)
    wet *= rms(x) / max(rms(wet), 1e-6)
    return ((1 - mix) * x + mix * wet).astype(np.float32)


def fx_shimmer(x, sr, rng, semitones: float = 12.0, feedback: float = 0.4, mix: float = 0.3, room: float = 0.8):
    """Pitch-shifted reverb: the tail rises an octave (or whatever) each time round. Ethereal, magical."""
    wet = fx_reverb(x, sr, rng, room=room, decay=0.7, damping=0.3, mix=1.0)
    shifted = fx_pitch(wet, sr, rng, semitones, keep_length=True)
    for _ in range(2 if abs(feedback) > 0.05 else 0):
        shifted = shifted + feedback * fx_pitch(fx_reverb(shifted, sr, rng, room=room, decay=0.6, mix=1.0)[:len(shifted)], sr, rng, semitones, keep_length=True)
    out = np.zeros((max(len(x), len(shifted)), 2), dtype=np.float32)
    out[:len(x)] += (1 - mix) * x
    out[:len(shifted)] += mix * shifted * (rms(x) / max(rms(shifted), 1e-6))
    return out


def fx_denoise(x, sr, rng, amount: float = 0.7, floor_db: float = -30.0, n_fft: int = 2048):
    """Take steady noise out (hiss, hum, room): the quietest fifth of the frames gives the noise profile, which is
    subtracted from every frame by `amount`; floor_db caps how far any bin can be pulled down, so it never gets glassy."""
    out = np.empty_like(x)
    floor = amp(floor_db)
    for c in range(2):
        S = _stft(x[:, c], n_fft)
        mag = np.abs(S)
        energy = mag.sum(axis=1)
        quiet = mag[energy <= np.percentile(energy, 20)]
        profile = (quiet.mean(axis=0) if len(quiet) else mag.min(axis=0)) * amount
        gain = np.clip(1 - profile[None, :] / (mag + 1e-7), floor, 1.0)
        out[:, c] = _istft(S * gain, len(x), n_fft)
    return out


CATALOG: Dict[str, Dict[str, Any]] = {
    "denoise": {"fn": fx_denoise, "doc": "Remove steady noise (hiss, hum, room) by spectral subtraction.", "params": {"amount": [0.7, 0, 2, "how much of the noise profile to take out"], "floor_db": [-30.0, -60, 0, "deepest cut per bin"]}},
    "gain": {"fn": fx_gain, "doc": "Volume change.", "params": {"db_value": [0.0, -60, 24, "dB"]}},
    "level": {"fn": fx_level, "doc": "Set the RMS level, peak limited; the usual last step before export.", "params": {"rms_db": [-19.0, -40, -6, "dBFS RMS"], "peak_db": [-1.0, -12, 0, "dBFS ceiling"]}},
    "normalize": {"fn": fx_normalize, "doc": "Peak to a ceiling.", "params": {"peak_db": [-1.0, -12, 0, "dBFS"]}},
    "fade": {"fn": fx_fade, "doc": "Fade in and out.", "params": {"in_ms": [3.0, 0, 2000, "ms"], "out_ms": [120.0, 0, 5000, "ms"], "curve": [2.0, 0.5, 4, "shape, >1 holds then drops"]}},
    "trim": {"fn": fx_trim, "doc": "Cut leading and trailing silence.", "params": {"threshold_db": [-42.0, -80, -20, "dB under the peak"], "head_ms": [4.0, 0, 50, "ms kept before the start"]}},
    "length": {"fn": fx_length, "doc": "Cut or pad to a length.", "params": {"seconds": [1.0, 0.05, 30, "s"]}},
    "reverse": {"fn": fx_reverse, "doc": "Play backwards.", "params": {}},
    "dc": {"fn": fx_dc, "doc": "Remove DC offset.", "params": {}},
    "lowcut": {"fn": fx_lowcut, "doc": "High-pass: remove rumble below hz.", "params": {"hz": [80.0, 20, 2000, "Hz"], "order": [2, 1, 8, "steepness"]}},
    "highcut": {"fn": fx_highcut, "doc": "Low-pass: remove hiss above hz.", "params": {"hz": [12000.0, 200, 20000, "Hz"], "order": [2, 1, 8, "steepness"]}},
    "bandpass": {"fn": fx_bandpass, "doc": "Keep only a band (radio, phone, texture placement).", "params": {"low_hz": [300.0, 20, 10000, "Hz"], "high_hz": [3000.0, 100, 20000, "Hz"], "order": [2, 1, 8, "steepness"]}},
    "bass": {"fn": fx_bass, "doc": "Low shelf.", "params": {"gain_db": [0.0, -18, 18, "dB"], "hz": [150.0, 40, 500, "Hz"]}},
    "treble": {"fn": fx_treble, "doc": "High shelf.", "params": {"gain_db": [0.0, -18, 18, "dB"], "hz": [5000.0, 1500, 12000, "Hz"]}},
    "mid": {"fn": fx_mid, "doc": "Peaking band.", "params": {"hz": [1000.0, 50, 12000, "Hz"], "gain_db": [0.0, -18, 18, "dB"], "q": [1.0, 0.2, 10, "width, higher is narrower"]}},
    "tilt": {"fn": fx_tilt, "doc": "Darker (negative) or brighter overall.", "params": {"db_per_octave": [0.0, -6, 6, "dB per octave"], "pivot_hz": [1000.0, 100, 5000, "Hz unchanged"]}},
    "eq30": {"fn": fx_eq30, "doc": "30-band graphic EQ, ISO third-octave 20 Hz to 16 kHz; a preset, gains, or both added.", "params": {"gains_db": [None, -24, 24, "list of 30 dB values"], "preset": [None, None, None, "one of " + ", ".join(EQ30_PRESETS)]}},
    "pitch": {"fn": fx_pitch, "doc": "Pitch shift; keep_length holds the duration (phase vocoder), else it changes like tape.", "params": {"semitones": [0.0, -24, 24, "semitones"], "keep_length": [True, None, None, "bool"]}},
    "stretch": {"fn": fx_stretch, "doc": "Time stretch without pitch change.", "params": {"factor": [1.0, 0.25, 4, "x length"]}},
    "formant": {"fn": fx_formant, "doc": "Body size: resonances move, pitch stays. Down is bigger.", "params": {"semitones": [0.0, -12, 12, "semitones"], "lifter": [30, 10, 80, "envelope smoothness"]}},
    "tone_from": {"fn": fx_tone_from, "doc": "Take the overall colour of a reference sound.", "params": {"ref": [None, None, None, "source name"], "amount": [1.0, 0, 1, "0 none, 1 fully"], "lifter": [30, 10, 80, "envelope smoothness"], "per_frame": [False, None, None, "ref is the same sound time-aligned: match colour frame by frame"]}},
    "envelope_from": {"fn": fx_envelope_from, "doc": "Take the loudness shape of a reference sound.", "params": {"ref": [None, None, None, "source name"], "amount": [1.0, 0, 1, "0 none, 1 fully"], "ms": [5.0, 1, 50, "envelope smoothing"], "max_gain_db": [18.0, 0, 40, "cap"]}},
    "saturate": {"fn": fx_saturate, "doc": "Soft clipping: warmth to grit.", "params": {"drive": [0.3, 0, 1, "amount"], "mix": [1.0, 0, 1, "wet"], "tone_hz": [0.0, 0, 20000, "0 off, else low-pass on the wet part"]}},
    "bitcrush": {"fn": fx_bitcrush, "doc": "Lo-fi: fewer bits, lower sample rate.", "params": {"bits": [8.0, 1, 16, "bits"], "downsample": [1, 1, 32, "keep every nth sample"], "mix": [1.0, 0, 1, "wet"]}},
    "compress": {"fn": fx_compress, "doc": "Dynamics compression.", "params": {"threshold_db": [-18.0, -60, 0, "dB"], "ratio": [4.0, 1, 20, ":1"], "attack_ms": [5.0, 0.1, 100, "ms"], "release_ms": [80.0, 5, 1000, "ms"], "makeup_db": [0.0, 0, 24, "dB"]}},
    "intensity": {"fn": fx_intensity, "doc": "One knob for more punch and density.", "params": {"amount": [0.5, 0, 1, "amount"]}},
    "transient": {"fn": fx_transient, "doc": "Sharpen or soften the attack, lift or shorten the tail.", "params": {"attack": [0.0, -1, 1, "amount"], "sustain": [0.0, -1, 1, "amount"]}},
    "gate": {"fn": fx_gate, "doc": "Silence below a threshold.", "params": {"threshold_db": [-40.0, -80, -10, "dB under the peak"], "hold_ms": [30.0, 0, 500, "ms"], "release_ms": [40.0, 1, 500, "ms"]}},
    "flicker": {"fn": fx_flicker, "doc": "Irregular loudness movement (flame, arc, crackle), seeded.", "params": {"hz": [9.0, 1, 40, "changes per second"], "depth": [0.3, 0, 1, "amount"], "stereo": [0.3, 0, 1, "channel difference"]}},
    "tremolo": {"fn": fx_tremolo, "doc": "Volume wobble.", "params": {"hz": [5.0, 0.1, 30, "Hz"], "depth": [0.5, 0, 1, "amount"], "shape": ["sine", None, None, "sine, triangle, square"]}},
    "chop": {"fn": fx_chop, "doc": "Rhythmic on-off gating.", "params": {"hz": [8.0, 0.5, 50, "Hz"], "duty": [0.5, 0.05, 0.95, "on fraction"], "depth": [1.0, 0, 1, "amount"], "ramp_ms": [4.0, 0.5, 50, "edge softness"]}},
    "ring": {"fn": fx_ring, "doc": "Ring modulation: robotic, metallic.", "params": {"hz": [200.0, 1, 5000, "Hz"], "mix": [1.0, 0, 1, "wet"]}},
    "vibrato": {"fn": fx_vibrato, "doc": "Pitch wobble.", "params": {"hz": [5.0, 0.1, 20, "Hz"], "depth_ms": [1.5, 0.1, 10, "ms"]}},
    "chorus": {"fn": fx_chorus, "doc": "Detuned, spread copies.", "params": {"voices": [3, 1, 8, "count"], "hz": [0.8, 0.05, 5, "Hz"], "depth_ms": [4.0, 0.5, 15, "ms"], "delay_ms": [18.0, 5, 40, "ms"], "mix": [0.5, 0, 1, "wet"]}},
    "flanger": {"fn": fx_flanger, "doc": "Sweeping comb, jet-like.", "params": {"hz": [0.3, 0.05, 5, "Hz"], "depth_ms": [2.0, 0.1, 10, "ms"], "delay_ms": [1.0, 0.1, 10, "ms"], "feedback": [0.4, -0.9, 0.9, "amount"], "mix": [0.5, 0, 1, "wet"]}},
    "phaser": {"fn": fx_phaser, "doc": "Sweeping notches.", "params": {"hz": [0.5, 0.05, 5, "Hz"], "stages": [6, 2, 12, "all-pass count"], "low_hz": [300.0, 50, 2000, "Hz"], "high_hz": [3000.0, 500, 12000, "Hz"], "feedback": [0.3, -0.9, 0.9, "amount"], "mix": [0.5, 0, 1, "wet"]}},
    "echo": {"fn": fx_echo, "doc": "Repeats; lengthens the sound.", "params": {"time_ms": [300.0, 10, 2000, "ms"], "feedback": [0.4, 0, 0.95, "amount"], "mix": [0.35, 0, 1, "wet"], "damping_hz": [5000.0, 500, 20000, "Hz low-pass per repeat"], "repeats": [8, 1, 40, "count"], "stereo_ms": [0.0, 0, 50, "ms ping-pong offset"]}},
    "reverb": {"fn": fx_reverb, "doc": "Room; lengthens the sound.", "params": {"room": [0.5, 0, 1, "size"], "decay": [0.6, 0, 1, "length"], "damping": [0.4, 0, 0.99, "darkness"], "mix": [0.25, 0, 1, "wet"], "predelay_ms": [10.0, 0, 100, "ms"], "width": [1.0, 0, 1, "stereo difference"]}},
    "width": {"fn": fx_width, "doc": "Stereo width.", "params": {"amount": [1.0, 0, 3, "0 mono, 1 as is"]}},
    "pan": {"fn": fx_pan, "doc": "Position.", "params": {"position": [0.0, -1, 1, "left to right"]}},
    "freq_shift": {"fn": fx_freq_shift, "doc": "Move every partial by the same Hz: breaks the match of tonal resonances, length kept.", "params": {"hz": [20.0, -400, 400, "Hz"]}},
    "side_from_mid": {"fn": fx_side_from_mid, "doc": "Widen a mono sound without touching it: mid kept exactly, side made from an all-pass copy of it.", "params": {"width": [0.3, 0, 1.5, "side level against the mid"], "knots": [48, 8, 256, "phase detail"], "low_hz": [150.0, 0, 500, "side fades out below this"]}},
    "decorrelate": {"fn": fx_decorrelate, "doc": "New waveform, same spectrum, wide stereo (random phase per channel).", "params": {"spread": [0.35, 0, 1, "channel difference"], "knots": [96, 8, 512, "more is a harder scramble"], "keep_attack": [True, None, None, "bool"]}},
    "doubles": {"fn": fx_doubles, "doc": "Detuned late copies, thicker.", "params": {"voices": [2, 1, 6, "count"], "detune_cents": [12.0, 1, 50, "cents"], "delay_ms": [15.0, 2, 60, "ms"], "mix": [0.5, 0, 1, "wet"]}},
    "glide": {"fn": fx_glide, "doc": "Pitch bend across the sound (impact drop, riser climb).", "params": {"start_st": [0.0, -24, 24, "semitones at the start"], "end_st": [-12.0, -24, 24, "semitones at the end"], "curve": [1.0, 0.2, 5, ">1 holds then bends"]}},
    "sub": {"fn": fx_sub, "doc": "Synthesized sub-bass thump under the sound, following its envelope.", "params": {"hz": [45.0, 25, 120, "Hz"], "level_db": [-12.0, -40, 0, "dBFS RMS"], "decay": [0.6, 0.05, 3, "s"], "drive": [0.2, 0, 1, "amount"], "glide_st": [-7.0, -24, 0, "pitch drop in semitones"]}},
    "comb": {"fn": fx_comb, "doc": "Comb resonator: metallic ring at a pitch.", "params": {"hz": [220.0, 20, 4000, "Hz"], "feedback": [0.7, -0.98, 0.98, "ring length"], "damping_hz": [6000.0, 500, 20000, "Hz"], "mix": [0.5, 0, 1, "wet"]}},
    "shimmer": {"fn": fx_shimmer, "doc": "Pitch-shifted reverb; lengthens the sound.", "params": {"semitones": [12.0, -24, 24, "shift per pass"], "feedback": [0.4, 0, 0.8, "amount"], "mix": [0.3, 0, 1, "wet"], "room": [0.8, 0, 1, "size"]}},
    "noise": {"fn": fx_noise, "doc": "Add a noise bed that follows the sound.", "params": {"color": ["pink", None, None, "white, pink, brown"], "level_db": [-30.0, -60, 0, "dBFS RMS of the noise"], "band": [None, 20, 20000, "[low, high] Hz or null"], "follow": [1.0, 0, 2, "0 steady, 1 follows the envelope"]}},
}

PRESETS: Dict[str, Dict[str, Any]] = {
    "heavier": {"doc": "Bigger and lower: pitch and body down, more weight, a little grit.",
                "chain": [{"fx": "pitch", "semitones": -4}, {"fx": "formant", "semitones": -3}, {"fx": "bass", "gain_db": 4, "hz": 120}, {"fx": "saturate", "drive": 0.25, "mix": 0.7}, {"fx": "transient", "attack": 0.3}]},
    "smaller": {"doc": "Lighter and quicker: pitch and body up, less low end.",
                "chain": [{"fx": "pitch", "semitones": 4}, {"fx": "formant", "semitones": 3}, {"fx": "lowcut", "hz": 200}, {"fx": "treble", "gain_db": 2}]},
    "distant": {"doc": "Far away: dull, quiet, roomy.",
                "chain": [{"fx": "highcut", "hz": 3500}, {"fx": "lowcut", "hz": 120}, {"fx": "reverb", "room": 0.8, "decay": 0.7, "damping": 0.6, "mix": 0.45}, {"fx": "gain", "db_value": -6}]},
    "metallic": {"doc": "Ringing, clangy.",
                 "chain": [{"fx": "ring", "hz": 740, "mix": 0.35}, {"fx": "mid", "hz": 2800, "gain_db": 5, "q": 2.5}, {"fx": "flanger", "hz": 0.2, "feedback": 0.6, "mix": 0.3}]},
    "ghostly": {"doc": "Thin, wavering, washed out.",
                "chain": [{"fx": "bandpass", "low_hz": 400, "high_hz": 6000}, {"fx": "chorus", "voices": 4, "hz": 0.4, "depth_ms": 6, "mix": 0.6}, {"fx": "vibrato", "hz": 4, "depth_ms": 2}, {"fx": "reverb", "room": 0.9, "decay": 0.8, "mix": 0.5}]},
    "crushed": {"doc": "Lo-fi, broken.",
                "chain": [{"fx": "bitcrush", "bits": 6, "downsample": 4, "mix": 0.8}, {"fx": "eq30", "preset": "radio"}, {"fx": "chop", "hz": 14, "duty": 0.7, "depth": 0.5}]},
    "huge_impact": {"doc": "Cinematic hit: slow tail, sub weight, room.",
                    "chain": [{"fx": "pitch", "semitones": -7, "keep_length": False}, {"fx": "transient", "attack": 0.6, "sustain": 0.3}, {"fx": "bass", "gain_db": 6, "hz": 90}, {"fx": "saturate", "drive": 0.4, "mix": 0.5}, {"fx": "reverb", "room": 0.7, "decay": 0.6, "mix": 0.3}]},
    "robot": {"doc": "Machine voice.",
              "chain": [{"fx": "ring", "hz": 120, "mix": 0.6}, {"fx": "bandpass", "low_hz": 250, "high_hz": 5000}, {"fx": "bitcrush", "bits": 10, "mix": 0.4}, {"fx": "chorus", "voices": 2, "mix": 0.3}]},
    "clean_up": {"doc": "Tidy a raw clip: trim, rumble and hiss off, level, fade.",
                 "chain": [{"fx": "trim"}, {"fx": "dc"}, {"fx": "lowcut", "hz": 40}, {"fx": "eq30", "preset": "hiss_cut"}, {"fx": "level"}, {"fx": "fade"}]},
    "impact_punch": {"doc": "Impact engine, punch layer: the click and crack of the hit, highs only, sharpened, short.",
                     "chain": [{"fx": "lowcut", "hz": 300}, {"fx": "transient", "attack": 0.8, "sustain": -0.5}, {"fx": "fade", "in_ms": 0.5, "out_ms": 90}]},
    "impact_body": {"doc": "Impact engine, body layer: the weight and thump, mids and lows, a little drive.",
                    "chain": [{"fx": "bandpass", "low_hz": 50, "high_hz": 1800}, {"fx": "transient", "attack": 0.2, "sustain": 0.3}, {"fx": "saturate", "drive": 0.3, "mix": 0.6}, {"fx": "fade", "out_ms": 160}]},
    "impact_tail": {"doc": "Impact engine, tail layer: the rumble and room after the hit, lows, stretched, reverberant.",
                    "chain": [{"fx": "lowcut", "hz": 30}, {"fx": "highcut", "hz": 2500}, {"fx": "stretch", "factor": 1.6}, {"fx": "reverb", "room": 0.7, "decay": 0.7, "damping": 0.6, "mix": 0.5}, {"fx": "fade", "out_ms": 300}]},
    "brute": {"doc": "Character: huge, slow, thick-throated. Pitch and body down, drive, a double.",
              "chain": [{"fx": "pitch", "semitones": -7}, {"fx": "formant", "semitones": -5}, {"fx": "intensity", "amount": 0.7}, {"fx": "doubles", "voices": 1, "detune_cents": 10, "delay_ms": 22, "mix": 0.35}, {"fx": "bass", "gain_db": 5, "hz": 160}, {"fx": "highcut", "hz": 7000}]},
    "fiend": {"doc": "Character: two voices from below, grit and a slow wobble.",
              "chain": [{"fx": "pitch", "semitones": -4}, {"fx": "formant", "semitones": -3}, {"fx": "doubles", "voices": 2, "detune_cents": 35, "delay_ms": 12, "mix": 0.6}, {"fx": "saturate", "drive": 0.5, "mix": 0.7}, {"fx": "vibrato", "hz": 3.5, "depth_ms": 2.5}, {"fx": "ring", "hz": 55, "mix": 0.25}]},
    "wraith": {"doc": "Character: thin, breathy, far, unstable.",
               "chain": [{"fx": "pitch", "semitones": 3}, {"fx": "formant", "semitones": 4}, {"fx": "bandpass", "low_hz": 500, "high_hz": 7000}, {"fx": "chorus", "voices": 4, "hz": 0.3, "depth_ms": 7, "mix": 0.6}, {"fx": "tremolo", "hz": 6.5, "depth": 0.35}, {"fx": "shimmer", "semitones": 12, "mix": 0.35}]},
    "automaton": {"doc": "Character: machine voice, ring and crush, flat and even.",
                  "chain": [{"fx": "compress", "threshold_db": -24, "ratio": 8, "attack_ms": 1, "release_ms": 40, "makeup_db": 6}, {"fx": "ring", "hz": 110, "mix": 0.55}, {"fx": "comb", "hz": 440, "feedback": 0.6, "mix": 0.3}, {"fx": "bitcrush", "bits": 9, "downsample": 2, "mix": 0.5}, {"fx": "bandpass", "low_hz": 250, "high_hz": 5500}]},
    "giant": {"doc": "Character: an octave down with the room of a hall.",
              "chain": [{"fx": "pitch", "semitones": -12}, {"fx": "formant", "semitones": -6}, {"fx": "sub", "hz": 40, "level_db": -16, "decay": 0.8}, {"fx": "reverb", "room": 0.9, "decay": 0.7, "damping": 0.6, "mix": 0.35}]},
    "imp": {"doc": "Character: small, quick, nasal.",
            "chain": [{"fx": "pitch", "semitones": 7}, {"fx": "formant", "semitones": 6}, {"fx": "mid", "hz": 2200, "gain_db": 5, "q": 1.5}, {"fx": "lowcut", "hz": 250}, {"fx": "stretch", "factor": 0.85}]},
    "operator": {"doc": "Character: over a radio, band-limited, compressed, a little static.",
                 "chain": [{"fx": "eq30", "preset": "radio"}, {"fx": "compress", "threshold_db": -20, "ratio": 6, "attack_ms": 2, "release_ms": 60, "makeup_db": 6}, {"fx": "saturate", "drive": 0.35, "mix": 0.5}, {"fx": "noise", "color": "white", "level_db": -34, "band": [1500, 6000], "follow": 0.3}]},
    "cavern": {"doc": "Character: deep in stone, long dark echoes.",
               "chain": [{"fx": "lowcut", "hz": 80}, {"fx": "echo", "time_ms": 180, "feedback": 0.45, "mix": 0.3, "damping_hz": 2500, "repeats": 6, "stereo_ms": 20}, {"fx": "reverb", "room": 1.0, "decay": 0.9, "damping": 0.7, "mix": 0.45}]},
    "transmute": {"doc": "Transmute: the main sound takes the loudness shape and colour of the reference source named 'model' (envelope_from + tone_from), all by plain processing.",
                  "chain": [{"fx": "envelope_from", "ref": "model", "amount": 1.0, "ms": 6}, {"fx": "tone_from", "ref": "model", "amount": 0.7}]},
    "rebuild": {"doc": "A new waveform from a clip, far from the original: pitch, body, scramble, width (what sfx_alter does).",
                "chain": [{"fx": "pitch", "semitones": -4, "keep_length": False}, {"fx": "formant", "semitones": 2}, {"fx": "decorrelate", "spread": 0.4, "knots": 128}, {"fx": "eq30", "gains_db": [0, 0, 0, 1, 2, 2, 1, 0, -1, -2, -2, -1, 0, 1, 2, 2, 1, 0, 0, -1, -1, 0, 1, 1, 0, 0, -1, -2, -3, -4]}]},
}


# ----------------------------------------------------------------------------------------------------------------------
# analysis: numbers for the agent
# ----------------------------------------------------------------------------------------------------------------------

def band_spectrum(x: np.ndarray, sr: int) -> List[float]:
    """Level in dB of each of the 30 EQ bands, relative to the loudest band."""
    m = x.mean(axis=1)
    spec = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
    freqs = np.fft.rfftfreq(len(m), 1 / sr)
    edges = [c / 2 ** (1 / 6) for c in EQ30_HZ] + [EQ30_HZ[-1] * 2 ** (1 / 6)]
    levels = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = (freqs >= lo) & (freqs < hi)
        levels.append(10 * math.log10(float(spec[sel].mean()) + 1e-12) if sel.any() else -120.0)
    top = max(levels)
    return [round(l - top, 1) for l in levels]


def correlation(a: np.ndarray, b: np.ndarray) -> float:
    """Best normalised cross-correlation at any lag, over both channels and their sum: 1 is the same waveform."""
    def one(u, v):
        n = min(len(u), len(v))
        u, v = u[:n] - u[:n].mean(), v[:n] - v[:n].mean()
        size = int(2 ** np.ceil(np.log2(2 * n)))
        cc = np.fft.irfft(np.fft.rfft(u, size) * np.conj(np.fft.rfft(v, size)), size)
        return float(np.abs(cc).max() / (np.linalg.norm(u) * np.linalg.norm(v) or 1))
    a, b = to_stereo(a), to_stereo(b)
    return max(one(a[:, 0], b[:, 0]), one(a[:, 1], b[:, 1]), one(a.sum(axis=1), b.sum(axis=1)))


def tone_match(a: np.ndarray, b: np.ndarray, sr: int) -> float:
    """1 when two sounds have the same overall colour (band spectrum), lower when not."""
    u, v = np.array(band_spectrum(a, sr)[6:]), np.array(band_spectrum(b, sr)[6:])
    u, v = u - u.mean(), v - v.mean()
    return float((u * v).sum() / (np.linalg.norm(u) * np.linalg.norm(v) or 1))


def analyze(x: np.ndarray, sr: int = SR, refs: Optional[Dict[str, np.ndarray]] = None) -> Dict[str, Any]:
    x = to_stereo(x)
    env = np.abs(x).max(axis=1)
    peak = float(env.max()) if env.size else 0.0
    m = x.mean(axis=1)
    spec = np.abs(np.fft.rfft(m * np.hanning(len(m))))
    freqs = np.fft.rfftfreq(len(m), 1 / sr)
    centroid = float((spec * freqs).sum() / (spec.sum() or 1))
    cum = np.cumsum(spec ** 2); cum /= max(cum[-1], 1e-12)
    rolloff = float(freqs[min(int(np.searchsorted(cum, 0.95)), len(freqs) - 1)]) if cum.size else 0.0
    thr = peak * amp(-42)
    nz = np.nonzero(env > thr)[0]
    start, end = (int(nz[0]), int(nz[-1])) if nz.size else (0, len(x) - 1)
    attack_i = int(np.argmax(env >= 0.9 * peak)) if peak > 0 else 0
    mid, side = (x[:, 0] + x[:, 1]) / 2, (x[:, 0] - x[:, 1]) / 2
    out = {
        "seconds": round(len(x) / sr, 3),
        "sounding_seconds": round((end - start + 1) / sr, 3),
        "leading_silence_ms": round(1000 * start / sr, 1),
        "trailing_silence_ms": round(1000 * (len(x) - 1 - end) / sr, 1),
        "peak_db": round(db(peak), 1),
        "rms_db": round(db(rms(x)), 1),
        "crest_db": round(db(peak) - db(rms(x)), 1),
        "attack_ms": round(1000 * (attack_i - start) / sr, 1),
        "centroid_hz": round(centroid),
        "rolloff95_hz": round(rolloff),
        "stereo_width": round(float(np.sqrt(np.mean(side ** 2) / max(np.mean(mid ** 2), 1e-12))), 3),
        "clipped": bool(float(np.mean(env >= 0.999)) > 0.002),
        "mono_compat": round(float(np.corrcoef(x[:, 0], x[:, 1])[0, 1]) if len(x) > 1 and x[:, 0].std() > 1e-6 and x[:, 1].std() > 1e-6 else 1.0, 3),
        "dc_offset": round(float(abs(x.mean())), 4),
        "band_db": band_spectrum(x, sr),
        "band_hz": EQ30_HZ,
    }
    if refs:
        out["against"] = {name: distance(x, r, sr) for name, r in refs.items()}
    return out


# The terms bar: a shipped sound must stay under this waveform similarity to every clip it came from (the projects'
# manifests use 0.22 for licensed packs; sfx_alter 0.25 for Noise Alchemy references).
SIMILARITY_BAR_PCT = 22.0


def envelope_match(a: np.ndarray, b: np.ndarray, sr: int) -> float:
    """How alike two loudness shapes are (0..1), at the better of two alignments: as they are, and attack to attack."""
    n = min(len(a), len(b))
    if n < 8:
        return 0.0
    ea, eb = envelope(to_stereo(a)[:n], sr, 8.0), envelope(to_stereo(b)[:n], sr, 8.0)
    def cc(u, v):
        u, v = u - u.mean(), v - v.mean()
        return float((u * v).sum() / (np.linalg.norm(u) * np.linalg.norm(v) or 1))
    direct = cc(ea, eb)
    sa, sb = int(np.argmax(ea)), int(np.argmax(eb))
    shift = sb - sa
    if shift > 0:
        aligned = cc(ea[:n - shift], eb[shift:])
    elif shift < 0:
        aligned = cc(ea[-shift:], eb[:n + shift])
    else:
        aligned = direct
    return max(0.0, direct, aligned)


def distance(x: np.ndarray, ref: np.ndarray, sr: int, bar_pct: float = SIMILARITY_BAR_PCT) -> Dict[str, Any]:
    """The meter against one source: waveform similarity (the figure the terms are judged by), tone and envelope
    similarity, level and length, all as percent, and whether the waveform figure is under the bar."""
    r = to_stereo(ref)
    corr = correlation(x, r)
    wav_pct = round(100 * max(corr, 0.0), 1)
    return {"correlation": round(corr, 3), "waveform_pct": wav_pct, "tone_pct": round(100 * max(tone_match(x, r, sr), 0.0), 1),
            "envelope_pct": round(100 * envelope_match(x, r, sr), 1), "rms_delta_db": round(db(rms(x)) - db(rms(r)), 1),
            "length_ratio": round(len(x) / max(len(r), 1), 3), "bar_pct": bar_pct, "under_bar": wav_pct <= bar_pct}


# ----------------------------------------------------------------------------------------------------------------------
# recipes
# ----------------------------------------------------------------------------------------------------------------------

class Bench:
    """Renders recipes. Sources may be file paths or arrays; `sr` is the working rate."""

    def __init__(self, sr: int = SR):
        self.sr = sr

    def _source(self, spec: Any, sources: Dict[str, Any]) -> np.ndarray:
        if isinstance(spec, np.ndarray):
            return to_stereo(spec)
        if isinstance(spec, dict) and "synth" in spec:
            from audio_materials import synth
            return to_stereo(synth(spec, self.sr))
        if isinstance(spec, str) and spec in sources:
            v = sources[spec]
            if isinstance(v, np.ndarray):
                return to_stereo(v)
            if isinstance(v, dict) and "synth" in v:
                from audio_materials import synth
                return to_stereo(synth(v, self.sr))
            return load(str(v), self.sr)[0]
        if isinstance(spec, str) and os.path.exists(spec):
            return load(spec, self.sr)[0]
        raise KeyError(f"unknown source {spec!r}")

    def chain(self, x: np.ndarray, steps: Sequence[Dict[str, Any]], rng: np.random.Generator, sources: Optional[Dict[str, Any]] = None) -> np.ndarray:
        for step in steps or []:
            step = dict(step)
            name = step.pop("fx")
            if name == "preset":
                x = self.chain(x, PRESETS[step["name"]]["chain"], rng, sources)
                continue
            if name not in CATALOG:
                raise KeyError(f"unknown effect {name!r}; see describe()")
            if "ref" in step and isinstance(step["ref"], str):
                step["ref"] = self._source(step["ref"], sources or {})
            x = CATALOG[name]["fn"](to_stereo(x), self.sr, rng, **step)
            if not np.all(np.isfinite(x)):
                raise ArithmeticError(f"{name} produced non-finite samples")
        return to_stereo(x)

    def _fit(self, x: np.ndarray, n: int, how: str, rng: np.random.Generator) -> np.ndarray:
        if how == "cut":
            return fit_length(x, n)
        if how == "stretch":
            return fit_length(fx_stretch(x, self.sr, rng, factor=n / max(len(x), 1)), n)
        if how == "loop":
            if len(x) >= n:
                return x[:n]
            xf = max(3, int(self.sr * 0.03))
            out = np.zeros((n, 2), dtype=np.float32)
            pos = 0
            while pos < n:
                seg = x.copy()
                if pos > 0 and xf < len(seg):
                    seg[:xf] *= np.linspace(0, 1, xf, dtype=np.float32)[:, None]
                    pos -= xf
                take = seg[:n - pos]
                out[pos:pos + len(take)] += take
                pos += len(seg)
            return out
        if how == "grains":
            # Granular re-synthesis: a texture of any length refitted to n with random, overlapping grains.
            grain = int(self.sr * 0.08)
            hop = grain // 2
            out = np.zeros((n + grain, 2), dtype=np.float32)
            win = np.hanning(grain).astype(np.float32)[:, None]
            src_n = len(x)
            for pos in range(0, n, hop):
                start = int(rng.integers(0, max(1, src_n - grain))) if src_n > grain else 0
                g = fit_length(x[start:start + grain], grain) * win
                out[pos:pos + grain] += g
            return (out[:n] / 1.0).astype(np.float32)
        raise ValueError(f"unknown fit {how!r}")

    def render(self, recipe: Dict[str, Any]) -> Tuple[np.ndarray, int]:
        sr = int(recipe.get("sr", self.sr))
        self.sr = sr
        seed = int(recipe.get("seed", 0))
        sources = recipe.get("sources", {})
        layers = recipe.get("layers") or [{"source": next(iter(sources))}]
        rendered: List[np.ndarray] = []
        raw: List[np.ndarray] = []
        for i, layer in enumerate(layers):
            rng = np.random.default_rng([seed, i])
            x = self._source(layer["source"], sources)
            raw.append(x)
            if layer.get("pitch"):
                x = fx_pitch(x, sr, rng, float(layer["pitch"]), bool(layer.get("keep_length", True)))
            rendered.append(self.chain(x, layer.get("chain", []), rng, sources))
        length = recipe.get("length", "main")
        if length == "main":
            n = len(rendered[0])
        elif length == "longest":
            n = max(len(r) for r in rendered)
        else:
            n = int(float(length) * sr)
        mixed: List[np.ndarray] = []
        for i, (layer, x) in enumerate(zip(layers, rendered)):
            rng = np.random.default_rng([seed, i, 99])
            if layer.get("reverse"):
                x = x[::-1].copy()
            rep = layer.get("repeat")
            if rep:   # the layer again and again: stutters, echoing hits, each repeat quieter and lower
                r = rep if isinstance(rep, dict) else {"count": int(rep)}
                count, gap, decay, drop = int(r.get("count", 3)), int(sr * float(r.get("ms", 120)) / 1000), float(r.get("decay_db", -4)), float(r.get("pitch_st", 0))
                out = np.zeros((len(x) + gap * count, 2), dtype=np.float32); out[:len(x)] = x
                tap = x
                for k in range(1, count + 1):
                    if drop:
                        tap = fx_pitch(tap, sr, rng, drop, keep_length=True)
                    seg = out[gap * k:gap * k + len(tap)]; seg += tap[:len(seg)] * amp(decay * k)
                x = out
            off = int(sr * float(layer.get("offset_ms", 0)) / 1000)
            if layer.get("align") == "onset" and mixed:   # the attack lands on the main layer's attack
                ref_env = envelope(mixed[0], sr, 2.0); own_env = envelope(x, sr, 2.0)
                off += int(np.argmax(ref_env)) - int(np.argmax(own_env))
            if off > 0:
                x = np.pad(x, ((off, 0), (0, 0)))
            elif off < 0:
                x = x[-off:]
            x = self._fit(x, n, layer.get("fit", "cut"), rng)
            band = layer.get("band")
            if band:
                x = fx_bandpass(x, sr, rng, band[0], band[1])
            follow = layer.get("follow")
            if follow:
                f = follow if isinstance(follow, dict) else {"layer": follow}
                target = mixed[int(f.get("layer", 0))] if int(f.get("layer", 0)) < len(mixed) else rendered[int(f.get("layer", 0))]
                e = envelope(fit_length(target, n), sr, float(f.get("ms", 10.0)))
                e = (e / e.max()) ** float(f.get("amount", 1.0))
                x = (x * e[:, None]).astype(np.float32)
            duck = layer.get("duck")
            if duck:   # the opposite of follow: this layer gets out of the way while another plays
                d = duck if isinstance(duck, dict) else {"layer": duck}
                target = mixed[int(d.get("layer", 0))] if int(d.get("layer", 0)) < len(mixed) else rendered[int(d.get("layer", 0))]
                e = envelope(fit_length(target, n), sr, float(d.get("ms", 30.0))); e = e / e.max()
                x = (x * (1 - float(d.get("depth", 0.8)) * e)[:, None]).astype(np.float32)
            if layer.get("doppler"):   # passing by: pitch and level rise then fall
                dp = layer["doppler"] if isinstance(layer["doppler"], dict) else {}
                semi, depth = float(dp.get("semitones", 4)), float(dp.get("depth", 0.6))
                x = fx_glide(x, sr, rng, start_st=semi, end_st=-semi, curve=1.0)
                t = np.linspace(-1, 1, len(x), dtype=np.float32)
                x = (x * (1 - depth * t * t)[:, None]).astype(np.float32)
            if layer.get("auto_gain_db") is not None and mixed:   # sit a set distance under the main layer
                target_rms = rms(mixed[0]) * amp(float(layer["auto_gain_db"]))
                x = x * (target_rms / max(rms(x), 1e-6))
            x = x * amp(float(layer.get("gain_db", 0.0)))
            sweep = layer.get("pan_sweep")
            if sweep:   # moves across the field over its length
                sw = sweep if isinstance(sweep, dict) else {}
                a, b = float(sw.get("from", -1)), float(sw.get("to", 1))
                pos = (np.linspace(a, b, len(x), dtype=np.float32) + 1) / 2
                x = np.stack([x[:, 0] * np.cos(pos * np.pi / 2) * 1.414, x[:, 1] * np.sin(pos * np.pi / 2) * 1.414], axis=1).astype(np.float32)
            elif layer.get("pan") is not None:
                x = fx_pan(x, sr, rng, float(layer["pan"]))
            mixed.append(x.astype(np.float32))
        self.last_layer_share = _shares(mixed, [l.get("source") if isinstance(l.get("source"), str) else "synth" for l in layers])
        blend = recipe.get("blend") or {"mode": "sum"}
        mode = blend.get("mode", "sum")
        rng = np.random.default_rng([seed, 7777])
        if mode == "sum" or len(mixed) == 1:
            y = np.sum(mixed, axis=0).astype(np.float32)
        elif mode == "crossfade":
            a, b = mixed[0], mixed[1]
            t = np.clip((np.arange(n) / sr - float(blend.get("start_s", 0.0))) / max(float(blend.get("seconds", n / sr)), 1e-3), 0, 1).astype(np.float32)
            y = (a * np.sqrt(1 - t)[:, None] + b * np.sqrt(t)[:, None]) + np.sum(mixed[2:], axis=0) if len(mixed) > 2 else a * np.sqrt(1 - t)[:, None] + b * np.sqrt(t)[:, None]
        elif mode == "morph":
            # Spectral morph: magnitudes interpolate between the first two layers, the first layer's timing (phase) kept.
            a, b = mixed[0], mixed[1]
            amount = float(blend.get("amount", 0.5))
            y = np.empty_like(a)
            for c in range(2):
                A, B = _stft(a[:, c]), _stft(b[:, c])
                mag = np.abs(A) ** (1 - amount) * np.abs(B) ** amount
                y[:, c] = _istft(mag * np.exp(1j * np.angle(A)), n)
            if len(mixed) > 2:
                y = y + np.sum(mixed[2:], axis=0)
        else:
            raise ValueError(f"unknown blend {mode!r}")
        y = self.chain(y, recipe.get("master", []), rng, sources)
        return np.clip(y, -1, 1).astype(np.float32), sr

    def apply_preset(self, x: np.ndarray, name: str, seed: int = 0, master: Optional[Sequence[Dict[str, Any]]] = None) -> np.ndarray:
        rng = np.random.default_rng([seed])
        y = self.chain(x, PRESETS[name]["chain"], rng)
        return self.chain(y, master if master is not None else [{"fx": "level"}, {"fx": "fade"}], rng)


def impact_recipe(punch: Any, body: Any = None, tail: Any = None, *, seed: int = 0, sources: Optional[Dict[str, Any]] = None,
                  gains_db: Sequence[float] = (0.0, -2.0, -6.0), offsets_ms: Sequence[float] = (0.0, 6.0, 25.0),
                  pitches: Sequence[float] = (0.0, -4.0, -9.0)) -> Dict[str, Any]:
    """An impact engine recipe: three layers, punch, body and tail, each from its own source (or all from one), each with
    its own gain, time offset and pitch, on the impact_* presets. Edit anything afterwards; it is an ordinary recipe."""
    body = body if body is not None else punch
    tail = tail if tail is not None else punch
    roles = (("impact_punch", punch), ("impact_body", body), ("impact_tail", tail))
    layers = []
    for (preset, src), g, o, p in zip(roles, gains_db, offsets_ms, pitches):
        layer = {"source": src, "gain_db": float(g), "offset_ms": float(o), "fit": "cut", "chain": [{"fx": "preset", "name": preset}]}
        if p:
            layer["pitch"] = float(p)
            layer["keep_length"] = preset != "impact_tail"   # the tail may lengthen like tape
        layers.append(layer)
    return {"seed": int(seed), "length": "longest", "sources": sources or {}, "layers": layers, "blend": {"mode": "sum"},
            "master": [{"fx": "level", "rms_db": -19, "peak_db": -1}, {"fx": "fade", "in_ms": 1, "out_ms": 120}]}


BOOM_ROLES = ("impact_punch", "impact_body", "impact_tail", "heavier", "distant", "metallic")


def boom_recipe(sources: Sequence[Any], *, seed: int = 0, layers: int = 4, gain_range: Sequence[float] = (-14.0, 0.0),
                offset_range_ms: Sequence[float] = (0.0, 60.0), pitch_range: Sequence[float] = (-7.0, 5.0), pan_spread: float = 0.6,
                roles: Sequence[str] = BOOM_ROLES, source_names: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """A boom: several sounds stacked with a randomizer. Each layer draws a source, a role preset, gain, offset, pitch and
    pan from the seed, so one number re-rolls the whole stack and the same number brings it back. The first layer is the
    loudest and sits at time zero, so the stack still has one clear hit."""
    rng = np.random.default_rng([int(seed), 0xB00])
    srcs = list(sources)
    if not srcs:
        raise ValueError("boom needs at least one source")
    out = []
    for i in range(max(1, int(layers))):
        src = srcs[i % len(srcs)] if i < len(srcs) else srcs[int(rng.integers(0, len(srcs)))]
        role = roles[i % 3] if i < 3 else roles[int(rng.integers(0, len(roles)))]
        layer = {"source": src, "fit": "cut", "chain": [{"fx": "preset", "name": role}],
                 "gain_db": 0.0 if i == 0 else round(float(rng.uniform(*gain_range)), 1),
                 "offset_ms": 0.0 if i == 0 else round(float(rng.uniform(*offset_range_ms)), 1)}
        p = round(float(rng.uniform(*pitch_range)) * 2) / 2
        if p and (i > 0 or abs(p) >= 2):
            layer["pitch"] = p
            layer["keep_length"] = role != "impact_tail"
        if i > 0 and pan_spread > 0:
            layer["pan"] = round(float(rng.uniform(-pan_spread, pan_spread)), 2)
        out.append(layer)
    return {"seed": int(seed), "length": "longest", "sources": source_names or {}, "layers": out, "blend": {"mode": "sum"},
            "master": [{"fx": "compress", "threshold_db": -14, "ratio": 3, "attack_ms": 4, "release_ms": 90}, {"fx": "level", "rms_db": -19, "peak_db": -1}, {"fx": "fade", "in_ms": 1, "out_ms": 150}]}


def handoff(recipe: Dict[str, Any], out_dir: str, *, seeds: Sequence[int] = (1, 2, 3), stem: str = "variant", sr_out: int = 0,
            provenance: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Render the recipe under several seeds into out_dir as WAVs for tuning by hand in an outside editor (one you upload
    to), with a handoff.json beside them naming the recipe, the seeds and the sources' license tiers. The caller decides
    whether the sources may leave the machine: `provenance` is {source name: {"tier": ..., "origin": ...}}; sources whose
    tier is direct or restricted (Function Loops, Tao & Sound, Omni) are listed under "licensed_sources" so the decision
    is informed. Returns what was written."""
    os.makedirs(out_dir, exist_ok=True)
    bench = Bench(int(recipe.get("sr", SR)))
    written = []
    for seed in seeds:
        r = dict(recipe, seed=int(seed))
        y, sr = bench.render(r)
        if sr_out and sr_out != sr:
            y, sr = resample(y, sr, sr_out), sr_out
        path = os.path.join(out_dir, f"{stem}_seed{int(seed)}.wav")
        save(path, y, sr)
        written.append({"path": path, "seed": int(seed), "analysis": analyze(y, sr)})
    licensed = {n: p for n, p in (provenance or {}).items() if str(p.get("tier", "")) in ("direct", "restricted")}
    note = {"recipe": {k: v for k, v in recipe.items() if k != "sources"}, "sources": {k: (v if isinstance(v, str) else "<array>") for k, v in (recipe.get("sources") or {}).items()},
            "provenance": provenance or {}, "licensed_sources": licensed, "variants": written,
            "about": "Variants of one recipe for tuning by hand. Bring the tuned file back with audio_bench.py takeback (or the GUI) so it is checked against its sources and recorded."}
    json.dump(note, open(os.path.join(out_dir, "handoff.json"), "w", encoding="utf-8"), indent=1)
    return note


def takeback(tuned_path: str, handoff_dir: str, *, max_corr: float = 0.25) -> Dict[str, Any]:
    """Check a hand-tuned file against the hand-off it came from: finite, not clipped, level and length noted, and its
    correlation with every variant that went out (so a tuned file that came back unchanged is caught) and with the
    original sources when they were files. Returns the analysis with 'ok' and the reasons when not."""
    note = json.load(open(os.path.join(handoff_dir, "handoff.json"), encoding="utf-8"))
    x, sr = load(tuned_path)
    refs: Dict[str, np.ndarray] = {}
    for v in note.get("variants", []):
        if os.path.exists(v["path"]):
            refs[os.path.basename(v["path"])] = load(v["path"], sr)[0]
    for name, src in (note.get("sources") or {}).items():
        if isinstance(src, str) and os.path.exists(src):
            refs["source:" + name] = load(src, sr)[0]
    a = analyze(x, sr, refs or None)
    reasons = []
    if a["clipped"]:
        reasons.append("clipped")
    if a["peak_db"] < -30:
        reasons.append("very quiet")
    for name, r in (a.get("against") or {}).items():
        if name.startswith("source:") and r["correlation"] > max_corr:
            reasons.append(f"too close to {name[7:]} (correlation {r['correlation']})")
    a["ok"] = not reasons
    a["reasons"] = reasons
    a["tuned_path"] = os.path.abspath(tuned_path)
    return a


def _shares(mixed: Sequence[np.ndarray], names: Sequence[Any]) -> List[Dict[str, Any]]:
    """What each layer contributes to the mix, by energy: the explanation a person reads instead of guessing."""
    energies = [float(np.sum(np.square(m))) for m in mixed]
    total = sum(energies) or 1.0
    return [{"layer": i, "source": str(n), "share": round(e / total, 3)} for i, (n, e) in enumerate(zip(names, energies))]


def validate(recipe: Dict[str, Any]) -> List[str]:
    """Problems in a recipe before anything renders: unknown effects or presets, parameters out of range, missing sources,
    follows that point nowhere, blends that need two layers. Empty when it is fine."""
    issues: List[str] = []
    sources = recipe.get("sources") or {}
    layers = recipe.get("layers") or []
    if not layers:
        issues.append("no layers")
    for i, l in enumerate(layers):
        src = l.get("source")
        if not (isinstance(src, np.ndarray) or (isinstance(src, dict) and "synth" in src) or (isinstance(src, str) and (src in sources or os.path.exists(src)))):
            issues.append(f"layer {i}: source {src!r} is not a named source, a file or a synth")
        if l.get("fit") not in (None, "cut", "stretch", "loop", "grains"):
            issues.append(f"layer {i}: fit {l.get('fit')!r} is not cut, stretch, loop or grains")
        f = l.get("follow")
        if f:
            target = int((f if isinstance(f, dict) else {"layer": f}).get("layer", 0))
            if target >= len(layers) or target == i:
                issues.append(f"layer {i}: follows layer {target}, which does not exist or is itself")
        for where, steps in (("layer %d" % i, l.get("chain") or []), ):
            issues += _validate_chain(where, steps)
    issues += _validate_chain("master", recipe.get("master") or [])
    mode = (recipe.get("blend") or {}).get("mode", "sum")
    if mode not in ("sum", "crossfade", "morph"):
        issues.append(f"blend {mode!r} is not sum, crossfade or morph")
    if mode in ("crossfade", "morph") and len(layers) < 2:
        issues.append(f"blend {mode} needs two layers")
    return issues


def _validate_chain(where: str, steps: Sequence[Dict[str, Any]]) -> List[str]:
    out: List[str] = []
    for j, step in enumerate(steps):
        name = step.get("fx")
        if name == "preset":
            if step.get("name") not in PRESETS:
                out.append(f"{where} step {j}: unknown preset {step.get('name')!r}")
            continue
        if name not in CATALOG:
            out.append(f"{where} step {j}: unknown effect {name!r}")
            continue
        for p, v in step.items():
            if p in ("fx", "_bypass"):
                continue
            spec = CATALOG[name]["params"].get(p)
            if spec is None:
                out.append(f"{where} step {j} ({name}): no parameter {p!r}")
            elif isinstance(v, (int, float)) and not isinstance(v, bool) and spec[1] is not None and spec[2] is not None and not (spec[1] <= v <= spec[2]):
                out.append(f"{where} step {j} ({name}): {p} = {v} is outside {spec[1]}..{spec[2]}")
    return out


def check_render(x: np.ndarray, sr: int = SR) -> List[str]:
    """Problems in a rendered sound: clipping, DC offset, silence, too quiet, inaudible content, mono cancellation."""
    a = analyze(x, sr)
    out: List[str] = []
    if a["clipped"]:
        out.append("clipped")
    if a["dc_offset"] > 0.01:
        out.append(f"dc offset {a['dc_offset']}")
    if a["peak_db"] < -40:
        out.append("silent or nearly")
    else:
        # loudness where the sound sounds: a short knock padded with silence is not quiet (whole-file RMS says it is)
        env = np.abs(to_stereo(x)).max(axis=1)
        live = env > float(env.max()) * amp(-30) if env.size else env
        rms_live = db(rms(to_stereo(x)[live])) if live.any() else a["rms_db"]
        if rms_live < -36:
            out.append(f"very quiet ({round(rms_live, 1)} dBFS RMS while sounding)")
    if a["band_db"][0] > -6 or a["band_db"][1] > -6:
        out.append("most energy below 25 Hz: inaudible rumble")
    if a["mono_compat"] < 0.0:
        out.append(f"channels cancel in mono (correlation {a['mono_compat']})")
    return out


def breed(a: Dict[str, Any], b: Dict[str, Any], *, ratio: float = 0.5, mutation: float = 0.15, seed: int = 0) -> Dict[str, Any]:
    """Offspring of two recipes: layers drawn from both (the first layer from the dominant parent), every numeric
    parameter in every chain mutated within its catalog range by `mutation`, sources merged. Lineage recorded under
    "parents". Deterministic from the seed, so a line of descent can be replayed."""
    rng = np.random.default_rng([seed, 0xB12ED])
    dom, rec = (a, b) if ratio >= 0.5 else (b, a)
    layers = [json.loads(json.dumps(dom["layers"][0]))] if dom.get("layers") else []
    pool = list(dom.get("layers", [])[1:]) + list(rec.get("layers", []))
    rng.shuffle(pool)
    keep = max(1, int(round(len(pool) * (0.5 + abs(ratio - 0.5)))))
    layers += [json.loads(json.dumps(l)) for l in pool[:keep]]

    def mutate_chain(steps):
        for step in steps:
            if step.get("fx") in CATALOG:
                for p, spec in CATALOG[step["fx"]]["params"].items():
                    if isinstance(spec[0], (int, float)) and not isinstance(spec[0], bool) and spec[1] is not None and spec[2] is not None and rng.uniform() < mutation * 3:
                        cur = float(step.get(p, spec[0]))
                        span = spec[2] - spec[1]
                        step[p] = round(float(np.clip(cur + rng.normal(0, mutation * span), spec[1], spec[2])), 3)
    for l in layers:
        mutate_chain(l.get("chain", []))
        if rng.uniform() < mutation:
            l["gain_db"] = round(float(np.clip(l.get("gain_db", 0) + rng.normal(0, 3), -30, 6)), 1)
        if rng.uniform() < mutation:
            l["pitch"] = round(float(np.clip(l.get("pitch", 0) + rng.normal(0, 2), -12, 12)) * 2) / 2
    master = json.loads(json.dumps(dom.get("master") or []))
    mutate_chain(master)
    sources = dict(rec.get("sources") or {}); sources.update(dom.get("sources") or {})
    return {"seed": int(seed), "length": dom.get("length", "longest"), "sources": sources, "layers": layers, "blend": dom.get("blend") or {"mode": "sum"}, "master": master,
            "parents": [a.get("name") or "a", b.get("name") or "b"], "ratio": ratio, "mutation": mutation}


def catalog() -> Dict[str, Any]:
    """Effects, parameters (default, min, max, meaning), presets, EQ presets and the recipe schema, as plain data."""
    fx = {name: {"doc": e["doc"], "params": {p: {"default": v[0], "min": v[1], "max": v[2], "meaning": v[3]} for p, v in e["params"].items()}} for name, e in CATALOG.items()}
    return {
        "effects": fx,
        "presets": {k: {"doc": v["doc"], "chain": v["chain"]} for k, v in PRESETS.items()},
        "eq30_presets": EQ30_PRESETS,
        "eq30_hz": EQ30_HZ,
        "recipe": {
            "seed": "int; every random choice (decorrelate, grains, noise) comes from it, so a recipe renders the same twice",
            "sr": "sample rate, default 44100",
            "length": "'main' (first layer's rendered length), 'longest', or seconds",
            "sources": {"<name>": "file path (or an array from Python)"},
            "layers": [{"source": "<name>", "chain": ["effect steps: {\"fx\": name, ...params} or {\"fx\": \"preset\", \"name\": preset}"],
                        "gain_db": "level of this layer in the mix", "pan": "-1..1 or omit", "offset_ms": "start later",
                        "pitch": "semitones, applied before the chain (keep_length true by default)",
                        "fit": "how a layer meets the length: cut (default), stretch, loop, grains (granular re-synthesis, for textures)",
                        "band": "[low_hz, high_hz]: keep only this band of the layer (place a texture in a frequency range)",
                        "follow": {"layer": "index of the layer whose loudness shape this one follows (texture layering)", "amount": "0..2", "ms": "envelope smoothing"},
                        "duck": {"layer": "index of the layer this one gets out of the way of", "depth": "0..1", "ms": "smoothing"},
                        "align": "'onset': the attack lands on the main layer's attack (added to offset_ms)",
                        "auto_gain_db": "level relative to the main layer's RMS, e.g. -8 (then gain_db on top)",
                        "repeat": {"count": "repeats", "ms": "gap", "decay_db": "per repeat", "pitch_st": "drop per repeat"},
                        "pan_sweep": {"from": "-1..1", "to": "-1..1"}, "doppler": {"semitones": "rise then fall", "depth": "level dip at the ends"}, "reverse": "bool"}],
            "meter": "analyze(x, sr, refs) gives 'against' per source: waveform_pct (the figure the terms are judged by), tone_pct, envelope_pct, rms_delta_db, length_ratio, bar_pct and under_bar; SIMILARITY_BAR_PCT is the shipping bar",
            "blend": {"mode": "sum | crossfade (start_s, seconds) | morph (amount) between the first two layers"},
            "master": ["effect steps applied to the mix; usually ends with level and fade"],
        },
        "analysis_fields": list(analyze(np.zeros((4410, 2), dtype=np.float32)).keys()) + ["against.<ref>: correlation, tone_match, rms_delta_db, length_ratio"],
        "impact_engine": {"doc": "impact_recipe(punch, body, tail): three layers on the impact_punch / impact_body / impact_tail presets, each with gain_db, offset_ms and pitch",
                          "example": impact_recipe("hit", seed=1)},
        "boom": {"doc": "boom_recipe(sources, seed, layers): stacked layers with randomized role, gain, offset, pitch and pan from the seed; change the seed to re-roll",
                 "roles": list(BOOM_ROLES), "example": boom_recipe(["hit", "rumble"], seed=1)},
        "synth_sources": {"doc": "a source may be a dict instead of a path: synthesized from parameters, no clip and no license (audio_materials)",
                          "kinds": __import__("audio_materials").catalog(),
                          "example": {"sources": {"hit": {"synth": "material", "material": "crystal", "size": 0.7, "force": 0.6, "seed": 1}, "step": {"synth": "footstep", "surface": "gravel", "weight": 0.8}}}},
        "validate": "validate(recipe) lists problems before rendering (unknown effects, ranges, missing sources, bad follows/blends); check_render(audio) lists problems after (clipping, DC, silence, inaudible rumble, mono cancellation); the server's /api/render returns both",
        "breed": "breed(recipe_a, recipe_b, ratio, mutation, seed): offspring recipe with layers from both and mutated parameters; 'parents' records lineage",
        "explain": "render() keeps Bench.last_layer_share: each layer's energy share of the mix; the agent's 'report' lists its reasons",
    }


def describe() -> str:
    return json.dumps(catalog(), indent=1)


# ----------------------------------------------------------------------------------------------------------------------
# self-test and command line
# ----------------------------------------------------------------------------------------------------------------------

def _synthetic(sr: int = SR, seconds: float = 1.2, seed: int = 1) -> np.ndarray:
    """A click, a decaying tone and some noise: enough to exercise every effect."""
    rng = np.random.default_rng(seed)
    n = int(sr * seconds)
    t = np.arange(n) / sr
    tone = np.sin(2 * np.pi * 220 * t) * np.exp(-t * 4) * 0.5
    click = np.zeros(n); click[int(0.05 * sr):int(0.05 * sr) + 40] = np.linspace(1, 0, 40)
    noise = rng.standard_normal((n, 2)).astype(np.float32) * 0.05 * np.exp(-t * 3)[:, None]
    x = np.stack([tone + click, tone * 0.9 + click], axis=1).astype(np.float32) + noise
    return fx_level(x, sr, rng)


def selftest() -> int:
    sr = SR
    x = _synthetic(sr)
    bench = Bench(sr)
    fails = []
    for name, e in CATALOG.items():
        params = {p: v[0] for p, v in e["params"].items() if v[0] is not None}
        if name in ("tone_from", "envelope_from"):
            params["ref"] = fx_pitch(x, sr, np.random.default_rng(3), 5)
        if name == "eq30":
            params = {"preset": "presence"}
        try:
            y = e["fn"](x, sr, np.random.default_rng(1), **params)
            ok = y.ndim == 2 and y.shape[1] == 2 and np.all(np.isfinite(y)) and float(np.abs(y).max()) > 1e-4
            if name not in ("echo", "reverb", "stretch", "trim", "length", "shimmer") and len(y) != len(x):
                ok = False
            y2 = e["fn"](x, sr, np.random.default_rng(1), **params)
            if not np.allclose(y, y2):
                ok = False; name += " (not repeatable)"
            print(f"{'ok  ' if ok else 'FAIL'} {name:14} {len(y) / sr:5.2f} s  peak {db(float(np.abs(y).max())):6.1f} dB")
            if not ok:
                fails.append(name)
        except Exception as ex:
            print(f"FAIL {name}: {ex}")
            fails.append(name)
    for p in PRESETS:
        try:
            if p == "transmute":
                y, _ = bench.render({"seed": 2, "sources": {"main": x, "model": fx_pitch(x, sr, np.random.default_rng(3), -5)}, "layers": [{"source": "main", "chain": [{"fx": "preset", "name": "transmute"}]}]})
                assert np.all(np.isfinite(y)) and len(y) > 0
                print(f"ok   preset {p}")
                continue
            y = bench.apply_preset(x, p, seed=2)
            assert np.all(np.isfinite(y)) and len(y) > 0
            print(f"ok   preset {p}")
        except Exception as ex:
            print(f"FAIL preset {p}: {ex}"); fails.append("preset " + p)
    tex = np.random.default_rng(5).standard_normal((int(sr * 0.4), 2)).astype(np.float32) * 0.2
    recipe = {"seed": 11, "sr": sr, "length": "main", "sources": {"main": x, "tex": tex},
              "layers": [{"source": "main", "chain": [{"fx": "preset", "name": "heavier"}]},
                         {"source": "tex", "gain_db": -12, "fit": "grains", "band": [2000, 9000], "follow": {"layer": 0, "amount": 1.0}, "chain": [{"fx": "decorrelate"}]}],
              "master": [{"fx": "reverb", "mix": 0.15}, {"fx": "level"}, {"fx": "fade"}]}
    try:
        y, _ = bench.render(recipe)
        y2, _ = bench.render(recipe)
        a = analyze(y, sr, refs={"main": x})
        ok = np.all(np.isfinite(y)) and np.allclose(y, y2) and abs(a["rms_db"] + 19) < 1.0 and a["against"]["main"]["correlation"] < 0.9
        print(f"{'ok  ' if ok else 'FAIL'} texture-layer recipe: {a['seconds']} s, rms {a['rms_db']} dB, width {a['stereo_width']}, vs main: waveform {a['against']['main']['waveform_pct']}% tone {a['against']['main']['tone_pct']}%")
        if not ok:
            fails.append("recipe")
        for mode in ("crossfade", "morph"):
            r2 = dict(recipe, blend={"mode": mode, "amount": 0.5, "seconds": 0.8})
            y3, _ = bench.render(r2)
            assert np.all(np.isfinite(y3))
            print(f"ok   blend {mode}")
    except Exception as ex:
        print(f"FAIL recipe: {ex}"); fails.append("recipe")
    try:
        from audio_materials import MATERIALS, SURFACES, material_hit, footstep
        for m in MATERIALS:
            y = material_hit(m, size=0.6, force=0.6, seed=1)
            assert np.all(np.isfinite(y)) and float(np.abs(y).max()) > 0.1, m
        for sf in SURFACES:
            y = footstep(sf, weight=0.7, seed=1)
            assert np.all(np.isfinite(y)) and float(np.abs(y).max()) > 0.1, sf
        print(f"ok   materials ({len(MATERIALS)}) and footsteps ({len(SURFACES)})")
        r = {"seed": 3, "sources": {"hit": {"synth": "material", "material": "metal", "size": 0.5, "force": 0.8}, "tex": tex},
             "layers": [{"source": "hit", "chain": [{"fx": "preset", "name": "impact_body"}]}, {"source": "tex", "gain_db": -12, "fit": "grains", "follow": {"layer": 0}, "chain": []}],
             "master": [{"fx": "level"}, {"fx": "fade"}]}
        bad = validate(r); assert not bad, bad
        y, _ = bench.render(r); assert np.all(np.isfinite(y))
        print(f"ok   synth-source recipe, shares {[s['share'] for s in bench.last_layer_share]}, checks {check_render(y, sr) or 'clean'}")
        bad = validate({"layers": [{"source": "nope", "chain": [{"fx": "pitch", "semitones": 99}, {"fx": "nothing"}]}], "blend": {"mode": "morph"}})
        assert len(bad) >= 4, bad
        print(f"ok   validate catches {len(bad)} problems in a broken recipe")
        r3 = {"seed": 4, "length": "longest", "sources": {"main": x, "tex": tex},
              "layers": [{"source": "main", "chain": []},
                         {"source": "tex", "fit": "grains", "align": "onset", "auto_gain_db": -10, "duck": {"layer": 0, "depth": 0.7}, "repeat": {"count": 2, "ms": 150, "decay_db": -6, "pitch_st": -2}, "pan_sweep": {"from": -0.8, "to": 0.8}, "reverse": True, "doppler": {"semitones": 3, "depth": 0.5}, "chain": []}],
              "master": [{"fx": "level"}]}
        assert not validate(r3), validate(r3)
        y3, _ = bench.render(r3); assert np.all(np.isfinite(y3))
        m = analyze(y3, sr, {"main": x})["against"]["main"]
        print(f"ok   layer features; meter vs main: waveform {m['waveform_pct']}% tone {m['tone_pct']}% envelope {m['envelope_pct']}% (bar {m['bar_pct']}%, under: {m['under_bar']})")
        child = breed(dict(r, name="metal"), dict(recipe, name="layered"), ratio=0.6, mutation=0.2, seed=5)
        assert not validate(child), validate(child)
        y2, _ = bench.render(child); assert np.all(np.isfinite(y2))
        print(f"ok   breed: {len(child['layers'])} layers from {child['parents']}")
    except Exception as ex:
        print(f"FAIL materials/validate/breed: {ex}"); fails.append("materials")
    print("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}")
    return 0 if not fails else 1


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="AAMT Audio Bench: recipe-driven, deterministic sound shaping")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("describe")
    a = sub.add_parser("analyze"); a.add_argument("wav"); a.add_argument("--ref", action="append", default=[])
    r = sub.add_parser("apply"); r.add_argument("recipe"); r.add_argument("out")
    p = sub.add_parser("preset"); p.add_argument("name"); p.add_argument("inp"); p.add_argument("out"); p.add_argument("--seed", type=int, default=0)
    h = sub.add_parser("handoff", help="render seed variants of a recipe for tuning by hand in an outside editor"); h.add_argument("recipe"); h.add_argument("out_dir"); h.add_argument("--seeds", default="1,2,3"); h.add_argument("--stem", default="variant")
    t = sub.add_parser("takeback", help="check a hand-tuned file against the hand-off it came from"); t.add_argument("tuned"); t.add_argument("handoff_dir")
    sub.add_parser("selftest")
    args = ap.parse_args(argv)
    if args.cmd == "describe":
        print(describe()); return 0
    if args.cmd == "selftest":
        return selftest()
    if args.cmd == "analyze":
        x, sr = load(args.wav)
        refs = {os.path.basename(f): load(f, sr)[0] for f in args.ref}
        print(json.dumps(analyze(x, sr, refs or None), indent=1)); return 0
    if args.cmd == "apply":
        recipe = json.load(open(args.recipe, encoding="utf-8"))
        base = os.path.dirname(os.path.abspath(args.recipe))
        recipe["sources"] = {k: (v if os.path.isabs(v) else os.path.join(base, v)) for k, v in recipe.get("sources", {}).items()}
        y, sr = Bench().render(recipe)
        save(args.out, y, sr)
        print(json.dumps(analyze(y, sr), indent=1)); return 0
    if args.cmd == "preset":
        x, sr = load(args.inp)
        save(args.out, Bench(sr).apply_preset(x, args.name, args.seed), sr); return 0
    if args.cmd == "handoff":
        recipe = json.load(open(args.recipe, encoding="utf-8"))
        base = os.path.dirname(os.path.abspath(args.recipe))
        recipe["sources"] = {k: (v if os.path.isabs(v) else os.path.join(base, v)) for k, v in recipe.get("sources", {}).items()}
        note = handoff(recipe, args.out_dir, seeds=[int(s) for s in args.seeds.split(",") if s.strip()], stem=args.stem)
        print(json.dumps({"variants": [v["path"] for v in note["variants"]], "licensed_sources": note["licensed_sources"]}, indent=1)); return 0
    if args.cmd == "takeback":
        a = takeback(args.tuned, args.handoff_dir)
        print(json.dumps(a, indent=1)); return 0 if a["ok"] else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
