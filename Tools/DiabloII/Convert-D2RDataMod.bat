@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Convert-D2RDataMod.ps1" %*
exit /b %ERRORLEVEL%
