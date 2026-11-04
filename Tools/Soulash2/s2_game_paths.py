"""Top-level Soulash2 scripts resolve the live game through SkillCreator/s2_paths.

That honours TranscendenceTools.ini (Soulash2Path), AAMT_SOULASH2_PATH, then auto-detect,
so scripts stop hard-coding a Steam library that may no longer exist.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SKILLCREATOR = Path(__file__).resolve().parent / "SkillCreator"
if str(_SKILLCREATOR) not in sys.path:
    sys.path.insert(0, str(_SKILLCREATOR))

from s2_paths import core2_dir, mods_dir, soulash2_root, workshop_root  # noqa: E402,F401
