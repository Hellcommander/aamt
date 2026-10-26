# Shared AI asset pipeline — agent handoff

Working directory for this toolkit stage:

```
D:\games\Ai assisted toolkit\Tools\Shared
```

Read [AI_ASSET_RESOURCES.md](AI_ASSET_RESOURCES.md) before generating any image,
mesh, material, DDS, or audio. Probe the machine; do not assume servers are up:

```powershell
python ai_resources.py
python ai_resources.py --ensure image
python ai_resources.py --json
```

## Image pixels (Stable Diffusion 3.5)

SD3.5 on **:1338** is the image stage. Agents must use it for game icons,
sprites, tilesheets, and concept refs.

- Client: `sd_http_client.py` (`detect_server`, `generate_image`, `plan_sd_size`)
- Lifecycle: `sd_server_lifecycle.py` (`ensure_sd_server`, `managed_sd_server`)
- Server source: `sd35_server.py` (copied to `E:\tools\sd3.5\sd3.5\server.py` on start)
- Auth: the machine's existing `hf auth login` (`hf_token_switch.use_media_token()` just confirms it; no token names live in the repo)
- Start: `Tools\Start-StableDiffusionServer.ps1`  Stop: `Stop-StableDiffusionServer.ps1`

Do **not**:

- Use Cursor's image generator for game tiles or to "fix" a bad SD run
- POST to `/` or a guessed `/generate`-only URL without `/v1/images/generations`
- Stand up a second SD process on another port
- Generate native 32×32 with SD3.5 (near-black). Plan at 512 (`kind="icon"`), downscale
- Point `HF_HOME` at a drive that hides `%USERPROFILE%\.cache\huggingface\stored_tokens`

Do:

- `ensure("image")` then `make_image(...)` for one-off refs
- Game CLIs that already wrap `managed_sd_server` (Soulash 2 `generate-icons`)
- `AAMT_SD_KEEP_SERVER=1` for a batch of CLI invocations
- Prefer txt2img for new silhouettes; img2img is `image` + `strength` on the server

`:1338` must be **aamt-1338** (`Shared/sd35_server.py`). Starfield SFMAG
`sd_server.py` often steals that port; `ensure("image")` and
`Start-StableDiffusionServer.ps1` replace a foreign listener. Do not talk to it.

Soulash 2 skill icons: `Tools\Soulash2\SkillCreator` — `generate-icons --id <id> --overwrite`.
128px atlas cells, index 0 bottom-left. `--names` is comma-separated **display names**.

## Other stages

| Stage | Module | Port / kind |
|---|---|---|
| mesh | `trellis_http_client.py` | :7960 FP16 + RAM offload; `--precision half`; stops after each job unless `AAMT_TRELLIS_KEEP_SERVER=1`. **The default mesh stage**: creatures, characters, anything with limbs, thin parts or detail that matters (it rebuilds real volume and backs) |
| fast mesh | `sf3d_client.py` (`ai_resources.make_fast_mesh` / `make_fast_meshes`) | Stable Fast 3D in its own venv (`AAMT_SF3D_HOME`, default `E:\tools\stable-fast-3d`); one model load per batch, seconds per mesh; stops SD/TRELLIS first (`AAMT_KEEP_SERVERS=1` to skip) and takes the GPU lock; cuts plain-white concepts itself. **Reserved for background props and simple compact objects** (crates, terminals, beacons, round drones): it guesses the back from one view, so backs come out pale and smooth, and thin limbs fuse into slabs. Use TRELLIS for everything else |
| animate | `anim_client.py` (`ai_resources.make_animated_mesh`) | UniRig rig + skin, Wan2.2-TI2V-5B clip per action rendered from the rigged mesh, CoTracker3 tracks -> fitted bone rotations -> skinned .glb. Venvs under `E:\tools\anim` (`AAMT_ANIM_HOME`), weights in `D:\hf-cache\local`. Hours per creature on this card; every stage cached in a work folder; read `preview.png` and `fit/<clip>.json` (`mean_px`) after. [ANIMATION.md](ANIMATION.md) |
| mesh fix | `mesh_edit.py` (`ai_resources.inspect_mesh` / `preview_mesh` / `edit_mesh`) | Post-generation repair loop: `info` (pieces, tris, texture hints) -> `preview` (4-view PNG to Read) -> `fix` op chain -> preview again. trimesh ops (drop-small, keep-largest, merge, cut, rotate, texture brightness/min-luma/saturation/tint, match-back for pale guessed backs; min-luma lifts the near-black albedo TRELLIS bakes for dark or metal concepts) plus headless Blender (newest under `D:\tools\Blender Foundation`, or `AAMT_BLENDER`) for `--remesh VOXEL` (fuses SF3D shards into one shell, rebakes texture) and `--decimate N`. Typical SF3D fix: `--remesh 0.008 --decimate 14000 --drop-small 0.02`; ~1 min with Blender |
| material | `material_maker_client.py` | CLI |
| pixels | `pixelorama_client.py` | Godot CLI + visible GUI; Magi-Tech: `Tools\Starbound\produce_pixelorama_sheets.py` |
| layering | `ucupaint_support.py` / `ucupaint_bake.py` | Blender add-on; bake real maps onto mesh UVs |
| compress | `tool_paths.texconv_exe` | CLI |
| audio | `audio_pipeline.py` / `audio_asset_library.py` | in-process SA3 + `D:\assets\audio` |

Do not use the Caves of Qud Space-Time Vortex generators, or `Common/bake_texture.py` procedural noise, for Transcendence skins.

One 11 GB GPU. Hold `gpu_hub.acquire_gpu` per request, never across server startup.
Two model servers may be resident; they must not generate at once. Stable Audio 3
is in-process and also takes that lock — do not run it while SD/TRELLIS is generating.

## Audio (Stable Audio 3 + D:\assets\audio)

SFX belong on the `audio` stage. Agents retrieve from the purchased zip library,
then generate a variant — they do not invent a new commercial pack.

- Library: `audio_asset_library.py` (`ingest`, `search_text`, `search_audio`)
- Generate: `audio_pipeline.py` / `ai_resources.make_audio`
- Backend: `aamt_stable_audio_backend.py` (SA3 `init_audio` + GPU lock)
- First run: `python audio_pipeline.py ingest --fast`

Do **not** skip retrieval when the index has assets. Pass `archetype` when known
(`laser`, `ui`, `alien`, `mech`, `ship`, `magic`, `ambience`, `voice`, `impact`).

## Checks before you stop

1. `python ai_resources.py` shows the stage you used.
2. Image jobs went through `:1338`, not Cursor image gen.
3. You did not leave a second SD/TRELLIS server on a duplicate port.
4. Audio jobs went through `make_audio` / `audio_pipeline.py`, referencing `D:\assets\audio`.
