@echo off
REM ============================================================================
REM Broodmother Asset Generator - FULL quality mode (sequential multi-model)
REM ============================================================================
REM Vastly slower than police. Exclusive GPU swaps on 11GB:
REM   SD drafts → stop SD → composition (LLaVA) → tech QA (Qwen-VL) →
REM   preference heuristic → creative refine → SD retry failures only.
REM Prefer GenerateBroodmotherAssets-Police.bat for everyday quality.
REM ============================================================================

setlocal enabledelayedexpansion

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%GenerateBroodmotherAssets.ps1"

REM Check if PowerShell script exists
if not exist "%PS_SCRIPT%" (
    echo.
    echo [ERROR] PowerShell script not found: %PS_SCRIPT%
    echo.
    pause
    exit /b 1
)

REM Check if mod path was provided, if not use default automatically
set "MOD_PATH=%~1"
if "!MOD_PATH!"=="" (
    REM Use default mod path for Broodmother Mutation mod
    REM Use explicit path to ensure LocalLow (not Local)
    set "MOD_PATH=%USERPROFILE%\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Broodmother Mutation"
    
    echo.
    echo [INFO] Using default mod path: !MOD_PATH!
    echo.
)

REM Build PowerShell command with multi-agent enabled and recommended defaults
REM Note: We don't add -Verbose by default to avoid conflicts with PowerShell's common parameter
REM Properly quote MOD_PATH to handle paths with spaces
set "PS_CMD=powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -ModPath "%MOD_PATH%" -QualityMode full -LoadExisting -GenerateAudio -UnloadModels -Verbose"

REM Add remaining arguments (skip first argument which is mod path, if it was provided)
REM Filter out duplicate parameters that are already in the default command
set "ARG_COUNT=0"
:parse_args
set /a ARG_COUNT+=1
call set "ARG_VAL=%%%ARG_COUNT%%"
if "!ARG_VAL!"=="" goto :run_ps

REM Skip first argument if it was provided (it's the mod path, already handled)
if !ARG_COUNT! equ 1 goto :parse_args

REM Skip arguments that are already enabled by default to avoid duplicates
REM Check for exact matches (case-insensitive) of default parameters
set "SKIP_ARG=0"
echo !ARG_VAL! | findstr /i /C:"-QualityMode" /C:"-MultiAgent" /C:"-GenerateAudio" /C:"-UnloadModels" /C:"-LoadExisting" /C:"-Verbose" >nul
if not errorlevel 1 set "SKIP_ARG=1"

if !SKIP_ARG! equ 0 (
    REM Not a duplicate argument, add it (including -Verbose if user wants it)
    REM Arguments are added as-is; user should quote values with spaces
    set "PS_CMD=!PS_CMD! !ARG_VAL!"
)
goto :parse_args

:run_ps
echo.
echo ============================================================================
echo Broodmother FULL quality (sequential multi-model — SLOW)
echo ============================================================================
echo.
echo Mod Path: !MOD_PATH!
echo QualityMode: full (VRAM-exclusive agent swaps — overnight-friendly, not parallel)
echo Audio Generation: ENABLED (default)
echo Unload Models: ENABLED (default)
echo PowerShell Script: %PS_SCRIPT%
echo.
echo Running PowerShell script...
echo.

REM Execute PowerShell script
REM Execute the command directly (call is for batch files/labels, not external executables)
%PS_CMD%

REM Capture exit code
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo ============================================================================
if %EXIT_CODE% equ 0 (
    echo Generation completed successfully!
) else (
    echo Generation failed with exit code: %EXIT_CODE%
    echo.
    echo Check the error messages above for details.
)
echo ============================================================================
echo.

REM Pause so user can see the results
pause

endlocal
exit /b %EXIT_CODE%
