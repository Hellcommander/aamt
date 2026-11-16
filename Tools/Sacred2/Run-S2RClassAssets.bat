@echo off
rem Sacred 2 Remaster: icons and portraits for S2X custom classes. No arguments = help. See README.md.
setlocal
set "PY=python"
where python >nul 2>nul || set "PY=py -3"
if "%~1"=="" (
  %PY% "%~dp0s2r_class_assets.py" --help
  pause
) else (
  %PY% "%~dp0s2r_class_assets.py" %*
)
