@echo off
rem Drop one or more D2RMM mod folders onto this file (see README.md, "Drag and drop").
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0_drop.ps1" test %*
echo.
pause
