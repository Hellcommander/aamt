#!/usr/bin/env python3
"""Generate TRANSLATION language RAW from dwarf T_WORD keys + seeded phonology."""

from __future__ import annotations

import hashlib
import random
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from df_paths import templates_dir
from df_raw_parser import tokenize_text

PHONOLOGY: Dict[str, Dict[str, Sequence[str]]] = {
    "harsh": {
        "onset": ("k", "g", "t", "d", "b", "p", "kr", "gr", "th", "kh", "dr", "st", "sk"),
        "nucleus": ("a", "o", "u", "â", "ô", "û", "au", "ou"),
        "coda": ("k", "g", "t", "d", "sh", "th", "ng", "rk", "rt", "st", "m", "n", "b"),
    },
    "liquid": {
        "onset": ("l", "n", "m", "r", "s", "sh", "v", "f", "w", "y", "fl", "sl", "th"),
        "nucleus": ("a", "e", "i", "ia", "ea", "ai", "ei", "o"),
        "coda": ("l", "n", "m", "r", "s", "th", "sh", "nd", "ll", ""),
    },
    "guttural": {
        "onset": ("g", "gh", "k", "kh", "q", "r", "h", "ng", "z", "zg", "hr"),
        "nucleus": ("u", "o", "a", "û", "ö", "ua", "uo"),
        "coda": ("g", "gh", "k", "r", "rg", "nk", "z", "th", "ng", "h"),
    },
}


def extract_t_word_keys(reference_text: str) -> List[str]:
    keys: List[str] = []
    for name, args in tokenize_text(reference_text):
        if name.upper() == "T_WORD" and args:
            keys.append(args[0])
    return keys


def _seed_for(translation_id: str, phonology: str) -> int:
    h = hashlib.sha256(f"{translation_id}:{phonology}".encode("utf-8")).hexdigest()
    return int(h[:16], 16)


def generate_word(rng: random.Random, phonology: str, key: str) -> str:
    table = PHONOLOGY.get(phonology, PHONOLOGY["harsh"])
    # Bias length by key hash for variety
    syllables = 1 + (sum(ord(c) for c in key) % 3)
    parts: List[str] = []
    for i in range(syllables):
        onset = rng.choice(table["onset"])
        nucleus = rng.choice(table["nucleus"])
        coda = rng.choice(table["coda"]) if i == syllables - 1 or rng.random() < 0.6 else ""
        parts.append(onset + nucleus + coda)
    word = "".join(parts)
    # DF language words are typically lowercase ascii-ish; strip spaces
    return word[:12] if len(word) > 12 else word


def write_language_raw(
    translation_id: str,
    out_dir: Path,
    *,
    phonology: str = "harsh",
    reference_path: Optional[Path] = None,
) -> Path:
    ref = reference_path or (templates_dir() / "language_DWARF_reference.txt")
    text = ref.read_text(encoding="latin-1", errors="replace")
    keys = extract_t_word_keys(text)
    if not keys:
        raise ValueError(f"No T_WORD keys found in {ref}")

    tid = translation_id.upper()
    rng = random.Random(_seed_for(tid, phonology))
    lines = [
        "language_" + tid.lower(),
        "",
        "[OBJECT:LANGUAGE]",
        "",
        f"[TRANSLATION:{tid}]",
    ]
    used = set()
    for key in keys:
        word = generate_word(rng, phonology, key)
        # Avoid empty / duplicate collisions lightly
        base = word
        n = 0
        while word in used or not word:
            n += 1
            word = base + rng.choice(PHONOLOGY.get(phonology, PHONOLOGY["harsh"])["coda"] or ("a",))
            if n > 20:
                word = f"{base}{n}"
                break
        used.add(word)
        lines.append(f"\t[T_WORD:{key}:{word}]")
    lines.append("")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"language_{tid.lower()}.txt"
    out_path.write_text("\n".join(lines), encoding="latin-1", errors="replace")
    return out_path
