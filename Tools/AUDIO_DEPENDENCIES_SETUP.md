# Audio Generation Dependencies Setup

This guide helps you install all required dependencies for audio generation across all toolsets.

## Quick Start

### Automatic Installation (Recommended)

```powershell
# Install required dependencies
.\InstallAudioDependencies.ps1

# Or use the batch file
InstallAudioDependencies.bat
```

### Install to Custom Location (Avoid C: or D: drives)

```powershell
# Install to custom directory (e.g., E: drive)
.\InstallAudioDependencies.ps1 -InstallPath "E:\PythonPackages"

# Or create a virtual environment in custom location
.\InstallAudioDependencies.ps1 -InstallPath "E:\PythonPackages" -UseVirtualEnv
```

### Install with Advanced Features

```powershell
# Install all dependencies including advanced quality assessment
.\InstallAudioDependencies.ps1 -InstallOptional

# With custom location
.\InstallAudioDependencies.ps1 -InstallOptional -InstallPath "E:\PythonPackages"
```

## What Gets Installed

### Required Packages
- **numpy** (≥1.20.0) - Numerical operations for audio generation
- **soundfile** (≥0.10.0) - Audio file I/O (WAV, OGG support)

### Recommended Packages
- **scipy** (≥1.7.0) - Advanced signal processing (square waves, etc.)

### Optional Packages
- **librosa** (≥0.9.0) - Advanced audio analysis
- **requests** (≥2.25.0) - HTTP requests for Ollama integration

### Advanced Packages (Large Downloads)
- **torch** (≥2.0.0) - PyTorch for ML models
- **torchaudio** (≥2.0.0) - Audio processing with PyTorch
- **transformers** (≥4.20.0) - Wav2Vec2 and other models
- **openai-whisper** (≥20230314) - Whisper transcription

## Custom Installation Locations

If you have limited space on C: or D: drives, you can install packages to a custom location:

### Option 1: Custom Directory (with PYTHONPATH)

```powershell
# Install to E: drive (or any other drive)
.\InstallAudioDependencies.ps1 -InstallPath "E:\PythonPackages"

# Then set PYTHONPATH before running audio generators
$env:PYTHONPATH = "E:\PythonPackages"
```

### Option 2: Virtual Environment (Recommended)

```powershell
# Create virtual environment on E: drive
.\InstallAudioDependencies.ps1 -InstallPath "E:\PythonPackages" -UseVirtualEnv

# Activate virtual environment before using generators
& "E:\PythonPackages\Scripts\Activate.ps1"
```

## Manual Installation

If you prefer to install manually:

```bash
# Required
pip install numpy>=1.20.0 soundfile>=0.10.0

# Recommended
pip install scipy>=1.7.0

# Optional
pip install librosa>=0.9.0 requests>=2.25.0

# Advanced (large downloads, several GB)
pip install torch>=2.0.0 torchaudio>=2.0.0 transformers>=4.20.0 openai-whisper>=20230314

# To custom location:
pip install --target "E:\PythonPackages" numpy>=1.20.0 soundfile>=0.10.0
```

Or use the requirements file:

```bash
pip install -r requirements_audio.txt

# To custom location:
pip install --target "E:\PythonPackages" -r requirements_audio.txt
```

## Requirements by Toolset

### Elin Spell Audio Generator
- **Required**: numpy, soundfile
- **Optional**: scipy, librosa (for advanced processing)

### Qud Audio Generator
- **Required**: numpy, soundfile
- **Optional**: scipy, librosa (for advanced processing)

### Terraria Portal Audio Generator
- **Required**: numpy, soundfile
- **Optional**: scipy, librosa (for advanced processing)

### Starbound Audio Generator
- **Required**: numpy, soundfile
- **Optional**: scipy (for square wave generation), librosa

### Shared Audio Quality Assessment
- **Required**: numpy, requests
- **Optional**: librosa, soundfile, torch, transformers, openai-whisper

## Verification

After installation, verify your setup:

```python
python -c "import numpy, soundfile; print('✓ Core packages OK')"
python -c "import scipy; print('✓ SciPy OK')"
python -c "import librosa; print('✓ Librosa OK')"
```

## Troubleshooting

### Python Not Found
- Install Python 3.8 or later from [python.org](https://www.python.org/downloads/)
- Make sure Python is added to PATH during installation
- Or specify Python path: `.\InstallAudioDependencies.ps1 -PythonPath "C:\Python39\python.exe"`

### Limited Space on C: or D: Drives
- Use `-InstallPath` to install to a different drive: `.\InstallAudioDependencies.ps1 -InstallPath "E:\PythonPackages"`
- Use `-UseVirtualEnv` to create a virtual environment in the custom location
- If using custom directory (not virtual env), set PYTHONPATH: `$env:PYTHONPATH = "E:\PythonPackages"`

### pip Not Found
- Reinstall Python with pip included
- Or install pip manually: `python -m ensurepip --upgrade`

### Installation Fails
- Try upgrading pip first: `python -m pip install --upgrade pip`
- Some packages may require Visual C++ Build Tools on Windows
- For torch, consider using CPU-only version: `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu`

### Large Downloads
- Advanced packages (torch, transformers) are several GB
- Consider installing only required packages first
- Use `-InstallOptional` only if you need advanced quality assessment

## Platform-Specific Notes

### Windows
- May require Visual C++ Build Tools for some packages
- Consider using pre-built wheels when available

### Linux
- May require system packages: `sudo apt-get install libsndfile1`
- For librosa: `sudo apt-get install libasound2-dev`

### macOS
- May require Homebrew packages: `brew install libsndfile`
- For librosa: `brew install ffmpeg`

## Stable Audio 3 (AI text-to-SFX for Transcendence assets)

Uses [stabilityai/stable-audio-3-medium](https://huggingface.co/stabilityai/stable-audio-3-medium) via the official `stable-audio-3` library.

```powershell
# One-time setup (clones repo, installs into miniconda CUDA Python, caches medium)
.\Setup-StableAudio.ps1

# Generate a short game SFX (stop SD image server if VRAM is tight)
.\Generate-StableAudio.ps1 -Prompt "short spaceship laser shot, punchy" -Output ".\TestOutput\laser.wav" -Seconds 2
```

**HF access**
1. Accept license: https://huggingface.co/stabilityai/stable-audio-3-medium
2. Token must include that gated repo (classic Read, or fine-grained + this model — SD3.5-only tokens fail)
3. `hf auth login`

**Notes**
- Medium needs Flash Attention 2 + CUDA (~5GB+ VRAM). RTX 2080 Ti may struggle with flash-attn.
- For reliable short SFX without flash-attn, accept and use Small-SFX: `-Model small-sfx`
- Unload `Start-StableDiffusionServer` before generating on 11GB GPUs

Shared APIs: `Shared\stable_audio_generate.py`, `Shared\StableAudioIntegration.psm1`

## Next Steps

After installation:

1. **Test basic audio generation**:
   ```powershell
   # Elin
   .\ElinSpellAudioGenerator.ps1 -SpellDescription "Fire Magic - Fireball" -GenerateAll
   
   # Qud
   .\QudAudioGenerator.ps1 -ModName "TestMod" -SoundTypes "all"
   
   # Terraria
   .\TerrariaPortalAudioGenerator.ps1 -PortalName "TestPortal" -Preset Void -GenerateAll
   
   # Starbound
   .\StarboundSoundGenerator.ps1 -SoundName "testSound" -Preset Magic
   ```

2. **Enable quality assessment** (if advanced packages installed):
   ```powershell
   .\ElinSpellAudioGenerator.ps1 -SpellDescription "..." -GenerateAll -AssessQuality
   ```

## See Also

- **[Shared Audio Quality Assessment](../Shared/AUDIO_QUALITY_ASSESSMENT_README.md)** - Quality assessment system
- **[Elin Spell Audio Guide](../Elin/ELIN_SPELL_AUDIO_GUIDE.md)** - Elin audio generation
- **[Qud Audio Generator Guide](../Qud/QUD_AUDIO_GENERATOR_GUIDE.md)** - Qud audio generation
- **[Terraria Portal Audio Guide](../Terraria/TERRARIA_PORTAL_AUDIO_GUIDE.md)** - Terraria audio generation
- **[Starbound Audio Generator Guide](../Starbound/STARBOUND_AUDIO_GENERATOR_GUIDE.md)** - Starbound audio generation
