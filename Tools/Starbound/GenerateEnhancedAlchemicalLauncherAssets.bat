@echo off
REM Generate assets for Enhanced Alchemical Grenade Launcher system
pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0GenerateEnhancedAlchemicalLauncherAssets.ps1" %*
