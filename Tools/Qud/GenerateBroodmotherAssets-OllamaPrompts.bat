@echo off
REM ============================================================================
REM Broodmother - Ollama prompt pack only (optimized for 11GB VRAM hybrid)
REM ============================================================================
REM Does NOT start SD. Stops SD if running so wizardlm can use ~9GB free VRAM.
REM Writes: DesignDrafts\prompt_pack.json
REM Next:   GenerateBroodmotherAssets-Biomutation.bat / GENERATE_ASSETS.bat
REM
REM Usage: GenerateBroodmotherAssets-OllamaPrompts.bat [nopause] [force] [modpath]
REM   - Without force: skips Ollama entirely if prompt_pack.json is already 34/34 complete.
REM   - With force: warm-loads Ollama and regenerates the pack (merges; never wipes UI keys).
REM ============================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"
set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%GenerateBroodmotherAssets.ps1"
set "CHECK_PY=%SCRIPT_DIR%check_broodmother_prompt_pack.py"
set "LOG=%TEMP%\broodmother_ollama_prompts.log"
set "EXIT_CODE=0"
set "PYTHON_EXE=E:\tools\miniconda3\python.exe"
set "OLLAMA_MODEL=wizardlm-uncensored:latest"
set "OLLAMA_TIMEOUT=1800"
set "OLLAMA_LOAD_TIMEOUT_SEC=900"
REM auto = hybrid split (some layers VRAM, rest CPU/RAM). Not 0 (all CPU) or 99 (all GPU).
set "AAMT_OLLAMA_NUM_GPU=auto"
set "AAMT_OLLAMA_GPU_LAYER_FRACTION=0.65"
set "AAMT_OLLAMA_VRAM_HEADROOM_GB=1.0"
set "NOPAUSE=0"
set "FORCE=0"
set "MOD_PATH="

REM Parse args: nopause | force | modpath (any order)
:parse_args
if "%~1"=="" goto :args_done
if /I "%~1"=="nopause" (
    set "NOPAUSE=1"
    shift
    goto :parse_args
)
if /I "%~1"=="force" (
    set "FORCE=1"
    shift
    goto :parse_args
)
if /I "%~1"=="/force" (
    set "FORCE=1"
    shift
    goto :parse_args
)
set "MOD_PATH=%~1"
shift
goto :parse_args
:args_done

if "!MOD_PATH!"=="" set "MOD_PATH=%USERPROFILE%\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Broodmother Mutation"
set "PACK_PATH=!MOD_PATH!\DesignDrafts\prompt_pack.json"

echo ========================================
echo Broodmother Ollama Prompt Pack
echo ========================================
echo Mod:     !MOD_PATH!
echo Model:   !OLLAMA_MODEL!
echo Mode:    SkipSD35 / NoCache / UnloadModels
if "!FORCE!"=="1" (
    echo Force:   YES - regenerate even if pack complete
) else (
    echo Force:   no - skip if prompt_pack.json already 34/34
)
echo GPU:     AAMT_OLLAMA_NUM_GPU=!AAMT_OLLAMA_NUM_GPU!  fraction=!AAMT_OLLAMA_GPU_LAYER_FRACTION! headroom=!AAMT_OLLAMA_VRAM_HEADROOM_GB!GB
echo Timeout: !OLLAMA_TIMEOUT!s  (load !OLLAMA_LOAD_TIMEOUT_SEC!s)
echo Log:     !LOG!
echo ========================================
echo.
echo [%DATE% %TIME%] ollama prompts start force=!FORCE!> "!LOG!"

if not exist "%PS_SCRIPT%" (
    echo [ERROR] Missing %PS_SCRIPT%
    set "EXIT_CODE=1"
    goto :end
)
if not exist "!PYTHON_EXE!" (
    echo [ERROR] Missing !PYTHON_EXE!
    set "EXIT_CODE=1"
    goto :end
)
if not exist "!CHECK_PY!" (
    echo [ERROR] Missing !CHECK_PY!
    set "EXIT_CODE=1"
    goto :end
)

REM --- Skip warm-load/Ollama when pack is already complete (unless force) ---
if not "!FORCE!"=="1" (
    if exist "!PACK_PATH!" (
        "!PYTHON_EXE!" "!CHECK_PY!" "!PACK_PATH!"
        if not errorlevel 1 (
            echo [OK] prompt_pack.json already complete 34/34 - skipping Ollama.
            echo       Next: GENERATE_ASSETS.bat  (SD drafts from existing pack)
            echo       To regenerate prompts: re-run with force
            echo SKIP=complete>> "!LOG!"
            set "EXIT_CODE=0"
            goto :end
        ) else (
            echo [INFO] Pack incomplete - will regenerate with Ollama.
            echo INCOMPLETE=1>> "!LOG!"
        )
    ) else (
        echo [INFO] No prompt_pack.json yet - will generate with Ollama.
    )
)

REM --- Ollama up ---
powershell -NoProfile -Command "try { Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 5 | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 (
    echo [ERROR] Ollama API not reachable at :11434
    echo Start Ollama, then re-run this bat.
    set "EXIT_CODE=1"
    goto :end
)
echo [OK] Ollama API reachable

REM --- Model present ---
powershell -NoProfile -Command "try { $t=Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 8; $n=@($t.models | ForEach-Object { $_.name }); if ($n -contains 'wizardlm-uncensored:latest') { exit 0 }; Write-Host ('Have: ' + ($n -join ', ')); exit 1 } catch { exit 1 }"
if errorlevel 1 (
    echo [ERROR] !OLLAMA_MODEL! not installed.
    echo Run: ollama pull wizardlm-uncensored:latest
    set "EXIT_CODE=1"
    goto :end
)
echo [OK] !OLLAMA_MODEL! installed

REM --- Free VRAM: stop SD (server.py holds ~10GB when ready) ---
echo.
echo Stopping SD3.5 on :1338 so wizardlm can use GPU+RAM hybrid...
call "%SCRIPT_DIR%Stop-BroodmotherSDServer.bat" nopause
timeout /t 4 /nobreak >nul

powershell -NoProfile -Command "try { Invoke-RestMethod 'http://127.0.0.1:1338/ping' -TimeoutSec 2 | Out-Null; exit 1 } catch { exit 0 }"
if errorlevel 1 (
    echo [WARN] Something still answers on :1338 - Ollama may be forced to system RAM only.
) else (
    echo [OK] SD stopped / :1338 quiet
)

REM --- Drop any CPU-only residency, then warm-load onto GPU ---
echo.
echo Unloading any CPU-only wizardlm residency (so next load can use VRAM)...
"!PYTHON_EXE!" -c "import requests; requests.post('http://127.0.0.1:11434/api/generate',json={'model':'wizardlm-uncensored:latest','prompt':'','stream':False,'keep_alive':0},timeout=60); print('unload sent')"
timeout /t 2 /nobreak >nul

echo.
echo Warm-loading !OLLAMA_MODEL! hybrid (auto num_gpu - VRAM + CPU/RAM share)...
echo Expect size_vram ^< size (some layers on CPU). Util low until tokens.
"!PYTHON_EXE!" -c "import os,sys,requests; sys.path.insert(0,r'D:\games\Steam\steamapps\common\Transcendence\Tools\Shared'); from ollama_integration import get_num_gpu_layers; ng=get_num_gpu_layers('wizardlm-uncensored:latest'); print('num_gpu',ng,'(hybrid)'); r=requests.post('http://127.0.0.1:11434/api/generate',json={'model':'wizardlm-uncensored:latest','prompt':'.','stream':False,'keep_alive':'45m','options':{'num_predict':1,'temperature':0,'num_gpu':ng}},timeout=900); print('warm HTTP',r.status_code); sys.exit(0 if r.status_code==200 else 1)"
if errorlevel 1 (
    echo [WARN] Warm-load failed or timed out - continuing to full pack anyway.
    echo WARM=fail>> "!LOG!"
) else (
    echo [OK] Model warm
    echo WARM=ok>> "!LOG!"
    powershell -NoProfile -Command "try { $ps=Invoke-RestMethod 'http://127.0.0.1:11434/api/ps' -TimeoutSec 5; foreach($m in $ps.models){ $s=[math]::Round($m.size/1GB,2); $v=[math]::Round($m.size_vram/1GB,2); Write-Host ('[STATUS] '+$m.name+' size='+$s+'GB vram='+$v+'GB'); if($v -gt 0 -and $v -lt $s){ Write-Host '[OK] Hybrid share: VRAM + system RAM/CPU' } elseif($v -le 0){ Write-Host '[WARN] All in system RAM (CPU) - check AAMT_OLLAMA_NUM_GPU' } elseif($v -ge $s){ Write-Host '[WARN] All on VRAM - not sharing CPU layers; lower AAMT_OLLAMA_GPU_LAYER_FRACTION' } } } catch {}"
)

echo.
echo Generating prompt_pack.json (leave this window open)...
echo Watch: ollama.exe for GPU/RAM - generator python stays mostly idle.
echo.
if "!FORCE!"=="1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -ModPath "!MOD_PATH!" -SkipSD35 -Verbose -NoCache -ForcePromptPack -OllamaModel "!OLLAMA_MODEL!" -UnloadModels -OllamaTimeout !OLLAMA_TIMEOUT! -PythonExe "!PYTHON_EXE!"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -ModPath "!MOD_PATH!" -SkipSD35 -Verbose -NoCache -OllamaModel "!OLLAMA_MODEL!" -UnloadModels -OllamaTimeout !OLLAMA_TIMEOUT! -PythonExe "!PYTHON_EXE!"
)
set "EXIT_CODE=!ERRORLEVEL!"
echo EXIT=!EXIT_CODE!>> "!LOG!"

if not "!EXIT_CODE!"=="0" (
    echo [ERROR] Ollama prompt pack failed (exit !EXIT_CODE!)
    if exist "!MOD_PATH!\DesignDrafts\prompt_pack.json" (
        echo [HINT] Older prompt_pack.json still present - you can run GENERATE_ASSETS.bat with it.
    )
    goto :end
)

if not exist "!MOD_PATH!\DesignDrafts\prompt_pack.json" (
    echo [ERROR] prompt_pack.json missing after run
    set "EXIT_CODE=1"
    goto :end
)

echo.
echo [SUCCESS] Wrote !MOD_PATH!\DesignDrafts\prompt_pack.json
echo Next: GENERATE_ASSETS.bat  (starts SD, LoadExisting drafts)
echo NEXT=GENERATE_ASSETS>> "!LOG!"

:end
echo.
if "!NOPAUSE!"=="0" (
    echo Press any key to close...
    pause >nul
)
exit /b !EXIT_CODE!
