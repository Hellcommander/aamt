@echo off
REM Direct launch of the Obsolete-API Migrator GUI (x64 / win-x64).
REM Prefers the prebuilt exe so a locked ApiMigrator.Core.dll (PS1 Add-Type) does not
REM spam MSB3026 rebuild errors and prevent the window from opening.
setlocal
set SCRIPT_DIR=%~dp0
set EXE=%SCRIPT_DIR%src\ApiMigratorGui\bin\Release\net8.0-windows\win-x64\ApiMigratorGui.exe

if exist "%EXE%" (
  start "" "%EXE%"
  exit /b 0
)

echo Prebuilt GUI not found. Building Release win-x64...
pushd "%SCRIPT_DIR%src\ApiMigratorGui"
dotnet build -c Release -r win-x64
if errorlevel 1 (
  echo.
  echo BUILD FAILED.
  echo If you see "file is being used by another process" / MSB3026, a PowerShell
  echo Update-ObsoleteApis.ps1 session still has ApiMigrator.Core.dll loaded via Add-Type.
  echo Close that migrate window/process, then run this bat again.
  pause
  popd
  exit /b 1
)
popd

if exist "%EXE%" (
  start "" "%EXE%"
  exit /b 0
)

echo Built but exe missing:
echo   %EXE%
pause
exit /b 1
