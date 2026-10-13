@echo off
setlocal
cd /d "%~dp0"

where pwsh >nul 2>&1
if %ERRORLEVEL%==0 (
  pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0Generate_Astral_Magic_Assets.ps1" -UseSD -GenerateDesignDraft %*
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Generate_Astral_Magic_Assets.ps1" -UseSD -GenerateDesignDraft %*
)

endlocal
