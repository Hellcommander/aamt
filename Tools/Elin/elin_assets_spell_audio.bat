@echo off
setlocal
cd /d "%~dp0"
set "PY=D:\Python\Python314\python.exe"
if not exist "%PY%" set "PY=python"
set "PYTHONIOENCODING=utf-8"
if not exist "%~dp0Output\Logs" mkdir "%~dp0Output\Logs"
set "LOG=%~dp0Output\Logs\%~n0.log"
rem Spell and ability sounds: Stable Audio clips into the mod's Sound folder. Existing clips are skipped.
rem Goes through the toolkit's GPU guard.
echo Log: %LOG%
echo ^>^>^> elin_deploy_real_audio.py --skip-existing
echo ^>^>^> elin_deploy_real_audio.py --skip-existing >> "%LOG%"
"%PY%" -u elin_deploy_real_audio.py --skip-existing >> "%LOG%" 2>&1
if errorlevel 1 echo    FAILED, see the log
echo Finished. See %LOG%
if not defined ELIN_ASSETS_NOPAUSE pause
