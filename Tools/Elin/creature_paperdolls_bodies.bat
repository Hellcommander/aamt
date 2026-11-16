@echo off
setlocal
cd /d "%~dp0"
set "PY=D:\Python\Python314\python.exe"
if not exist "%PY%" set "PY=python"
set "LIST=E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator\Paperdolls\priority_ids.txt"
set "LOG=%~dp0Output\CreaturePaperdolls\%~n0.log"
rem Real bodies (Kontext redraw + TRELLIS) for the priority creatures, about 7 minutes each.
rem Finished creatures are skipped. Pass creature ids to do only those:  creature_paperdolls_bodies.bat dragon,harpy
rem Every model job goes through the toolkit's GPU guard; if another job holds the card this waits for it.
if "%~1"=="" (set SEL=--list "%LIST%") else (set SEL=--id %~1)
echo Log: %LOG%
"%PY%" -u elin_creature_paperdolls.py full %SEL% >> "%LOG%" 2>&1
echo Finished with exit code %ERRORLEVEL%. See %LOG%
pause
