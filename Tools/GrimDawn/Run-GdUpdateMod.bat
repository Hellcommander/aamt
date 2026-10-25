@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: Run-GdUpdateMod.bat ModName [OutName]
  echo   Updates a mod for the latest Grim Dawn patch + DLC: all classes selectable,
  echo   class UI expanded, combo names via Ollama. Output: mods\OutName ^(default ModName_Latest^)
  echo Example: Run-GdUpdateMod.bat dom
  pause
  exit /b 1
)
set "OUT=%~2"
if "%OUT%"=="" set "OUT=%~1_Latest"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-GdFoACompat.ps1" -Mod "%~1" -Out "%OUT%" -Latest -Ollama
echo.
pause
exit /b %ERRORLEVEL%
