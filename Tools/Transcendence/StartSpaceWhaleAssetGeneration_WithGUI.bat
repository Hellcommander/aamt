@echo off
REM ============================================================
REM Start Space Whale Asset Generation - With Full GUI
REM ============================================================
REM Launches the GUI-based generator instead of command-line
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_DIR=%SCRIPT_DIR%Output\SpaceWhaleAssets"
set "SHIP_ID=leviathan_alpha"
set "OLLAMA_MODEL=wizardlm-uncensored:latest"
set "VARIATIONS=150"

echo.
echo ============================================================
echo   Space Whale Asset Generation - GUI Mode
echo ============================================================
echo.
echo Launching GUI-based generator...
echo.

REM Launch GUI generator
set "GUI_SCRIPT=%SCRIPT_DIR%SpaceWhaleAssetGeneratorGUI.ps1"
if exist "%GUI_SCRIPT%" (
    REM GUI script accepts: -RegistryPath, -OutputDir, -ShipId
    REM Note: OllamaModel and Variations are hardcoded in the GUI script
    powershell -STA -NoProfile -ExecutionPolicy Bypass -File "%GUI_SCRIPT%" -ShipId "%SHIP_ID%" -OutputDir "%OUTPUT_DIR%"
    if errorlevel 1 (
        echo.
        echo ERROR: GUI script failed to launch
        echo Check the error message above for details
        pause
        exit /b 1
    )
) else (
    echo ERROR: GUI script not found: %GUI_SCRIPT%
    echo.
    echo Falling back to command-line generator...
    call "%SCRIPT_DIR%StartSpaceWhaleAssetGeneration.bat"
)

endlocal

