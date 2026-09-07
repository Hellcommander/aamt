#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Updates all PowerShell tools to use the shared AssetGenerationSettings.ps1 file.
    
.DESCRIPTION
    Scans all PowerShell scripts in the Tools directory and subdirectories,
    and adds code to load the shared settings file if they don't already have it.
#>

$ErrorActionPreference = "Stop"
$ToolsRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SettingsFile = "AssetGenerationSettings.ps1"
$SettingsPath = Join-Path $ToolsRoot $SettingsFile

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Update All Tools to Use Shared Settings" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $SettingsPath)) {
    Write-Host "Error: Settings file not found: $SettingsPath" -ForegroundColor Red
    exit 1
}

Write-Host "Settings file: $SettingsPath" -ForegroundColor Green
Write-Host "Scanning for PowerShell scripts..." -ForegroundColor Yellow
Write-Host ""

# Find all PowerShell scripts
$scripts = Get-ChildItem -Path $ToolsRoot -Filter "*.ps1" -Recurse | Where-Object {
    $_.FullName -notlike "*\obj\*" -and
    $_.FullName -notlike "*\bin\*" -and
    $_.Name -ne "AssetGenerationSettings.ps1" -and
    $_.Name -ne "Update-AllToolsToUseSharedSettings.ps1"
}

$updatedCount = 0
$skippedCount = 0
$errorCount = 0

foreach ($script in $scripts) {
    $content = Get-Content $script.FullName -Raw -ErrorAction SilentlyContinue
    if (-not $content) {
        $skippedCount++
        continue
    }
    
    # Check if script already loads settings
    if ($content -match "AssetGenerationSettings\.ps1" -or $content -match "Load.*Settings") {
        Write-Host "[SKIP] $($script.Name) (already uses shared settings)" -ForegroundColor Yellow
        $skippedCount++
        continue
    }
    
    # Check if script might benefit from shared settings
    $needsSettings = $false
    $reasons = @()
    
    if ($content -match "magick|ImageMagick|imageMagick") {
        $needsSettings = $true
        $reasons += "ImageMagick"
    }
    
    if ($content -match "OutputDir|output.*dir|assets") {
        $needsSettings = $true
        $reasons += "OutputDir"
    }
    
    if ($content -match "Ollama|ollama") {
        $needsSettings = $true
        $reasons += "Ollama"
    }
    
    if ($content -match "variants|Variants|animation.*frames|AnimationFrames") {
        $needsSettings = $true
        $reasons += "Defaults"
    }
    
    if (-not $needsSettings) {
        $skippedCount++
        continue
    }
    
    Write-Host "[UPDATE] $($script.Name)" -ForegroundColor Cyan
    Write-Host "         Reasons: $($reasons -join ', ')" -ForegroundColor Gray
    
    try {
        # Calculate path to settings file
        $scriptDir = Split-Path -Parent $script.FullName
        
        # Use absolute path calculation (more reliable)
        # Find Tools root by walking up directory tree
        $currentDir = $scriptDir
        $toolsRoot = $null
        
        while ($currentDir) {
            $settingsTest = Join-Path $currentDir $SettingsFile
            if (Test-Path $settingsTest) {
                $toolsRoot = $currentDir
                break
            }
            $parent = Split-Path -Parent $currentDir
            if ($parent -eq $currentDir) {
                break  # Reached filesystem root
            }
            $currentDir = $parent
        }
        
        if (-not $toolsRoot) {
            $toolsRoot = $ToolsRoot  # Fallback to known Tools root
        }
        
        # Calculate relative path from script directory to Tools root
        $relativePath = ""
        $currentDir = $scriptDir
        while ($currentDir -ne $toolsRoot -and $currentDir) {
            $relativePath = "..\" + $relativePath
            $parent = Split-Path -Parent $currentDir
            if ($parent -eq $currentDir) {
                break
            }
            $currentDir = $parent
        }
        
        if ([string]::IsNullOrEmpty($relativePath)) {
            $settingsRelativePath = $SettingsFile
        } else {
            $settingsRelativePath = $relativePath + $SettingsFile
        }
        
        # Find where to insert the settings load code
        # Look for $PSScriptRoot or $ErrorActionPreference near the top
        $lines = Get-Content $script.FullName
        $insertIndex = -1
        
        for ($i = 0; $i -lt [Math]::Min(50, $lines.Count); $i++) {
            if ($lines[$i] -match '^\s*\$\w*PSScriptRoot' -or 
                $lines[$i] -match '^\s*\$\w*ErrorActionPreference') {
                $insertIndex = $i + 1
                break
            }
        }
        
        # If not found, insert after param block or at line 10
        if ($insertIndex -eq -1) {
            for ($i = 0; $i -lt [Math]::Min(30, $lines.Count); $i++) {
                if ($lines[$i] -match '^\s*\)\s*$' -and $i -gt 5) {
                    $insertIndex = $i + 1
                    break
                }
            }
        }
        
        if ($insertIndex -eq -1) {
            $insertIndex = 10
        }
        
        # Insert settings load code
        # Escape backslashes in the relative path for PowerShell string
        $escapedPath = $settingsRelativePath -replace '\\', '\\'
        
        $settingsCode = @(
            "",
            "# Load shared asset generation settings",
            "`$settingsPath = Join-Path (Split-Path -Parent `$MyInvocation.MyCommand.Path) `"$escapedPath`"",
            "if (Test-Path `$settingsPath) {",
            "    . `$settingsPath",
            "}"
        )
        
        $newLines = @()
        $newLines += $lines[0..($insertIndex - 1)]
        $newLines += $settingsCode
        $newLines += $lines[$insertIndex..($lines.Count - 1)]
        
        # Write updated content
        $newLines | Set-Content $script.FullName -Encoding UTF8
        
        Write-Host "         ✓ Updated" -ForegroundColor Green
        $updatedCount++
        
    } catch {
        Write-Host "         ✗ Error: $_" -ForegroundColor Red
        $errorCount++
    }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Update Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Statistics:" -ForegroundColor Yellow
Write-Host "  Updated: $updatedCount" -ForegroundColor Green
Write-Host "  Skipped: $skippedCount" -ForegroundColor Yellow
Write-Host "  Errors: $errorCount" -ForegroundColor $(if ($errorCount -gt 0) { "Red" } else { "Gray" })
Write-Host ""
