# OpenStarbound Python Frame Generator Pipeline

Production-ready, AI-driven frame generation system for OpenStarbound modding.

## Features

- **AI-Driven Palette Selection**: Automatically generates color palettes using Ollama or Colormind API
- **High-Quality Frame Generation**: Supports pixel art, high-res, and MS-Designer quality levels
- **Intelligent Packing**: Uses rectpack algorithm for optimal atlas layout
- **Automatic Validation**: Detects colored boxes and validates output quality
- **Power-of-Two Support**: Automatic POT sizing for GPU optimization
- **OpenStarbound Compatible**: Generates `.frames` JSON files in correct format

## Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Verify installation
python frame_generator_orchestrator.py --help
```

## Quick Start

1. **Create a job JSON file** (see `example_job.json`):

```json
{
  "asset_name": "spell_cast",
  "frame_count": 8,
  "frame_width": 16,
  "frame_height": 16,
  "color_hints": ["purple", "gold"],
  "animation_type": "SpellCast",
  "output_dir": "output"
}
```

2. **Run the orchestrator**:

```bash
python frame_generator_orchestrator.py --job example_job.json --output assets
```

3. **Check output**:
   - `spell_cast.png` - Spritesheet atlas
   - `spell_cast.frames` - OpenStarbound metadata

## Integration with PowerShell Pipeline

The PowerShell `StarboundAssetGenerator.ps1` can call this Python orchestrator:

```powershell
# In PowerShell
$jobJson = @{
    asset_name = "spell_cast"
    frame_count = 8
    frame_width = 16
    frame_height = 16
    color_hints = @("purple", "gold")
    animation_type = "SpellCast"
    output_dir = "assets"
} | ConvertTo-Json

$jobJson | Out-File "job.json" -Encoding UTF8

python frame_generator_orchestrator.py --job "job.json" --output "assets"
```

## Quality Levels

### Pixel Art (default)
- 3-5 colors maximum
- High contrast
- Flat colors only
- Best for 16x16, 32x32 sprites

### High-Res
- 5-8 colors
- Subtle gradients
- More detail
- Best for 64x64, 128x128 sprites

### MS-Designer
- 8-16 colors
- Complex gradients
- Photorealistic
- Best for 256x256+ sprites

## Palette Generation

The system automatically generates palettes using:

1. **Colormind API** (free, no auth) - Fast, reliable
2. **Ollama AI** (local) - More creative, requires Ollama
3. **Role-Based Defaults** - Fallback if APIs unavailable

### Role-Based Palettes

- **Assault**: Warm reds/oranges, bright yellows
- **Support**: Cool blues, light cyans
- **Horror**: Dark reds, near-black
- **Magitech**: Magical blues, purples, golds

See `palette_decision_rules.md` for detailed rules.

## Animation Types

- **SpellCast**: Growing energy effect
- **DeviceActivation**: Pulsing effect
- **StatusEffect**: Shimmering effect
- **Default**: Simple growing circle

## Output Format

### Atlas PNG
- 32-bit RGBA format
- Uncompressed (Starbound requirement)
- Power-of-two dimensions (if enabled)
- Padding between frames (2px default)

### .frames JSON
```json
{
  "frameGrid": {
    "size": [16, 16],
    "dimensions": [8, 1]
  },
  "aliases": {
    "default": [0, 1, 2, 3, 4, 5, 6, 7]
  },
  "frames": [
    {"x": 0, "y": 0, "width": 16, "height": 16},
    ...
  ]
}
```

## Validation

The orchestrator automatically validates:

- ✅ Files exist and are readable
- ✅ Atlas is RGBA format
- ✅ No single-color frames (colored box detection)
- ✅ .frames JSON is valid
- ✅ Frame dimensions match atlas

## Troubleshooting

### "Colormind API failed"
- Check internet connection
- System will fall back to AI or default palette

### "AI palette generation failed"
- Ensure Ollama is running: `ollama serve`
- Check model is available: `ollama list`
- System will use role-based default palette

### "Validation failed: colored box detected"
- Check palette generation succeeded
- Verify frame generation logic
- Review output images manually

## Advanced Usage

### Custom Palette

```python
from frame_generator_orchestrator import FrameGeneratorOrchestrator, FrameJob, QualityLevel

orchestrator = FrameGeneratorOrchestrator()
job = FrameJob(
    asset_name="custom_asset",
    frame_count=8,
    frame_width=16,
    frame_height=16,
    color_hints=["crimson", "brass", "teal"],
    quality_level=QualityLevel.HIGH_RES
)
result = orchestrator.process_job(job)
```

### Batch Processing

```python
jobs = [
    FrameJob(asset_name=f"asset_{i}", ...)
    for i in range(10)
]

for job in jobs:
    result = orchestrator.process_job(job)
    print(f"Generated: {result['atlas_path']}")
```

## Performance

- **Palette Generation**: ~1-2 seconds (Colormind) or ~5-10 seconds (Ollama)
- **Frame Generation**: ~0.1 seconds per frame
- **Atlas Packing**: ~0.5 seconds for 8 frames
- **Total**: ~3-15 seconds per animation (depending on quality level)

## Future Enhancements

- [ ] SDXL integration for MS-Designer quality
- [ ] Aseprite template automation
- [ ] TexturePacker CLI integration
- [ ] Multipack support (multiple atlases)
- [ ] Pivot point extraction
- [ ] Animation duration metadata

## License

Same as main project.
