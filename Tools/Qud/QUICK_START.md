# Quick Start: Generate High-Quality Space-Time Vortex Assets

## Prerequisites (One-Time Setup)

### 1. Start Ollama
```bash
ollama serve
```

### 2. Install the recommended AI model
```bash
ollama pull wizardlm-uncensored:latest
```

### 3. Install Python dependencies
```bash
pip install Pillow requests
```

## Usage (Every Time)

### Option 1: Quick Launcher (Easiest)
1. Make sure Ollama is running
2. Double-click: `GenerateVortexAssetsQuick.bat`
3. Wait 1-2 minutes for Ollama to generate designs
4. Assets will be created in the mod's Textures and Visuals folders

### Option 2: Custom Path
```batch
GenerateVortexAssets.bat "C:\Path\To\Your\Mod"
```

### Option 3: PowerShell (Better Error Messages)
```powershell
.\GenerateVortexAssets.ps1 "C:\Path\To\Your\Mod"
```

## What Gets Generated

- **Space-Time Vortex_icon.png** - Mutation icon (64x64)
- **BlackHole_visual.png** + 4 animation frames (48x48)
- **WhiteHole_visual.png** + 4 animation frames (48x48)
- **VortexWarning_marker.png** - Pre-spawn warning (48x48)

All assets use Ollama AI to generate unique, high-quality designs.

## Expected Time

- **Total: 1-2 minutes**
  - Icon design: ~10-30 seconds (Ollama AI)
  - Black hole design: ~10-30 seconds (Ollama AI)
  - White hole design: ~10-30 seconds (Ollama AI)
  - Rendering all assets: < 1 second

## Troubleshooting

### Script closes immediately
- The batch file now has `pause` commands
- If you still see issues, use the PowerShell version for better error messages

### "Ollama is not available"
1. Start Ollama: `ollama serve`
2. Verify: `ollama list`
3. Test: `curl http://localhost:11434/api/tags`

### "wizardlm-uncensored not found"
```bash
ollama pull wizardlm-uncensored:latest
```

### Generation takes too long
- This is normal! Ollama takes 10-30 seconds per design
- Total time is about 1-2 minutes
- The AI is generating custom, high-quality designs
- **This is much better than procedural generation**

## Why Ollama is Required

The script **REQUIRES** Ollama because:
1. Procedural generation produces worse assets than base game
2. Ollama generates creative, professional-quality designs
3. AI-guided rendering produces distinctive, high-quality visuals
4. You want BETTER assets, not worse ones

Without Ollama, the script will fail immediately rather than generating low-quality assets.

## Files Reference

- `generate_vortex_professional.py` - **Unified generator** (use this one!)
- `GenerateVortexAssets.bat` - Batch file launcher with custom path
- `GenerateVortexAssetsQuick.bat` - Quick launcher with default path
- `GenerateVortexAssets.ps1` - PowerShell launcher with better error messages
- `VORTEX_ASSET_GENERATOR_README.md` - Full documentation
- `QUICK_START.md` - This file

**Note:** Legacy scripts (`generate_vortex_assets_ollama.py`, `generate_vortex_enhanced_assets.py`, etc.) have been superseded by the unified generator.

## Next Steps

1. Start Ollama: `ollama serve`
2. Double-click: `GenerateVortexAssetsQuick.bat`
3. Wait for completion (1-2 minutes)
4. Check the generated assets in your mod's `Textures/` and `Visuals/` folders
5. Load the mod in Caves of Qud and see your new high-quality visuals!
