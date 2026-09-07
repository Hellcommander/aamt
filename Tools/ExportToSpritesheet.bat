@echo off
REM ExportToSpritesheet.bat
REM Batch wrapper for ExportToSpritesheet.ps1

setlocal

set SCRIPT_DIR=%~dp0
set PS_SCRIPT=%SCRIPT_DIR%ExportToSpritesheet.ps1

REM Check if PowerShell is available
powershell -Command "exit 0" >nul 2>&1
if errorlevel 1 (
    echo Error: PowerShell is not available
    exit /b 1
)

REM Run PowerShell script with all arguments
powershell -ExecutionPolicy Bypass -File "%PS_SCRIPT%" %*

endlocal

