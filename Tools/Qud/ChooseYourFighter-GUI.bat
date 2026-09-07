@echo off
REM Choose Your Fighter — CoQ (Recur export / save import GUI)
cd /d "%~dp0"
powershell -STA -NoProfile -ExecutionPolicy Bypass -File "%~dp0ChooseYourFighter-GUI.ps1"
if errorlevel 1 pause
