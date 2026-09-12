@echo off
REM Direct launch of the Obsolete-API Migrator GUI (x64 / win-x64).
REM Always run an incremental build so source updates cannot silently launch a stale
REM ApiMigrator.Core.dll from a previous checkout.
setlocal
set SCRIPT_DIR=%~dp0
set EXE=%SCRIPT_DIR%src\ApiMigratorGui\bin\Release\net8.0-windows\win-x64\ApiMigratorGui.exe

echo Building current ApiMigrator GUI (incremental Release win-x64)...
pushd "%SCRIPT_DIR%src\ApiMigratorGui"
dotnet build -c Release -r win-x64
if errorlevel 1 (
  echo.
  echo BUILD FAILED.
  echo If you see "file is being used by another process" / MSB3026, a running
  echo ApiMigrator or Update-ObsoleteApis.ps1 session may have the output locked.
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
