@echo off
REM CustomRaceClassCreator Mod Checker - Batch Wrapper
REM This script provides an easy way to run the mod checker

setlocal enabledelayedexpansion
title CustomRaceClassCreator Mod Checker

REM Get the directory where this batch file is located (more reliable method)
for %%I in ("%~f0") do set "BATCH_DIR=%%~dpI"
REM Remove trailing backslash
if "!BATCH_DIR:~-1!"=="\" set "BATCH_DIR=!BATCH_DIR:~0,-1!"

REM Default mod path (adjust if needed)
set "DEFAULT_MOD_PATH=E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator"

REM Initialize exit code
set "PS_EXITCODE=0"

REM Check if PowerShell 7 (pwsh) is available
set "PS_EXE=powershell"
where pwsh >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    set "PS_EXE=pwsh"
    echo Using PowerShell 7 ^(pwsh^)
) else (
    echo Using Windows PowerShell
)

echo.
echo ========================================
echo  CustomRaceClassCreator Mod Checker
echo ========================================
echo.

REM Check if first arg is a path (drag-and-drop support)
set "MOD_PATH=!DEFAULT_MOD_PATH!"
if not "%~1"=="" (
    REM Check if it looks like a path (contains :\ or :/)
    echo "%~1" | findstr /r /c:":\\" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set "MOD_PATH=%~1"
        echo Using dropped path: !MOD_PATH!
        shift
    ) else (
        echo "%~1" | findstr /r /c:":/" >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            set "MOD_PATH=%~1"
            echo Using dropped path: !MOD_PATH!
            shift
        ) else (
            echo Using default mod path: !MOD_PATH!
        )
    )
) else (
    echo Using default mod path: !MOD_PATH!
)

REM Check for AI flags
set "AI_ENABLED=1"
set "FIX_ISSUES=0"

:argloop
if "%~1"=="" goto argdone
set "ARG=%~1"
if /i "!ARG!"=="-NoAI" set "AI_ENABLED=0"
if /i "!ARG!"=="-FixIssues" set "FIX_ISSUES=1"
shift
goto argloop
:argdone

if !AI_ENABLED! EQU 1 (
    echo AI: Enabled
) else (
    echo AI: Disabled
)

if !FIX_ISSUES! EQU 1 (
    echo Auto-fix: Enabled - AI will attempt to fix issues automatically
    echo WARNING: Backups will be created, but review changes before committing
) else (
    echo Auto-fix: Disabled - use -FixIssues to enable automatic fixes
)

echo.
echo Starting mod check...
echo Note: Mod checker uses HIGH PERFORMANCE settings ^(game not running^)
echo Performance: CPU throttling enabled to prevent 100%% CPU usage
echo.

REM Run the PowerShell script with proper quoting for paths with spaces
set "PS_SCRIPT=!BATCH_DIR!\CustomRaceClassCreatorModChecker.ps1"

REM Check if script exists
if not exist "!PS_SCRIPT!" (
    echo ERROR: PowerShell script not found: !PS_SCRIPT!
    echo.
    echo Batch file directory: !BATCH_DIR!
    echo Expected script location: !PS_SCRIPT!
    echo.
    echo Please ensure the PowerShell script is in the same directory as this batch file.
    echo.
    echo Press any key to close...
    pause
    endlocal
    exit /b 1
)

REM Run PowerShell with error handling
if !AI_ENABLED! EQU 1 (
    if !FIX_ISSUES! EQU 1 (
        !PS_EXE! -ExecutionPolicy Bypass -NoProfile -File "!PS_SCRIPT!" -ModPath "!MOD_PATH!" -UseAI -FixIssues
    ) else (
        !PS_EXE! -ExecutionPolicy Bypass -NoProfile -File "!PS_SCRIPT!" -ModPath "!MOD_PATH!" -UseAI
    )
) else (
    if !FIX_ISSUES! EQU 1 (
        !PS_EXE! -ExecutionPolicy Bypass -NoProfile -File "!PS_SCRIPT!" -ModPath "!MOD_PATH!" -NoAI -FixIssues
    ) else (
        !PS_EXE! -ExecutionPolicy Bypass -NoProfile -File "!PS_SCRIPT!" -ModPath "!MOD_PATH!" -NoAI
    )
)

REM Capture the exit code
set "PS_EXITCODE=!ERRORLEVEL!"

echo.
echo ========================================
if !PS_EXITCODE! NEQ 0 (
    echo  COMPLETED WITH ERRORS ^(Exit code: !PS_EXITCODE!^)
) else (
    echo  COMPLETED SUCCESSFULLY
)
echo ========================================
echo.

REM Always pause - use multiple methods to ensure it works
echo Press any key to close this window...
pause >nul 2>&1
if errorlevel 1 (
    timeout /t 10 >nul 2>&1
)

endlocal
exit /b !PS_EXITCODE!
