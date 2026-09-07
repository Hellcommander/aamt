@echo off
REM GenerateQuadrapedFormsAssets.bat
REM Batch wrapper for generating assets for all quadraped mech forms

cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -File "%~dp0GenerateQuadrapedFormsAssets.ps1" %*
pause
