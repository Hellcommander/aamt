@echo off
rem Drop a merged mod data folder onto this file (see README.md, "Drag and drop").
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0_drop.ps1" hdmatch %*
echo.
pause
