@echo off
setlocal
cd /d "%~dp0"
REM Pack BOTH:
REM   1) Survival DLC layer  ->  <game>\survivalmode4\
REM   2) Campaign Custom Game ->  <game>\mods\CampaignKitchenSink\
REM Source: mods\SurvivalPlayground (build first with Run-GdSurvivalClasses.bat)
python -u "%~dp0pack_dual_archives.py" --source SurvivalPlayground %*
echo.
pause
exit /b %ERRORLEVEL%
