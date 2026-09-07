@echo off
REM ============================================================
REM GenerateApiRules.bat - Drag-and-Drop Wrapper
REM ============================================================
REM This batch file allows you to drag-and-drop API folders
REM onto it to automatically generate API rules.
REM
REM Usage:
REM   1. Drag a TranscendenceDev-integration-API## folder onto this file
REM   2. Or double-click to use default API version
REM ============================================================

setlocal

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"

REM Check if a file/folder was dropped on this batch file
if "%~1"=="" (
    REM No argument - run with default settings
    echo ============================================================
    echo   Generate API Rules (Default Mode)
    echo ============================================================
    echo.
    echo No folder dropped. Using default API version...
    echo.
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%GenerateApiRules.ps1"
) else (
    REM File/folder was dropped - pass it to PowerShell script
    echo ============================================================
    echo   Generate API Rules (Drag-and-Drop Mode)
    echo ============================================================
    echo.
    echo Dropped item: %~1
    echo.
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%GenerateApiRules.ps1" "%~1"
)

REM Keep window open if there was an error
if errorlevel 1 (
    echo.
    echo ============================================================
    echo   ERROR: Script failed
    echo ============================================================
    echo.
    pause
)

endlocal

