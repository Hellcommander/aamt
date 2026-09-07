#!/usr/bin/env python3
"""Transcendence adapter for Tools/Shared AI asset resources.

Every Transcendence generator should go through this module instead of
talking to SD / TRELLIS / Material Maker / Blender / audio by hand. The Shared
folder owns the stages (see Shared/AGENTS.md and Shared/AI_ASSET_RESOURCES.md):

  image     SD3.5 on :1338          make_image / ensure("image")
  mesh      TRELLIS.2 on :7960      make_mesh
  material  Material Maker CLI      make_material
  compress  texconv                 compress_texture
  audio     SA3 + D:\\assets\\audio  make_audio
  blender   tool_paths.find_blender

Usage from a generator:

    import tx_ai_pipeline as tx
    with tx.session():  # start SD + TRELLIS; stop both when the block ends
        tx.generate_image("bioluminescent whale hull, top-down", out.png, kind="texture", size=512)
        tx.concept_mesh(prompt, ship.glb)
    # GPU servers are down so Blender/Ucupaint can bake
    tx.bake_onto_mesh(ship.glb, bake_dir, skin_dir=skins, name="ship")

CLI:

    python tx_ai_pipeline.py probe
    python tx_ai_pipeline.py session
    python tx_ai_pipeline.py release
    python tx_ai_pipeline.py image --prompt "..." --out icon.png --kind icon --size 96
    python tx_ai_pipeline.py concept-mesh --prompt "..." --out ship.glb
    python tx_ai_pipeline.py bake --mesh ship.glb --out-dir baked --skin-dir skins --name ship
    python tx_ai_pipeline.py audio --prompt "whale EM chirp" --out idle.wav --archetype alien
    python tx_ai_pipeline.py hd-facings --id scSpaceWhale
"""

from __future__ import annotations

import argparse
import atexit
import json
import os
import shutil
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple, Union

_TX = Path(__file__).resolve().parent
_TOOLS = _TX.parent
_SHARED = _TOOLS / "Shared"
for _p in (_TX, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

TX_NEGATIVE = (
    "text, logo, watermark, letters, ui, frame, border, multiple objects, "
    "photograph, blurry, lowres, jpeg artifacts, empty black image, "
    "2d sprite, top-down icon, flat orthographic game tile"
)

# TRELLIS reconstructs a 3D mesh from this image. Transcendence 2.5D is the
# later Blender 120-facing spritesheet of that mesh — not a 2D concept drawing.
TRELLIS_CONCEPT_PROMPT = (
    "no text, no watermark, cinematic 3D concept art, three-quarter view, "
    "single complete object centered, studio lighting, physically based materials, "
    "dark void, Unreal Engine cinematic sculpt. Not a 2D sprite, not top-down."
)
STARFIELD_MESH_DIR = _SHARED / "Concepts" / "meshes"


def _import_ai():
    import ai_resources  # noqa: WPS433

    return ai_resources


def probe() -> Dict[str, Any]:
    """Machine snapshot of Shared stages + GPU lock + Blender."""
    ai = _import_ai()
    report = {
        "resources": ai.resources(),
        "gpu_lock": ai.gpu_holder(),
        "blender": find_blender(),
        "transcendence": str(transcendence_root() or ""),
        "shared": str(_SHARED),
    }
    try:
        from aamt_stable_audio_backend import is_available, last_error

        report["stable_audio"] = {"ready": bool(is_available()), "error": last_error() or ""}
    except Exception as exc:  # noqa: BLE001
        report["stable_audio"] = {"ready": False, "error": str(exc)}
    return report


def print_probe(report: Optional[Dict[str, Any]] = None) -> None:
    report = report or probe()
    print("Transcendence Shared AI pipeline")
    print(f"  Shared: {_SHARED}")
    resources = report.get("resources") or {}
    for stage in ("image", "mesh", "material", "layering", "compress", "audio"):
        info = resources.get(stage) or {}
        flag = "READY" if info.get("ready") else "DOWN "
        detail = info.get("endpoint") or info.get("exe") or info.get("addon_dir") or info.get("library") or ""
        print(f"  [{flag}] {stage:9} {info.get('name', '?'):24} {detail}")
        if not info.get("ready") and info.get("start"):
            print(f"            start: {info['start']}")
        if stage == "audio" and info.get("assets") is not None:
            print(f"            assets={info.get('assets')}  stable_audio={info.get('stable_audio')}")
    holder = report.get("gpu_lock")
    if holder:
        print(f"  GPU lock held by pid {holder.get('pid')}: {holder.get('label')!r}")
    else:
        print("  GPU lock free")
    print(f"  Blender: {report.get('blender') or '(not found)'}")
    audio = report.get("stable_audio") or {}
    if audio and "ready" in audio:
        print(f"  Stable Audio import: {'OK' if audio.get('ready') else 'DOWN'}")
    if report.get("transcendence"):
        print(f"  Game: {report['transcendence']}")


def resolve_concept_art(
    entry: Optional[Dict[str, Any]] = None,
    *,
    path: str = "",
) -> Optional[Path]:
    """Find a 3D concept PNG under Transcendence/References or Shared/Concepts."""
    raw = path or (entry or {}).get("conceptArt") or (entry or {}).get("referenceImage") or ""
    if not raw:
        return None
    p = Path(str(raw))
    candidates = [
        p,
        _TX / raw,
        _TX / "References" / p.name,
        _SHARED / "Concepts" / p.name,
    ]
    for c in candidates:
        if c.is_file():
            return c.resolve()
    return None


def publish_starfield_mesh(glb: Path | str, asset_id: str = "") -> Optional[Path]:
    """Copy the TRELLIS GLB so a Starfield mod can consume the same 3D mesh."""
    src = Path(glb)
    if not src.is_file():
        return None
    stem = asset_id or src.stem
    dest = STARFIELD_MESH_DIR / f"{stem}.glb"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    meta = {
        "id": stem,
        "glb": str(dest),
        "source": str(src),
        "consumers": [
            "Transcendence: Blender 120-facing spritesheet (2.5D)",
            "Starfield: in-game mesh (this GLB)",
        ],
    }
    dest.with_suffix(".json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[tx] Starfield mesh copy: {dest}")
    return dest


_SESSION_HELD = False


def _keep_from_env() -> bool:
    return os.environ.get("AAMT_SD_KEEP_SERVER", "").strip().lower() in ("1", "true", "yes", "on")


def prepare(
    *,
    image: bool = True,
    mesh: bool = True,
    keep_server: bool = False,
    wait: float = 2400.0,
) -> Dict[str, Any]:
    """Bring Shared stages up for a Transcendence job.

    Starts **both** SD (:1338) and TRELLIS (:7960) by default. Does not leave
    them running unless keep_server / AAMT_SD_KEEP_SERVER is set — call
    ``release()`` or use ``session()`` so Blender/Ucupaint can have the GPU.
    """
    if keep_server:
        os.environ["AAMT_SD_KEEP_SERVER"] = "1"
        # Shared trellis_http_client stops :7960 after every GLB unless this is set.
        os.environ["AAMT_TRELLIS_KEEP_SERVER"] = "1"
    ai = _import_ai()
    out: Dict[str, Any] = {}
    if image:
        out["image"] = ai.ensure("image", wait=wait)
        if out["image"].get("ready"):
            print(f"[tx] image stage ready at {out['image'].get('endpoint')}")
        else:
            print(f"[tx] image stage DOWN: {out['image'].get('error') or 'see Shared/AGENTS.md'}")
    if mesh:
        out["mesh"] = ai.ensure("mesh", wait=wait)
        if out["mesh"].get("ready"):
            print(f"[tx] mesh stage ready at {out['mesh'].get('endpoint')}")
        else:
            print(f"[tx] mesh stage DOWN: {out['mesh'].get('error') or 'TRELLIS not started'}")
    return out


def release(*, force: bool = True) -> Dict[str, bool]:
    """Stop SD and TRELLIS so VRAM is free for Ucupaint / spritesheet export."""
    global _SESSION_HELD
    out = {"image": False, "mesh": False}
    try:
        from sd_server_lifecycle import stop_sd_server

        out["image"] = bool(stop_sd_server(force=force))
        print("[tx] SD stopped" if out["image"] else "[tx] SD still up after stop")
    except Exception as exc:  # noqa: BLE001
        print(f"[tx] SD stop failed: {exc}", file=sys.stderr)
    try:
        from trellis_http_client import stop_server

        out["mesh"] = bool(stop_server(force=force))
    except Exception as exc:  # noqa: BLE001
        print(f"[tx] TRELLIS stop failed: {exc}", file=sys.stderr)
    os.environ.pop("AAMT_SD_KEEP_SERVER", None)
    os.environ.pop("AAMT_TRELLIS_KEEP_SERVER", None)
    _SESSION_HELD = False
    return out


def _atexit_release() -> None:
    if _SESSION_HELD and not _keep_from_env():
        release(force=True)


@contextmanager
def session(
    *,
    image: bool = True,
    mesh: bool = True,
    keep: Optional[bool] = None,
    wait: float = 2400.0,
) -> Iterator[Dict[str, Any]]:
    """Start both GPU servers for the job; stop both afterward unless keep.

    Sets ``AAMT_TRELLIS_KEEP_SERVER`` for the duration so a batch of
    ``make_mesh`` calls does not kill :7960 after the first GLB. ``release()``
    clears that flag and stops both servers.
    """
    global _SESSION_HELD
    if keep is None:
        keep = _keep_from_env()
    if mesh:
        os.environ["AAMT_TRELLIS_KEEP_SERVER"] = "1"
    started = prepare(image=image, mesh=mesh, keep_server=bool(keep), wait=wait)
    _SESSION_HELD = True
    atexit.register(_atexit_release)
    try:
        yield started
    finally:
        if not keep:
            release(force=True)
        _SESSION_HELD = False


def image_ready() -> bool:
    try:
        from sd_http_client import detect_server

        return bool(detect_server(verbose=False))
    except Exception:
        return False


def mesh_ready() -> bool:
    try:
        from trellis_http_client import detect_server

        return bool(detect_server(verbose=False))
    except Exception:
        return False


def plan_image(delivery_w: int, delivery_h: int, kind: str = "texture") -> Tuple[int, int, int]:
    from sd_http_client import plan_sd_size

    return plan_sd_size(delivery_w, delivery_h, kind)


def generate_image(
    prompt: str,
    output: Path | str,
    *,
    kind: str = "texture",
    size: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    negative_prompt: str = TX_NEGATIVE,
    seed: int = 0,
    steps: Optional[int] = None,
    guidance_scale: float = 7.0,
    reference_image: Optional[str] = None,
    image_strength: float = 0.65,
    autostart: bool = True,
) -> Optional[Path]:
    """SD3.5 image via Shared/ai_resources.make_image. Returns None on failure."""
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    dw = int(width or size or 512)
    dh = int(height or size or dw)
    try:
        gw, gh, plan_steps = plan_image(dw, dh, kind)
    except Exception:
        gw, gh, plan_steps = 512, 512, 24
    gen_steps = int(steps if steps is not None else plan_steps)
    try:
        if autostart:
            _import_ai().ensure("image")
        from ai_resources import make_image

        make_image(
            prompt,
            out,
            negative_prompt=negative_prompt,
            width=gw,
            height=gh,
            steps=gen_steps,
            guidance_scale=guidance_scale,
            seed=int(seed),
            reference_image=reference_image,
            image_strength=float(image_strength),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[tx] SD image failed: {exc}", file=sys.stderr)
        return None
    if not out.is_file():
        return None
    if (dw, dh) != (gw, gh):
        try:
            from PIL import Image

            im = Image.open(out)
            if im.size != (dw, dh):
                im = im.convert("RGBA").resize((dw, dh), Image.Resampling.LANCZOS)
                im.save(out)
        except Exception:
            pass
    return out


def generate_mesh(
    image: Path | str,
    output: Path | str,
    *,
    autostart: bool = True,
    **kwargs: Any,
) -> Optional[Path]:
    """TRELLIS image→GLB. Autostarts TRELLIS unless the caller already prepared it.

    Shared stops TRELLIS after each GLB unless ``AAMT_TRELLIS_KEEP_SERVER=1``
    (set by ``session()`` / ``prepare(keep_server=True)``).
    """
    img = Path(image)
    out = Path(output)
    if not img.is_file():
        return None
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        if autostart:
            _import_ai().ensure("mesh")
        elif not mesh_ready():
            return None
        from ai_resources import make_mesh

        make_mesh(img, out, **kwargs)
    except Exception as exc:  # noqa: BLE001
        print(f"[tx] TRELLIS mesh failed: {exc}", file=sys.stderr)
        return None
    return out if out.is_file() else None


def generate_audio(
    prompt: str,
    output: Path | str,
    *,
    duration: float = 2.5,
    archetype: str = "",
    strength: float = 0.65,
    **kwargs: Any,
) -> Optional[Path]:
    """Library-conditioned SFX via Shared/ai_resources.make_audio."""
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        from ai_resources import make_audio

        make_audio(
            prompt,
            out,
            duration=duration,
            archetype=archetype,
            strength=strength,
            **kwargs,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[tx] audio failed: {exc}", file=sys.stderr)
        return None
    return out if out.is_file() else None


def concept_mesh(
    prompt: str,
    glb: Path | str,
    *,
    concept: Optional[Path | str] = None,
    kind: str = "default",
    size: int = 768,
    autostart_mesh: bool = True,
    seed: int = 0,
    reference_image: Optional[str] = None,
    asset_id: str = "",
    publish_starfield: bool = True,
) -> Optional[Path]:
    """3D concept image → TRELLIS GLB.

    Transcendence 2.5D is *not* this image: Blender later renders the GLB at
    120 facing angles. Starfield uses the same GLB as a real mesh.
    Existing concept files are copied into the mesh dir and never overwritten.
    """
    glb_path = Path(glb)
    glb_path.parent.mkdir(parents=True, exist_ok=True)
    if not autostart_mesh and not mesh_ready():
        return None
    work = glb_path.parent / f"{glb_path.stem}_concept.png"
    src = Path(concept) if concept else None
    if src and src.is_file():
        if src.resolve() != work.resolve():
            shutil.copy2(src, work)
        print(f"[tx] TRELLIS from 3D concept {src}")
    elif work.is_file():
        print(f"[tx] TRELLIS from existing {work}")
    else:
        full = f"{TRELLIS_CONCEPT_PROMPT} {prompt}".strip()
        if not generate_image(
            full,
            work,
            kind=kind,
            size=size,
            seed=seed,
            reference_image=reference_image,
        ):
            return None
    mesh = generate_mesh(work, glb_path, autostart=autostart_mesh)
    if mesh and publish_starfield:
        publish_starfield_mesh(mesh, asset_id or glb_path.stem)
    return mesh


def generate_pbr_skins(
    output_dir: Path | str,
    name: str,
    spec: Optional[Dict[str, Any]] = None,
    *,
    quality: str = "standard",
    use_sd: bool = True,
    seed: int = 17,
    glow: bool = False,
) -> Dict[str, Any]:
    """PBR maps via Shared/pbr_skin_generator. SD is required; no procedural skins."""
    if not use_sd:
        raise RuntimeError("procedural PBR skins are disabled; use SD (omit --no-sd)")
    if not image_ready():
        prepare(image=True, mesh=False, keep_server=_keep_from_env())
    from pbr_skin_generator import generate_pbr_skin_set

    paths = generate_pbr_skin_set(
        output_dir,
        name,
        spec or {},
        quality=quality,
        use_sd=True,
        seed=seed,
        glow=glow,
        allow_procedural=False,
    )
    return {k: str(v) for k, v in paths.items()}


def bake_onto_mesh(
    mesh: Union[str, Path],
    out_dir: Union[str, Path],
    *,
    maps: Optional[Dict[str, Union[str, Path]]] = None,
    skin_dir: Optional[Union[str, Path]] = None,
    name: str = "",
    size: int = 1024,
    ao: bool = True,
    blender: Optional[str] = None,
    stop_servers: bool = True,
) -> Dict[str, Any]:
    """Ucupaint-bake real maps onto mesh UVs. Stops GPU servers first so VRAM is free."""
    if stop_servers:
        release(force=True)
    from ucupaint_support import bake_onto_mesh as _bake

    return _bake(
        mesh,
        out_dir,
        maps=maps,
        skin_dir=skin_dir,
        name=name,
        size=size,
        ao=ao,
        blender=blender or find_blender(),
    )


def find_blender(explicit: Optional[str] = None) -> Optional[str]:
    try:
        from tool_paths import find_blender as _fb

        return _fb(explicit)
    except Exception:
        pass
    try:
        from mesh_skin_export import find_blender as _fb2

        return _fb2(explicit)
    except Exception:
        return None


def transcendence_root() -> Optional[Path]:
    try:
        from tool_paths import transcendence_root as _tr

        return _tr()
    except Exception:
        game = Path(r"D:\games\Steam\steamapps\common\Transcendence")
        return game if game.is_dir() else None


def enhance_prompt(prompt: str, *, model: Optional[str] = None) -> str:
    """Optional Ollama rewrite. Returns the original prompt on any failure."""
    try:
        from ollama_integration import call_ollama, test_ollama_connection

        if not test_ollama_connection():
            return prompt
        system = (
            "Rewrite this as a concise Stable Diffusion 3.5 prompt for a "
            "Transcendence space-game asset. Front-load: no text, no watermark. "
            "Keep under 70 CLIP tokens. Return only the prompt."
        )
        out = call_ollama(prompt, system=system, model=model) if model else call_ollama(prompt, system=system)
        text = (out or "").strip().splitlines()[0].strip().strip('"')
        return text or prompt
    except Exception:
        return prompt


@contextmanager
def sd_session(*, use_sd: bool = True, timeout_sec: float = 240.0) -> Iterator[bool]:
    """Yield True if :1338 is reachable for the block."""
    if not use_sd:
        yield False
        return
    from sd_server_lifecycle import managed_sd_server

    with managed_sd_server(timeout_sec=timeout_sec) as ready:
        yield bool(ready)


def _cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Transcendence Shared AI pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("probe", help="Print Shared stage status")

    p_ensure = sub.add_parser("ensure", help="Start a Shared stage")
    p_ensure.add_argument("stage", choices=("image", "mesh", "material", "layering", "compress", "audio"))
    sub.add_parser("session", help="Start both SD and TRELLIS")
    sub.add_parser("release", help="Stop both SD and TRELLIS")

    p_img = sub.add_parser("image", help="Generate one SD3.5 image")
    p_img.add_argument("--prompt", required=True)
    p_img.add_argument("--out", required=True)
    p_img.add_argument("--kind", default="icon", choices=("icon", "texture", "sprite", "hud", "banner", "default"))
    p_img.add_argument("--size", type=int, default=512)
    p_img.add_argument("--width", type=int, default=0)
    p_img.add_argument("--height", type=int, default=0)
    p_img.add_argument("--seed", type=int, default=0)
    p_img.add_argument("--steps", type=int, default=0)
    p_img.add_argument("--negative", default=TX_NEGATIVE)
    p_img.add_argument("--no-enhance", action="store_true")

    p_mesh = sub.add_parser(
        "concept-mesh",
        help="3D concept → TRELLIS GLB (TX 120-facings + Starfield mesh copy)",
    )
    p_mesh.add_argument(
        "--prompt",
        default="",
        help="Used only if --concept is missing; always a 3D three-quarter sculpt, not top-down",
    )
    p_mesh.add_argument("--out", required=True)
    p_mesh.add_argument("--concept", default="", help="Existing 3D concept PNG (preferred)")
    p_mesh.add_argument("--size", type=int, default=768)
    p_mesh.add_argument("--seed", type=int, default=0)
    p_mesh.add_argument("--id", default="", help="Asset id for Starfield mesh copy")

    p_audio = sub.add_parser("audio", help="Generate one library-conditioned SFX")
    p_audio.add_argument("--prompt", required=True)
    p_audio.add_argument("--out", required=True)
    p_audio.add_argument("--duration", type=float, default=2.5)
    p_audio.add_argument("--archetype", default="")
    p_audio.add_argument("--strength", type=float, default=0.65)
    p_audio.add_argument("--engine", default="auto")

    p_bake = sub.add_parser("bake", help="Ucupaint-bake real maps onto a mesh")
    p_bake.add_argument("--mesh", required=True)
    p_bake.add_argument("--out-dir", required=True)
    p_bake.add_argument("--skin-dir", default="")
    p_bake.add_argument("--name", default="")
    p_bake.add_argument("--size", type=int, default=1024)
    p_bake.add_argument("--color", default="")
    p_bake.add_argument("--roughness", default="")
    p_bake.add_argument("--metallic", default="")
    p_bake.add_argument("--normal", default="")

    p_skins = sub.add_parser("skins", help="SD PBR maps (albedo + derived roughness/normal/metallic)")
    p_skins.add_argument("--name", required=True)
    p_skins.add_argument("--out-dir", required=True)
    p_skins.add_argument("--theme", default="")
    p_skins.add_argument("--description", default="")
    p_skins.add_argument("--quality", default="standard")
    p_skins.add_argument("--glow", action="store_true")

    args = parser.parse_args(argv)

    if args.cmd == "probe":
        print_probe()
        return 0

    if args.cmd == "session":
        result = prepare(image=True, mesh=True, keep_server=True)
        print(json.dumps(result, indent=2))
        ready = all((result.get(k) or {}).get("ready") for k in result)
        return 0 if ready else 1

    if args.cmd == "release":
        print(json.dumps(release(), indent=2))
        return 0

    if args.cmd == "ensure":
        result = _import_ai().ensure(args.stage)
        print(json.dumps(result, indent=2))
        return 0 if result.get("ready") else 1

    if args.cmd == "image":
        prompt = args.prompt if args.no_enhance else enhance_prompt(args.prompt)
        path = generate_image(
            prompt,
            args.out,
            kind=args.kind,
            size=args.size,
            width=args.width or None,
            height=args.height or None,
            negative_prompt=args.negative,
            seed=args.seed,
            steps=args.steps or None,
        )
        if not path:
            return 1
        print(path)
        return 0

    if args.cmd == "concept-mesh":
        concept = args.concept or None
        prompt = args.prompt or TRELLIS_CONCEPT_PROMPT
        if not concept and args.prompt:
            prompt = enhance_prompt(args.prompt)
        path = concept_mesh(
            prompt,
            args.out,
            concept=concept,
            size=args.size,
            seed=args.seed,
            autostart_mesh=True,
            asset_id=args.id,
        )
        if not path:
            return 1
        print(path)
        return 0

    if args.cmd == "audio":
        path = generate_audio(
            args.prompt,
            args.out,
            duration=args.duration,
            archetype=args.archetype,
            strength=args.strength,
            engine=args.engine,
        )
        if not path:
            return 1
        print(path)
        return 0

    if args.cmd == "bake":
        maps = {
            k: getattr(args, k)
            for k in ("color", "roughness", "metallic", "normal")
            if getattr(args, k)
        }
        report = bake_onto_mesh(
            args.mesh,
            args.out_dir,
            maps=maps or None,
            skin_dir=args.skin_dir or None,
            name=args.name,
            size=args.size,
        )
        print(json.dumps(report, indent=2))
        return 0 if report.get("ok") else 1

    if args.cmd == "skins":
        spec = {
            "theme": args.theme or args.name,
            "description": args.description,
        }
        try:
            with session(image=True, mesh=False):
                paths = generate_pbr_skins(
                    args.out_dir,
                    args.name,
                    spec,
                    quality=args.quality,
                    glow=args.glow,
                )
        except Exception as exc:  # noqa: BLE001
            print(f"[tx] skins failed: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(paths, indent=2))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(_cli())
