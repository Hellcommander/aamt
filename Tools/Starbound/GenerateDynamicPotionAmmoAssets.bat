@echo off
cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -File "%~dp0GenerateDynamicPotionAmmoAssets.ps1" %*
pause
