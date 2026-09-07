@echo off
setlocal
cd /d "%~dp0"

REM CLI wrapper — use this for serve / ollama / compile (not QudLab.bat; that opens the GUI)
REM Phase 6: qudlab project set "Broodmother" | qudlab logs tail --kind threading
REM Lag sim: qudlab simulate --scenario lag-diagnose | lag-suite | npc-cta-no-spend --stress
set CLI=artifacts\bin\QudLab.Cli\Release\net8.0\QudLab.Cli.dll
if not exist "%CLI%" (
  echo Building Qud Lab CLI...
  dotnet build src\QudLab.Cli\QudLab.Cli.csproj -c Release -v q
  if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
  )
)

dotnet "%CLI%" %*
set EXIT=%ERRORLEVEL%
if %EXIT% neq 0 if "%~1"=="" pause
endlocal & exit /b %EXIT%
