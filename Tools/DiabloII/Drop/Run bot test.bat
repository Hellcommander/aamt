@echo off
rem Drop a bot script .txt onto this file (see README.md, "Drag and drop").
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0_drop.ps1" bot-test %*
echo.
pause
