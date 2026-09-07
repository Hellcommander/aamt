# Quick test script to verify design draft generation works
# Usage: .\Test-DesignDraftGeneration.ps1

Write-Host "Testing SD3 Design Draft Generation..." -ForegroundColor Cyan
Write-Host ""

# Import SD3 module
$sharedPath = Join-Path (Split-Path -Parent $PSScriptRoot) "Shared"
$sdModule = Join-Path $sharedPath "StableDiffusionIntegration.psm1"

if (-not (Test-Path $sdModule)) {
    Write-Host "[ERROR] StableDiffusionIntegration.psm1 not found at: $sdModule" -ForegroundColor Red
    exit 1
}

Import-Module $sdModule -DisableNameChecking -Force

# Test 1: Check if functions are available
Write-Host "Test 1: Checking function availability..." -ForegroundColor Yellow
$functions = @("Find-LocalStableDiffusionServer", "Test-StableDiffusionConnection", "Generate-AssetImageWithSD3")
foreach ($func in $functions) {
    if (Get-Command $func -ErrorAction SilentlyContinue) {
        Write-Host "  [OK] $func is available" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $func is NOT available" -ForegroundColor Red
    }
}
Write-Host ""

# Test 2: Test server detection
Write-Host "Test 2: Testing server detection..." -ForegroundColor Yellow
try {
    $serverInfo = Find-LocalStableDiffusionServer
    if ($serverInfo -is [hashtable]) {
        Write-Host "  [OK] Server detected (hashtable)" -ForegroundColor Green
        if ($serverInfo.ContainsKey("BaseUrl")) {
            Write-Host "    BaseUrl: $($serverInfo.BaseUrl)" -ForegroundColor Gray
        }
        if ($serverInfo.ContainsKey("ApiEndpoint")) {
            Write-Host "    ApiEndpoint: $($serverInfo.ApiEndpoint)" -ForegroundColor Gray
        }
    } elseif ($serverInfo -eq $null) {
        Write-Host "  [WARN] No server detected (returned null)" -ForegroundColor Yellow
    } else {
        Write-Host "  [WARN] Unexpected return type: $($serverInfo.GetType().Name)" -ForegroundColor Yellow
        Write-Host "    Value: $serverInfo" -ForegroundColor Gray
    }
} catch {
    Write-Host "  [ERROR] Server detection failed: $_" -ForegroundColor Red
}
Write-Host ""

# Test 3: Test connection
Write-Host "Test 3: Testing connection..." -ForegroundColor Yellow
try {
    $connected = Test-StableDiffusionConnection
    if ($connected) {
        Write-Host "  [OK] Connection test passed" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Connection test failed" -ForegroundColor Red
    }
} catch {
    Write-Host "  [ERROR] Connection test error: $_" -ForegroundColor Red
}
Write-Host ""

# Test 4: Check module variables (if accessible)
Write-Host "Test 4: Checking module state..." -ForegroundColor Yellow
Write-Host "  Note: Module variables are private, checking via function calls" -ForegroundColor Gray
Write-Host ""

# Test 5: Try a simple generation (if server is available)
Write-Host "Test 5: Testing actual generation (optional)..." -ForegroundColor Yellow
Write-Host "  Run with -TestGeneration to test actual image generation" -ForegroundColor Gray
if ($args -contains "-TestGeneration") {
    $testOutput = Join-Path $env:TEMP "test_design_draft.png"
    Write-Host "  Attempting to generate test image to: $testOutput" -ForegroundColor Gray
    
    try {
        if (Get-Command Generate-AssetImageWithSD3 -ErrorAction SilentlyContinue) {
            $result = Generate-AssetImageWithSD3 `
                -Prompt "Test image, simple red circle on white background" `
                -OutputPath $testOutput `
                -Width 512 `
                -Height 512 `
                -Steps 10 `
                -GuidanceScale 7.0 `
                -EnhanceWithOllama:$false `
                -AutoStartServer:$false
            
            if ($result -and (Test-Path $testOutput)) {
                Write-Host "  [OK] Test image generated successfully!" -ForegroundColor Green
                Write-Host "    File: $testOutput" -ForegroundColor Gray
                Write-Host "    Size: $((Get-Item $testOutput).Length) bytes" -ForegroundColor Gray
            } else {
                Write-Host "  [FAIL] Test image generation failed" -ForegroundColor Red
            }
        } else {
            Write-Host "  [ERROR] Generate-AssetImageWithSD3 not available" -ForegroundColor Red
        }
    } catch {
        Write-Host "  [ERROR] Generation test failed: $_" -ForegroundColor Red
        Write-Host "    Exception type: $($_.Exception.GetType().Name)" -ForegroundColor Gray
    }
}
Write-Host ""

Write-Host "Test complete!" -ForegroundColor Cyan
