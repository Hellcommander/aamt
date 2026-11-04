"""Rewrite a GGUF so every tensor takes the shape its namesake has in a reference GGUF (same data, same quant type).
Different converters lay Wan's weights out differently (stable-diffusion.cpp squeezes the modulation tables to
(6, dim), flattens the patch embedding to (dim*48, 1, 2, 2) and quantizes norm weights); diffusers only loads the
ComfyUI-GGUF layout, so tensors the reference keeps as F16/F32 are dequantized to that type too.

    python gguf_reshape.py <in.gguf> <reference.gguf> <out.gguf>
"""
import sys

import numpy as np
from gguf import GGML_QUANT_SIZES, GGMLQuantizationType, GGUFReader, GGUFWriter
from gguf.quants import dequantize

src, ref, out = sys.argv[1:4]
r_src, r_ref = GGUFReader(src), GGUFReader(ref)
ref_shape = {t.name: [int(x) for x in t.shape][::-1] for t in r_ref.tensors}  # numpy order (slowest first)
ref_type = {t.name: t.tensor_type for t in r_ref.tensors}
PLAIN = {GGMLQuantizationType.F32: np.float32, GGMLQuantizationType.F16: np.float16}
arch = "wan"
for f in r_ref.fields.values():
    if f.name == "general.architecture":
        arch = bytes(f.parts[f.data[0]]).decode()
w = GGUFWriter(out, arch)
changed = 0
for t in r_src.tensors:
    data = np.asarray(t.data)
    want = ref_shape.get(t.name)
    qtype = t.tensor_type
    if ref_type.get(t.name) in PLAIN and qtype not in PLAIN:
        # the reference keeps it unquantized (norm weights, biases): diffusers only dequantizes Linear layers
        data = dequantize(data, qtype).astype(PLAIN[ref_type[t.name]])
        qtype = ref_type[t.name]
        changed += 1
    block, tsize = GGML_QUANT_SIZES[qtype]
    if want is not None and int(np.prod(want)) == int(t.n_elements):
        byte_shape = list(want)
        byte_shape[-1] = want[-1] // block * tsize if block > 1 else want[-1]
        if list(data.shape) != byte_shape and data.size == int(np.prod(byte_shape)):
            data = data.reshape(byte_shape)
            changed += 1
    w.add_tensor(t.name, data, raw_shape=data.shape, raw_dtype=qtype)
w.write_header_to_file()
w.write_kv_data_to_file()
w.write_tensors_to_file(progress=False)
w.close()
print(f"reshaped {changed} of {len(r_src.tensors)} tensors -> {out}")
