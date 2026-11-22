@echo off
rem Drop .mpq archives onto this file (see README.md, "Drag and drop").
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0_drop.ps1" extract-mpq %*
echo.
pause
