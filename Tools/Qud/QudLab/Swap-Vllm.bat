@echo off
setlocal EnableExtensions
cd /d "%~dp0"
REM Optional CLI: list | status | stop | swap
REM   Swap-Vllm.bat list
REM   Swap-Vllm.bat status
REM   Swap-Vllm.bat swap Qwen/Qwen2.5-Coder-7B-Instruct-AWQ
REM   Swap-Vllm.bat swap Qwen/Qwen2.5-3B-Instruct --frontend

set ACTION=%~1
if "%ACTION%"=="" set ACTION=status

if /I "%ACTION%"=="list" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Swap-VllmModel.ps1" list
  exit /b %ERRORLEVEL%
)
if /I "%ACTION%"=="status" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Swap-VllmModel.ps1" status
  exit /b %ERRORLEVEL%
)
if /I "%ACTION%"=="stop" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Swap-VllmModel.ps1" stop
  exit /b %ERRORLEVEL%
)
if /I "%ACTION%"=="swap" (
  set MODEL=%~2
  if "%MODEL%"=="" (
    echo Usage: Swap-Vllm.bat swap org/name [--frontend]
    exit /b 2
  )
  set FE=
  if /I "%~3"=="--frontend" set FE=-RestartFrontend
  if /I "%~3"=="-RestartFrontend" set FE=-RestartFrontend
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Swap-VllmModel.ps1" swap -Model "%MODEL%" %FE%
  exit /b %ERRORLEVEL%
)

echo Usage: Swap-Vllm.bat list^|status^|stop^|swap org/name [--frontend]
exit /b 2
