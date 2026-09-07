@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Stop-StableDiffusionServer.ps1" %*
