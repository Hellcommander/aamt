@echo off
rem Drop a data mod (.mpq folder, packed .mpq, .zip, .7z, .rar) onto this file (see README.md, "Drag and drop").
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0_drop.ps1" convert-data %*
echo.
pause
