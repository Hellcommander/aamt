@echo off
rem Drop .model or .skeleton files here: each is queued for a Noesis export check (ToolJobs.py). Nothing runs yet.
for %%F in (%*) do python "%~dp0..\ToolJobs.py" add noesis-export "%%~F" --to obj,smd
echo.
echo Start "Run tool jobs.bat" to run them.
pause
