@echo off
REM StarboundTileGenerator.bat - Drag-and-Drop Wrapper
REM Generates Starbound tile files (.frames, .material)
setlocal

set "SCRIPT_DIR=%~dp0"

if "%~1" neq "" (
    REM File/folder dropped - use as tile name
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%StarboundTileGenerator.ps1" -TileName "%~n1" -Preset Basic -OutputDir "%~dp1" -GeneratePlaceholderImage
) else (
    REM No file dropped, show usage
    echo.
    echo ============================================
    echo   Starbound Tile Generator
    echo ============================================
    echo.
    echo Usage: Drag a file onto this batch file to use its name as the tile name
    echo.
    echo Or run directly with PowerShell:
    echo   .\StarboundTileGenerator.ps1 -TileName "mytile" -Preset Brick
    echo.
    echo Available Presets:
    echo   Basic      - Simple 1-variant tile
    echo   Protection - 5-variant protection blocks
    echo   Platform   - Platform tiles (4 variants)
    echo   Ore        - Mineable ore (with item drops)
    echo   Brick      - 16-variant brick patterns
    echo   Natural    - Dirt/grass type tiles
    echo   Metal      - Metal/industrial tiles
    echo   Glass      - Transparent glass tiles
    echo   Organic    - Fleshy/organic tiles
    echo   Tech       - High-tech tiles (8 variants)
    echo   Custom     - Full customization
    echo.
    echo Additional flags:
    echo   -GenerateMaterial   : Also generate .material file
    echo   -GenerateMatmod     : Also generate .matmod file
    echo.
    pause
)

if %ERRORLEVEL% neq 0 pause
endlocal

