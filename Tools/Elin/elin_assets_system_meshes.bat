@echo off
setlocal
cd /d "%~dp0"
set "PY=D:\Python\Python314\python.exe"
if not exist "%PY%" set "PY=python"
set "PYTHONIOENCODING=utf-8"
if not exist "%~dp0Output\Logs" mkdir "%~dp0Output\Logs"
set "LOG=%~dp0Output\Logs\%~n0.log"
rem 3D hero models of the magic systems: TRELLIS mesh for every system that has none, then installed as FBX.
rem Goes through the toolkit's GPU guard.
echo Log: %LOG%
echo ^>^>^> elin_trellis_unity.py trellis --all
echo ^>^>^> elin_trellis_unity.py trellis --all >> "%LOG%"
"%PY%" -u elin_trellis_unity.py trellis --all >> "%LOG%" 2>&1
if errorlevel 1 echo    FAILED, see the log
echo ^>^>^> elin_trellis_unity.py deploy-elin --all
echo ^>^>^> elin_trellis_unity.py deploy-elin --all >> "%LOG%"
"%PY%" -u elin_trellis_unity.py deploy-elin --all >> "%LOG%" 2>&1
if errorlevel 1 echo    FAILED, see the log
echo Finished. See %LOG%
if not defined ELIN_ASSETS_NOPAUSE pause
