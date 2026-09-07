# Elin Spell Audio Generator - Guide

Complete spell sound effect generation system for the game Elin, integrated with procedural audio generation and quality assessment.

## Overview

Generates Elin-compatible spell sound effects including:
- **Cast Sounds** (0.3-0.8s) - Whoosh, charge, activation sounds
- **Impact Sounds** (0.2-0.5s) - Hit, explosion, contact sounds
- **Loop Sounds** (1-3s) - Loopable sounds for channeled spells and buffs

## Quick Start

### Generate All Sound Types

```powershell
.\ElinSpellAudioGenerator.ps1 -SpellDescription "Nature Magic - Verdant Pulse: a burst of green life energy" -GenerateAll
```

### Generate Specific Sound Types

```powershell
# Cast and impact only
.\ElinSpellAudioGenerator.ps1 -SpellDescription "Fireball spell" -GenerateCast -GenerateImpact

# Loop sound for channeled spell
.\ElinSpellAudioGenerator.ps1 -SpellDescription "Nature Magic - Healing Channel" -GenerateLoop
```

### With AI-Generated Specifications

```powershell
.\ElinSpellAudioGenerator.ps1 -SpellDescription "Arachnomancy - Venom Web" -GenerateAll -UseAI -OllamaModel "wizardlm-uncensored:latest"
```

### With Quality Assessment

```powershell
.\ElinSpellAudioGenerator.ps1 -SpellDescription "Nature Magic - Leaf Shield" -GenerateAll -AssessQuality -MinQualityScore 17
```

## Parameters

- **`-SpellDescription`** (Required) - Description of the spell
- **`-SpellName`** - Custom spell name (auto-generated if not provided)
- **`-OutputDir`** - Output directory (default: `ElinAssets`)
- **`-GenerateCast`** - Generate cast sound
- **`-GenerateImpact`** - Generate impact sound
- **`-GenerateLoop`** - Generate loop sound
- **`-GenerateAll`** - Generate all sound types
- **`-UseAI`** - Use Ollama to generate audio specifications
- **`-AssessQuality`** - Assess audio quality using shared quality system
- **`-MinQualityScore`** - Minimum quality score to keep (default: 17/20)
- **`-OllamaModel`** - Ollama model to use (default: auto-detected)

## Output Structure

```
ElinAssets/
└── audio/
    ├── spell_name_cast.ogg      (Cast sound)
    ├── spell_name_impact.ogg    (Impact sound)
    └── spell_name_loop.ogg       (Loop sound)
```

## Spell School Support

The generator supports all major spell schools with unique audio characteristics:

### Nature Magic
- **Base Frequency**: A3 (220 Hz) - earthy, organic
- **Character**: Organic, flowing with slow vibrato
- **Colors**: Green palette (#4caf50, #81c784)

### Fire Magic
- **Base Frequency**: E4 (330 Hz) - bright, energetic
- **Character**: Bright, crackling with high-frequency content
- **Colors**: Red/orange palette (#f44336, #ff7043)

### Ice Magic
- **Base Frequency**: E3 (165 Hz) - cold, deep
- **Character**: Cold, crystalline with harmonics
- **Colors**: Blue palette (#03a9f4, #81d4fa)

### Lightning Magic
- **Base Frequency**: A4 (440 Hz) - sharp, electric
- **Character**: Sharp, electric with transients
- **Colors**: Yellow palette (#ffeb3b, #fff59d)

### Dark Magic / Arachnomancy
- **Base Frequency**: D3/G3 (147/196 Hz) - deep, ominous
- **Character**: Dark, muffled with subtle distortion
- **Colors**: Dark purple/black palette

### Dragon Magic
- **Base Frequency**: B3 (247 Hz) - powerful, ancient
- **Character**: Powerful, rumbling with low frequencies
- **Colors**: Red/orange palette (#d32f2f, #f57c00)

## Sound Types

### Cast Sounds
- **Duration**: 0.3-0.8 seconds
- **Types**: Whoosh, charge, activation
- **Characteristics**: 
  - Charging spells: Rising pitch
  - Burst spells: Sharp attack
  - Beam spells: Steady with modulation
  - Default: Magical whoosh

### Impact Sounds
- **Duration**: 0.2-0.5 seconds
- **Types**: Hit, explosion, contact
- **Characteristics**: Sharp attack with fast decay, impact transients

### Loop Sounds
- **Duration**: 1-3 seconds (loopable)
- **Use Cases**: Channeled spells, buffs, sustained effects
- **Characteristics**: Steady tone with slow modulation, fade in/out for smooth looping

## Integration with Visual Assets

Generate both visual and audio assets together:

```powershell
# Generate visual assets
.\ElinSpellAssetGenerator.ps1 -SpellDescription "Nature Magic - Verdant Pulse" -GenerateAll

# Generate audio assets
.\ElinSpellAudioGenerator.ps1 -SpellDescription "Nature Magic - Verdant Pulse" -GenerateAll
```

## Batch Processing

### Process Multiple Spells

```powershell
$spells = @(
    "Nature Magic - Verdant Pulse: a burst of green life energy",
    "Nature Magic - Leaf Shield: protective barrier of leaves",
    "Fire Magic - Fireball: explosive fire projectile",
    "Ice Magic - Frost Bolt: icy projectile",
    "Arachnomancy - Venom Web: toxic web trap"
)

foreach ($spell in $spells) {
    .\ElinSpellAudioGenerator.ps1 -SpellDescription $spell -GenerateAll -OutputDir "ElinAssets"
}
```

### From File

```powershell
# spells.txt contains one description per line
$spells = Get-Content "spells.txt"

foreach ($spell in $spells) {
    if (-not [string]::IsNullOrWhiteSpace($spell)) {
        .\ElinSpellAudioGenerator.ps1 -SpellDescription $spell -GenerateAll
    }
}
```

## Quality Assessment

The generator integrates with the shared audio quality assessment system:

```powershell
.\ElinSpellAudioGenerator.ps1 `
    -SpellDescription "Nature Magic - Healing Wave" `
    -GenerateAll `
    -AssessQuality `
    -MinQualityScore 17
```

This will:
1. Generate all sound effects
2. Assess quality using hybrid pipeline (embeddings + Whisper + LLM)
3. Filter out files with scores < 17
4. Save assessment results to `audio/audio_quality_assessments.json`

## Audio Specifications

When using `-UseAI`, the system generates JSON specifications:

```json
{
  "spellName": "Verdant Pulse",
  "school": "nature",
  "spellType": "burst",
  "colors": ["#4caf50", "#81c784"],
  "castDuration": 0.5,
  "impactDuration": 0.3,
  "loopDuration": 2.0
}
```

## Technical Details

### Sample Rate
- **Default**: 44.1 kHz (CD quality)
- **Format**: OGG Vorbis (compressed, game-friendly)

### Procedural Generation
- **Deterministic**: Same spell description = same sounds (via seed)
- **School-Based**: Each school has unique frequency and character
- **Type-Based**: Different sound types (cast/impact/loop) have different characteristics

### Dependencies
- **Required**: Python 3.x, numpy, soundfile
- **Optional**: Ollama (for AI specifications), librosa (for advanced processing)

Install with:
```bash
pip install numpy soundfile
```

## Workflow Examples

### Rapid Prototyping

```powershell
# Generate placeholder sounds for 20 spells in minutes
$spellSchools = @("Nature Magic", "Fire Magic", "Ice Magic", "Arachnomancy")
$spellTypes = @("Bolt", "Shield", "Heal", "Trap", "AoE")

foreach ($school in $spellSchools) {
    foreach ($type in $spellTypes) {
        $desc = "$school - $type spell"
        .\ElinSpellAudioGenerator.ps1 -SpellDescription $desc -GenerateAll -OutputDir "ElinAssets\$school"
    }
}
```

### Production Quality with Assessment

```powershell
.\ElinSpellAudioGenerator.ps1 `
    -SpellDescription "Dragon Magic - Ancient Roar" `
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
- Adjust frequencies and characteristics in `elin_spell_audio.py`
- Extend procedural generation functions

### Quality Assessment Fails
- Ensure shared audio quality assessment module is available
- Check that Ollama is running (if using LLM assessment)
- Install optional dependencies: `pip install librosa torch transformers openai-whisper`

### Audio Format Issues
- OGG Vorbis is the default format (game-friendly)
- Can be converted to WAV if needed: `ffmpeg -i input.ogg output.wav`

## Integration with Existing Tools

### With ElinSpellAssetGenerator

```powershell
# Generate complete spell package (visual + audio)
$spell = "Nature Magic - Verdant Pulse: a burst of green life energy"

# Visual assets
.\ElinSpellAssetGenerator.ps1 -SpellDescription $spell -GenerateAll

# Audio assets
.\ElinSpellAudioGenerator.ps1 -SpellDescription $spell -GenerateAll -AssessQuality
```

### With OllamaAssetGenerator

```powershell
# Generate all assets (textures, icons, audio)
.\OllamaAssetGenerator.ps1 -ModPath "..." -AssetTypes "all" -UseOllama

# Then generate spell-specific audio
.\ElinSpellAudioGenerator.ps1 -SpellDescription "..." -GenerateAll
```

## Design Principles

- **Placeholder-First**: Generate usable sounds quickly
- **School-Aligned**: Each spell school has unique audio identity
- **Deterministic**: Same description = same sounds (reproducible)
- **Modular**: Generate only what you need
- **Game-Ready**: Outputs match Elin's audio requirements
- **Quality-Assured**: Optional quality assessment ensures production-ready sounds

## Future Enhancements

- [ ] Custom sound libraries per spell school
- [ ] Integration with spell XML generation
- [ ] Batch processing from spell database
- [ ] Advanced audio effects (reverb, delay, etc.)
- [ ] 3D spatial audio support
- [ ] Preview generation for audio review

## References

- **Shared Audio Quality Assessment**: `Tools/Shared/AUDIO_QUALITY_ASSESSMENT_README.md`
- **Elin Spell Asset Generator**: `ELIN_SPELL_ASSETS_GUIDE.md`
- **Elin Toolset Integration**: `ELIN_TOOLSET_INTEGRATION.md`

## See Also

- **[Elin Spell Assets Guide](./ELIN_SPELL_ASSETS_GUIDE.md)** - Visual asset generation
- **[Shared Audio Quality Assessment](../Shared/AUDIO_QUALITY_ASSESSMENT_README.md)** - Quality assessment system
- **[Elin Toolset Integration](./ELIN_TOOLSET_INTEGRATION.md)** - Tool integration guide
