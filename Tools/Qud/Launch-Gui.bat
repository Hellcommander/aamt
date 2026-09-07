@echo off
REM Qud toolkit launcher — every desktop GUI in this folder, plus ApiMigrator.
setlocal EnableDelayedExpansion
cd /d "%~dp0"

:menu
cls
echo ============================================================
echo   Caves of Qud toolkit
echo   %CD%
echo ============================================================
echo.
echo   1  ApiMigrator          obsolete APIs / dump / DLL research
echo   2  Qud Lab              mod IDE / simulate / local AI
echo   3  Choose Your Fighter  player tile + detailed art
echo   4  Atlas Art Translator CP437 / atlas text
echo   5  SD Server status     Stable Diffusion :1338
echo   6  Broodmother assets   generation menu
echo.
echo   Q  Quit
echo.
set /p CHOICE=Select: 
if /I "%CHOICE%"=="Q" exit /b 0
if "%CHOICE%"=="1" call "%~dp0Launch-ApiMigrator.bat" & goto after
if "%CHOICE%"=="2" call "%~dp0QudLab\QudLab.bat" & goto after
if "%CHOICE%"=="3" call "%~dp0ChooseYourFighter-GUI.bat" & goto after
if "%CHOICE%"=="4" call "%~dp0AtlasArtTranslator-GUI.bat" & goto after
if "%CHOICE%"=="5" call "%~dp0SDServer-Status-GUI.bat" & goto after
if "%CHOICE%"=="6" call "%~dp0BroodmotherAssets-Menu.bat" & goto after
echo Unknown choice.
pause
goto menu

:after
echo.
pause
goto menu
