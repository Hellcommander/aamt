@echo off
setlocal
cd /d "%~dp0"

REM Desktop GUI launcher (do not name a sibling qudlab.bat — Windows paths are case-insensitive)
set GUI_EXE=artifacts\bin\QudLab.Gui\Release\net8.0-windows\QudLab.Gui.exe
set GUI_DLL=artifacts\bin\QudLab.Gui\Release\net8.0-windows\QudLab.Gui.dll

if not exist "%GUI_EXE%" if not exist "%GUI_DLL%" (
  echo Building Qud Lab GUI...
  dotnet build src\QudLab.Gui\QudLab.Gui.csproj -c Release -v q
  if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
  )
)

if exist "%GUI_EXE%" (
  start "Qud Lab" "%GUI_EXE%"
  exit /b 0
)

dotnet "%GUI_DLL%"
if errorlevel 1 (
  echo Qud Lab GUI exited with an error.
  pause
  exit /b 1
)
endlocal
