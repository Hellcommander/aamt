@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: Run-GdModMerger.bat OutName Mod1 [Mod2 ...]
  echo   Merge-rule priority decides order; result is patched for the latest
  echo   game/DLC with class UI + Ollama combo names. See README for options.
  echo Example: Run-GdModMerger.bat MergedMod grimarillion Rebirth
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
rem %%* ignores shift, so collect the remaining (quoted) mod names by hand
set MODS=
:collect
if "%~1"=="" goto run
set MODS=!MODS! "%~1"
shift
goto collect
:run
python -u "%~dp0merge_mod_databases.py" --out "%OUT%" --latest --ollama --mods !MODS!
set RC=%ERRORLEVEL%
echo.
pause
exit /b %RC%
