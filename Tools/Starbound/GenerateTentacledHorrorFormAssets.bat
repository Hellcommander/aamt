@echo off
REM Generate assets for Tentacled Horror mech form
pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0GenerateTentacledHorrorFormAssets.ps1" %*
