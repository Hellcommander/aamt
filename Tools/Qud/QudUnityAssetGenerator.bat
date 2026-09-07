@echo off
setlocal enabledelayedexpansion
set SCRIPT_DIR=%~dp0
set PS_SCRIPT=%SCRIPT_DIR%QudUnityAssetGenerator.ps1

echo.
echo ========================================
echo Caves of Qud Unity Asset Generator
echo ========================================
echo.

if not exist "%PS_SCRIPT%" (
    echo ERROR: PowerShell script not found: %PS_SCRIPT%
    echo.
    pause
    exit /b 1
)

REM Default mod path if not provided
set "DEFAULT_MOD_PATH="

REM Use provided path or prompt
if "%~1"=="" (
    if "!DEFAULT_MOD_PATH!"=="" (
        echo ERROR: No mod path provided
        echo.
        echo Usage: %~nx0 "MOD_PATH"
        echo   or: %~nx0 "MOD_PATH" "ASSET_TYPES"
        echo.
        echo Example: %~nx0 "C:\QudMods\MyMod"
        echo Example: %~nx0 "C:\QudMods\MyMod" "materials,prefabs"
        echo.
        pause
        exit /b 1
    )
    set "MOD_PATH=!DEFAULT_MOD_PATH!"
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

REM Check for scan-only flag
set "SCAN_ONLY="
if /i "%~2"=="--scan" set "SCAN_ONLY=-ScanOnly"

REM Use PowerShell 7
"C:\Program Files\PowerShell\7\pwsh.exe" -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -ModPath "!MOD_PATH!" !SCAN_ONLY!

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
