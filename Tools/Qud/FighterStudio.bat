@echo off
rem Fighter Studio: character export -> picture prompt -> layered portrait -> 16x24 tile -> install
cd /d "%~dp0FighterStudio"
where pythonw >nul 2>nul && (start "" pythonw fighter_studio.py & exit /b)
python fighter_studio.py
if errorlevel 1 pause
