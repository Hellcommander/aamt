@echo off
REM ============================================================
REM Export to Transcendence XML
REM Converts generated assets to Transcendence-compatible XML
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_DIR=%SCRIPT_DIR%Output\TranscendenceXML"
set "REGISTRY=%SCRIPT_DIR%space_whale_ship_example.json"
set "SHIP_ID=leviathan_alpha"

echo.
echo ============================================================
echo   Transcendence XML Exporter
echo ============================================================
echo.
echo Exporting ship: %SHIP_ID%
echo Output: %OUTPUT_DIR%
echo.
echo ============================================================
echo.

cd /d "%SCRIPT_DIR%"

python transcendence_space_whale_exporter.py --registry "%REGISTRY%" --ship-id "%SHIP_ID%" --output-dir "%OUTPUT_DIR%"

if %ERRORLEVEL% equ 0 (
    echo.
    echo ============================================================
    echo   XML Export Complete!
    echo ============================================================
    echo.
    echo XML files saved to: %OUTPUT_DIR%
    echo.
    echo You can now integrate these into your Transcendence mod.
) else (
    echo.
    echo ============================================================
    echo   Export Failed
    echo ============================================================
)

pause
endlocal

