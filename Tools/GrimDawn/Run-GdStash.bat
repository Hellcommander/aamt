@echo off
setlocal
set "GDSTASH=D:\games\Steam\steamapps\common\Grim Dawn\GD Stash"
if not exist "%GDSTASH%\gdstash.bat" (
  echo GD Stash not found:
  echo   %GDSTASH%
  pause
  exit /b 1
)
cd /d "%GDSTASH%"
call gdstash.bat
exit /b %ERRORLEVEL%
