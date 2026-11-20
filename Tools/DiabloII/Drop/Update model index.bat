@echo off
rem Drop D2RMM mod folders that add HD models onto this file (see README.md, "Drag and drop").
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0_drop.ps1" model-index %*
echo.
pause
