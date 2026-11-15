"""refart command line (run with the refart venv; refart_client.py does that for you).

  generate --prompt P --out F [--ref IMG ...] [--ref-scale 0.6] [--control IMG --control-mode lineart|depth|tile|canny]
           [--width 832 --height 1216 --steps 30 --guidance 6 --seed N --negative N]
  inpaint  --image IMG --mask MASK --prompt P --out F [--ref IMG ...] [--strength 0.95] [--grow 8] [--blur 8]
  edit     --image IMG --instruction TEXT --out F [--steps 24 --guidance 2.5 --seed N]        (FLUX.1 Kontext)
  segment  --image IMG --phrase TEXT [--phrase ...] --out-dir DIR [--box-threshold 0.3]
           writes <phrase>_<i>.png masks and segment.json (boxes, scores)
  layers   --spec SPEC.json --out-dir DIR [--preview DIR]                                    (see layers.py)
  overlay  --base IMG --instruction TEXT --phrase TEXT --out F [--mode edit|inpaint]          (see layers.py)
  status   prints what is installed
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate")
    g.add_argument("--prompt", required=True)
    g.add_argument("--out", type=Path, required=True)
    g.add_argument("--ref", type=Path, action="append", default=[])
    g.add_argument("--ref-scale", type=float, default=0.6)
    g.add_argument("--control", type=Path)
    g.add_argument("--control-mode", default="lineart")
    g.add_argument("--control-scale", type=float, default=0.6)
    g.add_argument("--width", type=int, default=832)
    g.add_argument("--height", type=int, default=1216)
    g.add_argument("--steps", type=int, default=30)
    g.add_argument("--guidance", type=float, default=6.0)
    g.add_argument("--seed", type=int, default=0)
    g.add_argument("--negative", default="")

    i = sub.add_parser("inpaint")
    i.add_argument("--image", type=Path, required=True)
    i.add_argument("--mask", type=Path, required=True)
    i.add_argument("--prompt", required=True)
    i.add_argument("--out", type=Path, required=True)
    i.add_argument("--ref", type=Path, action="append", default=[])
    i.add_argument("--ref-scale", type=float, default=0.5)
    i.add_argument("--strength", type=float, default=0.95)
    i.add_argument("--steps", type=int, default=30)
    i.add_argument("--guidance", type=float, default=6.0)
    i.add_argument("--seed", type=int, default=0)
    i.add_argument("--negative", default="")
    i.add_argument("--grow", type=int, default=8)
    i.add_argument("--blur", type=int, default=8)

    e = sub.add_parser("edit")
    e.add_argument("--image", type=Path, required=True)
    e.add_argument("--instruction", required=True)
    e.add_argument("--out", type=Path, required=True)
    e.add_argument("--steps", type=int, default=24)
    e.add_argument("--guidance", type=float, default=2.5)
    e.add_argument("--seed", type=int, default=0)
    e.add_argument("--ref", type=Path, help="reference picture shown beside the image (e.g. the item's game icon)")

    s = sub.add_parser("segment")
    s.add_argument("--image", type=Path, required=True)
    s.add_argument("--phrase", action="append", required=True)
    s.add_argument("--out-dir", type=Path, required=True)
    s.add_argument("--box-threshold", type=float, default=0.3)

    l = sub.add_parser("layers")
    l.add_argument("--spec", type=Path, required=True)
    l.add_argument("--out-dir", type=Path, required=True)
    l.add_argument("--preview", type=Path)

    o = sub.add_parser("overlay")
    o.add_argument("--base", type=Path, required=True)
    o.add_argument("--instruction", required=True)
    o.add_argument("--phrase", required=True)
    o.add_argument("--out", type=Path, required=True)
    o.add_argument("--mode", choices=["edit", "inpaint"], default="edit")
    o.add_argument("--region", default="", help="inpaint: area to repaint (default: --phrase); edit: area for --clip-region")
    o.add_argument("--clip-region", action="store_true",
                   help="edit mode: keep the cut inside --region's box (stops repainted torso/back leaking into the layer)")
    o.add_argument("--seed", type=int, default=0)
    o.add_argument("--work", type=Path)
    o.add_argument("--ref", type=Path, help="edit mode: reference picture shown beside the base (the item's icon)")
    o.add_argument("--protect", type=Path, help="inpaint mode: mask PNG (white) of pixels never repainted, e.g. the face")
    o.add_argument("--region-grow", type=float, default=0.0, help="inpaint+protect: grow the region by this x its height")
    o.add_argument("--inpaint-ref", type=Path, help="inpaint+protect: IP-Adapter reference (e.g. a Kontext render of the item)")
    o.add_argument("--ref-scale", type=float, default=0.4)
    o.add_argument("--negative", default="")

    sub.add_parser("status")
    a = ap.parse_args(argv)

    import engine
    if a.cmd == "generate":
        engine.generate(a.prompt, a.out, a.ref, a.ref_scale, a.control, a.control_mode, a.control_scale,
                        a.width, a.height, a.steps, a.guidance, a.seed, a.negative)
        print(json.dumps({"out": str(a.out)}))
    elif a.cmd == "inpaint":
        engine.inpaint(a.image, a.mask, a.prompt, a.out, a.ref, a.ref_scale, a.strength, a.steps, a.guidance,
                       a.seed, a.negative, a.grow, a.blur)
        print(json.dumps({"out": str(a.out)}))
    elif a.cmd == "edit":
        engine.edit(a.image, a.instruction, a.out, a.steps, a.guidance, a.seed, ref=a.ref)
        print(json.dumps({"out": str(a.out)}))
    elif a.cmd == "segment":
        from PIL import Image
        import numpy as np
        a.out_dir.mkdir(parents=True, exist_ok=True)
        res = engine.segment(a.image, a.phrase, a.box_threshold)
        summary = {}
        for ph, found in res.items():
            items = []
            for k, d in enumerate(found):
                name = f"{''.join(c if c.isalnum() else '_' for c in ph)}_{k}.png"
                if "mask" in d:
                    Image.fromarray((d["mask"] * 255).astype(np.uint8)).save(a.out_dir / name)
                items.append({"file": name, "box": [round(v, 1) for v in d["box"]], "score": round(d["score"], 3)})
            summary[ph] = items
        (a.out_dir / "segment.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
        print(json.dumps(summary))
    elif a.cmd == "layers":
        import layers
        print(json.dumps(layers.split(a.spec, a.out_dir, a.preview)))
    elif a.cmd == "overlay":
        import layers
        print(json.dumps(layers.overlay(a.base, a.instruction, a.phrase, a.out, a.mode, a.region,
                                        a.seed, a.work, clip=a.clip_region, ref=a.ref,
                                        protect=a.protect, region_grow=a.region_grow,
                                        inpaint_ref=a.inpaint_ref, ref_scale=a.ref_scale, negative=a.negative)))
    elif a.cmd == "status":
        print(json.dumps(status(), indent=1))
    return 0


def status() -> dict:
    import os
    from huggingface_hub import try_to_load_from_cache
    import engine
    def has(repo, f):
        r = try_to_load_from_cache(repo, f)
        return isinstance(r, str) and os.path.exists(r)
    import torch
    return {
        "cuda": torch.cuda.is_available(),
        "sdxl": has(engine.SDXL, "model_index.json"),
        "ip_adapter": has(engine.IP_REPO, f"{engine.IP_SUB}/{engine.IP_WEIGHT}"),
        "controlnet_union_promax": has(engine.UNION_REPO, "diffusion_pytorch_model_promax.safetensors"),
        "grounding_dino": has(engine.DINO, "model.safetensors"),
        "sam2": has(engine.SAM2, "model.safetensors"),
        "kontext_gguf": has(*engine.KONTEXT_GGUF),
        "flux_parts": has(engine.SCHNELL, "text_encoder_2/config.json"),
    }


if __name__ == "__main__":
    sys.exit(main())
