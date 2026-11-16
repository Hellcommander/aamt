@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Sort-D2RMods.ps1" %*
if errorlevel 1 pause
exit /b %ERRORLEVEL%
