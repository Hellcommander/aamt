# Stop-StableDiffusionServer.ps1
# Stops the local SD3.5 API server on port 1338 and frees GPU VRAM.
#
# Prefer this (or GET http://127.0.0.1:1338/shutdown) when generation is done.
# The server also auto-exits after SD_IDLE_SHUTDOWN_SEC (default 180) with no
# generations — /ping polls do not keep it alive.

$ErrorActionPreference = "Continue"
$toolsRoot = $PSScriptRoot

# Prefer graceful HTTP shutdown (unloads model cleanly)
try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:1338/shutdown" -Method Get -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
    Write-Host "Requested graceful shutdown via /shutdown ($($resp.StatusCode))" -ForegroundColor Cyan
    Start-Sleep -Seconds 2
} catch {
    # Not running or already stopping — fall through to force kill
}

$qudStop = Join-Path $toolsRoot "Qud\Stop-SdServer.ps1"
if (Test-Path -LiteralPath $qudStop) {
    & $qudStop
} else {
    $pids = @()
    try {
        $pids += @(Get-NetTCPConnection -LocalPort 1338 -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique)
    } catch {}
    try {
        foreach ($line in (netstat -ano | Select-String ":1338\s+.*LISTENING")) {
            if ($line -match '\s(\d+)\s*$') { $pids += [int]$Matches[1] }
        }
    } catch {}
    $pids = $pids | Where-Object { $_ -and $_ -gt 0 } | Select-Object -Unique
    if (-not $pids) {
        Write-Host "No SD listener on port 1338" -ForegroundColor Green
        exit 0
    }
    foreach ($procId in $pids) {
        try {
            Stop-Process -Id $procId -Force -ErrorAction Stop
            Write-Host "Stopped PID $procId" -ForegroundColor Yellow
        } catch {
            Write-Host "WARN: could not stop PID $procId : $_" -ForegroundColor Red
        }
    }
}

Start-Sleep -Seconds 1
try {
    $null = Invoke-WebRequest -Uri "http://127.0.0.1:1338/ping" -TimeoutSec 1 -UseBasicParsing -ErrorAction Stop
    Write-Host "WARN: something still answers on :1338" -ForegroundColor Red
    exit 1
} catch {
    Write-Host "[OK] SD server stopped (port 1338 free)" -ForegroundColor Green
    exit 0
}
