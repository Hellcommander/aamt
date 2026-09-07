@echo off
REM ============================================================================
REM Start SD3.5 server for Broodmother / Qud asset generation (port 1338)
REM ============================================================================
REM Usage:
REM   Start-BroodmotherSDServer.bat
REM   Start-BroodmotherSDServer.bat nopause   (when called from another bat)
REM ============================================================================

setlocal
set "SCRIPT_DIR=%~dp0"
set "START_PS=%SCRIPT_DIR%..\Start-StableDiffusionServer.ps1"
set "NOPAUSE=0"
if /I "%~1"=="nopause" set "NOPAUSE=1"

if not exist "%START_PS%" (
    echo [ERROR] Missing %START_PS%
    if "%NOPAUSE%"=="0" pause
    exit /b 1
)

echo ========================================
echo Start SD3.5 API Server  (port 1338)
echo ========================================
echo Mode: CLIP-only GPU (SD_SKIP_T5=1) — avoids T5 CPU-offload pagefile balloon
echo Opt-in T5: set SD_ALLOW_T5_RAM=1 and SD_SKIP_T5=0 before running
echo.

REM Live status window (single-instance; safe from nested bats)
if /I not "%SD_STATUS_GUI%"=="0" (
  if exist "%SCRIPT_DIR%Open-SDStatusGui.ps1" (
    echo Opening SD Status GUI...
    powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%Open-SDStatusGui.ps1"
  )
)

REM Safe defaults for 11GB Turing + Windows commit/pagefile.
REM Do not use unbounded model_cpu_offload + T5 (was ~167GB private / ~210GB commit).
if not defined SD_SKIP_T5 set "SD_SKIP_T5=1"
if not defined SD_ALLOW_T5_RAM set "SD_ALLOW_T5_RAM=0"
if not defined SD_REBALANCE set "SD_REBALANCE=0"
if not defined SD_HEADROOM_GB set "SD_HEADROOM_GB=0"
if not defined SD_MAX_CPU_GB set "SD_MAX_CPU_GB=24"
if not defined SD_MAX_GPU_GB set "SD_MAX_GPU_GB=10"
if not defined SD_ALLOW_NONADMIN set "SD_ALLOW_NONADMIN=1"
REM Prefer full GPU. Past vortex runs often spilled to CPU (model/sequential) and pegged host cores.
if not defined SD_OFFLOAD set "SD_OFFLOAD=gpu"
if not defined SD_GPU_DIRECT_MIN_FREE_GB set "SD_GPU_DIRECT_MIN_FREE_GB=6"

powershell -NoProfile -ExecutionPolicy Bypass -File "%START_PS%" -Force -WaitSec 150
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if %EXIT_CODE% equ 0 (
    echo [OK] SD3.5 ping responded. Pipeline may still be loading to ready.
) else (
    echo [ERROR] Start failed (exit %EXIT_CODE%).
    echo Check: E:\tools\sd3.5\sd3.5\sd_server.out.log
    echo         E:\tools\sd3.5\sd3.5\sd_server.err.log
)

if "%NOPAUSE%"=="0" (
    echo.
    echo Press any key to close...
    pause >nul
)
endlocal & exit /b %EXIT_CODE%
