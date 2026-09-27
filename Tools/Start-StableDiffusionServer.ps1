# Start-StableDiffusionServer.ps1
# AI-Assisted Modding Tools (AAMT)
# Starts SD3.5 API server (updated to use SD3.5 from GitHub)

# SD3.5 installation path
$sd35Path = "E:\tools\sd3.5\sd3.5"
$sd35Server = Join-Path $sd35Path "server.py"

# Check if SD3.5 server exists
if (Test-Path $sd35Server) {
    Write-Host "Starting SD3.5 API Server..." -ForegroundColor Cyan
    Write-Host "Server: $sd35Server" -ForegroundColor Gray
    Write-Host ""
    
    # Check if Python is available
    $pythonCmd = $null
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonCmd = "python"
    } elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
        $pythonCmd = "python3"
    } else {
        Write-Host "❌ ERROR: Python not found!" -ForegroundColor Red
        exit 1
    }
    
    Push-Location $sd35Path
    & $pythonCmd server.py --host localhost --port 1337
    Pop-Location
    exit 0
}

# Fallback to old server detection (from original script)
Write-Host "SD3.5 server not found, trying legacy server..." -ForegroundColor Yellow

# Determine best drive for model storage (not C: or D:)
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

# Try to find legacy server
$serverStarted = $false
$commonPaths = @(
    "E:\tools\stable-diffusion-api-server",
    "$env:USERPROFILE\stable-diffusion-api-server"
)

foreach ($path in $commonPaths) {
    $serverPy = Join-Path $path "server.py"
    if (Test-Path $serverPy) {
        Write-Host "Found legacy server at: $serverPy" -ForegroundColor Green
        Push-Location $path
        & $pythonCmd server.py
        Pop-Location
        $serverStarted = $true
        break
    }
}

if (-not $serverStarted) {
    Write-Host "❌ ERROR: No SD server found!" -ForegroundColor Red
    Write-Host "Run Setup-SD35Server.ps1 to install SD3.5" -ForegroundColor Yellow
    exit 1
}
