@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Convert-D2RLegacyMonster.ps1" %*
exit /b %ERRORLEVEL%
