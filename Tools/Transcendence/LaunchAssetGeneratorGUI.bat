@echo off
REM ============================================================
REM Launch Asset Generator GUI
REM Full GUI-based asset generation with interactive controls
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_DIR=%SCRIPT_DIR%Output\SpaceWhaleAssets"
set "SHIP_ID=leviathan_alpha"
set "OLLAMA_MODEL="
set "VARIATIONS=150"

echo.
echo ============================================================
echo   Asset Generator GUI
echo ============================================================
echo.
echo Launching GUI-based generator...
echo.
echo Configuration:
echo   - Ship ID: %SHIP_ID%
echo   - Output: %OUTPUT_DIR%
echo   - Variations: %VARIATIONS%
echo   - Models: Auto-detected (CodeLlama-34B + WizardLM-uncensored)
echo.
echo ============================================================
echo.

cd /d "%SCRIPT_DIR%"

powershell -STA -NoProfile -ExecutionPolicy Bypass -File "SpaceWhaleAssetGeneratorGUI.ps1" -ShipId "%SHIP_ID%" -OutputDir "%OUTPUT_DIR%" -Variations %VARIATIONS%

echo.
echo GUI closed.
echo.
pause
endlocal

