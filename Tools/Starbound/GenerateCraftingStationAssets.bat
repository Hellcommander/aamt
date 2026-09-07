@echo off
cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -File "%~dp0GenerateCraftingStationAssets.ps1" %*
pause
