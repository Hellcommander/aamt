@echo off
REM ============================================================================
REM Apply-ManualReviewFixes.bat
REM ============================================================================
REM Batch wrapper for Apply-ManualReviewFixes.ps1 - Best AI for manual review fixes
REM ============================================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   Manual Review Fix Application Tool (Best AI)
echo ============================================================
echo.

REM Check if PowerShell is available
where powershell >nul 2>&1
if errorlevel 1 (
    echo ERROR: PowerShell is not available on this system.
    pause
    exit /b 1
)

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%Apply-ManualReviewFixes.ps1"

REM Check if the PowerShell script exists
if not exist "%PS_SCRIPT%" (
    echo ERROR: PowerShell script not found: %PS_SCRIPT%
    pause
    exit /b 1
)

REM Check if files/folders were dropped (drag and drop)
set "SOURCE_PATH=."
if not "%~1"=="" (
    if exist "%~1" (
        if exist "%~1\" (
            set "SOURCE_PATH=%~1"
        ) else (
            for %%F in ("%~1") do set "SOURCE_PATH=%%~dpF"
            set "SOURCE_PATH=!SOURCE_PATH:~0,-1!"
        )
    ) else (
        set "SOURCE_PATH=%~1"
    )
)

REM Check for flags
set "DRYRUN_FLAG="
set "VERBOSE_FLAG="
set "MODEL_FLAG="
set "REVIEW_FILE="

:parse_args
if "%~1"=="" goto run_script
if /i "%~1"=="-dryrun" set "DRYRUN_FLAG=-DryRun"
if /i "%~1"=="-verbose" set "VERBOSE_FLAG=-ShowDetails"
if /i "%~1"=="-model" (
    set "MODEL_FLAG=-OllamaModel %~2"
    shift
)
if /i "%~1"=="-file" (
    set "REVIEW_FILE=-ManualReviewFile %~2"
    shift
)
shift
goto parse_args

:run_script
echo Running PowerShell script...
echo.

REM Run PowerShell script
powershell.exe -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -Path "%SOURCE_PATH%" %DRYRUN_FLAG% %VERBOSE_FLAG% %MODEL_FLAG% %REVIEW_FILE%

if errorlevel 1 (
    echo.
    echo ERROR: Script failed.
    pause
    exit /b 1
)

echo.
echo Processing complete!
pause

