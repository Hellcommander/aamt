@echo off
rem Drop a saved mod list .json onto this file (see README.md, "Drag and drop").
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0_drop.ps1" check-list %*
echo.
pause
