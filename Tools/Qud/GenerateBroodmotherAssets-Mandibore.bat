@echo off
REM ============================================================================
REM Broodmother — Mandibore only (CLIP-only SD on :1338)
REM ============================================================================
REM Starts SD if needed, force-regens BroodlingMandibore_T4 draft + 16x24 export.
REM Optional: pass "variants" to also roll pose/seed attempts into DesignDrafts\MandiboreVariants\
REM ============================================================================
REM Usage:
REM   GenerateBroodmotherAssets-Mandibore.bat
REM   GenerateBroodmotherAssets-Mandibore.bat variants
REM   GenerateBroodmotherAssets-Mandibore.bat nopause
REM ============================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"
set "SCRIPT_DIR=%~dp0"
set "PY=E:\tools\miniconda3\python.exe"
set "GEN=%SCRIPT_DIR%generate_broodmother_assets_ollama.py"
set "VAR=%SCRIPT_DIR%generate_mandibore_variants.py"
set "WAIT_SD=%SCRIPT_DIR%Wait-SdReady.ps1"
set "START_SD=%SCRIPT_DIR%Start-BroodmotherSDServer.bat"
set "MOD_PATH=%USERPROFILE%\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Broodmother Mutation"
set "LOG=%TEMP%\broodmother_mandibore_status.log"
set "EXIT_CODE=0"
set "NOPAUSE=0"
set "VARIANTS=0"

:parse
if "%~1"=="" goto :parsed
if /I "%~1"=="nopause" (set "NOPAUSE=1" & shift & goto :parse)
if /I "%~1"=="variants" (set "VARIANTS=1" & shift & goto :parse)
set "MOD_PATH=%~1"
shift
goto :parse
:parsed

set "SD_SKIP_T5=1"
set "SD_ALLOW_T5_RAM=0"
set "SD_REBALANCE=0"
set "SD_HEADROOM_GB=0"
set "SD_MAX_CPU_GB=24"
set "SD_MAX_GPU_GB=10"
set "SD_ALLOW_NONADMIN=1"

echo ========================================
echo Broodmother — Mandibore only
echo ========================================
echo Mod:      !MOD_PATH!
echo Variants: !VARIANTS!
echo Status:   !LOG!
echo ========================================
echo [%DATE% %TIME%] Mandibore bat start> "!LOG!"

if not exist "%PY%" (
  echo [ERROR] Python missing: %PY%
  set "EXIT_CODE=1"
  goto :end
)
if not exist "!MOD_PATH!\DesignDrafts\prompt_pack.json" (
  echo [ERROR] Missing prompt pack
  set "EXIT_CODE=1"
  goto :end
)

echo [0/3] Opening SD Status GUI...
if exist "%SCRIPT_DIR%Open-SDStatusGui.ps1" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%Open-SDStatusGui.ps1"
)
echo [%DATE% %TIME%] opening status GUI>> "!LOG!"

echo [1/3] Ensuring SD3.5 on :1338 ^(CLIP-only^)...
echo [%DATE% %TIME%] ensuring SD>> "!LOG!"
set "SD_OK=0"
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:1338/ping' -UseBasicParsing -TimeoutSec 3 | Out-Null; exit 0 } catch { exit 1 }"
if not errorlevel 1 set "SD_OK=1"
if "!SD_OK!"=="0" (
  echo [WARN] SD down — starting...
  echo [%DATE% %TIME%] starting SD>> "!LOG!"
  call "%START_SD%" nopause
) else (
  echo [OK] SD already up
  echo [%DATE% %TIME%] SD already up>> "!LOG!"
)
if exist "%WAIT_SD%" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%WAIT_SD%" -TimeoutSec 180
)

echo/
echo [2/3] Force-regen Mandibore draft + export...
"%PY%" "%GEN%" "!MOD_PATH!" --draft-dir DesignDrafts --load-existing --only BroodlingMandibore_T4 --force-drafts --verbose --model wizardlm-uncensored:latest
set "EXIT_CODE=!ERRORLEVEL!"
if not "!EXIT_CODE!"=="0" goto :end

if "!VARIANTS!"=="1" (
  echo/
  echo [3/3] Extra pose/seed variants...
  "%PY%" "%VAR%" "!MOD_PATH!"
  set "EXIT_CODE=!ERRORLEVEL!"
) else (
  echo [3/3] Skip variants ^(pass "variants" to roll attempts^)
)

:end
echo/
if "!EXIT_CODE!"=="0" (
  echo [SUCCESS] Check DesignDrafts\BroodlingMandibore_T4_design_draft.png
  echo           and Textures\Creatures\BroodlingMandibore_T4.png
  if "!VARIANTS!"=="1" echo           Variants: DesignDrafts\MandiboreVariants\
) else (
  echo [ERROR] exit !EXIT_CODE!
  echo SD log: E:\tools\sd3.5\sd3.5\sd_server.err.log
)
if "!NOPAUSE!"=="0" (
  echo Press any key to close...
  pause >nul
)
exit /b !EXIT_CODE!
