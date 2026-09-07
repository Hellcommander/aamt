#!/usr/bin/env python3
"""Stable Audio 3 clips for every concept mesh id.

Writes:
  Transcendence Output/HdPipeline/{id}/Audio/*.wav   — short clips TX can use
  Starfield Data/Sound/ArcaneConduit/nd_{id}_*.wav   — includes longer 3D beds
    TX cannot spatialize (ArcaneConduit SFSE XAudio2 Play(event, pos, loop))

Run only when TRELLIS/SD are stopped.

  python tx_concept_audio_batch.py
  python tx_concept_audio_batch.py --id scSpaceWhale
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_TX = Path(__file__).resolve().parent
_TOOLS = _TX.parent
_SHARED = _TOOLS / "Shared"
_INDEX = _SHARED / "Concepts" / "index.json"
_OUT = _TX / "Output" / "HdPipeline"
_SF_SND = Path(r"F:\SteamLibrary\steamapps\common\Starfield\Data\Sound\ArcaneConduit")

for _p in (_TX, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import tx_ai_pipeline as tx  # noqa: E402

# (event, duration, archetype, strength, prompt, consumers)
# consumers: "tx" | "starfield" | "both"
Clip = Tuple[str, float, str, float, str, str]


def _clips_for(asset_id: str) -> List[Clip]:
    kind = "ship" if asset_id.startswith("sc") or asset_id.endswith("Ship") else "weapon"
    if "Shield" in asset_id or "Halo" in asset_id or "Siphon" in asset_id:
        kind = "shield"
    name = asset_id
    if kind == "ship":
        manta = "Manta" in name
        clips: List[Clip] = [
            (
                "idle",
                3.0,
                "alien" if ("Whale" in name or "Leviathan" in name or manta) else "ship",
                0.65,
                (
                    f"short soft wing-glide membrane hum of living manta-ray hull {name}, gentle organic resonance, game sfx, no music"
                    if manta
                    else f"short idle hum of living bio-tech hull {name}, subtle organic resonance, game sfx, no music"
                ),
                "both",
            ),
            (
                "fire",
                1.6,
                "magic" if manta else ("impact" if "Horn" in name else "laser"),
                0.55 if manta else 0.6,
                (
                    f"short soft arcane mist breath cone from {name}, deterrent whoosh not a blast, game sfx, no music"
                    if manta
                    else f"short attack call of {name}, punchy space combat sfx, no music"
                ),
                "both",
            ),
            (
                "spatial_loop",
                8.0,
                "ambience",
                0.62,
                (
                    f"looping near-field 3D membrane bed of living manta-ray {name}, soft ventral field drone, seamless game loop, no music"
                    if manta
                    else f"looping near-field 3D ambience of living organism-ship {name}, deep bio-tech drone bed, seamless game loop, no music"
                ),
                "starfield",
            ),
            (
                "proximity",
                2.5,
                "ship",
                0.58,
                (
                    f"short proximity membrane wash when near {name}, spatial game sfx, no music"
                    if manta
                    else f"short proximity whoosh and hull rumble when near {name}, spatial game sfx, no music"
                ),
                "starfield",
            ),
        ]
        if manta:
            clips.extend(
                [
                    (
                        "chorus",
                        2.2,
                        "alien",
                        0.6,
                        f"short resonant song-sac pulse of {name}, long-range sensor chime, game sfx, no music",
                        "both",
                    ),
                    (
                        "field",
                        4.0,
                        "ambience",
                        0.6,
                        f"low gravity thrum of ventral sweep field from {name}, sustained support bed, game sfx, no music",
                        "both",
                    ),
                ]
            )
        return clips
    if kind == "shield":
        return [
            (
                "idle",
                3.0,
                "magic",
                0.62,
                f"short idle barrier hum of living shield {name}, cyan-violet lattice tone, game sfx, no music",
                "both",
            ),
            (
                "fire",
                1.4,
                "magic",
                0.58,
                f"short shield pulse activate of {name}, protective energy hit, game sfx, no music",
                "both",
            ),
            (
                "spatial_loop",
                7.0,
                "ambience",
                0.6,
                f"looping 3D shield field bed for {name}, soft barrier drone, seamless, no music",
                "starfield",
            ),
            (
                "proximity",
                2.2,
                "magic",
                0.55,
                f"short near-field shield shimmer for {name}, spatial sfx, no music",
                "starfield",
            ),
        ]
    # weapon
    return [
        (
            "idle",
            2.5,
            "mech",
            0.6,
            f"short idle charge tick of living weapon {name}, bio-tech mechanism, game sfx, no music",
            "both",
        ),
        (
            "fire",
            1.5,
            "laser",
            0.62,
            f"short fire blast of living weapon {name}, punchy sci-fi shot, game sfx, no music",
            "both",
        ),
        (
            "spatial_loop",
            6.0,
            "ambience",
            0.58,
            f"looping 3D weapon charge bed for {name}, sustained energy coil, seamless, no music",
            "starfield",
        ),
        (
            "proximity",
            2.0,
            "impact",
            0.55,
            f"short muzzle proximity crack for {name}, spatial sfx, no music",
            "starfield",
        ),
    ]


def _load_index() -> Dict[str, str]:
    data = json.loads(_INDEX.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in (data.get("concepts") or {}).items()}


def generate_one(asset_id: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {"id": asset_id, "ok": True, "clips": []}
    tx_dir = _OUT / asset_id / "Audio"
    tx_dir.mkdir(parents=True, exist_ok=True)
    _SF_SND.mkdir(parents=True, exist_ok=True)
    for event, duration, archetype, strength, prompt, consumers in _clips_for(asset_id):
        wav_name = f"{asset_id}_{event}.wav"
        tmp = tx_dir / wav_name
        print(f"[audio] {asset_id}/{event} {duration}s ({consumers})", flush=True)
        try:
            path = tx.generate_audio(
                prompt,
                tmp,
                duration=duration,
                archetype=archetype,
                strength=strength,
                engine="stable-audio",
            )
        except Exception as exc:  # noqa: BLE001
            result["ok"] = False
            result["clips"].append({"event": event, "error": str(exc)})
            print(f"[audio] FAIL {asset_id}/{event}: {exc}", file=sys.stderr)
            continue
        if not path or not Path(path).is_file():
            result["ok"] = False
            result["clips"].append({"event": event, "error": "no output"})
            continue
        entry: Dict[str, Any] = {"event": event, "tx": str(tmp), "consumers": consumers}
        if consumers in ("starfield", "both"):
            sf = _SF_SND / f"nd_{asset_id}_{event}.wav"
            sf.write_bytes(Path(path).read_bytes())
            entry["starfield"] = str(sf)
        result["clips"].append(entry)
    (tx_dir / "audio_manifest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", action="append", default=[])
    args = ap.parse_args(argv)

    # Free GPU servers before SA3
    try:
        tx.release(force=True)
    except Exception:
        pass
    try:
        from trellis_http_client import stop_server

        stop_server(force=True)
    except Exception:
        pass

    print("[audio] ensuring audio stage...", flush=True)
    prep = tx._import_ai().ensure("audio")
    print(json.dumps(prep, indent=2), flush=True)

    index = _load_index()
    ids = args.id or list(index.keys())
    report: List[Dict[str, Any]] = []
    for asset_id in ids:
        print(f"\n==== audio {asset_id} ====", flush=True)
        report.append(generate_one(asset_id))

    out = _OUT / "_audio_batch_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    ok = sum(1 for r in report if r.get("ok"))
    print(f"\n[audio] done {ok}/{len(report)} -> {out}")
    return 0 if ok == len(report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
