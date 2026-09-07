#!/usr/bin/env python3
"""
Generate alt HUD textures from current Transcendence armor/shield content.

Scans base game + DLC + Extensions ItemTypes (via tx_item_alt_mesh catalog).
For each armor/shield item (and family), writes UI textures under:

  <Pack>/Source/Models/Alt/Textures/Armor/{entity}.png
  <Pack>/Source/Models/Alt/Textures/Shield/{entity}.png
  <Pack>/Source/Models/Alt/Textures/Armor/family_{fam}.png
  ...

Re-run after adding mods/DLC content; only missing files are generated unless
--force. Uses Stable Diffusion when available, else procedural textures from
item family + ship hero. Optional Ollama prompt enrichment from item metadata.

Wire-in: ship_hud_export prefers these textures when composing unique HUD.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from tx_item_alt_mesh import (
    FAMILY_COLORS,
    alt_models_dir,
    catalog_armor_shield_items,
    family_color,
    seed_alt_mesh_pool,
)

TEX_REL = Path("Textures")


def textures_dir(pack_dir: Path) -> Path:
    return alt_models_dir(pack_dir) / TEX_REL


def texture_path(pack_dir: Path, kind: str, entity_or_family: str) -> Path:
    sub = "Armor" if kind == "armor" else "Shield"
    return textures_dir(pack_dir) / sub / f"{entity_or_family}.png"


def resolve_alt_texture(
    pack_dir: Path,
    *,
    kind: str,
    entity: str,
    family: str = "default",
) -> Optional[Path]:
    for key in (entity, f"family_{family}", "family_default"):
        p = texture_path(pack_dir, kind, key)
        if p.is_file():
            return p
    return None


def _hex(rgb: Tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _item_prompt(rec: Dict[str, Any], *, kind: str) -> str:
    name = rec.get("name") or rec.get("entity") or kind
    fam = rec.get("family") or "default"
    level = rec.get("level") or 1
    attrs = (rec.get("attributes") or "").replace(",", " ")
    if kind == "armor":
        return (
            f"top-down spaceship armor HUD overlay texture, {name}, "
            f"level {level} {fam} plating, {attrs}, metallic panel segments, "
            f"game UI asset, dark void background, clear silhouette, no text"
        )
    return (
        f"top-down spaceship shield HUD energy ring texture, {name}, "
        f"level {level} {fam} deflector field, {attrs}, translucent glow oval, "
        f"game UI asset, dark void background, no text"
    )


def _enrich_prompt_ollama(
    prompt: str,
    rec: Dict[str, Any],
    *,
    model: str,
    ollama_url: str,
) -> str:
    try:
        import urllib.request

        from ollama_mesh_spec import acquire_gpu, ollama_memory_options

        options = ollama_memory_options()
        body = json.dumps(
            {
                "model": model,
                "stream": False,
                "options": options,
                "prompt": (
                    "Rewrite this into one concise Stable Diffusion prompt for a "
                    "Transcendence ship status HUD texture (no commentary):\n"
                    f"item={rec.get('entity')} name={rec.get('name')} "
                    f"family={rec.get('family')} level={rec.get('level')}\n"
                    f"base: {prompt}"
                ),
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            ollama_url.rstrip("/") + "/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # GPU turn-taking: CPU-only calls (num_gpu=0) skip the shared lock.
        with acquire_gpu(f"Ollama HUD-prompt {model}", enabled=options.get("num_gpu") != 0):
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        text = (data.get("response") or "").strip().splitlines()[0].strip()
        return text[:400] if text else prompt
    except Exception as exc:
        print(f"[WARN] ollama prompt skip: {exc}", file=sys.stderr)
        return prompt


def _try_sd(prompt: str, path: Path, *, size: int, no_sd: bool) -> bool:
    if no_sd:
        return False
    try:
        from sd_http_client import detect_server, generate_image, plan_sd_size

        if not detect_server(verbose=False):
            return False
        # Right-size for the HUD delivery target (multiple-of-64, 512 floor,
        # capped supersample) instead of a fixed large request.
        gen_w, gen_h, gen_steps = plan_sd_size(size, size, "hud")
        gen_size = max(gen_w, gen_h)
        generate_image(
            prompt,
            path,
            width=gen_w,
            height=gen_h,
            steps=gen_steps,
            timeout=600.0,
            connect_timeout=5.0,
        )
        if path.exists() and size < gen_size:
            from PIL import Image

            im = Image.open(path).convert("RGBA")
            im = im.resize((size, size), Image.Resampling.LANCZOS)
            im.save(path)
        return path.is_file()
    except Exception as exc:
        print(f"[WARN] SD skip: {exc}", file=sys.stderr)
        return False


def _proc_armor_texture(
    size: int,
    tint: Tuple[int, int, int],
    *,
    hero: Optional[Path] = None,
    seed: int = 0,
) -> Any:
    from PIL import Image, ImageDraw, ImageFilter
    import random

    rng = random.Random(seed)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    if hero and Path(hero).is_file():
        base = Image.open(hero).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
        # recolor toward tint
        px = base.load()
        out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        op = out.load()
        for y in range(size):
            for x in range(size):
                r, g, b, a = px[x, y]
                if a < 20:
                    continue
                lum = (r + g + b) / 765.0
                if lum < 0.04 and a == 255:
                    continue
                op[x, y] = (
                    int(tint[0] * (0.35 + 0.65 * lum)),
                    int(tint[1] * (0.35 + 0.65 * lum)),
                    int(tint[2] * (0.35 + 0.65 * lum)),
                    255,
                )
        im = out
    d = ImageDraw.Draw(im)
    # plate seams
    for _ in range(4):
        y = rng.randint(size // 8, size - size // 8)
        d.line((size // 10, y, size - size // 10, y), fill=(*tint, 90), width=1)
    for _ in range(3):
        x = rng.randint(size // 8, size - size // 8)
        d.line((x, size // 10, x, size - size // 10), fill=(*tint, 70), width=1)
    return im.filter(ImageFilter.SMOOTH_MORE)


def _proc_shield_texture(
    size: int,
    tint: Tuple[int, int, int],
    *,
    hero: Optional[Path] = None,
    seed: int = 0,
) -> Any:
    from PIL import Image, ImageDraw, ImageFilter

    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    if hero and Path(hero).is_file():
        ship = Image.open(hero).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
        # darken ship as underlay
        dark = Image.new("RGBA", (size, size), (0, 0, 0, 180))
        im = Image.alpha_composite(Image.new("RGBA", (size, size), (0, 0, 0, 255)), ship)
        im = Image.alpha_composite(im, dark)
    d = ImageDraw.Draw(im)
    pad = size // 10
    for i, alpha in enumerate((40, 90, 160)):
        inset = pad + i * 3
        d.ellipse(
            [inset, inset, size - inset, size - inset],
            outline=(*tint, alpha),
            width=max(2, size // 48),
        )
    glow = im.filter(ImageFilter.GaussianBlur(radius=max(2, size // 24)))
    return Image.alpha_composite(glow, im)


def _save_png(im: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "PNG")


def _targets_from_catalog(
    catalog: Dict[str, List[Dict[str, Any]]],
    *,
    kinds: Sequence[str],
    max_per_kind: Optional[int],
) -> List[Tuple[str, Dict[str, Any], str]]:
    """(kind, record, filename_stem) including family_* entries."""
    out: List[Tuple[str, Dict[str, Any], str]] = []
    families_done: Dict[str, set] = {"armor": set(), "shield": set()}
    for kind in kinds:
        items = list(catalog.get(kind) or [])
        if max_per_kind is not None:
            items = items[: max_per_kind]
        for rec in items:
            out.append((kind, rec, rec["entity"]))
            fam = rec.get("family") or "default"
            if fam not in families_done[kind]:
                fam_rec = {
                    **rec,
                    "entity": f"family_{fam}",
                    "name": f"{fam} {kind}",
                    "family": fam,
                }
                out.append((kind, fam_rec, f"family_{fam}"))
                families_done[kind].add(fam)
        # always ensure family_default
        if "default" not in families_done[kind]:
            out.append(
                (
                    kind,
                    {
                        "entity": "family_default",
                        "name": f"default {kind}",
                        "family": "default",
                        "level": 1,
                        "attributes": "",
                    },
                    "family_default",
                )
            )
            families_done[kind].add("default")
    return out


def generate_alt_hud_textures(
    pack_dir: Path,
    *,
    ship_name: str = "",
    hero: Optional[Path] = None,
    base_mesh: Optional[Path] = None,
    tx_root: Optional[Path] = None,
    catalog: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    kinds: Sequence[str] = ("armor", "shield"),
    only_missing: bool = True,
    force: bool = False,
    no_sd: bool = False,
    use_ollama: bool = False,
    ollama_model: str = "qwen2.5-coder:7b",
    ollama_url: str = "http://127.0.0.1:11434",
    max_per_kind: Optional[int] = None,
    size: int = 256,
    seed_meshes: bool = True,
) -> Dict[str, Any]:
    """
    Generate alt UI textures for all (or missing) armor/shield items in current content.
    """
    pack_dir = Path(pack_dir)
    pack_dir.mkdir(parents=True, exist_ok=True)
    cat = catalog or catalog_armor_shield_items(tx_root)

    if not ship_name:
        # infer from Source/Models/*.fbx or pack folder name
        models = list((pack_dir / "Source" / "Models").glob("*.fbx")) if (pack_dir / "Source" / "Models").is_dir() else []
        ship_name = models[0].stem if models else pack_dir.name

    mesh = base_mesh
    if mesh is None:
        for p in (
            pack_dir / "Source" / "Models" / f"{ship_name}.fbx",
            pack_dir / "Meshes" / f"{ship_name}.fbx",
        ):
            if p.is_file():
                mesh = p
                break

    if seed_meshes:
        seed_alt_mesh_pool(
            pack_dir,
            ship_name,
            base_mesh=mesh,
            catalog=cat,
            tx_root=tx_root,
            max_per_kind=max_per_kind or 24,
        )

    hero_path = hero
    if hero_path is None:
        for p in (pack_dir / f"{ship_name}Large.jpg", pack_dir / f"{ship_name}_sketch.png"):
            if p.is_file():
                hero_path = p
                break

    tex_root = textures_dir(pack_dir)
    tex_root.mkdir(parents=True, exist_ok=True)
    (tex_root / "Armor").mkdir(exist_ok=True)
    (tex_root / "Shield").mkdir(exist_ok=True)

    readme = tex_root / "README.txt"
    if not readme.is_file():
        readme.write_text(
            "Alt HUD textures (generated from current armor/shield ItemTypes)\n"
            "==============================================================\n"
            "Re-run after adding mods/DLC:\n"
            "  .\\Generate-AamtShipHudAltTextures.ps1 -PackDir <pack>\n"
            "Only missing textures are created unless -Force.\n"
            "Used by unique ship ArmorDisplay / ShieldDisplay composition.\n",
            encoding="utf-8",
        )

    targets = _targets_from_catalog(cat, kinds=kinds, max_per_kind=max_per_kind)
    created: List[str] = []
    skipped: List[str] = []
    failed: List[str] = []
    sources: Dict[str, str] = {}

    only_missing = only_missing and not force

    for kind, rec, stem in targets:
        dest = texture_path(pack_dir, kind, stem)
        if only_missing and dest.is_file():
            skipped.append(str(dest))
            continue
        tint = family_color(rec.get("family") or "default")
        prompt = _item_prompt(rec, kind=kind)
        if use_ollama:
            prompt = _enrich_prompt_ollama(
                prompt, rec, model=ollama_model, ollama_url=ollama_url
            )
        ok = _try_sd(prompt, dest, size=size, no_sd=no_sd)
        src_tag = "sd"
        if not ok:
            seed = int(hashlib.md5(stem.encode()).hexdigest()[:8], 16)
            if kind == "armor":
                im = _proc_armor_texture(size, tint, hero=hero_path, seed=seed)
            else:
                im = _proc_shield_texture(size, tint, hero=hero_path, seed=seed)
            _save_png(im, dest)
            ok = dest.is_file()
            src_tag = "procedural"
        if ok:
            created.append(str(dest))
            sources[stem] = src_tag
            print(f"[alt_tex] {kind}/{stem} ({src_tag})", file=sys.stderr)
        else:
            failed.append(str(dest))

    manifest = {
        "ship": ship_name,
        "armorCatalog": len(cat.get("armor") or []),
        "shieldCatalog": len(cat.get("shield") or []),
        "created": created,
        "skippedExisting": len(skipped),
        "failed": failed,
        "sources": sources,
        "tintFamilies": {k: list(v) for k, v in FAMILY_COLORS.items()},
    }
    (tex_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    # refresh Alt catalog item lists
    alt_cat = alt_models_dir(pack_dir) / "catalog.json"
    if alt_cat.is_file():
        try:
            data = json.loads(alt_cat.read_text(encoding="utf-8"))
            data["textures"] = {
                "dir": str(tex_root),
                "created": len(created),
                "skipped": len(skipped),
            }
            alt_cat.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    print(
        f"[alt_tex] done: created={len(created)} skipped={len(skipped)} "
        f"failed={len(failed)} (catalog armor={manifest['armorCatalog']} "
        f"shield={manifest['shieldCatalog']})",
        file=sys.stderr,
    )
    return manifest


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pack-dir", required=True, help="Ship pack root (or Extension folder)")
    ap.add_argument("--name", default="", help="Ship name (default: infer)")
    ap.add_argument("--hero", default="")
    ap.add_argument("--mesh", default="")
    ap.add_argument("--tx-root", default="")
    ap.add_argument("--force", action="store_true", help="Regenerate even if texture exists")
    ap.add_argument("--no-sd", action="store_true")
    ap.add_argument("--ollama", action="store_true", help="Enrich prompts via Ollama")
    ap.add_argument("--model", default="qwen2.5-coder:7b")
    ap.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    ap.add_argument("--max-per-kind", type=int, default=0, help="0 = all catalog items")
    ap.add_argument("--size", type=int, default=256)
    ap.add_argument("--no-seed-meshes", action="store_true")
    ap.add_argument("--armor-only", action="store_true")
    ap.add_argument("--shield-only", action="store_true")
    args = ap.parse_args()

    kinds: List[str] = ["armor", "shield"]
    if args.armor_only:
        kinds = ["armor"]
    if args.shield_only:
        kinds = ["shield"]

    result = generate_alt_hud_textures(
        Path(args.pack_dir),
        ship_name=args.name,
        hero=Path(args.hero) if args.hero else None,
        base_mesh=Path(args.mesh) if args.mesh else None,
        tx_root=Path(args.tx_root) if args.tx_root else None,
        force=args.force,
        only_missing=not args.force,
        no_sd=args.no_sd,
        use_ollama=args.ollama,
        ollama_model=args.model,
        ollama_url=args.ollama_url,
        max_per_kind=args.max_per_kind or None,
        size=args.size,
        seed_meshes=not args.no_seed_meshes,
        kinds=kinds,
    )
    print(json.dumps({k: result[k] for k in ("ship", "armorCatalog", "shieldCatalog", "created", "skippedExisting", "failed") if k in result}, indent=2))
    # truncate created list in stdout summary
    summary = {
        "ship": result["ship"],
        "armorCatalog": result["armorCatalog"],
        "shieldCatalog": result["shieldCatalog"],
        "createdCount": len(result.get("created") or []),
        "skippedExisting": result.get("skippedExisting"),
        "failedCount": len(result.get("failed") or []),
    }
    print(json.dumps(summary, indent=2))
    return 1 if result.get("failed") and not result.get("created") else 0


if __name__ == "__main__":
    raise SystemExit(main())
