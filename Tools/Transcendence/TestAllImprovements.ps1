#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Comprehensive test script for Space Whale Asset Generator improvements
    
.DESCRIPTION
    Tests all recent improvements:
    - GUI rendering (colors, borders, progress bars)
    - Error handling in scripts
    - Image preview loading
    - Script validation
#>

$ErrorActionPreference = "Continue"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Space Whale Improvements Test Suite" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$testResults = @{
    Passed = 0
    Failed = 0
    Skipped = 0
}

function Test-Passed {
    param([string]$TestName)
    Write-Host "  ✓ PASS: $TestName" -ForegroundColor Green
    $script:testResults.Passed++
}

function Test-Failed {
    param([string]$TestName, [string]$Reason = "")
    Write-Host "  ✗ FAIL: $TestName" -ForegroundColor Red
    if ($Reason) {
        Write-Host "      Reason: $Reason" -ForegroundColor Gray
    }
    $script:testResults.Failed++
}

function Test-Skipped {
    param([string]$TestName, [string]$Reason = "")
    Write-Host "  ⊘ SKIP: $TestName" -ForegroundColor Yellow
    if ($Reason) {
        Write-Host "      Reason: $Reason" -ForegroundColor Gray
    }
    $script:testResults.Skipped++
}

# Test 1: Check required files exist
Write-Host "Test 1: File Existence Check" -ForegroundColor Yellow
$requiredFiles = @(
    "AssetGeneratorControlRoom_Monitor.ps1",
    "blender_space_whale_120_facings.py",
    "transcendence_space_whale_exporter.py",
    "SpaceWhale120FacingsGenerator.ps1"
)

$allFilesExist = $true
foreach ($file in $requiredFiles) {
    $path = Join-Path $PSScriptRoot $file
    if (Test-Path $path) {
        Test-Passed "File exists: $file"
    } else {
        Test-Failed "File exists: $file" "File not found at $path"
        $allFilesExist = $false
    }
}
Write-Host ""

# Test 2: Check PowerShell syntax
Write-Host "Test 2: PowerShell Script Syntax" -ForegroundColor Yellow
$psScripts = @(
    "AssetGeneratorControlRoom_Monitor.ps1",
    "SpaceWhale120FacingsGenerator.ps1"
)

foreach ($script in $psScripts) {
    $path = Join-Path $PSScriptRoot $script
    try {
        $null = [System.Management.Automation.PSParser]::Tokenize((Get-Content $path -Raw), [ref]$null)
        Test-Passed "Syntax check: $script"
    } catch {
        Test-Failed "Syntax check: $script" $_.Exception.Message
    }
}
Write-Host ""

# Test 3: Check Python syntax
Write-Host "Test 3: Python Script Syntax" -ForegroundColor Yellow
$pyScripts = @(
    "blender_space_whale_120_facings.py",
    "transcendence_space_whale_exporter.py"
)

foreach ($script in $pyScripts) {
    $path = Join-Path $PSScriptRoot $script
    try {
        $python = Get-Command python -ErrorAction SilentlyContinue
        if ($python) {
            $result = python -m py_compile $path 2>&1
            if ($LASTEXITCODE -eq 0) {
                Test-Passed "Syntax check: $script"
            } else {
                Test-Failed "Syntax check: $script" ($result -join "`n")
            }
        } else {
            Test-Skipped "Syntax check: $script" "Python not found in PATH"
        }
    } catch {
        Test-Failed "Syntax check: $script" $_.Exception.Message
    }
}
Write-Host ""

# Test 4: Check for required imports in Python scripts
Write-Host "Test 4: Python Import Validation" -ForegroundColor Yellow
$blenderScript = Join-Path $PSScriptRoot "blender_space_whale_120_facings.py"
if (Test-Path $blenderScript) {
    $content = Get-Content $blenderScript -Raw
    if ($content -match "from pathlib import Path") {
        Test-Passed "Path import in blender script"
    } else {
        Test-Failed "Path import in blender script" "Missing 'from pathlib import Path'"
    }
    
    if ($content -match "import sys") {
        Test-Passed "sys import in blender script"
    } else {
        Test-Failed "sys import in blender script" "Missing 'import sys'"
    }
}
Write-Host ""

# Test 5: Check error handling in scripts
Write-Host "Test 5: Error Handling Validation" -ForegroundColor Yellow
$blenderScript = Join-Path $PSScriptRoot "blender_space_whale_120_facings.py"
if (Test-Path $blenderScript) {
    $content = Get-Content $blenderScript -Raw
    if ($content -match "try:" -and $content -match "except") {
        Test-Passed "Error handling in blender script"
    } else {
        Test-Failed "Error handling in blender script" "Missing try-except blocks"
    }
}

$xmlScript = Join-Path $PSScriptRoot "transcendence_space_whale_exporter.py"
if (Test-Path $xmlScript) {
    $content = Get-Content $xmlScript -Raw
    if ($content -match "try:" -and $content -match "except") {
        Test-Passed "Error handling in XML exporter"
    } else {
        Test-Failed "Error handling in XML exporter" "Missing try-except blocks"
    }
}

$psMonitor = Join-Path $PSScriptRoot "AssetGeneratorControlRoom_Monitor.ps1"
if (Test-Path $psMonitor) {
    $content = Get-Content $psMonitor -Raw
    $hasTry = $content -match 'try\s*\{'
    $hasCatch = $content -match 'catch\s*\{'
    if ($hasTry -or $hasCatch) {
        Test-Passed "Error handling in monitor script"
    } else {
        Test-Failed "Error handling in monitor script" "Missing try-catch blocks"
    }
}
Write-Host ""

# Test 6: Check WPF Application initialization
Write-Host "Test 6: WPF Application Initialization" -ForegroundColor Yellow
$monitorScript = Join-Path $PSScriptRoot "AssetGeneratorControlRoom_Monitor.ps1"
if (Test-Path $monitorScript) {
    $content = Get-Content $monitorScript -Raw
    if ($content -match "System\.Windows\.Application" -and $content -match "WindowStartupLocation") {
        Test-Passed "WPF Application initialization"
    } else {
        Test-Failed "WPF Application initialization" "Missing Application or WindowStartupLocation"
    }
    
    if ($content -match "AllowsTransparency\s*=" -or $content -match "WindowStyle") {
        Test-Passed "Window properties set"
    } else {
        Test-Failed "Window properties set" "Missing window property settings"
    }
}
Write-Host ""

# Test 7: Check progress bar binding
Write-Host "Test 7: Progress Bar Data Binding" -ForegroundColor Yellow
$monitorScript = Join-Path $PSScriptRoot "AssetGeneratorControlRoom_Monitor.ps1"
if (Test-Path $monitorScript) {
    $content = Get-Content $monitorScript -Raw
    if ($content -match 'Value="\{Binding Percent\}"' -or $content -match 'Value=\{Binding Percent\}') {
        Test-Passed "Progress bar Value binding"
    } else {
        Test-Failed "Progress bar Value binding" "Missing Value binding to Percent"
    }
    
    if ($content -match "Foreground.*#FF66ccff" -or $content -match "Foreground.*#66ccff") {
        Test-Passed "Progress bar styling (cyan color)"
    } else {
        Test-Failed "Progress bar styling" "Missing cyan foreground color"
    }
}
Write-Host ""

# Test 8: Check image loading function
Write-Host "Test 8: Image Preview Loading" -ForegroundColor Yellow
$monitorScript = Join-Path $PSScriptRoot "AssetGeneratorControlRoom_Monitor.ps1"
if (Test-Path $monitorScript) {
    $content = Get-Content $monitorScript -Raw
    if ($content -match "function Load-PreviewImage") {
        Test-Passed "Load-PreviewImage function exists"
    } else {
        Test-Failed "Load-PreviewImage function" "Function not found"
    }
    
    if ($content -match "CacheOption.*OnLoad") {
        Test-Passed "Image cache option set correctly"
    } else {
        Test-Failed "Image cache option" "Missing CacheOption=OnLoad"
    }
    
    if (($content -match "Freeze\(\)") -or ($content -match "\.Freeze\(\)")) {
        Test-Passed "Image Freeze method called"
    } else {
        Test-Failed "Image Freeze method" "Missing Freeze call"
    }
    
    if ($content -match "Test-Path.*filePath" -or $content -match "if.*-not.*Test-Path") {
        Test-Passed "File existence check in Load-PreviewImage"
    } else {
        Test-Failed "File existence check" "Missing file path validation"
    }
}
Write-Host ""

# Test 9: Check validation in scripts
Write-Host "Test 9: Input Validation" -ForegroundColor Yellow
$blenderScript = Join-Path $PSScriptRoot "blender_space_whale_120_facings.py"
if (Test-Path $blenderScript) {
    $content = Get-Content $blenderScript -Raw
    if ($content -match "if.*columns.*<.*1" -or $content -match "if.*rows.*<.*1") {
        Test-Passed "Column/row validation in blender script"
    } else {
        Test-Failed "Column/row validation" "Missing validation for columns/rows"
    }
}

$xmlScript = Join-Path $PSScriptRoot "transcendence_space_whale_exporter.py"
if (Test-Path $xmlScript) {
    $content = Get-Content $xmlScript -Raw
    if ($content -match "if.*export.*not in" -or $content -match "if.*unid.*not in") {
        Test-Passed "Required field validation in XML exporter"
    } else {
        Test-Failed "Required field validation" "Missing validation for required fields"
    }
}
Write-Host ""

# Test 10: Check error messages
Write-Host "Test 10: Error Message Quality" -ForegroundColor Yellow
$blenderScript = Join-Path $PSScriptRoot "blender_space_whale_120_facings.py"
if (Test-Path $blenderScript) {
    $content = Get-Content $blenderScript -Raw
    if ($content -match "FileNotFoundError" -or $content -match "registry file not found") {
        Test-Passed "Descriptive error messages in blender script"
    } else {
        Test-Failed "Error messages" "Missing descriptive error messages"
    }
}

$xmlScript = Join-Path $PSScriptRoot "transcendence_space_whale_exporter.py"
if (Test-Path $xmlScript) {
    $content = Get-Content $xmlScript -Raw
    if ($content -match "ValueError" -or $content -match "missing.*field") {
        Test-Passed "Descriptive error messages in XML exporter"
    } else {
        Test-Failed "Error messages" "Missing descriptive error messages"
    }
}
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Test Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Passed:  $($testResults.Passed)" -ForegroundColor Green
Write-Host "  Failed:  $($testResults.Failed)" -ForegroundColor $(if ($testResults.Failed -eq 0) { "Green" } else { "Red" })
Write-Host "  Skipped: $($testResults.Skipped)" -ForegroundColor Yellow
Write-Host ""

$total = $testResults.Passed + $testResults.Failed + $testResults.Skipped
$passRate = if ($total -gt 0) { [math]::Round(($testResults.Passed / $total) * 100, 1) } else { 0 }
Write-Host "  Pass Rate: $passRate%" -ForegroundColor $(if ($passRate -ge 90) { "Green" } elseif ($passRate -ge 70) { "Yellow" } else { "Red" })
Write-Host ""

if ($testResults.Failed -eq 0) {
    Write-Host "✓ All tests passed!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "✗ Some tests failed. Review output above." -ForegroundColor Red
    exit 1
}

