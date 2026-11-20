<#
.SYNOPSIS
    Watches the NVIDIA card and, when the driver loses it, stops the toolkit's GPU queue and tries to restart the
    graphics device.
.DESCRIPTION
    Every -IntervalSec seconds it runs `nvidia-smi -L`. When that reports the card lost ("GPU is lost", no device,
    or nvidia-smi hanging):
      1. It writes %LOCALAPPDATA%\AamtGpuHub\gpu_lost.json. The toolkit's GPU hub (Common\gpu_hub.py) refuses every
         GPU job while that file exists, so queued jobs stop instead of starting on a dead card.
      2. If it runs elevated (as the scheduled task Install-GpuWatchdog.ps1 sets up), it restarts the NVIDIA display
         device with `pnputil /restart-device` and checks again. At most -MaxRestarts tries per loss, -RetryWaitSec
         apart.
      3. When the card answers again it deletes the marker, and GPU jobs can run again.
    A card that "fell off the bus" (2026-11-20, during a UniRig job) often does not come back without a reboot; the
    marker then stays until the reboot (the task starts again at logon and clears it once the card is there).
    Log: %LOCALAPPDATA%\AamtGpuHub\gpu_watchdog.log. Manual reset of the display without any of this: Win+Ctrl+Shift+B.
.PARAMETER Once
    Check once and exit (0 = present, 3 = lost). Restarts the device only with -Restart.
.PARAMETER DryRun
    Never restart the device; log what would be done.
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File GpuWatchdog.ps1 -Once
#>
[CmdletBinding()]
param(
    [int]$IntervalSec = 30,
    [int]$MaxRestarts = 2,
    [int]$RetryWaitSec = 60,
    [switch]$Once,
    [switch]$Restart,
    [switch]$DryRun
)

$HubDir = if ($env:AAMT_GPU_HUB_DIR) { $env:AAMT_GPU_HUB_DIR } else { Join-Path $env:LOCALAPPDATA 'AamtGpuHub' }
New-Item -ItemType Directory -Force -Path $HubDir | Out-Null
$Marker = Join-Path $HubDir 'gpu_lost.json'
$LogFile = Join-Path $HubDir 'gpu_watchdog.log'

function Write-Log([string]$Text) {
    $line = '{0:yyyy-MM-dd HH:mm:ss} {1}' -f (Get-Date), $Text
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
    Write-Host $line
}

function Test-Elevated {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    (New-Object Security.Principal.WindowsPrincipal $id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-NvidiaSmi {
    $cmd = Get-Command nvidia-smi -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $p = Join-Path $env:SystemRoot 'System32\nvidia-smi.exe'
    if (Test-Path $p) { return $p }
    return $null
}

# Returns @{ Ok = bool; Detail = string }.
function Test-Gpu {
    $smi = Get-NvidiaSmi
    if (-not $smi) { return @{ Ok = $true; Detail = 'nvidia-smi not found (nothing to watch)' } }
    $out = Join-Path $HubDir 'smi_out.txt'
    $p = Start-Process -FilePath $smi -ArgumentList '-L' -NoNewWindow -PassThru -RedirectStandardOutput $out -RedirectStandardError "$out.err"
    $null = $p.Handle  # without the cached handle, ExitCode stays empty after the process ends
    if (-not $p.WaitForExit(20000)) {
        try { $p.Kill() } catch { }
        return @{ Ok = $false; Detail = 'nvidia-smi hung for 20 s (driver not answering)' }
    }
    $text = ((Get-Content $out -Raw -ErrorAction SilentlyContinue) + (Get-Content "$out.err" -Raw -ErrorAction SilentlyContinue)).Trim()
    if ($p.ExitCode -ne 0 -or $text -notmatch 'GPU \d' -or $text -match 'lost') {
        $first = ($text -split "`r?`n")[0]
        if (-not $first) { $first = "nvidia-smi exit $($p.ExitCode)" }
        return @{ Ok = $false; Detail = $first }
    }
    return @{ Ok = $true; Detail = ($text -split "`r?`n")[0] }
}

function Set-Marker([string]$Detail, [int]$Attempts, [string]$Since) {
    @{ since = $Since; detail = $Detail; attempts = $Attempts; by = 'GpuWatchdog.ps1' } |
        ConvertTo-Json | Set-Content -Path $Marker -Encoding UTF8
}

function Restart-NvidiaDevice {
    $devs = Get-PnpDevice -Class Display -ErrorAction SilentlyContinue | Where-Object { $_.FriendlyName -match 'NVIDIA' }
    if (-not $devs) { Write-Log 'no NVIDIA display device found to restart'; return $false }
    foreach ($d in $devs) {
        if ($DryRun) { Write-Log "dry run: would run pnputil /restart-device `"$($d.InstanceId)`" ($($d.FriendlyName), status $($d.Status))"; continue }
        Write-Log "restarting $($d.FriendlyName) ($($d.InstanceId), status $($d.Status))"
        $r = & pnputil.exe /restart-device "$($d.InstanceId)" 2>&1 | Out-String
        Write-Log ("pnputil: " + ($r -replace '\s+', ' ').Trim())
    }
    return $true
}

$elevated = Test-Elevated

if ($Once) {
    $s = Test-Gpu
    if ($s.Ok) {
        if (Test-Path $Marker) { Remove-Item $Marker -Force; Write-Log "card present again ($($s.Detail)); marker cleared" }
        Write-Host "GPU present: $($s.Detail)"; exit 0
    }
    Write-Log "GPU LOST: $($s.Detail)"
    if (-not (Test-Path $Marker)) { Set-Marker $s.Detail 0 ('{0:yyyy-MM-dd HH:mm:ss}' -f (Get-Date)) }
    if ($Restart) {
        if ($elevated -or $DryRun) { Restart-NvidiaDevice | Out-Null } else { Write-Log 'not elevated: cannot restart the device' }
    }
    exit 3
}

Write-Log "watchdog started (pid $PID, elevated $elevated, every $IntervalSec s, dry run $([bool]$DryRun))"
$attempts = 0
$since = $null
$lastTry = [datetime]::MinValue
while ($true) {
    $s = Test-Gpu
    if ($s.Ok) {
        if (Test-Path $Marker) {
            Remove-Item $Marker -Force
            Write-Log "card present again ($($s.Detail)); marker cleared, GPU jobs can run"
        }
        $attempts = 0; $since = $null
    } else {
        if (-not $since) {
            $since = '{0:yyyy-MM-dd HH:mm:ss}' -f (Get-Date)
            Write-Log "GPU LOST: $($s.Detail) - GPU jobs blocked"
        }
        Set-Marker $s.Detail $attempts $since
        if (($elevated -or $DryRun) -and $attempts -lt $MaxRestarts -and ((Get-Date) - $lastTry).TotalSeconds -ge $RetryWaitSec) {
            $attempts++; $lastTry = Get-Date
            Write-Log "restart attempt $attempts of $MaxRestarts"
            Restart-NvidiaDevice | Out-Null
            Start-Sleep -Seconds 20
            continue
        } elseif (-not $elevated -and $attempts -eq 0) {
            Write-Log 'not elevated: cannot restart the device; reboot to recover'
            $attempts = $MaxRestarts
        } elseif ($attempts -ge $MaxRestarts -and $attempts -lt 100) {
            Write-Log 'restarts did not bring the card back: reboot the PC to recover it'
            $attempts = 100
        }
    }
    Start-Sleep -Seconds $IntervalSec
}
