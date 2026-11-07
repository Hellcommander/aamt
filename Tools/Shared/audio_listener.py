"""Listening tests for generated and altered sounds: an audio model judges, not a person, and not the game.

Built on audio_quality_model (CLAP, offline, CPU, so it never takes the GPU). Every tool that makes or changes a sound
can use the same three questions:

  pick     Of these candidates, which one is best for this purpose? (takes of one SA3 render, tries of a DSP alteration)
  compare  Is the new version better or worse than the one it replaces, by more than noise?
  audit    Across a whole set, which sounds don't fit their purpose, and which other purpose fits them better?

Scores: `match` is how close the sound is to its purpose in words (CLAP cosine, about 0.2 poor to 0.5 strong), `clean` is
the judge's log-odds of "clear and clean" against "noisy with artifacts" (compare takes of ONE sound with it; its level
differs by kind of sound), `faults` are plain measurements (clipped, silent, cut off), `total` folds them into one number
and `rank` adds the tone match against a reference when one is given, so a cleaner candidate that no longer sounds like
the thing it stands in for doesn't win. Tone matching is plain signal processing: a reference never goes into the model,
so pack clips whose licenses bar AI tools can still serve as the tone reference for what was made from them.

    from audio_listener import Listener
    ears = Listener()
    best, scores = ears.pick(candidates, sr, "heavy metal door slams shut", tone_ref=original)
    verdict = ears.compare(new, old, sr, "heavy metal door slams shut")      # verdict["verdict"] in better/same/worse
    rows = ears.audit([(label, audio, sr, purpose), ...])                     # worst first

Command line: python audio_listener.py audit <folder or files...> [--json out.json]   (purpose from a sibling .meta.json
"prompt", or the file name) and python audio_listener.py compare <new.wav> <old.wav> --purpose "...".
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audio_quality_model import SfxJudge, faults, second, shared  # noqa: E402

# A change in total smaller than this is noise between two takes, not a better or worse sound.
SAME_MARGIN = 0.05
# How much the tone match counts next to the judge's total in pick(); the total moves by about 0.1 between a poor and a
# good take, the tone match by about the same between "still that sound" and "something else".
TONE_WEIGHT = 0.25


def _mono(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    return x.mean(axis=1) if x.ndim == 2 else x


def tone(x: np.ndarray, sr: int, bands: int = 32) -> np.ndarray:
    """Average log spectrum in log-spaced bands from 400 Hz up: the overall colour of a sound, time averaged out."""
    m = _mono(x)
    frame, hop = 1024, 256
    if len(m) < frame:
        m = np.pad(m, (0, frame - len(m)))
    win = np.hanning(frame)
    frames = np.stack([np.abs(np.fft.rfft(m[i:i + frame] * win)) for i in range(0, len(m) - frame + 1, hop)])
    freqs = np.fft.rfftfreq(frame, 1 / sr)
    edges = np.geomspace(400, sr / 2, bands + 1)
    out = np.stack([frames[:, (freqs >= a) & (freqs < b)].mean(axis=1) for a, b in zip(edges[:-1], edges[1:])], axis=1)
    return np.log10(out + 1e-6).mean(axis=0)


def tone_match(a: np.ndarray, b: np.ndarray, sr: int) -> float:
    """1.0 when two sounds have the same colour; a repitched or rephased version of a sound stays high, a different sound drops."""
    u, v = tone(a, sr), tone(b, sr)
    u, v = u - u.mean(), v - v.mean()
    return float((u * v).sum() / (np.linalg.norm(u) * np.linalg.norm(v) or 1))


class Listener:
    def __init__(self, judge: Optional[SfxJudge] = None):
        self._judge = judge

    @property
    def judge(self) -> SfxJudge:
        if self._judge is None:
            self._judge = shared()
        return self._judge

    def score(self, x: np.ndarray, sr: int, purpose: str = "") -> Dict[str, Any]:
        return self.judge.score(x, sr, purpose)

    @classmethod
    def second(cls) -> "Listener":
        """The after-the-fact judge (a different CLAP checkpoint, audio_quality_model.SECOND_MODEL): for the final
        verdict on a finished take only, never inside a loop that tunes against it."""
        return cls(second())

    def pick(self, candidates: Sequence[np.ndarray], sr: int, purpose: str, tone_ref: Optional[np.ndarray] = None,
             tone_weight: float = TONE_WEIGHT) -> Tuple[int, List[Dict[str, Any]]]:
        """The index of the best candidate, and every candidate's scores (with 'rank', and 'tone' when a reference is given)."""
        scores: List[Dict[str, Any]] = []
        for c in candidates:
            s = dict(self.score(c, sr, purpose))
            s["rank"] = s["total"]
            if tone_ref is not None:
                s["tone"] = round(tone_match(c, tone_ref, sr), 3)
                s["rank"] = round(s["total"] + tone_weight * s["tone"], 3)
            scores.append(s)
        if not scores:
            raise ValueError("no candidates")
        return int(np.argmax([s["rank"] for s in scores])), scores

    def compare(self, new: np.ndarray, old: np.ndarray, sr: int, purpose: str,
                new_score: Optional[Dict[str, Any]] = None, old_score: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """better / same / worse, by the judge's total, with both scores. Pass scores you already have to save a run."""
        n = new_score or self.score(new, sr, purpose)
        o = old_score or self.score(old, sr, purpose)
        delta = round(n["total"] - o["total"], 3)
        verdict = "better" if delta > SAME_MARGIN else "worse" if delta < -SAME_MARGIN else "same"
        return {"new": n, "old": o, "delta": delta, "verdict": verdict}

    def audit(self, sounds: Iterable[Tuple[str, np.ndarray, int, str]]) -> List[Dict[str, Any]]:
        """Rows for every (label, audio, sr, purpose), worst first: scores, own_rank (1 = no other purpose in the set fits
        the sound better) and confused_with (the label whose purpose fits it best when that isn't its own)."""
        items = list(sounds)
        if not items:
            return []
        clap = self.judge.clap
        texts = np.stack([self.judge.texts.setdefault(p, clap.text(p)) for _, _, _, p in items])
        rows = []
        for i, (label, x, sr, purpose) in enumerate(items):
            r = dict(self.score(x, sr, purpose))
            sims = texts @ clap.audio(_mono(x), sr)
            rank = int((sims > sims[i]).sum()) + 1
            r.update({"sound": label, "purpose": purpose, "own_rank": rank})
            if rank > 1:
                r["confused_with"] = items[int(np.argmax(sims))][0]
            rows.append(r)
        rows.sort(key=lambda r: (r["own_rank"], -r["total"]), reverse=True)
        return rows


TAGS = ("aggressive", "calm", "organic", "mechanical", "magical", "metallic", "wet", "dry", "heavy", "light", "sharp", "soft", "hostile", "friendly", "large", "small", "electric", "fiery", "icy", "ancient")
TAG_PROMPTS = {t: f"a {t} sound" for t in TAGS}


def tags(self, x: np.ndarray, sr: int, names: Sequence[str] = TAGS) -> Dict[str, float]:
    """Semantic tags, 0..1 each, from CLAP similarity to short tag prompts, scaled so the best tag is 1: how a sound reads
    in words, for searching by meaning instead of file names."""
    clap = self.judge.clap
    a = clap.audio(_mono(x), sr)
    sims = {t: float(a @ self.judge.texts.setdefault(TAG_PROMPTS.get(t, f"a {t} sound"), clap.text(TAG_PROMPTS.get(t, f"a {t} sound")))) for t in names}
    lo, hi = min(sims.values()), max(sims.values())
    return {t: round((v - lo) / (hi - lo), 3) if hi > lo else 0.0 for t, v in sorted(sims.items(), key=lambda kv: -kv[1])}


Listener.tags = tags


def summarize(rows: Sequence[Dict[str, Any]]) -> str:
    if not rows:
        return "no sounds"
    ranks = np.array([r["own_rank"] for r in rows])
    bad = [(r["sound"], r["faults"]) for r in rows if r["faults"]]
    return (f"{len(rows)} sounds; own purpose fits best for {(ranks == 1).sum()}, in the top 10 for {(ranks <= 10).sum()}, "
            f"median rank {int(np.median(ranks))}; faults: {bad if bad else 'none'}")


def _read(path: str) -> Tuple[np.ndarray, int]:
    import soundfile as sf

    x, sr = sf.read(path, always_2d=True, dtype="float32")
    return x, int(sr)


def _purpose(path: str) -> str:
    meta = os.path.splitext(path)[0] + ".meta.json"
    if os.path.exists(meta):
        try:
            return str(json.load(open(meta, encoding="utf-8")).get("prompt") or "")
        except Exception:
            pass
    return os.path.splitext(os.path.basename(path))[0].replace("_", " ")


def _label(path: str) -> str:
    try:
        return os.path.relpath(path, os.getcwd())
    except ValueError:   # another drive on Windows
        return path


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit", help="rank a set of sounds, worst first")
    a.add_argument("paths", nargs="+", help="folders (searched for *.wav) or files")
    a.add_argument("--json", help="write the rows here")
    a.add_argument("--show", type=int, default=25)
    c = sub.add_parser("compare", help="is the new sound better than the old one?")
    c.add_argument("new"); c.add_argument("old")
    c.add_argument("--purpose", required=True)
    args = ap.parse_args(argv)
    ears = Listener()
    if args.cmd == "compare":
        new, sr = _read(args.new)
        old, _ = _read(args.old)
        v = ears.compare(new, old, sr, args.purpose)
        print(json.dumps(v, indent=1))
        return 0 if v["verdict"] != "worse" else 1
    files: List[str] = []
    for p in args.paths:
        files += sorted(glob.glob(os.path.join(p, "**", "*.wav"), recursive=True)) if os.path.isdir(p) else [p]
    rows = ears.audit((_label(f), *_read(f), _purpose(f)) for f in files)
    if args.json:
        json.dump(rows, open(args.json, "w", encoding="utf-8"), indent=1)
    print(summarize(rows))
    for r in rows[:args.show]:
        extra = f"  fits '{r['confused_with']}' better" if r.get("confused_with") else ""
        print(f"{r['sound']:48} rank {r['own_rank']:3}  match {r['match']:.3f}  clean {r['clean']:+.2f}{extra}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
