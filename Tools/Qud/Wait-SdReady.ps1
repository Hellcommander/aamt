# Wait until SD3.5 reports ready on port 1338 (or timeout).
param(
    [int]$TimeoutSec = 180,
    [string]$Url = "http://127.0.0.1:1338/ping"
)

$ErrorActionPreference = "Continue"
$deadline = (Get-Date).AddSeconds($TimeoutSec)

Write-Host "Waiting for SD3.5 ready at $Url (up to ${TimeoutSec}s)..." -ForegroundColor Cyan

while ((Get-Date) -lt $deadline) {
    try {
        $j = Invoke-RestMethod -Uri $Url -TimeoutSec 5
        $state = [string]$j.model_state
        $ready = $false
        if ($j.PSObject.Properties.Name -contains "ready") {
            $ready = [bool]$j.ready
        }
        if ($ready -or $state -eq "ready") {
            Write-Host "[OK] SD3.5 ready (state=$state, offload=$($j.offload))" -ForegroundColor Green
            exit 0
        }
        Write-Host "  state=$state (loading...)" -ForegroundColor Gray
    } catch {
        Write-Host "  waiting for ping..." -ForegroundColor Gray
    }
    Start-Sleep -Seconds 5
}

Write-Host "[WARN] SD3.5 not ready within ${TimeoutSec}s" -ForegroundColor Yellow
exit 1
