@echo off
REM ============================================================================
REM Broodmother — finish low-quality SD drafts (safe CLIP-only GPU path)
REM ============================================================================
REM 1) Starts SD3.5 with SD_SKIP_T5=1 (no T5 CPU-offload / pagefile balloon)
REM 2) Scores DesignDrafts; deletes near-black / empty / low-signal drafts
REM 3) Regenerates only missing drafts + re-exports (keeps good drafts)
REM ============================================================================
REM Usage:
REM   GenerateBroodmotherAssets-FinishLowQuality.bat
REM   GenerateBroodmotherAssets-FinishLowQuality.bat "C:\path\to\Broodmother Mutation"
REM   GenerateBroodmotherAssets-FinishLowQuality.bat dry-run
REM   GenerateBroodmotherAssets-FinishLowQuality.bat nopause
REM ============================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"
set "SCRIPT_DIR=%~dp0"
set "PY=E:\tools\miniconda3\python.exe"
set "GEN=%SCRIPT_DIR%generate_broodmother_assets_ollama.py"
set "FINISH=%SCRIPT_DIR%finish_low_quality_broodmother_drafts.py"
set "WAIT_SD=%SCRIPT_DIR%Wait-SdReady.ps1"
set "START_SD=%SCRIPT_DIR%Start-BroodmotherSDServer.bat"
set "LOG=%TEMP%\broodmother_finish_low_quality.log"
set "EXIT_CODE=0"
set "NOPAUSE=0"
set "DRYRUN=0"
set "MOD_PATH="

:parse
if "%~1"=="" goto :parsed
if /I "%~1"=="nopause" (set "NOPAUSE=1" & shift & goto :parse)
if /I "%~1"=="dry-run" (set "DRYRUN=1" & shift & goto :parse)
if /I "%~1"=="dryrun" (set "DRYRUN=1" & shift & goto :parse)
set "MOD_PATH=%~1"
shift
goto :parse
:parsed

if "!MOD_PATH!"=="" (
    set "MOD_PATH=%USERPROFILE%\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Broodmother Mutation"
)

echo ========================================
echo Broodmother — Finish Low-Quality Drafts
echo ========================================
echo Mod:     !MOD_PATH!
echo Mode:    CLIP-only GPU ^(no T5 pagefile offload^)
echo Dry-run: !DRYRUN!
echo Log:     !LOG!
echo ========================================
echo/
echo [%DATE% %TIME%] FinishLowQuality start> "!LOG!"

if not exist "%PY%" (
    echo [ERROR] Python not found: %PY%
    echo [ERROR] missing python>> "!LOG!"
    goto :fail
)
if not exist "%GEN%" (
    echo [ERROR] Missing %GEN%
    goto :fail
)
if not exist "%FINISH%" (
    echo [ERROR] Missing %FINISH%
    goto :fail
)
if not exist "!MOD_PATH!\DesignDrafts\prompt_pack.json" (
    echo [ERROR] No prompt pack at:
    echo   !MOD_PATH!\DesignDrafts\prompt_pack.json
    echo [ERROR] missing prompt_pack>> "!LOG!"
    goto :fail
)

REM --- Safe SD defaults: never unbounded T5+model_cpu_offload on Windows ---
set "SD_SKIP_T5=1"
set "SD_ALLOW_T5_RAM=0"
set "SD_REBALANCE=0"
set "SD_HEADROOM_GB=0"
set "SD_MAX_CPU_GB=24"
set "SD_MAX_GPU_GB=10"
set "SD_ALLOW_NONADMIN=1"

echo [1/4] Scoring drafts for low quality...
if "!DRYRUN!"=="1" (
    "%PY%" "%FINISH%" "!MOD_PATH!" --dry-run
    set "EXIT_CODE=!ERRORLEVEL!"
    echo DRYRUN score exit=!EXIT_CODE!>> "!LOG!"
    if not "!EXIT_CODE!"=="0" goto :fail
    echo/
    echo Dry-run complete. No deletes / no SD regen.
    goto :end
)

"%PY%" "%FINISH%" "!MOD_PATH!" --apply
set "EXIT_CODE=!ERRORLEVEL!"
echo score/apply exit=!EXIT_CODE!>> "!LOG!"
if not "!EXIT_CODE!"=="0" goto :fail

echo/
echo [2/4] Opening SD Status GUI + ensuring SD3.5 on :1338 ^(CLIP-only^)...
if exist "%SCRIPT_DIR%Open-SDStatusGui.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%Open-SDStatusGui.ps1"
)
set "SD_OK=0"
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:1338/ping' -UseBasicParsing -TimeoutSec 3 | Out-Null; exit 0 } catch { exit 1 }"
if not errorlevel 1 set "SD_OK=1"

if "!SD_OK!"=="0" (
    echo [WARN] SD not up — starting safe server...
    call "%START_SD%" nopause
) else (
    echo [OK] SD already responding on :1338
    echo       If this was an old T5/offload server, restart with Start-BroodmotherSDServer.bat
)

if exist "%WAIT_SD%" (
    echo Waiting for SD pipeline ready...
    powershell -NoProfile -ExecutionPolicy Bypass -File "%WAIT_SD%" -TimeoutSec 180
)

echo/
echo [3/4] Regenerating missing drafts + exporting...
echo       ^(good drafts kept; only deleted LOWs are re-POSTed^)
echo/
"%PY%" "%GEN%" "!MOD_PATH!" --draft-dir DesignDrafts --load-existing --verbose --model wizardlm-uncensored:latest
set "EXIT_CODE=!ERRORLEVEL!"
echo generator exit=!EXIT_CODE!>> "!LOG!"

echo/
echo [4/4] Done.
if "!EXIT_CODE!"=="0" (
    echo [SUCCESS] Low-quality drafts finished. Check DesignDrafts\ and Textures\
    echo Report: !MOD_PATH!\DesignDrafts\low_quality_report.json
) else (
    echo [ERROR] Generator exit !EXIT_CODE!
    echo SD log: E:\tools\sd3.5\sd3.5\sd_server.err.log
    echo Bat log: !LOG!
)
goto :end

:fail
set "EXIT_CODE=1"

:end
echo/
echo [%DATE% %TIME%] FinishLowQuality end exit=!EXIT_CODE!>> "!LOG!"
if "!NOPAUSE!"=="0" (
    echo Press any key to close this window...
    pause >nul
)
exit /b !EXIT_CODE!
