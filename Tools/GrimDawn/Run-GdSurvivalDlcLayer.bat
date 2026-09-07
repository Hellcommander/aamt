@echo off
setlocal
cd /d "%~dp0"
REM Deploy SurvivalPlayground as game-root survivalmode4 (Crucible DLC-style layer)
python -u "%~dp0pack_survival_dlc_layer.py" --source SurvivalPlayground --layer survivalmode4 %*
echo.
pause
exit /b %ERRORLEVEL%
