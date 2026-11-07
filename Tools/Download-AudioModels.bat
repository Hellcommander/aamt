@echo off
rem Downloads the audio listener models (and Stable Audio 3 with --sa3) into the Hugging Face cache.
rem Sign in first with:  hf auth login
rem   Download-AudioModels.bat            listeners only (CPU)
rem   Download-AudioModels.bat --sa3      also Stable Audio 3 medium (gated: accept its terms on huggingface.co first)
rem   Download-AudioModels.bat --list     show what is already here
setlocal
set "PY=python"
if exist "D:\Python\Python314\python.exe" set "PY=D:\Python\Python314\python.exe"
"%PY%" "%~dp0Shared\download_audio_models.py" %*
exit /b %ERRORLEVEL%
