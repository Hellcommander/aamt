# Model Selection Guide

## Overview

The asset generators use the **Shared OllamaIntegration.psm1 tier system** for intelligent model selection. The shared module automatically detects dark tone content and routes to appropriate tiers, reserving `wizardlm-uncensored:latest` for dark tone/escalation tiers.

## Tier System (Shared Module)

The Shared OllamaIntegration module provides a three-tier routing system:

### Tier 1: Standard Tasks
- **visual**: `llama3.1:8b` (default) - Creative concepting, descriptions, visual assets
- **code**: `qwen2.5-coder:14b` - Technical specs, structured planning
- **analysis**: `qwen2.5-coder:14b` - Hybrid tasks, physics, balancing
- **simple**: `qwen2.5-coder:7b` - Fast tasks, JSON repair

### Tier 2: Dark Tone Content
- **dark_tone**: `llama3.1:8b` → `wizardlm-uncensored:latest` (fallback)
- **Auto-detected** via `Test-DarkTone` function with weighted scoring
- **Triggers**: Horror, corrupted, eldritch, mutation, taboo content
- **Threshold**: Score of 3.0+ indicates dark tone

### Tier 3: Escalation
- **escalation**: `wizardlm-uncensored:latest` (last resort)
- **Used when**: Primary models refuse to generate content
- **Automatic**: Only triggered on model refusal detection

## Automatic Dark Tone Detection

The Shared module's `Test-DarkTone` function automatically detects dark tone content with weighted scoring:

### Detection Categories (Weighted)
- **Strong Indicators** (2.0-3.0 weight):
  - Eldritch, Horror, Gore, Corrupted, Monstrous, Glitch, Organic Horror, Body Horror
  
- **Moderate Indicators** (1.5 weight):
  - Void, Undead, Demonic
  
- **Weak Indicators** (1.0 weight):
  - Evil (common in fantasy)

### Detection Keywords
The shared module scans for patterns like:
- `mutation`, `taboo`, `corruption`, `eldritch`, `horror`
- `tentacle`, `writhing`, `pulsating`, `organic growth`
- `abomination`, `grotesque`, `malformed`, `twisted`
- `glitch`, `corrupted data`, `virus`, `infection`
- And many more (see Shared/OllamaIntegration.psm1 for full list)

## Usage Examples

### Regular Content (Auto-selects llama3.1:8b)
```powershell
# Regular spell - uses llama3.1:8b
.\ElinSpellAssetGenerator.ps1 -SpellDescription "Nature Magic - Verdant Pulse" -GenerateAll

# Regular asset - uses llama3.1:8b
.\CustomRaceClassCreatorAssetGenerator.ps1 -ModPath "..." -AssetTypes "icons" -Systems "DragonMagic"
```

### Taboo Content (Auto-selects wizardlm-uncensored)
```powershell
# Mutation spell - automatically uses wizardlm-uncensored
.\ElinSpellAssetGenerator.ps1 -SpellDescription "PCCMutation - Warped Flesh" -GenerateAll

# Mutation system assets - automatically uses wizardlm-uncensored
.\CustomRaceClassCreatorAssetGenerator.ps1 -ModPath "..." -AssetTypes "icons" -Systems "PCCMutation"
```

### Manual Override
```powershell
# Force specific model (not recommended - auto-selection is preferred)
.\ElinSpellAssetGenerator.ps1 -SpellDescription "..." -OllamaModel "llama3.1:8b"
```

## Model Availability

The generators will automatically fall back to available models if the preferred model is not installed. The Shared OllamaIntegration module handles model selection and fallback.

### Recommended Models to Install
```bash
# Regular content models (required)
ollama pull llama3.1:8b
ollama pull qwen2.5-coder:14b

# Taboo content model (required for mutation systems)
ollama pull wizardlm-uncensored:latest
```

## Implementation Details

All asset generators now use **Shared OllamaIntegration.psm1** for model selection:

### CustomRaceClassCreatorAssetGenerator.ps1
- Uses `Invoke-OllamaRequest` with `TaskType="visual"` or `TaskType="code"`
- Automatic dark tone detection via Shared module's `Test-DarkTone`
- Auto-routing to `dark_tone` tier when dark content detected
- Asset type to task type mapping:
  - Visual assets → `TaskType="visual"`
  - Technical assets → `TaskType="code"`

### OllamaAssetGenerator.ps1
- Uses `Invoke-OllamaRequest` with `TaskType="visual"`
- Automatic dark tone detection and tier routing
- No custom model selection needed

### ElinSpellAssetGenerator.ps1
- Uses `Invoke-OllamaRequest` with `TaskType="visual"`
- Automatic dark tone detection from spell descriptions
- Auto-routing to `dark_tone` tier when dark content detected

## Benefits

1. **Unified System**: All tools use the same Shared tier system for consistency
2. **Automatic Detection**: Dark tone content automatically detected via weighted scoring
3. **Resource Efficiency**: Regular content uses faster, more efficient models
4. **Content Appropriateness**: Dark tone content routes to appropriate tier automatically
5. **Refusal Handling**: Automatic escalation to uncensored model if primary models refuse
6. **No Manual Configuration**: No need to specify models - system handles routing automatically

## Migration Notes

The asset generators now use the Shared OllamaIntegration tier system. If you have existing scripts:

1. **Remove explicit model specifications** - Let the Shared module handle routing
2. **Use TaskType parameter** - Specify `TaskType="visual"` or `TaskType="code"` instead of models
3. **Enable AutoEscalate** - Use `-AutoEscalate` flag to enable automatic dark tone detection

### Example Migration

**Before:**
```powershell
.\ElinSpellAssetGenerator.ps1 -SpellDescription "..." -OllamaModel "wizardlm-uncensored:latest"
```

**After:**
```powershell
# Just use the generator - it auto-detects dark tone and routes appropriately
.\ElinSpellAssetGenerator.ps1 -SpellDescription "..." -UseAI
```

The Shared module will automatically:
- Detect dark tone content in the description
- Route to `dark_tone` tier if needed
- Escalate to `escalation` tier if models refuse
- Use appropriate models from the tier system
