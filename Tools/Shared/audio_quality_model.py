"""Listens to game sound effects with CLAP. Offline, on CPU, so it never takes the GPU.

clean: PAM (Deshmukh et al., arXiv 2402.00282), log-odds of two opposite quality prompts. Damage lowers it, but its
       level depends on the kind of sound, so compare takes of ONE sound with it; it is not a pass mark across sounds.
match: how close the sound is to its prompt.
faults: plain measurements that need no model (clipping, silence, a tail cut off mid-sound).
"""
from typing import Any, Dict, List, Optional

import numpy as np

from audio_asset_library import _ClapEmbedder

GOOD = "the sound is clear and clean."
BAD = "the sound is noisy and with artifacts."
LOGIT_SCALE = 33.0
_shared: Optional["SfxJudge"] = None


def faults(x: np.ndarray, sr: int) -> List[str]:
    """x is (samples, channels) or (samples,)."""
    a = np.abs(np.asarray(x, dtype=np.float32))
    a = a.max(axis=1) if a.ndim == 2 else a
    if a.size == 0 or a.max() < 1e-3:
        return ["silent"]
    out = []
    if float(np.mean(a >= 0.999)) > 0.002:
        out.append("clipped")
    tail = a[-max(1, int(0.01 * sr)):]
    if float(tail.max()) > 0.25 * float(a.max()):
        out.append("cut off")
    return out


class SfxJudge:
    def __init__(self, device: str = "cpu", model: Optional[str] = None):
        self.clap = _ClapEmbedder(device, model)
        self.model = model or "default"
        if not self.clap.ok:
            raise RuntimeError("CLAP did not load")
        self.good, self.bad = self.clap.text(GOOD), self.clap.text(BAD)
        self.texts: Dict[str, np.ndarray] = {}

    def score(self, x: np.ndarray, sr: int, prompt: str = "") -> Dict[str, Any]:
        x = np.asarray(x, dtype=np.float32)
        mono = x.mean(axis=1) if x.ndim == 2 else x
        a = self.clap.audio(mono, sr)
        clean = float(np.clip((a @ self.good - a @ self.bad) * LOGIT_SCALE, -6.0, 6.0))
        match = 0.0
        if prompt:
            t = self.texts.setdefault(prompt, self.clap.text(prompt))
            match = float(a @ t)
        found = faults(x, sr)
        return {"clean": round(clean, 3), "match": round(match, 3), "faults": found,
                "total": round(0.05 * clean + match - 0.5 * len(found), 3)}


# A second judge on a different CLAP checkpoint: it scores finished takes only and never steers a loop, so a plan tuned
# to please the loop's listener cannot pass by gaming it.
SECOND_MODEL = "laion/larger_clap_general"
_second: Optional["SfxJudge"] = None


def second() -> SfxJudge:
    global _second
    if _second is None:
        import os
        _second = SfxJudge(model=os.environ.get("AAMT_JUDGE_MODEL", SECOND_MODEL))
    return _second


def shared() -> SfxJudge:
    global _shared
    if _shared is None:
        _shared = SfxJudge()
    return _shared
