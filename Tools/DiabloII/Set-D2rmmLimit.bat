@echo off
rem Defaults to the game folder when called without arguments.
if "%~1"=="" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Set-D2rmmLimit.ps1" -Root "D:\games\Diablo II Resurrected"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Set-D2rmmLimit.ps1" %*
)
set rc=%ERRORLEVEL%
if "%~1"=="" pause
exit /b %rc%
