@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Qud Lab SGLang frontend
echo SGLang Model Gateway: http://127.0.0.1:30000/v1
echo Backend worker:      vLLM http://127.0.0.1:8000
echo This is sglang_router (https://github.com/sgl-project/sglang), not a raw pipe.
echo Start the GPU backend shortcut first. Close this window or Ctrl+C to stop.
echo.

call qudlab-cli.bat sglang serve --remote --model "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"
set EXIT=%ERRORLEVEL%
echo.
if %EXIT% neq 0 (
  echo SGLang frontend exited with error %EXIT%.
) else (
  echo SGLang frontend stopped.
)
pause
endlocal & exit /b %EXIT%
