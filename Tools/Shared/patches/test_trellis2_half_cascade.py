"""CPU-only check of the half-precision cascade fix: runs TRELLIS.2's own
`sample_shape_slat_cascade` with stand-in models that hold float16 weights and refuse data of
another dtype the way a real layer does ("mat1 and mat2 must have the same dtype"). No weights
are loaded and the GPU is not touched.

Run with the TRELLIS venv, from anywhere:
    D:\\trellis2\\code\\venv\\Scripts\\python.exe test_trellis2_half_cascade.py [--root D:\\trellis2]
Exit 0: the cascade path hands every model data in its own dtype. Exit 1: it does not (the
unpatched install), and the message says where.
"""
import os
import sys
import types

root = sys.argv[sys.argv.index('--root') + 1] if '--root' in sys.argv else r'D:\trellis2'
sys.path.insert(0, os.path.join(root, 'code'))
os.environ.setdefault('SPARSE_BACKEND', 'spconv')
os.environ.setdefault('ATTN_BACKEND', 'sdpa')

import torch  # noqa: E402
import torch.nn as nn  # noqa: E402

from trellis2.modules.sparse import SparseTensor  # noqa: E402
from trellis2.pipelines.trellis2_image_to_3d import Trellis2ImageTo3DPipeline  # noqa: E402

HALF = torch.float16


class Flow(nn.Module):
    """Stands in for a flow model: float16 weights, and a real Linear over the conditioning."""

    def __init__(self, name):
        super().__init__()
        self.name, self.in_channels = name, 8
        self.read_cond = nn.Linear(16, 4).half()
        self.read_feats = nn.Linear(8, 8).half()


class Sampler:
    def sample(self, model, noise, cond=None, neg_cond=None, **kwargs):
        for label, value in (('cond', cond), ('neg_cond', neg_cond)):
            if value is not None:
                try:
                    model.read_cond(value)                 # float32 here is the reported error
                except RuntimeError as error:
                    raise RuntimeError(f'{model.name}: {label} arrives as {value.dtype}: {error}')
        return types.SimpleNamespace(samples=noise)        # float32, like the real sampler's output


class Decoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.from_latent = nn.Linear(8, 8).half()

    def upsample(self, x, upsample_times):
        try:
            self.from_latent(x.feats)
        except RuntimeError as error:
            raise RuntimeError(f'shape decoder upsample: latent arrives as {x.feats.dtype}: {error}')
        return x.coords


def main():
    pipeline = object.__new__(Trellis2ImageTo3DPipeline)
    pipeline.low_vram = False
    pipeline._device = torch.device('cpu')
    pipeline.shape_slat_sampler = Sampler()
    pipeline.shape_slat_sampler_params = {}
    pipeline.shape_slat_normalization = {'std': [1.0] * 8, 'mean': [0.0] * 8}
    pipeline.models = {'shape_slat_decoder': Decoder()}
    coords = torch.tensor([[0, 1, 2, 3], [0, 4, 5, 6], [0, 7, 8, 9]], dtype=torch.int32)
    cond = {'cond': torch.randn(1, 5, 16), 'neg_cond': torch.zeros(1, 5, 16)}        # float32, as get_cond gives it
    try:
        slat, resolution = pipeline.sample_shape_slat_cascade(dict(cond), dict(cond), Flow('low-resolution flow model'),
                                                             Flow('high-resolution flow model'), 512, 1024, coords)
    except RuntimeError as error:
        print('FAIL:', error)
        return 1
    print(f'OK: the cascade path ran with float16 models and float32 inputs (resolution {resolution}, {slat.feats.shape[0]} tokens)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
