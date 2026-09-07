@echo off
REM ============================================================
REM Start Space Whale Asset Generation - Complete Setup
REM ============================================================
REM Launches all necessary components for Space Whale asset generation:
REM   - Control Room Monitor (optional GUI)
REM   - Comprehensive Asset Generator (multithreaded)
REM ============================================================

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_DIR=%SCRIPT_DIR%Output\SpaceWhaleAssets"
set "SHIP_ID=leviathan_alpha"
REM Model selection: CodeLlama-34B for best code generation, WizardLM-uncensored for general use
REM Set to empty to use auto-detection (recommended)
set "OLLAMA_MODEL="
REM Or explicitly set:
REM set "OLLAMA_MODEL=codellama:34b"
REM set "OLLAMA_MODEL=wizardlm-uncensored:latest"
set "VARIATIONS=150"
set "USE_MONITOR=1"

echo.
echo ============================================================
echo   Space Whale Asset Generation - Complete Setup
echo ============================================================
echo.
echo Configuration:
echo   - Output Directory: %OUTPUT_DIR%
echo   - Ship ID: %SHIP_ID%
echo   - Ollama Model: %OLLAMA_MODEL%
echo   - Variations: %VARIATIONS%
echo   - Monitor GUI: %USE_MONITOR%
echo.
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and add it to your PATH
    pause
    exit /b 1
)

REM Check if Ollama is running (optional check)
curl -s http://localhost:11434/api/tags >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo WARNING: Ollama does not appear to be running
    echo Some features may not work without Ollama
    echo.
    echo To start Ollama:
    echo   ollama serve
    echo.
    echo Continuing anyway (generation will use fallback methods if Ollama unavailable)...
    timeout /t 2 >nul
)

REM Create output directory
if not exist "%OUTPUT_DIR%" (
    mkdir "%OUTPUT_DIR%"
    echo Created output directory: %OUTPUT_DIR%
)

REM Launch Control Room Monitor (optional, in foreground)
if "%USE_MONITOR%"=="1" (
    echo.
    echo [1/2] Launching Control Room Monitor...
    echo   Opening GUI window (should appear in a few seconds)...
    echo   If GUI doesn't appear, check taskbar or run separately:
    echo   StartSpaceWhaleAssetGeneration_MonitorOnly.bat
    echo.
    if not exist "%SCRIPT_DIR%AssetGeneratorControlRoom_Monitor.ps1" (
        echo ERROR: Monitor script not found: %SCRIPT_DIR%AssetGeneratorControlRoom_Monitor.ps1
        echo Skipping monitor launch...
    ) else (
        start "Space Whale Monitor" powershell -STA -NoProfile -ExecutionPolicy Bypass -WindowStyle Normal -File "%SCRIPT_DIR%AssetGeneratorControlRoom_Monitor.ps1" -WatchDirectory "%OUTPUT_DIR%" -MaxCores 32
        if errorlevel 1 (
            echo WARNING: Monitor launch may have failed (check if window appeared)
        )
        timeout /t 3 >nul
    )
)

REM Launch Comprehensive Asset Generator
echo.
echo [2/2] Starting Comprehensive Asset Generation...
echo.
echo This will generate:
echo   - Visual Language Assets (150 variations)
echo   - FX Assets (150 variations)
echo   - Audio Assets (150 variations)
echo   - Textures for Rigging
echo   - Quality Reports
echo.
echo Generation is multithreaded (up to 32 cores)
echo Estimated time: ~1 hour (down from 30+ hours)
echo.
echo ============================================================
echo.

REM Check if comprehensive generator exists
set "GENERATOR_SCRIPT=%SCRIPT_DIR%space_whale_comprehensive_asset_generator.py"
if not exist "%GENERATOR_SCRIPT%" (
    echo ERROR: Comprehensive generator not found: %GENERATOR_SCRIPT%
    echo.
    echo Trying alternative: GenerateSpaceWhaleAssets.ps1
    set "GENERATOR_SCRIPT=%SCRIPT_DIR%GenerateSpaceWhaleAssets.ps1"
    if not exist "%GENERATOR_SCRIPT%" (
        echo ERROR: No generator script found!
        pause
        exit /b 1
    )
)

REM Launch generator
if "%GENERATOR_SCRIPT:~-3%"==".py" (
    REM Python script
    echo Starting Python generator...
    echo   Script: %GENERATOR_SCRIPT%
    echo   Working directory: %CD%
    echo.
    python "%GENERATOR_SCRIPT%" 2>&1
    set "GEN_EXIT=%ERRORLEVEL%"
    if %GEN_EXIT% neq 0 (
        echo.
        echo ERROR: Python generator failed with exit code %GEN_EXIT%
        echo Check the error messages above for details.
    )
) else (
    REM PowerShell script - try comprehensive generator first
    set "COMPREHENSIVE_SCRIPT=%SCRIPT_DIR%space_whale_comprehensive_asset_generator.py"
    if exist "%COMPREHENSIVE_SCRIPT%" (
        echo Starting comprehensive Python generator...
        echo   Script: %COMPREHENSIVE_SCRIPT%
        echo   Working directory: %CD%
        echo.
        python "%COMPREHENSIVE_SCRIPT%" 2>&1
        set "GEN_EXIT=%ERRORLEVEL%"
        if %GEN_EXIT% neq 0 (
            echo.
            echo ERROR: Comprehensive generator failed with exit code %GEN_EXIT%
            echo Check the error messages above for details.
        )
    ) else (
        echo Starting PowerShell generator...
        echo   Script: %GENERATOR_SCRIPT%
        echo   Working directory: %CD%
        echo.
        powershell -NoProfile -ExecutionPolicy Bypass -File "%GENERATOR_SCRIPT%" -ShipId "%SHIP_ID%" -OutputDir "%OUTPUT_DIR%" -OllamaModel "%OLLAMA_MODEL%" -Variations %VARIATIONS%
        set "GEN_EXIT=%ERRORLEVEL%"
        if %GEN_EXIT% neq 0 (
            echo.
            echo ERROR: PowerShell generator failed with exit code %GEN_EXIT%
            echo Check the error messages above for details.
        )
    )
)

echo.
echo ============================================================
if %GEN_EXIT% equ 0 (
    echo   Asset Generation Complete!
    echo ============================================================
    echo.
    echo Generated assets are in: %OUTPUT_DIR%
    echo.
    echo Next steps:
    echo   1. Review quality reports in the output directory
    echo   2. Select best variations for each asset type
    echo   3. Generate final spritesheets with Blender
    echo   4. Export to Transcendence XML format
    echo.
) else (
    echo   Asset Generation Failed (Exit Code: %GEN_EXIT%)
    echo ============================================================
    echo.
    echo Check the logs above for error details.
    echo.
)

REM Keep window open
echo Press any key to exit...
pause >nul

endlocal

