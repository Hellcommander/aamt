@echo off
REM Generate assets for Centipede mech form
pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0GenerateCentipedeFormAssets.ps1" %*
