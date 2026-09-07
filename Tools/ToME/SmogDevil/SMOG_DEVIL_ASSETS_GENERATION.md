# Smog Devil Assets — Ollama + SD3.5

## Pipeline

1. **Ollama** (`:11434`) writes a ToME-style icon prompt (`wizardlm-uncensored`)
2. **SD3.5** (`:1338`) renders the image via `Tools\Shared\sd_http_client.py`
3. Post-process: black-background cut-out → 64×64 RGBA
4. Drafts land in `Tools\Output\SmogDevilAssets` (not the live mod)

Procedural Pillow generators are **not** used for shipped art.

## Prerequisites

```powershell
# Terminal A — Ollama already serving models
# Terminal B — SD API
D:\games\Steam\steamapps\common\Transcendence\Tools\Start-StableDiffusionServer.ps1
```

Confirm:

```powershell
curl.exe http://127.0.0.1:11434/api/tags
curl.exe http://127.0.0.1:1338/ping
```

## Usage

```powershell
cd D:\games\Steam\steamapps\common\Transcendence\Tools\ToME\SmogDevil

# One smoke asset
python generate_smog_devil_assets.py --main-only --limit 1

# All main effects/items
python generate_smog_devil_assets.py --main-only

# Talents too (slow — one SD job each)
python generate_smog_devil_assets.py

# Only after visual review
python generate_smog_devil_assets.py --install-mod
```

## Policy

Live addon prefers vanilla `image=` refs (`object/staff.png`, `effects/steam_power.png`, etc.).
Install custom PNGs only when they clearly beat those.
