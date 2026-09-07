# Qud Audio Generator - Guide

Complete sound effect generation system for Caves of Qud mods, integrated with procedural audio generation and quality assessment.

## Overview

Generates Qud-compatible sound effects for mods including:
- **Attack Sounds** (0.3s) - Swing, strike sounds
- **Hit Sounds** (0.2s) - Impact, contact sounds (material-based)
- **Death Sounds** (0.5s) - Creature death sounds
- **Spawn Sounds** (0.4s) - Appear, summon sounds
- **Ambient/Idle Sounds** (2.0s) - Loopable background sounds
- **Walk/Run/Jump/Land Sounds** (0.15s) - Footstep sounds (surface-based)
- **Use Sounds** (0.3s) - Item activation sounds
- **Missile Fire Sounds** (0.2s) - Projectile launch sounds
- **Detonated Sounds** (0.4s) - Explosion sounds

## Quick Start

### Generate All Sound Types

```powershell
.\QudAudioGenerator.ps1 -ModName "Broodmother Mutation" -SoundTypes "all"
```

### Generate Specific Sound Types

```powershell
# Attack, hit, and death sounds only
.\QudAudioGenerator.ps1 -ModName "Broodmother Mutation" -SoundTypes "attack,hit,death"

# Ambient sound for creature
.\QudAudioGenerator.ps1 -ModName "Broodmother Mutation" -SoundTypes "ambient" -CreatureType "large"
```

### With Quality Assessment

```powershell
.\QudAudioGenerator.ps1 -ModName "Broodmother Mutation" -SoundTypes "all" -AssessQuality -MinQualityScore 17
```

### With AI-Generated Specifications

```powershell
.\QudAudioGenerator.ps1 -ModName "Space Time Vortex" -SoundTypes "all" -UseAI -OllamaModel "llama3.1:8b"
```

## Parameters

- **`-ModName`** (Required) - Name of the mod or path to mod directory
- **`-SoundTypes`** - Comma-separated list of sound types or "all" (default: "all")
- **`-CreatureType`** - Type of creature (small, medium, large, insect, beast, robot, mutant, generic)
- **`-Material`** - Material type for hit sounds (flesh, metal, stone, wood, crystal, generic)
- **`-Surface`** - Surface type for walk sounds (dirt, stone, metal, wood, sand, generic)
- **`-OutputDir`** - Output directory (default: mod's Sounds directory)
- **`-UseAI`** - Use Ollama to generate audio specifications
- **`-AssessQuality`** - Assess audio quality using shared quality system
- **`-MinQualityScore`** - Minimum quality score to keep (default: 17/20)
- **`-OllamaModel`** - Ollama model to use (default: auto-detected)

## Output Structure

```
ModName/
└── Sounds/
    ├── ModName_attack.ogg
    ├── ModName_hit.ogg
    ├── ModName_death.ogg
    ├── ModName_spawn.ogg
    ├── ModName_ambient.ogg
    ├── ModName_walk.ogg
    ├── ModName_run.ogg
    ├── ModName_jump.ogg
    ├── ModName_land.ogg
    ├── ModName_use.ogg
    ├── ModName_missilefire.ogg
    └── ModName_detonated.ogg
```

## Sound Types

### Attack Sounds
- **Duration**: 0.3 seconds
- **Characteristics**: Sharp attack with quick decay, whoosh envelope
- **Creature-Based**: Frequency varies by creature size/type

### Hit Sounds
- **Duration**: 0.2 seconds
- **Characteristics**: Very sharp attack, fast decay, impact transients
- **Material-Based**: Different frequencies for flesh, metal, stone, wood, crystal

### Death Sounds
- **Duration**: 0.5 seconds
- **Characteristics**: Falling pitch with decay, noise texture
- **Creature-Based**: Frequency based on creature type

### Spawn Sounds
- **Duration**: 0.4 seconds
- **Characteristics**: Rising pitch, fade in/out
- **Creature-Based**: Frequency based on creature type

### Ambient/Idle Sounds
- **Duration**: 2.0 seconds (loopable)
- **Characteristics**: Low, steady tone with slow modulation, fade in/out
- **Use Cases**: Background sounds for creatures, environmental ambience

### Walk/Run/Jump/Land Sounds
- **Duration**: 0.15 seconds (walk), 0.12s (run), 0.075s (jump)
- **Characteristics**: Thud-like sound with low-frequency component
- **Surface-Based**: Different frequencies for dirt, stone, metal, wood, sand

### Use Sounds
- **Duration**: 0.3 seconds
- **Characteristics**: Click/activation sound, quick envelope
- **Item-Based**: Different frequencies for mechanical, magical, electronic items

### Missile Fire Sounds
- **Duration**: 0.2 seconds
- **Characteristics**: Sharp whoosh, quick envelope
- **Projectile-Based**: Different frequencies for energy, physical, explosive projectiles

### Detonated Sounds
- **Duration**: 0.4 seconds
- **Characteristics**: Wide frequency range, noise burst, decay envelope
- **Explosion-Based**: Full-spectrum explosion sound

## Creature Type Support

The generator supports different creature types with unique audio characteristics:

- **Small**: High-pitched (400 Hz) - small creatures, insects
- **Medium**: Mid-range (250 Hz) - standard creatures
- **Large**: Low-pitched (150 Hz) - large creatures
- **Insect**: Very high (500 Hz) - insects, small critters
- **Beast**: Animal-like (200 Hz) - organic creatures
- **Robot**: Mechanical (300 Hz) - robotic creatures
- **Mutant**: Altered organic (220 Hz) - mutated creatures
- **Generic**: Default (250 Hz)

## Integration with Visual Assets

Generate both visual and audio assets together:

```powershell
# Generate all assets including audio
python generate_mod_assets.py "Broodmother Mutation" --include-audio

# Or use standalone audio generator
.\QudAudioGenerator.ps1 -ModName "Broodmother Mutation" -SoundTypes "all"
```

## Integration with Mod Fixer

The audio generator can be used alongside the mod fixer:

```powershell
# Fix mod and generate all assets (visual + audio)
python qud_mod_fixer.py "Broodmother Mutation"

# Then generate additional audio
.\QudAudioGenerator.ps1 -ModName "Broodmother Mutation" -SoundTypes "all" -AssessQuality
```

## Quality Assessment

The generator integrates with the shared audio quality assessment system:

```powershell
.\QudAudioGenerator.ps1 `
    -ModName "Broodmother Mutation" `
    -SoundTypes "all" `
    -AssessQuality `
    -MinQualityScore 17
```

This will:
1. Generate all sound effects
2. Assess quality using hybrid pipeline (embeddings + Whisper + LLM)
3. Filter out files with scores < 17
4. Save assessment results to `Sounds/audio_quality_assessments.json`

## Batch Processing

### Process Multiple Mods

```powershell
$mods = @(
    "Broodmother Mutation",
    "Space Time Vortex",
    "Custom Creature Pack"
)

foreach ($mod in $mods) {
    .\QudAudioGenerator.ps1 -ModName $mod -SoundTypes "all" -AssessQuality
}
```

## Technical Details

### Sample Rate
- **Default**: 44.1 kHz (CD quality)
- **Format**: OGG Vorbis (compressed, game-friendly)

### Procedural Generation
- **Deterministic**: Same parameters = same sounds (via seed)
- **Type-Based**: Each sound type has unique characteristics
- **Parameter-Based**: Creature type, material, surface affect frequency and character

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
# Generate all sounds for a mod
.\QudAudioGenerator.ps1 -ModName "Broodmother Mutation" -SoundTypes "all"
```

### Creature-Specific Sounds

```powershell
# Large creature sounds
.\QudAudioGenerator.ps1 -ModName "Giant Beast" -SoundTypes "attack,hit,death" -CreatureType "large"

# Small insect sounds
.\QudAudioGenerator.ps1 -ModName "Ant Swarm" -SoundTypes "attack,walk" -CreatureType "insect"
```

### Material-Based Hit Sounds

```powershell
# Metal impact sounds
.\QudAudioGenerator.ps1 -ModName "Robot Mod" -SoundTypes "hit" -Material "metal"

# Stone impact sounds
.\QudAudioGenerator.ps1 -ModName "Stone Golem" -SoundTypes "hit" -Material "stone"
```

### Production Quality with Assessment

```powershell
.\QudAudioGenerator.ps1 `
    -ModName "Broodmother Mutation" `
    -SoundTypes "all" `
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

### Mod Not Found
- Check mod name spelling
- Verify mod is in default mods directory:
  - Windows: `%USERPROFILE%\AppData\LocalLow\Freehold Games\CavesOfQud\Mods`
  - Linux: `~/.config/unity3d/Freehold Games/CavesOfQud/Mods`
- Or provide full path to mod directory

### Sounds Too Simple
- Use `-UseAI` for more sophisticated specifications
- Adjust frequencies and characteristics in `qud_audio_generator.py`
- Extend procedural generation functions

### Quality Assessment Fails
- Ensure shared audio quality assessment module is available
- Check that Ollama is running (if using LLM assessment)
- Install optional dependencies: `pip install librosa torch transformers openai-whisper`

## Integration with Existing Tools

### With generate_mod_assets.py

```powershell
# Generate all assets including audio
python generate_mod_assets.py "Broodmother Mutation" --include-audio

# Generate only audio
python generate_mod_assets.py "Broodmother Mutation" --audio-only
```

### With qud_mod_fixer.py

The mod fixer detects sound references but doesn't generate them. Use the audio generator separately:

```powershell
# Fix mod
python qud_mod_fixer.py "Broodmother Mutation"

# Generate missing sounds
.\QudAudioGenerator.ps1 -ModName "Broodmother Mutation" -SoundTypes "all"
```

## Design Principles

- **Placeholder-First**: Generate usable sounds quickly
- **Type-Aligned**: Each sound type has unique audio identity
- **Deterministic**: Same parameters = same sounds (reproducible)
- **Modular**: Generate only what you need
- **Game-Ready**: Outputs match Qud's audio requirements
- **Quality-Assured**: Optional quality assessment ensures production-ready sounds

## Future Enhancements

- [ ] Custom sound libraries per creature type
- [ ] Integration with XML generation
- [ ] Batch processing from mod database
- [ ] Advanced audio effects (reverb, delay, etc.)
- [ ] 3D spatial audio support
- [ ] Preview generation for audio review

## References

- **Shared Audio Quality Assessment**: `Tools/Shared/AUDIO_QUALITY_ASSESSMENT_README.md`
- **Qud Asset Generation Guide**: `ASSET_GENERATION_GUIDE.md`
- **Qud Toolset Integration**: `QUD_TOOLSET_INTEGRATION.md`

## See Also

- **[Asset Generation Guide](./ASSET_GENERATION_GUIDE.md)** - Visual asset generation
- **[Shared Audio Quality Assessment](../Shared/AUDIO_QUALITY_ASSESSMENT_README.md)** - Quality assessment system
- **[Qud Toolset Integration](./QUD_TOOLSET_INTEGRATION.md)** - Tool integration guide
