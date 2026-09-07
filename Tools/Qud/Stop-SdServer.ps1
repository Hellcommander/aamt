# Stop whatever is listening on SD3.5 port 1338 so Ollama can use the GPU.
$ErrorActionPreference = "Continue"
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
    Write-Host "No listener on port 1338"
    exit 0
}
foreach ($procId in $pids) {
    try {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue
        $parentId = if ($proc) { [int]$proc.ParentProcessId } else { 0 }
        foreach ($killId in @($parentId, $procId) | Where-Object { $_ -gt 0 } | Select-Object -Unique) {
            try {
                Stop-Process -Id $killId -Force -ErrorAction Stop
                Write-Host "Stopped PID $killId"
            } catch {
                Write-Host "WARN: could not stop PID $killId : $_"
            }
        }
    } catch {
        Write-Host "WARN: $_"
    }
}
Start-Sleep -Seconds 2
exit 0
