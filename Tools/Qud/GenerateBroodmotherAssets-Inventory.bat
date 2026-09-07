@echo off
REM ============================================================================
REM Broodmother — regenerate inventory / dual-view gear art
REM ============================================================================
REM Targets (default):
REM   broodmother_icon   -> Textures/Broodmother_icon.png (64x96)
REM   broodling_sack     -> Equipment sack tile/icon + Items/sw_broodmother_back.png
REM   texture_carapace   -> Equipment/Items sw_carapace.png
REM
REM Uses CLIP-only GPU SD (no T5 pagefile balloon). Keeps other drafts untouched.
REM ============================================================================
REM Usage:
REM   GenerateBroodmotherAssets-Inventory.bat
REM   GenerateBroodmotherAssets-Inventory.bat "C:\path\to\Broodmother Mutation"
REM   GenerateBroodmotherAssets-Inventory.bat only=broodmother_icon,broodling_sack
REM   GenerateBroodmotherAssets-Inventory.bat dry-run
REM   GenerateBroodmotherAssets-Inventory.bat nopause
REM ============================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"
set "SCRIPT_DIR=%~dp0"
set "PY=E:\tools\miniconda3\python.exe"
set "GEN=%SCRIPT_DIR%generate_broodmother_assets_ollama.py"
set "WAIT_SD=%SCRIPT_DIR%Wait-SdReady.ps1"
set "START_SD=%SCRIPT_DIR%Start-BroodmotherSDServer.bat"
set "LOG=%TEMP%\broodmother_inventory_assets.log"
set "EXIT_CODE=0"
set "NOPAUSE=0"
set "DRYRUN=0"
set "MOD_PATH="
set "ONLY=broodmother_icon,broodling_sack,texture_carapace"

:parse
if "%~1"=="" goto :parsed
if /I "%~1"=="nopause" (set "NOPAUSE=1" & shift & goto :parse)
if /I "%~1"=="dry-run" (set "DRYRUN=1" & shift & goto :parse)
if /I "%~1"=="dryrun" (set "DRYRUN=1" & shift & goto :parse)
set "ARG=%~1"
if /I "!ARG:~0,5!"=="only=" (
    set "ONLY=!ARG:~5!"
    shift
    goto :parse
)
set "MOD_PATH=%~1"
shift
goto :parse
:parsed

if "!MOD_PATH!"=="" (
    set "MOD_PATH=%USERPROFILE%\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Broodmother Mutation"
)

echo ========================================
echo Broodmother — Inventory / Dual-View Art
echo ========================================
echo Mod:   !MOD_PATH!
echo Only:  !ONLY!
echo Mode:  CLIP-only GPU ^(SD_SKIP_T5=1^)
echo Log:   !LOG!
echo ========================================
echo/
echo [%DATE% %TIME%] Inventory assets start> "!LOG!"

if not exist "%PY%" (
    echo [ERROR] Python not found: %PY%
    goto :fail
)
if not exist "%GEN%" (
    echo [ERROR] Missing %GEN%
    goto :fail
)
if not exist "!MOD_PATH!\DesignDrafts\prompt_pack.json" (
    echo [ERROR] No prompt pack at:
    echo   !MOD_PATH!\DesignDrafts\prompt_pack.json
    echo Run GenerateBroodmotherAssets-OllamaPrompts.bat / Biomutation pack first.
    goto :fail
)

REM Safe SD defaults
set "SD_SKIP_T5=1"
set "SD_ALLOW_T5_RAM=0"
set "SD_REBALANCE=0"
set "SD_HEADROOM_GB=0"
set "SD_MAX_CPU_GB=24"
set "SD_MAX_GPU_GB=10"
set "SD_ALLOW_NONADMIN=1"

if "!DRYRUN!"=="1" (
    echo [DRY-RUN] Would force-regen and export:
    echo   !ONLY!
    echo Drafts typically:
    echo   icon_design_draft.png / sack_design_draft.png / texture_carapace_design_draft.png
    echo Exports:
    echo   Textures\Broodmother_icon.png
    echo   Textures\Equipment\Broodling_Sack_tile.png
    echo   Textures\Equipment\Broodling_Sack_icon.png
    echo   Items\sw_broodmother_back.png
    echo   Textures\Equipment\sw_carapace.png
    echo   Items\sw_carapace.png
    set "EXIT_CODE=0"
    goto :end
)

echo [1/3] Opening SD Status GUI + ensuring SD3.5 on :1338...
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
    echo [OK] SD responding on :1338
)

if exist "%WAIT_SD%" (
    echo Waiting for SD pipeline ready...
    powershell -NoProfile -ExecutionPolicy Bypass -File "%WAIT_SD%" -TimeoutSec 180
)

echo/
echo [2/3] Force-regenerating inventory drafts + exporting ^(64x96 dual-view^)...
echo/
"%PY%" "%GEN%" "!MOD_PATH!" --draft-dir DesignDrafts --load-existing --verbose --force-drafts --only "!ONLY!" --model wizardlm-uncensored:latest
set "EXIT_CODE=!ERRORLEVEL!"
echo generator exit=!EXIT_CODE!>> "!LOG!"

echo/
echo [3/3] Spot-check inventory exports...
"%PY%" -c "from pathlib import Path; from PIL import Image; mod=Path(r'!MOD_PATH!'); paths=['Textures/Broodmother_icon.png','Textures/Equipment/Broodling_Sack_tile.png','Textures/Equipment/Broodling_Sack_icon.png','Items/sw_broodmother_back.png','Textures/Equipment/sw_carapace.png','Items/sw_carapace.png'];
for rel in paths:
 p=mod/rel
 if not p.exists(): print('MISSING', rel); continue
 im=Image.open(p).convert('RGBA'); op=[(r,g,b) for r,g,b,a in im.getdata() if a>=16]; u=len(set(op)); print(('BAD' if u<2 else 'ok '), rel, f'{im.size[0]}x{im.size[1]}', f'uniq={u}', f'{p.stat().st_size}B')"

if "!EXIT_CODE!"=="0" (
    echo [SUCCESS] Inventory art pass finished.
    echo Tip: set Mutations.xml Icon="Textures/Broodmother_icon.png" if not already wired.
) else (
    echo [ERROR] Exit !EXIT_CODE!
    echo SD log: E:\tools\sd3.5\sd3.5\sd_server.err.log
    echo Bat log: !LOG!
)
goto :end

:fail
set "EXIT_CODE=1"

:end
echo/
echo [%DATE% %TIME%] Inventory assets end exit=!EXIT_CODE!>> "!LOG!"
if "!NOPAUSE!"=="0" (
    echo Press any key to close this window...
    pause >nul
)
exit /b !EXIT_CODE!
