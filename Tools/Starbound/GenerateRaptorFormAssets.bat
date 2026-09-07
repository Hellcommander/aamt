@echo off
REM Generate assets for Raptor mech form
pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0GenerateRaptorFormAssets.ps1" %*
