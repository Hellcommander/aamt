# refart — reference-image art and automatic layers

Stage `refart` in `ai_resources.py`. It covers what SD3.5 Medium (CLIP-only, 77 tokens, text-to-image only) cannot do:

- keep a character across pictures;
- edit a picture without redrawing it;
- split a picture into layers by naming the parts.

| Command | Engine | Use it for |
|---|---|---|
| `generate` | SDXL base + **IP-Adapter Plus** (+ optional **ControlNet Union ProMax**) | new art that keeps the look of `--ref` images; `--control` follows a shape (lineart/canny/depth/tile) |
| `inpaint` | SDXL + ControlNet Union ProMax repaint + IP-Adapter | repaint only a masked area, in the picture's own style; the rest is pasted back pixel-exact |
| `edit` | **FLUX.1 Kontext dev** (GGUF Q4_K_M) | instruction edits that keep everything else: "make the character wear a filthy toga" |
| `segment` | **Grounding DINO** + **SAM 2.1** | masks for parts named in plain words ("head", "white horn", "fleshy sack", "claw") |
| `layers` | segment + inpaint + BiRefNet matte | a layered picture from a spec of named parts (see below) |
| `overlay` | edit (or inpaint) + segment | an item layer that fits the body: edit the base to wear the item, then cut out the pixels the edit changed (Kontext keeps the framing); inpaint mode cuts by name |

## Install (done 2026-11-08)

- venv: `E:\tools\refart\.venv` (uv, Python 3.12, torch 2.8.0+cu128, diffusers 0.42, transformers 5.22, opencv, timm, kornia, einops). `AAMT_REFART_HOME` moves it.
- weights in the shared cache `D:\hf-cache`:
  - `h94/IP-Adapter`: `sdxl_models/ip-adapter-plus_sdxl_vit-h` + `models/image_encoder`
  - `xinsir/controlnet-union-sdxl-1.0`: the promax weights. The engine links them into `D:\hf-cache\local\controlnet-union-sdxl-promax`.
  - `madebyollin/sdxl-vae-fp16-fix`
  - `IDEA-Research/grounding-dino-base`
  - `facebook/sam2.1-hiera-large`
  - SDXL base was already cached.
- Kontext:
  - `QuantStack/FLUX.1-Kontext-dev-GGUF` `flux1-kontext-dev-Q4_K_M.gguf` (6.9 GB).
  - Text encoders, VAE and tokenizers come from `black-forest-labs/FLUX.1-schnell`.
  - Both FLUX repos are **gated**. The Hugging Face account used for downloads must accept the licence on `FLUX.1-schnell` and `FLUX.1-Kontext-dev`.
  - The engine builds the Kontext transformer config from schnell's, with guidance embeddings turned on.
- Token: the `D:\hf-cache` token store is stale. Downloads used the profile login (`%USERPROFILE%\.cache\huggingface`, oauth-Arendeth).

## Card rules (RTX 2080 Ti, 11 GB, Turing)

- **One pipeline resident** at a time: SDXL-plain, SDXL-control, SDXL-inpaint, Kontext or the segmenter. Switching frees the last one.
- **Every GPU call takes the toolkit GPU lock** (`Common/gpu_hub.py`), the same lock as SD3.5, TRELLIS and Wan. Do not run two generators at once.
- **fp16 everywhere on the GPU.** bf16 is emulated only on Turing.
  - Kontext's T5 and CLIP encoders run on the CPU in bf16, because T5 overflows in fp16.
  - Kontext's transformer runs on the GPU as GGUF with fp16 compute. FLUX overflows fp16 (the last double block's image stream goes inf on step 2 and every later latent is NaN, so the picture is black); the engine clamps module outputs to the fp16 range, which fixes it. Emulated bf16 (`REFART_KONTEXT_BF16=1`) runs out of memory on an 11 GB card.
  - Its VAE stays fp32 and casts the pipeline's fp16 tensors itself.
  - `edit` keeps the input's aspect (about 1 MP, sides multiples of 16) instead of Kontext's own resolution list, so the edit lines up with the source pixel for pixel.
  - Speed: a direct 20-step edit took about 3.5 minutes (7 s/step), but a full `overlay` run (24 steps + segmenter) took 27 to 34 minutes on 2026-11-08. The cause is not yet found (GPU-lock wait or memory spill are the suspects). Later batches ran at 4 to 14 minutes per item, so the 30-minute runs were one-offs.
  - When an edit removes something (Kontext sometimes drops the back sack under a helmet), the changed pixels include a backdrop-coloured patch. `overlay` now leaves pixels the edit painted as plain backdrop (12,53,59, distance 40) out of the cut automatically.
  - Kontext may also repaint the whole torso while adding a helmet. `overlay --clip-region --region head` (Python `clip_region=True`) stops the cut one region-height below the region's matches, so the layer never covers body armour. Without it such an edit fails with "covers the whole figure". `cyf_portrait_items.py --fitted` turns it on for head and face slots.
  - A failed run's stderr ends with the GPU hub's "GPU job lease released" line, which is not the error. `refart_client.run` now appends the real exception line last, so callers that print only the last line show the cause.
  - Head items: say "middle head only" and "side heads unchanged" in the hint. Kontext still often fits face gear to all three heads. A coronet came out as a collar in all three tries.
- SDXL uses model CPU offload. Expect about 30–60 s per 1 MP image on an idle card. With a game holding VRAM, a run takes several minutes.

## Layers spec

```json
{"fighter": "rhomustos", "source": "art.png", "subject": "three-headed green slime mutant", "crop": "auto",
 "parts": [
  {"phrase": "white horn", "count": 3, "assign": "x", "files": ["horns2.png", "horns.png", "horns3.png"],
   "follow": ["horns2,head2", "horns", "horns3,head3"], "z": "front",
   "fill": "inpaint", "within": "head", "fill_prompt": "bald smooth green slimy scalp"},
  {"phrase": "glowing eye", "count": 6, "assign": "group:head", "files": ["glow2.png", "glow1.png", "glow3.png"],
   "follow": ["glow_eyes,head2", "glow_eyes", "glow_eyes,head3"], "z": "front", "fill": "dark"},
  {"phrase": "head", "count": 3, "assign": "x", "files": ["head2.png", null, "head3.png"],
   "follow": ["head2", null, "head3"], "z": "back", "fill": "transparent", "stump": true},
  {"phrase": "fleshy sack", "count": 1, "files": ["brood.png"], "follow": ["brood"], "z": "back",
   "fill": "transparent", "grow": 4}]}
```

- **Parts are lifted in order.** A head layer is cut after its horn is gone, so it carries the refilled scalp.
- **`assign`:**
  - `"x"` maps matches left to right onto `files`; `null` means found but left in the base.
  - `"group:head"` merges the matches inside each head into one file.
- **`fill`:**
  - `transparent`: there is nothing behind the part.
  - `inpaint`: SDXL repaints the area. With `within`, it repaints only inside the hull of those parts, so a horn's base becomes scalp and the rest of the horn goes clear.
  - `dark`: flat dark sockets.
- **`stump`** adds an outline layer, shown when the part is gone (`!head2`).
- **Output:** `base.png`, one cropped PNG per layer, `portrait.xml` (Arendeth_CYFTiles layered-portrait format, X/Y per layer), `layers.json`, and previews with each optional part removed.
- **Phrases that worked** on the Rhomustos art: `head`, `white horn` (plain `horn` matched the whole figure), `glowing eye`, `fleshy sack`, `claw`, `magenta patch`.
- **Whole-figure matches** that Grounding DINO returns for vague phrases are dropped automatically: any box over 45% of the figure.
