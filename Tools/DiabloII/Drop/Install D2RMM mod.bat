@echo off
rem Drop a mod download (.zip, .7z, .rar or folder) onto this file (see README.md, "Drag and drop").
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0_drop.ps1" install %*
echo.
pause
