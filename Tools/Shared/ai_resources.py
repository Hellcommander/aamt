#!/usr/bin/env python3
"""One entry point for the shared AI asset-generation resources.

Any game toolset (or agent) can ask "what can this machine generate right now?"
and get a straight answer, instead of each tool re-implementing detection.

  python ai_resources.py                 # human-readable status
  python ai_resources.py --json          # machine-readable
  python ai_resources.py --ensure image  # start what's needed

From code:

    from ai_resources import resources, ensure, make_image, make_mesh, make_audio

    ensure("mesh")                       # start TRELLIS if it's down
    ref  = make_image("a mossy stone idol", Path("ref.png"))
    mesh = make_mesh(ref, Path("idol.glb"))
    sfx  = make_audio("short plasma vent burst", Path("vent.wav"), archetype="laser")

Stages and who owns them:

  image     Stable Diffusion 3.5    concept art, reference shots, detail overlays
  mesh      TRELLIS.2-4B FP16      RAM-offload image -> textured mesh (11 GB)
  material  Material Maker          seamless, tileable, exact PBR base maps
  pixels    Pixelorama              pixel-art .pxo inspect/export + visible GUI
  layering  Ucupaint (Blender)      composite + mask the above onto a mesh's UVs
  compress  DirectXTex texconv      engine-ready DDS/BCn output
  audio     Stable Audio 3 + lib    SFX from purchased/made packs at D:\\assets\\audio

GPU note: this box has one 11 GB card, so every GPU-heavy call routes through
Common/gpu_hub.py. Two model servers can be *resident* at once, but they must
not *generate* at once — and Material Maker crashes outright if VRAM is tight.
Pixelorama headless export takes the same lock (Godot renders on the GPU).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

STAGES = ("image", "mesh", "material", "pixels", "layering", "compress", "audio")


# --------------------------------------------------------------------------
# discovery
# --------------------------------------------------------------------------


def _safe(fn: Callable[[], Any], default: Any = None) -> Any:
    try:
        return fn()
    except Exception:
        return default


def _image_status() -> Dict[str, Any]:
    import sd_http_client as sd

    ping: Dict[str, Any] = {}
    try:
        from sd_server_lifecycle import sd_status

        ping = sd_status() or {}
    except Exception:
        ping = {}
    aamt = str(ping.get("version") or "").startswith("aamt-1338")
    url = _safe(lambda: sd.detect_server(verbose=False))
    foreign = bool(ping) and not aamt
    info = {
        "stage": "image",
        "name": "Stable Diffusion 3.5",
        "ready": bool(url),
        "endpoint": url,
        "loaded": ping.get("loaded") if aamt else None,
        "version": ping.get("version"),
        "token_ok": ping.get("token_ok") if aamt else None,
        "img2img": ping.get("img2img") if aamt else None,
        "kind": "http-server",
        "gpu": True,
        "start": "Tools\\Start-StableDiffusionServer.ps1",
        "token_profile": "media",
        "api": "POST /v1/images/generations",
        "aamt": aamt,
        "foreign": foreign,
        "process": (
            "ensure('image') then make_image() / sd_http_client.generate_image; "
            "Soulash 2 tiles: SkillCreator generate-icons. Do not use Cursor image gen."
        ),
    }
    if foreign:
        info["caveat"] = (
            "Port 1338 is a foreign SD process (often Starfield SFMAG sd_server.py), "
            "not aamt-1338. ensure('image') replaces it."
        )
    return info


def _mesh_status() -> Dict[str, Any]:
    import trellis_http_client as tr

    url = _safe(lambda: tr.detect_server(verbose=False))
    root = _safe(tr._root)
    variant = "trellis2"
    precision = "half"
    backends = []
    try:
        from tool_paths import trellis_variant, trellis_precision, trellis_backends

        variant = trellis_variant()
        precision = trellis_precision()
        backends = trellis_backends()
    except Exception:
        pass
    names = {
        "trellis2": "TRELLIS.2-4B FP16 (RAM offload)",
        "trellis1": "TRELLIS-image-large (fp16)",
    }
    return {
        "stage": "mesh",
        "name": names.get(variant, "TRELLIS"),
        "variant": variant,
        "precision": precision,
        "ready": bool(url),
        "endpoint": url,
        "installed": bool(root and Path(root).is_dir()),
        "kind": "http-server",
        "gpu": True,
        "ram_offload": True,
        "busy": _safe(tr.server_busy, False),
        "start": "Shared\\trellis_http_client.py --start",
        "options": backends,
        "caveat": (
            "11 GB 2080 Ti: float16 + CPU/RAM offload only. "
            "Do not load this into vLLM/SGLang. Default voxel tier is 512."
        ),
    }


def _material_status() -> Dict[str, Any]:
    import material_maker_client as mm

    info = mm.status()
    return {
        "stage": "material",
        "name": "Material Maker",
        "ready": bool(info.get("available")),
        "exe": info.get("exe"),
        "kind": "cli",
        "gpu": True,
        "caveat": info.get("known_limitation"),
    }


def _pixels_status() -> Dict[str, Any]:
    import pixelorama_client as px

    info = px.status()
    gui = info.get("gui") or {}
    return {
        "stage": "pixels",
        "name": "Pixelorama",
        "ready": bool(info.get("available")),
        "exe": info.get("exe"),
        "kind": "godot-cli + visible-gui",
        "gpu": True,
        "gui_running": bool(gui.get("running")),
        "start": "python Shared\\pixelorama_client.py open",
        "see": "python Shared\\pixelorama_client.py see --out Tools\\Logs\\pixelorama\\see.png",
        "docs": "Shared\\PIXELORAMA.md",
    }


def _layering_status() -> Dict[str, Any]:
    import ucupaint_support as uc

    info = uc.status()
    return {
        "stage": "layering",
        "name": "Ucupaint",
        "ready": bool(info.get("installed")),
        "version": info.get("version"),
        "kind": "blender-addon",
        "gpu": False,
        "blender_installs": [
            e["blender_version"] for e in info.get("installations", []) if e.get("installed")
        ],
    }


def _audio_status() -> Dict[str, Any]:
    library = None
    index = None
    assets = 0
    try:
        from tool_paths import audio_index_dir, audio_library_dir

        library = audio_library_dir()
        index = audio_index_dir()
    except Exception:
        library = Path(r"D:\assets\audio")
        index = library / "_aamt_index"
    cat = Path(index) / "catalog.json" if index else None
    if cat and cat.is_file():
        try:
            assets = len(json.loads(cat.read_text(encoding="utf-8")).get("records") or [])
        except Exception:
            assets = 0
    sa3_ready = False
    sa3_error = ""
    try:
        import aamt_stable_audio_backend as sa3

        sa3_ready = bool(sa3.is_available())
        sa3_error = sa3.last_error() or ""
    except Exception as exc:
        sa3_error = str(exc)
    lib_ok = bool(library and Path(library).is_dir())
    return {
        "stage": "audio",
        "name": "Stable Audio 3 + asset library",
        "ready": lib_ok and (sa3_ready or assets > 0),
        "library": str(library) if library else None,
        "index": str(index) if index else None,
        "assets": assets,
        "stable_audio": sa3_ready,
        "kind": "in-process + zip library",
        "gpu": True,
        "error": sa3_error or None,
        "start": "python Shared\\audio_pipeline.py ingest --fast",
        "process": (
            "ensure('audio') then make_audio(); retrieve from D:\\assets\\audio, "
            "condition SA3 with init_audio, or mix library clips if SA3 is down."
        ),
    }


def _compress_status() -> Dict[str, Any]:
    exe = None
    try:
        from tool_paths import texconv_exe

        exe = texconv_exe()
    except Exception:
        pass
    return {
        "stage": "compress",
        "name": "DirectXTex texconv",
        "ready": exe is not None,
        "exe": str(exe) if exe else None,
        "kind": "cli",
        "gpu": False,
    }


_PROBES: Dict[str, Callable[[], Dict[str, Any]]] = {
    "image": _image_status,
    "mesh": _mesh_status,
    "material": _material_status,
    "pixels": _pixels_status,
    "layering": _layering_status,
    "compress": _compress_status,
    "audio": _audio_status,
}


def resources(stages: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    """Probe every stage (or a subset). Never raises — unreachable stages report ready=False."""
    out: Dict[str, Dict[str, Any]] = {}
    for stage in stages or STAGES:
        probe = _PROBES.get(stage)
        if not probe:
            continue
        try:
            out[stage] = probe()
        except Exception as exc:
            out[stage] = {"stage": stage, "ready": False, "error": str(exc)}
    return out


def gpu_holder() -> Optional[Dict[str, Any]]:
    """Who currently holds the shared GPU lock, if anyone."""
    try:
        from gpu_hub import current_holder

        return current_holder()
    except Exception:
        return None


def ensure(stage: str, *, wait: float = 2400.0) -> Dict[str, Any]:
    """Bring a stage up if it isn't already. Only the server stages can be started."""
    if stage == "image":
        import sd_http_client as sd

        url = sd.detect_server(verbose=False)
        if url:
            return {"stage": stage, "ready": True, "endpoint": url, "started": False}
        # The server arms a 180 s idle shutdown, so it is routinely down between
        # batches. Launch it rather than making every caller do it by hand.
        try:
            from sd_server_lifecycle import ensure_sd_server

            started = ensure_sd_server(timeout_sec=wait)
        except Exception as exc:  # noqa: BLE001
            return {"stage": stage, "ready": False, "error": f"SD autostart failed: {exc}"}
        if not started:
            return {
                "stage": stage,
                "ready": False,
                "error": "SD autostart timed out: Tools\\Start-StableDiffusionServer.ps1",
            }
        return {
            "stage": stage,
            "ready": True,
            "endpoint": sd.detect_server(verbose=False),
            "started": True,
        }

    if stage == "mesh":
        import trellis_http_client as tr

        url = tr.detect_server(verbose=False)
        if url:
            return {"stage": stage, "ready": True, "endpoint": url, "started": False}
        url = tr.start_server(wait_seconds=wait)
        return {"stage": stage, "ready": bool(url), "endpoint": url, "started": True}

    if stage == "audio":
        info = _audio_status()
        indexed = int(info.get("assets") or 0) > 0
        if info.get("library") and not indexed:
            info = {
                **info,
                "ready": bool(info.get("ready")),
                "started": False,
                "hint": "python Shared\\audio_pipeline.py ingest --fast",
            }
        return {"stage": stage, "started": False, **info}

    info = resources([stage]).get(stage, {})
    return {"stage": stage, "ready": bool(info.get("ready")), "started": False, **info}


# --------------------------------------------------------------------------
# thin generation facade
# --------------------------------------------------------------------------


def make_image(prompt: str, output: Path, **kwargs: Any) -> Path:
    """Reference/concept image via SD3.5. Waits for :1338. Takes the GPU lock.

    Never falls back to procedural PIL. If the image stage cannot come up,
    raises — leave placeholders alone rather than stamping junk rings.
    """
    from sd_server_lifecycle import require_sd_server

    wait = float(kwargs.pop("ensure_wait", os.environ.get("AAMT_SD_WAIT_SEC") or 2400.0))
    api_url = kwargs.pop("api_url", None) or require_sd_server(timeout_sec=wait)
    from sd_http_client import generate_image

    return generate_image(prompt=prompt, output_path=Path(output), api_url=api_url, **kwargs)


def make_mesh(image: Path, output: Path, **kwargs: Any) -> Path:
    """Image -> textured GLB via TRELLIS.2 FP16 + RAM offload (or TRELLIS 1).

    Stops TRELLIS after the job unless AAMT_TRELLIS_KEEP_SERVER=1.
    """
    from trellis_http_client import generate_mesh

    return generate_mesh(Path(image), Path(output), **kwargs)


def make_material(ptex: Path, out_dir: Path, **kwargs: Any) -> Dict[str, Any]:
    """Procedural tileable PBR maps via Material Maker."""
    from material_maker_client import export

    return export(Path(ptex), Path(out_dir), **kwargs)


def make_pixels(project: Path, out: Path, **kwargs: Any) -> Dict[str, Any]:
    """Export a Pixelorama .pxo (headless). Takes the GPU lock. Open the GUI with pixelorama_client.open_gui."""
    from pixelorama_client import export_project

    return export_project(Path(project), Path(out), **kwargs)


def make_audio(prompt: str, output: Path, **kwargs: Any) -> Path:
    """SFX via library retrieval + Stable Audio 3. Takes the GPU lock when SA3 runs."""
    from audio_pipeline import generate_audio

    return generate_audio(prompt, Path(output), **kwargs)


def compress_texture(pngs: List[Path], out_dir: Path, dds_format: str, extra: Optional[List[str]] = None) -> int:
    """PNG -> DDS via texconv. Caller picks the BCn format for its engine."""
    import subprocess

    from tool_paths import texconv_exe

    exe = texconv_exe()
    if not exe:
        raise RuntimeError("texconv not found")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [str(exe), "-y", "-nologo", "-f", dds_format, *(extra or []), "-o", str(out_dir)]
    cmd += [str(p) for p in pngs]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"texconv failed ({dds_format}): {(proc.stderr or proc.stdout)[-400:]}")
    return len(pngs)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Shared AI asset-generation resources")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--stage", action="append", choices=list(STAGES), default=None)
    parser.add_argument("--ensure", choices=list(STAGES), default=None)
    args = parser.parse_args()

    if args.ensure:
        result = ensure(args.ensure)
        print(json.dumps(result, indent=2))
        return 0 if result.get("ready") else 1

    report = resources(args.stage)
    holder = gpu_holder()

    if args.json:
        print(json.dumps({"resources": report, "gpu_lock": holder}, indent=2))
        return 0

    print("Shared AI asset resources\n")
    for stage in STAGES:
        info = report.get(stage)
        if not info:
            continue
        flag = "READY" if info.get("ready") else "DOWN "
        detail = info.get("endpoint") or info.get("exe") or info.get("addon_dir") or info.get("library") or ""
        print(f"  [{flag}] {stage:9} {info.get('name','?'):24} {detail}")
        if stage == "image" and info.get("ready"):
            print(
                f"            loaded={info.get('loaded')}  version={info.get('version')}  "
                f"token_ok={info.get('token_ok')}  img2img={info.get('img2img')}"
            )
        if stage == "audio" and info.get("ready"):
            print(
                f"            assets={info.get('assets')}  stable_audio={info.get('stable_audio')}  "
                f"index={info.get('index')}"
            )
        if info.get("caveat"):
            print(f"            caveat: {info['caveat']}")
        if not info.get("ready") and info.get("start"):
            print(f"            start:  {info['start']}")
    print()
    if holder:
        print(f"  GPU lock held by pid {holder.get('pid')}: {holder.get('label')!r}")
    else:
        print("  GPU lock free")
    return 0


if __name__ == "__main__":
    sys.exit(main())
