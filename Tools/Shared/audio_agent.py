"""The local audio agent: works out what layering and tuning a sound needs, then hands a recipe to the bench.

It is read-only in the sense that matters: it never touches audio itself. It reads the purpose, searches the asset library
for clips (by file name for the licensed tiers, whose terms keep them out of the model; by name and CLAP for Noise
Alchemy's), reads `audio_bench.analyze` numbers, decides layers, roles, gains, offsets and pitches by rules, renders a few
seeds through the bench (plain processing), lets the listener (audio_listener, CLAP on CPU) pick the best, and returns the
recipe with the candidates' scores. A person then opens that recipe in the bench page, adds or removes layers, and hears
the original base clip next to the result.

    from audio_agent import Agent
    plan = Agent().propose("heavy iron portcullis slams shut", kind="impact", seconds=1.6)
    plan["recipe"], plan["sources"] (name -> clip path or library id), plan["candidates"], plan["chosen"]

kind: impact (punch / body / tail from three clips), boom (a randomized stack), texture (a bed that follows a main clip),
voice (a character chain on one clip), plain (one clip, cleaned and levelled), auto (guessed from the purpose words).
"""
from __future__ import annotations

import os
import re
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio_bench as bench  # noqa: E402

ROLE_WORDS = {
    "punch": "impact hit crack snap click transient",
    "body": "thump body weight mid blow slam",
    "tail": "rumble tail decay boom low sub room",
    "texture": "texture bed hiss crackle grain debris air noise",
    "main": "",
}
KIND_HINTS = {
    "impact": ("impact", "hit", "slam", "crash", "punch", "stomp", "smash", "thud", "crush", "shatter", "explosion", "boom", "blast", "bang", "kick"),
    "voice": ("voice", "growl", "roar", "speak", "shout", "scream", "whisper", "grunt", "howl", "chant", "laugh", "vocal", "creature says"),
    "texture": ("ambience", "ambient", "drone", "loop", "hum", "wind", "rain", "fire crackle", "bed", "atmosphere", "steady"),
    "boom": ("huge", "massive", "cinematic", "colossal", "earth", "quake", "detonation"),
}
CHARACTERS = {"brute": ("huge", "ogre", "brute", "heavy", "giant"), "fiend": ("demon", "fiend", "evil", "dark", "infernal"), "wraith": ("ghost", "wraith", "spirit", "whisper", "ethereal"),
              "automaton": ("robot", "machine", "android", "automaton", "drone"), "giant": ("colossal", "titan", "mountain"), "imp": ("small", "imp", "goblin", "tiny", "quick"),
              "operator": ("radio", "comms", "intercom", "transmission"), "cavern": ("cave", "cavern", "tunnel", "depths", "underground")}


def _words(text: str) -> List[str]:
    return [w for w in re.findall(r"[a-z]+", text.lower()) if len(w) > 2]


def positive(purpose: str) -> str:
    """The purpose without what it rules out: "no music, no voice" or "without reverb" must not make a sound a voice."""
    return re.sub(r"\b(no|not|without|never)\s+[a-z \-]+?(?=[,.;]|$)", "", purpose.lower())


def has_word(text: str, hint: str) -> bool:
    """A hint as a whole word or phrase (a plural s allowed): "roaring flame" is not a "roar", "hitch" is not a "hit"."""
    return re.search(r"\b" + re.escape(hint) + r"s?\b", text) is not None


def guess_kind(purpose: str) -> str:
    p = positive(purpose)
    for kind in ("voice", "texture", "boom", "impact"):
        if any(has_word(p, h) for h in KIND_HINTS[kind]):
            return kind
    return "plain"


# sounds whose shape is one sharp event: an engineer gives these a slapback, never a flicker
HIT_WORDS = ("whip", "crack", "snap", "strike", "slash", "stab", "shot", "bolt", "dart", "spike", "claw", "cut", "clang", "knock", "pop",
             "whack", "whacks", "thud", "thuds", "thudding", "smack", "slam", "slams", "bash", "chop", "clack", "clonk", "tap",
             "impact", "punch", "hit", "hits", "blow", "crunch", "crush", "stomp", "smash")


def is_hit(purpose: str) -> bool:
    p = positive(purpose)
    return guess_kind(purpose) in ("impact", "boom") or any(has_word(p, h) for h in HIT_WORDS)


def guess_character(purpose: str) -> str:
    p = positive(purpose)
    for name, hints in CHARACTERS.items():
        if any(has_word(p, h) for h in hints):
            return name
    return "brute"


class Agent:
    def __init__(self, library=None, listener=None, sr: int = bench.SR):
        self._lib = library
        self._ears = listener
        self.sr = sr

    @property
    def lib(self):
        if self._lib is None:
            from audio_asset_library import AudioLibrary

            self._lib = AudioLibrary()
            self._lib.load()
        return self._lib

    @property
    def ears(self):
        if self._ears is None:
            from audio_listener import Listener

            self._ears = Listener()
        return self._ears

    # ---- finding material ------------------------------------------------------------------------------------------
    def find_clips(self, purpose: str, role: str = "main", k: int = 6, exclude: Sequence[str] = (), tiers: Optional[Sequence[str]] = None) -> List[Any]:
        """Library records for a role: the purpose words plus the role's words. Restricted and direct clips come back
        too (they are legitimate layers for plain processing); the search for them is by name, never by the model."""
        query = (purpose + " " + ROLE_WORDS.get(role, "")).strip()
        hits = self.lib.search_text(query, k=k + len(exclude))
        out = []
        for h in hits:
            r = h.record
            if r.id in exclude:
                continue
            if tiers and r.license_tier() not in tiers:
                continue
            if r.duration and r.duration > 12:
                continue
            out.append(r)
        return out[:k]

    def load_clip(self, rec, max_seconds: float = 8.0) -> np.ndarray:
        from audio_asset_library import load_asset_audio

        x, sr = load_asset_audio(rec, sr=self.sr, max_seconds=max_seconds)
        x = bench.to_stereo(x)
        return bench.fx_trim(x, self.sr, None)

    # ---- deciding --------------------------------------------------------------------------------------------------
    def tune_layer(self, layer: Dict[str, Any], x: np.ndarray, purpose: str, role: str, seconds: Optional[float]) -> List[str]:
        """Rules from the numbers: pitch a bright clip down for a heavy purpose, lift a dull one for a sharp purpose, cut a
        long clip, fade a cut-off one. Returns the reasons, for the report."""
        a = bench.analyze(x, self.sr)
        p = purpose.lower()
        why = []
        heavy = any(w in p for w in ("heavy", "huge", "deep", "massive", "giant", "low", "big"))
        light = any(w in p for w in ("light", "small", "tiny", "quick", "sharp", "thin", "high"))
        if role in ("body", "tail", "main") and heavy and a["centroid_hz"] > 1500:
            layer["pitch"] = float(layer.get("pitch", 0) - (5 if a["centroid_hz"] > 3000 else 3)); why.append(f"{role}: centroid {a['centroid_hz']} Hz is bright for a heavy sound, pitched down")
        if light and a["centroid_hz"] < 800 and role != "tail":
            layer["pitch"] = float(layer.get("pitch", 0) + 4); why.append(f"{role}: centroid {a['centroid_hz']} Hz is dull for a light sound, pitched up")
        if a["attack_ms"] > 60 and role in ("punch", "main") and guess_kind(purpose) in ("impact", "boom"):
            layer.setdefault("chain", []).insert(0, {"fx": "trim", "threshold_db": -30, "head_ms": 2}); why.append(f"{role}: attack at {a['attack_ms']} ms, trimmed to the hit")
        if a["trailing_silence_ms"] < 5 and a["sounding_seconds"] > 0.2:
            layer.setdefault("chain", []).append({"fx": "fade", "out_ms": 60}); why.append(f"{role}: ends abruptly, faded")
        if seconds and a["seconds"] > seconds * 1.5 and role != "tail":
            layer["fit"] = "cut"; why.append(f"{role}: {a['seconds']} s cut to the target")
        if a["stereo_width"] < 0.02 and role in ("tail", "texture"):
            layer.setdefault("chain", []).append({"fx": "decorrelate", "spread": 0.4}); why.append(f"{role}: mono, widened")
        return why

    def rebuild_plan(self, purpose: str, clips: Sequence[np.ndarray], seconds: Optional[float] = None) -> Tuple[List[np.ndarray], Dict[str, Any], List[str]]:
        """What to mix and what to adjust when a sound is rebuilt from clips (audio_rebuild): the clip order (which one
        leads), the pitch direction and size, how much of a second and third clip to layer, how much of the lead clip's
        loudness shape to keep, and how hard to scramble. Decided from the purpose words and the clips' numbers only.
        Returns (ordered clips, settings, reasons)."""
        kind = guess_kind(purpose)
        p = purpose.lower()
        why = [f"kind: {kind}"]
        stats = [bench.analyze(c, self.sr) for c in clips]
        order = list(range(len(clips)))
        if kind in ("impact", "boom") and len(clips) > 1:
            order.sort(key=lambda i: (stats[i]["attack_ms"], -stats[i]["crest_db"]))   # the sharpest hit leads
            why.append("impact: the clip with the sharpest attack leads, the others give body and tail")
        elif kind == "texture" and len(clips) > 1:
            order.sort(key=lambda i: -stats[i]["sounding_seconds"])                      # the longest bed leads
            why.append("texture: the longest clip leads as the bed")
        lead = stats[order[0]]
        heavy = any(w in p for w in ("heavy", "huge", "deep", "massive", "giant", "low", "big", "boom", "rumble", "thunder"))
        light = any(w in p for w in ("light", "small", "tiny", "quick", "sharp", "thin", "high", "bright", "chime", "beep"))
        cfg: Dict[str, Any] = {}
        if heavy:
            cfg["steps"] = [-5, -4, -6, -3, -7]; why.append("heavy purpose: pitched down only")
        elif light:
            cfg["steps"] = [4, 5, 3, 6, 7]; why.append("light purpose: pitched up only")
        elif lead["centroid_hz"] > 4000:
            cfg["steps"] = [-4, -3, -5, 3, -6]; why.append(f"lead clip is bright ({lead['centroid_hz']} Hz): mostly down")
        elif lead["centroid_hz"] < 600:
            cfg["steps"] = [3, 4, -3, 5, -4]; why.append(f"lead clip is dull ({lead['centroid_hz']} Hz): mostly up")
        if kind in ("impact", "boom"):
            cfg["reshape"] = 1.0; cfg["layer"] = 0.55; cfg["knots"] = 64; why.append("impact: keep the hit's shape, layer the others under it, light scramble to keep the attack")
        elif kind == "texture":
            cfg["reshape"] = 0.3; cfg["layer"] = 0.5; cfg["knots"] = 192; cfg["spread"] = 0.5; why.append("texture: little of the clip's shape, wide, hard scramble")
        elif kind == "voice":
            cfg["reshape"] = 0.8; cfg["layer"] = 0.3; cfg["knots"] = 48; why.append("voice: keep the phrasing, little layering")
        else:
            cfg["reshape"] = 0.7; cfg["layer"] = 0.45; why.append("plain: some of the clip's shape, one layer")
        if lead["sounding_seconds"] < 0.3:
            cfg["reshape"] = min(cfg.get("reshape", 1.0), 0.5); cfg["knots"] = max(cfg.get("knots", 96), 128); why.append("very short lead clip: keep less of its shape so it still gets far from the clip")
        if seconds and lead["seconds"] > seconds * 1.5:
            why.append(f"lead clip {lead['seconds']} s cut to {seconds} s")
        return [clips[i] for i in order], cfg, why

    # ---- unique rebuilds: the agent decides, audio_rebuild.render_unique (plain DSP) does -----------------------------
    def unique_plan(self, purpose: str, clips: Sequence[np.ndarray], n: int, fit: Optional[Sequence[float]] = None) -> Tuple[Dict[str, Any], List[str]]:
        """The first plan for a sound that must be its own sound against every clip: roles from different clips so none
        leads, pitches by the purpose, the MIX's shape and colour (not a lead clip's) put back only in part."""
        kind = guess_kind(purpose)
        p = positive(purpose)
        stats = [bench.analyze(bench.to_stereo(c), self.sr) for c in clips]
        heavy = any(w in p for w in ("heavy", "huge", "deep", "massive", "giant", "low", "big", "boom", "rumble", "thunder", "quake"))
        light = any(w in p for w in ("light", "small", "tiny", "quick", "sharp", "thin", "high", "bright", "chime", "beep", "needle", "spark"))
        steps = [-5, -3, -7] if heavy else [4, 3, 6] if light else [-4, 3, -6]
        why = [f"kind {kind}, {'heavy' if heavy else 'light' if light else 'neutral'} purpose: pitches {steps}"]
        idx = list(range(len(clips)))
        if kind in ("impact", "boom"):
            punch = min(idx, key=lambda i: (stats[i]["attack_ms"], -stats[i]["crest_db"]))
            rest = [i for i in idx if i != punch] or [punch]
            tail = min(rest, key=lambda i: (stats[i]["centroid_hz"], -stats[i]["sounding_seconds"]))
            body = max((i for i in rest if i != tail), key=lambda i: fit[i] if fit else 0.0, default=tail)
            roles = [("punch", punch), ("body", body), ("tail", tail)]
            why.append("impact: sharpest clip gives only a short punch, others give body and tail, so no clip leads")
        else:
            order = sorted(idx, key=lambda i: (-(fit[i] if fit else 0.0), -stats[i]["sounding_seconds"]))
            roles = [("body", i) for i in order[:3]]
            if len(order) == 1:
                roles.append(("tail", order[0]))
            why.append(f"{kind}: up to three clips layered as equals")
        layers = []
        for k, (role, i) in enumerate(roles):
            shared = sum(1 for _, j in roles if j == i) > 1
            L = {"clip": i, "role": role, "pitch": float(steps[k % len(steps)] + (-12 if role == "tail" and shared else 0)),
                 "gain_db": {"punch": 0.0, "body": -1.0 - 2.0 * k, "tail": -6.0}[role], "offset_ms": {"punch": 0.0, "body": 6.0 * k, "tail": 25.0}[role]}
            if role == "punch":
                L.update(lowcut=180.0, length_ms=180.0)
            if role == "tail":
                L.update(highcut=5000.0, stretch=1.2)
            layers.append(L)
        for L in layers:
            L["fit"] = round(float(fit[L["clip"]]), 3) if fit else 0.0
            L["centroid_hz"] = stats[L["clip"]]["centroid_hz"]
        plan = {"hit": is_hit(purpose), "layers": layers, "scramble": {"knots": 96, "spread": 0.5, "eq_db": 1.5}, "shape": 0.7, "tone": 0.3,
                "attack_ms": 4.0 if kind in ("impact", "boom") else 0.0, "width": 0.26, "glue": 0.25, "level_db": -19.0, "eq30": [0.0] * 30,
                "tone_frames": True, "widen_mid": True}
        return plan, why

    def repair_plan(self, base_index: int) -> Tuple[Dict[str, Any], List[str]]:
        """The first plan for repairing a sound that already listens well but sits a little too close to a clip: the
        current file as the only layer, changed as little as possible: no phase change until the waveform figure needs one
        (its waveform is usually far under, the closeness is in tone or envelope), its own timing, its own character put
        back (its colour by spectral matching, its first 12 ms crossfaded in, its shape), since the judge measures closeness
        to the CLIPS, not to the current file."""
        plan = {"layers": [{"clip": base_index, "role": "base", "pitch": 0.0, "gain_db": 0.0, "offset_ms": 0.0, "keep_lead": True}],
                "scramble": {"knots": 24, "spread": 0.2, "eq_db": 0.0, "depth": 0.0}, "shape": 1.0, "tone": 0.6, "attack_ms": 12.0,
                "width": 0.26, "glue": 0.0, "level_db": -19.0, "eq30": [0.0] * 30, "repair": True, "tone_frames": True, "widen_mid": True}
        plan["hit"] = bool(self._hit)
        return plan, ["repair: start from the current file, change only what the judge finds too close"]

    def revise(self, plan: Dict[str, Any], m: Dict[str, Any], clips: Sequence[np.ndarray], listen: Optional[float],
               base_listen: Optional[float], round_no: int) -> Tuple[Dict[str, Any], List[str]]:
        """The next plan from what the judge measured: the figure most over its limit, against which clip, decides the
        move; a take that is unique but listens worse than the current file is moved back toward the mix."""
        import copy
        plan = copy.deepcopy(plan)
        why: List[str] = []
        worst = m["worst"]
        i = worst["clip"]
        mine = [L for L in plan["layers"] if L["clip"] == i]
        if m["over"] > 1.0:
            metric = max(worst["ratios"], key=worst["ratios"].get)
            if metric == "waveform_pct":
                s = plan["scramble"]
                s["knots"] = int(min(512, s["knots"] * 1.5)); s["spread"] = round(min(1.0, s["spread"] + 0.1), 2)
                plan["attack_ms"] = round(plan["attack_ms"] / 2, 1)
                for L in mine:
                    dark = L.get("centroid_hz", 2000) * 2 ** (L["pitch"] / 12) < 400
                    L["pitch"] += 2.0 if (L["pitch"] >= 0 or dark) else -2.0
                    L["gain_db"] -= 1.5
                why.append(f"waveform {worst['figures']['waveform_pct']}% against clip {i}: harder scramble, less of the mix's attack, that clip's layers pitched 2 st further and 1.5 dB down")
            elif metric == "tone_pct":
                plan["tone"] = round(max(0.0, plan["tone"] - 0.15), 2)
                cb = np.clip(np.array(bench.band_spectrum(bench.to_stereo(clips[i]), self.sr)), -60, 0)
                cb = cb - cb.mean()
                push = -3.0 * cb / max(float(np.abs(cb).max()), 1e-6)       # cut where that clip is strong, lift where it is weak
                plan["eq30"] = [round(float(np.clip(g + d, -9, 9)), 1) for g, d in zip(plan["eq30"], push)]
                for L in mine:
                    L["gain_db"] -= 1.0
                why.append(f"tone {worst['figures']['tone_pct']}% against clip {i}: EQ away from its colour, less of the mix's colour put back")
            else:
                plan["shape"] = round(max(0.0, plan["shape"] - 0.2), 2)
                longer = round_no % 2 == 0
                for L in mine:
                    L["offset_ms"] = float(L.get("offset_ms", 0) + 20.0)
                    L["stretch"] = round(float(L.get("stretch", 1.0)) * (1.15 if longer else 0.87), 3)
                    L["gain_db"] -= 1.5
                tr = plan.setdefault("transient", {})
                tr["sustain"] = round(float(np.clip(tr.get("sustain", 0.0) + (0.3 if longer else -0.3), -0.8, 0.8)), 2)
                # a shape that small moves cannot shift: from the second envelope round on, change the shape itself, as a
                # sound engineer would: a slapback after a hit, an irregular flicker through a burning or crackling sound
                plan["envelope_rounds"] = int(plan.get("envelope_rounds", 0)) + 1
                if plan["envelope_rounds"] >= 2:
                    hit = plan.get("hit", False)
                    # the decay curve first (faster, then slower, further each time), then the hit's or texture's own move
                    k = plan["envelope_rounds"] - 1
                    plan["decay_gamma"] = round((1 + 0.25 * ((k + 1) // 2)) if k % 2 else 1 / (1 + 0.25 * ((k + 1) // 2)), 3)
                    why.append(f"  envelope still close after {plan['envelope_rounds']} rounds: decay curve x{plan['decay_gamma']} "
                               f"({'dies away faster' if plan['decay_gamma'] > 1 else 'rings longer'})")
                    if hit and plan["envelope_rounds"] >= 3:
                        ec = plan.setdefault("echo", {"time_ms": 70.0, "feedback": 0.2, "mix": 0.0, "damping_hz": 3500.0})
                        ec["mix"] = round(min(0.35, ec["mix"] + 0.1), 2)
                        why.append(f"  and a slapback {ec['time_ms']} ms at {ec['mix']} after the hit")
                    elif hit:
                        pass
                    elif plan["envelope_rounds"] >= 3:
                        fl = plan.setdefault("flicker", {"hz": 9.0, "depth": 0.0})
                        fl["depth"] = round(min(0.6, fl["depth"] + 0.15), 2)
                        why.append(f"  envelope still close after {plan['envelope_rounds']} rounds: irregular flicker at depth {fl['depth']}")
                if not mine:
                    # the closest clip is not a layer (a repair, or a shape every layer shares): reshape the whole sound
                    tr["attack"] = round(float(np.clip(tr.get("attack", 0.0) + (-0.3 if longer else 0.3), -0.8, 0.8)), 2)
                    for L in plan["layers"]:
                        L["stretch"] = round(float(L.get("stretch", 1.0)) * (1.06 if longer else 0.95), 3)
                    why.append(f"envelope {worst['figures']['envelope_pct']}% against clip {i}, which no single layer carries: the whole sound "
                               f"{'stretched 6%' if longer else 'tightened 5%'}, attack {tr['attack']:+.1f}, sustain {tr['sustain']:+.1f}, less shape put back")
                else:
                    why.append(f"envelope {worst['figures']['envelope_pct']}% against clip {i}: its layers 20 ms later and {'longer' if longer else 'shorter'}, less shape put back, sustain {tr['sustain']:+.1f}")
        elif listen is not None and base_listen is not None and listen < base_listen and plan.get("repair"):
            # bring the current file's character back, one lever per round in turn: colour, attack, scramble
            step = int(plan.get("quality_rounds", 0)); plan["quality_rounds"] = step + 1
            if step % 3 == 0 and plan["tone"] < 0.95:
                plan["tone"] = round(min(1.0, plan["tone"] + 0.2), 2)
                why.append(f"repair unique but listens {listen:+.3f} against the current {base_listen:+.3f}: more of its own colour back (tone {plan['tone']})")
            elif step % 3 == 1 and plan["attack_ms"] < 30:
                plan["attack_ms"] = round(min(30.0, plan["attack_ms"] + 8.0), 1)
                why.append(f"repair unique but listens {listen:+.3f} against the current {base_listen:+.3f}: more of its own attack back ({plan['attack_ms']} ms)")
            else:
                s = plan["scramble"]
                s["knots"] = int(max(8, s["knots"] * 0.8)); s["spread"] = round(max(0.05, s["spread"] - 0.05), 2)
                plan["shape"] = round(min(1.0, plan["shape"] + 0.1), 2)
                why.append(f"repair unique but listens {listen:+.3f} against the current {base_listen:+.3f}: lighter scramble, more of its own shape")
        elif listen is not None and base_listen is not None and listen < base_listen:
            fits = sorted({L.get("fit", 0.0) for L in plan["layers"]})
            if len(fits) > 1 and round_no % 2 == 0:
                for L in plan["layers"]:
                    if L.get("fit", 0.0) == fits[-1]:
                        L["gain_db"] = min(3.0, L["gain_db"] + 2.0)
                    elif L.get("fit", 0.0) == fits[0]:
                        L["gain_db"] -= 2.0
                why.append(f"unique but listens {listen:+.3f} against the current {base_listen:+.3f}: the layer that fits the purpose best up 2 dB, the weakest down 2 dB")
            else:
                plan["scramble"]["knots"] = int(max(32, plan["scramble"]["knots"] * 0.8))
                plan["glue"] = round(min(0.6, plan["glue"] + 0.1), 2)
                plan["shape"] = round(min(1.0, plan["shape"] + 0.1), 2)
                why.append(f"unique but listens {listen:+.3f} against the current {base_listen:+.3f}: lighter scramble, more glue, more of the mix's shape")
        if any("below 25 Hz" in t for t in m.get("problems", [])):
            # an engineer hears the mix go to mud: raise the floor and bring the darkest layers back up
            plan["floor_hz"] = round(min(90.0, float(plan.get("floor_hz", 30.0)) * 1.5), 1)
            for L in plan["layers"]:
                if L.get("centroid_hz", 2000) * 2 ** (L["pitch"] / 12) < 400 and L["pitch"] < 0:
                    L["pitch"] += 3.0
            why.append(f"inaudible sub rumble: low floor raised to {plan['floor_hz']} Hz, the darkest layers pitched 3 st up")
        if m["width"] < plan["width"]:
            plan["width"] = round(min(0.6, plan["width"] + 0.08), 2)
            why.append(f"width {m['width']:.2f}: wider target {plan['width']}")
        return plan, why

    def options(self, plan: Dict[str, Any], m: Dict[str, Any], clips: Sequence[np.ndarray], listen: Optional[float],
                base_listen: Optional[float], purpose: str = "") -> List[Tuple[str, Dict[str, Any], Any]]:
        """Single-lever alternatives to the current plan, for the loop to audition (render, measure, listen) side by
        side, as an engineer A/B-tests one change at a time instead of stacking several and hearing only the sum.
        A take still too close gets moves against the figure most over, in both directions where the right one is not
        known; a unique take that listens worse than the current file gets moves back toward its own character."""
        import copy
        out: List[Tuple[str, Dict[str, Any]]] = []

        def opt(label, fn):
            q = copy.deepcopy(plan)
            if fn(q) is not False:
                out.append((label, q, fn))
        tr = lambda q: q.setdefault("transient", {})
        clamp = lambda v, lo, hi: float(np.clip(v, lo, hi))
        worst = m["worst"]; i = worst["clip"]
        mine = lambda q: [L for L in q["layers"] if L["clip"] == i]
        if m["over"] > 1.0:
            metric = max(worst["ratios"], key=worst["ratios"].get)
            if metric == "waveform_pct":
                opt("phase deeper", lambda q: q["scramble"].update(depth=round(min(1.0, float(q["scramble"].get("depth", 1.0)) + 0.25), 2)) if float(q["scramble"].get("depth", 1.0)) < 1.0 else False)
                # (finer detail changes nothing while the phase is left alone: depth 0 in a repair)
                opt("phase finer", lambda q: q["scramble"].update(knots=int(min(512, q["scramble"]["knots"] * 1.5)), spread=round(min(1.0, q["scramble"]["spread"] + 0.1), 2))
                    if float(q["scramble"].get("depth", 1.0)) > 0 else False)
                opt("less of the mix's attack", lambda q: q.update(attack_ms=round(q["attack_ms"] / 2, 1)) if q["attack_ms"] > 1 else False)
                # a tonal resonance matches the clip's at some lag whatever its phase: only moving its frequency helps
                for d in (1.0, -1.0):
                    opt(f"whole sound {d:+.0f} st", lambda q, d=d: [L.update(pitch=L["pitch"] + d) for L in q["layers"]])
                for hz in (25.0, -25.0):
                    opt(f"partials shifted {hz:+.0f} Hz", lambda q, hz=hz: [L.update(shift_hz=round(float(L.get("shift_hz", 0.0)) + hz, 1)) for L in q["layers"]])
                self._new_attack(opt, plan, purpose)
                if mine(plan):
                    for d in (2.0, -2.0):
                        opt(f"clip {i} layers {d:+.0f} st", lambda q, d=d: [L.update(pitch=L["pitch"] + d) for L in mine(q)])
                    opt(f"clip {i} layers -2 dB", lambda q: [L.update(gain_db=L["gain_db"] - 2.0) for L in mine(q)])
            elif metric == "tone_pct":
                cb = np.clip(np.array(bench.band_spectrum(bench.to_stereo(clips[i]), self.sr)), -60, 0)
                cb = cb - cb.mean()
                push = -cb / max(float(np.abs(cb).max()), 1e-6)
                for amt in (2.0, 4.0):
                    opt(f"EQ {amt:.0f} dB away from clip {i}", lambda q, amt=amt: q.update(eq30=[round(clamp(g + amt * d, -9, 9), 1) for g, d in zip(q["eq30"], push)]))
                opt("less of the mix's colour", lambda q: q.update(tone=round(max(0.0, q["tone"] - 0.2), 2)) if q["tone"] > 0 else False)
                if mine(plan):
                    opt(f"clip {i} layers -2 dB", lambda q: [L.update(gain_db=L["gain_db"] - 2.0) for L in mine(q)])
            else:
                for g in (1.25, 0.8):
                    opt(f"decay x{g}", lambda q, g=g: q.update(decay_gamma=round(float(q.get("decay_gamma", 1.0)) * g, 3)))
                for v in (0.3, -0.3):
                    opt(f"sustain {v:+.1f}", lambda q, v=v: tr(q).update(sustain=round(clamp(tr(q).get("sustain", 0.0) + v, -0.8, 0.8), 2)))
                    opt(f"attack {v:+.1f}", lambda q, v=v: tr(q).update(attack=round(clamp(tr(q).get("attack", 0.0) + v, -0.8, 0.8), 2)))
                for f in (1.06, 0.95):
                    opt(f"whole sound x{f} long", lambda q, f=f: [L.update(stretch=round(float(L.get("stretch", 1.0)) * f, 3)) for L in q["layers"]])
                if plan.get("hit"):
                    opt("slapback", lambda q: q.setdefault("echo", {"time_ms": 70.0, "feedback": 0.2, "mix": 0.0, "damping_hz": 3500.0}).update(
                        mix=round(min(0.35, q.get("echo", {}).get("mix", 0.0) + 0.1), 2)))
                else:
                    opt("flicker", lambda q: q.setdefault("flicker", {"hz": 9.0, "depth": 0.0}).update(depth=round(min(0.6, q.get("flicker", {}).get("depth", 0.0) + 0.1), 2)))
                opt("less of the mix's shape", lambda q: q.update(shape=round(max(0.0, q["shape"] - 0.2), 2)) if q["shape"] > 0 else False)
                self._new_attack(opt, plan, purpose)
                if mine(plan):
                    opt(f"clip {i} layers 20 ms later", lambda q: [L.update(offset_ms=float(L.get("offset_ms", 0)) + 20.0) for L in mine(q)])
                    opt(f"clip {i} layers -2 dB", lambda q: [L.update(gain_db=L["gain_db"] - 2.0) for L in mine(q)])
        elif listen is not None and base_listen is not None and listen < base_listen:
            opt("more of the mix's colour", lambda q: q.update(tone=round(min(1.0, q["tone"] + 0.2), 2)) if q["tone"] < 1.0 else False)
            opt("more of the mix's attack", lambda q: q.update(attack_ms=round(min(30.0, q["attack_ms"] + 8.0), 1)) if q["attack_ms"] < 30 else False)
            opt("more of the mix's shape", lambda q: q.update(shape=round(min(1.0, q["shape"] + 0.15), 2)) if q["shape"] < 1.0 else False)
            opt("lighter phase", lambda q: q["scramble"].update(depth=round(max(0.0, float(q["scramble"].get("depth", 1.0)) - 0.2), 2)) if float(q["scramble"].get("depth", 1.0)) > 0 else False)
            opt("decay curve back toward its own", lambda q: q.update(decay_gamma=round(1.0 + (float(q.get("decay_gamma", 1.0)) - 1.0) / 2, 3)) if abs(float(plan.get("decay_gamma", 1.0)) - 1.0) > 0.02 else False)
            opt("transient back toward its own", lambda q: tr(q).update(attack=round(tr(q).get("attack", 0.0) / 2, 2), sustain=round(tr(q).get("sustain", 0.0) / 2, 2)) if any(abs(v) > 0.05 for v in (plan.get("transient") or {}).values()) else False)
            opt("less echo and flicker", lambda q: [d.update(**{k: round(d[k] / 2, 2)}) for d, k in ((q.get("echo") or {}, "mix"), (q.get("flicker") or {}, "depth")) if d.get(k)] or False)
            fits = sorted({L.get("fit", 0.0) for L in plan["layers"]})
            if len(fits) > 1:
                opt("best-fitting layer +2 dB", lambda q: [L.update(gain_db=min(3.0, L["gain_db"] + 2.0)) for L in q["layers"] if L.get("fit", 0.0) == fits[-1]])
            if not plan.get("repair"):
                opt("more glue", lambda q: q.update(glue=round(min(0.6, q["glue"] + 0.1), 2)))
        return out

    MATERIAL_WORDS = (("wood", ("wood", "wooden", "mallet", "plank", "club", "croquet", "staff", "log", "knock")),
                      ("metal", ("metal", "steel", "iron", "blade", "sword", "anvil", "chain", "clang", "armor", "armour", "hammer")),
                      ("stone", ("stone", "rock", "boulder", "brick", "rubble", "crush", "masonry")),
                      ("bone", ("bone", "skull", "skeleton")), ("glass", ("glass", "shatter", "pane")),
                      ("crystal", ("crystal", "gem", "ice", "frost")), ("flesh", ("flesh", "body", "bodies", "punch", "squelch", "gore")),
                      ("chitin", ("chitin", "carapace", "insect", "beetle")), ("plasma", ("plasma", "energy", "laser")))

    def material_of(self, purpose: str) -> Optional[str]:
        """The material a hit is made of, from the purpose's own words (whole words, negations ignored)."""
        for mat, words in self.MATERIAL_WORDS:
            if any(has_word(positive(purpose), w) for w in words):
                return mat
        return None

    def _new_attack(self, opt, plan: Dict[str, Any], purpose: str) -> None:
        """Transient replacement, as an engineer does for a drum: the hit's first ms come from a synthesized strike on
        the purpose's material (no clip behind it) and the existing layers fade in under it, so the attack that matched
        a clip is gone while the body stays. Offered once per plan, then its level and size can be moved."""
        if not plan.get("hit"):
            return
        mat = self.material_of(purpose)
        if mat is None:
            return
        have = [L for L in plan["layers"] if L.get("synth")]
        if not have:
            def add(q, mat=mat):
                q["layers"].append({"clip": -1, "role": "attack", "synth": {"material": mat, "size": 0.5, "force": 0.7, "seed": 1},
                                    "pitch": 0.0, "gain_db": -2.0, "offset_ms": 0.0, "length_ms": 140.0})
                for L in q["layers"]:
                    if not L.get("synth"):
                        L["attack_cut_ms"] = 18.0
                q["attack_ms"] = 0.0          # the mix's own attack is what is being replaced
            opt(f"new {mat} attack (synthesized)", add)
        else:
            opt("synthesized attack louder", lambda q: [L.update(gain_db=min(4.0, L["gain_db"] + 2.0)) for L in q["layers"] if L.get("synth")])
            opt("synthesized attack larger", lambda q: [L["synth"].update(size=round(min(1.0, L["synth"]["size"] + 0.2), 2)) for L in q["layers"] if L.get("synth")])
            opt("synthesized attack smaller", lambda q: [L["synth"].update(size=round(max(0.0, L["synth"]["size"] - 0.2), 2)) for L in q["layers"] if L.get("synth")])
            opt("longer hand-over to it", lambda q: [L.update(attack_cut_ms=round(min(60.0, float(L.get("attack_cut_ms", 18.0)) * 1.5), 1)) for L in q["layers"] if not L.get("synth")])

    @staticmethod
    def closeness(m: Dict[str, Any]) -> float:
        """How close a take is overall: the worst clip, plus half the mean of the next two. Fixing one clip by moving
        onto another then shows as no gain, so the loop stops trading one near clip for the next."""
        overs = sorted((row["over"] for row in m["rows"]), reverse=True)
        rest = overs[1:3]
        return overs[0] + (0.5 * sum(rest) / len(rest) if rest else 0.0)

    def rebuild_unique(self, name: str, sources: List[Dict[str, Any]], n: int, purpose: str, *, base_listen: Optional[float] = None,
                       rounds: int = 10, seeds: int = 2, min_width: float = 0.2, more=None, max_new: int = 2,
                       stuck_rounds: int = 3, base: Optional[np.ndarray] = None, mark_for=None, patience: int = 3,
                       audition: bool = True) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
        """Render, measure, decide, repeat: the sound engineer's loop, with every sample made by render_unique (plain DSP).

        sources: [{"audio": array, "meta": caller's record, "limits": {figure: limit}, "listen": may the listener hear
        it (only packs whose terms allow AI tools; the rest are judged by plain numbers)}]. The judge measures each take
        against every clip the plan USES; the listener scores the purpose; revise() decides the next plan. When one clip
        stays the closest for `stuck_rounds` rounds, `more(exclude_metas, role)` may supply a new source (same dict), which
        takes over that clip's layers: the engineer swaps a layer that cannot be made its own. With `base` (the current
        file, made from these sources) the loop repairs instead of rebuilding; `mark_for(list of the checked sources)`
        gives the measured pass mark for that set of clips (1.0 when not given): the base is the only layer at first and every
        source is still checked, since the base carries all of them. With `audition` (the default) each round A/B-tests
        single-lever options() side by side and keeps the best trade of closeness against listening; without it revise()
        stacks its moves (the older loop). Returns the best unique,
        stereo, clean take by the listener (or None) and the record (plan, the sources used, what was decided)."""
        import zlib
        import audio_rebuild as rb
        sources = list(sources)
        self._hit = is_hit(purpose)
        if base is not None:
            sources = [dict(s, always=True) for s in sources] + [{"audio": bench.to_stereo(base), "meta": {"base": "current file"}, "limits": None, "check": False}]
            clips = [s["audio"] for s in sources]
            plan, log = self.repair_plan(len(sources) - 1)
        else:
            clips = [s["audio"] for s in sources]
            fit = [self.ears.score(bench.to_stereo(s["audio"]), self.sr, purpose)["match"] if s.get("listen") else 0.0 for s in sources]
            plan, log = self.unique_plan(purpose, clips, n, fit if any(fit) else None)
            if any(fit):
                log.append("source fit to the purpose (listened sources only): " + ", ".join(f"clip {i} {f:.3f}" for i, f in enumerate(fit)))

        def checked_for(q):
            use = {int(L["clip"]) for L in q["layers"] if int(L.get("clip", -1)) >= 0} | {i for i, s in enumerate(sources) if s.get("always")}
            return tuple(sorted(i for i in use if sources[i].get("check", True)))

        def checked():
            """The clips a take must be unique against: every clip a layer uses, and every source the base was made from."""
            use = {int(L["clip"]) for L in plan["layers"] if int(L.get("clip", -1)) >= 0} | {i for i, s in enumerate(sources) if s.get("always")}
            return tuple(sorted(i for i in use if sources[i].get("check", True)))
        judges: Dict[Tuple[int, ...], Any] = {}
        marks: Dict[Tuple[int, ...], float] = {}

        def judge(y):
            used = checked()
            if used not in judges:
                mk = float(mark_for([sources[i] for i in used])) if mark_for else 1.0
                judges[used] = rb.unique_judge([clips[i] for i in used], [sources[i]["limits"] for i in used], mk)
                marks[used] = mk
            m = judges[used](y)
            for row in m["rows"]:
                row["clip"] = used[row["clip"]]
            return m

        best, best_info, streak, last, added, flat = None, None, 0, None, 0, 0
        for r in range(rounds):
            tries = []
            for s in range(seeds):
                seed = zlib.crc32(f"{name}/u{r}/{s}".encode())
                y = rb.render_unique(clips, n, plan, seed)
                m = judge(y)
                ok = m["over"] <= 1.0 and m["width"] >= min_width and not m["problems"]
                lis = self.ears.score(y, self.sr, purpose) if ok else None
                tries.append((ok, lis["total"] if lis else None, m["over"], y, m, lis, seed))
            ok, lv, over, y, m, lis, seed = max(tries, key=lambda t: (t[0], t[1] if t[1] is not None else -9.0, -t[2]))
            figs = ", ".join(f"{k.split('_')[0]} {v}%" for k, v in m["worst"]["figures"].items())
            log.append(f"round {r}: over {over:.2f} (clip {m['worst']['clip']}: {figs}), width {m['width']:.2f}"
                       + (f", listens {lv:+.3f}" if lv is not None else "") + (f", {', '.join(m['problems'])}" if m["problems"] else ""))
            if ok and (best_info is None or lv > best_info["listen"]["total"]):
                best = y
                used = checked()
                best_info = {"plan": plan, "seed": seed, "round": r, "over": round(over, 3), "worst": m["worst"], "width": round(m["width"], 3),
                             "listen": lis, "used": [sources[i]["meta"] for i in used], "used_limits": [sources[i]["limits"] for i in used],
                             "closest": sources[m["worst"]["clip"]]["meta"], "pass_mark": marks.get(used, 1.0)}
            improved = ok and best_info is not None and best_info["round"] == r
            flat = 0 if (improved or not ok) else flat + 1
            if best_info is not None and flat >= patience:
                log.append(f"round {r}: {flat} unique rounds without a better listen, stopped (best is round {best_info['round']})")
                break
            if ok and base_listen is not None and lv >= base_listen:
                log.append(f"round {r}: unique and listens at least as well as the current file, done")
                break
            wc = m["worst"]["clip"]
            streak = streak + 1 if (over > 1.0 and wc == last) else (1 if over > 1.0 else 0)
            last = wc
            if more is not None and streak >= stuck_rounds and added < max_new and any(L["clip"] == wc for L in plan["layers"]):
                role = next((L["role"] for L in plan["layers"] if L["clip"] == wc), "body")
                in_use = [s["meta"] for s in sources]
                new = more(in_use, role)
                if new is not None:
                    sources.append(new); clips.append(new["audio"]); added += 1
                    k = len(clips) - 1
                    import copy
                    plan = copy.deepcopy(plan)      # the best take's record keeps the plan it was made with
                    nf = self.ears.score(bench.to_stereo(new["audio"]), self.sr, purpose)["match"] if new.get("listen") else 0.0
                    nc = bench.analyze(bench.to_stereo(new["audio"]), self.sr)["centroid_hz"]
                    for L in plan["layers"]:
                        if L["clip"] == wc:
                            L.update(clip=k, fit=round(float(nf), 3), centroid_hz=nc)
                    log.append(f"  -> clip {wc} stayed closest for {streak} rounds: its {role} layer now comes from a new library clip ({k})")
                    streak = 0
                    continue
            if audition:
                fixed, why = self.revise(plan, m, clips, lv, base_listen, r)   # its rumble and width fixes ride along
                opts = self.options(plan, m, clips, lv, base_listen, purpose)
                if not opts:
                    plan = fixed; log.extend("  -> " + w for w in why); continue
                here = self.closeness(m)

                def hear(label, q):
                    """Render one option at 2 seeds; its figures are the mean, a unique take among them may become the best."""
                    nonlocal best, best_info
                    for key in ("floor_hz", "width"):
                        if key in fixed:
                            q[key] = fixed[key]
                    got = []
                    for s in range(2):
                        sd = zlib.crc32(f"{name}/a{r}/{label}/{s}".encode())
                        yq = rb.render_unique(clips, n, q, sd)
                        mq = judge(yq)
                        okq = mq["over"] <= 1.0 and mq["width"] >= min_width and not mq["problems"]
                        lq = self.ears.score(yq, self.sr, purpose)
                        got.append((mq, lq["total"], okq))
                        if okq and (best_info is None or lq["total"] > best_info["listen"]["total"]):
                            used = checked_for(q)
                            best = yq
                            best_info = {"plan": q, "seed": sd, "round": r, "over": round(mq["over"], 3), "worst": mq["worst"], "width": round(mq["width"], 3),
                                         "listen": lq, "used": [sources[i]["meta"] for i in used], "used_limits": [sources[i]["limits"] for i in used],
                                         "closest": sources[mq["worst"]["clip"]]["meta"], "pass_mark": marks.get(used, 1.0), "audition": label}
                    ov = float(np.mean([g[0]["over"] for g in got])); cl = float(np.mean([self.closeness(g[0]) for g in got]))
                    return (label, q, ov, float(np.mean([g[1] for g in got])), any(g[2] for g in got), any(g[0]["problems"] for g in got), cl)
                heard = [hear(label, q) for label, q, _ in opts]
                moves = {label: fn for label, _, fn in opts}
                clean = [h for h in heard if not h[5]]
                if not clean:
                    log.append("  audition: every option has a render problem (" + "; ".join(h[0] for h in heard) + ")")
                    plan = fixed; log.extend("  -> " + w for w in why); continue
                heard = clean           # a change that breaks the render (silence, clipping, mud) is never kept
                if over > 1.0:
                    # still too close: the option that buys the most distance (over every near clip, not just the worst)
                    # for the least listening lost; then the two best such moves together, kept if that beats either
                    ref_l = lv if lv is not None else max(h[3] for h in heard)
                    gain = lambda h: (h[4], h[3] if h[4] else (here - h[6]) - 0.3 * max(0.0, ref_l - h[3]))
                    ranked = sorted(heard, key=gain, reverse=True)
                    pick = ranked[0]
                    if len(ranked) > 1 and not pick[4] and here - ranked[1][6] > 0 and here - pick[6] > 0:
                        import copy as _c
                        q2 = _c.deepcopy(pick[1])
                        if moves[ranked[1][0]](q2) is not False:
                            both = hear(f"{pick[0]} + {ranked[1][0]}", q2)
                            heard.append(both)
                            if not both[5] and gain(both) > gain(pick):
                                pick = both
                else:
                    # unique but weaker than the current file: the best-listening option that stays unique, if any beats this one
                    good = [h for h in heard if h[4]]
                    pick = max(good, key=lambda h: h[3]) if good else None
                    if pick is not None and lv is not None and pick[3] <= lv:
                        pick = None
                log.append("  audition: " + "; ".join(f"{h[0]} over {h[2]:.2f}/{h[6]:.2f} listens {h[3]:+.3f}" for h in heard))
                if pick is None:
                    log.append("  -> no single change keeps it unique and listens better")
                    flat = patience          # nothing left to try from here
                    break
                if pick[1] == plan:
                    log.append(f"  -> {pick[0]} changes nothing: no move left from here")
                    break
                plan = pick[1]
                log.append(f"  -> kept: {pick[0]} (over {pick[2]:.2f}, listens {pick[3]:+.3f})")
            else:
                plan, why = self.revise(plan, m, clips, lv, base_listen, r)
                log.extend("  -> " + w for w in why)
        info = dict(best_info or {"error": "no round gave a unique, stereo, clean take"}, log=log)
        return best, info

    def propose(self, purpose: str, *, kind: str = "auto", seconds: Optional[float] = None, seed: int = 1, candidates: int = 4,
                sources: Optional[Dict[str, np.ndarray]] = None, tiers: Optional[Sequence[str]] = None) -> Dict[str, Any]:
        """A recipe for the purpose, judged across `candidates` seeds. `sources` fixes the material (name -> array) instead
        of searching the library; the first is the main clip. The result's 'sources' maps names to arrays for the bench."""
        kind = guess_kind(purpose) if kind == "auto" else kind
        report: List[str] = [f"kind: {kind}"]
        mats: Dict[str, np.ndarray] = {}
        origins: Dict[str, Dict[str, Any]] = {}
        used: List[str] = []

        def pick(role: str, name: str) -> Optional[str]:
            if sources:
                names = list(sources)
                idx = {"main": 0, "punch": 0, "body": 1 if len(names) > 1 else 0, "tail": 2 if len(names) > 2 else 0, "texture": 1 if len(names) > 1 else 0}[role]
                mats[name] = bench.to_stereo(sources[names[idx]]); origins[name] = {"tier": "given", "origin": names[idx]}
                return name
            recs = self.find_clips(purpose, role, k=3, exclude=used, tiers=tiers)
            if not recs:
                return None
            r = recs[0]; used.append(r.id)
            mats[name] = self.load_clip(r); origins[name] = {"tier": r.license_tier(), "origin": r.label(), "id": r.id, "ai_allowed": r.ai_allowed()}
            report.append(f"{role}: {r.label()} [{r.license_tier()}]")
            return name

        if kind == "impact" or kind == "boom":
            names = [pick(r, r) for r in ("punch", "body", "tail")]
            names = [n for n in names if n]
            if not names:
                raise RuntimeError("no clips found for that purpose")
            if kind == "impact":
                recipe = bench.impact_recipe(names[0], names[1] if len(names) > 1 else None, names[2] if len(names) > 2 else None, seed=seed)
            else:
                recipe = bench.boom_recipe(names, seed=seed, layers=max(3, len(names) + 1))
            for layer, role in zip(recipe["layers"], ("punch", "body", "tail", "extra", "extra")):
                report += self.tune_layer(layer, mats[layer["source"]], purpose, role if role != "extra" else "body", seconds)
        elif kind == "texture":
            main = pick("main", "main"); tex = pick("texture", "texture")
            if not main:
                raise RuntimeError("no clips found for that purpose")
            layers = [{"source": main, "gain_db": 0, "fit": "loop" if seconds else "cut", "chain": [{"fx": "denoise", "amount": 0.4}]}]
            if tex:
                layers.append({"source": tex, "gain_db": -9, "fit": "grains", "band": [1500, 9000], "follow": {"layer": 0, "amount": 1.0, "ms": 12}, "chain": [{"fx": "decorrelate", "spread": 0.5}]})
            recipe = {"seed": seed, "length": seconds or "main", "layers": layers, "blend": {"mode": "sum"}, "master": [{"fx": "level", "rms_db": -19}, {"fx": "fade", "in_ms": 20, "out_ms": 200}]}
            for layer, role in zip(layers, ("main", "texture")):
                report += self.tune_layer(layer, mats[layer["source"]], purpose, role, seconds)
        elif kind == "voice":
            main = pick("main", "main")
            if not main:
                raise RuntimeError("no clips found for that purpose")
            character = guess_character(purpose); report.append(f"character: {character}")
            recipe = {"seed": seed, "length": "main", "layers": [{"source": main, "gain_db": 0, "fit": "cut", "chain": [{"fx": "denoise", "amount": 0.5}, {"fx": "preset", "name": character}]}],
                      "blend": {"mode": "sum"}, "master": [{"fx": "level", "rms_db": -19}, {"fx": "fade"}]}
            report += self.tune_layer(recipe["layers"][0], mats[main], purpose, "main", seconds)
        else:
            main = pick("main", "main")
            if not main:
                raise RuntimeError("no clips found for that purpose")
            recipe = {"seed": seed, "length": seconds or "main", "layers": [{"source": main, "gain_db": 0, "fit": "cut", "chain": [{"fx": "preset", "name": "clean_up"}]}],
                      "blend": {"mode": "sum"}, "master": []}
            report += self.tune_layer(recipe["layers"][0], mats[main], purpose, "main", seconds)
        if seconds:
            recipe["length"] = float(seconds)
        recipe["sources"] = dict(mats)

        # Several seeds, the listener picks. The base clip is the tone reference so the result still sounds like its material.
        renders: List[np.ndarray] = []
        seeds = [seed + 7919 * i for i in range(max(1, candidates))]
        b = bench.Bench(self.sr)
        for s in seeds:
            y, _ = b.render(dict(recipe, seed=s))
            renders.append(y)
        base = mats[recipe["layers"][0]["source"]]
        best, scores = self.ears.pick(renders, self.sr, purpose, tone_ref=base, tone_weight=0.15)
        recipe["seed"] = seeds[best]
        base_score = self.ears.score(base, self.sr, purpose)
        report.append(f"listener: seed {seeds[best]} chosen, total {scores[best]['total']:+.3f} (base clip {base_score['total']:+.3f}), match {scores[best]['match']:.3f}")
        return {"kind": kind, "recipe": recipe, "sources": origins, "candidates": [{"seed": s, **sc} for s, sc in zip(seeds, scores)], "chosen": best,
                "base_score": base_score, "render": renders[best], "report": report}


def main(argv=None) -> int:
    import argparse, json

    ap = argparse.ArgumentParser(description="local audio agent: propose a bench recipe for a purpose")
    ap.add_argument("purpose"); ap.add_argument("--kind", default="auto"); ap.add_argument("--seconds", type=float); ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--candidates", type=int, default=4); ap.add_argument("--out", help="write the chosen render here (wav)"); ap.add_argument("--recipe", help="write the recipe here (json, sources as library ids)")
    a = ap.parse_args(argv)
    plan = Agent().propose(a.purpose, kind=a.kind, seconds=a.seconds, seed=a.seed, candidates=a.candidates)
    for line in plan["report"]:
        print(line)
    if a.out:
        bench.save(a.out, plan["render"], bench.SR); print("wrote", a.out)
    if a.recipe:
        r = dict(plan["recipe"]); r["sources"] = {k: (v.get("id") or v.get("origin")) for k, v in plan["sources"].items()}
        json.dump(r, open(a.recipe, "w", encoding="utf-8"), indent=1); print("wrote", a.recipe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
