@echo off
REM Live SD3.5 server status GUI (:1338) - no console flash
REM Usage:
REM   SDServer-Status-GUI.bat
REM   SDServer-Status-GUI.bat -StartServer
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Open-SDStatusGui.ps1" %*
exit /b 0
