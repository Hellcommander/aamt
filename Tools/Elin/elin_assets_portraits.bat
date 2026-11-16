@echo off
setlocal
cd /d "%~dp0"
set "PY=D:\Python\Python314\python.exe"
if not exist "%PY%" set "PY=python"
set "PYTHONIOENCODING=utf-8"
if not exist "%~dp0Output\Logs" mkdir "%~dp0Output\Logs"
set "LOG=%~dp0Output\Logs\%~n0.log"
rem Patron portraits for the magic systems that have none (SD3.5), cut to 240x320 into the mod's Portrait folder.
rem Existing portraits are kept. Goes through the toolkit's GPU guard; about a minute per portrait once the server is up.
echo Log: %LOG%
echo ^>^>^> elin_generate_portraits.py
echo ^>^>^> elin_generate_portraits.py >> "%LOG%"
"%PY%" -u elin_generate_portraits.py >> "%LOG%" 2>&1
if errorlevel 1 echo    FAILED, see the log
echo Finished. See %LOG%
if not defined ELIN_ASSETS_NOPAUSE pause
