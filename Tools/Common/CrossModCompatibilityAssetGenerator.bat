@echo off
REM CrossModCompatibility Asset Generator - Batch Launcher
REM Generates all assets for CrossModCompatibility extension:
REM   - Ships (120 facings spritesheets)
REM   - Weapons (icons + projectile sprites)
REM   - Items (icons)
REM   - Projectiles (sprites)
REM   - Spritesheets (weapon parts)

echo ========================================
echo CrossModCompatibility Asset Generator
echo ========================================
echo.
echo This will generate:
echo   - Ship assets (120 facings)
echo   - Weapon icons (96x96)
echo   - Weapon projectiles (32x32 sprites)
echo   - Item icons (96x96)
echo   - Projectile sprites (32x32)
echo   - Weapon parts spritesheet
echo.
echo Quality: High
echo.

pwsh.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0CrossModCompatibilityAssetGenerator.ps1" -GenerateAll -Quality High

echo.
echo ========================================
echo Generation Complete!
echo ========================================
echo.
echo Check the output directory for generated assets:
echo   Transcendence\TranscendenceArt\CrossModCompatibility
echo.
echo Check logs for details:
echo   Tools\Logs\CrossModCompatibilityAssets_*.log
echo.

pause

