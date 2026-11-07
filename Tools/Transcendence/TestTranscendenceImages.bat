@echo off
rem Transcendence image / facing tester (rules mirrored from the engine source).
rem   TestTranscendenceImages.bat                      -> tests ZZZ_CrossModCompatibility
rem   TestTranscendenceImages.bat <folder-or-xml> ...  -> tests what you pass (drag and drop works)
rem Report + contact strips (frames 0/90/180/270 deg) land in Tools\Transcendence\Logs\image_tester\
setlocal
set "HERE=%~dp0"
set "OUT=%HERE%Logs\image_tester"
if not exist "%OUT%" mkdir "%OUT%"
set "TARGETS=%*"
if "%TARGETS%"=="" set TARGETS="D:\games\Steam\steamapps\common\Transcendence\Extensions\ZZZ_CrossModCompatibility"
python -I "%HERE%tx_image_tester.py" %TARGETS% --inventory --json "%OUT%\report.json" --contact "%OUT%\contact"
set RC=%ERRORLEVEL%
echo.
echo Report: %OUT%\report.json
echo Contact strips: %OUT%\contact
if %RC% NEQ 0 (echo RESULT: ERRORS FOUND) else (echo RESULT: PASS)
pause
exit /b %RC%
