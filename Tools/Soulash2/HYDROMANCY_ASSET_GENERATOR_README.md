# Soulash 2 Hydromancy Asset Generator

Generates and validates branding assets for the `arendeth_water_magic` mod, reusing **core_2** tilesheet indices or rendering mod icon/thumbnail via **Stable Diffusion**, **Ollama**, or procedural fallback.

## Asset-size policy

| Asset | Size | Method |
|-------|------|--------|
| `S.png` mod icon | 32×32 | **Always procedural PIL** (+ optional Ollama spec). Never SD. |
| `thumbnail2.png` workshop banner | 800×600 | **SD** when GPU available (~7 GB free); procedural fallback on failure |
| Ability animation tiles / sprite sheets | 32×32 frames | **Procedural PIL** (see animation worker; no SD) |

Overnight runner: `run_overnight_mod_branding.py` — procedural icons first, then SD thumbnails sequentially.
Unified branding: `generate_mod_branding_assets.py` — `--use-sd` applies to thumbnails only.

## Requirements

- Python 3.10+ with **Pillow** (`pip install Pillow`)
- Optional: **Ollama** (design specs, prompt enhancement, vision QA)
- Optional: **Stable Diffusion 3** server on port **1338** (or A1111 on 7860) via `Tools/Shared/StableDiffusionIntegration.psm1`
- **PowerShell 7 (`pwsh`)** recommended for SD; Windows PowerShell 5.1 also works after Shared module encoding fix
- Optional: vision models `qwen3-vl:8b` for `--quality full`

## Quick Start

```bat
cd D:\games\Steam\steamapps\common\Transcendence\Tools\Soulash2
GenerateHydromancyAssets.bat
```

Procedural only (no SD/Ollama):

```powershell
.\GenerateHydromancyAssets.ps1 -Mode procedural -Quality mechanical
```

With Stable Diffusion design drafts:

```powershell
.\GenerateHydromancyAssets.ps1 -Mode sd -Quality mechanical
# or
.\GenerateHydromancyAssets.ps1 -Mode all -UseSD
```

Python directly:

```powershell
python generate_hydromancy_assets.py --mod-path "E:\...\arendeth_water_magic" --mode procedural --quality mechanical
python generate_hydromancy_assets.py --mode sd --use-sd --sd-drafts-dir "...\DesignDrafts"
```

## Modes

| Mode | What it does |
|------|----------------|
| `references` | Applies `core2_asset_references.json` to mod JSON |
| `procedural` | PIL-render `S.png` (32×32) + `thumbnail2.png` (800×600) |
| `ollama` | Ollama JSON design spec + procedural render |
| `sd` | SD3 concept drafts → downscale/post-process → quality gate; falls back to procedural |
| `all` | References + SD if drafts available, else Ollama/procedural |

## Stable Diffusion Pipeline

Follows the Qud vortex generator pattern:

1. **PS1** calls `Generate-AssetImageWithSD3` (Shared module) to create:
   - `DesignDrafts/icon_design_draft.png` (1024×1024)
   - `DesignDrafts/thumbnail_design_draft.png` (1024×768)
2. Prompts are optionally enhanced via Ollama before SD generation
3. **Python** center-crops, downscales, sharpens → `S.png` + `thumbnail2.png`
4. **hydromancy_quality.py** validates size, contrast, palette match

### SD Server Requirements

- **Recommended**: SD3.5 Diffusers server via `Tools\Start-StableDiffusionServer.ps1` on **port 1338**
- Install path: `E:\tools\sd3.5\sd3.5\server.py` (HTTP/1.1, no HTTP/2 required)
- Python client `Tools/Shared/sd_http_client.py` is used automatically (works on Windows PowerShell 5.1+)
- PowerShell HTTP/2 client remains as fallback for OpenAI-style SD3 API servers

> **IMPORTANT — the SD3.5 server MUST run as Administrator.** `server.py` hard-exits
> without admin rights (it needs symlink access for the Hugging Face model cache).
> An agent session cannot self-elevate, so this is always a **manual, one-time step**
> per boot. Easiest options:
>
> - Double-click **`E:\tools\sd3.5\sd3.5\start_server_admin.bat`** — it self-elevates via a
>   normal UAC prompt, then launches the server on port 1338. (Recommended.)
> - Or right-click `start_server.bat` → *Run as administrator*.
> - Or enable Windows **Developer Mode** (Settings > Privacy & Security > For developers)
>   so symlinks work without elevation.
>
> Leave that window open, then run the generator in another shell.

### SD Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `StableDiffusionIntegration.psm1 not loaded` | Unicode parse error in module (fixed) | Update Shared module; re-run generator |
| `HTTP 426 Upgrade Required` | Wrong service on port (e.g. WebSocket++ on 1337) | Start SD3.5 on **1338**; detection now rejects non-SD ports |
| `No Stable Diffusion server detected` | SD3.5 not running | Launch `start_server_admin.bat` (self-elevating) or run `start_server.bat` as Administrator |
| `ERROR: Administrator privileges required!` | server.py needs admin for HF symlink cache | Use `start_server_admin.bat`, or enable Windows Developer Mode |
| SD drafts fail, procedural works | Expected fallback | Check SD server logs; verify `python sd_http_client.py --detect-only` |

Detect SD server:
```powershell
python D:\games\Steam\steamapps\common\Transcendence\Tools\Shared\sd_http_client.py --detect-only
```

## Quality Tiers

| Tier | Checks |
|------|--------|
| `fast` | File exists, PIL size/aspect |
| `mechanical` | Alpha coverage, luma variance, palette match |
| `full` | Mechanical + Ollama vision model scoring |

## Mod Asset Map

`core2_asset_references.json` documents curated **core_2** tilesheet indices for abilities, passives, skill, and buildings. Custom `assets.json` is not required when `mods_required` includes `core_2`.

## Skill Animations

Skills support an optional `"animation"` field (string), using the same animation registry as abilities and weather:

```json
{
  "id": "arendeth_water_magic_hydromancy",
  "name": "Hydromancy",
  "image": 17,
  "animation": "196"
}
```

- **Value format**: numeric id (`"196"`) or mod-prefixed id (`"core_2_Heavy_Rain"`)
- **Source files**: `{mod}/animations/*.json` — copy from core_2 or create in the Animation Editor (F2)
- **Hydromancy uses**: `"196"` → core_2 Water wave (`animations/196_Water_wave.json`)
- **No custom animation assets required** when referencing core_2 animations

Other water-themed core_2 animation ids: `"113"` (Rain), `"core_2_Heavy_Rain"`, `"core_2_Summon_rain"`.

## Files

```
Tools/Soulash2/
├── generate_hydromancy_assets.py
├── apply_core2_references.py
├── hydromancy_quality.py
├── GenerateHydromancyAssets.ps1
├── GenerateHydromancyAssets.bat
└── HYDROMANCY_ASSET_GENERATOR_README.md

Mod/arendeth_water_magic/
├── S.png                    (32×32 mod icon)
├── thumbnail2.png           (800×600 workshop thumbnail)
├── core2_asset_references.json
└── DesignDrafts/            (SD concept art, optional)
```

## Shared Infrastructure

- `Tools/Shared/StableDiffusionIntegration.psm1` — SD3 txt2img/img2img
- `Tools/Shared/ollama_integration.py` — prompt enhancement + vision QA
- `Tools/Qud/GenerateVortexAssets.ps1` — design draft workflow reference
