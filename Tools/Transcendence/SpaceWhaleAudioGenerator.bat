@echo off
REM ============================================================
REM SpaceWhaleAudioGenerator - Wrapper Script
REM ============================================================
REM
REM Launches the PowerShell script with proper execution policy
REM ============================================================

set SCRIPT_DIR=%~dp0
set PS_SCRIPT=%SCRIPT_DIR%SpaceWhaleAudioGenerator.ps1

if not exist "%PS_SCRIPT%" (
    echo ERROR: PowerShell script not found at:
    echo   %PS_SCRIPT%
    echo.
    pause
    exit /b 1
)

REM Try PowerShell Core first, fallback to Windows PowerShell
where pwsh >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" %*
) else (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" %*
)

set EXIT_CODE=%ERRORLEVEL%

if %EXIT_CODE% NEQ 0 (
    echo.
    echo Script exited with error code: %EXIT_CODE%
) else (
    echo.
    echo Script completed successfully.
)

echo.
pause
