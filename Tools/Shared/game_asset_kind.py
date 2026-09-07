#!/usr/bin/env python3
"""
Shared game-asset kinds: spell / projectile / ship → sprites + optional Unity mesh.

Uses local SD when available (sd_http_client), otherwise procedural PIL.
Meshes use mesh_skin_export / blender_aamt_mesh (silhouette for icons/projectiles,
armor_panel/displaced for ships). Transcendence ships always export a 120-facings
rotation JPG via ship_spritesheet_export (mesh → Blender orthographic render).

Layouts (Unity):
  Assets/Resources/{system}/Spells/{name}/
  Assets/Resources/{system}/Projectiles/{name}/
  Assets/Resources/{system}/Ships/{name}/

Examples:
  python game_asset_kind.py --kind spell --theme "verdant pulse" --name VerdantPulse --out-dir out --system NatureMagic
  python game_asset_kind.py --kind projectile --theme "plasma bolt" --name PlasmaBolt --out-dir out --mesh
  python game_asset_kind.py --kind ship --theme "obsidian frigate" --name ObsidianFrigate --out-dir out --mesh --no-sd
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from unity_meta import write_model_meta, write_texture_meta  # noqa: E402

try:
    from PIL import Image, ImageDraw, ImageFilter
except ImportError as exc:
    raise SystemExit(f"Pillow required: {exc}") from exc

KINDS = ("spell", "projectile", "ship")


def _safe(name: str) -> str:
    return "".join(c if c.isalnum() or c == "_" else "_" for c in name)


def _hex_rgb(h: str, default: Tuple[int, int, int] = (80, 140, 220)) -> Tuple[int, int, int]:
    h = (h or "").strip().lstrip("#")
    if len(h) >= 6:
        try:
            return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        except ValueError:
            pass
    return default


def _try_sd(prompt: str, path: Path, *, size: int, no_sd: bool) -> bool:
    if no_sd:
        return False
    try:
        from ai_resources import make_image
        from sd_http_client import plan_sd_size

        gen_w, gen_h, gen_steps = plan_sd_size(size, size, "sprite")
        gen_size = max(gen_w, gen_h)
        make_image(
            prompt,
            path,
            width=gen_w,
            height=gen_h,
            steps=gen_steps,
            timeout=600.0,
            connect_timeout=5.0,
        )
        if path.exists() and size < gen_size:
            im = Image.open(path).convert("RGBA")
            im = im.resize((size, size), Image.Resampling.LANCZOS)
            im.save(path)
        return path.exists()
    except Exception as exc:
        print(f"[WARN] SD skipped: {exc}", file=sys.stderr)
        return False


def _proc_orb(
    size: int,
    colors: List[str],
    *,
    glow: bool = True,
    spike: bool = False,
    seed: int = 0,
) -> Image.Image:
    import random

    rng = random.Random(seed)
    c0 = _hex_rgb(colors[0] if colors else "#4a90d9")
    c1 = _hex_rgb(colors[1] if len(colors) > 1 else "#e8f0ff", (232, 240, 255))
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pad = max(1, size // 10)
    d.ellipse((pad, pad, size - pad - 1, size - pad - 1), fill=(*c0, 255))
    # highlight
    hpad = pad + size // 5
    d.ellipse((hpad, hpad, size // 2, size // 2), fill=(*c1, 180))
    if spike:
        cx = cy = size / 2
        for i in range(6):
            ang = (i / 6.0) * math.tau + rng.random() * 0.2
            x2 = cx + math.cos(ang) * (size * 0.48)
            y2 = cy + math.sin(ang) * (size * 0.48)
            d.line((cx, cy, x2, y2), fill=(*c1, 220), width=max(1, size // 16))
    if glow:
        glow_im = im.filter(ImageFilter.GaussianBlur(radius=max(1, size // 12)))
        base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        base = Image.alpha_composite(base, glow_im)
        base = Image.alpha_composite(base, im)
        im = base
    return im


def _proc_ship_silhouette(size: int, colors: List[str], seed: int = 0) -> Image.Image:
    """Higher-detail top-down hull for mesh cutout + readable facings."""
    import random

    rng = random.Random(seed)
    c0 = _hex_rgb(colors[0] if colors else "#3a3a48")
    c1 = _hex_rgb(colors[1] if len(colors) > 1 else "#7ec8ff", (126, 200, 255))
    c_mid = tuple(min(255, (a + b) // 2) for a, b in zip(c0, c1))
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    # Main fuselage (nose-up)
    hull = [
        (size * 0.50, size * 0.08),
        (size * 0.62, size * 0.28),
        (size * 0.70, size * 0.55),
        (size * 0.58, size * 0.88),
        (size * 0.42, size * 0.88),
        (size * 0.30, size * 0.55),
        (size * 0.38, size * 0.28),
    ]
    d.polygon(hull, fill=(*c0, 255))

    # Wing spars
    d.polygon(
        [
            (size * 0.08, size * 0.48),
            (size * 0.34, size * 0.40),
            (size * 0.34, size * 0.58),
            (size * 0.12, size * 0.62),
        ],
        fill=(*c0, 250),
    )
    d.polygon(
        [
            (size * 0.92, size * 0.48),
            (size * 0.66, size * 0.40),
            (size * 0.66, size * 0.58),
            (size * 0.88, size * 0.62),
        ],
        fill=(*c0, 250),
    )

    # Centerline ridge + panel cuts
    d.line([(size * 0.5, size * 0.12), (size * 0.5, size * 0.82)], fill=(*c_mid, 200), width=max(1, size // 64))
    for yf in (0.35, 0.50, 0.65):
        y = size * yf
        d.line([(size * 0.38, y), (size * 0.62, y)], fill=(*c_mid, 160), width=max(1, size // 80))

    # Cockpit canopy
    d.ellipse(
        (size * 0.42, size * 0.22, size * 0.58, size * 0.38),
        fill=(*c1, 230),
        outline=(*c1, 255),
    )
    # Engine glow cluster
    for i, xf in enumerate((0.42, 0.50, 0.58)):
        x = size * xf
        y = size * 0.90
        r = max(2, size // 28 - i)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(*c1, 255))

    # Soft edge AA via slight blur of alpha only
    soft = im.filter(ImageFilter.GaussianBlur(radius=max(0.6, size / 220.0)))
    return Image.alpha_composite(soft, im)


def _write_png(path: Path, im: Image.Image, *, kind: str = "sprite") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)
    write_texture_meta(path, kind=kind if kind in ("sprite", "gui", "default", "normal") else "sprite")


def _request_kind_spec(kind: str, theme: str, *, model: str, ollama_url: str) -> Dict[str, Any]:
    try:
        from ollama_mesh_spec import request_mesh_spec

        # Reuse mesh-spec for colors/shape, then specialize
        base = request_mesh_spec(theme, model=model, ollama_url=ollama_url)
    except Exception as exc:
        print(f"[WARN] Ollama spec fallback: {exc}", file=sys.stderr)
        base = {
            "theme": theme,
            "colors": ["#4a90d9", "#e8f0ff"] if kind != "ship" else ["#2a2a32", "#7ec8ff"],
            "glow": kind != "ship",
            "shape": "silhouette" if kind in ("spell", "projectile") else "armor_panel",
            "pattern": "organic" if kind != "ship" else "plates",
        }
    base.setdefault("theme", theme)
    base.setdefault("kind", kind)
    if kind in ("spell", "projectile"):
        base.setdefault("shape", "silhouette")
    elif kind == "ship":
        base.setdefault("shape", "silhouette")
        base.setdefault("frameWidth", 128)
        base.setdefault("facings", 120)
        base.setdefault("columns", 12)
    return base


def _export_mesh(
    *,
    skin_dir: Path,
    name: str,
    fbx: Path,
    shape: str,
    sketch: Optional[Path],
    no_sd: bool,
    theme: str,
) -> int:
    from mesh_skin_export import run_blender_export
    from pbr_skin_generator import generate_pbr_skin_set

    generate_pbr_skin_set(
        skin_dir,
        name,
        {"theme": theme, "shape": shape},
        quality="draft",
        use_sd=not no_sd,
    )
    # Prefer sketch as height/cutout source when present
    return run_blender_export(
        skin_dir=skin_dir,
        name=name,
        fbx=fbx,
        shape=shape,
        sketch=sketch,
        subdivisions=2,
        displace_strength=0.2 if shape != "silhouette" else 0.12,
        solidify_thickness=0.1,
        bevel_amount=0.015,
    )


def generate_spell(
    out_dir: Path,
    name: str,
    *,
    theme: str,
    spec: Dict[str, Any],
    no_sd: bool,
    mesh: bool,
    icon_size: int = 64,
    fx_frames: int = 4,
    proj_frames: int = 2,
) -> Dict[str, Any]:
    colors = list(spec.get("colors") or ["#4a90d9", "#e8f0ff"])
    manifest: Dict[str, Any] = {"kind": "spell", "name": name, "theme": theme, "files": {}}

    icon_path = out_dir / f"{name}_icon.png"
    prompt = f"game spell icon, {theme}, painterly, high contrast, soft edges, centered, transparent background"
    if not _try_sd(prompt, icon_path, size=icon_size, no_sd=no_sd):
        _write_png(icon_path, _proc_orb(icon_size, colors, glow=True, seed=1))
    else:
        write_texture_meta(icon_path, kind="sprite")
    manifest["files"]["icon"] = str(icon_path)

    fx_dir = out_dir / "FX"
    fx_paths = []
    for i in range(fx_frames):
        p = fx_dir / f"{name}_fx_{i:02d}.png"
        scale = 0.55 + 0.45 * ((i + 1) / fx_frames)
        sz = max(16, int(icon_size * scale))
        im = _proc_orb(sz, colors, glow=True, spike=(i % 2 == 1), seed=10 + i)
        canvas = Image.new("RGBA", (icon_size, icon_size), (0, 0, 0, 0))
        ox = (icon_size - sz) // 2
        canvas.paste(im, (ox, ox), im)
        _write_png(p, canvas)
        fx_paths.append(str(p))
    manifest["files"]["fx"] = fx_paths

    proj_dir = out_dir / "Projectile"
    proj_paths = []
    for i in range(proj_frames):
        p = proj_dir / f"{name}_proj_{i:02d}.png"
        im = _proc_orb(icon_size, colors, glow=True, spike=True, seed=50 + i)
        _write_png(p, im)
        proj_paths.append(str(p))
    manifest["files"]["projectile"] = proj_paths

    if mesh:
        skin_dir = out_dir / "Skins"
        fbx = out_dir / "Meshes" / f"{name}.fbx"
        code = _export_mesh(
            skin_dir=skin_dir,
            name=name,
            fbx=fbx,
            shape=str(spec.get("shape") or "silhouette"),
            sketch=icon_path,
            no_sd=True,  # skins already from theme; avoid double SD
            theme=theme,
        )
        if fbx.exists():
            write_model_meta(fbx)
            manifest["files"]["mesh"] = str(fbx)
            manifest["mesh_exit"] = code

    return manifest


def generate_projectile(
    out_dir: Path,
    name: str,
    *,
    theme: str,
    spec: Dict[str, Any],
    no_sd: bool,
    mesh: bool,
    size: int = 64,
    frames: int = 4,
) -> Dict[str, Any]:
    colors = list(spec.get("colors") or ["#ff6a3d", "#ffe0a0"])
    manifest: Dict[str, Any] = {"kind": "projectile", "name": name, "theme": theme, "files": {}}

    frames_dir = out_dir / "Frames"
    paths = []
    for i in range(frames):
        p = frames_dir / f"{name}_{i:02d}.png"
        prompt = f"game projectile sprite frame {i+1}/{frames}, {theme}, centered, transparent background, stylized"
        if not _try_sd(prompt, p, size=size, no_sd=no_sd):
            _write_png(p, _proc_orb(size, colors, glow=True, spike=True, seed=20 + i))
        else:
            write_texture_meta(p, kind="sprite")
        paths.append(str(p))
    manifest["files"]["frames"] = paths

    if mesh:
        skin_dir = out_dir / "Skins"
        fbx = out_dir / "Meshes" / f"{name}.fbx"
        sketch = Path(paths[0]) if paths else None
        code = _export_mesh(
            skin_dir=skin_dir,
            name=name,
            fbx=fbx,
            shape=str(spec.get("shape") or "silhouette"),
            sketch=sketch,
            no_sd=True,
            theme=theme,
        )
        if fbx.exists():
            write_model_meta(fbx)
            manifest["files"]["mesh"] = str(fbx)
            manifest["mesh_exit"] = code
    return manifest


def generate_ship(
    out_dir: Path,
    name: str,
    *,
    theme: str,
    spec: Dict[str, Any],
    no_sd: bool,
    mesh: bool,
    size: int = 256,
    unique_hud: bool = True,
) -> Dict[str, Any]:
    colors = list(spec.get("colors") or ["#2a2a32", "#7ec8ff"])
    manifest: Dict[str, Any] = {"kind": "ship", "name": name, "theme": theme, "files": {}}

    # Top-down sketch drives mesh silhouette + fallback 2D rotation sheet
    sketch = out_dir / f"{name}_sketch.png"
    prompt = f"top-down spaceship sprite, {theme}, clear silhouette, game asset, transparent background"
    if not _try_sd(prompt, sketch, size=max(size, 512), no_sd=no_sd):
        _write_png(sketch, _proc_ship_silhouette(max(size, 384), colors, seed=7))
    else:
        write_texture_meta(sketch, kind="sprite")
    manifest["files"]["sketch"] = str(sketch)

    # Transcendence ships need 120-facings JPG from 3D mesh (dev workflow)
    from ship_spritesheet_export import export_ship_rotation_sheet

    sheet_spec = {**spec, "no_sd": no_sd, "no_unique_hud": not unique_hud}
    sheet_manifest = export_ship_rotation_sheet(
        out_dir,
        name,
        theme=theme,
        sketch=sketch,
        spec=sheet_spec,
        ensure_mesh=True,
    )
    manifest["files"].update(sheet_manifest.get("files") or {})
    if sheet_manifest.get("shipRotation"):
        manifest["shipRotation"] = sheet_manifest["shipRotation"]
    if sheet_manifest.get("uniqueHud") is not None:
        manifest["uniqueHud"] = sheet_manifest["uniqueHud"]
    if sheet_manifest.get("mesh_exit") is not None:
        manifest["mesh_exit"] = sheet_manifest["mesh_exit"]
    if sheet_manifest.get("spritesheet_exit") is not None:
        manifest["spritesheet_exit"] = sheet_manifest["spritesheet_exit"]

    # Ensure unique HUD even if spritesheet path skipped it
    if unique_hud and not (manifest.get("uniqueHud") or {}).get("enabled"):
        from ship_hud_export import export_unique_ship_hud

        hud = export_unique_ship_hud(
            out_dir,
            name,
            hero=Path(manifest["files"]["hero"]) if manifest["files"].get("hero") else None,
            sketch=sketch,
            base_mesh=Path(manifest["files"]["mesh"]) if manifest["files"].get("mesh") else None,
            spec=sheet_spec,
            unique_hud=True,
        )
        manifest["files"].update(hud.get("files") or {})
        if hud.get("uniqueHud") is not None:
            manifest["uniqueHud"] = hud["uniqueHud"]

    if mesh and manifest["files"].get("mesh"):
        write_model_meta(Path(manifest["files"]["mesh"]))

    # Legacy single-frame alias (first frame of sheet)
    if manifest["files"].get("spritesheet"):
        manifest["files"]["sprite"] = manifest["files"]["spritesheet"]
    elif sketch.is_file():
        manifest["files"]["sprite"] = str(sketch)

    return manifest


def resolve_out_dir(base: Path, *, kind: str, system: str, name: str, unity_layout: bool) -> Path:
    if not unity_layout:
        return base / kind / name
    folder = {"spell": "Spells", "projectile": "Projectiles", "ship": "Ships"}[kind]
    sys_name = system or "GameAssets"
    return base / "Assets" / "Resources" / sys_name / folder / name


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kind", required=True, choices=KINDS)
    ap.add_argument("--theme", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out-dir", required=True, help="Mod/project root or plain output folder")
    ap.add_argument("--system", default="GameAssets", help="Unity Resources/{system}/…")
    ap.add_argument("--unity-layout", action="store_true", help="Write under Assets/Resources/…")
    ap.add_argument("--mesh", action="store_true", help="Also export Blender FBX")
    ap.add_argument("--no-sd", action="store_true")
    ap.add_argument("--no-ollama", action="store_true")
    ap.add_argument("--model", default="qwen2.5-coder:7b")
    ap.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    ap.add_argument("--fx-frames", type=int, default=4)
    ap.add_argument("--proj-frames", type=int, default=2)
    ap.add_argument("--defs", action="store_true", help="Write gameplay JSON/XML defs referencing this pack")
    ap.add_argument(
        "--no-unique-hud",
        action="store_true",
        help="Ship: skip unique Armor/Shield HUD (use circular + default shield)",
    )
    args = ap.parse_args()

    name = _safe(args.name)
    base = Path(args.out_dir)
    out = resolve_out_dir(base, kind=args.kind, system=args.system, name=name, unity_layout=args.unity_layout)
    out.mkdir(parents=True, exist_ok=True)

    if args.no_ollama:
        spec = {
            "theme": args.theme,
            "kind": args.kind,
            "colors": ["#4a90d9", "#e8f0ff"] if args.kind != "ship" else ["#2a2a32", "#7ec8ff"],
            "shape": "silhouette" if args.kind != "ship" else "silhouette",
            "glow": True,
        }
    else:
        spec = _request_kind_spec(args.kind, args.theme, model=args.model, ollama_url=args.ollama_url)

    (out / f"{name}_spec.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")

    if args.kind == "spell":
        manifest = generate_spell(
            out,
            name,
            theme=args.theme,
            spec=spec,
            no_sd=args.no_sd,
            mesh=args.mesh,
            fx_frames=args.fx_frames,
            proj_frames=args.proj_frames,
        )
    elif args.kind == "projectile":
        manifest = generate_projectile(
            out, name, theme=args.theme, spec=spec, no_sd=args.no_sd, mesh=args.mesh, frames=args.proj_frames
        )
    else:
        manifest = generate_ship(
            out,
            name,
            theme=args.theme,
            spec=spec,
            no_sd=args.no_sd,
            mesh=args.mesh,
            unique_hud=not args.no_unique_hud,
        )

    defs_written = {}
    if args.defs:
        from game_asset_defs import write_defs_for_pack

        defs_written = write_defs_for_pack(
            out,
            kind=args.kind,
            name=name,
            theme=args.theme,
            system=args.system,
            manifest=manifest,
            spec=spec,
        )
        manifest["defs"] = defs_written

    man_path = out / f"{name}_manifest.json"
    man_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out),
                "manifest": str(man_path),
                "files": manifest.get("files"),
                "defs": defs_written,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
