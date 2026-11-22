@echo off
rem Runs the jobs queued for the downloaded community tools (ToolJobs.py): shows the command lines, asks, runs them.
python "%~dp0..\ToolJobs.py" run
echo.
pause
