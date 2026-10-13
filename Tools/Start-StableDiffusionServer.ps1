# Start-StableDiffusionServer.ps1
# AI-Assisted Modding Tools (AAMT)
# Starts the SD3.5 API server (Shared\sd35_server.py) on 127.0.0.1 AND ::1, port 1338.
#
# Parameters used by sd_server_lifecycle.py / StableDiffusionIntegration.psm1:
#   -NoStatusGui   accepted for compatibility (no GUI is started)
#   -WaitSec       accepted for compatibility (the caller does its own waiting)
#   -Port          default 1338
#   -BindHost      localhost (default) = IPv4 + IPv6 loopback; or one literal address

param(
    [switch]$NoStatusGui,
    [int]$WaitSec = 0,
    [int]$Port = 1338,
    [string]$BindHost = "localhost"
)

$ErrorActionPreference = "Stop"

# SD3.5 installation path (override with AAMT_SD_HOME)
$sd35Path = "E:\tools\sd3.5\sd3.5"
if ($env:AAMT_SD_HOME) { $sd35Path = $env:AAMT_SD_HOME }
$sd35Server = Join-Path $sd35Path "server.py"

# Canonical source: Tools\Shared\sd35_server.py (this script lives in Tools\)
$canonical = Join-Path $PSScriptRoot "Shared\sd35_server.py"

function Test-AamtServerUp {
    param([int]$TestPort)
    foreach ($h in @("127.0.0.1", "[::1]")) {
        try {
            $resp = Invoke-WebRequest -Uri "http://${h}:${TestPort}/ping" -UseBasicParsing -TimeoutSec 4 -ErrorAction Stop
            if ($resp.Content -match '"version"\s*:\s*"aamt-1338') { return $true }
        } catch {
            # try next address family
        }
    }
    return $false
}

# Already running? Do not start a second copy on the same port.
if (Test-AamtServerUp -TestPort $Port) {
    Write-Host "SD3.5 server is already running on port $Port." -ForegroundColor Green
    exit 0
}

# Sync the canonical server into the install dir (the E:\tools copy is NOT the source of truth).
if (Test-Path -LiteralPath $canonical) {
    if (-not (Test-Path -LiteralPath $sd35Path)) {
        New-Item -ItemType Directory -Path $sd35Path -Force | Out-Null
    }
    $needCopy = $true
    if (Test-Path -LiteralPath $sd35Server) {
        $needCopy = ((Get-FileHash -LiteralPath $canonical).Hash -ne (Get-FileHash -LiteralPath $sd35Server).Hash)
    }
    if ($needCopy) {
        Copy-Item -LiteralPath $canonical -Destination $sd35Server -Force
        Write-Host "Synced sd35_server.py -> $sd35Server" -ForegroundColor Gray
    }
} elseif (-not (Test-Path -LiteralPath $sd35Server)) {
    Write-Host "ERROR: no SD3.5 server found." -ForegroundColor Red
    Write-Host "  Expected canonical copy: $canonical" -ForegroundColor Yellow
    Write-Host "  or installed copy:       $sd35Server" -ForegroundColor Yellow
    exit 1
}

# Python
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
} else {
    Write-Host "ERROR: Python not found!" -ForegroundColor Red
    exit 1
}

Write-Host "Starting SD3.5 API Server..." -ForegroundColor Cyan
Write-Host "Server: $sd35Server" -ForegroundColor Gray
Write-Host "Listen: $BindHost (port $Port)" -ForegroundColor Gray
Write-Host ""

$env:PYTHONUNBUFFERED = "1"
$ErrorActionPreference = "Continue"
Push-Location $sd35Path
try {
    & $pythonCmd server.py --host $BindHost --port $Port
    $code = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $code
