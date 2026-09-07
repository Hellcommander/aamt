# Required Tools Setup Guide
**AI-Assisted Modding Tools (AAMT)**

This guide helps you download and install the required tools for AAMT. Different tools require different dependencies - check which tools you plan to use.

## Repository bootstrap (after git clone)

The public repo is scripts and docs only (~22 MB). Your local workspace can grow to
many GB once you generate assets or fetch third-party trees. Do this once per machine:

```powershell
cd Tools
.\Copy-LocalSettings.ps1
```

That copies tracked `*.example` files to gitignored local settings:

| Example | Local file (edit paths) |
|---|---|
| `AssetGenerationSettings.example.ps1` | `AssetGenerationSettings.ps1` |
| `TranscendenceTools.ini.example` | `TranscendenceTools.ini` |
| `Qud/settings.example.json` | `Qud/settings.json` |
| `HfTokenProfiles.example.ps1` | `HfTokenProfiles.local.ps1` |

Optional third-party clones (not in git): `.\Fetch-ThirdParty.ps1`  
Qud Lab private sim (access-gated): `.\Qud\QudLab\Fetch-PrivatePack.ps1`

Do **not** commit generated output under `Output/`, `Shared/Concepts/`, or per-game
staging folders — regenerate with the tools instead.

---

### 1. Ollama (for description enhancement)

**Purpose**: Enhances character descriptions using AI with automatic routing for dark/uncensored content.

**Download**: https://ollama.com/download/OllamaSetup.exe

**Installation**:
1. Download `OllamaSetup.exe` from https://ollama.com
2. Run the installer
3. After installation, download required models:
   ```bash
   ollama pull llama3.1:8b
   ollama pull wizardlm-uncensored:latest
   ollama pull deepseek-r1:7b
   ```

**Verify**: Run `ollama --version` in PowerShell/CMD

**Default URL**: http://localhost:11434

---

### 2. Stable Diffusion API Server (for image generation)

**Required for**: `UncensoredCharacterImageGenerator`, `OllamaImageGenerator`, `Generate-AssetImageWithSD3`

**Purpose**: Generates detailed character images from enhanced descriptions.

**Installation**:
```bash
python -m pip install stable-diffusion-api-server
```

**Start Server** (recommended - automatically configures model storage):
```bash
.\Start-StableDiffusionServer.ps1
```

Or manually:
```bash
stable-diffusion-api-server
```

Or with custom port:
```bash
stable-diffusion-api-server --port 8000
```

**Note**: The `Start-StableDiffusionServer.ps1` script automatically:
- Finds the best available drive (not C: or D:, with >10GB free)
- Sets `HF_HOME` environment variable to store models there
- Creates the model directory if needed

**⚠ IMPORTANT - Model Storage Location**:
Stable Diffusion models can be several GB each. By default, they download to your user cache (usually on C: or D:).

**To store models on a different drive**:

1. **Set environment variable** (recommended):
   ```powershell
   # Set for current session
   $env:HF_HOME = "E:\StableDiffusion\Models"
   
   # Set permanently (run as Administrator)
   [System.Environment]::SetEnvironmentVariable("HF_HOME", "E:\StableDiffusion\Models", "User")
   ```

2. **Or use command-line option**:
   ```bash
   stable-diffusion-api-server --model-path E:\StableDiffusion\Models
   ```

3. **Or configure in server settings** (check stable-diffusion-api-server documentation)

**Setup Guide**: https://github.com/cantrell/stable-diffusion-api-server

**Default URL**: http://localhost:8000

---

## Image Processing Tools

### 3. ImageMagick (for post-processing)

**Required for**: Most asset generation scripts, AI image post-processing

**Purpose**: Post-processes AI-generated images for game compatibility, format optimization, and quality standardization.

**Download**: https://imagemagick.org/script/download.php#windows

**Installation**:
1. Download the Windows binary from https://imagemagick.org/script/download.php#windows
2. Run the installer
3. **Important**: Check "Add application directory to your system path" during installation
4. Recommended installation path: `E:\tools\ImageMagick` (or your preferred tools directory)

**Verify**:
```powershell
magick --version
```

**Configuration**:
The tools automatically detect ImageMagick in common locations:
- `E:\tools\ImageMagick\magick.exe`
- `C:\Program Files\ImageMagick-*\magick.exe`
- System PATH

**Note**: ImageMagick is used extensively for:
- Format conversion (PNG, JPG, etc.)
- Resizing and optimization
- Color space correction
- Quality standardization
- Game-specific format requirements

---

### 4. Python (Core Dependency)

**Required for**: Ollama integration, Stable Diffusion API, image generation scripts, asset processing

**Purpose**: Core runtime for many AAMT tools and dependencies.

**Download**: https://www.python.org/downloads/

**Installation**:
1. Download Python 3.8+ from https://www.python.org/downloads/
2. **Important**: Check "Add Python to PATH" during installation
3. **Important**: Check "Install pip" during installation
4. Restart terminal after installation

**Verify**:
```powershell
python --version
pip --version
```

**Python Dependencies**:

Install core dependencies:
```bash
cd "D:\games\Steam\steamapps\common\Transcendence\Tools\Shared"
python -m pip install requests typing-extensions Pillow
```

Or install from requirements.txt (if available):
```bash
python -m pip install -r requirements.txt
```

**Common Dependencies**:
- `requests>=2.31.0` - HTTP requests for Ollama API
- `typing-extensions>=4.8.0` - Type hints support
- `Pillow` - Image processing for Python scripts

---

## 3D Asset Tools

### 5. Blender (for 3D asset generation)

**Required for**: `BakeQudTile.ps1`, 3D model rendering, some Starbound asset generators

**Purpose**: 3D modeling and rendering for game assets, especially tile baking for Caves of Qud.

**Download**: https://www.blender.org/download/

**Installation**:
1. Download Blender from https://www.blender.org/download/
2. Run the installer
3. Recommended: Install to `D:\tools\Blender Foundation\Blender [version]` or `C:\Program Files\Blender Foundation\Blender [version]`
4. Optional: Add Blender to PATH (or tools will auto-detect common locations)

**Verify**:
```powershell
blender --version
```

**Auto-Detection**:
The tools automatically search for Blender in:
- Environment variables: `BLENDER_PATH`, `BLENDER_DIR`, `BLENDER_HOME`
- System PATH
- `D:\tools\Blender Foundation\Blender*`
- `C:\Program Files\Blender Foundation\Blender*`

**Manual Configuration**:
If Blender is not auto-detected, specify the path:
```powershell
# For BakeQudTile.ps1
.\BakeQudTile.ps1 -BlenderPath "C:\Program Files\Blender Foundation\Blender 4.0\blender.exe"
```

Or set environment variable:
```powershell
$env:BLENDER_PATH = "C:\Program Files\Blender Foundation\Blender 4.0"
```

---

## Tool-Specific Requirements

### Character Image Generation
- ✅ Ollama
- ✅ Stable Diffusion API Server
- ✅ Python + dependencies

### Starbound Asset Generation
- ✅ Ollama (for AI assistance)
- ✅ ImageMagick (for post-processing)
- ✅ Python + Pillow
- ⚠️ Blender (optional, for some 3D assets)

### Caves of Qud Tile Generation
- ✅ Blender (required for `BakeQudTile.ps1`)
- ✅ ImageMagick (for post-processing)

### Elin Asset Generation
- ✅ Ollama (for AI assistance)
- ✅ ImageMagick (for post-processing)
- ✅ Python + Pillow

---

## Quick Setup Script

**Installation**:
```bash
cd "D:\games\Steam\steamapps\common\Transcendence\Tools\Shared"
python -m pip install requests typing-extensions
```

Or install from requirements.txt:
```bash
python -m pip install -r requirements.txt
```

**Dependencies**:
- `requests>=2.31.0` - HTTP requests for Ollama API
- `typing-extensions>=4.8.0` - Type hints support

---

## Quick Setup Script

Run the PowerShell script to check and download tools:

```powershell
.\Download-RequiredTools.ps1 -All
```

Or install components individually:
```powershell
.\Download-RequiredTools.ps1 -InstallOllama
.\Download-RequiredTools.ps1 -InstallStableDiffusion
.\Download-RequiredTools.ps1 -InstallPythonDependencies
.\Download-RequiredTools.ps1 -InstallImageMagick
.\Download-RequiredTools.ps1 -InstallBlender
```

---

## Verification

After installation, verify everything works:

1. **Check Python**:
   ```powershell
   python --version
   pip --version
   ```

2. **Check Ollama**:
   ```powershell
   ollama --version
   ollama list
   ```

3. **Check ImageMagick**:
   ```powershell
   magick --version
   ```

4. **Check Blender** (if installed):
   ```powershell
   blender --version
   ```

5. **Check Stable Diffusion API**:
   ```powershell
   # Start the server, then test:
   Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing
   ```

6. **Test the Image Generator**:
   ```powershell
   .\UncensoredCharacterImageGenerator.ps1 `
       -Description "Test character" `
       -CharacterName "Test" `
       -GameType "Generic"
   ```

---

## Troubleshooting

### Ollama not found
- Ensure Ollama is installed and in PATH
- Restart terminal after installation
- Check: `Get-Command ollama`

### Python not found
- Download from: https://www.python.org/downloads/
- **Important**: Check "Add Python to PATH" during installation
- Restart terminal after installation
- Verify: `python --version` and `pip --version`

### ImageMagick not found
- Download from: https://imagemagick.org/script/download.php#windows
- **Important**: Check "Add application directory to your system path" during installation
- Restart terminal after installation
- Verify: `magick --version`
- If not in PATH, tools will search common locations like `E:\tools\ImageMagick\magick.exe`

### Blender not found
- Download from: https://www.blender.org/download/
- Tools auto-detect Blender in common locations
- If not auto-detected, set `BLENDER_PATH` environment variable or use `-BlenderPath` parameter
- Verify: `blender --version` (if in PATH) or check installation directory

### Stable Diffusion API not responding
- Ensure the server is running: `stable-diffusion-api-server`
- Check firewall settings
- Verify port 8000 is not in use

### Python dependencies not installing
- Try: `python -m pip install --upgrade pip`
- Use: `python -m pip install requests typing-extensions --user`

### Models downloading to C: or D: drive
- **Set HF_HOME environment variable** before starting the server:
  ```powershell
  $env:HF_HOME = "E:\StableDiffusion\Models"  # Use your preferred drive
  stable-diffusion-api-server
  ```
- **Or set permanently** (run as Administrator):
  ```powershell
  [System.Environment]::SetEnvironmentVariable("HF_HOME", "E:\StableDiffusion\Models", "User")
  ```
- **Or use --model-path** when starting server:
  ```bash
  stable-diffusion-api-server --model-path E:\StableDiffusion\Models
  ```
- Check stable-diffusion-api-server documentation for additional configuration options

---

## Next Steps

Once all tools are installed:

1. Start Ollama (usually runs automatically after installation)
2. Start Stable Diffusion API server: `.\Start-StableDiffusionServer.ps1` (automatically configures model storage)
3. Run the image generator: `.\UncensoredCharacterImageGenerator.ps1`
