#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Setup script for Python frame generator pipeline

.DESCRIPTION
    Installs Python dependencies and verifies setup.
#>

$ErrorActionPreference = "Stop"

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Python Frame Generator Pipeline Setup" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "[STEP 1] Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  [OK] Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  [FAIL] Python not found!" -ForegroundColor Red
    Write-Host "    Install Python 3.8+ from https://www.python.org/" -ForegroundColor Yellow
    exit 1
}

# Check pip
Write-Host ""
Write-Host "[STEP 2] Checking pip..." -ForegroundColor Yellow
try {
    $pipVersion = pip --version 2>&1
    Write-Host "  [OK] pip found: $pipVersion" -ForegroundColor Green
} catch {
    Write-Host "  [FAIL] pip not found!" -ForegroundColor Red
    Write-Host "    pip should come with Python installation" -ForegroundColor Yellow
    exit 1
}

# Install dependencies
Write-Host ""
Write-Host "[STEP 3] Installing Python dependencies..." -ForegroundColor Yellow
$requirementsFile = Join-Path $PSScriptRoot "requirements.txt"
if (Test-Path $requirementsFile) {
    pip install -r $requirementsFile
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Failed to install dependencies" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  [WARN] requirements.txt not found" -ForegroundColor Yellow
}

# Verify imports
Write-Host ""
Write-Host "[STEP 4] Verifying Python modules..." -ForegroundColor Yellow
$testScript = @"
import sys
errors = []
try:
    import PIL
    print('  [OK] Pillow (PIL)')
except ImportError as e:
    errors.append('Pillow: ' + str(e))
    print('  [FAIL] Pillow (PIL)')

try:
    import rectpack
    print('  [OK] rectpack')
except ImportError as e:
    errors.append('rectpack: ' + str(e))
    print('  [FAIL] rectpack')

try:
    import requests
    print('  [OK] requests')
except ImportError as e:
    errors.append('requests: ' + str(e))
    print('  [FAIL] requests')

if errors:
    print('')
    print('  [ERROR] Missing modules. Run: pip install -r requirements.txt')
    sys.exit(1)
else:
    print('')
    print('  [OK] All modules available')
    sys.exit(0)
"@

$testScript | python
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [FAIL] Module verification failed" -ForegroundColor Red
    exit 1
}

# Test orchestrator
Write-Host ""
Write-Host "[STEP 5] Testing orchestrator..." -ForegroundColor Yellow
$orchestratorScript = Join-Path $PSScriptRoot "frame_generator_orchestrator.py"
if (Test-Path $orchestratorScript) {
    python $orchestratorScript --help | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Orchestrator script is valid" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Orchestrator script has issues" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [WARN] Orchestrator script not found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Test with: python frame_generator_orchestrator.py --job example_job.json" -ForegroundColor Gray
Write-Host "  2. Integrate with PowerShell: .\integrate_with_powershell.ps1 -AssetName test" -ForegroundColor Gray
Write-Host ""
