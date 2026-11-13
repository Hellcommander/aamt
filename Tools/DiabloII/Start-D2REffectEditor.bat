@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-D2REffectEditor.ps1" %*
exit /b %ERRORLEVEL%
