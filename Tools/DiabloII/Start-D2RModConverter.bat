@echo off
rem Opens the D2R mod converter (data mods into D2RMM mods, and updates of converted mods).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-D2RModConverter.ps1" %*
exit /b %ERRORLEVEL%
