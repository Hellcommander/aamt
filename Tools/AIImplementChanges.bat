@echo off
REM ============================================================================
REM AIImplementChanges.bat
REM ============================================================================
REM AI-Powered Code Change Implementation Tool
REM Uses AI to analyze code and automatically implement suggested changes
REM Supports drag and drop: drag files/folders onto this batch file
REM ============================================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   AI-Powered Code Change Implementation Tool
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
set "PS_SCRIPT=%SCRIPT_DIR%AIImplementChanges.ps1"

REM Check if the PowerShell script exists
if not exist "%PS_SCRIPT%" (
    echo ERROR: PowerShell script not found: %PS_SCRIPT%
    echo Please ensure AIImplementChanges.ps1 is in the same directory.
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
set "INTERACTIVE_FLAG="
set "FOCUS_FLAG="
set "MODEL_FLAG="

:parse_args
if "%~1"=="" goto run_script
if /i "%~1"=="-backup" set "BACKUP_FLAG=-Backup"
if /i "%~1"=="-nobackup" set "BACKUP_FLAG="
if /i "%~1"=="-verbose" set "VERBOSE_FLAG=-ShowDetails"
if /i "%~1"=="-details" set "VERBOSE_FLAG=-ShowDetails"
if /i "%~1"=="-dryrun" set "DRYRUN_FLAG=-DryRun"
if /i "%~1"=="-interactive" set "INTERACTIVE_FLAG=-Interactive"
if /i "%~1"=="-focus" (
    set "FOCUS_FLAG=-Focus %~2"
    shift
)
if /i "%~1"=="-model" (
    set "MODEL_FLAG=-OllamaModel %~2"
    shift
)
shift
goto parse_args

:run_script
if not "!DROPPED_PATH!"=="" (
    echo Drag and drop detected: !DROPPED_PATH!
    echo Using path: %SOURCE_PATH%
    if not "!LOG_FILE!"=="" (
        echo Log file detected: !LOG_FILE!
        echo Will implement changes from log file one by one.
    )
    echo.
)

echo Running AI implementation script...
echo.

REM Build command with log file if present
set "LOG_FILE_FLAG="
if not "!LOG_FILE!"=="" set "LOG_FILE_FLAG=-LogFile "!LOG_FILE!""

REM Run PowerShell script with appropriate parameters
powershell.exe -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -Path "%SOURCE_PATH%" %BACKUP_FLAG% %VERBOSE_FLAG% %DRYRUN_FLAG% %INTERACTIVE_FLAG% %FOCUS_FLAG% %MODEL_FLAG% %LOG_FILE_FLAG%

if errorlevel 1 (
    echo.
    echo ERROR: AI implementation script failed.
    pause
    exit /b 1
)

echo.
echo AI implementation complete!
pause

