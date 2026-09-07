@echo off
setlocal
cd /d "%~dp0"
python generate_all.py --install --preview
exit /b %ERRORLEVEL%
