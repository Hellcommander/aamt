"""Material-based sound synthesis: a hit, scrape or footstep on a material, from parameters alone. No clip, no model, so
what comes out is the project's own sound with no license behind it.

Modal synthesis: a material is a set of partials (frequency ratios, relative levels, damping), struck by an excitation
(a click for hard materials, a noise burst for soft ones), with size scaling the fundamental and the decay and force the
drive and the brightness. A few materials add their own layer: slime bubbles, chitin clicks, plasma noise, void sub.
Everything is seeded, so the same parameters give the same sound.

    from audio_materials import material_hit, MATERIALS
    x = material_hit("crystal", size=0.7, force=0.6, seconds=1.2, seed=3)       # (samples, 2) float32 at 44100
    x = footstep("mud", weight=0.8, seed=1)

In a bench recipe a synthesized source is a dict instead of a path:
    "sources": {"hit": {"synth": "material", "material": "crystal", "size": 0.7, "force": 0.6}}
    "sources": {"step": {"synth": "footstep", "surface": "mud", "weight": 0.8}}
"""
from __future__ import annotations

import math
import zlib
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

SR = 44100

# ratios: partial frequencies over the fundamental; levels: dB per partial; q: how long partials ring (higher = longer);
# base_hz: fundamental at size 0.5; excite: "click" (hard) or "burst" (soft noise); tilt: dB/octave colour; extra: a
# material's own layer.
MATERIALS: Dict[str, Dict[str, Any]] = {
    "wood":     {"ratios": [1, 2.2, 3.1, 4.5, 6.3], "levels": [0, -6, -10, -16, -22], "q": 18, "base_hz": 240, "excite": "click", "tilt": -3, "extra": None},
    "bone":     {"ratios": [1, 2.7, 4.1, 5.9], "levels": [0, -4, -9, -15], "q": 28, "base_hz": 520, "excite": "click", "tilt": -1, "extra": None},
    "crystal":  {"ratios": [1, 2.76, 5.4, 8.93, 13.3], "levels": [0, -3, -6, -10, -14], "q": 400, "base_hz": 1400, "excite": "click", "tilt": 2, "extra": None},
    "glass":    {"ratios": [1, 2.32, 4.25, 6.63], "levels": [0, -5, -9, -14], "q": 260, "base_hz": 1900, "excite": "click", "tilt": 1, "extra": None},
    "metal":    {"ratios": [1, 1.5, 2.98, 4.4, 6.1, 7.7], "levels": [0, -2, -5, -8, -12, -16], "q": 600, "base_hz": 620, "excite": "click", "tilt": 0, "extra": None},
    "stone":    {"ratios": [1, 1.7, 2.9, 4.2], "levels": [0, -7, -12, -18], "q": 12, "base_hz": 180, "excite": "burst", "tilt": -4, "extra": "grit"},
    "mushroom": {"ratios": [1, 1.9, 3.3], "levels": [0, -8, -16], "q": 6, "base_hz": 120, "excite": "burst", "tilt": -6, "extra": "squelch"},
    "slime":    {"ratios": [1, 1.6, 2.4], "levels": [0, -9, -18], "q": 4, "base_hz": 90, "excite": "burst", "tilt": -8, "extra": "bubbles"},
    "chitin":   {"ratios": [1, 2.1, 3.4, 5.2, 7.9], "levels": [0, -5, -8, -12, -16], "q": 40, "base_hz": 900, "excite": "click", "tilt": 3, "extra": "clicks"},
    "flesh":    {"ratios": [1, 1.8, 2.9], "levels": [0, -10, -18], "q": 5, "base_hz": 140, "excite": "burst", "tilt": -7, "extra": "squelch"},
    "astral":   {"ratios": [1, 1.498, 2.0, 2.997, 4.0, 5.04], "levels": [0, -4, -6, -9, -12, -15], "q": 900, "base_hz": 330, "excite": "click", "tilt": 1, "extra": "shimmer"},
    "void":     {"ratios": [1, 1.33, 1.78], "levels": [0, -6, -12], "q": 80, "base_hz": 55, "excite": "burst", "tilt": -9, "extra": "sub"},
    "plasma":   {"ratios": [1, 2.01, 3.02, 4.03], "levels": [0, -4, -8, -12], "q": 30, "base_hz": 260, "excite": "burst", "tilt": 4, "extra": "crackle"},
}

SURFACES: Dict[str, Dict[str, Any]] = {
    "mud":    {"material": "slime", "grit": 0.2, "tone": 0.4, "squelch": 0.9},
    "gravel": {"material": "stone", "grit": 1.0, "tone": 0.3, "squelch": 0.0},
    "stone":  {"material": "stone", "grit": 0.4, "tone": 0.8, "squelch": 0.0},
    "wood":   {"material": "wood", "grit": 0.2, "tone": 1.0, "squelch": 0.0},
    "metal":  {"material": "metal", "grit": 0.1, "tone": 1.0, "squelch": 0.0},
    "grass":  {"material": "mushroom", "grit": 0.6, "tone": 0.2, "squelch": 0.2},
    "snow":   {"material": "mushroom", "grit": 0.8, "tone": 0.1, "squelch": 0.1},
    "sand":   {"material": "stone", "grit": 0.9, "tone": 0.1, "squelch": 0.0},
    "bone":   {"material": "bone", "grit": 0.3, "tone": 0.9, "squelch": 0.0},
    "chitin": {"material": "chitin", "grit": 0.2, "tone": 1.0, "squelch": 0.0},
}


def _env(n: int, attack: float, decay: float, sr: int = SR) -> np.ndarray:
    t = np.arange(n) / sr
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return (a * np.exp(-t / max(decay, 1e-3))).astype(np.float32)


def _resonator(excite: np.ndarray, hz: float, q: float, sr: int = SR) -> np.ndarray:
    """A two-pole resonator (one partial) driven by the excitation."""
    from scipy import signal

    hz = min(max(hz, 20.0), sr * 0.45)
    w0 = 2 * math.pi * hz / sr
    r = math.exp(-math.pi * hz / (q * sr))   # q cycles to decay by e^-pi
    b = [1 - r]
    a = [1, -2 * r * math.cos(w0), r * r]
    return signal.lfilter(b, a, excite).astype(np.float32)


def _excitation(kind: str, n: int, force: float, rng: np.random.Generator, sr: int = SR) -> np.ndarray:
    if kind == "click":
        ms = 0.4 + 2.5 * (1 - force)                # a harder hit is a shorter click
        k = max(4, int(sr * ms / 1000))
        x = np.zeros(n, dtype=np.float32)
        x[:k] = (rng.standard_normal(k) * 0.5 + np.hanning(k) * 2).astype(np.float32) * np.linspace(1, 0, k) ** 0.5
        return x
    ms = 8 + 40 * (1 - force)
    k = max(8, int(sr * ms / 1000))
    x = np.zeros(n, dtype=np.float32)
    x[:k] = rng.standard_normal(k).astype(np.float32) * np.hanning(k)
    return x


def _extra(kind: Optional[str], n: int, size: float, force: float, rng: np.random.Generator, sr: int = SR) -> np.ndarray:
    t = np.arange(n) / sr
    if kind is None:
        return np.zeros(n, dtype=np.float32)
    if kind == "grit":        # loose particles: a decaying burst of tiny clicks
        x = np.zeros(n, dtype=np.float32)
        count = int(40 + 160 * force)
        pos = (rng.exponential(0.06 + 0.15 * size, count) * sr).astype(int)
        x[pos[pos < n]] += rng.uniform(0.2, 1.0, (pos < n).sum()).astype(np.float32)
        return x * np.exp(-t / (0.15 + 0.3 * size))
    if kind in ("squelch", "bubbles"):   # wet: noise through a swept resonance, bubbles as short rising blips
        noise = rng.standard_normal(n).astype(np.float32)
        sweep = (300 + 900 * size) * (1 + 0.5 * np.sin(2 * np.pi * (2 + 6 * force) * t))
        out = np.zeros(n, dtype=np.float32)
        step = 256
        from scipy import signal
        for i in range(0, n, step):
            hz = float(np.clip(sweep[i], 60, sr * 0.4)); w0 = 2 * math.pi * hz / sr; r = 0.97
            out[i:i + step] = signal.lfilter([1 - r], [1, -2 * r * math.cos(w0), r * r], noise[i:i + step])
        out = out * np.exp(-t / (0.2 + 0.4 * size)) * 3
        if kind == "bubbles":
            for _ in range(int(3 + 8 * force)):
                start = int(rng.uniform(0.02, 0.35) * sr); length = int(sr * rng.uniform(0.02, 0.06))
                if start + length < n:
                    f0 = rng.uniform(300, 900) * (1.2 - size)
                    seg = np.sin(2 * np.pi * f0 * (1 + 1.5 * np.linspace(0, 1, length) ** 2) * np.arange(length) / sr) * np.hanning(length)
                    out[start:start + length] += seg.astype(np.float32) * 0.8
        return out
    if kind == "clicks":      # chitin: a few hard clicks after the hit
        x = np.zeros(n, dtype=np.float32)
        for _ in range(int(2 + 5 * force)):
            p = int(rng.uniform(0.01, 0.12) * sr)
            if p + 40 < n:
                x[p:p + 40] += (rng.standard_normal(40) * np.hanning(40)).astype(np.float32) * 1.5
        return x
    if kind == "shimmer":     # astral: slow detuned high partials fading in
        out = np.zeros(n, dtype=np.float32)
        for k in range(4):
            f = (1800 + 600 * k) * (1 + 0.004 * rng.standard_normal())
            out += (np.sin(2 * np.pi * f * t) * np.exp(-t / (0.8 + 0.8 * size)) * (1 - np.exp(-t / 0.12)) * 0.15).astype(np.float32)
        return out
    if kind == "sub":         # void: a sine two octaves under the fundamental, slow
        f = 55 * (0.7 + 0.6 * size) / 2
        return (np.sin(2 * np.pi * f * t) * np.exp(-t / (0.6 + 1.2 * size)) * 0.9).astype(np.float32)
    if kind == "crackle":     # plasma: bright noise crackle with a hum
        noise = rng.standard_normal(n).astype(np.float32)
        gate = (rng.uniform(0, 1, n) < 0.02 + 0.08 * force).astype(np.float32)
        hum = np.sin(2 * np.pi * 120 * t) * 0.3
        return ((noise * gate * 2 + hum) * np.exp(-t / (0.3 + 0.5 * size))).astype(np.float32)
    return np.zeros(n, dtype=np.float32)


def material_hit(material: str, *, size: float = 0.5, force: float = 0.5, seconds: Optional[float] = None, seed: int = 0, sr: int = SR) -> np.ndarray:
    """A single strike on the material. size 0 small .. 1 large (pitch down, decay up); force 0 soft .. 1 hard."""
    m = MATERIALS[material]
    rng = np.random.default_rng([seed, zlib.crc32(material.encode()) & 0xFFFF])   # hash() changes per process; crc32 repeats
    size = float(np.clip(size, 0, 1)); force = float(np.clip(force, 0, 1))
    f0 = m["base_hz"] * 2 ** ((0.5 - size) * 2.5)              # +-1.25 octaves over the size range
    q = m["q"] * (0.6 + 0.8 * size)
    decay = min(4.0, 0.08 + (q / 150.0) * (0.5 + size))
    secs = seconds or float(np.clip(decay * 2.5, 0.25, 4.0))
    n = int(sr * secs)
    excite = _excitation(m["excite"], n, force, rng, sr)
    out = np.zeros(n, dtype=np.float32)
    for ratio, level in zip(m["ratios"], m["levels"]):
        detune = 1 + 0.002 * rng.standard_normal()
        out += _resonator(excite, f0 * ratio * detune, q * (0.6 + 0.4 * rng.uniform()), sr) * 10 ** ((level - 3 * (1 - force) * ratio) / 20)
    out += _extra(m["extra"], n, size, force, rng, sr) * (0.6 + 0.6 * force)
    # force adds drive (harder hits distort a little) and brightness; tilt is the material's colour
    out = np.tanh(out * (1 + 2 * force)) / (1 + 1.2 * force)
    out *= _env(n, 0.0005, max(decay, 0.05) * 1.5, sr) ** 0.3
    # Mono by nature: widen in the recipe with width or decorrelate if wanted (an inter-channel delay would cancel in mono).
    stereo = np.stack([out, out], axis=1)
    peak = float(np.abs(stereo).max()) or 1.0
    return (stereo / peak * 0.9).astype(np.float32)


def footstep(surface: str, *, weight: float = 0.5, speed: float = 0.5, seed: int = 0, sr: int = SR) -> np.ndarray:
    """One footstep on a surface: heel then toe, the surface's material under it, grit and squelch as the surface has."""
    s = SURFACES[surface]
    rng = np.random.default_rng([seed, 0x57E9])
    heel = material_hit(s["material"], size=0.3 + 0.4 * weight, force=0.4 + 0.5 * weight, seconds=0.5, seed=seed, sr=sr)
    toe = material_hit(s["material"], size=0.2 + 0.3 * weight, force=0.3 + 0.4 * weight, seconds=0.4, seed=seed + 1, sr=sr) * 0.7
    gap = int(sr * (0.05 + 0.09 * (1 - speed)))
    n = len(heel) + gap
    out = np.zeros((n, 2), dtype=np.float32)
    out[:len(heel)] += heel * s["tone"]
    out[gap:gap + len(toe)] += toe * s["tone"]
    if s["grit"] > 0:
        g = _extra("grit", n, 0.3 + 0.4 * weight, 0.5 + 0.5 * weight, rng, sr) * s["grit"] * 0.6
        out += np.stack([g, np.roll(g, int(sr * 0.0005))], axis=1)
    if s["squelch"] > 0:
        q = _extra("squelch", n, 0.4, 0.5 + 0.5 * weight, rng, sr) * s["squelch"] * 0.5
        out += np.stack([q, q], axis=1)
    peak = float(np.abs(out).max()) or 1.0
    return (out / peak * 0.9).astype(np.float32)


def synth(spec: Dict[str, Any], sr: int = SR) -> np.ndarray:
    """A synthesized source from a recipe's source dict: {"synth": "material", ...} or {"synth": "footstep", ...}."""
    kind = spec.get("synth")
    seed = int(spec.get("seed", 0))
    if kind == "material":
        return material_hit(str(spec.get("material", "stone")), size=float(spec.get("size", 0.5)), force=float(spec.get("force", 0.5)),
                            seconds=spec.get("seconds"), seed=seed, sr=sr)
    if kind == "footstep":
        return footstep(str(spec.get("surface", "stone")), weight=float(spec.get("weight", 0.5)), speed=float(spec.get("speed", 0.5)), seed=seed, sr=sr)
    raise ValueError(f"unknown synth {kind!r}; use material or footstep")


def catalog() -> Dict[str, Any]:
    return {"material": {"doc": "a strike on a material: material, size 0..1, force 0..1, seconds (optional), seed", "materials": list(MATERIALS)},
            "footstep": {"doc": "one footstep on a surface: surface, weight 0..1, speed 0..1, seed", "surfaces": list(SURFACES)}}
