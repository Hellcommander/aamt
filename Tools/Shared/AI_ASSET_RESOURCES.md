# Shared AI asset-generation resources

Seven machine-wide resources any game toolset can use. Each owns one stage, and
they are deliberately not interchangeable — each is strong exactly where the
others are weak.

| Stage | Resource | Kind | Owns |
|---|---|---|---|
| `image` | Stable Diffusion 3.5 | HTTP :1338 | concept art, reference shots, detail overlays |
| `mesh` | TRELLIS.2-4B FP16 | HTTP :7960 | one image → textured mesh; RAM-offload on 11 GB |
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
| Token | `hf_token_switch` profile `"media"` → stored name `SD3.5 Token` |
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
Noise Alchemy / Dark Fantasy Studio) into a queryable conditioning space, then
generates a *new* clip that inherits that spectral DNA.

**ToS / unique mode (default on):** pack WAVs are **reference DNA only**. Never
copy, resample, trim, or lightly edit them into a game `Data/Sound` tree.
`generate_audio(..., unique=True)` (AAMT default) mixes several hits, **mutates
that mix** (pitch / time / EQ / waveshape / reverse-slice / noise), runs Stable
Audio 3 with high `init_noise` + harder negatives + extra steps, retries when
`copy_corr` stays above the bar, then applies a second DSP morph. Library-mix
fallback is refused in unique mode. Override mutate strength with
`AAMT_AUDIO_DNA_MUTATE` (default `0.72`); SA3 unique steps/negative via
`AAMT_STABLE_AUDIO_UNIQUE_STEPS` / `AAMT_STABLE_AUDIO_UNIQUE_NEGATIVE`.

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
python Shared\audio_pipeline.py search --query "muffled gas release waste" --archetype bodily
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
5. Never ship pack files or near copies. Unique mode is mandatory for Starfield mods.
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
