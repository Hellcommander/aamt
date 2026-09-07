@echo off
setlocal
set "TOOLS=%~dp0"
set "PY="
if exist "%TOOLS%TranscendenceTools.ini" (
  for /f "usebackq tokens=1,* delims==" %%A in (`findstr /i /b "PythonPath" "%TOOLS%TranscendenceTools.ini"`) do set "PY=%%B"
)
if not defined PY if exist "E:\tools\miniconda3\python.exe" set "PY=E:\tools\miniconda3\python.exe"
if not defined PY set "PY=python"
"%PY%" "%TOOLS%Shared\pixelorama_client.py" %*
exit /b %ERRORLEVEL%
