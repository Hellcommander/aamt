"""Cut-out masks for particle frames: BiRefNet (ZhengPeng7/BiRefNet, MIT) for solid things drawn on a plain backdrop
(debris, shards, coins, leaves), where brightness-as-alpha would eat the dark parts. Glows and smoke drawn on black
don't need it; fx_frames.py derives their alpha from brightness.

Runs in the animation venv (torch, torchvision). The weights and the model's own code are fetched on first use into
<HF_HOME>/local/BiRefNet as a plain folder (hub snapshot symlinks fail with WinError 1314 in agent shells);
particle_client.ensure_matte() also installs the two packages the model code needs (timm, kornia).
"""
import importlib, os, sys
from pathlib import Path

import numpy as np
import torch

REPO = "ZhengPeng7/BiRefNet"
LOCAL = Path(os.environ.get("HF_HOME") or r"D:\hf-cache") / "local"
DIR = Path(os.environ.get("AAMT_BIREFNET") or LOCAL / "BiRefNet")
SIZE = 1024
_model = None


def download() -> Path:
    if not (DIR / "model.safetensors").exists():
        from huggingface_hub import snapshot_download
        snapshot_download(REPO, local_dir=str(DIR), allow_patterns=["*.py", "*.json", "model.safetensors"])
    return DIR


def load():
    """The model on the GPU in fp16 (fp32 on CPU). The repo's code uses a relative import, so it is imported as a
    package named after its folder."""
    global _model
    if _model is not None:
        return _model
    download()
    sys.path.insert(0, str(DIR.parent))
    mod = importlib.import_module(f"{DIR.name}.birefnet")
    from safetensors.torch import load_file
    m = mod.BiRefNet(config=mod.BiRefNetConfig(bb_pretrained=False))
    m.load_state_dict(load_file(str(DIR / "model.safetensors")))
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    m = m.to(dev).eval()
    if dev == "cuda":
        m = m.half()
    _model = m
    return m


@torch.no_grad()
def mask(rgb: np.ndarray) -> np.ndarray:
    """HxWx3 float [0,1] -> HxW float [0,1] foreground alpha."""
    import torch.nn.functional as F
    m = load()
    p = next(m.parameters())
    x = torch.from_numpy(np.ascontiguousarray(rgb.transpose(2, 0, 1))).float()[None]
    x = F.interpolate(x, (SIZE, SIZE), mode="bilinear", align_corners=False)
    mean = torch.tensor([0.485, 0.456, 0.406])[None, :, None, None]
    std = torch.tensor([0.229, 0.224, 0.225])[None, :, None, None]
    x = ((x - mean) / std).to(p.device, p.dtype)
    a = m(x)[-1].sigmoid().float()
    a = F.interpolate(a, rgb.shape[:2], mode="bilinear", align_corners=False)
    return a[0, 0].cpu().numpy().clip(0, 1)


def free():
    global _model
    _model = None
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
