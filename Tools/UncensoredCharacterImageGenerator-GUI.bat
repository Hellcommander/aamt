@echo off
REM UncensoredCharacterImageGenerator-GUI.bat
REM Batch wrapper for UncensoredCharacterImageGenerator-GUI.ps1

setlocal

set "SCRIPT_PATH=%~dp0UncensoredCharacterImageGenerator-GUI.ps1"

REM Verify script exists
if not exist "%SCRIPT_PATH%" (
    echo Error: PowerShell script not found: %SCRIPT_PATH%
    pause
    exit /b 1
)

echo Starting GUI...
powershell -STA -ExecutionPolicy Bypass -File "%SCRIPT_PATH%"

set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
    echo.
    echo Error: Script exited with code %EXIT_CODE%
    pause
    exit /b %EXIT_CODE%
)

endlocal
