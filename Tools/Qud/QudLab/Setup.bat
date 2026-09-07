@echo off
setlocal
cd /d "%~dp0"
dotnet build QudLab.sln -c Release -v q
if errorlevel 1 exit /b 1
set CLI=artifacts\bin\QudLab.Cli\Release\net8.0\QudLab.Cli.dll
dotnet "%CLI%" setup
if errorlevel 1 exit /b 1
echo.
echo Open QudLab.bat for the desktop GUI, or QudLab.code-workspace in Cursor.
endlocal
