#!/usr/bin/env python3
"""Animation stage: a generated mesh -> a skinned .glb with real motion clips (idle, idle2, move, attack, attack2, hit,
death, special).

The chain, every step cached in a work folder so a stopped run picks up where it left off:
  prep    Blender: centre, feet on the floor, longest side 1 (the mesh must already face -Y)  -> norm.glb, mesh.npz
  rig     UniRig (learned skeleton + skin weights, any body plan), weights moved onto our vertices -> rig.npz
  render  Blender: the rigged body from a front-three-quarter camera on white, and that camera -> frame0.png, cam.json
  video   Wan2.2-TI2V-5B: frame0 + "it lunges and strikes..." -> a short clip per action        -> video/<clip>.mp4
  fit     CoTracker3 follows the visible vertices through each clip; joint rotations are fitted to those tracks
          through the known camera, then the clip is looped / trimmed / kept in place at 30 fps   -> clips/<clip>.npz
  build   Blender: armature, skin, one glTF animation per clip                                   -> the output .glb

Python:
    from ai_resources import make_animated_mesh
    make_animated_mesh("hound.glb", "hound_rigged.glb", "a lean robotic hound", body="quadruped")
CLI:
    python anim_client.py hound.glb hound_rigged.glb --desc "a lean robotic hound" --body quadruped [--work DIR]
                          [--only rig,render] [--clips idle,attack] [--redo video]
    python anim_client.py --status

Installs (see Tools/Shared/ANIMATION.md): AAMT_ANIM_HOME (default E:\\tools\\anim) holds .venv (torch, diffusers,
co-tracker) and UniRig\\ with its own .venv. Weights live as plain folders in <HF_HOME>\\local (D:\\hf-cache\\local).
GPU-heavy steps (rig, video, fit) stop the SD and TRELLIS servers first (AAMT_KEEP_SERVERS=1 to skip) and hold the
AAMT GPU lock.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
_ANIM = _SHARED / "anim"

try:
    from gpu_hub import acquire_gpu
except Exception:  # hub is optional
    import contextlib

    def acquire_gpu(label, timeout=None, poll=2.0, enabled=True):  # type: ignore
        return contextlib.nullcontext()

STAGES = ["prep", "rig", "render", "video", "fit", "build"]

# What each clip asks the video model for, by body plan. {it} is the creature description. Loops get a cycle cut
# out of them; one-shots get their busiest stretch of the given length and settle back to rest (death stays down).
_STILL = "Static camera, plain white background, the whole body stays in frame."
MOTION = {
    "idle": ("loop", None, "{it} stands in place, breathing, shifting its weight from leg to leg and turning its head to look around."),
    "move": ("move", None, {
        # tested: "walks forward" mostly gets a creature standing still; marching or walking on the spot, with each
        # limb named, gets real steps
        "biped": "{it} marches on the spot, lifting its left knee high, then its right knee high, arms swinging, over and over.",
        "quadruped": "{it} trots on a treadmill, lifting each paw high in a steady rhythm, head bobbing.",
        "crawler": "{it} walks slowly to the left, each of its legs lifting high and stepping down in turn.",
        "hover": "{it} slowly spins around in the air on the spot, its arms opening and closing as it turns.",
        "serpent": "{it} coils its body into a tight curve and then stretches out straight again, over and over.",
    }),
    # played now and then instead of idle, as a one-shot from and back to rest
    "idle2": ("oneshot", 2.4, "{it} stands in place and turns to look left, then right, curious, then settles back."),
    "attack": ("oneshot", 1.2, "{it} rears back and lunges forward to attack, then drops back into place. Fast, energetic movement."),
    "attack2": ("oneshot", 1.2, "{it} jabs forward twice in quick strikes, then settles. Fast, energetic movement."),
    "hit": ("oneshot", 0.7, "{it} flinches and recoils backwards as if struck, then steadies itself. Fast, sudden movement."),
    "death": ("death", 2.0, {
        "hover": "{it} sparks and loses power, drops heavily to the ground and lies still on its side.",
        "serpent": "{it} thrashes, then goes limp and lies still on the ground.",
        "default": "{it} staggers, its legs give way and it collapses onto the ground and lies still.",
    }),
    "special": ("oneshot", 1.4, "{it} rears up tall and shakes violently, gathering power, then settles. Energetic movement."),
}
DEFAULT_CLIPS = ["idle", "idle2", "move", "attack", "attack2", "hit", "death", "special"]


def anim_home() -> Path:
    return Path(os.environ.get("AAMT_ANIM_HOME") or r"E:\tools\anim")


def _py() -> Path:
    return anim_home() / ".venv" / "Scripts" / "python.exe"


def unirig_home() -> Path:
    return anim_home() / "UniRig"


def _unirig_py() -> Path:
    return unirig_home() / ".venv" / "Scripts" / "python.exe"


def blender_exe() -> Path:
    if os.environ.get("AAMT_BLENDER"):
        return Path(os.environ["AAMT_BLENDER"])
    found = []
    for root in (r"D:/tools/Blender Foundation", r"C:/Program Files/Blender Foundation"):
        found += Path(root).glob("*/blender.exe") if Path(root).exists() else []
    if not found:
        raise RuntimeError("Blender not found (set AAMT_BLENDER)")
    return max(found, key=lambda p: p.stat().st_mtime)


def status() -> Dict[str, Any]:
    local = Path(os.environ.get("HF_HOME") or r"D:\hf-cache") / "local"
    return {
        "anim_venv": _py().exists(),
        "unirig": _unirig_py().exists() and (unirig_home() / "experiments" / "skin" / "articulation-xl" / "model.ckpt").exists(),
        "wan": (local / "Wan2.2-TI2V-5B-Diffusers" / "model_index.json").exists() and (local / "Wan2.2-TI2V-5B-GGUF").exists(),
        "cotracker": (local / "cotracker3" / "scaled_offline.pth").exists(),
        "blender": str(blender_exe()),
    }


def available() -> bool:
    s = status()
    return all(s[k] for k in ("anim_venv", "unirig", "wan", "cotracker"))


def _env() -> Dict[str, str]:
    env = dict(os.environ)
    env.pop("NoDefaultCurrentDirectoryInExePath", None)  # agent shells set it; breaks child launchers
    env.setdefault("HF_HOME", r"D:\hf-cache")
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _run(cmd: List[str], label: str, cwd: Optional[Path] = None, timeout: float = 3600) -> str:
    t = time.time()
    p = subprocess.run([str(c) for c in cmd], cwd=str(cwd) if cwd else None, env=_env(), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    out = p.stdout + p.stderr
    if p.returncode != 0:
        tail = "\n".join(out.splitlines()[-25:])
        raise RuntimeError(f"{label} failed (exit {p.returncode}):\n{tail}")
    print(f"[ANIM] {label}: {time.time() - t:.0f}s", file=sys.stderr, flush=True)
    return out


def _blender(*args: Any, label: str) -> str:
    return _run([blender_exe(), "-b", "--factory-startup", "-P", _ANIM / "blender_anim.py", "--", *args], label)


def _free_gpu() -> None:
    if os.environ.get("AAMT_KEEP_SERVERS") == "1":
        return
    for mod, fn in (("sd_server_lifecycle", "stop_sd_server"), ("trellis_http_client", "stop_server")):
        try:
            getattr(__import__(mod), fn)(force=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[ANIM] could not stop {mod}: {exc}", file=sys.stderr)


# ---- stages ---------------------------------------------------------------------------------------------------------

def prep(src: Path, work: Path) -> None:
    _blender("prep", Path(src).resolve(), work, label="prep")


def rig(work: Path, seed: int = 12345) -> Dict[str, Any]:
    """UniRig's skeleton then skin on norm.glb; its weights moved onto mesh.npz's vertices -> rig.npz."""
    u = unirig_home()
    npz = work / "unirig"
    npz.mkdir(exist_ok=True)
    src = (work / "norm.glb").resolve()
    with acquire_gpu("UniRig"):
        _free_gpu()  # inside the lock: another session's SD/TRELLIS request may be running until we hold it
        _run([_unirig_py(), "-m", "src.data.extract", "--config=configs/data/quick_inference.yaml", "--require_suffix=glb",
              "--force_override=true", "--num_runs=1", "--id=0", "--time=aamt", "--faces_target_count=50000",
              f"--input={src}", f"--output_dir={npz}"], "unirig extract", cwd=u)
        _run([_unirig_py(), "run.py", "--task=configs/task/aamt_skeleton.yaml", f"--seed={seed}", f"--input={src}",
              f"--output_dir={npz / 'out'}", f"--npz_dir={npz}"], "unirig skeleton", cwd=u)
        _run([_unirig_py(), "run.py", "--task=configs/task/aamt_skin.yaml", f"--seed={seed}", f"--input={src}",
              f"--output_dir={npz / 'out'}", f"--npz_dir={npz}", "--data_name=predict_skeleton.npz"], "unirig skin", cwd=u)
    out = _run([_py(), "-I", _ANIM / "rig_transfer.py", work], "rig transfer")
    return json.loads(out.strip().splitlines()[-1])


def render(work: Path, width: int = 640, height: int = 352) -> None:
    """640x352: what Wan2.2-TI2V-5B makes in about 100 s here (832x480 tips the 11 GB card into swapping)."""
    _blender("render", work, width, height, label="render")
    if (work / "rig.npz").exists():
        overlay(work)


def overlay(work: Path) -> Path:
    """skeleton.png: the rig over frame0 (read it to judge the skeleton before spending GPU hours on video)."""
    _run([_py(), "-I", _ANIM / "overlay.py", work], "overlay")
    return work / "skeleton.png"


def clip_prompt(clip: str, desc: str, body: str, override: Optional[str] = None) -> str:
    text = override or MOTION[clip][2]
    if isinstance(text, dict):
        text = text.get(body) or text.get("default") or text["quadruped"]
    it = desc[0].upper() + desc[1:]
    return text.format(it=it) + " " + _STILL


def make_videos(work: Path, prompts: Dict[str, str], *, frames: int = 49, steps: int = 20, seed: int = 7, redo: bool = False,
                model: Optional[str] = None, seeds: Optional[Dict[str, int]] = None) -> List[Dict]:
    """One clip per prompt from frame0.png. model "fast" (FastWan, 3 steps; the default, AAMT_ANIM_VIDEO_MODEL) or
    "base" (Wan2.2-TI2V-5B, `steps` steps with guidance; better prompt following, about 16x the time)."""
    model = model or os.environ.get("AAMT_ANIM_VIDEO_MODEL", "base")
    vid = work / "video"
    vid.mkdir(exist_ok=True)
    jobs = []
    for i, (clip, prompt) in enumerate(prompts.items()):
        out = vid / f"{clip}.mp4"
        meta = vid / f"{clip}.json"
        if out.exists() and not redo and meta.exists() and json.loads(meta.read_text()).get("prompt") == prompt                 and json.loads(meta.read_text()).get("model", "base") == model:
            continue
        kind, secs = MOTION.get(clip, ("oneshot", None))[:2]
        n = 73 if kind in ("loop", "move", "death") or (secs or 0) > 1.8 else frames
        jobs.append({"image": str((work / "frame0.png").resolve()), "prompt": prompt, "out": str(out.resolve()), "frames": n, "seed": (seeds or {}).get(clip, seed + i)})
    if not jobs:
        return []
    spec = work / "video" / "jobs.json"
    spec.write_text(json.dumps({"width": json.loads((work / "cam.json").read_text())["width"],
                                "height": json.loads((work / "cam.json").read_text())["height"], "model": model, "steps": steps, "jobs": jobs}, indent=1))
    with acquire_gpu(f"Wan2.2 x{len(jobs)}"):
        _free_gpu()  # inside the lock: another session's SD/TRELLIS request may be running until we hold it
        out = _run([_py(), "-I", _ANIM / "wan_video.py", "--jobs", spec], f"video x{len(jobs)}", timeout=6 * 3600)
    res = [json.loads(l) for l in out.splitlines() if l.startswith("{")]
    for j in jobs:
        r = next((x for x in res if x.get("out") == j["out"]), None)
        if r and r.get("ok"):
            Path(j["out"]).with_suffix(".json").write_text(json.dumps({"prompt": j["prompt"], "seed": r.get("seed", j["seed"]), "model": model,
                                                                  "cut": r.get("cut"), "seconds": r.get("seconds")}))
    return res


def reshape(work: Path, clips: List[str]) -> List[Dict]:
    """Re-cut clips from their saved raw fits (loop choice, in-place, settling), without tracking or fitting again:
    for after a change to track_fit.shape_clip."""
    res = []
    for clip in clips:
        if not (work / "fit" / f"{clip}_raw.npz").exists():
            continue
        kind, seconds, _ = MOTION.get(clip, ("oneshot", 1.2, ""))
        cmd = [_py(), "-I", _ANIM / "track_fit.py", "--work", work, "--clip", clip, "--kind", kind, "--reshape"]
        if seconds:
            cmd += ["--seconds", seconds]
        o = _run(cmd, f"reshape {clip}")
        res.append(json.loads([l for l in o.splitlines() if l.startswith("{")][-1]))
    return res


def recut(work: Path, limit: float = 0.04) -> Dict[str, float]:
    """Clips whose video has a cut (the creature jumps between two frames; untrackable) lose their video and fitted
    clip, so the next run re-rolls them (wan_video retries seeds until a take is clean). Returns the scores."""
    out = _run([_py(), "-I", _ANIM / "cut_check.py", work], "cut check")
    scores = json.loads(out.strip().splitlines()[-1])
    for clip, score in scores.items():
        meta = work / "video" / f"{clip}.json"
        if meta.exists() and json.loads(meta.read_text()).get("cut") is not None:
            continue  # made with the cut check: already the cleanest of its re-rolls
        if score >= limit:
            for f in (work / "video" / f"{clip}.mp4", work / "video" / f"{clip}.json", work / "clips" / f"{clip}.npz"):
                f.unlink(missing_ok=True)
            print(f"[ANIM] {work.name}/{clip}: cut {score:.3f}, will re-roll", file=sys.stderr, flush=True)
    return scores


def fit_motions(work: Path, clips: List[str], redo: bool = False, body: str = "quadruped") -> List[Dict]:
    res = []
    for clip in clips:
        video = work / "video" / f"{clip}.mp4"
        out = work / "clips" / f"{clip}.npz"
        if not video.exists():
            res.append({"ok": False, "clip": clip, "error": "no video"})
            continue
        if out.exists() and not redo and out.stat().st_mtime > video.stat().st_mtime:
            continue
        kind, seconds, _ = MOTION.get(clip, ("oneshot", 1.2, ""))
        cmd = [_py(), "-I", _ANIM / "track_fit.py", "--work", work, "--video", video, "--clip", clip, "--kind", kind]
        if seconds:
            cmd += ["--seconds", seconds]
        if body == "hover":
            cmd += ["--hover"]
        try:
            with acquire_gpu(f"fit {clip}"):
                o = _run(cmd, f"fit {clip}", timeout=3600)
            res.append(json.loads([l for l in o.splitlines() if l.startswith("{")][-1]))
        except Exception as exc:  # noqa: BLE001
            res.append({"ok": False, "clip": clip, "error": str(exc)[-800:]})
    return res


def build(work: Path, out_glb: Path) -> Path:
    out_glb = Path(out_glb).resolve()
    out_glb.parent.mkdir(parents=True, exist_ok=True)
    _blender("build", work, out_glb, label="build")
    return out_glb


def preview(glb: Path, png: Path) -> Path:
    """One row per clip, four moments each."""
    from PIL import Image, ImageDraw
    png = Path(png).resolve()
    _blender("preview", Path(glb).resolve(), png, label="preview")
    tmp = png.with_name(png.stem + "_frames")
    rows = json.loads((tmp / "rows.json").read_text())
    size = 240
    sheet = Image.new("RGB", (size * 4 + 90, size * len(rows)), (22, 24, 30))
    d = ImageDraw.Draw(sheet)
    for r, (name, frames) in enumerate(rows):
        d.text((6, r * size + size // 2), name, fill=(220, 220, 230))
        for i, f in enumerate(frames):
            sheet.paste(Image.open(f).convert("RGB").resize((size, size)), (90 + i * size, r * size))
    sheet.save(png)
    shutil.rmtree(tmp, ignore_errors=True)
    return png


MAX_PX = 6.0  # a clip whose fit misses its tracks by more than this (mean, pixels) is filmed again
# ...and one that hardly moves (90th percentile over joints of each joint's largest turn, degrees): video models often
# keep a creature nearly still, which fits perfectly and looks like nothing in game
MIN_SWING = {"move": 12, "attack": 15, "attack2": 15, "special": 12, "hit": 8, "death": 20, "idle2": 10}


def _fit_px(work: Path, clip: str) -> Optional[float]:
    f = work / "fit" / f"{clip}.json"
    return json.loads(f.read_text()).get("mean_px") if f.exists() else None


def _swing(work: Path, clip: str) -> Optional[float]:
    f = work / "clips" / f"{clip}.npz"
    if not f.exists():
        return None
    import numpy as np
    q = np.load(f)["rot"]
    ang = np.degrees(2 * np.arccos(np.clip(np.abs(q[..., 0]), 0, 1)))
    return round(float(np.percentile(ang.max(0), 90)), 1)


def _take_score(work: Path, clip: str, max_px: float):
    """Better takes sort higher: one the fit follows first, then the one that moves more. Choosing between takes,
    a fit a little past max_px still counts as followed (a big 63-degree lunge at 7.7 px beats a 0.6 px take that
    barely moves); a clip is only re-filmed past max_px itself."""
    px, sw = _fit_px(work, clip), _swing(work, clip)
    return (px is not None and px <= 1.4 * max_px, sw or 0.0, -(px or 99.0))


def reroll_bad_fits(work: Path, texts: Dict[str, str], body: str, *, steps: int = 20, seed: int = 7, rounds: int = 2,
                    max_px: float = MAX_PX, min_swing: Optional[Dict[str, float]] = None) -> List[Dict]:
    """Clips the fit couldn't follow (the video redrew or spun the creature in ways the cut check missed), or that
    barely move, are filmed again with new seeds and refitted, up to `rounds` times; the best take is kept (one the
    fit follows, then the one with the most motion)."""
    min_swing = MIN_SWING if min_swing is None else min_swing
    log: List[Dict] = []
    take = lambda c: [work / "video" / f"{c}.mp4", work / "video" / f"{c}.json", work / "clips" / f"{c}.npz",  # noqa: E731
                      work / "fit" / f"{c}.json", work / "fit" / f"{c}_raw.npz", work / "fit" / f"{c}_check.png"]

    def needs(c):
        px, sw = _fit_px(work, c), _swing(work, c)
        return (px or 0) > max_px or (sw is not None and sw < min_swing.get(c, 0))
    for r in range(1, rounds + 1):
        bad = {c: (_fit_px(work, c), _swing(work, c), _take_score(work, c, max_px)) for c in texts if needs(c)}
        if not bad:
            break
        seeds = {}
        for i, c in enumerate(bad):
            meta = work / "video" / f"{c}.json"
            # onward from the seed of the take being replaced: same prompt + same seed films the same clip again
            last = json.loads(meta.read_text()).get("seed", seed + i) if meta.exists() else seed + i
            seeds[c] = int(last) + 5000
            for f in take(c):
                if f.exists():
                    shutil.copy2(f, f.with_name(f.name + ".prev"))
            for f in take(c)[:2]:
                f.unlink(missing_ok=True)
        make_videos(work, {c: texts[c] for c in bad}, steps=steps, seeds=seeds)
        fit_motions(work, list(bad), body=body, redo=True)
        for c, (px0, sw0, score0) in bad.items():
            px1, sw1 = _fit_px(work, c), _swing(work, c)
            kept = "new" if px1 is not None and _take_score(work, c, max_px) > score0 else "old"
            for f in take(c):
                prev = f.with_name(f.name + ".prev")
                if kept == "old" and prev.exists():
                    shutil.move(str(prev), str(f))
                prev.unlink(missing_ok=True)
            log.append({"clip": c, "round": r, "before": [px0, sw0], "after": [px1, sw1], "kept": kept})
            print(f"[ANIM] {work.name}/{c}: re-filmed, fit {px0} -> {px1} px, swing {sw0} -> {sw1} deg, kept the {kept} take",
                  file=sys.stderr, flush=True)
    return log


def animate(src: Path, out_glb: Path, desc: str, *, body: str = "quadruped", work: Optional[Path] = None,
            clips: Optional[List[str]] = None, prompts: Optional[Dict[str, str]] = None, only: Optional[List[str]] = None,
            redo: Optional[List[str]] = None, steps: int = 20, seed: int = 7) -> Dict[str, Any]:
    """The whole chain for one mesh. `prompts` overrides a clip's motion text (still wrapped with the creature
    description and the locked-camera line); `only` runs just those stages; `redo` re-runs stages despite the cache."""
    src, out_glb = Path(src), Path(out_glb)
    work = Path(work or out_glb.with_suffix("").as_posix() + "_anim").resolve()
    work.mkdir(parents=True, exist_ok=True)
    clips = clips or DEFAULT_CLIPS
    only, redo = set(only or STAGES), set(redo or [])
    report: Dict[str, Any] = {"work": str(work)}
    want = lambda s, f: s in only and (s in redo or not (work / f).exists())  # noqa: E731
    if want("prep", "norm.glb"):
        prep(src, work)
    if want("rig", "rig.npz"):
        report["rig"] = rig(work, seed=12345 + seed - 7)
        if (work / "frame0.png").exists():
            overlay(work)
    if want("render", "frame0.png") or ("render" in only and (work / "norm.glb").stat().st_mtime > (work / "frame0.png").stat().st_mtime):
        render(work)
    texts = {c: clip_prompt(c, desc, body, (prompts or {}).get(c)) for c in clips}
    if "video" in only:
        if any((work / "video").glob("*.mp4")):
            report["cuts"] = recut(work)  # clips made before the cut check, or that slipped past it
        report["video"] = make_videos(work, texts, steps=steps, seed=seed, redo="video" in redo)
    if "fit" in only:
        report["fit"] = fit_motions(work, clips, redo="fit" in redo or "video" in redo, body=body)
        if "video" in only:
            report["rerolls"] = reroll_bad_fits(work, texts, body, steps=steps, seed=seed)
    if "build" in only:
        report["glb"] = str(build(work, out_glb))
        report["preview"] = str(preview(out_glb, work / "preview.png"))
    (work / "report.json").write_text(json.dumps(report, indent=1))
    return report


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", nargs="?", type=Path)
    ap.add_argument("out", nargs="?", type=Path)
    ap.add_argument("--desc", default="the creature")
    ap.add_argument("--body", default="quadruped", choices=["biped", "quadruped", "crawler", "hover", "serpent"])
    ap.add_argument("--work", type=Path)
    ap.add_argument("--clips", default=",".join(DEFAULT_CLIPS))
    ap.add_argument("--only", default="")
    ap.add_argument("--redo", default="")
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args(argv)
    if a.status or not a.src:
        print(json.dumps(status(), indent=1))
        return 0
    split = lambda s: [x.strip() for x in s.split(",") if x.strip()] or None  # noqa: E731
    rep = animate(a.src, a.out, a.desc, body=a.body, work=a.work, clips=split(a.clips), only=split(a.only), redo=split(a.redo),
                  steps=a.steps, seed=a.seed)
    print(json.dumps(rep, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
