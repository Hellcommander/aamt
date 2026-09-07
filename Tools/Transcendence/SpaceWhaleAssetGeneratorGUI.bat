@echo off
REM ============================================================
REM Space Whale Asset Generator GUI - Launcher
REM User-friendly graphical interface
REM ============================================================

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%SpaceWhaleAssetGeneratorGUI.ps1"

if not exist "%PS_SCRIPT%" (
    echo ERROR: PowerShell GUI script not found at:
    echo   %PS_SCRIPT%
    echo.
    pause
    exit /b 1
)

echo ============================================================
echo Space Whale Asset Generator - GUI
echo User-Friendly Control Panel
echo ============================================================
echo.
echo Launching graphical interface...
echo.

REM Launch PowerShell GUI
powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%PS_SCRIPT%"

exit /b 0
