# Shared AI asset-generation resources

Eight machine-wide resources any game toolset can use. Each owns one stage, and
they are deliberately not interchangeable — each is strong exactly where the
others are weak.

| Stage | Resource | Kind | Owns |
|---|---|---|---|
| `image` | Stable Diffusion 3.5 | HTTP :1338 | concept art, reference shots, detail overlays |
| `mesh` | TRELLIS.2-4B FP16 | HTTP :7960 | one image → textured mesh; RAM-offload on 11 GB. The default for creatures, characters and anything detailed |
| fast mesh | Stable Fast 3D | own venv (`sf3d_client.py`) | seconds per mesh; **only for background props and simple compact objects** (guessed backs, fused thin limbs) |
| `animate` | UniRig + Wan2.2-TI2V-5B + CoTracker3 | own venvs (`anim_client.py`) | mesh → skinned .glb with idle/move/attack/hit/death/special fitted to generated video of that mesh. See [ANIMATION.md](ANIMATION.md) |
| `particles` | SD3.5 + Wan2.2-TI2V-5B + BiRefNet | animation venv (`particle_client.py`) | description → flipbook / sprite-sheet particle texture with alpha + an emitter layer. See [PARTICLES.md](PARTICLES.md) |
| `material` | Material Maker | CLI | seamless tileable PBR base maps |
| `pixels` | Pixelorama | CLI + visible GUI | pixel-art .pxo inspect/export; `see` screenshots the editor |
| `layering` | Ucupaint | Blender add-on | compositing/masking onto a mesh's UVs |
| `compress` | DirectXTex texconv | CLI | engine-ready DDS/BCn |
| `audio` | Stable Audio 3 + asset library | in-process | SFX that reuse purchased/made packs |

## Start here

```powershell
python Shared\ai_resources.py            # what's available right now
python Shared\ai_resources.py --json     # same, machine-readable
python Shared\ai_resources.py --ensure mesh
```

From Python:

```python
from ai_resources import ensure, make_image, make_mesh, make_audio

ensure("mesh")
ref  = make_image("a mossy stone idol, on white background", Path("ref.png"))
mesh = make_mesh(ref, Path("idol.glb"), resolution=512)
sfx  = make_audio("short sci-fi plasma vent burst", Path("vent.wav"), archetype="laser")
```

`ai_resources.py` never raises during discovery — an unreachable stage simply
reports `ready: false` with a `start` hint, so callers can degrade instead of
crashing.

## The one hard constraint: a single 11 GB GPU

Three of the visual stages plus Stable Audio want the GPU, and this box has
one RTX 2080 Ti. Two model servers can be *resident* at once, but they must
never *generate* at once. Everything GPU-heavy therefore routes through
`Common/gpu_hub.py`:

```python
from gpu_hub import acquire_gpu
with acquire_gpu("my label"):
    ...one generation request...
```

`sd_http_client`, `trellis_http_client`, `material_maker_client`, and
`aamt_stable_audio_backend` already do this internally, so calling them needs
no extra care. Take the lock yourself only if you drive a GPU tool directly.

Hold the lock for individual requests, never for server startup.

## Per-resource notes

### Stable Diffusion 3.5 (`sd_http_client.py`, `sd35_server.py`)

This is the **only** pixel generator for AAMT game tiles. Agents must not use
Cursor's image generator for Soulash 2 (or other game) icons, sprites, or
tilesheets — those belong on `:1338` via this client.

Canonical server source is `Shared/sd35_server.py`. `Start-StableDiffusionServer.ps1`
copies it to `E:\tools\sd3.5\sd3.5\server.py` on every start.

```powershell
python Shared\ai_resources.py --ensure image
python Shared\sd_http_client.py --detect-only
```

| Fact | Value |
|---|---|
| Port | `1338` (`aamt-1338.2`) |
| Generate | `POST /v1/images/generations` (alias `/generate`) |
| Health | `GET /ping` → `{status, loaded, token_ok, img2img}` |
| Auth | the machine's existing `hf auth login` (`hf_token_switch.use_media_token()` only confirms it) |
| Weights | `stabilityai/stable-diffusion-3.5-medium` (gated; local cache first) |
| Default | `SD_SKIP_T5=1` (CLIP-only; **77 tokens**). Longer prompts: `SD_SKIP_T5=0` + `SD_ALLOW_T5_RAM=1` + `SD_MAX_SEQ_LEN=256` (T5 on CPU/RAM). |
| Idle | `SD_IDLE_SHUTDOWN_SEC=180`. Batch jobs: `AAMT_SD_KEEP_SERVER=1` |
| Img2img | body `image` (b64) + `strength`. `--from-existing` needs this. |

**Agent rules**

1. `ensure("image")` / `make_image()` or the game CLI (`generate-icons`). Do not
   invent a second SD server or a second port.
2. Size requests with `plan_sd_size(..., kind="icon")` (512 floor, then downscale).
   Native 32×32 SD inference is near-black; do not set `native=True` for icons.
3. Soulash 2 skill atlases: 128px cells, index 0 = bottom-left, padded 16-col grid.
   `python s2_skill_cli.py generate-icons --id <id> --overwrite`
   Prefer txt2img (no `--from-existing`) for new silhouettes. `--names` is
   comma-separated display names, exact match.
4. After a 401 / `GatedRepoError`, restart the server (token is applied in
   `load_pipeline`). Do not stamp Cursor PNGs into the atlas as a workaround.
5. CLIP-only Medium will not match Flux-class prompt following. Fix reliability
   and prompts first; do not silently switch generators.
6. If `/ping` is not `version: aamt-1338*`, port 1338 is a **foreign** process
   (commonly Starfield SFMAG `sd_server.py`). AAMT start/ensure replaces it.
   Do not treat that listener as the toolkit server.

### TRELLIS.2 (`trellis_http_client.py`)

[microsoft/TRELLIS.2](https://github.com/microsoft/TRELLIS.2) is Linux + **24 GB**.
On this 11 GB 2080 Ti (64 GB RAM) the 4B model only runs as **FP16 with CPU/RAM
offload**: weights stay in system RAM (~30–50 GB), active DiT / O-Voxel stages
swap onto the GPU. Expect slow inference and VRAM spikes near 10–11 GB. Use
voxel tier **512** here. Do **not** load this into vLLM or SGLang.

Two Windows backends (`TrellisVariant` / `AAMT_TRELLIS_VARIANT`):

| Option | What | VRAM |
|---|---|---|
| `trellis2` (default if `D:\trellis2` exists) | [IgorAherne/TRELLIS.2-stableprojectorz](https://github.com/IgorAherne/TRELLIS.2-stableprojectorz) — Windows fork of TRELLIS.2, **lags microsoft**. `low_vram` + `--precision half`. Gradio **Precision = float16**. | 8–11 GB + RAM offload |
| `trellis1` | [IgorAherne/trellis-stable-projectorz](https://github.com/IgorAherne/trellis-stable-projectorz) + [int32 FlexiCubes](https://github.com/IgorAherne/flexicubes-stable-projectorz) — `pipeline.to(float16)`. Lighter 1.2B. | 8 GB half-precision |

`TrellisPrecision=half` (default) is the GUI/API float16 option. `full` is the
24 GB path.

**Idle shutdown (required on this card).** `generate_mesh()` stops the TRELLIS
server when the GLB is written, unless `AAMT_TRELLIS_KEEP_SERVER=1`. Multi-job
SFMAG / `run_fx_batch` sets KEEP for the batch and calls `stop_mesh()` in
`finally`. Idle TRELLIS holds several GB and starves Stable Audio 3 / SD /
Starfield — do not leave `:7960` up "just in case."

Output is a GLB with `POSITION`, `NORMAL`, `TEXCOORD_0` and PBR textures. The
UVs are the important part — they're what later baking and skinning bind to.
Treat the baked textures as a starting point, not a final material.

Resolution is a voxel tier: `512` (safe here), `1024`, `1536`.
`mesh_simplify` is a decimation target in thousands of faces.

Weights live in the shared HF cache (`tool_paths.hf_home()`, `D:\hf-cache`) via
a junction at `D:\trellis2\code\models`, so nothing is downloaded twice.

TRELLIS.2 also loads its sparse-structure decoder out of
`microsoft/TRELLIS-image-large`. That repo has been pruned to just that one
checkpoint — do not delete it, and do not expect the rest of TRELLIS-1 to be
there.

### Material Maker (`material_maker_client.py`)

Two real failure modes, both verified on this build (1.7 / Godot 4.7):

1. **Multi-output graphs crash the headless exporter** with an access
   violation, on every renderer (vulkan/d3d12/opengl3) and every target. Only
   single-output graphs export from the CLI. Author multi-map materials once in
   the GUI and let the pipeline consume the PNGs.
2. **It crashes when VRAM is tight.** Material Maker renders its node graph on
   the GPU, so an export that succeeds on an idle card fails with the model
   servers resident. This is why it takes the GPU lock.

It also resolves `-o` relative to its own cwd and joins with `/`, so backslash
output paths silently write nothing. `export()` converts paths for you.

`export()` normalises MM's map names to toolkit names (`albedo` → `color`,
`roughness` → `rough`, and so on) and returns `{kind: path}`.

### Pixelorama (`pixelorama_client.py`)

Install is `D:\tools\Orama Interactive\Pixelorama`. Agents use the host, not
raw Godot flags:

```powershell
python Shared\pixelorama_client.py status
python Shared\pixelorama_client.py open sprite.pxo
python Shared\pixelorama_client.py see --out Tools\Logs\pixelorama\see.png
python Shared\pixelorama_client.py export sprite.pxo --out out.png
```

`open` shows the real editor. `see` captures that window for vision. Headless
`export` / `spritesheet` / `inspect` take the GPU lock. Full notes:
`Shared/PIXELORAMA.md`. Magi-Tech pack: `Tools/Starbound/produce_pixelorama_sheets.py`
(`Produce-UnityStillAnimations.ps1 -Backend pixelorama`).

### Ucupaint (`ucupaint_support.py`)

Installed for every Blender version found under `%APPDATA%`. Inside a headless
Blender script call `ensure_enabled()` before using it. Bake real SD / Material
Maker / TRELLIS maps onto a mesh's UVs with `ucupaint_bake.py` /
`ucupaint_support.bake_onto_mesh`. Do not use `Common/bake_texture.py` for that
(procedural materials only), and do not use the Caves of Qud Space-Time Vortex
generators.

### texconv

Formats are the caller's choice because they're engine-specific. Starfield's
Creation Engine 2, for example, requires `BC7_UNORM_SRGB` for color,
`BC5_SNORM` for normals and `BC4_UNORM` for roughness, all with DX10 headers
and power-of-two dimensions.

### Audio (`audio_pipeline.py`, `audio_asset_library.py`)

The audio stage does **not** invent SFX from a blank prompt when you already
own the timbre. It turns `D:\assets\audio` (purchased zip packs, including
Noise Alchemy, whose packs include the Dark Fantasy Studio line) into a queryable conditioning space, then
generates a *new* clip that inherits that spectral DNA.

**License tiers** (from the license files in `D:\assets\audio`;
`license_tier()` in `audio_asset_library.py`):

| Tier | Packs | How it may reach a game/mod | Credit |
|---|---|---|---|
| `own` | `D:\assets\audio\made\<archetype>\` — audio we made (filled by `--keep`, or drop files in and re-run `ingest`) | As-is; reusable as references | Whatever its sidecar `.meta.json` `attribution` says (carried forward on reuse) |
| `direct` | `bt25_ultimatesfxforgames_softwarebundle\` (Function Loops, functionloops.com, sold via Humble Bundle), `magicspellssfxbundle_audio.zip`, `inventorysfxbundle_audio.zip`, `puzzleaudiokit.zip`, `buttonssfxlibrary.zip` (Tao & Sound $5 bundle, royalty-free EULA) | Unique mode, or close-copy (`--close-copy --direct-only`) — altered either way | — |
| `reference` | Noise Alchemy packs — both `NOISE ALCHEMY- *` and `Dark Fantasy Studio- *` zips (one vendor, one EULA) — plus any pack without its own license file | Unique mode only | `Sound effects created with NOISE ALCHEMY – NOISEALCHEMY.COM` once in the project credits/description |

**No purchased original ever ships, whatever the tier.** Even where a license
would allow raw use, every pack clip is altered first so nobody can pull the pack
file back out of a mod. Only `own` clips ship as-is. No tier allows redistributing
clips as a standalone sound pack or library.

**Reusing what we make:** add `--keep` to `generate` or `blend` and a shippable
result is copied to `made\<archetype>\` with its `.meta.json` and indexed on the
spot (no full rescan; its prompt and archetype become tags). Non-shippable output
is never kept. Own clips count as `--direct-only` references and are ignored by
the `source_corr` / `check` copy test.

**ToS / unique mode (default on):** `reference`-tier WAVs are **DNA only**. Never
copy, resample, trim, or lightly edit them into a game `Data/Sound` tree.
`generate_audio(..., unique=True)` (AAMT default) mixes several hits, **mutates
that mix** (pitch / time / EQ / waveshape / reverse-slice / noise), runs Stable
Audio 3 with high `init_noise` + harder negatives + extra steps, retries when
`copy_corr` stays above the bar, then applies a second DSP morph. Library-mix
fallback is refused in unique mode. Override mutate strength with
`AAMT_AUDIO_DNA_MUTATE` (default `0.72`); SA3 unique steps/negative via
`AAMT_STABLE_AUDIO_UNIQUE_STEPS` / `AAMT_STABLE_AUDIO_UNIQUE_NEGATIVE`.

`--direct-only` (`direct_only=True`) limits retrieval to `direct` and `own` clips.
`--close-copy` output and `blend` output are always run through the DSP
alteration (pitch / EQ / waveshape / reverse-slice / noise), escalating
`0.45 → 0.65 → 0.85` until `source_corr` — similarity to each **raw** source
clip, not the mixed reference — is ≤ 0.22. Every `.meta.json` records each
reference's `license`, `source_corr`, a `shippable` flag, and the `attribution`
line owed (if any). Only ship clips with `"shippable": true`.

Before packaging a mod, scan its sound folder for anything that slipped in
unaltered: `audio_pipeline.py check <folder>` prints `COPY` with the matching
pack clip and exits 1 if any file is too close. It reads wav/ogg/flac/mp3/aiff;
decode `.xwm` / `.fuz` to wav first. The check fails closed: a library clip it
cannot decode counts as a match. `pip install av` lets it decode the library's MP3s
(e.g. `puzzleaudiokit.zip`'s MP3 folder).

**SFMAG crapping / accident SFX:** use archetype `bodily` (indexes
`Dark Fantasy Studio- Farts!.zip` and related tags: `fart`, `gas`, `waste`,
`crapping`, `mess`). Prompt the *event*, not a pack filename — e.g.
`"short muffled fabric-buffered gas release, adult MAG accident"` with
`archetype="bodily"`.

```powershell
python Shared\audio_pipeline.py status
python Shared\audio_pipeline.py ingest --fast          # tags + spectral (all packs)
python Shared\audio_pipeline.py ingest --fast --pack Farts   # new bodily pack only
python Shared\audio_pipeline.py ingest                 # also CLAP + Whisper on vocals
python Shared\audio_pipeline.py backfill-clap          # fill CLAP rows missing after a --fast/--no-clap ingest
python Shared\audio_pipeline.py rebuild-tags           # re-embed tags after installing/changing sentence-transformers
python Shared\audio_pipeline.py search --query "muffled gas release waste" --archetype bodily
python Shared\audio_pipeline.py search --query "sci-fi ui click" --direct-only
python Shared\audio_pipeline.py generate --prompt "soft inventory pickup" --out pickup.wav --close-copy --direct-only
python Shared\audio_pipeline.py generate --prompt "short plasma vent burst" --out vent.wav --archetype laser --keep   # reuse later as own tier
python Shared\audio_pipeline.py check "D:\path\to\mod\Sound"   # flag near copies before shipping
python Shared\audio_pipeline.py generate --prompt "short plasma vent burst" --out vent.wav --archetype laser
python Shared\audio_pipeline.py generate --prompt "short muffled MAG accident gas release" --out mess.wav --archetype bodily
```

From Python:

```python
from ai_resources import make_audio
make_audio("short metallic hatch slam", Path("hatch.wav"), archetype="ship", strength=0.7)
make_audio(
    "short muffled fabric-buffered gas release, adult incontinence accident",
    Path("sfmag_mess_gas.wav"),
    archetype="bodily",
    duration=1.4,
)
```

| Fact | Value |
|---|---|
| Library | `D:\assets\audio` (`AudioLibraryDir` / `AAMT_AUDIO_LIBRARY_DIR`) |
| Index | `D:\assets\audio\_aamt_index` |
| Generator | Stable Audio 3 (`aamt_stable_audio_backend.py` under `E:\tools\stable-audio`), GPU-locked |
| Retrieval | tag MiniLM + spectral fingerprint; optional CLAP (`laion/clap-htsat-unfused`, CPU) |
| Conditioning | mix top-k refs → (unique: mutate DNA) → SA3 `init_audio` (`strength` 0=text-only, 1=stay on refs; unique caps ~0.28) |
| Unique bar | `copy_corr` ≤ ~0.22 after retries; refuse library-mix |
| Fallback | only when unique is off and SA3 is down: duration-fit mix of retrieved clips |
| Archetypes | laser, ui, alien, mech, ship, magic, ambience, voice, impact, organic, **bodily**, horror, water, fire |

**Agent rules**

1. `ensure("audio")` then `make_audio(...)` or `audio_pipeline.py generate`. Do not
   hallucinate a new SFX pack or download random web sounds.
2. Ingest once (`--fast` is enough to search). Resume is incremental; re-run
   `--pack Farts` after adding that zip.
3. Pass `archetype` / `tags` when you know the family (Starfield ship hatch →
   `ship`, UI beep → `ui`, spell → `magic`, SFMAG mess gas → `bodily`).
4. SA3 takes the GPU lock. Do not generate audio while SD/TRELLIS is rendering.
5. Never put an original pack file, or a near copy, into a mod — any purchased
   tier. Ship only `own` clips or generated clips whose meta says `"shippable": true`
   (`--keep` the good ones so they're reusable); `reference`-tier DNA
   needs unique mode (Starfield mods included). Run `check` on the mod's sound
   folder before packaging. Add the Noise Alchemy credit whenever a meta's
   `attribution` is non-empty.
6. `doomnoisealchemy.zip` / `downsweeps.zip` may be skipped if Python cannot
   open them as zip; the rest of the library still indexes.

## Adding a consumer

Put `Tools\Shared` on `sys.path` and import. For a worked example of a
consumer living outside this tree, see the Starfield SFFuncon bridge at
`SFFuncon\tools\aamt_bridge.py`, which prefers these shared resources and only
falls back to local clients when the toolkit is absent.

Do not stand up a second SD or TRELLIS server on the same ports — that was the
original SFFuncon mistake, and it wastes VRAM and defeats the GPU lock.

## Paths

All resolved by `tool_paths.py` (env var → `TranscendenceTools.ini` → default):

| Function | Default |
|---|---|
| `hf_home()` | `D:\hf-cache` |
| `trellis_root()` / `trellis_port()` / `trellis_variant()` / `trellis_precision()` | `D:\trellis2` / `7960` / `auto` / `half` |
| `material_maker_exe()` | `D:\tools\Texture_Making_tools\material_maker_1_7_windows\material_maker.exe` |
| `ucupaint_addon_dir()` | newest Blender under `%APPDATA%` |
| `texconv_exe()` | `D:\decompilers\DirectXTex\texconv.exe` |
| `audio_library_dir()` | `D:\assets\audio` |
| `audio_index_dir()` | `D:\assets\audio\_aamt_index` |

Check them with `python Shared\tool_paths.py`.
