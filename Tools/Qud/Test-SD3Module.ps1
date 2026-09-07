# Simple test to verify SD3 module loads and HTTP/2 works
param([switch]$TestGeneration)

$ErrorActionPreference = "Stop"

Write-Host "Testing SD3 Module..." -ForegroundColor Cyan
Write-Host ""

# Import module
$sharedPath = Join-Path (Split-Path -Parent $PSScriptRoot) "Shared"
$sdModule = Join-Path $sharedPath "StableDiffusionIntegration.psm1"

if (-not (Test-Path $sdModule)) {
    Write-Host "[ERROR] Module not found: $sdModule" -ForegroundColor Red
    exit 1
}

Write-Host "Importing module: $sdModule" -ForegroundColor Gray
try {
    Import-Module $sdModule -DisableNameChecking -Force -ErrorAction Stop
    Write-Host "[OK] Module imported successfully" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to import module: $_" -ForegroundColor Red
    Write-Host "Error details: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test functions
Write-Host ""
Write-Host "Testing functions..." -ForegroundColor Yellow
$functions = @("Find-LocalStableDiffusionServer", "Test-StableDiffusionConnection", "Generate-AssetImageWithSD3")
foreach ($func in $functions) {
    if (Get-Command $func -ErrorAction SilentlyContinue) {
        Write-Host "  [OK] $func" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $func" -ForegroundColor Red
    }
}

# Test server detection
Write-Host ""
Write-Host "Testing server detection..." -ForegroundColor Yellow
try {
    $server = Find-LocalStableDiffusionServer
    if ($server) {
        Write-Host "  [OK] Server found: $($server.BaseUrl)" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] No server detected" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [ERROR] Server detection failed: $_" -ForegroundColor Red
}

# Test connection
Write-Host ""
Write-Host "Testing connection..." -ForegroundColor Yellow
try {
    $connected = Test-StableDiffusionConnection
    if ($connected) {
        Write-Host "  [OK] Connection successful" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Connection failed" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [ERROR] Connection test failed: $_" -ForegroundColor Red
}

# Test generation if requested
if ($TestGeneration) {
    Write-Host ""
    Write-Host "Testing image generation..." -ForegroundColor Yellow
    $testFile = Join-Path $env:TEMP "test_sd3_$(Get-Date -Format 'yyyyMMddHHmmss').png"
    try {
        $result = Generate-AssetImageWithSD3 `
            -Prompt "Simple test: red circle on white background" `
            -OutputPath $testFile `
            -Width 512 `
            -Height 512 `
            -Steps 10 `
            -GuidanceScale 7.0 `
            -EnhanceWithOllama:$false `
            -AutoStartServer:$false
        
        if ($result -and (Test-Path $testFile)) {
            Write-Host "  [OK] Image generated: $testFile" -ForegroundColor Green
            Write-Host "    Size: $((Get-Item $testFile).Length) bytes" -ForegroundColor Gray
        } else {
            Write-Host "  [FAIL] Generation failed" -ForegroundColor Red
        }
    } catch {
        Write-Host "  [ERROR] Generation error: $_" -ForegroundColor Red
        if ($_.Exception.Message -match "426|Upgrade Required") {
            Write-Host "    This is an HTTP/2 upgrade error - the fix should handle this" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "Test complete!" -ForegroundColor Cyan
