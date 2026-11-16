#!/usr/bin/env python3
"""New CrossMod hulls: SD3.5 concept -> TRELLIS mesh -> SD PBR skins -> Ucupaint bake, Transcendence only.

Uses the tx_ai_pipeline stages directly (no Starfield publishing, Shared/Concepts untouched). Output per id in
Output/HdPipeline/<id>/: concept.png, mesh/<id>.glb, skins/, bake/<id>_baked.glb (same layout as the existing packs,
so tx_facings_batch.py renders them like the others).

Stages run in GPU order, one server at a time: all concepts (SD) -> all meshes (TRELLIS) -> all skins (SD) ->
all bakes (Blender). Finished outputs are skipped, so a run can be resumed.

  python tx_generate_hulls.py [--id scEvolvedFirefly ...] [--stage concept|mesh|skins|bake|all]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "Output" / "HdPipeline"
#   Sandboxed shells set NoDefaultCurrentDirectoryInExePath=1, so cmd stops finding scripts in the current folder and
#   the TRELLIS launcher ("call projectorz-internal.bat") fails with "not recognized". Clear it for our children.
os.environ.pop("NoDefaultCurrentDirectoryInExePath", None)
sys.path.insert(0, str(HERE))
import tx_ai_pipeline as tx  # noqa: E402

STYLE = ("original living biometal starship, silver-white organic armor plates over a dark carapace, cyan "
         "bioluminescent veins and a glowing core, sleek alien-organic hull, readable silhouette from above, "
         "evolved techno-organic design")

HULLS = {
    "scEvolvedFirefly": "evolved light transport: compact rounded hull with two swollen cargo pods on the flanks, "
                        "small cockpit dome at the front, twin rear thrusters",
    "scEvolvedWolfen": "evolved gunship: aggressive predator hull with forward-swept claw-like wings, "
                       "twin forward cannons, narrow snout",
    "scEvolvedSapphire": "evolved yacht: elegant slim teardrop hull, large faceted crystal canopy like a gemstone, "
                         "graceful fin pair at the rear",
    "scEvolvedCenturion": "evolved heavy gunship: broad armored wedge hull with thick layered shoulder plates, "
                          "single heavy spinal cannon, wide stance",
    "scEvolvedSpectre": "evolved stealth gunship: thin angular blade-like hull, translucent membrane wings, "
                        "low profile, faint glow",
    "scEvolvedHullbreaker": "evolved ramming gunship: massive reinforced horned prow made for ramming, "
                            "compact body behind the ram, heavy engines",
    "scEvolvedBattery": "evolved broadside gunship: wide flat hull with rows of weapon pods along both sides, "
                        "short nose, armored spine",
    "scEvolvedCourser": "evolved fast broadside gunship: long narrow hull, swept side fins carrying weapon pods, "
                        "streamlined racing shape",
    "scEvolvedArchitect": "evolved construction carrier: large hull with folded manipulator arms, an open "
                          "fabrication bay in the belly, crane-like spines",
    "scCarrierSwarmConstruct": "tiny swarm drone: small insectoid construct with stubby wings and a single glowing eye",
    "scArchitectConstruct": "small builder drone: compact body with two grasping manipulator claws and a welding light",
    "scLeviathanSegment": "one short body segment cut from the middle of a long sea-serpent leviathan: a thick "
                          "cylindrical armored vertebra section, crystalline cyan spikes along the spine, overlapping "
                          "silver scale plates, no head, no tail, no legs, no wings",
    #   2026-11-13: the old head pack (scLeviathanBase) was a reconstruction of a whole coiled serpent; as the head
    #   of a segmented ship it read as a dark forked stick. This is a head only, in the segment's style.
    "scLeviathanHead": "the severed head and short neck stub of a colossal sea-serpent leviathan, nothing else: "
                       "a long wedge-shaped armored dragon skull with overlapping silver scale plates, a crown of "
                       "crystalline cyan spikes sweeping back from the brow, two long swept-back horns, glowing cyan "
                       "eyes, closed jaws with a pointed snout, the neck ends in a flat round socket, "
                       "no body, no tail, no legs, no wings",
}

#   concept image-to-image references (style/shape anchor for parts of an existing hull)
REFERENCE = {
    "scLeviathanSegment": (HERE / "References" / "leviathan_nova_drift_concept.png", 0.85),
    "scLeviathanHead": (OUT / "scLeviathanSegment" / "concept.png", 0.88),
}

#   2026-11-13: biometal FAUNA sculpts in the style of the Starfield mod's scFauna*_trellis_ref.png stills (grey clay
#   creature on white, three-quarter view). These are rendered with --skin biometal, so no colour is wanted here.
CLAY_STYLE = ("grey clay sculpture of a single alien space creature, matte grey clay material, ZBrush sculpt, "
              "three-quarter view, whole creature in frame, centered, plain white studio background, soft studio "
              "lighting, highly detailed armored plates, no colour, no text")
CLAY = {
    "scFaunaArchitectV2": "swimming manta-ray-shaped creature seen from above and slightly to the side, wide flat "
                          "wing fins, a pointed head at the front, a long thin tail at the back, and its whole back "
                          "covered in clusters of large round spore bulbs like a garden of bubbles, no legs, no claws",
    "scFaunaSpawn": "a swimming tadpole, seen from the side: one big smooth round armored head with large eyes, "
                    "a long flat paddle tail behind it, no legs, no arms, no feet, streamlined",
    "scFaunaMote": "small floating spore mote: a round seed-pod body covered in overlapping scales with a pointed "
                   "front tip, three short trailing tendrils at the back, simple chunky shapes",
}
CLAY_REF = HERE.parent.parent.parent / "Steam" / "steamapps" / "common" / "Starfield" / "ArcaneConduit" / "assets" / "Transcendence" / "Concepts"
for _k, _r in (("scFaunaArchitectV2", "scFaunaBattery_trellis_ref.png"), ("scFaunaSpawn", "scFaunaViper_trellis_ref.png"),
               ("scFaunaMote", "scFaunaStealth_trellis_ref.png")):
    HULLS[_k] = CLAY[_k]
    REFERENCE[_k] = (CLAY_REF / _r, 0.82)

#   seed offsets, to re-roll one concept without touching the others (delete concept.png, bump the number)
RESEED = {}

SKIN = {
    "theme": "living biometal hull plate",
    "colors": ["#0e1a24", "#2a6f8f", "#7fe3ff", "#e8f4ff"],
    "pattern": "organic armor plates with bioluminescent seams",
    "style": "seamless tileable PBR albedo, flat lighting",
    "glow": True,
}


def paths(i: str) -> dict:
    d = OUT / i
    return {"dir": d, "concept": d / "concept.png", "glb": d / "mesh" / f"{i}.glb", "skins": d / "skins",
            "baked": d / "bake" / f"{i}_baked.glb"}


def stage_concepts(ids):
    todo = [i for i in ids if not paths(i)["concept"].is_file()]
    if not todo:
        return
    os.environ["AAMT_SD_KEEP_SERVER"] = "1"
    tx.prepare(image=True, mesh=False, keep_server=True)
    try:
        for i in todo:
            p = paths(i)
            prompt = (f"{CLAY_STYLE}, {CLAY[i]}" if i in CLAY else f"{tx.TRELLIS_CONCEPT_PROMPT} {STYLE}, {HULLS[i]}")
            ref, strength = REFERENCE.get(i, (None, 0.65))
            ok = tx.generate_image(prompt, p["concept"], kind="default", size=768,
                                   seed=101 + zlib.crc32(i.encode()) % 1000 + RESEED.get(i, 0),
                                   reference_image=str(ref) if ref else None, image_strength=strength)
            print(f"[hulls] concept {i}: {'ok' if ok else 'FAILED'}", flush=True)
    finally:
        tx.release(force=True)


def stage_meshes(ids):
    todo = [i for i in ids if paths(i)["concept"].is_file() and not paths(i)["glb"].is_file()]
    if not todo:
        return
    os.environ["AAMT_TRELLIS_KEEP_SERVER"] = "1"
    tx.prepare(image=False, mesh=True, keep_server=True)
    try:
        for i in todo:
            p = paths(i)
            ok = tx.generate_mesh(p["concept"], p["glb"], autostart=True)
            print(f"[hulls] mesh {i}: {'ok' if ok else 'FAILED'}", flush=True)
    finally:
        tx.release(force=True)


def stage_skins(ids):
    todo = [i for i in ids if paths(i)["glb"].is_file() and not (paths(i)["skins"] / f"{i}_diffuse.png").is_file()]
    if not todo:
        return
    os.environ["AAMT_SD_KEEP_SERVER"] = "1"
    tx.prepare(image=True, mesh=False, keep_server=True)
    try:
        for i in todo:
            p = paths(i)
            spec = dict(SKIN, description=f"seamless biometal material for {HULLS[i][:60]}",
                        referenceImage=str(p["concept"]), imageStrength=0.45)
            tx.generate_pbr_skins(p["skins"], i, spec, quality="standard", use_sd=True,
                                  seed=17 + zlib.crc32(i.encode()) % 1000, glow=True)
            print(f"[hulls] skins {i}: ok", flush=True)
    finally:
        tx.release(force=True)


def stage_bake(ids):
    for i in ids:
        p = paths(i)
        if p["baked"].is_file() or not (p["skins"] / f"{i}_diffuse.png").is_file():
            continue
        r = tx.bake_onto_mesh(p["glb"], p["dir"] / "bake", skin_dir=p["skins"], name=i, size=1024, ao=False,
                              blender=tx.find_blender(), stop_servers=True)
        print(f"[hulls] bake {i}: {'ok' if p['baked'].is_file() else 'FAILED ' + json.dumps(r)[:300]}", flush=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", action="append")
    ap.add_argument("--stage", default="all", choices=["concept", "mesh", "skins", "bake", "all"])
    a = ap.parse_args(argv)
    ids = a.id or list(HULLS)
    for i in ids:
        if i not in HULLS:
            raise SystemExit(f"unknown id {i}")
    if a.stage in ("concept", "all"):
        stage_concepts(ids)
    if a.stage in ("mesh", "all"):
        stage_meshes(ids)
    if a.stage in ("skins", "all"):
        stage_skins(ids)
    if a.stage in ("bake", "all"):
        stage_bake(ids)
    for i in ids:
        p = paths(i)
        print(f"{i}: concept={p['concept'].is_file()} mesh={p['glb'].is_file()} baked={p['baked'].is_file()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
