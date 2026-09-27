@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Qud Lab vLLM GPU backend
echo GPU backend: vLLM in WSL on http://127.0.0.1:8000/v1
echo Model: Qwen/Qwen2.5-Coder-7B-Instruct-AWQ  (64k ctx, CPU swap, ~9GB for GPU + Cursor)
echo Close this window or Ctrl+C to stop.
echo.

call qudlab-cli.bat vllm serve --model "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ" %*
set EXIT=%ERRORLEVEL%
echo.
if %EXIT% neq 0 (
  echo vLLM exited with error %EXIT%.
  echo If the model id looks like QwenQwen... the shortcut ate the slash; this launcher quotes it.
) else (
  echo vLLM stopped.
)
pause
endlocal & exit /b %EXIT%
