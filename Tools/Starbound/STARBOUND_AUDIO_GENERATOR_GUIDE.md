# Starbound Audio Generator - Guide

Complete sound effect generation system for Starbound mods, integrated with procedural audio generation and quality assessment.

## Overview

Generates Starbound-compatible sound effects including:
- **Impact Sounds** (0.2s) - Hits, strikes, collisions
- **Charge Sounds** (0.5s) - Building energy, charging up
- **Ambient Sounds** (2.0s) - Loopable background sounds
- **Magic Sounds** (0.8s) - Ethereal, mystical energy
- **Mechanical Sounds** (0.3s) - Machines, gears, clicks
- **Organic Sounds** (0.6s) - Biological, natural
- **Explosion Sounds** (0.4s) - Booms, blasts
- **Whoosh Sounds** (0.3s) - Air movement, fast motion
- **Roar Sounds** (1.0s) - Powerful, deep vocalizations

## Quick Start

### Generate Sound with Preset

```powershell
.\StarboundSoundGenerator.ps1 -SoundName "rhinoChargeStart" -Preset Charge
```

### Generate Custom Sound

```powershell
.\StarboundSoundGenerator.ps1 -SoundName "magicImpact" -SoundType Magic -Description "magical energy impact sound"
```

### With Quality Assessment

The existing `StarboundSoundGenerator.ps1` can be enhanced to use the shared audio quality assessment system. For now, use the Python script directly:

```powershell
python starbound_audio_generator.py --spec spec.json --output "StarboundSounds" --name "magicImpact" --type magic --format ogg
```

## Parameters

- **`-SoundName`** (Required) - Name/ID of the sound
- **`-SoundType`** - Type of sound (Impact, Charge, Ambient, Magic, Mechanical, Organic, Explosion, Whoosh, Roar, Custom)
- **`-Preset`** - Preset configuration (uses preset defaults if specified)
- **`-Description`** - Description for AI-assisted generation
- **`-Duration`** - Sound duration in seconds (default: varies by preset)
- **`-Frequency`** - Base frequency in Hz (default: varies by preset)
- **`-Volume`** - Volume level 0.0-1.0 (default: varies by preset)
- **`-OutputDir`** - Output directory (default: `StarboundSounds`)
- **`-Format`** - Output format: wav or ogg (default: ogg)
- **`-OllamaModel`** - Ollama model for AI-assisted generation
- **`-UsePython`** - Use Python script for generation

## Output Structure

```
StarboundSounds/
└── sounds/
    ├── rhinoChargeStart.ogg
    ├── magicImpact.ogg
    └── ambientLoop.ogg
```

## Sound Type Support

### Impact
- **Duration**: 0.2 seconds
- **Frequency**: 200 Hz
- **Volume**: 0.8
- **Characteristics**: Sharp attack with quick decay, impact noise, low-frequency thud
- **Use Case**: Hits, strikes, collisions

### Charge
- **Duration**: 0.5 seconds
- **Frequency**: 300 Hz
- **Volume**: 0.7
- **Characteristics**: Rising pitch, build-up envelope, energy harmonics
- **Use Case**: Building energy, charging up

### Ambient
- **Duration**: 2.0 seconds (loopable)
- **Frequency**: 220 Hz
- **Volume**: 0.4
- **Characteristics**: Steady tone with slow modulation, fade in/out
- **Use Case**: Background sounds, environmental ambience

### Magic
- **Duration**: 0.8 seconds
- **Frequency**: 600 Hz
- **Volume**: 0.6
- **Characteristics**: Multiple harmonics with modulation, ethereal shimmer
- **Use Case**: Magical energy, mystical effects

### Mechanical
- **Duration**: 0.3 seconds
- **Frequency**: 400 Hz
- **Volume**: 0.7
- **Characteristics**: Square wave with harmonics, clicking transients
- **Use Case**: Machines, gears, mechanical devices

### Organic
- **Duration**: 0.6 seconds
- **Frequency**: 150 Hz
- **Volume**: 0.6
- **Characteristics**: Natural resonance with vibrato, organic decay
- **Use Case**: Biological sounds, natural creatures

### Explosion
- **Duration**: 0.4 seconds
- **Frequency**: 100 Hz
- **Volume**: 0.9
- **Characteristics**: Low frequency rumble, explosive noise burst
- **Use Case**: Booms, blasts, explosions

### Whoosh
- **Duration**: 0.3 seconds
- **Frequency**: 500 Hz
- **Volume**: 0.6
- **Characteristics**: White noise with frequency sweep, quick envelope
- **Use Case**: Air movement, fast motion

### Roar
- **Duration**: 1.0 seconds
- **Frequency**: 80 Hz
- **Volume**: 0.8
- **Characteristics**: Low frequency with noise, build-up and sustain, growling texture
- **Use Case**: Powerful vocalizations, creature roars

## Integration with Visual Assets

Generate both visual and audio assets together:

```powershell
# Generate visual assets
.\StarboundAssetGenerator.ps1 -AssetType Texture -AssetName "magicportal"

# Generate audio assets
.\StarboundSoundGenerator.ps1 -SoundName "magicportal_activate" -Preset Magic
```

## Quality Assessment

The enhanced `starbound_audio_generator.py` can be integrated with the shared audio quality assessment system:

```python
# After generating sounds, assess quality
from audio_quality_assessment import batch_assess_audio_quality, filter_audio_by_quality

assessments, total, filtered = batch_assess_audio_quality(
    "StarboundSounds/sounds",
    min_score=17,
    ollama_url="http://localhost:11434",
    ollama_model="llama3.1:8b"
)
```

## Batch Processing

### Process Multiple Sounds

```powershell
$sounds = @(
    @{Name="rhinoChargeStart"; Type="Charge"},
    @{Name="rhinoChargeLoop"; Type="Ambient"},
    @{Name="rhinoRoar"; Type="Roar"},
    @{Name="magicImpact"; Type="Magic"}
)

foreach ($sound in $sounds) {
    .\StarboundSoundGenerator.ps1 -SoundName $sound.Name -SoundType $sound.Type -OutputDir "StarboundSounds"
}
```

## Technical Details

### Sample Rate
- **Default**: 44.1 kHz (CD quality)
- **Format**: OGG Vorbis (compressed, game-friendly) or WAV (uncompressed)

### Procedural Generation
- **Deterministic**: Same sound name = same sounds (via seed)
- **Type-Based**: Each sound type has unique characteristics
- **Preset-Based**: Presets provide optimized defaults

### Dependencies
- **Required**: Python 3.x, numpy, soundfile
- **Optional**: scipy (for advanced signal processing), Ollama (for AI specifications), librosa/torch (for quality assessment)

Install with:
```bash
pip install numpy soundfile
# Optional:
pip install scipy librosa torch transformers openai-whisper
```

## Usage Examples

### Basic Generation

```powershell
# Generate impact sound
.\StarboundSoundGenerator.ps1 -SoundName "swordHit" -Preset Impact

# Generate magic sound
.\StarboundSoundGenerator.ps1 -SoundName "spellCast" -Preset Magic
```

### Custom Parameters

```powershell
.\StarboundSoundGenerator.ps1 `
    -SoundName "customExplosion" `
    -SoundType Explosion `
    -Duration 0.6 `
    -Frequency 80 `
    -Volume 0.95
```

### With AI-Generated Descriptions

```powershell
.\StarboundSoundGenerator.ps1 `
    -SoundName "alienRoar" `
    -SoundType Roar `
    -Description "deep alien creature roar with otherworldly resonance" `
    -OllamaModel "llama3.1:8b"
```

## Troubleshooting

### Python/numpy/soundfile Not Found
- Install Python 3.x
- Install dependencies: `python -m pip install numpy soundfile`
- Verify installation: `python -c "import numpy, soundfile; print('OK')"`

### Sounds Too Simple
- Use `-Description` with detailed descriptions
- Adjust frequencies and characteristics in `starbound_audio_generator.py`
- Extend procedural generation functions

### Quality Assessment Fails
- Ensure shared audio quality assessment module is available
- Check that Ollama is running (if using LLM assessment)
- Install optional dependencies: `pip install librosa torch transformers openai-whisper`

## Integration with Existing Tools

### With StarboundAssetGenerator

```powershell
# Generate complete asset package (visual + audio)
$assetName = "magicportal"

# Visual assets
.\StarboundAssetGenerator.ps1 -AssetType Texture -AssetName $assetName

# Audio assets
.\StarboundSoundGenerator.ps1 -SoundName "${assetName}_activate" -Preset Magic
.\StarboundSoundGenerator.ps1 -SoundName "${assetName}_ambient" -Preset Ambient
```

### With StarboundOllamaAssetGenerator

```powershell
# Generate all assets (textures, icons, audio)
.\StarboundOllamaAssetGenerator.ps1 -AssetType Sound -AssetName "magicImpact" -Prompt "magical energy impact sound"
```

## Design Principles

- **Placeholder-First**: Generate usable sounds quickly
- **Type-Aligned**: Each sound type has unique audio identity
- **Deterministic**: Same name = same sounds (reproducible)
- **Modular**: Generate only what you need
- **Game-Ready**: Outputs match Starbound's audio requirements
- **Quality-Assured**: Optional quality assessment ensures production-ready sounds

## Future Enhancements

- [ ] Integration with shared audio quality assessment in PowerShell wrapper
- [ ] Custom sound libraries per sound type
- [ ] Integration with asset generation pipeline
- [ ] Batch processing from asset database
- [ ] Advanced audio effects (reverb, delay, etc.)
- [ ] 3D spatial audio support
- [ ] Preview generation for audio review

## References

- **Shared Audio Quality Assessment**: `Tools/Shared/AUDIO_QUALITY_ASSESSMENT_README.md`
- **Starbound Toolset Integration**: `STARBOUND_TOOLSET_INTEGRATION.md`
- **Starbound Asset Generator**: `StarboundAssetGenerator.ps1`

## See Also

- **[Starbound Toolset Integration](./STARBOUND_TOOLSET_INTEGRATION.md)** - Tool integration guide
- **[Shared Audio Quality Assessment](../Shared/AUDIO_QUALITY_ASSESSMENT_README.md)** - Quality assessment system
