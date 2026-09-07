@echo off
REM ============================================================================
REM Broodmother Mutation - Biomutation asset generation (recommended)
REM ============================================================================
REM Uses existing DesignDrafts\prompt_pack.json. Goes straight to SD3.5.
REM ============================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"
set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%GenerateBroodmotherAssets.ps1"
set "WAIT_SD=%SCRIPT_DIR%Wait-SdReady.ps1"
set "LOG=%TEMP%\broodmother_biomutation_assets.log"
set "EXIT_CODE=0"
set "NOPAUSE=0"
set "MOD_PATH=%~1"
if /I "%~1"=="nopause" (
    set "NOPAUSE=1"
    set "MOD_PATH=%~2"
)
if "!MOD_PATH!"=="" (
    set "MOD_PATH=%USERPROFILE%\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Broodmother Mutation"
)

echo ========================================
echo Broodmother Biomutation Assets
echo ========================================
echo Mod:    !MOD_PATH!
echo Mode:   POLICE quality loop ^(heuristic + wizardlm critic + SD retry^)
echo Ollama: wizardlm-uncensored:latest
echo Log:    !LOG!
echo Note:   Slower than draft-only — catches broken near-black/flat drafts
echo ========================================
echo/
echo [%DATE% %TIME%] Biomutation police start> "!LOG!"

if not exist "%PS_SCRIPT%" (
    echo [ERROR] Missing %PS_SCRIPT%
    goto :fail
)

if not exist "!MOD_PATH!\DesignDrafts\prompt_pack.json" (
    echo [ERROR] No prompt pack at:
    echo   !MOD_PATH!\DesignDrafts\prompt_pack.json
    echo Run GENERATE_OLLAMA_PROMPTS.bat first, or menu option: Ollama prompt pack only.
    echo [ERROR] missing prompt_pack>> "!LOG!"
    goto :fail
)

if exist "%SCRIPT_DIR%Open-SDStatusGui.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%Open-SDStatusGui.ps1"
)

set "SD_OK=0"
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:1338/ping' -UseBasicParsing -TimeoutSec 3 | Out-Null; exit 0 } catch { exit 1 }"
if not errorlevel 1 set "SD_OK=1"

if "!SD_OK!"=="0" (
    echo [WARN] SD3.5 not on :1338 - starting server...
    call "%SCRIPT_DIR%Start-BroodmotherSDServer.bat" nopause
)

echo Waiting for SD3.5 pipeline ready...
powershell -NoProfile -ExecutionPolicy Bypass -File "%WAIT_SD%" -TimeoutSec 180
if errorlevel 1 (
    echo [WARN] SD not fully ready - continuing anyway.
) else (
    echo [OK] SD ready>> "!LOG!"
)

echo/
echo Starting generator ^(can take hours - leave this window open^)...
echo/
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -ModPath "!MOD_PATH!" -LoadExisting -Verbose -QualityMode police -OllamaModel "wizardlm-uncensored:latest" -UnloadModels -PythonExe "E:\tools\miniconda3\python.exe"
set "EXIT_CODE=!ERRORLEVEL!"
echo EXIT_CODE=!EXIT_CODE!>> "!LOG!"

echo/
if "!EXIT_CODE!"=="0" (
    echo [SUCCESS] Done. Check DesignDrafts\ Textures\ preview.png
) else (
    echo [ERROR] Exit code !EXIT_CODE!
    echo SD log: E:\tools\sd3.5\sd3.5\sd_server.err.log
    echo Bat log: !LOG!
)
goto :end

:fail
set "EXIT_CODE=1"

:end
echo/
if "!NOPAUSE!"=="0" (
    echo Press any key to close this window...
    pause >nul
)
exit /b !EXIT_CODE!

