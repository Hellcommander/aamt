@echo off
setlocal
cd /d "%~dp0"

REM Double-click / no args → open the Studio. Extra args still go to the CLI.
if "%~1"=="" (
  python "%~dp0s2_skill_cli.py" editor
) else (
  python "%~dp0s2_skill_cli.py" %*
)

set ERR=%ERRORLEVEL%
if not %ERR%==0 (
  echo.
  echo SkillCreator exited with code %ERR%.
  pause
)
exit /b %ERR%
