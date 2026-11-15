@echo off
setlocal
cd /d "%~dp0"
set "PY=D:\Python\Python314\python.exe"
if not exist "%PY%" set "PY=python"
set "LIST=E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator\Paperdolls\priority_ids.txt"
set "LOG=%~dp0Output\CreaturePaperdolls\%~n0.log"
rem How many creature tiles have reached each stage.
"%PY%" elin_creature_paperdolls.py status
pause
