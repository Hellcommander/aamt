@echo off
REM ============================================================
REM Transcendence TLisp/XML Checker - Easy Launcher
REM ============================================================
REM
REM INSTRUCTIONS:
REM   1. Edit the MOD_PATH variable below to point to your mod folder or XML file
REM   2. Save this file
REM   3. Double-click to run
REM
REM Examples:
REM   MOD_PATH=MyMod
REM   MOD_PATH=MyMod\MyMod.xml
REM   MOD_PATH=..\MyMod
REM ============================================================

REM ============================================================
REM CHANGE THIS PATH TO YOUR MOD FOLDER OR XML FILE
REM ============================================================
set MOD_PATH=ZZZ_CrossModCompatibility

REM ============================================================
REM OPTIONS:
REM ============================================================
REM Recurse into subdirectories (1=yes, 0=no)
set RECURSE=1

REM Severity filter: All, Error, Warning, Info
set SEVERITY=All

REM Skip specific check codes (comma-separated, leave empty for none)
REM Example: ENTITY_UNDEFINED,API_DEPRECATED
set SKIP_CODES=

REM Only run specific check codes (comma-separated, leave empty for all)
REM Example: TLISP_PARENS_UNBALANCED,TAG_MISMATCH
set ONLY_CODES=

REM Export report to file (leave empty for console only)
REM Example: report.csv or report.txt
set EXPORT_PATH=

REM Show detailed output with fix hints (1=yes, 0=no)
set DETAILED=0

REM ============================================================
REM DO NOT EDIT BELOW THIS LINE
REM ============================================================

set SCRIPT_DIR=%~dp0
set CHECKER_SCRIPT=%SCRIPT_DIR%TranscendenceTlispXmlChecker.ps1

REM Check if the checker script exists
if not exist "%CHECKER_SCRIPT%" (
    echo ERROR: Checker script not found at:
    echo   %CHECKER_SCRIPT%
    echo.
    echo Please make sure this batch file is in the Tools folder.
    pause
    exit /b 1
)

REM Build the PowerShell command
set PS_CMD=pwsh -NoProfile -ExecutionPolicy Bypass -File "%CHECKER_SCRIPT%" -NoGui -Path "%MOD_PATH%"

REM Add -Recurse if enabled
if "%RECURSE%"=="1" (
    set PS_CMD=%PS_CMD% -Recurse
)

REM Add severity filter
if not "%SEVERITY%"=="" (
    set PS_CMD=%PS_CMD% -Severity %SEVERITY%
)

REM Add skip codes
if not "%SKIP_CODES%"=="" (
    set PS_CMD=%PS_CMD% -SkipCodes "%SKIP_CODES%"
)

REM Add only codes
if not "%ONLY_CODES%"=="" (
    set PS_CMD=%PS_CMD% -OnlyCodes "%ONLY_CODES%"
)

REM Add export path
if not "%EXPORT_PATH%"=="" (
    set PS_CMD=%PS_CMD% -ExportPath "%EXPORT_PATH%"
)

REM Add detailed output
if "%DETAILED%"=="1" (
    set PS_CMD=%PS_CMD% -Detailed
)

REM Run the checker
%PS_CMD%

REM Check exit code
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================================
    echo Checker completed with errors (exit code: %ERRORLEVEL%)
    echo ============================================================
) else (
    echo.
    echo ============================================================
    echo Checker completed successfully
    echo ============================================================
)

echo.
pause

