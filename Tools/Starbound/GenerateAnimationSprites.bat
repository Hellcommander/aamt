@echo off
REM ============================================================
REM GenerateAnimationSprites - Wrapper Script
REM ============================================================
REM
REM Generates animation spritesheets for mod animations
REM ============================================================

set SCRIPT_DIR=%~dp0
set PS_SCRIPT=%SCRIPT_DIR%GenerateAnimationSprites.ps1

if not exist "%PS_SCRIPT%" (
    echo ERROR: PowerShell script not found at:
    echo   %PS_SCRIPT%
    echo.
    if defined STARBOUND_INTERACTIVE pause
    exit /b 1
)

echo Running GenerateAnimationSprites.ps1...
echo.

pwsh -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" %*

set EXIT_CODE=%ERRORLEVEL%

if %EXIT_CODE% NEQ 0 (
    echo.
    echo ============================================================
    echo Script exited with error code: %EXIT_CODE%
    echo ============================================================
    echo.
    echo Please check the error messages above for details.
    echo.
) else (
    echo.
    echo ============================================================
    echo Script completed successfully!
    echo ============================================================
    echo.
)

REM Non-interactive by default; set STARBOUND_INTERACTIVE=1 to hold the window open.
if defined STARBOUND_INTERACTIVE pause
exit /b %EXIT_CODE%
