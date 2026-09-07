#!/usr/bin/env python3
"""
Detect a Unity game's editor version and resolve a matching Hub install.

Strict policy (AAMT):
  - Prefer an exact Hub folder match for the game's detected version.
  - Accept letter-only siblings (e.g. game 2021.3.45f2 vs Hub 2021.3.45f1)
    when Hub does not ship that exact letter.
  - Never silently use a different patch (6000.0.58 for 6000.0.77).
  - Callers should skip Unity batch export and print install_hint when missing.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

VERSION_RE = re.compile(rb"(\d+\.\d+\.\d+[a-z]\d+)")
VERSION_STR_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)([a-z])(\d+)$", re.I)
# Hub sometimes names folders "Unity 2021.3.45f2" or "2021.3.45.8976527"
VERSION_IN_TEXT_RE = re.compile(r"(\d+\.\d+\.\d+[a-z]\d+)", re.I)
VERSION_CHANGESET_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)\.(\d+)$")


def normalize_version_token(raw: str) -> Optional[str]:
    """Turn folder names / log tokens into a Hub-style version (e.g. 2021.3.45f2)."""
    raw = (raw or "").strip()
    if not raw:
        return None
    if parse_version_parts(raw):
        return raw
    m = VERSION_IN_TEXT_RE.search(raw)
    if m:
        return m.group(1)
    # Log-style 2021.3.45.8976527 — keep X.Y.Z; letter resolved via sibling match later
    m2 = VERSION_CHANGESET_RE.match(raw)
    if m2:
        return f"{m2.group(1)}.{m2.group(2)}.{m2.group(3)}"
    return None

# Hub secondary install path used on this machine + common defaults.
# Prefer E:\tools\Unity_Editor (current Hub secondary); keep H: as legacy fallback.
DEFAULT_EDITOR_ROOTS = [
    Path(r"E:\tools\Unity_Editor"),
    Path(r"H:\tools\Unity_Editor"),
    Path(r"D:\tools\Unity_Editor"),
    Path(r"C:\Program Files\Unity\Hub\Editor"),
    Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\Unity\Hub\Editor")),
]


@dataclass
class UnityMatch:
    required: str
    editor_exe: Optional[str]
    matched_version: Optional[str]
    exact: bool
    letter_sibling: bool
    install_hint: str


def parse_version_parts(version: str) -> Optional[Tuple[int, int, int, str, int]]:
    m = VERSION_STR_RE.match(version.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4).lower(), int(m.group(5))


def same_xyz(a: str, b: str) -> bool:
    pa, pb = parse_version_parts(a), parse_version_parts(b)
    if pa and pb:
        return pa[0:3] == pb[0:3]
    # Allow comparing full Hub version to bare X.Y.Z from changeset logs
    def xyz(v: str):
        p = parse_version_parts(v)
        if p:
            return p[0:3]
        parts = v.split(".")
        if len(parts) >= 3 and all(x.isdigit() for x in parts[:3]):
            return int(parts[0]), int(parts[1]), int(parts[2])
        return None
    xa, xb = xyz(a), xyz(b)
    return bool(xa and xb and xa == xb)


def get_hub_secondary_root() -> Optional[Path]:
    cfg = Path(os.path.expandvars(r"%APPDATA%\UnityHub\secondaryInstallPath.json"))
    if not cfg.exists():
        return None
    try:
        text = cfg.read_text(encoding="utf-8").strip().strip('"')
        p = Path(text)
        return p if p.exists() else None
    except OSError:
        return None


def editor_search_roots() -> List[Path]:
    roots: List[Path] = []
    secondary = get_hub_secondary_root()
    if secondary:
        roots.append(secondary)
    for r in DEFAULT_EDITOR_ROOTS:
        if r not in roots and r.exists():
            roots.append(r)
    return roots


def get_game_unity_version(game_root: Path | str) -> Optional[str]:
    """Read Unity version from <Game>_Data/globalgamemanagers under game_root."""
    root = Path(game_root)
    if not root.exists():
        return None
    candidates: List[Path] = []
    for data_dir in root.glob("*_Data"):
        ggm = data_dir / "globalgamemanagers"
        if ggm.is_file():
            candidates.append(ggm)
    # Prefer CoQ_Data / Elin_Data style names first (deterministic: shortest first then alpha)
    candidates.sort(key=lambda p: (len(p.parent.name), p.parent.name.lower()))
    for ggm in candidates:
        try:
            # Version string sits near the start of the file.
            blob = ggm.read_bytes()[:8192]
        except OSError:
            continue
        m = VERSION_RE.search(blob)
        if m:
            return m.group(1).decode("ascii", errors="ignore")
    return None


def list_installed_editors(roots: Optional[Iterable[Path]] = None) -> List[Tuple[str, Path]]:
    """Return [(version_folder_name, Unity.exe path), ...]."""
    out: List[Tuple[str, Path]] = []
    for root in roots or editor_search_roots():
        if not root.exists():
            continue
        for child in root.iterdir():
            if not child.is_dir():
                continue
            # Skip architecture suffix folders that wrap the real version when present.
            name = child.name
            if name.endswith("-x86_64"):
                continue
            ver = normalize_version_token(name)
            if not ver or not parse_version_parts(ver):
                # Bare X.Y.Z from weird folder names — skip; need lettered Hub builds
                continue
            exe = child / "Editor" / "Unity.exe"
            if not exe.is_file():
                # Some installs nest as <folder>/Unity.exe or <folder>/<ver>/Editor/Unity.exe
                alt = child / "Unity.exe"
                nested = list(child.glob("*/Editor/Unity.exe"))
                if alt.is_file():
                    exe = alt
                elif nested:
                    exe = nested[0]
                else:
                    continue
            out.append((ver, exe))
    # Prefer unique versions; first root wins.
    seen = set()
    unique: List[Tuple[str, Path]] = []
    for ver, exe in out:
        if ver in seen:
            continue
        seen.add(ver)
        unique.append((ver, exe))
    return unique


def install_hint(required: str) -> str:
    dest = get_hub_secondary_root() or Path(r"E:\tools\Unity_Editor")
    return (
        f"Install Unity {required} via Unity Hub into {dest}\\{required}\\ "
        f"(Editor\\Unity.exe). Re-run export after install. "
        f"PNG/.meta generation does not require the Editor."
    )


def _version_from_editor_path(path: Path) -> Optional[str]:
    cur = path
    for _ in range(6):
        m = re.search(r"(\d+\.\d+\.\d+[a-z]\d+)", cur.name, re.I)
        if m:
            return m.group(1)
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def find_matching_unity_editor(
    required: str,
    *,
    manual_path: Optional[str] = None,
    allow_mismatched_manual: bool = False,
) -> UnityMatch:
    """
    Strict match for required game version.
    Returns UnityMatch with editor_exe=None when no acceptable install exists.
    """
    hint = install_hint(required)
    if manual_path:
        mp = Path(manual_path)
        candidate: Optional[Path] = None
        if mp.is_file():
            candidate = mp
        elif (mp / "Editor" / "Unity.exe").is_file():
            candidate = mp / "Editor" / "Unity.exe"
        if candidate is not None:
            manual_ver = _version_from_editor_path(candidate)
            exact = bool(manual_ver and manual_ver.lower() == required.lower())
            sibling = bool(manual_ver and same_xyz(manual_ver, required))
            if not exact and not sibling and not allow_mismatched_manual:
                return UnityMatch(required, None, manual_ver, False, False, hint)
            return UnityMatch(
                required,
                str(candidate),
                manual_ver or required,
                exact,
                sibling and not exact,
                hint,
            )

    installed = list_installed_editors()
    # 1) Exact folder name
    for ver, exe in installed:
        if ver.lower() == required.lower():
            return UnityMatch(required, str(exe), ver, True, False, hint)

    # 2) Letter-sibling same X.Y.Z (f1 vs f2) when exact letter not present
    siblings = [(ver, exe) for ver, exe in installed if same_xyz(ver, required)]
    if siblings:
        siblings.sort(key=lambda t: t[0].lower())
        ver, exe = siblings[0]
        return UnityMatch(required, str(exe), ver, False, True, hint)

    return UnityMatch(required, None, None, False, False, hint)


def resolve_for_game(
    game_root: Path | str,
    *,
    manual_path: Optional[str] = None,
) -> Tuple[Optional[str], UnityMatch]:
    """Detect game version then resolve editor. Returns (version, match)."""
    ver = get_game_unity_version(game_root)
    if not ver:
        empty = UnityMatch(
            "",
            None,
            None,
            False,
            False,
            f"Could not detect Unity version under {game_root} "
            f"(expected *_Data/globalgamemanagers).",
        )
        return None, empty
    return ver, find_matching_unity_editor(ver, manual_path=manual_path)


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Detect / resolve Unity editor for a game")
    ap.add_argument("--game-root", required=True, help="Game install root")
    ap.add_argument("--manual", default=None, help="Override Unity.exe path")
    args = ap.parse_args()
    version, match = resolve_for_game(args.game_root, manual_path=args.manual)
    print(
        json.dumps(
            {
                "gameVersion": version,
                "editorExe": match.editor_exe,
                "matchedVersion": match.matched_version,
                "exact": match.exact,
                "letterSibling": match.letter_sibling,
                "installHint": match.install_hint,
                "installed": [{"version": v, "exe": str(e)} for v, e in list_installed_editors()],
            },
            indent=2,
        )
    )
