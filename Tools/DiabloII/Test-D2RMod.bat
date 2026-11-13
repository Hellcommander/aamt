@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Test-D2RMod.ps1" %*
exit /b %ERRORLEVEL%
