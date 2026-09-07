@echo off
REM Pin ApiMigrator's active obsolete dump + rewrite rules to a by-version profile
REM (public vs lang-experimental) without changing the installed game.
REM Prefers the prebuilt CLI exe; falls back to `dotnet run`.
setlocal
set SCRIPT_DIR=%~dp0
if not defined DOTNET_ROOT if exist "C:\Program Files\dotnet\dotnet.exe" set "DOTNET_ROOT=C:\Program Files\dotnet"
if defined DOTNET_ROOT set "PATH=%DOTNET_ROOT%;%PATH%"

set EXE=%SCRIPT_DIR%src\ApiMigrator.Cli\bin\Release\net8.0\win-x64\ApiMigrator.Cli.exe
set EXE2=%SCRIPT_DIR%src\ApiMigrator.Cli\bin\Release\net8.0\ApiMigrator.Cli.exe

if "%~1"=="" (
  call :run switch-api --list
  echo.
  echo Usage: Switch-Api.bat public ^| lang ^| live ^| ^<FileVersion^>
  echo   public / stable     pin dump+rules to the public/stable profile
  echo   lang / beta         pin dump+rules to lang-experimental
  echo   live / auto         clear pin and follow the installed game
  echo.
  echo GUI: Launch-Gui.bat — API dump profile bar + Switch
  echo Do not share data\by-version\active-override.json; recipients pick their own profile.
  pause
  exit /b 0
)

call :run switch-api %*
exit /b %ERRORLEVEL%

:run
if exist "%EXE%" (
  "%EXE%" %*
  exit /b %ERRORLEVEL%
)
if exist "%EXE2%" (
  "%EXE2%" %*
  exit /b %ERRORLEVEL%
)
echo Prebuilt CLI not found. Running via dotnet...
pushd "%SCRIPT_DIR%src\ApiMigrator.Cli"
dotnet run -c Release -- %*
set ERR=%ERRORLEVEL%
popd
exit /b %ERR%
