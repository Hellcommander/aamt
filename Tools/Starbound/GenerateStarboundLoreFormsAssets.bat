@echo off
REM GenerateStarboundLoreFormsAssets.bat
REM Batch wrapper for generating assets for all Starbound lore-themed mech forms

cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -File "%~dp0GenerateStarboundLoreFormsAssets.ps1" %*
pause
