@echo off
setlocal
cd /d "%~dp0"
dotnet build QudLab.sln -c Release -v q
if errorlevel 1 exit /b 1
set CLI=artifacts\bin\QudLab.Cli\Release\net8.0\QudLab.Cli.dll
dotnet "%CLI%" sync-refs
echo.
echo Open QudLab.code-workspace (or Workspace\QudLab.ModWorkspace.csproj) in Cursor.
endlocal
