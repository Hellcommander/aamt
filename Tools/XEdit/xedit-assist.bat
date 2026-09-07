@echo off
setlocal
set ROOT=%~dp0
set EXE=%ROOT%XEdit.Assist\bin\Release\net8.0\xedit-assist.exe
if not exist "%EXE%" set EXE=%ROOT%XEdit.Assist\bin\Debug\net8.0\xedit-assist.exe
if not exist "%EXE%" (
  echo Building xedit-assist...
  dotnet build "%ROOT%XEdit.Clr.sln" -c Release -v q
  set EXE=%ROOT%XEdit.Assist\bin\Release\net8.0\xedit-assist.exe
)
"%EXE%" %*
