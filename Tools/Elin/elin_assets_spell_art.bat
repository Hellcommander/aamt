@echo off
setlocal
cd /d "%~dp0"
set "PY=D:\Python\Python314\python.exe"
if not exist "%PY%" set "PY=python"
set "PYTHONIOENCODING=utf-8"
if not exist "%~dp0Output\Logs" mkdir "%~dp0Output\Logs"
set "LOG=%~dp0Output\Logs\%~n0.log"
rem Spell icons and concept art: one unique picture per spell (Stable Diffusion), 48x48 icons into the mod's Texture folder.
rem Existing art is kept; add --force inside to redo. Goes through the toolkit's GPU guard.
echo Log: %LOG%
echo ^>^>^> elin_unique_spell_art.py all
echo ^>^>^> elin_unique_spell_art.py all >> "%LOG%"
"%PY%" -u elin_unique_spell_art.py all >> "%LOG%" 2>&1
if errorlevel 1 echo    FAILED, see the log
echo Finished. See %LOG%
if not defined ELIN_ASSETS_NOPAUSE pause
