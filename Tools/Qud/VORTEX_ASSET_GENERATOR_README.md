# Unified Space-Time Vortex Asset Generator

**Professional-quality asset generator for the Space-Time Vortex mutation using Ollama AI.**

This is the **unified generator** that merges all improvements from multiple generator scripts into one comprehensive solution.

## Requirements

### 1. Ollama MUST be running
This generator **REQUIRES** Ollama to be running. Without Ollama, it will fail immediately because the procedural fallback produces worse assets than the existing Caves of Qud visuals.

**Start Ollama before running this script!**

### 2. Python Dependencies
```bash
pip install Pillow requests
```

**Optional (for audio generation):**
```bash
pip install numpy soundfile
```

### 3. Recommended Ollama Models
The script uses multi-AI support and works best with:
- `wizardlm-uncensored:latest` - For visual/aesthetic design (visual AI)
- `codellama` or similar - For mathematical/geometric design specs (math AI)

```bash
ollama pull wizardlm-uncensored:latest
ollama pull codellama  # Optional, for math-focused design specs
```

The generator will automatically select appropriate models using the model router if available.

## Mod Integration (v2.3.0+)

The mod runs with **ASCII fallbacks** when `Textures/` is empty. After generation:

1. PNGs are written to `Textures/` and `Visuals/`
2. `vortex_mod_integration.py` auto-patches `ObjectBlueprints.xml` and `Mutations.xml`
3. Mod C# code (`VortexAssetHelper`) detects files at runtime for particles and warning markers

Re-run integration only (if PNGs already exist):

```bash
python generate_vortex_professional.py "MOD_PATH" --integration-only
```

## Usage

### Batch File (Windows)
```batch
GenerateVortexAssets.bat "C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Improved and Rebalanced Space Time Vortex"
```

### Python Script Directly
```bash
python generate_vortex_professional.py "MOD_PATH"

# Quality modes
python generate_vortex_professional.py "MOD_PATH" --quality full    # default: smooth animations + ImageMagick
python generate_vortex_professional.py "MOD_PATH" --quality fast   # skip validation/smoothing

# Cache and drafts
python generate_vortex_professional.py "MOD_PATH" --no-cache       # force fresh Ollama calls
python generate_vortex_professional.py "MOD_PATH" --no-drafts      # ignore DesignDrafts/ palette hints
```

**With custom Ollama URL or model:**
```bash
python generate_vortex_professional.py "MOD_PATH" --ollama-url "http://localhost:11434" --model "wizardlm-uncensored:latest"
```

## What It Generates

### 1. Mutation Icon (96x96 - High Resolution)
- `Space-Time Vortex_icon.png`
- Spiral singularity design with event horizon
- Blue/purple color scheme (mental mutation)
- Multiple layers: outer glow, spiral pattern, event horizon rings, void center
- **4x supersampling** with LANCZOS anti-aliasing for smooth edges

### 2. Black Hole Animation (64x64 - High Resolution)
- `BlackHole_visual.png` (main visual)
- `BlackHole_frame00.png` through `BlackHole_frame15.png` (**16 frames** for ultra-smooth animation)
- Dark, ominous appearance with spiral accretion disk
- Rotating animation with pulsing effects
- **4x supersampling** with layered effects (5+ layers per frame)

### 3. White Hole Animation (64x64 - High Resolution)
- `WhiteHole_visual.png` (main visual)
- `WhiteHole_frame00.png` through `WhiteHole_frame15.png` (**16 frames** for ultra-smooth animation)
- Bright, explosive appearance with radiating energy
- Counter-rotating animation with energy burst effects
- **4x supersampling** with layered effects

### 4. Animated Particles (16x16)
- `VortexParticle_spark_blue_frame00.png` through `frame07.png` (6 types × 8 frames = 48 frames)
- Spark, swirl, and dot particle types in multiple colors
- Rotating, spiraling, and pulsing animations

### 5. Distortion Overlays (32x32)
- `VortexDistortion_00.png`, `VortexDistortion_01.png`, `VortexDistortion_02.png`
- Space-time distortion texture overlays
- 3 variants for visual variety

### 6. Ability Icons (64x64)
- `VortexAbility_Aggressive.png` - Diamond-shaped offensive icon
- `VortexAbility_Defensive.png` - Circle/shield-shaped defensive icon

### 7. Warning Marker (64x64)
- `VortexWarning_marker.png`
- Pre-spawn warning indicator
- Yellow/orange pulsing ring with exclamation mark

### 8. White Hole Sounds (Optional)
- `WhiteHole_ambient.ogg` - Low harmonic drone with pitch modulation
- `WhiteHole_active.ogg` - Sharp whoosh with crystalline chimes
- `WhiteHole_ejection.ogg` - Whoosh with Doppler effect
- **Requires:** `numpy` and `soundfile` packages

## Output Locations

Assets are saved to:
- `Textures/` - Standard Qud mod location (all visual assets)
- `Visuals/` - Alternative location for compatibility (icons and main visuals)
- `Sounds/` - Audio files (if audio generation is enabled)

## How It Works

### Phase 1: AI Design Generation (Multi-AI Support)
- **Math-focused AI (analysis)**: Generates design specifications for geometry, patterns, and mathematical properties
- **Visual AI (wizardlm-uncensored)**: Generates aesthetic specifications for colors, style, and visual effects
- Calls Ollama with detailed prompts for each asset type
- Gets structured JSON design specifications (colors, shapes, effects, animation parameters)
- **Retry logic**: Automatically retries failed AI calls (2 attempts)

### Phase 2: Mathematical Rendering
- Renders at **4x resolution** (e.g., 256x256 for 64x64 output)
- Uses precise mathematical calculations for:
  - Spiral patterns and accretion disks
  - Rotating animations with smooth interpolation
  - Pulsing effects with sine wave calculations
  - HSV color space for vibrant gradients
- Applies **5+ layers per frame**:
  - Outer space-time distortion glow
  - Rotating spiral arms/accretion disk
  - Event horizon rings
  - Void/energy core
  - Inner hotspot

### Phase 3: Image Optimization
- **LANCZOS downscaling** from 4x resolution to final size
- Smooth filtering for anti-aliased edges
- Professional image optimization

### Phase 4: Audio Generation (Optional)
- Generates white hole sounds using procedural audio synthesis
- Creates ambient, active, and ejection sound effects
- Requires `numpy` and `soundfile` packages

### Saving
- Saves as PNG files with alpha transparency
- Saves to Textures, Visuals, and Sounds folders
- Validates file creation and size

## Error Handling

The generator includes robust error handling:

### Connection Errors
- **Ollama not running**: Clear error message with troubleshooting steps
- **Connection timeout**: Automatic retry with detailed diagnostics
- **Model unavailable**: Graceful fallback to available models or model router

### Generation Errors
- **AI design failures**: Automatic retry (2 attempts) with improved JSON parsing
- **Asset generation failures**: Continues with other assets, reports errors at end
- **File save failures**: Validates file creation and size, reports specific errors

### Error Reporting
- Tracks errors per asset type
- Reports partial completion if some assets fail
- Provides detailed error messages with troubleshooting suggestions

**Note:** The generator requires Ollama for AI-designed assets. There is no procedural fallback because it would produce lower-quality assets than the base game.

## Troubleshooting

### "Ollama is not available"
1. Start Ollama: `ollama serve`
2. Verify it's running: `ollama list`
3. Pull the recommended model: `ollama pull wizardlm-uncensored:latest`

### "Ollama integration module not found"
Make sure the Ollama integration module exists at:
`D:\games\Steam\steamapps\common\Transcendence\Tools\Shared\ollama_integration.py`

### Script hangs/times out
- Check Ollama is responding: `curl http://localhost:11434/api/tags`
- Try a smaller model if wizardlm-uncensored is slow
- Check available RAM (models need memory)

### Assets don't look good
The script REQUIRES Ollama specifically because:
- Procedural generation produces worse assets than base game
- Ollama generates creative, high-quality design specifications
- AI-guided rendering produces professional-looking assets

## Example Output

After running successfully:
```
============================================================
Space-Time Vortex Asset Generator (Ollama)
============================================================
Mod: Improved and Rebalanced Space Time Vortex
Path: C:\Users\Arend\AppData\LocalLow\...\Improved and Rebalanced Space Time Vortex

Testing Ollama connection...
Generating Space-Time Vortex assets with Ollama...
NOTE: This requires Ollama to be running for high-quality AI-generated designs.

1. Generating mutation icon...
  Calling Ollama for Space-Time Vortex icon design...
  Ollama response received in 12.3 seconds
  [OK] Ollama generated icon design
   [OK] Created: Space-Time Vortex_icon.png

2. Generating black hole visuals...
  Calling Ollama for black hole visual design...
  [OK] Ollama generated black hole design
   [OK] Created 4 frames + main visual

3. Generating white hole visuals...
  Calling Ollama for white hole visual design...
  [OK] Ollama generated white hole design
   [OK] Created 4 frames + main visual

4. Generating warning marker...
   [OK] Created: VortexWarning_marker.png

============================================================
Summary
============================================================
Icon: 1
Black hole frames: 4
White hole frames: 4
Warning marker: 1

Assets saved to:
  - C:\...\Improved and Rebalanced Space Time Vortex\Textures
  - C:\...\Improved and Rebalanced Space Time Vortex\Visuals
```

## Quality Assessment

The generator includes **automatic quality assessment** using vision models (optional, via PowerShell wrapper):

### Quality Assessment Depth Options

- **"fast"** (default): Sanity checks only (file exists, not empty, valid PNG)
- **"mechanical"**: Uses Qwen3-VL-8B for mechanical quality checks (artifacts, corruption, technical issues)
- **"full"**: Uses both Qwen3-VL-8B and LLaVA:13b for complete quality assessment (technical + aesthetic)

### Usage with Quality Assessment

**PowerShell wrapper (recommended for quality assessment):**
```powershell
.\GenerateVortexAssets.ps1 -ModPath "MOD_PATH" -QualityAssessmentDepth "full"
```

**Batch file (uses PowerShell wrapper with full quality assessment by default):**
```batch
GenerateVortexAssets.bat
```

### Quality Assessment Features

- **Automatic detection** of low-quality assets (score < 15.0/20)
- **Detailed reporting** with quality scores for each image
- **Low-quality asset identification** for manual regeneration
- **Vision model integration** (Qwen3-VL-8B, LLaVA:13b) for professional quality checks

### Quality Scores

- **Score range**: 0-20
- **Pass threshold**: ≥ 15.0
- **Low quality**: < 15.0 (recommended for regeneration)

**Note:** Quality assessment requires the PowerShell wrapper. Direct Python execution skips quality assessment.

## Performance

- **AI Design Phase**: ~1-2 minutes (multiple Ollama calls for all asset types)
- **Rendering Phase**: ~30-60 seconds (4x supersampling + 16 frames × multiple assets)
- **Audio Generation**: ~5-10 seconds (if enabled)
- **Quality Assessment**: ~30-60 seconds (if enabled, depends on number of images and depth)
- **Total time: ~2-5 minutes** (with quality assessment)

The time is primarily spent on:
1. Ollama generating high-quality design specifications (multi-AI calls)
2. 4x supersampling rendering (rendering at 4x resolution, then downscaling)
3. Generating 16 frames per animation (instead of 4-8 frames)
4. Quality assessment with vision models (if enabled)

**Quality vs. Speed:** This generator prioritizes **QUALITY over SPEED**:
- Professional-quality assets with smooth animations
- High-resolution support for tile scaling mods
- Multi-AI design generation for optimal results

## Key Features

### Rendering Quality
- ✅ **4x Supersampling** - Renders at 4x resolution, downscales with LANCZOS for smooth edges
- ✅ **HSV Color Space** - Vibrant gradients and smooth color transitions
- ✅ **Multiple Layered Effects** - 5+ layers per frame for depth and realism
- ✅ **Professional Smooth Filtering** - Anti-aliased edges and professional polish

### Animation Quality
- ✅ **16-Frame Ultra-Smooth Animation** - Upgraded from 8 frames for smoother playback
- ✅ **Frame Interpolation** - Smooth rotation and pulse calculations
- ✅ **High-Resolution Support** - 64x64 animations, 96x96 icons for tile scaling mods

### AI Integration
- ✅ **Multi-AI Support** - Math AI for geometry, Visual AI for aesthetics
- ✅ **Model Router Integration** - Automatic model selection
- ✅ **Enhanced Design Prompts** - Structured JSON specifications
- ✅ **Retry Logic** - Automatic retry for failed AI calls

### Asset Types
- ✅ **Complete Asset Set** - Icons, animations, particles, overlays, ability icons, warning markers
- ✅ **Audio Generation** - Optional white hole sound effects
- ✅ **High-Resolution** - Support for tile scaling mods

## Legacy Scripts (Archived)

The following scripts have been **archived** and superseded by the unified generator:
- `archive/generate_vortex_assets_ollama.py.deprecated` - Basic generator (8 frames, standard resolution)
- `archive/generate_vortex_enhanced_assets.py.deprecated` - Enhanced assets
- `archive/generate_vortex_premium_assets.py.deprecated` - Premium assets

**All features from these scripts have been merged into `generate_vortex_professional.py` (the unified generator).**

See `archive/DEPRECATED_SCRIPTS_README.md` for migration guide and details.

**Use `generate_vortex_professional.py` (the unified generator) for all new asset generation.**

## Quality Assessment Integration

The generator now includes **automatic quality assessment** when using the PowerShell wrapper:

- **Integrated ImageQualityAssessment.psm1** for generated assets
- **Vision models** (Qwen3-VL-8B, LLaVA:13b) verify asset quality
- **Low-quality detection** with automatic reporting
- **Quality scores** (0-20 scale) for each generated image
- **Regeneration recommendations** for assets scoring < 15.0

**Usage:**
- Use `GenerateVortexAssets.ps1` with `-QualityAssessmentDepth "full"` for complete quality assessment
- Use `GenerateVortexAssets.bat` (calls PowerShell wrapper with full quality assessment by default)
