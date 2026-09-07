@echo off
setlocal
cd /d "%~dp0"
REM Build .arz for Survival DLC + Campaign Custom Game via arzedit
if not exist "%~dp0bin\arzedit.exe" (
  echo arzedit missing — building from source...
  call "%~dp0Build-Arzedit.bat"
  if errorlevel 1 exit /b 1
)
python -u "%~dp0build_mod_arz.py" %*
echo.
pause
exit /b %ERRORLEVEL%
