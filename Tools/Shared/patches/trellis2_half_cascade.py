"""Fix for TRELLIS.2 (IgorAherne/TRELLIS.2-stableprojectorz, the install in D:\\trellis2) failing at
the 1024 and 1536 voxel tiers in half precision:

    HTTP 500  "mat1 and mat2 must have the same dtype, but got Float and Half"

Cause (found 2026-11-19): with `--precision half` the flow models and the shape decoder hold
float16 weights, while the image conditioning and the sampler's output are float32. The 512 path
(`sample_shape_slat`, `sample_tex_slat`, `decode_shape_slat`) already casts what it hands to a
model; the cascade path used for 1024 and 1536 (`sample_shape_slat_cascade`) did not, in three
places: the low-resolution sampling, the upsampling through the shape decoder, and the
high-resolution sampling.

This script patches `code/trellis2/pipelines/trellis2_image_to_3d.py` of that install in place
(a third-party file outside this repository, so the fix lives here as a patch that can be
applied again after a reinstall or update). It is idempotent and keeps a backup beside the file.

    python trellis2_half_cascade.py [--root D:\\trellis2] [--check] [--revert]

--check only reports whether the install is patched; --revert puts the backup back.
Written against the install as it was on 2026-11-19 (pipeline file of 962 lines, already
carrying the toolkit's earlier half-precision casts: `_cond_like`, `[DTYPE]` prints).
"""
import argparse
import os
import re
import shutil
import sys

MARK = '# AAMT half-precision cascade fix'

# (pattern, replacement) pairs; each pattern must match exactly once. Blank lines in the file
# carry trailing spaces, hence the patterns rather than plain text.
EDITS = [
    # 1. low-resolution sampling: conditioning in the low-resolution model's dtype
    (r'(            flow_model_lr\.to\(self\.device\)\n)',
     r'\1        lr_cond = self._cond_like(lr_cond, flow_model_lr)  ' + MARK + '\n'),
    # 2. upsampling: the sampler's float32 latent in the decoder's dtype (as decode_shape_slat does)
    (r"        hr_coords = self\.models\['shape_slat_decoder'\]\.upsample\(slat, upsample_times=4\)\n",
     "        _up_decoder = self.models['shape_slat_decoder']\n"
     '        slat = slat.to(next(_up_decoder.parameters()).dtype)  ' + MARK + '\n'
     '        hr_coords = _up_decoder.upsample(slat, upsample_times=4)\n'),
    # 3. high-resolution sampling: conditioning in the high-resolution model's dtype
    (r'(            flow_model\.to\(self\.device\)\n)([ \t]*\n        slat = self\.shape_slat_sampler\.sample\(\n            flow_model,\n'
     r'            noise,\n            \*\*cond,\n            \*\*sampler_params,\n            verbose=True,\n'
     r'            tqdm_desc="Sampling shape SLat \(HR\)",)',
     r'\1        cond = self._cond_like(cond, flow_model)  ' + MARK + r'\n\2'),
]


def target(root):
    return os.path.join(root, 'code', 'trellis2', 'pipelines', 'trellis2_image_to_3d.py')


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--root', default=os.environ.get('AAMT_TRELLIS_ROOT', r'D:\trellis2'))
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--revert', action='store_true')
    args = parser.parse_args(argv)
    path = target(args.root)
    backup = path + '.before-half-cascade-fix'
    if not os.path.isfile(path):
        print(f'{path} not found (is --root the TRELLIS.2 install?)')
        return 2
    with open(path, encoding='utf-8', newline='') as f:
        text = f.read()
    done = text.count(MARK)
    if args.check:
        print(f'{path}: ' + ('patched' if done == len(EDITS) else 'not patched' if done == 0 else f'partly patched ({done} of {len(EDITS)})'))
        return 0 if done == len(EDITS) else 1
    if args.revert:
        if not os.path.isfile(backup):
            print('no backup to put back')
            return 1
        shutil.copyfile(backup, path)
        print(f'reverted from {backup}')
        return 0
    if done == len(EDITS):
        print('already patched')
        return 0
    if done:
        print(f'partly patched ({done} of {len(EDITS)}): revert first (--revert) or fix by hand')
        return 1
    if '_cond_like' not in text:
        print('this pipeline file has no _cond_like helper: it is not the version this patch was written for')
        return 1
    newline = '\r\n' if '\r\n' in text else '\n'
    work = text.replace('\r\n', '\n')
    for number, (pattern, replacement) in enumerate(EDITS, 1):
        work, count = re.subn(pattern, replacement, work)
        if count != 1:
            print(f'the pipeline file does not look as expected (place {number} was found {count} times); nothing changed')
            return 1
    if not os.path.isfile(backup):
        shutil.copyfile(path, backup)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(work.replace('\n', newline))
    print(f'patched {path} ({len(EDITS)} places); backup: {backup}')
    print('restart the TRELLIS server for it to take effect')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
