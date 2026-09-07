@echo off
cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -File "%~dp0GenerateMechCockpitAssets.ps1" %*
pause
