@echo off
REM GenerateHorrorFormsAssets.bat
REM Batch wrapper for generating assets for all horror-themed mech forms

cd /d "%~dp0"
echo WARNING: This will generate horror-themed assets that may contain disturbing imagery.
echo.
pause
powershell.exe -ExecutionPolicy Bypass -File "%~dp0GenerateHorrorFormsAssets.ps1" %*
pause
