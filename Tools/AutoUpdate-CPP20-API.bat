@echo off
REM ============================================================================
REM AutoUpdate-CPP20-API.bat
REM ============================================================================
REM Generic C++20 Migration Script for Transcendence API
REM Auto-detects API version and applies C++20 migration rules
REM ============================================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   Auto C++20 Migration Tool for Transcendence API
echo ============================================================
echo.
echo Performance: CPU throttling enabled to prevent 100%% CPU usage
echo.

REM Check if PowerShell is available
where powershell >nul 2>&1
if errorlevel 1 (
    echo ERROR: PowerShell is not available on this system.
    echo Please install PowerShell or use the .ps1 script directly.
    pause
    exit /b 1
)

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%AutoUpdate-CPP20-API.ps1"

REM Check if the PowerShell script exists
if not exist "%PS_SCRIPT%" (
    echo ERROR: PowerShell script not found: %PS_SCRIPT%
    echo Please ensure AutoUpdate-CPP20-API.ps1 is in the same directory.
    pause
    exit /b 1
)

REM Check if files/folders were dropped (drag and drop)
set "DROPPED_PATH="
set "SOURCE_PATH=."
if not "%~1"=="" (
    REM Check if first argument is a valid path
    if exist "%~1" (
        set "DROPPED_PATH=%~1"
        REM If it's a file, get its parent directory
        if exist "%~1\" (
            REM It's a folder
            set "SOURCE_PATH=%~1"
        ) else (
            REM It's a file - get parent directory
            for %%F in ("%~1") do set "SOURCE_PATH=%%~dpF"
            REM Remove trailing backslash
            set "SOURCE_PATH=!SOURCE_PATH:~0,-1!"
        )
    ) else (
        REM Not a path, might be a flag - use as-is
        set "SOURCE_PATH=%~1"
    )
)

REM Check for flags
set "BACKUP_FLAG=-Backup"
set "VERBOSE_FLAG="
set "DRYRUN_FLAG="
set "SKIPONLINE_FLAG="
set "NOAI_FLAG="
set "USEAI_FLAG="
set "FASTMODE_FLAG="
set "INTERACTIVE_FLAG="
set "OLLAMA_MODEL="
set "AI_STRATEGY="
set "AI_DELAY="

:parse_args
if "%~1"=="" goto run_script
if /i "%~1"=="-backup" set "BACKUP_FLAG=-Backup"
if /i "%~1"=="-nobackup" set "BACKUP_FLAG="
if /i "%~1"=="-verbose" set "VERBOSE_FLAG=-ShowDetails"
if /i "%~1"=="-details" set "VERBOSE_FLAG=-ShowDetails"
if /i "%~1"=="-dryrun" set "DRYRUN_FLAG=-DryRun"
if /i "%~1"=="-skiponline" set "SKIPONLINE_FLAG=-SkipOnlineCheck"
if /i "%~1"=="-noai" set "NOAI_FLAG=-NoAI"
if /i "%~1"=="-useai" set "USEAI_FLAG=-UseAI"
if /i "%~1"=="-fast" set "FASTMODE_FLAG=-FastMode"
if /i "%~1"=="-fastmode" set "FASTMODE_FLAG=-FastMode"
if /i "%~1"=="-interactive" set "INTERACTIVE_FLAG=-Interactive"
if /i "%~1"=="-model" (
    set "OLLAMA_MODEL=-OllamaModel %~2"
    shift
)
if /i "%~1"=="-ai-strategy" (
    set "AI_STRATEGY=-AIStrategy %~2"
    shift
)
if /i "%~1"=="-ai-delay" (
    set "AI_DELAY=-AIDelay %~2"
    shift
)
shift
goto parse_args

:run_script
if not "!DROPPED_PATH!"=="" (
    echo Drag and drop detected: !DROPPED_PATH!
    echo Using path: %SOURCE_PATH%
    echo.
)

echo Running PowerShell migration script...
echo.

REM Run PowerShell script with appropriate parameters
REM Note: AI will auto-detect if neither -UseAI nor -NoAI is specified
powershell.exe -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -Path "%SOURCE_PATH%" %BACKUP_FLAG% %VERBOSE_FLAG% %DRYRUN_FLAG% %SKIPONLINE_FLAG% %USEAI_FLAG% %NOAI_FLAG% %FASTMODE_FLAG% %INTERACTIVE_FLAG% %OLLAMA_MODEL% %AI_STRATEGY% %AI_DELAY%

if errorlevel 1 (
    echo.
    echo ERROR: Migration script failed.
    pause
    exit /b 1
)

echo.
echo Migration complete!
pause

