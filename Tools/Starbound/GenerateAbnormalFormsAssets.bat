@echo off
REM GenerateAbnormalFormsAssets.bat
REM Batch wrapper for generating assets for all abnormal segmented mech forms

cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -File "%~dp0GenerateAbnormalFormsAssets.ps1" %*
pause
