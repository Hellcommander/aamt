# Transcendence Tools Settings

## Configuration File

The Transcendence Tools can be configured using a settings file located at:
```
Tools/TranscendenceTools.ini
```

## Setup

1. Copy `TranscendenceTools.ini.example` to `TranscendenceTools.ini`
2. Edit `TranscendenceTools.ini` and set your Transcendence installation path

## Settings

### TranscendencePath

The path to your Transcendence installation directory (the folder containing `Transcendence.tdb`, `Extensions`, `Collection`, etc.).

**Example:**
```ini
TranscendencePath = D:\games\Steam\steamapps\common\Transcendence
```

**Using Environment Variables:**
You can use environment variables in the path:
```ini
TranscendencePath = %ProgramFiles(x86)%\Steam\steamapps\common\Transcendence
TranscendencePath = %USERPROFILE%\SteamLibrary\steamapps\common\Transcendence
```

## Auto-Detection

If no settings file is found or `TranscendencePath` is not set, the tools will automatically search for your Transcendence installation in these locations (in order):

1. `%ProgramFiles(x86)%\Steam\steamapps\common\Transcendence`
2. `%ProgramFiles%\Steam\steamapps\common\Transcendence`
3. `%LOCALAPPDATA%\Programs\Steam\steamapps\common\Transcendence`
4. `%USERPROFILE%\SteamLibrary\steamapps\common\Transcendence`
5. `%USERPROFILE%\Steam\steamapps\common\Transcendence`
6. `D:\games\Steam\steamapps\common\Transcendence` (and E:, F:, G:, H: drives)
7. `D:\SteamLibrary\steamapps\common\Transcendence` (and E:, F:, G:, H: drives)
8. Relative to the Tools folder location

**Note:** The tools automatically check common drive letters (D:, E:, F:, G:, H:) for:
- `\games\Steam\steamapps\common\Transcendence` - Common for users who partition their OS drive
- `\SteamLibrary\steamapps\common\Transcendence` - Common for additional Steam library locations

The tools verify the installation by checking for:
- `Transcendence.tdb` file
- `Extensions` folder
- `Collection` folder

## Notes

- The settings file is optional - if you don't create it, the tools will use auto-detection
- Paths can use forward slashes (`/`) or backslashes (`\`)
- Environment variables are automatically expanded
- The settings file is located in the Tools root folder (same level as subdirectories like `Transcendence`, `Common`, etc.)

