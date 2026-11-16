@echo off
setlocal
cd /d "%~dp0"
set "PY=D:\Python\Python314\python.exe"
if not exist "%PY%" set "PY=python"
set "LIST=E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator\Paperdolls\priority_ids.txt"
set "LOG=%~dp0Output\CreaturePaperdolls\%~n0.log"
rem Pipeline sheets for EVERY creature tile on the fast route (shallow relief, about 5 seconds each, about an hour
rem for all 739). Tiles that already have a sheet are skipped, and real bodies are not replaced.
rem This gives every creature four faces now; the real-body and motion files improve them later.
echo Log: %LOG%
"%PY%" -u elin_creature_paperdolls.py run --all >> "%LOG%" 2>&1
echo Finished with exit code %ERRORLEVEL%. See %LOG%
if not defined ELIN_ASSETS_NOPAUSE pause
