@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: Run-GdFoACompat.bat ModName
  echo Example: Run-GdFoACompat.bat grimarillion
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-GdFoACompat.ps1" -Mod "%~1" -FullCompat
echo.
pause
exit /b %ERRORLEVEL%
