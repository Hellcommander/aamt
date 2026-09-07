@echo off
REM ============================================================
REM Space Whale SD3 Texture Generator - Batch Wrapper
REM Uses Stable Diffusion 3 for high-quality texture generation
REM FULL VERSION: Includes design drafts (slower, higher quality)
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
echo Space Whale SD3 Texture Generator (FULL VERSION)
echo Stable Diffusion 3 Medium for Creative Textures
echo Includes: Blender textures, Projectiles, Design Drafts, Full Ship Artwork
echo ============================================================
echo.
echo This generator uses SD3 to create:
echo   - Blender model textures (diffuse maps)
echo   - Projectile textures (energy bolts, plasma, bio-missiles)
echo   - Design drafts (concept art)
echo   - Full ship artwork (complete ship renders) - SLOWER but highest quality
echo.
echo NOTE: This is the FULL version with design drafts and full ship artwork.
echo       For faster generation without design drafts/artwork, use:
echo       SpaceWhaleSD3TextureGenerator_Fast.bat
echo.

REM Run PowerShell script with all texture types including full ship artwork
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" %* -TextureType "all" -IncludeFullShipArtwork

set "EXIT_CODE=%ERRORLEVEL%"

if %EXIT_CODE% NEQ 0 (
    echo.
    echo Script exited with error code: %EXIT_CODE%
    pause
)

exit /b %EXIT_CODE%
