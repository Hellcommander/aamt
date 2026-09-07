@echo off
setlocal
cd /d "%~dp0"
REM Rebuild arzedit.exe from arzedit\arzedit-master into bin\
dotnet build "%~dp0arzedit\toolset\arzedit.csproj" -c Release
if errorlevel 1 (
  echo Build failed.
  exit /b 1
)
echo.
echo Installed: %~dp0bin\arzedit.exe
"%~dp0bin\arzedit.exe"
REM help text exits 1 — treat compile success as success
exit /b 0
