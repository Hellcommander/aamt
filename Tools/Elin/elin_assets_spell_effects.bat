@echo off
setlocal
cd /d "%~dp0"
set "PY=D:\Python\Python314\python.exe"
if not exist "%PY%" set "PY=python"
set "PYTHONIOENCODING=utf-8"
if not exist "%~dp0Output\Logs" mkdir "%~dp0Output\Logs"
set "LOG=%~dp0Output\Logs\%~n0.log"
rem Spell effects: effect sprite strips into Texture, sound and effect ids stamped into the MagicPlus XML,
rem then the particle bundle packed with Unity 2021.3.45f2. No model is used; the Unity step needs Elin closed.
echo Log: %LOG%
echo ^>^>^> elin_deploy_real_effects.py
echo ^>^>^> elin_deploy_real_effects.py >> "%LOG%"
"%PY%" -u elin_deploy_real_effects.py >> "%LOG%" 2>&1
if errorlevel 1 echo    FAILED, see the log
echo ^>^>^> elin_unity_pack_asset.py
echo ^>^>^> elin_unity_pack_asset.py >> "%LOG%"
"%PY%" -u elin_unity_pack_asset.py >> "%LOG%" 2>&1
if errorlevel 1 echo    FAILED, see the log
echo Finished. See %LOG%
if not defined ELIN_ASSETS_NOPAUSE pause
