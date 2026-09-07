@echo off
REM ============================================================
REM QudTileAIGenerator.bat - Launch GUI Control Room
REM ============================================================
REM Launches the real-time GUI for Qud tile generation with AI.

setlocal

REM Get the directory of the batch file
set "SCRIPT_DIR=%~dp0"

REM Launch PowerShell GUI
pwsh -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%QudTileAIGenerator.ps1" %*

REM Keep window open on error
if %ERRORLEVEL% neq 0 pause

endlocal

