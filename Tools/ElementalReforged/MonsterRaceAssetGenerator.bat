@echo off
setlocal
cd /d "%~dp0"
REM Elemental Reforged Monster Gear — AAMT (Ollama + SD + ImageMagick + Tools)
REM
REM   MonsterRaceAssetGenerator.bat -Race All -Mode Both -InstallToMod -StartSD
REM   MonsterRaceAssetGenerator.bat -Race Darkling -Mode AI -InstallToMod
REM   MonsterRaceAssetGenerator.bat -Doctor -StartSD
REM
REM Pure Python:
REM   python monster_race_tool.py doctor --start-sd
REM   python monster_race_tool.py generate --all --mode both --start-sd --install

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0MonsterRaceAssetGenerator.ps1" %*
exit /b %ERRORLEVEL%
