@echo off
REM Stop SD3.5 API server on port 1338 (free VRAM for Ollama).
setlocal
echo Stopping SD3.5 listeners on port 1338...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Stop-SdServer.ps1"
echo Done.
if /I not "%~1"=="nopause" pause
endlocal
exit /b 0
