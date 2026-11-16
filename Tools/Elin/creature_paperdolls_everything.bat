@echo off
setlocal
cd /d "%~dp0"
set "PY=D:\Python\Python314\python.exe"
if not exist "%PY%" set "PY=python"
set "LIST=E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator\Paperdolls\priority_ids.txt"
set "LOG=%~dp0Output\CreaturePaperdolls\%~n0.log"
rem Everything, in order: bodies and motion for the priority creatures, then for every other creature tile.
rem Days of GPU time. Safe to stop with Ctrl+C between creatures and start again: finished work is kept.
echo Log: %LOG%
"%PY%" -u elin_creature_paperdolls.py full --motion --list "%LIST%" >> "%LOG%" 2>&1
"%PY%" -u elin_creature_paperdolls.py full --motion --all >> "%LOG%" 2>&1
echo Finished with exit code %ERRORLEVEL%. See %LOG%
pause
