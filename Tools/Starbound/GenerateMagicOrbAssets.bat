@echo off
REM Generate assets for Magic Orb weapon system
pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0GenerateMagicOrbAssets.ps1" %*
