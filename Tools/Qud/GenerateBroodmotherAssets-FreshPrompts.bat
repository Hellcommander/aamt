@echo off
REM ============================================================================
REM Broodmother Fresh Prompts + Assets
REM ============================================================================
REM Thin wrapper: Ollama pack bat, then Biomutation SD bat.
REM Prefer running each alone when iterating.
REM ============================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"
set "SCRIPT_DIR=%~dp0"
set "LOG=%TEMP%\broodmother_fresh_assets.log"
set "EXIT_CODE=0"

set "MOD_PATH=%~1"
if "!MOD_PATH!"=="" set "MOD_PATH=%USERPROFILE%\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Broodmother Mutation"

echo ========================================
echo Broodmother Fresh Prompts + Assets
echo ========================================
echo 1^) Ollama prompt pack   (SD stopped)
echo 2^) SD drafts            (LoadExisting)
echo Log: !LOG!
echo ========================================
echo.
echo [%DATE% %TIME%] fresh wrapper start> "!LOG!"

call "%SCRIPT_DIR%GenerateBroodmotherAssets-OllamaPrompts.bat" nopause "!MOD_PATH!"
set "EXIT_CODE=!ERRORLEVEL!"
echo PHASE_OLLAMA=!EXIT_CODE!>> "!LOG!"
if not "!EXIT_CODE!"=="0" goto :end

call "%SCRIPT_DIR%GenerateBroodmotherAssets-Biomutation.bat" nopause "!MOD_PATH!"
set "EXIT_CODE=!ERRORLEVEL!"
echo PHASE_SD=!EXIT_CODE!>> "!LOG!"

:end
echo.
if "!EXIT_CODE!"=="0" (echo [SUCCESS] Fresh prompts + assets done) else (echo [ERROR] exit !EXIT_CODE!)
echo Press any key to close...
pause >nul
exit /b !EXIT_CODE!
