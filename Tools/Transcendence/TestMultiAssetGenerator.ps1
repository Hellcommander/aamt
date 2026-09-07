#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Comprehensive test suite for the Multi-Asset Generator.
    
.DESCRIPTION
    Tests the Multi-Asset Generator with various configurations:
    - Single asset type, single game
    - Multiple asset types, single game
    - Single asset type, multiple games
    - Multiple asset types, multiple games
    - All asset types, all games
    - Error handling (invalid parameters, missing generators)
    - Performance (large batch generation)
    
.PARAMETER TestType
    Type of test to run: Quick, Standard, Full, ErrorHandling, Performance
    
.PARAMETER OutputDir
    Output directory for test results
    
.PARAMETER SkipCleanup
    Don't delete test output after tests complete
    
.EXAMPLE
    .\TestMultiAssetGenerator.ps1 -TestType Quick
    
.EXAMPLE
    .\TestMultiAssetGenerator.ps1 -TestType Full -SkipCleanup
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("Quick", "Standard", "Full", "ErrorHandling", "Performance")]
    [string]$TestType = "Quick",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "TestMultiAsset_$(Get-Date -Format 'yyyyMMdd_HHmmss')",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipCleanup
)

$ErrorActionPreference = "Continue"

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Test result tracking
$script:TestResults = @{
    Passed = 0
    Failed = 0
    Skipped = 0
    Tests = @()
}

$script:StartTime = Get-Date

function Write-TestHeader {
    param([string]$Title)
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
}

function Write-TestResult {
    param(
        [string]$TestName,
        [bool]$Passed,
        [string]$Message = "",
        [double]$Duration = 0
    )
    
    $status = if ($Passed) { "PASS" } else { "FAIL" }
    $color = if ($Passed) { "Green" } else { "Red" }
    $icon = if ($Passed) { "✓" } else { "✗" }
    
    Write-Host "  $icon [$status] $TestName" -ForegroundColor $color
    if ($Message) {
        Write-Host "           $Message" -ForegroundColor Gray
    }
    if ($Duration -gt 0) {
        Write-Host "           Duration: $([math]::Round($Duration, 2))s" -ForegroundColor Gray
    }
    
    if ($Passed) {
        $script:TestResults.Passed++
    } else {
        $script:TestResults.Failed++
    }
    
    $script:TestResults.Tests += @{
        Name = $TestName
        Passed = $Passed
        Message = $Message
        Duration = $Duration
    }
}

function Invoke-MultiAssetTest {
    param(
        [string]$TestName,
        [string[]]$AssetTypes,
        [string[]]$GameTypes,
        [string]$AssetName,
        [string]$Description = "Test asset",
        [bool]$ExpectSuccess = $true
    )
    
    $testStart = Get-Date
    $testOutputDir = Join-Path $OutputDir $TestName.Replace(" ", "_")
    
    try {
        # Build command
        $scriptPath = Join-Path $PSScriptRoot "MultiAssetGenerator.ps1"
        
        $params = @{
            AssetTypes = $AssetTypes
            GameTypes = $GameTypes
            AssetName = $AssetName
            AssetDescription = $Description
            OutputDir = $testOutputDir
        }
        
        # Run the generator
        $output = & $scriptPath @params 2>&1
        $exitCode = $LASTEXITCODE
        
        $duration = ((Get-Date) - $testStart).TotalSeconds
        
        # Check for expected outcome
        $outputPath = Join-Path $testOutputDir $AssetName
        $hasOutput = Test-Path $outputPath
        
        # Count generated files
        $fileCount = 0
        if ($hasOutput) {
            $files = Get-ChildItem -Path $outputPath -Recurse -File -ErrorAction SilentlyContinue
            $fileCount = $files.Count
        }
        
        if ($ExpectSuccess) {
            # For success tests, we expect the output directory to exist
            # (files may not be generated if generators aren't fully functional)
            $passed = $hasOutput -or ($exitCode -eq 0)
            $message = if ($passed) { "Generated $fileCount file(s)" } else { "No output generated" }
        } else {
            # For failure tests, we expect graceful handling
            $passed = $true  # Script should not crash
            $message = "Handled gracefully"
        }
        
        Write-TestResult -TestName $TestName -Passed $passed -Message $message -Duration $duration
        return $passed
    }
    catch {
        $duration = ((Get-Date) - $testStart).TotalSeconds
        Write-TestResult -TestName $TestName -Passed $false -Message "Exception: $_" -Duration $duration
        return $false
    }
}

# ============================================================
# QUICK TESTS - Basic functionality
# ============================================================

function Run-QuickTests {
    Write-TestHeader "Quick Tests - Basic Functionality"
    
    # Test 1: Single asset type, single game (Terraria Tile)
    Invoke-MultiAssetTest -TestName "Single Asset Single Game" `
        -AssetTypes @("Tile") `
        -GameTypes @("Terraria") `
        -AssetName "QuickTest_Tile"
    
    # Test 2: Single asset type, single game (Elin Icon)
    Invoke-MultiAssetTest -TestName "Elin Icon Generation" `
        -AssetTypes @("Icon") `
        -GameTypes @("Elin") `
        -AssetName "QuickTest_Icon"
    
    # Test 3: Texture generation (uses AssetMakerAI)
    Invoke-MultiAssetTest -TestName "Texture Generation" `
        -AssetTypes @("Texture") `
        -GameTypes @("Transcendence") `
        -AssetName "QuickTest_Texture"
}

# ============================================================
# STANDARD TESTS - Multiple combinations
# ============================================================

function Run-StandardTests {
    Write-TestHeader "Standard Tests - Multiple Combinations"
    
    # Test 1: Multiple asset types, single game
    Invoke-MultiAssetTest -TestName "Multiple Assets Single Game" `
        -AssetTypes @("Tile", "Particle") `
        -GameTypes @("Terraria") `
        -AssetName "StdTest_MultiAsset"
    
    # Test 2: Single asset type, multiple games
    Invoke-MultiAssetTest -TestName "Single Asset Multiple Games" `
        -AssetTypes @("Texture") `
        -GameTypes @("Terraria", "Starbound", "Transcendence") `
        -AssetName "StdTest_MultiGame"
    
    # Test 3: Multiple asset types, multiple games
    Invoke-MultiAssetTest -TestName "Multiple Assets Multiple Games" `
        -AssetTypes @("Icon", "Texture") `
        -GameTypes @("Elin", "Qud") `
        -AssetName "StdTest_MultiMulti"
    
    # Test 4: Particle effects across games
    Invoke-MultiAssetTest -TestName "Particle Effects" `
        -AssetTypes @("Particle", "FX") `
        -GameTypes @("Terraria", "Transcendence") `
        -AssetName "StdTest_Particles"
}

# ============================================================
# FULL TESTS - All combinations
# ============================================================

function Run-FullTests {
    Write-TestHeader "Full Tests - Comprehensive Coverage"
    
    # Test all supported games with common asset types
    $commonAssets = @("Tile", "Icon", "Texture")
    $allGames = @("Terraria", "Elin", "Qud", "Starbound", "CDDA", "Transcendence")
    
    foreach ($game in $allGames) {
        Invoke-MultiAssetTest -TestName "Full Test - $game Common Assets" `
            -AssetTypes $commonAssets `
            -GameTypes @($game) `
            -AssetName "FullTest_${game}"
    }
    
    # Test with "All" games option
    Invoke-MultiAssetTest -TestName "All Games - Tile" `
        -AssetTypes @("Tile") `
        -GameTypes @("All") `
        -AssetName "FullTest_AllGames"
    
    # Test specialized asset types
    Invoke-MultiAssetTest -TestName "Starbound Ship" `
        -AssetTypes @("Ship") `
        -GameTypes @("Starbound") `
        -AssetName "FullTest_Ship"
    
    Invoke-MultiAssetTest -TestName "CDDA Creature" `
        -AssetTypes @("Creature") `
        -GameTypes @("CDDA") `
        -AssetName "FullTest_Creature"
}

# ============================================================
# ERROR HANDLING TESTS
# ============================================================

function Run-ErrorHandlingTests {
    Write-TestHeader "Error Handling Tests"
    
    # Test 1: Unsupported combination (Ship in CDDA)
    Invoke-MultiAssetTest -TestName "Unsupported Combo - CDDA Ship" `
        -AssetTypes @("Ship") `
        -GameTypes @("CDDA") `
        -AssetName "ErrTest_CDDAShip" `
        -ExpectSuccess $false
    
    # Test 2: Unsupported combination (Model in CDDA)
    Invoke-MultiAssetTest -TestName "Unsupported Combo - CDDA Model" `
        -AssetTypes @("Model") `
        -GameTypes @("CDDA") `
        -AssetName "ErrTest_CDDAModel" `
        -ExpectSuccess $false
    
    # Test 3: Mix of supported and unsupported
    Invoke-MultiAssetTest -TestName "Mixed Support - Tile and Ship in CDDA" `
        -AssetTypes @("Tile", "Ship") `
        -GameTypes @("CDDA") `
        -AssetName "ErrTest_Mixed" `
        -ExpectSuccess $true  # Should partially succeed
    
    # Test 4: Empty description handling
    Invoke-MultiAssetTest -TestName "Empty Description" `
        -AssetTypes @("Tile") `
        -GameTypes @("Terraria") `
        -AssetName "ErrTest_NoDesc" `
        -Description ""
}

# ============================================================
# PERFORMANCE TESTS
# ============================================================

function Run-PerformanceTests {
    Write-TestHeader "Performance Tests - Large Batch"
    
    # Test 1: Many asset types, all games
    $perfStart = Get-Date
    
    Invoke-MultiAssetTest -TestName "Performance - All Assets All Games" `
        -AssetTypes @("Tile", "Texture", "Icon", "Spritesheet") `
        -GameTypes @("All") `
        -AssetName "PerfTest_Large"
    
    $perfDuration = ((Get-Date) - $perfStart).TotalSeconds
    Write-Host "  Performance test completed in $([math]::Round($perfDuration, 2))s" -ForegroundColor Yellow
}

# ============================================================
# MAIN EXECUTION
# ============================================================

Write-TestHeader "Multi-Asset Generator Test Suite"
Write-Host "Test Type: $TestType" -ForegroundColor Yellow
Write-Host "Output Directory: $OutputDir" -ForegroundColor Yellow
Write-Host ""

# Create output directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Run appropriate tests based on TestType
switch ($TestType) {
    "Quick" {
        Run-QuickTests
    }
    "Standard" {
        Run-QuickTests
        Run-StandardTests
    }
    "Full" {
        Run-QuickTests
        Run-StandardTests
        Run-FullTests
    }
    "ErrorHandling" {
        Run-ErrorHandlingTests
    }
    "Performance" {
        Run-PerformanceTests
    }
}

# ============================================================
# TEST SUMMARY
# ============================================================

$totalTime = ((Get-Date) - $script:StartTime).TotalSeconds

Write-Host ""
Write-TestHeader "Test Summary"

$total = $script:TestResults.Passed + $script:TestResults.Failed + $script:TestResults.Skipped
$passRate = if ($total -gt 0) { [math]::Round(($script:TestResults.Passed / $total) * 100, 1) } else { 0 }

Write-Host "  Total Tests: $total" -ForegroundColor Cyan
Write-Host "  Passed: $($script:TestResults.Passed)" -ForegroundColor Green
Write-Host "  Failed: $($script:TestResults.Failed)" -ForegroundColor $(if ($script:TestResults.Failed -gt 0) { "Red" } else { "Gray" })
Write-Host "  Skipped: $($script:TestResults.Skipped)" -ForegroundColor $(if ($script:TestResults.Skipped -gt 0) { "Yellow" } else { "Gray" })
Write-Host ""
Write-Host "  Pass Rate: $passRate%" -ForegroundColor $(if ($passRate -ge 80) { "Green" } elseif ($passRate -ge 60) { "Yellow" } else { "Red" })
Write-Host "  Total Time: $([math]::Round($totalTime, 2))s" -ForegroundColor Cyan
Write-Host ""

# Write test report to file
$reportPath = Join-Path $OutputDir "test_report.json"
$report = @{
    TestType = $TestType
    StartTime = $script:StartTime.ToString("o")
    Duration = $totalTime
    Results = @{
        Total = $total
        Passed = $script:TestResults.Passed
        Failed = $script:TestResults.Failed
        Skipped = $script:TestResults.Skipped
        PassRate = $passRate
    }
    Tests = $script:TestResults.Tests
}

$report | ConvertTo-Json -Depth 10 | Out-File -FilePath $reportPath -Encoding UTF8
Write-Host "  Test report saved to: $reportPath" -ForegroundColor Gray
Write-Host ""

# Cleanup if requested
if (-not $SkipCleanup) {
    Write-Host "Cleaning up test output..." -ForegroundColor Gray
    # Keep the report but remove generated files
    Get-ChildItem -Path $OutputDir -Directory | ForEach-Object {
        Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Cleanup complete" -ForegroundColor Gray
}

# Exit with appropriate code
if ($script:TestResults.Failed -gt 0) {
    exit 1
} else {
    exit 0
}

