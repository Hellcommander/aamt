@echo off
REM ============================================================
REM CompileApiFolder.bat - Drag-and-Drop Wrapper
REM ============================================================
REM This batch file allows you to drag-and-drop API folders
REM onto it to automatically compile them.
REM
REM Usage:
REM   1. Drag a TranscendenceDev-integration-API## folder onto this file
REM   2. Or run with path as argument
REM ============================================================

setlocal EnableDelayedExpansion

REM Get the directory of the batch file
set "SCRIPT_DIR=%~dp0"

echo.
echo ============================================================
echo   Transcendence API Folder Compiler
echo ============================================================
echo.

REM Check if PowerShell is available
where pwsh >nul 2>&1
if %ERRORLEVEL% neq 0 (
    where powershell >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo ERROR: PowerShell not found in PATH
        echo Please install PowerShell or add it to your PATH
        pause
        exit /b 1
    )
    set "PWSH_CMD=powershell"
) else (
    set "PWSH_CMD=pwsh"
)

REM Check if PowerShell script exists
if not exist "%SCRIPT_DIR%CompileApiFolder.ps1" (
    echo ERROR: PowerShell script not found: %SCRIPT_DIR%CompileApiFolder.ps1
    pause
    exit /b 1
)

REM Check if a file/folder was dropped
if "%~1" neq "" (
    echo Compiling API folder: %~1
    echo.
    REM Pass the dropped path as the first argument to the PowerShell script
    %PWSH_CMD% -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%CompileApiFolder.ps1" "%~1"
    set "EXIT_CODE=%ERRORLEVEL%"
) else (
    REM No folder dropped, run PowerShell script normally (will show usage)
    %PWSH_CMD% -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%CompileApiFolder.ps1"
    set "EXIT_CODE=%ERRORLEVEL%"
)

echo.
echo ============================================================
if !EXIT_CODE! equ 0 (
    echo   Compilation Complete!
    echo ============================================================
) else (
    echo   Compilation Failed (Exit Code: !EXIT_CODE!)
    echo ============================================================
    echo.
    echo Check the error messages above for details.
    echo.
    pause
)

endlocal
exit /b %EXIT_CODE%

