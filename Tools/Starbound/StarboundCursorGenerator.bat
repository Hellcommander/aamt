@echo off
REM StarboundCursorGenerator.bat - Drag-and-Drop Wrapper
REM Generates Starbound cursor files (.cursor, .frames)
setlocal

set "SCRIPT_DIR=%~dp0"

if "%~1" neq "" (
    REM File/folder dropped - use as cursor name
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%StarboundCursorGenerator.ps1" -CursorName "%~n1" -Preset Default -OutputDir "%~dp1" -GeneratePlaceholderImage
) else (
    REM No file dropped, show usage
    echo.
    echo ============================================
    echo   Starbound Cursor Generator
    echo ============================================
    echo.
    echo Usage: Drag a file onto this batch file to use its name as the cursor name
    echo.
    echo Or run directly with PowerShell:
    echo   .\StarboundCursorGenerator.ps1 -CursorName "mycursor" -Preset Pointer
    echo.
    echo Available Presets:
    echo   Default   - Simple 16x16 cursor
    echo   Pointer   - Arrow pointer with states (normal, hover, click)
    echo   Crosshair - Centered 32x32 crosshair
    echo   Joystick  - 5-direction joystick (neutral, up, down, left, right)
    echo   Hand      - Hand cursor (open, pointing, grabbing)
    echo   Text      - I-beam text cursor
    echo   Wait      - Animated waiting cursor (8 frames)
    echo   Move      - Move/drag cursor
    echo   Resize    - Resize cursors (4 directions)
    echo   Custom    - Full customization
    echo.
    pause
)

if %ERRORLEVEL% neq 0 pause
endlocal

