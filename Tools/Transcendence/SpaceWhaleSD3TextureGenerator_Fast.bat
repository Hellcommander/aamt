@echo off
REM ============================================================
REM Space Whale SD3 Texture Generator - FAST VERSION
REM Uses Stable Diffusion 3 for high-quality texture generation
REM FAST VERSION: Skips design drafts (faster generation)
REM ============================================================

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%SpaceWhaleSD3TextureGenerator.ps1"

if not exist "%PS_SCRIPT%" (
    echo ERROR: PowerShell script not found at:
    echo   %PS_SCRIPT%
    echo.
    pause
    exit /b 1
)

echo ============================================================
echo Space Whale SD3 Texture Generator (FAST VERSION)
echo Stable Diffusion 3 Medium for Creative Textures
echo Includes: Blender textures, Projectiles (NO design drafts)
echo ============================================================
echo.
echo This generator uses SD3 to create:
echo   - Blender model textures (diffuse maps)
echo   - Projectile textures (energy bolts, plasma, bio-missiles)
echo   - SKIPS design drafts for faster generation
echo.
echo NOTE: This is the FAST version without design drafts.
echo       For full generation with design drafts, use:
echo       SpaceWhaleSD3TextureGenerator.bat
echo.

REM Run PowerShell script without design drafts
REM Note: PowerShell script will parse TextureType parameter and skip design_draft
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" %* -TextureType "blender,projectile"

set "EXIT_CODE=%ERRORLEVEL%"

if %EXIT_CODE% NEQ 0 (
    echo.
    echo Script exited with error code: %EXIT_CODE%
    pause
)

exit /b %EXIT_CODE%
