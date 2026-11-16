#!/usr/bin/env python3
"""Elin creature paperdolls: one game tile -> true south/west/east/north faces -> animation sheets.

Elin draws monsters, summons and most townsfolk as ONE static tile (a three-quarter view facing left). Its
paperdoll actor wants a 4x4 walk sheet: rows front (S), left (W), right (E), back (N), four frames each. This
pipeline makes that sheet, and a second sheet with attack and casting parts, for every creature tile of the game:

  tiles    (in game)  CustomRaceClassCreator `CreaturePaperdolls.ExportTiles(dir)` writes tile_*.png + manifest.json
  concept  PIL        the figure cut out, enlarged with a pixel-art scaler (Scale2x) and centred on a 1024 canvas
  mesh     TRELLIS    concept -> textured body (Shared/trellis_http_client; real volume, a real back)
  views    Blender    blender_creature_views.py finds where the body is heading (its mirror plane) and renders the
                      S, W, E and N faces plus T, the view the tile was drawn from, with one shared framing
  sprites  PIL        each face scaled so T matches the tile's figure, snapped to the tile's own colours, outlined
                      in the tile's outline colour, feet on the tile's ground line
  sheet    PIL        pcc_body_KEY.png  4x4 walk sheet (the game's paperdoll format)
                      anim_KEY.png/.json  extra parts per direction: attack (4 frames), cast (4 frames), hit (2)
  deploy              walk sheets -> <mod>/Actor/PCC/crcc/, extra parts -> <mod>/Paperdolls/Anim/

The mod (CreaturePaperdolls.cs) uses a deployed sheet when there is one for a tile and its run-time sheet (made from
the tile alone, so without true faces) when there is not, so the batch can run for days and be stopped at any point.

  python elin_creature_paperdolls.py status
  python elin_creature_paperdolls.py run --id dragon,skeleton_warrior          # every stage, cached
  python elin_creature_paperdolls.py run --all --limit 40 --keep               # batch, TRELLIS kept between jobs
  python elin_creature_paperdolls.py run --id dragon --from sprites            # redo from a stage on
  python elin_creature_paperdolls.py run --id dragon --heading 40              # override the estimated heading
  python elin_creature_paperdolls.py preview --id dragon                       # contact sheet to look at
  python elin_creature_paperdolls.py motion --id silverwolf                    # REAL motion for a full body: UniRig +
                                                                               # Wan video + CoTracker fit (15-20 min)
  python elin_creature_paperdolls.py full --motion --id harpy                  # body and motion in one go
  python elin_creature_paperdolls.py full --id grizzlyBear,silverwolf          # REAL bodies: Kontext redraw + TRELLIS,
                                                                               # about 20 minutes per creature

Work folders: Tools/Elin/Output/CreaturePaperdolls/work/<tile>/ (concept.png, mesh.glb, views/, faces/, sheets).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

_ELIN = Path(__file__).resolve().parent
_TOOLS = _ELIN.parent
_SHARED = _TOOLS / "Shared"
for _p in (_ELIN, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

OUT = _ELIN / "Output" / "CreaturePaperdolls"
TILES = OUT / "tiles"
WORK = OUT / "work"
BLENDER_WORKER = _ELIN / "blender_creature_views.py"
DEFAULT_MOD = Path(r"E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator")
STAGES = ["concept", "mesh", "views", "sprites", "sheet", "deploy"]
DIRS = ["S", "W", "E", "N"]          # row order of the game's paperdoll sheet, top to bottom
CLIPS = {"attack": {"frames": 4, "fps": 14}, "cast": {"frames": 4, "fps": 10}, "hit": {"frames": 2, "fps": 12}}


# --------------------------------------------------------------------------------------------- one GPU user at a time

try:
    from gpu_hub import acquire_gpu
except Exception:      # the hub is part of the toolkit; without it there is nothing to serialise against
    import contextlib

    def acquire_gpu(label, timeout=None, poll=2.0, enabled=True):  # type: ignore
        return contextlib.nullcontext()

GAMES = ("Elin.exe",)   # GPU users the toolkit's guard cannot see


def game_running() -> Optional[str]:
    for exe in GAMES:
        try:
            out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {exe}", "/NH"], capture_output=True, text=True, timeout=30).stdout
        except Exception:
            return None
        if exe.lower() in out.lower():
            return exe
    return None


def wait_for_free_gpu(what: str) -> None:
    """The rule on this PC is one CUDA job at a time, and the toolkit's guard (acquire_gpu) enforces it. A game is
    not a CUDA job and may run beside a batch. Set AAMT_GPU_WAIT_FOR_GAMES=1 to also hold a GPU stage back while a
    game is running (slower machines, or when chasing a crash)."""
    if os.environ.get("AAMT_GPU_WAIT_FOR_GAMES", "") not in ("1", "true", "yes"):
        return
    told = False
    while True:
        exe = game_running()
        if exe is None:
            return
        if not told:
            print(f"[gpu] {exe} is running; waiting for it to close before {what}", flush=True)
            told = True
        time.sleep(10)


# --------------------------------------------------------------------------------------------- manifest

def mod_dir() -> Path:
    raw = os.environ.get("AAMT_ELIN_CRCC_MOD")
    return Path(raw) if raw else DEFAULT_MOD


def load_manifest() -> List[Dict[str, Any]]:
    path = TILES / "manifest.json"
    if not path.is_file():
        raise SystemExit(f"{path} missing: run CreaturePaperdolls.ExportTiles in game first (see the docstring)")
    return json.loads(path.read_text(encoding="utf-8"))


def tile_name(entry: Dict[str, Any]) -> str:
    return Path(entry["tile"]).stem[len("tile_"):]


def work_dir(tile: str) -> Path:
    return WORK / tile


# --------------------------------------------------------------------------------------------- pixels

def rgba(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGBA"))


def bbox(a: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
    """left, top, right, bottom (inclusive) of the opaque pixels, image rows top first."""
    ys, xs = np.nonzero(a[:, :, 3] > 0)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def scale2x(a: np.ndarray) -> np.ndarray:
    """EPX / Scale2x: doubles pixel art without blurring and rounds stair-stepped edges."""
    key = (a[:, :, 0].astype(np.uint32) << 24) | (a[:, :, 1].astype(np.uint32) << 16) | (a[:, :, 2].astype(np.uint32) << 8) | a[:, :, 3]
    p = np.pad(key, 1, mode="edge")
    A, B, C, D = p[:-2, 1:-1], p[1:-1, 2:], p[1:-1, :-2], p[2:, 1:-1]   # up, right, left, down
    h, w = key.shape
    out = np.repeat(np.repeat(a, 2, axis=0), 2, axis=1).copy()
    src = np.pad(a, ((1, 1), (1, 1), (0, 0)), mode="edge")
    up, right, left, down = src[:-2, 1:-1], src[1:-1, 2:], src[1:-1, :-2], src[2:, 1:-1]
    ok = (C != B) & (A != D)
    m1 = ok & (C == A); m2 = ok & (A == B); m3 = ok & (D == C); m4 = ok & (B == D)
    out[0::2, 0::2][m1] = up[m1]
    out[0::2, 1::2][m2] = right[m2]
    out[1::2, 0::2][m3] = left[m3]
    out[1::2, 1::2][m4] = right[m4]
    return out


def resize_area(a: np.ndarray, w: int, h: int) -> np.ndarray:
    """Area resize with premultiplied alpha (no dark fringes)."""
    f = a.astype(np.float32) / 255.0
    f[:, :, :3] *= f[:, :, 3:4]
    im = Image.fromarray((f * 255).astype(np.uint8), "RGBA").resize((max(1, w), max(1, h)), Image.BOX)
    g = np.asarray(im).astype(np.float32) / 255.0
    al = np.maximum(g[:, :, 3:4], 1e-4)
    g[:, :, :3] = np.clip(g[:, :, :3] / al, 0, 1)
    return (g * 255).astype(np.uint8)


# --------------------------------------------------------------------------------------------- stages

def stage_concept(tile: str) -> Path:
    """The figure on a 1024 canvas, about 760 px on its long side, transparent around it."""
    dst = work_dir(tile) / "concept.png"
    a = rgba(TILES / f"tile_{tile}.png")
    box = bbox(a)
    if box is None:
        raise RuntimeError("empty tile")
    l, t, r, b = box
    fig = a[t:b + 1, l:r + 1]
    while max(fig.shape[:2]) < 380:
        fig = scale2x(fig)
    k = 760 / max(fig.shape[:2])
    im = Image.fromarray(fig, "RGBA").resize((max(1, round(fig.shape[1] * k)), max(1, round(fig.shape[0] * k))), Image.LANCZOS)
    # a hard alpha edge: soft edges become a halo in the mesh texture
    arr = np.asarray(im).copy()
    arr[:, :, 3] = np.where(arr[:, :, 3] >= 128, 255, 0)
    canvas = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    im = Image.fromarray(arr, "RGBA")
    canvas.paste(im, ((1024 - im.width) // 2, (1024 - im.height) // 2), im)
    dst.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dst)
    return dst


def stage_mesh(tile: str, seed: int = 1234, mesher: str = "fast") -> Path:
    """fast: Stable Fast 3D (seconds; always gives a body, a shallow one). trellis: TRELLIS (a minute; better
    volume and backs for shaded concepts, but it turns a pixel-art tile into a flat card)."""
    dst = work_dir(tile) / "mesh.glb"
    wait_for_free_gpu("meshing")
    if mesher == "trellis":
        from trellis_http_client import generate_mesh
        generate_mesh(work_dir(tile) / "concept.png", dst, resolution=512, steps=12, seed=seed, mesh_simplify=40,
                      texture_size=1024, autostart=True)
    else:
        from sf3d_client import generate_fast_mesh
        generate_fast_mesh(work_dir(tile) / "concept.png", dst, bake_res=1024)
    return dst


def stage_full_body(tile: str, entries: List[Dict[str, Any]], steps: int = 16, seed: int = 7) -> Path:
    """A real body instead of a relief: the tile is redrawn as a shaded 3D figure (FLUX Kontext, refart `edit`),
    and TRELLIS builds the body from that picture. A pixel tile, even lit, gives TRELLIS a flat card; a shaded
    figure gives it a body about half as deep as it is long, with true flanks and a true back.

    About 20 minutes per creature on the 11 GB card (Kontext 15-18, TRELLIS 3). Writes concept3d.png,
    concept3d_cut.png, mesh.glb (the fast mesh is kept as mesh_fast.glb) and full_body.txt, which makes the views
    stage find the front itself, measure the heading from the body's mirror plane, light the faces and use true
    side views. Look at work/<tile>/preview.png afterwards: if the faces are turned (a rear where the front should
    be), put {"<id>": {"tile_yaw": DEG}} in elin_creature_headings.json, DEG read off work/<tile>/probe/."""
    import refart_client
    from trellis_http_client import generate_mesh
    w = work_dir(tile)
    if not done(tile, "concept"):
        stage_concept(tile)
    names = [e for e in entries if tile_name(e) == tile]
    what = str(names[0].get("name") or names[0]["id"]) if names else "creature"
    white = w / "concept_white.png"
    im = Image.open(w / "concept.png").convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.paste(im, (0, 0), im)
    bg.convert("RGB").save(white)
    c3 = w / "concept3d.png"
    if not c3.is_file():
        refart_client.run("edit", image=white, out=c3, steps=steps, seed=seed, instruction=(
            f"Turn this pixel art sprite of a {what} into a smooth 3D rendered game creature model with real volume, "
            "rounded body and limbs, soft studio lighting and shading. Keep the same creature, the same pose, the same "
            "colors and the same equipment. Full body, plain white background."))
    cut_concept(c3, w / "concept3d_cut.png")
    full = w / "mesh_full.glb"
    if not full.is_file():
        generate_mesh(w / "concept3d_cut.png", full, resolution=512, steps=12, seed=1234, mesh_simplify=40,
                      texture_size=1024, autostart=True)
    if (w / "mesh.glb").is_file() and not (w / "mesh_fast.glb").is_file():
        shutil.copyfile(w / "mesh.glb", w / "mesh_fast.glb")
    shutil.copyfile(full, w / "mesh.glb")
    (w / "full_body.txt").write_text("kontext + trellis\n", encoding="utf-8")
    return w / "mesh.glb"


def mesh_batch(tiles: List[str]) -> int:
    """Concepts and fast meshes for many tiles with one model load. Returns how many meshes were made."""
    from sf3d_client import generate_fast_meshes
    todo = []
    for t in tiles:
        try:
            if not done(t, "concept"):
                stage_concept(t)
            if not done(t, "mesh"):
                todo.append(t)
        except Exception as exc:
            work_dir(t).mkdir(parents=True, exist_ok=True)
            (work_dir(t) / "error.txt").write_text(f"concept: {exc}", encoding="utf-8")
    made = 0
    for i in range(0, len(todo), 60):
        chunk = todo[i:i + 60]
        wait_for_free_gpu("meshing")
        res = generate_fast_meshes([(work_dir(t) / "concept.png", work_dir(t) / "mesh.glb") for t in chunk], bake_res=1024)
        for t, r in zip(chunk, res):
            if r.get("ok"):
                made += 1
            else:
                (work_dir(t) / "error.txt").write_text(f"mesh: {r.get('error')}", encoding="utf-8")
        print(f"[mesh] {min(i + 60, len(todo))}/{len(todo)}", flush=True)
    return made


def find_blender() -> Path:
    try:
        import mesh_edit
        return Path(mesh_edit.BLENDER)
    except Exception:
        found: List[Path] = []
        for root in (r"D:/tools/Blender Foundation", r"C:/Program Files/Blender Foundation"):
            if Path(root).exists():
                found += list(Path(root).glob("*/blender.exe"))
        if not found:
            raise RuntimeError("blender.exe not found (set AAMT_BLENDER)")
        return max(found, key=lambda p: p.stat().st_mtime)


MIN_DEPTH = 0.12      # thinnest side / longest side below this: the mesh is a flat card, not a body
BODY_DEPTH = 0.26     # single-image meshes are shallow reliefs; bodies are stretched to at least this deep
ROUND_DEPTH = 0.75    # ... and round bodies (slimes, eyes, spirits) to this
MAX_TURN = 55.0       # fast meshes are reliefs: no face looks at one from more than this off its front or back
                      # (edge-on it is a striped slab); full bodies (TRELLIS on a shaded concept) use 90
TILE_YAW_PRIOR = 180.0  # where Stable Fast 3D and TRELLIS put the picture's camera; kept unless another yaw fits clearly better
HEADING_FILE = _ELIN / "elin_creature_headings.json"
# Body plans drawn facing the viewer whatever their outline says.
FRONTAL_RACES = {"slime", "putty", "eye", "ghost", "spirit", "wisp", "mushroom", "plant", "tree", "bell", "yeek", "imp"}


def tile_heading(tile: str, entries: List[Dict[str, Any]]) -> Tuple[float, str]:
    """Where the creature of a tile is heading, in degrees counter-clockwise from the tile's camera: 0 = toward the
    viewer, 270 = to the left of the tile (a side view), 315 = the usual three-quarter view.

    Elin's artists draw upright creatures facing the viewer (turned a little to the left) and long creatures from the
    side, heads to the left. A single-image mesh is a relief in the picture's plane, so its shape cannot tell the two
    apart; the outline of the tile can. elin_creature_headings.json overrides this per creature id or tile name."""
    ids = [e["id"] for e in entries if tile_name(e) == tile]
    if HEADING_FILE.is_file():
        table = json.loads(HEADING_FILE.read_text(encoding="utf-8"))
        for k in [tile] + ids:
            if k in table and not isinstance(table[k], dict):
                return float(table[k]) % 360.0, "override"
            if k in table and "heading" in table[k]:
                return float(table[k]["heading"]) % 360.0, "override"
    races = {str(e.get("race") or "").lower() for e in entries if tile_name(e) == tile}
    if races & FRONTAL_RACES:
        return 350.0, "frontal race"
    a = rgba(TILES / f"tile_{tile}.png")
    l, t, r, b = bbox(a)
    aspect = (r - l + 1) / max(1, b - t + 1)
    side = min(1.0, max(0.0, (aspect - 0.8) / 0.5))     # 0 = upright, 1 = long
    return (350.0 - 80.0 * side) % 360.0, f"outline {aspect:.2f}"


def _blender(tile: str, out: Path, extra: List[str], size: int, want: str, model: Optional[Path] = None) -> None:
    w = work_dir(tile)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    blender = os.environ.get("AAMT_BLENDER") or str(find_blender())
    cmd = [blender, "-b", "--factory-startup", "-P", str(BLENDER_WORKER), "--", "--model", str(model or w / "mesh.glb"),
           "--out", str(out), "--size", str(size)] + extra
    env = dict(os.environ)
    for _k in [k for k in env if k.lower() == "nodefaultcurrentdirectoryinexepath"]:
        env.pop(_k)   # os.environ keys are upper-case on Windows; a pop by the mixed-case name misses
    wait_for_free_gpu("rendering")
    with acquire_gpu(f"Blender creature views {tile}"):
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=900, env=env)
    (w / f"blender_{out.name}.log").write_text((run.stdout or "") + "\n" + (run.stderr or ""), encoding="utf-8", errors="replace")
    if run.returncode != 0 or not (out / want).is_file():
        tail = "\n".join(((run.stdout or "") + (run.stderr or "")).splitlines()[-12:])
        raise RuntimeError(f"Blender failed ({run.returncode}):\n{tail}")


def cut_concept(src: Path, dst: Path) -> Path:
    """A redrawn concept (plain white backdrop, usually a soft ground shadow) as an RGBA cut-out of the body alone.
    The toolkit's cut-out floods the white away; the shadow is what is left that is light and colourless. It is
    dropped unless that would take a real part of the figure (a pale grey creature)."""
    from sf3d_client import cutout
    cutout(Path(src), Path(dst))
    a = np.asarray(Image.open(dst).convert("RGBA")).copy()
    rgb = a[:, :, :3].astype(np.int32)
    op = a[:, :, 3] >= 128
    shadow = op & (rgb.max(axis=2) > 135) & ((rgb.max(axis=2) - rgb.min(axis=2)) < 26)
    if 0 < shadow.sum() < 0.15 * op.sum():
        a[shadow, 3] = 0
        Image.fromarray(a, "RGBA").save(dst)
    return Path(dst)


def _square(a: np.ndarray, n: int) -> Optional[np.ndarray]:
    """The figure cut to its bounding box and centred in an n x n picture without changing its proportions."""
    box = bbox(np.where(a[:, :, 3:4] >= 128, a, 0))
    if box is None:
        return None
    l, t, r, b = box
    cut = a[t:b + 1, l:r + 1].copy()
    cut[cut[:, :, 3] < 128] = 0
    k = (n - 2) / max(cut.shape[:2])
    im = Image.fromarray(cut, "RGBA").resize((max(1, round(cut.shape[1] * k)), max(1, round(cut.shape[0] * k))), Image.BOX)
    out = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    out.paste(im, ((n - im.width) // 2, (n - im.height) // 2))
    return np.asarray(out)


def _features(sq: np.ndarray) -> np.ndarray:
    """Where the figure's darkest details are in its upper two thirds (eyes, nose, mouth): what tells a front from a
    back when the outlines are alike. Feet are left out: claws and ground shading are dark from every side."""
    op = sq[:, :, 3] >= 128
    lum = sq[:, :, :3].astype(np.float32).mean(axis=2)
    if op.sum() < 8:
        return np.zeros((16, 16), np.float32)
    rows = np.nonzero(op.any(axis=1))[0]
    cut = rows[0] + int((rows[-1] - rows[0]) * 0.66)
    top = op.copy()
    top[cut:] = False
    dark = top & (lum <= np.percentile(lum[op], 6))
    im = Image.fromarray((dark * 255).astype(np.uint8), "L").resize((16, 16), Image.BOX)
    f = np.asarray(im).astype(np.float32)
    n = float(np.linalg.norm(f))
    return f / n if n > 1e-6 else f


def find_tile_yaw(tile: str) -> Tuple[float, Dict[str, Any]]:
    """Which camera yaw shows the mesh the way its concept does. Mesh generators do not agree on where the front of
    a model is, so level views all round are compared with the concept: by outline, and by where the dark details
    sit (a rear view has the same outline as a front view but no face)."""
    w = work_dir(tile)
    full = (w / "full_body.txt").is_file()
    step = 22.5 if full else 45.0
    _blender(tile, w / "probe", ["--probe", "--probe-step", str(step)], 256, "probe_0000.png")
    info = json.loads((w / "probe" / "probe.json").read_text(encoding="utf-8"))
    ref = rgba(w / "concept.png")
    if full and (w / "concept3d_cut.png").is_file():
        ref = rgba(w / "concept3d_cut.png")
    rs = _square(ref, 64)
    rf = _features(rs)
    scores: Dict[str, float] = {}
    for f in sorted((w / "probe").glob("probe_*.png")):
        yaw = int(f.stem.split("_")[1]) / 10.0
        vs = _square(rgba(f), 64)
        if vs is None:
            scores[str(yaw)] = 0.0
            continue
        ma, mb = rs[:, :, 3] >= 128, vs[:, :, 3] >= 128
        iou = float((ma & mb).sum()) / max(1, int((ma | mb).sum()))
        feat = float((rf * _features(vs)).sum())
        scores[str(yaw)] = round(0.6 * iou + 0.4 * feat, 4)
    best = max(scores, key=lambda k: scores[k])
    prior = str(float(TILE_YAW_PRIOR))
    if not full and scores.get(prior, 0.0) >= scores[best] - 0.05:
        best = prior
    info["scores"] = scores
    return float(best), info


def views_batch(tiles: List[str], entries: List[Dict[str, Any]], pitch: float = 10.0) -> None:
    """The four faces of many fast meshes in one Blender start per 40 bodies. Fast meshes always have the picture's
    camera at TILE_YAW_PRIOR, so the probe pass is skipped."""
    todo = [t for t in tiles if done(t, "mesh") and not done(t, "views") and not (work_dir(t) / "full_body.txt").is_file()]
    blender = os.environ.get("AAMT_BLENDER") or str(find_blender())
    env = dict(os.environ)
    for _k in [k for k in env if k.lower() == "nodefaultcurrentdirectoryinexepath"]:
        env.pop(_k)   # os.environ keys are upper-case on Windows; a pop by the mixed-case name misses
    for i in range(0, len(todo), 40):
        chunk = todo[i:i + 40]
        jobs = []
        for t in chunk:
            w = work_dir(t)
            heading, why = tile_heading(t, entries)
            (w / "probe.json").write_text(json.dumps({"tile_yaw": TILE_YAW_PRIOR, "heading": heading, "heading_from": why}, indent=2),
                                          encoding="utf-8")
            out = w / "views"
            if out.exists():
                shutil.rmtree(out)
            full = False
            jobs.append({"model": str(w / "mesh.glb"), "out": str(out), "heading": heading, "tile_yaw": TILE_YAW_PRIOR,
                         "min_depth": 0.0 if full else ROUND_DEPTH if why == "frontal race" else BODY_DEPTH,
                         "max_turn": 90.0 if full else MAX_TURN, "pitch": pitch})
        spec = WORK / "_views_jobs.json"
        spec.write_text(json.dumps(jobs), encoding="utf-8")
        wait_for_free_gpu("rendering")
        with acquire_gpu(f"Blender creature views x{len(chunk)}"):
            run = subprocess.run([blender, "-b", "--factory-startup", "-P", str(BLENDER_WORKER), "--", "--jobs", str(spec), "--size", "768"],
                                 capture_output=True, text=True, timeout=3600, env=env)
        (WORK / "_views_batch.log").write_text((run.stdout or "") + "\n" + (run.stderr or ""), encoding="utf-8", errors="replace")
        print(f"[views] {min(i + 40, len(todo))}/{len(todo)}", flush=True)


def stage_views(tile: str, entries: List[Dict[str, Any]], heading: Optional[float] = None, pitch: float = 10.0) -> Path:
    w = work_dir(tile)
    tile_yaw, info = find_tile_yaw(tile)
    # {"<id or tile>": {"tile_yaw": 22.5}} in the headings file: the camera yaw that shows the body as its concept
    # does, read off work/<tile>/probe/ when the automatic match picked the wrong side (a rear for a front)
    if HEADING_FILE.is_file():
        table = json.loads(HEADING_FILE.read_text(encoding="utf-8"))
        for k in [tile] + [e["id"] for e in entries if tile_name(e) == tile]:
            if isinstance(table.get(k), dict) and "tile_yaw" in table[k]:
                tile_yaw = float(table[k]["tile_yaw"])
    why = "given"
    full = (w / "full_body.txt").is_file()
    measure = False
    if heading is None:
        heading, why = tile_heading(tile, entries)
        # a full body has a real mirror plane, so the worker can measure its heading; the outline guess is for reliefs
        measure = full and why != "override"
        if measure:
            why = "measured from the body's mirror plane"
    (w / "probe.json").write_text(json.dumps({"tile_yaw": tile_yaw, "heading": heading, "heading_from": why, **info}, indent=2),
                                  encoding="utf-8")
    if info["depth_ratio"] < MIN_DEPTH:
        raise RuntimeError(f"flat mesh (depth {info['depth_ratio']:.3f} of its longest side): the concept reads as a "
                           "flat drawing; use the fast mesher or a shaded 3D-looking concept")
    extra = ["--pitch", str(pitch), "--tile-yaw", str(tile_yaw)] + (["--front-prior", "0"] if measure else ["--heading", str(heading)]) + [
             "--min-depth", str(0.0 if full else ROUND_DEPTH if why == "frontal race" else BODY_DEPTH),
             "--max-turn", str(90.0 if full else MAX_TURN)]
    if full:
        extra += ["--shaded"]
    _blender(tile, w / "views", extra, 768, "view_S.png")
    return w / "views"


# --------------------------------------------------------------------------------------------- real motion
# The toolkit's animation stage (Shared/anim_client.py: UniRig skeleton and skin, Wan2.2 video of the creature moving,
# CoTracker fit of the joints to that video) gives a full body real clips. They are rendered from the four faces and
# take the place of the frames that are otherwise pushed out of the still faces.
#   anim clip -> (sheet part, frames, where in each slice the pose is taken)
MOTION = {"move": ("walk", 4, 0.0), "attack": ("attack", 4, 0.5), "special": ("cast", 4, 0.5), "hit": ("hit", 2, 0.6)}
BODY_PLANS = {
    "quadruped": {"cat", "dog", "horse", "animal", "bear", "sheep", "rabbit", "shiba", "wolf", "hound", "rat", "frog",
                  "dinosaur", "dragon", "drake", "cerberus", "centaur", "wyvern", "bike"},
    "hover": {"fairy", "ghost", "phantom", "wisp", "spirit", "eye", "bat", "wraith", "cupid", "wasp", "harpy", "fish",
              "bell", "hand", "piece", "metal"},
    "serpent": {"snake", "slime", "putty", "snail", "mermaid", "octopus", "shell"},
    "crawler": {"spider", "centipede", "crab", "eldercrab", "beetle", "yith"},
    "biped": {"norland", "yerles", "roran", "elea", "eulderna", "juere", "servant", "zombie", "mifu", "nefu", "lich",
              "minotaur", "armor", "mutant", "yeek", "goblin", "dwarf", "vampire", "golem", "orc", "imp", "skeleton",
              "giant", "god", "asura", "ent", "succubus", "lizardman", "demigod", "troll", "demon", "ratkin",
              "catsister", "kobolt", "rabbitkin", "werewolf", "medusa", "machine", "mandrake", "mushroom", "alien",
              "chicken", "stalker", "undeadgod", "machinegod", "god_mani", "quickling", "rock"},
}


def body_plan(tile: str, entries: List[Dict[str, Any]]) -> str:
    """Which of the animation stage's body plans a creature is: {"<id or tile>": {"body": "hover"}} in
    elin_creature_headings.json, else its race, else its shape (a side face wider than high walks on four legs)."""
    mine = [e for e in entries if tile_name(e) == tile]
    if HEADING_FILE.is_file():
        table = json.loads(HEADING_FILE.read_text(encoding="utf-8"))
        for k in [tile] + [e["id"] for e in mine]:
            if isinstance(table.get(k), dict) and "body" in table[k]:
                return str(table[k]["body"])
    races = {str(e.get("race") or "").lower() for e in mine}
    for plan, names in BODY_PLANS.items():
        if races & names:
            return plan
    f = work_dir(tile) / "faces.json"
    if f.is_file():
        side = json.loads(f.read_text(encoding="utf-8"))["faces"].get("W")
        if side and side["w"] < 1.15 * side["h"]:
            return "biped"
    return "quadruped"


def stage_motion(tile: str, entries: List[Dict[str, Any]], pitch: float = 10.0) -> Path:
    """Real motion for a full body: rig it, film it moving, fit the joints, and render the clips from the four faces.
    rigged.glb, anim/ (the animation stage's own cache), motion/<part>/ (renders), motion/frames/ (sprites).
    About 15 to 20 minutes per creature on the 11 GB card; every step is cached."""
    import anim_client
    w = work_dir(tile)
    if not (w / "full_body.txt").is_file():
        raise RuntimeError("real motion needs a real body: run `full` for this creature first")
    if not (w / "views" / "views.json").is_file():
        raise RuntimeError("no views yet: run the views stage first")
    mine = [e for e in entries if tile_name(e) == tile]
    what = str(mine[0].get("name") or mine[0]["id"]) if mine else "creature"
    if (w / "motion.json").is_file() and (w / "motion" / "frames").is_dir():
        return w / "motion"          # done; delete motion.json to make the frames again
    body = body_plan(tile, entries)
    rigged = w / "rigged.glb"
    if not rigged.is_file():
        wait_for_free_gpu("animating")
        anim_client.animate(w / "mesh.glb", rigged, f"the {what}", body=body, work=w / "anim", clips=list(MOTION))
    # the rigged body is the same body, moved and scaled but not turned: its front is where the views stage found it
    front = float(json.loads((w / "views" / "views.json").read_text(encoding="utf-8"))["yaws"]["S"])
    base = ["--pitch", str(pitch), "--tile-yaw", "0", "--heading", str(front), "--min-depth", "0", "--max-turn", "90",
            "--shaded"]
    out = w / "motion"
    _blender(tile, out / "rest", base, 768, "view_S.png", model=rigged)
    for clip, (tag, frames, phase) in MOTION.items():
        _blender(tile, out / tag, base + ["--action", clip, "--frames", str(frames), "--phase", str(phase), "--tag", tag],
                 768, f"{tag}_S_0.png", model=rigged)
    motion_sprites(tile)
    (w / "motion.json").write_text(json.dumps({"body": body, "front": front, "clips": list(MOTION)}, indent=2), encoding="utf-8")
    return out


def motion_sprites(tile: str) -> None:
    """motion/frames/<part>_<D>_<i>.png: the rendered poses as sprites, at the scale and in the colours of the faces.
    Every pose of a direction is placed by that direction's rest view, so a lunge, a rear or a recoil moves in the
    cell; a pose that leaves the cell is cut at its edge."""
    w = work_dir(tile)
    tile_px = rgba(TILES / f"tile_{tile}.png")
    ch, cw = tile_px.shape[:2]
    l, t, r, b = bbox(tile_px)
    cols, outline = palette_of(tile_px)
    scale = float(json.loads((w / "faces.json").read_text(encoding="utf-8"))["scale"])

    def stats(px: np.ndarray, mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        v = px[mask][:, :3].astype(np.float32)
        return v.mean(axis=0), np.maximum(v.std(axis=0), 1.0)

    def small_of(px: np.ndarray, n: int) -> np.ndarray:
        s = resize_area(px, n, n)
        s[:, :, 3] = np.where(s[:, :, 3] >= 110, 255, 0)
        return s

    rest = {d: rgba(w / "motion" / "rest" / f"view_{d}.png") for d in DIRS}
    size = rest["S"].shape[0]
    small = max(1, round(size * scale))
    tile_mean, tile_std = stats(tile_px, tile_px[:, :, 3] > 0)
    every = np.concatenate([small_of(rest[d], small).reshape(-1, 4) for d in DIRS])
    view_mean, view_std = stats(every[None], (every[:, 3] > 0)[None])
    gain = np.clip(tile_std / view_std, 0.6, 2.2)

    def finish(px: np.ndarray) -> np.ndarray:
        out = px.astype(np.float32)
        out[:, :, :3] = np.clip((out[:, :, :3] - view_mean) * gain + tile_mean, 0, 255)
        out = snap_to_palette(out.astype(np.uint8), cols)
        op = out[:, :, 3] > 0
        pad = np.pad(op, 1)
        edge = op & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
        out[edge, :3] = outline
        out[~op] = 0
        return out

    frames_dir = w / "motion" / "frames"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True)
    ground, centre = b, (l + r) / 2.0
    for d in DIRS:
        n = small
        fb = bbox(small_of(rest[d], n))
        if fb is None:
            raise RuntimeError(f"rest view {d} of the rigged body is empty")
        fw, fh = fb[2] - fb[0] + 1, fb[3] - fb[1] + 1
        if fw > cw - 2 or fh > ch - 1:               # the same shrink the face of a long body gets
            n = max(1, int(small * min((cw - 2) / fw, (ch - 1) / fh)))
            fb = bbox(small_of(rest[d], n))
            fw, fh = fb[2] - fb[0] + 1, fb[3] - fb[1] + 1
        ox = min(max(0, int(round(centre - (fw - 1) / 2.0))), cw - fw) - fb[0]
        oy = min(max(0, ground - fh + 1), ch - fh) - fb[1]
        for tag, count, _ in MOTION.values():
            for i in range(count):
                px = finish(small_of(rgba(w / "motion" / tag / f"{tag}_{d}_{i}.png"), n))
                cell = np.zeros((ch, cw, 4), dtype=np.uint8)
                x0, y0 = max(0, ox), max(0, oy)
                x1, y1 = min(cw, ox + n), min(ch, oy + n)
                if x1 > x0 and y1 > y0:
                    cell[y0:y1, x0:x1] = px[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
                Image.fromarray(cell, "RGBA").save(frames_dir / f"{tag}_{d}_{i}.png")


def motion_frames(tile: str, tag: str, d: str, count: int) -> Optional[List[np.ndarray]]:
    """The real frames of a sheet part in one direction, if the motion stage made them."""
    fs = [work_dir(tile) / "motion" / "frames" / f"{tag}_{d}_{i}.png" for i in range(count)]
    return [rgba(f) for f in fs] if all(f.is_file() for f in fs) else None


def palette_of(tile_px: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """The tile's colours (N x 3) and its outline colour (the commonest colour on the figure's edge)."""
    op = tile_px[:, :, 3] > 0
    cols = np.unique(tile_px[op][:, :3], axis=0)
    pad = np.pad(op, 1)
    edge = op & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    ec, counts = np.unique(tile_px[edge][:, :3], axis=0, return_counts=True)
    order = np.argsort(-counts)[:6]
    outline = ec[order][np.argmin(ec[order].astype(int).sum(axis=1))] if len(ec) else np.array([20, 20, 24])
    return cols, outline


def snap_to_palette(px: np.ndarray, cols: np.ndarray) -> np.ndarray:
    flat = px[:, :, :3].reshape(-1, 3).astype(np.int32)
    out = np.empty_like(flat)
    w = np.array([3, 4, 2])                    # the eye weighs green most
    for i in range(0, len(flat), 8192):
        d = ((flat[i:i + 8192, None, :] - cols[None, :, :].astype(np.int32)) ** 2 * w).sum(axis=2)
        out[i:i + 8192] = cols[np.argmin(d, axis=1)]
    res = px.copy()
    res[:, :, :3] = out.reshape(px.shape[0], px.shape[1], 3)
    return res


def stage_sprites(tile: str) -> Dict[str, Any]:
    """faces/face_<D>.png: each rendered face as a sprite in the tile's own cell, scale, colours and outline."""
    w = work_dir(tile)
    tile_px = rgba(TILES / f"tile_{tile}.png")
    ch, cw = tile_px.shape[:2]
    l, t, r, b = bbox(tile_px)
    fig_h, fig_w = b - t + 1, r - l + 1
    cols, outline = palette_of(tile_px)

    views = {d: rgba(w / "views" / f"view_{d}.png") for d in DIRS + ["T"]}
    tb = bbox(np.where(views["T"][:, :, 3:4] >= 128, views["T"], 0))
    if tb is None:
        raise RuntimeError("the mesh rendered empty")
    scale = fig_h / (tb[3] - tb[1] + 1)            # the tile view of the body is as tall as the tile's figure
    size = views["T"].shape[0]
    small = max(1, round(size * scale))
    # A mesh texture is the tile with the light taken out, so it is paler and flatter. Measure that on the view the
    # tile was drawn from and undo it on every face, then snap to the tile's own colours.
    def stats(px: np.ndarray, mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        v = px[mask][:, :3].astype(np.float32)
        return v.mean(axis=0), np.maximum(v.std(axis=0), 1.0)

    t_small = resize_area(views["T"], small, small)
    tile_mean, tile_std = stats(tile_px, tile_px[:, :, 3] > 0)
    view_mean, view_std = stats(t_small, t_small[:, :, 3] >= 110)
    gain = np.clip(tile_std / view_std, 0.6, 2.2)

    def recolour(px: np.ndarray) -> np.ndarray:
        out = px.astype(np.float32)
        out[:, :, :3] = np.clip((out[:, :, :3] - view_mean) * gain + tile_mean, 0, 255)
        return out.astype(np.uint8)

    faces_dir = w / "faces"
    faces_dir.mkdir(exist_ok=True)
    info: Dict[str, Any] = {"scale": round(scale, 4), "cell": [cw, ch], "figure": [l, t, r, b], "faces": {}}
    ground = b                                      # the tile's ground line (image row)
    centre = (l + r) / 2.0
    for d in DIRS + ["T"]:
        s = resize_area(views[d], small, small)
        s[:, :, 3] = np.where(s[:, :, 3] >= 110, 255, 0)
        fb = bbox(s)
        if fb is None:
            raise RuntimeError(f"face {d} is empty")
        cut = s[fb[1]:fb[3] + 1, fb[0]:fb[2] + 1]
        # too wide for the cell (a long body seen from the side): shrink that face to fit
        if cut.shape[1] > cw - 2 or cut.shape[0] > ch - 1:
            k = min((cw - 2) / cut.shape[1], (ch - 1) / cut.shape[0])
            cut = resize_area(cut, max(1, int(cut.shape[1] * k)), max(1, int(cut.shape[0] * k)))
            cut[:, :, 3] = np.where(cut[:, :, 3] >= 110, 255, 0)
        cut = snap_to_palette(recolour(cut), cols)
        op = cut[:, :, 3] > 0
        pad = np.pad(op, 1)
        edge = op & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
        cut[edge, :3] = outline
        cut[~op] = 0
        cell = np.zeros((ch, cw, 4), dtype=np.uint8)
        fh, fw = cut.shape[:2]
        x0 = int(round(centre - (fw - 1) / 2.0))
        x0 = min(max(0, x0), cw - fw)
        y0 = min(max(0, ground - fh + 1), ch - fh)
        cell[y0:y0 + fh, x0:x0 + fw] = cut
        Image.fromarray(cell, "RGBA").save(faces_dir / f"face_{d}.png")
        info["faces"][d] = {"w": fw, "h": fh}
    (w / "faces.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    return info


def shift_rows(face: np.ndarray, dx_of_row, dy_of_row) -> np.ndarray:
    """A frame from a face: every destination row (counted up from the figure's lowest row) names the source row
    and the sideways shift it shows."""
    h, w = face.shape[:2]
    box = bbox(face)
    out = np.zeros_like(face)
    if box is None:
        return out
    l, t, r, b = box
    fig = b - t + 1
    for row in range(h):                       # image rows, top first
        y = b - row                            # rows above the ground line; negative = below it
        if y < 0:
            continue
        src_y, dx = dy_of_row(y, fig), dx_of_row(y, fig)
        src_row = b - src_y
        if src_row < 0 or src_row >= h:
            continue
        line = face[src_row]
        if dx > 0:
            out[row, dx:] = line[:w - dx]
        elif dx < 0:
            out[row, :w + dx] = line[-dx:]
        else:
            out[row] = line
    return out


def scale_face(face: np.ndarray, kx: float, ky: float, push: Tuple[int, int] = (0, 0), tint: float = 0.0) -> np.ndarray:
    """A face stretched about its feet (kx, ky), moved by push pixels, and lightened by tint (0..1)."""
    box = bbox(face)
    out = np.zeros_like(face)
    if box is None:
        return out
    l, t, r, b = box
    cut = face[t:b + 1, l:r + 1]
    nw, nh = max(1, round(cut.shape[1] * kx)), max(1, round(cut.shape[0] * ky))
    im = np.asarray(Image.fromarray(cut, "RGBA").resize((nw, nh), Image.NEAREST)).copy()
    if tint > 0:
        im[:, :, :3] = (im[:, :, :3] + (255 - im[:, :, :3]) * tint).astype(np.uint8)
    h, w = face.shape[:2]
    cx = (l + r) / 2.0
    x0 = int(round(cx - (nw - 1) / 2.0)) + push[0]
    y0 = b - nh + 1 + push[1]
    xs, ys = max(0, x0), max(0, y0)
    xe, ye = min(w, x0 + nw), min(h, y0 + nh)
    if xe > xs and ye > ys:
        out[ys:ye, xs:xe] = im[ys - y0:ye - y0, xs - x0:xe - x0]
    return out


def walk_frames(face: np.ndarray, d: str) -> List[np.ndarray]:
    """neutral, step, neutral, opposite step. Seen from the side the legs swing along the screen; seen from the
    front or back the body sways and rises instead (legs swinging toward the viewer do not read sideways)."""
    def frame(step: int) -> np.ndarray:
        if step == 0:
            return face
        side = d in ("W", "E")
        stride, lean, rise_k, legs_k = (0.07, 0.025, 0.025, 0.42) if side else (0.0, 0.05, 0.035, 0.42)

        def src_row(y: int, fig: int) -> int:
            rise = max(1, round(fig * rise_k))
            legs = max(1.0, fig * legs_k)
            return y - rise if y >= legs + rise else int(math.floor(y * legs / (legs + rise)))

        def dx(y: int, fig: int) -> int:
            body = src_row(y, fig)
            legs = max(1.0, fig * legs_k)
            if body < legs:
                return int(round(step * fig * stride * (1 - body / legs)))
            return -int(round(step * fig * lean * ((body - legs) / max(1.0, fig - legs))))

        return shift_rows(face, dx, src_row)
    return [frame(0), frame(1), frame(0), frame(-1)]


def lean_frame(face: np.ndarray, toward: int, amount: float) -> np.ndarray:
    """The body leaning sideways from the feet up (toward = -1 left, +1 right) by amount of its height at the top."""
    return shift_rows(face, lambda y, fig: int(round(toward * fig * amount * y / max(1, fig))), lambda y, fig: y)


def attack_frames(face: np.ndarray, d: str) -> List[np.ndarray]:
    """wind-up, strike, follow-through, recover, toward where the face is heading."""
    h, w = face.shape[:2]
    reach = max(2, round(w * 0.11))
    if d in ("W", "E"):
        s = -1 if d == "W" else 1
        return [
            scale_face(lean_frame(face, -s, 0.10), 1.0, 0.95, (-s * max(1, reach // 3), 0)),
            scale_face(lean_frame(face, s, 0.16), 1.06, 0.97, (s * reach, 0)),
            scale_face(lean_frame(face, s, 0.08), 1.02, 1.0, (s * max(1, reach // 2), 0)),
            face,
        ]
    if d == "S":   # toward the viewer: the body dips, then looms larger
        return [scale_face(face, 1.0, 0.93), scale_face(face, 1.12, 1.12, (0, max(1, reach // 3))),
                scale_face(face, 1.06, 1.06), face]
    # N, away from the viewer: it rears, then drives up the screen and shrinks
    return [scale_face(face, 1.04, 0.95), scale_face(face, 0.92, 0.94, (0, -reach)),
            scale_face(face, 0.96, 0.97, (0, -max(1, reach // 2))), face]


def cast_frames(face: np.ndarray, d: str) -> List[np.ndarray]:
    """gather (crouch), rise, release (tall and lit), settle."""
    return [scale_face(face, 1.03, 0.94), scale_face(face, 0.98, 1.05, tint=0.12),
            scale_face(face, 0.96, 1.09, tint=0.30), scale_face(face, 1.0, 1.02, tint=0.10)]


def hit_frames(face: np.ndarray, d: str) -> List[np.ndarray]:
    """recoil away from where it is heading, then back."""
    h, w = face.shape[:2]
    back = max(1, round(w * 0.05))
    if d in ("W", "E"):
        s = 1 if d == "W" else -1
        return [scale_face(lean_frame(face, s, 0.10), 1.0, 0.96, (s * back, 0), tint=0.35), scale_face(face, 1.0, 0.99, (s * max(1, back // 2), 0), tint=0.12)]
    return [scale_face(face, 1.05, 0.93, tint=0.35), scale_face(face, 1.02, 0.97, tint=0.12)]


def stage_sheet(tile: str) -> Dict[str, Path]:
    w = work_dir(tile)
    faces = {d: rgba(w / "faces" / f"face_{d}.png") for d in DIRS}
    ch, cw = faces["S"].shape[:2]
    # The game keeps one paperdoll canvas per sheet WIDTH, so two sheets as wide as each other must be as high as
    # each other. Cells that are not square get two empty columns on each side: their sheets then have a width no
    # square-cell sheet has. The sprite pivot is the bottom centre, so the creature does not move.
    pad = 0 if ch == cw else 2
    fw = cw + 2 * pad
    walk = np.zeros((ch * 4, fw * 4, 4), dtype=np.uint8)
    for row, d in enumerate(DIRS):
        for col, fr in enumerate(motion_frames(tile, "walk", d, 4) or walk_frames(faces[d], d)):
            walk[row * ch:(row + 1) * ch, col * fw + pad:col * fw + pad + cw] = fr
    walk_path = w / "walk.png"
    Image.fromarray(walk, "RGBA").save(walk_path)

    makers = {"attack": attack_frames, "cast": cast_frames, "hit": hit_frames}
    total = sum(c["frames"] for c in CLIPS.values())
    anim = np.zeros((ch * 4, cw * total, 4), dtype=np.uint8)
    meta: Dict[str, Any] = {"version": 1, "cell": [cw, ch], "dirs": DIRS, "clips": {}}
    col0 = 0
    for name, spec in CLIPS.items():
        for row, d in enumerate(DIRS):
            frames = motion_frames(tile, name, d, spec["frames"]) or makers[name](faces[d], d)
            for i in range(spec["frames"]):
                anim[row * ch:(row + 1) * ch, (col0 + i) * cw:(col0 + i + 1) * cw] = frames[i]
        meta["clips"][name] = {"col": col0, "frames": spec["frames"], "fps": spec["fps"]}
        col0 += spec["frames"]
    anim_path = w / "anim.png"
    Image.fromarray(anim, "RGBA").save(anim_path)
    (w / "anim.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"walk": walk_path, "anim": anim_path}


def stage_deploy(tile: str, entries: List[Dict[str, Any]]) -> int:
    """Copy this tile's sheets into the mod once per creature key that uses the tile."""
    w = work_dir(tile)
    pcc = mod_dir() / "Actor" / "PCC" / "crcc"
    extra = mod_dir() / "Paperdolls" / "Anim"
    pcc.mkdir(parents=True, exist_ok=True)
    extra.mkdir(parents=True, exist_ok=True)
    n = 0
    for e in entries:
        if tile_name(e) != tile:
            continue
        shutil.copyfile(w / "walk.png", pcc / f"pcc_body_{e['key']}.png")
        shutil.copyfile(w / "anim.png", extra / f"anim_{e['key']}.png")
        shutil.copyfile(w / "anim.json", extra / f"anim_{e['key']}.json")
        n += 1
    return n


def done(tile: str, stage: str) -> bool:
    w = work_dir(tile)
    return {
        "concept": (w / "concept.png").is_file(),
        "mesh": (w / "mesh.glb").is_file(),
        "views": (w / "views" / "view_T.png").is_file(),
        "sprites": (w / "faces" / "face_N.png").is_file(),
        "sheet": (w / "anim.json").is_file(),
        "deploy": (w / "deployed.txt").is_file(),
    }[stage]


def make_preview(tile: str) -> Path:
    """One picture to judge a creature by: the tile, the four faces, the tile-view check and the walk sheet."""
    w = work_dir(tile)
    tile_im = Image.open(TILES / f"tile_{tile}.png").convert("RGBA")
    k = 3
    parts = [tile_im] + [Image.open(w / "faces" / f"face_{d}.png").convert("RGBA") for d in DIRS + ["T"]]
    cw, ch = tile_im.size
    board = Image.new("RGBA", (cw * k * len(parts) + 8 * (len(parts) + 1), ch * k + 16 + ch * 4 * 2 // 1), (62, 84, 62, 255))
    x = 8
    for im in parts:
        big = im.resize((cw * k, ch * k), Image.NEAREST)
        board.paste(big, (x, 8), big)
        x += cw * k + 8
    walk = Image.open(w / "walk.png").convert("RGBA")
    anim = Image.open(w / "anim.png").convert("RGBA")
    y = ch * k + 16
    board.paste(walk, (8, y), walk)
    board.paste(anim, (8 + walk.width + 16, y), anim)
    out = w / "preview.png"
    board.convert("RGB").save(out)
    return out


# --------------------------------------------------------------------------------------------- driver

def pick_tiles(manifest: List[Dict[str, Any]], ids: List[str], everything: bool, limit: int) -> List[str]:
    if ids:
        rank = {x: i for i, x in enumerate(ids)}
        wanted = sorted((e for e in manifest if e["id"] in ids or tile_name(e) in ids),
                        key=lambda e: min(rank.get(e["id"], 10 ** 6), rank.get(tile_name(e), 10 ** 6)))
        missing = set(ids) - {e["id"] for e in wanted} - {tile_name(e) for e in wanted}
        if missing:
            print(f"[warn] not in the manifest: {sorted(missing)}")
    elif everything:
        # creatures a player meets most come first: common, low level
        wanted = sorted(manifest, key=lambda e: (-(e.get("chance") or 0) > -1, e.get("lv") or 0))
    else:
        wanted = []
    tiles: List[str] = []
    for e in wanted:
        t = tile_name(e)
        if t not in tiles:
            tiles.append(t)
    return tiles[:limit] if limit else tiles


def run(tiles: List[str], manifest: List[Dict[str, Any]], start: str, heading: Optional[float], pitch: float,
        seed: int, stop_at: str, mesher: str = "fast") -> int:
    failed = 0
    order = STAGES[:STAGES.index(stop_at) + 1]
    if mesher == "fast" and "mesh" in order and start in ("", "concept", "mesh"):
        if start in ("concept", "mesh"):
            for t in tiles:
                for f in (["concept.png"] if start == "concept" else []) + ["mesh.glb"]:
                    (work_dir(t) / f).unlink(missing_ok=True)
            start = "views"
        mesh_batch(tiles)
    if mesher == "fast" and "views" in order and heading is None:
        if start == "views":
            for t in tiles:
                shutil.rmtree(work_dir(t) / "views", ignore_errors=True)
            start = "sprites"
        views_batch(tiles, manifest, pitch)
    for n, tile in enumerate(tiles, 1):
        names = sorted({e["id"] for e in manifest if tile_name(e) == tile})
        t0 = time.monotonic()
        try:
            redo = False
            for stage in order:
                if stage == start:
                    redo = True
                if not redo and done(tile, stage):
                    continue
                if stage == "views" and (work_dir(tile) / "views" / "error.txt").is_file():
                    raise RuntimeError((work_dir(tile) / "views" / "error.txt").read_text(encoding="utf-8"))
                redo = True                    # a stage that ran makes every later stage stale
                if stage == "concept":
                    stage_concept(tile)
                elif stage == "mesh":
                    stage_mesh(tile, seed, mesher)
                elif stage == "views":
                    stage_views(tile, manifest, heading, pitch)
                elif stage == "sprites":
                    stage_sprites(tile)
                elif stage == "sheet":
                    stage_sheet(tile)
                    make_preview(tile)
                elif stage == "deploy":
                    k = stage_deploy(tile, manifest)
                    (work_dir(tile) / "deployed.txt").write_text(f"{k} keys\n", encoding="utf-8")
            print(f"[{n}/{len(tiles)}] {tile} ({', '.join(names[:3])}) ok in {time.monotonic() - t0:.0f}s", flush=True)
        except Exception as exc:
            failed += 1
            work_dir(tile).mkdir(parents=True, exist_ok=True)
            (work_dir(tile) / "error.txt").write_text(str(exc), encoding="utf-8")
            print(f"[{n}/{len(tiles)}] {tile} ({', '.join(names[:3])}) FAILED: {str(exc).splitlines()[0][:200]}", flush=True)
    return failed


def status(manifest: List[Dict[str, Any]]) -> None:
    tiles = sorted({tile_name(e) for e in manifest})
    counts = {s: sum(1 for t in tiles if done(t, s)) for s in STAGES}
    errors = sum(1 for t in tiles if (work_dir(t) / "error.txt").is_file() and not done(t, "deploy"))
    print(f"creature rows {len(manifest)}, tiles {len(tiles)}")
    for s in STAGES:
        print(f"  {s:8} {counts[s]:4} / {len(tiles)}")
    print(f"  failed   {errors}")
    pcc = mod_dir() / "Actor" / "PCC" / "crcc"
    print(f"deployed sheets in the mod: {len(list(pcc.glob('pcc_body_*.png'))) if pcc.is_dir() else 0}  ({pcc})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["run", "full", "motion", "status", "preview", "probe"])
    ap.add_argument("--motion", action="store_true",
                    help="with `full`: also rig the body and film it moving, for real walk, attack, cast and hit frames")
    ap.add_argument("--id", default="", help="creature ids or tile names, comma separated")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--from", dest="start", default="", choices=[""] + STAGES, help="redo from this stage on")
    ap.add_argument("--to", dest="stop", default="deploy", choices=STAGES)
    ap.add_argument("--heading", type=float, default=None, help="where the body is heading, degrees CCW from the tile camera")
    ap.add_argument("--pitch", type=float, default=10.0, help="camera elevation of the four faces, degrees")
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--keep", action="store_true", help="keep the TRELLIS server between meshes (batch)")
    ap.add_argument("--mesher", default="fast", choices=["fast", "trellis"],
                    help="fast = Stable Fast 3D (default; right for game tiles), trellis = TRELLIS (shaded concepts)")
    ap.add_argument("--list", default="", help="text file of creature ids, one per line, most important first")
    a = ap.parse_args()

    manifest = load_manifest()
    if a.command == "status":
        status(manifest)
        return 0
    ids = [x.strip() for x in a.id.split(",") if x.strip()]
    if a.list:
        ids += [l.strip() for l in Path(a.list).read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    tiles = pick_tiles(manifest, ids, a.all, a.limit)
    if not tiles:
        print("nothing selected: pass --id or --all")
        return 2
    if a.command == "preview":
        for t in tiles:
            print(make_preview(t))
        return 0
    if a.command == "probe":
        for t in tiles:
            print(find_tile_yaw(t))
        return 0
    if a.command == "motion":
        # real motion for creatures that already have a full body: rig, film, fit, render, new sheets, deploy
        failed = 0
        for n, t in enumerate(tiles, 1):
            t0 = time.monotonic()
            try:
                stage_motion(t, manifest, a.pitch)
                failed += run([t], manifest, "sheet", a.heading, a.pitch, a.seed, a.stop, "trellis")
                print(f"[motion {n}/{len(tiles)}] {t} done in {(time.monotonic() - t0) / 60:.0f} min", flush=True)
            except Exception as exc:
                failed += 1
                print(f"[motion {n}/{len(tiles)}] {t} FAILED: {str(exc).splitlines()[-1][:200]}", flush=True)
        print(f"done: {len(tiles) - failed} ok, {failed} failed")
        return 1 if failed else 0
    if a.command == "full":
        # one creature after another: redraw, body, faces, sheets, deploy. Kontext and TRELLIS cannot both be resident,
        # so TRELLIS is stopped after each mesh (the default) and the guard hands the card from one to the other.
        failed = 0
        for n, t in enumerate(tiles, 1):
            t0 = time.monotonic()
            try:
                stage_full_body(t, manifest)
                failed += run([t], manifest, "views", a.heading, a.pitch, a.seed, a.stop, "trellis")
                if a.motion:
                    stage_motion(t, manifest, a.pitch)
                    failed += run([t], manifest, "sheet", a.heading, a.pitch, a.seed, a.stop, "trellis")
                print(f"[full {n}/{len(tiles)}] {t} done in {(time.monotonic() - t0) / 60:.0f} min", flush=True)
            except Exception as exc:
                failed += 1
                print(f"[full {n}/{len(tiles)}] {t} FAILED: {str(exc).splitlines()[-1][:200]}", flush=True)
        print(f"done: {len(tiles) - failed} ok, {failed} failed")
        return 1 if failed else 0
    if a.keep:
        os.environ["AAMT_TRELLIS_KEEP_SERVER"] = "1"
    failed = run(tiles, manifest, a.start, a.heading, a.pitch, a.seed, a.stop, a.mesher)
    print(f"done: {len(tiles) - failed} ok, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
