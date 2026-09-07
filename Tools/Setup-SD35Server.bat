@echo off
REM Setup SD3.5 Server (from Tools directory)
REM Wrapper for Setup-SD35Server.ps1

setlocal

cd /d "%~dp0"

echo ============================================================
echo SD3.5 Server Setup
echo ============================================================
echo.

REM Check for PowerShell
where pwsh >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PWSH_CMD=pwsh
) else (
    where powershell >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set PWSH_CMD=powershell
    ) else (
        echo [ERROR] PowerShell not found!
        pause
        exit /b 1
    )
)

echo Using: %PWSH_CMD%
echo.

REM Run the PowerShell setup script
%PWSH_CMD% -NoProfile -ExecutionPolicy Bypass -File "%~dp0Setup-SD35Server.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Setup failed!
    pause
    exit /b 1
)

echo.
echo Setup complete!
echo.
pause
