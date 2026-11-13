@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0New-RecoloredEffect.ps1" %*
exit /b %ERRORLEVEL%
