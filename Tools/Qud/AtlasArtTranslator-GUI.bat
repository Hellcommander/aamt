@echo off
cd /d "%~dp0"
powershell -STA -NoProfile -ExecutionPolicy Bypass -File "%~dp0AtlasArtTranslator-GUI.ps1"
if errorlevel 1 pause
