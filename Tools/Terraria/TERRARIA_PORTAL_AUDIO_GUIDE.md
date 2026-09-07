# Terraria Portal Audio Generator - Guide

Complete sound effect generation system for Terraria portal mods, integrated with procedural audio generation and quality assessment.

## Overview

Generates Terraria-compatible portal sound effects including:
- **Activation Sounds** (1.0s) - Portal opening sounds
- **Ambient Sounds** (3.0s) - Loopable sounds while portal is active
- **Teleport Sounds** (0.5s) - Sounds when using portal
- **Deactivation Sounds** (0.8s) - Portal closing sounds

## Quick Start

### Generate All Sound Types

```powershell
.\TerrariaPortalAudioGenerator.ps1 -PortalName "VoidPortal" -Preset Void -GenerateAll
```

### Generate Specific Sound Types

```powershell
# Activation and ambient only
.\TerrariaPortalAudioGenerator.ps1 -PortalName "FirePortal" -Preset Fire -GenerateActivation -GenerateAmbient

# Teleport sound only
.\TerrariaPortalAudioGenerator.ps1 -PortalName "IcePortal" -Preset Ice -GenerateTeleport
```

### With Quality Assessment

```powershell
.\TerrariaPortalAudioGenerator.ps1 -PortalName "VoidPortal" -Preset Void -GenerateAll -AssessQuality -MinQualityScore 17
```

### With AI-Generated Specifications

```powershell
.\TerrariaPortalAudioGenerator.ps1 -PortalName "SynthwavePortal" -Preset Shadow -Description "vibrant purple-pink synthwave portal" -GenerateAll -UseAI
```

## Parameters

- **`-PortalName`** (Required) - Name/ID of the portal
- **`-Preset`** - Portal preset (Void, Fire, Ice, Electric, Nature, Shadow, Light, Generic)
- **`-Description`** - Natural language description of the portal
- **`-OutputDir`** - Output directory (default: `TerrariaPortals`)
- **`-GenerateActivation`** - Generate activation sound
- **`-GenerateAmbient`** - Generate ambient sound
- **`-GenerateTeleport`** - Generate teleport sound
- **`-GenerateDeactivation`** - Generate deactivation sound
- **`-GenerateAll`** - Generate all sound types
- **`-UseAI`** - Use Ollama to generate audio specifications
- **`-AssessQuality`** - Assess audio quality using shared quality system
- **`-MinQualityScore`** - Minimum quality score to keep (default: 17/20)
- **`-OllamaModel`** - Ollama model to use (default: auto-detected)

## Output Structure

```
TerrariaPortals/
└── Sounds/
    ├── voidportal_activation.ogg    (Activation sound)
    ├── voidportal_ambient.ogg       (Ambient/loop sound)
    ├── voidportal_teleport.ogg      (Teleport sound)
    └── voidportal_deactivation.ogg  (Deactivation sound)
```

## Portal Preset Support

The generator supports all portal presets with unique audio characteristics:

### Void
- **Base Frequency**: A3 (220 Hz) - deep, mysterious
- **Character**: Deep, spacey with reverb-like tail
- **Use Case**: Mysterious, otherworldly portals

### Fire
- **Base Frequency**: E4 (330 Hz) - bright, energetic
- **Character**: Bright, crackling with high-frequency content
- **Use Case**: Fiery, energetic portals

### Ice
- **Base Frequency**: E3 (165 Hz) - cold, deep
- **Character**: Cold, crystalline with harmonics
- **Use Case**: Frosty, cold portals

### Electric
- **Base Frequency**: A4 (440 Hz) - sharp, electric
- **Character**: Sharp, electric with transients
- **Use Case**: Electric, energetic portals

### Nature
- **Base Frequency**: C4 (262 Hz) - organic, earthy
- **Character**: Organic, flowing with slow vibrato
- **Use Case**: Natural, organic portals

### Shadow
- **Base Frequency**: G3 (196 Hz) - dark, ominous
- **Character**: Dark, muffled with subtle distortion
- **Use Case**: Dark, shadowy portals

### Light
- **Base Frequency**: E4 (330 Hz) - bright, pure
- **Character**: Pure, clear with minimal processing
- **Use Case**: Bright, pure portals

## Sound Types

### Activation Sounds
- **Duration**: 1.0 seconds
- **Characteristics**: Rising pitch with energy buildup, build-up envelope
- **Use Case**: Played when portal opens/activates

### Ambient Sounds
- **Duration**: 3.0 seconds (loopable)
- **Characteristics**: Steady tone with slow modulation, fade in/out
- **Use Case**: Looped while portal is active

### Teleport Sounds
- **Duration**: 0.5 seconds
- **Characteristics**: Quick whoosh with pitch sweep, teleport "pop" transient
- **Use Case**: Played when player uses portal

### Deactivation Sounds
- **Duration**: 0.8 seconds
- **Characteristics**: Falling pitch with decay, closing "snap"
- **Use Case**: Played when portal closes/deactivates

## Integration with Visual Portal Generation

Generate both visual and audio assets together:

```powershell
# Generate visual portal assets
.\TerrariaPortalOllamaGenerator.ps1 -PortalName "VoidPortal" -Description "cold blue void portal" -Preset Void

# Generate audio assets
.\TerrariaPortalAudioGenerator.ps1 -PortalName "VoidPortal" -Preset Void -GenerateAll
```

## Quality Assessment

The generator integrates with the shared audio quality assessment system:

```powershell
.\TerrariaPortalAudioGenerator.ps1 `
    -PortalName "VoidPortal" `
    -Preset Void `
    -GenerateAll `
    -AssessQuality `
    -MinQualityScore 17
```

This will:
1. Generate all sound effects
2. Assess quality using hybrid pipeline (embeddings + Whisper + LLM)
3. Filter out files with scores < 17
4. Save assessment results to `Sounds/audio_quality_assessments.json`

## Batch Processing

### Process Multiple Portals

```powershell
$portals = @(
    @{Name="VoidPortal"; Preset="Void"},
    @{Name="FirePortal"; Preset="Fire"},
    @{Name="IcePortal"; Preset="Ice"},
    @{Name="ElectricPortal"; Preset="Electric"}
)

foreach ($portal in $portals) {
    .\TerrariaPortalAudioGenerator.ps1 -PortalName $portal.Name -Preset $portal.Preset -GenerateAll -OutputDir "TerrariaPortals"
}
```

## Technical Details

### Sample Rate
- **Default**: 44.1 kHz (CD quality)
- **Format**: OGG Vorbis (compressed, game-friendly)

### Procedural Generation
- **Deterministic**: Same portal name = same sounds (via seed)
- **Preset-Based**: Each preset has unique frequency and character
- **Type-Based**: Different sound types (activation/ambient/teleport/deactivation) have different characteristics

### Dependencies
- **Required**: Python 3.x, numpy, soundfile
- **Optional**: Ollama (for AI specifications), librosa/torch (for quality assessment)

Install with:
```bash
pip install numpy soundfile
```

## Usage Examples

### Basic Generation

```powershell
# Generate all sounds for a portal
.\TerrariaPortalAudioGenerator.ps1 -PortalName "VoidPortal" -Preset Void -GenerateAll
```

### Preset-Specific Sounds

```powershell
# Fire portal sounds
.\TerrariaPortalAudioGenerator.ps1 -PortalName "FirePortal" -Preset Fire -GenerateAll

# Ice portal sounds
.\TerrariaPortalAudioGenerator.ps1 -PortalName "IcePortal" -Preset Ice -GenerateAll
```

### Production Quality with Assessment

```powershell
.\TerrariaPortalAudioGenerator.ps1 `
    -PortalName "SynthwavePortal" `
    -Preset Shadow `
    -Description "vibrant purple-pink synthwave portal" `
    -GenerateAll `
    -UseAI `
    -AssessQuality `
    -MinQualityScore 17 `
    -OllamaModel "llama3.1:8b"
```

## Troubleshooting

### Python/numpy/soundfile Not Found
- Install Python 3.x
- Install dependencies: `python -m pip install numpy soundfile`
- Verify installation: `python -c "import numpy, soundfile; print('OK')"`

### Sounds Too Simple
- Use `-UseAI` for more sophisticated specifications
- Adjust frequencies and characteristics in `terraria_portal_audio_generator.py`
- Extend procedural generation functions

### Quality Assessment Fails
- Ensure shared audio quality assessment module is available
- Check that Ollama is running (if using LLM assessment)
- Install optional dependencies: `pip install librosa torch transformers openai-whisper`

## Integration with Existing Tools

### With TerrariaPortalOllamaGenerator

```powershell
# Generate complete portal package (visual + audio)
$portal = "VoidPortal"
$description = "cold blue void portal with spacetime distortion"

# Visual assets
.\TerrariaPortalOllamaGenerator.ps1 -PortalName $portal -Description $description -Preset Void

# Audio assets
.\TerrariaPortalAudioGenerator.ps1 -PortalName $portal -Preset Void -GenerateAll -AssessQuality
```

### With TerrariaPortalGenerator

```powershell
# Generate portal package (no AI)
.\TerrariaPortalGenerator.ps1 -PortalName "FirePortal" -Preset Fire -GeneratePlaceholders

# Then generate audio
.\TerrariaPortalAudioGenerator.ps1 -PortalName "FirePortal" -Preset Fire -GenerateAll
```

## Design Principles

- **Placeholder-First**: Generate usable sounds quickly
- **Preset-Aligned**: Each preset has unique audio identity
- **Deterministic**: Same portal name = same sounds (reproducible)
- **Modular**: Generate only what you need
- **Game-Ready**: Outputs match Terraria's audio requirements
- **Quality-Assured**: Optional quality assessment ensures production-ready sounds

## Future Enhancements

- [ ] Custom sound libraries per preset
- [ ] Integration with portal JSON profiles
- [ ] Batch processing from portal database
- [ ] Advanced audio effects (reverb, delay, etc.)
- [ ] 3D spatial audio support
- [ ] Preview generation for audio review

## References

- **Shared Audio Quality Assessment**: `Tools/Shared/AUDIO_QUALITY_ASSESSMENT_README.md`
- **Terraria Portal Generator Guide**: `TERRARIA_PORTAL_GENERATOR_GUIDE.md`
- **Terraria Toolset Integration**: `TERRARIA_TOOLSET_INTEGRATION.md`

## See Also

- **[Terraria Portal Generator Guide](./TERRARIA_PORTAL_GENERATOR_GUIDE.md)** - Visual portal generation
- **[Shared Audio Quality Assessment](../Shared/AUDIO_QUALITY_ASSESSMENT_README.md)** - Quality assessment system
- **[Terraria Toolset Integration](./TERRARIA_TOOLSET_INTEGRATION.md)** - Tool integration guide
