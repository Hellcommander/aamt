#!/usr/bin/env python3
"""Batch 120-facing renders with the engine-correct renderer (blender_tx_facings.py) + tx_build_facings.py.

Registry: facings_registry.json  { id: {glb, noseYaw, cell, poses:[idle, ...]} }

  python tx_facings_batch.py --probe [--id X ...]      4-yaw probes + contact sheets (to set noseYaw by eye)
  python tx_facings_batch.py --render [--id X ...]     120 frames per pose -> sheet + 8-bit mask + XML, then tester
  python tx_facings_batch.py --list

Output: Output/Facings/<id>/  (<id>.jpg, <id>Mask.bmp, <id>_<pose>.jpg ..., <id>.image.xml, test.xml, contact/)
Poses share the idle framing (--fit-radius), so overlays line up with the idle sheet.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
REG = HERE / "facings_registry.json"
OUT = HERE / "Output" / "Facings"
WORK = HERE / "Output" / "Facings" / "_frames"
BLENDER = Path(r"D:\tools\Blender Foundation\Blender 5.0\blender.exe")
sys.path.insert(0, str(HERE))
import tx_build_facings  # noqa: E402


def load_reg() -> dict:
    return json.loads(REG.read_text(encoding="utf-8")) if REG.exists() else {}


def save_reg(reg: dict) -> None:
    REG.write_text(json.dumps(reg, indent=1), encoding="utf-8")


def blender(args: list[str]) -> int:
    p = subprocess.run([str(BLENDER), "-b", "-P", str(HERE / "blender_tx_facings.py"), "--", *args],
                       capture_output=True, text=True, errors="replace")
    if p.returncode != 0:
        print(p.stdout[-1500:], p.stderr[-1500:])
    return p.returncode


def orient_args(e: dict) -> list[str]:
    """registry: "orient": "pca" (tilted image-to-3D meshes), "flip": true (view the other side)"""
    out = []
    if e.get("orient"):
        out += ["--orient", e["orient"]]
    if e.get("viewAxis"):
        out += ["--view-axis", str(e["viewAxis"])]
    if e.get("skin"):
        out += ["--skin", e["skin"]]
    if e.get("deepGlow") is not None:
        out += ["--deep-glow", str(e["deepGlow"])]
    if e.get("palette"):
        out += ["--palette", e["palette"]]
    if e.get("flip"):
        out += ["--flip"]
    return out


def probe(asset: str, e: dict) -> Path:
    d = WORK / f"{asset}_probe"
    blender(["--model", e["glb"], "--out", str(d), "--probe", "--size", "384", *orient_args(e)])
    ims = [Image.open(d / f"f{i:03d}.png").convert("RGBA").resize((192, 192)) for i in range(4)]
    sheet = Image.new("RGB", (4 * 198, 214), (40, 40, 60))
    dr = ImageDraw.Draw(sheet)
    for i, im in enumerate(ims):
        bg = Image.new("RGB", im.size, (40, 40, 60)); bg.paste(im, mask=im.getchannel("A"))
        sheet.paste(bg, (i * 198, 20)); dr.text((i * 198 + 4, 3), f"{asset} yaw {i * 90}", fill=(255, 255, 0))
    sheet.save(d / "contact.png")
    return d / "contact.png"


def test_xml(out: Path, asset: str, cell: int, sheets: list[str]) -> Path:
    lines = ['<?xml version="1.0" encoding="utf-8"?>', '<TranscendenceExtension UNID="0xE7E5F000" apiVersion="59" name="facing test">']
    for i, s in enumerate(sheets):
        lines.append(f'\t<Image UNID="0x{0xE7E5F100 + i:08X}" bitmap="{s}.jpg" bitmask="{s}Mask.bmp" />')
        lines.append(f'\t<ShipClass UNID="0x{0xE7E5F200 + i:08X}" class="{s}" rotationCount="120">')
        lines.append(f'\t\t<Image imageID="0x{0xE7E5F100 + i:08X}" imageWidth="{cell}" imageHeight="{cell}" rotationCount="120" rotationColumns="12"/>')
        lines.append('\t</ShipClass>')
    lines.append('</TranscendenceExtension>')
    p = out / "test.xml"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def render(asset: str, e: dict) -> dict:
    out = OUT / asset
    out.mkdir(parents=True, exist_ok=True)
    sheets, fit = [], 0.0
    for pose in e.get("poses", ["idle"]):
        d = WORK / f"{asset}_{pose}"
        args = ["--model", e["glb"], "--out", str(d), "--frames", "120", "--size", str(max(256, e["cell"] * 4)),
                "--nose-yaw", str(e["noseYaw"]), "--pose", pose, *orient_args(e)]
        if fit:
            args += ["--fit-radius", str(fit)]
        t0 = time.time()
        if blender(args) != 0:
            return {"id": asset, "ok": False, "error": f"blender failed on pose {pose}"}
        if pose == "idle":
            fit = json.loads((d / "render.json").read_text())["radius"]
        name = asset if pose == "idle" else f"{asset}_{pose}"
        tx_build_facings.build(d, out, name, e["cell"], 12, 95, None)
        sheets.append(name)
        print(f"  {asset} {pose}: {time.time() - t0:.0f}s")
    t = test_xml(out, asset, e["cell"], sheets)
    p = subprocess.run([sys.executable, "-I", str(HERE / "tx_image_tester.py"), str(t), "--contact", str(out / "contact")],
                       capture_output=True, text=True, errors="replace")
    summary = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr[-300:]
    (out / "tester.txt").write_text(p.stdout + p.stderr, encoding="utf-8")
    return {"id": asset, "ok": p.returncode == 0, "sheets": sheets, "tester": summary}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--id", action="append")
    a = ap.parse_args(argv)
    reg = load_reg()
    ids = a.id or sorted(reg)
    if a.list:
        for i in ids:
            print(i, reg[i])
    if a.probe:
        for i in ids:
            print("probe", i, probe(i, reg[i]))
    if a.render:
        results = []
        for i in ids:
            if reg[i].get("noseYaw") is None:
                print(f"  {i}: noseYaw not set, skipped"); continue
            r = render(i, reg[i]); results.append(r)
            print(f"[facings] {i}: {'OK' if r['ok'] else 'FAIL'} {r.get('tester', r.get('error', ''))}", flush=True)
        (OUT / "batch_report.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
