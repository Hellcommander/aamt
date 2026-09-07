#!/usr/bin/env python3
"""
Atlas of Qud -> Art helper

Scans Automap/tiles PNGs from CoQ saves (Atlas of Qud workshop mod),
optionally stitches a parasang (3x3), builds img2img prompts, and can
call Ollama for a layout caption.

Atlas tile size (mod): 1280×600 per local zone.
Zone ID: World.ParasangX.ParasangY.ZoneX.ZoneY.Z
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from PIL import Image
except ImportError as e:
    raise SystemExit("Pillow required: pip install Pillow") from e


DEFAULT_USERDATA = (
    Path.home() / "AppData" / "LocalLow" / "Freehold Games" / "CavesOfQud"
)
ATLAS_W, ATLAS_H = 1280, 600
ZONE_ID_RE = re.compile(
    r"^(?P<world>[^.]+)\.(?P<px>\d+)\.(?P<py>\d+)\.(?P<zx>\d+)\.(?P<zy>\d+)\.(?P<z>-?\d+)$"
)

STYLE_PRESETS = {
    "cartography": {
        "strength": 0.42,
        "label": "Painted atlas plate — keep roads/rooms, remove pixel tiles",
    },
    "landscape": {
        "strength": 0.60,
        "label": "Illustrated overhead landscape — same geography, not tile art",
    },
    "dream": {
        "strength": 0.78,
        "label": "Dreamlike science-fantasy vista loosely based on the map",
    },
}

NEGATIVE_DEFAULT = (
    "pixel art, 16x16 tiles, RPG maker, mosaic grid, UI chrome, watermark, "
    "text overlay, blurry, lowres, duplicate terrain stamps"
)


@dataclass
class ZoneCoord:
    world: str
    parasang_x: int
    parasang_y: int
    zone_x: int
    zone_y: int
    z: int

    @property
    def zone_id(self) -> str:
        return f"{self.world}.{self.parasang_x}.{self.parasang_y}.{self.zone_x}.{self.zone_y}.{self.z}"

    @property
    def parasang_key(self) -> str:
        return f"{self.world}.{self.parasang_x}.{self.parasang_y}.{self.z}"

    @classmethod
    def parse(cls, zone_id: str) -> Optional["ZoneCoord"]:
        m = ZONE_ID_RE.match(zone_id.strip())
        if not m:
            return None
        return cls(
            world=m.group("world"),
            parasang_x=int(m.group("px")),
            parasang_y=int(m.group("py")),
            zone_x=int(m.group("zx")),
            zone_y=int(m.group("zy")),
            z=int(m.group("z")),
        )


@dataclass
class AtlasTile:
    path: str
    zone_id: str
    coord: Optional[Dict[str, Any]] = None
    bytes: int = 0
    mtime: float = 0.0


@dataclass
class SaveAtlas:
    save_id: str
    save_name: str
    save_path: str
    tiles_dir: str
    tile_count: int
    tiles: List[AtlasTile] = field(default_factory=list)


def userdata_root(root: Optional[Path] = None) -> Path:
    return Path(root) if root else DEFAULT_USERDATA


def save_roots(root: Optional[Path] = None) -> List[Path]:
    base = userdata_root(root)
    return [base / "Synced" / "Saves", base / "Saves", base / "Local" / "Saves"]


def _load_save_name(save_dir: Path) -> str:
    primary = save_dir / "Primary.json"
    if not primary.is_file():
        return save_dir.name
    try:
        data = json.loads(primary.read_text(encoding="utf-8", errors="replace"))
        name = data.get("Name") or save_dir.name
        name = re.sub(r"\{\{[^{}|]*\|([^{}]*)\}\}", r"\1", str(name))
        name = re.sub(r"\{\{|\}\}", "", name)
        name = re.sub(r"[&^][A-Za-z0-9]", "", name)
        return name.strip() or save_dir.name
    except (OSError, json.JSONDecodeError):
        return save_dir.name


def find_automap_dirs(root: Optional[Path] = None) -> List[Path]:
    """Find Automap/tiles directories under saves and loose cache paths."""
    found: List[Path] = []
    seen = set()
    for sr in save_roots(root):
        if not sr.is_dir():
            continue
        for child in sr.iterdir():
            if not child.is_dir():
                continue
            tiles = child / "Automap" / "tiles"
            if tiles.is_dir():
                key = str(tiles.resolve()).lower()
                if key not in seen:
                    seen.add(key)
                    found.append(tiles)
    # Loose cache sometimes used by GetCacheDirectory
    base = userdata_root(root)
    for extra in (base / "Automap" / "tiles", base / "Cache" / "Automap" / "tiles"):
        if extra.is_dir():
            key = str(extra.resolve()).lower()
            if key not in seen:
                seen.add(key)
                found.append(extra)
    return found


def list_tiles_in_dir(tiles_dir: Path) -> List[AtlasTile]:
    out: List[AtlasTile] = []
    if not tiles_dir.is_dir():
        return out
    for png in sorted(tiles_dir.glob("*.png")):
        zone_id = png.stem
        coord = ZoneCoord.parse(zone_id)
        st = png.stat()
        out.append(
            AtlasTile(
                path=str(png),
                zone_id=zone_id,
                coord=asdict(coord) if coord else None,
                bytes=st.st_size,
                mtime=st.st_mtime,
            )
        )
    return out


def discover_atlases(root: Optional[Path] = None, include_tiles: bool = True) -> List[SaveAtlas]:
    atlases: List[SaveAtlas] = []
    for tiles_dir in find_automap_dirs(root):
        save_dir = tiles_dir.parent.parent  # .../SaveId/Automap/tiles
        if save_dir.name.lower() == "automap":
            save_dir = tiles_dir.parent
        tiles = list_tiles_in_dir(tiles_dir) if include_tiles else []
        if not include_tiles:
            # cheap count
            count = len(list(tiles_dir.glob("*.png")))
        else:
            count = len(tiles)
        atlases.append(
            SaveAtlas(
                save_id=save_dir.name,
                save_name=_load_save_name(save_dir) if (save_dir / "Primary.json").is_file() else save_dir.name,
                save_path=str(save_dir),
                tiles_dir=str(tiles_dir),
                tile_count=count,
                tiles=tiles if include_tiles else [],
            )
        )
    atlases.sort(key=lambda a: a.tile_count, reverse=True)
    return atlases


def stitch_parasang(
    tiles_dir: Path,
    world: str,
    parasang_x: int,
    parasang_y: int,
    z: int,
    out_path: Path,
) -> Path:
    """Stitch local zones 0..2 × 0..2 into one parasang plate (3840×1800)."""
    canvas = Image.new("RGBA", (ATLAS_W * 3, ATLAS_H * 3), (15, 59, 58, 255))
    missing = 0
    for zy in range(3):
        for zx in range(3):
            zone_id = f"{world}.{parasang_x}.{parasang_y}.{zx}.{zy}.{z}"
            src = tiles_dir / f"{zone_id}.png"
            x = zx * ATLAS_W
            y = zy * ATLAS_H
            if src.is_file():
                im = Image.open(src).convert("RGBA")
                if im.size != (ATLAS_W, ATLAS_H):
                    im = im.resize((ATLAS_W, ATLAS_H), Image.Resampling.NEAREST)
                canvas.paste(im, (x, y))
            else:
                missing += 1
                # dim placeholder
                ph = Image.new("RGBA", (ATLAS_W, ATLAS_H), (20, 40, 40, 255))
                canvas.paste(ph, (x, y))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, "PNG")
    return out_path


def default_prompt(zone_id: str, style: str, caption: str = "") -> str:
    preset = STYLE_PRESETS.get(style, STYLE_PRESETS["landscape"])
    bits = [
        "Caves of Qud overhead science-fantasy landscape illustration",
        preset["label"],
        "based on an in-game automap of zone " + zone_id,
        "readable terrain: salt desert, rust wells, ruins, jungle, water, roads, settlements when present",
        "painterly detailed, cohesive lighting, not a screenshot, not pixel tiles, not UI",
    ]
    if caption:
        bits.append("Layout notes: " + caption.strip())
    return ". ".join(bits) + "."


def ollama_caption(
    image_path: Path,
    ollama_url: str = "http://localhost:11434",
    model: str = "",
) -> str:
    """Ask a vision-capable Ollama model to describe map layout. Falls back to text-only if needed."""
    image_path = Path(image_path)
    if not image_path.is_file():
        return ""

    # Prefer a vision model if present
    tags = _ollama_tags(ollama_url)
    if not model:
        for cand in ("llava", "llava:latest", "llama3.2-vision", "minicpm-v", "bakllava"):
            if any(cand.split(":")[0] in t for t in tags):
                # pick exact tag if available
                model = next((t for t in tags if t.startswith(cand.split(":")[0])), cand)
                break
        if not model:
            model = tags[0] if tags else "llama3.2"

    import base64

    b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    prompt = (
        "You are describing a Caves of Qud automap (overhead tile mosaic) for an artist. "
        "List concrete layout features: terrain types, water, roads, ruins, buildings, "
        "walls, open courtyards, vegetation, and fog/unexplored holes. "
        "Be concise (80-120 words). No pixel-art instructions."
    )
    body = {
        "model": model,
        "prompt": prompt,
        "images": [b64],
        "stream": False,
    }
    try:
        data = _http_json(f"{ollama_url.rstrip('/')}/api/generate", body, timeout=180)
        return (data.get("response") or "").strip()
    except Exception as e:
        # Text-only fallback
        try:
            body2 = {
                "model": model.split(":")[0] if "llava" in model or "vision" in model else model,
                "prompt": (
                    "Write a short overhead landscape description for a Caves of Qud zone "
                    f"named {image_path.stem}: salt, rust, ruins, possible water or village. "
                    "80 words max."
                ),
                "stream": False,
            }
            data = _http_json(f"{ollama_url.rstrip('/')}/api/generate", body2, timeout=120)
            return (data.get("response") or "").strip()
        except Exception:
            return f"(Ollama caption failed: {e})"


def _ollama_tags(ollama_url: str) -> List[str]:
    try:
        data = _http_json(f"{ollama_url.rstrip('/')}/api/tags", None, method="GET", timeout=10)
        return [m.get("name", "") for m in data.get("models") or [] if m.get("name")]
    except Exception:
        return []


def _http_json(url: str, body: Optional[dict], method: str = "POST", timeout: int = 60) -> dict:
    if method == "GET":
        req = urllib.request.Request(url, method="GET")
    else:
        raw = json.dumps(body or {}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=raw,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def build_job(
    image_path: Path,
    *,
    style: str = "landscape",
    caption: str = "",
    use_ollama: bool = False,
    ollama_url: str = "http://localhost:11434",
    out_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    image_path = Path(image_path)
    zone_id = image_path.stem
    if use_ollama and not caption:
        caption = ollama_caption(image_path, ollama_url=ollama_url)
    preset = STYLE_PRESETS.get(style, STYLE_PRESETS["landscape"])
    prompt = default_prompt(zone_id, style, caption)
    out_dir = Path(out_dir) if out_dir else image_path.parent / "_atlas_art"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_png = out_dir / f"{zone_id}.{style}.png"
    return {
        "sourceImage": str(image_path),
        "zoneId": zone_id,
        "style": style,
        "strength": preset["strength"],
        "prompt": prompt,
        "negativePrompt": NEGATIVE_DEFAULT,
        "caption": caption,
        "outputImage": str(out_png),
        "width": 1280,
        "height": 640,
        "notes": [
            "Feed sourceImage to SD img2img as ReferenceImagePath",
            "ImageStrength / denoising_strength = strength",
            "Atlas native size is 1280x600; generation uses 1280x640",
        ],
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Atlas of Qud automap -> art job builder")
    p.add_argument("--userdata", type=Path, default=None)
    sub = p.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List saves with Automap/tiles")
    p_list.add_argument("--json", action="store_true")
    p_list.add_argument("--tiles", action="store_true", help="Include every tile path")

    p_prep = sub.add_parser("prepare", help="Build an img2img job JSON for one PNG or parasang")
    p_prep.add_argument("path", type=Path, help="Atlas PNG, or Automap/tiles dir with --parasang")
    p_prep.add_argument("--style", choices=list(STYLE_PRESETS), default="landscape")
    p_prep.add_argument("--ollama", action="store_true")
    p_prep.add_argument("--ollama-url", default="http://localhost:11434")
    p_prep.add_argument("--caption", default="")
    p_prep.add_argument("-o", "--output", type=Path, default=None, help="Job JSON path")
    p_prep.add_argument("--out-dir", type=Path, default=None, help="Art output directory")
    p_prep.add_argument(
        "--parasang",
        default="",
        help="With tiles dir: World.PX.PY.Z (stitches 3x3 local zones)",
    )

    args = p.parse_args(argv)

    if args.cmd == "list":
        atlases = discover_atlases(args.userdata, include_tiles=bool(args.tiles))
        payload = [asdict(a) for a in atlases]
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            if not payload:
                print("No Automap/tiles folders found.")
                print("Play with Atlas of Qud (Ctrl+M) so zones are captured under:")
                print("  <Save>/Automap/tiles/*.png")
            for a in atlases:
                print(f"[{a.tile_count:4d} tiles] {a.save_name}  ::  {a.tiles_dir}")
                if args.tiles:
                    for t in a.tiles[:30]:
                        print(f"    {t.zone_id}")
                    if len(a.tiles) > 30:
                        print(f"    ... +{len(a.tiles) - 30} more")
        return 0

    if args.cmd == "prepare":
        path = Path(args.path)
        work = path
        if args.parasang:
            if not path.is_dir():
                raise SystemExit("--parasang requires a tiles directory")
            parts = args.parasang.split(".")
            if len(parts) != 4:
                raise SystemExit("--parasang format: World.ParasangX.ParasangY.Z")
            world, px, py, z = parts[0], int(parts[1]), int(parts[2]), int(parts[3])
            out_dir = args.out_dir or (path.parent / "_atlas_art")
            stitch_path = Path(out_dir) / f"{world}.{px}.{py}.parasang.{z}.png"
            work = stitch_parasang(path, world, px, py, z, stitch_path)
        elif path.is_dir():
            raise SystemExit("Pass a .png tile, or a tiles dir with --parasang World.PX.PY.Z")

        job = build_job(
            work,
            style=args.style,
            caption=args.caption,
            use_ollama=bool(args.ollama),
            ollama_url=args.ollama_url,
            out_dir=args.out_dir,
        )
        text = json.dumps(job, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
            print(str(args.output))
        else:
            print(text)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
