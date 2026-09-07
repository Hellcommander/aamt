# Test-SD3Detection.ps1
# Quick test script for Stable Diffusion 3 auto-detection

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "Stable Diffusion 3 Detection Test" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

# Import the integration module
$sdModule = Join-Path $PSScriptRoot "Shared\StableDiffusionIntegration.psm1"
if (-not (Test-Path $sdModule)) {
    Write-Host "[ERROR] StableDiffusionIntegration.psm1 not found at: $sdModule" -ForegroundColor Red
    exit 1
}

Import-Module $sdModule -Force -WarningAction SilentlyContinue

Write-Host "Testing Stable Diffusion server detection..." -ForegroundColor Yellow
Write-Host ""

# Try to find any running SD server
$detected = Find-LocalStableDiffusionServer -Verbose

if ($detected) {
    Write-Host "`n[SUCCESS] Detected running Stable Diffusion server!" -ForegroundColor Green
    Write-Host "  Setup: $($detected.Name)" -ForegroundColor Cyan
    Write-Host "  URL: $($detected.BaseUrl)" -ForegroundColor Cyan
    Write-Host "  Type: $($detected.Type)" -ForegroundColor Cyan
    Write-Host "  API Endpoint: $($detected.ApiEndpoint)" -ForegroundColor Cyan
    
    Write-Host "`nTesting connection..." -ForegroundColor Yellow
    if (Test-StableDiffusionConnection -Verbose) {
        Write-Host "`n[SUCCESS] Server is responding and ready!" -ForegroundColor Green
    } else {
        Write-Host "`n[WARNING] Server detected but not responding properly" -ForegroundColor Yellow
    }
} else {
    Write-Host "`n[INFO] No running Stable Diffusion server detected" -ForegroundColor Yellow
    Write-Host "`nPlease start one of the following:" -ForegroundColor Gray
    Write-Host "  - AUTOMATIC1111 WebUI (most common, port 7860)" -ForegroundColor Gray
    Write-Host "  - ComfyUI (port 8188)" -ForegroundColor Gray
    Write-Host "  - Stable Diffusion API Server (port 1337 or 8000)" -ForegroundColor Gray
    Write-Host "  - InvokeAI (port 9090)" -ForegroundColor Gray
}

Write-Host "`n============================================================`n" -ForegroundColor Cyan
