"""Rebuild the Magi-Tech sounds the listener hears as poor fits, from the same library clips, with the agent and the bench.

For every manifest entry whose purpose match is under --min-match (from a saved audit, or measured here), the clips named
in the manifest are loaded (by path, so a rebuilt library index still finds them), the agent lays them out (impact / boom
for hits, plain for the rest), several seeds are rendered, the listener picks, and the result is written as OGG 48 kHz
mono into the loose folder (the dev copy the sealed archive is built from) and the manifest entry updated. Nothing here
is AI-generated: the bench is deterministic processing; the listener only scores.

Usage: python magitech_audio_redo.py <mod> <loose folder> [--audit audit.json] [--min-match 0.15] [--only a,b] [--candidates 4] [--dry]
       python magitech_audio_redo.py <mod> <loose folder> --add new_sounds.json [--candidates 4]

--add makes sounds the mod references but never had: new_sounds.json is a list of {"path", "purpose", "kind"
(one-shot | loop), "seconds", optional "group", "query"}. The agent finds library clips for the purpose by name
(own, reference and direct tiers; the restricted Ovani tier is never picked for new sounds), the entry joins the
manifest with those clips as its references, and it is then built exactly like a remake (same DSP, same 0.22
similarity bar, the listener picks), so the new file is no copy of any clip.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Shared"))
import audio_bench as bench  # noqa: E402
from audio_rebuild import rebuild  # noqa: E402
from audio_listener import Listener  # noqa: E402
from audio_agent import Agent  # noqa: E402
from audio_asset_library import AudioLibrary, load_asset_audio  # noqa: E402

MAX_CORR = 0.22


def find_record(lib, finder_cache, ref):
    rec = lib.get(ref.get("id") or "")
    if rec is not None:
        return rec
    inner = (ref.get("clip") or ref.get("inner") or "").replace("\\", "/")
    if not finder_cache:
        for r in lib.records:
            finder_cache[r.inner] = r
            finder_cache.setdefault(r.inner.split("/")[-1].lower(), r)
    if inner in finder_cache:
        return finder_cache[inner]
    for k, r in finder_cache.items():
        if "/" in k and (k.endswith("/" + inner) or inner.endswith("/" + k)):
            return r
    return finder_cache.get(inner.split("/")[-1].lower())


def to_ogg(path, x, sr_out, channels):
    y = bench.resample(x, bench.SR, sr_out) if sr_out != bench.SR else x
    if channels == 1:
        y = y.mean(axis=1, keepdims=True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ext = os.path.splitext(path)[1].lower()
    sf.write(path, np.clip(y, -1, 1), sr_out, format="OGG" if ext == ".ogg" else "WAV", subtype="VORBIS" if ext == ".ogg" else "PCM_16")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mod"); ap.add_argument("loose")
    ap.add_argument("--audit"); ap.add_argument("--min-match", type=float, default=0.15)
    ap.add_argument("--only", default=""); ap.add_argument("--candidates", type=int, default=4); ap.add_argument("--dry", action="store_true"); ap.add_argument("--failed-only", action="store_true", help="only entries whose check is not ok"); ap.add_argument("--all", action="store_true", help="every entry: remake the whole set")
    ap.add_argument("--add", help="json list of new sounds to make (see the module doc)")
    a = ap.parse_args(argv)
    manifest_path = os.path.join(a.mod, "sfx", "AUDIO_MANIFEST.json")
    manifest = json.load(open(manifest_path, encoding="utf-8"))
    by_path = {e["path"].lstrip("/"): e for e in manifest["files"]}
    only = set(filter(None, a.only.split(",")))
    lib = listener = agent = None
    if a.add:
        lib = AudioLibrary(); lib.load()
        listener = Listener()
        agent = Agent(library=lib, listener=listener)
        only = set()
        for job in json.load(open(a.add, encoding="utf-8")):
            path = job["path"].lstrip("/")
            if path in by_path:
                # already made (it ships in the sealed archive): --add never remakes an existing sound;
                # use --only for a deliberate remake
                print(f"exists {path}: skipped")
                continue
            recs = []
            for role in ("main", "body", "tail"):
                recs += agent.find_clips(job.get("query") or job["purpose"], role=role, k=2, exclude=[r.id for r in recs],
                                         tiers=("own", "reference", "direct"))
            recs = recs[:4]
            if not recs:
                print(f"SKIP {path}: no library clip fits '{job['purpose']}'")
                continue
            entry = {"path": "/" + path, "group": job.get("group", path.split("/")[-2]), "replaces_reference": [],
                     "purpose": job["purpose"], "prompt": job["purpose"], "kind": job.get("kind", "one-shot"),
                     "format": "OGG", "duration_s": float(job.get("seconds", 1.0)), "sample_rate": 48000, "channels": 1,
                     "tiers": sorted({r.license_tier() for r in recs}),
                     "references": [{"id": r.id, "pack": r.pack, "clip": r.inner, "license": r.license_tier()} for r in recs]}
            manifest["files"].append(entry)
            by_path[path] = entry
            only.add(path)
            print(f"new {path}: {[r.inner.split('/')[-1] for r in recs]}")
        if not only:
            print("nothing new to make")
            return 0
    audit = {r["sound"]: r for r in json.load(open(a.audit, encoding="utf-8"))} if a.audit else {}
    todo = []
    for path, e in by_path.items():
        short = os.path.splitext(os.path.basename(path))[0]
        if only and short not in only and path not in only:
            continue
        if a.all:
            pass
        elif a.failed_only:
            if e.get("check", {}).get("ok", True):
                continue
        elif not only and audit and audit.get(path, {}).get("match", 1.0) >= a.min_match:
            continue
        todo.append((path, e))
    print(f"{len(todo)} sounds to rebuild")
    if a.dry:
        for p, e in todo:
            print(f"  {p}: {e['purpose']}  <- {[r['clip'].split('/')[-1] for r in e['references']]}")
        return 0
    if lib is None:
        lib = AudioLibrary(); lib.load()
        listener = Listener()
        agent = Agent(library=lib, listener=listener)
    cache = {}
    done = failed = 0
    for path, e in todo:
        t = time.time()
        clips = {}
        for i, ref in enumerate(e["references"]):
            rec = find_record(lib, cache, ref)
            if rec is None:
                continue
            x, sr = load_asset_audio(rec, sr=bench.SR, max_seconds=8.0)
            clips[f"clip{i + 1}"] = bench.fx_trim(bench.to_stereo(x), bench.SR, None)
            ref["id"], ref["pack"], ref["clip"] = rec.id, rec.pack, rec.inner
        if not clips:
            print(f"SKIP {path}: none of its clips are in the index"); failed += 1
            continue
        purpose = e.get("purpose") or e.get("prompt") or ""
        n = int(bench.SR * float(e.get("duration_s") or 1.0))
        ordered, cfg, plan_why = agent.rebuild_plan(purpose, list(clips.values()), n / bench.SR)
        y, info = rebuild(os.path.splitext(os.path.basename(path))[0], ordered, n, purpose, listener, max_corr=MAX_CORR, tries=a.candidates * 3, cfg=cfg)
        if y is None:
            print(f"FAIL {path}: {info}"); failed += 1
            continue
        corr = info["corr"]
        kind = info["stage"]
        chosen = info.get("listen") or {"match": 0.0, "clean": 0.0, "total": 0.0}
        base_total = listener.score(list(clips.values())[0], bench.SR, purpose)["total"] if listener is not None else 0.0
        out = os.path.join(a.loose, path if path.startswith("sfx") else os.path.join("interface_magitech_sounds", os.path.basename(path)))
        to_ogg(out, y, int(e.get("sample_rate") or 48000), int(e.get("channels") or 1))
        e["engine"] = "audio_rebuild (CPU): the manifest's clips pitched, layered, all-passed and EQ'd until far from every clip; the listener picks the try"
        e["rebuild"] = {"stage": info["stage"], "semitones": info["semitones"], "candidates": info["candidates"], "agent_plan": plan_why}
        e.pop("recipe", None)
        e["check"] = {"source_corr": round(corr, 3), "closest": "", "ok": corr <= MAX_CORR}
        e["listen"] = {"match": chosen["match"], "clean": chosen["clean"], "total": chosen["total"], "base_total": base_total}
        e["duration_s"] = round(len(y) / bench.SR, 2)
        done += 1
        print(f"{path}: {kind}, corr {corr:.3f}, listen {chosen['total']:+.3f} (match {chosen['match']:.3f}), {time.time() - t:.0f} s")
    manifest["updated"] = time.strftime("%Y-%m-%d %H:%M")
    manifest["about"] = (manifest["about"].split(" Sounds rebuilt")[0] + " Sounds rebuilt on " + manifest["updated"] + " carry a 'recipe' and 'listen' block: the audio bench rebuilt them from the same clips with the local audio agent choosing the layout and the listener the seed. The sounds ship sealed in sfx/magitech/sounds.mtsa (audio_seal.py).")
    json.dump(manifest, open(manifest_path, "w", encoding="utf-8"), indent=1)
    print(f"{done} rebuilt, {failed} failed; manifest updated. Re-seal with audio_seal.py to ship them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
