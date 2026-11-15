@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Edit-D2REffect.ps1" %*
exit /b %ERRORLEVEL%
