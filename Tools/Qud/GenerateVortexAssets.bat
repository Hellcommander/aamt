@echo off
REM ====================================================================
REM Space-Time Vortex Asset Generator (Multi-AI Powered)
REM Uses Ollama AI for design + mathematical rendering for quality
REM ====================================================================

echo.
echo ====================================================================
echo Space-Time Vortex Asset Generator
echo Multi-AI: Math AI + Visual AI (wizardlm-uncensored)
echo ====================================================================
echo.

REM Set the mod path
set MOD_PATH="C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Improved and Rebalanced Space Time Vortex"

REM Change to script directory
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.x and try again.
    pause
    exit /b 1
)

REM Check if the script exists
if not exist "generate_vortex_professional.py" (
    echo ERROR: generate_vortex_professional.py not found in current directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

REM Check if mod path exists
if not exist %MOD_PATH% (
    echo ERROR: Mod directory not found: %MOD_PATH%
    echo Please update MOD_PATH in this batch file.
    pause
    exit /b 1
)

echo Generating professional-quality vortex assets with AI...
echo Mod path: %MOD_PATH%
echo.
echo This will generate:
echo   - Mutation icon (96x96, AI-designed)
echo   - 16 black hole animation frames (64x64, AI-designed)
echo   - 16 white hole animation frames (64x64, AI-designed)
echo   - 48 animated particle frames (16x16)
echo   - 3 distortion overlays (32x32)
echo   - 2 ability icons (64x64)
echo   - 1 warning marker (64x64)
echo   - White hole sounds (optional, if numpy/soundfile available)
echo.
echo Features:
echo   - 4x supersampling with LANCZOS anti-aliasing
echo   - Multi-AI support (math AI + visual AI)
echo   - 16-frame ultra-smooth animations
echo   - High-resolution support for tile scaling mods
echo.
echo IMPORTANT: This requires Ollama to be running!
echo           The AI will design color schemes and patterns.
echo.

REM Run the professional generator (uses multi-AI support)
REM Option 1: Direct Python call (faster, no quality assessment)
REM python generate_vortex_professional.py %MOD_PATH%

REM Option 2: PowerShell wrapper (includes quality assessment and design drafts)
REM Quality assessment depth: "fast" (sanity only), "mechanical" (Qwen3-VL-8B), "full" (both models)
REM Design drafts: Enabled by default if SD3 is available (use -GenerateDesignDraft:$false to disable)
pwsh -ExecutionPolicy Bypass -File "%~dp0GenerateVortexAssets.ps1" -ModPath %MOD_PATH% -QualityAssessmentDepth "full"

if errorlevel 1 (
    echo.
    echo ERROR: Asset generation failed!
    echo Check the error messages above.
    echo.
    echo Make sure:
    echo   1. Ollama is running (ollama serve)
    echo   2. You have models installed (wizardlm-uncensored, codellama, etc.)
    echo   3. Check the error messages above for details
    pause
    exit /b 1
)

echo.
echo ====================================================================
echo Asset generation complete!
echo ====================================================================
echo.
pause
