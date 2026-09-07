# Start-StableDiffusionServer.ps1
# AI-Assisted Modding Tools (AAMT)
# Starts SD3.5 API server (updated to use SD3.5 from GitHub)
#
# The server is launched with CREATE_NO_WINDOW (no console host). A previous
# `cmd start "SD3.5 Server" /MIN` launch created a closable console; closing it
# triggered `forrtl: error (200): window-CLOSE` and killed Python mid-run.
# The launcher may wait up to -WaitSec for /ping, then exit; that wait never
# terminates the server. Closing the Status GUI / bat wrapper also cannot kill it.
# By default the server auto-exits after SD_IDLE_SHUTDOWN_SEC (180) with no
# generations — use Stop-StableDiffusionServer.ps1 to stop immediately.
#
# Prefer VRAM-first inference (SD_OFFLOAD=auto -> gpu on 8GB+ free). System RAM
# is a spill path for CPU overflow when VRAM is tight — not the preferred load
# target. SD_REBALANCE spills under headroom pressure and reclaims to VRAM when
# free again. Do not launch a CPU-only PyTorch.
#
# Server output is logged to:
#   E:\tools\sd3.5\sd3.5\sd_server.out.log
#   E:\tools\sd3.5\sd3.5\sd_server.err.log
#
# Env knobs (optional):
#   SD_OFFLOAD=auto|gpu|0|shared|model|sequential|cpu
#     auto (default): full GPU when free VRAM >= SD_GPU_DIRECT_MIN_FREE_GB (default 8)
#     gpu / 0:        prefer full GPU (still spill on OOM / headroom)
#     shared / model: start spilled (active on GPU, idle in RAM) — avoid unless needed
#     sequential/cpu: heavier RAM spill (last resorts)
#   SD_GPU_DIRECT_MIN_FREE_GB   (default 8)  auto -> gpu threshold / reclaim target
#   SD_GPU_SHARED_MIN_FREE_GB   (default 3.5)
#   SD_REBALANCE=1              spill+reclaim around each generate
#   SD_HEADROOM_GB=0            spill from full-gpu when free VRAM below this
#                               (default 0: SD3.5 Medium fills 11GB so free≈0;
#                               a 0.5 threshold forced CPU spill every generate)
#   SD_RECLAIM_MIN_FREE_GB      free needed to reclaim toward gpu (default = direct)
#   SD_PRELOAD=1  SD_MAX_SEQ_LEN=256  SD_ALLOW_NONADMIN=1

param(
    [switch]$Force,
    [int]$WaitSec = 90,
    [switch]$NoStatusGui
)

$sd35Path = "E:\tools\sd3.5\sd3.5"
$sd35Server = Join-Path $sd35Path "server.py"
$sharedSdServer = Join-Path $PSScriptRoot "Shared\sd35_server.py"
$preferredCudaPython = "E:\tools\miniconda3\python.exe"
$qudTools = Join-Path $PSScriptRoot "Qud"
$openGui = Join-Path $qudTools "Open-SDStatusGui.ps1"

# Live status window for any SD start (set SD_STATUS_GUI=0 or -NoStatusGui to skip)
if (-not $NoStatusGui -and $env:SD_STATUS_GUI -ne "0" -and (Test-Path -LiteralPath $openGui)) {
    try {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $openGui | Out-Null
    } catch {
        Write-Host "[WARN] Could not open SD Status GUI: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

function Test-SdAlreadyRunning {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $async = $client.BeginConnect("127.0.0.1", 1338, $null, $null)
        $ok = $async.AsyncWaitHandle.WaitOne(500, $false)
        if ($ok) {
            try { $client.EndConnect($async); $client.Close(); return $true }
            catch { $client.Close(); return $false }
        }
        $client.Close()
        return $false
    } catch {
        return $false
    }
}

function Test-SdResponding {
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:1338/ping" -Method Get -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
        return ($resp.StatusCode -eq 200)
    } catch {
        return $false
    }
}

function Test-AamtSdServer {
    <# True only for Tools/Shared/sd35_server.py (ping.version starts with aamt-1338). #>
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:1338/ping" -Method Get -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
        return ([string]$resp.Content -match 'aamt-1338')
    } catch {
        return $false
    }
}

function Stop-SdListeners {
    <# Kill whatever holds TCP 1338 so -Force can replace a bad (e.g. CPU-only) server. #>
    $pids = @()
    try {
        $conns = Get-NetTCPConnection -LocalPort 1338 -State Listen -ErrorAction SilentlyContinue
        if ($conns) { $pids += @($conns | Select-Object -ExpandProperty OwningProcess -Unique) }
    } catch { }
    try {
        $lines = netstat -ano | Select-String ":1338\s+.*LISTENING"
        foreach ($line in $lines) {
            if ($line -match '\s(\d+)\s*$') { $pids += [int]$Matches[1] }
        }
    } catch { }
    $pids = $pids | Where-Object { $_ -and $_ -gt 0 } | Select-Object -Unique
    foreach ($procId in $pids) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue
        $parentId = if ($proc) { [int]$proc.ParentProcessId } else { 0 }
        foreach ($killId in @($parentId, $procId) | Where-Object { $_ -gt 0 } | Select-Object -Unique) {
            try { Stop-Process -Id $killId -Force -ErrorAction Stop; Write-Host "Stopped PID $killId" -ForegroundColor Yellow }
            catch {
                try {
                    $cim = Get-CimInstance Win32_Process -Filter "ProcessId=$killId" -ErrorAction Stop
                    $rv = (Invoke-CimMethod -InputObject $cim -MethodName Terminate).ReturnValue
                    if ($rv -eq 0) { Write-Host "Terminated PID $killId via CIM" -ForegroundColor Yellow }
                    else { Write-Host "WARN: could not stop PID $killId (CIM ReturnValue=$rv). Kill it manually if -Force relaunch fails." -ForegroundColor Red }
                } catch {
                    Write-Host "WARN: access denied stopping PID $killId. End that console/admin process, then retry -Force." -ForegroundColor Red
                }
            }
        }
    }
    Start-Sleep -Seconds 2
    if (Test-SdAlreadyRunning) {
        Write-Host "WARN: port 1338 still listening after stop attempt." -ForegroundColor Red
    }
}

function Resolve-CudaPython {
    <# Prefer Miniconda CUDA torch; never silently pick a CPU-only interpreter. #>
    $candidates = @()
    if (Test-Path -LiteralPath $preferredCudaPython) { $candidates += $preferredCudaPython }
    foreach ($name in @("python", "python3")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source -and (Test-Path -LiteralPath $cmd.Source)) {
            if ($candidates -notcontains $cmd.Source) { $candidates += $cmd.Source }
        }
    }
    foreach ($cand in $candidates) {
        try {
            $out = & $cand -c "import torch; print('CUDA' if torch.cuda.is_available() else 'CPU'); print(torch.__version__); print(torch.__file__)" 2>&1
            $text = ($out | Out-String)
            if ($text -match 'CUDA' -and $text -notmatch '\+cpu\b') {
                Write-Host "Using CUDA Python: $cand" -ForegroundColor Gray
                Write-Host "  $($text.Trim())" -ForegroundColor Gray
                return $cand
            }
            Write-Host "Skipping CPU-only / broken torch at $cand" -ForegroundColor Yellow
            Write-Host "  $($text.Trim())" -ForegroundColor DarkYellow
        } catch {
            Write-Host "Skipping $cand (torch probe failed)" -ForegroundColor Yellow
        }
    }
    return $null
}

function Start-DetachedServer {
    <#
    Launch server.py fully breakaway from the launcher console/job.

    Failure modes we hit before:
      - `start "SD3.5 Server" /MIN` -> closable console -> forrtl window-CLOSE abort
      - CreateNoWindow child of PowerShell (same process group) -> bat/console
        Ctrl+C or close still kills Python seconds after ping looks OK

    Fix: write env launch .cmd, then start it via WScript.Shell.Run(style=0,
    wait=False) so it is not in the launcher's console group and has no window.
    #>
    param(
        [Parameter(Mandatory = $true)][string]$PythonExe,
        [Parameter(Mandatory = $true)][string]$WorkDir,
        [string]$ServerScript = "server.py",
        [string]$ExtraArgs = "--host localhost --port 1338"
    )
    $outLog = Join-Path $WorkDir "sd_server.out.log"
    $errLog = Join-Path $WorkDir "sd_server.err.log"
    $launchCmd = Join-Path $WorkDir "_sd_detached_launch.cmd"
    $launchVbs = Join-Path $WorkDir "_sd_detached_launch.vbs"
    $pidFile = Join-Path $WorkDir "sd_server.pid"

    # Build .cmd lines with -f / single-quoted formats so Windows PowerShell 5.1
    # does not treat >> or > inside "..." as redirects (breaks whole-file parse).
    $lines = @(
        '@echo off'
        ('cd /d "{0}"' -f $WorkDir)
        ('set "SD_OFFLOAD={0}"' -f $env:SD_OFFLOAD)
        ('set "SD_ALLOW_NONADMIN={0}"' -f $env:SD_ALLOW_NONADMIN)
        ('set "SD_PRELOAD={0}"' -f $env:SD_PRELOAD)
        ('set "SD_MAX_SEQ_LEN={0}"' -f $env:SD_MAX_SEQ_LEN)
        ('set "SD_GPU_DIRECT_MIN_FREE_GB={0}"' -f $env:SD_GPU_DIRECT_MIN_FREE_GB)
        ('set "SD_GPU_SHARED_MIN_FREE_GB={0}"' -f $env:SD_GPU_SHARED_MIN_FREE_GB)
        ('set "SD_REBALANCE={0}"' -f $env:SD_REBALANCE)
        ('set "SD_HEADROOM_GB={0}"' -f $env:SD_HEADROOM_GB)
        ('set "SD_RECLAIM_MIN_FREE_GB={0}"' -f $env:SD_RECLAIM_MIN_FREE_GB)
        ('set "SD_SKIP_T5={0}"' -f $env:SD_SKIP_T5)
        ('set "SD_ALLOW_T5_RAM={0}"' -f $env:SD_ALLOW_T5_RAM)
        ('set "SD_MAX_CPU_GB={0}"' -f $env:SD_MAX_CPU_GB)
        ('set "SD_MAX_GPU_GB={0}"' -f $env:SD_MAX_GPU_GB)
        ('set "SD_MIN_DIM={0}"' -f $env:SD_MIN_DIM)
        ('set "SD_MAX_DIM={0}"' -f $env:SD_MAX_DIM)
        ('set "SD_DIM_STEP={0}"' -f $env:SD_DIM_STEP)
        ('set "SD_QUALITY_FLOOR={0}"' -f $env:SD_QUALITY_FLOOR)
        ('set "SD_SUPER_SAMPLE={0}"' -f $env:SD_SUPER_SAMPLE)
        ('set "SD_ICON_STEPS={0}"' -f $env:SD_ICON_STEPS)
        ('set "SD_DOWNSCALE_SHARPNESS={0}"' -f $env:SD_DOWNSCALE_SHARPNESS)
        ('set "SD_DOWNSCALE_CONTRAST={0}"' -f $env:SD_DOWNSCALE_CONTRAST)
        ('set "SD_NATIVE_RESOLUTION={0}"' -f $env:SD_NATIVE_RESOLUTION)
        ('echo [%DATE% %TIME%] launch (breakaway) SD_OFFLOAD=%SD_OFFLOAD% SD_SKIP_T5=%SD_SKIP_T5%>>"{0}"' -f $outLog)
        ('"{0}" {1} {2} 1>>"{3}" 2>>"{4}"' -f $PythonExe, $ServerScript, $ExtraArgs, $outLog, $errLog)
    )
    Set-Content -LiteralPath $launchCmd -Value $lines -Encoding ASCII

    # VBS: hidden (0), don't wait (False) - independent of parent console/Ctrl+C.
    # In VBS, "" inside a "..." string is one literal quote. Paths use normal `\`.
    $vbs = @(
        'Set sh = CreateObject("WScript.Shell")'
        ('sh.CurrentDirectory = "{0}"' -f $WorkDir)
        ('sh.Run "cmd.exe /d /c ""{0}""", 0, False' -f $launchCmd)
    ) -join "`r`n"
    Set-Content -LiteralPath $launchVbs -Value $vbs -Encoding ASCII

    $wscript = Join-Path $env:SystemRoot "System32\wscript.exe"
    if (-not (Test-Path -LiteralPath $wscript)) {
        $wscript = "wscript.exe"
    }

    # Start wscript breakaway; do not inherit this PowerShell's console group.
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $wscript
    $psi.Arguments = "`"$launchVbs`""
    $psi.WorkingDirectory = $WorkDir
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true

    # CREATE_NEW_PROCESS_GROUP | CREATE_BREAKAWAY_FROM_JOB | CREATE_NO_WINDOW | DETACHED_PROCESS
    # ProcessStartInfo doesn't expose all flags; use native CreateProcess when possible.
    $startedPid = 0
    try {
        if (-not ("SdNativeDetach" -as [type])) {
            Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class SdNativeDetach {
  public const uint CREATE_NEW_PROCESS_GROUP = 0x00000200;
  public const uint CREATE_BREAKAWAY_FROM_JOB = 0x01000000;
  public const uint DETACHED_PROCESS = 0x00000008;
  public const uint CREATE_NO_WINDOW = 0x08000000;
  [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
  public struct STARTUPINFO {
    public int cb; public IntPtr lpReserved; public IntPtr lpDesktop; public IntPtr lpTitle;
    public int dwX, dwY, dwXSize, dwYSize, dwXCountChars, dwYCountChars, dwFillAttribute, dwFlags;
    public short wShowWindow, cbReserved2; public IntPtr lpReserved2, hStdInput, hStdOutput, hStdError;
  }
  [StructLayout(LayoutKind.Sequential)]
  public struct PROCESS_INFORMATION {
    public IntPtr hProcess; public IntPtr hThread; public uint dwProcessId; public uint dwThreadId;
  }
  [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
  public static extern bool CreateProcess(
    string lpApplicationName, string lpCommandLine, IntPtr lpProcessAttributes,
    IntPtr lpThreadAttributes, bool bInheritHandles, uint dwCreationFlags,
    IntPtr lpEnvironment, string lpCurrentDirectory,
    ref STARTUPINFO lpStartupInfo, out PROCESS_INFORMATION lpProcessInformation);
  [DllImport("kernel32.dll", SetLastError = true)]
  public static extern bool CloseHandle(IntPtr hObject);
}
"@
        }
        $cmdLine = "`"$wscript`" `"$launchVbs`""
        $flagsList = @(
            ([SdNativeDetach]::CREATE_NO_WINDOW -bor [SdNativeDetach]::CREATE_NEW_PROCESS_GROUP -bor [SdNativeDetach]::CREATE_BREAKAWAY_FROM_JOB -bor [SdNativeDetach]::DETACHED_PROCESS),
            ([SdNativeDetach]::CREATE_NO_WINDOW -bor [SdNativeDetach]::CREATE_NEW_PROCESS_GROUP -bor [SdNativeDetach]::DETACHED_PROCESS),
            ([SdNativeDetach]::CREATE_NO_WINDOW -bor [SdNativeDetach]::CREATE_NEW_PROCESS_GROUP)
        )
        foreach ($flags in $flagsList) {
            $si = New-Object SdNativeDetach+STARTUPINFO
            $si.cb = [Runtime.InteropServices.Marshal]::SizeOf([type][SdNativeDetach+STARTUPINFO])
            $pi = New-Object SdNativeDetach+PROCESS_INFORMATION
            $ok = [SdNativeDetach]::CreateProcess(
                $null, $cmdLine, [IntPtr]::Zero, [IntPtr]::Zero, $false,
                $flags, [IntPtr]::Zero, $WorkDir, [ref]$si, [ref]$pi
            )
            if ($ok) {
                $startedPid = [int]$pi.dwProcessId
                [void][SdNativeDetach]::CloseHandle($pi.hThread)
                [void][SdNativeDetach]::CloseHandle($pi.hProcess)
                break
            }
        }
    } catch {
        Write-Host "Native detach unavailable ($($_.Exception.Message)); falling back to Start-Process wscript" -ForegroundColor Yellow
    }

    if ($startedPid -le 0) {
        $proc = New-Object System.Diagnostics.Process
        $proc.StartInfo = $psi
        if (-not $proc.Start()) { throw "Failed to start breakaway SD launcher (wscript)" }
        $startedPid = $proc.Id
    }

    # Resolve actual python PID once it appears (wscript exits almost immediately).
    $pythonPid = 0
    $deadline = (Get-Date).AddSeconds(8)
    while ((Get-Date) -lt $deadline) {
        try {
            $conns = Get-NetTCPConnection -LocalPort 1338 -State Listen -ErrorAction SilentlyContinue
            if ($conns) {
                $pythonPid = @($conns | Select-Object -ExpandProperty OwningProcess -Unique)[0]
                if ($pythonPid) { break }
            }
        } catch { }
        $py = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -match 'server\.py' -and $_.CommandLine -match '1338' } |
            Select-Object -First 1
        if ($py) { $pythonPid = [int]$py.ProcessId; break }
        Start-Sleep -Milliseconds 400
    }
    try {
        $storePid = if ($pythonPid -gt 0) { $pythonPid } else { $startedPid }
        Set-Content -LiteralPath $pidFile -Value $storePid -Encoding ASCII
    } catch { }

    Write-Host "Launched breakaway SD server (wscript/native detach; python PID $(if ($pythonPid) { $pythonPid } else { 'pending' }))" -ForegroundColor Gray
    Write-Host "Logs: $outLog" -ForegroundColor Gray
    Write-Host 'Safe to close this window - Ctrl+C / console close will NOT kill SD.' -ForegroundColor DarkGreen
}

function Wait-ForSdReady {
    param([int]$TimeoutSec = 90)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-SdResponding) { return $true }
        Start-Sleep -Seconds 2
    }
    return $false
}

if ($Force -and (Test-SdAlreadyRunning)) {
    Write-Host "[Force] Stopping existing listener on port 1338..." -ForegroundColor Yellow
    Stop-SdListeners
}

if (-not $Force -and (Test-SdAlreadyRunning)) {
    if (Test-AamtSdServer) {
        Write-Host "[OK] AAMT SD server already listening on port 1338; not starting a second one." -ForegroundColor Green
        Write-Host "     Use -Force to replace it (stops the old listener first)." -ForegroundColor Gray
        exit 0
    }
    Write-Host "[WARN] Port 1338 is a foreign SD process (not aamt-1338). Replacing it." -ForegroundColor Yellow
    Write-Host "       (Starfield SFMAG sd_server.py commonly steals this port.)" -ForegroundColor DarkYellow
    Stop-SdListeners
}

$pythonCmd = Resolve-CudaPython
if (-not $pythonCmd) {
    Write-Host "ERROR: No Python with CUDA-enabled PyTorch found." -ForegroundColor Red
    Write-Host "       Expected CUDA build at $preferredCudaPython" -ForegroundColor Yellow
    Write-Host "       Refusing CPU-only torch (would place the model in system RAM)." -ForegroundColor Yellow
    exit 1
}

function Sync-SharedSdServer {
    <# Keep E:\tools\sd3.5\sd3.5\server.py in sync with Tools\Shared\sd35_server.py. #>
    if (-not (Test-Path -LiteralPath $sharedSdServer)) {
        return
    }
    New-Item -ItemType Directory -Path $sd35Path -Force | Out-Null
    Copy-Item -LiteralPath $sharedSdServer -Destination $sd35Server -Force
    Write-Host "Synced Shared\sd35_server.py -> $sd35Server" -ForegroundColor Gray
}

Sync-SharedSdServer

if (Test-Path $sd35Server) {
    Write-Host "Starting SD3.5 API Server..." -ForegroundColor Cyan
    Write-Host "Server: $sd35Server" -ForegroundColor Gray
    Write-Host ""

    # VRAM-first defaults for RTX 2080 Ti 11GB + SD3.5 Medium.
    # RAM spill is overflow/CPU only; rebalance reclaims VRAM when free returns.
    if (-not $env:SD_OFFLOAD) { $env:SD_OFFLOAD = "gpu" }
    if (-not $env:SD_ALLOW_NONADMIN) { $env:SD_ALLOW_NONADMIN = "1" }
    if (-not $env:SD_PRELOAD) { $env:SD_PRELOAD = "1" }
    # Auto-exit when idle so the GPU is free for games / Ollama. Generators
    # should start this script on demand; do not leave SD running "just in case".
    if (-not $env:SD_IDLE_SHUTDOWN_SEC) { $env:SD_IDLE_SHUTDOWN_SEC = "180" }
    if (-not $env:SD_MAX_SEQ_LEN) { $env:SD_MAX_SEQ_LEN = "256" }
    if (-not $env:SD_GPU_DIRECT_MIN_FREE_GB) { $env:SD_GPU_DIRECT_MIN_FREE_GB = "8" }
    if (-not $env:SD_GPU_SHARED_MIN_FREE_GB) { $env:SD_GPU_SHARED_MIN_FREE_GB = "3.5" }
    # Rebuild-on-rebalance can leak commit on Windows; keep off unless debugging.
    if (-not $env:SD_REBALANCE) { $env:SD_REBALANCE = "0" }
    # 0.5 was wrong on 11GB: SD3.5 Medium fills VRAM so free≈0, and every generate
    # immediately spilled to CPU (~2 min/step). Only spill on real OOM / other apps.
    if (-not $env:SD_HEADROOM_GB) { $env:SD_HEADROOM_GB = "0" }
    # Default CLIP-only on GPU. T5+model_cpu_offload ballooned pagefile (~167GB private /
    # ~210GB commit on 64GB RAM). Opt-in: SD_ALLOW_T5_RAM=1 SD_SKIP_T5=0 SD_MAX_CPU_GB=24
    if (-not $env:SD_SKIP_T5) { $env:SD_SKIP_T5 = "1" }
    if (-not $env:SD_MAX_CPU_GB) { $env:SD_MAX_CPU_GB = "24" }
    if (-not $env:SD_MAX_GPU_GB) { $env:SD_MAX_GPU_GB = "10" }
    if (-not $env:SD_ALLOW_T5_RAM) { $env:SD_ALLOW_T5_RAM = "0" }
    # Delivery sizes may be tiny (32/64); server plans inference like ToME
    # (floor 512, supersample 1.5, icon steps 24) then stepwise Lanczos-downscales.
    if (-not $env:SD_MIN_DIM) { $env:SD_MIN_DIM = "32" }
    if (-not $env:SD_MAX_DIM) { $env:SD_MAX_DIM = "1536" }
    if (-not $env:SD_DIM_STEP) { $env:SD_DIM_STEP = "16" }
    if (-not $env:SD_QUALITY_FLOOR) { $env:SD_QUALITY_FLOOR = "512" }
    if (-not $env:SD_SUPER_SAMPLE) { $env:SD_SUPER_SAMPLE = "1.5" }
    if (-not $env:SD_ICON_STEPS) { $env:SD_ICON_STEPS = "24" }
    if (-not $env:SD_DOWNSCALE_SHARPNESS) { $env:SD_DOWNSCALE_SHARPNESS = "1.1" }
    if (-not $env:SD_DOWNSCALE_CONTRAST) { $env:SD_DOWNSCALE_CONTRAST = "1.05" }
    if (-not $env:SD_NATIVE_RESOLUTION) { $env:SD_NATIVE_RESOLUTION = "0" }

    # Avoid ">" inside double-quoted Write-Host strings (PowerShell treats it as redirect).
    Write-Host ('SD_OFFLOAD={0}  (VRAM-first; free >= {1}GB -> gpu)' -f $env:SD_OFFLOAD, $env:SD_GPU_DIRECT_MIN_FREE_GB) -ForegroundColor Gray
    Write-Host ('SD_REBALANCE={0}  SD_HEADROOM_GB={1}  SD_SKIP_T5={2}' -f $env:SD_REBALANCE, $env:SD_HEADROOM_GB, $env:SD_SKIP_T5) -ForegroundColor Gray
    Write-Host ('SD_ALLOW_T5_RAM={0}  SD_MAX_CPU_GB={1}  SD_MAX_GPU_GB={2}' -f $env:SD_ALLOW_T5_RAM, $env:SD_MAX_CPU_GB, $env:SD_MAX_GPU_GB) -ForegroundColor Gray
    Write-Host ('SD_PRELOAD={0}  SD_MAX_SEQ_LEN={1}  SD_IDLE_SHUTDOWN_SEC={2}' -f $env:SD_PRELOAD, $env:SD_MAX_SEQ_LEN, $env:SD_IDLE_SHUTDOWN_SEC) -ForegroundColor Gray
    Write-Host ('SD_MIN_DIM={0}  SD_MAX_DIM={1}  SD_DIM_STEP={2}' -f $env:SD_MIN_DIM, $env:SD_MAX_DIM, $env:SD_DIM_STEP) -ForegroundColor Gray
    Write-Host ('SD_QUALITY_FLOOR={0}  SD_SUPER_SAMPLE={1}  SD_ICON_STEPS={2}  (ToME-style low-res plan)' -f $env:SD_QUALITY_FLOOR, $env:SD_SUPER_SAMPLE, $env:SD_ICON_STEPS) -ForegroundColor Gray
    Write-Host ('SD_DOWNSCALE_SHARPNESS={0}  SD_DOWNSCALE_CONTRAST={1}  SD_NATIVE_RESOLUTION={2}' -f $env:SD_DOWNSCALE_SHARPNESS, $env:SD_DOWNSCALE_CONTRAST, $env:SD_NATIVE_RESOLUTION) -ForegroundColor Gray

    Start-DetachedServer -PythonExe $pythonCmd -WorkDir $sd35Path

    Write-Host ('Waiting up to {0} s for http://127.0.0.1:1338/ping ...' -f $WaitSec) -ForegroundColor Cyan
    if (Wait-ForSdReady -TimeoutSec $WaitSec) {
        Write-Host '[OK] SD3.5 server is up on port 1338.' -ForegroundColor Green
        if ([int]$env:SD_IDLE_SHUTDOWN_SEC -gt 0) {
            Write-Host ("      Auto-stops after {0}s with no generations (SD_IDLE_SHUTDOWN_SEC=0 to keep alive)." -f $env:SD_IDLE_SHUTDOWN_SEC) -ForegroundColor DarkYellow
        }
        Write-Host '      Stop now: Stop-StableDiffusionServer.ps1  (or GET http://127.0.0.1:1338/shutdown)' -ForegroundColor Gray
        exit 0
    }

    Write-Host ('[ERROR] Server did not respond within {0} s (server process was NOT killed).' -f $WaitSec) -ForegroundColor Red
    $errLog = Join-Path $sd35Path "sd_server.err.log"
    if (Test-Path $errLog) {
        Write-Host ('Last lines of {0}:' -f $errLog) -ForegroundColor Yellow
        Get-Content $errLog -Tail 15 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
    }
    exit 1
}

Write-Host "SD3.5 server not found, trying legacy server..." -ForegroundColor Yellow

$availableDrives = Get-PSDrive -PSProvider FileSystem | Where-Object {
    $_.Name -ne "C" -and $_.Name -ne "D" -and $_.Free -gt 10GB
} | Sort-Object Free -Descending

if ($availableDrives) {
    $bestDrive = $availableDrives[0].Name
    $modelPath = "${bestDrive}:\StableDiffusion\Models"
    if (-not (Test-Path $modelPath)) {
        New-Item -ItemType Directory -Path $modelPath -Force | Out-Null
    }
    $env:HF_HOME = $modelPath
    Write-Host "Model storage: $env:HF_HOME" -ForegroundColor Gray
}

$serverStarted = $false
$commonPaths = @(
    "E:\tools\stable-diffusion-api-server",
    "$env:USERPROFILE\stable-diffusion-api-server"
)

foreach ($path in $commonPaths) {
    $serverPy = Join-Path $path "server.py"
    if (Test-Path $serverPy) {
        Write-Host "Found legacy server at: $serverPy" -ForegroundColor Green
        Start-DetachedServer -PythonExe $pythonCmd -WorkDir $path -ExtraArgs ""
        $serverStarted = $true
        break
    }
}

if (-not $serverStarted) {
    Write-Host "ERROR: No SD server found!" -ForegroundColor Red
    Write-Host "Run Setup-SD35Server.ps1 to install SD3.5" -ForegroundColor Yellow
    exit 1
}
