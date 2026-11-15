@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Update-D2RPlugins.ps1" %*
exit /b %ERRORLEVEL%
