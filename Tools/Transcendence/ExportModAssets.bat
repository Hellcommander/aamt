@echo off
REM ============================================================
REM ExportModAssets.bat - Drag-and-Drop Wrapper
REM ============================================================
REM This batch file allows you to drag-and-drop folders
REM onto it to export assets from TranscendenceArt repository.

setlocal

REM Get the directory of the batch file
set "SCRIPT_DIR=%~dp0"

REM Check if a file/folder was dropped
if "%~1" neq "" (
    REM Pass the dropped path as the first argument to the PowerShell script
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%ExportModAssets.ps1" -SourceFolder "%~1"
) else (
    REM No folder dropped, run PowerShell script normally
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%ExportModAssets.ps1"
)

REM Keep window open on error
if %ERRORLEVEL% neq 0 pause

endlocal

