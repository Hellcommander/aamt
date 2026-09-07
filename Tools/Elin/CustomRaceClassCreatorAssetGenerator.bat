@echo off
setlocal enabledelayedexpansion
set SCRIPT_DIR=%~dp0
set PS_SCRIPT=%SCRIPT_DIR%CustomRaceClassCreatorAssetGenerator.ps1

echo.
echo ========================================
echo CustomRaceClassCreator Asset Generator
echo ========================================
echo.

if not exist "%PS_SCRIPT%" (
    echo ERROR: PowerShell script not found: %PS_SCRIPT%
    echo.
    pause
    exit /b 1
)

REM Default mod path if not provided
set "DEFAULT_MOD_PATH=E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator"

REM Use provided path or default
if "%~1"=="" (
    set "MOD_PATH=!DEFAULT_MOD_PATH!"
    echo Using default mod path: !MOD_PATH!
    echo.
    echo To use a different path, drag the mod folder onto this batch file
    echo or run: %~nx0 "MOD_PATH"
    echo.
) else (
    set "MOD_PATH=%~1"
)

if not exist "!MOD_PATH!" (
    echo ERROR: Mod path does not exist: !MOD_PATH!
    echo.
    pause
    exit /b 1
)

echo Mod Path: !MOD_PATH!
echo.
echo Starting asset generation...
echo.

REM Enable AI by default (will auto-disable if Ollama not available)
REM Use PowerShell 7 from specific path
"C:\Program Files\PowerShell\7\pwsh.exe" -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -ModPath "!MOD_PATH!" -UseAI

set EXIT_CODE=%ERRORLEVEL%
echo.
echo ========================================
if %EXIT_CODE% NEQ 0 (
    echo Script exited with error code: %EXIT_CODE%
    echo.
    echo Check the output above for error details.
) else (
    echo Generation completed successfully!
)
echo ========================================
echo.
pause
endlocal
exit /b %EXIT_CODE%