@echo off
REM ============================================================
REM AssetGeneratorControlRoom.bat - Launch Universal Control Room
REM ============================================================
REM Launches the real-time GUI for all asset generation types.

setlocal

REM Get the directory of the batch file
set "SCRIPT_DIR=%~dp0"

REM Launch PowerShell GUI (STA mode required for WPF)
powershell -STA -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%AssetGeneratorControlRoom.ps1" %*

REM Keep window open on error
if %ERRORLEVEL% neq 0 pause

endlocal

