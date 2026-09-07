@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: Run-GdModMerger.bat OutName Mod1 [Mod2 ...]
  echo Example: Run-GdModMerger.bat MergedMod grimarillion survivalmode
  pause
  exit /b 1
)
set "OUT=%~1"
shift
if "%~1"=="" (
  echo Need at least one mod after OutName.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-GdModMerger.ps1" -Out "%OUT%" -Mods %*
echo.
pause
exit /b %ERRORLEVEL%
