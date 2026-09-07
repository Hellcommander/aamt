# Stable Diffusion 3 Texture Integration

## Overview

The quality generator now supports **Stable Diffusion 3 Medium** for generating high-quality creative textures and design drafts. SD3 provides AI-generated textures that complement the procedural texture generation system.

## Features

### 1. **Blender Model Textures**
- **Purpose**: High-quality diffuse maps for Blender models
- **Resolution**: 1024x1024 or 2048x2048
- **Style**: Organic-mechanical hybrid with bioluminescent details
- **Output**: `Stage1_Draft/Textures/Blender/{ship_id}_diffuse_v{##}.png`

### 2. **Projectile Textures**
- **Types**: Energy bolts, plasma balls, bio-missiles
- **Resolution**: 512x512
- **Style**: Nova Drift aesthetic with high-energy glows
- **Output**: `Stage1_Draft/Textures/Projectiles/{type}_v{##}.png`

### 3. **Design Drafts**
- **Purpose**: Concept art and design references
- **Resolution**: 1024x1024
- **Style**: Cinematic concept art with dramatic lighting
- **Output**: `Stage1_Draft/Textures/DesignDrafts/{ship_id}_design_draft_v{##}.png`

### 4. **Full Ship Artwork**
- **Purpose**: Complete ship renders showing the entire ship design
- **Resolution**: 2048x2048 (ultra-high detail)
- **Views**: Side, Front, Three-quarter, Top, Dramatic angles
- **Style**: Complete ship artwork, all features visible, cinematic quality
- **Output**: `Stage1_Draft/Textures/FullShipArtwork/{ship_id}_full_ship_{view}_v{##}.png`

## Integration

### Quality Generator Integration

SD3 texture generation is **optional** and runs after standard texture generation:

1. **Standard textures** are generated first (required for Blender)
2. **SD3 textures** are generated as enhancement (if `--use-sd3` flag is set)
   - **Uses procedural textures as reference** for better visual consistency
   - **Image-to-image mode** with configurable strength (default: 0.7)
3. Both texture types are saved to `Stage1_Draft/Textures/`

### Image-to-Image Generation

SD3 texture generator now supports **image-to-image** generation:

- **Reference Images**: Uses procedural textures as visual reference
- **Image Strength**: Controls how much the reference influences output (0.0-1.0)
  - `0.7` (default): Balanced - reference guides style, prompt guides details
  - `0.5`: More creative freedom, less reference influence
  - `0.9`: Strong reference influence, minimal variation
- **Benefits**: 
  - Better visual consistency with existing textures
  - More accurate color matching
  - Preserves procedural texture patterns while adding AI creativity

### Usage

```bash
# Enable SD3 texture generation (all types)
python space_whale_quality_asset_generator.py --use-sd3

# Generate only design drafts
python space_whale_quality_asset_generator.py --use-sd3 --sd3-texture-type design_draft

# Generate only Blender textures
python space_whale_quality_asset_generator.py --use-sd3 --sd3-texture-type blender

# Generate only projectile textures
python space_whale_quality_asset_generator.py --use-sd3 --sd3-texture-type projectile

# Custom variation count
python space_whale_quality_asset_generator.py --use-sd3 --sd3-variations 5
```

### Standalone Usage

```powershell
# Generate all texture types
.\SpaceWhaleSD3TextureGenerator.ps1 `
    -ShipRegistry "space_whale_ship_example.json" `
    -VisualRegistry "space_whale_visual_language_registry.json" `
    -OutputDir "Output/Textures" `
    -TextureType "all" `
    -Variations 3

# Generate only design drafts
.\SpaceWhaleSD3TextureGenerator.ps1 `
    -ShipRegistry "space_whale_ship_example.json" `
    -VisualRegistry "space_whale_visual_language_registry.json" `
    -OutputDir "Output/Textures" `
    -TextureType "design_draft" `
    -Variations 5 `
    -ShipId "leviathan_alpha"

# Generate with reference textures (image-to-image)
.\SpaceWhaleSD3TextureGenerator.ps1 `
    -ShipRegistry "space_whale_ship_example.json" `
    -VisualRegistry "space_whale_visual_language_registry.json" `
    -OutputDir "Output/Textures" `
    -TextureType "all" `
    -Variations 3 `
    -ReferenceTextureDir "Output/Textures" `
    -ImageStrength 0.7
```

## Requirements

### Stable Diffusion 3 Server
- **Server**: `stable-diffusion-api-server` (OpenAI-compatible API)
- **Default URL**: `http://localhost:1337`
- **Model**: SD3 Medium (recommended)
- **Auto-start**: Script can auto-start server if `Start-StableDiffusionServer.ps1` exists

### Dependencies
- **PowerShell 5.1+** or **PowerShell Core 7+**
- **StableDiffusionIntegration.psm1** (in `Tools/Shared/`)
- **OllamaIntegration.psm1** (optional, for prompt enhancement)

## Prompt Enhancement

SD3 texture generator uses **Ollama for prompt enhancement** and **detailed ship descriptions**:

1. **Ship Description Extraction**: Extracts detailed information from ship registry:
   - Ship name and description
   - Dimensions (length, width, height)
   - Profile type (streamlined, etc.)
   - Skin type (bioluminescent, etc.)
   - Gill vent count
   - Breathing speed
   - Dorsal crest glow settings
   - Animation properties

2. **Enhanced Prompts**: Creates detailed prompts based on:
   - Ship description text
   - Ship specifications from registry
   - Visual language colors
   - Design draft references (when available)

3. **Ollama Enhancement**: Ollama further enhances prompts with visual details

4. **Reference-Based Generation**: Uses design drafts as primary visual reference

**Benefits**:
- More accurate representation of ship design
- Better style consistency with ship specifications
- Context-aware generation based on actual ship data
- Design drafts guide visual consistency

## Image-to-Image Generation

SD3 texture generator supports **image-to-image** mode for better results:

### How It Works

1. **Reference Image Detection**: Automatically finds procedural textures as reference
   - Looks for: `{ship_id}_diffuse.png`, `{ship_id}_texture.png`, or any matching PNG
   - Falls back to text-to-image if no reference found

2. **Image Conditioning**: SD3 uses reference image to guide generation
   - **Color matching**: Preserves color palette from reference
   - **Pattern preservation**: Maintains texture patterns and structure
   - **Style consistency**: Ensures visual coherence with existing assets

3. **Strength Control**: Configurable influence level
   - `0.7` (default): Balanced - reference guides style, prompt adds creativity
   - `0.5`: More creative freedom, less strict adherence to reference
   - `0.9`: Strong reference influence, minimal variation

### Benefits

✅ **Better Visual Consistency**: Matches existing procedural textures
✅ **Color Accuracy**: Preserves color palette from reference
✅ **Pattern Preservation**: Maintains texture structure while adding AI creativity
✅ **Quality Improvement**: Reference images provide better visual guidance than text alone
✅ **Flexible Control**: Adjustable strength for different use cases

### Use Cases

- **Blender Textures**: Use design drafts as primary reference, then procedural textures
- **Design Drafts**: Use existing design drafts as reference for consistency
- **Full Ship Artwork**: Use design drafts as primary reference for complete ship visualization
- **Projectile Textures**: Use base textures as reference for consistent style

## Description-Based Generation

SD3 texture generator now **creates images based on ship descriptions and design drafts**:

### How It Works

1. **Ship Description Extraction**: Extracts detailed information from ship registry:
   - Ship name and description text
   - Dimensions (length × width × height)
   - Profile type (streamlined, etc.)
   - Skin type (bioluminescent, etc.)
   - Gill vent count
   - Breathing speed and animation properties
   - Dorsal crest glow settings

2. **Enhanced Prompts**: All prompts include:
   - **Ship description**: Full text description from registry
   - **Ship specifications**: Dimensions, profile, skin type, etc.
   - **Visual details**: Colors, materials, lighting effects
   - **Reference instructions**: Explicitly tells AI to match description and use design drafts

3. **Design Draft Priority**: Design drafts are used as **primary reference**:
   - **Blender textures**: Design drafts → Best textures → Procedural textures
   - **Full ship artwork**: Design drafts → Best artwork → Other artwork
   - **Design drafts**: Best design drafts → Existing design drafts

4. **Reference Strength**: Higher strength for design drafts (0.85 vs 0.7 default):
   - Design drafts provide complete visual reference
   - Better consistency across all generated assets
   - More accurate representation of ship design

### Benefits

✅ **Accurate Representation**: Images match ship descriptions and specifications
✅ **Design Consistency**: Design drafts ensure visual consistency across all assets
✅ **Specification-Based**: Uses actual ship data (dimensions, properties) in prompts
✅ **Reference-Guided**: Design drafts provide complete visual guide
✅ **Quality Improvement**: Better prompts + better references = better results

## Best Images for Reference

SD3 texture generator automatically **saves the best generated images** for future reference:

### How It Works

1. **Quality Assessment**: Each generated image is scored based on:
   - File size (indicates detail level)
   - Resolution (higher = better)
   - Basic quality heuristics

2. **Best Image Selection**: The highest-scoring image per ship/category is saved to `Best/` directory

3. **Automatic Reference**: Best images are **automatically used as reference** in future generation:
   - Priority: BEST images → Design drafts → Other textures
   - Better visual consistency across generations
   - Quality improves over time

### Best Image Structure

```
Best/
├── blender/          (Best Blender textures)
├── projectile/       (Best projectile textures)
├── design_draft/     (Best design drafts)
└── full_ship_artwork/ (Best full ship artwork)
```

### Benefits

✅ **Quality Improvement**: Best images used as reference improve future generation
✅ **Consistency**: Maintains visual style across multiple generation runs
✅ **Reference Library**: Builds a library of best assets for reuse
✅ **Automatic Selection**: No manual curation needed
✅ **Future Use**: Best images automatically prioritized in reference detection

## Output Structure

```
Stage1_Draft/Textures/
├── Blender/
│   ├── leviathan_alpha_diffuse_v00.png
│   ├── leviathan_alpha_diffuse_v01.png
│   └── serpent_void_diffuse_v00.png
├── Projectiles/
│   ├── energy_bolt_v00.png
│   ├── plasma_ball_v00.png
│   └── bio_missile_v00.png
├── DesignDrafts/
│   ├── leviathan_alpha_design_draft_v00.png
│   └── serpent_void_design_draft_v00.png
├── FullShipArtwork/
│   ├── leviathan_alpha_full_ship_side_v00.png
│   ├── leviathan_alpha_full_ship_front_v00.png
│   ├── leviathan_alpha_full_ship_three_quarter_v00.png
│   ├── leviathan_alpha_full_ship_dramatic_v00.png
│   └── serpent_void_full_ship_side_v00.png
└── Best/
    ├── blender/
    │   ├── leviathan_alpha_best.png
    │   └── serpent_void_best.png
    ├── projectile/
    │   ├── energy_bolt_best.png
    │   └── plasma_ball_best.png
    ├── design_draft/
    │   ├── leviathan_alpha_best.png
    │   └── serpent_void_best.png
    └── full_ship_artwork/
        ├── leviathan_alpha_best.png
        └── serpent_void_best.png
```

## Configuration

### Quality Generator Config

```python
config.use_sd3_textures = True  # Enable SD3 generation
config.sd3_texture_type = "all"  # "blender", "projectile", "design_draft", "all"
config.sd3_variations = 3  # Variations per texture type
```

### SD3 Generation Parameters

- **Width/Height**: 1024x1024 (Blender/Design), 512x512 (Projectiles)
- **Steps**: 28 (SD3 Medium optimized)
- **Guidance Scale**: 7.0
- **Negative Prompt**: Prevents blurry, low-quality, pixelated outputs
- **Ollama Enhancement**: Enabled by default

## Use Cases

### 1. **Blender Model Textures**
- **When**: Need high-quality diffuse maps for Blender models
- **Benefit**: Creative, detailed textures with organic-mechanical aesthetic
- **Alternative**: Procedural texture generator (faster, but less creative)

### 2. **Projectile Textures**
- **When**: Need unique projectile visuals
- **Benefit**: High-energy, Nova Drift-style projectile textures
- **Types**: Energy bolts, plasma balls, bio-missiles

### 3. **Design Drafts**
- **When**: Need concept art or design references
- **Benefit**: Cinematic concept art for reference and inspiration
- **Use**: Visual reference, documentation, marketing materials

### 4. **Full Ship Artwork**
- **When**: Need complete ship renders showing the entire design
- **Benefit**: Ultra-high detail complete ship artwork in multiple views
- **Views**: Side, Front, Three-quarter, Top, Dramatic angles
- **Use**: Complete ship visualization, marketing, documentation, reference for all angles

## Performance

### Generation Time
- **Blender textures**: ~30-60 seconds per image (1024x1024)
- **Projectile textures**: ~15-30 seconds per image (512x512)
- **Design drafts**: ~30-60 seconds per image (1024x1024)
- **Full ship artwork**: ~60-120 seconds per image (2048x2048, higher detail)

### Total Time (3 variations each, all types)
- **Per ship (without full artwork)**: ~5-10 minutes
- **Per ship (with full artwork, 4 views)**: ~15-25 minutes
- **All ships (2 ships, with full artwork)**: ~30-50 minutes

### Optimization Tips
1. **Use specific texture types** instead of "all" to reduce time
2. **Filter by ship ID** to generate for specific ships only
3. **Reduce variations** if time is limited (default: 3)
4. **Run SD3 generation separately** from main pipeline if needed

## Integration with Pipeline

### Stage 1: Draft Generation
1. Standard textures generated (required)
2. SD3 textures generated (optional, if `--use-sd3`)
3. Both saved to `Stage1_Draft/Textures/`

### Stage 6: Spritesheet Generation
- Blender uses **standard textures** (required)
- SD3 textures can be used as **alternatives** or **enhancements**
- Design drafts used for **reference** during spritesheet creation

## Error Handling

### SD3 Server Not Available
- **Behavior**: SD3 generation is skipped with warning
- **Impact**: Pipeline continues with standard textures only
- **Recovery**: Start SD3 server and re-run with `--use-sd3`

### Ollama Not Available
- **Behavior**: Prompts used without enhancement
- **Impact**: Slightly less detailed prompts, but generation continues
- **Recovery**: Start Ollama service for better results

### Generation Failures
- **Behavior**: Individual failures logged, generation continues
- **Impact**: Some textures may be missing, but pipeline continues
- **Recovery**: Re-run with `--resume` to regenerate failed textures

## Best Practices

### 1. **Use SD3 for Creative Enhancement**
- Standard textures: Fast, procedural, consistent
- SD3 textures: Creative, detailed, unique
- **Recommendation**: Use both - standard for production, SD3 for variety

### 2. **Design Drafts for Reference**
- Generate design drafts early in pipeline
- Use as visual reference for other asset generation
- Include in documentation and presentations

### 3. **Projectile Textures**
- Generate projectile textures separately if needed
- Use for unique weapon visuals
- Can be generated independently of ship textures

### 4. **Performance Optimization**
- Generate SD3 textures in separate run if pipeline is slow
- Use `--skip-draft` to skip standard textures if only SD3 needed
- Filter by ship ID to reduce generation time

## Examples

### Example 1: Full Pipeline with SD3
```bash
# Generate all assets including SD3 textures and design drafts
python space_whale_quality_asset_generator.py --use-sd3 --sd3-texture-type all
```

### Example 2: Design Drafts Only
```bash
# Generate only design drafts for reference
python space_whale_quality_asset_generator.py --use-sd3 --sd3-texture-type design_draft --skip-draft
```

### Example 3: Projectile Textures
```bash
# Generate projectile textures for weapons
python space_whale_quality_asset_generator.py --use-sd3 --sd3-texture-type projectile
```

### Example 4: Standalone SD3 Generation
```powershell
# Generate SD3 textures independently
.\SpaceWhaleSD3TextureGenerator.bat `
    -ShipRegistry "space_whale_ship_example.json" `
    -VisualRegistry "space_whale_visual_language_registry.json" `
    -OutputDir "Output/Textures" `
    -TextureType "all" `
    -Variations 3 `
    -ShipId "leviathan_alpha"
```

## Summary

SD3 texture generation provides **high-quality creative textures**, **design drafts**, and **full ship artwork** that complement the procedural texture system:

✅ **Blender textures**: Creative diffuse maps for 3D models
✅ **Projectile textures**: Unique weapon visuals
✅ **Design drafts**: Concept art and references
✅ **Full ship artwork**: Complete ship renders in multiple views (2048x2048)
✅ **Ollama enhancement**: Better prompts for better results
✅ **Image-to-image**: Uses references for better visual consistency
✅ **Optional integration**: Works alongside standard textures

The system is **production-ready** and integrates seamlessly with the quality generator pipeline. **Full ship artwork** provides complete visualization of the entire ship design from multiple angles.
