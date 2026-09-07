# AI-Assisted Modding Tools (AAMT) - Branding Update

This document summarizes the branding update from "Transcendence Tools" to **AI-Assisted Modding Tools (AAMT)**.

## Overview

The toolset has been rebranded to better reflect its multi-game, AI-assisted nature. The name "AI-Assisted Modding Tools" (AAMT) emphasizes:
- **AI-powered** capabilities (Ollama + Stable Diffusion 3)
- **Multi-game** modding support
- **Comprehensive toolkit** approach

## Files Updated

### Core Modules
- ✅ `Shared/ToolsetInfo.psm1` - **NEW** - Central toolset information module
- ✅ `Shared/OllamaIntegration.psm1` - Updated header to reference AAMT
- ✅ `Shared/StableDiffusionIntegration.psm1` - Updated header to reference AAMT
- ✅ `Shared/ollama_integration.py` - Updated header to reference AAMT

### Documentation
- ✅ `README_AAMT.md` - **NEW** - Main toolset overview and documentation
- ✅ `UNCENSORED_IMAGE_GENERATOR_README.md` - Updated license reference
- ✅ `SHARED_SETTINGS_INTEGRATION_SUMMARY.md` - Updated toolset reference

### Scripts
- ✅ `Start-StableDiffusionServer.ps1` - Added AAMT header comment
- ✅ `Install-CondaAndSetup.ps1` - Added AAMT header comment
- ✅ `Starbound/OllamaImageGenerator.ps1` - Added AAMT header comment
- ✅ `Elin/OllamaAssetGenerator.ps1` - Added AAMT header comment

## Toolset Information Module

The new `Shared/ToolsetInfo.psm1` module provides:
- `Get-ToolsetName()` - Returns "AI-Assisted Modding Tools"
- `Get-ToolsetAcronym()` - Returns "AAMT"
- `Get-ToolsetInfo()` - Returns full toolset information object

### Usage Example

```powershell
Import-Module "$PSScriptRoot\Shared\ToolsetInfo.psm1"
$toolsetName = Get-ToolsetName
$acronym = Get-ToolsetAcronym
$info = Get-ToolsetInfo
```

## Notes

- Game-specific guide files (e.g., `*_ASSET_GENERATION_GUIDE.md`) still reference "Starbound Ollama Asset Generator suite" - this is intentional as they describe game-specific functionality within the broader AAMT framework.
- The toolset supports multiple games: Starbound, Elin, Caves of Qud, Terraria, Tales of Maj'Eyal, and Transcendence (uses Transcendence art as reference source).

## Future Updates

Consider updating:
- Individual script help text (`.SYNOPSIS` and `.DESCRIPTION`) to reference AAMT where appropriate
- Any remaining documentation that references "Transcendence Tools"
- User-facing messages and output text
