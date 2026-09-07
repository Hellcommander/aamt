@echo off
REM ============================================================
REM StarboundParticleGenerator.bat - Quick Particle Creation
REM ============================================================

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%StarboundParticleGenerator.ps1"

where pwsh >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "POWERSHELL=pwsh"
) else (
    set "POWERSHELL=powershell"
)

echo ================================================================
echo   Starbound Particle Generator
echo ================================================================
echo.
echo Presets: Fire, Ice, Poison, Electric, Blood, Sparkle, Smoke, Bubble
echo.

set /p "PARTICLE_NAME=Enter particle name: "
if "!PARTICLE_NAME!"=="" (
    echo Error: Particle name is required.
    goto :error
)

echo.
echo Select a preset (or press Enter for custom):
set /p "PRESET=Preset [Fire/Ice/Poison/Electric/Blood/Sparkle/Smoke/Bubble]: "
if "!PRESET!"=="" set "PRESET=None"

echo.
echo Generating particle...

%POWERSHELL% -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -ParticleName "!PARTICLE_NAME!" -Preset "!PRESET!"

if %ERRORLEVEL% neq 0 goto :error

echo.
echo ================================================================
echo   Generation Complete!
echo ================================================================
goto :end

:error
echo.
echo An error occurred.

:end
echo.
pause
endlocal

