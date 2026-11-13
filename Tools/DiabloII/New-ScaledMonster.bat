@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0New-ScaledMonster.ps1" %*
exit /b %ERRORLEVEL%
