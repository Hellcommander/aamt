@echo off
REM StarboundShipGenerator.bat - Drag-and-Drop Wrapper
REM Generates Starbound ship structure files
setlocal

set "SCRIPT_DIR=%~dp0"

if "%~1" neq "" (
    REM File/folder dropped - use as ship/race name
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%StarboundShipGenerator.ps1" -ShipName "%~n1" -Race "%~n1" -Preset Generic -OutputDir "%~dp1" -IncludeAllTiers -GeneratePlaceholders
) else (
    REM No file dropped, show usage
    echo.
    echo ============================================
    echo   Starbound Ship Generator
    echo ============================================
    echo.
    echo Usage: Drag a file onto this batch file to use its name as the ship name
    echo.
    echo Or run directly with PowerShell:
    echo   .\StarboundShipGenerator.ps1 -ShipName "myship" -Race "myrace"
    echo.
    echo Available Presets:
    echo   Human    - Human ship style
    echo   Apex     - Apex ship style
    echo   Avian    - Avian ship style
    echo   Floran   - Floran ship style
    echo   Glitch   - Glitch ship style
    echo   Hylotl   - Hylotl ship style
    echo   Novakid  - Novakid ship style
    echo   Generic  - Generic ship template
    echo   Custom   - Full customization
    echo.
    echo Generated files per tier:
    echo   - shipnameT#.structure  (ship definition)
    echo   - shipnameT#blocks.png  (block map)
    echo   - shipnameT#.png        (ship sprite - you create)
    echo   - shipnameT#lit.png     (lit overlay - you create)
    echo.
    pause
)

if %ERRORLEVEL% neq 0 pause
endlocal

