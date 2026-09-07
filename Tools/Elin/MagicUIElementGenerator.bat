@echo off
REM ============================================================
REM Magic UI Element Generator - Wrapper
REM ============================================================
REM
REM Generates magic-themed UI elements for CustomRaceClassCreator
REM ============================================================

set SCRIPT_DIR=%~dp0
set PS_SCRIPT=%SCRIPT_DIR%MagicUIElementGenerator.ps1

if not exist "%PS_SCRIPT%" (
    echo ERROR: PowerShell script not found at:
    echo   %PS_SCRIPT%
    echo.
    pause
    exit /b 1
)

REM Check if mod path provided
if "%~1"=="" (
    echo.
    echo Usage: %~nx0 "MOD_PATH" [options]
    echo.
    echo Example:
    echo   %~nx0 "E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator" -SystemName "DragonMagic" -UIElementType "all" -UseAI
    echo.
    echo Or drag the mod folder onto this batch file.
    echo.
    pause
    exit /b 0
)

REM Use provided path or dropped folder
set "MOD_PATH=%~1"

pwsh -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -ModPath "%MOD_PATH%" %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Script exited with error code: %ERRORLEVEL%
    pause
)

