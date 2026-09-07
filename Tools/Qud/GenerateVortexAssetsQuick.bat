@echo off
REM Quick launcher — uses full PowerShell wrapper (Ollama check + quality pass)
set MOD_PATH=C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Improved and Rebalanced Space Time Vortex

cd /d "%~dp0"

echo ============================================================
echo Space-Time Vortex Asset Generator (Ollama REQUIRED)
echo ============================================================
echo Mod: Improved and Rebalanced Space Time Vortex
echo Tool: %~dp0generate_vortex_professional.py
echo.
echo Prerequisites:
echo   ollama serve
echo   ollama pull wizardlm-uncensored:latest
echo   pip install Pillow requests
echo.
pause

where pwsh >nul 2>&1
if %ERRORLEVEL%==0 (
    pwsh -ExecutionPolicy Bypass -File "%~dp0GenerateVortexAssets.ps1" -ModPath "%MOD_PATH%" -QualityAssessmentDepth full
) else (
    powershell -ExecutionPolicy Bypass -File "%~dp0GenerateVortexAssets.ps1" -ModPath "%MOD_PATH%" -QualityAssessmentDepth fast
)
