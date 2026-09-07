@echo off
REM Transcendence API Switcher GUI
set SCRIPT_DIR=%~dp0
set GUI=%SCRIPT_DIR%TranscendenceApiSwitcherGUI.ps1
set CLI=%SCRIPT_DIR%TranscendenceApiSwitcher.ps1

if not exist "%GUI%" (
  echo ERROR: Missing %GUI%
  pause
  exit /b 1
)

REM No args / -Gui → GUI. Drag-drop folder or CLI flags → CLI.
if "%~1"=="" (
  start "" pwsh -NoProfile -ExecutionPolicy Bypass -STA -File "%GUI%"
  exit /b 0
)
if /I "%~1"=="-Gui" (
  start "" pwsh -NoProfile -ExecutionPolicy Bypass -STA -File "%GUI%"
  exit /b 0
)
if /I "%~1"=="/gui" (
  start "" pwsh -NoProfile -ExecutionPolicy Bypass -STA -File "%GUI%"
  exit /b 0
)

if exist "%~1\" (
  pwsh -NoProfile -ExecutionPolicy Bypass -File "%CLI%" -ApiFolder "%~1" %2 %3 %4 %5 %6 %7 %8 %9
) else (
  pwsh -NoProfile -ExecutionPolicy Bypass -File "%CLI%" %*
)

if %ERRORLEVEL% NEQ 0 (
  echo.
  echo Exit code: %ERRORLEVEL%
  pause
)
exit /b %ERRORLEVEL%
