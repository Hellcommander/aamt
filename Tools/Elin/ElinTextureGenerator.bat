@echo off
REM ElinTextureGenerator.bat - Drag-and-Drop Wrapper
REM Generates Elin texture files with animation support
setlocal

set "SCRIPT_DIR=%~dp0"

if "%~1" neq "" (
    REM File/folder dropped - use as texture name
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%ElinTextureGenerator.ps1" -TextureName "%~n1" -TextureType Item -Preset Basic -OutputDir "%~dp1" -GeneratePlaceholder
) else (
    REM No file dropped, show usage
    echo.
    echo ============================================
    echo   Elin Texture Generator
    echo ============================================
    echo.
    echo Usage: Drag a file onto this batch file to use its name as the texture name
    echo.
    echo Or run directly with PowerShell:
    echo   .\ElinTextureGenerator.ps1 -TextureName "my_item" -TextureType Item -Preset Fountain
    echo.
    echo Texture Types:
    echo   Item         - Items, furniture, objects (48x48)
    echo   Chara        - Character sprites (32x48)
    echo   CharaSprite  - Character sprite parts (32x32)
    echo   Map          - Map backgrounds (256x256)
    echo   MapTile      - Map tiles (48x24)
    echo   Effect       - Visual effects (64x64)
    echo   UI           - UI elements (32x32)
    echo   Icon         - Icons (32x32)
    echo   Portrait     - Character portraits (80x112)
    echo.
    echo Item Presets:
    echo   Basic, Furniture, Statue, Sign, Wagon, Boat, Tree, Fountain, Tent
    echo.
    echo Flags:
    echo   -Animated              Enable animation
    echo   -GenerateSnowVariant   Create snow variant
    echo   -NumberedVariants N    Create N numbered variants
    echo   -GeneratePlaceholder   Create placeholder images
    echo.
    pause
)

if %ERRORLEVEL% neq 0 pause
endlocal

