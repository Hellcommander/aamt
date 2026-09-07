#!/usr/bin/env python3
"""Generate Soulash 2 skill tilesheets via the local SD3.5 server.

Sheets follow workshop Geomancy (`assets.json` + `assets/*.png`). Tile indexes
count from the **bottom left** (docs §5). Placeholders from `write` are solid
color blocks; this replaces them with thematic 128px-cell icons packed into
padded sheets (`s2_assets.SHEET_TILE`).

Default pixels come from Tools/Shared SD3.5. ``inject-icon`` packs external
PNGs (including Cursor image-gen) through the same ``fit_icon_tile`` + bottom-left
repacker so atlas indexes stay valid. When SD is requested, wait/retry rather
than auto-falling back to procedural rings.

Downscale / pack / SD session live in ``s2_icon_pipeline`` so other Soulash 2
sheet generators use the same path.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from s2_assets import (
    TILE,
    SHEET_COLS,
    SHEET_TILE,
    default_assets,
    sheet_grid_for,
    write_icon_png,
    write_png,
    write_thumbnail_png,
    _rgb,
)
from s2_icon_pipeline import (
    NEGATIVE,
    compose_icon_prompt,
    empty_tile_bytes,
    fit_icon_tile,
    generate_sd_tile,
    pack_bottom_left,
    sd_session,
    seed_from_name,
    sheet_rows_for,
    unpack_bottom_left,
)
from s2_paths import staging_dir

SHEET_JOBS = (
    ("skills", "skills", "skill"),
    ("abilities", "abilities", "ability"),
    ("amplifiers", "amplifiers", "amplifier"),
    ("passives", "passive_skills", "passive"),
    ("stackers", "stackers", "stacker"),
)

_KIND_ROLE = {
    "skill": "skill school emblem, one recognizable object",
    "ability": "active ability icon",
    "amplifier": "ability support gem icon",
    "passive": "passive trait icon",
    "stacker": "status effect icon",
    "icon": "mod folder icon",
    "thumbnail": "workshop banner painting",
}


def _blurb(text: str, limit: int = 140) -> str:
    raw = " ".join(str(text or "").split())
    if len(raw) <= limit:
        return raw
    return raw[: limit - 1].rsplit(" ", 1)[0] + "…"


def _theme(spec: Dict[str, Any]) -> str:
    skill = spec.get("skill") or {}
    return str(skill.get("name") or spec.get("skill_id") or "skill")


def _school_accent(theme: str, name: str, description: str) -> str:
    blob = f"{theme} {name} {description}".lower()
    if any(w in blob for w in ("blood", "hemo", "sangui", "heart", "arter", "vein")):
        return (
            "anatomical heart / blood droplet motif, deep crimson and maroon accents, "
            "not a diamond, not a gem, not a crystal, not a rhombus"
        )
    if any(w in blob for w in ("water", "hydro", "aqua", "tide", "wave", "ocean", "brine", "splash")):
        return (
            "cresting wave or water droplet, cobalt and seafoam accents, liquid splash, "
            "not a sword, not a blade, not a diamond, not a gem"
        )
    if any(w in blob for w in ("acid", "vitriol", "corrosion", "caustic", "solvent", "fume")):
        return (
            "caustic flask or lime-green acid splash, neon lime and olive accents, "
            "alchemical vial, not a spike, not a diamond, not a gem"
        )
    if any(w in blob for w in ("cosmic", "star", "meteor", "gravity", "umbra", "astral", "stellar")):
        return (
            "star, meteor, or gravity well motif, violet and pale gold accents, "
            "night-sky magic, not a diamond, not a gem cluster"
        )
    if any(
        w in blob
        for w in (
            "wind",
            "gale",
            "zephyr",
            "air elemental",
            "aeromancy",
            "baromancy",
            "baro",
            "pressure",
            "shear",
            "tempest",
            "cyclone",
            "gust",
            "tornado",
        )
    ):
        return (
            "pale cyan, white mist, and steel-blue only, compressed airflow, "
            "not orange, not lime green, not red, not a yin-yang, "
            "not a lightning bolt, not a water wave, not a diamond, not a gem, not a sword"
        )
    return "not a diamond, not a gem, not a crystal, not a rhombus, not nested lozenges, not a sword"


# Concrete silhouettes so a whole school is not 30 identical swirls after 32px downscale.
_DISTINCT_MOTIF = {
    "air slice": "thin crescent cutting blade of compressed air, scythe arc from the side, not a round vortex",
    "gust push": "pale cyan forward shockwave cone, open-palm air blast shoving outward, not fire, not orange, not a flame, not a cyclone from above",
    "wind veil": "layered wind cloak wrapping a torso, air-fabric folds, not a ring, not a circle, not a black hole",
    "zephyr step": "dash afterimage, two footprints with a wind streak, motion lines, not a spiral",
    "cyclone grip": "hooking inward spiral yanking a silhouette toward the caster, grappling wind",
    "mini tornado": "small tornado funnel standing upright, dirt at the base, side view",
    "wind lance": "long thin spear of air pointing diagonally, piercing needle shaft, not a swirl",
    "tempest": "wide many-armed storm burst filling the tile, chaotic pressure collapse",
    "eye of the storm": "hurricane from above, spiral clouds around a bright calm eye, not a moon, not a crescent, not a line",
    "skybreaker": "air collapsing inward on one point, concentric implosion rings, pale cyan and white only, not yellow, not gold",
    "summon air elemental": "full humanoid wind elemental with head, arms, and swirling mist torso, creature, not a circle, not a ring",
    "become air elemental": "humanoid body made of rushing wind, running transformation, not feet, not a blade",
    "become living gale": "humanoid body made of rushing wind, running transformation, not feet, not a blade",
    "summon storm elemental": "bulky thundercloud elemental creature, dark cyan mass with a pale core",
    "shear edge": "serrated crescent edge, jagged wind blade",
    "wall collision": "body slammed into a stone wall with an impact burst, collision spark",
    "unleash momentum": "stacked chevrons bursting forward, stored force release",
    "sustained cell": "lingering small tornado sitting on one tile, duration cell",
    "pierce winds": "air arrow passing through a target, through-and-through hole",
    "collapse shear": "stacked rings snapping into a vulnerable mark, collapsing coils",
    "gale reach": "elongated wind stretching farther, extra-range arrow of air",
    "overpressure": "dense compressed sphere about to burst, tight packed air ball",
    "wind magic mastery": "school emblem, four-pointed wind rose / compass of air",
    "baromancy mastery": "school emblem, four-pointed wind rose / compass of air",
    "aerodynamic flow": "streamlined running silhouette with a tailwind",
    "stormborn reflexes": "dodging silhouette slipping past a projectile",
    "pressure mastery": "wall-slam burst, bonus impact on collision",
    "momentum overflow": "overflowing wind reservoir, full bar bursting pale cyan",
    "momentum": "upward tailwind chevron, caster haste wisp, vertical not circular",
    "shear": "dragging slow spiral around feet, sticky air coils, status mark",
    "wind magic": "school emblem, pale cyan pressure spiral with a cutting crescent",
    "baromancy": "school emblem, pale cyan pressure spiral with a cutting crescent",
    "deluge": "sheets of falling rain filling the tile, torrential downpour wall, cobalt water",
    "geyser burst": "vertical water geyser exploding upward, white foam, not a sword",
    "water vortex": "overhead cobalt whirlpool with white foam spiral, visible funnel of water, not an empty ring, not a black hole, not neon green, not a hollow circle",
    "mistform": "pale humanoid body dissolving into white fog, mist torso and head still readable, not a blank tile, not a simple flame, not a droplet",
    "splash step": "wet footprints dashing sideways, water spray trail",
    "summon water elemental": "humanoid water elemental creature, flowing liquid torso",
    "tidal wave": "huge side-view cresting wave, white foam lip, cobalt body",
    "undertow": "downward sucking current, whirlpool pulling a silhouette under",
    "water bolt": "compact spinning water projectile, round splash core",
    "water jet": "thin high-pressure water stream, needle of cobalt",
    "water splash": "radial splash burst, droplets flying outward",
    "whirlpool blast": "exploding whirlpool, water rings bursting out",
    "riptide": "sideways ripping current, shear of water cutting across",
    "brine skin": "salt-crusted torso armor, crystalline brine plates",
    "hydromancy": "cresting cobalt wave hurled by a pale hand, white foam, not a green droplet",
    "bloodward": "crimson barrier of circulating blood, shield of veins",
    "capillary rupture": "bursting capillary spray, fine arterial mist",
    "circulatory lock": "closed arterial knot, locked vein loop",
    "contagious rupture": "blood splash jumping to a second silhouette",
    "heart implosion": "anatomical heart collapsing inward, crimson crush",
    "hypertensive field": "pressure aura around a pulsing heart, red rings",
    "organ crush": "squeezed organ burst, visceral crimson crush",
    "pressure spike": "sharp arterial spike, blood needle",
    "sanguine channel": "flowing blood stream between two points, siphon",
    "blood step": "bloody footprints, crimson dash trail",
    "pressure dump": "released blood pressure burst, exploding droplet",
    "sanguimancy": "pale hand squeezing a dripping anatomical heart, deep crimson",
    "falling star": "gold meteor streaking down a violet sky, not a staff",
    "gravity pin": "target pinned under a gravity well, concentric violet rings",
    "stellar ward": "star-etched barrier, gold rim on indigo shield",
    "astral step": "silhouette stepping through a star gate, afterimage",
    "meteorite slam": "bright burning meteor rock slamming cracked earth, orange fire core, visible stone, not empty, not a dark blob",
    "starfire lance": "long gold-violet spear of starfire, piercing shaft",
    "asteroid drop": "falling asteroid, crater impact below",
    "umbra well": "dark gravity well, black core with violet accretion",
    "meteor swarm": "three separate flaming meteors with gold trails, not one blob, not empty",
    "planet cracker": "a planet splitting in half with gold lava cracks, broken globe, not concentric circles",
    "starcaller pact": "mage hand clasping a bright eight-pointed gold star, pact, not blank",
    "cosmic blast": "starburst nova, gold core violet petals",
    "cosmic magic": "violet gravity well with a pale-gold meteor core, starfield",
    "acid dart": "flying acid needle, lime trail, not a heart",
    "etch": "acid eating a rune into dark metal, dripping lime",
    "alembic ward": "protective glass alembic shield, bubbling lime",
    "vitriol infusion": "lime liquid pouring into a wound, solvent soak",
    "acid pool": "floor puddle of bubbling acid, fumes up",
    "vitriol step": "footstep burning a lime hole in stone",
    "armor melt": "breastplate dripping into slag, lime corrosion",
    "neutralize": "two flasks mixing, fizz cancelling a glow",
    "volatile reaction": "exploding flask, lime burst shards",
    "fuming aura": "cloud of acid fumes around a figure, lime vapor",
    "fuming aura trigger": "fume cloud igniting, sudden lime flash",
    "total dissolution": "silhouette dissolving into lime sludge",
    "acid gag": "choking acid splash at a mouth, lime mist",
    "hemolysis": "blood cell bursting in acid, lime eating red",
    "acid magic": "tilted erlenmeyer flask pouring lime acid that eats metal",
}


def _distinct_motif(name: str) -> str:
    key = " ".join(str(name or "").lower().split())
    return _DISTINCT_MOTIF.get(key, "")


def _prompt(spec: Dict[str, Any], *, name: str, description: str, kind: str) -> str:
    theme = _theme(spec)
    role = _KIND_ROLE.get(kind, "skill icon")
    accent = _school_accent(theme, name, description)
    motif = _distinct_motif(name)
    blurb = _blurb(description) or name
    if motif:
        subject = f"for the {theme} school, symbol of {name}: {motif}. {blurb}, {accent}"
    else:
        subject = f"for the {theme} school, symbol of {name}: {blurb}, {accent}"
    # Keep school accents on ability/amp/passive tiles so the four magics share one Soulash look.
    if kind in ("skill", "icon"):
        subject = f"{subject}, bold school emblem for mod folder / skill tree"
    elif kind == "thumbnail":
        subject = (
            f"{subject}, Soulash 2 workshop banner painting, dark dungeon, "
            "a mage warping pale-cyan pressure into a cyclone, no text"
        )
    return compose_icon_prompt(role=role, subject=subject)


def _items_for_bucket(spec: Dict[str, Any], bucket: str) -> List[Dict[str, Any]]:
    if bucket == "skills":
        return [spec.setdefault("skill", {})]
    return [row for row in (spec.get(bucket) or []) if isinstance(row, dict)]


def _procedural_tile(seed: str, size: int = TILE) -> bytes:
    r, g, b = _rgb(seed)
    pix = bytearray(size * size * 4)
    for y in range(size):
        for x in range(size):
            i = (y * size + x) * 4
            edge = x < 2 or y < 2 or x >= size - 2 or y >= size - 2
            cx, cy = x - size / 2, y - size / 2
            ring = abs((cx * cx + cy * cy) ** 0.5 - size * 0.28) < 2.2
            if edge:
                pix[i : i + 4] = bytes((18, 18, 20, 255))
            elif ring:
                pix[i : i + 4] = bytes((min(255, r + 70), min(255, g + 70), min(255, b + 70), 255))
            else:
                pix[i : i + 4] = bytes((r, g, b, 255))
    return bytes(pix)


def _sd_tile(
    spec: Dict[str, Any],
    item: Dict[str, Any],
    *,
    kind: str,
    api_url: str,
    work: Path,
    steps: int,
    init_image=None,
    strength: float = 0.58,
    native: bool = False,
) -> bytes:
    kind = str(kind or "ability")
    name = str(item.get("name") or item.get("id") or kind)
    prompt = _prompt(spec, name=name, description=str(item.get("description") or ""), kind=kind)
    img = generate_sd_tile(
        prompt,
        work=work,
        api_url=api_url,
        seed=seed_from_name(name),
        steps=steps,
        size=SHEET_TILE if kind != "icon" else TILE,
        name=f"{kind}:{name}",
        init_image=init_image,
        strength=strength,
        native=native,
    )
    return img.tobytes()


def _sd_tile_retry(
    spec: Dict[str, Any],
    item: Dict[str, Any],
    *,
    kind: str,
    api_url: str,
    work: Path,
    steps: int,
    init_image=None,
    strength: float = 0.58,
    native: bool = False,
    sheet_name: str = "sheet",
    index: int = 0,
    total: int = 1,
    attempts: int = 4,
    retry_wait_sec: float = 20.0,
) -> bytes:
    """Generate one tile via SD; wait and retry on failure. Never stamps procedural rings."""
    import time

    name = str(item.get("name") or item.get("id") or kind)
    last_exc: Optional[BaseException] = None
    for attempt in range(1, max(1, attempts) + 1):
        try:
            extra = " img2img" if init_image is not None else ""
            suffix = f" (retry {attempt}/{attempts})" if attempt > 1 else ""
            print(
                f"[icons] SD{extra} {sheet_name} {index + 1}/{total} {name}{suffix}",
                flush=True,
            )
            return _sd_tile(
                spec,
                item,
                kind=kind,
                api_url=api_url,
                work=work,
                steps=steps,
                init_image=init_image,
                strength=strength,
                native=native,
            )
        except Exception as exc:
            last_exc = exc
            print(f"[icons] SD failed for {name}: {exc}", file=sys.stderr, flush=True)
            if attempt >= attempts:
                break
            print(
                f"[icons] waiting {retry_wait_sec:.0f}s before retry "
                f"(GPU lock / server recovery)...",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(retry_wait_sec)
    raise RuntimeError(
        f"SD failed for {name} after {attempts} attempts; refusing procedural fallback"
    ) from last_exc


def generate_spritesheets(
    spec: Dict[str, Any],
    dest: Optional[Path] = None,
    *,
    kinds: Optional[Iterable[str]] = None,
    use_sd: bool = True,
    overwrite: bool = True,
    include_icon: bool = True,
    include_thumbnail: bool = False,
    dry_run: bool = False,
    limit: Optional[int] = None,
    steps: int = 24,
    from_existing: bool = False,
    strength: float = 0.58,
    names: Optional[Iterable[str]] = None,
) -> List[str]:
    """Write packed tilesheets next to the spec. Returns relative paths written."""
    root = Path(dest) if dest else staging_dir(spec)
    root.mkdir(parents=True, exist_ok=True)
    assets = spec.get("assets") or default_assets()
    spec["assets"] = assets
    sheets = (assets.get("graphics") or {}).setdefault("tilesheets", [])
    wanted = {k.strip() for k in (kinds or ("skills", "abilities", "amplifiers", "passives", "stackers"))}
    written: List[str] = []
    jobs: List[Tuple[str, str, str, List[Dict[str, Any]]]] = []
    for bucket, sheet_name, kind in SHEET_JOBS:
        if bucket not in wanted and sheet_name not in wanted and kind not in wanted:
            continue
        items = _items_for_bucket(spec, bucket)
        if limit is not None:
            items = items[: int(limit)]
        jobs.append((bucket, sheet_name, kind, items))

    if dry_run:
        for bucket, sheet_name, kind, items in jobs:
            cols, rows = sheet_grid_for(sheet_name, len(items))
            print(f"[icons] {sheet_name}: {len(items)} tiles on {cols}x{rows} {SHEET_TILE}px grid")
            for item in items:
                print(
                    f"  - {item.get('id')}  "
                    f"{_prompt(spec, name=str(item.get('name') or item.get('id')), description=str(item.get('description') or ''), kind=kind)[:120]}"
                )
        return written

    with sd_session(use_sd=use_sd) as api_url:
        written.extend(
            _render_jobs(
                spec,
                root,
                jobs,
                sheets,
                api_url=api_url,
                use_sd=bool(api_url),
                overwrite=overwrite,
                steps=steps,
                from_existing=from_existing,
                strength=strength,
                names=names,
            )
        )
        if include_icon:
            written.extend(
                _write_mod_icon(
                    spec,
                    root,
                    api_url=api_url,
                    use_sd=bool(api_url),
                    overwrite=overwrite,
                    steps=steps,
                    from_existing=from_existing,
                    strength=strength,
                )
            )
        if include_thumbnail:
            written.extend(
                _write_thumbnail(
                    spec, root, api_url=api_url, use_sd=bool(api_url), overwrite=overwrite, steps=steps
                )
            )

    import json

    (root / "assets.json").write_text(json.dumps(assets, indent="\t") + "\n", encoding="utf-8")
    return written


def _ensure_sheet_row(sheets: List[Dict[str, Any]], name: str, cols: int, rows: int, rel: str) -> None:
    for sheet in sheets:
        if sheet.get("name") == name:
            sheet["tiles"] = [cols, rows]
            sheet["file"] = rel
            return
    sheets.append({"name": name, "tiles": [cols, rows], "file": rel})


def _name_match(item: Dict[str, Any], names: Optional[Iterable[str]]) -> bool:
    wanted = {str(n).strip().lower() for n in (names or ()) if str(n).strip()}
    if not wanted:
        return True
    return str(item.get("name") or "").strip().lower() in wanted


def _render_jobs(
    spec: Dict[str, Any],
    root: Path,
    jobs: List[Tuple[str, str, str, List[Dict[str, Any]]]],
    sheets: List[Dict[str, Any]],
    *,
    api_url: Optional[str],
    use_sd: bool,
    overwrite: bool,
    steps: int,
    from_existing: bool = False,
    strength: float = 0.58,
    names: Optional[Iterable[str]] = None,
) -> List[str]:
    written: List[str] = []
    work = root / "_sd_work"
    work.mkdir(exist_ok=True)
    for bucket, sheet_name, kind, items in jobs:
        cols, rows = sheet_grid_for(sheet_name, len(items) or 1)
        file_name = {
            "skills": "assets/skills.png",
            "abilities": "assets/abilities.png",
            "amplifiers": "assets/amplifiers.png",
            "passive_skills": "assets/passive_skills.png",
            "stackers": "assets/stackers.png",
        }.get(sheet_name, f"assets/{sheet_name}.png")
        path = root / file_name
        old_cols = None
        for sheet in sheets:
            if sheet.get("name") == sheet_name:
                old_cols = int((sheet.get("tiles") or [cols])[0] or cols)
                break
        existing: List = (
            unpack_bottom_left(path, cols=old_cols) if from_existing and path.is_file() else []
        )
        current: List = unpack_bottom_left(path, tile=SHEET_TILE) if path.is_file() else []
        tiles: List[bytes] = []
        # SD3.5 cannot paint a readable 32×32 natively; img2img at the 512
        # quality floor, then pack with fit_icon_tile like every other sheet.
        native = False
        for i, item in enumerate(items):
            seed = str(item.get("id") or item.get("name") or i)
            item["image"] = i
            if path.is_file() and not overwrite:
                continue
            if names and not _name_match(item, names):
                if i < len(current):
                    cell = current[i]
                    tiles.append(cell.tobytes() if hasattr(cell, "tobytes") else cell)
                else:
                    tiles.append(empty_tile_bytes(SHEET_TILE))
                continue
            init = existing[i] if i < len(existing) else None
            if use_sd:
                if not api_url:
                    raise RuntimeError(
                        "SD session has no API URL; refusing procedural icon tiles. "
                        "Pass --no-sd only for explicit placeholders."
                    )
                tiles.append(
                    _sd_tile_retry(
                        spec,
                        item,
                        kind=kind,
                        api_url=api_url,
                        work=work,
                        steps=steps,
                        init_image=init,
                        strength=strength,
                        native=native,
                        sheet_name=sheet_name,
                        index=i,
                        total=len(items),
                    )
                )
            else:
                tiles.append(_procedural_tile(seed, size=SHEET_TILE))
        if bucket == "skills" and items:
            spec.setdefault("skill", {})["image"] = 0
        if path.is_file() and not overwrite:
            print(f"[icons] skip existing {file_name}")
            continue
        if not tiles:
            if use_sd:
                raise RuntimeError(f"No tiles generated for {file_name}; refusing procedural fill")
            tiles.append(_procedural_tile(sheet_name, size=SHEET_TILE))
        empty = empty_tile_bytes(SHEET_TILE)
        while len(tiles) < cols * rows:
            tiles.append(empty)
        w, h, rgba = pack_bottom_left(tiles, cols, rows, tile=SHEET_TILE)
        write_png(path, w, h, rgba)
        _ensure_sheet_row(sheets, sheet_name, cols, rows, file_name.replace("\\", "/"))
        written.append(file_name)
        print(f"[icons] wrote {file_name} ({cols}x{rows} at {SHEET_TILE}px, index 0 = bottom left)")
    return written


def _write_mod_icon(
    spec: Dict[str, Any],
    root: Path,
    *,
    api_url: Optional[str],
    use_sd: bool,
    overwrite: bool,
    steps: int,
    from_existing: bool = False,
    strength: float = 0.58,
) -> List[str]:
    name = str((spec.get("mod") or {}).get("icon") or "icon.png")
    path = root / name
    if path.is_file() and not overwrite:
        return []
    skill = spec.get("skill") or {}
    item = {"id": spec.get("skill_id"), "name": skill.get("name"), "description": skill.get("description") or ""}
    init = None
    if from_existing and path.is_file():
        from PIL import Image

        init = Image.open(path).convert("RGBA")
    if use_sd:
        if not api_url:
            raise RuntimeError("SD session has no API URL; refusing procedural mod icon")
        from PIL import Image as _Image

        raw = _sd_tile_retry(
            spec,
            item,
            kind="skill",
            api_url=api_url,
            work=root / "_sd_work",
            steps=steps,
            init_image=init,
            strength=strength,
            native=False,
            sheet_name="icon",
            index=0,
            total=1,
        )
        big = _Image.frombytes("RGBA", (SHEET_TILE, SHEET_TILE), raw)
        small = fit_icon_tile(big, size=TILE)
        write_png(path, TILE, TILE, small.tobytes())
    else:
        write_icon_png(path, _rgb(_theme(spec)), overwrite=True)
    return [name]


def _write_thumbnail(
    spec: Dict[str, Any],
    root: Path,
    *,
    api_url: Optional[str],
    use_sd: bool,
    overwrite: bool,
    steps: int,
) -> List[str]:
    from s2_assets import write_thumbnail_png as _thumb

    name = str((spec.get("mod") or {}).get("thumbnail") or "thumbnail.png")
    spec.setdefault("mod", {})["thumbnail"] = name
    path = root / name
    if path.is_file() and not overwrite:
        return []
    if not use_sd:
        _thumb(path, _rgb(_theme(spec)), overwrite=True)
        return [name]
    if not api_url:
        raise RuntimeError("SD session has no API URL; refusing procedural thumbnail")
    from sd_http_client import generate_image, plan_sd_size
    from PIL import Image
    import time

    gw, gh, plan_steps = plan_sd_size(400, 300, kind="banner")
    raw_path = root / "_sd_work" / "thumbnail_raw.png"
    last_exc: Optional[BaseException] = None
    for attempt in range(1, 5):
        try:
            if attempt > 1:
                print(f"[icons] thumbnail retry {attempt}/4...", file=sys.stderr, flush=True)
                time.sleep(20.0)
            generate_image(
                _prompt(
                    spec,
                    name=_theme(spec),
                    description=str((spec.get("skill") or {}).get("description") or ""),
                    kind="thumbnail",
                ),
                raw_path,
                api_url=api_url,
                negative_prompt=NEGATIVE,
                width=gw,
                height=gh,
                steps=max(steps, plan_steps),
            )
            img = Image.open(raw_path).convert("RGBA")
            img = img.resize((400, 300), Image.Resampling.LANCZOS)
            img.save(path)
            return [name]
        except Exception as exc:
            last_exc = exc
            print(f"[icons] thumbnail SD failed: {exc}", file=sys.stderr, flush=True)
    raise RuntimeError(
        "SD thumbnail failed after retries; refusing procedural fallback (leave existing placeholder)"
    ) from last_exc


_SHEET_FILES = {
    "skills": ("skills", "assets/skills.png", "skill"),
    "abilities": ("abilities", "assets/abilities.png", "ability"),
    "amplifiers": ("amplifiers", "assets/amplifiers.png", "amplifier"),
    "passives": ("passive_skills", "assets/passive_skills.png", "passive"),
    "stackers": ("stackers", "assets/stackers.png", "stacker"),
}


def _normalize_sheet_key(raw: str) -> str:
    key = str(raw or "").strip().lower()
    aliases = {
        "skill": "skills",
        "ability": "abilities",
        "amplifier": "amplifiers",
        "amp": "amplifiers",
        "passive": "passives",
        "passive_skills": "passives",
        "stacker": "stackers",
    }
    key = aliases.get(key, key)
    if key not in _SHEET_FILES:
        raise ValueError(f"unknown sheet {raw!r}; use {sorted(_SHEET_FILES)}")
    return key


def inject_external_icons(
    spec: Dict[str, Any],
    injections: List[Dict[str, Any]],
    dest: Optional[Path] = None,
) -> List[str]:
    """Pack external PNG(s) into atlas cells via fit_icon_tile + bottom-left packer.

    Each injection needs ``png`` and either ``name`` or ``sheet``+``index``.
    Optional ``sheet`` disambiguates display names across buckets.
    """
    from PIL import Image

    root = Path(dest) if dest else staging_dir(spec)
    root.mkdir(parents=True, exist_ok=True)
    assets = spec.get("assets") or default_assets()
    spec["assets"] = assets
    sheets_meta = (assets.get("graphics") or {}).setdefault("tilesheets", [])
    written: List[str] = []
    resolved: List[Tuple[str, int, Path]] = []

    for inj in injections:
        png = Path(str(inj.get("png") or ""))
        if not png.is_file():
            raise FileNotFoundError(f"inject PNG missing: {png}")
        name = str(inj.get("name") or "").strip()
        sheet_hint = str(inj.get("sheet") or "").strip() or None
        index = inj.get("index")
        if index is not None and sheet_hint:
            resolved.append((_normalize_sheet_key(sheet_hint), int(index), png))
            continue
        if not name:
            raise ValueError("inject needs --name or --sheet + --index")
        want = _normalize_sheet_key(sheet_hint) if sheet_hint else None
        hits: List[Tuple[str, int]] = []
        skill = spec.get("skill") or {}
        if str(skill.get("name") or "").strip().lower() == name.lower():
            if want in (None, "skills"):
                hits.append(("skills", 0))
        for bucket, key in (
            ("abilities", "abilities"),
            ("amplifiers", "amplifiers"),
            ("passives", "passives"),
            ("stackers", "stackers"),
        ):
            if want is not None and key != want:
                continue
            for i, row in enumerate(spec.get(bucket) or []):
                if str(row.get("name") or "").strip().lower() == name.lower():
                    hits.append((key, i))
        if not hits:
            raise ValueError(f"no icon target named {name!r}")
        if len(hits) > 1:
            raise ValueError(f"ambiguous name {name!r}: {hits}; pass --sheet")
        key, idx = hits[0]
        resolved.append((key, idx, png))
        if key == "skills":
            spec.setdefault("skill", {})["image"] = idx
        else:
            rows = spec.get(key) or []
            if 0 <= idx < len(rows):
                rows[idx]["image"] = idx

    by_sheet: Dict[str, List[Tuple[int, Path]]] = {}
    for key, idx, png in resolved:
        by_sheet.setdefault(key, []).append((idx, png))

    for key, jobs in by_sheet.items():
        sheet_name, rel, _kind = _SHEET_FILES[key]
        if key == "skills":
            items = [spec.get("skill") or {}]
        else:
            items = [r for r in (spec.get(key) or []) if isinstance(r, dict)]
        cols, rows = sheet_grid_for(sheet_name, max(len(items), 1))
        path = root / rel
        current = unpack_bottom_left(path, tile=SHEET_TILE) if path.is_file() else []
        total = cols * rows
        tiles: List[bytes] = []
        for i in range(total):
            if i < len(current):
                cell = current[i]
                tiles.append(cell.tobytes() if hasattr(cell, "tobytes") else cell)
            else:
                tiles.append(empty_tile_bytes(SHEET_TILE))
        for idx, png in jobs:
            if idx < 0 or idx >= total:
                raise IndexError(f"{key} index {idx} out of range for {cols}x{rows}")
            fitted = fit_icon_tile(Image.open(png).convert("RGBA"), size=SHEET_TILE)
            tiles[idx] = fitted.tobytes()
            print(f"[inject] {rel} index {idx} <- {png}")
        w, h, rgba = pack_bottom_left(tiles, cols, rows, tile=SHEET_TILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        write_png(path, w, h, rgba)
        _ensure_sheet_row(sheets_meta, sheet_name, cols, rows, rel.replace("\\", "/"))
        written.append(rel)
        print(f"[inject] wrote {rel} ({cols}x{rows} at {SHEET_TILE}px)")

    import json

    (root / "assets.json").write_text(json.dumps(assets, indent="\t") + "\n", encoding="utf-8")
    return written
