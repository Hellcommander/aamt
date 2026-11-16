@echo off
setlocal
cd /d "%~dp0"
set "PY=D:\Python\Python314\python.exe"
if not exist "%PY%" set "PY=python"
set "LIST=E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator\Paperdolls\priority_ids.txt"
set "LOG=%~dp0Output\CreaturePaperdolls\%~n0.log"
rem Real motion (UniRig + Wan video + CoTracker) for creatures that already have a real body, 15-20 minutes each.
rem Finished creatures are skipped. Pass creature ids to do only those:  creature_paperdolls_motion.bat silverwolf
if "%~1"=="" (set SEL=--list "%LIST%") else (set SEL=--id %~1)
echo Log: %LOG%
"%PY%" -u elin_creature_paperdolls.py motion %SEL% >> "%LOG%" 2>&1
echo Finished with exit code %ERRORLEVEL%. See %LOG%
pause
