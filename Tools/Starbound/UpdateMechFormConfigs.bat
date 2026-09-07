@echo off
REM Update existing mech form JSON configs with new animation and enhanced fields
pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0UpdateMechFormConfigs.ps1" %*
