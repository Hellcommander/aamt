#!/usr/bin/env python3
"""
Living weapons / projectiles — 3D mesh first, then Transcendence facings.

  1. 3D concept (registry conceptArt) → TRELLIS GLB
     Same GLB copied to Shared/Concepts/meshes for Starfield.
  2. PBR skins + Ucupaint bake onto UVs
  3. Orthographic facings via Common/blender_ship_spritesheet_export.py
     (Transcendence 2.5D — facing angles of the mesh, not a 2D drawing)

Usage (from Tools/Transcendence):
  python generate_living_weapon_assets.py --out-dir C:\\Output\\LivingWeaponAssets
  python generate_living_weapon_assets.py --out-dir C:\\Output\\LivingWeaponAssets --deploy-resources
  python generate_living_weapon_assets.py --skins-only --out-dir C:\\Output\\LivingWeaponAssets
  python generate_living_weapon_assets.py --asset-id lwFireModule --quality draft
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps

_TOOLS_TX = Path(__file__).resolve().parent
_TOOLS = _TOOLS_TX.parent
_SHARED = _TOOLS / "Shared"
_COMMON = _TOOLS / "Common"
_REGISTRY_FILE = _TOOLS_TX / "crossmod_living_weapon_registry.json"
_SHEET_SCRIPT = _COMMON / "blender_ship_spritesheet_export.py"
_DEFAULT_DEPLOY = (
    _TOOLS.parent
    / "steamapps"
    / "common"
    / "Transcendence"
    / "Extensions"
    / "ZZZ_CrossModCompatibility"
    / "Resources"
    / "LivingWeapons"
)
# Prefer workspace Extensions path when tools live beside the game install
_GAME_DEPLOY = Path(
    r"D:\games\Steam\steamapps\common\Transcendence\Extensions"
    r"\ZZZ_CrossModCompatibility\Resources\LivingWeapons"
)

if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
if str(_TOOLS_TX) not in sys.path:
    sys.path.insert(0, str(_TOOLS_TX))

try:
    import tx_ai_pipeline as tx  # type: ignore
except Exception:
    tx = None  # type: ignore

ICON = 96
COLS = 12


def _load_registry(path: Optional[Path] = None) -> Dict[str, Any]:
    p = path or _REGISTRY_FILE
    return json.loads(p.read_text(encoding="utf-8"))


def _find_blender(explicit: Optional[str] = None) -> Optional[str]:
    if tx:
        hit = tx.find_blender(explicit)
        if hit:
            return hit
    from mesh_skin_export import find_blender

    return find_blender(explicit)


def generate_skins_for_asset(
    asset: Dict[str, Any],
    skin_dir: Path,
    *,
    quality: str = "standard",
    use_sd: bool = True,
) -> Dict[str, Any]:
    name = asset.get("name") or asset.get("id")
    if not name:
        raise ValueError("asset missing name/id")
    skin_dir.mkdir(parents=True, exist_ok=True)
    spec = {
        "theme": asset.get("theme") or name,
        "colors": asset.get("colors") or [],
        "pattern": asset.get("pattern") or "organic",
        "style": asset.get("style") or "stylized",
        "description": asset.get("description") or "",
        "glow": bool(asset.get("glow", True)),
        "shape": asset.get("shape") or "armor_panel",
    }
    print(f"[skin] {name} quality={quality} use_sd={use_sd} (Shared via tx_ai_pipeline)")
    if tx:
        return tx.generate_pbr_skins(
            skin_dir,
            name,
            spec,
            quality=quality,
            use_sd=use_sd,
            glow=True,
            seed=abs(hash(name)) % 10_000_000,
        )
    from pbr_skin_generator import generate_pbr_skin_set

    paths = generate_pbr_skin_set(
        skin_dir,
        name,
        spec,
        quality=quality,
        use_sd=use_sd,
        glow=True,
        seed=abs(hash(name)) % 10_000_000,
    )
    return {k: str(v) for k, v in paths.items()}


def build_mesh_fbx(
    asset: Dict[str, Any],
    skin_dir: Path,
    fbx: Path,
    *,
    blender: Optional[str] = None,
) -> int:
    from mesh_skin_export import run_blender_export

    name = asset["name"]
    shape = str(asset.get("shape") or "armor_panel")
    print(f"[mesh] Shared/mesh_skin_export shape={shape} -> {fbx.name}")
    fbx.parent.mkdir(parents=True, exist_ok=True)
    return run_blender_export(
        skin_dir=skin_dir,
        name=name,
        fbx=fbx,
        shape=shape,
        blender=blender,
        subdivisions=int(asset.get("subdivisions", 1)),
        displace_strength=float(asset.get("displaceStrength", 0.08)),
        solidify_thickness=float(asset.get("solidifyThickness", 0.04)),
        bevel_amount=float(asset.get("bevelAmount", 0.02)),
    )


def render_facings(
    *,
    model_path: Path,
    sheet_path: Path,
    hero_path: Path,
    params: Dict[str, int],
    blender: Optional[str] = None,
) -> int:
    """Same exporter as CrossMod ships / Export-AamtShipSpritesheet."""
    from ship_spritesheet_export import _run_blender_spritesheet

    if not _SHEET_SCRIPT.is_file():
        print(f"[ERROR] Missing {_SHEET_SCRIPT}")
        return 1
    print(
        f"[sheet] Common/blender_ship_spritesheet_export "
        f"{params['facings']} facings @ {params['frame_width']}px"
    )
    return _run_blender_spritesheet(
        model_path=model_path,
        sheet_path=sheet_path,
        hero_path=hero_path,
        params=params,
        blender=blender,
    )


def _trellis_prompt(asset: Dict[str, Any]) -> str:
    name = asset.get("name") or asset.get("id") or "weapon"
    theme = asset.get("theme") or name
    desc = asset.get("description") or ""
    return (
        f"{theme}, {desc}, organic living weapon as a complete 3D sculpt, "
        f"three-quarter studio view, single object"
    )


def export_asset_pack(
    asset: Dict[str, Any],
    out_root: Path,
    *,
    quality: str = "standard",
    use_sd: bool = True,
    skins_only: bool = False,
    blender: Optional[str] = None,
    mesh_source: str = "auto",
    defer_render: bool = False,
) -> Dict[str, Any]:
    from ship_spritesheet_export import _resolve_tx_params

    name = asset.get("name") or asset.get("id")
    if not name:
        return {"ok": False, "error": "asset missing name/id"}
    pack_dir = out_root / name
    pack_dir.mkdir(parents=True, exist_ok=True)
    skin_dir = pack_dir / "Skins"

    if (skin_dir / f"{name}_diffuse.png").is_file() and not use_sd:
        skin_meta = {"reused": str(skin_dir)}
    elif (skin_dir / f"{name}_diffuse.png").is_file() and quality == "reuse":
        skin_meta = {"reused": str(skin_dir)}
    else:
        skin_meta = generate_skins_for_asset(
            asset, skin_dir, quality=quality if quality != "reuse" else "standard", use_sd=use_sd
        )

    result: Dict[str, Any] = {
        "id": asset.get("id"),
        "name": name,
        "kind": asset.get("kind"),
        "skins": skin_meta,
        "pack": str(pack_dir),
        "method": "mesh_pbr_ortho",
    }
    result["skin_dir"] = str(skin_dir)
    if skins_only:
        result["ok"] = True
        return result

    mesh_dir = pack_dir / "Meshes"
    mesh_dir.mkdir(parents=True, exist_ok=True)
    fbx = mesh_dir / f"{name}.fbx"
    blend = mesh_dir / f"{name}.blend"
    glb = mesh_dir / f"{name}.glb"
    model_for_sheet: Optional[Path] = None
    want_trellis = mesh_source in ("trellis", "auto") and tx is not None
    if want_trellis:
        print(f"[mesh] TRELLIS 3D concept→GLB ({name}) — TX 2.5D is 120-facings later")
        concept = None
        if tx:
            concept = tx.resolve_concept_art(asset)
        hit = tx.concept_mesh(
            _trellis_prompt(asset),
            glb,
            concept=concept or (mesh_dir / f"{name}_concept.png"),
            autostart_mesh=True,
            seed=abs(hash(name)) % 10_000_000,
            asset_id=str(asset.get("id") or name),
        )
        if hit and hit.is_file():
            model_for_sheet = hit
            result["method"] = "trellis_pbr_ortho"
    if model_for_sheet is None:
        if mesh_source == "trellis":
            result["ok"] = False
            result["error"] = "TRELLIS mesh failed"
            return result
        mesh_code = build_mesh_fbx(asset, skin_dir, fbx, blender=blender)
        result["mesh_exit"] = mesh_code
        model_for_sheet = blend if blend.is_file() else fbx
    if not model_for_sheet.is_file():
        result["ok"] = False
        result["error"] = "mesh build failed (no .blend/.fbx/.glb)"
        return result
    result["mesh"] = str(model_for_sheet)
    result["skin_dir"] = str(skin_dir)
    fw = int(asset.get("frameWidth") or 96)
    facings = int(asset.get("facings") or 1)
    columns = int(asset.get("columns") or max(1, min(facings, 8)))
    params = _resolve_tx_params(
        {
            "facings": facings,
            "columns": columns,
            "frameWidth": fw,
            "frameHeight": fw,
            "heroWidth": int(asset.get("heroWidth") or fw),
            "heroHeight": int(asset.get("heroHeight") or fw),
            "supersample": int(asset.get("supersample") or 2),
        }
    )
    result["sheet_path"] = str(pack_dir / f"{name}.jpg")
    result["hero_path"] = str(pack_dir / f"{name}Large.jpg")
    result["params"] = params
    if defer_render:
        result["ok"] = True
        return result
    return finish_asset_pack(result, blender=blender)


def finish_asset_pack(result: Dict[str, Any], *, blender: Optional[str] = None) -> Dict[str, Any]:
    """Ucupaint-bake real skins onto the mesh, then ortho spritesheet. GPU servers must be down."""
    name = result["name"]
    model_for_sheet = Path(result["mesh"])
    skin_dir = Path(result.get("skin_dir") or (Path(result["pack"]) / "Skins"))
    if tx and model_for_sheet.is_file() and skin_dir.is_dir():
        bake_dir = Path(result["pack"]) / "Meshes" / "Ucupaint"
        try:
            baked = tx.bake_onto_mesh(
                model_for_sheet,
                bake_dir,
                skin_dir=skin_dir,
                name=name,
                blender=blender,
                stop_servers=True,
            )
            result["ucupaint"] = baked
            glb = baked.get("glb") or baked.get("blend")
            if glb and Path(glb).is_file():
                model_for_sheet = Path(glb)
                result["mesh"] = str(model_for_sheet)
                result["method"] = str(result.get("method") or "") + "+ucupaint"
        except Exception as exc:  # noqa: BLE001
            print(f"[ucupaint] bake skipped for {name}: {exc}", file=sys.stderr)
    params = result.get("params") or {}
    sheet_path = Path(result["sheet_path"])
    hero_path = Path(result["hero_path"])
    code = render_facings(
        model_path=model_for_sheet,
        sheet_path=sheet_path,
        hero_path=hero_path,
        params=params,
        blender=blender,
    )
    result["spritesheet_exit"] = code
    result["ok"] = code == 0 and sheet_path.is_file()
    result["sheet"] = str(sheet_path) if sheet_path.is_file() else None
    result["hero"] = str(hero_path) if hero_path.is_file() else None
    return result


def _make_mask(rgba: Image.Image) -> Image.Image:
    a = rgba.split()[-1]
    return Image.merge("RGB", (a, a, a)).convert("1")


def _icon_silhouette(name: str, size: int) -> Image.Image:
    """
    Distinct Transcendence-style item silhouette per living-weapon archetype.
    Mesh ortho exports were flat panels; these cutouts make diffuse skins readable.
    """
    from PIL import ImageDraw

    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    s = float(size)
    cx = cy = s * 0.5
    n = name.lower()

    def poly(pts, fill=255):
        d.polygon([(float(x), float(y)) for x, y in pts], fill=fill)

    def nova_blade_pinwheel(*, scale: float = 1.0, hub: float = 0.14):
        """Nova Drift Blade: 4 stepped blades around concentric hub."""
        for i in range(4):
            ang = i * (math.pi / 2) + math.pi / 4
            ca, sa = math.cos(ang), math.sin(ang)
            # Local blade (tip outward) with notched outer edge
            local = [
                (s * 0.06 * scale, 0.0),
                (s * 0.18 * scale, -s * 0.10 * scale),
                (s * 0.38 * scale, -s * 0.12 * scale),
                (s * 0.42 * scale, -s * 0.06 * scale),  # notch step
                (s * 0.46 * scale, -s * 0.10 * scale),
                (s * 0.48 * scale, 0.0),
                (s * 0.46 * scale, s * 0.10 * scale),
                (s * 0.42 * scale, s * 0.06 * scale),
                (s * 0.38 * scale, s * 0.12 * scale),
                (s * 0.18 * scale, s * 0.10 * scale),
            ]
            pts = [(cx + lx * ca - ly * sa, cy + lx * sa + ly * ca) for lx, ly in local]
            poly(pts)
        r_hub = s * hub * scale
        d.ellipse([cx - r_hub, cy - r_hub, cx + r_hub, cy + r_hub], fill=255)
        r_inner = r_hub * 0.55
        d.ellipse([cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner], fill=200)

    def nova_sword_crescents(*, scale: float = 1.0):
        """Nova Drift Sword: dual orbiting crescent blades + jagged crystal hub."""
        # Crystal hub spikes (forward cluster)
        for i, ang in enumerate((-0.55, -0.18, 0.18, 0.55, math.pi)):
            ca, sa = math.cos(ang - math.pi / 2), math.sin(ang - math.pi / 2)
            tip = s * (0.22 if i < 4 else 0.14) * scale
            base = s * 0.05 * scale
            local = [(0.0, -base), (tip, 0.0), (0.0, base), (-base * 0.6, 0.0)]
            pts = [(cx + lx * ca - ly * sa, cy + lx * sa + ly * ca) for lx, ly in local]
            poly(pts)
        d.ellipse(
            [cx - s * 0.08 * scale, cy - s * 0.08 * scale, cx + s * 0.08 * scale, cy + s * 0.08 * scale],
            fill=255,
        )
        # Two crescent blades (left / right), white hilt + sweeping arc
        for side in (-1, 1):
            hilt = [
                (cx + side * s * 0.18 * scale, cy - s * 0.02 * scale),
                (cx + side * s * 0.28 * scale, cy - s * 0.10 * scale),
                (cx + side * s * 0.32 * scale, cy),
                (cx + side * s * 0.28 * scale, cy + s * 0.10 * scale),
                (cx + side * s * 0.18 * scale, cy + s * 0.02 * scale),
            ]
            poly(hilt)
            # Approximate crescent as thick curved polygon
            arc = []
            for t in range(0, 11):
                a = (-math.pi / 2) + side * (t / 10.0) * math.pi
                r = s * (0.42 + 0.04 * math.sin(t / 10.0 * math.pi)) * scale
                arc.append((cx + math.cos(a) * r, cy + math.sin(a) * r * 0.95))
            for t in range(10, -1, -1):
                a = (-math.pi / 2) + side * (t / 10.0) * math.pi
                r = s * (0.30 + 0.03 * math.sin(t / 10.0 * math.pi)) * scale
                arc.append((cx + math.cos(a) * r, cy + math.sin(a) * r * 0.95))
            poly(arc)

    def nova_torrent_spray(*, scale: float = 1.0):
        """Nova Drift Torrent: circular hub + staggered almond needles in a conical fan."""
        r_hub = s * 0.10 * scale
        d.ellipse([cx - r_hub, cy - r_hub, cx + r_hub, cy + r_hub], fill=255)
        r_ring = r_hub * 1.35
        d.ellipse([cx - r_ring, cy - r_ring, cx + r_ring, cy + r_ring], fill=200)
        # Fan of droplet needles aimed right (forward)
        for i, ang in enumerate((-0.55, -0.35, -0.18, 0.0, 0.18, 0.35, 0.55, -0.45, 0.45)):
            ca, sa = math.cos(ang), math.sin(ang)
            length = s * (0.38 + (0.04 if i % 2 else 0.0)) * scale
            width = s * 0.045 * scale
            # Almond: tip forward, blunt rear near hub
            local = [
                (s * 0.12 * scale, 0.0),
                (length * 0.55, -width),
                (length, 0.0),
                (length * 0.55, width),
            ]
            pts = [(cx + lx * ca - ly * sa, cy + lx * sa + ly * ca) for lx, ly in local]
            poly(pts)
        # Jagged branch tendril accents
        for side in (-1, 1):
            poly(
                [
                    (cx + s * 0.14 * scale, cy + side * s * 0.02 * scale),
                    (cx + s * 0.28 * scale, cy + side * s * 0.12 * scale),
                    (cx + s * 0.36 * scale, cy + side * s * 0.08 * scale),
                    (cx + s * 0.30 * scale, cy + side * s * 0.14 * scale),
                    (cx + s * 0.18 * scale, cy + side * s * 0.06 * scale),
                ]
            )

    def nova_blaster_twins(*, scale: float = 1.0):
        """Nova Drift starting Blaster: twin diamond bolts on a soft trail axis."""
        # Broad tracer band (alpha via lower fill)
        poly(
            [
                (cx - s * 0.35 * scale, cy - s * 0.06 * scale),
                (cx + s * 0.40 * scale, cy - s * 0.04 * scale),
                (cx + s * 0.40 * scale, cy + s * 0.04 * scale),
                (cx - s * 0.35 * scale, cy + s * 0.06 * scale),
            ],
            fill=160,
        )
        for dy in (-s * 0.10 * scale, s * 0.10 * scale):
            # Diamond bolt
            poly(
                [
                    (cx - s * 0.06 * scale, cy + dy),
                    (cx, cy + dy - s * 0.05 * scale),
                    (cx + s * 0.14 * scale, cy + dy),
                    (cx, cy + dy + s * 0.05 * scale),
                ]
            )
            # Soft bloom ellipse
            d.ellipse(
                [
                    cx - s * 0.04 * scale,
                    cy + dy - s * 0.035 * scale,
                    cx + s * 0.10 * scale,
                    cy + dy + s * 0.035 * scale,
                ],
                fill=220,
            )

    def nova_thermal_lance(*, scale: float = 1.0):
        """Nova Drift Thermal Lance: focus ring + tapered continuous beam + side sparks."""
        # Muzzle focus ring
        r = s * 0.10 * scale
        d.ellipse([cx - r - s * 0.28 * scale, cy - r, cx - s * 0.28 * scale + r, cy + r], fill=200)
        d.ellipse(
            [
                cx - r * 0.55 - s * 0.28 * scale,
                cy - r * 0.55,
                cx - s * 0.28 * scale + r * 0.55,
                cy + r * 0.55,
            ],
            fill=255,
        )
        # Tapered lance body (wide at muzzle → tip)
        poly(
            [
                (cx - s * 0.22 * scale, cy - s * 0.08 * scale),
                (cx + s * 0.42 * scale, cy - s * 0.015 * scale),
                (cx + s * 0.48 * scale, cy),
                (cx + s * 0.42 * scale, cy + s * 0.015 * scale),
                (cx - s * 0.22 * scale, cy + s * 0.08 * scale),
            ]
        )
        # Bright core line
        poly(
            [
                (cx - s * 0.20 * scale, cy - s * 0.025 * scale),
                (cx + s * 0.40 * scale, cy - s * 0.008 * scale),
                (cx + s * 0.40 * scale, cy + s * 0.008 * scale),
                (cx - s * 0.20 * scale, cy + s * 0.025 * scale),
            ],
            fill=255,
        )
        # Side sparks
        for dy, ox in ((-0.14, 0.05), (0.12, 0.12), (-0.08, 0.22)):
            poly(
                [
                    (cx + s * ox * scale, cy + s * dy * scale),
                    (cx + s * (ox + 0.10) * scale, cy + s * (dy - 0.02) * scale),
                    (cx + s * (ox + 0.14) * scale, cy + s * dy * scale),
                    (cx + s * (ox + 0.10) * scale, cy + s * (dy + 0.02) * scale),
                ]
            )

    def nova_railgun_bolt(*, scale: float = 1.0):
        """Nova Drift Railgun: arrowhead slug + long cyan double-line trail + muzzle rings."""
        # Trail double lines
        for dy in (-s * 0.025 * scale, s * 0.025 * scale):
            poly(
                [
                    (cx - s * 0.40 * scale, cy + dy - s * 0.008 * scale),
                    (cx + s * 0.18 * scale, cy + dy - s * 0.006 * scale),
                    (cx + s * 0.18 * scale, cy + dy + s * 0.006 * scale),
                    (cx - s * 0.40 * scale, cy + dy + s * 0.008 * scale),
                ],
                fill=180,
            )
        # Soft trail glow
        poly(
            [
                (cx - s * 0.38 * scale, cy - s * 0.04 * scale),
                (cx + s * 0.10 * scale, cy - s * 0.02 * scale),
                (cx + s * 0.10 * scale, cy + s * 0.02 * scale),
                (cx - s * 0.38 * scale, cy + s * 0.04 * scale),
            ],
            fill=140,
        )
        # Arrowhead tip
        poly(
            [
                (cx + s * 0.12 * scale, cy),
                (cx + s * 0.28 * scale, cy - s * 0.06 * scale),
                (cx + s * 0.42 * scale, cy),
                (cx + s * 0.28 * scale, cy + s * 0.06 * scale),
            ]
        )
        # Muzzle rings (near left of tip / ship side)
        for rr in (0.10, 0.14):
            r = s * rr * scale
            d.ellipse([cx - r - s * 0.05 * scale, cy - r, cx - s * 0.05 * scale + r, cy + r], outline=255)
        # Rear discharge shards
        for ang in (-0.55, 0.0, 0.55):
            ca, sa = math.cos(ang + math.pi), math.sin(ang + math.pi)
            tip = s * 0.18 * scale
            local = [(0.0, 0.0), (tip, -s * 0.04 * scale), (tip * 0.7, 0.0), (tip, s * 0.04 * scale)]
            pts = [
                (cx - s * 0.05 * scale + lx * ca - ly * sa, cy + lx * sa + ly * ca) for lx, ly in local
            ]
            poly(pts, fill=200)

    if "blaster" in n:
        nova_blaster_twins(scale=0.9 if "module" in n else 1.0)
    elif "railshrapnel" in n:
        poly([(cx, cy - s * 0.08), (cx + s * 0.18, cy), (cx, cy + s * 0.08), (cx - s * 0.10, cy)])
    elif "railgun" in n or n.endswith("rail"):
        nova_railgun_bolt(scale=0.9 if "module" in n else 1.0)
    elif "thermalspark" in n:
        # Side sparks only — small teardrops, not the heat beam
        for dy, ox in ((0.0, 0.0),):
            poly(
                [
                    (cx - s * 0.08, cy),
                    (cx + s * 0.05, cy - s * 0.06),
                    (cx + s * 0.22, cy),
                    (cx + s * 0.05, cy + s * 0.06),
                ]
            )
    elif "thermallure" in n or "thermal_lance" in n or "thermallance" in n:
        nova_thermal_lance(scale=0.9 if "module" in n else 1.0)
    elif "bladechamber" in n or n.endswith("bladechamber"):
        nova_blade_pinwheel(scale=1.0, hub=0.15)
    elif "blademodule" in n:
        nova_blade_pinwheel(scale=0.82, hub=0.13)
    elif "torrent" in n:
        nova_torrent_spray(scale=0.85 if "module" in n and not n.startswith("pt") else 1.0)
    elif "swordchamber" in n:
        nova_sword_crescents(scale=1.0)
    elif "swordmodule" in n:
        nova_sword_crescents(scale=0.78)
    elif "shield" in n:
        # Heater / aegis shield
        poly(
            [
                (cx, s * 0.08),
                (s * 0.88, s * 0.28),
                (s * 0.82, s * 0.62),
                (cx, s * 0.92),
                (s * 0.18, s * 0.62),
                (s * 0.12, s * 0.28),
            ]
        )
    elif "firemodule" in n or "novasplit" in n:
        # Fire mods sit on Blaster baseline twin-bolt glyph
        nova_blaster_twins(scale=0.75)
    elif "wildmod" in n:
        # Chaotic starburst
        pts = []
        for i in range(12):
            ang = i * math.pi / 6 - math.pi / 2
            r = s * (0.46 if i % 2 == 0 else 0.26)
            pts.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))
        poly(pts)
    elif "tiermod" in n:
        # Growth crystal square with facets
        d.rounded_rectangle((s * 0.14, s * 0.14, s * 0.86, s * 0.86), radius=s * 0.12, fill=255)
        poly([(cx, s * 0.18), (s * 0.78, cx), (cx, s * 0.82), (s * 0.22, cx)], fill=200)
    elif "esmod" in n:
        # Engineered ship-mod plate
        d.rounded_rectangle((s * 0.12, s * 0.22, s * 0.88, s * 0.78), radius=s * 0.08, fill=255)
        poly([(s * 0.20, s * 0.35), (s * 0.50, s * 0.18), (s * 0.80, s * 0.35), (s * 0.80, s * 0.65), (s * 0.50, s * 0.82), (s * 0.20, s * 0.65)])
    elif "leviathan" in n:
        # Serpent organ / bio-weapon
        d.ellipse([s * 0.18, s * 0.22, s * 0.82, s * 0.78], fill=255)
        poly([(s * 0.55, s * 0.30), (s * 0.95, s * 0.20), (s * 0.88, s * 0.45)])
        poly([(s * 0.55, s * 0.70), (s * 0.95, s * 0.80), (s * 0.88, s * 0.55)])
        poly([(s * 0.05, cy), (s * 0.28, s * 0.35), (s * 0.28, s * 0.65)])
    elif "discordorb" in n or (n.startswith("pt") and "orb" in n):
        d.ellipse([s * 0.12, s * 0.12, s * 0.88, s * 0.88], fill=255)
        d.ellipse([s * 0.28, s * 0.28, s * 0.72, s * 0.72], fill=180)
    elif "livingblade" in n or n == "ptlivingblade":
        nova_blade_pinwheel(scale=0.95, hub=0.14)
    elif "livingsword" in n or n == "ptlivingsword":
        nova_sword_crescents(scale=0.92)
    elif "livingball" in n or n == "ptlivingball":
        d.ellipse([s * 0.18, s * 0.18, s * 0.82, s * 0.82], fill=255)
        d.ellipse([s * 0.35, s * 0.35, s * 0.65, s * 0.65], fill=200)
    elif "levelfx" in n:
        d.ellipse([s * 0.08, s * 0.08, s * 0.92, s * 0.92], fill=200)
        d.ellipse([s * 0.22, s * 0.22, s * 0.78, s * 0.78], fill=255)
    else:
        # Default faceted crystal module
        poly(
            [
                (cx, s * 0.10),
                (s * 0.82, s * 0.32),
                (s * 0.82, s * 0.68),
                (cx, s * 0.90),
                (s * 0.18, s * 0.68),
                (s * 0.18, s * 0.32),
            ]
        )

    # Soft edge
    return m.filter(ImageFilter.GaussianBlur(radius=max(0.6, size / 96.0)))


def _skin_through_silhouette(diffuse: Image.Image, sil: Image.Image, size: int) -> Image.Image:
    """Map PBR diffuse through archetype silhouette with neon rim."""
    from PIL import ImageDraw, ImageFilter as IF

    d = diffuse.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    # Slight vignette boost toward neon
    enh = ImageEnhance.Color(d).enhance(1.25)
    enh = ImageEnhance.Contrast(enh).enhance(1.15)
    d = enh.convert("RGBA")
    sil = sil.resize((size, size), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(d, (0, 0))
    out.putalpha(sil)
    # Neon rim from silhouette edge
    edge = sil.filter(IF.FIND_EDGES).point(lambda v: 255 if v > 20 else 0)
    edge = edge.filter(IF.GaussianBlur(radius=1.2))
    rim = Image.new("RGBA", (size, size), (230, 170, 255, 0))
    rim.putalpha(edge.point(lambda v: int(v * 0.85)))
    out = Image.alpha_composite(out, rim)
    # Soft outer glow
    glow = sil.filter(IF.GaussianBlur(radius=size * 0.08))
    glow_layer = Image.new("RGBA", (size, size), (180, 120, 255, 0))
    glow_layer.putalpha(glow.point(lambda v: int(v * 0.35)))
    return Image.alpha_composite(glow_layer, out)


def _load_icon_tile(pack_dir: Path, name: str, size: int = ICON) -> Image.Image:
    """Prefer PBR diffuse cut through a distinctive silhouette (not flat mesh hex)."""
    diffuse = pack_dir / "Skins" / f"{name}_diffuse.png"
    emission = pack_dir / "Skins" / f"{name}_emission.png"

    if diffuse.is_file():
        base = Image.open(diffuse).convert("RGBA")
        if emission.is_file():
            em = Image.open(emission).convert("RGBA").resize(base.size, Image.Resampling.LANCZOS)
            # Add emission glow into diffuse
            br, bg, bb, ba = base.split()
            er, eg, eb, _ea = em.split()
            br = ImageChops.add(br, er.point(lambda p: int(p * 0.45)))
            bg = ImageChops.add(bg, eg.point(lambda p: int(p * 0.45)))
            bb = ImageChops.add(bb, eb.point(lambda p: int(p * 0.45)))
            base = Image.merge("RGBA", (br, bg, bb, ba))
        sil = _icon_silhouette(name, size)
        im = _skin_through_silhouette(base, sil, size)
    else:
        # Fallback: ortho sheet / rounded plate
        hero = pack_dir / f"{name}Large.jpg"
        sheet = pack_dir / f"{name}.jpg"
        src = hero if hero.is_file() else sheet
        im = None
        if src.is_file():
            im = Image.open(src).convert("RGBA")
            if sheet.is_file() and src == sheet:
                fw = size
                for cand in (96, 32, 128, 64):
                    if im.width >= cand and im.height >= cand:
                        fw = cand
                        break
                im = im.crop((0, 0, fw, fw))
            im = im.resize((size, size), Image.Resampling.LANCZOS)
        if im is None:
            im = Image.new("RGBA", (size, size), (40, 20, 60, 255))
        sil = _icon_silhouette(name, size)
        im.putalpha(sil)

    px = im.load()
    for y in range(size):
        for x in range(size):
            r, g, b, a = px[x, y]
            if a > 0 and r + g + b < 24:
                px[x, y] = (0, 0, 0, 0)
    return im


def _tint_variant(base: Image.Image, seed: int) -> Image.Image:
    """Slight per-item hue/contrast variation so shared archetypes aren't identical."""
    img = base.copy()
    hue_shift = ((seed % 21) - 10) / 40.0
    if abs(hue_shift) > 0.01:
        hsv = img.convert("RGB").convert("HSV")
        h, s, v = hsv.split()
        h = h.point(lambda p: int((p + int(hue_shift * 255)) % 256))
        img = Image.merge("HSV", (h, s, v)).convert("RGBA")
        # restore alpha from base
        img.putalpha(base.split()[-1])
    contrast = 1.0 + ((seed % 7) - 3) * 0.03
    rgb = ImageEnhance.Contrast(img.convert("RGB")).enhance(contrast)
    out = rgb.convert("RGBA")
    out.putalpha(base.split()[-1])
    return out


def assemble_and_deploy(
    registry: Dict[str, Any],
    out_root: Path,
    deploy_dir: Path,
) -> Dict[str, Any]:
    deploy_dir.mkdir(parents=True, exist_ok=True)
    assignments: Dict[str, str] = dict(registry.get("iconAssignments") or {})
    # Stable ICON_ORDER from assignments keys in registry order + known extras
    icon_order = list(assignments.keys())
    if "ptDiscordOrb" not in icon_order:
        icon_order.append("ptDiscordOrb")

    # Cache archetype tiles
    arch_tiles: Dict[str, Image.Image] = {}
    for asset in registry.get("assets") or []:
        if asset.get("kind") != "icon" and asset.get("id") not in (
            "ptDiscordOrb",
            "lwLeviathanWeapon",
        ):
            if asset.get("kind") == "fx":
                continue
            if asset.get("kind") == "projectile" and asset.get("id") == "ptDiscordOrb":
                pass
            elif asset.get("kind") == "projectile":
                continue
        name = asset["name"]
        pack = out_root / name
        if pack.is_dir():
            arch_tiles[asset["id"]] = _load_icon_tile(pack, name, ICON)

    mapping: Dict[str, Any] = {}
    n = len(icon_order)
    rows = max(1, math.ceil(n / COLS))
    atlas = Image.new("RGBA", (COLS * ICON, rows * ICON), (0, 0, 0, 0))
    for i, ent in enumerate(icon_order):
        arch = assignments.get(ent, "lwFireModule")
        base = arch_tiles.get(arch)
        if base is None:
            # try pack named after archetype
            pack = out_root / arch
            base = _load_icon_tile(pack, arch, ICON) if pack.is_dir() else Image.new(
                "RGBA", (ICON, ICON), (60, 30, 90, 255)
            )
            arch_tiles[arch] = base
        tile = _tint_variant(base, abs(hash(ent)) % 10_000)
        col, row = i % COLS, i // COLS
        x, y = col * ICON, row * ICON
        atlas.paste(tile, (x, y), tile)
        mapping[ent] = {"x": x, "y": y, "w": ICON, "h": ICON, "index": i, "archetype": arch}

    jpg = deploy_dir / "LivingWeaponItemIcons.jpg"
    mask = deploy_dir / "LivingWeaponItemIconsMask.bmp"
    atlas.convert("RGB").save(jpg, quality=92)
    _make_mask(atlas).save(mask)
    (deploy_dir / "living_weapon_icon_map.json").write_text(
        json.dumps(mapping, indent=2), encoding="utf-8"
    )
    print(f"[OK] icons {jpg} ({COLS}x{rows}, {n} tiles)")

    # Level FX: three tinted copies of lwLevelFX hero
    fx_pack = out_root / "lwLevelFX"
    fx_base = _load_icon_tile(fx_pack, "lwLevelFX", ICON) if fx_pack.is_dir() else None
    fx_sheet = Image.new("RGBA", (ICON * 3, ICON), (0, 0, 0, 0))
    tints = [
        (0.55, 0.85, 1.0),  # low cyan
        (0.85, 0.55, 1.0),  # mid violet
        (1.0, 0.65, 0.35),  # high amber
    ]
    for i, (tr, tg, tb) in enumerate(tints):
        if fx_base is None:
            tile = Image.new("RGBA", (ICON, ICON), (0, 0, 0, 0))
        else:
            tile = fx_base.copy()
            r, g, b, a = tile.split()
            r = r.point(lambda p, t=tr: int(min(255, p * t)))
            g = g.point(lambda p, t=tg: int(min(255, p * t)))
            b = b.point(lambda p, t=tb: int(min(255, p * t)))
            tile = Image.merge("RGBA", (r, g, b, a))
        fx_sheet.paste(tile, (i * ICON, 0), tile)
    fx_jpg = deploy_dir / "LivingWeaponLevelFX.jpg"
    fx_sheet.convert("RGB").save(fx_jpg, quality=92)
    _make_mask(fx_sheet).save(deploy_dir / "LivingWeaponLevelFXMask.bmp")
    print(f"[OK] level FX {fx_jpg}")

    # Projectile strips
    def _copy_proj(asset_id: str, dest_name: str) -> None:
        pack = out_root / asset_id
        sheet = pack / f"{asset_id}.jpg"
        hero = pack / f"{asset_id}Large.jpg"
        if sheet.is_file():
            shutil.copy2(sheet, deploy_dir / f"{dest_name}.jpg")
            m = pack / f"{asset_id}Mask.bmp"
            if m.is_file():
                shutil.copy2(m, deploy_dir / f"{dest_name}Mask.bmp")
            else:
                rgba = Image.open(sheet).convert("RGBA")
                _make_mask(rgba).save(deploy_dir / f"{dest_name}Mask.bmp")
            print(f"[OK] projectile {dest_name}.jpg")
        elif hero.is_file():
            # Build 8-frame strip by rotating hero (fallback)
            h = Image.open(hero).convert("RGBA").resize((32, 32), Image.Resampling.LANCZOS)
            strip = Image.new("RGBA", (32 * 8, 32), (0, 0, 0, 0))
            for i in range(8):
                strip.paste(h.rotate(-i * 45, expand=False, fillcolor=(0, 0, 0, 0)), (i * 32, 0))
            strip.convert("RGB").save(deploy_dir / f"{dest_name}.jpg", quality=95)
            _make_mask(strip).save(deploy_dir / f"{dest_name}Mask.bmp")
            print(f"[OK] projectile {dest_name}.jpg (rotated hero fallback)")

    _copy_proj("ptDiscordOrb", "DiscordOrb")
    # Melee combined strip: blade / sword / ball rows
    melee = Image.new("RGBA", (32 * 8, 32 * 3), (0, 0, 0, 0))
    for row, aid in enumerate(("ptLivingBlade", "ptLivingSword", "ptLivingBall")):
        pack = out_root / aid
        sheet = pack / f"{aid}.jpg"
        if sheet.is_file():
            im = Image.open(sheet).convert("RGBA")
            # Normalize to 8*32 x 32
            target = Image.new("RGBA", (32 * 8, 32), (0, 0, 0, 0))
            target.paste(im.resize((32 * 8, 32), Image.Resampling.LANCZOS), (0, 0))
            melee.paste(target, (0, row * 32), target)
        else:
            _copy_proj(aid, aid)  # still export solo if needed
    if any((out_root / a / f"{a}.jpg").is_file() for a in ("ptLivingBlade", "ptLivingSword", "ptLivingBall")):
        melee.convert("RGB").save(deploy_dir / "LivingMeleeProjectiles.jpg", quality=95)
        _make_mask(melee).save(deploy_dir / "LivingMeleeProjectilesMask.bmp")
        print(f"[OK] melee {deploy_dir / 'LivingMeleeProjectiles.jpg'}")

    # Discord icon convenience
    if (deploy_dir / "DiscordOrb.jpg").is_file():
        d = Image.open(deploy_dir / "DiscordOrb.jpg").convert("RGBA")
        single = d.crop((0, 0, min(32, d.width), min(32, d.height))).resize(
            (96, 96), Image.Resampling.NEAREST
        )
        single.convert("RGB").save(deploy_dir / "DiscordOrbIcon.jpg", quality=95)
        _make_mask(single).save(deploy_dir / "DiscordOrbIconMask.bmp")

    return {"icons": n, "deploy": str(deploy_dir)}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Living weapons: PBR → mesh → ortho (same path as CrossMod ships)"
    )
    ap.add_argument(
        "--out-dir",
        default=r"C:\Output\LivingWeaponAssets",
        help="Working output (Skins/Meshes/sheets per asset)",
    )
    ap.add_argument("--registry", default=str(_REGISTRY_FILE))
    ap.add_argument("--asset-id", action="append", default=[], help="Only these asset ids")
    ap.add_argument("--quality", default="standard", choices=["draft", "standard", "high", "ultra", "reuse"])
    ap.add_argument("--no-sd", action="store_true", help="Procedural PBR only")
    ap.add_argument(
        "--mesh-source",
        choices=("auto", "blender", "trellis"),
        default="auto",
        help="auto starts TRELLIS; blender = mesh_skin_export only",
    )
    ap.add_argument("--skins-only", action="store_true")
    ap.add_argument("--assemble-only", action="store_true", help="Skip generate; assemble+deploy from out-dir")
    ap.add_argument("--deploy-resources", action="store_true")
    ap.add_argument("--deploy-dir", default=str(_GAME_DEPLOY))
    ap.add_argument("--blender", default=None)
    args = ap.parse_args()

    registry = _load_registry(Path(args.registry))
    assets: List[Dict[str, Any]] = list(registry.get("assets") or [])
    if args.asset_id:
        wanted = set(args.asset_id)
        assets = [a for a in assets if a.get("id") in wanted]
        if not assets:
            print(f"[ERROR] no assets matched {wanted}")
            return 1

    out_root = Path(args.out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    results = []

    if not args.assemble_only:
        pending = []
        session_cm = tx.session() if (tx and not args.no_sd) else None
        if tx:
            tx.print_probe()
        try:
            if session_cm:
                session_cm.__enter__()
            for asset in assets:
                print(f"\n=== {asset.get('id')} ({asset.get('kind')}) ===")
                r = export_asset_pack(
                    asset,
                    out_root,
                    quality=args.quality,
                    use_sd=not args.no_sd,
                    skins_only=args.skins_only,
                    blender=args.blender,
                    mesh_source=args.mesh_source,
                    defer_render=not args.skins_only,
                )
                pending.append(r)
                print(f"[{'OK' if r.get('ok') else 'FAIL'}] {asset.get('id')} method={r.get('method')}")
        finally:
            if session_cm:
                session_cm.__exit__(None, None, None)

        if not args.skins_only:
            print("\n=== Ucupaint bake + spritesheets (GPU servers stopped) ===")
            for r in pending:
                if not r.get("ok") or not r.get("mesh"):
                    results.append(r)
                    continue
                results.append(finish_asset_pack(r, blender=args.blender))
                print(f"[{'OK' if results[-1].get('ok') else 'FAIL'}] sheet {r.get('id')}")
        else:
            results = pending

        summary = out_root / "living_weapon_generation_summary.json"
        summary.write_text(json.dumps(results, indent=2), encoding="utf-8")
        ok = sum(1 for r in results if r.get("ok"))
        print(f"\nDone generate: {ok}/{len(results)} ok -> {summary}")

    if args.deploy_resources or args.assemble_only:
        info = assemble_and_deploy(registry, out_root, Path(args.deploy_dir))
        print(f"[OK] deployed {info}")

    if results and not any(r.get("ok") for r in results) and not args.assemble_only:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
