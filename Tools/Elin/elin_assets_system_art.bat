@echo off
setlocal
cd /d "%~dp0"
set "PY=D:\Python\Python314\python.exe"
if not exist "%PY%" set "PY=python"
set "PYTHONIOENCODING=utf-8"
if not exist "%~dp0Output\Logs" mkdir "%~dp0Output\Logs"
set "LOG=%~dp0Output\Logs\%~n0.log"
rem System icons, UI chrome, Element sheets and the 32 patron portraits. No model is used.
rem Only ADDS files: anything already in the mod is left alone (elin_keep.py).
rem To replace existing files too, run with FORCE as the argument:  elin_assets_system_art.bat FORCE
rem Replaced files are first copied to Output\ModBackup\<time>.
if /I "%~1"=="FORCE" set AAMT_ELIN_FORCE=1
if /I "%~1"=="PREVIEW" set AAMT_ELIN_DRY_RUN=1
echo Log: %LOG%
echo ^>^>^> elin_deploy_real_assets.py
echo ^>^>^> elin_deploy_real_assets.py >> "%LOG%"
"%PY%" -u elin_deploy_real_assets.py >> "%LOG%" 2>&1
if errorlevel 1 echo    FAILED, see the log
echo ^>^>^> elin_deploy_portraits.py
echo ^>^>^> elin_deploy_portraits.py >> "%LOG%"
"%PY%" -u elin_deploy_portraits.py >> "%LOG%" 2>&1
if errorlevel 1 echo    FAILED, see the log
echo ^>^>^> elin_trellis_unity.py deploy-ui
echo ^>^>^> elin_trellis_unity.py deploy-ui >> "%LOG%"
"%PY%" -u elin_trellis_unity.py deploy-ui >> "%LOG%" 2>&1
if errorlevel 1 echo    FAILED, see the log
echo ^>^>^> elin_trellis_unity.py deploy-icons
echo ^>^>^> elin_trellis_unity.py deploy-icons >> "%LOG%"
"%PY%" -u elin_trellis_unity.py deploy-icons >> "%LOG%" 2>&1
if errorlevel 1 echo    FAILED, see the log
echo Finished. See %LOG%
if not defined ELIN_ASSETS_NOPAUSE pause
