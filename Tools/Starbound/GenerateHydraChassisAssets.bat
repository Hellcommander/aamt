@echo off
REM Generate assets for Hydra Chassis modular mech system
pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0GenerateHydraChassisAssets.ps1" %*
