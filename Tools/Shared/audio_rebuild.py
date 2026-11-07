"""Rebuild a sound from library clips so it stays far from every clip: the production step behind sfx_alter, shared.

Plain, deterministic processing on the bench's effects: a pitch move (never small), a layer from a second and third
clip, a random all-pass in each channel (the stereo width), an EQ curve, the first clip's loudness shape put back by a
chosen amount, then trim and level. Every try is checked against every clip (normalized cross-correlation at any lag,
both channels and their sum) and only tries under `max_corr` are candidates; the listener (audio_listener) picks among
them with the first clip as the tone reference, or the spectrum match does when no listener is given. Settings escalate
in three stages when nothing gets far enough. Seeds come from the sound's name and the try number, so a rebuild repeats.

    from audio_rebuild import rebuild
    y, info = rebuild("km_palisade", [clip0, clip1], n_samples, purpose, listener=Listener(), max_corr=0.22)

Folder mode for AAMT sidecars (.wav + .meta.json with "references"): every sound whose references include a pack that
bars AI tools is rebuilt from the allowed references when its main clip is allowed, else from its own clips (a licensed
derivative, in-game only), and the sidecar is updated.

    python audio_rebuild.py <folder with .meta.json sidecars> [--only a,b] [--max-corr 0.25] [--tries 12] [--no-listen] [--write]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import zlib
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio_bench as bench  # noqa: E402

SR = bench.SR
# tone: how far the result is pulled back to the lead clip's colour (0 none, 1 fully); tilt_db: a little random tilt for
# variety; attack_ms: the first milliseconds of the hit kept unscrambled; glue: light compression for density;
# level_db: None keeps the lead clip's loudness, a number sets dBFS RMS.
DEFAULTS = {"steps": [-5, -4, -3, 3, 4, 5, -6, 6], "layer": 0.45, "spread": 0.35, "knots": 64, "eq_db": 1.5, "reshape": 1.0,
            "tone": 0.8, "attack_ms": 8.0, "glue": 0.25, "level_db": None}


def harder(cfg: Dict[str, Any], times: int = 1) -> Dict[str, Any]:
    far = [-8 - times, -7 - times, 7 + times, 8 + times]
    return dict(cfg, steps=far + list(cfg["steps"]), layer=max(cfg["layer"], 0.5 + 0.3 * (times - 1)),
                spread=max(cfg["spread"], 0.5 + 0.2 * (times - 1)), knots=cfg["knots"] * 2 * times, reshape=min(cfg.get("reshape", 1.0), 1.0 - 0.3 * times))


def repitch(x: np.ndarray, semitones: float) -> np.ndarray:
    """Tape-style pitch move by polyphase resampling (anti-aliased), not linear interpolation: no added hiss or aliasing."""
    from fractions import Fraction
    from scipy import signal

    rate = 2 ** (semitones / 12)
    fr = Fraction(1 / rate).limit_denominator(2000)      # new length / old length
    return signal.resample_poly(x, fr.numerator, fr.denominator, axis=0).astype(np.float32)


def allpass_and_curve(x: np.ndarray, rng: np.random.Generator, cfg: Dict[str, Any], harder_by: int = 1) -> np.ndarray:
    """Random phase per channel (a new waveform with the same spectrum) with a gentle random tilt. The lowest band keeps
    its phase, so the weight of a hit stays where it was, and the phase steps are smooth across frequency."""
    n = len(x)
    size = int(2 ** np.ceil(np.log2(n + 2048)))
    bins = size // 2 + 1
    freqs = np.fft.rfftfreq(size, 1 / SR)
    tilt = cfg["eq_db"] * rng.uniform(-1, 1)
    curve = (10 ** (tilt * np.log2(np.maximum(freqs, 30.0) / 1000.0) / 20)).astype(np.float32)
    keep_low = np.clip((freqs - 60.0) / 120.0, 0.0, 1.0)      # phase untouched below 60 Hz, fully random above 180 Hz
    out = np.zeros_like(x)
    k = int(cfg["knots"] * harder_by)
    grid = np.log1p(np.arange(bins)) / np.log1p(bins - 1)
    depth = float(cfg.get("depth", 1.0))     # how far the phase moves (1 = fully random above 180 Hz)
    shared = np.interp(grid, np.linspace(0, 1, k), rng.uniform(-np.pi, np.pi, k)) * keep_low * depth
    for c in range(2):
        own = np.interp(grid, np.linspace(0, 1, k), rng.uniform(-np.pi, np.pi, k)) * keep_low * depth
        spec = np.fft.rfft(x[:, c], size) * curve * np.exp(1j * (shared + own * cfg["spread"]))
        out[:, c] = np.fft.irfft(spec, size)[:n]
    return out


def candidate(name: str, clips: Sequence[np.ndarray], n: int, cfg: Dict[str, Any], t: int, tag: str = "") -> Tuple[np.ndarray, int]:
    rng = np.random.default_rng(zlib.crc32(f"{name}/{tag}{t}".encode()))
    steps = cfg["steps"]
    step = steps[(zlib.crc32(name.encode()) + t) % len(steps)]
    x = bench.fit_length(repitch(clips[0], step), n)
    for k, c in enumerate(clips[1:3]):
        layer = bench.fit_length(repitch(c, step + rng.choice([-7, 5, 7, 12])), n)
        x = x + layer * (cfg["layer"] / (k + 1)) * (bench.rms(x) / max(bench.rms(layer), 1e-6))
    y = allpass_and_curve(x, rng, cfg, 1 + t // 4)
    y = bench.fx_envelope_from(y, SR, rng, ref=x, amount=float(cfg.get("reshape", 1.0)), ms=4.0)
    # the colour of the lead clip comes back (the scramble and the layers had moved it), by plain spectral matching
    if cfg.get("tone", 0) > 0:
        y = bench.fx_tone_from(y, SR, rng, ref=clips[0], amount=float(cfg["tone"]))
    # the first milliseconds of the hit are the mix before scrambling: the attack stays sharp (a sliver of a second)
    y = bench.fit_length(y, n)
    a_ms = float(cfg.get("attack_ms", 0))
    if a_ms > 0:
        k = min(int(SR * a_ms / 1000), n // 4)
        if k > 8:
            w = (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, k, dtype=np.float32)))[:, None]   # 0 -> 1
            lead_start = int(np.argmax(np.abs(x).max(axis=1) > 0.05 * float(np.abs(x).max())))
            s0 = max(0, lead_start)
            seg = slice(s0, min(n, s0 + k))
            kk = seg.stop - seg.start
            y[seg] = x[seg] * (1 - w[:kk]) + y[seg] * w[:kk]
    if cfg.get("glue", 0) > 0:
        y = bench.fx_intensity(y, SR, rng, amount=float(cfg["glue"]))
    level = cfg.get("level_db")
    target = float(level) if level is not None else bench.db(bench.rms(clips[0]))
    y = bench.fx_fade(bench.fx_level(y, SR, rng, rms_db=max(-30.0, min(-6.0, target)), peak_db=-1), SR, rng, in_ms=1, out_ms=120)
    return y, int(step)


def spectrum_match(a: np.ndarray, b: np.ndarray) -> float:
    return bench.tone_match(a, b, SR)


def rebuild(name: str, clips: Sequence[np.ndarray], n: int, purpose: str = "", listener=None, *, max_corr: float = 0.25,
            tries: int = 12, cfg: Optional[Dict[str, Any]] = None) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
    """The best rebuild under max_corr, or (None, info) when no try of any stage gets far enough from the clips."""
    cfg = dict(DEFAULTS, **(cfg or {}))
    clips = [bench.to_stereo(c) for c in clips if c is not None and len(c) > 8]
    if not clips:
        return None, {"error": "no clips"}
    fitted = [bench.fit_length(c, n) for c in clips]
    for tag, c in (("", cfg), ("hard", harder(cfg)), ("harder", harder(cfg, 2))):
        passing = []
        for t in range(tries):
            y, step = candidate(name, clips, n, c, t, tag)
            cr = max(bench.correlation(y, f) for f in fitted)
            if cr > max_corr:
                continue
            passing.append((y, spectrum_match(y, fitted[0]), cr, step))
            if listener is None and passing[-1][1] >= 0.9:
                break
        if not passing:
            continue
        if listener is None:
            y, s, cr, step = max(passing, key=lambda p: p[1])
            return y, {"stage": tag or "plain", "corr": round(cr, 3), "spectrum": round(s, 3), "semitones": step, "candidates": len(passing)}
        i, scores = listener.pick([p[0] for p in passing], SR, purpose, tone_ref=fitted[0])
        y, s, cr, step = passing[i]
        return y, {"stage": tag or "plain", "corr": round(cr, 3), "spectrum": round(s, 3), "semitones": step, "candidates": len(passing), "listen": scores[i]}
    return None, {"error": f"no try under correlation {max_corr}", "stage": "harder"}


# ---- unique mode: the program side ------------------------------------------------------------------------------------
# rebuild() aims at one figure (waveform correlation) and puts the lead clip's colour, loudness shape and attack back on
# purpose, so its results keep that clip's fingerprint. render_unique() is the plain-DSP program the audio agent drives
# when a sound must be its own sound against EVERY clip (waveform, tone and envelope): it renders exactly the plan it
# is given, nothing random beyond the plan's seed. The agent (audio_agent.Agent.rebuild_unique) reads the judge's
# figures and the listener's score and decides the next plan; this function never decides anything.
#
# plan = {"layers": [{"clip": i, "role": "punch"|"body"|"tail", "pitch": st, "gain_db": g, "offset_ms": o,
#                     "stretch": 1.0, "reverse": False, "lowcut": hz, "highcut": hz, "length_ms": ms}, ...],
#         "scramble": {"knots": 64, "spread": 0.5, "eq_db": 1.5}, "shape": 0..1 (loudness shape of the MIX put back),
#         "tone": 0..1 (colour of the MIX put back), "eq30": [30 dB], "transient": {"attack": a, "sustain": s},
#         "attack_ms": ms (unscrambled start of the mix), "width": min stereo width, "glue": 0..1, "level_db": -19,
#         "echo": {"time_ms", "feedback", "mix"} (a slapback after a hit), "flicker": {"hz", "depth"} (irregular movement)}

def width_of(x: np.ndarray) -> float:
    x = bench.to_stereo(x)
    mid, side = (x[:, 0] + x[:, 1]) / 2, (x[:, 0] - x[:, 1]) / 2
    return float(np.sqrt(np.mean(side ** 2) / max(np.mean(mid ** 2), 1e-12)))


def mono_corr(x: np.ndarray) -> float:
    x = bench.to_stereo(x)
    a, b = x[:, 0] - x[:, 0].mean(), x[:, 1] - x[:, 1].mean()
    return float((a * b).sum() / ((np.linalg.norm(a) * np.linalg.norm(b)) or 1.0))


def _lead_trim(x: np.ndarray) -> np.ndarray:
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    if peak <= 1e-4:
        return x
    return x[int(np.argmax(np.max(np.abs(x), axis=1) > 0.02 * peak)):]


def render_unique(clips: Sequence[np.ndarray], n: int, plan: Dict[str, Any], seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    mix = np.zeros((n, 2), dtype=np.float32)
    for L in plan["layers"]:
        if L.get("synth"):
            # our own material, no clip behind it (audio_materials: modal synthesis), e.g. a new attack for a hit
            import audio_materials as mat
            sp = L["synth"]
            x = bench.to_stereo(mat.material_hit(sp["material"], size=float(sp.get("size", 0.5)), force=float(sp.get("force", 0.6)),
                                                 seed=int(sp.get("seed", 0)), sr=SR))
        else:
            x = bench.to_stereo(clips[int(L["clip"])])
        if L.get("reverse"):
            x = x[::-1].copy()
        if L.get("pitch"):
            x = repitch(x, float(L["pitch"]))
        if L.get("shift_hz"):
            x = bench.fx_freq_shift(x, SR, None, hz=float(L["shift_hz"]))
        if abs(float(L.get("stretch", 1.0)) - 1.0) > 1e-3:
            x = bench.fx_stretch(x, SR, rng, factor=float(L["stretch"]))
        if not L.get("keep_lead"):     # a repair's base keeps its own timing
            x = _lead_trim(x)
        if L.get("attack_cut_ms"):
            # this layer hands its first ms to another layer's attack: faded in over that time instead of striking
            k = min(len(x), max(8, int(SR * float(L["attack_cut_ms"]) / 1000)))
            s0 = int(np.argmax(np.abs(x).max(axis=1) > 0.05 * float(np.abs(x).max() or 1)))
            ramp = np.ones(len(x), dtype=np.float32); ramp[:s0] = 0.0
            ramp[s0:s0 + k] = (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, len(ramp[s0:s0 + k]), dtype=np.float32))) ** 2
            x = x * ramp[:, None]
        if L.get("lowcut"):
            x = bench.fx_lowcut(x, SR, rng, hz=float(L["lowcut"]))
        if L.get("highcut"):
            x = bench.fx_highcut(x, SR, rng, hz=float(L["highcut"]))
        if L.get("length_ms"):
            k = max(8, int(SR * float(L["length_ms"]) / 1000))
            x = bench.fx_fade(x[:k], SR, rng, in_ms=0.5, out_ms=min(60.0, float(L["length_ms"]) / 3))
        off = max(0, int(SR * float(L.get("offset_ms", 0)) / 1000))
        if off >= n or len(x) == 0:
            continue
        seg = x[:n - off]
        r = bench.rms(seg)
        if r <= 1e-6:
            continue
        mix[off:off + len(seg)] += seg * (bench.amp(-20.0 + float(L.get("gain_db", 0.0))) / r)
    s = plan.get("scramble", {})
    depth = float(s.get("depth", 1.0))      # 0 = phase untouched (a repair whose waveform figure is already far under)
    if depth <= 0 and not float(s.get("eq_db", 1.5)):
        y = mix.copy()
    else:
        y = allpass_and_curve(mix, rng, {"eq_db": float(s.get("eq_db", 1.5)), "knots": int(s.get("knots", 64)),
                                         "spread": float(s.get("spread", 0.5)), "depth": depth})
    y = bench.fit_length(y, n)
    if plan.get("shape", 0) > 0:
        y = bench.fx_envelope_from(y, SR, rng, ref=mix, amount=float(plan["shape"]), ms=4.0)
    if plan.get("tone", 0) > 0:
        # tone_frames: the mix is time-aligned, so its colour is matched moment by moment (older plans: one average)
        y = bench.fx_tone_from(y, SR, rng, ref=mix, amount=float(plan["tone"]), per_frame=bool(plan.get("tone_frames", False)))
    if plan.get("eq30"):
        y = bench.fx_eq30(y, SR, rng, gains_db=plan["eq30"])
    tr = plan.get("transient") or {}
    if tr.get("attack") or tr.get("sustain"):
        y = bench.fx_transient(y, SR, rng, attack=float(tr.get("attack", 0)), sustain=float(tr.get("sustain", 0)))
    g = float(plan.get("decay_gamma", 1.0))
    if abs(g - 1.0) > 1e-3:
        # the decay curve itself: the loudness shape raised to a power (above 1 dies away faster, below 1 rings longer),
        # attack kept, so a hit whose fall-off matches a clip gets a fall-off of its own
        e = bench.envelope(y, SR, 8.0)
        e = e / max(float(e.max()), 1e-9)
        y = (y * np.clip(np.maximum(e, 1e-4) ** (g - 1.0), 0.05, 4.0)[:, None]).astype(np.float32)
    ec = plan.get("echo") or {}
    if ec.get("mix"):
        y = bench.fit_length(bench.fx_echo(y, SR, rng, time_ms=float(ec.get("time_ms", 90)), feedback=float(ec.get("feedback", 0.25)),
                                           mix=float(ec["mix"]), damping_hz=float(ec.get("damping_hz", 4000)), repeats=4, stereo_ms=12.0), n)
    fl = plan.get("flicker") or {}
    if fl.get("depth"):
        y = bench.fx_flicker(y, SR, rng, hz=float(fl.get("hz", 9.0)), depth=float(fl["depth"]))
    a_ms = float(plan.get("attack_ms", 0))
    if a_ms > 0:
        k = min(int(SR * a_ms / 1000), n // 4)
        if k > 8:
            s0 = int(np.argmax(np.abs(mix).max(axis=1) > 0.05 * float(np.abs(mix).max() or 1)))
            seg = slice(s0, min(n, s0 + k)); kk = seg.stop - seg.start
            w = (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, kk, dtype=np.float32)))[:, None]
            y[seg] = mix[seg] * (1 - w) + y[seg] * w
    target = float(plan.get("width", 0.0))
    if target > 0 and width_of(y) < target:
        if width_of(y) < 0.05 and plan.get("widen_mid"):
            # (near) one signal twice: keep that signal as the mid, exactly, and add a side made from an all-pass copy
            y = bench.fx_side_from_mid(y, SR, rng, width=1.05 * target)
        elif width_of(y) < 0.05:   # (older plans) give the channels their own phase first
            y = bench.fx_decorrelate(y, SR, rng, spread=0.6, knots=96)
        w = width_of(y)
        if w < target:
            y = bench.fx_width(y, SR, rng, amount=min(3.0, 1.08 * target / max(w, 0.02)))
    for _ in range(6):   # channels must never cancel in mono: narrow until they stop
        if mono_corr(y) >= 0.05:
            break
        y = bench.fx_width(y, SR, rng, amount=0.7)
    if plan.get("glue", 0) > 0:
        y = bench.fx_intensity(y, SR, rng, amount=float(plan["glue"]))
    y = bench.fit_length(y, n)
    y = bench.fx_lowcut(y, SR, rng, hz=float(plan.get("floor_hz", 30.0)), order=4)   # pitch moves must never leave inaudible sub rumble
    y = bench.fx_level(y, SR, rng, rms_db=float(plan.get("level_db", -19.0)), peak_db=-1)
    return bench.fx_fade(y, SR, rng, in_ms=1, out_ms=min(120.0, 1000.0 * n / SR / 4)).astype(np.float32)


def unique_judge(clips: Sequence[np.ndarray], limits: Sequence[Dict[str, float]], mark: float = 1.0):
    """A measuring function for the agent: per clip, each figure over that clip's own limit, divided by the sound's
    pass mark (so 1.0 is the line whatever the mark). limits[i] is {"waveform_pct", "tone_pct", "envelope_pct"} for
    clips[i]; mark is the measured worst-of-all-clips line (sfx_unique.pass_mark), 1.0 when unknown. It measures; it
    decides nothing."""
    refs = [bench.to_stereo(c) for c in clips]
    mark = max(float(mark), 1e-6)
    def judge(y: np.ndarray) -> Dict[str, Any]:
        rows = []
        for i, r in enumerate(refs):
            d = bench.distance(y, r, SR)
            ratios = {k: d[k] / max(limits[i][k], 1e-6) / mark for k in ("waveform_pct", "tone_pct", "envelope_pct")}
            rows.append({"clip": i, "figures": {k: d[k] for k in ratios}, "ratios": ratios, "over": max(ratios.values())})
        worst = max(rows, key=lambda r: r["over"])
        return {"over": worst["over"], "worst": worst, "rows": rows, "width": width_of(y), "problems": bench.check_render(y, SR)}
    return judge


# ---- folder mode ------------------------------------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder"); ap.add_argument("--only", default=""); ap.add_argument("--max-corr", type=float, default=0.25)
    ap.add_argument("--tries", type=int, default=12); ap.add_argument("--no-listen", action="store_true"); ap.add_argument("--write", action="store_true")
    ap.add_argument("--out", default="", help="folder for the results when not writing in place"); ap.add_argument("--force", action="store_true", help="rebuild even sounds whose references are all allowed (a retry with more tries)"); ap.add_argument("--agent", action="store_true", help="let the audio agent decide clip order, pitch direction, layering and shape from the purpose")
    a = ap.parse_args(argv)
    from audio_asset_library import AudioLibrary, ai_allowed, load_asset_audio

    lib = AudioLibrary(); lib.load()
    by_inner = {r.inner: r for r in lib.records}
    tails = {}
    for r in lib.records:
        tails.setdefault(r.inner.split("/")[-1].lower(), r)

    def find(ref):
        rec = lib.get(ref.get("id") or "")
        if rec is not None:
            return rec
        inner = (ref.get("inner") or ref.get("clip") or "").replace("\\", "/")
        return by_inner.get(inner) or tails.get(inner.split("/")[-1].lower())

    listener = None
    if not a.no_listen:
        from audio_listener import Listener
        listener = Listener()
    only = set(filter(None, a.only.split(",")))
    done = skipped = failed = 0
    for meta in sorted(glob.glob(os.path.join(a.folder, "**", "*.meta.json"), recursive=True)):
        name = os.path.basename(meta)[:-len(".meta.json")]
        if only and name not in only:
            continue
        j = json.load(open(meta, encoding="utf-8"))
        used = set(j.get("used_ids") or [])
        refs = [r for r in j.get("references", []) if isinstance(r, dict) and (not used or r.get("id") in used)]
        if not refs or (not a.force and all(ai_allowed(r.get("pack", ""), r.get("inner", "")) for r in refs)):
            skipped += 1
            continue
        main_free = ai_allowed(refs[0].get("pack", ""), refs[0].get("inner", ""))
        use = [r for r in refs if ai_allowed(r.get("pack", ""), r.get("inner", ""))] if main_free else refs
        clips = []
        for r in use:
            rec = find(r)
            if rec is None:
                continue
            x, _ = load_asset_audio(rec, sr=SR, max_seconds=8.0)
            clips.append(bench.fx_trim(bench.to_stereo(x), SR, None))
            r["id"], r["pack"], r["inner"], r["license"] = rec.id, rec.pack, rec.inner, rec.license_tier()
        wav = meta[:-len(".meta.json")] + ".wav"
        x0, sr0 = bench.load(wav) if os.path.exists(wav) else (None, SR)
        n = len(x0) if x0 is not None else int(SR * float(j.get("duration") or 1.0))
        purpose = j.get("prompt") or j.get("purpose") or name
        cfg = None
        plan_why = []
        if a.agent and clips:
            from audio_agent import Agent
            clips, cfg, plan_why = Agent(listener=listener).rebuild_plan(purpose, clips, n / SR)
        y, info = rebuild(name, clips, n, purpose, listener, max_corr=a.max_corr, tries=a.tries, cfg=cfg)
        if plan_why:
            info["plan"] = plan_why
        if y is None:
            print(f"FAIL {name}: {info}"); failed += 1
            continue
        verdict = ""
        if listener is not None and x0 is not None:
            cmp = listener.compare(y, x0, SR, purpose, new_score=info["listen"])
            verdict = f"  before {cmp['old']['total']:+.3f} ({cmp['verdict']})"
        print(f"{name}: {'free' if main_free else 'licensed'} clips={len(clips)} {info['stage']} corr {info['corr']:.3f} tone {info['spectrum']:.2f} {info['semitones']:+d} st" + (f"  listen {info['listen']['total']:+.3f}" if 'listen' in info else "") + verdict)
        dest = wav if a.write else os.path.join(a.out or os.path.join(a.folder, "_rebuilt"), os.path.basename(wav))
        bench.save(dest, y, SR)
        if a.write:
            for k in ("conditioned_prompt", "strength", "init_noise_level", "copy_corr", "source_corr"):
                j.pop(k, None)
            j["references"] = use
            j.pop("used_ids", None)
            j.update({"engine": "audio_rebuild", "method": "rebuilt from the referenced clips by pitch shift, layering, random all-pass and EQ; no AI generation",
                      "unique": False, "derived": True, "licensed_derivative": not main_free, "max_corr": info["corr"], "semitones": info["semitones"], "stage": info["stage"]})
            if "listen" in info:
                j["listen"] = {k: info["listen"][k] for k in ("match", "clean", "faults", "total")}
            if "plan" in info:
                j["agent_plan"] = info["plan"]
            json.dump(j, open(meta, "w", encoding="utf-8"), indent=2)
        done += 1
    print(f"{done} rebuilt, {failed} failed, {skipped} needed nothing")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
