@echo off
REM Batch renderer for all Space Whale and Evolved Ship 120 Facings
REM Calls Blender with appropriate Python scripts for each ship type

setlocal enabledelayedexpansion

echo ============================================================
echo Space Whale and Evolved Ships 120 Facings Batch Renderer
echo ============================================================
echo.

REM Prefer Tools\TranscendenceTools.ini BlenderPath (via python Shared\tool_paths.py)
for /f "usebackq tokens=2 delims=:" %%A in (`python "%~dp0..\Shared\tool_paths.py" 2^>nul ^| findstr /b "Blender:"`) do set "BLENDER_PATH=%%A"
if defined BLENDER_PATH set "BLENDER_PATH=%BLENDER_PATH:~1%"
if not defined BLENDER_PATH set "BLENDER_PATH=E:\tools\Blender Foundation\Blender 5.2\blender.exe"
set "OUTPUT_DIR=Output\120Facings"
set "SCRIPT_DIR=%~dp0"

REM Check if Blender exists
if not exist "%BLENDER_PATH%" (
    echo ERROR: Blender not found at: %BLENDER_PATH%
    echo Please update BLENDER_PATH in this script
    pause
    exit /b 1
)

echo Using Blender: %BLENDER_PATH%
echo Output directory: %OUTPUT_DIR%
echo.

REM Create output directory
if not exist "%OUTPUT_DIR%" (
    mkdir "%OUTPUT_DIR%"
    echo Created output directory
)

echo.
echo ==================================================
echo Rendering Space Whale Ships
echo ==================================================
echo.

REM Main Space Whale (256x256)
echo [1/3] Rendering Main Space Whale (256x256)...
"%BLENDER_PATH%" --background --python "%SCRIPT_DIR%blender_space_whale_main_120_facings.py" -- --output-dir "%OUTPUT_DIR%" --ship-id scSpaceWhale --frame-size 256
if errorlevel 1 (
    echo WARNING: Main Space Whale rendering failed
) else (
    echo SUCCESS: Main Space Whale rendered
)
echo.

REM Whale Segment (128x128)
echo [2/3] Rendering Space Whale Segment (128x128)...
"%BLENDER_PATH%" --background --python "%SCRIPT_DIR%blender_space_whale_segment_120_facings.py" -- --output-dir "%OUTPUT_DIR%" --ship-id scSpaceWhaleSegment --frame-size 128
if errorlevel 1 (
    echo WARNING: Space Whale Segment rendering failed
) else (
    echo SUCCESS: Space Whale Segment rendered
)
echo.

REM Whale Drone (64x64)
echo [3/3] Rendering Space Whale Drone (64x64)...
"%BLENDER_PATH%" --background --python "%SCRIPT_DIR%blender_space_whale_drone_120_facings.py" -- --output-dir "%OUTPUT_DIR%" --ship-id scSpaceWhaleDrone --frame-size 64
if errorlevel 1 (
    echo WARNING: Space Whale Drone rendering failed
) else (
    echo SUCCESS: Space Whale Drone rendered
)
echo.

echo.
echo ==================================================
echo Rendering Complete!
echo ==================================================
echo.
echo Output directory: %OUTPUT_DIR%
echo.
echo Rendered ship types:
echo   - scSpaceWhale (256x256 main ship)
echo   - scSpaceWhaleSegment (128x128 segment)
echo   - scSpaceWhaleDrone (64x64 drone)
echo.
echo Each ship has:
echo   - [shipid]_120facings.png (spritesheet)
echo   - [shipid]_120facingsMask.bmp (transparency mask)
echo.
pause
