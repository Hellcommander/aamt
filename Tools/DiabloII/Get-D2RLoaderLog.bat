@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Get-D2RLoaderLog.ps1" %*
exit /b %ERRORLEVEL%
