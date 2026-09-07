@echo off
REM Generate high-quality Broodmother Mutation assets using Ollama AI tools
REM This script ALWAYS uses AI tools for asset generation with quality control
REM
REM Usage:
REM   GenerateBroodmotherAssets.bat [ModPath]
REM
REM If ModPath is not provided, uses default:
REM   %USERPROFILE%\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Broodmother Mutation

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0

REM Check if mod path was provided as argument
set "MOD_PATH=%~1"
if "!MOD_PATH!"=="" (
    REM Use default mod path for Broodmother Mutation mod
    set "MOD_PATH=%USERPROFILE%\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Broodmother Mutation"
    echo [INFO] Using default mod path: !MOD_PATH!
    echo.
)

echo ========================================
echo Broodmother Mutation Asset Generator
echo Using Ollama AI Tools with Quality Control
echo ========================================
echo.

REM Check if Ollama API is reachable (PowerShell first — reliable on double-click)
echo Checking Ollama connection...
set "OLLAMA_OK=0"
powershell -NoProfile -Command "try { Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 5 | Out-Null; exit 0 } catch { exit 1 }"
if not errorlevel 1 set "OLLAMA_OK=1"
if "!OLLAMA_OK!"=="0" (
    python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=5).read()" 2>nul
    if not errorlevel 1 set "OLLAMA_OK=1"
)
if "!OLLAMA_OK!"=="0" (
    echo [ERROR] Cannot reach Ollama at http://127.0.0.1:11434/api/tags
    echo         The app can be open while the API is still starting — wait and retry.
    echo         Or run: ollama serve
    echo.
    pause
    exit /b 1
)

echo [OK] Ollama API reachable
echo.

REM Prefer PowerShell wrapper (SD3.5 drafts + exports) if available
if exist "%SCRIPT_DIR%GenerateBroodmotherAssets.ps1" (
    echo Starting asset generation via PowerShell wrapper...
    echo Ollama model: wizardlm-uncensored:latest
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%GenerateBroodmotherAssets.ps1" -ModPath "!MOD_PATH!" -Verbose -OllamaModel "wizardlm-uncensored:latest" -UnloadModels
) else (
    echo Starting asset generation via Python script...
    echo.
    python "%SCRIPT_DIR%generate_broodmother_assets_ollama.py" "!MOD_PATH!" --verbose --model wizardlm-uncensored:latest --unload-models
)

if errorlevel 1 (
    echo.
    echo [ERROR] Asset generation failed!
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Asset generation completed!
echo.
pause
