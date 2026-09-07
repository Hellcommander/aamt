# Magi-Tech Spell Asset Pipeline (Starbound)

Vortex-quality workflow for Magi-Tech Arcane Alchemy and Sorcery, with **full SD draft → reference → final** usage (the gap in the older vortex kit).

## GPU / SD notes

Vortex historically often ran SD in **CPU spill** (`model` / `sequential` / `cpu` offload), which pegs host cores.
This pipeline forces **VRAM-first**:

- `SD_OFFLOAD=gpu` (via `Set-StableDiffusionGpuPreferredEnv`)
- `SD_HEADROOM_GB=0` (avoids false CPU spill when 11GB cards report free≈0 after load)
- `SD_SKIP_T5=1` (avoids T5 RAM balloon)
- Asserts live server offload after connect; warns if still on CPU

Watch Task Manager → GPU → **Cuda** (not 3D) while generating.

## Quality flow (required pattern)

```
1. SD server       → high-res DesignDraft PNG  (quality draft)
2. Final           → REFERENCES that draft (img2img / ReferenceImagePath)
3. Multi-module QA → Shared ImageQualityAssessment:
                     - sanity checks
                     - mechanical (qwen3-vl:8b) → score + ISSUES + FIX
                     - aesthetic  (llava:13b)   → score + ISSUES + FIX
4. If score < 15   → feed FIX briefs back into prompt and retry
5. Pack            → Starbound PNG + .frames (optional)
```

Vortex scored with those modules but often only *reported* failures.
This Magi-Tech pipeline **retries with the fix brief** (default 2 retries).

## Quick start

```powershell
# SD server should be up (or let the script auto-start)
..\Start-StableDiffusionServer.ps1

# Generate Magi-Tech spell/projectile icons + optional sheets
.\Generate-MagiTechSpellPipeline.ps1 `
  -ModPath "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery" `
  -AssetId "vortexTwister" `
  -Theme "arcane dust twister spell, swirling funnel, magitech" `
  -Kind spell

# Icons only (skip hard multi-frame sheets)
.\Generate-MagiTechSpellPipeline.ps1 -AssetId "fireBolt" -Theme "fire bolt spell icon" -IconsOnly

# Re-use an existing draft without regenerating it
.\Generate-MagiTechSpellPipeline.ps1 -AssetId "vortexTwister" -Theme "..." -SkipDraft
```

## Outputs

```
<ModPath>/
  DesignDrafts/
    <AssetId>_design_draft.png          # SD quality draft (referenced by finals)
  assets/magitech/generated/<AssetId>/
    <AssetId>.png                       # final icon / sheet
    <AssetId>.frames                    # Starbound frame grid (if animated)
    Source/
      draft_ref.json                    # path + strength used for reference
```

## Tooling this wraps

| Layer | Tool |
|-------|------|
| Detection | `Shared/ToolDetection.psm1`, `ToolsetIntegration.psm1` |
| SD | `Shared/StableDiffusionIntegration.psm1` (`Generate-AssetImageWithSD3`) |
| HTTP SD | `Shared/sd_http_client.py` (size profiles, GPU hub) |
| Ollama | `Shared/OllamaIntegration.psm1` |
| Sheets | `Common/CrossGameSpritesheet.ps1` (`-GameFormat Starbound`) |
| Quality bar | Vortex (`Qud/GenerateVortexAssets.ps1` + `vortex_quality.py`) |

## Pixelorama (headless sprite export)

Pixelorama is the Shared `pixels` stage. It exports authored `.pxo` frames; it
does **not** invent walk/attack limbs from a Unity still (unlike SD img2img).

```powershell
# Status / GUI
python ..\Shared\pixelorama_client.py status
.\Produce-PixeloramaSheets.ps1 -Status
.\Produce-PixeloramaSheets.ps1 -OpenGui grenade_fire

# Pack .pxo → Starbound strip + .frames + .animation
.\Produce-UnityStillAnimations.ps1 -Backend pixelorama -AssetIds grenade_fire
.\Produce-PixeloramaSheets.ps1 -AssetIds grenade_fire
```

Put projects in `<mod>/assets/magitech/pixelorama/<id>.pxo`. See `Shared/PIXELORAMA.md`.

The Steam `Transcendence\Tools\Starbound\Produce-UnityStillAnimations.ps1` stub
forwards here (`-Backend sd|pixelorama`).

## Modes

| Mode | Behavior |
|------|----------|
| Default | Draft → SD final with draft as reference → optional frames |
| `-IconsOnly` | Draft → single-frame final only (avoids hard spritesheets) |
| `-SkipDraft` | Reuse `DesignDrafts/<id>_design_draft.png` |
| `-DraftOnly` | Stop after writing the quality draft |
| `-ImageStrength` | 0.0–1.0 draft influence on SD final (default 0.65) |
