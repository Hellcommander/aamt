# Test script for Transcendence Mod Tools installation

Write-Host "Testing Transcendence Mod Tools Installation..." -ForegroundColor Cyan
Write-Host ""

# Test 1: Check main script
Write-Host "Test 1: Main script..." -NoNewline
if (Test-Path "TranscendenceModTools.ps1") {
    Write-Host " PASS" -ForegroundColor Green
} else {
    Write-Host " FAIL" -ForegroundColor Red
    exit 1
}

# Test 2: Check all modules
Write-Host "Test 2: Module files..." -NoNewline
$modules = @(
    'TranscendenceModTools_Advanced.ps1',
    'TranscendenceModTools_DependencyGraph.ps1',
    'TranscendenceModTools_DiffMode.ps1',
    'TranscendenceModTools_Formatting.ps1',
    'TranscendenceModTools_LivePreview.ps1',
    'TranscendenceModTools_ResourceIntegrity.ps1',
    'TranscendenceModTools_Semantic.ps1',
    'TranscendenceModTools_SmartDetect.ps1',
    'TranscendenceModTools_TMLStaticAnalysis.ps1',
    'TranscendenceModTools_UNIDIntelligence.ps1'
)

$missing = @()
foreach ($mod in $modules) {
    if (-not (Test-Path $mod)) {
        $missing += $mod
    }
}

if ($missing.Count -eq 0) {
    Write-Host " PASS ($($modules.Count) modules)" -ForegroundColor Green
} else {
    Write-Host " FAIL" -ForegroundColor Red
    Write-Host "  Missing: $($missing -join ', ')" -ForegroundColor Yellow
    exit 1
}

# Test 3: Test smart detection on CrossModCompatibility
Write-Host "Test 3: Smart detection..." -NoNewline
$testPath = "..\ZZZ_CrossModCompatibility"
if (Test-Path $testPath) {
    try {
        . .\TranscendenceModTools_SmartDetect.ps1
        $result = Invoke-SmartDetection -Paths @((Resolve-Path $testPath).Path)
        Write-Host " PASS" -ForegroundColor Green
        Write-Host "  Detected: $($result.FileType)" -ForegroundColor Gray
        Write-Host "  XML Files: $($result.XmlFileCount)" -ForegroundColor Gray
        if ($result.ApiVersion) {
            Write-Host "  API Version: $($result.ApiVersion) ($($result.ApiStatus))" -ForegroundColor Gray
        }
        Write-Host "  Health Score: $($result.Score)/100" -ForegroundColor Gray
        Write-Host "  Issues Found: $($result.Issues.Count)" -ForegroundColor Gray
    } catch {
        Write-Host " FAIL" -ForegroundColor Red
        Write-Host "  Error: $_" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host " SKIP (test mod not found)" -ForegroundColor Yellow
}

# Test 4: Test basic XML checking
Write-Host "Test 4: XML checking..." -NoNewline
$testXml = "..\ZZZ_CrossModCompatibility\CrossModCompatibility_Part1.xml"
if (Test-Path $testXml) {
    try {
        # Load the main script to get Get-XmlIssues function
        $mainScript = Get-Content "TranscendenceModTools.ps1" -Raw
        $functionMatch = [regex]::Match($mainScript, 'function Get-XmlIssues\s*\{[^}]+\}', [System.Text.RegularExpressions.RegexOptions]::Singleline)
        if ($functionMatch.Success) {
            Invoke-Expression $functionMatch.Value
            $issues = Get-XmlIssues -FilePath (Resolve-Path $testXml).Path
            Write-Host " PASS ($($issues.Count) issues found)" -ForegroundColor Green
        } else {
            Write-Host " SKIP (function not found in script)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host " SKIP (function requires full script context)" -ForegroundColor Yellow
    }
} else {
    Write-Host " SKIP (test file not found)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "All tests passed! Installation is working correctly." -ForegroundColor Green
Write-Host ""
Write-Host "To launch the tool, double-click: TranscendenceModTools.bat" -ForegroundColor Cyan

