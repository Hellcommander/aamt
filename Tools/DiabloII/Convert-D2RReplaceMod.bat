@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Convert-D2RReplaceMod.ps1" %*
if errorlevel 1 pause
exit /b %ERRORLEVEL%
