@echo off
REM ============================================================
REM Generate Rigging Assets
REM Creates Blender armature and bone structure for Space Whale
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_DIR=%SCRIPT_DIR%Output\Rigging"
set "REGISTRY=%SCRIPT_DIR%space_whale_ship_example.json"

echo.
echo ============================================================
echo   Rigging Generator
echo ============================================================
echo.
echo Generating rigging assets...
echo Output: %OUTPUT_DIR%
echo.
echo NOTE: Requires Blender to be installed
echo.
echo ============================================================
echo.

cd /d "%SCRIPT_DIR%"

powershell -NoProfile -ExecutionPolicy Bypass -File "SpaceWhaleRiggingGenerator.ps1" -RegistryPath "%REGISTRY%" -OutputDir "%OUTPUT_DIR%"

if %ERRORLEVEL% equ 0 (
    echo.
    echo ============================================================
    echo   Rigging Generation Complete!
    echo ============================================================
) else (
    echo.
    echo ============================================================
    echo   Generation Failed
    echo ============================================================
    echo.
    echo Make sure Blender is installed and configured.
)

pause
endlocal

