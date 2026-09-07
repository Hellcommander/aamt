@echo off
REM ============================================================
REM StarboundAnimationGenerator.bat - Quick Animation Creation
REM ============================================================

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%StarboundAnimationGenerator.ps1"

where pwsh >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "POWERSHELL=pwsh"
) else (
    set "POWERSHELL=powershell"
)

echo ================================================================
echo   Starbound Animation Generator
echo ================================================================
echo.
echo Presets: Fire, Ice, Poison, Electric, Smoke, Sparkle, Poof, HitSpark
echo.

REM Check if file was dropped
if "%~1" neq "" (
    REM Image file was dropped - use it as source
    echo Using dropped image: %~nx1
    set /p "ANIM_NAME=Enter animation name: "
    if "!ANIM_NAME!"=="" set "ANIM_NAME=animation"
    
    set /p "FRAME_COUNT=Enter frame count: "
    if "!FRAME_COUNT!"=="" set "FRAME_COUNT=8"
    
    %POWERSHELL% -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -AnimationName "!ANIM_NAME!" -ImagePath "%~1" -FrameCount !FRAME_COUNT!
    goto :done
)

set /p "ANIM_NAME=Enter animation name: "
if "!ANIM_NAME!"=="" (
    echo Error: Animation name is required.
    goto :error
)

echo.
echo Select a preset (or press Enter for custom):
set /p "PRESET=Preset [Fire/Ice/Poison/Electric/Smoke/Sparkle/Poof/HitSpark]: "
if "!PRESET!"=="" set "PRESET=None"

if /i "!PRESET!"=="None" (
    echo.
    set /p "FRAME_COUNT=Frame count [8]: "
    if "!FRAME_COUNT!"=="" set "FRAME_COUNT=8"
    
    set /p "FRAME_SIZE=Frame size WxH [32x32]: "
    if "!FRAME_SIZE!"=="" set "FRAME_SIZE=32x32"
    
    REM Parse frame size
    for /f "tokens=1,2 delims=x" %%a in ("!FRAME_SIZE!") do (
        set "FRAME_W=%%a"
        set "FRAME_H=%%b"
    )
    
    set /p "CYCLE=Animation cycle seconds [0.5]: "
    if "!CYCLE!"=="" set "CYCLE=0.5"
    
    set /p "GEN_PLACEHOLDER=Generate placeholder image? [y/N]: "
    
    if /i "!GEN_PLACEHOLDER!"=="y" (
        %POWERSHELL% -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -AnimationName "!ANIM_NAME!" -FrameCount !FRAME_COUNT! -FrameSize @(!FRAME_W!,!FRAME_H!) -AnimationCycle !CYCLE! -GeneratePlaceholderImage
    ) else (
        %POWERSHELL% -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -AnimationName "!ANIM_NAME!" -FrameCount !FRAME_COUNT! -FrameSize @(!FRAME_W!,!FRAME_H!) -AnimationCycle !CYCLE!
    )
) else (
    set /p "GEN_PLACEHOLDER=Generate placeholder image? [y/N]: "
    
    if /i "!GEN_PLACEHOLDER!"=="y" (
        %POWERSHELL% -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -AnimationName "!ANIM_NAME!" -Preset "!PRESET!" -GeneratePlaceholderImage
    ) else (
        %POWERSHELL% -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -AnimationName "!ANIM_NAME!" -Preset "!PRESET!"
    )
)

:done
if %ERRORLEVEL% neq 0 goto :error

echo.
echo ================================================================
echo   Generation Complete!
echo ================================================================
goto :end

:error
echo.
echo An error occurred.

:end
echo.
pause
endlocal

