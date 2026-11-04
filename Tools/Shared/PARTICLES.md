# Particle stage: description -> flipbook particle texture

`particle_client.py` (`ai_resources.make_particles`) makes particle textures from a description. The image model
draws the effect at its peak, the video model sets it in motion, and the frames are cut into an atlas a particle
system can play. Nothing is drawn procedurally.

```
recipe {"name": "green_blast", "preset": "explosion", "desc": "a burst of green plasma fire"}
  key     SD3.5 (:1338)     the effect on pure black (glows, fire, smoke, lightning), or solid
                            pieces on a plain grey backdrop (debris)                    <work>/<name>/key.png, key_<n>.png
  video   Wan2.2-TI2V-5B    key.png shrunk to 72% on black (room to grow) + the
                            preset's motion text, 480x480, 49 frames                   <work>/<name>/key_video.png, clip.mp4
  sheet   fx_frames.py      alpha, one shared square crop, frames picked or looped,
                            packed into an atlas; previews                              <out>/<name>.png, _preview.png, .gif, _sheet.json
  effect                    an emitter layer for the atlas (Chimera particle schema)    <out>/<name>_effect.json
```

```powershell
python Shared\particle_client.py --status            # what is installed
python Shared\particle_client.py --install           # fetch every weight/package now instead of on first use
python Shared\particle_client.py --presets
python Shared\particle_client.py out\fx --preset explosion --name green_blast --desc "a burst of green plasma fire"
python Shared\particle_client.py out\fx --recipes recipes.json --only sheet          # re-cut without the GPU
python Shared\particle_client.py out\fx --recipes recipes.json --redo video --seed 4
```

```python
from ai_resources import make_particles
make_particles([{"name": "frost_puff", "preset": "smoke_puff", "desc": "a puff of icy blue mist", "seed": 2,
                 "layer": {"color": "#C8E8FF"}}], Path("out/fx"))
```

A recipe is merged over its preset; any preset field can be overridden (`desc`, `motion`, `key_scale`, `grid`, `tint`,
`blend`, `matte`, `loop`, `grow_in`, `gamma`, `fade`, `count`, `frames`, `cell`, and `layer` key by key).

## Presets

| preset | kind | blend | tint | notes |
|---|---|---|---|---|
| explosion | flipbook 6x6 | add | baked | fireball; 3 grow-in frames because the clip starts at the peak |
| impact | flipbook 5x5 | add | white | hit flash with sparks |
| smoke_puff | flipbook 6x6 | alpha | white | white smoke; the layer colour sets its shade (dark smoke works too) |
| electric | flipbook 4x4 | add | white | each frame a different arc: use `randomFrame` |
| magic_burst | flipbook 6x6 | add | white | swirling flare |
| flame_loop | flipbook 6x6, loop | add | baked | a cycle cut from the clip, ends cross-faded |
| energy_orb | flipbook 6x6, loop | add | white | pulsing orb for projectile heads |
| shards | 4 sprites (2x2) | alpha | baked | BiRefNet cut-outs; `randomFrame` debris |
| glyph | 4 sprites (2x2) | add | white | sigils seen from above; flat ground layers |

- **tint**: `white` sheets are greyscale with their brightest solid parts at full white, so a particle's colour
  tints them (one sheet serves every palette). `baked` keeps the model's colours: tint those with white.
- **blend**: `add` for light (black is see-through); `alpha` for smoke and solid pieces.

## How the sheet is cut

- **Alpha.** Drawn on black (`matte: luma`): alpha comes from the brightest channel above the clip's own black level
  (generated black is never 0, and the codec lifts it), with a knee that keeps compression noise transparent. Colour
  is stored un-premultiplied, so colour x alpha, which is what both additive and alpha-blended particle shaders use,
  gives back the drawing. `gamma` < 1 thickens faint smoke. Solid pieces (`matte: birefnet`) are drawn on grey and cut
  out with BiRefNet, because brightness-as-alpha would make their dark faces transparent.
- **Edges.** Alpha fades over the outer 5% of the source frame, since anything touching it was cut off there.
- **Framing.** One square crop around everything the frames cover, so the effect doesn't jump between cells.
  Cells are resized premultiplied (no dark fringes), and their outer pixels fade so mipmaps don't bleed into
  neighbours.
- **Timing.** One-shots run from the first frame to where the effect has all but gone (4% of its peak coverage),
  evenly; the last `fade` (25%) fades to nothing. `grow_in` N replaces the first N frames with frame N scaled up
  from 30%, because image-to-video starts at the drawn peak. Loops take the stretch whose end best matches its start
  and cross-fade the frames just past the end into the first few.
- **Atlas.** Frame 0 top-left, rows left to right (Unity's texture sheet animation order), straight alpha RGBA PNG,
  128 px cells by default (`cell`).

Check `<name>_preview.png` (every cell composited over a dark floor the way the game blends it) and `<name>.gif`.
`_sheet.json` records which clip frames were used, the crop, and for loops the seam score.

## What runs where

| Piece | Where | Licence |
|---|---|---|
| Animation venv (torch 2.8 cu128, diffusers, opencv) shared with the animate stage | `E:\tools\anim\.venv` (`AAMT_ANIM_HOME`) | |
| timm, kornia (BiRefNet's model code needs them) | installed into that venv with `uv` on first cut-out | Apache 2.0 |
| Wan2.2-TI2V-5B Diffusers parts + Q8_0 GGUF transformer | `D:\hf-cache\local\Wan2.2-TI2V-5B-*` (fetched if missing) | Apache 2.0 |
| BiRefNet (ZhengPeng7/BiRefNet), weights + model code | `D:\hf-cache\local\BiRefNet` (fetched on first cut-out; `AAMT_BIREFNET`) | MIT |
| Workers | `Shared\particles\fx_frames.py`, `matte.py`; video through `Shared\anim\wan_video.py` | |

Weights are plain folders under `<HF_HOME>\local` (hub snapshot symlinks fail with WinError 1314 in agent shells).
`wan_video.py` takes `negative` and `cut_check: false` from the job file for these clips: its default negative prompt
and cut re-rolls are tuned for creatures, and particle clips flash and vanish on purpose.

## Budget on this box (11 GB 2080 Ti)

- Key frame: SD3.5 1024x1024, 28 steps.
- Clip: Wan2.2 base at 480x480 (about the pixel count of the animate stage's 640x352), 20 steps, 49 frames. The
  umT5 prompt encoding runs on the CPU (about 22 GB of RAM) once per prompt and is cached beside the clip.
- Sheet: seconds; BiRefNet adds about 14 s to load, then 0.2 s per frame.

SD and TRELLIS are stopped before video (`AAMT_KEEP_SERVERS=1` keeps them), and every GPU step takes the AAMT GPU
lock. A game under test doesn't take the lock but shares the card; clips slow down a lot when it is full.
