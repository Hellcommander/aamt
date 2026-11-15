"""refart engine: reference-image art generation, edits, inpainting and part segmentation.

Runs in its own venv (AAMT_REFART_HOME, default E:\\tools\\refart\\.venv; see REFART.md). One pipeline is
resident at a time (11 GB RTX 2080 Ti); every GPU call holds the toolkit GPU lock (Common/gpu_hub.py).

  generate  SDXL base + IP-Adapter Plus (reference images keep the character/style)
            + optional ControlNet Union ProMax (canny/lineart/depth/tile guidance from a control image)
  inpaint   SDXL + ControlNet Union ProMax repaint mode + IP-Adapter: repaint only the masked area,
            so a fitted garment or a filled-in scalp lines up with the rest of the picture
  edit      FLUX.1 Kontext dev (GGUF Q4_K_M transformer; CLIP/T5/VAE from FLUX.1-schnell, Apache-2.0):
            instruction edits ("make the character wear a filthy toga") that keep everything else
  segment   Grounding DINO (text -> boxes) + SAM 2.1 (box -> exact mask)
  matte     BiRefNet foreground alpha (shared with the particle stage)

Weights live in the shared HF cache (HF_HOME, D:\\hf-cache); nothing here downloads on its own except the
first-use helpers ensure_union() / ensure_kontext_config().
"""
from __future__ import annotations

import gc
import json
import os
import shutil
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
from PIL import Image, ImageFilter

TOOLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TOOLS / "Common"))
sys.path.insert(0, str(TOOLS / "Shared"))

HF_HOME = Path(os.environ.get("HF_HOME") or r"D:\hf-cache")
os.environ.setdefault("HF_HOME", str(HF_HOME))
LOCAL = HF_HOME / "local"

SDXL = "stabilityai/stable-diffusion-xl-base-1.0"
SDXL_VAE = "madebyollin/sdxl-vae-fp16-fix"
IP_REPO, IP_SUB, IP_WEIGHT, IP_ENCODER = "h94/IP-Adapter", "sdxl_models", "ip-adapter-plus_sdxl_vit-h.safetensors", "models/image_encoder"
UNION_REPO = "xinsir/controlnet-union-sdxl-1.0"
UNION_LOCAL = LOCAL / "controlnet-union-sdxl-promax"
SCHNELL = "black-forest-labs/FLUX.1-schnell"
KONTEXT_GGUF = ("QuantStack/FLUX.1-Kontext-dev-GGUF", "flux1-kontext-dev-Q4_K_M.gguf")
KONTEXT_CONFIG = LOCAL / "flux-kontext-dev-config"
DINO = "IDEA-Research/grounding-dino-base"
SAM2 = "facebook/sam2.1-hiera-large"

# ControlNet Union ProMax control_mode ids
MODES = {"openpose": 0, "depth": 1, "hed": 2, "scribble": 2, "canny": 3, "lineart": 3, "normal": 4,
         "segment": 5, "tile": 6, "repaint": 7}

DEV = "cuda" if torch.cuda.is_available() else "cpu"
F16 = torch.float16

_pipe = None
_pipe_kind: Optional[str] = None
_seg = None


def log(msg: str) -> None:
    print(f"[refart] {msg}", file=sys.stderr, flush=True)


@contextmanager
def gpu(label: str):
    try:
        from gpu_hub import acquire_gpu
    except Exception:  # noqa: BLE001  (lock is optional outside the toolkit)
        yield
        return
    with acquire_gpu("refart " + label):
        yield


def free() -> None:
    """Drop every resident model (call before another stage needs the card)."""
    global _pipe, _pipe_kind, _seg
    _pipe = None
    _pipe_kind = None
    _seg = None
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


# ------------------------------------------------------------------ local folders built from cached repos

def _snap(repo: str, **kw) -> Path:
    from huggingface_hub import snapshot_download
    return Path(snapshot_download(repo, local_files_only=True, **kw))


def ensure_union() -> None:
    """The ProMax ControlNet as a plain folder diffusers can load (its weights ship under another file name)."""
    if not (UNION_LOCAL / "diffusion_pytorch_model.safetensors").exists():
        src = _snap(UNION_REPO, allow_patterns=["diffusion_pytorch_model_promax.safetensors", "config_promax.json"])
        UNION_LOCAL.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src / "config_promax.json", UNION_LOCAL / "config.json")
        weights = (src / "diffusion_pytorch_model_promax.safetensors").resolve()
        dst = UNION_LOCAL / "diffusion_pytorch_model.safetensors"
        try:
            os.link(weights, dst)  # same volume: no second 2.5 GB copy
        except OSError:
            shutil.copyfile(weights, dst)


def ensure_kontext_config() -> None:
    """The Kontext transformer config: schnell's, with guidance embeddings (dev/Kontext have them)."""
    cfg = KONTEXT_CONFIG / "transformer" / "config.json"
    if not cfg.exists():
        src = _snap(SCHNELL, allow_patterns=["transformer/config.json"]) / "transformer" / "config.json"
        c = json.loads(src.read_text(encoding="utf-8"))
        c["guidance_embeds"] = True  # dev/Kontext have the distilled-guidance embedding, schnell does not
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text(json.dumps(c, indent=2), encoding="utf-8")


# ------------------------------------------------------------------ SDXL family

def _sdxl(kind: str):
    """kind: 'plain' | 'control' | 'inpaint' (all with IP-Adapter Plus loaded)."""
    global _pipe, _pipe_kind
    if _pipe_kind == kind:
        return _pipe
    free()
    from diffusers import AutoencoderKL
    vae = AutoencoderKL.from_pretrained(SDXL_VAE, torch_dtype=F16)
    common = dict(vae=vae, torch_dtype=F16, variant="fp16", use_safetensors=True)
    if kind == "plain":
        from diffusers import StableDiffusionXLPipeline
        pipe = StableDiffusionXLPipeline.from_pretrained(SDXL, **common)
    else:
        ensure_union()
        from diffusers import ControlNetUnionModel
        cn = ControlNetUnionModel.from_pretrained(str(UNION_LOCAL), torch_dtype=F16)
        if kind == "control":
            from diffusers import StableDiffusionXLControlNetUnionPipeline as P
        else:
            from diffusers import StableDiffusionXLControlNetUnionInpaintPipeline as P
        pipe = P.from_pretrained(SDXL, controlnet=cn, **common)
    pipe.load_ip_adapter(IP_REPO, subfolder=IP_SUB, weight_name=IP_WEIGHT, image_encoder_folder=IP_ENCODER)
    pipe.enable_model_cpu_offload()
    if hasattr(pipe, "enable_vae_tiling"):
        pipe.enable_vae_tiling()
    else:
        pipe.vae.enable_tiling()
    _pipe, _pipe_kind = pipe, kind
    log(f"loaded SDXL ({kind})")
    return pipe


def _fit(w: int, h: int, side: int = 1024) -> Tuple[int, int]:
    """SDXL-friendly size near `side` megapixels with the same aspect, multiples of 64."""
    s = (side * side / (w * h)) ** 0.5
    return max(512, int(round(w * s / 64)) * 64), max(512, int(round(h * s / 64)) * 64)


def _control_image(img: Image.Image, mode: str) -> Image.Image:
    if mode in ("canny", "lineart"):
        import cv2
        a = np.asarray(img.convert("RGB"))
        e = cv2.Canny(cv2.cvtColor(a, cv2.COLOR_RGB2GRAY), 80, 180)
        return Image.fromarray(np.dstack([e] * 3))
    return img.convert("RGB")


def generate(prompt: str, out: Path, refs: Sequence[Path] = (), ref_scale: float = 0.6,
             control: Optional[Path] = None, control_mode: str = "lineart", control_scale: float = 0.6,
             width: int = 832, height: int = 1216, steps: int = 30, guidance: float = 6.0, seed: int = 0,
             negative: str = "") -> Path:
    ref_imgs = [Image.open(r).convert("RGB") for r in refs]
    kind = "control" if control else "plain"
    pipe = _sdxl(kind)
    pipe.set_ip_adapter_scale(ref_scale if ref_imgs else 0.0)
    kw = dict(prompt=prompt, negative_prompt=negative or None, width=width, height=height,
              num_inference_steps=steps, guidance_scale=guidance,
              generator=torch.Generator("cpu").manual_seed(seed))
    kw["ip_adapter_image"] = ref_imgs[0] if len(ref_imgs) == 1 else (ref_imgs or Image.new("RGB", (224, 224)))
    if control:
        c = Image.open(control).convert("RGB").resize((width, height), Image.LANCZOS)
        kw.update(control_image=[_control_image(c, control_mode)], control_mode=[MODES[control_mode]],
                  controlnet_conditioning_scale=control_scale)
    with gpu(f"generate {out.name}"):
        img = pipe(**kw).images[0]
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


def inpaint(image: Path, mask: Path, prompt: str, out: Path, refs: Sequence[Path] = (), ref_scale: float = 0.5,
            strength: float = 0.95, steps: int = 30, guidance: float = 6.0, seed: int = 0, negative: str = "",
            grow: int = 8, blur: int = 8) -> Path:
    """Repaint the white area of `mask` on `image`; the rest is pasted back unchanged (pixel-exact)."""
    src = Image.open(image).convert("RGB")
    m = Image.open(mask).convert("L")
    if grow:
        m = m.filter(ImageFilter.MaxFilter(grow * 2 + 1))
    w, h = _fit(*src.size)
    s = src.resize((w, h), Image.LANCZOS)
    mm = m.resize((w, h), Image.NEAREST)
    masked = Image.composite(Image.new("RGB", (w, h), (0, 0, 0)), s, mm)
    ref_imgs = [Image.open(r).convert("RGB") for r in refs] or [src]
    pipe = _sdxl("inpaint")
    pipe.set_ip_adapter_scale(ref_scale)
    with gpu(f"inpaint {out.name}"):
        img = pipe(prompt=prompt, negative_prompt=negative or None, image=s, mask_image=mm,
                   control_image=[masked], control_mode=[MODES["repaint"]], strength=strength,
                   width=w, height=h, num_inference_steps=steps, guidance_scale=guidance,
                   ip_adapter_image=ref_imgs[0], generator=torch.Generator("cpu").manual_seed(seed)).images[0]
    img = img.resize(src.size, Image.LANCZOS)
    soft = m.filter(ImageFilter.GaussianBlur(blur)) if blur else m
    res = Image.composite(img, src, soft)
    out.parent.mkdir(parents=True, exist_ok=True)
    res.save(out)
    return out


# ------------------------------------------------------------------ FLUX.1 Kontext

def _fp32_vae(vae) -> None:
    """The pipeline hands the VAE tensors in the transformer's dtype; run it in fp32 and hand fp16 back."""
    enc, dec = vae.encode, vae.decode

    def encode(x, *a, **k):
        r = enc(x.to(torch.float32), *a, **k)
        dist = r.latent_dist if hasattr(r, "latent_dist") else r[0]
        dist.mean, dist.std = dist.mean.to(x.dtype), dist.std.to(x.dtype)
        dist.var, dist.logvar = dist.var.to(x.dtype), dist.logvar.to(x.dtype)
        dist.parameters = dist.parameters.to(x.dtype)
        return r

    def decode(z, *a, **k):
        return dec(z.to(torch.float32), *a, **k)

    vae.encode, vae.decode = encode, decode


def _fp16_clamp(transformer) -> None:
    """FLUX overflows fp16 (the last double block's image stream turns inf on step 2, then every latent is NaN).
    Clamping module outputs to the fp16 range keeps it finite; tested 2026-11-08 on the 2080 Ti."""
    def hook(_mod, _inp, out):
        outs = out if isinstance(out, tuple) else (out,)
        fixed = tuple(torch.nan_to_num(o, nan=0.0, posinf=65000.0, neginf=-65000.0).clamp_(-65000.0, 65000.0)
                      if torch.is_tensor(o) and o.dtype == torch.float16 else o for o in outs)
        return fixed if isinstance(out, tuple) else fixed[0]
    for name, mod in transformer.named_modules():
        if name and name.count(".") <= 3:
            mod.register_forward_hook(hook)


def _kontext():
    global _pipe, _pipe_kind
    if _pipe_kind == "kontext":
        return _pipe
    free()
    ensure_kontext_config()
    from diffusers import FluxKontextPipeline, FluxTransformer2DModel, GGUFQuantizationConfig, FlowMatchEulerDiscreteScheduler
    from huggingface_hub import hf_hub_download
    gguf = hf_hub_download(*KONTEXT_GGUF, local_files_only=True)
    dtype = torch.bfloat16 if os.environ.get("REFART_KONTEXT_BF16") == "1" else F16
    tr = FluxTransformer2DModel.from_single_file(
        gguf, quantization_config=GGUFQuantizationConfig(compute_dtype=dtype),
        config=str(KONTEXT_CONFIG), subfolder="transformer", torch_dtype=dtype)
    sched = FlowMatchEulerDiscreteScheduler(num_train_timesteps=1000, shift=3.0, use_dynamic_shifting=True,
                                            base_shift=0.5, max_shift=1.15, base_image_seq_len=256,
                                            max_image_seq_len=4096)
    # Text encoders stay on the CPU in bf16 (T5 overflows in fp16; the 9.5 GB encoder would not fit beside
    # the transformer anyway). VAE in fp32 on the GPU when decoding.
    pipe = FluxKontextPipeline.from_pretrained(SCHNELL, transformer=tr, scheduler=sched, torch_dtype=torch.bfloat16)
    pipe.vae.to(torch.float32)
    _fp32_vae(pipe.vae)
    if dtype == F16:
        _fp16_clamp(pipe.transformer)
    _pipe, _pipe_kind = pipe, "kontext"
    log(f"loaded Kontext ({dtype})")
    return pipe


def stitch_ref(src: Image.Image, ref: Image.Image, frac: float = 0.5) -> Image.Image:
    """src with a reference panel to its right (Kontext reads both; the edit is cropped back to src).
    The panel is frac of src's width, src-tall, the reference fitted in its middle on src's corner colour."""
    pw = max(16, int(src.width * frac))
    bg = src.getpixel((2, 2))
    panel = Image.new("RGB", (pw, src.height), bg)
    r = ref.convert("RGBA")
    k = min((pw * 0.9) / r.width, (src.height * 0.6) / r.height)
    r = r.resize((max(1, int(r.width * k)), max(1, int(r.height * k))), Image.NEAREST if max(ref.size) <= 64 else Image.LANCZOS)
    panel.paste(r, ((pw - r.width) // 2, (src.height - r.height) // 2), r)
    out = Image.new("RGB", (src.width + pw, src.height), bg)
    out.paste(src, (0, 0))
    out.paste(panel, (src.width, 0))
    return out


def edit(image: Path, instruction: str, out: Path, steps: int = 24, guidance: float = 2.5, seed: int = 0,
         keep_size: bool = True, ref: Optional[Path] = None) -> Path:
    src = Image.open(image).convert("RGB")
    orig = src
    if ref is not None and Path(ref).is_file():
        src = stitch_ref(orig, Image.open(ref))
    pipe = _kontext()
    with torch.no_grad():
        pe, ppe, _ids = pipe.encode_prompt(prompt=instruction, prompt_2=None, device="cpu")
    dtype = pipe.transformer.dtype if pipe.transformer.dtype in (torch.float16, torch.bfloat16) else F16
    with gpu(f"edit {out.name}"):
        pipe.transformer.to(DEV)
        pipe.vae.to(DEV)
        try:
            # Keep the input's framing (Kontext would snap to its own aspect list and shift the figure), so
            # pixels in the edit line up with the source: ~1 MP, sides multiples of 16.
            k = (1024 * 1024 / (src.width * src.height)) ** 0.5
            w16, h16 = max(16, round(src.width * k / 16) * 16), max(16, round(src.height * k / 16) * 16)
            img = pipe(image=src.resize((w16, h16), Image.LANCZOS), width=w16, height=h16, max_area=w16 * h16, _auto_resize=False,
                       prompt_embeds=pe.to(DEV, dtype), pooled_prompt_embeds=ppe.to(DEV, dtype),
                       guidance_scale=guidance, num_inference_steps=steps,
                       generator=torch.Generator("cpu").manual_seed(seed)).images[0]
        finally:
            pipe.transformer.to("cpu")
            pipe.vae.to("cpu")
            torch.cuda.empty_cache()
    if keep_size:
        img = img.resize(src.size, Image.LANCZOS)
    if src is not orig:  # drop the reference panel again
        img = img.crop((0, 0, orig.width, orig.height)) if keep_size else img.crop((0, 0, round(img.width * orig.width / src.width), img.height))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


# ------------------------------------------------------------------ segmentation

def _segmenter():
    global _seg
    if _seg is not None:
        return _seg
    from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor, Sam2Model, Sam2Processor
    dp = AutoProcessor.from_pretrained(DINO)
    dm = AutoModelForZeroShotObjectDetection.from_pretrained(DINO).to(DEV).eval()
    sp = Sam2Processor.from_pretrained(SAM2)
    sm = Sam2Model.from_pretrained(SAM2).to(DEV).eval()
    _seg = (dp, dm, sp, sm)
    return _seg


@torch.no_grad()
def detect(img: Image.Image, phrase: str, box_threshold: float = 0.3, text_threshold: float = 0.25) -> List[Dict]:
    """[{box: [x0,y0,x1,y1], score}] for one phrase, best first."""
    dp, dm, _sp, _sm = _segmenter()
    text = phrase.strip().lower().rstrip(".") + "."
    inputs = dp(images=img, text=text, return_tensors="pt").to(DEV)
    outputs = dm(**inputs)
    res = dp.post_process_grounded_object_detection(outputs, inputs.input_ids, threshold=box_threshold,
                                                    text_threshold=text_threshold, target_sizes=[img.size[::-1]])[0]
    found = [{"box": [float(v) for v in b], "score": float(s)} for b, s in zip(res["boxes"].cpu(), res["scores"].cpu())]
    return sorted(found, key=lambda d: -d["score"])


@torch.no_grad()
def masks_for_boxes(img: Image.Image, boxes: List[List[float]]) -> List[np.ndarray]:
    if not boxes:
        return []
    _dp, _dm, sp, sm = _segmenter()
    inputs = sp(images=img, input_boxes=[boxes], return_tensors="pt").to(DEV)
    outputs = sm(**inputs, multimask_output=False)
    ms = sp.post_process_masks(outputs.pred_masks.cpu(), inputs["original_sizes"].cpu())[0]
    return [ms[i, 0].numpy() > 0.5 for i in range(ms.shape[0])]


def segment(image: Path, phrases: Sequence[str], box_threshold: float = 0.3, max_per_phrase: int = 8) -> Dict[str, List[Dict]]:
    """phrase -> [{box, score, mask (HxW bool)}], boxes de-duplicated (IoU > 0.7 keeps the better one)."""
    img = Image.open(image).convert("RGB")
    out: Dict[str, List[Dict]] = {}
    with gpu(f"segment {Path(image).name}"):
        for ph in phrases:
            found = []
            for d in detect(img, ph, box_threshold):
                if all(_iou(d["box"], k["box"]) < 0.7 for k in found):
                    found.append(d)
                if len(found) >= max_per_phrase:
                    break
            for d, m in zip(found, masks_for_boxes(img, [d["box"] for d in found])):
                d["mask"] = m
            out[ph] = found
    return out


def _iou(a, b) -> float:
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def matte(image: Path) -> np.ndarray:
    """Foreground alpha (BiRefNet, shared with the particle stage), HxW float 0..1."""
    from particles import matte as m
    rgb = np.asarray(Image.open(image).convert("RGB")).astype(np.float32) / 255.0
    with gpu(f"matte {Path(image).name}"):
        a = m.mask(rgb)
    m.free()
    return a
