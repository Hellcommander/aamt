@echo off
rem Drop converted mod folders onto this file (see README.md, "Drag and drop").
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0_drop.ps1" update-converted %*
echo.
pause
