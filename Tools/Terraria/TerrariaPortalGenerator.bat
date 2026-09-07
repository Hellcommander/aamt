@echo off
REM TerrariaPortalGenerator.bat - Drag-and-Drop Wrapper
REM AI-Assisted Modding Tools (AAMT) - Terraria Toolset
REM Generates complete portal effect packages for Terraria mods
setlocal

set "SCRIPT_DIR=%~dp0"

if "%~1" neq "" (
    REM File/folder dropped - use as portal name
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%TerrariaPortalGenerator.ps1" -PortalName "%~n1" -Preset Void -OutputDir "%~dp1" -GeneratePlaceholders
) else (
    REM No file dropped, show usage
    echo.
    echo ============================================
    echo   Terraria Portal Generator
    echo ============================================
    echo.
    echo Usage: Drag a file onto this batch file to use its name as the portal name
    echo.
    echo Or run directly with PowerShell:
    echo   .\TerrariaPortalGenerator.ps1 -PortalName "voidgate" -Preset Void
    echo.
    echo Presets:
    echo   Void      - Cold blue void portal (default)
    echo   Fire      - Fiery red portal
    echo   Ice       - Frosty blue portal
    echo   Electric  - Electric yellow portal
    echo   Nature    - Green nature portal
    echo   Shadow    - Dark purple portal
    echo   Light     - Bright golden portal
    echo   Custom    - Full customization
    echo.
    echo Features:
    echo   - Portal tile textures (base, frame, normal, distortion)
    echo   - Particle effect JSON profiles
    echo   - Shader configuration
    echo   - tModLoader code templates
    echo   - Spacetime distortion effects
    echo.
    pause
)

if %ERRORLEVEL% neq 0 pause
endlocal

