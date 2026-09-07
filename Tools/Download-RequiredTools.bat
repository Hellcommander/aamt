@echo off
REM Download-RequiredTools.bat
REM Batch wrapper for Download-RequiredTools.ps1

setlocal

powershell -ExecutionPolicy Bypass -File "%~dp0Download-RequiredTools.ps1" -All

pause

endlocal
