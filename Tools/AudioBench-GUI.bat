@echo off
REM Audio Bench: programmatic mixing, blending and sound shaping with a control-panel page in your browser.
REM Starts the local server (127.0.0.1:8765) and opens the page. Ctrl+C in this window stops it.
setlocal
set "TOOLS=%~dp0"
set "PY="
if exist "%TOOLS%TranscendenceTools.ini" (
  for /f "usebackq tokens=1,* delims==" %%A in (`findstr /i /b "PythonPath" "%TOOLS%TranscendenceTools.ini"`) do set "PY=%%B"
)
if not defined PY if exist "E:\tools\miniconda3\python.exe" set "PY=E:\tools\miniconda3\python.exe"
if not defined PY set "PY=python"
"%PY%" "%TOOLS%Shared\audio_bench_server.py" --open %*
exit /b %ERRORLEVEL%
