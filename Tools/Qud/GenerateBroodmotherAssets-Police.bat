@echo off
REM ============================================================================
REM Broodmother — quality POLICE loop (default recommended quality path)
REM ============================================================================
REM Heuristic gate (dark/flat/empty) → one Ollama critic (wizardlm) →
REM feed corrections into SD → retry failures only. Exclusive GPU swaps.
REM Slower than --quality-mode draft; much faster than full multi-model.
REM ============================================================================

setlocal enabledelayedexpansion
set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%GenerateBroodmotherAssets.ps1"
set "MOD_PATH=%~1"
if "!MOD_PATH!"=="" set "MOD_PATH=%USERPROFILE%\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Broodmother Mutation"

echo ========================================
echo Broodmother QUALITY POLICE (critique→correct→retry)
echo ========================================
echo Mod: !MOD_PATH!
echo Mode: police — heuristic + wizardlm critic + SD retry
echo Tradeoff: slower than draft-only; catches broken near-black/flat drafts
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -ModPath "!MOD_PATH!" -LoadExisting -Verbose -QualityMode police -OllamaModel "wizardlm-uncensored:latest" -UnloadModels -PythonExe "E:\tools\miniconda3\python.exe"
set "EXIT_CODE=%ERRORLEVEL%"

if %EXIT_CODE% equ 0 (
    echo.
    echo [SUCCESS] Police loop finished. See DesignDrafts\quality_loop_report.json
) else (
    echo.
    echo [ERROR] Exit %EXIT_CODE%
)
if /I not "%~2"=="nopause" pause
endlocal & exit /b %EXIT_CODE%
