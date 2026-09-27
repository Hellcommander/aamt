#!/usr/bin/env python3
"""
Shared path resolution for the AAMT / Transcendence toolset.

Reads Tools/TranscendenceTools.ini (copy from TranscendenceTools.ini.example).
Environment variables always win over the INI. Missing keys fall back to
auto-detect / historical defaults.

Usage:
  from tool_paths import get_path, find_blender, tools_root

  blender = find_blender()
  sd_root = get_path("SDRoot")
"""

from __future__ import annotations

import configparser
import os
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

_SHARED = Path(__file__).resolve().parent
_TOOLS_ROOT = _SHARED.parent
_INI_NAME = "TranscendenceTools.ini"


def tools_root() -> Path:
    return _TOOLS_ROOT


def ini_path() -> Path:
    override = (os.environ.get("AAMT_TOOLS_INI") or "").strip().strip('"')
    if override:
        return Path(os.path.expandvars(override))
    return _TOOLS_ROOT / _INI_NAME


def _expand(raw: str) -> str:
    return os.path.expandvars(raw.strip().strip('"').strip("'"))


@lru_cache(maxsize=1)
def _load_ini() -> configparser.ConfigParser:
    """
    Load INI. Supports both sectioned keys ([Paths] BlenderPath=...) and the
    legacy flat style (TranscendencePath=... at top level → [Paths]).
    Keys are case-insensitive.
    """
    cp = configparser.ConfigParser(interpolation=None)
    path = ini_path()
    if not path.is_file():
        return cp

    text = path.read_text(encoding="utf-8-sig")
    # Flat legacy files have no [section] headers — wrap as [Paths].
    has_section = any(line.lstrip().startswith("[") and "]" in line for line in text.splitlines())
    if text.strip() and not has_section:
        text = "[Paths]\n" + text
    try:
        cp.read_string(text)
    except configparser.Error as exc:
        # Last resort: line-based key=value scrape into [Paths]
        cp = configparser.ConfigParser(interpolation=None)
        cp.add_section("Paths")
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            t = line.strip()
            if not t or t.startswith("#") or t.startswith(";") or t.startswith("["):
                continue
            if "=" not in t:
                continue
            k, _, v = t.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and v and not cp.has_option("Paths", k):
                cp.set("Paths", k, v)
        if not cp.options("Paths"):
            raise exc
    return cp


def clear_cache() -> None:
    """Call after writing a new INI in the same process."""
    _load_ini.cache_clear()


def _ini_get(key: str) -> Optional[str]:
    cp = _load_ini()
    key_l = key.lower()
    # Prefer [Paths], then other sections
    section_order = ["Paths"] + [s for s in cp.sections() if s != "Paths"]
    for section in section_order:
        if section not in cp:
            continue
        for opt in cp.options(section):
            if opt.lower() == key_l:
                val = _expand(cp.get(section, opt))
                if val:
                    return val
    return None


def get_path(
    key: str,
    *,
    env: Optional[Iterable[str]] = None,
    default: Optional[str] = None,
) -> Optional[Path]:
    """
    Resolve a path-like setting.

    Order: env names → INI key → default.
    Returns None if nothing resolves to an existing path (unless default is set
    and you only want the configured string — see get_setting).
    """
    for name in env or ():
        raw = (os.environ.get(name) or "").strip().strip('"')
        if not raw:
            continue
        p = Path(_expand(raw))
        return p
    ini_val = _ini_get(key)
    if ini_val:
        return Path(ini_val)
    if default:
        return Path(_expand(default))
    return None


def get_setting(
    key: str,
    *,
    env: Optional[Iterable[str]] = None,
    default: Optional[str] = None,
) -> Optional[str]:
    """Resolve a string setting (path or not). Does not require the path to exist."""
    for name in env or ():
        raw = (os.environ.get(name) or "").strip().strip('"')
        if raw:
            return _expand(raw)
    ini_val = _ini_get(key)
    if ini_val:
        return ini_val
    return default


def _as_blender_exe(p: Path) -> Optional[Path]:
    if p.is_file() and p.name.lower() == "blender.exe":
        return p
    if p.is_dir():
        exe = p / "blender.exe"
        if exe.is_file():
            return exe
    return None


def _scan_blender_roots(roots: Iterable[Path]) -> Optional[Path]:
    hits: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        hits.extend(root.glob("Blender */blender.exe"))
        # Also allow root itself to be the version folder
        direct = root / "blender.exe"
        if direct.is_file():
            hits.append(direct)
    if not hits:
        return None
    hits.sort(key=lambda p: p.as_posix().lower(), reverse=True)
    return hits[0]


def find_blender(explicit: Optional[str] = None) -> Optional[str]:
    """
    Locate blender.exe.

    Order: explicit → BLENDER* env → INI BlenderPath → INI BlenderRoots →
    PATH → common install roots.
    """
    if explicit:
        p = _as_blender_exe(Path(_expand(explicit)))
        if p:
            return str(p)

    for key in ("BLENDER", "BLENDER_PATH", "BLENDER_EXE"):
        raw = (os.environ.get(key) or "").strip().strip('"')
        if not raw:
            continue
        p = _as_blender_exe(Path(_expand(raw)))
        if p:
            return str(p)

    ini_blender = _ini_get("BlenderPath")
    if ini_blender:
        p = _as_blender_exe(Path(ini_blender))
        if p:
            return str(p)

    roots_raw = _ini_get("BlenderRoots") or ""
    if roots_raw:
        roots = [Path(_expand(x)) for x in roots_raw.replace(";", ",").split(",") if x.strip()]
        hit = _scan_blender_roots(roots)
        if hit:
            return str(hit)

    for name in ("blender", "Blender"):
        which = shutil.which(name)
        if which:
            return which

    # Defaults / migration-friendly roots (after INI so users can override)
    default_roots = [
        Path(r"E:\tools\Blender Foundation"),
        Path(r"D:\tools\Blender Foundation"),
        Path(r"C:\Program Files\Blender Foundation"),
        Path(r"C:\Program Files (x86)\Blender Foundation"),
        Path(r"D:\Program Files\Blender Foundation"),
        Path(r"E:\Program Files\Blender Foundation"),
    ]
    known = [
        Path(r"E:\tools\Blender Foundation\Blender 5.2\blender.exe"),
        Path(r"D:\tools\Blender Foundation\Blender 5.2\blender.exe"),
        Path(r"D:\tools\Blender Foundation\Blender 5.0\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"),
    ]
    for p in known:
        if p.is_file():
            return str(p)
    hit = _scan_blender_roots(default_roots)
    return str(hit) if hit else None


def sd_root() -> Path:
    p = get_path(
        "SDRoot",
        env=("AAMT_SD_ROOT", "SD35_ROOT"),
        default=r"E:\tools\sd3.5\sd3.5",
    )
    return p or Path(r"E:\tools\sd3.5\sd3.5")


def sd_python() -> Path:
    p = get_path(
        "SDPython",
        env=("AAMT_SD_PYTHON", "SD35_PYTHON"),
        default=r"E:\tools\miniconda3\python.exe",
    )
    if p and p.is_file():
        return p
    # Fall back to current interpreter
    import sys

    return Path(sys.executable)


def sd_port() -> int:
    raw = get_setting("SDPort", env=("AAMT_SD_PORT", "SD35_PORT"), default="1338") or "1338"
    try:
        return int(raw)
    except ValueError:
        return 1338


def sd_outputs_dir() -> Path:
    p = get_path(
        "SDOutputsDir",
        env=("AAMT_SD_OUTPUTS_DIR",),
        default=str(sd_root() / "outputs"),
    )
    return p or (sd_root() / "outputs")


def stable_audio_dir() -> Path:
    p = get_path(
        "StableAudioDir",
        env=("AAMT_STABLE_AUDIO_DIR",),
        default=r"E:\tools\stable-audio",
    )
    return p or Path(r"E:\tools\stable-audio")


def audio_library_dir() -> Path:
    """Purchased / made SFX packs (zip archives or loose wav/mp3)."""
    p = get_path(
        "AudioLibraryDir",
        env=("AAMT_AUDIO_LIBRARY_DIR",),
        default=r"D:\assets\audio",
    )
    return p or Path(r"D:\assets\audio")


def audio_index_dir() -> Path:
    """Sidecar embeddings + catalog for audio_asset_library (not inside the zips)."""
    p = get_path(
        "AudioIndexDir",
        env=("AAMT_AUDIO_INDEX_DIR",),
        default=str(audio_library_dir() / "_aamt_index"),
    )
    return p or (audio_library_dir() / "_aamt_index")


# ---------------------------------------------------------------------------
# Image-to-3D / material authoring resources (shared across game toolsets)
# ---------------------------------------------------------------------------


def hf_home() -> Path:
    """Hugging Face cache root. Kept off C: — models are tens of GB."""
    p = get_path("HfHome", env=("HF_HOME", "AAMT_HF_HOME"), default=r"D:\hf-cache")
    return p or Path(r"D:\hf-cache")


def trellis1_root() -> Path:
    """
    TRELLIS 1 Windows fork: https://github.com/IgorAherne/trellis-stable-projectorz

    float16 pipeline + int32 FlexiCubes (https://github.com/IgorAherne/flexicubes-stable-projectorz)
    so jetx/TRELLIS-image-large fits on 8 GB. Launch with --precision half.
    """
    p = get_path("Trellis1Root", env=("AAMT_TRELLIS1_ROOT",), default=r"D:\trellis")
    return p or Path(r"D:\trellis")


def trellis2_root() -> Path:
    """
    TRELLIS.2 Windows install (IgorAherne/TRELLIS.2-stableprojectorz).

    Upstream https://github.com/microsoft/TRELLIS.2 is Linux + 24 GB and more
    recent. This fork is the Windows + RAM-offload vehicle (low_vram keeps
    weights in system memory). It lags microsoft; do not treat it as upstream.
    """
    p = get_path("Trellis2Root", env=("AAMT_TRELLIS2_ROOT",), default=r"D:\trellis2")
    return p or Path(r"D:\trellis2")


def _trellis_code_root(root: Path) -> Path:
    nested = root / "code"
    if (nested / "api_spz" / "main_api.py").is_file():
        return nested
    return root


def _trellis_api_script(root: Path) -> Optional[Path]:
    script = _trellis_code_root(root) / "api_spz" / "main_api.py"
    return script if script.is_file() else None


def _looks_like_trellis1(root: Path) -> bool:
    if not root.is_dir():
        return False
    code = _trellis_code_root(root)
    if (code / "o-voxel").is_dir():
        return False
    return bool(_trellis_api_script(root) or (code / "trellis" / "pipelines").is_dir())


def _looks_like_trellis2(root: Path) -> bool:
    if not root.is_dir():
        return False
    code = _trellis_code_root(root)
    return (code / "o-voxel").is_dir() or (root / "code" / "trellis2_init_done.txt").is_file()


def trellis_variant() -> str:
    """
    Active mesh backend: trellis2 (recent 4B, Windows RAM-offload) | trellis1 (8GB fp16).

    auto: installed trellis2 first (this machine already has D:\\trellis2), else trellis1.
    """
    raw = (get_setting("TrellisVariant", env=("AAMT_TRELLIS_VARIANT",), default="auto") or "auto")
    raw = str(raw).strip().lower()
    aliases = {
        "trellis1": "trellis1",
        "trellis-1": "trellis1",
        "spz": "trellis1",
        "image-large": "trellis1",
        "trellis2": "trellis2",
        "trellis-2": "trellis2",
        "trellis.2": "trellis2",
        "4b": "trellis2",
    }
    if raw in aliases:
        return aliases[raw]
    if _looks_like_trellis2(trellis2_root()):
        return "trellis2"
    if _looks_like_trellis1(trellis1_root()):
        return "trellis1"
    return "trellis2"


def trellis_root() -> Path:
    """Install root for the active TRELLIS variant."""
    override = None
    for name in ("AAMT_TRELLIS_ROOT",):
        raw = (os.environ.get(name) or "").strip().strip('"')
        if raw:
            override = Path(_expand(raw))
            break
    if override is None:
        ini_val = _ini_get("TrellisRoot")
        if ini_val:
            override = Path(ini_val)
    if override is not None:
        return override
    return trellis1_root() if trellis_variant() == "trellis1" else trellis2_root()


def trellis_precision() -> str:
    """half = float16. Default for both backends on this 8-11 GB card."""
    raw = (get_setting("TrellisPrecision", env=("AAMT_TRELLIS_PRECISION",), default="half") or "half")
    raw = str(raw).strip().lower()
    if raw in ("full", "float32", "fp32"):
        return "full"
    return "half"


def trellis_launcher() -> Optional[Path]:
    """Windows .bat for the StableProjectorz one-click layout."""
    root = trellis_root()
    for rel in (
        Path("run-stableprojectorz") / "run-stableprojectorz.bat",
        Path("run-stableprojectorz.bat"),
    ):
        bat = root / rel
        if bat.is_file():
            return bat
    return None


def trellis_api_script() -> Optional[Path]:
    return _trellis_api_script(trellis_root())


def trellis_python() -> Optional[Path]:
    code = _trellis_code_root(trellis_root())
    for candidate in (
        code / "venv" / "Scripts" / "python.exe",
        trellis_root() / "tools" / "python" / "python.exe",
    ):
        if candidate.is_file():
            return candidate
    return None


def trellis_port() -> int:
    raw = get_setting("TrellisPort", env=("AAMT_TRELLIS_PORT",), default="7960") or "7960"
    try:
        return int(raw)
    except ValueError:
        return 7960


def trellis_backends() -> list:
    """Selectable mesh backends. Installs stay outside git."""
    active = trellis_variant()
    return [
        {
            "id": "trellis2",
            "name": "TRELLIS.2-4B (Windows RAM-offload)",
            "vram": "8-11GB via low_vram CPU offload + fp16; upstream microsoft wants 24GB Linux",
            "root": str(trellis2_root()),
            "installed": _looks_like_trellis2(trellis2_root()),
            "active": active == "trellis2",
            "outdated_vs_upstream": True,
            "windows": True,
            "ram_offload": True,
            "repo": "https://github.com/IgorAherne/TRELLIS.2-stableprojectorz",
            "upstream": "https://github.com/microsoft/TRELLIS.2",
        },
        {
            "id": "trellis1",
            "name": "TRELLIS-image-large (fp16 + int32 FlexiCubes)",
            "vram": "8GB half-precision (float16 pipeline, int32 FlexiCubes)",
            "root": str(trellis1_root()),
            "installed": _looks_like_trellis1(trellis1_root()),
            "active": active == "trellis1",
            "outdated_vs_upstream": False,
            "windows": True,
            "ram_offload": True,
            "repo": "https://github.com/IgorAherne/trellis-stable-projectorz",
            "flexicubes": "https://github.com/IgorAherne/flexicubes-stable-projectorz",
        },
    ]


def pixelorama_exe() -> Optional[Path]:
    """
    Pixelorama (Godot pixel-art editor). AI host is Shared/pixelorama_client.py.

    Default install on this machine: D:\\tools\\Orama Interactive\\Pixelorama\\Pixelorama.exe
    """
    p = get_path(
        "PixeloramaExe",
        env=("AAMT_PIXELORAMA", "PIXELORAMA"),
        default=r"D:\tools\Orama Interactive\Pixelorama\Pixelorama.exe",
    )
    if p and p.is_file():
        return p
    if p and p.is_dir():
        exe = p / "Pixelorama.exe"
        if exe.is_file():
            return exe
    root = get_path("PixeloramaRoot", env=("AAMT_PIXELORAMA_ROOT",))
    if root:
        exe = root / "Pixelorama.exe"
        if exe.is_file():
            return exe
    which = shutil.which("Pixelorama")
    return Path(which) if which else None


def material_maker_exe() -> Optional[Path]:
    """
    Material Maker (procedural, seamless PBR authoring).

    NOTE: the 1.7 headless --export-material path segfaults on any graph with
    more than one output map, so treat this as GUI-authoring-first.
    """
    p = get_path(
        "MaterialMakerExe",
        env=("AAMT_MATERIAL_MAKER",),
        default=r"D:\tools\Texture_Making_tools\material_maker_1_7_windows\material_maker.exe",
    )
    if p and p.is_file():
        return p
    root = get_path("MaterialMakerRoot", env=("AAMT_MATERIAL_MAKER_ROOT",))
    if root:
        exe = root / "material_maker.exe"
        if exe.is_file():
            return exe
    return None


def blender_user_scripts() -> Optional[Path]:
    """Blender's per-user scripts dir (where add-ons are installed)."""
    explicit = get_path("BlenderUserScripts", env=("AAMT_BLENDER_USER_SCRIPTS",))
    if explicit and explicit.is_dir():
        return explicit
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    base = Path(appdata) / "Blender Foundation" / "Blender"
    if not base.is_dir():
        return None
    versions = sorted((d for d in base.iterdir() if d.is_dir()), key=lambda d: d.name, reverse=True)
    for ver in versions:
        scripts = ver / "scripts"
        if scripts.is_dir():
            return scripts
    return None


def ucupaint_addon_dir() -> Optional[Path]:
    """Ucupaint (layered texture painting + baking) add-on folder, if installed."""
    explicit = get_path("UcupaintDir", env=("AAMT_UCUPAINT_DIR",))
    if explicit and explicit.is_dir():
        return explicit
    scripts = blender_user_scripts()
    if not scripts:
        return None
    for candidate in (scripts / "addons" / "ucupaint", scripts.parent / "extensions" / "user_default" / "ucupaint"):
        if candidate.is_dir():
            return candidate
    return None


def texconv_exe() -> Optional[Path]:
    """DirectXTex texconv — DDS compression for engine-ready textures."""
    p = get_path(
        "TexconvExe",
        env=("AAMT_TEXCONV",),
        default=r"D:\decompilers\DirectXTex\texconv.exe",
    )
    if p and p.is_file():
        return p
    which = shutil.which("texconv")
    return Path(which) if which else None


def output_dir() -> Path:
    p = get_path("OutputDir", env=("AAMT_OUTPUT_DIR",), default=r"C:\Output")
    return p or Path(r"C:\Output")


def transcendence_root() -> Optional[Path]:
    p = get_path(
        "TranscendencePath",
        env=("AAMT_TRANSCENDENCE_ROOT", "TRANSCENDENCE_ROOT"),
    )
    if p and p.is_dir():
        return p
    # Tools live under <Game>/Tools → parent of Tools
    candidate = _TOOLS_ROOT.parent
    if (candidate / "Transcendence.tdb").is_file() or (candidate / "Extensions").is_dir():
        return candidate
    return p


if __name__ == "__main__":
    print(f"INI: {ini_path()} exists={ini_path().is_file()}")
    print(f"Blender: {find_blender()}")
    print(f"SDRoot: {sd_root()}")
    print(f"SDPython: {sd_python()}")
    print(f"SDPort: {sd_port()}")
    print(f"SDOutputs: {sd_outputs_dir()}")
    print(f"StableAudio: {stable_audio_dir()}")
    print(f"AudioLibrary: {audio_library_dir()}")
    print(f"AudioIndex: {audio_index_dir()}")
    print(f"OutputDir: {output_dir()}")
    print(f"Transcendence: {transcendence_root()}")
    print(f"HfHome: {hf_home()}")
    print(f"TrellisRoot: {trellis_root()} variant={trellis_variant()} precision={trellis_precision()} launcher={trellis_launcher()} port={trellis_port()}")
    print(f"MaterialMaker: {material_maker_exe()}")
    print(f"Pixelorama: {pixelorama_exe()}")
    print(f"Ucupaint: {ucupaint_addon_dir()}")
    print(f"Texconv: {texconv_exe()}")
