@echo off
REM Install-CondaAndSetup.bat
REM Batch wrapper for Install-CondaAndSetup.ps1

setlocal

powershell -ExecutionPolicy Bypass -File "%~dp0Install-CondaAndSetup.ps1"

pause

endlocal
