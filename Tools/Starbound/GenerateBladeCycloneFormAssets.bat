@echo off
REM Generate assets for Blade Cyclone mech form
pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0GenerateBladeCycloneFormAssets.ps1" %*
