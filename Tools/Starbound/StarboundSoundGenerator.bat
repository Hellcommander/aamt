@echo off
REM Wrapper for StarboundSoundGenerator.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0StarboundSoundGenerator.ps1" %*
