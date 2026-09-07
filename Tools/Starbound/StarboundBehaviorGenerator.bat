@echo off
REM StarboundBehaviorGenerator.bat - Drag-and-Drop Wrapper
REM Generates Starbound behavior tree files for monster/NPC AI
setlocal

set "SCRIPT_DIR=%~dp0"

if "%~1" neq "" (
    REM File/folder dropped - use as behavior name
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%StarboundBehaviorGenerator.ps1" -BehaviorName "%~n1" -Preset Default -OutputDir "%~dp1"
) else (
    REM No file dropped, show usage
    echo.
    echo ============================================
    echo   Starbound Behavior Generator
    echo ============================================
    echo.
    echo Usage: Drag a file onto this batch file to use its name as the behavior name
    echo.
    echo Or run directly with PowerShell:
    echo   .\StarboundBehaviorGenerator.ps1 -BehaviorName "mybehavior" -Preset Attack
    echo.
    echo Available Presets:
    echo   Default  - Basic monster with targeting, chase, and melee
    echo   Patrol   - Walks between patrol points
    echo   Attack   - Single attack action
    echo   Flee     - Runs away from target
    echo   Chase    - Follows target
    echo   Guard    - Guards a position, attacks intruders
    echo   Boss     - Multi-stage boss with health thresholds
    echo   Ranged   - Keeps distance, fires projectiles
    echo   Melee    - Close-range combat
    echo   Idle     - Just stands around
    echo   Wander   - Random movement
    echo   Targeting - Just the targeting module
    echo.
    pause
)

if %ERRORLEVEL% neq 0 pause
endlocal

