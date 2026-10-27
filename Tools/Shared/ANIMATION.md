# Animation stage: generated mesh -> rigged, animated .glb

`anim_client.py` (`ai_resources.make_animated_mesh`) turns a TRELLIS or SF3D mesh into a skinned glTF with real
motion clips. Nothing is keyframed by hand: the skeleton and skin weights come from a learned rigger, and the motion
comes from video of the creature itself.

```
mesh (faces -Y, feet down)
  prep    Blender      centre, feet on z=0, longest side 1               norm.glb, mesh.npz
  rig     UniRig       learned skeleton + skin weights (any body plan)   rig.npz, skeleton.png
  render  Blender      the body on white from a known camera, 640x352    frame0.png, cam.json, visible.npy
  video   Wan2.2-TI2V  frame0 + "it rears back and lunges forward..."    video/<clip>.mp4   (one per clip)
  fit     CoTracker3   tracks the visible vertices through each clip;
          + LBS fit    joint rotations fitted so skinned vertices land
                       on the tracks through cam.json (feet that touch
                       the floor don't slide); looped or trimmed, kept
                       in place, 30 fps                                  clips/<clip>.npz, fit/<clip>_check.png
  build   Blender      armature, 4-bone skin, one glTF animation/clip    <out>.glb, preview.png
```

```powershell
python Shared\anim_client.py --status
python Shared\anim_client.py hound.glb hound_anim.glb --desc "a lean robotic hound" --body quadruped
python Shared\anim_client.py hound.glb hound_anim.glb --desc "..." --only video,fit,build --redo video --clips attack --seed 9
```

```python
from ai_resources import make_animated_mesh
make_animated_mesh("hound.glb", "hound_anim.glb", "a lean robotic hound", body="quadruped",
                   prompts={"attack": "{it} leaps forward and bites, then lands and recovers. Fast, energetic movement."})
```

Clips (names are what game loaders look for):
- `idle` and `move` loop. A cycle is cut out of the footage and its ends are joined; `move` is made in place.
- `idle2`, `attack`, `attack2`, `hit` and `special` are one-shots. Each starts where the action does (video models
  drift the longer they run, so the start is the trustworthy part), eases out of the rest pose and settles back
  into it.
- `death` ends on the floor and holds.

`body` (biped, quadruped, crawler, hover, serpent) picks the `move` prompt; `hover` also drops the floor and
planted-feet terms from the fit. `prompts` overrides a clip's text, where `{it}` is the description. Every prompt
gets "Static camera, plain white background..." appended, because camera moves turn into root motion.

Prompts that move: name body parts and verbs ("raises its front legs high, rears up and lunges forward, then drops
back down"), and add "Fast, energetic movement". Vague prompts ("strikes hard") give a creature that barely moves,
or one that sprouts things (weapons, mouths) the rig can't follow.

Walks, as tested on the Interlopers (scratch prompt tests score each take's motion and save a contact sheet):
- "walks forward" mostly gets a creature that stands still.
- Walking in place with the limbs named works: bipeds march on the spot lifting each knee high, quadrupeds trot on a
  treadmill, crawlers walk slowly to the left lifting each leg.
- "toward the camera" barely moves.
- Hovering bodies: flying or dipping leaves the frame and bobbing doesn't move, but spinning on the spot with the
  arms opening and closing does.
- Serpents are the weakest; coiling and stretching moves a little.

The mesh matters as much as the prompt. A creature that lies flat with its legs splayed (a concept drawn from above)
reads as a sticker, and no prompt or camera angle makes it walk: regenerate it standing, from a side or
three-quarter concept. TRELLIS sometimes collapses many-legged concepts into a flat card; try another seed or
candidate, and check the raw mesh's extents.

## What runs where

| Piece | Where | Licence |
|---|---|---|
| venv: torch 2.8 cu128, diffusers, transformers, gguf, co-tracker | `E:\tools\anim\.venv` (`AAMT_ANIM_HOME`) | — |
| UniRig (VAST-AI) and its venv (torch 2.5.1 cu124, spconv, torch_scatter/cluster, bpy 4.2) | `E:\tools\anim\UniRig` | code MIT; weights unstated |
| UniRig checkpoints (Articulation-XL skeleton + skin) | `UniRig\experiments\...` (copies of `D:\hf-cache\local\UniRig`) | |
| Wan2.2-TI2V-5B (text encoder, VAE, config) | `D:\hf-cache\local\Wan2.2-TI2V-5B-Diffusers` (without the fp32 transformer) | Apache 2.0 |
| Wan2.2-TI2V-5B transformer, Q8_0 GGUF (QuantStack) | `D:\hf-cache\local\Wan2.2-TI2V-5B-GGUF` | Apache 2.0 |
| FastWan2.2-TI2V-5B Q8_0 (Green-Sky), relaid by `gguf_reshape.py` | `D:\hf-cache\local\FastWan2.2-TI2V-5B-GGUF\*-diffusers.gguf` | Apache 2.0 |
| CoTracker3 offline | `D:\hf-cache\local\cotracker3\scaled_offline.pth` | CC BY-NC 4.0 (non-commercial) |
| Workers | `Shared\anim\`: `blender_anim.py`, `rig_transfer.py`, `overlay.py`, `wan_video.py`, `track_fit.py`, `gguf_reshape.py` | |

Weights are plain folders under `<HF_HOME>\local`, not the hub cache: the hub's snapshot symlinks fail with
WinError 1314 in agent shells.

**Video model.** `base` (Wan2.2-TI2V-5B, 20 UniPC steps, guidance 5) is the default. `fast` (FastWan, the
FastVideo DMD distillation: 3 steps, no guidance; `AAMT_ANIM_VIDEO_MODEL=fast`) costs a fraction of the steps, but it
was distilled text-to-video only. It redraws the creature a few frames in (new shading, new position), and the
tracks can't follow across that jump. Keep it for previews, not for fitting. Its GGUF came from
stable-diffusion.cpp's converter (squeezed modulation tables, flattened patch embedding, quantised norms);
`gguf_reshape.py` relays it into the ComfyUI-GGUF layout diffusers loads.

## Changes made to the UniRig checkout (re-apply after a `git pull`)

The 2080 Ti is Turing: no FlashAttention 2, no fast bf16.

- `configs/model/aamt_ar_sdpa.yaml`: the skeleton model with `_attn_implementation: sdpa`.
- `configs/model/aamt_skin_noflash.yaml`: the skin model with PTv3 `enable_flash: False`.
- `configs/task/aamt_skeleton.yaml` and `aamt_skin.yaml`: those models at `precision: 32`.
- `src/model/aamt_mha.py` and the import in `src/model/unirig_skin.py`: a plain-PyTorch stand-in for
  `flash_attn.modules.mha.MHA` with the same parameter names, so the checkpoint loads unchanged.
- `src/inference/download.py`: uses a checkpoint path that exists instead of re-fetching it through the hub.
- `src/system/ar.py`: writes `predict_skeleton.npz` in user mode too.
- `src/system/skin.py`: also writes `predict_skin_full.npz` (per-vertex weights on the extracted mesh, plus the
  skeleton), which `rig_transfer.py` maps back onto our vertices.

`flash_attn` is left out of its requirements (`req_win.txt`). UniRig writes its npz files beside its input
(`<work>\norm\`), not in `--output_dir`.

## Budget on this box (11 GB 2080 Ti, 64 GB RAM)

- UniRig: 2 to 7 minutes per mesh (the skeleton is autoregressive, at fp32), under 8 GB.
- Wan2.2 base at 640x352: about 3 s per step, 115 s for a 73-frame clip with decode, and a 7.9 GB peak. The umT5
  encoder runs once per prompt on the CPU in fp32 (about 22 GB of RAM, around 25 s) and is cached as
  `video/emb_*.pt`.
  - 832x480 does not fit beside the desktop. The card starts swapping and a clip takes over half an hour.
  - diffusers' offload order never sends the fp32 VAE (2.8 GB) back after it encodes the first frame, which caused
    the same swapping. `wan_video.py` sends it back as soon as the latents are prepared.
  - Each clip writes `video/<clip>.progress` (step, seconds), so a stuck run is easy to spot.
- Fit: CoTracker3 on about 1,400 vertices, then about 1,900 Adam steps; 1.5 to 3 minutes per clip on the GPU.
- A full creature (8 clips): about 35 minutes.

Do not run this while TRELLIS is resident: TRELLIS's RAM offload plus the fp32 text encoder can exhaust RAM.
`anim_client` stops SD and TRELLIS first unless `AAMT_KEEP_SERVERS=1`, and every GPU step takes the AAMT GPU lock.
Other GPU users that don't take the lock (a game under test, for example) still share the 11 GB, and steps slow
down when the card is full.

## Checking the result

- `skeleton.png` (after `rig`): the bones over the render, with vertices tinted by owning bone. Check it before
  spending GPU time on video.
- `fit/<clip>_check.png`: six video frames with the tracks (red) and the fitted, skinned vertices (blue) drawn on
  top. Blue on red means the bones follow the video. Red running off alone is motion the rig can't make, or the
  video redrawing the creature.
- `fit/<clip>.json`: `mean_px` is the average distance between skinned vertices and their tracks; `window`/`cycle`
  say which frames were kept. Under about 4 px the motion follows the video.
- `preview.png` (after `build`): one row per clip, four moments each.

Re-roll a bad clip with `--only video,fit,build --redo video --clips <clip> --seed N`, or reword its prompt.

Automatic re-films (`reroll_bad_fits`, after the fit stage, up to 2 rounds, keeping the best take):
- A clip is re-filmed if its fit misses the tracks by more than `MAX_PX` (6 px), or if it barely moves:
  `swing_deg` (90th percentile over joints of each joint's largest turn) is below `MIN_SWING` for that clip
  (move 12, attack/attack2 15, special 12, hit 8, death 20, idle2 10).
- A model keeping the creature still fits perfectly and looks like nothing in game.
- `recut` also re-films clips made before the cut check, or with a cut or vanishing creature.

Loops are cut at the stretch that both comes back to its first pose and travels away from it. Closing well alone
picks the calm stretches. After changing `shape_clip`, `anim_client.reshape(work, clips)` re-cuts from the saved
raw fits in seconds.

What the fit can and can't do:
- It sees one camera, so motion toward or away from the camera is weakly constrained. A synthetic test recovers the
  projected motion to under 1 px, but individual rotations only to about 4°, mostly twist about thin limbs, which
  doesn't show.
- Joints with few tracked vertices are held near the rest pose by a prior.
- Floor-level vertices (soles, leg tips) that are down in two frames running are kept from sliding. This removed
  about 97% of foot skate in testing, so bodies moving over planted feet bend their legs.
- CoTracker marks many points occluded mid-clip that it still tracks sensibly. They count at 0.3 weight, and a
  Huber loss limits the wild ones.
