@echo off
REM ============================================================
REM Space Whale Item Generator - Batch Wrapper
REM Generates Transcendence ItemType definitions
REM ============================================================

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%SpaceWhaleItemGenerator.ps1"

echo ============================================================
echo Space Whale Item Generator
echo ============================================================
echo.
echo Generates Transcendence XML items (weapons, devices, armor)
echo using Space Whale themed bio-organic technology
echo.

if not exist "%PS_SCRIPT%" (
    echo ERROR: PowerShell script not found at:
    echo   %PS_SCRIPT%
    echo.
    pause
    exit /b 1
)

echo Item Categories:
echo   [1] Weapons (Bio-Pulse Cannon, Whale Song Resonator, etc.)
echo   [2] Devices (Bio-Regenerative Shield, Symbiotic Repair, etc.)
echo   [3] Armor (Living Carapace, Bio-Reactive Hull, etc.)
echo   [4] Reactors (Bio-Organic Core, Leviathan Heart, etc.)
echo   [5] Ammunition (Bio-Missiles, Symbiotic Torpedoes, etc.)
echo.
echo Generating all categories...
echo.

pwsh -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" %*

set "EXIT_CODE=%ERRORLEVEL%"

echo.
if %EXIT_CODE%==0 (
    echo ============================================================
    echo Item Generation Complete!
    echo ============================================================
    echo.
    echo Output: Output\Items\
    echo.
    echo Generated Files:
    echo   - SpaceWhaleWeapons.xml (6 weapons)
    echo   - SpaceWhaleDevices.xml (6 devices)
    echo   - SpaceWhaleArmor.xml (6 armor types)
    echo   - SpaceWhaleReactors.xml (6 bio-reactors)
    echo   - SpaceWhaleAmmunition.xml (3 ammo types)
    echo   - item_registry.json
    echo.
    echo Next Steps:
    echo   1. Review XML files in Output\Items
    echo   2. Copy to your Transcendence extension
    echo   3. Add to your extension's main XML file
    echo   4. Test in-game
    echo.
) else (
    echo ============================================================
    echo Item Generation Failed
    echo ============================================================
    echo.
    echo Exit code: %EXIT_CODE%
    echo Check error messages above
    echo.
)

pause
exit /b %EXIT_CODE%
