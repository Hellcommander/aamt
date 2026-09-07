@echo off
REM Script to make PowerShell 7 the default PowerShell
REM Run this as Administrator

echo.
echo ========================================
echo Make PowerShell 7 Default
echo ========================================
echo.
echo This script will:
echo   1. Add PowerShell 7 to your PATH
echo   2. Create pwsh alias in PowerShell profile
echo   3. Show Windows Terminal setup instructions
echo.
echo NOTE: This script must be run as Administrator!
echo.
pause

REM Check for Administrator
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: This script must be run as Administrator!
    echo Right-click this file and select "Run as administrator"
    pause
    exit /b 1
)

REM Run the PowerShell script
"C:\Program Files\PowerShell\7\pwsh.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0SetPowerShell7AsDefault.ps1"

pause
