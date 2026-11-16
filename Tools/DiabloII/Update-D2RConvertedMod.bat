@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Update-D2RConvertedMod.ps1" %*
exit /b %ERRORLEVEL%
