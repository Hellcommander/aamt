@echo off
REM ============================================================
REM AssetMakerAI.bat - Drag-and-Drop Wrapper
REM ============================================================
REM This batch file allows you to use the AI-powered asset maker
REM for Transcendence mods using local Ollama models.

setlocal

REM Get the directory of the batch file
set "SCRIPT_DIR=%~dp0"

REM Run the PowerShell script
pwsh -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%AssetMakerAI.ps1" %*

REM Keep window open on error
if %ERRORLEVEL% neq 0 pause

endlocal

