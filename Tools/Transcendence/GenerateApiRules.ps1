<#
.SYNOPSIS
  Generate or update API rules from game source
  
.DESCRIPTION
  This script scans the game's source files and generates an api_rules.json
  file that the mod tools use for validation.
  
  API versions are auto-detected from the source folder. Any new 
  TranscendenceDev-integration-API## folders will be automatically recognized.
  
  DRAG-AND-DROP SUPPORT:
  You can drag-and-drop a TranscendenceDev-integration-API## folder onto this
  script (or the GenerateApiRules.bat wrapper) to automatically detect and
  generate rules for that API version.
  
.EXAMPLE
  .\GenerateApiRules.ps1                    # Uses default API version (57)
  .\GenerateApiRules.ps1 -ApiVersion 59     # Uses API 59
  .\GenerateApiRules.ps1 -ApiVersion 61     # Uses API 61 (if available)
  .\GenerateApiRules.ps1 -Latest            # Uses latest available API
  .\GenerateApiRules.ps1 -Compare           # Compare all available versions
  .\GenerateApiRules.ps1 -ListVersions      # Show available API versions
  
.EXAMPLE
  # Drag-and-drop: Drag a folder onto GenerateApiRules.bat or .ps1
  # Example: Drag "TranscendenceDev-integration-API60" folder onto script
  # The script will auto-detect API 60 and generate rules for it
#>

param(
    [Parameter(Position=0)]
    [string]$DroppedPath = $null,  # For drag-and-drop support
    
    [int]$ApiVersion = 0,  # 0 = use default
    
    [switch]$Latest,
    [switch]$Compare,
    [switch]$ListVersions,
    
    [string[]]$SourcePaths = $null
)

# ============================================================
# DRAG-AND-DROP SUPPORT
# ============================================================
# If a folder/file is dropped on this script, detect API version from path
# Check both $DroppedPath parameter and $args for compatibility
    $droppedItem = if ($DroppedPath) { $DroppedPath } elseif ($args.Count -gt 0) { $args[0] } else { $null }

if ($droppedItem -and $ApiVersion -eq 0 -and -not $Latest -and -not $Compare -and -not $ListVersions) {
    # Resolve the path (handle quoted paths from drag-and-drop)
    $droppedPath = $droppedItem.Trim('"', "'")
    
    if ($droppedPath) {
        if (Test-Path $droppedPath) {
            $resolvedPath = Resolve-Path $droppedPath -ErrorAction SilentlyContinue
            if ($resolvedPath) {
                $item = Get-Item $resolvedPath
                
                # Check if it's a directory matching the pattern
                if ($item.PSIsContainer) {
                    $folderName = $item.Name
                    $folderPath = $item.FullName
                }
                else {
                    # If it's a file, use the parent directory
                    $folderName = $item.Directory.Name
                    $folderPath = $item.Directory.FullName
                }
                
                # Check if folder name matches TranscendenceDev-integration-API## pattern
                if ($folderName -match 'TranscendenceDev-integration-API(\d+)') {
                    $detectedVersion = [int]$matches[1]
                    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
                    Write-Host "  DRAG-AND-DROP DETECTED" -ForegroundColor Cyan
                    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
                    Write-Host ""
                    Write-Host "Detected API version: $detectedVersion" -ForegroundColor Green
                    Write-Host "From folder: $folderName" -ForegroundColor Gray
                    Write-Host "Path: $folderPath" -ForegroundColor Gray
                    Write-Host ""
                    Write-Host "Generating API rules for API $detectedVersion..." -ForegroundColor Cyan
                    Write-Host ""
                    
                    # Set the API version to the detected one
                    $ApiVersion = $detectedVersion
                }
                # Also check if the path contains the pattern (in case folder was renamed)
                elseif ($folderPath -match 'TranscendenceDev-integration-API(\d+)') {
                    $detectedVersion = [int]$matches[1]
                    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
                    Write-Host "  DRAG-AND-DROP DETECTED" -ForegroundColor Cyan
                    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
                    Write-Host ""
                    Write-Host "Detected API version: $detectedVersion" -ForegroundColor Green
                    Write-Host "From path: $folderPath" -ForegroundColor Gray
                    Write-Host ""
                    Write-Host "Generating API rules for API $detectedVersion..." -ForegroundColor Cyan
                    Write-Host ""
                    
                    $ApiVersion = $detectedVersion
                }
                else {
                    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
                    Write-Host "  DRAG-AND-DROP DETECTED (but not an API folder)" -ForegroundColor Yellow
                    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
                    Write-Host ""
                    Write-Host "Dropped item: $folderName" -ForegroundColor Gray
                    Write-Host "Path: $folderPath" -ForegroundColor Gray
                    Write-Host ""
                    Write-Host "Expected folder name pattern: TranscendenceDev-integration-API##" -ForegroundColor Yellow
                    Write-Host "Example: TranscendenceDev-integration-API60" -ForegroundColor Yellow
                    Write-Host ""
                    Write-Host "Falling back to default API version..." -ForegroundColor Gray
                    Write-Host ""
                }
            }
        }
    }
}

# Load the API rules module
$apiRulesModule = Join-Path $PSScriptRoot 'TranscendenceModTools_ApiRules.ps1'
if (Test-Path $apiRulesModule) {
    . $apiRulesModule
}
else {
    Write-Host "ERROR: API Rules module not found: $apiRulesModule" -ForegroundColor Red
    exit 1
}

# List versions mode
if ($ListVersions) {
    Show-AvailableApiVersions
    exit 0
}

# Determine which API version to use
if ($Latest) {
    $ApiVersion = Get-LatestApiVersion
    Write-Host "Using latest API version: $ApiVersion" -ForegroundColor Cyan
}
elseif ($ApiVersion -eq 0) {
    $ApiVersion = $script:DefaultApiVersion
}

# If API version was detected from drag-and-drop but not in auto-detected list,
# try to register it manually
if ($ApiVersion -gt 0 -and -not $script:ApiVersions.ContainsKey($ApiVersion)) {
    $expectedFolder = "TranscendenceDev-integration-API$ApiVersion"
    $expectedPath = Join-Path $script:SourceBaseDir $expectedFolder
    $transCorePath = Join-Path $expectedPath "Transcendence\TransCore"
    
    if (Test-Path $transCorePath) {
        Write-Host "Registering API $ApiVersion from: $expectedPath" -ForegroundColor Cyan
        $script:ApiVersions[$ApiVersion] = @{
            Name = "API $ApiVersion (2.x dev)"
            SourcePaths = @(
                $transCorePath,
                (Join-Path $script:SourceBaseDir "Transcendence_Source")
            )
            FolderName = $expectedFolder
        }
    }
    else {
        Write-Host "ERROR: API version $ApiVersion not found" -ForegroundColor Red
        Write-Host "Expected path: $transCorePath" -ForegroundColor Yellow
        Write-Host ""
        Show-AvailableApiVersions
        exit 1
    }
}

# Validate version exists (final check)
if ($ApiVersion -gt 0 -and -not $script:ApiVersions.ContainsKey($ApiVersion)) {
    Write-Host "ERROR: API version $ApiVersion not found" -ForegroundColor Red
    Write-Host ""
    Show-AvailableApiVersions
    exit 1
}

# Compare mode: show differences between all available API versions
if ($Compare) {
    $sortedVersions = @($script:ApiVersions.Keys) | Sort-Object
    
    if ($sortedVersions.Count -lt 2) {
        Write-Host "Need at least 2 API versions to compare" -ForegroundColor Yellow
        exit 0
    }
    
    Write-Host "Comparing all available API versions..." -ForegroundColor Cyan
    Write-Host ""
    
    # Generate rules for all versions
    $allRules = @{}
    foreach ($ver in $sortedVersions) {
        Write-Host "=== $($script:ApiVersions[$ver].Name) ===" -ForegroundColor Yellow
        $allRules[$ver] = Update-ApiRules -ApiVersion $ver -OutputPath "$PSScriptRoot\api_rules_$ver.json"
        Write-Host ""
    }
    
    # Show comparison table
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  API VERSION COMPARISON" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    # Header
    $header = "                "
    foreach ($ver in $sortedVersions) {
        $header += "API $ver".PadLeft(10)
    }
    Write-Host $header -ForegroundColor White
    
    # Tags row
    $row = "  Tags:         "
    foreach ($ver in $sortedVersions) {
        $row += $allRules[$ver].Stats.TotalTags.ToString().PadLeft(10)
    }
    Write-Host $row -ForegroundColor Gray
    
    # Events row
    $row = "  Events:       "
    foreach ($ver in $sortedVersions) {
        $row += $allRules[$ver].Stats.TotalEvents.ToString().PadLeft(10)
    }
    Write-Host $row -ForegroundColor Gray
    
    # Functions row
    $row = "  Functions:    "
    foreach ($ver in $sortedVersions) {
        $row += $allRules[$ver].Stats.TotalFunctions.ToString().PadLeft(10)
    }
    Write-Host $row -ForegroundColor Gray
    
    # Entities row
    $row = "  Entities:     "
    foreach ($ver in $sortedVersions) {
        $row += $allRules[$ver].Stats.TotalEntities.ToString().PadLeft(10)
    }
    Write-Host $row -ForegroundColor Gray
    
    Write-Host ""
    
    # Show what's new in each version compared to previous
    for ($i = 1; $i -lt $sortedVersions.Count; $i++) {
        $prevVer = $sortedVersions[$i - 1]
        $currVer = $sortedVersions[$i]
        
        $prevFuncs = @($allRules[$prevVer].Functions.PSObject.Properties.Name)
        $currFuncs = @($allRules[$currVer].Functions.PSObject.Properties.Name)
        $newFuncs = $currFuncs | Where-Object { $prevFuncs -notcontains $_ }
        
        if ($newFuncs.Count -gt 0) {
            Write-Host "New in API $currVer (vs $prevVer): $($newFuncs.Count) functions" -ForegroundColor Green
            $newFuncs | Select-Object -First 10 | ForEach-Object { Write-Host "  + $_" -ForegroundColor Green }
            if ($newFuncs.Count -gt 10) {
                Write-Host "  ... and $($newFuncs.Count - 10) more" -ForegroundColor Gray
            }
            Write-Host ""
        }
    }
    
    Write-Host "Rule files saved:" -ForegroundColor Gray
    foreach ($ver in $sortedVersions) {
        Write-Host "  api_rules_$ver.json" -ForegroundColor Gray
    }
    
    exit 0
}

# Generate API rules for specified version
$outputPath = Join-Path $PSScriptRoot "api_rules.json"
$versionedPath = Join-Path $PSScriptRoot "api_rules_$ApiVersion.json"

if ($SourcePaths) {
    $result = Update-ApiRules -ApiVersion $ApiVersion -SourcePaths $SourcePaths -OutputPath $outputPath
}
else {
    $result = Update-ApiRules -ApiVersion $ApiVersion -OutputPath $outputPath
}

if ($result) {
    # Also save a versioned copy
    if (Test-Path $outputPath) {
        Copy-Item $outputPath $versionedPath -Force | Out-Null
    }
    
    Write-Host ""
    Write-Host "API rules generated successfully!" -ForegroundColor Green
    Write-Host "File: $outputPath" -ForegroundColor Gray
    Write-Host "Versioned: $versionedPath" -ForegroundColor Gray
    Write-Host "API Version: $ApiVersion" -ForegroundColor Gray
    Write-Host ""
    
    # Generate human-readable function list
    Write-Host "Generating function list..." -ForegroundColor Cyan
    try {
        $functionListPath = Join-Path $PSScriptRoot "FunctionList_API$ApiVersion.txt"
        $functionListScript = Join-Path $PSScriptRoot "GenerateFunctionList.ps1"
        
        if (Test-Path $functionListScript) {
            & $functionListScript -ApiVersion $ApiVersion -RulesPath $versionedPath -OutputPath $functionListPath | Out-Null
            Write-Host "Function list: $functionListPath" -ForegroundColor Gray
        }
        else {
            Write-Host "  (GenerateFunctionList.ps1 not found, skipping)" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "  (Function list generation failed: $_)" -ForegroundColor Yellow
    }
}
else {
    Write-Host "Failed to generate API rules" -ForegroundColor Red
    exit 1
}

