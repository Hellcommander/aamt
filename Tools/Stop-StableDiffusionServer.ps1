# Stop-StableDiffusionServer.ps1
# Stops the local SD3.5 API server (port 1338, or -Port / AAMT_SD_PORT) and frees GPU VRAM.
#
# Prefer this (or GET http://127.0.0.1:1338/shutdown) when generation is done.
# The server also auto-exits after SD_IDLE_SHUTDOWN_SEC (default 180) with no
# generations - /ping polls do not keep it alive.

param(
    [int]$Port = 0
)

$ErrorActionPreference = "Continue"
$toolsRoot = $PSScriptRoot
if ($Port -le 0) {
    $Port = 1338
    $parsedPort = 0
    if ($env:AAMT_SD_PORT -and [int]::TryParse($env:AAMT_SD_PORT, [ref]$parsedPort) -and $parsedPort -gt 0 -and $parsedPort -lt 65536) {
        $Port = $parsedPort
    }
}

# Launched from PowerShell 7 (pwsh), Windows PowerShell 5.1 inherits a PSModulePath listing the
# PowerShell 7 module folders, so Invoke-WebRequest / Get-NetTCPConnection fail to load (and the
# try/catch blocks below would hide it). Restore the stock 5.1 module path first.
if ($PSVersionTable.PSEdition -eq 'Desktop' -and $env:PSModulePath -match '\\PowerShell\\Modules|microsoft\.powershell_') {
    $stock = @(
        (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'WindowsPowerShell\Modules'),
        (Join-Path $env:ProgramFiles 'WindowsPowerShell\Modules'),
        (Join-Path $PSHOME 'Modules')
    )
    $machine = [Environment]::GetEnvironmentVariable('PSModulePath', 'Machine') -split ';'
    $env:PSModulePath = (($stock + $machine) | Where-Object { $_ } | Select-Object -Unique) -join ';'
}

# Prefer graceful HTTP shutdown (unloads model cleanly)
# The server listens on 127.0.0.1 and ::1; ask whichever answers.
foreach ($bindAddr in @("127.0.0.1", "[::1]")) {
    try {
        $resp = Invoke-WebRequest -Uri "http://${bindAddr}:${Port}/shutdown" -Method Get -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
        Write-Host "Requested graceful shutdown via /shutdown on $bindAddr ($($resp.StatusCode))" -ForegroundColor Cyan
        Start-Sleep -Seconds 2
        break
    } catch {
        # Not listening on this family, or already stopping - try the next one
    }
}

$qudStop = Join-Path $toolsRoot "Qud\Stop-SdServer.ps1"
# The Qud helper only knows port 1338 (it also stops the hidden PowerShell parent).
if ($Port -eq 1338 -and (Test-Path -LiteralPath $qudStop)) {
    & $qudStop
} else {
    $pids = @()
    try {
        $pids += @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique)
    } catch {}
    try {
        foreach ($line in (netstat -ano | Select-String ":${Port}\s+.*LISTENING")) {
            if ($line -match '\s(\d+)\s*$') { $pids += [int]$Matches[1] }
        }
    } catch {}
    $pids = $pids | Where-Object { $_ -and $_ -gt 0 } | Select-Object -Unique
    if (-not $pids) {
        Write-Host "No SD listener on port $Port" -ForegroundColor Green
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
$stillUp = $false
foreach ($bindAddr in @("127.0.0.1", "[::1]")) {
    try {
        $null = Invoke-WebRequest -Uri "http://${bindAddr}:${Port}/ping" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        $stillUp = $true
    } catch {
        # nothing answering on this address
    }
}
# A hung server can hold the port without answering /ping: check the listener too.
$leftPids = @()
try {
    $leftPids = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ -gt 0 })
} catch {}
if ($stillUp -or $leftPids.Count -gt 0) {
    Write-Host "WARN: port $Port is still in use (answers /ping: $stillUp; listener PID(s): $($leftPids -join ', '))" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] SD server stopped (port $Port free)" -ForegroundColor Green
exit 0
