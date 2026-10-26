"""Image -> short video of the thing in it acting out a prompt: Wan2.2-TI2V-5B through diffusers, sized for the 11 GB 2080 Ti.
Runs in the animation venv (AAMT_ANIM_HOME, default E:\\tools\\anim\\.venv); anim_client.make_videos drives it.

    python wan_video.py --jobs jobs.json

jobs.json: {"width": 832, "height": 480, "model": "fast", "steps": 24, "guidance": 5.0,
            "jobs": [{"image": "frame0.png", "prompt": "...", "out": "attack.mp4", "frames": 49, "seed": 1}]}

model "fast" (default): FastWan2.2-TI2V-5B (FastVideo's DMD distillation of the same model), three fixed denoising
steps and no classifier-free guidance, so about a sixteenth of the base model's work; "base": Wan2.2-TI2V-5B with
`steps` UniPC steps at `guidance`.

How it fits: the umT5 text encoder runs once on the CPU in fp32 (fp16 T5 overflows) and its embeddings are cached
next to each output; the transformer is a Q8_0 GGUF (5.4 GB) dequantised to fp16 layer by layer; the VAE stays fp32
and decodes in tiles. Each job writes <out>.progress (step, seconds) as it goes. One JSON line per job on stdout
({"ok", "out", "seconds"}), then a summary line.
"""
import argparse, gc, hashlib, json, os, sys, time
from pathlib import Path

import torch

# Plain folders under the shared HF cache (snapshot symlinks need a privilege agent shells lack). See ANIMATION.md.
LOCAL = Path(os.environ.get("HF_HOME") or r"D:\hf-cache") / "local"
MODEL = os.environ.get("AAMT_WAN_MODEL") or str(LOCAL / "Wan2.2-TI2V-5B-Diffusers")
GGUF = {"base": os.environ.get("AAMT_WAN_GGUF") or str(LOCAL / "Wan2.2-TI2V-5B-GGUF" / "Wan2.2-TI2V-5B-Q8_0.gguf"),
        "fast": os.environ.get("AAMT_FASTWAN_GGUF") or str(LOCAL / "FastWan2.2-TI2V-5B-GGUF" / "FastWan2.2-TI2V-5B-q8_0-diffusers.gguf")}
# (Green-Sky/FastWan2.2-TI2V-5B-FullAttn-GGUF q8_0, put into the ComfyUI-GGUF tensor layout with gguf_reshape.py)
DEV = "cuda" if torch.cuda.is_available() else "cpu"
# Wan's own negative prompt, plus what breaks motion transfer: cuts, camera moves, extra limbs, things appearing
NEGATIVE = ("vivid colours, overexposed, static, blurry details, subtitles, text, watermark, worst quality, low quality, "
            "jpeg artifacts, ugly, deformed, disfigured, extra limbs, fused limbs, extra heads, morphing, melting, "
            "camera movement, camera pan, zoom, cut, scene change, cluttered background, multiple creatures")


# A clip the model "cuts" (the creature jumps to a new pose or place between two frames, or a slab of something
# wipes across), or where the creature fades away, can't be tracked through: re-roll it with another seed, up to RETRIES times, and keep the cleanest.
# A cut is one frame-to-frame change far above its neighbours'; frame 0 -> 1 is skipped (our render vs the model's
# own look always shifts the tone a little).
CUT, RETRIES = 0.04, 2


def cut_score(vid):
    import numpy as np
    vid = np.asarray(vid, np.float32)
    # the creature fading out or leaving the frame is as untrackable as a cut: its pixels (anything not near-white
    # background) dropping below 40% of the first frame's count scores 1
    fg = (vid.min(-1) < 0.82).mean((1, 2))
    if fg[0] > 0 and fg.min() < 0.4 * fg[0]:
        return 1.0
    d = np.abs(np.diff(vid, axis=0)).mean((1, 2, 3))
    worst = 0.0
    for t in range(1, len(d)):
        nb = np.r_[d[max(0, t - 3):t], d[t + 1:t + 4]]
        if d[t] > 6 * max(float(np.median(nb)), 1e-4):
            worst = max(worst, float(d[t]))
    return worst


class DMDScheduler:
    """FastVideo's DMD sampler in the shape of a diffusers scheduler, so WanImageToVideoPipeline can drive it: at each
    of the fixed timesteps predict the clean latent (x0 = x_t - sigma * v for flow matching), then noise it afresh to
    the next timestep; the last prediction is the result."""
    order = 1
    init_noise_sigma = 1.0

    def __init__(self, steps=(1000, 757, 522), seed=0):
        self.steps = steps
        self.config = type("cfg", (), {"num_train_timesteps": 1000})()
        self.gen = torch.Generator("cpu").manual_seed(seed)
        self.timesteps = torch.tensor(steps)

    def set_timesteps(self, num_inference_steps=None, device=None, **_):
        self.timesteps = torch.tensor(self.steps, device=device)

    def step(self, model_output, timestep, sample, return_dict=False, **_):
        i = int((self.timesteps == timestep).nonzero()[0])
        sigma = float(self.steps[i]) / 1000.0
        x0 = sample.float() - sigma * model_output.float()
        if i + 1 < len(self.steps):
            s2 = float(self.steps[i + 1]) / 1000.0
            noise = torch.randn(sample.shape, generator=self.gen, dtype=torch.float32).to(sample.device)
            x0 = (1 - s2) * x0 + s2 * noise
        return (x0.to(sample.dtype),)


def embed_prompts(prompts, cache_dir: Path):
    """{prompt: tensor} from the cache, encoding the missing ones with umT5 on the CPU."""
    out, todo = {}, []
    for p in prompts:
        f = cache_dir / f"emb_{hashlib.sha1(p.encode()).hexdigest()[:16]}.pt"
        if f.exists():
            out[p] = torch.load(f)
        else:
            todo.append((p, f))
    if todo:
        from transformers import AutoTokenizer, UMT5EncoderModel
        t = time.time()
        tok = AutoTokenizer.from_pretrained(MODEL, subfolder="tokenizer")
        enc = UMT5EncoderModel.from_pretrained(MODEL, subfolder="text_encoder", torch_dtype=torch.float32).eval()
        for p, f in todo:
            ids = tok([p], padding="max_length", max_length=512, truncation=True, add_special_tokens=True, return_attention_mask=True, return_tensors="pt")
            n = int(ids.attention_mask.sum())
            with torch.no_grad():
                h = enc(ids.input_ids, ids.attention_mask).last_hidden_state[0, :n]
            emb = torch.cat([h, h.new_zeros(512 - n, h.shape[1])])[None]  # the pipeline pads the same way
            torch.save(emb, f)
            out[p] = emb
        del enc
        gc.collect()
        print(json.dumps({"info": f"encoded {len(todo)} prompt(s) on the CPU in {time.time() - t:.0f}s"}), flush=True)
    return out


def _accept_squeezed_gguf():
    """Some GGUF converters (the FastWan one among them) store Wan's (1, 6, dim) modulation tables as (6, dim). Same
    data: put the leading 1s back instead of refusing the file."""
    from diffusers.quantizers.gguf.gguf_quantizer import GGUFQuantizer
    if getattr(GGUFQuantizer, "_aamt_patched", False):
        return
    orig = GGUFQuantizer.check_quantized_param_shape

    def check(self, name, current, loaded):
        try:
            return orig(self, name, current, loaded)
        except ValueError:
            extra = len(current.shape) - len(loaded.shape)
            if extra > 0 and all(s == 1 for s in current.shape[:extra]):
                loaded.data = loaded.data.reshape((1,) * extra + tuple(loaded.data.shape))
                return orig(self, name, current, loaded)
            raise
    GGUFQuantizer.check_quantized_param_shape = check
    GGUFQuantizer._aamt_patched = True


def load_pipeline(model):
    from diffusers import AutoencoderKLWan, GGUFQuantizationConfig, WanImageToVideoPipeline, WanTransformer3DModel
    _accept_squeezed_gguf()
    tr = WanTransformer3DModel.from_single_file(GGUF[model], config=MODEL, subfolder="transformer",
                                                quantization_config=GGUFQuantizationConfig(compute_dtype=torch.float16),
                                                torch_dtype=torch.float16)
    vae = AutoencoderKLWan.from_pretrained(MODEL, subfolder="vae", torch_dtype=torch.float32)
    pipe = WanImageToVideoPipeline.from_pretrained(MODEL, transformer=tr, vae=vae, text_encoder=None, tokenizer=None,
                                                   image_encoder=None, image_processor=None, expand_timesteps=True,
                                                   torch_dtype=torch.float16)
    pipe.enable_model_cpu_offload()
    # The offload order (...transformer->vae) never sends the VAE back after it encodes the first frame, so its 2.8 GB
    # would sit beside the transformer and push the card into swapping (a 3 s step took minutes). Send it back as soon
    # as the latents are prepared; its hook brings it back to decode.
    prepare = pipe.prepare_latents

    def prepare_then_free_vae(*a, **k):
        out = prepare(*a, **k)
        pipe.vae.to("cpu")
        torch.cuda.empty_cache()
        return out
    object.__setattr__(pipe, "prepare_latents", prepare_then_free_vae)
    try:
        pipe.vae.enable_tiling()
    except Exception:
        pass
    return pipe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", required=True)
    a = ap.parse_args()
    spec = json.loads(Path(a.jobs).read_text(encoding="utf-8"))
    jobs = spec["jobs"]
    W, H = int(spec.get("width", 832)), int(spec.get("height", 480))
    model = spec.get("model", "fast")
    steps, cfg = (3, 1.0) if model == "fast" else (int(spec.get("steps", 24)), float(spec.get("guidance", 5.0)))
    t0 = time.time()
    by_dir = {}
    for j in jobs:
        by_dir.setdefault(str(Path(j["out"]).parent), set()).update([j["prompt"], NEGATIVE])
    emb = {}
    for d, ps in by_dir.items():
        Path(d).mkdir(parents=True, exist_ok=True)
        emb.update(embed_prompts(sorted(ps), Path(d)))
    pipe = load_pipeline(model)
    load_s = time.time() - t0
    from diffusers.utils import export_to_video
    from PIL import Image
    done = 0
    for j in jobs:
        t = time.time()
        try:
            img = Image.open(j["image"]).convert("RGB").resize((W, H), Image.LANCZOS)
            frames = int(j.get("frames", 49))
            frames = (frames - 1) // 4 * 4 + 1  # the VAE packs 4 frames per latent after the first
            seed = int(j.get("seed", 0))
            prog = Path(j["out"]).with_suffix(".progress")

            def on_step(_pipe, i, _t, kw, prog=prog, t=t):  # <clip>.progress, for watching long runs
                prog.write_text(f"step {i + 1}/{steps} {time.time() - t:.0f}s")
                return kw
            best = None
            for attempt in range(1 + RETRIES):
                s_ = seed + 1000 * attempt
                if model == "fast":
                    object.__setattr__(pipe, "scheduler", DMDScheduler(seed=s_))
                res = pipe(image=img, prompt_embeds=emb[j["prompt"]].to(DEV, torch.float16),
                           negative_prompt_embeds=emb[NEGATIVE].to(DEV, torch.float16) if cfg > 1 else None,
                           height=H, width=W, num_frames=frames, guidance_scale=cfg, num_inference_steps=steps,
                           generator=torch.Generator("cpu").manual_seed(s_), output_type="np", callback_on_step_end=on_step)
                vid = res.frames[0]
                if not (vid == vid).all():
                    raise RuntimeError("NaN frames (fp16 overflow)")
                cut = cut_score(vid)
                if best is None or cut < best[0]:
                    best = (cut, vid, s_)
                if cut < CUT:
                    break
                print(json.dumps({"info": f"{Path(j['out']).name}: seed {s_} has a cut ({cut:.3f}), re-rolling"}), flush=True)
            cut, vid, seed = best
            export_to_video(list(vid), j["out"], fps=24)
            prog.write_text(f"done {time.time() - t:.0f}s")
            done += 1
            print(json.dumps({"ok": True, "out": j["out"], "seconds": round(time.time() - t, 1), "seed": seed, "cut": round(cut, 3)}), flush=True)
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            print(json.dumps({"ok": False, "out": j["out"], "error": f"{type(e).__name__}: {e}"[:600]}), flush=True)
    peak = torch.cuda.max_memory_allocated() // (1 << 20) if torch.cuda.is_available() else 0
    print(json.dumps({"summary": True, "model": model, "done": done, "of": len(jobs), "load_s": round(load_s),
                      "total_s": round(time.time() - t0), "peak_vram_mb": peak}), flush=True)


if __name__ == "__main__":
    sys.exit(main())
